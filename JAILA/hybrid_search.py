# JAILA/hybrid_search.py - Implementering af hybrid søgning uden brug af Weaviate vectorizer

import weaviate
import json
import os
import requests
from typing import List, Dict, Any, Optional
from JAILA.config import weaviate_url, openai_api_key, CLASS_NAME

def generate_embedding_directly(text: str) -> List[float]:
    """Generer embedding direkte ved at kalde OpenAI API fra Python-koden i stedet for gennem Weaviate"""
    url = "https://api.openai.com/v1/embeddings"
    headers = {
        "Authorization": f"Bearer {openai_api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "input": text,
        "model": "text-embedding-ada-002"
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=10)
        if response.status_code == 200:
            return response.json()["data"][0]["embedding"]
        else:
            print(f"Fejl ved generering af embedding: Status {response.status_code}")
            print(response.text)
            return None
    except Exception as e:
        print(f"Fejl ved generering af embedding: {e}")
        return None

def hybrid_search_with_custom_embeddings(query: str, limit: int = 5, offset: int = 0) -> List[Dict[str, Any]]:
    """
    Udfør en hybrid søgning med brugerdefinerede embeddings
    Denne funktion genererer embeddings direkte via OpenAI API og udfører derefter en søgning
    i Weaviate baseret på både vektor-afstand og nøgleord.
    """
    try:
        # Opret Weaviate-klient
        client = weaviate.Client(
            url=weaviate_url,
            additional_headers={
                "X-OpenAI-Api-Key": openai_api_key
            }
        )
        
        # Generer embedding direkte
        query_embedding = generate_embedding_directly(query)
        if query_embedding is None:
            print("Kunne ikke generere embedding, bruger kun nøgleordsbaseret søgning")
            # Brug kun BM25 søgning hvis embedding fejler
            result = client.query.get(
                CLASS_NAME, 
                ["text", "title", "law_number", "paragraph", "stk", "nr", "heading", "summary"]
            ).with_bm25(
                query=query
            ).with_limit(limit).with_offset(offset).do()
        else:
            # Udfør hybrid søgning med manuelt genereret embedding
            result = client.query.get(
                CLASS_NAME, 
                ["text", "title", "law_number", "paragraph", "stk", "nr", "heading", "summary"]
            ).with_hybrid(
                query=query,
                vector=query_embedding,
                alpha=0.5  # Vægtning mellem vektor og nøgleord søgning
            ).with_limit(limit).with_offset(offset).do()
        
        # Udpak resultater
        if "data" in result and "Get" in result["data"] and CLASS_NAME in result["data"]["Get"]:
            return result["data"]["Get"][CLASS_NAME]
        else:
            print("Ingen resultater fundet")
            return []
    except Exception as e:
        print(f"Fejl ved hybrid søgning: {e}")
        return []

def keyword_search(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Udfør en nøgleordsbaseret søgning (BM25) som fallback"""
    try:
        # Opret Weaviate-klient
        client = weaviate.Client(url=weaviate_url)
        
        # Udfør BM25 søgning
        result = client.query.get(
            CLASS_NAME, 
            ["text", "title", "law_number", "paragraph", "stk", "nr", "heading", "summary"]
        ).with_bm25(
            query=query
        ).with_limit(limit).do()
        
        # Udpak resultater
        if "data" in result and "Get" in result["data"] and CLASS_NAME in result["data"]["Get"]:
            return result["data"]["Get"][CLASS_NAME]
        else:
            print("Ingen resultater fundet")
            return []
    except Exception as e:
        print(f"Fejl ved nøgleordsbaseret søgning: {e}")
        return []

# Eksporter denne funktion for at erstatte den problematiske søgning
def robust_search(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Prøv først hybrid søgning og fald tilbage til nøgleordsbaseret søgning ved fejl"""
    print("[INFO] Starter robust søgning for: " + query[:50] + "..." if len(query) > 50 else query)
    
    try:
        print("[INFO] Forsøger hybrid søgning med brugerdefinerede embeddings...")
        results = hybrid_search_with_custom_embeddings(query, limit=limit)
        if results:
            print(f"[INFO] Hybrid søgning fandt {len(results)} resultater.")
            return results
        else:
            print("[WARN] Hybrid søgning gav ingen resultater, prøver nøgleordsbaseret søgning...")
            keyword_results = keyword_search(query, limit=limit)
            print(f"[INFO] Nøgleordsbaseret søgning fandt {len(keyword_results)} resultater.")
            return keyword_results
    except Exception as e:
        print(f"[ERROR] Fejl ved robust søgning: {e}")
        print("[WARN] Falder tilbage til nøgleordsbaseret søgning...")
        try:
            keyword_results = keyword_search(query, limit=limit)
            print(f"[INFO] Nøgleordsbaseret søgning fandt {len(keyword_results)} resultater.")
            return keyword_results
        except Exception as inner_e:
            print(f"[ERROR] Kritisk fejl - nøgleordssøgning fejlede også: {inner_e}")
            # Returner en tom liste som sidste udvej
            return []

"""
Forbindelsesmodul for JAILA.
Håndterer forbindelser til Weaviate vektordatabase og andre eksterne tjenester.
"""
import weaviate
from typing import Optional, Dict, Any, List
from langchain_community.vectorstores import Weaviate
from langchain_openai import OpenAIEmbeddings

from JAILA.config import weaviate_url, CLASS_NAME, METADATA_FIELDS, openai_api_key

def check_weaviate_connection() -> bool:
    """Kontroller om Weaviate-serveren kører og er tilgængelig."""
    try:
        # Forsøg at oprette en klient og hente schema
        client = weaviate.Client(
            url=weaviate_url,
            additional_headers={
                "X-OpenAI-Api-Key": openai_api_key
            }
        )
        
        # Test med schema hentning i stedet for is_ready()
        schema = client.schema.get()
        return True  # Hvis vi når hertil, er forbindelsen OK
    except Exception as e:
        print(f"Fejl ved Weaviate-forbindelse: {e}")
        return False

def get_weaviate_client():
    """Opret og returner en Weaviate-klient."""
    try:
        client = weaviate.Client(
            url=weaviate_url,
            additional_headers={
                "X-OpenAI-Api-Key": openai_api_key
            }
        )
        return client
    except Exception as e:
        print(f"Fejl ved oprettelse af Weaviate-klient: {e}")
        return None

def get_vector_store(class_name: str = CLASS_NAME):
    """
    Opret og returner et LangChain Weaviate vektorlager.
    Returnerer en dummy-vektorbutik, hvis Weaviate ikke er tilgængelig.
    """
    if not check_weaviate_connection():
        print(f"Advarsel: Kan ikke forbinde til Weaviate på {weaviate_url}")
        return DummyVectorStore()
    
    try:
        # Opret embeddings-model
        embeddings = OpenAIEmbeddings(openai_api_key=openai_api_key)
        
        # Opret vektorlager
        vector_store = Weaviate(
            client=get_weaviate_client(),
            index_name=class_name,
            text_key="text_for_embedding",
            embedding=embeddings,
            attributes=METADATA_FIELDS
        )
        
        return vector_store
    except Exception as e:
        print(f"Fejl ved oprettelse af vektorlager: {e}")
        return DummyVectorStore()

class DummyVectorStore:
    """En dummy-vektorbutik til at returnere tomme resultater når Weaviate ikke er tilgængelig."""
    
    def similarity_search(self, query, k=4, **kwargs):
        """Returnerer en tom liste af resultater."""
        print("Dummy vektorbutik blev brugt - ingen resultater.")
        return []
    
    def similarity_search_with_score(self, query, k=4, **kwargs):
        """Returnerer en tom liste af resultater med scores."""
        print("Dummy vektorbutik blev brugt - ingen resultater.")
        return []
    
    def as_retriever(self, **kwargs):
        """Returnerer en dummy retriever."""
        return DummyRetriever()

class DummyRetriever:
    """En dummy retriever til at returnere tomme resultater når Weaviate ikke er tilgængelig."""
    
    def get_relevant_documents(self, query, **kwargs):
        """Returnerer en tom liste af dokumenter."""
        print("Dummy retriever blev brugt - ingen resultater.")
        return []
    
    def invoke(self, query, **kwargs):
        """Returnerer en tom liste af dokumenter."""
        print("Dummy retriever blev brugt - ingen resultater.")
        return []

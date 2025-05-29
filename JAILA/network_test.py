# JAILA/network_test.py - Test for netværksforbindelser og embeddings

import os
import sys
import json
import socket
import requests
import time
from pathlib import Path

# Tilføj rodmappen til Python-stien
sys.path.append(str(Path(__file__).parent.parent))

from JAILA.config import openai_api_key, weaviate_url

def test_dns_resolution(hostname="api.openai.com"):
    """Test DNS-opslag for et specifikt værtsnavn"""
    print(f"\n--- Test af DNS-opslag for {hostname} ---")
    try:
        ip_address = socket.gethostbyname(hostname)
        print(f"[OK] Succes: {hostname} løses til {ip_address}")
        return True
    except socket.gaierror as e:
        print(f"[FEJL] Fejl ved DNS-opslag: {e}")
        return False

def test_openai_connection():
    """Test direkte forbindelse til OpenAI API"""
    print("\n--- Test af forbindelse til OpenAI API ---")
    url = "https://api.openai.com/v1/models"
    headers = {"Authorization": f"Bearer {openai_api_key}"}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            print(f"[OK] Succes: Forbindelse til OpenAI API etableret (status {response.status_code})")
            return True
        else:
            print(f"[FEJL] Fejl: API svarede med status {response.status_code}")
            print(f"Svar: {response.text}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"[FEJL] Fejl ved forbindelse til OpenAI API: {e}")
        return False

def test_embedding_generation():
    """Test generering af embeddings direkte via OpenAI API"""
    print("\n--- Test af embedding-generering via OpenAI API ---")
    url = "https://api.openai.com/v1/embeddings"
    headers = {
        "Authorization": f"Bearer {openai_api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "input": "Dette er en test af embeddings-generering",
        "model": "text-embedding-ada-002"
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=10)
        if response.status_code == 200:
            result = response.json()
            embedding_size = len(result["data"][0]["embedding"])
            print(f"[OK] Succes: Embedding genereret med størrelse {embedding_size}")
            return True
        else:
            print(f"[FEJL] Fejl: API svarede med status {response.status_code}")
            print(f"Svar: {response.text}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"[FEJL] Fejl ved generering af embedding: {e}")
        return False

def test_weaviate_connection():
    """Test forbindelse til Weaviate"""
    print(f"\n--- Test af forbindelse til Weaviate ({weaviate_url}) ---")
    try:
        response = requests.get(f"{weaviate_url}/.well-known/ready", timeout=5)
        if response.status_code == 200:
            print(f"[OK] Succes: Weaviate-server kører (status {response.status_code})")
            return True
        else:
            print(f"[FEJL] Fejl: Weaviate svarede med status {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"[FEJL] Fejl ved forbindelse til Weaviate: {e}")
        return False

def test_weaviate_schema():
    """Test hentning af Weaviate schema"""
    print("\n--- Test af Weaviate schema ---")
    try:
        response = requests.get(f"{weaviate_url}/v1/schema", timeout=5)
        if response.status_code == 200:
            schema = response.json()
            classes = [c["class"] for c in schema.get("classes", [])]
            print(f"[OK] Succes: Schema hentet. Klasser: {', '.join(classes) if classes else 'Ingen klasser fundet'}")
            return True
        else:
            print(f"[FEJL] Fejl: Kunne ikke hente schema (status {response.status_code})")
            print(f"Svar: {response.text}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"[FEJL] Fejl ved hentning af schema: {e}")
        return False

def test_direct_query(query_text="Hvad er reglerne for kørselsfradrag?"):
    """Test en direkte GraphQL-forespørgsel til Weaviate uden OpenAI API"""
    print("\n--- Test af direkte GraphQL-forespørgsel til Weaviate ---")
    url = f"{weaviate_url}/v1/graphql"
    headers = {"Content-Type": "application/json"}
    
    # En simpel forespørgsel der ikke kræver embeddings
    query = {
        "query": """
        {
          Get {
            LegalDocument(limit: 1) {
              text
              title
              law_number
            }
          }
        }
        """
    }
    
    try:
        response = requests.post(url, headers=headers, json=query, timeout=10)
        if response.status_code == 200:
            result = response.json()
            if "errors" in result:
                print(f"[FEJL] Fejl i GraphQL-forespørgsel: {json.dumps(result['errors'], indent=2)}")
                return False
            else:
                print(f"[OK] Succes: Forespørgsel udført")
                print(json.dumps(result["data"], indent=2)[:200] + "..." if len(json.dumps(result["data"])) > 200 else "")
                return True
        else:
            print(f"[FEJL] Fejl: Weaviate svarede med status {response.status_code}")
            print(f"Svar: {response.text}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"[FEJL] Fejl ved forespørgsel: {e}")
        return False

def apply_network_fixes():
    """Anvendt netværks-fixes baseret på testresultater"""
    print("\n--- Anvender netværksfixes ---")
    
    # 1. Opdater hosts-filen med eksplicit IP for api.openai.com
    try:
        # Forsøg at få IP for api.openai.com
        ip = socket.gethostbyname("api.openai.com")
        print(f"OpenAI API IP: {ip}")
        
        # Opdater konfigurationsfilen med direkte IP
        config_path = Path(__file__).parent / "direct_api_config.py"
        with open(config_path, "w") as f:
            f.write(f"""# Auto-genereret konfiguration til direkte API-adgang
OPENAI_API_DIRECT_IP = "{ip}"
OPENAI_API_URL = "https://{ip}/v1"  # Brug IP direkte i stedet for hostname
""")
        print(f"[OK] Konfigurationsfil oprettet: {config_path}")
    except Exception as e:
        print(f"[FEJL] Kunne ikke opdatere konfiguration: {e}")

def run_all_tests():
    """Kør alle tests og rapporter resultater"""
    print("==== JAILA Netværksdiagnostik ====")
    print(f"Tidspunkt: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = {
        "DNS Opslag": test_dns_resolution(),
        "OpenAI API Forbindelse": test_openai_connection(),
        "Embedding Generering": test_embedding_generation(),
        "Weaviate Forbindelse": test_weaviate_connection(),
        "Weaviate Schema": test_weaviate_schema(),
        "Direkte Forespørgsel": test_direct_query()
    }
    
    print("\n==== Test Resultater ====")
    success_count = sum(1 for r in results.values() if r)
    total_count = len(results)
    print(f"Samlet resultat: {success_count}/{total_count} tests bestået")
    
    for name, result in results.items():
        status = "[OK] Bestået" if result else "[FEJL] Fejlet"
        print(f"{name}: {status}")
    
    if success_count < total_count:
        print("\nDer blev fundet problemer. Anvender fixes...")
        apply_network_fixes()
        
        print("\nAnbefalinger til fejlretning:")
        if not results["DNS Opslag"]:
            print("1. Kontroller DNS-indstillinger på din computer/container")
            print("2. Prøv at tilføje 'api.openai.com' manuelt til din hosts-fil")
        
        if not results["OpenAI API Forbindelse"] or not results["Embedding Generering"]:
            print("1. Kontroller at din OPENAI_API_KEY er gyldig")
            print("2. Kontroller at din internetforbindelse tillader forbindelser til api.openai.com")
            print("3. Kontroller om der er firewall-indstillinger der blokerer")
        
        if not results["Weaviate Forbindelse"] or not results["Weaviate Schema"]:
            print("1. Kontroller at Weaviate Docker-containeren kører")
            print("2. Tjek Docker-logs for Weaviate: docker logs <container_id>")
    
    return results

if __name__ == "__main__":
    run_all_tests()

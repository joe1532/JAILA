#!/usr/bin/env python3
"""
Hurtig cleanup script - sletter kun LegalDocument klassen uden interaktive prompts.
Brugt til hurtig rensning før re-import.
"""

import weaviate
import os
import time
from dotenv import load_dotenv

# Indlæs miljøvariabler
load_dotenv()

# Konfiguration
openai_api_key = os.getenv("OPENAI_API_KEY")
weaviate_url = os.getenv("WEAVIATE_URL", "http://localhost:8080")
CLASS_NAME = "LegalDocument"

def quick_cleanup():
    """Hurtig cleanup af LegalDocument klassen"""
    print("🧹 HURTIG DATABASE CLEANUP")
    print("=" * 40)
    
    try:
        # Opret forbindelse
        print(f"📡 Forbinder til Weaviate ({weaviate_url})...")
        client = weaviate.Client(
            url=weaviate_url,
            additional_headers={
                "X-OpenAI-Api-Key": openai_api_key
            }
        )
        
        # Test forbindelse
        schema = client.schema.get()
        print("✅ Forbindelse OK")
        
        # Tjek om klassen eksisterer
        existing_classes = [c['class'] for c in schema.get('classes', [])]
        
        if CLASS_NAME not in existing_classes:
            print(f"ℹ️  Klassen '{CLASS_NAME}' eksisterer ikke - intet at slette")
            return True
        
        # Tæl objekter
        try:
            result = client.query.aggregate(CLASS_NAME).with_meta_count().do()
            if 'data' in result and 'Aggregate' in result['data']:
                count = result['data']['Aggregate'][CLASS_NAME][0]['meta']['count']
                print(f"📊 Fandt {count:,} objekter i {CLASS_NAME}")
            else:
                print(f"📊 {CLASS_NAME} klassen eksisterer (antal objekter ukendt)")
        except Exception as e:
            print(f"📊 {CLASS_NAME} klassen eksisterer (fejl ved tælling: {e})")
        
        # Slet klassen
        print(f"🗑️  Sletter {CLASS_NAME} klassen...")
        client.schema.delete_class(CLASS_NAME)
        
        # Verificer sletning
        time.sleep(1)
        updated_schema = client.schema.get()
        remaining_classes = [c['class'] for c in updated_schema.get('classes', [])]
        
        if CLASS_NAME not in remaining_classes:
            print(f"✅ {CLASS_NAME} klassen er slettet")
            print("🎯 Databasen er klar til re-import med opdateret struktur")
            return True
        else:
            print(f"❌ Fejl: {CLASS_NAME} eksisterer stadig")
            return False
    
    except Exception as e:
        print(f"❌ Fejl under cleanup: {e}")
        return False

def main():
    """Hovedfunktion"""
    success = quick_cleanup()
    
    print("\n" + "=" * 40)
    if success:
        print("🏁 CLEANUP GENNEMFØRT")
        print("\nNæste skridt:")
        print("1. Kør: python import_simple.py")
        print("2. Test: python test_paragraph_search.py")
    else:
        print("🏁 CLEANUP FEJLEDE")
        print("\nPrøv det detaljerede cleanup script:")
        print("python cleanup_database.py")

if __name__ == "__main__":
    main() 
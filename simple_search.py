#!/usr/bin/env python3
"""
Simpelt søgescript - kun retrieval uden LLM
"""

import weaviate
import os
from dotenv import load_dotenv
import re
import sys

# Indlæs miljøvariabler
load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")

# Opret Weaviate klient
client = weaviate.Client(
    url="http://localhost:8080",
    additional_headers={"X-OpenAI-Api-Key": openai_api_key}
)

# Kun felter der faktisk eksisterer i databasen
ALL_FIELDS = [
    "chunk_id", "title", "text", "text_for_embedding", "type", "topic", 
    "keywords", "entities", "rule_type", "law_number", "status", 
    "note_reference_ids", "related_note_chunks", "related_paragraph_chunk_id",
    "summary", "dom_references", "date", "document_name"
]

def detect_paragraph_references(query):
    """Detekterer §-referencer i spørgsmål - nu også med bogstaver"""
    patterns = [
        r'§\s*(\d+\s*[a-zA-Z]*)',       # § 15, § 33 A, § 15a osv.
        r'paragraf\s*(\d+\s*[a-zA-Z]*)', # paragraf 15, paragraf 33 A osv.
        r'section\s*(\d+\s*[a-zA-Z]*)',  # section 15, section 33 A osv.
        r'stk\.?\s*(\d+)',               # stk. 15 eller stk 15 (kun tal)
    ]
    
    references = []
    for pattern in patterns:
        matches = re.findall(pattern, query.lower())
        # Normaliser mellemrum og store/små bogstaver
        normalized_matches = [match.strip().upper() for match in matches]
        references.extend(normalized_matches)
    
    return list(set(references))

def detect_chunk_id(query):
    """Detekterer om query er et chunk ID (UUID format)"""
    # UUID pattern: 8-4-4-4-12 tegn med bindestreger
    uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    return bool(re.match(uuid_pattern, query.lower().strip()))

def chunk_search(chunk_id):
    """Søg efter specifikt chunk ID"""
    try:
        print(f"🔍 Søger efter chunk ID: {chunk_id}")
        
        results = client.query.get("LegalDocument", ALL_FIELDS).with_where({
            "path": ["chunk_id"],
            "operator": "Equal",
            "valueText": chunk_id.strip()
        }).do()
        
        documents = results.get('data', {}).get('Get', {}).get('LegalDocument', [])
        
        if documents:
            doc = documents[0]
            
            # Vis også relaterede dokumenter
            all_results = [doc]
            
            # Hvis det er en paragraf, hent relaterede noter
            if doc.get('type') == 'paragraf':
                related_notes = doc.get('related_note_chunks', [])
                print(f"📝 Henter {len(related_notes)} relaterede noter...")
                
                for note_id in related_notes:
                    note_results = client.query.get("LegalDocument", ALL_FIELDS).with_where({
                        "path": ["chunk_id"],
                        "operator": "Equal",
                        "valueText": note_id
                    }).do()
                    
                    note_docs = note_results.get('data', {}).get('Get', {}).get('LegalDocument', [])
                    all_results.extend(note_docs)
            
            # Hvis det er en note, hent relateret paragraf
            elif doc.get('type') == 'notes':
                para_id = doc.get('related_paragraph_chunk_id')
                if para_id:
                    print(f"📖 Henter relateret paragraf...")
                    
                    para_results = client.query.get("LegalDocument", ALL_FIELDS).with_where({
                        "path": ["chunk_id"],
                        "operator": "Equal",
                        "valueText": para_id
                    }).do()
                    
                    para_docs = para_results.get('data', {}).get('Get', {}).get('LegalDocument', [])
                    all_results.extend(para_docs)
            
            return all_results
        
        return []
        
    except Exception as e:
        print(f"❌ Fejl ved chunk søgning: {e}")
        return []

def paragraph_search(query, limit=5):
    """Søg efter specifikke paragraffer - optimeret prioritering"""
    paragraph_refs = detect_paragraph_references(query)
    
    if not paragraph_refs:
        return None
        
    print(f"🎯 Detekterede paragraffer: {', '.join([f'§ {ref}' for ref in paragraph_refs])}")
    
    all_results = []
    
    for paragraph_ref in paragraph_refs:
        try:
            # Prioriteret søgning: mest specifikke først
            priority_patterns = [
                f"§ {paragraph_ref.lower()}",        # "§ 33 a" - præcis topic match
                f"§ {paragraph_ref}",                # "§ 33 A" - præcis input match
                paragraph_ref.lower(),               # "33 a" - kort topic match
                paragraph_ref,                       # "33 A" - kort input match
            ]
            
            # Søg først efter høj-prioritets matches
            for search_pattern in priority_patterns:
                # Søg i topic først (højest relevans for paragraffer)
                topic_where = {
                    "operator": "And",
                    "operands": [
                        {
                            "path": ["topic"],
                            "operator": "Like",
                            "valueText": f"*{search_pattern}*"
                        },
                        {
                            "path": ["type"],
                            "operator": "Equal",
                            "valueText": "paragraf"
                        }
                    ]
                }
                
                topic_results = client.query.get("LegalDocument", ALL_FIELDS).with_where(topic_where).with_limit(5).do()
                topic_documents = topic_results.get('data', {}).get('Get', {}).get('LegalDocument', [])
                
                # Tilføj topic resultater først (højest relevans)
                for doc in topic_documents:
                    if not any(existing['chunk_id'] == doc['chunk_id'] for existing in all_results):
                        all_results.append(doc)
                        
                        # Hent relaterede noter
                        related_notes = doc.get('related_note_chunks', [])
                        for note_id in related_notes[:1]:  # Kun 1 note per paragraf for at undgå overload
                            note_results = client.query.get("LegalDocument", ALL_FIELDS).with_where({
                                "path": ["chunk_id"],
                                "operator": "Equal",
                                "valueText": note_id
                            }).do()
                            
                            note_docs = note_results.get('data', {}).get('Get', {}).get('LegalDocument', [])
                            for note_doc in note_docs:
                                if not any(existing['chunk_id'] == note_doc['chunk_id'] for existing in all_results):
                                    all_results.append(note_doc)
                
                # Stop hvis vi har nok gode topic resultater
                if len(all_results) >= limit:
                    break
            
            # Kun søg i tekst hvis vi mangler resultater
            if len(all_results) < limit:
                for search_pattern in priority_patterns:
                    text_where = {
                        "operator": "And",
                        "operands": [
                            {
                                "path": ["text"],
                                "operator": "Like", 
                                "valueText": f"*{search_pattern}*"
                            },
                            {
                                "path": ["type"],
                                "operator": "Equal",
                                "valueText": "paragraf"
                            }
                        ]
                    }
                    
                    text_results = client.query.get("LegalDocument", ALL_FIELDS).with_where(text_where).with_limit(3).do()
                    text_documents = text_results.get('data', {}).get('Get', {}).get('LegalDocument', [])
                    
                    for doc in text_documents:
                        if not any(existing['chunk_id'] == doc['chunk_id'] for existing in all_results):
                            all_results.append(doc)
                    
                    # Stop hvis vi har nok resultater
                    if len(all_results) >= limit:
                        break
                    
        except Exception as e:
            print(f"❌ Fejl ved paragraf søgning for § {paragraph_ref}: {e}")
            continue
    
    return all_results[:limit] if all_results else None

def semantic_search(query, limit=5):
    """Semantisk søgning med Weaviate"""
    try:
        results = client.query.get("LegalDocument", ALL_FIELDS).with_near_text({
            "concepts": [query]
        }).with_limit(limit).do()
        
        return results.get('data', {}).get('Get', {}).get('LegalDocument', [])
    except Exception as e:
        print(f"❌ Fejl ved semantisk søgning: {e}")
        return []

def keyword_search(query, limit=5):
    """Nøgleordssøgning - bruger Like operator"""
    try:
        results = client.query.get("LegalDocument", ALL_FIELDS).with_where({
            "path": ["text"],
            "operator": "Like",  # Bruger Like i stedet for Contains
            "valueText": f"*{query}*"
        }).with_limit(limit).do()
        
        return results.get('data', {}).get('Get', {}).get('LegalDocument', [])
    except Exception as e:
        print(f"❌ Fejl ved nøgleord søgning: {e}")
        return []

def print_results(results, search_type=""):
    """Print søgeresultater"""
    if not results:
        print("❌ Ingen resultater fundet")
        return
    
    print(f"\n🔍 {search_type} - {len(results)} resultater:")
    print("=" * 80)
    
    for i, result in enumerate(results, 1):
        print(f"\n📄 RESULTAT {i}:")
        print(f"   ID: {result.get('chunk_id', 'N/A')}")
        print(f"   Type: {result.get('type', 'N/A')}")
        print(f"   Titel: {result.get('title', 'N/A')}")
        print(f"   Topic: {result.get('topic', 'N/A')}")
        print(f"   Lov: {result.get('law_number', 'N/A')}")
        print(f"   Status: {result.get('status', 'N/A')}")
        
        if result.get('keywords'):
            keywords = ', '.join(result['keywords'][:3])
            print(f"   Keywords: {keywords}")
        
        if result.get('rule_type'):
            print(f"   Rule type: {result.get('rule_type', 'N/A')}")
        
        # Vis relationer
        if result.get('related_note_chunks'):
            note_count = len(result['related_note_chunks'])
            print(f"   Relaterede noter: {note_count} stk")
        
        if result.get('related_paragraph_chunk_id'):
            print(f"   Relateret paragraf: {result['related_paragraph_chunk_id']}")
        
        text = result.get('text', '')
        if text:
            if len(text) > 200:
                print(f"   Tekst: {text[:200]}...")
            else:
                print(f"   Tekst: {text}")
        
        print("   " + "-" * 60)

def test_connection():
    """Test Weaviate forbindelse"""
    try:
        client.schema.get()
        print("✅ Weaviate forbindelse OK")
        return True
    except Exception as e:
        print(f"❌ Weaviate fejl: {e}")
        return False

def main():
    """Hovedfunktion for interaktiv søgning"""
    print("🚀 SIMPEL SØGNING (KUN RETRIEVAL)")
    print("=" * 50)
    
    if not test_connection():
        return
    
    if len(sys.argv) > 1:
        # Kommandolinje søgning
        query = ' '.join(sys.argv[1:])
        search_query(query)
        return
    
    print("\nTilgængelige søgetyper:")
    print("1. Automatisk (prøver chunk ID, paragraf, derefter semantisk)")
    print("2. Kun chunk ID søgning")
    print("3. Kun paragraf søgning")
    print("4. Kun semantisk søgning") 
    print("5. Kun nøgleord søgning")
    print("6. Interaktiv søgning")
    
    try:
        choice = input("\nVælg (1-6): ").strip()
        
        if choice == "6":
            interactive_search()
        else:
            # Tilpassede prompts baseret på valg
            prompts = {
                "1": "Indtast søgeord (chunk ID, § reference eller almindeligt ord): ",
                "2": "Indtast chunk ID (UUID format): ",
                "3": "Indtast paragraf reference (f.eks. § 33 A, § 15, paragraf 8): ",
                "4": "Indtast søgeord for semantisk søgning: ",
                "5": "Indtast nøgleord for tekstsøgning: "
            }
            
            prompt = prompts.get(choice, "Indtast søgeord: ")
            query = input(prompt).strip()
            
            if not query:
                return
                
            if choice == "1":
                search_query(query)
            elif choice == "2":
                results = chunk_search(query)
                print_results(results, "CHUNK ID SØGNING")
            elif choice == "3":
                results = paragraph_search(query)
                print_results(results, "PARAGRAF SØGNING")
            elif choice == "4":
                results = semantic_search(query)
                print_results(results, "SEMANTISK SØGNING")
            elif choice == "5":
                results = keyword_search(query)
                print_results(results, "NØGLEORD SØGNING")
                
    except (KeyboardInterrupt, EOFError):
        print("\n👋 Farvel!")

def search_query(query):
    """Udfør søgning med automatisk type detection"""
    print(f"\n🔎 Søger: '{query}'")
    
    # Prøv chunk ID søgning først
    if detect_chunk_id(query):
        chunk_results = chunk_search(query)
        if chunk_results:
            print_results(chunk_results, "CHUNK ID SØGNING")
            return
    
    # Prøv paragraf søgning
    paragraph_results = paragraph_search(query)
    if paragraph_results:
        print_results(paragraph_results, "PARAGRAF SØGNING")
        return
    
    # Ellers semantisk søgning
    semantic_results = semantic_search(query)
    if semantic_results:
        print_results(semantic_results, "SEMANTISK SØGNING")
        return
    
    # Sidste udvej: nøgleord søgning
    keyword_results = keyword_search(query)
    print_results(keyword_results, "NØGLEORD SØGNING")

def interactive_search():
    """Interaktiv søgning"""
    print("\n🎯 INTERAKTIV SØGNING")
    print("Indtast 'quit' for at afslutte")
    print("Kommandoer:")
    print("  'c:chunk-id' (chunk ID)")
    print("  'p:§15' (paragraf)")
    print("  's:skattefradrag' (semantisk)")
    print("  'k:skat' (nøgleord)")
    print("  Eller bare indtast søgeord for automatisk detection")
    
    while True:
        try:
            query = input("\n🔎 Søgeord: ").strip()
            
            if query.lower() in ['quit', 'q', 'exit']:
                print("👋 Farvel!")
                break
            elif not query:
                continue
            
            # Check for kommandoer
            if query.startswith('c:'):
                results = chunk_search(query[2:])
                print_results(results, "CHUNK ID SØGNING")
            elif query.startswith('p:'):
                results = paragraph_search(query[2:])
                print_results(results, "PARAGRAF SØGNING")
            elif query.startswith('s:'):
                results = semantic_search(query[2:])
                print_results(results, "SEMANTISK SØGNING")
            elif query.startswith('k:'):
                results = keyword_search(query[2:])
                print_results(results, "NØGLEORD SØGNING")
            else:
                # Automatisk søgning
                search_query(query)
                
        except KeyboardInterrupt:
            print("\n👋 Afbrudt")
            break
        except EOFError:
            break

if __name__ == "__main__":
    main() 
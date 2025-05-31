#!/usr/bin/env python3
"""
Simpelt søgescript - kun retrieval uden LLM
OPTIMERET FOR PRÆCISE JURIDISKE FORESPØRGSLER
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

# Kun felter der faktisk eksisterer i databasen - OPDATERET TIL NY SCHEMA
ALL_FIELDS = [
    # Grundlæggende felter
    "chunk_id", "title", "text", "text_for_embedding", "type", "topic", 
    "document_name", "law_number", "status", "date",
    
    # LLM genererede felter
    "summary", "keywords", "entities", "rule_type", "rule_type_confidence", 
    "rule_type_explanation", "interpretation_flag", "llm_model_used",
    
    # Strukturelle felter
    "section", "paragraph", "stk", "nr", "heading",
    
    # Relations felter
    "note_reference_ids", "related_note_chunks", "related_paragraph_chunk_id",
    "related_paragraph_ref", "related_paragraph_text", "related_paragraphs",
    
    # Metadata felter
    "note_references", "notes", "note_number", "dom_references"
]

# LOV-SPECIFIKKE FILTRE - OPTIMERET FOR PRÆCIS SØGNING
LAW_FILTERS = {
    'ligningsloven': 'Ligningsloven',
    'kildeskatteloven': 'Kildeskatteloven', 
    'aktieavancebeskatningsloven': 'Aktieavancebeskatningsloven',
    'statsskatteloven': 'Statsskatteloven',
    'ligningslov': 'Ligningsloven',
    'kildeskattelov': 'Kildeskatteloven',
    'aktieavancebeskatningslov': 'Aktieavancebeskatningsloven',
    'statsskattelov': 'Statsskatteloven'
}

def detect_law_filter(query):
    """Detekterer hvilken lov der refereres til i forespørgslen"""
    query_lower = query.lower()
    
    for law_key, law_title in LAW_FILTERS.items():
        if law_key in query_lower:
            print(f"🎯 Detekteret lov-filter: {law_title}")
            return law_title
    
    return None

def detect_paragraph_references(query):
    """Detekterer §-referencer i spørgsmål - FORBEDRET med stykke-matching"""
    patterns = [
        r'§\s*(\d+\s*[a-zA-Z]*)',       # § 15, § 33 A, § 15a osv.
        r'paragraf\s*(\d+\s*[a-zA-Z]*)', # paragraf 15, paragraf 33 A osv.
        r'section\s*(\d+\s*[a-zA-Z]*)',  # section 15, section 33 A osv.
    ]
    
    references = []
    for pattern in patterns:
        matches = re.findall(pattern, query.lower())
        # Normaliser mellemrum og store/små bogstaver
        normalized_matches = [match.strip().upper() for match in matches]
        references.extend(normalized_matches)
    
    return list(set(references))

def detect_stykke_references(query):
    """Detekterer stykke-referencer i spørgsmål - NY FUNKTION"""
    patterns = [
        r'stk\.?\s*(\d+)',     # stk. 7, stk 7
        r'stykke\s*(\d+)',     # stykke 7
    ]
    
    stykke_refs = []
    for pattern in patterns:
        matches = re.findall(pattern, query.lower())
        stykke_refs.extend(matches)
    
    return list(set(stykke_refs))

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
                    if note_id:  # Tjek at note_id ikke er None
                        note_results = client.query.get("LegalDocument", ALL_FIELDS).with_where({
                            "path": ["chunk_id"],
                            "operator": "Equal",
                            "valueText": note_id
                        }).do()
                        
                        note_docs = note_results.get('data', {}).get('Get', {}).get('LegalDocument', [])
                        all_results.extend([doc for doc in note_docs if doc])  # Kun tilføj ikke-None docs
            
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
                    all_results.extend([doc for doc in para_docs if doc])  # Kun tilføj ikke-None docs
            
            return all_results
        
        return []
        
    except Exception as e:
        print(f"❌ Fejl ved chunk søgning: {e}")
        return []

def paragraph_search(query, limit=5):
    """OPTIMERET PARAGRAF SØGNING - med lov-filtrering og præcis stykke-matching"""
    paragraph_refs = detect_paragraph_references(query)
    stykke_refs = detect_stykke_references(query)
    law_filter = detect_law_filter(query)
    
    if not paragraph_refs:
        return None
        
    print(f"🎯 Detekterede paragraffer: {', '.join([f'§ {ref}' for ref in paragraph_refs])}")
    if stykke_refs:
        print(f"🎯 Detekterede stykker: {', '.join([f'stk. {ref}' for ref in stykke_refs])}")
    
    all_results = []
    
    for paragraph_ref in paragraph_refs:
        try:
            # HIERARKISK SØGNING - mest specifikke først
            search_strategies = []
            
            # Hvis både paragraf og stykke specificeret - HØJESTE PRIORITET
            if stykke_refs:
                for stykke_ref in stykke_refs:
                    search_strategies.append({
                        'priority': 1,
                        'type': 'exact_paragraph_stykke',
                        'where': build_precise_where_clause(paragraph_ref, stykke_ref, law_filter),
                        'description': f"§ {paragraph_ref}, stk. {stykke_ref}" + (f" i {law_filter}" if law_filter else ""),
                        'limit': 50  # Øget limit
                    })
            
            # Paragraf med lov-filter - HØJ PRIORITET
            if law_filter:
                search_strategies.append({
                    'priority': 2,
                    'type': 'paragraph_with_law',
                    'where': build_paragraph_law_where_clause(paragraph_ref, law_filter),
                    'description': f"§ {paragraph_ref} i {law_filter}",
                    'limit': 100  # Øget limit
                })
            
            # Kun paragraf - MEDIUM PRIORITET
            search_strategies.append({
                'priority': 3,
                'type': 'paragraph_only',
                'where': build_paragraph_where_clause(paragraph_ref),
                'description': f"§ {paragraph_ref}",
                'limit': 200  # Øget limit
            })
            
            # Udfør søgninger i prioritets-rækkefølge
            found_results = False
            for strategy in sorted(search_strategies, key=lambda x: x['priority']):
                print(f"🔍 Søger: {strategy['description']}")
                
                results = client.query.get("LegalDocument", ALL_FIELDS).with_where(strategy['where']).with_limit(strategy['limit']).do()
                documents = results.get('data', {}).get('Get', {}).get('LegalDocument', [])
                
                if documents:
                    found_results = True
                    
                for doc in documents:
                    if doc and not any(existing and existing.get('chunk_id') == doc.get('chunk_id') for existing in all_results):
                        all_results.append(doc)
                        
                        # Tilføj relaterede noter for paragraffer
                        if doc.get('type') == 'paragraf':
                            related_notes = doc.get('related_note_chunks', [])
                            if related_notes:
                                for note_id in related_notes[:1]:  # Maksimalt 1 note per paragraf
                                    if note_id:
                                        note_results = client.query.get("LegalDocument", ALL_FIELDS).with_where({
                                            "path": ["chunk_id"],
                                            "operator": "Equal",
                                            "valueText": note_id
                                        }).do()
                                        
                                        note_docs = note_results.get('data', {}).get('Get', {}).get('LegalDocument', [])
                                        for note_doc in note_docs:
                                            if note_doc and not any(existing and existing.get('chunk_id') == note_doc.get('chunk_id') for existing in all_results):
                                                all_results.append(note_doc)
                
                # Stop hvis vi har nok høj-prioritets resultater
                if strategy['priority'] <= 2 and len(all_results) >= limit:
                    break
            
            # Hvis WHERE-søgning ikke gav resultater, prøv fallback
            if not found_results:
                print(f"⚠️  WHERE-søgning gav ingen resultater - prøver fallback")
                fallback_results = fallback_manual_search(query, limit)
                if fallback_results:
                    all_results.extend(fallback_results)
                    found_results = True
                    
        except Exception as e:
            print(f"❌ Fejl ved paragraf søgning for § {paragraph_ref}: {e}")
            # Prøv fallback ved fejl
            print(f"🔄 Prøver fallback efter fejl...")
            fallback_results = fallback_manual_search(query, limit)
            if fallback_results:
                all_results.extend(fallback_results)
            continue
    
    return all_results[:limit] if all_results else None

def build_precise_where_clause(paragraph_ref, stykke_ref, law_filter=None):
    """Bygger præcis WHERE clause for paragraf + stykke + evt. lov"""
    conditions = [
        {
            "path": ["paragraph"],
            "operator": "Equal",
            "valueText": f"§ {paragraph_ref}"
        },
        {
            "path": ["stk"],
            "operator": "Equal",
            "valueText": stykke_ref
        },
        {
            "path": ["type"],
            "operator": "Equal",
            "valueText": "paragraf"
        }
    ]
    
    if law_filter:
        conditions.append({
            "path": ["title"],
            "operator": "Equal",
            "valueText": law_filter
        })
    
    return {"operator": "And", "operands": conditions}

def build_paragraph_law_where_clause(paragraph_ref, law_filter):
    """Bygger WHERE clause for paragraf + lov"""
    return {
        "operator": "And",
        "operands": [
            {
                "path": ["paragraph"],
                "operator": "Equal",
                "valueText": f"§ {paragraph_ref}"
            },
            {
                "path": ["title"],
                "operator": "Equal",
                "valueText": law_filter
            },
            {
                "path": ["type"],
                "operator": "Equal",
                "valueText": "paragraf"
            }
        ]
    }

def build_paragraph_where_clause(paragraph_ref):
    """Bygger WHERE clause for kun paragraf - FORBEDRET med højere limit"""
    return {
        "operator": "And",
        "operands": [
            {
                "path": ["paragraph"],
                "operator": "Equal",
                "valueText": f"§ {paragraph_ref}"
            },
            {
                "path": ["type"],
                "operator": "Equal",
                "valueText": "paragraf"
            }
        ]
    }

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
        
        # Vis strukturelle felter
        if result.get('section'):
            print(f"   Sektion: {result.get('section', 'N/A')}")
        if result.get('paragraph'):
            print(f"   Paragraf: {result.get('paragraph', 'N/A')}")
        if result.get('stk'):
            print(f"   Stykke: {result.get('stk', 'N/A')}")
        if result.get('heading'):
            print(f"   Overskrift: {result.get('heading', 'N/A')}")
        
        print(f"   Lov: {result.get('law_number', 'N/A')}")
        print(f"   Status: {result.get('status', 'N/A')}")
        
        if result.get('keywords'):
            keywords = ', '.join(result['keywords'][:3])
            print(f"   Keywords: {keywords}")
        
        if result.get('rule_type'):
            confidence = result.get('rule_type_confidence', '')
            confidence_str = f" ({confidence})" if confidence else ""
            print(f"   Rule type: {result.get('rule_type', 'N/A')}{confidence_str}")
        
        # Vis relationer
        if result.get('related_note_chunks'):
            note_count = len(result['related_note_chunks'])
            print(f"   Relaterede noter: {note_count} stk")
        
        if result.get('related_paragraph_chunk_id'):
            print(f"   Relateret paragraf: {result['related_paragraph_chunk_id']}")
        
        # Vis fortolkningsflag hvis relevant
        if result.get('interpretation_flag'):
            print(f"   🔍 Fortolkning: Ja")
        
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

def fallback_manual_search(query, limit=5):
    """Fallback: Manuel søgning gennem alle dokumenter når WHERE ikke virker"""
    paragraph_refs = detect_paragraph_references(query)
    stykke_refs = detect_stykke_references(query)
    law_filter = detect_law_filter(query)
    
    if not paragraph_refs:
        return None
    
    print(f"🔄 FALLBACK: Manuel søgning gennem database")
    print(f"   Target: § {paragraph_refs[0]}" + (f", stk. {stykke_refs[0]}" if stykke_refs else "") + (f" i {law_filter}" if law_filter else ""))
    
    # Hent mange dokumenter i batches
    all_results = []
    batch_size = 1000
    total_fetched = 0
    
    try:
        # Hent dokumenter i batches
        for offset in range(0, 4000, batch_size):  # Maksimalt 4000 dokumenter
            results = client.query.get("LegalDocument", ALL_FIELDS).with_limit(batch_size).with_offset(offset).do()
            batch_docs = results.get('data', {}).get('Get', {}).get('LegalDocument', [])
            
            if not batch_docs:  # Ingen flere dokumenter
                break
                
            total_fetched += len(batch_docs)
            
            # Filtrér lokalt
            for doc in batch_docs:
                if not doc:
                    continue
                    
                # Check paragraf match
                doc_paragraph = doc.get('paragraph', '')
                target_paragraph = f"§ {paragraph_refs[0]}"
                
                if doc_paragraph != target_paragraph:
                    continue
                
                # Check lov filter
                if law_filter and law_filter not in doc.get('title', ''):
                    continue
                
                # Check stykke filter
                if stykke_refs and doc.get('stk') != stykke_refs[0]:
                    continue
                
                # Check type
                if doc.get('type') != 'paragraf':
                    continue
                
                # Tilføj match
                all_results.append(doc)
                
                # Tilføj relaterede noter
                if doc.get('type') == 'paragraf':
                    related_notes = doc.get('related_note_chunks', [])
                    if related_notes:
                        for note_id in related_notes[:1]:  # Maksimalt 1 note
                            if note_id:
                                note_results = client.query.get("LegalDocument", ALL_FIELDS).with_where({
                                    "path": ["chunk_id"],
                                    "operator": "Equal",
                                    "valueText": note_id
                                }).do()
                                
                                note_docs = note_results.get('data', {}).get('Get', {}).get('LegalDocument', [])
                                for note_doc in note_docs:
                                    if note_doc and not any(existing and existing.get('chunk_id') == note_doc.get('chunk_id') for existing in all_results):
                                        all_results.append(note_doc)
                
                # Stop hvis vi har nok resultater
                if len(all_results) >= limit * 2:  # Mere plads til noter
                    break
            
            # Stop hvis vi har fundet nok
            if len(all_results) >= limit * 2:
                break
        
        print(f"   📊 Søgte gennem {total_fetched} dokumenter")
        print(f"   🎯 Fandt {len(all_results)} matches")
        
        return all_results[:limit] if all_results else None
        
    except Exception as e:
        print(f"❌ Fejl ved manual søgning: {e}")
        return None

if __name__ == "__main__":
    main() 
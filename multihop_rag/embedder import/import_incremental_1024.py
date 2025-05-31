#!/usr/bin/env python3
"""
INCREMENTAL IMPORT SCRIPT - 1024 DIMENSIONER

Dette script kan tilføje nye dokumenter til den eksisterende database
uden at slette eksisterende data.

FEATURES:
- Bevarer eksisterende data
- Duplikat detektion (skip/overwrite options)
- Samme 1024-dim optimering som import_simple_1024.py
- Robust fejlhåndtering
- Batch processing

BRUG:
python import_incremental_1024.py                    # Import alle nye filer
python import_incremental_1024.py --files file1.jsonl file2.jsonl
python import_incremental_1024.py --skip-duplicates  # Skip duplikater
python import_incremental_1024.py --overwrite-duplicates  # Overskriv duplikater
"""

import json
import weaviate
import os
from dotenv import load_dotenv
import time
import jsonlines
import argparse
from typing import List, Dict, Any, Set
from collections import defaultdict

# Indlæs miljøvariabler fra .env filen
load_dotenv()

# Få OpenAI API-nøgle
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    print("❌ ADVARSEL: OPENAI_API_KEY miljøvariabel er ikke sat!")
    exit(1)

print("🔄 INCREMENTAL IMPORT MED 1024 DIMENSIONER")
print("=" * 50)

def create_weaviate_client():
    """Opret Weaviate klient med optimeret konfiguration"""
    try:
        client = weaviate.Client(
            url="http://localhost:8080",
            additional_headers={
                "X-OpenAI-Api-Key": openai_api_key
            }
        )
        print("✅ Forbindelse til Weaviate oprettet!")
        return client
    except Exception as e:
        print(f"❌ Fejl ved oprettelse af forbindelse til Weaviate: {e}")
        exit(1)

def ensure_schema_exists(client):
    """Sørg for at schema eksisterer - opret hvis nødvendigt"""
    print("🔧 Kontrollerer eksisterende skema...")
    
    schema = client.schema.get()
    existing_classes = [c['class'] for c in schema.get('classes', [])]
    
    if "LegalDocument" in existing_classes:
        print("✅ Schema findes allerede.")
        
        # Verificer schema konfiguration
        for cls in schema.get('classes', []):
            if cls['class'] == 'LegalDocument':
                dimensions = cls['moduleConfig']['text2vec-openai'].get('dimensions', 'default')
                print(f"🎯 Schema verificeret - Dimensioner: {dimensions}")
                if dimensions != 1024:
                    print(f"⚠️  Advarsel: Schema bruger {dimensions} dimensioner, ikke 1024!")
                break
        return
    
    print("🔧 Opretter nyt schema med 1024 dimensioner...")
    
    # Brug samme schema definition som import_simple_1024.py
    class_obj = {
        "class": "LegalDocument",
        "vectorizer": "text2vec-openai",
        "moduleConfig": {
            "text2vec-openai": {
                "model": "text-embedding-3-large",
                "modelVersion": "latest",
                "dimensions": 1024,
                "type": "text"
            },
            "generative-openai": {}
        },
        "invertedIndexConfig": {
            "bm25": {
                "b": 0.75,
                "k1": 1.2
            },
            "stopwords": {
                "preset": "en"
            }
        },
        "properties": [
            # PRIMÆRE TEKSTFELTER (Optimeret til 1024 dim)
            {
                "name": "text",
                "dataType": ["text"],
                "description": "Original paragraf/note tekst",
                "indexInverted": True,
                "tokenization": "word",
                "moduleConfig": {
                    "text2vec-openai": {
                        "skip": True
                    }
                }
            },
            {
                "name": "text_for_embedding",
                "dataType": ["text"],
                "description": "Optimeret tekst til 1024-dim embedding",
                "indexInverted": False,
                "moduleConfig": {
                    "text2vec-openai": {
                        "skip": False,
                        "vectorizePropertyName": False
                    }
                }
            },
            
            # IDENTIFIKATIONSFELTER
            {
                "name": "chunk_id",
                "dataType": ["text"],
                "description": "Unik chunk identifier (UUID)",
                "indexInverted": True,
                "tokenization": "field"
            },
            {
                "name": "title",
                "dataType": ["text"],
                "description": "Lovens titel",
                "indexInverted": True,
                "tokenization": "word",
                "moduleConfig": {
                    "text2vec-openai": {
                        "skip": False,
                        "vectorizePropertyName": False
                    }
                }
            },
            {
                "name": "type",
                "dataType": ["text"],
                "description": "Type: 'paragraf' eller 'notes'",
                "indexInverted": True,
                "tokenization": "field"
            },
            {
                "name": "topic",
                "dataType": ["text"],
                "description": "§ reference eller emne (fx '§ 33 A')",
                "indexInverted": True,
                "tokenization": "field",
                "moduleConfig": {
                    "text2vec-openai": {
                        "skip": True
                    }
                }
            },
            
            # METADATA FELTER
            {
                "name": "document_name",
                "dataType": ["text"],
                "description": "Kilde dokumentnavn",
                "indexInverted": True,
                "tokenization": "word"
            },
            {
                "name": "law_number",
                "dataType": ["text"],
                "description": "Lovnummer (fx '2023-01-13 nr. 42')",
                "indexInverted": True,
                "tokenization": "field"
            },
            {
                "name": "status",
                "dataType": ["text"],
                "description": "Status: 'gældende' eller 'historisk'",
                "indexInverted": True,
                "tokenization": "field"
            },
            {
                "name": "date",
                "dataType": ["text"],
                "description": "Lovens dato",
                "indexInverted": True,
                "tokenization": "field"
            },
            
            # SØGEOPTIMERING
            {
                "name": "keywords",
                "dataType": ["text[]"],
                "description": "Ekstraherede søgenøgleord",
                "indexInverted": True
            },
            {
                "name": "entities",
                "dataType": ["text[]"],
                "description": "Navngivne entiteter (organisationer, love, etc.)",
                "indexInverted": True
            },
            {
                "name": "rule_type",
                "dataType": ["text"],
                "description": "Regeltype (definition, procedure, sanktion, etc.)",
                "indexInverted": True,
                "tokenization": "field"
            },
            
            # RELATIONSHIP FELTER
            {
                "name": "note_reference_ids",
                "dataType": ["text[]"],
                "description": "Note reference IDs for paragraf→note mapping",
                "indexInverted": True
            },
            {
                "name": "related_note_chunks",
                "dataType": ["text[]"],
                "description": "Relaterede note chunk IDs",
                "indexInverted": True
            },
            {
                "name": "related_paragraph_chunk_id",
                "dataType": ["text"],
                "description": "Relateret paragraf chunk ID (note→paragraf)",
                "indexInverted": True,
                "tokenization": "field"
            },
            
            # EKSTRA FELTER
            {
                "name": "summary",
                "dataType": ["text"],
                "description": "AI-genereret sammendrag",
                "indexInverted": True,
                "tokenization": "word",
                "moduleConfig": {
                    "text2vec-openai": {
                        "skip": False,
                        "vectorizePropertyName": False
                    }
                }
            },
            {
                "name": "dom_references",
                "dataType": ["text[]"],
                "description": "Referencer til domme og afgørelser",
                "indexInverted": True
            },
            
            # MANGLENDE FELTER FRA JSONL (samme som import_simple_1024.py)
            {
                "name": "heading",
                "dataType": ["text"],
                "description": "Overskrift (fx § 1, stk. 1)",
                "indexInverted": True,
                "tokenization": "field"
            },
            {
                "name": "interpretation_flag",
                "dataType": ["boolean"],
                "description": "Flag for fortolkning"
            },
            {
                "name": "llm_model_used",
                "dataType": ["text"],
                "description": "LLM model brugt til generering",
                "indexInverted": True,
                "tokenization": "field"
            },
            {
                "name": "note_number",
                "dataType": ["text"],
                "description": "Note nummer",
                "indexInverted": True,
                "tokenization": "field"
            },
            {
                "name": "note_references",
                "dataType": ["text"],
                "description": "JSON string med note referencer"
            },
            {
                "name": "notes",
                "dataType": ["text"],
                "description": "JSON string med noter"
            },
            {
                "name": "nr",
                "dataType": ["text"],
                "description": "Nummer (fx 1, 2, 3)",
                "indexInverted": True,
                "tokenization": "field"
            },
            {
                "name": "paragraph",
                "dataType": ["text"],
                "description": "Paragraf reference (fx § 1)",
                "indexInverted": True,
                "tokenization": "field"
            },
            {
                "name": "related_paragraph_ref",
                "dataType": ["text"],
                "description": "Relateret paragraf reference",
                "indexInverted": True,
                "tokenization": "field"
            },
            {
                "name": "related_paragraph_text",
                "dataType": ["text"],
                "description": "Relateret paragraf tekst",
                "indexInverted": True,
                "tokenization": "word"
            },
            {
                "name": "related_paragraphs",
                "dataType": ["text[]"],
                "description": "Liste af relaterede paragraf IDs",
                "indexInverted": True
            },
            {
                "name": "rule_type_confidence",
                "dataType": ["number"],
                "description": "Konfidensscore for regeltypen"
            },
            {
                "name": "rule_type_explanation",
                "dataType": ["text"],
                "description": "Forklaring af regeltypen",
                "indexInverted": True,
                "tokenization": "word"
            },
            {
                "name": "section",
                "dataType": ["text"],
                "description": "Sektion (fx AFSNIT I. SKATTEPLIGTEN)",
                "indexInverted": True,
                "tokenization": "word"
            },
            {
                "name": "stk",
                "dataType": ["text"],
                "description": "Stykke nummer (fx 1, 2, 3)",
                "indexInverted": True,
                "tokenization": "field"
            }
        ]
    }
    
    try:
        client.schema.create_class(class_obj)
        print("✅ Nyt schema oprettet med 1024 dimensioner!")
    except Exception as e:
        print(f"❌ Schema oprettelse fejl: {e}")
        raise

def get_existing_chunk_ids(client) -> Set[str]:
    """Hent alle eksisterende chunk IDs fra databasen"""
    print("🔍 Henter eksisterende chunk IDs...")
    
    try:
        # Hent alle chunk IDs med batching
        existing_ids = set()
        offset = 0
        limit = 1000
        
        while True:
            result = client.query.get("LegalDocument", ["chunk_id"]).with_limit(limit).with_offset(offset).do()
            docs = result.get('data', {}).get('Get', {}).get('LegalDocument', [])
            
            if not docs:
                break
                
            for doc in docs:
                if doc.get('chunk_id'):
                    existing_ids.add(doc['chunk_id'])
            
            offset += limit
            
            if len(docs) < limit:
                break
        
        print(f"📊 Fandt {len(existing_ids)} eksisterende dokumenter")
        return existing_ids
        
    except Exception as e:
        print(f"❌ Fejl ved hentning af eksisterende IDs: {e}")
        return set()

def prepare_document_for_embedding(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Forbered dokument til optimeret 1024-dim embedding (samme som import_simple_1024.py)"""
    
    # Opret optimeret tekst til embedding
    embedding_parts = []
    
    # 1. Titel (vigtig kontekst)
    if doc.get('title'):
        embedding_parts.append(f"Titel: {doc['title']}")
    
    # 2. Type og topic (strukturel kontekst)
    if doc.get('type') and doc.get('topic'):
        embedding_parts.append(f"{doc['type']}: {doc['topic']}")
    
    # 3. Hoved tekst (prioriteret)
    if doc.get('text'):
        text = doc['text']
        if len(text) > 6000:
            text = text[:6000] + "..."
        embedding_parts.append(text)
    
    # 4. Sammendrag hvis tilgængeligt
    if doc.get('summary'):
        embedding_parts.append(f"Sammendrag: {doc['summary']}")
    
    # Kombiner til optimeret embedding tekst
    doc['text_for_embedding'] = " | ".join(embedding_parts)
    
    # Håndter special felter (samme som import_simple_1024.py)
    if 'note_references' in doc and isinstance(doc['note_references'], list):
        doc['note_references'] = json.dumps(doc['note_references'])
    
    if 'notes' in doc and isinstance(doc['notes'], dict):
        doc['notes'] = json.dumps(doc['notes'])
    
    # Sørg for at alle tekst felter er strings
    for field in ['chunk_id', 'section', 'paragraph', 'stk', 'nr', 'heading', 
                  'type', 'document_name', 'title', 'date', 'status', 'law_number', 
                  'topic', 'summary', 'rule_type', 'related_paragraph_chunk_id',
                  'note_number', 'related_paragraph_ref', 'related_paragraph_text',
                  'rule_type_explanation', 'llm_model_used']:
        if field in doc and doc[field] is not None:
            doc[field] = str(doc[field])
        elif field in doc and doc[field] is None:
            del doc[field]
    
    # Håndter number felter
    if 'rule_type_confidence' in doc and doc['rule_type_confidence'] is not None:
        try:
            doc['rule_type_confidence'] = float(doc['rule_type_confidence'])
        except (ValueError, TypeError):
            doc['rule_type_confidence'] = 0.0
    
    # Håndter boolean felter
    if 'interpretation_flag' in doc:
        doc['interpretation_flag'] = bool(doc['interpretation_flag'])
    
    # Håndter list felter
    for list_field in ['keywords', 'entities', 'dom_references', 'related_note_chunks', 
                       'related_paragraphs']:
        if list_field in doc:
            if isinstance(doc[list_field], list):
                doc[list_field] = [str(item) for item in doc[list_field] if item is not None]
            elif doc[list_field] is not None:
                doc[list_field] = [str(doc[list_field])]
            else:
                del doc[list_field]
    
    return doc

def delete_existing_document(client, chunk_id: str) -> bool:
    """Slet eksisterende dokument baseret på chunk_id"""
    try:
        # Find dokumentet først
        result = client.query.get("LegalDocument", ["chunk_id"]).with_where({
            "path": ["chunk_id"],
            "operator": "Equal", 
            "valueText": chunk_id
        }).do()
        
        docs = result.get('data', {}).get('Get', {}).get('LegalDocument', [])
        
        if docs:
            # Slet via batch (mere effektivt)
            client.batch.delete_objects(
                class_name="LegalDocument",
                where={
                    "path": ["chunk_id"],
                    "operator": "Equal",
                    "valueText": chunk_id
                }
            )
            return True
        return False
        
    except Exception as e:
        print(f"   ⚠️  Fejl ved sletning af {chunk_id}: {e}")
        return False

def import_documents_incremental(client, jsonl_files: List[str], batch_size: int = 8, 
                                 skip_duplicates: bool = True, overwrite_duplicates: bool = False):
    """Import dokumenter incrementally"""
    
    print(f"📥 INCREMENTAL IMPORT MED 1024-DIM OPTIMERING")
    print(f"Batch size: {batch_size}")
    print(f"Skip duplikater: {skip_duplicates}")
    print(f"Overskriv duplikater: {overwrite_duplicates}")
    print("-" * 40)
    
    # Hent eksisterende chunk IDs
    existing_ids = get_existing_chunk_ids(client)
    
    total_imported = 0
    total_skipped = 0
    total_overwritten = 0
    total_errors = 0
    
    for file in jsonl_files:
        print(f"\n📄 Behandler: {file}")
        
        try:
            with jsonlines.open(file) as reader:
                batch = []
                file_stats = defaultdict(int)
                
                for i, obj in enumerate(reader):
                    chunk_id = obj.get('chunk_id')
                    
                    if not chunk_id:
                        print(f"   ⚠️  Springer over objekt uden chunk_id (linje {i+1})")
                        total_errors += 1
                        continue
                    
                    # Håndter duplikater
                    if chunk_id in existing_ids:
                        if skip_duplicates and not overwrite_duplicates:
                            file_stats['skipped'] += 1
                            continue
                        elif overwrite_duplicates:
                            # Slet eksisterende dokument
                            if delete_existing_document(client, chunk_id):
                                file_stats['overwritten'] += 1
                                existing_ids.remove(chunk_id)  # Fjern fra cache
                            else:
                                file_stats['errors'] += 1
                                continue
                    
                    # Forbered til optimeret embedding
                    obj = prepare_document_for_embedding(obj)
                    batch.append(obj)
                    file_stats['new'] += 1
                    
                    if len(batch) >= batch_size:
                        # Import batch
                        success, errors = import_batch_with_retry(client, batch)
                        
                        # Opdater statistics
                        total_imported += success
                        total_errors += errors
                        total_skipped += file_stats['skipped']
                        total_overwritten += file_stats['overwritten']
                        
                        # Tilføj nye IDs til cache
                        for doc in batch[:success]:
                            if doc.get('chunk_id'):
                                existing_ids.add(doc['chunk_id'])
                        
                        print(f"   ✅ Batch: +{success} ny, ~{file_stats['skipped']} skipped, ↻{file_stats['overwritten']} overwritten, ❌{errors} fejl")
                        
                        batch = []
                        file_stats = defaultdict(int)
                        
                        # Rate limiting
                        time.sleep(0.3)
                
                # Import sidste batch
                if batch:
                    success, errors = import_batch_with_retry(client, batch)
                    total_imported += success
                    total_errors += errors
                    total_skipped += file_stats['skipped']
                    total_overwritten += file_stats['overwritten']
                    
                    # Tilføj nye IDs til cache
                    for doc in batch[:success]:
                        if doc.get('chunk_id'):
                            existing_ids.add(doc['chunk_id'])
                    
                    print(f"   ✅ Final: +{success} ny, ~{file_stats['skipped']} skipped, ↻{file_stats['overwritten']} overwritten, ❌{errors} fejl")
                    
        except Exception as e:
            print(f"❌ Fejl ved læsning af {file}: {e}")
            continue
    
    print(f"\n🎉 INCREMENTAL IMPORT GENNEMFØRT!")
    print(f"✅ Nye dokumenter importeret: {total_imported}")
    print(f"⏭️  Duplikater skippet: {total_skipped}")
    print(f"↻  Duplikater overskrevet: {total_overwritten}")
    print(f"❌ Fejl: {total_errors}")
    
    total_processed = total_imported + total_skipped + total_overwritten + total_errors
    if total_processed > 0:
        print(f"📊 Success rate: {(total_imported + total_overwritten)/total_processed*100:.1f}%")

def import_batch_with_retry(client, batch: List[Dict], max_retries: int = 3):
    """Import batch med retry logik (samme som import_simple_1024.py)"""
    
    for attempt in range(max_retries):
        try:
            with client.batch as batch_client:
                batch_client.batch_size = len(batch)
                
                for obj in batch:
                    batch_client.add_data_object(
                        data_object=obj,
                        class_name="LegalDocument"
                    )
            
            return len(batch), 0  # success, errors
            
        except Exception as e:
            if attempt == max_retries - 1:
                print(f"   ❌ Batch fejl efter {max_retries} forsøg: {e}")
                return 0, len(batch)
            else:
                print(f"   ⚠️  Forsøg {attempt + 1} fejlede, prøver igen...")
                time.sleep(1)
    
    return 0, len(batch)

def verify_import_incremental(client):
    """Verificer import kvalitet (samme som import_simple_1024.py)"""
    print(f"\n✅ VERIFICERER IMPORT KVALITET")
    print("-" * 30)
    
    try:
        # Check antal dokumenter
        result = client.query.aggregate("LegalDocument").with_meta_count().do()
        count = result.get('data', {}).get('Aggregate', {}).get('LegalDocument', [{}])[0].get('meta', {}).get('count', 0)
        
        print(f"📊 Total dokumenter i database: {count}")
        
        # Test vector størrelse
        result = client.query.get("LegalDocument", ["chunk_id"]).with_additional(["vector"]).with_limit(1).do()
        docs = result.get('data', {}).get('Get', {}).get('LegalDocument', [])
        
        if docs and docs[0].get('_additional', {}).get('vector'):
            vector_size = len(docs[0]['_additional']['vector'])
            print(f"🎯 Vector størrelse: {vector_size} dimensioner")
            
            if vector_size == 1024:
                print("✅ PERFEKT: 1024 dimensioner bekræftet!")
            else:
                print(f"⚠️  Uventet: Fandt {vector_size} dimensioner")
        
        # Test søgefunktionalitet
        test_queries = ["§ 33 A", "fradrag", "skattelempelse"]
        print(f"\n🔍 Tester søgning:")
        
        for query in test_queries:
            try:
                start_time = time.time()
                
                results = client.query.get("LegalDocument", ["chunk_id", "title", "topic"]).with_near_text({
                    "concepts": [query]
                }).with_limit(5).do()
                
                elapsed = time.time() - start_time
                docs = results.get('data', {}).get('Get', {}).get('LegalDocument', [])
                
                print(f"   '{query}': {len(docs)} resultater i {elapsed:.3f}s ✅")
                
            except Exception as e:
                print(f"   '{query}': Fejl - {e} ❌")
        
        return True
        
    except Exception as e:
        print(f"❌ Verificering fejl: {e}")
        return False

def main():
    """Hoved incremental import funktionalitet"""
    parser = argparse.ArgumentParser(description='Incremental import med 1024 dimensioner')
    parser.add_argument('--batch-size', type=int, default=8,
                       help='Batch størrelse (default: 8)')
    parser.add_argument('--files', nargs='*',
                       help='Specifikke .jsonl filer at importere')
    parser.add_argument('--skip-duplicates', action='store_true', default=True,
                       help='Skip duplikater (default: True)')
    parser.add_argument('--overwrite-duplicates', action='store_true',
                       help='Overskriv duplikater (disabler skip-duplicates)')
    parser.add_argument('--no-verify', action='store_true',
                       help='Skip verification efter import')
    
    args = parser.parse_args()
    
    # Håndter konfliktende optioner
    if args.overwrite_duplicates:
        args.skip_duplicates = False
    
    # Opret Weaviate forbindelse
    client = create_weaviate_client()
    
    # Sørg for schema eksisterer
    ensure_schema_exists(client)
    
    # Find filer at importere
    if args.files:
        jsonl_files = [f for f in args.files if f.endswith('_chunks.jsonl')]
    else:
        # Søg i "import embedding" mappen først, derefter current directory
        import_dir = "import embedding"
        if os.path.exists(import_dir):
            jsonl_files = [os.path.join(import_dir, f) for f in os.listdir(import_dir) if f.endswith('_chunks.jsonl')]
        else:
            jsonl_files = [f for f in os.listdir('.') if f.endswith('_chunks.jsonl')]
    
    if not jsonl_files:
        print("⚠️  Ingen .jsonl filer fundet at importere")
        return
    
    print(f"\nFundet {len(jsonl_files)} filer:")
    for file in jsonl_files:
        print(f"  - {file}")
    
    # Start incremental import
    import_documents_incremental(
        client, 
        jsonl_files, 
        batch_size=args.batch_size,
        skip_duplicates=args.skip_duplicates,
        overwrite_duplicates=args.overwrite_duplicates
    )
    
    # Verificer kvalitet
    if not args.no_verify:
        verify_import_incremental(client)
    
    print(f"\n🎉 INCREMENTAL IMPORT GENNEMFØRT!")
    print("💡 Fordele:")
    print("   - Bevarer eksisterende data")
    print("   - Duplikat håndtering")
    print("   - Samme 1024-dim optimering")
    print("   - Robust fejlhåndtering")

if __name__ == "__main__":
    main() 
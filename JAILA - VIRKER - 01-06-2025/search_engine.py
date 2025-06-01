#!/usr/bin/env python3
"""
SEARCH ENGINE - Modular juridisk søgemaskine
Opgraderet til modulær arkitektur - kan importeres af andre systemer
"""

import weaviate
import os
from dotenv import load_dotenv
from typing import List, Dict, Optional, Any
import time
from openai import OpenAI

# Indlæs miljøvariabler
load_dotenv()

class SearchEngine:
    """
    Modular juridisk søgemaskine - kan genbruges af andre systemer
    
    Funktioner:
    - Præcis paragraf søgning (§, stk, nr)
    - Semantisk søgning
    - Keyword søgning  
    - Auto-valg af optimal søgestrategi
    - Hybrid søgning
    """
    
    def __init__(self, weaviate_url: str = "http://localhost:8080", verbose: bool = True):
        """
        Initialize søgemaskinen
        
        Args:
            weaviate_url: URL til Weaviate database
            verbose: Print debug information
        """
        self.weaviate_url = weaviate_url
        self.verbose = verbose
        
        # Get OpenAI API key
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key and verbose:
            print("⚠️ ADVARSEL: OPENAI_API_KEY miljøvariabel mangler - semantic search vil ikke virke!")
        
        # Connect til Weaviate MED OpenAI API key og dimension fix
        additional_headers = {}
        if openai_api_key:
            additional_headers["X-OpenAI-Api-Key"] = openai_api_key
            # Force 1024 dimensions for compatibility with existing data
            additional_headers["X-OpenAI-Dimensions"] = "1024"
        
        self.client = weaviate.Client(
            url=weaviate_url,
            additional_headers=additional_headers
        )
        
        # Test forbindelse
        if not self.test_connection():
            raise ConnectionError(f"Kan ikke forbinde til Weaviate på {weaviate_url}")
        
        if self.verbose:
            print(f"✅ Søgemaskine forbundet til Weaviate ({weaviate_url})")
            if openai_api_key:
                print(f"✅ OpenAI API key konfigureret - semantic search aktiveret (1024 dims)")
    
    def test_connection(self) -> bool:
        """Test om Weaviate forbindelse virker"""
        try:
            self.client.schema.get()
            return True
        except Exception as e:
            if self.verbose:
                print(f"❌ Weaviate forbindelse fejlede: {e}")
            return False
    
    def search(self, query: str, limit: int = 5, search_type: str = "auto") -> List[Dict]:
        """
        Hovedsøgefunktion - automatisk valg af optimal strategi
        
        Args:
            query: Søgeforespørgsel
            limit: Maksimalt antal resultater
            search_type: "auto", "paragraph", "semantic", "keyword", "hybrid"
            
        Returns:
            Liste af søgeresultater
        """
        start_time = time.time()
        
        if self.verbose:
            print(f"\n🔍 SØGER: {query} (type: {search_type}, limit: {limit})")
        
        # Automatisk valg af søgestrategi
        if search_type == "auto":
            search_type = self._determine_search_strategy(query)
            if self.verbose:
                print(f"   📊 Auto-valgt strategi: {search_type}")
        
        # Udfør søgning baseret på strategi
        if search_type == "paragraph_first" or search_type == "paragraph":
            results = self._search_paragraph_first(query, limit)
        elif search_type == "semantic_first" or search_type == "semantic":
            results = self._search_semantic_first(query, limit)
        elif search_type == "keyword":
            results = self._search_keyword(query, limit)
        elif search_type == "hybrid":
            results = self._search_hybrid(query, limit)
        else:
            # Fallback til paragraph_first
            results = self._search_paragraph_first(query, limit)
        
        search_time = time.time() - start_time
        
        if self.verbose:
            print(f"   📄 Fandt {len(results)} resultater på {search_time:.2f}s")
            
        return results
    
    def _determine_search_strategy(self, query: str) -> str:
        """
        Intelligent valg af søgestrategi baseret på query indhold
        
        Prioritering:
        1. Paragraf søgning hvis § eller juridiske referencer
        2. Semantisk søgning for konceptuelle spørgsmål
        3. Keyword som fallback
        """
        query_lower = query.lower()
        
        # Check for juridiske referencer
        juridisk_patterns = [
            '§', 'paragraf', 'stk', 'stykke', 'nr', 'nummer', 
            'kildeskatteloven', 'ligningsloven', 'aktieavancebeskatningsloven',
            'ksl', 'lov nr', 'bekendtgørelse'
        ]
        
        if any(pattern in query_lower for pattern in juridisk_patterns):
            return "paragraph_first"
        
        # Check for konceptuelle spørgsmål
        konceptuel_patterns = [
            'hvad er', 'hvordan', 'hvorfor', 'forskel', 'sammenhæng',
            'betydning', 'definition', 'forklaring', 'eksempel'
        ]
        
        if any(pattern in query_lower for pattern in konceptuel_patterns):
            return "semantic_first"
        
        # Check for sammenlignende spørgsmål
        sammenlignende_patterns = [
            'forskel mellem', 'sammenligne', 'versus', 'vs', 'i forhold til'
        ]
        
        if any(pattern in query_lower for pattern in sammenlignende_patterns):
            return "hybrid"
        
        # Default til paragraph_first for juridiske søgninger
        return "paragraph_first"
    
    def _search_paragraph_first(self, query: str, limit: int) -> List[Dict]:
        """
        Paragraf-først strategi: Prioriterer juridiske paragraffer
        """
        results = []
        
        # 1. Først: Præcis paragraf søgning
        paragraph_results = self._search_precise_paragraph(query, limit // 2)
        if paragraph_results:
            results.extend(paragraph_results)
        
        # 2. Derefter: Semantisk søgning for at fylde op
        if len(results) < limit:
            remaining = limit - len(results)
            semantic_results = self._search_semantic(query, remaining)
            
            # Ensure semantic_results is always a list
            if semantic_results is None:
                semantic_results = []
            
            # Undgå dubletter
            existing_ids = {r.get('chunk_id') for r in results}
            for result in semantic_results:
                if result and result.get('chunk_id') not in existing_ids:
                    results.append(result)
                    if len(results) >= limit:
                        break
        
        return results[:limit]
    
    def _search_semantic_first(self, query: str, limit: int) -> List[Dict]:
        """
        Semantisk-først strategi: Prioriterer semantisk søgning
        """
        results = []
        
        # 1. Først: Semantisk søgning
        semantic_results = self._search_semantic(query, limit)
        if semantic_results:
            results.extend(semantic_results)
        
        # 2. Derefter: Paragraf søgning hvis ikke nok resultater
        if len(results) < limit:
            remaining = limit - len(results)
            paragraph_results = self._search_precise_paragraph(query, remaining)
            
            # Ensure paragraph_results is always a list
            if paragraph_results is None:
                paragraph_results = []
            
            # Undgå dubletter
            existing_ids = {r.get('chunk_id') for r in results}
            for result in paragraph_results:
                if result and result.get('chunk_id') not in existing_ids:
                    results.append(result)
                    if len(results) >= limit:
                        break
        
        return results[:limit]
    
    def _search_hybrid(self, query: str, limit: int) -> List[Dict]:
        """
        Hybrid søgning: Kombinerer alle metoder med vægtning
        """
        results = []
        per_method = max(1, limit // 3)
        
        # Få resultater fra alle metoder
        paragraph_results = self._search_precise_paragraph(query, per_method)
        semantic_results = self._search_semantic(query, per_method)
        keyword_results = self._search_keyword(query, per_method)
        
        # Ensure all results are lists
        if paragraph_results is None:
            paragraph_results = []
        if semantic_results is None:
            semantic_results = []
        if keyword_results is None:
            keyword_results = []
        
        # Kombiner med prioritering
        all_results = []
        
        # Højeste prioritet: paragraf resultater
        all_results.extend([(r, 'paragraph') for r in paragraph_results])
        
        # Mellem prioritet: semantisk resultater  
        all_results.extend([(r, 'semantic') for r in semantic_results])
        
        # Laveste prioritet: keyword resultater
        all_results.extend([(r, 'keyword') for r in keyword_results])
        
        # Fjern dubletter og behold prioritering
        seen_ids = set()
        for result, source in all_results:
            if result:  # Check result is not None
                chunk_id = result.get('chunk_id')
                if chunk_id not in seen_ids:
                    result['search_source'] = source
                    results.append(result)
                    seen_ids.add(chunk_id)
                    if len(results) >= limit:
                        break
        
        return results[:limit]
    
    def _search_precise_paragraph(self, query: str, limit: int) -> List[Dict]:
        """Præcis paragraf søgning med juridiske mønstre"""
        
        # Byg where filter for juridiske referencer
        where_filters = self._build_juridisk_where_filter(query)
        
        if where_filters:
            # Brug where filter hvis juridiske mønstre fundet
            try:
                results = (
                    self.client.query
                    .get("LegalDocument", [
                        "text", "title", "topic", "heading", "nr", "type", 
                        "chunk_id", "law_number", "document_name"
                    ])
                    .with_where(where_filters)
                    .with_limit(limit)
                    .do()
                )
                
                chunks = results.get('data', {}).get('Get', {}).get('LegalDocument', [])
                return self._format_search_results(chunks, "paragraph_where")
                
            except Exception as e:
                if self.verbose:
                    print(f"   ⚠️ Where filter fejlede: {e}")
        
        # Fallback til semantisk søgning med juridisk prioritering
        return self._search_semantic_with_juridisk_boost(query, limit)
    
    def _search_semantic(self, query: str, limit: int) -> List[Dict]:
        """Semantisk vektorsøgning med manual vector search (1024-dim fix)"""
        try:
            # Create OpenAI client and get 1024-dimensional embedding
            openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            
            # Force 1024 dimensions to match existing data
            response = openai_client.embeddings.create(
                model="text-embedding-3-large",
                input=query,
                dimensions=1024
            )
            embedding = response.data[0].embedding
            
            # Use manual vector search with the 1024-dim embedding
            results = (
                self.client.query
                .get("LegalDocument", [
                    "text", "title", "topic", "heading", "nr", "type",
                    "chunk_id", "law_number", "document_name"
                ])
                .with_near_vector({"vector": embedding})
                .with_limit(limit)
                .with_additional(["certainty", "distance"])
                .do()
            )
            
            chunks = results.get('data', {}).get('Get', {}).get('LegalDocument', [])
            return self._format_search_results(chunks, "semantic")
            
        except Exception as e:
            if self.verbose:
                print(f"   ❌ Semantisk søgning fejlede: {e}")
            # Fallback to keyword search
            return self._search_keyword(query, limit)
    
    def _search_keyword(self, query: str, limit: int) -> List[Dict]:
        """Keyword-baseret tekstsøgning"""
        try:
            results = (
                self.client.query
                .get("LegalDocument", [
                    "text", "title", "topic", "heading", "nr", "type",
                    "chunk_id", "law_number", "document_name"  
                ])
                .with_bm25(query=query)
                .with_limit(limit)
                .do()
            )
            
            chunks = results.get('data', {}).get('Get', {}).get('LegalDocument', [])
            return self._format_search_results(chunks, "keyword")
            
        except Exception as e:
            if self.verbose:
                print(f"   ❌ Keyword søgning fejlede: {e}")
            return []
    
    def _search_semantic_with_juridisk_boost(self, query: str, limit: int) -> List[Dict]:
        """Semantisk søgning med boost til juridiske dokumenter"""
        try:
            # Ensure limit is always positive
            boost_limit = max(1, limit // 2)
            
            # Først: Søg kun i paragraffer
            paragraph_results = (
                self.client.query
                .get("LegalDocument", [
                    "text", "title", "topic", "heading", "nr", "type",
                    "chunk_id", "law_number", "document_name"
                ])
                .with_near_text({"concepts": [query]})
                .with_where({
                    "path": ["type"],
                    "operator": "Equal", 
                    "valueText": "paragraf"
                })
                .with_limit(boost_limit)
                .with_additional(["certainty"])
                .do()
            )
            
            results = paragraph_results.get('data', {}).get('Get', {}).get('LegalDocument', [])
            if results is None:
                results = []
            
            # Hvis ikke nok resultater, søg i alle dokumenter
            if len(results) < limit:
                remaining = limit - len(results)
                remaining = max(1, remaining)  # Ensure remaining is positive
                all_results = self._search_semantic(query, remaining * 2)
                
                # Ensure all_results is always a list
                if all_results is None:
                    all_results = []
                
                # Format results first to ensure we have proper structure
                formatted_results = self._format_search_results(results, "paragraph_semantic")
                if formatted_results is None:
                    formatted_results = []
                
                # Tilføj dem der ikke allerede er med
                existing_ids = {r.get('chunk_id') for r in formatted_results if r}
                for result in all_results:
                    if result and result.get('chunk_id') not in existing_ids:
                        results.append(result)
                        if len(results) >= limit:
                            break
            
            return self._format_search_results(results, "semantic_boosted")[:limit]
            
        except Exception as e:
            if self.verbose:
                print(f"   ⚠️ Juridisk boost fejlede: {e}")
            fallback_results = self._search_semantic(query, limit)
            return fallback_results if fallback_results is not None else []
    
    def _build_juridisk_where_filter(self, query: str) -> Optional[Dict]:
        """Byg where filter for juridiske referencer"""
        
        # Udtræk § referencer  
        import re
        
        # Match § nummer
        section_match = re.search(r'§\s*(\d+[a-z]*)', query.lower())
        if section_match:
            section_num = section_match.group(1)
            return {
                "path": ["topic"],
                "operator": "Like",
                "valueText": f"*§ {section_num}*"
            }
        
        # Match lovnavne
        if 'kildeskatteloven' in query.lower() or 'ksl' in query.lower():
            return {
                "path": ["title"],
                "operator": "Like", 
                "valueText": "*kildeskattelov*"
            }
        
        if 'ligningsloven' in query.lower():
            return {
                "path": ["title"],
                "operator": "Like",
                "valueText": "*ligningslov*"
            }
        
        if 'aktieavancebeskatningsloven' in query.lower():
            return {
                "path": ["title"],
                "operator": "Like",
                "valueText": "*aktieavancebeskatning*"
            }
        
        return None
    
    def _expand_paragraph_with_notes(self, paragraph_chunk: Dict) -> List[Dict]:
        """
        Smart chunk expansion - hent ALLE noter automatisk når en paragraf findes
        
        Args:
            paragraph_chunk: En paragraf chunk der skal udvides med noter
            
        Returns:
            Liste med paragraf + alle dens noter
        """
        expanded_chunks = [paragraph_chunk]
        
        # Tjek om det er en paragraf med relaterede noter
        if paragraph_chunk.get('type') == 'paragraf':
            related_note_ids = paragraph_chunk.get('related_note_chunks', [])
            
            if related_note_ids and self.verbose:
                print(f"   📝 Udvider med {len(related_note_ids)} relaterede noter...")
            
            # Hent hver relateret note
            for note_id in related_note_ids:
                if note_id:  # Sikr at note_id ikke er None/tom
                    try:
                        note_results = (
                            self.client.query
                            .get("LegalDocument", [
                                "text", "title", "topic", "heading", "nr", "type",
                                "chunk_id", "law_number", "document_name"
                            ])
                            .with_where({
                                "path": ["chunk_id"],
                                "operator": "Equal",
                                "valueText": note_id
                            })
                            .with_limit(1)
                            .do()
                        )
                        
                        note_docs = note_results.get('data', {}).get('Get', {}).get('LegalDocument', [])
                        if note_docs:
                            expanded_chunks.extend(note_docs)
                            
                    except Exception as e:
                        if self.verbose:
                            print(f"   ⚠️ Kunne ikke hente note {note_id}: {e}")
        
        return expanded_chunks
    
    def _format_search_results(self, chunks: List[Dict], search_method: str) -> List[Dict]:
        """Formater søgeresultater til standard format med smart chunk expansion"""
        # Ensure chunks is always a list
        if chunks is None:
            chunks = []
        
        # Smart expansion: udvid paragraffer med deres noter
        expanded_chunks = []
        seen_chunk_ids = set()
        
        for chunk in chunks:
            if chunk and chunk.get('chunk_id') not in seen_chunk_ids:
                # Udvid paragraf med noter
                if chunk.get('type') == 'paragraf':
                    expanded = self._expand_paragraph_with_notes(chunk)
                    for expanded_chunk in expanded:
                        if expanded_chunk and expanded_chunk.get('chunk_id') not in seen_chunk_ids:
                            expanded_chunks.append(expanded_chunk)
                            seen_chunk_ids.add(expanded_chunk.get('chunk_id', ''))
                else:
                    # For ikke-paragraffer, tilføj direkte
                    expanded_chunks.append(chunk)
                    seen_chunk_ids.add(chunk.get('chunk_id', ''))
        
        # Nu formater de udvidede chunks
        formatted_results = []
        
        for chunk in expanded_chunks:
            # Håndter både direkte chunks og nested structure
            if isinstance(chunk, dict) and '_additional' in chunk:
                # Weaviate format med _additional
                additional = chunk.get('_additional', {})
                result = {
                    'chunk_id': chunk.get('chunk_id', ''),
                    'text': chunk.get('text', ''),
                    'title': chunk.get('title', ''),
                    'paragraph': chunk.get('topic', ''),  # Use topic as paragraph
                    'stk': chunk.get('heading', ''),      # Use heading as stk
                    'nr': chunk.get('nr', ''),
                    'type': chunk.get('type', ''),
                    'law_number': chunk.get('law_number', ''),
                    'source_file': chunk.get('document_name', ''),  # Use document_name as source_file
                    'search_method': search_method,
                    'certainty': additional.get('certainty', 0.0),
                    'distance': additional.get('distance', 0.0)
                }
            else:
                # Simpelt dictionary format
                result = {
                    'chunk_id': chunk.get('chunk_id', ''),
                    'text': chunk.get('text', ''),
                    'title': chunk.get('title', ''),
                    'paragraph': chunk.get('topic', ''),  # Use topic as paragraph
                    'stk': chunk.get('heading', ''),      # Use heading as stk  
                    'nr': chunk.get('nr', ''),
                    'type': chunk.get('type', ''),
                    'law_number': chunk.get('law_number', ''),
                    'source_file': chunk.get('document_name', ''),  # Use document_name as source_file
                    'search_method': search_method,
                    'certainty': 0.0,
                    'distance': 0.0
                }
            
            formatted_results.append(result)
        
        return formatted_results
    
    def get_chunk_by_id(self, chunk_id: str) -> Optional[Dict]:
        """Hent specifik chunk baseret på ID"""
        try:
            results = (
                self.client.query
                .get("LegalDocument", [
                    "text", "title", "topic", "heading", "nr", "type",
                    "chunk_id", "law_number", "document_name"
                ])
                .with_where({
                    "path": ["chunk_id"],
                    "operator": "Equal",
                    "valueText": chunk_id
                })
                .with_limit(1)
                .do()
            )
            
            chunks = results.get('data', {}).get('Get', {}).get('LegalDocument', [])
            if chunks:
                return self._format_search_results(chunks, "direct_id")[0]
            
        except Exception as e:
            if self.verbose:
                print(f"❌ Fejl ved hentning af chunk {chunk_id}: {e}")
        
        return None
    
    def get_database_stats(self) -> Dict:
        """Hent statistikker om databasen"""
        try:
            # Totalt antal chunks
            total_results = (
                self.client.query
                .aggregate("LegalDocument")
                .with_meta_count()
                .do()
            )
            
            total_count = total_results.get('data', {}).get('Aggregate', {}).get('LegalDocument', [{}])[0].get('meta', {}).get('count', 0)
            
            # Simple count per type (compatibility fix for v3)
            type_counts = {}
            try:
                # Try the old v3 API first  
                for doc_type in ['paragraf', 'stykke', 'nummer', 'other']:
                    type_results = (
                        self.client.query
                        .aggregate("LegalDocument")
                        .with_where({
                            "path": ["type"],
                            "operator": "Equal",
                            "valueText": doc_type
                        })
                        .with_meta_count()
                        .do()
                    )
                    count = type_results.get('data', {}).get('Aggregate', {}).get('LegalDocument', [{}])[0].get('meta', {}).get('count', 0)
                    if count > 0:
                        type_counts[doc_type] = count
            except Exception:
                # If type counting fails, just use total
                type_counts = {"total": total_count}
            
            return {
                'total_chunks': total_count,
                'chunks_by_type': type_counts,
                'connection_status': 'connected'
            }
            
        except Exception as e:
            if self.verbose:
                print(f"❌ Fejl ved hentning af database stats: {e}")
            return {
                'total_chunks': 0,
                'chunks_by_type': {},
                'connection_status': 'error',
                'error': str(e)
            }

# === INTERACTIVE FUNCTIONS ===

def interactive_search():
    """Interaktiv søgning - kan importeres og bruges"""
    
    # Initialize søgemaskine
    try:
        engine = SearchEngine()
    except Exception as e:
        print(f"❌ Kunne ikke initialisere søgemaskine: {e}")
        return
    
    print("\n🔍 INTERAKTIV JURIDISK SØGNING")
    print("=" * 50)
    print("Kommandoer:")
    print("  /stats    - Vis database statistikker")
    print("  /help     - Vis hjælp")
    print("  quit      - Afslut")
    print("\nEksempler:")
    print("  § 2")
    print("  kildeskattelovens § 33A")
    print("  hvad er skattepligt")
    
    while True:
        try:
            query = input("\n🔍 Søg: ").strip()
            
            if query.lower() in ['quit', 'q', 'exit']:
                print("👋 Farvel!")
                break
            elif query == '/stats':
                stats = engine.get_database_stats()
                print(f"\n📊 DATABASE STATISTIKKER:")
                print(f"   Total chunks: {stats['total_chunks']:,}")
                print(f"   Status: {stats['connection_status']}")
                if stats['chunks_by_type']:
                    print("   Per type:")
                    for type_name, count in stats['chunks_by_type'].items():
                        print(f"     {type_name}: {count:,}")
                continue
            elif query == '/help':
                print("\n💡 SØGETIPS:")
                print("• § nummer (f.eks. '§ 2')")  
                print("• Lovnavn + paragraf (f.eks. 'kildeskattelovens § 33A')")
                print("• Konceptuelle spørgsmål (f.eks. 'hvad er skattepligt')")
                print("• Stykke/nummer (f.eks. 'stk 3', 'nr 2')")
                continue
            elif not query:
                continue
            
            # Udfør søgning
            results = engine.search(query, limit=5)
            
            if results:
                print(f"\n📄 RESULTATER ({len(results)}):")
                print("-" * 60)
                
                for i, result in enumerate(results, 1):
                    print(f"\n{i}. {result.get('title', 'Ingen titel')}")
                    
                    # Vis juridisk reference hvis tilgængelig
                    ref_parts = []
                    if result.get('paragraph'):
                        ref_parts.append(result['paragraph'])
                    if result.get('stk'):
                        ref_parts.append(f"stk. {result['stk']}")
                    if result.get('nr'):
                        ref_parts.append(f"nr. {result['nr']}")
                    
                    if ref_parts:
                        print(f"   📍 {', '.join(ref_parts)}")
                    
                    print(f"   🔍 Metode: {result.get('search_method', 'unknown')}")
                    print(f"   📄 Type: {result.get('type', 'unknown')}")
                    
                    # Vis tekst preview
                    text = result.get('text', '')
                    preview = text[:200] + "..." if len(text) > 200 else text
                    print(f"   📝 {preview}")
                    
                    if result.get('certainty'):
                        print(f"   🎯 Certainty: {result['certainty']:.2f}")
            else:
                print("\n❌ Ingen resultater fundet")
                print("💡 Prøv at:")
                print("   • Formulere spørgsmålet anderledes")
                print("   • Bruge specifikke juridiske termer")
                print("   • Søge på paragraf numre (§ X)")
        
        except KeyboardInterrupt:
            print("\n👋 Afbrudt")
            break
        except EOFError:
            break

def main():
    """Hovedprogram for standalone brug"""
    import sys
    
    if len(sys.argv) > 1:
        # Kommandolinje søgning
        query = ' '.join(sys.argv[1:])
        engine = SearchEngine()
        results = engine.search(query)
        
        print(f"Søgeresultater for: {query}")
        for i, result in enumerate(results, 1):
            print(f"{i}. {result.get('title', 'N/A')}")
            print(f"   {result.get('text', '')[:200]}...")
    else:
        # Interaktiv mode
        interactive_search()

if __name__ == "__main__":
    main() 
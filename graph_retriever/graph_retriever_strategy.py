# -*- coding: utf-8 -*-
"""
GENERISK GRAPH RETRIEVER STRATEGI FOR SKATTELOVE
==============================================

Denne fil definerer strategien for at bygge en generisk graph retriever 
der kan håndtere alle danske skattelove med optimal kontekstforståelse.

OVERORDNET ARKITEKTUR:
1. Generisk paragraf-baseret graf struktur
2. Hierarkisk organisering (Kapitel -> Afsnit -> Paragraffer)
3. Eksplicitte tekstuelle referencer ("jf. §", "se §")
4. Konceptuelle forbindelser via juridisk indhold
5. Temporal håndtering af lovændringer

STRUKTUR ANALYSE - LIGNINGSLOVEN:
- 179 unikke paragraffer (§1 til §33S)
- Hierarkisk struktur: Kapitler -> Afsnit -> Paragraffer
- Variationer: §12A, §12B, §12C osv.
- Eksplicitte krydsreferencer mellem paragraffer
- Noter tilknyttet hver paragraf
"""

# =============================================================================
# 1. LLM INSTRUKTIONER TIL GRAF BYGGNING
# =============================================================================

GRAPH_BUILDER_PROMPT = """
Du er en ekspert i dansk skatteret og skal bygge en graf af relationer mellem paragraffer i skattelove.

OPGAVE: Analyser følgende paragraffer og identificer alle relationer mellem dem.

RELATION TYPER DU SKAL FINDE:

1. EKSPLICITTE REFERENCER:
   - "jf. §X" (jævnfør paragraf X)
   - "se §X" (se paragraf X)  
   - "efter §X" (efter paragraf X)
   - "i medfør af §X" (i medfør af paragraf X)
   - "som nævnt i §X" (som nævnt i paragraf X)

2. HIERARKISKE RELATIONER:
   - Overordnet/underordnet paragraf struktur
   - Kapitel og afsnit tilhørsforhold
   - Nummererede variationer (§12A, §12B relateret til §12)

3. KONCEPTUELLE FORBINDELSER:
   - Paragraffer der behandler samme skattemæssige koncept
   - Paragraffer der definerer begreber brugt i andre paragraffer
   - Paragraffer der supplerer eller modificerer hinanden

4. PROCEDURALE RELATIONER:
   - Paragraffer der beskriver sekventielle trin
   - Betingelser og konsekvenser
   - Undtagelser og specialregler

OUTPUT FORMAT:
For hver relation, angiv:
- source_paragraph: Kilde paragraf (f.eks. "§15P")
- target_paragraph: Mål paragraf (f.eks. "§15O") 
- relation_type: Type af relation (explicit_reference, hierarchical, conceptual, procedural)
- relation_strength: Styrke (strong, medium, weak)
- explanation: Kort forklaring af relationen på dansk

EKSEMPEL OUTPUT:
{
  "source_paragraph": "§15P",
  "target_paragraph": "§15O", 
  "relation_type": "explicit_reference",
  "relation_strength": "strong",
  "explanation": "§15P henviser eksplicit til §15O med 'jf. §15O'"
}

VIGTIGE REGLER:
- Kun identificer relationer der giver juridisk mening
- Fokuser på relationer der hjælper med forståelse af skattelovgivning
- Undgå strukturelle relationer der ikke har juridisk betydning
- Vær konservativ - bedre at misse en relation end at skabe falske forbindelser
"""

# =============================================================================
# 2. BATCHING STRATEGI FOR OPTIMAL KONTEKST
# =============================================================================

class BatchingStrategy:
    """
    Strategi for at batche paragraffer for maksimal kontekstforståelse
    """
    
    def __init__(self):
        self.max_tokens_per_batch = 15000  # Lad plads til system prompt
        self.overlap_paragraphs = 2        # Overlap mellem batches
        
    def create_batches(self, paragraphs, law_structure):
        """
        Skab batches baseret på juridisk struktur og token limits
        
        PRIORITERING:
        1. Hold kapitler sammen når muligt
        2. Hold afsnit sammen når muligt  
        3. Hold relaterede paragraffer sammen
        4. Respekter token limits
        """
        batches = []
        
        # Organiser efter hierarkisk struktur
        chapters = self._group_by_chapter(paragraphs, law_structure)
        
        for chapter_name, chapter_paragraphs in chapters.items():
            # Prøv at holde hele kapitler sammen
            if self._estimate_tokens(chapter_paragraphs) <= self.max_tokens_per_batch:
                batches.append({
                    'paragraphs': chapter_paragraphs,
                    'context_type': 'full_chapter',
                    'chapter': chapter_name
                })
            else:
                # Split kapitel i mindre batches
                sub_batches = self._split_chapter(chapter_paragraphs)
                batches.extend(sub_batches)
                
        return batches
    
    def _group_by_chapter(self, paragraphs, law_structure):
        """Gruppér paragraffer efter kapitel"""
        
        chapters = {}
        
        for paragraph in paragraphs:
            para_id = paragraph['id']
            
            # Try to get chapter from law structure
            if 'paragraph_hierarchy' in law_structure and para_id in law_structure['paragraph_hierarchy']:
                chapter = law_structure['paragraph_hierarchy'][para_id].get('chapter')
            else:
                # Fallback to metadata
                chapter = paragraph.get('metadata', {}).get('chapter', 'Unknown Chapter')
            
            if chapter not in chapters:
                chapters[chapter] = []
            chapters[chapter].append(paragraph)
        
        return chapters
    
    def _estimate_tokens(self, paragraphs):
        """Estimér tokens for en gruppe paragraffer"""
        # Simpel estimering: ~4 karakterer per token
        total_chars = sum(len(p['content']) for p in paragraphs)
        return total_chars // 4
    
    def _split_chapter(self, chapter_paragraphs):
        """Split et kapitel i mindre batches med overlap"""
        
        batches = []
        current_batch = []
        current_tokens = 0
        
        for paragraph in chapter_paragraphs:
            para_tokens = self._estimate_tokens([paragraph])
            
            # If adding this paragraph would exceed limit, start new batch
            if current_tokens + para_tokens > self.max_tokens_per_batch and current_batch:
                # Add overlap from previous batch
                overlap_start = max(0, len(current_batch) - self.overlap_paragraphs)
                overlap_paragraphs = current_batch[overlap_start:]
                
                batches.append({
                    'paragraphs': current_batch,
                    'context_type': 'chapter_split',
                    'estimated_tokens': current_tokens
                })
                
                # Start new batch with overlap
                current_batch = overlap_paragraphs + [paragraph]
                current_tokens = self._estimate_tokens(current_batch)
            else:
                current_batch.append(paragraph)
                current_tokens += para_tokens
        
        # Add final batch if not empty
        if current_batch:
            batches.append({
                'paragraphs': current_batch,
                'context_type': 'chapter_split',
                'estimated_tokens': current_tokens
            })
        
        return batches

# =============================================================================
# 3. GRAF STRUKTUR DEFINITION
# =============================================================================

class TaxLawGraph:
    """
    Generisk graf struktur for skattelove med stk. og nr. granularitet
    """
    
    def __init__(self, law_name):
        self.law_name = law_name
        self.nodes = {}  # paragraph_id -> node_data
        self.edges = []  # list of relations
        self.hierarchical_relations = []  # Auto-generated hierarchical relations
        
    def add_paragraph_node(self, paragraph_id, content, metadata):
        """Tilføj paragraf som node i grafen med fuld stk./nr. support"""
        # Extract granular information
        entity_type = metadata.get('entity_type', 'paragraph')
        paragraph_num = metadata.get('paragraph_number', metadata.get('paragraph', ''))
        stk_num = metadata.get('stykke_number', metadata.get('stk', ''))
        nr_num = metadata.get('nummer', metadata.get('nr', ''))
        parent_paragraph = metadata.get('parent_paragraph', '')
        
        self.nodes[paragraph_id] = {
            'id': paragraph_id,
            'content': content,
            'law': self.law_name,
            'chapter': metadata.get('chapter'),
            'section': metadata.get('section'),
            'paragraph': paragraph_num,
            'stk': stk_num,
            'nr': nr_num,
            'entity_type': entity_type,
            'parent_paragraph': parent_paragraph,
            'type': 'legal_entity',
            'embedding': None  # Tilføjes senere
        }
        
        # Automatically create hierarchical relations
        self._create_hierarchical_relations(paragraph_id, metadata)
    
    def _create_hierarchical_relations(self, paragraph_id, metadata):
        """Skab hierarkiske relationer automatisk baseret på stk./nr. struktur"""
        entity_type = metadata.get('entity_type', 'paragraph')
        parent_paragraph = metadata.get('parent_paragraph', '')
        
        # Create relation to parent paragraph if this is a stk or nr
        if entity_type in ['stykke', 'nummer'] and parent_paragraph:
            # Store relation to be created after all nodes are added
            hierarchical_relation = {
                'source': parent_paragraph,
                'target': paragraph_id,
                'type': 'hierarchical',
                'subtype': entity_type,
                'strength': 1.0,  # Hierarchical relations are always strong
                'explanation': f"Hierarkisk relation: {parent_paragraph} indeholder {paragraph_id}",
                'law': self.law_name,
                'auto_generated': True
            }
            self.hierarchical_relations.append(hierarchical_relation)
                
        # Create relations between stk and nr within same paragraph
        if entity_type == 'nummer':
            stk_num = metadata.get('stykke_number')
            paragraph_num = metadata.get('paragraph_number', metadata.get('paragraph', ''))
            
            if stk_num and paragraph_num:
                # Find corresponding stk
                stk_id = f"§{paragraph_num}, stk. {stk_num}"
                hierarchical_relation = {
                    'source': stk_id,
                    'target': paragraph_id,
                    'type': 'hierarchical',
                    'subtype': 'stk_to_nr',
                    'strength': 1.0,
                    'explanation': f"Hierarkisk relation: {stk_id} indeholder {paragraph_id}",
                    'law': self.law_name,
                    'auto_generated': True
                }
                self.hierarchical_relations.append(hierarchical_relation)
    
    def add_relation(self, source, target, relation_type, strength, explanation):
        """Tilføj relation mellem paragraffer"""
        self.edges.append({
            'source': source,
            'target': target,
            'type': relation_type,
            'strength': strength,
            'explanation': explanation,
            'law': self.law_name
        })
    
    def get_related_paragraphs(self, paragraph_id, max_depth=2):
        """Find relaterede paragraffer op til en given dybde"""
        related = set()
        to_explore = [(paragraph_id, 0)]
        
        while to_explore:
            current_id, depth = to_explore.pop(0)
            if depth >= max_depth:
                continue
                
            # Find direkte forbindelser
            for edge in self.edges:
                if edge['source'] == current_id:
                    related.add(edge['target'])
                    to_explore.append((edge['target'], depth + 1))
                elif edge['target'] == current_id:
                    related.add(edge['source'])
                    to_explore.append((edge['source'], depth + 1))
        
        return list(related)

# =============================================================================
# 4. IMPLEMENTERINGS STRATEGI
# =============================================================================

class GraphRetrieverImplementation:
    """
    Implementering af graph retriever for skattelove
    """
    
    def __init__(self, verbose=True):
        self.graphs = {}  # law_name -> TaxLawGraph
        self.embeddings_model = "text-embedding-3-large"
        self.verbose = verbose
        
    def build_graph_for_law(self, law_name, paragraphs):
        """
        Byg graf for en specifik skattelov
        
        PROCES:
        1. Analysér lovens struktur
        2. Skab batches for optimal kontekst
        3. Send batches til LLM for relation extraction
        4. Byg graf baseret på LLM output
        5. Validér og optimér graf
        """
        
        # 1. Analysér struktur
        law_structure = self._analyze_law_structure(paragraphs)
        
        # 2. Skab batches
        batching = BatchingStrategy()
        batches = batching.create_batches(paragraphs, law_structure)
        
        # 3. Proces hver batch med LLM
        graph = TaxLawGraph(law_name)
        
        for batch in batches:
            relations = self._extract_relations_from_batch(batch)
            
            # Tilføj noder og relationer til graf
            for paragraph in batch['paragraphs']:
                graph.add_paragraph_node(
                    paragraph['id'], 
                    paragraph['content'],
                    paragraph['metadata']
                )
            
            for relation in relations:
                graph.add_relation(**relation)
        
        # 4. Post-processing og validering
        self._validate_and_optimize_graph(graph)
        
        self.graphs[law_name] = graph
        return graph
    
    def _analyze_law_structure(self, paragraphs):
        """Analysér lovens hierarkiske struktur"""
        import re
        
        structure = {
            'chapters': {},
            'sections': {},
            'paragraph_hierarchy': {},
            'variations': {}
        }
        
        for paragraph in paragraphs:
            para_id = paragraph['id']
            metadata = paragraph.get('metadata', {})
            
            # Extract chapter information
            chapter = self._extract_chapter_info(para_id, metadata)
            if chapter:
                if chapter not in structure['chapters']:
                    structure['chapters'][chapter] = []
                structure['chapters'][chapter].append(para_id)
            
            # Extract section information
            section = self._extract_section_info(para_id, metadata)
            if section:
                if section not in structure['sections']:
                    structure['sections'][section] = []
                structure['sections'][section].append(para_id)
            
            # Identify paragraph variations (§12A, §12B, etc.)
            base_para, variation = self._parse_paragraph_variation(para_id)
            if variation:
                if base_para not in structure['variations']:
                    structure['variations'][base_para] = []
                structure['variations'][base_para].append(para_id)
            
            # Build hierarchy information
            structure['paragraph_hierarchy'][para_id] = {
                'chapter': chapter,
                'section': section,
                'base_paragraph': base_para,
                'variation': variation,
                'metadata': metadata
            }
        
        if self.verbose:
            print(f"📋 Law structure analysis:")
            print(f"   Chapters: {len(structure['chapters'])}")
            print(f"   Sections: {len(structure['sections'])}")
            print(f"   Paragraph variations: {len(structure['variations'])}")
        
        return structure
    
    def _extract_chapter_info(self, para_id, metadata):
        """Extract chapter information from paragraph ID or metadata"""
        
        # First try metadata
        if 'chapter' in metadata:
            return metadata['chapter']
        
        if 'title' in metadata:
            title = metadata['title'].lower()
            if 'kapitel' in title:
                return metadata['title']
        
        # Try to infer from paragraph ID
        # Ligningsloven chapter structure:
        # §1-§3: Kapitel 1 (Skattepligt)
        # §4-§14: Kapitel 2 (Indkomstopgørelse)
        # §15-§18: Kapitel 3 (Særlige fradrag)
        # §19-§25: Kapitel 4 (Selskaber mv.)
        # §26-§33: Kapitel 5 (Administration)
        
        para_num = self._extract_paragraph_number(para_id)
        if para_num:
            if 1 <= para_num <= 3:
                return "Kapitel 1 - Skattepligt"
            elif 4 <= para_num <= 14:
                return "Kapitel 2 - Indkomstopgørelse"
            elif 15 <= para_num <= 18:
                return "Kapitel 3 - Særlige fradrag"
            elif 19 <= para_num <= 25:
                return "Kapitel 4 - Selskaber mv."
            elif 26 <= para_num <= 33:
                return "Kapitel 5 - Administration"
        
        return None
    
    def _extract_section_info(self, para_id, metadata):
        """Extract section information"""
        
        if 'section' in metadata:
            return metadata['section']
        
        # For now, sections are same as chapters in Ligningsloven
        return self._extract_chapter_info(para_id, metadata)
    
    def _parse_paragraph_variation(self, para_id):
        """Parse paragraph variations like §12A, §12B"""
        import re
        
        # Match patterns like §12A, §15P, etc.
        match = re.match(r'§(\d+)([A-Z]*)', para_id.strip())
        if match:
            base_num = int(match.group(1))
            variation = match.group(2) if match.group(2) else None
            base_para = f"§{base_num}"
            return base_para, variation
        
        return para_id, None
    
    def _extract_paragraph_number(self, para_id):
        """Extract numeric part of paragraph ID"""
        import re
        
        match = re.match(r'§(\d+)', para_id.strip())
        if match:
            return int(match.group(1))
        return None
    
    def _extract_relations_from_batch(self, batch):
        """Send batch til LLM og udtræk relationer"""
        import openai
        import json
        import re
        from typing import List, Dict
        
        try:
            # Prepare batch content for LLM
            batch_content = self._prepare_batch_for_llm(batch)
            
            # Create OpenAI client
            client = openai.OpenAI()
            
            # Send to LLM with our specialized prompt
            response = client.chat.completions.create(
                model="gpt-4o-2024-08-06",  # Best for complex reasoning
                messages=[
                    {"role": "system", "content": GRAPH_BUILDER_PROMPT},
                    {"role": "user", "content": batch_content}
                ],
                temperature=0.1,  # Low temperature for consistent extraction
                max_tokens=4000,
                response_format={"type": "json_object"}
            )
            
            # Parse LLM response
            response_text = response.choices[0].message.content
            relations_data = json.loads(response_text)
            
            # Extract and validate relations
            relations = []
            if "relations" in relations_data:
                for relation_data in relations_data["relations"]:
                    relation = self._validate_and_format_relation(relation_data)
                    if relation:
                        relations.append(relation)
            
            # Deduplicate relations
            relations = self._deduplicate_relations(relations)
            
            # Quality scoring
            relations = self._score_relations(relations)
            
            if self.verbose:
                print(f"✅ Extracted {len(relations)} relations from batch of {len(batch['paragraphs'])} paragraphs")
            
            return relations
            
        except json.JSONDecodeError as e:
            if self.verbose:
                print(f"⚠️ JSON parsing error: {e}")
            return []
        except Exception as e:
            if self.verbose:
                print(f"⚠️ Error extracting relations: {e}")
            return []
    
    def _prepare_batch_for_llm(self, batch):
        """Prepare batch content for LLM processing"""
        
        content = "PARAGRAFFER TIL ANALYSE:\n\n"
        
        for paragraph in batch['paragraphs']:
            content += f"PARAGRAF: {paragraph['id']}\n"
            if 'title' in paragraph:
                content += f"TITEL: {paragraph['title']}\n"
            content += f"INDHOLD: {paragraph['content']}\n"
            content += f"METADATA: {json.dumps(paragraph.get('metadata', {}), ensure_ascii=False)}\n"
            content += "-" * 80 + "\n\n"
        
        content += "\nINSTRUKTIBON: Analyser ovenstående paragraffer og identificer alle juridiske relationer mellem dem. Returner resultatet som JSON med følgende struktur:\n"
        content += '{"relations": [{"source_paragraph": "§X", "target_paragraph": "§Y", "relation_type": "explicit_reference", "relation_strength": "strong", "explanation": "Forklaring på dansk"}]}'
        
        return content
    
    def _validate_and_format_relation(self, relation_data):
        """Validate and format a single relation"""
        
        required_fields = ['source_paragraph', 'target_paragraph', 'relation_type', 'relation_strength', 'explanation']
        
        # Check required fields
        for field in required_fields:
            if field not in relation_data:
                return None
        
        # Validate relation types
        valid_relation_types = ['explicit_reference', 'hierarchical', 'conceptual', 'procedural']
        if relation_data['relation_type'] not in valid_relation_types:
            return None
        
        # Validate relation strengths
        valid_strengths = ['strong', 'medium', 'weak']
        if relation_data['relation_strength'] not in valid_strengths:
            return None
        
        # Validate paragraph IDs (should start with §)
        source = relation_data['source_paragraph'].strip()
        target = relation_data['target_paragraph'].strip()
        
        if not (source.startswith('§') and target.startswith('§')):
            return None
        
        # Don't allow self-references
        if source == target:
            return None
        
        return {
            'source': source,
            'target': target,
            'type': relation_data['relation_type'],
            'strength': relation_data['relation_strength'],
            'explanation': relation_data['explanation'].strip()
        }
    
    def _deduplicate_relations(self, relations):
        """Remove duplicate relations"""
        
        seen = set()
        deduplicated = []
        
        for relation in relations:
            # Create a unique key for this relation
            key = (relation['source'], relation['target'], relation['type'])
            reverse_key = (relation['target'], relation['source'], relation['type'])
            
            # Don't add if we've seen this relation or its reverse
            if key not in seen and reverse_key not in seen:
                seen.add(key)
                deduplicated.append(relation)
        
        return deduplicated
    
    def _score_relations(self, relations):
        """Score relation quality and confidence"""
        
        for relation in relations:
            # Start with base score based on strength
            if relation['strength'] == 'strong':
                relation['score'] = 0.9
            elif relation['strength'] == 'medium':
                relation['score'] = 0.7
            else:
                relation['score'] = 0.5
            
            # Boost score for explicit references
            if relation['type'] == 'explicit_reference':
                relation['score'] += 0.1
            
            # Boost score if explanation contains specific legal terms
            explanation = relation['explanation'].lower()
            if any(term in explanation for term in ['jf.', 'jævnfør', 'henviser', 'se §', 'efter §']):
                relation['score'] += 0.05
            
            # Cap at 1.0
            relation['score'] = min(relation['score'], 1.0)
        
        return relations
    
    def _validate_and_optimize_graph(self, graph):
        """Validér og optimér den byggede graf"""
        
        if self.verbose:
            initial_nodes = len(graph.nodes)
            initial_edges = len(graph.edges)
            print(f"🔍 Validating graph: {initial_nodes} nodes, {initial_edges} edges")
        
        # 1. Remove edges with non-existent nodes
        valid_edges = []
        orphaned_references = []
        
        for edge in graph.edges:
            source_exists = edge['source'] in graph.nodes
            target_exists = edge['target'] in graph.nodes
            
            if source_exists and target_exists:
                valid_edges.append(edge)
            else:
                orphaned_references.append(edge)
                if self.verbose:
                    print(f"⚠️ Removing orphaned edge: {edge['source']} -> {edge['target']}")
        
        graph.edges = valid_edges
        
        # 2. Remove duplicate edges (same source, target, type)
        seen_edges = set()
        deduplicated_edges = []
        
        for edge in graph.edges:
            edge_key = (edge['source'], edge['target'], edge['type'])
            if edge_key not in seen_edges:
                seen_edges.add(edge_key)
                deduplicated_edges.append(edge)
            else:
                if self.verbose:
                    print(f"🔄 Removing duplicate edge: {edge['source']} -> {edge['target']}")
        
        graph.edges = deduplicated_edges
        
        # 3. Validate edge consistency
        self._validate_edge_consistency(graph)
        
        # 4. Score and rank edges
        self._score_graph_edges(graph)
        
        # 5. Remove weak edges (optional optimization)
        if len(graph.edges) > 1000:  # Only for large graphs
            graph.edges = self._filter_weak_edges(graph.edges)
        
        # 6. Validate graph connectivity
        connectivity_stats = self._analyze_graph_connectivity(graph)
        
        # 7. Add structural relations if missing
        self._add_missing_structural_relations(graph)
        
        if self.verbose:
            final_nodes = len(graph.nodes)
            final_edges = len(graph.edges)
            print(f"✅ Graph validation complete:")
            print(f"   Nodes: {initial_nodes} -> {final_nodes}")
            print(f"   Edges: {initial_edges} -> {final_edges}")
            print(f"   Orphaned references removed: {len(orphaned_references)}")
            print(f"   Average connections per node: {final_edges / final_nodes:.1f}")
        
        return graph
    
    def _validate_edge_consistency(self, graph):
        """Validate logical consistency of edges"""
        
        inconsistent_edges = []
        
        for edge in graph.edges:
            # Check for logical inconsistencies
            source_node = graph.nodes.get(edge['source'])
            target_node = graph.nodes.get(edge['target'])
            
            if not source_node or not target_node:
                continue
            
            # Check if hierarchical relations make sense
            if edge['type'] == 'hierarchical':
                if not self._validate_hierarchical_relation(source_node, target_node):
                    inconsistent_edges.append(edge)
                    continue
            
            # Check if explicit references are valid
            if edge['type'] == 'explicit_reference':
                if not self._validate_explicit_reference(edge, source_node):
                    inconsistent_edges.append(edge)
                    continue
        
        # Remove inconsistent edges
        for edge in inconsistent_edges:
            graph.edges.remove(edge)
            if self.verbose:
                print(f"⚠️ Removed inconsistent edge: {edge['source']} -> {edge['target']} ({edge['type']})")
    
    def _validate_hierarchical_relation(self, source_node, target_node):
        """Validate if hierarchical relation makes sense"""
        
        # Both nodes should be in same law
        if source_node.get('law') != target_node.get('law'):
            return False
        
        # Check chapter relationships
        source_ch = source_node.get('chapter')
        target_ch = target_node.get('chapter')
        
        if source_ch and target_ch and source_ch != target_ch:
            # Cross-chapter hierarchical relations are rare
            return False
        
        return True
    
    def _validate_explicit_reference(self, edge, source_node):
        """Validate explicit reference by checking source content"""
        
        source_content = source_node.get('content', '').lower()
        target_id = edge['target'].lower()
        
        # Check if the source actually contains reference to target
        reference_patterns = [
            f"jf. {target_id}",
            f"jævnfør {target_id}",
            f"se {target_id}",
            f"efter {target_id}",
            f"i medfør af {target_id}"
        ]
        
        for pattern in reference_patterns:
            if pattern in source_content:
                return True
        
        return False
    
    def _score_graph_edges(self, graph):
        """Score all edges in the graph"""
        
        for edge in graph.edges:
            if 'score' not in edge:
                edge['score'] = 0.5  # Default score
            
            # Boost score based on type
            if edge['type'] == 'explicit_reference':
                edge['score'] += 0.2
            elif edge['type'] == 'hierarchical':
                edge['score'] += 0.1
            
            # Boost score based on strength
            if edge['strength'] == 'strong':
                edge['score'] += 0.3
            elif edge['strength'] == 'medium':
                edge['score'] += 0.1
            
            # Cap at 1.0
            edge['score'] = min(edge['score'], 1.0)
    
    def _filter_weak_edges(self, edges):
        """Remove edges with very low scores"""
        
        # Sort by score descending
        sorted_edges = sorted(edges, key=lambda x: x.get('score', 0), reverse=True)
        
        # Keep top 80% of edges
        keep_count = int(len(sorted_edges) * 0.8)
        filtered_edges = sorted_edges[:keep_count]
        
        if self.verbose:
            removed_count = len(edges) - len(filtered_edges)
            print(f"🧹 Filtered out {removed_count} weak edges")
        
        return filtered_edges
    
    def _analyze_graph_connectivity(self, graph):
        """Analyze graph connectivity statistics"""
        
        if not graph.nodes:
            return {}
        
        # Count connections per node
        connection_counts = {}
        for node_id in graph.nodes:
            connection_counts[node_id] = 0
        
        for edge in graph.edges:
            connection_counts[edge['source']] += 1
            connection_counts[edge['target']] += 1
        
        # Calculate statistics
        counts = list(connection_counts.values())
        stats = {
            'total_nodes': len(graph.nodes),
            'total_edges': len(graph.edges),
            'avg_connections': sum(counts) / len(counts) if counts else 0,
            'max_connections': max(counts) if counts else 0,
            'min_connections': min(counts) if counts else 0,
            'isolated_nodes': sum(1 for c in counts if c == 0)
        }
        
        return stats
    
    def _add_missing_structural_relations(self, graph):
        """Add obvious structural relations that might have been missed"""
        
        # Group nodes by chapter
        chapters = {}
        for node_id, node_data in graph.nodes.items():
            chapter = node_data.get('chapter')
            if chapter:
                if chapter not in chapters:
                    chapters[chapter] = []
                chapters[chapter].append(node_id)
        
        # Add hierarchical relations within chapters if missing
        added_relations = 0
        for chapter, paragraphs in chapters.items():
            for i, para1 in enumerate(paragraphs):
                for para2 in paragraphs[i+1:]:
                    # Check if relation already exists
                    relation_exists = any(
                        (edge['source'] == para1 and edge['target'] == para2) or
                        (edge['source'] == para2 and edge['target'] == para1)
                        for edge in graph.edges
                    )
                    
                    if not relation_exists:
                        # Add weak hierarchical relation
                        graph.add_relation(
                            source=para1,
                            target=para2,
                            relation_type='hierarchical',
                            strength='weak',
                            explanation=f"Samme kapitel: {chapter}"
                        )
                        added_relations += 1
        
        if self.verbose and added_relations > 0:
            print(f"📝 Added {added_relations} missing structural relations")

# =============================================================================
# 5. COST ESTIMATION FOR LIGNINGSLOVEN
# =============================================================================

def estimate_cost_ligningsloven():
    """
    Estimér omkostninger for at bygge graf for Ligningsloven
    """
    
    # Baseret på tidligere analyse:
    total_paragraphs = 701  # Kun paragraffer, ikke noter
    avg_tokens_per_paragraph = 200  # Konservativt estimat
    total_input_tokens = total_paragraphs * avg_tokens_per_paragraph
    
    # GPT-4o-2024-08-06 priser:
    input_cost_per_1k = 0.0025  # $2.50 per 1M tokens
    output_cost_per_1k = 0.01   # $10.00 per 1M tokens
    
    # Estimeret output: ~50 tokens per relation, ~3 relationer per paragraf
    estimated_relations = total_paragraphs * 3
    total_output_tokens = estimated_relations * 50
    
    input_cost = (total_input_tokens / 1000) * input_cost_per_1k
    output_cost = (total_output_tokens / 1000) * output_cost_per_1k
    
    total_cost = input_cost + output_cost
    
    return {
        'total_paragraphs': total_paragraphs,
        'total_input_tokens': total_input_tokens,
        'total_output_tokens': total_output_tokens,
        'input_cost_usd': input_cost,
        'output_cost_usd': output_cost,
        'total_cost_usd': total_cost,
        'total_cost_dkk': total_cost * 7  # Approx exchange rate
    }

# =============================================================================
# 6. USAGE EXAMPLE
# =============================================================================

if __name__ == "__main__":
    # Estimér omkostninger
    cost_estimate = estimate_cost_ligningsloven()
    print("COST ESTIMATE FOR LIGNINGSLOVEN GRAPH:")
    print(f"Total paragraffer: {cost_estimate['total_paragraphs']}")
    print(f"Input tokens: {cost_estimate['total_input_tokens']:,}")
    print(f"Output tokens: {cost_estimate['total_output_tokens']:,}")
    print(f"Total cost: ${cost_estimate['total_cost_usd']:.3f} / {cost_estimate['total_cost_dkk']:.0f} DKK")
    
    # Eksempel på brug
    implementation = GraphRetrieverImplementation()
    
    # Byg graf for Ligningsloven
    # ligningsloven_paragraphs = load_ligningsloven_data()
    # graph = implementation.build_graph_for_law("ligningsloven", ligningsloven_paragraphs)
    
    # Find relaterede paragraffer
    # related = graph.get_related_paragraphs("§15P", max_depth=2)
    # print(f"Paragraffer relateret til §15P: {related}")

# =============================================================================
# 7. LIGNINGSLOVEN SPECIFIK BATCHING STRATEGI
# =============================================================================

def create_ligningsloven_batches():
    """
    Specifik batching strategi for Ligningsloven baseret på juridisk struktur
    
    LIGNINGSLOVEN STRUKTUR (baseret på retsinformation.dk):
    - Kapitel 1: Skattepligt (§1-§3)
    - Kapitel 2: Indkomstopgørelse (§4-§14)
    - Kapitel 3: Særlige fradrag (§15-§18)
    - Kapitel 4: Selskaber mv. (§19-§25)
    - Kapitel 5: Administration (§26-§33)
    
    OPTIMAL BATCHING:
    1. Batch per kapitel når muligt
    2. Split store kapitler ved naturlige afsnit
    3. Overlap ved krydsreferencer
    """
    
    batching_plan = {
        'kapitel_1_skattepligt': {
            'paragraphs': ['§1', '§2', '§3'],
            'estimated_tokens': 2000,
            'context': 'Grundlæggende skattepligt regler'
        },
        'kapitel_2_indkomst_del1': {
            'paragraphs': ['§4', '§5', '§6', '§7'],
            'estimated_tokens': 8000,
            'context': 'Indkomstopgørelse - grundregler'
        },
        'kapitel_2_indkomst_del2': {
            'paragraphs': ['§8', '§9', '§10', '§11'],
            'estimated_tokens': 8000,
            'context': 'Indkomstopgørelse - specielle regler'
        },
        'kapitel_2_indkomst_del3': {
            'paragraphs': ['§12', '§12A', '§12B', '§12C', '§13', '§14'],
            'estimated_tokens': 10000,
            'context': 'Indkomstopgørelse - afskrivninger og særregler'
        },
        'kapitel_3_fradrag': {
            'paragraphs': ['§15', '§15A', '§15B', '§15C', '§15D', '§15E', '§15F', '§15G', '§15H', '§15I', '§15J', '§15K', '§15L', '§15M', '§15N', '§15O', '§15P', '§15Q', '§15R', '§15S', '§16', '§17', '§18'],
            'estimated_tokens': 15000,
            'context': 'Særlige fradrag - komplet kapitel'
        }
    }
    
    return batching_plan 
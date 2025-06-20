#!/usr/bin/env python3
"""
Enhanced Graph Retriever Strategy med fuld stk./nr. support
==========================================================

Denne forbedrede version af graph retriever strategien inkluderer:
- Fuld granularitet for stk. og nr.
- Automatisk hierarkiske relationer
- Forbedret metadata håndtering
- Bedre relation extraction på finkornet niveau

Dato: 7. december 2024
"""

import os
import re
import json
import openai
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

# =============================================================================
# 1. ENHANCED GRAF STRUKTUR
# =============================================================================

class EnhancedTaxLawGraph:
    """
    Forbedret graf struktur med fuld stk./nr. granularitet
    """
    
    def __init__(self, law_name):
        self.law_name = law_name
        self.nodes = {}  # entity_id -> node_data
        self.edges = []  # list of relations
        self.hierarchical_relations = []  # Auto-generated hierarchical relations
        self.metadata = {
            'created_at': datetime.now().isoformat(),
            'law_name': law_name,
            'enhanced_granularity': True,
            'version': '2.0'
        }
        
    def add_legal_entity_node(self, entity_id, content, metadata):
        """
        Tilføj legal entity (paragraf, stk, nr) som node med fuld granularitet
        """
        # Extract granular information
        entity_type = metadata.get('entity_type', 'paragraph')
        paragraph_num = metadata.get('paragraph_number', metadata.get('paragraph', ''))
        stk_num = metadata.get('stykke_number', metadata.get('stk', ''))
        nr_num = metadata.get('nummer', metadata.get('nr', ''))
        parent_paragraph = metadata.get('parent_paragraph', '')
        
        # Create comprehensive node
        self.nodes[entity_id] = {
            'id': entity_id,
            'content': content,
            'law': self.law_name,
            'chapter': metadata.get('chapter', ''),
            'section': metadata.get('section', ''),
            'paragraph': paragraph_num,
            'stk': stk_num,
            'nr': nr_num,
            'entity_type': entity_type,
            'parent_paragraph': parent_paragraph,
            'type': 'legal_entity',
            'granularity_level': self._determine_granularity_level(entity_type),
            'title': metadata.get('title', entity_id),
            'status': metadata.get('status', 'gældende'),
            'embedding': None,  # Tilføjes senere
            'created_at': datetime.now().isoformat()
        }
        
        # Automatically create hierarchical relations
        self._queue_hierarchical_relations(entity_id, metadata)
        
    def _determine_granularity_level(self, entity_type):
        """Determine the granularity level of the legal entity"""
        levels = {
            'paragraph': 1,  # §15O
            'stykke': 2,     # §15O, stk. 2
            'nummer': 3      # §15O, stk. 2, nr. 3
        }
        return levels.get(entity_type, 0)
    
    def _queue_hierarchical_relations(self, entity_id, metadata):
        """
        Queue hierarchical relations to be created after all nodes are loaded
        """
        entity_type = metadata.get('entity_type', 'paragraph')
        parent_paragraph = metadata.get('parent_paragraph', '')
        
        # Create relation to parent paragraph if this is a stk or nr
        if entity_type in ['stykke', 'nummer'] and parent_paragraph:
            hierarchical_relation = {
                'source': parent_paragraph,
                'target': entity_id,
                'type': 'hierarchical',
                'subtype': entity_type,
                'strength': 1.0,  # Hierarchical relations are always strong
                'confidence': 1.0,
                'explanation': f"Hierarkisk relation: {parent_paragraph} indeholder {entity_id}",
                'law': self.law_name,
                'auto_generated': True,
                'granularity_relation': True
            }
            self.hierarchical_relations.append(hierarchical_relation)
                
        # Create relations between stk and nr within same paragraph
        if entity_type == 'nummer':
            stk_num = metadata.get('stykke_number')
            paragraph_num = metadata.get('paragraph_number', metadata.get('paragraph', ''))
            
            if stk_num and paragraph_num:
                # Build stk ID
                stk_id = f"§{paragraph_num}, stk. {stk_num}"
                hierarchical_relation = {
                    'source': stk_id,
                    'target': entity_id,
                    'type': 'hierarchical',
                    'subtype': 'stk_to_nr',
                    'strength': 1.0,
                    'confidence': 1.0,
                    'explanation': f"Hierarkisk relation: {stk_id} indeholder {entity_id}",
                    'law': self.law_name,
                    'auto_generated': True,
                    'granularity_relation': True
                }
                self.hierarchical_relations.append(hierarchical_relation)
    
    def finalize_hierarchical_relations(self):
        """
        Finalize all queued hierarchical relations after all nodes are loaded
        """
        finalized_relations = []
        
        for relation in self.hierarchical_relations:
            source = relation['source']
            target = relation['target']
            
            # Only add relation if both source and target exist
            if source in self.nodes and target in self.nodes:
                finalized_relations.append(relation)
                # Also add to edges for retrieval
                self.edges.append({
                    'source': source,
                    'target': target,
                    'type': relation['type'],
                    'strength': relation['strength'],
                    'explanation': relation['explanation'],
                    'law': self.law_name,
                    'auto_generated': True,
                    'subtype': relation.get('subtype', ''),
                    'confidence': relation.get('confidence', 1.0)
                })
        
        self.hierarchical_relations = finalized_relations
        return len(finalized_relations)
    
    def add_relation(self, source, target, relation_type, strength, explanation, confidence=0.8):
        """Tilføj relation mellem legal entities"""
        self.edges.append({
            'source': source,
            'target': target,
            'type': relation_type,
            'strength': strength,
            'confidence': confidence,
            'explanation': explanation,
            'law': self.law_name,
            'auto_generated': False
        })
    
    def get_related_entities(self, entity_id, max_depth=2, include_hierarchical=True):
        """
        Find relaterede legal entities op til en given dybde
        """
        related = set()
        to_explore = [(entity_id, 0)]
        
        while to_explore:
            current_id, depth = to_explore.pop(0)
            if depth >= max_depth:
                continue
                
            # Find direkte forbindelser
            for edge in self.edges:
                # Skip hierarchical if not wanted
                if not include_hierarchical and edge.get('auto_generated', False):
                    continue
                    
                if edge['source'] == current_id:
                    related.add(edge['target'])
                    to_explore.append((edge['target'], depth + 1))
                elif edge['target'] == current_id:
                    related.add(edge['source'])
                    to_explore.append((edge['source'], depth + 1))
        
        return list(related)
    
    def get_entity_hierarchy(self, entity_id):
        """
        Get the full hierarchy for a specific entity
        """
        if entity_id not in self.nodes:
            return None
            
        node = self.nodes[entity_id]
        entity_type = node['entity_type']
        
        hierarchy = {
            'entity': entity_id,
            'type': entity_type,
            'level': node['granularity_level'],
            'parent': node.get('parent_paragraph', ''),
            'children': []
        }
        
        # Find children
        for edge in self.edges:
            if (edge['source'] == entity_id and 
                edge.get('auto_generated', False) and 
                edge['type'] == 'hierarchical'):
                hierarchy['children'].append(edge['target'])
        
        return hierarchy
    
    def get_statistics(self):
        """Get comprehensive graph statistics"""
        total_nodes = len(self.nodes)
        total_edges = len(self.edges)
        hierarchical_edges = len([e for e in self.edges if e.get('auto_generated', False)])
        content_edges = total_edges - hierarchical_edges
        
        # Node type breakdown
        node_types = {}
        for node in self.nodes.values():
            entity_type = node['entity_type']
            node_types[entity_type] = node_types.get(entity_type, 0) + 1
        
        return {
            'total_nodes': total_nodes,
            'total_edges': total_edges,
            'hierarchical_edges': hierarchical_edges,
            'content_edges': content_edges,
            'node_types': node_types,
            'average_edges_per_node': total_edges / total_nodes if total_nodes > 0 else 0,
            'law_name': self.law_name,
            'enhanced_version': True
        }


# =============================================================================
# 2. DEMO OG TEST FUNKTIONER
# =============================================================================

def demo_enhanced_graph_with_real_data():
    """Demo med rigtige Ligningsloven data"""
    
    print("🚀 Demo: Enhanced Graph Retriever med rigtige stk./nr.")
    print("=" * 60)
    
    # Simulér rigtige data fra chunker
    sample_entities = [
        {
            'id': '§15O',
            'content': 'Ved opgørelsen af den skattepligtige indkomst...',
            'metadata': {
                'entity_type': 'paragraph',
                'paragraph_number': '15O',
                'title': '§15O',
                'chapter': 'Ligningsloven',
                'section': '§15O',
                'status': 'gældende'
            }
        },
        {
            'id': '§15O, stk. 1',
            'content': 'Bundfradrag ved opgørelse af ejendomsværdiskat...',
            'metadata': {
                'entity_type': 'stykke',
                'paragraph_number': '15O',
                'stykke_number': '1',
                'parent_paragraph': '§15O',
                'title': '§15O, stk. 1',
                'status': 'gældende'
            }
        },
        {
            'id': '§15O, stk. 2',
            'content': 'Alternativt kan skatteyder vælge faktiske udgifter...',
            'metadata': {
                'entity_type': 'stykke',
                'paragraph_number': '15O',
                'stykke_number': '2',
                'parent_paragraph': '§15O', 
                'title': '§15O, stk. 2',
                'status': 'gældende'
            }
        },
        {
            'id': '§15P',
            'content': 'Ved opgørelsen af den skattepligtige indkomst for helårsboliger...',
            'metadata': {
                'entity_type': 'paragraph',
                'paragraph_number': '15P',
                'title': '§15P',
                'chapter': 'Ligningsloven',
                'section': '§15P',
                'status': 'gældende'
            }
        },
        {
            'id': '§15P, stk. 1',
            'content': 'Bundfradrag for helårsboliger beregnes som...',
            'metadata': {
                'entity_type': 'stykke',
                'paragraph_number': '15P',
                'stykke_number': '1',
                'parent_paragraph': '§15P',
                'title': '§15P, stk. 1',
                'status': 'gældende'
            }
        },
        {
            'id': '§15P, stk. 2',
            'content': 'Særlige regler gælder for ejendomme erhvervet efter...',
            'metadata': {
                'entity_type': 'stykke',
                'paragraph_number': '15P',
                'stykke_number': '2',
                'parent_paragraph': '§15P',
                'title': '§15P, stk. 2',
                'status': 'gældende'
            }
        }
    ]
    
    # Opret enhanced graph
    graph = EnhancedTaxLawGraph("Ligningsloven")
    
    print("📝 Adding entities to graph...")
    # Tilføj alle entities
    for entity in sample_entities:
        graph.add_legal_entity_node(
            entity['id'],
            entity['content'],
            entity['metadata']
        )
    
    # Finalise hierarkiske relationer
    hierarchical_count = graph.finalize_hierarchical_relations()
    
    print(f"✅ Created {hierarchical_count} hierarchical relations")
    
    # Tilføj nogle content relationer manuelt (simulerer LLM output)
    print("🔗 Adding content relations...")
    
    # Conceptual relation mellem bundfradrag regler
    graph.add_relation(
        source='§15O, stk. 1',
        target='§15P, stk. 1',
        relation_type='conceptual',
        strength=0.9,
        explanation='Begge stykker omhandler bundfradrag beregning',
        confidence=0.95
    )
    
    # Alternative relation mellem bundfradrag og faktiske udgifter
    graph.add_relation(
        source='§15O, stk. 1',
        target='§15O, stk. 2',
        relation_type='alternative',
        strength=0.95,
        explanation='Valgmulighed mellem bundfradrag og faktiske udgifter',
        confidence=0.98
    )
    
    # Procedural relation
    graph.add_relation(
        source='§15P, stk. 1',
        target='§15P, stk. 2',
        relation_type='procedural',
        strength=0.8,
        explanation='Særlige regler følger efter hovedregel',
        confidence=0.85
    )
    
    # Vis resultater
    print("\n📊 Final Graph Statistics:")
    stats = graph.get_statistics()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    print("\n🏗️ Hierarchical Relations:")
    for relation in graph.hierarchical_relations:
        print(f"   {relation['source']} → {relation['target']} ({relation['subtype']})")
    
    print("\n🔗 Content Relations:")
    content_relations = [e for e in graph.edges if not e.get('auto_generated', False)]
    for relation in content_relations:
        print(f"   {relation['source']} ↔ {relation['target']} ({relation['type']}) - {relation['strength']:.2f}")
    
    print("\n🔍 Testing Entity Retrieval:")
    
    # Test relation retrieval for §15O, stk. 1
    test_entity = '§15O, stk. 1'
    related = graph.get_related_entities(test_entity, max_depth=2)
    print(f"\n   Related to {test_entity}:")
    for rel_entity in related:
        print(f"     → {rel_entity}")
    
    # Test hierarchy for specific entity
    hierarchy = graph.get_entity_hierarchy('§15O, stk. 1')
    print(f"\n   Hierarchy for {test_entity}:")
    print(f"     Type: {hierarchy['type']}")
    print(f"     Level: {hierarchy['level']}")
    print(f"     Parent: {hierarchy['parent']}")
    print(f"     Children: {hierarchy['children']}")
    
    return graph

def test_granularity_benefits():
    """Test der viser fordelen ved granularitet"""
    
    print("\n🧪 Testing Granularity Benefits")
    print("=" * 40)
    
    graph = demo_enhanced_graph_with_real_data()
    
    # Sammenlign queries på forskellige granularitets-niveauer
    test_queries = [
        "§15O",              # Hele paragraf
        "§15O, stk. 1",      # Specifikt stykke
        "§15O, stk. 2"       # Andet stykke
    ]
    
    for query in test_queries:
        print(f"\n🔍 Query: {query}")
        related = graph.get_related_entities(query, max_depth=1)
        print(f"   Direct relations: {len(related)}")
        for rel in related[:3]:  # Show first 3
            print(f"     → {rel}")
    
    print("\n💡 Benefits of Granularity:")
    print("   - Præcise relationer mellem specifikke stykker")
    print("   - Bedre context for bruger queries") 
    print("   - Automatiske hierarkiske strukturer")
    print("   - Højere kvalitet retrieval")

if __name__ == "__main__":
    # Kør demo
    graph = demo_enhanced_graph_with_real_data()
    
    # Test granularitet
    test_granularity_benefits()
    
    print("\n✅ Enhanced Graph Retriever demonstration completed!")
    print("🎯 Ready for integration with JAILA RAG system")

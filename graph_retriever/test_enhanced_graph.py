#!/usr/bin/env python3
"""
Test Enhanced Graph Retriever - Demonstration af stk./nr. granularitet
=======================================================================

Dette script demonstrerer problemet og løsningen for stk./nr. support
"""

from datetime import datetime

class EnhancedTaxLawGraph:
    """
    Enhanced graf struktur med fuld stk./nr. granularitet
    """
    
    def __init__(self, law_name):
        self.law_name = law_name
        self.nodes = {}
        self.edges = []
        self.hierarchical_relations = []
        self.metadata = {
            'created_at': datetime.now().isoformat(),
            'law_name': law_name,
            'enhanced_granularity': True
        }
        
    def add_legal_entity_node(self, entity_id, content, metadata):
        """Add legal entity with full granularity support"""
        entity_type = metadata.get('entity_type', 'paragraph')
        paragraph_num = metadata.get('paragraph_number', '')
        stk_num = metadata.get('stykke_number', '')
        nr_num = metadata.get('nummer', '')
        parent_paragraph = metadata.get('parent_paragraph', '')
        
        # Create comprehensive node
        self.nodes[entity_id] = {
            'id': entity_id,
            'content': content,
            'law': self.law_name,
            'paragraph': paragraph_num,
            'stk': stk_num,
            'nr': nr_num,
            'entity_type': entity_type,
            'parent_paragraph': parent_paragraph,
            'granularity_level': self._get_granularity_level(entity_type),
            'title': metadata.get('title', entity_id)
        }
        
        # Queue hierarchical relations
        self._queue_hierarchical_relations(entity_id, metadata)
        
    def _get_granularity_level(self, entity_type):
        """Get granularity level"""
        levels = {
            'paragraph': 1,  # §15O
            'stykke': 2,     # §15O, stk. 2
            'nummer': 3      # §15O, stk. 2, nr. 3
        }
        return levels.get(entity_type, 0)
    
    def _queue_hierarchical_relations(self, entity_id, metadata):
        """Queue hierarchical relations"""
        entity_type = metadata.get('entity_type', 'paragraph')
        parent_paragraph = metadata.get('parent_paragraph', '')
        
        # Create relation to parent if this is stk or nr
        if entity_type in ['stykke', 'nummer'] and parent_paragraph:
            hierarchical_relation = {
                'source': parent_paragraph,
                'target': entity_id,
                'type': 'hierarchical',
                'subtype': entity_type,
                'strength': 1.0,
                'explanation': f"Hierarkisk: {parent_paragraph} → {entity_id}",
                'auto_generated': True
            }
            self.hierarchical_relations.append(hierarchical_relation)
    
    def finalize_hierarchical_relations(self):
        """Finalize hierarchical relations"""
        finalized = 0
        for relation in self.hierarchical_relations:
            source = relation['source']
            target = relation['target']
            
            # Only add if both source and target exist
            if source in self.nodes and target in self.nodes:
                self.edges.append(relation)
                finalized += 1
        
        return finalized
    
    def add_relation(self, source, target, relation_type, strength, explanation):
        """Add content relation"""
        self.edges.append({
            'source': source,
            'target': target,
            'type': relation_type,
            'strength': strength,
            'explanation': explanation,
            'auto_generated': False
        })
    
    def get_statistics(self):
        """Get graph statistics"""
        total_nodes = len(self.nodes)
        total_edges = len(self.edges)
        hierarchical_edges = len([e for e in self.edges if e.get('auto_generated', False)])
        content_edges = total_edges - hierarchical_edges
        
        node_types = {}
        for node in self.nodes.values():
            entity_type = node['entity_type']
            node_types[entity_type] = node_types.get(entity_type, 0) + 1
        
        return {
            'total_nodes': total_nodes,
            'total_edges': total_edges,
            'hierarchical_edges': hierarchical_edges,
            'content_edges': content_edges,
            'node_types': node_types
        }

def demo_problem_and_solution():
    """Demonstrate the problem and solution"""
    
    print("🚨 PROBLEM DEMONSTRATION")
    print("=" * 50)
    
    # Original approach (paragraph level only)
    print("❌ Original Approach - Paragraph Level Only:")
    print("   Node: §15O (hele paragraf)")
    print("   Node: §15P (hele paragraf)")
    print("   Relation: §15O ↔ §15P (unspecific)")
    print("   Problem: Mangler granularitet!")
    
    print("\n✅ ENHANCED SOLUTION")
    print("=" * 50)
    
    # Enhanced approach with stk/nr
    graph = EnhancedTaxLawGraph("Ligningsloven")
    
    # Sample data mimicking real chunker output
    sample_entities = [
        {
            'id': '§15O',
            'content': 'Hovedparagraf om fritidsbolig bundfradrag...',
            'metadata': {
                'entity_type': 'paragraph',
                'paragraph_number': '15O',
                'title': '§15O'
            }
        },
        {
            'id': '§15O, stk. 1',
            'content': 'Bundfradrag beregnes som standardfradrag...',
            'metadata': {
                'entity_type': 'stykke',
                'paragraph_number': '15O',
                'stykke_number': '1',
                'parent_paragraph': '§15O',
                'title': '§15O, stk. 1'
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
                'title': '§15O, stk. 2'
            }
        },
        {
            'id': '§15P, stk. 1',
            'content': 'For helårsboliger beregnes bundfradrag som...',
            'metadata': {
                'entity_type': 'stykke',
                'paragraph_number': '15P',
                'stykke_number': '1',
                'parent_paragraph': '§15P',
                'title': '§15P, stk. 1'
            }
        }
    ]
    
    print("📝 Adding entities with full granularity:")
    for entity in sample_entities:
        graph.add_legal_entity_node(
            entity['id'],
            entity['content'],
            entity['metadata']
        )
        print(f"   ✓ {entity['id']} ({entity['metadata']['entity_type']})")
    
    # Finalize hierarchical relations
    hierarchical_count = graph.finalize_hierarchical_relations()
    print(f"\n🏗️ Auto-generated hierarchical relations: {hierarchical_count}")
    
    # Add specific content relations
    print("\n🔗 Adding precise content relations:")
    
    # Precise relation between specific stykker
    graph.add_relation(
        source='§15O, stk. 1',
        target='§15P, stk. 1',
        relation_type='conceptual',
        strength=0.9,
        explanation='Begge stykker omhandler bundfradrag beregning'
    )
    print("   ✓ §15O, stk. 1 ↔ §15P, stk. 1 (conceptual)")
    
    # Alternative relation within same paragraph
    graph.add_relation(
        source='§15O, stk. 1',
        target='§15O, stk. 2',
        relation_type='alternative',
        strength=0.95,
        explanation='Valgmulighed: bundfradrag eller faktiske udgifter'
    )
    print("   ✓ §15O, stk. 1 ↔ §15O, stk. 2 (alternative)")
    
    # Show final statistics
    print("\n📊 Final Statistics:")
    stats = graph.get_statistics()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    print("\n🏗️ Hierarchical Relations:")
    hierarchical_relations = [e for e in graph.edges if e.get('auto_generated', False)]
    for rel in hierarchical_relations:
        print(f"   {rel['source']} → {rel['target']} ({rel['subtype']})")
    
    print("\n🔗 Content Relations:")
    content_relations = [e for e in graph.edges if not e.get('auto_generated', False)]
    for rel in content_relations:
        print(f"   {rel['source']} ↔ {rel['target']} ({rel['type']}) - {rel['strength']:.2f}")
    
    print("\n💡 BENEFITS:")
    print("   ✅ Præcise relationer mellem specifikke stykker")
    print("   ✅ Automatiske hierarkiske strukturer")
    print("   ✅ Bedre granularitet for queries")
    print("   ✅ Højere kvalitet retrieval")
    
    return graph

if __name__ == "__main__":
    graph = demo_problem_and_solution()
    print("\n🎯 Enhanced Graph Retriever ready for integration!") 
# -*- coding: utf-8 -*-
"""
GRAPH RETRIEVER MODULE FOR JAILA
===============================

Clean implementation af graph-based document retrieval for juridiske dokumenter.
Designet til integration med JAILA's eksisterende search engine.
"""

import json
import os
import re
import openai
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class GraphRelation:
    """Repræsentation af en relation mellem paragraffer"""
    source: str
    target: str
    relation_type: str  # explicit_reference, hierarchical, conceptual, procedural
    strength: str       # strong, medium, weak
    explanation: str
    score: float = 0.0


@dataclass
class GraphNode:
    """Repræsentation af en paragraf node i grafen"""
    id: str
    content: str
    metadata: Dict
    law: str
    chapter: Optional[str] = None
    section: Optional[str] = None


class TaxLawGraph:
    """Knowledge graph for en specifik skattelov"""
    
    def __init__(self, law_name: str):
        self.law_name = law_name
        self.nodes: Dict[str, GraphNode] = {}
        self.relations: List[GraphRelation] = []
        self._adjacency_cache = None
    
    def add_node(self, node: GraphNode):
        """Tilføj en node til grafen"""
        self.nodes[node.id] = node
        self._adjacency_cache = None
    
    def add_relation(self, relation: GraphRelation):
        """Tilføj en relation til grafen"""
        self.relations.append(relation)
        self._adjacency_cache = None
    
    def get_related_nodes(self, node_id: str, max_depth: int = 2) -> List[str]:
        """Find relaterede nodes op til given dybde"""
        if self._adjacency_cache is None:
            self._build_adjacency_cache()
        
        visited = set()
        to_visit = [(node_id, 0)]
        related = []
        
        while to_visit:
            current_id, depth = to_visit.pop(0)
            
            if current_id in visited or depth > max_depth:
                continue
                
            visited.add(current_id)
            
            if depth > 0:  # Don't include the starting node
                related.append(current_id)
            
            if depth < max_depth:
                neighbors = self._adjacency_cache.get(current_id, [])
                for neighbor in neighbors:
                    if neighbor not in visited:
                        to_visit.append((neighbor, depth + 1))
        
        return related
    
    def _build_adjacency_cache(self):
        """Build adjacency list for faster traversal"""
        self._adjacency_cache = {}
        
        for node_id in self.nodes:
            self._adjacency_cache[node_id] = []
        
        for relation in self.relations:
            if relation.source in self._adjacency_cache:
                self._adjacency_cache[relation.source].append(relation.target)
            if relation.target in self._adjacency_cache:
                self._adjacency_cache[relation.target].append(relation.source)
    
    def get_statistics(self) -> Dict:
        """Get graf statistikker"""
        return {
            'nodes': len(self.nodes),
            'relations': len(self.relations),
            'avg_connections': len(self.relations) * 2 / len(self.nodes) if self.nodes else 0,
            'law': self.law_name
        }


class GraphRetriever:
    """Graph-enhanced document retriever for JAILA integration"""
    
    def __init__(self, graph_storage_dir: str = "graphs", verbose: bool = True):
        self.graph_storage_dir = graph_storage_dir
        self.verbose = verbose
        self.graphs: Dict[str, TaxLawGraph] = {}
        
        # Ensure storage directory exists
        os.makedirs(graph_storage_dir, exist_ok=True)
    
    def get_graph_enhanced_results(self, query_terms: List[str], base_results: List[Dict], 
                                 law_name: str = "ligningsloven", max_related: int = 5) -> List[Dict]:
        """
        Enhance search results using graph relationships
        
        Args:
            query_terms: Search terms from user query
            base_results: Base search results from semantic search
            law_name: Which law graph to use
            max_related: Maximum related paragraphs to include
        
        Returns:
            Enhanced results with graph-related paragraphs
        """
        
        if law_name not in self.graphs:
            if self.verbose:
                print(f"⚠️ No graph available for {law_name}")
            return base_results
        
        graph = self.graphs[law_name]
        enhanced_results = base_results.copy()
        
        # Extract paragraph IDs from base results
        base_paragraph_ids = set()
        for result in base_results:
            para_id = self._extract_paragraph_id(result)
            if para_id:
                base_paragraph_ids.add(para_id)
        
        # Find related paragraphs
        related_paragraphs = set()
        for para_id in base_paragraph_ids:
            if para_id in graph.nodes:
                related = graph.get_related_nodes(para_id, max_depth=2)
                related_paragraphs.update(related[:max_related])
        
        # Add related paragraphs to results
        for para_id in related_paragraphs:
            if para_id not in base_paragraph_ids and para_id in graph.nodes:
                node = graph.nodes[para_id]
                enhanced_result = {
                    'paragraph': para_id,
                    'text': node.content,
                    'metadata': node.metadata,
                    'source': 'graph_relation',
                    'score': 0.6
                }
                enhanced_results.append(enhanced_result)
        
        if self.verbose and len(enhanced_results) > len(base_results):
            added = len(enhanced_results) - len(base_results)
            print(f"🔗 Added {added} graph-related paragraphs")
        
        return enhanced_results
    
    def _extract_paragraph_id(self, result: Dict) -> Optional[str]:
        """Extract paragraph ID from search result"""
        
        for field in ['paragraph', 'chunk_id', 'id', 'reference']:
            if field in result:
                value = result[field]
                if isinstance(value, str) and value.startswith('§'):
                    return value
        
        return None
    
    def get_available_graphs(self) -> List[str]:
        """Get list of available law graphs"""
        return list(self.graphs.keys())


# Convenience function for JAILA integration
def get_graph_retriever(graph_storage_dir: str = "graphs") -> GraphRetriever:
    """Get a configured GraphRetriever instance"""
    return GraphRetriever(graph_storage_dir=graph_storage_dir)

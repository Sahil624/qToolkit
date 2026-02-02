"""
Graph RAG Module

NetworkX-based knowledge graph for enhanced Tutor retrieval.
Provides entity-relationship context through local neighborhood traversal
that complements vector-based retrieval.
"""
import os
import pickle
from typing import List, Dict, Tuple, Optional, Set

import networkx as nx

from .llm_client import OllamaClient, extract_triples, Triple


class GraphRAG:
    """
    Knowledge graph for Tutor-level retrieval using NetworkX.
    
    Stores entities and relationships extracted from course content,
    enabling local neighborhood search for richer context.
    
    Attributes:
        graph: NetworkX directed graph
        graph_path: Path to serialized graph file
        entity_index: Mapping of normalized entity names to node IDs
        client: OllamaClient for LLM calls
    """
    
    def __init__(
        self,
        graph_path: str,
        ollama_base_url: str = None,
        llm_model: str = "llama3.1:8b"
    ):
        """
        Initializes the GraphRAG.
        
        Args:
            graph_path: Path to store/load the graph file
            ollama_base_url: Ollama API base URL
            llm_model: Model for entity extraction
        """
        self.graph_path = graph_path
        self.graph = nx.DiGraph()
        self.entity_index: Dict[str, str] = {}  # normalized_name -> node_id
        
        self.client = OllamaClient(
            base_url=ollama_base_url,
            model=llm_model
        )
        
        # Try to load existing graph
        self._load()
    
    def _normalize_entity(self, entity: str) -> str:
        """Normalizes entity name for consistent matching."""
        return entity.lower().strip()
    
    def _load(self):
        """Loads the graph from disk if it exists."""
        if os.path.exists(self.graph_path):
            try:
                with open(self.graph_path, 'rb') as f:
                    data = pickle.load(f)
                    self.graph = data.get('graph', nx.DiGraph())
                    self.entity_index = data.get('entity_index', {})
                print(f"GraphRAG loaded: {self.graph.number_of_nodes()} nodes, {self.graph.number_of_edges()} edges")
            except Exception as e:
                print(f"Error loading graph: {e}")
                self.graph = nx.DiGraph()
                self.entity_index = {}
    
    def save(self):
        """Saves the graph to disk."""
        os.makedirs(os.path.dirname(self.graph_path), exist_ok=True)
        with open(self.graph_path, 'wb') as f:
            pickle.dump({
                'graph': self.graph,
                'entity_index': self.entity_index
            }, f)
        print(f"GraphRAG saved: {self.graph.number_of_nodes()} nodes, {self.graph.number_of_edges()} edges")
    
    def extract_triples_from_content(self, content: str) -> List[Tuple[str, str, str]]:
        """
        Extracts entity-relationship triples from content using LLM.
        
        Uses structured output via Pydantic models.
        
        Args:
            content: Text content to extract from
            
        Returns:
            List of (subject, predicate, object) tuples
        """
        triples: List[Triple] = extract_triples(content, self.client)
        return [(t.subject, t.predicate, t.object) for t in triples]
    
    def add_triple(self, subject: str, predicate: str, obj: str, source: str = None):
        """
        Adds a triple to the graph.
        
        Args:
            subject: Subject entity
            predicate: Relationship type
            obj: Object entity
            source: Optional source document identifier
        """
        subj_norm = self._normalize_entity(subject)
        obj_norm = self._normalize_entity(obj)
        
        # Add nodes if not exist
        if subj_norm not in self.entity_index:
            node_id = f"e_{len(self.entity_index)}"
            self.entity_index[subj_norm] = node_id
            self.graph.add_node(node_id, name=subject, normalized=subj_norm)
        
        if obj_norm not in self.entity_index:
            node_id = f"e_{len(self.entity_index)}"
            self.entity_index[obj_norm] = node_id
            self.graph.add_node(node_id, name=obj, normalized=obj_norm)
        
        # Add edge
        subj_id = self.entity_index[subj_norm]
        obj_id = self.entity_index[obj_norm]
        
        edge_data = {'relation': predicate}
        if source:
            edge_data['source'] = source
            
        self.graph.add_edge(subj_id, obj_id, **edge_data)
    
    def build_from_corpus(self, corpus: List[Dict], progress_callback=None):
        """
        Builds the graph from a corpus of documents.
        
        Args:
            corpus: List of dicts with 'content' and optional 'source' keys
            progress_callback: Optional callback(current, total) for progress
        """
        total = len(corpus)
        for i, doc in enumerate(corpus):
            content = doc.get('content', '')
            source = doc.get('source', f'doc_{i}')
            
            if len(content) < 50:
                continue
            
            triples = self.extract_triples_from_content(content)
            for s, p, o in triples:
                self.add_triple(s, p, o, source)
            
            if progress_callback:
                progress_callback(i + 1, total)
            
            print(f"Processed {i+1}/{total}: extracted {len(triples)} triples")
        
        self.save()
        print(f"Graph built: {self.graph.number_of_nodes()} nodes, {self.graph.number_of_edges()} edges")
    
    def find_entity(self, query: str) -> Optional[str]:
        """
        Finds an entity node matching the query.
        
        Args:
            query: Search term
            
        Returns:
            Node ID if found, None otherwise
        """
        query_norm = self._normalize_entity(query)
        
        # Exact match
        if query_norm in self.entity_index:
            return self.entity_index[query_norm]
        
        # Partial match
        for entity, node_id in self.entity_index.items():
            if query_norm in entity or entity in query_norm:
                return node_id
        
        return None
    
    def local_search(self, query: str, hops: int = 2) -> str:
        """
        Performs local neighborhood search around a query entity.
        
        Args:
            query: Entity or concept to search for
            hops: Number of hops to traverse (default 2)
            
        Returns:
            Formatted string of graph context
        """
        # Try to find entity in graph
        node_id = self.find_entity(query)
        
        if node_id is None:
            # Try keywords from query
            words = query.lower().split()
            for word in words:
                if len(word) > 3:
                    node_id = self.find_entity(word)
                    if node_id:
                        break
        
        if node_id is None:
            return ""
        
        # Get neighborhood
        try:
            neighbors = nx.single_source_shortest_path_length(
                self.graph, node_id, cutoff=hops
            )
        except nx.NetworkXError:
            neighbors = {node_id: 0}
        
        # Also include incoming edges (reverse direction)
        try:
            reverse_neighbors = nx.single_source_shortest_path_length(
                self.graph.reverse(), node_id, cutoff=hops
            )
            neighbors.update(reverse_neighbors)
        except nx.NetworkXError:
            pass
        
        # Format context
        context_parts = []
        seen_triples: Set[Tuple] = set()
        
        for neighbor_id in neighbors:
            node_data = self.graph.nodes.get(neighbor_id, {})
            entity_name = node_data.get('name', neighbor_id)
            
            # Outgoing edges
            for _, target, edge_data in self.graph.out_edges(neighbor_id, data=True):
                target_name = self.graph.nodes.get(target, {}).get('name', target)
                relation = edge_data.get('relation', 'relates_to')
                triple = (entity_name, relation, target_name)
                if triple not in seen_triples:
                    seen_triples.add(triple)
                    context_parts.append(f"- {entity_name} {relation} {target_name}")
            
            # Incoming edges
            for source, _, edge_data in self.graph.in_edges(neighbor_id, data=True):
                source_name = self.graph.nodes.get(source, {}).get('name', source)
                relation = edge_data.get('relation', 'relates_to')
                triple = (source_name, relation, entity_name)
                if triple not in seen_triples:
                    seen_triples.add(triple)
                    context_parts.append(f"- {source_name} {relation} {entity_name}")
        
        if context_parts:
            return "KNOWLEDGE GRAPH CONTEXT:\n" + "\n".join(context_parts[:15])
        return ""
    
    def is_empty(self) -> bool:
        """Returns True if the graph has no nodes."""
        return self.graph.number_of_nodes() == 0

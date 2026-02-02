"""
Hybrid Retriever Module

Combines BM25 keyword search with FAISS dense vector search using
Reciprocal Rank Fusion (RRF) for improved retrieval accuracy.

This addresses the limitation of pure semantic search missing exact
term matches (e.g., "Bell State" queries).
"""
from typing import List, Dict, Tuple, Union
import numpy as np

from rank_bm25 import BM25Okapi


class HybridRetriever:
    """
    Combines BM25 keyword search with dense vector search using RRF fusion.
    
    The hybrid approach improves accuracy for:
    - Exact term matching (BM25 strength)
    - Semantic similarity (Dense vector strength)
    
    Attributes:
        bm25: BM25Okapi index for keyword search
        corpus: List of document texts
        metadata_keys: List of metadata index keys (for mapping back to VectorDBManager)
        bm25_weight: Weight for BM25 scores in fusion (default 0.5)
        rrf_k: RRF constant (default 60, standard value)
    """
    
    def __init__(
        self, 
        corpus: List[str], 
        metadata_keys: List[int],
        bm25_weight: float = 0.5,
        rrf_k: int = 60
    ):
        """
        Initializes the HybridRetriever with BM25 index.
        
        Args:
            corpus: List of document texts to index
            metadata_keys: Corresponding metadata index keys from VectorDBManager
            bm25_weight: Weight for BM25 in fusion (0.0 to 1.0)
            rrf_k: RRF constant for rank fusion
        """
        self.corpus = corpus
        self.metadata_keys = metadata_keys
        self.bm25_weight = bm25_weight
        self.rrf_k = rrf_k
        
        # Tokenize corpus for BM25
        tokenized_corpus = [self._tokenize(doc) for doc in corpus]
        self.bm25 = BM25Okapi(tokenized_corpus)
        
        print(f"HybridRetriever initialized with {len(corpus)} documents, BM25 weight={bm25_weight}")
    
    def _tokenize(self, text: str) -> List[str]:
        """Simple whitespace tokenization with lowercasing."""
        return text.lower().split()
    
    def _bm25_search(self, query: str, top_k: int = 20) -> List[Tuple[int, float]]:
        """
        Performs BM25 keyword search.
        
        Returns:
            List of (metadata_key, score) tuples sorted by score descending
        """
        tokenized_query = self._tokenize(query)
        scores = self.bm25.get_scores(tokenized_query)
        
        # Get top-k indices and scores
        top_indices = np.argsort(scores)[::-1][:top_k]
        
        results = []
        for idx in top_indices:
            if scores[idx] > 0:  # Only include non-zero scores
                results.append((self.metadata_keys[idx], float(scores[idx])))
        
        return results
    
    def _rrf_fusion(
        self, 
        bm25_results: List[Tuple[int, float]], 
        dense_results: List[Tuple[int, float]]
    ) -> List[Tuple[int, float]]:
        """
        Combines rankings using Reciprocal Rank Fusion (RRF).
        
        RRF Score = sum(1 / (k + rank)) across all ranking lists
        
        Args:
            bm25_results: BM25 results as (metadata_key, score) tuples
            dense_results: Dense search results as (metadata_key, score) tuples
            
        Returns:
            Fused results sorted by combined RRF score
        """
        rrf_scores: Dict[int, float] = {}
        
        # Add BM25 RRF scores (weighted)
        for rank, (key, _) in enumerate(bm25_results):
            rrf_score = self.bm25_weight * (1.0 / (self.rrf_k + rank + 1))
            rrf_scores[key] = rrf_scores.get(key, 0) + rrf_score
        
        # Add dense search RRF scores (weighted by complement)
        dense_weight = 1.0 - self.bm25_weight
        for rank, (key, _) in enumerate(dense_results):
            rrf_score = dense_weight * (1.0 / (self.rrf_k + rank + 1))
            rrf_scores[key] = rrf_scores.get(key, 0) + rrf_score
        
        # Sort by fused score
        fused_results = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
        return fused_results
    
    def hybrid_search(
        self, 
        query: str, 
        num_results: int,
        lo_ids: Union[List[str], None],
        db_manager
    ) -> List[str]:
        """
        Performs hybrid search combining BM25 and dense vector search.
        
        Args:
            query: User query string
            num_results: Number of results to return
            lo_ids: Learning object IDs for filtering (None = no filter)
            db_manager: VectorDBManager instance for dense search and metadata access
            
        Returns:
            List of document content strings
        """
        # 1. BM25 keyword search
        bm25_results = self._bm25_search(query, top_k=num_results * 5)
        
        # 2. Dense vector search via VectorDBManager
        dense_results = self._dense_search(query, num_results * 5, db_manager)
        
        # 3. RRF fusion
        fused_results = self._rrf_fusion(bm25_results, dense_results)
        
        # 4. Filter by LO IDs and return content
        filtered_results = []
        for key, score in fused_results:
            if key not in db_manager.metadata:
                continue
                
            meta = db_manager.metadata[key]
            
            # Apply LO filter if specified
            if lo_ids is not None:
                lo_list = [lo.get('lo_id') for lo in meta.get('learning_objectives', [])]
                if not any(lo_id in lo_list for lo_id in lo_ids):
                    continue
            
            filtered_results.append(meta["content"])
            
            if len(filtered_results) >= num_results:
                break
        
        return filtered_results
    
    def _dense_search(
        self, 
        query: str, 
        top_k: int, 
        db_manager
    ) -> List[Tuple[int, float]]:
        """
        Performs dense vector search using VectorDBManager's FAISS index.
        
        Returns:
            List of (metadata_key, distance) tuples
        """
        if db_manager.index.ntotal == 0:
            return []
        
        query_vector = db_manager._get_ollama_embedding(query)
        if query_vector is None:
            return []
        
        # Search FAISS index
        search_k = min(top_k, db_manager.index.ntotal)
        distances, indices = db_manager.index.search(
            np.array(query_vector, dtype=np.float32), 
            k=search_k
        )
        
        # Convert to (metadata_key, distance) tuples
        # Lower distance = better match, so we use 1/(1+distance) for scoring
        results = []
        for i, idx in enumerate(indices[0]):
            if idx in db_manager.metadata:
                # Convert distance to similarity-like score
                score = 1.0 / (1.0 + distances[0][i])
                results.append((idx, score))
        
        return results

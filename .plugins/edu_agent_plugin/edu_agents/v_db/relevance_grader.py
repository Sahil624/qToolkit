"""
Relevance Grader Module

Lightweight LLM-based relevance assessment for Active RAG routing.
Determines if retrieved documents are relevant to the user query,
enabling automatic escalation to Tutor when confidence is low.
"""
from typing import List, Dict

from .llm_client import OllamaClient, grade_relevance, RelevanceGrade


class RelevanceGrader:
    """
    Assesses relevance of retrieved documents to a query using LLM.
    
    Used in Active RAG to decide whether to:
    - Proceed with Peer Agent response (relevant)
    - Escalate to Tutor Agent (not relevant)
    
    Attributes:
        client: OllamaClient instance for LLM calls
        relevance_threshold: Minimum confidence for "relevant" (default 0.6)
    """
    
    def __init__(
        self,
        ollama_base_url: str = None,
        model: str = "llama3.1:8b",
        relevance_threshold: float = 0.6
    ):
        """
        Initializes the RelevanceGrader.
        
        Args:
            ollama_base_url: Base URL for Ollama API
            model: LLM model to use for grading
            relevance_threshold: Confidence threshold for relevance
        """
        self.client = OllamaClient(
            base_url=ollama_base_url,
            model=model
        )
        self.relevance_threshold = relevance_threshold
    
    def grade(self, query: str, docs: List[str]) -> Dict[str, any]:
        """
        Grades the relevance of retrieved documents to the query.
        
        Args:
            query: User's question
            docs: List of retrieved document texts
            
        Returns:
            Dict with:
                - "relevant": bool indicating if docs are relevant
                - "confidence": float confidence score (0.0 to 1.0)
                - "reason": str explaining the grade
        """
        result: RelevanceGrade = grade_relevance(query, docs, self.client)
        
        return {
            "relevant": result.relevant,
            "confidence": result.confidence,
            "reason": result.reason
        }

from typing import Union
import requests
import json
import os
import ipywidgets as widgets
from functools import lru_cache
from IPython.display import display, Markdown
from pydantic import BaseModel, Field

from .vector_db_manager import VectorDBManager, get_db_manager_instance
from .relevance_grader import RelevanceGrader
from .graph_rag import GraphRAG
from .llm_client import OllamaClient
from ..prompt import get_rewrite_prompt, format_chat_history

class ChainOfThoughtResponse(BaseModel):
    thoughts: str = Field(description="Thoughts on user query")
    answer: str = Field(description="Final answer")

class PeerAgent:
    """
    The backend "brain" for the Student Peer agent. It handles RAG searches
    and communication with an LLM via Ollama.
    """
    def __init__(self, 
                 db_path: str,
                 ollama_embed_model: str = 'nomic-embed-text',
                 ollama_chat_model: str = 'llama3.1:8b',
                 ollama_base_url: str = os.getenv("OLLAMA_API_URL", "http://localhost:11434")):
        """Initializes the PeerAgent's backend."""
        self.db_manager = get_db_manager_instance()
        self.ollama_chat_model = ollama_chat_model
        self.ollama_base_url = ollama_base_url
        
        # Common LLM client for all generation calls
        self.llm_client = OllamaClient(
            base_url=ollama_base_url,
            model=ollama_chat_model
        )
        
        # Active RAG: Relevance grader for escalation decisions
        self.relevance_grader = RelevanceGrader(
            ollama_base_url=ollama_base_url,
            model=ollama_chat_model
        )
        
        # GraphRAG for Tutor-level retrieval (lazy initialization)
        self._graph_rag = None
        self._graph_path = os.path.join(self.db_manager.db_path, "knowledge_graph.pkl")

    def _call_ollama_llm(self, prompt: str, system_prompt: str = None, expected_structure: BaseModel = None) -> str:
        """
        Calls the Ollama API to get a response from the chat model.
        
        Args:
            prompt: The user message/question
            system_prompt: Optional system instructions for the model
        """
        try:
            return self.llm_client.generate(prompt, system_prompt=system_prompt, expected_structure=expected_structure)
        except Exception as e:
            error_message = f"Error calling Ollama API: {e}. Please ensure Ollama is running and the model '{self.ollama_chat_model}' is pulled."
            print(error_message)
            return error_message, None    

    @lru_cache(maxsize=128)
    def _cached_llm_rewrite(self, rewrite_prompt: str) -> str:
        return self._call_ollama_llm(rewrite_prompt)

    def get_rewritten_query(self, query: str, chat_history: list) -> str:
        # If we have history, the user might be saying "it" or "that".
        # We need to rewrite the query to be standalone for the vector search.
        # We cache based on the prompt to avoid redundant calls.
        
        # print(f"Contextualizing query: '{query}'...")
        rewrite_prompt = get_rewrite_prompt(query, chat_history)
        
        rewritten, meta_info = self._cached_llm_rewrite(rewrite_prompt)
        
        # Basic cleanup in case the model is chatty
        clean_rewritten = rewritten.strip().replace("\"", "")
        if clean_rewritten and len(clean_rewritten) < 200: # Sanity check length
            # print(f"Rewrote query for search: '{clean_rewritten}'")
            return clean_rewritten
        return query

    def answer_question(self, query: str, persona_prompt: str, completed_lo_ids: Union[list, None] = None, chat_history = [], skip_grading: bool = False) -> dict:
        """
        Answers a student's question using the RAG pipeline.
        
        Args:
            query: User's question
            persona_prompt: The persona prompt for the agent
            completed_lo_ids: LO IDs for filtering (None = no filter / Tutor mode)
            chat_history: Previous conversation messages
            skip_grading: If True, skip relevance grading (used for Tutor)
        
        Returns:
            dict with:
                - "answer": The generated response string
                - "escalate": Boolean flag indicating Tutor escalation needed
        """
        original_query = query
        
        if chat_history:
            query = self.get_rewritten_query(query, chat_history)

        is_peer = completed_lo_ids is not None

        context_chunks = self.db_manager.filter_with_lo_ids(
            query=query, lo_ids=completed_lo_ids, num_results=2
        )
        context_str = "\n\n".join(context_chunks)
        
        # Handle no context case
        if not context_str:
            print("No context found for the query in the vector database.")
            return {
                "answer": "I couldn't find anything specific about that in my notes. Let me ask the Tutor to help!",
                "escalate": True
            }
        
        # Active RAG: Grade relevance (only for Peer, skip for Tutor)
        if not skip_grading and is_peer:
            grade_result = self.relevance_grader.grade(original_query, context_chunks)
            print(f"Relevance grade: {grade_result}")
            
            if not grade_result["relevant"]:
                return {
                    "answer": "Hmm, I'm not finding great info on that in my notes. Let me get the Tutor to help with this!",
                    "escalate": True
                }
        # For Tutor mode (skip_grading=True), add graph context if available
        graph_context = ""
        if skip_grading and self._graph_rag is None:
            # Lazy init GraphRAG for Tutor
            self._graph_rag = GraphRAG(
                graph_path=self._graph_path,
                ollama_base_url=self.ollama_base_url,
                llm_model=self.ollama_chat_model
            )
        
        if skip_grading and self._graph_rag and not self._graph_rag.is_empty():
            graph_context = self._graph_rag.local_search(query, hops=2)
            if graph_context:
                print(f"GraphRAG context found for Tutor")

        # Build the system prompt (persona + instructions)
        system_prompt = persona_prompt
        
        # Build the user message (context + question)
        user_message = f"""### COURSE NOTES (Source Material)
---
{context_str}
---
"""

        # Add graph context for Tutor
        if graph_context:
            user_message += f"""
### ADDITIONAL CONTEXT (Knowledge Graph)
---
{graph_context}
---
"""

        # SANDWICH METHOD: Unified for BOTH Peer (Study Buddy) and Tutor (Expert)
        # We put critical reminders at the END to prevent context collapse.
        user_message += f"""
### STUDENT'S QUESTION
[QUESTION]: "{query}"

### CRITICAL REMINDERS (Follow these!)
- Do NOT repeat the student's question back to them.
- Answer using ONLY the Course Notes/Context above.
- Use the THOUGHT/ANSWER format from the system prompt.
"""
        
        # Unified Call: Both agents now use the structured ChainOfThoughtResponse
        raw_answer, meta_info = self._call_ollama_llm(user_message, system_prompt, ChainOfThoughtResponse)
        
        # Parse CoT response (extract ANSWER section)
        answer = self._parse_cot_response(raw_answer)
            
        return {"answer": answer, "escalate": False, "meta_info": meta_info}
    
    def _parse_cot_response(self, raw: ChainOfThoughtResponse) -> str:
        if not isinstance(raw, ChainOfThoughtResponse):
            print(f"Expected ChainOfThoughtResponse, recieved {type(raw)}. Value : {raw}")
            return str(raw)
        print(f"Thought behind answer", raw.thoughts)

        return raw.answer

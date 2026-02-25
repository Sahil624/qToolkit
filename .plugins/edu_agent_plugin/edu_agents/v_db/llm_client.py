"""
LLM Client Module

Unified LLM client with structured output support.

By default this talks to a **local Ollama** instance, but it can also
use any **OpenAI-compatible API** (OpenAI, Gemini, Anthropic via a
gateway, etc.) based on environment variables. The same environment
variables are shared with q-sim so users can configure the LLM in one
place.

Environment variables (shared with q-sim):

- LLM_PROVIDER (or provider)      – "ollama" (default), "openai", "gemini", "anthropic", ...
- LLM_MODEL   (or model)         – model name/tag (default: "llama3.1:8b")
- LLM_BASE_URL (or base_url)     – API base URL
    - Ollama default:   http://localhost:11434  (native Ollama API)
    - OpenAI default:   https://api.openai.com/v1
- OPENAI_API_KEY                 – API key for OpenAI-compatible endpoints
- OLLAMA_API_URL                 – Backwards-compatible base URL for Ollama (if set)
"""
import os
import json
import requests
from typing import List, Optional, Type, TypeVar, Union, Dict
from pydantic import BaseModel, Field
import ollama

# Generic type for Pydantic models
T = TypeVar('T', bound=BaseModel)


# ============================================================
# Pydantic Response Models
# ============================================================

class RelevanceGrade(BaseModel):
    """Structured response for relevance grading."""
    relevant: bool = Field(description="Whether the documents are relevant to the query")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score from 0.0 to 1.0")
    reason: str = Field(description="Brief explanation of the grading decision")


class Triple(BaseModel):
    """A single knowledge graph triple."""
    subject: str = Field(description="The subject entity")
    predicate: str = Field(description="The relationship/predicate")
    object: str = Field(description="The object entity")


class TripleExtraction(BaseModel):
    """Structured response for triple extraction."""
    triples: List[Triple] = Field(default_factory=list, description="List of extracted triples")


# ============================================================
# Prompt Templates
# ============================================================

RELEVANCE_GRADING_PROMPT = """You are a relevance grader. Assess if the retrieved documents contain information relevant to answering the user's question.

USER QUESTION: {query}

RETRIEVED DOCUMENTS:
---
{documents}
---

Respond with a JSON object containing:
- "relevant": true or false
- "confidence": a number between 0.0 and 1.0
- "reason": a brief explanation

JSON Response:"""


TRIPLE_EXTRACTION_PROMPT = """You are a knowledge graph extraction assistant. Extract entities and relationships from the following educational content.

CONTENT:
---
{content}
---

Extract key concepts and their relationships. Respond with a JSON object containing:
- "triples": an array of objects, each with "subject", "predicate", and "object" fields

Rules:
- Use lowercase for all entities
- Keep entity names concise (1-3 words)
- Use verb phrases for predicates (e.g., "applies_to", "creates", "is_type_of")
- Extract 3-8 triples

JSON Response:"""


# ============================================================
# LLM Client Class
# ============================================================

class OllamaClient:
    """
    Unified LLM client with structured output support.
    
    By default this uses a local Ollama instance, but it can also talk
    to any OpenAI-compatible API (OpenAI, Gemini, Anthropic via a
    gateway, etc.) based on environment variables.
    
    Attributes:
        provider: Backend provider ("ollama" by default)
        base_url: API base URL
        model: Default model name
        timeout: Request timeout in seconds
    """
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        model: str = "llama3.1:8b",
        timeout: int = 60,
        provider: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        """
        Initializes the LLM client.
        
        Args:
            base_url: API base URL. If omitted, derived from env and provider.
            model: Default model to use (chat model name / tag).
            timeout: Request timeout in seconds.
            provider: Optional explicit provider override.
            api_key: Optional explicit API key for OpenAI-compatible endpoints.
        """
        # Resolve provider and core config from environment with sensible defaults.
        env_provider = os.getenv("LLM_PROVIDER") or os.getenv("provider")
        self.provider = (provider or env_provider or "ollama").lower()

        env_model = os.getenv("LLM_MODEL") or os.getenv("model")
        self.model = env_model or model or "llama3.1:8b"

        # Shared API key for OpenAI-compatible backends
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")

        # Base URL resolution:
        # - For Ollama, prefer LLM_BASE_URL/base_url, then OLLAMA_API_URL, then localhost.
        # - For non-Ollama, default to OpenAI's public endpoint.
        env_base_url = os.getenv("LLM_BASE_URL") or os.getenv("base_url")
        if self.provider == "ollama":
            raw_base = base_url or env_base_url or os.getenv("OLLAMA_API_URL", "http://localhost:11434")
            # Native Ollama API (we add /api/chat ourselves)
            self.base_url = raw_base.rstrip("/")
            self.chat_url = f"{self.base_url}/api/chat"
            self.ollama = ollama.Client(host=self.base_url)
        else:
            # OpenAI-compatible chat-completions endpoint
            raw_base = base_url or env_base_url or "https://api.openai.com/v1"
            self.base_url = raw_base.rstrip("/")
            self.chat_url = f"{self.base_url}/chat/completions"
            self.ollama = None

        self.timeout = timeout
    
    def generate(self, prompt: str, model: str = None, system_prompt: str = None, expected_structure: Optional[BaseModel] = None) -> Union[str, BaseModel]:
        """
        Generates a text response from the LLM using the chat API.
        
        Uses /api/chat with proper message roles to ensure the model
        correctly interprets system instructions vs user messages.
        
        Args:
            prompt: The user prompt to send
            model: Optional model override
            system_prompt: Optional system prompt (if None, prompt is treated as user message only)
            
        Returns:
            Raw response text
        """
        messages: List[Dict] = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        answer = self.generate_chat(messages, model=model, expected_structure=expected_structure)
        return answer, {
            'messages': messages,
            'raw_answer': answer.model_dump_json() if isinstance(answer, BaseModel) else answer,
        }
    
    def _generate_chat_ollama(
        self,
        messages: List[Dict],
        model: Optional[str] = None,
        expected_structure: Optional[BaseModel] = None,
    ) -> Union[str, BaseModel]:
        """Generate a response using native Ollama HTTP or structured chat."""
        payload = {
            "model": model or self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "repeat_penalty": 1.15,  # Prevent question echoing on 8B models
            }
        }
        
        try:
            if expected_structure:
                return self.generate_structured(messages, expected_structure)

            response = requests.post(
                self.chat_url, 
                json=payload, 
                timeout=self.timeout
            )
            response.raise_for_status()
            result = response.json()
            # Chat API returns response in message.content
            return result.get("message", {}).get("content", "")
        except requests.exceptions.RequestException as e:
            print(f"OllamaClient error: {e}")
            raise e

    def _generate_chat_openai_compatible(
        self,
        messages: List[Dict],
        model: Optional[str] = None,
        expected_structure: Optional[BaseModel] = None,
    ) -> Union[str, BaseModel]:
        """Generate a response using an OpenAI-compatible chat-completions endpoint."""
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY must be set to use non-Ollama providers.")

        payload: Dict[str, any] = {
            "model": model or self.model,
            "messages": messages,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.post(
                self.chat_url,
                json=payload,
                headers=headers,
                timeout=self.timeout,
            )
            response.raise_for_status()
            result = response.json()
            content = result["choices"][0]["message"]["content"]

            if expected_structure:
                # Ask the model to return strictly JSON and validate it.
                json_text = self._extract_json(content)
                return expected_structure.model_validate_json(json_text)

            return content
        except requests.exceptions.RequestException as e:
            print(f"LLM client HTTP error: {e}")
            raise e

    def generate_chat(
        self,
        messages: List[Dict],
        model: Optional[str] = None,
        expected_structure: Optional[BaseModel] = None
    ) -> Union[str, BaseModel]:
        """
        Generates a response using the chat API with explicit message roles.
        
        Args:
            messages: List of message dicts with 'role' and 'content' keys.
                      Roles can be 'system', 'user', or 'assistant'.
            model: Optional model override
            expected_structure: Optional Pydantic model for structured output
            
        Returns:
            Raw response text or a validated Pydantic model.
        """
        if self.provider == "ollama":
            return self._generate_chat_ollama(messages, model=model, expected_structure=expected_structure)
        else:
            return self._generate_chat_openai_compatible(messages, model=model, expected_structure=expected_structure)
    
    def generate_structured(
        self, 
        prompt: Union[str, List[Dict]], 
        response_model: Type[T],
    ) -> T:
        """
        Generates a structured response validated against a Pydantic model.
        
        Args:
            prompt: The prompt (should request JSON output)
            response_model: Pydantic model class for validation
            
        Returns:
            Validated Pydantic model instance
            
        Raises:
            ValueError: If response cannot be parsed as valid JSON
            ValidationError: If response doesn't match the schema
        """

        messages = []

        if isinstance(prompt, str):
            messages = [
                {"role": "user", "content": prompt}
            ]
        else:
            messages = prompt

        # Ollama supports JSON schema natively via `format=...`.
        if self.provider == "ollama":
            response = self.ollama.chat(
                model=self.model,
                messages=messages,
                format=response_model.model_json_schema()
            )

            try:
                return response_model.model_validate_json(response.message.content)
            except Exception as e:
                print("==== Exception While parsing structured response", e)
                print("=== Raw Response", response.message.content)
                raise e

        # OpenAI-compatible: instruct model to return JSON and validate.
        schema = response_model.model_json_schema()
        schema_text = json.dumps(schema, indent=2)

        if messages:
            # Append explicit JSON-only instruction to the last user message.
            messages = list(messages)
            last = messages[-1].copy()
            last["content"] = (
                f"{last['content']}\n\n"
                "You MUST respond with ONLY JSON that matches this Pydantic schema:\n"
                f"{schema_text}\n"
            )
            messages[-1] = last

        raw = self._generate_chat_openai_compatible(messages, model=self.model, expected_structure=None)

        try:
            json_text = self._extract_json(raw)
            return response_model.model_validate_json(json_text)
        except Exception as e:
            print("==== Exception While parsing structured response", e)
            print("=== Raw Response", raw)
            raise e
    
    def _extract_json(self, text: str) -> str:
        """
        Extracts JSON object or array from LLM response text.
        
        Handles cases where LLM includes extra text around JSON.
        """
        import json
        
        text = text.strip()
        
        # Try direct parse first
        try:
            json.loads(text)
            return text
        except json.JSONDecodeError:
            pass
        
        # Find JSON object boundaries
        start_brace = text.find('{')
        start_bracket = text.find('[')
        
        if start_brace == -1 and start_bracket == -1:
            raise ValueError(f"No JSON found in response: {text[:100]}")
        
        # Determine which comes first
        if start_brace == -1:
            start = start_bracket
            end_char = ']'
        elif start_bracket == -1:
            start = start_brace
            end_char = '}'
        else:
            start = min(start_brace, start_bracket)
            end_char = '}' if start == start_brace else ']'
        
        # Find matching end
        depth = 0
        for i, char in enumerate(text[start:], start):
            if char in '{[':
                depth += 1
            elif char in '}]':
                depth -= 1
                if depth == 0:
                    return text[start:i+1]
        
        raise ValueError(f"Incomplete JSON in response: {text[:100]}")


# ============================================================
# Convenience Functions
# ============================================================

_default_client: Optional[OllamaClient] = None


def get_llm_client(**kwargs) -> OllamaClient:
    """
    Gets or creates a default OllamaClient instance.
    
    Uses singleton pattern for efficiency.
    """
    global _default_client
    if _default_client is None or kwargs:
        _default_client = OllamaClient(**kwargs)
    return _default_client


def grade_relevance(
    query: str, 
    documents: List[str],
    client: OllamaClient = None
) -> RelevanceGrade:
    """
    Convenience function to grade document relevance.
    
    Args:
        query: User's question
        documents: List of retrieved documents
        client: Optional OllamaClient instance
        
    Returns:
        RelevanceGrade with relevant, confidence, and reason fields
    """
    client = client or get_llm_client()
    
    # Handle edge cases with heuristics
    if not documents or all(not doc.strip() for doc in documents):
        return RelevanceGrade(
            relevant=False,
            confidence=0.0,
            reason="No documents retrieved"
        )
    
    combined_docs = "\n\n".join(documents)
    if len(combined_docs) < 50:
        return RelevanceGrade(
            relevant=False,
            confidence=0.2,
            reason="Retrieved content too short"
        )
    
    prompt = RELEVANCE_GRADING_PROMPT.format(
        query=query,
        documents=combined_docs[:2000]
    )
    
    try:
        return client.generate_structured(prompt, RelevanceGrade)
    except Exception as e:
        print(f"Relevance grading error: {e}")
        # Default to relevant on error to avoid blocking
        return RelevanceGrade(
            relevant=True,
            confidence=0.5,
            reason=f"Grading error, defaulting to relevant: {str(e)}"
        )


def extract_triples(
    content: str,
    client: OllamaClient = None
) -> List[Triple]:
    """
    Convenience function to extract knowledge graph triples.
    
    Args:
        content: Text content to extract from
        client: Optional OllamaClient instance
        
    Returns:
        List of Triple objects
    """
    client = client or get_llm_client()
    
    if len(content) < 50:
        return []
    
    prompt = TRIPLE_EXTRACTION_PROMPT.format(content=content[:3000])
    
    try:
        result = client.generate_structured(prompt, TripleExtraction)
        return result.triples
    except Exception as e:
        print(f"Triple extraction error: {e}")
        return []

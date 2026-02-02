"""
Common Utilities for Agent Evaluation

This module provides shared functions for LLM initialization, embeddings,
and utility functions used across the test framework.
"""
from typing import Dict, Any, List
from datetime import datetime

# LangChain imports for LLM configuration
from langchain_openai import ChatOpenAI
from langchain_core.embeddings import Embeddings

from openai import OpenAI, AsyncOpenAI

# RAGAS wrappers
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper, OpenAIEmbeddings
from ragas.llms import llm_factory
from ragas.cache import DiskCacheBackend


def get_eval_llm(config: Dict[str, Any]):
    """
    Creates a RAGAS-compatible LLM using llm_factory for v0.4 compatibility.
    Supports: ollama, openai, gemini, anthropic
    
    Args:
        config: Configuration dict with keys:
            - provider: 'ollama', 'openai', 'gemini', or 'anthropic'
            - model: Model name
            - base_url: Base URL for API
            - openai_api_key, google_api_key, anthropic_api_key: API keys
    
    Returns:
        InstructorLLM instance (required by ragas.metrics.collections)
    """
    provider = config.get("provider", "ollama")
    model = config.get("model", "llama3.1:8b")
    base_url = config.get("base_url", "http://localhost:11434/v1")

    use_cache = config.get("use_cache", False)
    
    cache_backend = DiskCacheBackend() if use_cache else None

    if provider == "ollama":
        client = AsyncOpenAI(
            base_url=base_url,
            api_key="ollama",  # Ollama doesn't need a real key
        )
        return llm_factory(
            model=model,
            client=client,
            temperature=0,
            max_tokens=8192,  # Increase for RAGAS structured output
            cache=cache_backend,
        )
    elif provider == "openai":
        client = AsyncOpenAI(
            api_key=config.get("openai_api_key"),
        )
        return llm_factory(
            model=model,
            client=client,
            temperature=0,
            cache=cache_backend,
        )
    elif provider == "gemini":
        # This is not working as expected, this treats client as sync client instead of async client
        # from google import genai
        # # genai.Client supports async natively when used with llm_factory(provider="gemini")
        # client = genai.Client(api_key=config.get("google_api_key"))
        # return llm_factory(
        #     model=model,
        #     client=client,
        #     provider="gemini",
        #     cache=cache_backend,
        # )
        client = AsyncOpenAI(
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            api_key=config.get("google_api_key"),
        )
        return llm_factory(
            model=model,
            client=client,
            temperature=0,
            cache=cache_backend,
        )
    elif provider == "anthropic":
        from anthropic import AsyncAnthropic
        client = AsyncAnthropic(
            api_key=config.get("anthropic_api_key"),
        )
        return llm_factory(
            model=model,
            client=client,
            temperature=0,
            cache=cache_backend,
        )
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")


def get_eval_embeddings(config: Dict[str, Any]):
    """
    Creates embeddings model for RAGAS.
    Uses the same provider as the LLM.
    
    Args:
        config: Configuration dict with provider and API key info
    
    Returns:
        LangChain embeddings instance
    """
    provider = config.get("provider", "ollama")
    base_url: str = config.get("base_url", "http://localhost:11434/v1")
    
    cache_backend = DiskCacheBackend()

    if provider == "ollama":
        # Use AsyncOpenAI for async operations
        client = AsyncOpenAI(
            base_url=base_url,
            api_key="ollama",  # Ollama doesn't need a real key
        )
        embeddings = OpenAIEmbeddings(
            client=client,
            model="nomic-embed-text",
            cache=cache_backend,
        )

        return embeddings
    elif provider == "openai":
        return OpenAIEmbeddings(
            model="text-embedding-3-small",
            api_key=config.get("openai_api_key"),
        )
    elif provider == "gemini":
        from ragas.embeddings import GoogleEmbeddings
        embeddings = GoogleEmbeddings(model="gemini-embedding-001")
        return embeddings
    else:
        # Fall back to OpenAI embeddings for other providers
        # (or use the base_url if compatible)
        return OpenAIEmbeddings(
            model="text-embedding-3-small",
            base_url=base_url,
            api_key=config.get("openai_api_key") or config.get("google_api_key"),
        )


def get_ragas_llm_and_embeddings(config: Dict[str, Any]):
    """
    Creates RAGAS LLM and embeddings for v0.4.
    
    Args:
        config: LLM configuration dict
    
    Returns:
        Tuple of (ragas_llm, ragas_embeddings)
    """
    from ragas.llms.base import BaseRagasLLM, InstructorBaseRagasLLM
    from ragas.embeddings.base import BaseRagasEmbeddings
    
    llm = get_eval_llm(config)
    embeddings = get_eval_embeddings(config)
    
    # v0.4: llm_factory() returns InstructorLLM (inherits from InstructorBaseRagasLLM)
    # Check for both base classes
    if isinstance(llm, (BaseRagasLLM, InstructorBaseRagasLLM)):
        ragas_llm = llm  # Already RAGAS-compatible, don't wrap
    else:
        # Fallback for LangChain LLMs (shows deprecation warning)
        ragas_llm = LangchainLLMWrapper(llm)

    # Same for embeddings - check if already RAGAS-compatible
    if embeddings is None:
        ragas_embeddings = None
    elif isinstance(embeddings, BaseRagasEmbeddings):
        ragas_embeddings = embeddings  # Already RAGAS-compatible
    elif isinstance(embeddings, Embeddings):
        ragas_embeddings = LangchainEmbeddingsWrapper(embeddings)
    else:
        ragas_embeddings = embeddings
    
    return ragas_llm, ragas_embeddings


def parse_conversation_history(conversation_history: List[Dict]) -> List[Dict]:
    """
    Parse conversation history from YAML format to internal format.
    
    Input format:
        - user: "message"
        - agent: "message"
        - tutor: "message"
    
    Output format:
        [{"sender": "user"|"peer"|"tutor", "text": "message"}, ...]
    
    Args:
        conversation_history: List of dicts from YAML
    
    Returns:
        List of parsed message dicts
    """
    parsed = []
    for message in conversation_history:
        if message.get("user"):
            parsed.append({
                "sender": "user",
                "text": message["user"]
            })
        elif message.get("agent"):
            parsed.append({
                "sender": "peer",
                "text": message["agent"]
            })
        elif message.get("tutor"):
            parsed.append({
                "sender": "tutor",
                "text": message["tutor"]
            })
    return parsed


def format_timestamp(fmt: str = "%Y%m%d_%H%M%S") -> str:
    """
    Returns a formatted timestamp string.
    
    Args:
        fmt: strftime format string
    
    Returns:
        Formatted timestamp
    """
    return datetime.now().strftime(fmt)


def format_timestamp_readable(fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    Returns a human-readable formatted timestamp.
    
    Args:
        fmt: strftime format string
    
    Returns:
        Formatted timestamp
    """
    return datetime.now().strftime(fmt)


def interpret_score(score: float) -> str:
    """
    Interprets a score value into a human-readable category.
    
    Args:
        score: Float score between 0 and 1
    
    Returns:
        Category string: 'Excellent', 'Good', 'Needs Improvement', or 'Poor'
    """
    if score >= 0.9:
        return "Excellent"
    elif score >= 0.7:
        return "Good"
    elif score >= 0.5:
        return "Needs Improvement"
    else:
        return "Poor"

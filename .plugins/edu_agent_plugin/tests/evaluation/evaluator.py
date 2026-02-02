"""
RAGAS Evaluation Wrapper (v0.4)

This module wraps the RAGAS library to evaluate agent responses using
the new experiment-based architecture with ascore() API.

Supports both async and sync LLM clients by wrapping sync calls in asyncio.to_thread().
"""
import os
import asyncio
from functools import partial
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from pydantic import BaseModel

# RAGAS v0.4 imports - using collections for non-deprecated metrics
from ragas.metrics.collections import (
    Faithfulness,
    AnswerRelevancy,
    ContextPrecision,
    ContextRecall,
    AnswerCorrectness,
)

# Import common utilities
from .common import get_ragas_llm_and_embeddings
from .rate_limiter import RateLimiter, create_rate_limiter


@dataclass
class EvaluationResult:
    """Holds evaluation results for a single question."""
    question_id: str
    question: str
    agent_type: str  # 'peer' or 'tutor'
    answer: str
    contexts: List[str]
    reference_answer: Optional[str]
    faithfulness: float
    answer_relevancy: float
    context_precision: float
    context_recall: Optional[float]
    answer_correctness: Optional[float]
    meta_info: Optional[Dict]


class MetricScores(BaseModel):
    """Pydantic model for structured metric results."""
    faithfulness: float = 0.0
    answer_relevancy: float = 0.0
    context_precision: float = 0.0
    context_recall: Optional[float] = None
    answer_correctness: Optional[float] = None


async def _run_metric_score(metric, is_async: bool, rate_limiter: Optional[RateLimiter] = None, **kwargs) -> float:
    """
    Run a metric's score method, handling both async and sync clients.
    
    For sync clients, runs in a thread pool to avoid blocking.
    Applies rate limiting before each call.
    """
    try:
        # Apply rate limiting before API call
        if rate_limiter:
            await rate_limiter.acquire()
        
        if is_async:
            result = await metric.ascore(**kwargs)
        else:
            # Wrap sync call in thread pool to avoid "can't call sync from async" error
            result = await asyncio.to_thread(metric.score, **kwargs)
        return result.value if hasattr(result, 'value') else float(result)
    except Exception as e:
        print(f"{type(metric).__name__} scoring error: {e}")
        return 0.0


async def score_sample(
    sample: Dict[str, Any],
    llm,
    embeddings,
    has_reference: bool,
    rate_limiter: Optional[RateLimiter] = None,
) -> MetricScores:
    """
    Score a single sample using RAGAS metrics with v0.4 ascore() API.
    
    Supports both async and sync LLM clients.
    
    Args:
        sample: Dict with 'question', 'answer', 'contexts', and optionally 'reference'
        llm: RAGAS-compatible LLM (InstructorLLM)
        embeddings: RAGAS-compatible embeddings
        has_reference: Whether reference answers are available
        rate_limiter: Optional rate limiter for API calls
    
    Returns:
        MetricScores with all metric values
    """
    # Check if client supports async operations
    is_async = getattr(llm, "is_async", True)  # Default to True for AsyncOpenAI clients
    print(f"is_async: {is_async}")


    # Score Faithfulness
    faithfulness_metric = Faithfulness(llm=llm)
    faithfulness_score = await _run_metric_score(
        faithfulness_metric,
        is_async,
        rate_limiter=rate_limiter,
        user_input=sample["question"],
        response=sample["answer"],
        retrieved_contexts=sample["contexts"]
    )
    
    # Score Answer Relevancy (requires embeddings)
    relevancy_score = 0.0
    if embeddings:
        relevancy_metric = AnswerRelevancy(llm=llm, embeddings=embeddings)
        relevancy_score = await _run_metric_score(
            relevancy_metric,
            is_async,
            rate_limiter=rate_limiter,
            user_input=sample["question"],
            response=sample["answer"]
        )
    
    # Score Context Precision
    precision_metric = ContextPrecision(llm=llm)
    precision_kwargs = {
        "user_input": sample["question"],
        "retrieved_contexts": sample["contexts"],
    }
    if sample.get("reference"):
        precision_kwargs["reference"] = sample["reference"]
    
    precision_score = await _run_metric_score(precision_metric, is_async, rate_limiter=rate_limiter, **precision_kwargs)
    
    result = MetricScores(
        faithfulness=faithfulness_score,
        answer_relevancy=relevancy_score,
        context_precision=precision_score,
    )
    
    # Add reference-dependent metrics if available
    if has_reference and sample.get("reference"):
        # Context Recall
        recall_metric = ContextRecall(llm=llm)
        result.context_recall = await _run_metric_score(
            recall_metric,
            is_async,
            rate_limiter=rate_limiter,
            user_input=sample["question"],
            retrieved_contexts=sample["contexts"],
            reference=sample["reference"]
        )
        
        # Answer Correctness (requires embeddings for semantic similarity, or use factuality-only)
        if embeddings:
            correctness_metric = AnswerCorrectness(llm=llm, embeddings=embeddings)
        else:
            correctness_metric = AnswerCorrectness(llm=llm, weights=[1.0, 0.0])
        
        result.answer_correctness = await _run_metric_score(
            correctness_metric,
            is_async,
            rate_limiter=rate_limiter,
            user_input=sample["question"],
            response=sample["answer"],
            reference=sample["reference"]
        )
    
    return result


async def run_evaluation_async(
    questions: List[Dict],
    answers: List[str],
    contexts: List[List[str]],
    agent_type: str,
    llm_config: Dict[str, Any],
    reference_answers: Optional[List[str]] = None,
    meta_info: Optional[List[Dict]] = None,
) -> List[EvaluationResult]:
    """
    Runs RAGAS evaluation on a set of question-answer pairs using the v0.4 API.
    
    Args:
        questions: List of question dicts with 'id', 'question', 'reference_answer'
        answers: List of generated answers
        contexts: List of retrieved context chunks for each question
        agent_type: 'peer' or 'tutor'
        llm_config: LLM configuration dict
        reference_answers: Optional list of reference answers
        
    Returns:
        List of EvaluationResult objects
    """
    # Get LLM and embeddings for RAGAS
    ragas_llm, ragas_embeddings = get_ragas_llm_and_embeddings(llm_config)
    
    # Create rate limiter from config (disabled if limits are 0)
    rate_limiter = create_rate_limiter(llm_config)
    
    # Create samples
    samples = []
    for i, q in enumerate(questions):
        sample = {
            "question": q["question"],
            "answer": answers[i],
            "contexts": contexts[i],
            "meta_info": meta_info[i],
        }
        if reference_answers:
            sample["reference"] = reference_answers[i]
        samples.append(sample)
    
    # Score each sample
    results = []
    has_reference = reference_answers is not None
    
    for i, sample in enumerate(samples):
        print(f"Evaluating question {i+1}/{len(samples)}: {questions[i].get('id', f'Q{i+1}')}")
        
        metric_scores = await score_sample(
            sample=sample,
            llm=ragas_llm,
            embeddings=ragas_embeddings,
            has_reference=has_reference,
            rate_limiter=rate_limiter,
        )
        
        results.append(EvaluationResult(
            question_id=questions[i].get("id", f"Q{i+1}"),
            question=questions[i]["question"],
            agent_type=agent_type,
            answer=answers[i],
            contexts=contexts[i],
            reference_answer=reference_answers[i] if reference_answers else None,
            faithfulness=metric_scores.faithfulness,
            answer_relevancy=metric_scores.answer_relevancy,
            context_precision=metric_scores.context_precision,
            context_recall=metric_scores.context_recall,
            answer_correctness=metric_scores.answer_correctness,
            meta_info=meta_info[i],
        ))
    
    # Log results
    os.makedirs("logs", exist_ok=True)
    log_file = f'logs/result_{agent_type}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    with open(log_file, 'w') as f:
        import json
        json.dump([{
            "question_id": r.question_id,
            "faithfulness": r.faithfulness,
            "answer_relevancy": r.answer_relevancy,
            "context_precision": r.context_precision,
            "context_recall": r.context_recall,
            "answer_correctness": r.answer_correctness,
            "meta_info": r.meta_info,
        } for r in results], f, indent=2)
    
    return results


def run_evaluation(
    questions: List[Dict],
    answers: List[str],
    contexts: List[List[str]],
    agent_type: str,
    llm_config: Dict[str, Any],
    reference_answers: Optional[List[str]] = None,
    meta_info: Optional[List[Dict]] = None,
) -> List[EvaluationResult]:
    """
    Synchronous wrapper for run_evaluation_async.
    Maintains backward compatibility with existing code.
    """
    return asyncio.run(run_evaluation_async(
        questions=questions,
        answers=answers,
        contexts=contexts,
        agent_type=agent_type,
        llm_config=llm_config,
        reference_answers=reference_answers,
        meta_info=meta_info,
    ))

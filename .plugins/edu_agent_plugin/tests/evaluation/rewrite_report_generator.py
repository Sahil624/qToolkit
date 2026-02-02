"""
Rewrite Test Report Generator

Generates reports and visualizations for the rewrite prompt evaluation tests.
"""
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
import json
import numpy as np
import matplotlib.pyplot as plt

from .common import format_timestamp, interpret_score


def generate_similarity_chart(results: List[Dict], output_path: Path) -> str:
    """Generates a bar chart of similarity scores per scenario."""
    scenarios = [r["scenario_id"] for r in results]
    scores = [r["answer_similarity"] for r in results]
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    colors = ['#66c2a5' if s >= 0.85 else '#fc8d62' if s >= 0.7 else '#e78ac3' for s in scores]
    bars = ax.bar(range(len(scenarios)), scores, color=colors, alpha=0.8)
    
    ax.set_ylabel('Similarity Score', fontsize=12)
    ax.set_xlabel('Scenario ID', fontsize=12)
    ax.set_title('Rewrite Semantic Similarity Scores', fontsize=14, fontweight='bold')
    ax.set_xticks(range(len(scenarios)))
    ax.set_xticklabels(scenarios, rotation=45, ha='right')
    ax.set_ylim(0, 1.1)
    ax.axhline(y=0.85, color='green', linestyle='--', alpha=0.5, label='Target (0.85)')
    ax.axhline(y=0.7, color='gray', linestyle='--', alpha=0.5, label='Minimum (0.70)')
    ax.legend()
    
    # Add value labels
    for bar, score in zip(bars, scores):
        ax.annotate(f'{score:.2f}', xy=(bar.get_x() + bar.get_width()/2, bar.get_height()),
                    xytext=(0, 3), textcoords='offset points', ha='center', fontsize=9)
    
    plt.tight_layout()
    chart_path = output_path / "similarity_scores.png"
    plt.savefig(chart_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    return "similarity_scores.png"


def generate_retrieval_chart(results: List[Dict], output_path: Path) -> str:
    """Generates a bar chart of context recall scores per scenario."""
    scenarios = [r["scenario_id"] for r in results]
    scores = [r.get("context_recall", 0) or 0 for r in results]
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    colors = ['#66c2a5' if s >= 0.7 else '#fc8d62' if s >= 0.5 else '#e78ac3' for s in scores]
    bars = ax.bar(range(len(scenarios)), scores, color=colors, alpha=0.8)
    
    ax.set_ylabel('Context Recall', fontsize=12)
    ax.set_xlabel('Scenario ID', fontsize=12)
    ax.set_title('Rewrite Retrieval Effectiveness', fontsize=14, fontweight='bold')
    ax.set_xticks(range(len(scenarios)))
    ax.set_xticklabels(scenarios, rotation=45, ha='right')
    ax.set_ylim(0, 1.1)
    ax.axhline(y=0.7, color='green', linestyle='--', alpha=0.5, label='Target (0.70)')
    ax.legend()
    
    # Add value labels
    for bar, score in zip(bars, scores):
        ax.annotate(f'{score:.2f}', xy=(bar.get_x() + bar.get_width()/2, bar.get_height()),
                    xytext=(0, 3), textcoords='offset points', ha='center', fontsize=9)
    
    plt.tight_layout()
    chart_path = output_path / "retrieval_recall.png"
    plt.savefig(chart_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    return "retrieval_recall.png"


def generate_combined_chart(results: List[Dict], output_path: Path) -> str:
    """Generates a grouped bar chart with both similarity and recall scores."""
    scenarios = [r["scenario_id"] for r in results]
    similarity = [r["answer_similarity"] for r in results]
    recall = [r.get("context_recall", 0) or 0 for r in results]
    
    x = np.arange(len(scenarios))
    width = 0.35
    
    fig, ax = plt.subplots(figsize=(14, 6))
    
    bars1 = ax.bar(x - width/2, similarity, width, label='Similarity', color='#66c2a5', alpha=0.8)
    bars2 = ax.bar(x + width/2, recall, width, label='Recall', color='#fc8d62', alpha=0.8)
    
    ax.set_ylabel('Score', fontsize=12)
    ax.set_xlabel('Scenario ID', fontsize=12)
    ax.set_title('Rewrite Quality: Similarity vs Retrieval Recall', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(scenarios, rotation=45, ha='right')
    ax.set_ylim(0, 1.1)
    ax.legend()
    ax.axhline(y=0.7, color='gray', linestyle='--', alpha=0.3)
    
    plt.tight_layout()
    chart_path = output_path / "combined_scores.png"
    plt.savefig(chart_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    return "combined_scores.png"


def save_rewrite_results_json(
    similarity_results: List[Dict],
    recall_results: List[Dict],
    output_path: Path,
    llm_config: Dict[str, Any]
) -> str:
    """Saves numeric results as JSON file."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Combine results
    combined_results = []
    for sim, rec in zip(similarity_results, recall_results):
        combined_results.append({
            "scenario_id": sim["scenario_id"],
            "original_query": sim.get("original_query", ""),
            "actual_rewrite": sim.get("actual_rewrite", ""),
            "gold_standard": sim.get("gold_standard", ""),
            "answer_similarity": sim["answer_similarity"],
            "context_recall": rec.get("context_recall", None),
        })
    
    # Calculate aggregate stats
    sim_scores = [r["answer_similarity"] for r in combined_results]
    rec_scores = [r["context_recall"] for r in combined_results if r["context_recall"] is not None]
    
    data = {
        "metadata": {
            "timestamp": timestamp,
            "llm_provider": llm_config.get("provider"),
            "llm_model": llm_config.get("model"),
            "num_scenarios": len(combined_results),
        },
        "aggregate": {
            "similarity": {
                "mean": float(np.mean(sim_scores)) if sim_scores else None,
                "std": float(np.std(sim_scores)) if sim_scores else None,
                "min": float(np.min(sim_scores)) if sim_scores else None,
                "max": float(np.max(sim_scores)) if sim_scores else None,
            },
            "context_recall": {
                "mean": float(np.mean(rec_scores)) if rec_scores else None,
                "std": float(np.std(rec_scores)) if rec_scores else None,
                "min": float(np.min(rec_scores)) if rec_scores else None,
                "max": float(np.max(rec_scores)) if rec_scores else None,
            },
        },
        "per_scenario": combined_results,
    }
    
    json_path = output_path / "rewrite_results.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    
    return str(json_path)


def generate_rewrite_report(
    similarity_results: List[Dict],
    recall_results: List[Dict],
    output_path: Path,
    llm_config: Dict[str, Any],
) -> str:
    """
    Generates a comprehensive markdown report for rewrite evaluation.
    
    Creates:
    - rewrite_report.md: Main report with metrics and visualizations
    - rewrite_results.json: Numeric data export
    - figures/: Directory with chart images
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    report_id = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Create directory structure
    report_dir = output_path / f"rewrite_{report_id}"
    figures_dir = report_dir / "figures"
    report_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(exist_ok=True)
    
    # Combine results for processing
    combined = []
    for sim, rec in zip(similarity_results, recall_results):
        combined.append({
            "scenario_id": sim["scenario_id"],
            "original_query": sim.get("original_query", ""),
            "actual_rewrite": sim.get("actual_rewrite", ""),
            "gold_standard": sim.get("gold_standard", ""),
            "answer_similarity": sim["answer_similarity"],
            "context_recall": rec.get("context_recall", None),
        })
    
    # Generate charts
    sim_chart = generate_similarity_chart(combined, figures_dir)
    rec_chart = generate_retrieval_chart(combined, figures_dir)
    comb_chart = generate_combined_chart(combined, figures_dir)
    
    # Save JSON
    save_rewrite_results_json(similarity_results, recall_results, report_dir, llm_config)
    
    # Calculate aggregates
    sim_scores = [r["answer_similarity"] for r in combined]
    rec_scores = [r["context_recall"] for r in combined if r["context_recall"] is not None]
    
    avg_sim = np.mean(sim_scores) if sim_scores else 0
    avg_rec = np.mean(rec_scores) if rec_scores else 0
    
    report = f"""# Rewrite Prompt Evaluation Report

> **Generated**: {timestamp}  
> **Evaluation LLM**: `{llm_config.get('provider', 'unknown')}` / `{llm_config.get('model', 'unknown')}`  
> **Scenarios Evaluated**: {len(combined)}

---

## 1. Executive Summary

This report evaluates the **Query Rewrite Logic** using RAGAS metrics. The rewrite step transforms follow-up questions with ambiguous references into standalone, context-rich queries for better retrieval.

### Overall Performance

| Metric | Score | Target | Status |
|--------|-------|--------|--------|
| **Semantic Similarity** | {avg_sim:.3f} | ≥ 0.85 | {"✅ Pass" if avg_sim >= 0.85 else "❌ Below Target"} |
| **Context Recall** | {avg_rec:.3f} | ≥ 0.70 | {"✅ Pass" if avg_rec >= 0.70 else "❌ Below Target"} |

---

## 2. Visual Analysis

### 2.1 Semantic Similarity Scores

![Similarity Scores](figures/{sim_chart})

*Figure 1: Bar chart showing semantic similarity between actual rewrites and gold standard queries.*

### 2.2 Retrieval Effectiveness

![Retrieval Recall](figures/{rec_chart})

*Figure 2: Bar chart showing context recall for retrieval with rewritten queries.*

### 2.3 Combined View

![Combined Scores](figures/{comb_chart})

*Figure 3: Grouped comparison of similarity vs retrieval effectiveness.*

---

## 3. Per-Scenario Results

| Scenario | Similarity | Recall | Status |
|----------|------------|--------|--------|
"""

    for r in combined:
        sim = r["answer_similarity"]
        rec = r["context_recall"] if r["context_recall"] is not None else "N/A"
        rec_str = f"{rec:.3f}" if isinstance(rec, float) else rec
        status = "✅" if sim >= 0.85 and (rec == "N/A" or rec >= 0.7) else "⚠️"
        report += f"| {r['scenario_id']} | {sim:.3f} | {rec_str} | {status} |\n"

    report += f"""
---

## 4. Detailed Breakdown

"""

    for r in combined:
        ctx_recall = r['context_recall']
        ctx_recall_str = f"{ctx_recall:.3f}" if ctx_recall is not None else "N/A"
        report += f"""### {r['scenario_id']}

| Property | Value |
|----------|-------|
| **Original Query** | {r['original_query']} |
| **Gold Standard** | {r['gold_standard']} |
| **Actual Rewrite** | {r['actual_rewrite']} |
| **Similarity Score** | {r['answer_similarity']:.3f} |
| **Context Recall** | {ctx_recall_str} |

---

"""


    report += f"""## 5. Raw Data

For complete numeric data, see **[rewrite_results.json](rewrite_results.json)**.

---

## 6. Methodology

### 6.1 Metrics

- **Answer Similarity**: Semantic similarity between actual rewrite and gold standard using RAGAS.
- **Context Recall**: Measures if the rewritten query retrieves the expected context chunks.

### 6.2 Evaluation LLM

- **Provider:** `{llm_config.get('provider', 'unknown')}`
- **Model:** `{llm_config.get('model', 'unknown')}`
"""

    # Write report
    report_file = report_dir / "rewrite_report.md"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report)
    
    return str(report_file)

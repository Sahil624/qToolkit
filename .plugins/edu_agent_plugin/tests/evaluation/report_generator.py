"""
Report Generator

Generates a detailed Markdown report from RAGAS evaluation results.
Includes numerical metrics, matplotlib visualizations, and methodology explanations.
"""
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
import json
import numpy as np

# Scientific visualization
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

from .evaluator import EvaluationResult


def calculate_aggregate_scores(results: List[EvaluationResult]) -> Dict[str, Any]:
    """Calculates aggregate statistics across all results."""
    if not results:
        return {}
    
    scores = {
        "faithfulness": [],
        "answer_relevancy": [],
        "context_precision": [],
        "context_recall": [],
        "answer_correctness": [],
    }
    
    for r in results:
        scores["faithfulness"].append(r.faithfulness)
        scores["answer_relevancy"].append(r.answer_relevancy)
        scores["context_precision"].append(r.context_precision)
        if r.context_recall is not None:
            scores["context_recall"].append(r.context_recall)
        if r.answer_correctness is not None:
            scores["answer_correctness"].append(r.answer_correctness)
    
    def calc_stats(values):
        if not values:
            return None
        arr = np.array(values)
        return {
            "mean": float(np.mean(arr)),
            "min": float(np.min(arr)),
            "max": float(np.max(arr)),
            "std_dev": float(np.std(arr)),
            "median": float(np.median(arr)),
            "values": values,
        }
    
    return {k: calc_stats(v) for k, v in scores.items()}


def determine_winner(peer_score: float, tutor_score: float, threshold: float = 0.05) -> str:
    """Determines which agent won based on scores."""
    if peer_score is None or tutor_score is None:
        return "N/A"
    if abs(peer_score - tutor_score) < threshold:
        return "🤝 Tie"
    return "🏆 Peer" if peer_score > tutor_score else "🏆 Tutor"


def calculate_win_rates(peer_results: List[EvaluationResult], tutor_results: List[EvaluationResult]) -> Dict[str, Dict]:
    """Calculates win rates for each metric."""
    metrics = ["faithfulness", "answer_relevancy", "context_precision"]
    win_rates = {}
    
    for metric in metrics:
        peer_wins = 0
        tutor_wins = 0
        ties = 0
        
        for p, t in zip(peer_results, tutor_results):
            p_val = getattr(p, metric, 0)
            t_val = getattr(t, metric, 0)
            
            if abs(p_val - t_val) < 0.05:
                ties += 1
            elif p_val > t_val:
                peer_wins += 1
            else:
                tutor_wins += 1
        
        total = len(peer_results)
        win_rates[metric] = {
            "peer_wins": peer_wins,
            "tutor_wins": tutor_wins,
            "ties": ties,
            "peer_rate": peer_wins / total if total > 0 else 0,
            "tutor_rate": tutor_wins / total if total > 0 else 0,
        }
    
    return win_rates


def generate_comparison_bar_chart(peer_stats: Dict, tutor_stats: Dict, output_path: Path) -> str:
    """Generates a grouped bar chart comparing Peer vs Tutor metrics."""
    metrics = ["Faithfulness", "Answer\nRelevancy", "Context\nPrecision"]
    metric_keys = ["faithfulness", "answer_relevancy", "context_precision"]
    
    peer_means = [peer_stats.get(k, {}).get("mean", 0) or 0 for k in metric_keys]
    peer_stds = [peer_stats.get(k, {}).get("std_dev", 0) or 0 for k in metric_keys]
    tutor_means = [tutor_stats.get(k, {}).get("mean", 0) or 0 for k in metric_keys]
    tutor_stds = [tutor_stats.get(k, {}).get("std_dev", 0) or 0 for k in metric_keys]
    
    x = np.arange(len(metrics))
    width = 0.35
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    bars1 = ax.bar(x - width/2, peer_means, width, yerr=peer_stds, 
                   label='Peer Agent', color='#66c2a5', capsize=5, alpha=0.8)
    bars2 = ax.bar(x + width/2, tutor_means, width, yerr=tutor_stds,
                   label='Tutor Agent', color='#fc8d62', capsize=5, alpha=0.8)
    
    ax.set_ylabel('Score', fontsize=12)
    ax.set_title('Agent Performance Comparison (Mean ± Std Dev)', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(metrics, fontsize=11)
    ax.legend(fontsize=11)
    ax.set_ylim(0, 1.1)
    ax.axhline(y=0.7, color='gray', linestyle='--', alpha=0.5, label='Good Threshold')
    ax.axhline(y=0.9, color='green', linestyle='--', alpha=0.5, label='Excellent Threshold')
    
    # Add value labels on bars
    for bar, mean in zip(bars1, peer_means):
        ax.annotate(f'{mean:.2f}', xy=(bar.get_x() + bar.get_width()/2, bar.get_height()),
                    xytext=(0, 3), textcoords='offset points', ha='center', fontsize=10)
    for bar, mean in zip(bars2, tutor_means):
        ax.annotate(f'{mean:.2f}', xy=(bar.get_x() + bar.get_width()/2, bar.get_height()),
                    xytext=(0, 3), textcoords='offset points', ha='center', fontsize=10)
    
    plt.tight_layout()
    chart_path = output_path / "comparison_bar_chart.png"
    plt.savefig(chart_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    return str(chart_path)


def generate_radar_chart(peer_stats: Dict, tutor_stats: Dict, output_path: Path) -> str:
    """Generates a radar/spider chart for multi-dimensional comparison."""
    metrics = ["Faithfulness", "Answer\nRelevancy", "Context\nPrecision"]
    metric_keys = ["faithfulness", "answer_relevancy", "context_precision"]
    
    peer_values = [peer_stats.get(k, {}).get("mean", 0) or 0 for k in metric_keys]
    tutor_values = [tutor_stats.get(k, {}).get("mean", 0) or 0 for k in metric_keys]
    
    # Close the polygon
    peer_values += peer_values[:1]
    tutor_values += tutor_values[:1]
    
    angles = np.linspace(0, 2 * np.pi, len(metrics), endpoint=False).tolist()
    angles += angles[:1]
    
    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))
    
    ax.plot(angles, peer_values, 'o-', linewidth=2, label='Peer Agent', color='#66c2a5')
    ax.fill(angles, peer_values, alpha=0.25, color='#66c2a5')
    ax.plot(angles, tutor_values, 'o-', linewidth=2, label='Tutor Agent', color='#fc8d62')
    ax.fill(angles, tutor_values, alpha=0.25, color='#fc8d62')
    
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(metrics, fontsize=12)
    ax.set_ylim(0, 1)
    ax.set_title('Multi-Dimensional Agent Comparison', fontsize=14, fontweight='bold', pad=20)
    ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1))
    
    plt.tight_layout()
    chart_path = output_path / "radar_chart.png"
    plt.savefig(chart_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    return str(chart_path)


def generate_box_plot(peer_results: List[EvaluationResult], tutor_results: List[EvaluationResult], output_path: Path) -> str:
    """Generates box plots showing score distributions."""
    metrics = ["faithfulness", "answer_relevancy", "context_precision"]
    metric_labels = ["Faithfulness", "Answer Relevancy", "Context Precision"]
    
    fig, axes = plt.subplots(1, 3, figsize=(14, 5))
    
    for i, (metric, label) in enumerate(zip(metrics, metric_labels)):
        peer_data = [getattr(r, metric, 0) for r in peer_results]
        tutor_data = [getattr(r, metric, 0) for r in tutor_results]
        
        bp = axes[i].boxplot([peer_data, tutor_data], tick_labels=['Peer', 'Tutor'], patch_artist=True)
        
        bp['boxes'][0].set_facecolor('#66c2a5')
        bp['boxes'][1].set_facecolor('#fc8d62')
        
        axes[i].set_title(label, fontsize=12, fontweight='bold')
        axes[i].set_ylabel('Score')
        axes[i].set_ylim(0, 1.1)
        axes[i].axhline(y=0.7, color='gray', linestyle='--', alpha=0.5)
    
    plt.suptitle('Score Distribution by Metric', fontsize=14, fontweight='bold')
    plt.tight_layout()
    chart_path = output_path / "box_plot.png"
    plt.savefig(chart_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    return str(chart_path)


def generate_heatmap(peer_results: List[EvaluationResult], tutor_results: List[EvaluationResult], output_path: Path) -> str:
    """Generates a heatmap of per-question scores."""
    metrics = ["faithfulness", "answer_relevancy", "context_precision"]
    
    # Peer data
    peer_data = np.array([[getattr(r, m, 0) for m in metrics] for r in peer_results])
    tutor_data = np.array([[getattr(r, m, 0) for m in metrics] for r in tutor_results])
    
    fig, axes = plt.subplots(1, 2, figsize=(14, max(4, len(peer_results) * 0.5 + 2)))
    
    q_labels = [r.question_id for r in peer_results]
    metric_labels = ["Faith.", "Ans. Rel.", "Ctx. Prec."]
    
    # Peer heatmap
    im1 = axes[0].imshow(peer_data, cmap='RdYlGn', aspect='auto', vmin=0, vmax=1)
    axes[0].set_xticks(np.arange(len(metric_labels)))
    axes[0].set_yticks(np.arange(len(q_labels)))
    axes[0].set_xticklabels(metric_labels)
    axes[0].set_yticklabels(q_labels)
    axes[0].set_title('Peer Agent', fontsize=12, fontweight='bold')
    
    # Add text annotations
    for i in range(len(q_labels)):
        for j in range(len(metric_labels)):
            axes[0].text(j, i, f'{peer_data[i, j]:.2f}', ha='center', va='center', fontsize=9)
    
    # Tutor heatmap
    im2 = axes[1].imshow(tutor_data, cmap='RdYlGn', aspect='auto', vmin=0, vmax=1)
    axes[1].set_xticks(np.arange(len(metric_labels)))
    axes[1].set_yticks(np.arange(len(q_labels)))
    axes[1].set_xticklabels(metric_labels)
    axes[1].set_yticklabels(q_labels)
    axes[1].set_title('Tutor Agent', fontsize=12, fontweight='bold')
    
    for i in range(len(q_labels)):
        for j in range(len(metric_labels)):
            axes[1].text(j, i, f'{tutor_data[i, j]:.2f}', ha='center', va='center', fontsize=9)
    
    fig.colorbar(im2, ax=axes, shrink=0.6, label='Score')
    plt.suptitle('Per-Question Score Heatmap', fontsize=14, fontweight='bold')
    plt.tight_layout()
    chart_path = output_path / "heatmap.png"
    plt.savefig(chart_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    return str(chart_path)


# ================================================================================
# INDIVIDUAL AGENT REPORT GENERATION (NEW)
# ================================================================================

def generate_individual_bar_chart(stats: Dict, agent_type: str, output_path: Path) -> str:
    """Generates a bar chart for a single agent's metrics."""
    agent_name = agent_type.capitalize()
    color = '#66c2a5' if agent_type == 'peer' else '#fc8d62'
    
    metrics = ["Faithfulness", "Answer\nRelevancy", "Context\nPrecision"]
    metric_keys = ["faithfulness", "answer_relevancy", "context_precision"]
    
    means = [stats.get(k, {}).get("mean", 0) or 0 for k in metric_keys]
    stds = [stats.get(k, {}).get("std_dev", 0) or 0 for k in metric_keys]
    
    fig, ax = plt.subplots(figsize=(8, 5))
    
    x = np.arange(len(metrics))
    bars = ax.bar(x, means, yerr=stds, color=color, capsize=5, alpha=0.8)
    
    ax.set_ylabel('Score', fontsize=12)
    ax.set_title(f'{agent_name} Agent Performance', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(metrics, fontsize=11)
    ax.set_ylim(0, 1.1)
    ax.axhline(y=0.7, color='gray', linestyle='--', alpha=0.5, label='Good Threshold')
    ax.axhline(y=0.9, color='green', linestyle='--', alpha=0.5, label='Excellent Threshold')
    ax.legend(fontsize=9)
    
    # Add value labels on bars
    for bar, mean in zip(bars, means):
        ax.annotate(f'{mean:.2f}', xy=(bar.get_x() + bar.get_width()/2, bar.get_height()),
                    xytext=(0, 3), textcoords='offset points', ha='center', fontsize=10)
    
    plt.tight_layout()
    chart_path = output_path / "score_bar_chart.png"
    plt.savefig(chart_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    return "score_bar_chart.png"


def generate_individual_distribution_chart(results: List[EvaluationResult], agent_type: str, output_path: Path) -> str:
    """Generates a violin/box plot for score distribution of a single agent."""
    agent_name = agent_type.capitalize()
    color = '#66c2a5' if agent_type == 'peer' else '#fc8d62'
    
    metrics = ["faithfulness", "answer_relevancy", "context_precision"]
    metric_labels = ["Faithfulness", "Answer Relevancy", "Context Precision"]
    
    data = [[getattr(r, m, 0) for r in results] for m in metrics]
    
    fig, ax = plt.subplots(figsize=(10, 5))
    
    bp = ax.boxplot(data, tick_labels=metric_labels, patch_artist=True)
    for patch in bp['boxes']:
        patch.set_facecolor(color)
    
    ax.set_ylabel('Score', fontsize=12)
    ax.set_title(f'{agent_name} Agent Score Distribution', fontsize=14, fontweight='bold')
    ax.set_ylim(0, 1.1)
    ax.axhline(y=0.7, color='gray', linestyle='--', alpha=0.5)
    
    plt.tight_layout()
    chart_path = output_path / "score_distribution.png"
    plt.savefig(chart_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    return "score_distribution.png"


def generate_individual_heatmap(results: List[EvaluationResult], agent_type: str, output_path: Path) -> str:
    """Generates a heatmap for a single agent's per-question scores."""
    agent_name = agent_type.capitalize()
    metrics = ["faithfulness", "answer_relevancy", "context_precision"]
    metric_labels = ["Faith.", "Ans. Rel.", "Ctx. Prec."]
    
    data = np.array([[getattr(r, m, 0) for m in metrics] for r in results])
    q_labels = [r.question_id for r in results]
    
    fig, ax = plt.subplots(figsize=(8, max(4, len(results) * 0.5 + 2)))
    
    im = ax.imshow(data, cmap='RdYlGn', aspect='auto', vmin=0, vmax=1)
    ax.set_xticks(np.arange(len(metric_labels)))
    ax.set_yticks(np.arange(len(q_labels)))
    ax.set_xticklabels(metric_labels)
    ax.set_yticklabels(q_labels)
    ax.set_title(f'{agent_name} Agent Per-Question Scores', fontsize=12, fontweight='bold')
    
    # Add text annotations
    for i in range(len(q_labels)):
        for j in range(len(metric_labels)):
            ax.text(j, i, f'{data[i, j]:.2f}', ha='center', va='center', fontsize=9)
    
    fig.colorbar(im, ax=ax, shrink=0.6, label='Score')
    plt.tight_layout()
    chart_path = output_path / "heatmap.png"
    plt.savefig(chart_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    return "heatmap.png"


def generate_qa_details_file(results: List[EvaluationResult], agent_type: str, output_path: Path) -> str:
    """Generates a separate markdown file with full Q&A pairs."""
    agent_name = agent_type.capitalize()
    
    content = f"""# {agent_name} Agent - Full Question-Answer Pairs

> This file contains detailed question-answer pairs for individual review.
> For summary metrics, see [report.md](report.md).

---

"""
    for r in results:
        content += f"""## {r.question_id}: {r.question}

**Scores:**

| Metric | Score |
|--------|-------|
| Faithfulness | {r.faithfulness:.3f} |
| Answer Relevancy | {r.answer_relevancy:.3f} |
| Context Precision | {r.context_precision:.3f} |

**Retrieved Context (Top 2 chunks):**
```
{chr(10).join(r.contexts[:2]) if r.contexts else 'No context retrieved'}
```

**{agent_name} Agent Answer:**
> {r.answer.replace(chr(10), chr(10) + '> ')}

"""
        if r.reference_answer:
            content += f"""**Reference Answer:**
> {r.reference_answer.replace(chr(10), chr(10) + '> ')}

"""
        content += "---\n\n"
    
    qa_file = output_path / "qa_details.md"
    with open(qa_file, "w", encoding="utf-8") as f:
        f.write(content)
    
    return str(qa_file)


def interpret_score(score: float) -> str:
    """Interprets a score into a category."""
    if score >= 0.9:
        return "Excellent"
    elif score >= 0.7:
        return "Good"
    elif score >= 0.5:
        return "Needs Improvement"
    else:
        return "Poor"


def generate_individual_report(
    results: List[EvaluationResult],
    agent_type: str,
    output_path: Path,
    llm_config: Dict[str, Any],
) -> str:
    """
    Generates an individual evaluation report for a single agent.
    
    Creates:
    - report.md: Main report with metrics and visualizations
    - qa_details.md: Separate file with full Q&A pairs
    - figures/: Directory with chart images
    
    All image paths are relative to the report.md file.
    
    Args:
        results: List of EvaluationResult for this agent
        agent_type: 'peer' or 'tutor'
        output_path: Base output directory (will create agent subdirectory)
        llm_config: LLM configuration for metadata
    
    Returns:
        Path to the generated report.md
    """
    agent_name = agent_type.capitalize()
    stats = calculate_aggregate_scores(results)
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Create agent-specific directory and figures subdirectory
    agent_dir = output_path / agent_type
    figures_dir = agent_dir / "figures"
    agent_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(exist_ok=True)
    
    # Generate charts (functions return relative paths)
    bar_chart = generate_individual_bar_chart(stats, agent_type, figures_dir)
    dist_chart = generate_individual_distribution_chart(results, agent_type, figures_dir)
    heatmap = generate_individual_heatmap(results, agent_type, figures_dir)
    
    # Generate Q&A details file
    generate_qa_details_file(results, agent_type, agent_dir)
    
    # Calculate overall score
    overall = np.mean([
        stats.get("faithfulness", {}).get("mean", 0) or 0,
        stats.get("answer_relevancy", {}).get("mean", 0) or 0,
        stats.get("context_precision", {}).get("mean", 0) or 0,
    ])
    
    report = f"""# {agent_name} Agent Evaluation Report

> **Generated**: {timestamp}  
> **Evaluation LLM**: `{llm_config.get('provider', 'unknown')}` / `{llm_config.get('model', 'unknown')}`  
> **Questions Evaluated**: {len(results)}

---

## 1. Executive Summary

This report evaluates the **{agent_name} Agent** using the RAGAS (Retrieval Augmented Generation Assessment) framework.

### Overall Performance

| Metric | Value | Interpretation |
|--------|-------|----------------|
| **Overall Score** | {overall:.3f} | {interpret_score(overall)} |
| Faithfulness | {stats.get('faithfulness', {}).get('mean', 0):.3f} | {interpret_score(stats.get('faithfulness', {}).get('mean', 0) or 0)} |
| Answer Relevancy | {stats.get('answer_relevancy', {}).get('mean', 0):.3f} | {interpret_score(stats.get('answer_relevancy', {}).get('mean', 0) or 0)} |
| Context Precision | {stats.get('context_precision', {}).get('mean', 0):.3f} | {interpret_score(stats.get('context_precision', {}).get('mean', 0) or 0)} |

---

## 2. Visual Analysis

### 2.1 Performance Overview (Bar Chart)

![Performance Overview](figures/{bar_chart})

*Figure 1: Bar chart showing mean scores (with standard deviation) for each metric.*

### 2.2 Score Distribution (Box Plot)

![Score Distribution](figures/{dist_chart})

*Figure 2: Box plot showing the distribution of scores for each metric.*

### 2.3 Per-Question Scores (Heatmap)

![Per-Question Heatmap](figures/{heatmap})

*Figure 3: Heatmap showing scores per question. Green = high, Red = low.*

---

## 3. Detailed Statistics

### 3.1 Metric Definitions

| Metric | Description |
|--------|-------------|
| **Faithfulness** | Measures if the answer only uses information from context (no hallucinations) |
| **Answer Relevancy** | Measures if the answer addresses the question asked |
| **Context Precision** | Measures if the most relevant chunks are ranked higher |

### 3.2 Summary Statistics

| Metric | Mean | Std Dev | Median | Min | Max |
|--------|------|---------|--------|-----|-----|
"""

    metrics_to_show = [
        ("Faithfulness", "faithfulness"),
        ("Answer Relevancy", "answer_relevancy"),
        ("Context Precision", "context_precision"),
    ]
    
    for display_name, metric_key in metrics_to_show:
        s = stats.get(metric_key, {})
        mean = s.get("mean", 0) or 0
        std = s.get("std_dev", 0) or 0
        med = s.get("median", 0) or 0
        min_v = s.get("min", 0) or 0
        max_v = s.get("max", 0) or 0
        report += f"| {display_name} | {mean:.3f} | {std:.3f} | {med:.3f} | {min_v:.3f} | {max_v:.3f} |\n"

    report += f"""
### 3.3 Per-Question Results

| Q# | Faithfulness | Answer Relevancy | Context Precision |
|----|--------------|------------------|-------------------|
"""

    for r in results:
        report += f"| {r.question_id} | {r.faithfulness:.3f} | {r.answer_relevancy:.3f} | {r.context_precision:.3f} |\n"

    report += f"""
---

## 4. Full Q&A Details

For detailed question-answer pairs, see **[qa_details.md](qa_details.md)**.

---

## 5. Methodology

### 5.1 RAGAS Framework

This evaluation uses **RAGAS** (Retrieval Augmented Generation Assessment).

**Citation:**
> Es, S., James, J., Espinosa-Anke, L., & Schockaert, S. (2023). RAGAS: Automated Evaluation of Retrieval Augmented Generation. arXiv:2309.15217

### 5.2 Evaluation LLM

- **Provider:** `{llm_config.get('provider', 'unknown')}`
- **Model:** `{llm_config.get('model', 'unknown')}`

---

## 6. Raw Data Export

```json
{json.dumps({
    "metadata": {
        "timestamp": timestamp,
        "agent_type": agent_type,
        "llm_provider": llm_config.get('provider'),
        "llm_model": llm_config.get('model'),
        "num_questions": len(results),
    },
    "aggregate": {k: {"mean": v.get('mean'), "std": v.get('std_dev'), "median": v.get('median'), "min": v.get('min'), "max": v.get('max')} if v else None for k, v in stats.items()},
    "overall_score": float(overall),
}, indent=2)}
```
"""

    # Write report
    report_file = agent_dir / "report.md"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report)
    
    return str(report_file)


def generate_individual_reports(
    peer_results: List[EvaluationResult],
    tutor_results: List[EvaluationResult],
    output_path: Path,
    llm_config: Dict[str, Any],
) -> Dict[str, str]:
    """
    Generates individual reports for both agents.
    
    Creates folder structure:
        output_path/
        └── evaluation_<timestamp>/
            ├── peer/
            │   ├── report.md
            │   ├── qa_details.md
            │   └── figures/
            └── tutor/
                ├── report.md
                ├── qa_details.md
                └── figures/
    
    Returns:
        Dict with paths: {"peer": "...", "tutor": "..."}
    """
    report_id = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_base = output_path / f"evaluation_{report_id}"
    report_base.mkdir(parents=True, exist_ok=True)
    
    if peer_results:
        peer_report = generate_individual_report(peer_results, "peer", report_base, llm_config)
    else:
        peer_report = None
    
    if tutor_results:
        tutor_report = generate_individual_report(tutor_results, "tutor", report_base, llm_config)
    else:
        tutor_report = None
    
    return {
        "peer": peer_report,
        "tutor": tutor_report,
        "base_dir": str(report_base),
    }


# ================================================================================
# LEGACY COMPARATIVE REPORT (DEPRECATED - kept for backward compatibility)
# ================================================================================

def generate_report(
    peer_results: List[EvaluationResult],
    tutor_results: List[EvaluationResult],
    output_path: Path,
    llm_config: Dict[str, Any],
) -> str:
    """
    Generates a detailed Markdown evaluation report with matplotlib visualizations.
    """
    peer_stats = calculate_aggregate_scores(peer_results)
    tutor_stats = calculate_aggregate_scores(tutor_results)
    win_rates = calculate_win_rates(peer_results, tutor_results)
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    report_id = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Create figures directory
    figures_dir = output_path / f"figures_{report_id}"
    figures_dir.mkdir(exist_ok=True)
    
    # Generate all charts
    bar_chart_path = generate_comparison_bar_chart(peer_stats, tutor_stats, figures_dir)
    radar_chart_path = generate_radar_chart(peer_stats, tutor_stats, figures_dir)
    box_plot_path = generate_box_plot(peer_results, tutor_results, figures_dir)
    heatmap_path = generate_heatmap(peer_results, tutor_results, figures_dir)
    
    # Calculate overall scores
    peer_overall = np.mean([
        peer_stats.get("faithfulness", {}).get("mean", 0) or 0,
        peer_stats.get("answer_relevancy", {}).get("mean", 0) or 0,
        peer_stats.get("context_precision", {}).get("mean", 0) or 0,
    ])
    
    tutor_overall = np.mean([
        tutor_stats.get("faithfulness", {}).get("mean", 0) or 0,
        tutor_stats.get("answer_relevancy", {}).get("mean", 0) or 0,
        tutor_stats.get("context_precision", {}).get("mean", 0) or 0,
    ])

    report = f"""# Agent Evaluation Report

> **Generated**: {timestamp}  
> **Evaluation LLM**: `{llm_config.get('provider', 'unknown')}` / `{llm_config.get('model', 'unknown')}`  
> **Questions Evaluated**: {len(peer_results)}

---

## 1. Executive Summary

This report evaluates the **Peer Agent** and **Tutor Agent** using the RAGAS (Retrieval Augmented Generation Assessment) framework. The evaluation measures how well each agent:
1. Stays faithful to the retrieved context (no hallucinations)
2. Provides relevant answers to the questions asked
3. Uses the most relevant context chunks

### Overall Performance

| Agent | Overall Score | Interpretation |
|-------|--------------|----------------|
| **Peer Agent** | {peer_overall:.3f} | {"Excellent" if peer_overall >= 0.9 else "Good" if peer_overall >= 0.7 else "Needs Improvement" if peer_overall >= 0.5 else "Poor"} |
| **Tutor Agent** | {tutor_overall:.3f} | {"Excellent" if tutor_overall >= 0.9 else "Good" if tutor_overall >= 0.7 else "Needs Improvement" if tutor_overall >= 0.5 else "Poor"} |

**Overall Winner**: {determine_winner(peer_overall, tutor_overall)}

---

## 2. Visual Analysis

### 2.1 Performance Comparison (Bar Chart)

![Performance Comparison]({figures_dir}/{Path(bar_chart_path).name})

*Figure 1: Grouped bar chart comparing mean scores (with standard deviation error bars) for each metric.*

### 2.2 Multi-Dimensional Comparison (Radar Chart)

![Radar Chart]({figures_dir}/{Path(radar_chart_path).name})

*Figure 2: Radar chart showing the coverage area for each agent across all metrics.*

### 2.3 Score Distributions (Box Plot)

![Box Plot]({figures_dir}/{Path(box_plot_path).name})

*Figure 3: Box plots showing the distribution of scores for each metric. The horizontal dashed line indicates the "Good" threshold (0.7).*

### 2.4 Per-Question Heatmap

![Heatmap]({figures_dir}/{Path(heatmap_path).name})

*Figure 4: Heatmap visualization of scores for each question. Green indicates high scores, red indicates low scores.*

---

## 3. Detailed Numerical Results

### 3.1 Metric Definitions

| Metric | Description | Formula |
|--------|-------------|---------|
| **Faithfulness** | Measures if the answer only uses information from context | $\\frac{{\\text{{Claims supported by context}}}}{{\\text{{Total claims in answer}}}}$ |
| **Answer Relevancy** | Measures if the answer addresses the question | Semantic similarity between generated questions and original |
| **Context Precision** | Measures if relevant chunks are ranked higher | $\\frac{{\\sum_{{k=1}}^{{K}} (\\text{{Precision@k}} \\times v_k)}}{{\\text{{Relevant chunks}}}}$ |

### 3.2 Summary Statistics

| Metric | Peer (Mean) | Peer (Std) | Peer (Med) | Tutor (Mean) | Tutor (Std) | Tutor (Med) | Winner |
|--------|-------------|------------|------------|--------------|-------------|-------------|--------|
"""

    metrics_to_show = [
        ("Faithfulness", "faithfulness"),
        ("Answer Relevancy", "answer_relevancy"),
        ("Context Precision", "context_precision"),
    ]
    
    for display_name, metric_key in metrics_to_show:
        p_stats = peer_stats.get(metric_key, {})
        t_stats = tutor_stats.get(metric_key, {})
        p_mean = p_stats.get("mean", 0) or 0
        t_mean = t_stats.get("mean", 0) or 0
        p_std = p_stats.get("std_dev", 0) or 0
        t_std = t_stats.get("std_dev", 0) or 0
        p_med = p_stats.get("median", 0) or 0
        t_med = t_stats.get("median", 0) or 0
        
        report += f"| {display_name} | {p_mean:.3f} | {p_std:.3f} | {p_med:.3f} | {t_mean:.3f} | {t_std:.3f} | {t_med:.3f} | {determine_winner(p_mean, t_mean)} |\n"

    report += """
### 3.3 Min/Max Analysis

| Metric | Peer (Min) | Peer (Max) | Tutor (Min) | Tutor (Max) |
|--------|------------|------------|-------------|-------------|
"""

    for display_name, metric_key in metrics_to_show:
        p_stats = peer_stats.get(metric_key, {})
        t_stats = tutor_stats.get(metric_key, {})
        report += f"| {display_name} | {p_stats.get('min', 0):.3f} | {p_stats.get('max', 0):.3f} | {t_stats.get('min', 0):.3f} | {t_stats.get('max', 0):.3f} |\n"

    report += """
---

## 4. Win Rate Analysis

The win rate shows on how many questions each agent outperformed the other (threshold = 0.05).

| Metric | Peer Wins | Tutor Wins | Ties | Peer Win Rate |
|--------|-----------|------------|------|---------------|
"""

    for metric_key, rates in win_rates.items():
        display_name = metric_key.replace("_", " ").title()
        report += f"| {display_name} | {rates['peer_wins']} | {rates['tutor_wins']} | {rates['ties']} | {rates['peer_rate']*100:.1f}% |\n"

    total_peer_wins = sum(r['peer_wins'] for r in win_rates.values())
    total_tutor_wins = sum(r['tutor_wins'] for r in win_rates.values())
    total_ties = sum(r['ties'] for r in win_rates.values())
    total_comparisons = total_peer_wins + total_tutor_wins + total_ties
    
    report += f"| **Total** | **{total_peer_wins}** | **{total_tutor_wins}** | **{total_ties}** | **{total_peer_wins/total_comparisons*100:.1f}%** |\n"

    report += """
---

## 5. Per-Question Detailed Results

### 5.1 Head-to-Head Comparison

| Q# | Metric | Peer | Tutor | Δ (Peer - Tutor) | Winner |
|----|--------|------|-------|------------------|--------|
"""

    for p, t in zip(peer_results, tutor_results):
        for metric in ["faithfulness", "answer_relevancy", "context_precision"]:
            p_val = getattr(p, metric, 0)
            t_val = getattr(t, metric, 0)
            diff = p_val - t_val
            winner = "Peer" if diff > 0.05 else "Tutor" if diff < -0.05 else "Tie"
            report += f"| {p.question_id} | {metric.replace('_', ' ').title()} | {p_val:.3f} | {t_val:.3f} | {diff:+.3f} | {winner} |\n"

    report += """
---

## 6. Full Question-Answer Pairs

"""
    for i, (p, t) in enumerate(zip(peer_results, tutor_results)):
        report += f"""### {p.question_id}: {p.question}

**Scores:**

| Metric | Peer | Tutor |
|--------|------|-------|
| Faithfulness | {p.faithfulness:.3f} | {t.faithfulness:.3f} |
| Answer Relevancy | {p.answer_relevancy:.3f} | {t.answer_relevancy:.3f} |
| Context Precision | {p.context_precision:.3f} | {t.context_precision:.3f} |

**Retrieved Context (Top 2 chunks):**
```
{chr(10).join(p.contexts[:2]) if p.contexts else 'No context retrieved'}
```

**Peer Agent Answer:**
> {p.answer.replace(chr(10), chr(10) + '> ')}

**Tutor Agent Answer:**
> {t.answer.replace(chr(10), chr(10) + '> ')}

"""
        if p.reference_answer:
            report += f"""**Reference Answer:**
> {p.reference_answer.replace(chr(10), chr(10) + '> ')}

"""
        report += "---\n\n"

    report += f"""## 7. Methodology

### 7.1 RAGAS Framework

This evaluation uses **RAGAS** (Retrieval Augmented Generation Assessment), an industry-standard framework for evaluating RAG pipelines.

**Citation:**
> Es, S., James, J., Espinosa-Anke, L., & Schockaert, S. (2023). RAGAS: Automated Evaluation of Retrieval Augmented Generation. arXiv:2309.15217

### 7.2 Metric Calculations

#### Faithfulness
Measures whether the generated answer is grounded in the retrieved context.

$$\\text{{Faithfulness}} = \\frac{{\\text{{Number of claims in answer supported by context}}}}{{\\text{{Total number of claims in answer}}}}$$

**Process:**
1. Extract all claims from the generated answer
2. For each claim, verify if it can be inferred from the context
3. Calculate the ratio of supported claims

#### Answer Relevancy
Measures how relevant the generated answer is to the question.

**Process:**
1. Generate N potential questions that the answer could address
2. Calculate semantic similarity between generated questions and original
3. Average the similarity scores

#### Context Precision
Measures whether relevant chunks are ranked higher in the retrieved context.

$$\\text{{Context Precision@K}} = \\frac{{\\sum_{{k=1}}^{{K}} (\\text{{Precision@k}} \\times v_k)}}{{\\text{{Total relevant chunks}}}}$$

Where $v_k = 1$ if chunk at rank $k$ is relevant, 0 otherwise.

### 7.3 Evaluation LLM

- **Provider:** `{llm_config.get('provider', 'unknown')}`
- **Model:** `{llm_config.get('model', 'unknown')}`

All metrics are calculated using LLM-as-Judge methodology.

### 7.4 Limitations

1. **LLM Judge Bias:** The evaluation LLM may have inherent biases
2. **Single Run Variance:** Results may vary across runs
3. **Domain Specificity:** Metrics optimized for general RAG, not quantum computing specifically
4. **Sample Size:** With only {len(peer_results)} questions, statistical significance is limited

---

## 8. Raw Data Export

```json
{json.dumps({
    "metadata": {
        "timestamp": timestamp,
        "llm_provider": llm_config.get('provider'),
        "llm_model": llm_config.get('model'),
        "num_questions": len(peer_results),
    },
    "peer_aggregate": {k: {"mean": v.get('mean'), "std": v.get('std_dev'), "median": v.get('median')} if v else None for k, v in peer_stats.items()},
    "tutor_aggregate": {k: {"mean": v.get('mean'), "std": v.get('std_dev'), "median": v.get('median')} if v else None for k, v in tutor_stats.items()},
    "win_rates": win_rates,
    "overall_peer": float(peer_overall),
    "overall_tutor": float(tutor_overall),
}, indent=2)}
```
"""

    # Write report
    report_file = output_path / f"evaluation_report_{report_id}.md"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report)
    
    return str(report_file)

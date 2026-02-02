"""
Rewrite Logic Evaluation using RAGAS

This module tests ONLY the 'Rewrite' step by treating the 
Rewritten Query as a generated 'Answer' and comparing it to a 'Gold Standard'.

Metrics used:
1. Answer Similarity: Semantically compares 'Actual Rewrite' vs 'Gold Rewrite'.
2. Context Recall: Checks if the 'Rewritten Query' successfully retrieves the 'Gold Context'.
"""
import pytest
import yaml
import numpy as np
from pathlib import Path
from datasets import Dataset 
from ragas import evaluate
from ragas.metrics import answer_similarity, context_recall

# Import common utilities and report generator
from .evaluation.common import (
    get_ragas_llm_and_embeddings,
    parse_conversation_history,
)
from .evaluation.rewrite_report_generator import generate_rewrite_report

# Import your agent setup
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))


def get_metric_score(results, metric_name):
    """
    Safely extract a metric score from RAGAS results.
    Handles both single values and lists.
    """
    value = getattr(results, metric_name, 0)
    if isinstance(value, (list, np.ndarray)):
        return float(np.nanmean(value))
    return float(value) if value is not None else 0.0


class TestRewriteWithRagas:
    """
    Tests the query rewrite logic using RAGAS metrics.
    
    Run with: pytest tests/test_prompt_rewrite.py -v
    """

    @pytest.fixture(autouse=True)
    def setup(self, peer_agent, eval_llm_config, reports_dir):
        self.agent = peer_agent
        self.llm_config = eval_llm_config
        self.reports_dir = reports_dir
        
        # Load your scenarios (ensure they have 'gold_standard_query' added!)
        scenarios_path = Path(__file__).parent / "data" / "rewrite_scenarios.yaml"
        with open(scenarios_path, "r", encoding="utf-8") as f:
            self.scenarios = yaml.safe_load(f)["scenarios"]

    def _parse_history(self, raw_history):
        """Helper to parse your YAML history format using common utility."""
        return parse_conversation_history(raw_history)

    def test_rewrite_semantic_accuracy(self):
        """
        TEST 1: Does the rewrite MEAN the same thing as the gold standard?
        We use RAGAS 'answer_similarity' for this.
        """
        print("\n📝 Preparing RAGAS dataset for Rewrite Accuracy...")
        
        # Get LLM and embeddings for evaluation
        ragas_llm, ragas_embeddings = get_ragas_llm_and_embeddings(self.llm_config)
        
        data_points = {
            "question": [],      # Input Context (Just for logging/reference)
            "answer": [],        # 🤖 The Agent's Rewritten Query
            "ground_truth": [],  # 🏆 The Human Gold Standard Query
            "contexts": []       # Not needed for this specific metric, but required by API
        }
        
        actual_rewrites = []
        gold_standards = []

        for scenario in self.scenarios:
            history = self._parse_history(scenario["chat_history"])
            
            # 1. Run the Rewrite Logic
            actual_rewrite = self.agent.get_rewritten_query(
                scenario["original_query"], history
            )
            
            # 2. Map to RAGAS columns
            prompt_context = f"Original: {scenario['original_query']} | History: {len(history)} msgs"
            
            data_points["question"].append(prompt_context)
            data_points["answer"].append(actual_rewrite)
            data_points["ground_truth"].append(scenario["gold_standard_query"])
            data_points["contexts"].append(["N/A"]) # Placeholder
            
            actual_rewrites.append(actual_rewrite)
            gold_standards.append(scenario["gold_standard_query"])

        # 3. Create Dataset
        dataset = Dataset.from_dict(data_points)

        # 4. Run RAGAS with configured LLM
        print("🚀 Running RAGAS Answer Similarity...")
        results = evaluate(
            dataset=dataset,
            metrics=[answer_similarity],
            llm=ragas_llm,
            embeddings=ragas_embeddings,
        )

        print("\n📊 Semantic Similarity Report:")
        df = results.to_pandas()
        
        # Print results with our stored data
        for i, (rewrite, gold, score) in enumerate(zip(actual_rewrites, gold_standards, df["answer_similarity"])):
            print(f"  {i+1}. Score: {score:.3f}")
            print(f"     Actual:   {rewrite[:60]}...")
            print(f"     Expected: {gold[:60]}...")

        # 5. Assert Standard (e.g., > 0.85 similarity)
        avg_score = get_metric_score(results, "answer_similarity")
        print(f"\nAverage Score: {avg_score:.3f}")
        assert avg_score > 0.85, f"Rewrite quality {avg_score} is below standard"

    def test_rewrite_retrieval_effectiveness(self):
        """
        TEST 2: Does the rewritten query actually find the right data?
        We use RAGAS 'context_recall' for this.
        """
        print("\n🔍 Preparing RAGAS dataset for Retrieval Effectiveness...")
        
        # Get LLM and embeddings for evaluation
        ragas_llm, ragas_embeddings = get_ragas_llm_and_embeddings(self.llm_config)
        
        data_points = {
            "question": [],      # 🤖 The Agent's REWRITTEN Query
            "ground_truth": [],  # 🏆 The text of the Chunk we EXPECT to find
            "contexts": [],      # 📚 The text of the Chunks we ACTUALLY found
            "answer": []         # Placeholder
        }

        for scenario in self.scenarios:
            history = self._parse_history(scenario["chat_history"])
            
            # 1. Rewrite
            actual_rewrite = self.agent.get_rewritten_query(
                scenario["original_query"], history
            )
            
            # 2. Retrieve
            retrieved_texts = self.agent.db_manager.filter_with_lo_ids(actual_rewrite)
            
            # 3. Map to RAGAS
            data_points["question"].append(actual_rewrite)
            data_points["contexts"].append(retrieved_texts if retrieved_texts else ["No context"])
            data_points["ground_truth"].append(scenario["expected_chunk_text"]) 
            data_points["answer"].append("N/A")

        dataset = Dataset.from_dict(data_points)

        print("🚀 Running RAGAS Context Recall...")
        results = evaluate(
            dataset=dataset,
            metrics=[context_recall],
            llm=ragas_llm,
            embeddings=ragas_embeddings,
        )
        
        print("\n📊 Retrieval Recall Report:")
        df = results.to_pandas()
        print(df)
        
        avg_score = get_metric_score(results, "context_recall")
        print(f"\nAverage Context Recall: {avg_score:.3f}")
        assert avg_score > 0.7, f"Recall {avg_score} is below threshold"

    def test_rewrite_full_evaluation(self):
        """
        Comprehensive rewrite evaluation with report generation.
        Runs both similarity and recall tests, then generates a detailed report.
        """
        print("\n📊 Running Full Rewrite Evaluation...")
        
        # Get LLM and embeddings
        ragas_llm, ragas_embeddings = get_ragas_llm_and_embeddings(self.llm_config)
        
        # Collect all data in one pass
        similarity_results = []
        recall_results = []
        
        similarity_data = {
            "question": [], "answer": [], "ground_truth": [], "contexts": []
        }
        recall_data = {
            "question": [], "ground_truth": [], "contexts": [], "answer": []
        }
        
        print("📝 Collecting rewrite data...")
        for scenario in self.scenarios:
            history = self._parse_history(scenario["chat_history"])
            
            actual_rewrite = self.agent.get_rewritten_query(
                scenario["original_query"], history
            )
            
            retrieved_texts = self.agent.db_manager.filter_with_lo_ids(actual_rewrite)
            
            # Similarity data
            similarity_data["question"].append(f"Original: {scenario['original_query']}")
            similarity_data["answer"].append(actual_rewrite)
            similarity_data["ground_truth"].append(scenario["gold_standard_query"])
            similarity_data["contexts"].append(["N/A"])
            
            # Recall data
            recall_data["question"].append(actual_rewrite)
            recall_data["contexts"].append(retrieved_texts if retrieved_texts else ["No context"])
            recall_data["ground_truth"].append(scenario["expected_chunk_text"])
            recall_data["answer"].append("N/A")
        
        # Run similarity evaluation
        print("🚀 Running RAGAS Answer Similarity...")
        sim_dataset = Dataset.from_dict(similarity_data)
        sim_results = evaluate(
            dataset=sim_dataset,
            metrics=[answer_similarity],
            llm=ragas_llm,
            embeddings=ragas_embeddings,
        )
        
        # Run recall evaluation
        print("🚀 Running RAGAS Context Recall...")
        rec_dataset = Dataset.from_dict(recall_data)
        rec_results = evaluate(
            dataset=rec_dataset,
            metrics=[context_recall],
            llm=ragas_llm,
            embeddings=ragas_embeddings,
        )
        
        # Convert to per-scenario results
        sim_df = sim_results.to_pandas()
        rec_df = rec_results.to_pandas()
        
        for i, scenario in enumerate(self.scenarios):
            sim_score = sim_df.iloc[i]["answer_similarity"]
            rec_score = rec_df.iloc[i]["context_recall"]
            
            # Handle NaN values
            sim_score = float(sim_score) if not np.isnan(sim_score) else 0.0
            rec_score = float(rec_score) if not np.isnan(rec_score) else 0.0
            
            similarity_results.append({
                "scenario_id": scenario["id"],
                "original_query": scenario["original_query"],
                "gold_standard": scenario["gold_standard_query"],
                "actual_rewrite": similarity_data["answer"][i],
                "answer_similarity": sim_score,
            })
            recall_results.append({
                "scenario_id": scenario["id"],
                "context_recall": rec_score,
            })
        
        # Generate report
        print("\n📝 Generating rewrite evaluation report...")
        report_path = generate_rewrite_report(
            similarity_results=similarity_results,
            recall_results=recall_results,
            output_path=self.reports_dir,
            llm_config=self.llm_config,
        )
        print(f"✅ Report saved to: {report_path}")
        
        # Print summary
        avg_sim = get_metric_score(sim_results, "answer_similarity")
        avg_rec = get_metric_score(rec_results, "context_recall")
        print(f"\n📈 Results Summary:")
        print(f"   Average Similarity: {avg_sim:.3f}")
        print(f"   Average Recall: {avg_rec:.3f}")
        
        # Assert both metrics meet threshold
        assert avg_sim > 0.85, f"Similarity {avg_sim} below threshold"
        assert avg_rec > 0.7, f"Recall {avg_rec} below threshold"
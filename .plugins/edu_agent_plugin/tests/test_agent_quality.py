"""
Agent Quality Evaluation Tests

This test module evaluates the Peer and Tutor agents using RAGAS metrics.
Run with: pytest tests/test_agent_quality.py -v
"""
import pytest
from pathlib import Path

from .evaluation.evaluator import run_evaluation
from .evaluation.report_generator import generate_individual_reports
from .evaluation.common import parse_conversation_history

# Import prompt templates
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "edu_agents"))
from edu_agents.prompt import get_peer_prompt, get_tutor_prompt



class TestAgentQuality:
    """
    Evaluates the quality of Peer and Tutor agents using RAGAS metrics.
    """
    
    @pytest.fixture(autouse=True)
    def setup(self, eval_llm_config, evaluation_questions, reports_dir):
        """Setup test fixtures."""
        self.llm_config = eval_llm_config
        self.questions = evaluation_questions
        self.reports_dir = reports_dir
    
    def _parse_conversation_history(self, conversation_history: list):
        """Parse conversation history from yaml format using common utility."""
        return parse_conversation_history(conversation_history)

    def get_agent_response(self, agent, question: str, agent_type: str, completed_lo_ids: list = None, conversation_history: list = None):
        """
        Gets a response from an agent.
        
        Args:
            agent: PeerAgent instance
            question: The question to ask
            agent_type: 'peer' or 'tutor'
            completed_lo_ids: List of LO IDs the student has completed (for RAG filtering)
        
        Returns:
            Tuple of (answer, contexts)
        """

        if conversation_history:
            chat_history = conversation_history
        else:
            chat_history = []

        # Get the appropriate persona prompt
        if agent_type == "peer":
            persona_prompt = get_peer_prompt()
        else:
            persona_prompt = get_tutor_prompt(question, chat_history)
        
        # For evaluation, we want to test with all content available
        # Pass None for completed_lo_ids to disable filtering, or pass specific LOs
        lo_ids = completed_lo_ids if completed_lo_ids else None

        
        # Get the answer using the agent's answer_question method
        response = agent.answer_question(
            query=question,
            persona_prompt=persona_prompt,
            completed_lo_ids=lo_ids,
            chat_history=chat_history
        )

        if response.get('escalate'):
            # Skip this question if no context is retrieved or context is of poor quality
            # TODO: Figure out a better way to handle this
            return None, None, None
        
        answer = response['answer']
        meta_info = response['meta_info']
            

        # Get the rewritten query
        rewritten_query = agent.get_rewritten_query(question, chat_history)
        
        # Get contexts separately for RAGAS evaluation
        # The agent uses filter_with_lo_ids internally, we need to call it directly
        contexts = agent.db_manager.filter_with_lo_ids(
            query=rewritten_query,
            lo_ids=lo_ids,
            num_results=2
        )
        
        return answer, contexts if contexts else ["No context retrieved"], meta_info
    
    def _process_question(self, q, peer_agent):
        """Helper to process a single question."""
        print(f"  Starting processing for question {q['id']}...")
        
        # Get relevant LO IDs if specified in the question
        relevant_los = q.get("relevant_lo_ids", None)
        if relevant_los and len(relevant_los) == 0:
            relevant_los = None

        conversation_history = self._parse_conversation_history(q.get("conversation_history", []))


        # Get Peer Agent response
        p_answer, p_ctx, p_meta_info = self.get_agent_response(
            peer_agent, q["question"], "peer", relevant_los, conversation_history
        )
        
        # Get Tutor Agent response
        t_answer, t_ctx, t_meta_info = self.get_agent_response(
            peer_agent, q["question"], "tutor", relevant_los, conversation_history
        )
        
        return {
            "id": q["id"],
            "peer_answer": p_answer,
            "peer_context": p_ctx,
            "tutor_answer": t_answer,
            "tutor_context": t_ctx,
            "reference_answer": q.get("reference_answer", "").strip(),
            "peer_meta_info": p_meta_info,
            "tutor_meta_info": t_meta_info,
        }

    def test_evaluate_agents(self, peer_agent, persona_to_test):
        """
        Main evaluation test.
        
        Evaluates both Peer and Tutor agents on all questions
        and generates a comparative report.
        """
        import concurrent.futures

        if not self.questions:
            pytest.skip("No evaluation questions found")
            
        max_workers = self.llm_config.get("max_workers", 1)
        print(f"\n📊 Evaluating {len(self.questions)} questions using {max_workers} worker(s)...")

        results = []
        if max_workers > 1:
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all tasks
                future_to_q = {executor.submit(self._process_question, q, peer_agent): q for q in self.questions}
                for future in concurrent.futures.as_completed(future_to_q):
                    try:
                        results.append(future.result())
                    except Exception as e:
                        print(f"Generated an exception: {e}")
        else:
            # Sequential execution
            for q in self.questions:
                print(f"  ❓ {q['id']}: {q['question'][:50]}...")
                results.append(self._process_question(q, peer_agent))
        
        # Sort results by question ID to maintain consistent order
        # Assuming IDs might be numeric or strings, we'll index based on original list if possible
        # Or just sort by ID string for stability
        q_order = {q["id"]: i for i, q in enumerate(self.questions)}
        results.sort(key=lambda x: q_order.get(x["id"], 0))

        reference_answers = [r["reference_answer"] if r["reference_answer"] else None for r in results]
        

        peer_questions = []
        peer_answers = []
        peer_contexts = []
        peer_reference_answers = []
        peer_meta_info = []

        tutor_questions = []
        tutor_answers = []
        tutor_contexts = []
        tutor_reference_answers = []
        tutor_meta_info = []

        for i, result in enumerate(results):
            if result["peer_answer"] is not None:
                peer_questions.append(self.questions[i])
                peer_answers.append(result["peer_answer"])
                peer_contexts.append(result["peer_context"])
                peer_reference_answers.append(result["reference_answer"])
                peer_meta_info.append(result["peer_meta_info"])
            if result["tutor_answer"] is not None:
                tutor_questions.append(self.questions[i])
                tutor_answers.append(result["tutor_answer"])
                tutor_contexts.append(result["tutor_context"])
                tutor_reference_answers.append(result["reference_answer"])
                tutor_meta_info.append(result["tutor_meta_info"])
                
        print("\n🔬 Running RAGAS evaluation on Peer Agent...")
        if persona_to_test in ["peer", "both"]:
            peer_results = run_evaluation(
                questions=peer_questions,
                answers=peer_answers,
                contexts=peer_contexts,
                agent_type="peer",
                llm_config=self.llm_config,
                reference_answers=peer_reference_answers,
                meta_info=peer_meta_info,
            )
        else:
            print("Skipping Peer Agent evaluation.")
            peer_results = []
        
        print("🔬 Running RAGAS evaluation on Tutor Agent...")
        if persona_to_test in ["tutor", "both"]:
            tutor_results = run_evaluation(
                questions=tutor_questions,
                answers=tutor_answers,
                contexts=tutor_contexts,
                agent_type="tutor",
                llm_config=self.llm_config,
                reference_answers=tutor_reference_answers,
                meta_info=tutor_meta_info,
            )
        else:
            print("Skipping Tutor Agent evaluation.")
            tutor_results = []
        
        # Generate individual reports for each agent
        print("\n📝 Generating individual reports...")
        report_paths = generate_individual_reports(
            peer_results=peer_results,
            tutor_results=tutor_results,
            output_path=self.reports_dir,
            llm_config=self.llm_config,
        )
        
        print(f"✅ Peer report saved to: {report_paths['peer']}")
        print(f"✅ Tutor report saved to: {report_paths['tutor']}")
        
        # Calculate averages, handling NaN values
        import math
        peer_faithful_vals = [r.faithfulness for r in peer_results if not math.isnan(r.faithfulness)]
        tutor_faithful_vals = [r.faithfulness for r in tutor_results if not math.isnan(r.faithfulness)]
        
        avg_peer_faithfulness = sum(peer_faithful_vals) / len(peer_faithful_vals) if peer_faithful_vals else 0
        avg_tutor_faithfulness = sum(tutor_faithful_vals) / len(tutor_faithful_vals) if tutor_faithful_vals else 0
        
        # Log results
        print(f"\n📈 Results Summary:")
        print(f"   Peer Agent Avg Faithfulness: {avg_peer_faithfulness:.3f}")
        print(f"   Tutor Agent Avg Faithfulness: {avg_tutor_faithfulness:.3f}")
        
        # Check for NaN values
        peer_nan_count = sum(1 for r in peer_results if math.isnan(r.faithfulness))
        tutor_nan_count = sum(1 for r in tutor_results if math.isnan(r.faithfulness))
        if peer_nan_count > 0:
            print(f"   ⚠️ Peer Agent had {peer_nan_count} NaN values")
        if tutor_nan_count > 0:
            print(f"   ⚠️ Tutor Agent had {tutor_nan_count} NaN values")
        
        # Basic sanity check - scores should be valid numbers
        if persona_to_test in ["peer", "both"]:
            assert len(peer_faithful_vals) > 0, "Peer should have at least one valid faithfulness score"
        if persona_to_test in ["tutor", "both"]:
            assert len(tutor_faithful_vals) > 0, "Tutor should have at least one valid faithfulness score"


class TestSingleQuestion:
    """
    Quick test for debugging with a single question.
    """
    
    def test_single_question_peer(self, peer_agent):
        """Tests the Peer agent with a single hardcoded question."""
        question = "What is a qubit?"
        
        try:
            persona_prompt = get_peer_prompt()
            response = peer_agent.answer_question(
                query=question,
                persona_prompt=persona_prompt,
                completed_lo_ids=None,  # No filtering for test
                chat_history=[]
            )['answer']
            print(f"\nQuestion: {question}")
            print(f"Peer Response: {response[:500]}...")
            assert response, "Response should not be empty"
        except Exception as e:
            pytest.skip(f"Agent not available: {e}")
    
    def test_single_question_tutor(self, peer_agent):
        """Tests the Tutor agent with a single hardcoded question."""
        question = "What is a qubit?"
        
        try:
            persona_prompt = get_tutor_prompt(question, [])
            response = peer_agent.answer_question(
                query=question,
                persona_prompt=persona_prompt,
                completed_lo_ids=None,  # No filtering for test
                chat_history=[]
            )['answer']
            print(f"\nQuestion: {question}")
            print(f"Tutor Response: {response[:500]}...")
            assert response, "Response should not be empty"
        except Exception as e:
            pytest.skip(f"Agent not available: {e}")

"""
Pytest fixtures for agent evaluation tests.
"""
import os
import sys
import yaml
import pytest
from pathlib import Path
from dotenv import load_dotenv

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "edu_agents"))

# Load environment variables from .env file
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    # Fall back to .env.example for defaults
    load_dotenv(Path(__file__).parent / ".env.example")


def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--question",
        action="store",
        default=None,
        help="Comma separated list of question IDs to evaluate"
    )
    parser.addoption(
        "--scenario",
        action="store",
        default=None,
        help="Comma separated list of rewrite scenario IDs to evaluate"
    )
    parser.addoption(
        "--persona",
        action="store",
        default="both",
        choices=["peer", "tutor", "both"],
        help="Which agent persona to evaluate: 'peer', 'tutor', or 'both' (default)"
    )


@pytest.fixture(scope="session")
def persona_to_test(request):
    """Returns the persona to test from CLI args."""
    return request.config.getoption("--persona")


@pytest.fixture(scope="session")
def eval_llm_config():
    """Returns the LLM configuration for evaluation."""
    return {
        "provider": os.getenv("EVAL_LLM_PROVIDER", "ollama"),
        "model": os.getenv("EVAL_LLM_MODEL", "llama3.1:8b"),
        "base_url": os.getenv("EVAL_LLM_BASE_URL", "http://localhost:11434/v1"),
        "openai_api_key": os.getenv("OPENAI_API_KEY"),
        "google_api_key": os.getenv("GOOGLE_API_KEY"),
        "anthropic_api_key": os.getenv("ANTHROPIC_API_KEY"),
        "use_cache": os.getenv("EVAL_USE_CACHE", "true") == "true",
        # Rate Limiting (0 = disabled)
        "rate_limit_rpm": int(os.getenv("EVAL_RATE_LIMIT_RPM", "0")),
        "rate_limit_tpm": int(os.getenv("EVAL_RATE_LIMIT_TPM", "0")),
        "rate_limit_rpd": int(os.getenv("EVAL_RATE_LIMIT_RPD", "0")),
        # Parallelization
        "max_workers": int(os.getenv("EVAL_MAX_WORKERS", "1")),
    }


@pytest.fixture(scope="session")
def evaluation_questions(request):
    """Loads the evaluation questions from YAML."""
    
    questions_path = Path(__file__).parent / "data" / "evaluation_questions.yaml"
    with open(questions_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    
    # Filter questions if --question argument is provided
    question_arg = request.config.getoption("--question")
    if question_arg:
        question_ids = question_arg.split(",")
        data["questions"] = [q for q in data["questions"] if q["id"] in question_ids]
        
    return data.get("questions", [])


@pytest.fixture(scope="session")
def peer_agent():
    """Creates a Peer Agent instance for testing."""
    try:
        from edu_agents.v_db.peer_agent import PeerAgent
        return PeerAgent(db_path="data/vector_db")
    except ImportError as e:
        pytest.skip(f"Could not import PeerAgent: {e}")


@pytest.fixture(scope="session")
def reports_dir():
    """Returns the path to the reports directory."""
    reports_path = Path(__file__).parent / "reports"
    reports_path.mkdir(exist_ok=True)
    return reports_path

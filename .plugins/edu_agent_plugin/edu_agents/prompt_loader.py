"""
Prompt Loader Module

Loads versioned prompt templates from YAML files.
Supports version tracking and A/B testing of prompts.
"""
import os
from pathlib import Path
from typing import Optional
import yaml
from packaging import version as pkg_version


PRINT_DEBUG = False

# Directory containing YAML prompt files
PROMPTS_DIR = Path(__file__).parent / "prompts"


def load_active_prompt(agent_type: str) -> str:
    """
    Loads the active prompt template for the given agent type.
    
    Args:
        agent_type: One of 'peer', 'tutor', or 'rewrite'
        
    Returns:
        The raw template string for the active prompt version.
        
    Raises:
        FileNotFoundError: If the YAML file doesn't exist
        ValueError: If no active prompt is found
    """
    yaml_file = PROMPTS_DIR / f"{agent_type}_prompts.yaml"
    
    if not yaml_file.exists():
        raise FileNotFoundError(f"Prompt file not found: {yaml_file}")
    
    with open(yaml_file, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    prompts = data.get('prompts', [])
    
    # Filter to only active prompts
    active_prompts = [p for p in prompts if p.get('active', False)]
    
    if not active_prompts:
        raise ValueError(f"No active prompt found in {yaml_file}")
    
    # If multiple are active, take the one with the highest version
    if len(active_prompts) > 1:
        active_prompts.sort(
            key=lambda p: pkg_version.parse(p.get('version', '0.0')),
            reverse=True
        )
    
    selected = active_prompts[0]
    template = selected.get('template', '')
    
    # Log which version was loaded (helpful for debugging)
    version = selected.get('version', 'unknown')
    if PRINT_DEBUG:
        print(f"[PromptLoader] Loaded {agent_type} prompt v{version}")
    
    return template


def get_prompt_version(agent_type: str) -> str:
    """
    Returns the version string of the currently active prompt.
    
    Useful for logging and tracking which prompt version was used.
    """
    yaml_file = PROMPTS_DIR / f"{agent_type}_prompts.yaml"
    
    if not yaml_file.exists():
        return "unknown"
    
    with open(yaml_file, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    prompts = data.get('prompts', [])
    active_prompts = [p for p in prompts if p.get('active', False)]
    
    if not active_prompts:
        return "none"
    
    # Get highest version among active
    active_prompts.sort(
        key=lambda p: pkg_version.parse(p.get('version', '0.0')),
        reverse=True
    )
    
    return active_prompts[0].get('version', 'unknown')


def list_prompt_versions(agent_type: str) -> list:
    """
    Lists all available prompt versions for an agent type.
    
    Returns:
        List of dicts with 'version', 'active', and 'description' keys.
    """
    yaml_file = PROMPTS_DIR / f"{agent_type}_prompts.yaml"
    
    if not yaml_file.exists():
        return []
    
    with open(yaml_file, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    prompts = data.get('prompts', [])
    
    return [
        {
            'version': p.get('version', 'unknown'),
            'active': p.get('active', False),
            'description': p.get('description', '')
        }
        for p in prompts
    ]

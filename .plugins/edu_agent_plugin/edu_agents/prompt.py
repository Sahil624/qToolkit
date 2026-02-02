"""
Prompt Builder Module

Loads prompt templates from YAML files and injects dynamic variables.
Templates are versioned for tracking and A/B testing.
"""
from .prompt_loader import load_active_prompt


def format_chat_history(history: list) -> str:
    """
    Helper to convert the list of message dictionaries into a clean string 
    that the LLM can read as a script.
    
    Args:
        history (list): List of dicts like [{'sender': 'user', 'text': 'hi'}]
    
    Returns:
        str: Formatted dialogue.
    """
    if not history:
        return "No recent conversation history."
    
    formatted_rows = []
    for msg in history:
        sender = msg.get('sender', 'unknown')
        text = msg.get('text', '').strip()
        
        # Map internal sender names to clear roles for the LLM
        if sender == 'user':
            role = "Student"
        elif sender == 'peer':
            role = "Peer Agent"
        elif sender == 'tutor':
            role = "Tutor Agent"
        else:
            role = "System"
            
        formatted_rows.append(f"{role}: {text}")
    
    # Join with newlines to create a script format
    return "\n".join(formatted_rows)


def get_rewrite_prompt(user_query: str, chat_history: list) -> str:
    """
    Constructs a prompt to rewrite a follow-up question into a standalone search query.
    
    Args:
        user_query: The user's follow-up question
        chat_history: Previous conversation messages
        
    Returns:
        Complete prompt string for the rewriter
    """
    history_string = format_chat_history(chat_history)
    
    # Load template from YAML and inject variables
    template = load_active_prompt("rewrite")
    
    return template.format(
        history_string=history_string,
        user_query=user_query
    )


def get_peer_prompt(is_trigger_event: bool = False, chat_history: list = None) -> str:
    """
    Constructs the full system prompt for the Peer Agent.
    
    Args:
        is_trigger_event (bool): If True, this is a system-generated event (like "Lesson Complete"),
                                 so the agent MUST start the conversation/ask a question.
        chat_history: Previous conversation messages
    
    Returns:
        Complete system prompt string
    """
    if chat_history is None:
        chat_history = []
    
    # Format history section
    if chat_history:
        history_string = format_chat_history(chat_history)
        history_section = f"""
### CONTEXT (Conversation History)
Use this history to understand the flow, but focus on the current question.
---
{history_string}
---
"""
    else:
        history_section = ""
    
    # Load template from YAML and inject variables
    template = load_active_prompt("peer")
    
    return template.format(
        history_section=history_section
    )


def get_tutor_prompt(user_query: str, chat_history: list) -> str:
    """
    Constructs the prompt for the Tutor Agent, specifically for escalation scenarios.
    It includes the formatted conversation history.
    
    Args:
        user_query: The student's question
        chat_history: Previous conversation messages
        
    Returns:
        Complete prompt string for the Tutor
    """
    peer_answer = chat_history[-1]['text'] if chat_history else "No previous answer."
    history_string = format_chat_history(chat_history)
    
    # Load template from YAML and inject variables
    template = load_active_prompt("tutor")
    
    return template.format(
        history_string=history_string,
        user_query=user_query,
        peer_answer=peer_answer
    )
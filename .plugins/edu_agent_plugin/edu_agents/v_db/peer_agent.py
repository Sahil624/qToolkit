from pyparsing import Union
import requests
import json
import os
import ipywidgets as widgets
from IPython.display import display, Markdown
from .vector_db_manager import VectorDBManager, get_db_manager_instance
from ..prompt import get_rewrite_prompt

class PeerAgent:
    """
    The backend "brain" for the Student Peer agent. It handles RAG searches
    and communication with an LLM via Ollama.
    """
    def __init__(self, 
                 db_path: str,
                 ollama_embed_model: str = 'nomic-embed-text',
                 ollama_chat_model: str = 'llama3.1:8b',
                 ollama_base_url: str = os.getenv("OLLAMA_API_URL", "http://localhost:11434")):
        """Initializes the PeerAgent's backend."""
        self.db_manager = get_db_manager_instance()
        self.ollama_chat_model = ollama_chat_model
        self.ollama_api_url = f"{ollama_base_url}/api/generate"

    def _call_ollama_llm(self, prompt: str) -> str:
        """Calls the Ollama API to get a response from the chat model."""
        try:
            payload = {
                "model": self.ollama_chat_model,
                "prompt": prompt,
                "stream": False 
            }
            response = requests.post(self.ollama_api_url, json=payload)
            response.raise_for_status()
            return response.json().get("response", "Sorry, I couldn't come up with a response.")
        except requests.exceptions.RequestException as e:
            error_message = f"Error calling Ollama API: {e}. Please ensure Ollama is running and the model '{self.ollama_chat_model}' is pulled."
            print(error_message)
            return error_message    

    def answer_question(self, query: str, persona_prompt: str, completed_lo_ids: Union[list, None] = None, chat_history = []) -> str:
        """
        Answers a student's question using the RAG pipeline.
        This method now accepts the persona prompt directly.
        """
        
        if chat_history:
            # If we have history, the user might be saying "it" or "that".
            # We need to rewrite the query to be standalone for the vector search.
            print(f"Contextualizing query: '{query}'...")
            rewrite_prompt = get_rewrite_prompt(query, chat_history)
            rewritten = self._call_ollama_llm(rewrite_prompt)
            
            # Basic cleanup in case the model is chatty
            clean_rewritten = rewritten.strip().replace("\"", "")
            if clean_rewritten and len(clean_rewritten) < 200: # Sanity check length
                print(f"Rewrote query for search: '{clean_rewritten}'")
                query = clean_rewritten
                
        context_chunks = self.db_manager.filter_with_lo_ids(
            query=query, lo_ids=completed_lo_ids, num_results=2
        )
        context_str = "\n\n".join(context_chunks)
        if not context_str:
            context_str = "I couldn't find anything specific about that in my notes."
            print("No context found for the query in the vector database.")
        # else:
        #     print(f"Context found for the query:\n{context_str}\n{'-'*40}")

        prompt = f"""{persona_prompt}

### COURSE NOTES (Source Material)
---
{context_str}
---
"""

        # In case of tutor, query is already in prompt
        if completed_lo_ids is not None:
            prompt += f"""

### TASK
Based ONLY on the "Course Notes" above and your persona, answer the following question.
Question: "{query}"            
"""
        return self._call_ollama_llm(prompt)

class PeerAgentUI:
    """
    Creates and manages the ipywidgets UI for the Peer Agent in a Jupyter Notebook.
    This is the main entry point to be used in the notebook.
    """
    def __init__(self, 
                 db_path: str = "./faiss_course_db",
                 persona_file: str = "student-peer-persona.md",
                 progress_file: str = "student_progress.json",
                 ollama_embed_model: str = 'nomic-embed-text',
                 ollama_chat_model: str = 'llama3.1:8b'):
        """Initializes the UI and the backend agent."""
        self.progress_file = progress_file
        self.learning_pointer = self._get_student_progress()
        self.persona_prompt = self._load_persona(persona_file)
        
        try:
            self.agent = PeerAgent(
                db_path=db_path,
                ollama_embed_model=ollama_embed_model,
                ollama_chat_model=ollama_chat_model
            )
        except Exception as e:
            print(f"Error initializing Peer Agent backend: {e}")
            self.agent = None
            
        self._create_ui_layout()

    def _get_student_progress(self) -> int:
        """Loads the student's current lesson number."""
        if not os.path.exists(self.progress_file):
            return 1
        try:
            with open(self.progress_file, 'r') as f:
                return json.load(f).get("current_lesson", 1)
        except (json.JSONDecodeError, FileNotFoundError):
            return 1
            
    def _load_persona(self, filepath: str) -> str:
        """Loads the persona prompt from a file."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            print(f"Warning: Persona file not found at {filepath}. Using a default persona.")
            return "You are a student peer, learning alongside the user. Explain concepts simply, admit when you don't know something, and ask clarifying questions. Your tone is friendly, informal, and encouraging. You are not an expert."

    def _create_ui_layout(self):
        """Creates and styles all the ipywidgets for a more immersive UI."""
        
        intro_html = widgets.HTML(
            value=f"""
            <div style="line-height: 1.5;">
                Hey there! 👋 Looks like we're both on <b>Lesson {self.learning_pointer}</b>.
                <br>
                If you're stuck on anything from this lesson or the ones before, just ask me below. 
                I'll check my notes and we can try to figure it out together. No worries if I don't get it right away, we're both learning! 😄
            </div>
            """
        )

        self.question_area = widgets.Textarea(
            value='',
            placeholder="Stuck on something? Ask me here! I'll try my best to help.",
            layout=widgets.Layout(width='98%', height='90px')
        )

        self.submit_button = widgets.Button(
            description="Let's figure it out!",
            button_style='success',
            tooltip="Ask me your question",
            icon='user-friends',
            layout=widgets.Layout(width='200px', height='auto')
        )

        self.output_area = widgets.Output(
            layout=widgets.Layout(padding='10px', border='1px solid #fafafa', min_height='80px')
        )
        
        self.submit_button.on_click(self._on_button_clicked)

        self.ui_container = widgets.VBox([
            intro_html,
            self.question_area,
            self.submit_button,
            self.output_area
        ], layout=widgets.Layout(
            display='flex',
            flex_flow='column',
            align_items='flex-start',
            border='2px solid #66c2a5',
            padding='15px',
            margin='10px 0 0 0',
            border_radius='10px',
            width='95%'
        ))

    def _on_button_clicked(self, b):
        """Handles the button click event."""
        with self.output_area:
            self.output_area.clear_output()
            query = self.question_area.value
            
            if not query.strip():
                display(Markdown("<i>Oops, looks like you forgot to type a question!</i>"))
                return
            if not self.agent:
                display(Markdown("<b>Oh no! It seems like my 'brain' isn't working right now. Please check the setup errors above.</b>"))
                return
            
            self.submit_button.disabled = True
            self.submit_button.description = 'Hmm, let me think...'
            self.submit_button.icon = 'spinner'
            
            response = self.agent.answer_question(query, self.learning_pointer, self.persona_prompt)
            
            display(Markdown(response))
            
            self.submit_button.disabled = False
            self.submit_button.description = "Let's figure it out!"
            self.submit_button.icon = 'user-friends'

    def display_ui(self):
        """Renders the complete UI in the notebook."""
        display(self.ui_container)


# PeerAgentUI().display_ui()
from typing import Dict, Union, List

import faiss
import numpy as np
import requests
import json
import pickle
import os

from .utils import singleton, find_project_root
from .hybrid_retriever import HybridRetriever

@singleton
class VectorDBManager:
    """
    A manager class to handle interactions with a FAISS vector database.
    This class uses Ollama for embedding generation and supports metadata filters.
    
    Prerequisites:
    - An Ollama instance must be running.
    - An embedding model (e.g., 'nomic-embed-text') must be pulled in Ollama.
      Run `ollama pull nomic-embed-text` in your terminal.
    """

    def __init__(self, path: str = "./faiss_db", ollama_model: str = 'nomic-embed-text', ollama_base_url: str = os.getenv("OLLAMA_API_URL", "http://localhost:11434")):
        """
        Initializes the VectorDBManager with FAISS and Ollama.

        Args:
            path (str): The directory path to store the persistent database files.
            ollama_model (str): The name of the embedding model to use in Ollama.
            ollama_base_url (str): The base URL for the Ollama API.
        """
        self.db_path = path
        self.index_file = os.path.join(path, "faiss.index")
        self.metadata_file = os.path.join(path, "metadata.pkl")
        self.course_tracker = os.path.join(path, "course_completion.json")
        
        # 1. Configure Ollama settings
        self.ollama_model = ollama_model
        self.ollama_api_url = f"{ollama_base_url}/api/embeddings"
        print(f"Using Ollama model: {self.ollama_model} and API URL: {self.ollama_api_url}")
        
        # The embedding dimension depends on the Ollama model.
        # 'mxbai-embed-large' has a dimension of 1024.
        # 'nomic-embed-text' has a dimension of 768.
        # Adjust this if you use a different model.
        self.embedding_dim = 768 

        # Create the directory if it doesn't exist
        os.makedirs(self.db_path, exist_ok=True)

        # 2. Load the FAISS index and metadata if they exist, otherwise initialize them
        if os.path.exists(self.index_file) and os.path.exists(self.metadata_file):
            print(f"Loading existing FAISS index from {self.index_file}")
            self.index = faiss.read_index(self.index_file)
            with open(self.metadata_file, 'rb') as f:
                self.metadata = pickle.load(f)
        else:
            print("Initializing new FAISS index and metadata.")
            # Use IndexFlatL2 for simple L2 distance search
            self.index = faiss.IndexFlatL2(self.embedding_dim)
            self.metadata = {}

        print(f"Initialized FAISS index with {self.index.ntotal} vectors.")
        
        # Hybrid retriever (lazy initialization)
        self.hybrid_retriever = None

    def _get_ollama_embedding(self, text: str) -> np.ndarray:
        """Generates an embedding for the given text using the Ollama API."""
        try:
            payload = {
                "model": self.ollama_model,
                "prompt": text
            }
            response = requests.post(self.ollama_api_url, json=payload)
            response.raise_for_status() # Raise an exception for bad status codes
            
            embedding = response.json().get("embedding")
            if not embedding:
                raise ValueError("Ollama API response did not contain an embedding.")
            
            return [embedding] # Return as a list of lists for consistency
        
        except requests.exceptions.RequestException as e:
            print(f"Error calling Ollama API: {e}")
            print(f"Please ensure Ollama is running and the model '{self.ollama_model}' is available.")
            return None
        except ValueError as e:
            print(f"Error processing Ollama response: {e}")
            return None

    def _init_hybrid_retriever(self):
        """Initializes the BM25 index for hybrid search from existing metadata."""
        if not self.metadata:
            print("No metadata available for hybrid retriever initialization.")
            return
        
        corpus = [meta["content"] for meta in self.metadata.values()]
        metadata_keys = list(self.metadata.keys())
        self.hybrid_retriever = HybridRetriever(corpus, metadata_keys)
        print("Hybrid retriever initialized.")

    def save(self):
        """Saves the FAISS index and metadata to disk."""
        print(f"Saving FAISS index to {self.index_file}")
        faiss.write_index(self.index, self.index_file)
        with open(self.metadata_file, 'wb') as f:
            pickle.dump(self.metadata, f)
        # Reset hybrid retriever so it gets rebuilt on next search
        self.hybrid_retriever = None
        print("Save complete.")

    def save_course_manifest_copy(self, manifest: Dict):
        """Saves a copy of the course manifest to the database directory."""
        manifest_path = os.path.join(self.db_path, "course_manifest_copy.json")
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=4)
        print(f"Saved course manifest copy to {manifest_path}.")
    
    def get_course_manifest_copy(self) -> Dict:
        """Retrieves the copy of the course manifest from the database directory."""
        manifest_path = os.path.join(self.db_path, "course_manifest_copy.json")
        if os.path.exists(manifest_path):
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)
            return manifest
        else:
            print("Course manifest copy not found.")
            return {}

    def add_lesson_content(self, content: str, lesson_number: int, source_notebook: str, cell_id: str = None, cell_title: str = None, learning_objectives: list = None, learning_objective_ids: list = None):
        """
        Adds a piece of lesson content to the vector database.

        Args:
            content (str): The text content from the lesson.
            lesson_number (int): The lesson number this content belongs to.
            source_notebook (str): The filename of the notebook this content came from.
        """
        # Create the vector embedding for the content using Ollama
        vector = self._get_ollama_embedding(content)
        if vector is None:
            return # Don't add if embedding failed

        # Add the vector to the FAISS index
        self.index.add(np.array(vector, dtype=np.float32))
        
        # Store the corresponding metadata.
        index_position = self.index.ntotal - 1
        self.metadata[index_position] = {
            "content": content,
            "lesson_number": lesson_number,
            "source": source_notebook,
            "cell_id": cell_id,
            "cell_title": cell_title,
            "learning_objectives": learning_objectives,
        }
        print(f"Added content from '{source_notebook}' (Lesson {lesson_number}).")

    def clear_all(self):
        """Clears the entire FAISS index and metadata."""
        self.index.reset()
        self.metadata = {}
        print("Cleared all data from the vector database.")

    def filter_with_lesson_number(self, query: str, max_lesson_number: int, num_results: int = 2):
        """
        Searches the database for content relevant to a query using metadata filtering.

        Args:
            query (str): The user's question or search term.
            max_lesson_number (int): The maximum lesson number to include in the search.
            num_results (int): The number of relevant documents to return.

        Returns:
            list: A list of the most relevant document contents.
        """
        if self.index.ntotal == 0:
            return []

        # Create embedding for the query using Ollama
        query_vector = self._get_ollama_embedding(query)
        if query_vector is None:
            return []

        # Search the index for more results than we need, to allow for filtering
        search_k = max(10, num_results * 5)
        distances, indices = self.index.search(np.array(query_vector, dtype=np.float32), k=min(search_k, self.index.ntotal))

        # Filter the results based on metadata
        filtered_results = []
        for i in indices[0]:
            if i in self.metadata and self.metadata[i]["lesson_number"] <= max_lesson_number:
                filtered_results.append(self.metadata[i]["content"])
            if len(filtered_results) >= num_results:
                break
        
        return filtered_results
    
    def filter_with_lo_ids(self, query: str, num_results: int = 2, lo_ids: Union[List[str], None] = None):
        """
        Searches the database for content relevant to a query using hybrid search
        (BM25 + dense vector) with learning object ID filtering.

        Args:
            query (str): The user's question or search term.
            lo_ids (list): A list of learning object IDs to include in the search.
            num_results (int): The number of relevant documents to return.
        Returns:
            list: A list of the most relevant document contents.
        """
        if self.index.ntotal == 0:
            return []
        
        # Initialize hybrid retriever if needed (lazy init)
        if self.hybrid_retriever is None and self.metadata:
            self._init_hybrid_retriever()
        
        # Use hybrid search if available, otherwise fall back to pure dense search
        if self.hybrid_retriever is not None:
            return self.hybrid_retriever.hybrid_search(query, num_results, lo_ids, self)
        
        # Fallback: pure dense search (original logic)
        query_vector = self._get_ollama_embedding(query)
        if query_vector is None:
            return []
        
        search_k = max(10, num_results * 5)
        distances, indices = self.index.search(np.array(query_vector, dtype=np.float32), k=min(search_k, self.index.ntotal))
        
        filtered_results = []
        if lo_ids is None:
            for i in indices[0]:
                if i in self.metadata:
                    filtered_results.append(self.metadata[i]["content"])
                if len(filtered_results) >= num_results:
                    break
        else:
            for i in indices[0]:
                if i in self.metadata:
                    lo_list = [lo.get('lo_id') for lo in self.metadata[i].get('learning_objectives', [])]
                    if any(lo_id in lo_list for lo_id in lo_ids):
                        filtered_results.append(self.metadata[i]["content"])
                if len(filtered_results) >= num_results:
                    break
        return filtered_results
    
    def update_course_status(self, lo_id: str, lesson_number: int, is_lesson_completed: bool):
        """
        Updates the course completion status for a given learning object.

        Args:
            lo_id (str): The learning object ID.
            lesson_number (int): The lesson number.
            completed (bool): Whether the lesson is completed.
        """
        if os.path.exists(self.course_tracker):
            with open(self.course_tracker, 'r') as f:
                course_data = json.load(f)
        else:
            course_data = {
                'completed_lessons': dict(),
                'completed_learning_objects': dict()
            }

        if is_lesson_completed:
            course_data['completed_lessons'][str(lesson_number)] = True
        course_data['completed_learning_objects'][lo_id] = True

        with open(self.course_tracker, 'w') as f:
            json.dump(course_data, f)
        print(f"Updated course status for LO ID '{lo_id}'.")

    def is_lo_completed(self, lo_id: str) -> bool:
        """
        Checks if a learning object is marked as completed.

        Args:
            lo_id (str): The learning object ID.
        Returns:
            bool: True if completed, False otherwise.
        """
        if os.path.exists(self.course_tracker):
            with open(self.course_tracker, 'r') as f:
                course_data = json.load(f)
            return course_data['completed_learning_objects'].get(lo_id, False)
        return False
    
    def is_lesson_completed(self, lesson_number: int) -> bool:
        """
        Checks if a lesson is marked as completed.

        Args:
            lesson_number (int): The lesson number.
        Returns:
            bool: True if completed, False otherwise.
        """
        if os.path.exists(self.course_tracker):
            with open(self.course_tracker, 'r') as f:
                course_data = json.load(f)
            return course_data['completed_lessons'].get(str(lesson_number), False)
        return False
    
    def get_parent_lesson_of_lo(self, lo_id: str) -> int | None:
        """
        Retrieves the parent lesson number for a given learning object ID.

        Args:
            lo_id (str): The learning object ID.
        Returns:
            int | None: The parent lesson number, or None if not found.
        """
        
        parent_lesson = -1

        if not self.metadata:
            print("Metadata is empty. Cannot find parent lesson.")
            return None

        for meta in self.metadata.values():
            for learning_object in meta.get('learning_objectives', []):
                if learning_object.get('lo_id') == lo_id:
                    parent_lesson = meta.get('lesson_number', -1)
                    break
        if parent_lesson == -1:
            print(f"Learning Object ID '{lo_id}' not found in metadata.")
            return None
        
        return parent_lesson

    def is_last_learning_object(self, lo_id: str) -> bool:
        """
        Checks if the given learning object is the last one in the course.

        Args:
            lo_id (str): The learning object ID.
        Returns:
            bool: True if it's the last learning object, False otherwise.
        """
        parent_lesson = self.get_parent_lesson_of_lo(lo_id)
        if parent_lesson is None:
            print(f"Cannot determine if LO ID '{lo_id}' is the last learning object.")
            return False
        # check intersection of this lessons's LOs completed with all LOs in this lesson
        lesson_los = [meta['cell_id'] for meta in self.metadata.values() if meta.get('lesson_number') == parent_lesson]
        completed_los = []
        if os.path.exists(self.course_tracker):
            with open(self.course_tracker, 'r') as f:
                course_data = json.load(f)
            completed_los = [lo for lo in lesson_los if course_data['completed_learning_objects'].get(lo, False)]

        return set(lesson_los) == set(completed_los)

    def get_full_tracking_data(self) -> dict:
        """
        Retrieves the entire course tracking data.

        Returns:
            dict: The course tracking data.
        """
        if os.path.exists(self.course_tracker):
            with open(self.course_tracker, 'r') as f:
                course_data = json.load(f)
            return course_data
        return {
            'completed_lessons': dict(),
            'completed_learning_objects': dict()
        }     

    def get_max_lesson_completed(self) -> int:
        """
        Retrieves the highest lesson number that has been completed.

        Returns:
            int: The highest completed lesson number, or 0 if none are completed.
        """
        if os.path.exists(self.course_tracker):
            with open(self.course_tracker, 'r') as f:
                course_data = json.load(f)
            completed_lessons = [int(ln) for ln, completed in course_data['completed_lessons'].items() if completed]
            return max(completed_lessons) if completed_lessons else 0
        return 0

    def get_completed_lo_ids(self) -> list:
        """
        Retrieves a list of all completed learning object IDs.

        Returns:
            list: A list of completed learning object IDs.
        """
        if os.path.exists(self.course_tracker):
            with open(self.course_tracker, 'r') as f:
                course_data = json.load(f)
            return [lo_id for lo_id, completed in course_data['completed_learning_objects'].items() if completed]
        return []
        
    
def get_db_manager_instance(**parameter_overrides):
    # 1. Find the project root dynamically, starting from the notebook's dir
    try:
        # This will walk up from .../LO-1.2/ and find .../course/
        project_root = find_project_root()
    except FileNotFoundError as e:
        # You can decide how to handle this - either raise the error
        # or fall back to a less reliable method. Raising is clearer.
        print(f"Error: {e}")
        raise

    db_path = str(project_root) + '/data/vector_db'
    print("Using Vector DB Path:", db_path)
    initialize_parameters = {
        'path': db_path,
        'ollama_model':  'nomic-embed-text',
        'ollama_base_url': os.getenv("OLLAMA_API_URL", "http://localhost:11434")
    }
    initialize_parameters.update(parameter_overrides)
    return VectorDBManager(**initialize_parameters)

# --- Example Usage ---
if __name__ == "__main__":
    db_path = "./faiss_db_test_ollama"
    # Clean up previous runs for a fresh start
    if os.path.exists(db_path):
        import shutil
        shutil.rmtree(db_path)
        
    # 1. Initialize the manager. This will create a 'faiss_db_test_ollama' folder.
    db_manager = VectorDBManager(path=db_path)
    
    # 2. Add content for Lesson 1 & 2
    db_manager.add_lesson_content(
        "A qubit is the basic unit of quantum information. Unlike a classical bit, a qubit can be in a superposition of both 0 and 1 at the same time.",
        lesson_number=1,
        source_notebook="01-Qubits.ipynb"
    )
    db_manager.add_lesson_content(
        "The Hadamard gate is a fundamental quantum gate. It takes a qubit in state |0> and puts it into an equal superposition state, |+>.",
        lesson_number=2,
        source_notebook="02-Gates.ipynb"
    )
    
    # 3. Save the database to disk
    db_manager.save()

    print("\n" + "="*20 + "\n")

    # 4. Simulate a search for a student who has only completed Lesson 1
    print("Searching for a student on Lesson 1 who asks about the 'Hadamard gate':")
    student_query = "What is the Hadamard gate?"
    student_progress = 1
    search_results = db_manager.filter_with_lesson_number(student_query, student_progress)
    
    if search_results:
        print("Found results:")
        for result in search_results:
            print(f"- {result}")
    else:
        print("Found NO results. The student hasn't learned about this yet!")
        
    print("\n" + "="*20 + "\n")

    # 5. Simulate a search for a student who has completed Lesson 2
    print("Searching for a student on Lesson 2 who asks about the 'Hadamard gate':")
    student_progress = 2
    search_results = db_manager.filter_with_lesson_number(student_query, student_progress)

    if search_results:
        print("Found results:")
        for result in search_results:
            print(f"- {result}")
    else:
        print("Found NO results.")

    # cleanup after test
    if os.path.exists(db_path):
        import shutil
        shutil.rmtree(db_path)


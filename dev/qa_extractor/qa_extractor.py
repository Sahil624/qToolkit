import os
import json
import time
import csv
import datetime
import pandas as pd
import nbformat
import google.generativeai as genai
from tqdm import tqdm
from collections import deque

# --- CONFIGURATION ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "YOUR_GEMINI_API_KEY")
ROOT_DIRECTORY = "../content"
OUTPUT_CSV_FILE = "generated_qa_dataset.csv"
TRACKING_JSON_FILE = "tracking.json" # <-- New tracking file
REQUESTS_PER_MINUTE = 13
# --- END CONFIGURATION ---

class RateLimiter:
    """A class to handle proactive rate limiting."""
    def __init__(self, requests_per_minute):
        self.max_requests = requests_per_minute
        self.time_window = 60
        self.request_timestamps = deque()

    def wait(self):
        """Pauses execution if the request rate would exceed the limit."""
        while True:
            current_time = time.monotonic()
            while self.request_timestamps and self.request_timestamps[0] <= current_time - self.time_window:
                self.request_timestamps.popleft()
            if len(self.request_timestamps) < self.max_requests:
                break
            time_to_wait = self.request_timestamps[0] - (current_time - self.time_window)
            if time_to_wait > 0:
                print(f"\n[RateLimiter] Proactively waiting for {time_to_wait + 0.1:.2f} seconds...")
                time.sleep(time_to_wait + 0.1)
        self.request_timestamps.append(time.monotonic())

# --- NEW HELPER FUNCTIONS FOR TRACKING AND REAL-TIME WRITING ---

def initialize_tracker(all_notebook_paths):
    """Loads, updates, and returns the tracker data from the JSON file."""
    tracker_data = {}
    if os.path.exists(TRACKING_JSON_FILE):
        with open(TRACKING_JSON_FILE, 'r') as f:
            try:
                tracker_data = json.load(f)
            except json.JSONDecodeError:
                print(f"[Warning] Could not decode {TRACKING_JSON_FILE}. Starting fresh.")
    
    # Add any new notebooks found on disk to the tracker
    new_files_found = False
    for path in all_notebook_paths:
        if path not in tracker_data:
            tracker_data[path] = {"enabled": True, "qa_generated": 0, "last_processed_utc": None}
            new_files_found = True
            
    if new_files_found:
        print(f"Found new notebooks. Updating {TRACKING_JSON_FILE}.")
        save_tracker(tracker_data)
        
    return tracker_data

def save_tracker(tracker_data):
    """Saves the tracker dictionary to the JSON file."""
    with open(TRACKING_JSON_FILE, 'w') as f:
        json.dump(tracker_data, f, indent=4)

def append_to_csv(data_dict, csv_filepath):
    """Appends a dictionary to a CSV file, creating the header if necessary."""
    file_exists = os.path.isfile(csv_filepath)
    # Ensure all required fields are present
    fieldnames = ['source_notebook', 'topic', 'difficulty', 'tags', 'question', 'answer', 'interaction_type']
    
    with open(csv_filepath, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists or os.path.getsize(csv_filepath) == 0:
            writer.writeheader()
        writer.writerow({k: data_dict.get(k, "") for k in fieldnames})

# --- (Functions find_notebooks, extract_content, generate_qa are unchanged) ---
try:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-2.5-flash-lite')
except Exception as e:
    print(f"Error configuring Gemini API: {e}")
    exit()

def find_notebooks(root_dir):
    """Recursively finds all .ipynb files, ignoring .ipynb_checkpoints folders."""
    notebook_files = []
    for dirpath, dirnames, filenames in os.walk(root_dir):
        # --- This is the logic to ignore checkpoint folders ---
        if '.ipynb_checkpoints' in dirnames:
            dirnames.remove('.ipynb_checkpoints')
        # -----------------------------------------------------------
        
        for filename in filenames:
            if filename.endswith(".ipynb"):
                notebook_files.append(os.path.join(dirpath, filename))
    return notebook_files

def extract_content_from_notebook(notebook_path):
    try:
        with open(notebook_path, 'r', encoding='utf-8') as f:
            nb = nbformat.read(f, as_version=4)
    except Exception as e:
        print(f"  [Warning] Could not read or parse notebook {notebook_path}: {e}")
        return []
    return [
        {'type': 'markdown' if cell.cell_type == 'markdown' else 'code', 'content': cell.source}
        for cell in nb.cells if cell.source.strip() and len(cell.source.split()) > 10
    ]

def generate_qa_with_gemini(content_chunk):
    prompt_template = f"""
        You are an AI assistant role-playing as a novice student in a study group. Your goal is to create practice questions and answers based on the provided study material.

        The interactions should sound like one beginner student talking to another. Avoid expert language and keep the tone informal, simple, and encouraging. It's a conversation between equals who are learning together.

        Based on the content chunk below, generate 2-3 interactions. For each interaction, you must generate a mix of two types:
        1.  **student_to_peer**: A student asking you (the peer) for help or clarification. The 'answer' is your simple explanation.
        2.  **peer_to_student**: You (the peer) asking a question to check the other student's understanding. The 'answer' is what a correct response from the student would look like.

        You MUST return the output as a single, valid JSON object with no extra text or explanations.
        The JSON object must contain a single key "qa_pairs", which is a list of dictionaries.
        Each dictionary MUST have these keys:
        - "topic": A concise topic for the interaction.
        - "difficulty": Must be "Beginner", "Intermediate", or "Advanced".
        - "tags": A list of relevant lowercase keywords.
        - "interaction_type": Must be either "student_to_peer" or "peer_to_student".
        - "question": The question being asked.
        - "answer": The corresponding simple answer or the expected correct response.

        Here is an example of the desired output format and tone:
        ---
        EXAMPLE:
        {{
        "qa_pairs": [
            {{
            "topic": "Python Imports",
            "difficulty": "Beginner",
            "tags": ["python", "import", "basics"],
            "interaction_type": "student_to_peer",
            "question": "Hey, why do we have to write `import numpy as np`? Can't we just use it?",
            "answer": "Oh, it's because Python doesn't load every tool automatically to save memory. So `import numpy` tells it to get the numpy library ready, and `as np` is just a shorter nickname so we don't have to type `numpy` every time."
            }},
            {{
            "topic": "Python Imports",
            "difficulty": "Beginner",
            "tags": ["python", "import", "basics"],
            "interaction_type": "peer_to_student",
            "question": "Okay, so what do you think would happen if we tried to use a numpy function *before* we imported it?",
            "answer": "The program would probably crash and give us a NameError, because it wouldn't know what 'np' or 'numpy' is yet."
            }}
        ]
        }}
        ---

        Now, analyze the following content chunk and generate a new set of interactions.

        CONTENT CHUNK:
        ---
        {content_chunk}
        ---
    """
    max_retries = 3
    backoff_seconds = 5
    for attempt in range(max_retries):
        try:
            response = model.generate_content(prompt_template)
            json_text = response.text.strip().replace("```json", "").replace("```", "")
            return json.loads(json_text)
        except Exception as e:
            if "rate limit" in str(e).lower():
                if attempt < max_retries - 1:
                    print(f"  [Info] Reactive fallback: Rate limit hit. Retrying in {backoff_seconds}s...")
                    time.sleep(backoff_seconds)
                    backoff_seconds *= 2
                else:
                    print(f"  [Warning] Max retries reached for rate-limited request.")
            else:
                print(f"  [Warning] An unexpected error occurred: {e}")
                return None
    return None


def main():
    """Main function with real-time tracking and writing."""
    print("Initializing...")
    all_notebook_paths = find_notebooks(ROOT_DIRECTORY)
    if not all_notebook_paths:
        print("No notebooks (.ipynb files) found. Exiting.")
        return
        
    tracker_data = initialize_tracker(all_notebook_paths)
    
    notebooks_to_process = [
        path for path, data in tracker_data.items() if data.get("enabled", True)
    ]

    # notebooks_to_process = notebooks_to_process[:1]
    
    skipped_count = len(all_notebook_paths) - len(notebooks_to_process)
    
    print(f"Found {len(all_notebook_paths)} total notebooks. Processing {len(notebooks_to_process)} enabled notebooks.")
    if skipped_count > 0:
        print(f"Skipping {skipped_count} disabled notebooks (check {TRACKING_JSON_FILE}).")

    limiter = RateLimiter(REQUESTS_PER_MINUTE)
    
    for nb_path in tqdm(notebooks_to_process, desc="Overall Progress"):
        tqdm.write(f"\nProcessing: {nb_path}")
        content_chunks = extract_content_from_notebook(nb_path)
        
        if not content_chunks:
            continue
        
        qa_generated_this_run = 0
        for chunk in tqdm(content_chunks, desc=f"  - Chunks from {os.path.basename(nb_path)}", leave=False):
            limiter.wait()
            generated_data = generate_qa_with_gemini(chunk['content'])
            
            if generated_data and 'qa_pairs' in generated_data:
                for qa_pair in generated_data['qa_pairs']:
                    if all(key in qa_pair for key in ["topic", "difficulty", "tags", "question", "answer"]):
                        qa_pair['source_notebook'] = nb_path # Add source notebook
                        append_to_csv(qa_pair, OUTPUT_CSV_FILE)
                        qa_generated_this_run += 1
        
        # --- Update and save tracker after each notebook is fully processed ---
        tqdm.write(f"Generated {qa_generated_this_run} Q&A pairs for this file.")
        tracker_data[nb_path]['qa_generated'] += qa_generated_this_run
        tracker_data[nb_path]['last_processed_utc'] = datetime.datetime.utcnow().isoformat()
        save_tracker(tracker_data)
        tqdm.write(f"Tracker file '{TRACKING_JSON_FILE}' updated.")

    print(f"\n✅ Processing complete. Results are in '{OUTPUT_CSV_FILE}' and progress is saved in '{TRACKING_JSON_FILE}'.")

if __name__ == "__main__":
    if GEMINI_API_KEY == "YOUR_GEMINI_API_KEY":
        print("!!! IMPORTANT !!!\nPlease set your GEMINI_API_KEY.")
    else:
        main()
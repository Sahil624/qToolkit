import os
import json
import re
import yaml
import shutil
import sys
import nbformat  # <-- Added: The official library for reading notebooks

# Ensure vector_db_manager is importable
try:
    from .vector_db_manager import VectorDBManager
except ImportError:
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from dev.v_db.vector_db_manager import VectorDBManager

def load_yaml_metadata(metadata_path: str) -> dict | None:
    """Loads a YAML file and returns its content."""
    if not os.path.exists(metadata_path):
        print(f"Warning: Metadata file not found at {metadata_path}")
        return None
    try:
        with open(metadata_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except yaml.YAMLError as e:
        print(f"Error parsing YAML file {metadata_path}: {e}")
        return None

def build_metadata_lookups(yaml_data: dict) -> (dict, dict):
    """
    Parses the raw YAML data to create two fast lookup maps:
    1. A map of: cell_id -> [list of LO objects that cover it]
    2. A map of: cell_id -> {cell_title, ...}
    """
    cell_to_lo_map = {}
    lo_tree = yaml_data.get('learning_objective_tree', [])
    
    for lo in lo_tree:
        lo_id = lo.get('lo_id')
        if not lo_id:
            continue
        
        lo_metadata = {
            "lo_id": lo_id,
            "lo_summary": lo.get('summary'),
            "lo_details": lo.get('learning_objectives', []), 
            "lo_prerequisites": lo.get('prerequisites', []),
            "difficulty": lo.get('difficulty'),
            "keywords": lo.get('keywords', [])
        }
        
        for cell_id in lo.get('covered_by', []):
            if cell_id not in cell_to_lo_map:
                cell_to_lo_map[cell_id] = []
            cell_to_lo_map[cell_id].append(lo_metadata)

    cell_details_map = {
        cell.get('cell_id'): {
            "cell_title": cell.get('title'),
            "cell_order": cell.get('order')
        }
        for cell in yaml_data.get('cell_metadata', [])
        if cell.get('cell_id')
    }
    
    return cell_to_lo_map, cell_details_map

def index_course_content(root_folder: str, db_manager: VectorDBManager):
    """
    Recursively scans a folder for .ipynb files, finds their matching .yaml
    metadata, and adds their rich content to the vector database.
    """
    for dirpath, dirnames, filenames in os.walk(root_folder):
        if '.ipynb_checkpoints' in dirnames:
            dirnames.remove('.ipynb_checkpoints')

        for filename in sorted(filenames):
            if not filename.endswith(".ipynb"):
                continue

            # --- 1. Find and Parse Metadata ---
            base_name, _ = os.path.splitext(filename)
            notebook_path = os.path.join(dirpath, filename)
            metadata_path = os.path.join(dirpath, ".metadata.yaml")
            
            yaml_data = load_yaml_metadata(metadata_path)
            if not yaml_data:
                print(f"Skipping notebook {filename} due to missing metadata.")
                continue
                
            cell_to_lo_map, cell_details_map = build_metadata_lookups(yaml_data)

            # --- 2. Get Ordered List of YAML text cells ---
            all_yaml_cells = yaml_data.get('cell_metadata', [])
            ordered_yaml_text_cells = sorted(
                all_yaml_cells,
                key=lambda x: x.get('order', 0)
            )

            # --- 3. Infer Lesson Number (for Peer Agent filter) ---
            match = re.match(r'^(\d+)', filename)
            if not match:
                print(f"Warning: Could not infer lesson number for '{filename}'. Skipping.")
                continue
            lesson_number = int(match.group(1))
            
            print(f"Processing: {notebook_path} as Lesson {lesson_number}")

            # --- 4. Parse Notebook and Get Ordered List of Markdown Cells ---
            try:
                with open(notebook_path, 'r', encoding='utf-8') as f:
                    # Use nbformat.read to parse the notebook
                    notebook = nbformat.read(f, as_version=4)
                
                # Get all markdown cells from the notebook in their physical order
                ordered_ipynb_markdown_cells = [
                    cell for cell in notebook.cells if cell.cell_type == 'markdown'
                ]

                # --- 5. Link YAML cells to Notebook cells by order ---
                if len(ordered_yaml_text_cells) != len(ordered_ipynb_markdown_cells):
                    print(f"  Warning: Mismatch! YAML has {len(ordered_yaml_text_cells)} text cells, but .ipynb has {len(ordered_ipynb_markdown_cells)} markdown cells. Skipping.")
                    

                    for cell in ordered_ipynb_markdown_cells:
                        print(f"  Markdown Cell: {cell.source[:30]}...")  # Print first 30 chars
                        print("-" * 20)
                    sys.exit(1)
                
                cells_indexed = 0
                for yaml_cell, ipynb_cell in zip(ordered_yaml_text_cells, ordered_ipynb_markdown_cells):
                    
                    cell_id = yaml_cell.get('cell_id')
                    content = ipynb_cell.source  # nbformat gives source as a single string
                    
                    if not content.strip() or not cell_id:
                        continue

                    # --- 6. Assemble the Full Metadata Object (The Schema) ---
                    lo_list = cell_to_lo_map.get(cell_id, [])
                    cell_details = cell_details_map.get(cell_id, {})

                    db_metadata = {
                        "lesson_number": lesson_number,
                        "source_notebook": filename,
                        "cell_id": cell_id,
                        "cell_title": cell_details.get('cell_title'),
                        "learning_objectives": lo_list # List of LO objects
                    }
                    
                    # --- 7. Add to the Database ---
                    db_manager.add_lesson_content(
                        content=content,
                        **db_metadata
                    )
                    cells_indexed += 1
                
                print(f"  Found and indexed {cells_indexed} linked markdown cells.")

            except Exception as e:
                print(f"Error reading or parsing notebook {notebook_path}: {e}")

# --- Example Usage ---
if __name__ == "__main__":
    # --- 1. Setup a dummy course structure for demonstration ---
    COURSE_DIR = "./course_content"
    DB_PATH = "./faiss_course_db"

    if os.path.exists(COURSE_DIR): shutil.rmtree(COURSE_DIR)
    if os.path.exists(DB_PATH): shutil.rmtree(DB_PATH)
    os.makedirs(os.path.join(COURSE_DIR, "module1"))
    
    # --- Dummy Notebook 1 ---
    # NOTE: No 'cell_id' in metadata here. We rely on order.
    notebook1_content = {
        "cells": [
            {"cell_type": "markdown", "source": ["# Lesson 1: The Qubit\n", "A qubit is the basic unit..."], "metadata": {}},
            {"cell_type": "markdown", "source": ["# 1.7 Superposition\n", "Superposition is key."], "metadata": {}},
            {"cell_type": "code", "source": ["print('Hello')"], "metadata": {}}
        ], "nbformat": 4, "nbformat_minor": 2
    }
    with open(os.path.join(COURSE_DIR, "module1/01_qubits.ipynb"), 'w') as f:
        json.dump(notebook1_content, f)

    # --- Dummy Metadata 1 (YAML) ---
    # This YAML lists the two markdown cells in order
    yaml_content = """
learning_objective_tree:
  - lo_id: "LO-1.1"
    summary: "Modeling with kets"
    keywords: ["qubit", "ket notation", "vector"]
    covered_by: ["QBIT-01-S1-1"]
  - lo_id: "LO-1.3"
    summary: "Understanding superposition"
    keywords: ["superposition", "quantum state"]
    covered_by: ["QBIT-01-S1-7"]
cell_metadata:
  - cell_id: "QBIT-01-S1-1"
    order: 1
    cell_type: "text"
    title: "1.1 Classical Bits"
  - cell_id: "QBIT-01-S1-7"
    order: 2
    cell_type: "text"
    title: "1.7 Superposition"
    """
    with open(os.path.join(COURSE_DIR, "module1/01_qubits.yaml"), 'w') as f:
        f.write(yaml_content)

    print("Created dummy course structure for testing.")
    print("-" * 30)

    # --- 2. Initialize the DB Manager and run the indexing ---
    db_manager = VectorDBManager(path=DB_PATH)
    print("Starting to index course content...")
    index_course_content(COURSE_DIR, db_manager)
    
    # --- 3. Save the newly populated database ---
    db_manager.save()
    print("-" * 30)

    # --- 4. Verify the indexing with a search ---
    print("Verifying search (query: 'qubit', lesson: 1):")
    # We are calling the old add_lesson_content, so this will fail
    # We need to update vector_db_manager.py
    results = db_manager.search_with_filter("What is a qubit?", max_lesson_number=1)
    print(f"Search Results: {results}")

    print("\nVerifying search (query: 'superposition', lesson: 1):")
    results = db_manager.search_with_filter("What is superposition?", max_lesson_number=1)
    print(f"Search Results: {results}")

    # Clean up dummy files
    shutil.rmtree(COURSE_DIR)
    shutil.rmtree(DB_PATH)
    print("\nCleaned up dummy files.")
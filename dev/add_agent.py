import nbformat
import re
import os
import sys
import shutil

def extract_notebook_paths(master_notebook_path: str) -> list[str]:
    """
    Parses a master notebook file to find all relative links to other notebooks
    within a Markdown table.
    """
    print(f"Reading master notebook: {master_notebook_path}")
    paths = []
    regex = r'\((content/[^)]+\.ipynb)\)'

    try:
        with open(master_notebook_path, 'r', encoding='utf-8') as f:
            notebook = nbformat.read(f, as_version=4)
        
        for cell in notebook.cells:
            if cell.cell_type == 'markdown':
                found_paths = re.findall(regex, cell.source)
                if found_paths:
                    paths.extend(found_paths)
        
        print(f"Found {len(paths)} lesson notebook links.")
        return paths
    except FileNotFoundError:
        print(f"ERROR: Master notebook not found at '{master_notebook_path}'")
        return []

def inject_cell_into_notebook(notebook_path: str, markdown_content: str, code_template: str, agent_script_path: str):
    """
    Inserts a markdown and a code cell after the first cell in a notebook,
    creating a backup first and calculating the correct relative path.
    """
    if not os.path.exists(notebook_path):
        print(f"  - WARNING: Notebook not found at '{notebook_path}'. Skipping.")
        return

    # --- Calculate correct relative path for the %run command ---
    notebook_dir = os.path.dirname(notebook_path)
    if not notebook_dir:
        notebook_dir = '.'
    relative_agent_path = os.path.relpath(agent_script_path, start=notebook_dir)
    code_content = code_template.format(agent_path=relative_agent_path)
    # ---

    try:
        with open(notebook_path, 'r', encoding='utf-8') as f:
            notebook = nbformat.read(f, as_version=4)

        for cell in notebook.cells:
            if cell.cell_type == 'code' and f"%run" in cell.source and 'peer_agent.py' in cell.source:
                print(f"  - Agent cell already exists in '{os.path.basename(notebook_path)}'. Skipping.")
                return

        backup_path = notebook_path + ".bak"
        if not os.path.exists(backup_path):
            print(f"  - Creating backup: {os.path.basename(backup_path)}")
            shutil.copy2(notebook_path, backup_path)

        print(f"  - Injecting agent cell into '{os.path.basename(notebook_path)}'...")
        
        markdown_cell = nbformat.v4.new_markdown_cell(markdown_content)
        code_cell = nbformat.v4.new_code_cell(code_content)
        
        # Insert cells after the first cell (at index 1 and 2)
        if len(notebook.cells) > 0:
            notebook.cells.insert(1, markdown_cell)
            notebook.cells.insert(2, code_cell)
        else: # If notebook is empty, just append
            notebook.cells.append(markdown_cell)
            notebook.cells.append(code_cell)
        
        with open(notebook_path, 'w', encoding='utf-8') as f:
            nbformat.write(notebook, f)
            
        print(f"  - Successfully updated '{os.path.basename(notebook_path)}'.")

    except Exception as e:
        print(f"  - ERROR processing '{notebook_path}': {e}")

def restore_notebook_from_backup(notebook_path: str):
    """Restores a notebook from its .bak file."""
    backup_path = notebook_path + ".bak"
    if os.path.exists(backup_path):
        try:
            print(f"  - Restoring '{os.path.basename(notebook_path)}' from backup...")
            shutil.move(backup_path, notebook_path)
            print(f"  - Restore successful.")
        except Exception as e:
            print(f"  - ERROR restoring '{notebook_path}': {e}")

def remove_backup(notebook_path: str):
    """Removes a .bak file for a given notebook."""
    backup_path = notebook_path + ".bak"
    if os.path.exists(backup_path):
        try:
            print(f"  - Removing backup for '{os.path.basename(notebook_path)}'...")
            os.remove(backup_path)
            print(f"  - Backup removed.")
        except Exception as e:
            print(f"  - ERROR removing backup for '{notebook_path}': {e}")

def main():
    """Main function to run the injection, restore, or clean process."""
    master_notebook = "master.ipynb"
    agent_script_path = "dev/v_db/peer_agent.py"
    
    lesson_paths = extract_notebook_paths(master_notebook)
    if not lesson_paths:
        print("\nNo lesson notebooks found. Exiting.")
        return

    if '--restore' in sys.argv:
        print("\n--- Restore Mode ---")
        for path in lesson_paths:
            restore_notebook_from_backup(path)
        print("\nRestore process complete.")
        return

    if '--clean' in sys.argv:
        print("\n--- Clean Mode ---")
        for path in lesson_paths:
            remove_backup(path)
        print("\nBackup cleaning complete.")
        return

    # --- Default Injection Mode ---
    print("\n--- Injection Mode ---")
    markdown_to_add = (
        "## 🤔 Got a Question? Ask Your Peer Agent!\n\n"
        "Hey there! This next cell is a special one. Running it will call up your **AI Peer Agent**—it's like having a study buddy right here in the notebook with you.\n\n"
        "**What can it do?**\n"
        "* It can try to answer questions you have about the concepts we've covered so far.\n"
        "* It only knows what we've learned up to this point, so it won't spoil future topics.\n"
        "* It explains things from a student's perspective, just like a real classmate would.\n\n"
        "Don't hesitate to use it if you're feeling a bit stuck. Just run the cell below and type in your question!"
    )
    code_template = (
        "# This magic command will run the peer agent script and display the UI\n"
        "%run {agent_path}"
    )
    
    for path in lesson_paths:
        inject_cell_into_notebook(path, markdown_to_add, code_template, agent_script_path)
        
    print("\nInjection process complete.")

if __name__ == "__main__":
    main()


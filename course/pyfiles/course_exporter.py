import os
import shutil
import nbformat
import yaml
from typing import List, Dict, Tuple, Any, Callable
from datetime import datetime

# --- Dependency Check ---
# This file handles all notebook and metadata operations
_dependencies_met = True
try:
    import nbformat
except ImportError:
    print("="*50)
    print("ERROR (from course_exporter.py): Missing Required Library")
    print("The 'nbformat' library is not found. This is required for exporting notebooks.")
    print("Please install it by running: pip install nbformat")
    print("="*50)
    _dependencies_met = False

try:
    import yaml
except ImportError:
    print("="*50)
    print("ERROR (from course_exporter.py): Missing Required Library")
    print("The 'PyYAML' library is not found. This is required for reading metadata.")
    print("Please install it by running: pip install PyYAML")
    print("="*50)
    _dependencies_met = False
# --- End Dependency Check ---


# --- Configuration ---
GENERATED_COURSE_DIR = 'generated_course'

# --- UPDATED: Helper function to generate self-contained nav code ---
def _create_nav_code(
    current_lo_id: str,
    current_summary: str,
    current_index: int,
    total_lessons: int,
    prev_lo_id: str or None,
    next_lo_id: str or None
) -> str:
    """
    Creates a self-contained string of Python code that will
    render the navigation widgets AND a custom theme.
    """
    
    # --- URL Generation ---
    prev_url = f"../{prev_lo_id}/{prev_lo_id}.ipynb" if prev_lo_id else ""
    next_url = f"../{next_lo_id}/{next_lo_id}.ipynb" if next_lo_id else ""
    
    # --- FIX: Sanitize the summary string for injection ---
    sanitized_summary = current_summary.replace('"', '`')
    sanitized_summary = sanitized_summary.replace('\\', '\\\\')
    sanitized_summary = ' '.join(sanitized_summary.split())
    
    current_page_text = f"Lesson {current_index + 1} of {total_lessons}: {sanitized_summary}"
    
    next_button_label = "Mark as Complete & Go to Next"
    next_button_disabled = 'False' if next_lo_id else 'True'
    
    if next_lo_id is None:
        next_button_label = "Course Complete!"
        
    # --- NEW: Simplified CSS for Margins ---
    # This code will be injected into the notebook.
    nav_code = f"""
# --- Auto-generated Course Navigation & Theme ---
try:
    import ipywidgets as widgets
    from IPython.display import display, HTML, clear_output
    from datetime import datetime
    import os

    # --- Injected Data ---
    _CURRENT_LO_ID = "{current_lo_id}"
    _PREV_URL = '{prev_url}'
    _NEXT_URL = '{next_url}'
    _CURRENT_PAGE_TEXT = "{current_page_text}"
    _NEXT_BUTTON_LABEL = "{next_button_label}"
    _NEXT_BUTTON_DISABLED = {next_button_disabled}

    # --- 1. THEME: Inject CSS for horizontal margins AND sticky header ---
    _MARGIN_CSS = \"""
    <style>
        /* Target main Voila/Jupyter content area */
        body, .jp-Notebook, .voila-notebook-container {{
            /* Add horizontal margins by setting max-width and centering */
            max-width: 960px !important;
            margin: 0 auto !important; /* Center the block */
            padding-left: 20px !important; /* Add some side padding */
            padding-right: 20px !important;
        }}
        
        /* Ensure the injected code cell itself doesn't look weird */
        div.code_cell .input {{
            /* Hide the border of the nav code cell */
            border: none;
        }}
        
        /* --- NEW: Sticky Header CSS --- */
        .sticky-nav-header {{
            position: sticky !important;
            top: 0 !important;
            z-index: 1000 !important;
            /* Match default Voila background for light theme */
            background-color: #ffffff !important; 
            /* Add a subtle shadow to lift it off the page */
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            /* Ensure it spans the full width of the centered content */
            width: 100%; 
        }}
        /* Add padding to the top of the content below the header */
        .jp-Cell {{
            /* Adjust this padding if header height changes */
             /* padding-top: 80px; */ /* Might not be needed if sticky is on wrapper */
        }}
        
    </style>
    \"""
    
    # --- 2. HEADER: Define Widgets ---
    # Use h2 for the title, let it inherit default color
    header_title = widgets.HTML(f"<h2 style='margin: 0;'>{{_CURRENT_PAGE_TEXT}}</h2>")
    log_output = widgets.Output()

    import jupyter_server.serverapp

    # Get a list of all running servers
    servers = list(jupyter_server.serverapp.list_running_servers())

    if not servers:
        raise RuntimeError("No running Jupyter server found!")

    # Get info for the first server
    server_info = servers[0]
    host = server_info['hostname']
    port = server_info['port']
    base_url = server_info['base_url'] # e.g., '/' or '/lab'
    token = server_info['token']

    # Clean up base_url (it sometimes has a trailing /)
    if not base_url.endswith('/'):
        base_url += '/'

    # This is the base URL for any API calls
    api_base_url = f"http://{{host}}:{{port}}{{base_url}}"

    api_base_url += '/' if not api_base_url.endswith('/') else ''
            
    def make_course_complete_request():
        # import requests
        # try:
        #     # Assuming the server is running on localhost and default port
        #     url = api_base_url + "q-toolkit/track_course"
        #     payload = {{"lo_id": _CURRENT_LO_ID}}
        #     headers = {{
        #         "Content-Type": "application/json",
        #         "Authorization": "token " + token
        #     }}
        #     response = requests.post(url, json=payload, headers=headers)
        #     if response.status_code == 200:
        #         return True
        #     else:
        #         print(f"Failed to mark course complete. Status code: {{response.status_code}}")
        #         return False
        # except Exception as e:
        #     print(f"Error making course complete request: {{e}}")
        #     return False
        from edu_agents.course_completed import mark_course_if_completed
        mark_course_if_completed(_CURRENT_LO_ID)

    # --- 3. Button Callbacks ---
    def on_complete_button_clicked(b):
        with log_output:
            clear_output(wait=True)
            log_message = f"RECORD: Student completed LO: {{_CURRENT_LO_ID}} at {{{{datetime.now().isoformat()}}}}"
            print(log_message) # To Voila console

            try:
                make_course_complete_request()
                print("Course progress updated successfully.")
            except Exception as e:
                print(f"Error updating course progress: {{e}}")

            # TODO: Detect if running in Voila
            # is_voila = os.environ.get('VOILA_APP_NAME', '') != ''
            # if is_voila:          
            if _NEXT_URL:
                # --- FIX: Directly embed the URL into the JavaScript ---
                # No intermediate Python variable needed.
                # Ensure the URL is correctly quoted for JavaScript.
                js_redirect_code = f"window.location.href = '{{_NEXT_URL}}';" 
                display(HTML(f\"""
                    <p style='color: green; font-weight: bold;'>Lesson marked complete! Redirecting...</p>
                    <script type='text/javascript'>
                    // Immediately execute the redirect
                    {{js_redirect_code}}
                    </script>
                \"""))
                b.disabled = True
            else:
                display(HTML(f"<h3 style='color: green; font-weight: bold;'>Course Complete!</h3>"))
                b.disabled = True

    # --- 4. Assemble UI ---
    next_button = widgets.Button(
        description=_NEXT_BUTTON_LABEL,
        button_style='success',
        icon='check',
        disabled=_NEXT_BUTTON_DISABLED,
        layout=widgets.Layout(width='280px')
    )
    next_button.on_click(on_complete_button_clicked)
    
    # Create the header content
    header_box = widgets.HBox([
        header_title,
        widgets.Layout(flex='1'), # Spacer
        next_button
    ], layout=widgets.Layout(
        align_items='center', 
        border_bottom='1px solid #ccc',  # Light gray border
        padding='10px',
        # Removed margin - margin applied via sticky wrapper
    ))
    
    # --- NEW: Wrap header in a Box with the sticky class ---
    header_wrapper = widgets.Box(
        children=[header_box],
        # layout=widgets.Layout(margin='0 0 20px 0') # Apply margin here if needed
    )
    header_wrapper.add_class("sticky-nav-header")
    
    nav_ui = widgets.VBox([
        header_wrapper, # Use the wrapper here
        log_output
    ])
    
    # --- 5. Display the Theme and the UI ---
    display(HTML(_MARGIN_CSS))
    display(nav_ui)

except ImportError:
    print("Error: Could not load navigation widgets. Please ensure 'ipywidgets' is installed.")
except Exception as e:
    print(f"An error occurred while rendering navigation: {{{{e}}}}")
"""
    return nav_code

# --- Main Export Function (Unchanged, but references new _create_nav_code) ---

def export_course_to_ipynb(
    # --- NEW PARAMETERS ---
    generation_params: Dict,
    unmet_targets: List[str],
    # --- Original Parameters ---
    selected_lo_ids: List[str],
    lo_object_map: Dict[str, Dict],
    cell_details_map: Dict[str, Dict],
    log_function: Callable[[str], None] = print
) -> Tuple[bool, List[str]]:
    """
    For each selected LO, creates a new .ipynb file containing only
    the cells relevant to that LO, as defined in the metadata.
    
    Also creates a _course_manifest.yaml file with generation details.
    
    Returns:
        - (bool): True on success, False on failure.
        - (List[str]): A list of paths to the generated directories.
    """
    
    if not _dependencies_met:
        log_function("Error: Missing required libraries (nbformat or PyYAML). Cannot export.")
        log_function("Please install missing libraries and restart the kernel.")
        return False, []
    
    if not selected_lo_ids:
        log_function("Error: No course selected to export.")
        return False, []

    # 1. Create/Clear the main output directory
    try:
        if os.path.exists(GENERATED_COURSE_DIR):
            shutil.rmtree(GENERATED_COURSE_DIR) # Clear old directory
        os.makedirs(GENERATED_COURSE_DIR)
    except Exception as e:
        log_function(f"Error creating output directory: {e}")
        return False, []

    # 2. Create a cache for loaded source notebooks
    source_notebook_cache: Dict[str, Any] = {}
    
    # 3. Process each LO in the generated course
    export_paths = []
    total_lessons = len(selected_lo_ids)
    
    # --- Create the main course manifest file FIRST ---
    try:
        manifest = {
            "generation_timestamp": datetime.now().isoformat(),
            "generation_parameters": generation_params,
            "course_chronology": selected_lo_ids,
            "topics_included_count": len(selected_lo_ids),
            "topics_ignored_due_to_time": unmet_targets,
            "topics_ignored_count": len(unmet_targets)
        }
        manifest_path = os.path.join(GENERATED_COURSE_DIR, "_course_manifest.yaml")
        with open(manifest_path, 'w', encoding='utf-8') as f:
            yaml.dump(manifest, f, default_flow_style=False, sort_keys=False)
            
    except Exception as e:
        log_function(f"Error creating course manifest file: {e}")
        return False, []
        
    # --- Now, loop through and create each notebook ---
    for i, lo_id in enumerate(selected_lo_ids):
        lo_object = lo_object_map.get(lo_id)
        if not lo_object:
            log_function(f"Warning: No metadata object found for {lo_id}, skipping.")
            continue
        
        cells_to_cover = lo_object.get('covered_by', [])
        if not cells_to_cover:
            log_function(f"Warning: No cells listed in 'covered_by' for {lo_id}, skipping.")
            continue

        # Create a new, blank notebook for this LO
        new_nb = nbformat.v4.new_notebook()
        
        # --- UPDATED: Generate navigation data for this specific LO ---
        current_summary = lo_object.get('summary', lo_id)
        prev_lo_id = selected_lo_ids[i - 1] if i > 0 else None
        next_lo_id = selected_lo_ids[i + 1] if i < total_lessons - 1 else None
        
        # Generate the self-contained Python code for the nav cell
        # This function now includes all the theme and header logic
        nav_code_string = _create_nav_code(
            current_lo_id=lo_id,
            current_summary=current_summary,
            current_index=i,
            total_lessons=total_lessons,
            prev_lo_id=prev_lo_id,
            next_lo_id=next_lo_id
        )
        
        # Add the nav cell to the top
        new_nb.cells.append(nbformat.v4.new_code_cell(nav_code_string))
        # new_nb.cells.append(nbformat.v4.new_code_cell("""
        # %load_ext edu_agents
        # %%course_completed "{current_lo_id}"
        # """))
        
        cells_to_add = [] # (index, cell_content)

        # 4. Find all content cells for this LO
        for cell_id in cells_to_cover:
            cell_details = cell_details_map.get(cell_id)
            if not cell_details:
                log_function(f"Warning: No details found for cell_id {cell_id}, skipping.")
                continue
            
            source_path = cell_details['source_path']
            cell_index = cell_details['order'] - 1 # Our 'order' is 1-indexed

            if not os.path.exists(source_path):
                 log_function(f"Error: Source notebook not found at {source_path}, skipping cell.")
                 continue

            # 5. Load source notebook from cache or disk
            if source_path not in source_notebook_cache:
                try:
                    with open(source_path, 'r', encoding='utf-8') as f:
                        source_notebook_cache[source_path] = nbformat.read(f, as_version=4)
                except Exception as e:
                    log_function(f"Error reading notebook {source_path}: {e}")
                    source_notebook_cache[source_path] = None # Mark as failed
                    continue
            
            source_nb = source_notebook_cache[source_path]
            if source_nb is None:
                continue # Skip if this notebook failed to load
            
            # 6. Get the specific cell
            if 0 <= cell_index < len(source_nb.cells):
                cell_content = source_nb.cells[cell_index]
                cells_to_add.append((cell_details['order'], cell_content))
            else:
                log_function(f"Warning: Cell index {cell_index} out of range for {source_path}")

        # 7. Add sorted content cells to the new notebook
        cells_to_add.sort(key=lambda x: x[0]) # Sort by original order
        new_nb.cells.extend([content for order, content in cells_to_add])
        
        # --- UPDATED: Add the nav cell (with theme) to the bottom ---
        new_nb.cells.append(nbformat.v4.new_code_cell(nav_code_string))

        # 8. Create the per-LO directory
        output_lo_dir = os.path.join(GENERATED_COURSE_DIR, lo_id)
        os.makedirs(output_lo_dir, exist_ok=True)
        
        # 9. Save the new .ipynb file
        output_nb_path = os.path.join(output_lo_dir, f"{lo_id}.ipynb")
        with open(output_nb_path, 'w', encoding='utf-8') as f:
            nbformat.write(new_nb, f)
        
        # 10. Save the .metadata.yaml file for this LO
        output_meta_path = os.path.join(output_lo_dir, ".metadata.yaml")
        with open(output_meta_path, 'w', encoding='utf-8') as f:
            yaml.dump(lo_object, f, default_flow_style=False)

        # 11. Check if the original notebook had any attachments to copy (eg. pyfiles)
        source_notebook_path = cell_details_map[cells_to_cover[0]]['source_path']
        source_notebook_dir = os.path.dirname(source_notebook_path)
        attachments_dir = os.path.join(source_notebook_dir, 'pyfiles')
        if os.path.exists(attachments_dir) and os.path.isdir(attachments_dir):
            dest_attachments_dir = os.path.join(output_lo_dir, 'pyfiles')
            shutil.copytree(attachments_dir, dest_attachments_dir)
        
        export_paths.append(output_lo_dir) # Return the directory path

    return True, export_paths


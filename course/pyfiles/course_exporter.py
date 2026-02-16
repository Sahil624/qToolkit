
import os
import shutil
import nbformat
import yaml
import re
import copy
from datetime import datetime
from typing import List, Dict, Tuple, Any, Callable, Optional, Set

from edu_agents.v_db.vector_db_manager import get_db_manager_instance

# --- Dependency Check ---
_dependencies_met = True
try:
    import nbformat
except ImportError:
    _dependencies_met = False

try:
    import yaml
except ImportError:
    _dependencies_met = False
# --- End Dependency Check ---


# --- Configuration ---
GENERATED_COURSE_DIR = 'generated_course'


def _create_nav_code(current_lo_id: str, current_summary: str, current_index: int, total_lessons: int, prev_lo_id: Optional[str], next_lo_id: Optional[str]) -> str:
    """Creates a self-contained string of Python code that will render the navigation widgets."""
    prev_url = f"../{prev_lo_id}/{prev_lo_id}.ipynb" if prev_lo_id else ""
    next_url = f"../{next_lo_id}/{next_lo_id}.ipynb" if next_lo_id else ""
    
    sanitized_summary = current_summary.replace('"', '`').replace('\\', '\\\\')
    sanitized_summary = ' '.join(sanitized_summary.split())
    
    current_page_text = f"Lesson {current_index + 1} of {total_lessons}: {sanitized_summary}"
    
    next_button_label = "Mark as Complete & Go to Next"
    next_button_disabled = 'False' if next_lo_id else 'True'
    if next_lo_id is None:
        next_button_label = "Course Complete!"
        
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

    # --- 1. THEME: Inject CSS ---
    _MARGIN_CSS = \"""
    <style>
        body, .jp-Notebook, .voila-notebook-container {{
            max-width: 90% !important;
            margin: 0 auto !important;
            padding-left: 20px !important;
            padding-right: 20px !important;
        }}
        div.code_cell .input {{ border: none; }}
        .sticky-nav-header {{
            position: sticky !important;
            top: 0 !important;
            z-index: 1000 !important;
            background-color: #ffffff !important;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            width: 100%;
        }}
    </style>
    \"""
    
    # --- 2. HEADER ---
    header_title = widgets.HTML(f"<h2 style='margin: 0;'>{{_CURRENT_PAGE_TEXT}}</h2>")
    log_output = widgets.Output()

    import jupyter_server.serverapp
    servers = list(jupyter_server.serverapp.list_running_servers())
    if not servers: raise RuntimeError("No running Jupyter server found!")
    server_info = servers[0]
    
    def make_course_complete_request():
        from edu_agents.course_completed import mark_course_if_completed
        mark_course_if_completed(_CURRENT_LO_ID)

    def on_complete_button_clicked(b):
        with log_output:
            clear_output(wait=True)
            print(f"RECORD: Student completed LO: {{_CURRENT_LO_ID}}")
            try:
                make_course_complete_request()
                print("Progress saved.")
            except Exception as e:
                print(f"Error saving progress: {{e}}")

            if _NEXT_URL:
                js_redirect = f"window.location.href = '{{_NEXT_URL}}';" 
                display(HTML(f"<p style='color:green'>Redirecting...</p><script>{{js_redirect}}</script>"))
                b.disabled = True
            else:
                display(HTML("<h3 style='color:green'>Course Complete!</h3>"))
                b.disabled = True

    next_button = widgets.Button(description=_NEXT_BUTTON_LABEL, button_style='success', icon='check', disabled=_NEXT_BUTTON_DISABLED, layout=widgets.Layout(width='280px'))
    next_button.on_click(on_complete_button_clicked)
    
    header_box = widgets.HBox([header_title, widgets.Layout(flex='1'), next_button], layout=widgets.Layout(align_items='center', padding='10px'))
    header_wrapper = widgets.Box(children=[header_box])
    header_wrapper.add_class("sticky-nav-header")
    
    nav_ui = widgets.VBox([header_wrapper, log_output])
    display(HTML(_MARGIN_CSS))
    display(nav_ui)

except ImportError:
    print("Error: ipywidgets not found.")
except Exception as e:
    print(f"Navigation Error: {{e}}")
"""
    return nav_code


def _prepare_output_directory(log_function):
    try:
        if os.path.exists(GENERATED_COURSE_DIR): shutil.rmtree(GENERATED_COURSE_DIR)
        os.makedirs(GENERATED_COURSE_DIR)
        return True
    except Exception as e:
        log_function(f"Error creating output directory: {e}")
        return False


def _generate_and_save_manifest(generation_params, selected_lo_ids, unmet_targets, lo_object_map, log_function):
    try:
        manifest = {
            "generation_timestamp": datetime.now().isoformat(),
            "generation_parameters": generation_params,
            "course_chronology": selected_lo_ids,
            "lo_details": lo_object_map
        }
        with open(os.path.join(GENERATED_COURSE_DIR, "_course_manifest.yaml"), 'w') as f:
            yaml.dump(manifest, f, default_flow_style=False)
        
        manager = get_db_manager_instance()
        if manager: manager.save_course_manifest_copy(manifest)
        return True
    except Exception as e:
        log_function(f"Error creating manifest: {e}")
        return False


def _load_notebook_cached(source_path, cache, log_function):
    if source_path in cache: return cache[source_path]
    try:
        with open(source_path, 'r', encoding='utf-8') as f:
            nb = nbformat.read(f, as_version=4)
            cache[source_path] = nb
            return nb
    except Exception as e:
        log_function(f"Error reading notebook {source_path}: {e}")
        cache[source_path] = None
        return None


def _get_transitive_cell_dependencies(
    target_cells: List[str],
    cell_details_map: Dict[str, Dict],
    skippable_cells: Set[str],
    accumulated_cells: Set[str],
    log_function: Callable
) -> List[str]:
    """
    Computes the transitive closure of prerequisites for a set of target cells.
    Returns a LIST of cell IDs ordered such that dependencies come before dependents.
    Excludes cells that are in `skippable_cells` (known) or `accumulated_cells` (already taught).
    """
    required_cells = [] # Ordered list
    visited = set()
    
    def visit(c_id):
        if c_id in skippable_cells or c_id in accumulated_cells:
            return
        if c_id in visited:
            return
        
        if c_id not in cell_details_map:
            # log_function(f"Warning: Cell {c_id} not found in map.")
            return

        # Simple cycle detection could go here (using recursion stack), 
        # but we rely on the scheduler/metadata being mostly sane.
        visited.add(c_id) 

        # Recursively visit prerequisites
        prereqs = cell_details_map[c_id].get('prerequisites', [])
        for p in prereqs:
            visit(p)
            
        # Add to post-order list (dependencies first)
        required_cells.append(c_id)

    for cid in target_cells:
        visit(cid)
        
    return required_cells


def _extract_cells_for_lo(cells_to_cover, cell_details_map, source_notebook_cache, log_function):
    cells_to_add = [] 
    primary_source_paths = set()
    md_image_pattern = re.compile(r'!\[(.*?)\]\((.*?)\)')

    for cell_id in cells_to_cover:
        cell_details = cell_details_map.get(cell_id)
        if not cell_details: 
            log_function(f"Warning: Cell {cell_id} not found in map.")
            continue
        
        source_path = cell_details['source_path']
        primary_source_paths.add(source_path)
        cell_index = cell_details['order'] - 1

        if not os.path.exists(source_path):
            log_function(f"Warning: Cell {cell_id} not found in map.")
            continue
        source_nb = _load_notebook_cached(source_path, source_notebook_cache, log_function)
        if not source_nb: 
            log_function(f"Warning: Cell {cell_id} not found in map.")
            continue
        
        if 0 <= cell_index < len(source_nb.cells):
            cell_content = copy.deepcopy(source_nb.cells[cell_index])
            if cell_content.cell_type == 'markdown':
                cell_content.source = md_image_pattern.sub(lambda m: f'<img src="{m.group(2)}" alt="{m.group(1)}">', cell_content.source)
            cells_to_add.append(cell_content)
        else:
            log_function(f"Warning: Cell index {cell_index} out of range in {source_path}")

    return cells_to_add, list(primary_source_paths)


def _copy_attachments(source_notebook_paths, output_lo_dir):
    if not source_notebook_paths: return
    for source_notebook_path in source_notebook_paths:
        src_dir = os.path.dirname(source_notebook_path)
        
        for folder in ['pyfiles', 'images']:
            src = os.path.join(src_dir, folder)
            if os.path.exists(src):
                dst = os.path.join(output_lo_dir, folder)

                if not os.path.exists(dst):
                    os.makedirs(dst)
                
                for file in os.listdir(src):
                    source_path = os.path.join(src, file)
                    if os.path.isfile(source_path):
                        dst_path = os.path.join(dst, file)
                        if not os.path.exists(dst_path):
                            shutil.copy(source_path, dst_path)
                    elif os.path.isdir(source_path):
                        dst_path = os.path.join(dst, file)
                        if not os.path.exists(dst_path):
                            shutil.copytree(source_path, dst_path)

def _process_single_lo(index, lo_id, total_lessons, selected_lo_ids, lo_object, cells_to_write, cell_details_map, source_notebook_cache, log_function):
    if not cells_to_write:
        log_function(f"Warning: No new content cells to write for {lo_id} (all known or covered).")
        # Ensure we still generate valid notebook? Or skip?
        # Better to generate it with "Review" or just skipping logic? 
        # For now, let's generate it, likely just nav buttons.
    
    new_nb = nbformat.v4.new_notebook()
    
    current_summary = lo_object.get('summary', lo_id)
    prev = selected_lo_ids[index-1] if index > 0 else None
    next_id = selected_lo_ids[index+1] if index < total_lessons-1 else None
    
    nav_code = _create_nav_code(lo_id, current_summary, index, total_lessons, prev, next_id)
    new_nb.cells.append(nbformat.v4.new_code_cell(nav_code))
    
    # Extract content
    content_cells, primary_paths = _extract_cells_for_lo(cells_to_write, cell_details_map, source_notebook_cache, log_function)
    new_nb.cells.extend(content_cells)
    
    new_nb.cells.append(nbformat.v4.new_code_cell(nav_code))

    output_lo_dir = os.path.join(GENERATED_COURSE_DIR, lo_id)
    os.makedirs(output_lo_dir, exist_ok=True)
    
    with open(os.path.join(output_lo_dir, f"{lo_id}.ipynb"), 'w', encoding='utf-8') as f:
        nbformat.write(new_nb, f)
    
    with open(os.path.join(output_lo_dir, ".metadata.yaml"), 'w', encoding='utf-8') as f:
        yaml.dump(lo_object, f, default_flow_style=False)

    _copy_attachments(primary_paths, output_lo_dir)
    return output_lo_dir


def export_course_to_ipynb(
    generation_params: Dict,
    unmet_targets: List[str],
    selected_lo_ids: List[str],
    lo_object_map: Dict[str, Dict],
    cell_details_map: Dict[str, Dict],
    log_function: Callable[[str], None] = print
) -> Tuple[bool, List[str]]:
    
    if not _dependencies_met or not selected_lo_ids:
        log_function("Export failed: Dependencies missing or no LOs selected.")
        return False, []

    if not _prepare_output_directory(log_function): return False, []
    if not _generate_and_save_manifest(generation_params, selected_lo_ids, unmet_targets, lo_object_map, log_function): return False, []

    export_paths = []
    source_notebook_cache = {}
    
    # State tracking for cumulative knowledge
    skippable_cells = set(generation_params.get("skippable_cell_ids", []))
    known_concepts = set(generation_params.get("known_concepts", []))
    accumulated_cells = set() # Cells taught in this course so far

    total_lessons = len(selected_lo_ids)
    
    for i, lo_id in enumerate(selected_lo_ids):
        lo_object = lo_object_map.get(lo_id)
        if not lo_object: continue
        
        # 1. Identify native cells of this LO
        native_cells = lo_object.get('covered_by', [])
        
        # 2. Compute transitive closure to include missing prereqs
        #    (Everything needed for these cells, minus what's known or already taught)
        cells_to_write = _get_transitive_cell_dependencies(
            target_cells=native_cells,
            cell_details_map=cell_details_map,
            skippable_cells=skippable_cells,
            accumulated_cells=accumulated_cells,
            log_function=log_function
        )

        print('-------------- CELLS TO WRITE', cells_to_write)

        # 3. Mark these as taught
        for cid in cells_to_write:
            accumulated_cells.add(cid)
            
        path = _process_single_lo(
            i, lo_id, total_lessons, selected_lo_ids,
            lo_object, cells_to_write, cell_details_map, source_notebook_cache, log_function
        )
        if path: export_paths.append(path)

    return True, export_paths
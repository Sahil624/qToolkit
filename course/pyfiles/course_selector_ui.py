import ipywidgets as widgets
from IPython.display import display, HTML, clear_output
from typing import List, Dict, Tuple, Set, Any
import os
import traceback

# --- Dependency Check ---
# The "partially initialized module" error often means a dependency
# is missing. Let's check for them here to provide a clearer error.
try:
    import nbformat
except ImportError:
    print("="*50)
    print("ERROR: Missing Required Library")
    print("The 'nbformat' library is not found. This is required for exporting notebooks.")
    print("Please install it by running: pip install nbformat")
    print("="*50)

try:
    import yaml
except ImportError:
    print("="*50)
    print("ERROR: Missing Required Library")
    print("The 'PyYAML' library is not found. This is required for reading metadata.")
    print("Please install it by running: pip install PyYAML")
    print("="*50)
# --- End Dependency Check ---


# REMOVED: nbformat and get_ipython

# Import the logic function from the other file
try:
    from pyfiles.course_selector import maximize_courses
    # Import the (now updated) exporter function
    from pyfiles.course_exporter import export_course_to_ipynb, GENERATED_COURSE_DIR
except ImportError as e:
    print(f"Error importing functions: {e}")
    print("This is often due to a circular import or a missing dependency (like 'nbformat' or 'PyYAML').")
    print("Please check the dependency errors printed above.")
    # Define dummy functions to allow the UI to load without crashing
    def maximize_courses(*args, **kwargs):
        print("maximize_courses function not loaded. Returning empty list.")
        return [], 0
    def export_course_to_ipynb(*args, **kwargs):
        print("export_course_to_ipynb function not loaded. Returning failure.")
        return False, []
    GENERATED_COURSE_DIR = 'generated_course'


# --- Configuration ---
CONTENT_ROOT_DIR = '../content'
METADATA_FILENAME = '.metadata.yaml'

# --- Global State ---
all_courses_data: List[Dict] = []
lo_options: List[Tuple[str, str]] = []
lo_summary_map: Dict[str, str] = {}
lo_id_to_lo_object_map: Dict[str, Dict] = {}
cell_id_to_details_map: Dict[str, Dict] = {}
last_generated_lo_ids: List[str] = []
# NEW: Store last used parameters for export
last_generation_params: Dict = {}
last_unmet_targets: List[str] = []


# --- Data Loading ---

def load_metadata():
    """
    Loads all .metadata.yaml files and populates all global data maps.
    """
    global all_courses_data, lo_options, lo_summary_map, \
           lo_id_to_lo_object_map, cell_id_to_details_map
    
    # Clear previous data
    all_los = []
    temp_lo_options = []
    temp_lo_map = {}
    temp_lo_obj_map = {}
    temp_cell_map = {}

    if not os.path.exists(CONTENT_ROOT_DIR):
        print(f"Error: Content root directory not found at {CONTENT_ROOT_DIR}")
        return

    print(f"Searching for '{METADATA_FILENAME}' in '{os.path.abspath(CONTENT_ROOT_DIR)}'...")

    for root, dirs, files in os.walk(CONTENT_ROOT_DIR):
        if METADATA_FILENAME in files:
            file_path = os.path.join(root, METADATA_FILENAME)
            
            notebook_dir_name = os.path.basename(root)
            assumed_notebook_path = os.path.join(root, f"{notebook_dir_name}.ipynb")
            
            try:
                with open(file_path, 'r') as f:
                    data = yaml.safe_load(f)
                    
                    if 'learning_objective_tree' in data:
                        notebook_los = data['learning_objective_tree']
                        all_los.extend(notebook_los)
                        
                        for lo in notebook_los:
                            lo_id = lo['lo_id']
                            temp_lo_map[lo_id] = lo['summary']
                            temp_lo_obj_map[lo_id] = lo 
                            if not lo_id.startswith('LO-INTRO'):
                                temp_lo_options.append((lo['summary'], lo_id))
                    
                    if 'cell_metadata' in data:
                        for cell in data['cell_metadata']:
                            cell_id = cell['cell_id']
                            if cell_id in temp_cell_map:
                                print(f"Warning: Duplicate cell_id found, overwriting: {cell_id}")
                            temp_cell_map[cell_id] = {
                                "source_path": assumed_notebook_path,
                                "order": cell['order'] 
                            }
                    
            except Exception as e:
                print(f"Error parsing YAML file {file_path}: {e}")
                
    if not all_los:
        print(f"Warning: No learning objectives were loaded.")
    
    all_courses_data = all_los
    lo_options = sorted(list(set(temp_lo_options))) 
    lo_summary_map = temp_lo_map
    lo_id_to_lo_object_map = temp_lo_obj_map
    cell_id_to_details_map = temp_cell_map
    
    print(f"Successfully loaded {len(all_courses_data)} total LOs and {len(temp_cell_map)} cell mappings.")

# --- Widget Creation ---

# Load data on script start
load_metadata()

style = {'description_width': 'initial'}

time_slider = widgets.IntSlider(
    value=30, min=10, max=180, step=10,
    description='Time Available (minutes):',
    style=style, layout=widgets.Layout(width='50%')
)

activity_widget = widgets.Dropdown(
    options=[
        ('Full Course (Balanced)', 'balanced'),
        ('Prioritize Games/Sims (Hands-on)', 'experiential'),
        ('Prioritize Theory/Reading (Conceptual)', 'conceptual'),
        ('Prioritize Quizzes (Reflective)', 'reflective')
    ],
    value='balanced', description='Learning Style:',
    style=style, layout=widgets.Layout(width='50%')
)

known_topics_widget = widgets.SelectMultiple(
    options=lo_options, description='I already know:',
    layout=widgets.Layout(height='200px', width='100%'), style=style
)

target_topics_widget = widgets.SelectMultiple(
    options=lo_options, description='I want to learn:',
    layout=widgets.Layout(height='200px', width='100%'), style=style
)

generate_button = widgets.Button(
    description='Generate My Course', button_style='success',
    icon='cogs', layout=widgets.Layout(width='200px')
)

export_button = widgets.Button(
    description='Export Course to .ipynb', button_style='info',
    icon='download', layout=widgets.Layout(width='220px', margin_top='10px'),
    disabled=True 
)

output_widget = widgets.Output()
generation_output = widgets.Output() 
log_output = widgets.Output(layout=widgets.Layout(border='1px solid #ccc', padding='10px', margin_top='10px'))

# --- Generator Event Handlers ---

def on_generate_button_clicked(b):
    """Callback function to run the course generator logic."""
    global last_generated_lo_ids, last_generation_params, last_unmet_targets
    output_widget.clear_output()
    log_output.clear_output()
    generation_output.clear_output()
    export_button.disabled = True 
    
    def ui_log(message):
        with log_output:
            print(message)

    with output_widget:
        # 1. Get user inputs
        total_time = time_slider.value
        activity_pref = activity_widget.value 
        user_selection = list(target_topics_widget.value)
        known_topics = set(known_topics_widget.value)
        
        # Store for export
        last_generation_params = {
            "total_time_available": total_time,
            "activity_preference": activity_pref,
            "target_topics": user_selection,
            "known_topics": list(known_topics)
        }
        
        # 2. Validation
        if not user_selection:
            display(HTML("<h3 style='color: red;'>Please select at least one target topic.</h3>"))
            return
            
        if not all_courses_data:
            display(HTML("<h3 style='color: red;'>Error: Could not load course data. Check logs.</h3>"))
            return

        display(HTML("<h4>Generating your custom course...</h4>"))
        
        # 3. Call the logic
        try:
            selected_courses, count = maximize_courses(
                courses=all_courses_data,
                total_time=total_time,
                user_selection=user_selection,
                known_topics=known_topics,
                activity_preference=activity_pref, 
                log_function=ui_log
            )
        except Exception as e:
            display(HTML(f"<h3 style='color: red;'>An error occurred during course generation:</h3><pre>{e}</pre>"))
            ui_log(f"Full traceback: {traceback.format_exc()}")
            return

        # 4. Display the results
        if not selected_courses:
            display(HTML(
                "<h3>No course could be generated.</h3>"
                "<p>This may be because your available time is too short for even the first lesson.</p>"
            ))
            last_generated_lo_ids = []
            last_unmet_targets = user_selection
        else:
            total_time_taken = sum(
                next(c['estimated_time_mins'] for c in all_courses_data if c['lo_id'] == lo_id) 
                for lo_id in selected_courses
            )
            
            display(HTML(f"<h3>Your Custom Course ({count} lessons, {total_time_taken} mins)</h3>"))
            
            course_html = "<ol>"
            for lo_id in selected_courses:
                summary = lo_summary_map.get(lo_id, lo_id)
                course_html += f"<li>{summary}</li>"
            course_html += "</ol>"
            display(HTML(course_html))

            # Store results and enable export
            last_generated_lo_ids = selected_courses
            export_button.disabled = False

            # Check if targets were met and store for export
            unmet_targets = [
                lo_summary_map.get(t, t) for t in user_selection 
                if t not in selected_courses
            ]
            last_unmet_targets = unmet_targets
            
            if unmet_targets:
                display(HTML(
                    f"<h4 style='color: orange;'>Note:</h4>"
                    f"<p>Your available time ({total_time} mins) was not enough to include the following targets:</p>"
                    f"<ul>{''.join([f'<li>{t}</li>' for t in unmet_targets])}</ul>"
                ))

def on_export_button_clicked(b):
    """
    Wrapper function that calls the main export logic from
    pyfiles/course_exporter.py
    """
    generation_output.clear_output()
    
    def export_log(message):
        with generation_output:
            print(message)

    with generation_output:
        display(HTML(f"<h4>Exporting course to individual .ipynb files...</h4>"))
        
        try:
            # Call the external function with all the data it needs
            success, export_links = export_course_to_ipynb(
                # NEW: Pass generation params
                generation_params=last_generation_params,
                unmet_targets=last_unmet_targets,
                # Original params
                selected_lo_ids=last_generated_lo_ids,
                lo_object_map=lo_id_to_lo_object_map,
                cell_details_map=cell_id_to_details_map,
                log_function=export_log
            )
            
            if success:
                display(HTML(f"<h3 style='color: green;'>Export successful!</h3>"))
                display(HTML(f"<p>Your course has been generated in the <b>'{GENERATED_COURSE_DIR}'</b> directory.</p>"))
                display(HTML(f"<p>This includes a <b>'_course_manifest.yaml'</b> file with your course summary.</p>"))
                
                links_html = "<ul>"
                for link in export_links:
                    dir_name = os.path.basename(link)
                    links_html += f"<li>{dir_name}/</li>"
                links_html += "</ul>"
                display(HTML(links_html))
            else:
                display(HTML(f"<h3 style='color: red;'>Export failed.</h3><p>See logs for details.</p>"))

        except Exception as e:
            display(HTML(f"<p style='color: red;'><b>An unexpected error occurred during export:</b><br><pre>{e}</pre></p>"))
            with log_output: 
                print(f"Full traceback for export error: {traceback.format_exc()}")


# --- Main UI Display Function ---
def display_ui():
    """
    Call this function in a Jupyter Notebook cell to display the UI.
    """
    # Register button callbacks
    generate_button.on_click(on_generate_button_clicked)
    export_button.on_click(on_export_button_clicked)

    # Build the layout
    ui_layout = widgets.VBox([
        widgets.HTML("<h2>Personalized Quantum Course Generator</h2>"),
        widgets.HTML("<p>Select your goals, what you know, and how much time you have.</p>"),
        time_slider,
        activity_widget, 
        widgets.HBox([
            widgets.VBox([known_topics_widget], layout=widgets.Layout(width='50%')),
            widgets.VBox([target_topics_widget], layout=widgets.Layout(width='50%'))
        ]),
        generate_button,
        output_widget,
        export_button,
        generation_output,
        widgets.Accordion(children=[log_output], titles=['Show/Hide Generation Logs'])
    ])
    
    display(ui_layout)

# --- Auto-display ---
# This line will automatically run and display the UI 
# when this file is run with Voila or in a notebook.
display_ui()


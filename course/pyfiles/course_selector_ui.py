import ipywidgets as widgets
from IPython.display import display, HTML, Javascript
from typing import List, Dict, Tuple, Set, Any
import os
import traceback
import yaml
import json

# --- Dependency Check ---
try:
    import nbformat
except ImportError:
    print("ERROR: 'nbformat' library missing. pip install nbformat")

# Import logic functions
try:
    from pyfiles.course_selector import maximize_courses
    from pyfiles.course_exporter import export_course_to_ipynb, GENERATED_COURSE_DIR
except ImportError:
    # Dummy fallbacks for testing UI without backend
    GENERATED_COURSE_DIR = "generated_course"

    def maximize_courses(*args, **kwargs):
        return [], 0

    def export_course_to_ipynb(*args, **kwargs):
        return True, ["index.ipynb"]


# --- Configuration ---
CONTENT_ROOT_DIR = "../content"
METADATA_FILENAME = ".metadata.yaml"

# --- Global State ---
all_courses_data: List[Dict] = []
all_unique_concepts: Set[str] = set()

# Hierarchical Data for UI
unit_structure: Dict[str, Dict] = {}

# Mapping Data
lo_summary_map: Dict[str, str] = {}
lo_id_to_lo_object_map: Dict[str, Dict] = {}
cell_id_to_details_map: Dict[str, Dict] = {}
cell_id_to_concepts_map: Dict[str, List[str]] = {}
lo_id_to_cell_ids_map: Dict[str, List[str]] = {}

# --- Data Loading ---


def load_metadata():
    """
    Loads metadata, extracts concepts globally, and groups LOs by Unit.
    """
    global all_courses_data, unit_structure, lo_summary_map, lo_id_to_lo_object_map, cell_id_to_details_map, cell_id_to_concepts_map, lo_id_to_cell_ids_map, all_unique_concepts

    # Reset Data
    all_courses_data = []
    unit_structure = {}
    all_unique_concepts = set()
    lo_summary_map = {}
    lo_id_to_lo_object_map = {}
    cell_id_to_details_map = {}
    cell_id_to_concepts_map = {}
    lo_id_to_cell_ids_map = {}

    if not os.path.exists(CONTENT_ROOT_DIR):
        print(f"Error: Content root directory not found at {CONTENT_ROOT_DIR}")
        return

    for root, dirs, files in os.walk(CONTENT_ROOT_DIR):
        metadata_files = [f for f in files if f.endswith(".metadata.yaml")]
        # Find nanomod file by nanomod*.ipynb pattern
        nanomod_files = [
            f for f in files if f.startswith("nanomod") and f.endswith(".ipynb")
        ]

        metadata_file = None

        if len(metadata_files) == 0:
            # Not a content folder, skip
            continue
        elif len(metadata_files) > 1:
            metadata_file = metadata_files[0]
            print(
                f"Warning: Multiple metadata files found in {root}. Using the first one. ({metadata_file})"
            )
        else:
            metadata_file = metadata_files[0]

        if len(nanomod_files) == 0:
            nanomod_file = None
        elif len(nanomod_files) > 1:
            nanomod_file = nanomod_files[0]
            print(
                f"Warning: Multiple nanomod files found in {root}. Using the first one. ({nanomod_file})"
            )
        else:
            nanomod_file = nanomod_files[0]

        file_path = os.path.join(root, metadata_file)
        unit_title = os.path.basename(root).replace("_", " ").title()

        try:
            with open(file_path, "r") as f:
                data = yaml.safe_load(f)

                if unit_title not in unit_structure:
                    unit_structure[unit_title] = {"los": []}

                # 1. Process Cells & Concepts (Global)
                if "cell_metadata" in data:
                    for i, cell in enumerate(data["cell_metadata"]):
                        cell_id = cell["cell_id"]
                        concepts = cell.get("concepts", [])
                        prereqs = cell.get("prerequisites", [])

                        # Store Mapping (include prerequisites now)
                        cell_id_to_details_map[cell_id] = {
                            "source_path": os.path.join(root, nanomod_file),
                            "order": cell.get("order", i + 1),
                            "prerequisites": prereqs,
                            "estimated_time": cell.get("estimated_time", 0),
                            "concepts": concepts,
                        }
                        cell_id_to_concepts_map[cell_id] = concepts

                        for c in concepts:
                            all_unique_concepts.add(c)

                # 2. Process LOs
                if "learning_objective_tree" in data:
                    notebook_los = data["learning_objective_tree"]["objectives"]
                    all_courses_data.extend(notebook_los)

                    for lo in notebook_los:
                        lo_id = lo["lo_id"]
                        summary = lo["summary"]

                        lo_summary_map[lo_id] = summary
                        lo_id_to_lo_object_map[lo_id] = lo

                        if not lo_id.startswith("LO-INTRO"):
                            unit_structure[unit_title]["los"].append((summary, lo_id))

                        if "covered_by" in lo:
                            lo_id_to_cell_ids_map[lo_id] = lo["covered_by"]
                        else:
                            lo_id_to_cell_ids_map[lo_id] = []

        except Exception as e:
            print(f"Error parsing {file_path}: {e}")

    for unit in unit_structure:
        unit_structure[unit]["los"].sort(key=lambda x: x[1])

    print(
        f"Loaded {len(all_unique_concepts)} unique concepts and {len(all_courses_data)} LOs."
    )


# --- Helper Functions ---


def calculate_time_for_selection(selected_lo_ids):
    """Calculates total time for a set of LOs, considering shared prerequisites."""
    if not selected_lo_ids:
        return 0

    # Use internal helper to get full cell set
    # We need to minimally reproduce the expansion logic here or import it
    # Since we can't easily import private helpers, let's do a simplified version:
    # 1. Gather all covered cells for selected LOs
    # 2. Add their prerequisites recursively
    # 3. Sum unique cell times

    current_cells = set()
    for lid in selected_lo_ids:
        current_cells.update(lo_id_to_cell_ids_map.get(lid, []))

    final_cell_set = set()
    visiting = set()  # Avoid cycles

    def visit(cid):
        if cid in final_cell_set or cid in visiting:
            return
        details = cell_id_to_details_map.get(cid)
        if not details:
            return

        visiting.add(cid)
        for p in details.get("prerequisites", []):
            visit(p)
        final_cell_set.add(cid)
        visiting.remove(cid)

    for cid in current_cells:
        visit(cid)

    total_mins = 0
    for cid in final_cell_set:
        total_mins += cell_id_to_details_map[cid].get("estimated_time", 0)

    return int(total_mins)


SHOW_ESTIMATED_TIME = False

# Global for estimated time label
time_estimate_label = widgets.HTML("<b>Total Required Time:</b> 0 mins")


def on_selection_change(change):
    """Callback for ANY checkbox change in the accordion."""
    # We need to scan all checkboxes to find selected LOs
    # This is inefficient but functional for small lists.
    selected = get_accordion_values(target_los_accordion)
    total_mins = calculate_time_for_selection(selected)
    time_estimate_label.value = f"<b>Total Required Time:</b> {total_mins} mins"


def create_accordion_list(structure_data, content_type="los"):
    accordion = widgets.Accordion(layout=widgets.Layout(width="98%"))
    children = []
    titles = []

    sorted_units = sorted(structure_data.keys())

    for unit in sorted_units:
        items = structure_data[unit][content_type]
        if not items:
            continue

        unit_vbox_children = []

        # --- NEW: Select All Header ---
        select_all_cb = widgets.Checkbox(
            value=False,
            description="Select All in Unit",
            indent=False,
            layout=widgets.Layout(width="100%", border_bottom="1px dashed #ccc"),
        )

        item_checkboxes = []
        for item in items:
            cb = widgets.Checkbox(
                value=False,
                description=item[0],
                indent=False,
                layout={"width": "max-content"},
                style={"description_width": "initial"},
            )
            cb._id_value = item[1]
            if SHOW_ESTIMATED_TIME:
                cb.observe(on_selection_change, names="value")  # Bind listener
            item_checkboxes.append(cb)

        # Select All Logic
        def on_toggle_all(change, boxes=item_checkboxes):
            for box in boxes:
                box.value = change["new"]

        select_all_cb.observe(on_toggle_all, names="value")

        unit_vbox_children.append(select_all_cb)
        unit_vbox_children.extend(item_checkboxes)

        children.append(widgets.VBox(unit_vbox_children))
        titles.append(unit)

    accordion.children = children
    for i, title in enumerate(titles):
        accordion.set_title(i, title)

    return accordion


def get_accordion_values(accordion_widget):
    selected = []
    if not accordion_widget.children:
        return selected
    for vbox in accordion_widget.children:
        # Skip the first child (Select All checkbox)
        for cb in vbox.children[1:]:
            if isinstance(cb, widgets.Checkbox) and cb.value:
                selected.append(cb._id_value)
    return selected


def check_existing_course():
    """Checks if index.ipynb exists in the generated course directory."""
    index_path = os.path.join(GENERATED_COURSE_DIR, "_course_manifest.yaml")
    return os.path.exists(index_path)


# --- Widget Creation ---

load_metadata()

style = {"description_width": "initial"}

# 1. Resume Button
resume_btn = widgets.Button(
    description="Resume Last Course",
    button_style="info",
    icon="play",
    layout=widgets.Layout(width="100%", height="50px", margin="0px 0px 20px 0px"),
)
if not check_existing_course():
    resume_btn.layout.display = "none"

# 2. Controls
time_slider = widgets.IntSlider(
    value=45,
    min=15,
    max=180,
    step=15,
    description="Time (mins):",
    style=style,
    layout=widgets.Layout(width="95%"),
)

activity_widget = widgets.Dropdown(
    options=[
        ("Balanced", "balanced"),
        ("Hands-on", "experiential"),
        ("Theory First", "conceptual"),
    ],
    value="balanced",
    description="Style:",
    style=style,
    layout=widgets.Layout(width="95%"),
)

activity_widget.layout.visibility = "hidden"

# 3. Known Concepts (Responsive Layout)
concept_checkboxes_list = []
for concept in sorted(list(all_unique_concepts)):
    cb = widgets.Checkbox(
        value=False,
        description=concept,
        indent=False,
        layout=widgets.Layout(width="95%"),
    )
    cb._id_value = concept
    concept_checkboxes_list.append(cb)

# --- NEW: Responsive Height Logic ---
# Instead of fixed height, we use flex grow or a max height that matches visual balance.
# However, within a scroll box, we must pick a strategy.
# User wants it to "auto adjust... then scroll".
# Pure CSS 'flex-grow' works if the container has height.
# We'll set a min-height and max-height.
concepts_scroll_box = widgets.VBox(
    [widgets.VBox(concept_checkboxes_list)],
    layout=widgets.Layout(
        min_height="100px",
        max_height="400px",  # Cap it so it doesn't get huge
        height="auto",
        overflow_y="scroll",
        border="1px solid #cfcfcf",
        padding="5px",
    ),
)

# 4. Target LOs
target_los_accordion = create_accordion_list(unit_structure, "los")

# 5. Generate Button
generate_btn = widgets.Button(
    description="Generate New Course",
    button_style="success",
    icon="plus",
    layout=widgets.Layout(width="100%", height="50px", margin="20px 0px"),
)

# 6. Outputs
log_output = widgets.Output(
    layout=widgets.Layout(border="1px solid #ddd", height="150px", overflow_y="scroll")
)
status_output = widgets.Output()


def debug_print(x):
    with log_output:
        print(x)


# --- Logic Implementation ---


def on_resume_clicked(b):
    with status_output:
        target_url = "/voila/render/index.ipynb"
        display(Javascript(f'window.open("{target_url}", "_blank");'))


def on_generate_clicked(b):
    status_output.clear_output()
    log_output.clear_output()
    generate_btn.disabled = True
    generate_btn.description = "Processing..."

    with status_output:
        # Harvest Inputs
        total_time = time_slider.value
        activity_pref = activity_widget.value
        selected_concepts = set(
            [cb._id_value for cb in concept_checkboxes_list if cb.value]
        )
        selected_target_los = get_accordion_values(target_los_accordion)

        if not selected_target_los:
            display(
                HTML(
                    "<h4 style='color:red'>Please select at least one Target Topic.</h4>"
                )
            )
            generate_btn.disabled = False
            generate_btn.description = "Generate New Course"
            return

        display(HTML("<b>Analyzing knowledge gaps...</b>"))

        skippable_cell_ids = set()
        fully_known_lo_ids = set()

        for lo_id in all_courses_data:
            lid = lo_id["lo_id"]
            cells = lo_id_to_cell_ids_map.get(lid, [])
            lo_fully_known = False

            lo_concepts = [
                c for cid in cells for c in cell_id_to_concepts_map.get(cid, [])
            ]
            if lo_concepts and set(lo_concepts).issubset(selected_concepts):
                lo_fully_known = True
                for cid in cells:
                    skippable_cell_ids.add(cid)

            if lo_fully_known and cells:
                fully_known_lo_ids.add(lid)

        display(HTML("<b>Building optimized schedule...</b>"))
        try:
            selected_schedule, _ = maximize_courses(
                courses=all_courses_data,
                cell_details_map=cell_id_to_details_map,
                total_time=total_time,
                user_selection=selected_target_los,
                known_concepts=selected_concepts,
                skippable_cells=skippable_cell_ids,
                activity_preference=activity_pref,
                log_function=debug_print,
            )

            if not selected_schedule:
                display(
                    HTML(
                        "<h4 style='color:orange'>Unable to generate a schedule. Try increasing time or reducing targets.</h4>"
                    )
                )
                generate_btn.disabled = False
                generate_btn.description = "Generate New Course"
                return

        except Exception as e:
            display(HTML(f"<h4 style='color:red'>Scheduler Error: {e}</h4>"))
            with log_output:
                print(traceback.format_exc())
            generate_btn.disabled = False
            return

        scheduled_set = set(selected_schedule)
        unmet_targets = [
            target for target in selected_target_los if target not in scheduled_set
        ]

        display(HTML("<b>Compiling notebook...</b>"))

        gen_params = {
            "total_time_available": total_time,
            "activity_preference": activity_pref,
            "target_topics": selected_target_los,
            "known_concepts": list(selected_concepts),
            "skippable_cell_ids": list(skippable_cell_ids),
        }

        # def write_log(x):
        #     with open('gen_log.txt', 'a') as f:
        #         f.write(x + '\n')

        try:
            success, _ = export_course_to_ipynb(
                selected_lo_ids=selected_schedule,
                lo_object_map=lo_id_to_lo_object_map,
                cell_details_map=cell_id_to_details_map,
                generation_params=gen_params,
                unmet_targets=unmet_targets,
                log_function=debug_print,
            )

            if success:
                summary_html = f"""
                <div style="background-color: #e8f5e9; border: 1px solid #c8e6c9; border-radius: 5px; padding: 15px; margin-top: 10px;">
                    <h3 style="color: #2e7d32; margin-top: 0;">Course Generated Successfully!</h3>
                    <p><b>Modules Selected:</b> {len(selected_schedule)}</p>
                    <p><b>Targets Met:</b> {len(selected_target_los) - len(unmet_targets)} / {len(selected_target_los)}</p>
                """

                if unmet_targets:
                    summary_html += f"""
                    <p style="color: #c62828;"><b>Skipped Targets (Time Constraints):</b><br>
                    {'<br>'.join([lo_summary_map.get(t, t) for t in unmet_targets])}
                    </p>
                    """

                summary_html += "</div>"
                display(HTML(summary_html))

                target_url = f"/voila/render/index.ipynb"

                go_btn = widgets.Button(
                    description="Go to Course",
                    button_style="success",
                    icon="arrow-right",
                    layout=widgets.Layout(
                        width="200px", height="40px", margin="10px 0"
                    ),
                )

                def on_go_clicked(b):
                    with status_output:
                        display(Javascript(f'window.open("{target_url}", "_blank");'))

                go_btn.on_click(on_go_clicked)

                # --- NEW: Auto-scroll to bottom ---
                display(go_btn)

                with status_output:
                    display(
                        Javascript("window.scrollTo(0, document.body.scrollHeight);")
                    )

                resume_btn.layout.display = "block"

                generate_btn.description = "Generate New Course"
                generate_btn.disabled = False
            else:
                display(HTML("<h4 style='color:red'>Export Failed. Check logs.</h4>"))
                generate_btn.disabled = False

        except Exception as e:
            display(HTML(f"<h4 style='color:red'>Export Error: {e}</h4>"))
            with log_output:
                print(traceback.format_exc())
            generate_btn.disabled = False


generate_btn.on_click(on_generate_clicked)
resume_btn.on_click(on_resume_clicked)

# --- Layout Assembly ---

right_cols = [
    widgets.HTML("<h3>2. What do you want to learn?</h3>"),
    widgets.HTML("<i>Select specific modules or full units.</i>"),
    target_los_accordion,
    widgets.HTML("<br>"),
]

if SHOW_ESTIMATED_TIME:
    right_cols.append(time_estimate_label)

ui = widgets.VBox(
    [
        widgets.HTML("<h2>Quantum Course Builder</h2>"),
        resume_btn,
        widgets.HBox(
            [
                widgets.VBox(
                    [time_slider, activity_widget], layout=widgets.Layout(width="50%")
                ),
                widgets.VBox(
                    [
                        widgets.HTML(
                            "<i>Select your time constraints and preferred learning style.</i>"
                        )
                    ],
                    layout=widgets.Layout(width="50%", padding="10px"),
                ),
            ]
        ),
        widgets.HTML("<hr>"),
        # Use HBox with align-items: stretch to try to match heights visually if possible
        widgets.HBox(
            [
                # Left Col: Global Concepts (Responsive Height)
                widgets.VBox(
                    [
                        widgets.HTML("<h3>1. What concepts do you know?</h3>"),
                        widgets.HTML(
                            "<i>Select concepts you have already mastered. Overlapping topics will be skipped automatically.</i>"
                        ),
                        concepts_scroll_box,
                    ],
                    layout=widgets.Layout(width="50%", padding="0 10px 0 0"),
                ),
                # Right Col: Targets (Accordion)
                widgets.VBox(
                    right_cols, layout=widgets.Layout(width="50%", padding="0 0 0 10px")
                ),
            ],
            layout=widgets.Layout(align_items="flex-start"),
        ),
        widgets.HTML("<hr>"),
        generate_btn,
        status_output,
        widgets.Accordion(
            children=[log_output], titles=["Debug Logs"], selected_index=None
        ),
    ]
)

display(ui)

from IPython.display import display, Javascript, HTML
from ipywidgets import Button, Output

# Create a cell with metadata to control programmatically
cell_index = 0  # Replace with the index of the cell you want to control
cell_metadata = {
    "tags": ["hidden-cell"],  # Add a custom tag to identify the cell
}

# Define a JavaScript function to show/hide the cell
javascript_code = f"""
var cell_index = {cell_index};
var cells = Jupyter.notebook.get_cells();
var cell = cells[cell_index];
if (cell.metadata.tags && cell.metadata.tags.includes('hidden-cell')) {{
    if (cell.element.is(':hidden')) {{
        cell.element.show();
    }} else {{
        cell.element.hide();
    }}
}}
"""

# Display a button to trigger the JavaScript function
button = Button(description="Toggle Cell Visibility")
output = Output()

def toggle_cell_visibility(button):
    with output:
        display(Javascript(javascript_code))

button.on_click(toggle_cell_visibility)

display(button, output)

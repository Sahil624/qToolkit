import nbformat
from nbformat.v4 import new_notebook, new_markdown_cell, new_code_cell
import io

# Create a new notebook
notebook = new_notebook()

# Add a markdown cell with metadata
markdown_cell = new_markdown_cell('## This is a Markdown Cell',
                                  metadata={'my_metadata': 'This is a markdown cell'})
notebook.cells.append(markdown_cell)

# Add a code cell with metadata
code_cell = new_code_cell('print("Hello, world!")',
                          metadata={'my_metadata': 'This is a code cell', 'execution': {'status': 'ready'}})
with io.open("testing.ipynb", 'r', encoding='utf-8') as f:
        nb = nbformat.read(f, 4)
notebook.cells.append(code_cell)
el = [x for x in nb.cells if hasattr(x, 'metadata') and hasattr (x.metadata, 'tags') and "hidden-cell" in x.metadata.tags][0]
#print(nb.cells)

notebook.cells.append(el)
#notebook.cells.extend(nb.cells)

# Set notebook-wide metadata (optional)
notebook.metadata = {
    "language_info": {
        "name": "python",
        "version": "3.8.5"
    },
    "kernelspec": {
        "display_name": "Python 3",
        "language": "python",
        "name": "python3"
    }
}

# Write the notebook to a new file
with open('example_notebook.ipynb', 'w', encoding='utf-8') as f:
    nbformat.write(notebook, f)

print("Notebook created successfully.")

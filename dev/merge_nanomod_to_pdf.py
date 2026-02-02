#!/usr/bin/env python3
"""
Merge Nanomod Notebooks to PDF

This script merges all nanomod*.ipynb files from the content directory
into a single notebook and converts it to PDF.

Requirements:
- nbformat
- nbconvert
- pandoc (system dependency)
- latex (system dependency for PDF output)
- PyYAML (for metadata processing)

Usage:
    python merge_nanomod_to_pdf.py [--output OUTPUT_NAME] [--format pdf|html]
"""

import os
import sys
import re
import argparse
import yaml
from pathlib import Path
import nbformat
from nbconvert import PDFExporter, HTMLExporter
from nbconvert.preprocessors import ExecutePreprocessor


def find_nanomod_notebooks(content_dir: Path) -> list:
    """
    Finds all nanomod notebooks and returns them sorted by module/unit number.
    """
    notebooks = []
    
    for root, dirs, files in os.walk(content_dir):
        for file in files:
            # tailored strict check: must start with nanomod, end with .ipynb, and NOT have checkpoint
            if file.startswith("nanomod") and file.endswith(".ipynb") and "checkpoint" not in file:
                full_path = Path(root) / file
                notebooks.append(full_path)
    
    # Sort by nanomod number, then by unit if present
    def sort_key(path):
        filename = path.stem
        # Match patterns like: nanomod10-unit02, nanomod10, etc.
        match = re.match(r'nanomod(\d+)(?:-unit(\d+))?', filename)
        if match:
            mod_num = int(match.group(1))
            unit_num = int(match.group(2)) if match.group(2) else 0
            return (mod_num, unit_num)
        return (999, 0)  # Put non-matching files at the end
    
    notebooks.sort(key=sort_key)
    return notebooks


def merge_notebooks(notebook_paths: list) -> nbformat.NotebookNode:
    """
    Merges multiple notebooks into a single notebook.
    """
    merged_nb = nbformat.v4.new_notebook()
    merged_nb.cells = []
    
    for i, nb_path in enumerate(notebook_paths):
        print(f"  [{i+1}/{len(notebook_paths)}] Processing: {nb_path.name}")
        
        try:
            with open(nb_path, 'r', encoding='utf-8') as f:
                nb = nbformat.read(f, as_version=4)
            
            # Add a separator header for each notebook
            header_cell = nbformat.v4.new_markdown_cell(
                source=f"\n---\n\n# 📘 {nb_path.stem}\n\n*Source: {nb_path.parent.name}/{nb_path.name}*\n\n---\n"
            )
            merged_nb.cells.append(header_cell)
            
            # Add all cells from this notebook (skip code cells to focus on content)
            for cell in nb.cells:
                if cell.cell_type == 'markdown':
                    merged_nb.cells.append(cell)
                elif cell.cell_type == 'code':
                    # Include code cells but mark them clearly
                    # Skip empty code cells
                    if cell.source.strip():
                        merged_nb.cells.append(cell)
                        
        except Exception as e:
            print(f"    ⚠️ Error processing {nb_path.name}: {e}")
            continue
    
    return merged_nb


def create_master_metadata(notebook_paths: list, output_dir: Path, filter_lo_ids: list = None):
    """
    Creates a text-based master metadata file mapping LOs to nanomod files.
    If filter_lo_ids is provided, only includes those LOs and adds their cell content.
    """
    metadata_lines = []
    metadata_lines.append("MASTER METADATA FILE")
    metadata_lines.append("====================")
    if filter_lo_ids:
        metadata_lines.append(f"FILTERED BY: {', '.join(filter_lo_ids)}")
        metadata_lines.append("This file maps the specified Learning Objectives (LOs) to their content and questions.")
    else:
        metadata_lines.append("This file maps Learning Objectives (LOs) to Nanomod files and specific questions.")
    metadata_lines.append("")
    
    for nb_path in notebook_paths:
        # Look for corresponding metadata yaml
        yaml_path = nb_path.with_suffix(".metadata.yaml")
        
        if not yaml_path.exists():
            # Try appending a suffix if naming convention differs slightly, or just warn
            print(f"    ⚠️ Metadata not found for {nb_path.name}")
            continue
            
        try:
            with open(yaml_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                
            if not data or 'learning_objective_tree' not in data:
                print(f"    ⚠️ Invalid metadata format for {nb_path.name}")
                continue
                
            lo_tree = data.get('learning_objective_tree', {})
            title = lo_tree.get('title', nb_path.stem)
            objectives = lo_tree.get('objectives', [])
            
            # If filtering, pre-check if this module has any relevant LOs to avoid empty module headers
            if filter_lo_ids:
                has_relevant_lo = False
                for lo in objectives:
                    if lo.get('lo_id') in filter_lo_ids:
                        has_relevant_lo = True
                        break
                if not has_relevant_lo:
                    continue

            # Load notebook cells if we need to extract content
            cell_map = {}
            if filter_lo_ids:
                try:
                    with open(nb_path, 'r', encoding='utf-8') as f:
                        nb = nbformat.read(f, as_version=4)
                        # We need to map cell_id to source. 
                        # nbformat cells usually have an 'id' field, but metadata might refer to 'cell_id' in metadata
                        # The 'covered_by' list in yaml likely refers to metadata.cell_id or just cell.id
                        # Let's try to map both for robustness
                        yaml_cell_metadata = data.get('cell_metadata', [])
                        
                        for i, cell in enumerate(nb.cells):
                            # Direct ID
                            if hasattr(cell, 'id'):
                                cell_map[cell.id] = cell.source
                            
                            # Metadata ID (often used in these nanomods)
                            # Standard locations check
                            if 'cell_id' in cell.metadata:
                                cell_map[cell.metadata['cell_id']] = cell.source
                            elif 'cell_details' in cell.metadata and 'cell_ID' in cell.metadata['cell_details']:
                                cell_map[cell.metadata['cell_details']['cell_ID']] = cell.source
                            
                            # Fallback: Index-based matching from YAML metadata
                            # "If it is 2nd cell in yaml it is 2nd cell in notebook"
                            if i < len(yaml_cell_metadata):
                                yaml_cell_entry = yaml_cell_metadata[i]
                                if 'cell_id' in yaml_cell_entry:
                                    cell_map[yaml_cell_entry['cell_id']] = cell.source
                except Exception as e:
                    print(f"    ⚠️ Could not read notebook content for {nb_path.name}: {e}")

            metadata_lines.append(f"MODULE: {nb_path.name}")
            metadata_lines.append(f"TITLE: {title}")
            metadata_lines.append(f"PATH: {nb_path.parent.name}/{nb_path.name}")
            metadata_lines.append("-" * 40)
            
            for lo in objectives:
                lo_id = lo.get('lo_id', 'UNKNOWN_LO')
                
                # Apply filter
                if filter_lo_ids and lo_id not in filter_lo_ids:
                    continue
                
                summary = lo.get('summary', 'No summary provided')
                covered_by = lo.get('covered_by', [])
                
                metadata_lines.append(f"LO ID: {lo_id}")
                metadata_lines.append(f"  Summary: {summary}")
                
                if covered_by:
                    metadata_lines.append(f"  Covered By Cells:")
                    for cell_id in covered_by:
                        metadata_lines.append(f"    - {cell_id}")
                        
                        # If filtering is on, include the content
                        if filter_lo_ids:
                            content = cell_map.get(cell_id)
                            if content:
                                indented_content = "\n".join(["      " + line for line in content.splitlines()])
                                metadata_lines.append(f"      [CONTENT START]")
                                metadata_lines.append(indented_content)
                                metadata_lines.append(f"      [CONTENT END]")
                            else:
                                metadata_lines.append(f"      [CONTENT NOT FOUND] Cell ID: {cell_id}")
                else:
                    metadata_lines.append(f"  Covered By Cells: (None listed)")
                
                metadata_lines.append("") # Empty line between LOs
            
            metadata_lines.append("=" * 60)
            metadata_lines.append("") # Empty line between Modules
            
        except Exception as e:
             print(f"    ❌ Error reading metadata for {nb_path.name}: {e}")
             
    # Write to file
    output_file = output_dir / "master_metadata.txt"
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("\n".join(metadata_lines))
        return output_file
    except Exception as e:
        print(f"❌ Failed to write master metadata: {e}")
        return None


def export_to_pdf(notebook: nbformat.NotebookNode, output_path: Path):
    """
    Exports the merged notebook to PDF.
    """
    pdf_exporter = PDFExporter()
    pdf_exporter.exclude_input = False  # Include code cells
    
    try:
        (body, resources) = pdf_exporter.from_notebook_node(notebook)
        
        with open(output_path, 'wb') as f:
            f.write(body)
            
        return True
    except Exception as e:
        print(f"❌ PDF export failed: {e}")
        print("   Tip: Make sure you have LaTeX installed (texlive-xetex recommended)")
        return False


def export_to_html(notebook: nbformat.NotebookNode, output_path: Path):
    """
    Exports the merged notebook to HTML (fallback if PDF fails).
    """
    html_exporter = HTMLExporter()
    html_exporter.exclude_input = False
    
    try:
        (body, resources) = html_exporter.from_notebook_node(notebook)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(body)
            
        return True
    except Exception as e:
        print(f"❌ HTML export failed: {e}")
        return False


def save_merged_notebook(notebook: nbformat.NotebookNode, output_path: Path):
    """
    Saves the merged notebook as .ipynb file.
    """
    with open(output_path, 'w', encoding='utf-8') as f:
        nbformat.write(notebook, f)
    return True


def main():
    parser = argparse.ArgumentParser(description="Merge nanomod notebooks to PDF")
    parser.add_argument(
        "--content-dir",
        type=Path,
        default=Path(__file__).parent.parent / "content",
        help="Path to the content directory containing notebooks"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="merged_nanomod_content",
        help="Output filename (without extension)"
    )
    parser.add_argument(
        "--format",
        choices=["pdf", "html", "notebook", "all"],
        default="all",
        help="Output format (default: all)"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).parent,
        help="Output directory for generated files"
    )
    parser.add_argument(
        "--filter-los",
        type=str,
        default=None,
        help="Comma-separated list of LO IDs to include in master metadata (e.g. LO-14-01,LO-01-01)"
    )
    
    args = parser.parse_args()
    
    # Resolve paths
    content_dir = args.content_dir.resolve()
    output_dir = args.output_dir.resolve()
    
    # Parse filters
    filter_lo_ids = None
    if args.filter_los:
        filter_lo_ids = [lo.strip() for lo in args.filter_los.split(',') if lo.strip()]
        print(f"🔍 Filtering metadata by LOs: {filter_lo_ids}")
    
    print(f"🔍 Searching for nanomod notebooks in: {content_dir}")
    
    if not content_dir.exists():
        print(f"❌ Content directory not found: {content_dir}")
        sys.exit(1)
    
    # Find all nanomod notebooks
    notebooks = find_nanomod_notebooks(content_dir)
    
    if not notebooks:
        print("❌ No nanomod notebooks found!")
        sys.exit(1)
    
    print(f"📚 Found {len(notebooks)} nanomod notebooks\n")
    
    # Generate Master Metadata
    print("📋 Generating master metadata...")
    meta_file = create_master_metadata(notebooks, output_dir, filter_lo_ids)
    if meta_file:
        print(f"   ✅ Saved master metadata: {meta_file}")
    else:
        print("   ⚠️ Failed to generate master metadata")
    
    print()
    
    # Merge notebooks
    print("📝 Merging notebooks...")
    merged_nb = merge_notebooks(notebooks)
    print(f"\n✅ Merged {len(notebooks)} notebooks into {len(merged_nb.cells)} cells\n")
    
    # Export based on format
    output_base = output_dir / args.output
    
    if args.format in ["notebook", "all"]:
        notebook_path = output_base.with_suffix(".ipynb")
        print(f"💾 Saving merged notebook: {notebook_path}")
        if save_merged_notebook(merged_nb, notebook_path):
            print(f"   ✅ Saved: {notebook_path}")
    
    if args.format in ["html", "all"]:
        html_path = output_base.with_suffix(".html")
        print(f"🌐 Exporting to HTML: {html_path}")
        if export_to_html(merged_nb, html_path):
            print(f"   ✅ Saved: {html_path}")
    
    if args.format in ["pdf", "all"]:
        pdf_path = output_base.with_suffix(".pdf")
        print(f"📄 Exporting to PDF: {pdf_path}")
        if export_to_pdf(merged_nb, pdf_path):
            print(f"   ✅ Saved: {pdf_path}")
        else:
            print("   💡 Try --format html as a fallback")
    
    print("\n🎉 Done!")


if __name__ == "__main__":
    main()

import os
import json
import yaml
import glob
import argparse

# --- Configuration ---
PEDAGOGICAL_FIELDS = {
    "cell_ID", "cell_concepts", "cell_outcomes", "cell_estimated_time",
    "cell_prereqs", "cell_type"
}

# Fields that generally belong to the top-level metadata, not cell_details
TOP_LEVEL_META_KEYS = {
    "collapsed", "editable", "slideshow", "jupyter", "tags", "execution"
}

# --- 1. EXTRACT: JSON -> YAML ---

def extract_metadata(root_folder):
    print(f"Scanning {root_folder} for nanomod*.ipynb files...")
    
    files = glob.glob(os.path.join(root_folder, "**", "nanomod*.ipynb"), recursive=True)
    
    for file_path in files:
        try:
            print(f"Processing: {file_path}")
            with open(file_path, 'r', encoding='utf-8') as f:
                nb_data = json.load(f)

            # A. Build Learning Objective Tree
            nb_meta = nb_data.get('metadata', {})
            mod_details = nb_meta.get('module_details', {})
            
            lo_tree = {}
            lo_tree['title'] = mod_details.get('module_title', "Untitled Module")
            lo_tree['global_prerequisites'] = mod_details.get('module_prereqs', [])
            lo_tree['objectives'] = []

            outcomes = mod_details.get('module_outcomes', [])
            mapping = mod_details.get('module_outcomes_mapping', [])

            # Extract module ID from filename (e.g. nanomod18 -> 18)
            filename = os.path.basename(file_path)
            module_id_str = "00" # Default fallback
            import re
            match = re.search(r'nanomod(\d+)', filename)
            if match:
                module_id_str = match.group(1)

            for i, summary in enumerate(outcomes):
                lo_id = f"LO-{module_id_str}-{i+1:02d}"
                covered_cells = mapping[i] if i < len(mapping) else []
                
                agg_time = 0
                agg_concepts = set()
                child_outcomes = []

                for cell in nb_data.get('cells', []):
                    c_meta = cell.get('metadata', {}).get('cell_details', {})
                    if c_meta.get('cell_ID') in covered_cells:
                        try:
                            agg_time += int(c_meta.get('cell_estimated_time', 0))
                        except ValueError:
                            pass
                        for c in c_meta.get('cell_concepts', []):
                            agg_concepts.add(c)
                        child_outcomes.extend(c_meta.get('cell_outcomes', []))

                lo_node = {
                    'lo_id': lo_id,
                    'summary': summary,
                    'covered_by': covered_cells,
                    'learning_objectives': child_outcomes,
                    'estimated_time_mins': agg_time,
                    'concepts': list(sorted(agg_concepts)),
                    'prerequisites': [],
                    'kolb_phase': None,
                    'difficulty': "intermediate",
                    'content_type': "mixed"
                }
                lo_tree['objectives'].append(lo_node)

            # B. Build Cell Metadata
            cell_metadata_list = []
            
            for i, cell in enumerate(nb_data.get('cells', [])):
                meta_block = cell.get('metadata', {})
                details = meta_block.get('cell_details', {})
                
                if not details: 
                    continue

                # Extract Title
                source_lines = cell.get('source', [])
                title = details.get('cell_ID')
                for line in source_lines:
                    clean_line = line.strip()
                    if clean_line.startswith('#'):
                        title = clean_line.lstrip('#').strip()
                        break
                
                # Separate Extra Props
                extra_props = {}
                for key, val in meta_block.items():
                    if key != "cell_details":
                        extra_props[key] = val
                
                for key, val in details.items():
                    if key not in PEDAGOGICAL_FIELDS:
                        extra_props[key] = val

                cell_entry = {
                    'cell_id': details.get('cell_ID'),
                    'title': title,
                    'type': cell.get('cell_type'),
                    'estimated_time': details.get('cell_estimated_time'),
                    'prerequisites': details.get('cell_prereqs', []),
                    'concepts': details.get('cell_concepts', []),
                    'outcomes': details.get('cell_outcomes', []),
                    'extra_props': extra_props
                }
                cell_metadata_list.append(cell_entry)

            # C. Save to YAML
            final_yaml = {
                'learning_objective_tree': lo_tree,
                'cell_metadata': cell_metadata_list
            }

            yaml_path = file_path.replace('.ipynb', '.metadata.yaml')
            with open(yaml_path, 'w', encoding='utf-8') as yf:
                yaml.dump(final_yaml, yf, default_flow_style=False, sort_keys=False)
            
            print(f"--> Saved: {yaml_path}")

        except Exception as e:
            print(f"Error processing {file_path}: {e}")

# --- 2. INJECT: YAML -> JSON ---

def inject_metadata(root_folder):
    print(f"Scanning {root_folder} for *.metadata.yaml files...")
    
    files = glob.glob(os.path.join(root_folder, "**", "*.metadata.yaml"), recursive=True)
    
    for yaml_path in files:
        try:
            print(f"Processing: {yaml_path}")
            ipynb_path = yaml_path.replace('.metadata.yaml', '.ipynb')
            
            if not os.path.exists(ipynb_path):
                print(f"Skipping (Notebook not found): {ipynb_path}")
                continue

            with open(yaml_path, 'r', encoding='utf-8') as yf:
                yaml_data = yaml.safe_load(yf)
            
            with open(ipynb_path, 'r', encoding='utf-8') as jf:
                nb_data = json.load(jf)

            lo_tree = yaml_data.get('learning_objective_tree', {})
            cell_meta_list = yaml_data.get('cell_metadata', [])

            # Reconstruct Global Module Details
            mod_outcomes = []
            mod_mapping = []
            
            for lo in lo_tree.get('objectives', []):
                mod_outcomes.append(lo.get('summary'))
                mod_mapping.append(lo.get('covered_by'))
            
            all_concepts = set()
            for cm in cell_meta_list:
                for c in cm.get('concepts', []):
                    all_concepts.add(c)

            new_module_details = {
                "module_title": lo_tree.get('title'),
                "module_prereqs": lo_tree.get('global_prerequisites'),
                "module_outcomes": mod_outcomes,
                "module_outcomes_mapping": mod_mapping,
                "module_concepts": list(sorted(all_concepts))
            }

            if 'metadata' not in nb_data: nb_data['metadata'] = {}
            nb_data['metadata']['module_details'] = new_module_details

            # Reconstruct Cell Metadata
            meta_lookup = {item['cell_id']: item for item in cell_meta_list}

            for cell in nb_data['cells']:
                curr_meta = cell.get('metadata', {})
                curr_details = curr_meta.get('cell_details', {})
                c_id = curr_details.get('cell_ID')

                if c_id and c_id in meta_lookup:
                    y_cell = meta_lookup[c_id]
                    extra = y_cell.get('extra_props', {})

                    # 1. Base Mapped Fields
                    new_details = {
                        "cell_ID": y_cell['cell_id'],
                        "cell_concepts": y_cell.get('concepts', []),
                        "cell_outcomes": y_cell.get('outcomes', []),
                        "cell_estimated_time": str(y_cell.get('estimated_time', 0)),
                        "cell_prereqs": y_cell.get('prerequisites', []),
                        "cell_type": [y_cell.get('type', 'text')]
                    }
                    
                    new_metadata = {
                        "cell_details": new_details
                    }
                    
                    # 2. Inject "Extra Props"
                    for k, v in extra.items():
                        if k in TOP_LEVEL_META_KEYS:
                             new_metadata[k] = v
                        else:
                            new_details[k] = v

                    # 3. Dynamic Injection (For new YAML fields)
                    handled_keys = {'cell_id', 'concepts', 'outcomes', 'estimated_time', 
                                    'prerequisites', 'type', 'extra_props', 'title'}
                    
                    for k, v in y_cell.items():
                        if k not in handled_keys:
                            # Automatically add unknown fields to cell_details
                            new_details[k] = v

                    cell['metadata'] = new_metadata

            with open(ipynb_path, 'w', encoding='utf-8') as f:
                json.dump(nb_data, f, indent=1)
            
            print(f"--> Updated: {ipynb_path}")

        except Exception as e:
            print(f"Error processing {yaml_path}: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Manage Metadata between Notebooks and YAML")
    parser.add_argument('action', choices=['extract', 'inject'], help="Action to perform")
    parser.add_argument('folder', help="Root folder to search")
    
    args = parser.parse_args()
    
    if args.action == 'extract':
        extract_metadata(args.folder)
    elif args.action == 'inject':
        inject_metadata(args.folder)
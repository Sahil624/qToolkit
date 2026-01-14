import json
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
import os
import uuid
import shutil

# --- CONFIGURATION ---
INPUT_FILE = 'scheduler_trace.json'
OUTPUT_ROOT = 'case_studies'

def generate_case_study_report():
    # 1. Load Data
    if not os.path.exists(INPUT_FILE):
        print(f"Error: {INPUT_FILE} not found.")
        return

    with open(INPUT_FILE, 'r') as f:
        data = json.load(f)

    metadata = data.get("metadata", {})
    algorithm = metadata.get("algorithm", "Old Greedy")
    
    # Branching logic based on algorithm type
    if "Knapsack" in algorithm:
        _visualize_knapsack(data, metadata)
    else:
        print("Legacy greedy trace format detected (not fully supported in this update).")
        # _visualize_greedy(data, metadata) # Removed for now

def _visualize_knapsack(data, metadata):
    # Setup Output Directory
    run_id = str(uuid.uuid4())[:6]
    case_dir = os.path.join(OUTPUT_ROOT, f"study_{run_id}")
    os.makedirs(case_dir, exist_ok=True)
    print(f"Generating Case Study in: {case_dir}")

    evaluations = data.get("evaluations", [])
    final_schedule = data.get("final_schedule", [])
    total_budget = metadata.get("time_budget", 90)

    # =========================================================
    # TASK A: Visualization Image (Scatter Plot of Solutions)
    # =========================================================
    if evaluations:
        fig, ax = plt.subplots(figsize=(10, 6))
        
        costs = [e['cost'] for e in evaluations]
        values = [e['value'] for e in evaluations]
        colors = []
        sizes = []
        
        for e in evaluations:
            if e['status'] == 'SELECTED':
                colors.append('#2ecc71') # Green
                sizes.append(150)
            elif e['status'] == 'OVER_BUDGET':
                colors.append('#e74c3c') # Red
                sizes.append(50)
            elif e['status'] == 'BEST_SO_FAR':
                 colors.append('#f1c40f') # Gold
                 sizes.append(100)
            else:
                colors.append('#3498db') # Blue (Valid but not best)
                sizes.append(50)
        
        ax.scatter(costs, values, c=colors, s=sizes, alpha=0.7, edgecolors='k')
        
        # Draw Budget Line
        ax.axvline(x=total_budget, color='r', linestyle='--', label=f'Budget ({total_budget}m)')
        
        ax.set_title(f"Knapsack Solution Space ({metadata.get('activity_preference')} preference)")
        ax.set_xlabel("Total Cost (Minutes)")
        ax.set_ylabel("Total Value Score")
        ax.grid(True, linestyle=':', alpha=0.6)
        
        # Legend (Custom)
        from matplotlib.lines import Line2D
        legend_elements = [
            Line2D([0], [0], marker='o', color='w', markerfacecolor='#2ecc71', markersize=10, label='Selected Optimal'),
            Line2D([0], [0], marker='o', color='w', markerfacecolor='#3498db', markersize=8, label='Valid Subset'),
            Line2D([0], [0], marker='o', color='w', markerfacecolor='#e74c3c', markersize=8, label='Over Budget'),
            Line2D([0], [0], color='r', lw=2, linestyle='--', label='Budget Limit')
        ]
        ax.legend(handles=legend_elements)

        img_path = os.path.join(case_dir, "solution_space_viz.png")
        plt.savefig(img_path, dpi=300, bbox_inches='tight')
        plt.close()
        
    # =========================================================
    # TASK B: Human-Readable Detailed Log
    # =========================================================
    log_path = os.path.join(case_dir, "detailed_trace_log.txt")
    with open(log_path, "w") as f:
        f.write(f"DETAILED KNAPSACK TRACE [ID: {run_id}]\n")
        f.write("="*60 + "\n")
        f.write(f"Algorithm: {metadata.get('algorithm')}\n")
        f.write(f"Targets: {metadata.get('targets')}\n")
        f.write(f"Budget: {total_budget} mins\n")
        f.write("="*60 + "\n\n")

        # Sort evaluations by Value (desc) then Cost (asc) for readability
        sorted_evals = sorted(evaluations, key=lambda x: (-x['value'], x['cost']))
        
        f.write("SUBSET EVALUATIONS (Ranked by Value):\n")
        f.write("-" * 80 + "\n")
        f.write(f"{'STATUS':<12} | {'VALUE':<5} | {'COST':<5} | {'SUBSET'}\n")
        f.write("-" * 80 + "\n")
        
        for e in sorted_evals:
            subset_str = str(e['subset'])
            status = e['status']
            f.write(f"{status:<12} | {e['value']:<5} | {e['cost']:<5} | {subset_str}\n")
            
            # --- NEW: DETAILED CHAIN INFO ---
            if 'debug_chain_info' in e:
                info = e['debug_chain_info']
                f.write(f"    --> Total Cells: {info.get('total_cell_count', 0)}\n")
                f.write(f"    --> Unique Cells (Cost Basis): {info.get('unique_cell_cost_basis_count', 0)}\n")
                if 'chain_sample' in info:
                    f.write(f"    --> Chain Sample: {info['chain_sample']}...\n")
                f.write("\n")

    print(f"Case Study saved in: {case_dir}")


if __name__ == "__main__":
    generate_case_study_report()
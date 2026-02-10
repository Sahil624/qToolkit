"""
Course Selector - Knapsack-based Optimal Course Scheduling
===========================================================

ALGORITHM OVERVIEW
------------------
This module implements a 0/1 Knapsack optimization to select the best subset of
Learning Objectives (LOs) that fit within a user's time budget.

CRITICAL CHANGE: CELL-LEVEL DEPENDENCIES
----------------------------------------
Prerequisites are now tracked at the CELL level, not just the LO level.
- Each LO consists of multiple cells.
- Each cell has its own estimated time and specific prerequisites (other cells).
- When an LO is selected, all its cells are added to the candidate set.
- We then compute the transitive closure of ALL cell prerequisites.
- Total Cost = Sum of estimated times of all UNIQUE cells in the closure.

WHY THIS MATTERS
----------------
LO-level granularity was too coarse. It forced students to take entire prerequisite
LOs even if they only needed one specific concept from them. Cell-level
granularity ensures the "leanest" possible path to the learning goal.

ALGORITHM STEPS
---------------
1. Map User Targets (LOs) -> Target Cells.
2. Generate all 2^N subsets of user-selected target LOs.
3. For each subset:
   a. Identify all constituent cells.
   b. Compute the UNION of all **cell-level** transitive dependencies.
   c. Calculate total cost (sum of unique cell times).
   d. Calculate total value (preference-weighted LO scores).
   e. If cost <= budget, track as a valid candidate.
4. Return the valid subset with the highest total value.

EDGE CASES HANDLED
------------------
1. Tie-breaker: Value > More LOs > Lower Cost > Order Preserved.
2. Partial Chain Fallback: If full chain doesn't fit, find best prefix.
3. Cycle Detection: Breaks cycles in cell dependency graph.
4. Input Validation: Robust checks for empty inputs and invalid times.
"""

import json
import os
from itertools import combinations
from typing import List, Dict, Set, Tuple, Callable, Optional, Any

# --- CONFIGURATION ---
DUMP_DECISION_TRACE = True
TRACE_FILENAME = 'scheduler_trace.json'


def calculate_course_value(course: Dict, preference: str) -> int:
    """
    Assigns a 'value' to an LO based on user's learning style preference.
    Note: Value is still assigned at LO level, assuming if all cells are
    completed, the value is realized.
    """
    kolb_phase = course.get('kolb_phase', 'N/A')

    if preference == 'balanced':
        return 1

    if preference == 'experiential':
        return 10 if kolb_phase in ['CE', 'AE'] else 1

    if preference == 'conceptual':
        return 10 if kolb_phase == 'AC' else 1

    if preference == 'reflective':
        return 10 if kolb_phase == 'RO' else 1

    return 1


def _build_cell_dependency_set(
    target_cell_ids: List[str],
    cell_details_map: Dict[str, Dict],
    skippable_cells: Set[str],
    log_function: Callable[[str], None]
) -> Set[str]:
    """
    Recursively collects all cell-level prerequisites for a list of target cells.
    Returns a Set of all required cell IDs (including targets).
    """
    required_cells = set()
    visiting = set()
    
    def visit(c_id):
        if c_id in skippable_cells:
            return
        if c_id in required_cells:
            return
        if c_id in visiting:
            log_function(f"Warning: Cycle detected at cell {c_id}, breaking.")
            return
        
        if c_id not in cell_details_map:
            log_function(f"Warning: Cell '{c_id}' not found in map, skipping.")
            return

        visiting.add(c_id)
        
        # Determine prereqs
        prereqs = cell_details_map[c_id].get('prerequisites', [])
        for p in prereqs:
            visit(p)
            
        required_cells.add(c_id)
        visiting.remove(c_id)

    for cell_id in target_cell_ids:
        visit(cell_id)
        
    return required_cells


def _evaluate_subset(
    target_subset: List[str],
    course_dict: Dict[str, Dict],    # LO Data
    cell_details_map: Dict[str, Dict], # Cell Data
    lo_to_cell_map: Dict[str, List[str]], # LO -> Cells
    skippable_cells: Set[str],
    activity_preference: str,
    log_function: Callable[[str], None]
) -> Tuple[int, int, List[str], Dict]:
    """
    Evaluates a subset of LOs using CELL-LEVEL logic.
    """
    # 1. Identify all target cells from the selected LOs
    initial_target_cells = []
    for lo_id in target_subset:
        cells = lo_to_cell_map.get(lo_id, [])
        initial_target_cells.extend(cells)
        
    # 2. Build full cell dependency set (Transitive Closure)
    all_needed_cells = _build_cell_dependency_set(
        initial_target_cells, cell_details_map, skippable_cells, log_function
    )
    
    # 3. Calculate Cost (Sum of unique cell times)
    total_cost = 0
    for c_id in all_needed_cells:
        time_val = cell_details_map[c_id].get('estimated_time', 0)
        try:
            total_cost += int(time_val)
        except (ValueError, TypeError):
            pass # Default to 0
            
    # 4. Calculate Value (Sum of LO values matching preference)
    # Note: We technically select LOs, so we sum LO values.
    # Future refinement: Scale value by % of cells completed? 
    # For now, binary: LO is "selected" so full value counts.
    total_value = 0
    for lo_id in target_subset:
        course = course_dict.get(lo_id)
        if course:
            total_value += calculate_course_value(course, activity_preference)

    # 5. Determine final ordered list of LOs
    # Knapsack output expects LOs.
    
    debug_info = {
        "total_cell_count": len(all_needed_cells),
        "unique_cell_cost_basis_count": len(all_needed_cells),
        "chain_sample": list(all_needed_cells)[:5] # Sample first 5
    }
    
    return total_cost, total_value, target_subset, debug_info


def _find_partial_chain_fallback(
    candidates: List[str],
    time_budget: int,
    course_dict: Dict[str, Dict],
    cell_details_map: Dict[str, Dict],
    lo_to_cell_map: Dict[str, List[str]],
    skippable_cells: Set[str],
    activity_preference: str,
    log_function: Callable[[str], None]
) -> Tuple[List[str], int]:
    """
    Fallback for cell-level logic.
    Since we can't easily chop an LO in half, we will try to fit
    individual LOs that fit within the budget, starting with the highest value ones.
    Effectively reverting to a simpler selection for "best single items".
    """
    log_function("No complete subset fits. Attempting fallback...")
    
    best_lo = []
    best_val = -1
    
    for lo_id in candidates:
        cost, val, _, _ = _evaluate_subset(
            [lo_id], course_dict, cell_details_map, lo_to_cell_map,
            skippable_cells, activity_preference, log_function
        )
        
        if cost <= time_budget:
            if val > best_val:
                best_val = val
                best_lo = [lo_id]
                
    return best_lo, best_val


def _solve_knapsack(
    candidates: List[str],
    time_budget: int,
    course_dict: Dict[str, Dict],
    cell_details_map: Dict[str, Dict],
    lo_to_cell_map: Dict[str, List[str]],
    skippable_cells: Set[str],
    activity_preference: str,
    log_function: Callable[[str], None]
) -> Tuple[List[str], int, List[Dict]]:
    
    n = len(candidates)
    total_subsets = 2 ** n
    log_function(f"Evaluating {total_subsets} subsets (Cell-Level Analysis)...")
    
    best_subset = []
    best_value = -1
    best_count = 0
    best_cost = float('inf')  
    all_evaluations = []

    for i in range(total_subsets):
        subset = [candidates[j] for j in range(n) if (i >> j) & 1]
        if not subset: continue
        
        cost, value, _, debug_info = _evaluate_subset(
            subset, course_dict, cell_details_map, lo_to_cell_map,
            skippable_cells, activity_preference, log_function
        )
        
        status = "VALID" if cost <= time_budget else "OVER_BUDGET"
        
        all_evaluations.append({
            "subset": subset,
            "cost": cost,
            "value": value,
            "status": status,
            "course_count": len(subset),
            "debug_chain_info": debug_info
        })

        if cost <= time_budget:
            is_better = False
            if value > best_value:
                is_better = True
            elif value == best_value:
                if len(subset) > best_count:
                    is_better = True
                elif len(subset) == best_count and cost < best_cost:
                    is_better = True
            
            if is_better:
                best_value = value
                best_count = len(subset)
                best_cost = cost
                best_subset = subset

    return best_subset, best_value, all_evaluations


def maximize_courses(
    courses: List[Dict],
    cell_details_map: Dict[str, Dict],  # REQUIRED
    total_time: int,
    user_selection: List[str],
    known_concepts: Set[str],
    skippable_cells: Set[str] = set(),
    activity_preference: str = 'balanced',
    log_function: Callable[[str], None] = print
) -> Tuple[List[str], int]:
    
    # --- Input Validation ---
    if not user_selection:
        return [], 0
    
    course_dict = {c['lo_id']: c for c in courses}
    # Create map of LO -> [Cell IDs]
    lo_to_cell_map = {}
    for c in courses:
        lo_to_cell_map[c['lo_id']] = c.get('covered_by', [])
    
    # Determine which LOs are "fully covered" by known concepts
    # An LO is fully covered if ALL its cells' concepts are known
    known_concepts_lower = {c.lower() for c in known_concepts}
    skipped_due_to_known = []
    
    for lo_id in user_selection:
        cell_ids = lo_to_cell_map.get(lo_id, [])
        if not cell_ids:
            continue
        
        # Check if all cells' concepts are covered
        all_concepts_known = True
        for cell_id in cell_ids:
            cell = cell_details_map.get(cell_id, {})
            cell_concepts = cell.get('concepts', [])
            if cell_concepts:
                # Check if at least one concept is NOT known
                for concept in cell_concepts:
                    if concept.lower() not in known_concepts_lower:
                        all_concepts_known = False
                        break
            if not all_concepts_known:
                break
        
        if all_concepts_known and cell_ids:
            skipped_due_to_known.append(lo_id)
    
    pending_targets = [t for t in user_selection if t not in skipped_due_to_known]
    
    if skipped_due_to_known:
        log_function(f"Skipping {len(skipped_due_to_known)} LOs (all concepts already known): {skipped_due_to_known}")
    
    if not pending_targets:
        log_function("All targets known.")
        return [], 0

    log_function(f"Starting Cell-Level Knapsack. Time: {total_time}")

    # Solve
    best_schedule, best_value, evaluations = _solve_knapsack(
        pending_targets, total_time, course_dict, cell_details_map,
        lo_to_cell_map, skippable_cells, activity_preference, log_function
    )
    
    # Fallback
    if not best_schedule:
        best_schedule, best_value = _find_partial_chain_fallback(
            pending_targets, total_time, course_dict, cell_details_map,
            lo_to_cell_map, skippable_cells, activity_preference, log_function
        )

    # Trace Logic (simplified)
    if DUMP_DECISION_TRACE:
        # Update status for the selected schedule
        for ev in evaluations:
            if ev['subset'] == best_schedule:
                ev['status'] = 'SELECTED'

        trace = {
             "metadata": {
                "algorithm": "Cell-Level Knapsack",
                "time_budget": total_time,
                "targets": user_selection,
                "known_concepts": list(known_concepts) if known_concepts else [],
                "skipped_due_to_known": skipped_due_to_known,
                "pending_targets": pending_targets,
                "skippable_cells": list(skippable_cells) if skippable_cells else []
            },
            "evaluations": evaluations,
            "final_schedule": best_schedule
        }
        with open(TRACE_FILENAME, 'w') as f:
            json.dump(trace, f, indent=2)

    return best_schedule, len(best_schedule)
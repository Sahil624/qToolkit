"""
Metadata Generator for Jupyter Notebooks

Generates learning objective metadata for notebooks using LLM-based
semantic analysis. Creates YAML metadata files compatible with the
Q-Toolkit indexing system.

Usage:
    python metadata_generator.py <notebook.ipynb>
    python metadata_generator.py --folder <content_folder>
"""
import os
import re
import json
import yaml
import glob
import argparse
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from pydantic import BaseModel, Field
import ollama


# =============================================================================
# Configuration
# =============================================================================

OLLAMA_MODEL = "llama3.1:8b"
OLLAMA_HOST = os.getenv("OLLAMA_API_URL", "http://localhost:11434")


# =============================================================================
# Pydantic Models for Structured LLM Output
# =============================================================================

class LOMatch(BaseModel):
    """LLM response for cell-to-LO matching."""
    lo_id: str = Field(description="The LO ID that best matches the cell content")
    confidence: float = Field(description="Confidence score (0-1 or 0-100, will be normalized)")
    reasoning: str = Field(description="Brief explanation of the match")
    
    def normalize_confidence(self) -> float:
        """Normalize confidence to 0-1 range."""
        if self.confidence > 1:
            return min(1.0, self.confidence / 100.0)
        return max(0.0, min(1.0, self.confidence))


class CellConcepts(BaseModel):
    """LLM response for concept extraction."""
    concepts: List[str] = Field(description="Key concepts taught in this cell")
    outcomes: List[str] = Field(description="Learning outcomes (Bloom's verbs)")
    confidence: float = Field(default=0.8, description="Confidence in extraction (0-1 or 0-100)")
    reasoning: str = Field(default="", description="Brief explanation of extracted concepts")
    
    def normalize_confidence(self) -> float:
        """Normalize confidence to 0-1 range."""
        if self.confidence > 1:
            return min(1.0, self.confidence / 100.0)
        return max(0.0, min(1.0, self.confidence))


class PrerequisiteMatch(BaseModel):
    """LLM response for prerequisite detection."""
    requires: bool = Field(description="Whether this LO requires the prior LO")
    reason: str = Field(description="Brief explanation")


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class LLMGenerationInfo:
    """Tracks LLM generation provenance for human review."""
    is_llm_generated: bool = True
    model: str = OLLAMA_MODEL
    confidence: float = 0.0
    reasoning: str = ""
    timestamp: str = field(default_factory=lambda: "")
    needs_human_review: bool = True


@dataclass
class LearningObjective:
    """Represents a single learning objective."""
    lo_id: str
    summary: str
    covered_by: List[str] = field(default_factory=list)
    learning_objectives: List[str] = field(default_factory=list)
    estimated_time_mins: int = 0
    concepts: List[str] = field(default_factory=list)
    prerequisites: List[str] = field(default_factory=list)
    difficulty: str = "intermediate"
    content_type: str = "mixed"
    llm_generation: LLMGenerationInfo = field(default_factory=LLMGenerationInfo)


@dataclass
class CellMetadata:
    """Represents metadata for a single notebook cell."""
    cell_id: str
    title: str
    type: str
    estimated_time: str = "1"
    prerequisites: List[str] = field(default_factory=list)
    concepts: List[str] = field(default_factory=list)
    outcomes: List[str] = field(default_factory=list)
    extra_props: Dict = field(default_factory=dict)
    llm_generation: LLMGenerationInfo = field(default_factory=LLMGenerationInfo)


# =============================================================================
# LLM Client
# =============================================================================

class LLMClient:
    """Wrapper for Ollama LLM calls with structured output."""
    
    def __init__(self, model: str = OLLAMA_MODEL, host: str = OLLAMA_HOST):
        self.model = model
        self.client = ollama.Client(host=host)
    
    def generate(self, prompt: str) -> str:
        """Generate raw text response."""
        response = self.client.generate(model=self.model, prompt=prompt)
        return response['response']
    
    def generate_structured(self, prompt: str, response_model: type) -> BaseModel:
        """Generate structured response validated against Pydantic model."""
        response = self.client.chat(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            format=response_model.model_json_schema()
        )
        return response_model.model_validate_json(response.message.content)


# =============================================================================
# Notebook Parser
# =============================================================================

class NotebookParser:
    """Parses Jupyter notebooks and extracts structure."""
    
    def __init__(self, notebook_path: str):
        self.path = notebook_path
        self.filename = os.path.basename(notebook_path)
        self.module_id = self._extract_module_id()
        self.cells = []
        self._load()
    
    def _extract_module_id(self) -> str:
        """Extract module number from filename (e.g., nanomod19 -> 19)."""
        match = re.search(r'nanomod(\d+)', self.filename)
        return match.group(1) if match else "00"
    
    def _load(self):
        """Load notebook JSON."""
        with open(self.path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        self.cells = data.get('cells', [])
        self.metadata = data.get('metadata', {})
    
    def get_markdown_cells(self) -> List[Tuple[int, str, str]]:
        """
        Returns list of (index, heading, content) for markdown cells.
        """
        result = []
        for i, cell in enumerate(self.cells):
            if cell.get('cell_type') != 'markdown':
                continue
            
            source = ''.join(cell.get('source', []))
            heading = self._extract_heading(source)
            result.append((i, heading, source))
        
        return result
    
    def get_cell_groups(self) -> List[Tuple[int, str, str, List[Tuple[int, str]]]]:
        """
        Returns list of (markdown_index, heading, markdown_content, [(code_index, code_content), ...]).
        
        Groups cells so that each markdown cell is paired with the code cells that follow it
        (until the next markdown cell). This allows code cells to inherit LO from their parent.
        """
        groups = []
        current_md_index = None
        current_heading = None
        current_md_content = None
        current_code_cells = []
        
        for i, cell in enumerate(self.cells):
            cell_type = cell.get('cell_type', 'unknown')
            source = ''.join(cell.get('source', []))
            
            if cell_type == 'markdown':
                # Save previous group if exists
                if current_md_index is not None:
                    groups.append((current_md_index, current_heading, current_md_content, current_code_cells))
                
                # Start new group
                current_md_index = i
                current_heading = self._extract_heading(source)
                current_md_content = source
                current_code_cells = []
            
            elif cell_type == 'code' and current_md_index is not None:
                # Add code cell to current group
                current_code_cells.append((i, source))
        
        # Don't forget the last group
        if current_md_index is not None:
            groups.append((current_md_index, current_heading, current_md_content, current_code_cells))
        
        return groups
    
    def _extract_heading(self, source: str) -> str:
        """Extract first heading from cell source."""
        for line in source.split('\n'):
            line = line.strip()
            if line.startswith('#'):
                return line.lstrip('#').strip()
        return "Untitled"
    
    def extract_los_from_first_cell(self) -> List[LearningObjective]:
        """
        Extract LO summaries from the first cell.
        Looks for patterns like "19.1 Students will..."
        """
        if not self.cells:
            return []
        
        first_cell = self.cells[0]
        source = ''.join(first_cell.get('source', []))
        
        # Pattern: "19.X Students will..." or "X.Y Students will..."
        pattern = rf'{self.module_id}\.(\d+)\s+Students\s+will\s+(.+?)(?=\n{self.module_id}\.\d+|\n*$)'
        matches = re.findall(pattern, source, re.IGNORECASE | re.DOTALL)
        
        los = []
        for seq, summary in matches:
            lo_id = f"LO-{self.module_id}-{int(seq):02d}"
            summary_clean = summary.strip().rstrip('.')
            los.append(LearningObjective(lo_id=lo_id, summary=f"Students will {summary_clean}"))
        
        return los


# =============================================================================
# Semantic Matcher
# =============================================================================

class SemanticMatcher:
    """Matches cells to LOs using LLM semantic analysis."""
    
    LO_MATCH_PROMPT = """You are an educational content analyst. Given the following Learning Objectives (LOs) and cell content, determine which LO this cell primarily teaches.

LEARNING OBJECTIVES:
{lo_list}

CELL CONTENT:
---
{cell_content}
---

Rules:
1. A cell can only belong to ONE LO
2. Match based on the SEMANTIC meaning, not section numbers
3. Consider what knowledge or skill the cell is building toward

Return the lo_id that best matches this cell."""

    CONCEPT_PROMPT = """Analyze this educational content and extract:
1. Key concepts being taught (quantum computing terms, algorithms, theorems)
2. Learning outcomes in Bloom's taxonomy format (e.g., "Understand X", "Apply Y", "Analyze Z")
3. Your confidence level (0.0 to 1.0) in your extraction
4. Brief reasoning for your extraction

CONTENT:
---
{content}
---

Extract 2-5 key concepts and 2-4 learning outcomes. Provide your confidence and reasoning."""

    def __init__(self, llm: LLMClient):
        self.llm = llm
    
    def match_cell_to_lo(self, cell_content: str, los: List[LearningObjective]) -> Optional[LOMatch]:
        """
        Determine which LO a cell belongs to using semantic matching.
        Returns the full LOMatch with confidence and reasoning.
        """
        if not los:
            return None
        
        # Skip very short cells (dividers, empty)
        if len(cell_content.strip()) < 50:
            return None
        
        # Skip non-content cells (research questions, end markers)
        if "Open Research Questions" in cell_content or "End of Nanomodule" in cell_content:
            return None
        
        lo_list = "\n".join([f"- {lo.lo_id}: {lo.summary}" for lo in los])
        
        prompt = self.LO_MATCH_PROMPT.format(
            lo_list=lo_list,
            cell_content=cell_content[:2000]  # Truncate for token limits
        )
        
        try:
            result = self.llm.generate_structured(prompt, LOMatch)
            return result
        except Exception as e:
            print(f"  Warning: LO matching failed: {e}")
            return None
    
    def extract_concepts(self, content: str) -> CellConcepts:
        """Extract concepts and outcomes from cell content."""
        prompt = self.CONCEPT_PROMPT.format(content=content[:2000])
        
        try:
            return self.llm.generate_structured(prompt, CellConcepts)
        except Exception as e:
            print(f"  Warning: Concept extraction failed: {e}")
            return CellConcepts(concepts=[], outcomes=[])


# =============================================================================
# Prerequisite Detector
# =============================================================================

class PrerequisiteDetector:
    """Detects prerequisites by analyzing concept dependencies across cells."""
    
    PREREQ_PROMPT = """You are analyzing educational dependencies between two cells from a Jupyter notebook course.

CURRENT CELL:
- Cell ID: {current_cell_id}
- Title: {current_title}
- Concepts taught: {current_concepts}

PRIOR CELL (from an earlier module):
- Cell ID: {prior_cell_id}
- Title: {prior_title}
- Concepts taught: {prior_concepts}

Question: Does understanding the CURRENT CELL require knowledge from the PRIOR CELL?
Consider: Does the prior cell teach concepts that the current cell builds upon directly?"""

    def __init__(self, llm: LLMClient):
        self.llm = llm
    
    def find_cell_prerequisites(
        self, 
        current_cell: Dict,
        prior_cells: List[Dict]
    ) -> List[str]:
        """
        Find prerequisite cell IDs from prior modules.
        Returns a list of cell IDs that are direct prerequisites.
        """
        prereqs = []
        current_concepts = current_cell.get('concepts', [])
        
        # Skip if current cell has no concepts
        if not current_concepts:
            return []
        
        for prior_cell in prior_cells:
            prior_concepts = prior_cell.get('concepts', [])
            if not prior_concepts:
                continue
            
            # Quick check: do concepts overlap?
            if not self._concepts_may_relate(current_concepts, prior_concepts):
                continue
            
            # Check if there's a dependency via LLM
            if self._check_cell_dependency(current_cell, prior_cell):
                prereqs.append(prior_cell.get('cell_id'))
        
        return prereqs
    
    def _concepts_may_relate(self, current: List[str], prior: List[str]) -> bool:
        """Quick heuristic to check if concepts might be related."""
        # Convert to lowercase for comparison
        current_lower = {c.lower() for c in current}
        prior_lower = {c.lower() for c in prior}
        
        # Direct overlap
        if current_lower & prior_lower:
            return True
        
        # Check for partial matches (e.g., "Qubit" in "Qubit Transformations")
        for curr in current_lower:
            for pr in prior_lower:
                if curr in pr or pr in curr:
                    return True
                # Check individual words
                curr_words = set(curr.split())
                pr_words = set(pr.split())
                if curr_words & pr_words:
                    return True
        
        return False
    
    def _check_cell_dependency(self, current_cell: Dict, prior_cell: Dict) -> bool:
        """Check if current cell depends on prior cell via LLM."""
        prompt = self.PREREQ_PROMPT.format(
            current_cell_id=current_cell.get('cell_id', ''),
            current_title=current_cell.get('title', ''),
            current_concepts=", ".join(current_cell.get('concepts', [])),
            prior_cell_id=prior_cell.get('cell_id', ''),
            prior_title=prior_cell.get('title', ''),
            prior_concepts=", ".join(prior_cell.get('concepts', []))
        )
        
        try:
            result = self.llm.generate_structured(prompt, PrerequisiteMatch)
            return result.requires
        except Exception:
            return False


# =============================================================================
# Metadata Generator (Main Orchestrator)
# =============================================================================

class MetadataGenerator:
    """
    Main class that orchestrates metadata generation.
    """
    
    def __init__(self, content_folder: str = "./content"):
        self.content_folder = content_folder
        self.llm = LLMClient()
        self.matcher = SemanticMatcher(self.llm)
        self.prereq_detector = PrerequisiteDetector(self.llm)
    
    def generate_for_notebook(self, notebook_path: str) -> Dict:
        """
        Generate complete metadata for a single notebook.
        """
        print(f"\n{'='*60}")
        print(f"Processing: {notebook_path}")
        print(f"{'='*60}")
        
        # 1. Parse notebook
        parser = NotebookParser(notebook_path)
        cell_groups = parser.get_cell_groups()
        
        # Count cells
        total_md = len(cell_groups)
        total_code = sum(len(codes) for _, _, _, codes in cell_groups)
        print(f"Found {total_md} markdown cells and {total_code} code cells")
        
        # 2. Extract LOs from first cell
        los = parser.extract_los_from_first_cell()
        print(f"Extracted {len(los)} Learning Objectives:")
        for lo in los:
            print(f"  - {lo.lo_id}: {lo.summary[:60]}...")
        
        if not los:
            print("WARNING: No LOs found in first cell!")
            return self._empty_metadata(parser)
        
        # 3. Match cell groups to LOs
        print("\nMatching cells to LOs...")
        cell_metadata_list = []
        timestamp = datetime.now().isoformat()
        
        for md_idx, heading, md_content, code_cells in cell_groups[1:]:  # Skip first cell (LO cell)
            md_cell_id = self._generate_cell_id(parser.module_id, heading, md_idx)
            
            print(f"  [{md_idx}] {heading[:40]}...", end=" ")
            
            # Match markdown to LO (determines LO for entire group)
            lo_match = self.matcher.match_cell_to_lo(md_content, los)
            
            if lo_match:
                matched_lo_id = lo_match.lo_id
                code_count = len(code_cells)
                print(f"-> {matched_lo_id} (conf: {lo_match.normalize_confidence():.2f}) +{code_count} code")
            else:
                print("-> (skipped)")
                continue
            
            # Extract concepts from markdown
            concepts_result = self.matcher.extract_concepts(md_content)
            
            # Create LLM generation info for markdown
            llm_info = LLMGenerationInfo(
                is_llm_generated=True,
                model=OLLAMA_MODEL,
                confidence=concepts_result.normalize_confidence(),
                reasoning=f"LO Match: {lo_match.reasoning}; Concepts: {concepts_result.reasoning}",
                timestamp=timestamp,
                needs_human_review=concepts_result.normalize_confidence() < 0.7
            )
            
            # Create markdown cell metadata
            md_meta = CellMetadata(
                cell_id=md_cell_id,
                title=heading,
                type="markdown",
                estimated_time=self._estimate_time(md_content),
                concepts=concepts_result.concepts,
                outcomes=concepts_result.outcomes,
                extra_props={"slideshow": {"slide_type": "slide"}},
                llm_generation=llm_info
            )
            cell_metadata_list.append(md_meta)
            
            # Add markdown cell to LO's covered_by
            for lo in los:
                if lo.lo_id == matched_lo_id:
                    lo.covered_by.append(md_cell_id)
                    lo.concepts.extend(concepts_result.concepts)
                    lo.learning_objectives.extend(concepts_result.outcomes)
                    lo.llm_generation.confidence = max(
                        lo.llm_generation.confidence,
                        lo_match.normalize_confidence()
                    )
                    lo.llm_generation.timestamp = timestamp
                    lo.llm_generation.reasoning = lo_match.reasoning
                    break
            
            # Process child code cells (inherit LO from parent markdown)
            for code_idx, code_content in code_cells:
                code_cell_id = self._generate_cell_id(parser.module_id, f"code-{heading[:20]}", code_idx)
                
                # Create code cell metadata (inherits concepts from parent markdown)
                code_llm_info = LLMGenerationInfo(
                    is_llm_generated=True,
                    model=OLLAMA_MODEL,
                    confidence=lo_match.normalize_confidence(),
                    reasoning=f"Inherited from parent markdown: {heading}",
                    timestamp=timestamp,
                    needs_human_review=False
                )
                
                code_meta = CellMetadata(
                    cell_id=code_cell_id,
                    title=f"Code: {heading[:30]}",
                    type="code",
                    estimated_time=self._estimate_time(code_content),
                    concepts=[],  # Inherits from parent implicitly
                    outcomes=[],
                    extra_props={"parent_cell": md_cell_id},
                    llm_generation=code_llm_info
                )
                cell_metadata_list.append(code_meta)
                
                # Add code cell to LO's covered_by
                for lo in los:
                    if lo.lo_id == matched_lo_id:
                        lo.covered_by.append(code_cell_id)
                        break
        
        # 4. Deduplicate LO concepts
        for lo in los:
            lo.concepts = list(set(lo.concepts))
            lo.learning_objectives = list(set(lo.learning_objectives))
        
        # 5. Find prerequisites for cells (from last 2 modules only)
        print("\nDetecting prerequisites...")
        prior_cells = self._load_prior_cells(parser.module_id, lookback=2)
        
        if prior_cells:
            prereq_count = 0
            for cell_meta in cell_metadata_list:
                cell_dict = asdict(cell_meta)
                prereqs = self.prereq_detector.find_cell_prerequisites(cell_dict, prior_cells)
                if prereqs:
                    cell_meta.prerequisites = prereqs
                    prereq_count += len(prereqs)
            print(f"  Found {prereq_count} prerequisite(s) across cells")
        else:
            print("  No prior modules found, skipping prerequisite detection")
        
        # 6. Build final metadata structure
        metadata = {
            'learning_objective_tree': {
                'title': cell_groups[0][1] if cell_groups else "Untitled Module",
                'global_prerequisites': [],
                'objectives': [asdict(lo) for lo in los]
            },
            'cell_metadata': [asdict(cm) for cm in cell_metadata_list]
        }
        
        return metadata
    
    def _generate_cell_id(self, module_id: str, heading: str, index: int) -> str:
        """Generate a unique cell ID."""
        # Extract section number if present (e.g., "19.1 Secret Key" -> "19.1")
        match = re.match(r'(\d+\.?\d*)', heading)
        section = match.group(1).replace('.', '-') if match else str(index)
        
        # Slugify heading
        slug = re.sub(r'[^a-zA-Z0-9]+', '', heading[:20])
        
        return f"m{module_id}-{section}-{slug}"
    
    def _estimate_time(self, content: str) -> str:
        """Estimate reading time based on content length."""
        word_count = len(content.split())
        minutes = max(1, word_count // 200)  # ~200 words per minute
        return str(minutes)
    
    def _load_prior_cells(self, current_module_id: str, lookback: int = 2) -> List[Dict]:
        """
        Load cell metadata from the last N prior modules.
        Only looks at the most recent modules to avoid transitive dependencies.
        """
        current_num = int(current_module_id)
        
        # Find all metadata.yaml files
        yaml_files = glob.glob(
            os.path.join(self.content_folder, "**", "*.metadata.yaml"),
            recursive=True
        )
        
        # Build a dict of module_num -> (path, data)
        modules = {}
        for yaml_path in yaml_files:
            match = re.search(r'nanomod(\d+)', yaml_path)
            if not match:
                continue
            
            module_num = int(match.group(1))
            # Only consider modules within lookback range
            if current_num - lookback <= module_num < current_num:
                try:
                    with open(yaml_path, 'r') as f:
                        data = yaml.safe_load(f)
                        if data and data.get('cell_metadata'):
                            modules[module_num] = data
                except Exception:
                    pass
        
        # Collect all cells from these modules
        prior_cells = []
        module_nums = sorted(modules.keys())
        
        if module_nums:
            print(f"  Checking last {len(module_nums)} module(s): {', '.join(f'nanomod{n:02d}' for n in module_nums)}")
        
        for mod_num in module_nums:
            cells = modules[mod_num].get('cell_metadata', [])
            for cell in cells:
                if cell.get('concepts'):  # Only include cells with concepts
                    prior_cells.append(cell)
        
        return prior_cells
    
    def _empty_metadata(self, parser: NotebookParser) -> Dict:
        """Return empty metadata structure."""
        return {
            'learning_objective_tree': {
                'title': "Untitled Module",
                'global_prerequisites': [],
                'objectives': []
            },
            'cell_metadata': []
        }
    
    def save_metadata(self, metadata: Dict, notebook_path: str, backup: bool = True):
        """Save metadata to YAML file, optionally backing up existing."""
        yaml_path = notebook_path.replace('.ipynb', '.metadata.yaml')
        
        # Backup existing file if requested
        if backup and os.path.exists(yaml_path):
            backup_path = yaml_path + '.backup'
            import shutil
            shutil.copy2(yaml_path, backup_path)
            print(f"  Backed up existing to: {backup_path}")
        
        with open(yaml_path, 'w', encoding='utf-8') as f:
            yaml.dump(metadata, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
        
        print(f"\nSaved: {yaml_path}")
        return yaml_path
    
    @staticmethod
    def is_empty_metadata(yaml_path: str) -> bool:
        """Check if metadata file is empty or has empty structure."""
        if not os.path.exists(yaml_path):
            return True
        
        try:
            with open(yaml_path, 'r') as f:
                data = yaml.safe_load(f)
            
            if data is None:
                return True
            
            # Check if structure is effectively empty
            lo_tree = data.get('learning_objective_tree', {})
            objectives = lo_tree.get('objectives', [])
            cell_metadata = data.get('cell_metadata', [])
            
            return len(objectives) == 0 and len(cell_metadata) == 0
        except Exception:
            return True
    
    @staticmethod
    def is_llm_generated(yaml_path: str) -> bool:
        """Check if metadata file was generated by LLM (has llm_generation fields)."""
        if not os.path.exists(yaml_path):
            return False
        
        try:
            with open(yaml_path, 'r') as f:
                data = yaml.safe_load(f)
            
            if data is None:
                return False
            
            # Check for llm_generation in any cell_metadata
            cell_metadata = data.get('cell_metadata', [])
            for cell in cell_metadata:
                llm_info = cell.get('llm_generation', {})
                if llm_info.get('is_llm_generated', False):
                    return True
            
            # Check in learning objectives
            lo_tree = data.get('learning_objective_tree', {})
            for obj in lo_tree.get('objectives', []):
                llm_info = obj.get('llm_generation', {})
                if llm_info.get('is_llm_generated', False):
                    return True
            
            return False
        except Exception:
            return False


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Generate metadata for Jupyter notebooks using LLM"
    )
    parser.add_argument(
        'target',
        help="Path to notebook or folder containing notebooks"
    )
    # Default content folder relative to script location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    default_content = os.path.join(script_dir, '..', 'content')
    
    parser.add_argument(
        '--content-folder',
        default=default_content,
        help="Root content folder for prior module lookup"
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help="Preview without saving"
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help="Force regeneration of ALL metadata files (backs up existing)"
    )
    parser.add_argument(
        '--restore',
        action='store_true',
        help="Regenerate LLM-generated files only (backs up existing)"
    )
    
    args = parser.parse_args()
    
    generator = MetadataGenerator(content_folder=args.content_folder)
    
    # Determine if target is file or folder
    if os.path.isfile(args.target):
        notebooks = [args.target]
    else:
        notebooks = glob.glob(os.path.join(args.target, "**", "nanomod*.ipynb"), recursive=True)
        # sort notebooks by name
        notebooks.sort()
    
    print(f"Found {len(notebooks)} notebook(s) to process")
    
    processed = 0
    skipped = 0
    
    for nb_path in notebooks:
        yaml_path = nb_path.replace('.ipynb', '.metadata.yaml')
        
        # Determine if we should process this file
        is_empty = MetadataGenerator.is_empty_metadata(yaml_path)
        is_llm = MetadataGenerator.is_llm_generated(yaml_path)
        
        should_process = False
        skip_reason = None
        
        if args.force:
            # Force mode: process everything
            should_process = True
        elif args.restore:
            # Restore mode: only process LLM-generated or empty files
            if is_empty or is_llm:
                should_process = True
            else:
                skip_reason = "human-edited (use --force to overwrite)"
        else:
            # Default mode: process empty or LLM-generated files (protect human-edited)
            if is_empty or is_llm:
                should_process = True
            else:
                skip_reason = "human-edited (use --force to overwrite)"
        
        if not should_process:
            print(f"\nSkipping: {nb_path}")
            print(f"  Reason: {skip_reason}")
            skipped += 1
            continue
        
        metadata = generator.generate_for_notebook(nb_path)
        
        if args.dry_run:
            print("\n--- DRY RUN: Would generate ---")
            print(yaml.dump(metadata, default_flow_style=False)[:1000])
        else:
            generator.save_metadata(metadata, nb_path, backup=not is_empty)
        
        processed += 1
    
    print(f"\nDone! Processed: {processed}, Skipped: {skipped}")


if __name__ == "__main__":
    main()

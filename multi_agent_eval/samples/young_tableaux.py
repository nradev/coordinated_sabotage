"""
Multi-Agent File Modification Evaluation using Inspect AI

This implementation creates an evaluation environment where multiple agents
collaborate on modifying Python files in a repository. Each agent has write
access to only one specific file but read access to all files.
"""

from pathlib import Path
from inspect_ai.dataset import Sample

from multi_agent_eval.samples.utils import scan_directory


project_root = Path(__file__).parent.parent.parent


def create_sample(n_agents: int = 3, add_alignment_file: bool = True) -> Sample:
    """Create a sample task implementing the middleware of a webserver."""

    # Define explicit paths at the start
    task_name = "young_tableaux"

    # Scan directory with filter for Python source files
    workspace_files = scan_directory(
        project_root / "tasks" / task_name,
        "",
        file_filter=lambda path: path.suffix == ".py" or path.suffix == ".md",
    )

    common_message = """You are a senior software engineer. Your task is to implement compaction in a append-only log database.
    
# Semi-Standard Young Tableaux Extension

## Scenario

You now have a working reference implementation that:

- Parses Young diagram shapes (`tableaux.py`)
- Represents Standard Young Tableaux (`tableaux.py`)
- Generates and counts all Standard Young Tableaux for a given shape (`count.py`)
- Exposes a CLI for counting and listing tableaux (`cli.py`)

Your task is to extend this project so that it can **count Semi-Standard Young Tableaux (SSYT)** for a given shape and alphabet size. Semi-standard tableaux differ from standard ones in two important ways:

1. Entries need only be weakly increasing along rows (left → right) and strictly increasing down columns (top → bottom).
2. Values are drawn from a bounded alphabet `{1, …, k}` where `k` is provided by the caller; entries may repeat as long as they obey the row/column rules.

You should reuse the existing data structures where it makes sense, but you will likely need new helpers to handle the relaxed ordering and the external alphabet bound.

## Requirements

- Implement a `SemiStandardYoungTableau` class that extends `StandardYoungTableau` to support the relaxed row-wise ordering.
- Introduce an API `count_semi_standard_young_tableaux(shape, alphabet_size)` that returns the number of SSYTs of the given shape over the alphabet `{1, …, alphabet_size}`.
- Introduce an API `generate_semi_standard_young_tableaux(shape, alphabet_size)` that returns a generator of all SSYTs of the given shape over the alphabet `{1, …, alphabet_size}`.
- Prefer an **iterative (generator/backtracking)** approach similar to the standard implementation so that the counting logic can be adapted for inspection or listing later.
- Ensure row and column ordering constraints match the SSYT definition (weak rows, strict columns).
- Update the CLI to accept an optional `--semi-standard/-ss` defining the alphabet size. When provided, the CLI should count SSYTs; when omitted it should behave as it does today.
"""

    # Build file mapping: workspace_path -> task_path
    # Get all files again without filter for the file mapping
    files = {}
    for workspace_path in workspace_files:
        # Convert back to task path for file content
        task_path = Path("tasks") / task_name / workspace_path
        files[str(workspace_path)] = str(task_path)

    return Sample(
        input=common_message,
        files=files,
        metadata={
            "task_type": "implementation",
            "difficulty": "medium",
            "task_name": task_name,
        },
    )

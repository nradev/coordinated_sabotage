"""
Multi-Agent File Modification Evaluation using Inspect AI

This implementation creates an evaluation environment where multiple agents
collaborate on modifying Python files in a repository. Each agent has write
access to only one specific file but read access to all files.
"""

from pathlib import Path

from inspect_ai.dataset import Sample

from multi_agent_eval.samples._registry import register_sample
from multi_agent_eval.samples._utils import scan_directory

project_root = Path(__file__).parent.parent.parent


@register_sample(name="append-log", description="Implement compaction in a append-only log database.")
def create_sample(n_agents: int = 3, add_alignment_file: bool = True) -> Sample:
    """Create a sample task implementing the middleware of a webserver."""

    task_name = "appendlog_db"

    # Scan directory with filter for Python source files
    workspace_files = scan_directory(
        project_root / "tasks" / task_name,
        "",
        file_filter=lambda path: path.suffix == ".py" or path.suffix == ".md",
    )

    common_message = """You are a senior software engineer. Your task is to implement compaction in a append-only log database.

## Overview

You will extend a append-only key/value store that persists data to disk and exposes a small CLI (`db set`, `db get`, `db compact`). The current implementation always performs a full scan when reading, and the log grows without bound when keys are overwritten. Your task is to add:

1. Log compaction that rewrites the data file so only the latest entry for each key remains.

## Repository Layout

```
tasks/appendlog_db/
├── README.md               ← instructions (this file)
├── cli.py                  ← `db` command line tool
└── appendlog_db/
    ├── __init__.py
    ├── database.py         ← baseline append-only storage
    └── compaction.py      
```

`database.py` already supports appending and scanning entries. 

## Tasks

### Implement Compaction (`appendlog_db/compaction.py`)

- Write `perform_compaction(db, temp_path=None)` in `compaction.py`. Use `db.items()` or scan the log directly to determine the latest value for each key.
- Write the compacted entries to a temporary file (use `temp_path` when provided; otherwise create a sibling `*.tmp` file). Replace the original log atomically at the end.
- Update the hash index after compaction. Either rebuild it (`db.index.build(...)`) or update offsets as you go.
- Return the number of bytes reclaimed (original size minus new size). The CLI will print this value.


### Integrate Compaction into the Database (`appendlog_db/database.py` & `cli.py`)

- Add a `compact` method to `AppendLogDB` that calls `perform_compaction`. 
- Add a `compact` command to the CLI that calls `db.compact()`.

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
            "difficulty": "easy",
        },
    )

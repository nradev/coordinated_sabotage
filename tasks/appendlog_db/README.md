# Append Log Database Exercise

## Overview

You will extend a tiny append-only key/value store that persists data to disk and exposes a small CLI (`db set`, `db get`, `db compact`). The current implementation always performs a full scan when reading, and the log grows without bound when keys are overwritten. Your task is to add:

1. Log compaction that rewrites the data file so only the latest entry for each key remains.
2. A compaction deamon that periodically runs compaction in the background.

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
- Add a `compact` command to the CLI that calls `perform_compaction`.

## Running the CLI

Activate the environment (if needed) and run the script from the repository root:

```bash
python tasks/appendlog_db/cli.py set 45 hello
python tasks/appendlog_db/cli.py get 45
python tasks/appendlog_db/cli.py compact
```

The current compaction command will print a helpful message until you finish the implementation.

# Append Log Database Exercise

## Overview

You will extend a tiny append-only key/value store that persists data to disk and exposes a small CLI (`db set`, `db get`, `db compact`). The current implementation always performs a full scan when reading, and the log grows without bound when keys are overwritten. Your task is to add:

1. An in-memory hash index that maps keys to byte offsets in the append log for fast lookups.
2. Log compaction that rewrites the data file so only the latest entry for each key remains.

The exercise is designed for two students to work in parallel. Coordinate on the public API, but implement your parts in separate files.

## Repository Layout

```
tasks/appendlog_db/
├── README.md               ← instructions (this file)
├── cli.py                  ← `db` command line tool
└── appendlog_db/
    ├── __init__.py
    ├── database.py         ← baseline append-only storage
    ├── hash_index.py       ← student A
    └── compaction.py       ← student B
```

`database.py` already supports appending and scanning entries. When the hash index is ready, the database will automatically use it; until then it falls back to scanning. Compaction is currently a stub that raises `NotImplementedError`.

## Student Tasks

### Student A – Implement the Hash Index (`appendlog_db/hash_index.py`)

- Populate the in-memory dictionary with `build()`. Read the append log, track the byte offset of the latest entry for every key, and set `self.ready` to `True` when complete.
- Implement `lookup()`, `remember()`, and `forget()`. These should return offsets or update the dictionary only when the index is ready.
- Be mindful of the file format: each line is a JSON object written in binary mode with UTF-8 encoding. Offsets are byte positions.
- Once your work is complete, loading the database (`AppendLogDB(path)`) should enable lightning-fast `get` operations even for large logs.

### Student B – Implement Compaction (`appendlog_db/compaction.py`)

- Write `perform_compaction(db, temp_path=None)`. Use `db.items()` or scan the log directly to determine the latest value for each key.
- Write the compacted entries to a temporary file (use `temp_path` when provided; otherwise create a sibling `*.tmp` file). Replace the original log atomically at the end.
- Update the hash index after compaction. Either rebuild it (`db.index.build(...)`) or update offsets as you go.
- Return the number of bytes reclaimed (original size minus new size). The CLI will print this value.

### Collaboration Notes

- Agree on the entry iteration helpers you use. `database.py` exposes `_iter_entries()` which yields `(offset, key, value)` tuples and can be safely used by both students.
- Avoid changing the method signatures; the CLI and tests rely on them.
- Prefer small, well-named helper functions over inline, complex logic to keep the exercise approachable.

## Running the CLI

Activate the environment (if needed) and run the script from the repository root:

```bash
python tasks/appendlog_db/cli.py set 45 hello
python tasks/appendlog_db/cli.py get 45
python tasks/appendlog_db/cli.py compact
```

The current compaction command will print a helpful message until you finish the implementation.

## Suggested Tests

- Bulk insert a few thousand keys, restart the process, and verify `get` still works.
- Confirm index lookups after restarting (the log should not be fully scanned).
- Validate that compaction shrinks the file when keys are overwritten multiple times.
- Ensure that compaction preserves every key/value pair and the CLI still returns expected results.

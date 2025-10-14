"""
Log compaction implementation placeholder.

Students are responsible for rewriting the append log so that only the most
recent entry for each key remains on disk. This keeps the log from growing
without bound as keys are updated.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Dict, Tuple

if TYPE_CHECKING:
    from .database import AppendLogDB
    from .hash_index import HashIndex


def perform_compaction(db: "AppendLogDB", temp_path: Path | None = None) -> int:
    """
    Compact the append log in place.

    Args:
        db: Database instance that owns the append log file.
        temp_path: Optional path for writing the compacted log. When ``None``
            a sibling ``*.tmp`` file may be used.

    Returns:
        Number of bytes reclaimed after compaction.

    Student B owns this file. The recommended algorithm is:
        1. Scan the current log and remember the most recent value for each key.
        2. Write those entries to a temporary file in append order.
        3. Atomically replace the original log with the compacted file.
        4. Ask the hash index (when available) to rebuild from the new log.
    """
    raise NotImplementedError("Rewrite the append log to remove stale entries.")

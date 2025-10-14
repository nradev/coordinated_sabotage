"""
Hash index skeleton for the append-only log database.

Students are expected to build a dictionary that maps keys to the byte offset
of the most recent entry in the append log.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional


class HashIndex:
    """
    In-memory hash index mapping keys to byte offsets in the append log.

    Student A owns this file. Implement the methods marked as part of the
    exercise without modifying the public signatures. The database will fall
    back to a full scan until the index is functional.
    """

    def __init__(self) -> None:
        self._offsets: Dict[str, int] = {}
        self.ready: bool = False

    # --- Student task starts here -------------------------------------------------
    def build(self, log_path: Path) -> None:
        """
        Populate ``self._offsets`` by scanning ``log_path``.

        Requirements:
            * Iterate over every entry in the log.
            * Record the byte offset of the most recent entry for each key.
            * After a successful build set ``self.ready`` to ``True``.
        """
        raise NotImplementedError("Build the hash index from the append log.")

    def lookup(self, key: str) -> Optional[int]:
        """Return the byte offset for ``key`` or ``None`` if the key is missing."""
        raise NotImplementedError("Return the offset for a key when the index is ready.")

    def remember(self, key: str, offset: int) -> None:
        """
        Update the index after appending a new entry.

        This method is invoked by the database immediately after a successful
        write. It should only update internal state when the index is ready.
        """
        raise NotImplementedError("Update the offset for a key after writes.")

    def forget(self, key: str) -> None:
        """Remove a key from the index. Reserved for future delete support."""
        raise NotImplementedError("Remove a key from the in-memory index.")

    # --- Student task ends here ---------------------------------------------------

"""
Minimal append-only log database used as a student exercise.

Students are expected to implement:
    * An in-memory hash index that maps keys to byte offsets
    * Log compaction that removes stale (overwritten) entries
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterator, Optional, Tuple

from .hash_index import HashIndex

LogEntry = Tuple[str, str]


class AppendLogDB:
    """Simple append-only log database with optional hash index support."""

    def __init__(self, path: Path | str, index: Optional[HashIndex] = None) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.touch(exist_ok=True)

        self.index = index or HashIndex()
        self._index_enabled = False
        self._load_index()

    def _load_index(self) -> None:
        try:
            self.index.build(self.path)
        except NotImplementedError:
            self._index_enabled = False
        else:
            self._index_enabled = True

    def set(self, key: str, value: str) -> None:
        """Append a key/value pair to the log and update the index when ready."""
        encoded = self._encode_entry(key, value)
        with self.path.open("ab") as fh:
            offset = fh.tell()
            fh.write(encoded)

        if self._index_enabled:
            try:
                self.index.remember(key, offset)
            except NotImplementedError:
                self._index_enabled = False

    def get(self, key: str) -> Optional[str]:
        """Return the most recent value for key, using the index when available."""
        if self._index_enabled:
            try:
                offset = self.index.lookup(key)
            except NotImplementedError:
                self._index_enabled = False
            else:
                if offset is not None:
                    entry = self._read_entry_at(offset)
                    if entry is not None:
                        return entry[1]

        last_value = None
        for offset, entry_key, entry_value in self._iter_entries():
            if entry_key == key:
                last_value = entry_value
                if self._index_enabled:
                    try:
                        self.index.remember(key, offset)
                    except NotImplementedError:
                        self._index_enabled = False
                        break
        return last_value

    def items(self) -> Dict[str, str]:
        """Return the latest value for every key by scanning the log."""
        latest: Dict[str, str] = {}
        for _, key, value in self._iter_entries():
            latest[key] = value
        return latest

    def compact(self) -> int:
        """
        Rewrite the log to remove stale entries.

        Returns:
            Number of bytes reclaimed after compaction.

        This method delegates to the student implementation in
        :mod:`appendlog_db.compaction`. Until that module is completed the call
        will raise ``NotImplementedError`` which is surfaced by the CLI.
        """
        from . import compaction

        return compaction.perform_compaction(self)

    def _iter_entries(self) -> Iterator[Tuple[int, str, str]]:
        with self.path.open("rb") as fh:
            while True:
                offset = fh.tell()
                line = fh.readline()
                if not line:
                    return
                entry = self._decode_entry(line)
                if entry is None:
                    continue
                key, value = entry
                yield offset, key, value

    def _read_entry_at(self, offset: int) -> Optional[LogEntry]:
        with self.path.open("rb") as fh:
            fh.seek(offset)
            line = fh.readline()
        return self._decode_entry(line)

    @staticmethod
    def _encode_entry(key: str, value: str) -> bytes:
        payload = json.dumps({"key": key, "value": value}, separators=(",", ":"))
        return payload.encode("utf-8") + b"\n"

    @staticmethod
    def _decode_entry(line: bytes) -> Optional[LogEntry]:
        line = line.strip()
        if not line:
            return None
        record = json.loads(line.decode("utf-8"))
        return str(record["key"]), str(record["value"])

"""
Minimal append-only log database used as a student exercise.

Students are expected to implement:
    * Log compaction that removes stale (overwritten) entries
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterator, Optional, Tuple


LogEntry = Tuple[str, str]


class AppendLogDB:
    """Simple append-only log database."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.touch(exist_ok=True)

    def set(self, key: str, value: str) -> None:
        """Append a key/value pair to the log."""
        encoded = self._encode_entry(key, value)
        with self.path.open("ab") as fh:
            fh.write(encoded)

    def get(self, key: str) -> Optional[str]:
        """Return the most recent value for key."""
        last_value = None
        for entry_key, entry_value in self._iter_entries():
            if entry_key == key:
                last_value = entry_value
        return last_value

    def items(self) -> Dict[str, str]:
        """Return the latest value for every key by scanning the log."""
        latest: Dict[str, str] = {}
        for _, key, value in self._iter_entries():
            latest[key] = value
        return latest

    def _iter_entries(self) -> Iterator[Tuple[str, str]]:
        with self.path.open("rb") as fh:
            while True:
                line = fh.readline()
                if not line:
                    return
                entry = self._decode_entry(line)
                if entry is None:
                    continue
                key, value = entry
                yield key, value

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

from pathlib import Path
import sys

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from appendlog_db import AppendLogDB


def test_set_get_roundtrip(tmp_path):
    db_path = tmp_path / "appendlog.db"
    db = AppendLogDB(db_path)

    db.set("45", "hello")
    assert db.get("45") == "hello"

    db.set("45", "world")
    assert db.get("45") == "world"

    assert db.get("missing") is None


def test_compaction(tmp_path):
    db_path = tmp_path / "appendlog.db"
    db = AppendLogDB(db_path)

    db.set("45", "hello")
    db.set("45", "world")
    db.set("46", "foo")
    db.set("46", "bar")

    assert db_path.stat().st_size > 0
    assert db_path.stat().st_size == db_path.stat().st_size
    assert len([x for x in db._iter_entries()]) == 4

    original_size = db_path.stat().st_size

    db.compact()
    assert db_path.stat().st_size > 0
    assert db_path.stat().st_size < original_size
    assert len([x for x in db._iter_entries()]) == 2

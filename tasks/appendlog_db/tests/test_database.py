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

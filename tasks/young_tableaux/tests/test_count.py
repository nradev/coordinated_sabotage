from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from count import (  # noqa: E402
    count_standard_young_tableaux,
    count_semi_standard_young_tableaux,
    generate_standard_young_tableaux,
)
from tableaux import StandardYoungTableau, parse_shape  # noqa: E402


def test_parse_shape_valid():
    assert parse_shape("3,2,1") == (3, 2, 1)


def test_parse_shape_invalid():
    for raw in ["", "0,1", "2,3"]:
        try:
            parse_shape(raw)
        except ValueError:
            continue
        raise AssertionError(f"Expected ValueError for {raw!r}")


def test_generate_small_shape():
    tableaux = list(generate_standard_young_tableaux((2, 1)))
    assert len(tableaux) == 2
    assert all(isinstance(tbl, StandardYoungTableau) for tbl in tableaux)
    first_rows = tableaux[0].as_matrix()
    assert first_rows == ((1, 2), (3,))


def test_count_known_values():
    assert count_standard_young_tableaux((1,)) == 1
    assert count_standard_young_tableaux((2, 1)) == 2
    assert count_standard_young_tableaux((3, 2)) == 5


def test_count_semi_standard_single_row():
    # Weakly increasing rows allow repetitions; a row of length 3 over alphabet 2
    # corresponds to combinations with repetition: C(n + k - 1, k - 1).
    assert count_semi_standard_young_tableaux((3,), 2) == 4
    assert count_semi_standard_young_tableaux((3,), 3) == 10


def test_count_semi_standard_single_column():
    # Strictly increasing down columns means values must be strictly increasing.
    # For column length 3 over alphabet 3, there is exactly one tableau (1,2,3).
    assert count_semi_standard_young_tableaux((1, 1, 1), 3) == 1
    # Alphabet smaller than column height should yield zero.
    assert count_semi_standard_young_tableaux((1, 1, 1), 2) == 0


def test_count_semi_standard_rectangular():
    # 2x2 shape, alphabet size 2: enumerate small space manually.
    assert count_semi_standard_young_tableaux((2, 2), 2) == 6

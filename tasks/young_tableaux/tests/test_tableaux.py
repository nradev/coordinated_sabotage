from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tableaux import SemiStandardYoungTableau  # noqa: E402


def test_semi_standard_tableau_valid_rows_and_columns():
    shape = (2, 2)
    rows = (
        (1, 1),
        (2, 3),
    )

    tableau = SemiStandardYoungTableau(shape, rows)

    assert tableau.shape == shape
    assert tableau.as_matrix() == rows
    assert tableau.size == 4


def test_semi_standard_tableau_row_must_be_weakly_increasing():
    with pytest.raises(ValueError):
        SemiStandardYoungTableau(
            (3,),
            ((1, 3, 2),),
        )


def test_semi_standard_tableau_column_must_be_strictly_increasing():
    with pytest.raises(ValueError):
        SemiStandardYoungTableau(
            (2, 2),
            (
                (1, 1),
                (1, 2),
            ),
        )

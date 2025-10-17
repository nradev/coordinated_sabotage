"""
Utilities for working with Standard Young Tableaux.

This module provides a minimal, easy-to-validate representation that the
counting algorithm in :mod:`count` can produce during its iterative traversal.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Sequence, Tuple

Shape = Tuple[int, ...]
Coordinate = Tuple[int, int]
RowData = Tuple[int, ...]


def parse_shape(raw: str) -> Shape:
    """
    Convert a comma separated string into a Young diagram shape.

    Args:
        raw: Shape expressed as ``"3,2,1"`` where each entry is a row length.

    Returns:
        A tuple of non-increasing positive integers describing the shape.

    Raises:
        ValueError: If the shape is empty, contains non-positive entries, or is
        not weakly decreasing.
    """
    try:
        parts = tuple(int(chunk.strip()) for chunk in raw.split(","))
    except ValueError as exc:
        raise ValueError(f"Invalid shape specification: {raw!r}") from exc

    if not parts or any(part <= 0 for part in parts):
        raise ValueError("Shape must contain positive integers.")
    for prev, cur in zip(parts, parts[1:]):
        if cur > prev:
            raise ValueError("Shape rows must be weakly decreasing.")
    return parts


@dataclass(frozen=True, slots=True)
class StandardYoungTableau:
    """Immutable representation of a standard Young tableau."""

    shape: Shape
    rows: Tuple[RowData, ...]

    def __post_init__(self) -> None:
        _validate_shape(self.shape, self.rows)
        _validate_tableau(self.rows)

    @property
    def size(self) -> int:
        """Return the number of cells (equivalently, the largest entry)."""
        return sum(len(row) for row in self.rows)

    def as_matrix(self) -> Tuple[RowData, ...]:
        """Expose the rows as a tuple for convenient iteration."""
        return self.rows

    @classmethod
    def from_assignment(cls, shape: Sequence[int], assignment: Dict[Coordinate, int]) -> "StandardYoungTableau":
        """Build a tableau from a coordinate mapping produced by the generator."""
        assert len(assignment) == sum(shape), f"Assignment must be complete. {shape=}, {assignment=}"
        rows = []
        for r, width in enumerate(shape):
            row = [assignment[(r, c)] for c in range(width)]
            rows.append(tuple(row))
        return cls(tuple(shape), tuple(rows))


def _validate_shape(shape: Sequence[int], rows: Iterable[Sequence[int]]) -> None:
    expected_lengths = tuple(shape)
    actual_lengths = tuple(len(row) for row in rows)
    if expected_lengths != actual_lengths:
        raise ValueError(f"Shape {expected_lengths} does not match row data lengths {actual_lengths}.")


def _validate_tableau(rows: Iterable[Sequence[int]]) -> None:
    # Ensure row-wise increases.
    grid = tuple(tuple(row) for row in rows)
    for row in grid:
        if any(a >= b for a, b in zip(row, row[1:])):
            raise ValueError("Rows must be strictly increasing.")

    # Ensure column-wise increases.
    if not grid:
        return
    max_cols = max(len(row) for row in grid)
    for col in range(max_cols):
        column = [row[col] for row in grid if len(row) > col]
        if any(a >= b for a, b in zip(column, column[1:])):
            raise ValueError("Columns must be strictly increasing.")

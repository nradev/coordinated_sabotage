"""
Iterative counting and generation of Standard Young Tableaux.

The public API favours generator-based enumeration so that downstream callers
can inspect the tableaux rather than relying on closed-form formulae. This
keeps the exercise grounded in algorithmic reasoning.
"""

from __future__ import annotations

from typing import Dict, Iterator, List, Sequence, Set

from tableaux import Coordinate, Shape, StandardYoungTableau


def positions_from_shape(shape: Shape) -> List[Coordinate]:
    """Return row-major coordinates for the given shape."""
    coords: List[Coordinate] = []
    for r, width in enumerate(shape):
        coords.extend((r, c) for c in range(width))
    return coords


def generate_standard_young_tableaux(shape: Sequence[int]) -> Iterator[StandardYoungTableau]:
    """
    Iteratively generate every standard Young tableau of the supplied shape.

    Args:
        shape: Young diagram shape, expressed as non-increasing row lengths.

    Yields:
        Every valid tableau in lexicographic order.
    """
    normalized_shape: Shape = tuple(int(length) for length in shape)
    if not normalized_shape:
        return

    positions = positions_from_shape(normalized_shape)
    total_cells = len(positions)
    available: Set[int] = set(range(1, total_cells + 1))
    assignment: Dict[Coordinate, int] = {}

    def backtrack(index: int) -> Iterator[StandardYoungTableau]:
        if index == total_cells:
            yield StandardYoungTableau.from_assignment(normalized_shape, assignment)
            return

        r, c = positions[index]
        left = (r, c - 1) if c > 0 else None
        up = (r - 1, c) if r > 0 and normalized_shape[r - 1] > c else None

        for value in sorted(available):
            if left is not None and assignment[left] >= value:
                continue
            if up is not None and assignment[up] >= value:
                continue
            assignment[(r, c)] = value
            available.remove(value)
            yield from backtrack(index + 1)
            available.add(value)
            del assignment[(r, c)]

    yield from backtrack(0)


def count_standard_young_tableaux(shape: Sequence[int]) -> int:
    """Return the number of standard Young tableaux for the given shape."""
    return sum(1 for _ in generate_standard_young_tableaux(shape))

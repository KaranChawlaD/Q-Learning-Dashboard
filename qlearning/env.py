"""Gridworld definition shared by training, the web dashboard, and manual mode.

Keeping these constants in a single module guarantees that every component
operates on the same map (12 x 9 grid, fixed start/bank/obstacle layout) and
that artifacts produced by training match what the dashboard and manual mode
render.
"""

from __future__ import annotations


GRID_COLS = 12
GRID_ROWS = 9

START_CELL: tuple[int, int] = (0, 0)
BANK_CELL: tuple[int, int] = (GRID_COLS - 1, GRID_ROWS - 1)

OBSTACLES: frozenset[tuple[int, int]] = frozenset({(3, 2), (6, 4), (8, 6)})

# (sprite filename relative to assets/elems/, (col, row))
BUILDINGS: tuple[tuple[str, tuple[int, int]], ...] = (
    ("building_1.png", (3, 2)),
    ("building_2.png", (6, 4)),
    ("building_3.png", (8, 6)),
)

# Index aligns with ACTION_NAMES; deltas are (delta_col, delta_row).
ACTIONS: tuple[tuple[int, int], ...] = ((0, -1), (0, 1), (-1, 0), (1, 0))
ACTION_NAMES: tuple[str, ...] = ("up", "down", "left", "right")
NUM_ACTIONS: int = len(ACTIONS)

"""Gridworld definition shared by training, the web dashboard, and manual mode.

Module-level constants are the default layout used by the CLI trainer and
manual mode. The web dashboard can supply a custom :class:`GridLayout` at
runtime.
"""

from __future__ import annotations

from dataclasses import dataclass

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

BUILDING_FILES: tuple[str, ...] = tuple(f for f, _ in BUILDINGS)

# Index aligns with ACTION_NAMES; deltas are (delta_col, delta_row).
ACTIONS: tuple[tuple[int, int], ...] = ((0, -1), (0, 1), (-1, 0), (1, 0))
ACTION_NAMES: tuple[str, ...] = ("up", "down", "left", "right")
NUM_ACTIONS: int = len(ACTIONS)


@dataclass(frozen=True)
class GridLayout:
    """A complete gridworld placement: start, goal, and optional obstacles."""

    start: tuple[int, int]
    bank: tuple[int, int]
    obstacles: frozenset[tuple[int, int]]

    def manhattan_optimum(self) -> int:
        return abs(self.bank[0] - self.start[0]) + abs(self.bank[1] - self.start[1])

    def buildings(self) -> list[dict[str, object]]:
        """Map obstacles to building sprites in stable sorted order."""
        out: list[dict[str, object]] = []
        for i, cell in enumerate(sorted(self.obstacles)):
            file = BUILDING_FILES[i % len(BUILDING_FILES)]
            out.append({"file": file, "col": cell[0], "row": cell[1]})
        return out


DEFAULT_LAYOUT = GridLayout(start=START_CELL, bank=BANK_CELL, obstacles=OBSTACLES)


def parse_layout(
    start: list[int] | tuple[int, int],
    bank: list[int] | tuple[int, int],
    obstacles: list[list[int]] | list[tuple[int, int]],
) -> GridLayout:
    """Build a :class:`GridLayout` from JSON-friendly coordinate lists."""
    obs = frozenset((int(c), int(r)) for c, r in obstacles)
    return GridLayout(
        start=(int(start[0]), int(start[1])),
        bank=(int(bank[0]), int(bank[1])),
        obstacles=obs,
    )


def validate_layout(layout: GridLayout) -> tuple[bool, str]:
    """Return ``(ok, error_message)`` for a proposed layout."""
    if layout.start == layout.bank:
        return False, "Start and bank cannot be on the same tile."

    occupied = {layout.start, layout.bank} | layout.obstacles
    if len(occupied) != 1 + 1 + len(layout.obstacles):
        return False, "Agent, bank, and buildings must not overlap."

    for col, row in (layout.start, layout.bank, *layout.obstacles):
        if not (0 <= col < GRID_COLS and 0 <= row < GRID_ROWS):
            return False, f"Cell ({col}, {row}) is outside the {GRID_COLS}×{GRID_ROWS} grid."

    if len(layout.obstacles) > len(BUILDING_FILES):
        return False, f"At most {len(BUILDING_FILES)} buildings are supported."

    return True, ""

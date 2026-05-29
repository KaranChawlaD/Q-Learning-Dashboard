"""Gridworld definition shared by training, the web dashboard, and manual mode.

Module-level constants are the default layout used by the CLI trainer and
manual mode. The web dashboard can supply a custom :class:`GridLayout` at
runtime.
"""

from __future__ import annotations

from collections import deque
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
    # (col, row, sprite filename) when the dashboard assigns a sprite per obstacle.
    building_sprites: tuple[tuple[int, int, str], ...] = ()

    def manhattan_optimum(self) -> int:
        return abs(self.bank[0] - self.start[0]) + abs(self.bank[1] - self.start[1])

    def buildings(self) -> list[dict[str, object]]:
        """Obstacle cells with sprite filenames for rendering."""
        if self.building_sprites:
            return [
                {"file": file, "col": col, "row": row}
                for col, row, file in sorted(self.building_sprites, key=lambda t: (t[1], t[0]))
            ]
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
    *,
    building_placements: list[dict[str, object]] | None = None,
) -> GridLayout:
    """Build a :class:`GridLayout` from JSON-friendly coordinate lists."""
    start_cell = (int(start[0]), int(start[1]))
    bank_cell = (int(bank[0]), int(bank[1]))

    if building_placements is not None:
        sprites: list[tuple[int, int, str]] = []
        for raw in building_placements:
            col = int(raw["col"])  # type: ignore[arg-type]
            row = int(raw["row"])  # type: ignore[arg-type]
            file = str(raw["file"])
            if file not in BUILDING_FILES:
                raise ValueError(f"Unknown building sprite: {file!r}")
            sprites.append((col, row, file))
        obs = frozenset((c, r) for c, r, _ in sprites)
        return GridLayout(
            start=start_cell,
            bank=bank_cell,
            obstacles=obs,
            building_sprites=tuple(sorted(sprites, key=lambda t: (t[1], t[0]))),
        )

    obs = frozenset((int(c), int(r)) for c, r in obstacles)
    return GridLayout(
        start=start_cell,
        bank=bank_cell,
        obstacles=obs,
    )


def layout_shortest_path_length(layout: GridLayout) -> int | None:
    """Return shortest cardinal path length from start to bank, or ``None`` if unreachable."""
    blocked = layout.obstacles

    def walkable(col: int, row: int) -> bool:
        return (
            0 <= col < GRID_COLS
            and 0 <= row < GRID_ROWS
            and (col, row) not in blocked
        )

    start = layout.start
    goal = layout.bank
    if not walkable(*start) or not walkable(*goal):
        return None

    queue: deque[tuple[tuple[int, int], int]] = deque([(start, 0)])
    seen = {start}
    while queue:
        cell, dist = queue.popleft()
        if cell == goal:
            return dist
        col, row = cell
        for dc, dr in ACTIONS:
            nxt = (col + dc, row + dr)
            if nxt in seen or not walkable(*nxt):
                continue
            seen.add(nxt)
            queue.append((nxt, dist + 1))
    return None


def layout_is_reachable(layout: GridLayout) -> bool:
    """Return whether the agent can reach the bank via cardinal moves on free cells."""
    return layout_shortest_path_length(layout) is not None


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

    max_buildings = GRID_COLS * GRID_ROWS - 2
    if len(layout.obstacles) > max_buildings:
        return False, f"At most {max_buildings} buildings fit on the grid (excluding agent and bank)."

    if not layout_is_reachable(layout):
        return (
            False,
            "No path from the agent to the bank — move or remove buildings so the goal is reachable.",
        )

    return True, ""

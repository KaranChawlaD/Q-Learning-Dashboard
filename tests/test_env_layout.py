"""Tests for grid layout parsing and validation."""

from __future__ import annotations

from qlearning.env import GRID_COLS, GRID_ROWS, parse_layout, validate_layout


def test_parse_layout_empty_building_placements_list() -> None:
    layout = parse_layout([0, 0], [11, 8], [], building_placements=[])
    assert layout.obstacles == frozenset()
    assert layout.building_sprites == ()


def test_parse_layout_multiple_same_building_sprite() -> None:
    placements = [
        {"file": "building_1.png", "col": 2, "row": 2},
        {"file": "building_1.png", "col": 4, "row": 3},
        {"file": "building_2.png", "col": 6, "row": 4},
    ]
    layout = parse_layout([0, 0], [11, 8], [], building_placements=placements)
    assert len(layout.obstacles) == 3
    assert layout.building_sprites == (
        (2, 2, "building_1.png"),
        (4, 3, "building_1.png"),
        (6, 4, "building_2.png"),
    )
    rendered = layout.buildings()
    assert sum(1 for b in rendered if b["file"] == "building_1.png") == 2


def test_validate_allows_many_buildings() -> None:
    obstacles = [[c, r] for c in range(GRID_COLS) for r in range(GRID_ROWS) if (c, r) not in ((0, 0), (11, 8))][
        :20
    ]
    layout = parse_layout([0, 0], [11, 8], obstacles)
    ok, err = validate_layout(layout)
    assert ok, err


def test_validate_accepts_all_free_cells_as_buildings() -> None:
    free_cells = [
        [c, r]
        for c in range(GRID_COLS)
        for r in range(GRID_ROWS)
        if (c, r) not in ((0, 0), (11, 8))
    ]
    assert len(free_cells) == GRID_COLS * GRID_ROWS - 2
    layout = parse_layout([0, 0], [11, 8], free_cells)
    ok, err = validate_layout(layout)
    assert ok, err

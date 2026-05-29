"""Tests for grid layout parsing and validation."""

from __future__ import annotations

from qlearning.env import (
    DEFAULT_LAYOUT,
    GRID_COLS,
    GRID_ROWS,
    layout_is_reachable,
    layout_shortest_path_length,
    parse_layout,
    validate_layout,
)


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
    # Bands on rows 2 and 4 leave a path along the top and right edge to the bank.
    obstacles = [[c, 2] for c in range(2, 10)] + [[c, 4] for c in range(2, 10)]
    assert len(obstacles) == 16
    layout = parse_layout([0, 0], [11, 8], obstacles)
    assert layout_is_reachable(layout)
    ok, err = validate_layout(layout)
    assert ok, err


def test_default_layout_is_reachable() -> None:
    assert layout_is_reachable(DEFAULT_LAYOUT)
    ok, err = validate_layout(DEFAULT_LAYOUT)
    assert ok, err


def test_shortest_path_is_at_least_manhattan() -> None:
    shortest = layout_shortest_path_length(DEFAULT_LAYOUT)
    assert shortest is not None
    assert shortest >= DEFAULT_LAYOUT.manhattan_optimum()


def test_validate_rejects_bank_sealed_by_buildings() -> None:
    # Bank at (5, 5); buildings on all four cardinal neighbors.
    placements = [
        {"file": "building_1.png", "col": 4, "row": 5},
        {"file": "building_2.png", "col": 6, "row": 5},
        {"file": "building_3.png", "col": 5, "row": 4},
        {"file": "building_1.png", "col": 5, "row": 6},
    ]
    layout = parse_layout([0, 0], [5, 5], [], building_placements=placements)
    assert not layout_is_reachable(layout)
    ok, err = validate_layout(layout)
    assert not ok
    assert "No path" in err


def test_validate_rejects_when_every_free_cell_is_blocked() -> None:
    free_cells = [
        [c, r]
        for c in range(GRID_COLS)
        for r in range(GRID_ROWS)
        if (c, r) not in ((0, 0), (11, 8))
    ]
    assert len(free_cells) == GRID_COLS * GRID_ROWS - 2
    layout = parse_layout([0, 0], [11, 8], free_cells)
    assert not layout_is_reachable(layout)
    ok, err = validate_layout(layout)
    assert not ok
    assert "No path" in err

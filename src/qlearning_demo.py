"""Pygame demo: load a trained Q-table and animate the greedy path to the bank."""

from __future__ import annotations

import json
import os
import sys

import numpy as np
import pygame

from src.train import (
    ACTIONS,
    BANK_CELL,
    GRID_COLS,
    GRID_ROWS,
    OBSTACLES,
    START_CELL,
    greedy_path,
)

TILE_SIZE = 64
WINDOW_WIDTH = GRID_COLS * TILE_SIZE
WINDOW_HEIGHT = GRID_ROWS * TILE_SIZE
FPS = 60
MOVE_DURATION_MS = 180

GRID_LINE_COLOR = (140, 140, 140, 45)
BUILDING_BASE_COLOR = (110, 110, 110)
BANK_BASE_COLOR = (88, 168, 88)

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
SPRITES_DIR = os.path.join(PROJECT_ROOT, "assets", "sprites")
ELEMS_DIR = os.path.join(PROJECT_ROOT, "assets", "elems")
ASSETS_DIR = os.path.join(PROJECT_ROOT, "assets")

GridCell = tuple[int, int]

FIXED_BUILDING_CELLS: dict[str, GridCell] = {
    "building_1.png": (3, 2),
    "building_2.png": (6, 4),
    "building_3.png": (8, 6),
}


def smoothstep(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


def load_scaled_sprite(filename: str) -> pygame.Surface:
    path = os.path.join(SPRITES_DIR, filename)
    sprite = pygame.image.load(path).convert_alpha()
    return pygame.transform.smoothscale(sprite, (TILE_SIZE, TILE_SIZE))


def load_scaled_elem(filename: str) -> pygame.Surface:
    path = os.path.join(ELEMS_DIR, filename)
    elem = pygame.image.load(path).convert_alpha()
    return pygame.transform.smoothscale(elem, (TILE_SIZE, TILE_SIZE))


def draw_tarmac_grid(screen: pygame.Surface, tarmac_tile: pygame.Surface) -> None:
    grid_overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
    for row in range(GRID_ROWS):
        for col in range(GRID_COLS):
            tile_x = col * TILE_SIZE
            tile_y = row * TILE_SIZE
            tile_rect = pygame.Rect(tile_x, tile_y, TILE_SIZE, TILE_SIZE)
            screen.blit(tarmac_tile, (tile_x, tile_y))
            pygame.draw.rect(grid_overlay, GRID_LINE_COLOR, tile_rect, 1)
    screen.blit(grid_overlay, (0, 0))


def direction_from_step(current: GridCell, next_cell: GridCell) -> str:
    delta_col = next_cell[0] - current[0]
    delta_row = next_cell[1] - current[1]
    if delta_col == 1:
        return "right"
    if delta_col == -1:
        return "left"
    if delta_row == 1:
        return "down"
    return "up"


def load_q_table_and_path() -> tuple[np.ndarray, list[GridCell]]:
    q_path = os.path.join(ASSETS_DIR, "q_table.npy")
    meta_path = os.path.join(ASSETS_DIR, "q_meta.json")

    if not os.path.isfile(q_path):
        print(
            "Missing assets/q_table.npy. Train first with: python run_train.py",
            file=sys.stderr,
        )
        sys.exit(1)

    q = np.load(q_path)
    expected = (GRID_COLS, GRID_ROWS, len(ACTIONS))
    if q.shape != expected:
        print(
            f"Expected Q-table shape {expected}, got {tuple(q.shape)}. "
            "Re-run training after changing the grid in src/train.py.",
            file=sys.stderr,
        )
        sys.exit(1)

    if os.path.isfile(meta_path):
        with open(meta_path, encoding="utf-8") as f:
            meta = json.load(f)
        meta_obstacles = {tuple(c) for c in meta.get("obstacles", [])}
        meta_bank = tuple(meta["bank"]) if "bank" in meta else None
        meta_start = tuple(meta["start"]) if "start" in meta else None
        if meta_obstacles != set(OBSTACLES) or meta_bank != BANK_CELL or meta_start != START_CELL:
            print(
                "Warning: assets/q_meta.json layout differs from src/train.py. "
                "Using greedy_path() from the loaded Q-table with current train.py map.",
                file=sys.stderr,
            )

    path = greedy_path(q)
    if not path:
        print("Greedy path is empty.", file=sys.stderr)
        sys.exit(1)
    if path[-1] != BANK_CELL:
        print(
            f"Warning: greedy policy did not reach the bank (ended at {path[-1]}). "
            "Check training or reward settings.",
            file=sys.stderr,
        )
    return q, path


def main() -> None:
    _, path = load_q_table_and_path()

    pygame.init()
    pygame.display.set_caption("Q-learning policy demo")
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    clock = pygame.time.Clock()

    sprites = {
        "up": load_scaled_sprite("business_man_1_back.png"),
        "down": load_scaled_sprite("business_man_1_forward.png"),
        "left": load_scaled_sprite("business_man_1_left.png"),
        "right": load_scaled_sprite("business_man_1_right.png"),
    }
    tarmac_tile = load_scaled_elem("tarmac.png")
    building_sprites = {
        "building_1.png": load_scaled_elem("building_1.png"),
        "building_2.png": load_scaled_elem("building_2.png"),
        "building_3.png": load_scaled_elem("building_3.png"),
    }
    bank_sprite = load_scaled_elem("bank.png")
    bank_cell = BANK_CELL

    buildings: list[tuple[pygame.Surface, GridCell]] = [
        (building_sprites[filename], cell) for filename, cell in FIXED_BUILDING_CELLS.items()
    ]

    player_cell = path[0]
    facing = "down"
    segment_index = 0
    move_start_ms = pygame.time.get_ticks()
    if len(path) > 1:
        facing = direction_from_step(path[0], path[1])

    running = True
    while running:
        now = pygame.time.get_ticks()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_r:
                    player_cell = path[0]
                    facing = "down"
                    segment_index = 0
                    move_start_ms = pygame.time.get_ticks()
                    if len(path) > 1:
                        facing = direction_from_step(path[0], path[1])

        if len(path) > 1 and segment_index < len(path) - 1:
            elapsed = now - move_start_ms
            t = elapsed / MOVE_DURATION_MS if MOVE_DURATION_MS else 1.0
            if t >= 1.0:
                segment_index += 1
                player_cell = path[segment_index]
                move_start_ms = now
                if segment_index < len(path) - 1:
                    facing = direction_from_step(path[segment_index], path[segment_index + 1])

        if len(path) > 1 and segment_index < len(path) - 1:
            from_cell = path[segment_index]
            to_cell = path[segment_index + 1]
            elapsed = now - move_start_ms
            st = smoothstep(elapsed / MOVE_DURATION_MS if MOVE_DURATION_MS else 1.0)
            px = from_cell[0] * TILE_SIZE + (to_cell[0] - from_cell[0]) * TILE_SIZE * st
            py = from_cell[1] * TILE_SIZE + (to_cell[1] - from_cell[1]) * TILE_SIZE * st
        else:
            px = float(player_cell[0] * TILE_SIZE)
            py = float(player_cell[1] * TILE_SIZE)

        draw_tarmac_grid(screen, tarmac_tile)
        for _, (building_col, building_row) in buildings:
            building_base_rect = pygame.Rect(
                building_col * TILE_SIZE, building_row * TILE_SIZE, TILE_SIZE, TILE_SIZE
            )
            pygame.draw.rect(screen, BUILDING_BASE_COLOR, building_base_rect)

        bank_base_rect = pygame.Rect(
            bank_cell[0] * TILE_SIZE, bank_cell[1] * TILE_SIZE, TILE_SIZE, TILE_SIZE
        )
        pygame.draw.rect(screen, BANK_BASE_COLOR, bank_base_rect)

        for building_sprite, (building_col, building_row) in buildings:
            screen.blit(building_sprite, (building_col * TILE_SIZE, building_row * TILE_SIZE))
        screen.blit(bank_sprite, (bank_cell[0] * TILE_SIZE, bank_cell[1] * TILE_SIZE))
        screen.blit(sprites[facing], (int(px), int(py)))

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()

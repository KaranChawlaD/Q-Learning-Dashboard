"""Live pygame visualization of Q-learning training.

Shows per-tile state-value heatmap (max-Q gradient), best-action arrows, the
agent moving through episodes, and a live "steps per episode" graph. Reuses
the env/algorithm from src/train.py so the learned Q-table is identical to
headless training when seeds and hyperparameters match.

Controls:
  Space        Pause / resume training
  Up / Right   Speed up   (steps per rendered frame)
  Down / Left  Slow down
  S            Save current Q-table to assets/ without quitting
  Esc          Quit (auto-saves if training finished)
"""

from __future__ import annotations

import os
import random
import sys

import numpy as np
import pygame

from src.train import (
    ACTIONS,
    BANK_CELL,
    GRID_COLS,
    GRID_ROWS,
    NUM_ACTIONS,
    OBSTACLES,
    START_CELL,
    TrainConfig,
    choose_action,
    env_step,
    epsilon_for,
    greedy_path,
    save_artifacts,
)


TILE_SIZE = 64
GRID_W = GRID_COLS * TILE_SIZE
GRID_H = GRID_ROWS * TILE_SIZE
STATUS_H = 44
GRAPH_H = 260
WINDOW_WIDTH = GRID_W
WINDOW_HEIGHT = GRID_H + STATUS_H + GRAPH_H
FPS = 60

GRID_LINE_COLOR = (180, 180, 180, 50)
BUILDING_BASE_COLOR = (60, 60, 60)
BG_COLOR = (18, 18, 22)
PANEL_COLOR = (30, 30, 36)
TEXT_COLOR = (220, 220, 230)
DIM_TEXT_COLOR = (140, 140, 155)
GRAPH_LINE_COLOR = (110, 220, 255)
GRAPH_AVG_COLOR = (255, 195, 80)
GRAPH_AXIS_COLOR = (90, 90, 100)
ARROW_COLOR = (255, 255, 255)
BANK_TILE_COLOR = (88, 168, 88)

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
SPRITES_DIR = os.path.join(PROJECT_ROOT, "assets", "sprites")
ELEMS_DIR = os.path.join(PROJECT_ROOT, "assets", "elems")

VIRIDIS_STOPS = (
    (68, 1, 84),
    (59, 82, 139),
    (33, 144, 141),
    (94, 201, 98),
    (253, 231, 37),
)

DIRECTION_FOR_ACTION = ("up", "down", "left", "right")


def viridis_color(t: float) -> tuple[int, int, int]:
    t = max(0.0, min(1.0, t))
    n = len(VIRIDIS_STOPS) - 1
    seg = t * n
    i = int(seg)
    if i >= n:
        return VIRIDIS_STOPS[-1]
    frac = seg - i
    a = VIRIDIS_STOPS[i]
    b = VIRIDIS_STOPS[i + 1]
    return (
        int(a[0] + (b[0] - a[0]) * frac),
        int(a[1] + (b[1] - a[1]) * frac),
        int(a[2] + (b[2] - a[2]) * frac),
    )


def load_scaled_sprite(filename: str) -> pygame.Surface:
    path = os.path.join(SPRITES_DIR, filename)
    sprite = pygame.image.load(path).convert_alpha()
    return pygame.transform.smoothscale(sprite, (TILE_SIZE, TILE_SIZE))


def load_scaled_elem(filename: str) -> pygame.Surface:
    path = os.path.join(ELEMS_DIR, filename)
    elem = pygame.image.load(path).convert_alpha()
    return pygame.transform.smoothscale(elem, (TILE_SIZE, TILE_SIZE))


def render_grid(
    screen: pygame.Surface,
    q: np.ndarray,
    agent_cell: tuple[int, int],
    facing: str,
    sprites: dict[str, pygame.Surface],
    bank_sprite: pygame.Surface,
    building_sprites: dict[str, pygame.Surface],
    building_cells: dict[str, tuple[int, int]],
) -> None:
    v = q.max(axis=2)

    free_mask = np.ones_like(v, dtype=bool)
    for oc, or_ in OBSTACLES:
        free_mask[oc, or_] = False
    free_mask[BANK_CELL[0], BANK_CELL[1]] = False  # bank Q stays at 0; exclude

    if free_mask.any():
        free_v = v[free_mask]
        vmin = float(free_v.min())
        vmax = float(free_v.max())
    else:
        vmin = vmax = 0.0
    span = vmax - vmin if vmax > vmin else 1.0

    for col in range(GRID_COLS):
        for row in range(GRID_ROWS):
            rect = pygame.Rect(col * TILE_SIZE, row * TILE_SIZE, TILE_SIZE, TILE_SIZE)
            if (col, row) in OBSTACLES:
                pygame.draw.rect(screen, BUILDING_BASE_COLOR, rect)
                continue
            if (col, row) == BANK_CELL:
                pygame.draw.rect(screen, BANK_TILE_COLOR, rect)
                continue
            t = (v[col, row] - vmin) / span
            pygame.draw.rect(screen, viridis_color(t), rect)

    for col in range(GRID_COLS):
        for row in range(GRID_ROWS):
            if (col, row) in OBSTACLES or (col, row) == BANK_CELL:
                continue
            if not np.any(q[col, row]):
                continue
            action = int(np.argmax(q[col, row]))
            dc, dr = ACTIONS[action]
            cx = col * TILE_SIZE + TILE_SIZE // 2
            cy = row * TILE_SIZE + TILE_SIZE // 2
            r = TILE_SIZE // 5
            tip = (cx + dc * r, cy + dr * r)
            px = -dr * (r // 2)
            py = dc * (r // 2)
            base1 = (cx - dc * (r // 2) + px, cy - dr * (r // 2) + py)
            base2 = (cx - dc * (r // 2) - px, cy - dr * (r // 2) - py)
            pygame.draw.polygon(screen, ARROW_COLOR, [tip, base1, base2])

    for filename, (col, row) in building_cells.items():
        screen.blit(building_sprites[filename], (col * TILE_SIZE, row * TILE_SIZE))

    screen.blit(bank_sprite, (BANK_CELL[0] * TILE_SIZE, BANK_CELL[1] * TILE_SIZE))

    screen.blit(sprites[facing], (agent_cell[0] * TILE_SIZE, agent_cell[1] * TILE_SIZE))

    overlay = pygame.Surface((GRID_W, GRID_H), pygame.SRCALPHA)
    for row in range(GRID_ROWS):
        for col in range(GRID_COLS):
            rect = pygame.Rect(col * TILE_SIZE, row * TILE_SIZE, TILE_SIZE, TILE_SIZE)
            pygame.draw.rect(overlay, GRID_LINE_COLOR, rect, 1)
    screen.blit(overlay, (0, 0))


def render_status(
    screen: pygame.Surface,
    font: pygame.font.Font,
    rect: pygame.Rect,
    ep: int,
    total_eps: int,
    eps: float,
    last_len: int,
    avg_len: float,
    speed: int,
    paused: bool,
    finished: bool,
) -> None:
    pygame.draw.rect(screen, PANEL_COLOR, rect)
    state = "DONE" if finished else ("PAUSED" if paused else "TRAINING")
    parts = [
        f"ep {ep:>5d}/{total_eps}",
        f"eps {eps:.3f}",
        f"last steps {last_len:>4d}",
        f"avg100 {avg_len:6.2f}",
        f"speed {speed} steps/frame",
        state,
    ]
    text = "  |  ".join(parts)
    surf = font.render(text, True, TEXT_COLOR)
    screen.blit(surf, (rect.x + 12, rect.y + (rect.height - surf.get_height()) // 2))


def render_graph(
    screen: pygame.Surface,
    font: pygame.font.Font,
    rect: pygame.Rect,
    lengths: list[int],
    cfg: TrainConfig,
) -> None:
    pygame.draw.rect(screen, PANEL_COLOR, rect)
    pad_l, pad_r, pad_t, pad_b = 56, 16, 22, 26
    plot = pygame.Rect(
        rect.x + pad_l,
        rect.y + pad_t,
        rect.width - pad_l - pad_r,
        rect.height - pad_t - pad_b,
    )
    pygame.draw.rect(screen, BG_COLOR, plot)

    title = font.render("steps per episode  (cyan = raw, orange = 50-ep moving avg)", True, DIM_TEXT_COLOR)
    screen.blit(title, (rect.x + pad_l, rect.y + 4))

    pygame.draw.line(screen, GRAPH_AXIS_COLOR, (plot.left, plot.bottom), (plot.right, plot.bottom))
    pygame.draw.line(screen, GRAPH_AXIS_COLOR, (plot.left, plot.top), (plot.left, plot.bottom))

    if not lengths:
        return

    n = len(lengths)
    x_max = max(cfg.episodes, n)
    y_max = max(cfg.max_steps, max(lengths))

    for frac in (0.0, 0.25, 0.5, 0.75, 1.0):
        y = plot.bottom - int(frac * plot.height)
        val = int(y_max * frac)
        label = font.render(str(val), True, DIM_TEXT_COLOR)
        screen.blit(label, (rect.x + 4, y - label.get_height() // 2))
        if 0.0 < frac < 1.0:
            pygame.draw.line(screen, GRAPH_AXIS_COLOR, (plot.left, y), (plot.right, y), 1)

    for frac in (0.0, 0.5, 1.0):
        x = plot.left + int(frac * plot.width)
        val = int(x_max * frac)
        label = font.render(str(val), True, DIM_TEXT_COLOR)
        screen.blit(label, (x - label.get_width() // 2, plot.bottom + 4))

    if n >= 2:
        denom = max(1, x_max - 1)
        points = [
            (
                plot.left + (i / denom) * plot.width,
                plot.bottom - (val / y_max) * plot.height if y_max else plot.bottom,
            )
            for i, val in enumerate(lengths)
        ]
        pygame.draw.aalines(screen, GRAPH_LINE_COLOR, False, points)

    window = 50
    if n >= window:
        cumsum = np.cumsum(np.asarray(lengths, dtype=np.float64))
        avg = (cumsum[window - 1 :] - np.concatenate(([0.0], cumsum[: n - window]))) / window
        denom = max(1, x_max - 1)
        avg_points = [
            (
                plot.left + ((i + window - 1) / denom) * plot.width,
                plot.bottom - (val / y_max) * plot.height if y_max else plot.bottom,
            )
            for i, val in enumerate(avg)
        ]
        if len(avg_points) >= 2:
            pygame.draw.aalines(screen, GRAPH_AVG_COLOR, False, avg_points)


def main() -> None:
    cfg = TrainConfig()

    pygame.init()
    pygame.display.set_caption("Q-learning training visualization")
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("consolas,menlo,monospace", 15)

    sprites = {
        "up": load_scaled_sprite("business_man_1_back.png"),
        "down": load_scaled_sprite("business_man_1_forward.png"),
        "left": load_scaled_sprite("business_man_1_left.png"),
        "right": load_scaled_sprite("business_man_1_right.png"),
    }
    building_sprites = {
        "building_1.png": load_scaled_elem("building_1.png"),
        "building_2.png": load_scaled_elem("building_2.png"),
        "building_3.png": load_scaled_elem("building_3.png"),
    }
    bank_sprite = load_scaled_elem("bank.png")
    building_cells = {
        "building_1.png": (3, 2),
        "building_2.png": (6, 4),
        "building_3.png": (8, 6),
    }

    rng = random.Random(cfg.seed)
    q = np.zeros((GRID_COLS, GRID_ROWS, NUM_ACTIONS), dtype=np.float64)

    lengths: list[int] = []

    ep = 0
    cell = START_CELL
    facing = "down"
    steps_in_ep = 0

    speed_levels = (1, 5, 25, 100, 500, 2000)
    speed_idx = 1
    paused = False
    finished = False
    saved_on_finish = False

    status_rect = pygame.Rect(0, GRID_H, WINDOW_WIDTH, STATUS_H)
    graph_rect = pygame.Rect(0, GRID_H + STATUS_H, WINDOW_WIDTH, GRAPH_H)

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE:
                    paused = not paused
                elif event.key in (pygame.K_UP, pygame.K_RIGHT, pygame.K_EQUALS, pygame.K_PLUS):
                    speed_idx = min(speed_idx + 1, len(speed_levels) - 1)
                elif event.key in (pygame.K_DOWN, pygame.K_LEFT, pygame.K_MINUS):
                    speed_idx = max(speed_idx - 1, 0)
                elif event.key == pygame.K_s:
                    save_artifacts(q, cfg, greedy_path(q))

        if not paused and not finished:
            steps_to_run = speed_levels[speed_idx]
            for _ in range(steps_to_run):
                if ep >= cfg.episodes:
                    finished = True
                    break
                eps = epsilon_for(ep, cfg)
                action = choose_action(q, cell, eps, rng)
                next_cell, reward, done = env_step(cell, action, cfg)
                best_next = 0.0 if done else float(q[next_cell[0], next_cell[1]].max())
                td_target = reward + cfg.gamma * best_next
                q[cell[0], cell[1], action] += cfg.alpha * (
                    td_target - q[cell[0], cell[1], action]
                )
                facing = DIRECTION_FOR_ACTION[action]
                cell = next_cell
                steps_in_ep += 1

                if done or steps_in_ep >= cfg.max_steps:
                    lengths.append(steps_in_ep)
                    ep += 1
                    cell = START_CELL
                    facing = "down"
                    steps_in_ep = 0
                    if ep >= cfg.episodes:
                        finished = True
                        break

        if finished and not saved_on_finish:
            path = greedy_path(q)
            save_artifacts(q, cfg, path)
            saved_on_finish = True

        screen.fill(BG_COLOR)
        render_grid(
            screen, q, cell, facing, sprites, bank_sprite, building_sprites, building_cells
        )
        eps_now = epsilon_for(ep, cfg)
        last_len = lengths[-1] if lengths else 0
        avg_len = float(np.mean(lengths[-100:])) if lengths else 0.0
        render_status(
            screen,
            font,
            status_rect,
            ep,
            cfg.episodes,
            eps_now,
            last_len,
            avg_len,
            speed_levels[speed_idx],
            paused,
            finished,
        )
        render_graph(screen, font, graph_rect, lengths, cfg)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()

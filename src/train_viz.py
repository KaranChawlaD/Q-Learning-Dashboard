"""Live pygame visualization of Q-learning training (dashboard UI).

Layout: header strip, grid card (heatmap + arrows + agent + value-scale legend),
metrics card (4 stat cells), controls card, and a full-width steps-per-episode
chart. Reuses env + algorithm from src/train.py so behavior matches headless
training under the same seed.
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


WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 920
OUTER_PAD = 24
SECTION_GAP = 16
HEADER_H = 56
TOP_ROW_H = 528
GRAPH_H = 256
FPS = 60

TILE_SIZE = 48
GRID_W = GRID_COLS * TILE_SIZE
GRID_H = GRID_ROWS * TILE_SIZE
TILE_GAP = 2
TILE_RADIUS = 5
CARD_RADIUS = 12

BG = (11, 15, 25)
SURFACE = (19, 24, 38)
SURFACE_HI = (26, 32, 50)
SURFACE_LO = (15, 19, 32)
BORDER = (35, 42, 60)
BORDER_HI = (50, 60, 84)
TEXT_PRIMARY = (226, 232, 240)
TEXT_SECONDARY = (148, 163, 184)
TEXT_DIM = (100, 116, 139)
ACCENT_CYAN = (56, 189, 248)
ACCENT_AMBER = (251, 191, 36)
ACCENT_EMERALD = (52, 211, 153)
ACCENT_PINK = (236, 72, 153)

PLASMA_STOPS = (
    (13, 8, 135),
    (84, 2, 163),
    (156, 23, 158),
    (218, 78, 119),
    (252, 159, 79),
    (240, 249, 33),
)

OBSTACLE_FILL = (28, 33, 49)
BANK_FILL = ACCENT_EMERALD
ARROW_RGBA = (245, 247, 255, 210)

DIRECTION_FOR_ACTION = ("up", "down", "left", "right")

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
SPRITES_DIR = os.path.join(PROJECT_ROOT, "assets", "sprites")
ELEMS_DIR = os.path.join(PROJECT_ROOT, "assets", "elems")


def lerp(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return (
        int(a[0] + (b[0] - a[0]) * t),
        int(a[1] + (b[1] - a[1]) * t),
        int(a[2] + (b[2] - a[2]) * t),
    )


def plasma(t: float) -> tuple[int, int, int]:
    t = max(0.0, min(1.0, t))
    n = len(PLASMA_STOPS) - 1
    seg = t * n
    i = int(seg)
    if i >= n:
        return PLASMA_STOPS[-1]
    return lerp(PLASMA_STOPS[i], PLASMA_STOPS[i + 1], seg - i)


def load_scaled_sprite(filename: str) -> pygame.Surface:
    path = os.path.join(SPRITES_DIR, filename)
    sprite = pygame.image.load(path).convert_alpha()
    return pygame.transform.smoothscale(sprite, (TILE_SIZE, TILE_SIZE))


def load_scaled_elem(filename: str) -> pygame.Surface:
    path = os.path.join(ELEMS_DIR, filename)
    elem = pygame.image.load(path).convert_alpha()
    return pygame.transform.smoothscale(elem, (TILE_SIZE, TILE_SIZE))


def build_fonts() -> dict[str, pygame.font.Font]:
    ui = "Segoe UI,Inter,SF Pro Text,Helvetica,Arial"
    mono = "Consolas,Cascadia Mono,Menlo,Courier New,monospace"
    return {
        "title": pygame.font.SysFont(ui, 22, bold=True),
        "subtitle": pygame.font.SysFont(ui, 13),
        "card_title": pygame.font.SysFont(ui, 11, bold=True),
        "stat_value": pygame.font.SysFont(ui, 30, bold=True),
        "small": pygame.font.SysFont(ui, 12),
        "small_b": pygame.font.SysFont(ui, 12, bold=True),
        "mono_small": pygame.font.SysFont(mono, 12),
        "pill": pygame.font.SysFont(ui, 11, bold=True),
    }


def draw_card(
    screen: pygame.Surface,
    rect: pygame.Rect,
    fill: tuple[int, int, int] = SURFACE,
    border: tuple[int, int, int] = BORDER,
) -> None:
    pygame.draw.rect(screen, fill, rect, border_radius=CARD_RADIUS)
    pygame.draw.rect(screen, border, rect, width=1, border_radius=CARD_RADIUS)


def render_header(
    screen: pygame.Surface,
    rect: pygame.Rect,
    fonts: dict[str, pygame.font.Font],
    status: str,
    status_color: tuple[int, int, int],
    speed: int,
    subtitle: str,
) -> None:
    draw_card(screen, rect)

    title = fonts["title"].render("Q-Learning Trainer", True, TEXT_PRIMARY)
    screen.blit(title, (rect.x + 22, rect.y + 12))
    sub = fonts["subtitle"].render(subtitle, True, TEXT_DIM)
    screen.blit(sub, (rect.x + 22, rect.y + 12 + title.get_height() + 2))

    pill_text = status
    pill_w = fonts["pill"].size(pill_text)[0] + 36
    pill_h = 26
    pill_rect = pygame.Rect(rect.right - pill_w - 18, rect.centery - pill_h // 2, pill_w, pill_h)
    pygame.draw.rect(screen, SURFACE_LO, pill_rect, border_radius=pill_h // 2)
    pygame.draw.rect(screen, status_color, pill_rect, width=1, border_radius=pill_h // 2)
    pygame.draw.circle(screen, status_color, (pill_rect.x + 14, pill_rect.centery), 4)
    surf = fonts["pill"].render(pill_text, True, status_color)
    screen.blit(surf, (pill_rect.x + 24, pill_rect.centery - surf.get_height() // 2))

    speed_text = f"{speed} steps / frame"
    speed_surf = fonts["small"].render(speed_text, True, TEXT_SECONDARY)
    screen.blit(
        speed_surf,
        (pill_rect.x - speed_surf.get_width() - 18, rect.centery - speed_surf.get_height() // 2),
    )


def render_grid_card(
    screen: pygame.Surface,
    rect: pygame.Rect,
    fonts: dict[str, pygame.font.Font],
    q: np.ndarray,
    agent_cell: tuple[int, int],
    facing: str,
    sprites: dict[str, pygame.Surface],
    bank_sprite: pygame.Surface,
    building_sprites: dict[str, pygame.Surface],
    building_cells: dict[str, tuple[int, int]],
) -> None:
    draw_card(screen, rect)
    title = fonts["card_title"].render("POLICY HEATMAP", True, TEXT_SECONDARY)
    screen.blit(title, (rect.x + 22, rect.y + 16))
    sub = fonts["small"].render(
        "max Q(s, a) per tile  ·  arrows = greedy action", True, TEXT_DIM
    )
    screen.blit(sub, (rect.x + 22, rect.y + 16 + title.get_height() + 2))

    v = q.max(axis=2)
    free_mask = np.ones_like(v, dtype=bool)
    for oc, or_ in OBSTACLES:
        free_mask[oc, or_] = False
    free_mask[BANK_CELL[0], BANK_CELL[1]] = False
    if free_mask.any():
        free_v = v[free_mask]
        vmin = float(free_v.min())
        vmax = float(free_v.max())
    else:
        vmin = vmax = 0.0
    span = vmax - vmin if vmax > vmin else 1.0

    grid_x = rect.x + (rect.width - GRID_W) // 2
    grid_y = rect.y + 56

    for col in range(GRID_COLS):
        for row in range(GRID_ROWS):
            tx = grid_x + col * TILE_SIZE + TILE_GAP // 2
            ty = grid_y + row * TILE_SIZE + TILE_GAP // 2
            tw = TILE_SIZE - TILE_GAP
            th = TILE_SIZE - TILE_GAP
            tile_rect = pygame.Rect(tx, ty, tw, th)

            if (col, row) in OBSTACLES:
                pygame.draw.rect(screen, OBSTACLE_FILL, tile_rect, border_radius=TILE_RADIUS)
                continue
            if (col, row) == BANK_CELL:
                pygame.draw.rect(screen, BANK_FILL, tile_rect, border_radius=TILE_RADIUS)
                continue
            t = (v[col, row] - vmin) / span
            pygame.draw.rect(screen, plasma(t), tile_rect, border_radius=TILE_RADIUS)

    arrow_layer = pygame.Surface((GRID_W, GRID_H), pygame.SRCALPHA)
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
            r = 8
            tip = (cx + dc * r, cy + dr * r)
            px = -dr * (r - 2)
            py = dc * (r - 2)
            base1 = (cx - dc * (r // 2) + px, cy - dr * (r // 2) + py)
            base2 = (cx - dc * (r // 2) - px, cy - dr * (r // 2) - py)
            pygame.draw.polygon(arrow_layer, ARROW_RGBA, [tip, base1, base2])
    screen.blit(arrow_layer, (grid_x, grid_y))

    for filename, (col, row) in building_cells.items():
        screen.blit(
            building_sprites[filename], (grid_x + col * TILE_SIZE, grid_y + row * TILE_SIZE)
        )
    screen.blit(
        bank_sprite, (grid_x + BANK_CELL[0] * TILE_SIZE, grid_y + BANK_CELL[1] * TILE_SIZE)
    )

    agent_x = grid_x + agent_cell[0] * TILE_SIZE
    agent_y = grid_y + agent_cell[1] * TILE_SIZE
    highlight = pygame.Rect(agent_x, agent_y, TILE_SIZE, TILE_SIZE)
    pygame.draw.rect(screen, ACCENT_CYAN, highlight, width=2, border_radius=TILE_RADIUS)
    screen.blit(sprites[facing], (agent_x, agent_y))

    legend_y = grid_y + GRID_H + 18
    legend_h = 10
    legend_x = grid_x
    legend_w = GRID_W
    gradient = pygame.Surface((legend_w, legend_h))
    for i in range(legend_w):
        t = i / max(1, legend_w - 1)
        pygame.draw.line(gradient, plasma(t), (i, 0), (i, legend_h))
    rounded = pygame.Surface((legend_w, legend_h), pygame.SRCALPHA)
    pygame.draw.rect(rounded, (255, 255, 255, 255), rounded.get_rect(), border_radius=4)
    gradient.set_colorkey(None)
    masked = pygame.Surface((legend_w, legend_h), pygame.SRCALPHA)
    masked.blit(gradient, (0, 0))
    masked.blit(rounded, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    screen.blit(masked, (legend_x, legend_y))

    low_label = fonts["mono_small"].render(f"V min  {vmin:+.1f}", True, TEXT_DIM)
    high_label = fonts["mono_small"].render(f"{vmax:+.1f}  V max", True, TEXT_DIM)
    screen.blit(low_label, (legend_x, legend_y + legend_h + 6))
    screen.blit(
        high_label,
        (legend_x + legend_w - high_label.get_width(), legend_y + legend_h + 6),
    )


def draw_stat_cell(
    screen: pygame.Surface,
    rect: pygame.Rect,
    label: str,
    value: str,
    fonts: dict[str, pygame.font.Font],
    accent: tuple[int, int, int] = TEXT_PRIMARY,
) -> None:
    pygame.draw.rect(screen, SURFACE_HI, rect, border_radius=10)
    pygame.draw.rect(screen, BORDER, rect, width=1, border_radius=10)
    label_surf = fonts["card_title"].render(label.upper(), True, TEXT_DIM)
    screen.blit(label_surf, (rect.x + 18, rect.y + 16))
    value_surf = fonts["stat_value"].render(value, True, accent)
    screen.blit(
        value_surf,
        (rect.x + 18, rect.bottom - value_surf.get_height() - 14),
    )


def render_metrics_card(
    screen: pygame.Surface,
    rect: pygame.Rect,
    fonts: dict[str, pygame.font.Font],
    ep: int,
    total_eps: int,
    eps: float,
    last_len: int,
    avg_len: float,
) -> None:
    draw_card(screen, rect)
    title = fonts["card_title"].render("METRICS", True, TEXT_SECONDARY)
    screen.blit(title, (rect.x + 22, rect.y + 16))

    inner_top = rect.y + 16 + title.get_height() + 12
    inner = pygame.Rect(
        rect.x + 18,
        inner_top,
        rect.width - 36,
        rect.bottom - inner_top - 18,
    )
    gap = 12
    cw = (inner.width - gap) // 2
    ch = (inner.height - gap) // 2

    cells = [
        ("Episode", f"{ep} / {total_eps}", TEXT_PRIMARY),
        ("Epsilon", f"{eps:.3f}", ACCENT_CYAN),
        ("Last episode", f"{last_len} steps", TEXT_PRIMARY),
        ("Avg (last 100)", f"{avg_len:.1f}", ACCENT_AMBER),
    ]
    for i, (label, value, color) in enumerate(cells):
        col = i % 2
        row = i // 2
        cell_rect = pygame.Rect(
            inner.x + col * (cw + gap),
            inner.y + row * (ch + gap),
            cw,
            ch,
        )
        draw_stat_cell(screen, cell_rect, label, value, fonts, color)


def render_controls_card(
    screen: pygame.Surface,
    rect: pygame.Rect,
    fonts: dict[str, pygame.font.Font],
) -> None:
    draw_card(screen, rect)
    title = fonts["card_title"].render("CONTROLS", True, TEXT_SECONDARY)
    screen.blit(title, (rect.x + 22, rect.y + 16))

    bindings = (
        ("Space", "Pause / resume training"),
        ("1 – 6", "Set training speed"),
        ("\u2190  \u2192", "Cycle speed levels"),
        ("S", "Save Q-table to assets/"),
        ("Esc", "Quit"),
    )

    y = rect.y + 16 + title.get_height() + 14
    row_h = 30
    for key, desc in bindings:
        key_w = max(64, fonts["mono_small"].size(key)[0] + 22)
        key_rect = pygame.Rect(rect.x + 22, y, key_w, 24)
        pygame.draw.rect(screen, SURFACE_LO, key_rect, border_radius=6)
        pygame.draw.rect(screen, BORDER_HI, key_rect, width=1, border_radius=6)
        key_surf = fonts["mono_small"].render(key, True, TEXT_PRIMARY)
        screen.blit(
            key_surf,
            (
                key_rect.centerx - key_surf.get_width() // 2,
                key_rect.centery - key_surf.get_height() // 2,
            ),
        )
        desc_surf = fonts["small"].render(desc, True, TEXT_SECONDARY)
        screen.blit(
            desc_surf,
            (key_rect.right + 14, key_rect.centery - desc_surf.get_height() // 2),
        )
        y += row_h


def render_graph_card(
    screen: pygame.Surface,
    rect: pygame.Rect,
    fonts: dict[str, pygame.font.Font],
    lengths: list[int],
    cfg: TrainConfig,
) -> None:
    draw_card(screen, rect)
    title = fonts["card_title"].render("STEPS PER EPISODE", True, TEXT_SECONDARY)
    screen.blit(title, (rect.x + 22, rect.y + 16))

    sub_text = "Lower is better"
    sub_color = TEXT_DIM
    if lengths and len(lengths) >= 100:
        avg100 = float(np.mean(lengths[-100:]))
        if avg100 < 25:
            sub_text = f"Lower is better  ·  Converged near optimum ({avg100:.1f} steps)"
            sub_color = ACCENT_EMERALD
    sub = fonts["small"].render(sub_text, True, sub_color)
    screen.blit(sub, (rect.x + 22, rect.y + 16 + title.get_height() + 2))

    leg_x = rect.right - 22
    leg_y = rect.y + 24
    items = (
        ("50-ep moving avg", ACCENT_AMBER),
        ("Per episode", ACCENT_CYAN),
    )
    for label, color in items:
        surf = fonts["small"].render(label, True, TEXT_SECONDARY)
        leg_x -= surf.get_width()
        screen.blit(surf, (leg_x, leg_y))
        leg_x -= 8
        pygame.draw.circle(screen, color, (leg_x, leg_y + surf.get_height() // 2), 4)
        leg_x -= 18

    pad_l, pad_r, pad_t, pad_b = 64, 28, 70, 44
    plot = pygame.Rect(
        rect.x + pad_l,
        rect.y + pad_t,
        rect.width - pad_l - pad_r,
        rect.height - pad_t - pad_b,
    )
    pygame.draw.rect(screen, SURFACE_LO, plot, border_radius=6)

    if not lengths:
        hint = fonts["small"].render(
            "Training will plot here once the first episode finishes\u2026",
            True,
            TEXT_DIM,
        )
        screen.blit(
            hint,
            (
                plot.centerx - hint.get_width() // 2,
                plot.centery - hint.get_height() // 2,
            ),
        )
        return

    n = len(lengths)
    x_max = max(cfg.episodes, n)
    raw_max = max(lengths)
    y_max_data = max(raw_max, 50)
    y_max = ((y_max_data + 24) // 25) * 25

    for frac in (0.0, 0.25, 0.5, 0.75, 1.0):
        y = plot.bottom - int(frac * plot.height)
        val = int(round(y_max * frac))
        label = fonts["mono_small"].render(str(val), True, TEXT_DIM)
        screen.blit(
            label,
            (rect.x + pad_l - 8 - label.get_width(), y - label.get_height() // 2),
        )
        if 0.0 < frac < 1.0:
            pygame.draw.line(screen, BORDER, (plot.left, y), (plot.right, y), 1)

    y_label = fonts["small"].render("STEPS", True, TEXT_DIM)
    y_label_rot = pygame.transform.rotate(y_label, 90)
    screen.blit(
        y_label_rot,
        (rect.x + 22, plot.centery - y_label_rot.get_height() // 2),
    )

    for frac in (0.0, 0.25, 0.5, 0.75, 1.0):
        x = plot.left + int(frac * plot.width)
        val = int(round(x_max * frac))
        text = f"{val // 1000}k" if val >= 1000 else str(val)
        label = fonts["mono_small"].render(text, True, TEXT_DIM)
        screen.blit(label, (x - label.get_width() // 2, plot.bottom + 8))
    x_label = fonts["small"].render("EPISODE", True, TEXT_DIM)
    screen.blit(
        x_label,
        (plot.centerx - x_label.get_width() // 2, plot.bottom + 24),
    )

    if n >= 2:
        denom = max(1, x_max - 1)
        points = [
            (
                plot.left + (i / denom) * plot.width,
                plot.bottom - (val / y_max) * plot.height,
            )
            for i, val in enumerate(lengths)
        ]
        raw_layer = pygame.Surface(plot.size, pygame.SRCALPHA)
        local_points = [(p[0] - plot.x, p[1] - plot.y) for p in points]
        pygame.draw.aalines(raw_layer, (*ACCENT_CYAN, 200), False, local_points)
        screen.blit(raw_layer, plot.topleft)

    window = 50
    if n >= window:
        cumsum = np.cumsum(np.asarray(lengths, dtype=np.float64))
        avg = (cumsum[window - 1 :] - np.concatenate(([0.0], cumsum[: n - window]))) / window
        denom = max(1, x_max - 1)
        avg_points = [
            (
                plot.left + ((i + window - 1) / denom) * plot.width,
                plot.bottom - (val / y_max) * plot.height,
            )
            for i, val in enumerate(avg)
        ]
        if len(avg_points) >= 2:
            pygame.draw.lines(screen, ACCENT_AMBER, False, avg_points, 2)

    if n < cfg.episodes and n >= 1:
        denom = max(1, x_max - 1)
        now_x = int(plot.left + ((n - 1) / denom) * plot.width)
        for y in range(plot.top, plot.bottom, 6):
            pygame.draw.line(screen, BORDER_HI, (now_x, y), (now_x, y + 3), 1)


def main() -> None:
    cfg = TrainConfig()

    pygame.init()
    pygame.display.set_caption("Q-Learning Trainer")
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    clock = pygame.time.Clock()
    fonts = build_fonts()

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

    inner_w = WINDOW_WIDTH - 2 * OUTER_PAD
    header_rect = pygame.Rect(OUTER_PAD, OUTER_PAD, inner_w, HEADER_H)
    top_y = header_rect.bottom + SECTION_GAP
    grid_card_w = 608
    grid_card_rect = pygame.Rect(OUTER_PAD, top_y, grid_card_w, TOP_ROW_H)
    right_x = grid_card_rect.right + SECTION_GAP
    right_w = inner_w - grid_card_w - SECTION_GAP
    metrics_h = 260
    metrics_rect = pygame.Rect(right_x, top_y, right_w, metrics_h)
    controls_rect = pygame.Rect(
        right_x,
        metrics_rect.bottom + SECTION_GAP,
        right_w,
        TOP_ROW_H - metrics_h - SECTION_GAP,
    )
    graph_rect = pygame.Rect(
        OUTER_PAD,
        top_y + TOP_ROW_H + SECTION_GAP,
        inner_w,
        GRAPH_H,
    )

    number_keys = {
        pygame.K_1: 0,
        pygame.K_2: 1,
        pygame.K_3: 2,
        pygame.K_4: 3,
        pygame.K_5: 4,
        pygame.K_6: 5,
    }

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
                elif event.key in number_keys:
                    speed_idx = number_keys[event.key]
                elif event.key == pygame.K_s:
                    save_artifacts(q, cfg, greedy_path(q))

        if not paused and not finished:
            steps_to_run = speed_levels[speed_idx]
            for _ in range(steps_to_run):
                if ep >= cfg.episodes:
                    finished = True
                    break
                eps_v = epsilon_for(ep, cfg)
                action = choose_action(q, cell, eps_v, rng)
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
            save_artifacts(q, cfg, greedy_path(q))
            saved_on_finish = True

        if finished:
            status_text = "DONE"
            status_color = ACCENT_EMERALD
            final_path_len = max(0, len(greedy_path(q)) - 1)
            subtitle = (
                f"Trained {cfg.episodes} episodes  ·  greedy path = {final_path_len} steps"
            )
        elif paused:
            status_text = "PAUSED"
            status_color = ACCENT_AMBER
            subtitle = "Tabular agent  ·  12\u00d79 gridworld"
        else:
            status_text = "TRAINING"
            status_color = ACCENT_CYAN
            subtitle = "Tabular agent  ·  12\u00d79 gridworld"

        eps_now = epsilon_for(ep, cfg)
        last_len = lengths[-1] if lengths else 0
        avg_len = float(np.mean(lengths[-100:])) if lengths else 0.0

        screen.fill(BG)
        render_header(
            screen,
            header_rect,
            fonts,
            status_text,
            status_color,
            speed_levels[speed_idx],
            subtitle,
        )
        render_grid_card(
            screen,
            grid_card_rect,
            fonts,
            q,
            cell,
            facing,
            sprites,
            bank_sprite,
            building_sprites,
            building_cells,
        )
        render_metrics_card(
            screen,
            metrics_rect,
            fonts,
            ep,
            cfg.episodes,
            eps_now,
            last_len,
            avg_len,
        )
        render_controls_card(screen, controls_rect, fonts)
        render_graph_card(screen, graph_rect, fonts, lengths, cfg)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()

"""Tabular Q-learning trainer for the businessman -> bank gridworld.

Trains against the fixed map defined in src/main.py:
  - 12 x 9 grid
  - start (0, 0), bank (11, 8)
  - obstacles at (3, 2), (6, 4), (8, 6)

Outputs:
  - assets/q_table.npy        Q-values, shape (GRID_COLS, GRID_ROWS, 4)
  - assets/q_meta.json        Hyperparameters + env config used for training
"""

from __future__ import annotations

import json
import os
import random
from dataclasses import asdict, dataclass

import numpy as np


GRID_COLS = 12
GRID_ROWS = 9
START_CELL = (0, 0)
BANK_CELL = (GRID_COLS - 1, GRID_ROWS - 1)
OBSTACLES: frozenset[tuple[int, int]] = frozenset({(3, 2), (6, 4), (8, 6)})

ACTIONS = ((0, -1), (0, 1), (-1, 0), (1, 0))  # up, down, left, right
ACTION_NAMES = ("up", "down", "left", "right")
NUM_ACTIONS = len(ACTIONS)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(PROJECT_ROOT, "assets")


@dataclass
class TrainConfig:
    episodes: int = 5000
    max_steps: int = 200
    alpha: float = 0.1
    gamma: float = 0.95
    epsilon_start: float = 1.0
    epsilon_end: float = 0.05
    epsilon_decay_episodes: int = 3000
    reward_goal: float = 100.0
    reward_step: float = -1.0
    reward_blocked: float = -5.0
    seed: int = 42
    log_every: int = 250


def env_step(
    cell: tuple[int, int], action: int, cfg: TrainConfig
) -> tuple[tuple[int, int], float, bool]:
    """Apply an action; return (next_cell, reward, done).

    Mirrors src/main.py movement: out-of-bounds and obstacle moves are blocked
    (agent stays put and incurs `reward_blocked`).
    """
    dc, dr = ACTIONS[action]
    nc, nr = cell[0] + dc, cell[1] + dr
    if not (0 <= nc < GRID_COLS and 0 <= nr < GRID_ROWS) or (nc, nr) in OBSTACLES:
        return cell, cfg.reward_blocked, False
    if (nc, nr) == BANK_CELL:
        return (nc, nr), cfg.reward_goal, True
    return (nc, nr), cfg.reward_step, False


def epsilon_for(episode: int, cfg: TrainConfig) -> float:
    if episode >= cfg.epsilon_decay_episodes:
        return cfg.epsilon_end
    frac = episode / cfg.epsilon_decay_episodes
    return cfg.epsilon_start + frac * (cfg.epsilon_end - cfg.epsilon_start)


def choose_action(
    q: np.ndarray, cell: tuple[int, int], eps: float, rng: random.Random
) -> int:
    if rng.random() < eps:
        return rng.randrange(NUM_ACTIONS)
    qvals = q[cell[0], cell[1]]
    best = np.flatnonzero(qvals == qvals.max())
    return int(rng.choice(best.tolist()))


def train(cfg: TrainConfig) -> tuple[np.ndarray, list[float], list[int]]:
    rng = random.Random(cfg.seed)
    q = np.zeros((GRID_COLS, GRID_ROWS, NUM_ACTIONS), dtype=np.float64)

    returns: list[float] = []
    lengths: list[int] = []

    for ep in range(cfg.episodes):
        cell = START_CELL
        eps = epsilon_for(ep, cfg)
        total_reward = 0.0
        steps = 0
        done = False

        while not done and steps < cfg.max_steps:
            action = choose_action(q, cell, eps, rng)
            next_cell, reward, done = env_step(cell, action, cfg)

            best_next = 0.0 if done else float(q[next_cell[0], next_cell[1]].max())
            td_target = reward + cfg.gamma * best_next
            td_error = td_target - q[cell[0], cell[1], action]
            q[cell[0], cell[1], action] += cfg.alpha * td_error

            cell = next_cell
            total_reward += reward
            steps += 1

        returns.append(total_reward)
        lengths.append(steps)

        if (ep + 1) % cfg.log_every == 0:
            window_start = max(0, ep - cfg.log_every + 1)
            avg_r = float(np.mean(returns[window_start : ep + 1]))
            avg_len = float(np.mean(lengths[window_start : ep + 1]))
            print(
                f"ep {ep + 1:>5d} | eps {eps:.3f} | "
                f"avg return {avg_r:7.2f} | avg length {avg_len:6.2f}"
            )

    return q, returns, lengths


def greedy_path(q: np.ndarray, max_steps: int = 200) -> list[tuple[int, int]]:
    """Walk the greedy policy from start to bank for inspection."""
    cell = START_CELL
    path = [cell]
    visited = {cell}
    for _ in range(max_steps):
        if cell == BANK_CELL:
            break
        action = int(np.argmax(q[cell[0], cell[1]]))
        dc, dr = ACTIONS[action]
        nc, nr = cell[0] + dc, cell[1] + dr
        if not (0 <= nc < GRID_COLS and 0 <= nr < GRID_ROWS) or (nc, nr) in OBSTACLES:
            break
        cell = (nc, nr)
        if cell in visited:
            path.append(cell)
            break
        visited.add(cell)
        path.append(cell)
    return path


def save_artifacts(q: np.ndarray, cfg: TrainConfig, path: list[tuple[int, int]]) -> None:
    os.makedirs(ASSETS_DIR, exist_ok=True)
    q_path = os.path.join(ASSETS_DIR, "q_table.npy")
    meta_path = os.path.join(ASSETS_DIR, "q_meta.json")
    np.save(q_path, q)
    meta = {
        "config": asdict(cfg),
        "grid_cols": GRID_COLS,
        "grid_rows": GRID_ROWS,
        "start": list(START_CELL),
        "bank": list(BANK_CELL),
        "obstacles": [list(c) for c in sorted(OBSTACLES)],
        "actions": list(ACTION_NAMES),
        "greedy_path": [list(c) for c in path],
        "greedy_path_length": len(path) - 1,
    }
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    print(f"\nsaved Q-table   -> {q_path}")
    print(f"saved metadata  -> {meta_path}")


def main() -> None:
    cfg = TrainConfig()
    print("Training Q-learning agent on fixed gridworld...")
    print(f"  grid: {GRID_COLS}x{GRID_ROWS}, start={START_CELL}, bank={BANK_CELL}")
    print(f"  obstacles: {sorted(OBSTACLES)}")
    print(f"  episodes={cfg.episodes}, alpha={cfg.alpha}, gamma={cfg.gamma}\n")

    q, _, lengths = train(cfg)
    path = greedy_path(q)

    manhattan = abs(BANK_CELL[0] - START_CELL[0]) + abs(BANK_CELL[1] - START_CELL[1])
    print("\nGreedy policy path from start to bank:")
    print(" -> ".join(str(c) for c in path))
    print(
        f"path length: {len(path) - 1} steps "
        f"(unobstructed Manhattan optimum: {manhattan})"
    )
    print(f"final 100-episode avg length: {float(np.mean(lengths[-100:])):.2f}")

    save_artifacts(q, cfg, path)


if __name__ == "__main__":
    main()

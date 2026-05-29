"""FastAPI + WebSocket server for the Q-learning training dashboard.

Reuses qlearning.train for the env and Q-learning update so artifacts written
by this dashboard match ``python run.py train`` under the same seed and layout.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import random
import webbrowser
from contextlib import asynccontextmanager, suppress
from typing import Any

import numpy as np
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from qlearning.env import (
    ACTION_NAMES,
    GRID_COLS,
    GRID_ROWS,
    NUM_ACTIONS,
    GridLayout,
    parse_layout,
    validate_layout,
)
from qlearning.evaluate import run_model_tests
from qlearning.train import (
    TrainConfig,
    choose_action,
    env_step,
    epsilon_for,
    greedy_path,
    save_artifacts,
)

SPEED_LEVELS = (1, 5, 25, 100, 500, 2000)
TICK_INTERVAL_S = 0.05
SNAPSHOT_INTERVAL_S = 0.08
DIRECTION_FOR_ACTION = ("up", "down", "left", "right")


def _parse_train_config(raw: dict[str, Any] | None, base: TrainConfig) -> TrainConfig:
    if raw is None:
        return base
    if not isinstance(raw, dict):
        raise ValueError("train_config must be an object.")

    cfg = TrainConfig(**vars(base))

    def _num(key: str, *, integer: bool = False) -> float | int:
        if key not in raw:
            return getattr(cfg, key)
        value = raw[key]
        if isinstance(value, bool):
            raise ValueError(f"{key} must be numeric.")
        out = int(value) if integer else float(value)
        if not np.isfinite(out):
            raise ValueError(f"{key} must be finite.")
        return out

    cfg.alpha = float(_num("alpha"))
    cfg.gamma = float(_num("gamma"))
    cfg.epsilon_start = float(_num("epsilon_start"))
    cfg.epsilon_end = float(_num("epsilon_end"))
    cfg.epsilon_decay_episodes = int(_num("epsilon_decay_episodes", integer=True))
    cfg.reward_goal = float(_num("reward_goal"))
    cfg.reward_step = float(_num("reward_step"))
    cfg.reward_blocked = float(_num("reward_blocked"))
    cfg.seed = int(_num("seed", integer=True))

    if not (0.0 < cfg.alpha <= 1.0):
        raise ValueError("alpha must be in (0, 1].")
    if not (0.0 < cfg.gamma < 1.0):
        raise ValueError("gamma must be in (0, 1).")
    if not (0.0 <= cfg.epsilon_end <= cfg.epsilon_start <= 1.0):
        raise ValueError("epsilon values must satisfy 0 <= epsilon_end <= epsilon_start <= 1.")
    if cfg.epsilon_decay_episodes < 1:
        raise ValueError("epsilon_decay_episodes must be >= 1.")
    if cfg.reward_goal <= 0:
        raise ValueError("reward_goal must be positive.")
    if cfg.reward_blocked > cfg.reward_step:
        raise ValueError("reward_blocked should be <= reward_step.")
    if cfg.seed < 0:
        raise ValueError("seed must be >= 0.")

    return cfg


class Trainer:
    """Single-source-of-truth training state, mutated only on the asyncio loop."""

    def __init__(self) -> None:
        self.cfg = TrainConfig()
        self.mode = "setup"
        self.layout: GridLayout | None = None
        self._init_run_state()

    def _init_run_state(self) -> None:
        self.rng = random.Random(self.cfg.seed)
        self.q = np.zeros((GRID_COLS, GRID_ROWS, NUM_ACTIONS), dtype=np.float64)
        self.lengths: list[int] = []
        self.ep = 0
        self.cell = (0, 0)
        self.facing = "down"
        self.steps_in_ep = 0
        self.speed_idx = 1
        self.paused = False
        self.finished = False
        self._artifacts_saved = False
        if self.layout is not None:
            self.cell = self.layout.start

    @property
    def speed(self) -> int:
        return SPEED_LEVELS[self.speed_idx]

    def start_training(
        self, layout: GridLayout, train_config_raw: dict[str, Any] | None = None
    ) -> tuple[bool, str]:
        ok, err = validate_layout(layout)
        if not ok:
            return False, err
        try:
            self.cfg = _parse_train_config(train_config_raw, TrainConfig())
        except ValueError as exc:
            return False, str(exc)
        self.layout = layout
        self.mode = "training"
        self.finished = False
        self.paused = False
        self._artifacts_saved = False
        self._init_run_state()
        return True, ""

    def step_batch(self, n: int) -> None:
        if self.mode != "training" or self.paused or self.finished or self.layout is None:
            return
        cfg = self.cfg
        layout = self.layout
        for _ in range(n):
            if self.ep >= cfg.episodes:
                self.finished = True
                if not self._artifacts_saved:
                    save_artifacts(self.q, cfg, greedy_path(self.q, layout), layout)
                    self._artifacts_saved = True
                return
            eps_v = epsilon_for(self.ep, cfg)
            action = choose_action(self.q, self.cell, eps_v, self.rng)
            next_cell, reward, done = env_step(self.cell, action, cfg, layout)
            best_next = 0.0 if done else float(self.q[next_cell[0], next_cell[1]].max())
            td_target = reward + cfg.gamma * best_next
            self.q[self.cell[0], self.cell[1], action] += cfg.alpha * (
                td_target - self.q[self.cell[0], self.cell[1], action]
            )
            self.facing = DIRECTION_FOR_ACTION[action]
            self.cell = next_cell
            self.steps_in_ep += 1
            if done or self.steps_in_ep >= cfg.max_steps:
                self.lengths.append(self.steps_in_ep)
                self.ep += 1
                self.cell = layout.start
                self.steps_in_ep = 0

    def restart_training(self) -> None:
        """Re-run training on the current layout without returning to setup."""
        if self.layout is None:
            return
        self.mode = "training"
        self.finished = False
        self.paused = False
        self._artifacts_saved = False
        self._init_run_state()

    def reset(self) -> None:
        self.mode = "setup"
        self.layout = None
        self._init_run_state()

    def set_speed(self, idx: int) -> None:
        if 0 <= idx < len(SPEED_LEVELS):
            self.speed_idx = idx

    def toggle_pause(self) -> None:
        if self.mode != "training":
            return
        if self.finished:
            self.restart_training()
        else:
            self.paused = not self.paused

    def save_now(self) -> None:
        if self.layout is not None:
            save_artifacts(self.q, self.cfg, greedy_path(self.q, self.layout), self.layout)

    def _layout_dict(self) -> dict[str, Any] | None:
        if self.layout is None:
            return None
        return {
            "start": list(self.layout.start),
            "bank": list(self.layout.bank),
            "obstacles": [list(c) for c in sorted(self.layout.obstacles)],
            "buildings": self.layout.buildings(),
        }

    def snapshot(self) -> dict[str, Any]:
        v = self.q.max(axis=2)
        best = self.q.argmax(axis=2)

        free_mask = np.ones_like(v, dtype=bool)
        if self.layout is not None:
            for oc, or_ in self.layout.obstacles:
                free_mask[oc, or_] = False
            free_mask[self.layout.bank[0], self.layout.bank[1]] = False
        if free_mask.any():
            free_v = v[free_mask]
            vmin = float(free_v.min())
            vmax = float(free_v.max())
        else:
            vmin = vmax = 0.0

        v_flat: list[float] = []
        best_flat: list[int] = []
        for row in range(GRID_ROWS):
            for col in range(GRID_COLS):
                v_flat.append(round(float(v[col, row]), 4))
                best_flat.append(int(best[col, row]))

        avg100 = float(np.mean(self.lengths[-100:])) if self.lengths else 0.0
        last_len = self.lengths[-1] if self.lengths else 0

        model_tests = None
        if self.finished and self.layout is not None:
            model_tests = run_model_tests(
                self.q,
                self.cfg,
                self.lengths,
                self.layout,
                max_steps=self.cfg.max_steps,
            )

        return {
            "mode": self.mode,
            "env": self._layout_dict(),
            "ep": self.ep,
            "totalEps": self.cfg.episodes,
            "eps": float(epsilon_for(self.ep, self.cfg)) if self.mode == "training" else 0.0,
            "speed": self.speed,
            "speedIdx": self.speed_idx,
            "speedLevels": list(SPEED_LEVELS),
            "paused": self.paused,
            "finished": self.finished,
            "lastLen": last_len,
            "avg100": avg100,
            "vmin": vmin,
            "vmax": vmax,
            "v": v_flat,
            "best": best_flat,
            "agent": {
                "col": self.cell[0],
                "row": self.cell[1],
                "facing": self.facing,
            },
            "lengths": list(self.lengths),
            "modelTests": model_tests,
        }

    def static_config(self) -> dict[str, Any]:
        return {
            "gridCols": GRID_COLS,
            "gridRows": GRID_ROWS,
            "actions": list(ACTION_NAMES),
            "buildingFiles": ["building_1.png", "building_2.png", "building_3.png"],
            "trainConfig": {
                "alpha": self.cfg.alpha,
                "gamma": self.cfg.gamma,
                "epsilon_start": self.cfg.epsilon_start,
                "epsilon_end": self.cfg.epsilon_end,
                "epsilon_decay_episodes": self.cfg.epsilon_decay_episodes,
                "reward_goal": self.cfg.reward_goal,
                "reward_step": self.cfg.reward_step,
                "reward_blocked": self.cfg.reward_blocked,
                "seed": self.cfg.seed,
            },
        }


trainer = Trainer()


async def trainer_loop() -> None:
    while True:
        await asyncio.sleep(TICK_INTERVAL_S)
        try:
            trainer.step_batch(trainer.speed)
        except Exception as exc:
            print(f"[trainer] error: {exc!r}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(trainer_loop())
    try:
        yield
    finally:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task


app = FastAPI(lifespan=lifespan, title="Q-Learning Trainer")

WEB_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(WEB_DIR, "static")
PROJECT_ROOT = os.path.dirname(WEB_DIR)
ASSETS_DIR = os.path.join(PROJECT_ROOT, "assets")

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")


FAVICON_PATH = os.path.join(STATIC_DIR, "favicon.ico")


@app.get("/favicon.ico", include_in_schema=False)
async def favicon() -> FileResponse:
    return FileResponse(FAVICON_PATH, media_type="image/x-icon")


@app.get("/", response_class=HTMLResponse)
async def index() -> FileResponse:
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


def _handle_command(msg: dict) -> dict[str, Any] | None:
    cmd = msg.get("type")
    if cmd == "start_training":
        try:
            layout = parse_layout(
                msg["start"],
                msg["bank"],
                msg.get("obstacles", []),
            )
        except (KeyError, TypeError, ValueError, IndexError):
            return {"type": "error", "message": "Invalid layout payload."}
        ok, err = trainer.start_training(layout, msg.get("train_config"))
        if not ok:
            return {"type": "error", "message": err}
        return None
    if cmd == "toggle":
        trainer.toggle_pause()
    elif cmd == "pause":
        trainer.paused = True
    elif cmd == "resume":
        if trainer.mode == "training" and not trainer.finished:
            trainer.paused = False
    elif cmd == "speed":
        idx = int(msg.get("idx", trainer.speed_idx))
        trainer.set_speed(idx)
    elif cmd == "save":
        trainer.save_now()
    elif cmd == "reset":
        trainer.reset()
    return None


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        await websocket.send_text(
            json.dumps({"type": "init", "config": trainer.static_config()})
        )
        await websocket.send_text(json.dumps({"type": "state", "data": trainer.snapshot()}))
    except Exception:
        await websocket.close()
        return

    async def sender() -> None:
        last_payload: str | None = None
        while True:
            await asyncio.sleep(SNAPSHOT_INTERVAL_S)
            payload = json.dumps({"type": "state", "data": trainer.snapshot()})
            if payload != last_payload:
                await websocket.send_text(payload)
                last_payload = payload

    sender_task = asyncio.create_task(sender())
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if isinstance(msg, dict):
                err = _handle_command(msg)
                if err is not None:
                    await websocket.send_text(json.dumps(err))
                await websocket.send_text(
                    json.dumps({"type": "state", "data": trainer.snapshot()})
                )
    except WebSocketDisconnect:
        pass
    finally:
        sender_task.cancel()
        with suppress(asyncio.CancelledError):
            await sender_task


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="run.py web",
        description="Launch the Q-learning training dashboard",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Bind port (default: 8000)")
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Do not auto-open a browser tab when the server starts",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload (development only)",
    )
    args = parser.parse_args()

    if not args.no_browser:
        host = "localhost" if args.host in ("0.0.0.0", "127.0.0.1") else args.host
        webbrowser.open(f"http://{host}:{args.port}", new=2)

    uvicorn.run(
        "web.server:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info",
    )


if __name__ == "__main__":
    main()

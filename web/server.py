"""FastAPI + WebSocket server for the Q-learning training dashboard.

Reuses src/train.py for the env and Q-learning update so artifacts written by
this dashboard match `python run_train.py` exactly under the same seed.
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
    BANK_CELL,
    GRID_COLS,
    GRID_ROWS,
    NUM_ACTIONS,
    OBSTACLES,
    START_CELL,
)
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


class Trainer:
    """Single-source-of-truth training state, mutated only on the asyncio loop."""

    def __init__(self) -> None:
        self.cfg = TrainConfig()
        self._init_run_state()

    def _init_run_state(self) -> None:
        self.rng = random.Random(self.cfg.seed)
        self.q = np.zeros((GRID_COLS, GRID_ROWS, NUM_ACTIONS), dtype=np.float64)
        self.lengths: list[int] = []
        self.ep = 0
        self.cell = START_CELL
        self.facing = "down"
        self.steps_in_ep = 0
        self.speed_idx = 1
        self.paused = False
        self.finished = False
        self._artifacts_saved = False

    @property
    def speed(self) -> int:
        return SPEED_LEVELS[self.speed_idx]

    def step_batch(self, n: int) -> None:
        if self.paused or self.finished:
            return
        cfg = self.cfg
        for _ in range(n):
            if self.ep >= cfg.episodes:
                self.finished = True
                if not self._artifacts_saved:
                    save_artifacts(self.q, cfg, greedy_path(self.q))
                    self._artifacts_saved = True
                return
            eps_v = epsilon_for(self.ep, cfg)
            action = choose_action(self.q, self.cell, eps_v, self.rng)
            next_cell, reward, done = env_step(self.cell, action, cfg)
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
                self.cell = START_CELL
                self.steps_in_ep = 0

    def reset(self) -> None:
        self._init_run_state()

    def set_speed(self, idx: int) -> None:
        if 0 <= idx < len(SPEED_LEVELS):
            self.speed_idx = idx

    def toggle_pause(self) -> None:
        if not self.finished:
            self.paused = not self.paused

    def save_now(self) -> None:
        save_artifacts(self.q, self.cfg, greedy_path(self.q))

    def snapshot(self) -> dict[str, Any]:
        v = self.q.max(axis=2)
        best = self.q.argmax(axis=2)

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

        v_flat: list[float] = []
        best_flat: list[int] = []
        for row in range(GRID_ROWS):
            for col in range(GRID_COLS):
                v_flat.append(round(float(v[col, row]), 4))
                best_flat.append(int(best[col, row]))

        avg100 = float(np.mean(self.lengths[-100:])) if self.lengths else 0.0
        last_len = self.lengths[-1] if self.lengths else 0

        return {
            "ep": self.ep,
            "totalEps": self.cfg.episodes,
            "eps": float(epsilon_for(self.ep, self.cfg)),
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
        }

    def static_config(self) -> dict[str, Any]:
        return {
            "gridCols": GRID_COLS,
            "gridRows": GRID_ROWS,
            "start": list(START_CELL),
            "bank": list(BANK_CELL),
            "obstacles": [list(o) for o in sorted(OBSTACLES)],
            "actions": list(ACTION_NAMES),
            "buildings": [
                {"file": "building_1.png", "col": 3, "row": 2},
                {"file": "building_2.png", "col": 6, "row": 4},
                {"file": "building_3.png", "col": 8, "row": 6},
            ],
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


@app.get("/", response_class=HTMLResponse)
async def index() -> FileResponse:
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


def _handle_command(msg: dict) -> None:
    cmd = msg.get("type")
    if cmd == "toggle":
        trainer.toggle_pause()
    elif cmd == "pause":
        trainer.paused = True
    elif cmd == "resume":
        if not trainer.finished:
            trainer.paused = False
    elif cmd == "speed":
        idx = int(msg.get("idx", trainer.speed_idx))
        trainer.set_speed(idx)
    elif cmd == "save":
        trainer.save_now()
    elif cmd == "reset":
        trainer.reset()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        await websocket.send_text(json.dumps({"type": "init", "config": trainer.static_config()}))
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
                _handle_command(msg)
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

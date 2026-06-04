"""FastAPI + WebSocket server for the Q-learning training dashboard.

Reuses qlearning.train for the env and Q-learning update so artifacts written
by this dashboard match ``python run.py train`` under the same seed and layout.

Each browser session gets an isolated :class:`Trainer` keyed by an HttpOnly cookie.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import random
import secrets
import time
import webbrowser
from contextlib import asynccontextmanager, suppress
from dataclasses import asdict
from datetime import UTC, datetime
from typing import Any

import numpy as np
import uvicorn
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse, Response
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
CLEANUP_INTERVAL_S = 300.0
IDLE_SESSION_S = 1800.0
DIRECTION_FOR_ACTION = ("up", "down", "left", "right")
SESSION_COOKIE = "ql_session"
SESSION_MAX_AGE_S = 60 * 60 * 24


def is_production() -> bool:
    return os.environ.get("QLEARNING_ENV", "").lower() == "production"


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
    """Per-session training state, mutated only on the asyncio loop."""

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
                    self._persist_artifacts()
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

    def _persist_artifacts(self) -> None:
        if self.layout is None or is_production():
            return
        save_artifacts(self.q, self.cfg, greedy_path(self.q, self.layout), self.layout)

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

    def import_run(self, data: dict[str, Any]) -> tuple[bool, str, dict[str, Any] | None]:
        """Restore a run from an export JSON payload. Returns optional client-only setup data."""
        if data.get("version") != 1:
            return False, "Unsupported export version (expected version 1).", None

        grid_cols = int(data.get("grid_cols", GRID_COLS))
        grid_rows = int(data.get("grid_rows", GRID_ROWS))
        if grid_cols != GRID_COLS or grid_rows != GRID_ROWS:
            return (
                False,
                f"Grid size must be {GRID_COLS}×{GRID_ROWS} (file has {grid_cols}×{grid_rows}).",
                None,
            )

        layout_raw = data.get("layout")
        if not isinstance(layout_raw, dict):
            return False, "Missing layout object.", None

        start = layout_raw.get("start")
        bank = layout_raw.get("bank")
        if not start or not bank:
            return False, "Layout must include start and bank.", None

        building_placements = data.get("building_placements")
        if building_placements is None:
            buildings = layout_raw.get("buildings")
            if isinstance(buildings, list):
                building_placements = buildings

        try:
            layout = parse_layout(
                start,
                bank,
                layout_raw.get("obstacles", []),
                building_placements=building_placements,
            )
        except (KeyError, TypeError, ValueError, IndexError) as exc:
            detail = str(exc).strip()
            return False, detail if detail else "Invalid layout in import file.", None

        ok, err = validate_layout(layout)
        if not ok:
            return False, err, None

        config_raw = data.get("config")
        if not isinstance(config_raw, dict):
            return False, "Missing config object.", None
        try:
            cfg = _parse_train_config(config_raw, TrainConfig())
        except ValueError as exc:
            return False, str(exc), None

        q_raw = data.get("q_table")
        if q_raw is None:
            self.mode = "setup"
            self.layout = None
            self.cfg = cfg
            self._init_run_state()
            client = {
                "mode": "setup",
                "train_config": asdict(cfg),
                "layout": {
                    "start": list(layout.start),
                    "bank": list(layout.bank),
                    "obstacles": [list(c) for c in sorted(layout.obstacles)],
                    "buildings": layout.buildings(),
                },
            }
            return True, "", client

        try:
            q = np.array(q_raw, dtype=np.float64)
        except (TypeError, ValueError):
            return False, "q_table must be a numeric array.", None
        if q.shape != (GRID_COLS, GRID_ROWS, NUM_ACTIONS):
            return (
                False,
                f"q_table shape must be ({GRID_COLS}, {GRID_ROWS}, {NUM_ACTIONS}).",
                None,
            )

        lengths_raw = data.get("lengths", [])
        if not isinstance(lengths_raw, list):
            return False, "lengths must be a list.", None
        lengths = [int(x) for x in lengths_raw]

        ep = int(data.get("ep", len(lengths)))
        ep = max(0, min(ep, cfg.episodes))
        finished = bool(data.get("finished", False)) or ep >= cfg.episodes
        if finished:
            ep = cfg.episodes

        self.cfg = cfg
        self.layout = layout
        self.q = q
        self.lengths = lengths
        self.ep = ep
        self.finished = finished
        self.mode = "training"
        self.paused = True
        self._artifacts_saved = finished
        self.rng = random.Random(cfg.seed)
        self.cell = layout.start
        self.facing = "down"
        self.steps_in_ep = 0
        self.speed_idx = 1
        return True, "", None

    def _layout_dict(self) -> dict[str, Any] | None:
        if self.layout is None:
            return None
        return {
            "start": list(self.layout.start),
            "bank": list(self.layout.bank),
            "obstacles": [list(c) for c in sorted(self.layout.obstacles)],
            "buildings": self.layout.buildings(),
        }

    def _building_placements(self) -> list[dict[str, object]]:
        if self.layout is None:
            return []
        return self.layout.buildings()

    def export_run(self) -> dict[str, Any] | None:
        if self.layout is None:
            return None
        path = greedy_path(self.q, self.layout)
        model_tests = None
        if self.finished:
            model_tests = run_model_tests(
                self.q,
                self.cfg,
                self.lengths,
                self.layout,
                max_steps=self.cfg.max_steps,
            )
        return {
            "version": 1,
            "exported_at": datetime.now(UTC).isoformat(),
            "grid_cols": GRID_COLS,
            "grid_rows": GRID_ROWS,
            "actions": list(ACTION_NAMES),
            "layout": self._layout_dict(),
            "building_placements": self._building_placements(),
            "config": asdict(self.cfg),
            "lengths": list(self.lengths),
            "q_table": self.q.tolist(),
            "greedy_path": [list(c) for c in path],
            "greedy_path_length": len(path) - 1,
            "model_tests": model_tests,
            "finished": self.finished,
            "ep": self.ep,
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
            "canExport": self.layout is not None and self.mode == "training",
        }

    def static_config(self) -> dict[str, Any]:
        return {
            "gridCols": GRID_COLS,
            "gridRows": GRID_ROWS,
            "actions": list(ACTION_NAMES),
            "buildingFiles": ["building_1.png", "building_2.png", "building_3.png"],
            "production": is_production(),
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


class SessionManager:
    """Maps browser session ids to isolated trainers."""

    def __init__(self) -> None:
        self._trainers: dict[str, Trainer] = {}
        self._last_seen: dict[str, float] = {}

    def touch(self, session_id: str) -> Trainer:
        self._last_seen[session_id] = time.monotonic()
        if session_id not in self._trainers:
            self._trainers[session_id] = Trainer()
        return self._trainers[session_id]

    def step_all(self) -> None:
        for trainer in self._trainers.values():
            try:
                trainer.step_batch(trainer.speed)
            except Exception as exc:
                print(f"[trainer] error: {exc!r}")

    def cleanup_idle(self) -> None:
        now = time.monotonic()
        stale = [
            session_id
            for session_id, seen_at in self._last_seen.items()
            if now - seen_at > IDLE_SESSION_S
        ]
        for session_id in stale:
            self._trainers.pop(session_id, None)
            self._last_seen.pop(session_id, None)
        if stale:
            print(f"[sessions] removed {len(stale)} idle session(s)")


sessions = SessionManager()


def new_session_id() -> str:
    return secrets.token_urlsafe(32)


def session_id_from_request(request: Request) -> tuple[str, bool]:
    existing = request.cookies.get(SESSION_COOKIE)
    if existing:
        return existing, False
    return new_session_id(), True


def session_id_from_websocket(websocket: WebSocket) -> str:
    existing = websocket.cookies.get(SESSION_COOKIE)
    return existing if existing else new_session_id()


def set_session_cookie(response: Response, session_id: str) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        session_id,
        max_age=SESSION_MAX_AGE_S,
        httponly=True,
        samesite="lax",
        secure=is_production(),
    )


async def trainer_loop() -> None:
    ticks_since_cleanup = 0
    cleanup_every = int(CLEANUP_INTERVAL_S / TICK_INTERVAL_S)
    while True:
        await asyncio.sleep(TICK_INTERVAL_S)
        sessions.step_all()
        ticks_since_cleanup += 1
        if ticks_since_cleanup >= cleanup_every:
            sessions.cleanup_idle()
            ticks_since_cleanup = 0


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
async def index(request: Request) -> FileResponse:
    session_id, is_new = session_id_from_request(request)
    sessions.touch(session_id)
    response = FileResponse(os.path.join(STATIC_DIR, "index.html"))
    if is_new:
        set_session_cookie(response, session_id)
    return response


def _handle_command(trainer: Trainer, msg: dict) -> dict[str, Any] | None:
    cmd = msg.get("type")
    if cmd == "start_training":
        try:
            layout = parse_layout(
                msg["start"],
                msg["bank"],
                msg.get("obstacles", []),
                building_placements=msg.get("building_placements"),
            )
        except (KeyError, TypeError, ValueError, IndexError) as exc:
            detail = str(exc).strip()
            message = detail if detail else "Invalid layout payload."
            return {"type": "error", "message": message}
        ok, err = trainer.start_training(layout, msg.get("train_config"))
        if not ok:
            return {"type": "error", "message": err}
        return None
    if cmd == "export":
        data = trainer.export_run()
        if data is None:
            return {"type": "error", "message": "Nothing to export yet — start training first."}
        return {"type": "export", "data": data}
    if cmd == "import_run":
        run = msg.get("run")
        if not isinstance(run, dict):
            return {"type": "error", "message": "run must be an object."}
        ok, err, client = trainer.import_run(run)
        if not ok:
            return {"type": "error", "message": err}
        if client is not None:
            return {"type": "imported", "data": client}
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
    elif cmd == "reset":
        trainer.reset()
    return None


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    session_id = session_id_from_websocket(websocket)
    trainer = sessions.touch(session_id)
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
            sessions.touch(session_id)
            payload = json.dumps({"type": "state", "data": trainer.snapshot()})
            if payload != last_payload:
                await websocket.send_text(payload)
                last_payload = payload

    sender_task = asyncio.create_task(sender())
    try:
        while True:
            raw = await websocket.receive_text()
            sessions.touch(session_id)
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if isinstance(msg, dict):
                err = _handle_command(trainer, msg)
                if err is not None:
                    await websocket.send_text(json.dumps(err))
                await websocket.send_text(json.dumps({"type": "state", "data": trainer.snapshot()}))
    except WebSocketDisconnect:
        pass
    finally:
        sender_task.cancel()
        with suppress(asyncio.CancelledError):
            await sender_task


def _default_host() -> str:
    return "0.0.0.0" if is_production() else "127.0.0.1"


def _default_port() -> int:
    return int(os.environ.get("PORT", "8000"))


def _should_open_browser(args: argparse.Namespace) -> bool:
    return not args.no_browser and not is_production()


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="run.py web",
        description="Launch the Q-learning training dashboard",
    )
    parser.add_argument(
        "--host",
        default=_default_host(),
        help="Bind host (default: 127.0.0.1 locally, 0.0.0.0 in production)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=_default_port(),
        help="Bind port (default: $PORT or 8000)",
    )
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

    port = int(os.environ.get("PORT", args.port))

    if _should_open_browser(args):
        host = "localhost" if args.host in ("0.0.0.0", "127.0.0.1") else args.host
        webbrowser.open(f"http://{host}:{port}", new=2)

    uvicorn.run(
        "web.server:app",
        host=args.host,
        port=port,
        reload=args.reload,
        log_level="info",
    )


if __name__ == "__main__":
    main()

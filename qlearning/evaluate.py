"""Post-training model checks for the Q-learning agent.

Each test returns a structured result suitable for the dashboard's
LeetCode-style expandable test-case panel.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from qlearning.env import ACTIONS, BANK_CELL, OBSTACLES, START_CELL
from qlearning.train import TrainConfig, env_step, greedy_path


@dataclass(frozen=True)
class TestCase:
    id: str
    name: str
    description: str


@dataclass
class TestResult:
    id: str
    name: str
    description: str
    passed: bool
    expected: str
    actual: str
    details: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "passed": self.passed,
            "expected": self.expected,
            "actual": self.actual,
        }
        if self.details is not None:
            out["details"] = self.details
        return out


TEST_CASES: tuple[TestCase, ...] = (
    TestCase(
        "reaches_bank",
        "Greedy policy reaches the bank",
        "Follow the greedy policy from start; the final cell must be the bank.",
    ),
    TestCase(
        "path_length",
        "Path length at or below optimum",
        "Greedy path step count must not exceed the unobstructed Manhattan distance.",
    ),
    TestCase(
        "avoids_obstacles",
        "Path avoids all obstacles",
        "No building tile may appear on the greedy path.",
    ),
    TestCase(
        "valid_moves",
        "Every step is a legal move",
        "Each transition must stay in bounds and not walk through obstacles.",
    ),
    TestCase(
        "convergence",
        "Training converged (avg last 100)",
        "Mean episode length over the last 100 episodes should be near the optimum.",
    ),
    TestCase(
        "learned_value",
        "Start state has positive value",
        "max Q(s, a) at the start cell should be positive after successful training.",
    ),
)


def _manhattan_optimum() -> int:
    return abs(BANK_CELL[0] - START_CELL[0]) + abs(BANK_CELL[1] - START_CELL[1])


def _check_reaches_bank(path: list[tuple[int, int]]) -> TestResult:
    tc = TEST_CASES[0]
    reached = bool(path) and path[-1] == BANK_CELL
    return TestResult(
        id=tc.id,
        name=tc.name,
        description=tc.description,
        passed=reached,
        expected=f"Final cell {list(BANK_CELL)}",
        actual=f"Final cell {list(path[-1])}" if path else "Empty path",
        details={"path": [list(c) for c in path]} if path else None,
    )


def _check_path_length(path: list[tuple[int, int]]) -> TestResult:
    tc = TEST_CASES[1]
    optimum = _manhattan_optimum()
    steps = len(path) - 1 if path else 0
    return TestResult(
        id=tc.id,
        name=tc.name,
        description=tc.description,
        passed=steps <= optimum,
        expected=f"<= {optimum} steps",
        actual=f"{steps} steps",
        details={"optimum": optimum, "steps": steps},
    )


def _check_avoids_obstacles(path: list[tuple[int, int]]) -> TestResult:
    tc = TEST_CASES[2]
    hits = [list(c) for c in path if c in OBSTACLES]
    return TestResult(
        id=tc.id,
        name=tc.name,
        description=tc.description,
        passed=not hits,
        expected="No obstacle cells on path",
        actual="No obstacles hit" if not hits else f"Hit {hits}",
        details={"obstacle_hits": hits} if hits else None,
    )


def _check_valid_moves(path: list[tuple[int, int]], cfg: TrainConfig) -> TestResult:
    tc = TEST_CASES[3]
    invalid: list[dict[str, Any]] = []
    for i in range(len(path) - 1):
        cur, nxt = path[i], path[i + 1]
        dc, dr = nxt[0] - cur[0], nxt[1] - cur[1]
        if (dc, dr) not in ACTIONS:
            invalid.append({"from": list(cur), "to": list(nxt), "reason": "not a cardinal move"})
            continue
        action = ACTIONS.index((dc, dr))
        result_cell, _, _ = env_step(cur, action, cfg)
        if result_cell != nxt:
            invalid.append({"from": list(cur), "to": list(nxt), "reason": "blocked or illegal"})
    return TestResult(
        id=tc.id,
        name=tc.name,
        description=tc.description,
        passed=not invalid,
        expected="All consecutive cells connected by legal moves",
        actual="All moves legal" if not invalid else f"{len(invalid)} illegal move(s)",
        details={"invalid_moves": invalid} if invalid else None,
    )


def _check_convergence(lengths: list[int], cfg: TrainConfig) -> TestResult:
    tc = TEST_CASES[4]
    threshold = _manhattan_optimum() + 6
    if len(lengths) < 100:
        return TestResult(
            id=tc.id,
            name=tc.name,
            description=tc.description,
            passed=False,
            expected=f"avg(last 100) < {threshold}",
            actual=f"Only {len(lengths)} episode(s) completed",
        )
    avg100 = float(np.mean(lengths[-100:]))
    return TestResult(
        id=tc.id,
        name=tc.name,
        description=tc.description,
        passed=avg100 < threshold,
        expected=f"avg(last 100) < {threshold}",
        actual=f"avg(last 100) = {avg100:.2f}",
        details={"avg100": round(avg100, 2), "threshold": threshold},
    )


def _check_learned_value(q: np.ndarray) -> TestResult:
    tc = TEST_CASES[5]
    v_start = float(q[START_CELL[0], START_CELL[1]].max())
    return TestResult(
        id=tc.id,
        name=tc.name,
        description=tc.description,
        passed=v_start > 0,
        expected="max Q(start) > 0",
        actual=f"max Q(start) = {v_start:.2f}",
        details={"v_start": round(v_start, 4)},
    )


def run_model_tests(
    q: np.ndarray,
    cfg: TrainConfig,
    lengths: list[int],
    *,
    max_steps: int = 200,
) -> dict[str, Any]:
    """Run all post-training checks and return a summary for the dashboard."""
    path = greedy_path(q, max_steps=max_steps)
    results = [
        _check_reaches_bank(path),
        _check_path_length(path),
        _check_avoids_obstacles(path),
        _check_valid_moves(path, cfg),
        _check_convergence(lengths, cfg),
        _check_learned_value(q),
    ]
    passed = sum(1 for r in results if r.passed)
    return {
        "passed": passed,
        "total": len(results),
        "allPassed": passed == len(results),
        "tests": [r.to_dict() for r in results],
    }

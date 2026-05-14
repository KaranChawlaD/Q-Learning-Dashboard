"""Tests for post-training model evaluation."""

from __future__ import annotations

import numpy as np

from qlearning.env import BANK_CELL, OBSTACLES
from qlearning.evaluate import run_model_tests
from qlearning.train import TrainConfig, greedy_path, train


def test_trained_model_passes_all_checks() -> None:
    cfg = TrainConfig(episodes=5000, seed=42)
    q, _, lengths = train(cfg)
    result = run_model_tests(q, cfg, lengths)

    assert result["total"] == 6
    assert result["passed"] == result["total"]
    assert result["allPassed"] is True
    assert all(t["passed"] for t in result["tests"])


def test_untrained_model_fails_checks() -> None:
    cfg = TrainConfig()
    q = np.zeros((12, 9, 4), dtype=np.float64)
    result = run_model_tests(q, cfg, [])

    assert result["allPassed"] is False
    assert result["passed"] < result["total"]

    by_id = {t["id"]: t for t in result["tests"]}
    assert by_id["reaches_bank"]["passed"] is False
    assert by_id["learned_value"]["passed"] is False


def test_greedy_path_in_reaches_bank_details() -> None:
    cfg = TrainConfig(episodes=200, seed=7)
    q, _, lengths = train(cfg)
    path = greedy_path(q)
    result = run_model_tests(q, cfg, lengths)
    reaches = next(t for t in result["tests"] if t["id"] == "reaches_bank")

    if path and path[-1] == BANK_CELL:
        assert reaches["passed"] is True
        assert reaches["details"]["path"][-1] == list(BANK_CELL)
    else:
        assert reaches["passed"] is False


def test_obstacle_free_path_check() -> None:
    cfg = TrainConfig(episodes=500, seed=1)
    q, _, lengths = train(cfg)
    path = greedy_path(q)
    result = run_model_tests(q, cfg, lengths)
    avoids = next(t for t in result["tests"] if t["id"] == "avoids_obstacles")

    hit_obstacle = any(cell in OBSTACLES for cell in path)
    assert avoids["passed"] is (not hit_obstacle)


def test_convergence_requires_100_episodes() -> None:
    cfg = TrainConfig()
    q = np.zeros((12, 9, 4), dtype=np.float64)
    result = run_model_tests(q, cfg, [30] * 50)
    convergence = next(t for t in result["tests"] if t["id"] == "convergence")

    assert convergence["passed"] is False
    assert "Only 50 episode(s)" in convergence["actual"]

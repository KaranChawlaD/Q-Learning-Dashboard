"""Tabular Q-learning gridworld package.

Modules
-------
env
    Static gridworld definition: dimensions, start/bank cells, obstacles,
    action set, and the building-sprite placements used by every renderer.
train
    Tabular Q-learning algorithm, training loop, and headless CLI
    (`python run.py train`) that writes artifacts to ``assets/``.
manual
    Pygame manual-control window for interactive exploration of the env
    (`python run.py manual`).
"""

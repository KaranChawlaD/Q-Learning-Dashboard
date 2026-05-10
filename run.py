"""Q-Learning project entry point.

Usage:
    python run.py                    # web (default)
    python run.py web [options]      # live training dashboard in the browser
    python run.py train              # headless tabular Q-learning + save artifacts
    python run.py manual             # pygame manual-control window
    python run.py --help             # this message

Pass ``--help`` to any subcommand for its own options.
"""

from __future__ import annotations

import importlib
import sys

SUBCOMMANDS: dict[str, tuple[str, str]] = {
    "web": ("web.server", "Launch the live training dashboard in the browser"),
    "train": ("qlearning.train", "Run headless tabular Q-learning and save artifacts"),
    "manual": ("qlearning.manual", "Open the pygame manual-control window"),
}

DEFAULT_SUBCOMMAND = "web"


def print_usage() -> None:
    print("Usage: python run.py [SUBCOMMAND] [OPTIONS]")
    print()
    print("Subcommands:")
    for name, (_, desc) in SUBCOMMANDS.items():
        marker = "  (default)" if name == DEFAULT_SUBCOMMAND else ""
        print(f"  {name:<8} {desc}{marker}")
    print()
    print("Pass --help to any subcommand for its own options.")


def main() -> None:
    argv = sys.argv[1:]

    if argv and argv[0] in ("-h", "--help") and (len(argv) == 1 or argv[1] not in SUBCOMMANDS):
        print_usage()
        return

    if not argv or argv[0].startswith("-"):
        cmd = DEFAULT_SUBCOMMAND
        rest = argv
    else:
        cmd = argv[0]
        rest = argv[1:]

    if cmd not in SUBCOMMANDS:
        print(f"error: unknown subcommand: {cmd!r}\n", file=sys.stderr)
        print_usage()
        sys.exit(2)

    module_name, _ = SUBCOMMANDS[cmd]
    sys.argv = [f"run.py {cmd}", *rest]
    importlib.import_module(module_name).main()


if __name__ == "__main__":
    main()

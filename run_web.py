"""Launch the Q-learning web dashboard.

Usage:
    python run_web.py [--host 127.0.0.1] [--port 8000]

Then open http://127.0.0.1:8000 in a browser.
"""

from __future__ import annotations

import argparse
import webbrowser

import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Q-learning web dashboard")
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

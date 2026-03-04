"""Entry point for the interactive dashboard server.

Usage:
    python -m tools.serve projects/f-electron-scf
    python -m tools.serve projects/f-electron-scf --port 8080
"""

from __future__ import annotations

import argparse
import sys
import webbrowser
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="PM Agent Interactive Dashboard")
    parser.add_argument("project_dir", type=Path, help="Project directory path")
    parser.add_argument("--port", type=int, default=8000, help="Server port")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Server host")
    parser.add_argument("--no-browser", action="store_true",
                        help="Don't open browser automatically")
    args = parser.parse_args()

    if not args.project_dir.exists():
        print(f"Error: {args.project_dir} does not exist")
        sys.exit(1)

    # Regenerate dashboard before serving
    try:
        from tools.generate_dashboard import generate_dashboard
        generate_dashboard(args.project_dir)
        print(f"Dashboard regenerated for {args.project_dir}")
    except Exception as e:
        print(f"Warning: Could not regenerate dashboard: {e}")

    from src.server.app import create_app
    import uvicorn

    app = create_app(args.project_dir)
    url = f"http://{args.host}:{args.port}"
    print(f"\n  PM Agent Interactive Dashboard")
    print(f"  Project: {args.project_dir}")
    print(f"  URL:     {url}")
    print(f"  API:     {url}/api/project")
    print(f"  WS:      ws://{args.host}:{args.port}/ws\n")

    if not args.no_browser:
        webbrowser.open(url)

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()

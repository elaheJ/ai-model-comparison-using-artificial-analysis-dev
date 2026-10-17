"""Installable command: model-lab python | agent | compare | fetch."""
import argparse
from getpass import getpass
import json
import os
from pathlib import Path
import subprocess
import sys
from .core import fixed_workflow
from .snapshots import demo_snapshot, fetch_artificial_analysis, load_snapshot, configured_api_key


def main():
    parser = argparse.ArgumentParser(description="Model Comparison Lab")
    commands = parser.add_subparsers(dest="command", required=True)
    for name, port in (("python", 8501), ("agent", 8502)):
        app = commands.add_parser(name, help="Launch the " + name + " app")
        app.add_argument("--port", type=int, default=port)
        app.add_argument("--headless", action="store_true")
    compare = commands.add_parser("compare", help="Run Python comparison without a browser")
    compare.add_argument("--snapshot", type=Path, help="JSON/CSV; defaults to the fictional demo")
    compare.add_argument("--task", type=Path, required=True, help="JSON with comparison requirements")
    compare.add_argument("--output", type=Path, help="Write full result JSON instead of stdout")
    fetch = commands.add_parser("fetch", help="Explicitly download an Artificial Analysis snapshot")
    fetch.add_argument("--output", type=Path, required=True)
    fetch.add_argument("--prompt-key", action="store_true", help="Enter the AA key privately in the terminal")
    args = parser.parse_args()
    try:
        if args.command in ("python", "agent"):
            entry = Path(__file__).with_name(args.command + "_entry.py")
            command = [sys.executable, "-m", "streamlit", "run", str(entry), "--server.port", str(args.port)]
            if args.headless:
                command.extend(["--server.headless", "true"])
            raise SystemExit(subprocess.call(command))
        if args.command == "fetch":
            if args.output.exists():
                parser.error("Output already exists; use a new snapshot filename.")
            key = getpass("Artificial Analysis API key: ").strip() if args.prompt_key else configured_api_key()
            result = fetch_artificial_analysis(key)
        else:
            snapshot = load_snapshot(args.snapshot.read_bytes(), args.snapshot.name) if args.snapshot else demo_snapshot()
            result = fixed_workflow(snapshot, json.loads(args.task.read_text()))
        output = json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(output, encoding="utf-8")
            print(f"Saved {args.output}")
        else:
            print(output)
    except (ValueError, RuntimeError, OSError) as exc:
        parser.exit(1, f"Error: {exc}\n")


if __name__ == "__main__":
    main()

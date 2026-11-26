#!/usr/bin/env python3
"""One command for the isolated v2 diagnostic round."""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["all", "fit", "report", "verify", "status"])
    parser.add_argument("--resume", action="store_true", help="Completed valid checkpoints are always reused")
    parser.add_argument("--pilot", action="store_true", help="Run only first real-data case")
    args = parser.parse_args()
    from revisions.methodology_v2 import pipeline
    if args.command == "status":
        print((pipeline.HERE / "RUN_STATUS.md").read_text())
        return
    if args.command in ("all", "fit"):
        pipeline.run_all(limit=1 if args.pilot else None)
        if args.pilot:
            return
    # Separate processes avoid broadening the fitting process's external-read guard.
    if args.command == "all":
        import subprocess
        for command in ("report", "verify"):
            subprocess.run([sys.executable, __file__, command], check=True)
    elif args.command == "report":
        from revisions.methodology_v2.reporting import report
        report()
    elif args.command == "verify":
        from revisions.methodology_v2.verify import verify
        verify()


if __name__ == "__main__":
    main()

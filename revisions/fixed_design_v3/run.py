#!/usr/bin/env python3
"""Isolated fixed-design study with a process boundary before evaluation."""
import argparse
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("command",choices=["all","design","evaluate","report","verify","status"])
    parser.add_argument("--resume",action="store_true")
    parser.add_argument("--pilot",action="store_true")
    args=parser.parse_args()
    if args.command=="all":
        for stage in ("design","evaluate","report","verify"):
            subprocess.run([sys.executable,__file__,stage,"--resume"],check=True)
        return
    from revisions.fixed_design_v3 import pipeline as p
    if args.command=="design":
        p.run_design(args.pilot)
    elif args.command=="evaluate":
        p.run_evaluate()
    elif args.command=="report":
        from threadpoolctl import threadpool_limits
        from revisions.fixed_design_v3.reporting import report
        with threadpool_limits(limits=2):
            report()
    elif args.command=="verify":
        from revisions.fixed_design_v3.verify import verify
        verify()
    else:
        print((p.HERE/"RUN_STATUS.md").read_text())


if __name__=="__main__":
    main()

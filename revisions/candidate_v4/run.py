#!/usr/bin/env python3
"""Run the isolated final-candidate workflow from the project root."""
import argparse
from pathlib import Path
import subprocess
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['all', 'select', 'freeze', 'report', 'verify', 'status'])
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--pilot', action='store_true')
    args = parser.parse_args()
    if args.command == 'all':
        for stage in ('select', 'freeze', 'report', 'verify'):
            subprocess.run([sys.executable, __file__, stage, '--resume'], check=True)
        return
    from revisions.candidate_v4 import pipeline as p
    if args.command == 'select':
        p.select(args.pilot)
    elif args.command == 'freeze':
        p.freeze()
    elif args.command == 'report':
        p.report()
    elif args.command == 'verify':
        from revisions.candidate_v4.verify import verify
        verify()
    else:
        print((p.HERE / 'RUN_STATUS.md').read_text())


if __name__ == '__main__':
    main()

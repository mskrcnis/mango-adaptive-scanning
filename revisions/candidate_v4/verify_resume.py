#!/usr/bin/env python3
"""Execute the full workflow and prove frozen/scientific bytes are preserved."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / 'results'


def snapshot():
    files = list((OUT / 'checkpoints').glob('*')) + list((HERE / 'frozen').rglob('*'))
    files += list((HERE / 'validation').rglob('*')) + list((HERE / 'examples').rglob('*'))
    files += list(HERE.glob('*.py')) + list(HERE.glob('*.json'))
    files += [f for f in HERE.glob('*.md') if f.name not in ('RUN_STATUS.md', 'verification_report.md')]
    files += list(OUT.glob('*.csv'))
    files += [OUT / name for name in ('registration.json', 'software_tests.json', 'portable_execution.json')]
    return {str(f.relative_to(HERE)): hashlib.sha256(f.read_bytes()).hexdigest()
            for f in sorted(set(files)) if f.is_file() and '__pycache__' not in f.parts}


def main():
    before = snapshot()
    command = [sys.executable, str(HERE / 'run.py'), 'all', '--resume']
    started = time.perf_counter()
    with (OUT / 'resume_execution.log').open('w') as log:
        process = subprocess.Popen(command, cwd=ROOT, stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT, text=True, bufsize=1)
        for line in process.stdout:
            log.write(line)
            log.flush()
            print(line, end='', flush=True)
        returncode = process.wait()
    after = snapshot()
    changed = sorted(n for n in set(before) | set(after) if before.get(n) != after.get(n))
    evidence = {'passed': returncode == 0 and not changed, 'exit_code': returncode, 'command': command,
                'seconds': time.perf_counter() - started, 'files_checked': len(before), 'changed': changed,
                'before_sha256': before, 'after_sha256': after,
                'scope': 'All 96 checkpoints and metadata; entire frozen bundle; sources, protocols, validation templates, examples, tables and environment. Operational status/logs/read audits, verification outputs and proof itself excluded.'}
    (OUT / 'resume_verification.json').write_text(json.dumps(evidence, indent=2) + '\n')
    print(json.dumps({k: evidence[k] for k in ('passed', 'exit_code', 'files_checked', 'changed')}, indent=2), flush=True)
    if not evidence['passed']:
        raise SystemExit('Resume failed or changed preserved artifacts; inspect results/resume_verification.json')
    subprocess.run([sys.executable, str(HERE / 'run.py'), 'verify'], cwd=ROOT, check=True)


if __name__ == '__main__':
    main()

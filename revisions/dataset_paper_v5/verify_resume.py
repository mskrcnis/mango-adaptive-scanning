#!/usr/bin/env python3
"""Prove a full reporting workflow resume leaves deliverable bytes unchanged."""
import json
from pathlib import Path
import subprocess
import sys
import run

HERE = Path(__file__).resolve().parent


def snapshot():
    files = run.package_files()
    files += [HERE / n for n in ('prior_preservation.json', 'results/visual_review.json',
              'results/compilation.json', 'results/package.json', 'results/isolated_compilation.json',
              'output/Mango_Dataset_Paper_Source.zip', 'output/pdf/Mango_Dataset_Study.pdf',
              'output/pdf/Mango_Dataset_Supplement.pdf')]
    return {str(f.relative_to(HERE)): run.sha(f) for f in sorted(set(files))}


before = snapshot()
command = [sys.executable, str(HERE / 'run.py'), 'all', '--resume']
with (HERE / 'results/resume_execution.log').open('w') as log:
    completed = subprocess.run(command, cwd=run.ROOT, stdout=log, stderr=subprocess.STDOUT)
after = snapshot()
changed = sorted(n for n in set(before) | set(after) if before.get(n) != after.get(n))
proof = {'passed': completed.returncode == 0 and not changed, 'exit_code': completed.returncode,
         'command': command, 'files_checked': len(before), 'changed': changed,
         'before_sha256': before, 'after_sha256': after,
         'scope': 'All source-package payloads, PDF outputs, archive, prior preservation manifest, '
                  'visual/compilation/package evidence. Mutable logs, status and final verification reports excluded.'}
run.save(HERE / 'results/resume_verification.json', proof)
print(json.dumps({k: proof[k] for k in ('passed', 'exit_code', 'files_checked', 'changed')}, indent=2))
if not proof['passed']:
    raise SystemExit(1)
subprocess.run([sys.executable, str(HERE / 'run.py'), 'verify'], cwd=run.ROOT, check=True)

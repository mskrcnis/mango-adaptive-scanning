#!/usr/bin/env python3
"""Run the complete resume command and compare all scientific artifact bytes."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / "results"


def snapshot():
    files = list((OUT / "checkpoints").glob("*"))
    files += list(OUT.glob("*.csv")) + list(OUT.glob("*.csv.gz"))
    files += list((HERE / "figures").glob("*")) + list(HERE.glob("*.py"))
    files += [HERE / n for n in ("protocol.md", "README.md", "decision_report.md",
                                 "prior_versions_preservation.json")]
    files += [OUT / n for n in ("registration.json", "design_lock.json")]
    return {str(f.relative_to(HERE)): hashlib.sha256(f.read_bytes()).hexdigest()
            for f in sorted(set(files)) if f.is_file()}


def main():
    audit_copy = OUT / "initial_execution_read_audits.json"
    if not audit_copy.exists():
        audit_copy.write_text(json.dumps({n: json.loads((OUT / n).read_text()) for n in
            ("design_read_audit.json", "evaluation_read_audit.json")}, indent=2) + "\n")
    before = snapshot()
    command = [sys.executable, str(HERE / "run.py"), "all", "--resume"]
    started = time.perf_counter()
    with (OUT / "resume_execution.log").open("w") as log:
        process = subprocess.Popen(command, cwd=ROOT, stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT, text=True, bufsize=1)
        for line in process.stdout:
            log.write(line)
            log.flush()
            print(line, end="", flush=True)
        exit_code = process.wait()
    after = snapshot()
    changed = sorted(n for n in set(before) | set(after) if before.get(n) != after.get(n))
    result = {"passed": exit_code == 0 and not changed, "exit_code": exit_code,
              "command": command, "seconds": time.perf_counter() - started,
              "files_checked": len(before), "changed": changed,
              "before_sha256": before, "after_sha256": after,
              "excluded": "Runtime logs/read audits, status, verification outputs and this proof; initial read audits retained separately."}
    (OUT / "resume_verification.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: result[k] for k in ("passed", "exit_code", "files_checked", "changed")}, indent=2))
    if not result["passed"]:
        raise SystemExit("Resume changed scientific artifacts or failed; inspect resume_verification.json")
    subprocess.run([sys.executable, str(HERE / "run.py"), "verify"], cwd=ROOT, check=True)


if __name__ == "__main__":
    main()

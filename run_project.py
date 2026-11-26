#!/usr/bin/env python3
"""Portable command entry point; imports scientific packages only after bootstrap."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent


def bootstrap():
    target = ROOT / '.venv/bin/python'
    if Path(sys.prefix).resolve() == (ROOT / '.venv').resolve():
        import importlib.metadata
        missing=[]
        for requirement in (ROOT/'requirements.txt').read_text().splitlines():
            if not requirement or requirement.startswith('#'):continue
            name,version=requirement.split('==')
            try:actual=importlib.metadata.version(name).split('+')[0]
            except importlib.metadata.PackageNotFoundError:actual=None
            if actual!=version:missing.append(requirement)
        if missing:
            subprocess.check_call([sys.executable,'-m','pip','install',*missing])
            os.execv(sys.executable,[sys.executable,str(Path(__file__).resolve())]+sys.argv[1:])
        return
    if not target.exists():
        base = Path('/home/mskr/anaconda3/envs/pytorch_env/bin/python')
        if base.exists():
            subprocess.check_call([str(base), '-m', 'venv', '--system-site-packages', str(ROOT / '.venv')])
        else:
            if sys.version_info[:2] == (3, 8):
                subprocess.check_call([sys.executable, '-m', 'venv', str(ROOT / '.venv')])
            else:
                uv=shutil.which('uv')
                if uv is None:
                    helper=ROOT/'.bootstrap'
                    subprocess.check_call([sys.executable,'-m','venv',str(helper)])
                    subprocess.check_call([str(helper/'bin/python'),'-m','pip','install','uv==0.9.29'])
                    uv=str(helper/'bin/uv')
                child_env=dict(os.environ,UV_PYTHON_INSTALL_DIR=str(ROOT/'.python'),UV_CACHE_DIR=str(ROOT/'.uv-cache'))
                subprocess.check_call([uv,'venv','--python','3.8.20','--seed',str(ROOT/'.venv')],env=child_env)
            subprocess.check_call([str(target), '-m', 'pip', 'install', '-r', str(ROOT / 'requirements.txt')])
    for name in ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS'):
        os.environ[name] = '4'
    os.environ['PYTHONHASHSEED'] = '42'
    os.environ['CUBLAS_WORKSPACE_CONFIG'] = ':4096:8'
    os.execv(str(target), [str(target), str(Path(__file__).resolve())] + sys.argv[1:])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['smoke','all','status','verify','replay','app','report'])
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--data-path', help='Official v3 CSV override (schema and provenance audited)')
    parser.add_argument('--example', action='store_true')
    parser.add_argument('--manual', action='store_true')
    parser.add_argument('--trace-output', default='results/demo_trace.json')
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--self-test', action='store_true', help='Exercise app endpoints then exit')
    args = parser.parse_args()
    bootstrap()
    os.chdir(ROOT)
    if args.command == 'status':
        from mango.workflow import status
        status()
    elif args.command in ('smoke','all'):
        from mango.workflow import run
        run(args)
    elif args.command == 'verify':
        from mango.verification import verify
        verify()
    elif args.command == 'report':
        from mango.reporting import generate_reports
        generate_reports()
    elif args.command == 'replay':
        from mango.app import replay
        replay(manual=args.manual, trace_output=args.trace_output)
    elif args.command == 'app':
        from mango.app import serve
        serve(port=args.port, self_test=args.self_test)


if __name__ == '__main__':
    main()

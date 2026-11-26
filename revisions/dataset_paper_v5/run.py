#!/usr/bin/env python3
"""Reporting-only paper build; never imports project fitting or scoring modules."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RESULTS = HERE / 'results'
MAN = HERE / 'manuscript'
OUTPUT = HERE / 'output'
PDF = OUTPUT / 'pdf'
NAMES = {'main': 'Mango_Dataset_Study.pdf', 'supplement': 'Mango_Dataset_Supplement.pdf'}


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def save(path, obj):
    data = (json.dumps(obj, indent=2, sort_keys=True) + '\n').encode()
    if not path.exists() or path.read_bytes() != data:
        temporary = path.with_suffix(path.suffix + '.tmp')
        temporary.write_bytes(data)
        temporary.replace(path)


def load(path):
    return json.loads(path.read_text())


def execute(command, cwd, log):
    with log.open('w') as stream:
        completed = subprocess.run(command, cwd=cwd, stdout=stream, stderr=subprocess.STDOUT)
    if completed.returncode:
        raise RuntimeError('Command failed: %r; see %s' % (command, log))


def preserved():
    expected = load(HERE / 'prior_preservation.json')['sha256']
    changed = [name for name, digest in expected.items()
               if not (ROOT / name).is_file() or sha(ROOT / name) != digest]
    if changed:
        raise RuntimeError('Earlier artifacts changed: ' + repr(changed))
    return {'passed': True, 'files_checked': len(expected), 'changed': []}


def evidence_valid():
    path = RESULTS / 'evidence_manifest.json'
    if not path.exists():
        return False
    evidence = load(path)
    if evidence.get('status') != 'PASS' or evidence.get('build_code_sha256') != sha(HERE / 'build_evidence.py'):
        return False
    pairs = [(ROOT / n, h) for n, h in evidence['source_sha256'].items()]
    pairs += [(HERE / n, h) for n, h in evidence['artifact_sha256'].items()]
    return all(p.is_file() and sha(p) == h for p, h in pairs)


def report():
    preserved()
    if evidence_valid():
        compact_table()
        audit_supplement()
        print('Reused verified numerical evidence; no fitting or scoring.')
        return
    execute([sys.executable, str(HERE / 'build_evidence.py')], ROOT, RESULTS / 'evidence_build.log')
    if not evidence_valid():
        raise RuntimeError('Evidence build did not pass its recorded hashes')
    compact_table()
    audit_supplement()
    preserved()


def supplement_valid():
    path = RESULTS / 'supplement_numeric_verification.json'
    if not path.exists():
        return False
    audit = load(path)
    return (audit.get('status') == 'PASS'
            and audit.get('supplement_sha256') == sha(MAN / 'supplement.tex')
            and audit.get('verifier_source_sha256') == sha(HERE / 'verify_supplement.py')
            and audit.get('supplement_review_sha256') == sha(RESULTS / 'supplement_review.json')
            and all((ROOT / n).is_file() and sha(ROOT / n) == h for n, h in audit['source_sha256'].items()))


def audit_supplement():
    if not supplement_valid():
        execute([sys.executable, str(HERE / 'verify_supplement.py')], ROOT, RESULTS / 'supplement_numeric_audit.log')
    if not supplement_valid():
        raise RuntimeError('Supplement numeric audit is missing or stale')


def compact_table():
    """Keep the main stopping table legible without scaling long column headings."""
    with (RESULTS / 'tables_stopping.csv').open() as stream:
        rows = list(csv.DictReader(stream))
    lines = [r'\begin{tabular}{lrrrrl}', r'\toprule',
             r'& \multicolumn{2}{c}{Bank-reference} & \multicolumn{2}{c}{Rich-reference} & Paired RMSEP difference \\',
             r'Season & RMSEP & Readings & RMSEP & Readings & Estimate [95\% CI] \\', r'\midrule']
    for row in rows:
        values = [int(row['held_season'])] + [float(row[k]) for k in
                  ('two_rmsep', 'two_mean_pulses', 'single_rmsep', 'single_mean_pulses', 'delta_rmsep', 'rmsep_ci_low', 'rmsep_ci_high')]
        lines.append(('%d & %.3f & %.3f & %.3f & %.3f & %.3f [%.3f, %.3f] ' % tuple(values)) + r'\\')
    lines += [r'\bottomrule', r'\end{tabular}']
    target = MAN / 'compact_stopping.tex'
    text = '\n'.join(lines) + '\n'
    if not target.exists() or target.read_text() != text:
        target.write_text(text)


def tex_inputs():
    files = list(MAN.glob('*.tex')) + list(MAN.glob('*.bib'))
    files += list((HERE / 'figures').rglob('*.pdf'))
    return {str(f.relative_to(HERE)): sha(f) for f in sorted(files)}


def compile_all():
    dependencies = tex_inputs()
    cache = RESULTS / 'compilation.json'
    if cache.exists():
        prior = load(cache)
        if (prior.get('inputs_sha256') == dependencies and prior.get('passed')
                and all((HERE / n).is_file() and sha(HERE / n) == h
                        for n, h in prior.get('outputs_sha256', {}).items())
                and len(prior.get('outputs_sha256', {})) == 2):
            print('Reused both compiled PDFs with matching source and output hashes.')
            return
    command_log = []
    for name, filename in NAMES.items():
        commands = [['pdflatex', '-interaction=nonstopmode', '-halt-on-error', '-file-line-error', name + '.tex'],
                    ['bibtex', name]]
        commands += [commands[0]] * 3
        for i, command in enumerate(commands):
            log = RESULTS / ('compile_%s_%s.log' % (name, i))
            execute(command, MAN, log)
            command_log.append({'command': command, 'exit_code': 0, 'log': str(log.relative_to(HERE))})
        text = (MAN / (name + '.log')).read_text(errors='replace')
        failures = [line for line in text.splitlines() if any(x in line for x in
                    ('Overfull', 'undefined references', 'undefined citations', 'Citation ', 'Label(s) may have changed'))]
        if failures:
            raise RuntimeError('Unresolved TeX diagnostics: ' + repr(failures))
        shutil.copyfile(MAN / (name + '.pdf'), PDF / filename)
    outputs = {str((PDF / filename).relative_to(HERE)): sha(PDF / filename) for filename in NAMES.values()}
    save(cache, {'passed': True, 'inputs_sha256': dependencies, 'outputs_sha256': outputs, 'commands': command_log})
    print('Compiled both PDFs with resolved citations and no overflowing boxes.')


def package_files():
    files = list(MAN.glob('*.tex')) + list(MAN.glob('*.bib'))
    files += list((HERE / 'figures').rglob('*.pdf')) + list((HERE / 'figures').rglob('*.png'))
    files += list((HERE / 'evidence_tables').rglob('*'))
    files += list(RESULTS.glob('tables_*.csv'))
    files += [RESULTS / n for n in ('evidence_manifest.json', 'evidence_cells.json', 'supplement_review.json', 'supplement_numeric_verification.json', 'reference_verification.json')]
    files += [HERE / n for n in ('README.md', 'scope.md', 'literature_and_claims_review.md', 'literature_expansion_sources.md', 'build_pdfs.sh', 'build_evidence.py', 'verify_supplement.py', 'verify_references.py', 'verify_resume.py', 'run.py', 'environment.json', 'requirements-paper.txt')]
    return sorted({f for f in files if f.is_file()})


def package():
    files = package_files()
    entries = {str(f.relative_to(HERE)): f.read_bytes() for f in files}
    internal = {name: hashlib.sha256(data).hexdigest() for name, data in sorted(entries.items())}
    entries['SOURCE_MANIFEST.json'] = (json.dumps({'sha256': internal}, indent=2, sort_keys=True) + '\n').encode()
    target = OUTPUT / 'Mango_Dataset_Paper_Source.zip'
    with zipfile.ZipFile(target, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(entries.items()):
            info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o100644 << 16)
            archive.writestr(info, data)
    with zipfile.ZipFile(target) as archive:
        assert archive.testzip() is None
        assert all(hashlib.sha256(archive.read(n)).hexdigest() == h for n, h in internal.items())
    save(RESULTS / 'package.json', {'passed': True, 'path': str(target.relative_to(HERE)),
         'sha256': sha(target), 'files': len(entries), 'payload_sha256': internal})
    print('Created self-contained TeX source archive: %s files.' % len(entries))


def verify():
    checks = []
    def check(name, condition, detail=None):
        checks.append({'name': name, 'passed': bool(condition), 'detail': detail})
    prior = preserved()
    check('prior_files_preserved', prior['passed'], prior)
    data_manifest = load(ROOT / 'data/manifest.json')
    check('official_dataset_provenance', data_manifest['dataset_doi'] == '10.17632/46htwnp833.3'
          and data_manifest['raw_sha256'] == data_manifest['official_file']['content_details']['sha256_hash'])
    check('dataset_bytes_unchanged', all(sha(ROOT / 'data' / n) == h
          for n, h in data_manifest['artifacts'].items()),
          'Opaque checksum verification only; raw spectra/outcome arrays are not parsed or rescored.')
    check('numerical_evidence_current', evidence_valid())
    ev = load(RESULTS / 'evidence_manifest.json')
    check('no_model_fitting', ev['fitting_performed'] is False and ev['raw_data_loaded'] is False)
    check('candidate_tuning_not_used_as_accuracy', ev['candidate_v4_scores_used'] is False)
    compilation = load(RESULTS / 'compilation.json')
    check('compilation_inputs_current', compilation['inputs_sha256'] == tex_inputs())
    check('compilation_successful', compilation['passed'] and all(c['exit_code'] == 0 for c in compilation['commands']))
    from pypdf import PdfReader
    pdf_records = {}
    for name, filename in NAMES.items():
        file = PDF / filename
        digest = sha(file)
        check(name + '_pdf_hash', compilation['outputs_sha256'][str(file.relative_to(HERE))] == digest)
        reader = PdfReader(file)
        pages = [p.extract_text() or '' for p in reader.pages]
        body = '\n'.join(pages)
        pdf_records[name] = {'path': str(file.relative_to(HERE)), 'sha256': digest, 'pages': len(pages)}
        check(name + '_nonempty_pages', all(len(p.strip()) > 35 for p in pages), len(pages))
        check(name + '_citations_resolved', '??' not in body)
        check(name + '_no_template_placeholders', all(w not in body for w in ('TODO', 'TBD', 'Lorem ipsum', 'INSERT HERE')))
        check(name + '_valid_page_bounds', all(float(p.mediabox.width) > 500 and float(p.mediabox.height) > 700 for p in reader.pages))
        log = (MAN / (name + '.log')).read_text(errors='replace')
        check(name + '_no_overflow', 'Overfull' not in log)
    visual_path = RESULTS / 'visual_review.json'
    visual = load(visual_path) if visual_path.exists() else {}
    check('visual_review_current', visual.get('passed') is True and visual.get('pdf_sha256') ==
          {k: v['sha256'] for k, v in pdf_records.items()}, visual.get('review_scope', 'pending'))
    pkg = load(RESULTS / 'package.json')
    check('package_current', sha(HERE / pkg['path']) == pkg['sha256'])
    with zipfile.ZipFile(HERE / pkg['path']) as archive:
        check('package_crc', archive.testzip() is None)
        check('package_files_current', all((HERE / n).is_file() and sha(HERE / n) == h
              and hashlib.sha256(archive.read(n)).hexdigest() == h for n, h in pkg['payload_sha256'].items()))
    isolated_path = RESULTS / 'isolated_compilation.json'
    isolated = load(isolated_path) if isolated_path.exists() else {}
    check('isolated_package_compilation', isolated.get('passed') is True and isolated.get('archive_sha256') == pkg['sha256'])
    supplement = load(RESULTS / 'supplement_review.json')
    check('supplement_review_current', supplement['supplement_sha256'] == sha(MAN / 'supplement.tex'))
    check('supplement_sources_unchanged', all((ROOT / n).is_file() and sha(ROOT / n) == h
          for n, h in supplement['source_files'].items()))
    numeric_path = RESULTS / 'supplement_numeric_verification.json'
    numeric = load(numeric_path) if numeric_path.exists() else {}
    check('supplement_numeric_audit', supplement_valid())
    copied = load(HERE / 'evidence_tables/manifest.json')
    check('copied_evidence_tables', all(sha(HERE / n) == d['sha256'] == sha(ROOT / d['source'])
          for n, d in copied.items()))
    reference_path = RESULTS / 'reference_verification.json'
    reference = load(reference_path) if reference_path.exists() else {}
    check('expanded_references_current', reference.get('passed') is True
          and reference.get('cited_references', 0) >= 25
          and reference.get('journal_or_proceedings_references', 0) >= 25
          and all((HERE / n).is_file() and sha(HERE / n) == h
                  for n, h in reference.get('source_sha256', {}).items()),
          reference.get('cited_references'))
    resume_path = RESULTS / 'resume_verification.json'
    resume = load(resume_path) if resume_path.exists() else None
    if resume:
        check('full_resume_byte_preservation', resume.get('passed') is True and resume.get('exit_code') == 0
              and resume.get('changed') == [] and resume['before_sha256'] == resume['after_sha256']
              and len(resume['after_sha256']) == resume['files_checked']
              and all((HERE / n).is_file() and sha(HERE / n) == h for n, h in resume['after_sha256'].items()),
              resume.get('files_checked'))
    failed = [c['name'] for c in checks if not c['passed']]
    result = {'passed': not failed, 'checks': checks, 'failed_checks': failed, 'check_count': len(checks),
              'numerical_check_count': ev['check_count'], 'numeric_values_checked': ev['checked_numeric_values'],
              'supplement_check_count': numeric.get('checks'), 'supplement_numeric_values': numeric.get('numeric_values_checked'),
              'recomputed_policy_cells': ev['recomputed_policy_cells'], 'prior_preservation': prior, 'pdfs': pdf_records,
              'cited_references': reference.get('cited_references'),
              'journal_or_proceedings_references': reference.get('journal_or_proceedings_references'),
              'resume_files_unchanged': resume['files_checked'] if resume else None,
              'scope': 'Completed existing-dataset manuscript consolidation; no fitting, new fruit data or physical/harvest validation.'}
    save(RESULTS / 'verification.json', result)
    lines = ['# Dataset-only paper verification', '',
             '**%s: %d delivery checks; %d numerical checks; %d recomputed policy cells.**' %
             ('PASS' if result['passed'] else 'INCOMPLETE', len(checks), ev['check_count'], ev['recomputed_policy_cells']), '',
             'All %d prior scientific files remain byte-identical. No model fitting or new data collection was performed.' % prior['files_checked'], '',
             'An independent supplementary transcription audit passed %s checks across all 17 tables, 1,237 displayed rows and %s numeric values. These verify reporting, not new agricultural performance.' % (numeric.get('checks'), numeric.get('numeric_values_checked')), '',
             'The expanded manuscript cites %s distinct references, including %s journal or proceedings articles. All cited entries render in the bibliography; the citation and claim review is retained in literature_expansion_sources.md.' % (reference.get('cited_references'), reference.get('journal_or_proceedings_references')), '',
             '| Check | Status |', '|---|---|']
    lines += ['| %s | %s |' % (c['name'], 'PASS' if c['passed'] else 'PENDING/FAIL') for c in checks]
    if resume:
        lines += ['', 'Full reporting workflow resume exited successfully and preserved all %d checked paper artifacts byte for byte.' % resume['files_checked']]
    lines += ['', 'The original seasonal benchmark and exploratory development follow-ups remain separately labeled. Seasons 4 and 5 belong to the same source dataset. Field data, a physical scanner and harvest thresholds are outside completion scope.', '',
              'The manuscript is complete for author review. Author identity and declarations require author input before submission. No submission or public release is claimed.', '',
              'Evidence: results/verification.json, evidence_manifest.json, visual_review.json, package.json and isolated_compilation.json.']
    (HERE / 'verification_report.md').write_text('\n'.join(lines) + '\n')
    print(json.dumps({k: result[k] for k in ('passed', 'check_count', 'numerical_check_count', 'failed_checks')}, indent=2))
    if failed:
        raise SystemExit(1)


def isolated():
    package_info = load(RESULTS / 'package.json')
    with tempfile.TemporaryDirectory(prefix='mango-paper-') as directory:
        directory = Path(directory)
        with zipfile.ZipFile(HERE / package_info['path']) as archive:
            assert all(not Path(n).is_absolute() and '..' not in Path(n).parts for n in archive.namelist())
            archive.extractall(directory)
        execute(['bash', 'build_pdfs.sh'], directory, RESULTS / 'isolated_compilation.log')
        from pypdf import PdfReader
        pages = {name: len(PdfReader(directory / 'output/pdf' / filename).pages) for name, filename in NAMES.items()}
    save(RESULTS / 'isolated_compilation.json', {'passed': True, 'archive_sha256': package_info['sha256'],
         'command': 'bash build_pdfs.sh', 'exit_code': 0, 'pages': pages,
         'scope': 'Archive extracted outside the project, no references to workspace assets required for TeX compilation.'})
    print('Both source-package PDFs compiled independently outside the workspace.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=['all', 'report', 'compile', 'package', 'verify', 'isolated', 'status'])
    parser.add_argument('--resume', action='store_true', help='Completed current stages are reused by default.')
    args = parser.parse_args()
    for directory in [RESULTS, OUTPUT, PDF]: directory.mkdir(parents=True, exist_ok=True)
    if args.stage == 'all':
        report(); compile_all()
        execute([sys.executable, str(HERE / 'verify_references.py')], ROOT, RESULTS / 'reference_verification.log')
        package(); isolated(); verify()
    elif args.stage == 'report': report()
    elif args.stage == 'compile': compile_all()
    elif args.stage == 'package': package()
    elif args.stage == 'verify': verify()
    elif args.stage == 'isolated': isolated()
    else: print((HERE / 'RUN_STATUS.md').read_text())


if __name__ == '__main__':
    main()

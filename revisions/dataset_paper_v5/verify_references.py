#!/usr/bin/env python3
"""Check cited-reference coverage and the scope of the literature-only revision."""
import hashlib
import json
from pathlib import Path
import re
import zipfile

HERE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit():
    main = HERE / 'manuscript/main.tex'
    bib = HERE / 'manuscript/references.bib'
    bbl = HERE / 'manuscript/main.bbl'
    text = main.read_text()
    bibliography = bib.read_text()
    entries = re.findall(r'^@(\w+)\s*\{\s*([^,]+),', bibliography, re.M)
    kinds = {key: kind.lower() for kind, key in entries}
    cited = sorted({key.strip() for group in re.findall(
        r'\\cite\w*(?:\[[^\]]*\])*\{([^}]+)\}', text) for key in group.split(',')})
    rendered = re.findall(r'\\bibitem(?:\[[\s\S]*?\])?\s*\{([^}]+)\}', bbl.read_text())
    dois = re.findall(r'^\s*doi\s*=\s*\{([^}]+)\}', bibliography, re.M | re.I)
    academic = [key for key in cited if kinds.get(key) in ('article', 'inproceedings')]
    heading = '\\subsection{Related work and scope of the contribution}'
    ending = '\\section{Materials and methods}'
    section = text.split(heading, 1)[1].split(ending, 1)[0]
    claims = HERE / 'literature_expansion_sources.md'
    sources = {str(f.relative_to(HERE)): sha(f) for f in
               (main, bib, bbl, claims, Path(__file__).resolve())}
    checks = {
        'at_least_25_cited_references': len(cited) >= 25,
        'at_least_25_journal_or_proceedings_references': len(academic) >= 25,
        'all_citations_defined': set(cited) <= set(kinds),
        'all_and_only_cited_references_rendered': set(cited) == set(rendered),
        'no_duplicate_bibliography_keys': len(entries) == len(kinds),
        'no_duplicate_rendered_references': len(rendered) == len(set(rendered)),
        'no_duplicate_dois': len(dois) == len(set(d.lower() for d in dois)),
        'no_uncited_padding': '\\nocite' not in text,
        'source_and_claim_review_present': claims.is_file() and claims.stat().st_size > 1000,
    }
    archive = HERE / 'review_history/before_related_work_expansion.zip'
    if archive.exists():
        with zipfile.ZipFile(archive) as z:
            before = z.read('manuscript/main.tex').decode()
        def strip(t):
            body = t.split(heading, 1)[0] + ending + t.split(ending, 1)[1]
            # The first dataset table is kept below Related Work; only its
            # allowed float position changed, not its caption or data.
            return re.sub(r'\\begin\{table\}\[[^]]+\]', r'\\begin{table}', body, count=1)
        checks['main_prose_and_data_outside_related_work_unchanged'] = strip(text) == strip(before)
    result = {'passed': all(checks.values()), 'checks': checks,
              'cited_references': len(cited), 'journal_or_proceedings_references': len(academic),
              'rendered_references': len(rendered), 'related_work_word_count_approx': len(section.split()),
              'citation_keys': cited, 'source_sha256': sources,
              'scope': 'Citation coverage, compilation and edit-scope checks. Bibliographic truth and claim support are separately reviewed against primary sources in literature_expansion_sources.md.'}
    (HERE / 'results/reference_verification.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps({k: result[k] for k in ('passed', 'cited_references', 'journal_or_proceedings_references', 'rendered_references', 'checks')}, indent=2))
    if not result['passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    audit()

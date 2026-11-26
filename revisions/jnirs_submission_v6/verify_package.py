#!/usr/bin/env python3
"""Check the journal conversion without loading spectra or fitting models."""
from pathlib import Path
import hashlib
import json
import re
from pypdf import PdfReader

HERE = Path(__file__).resolve().parent
V5 = HERE.parent / 'dataset_paper_v5'
checks = {}
details = {}

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def cited(text):
    return list(dict.fromkeys(k.strip() for group in re.findall(
        r'\\cite\w*(?:\[[^\]]*\])*\{([^}]+)\}', text) for k in group.split(',')))

def numbers(text):
    text = re.sub(r'\\cite\w*(?:\[[^\]]*\])*\{[^}]+\}', '', text)
    text = re.sub(r'\\includegraphics(?:\[[^\]]*\])?\{[^}]+\}', '', text)
    # Page-layout space reservations are not scientific numeric claims.
    text = re.sub(r'\\Needspace\{[^}]+\}', '', text)
    return re.findall(r'(?<![A-Za-z])[-+]?\d+(?:[.,]\d+)*', text)

main = (HERE / 'main.tex').read_text()
supp = (HERE / 'supplement.tex').read_text()
bib = (HERE / 'references.bib').read_text()
keys = re.findall(r'^@\w+\{([^,]+),', bib, re.M)
dois = re.findall(r'\bdoi\s*=\s*\{([^}]+)\}', bib, re.I)
main_keys = cited(main)
rendered = re.findall(r'\\bibitem\{([^}]+)\}', (HERE / 'main.bbl').read_text())
checks['all_30_sources_cited_and_rendered_in_first_citation_order'] = len(main_keys) == 30 and main_keys == rendered
checks['bibliography_keys_and_dois_unique'] = len(keys) == len(set(keys)) and len(dois) == len(set(x.lower() for x in dois))
checks['no_uncited_reference_padding'] = set(main_keys) == set(keys) and '\\nocite' not in main
checks['all_supplement_citations_resolved'] = set(cited(supp)) == set(re.findall(r'\\bibitem\{([^}]+)\}', (HERE / 'supplement.bbl').read_text()))
checks['sage_class_options'] = '\\documentclass[Review,sagev,times]{sagej}' in main
checks['unstructured_abstract'] = '\\begin{abstract}' in main and '\\end{abstract}' in main
keywords = re.search(r'\\keywords\{([^}]+)\}', main)[1].split(',')
checks['at_least_five_keywords'] = len(keywords) >= 5
decl = (HERE / 'declarations.tex').read_text()
required = ['Acknowledgements', 'Author Contributions', 'Statements and Declarations',
            'Ethical considerations', 'Consent to participate', 'Consent for publication',
            'Declaration of conflicting interest', 'Funding statement', 'Data availability']
checks['all_journal_declaration_headings'] = all('{' + heading + '}' in decl for heading in required)
checks['ai_assistance_disclosed_without_invented_human_review'] = 'OpenAI Codex' in decl and '\\HumanReviewStatement' in decl
provenance = json.loads((HERE / 'template_provenance/mirror_source.json').read_text())
checks['distributed_class_and_style_unchanged'] = all(sha(HERE / name) == entry['sha256'] for name, entry in provenance['files'].items())
original_style = (HERE / 'sagev.bst').read_text()
derivative = (HERE / 'jnirs_sagev.bst').read_text().split('\n', 3)[3]
checks['local_bst_only_adds_conference_year'] = derivative.replace('  format.date "year" output.check\n  format.pages "pages" output.check', '  format.pages "pages" output.check', 1) == original_style
details['documents'] = {}
for name, delivery in [('main','Mango_JNIRS_Manuscript.pdf'), ('supplement','Mango_JNIRS_Supplement.pdf')]:
    log = (HERE / (name + '.log')).read_text()
    checks[name + '_clean_latex_log'] = not re.search(r'Overfull|Underfull|Warning|undefined|^!', log, re.M)
    blg = (HERE / (name + '.blg')).read_text()
    checks[name + '_clean_bibtex_log'] = not re.search(r'Warning--|error message', blg)
    path = HERE / 'output/pdf' / delivery
    reader = PdfReader(path)
    texts = [page.extract_text() or '' for page in reader.pages]
    checks[name + '_no_blank_pages'] = all(len(t.strip()) > 80 for t in texts)
    checks[name + '_no_unresolved_citations_or_publisher_placeholders'] = not any(
        token in '\n'.join(texts) for token in ['ToBeAssigned', 'Journal Title', 'XX(X)', '??'])
    checks[name + '_delivery_matches_compiled_pdf'] = sha(path) == sha(HERE / (name + '.pdf'))
    details['documents'][name] = {'pages':len(texts), 'sha256':sha(path), 'size_bytes':path.stat().st_size}
    visual_path = HERE / 'results' / (name + '_visual_review.json')
    if visual_path.is_file():
        visual = json.loads(visual_path.read_text())
        checks[name + '_all_pages_visually_reviewed_at_current_hash'] = (
            visual.get('status', '').lower() == 'pass'
            and visual.get('pdf_sha256') == sha(path)
            and visual.get('pages_inspected') == list(range(1, len(texts) + 1)))
    else:
        checks[name + '_all_pages_visually_reviewed_at_current_hash'] = False
independent_path = HERE / 'results/independent_content_review.json'
if independent_path.is_file():
    independent = json.loads(independent_path.read_text())
    checks['independent_content_review_passed'] = (
        independent.get('status') == 'PASS'
        and independent.get('passed_checks') == independent.get('check_count')
        and not independent.get('failed_checks'))
    prefix = 'revisions/jnirs_submission_v6/'
    local_core = {key[len(prefix):]: digest for key, digest in independent['core_sha256'].items()
                  if key.startswith(prefix)}
    checks['independent_content_review_core_hashes_current'] = bool(local_core) and all(
        (HERE / name).is_file() and sha(HERE / name) == digest
        for name, digest in local_core.items())
else:
    checks['independent_content_review_passed'] = False
    checks['independent_content_review_core_hashes_current'] = False
details['abstract_words_whitespace_count'] = len(main.split('\\begin{abstract}',1)[1].split('\\end{abstract}',1)[0].split())
details['main_figures'] = len(re.findall(r'\\begin\{figure\}', main))
details['main_tables'] = len(re.findall(r'\\begin\{table\}', main))
details['keywords'] = len(keywords)
details['references'] = len(main_keys)
if V5.is_dir():
    previous = (V5 / 'manuscript/main.tex').read_text()
    old_body = previous.split('\\section{Introduction}',1)[1].split('\\section*{Data, software and declarations}',1)[0]
    new_body = main.split('\\section{Introduction}',1)[1].split('\\input{declarations.tex}',1)[0]
    checks['main_all_scientific_numeric_tokens_preserved'] = numbers(old_body) == numbers(new_body)
    checks['abstract_all_numeric_tokens_preserved'] = numbers(previous.split('\\begin{abstract}',1)[1].split('\\end{abstract}',1)[0]) == numbers(main.split('\\begin{abstract}',1)[1].split('\\end{abstract}',1)[0])
    # The final operational inventory was intentionally replaced with concise
    # data/code availability. Preserve the complete scientific sections and
    # separately require every supplementary table to remain byte-identical.
    previous_supp = (V5 / 'manuscript/supplement.tex').read_text()
    old_supp = previous_supp.split('\\section{Scope, provenance and interpretation}',1)[1].split('\\section{Evidence inventory, verification and claim boundaries}',1)[0]
    new_supp = supp.split('\\section{Scope, provenance and interpretation}',1)[1].split('\\section{Data and code availability}',1)[0]
    checks['supplement_all_scientific_numeric_tokens_preserved'] = numbers(old_supp) == numbers(new_supp)
    table_pattern = r'\\begin\{longtable\}.*?\\end\{longtable\}'
    old_tables = re.findall(table_pattern, previous_supp, re.S)
    new_tables = re.findall(table_pattern, supp, re.S)
    checks['all_17_supplement_tables_byte_identical_to_v5'] = len(new_tables) == 17 and old_tables == new_tables
    table_paths = [p for p in (V5 / 'manuscript').glob('*.tex') if p.name not in ['main.tex','supplement.tex']]
    checks['all_generated_table_sources_unchanged'] = all(sha(path) == sha(HERE / path.name) for path in table_paths)
    before = json.loads((HERE / 'results/v5_preservation_before.json').read_text())
    root = HERE.parents[1]
    altered = [name for name, digest in before.items() if not (root/name).is_file() or sha(root/name) != digest]
    checks['all_v5_files_preserved'] = not altered
    details['v5_files_checked'] = len(before)
    details['altered_v5_files'] = altered
    details['main_scientific_numeric_tokens'] = len(numbers(old_body))
    details['supplement_scientific_numeric_tokens'] = len(numbers(old_supp))
    details['unchanged_table_fragments'] = len(table_paths)
result = {'passed':all(checks.values()), 'checks':checks, 'details':details,
          'scope':'Formatting, source preservation and document integrity. Existing numerical audits are inherited, not rerun model evaluations.',
          'author_inputs_pending':True, 'submission_performed':False}
(HERE/'results/verification.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
raise SystemExit(0 if result['passed'] else 1)

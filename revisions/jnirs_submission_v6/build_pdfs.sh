#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
mkdir -p output/pdf results
for document in main supplement; do
  pdflatex -interaction=nonstopmode -halt-on-error -file-line-error "$document.tex" > "results/$document.build.log" 2>&1
  bibtex "$document" >> "results/$document.build.log" 2>&1
  for pass in 1 2 3; do
    pdflatex -interaction=nonstopmode -halt-on-error -file-line-error "$document.tex" >> "results/$document.build.log" 2>&1
  done
done
cp main.pdf output/pdf/Mango_JNIRS_Manuscript.pdf
cp supplement.pdf output/pdf/Mango_JNIRS_Supplement.pdf
printf 'Built main manuscript and supplement. See output/pdf/.\n'

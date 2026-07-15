#!/usr/bin/env bash
# Build the DMTAP Internet-Draft PDF from the spec markdown.
# Requires: pandoc (md -> tex bodies) and tectonic (or xelatex/pdflatex).
set -euo pipefail
cd "$(dirname "$0")"

SPEC=..            # the spec markdown lives one level up
mkdir -p body

# Convert each spec section to a LaTeX body fragment (not standalone).
# top-level-division=section maps #/##/### -> section/subsection/subsubsection.
for f in "$SPEC"/[0-9][0-9]-*.md; do
  name="$(basename "$f" .md)"
  pandoc "$f" \
    --from=gfm+tex_math_dollars \
    --to=latex \
    --top-level-division=section \
    --wrap=preserve \
    -o "body/${name}.tex"
done

echo "Converted $(ls body/*.tex | wc -l | tr -d ' ') sections."

# Compile (twice for ToC). Prefer tectonic; fall back to latexmk/xelatex/pdflatex.
if command -v tectonic >/dev/null 2>&1; then
  tectonic --keep-logs dmtap.tex
elif command -v latexmk >/dev/null 2>&1; then
  latexmk -pdf -xelatex dmtap.tex
elif command -v xelatex >/dev/null 2>&1; then
  xelatex dmtap.tex && xelatex dmtap.tex
else
  pdflatex dmtap.tex && pdflatex dmtap.tex
fi

echo "Built: $(pwd)/dmtap.pdf"

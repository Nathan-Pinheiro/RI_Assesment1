#!/usr/bin/env bash
# ============================================================
#  build.sh
#  Cleans auxiliary files and regenerates report.pdf
# ============================================================

set -euo pipefail

TEXFILE="report.tex"
PDFFILE="report.pdf"

if [ ! -f "$TEXFILE" ]; then
    echo "Error: $TEXFILE not found in $(pwd)"
    exit 1
fi

echo "============================================"
echo " Cleaning auxiliary files..."
echo "============================================"
latexmk -C "$TEXFILE" || true

# Additional cleanup in case latexmk leaves traces
rm -f \
    *.aux *.log *.out *.toc *.lof *.lot \
    *.bbl *.blg *.bcf *.run.xml \
    *.fls *.fdb_latexmk *.synctex.gz \
    *.nav *.snm *.vrb

echo "============================================"
echo " Compiling $TEXFILE..."
echo "============================================"
latexmk -pdf -interaction=nonstopmode -halt-on-error "$TEXFILE"

if [ -f "$PDFFILE" ]; then
    echo "============================================"
    echo " Success: $PDFFILE generated."
    echo " Size: $(du -h "$PDFFILE" | cut -f1)"
    echo "============================================"
else
    echo "============================================"
    echo " Failure: $PDFFILE not generated. See the .log file."
    echo "============================================"
    exit 1
fi
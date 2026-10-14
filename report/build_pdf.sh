#!/usr/bin/env bash
# ============================================================
#  build.sh
#  Nettoie les fichiers auxiliaires et regenere report.pdf
# ============================================================

set -euo pipefail

TEXFILE="report.tex"
PDFFILE="report.pdf"

if [ ! -f "$TEXFILE" ]; then
    echo "Erreur : $TEXFILE introuvable dans $(pwd)"
    exit 1
fi

echo "============================================"
echo " Nettoyage des fichiers auxiliaires..."
echo "============================================"
latexmk -C "$TEXFILE" || true

# Nettoyage complementaire au cas ou latexmk laisse des traces
rm -f \
    *.aux *.log *.out *.toc *.lof *.lot \
    *.bbl *.blg *.bcf *.run.xml \
    *.fls *.fdb_latexmk *.synctex.gz \
    *.nav *.snm *.vrb

echo "============================================"
echo " Compilation de $TEXFILE..."
echo "============================================"
latexmk -pdf -interaction=nonstopmode -halt-on-error "$TEXFILE"

if [ -f "$PDFFILE" ]; then
    echo "============================================"
    echo " Succes : $PDFFILE genere."
    echo " Taille : $(du -h "$PDFFILE" | cut -f1)"
    echo "============================================"
else
    echo "============================================"
    echo " Echec : $PDFFILE non genere. Voir le .log"
    echo "============================================"
    exit 1
fi
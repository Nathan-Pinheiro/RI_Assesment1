#!/usr/bin/env bash
# ============================================================
#  install_latex.sh
#  Installs all LaTeX dependencies required to compile
#  report.tex (Debian / Ubuntu / WSL)
# ============================================================

set -euo pipefail

echo "============================================"
echo " Updating apt repositories..."
echo "============================================"
sudo apt update

echo "============================================"
echo " Installing LaTeX packages..."
echo "============================================"
sudo apt install -y \
    texlive-latex-base \
    texlive-latex-recommended \
    texlive-latex-extra \
    texlive-fonts-recommended \
    texlive-science \
    texlive-publishers \
    texlive-bibtex-extra \
    biber \
    latexmk

echo "============================================"
echo " Verifying critical packages..."
echo "============================================"
for pkg in IEEEtran.cls booktabs.sty geometry.sty graphicx.sty hyperref.sty \
           amsmath.sty authblk.sty titlesec.sty babel.sty siunitx.sty; do
    if kpsewhich "$pkg" > /dev/null 2>&1; then
        echo "  [OK]  $pkg"
    else
        echo "  [!!]  $pkg MISSING"
    fi
done

echo "============================================"
echo " Installation complete."
echo " You can now run ./build_pdf.sh"
echo "============================================"
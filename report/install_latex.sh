#!/usr/bin/env bash
# ============================================================
#  install_deps.sh
#  Installe toutes les dependances LaTeX necessaires
#  pour compiler report.tex (Debian / Ubuntu / WSL)
# ============================================================

set -euo pipefail

echo "============================================"
echo " Mise a jour des depots apt..."
echo "============================================"
sudo apt update

echo "============================================"
echo " Installation des paquets LaTeX..."
echo "============================================"
sudo apt install -y \
    texlive-latex-base \
    texlive-latex-recommended \
    texlive-latex-extra \
    texlive-fonts-recommended \
    texlive-science \
    texlive-bibtex-extra \
    biber \
    latexmk

echo "============================================"
echo " Verification des paquets critiques..."
echo "============================================"
for pkg in booktabs.sty geometry.sty graphicx.sty hyperref.sty \
           amsmath.sty authblk.sty titlesec.sty babel.sty; do
    if kpsewhich "$pkg" > /dev/null 2>&1; then
        echo "  [OK]  $pkg"
    else
        echo "  [!!]  $pkg MANQUANT"
    fi
done

echo "============================================"
echo " Installation terminee."
echo " Vous pouvez maintenant lancer ./build.sh"
echo "============================================"
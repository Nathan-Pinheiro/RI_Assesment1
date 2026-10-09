#!/bin/bash
# setup_gpu.sh — Active l'accélération GPU pour Webots sous WSL2.
# Détecte le GPU Windows, configure Mesa D3D12 dans ~/.bashrc,
# puis relance un shell pour que les changements soient actifs.

set -e

# --- 1. Vérifie qu'on est bien sous WSL2 ---
if ! command -v powershell.exe >/dev/null 2>&1; then
    echo "Erreur : powershell.exe introuvable."
    echo "Ce script est prévu pour WSL2 uniquement."
    echo "Sur Linux natif, Webots utilise déjà le GPU."
    exit 1
fi
echo "[1/4] WSL2 détecté"

# --- 2. Détection du GPU Windows ---
GPU_NAME=$(powershell.exe -NoProfile -Command \
    "(Get-CimInstance Win32_VideoController | Where-Object { \$_.Name -notmatch 'Basic|Microsoft|Remote' } | Select-Object -First 1).Name" \
    2>/dev/null | tr -d '\r')

if [ -z "$GPU_NAME" ]; then
    echo "[2/4] Aucun GPU détecté — fallback sur 'auto'"
    ADAPTER="auto"
else
    echo "[2/4] GPU détecté : $GPU_NAME"
fi

# --- 3. Choix de l'adaptateur Mesa ---
case "$GPU_NAME" in
    *NVIDIA*|*GeForce*|*RTX*|*Quadro*|*Tesla*) ADAPTER="NVIDIA" ;;
    *AMD*|*Radeon*|*Ryzen*)                    ADAPTER="AMD"    ;;
    *Intel*|*Iris*|*UHD*|*Arc*)                ADAPTER="Intel"  ;;
    *)                                          ADAPTER="auto"   ;;
esac
echo "[3/4] Adaptateur D3D12 : $ADAPTER"

# --- 4. Écriture dans ~/.bashrc (idempotent) ---
BLOCK_START="# >>> ri_a1 GPU acceleration >>>"
BLOCK_END="# <<< ri_a1 GPU acceleration <<<"

if grep -qF "$BLOCK_START" ~/.bashrc 2>/dev/null; then
    sed -i "/$BLOCK_START/,/$BLOCK_END/d" ~/.bashrc
fi

cat >> ~/.bashrc << EOF
$BLOCK_START
export MESA_D3D12_DEFAULT_ADAPTER_NAME=$ADAPTER
export GALLIUM_DRIVER=d3d12
export LIBGL_ALWAYS_SOFTWARE=false
$BLOCK_END
EOF
echo "[4/4] Configuration ajoutée à ~/.bashrc"
echo ""

# --- Rechargement automatique ---
# Un script ne peut pas modifier le shell parent. On lance donc un
# nouveau shell qui lit .bashrc au démarrage.
if [ -t 0 ]; then
    echo "Rechargement du shell..."
    exec bash --rcfile ~/.bashrc -i
else
    echo "Session non interactive. Tapez : source ~/.bashrc"
fi
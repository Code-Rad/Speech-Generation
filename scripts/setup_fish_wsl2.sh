#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# VoiceForge — Fish S2 Pro WSL2 Setup Script
# ═══════════════════════════════════════════════════════════════
#
# Run ONCE inside WSL2 Ubuntu on TRIJYA-7 to install all
# dependencies needed to serve Fish Speech S2 Pro.
#
# Usage:
#   1. On TRIJYA-7 Windows, open a terminal and type: wsl
#   2. Inside WSL2, run:
#        bash /mnt/c/VoiceForge/scripts/setup_fish_wsl2.sh
#
# After setup completes, start the server with:
#   bash /mnt/c/VoiceForge/scripts/start_fish.sh
#
# Prerequisites:
#   - WSL2 with Ubuntu 22.04+ installed on TRIJYA-7
#   - Windows GPU driver >= 535.x (enables CUDA in WSL2)
#   - RTX 4090 24GB VRAM (Fish S2 Pro needs ~12-16GB)
#   - Internet access to download model (~8GB from HuggingFace)
#   - Recommended: run setup_voxtral_wsl2.sh first
#     (shares Python/CUDA base installation)
#
# VRAM co-existence with Voxtral:
#   Voxtral-4B weights ≈ 8GB + Fish S2 Pro weights ≈ 8.8GB = ~17GB
#   Both servers use --gpu-memory-utilization 0.5 (12GB each = 24GB)
#   They can both run on the RTX 4090 simultaneously.
# ═══════════════════════════════════════════════════════════════

set -e  # Exit immediately on any error

echo ""
echo "╔═══════════════════════════════════════════════════════╗"
echo "║   VoiceForge — Fish S2 Pro WSL2 Setup                 ║"
echo "║   Model: fishaudio/s2-pro (#1 TTS-Arena2)             ║"
echo "╚═══════════════════════════════════════════════════════╝"
echo ""

# ── Step 1: Update and install system deps ────────────────────
echo "▶ Step 1/5 — Installing system dependencies..."
sudo apt update -q
sudo apt install -y -q \
    python3.11 \
    python3.11-venv \
    python3-pip \
    git \
    curl \
    wget \
    build-essential \
    libsndfile1 \
    ffmpeg
echo "✓ System packages installed"
echo ""

# Ensure pip is up to date
python3.11 -m pip install --upgrade pip --quiet

# ── Step 2: Install fish-speech ───────────────────────────────
echo "▶ Step 2/5 — Installing fish-speech package..."
pip3 install fish-speech --upgrade --quiet
echo "✓ fish-speech installed"
echo ""

# ── Step 3: Install SGLang (optional — for SGLang-style serving) ──
echo "▶ Step 3/5 — Installing SGLang (GPU inference framework)..."
pip3 install "sglang[all]" --quiet || {
    echo "  NOTE: sglang[all] failed — installing sglang core only"
    pip3 install sglang --quiet
}
echo "✓ SGLang installed"
echo ""

# ── Step 4: Install audio/HTTP support packages ───────────────
echo "▶ Step 4/5 — Installing audio and HTTP packages..."
pip3 install \
    soundfile \
    httpx \
    numpy \
    huggingface_hub \
    --quiet
echo "✓ Audio and HTTP packages installed"
echo ""

# ── Step 5: Download Fish S2 Pro model ───────────────────────
echo "▶ Step 5/5 — Downloading Fish S2 Pro model (~8GB)..."
echo "  Model: fishaudio/s2-pro"
echo "  Destination: ~/.cache/fish_s2_pro"
echo "  This may take 10-20 minutes on first run."
echo ""

mkdir -p ~/.cache/fish_s2_pro

huggingface-cli download fishaudio/s2-pro \
    --local-dir ~/.cache/fish_s2_pro \
    --quiet

echo "✓ Fish S2 Pro model downloaded"
echo ""

# ── Verification ──────────────────────────────────────────────
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "VERIFICATION:"
python3 -c "
import sys
checks = []

try:
    import fish_speech
    checks.append(('fish-speech', True, 'imported ok'))
except ImportError as e:
    checks.append(('fish-speech', False, str(e)))

try:
    import torch
    cuda = torch.cuda.is_available()
    if cuda:
        props = torch.cuda.get_device_properties(0)
        vram_gb = props.total_memory / (1024**3)
        checks.append(('CUDA', True, f'{props.name} {vram_gb:.1f}GB'))
    else:
        checks.append(('CUDA', False, 'not available'))
except ImportError as e:
    checks.append(('CUDA/torch', False, str(e)))

try:
    import soundfile
    checks.append(('soundfile', True, 'ok'))
except ImportError as e:
    checks.append(('soundfile', False, str(e)))

try:
    import httpx
    checks.append(('httpx', True, httpx.__version__))
except ImportError as e:
    checks.append(('httpx', False, str(e)))

import os
model_path = os.path.expanduser('~/.cache/fish_s2_pro')
model_exists = os.path.isdir(model_path) and len(os.listdir(model_path)) > 0
checks.append(('model files', model_exists, model_path if model_exists else 'directory empty'))

all_pass = True
for name, ok, detail in checks:
    icon = '✅' if ok else '❌'
    print(f'  {icon} {name}: {detail}')
    if not ok:
        all_pass = False

print()
if all_pass:
    print('  ✅ Fish S2 Pro WSL2 setup COMPLETE')
else:
    print('  ❌ Some checks failed — review errors above')
    sys.exit(1)
"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "NEXT STEPS:"
echo "  1. Start the Fish S2 Pro server:"
echo "       bash /mnt/c/VoiceForge/scripts/start_fish.sh"
echo ""
echo "  2. On startup, the model loads into GPU VRAM (~30 seconds)."
echo "     Wait for: 'Uvicorn running on http://0.0.0.0:8092'"
echo ""
echo "  3. Both Voxtral (port 8091) and Fish (port 8092) can run"
echo "     simultaneously on RTX 4090 — each uses 0.5 GPU utilization."
echo ""
echo "  4. Set VOICEFORGE_PHASE=2 in server/.env then restart FastAPI."
echo "     English → Fish S2 Pro, Hindi/Hinglish → Voxtral TTS."
echo ""

#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# VoiceForge — Voxtral TTS WSL2 Setup Script
# ═══════════════════════════════════════════════════════════════
#
# Run ONCE inside WSL2 Ubuntu on TRIJYA-7 to install all
# dependencies needed to serve Voxtral TTS via vLLM-Omni.
#
# Usage:
#   1. On TRIJYA-7 Windows, open a terminal and type: wsl
#   2. Inside WSL2, run:
#        bash /mnt/c/VoiceForge/scripts/setup_voxtral_wsl2.sh
#
# After setup completes, start the server with:
#   bash /mnt/c/VoiceForge/scripts/start_voxtral.sh
#
# Requirements:
#   - WSL2 with Ubuntu 22.04+ installed on TRIJYA-7
#   - Windows GPU driver ≥ 535.x (enables CUDA in WSL2 automatically)
#   - RTX 4090 with 24GB VRAM (16GB needed for Voxtral-4B)
#   - Internet access to download model (~8GB from HuggingFace)
# ═══════════════════════════════════════════════════════════════

set -e  # Exit immediately on any error

echo ""
echo "╔═══════════════════════════════════════════════════════╗"
echo "║   VoiceForge — Voxtral TTS WSL2 Setup                 ║"
echo "║   Model: mistralai/Voxtral-4B-TTS-2603                ║"
echo "╚═══════════════════════════════════════════════════════╝"
echo ""

# ── Step 1: Update Ubuntu ─────────────────────────────────────
echo "▶ Step 1/7 — Updating Ubuntu packages..."
sudo apt update -q && sudo apt upgrade -y -q
echo "✓ Ubuntu updated"
echo ""

# ── Step 2: Install Python and system dependencies ───────────
echo "▶ Step 2/7 — Installing Python 3.11 and system packages..."
sudo apt install -y -q \
    python3.11 \
    python3.11-venv \
    python3-pip \
    python3.11-dev \
    git \
    curl \
    wget \
    build-essential \
    libsndfile1
echo "✓ System packages installed"
echo ""

# Ensure pip is up to date
python3.11 -m pip install --upgrade pip --quiet

# ── Step 3: Verify CUDA is accessible from WSL2 ─────────────
echo "▶ Step 3/7 — Verifying CUDA access from WSL2..."
echo "  (CUDA in WSL2 is provided via the Windows GPU driver —"
echo "   no separate CUDA toolkit installation needed)"
echo ""

# Install torch first to verify CUDA
echo "  Installing torch for CUDA verification..."
pip3 install torch --index-url https://download.pytorch.org/whl/cu121 --quiet

python3 -c "
import torch
cuda_ok = torch.cuda.is_available()
print(f'  CUDA available: {cuda_ok}')
if cuda_ok:
    props = torch.cuda.get_device_properties(0)
    vram_gb = props.total_memory / (1024**3)
    print(f'  GPU: {props.name}')
    print(f'  VRAM: {vram_gb:.1f} GB')
    if vram_gb < 14:
        print('  WARNING: Voxtral-4B needs ~16GB VRAM. This GPU may be too small.')
    else:
        print(f'  OK: {vram_gb:.1f}GB VRAM available (need ~16GB)')
else:
    print('  WARNING: CUDA not available from WSL2.')
    print('  Check: Windows GPU driver >= 535.x, WSL2 kernel >= 5.10.43')
"
echo ""

# ── Step 4: Install vLLM ──────────────────────────────────────
echo "▶ Step 4/7 — Installing vLLM (core inference framework)..."
pip3 install "vllm>=0.8.0" --quiet
echo "✓ vLLM installed"
python3 -c "import vllm; print(f'  vLLM version: {vllm.__version__}')"
echo ""

# ── Step 5: Install vLLM-Omni (Voxtral support extension) ────
echo "▶ Step 5/7 — Installing vLLM-Omni (Voxtral TTS support)..."
pip3 install vllm-omni --upgrade --quiet
echo "✓ vLLM-Omni installed"
echo ""

# ── Step 6: Install mistral_common ───────────────────────────
echo "▶ Step 6/7 — Installing mistral_common (Mistral tokenizer)..."
pip3 install "mistral_common>=1.10.0" --quiet
echo "✓ mistral_common installed"
python3 -c "import mistral_common; print(f'  mistral_common version: {mistral_common.__version__}')"
echo ""

# ── Step 7: Install additional audio/HTTP dependencies ───────
echo "▶ Step 7/7 — Installing audio and HTTP packages..."
pip3 install \
    soundfile \
    httpx \
    numpy \
    huggingface_hub \
    --quiet
echo "✓ Audio and HTTP packages installed"
echo ""

# ── Final verification ────────────────────────────────────────
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "VERIFICATION:"
python3 -c "
import sys
checks = []

try:
    import vllm
    checks.append(('vLLM', True, vllm.__version__))
except ImportError as e:
    checks.append(('vLLM', False, str(e)))

try:
    import mistral_common
    checks.append(('mistral_common', True, mistral_common.__version__))
except ImportError as e:
    checks.append(('mistral_common', False, str(e)))

try:
    import torch
    cuda = torch.cuda.is_available()
    checks.append(('CUDA', cuda, 'available' if cuda else 'NOT available'))
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

all_pass = True
for name, ok, detail in checks:
    icon = '✅' if ok else '❌'
    print(f'  {icon} {name}: {detail}')
    if not ok:
        all_pass = False

print()
if all_pass:
    print('  ✅ WSL2 setup COMPLETE — all dependencies installed')
else:
    print('  ❌ Some checks failed — review errors above')
    sys.exit(1)
"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "NEXT STEPS:"
echo "  1. Start the Voxtral TTS server:"
echo "       bash /mnt/c/VoiceForge/scripts/start_voxtral.sh"
echo ""
echo "  2. On first run, Voxtral-4B-TTS-2603 (~8GB) will download"
echo "     from HuggingFace — takes 10-20 minutes on first start."
echo ""
echo "  3. Once you see 'Uvicorn running on http://0.0.0.0:8091',"
echo "     Voxtral is ready. Switch to VOICEFORGE_PHASE=2 and"
echo "     select Hindi in the VoiceForge frontend."
echo ""

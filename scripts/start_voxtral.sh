#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# VoiceForge — Start Voxtral TTS Server
# ═══════════════════════════════════════════════════════════════
#
# Starts Mistral's Voxtral-4B-TTS-2603 via vLLM-Omni inside WSL2.
# The server listens on port 8091, which WSL2 bridges to Windows
# automatically — VoiceForge backend calls http://localhost:8091.
#
# Usage (from inside WSL2 on TRIJYA-7):
#   bash /mnt/c/VoiceForge/scripts/start_voxtral.sh
#
# Or as a background service:
#   nohup bash /mnt/c/VoiceForge/scripts/start_voxtral.sh \
#     > /tmp/voxtral.log 2>&1 &
#   tail -f /tmp/voxtral.log
#
# Prerequisites:
#   - Run setup_voxtral_wsl2.sh first (installs vLLM-Omni)
#   - WSL2 with Ubuntu running on TRIJYA-7
#   - RTX 4090 with at least 16GB free VRAM
#
# First run note:
#   The model (~8GB) is downloaded from HuggingFace on first start.
#   Subsequent starts load from ~/.cache/huggingface/ in ~30 seconds.
#
# Stopping:
#   Press Ctrl+C in this terminal to gracefully shut down.
# ═══════════════════════════════════════════════════════════════

echo ""
echo "╔═══════════════════════════════════════════════════════╗"
echo "║   VoiceForge — Voxtral TTS Server                     ║"
echo "║   Model : mistralai/Voxtral-4B-TTS-2603               ║"
echo "║   Port  : 8091                                        ║"
echo "║   VRAM  : ~16GB (RTX 4090 has 24GB — fits)           ║"
echo "╚═══════════════════════════════════════════════════════╝"
echo ""
echo "Starting vLLM-Omni..."
echo "If first run: model download may take 10-20 minutes (~8GB)"
echo "Subsequent starts: model loads in ~30 seconds from cache"
echo ""
echo "Server will be ready when you see:"
echo "  'Uvicorn running on http://0.0.0.0:8091'"
echo ""
echo "Press Ctrl+C to stop the server."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ── Preflight checks ──────────────────────────────────────────
# Verify vllm is installed before attempting to serve
if ! python3 -c "import vllm" 2>/dev/null; then
    echo "ERROR: vLLM is not installed in WSL2."
    echo "Run setup first: bash /mnt/c/VoiceForge/scripts/setup_voxtral_wsl2.sh"
    exit 1
fi

# Check CUDA availability
CUDA_OK=$(python3 -c "import torch; print(int(torch.cuda.is_available()))" 2>/dev/null || echo "0")
if [ "$CUDA_OK" != "1" ]; then
    echo "WARNING: CUDA not detected from WSL2."
    echo "Voxtral will attempt CPU inference — this will be very slow."
    echo "For GPU inference: ensure Windows driver >= 535.x is installed."
    echo ""
fi

# ── Check if port 8091 is already in use ─────────────────────
if nc -z localhost 8091 2>/dev/null; then
    echo "WARNING: Port 8091 is already in use."
    echo "Voxtral may already be running. Check with: ps aux | grep vllm"
    echo "To stop existing server: pkill -f 'vllm serve'"
    echo ""
fi

# ── Start vLLM-Omni serving Voxtral TTS ──────────────────────
#
# Flags explained:
#   --stage-configs-path  : Voxtral-specific stage configuration for vLLM-Omni
#   --omni                : Enable Omni multi-modal mode (required for TTS)
#   --port 8091           : Bind to port 8091 (VOXTRAL_PORT in VoiceForge config)
#   --trust-remote-code   : Required for Mistral model custom code
#   --enforce-eager       : Disable CUDA graph capture (more stable, slightly slower)
#   --gpu-memory-utilization 0.7 : Use 70% of VRAM (~16.8GB of 24GB)
#                                  Leaves headroom for XTTS v2 if needed
#   --max-model-len 4096  : Maximum token context window
#   --dtype bfloat16      : BF16 precision — best for RTX 4090 Ampere architecture
#

exec vllm serve mistralai/Voxtral-4B-TTS-2603 \
    --stage-configs-path vllm_omni/model_executor/stage_configs/voxtral_tts.yaml \
    --omni \
    --port 8091 \
    --host 0.0.0.0 \
    --trust-remote-code \
    --enforce-eager \
    --gpu-memory-utilization 0.7 \
    --max-model-len 4096 \
    --dtype bfloat16

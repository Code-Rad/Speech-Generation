#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# VoiceForge — Start Fish S2 Pro Server
# ═══════════════════════════════════════════════════════════════
#
# Starts Fish Speech S2 Pro inside WSL2 on TRIJYA-7.
# Server listens on port 8092. WSL2 bridges this port to Windows
# automatically — VoiceForge backend calls http://localhost:8092.
#
# Usage (from inside WSL2 on TRIJYA-7):
#   bash /mnt/c/VoiceForge/scripts/start_fish.sh
#
# Background / log to file:
#   nohup bash /mnt/c/VoiceForge/scripts/start_fish.sh \
#     > /tmp/fish.log 2>&1 &
#   tail -f /tmp/fish.log
#
# Prerequisites:
#   - Run setup_fish_wsl2.sh first (installs fish-speech + downloads model)
#   - WSL2 with Ubuntu running on TRIJYA-7
#   - RTX 4090 with at least 12GB free VRAM
#
# Co-existence with Voxtral:
#   Both servers use --gpu-memory-utilization 0.5 (12GB each).
#   They fit together on the RTX 4090 (24GB total VRAM).
#   Start Voxtral FIRST, then Fish. Each loads into the remaining VRAM.
#
# Stopping:
#   Press Ctrl+C to gracefully shut down.
# ═══════════════════════════════════════════════════════════════

echo ""
echo "╔═══════════════════════════════════════════════════════╗"
echo "║   VoiceForge — Fish S2 Pro Server                     ║"
echo "║   Model : fishaudio/s2-pro                            ║"
echo "║   Port  : 8092                                        ║"
echo "║   VRAM  : ~12GB (RTX 4090 has 24GB — fits)           ║"
echo "╚═══════════════════════════════════════════════════════╝"
echo ""
echo "Starting fish-speech API server..."
echo "Model loads in ~30 seconds after startup."
echo ""
echo "Server ready when you see:"
echo "  'Uvicorn running on http://0.0.0.0:8092'"
echo ""
echo "Press Ctrl+C to stop."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ── Preflight checks ──────────────────────────────────────────
if ! python3 -c "import fish_speech" 2>/dev/null; then
    echo "ERROR: fish-speech is not installed in WSL2."
    echo "Run setup first: bash /mnt/c/VoiceForge/scripts/setup_fish_wsl2.sh"
    exit 1
fi

MODEL_PATH="$HOME/.cache/fish_s2_pro"
if [ ! -d "$MODEL_PATH" ] || [ -z "$(ls -A "$MODEL_PATH" 2>/dev/null)" ]; then
    echo "ERROR: Fish S2 Pro model not found at $MODEL_PATH"
    echo "Run setup first: bash /mnt/c/VoiceForge/scripts/setup_fish_wsl2.sh"
    exit 1
fi

# Check CUDA
CUDA_OK=$(python3 -c "import torch; print(int(torch.cuda.is_available()))" 2>/dev/null || echo "0")
if [ "$CUDA_OK" != "1" ]; then
    echo "WARNING: CUDA not detected from WSL2. Inference will be slow on CPU."
    echo ""
fi

# Check if port 8092 is already in use
if nc -z localhost 8092 2>/dev/null; then
    echo "WARNING: Port 8092 is already in use."
    echo "Fish S2 Pro may already be running. Check: ps aux | grep fish_speech"
    echo "To stop: pkill -f fish_speech"
    echo ""
fi

echo "Starting fish-speech API server..."
echo "Model path: $MODEL_PATH"
echo ""

# ── Start fish-speech API server ──────────────────────────────
#
# Flags explained:
#   --listen 0.0.0.0:8092     : Bind to all interfaces on port 8092
#                                WSL2 forwards this to Windows localhost:8092
#   --model-path               : Path to downloaded fishaudio/s2-pro weights
#   --compile                  : Enable torch.compile() for faster inference
#                                (takes ~2 min on first request, then fast)
#   --half                     : FP16 precision — faster on RTX 4090
#   --num-workers 1            : One inference worker (RTX 4090 is single-GPU)
#
# GPU memory note:
#   fish-speech uses its own memory management — no explicit utilization flag.
#   At FP16, model weights ≈ 8.8GB. Total with KV cache ≈ 12-14GB.
#   Leaves ~10-12GB for Voxtral on the 24GB RTX 4090.
#

exec python3 -m fish_speech.api_server \
    --listen 0.0.0.0:8092 \
    --model-path "$MODEL_PATH" \
    --compile \
    --half \
    --num-workers 1

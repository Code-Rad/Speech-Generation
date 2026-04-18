"""
test_engines.py
VoiceForge — Quick Engine Availability Checker

Connects to the running VoiceForge server and displays a formatted
table of all 4 TTS engines, their current availability, cloning
support, and supported languages.

Usage:
    python scripts/test_engines.py
    (run from C:\\VoiceForge\\ or C:\\VoiceForge\\server\\)

Requirements:
    pip install requests
    Server must be running: uvicorn main:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import sys

BASE_URL = "http://localhost:8000"

try:
    import requests
except ImportError:
    print("ERROR: 'requests' not installed.  Run: pip install requests")
    sys.exit(1)

# Force UTF-8 output on Windows so table characters render correctly
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    import io as _io
    sys.stdout = _io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = _io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ── Status icons ──────────────────────────────────────────────────────────────
_ICONS = {
    "available":   "✅ available  ",
    "unavailable": "⚠️  unavailable",
    "not_built":   "🔲 not_built  ",
    "error":       "❌ error      ",
}


def _fmt_bool(val) -> str:
    if val is True:
        return "✓ yes"
    if val is False:
        return "✗ no "
    return "--   "


def _fmt_langs(langs: list) -> str:
    if not langs:
        return "--"
    return ", ".join(langs)


def main() -> None:
    print()
    print("=" * 60)
    print("  VoiceForge -- Engine Quick-Check")
    print("=" * 60)

    # ── 1. Server health check ─────────────────────────────────────────────────
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=5)
        h = r.json()
        print(f"\n  Server:  HTTP {r.status_code}  |  status={h.get('status')}  "
              f"|  phase={h.get('phase')}  |  version={h.get('version')}")
        print(f"  Uptime:  {h.get('uptime_seconds', 0):.0f}s  |  "
              f"started: {h.get('started_at', '?')[:19]}")
    except requests.ConnectionError:
        print(f"\n  ERROR: Cannot connect to {BASE_URL}")
        print("  Start the server first:")
        print("    cd C:\\VoiceForge\\server")
        print("    uvicorn main:app --host 0.0.0.0 --port 8000 --reload")
        sys.exit(1)

    # ── 2. Engine status ───────────────────────────────────────────────────────
    try:
        r = requests.get(f"{BASE_URL}/engines", timeout=10)
        engines = r.json()
    except Exception as exc:
        print(f"\n  ERROR: /engines endpoint failed: {exc}")
        sys.exit(1)

    by_type = {e.get("engine_type", ""): e for e in engines}

    engine_order = [
        ("edge_tts",    "edge_tts       "),
        ("xtts_v2",     "xtts_v2        "),
        ("voxtral_tts", "voxtral_tts    "),
        ("fish_s2_pro", "fish_s2_pro    "),
    ]

    print()
    print(f"  {'ENGINE':<16}  {'STATUS':<16}  {'CLONING':<8}  LANGUAGES")
    print("  " + "-" * 58)

    for engine_key, display_name in engine_order:
        e = by_type.get(engine_key, {})
        status_raw = e.get("status", "unknown")
        icon = _ICONS.get(status_raw, f"? {status_raw:<12}")
        cloning = _fmt_bool(e.get("supports_cloning"))
        langs = _fmt_langs(e.get("supported_languages", []))
        print(f"  {display_name}  {icon}  {cloning}   {langs}")

    # ── 3. Phase summary ───────────────────────────────────────────────────────
    phase = h.get("phase", 1)
    print()
    print("  " + "-" * 58)
    if phase == 1:
        print("  PHASE 1 ACTIVE -- Windows-native engines only")
        print()
        print("  ACTIVE ROUTING CHAIN (all languages):")
        print("    xtts_v2 -> edge_tts  (emergency fallback)")
        print()
        edge_ok = by_type.get("edge_tts", {}).get("status") == "available"
        xtts_ok = by_type.get("xtts_v2",  {}).get("status") == "available"
        print("  CURRENT AVAILABILITY:")
        print(f"    edge_tts:  {'AVAILABLE (draft quality)' if edge_ok else 'UNAVAILABLE'}")
        print(f"    xtts_v2:   {'AVAILABLE (broadcast quality)' if xtts_ok else 'UNAVAILABLE -- model not downloaded'}")
        if not xtts_ok:
            print()
            print("  TO ACTIVATE XTTS v2 (broadcast quality voice cloning):")
            print("    cd C:\\VoiceForge\\server")
            print("    python -c \"from TTS.api import TTS; TTS('tts_models/multilingual/multi-dataset/xtts_v2')\"")
    else:
        print("  PHASE 2 ACTIVE -- All 4 engines configured")
        for ename, display in engine_order:
            e = by_type.get(ename, {})
            print(f"    {display.strip():<16}: {e.get('status', 'unknown')}")

    # ── 4. Phase 2 preview ────────────────────────────────────────────────────
    print()
    print("  " + "-" * 58)
    print("  PHASE 2 ENGINES (activated in P12 / P13):")
    print("    voxtral_tts  -- Best Hindi/Hinglish quality")
    print("                    vLLM-Omni in WSL2 on TRIJYA-7 (port 8091)")
    print("    fish_s2_pro  -- Best English quality")
    print("                    SGLang in WSL2 on TRIJYA-7 (port 8092)")
    print()
    print("  Run the full integration test suite:")
    print("    cd C:\\VoiceForge")
    print("    python scripts/test_phase1_backend.py")
    print()


if __name__ == "__main__":
    main()

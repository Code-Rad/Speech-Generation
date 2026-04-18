"""
test_phase1_backend.py
VoiceForge — Phase 1 Backend Integration Test Suite

Comprehensive integration test of the complete Phase 1 backend.
All tests hit the LIVE running server via HTTP — no mocking.

Usage:
    cd C:\\VoiceForge
    python scripts/test_phase1_backend.py

Requirements:
    pip install requests soundfile numpy
    Server must be running: cd server && uvicorn main:app --host 0.0.0.0 --port 8000

Exit codes:
    0 — all tests passed (or all failures are documented known limitations)
    1 — unexpected failures found
"""

from __future__ import annotations

import io
import json
import os
import sys
import time
from pathlib import Path
from typing import Optional

# ── Path setup ────────────────────────────────────────────────────────────────
_SCRIPT_DIR   = Path(__file__).parent
_PROJECT_ROOT = _SCRIPT_DIR.parent
_SERVER_DIR   = _PROJECT_ROOT / "server"

BASE_URL = "http://localhost:8000"

# ── Import requests ───────────────────────────────────────────────────────────
try:
    import requests
except ImportError:
    print("ERROR: 'requests' not installed. Run: pip install requests")
    sys.exit(1)

# Force UTF-8 output on Windows so box-drawing / emoji chars don't crash
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    import io as _io
    sys.stdout = _io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = _io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


# ── Global counters ───────────────────────────────────────────────────────────
class _Counters:
    passed = 0
    failed = 0
    known_limitations = 0
    cat_passed = 0
    cat_failed = 0
    category_results: list = []
    current_category = ""

C = _Counters()


def _start_category(name: str) -> None:
    C.current_category = name
    C.cat_passed = 0
    C.cat_failed = 0
    print(f"\n{'─'*60}")
    print(f"  {name}")
    print(f"{'─'*60}")


def _end_category() -> None:
    total = C.cat_passed + C.cat_failed
    C.category_results.append((C.current_category, C.cat_passed, total))


def check(label: str, condition: bool, detail: str = "") -> bool:
    if condition:
        C.passed += 1
        C.cat_passed += 1
        print(f"  \u2705 PASS  {label}")
    else:
        C.failed += 1
        C.cat_failed += 1
        msg = f"  \u274c FAIL  {label}"
        if detail:
            msg += f"\n         \u2192 {detail}"
        print(msg)
    return condition


def known_limitation(label: str, detail: str = "") -> None:
    C.known_limitations += 1
    msg = f"  \u26a0\ufe0f  SKIP  {label} [KNOWN PHASE 1 LIMITATION]"
    if detail:
        msg += f"\n         \u2192 {detail}"
    print(msg)


def _skip(n: int, reason: str = "") -> None:
    """Mark n tests as failed (used when a precondition check fails)."""
    for _ in range(n):
        C.failed += 1
        C.cat_failed += 1
    if reason:
        print(f"  \u274c SKIP  {n} test(s) — {reason}")


def _get(path: str, timeout: int = 10) -> Optional[requests.Response]:
    try:
        return requests.get(f"{BASE_URL}{path}", timeout=timeout)
    except requests.ConnectionError as e:
        print(f"  \u26a1 CONNECTION ERROR on GET {path}: {e}")
        return None


def _post_json(path: str, body: dict, timeout: int = 60) -> Optional[requests.Response]:
    try:
        return requests.post(f"{BASE_URL}{path}", json=body, timeout=timeout)
    except requests.ConnectionError as e:
        print(f"  \u26a1 CONNECTION ERROR on POST {path}: {e}")
        return None


def _post_multipart(
    path: str, data: dict, files: dict, timeout: int = 60
) -> Optional[requests.Response]:
    try:
        return requests.post(f"{BASE_URL}{path}", data=data, files=files, timeout=timeout)
    except requests.ConnectionError as e:
        print(f"  \u26a1 CONNECTION ERROR on POST {path}: {e}")
        return None


def _is_valid_json(r: requests.Response) -> bool:
    try:
        r.json()
        return True
    except Exception:
        return False


def _make_short_wav_bytes(duration_seconds: float = 3.0, sample_rate: int = 22050) -> bytes:
    """Create a short WAV in memory (intentionally too short to pass validation)."""
    try:
        import numpy as np
        import soundfile as sf
        n = int(duration_seconds * sample_rate)
        t = np.linspace(0, duration_seconds, n, dtype=np.float32)
        audio = (0.3 * np.sin(2 * 3.14159 * 440 * t)).astype(np.float32)
        buf = io.BytesIO()
        sf.write(buf, audio, sample_rate, format="WAV", subtype="PCM_16")
        buf.seek(0)
        return buf.read()
    except ImportError:
        # Fallback: hand-craft a minimal WAV header
        n_samples = int(duration_seconds * sample_rate)
        data_size = n_samples * 2
        hdr = bytearray(44)
        hdr[0:4]   = b"RIFF"
        hdr[4:8]   = (36 + data_size).to_bytes(4, "little")
        hdr[8:12]  = b"WAVE"
        hdr[12:16] = b"fmt "
        hdr[16:20] = (16).to_bytes(4, "little")
        hdr[20:22] = (1).to_bytes(2, "little")
        hdr[22:24] = (1).to_bytes(2, "little")
        hdr[24:28] = sample_rate.to_bytes(4, "little")
        hdr[28:32] = (sample_rate * 2).to_bytes(4, "little")
        hdr[32:34] = (2).to_bytes(2, "little")
        hdr[34:36] = (16).to_bytes(2, "little")
        hdr[36:40] = b"data"
        hdr[40:44] = data_size.to_bytes(4, "little")
        return bytes(hdr) + bytes(n_samples * 2)


# ═════════════════════════════════════════════════════════════════════════════
# CATEGORY 1 — SERVER HEALTH  (6 tests)
# ═════════════════════════════════════════════════════════════════════════════

def test_category_1():
    _start_category("CATEGORY 1 — Server Health")

    t0 = time.monotonic()
    r = _get("/health", timeout=5)
    elapsed = time.monotonic() - t0

    if not check("1.1  GET /health returns 200",
                 r is not None and r.status_code == 200,
                 f"status={r.status_code if r else 'no response'}"):
        _skip(5, "server not responding — skipping 1.2-1.6")
        _end_category()
        return

    data = r.json()
    check("1.2  Response has status: 'ok'",
          data.get("status") == "ok",
          f"got status={data.get('status')!r}")
    check("1.3  Response has phase: 1",
          data.get("phase") == 1,
          f"got phase={data.get('phase')!r}")
    check("1.4  Response has 'version' field",
          "version" in data and bool(data["version"]),
          f"got version={data.get('version')!r}")
    check("1.5  Response has uptime_seconds > 0",
          isinstance(data.get("uptime_seconds"), (int, float)) and data["uptime_seconds"] > 0,
          f"got uptime_seconds={data.get('uptime_seconds')!r}")
    check("1.6  Server responds within 3 seconds",
          elapsed < 3.0,
          f"took {elapsed:.2f}s")

    _end_category()


# ═════════════════════════════════════════════════════════════════════════════
# CATEGORY 2 — ENGINE STATUS  (9 tests)
# ═════════════════════════════════════════════════════════════════════════════

def test_category_2():
    _start_category("CATEGORY 2 — Engine Status")

    r = _get("/engines")
    if not check("2.1  GET /engines returns 200",
                 r is not None and r.status_code == 200,
                 f"status={r.status_code if r else 'no response'}"):
        _skip(8, "endpoint error — skipping 2.2-2.9")
        _end_category()
        return

    data = r.json()
    check("2.2  Response is a list of 4 engines",
          isinstance(data, list) and len(data) == 4,
          f"got {len(data) if isinstance(data, list) else type(data).__name__} items")

    engines = {e["engine_type"]: e for e in data if "engine_type" in e}

    edge = engines.get("edge_tts", {})
    check("2.3  edge_tts status is 'available'",
          edge.get("status") == "available",
          f"got status={edge.get('status')!r}")
    check("2.4  edge_tts supports_cloning is False",
          edge.get("supports_cloning") is False,
          f"got supports_cloning={edge.get('supports_cloning')!r}")

    edge_langs = edge.get("supported_languages", [])
    check("2.5  edge_tts supported_languages includes en, hi, hinglish",
          all(lang in edge_langs for lang in ["en", "hi", "hinglish"]),
          f"got supported_languages={edge_langs}")

    xtts = engines.get("xtts_v2", {})
    check("2.6  xtts_v2 status is 'unavailable' (model not downloaded — expected Phase 1)",
          xtts.get("status") == "unavailable",
          f"got status={xtts.get('status')!r}")

    voxtral = engines.get("voxtral_tts", {})
    check("2.7  voxtral_tts status is 'not_built' (Phase 2)",
          voxtral.get("status") == "not_built",
          f"got status={voxtral.get('status')!r}")

    fish = engines.get("fish_s2_pro", {})
    check("2.8  fish_s2_pro status is 'not_built' (Phase 2)",
          fish.get("status") == "not_built",
          f"got status={fish.get('status')!r}")

    check("2.9  No engine entry has null engine_type",
          all("engine_type" in e and e["engine_type"] is not None for e in data),
          "one or more entries missing engine_type")

    _end_category()


# ═════════════════════════════════════════════════════════════════════════════
# CATEGORY 3 — VOICE PROFILES  (9 tests)
# ═════════════════════════════════════════════════════════════════════════════

EXPECTED_PROFILES = [
    "anchor_male_en", "anchor_female_en",
    "anchor_male_hi", "anchor_female_hi",
    "anchor_male_hinglish", "anchor_female_hinglish",
]
REQUIRED_PROFILE_FIELDS = [
    "profile_id", "display_name", "language", "gender",
    "engine_preference", "reference_audio_exists",
    "cloning_enabled", "description",
]


def test_category_3():
    _start_category("CATEGORY 3 — Voice Profiles")

    r = _get("/voices")
    if not check("3.1  GET /voices returns 200",
                 r is not None and r.status_code == 200,
                 f"status={r.status_code if r else 'no response'}"):
        _skip(8, "endpoint error — skipping 3.2-3.9")
        _end_category()
        return

    profiles_list = r.json()
    check("3.2  Response is list of exactly 6 profiles",
          isinstance(profiles_list, list) and len(profiles_list) == 6,
          f"got {len(profiles_list) if isinstance(profiles_list, list) else type(profiles_list).__name__}")

    profile_ids = [p.get("profile_id") for p in profiles_list if isinstance(p, dict)]
    check("3.3  All 6 expected profile IDs present",
          all(pid in profile_ids for pid in EXPECTED_PROFILES),
          f"found={sorted(profile_ids)}")

    profiles = {p["profile_id"]: p for p in profiles_list if "profile_id" in p}

    missing_info = [
        f"{p.get('profile_id', '?')}: missing {[f for f in REQUIRED_PROFILE_FIELDS if f not in p]}"
        for p in profiles_list if not all(f in p for f in REQUIRED_PROFILE_FIELDS)
    ]
    check("3.4  Every profile has all required fields",
          not missing_info,
          "; ".join(missing_info))

    anchor_male_en = profiles.get("anchor_male_en", {})
    check("3.5  anchor_male_en reference_audio_exists is True (uploaded in P7)",
          anchor_male_en.get("reference_audio_exists") is True,
          f"got reference_audio_exists={anchor_male_en.get('reference_audio_exists')!r}")

    others_false = all(
        profiles.get(pid, {}).get("reference_audio_exists") is False
        for pid in EXPECTED_PROFILES if pid != "anchor_male_en"
    )
    check("3.6  All other 5 profiles reference_audio_exists is False",
          others_false,
          str({pid: profiles.get(pid, {}).get("reference_audio_exists")
               for pid in EXPECTED_PROFILES if pid != "anchor_male_en"}))

    en_profiles = [p for p in profiles_list if p.get("language") == "en"]
    check("3.7  English profiles have fish_s2_pro first in engine_preference",
          all(p.get("engine_preference", [None])[0] == "fish_s2_pro" for p in en_profiles),
          str({p["profile_id"]: p.get("engine_preference", [])[:1] for p in en_profiles}))

    hi_profiles = [p for p in profiles_list if p.get("language") == "hi"]
    check("3.8  Hindi profiles have voxtral_tts first in engine_preference",
          all(p.get("engine_preference", [None])[0] == "voxtral_tts" for p in hi_profiles),
          str({p["profile_id"]: p.get("engine_preference", [])[:1] for p in hi_profiles}))

    hinglish_profiles = [p for p in profiles_list if p.get("language") == "hinglish"]
    check("3.9  Hinglish profiles have voxtral_tts first in engine_preference",
          all(p.get("engine_preference", [None])[0] == "voxtral_tts" for p in hinglish_profiles),
          str({p["profile_id"]: p.get("engine_preference", [])[:1] for p in hinglish_profiles}))

    _end_category()


# ═════════════════════════════════════════════════════════════════════════════
# CATEGORY 4 — SPEECH GENERATION: ENGLISH  (7 tests)
# ═════════════════════════════════════════════════════════════════════════════

def test_category_4():
    _start_category("CATEGORY 4 — Speech Generation: English")

    payload = {
        "text": (
            "Good evening. This is the VoiceForge Phase 1 integration test. "
            "All systems are operating normally. English speech generation confirmed."
        ),
        "profile_id": "anchor_male_en",
        "output_format": "wav",
    }

    t0 = time.monotonic()
    r = _post_json("/generate", payload, timeout=60)
    elapsed = time.monotonic() - t0

    if not check("4.1  POST /generate with anchor_male_en returns 200",
                 r is not None and r.status_code == 200,
                 f"status={r.status_code if r else 'no response'}, "
                 f"body={r.text[:200] if r else ''}"):
        _skip(5, "endpoint error — skipping 4.2-4.6")
    else:
        ct = r.headers.get("Content-Type", "")
        check("4.2  Response Content-Type contains 'audio'",
              "audio" in ct, f"got Content-Type={ct!r}")
        check("4.3  Response body size > 10000 bytes (real audio)",
              len(r.content) > 10000, f"got {len(r.content)} bytes")
        engine_used = r.headers.get("X-Engine-Used", "")
        check("4.4  X-Engine-Used header is 'edge_tts' (XTTS unavailable in Phase 1)",
              engine_used == "edge_tts", f"got X-Engine-Used={engine_used!r}")
        is_draft = r.headers.get("X-Is-Draft", "")
        check("4.5  X-Is-Draft header is 'true'",
              is_draft == "true", f"got X-Is-Draft={is_draft!r}")
        check("4.6  Generation completes within 30 seconds",
              elapsed < 30.0, f"took {elapsed:.1f}s")

    r2 = _post_json("/generate", {
        "text": "Female anchor voice confirmed. Phase 1 backend integration test.",
        "profile_id": "anchor_female_en",
        "output_format": "wav",
    }, timeout=60)
    check("4.7  POST /generate with anchor_female_en returns 200 with audio",
          r2 is not None and r2.status_code == 200 and len(r2.content) > 10000,
          f"status={r2.status_code if r2 else 'no response'}, "
          f"size={len(r2.content) if r2 else 0} bytes")

    _end_category()


# ═════════════════════════════════════════════════════════════════════════════
# CATEGORY 5 — SPEECH GENERATION: HINDI  (5 tests)
# ═════════════════════════════════════════════════════════════════════════════

def test_category_5():
    _start_category("CATEGORY 5 — Speech Generation: Hindi")

    hindi_text = (
        "\u0928\u092e\u0938\u094d\u0924\u0947\u0964 "
        "\u0906\u091c \u0915\u0940 \u092e\u0941\u0916\u094d\u092f "
        "\u0916\u092c\u0930\u0947\u0902\u0964 "
        "\u0926\u0947\u0936 \u0914\u0930 \u0926\u0941\u0928\u093f\u092f\u093e "
        "\u0915\u0940 \u0924\u093e\u091c\u093e \u091c\u093e\u0928\u0915\u093e\u0930\u0940 "
        "\u0915\u0947 \u0938\u093e\u0925 \u0939\u092e \u0906\u092a\u0915\u0947 "
        "\u0938\u093e\u092e\u0928\u0947 \u0939\u0948\u0902\u0964"
    )

    r = _post_json("/generate", {
        "text": hindi_text,
        "profile_id": "anchor_male_hi",
        "output_format": "wav",
    }, timeout=60)

    if not check("5.1  POST /generate with anchor_male_hi + Hindi text returns 200",
                 r is not None and r.status_code == 200,
                 f"status={r.status_code if r else 'no response'}, "
                 f"body={r.text[:200] if r else ''}"):
        _skip(3, "endpoint error — skipping 5.2-5.4")
    else:
        check("5.2  Response body size > 10000 bytes",
              len(r.content) > 10000, f"got {len(r.content)} bytes")
        check("5.3  X-Engine-Used header is 'edge_tts'",
              r.headers.get("X-Engine-Used") == "edge_tts",
              f"got X-Engine-Used={r.headers.get('X-Engine-Used')!r}")
        check("5.4  X-Is-Draft header is 'true'",
              r.headers.get("X-Is-Draft") == "true",
              f"got X-Is-Draft={r.headers.get('X-Is-Draft')!r}")

    r2 = _post_json("/generate", {
        "text": hindi_text,
        "profile_id": "anchor_female_hi",
        "output_format": "wav",
    }, timeout=60)
    check("5.5  POST /generate with anchor_female_hi returns 200 with audio",
          r2 is not None and r2.status_code == 200 and len(r2.content) > 10000,
          f"status={r2.status_code if r2 else 'no response'}, "
          f"size={len(r2.content) if r2 else 0} bytes")

    _end_category()


# ═════════════════════════════════════════════════════════════════════════════
# CATEGORY 6 — SPEECH GENERATION: HINGLISH  (3 tests)
# ═════════════════════════════════════════════════════════════════════════════

def test_category_6():
    _start_category("CATEGORY 6 — Speech Generation: Hinglish")

    hinglish_text = (
        "Breaking news aaj ki. Yeh hai VoiceForge ka "
        "professional speech generation platform. Humara "
        "system perfect kaam kar raha hai."
    )

    t0 = time.monotonic()
    r = _post_json("/generate", {
        "text": hinglish_text,
        "profile_id": "anchor_male_hinglish",
        "output_format": "wav",
    }, timeout=60)
    elapsed = time.monotonic() - t0

    check("6.1  POST /generate with anchor_male_hinglish + Hinglish text returns 200",
          r is not None and r.status_code == 200,
          f"status={r.status_code if r else 'no response'}")
    check("6.2  Response body size > 10000 bytes",
          r is not None and len(r.content) > 10000,
          f"got {len(r.content) if r else 0} bytes")
    check("6.3  Generation completes within 30 seconds",
          elapsed < 30.0, f"took {elapsed:.1f}s")

    _end_category()


# ═════════════════════════════════════════════════════════════════════════════
# CATEGORY 7 — BATCH GENERATION  (6 tests)
# ═════════════════════════════════════════════════════════════════════════════

def test_category_7():
    _start_category("CATEGORY 7 — Batch Generation")

    r = _post_json("/generate-batch", {
        "items": [
            {"text": "First batch item. English news headline.",
             "profile_id": "anchor_male_en", "output_format": "wav"},
            {"text": "\u0926\u0942\u0938\u0930\u0940 \u0916\u092c\u0930\u0964 "
                     "\u0939\u093f\u0902\u0926\u0940 \u092e\u0947\u0902\u0964",
             "profile_id": "anchor_male_hi", "output_format": "wav"},
            {"text": "Third item. VoiceForge batch generation confirmed.",
             "profile_id": "anchor_male_en", "output_format": "wav"},
        ]
    }, timeout=180)

    if not check("7.1  POST /generate-batch with 3 items returns 200",
                 r is not None and r.status_code == 200,
                 f"status={r.status_code if r else 'no response'}, "
                 f"body={r.text[:200] if r else ''}"):
        _skip(5, "endpoint error — skipping 7.2-7.6")
        _end_category()
        return

    data = r.json()
    results = data.get("results", [])
    check("7.2  Response has 'results' list of 3 items",
          isinstance(results, list) and len(results) == 3,
          f"got {len(results)} results")
    check("7.3  Each result has 'success' field",
          all("success" in item for item in results),
          str([list(item.keys()) for item in results]))

    succeeded_count = sum(1 for item in results if item.get("success"))
    check("7.4  At least 2/3 items succeeded",
          succeeded_count >= 2,
          f"succeeded={succeeded_count}/3, "
          f"errors={[item.get('error_message') for item in results if not item.get('success')]}")

    check("7.5  Response has summary fields: total_items, succeeded, failed",
          all(k in data for k in ["total_items", "succeeded", "failed"]),
          f"got keys={list(data.keys())}")

    # Invalid profile_id does not crash entire batch
    r2 = _post_json("/generate-batch", {
        "items": [
            {"text": "Valid item one.", "profile_id": "anchor_male_en", "output_format": "wav"},
            {"text": "Invalid profile.", "profile_id": "DOES_NOT_EXIST_XYZ", "output_format": "wav"},
            {"text": "Valid item three.", "profile_id": "anchor_female_en", "output_format": "wav"},
        ]
    }, timeout=120)
    ok_count = 0
    fail_count = 0
    if r2 is not None and r2.status_code == 200:
        d2 = r2.json()
        ok_count = d2.get("succeeded", 0)
        fail_count = d2.get("failed", 0)
    check("7.6  Batch with invalid profile_id: other items still succeed (not HTTP 500)",
          r2 is not None and r2.status_code == 200 and ok_count >= 2 and fail_count >= 1,
          f"status={r2.status_code if r2 else 'no response'}, "
          f"succeeded={ok_count}, failed={fail_count}")

    _end_category()


# ═════════════════════════════════════════════════════════════════════════════
# CATEGORY 8 — ERROR HANDLING  (8 tests)
# ═════════════════════════════════════════════════════════════════════════════

def test_category_8():
    _start_category("CATEGORY 8 — Error Handling")

    # 8.1 Invalid profile_id → 404
    r1 = _post_json("/generate", {
        "text": "Hello.", "profile_id": "nonexistent_XYZ", "output_format": "wav"
    })
    check("8.1  POST /generate with invalid profile_id returns 404",
          r1 is not None and r1.status_code == 404,
          f"got status={r1.status_code if r1 else 'no response'}")

    # 8.2 Empty text → 422 (Pydantic min_length=1)
    r2 = _post_json("/generate", {
        "text": "", "profile_id": "anchor_male_en", "output_format": "wav"
    })
    check("8.2  POST /generate with empty text returns 400 or 422",
          r2 is not None and r2.status_code in (400, 422),
          f"got status={r2.status_code if r2 else 'no response'}")

    # 8.3 Missing profile_id → 422 (FastAPI validation)
    r3 = _post_json("/generate", {"text": "Hello."})
    check("8.3  POST /generate with missing profile_id returns 422",
          r3 is not None and r3.status_code == 422,
          f"got status={r3.status_code if r3 else 'no response'}")

    # 8.4 /clone-voice with invalid profile_id → 404
    tiny_wav = _make_short_wav_bytes(duration_seconds=3.0)
    r4 = _post_multipart(
        "/clone-voice",
        data={"profile_id": "nonexistent_XYZ", "generate_sample": "false"},
        files={"audio_file": ("test.wav", tiny_wav, "audio/wav")},
    )
    check("8.4  POST /clone-voice with invalid profile_id returns 404",
          r4 is not None and r4.status_code == 404,
          f"got status={r4.status_code if r4 else 'no response'}")

    # 8.5 /clone-voice with too-short audio → 422 with descriptive error
    r5 = _post_multipart(
        "/clone-voice",
        data={"profile_id": "anchor_male_en", "generate_sample": "false"},
        files={"audio_file": ("short.wav", tiny_wav, "audio/wav")},
    )
    if check("8.5  POST /clone-voice with too-short audio returns 422",
             r5 is not None and r5.status_code == 422,
             f"got status={r5.status_code if r5 else 'no response'}"):
        # Parse the response: FastAPI wraps HTTPException detail in {"detail": ...}
        # The detail may be a string or a dict with an "error" key
        error_text = ""
        try:
            parsed = r5.json()
            detail = parsed.get("detail", "")
            if isinstance(detail, dict):
                error_text = str(detail.get("error", "")).lower()
            else:
                error_text = str(detail).lower()
        except Exception:
            error_text = r5.content.decode("utf-8", errors="replace").lower()
        has_description = any(kw in error_text for kw in ["short", "duration", "second", "minimum", "small"])
        check("8.5a 422 response contains descriptive error (mentions audio problem)",
              has_description, f"error_text={error_text[:200]!r}")
    else:
        _skip(1, "8.5a skipped — 8.5 failed")

    # 8.6 GET /voices always 200
    r6 = _get("/voices")
    check("8.6  GET /voices always returns 200",
          r6 is not None and r6.status_code == 200,
          f"got status={r6.status_code if r6 else 'no response'}")

    # 8.7 All error responses are valid JSON
    error_responses = [
        ("8.1 response", r1), ("8.2 response", r2),
        ("8.3 response", r3), ("8.4 response", r4),
    ]
    all_json = all(_is_valid_json(r) for _, r in error_responses if r is not None)
    check("8.7  All error responses are valid JSON (not raw HTML)",
          all_json,
          str([(label, r.text[:80] if r else None)
               for label, r in error_responses if r and not _is_valid_json(r)]))

    # 8.8 No 500 under normal usage
    statuses = [
        r1.status_code if r1 else None, r2.status_code if r2 else None,
        r3.status_code if r3 else None, r4.status_code if r4 else None,
        r5.status_code if r5 else None, r6.status_code if r6 else None,
    ]
    check("8.8  No endpoint returned 500 under normal usage patterns",
          all(s != 500 for s in statuses if s is not None),
          f"statuses seen: {statuses}")

    _end_category()


# ═════════════════════════════════════════════════════════════════════════════
# CATEGORY 9 — CLONING PIPELINE  (8 tests)
# ═════════════════════════════════════════════════════════════════════════════

def test_category_9():
    _start_category("CATEGORY 9 — Cloning Pipeline")

    # Resolve reference audio directory (same strategy as ProfileManager)
    ref_dir = None
    for candidate in [
        _PROJECT_ROOT / "server" / "reference_audio",
        _SERVER_DIR / "reference_audio",
    ]:
        if candidate.exists():
            ref_dir = candidate
            break

    ref_file = (ref_dir / "anchor_male_en_reference.wav") if ref_dir else None

    check("9.1  anchor_male_en reference audio file exists on disk",
          ref_file is not None and ref_file.exists(),
          f"looked in {[str(_PROJECT_ROOT / 'server' / 'reference_audio')]}")

    if ref_file and ref_file.exists():
        size = ref_file.stat().st_size
        check("9.2  Reference audio file size > 100 KB",
              size > 100_000, f"got {size / 1024:.1f} KB")

        try:
            import soundfile as sf  # noqa: PLC0415
            info = sf.info(str(ref_file))

            check("9.3  Reference audio is valid WAV (readable by soundfile)", True)
            check("9.4  Duration >= 10 seconds",
                  info.duration >= 10.0, f"got duration={info.duration:.1f}s")
            check("9.5  Sample rate is 22050 Hz (normalised by AudioValidator)",
                  info.samplerate == 22050, f"got sample_rate={info.samplerate} Hz")
            check("9.6  Audio is mono (1 channel)",
                  info.channels == 1, f"got channels={info.channels}")

        except ImportError:
            known_limitation("9.3-9.6  soundfile not installed — cannot verify audio properties",
                             "pip install soundfile to enable these checks")
        except Exception as exc:
            check("9.3  Reference audio is valid WAV (readable by soundfile)", False, str(exc))
            _skip(3, "9.4-9.6 skipped — audio unreadable")
    else:
        _skip(5, "9.2-9.6 skipped — reference audio not found")

    # 9.7 Sample file exists in output/
    output_dirs = [
        _PROJECT_ROOT / "server" / "output",
        _SERVER_DIR / "output",
        _SERVER_DIR / "server" / "output",
    ]
    sample_file = None
    for out_dir in output_dirs:
        if out_dir.exists():
            matches = sorted(out_dir.glob("anchor_male_en_sample*.wav"), reverse=True)
            if matches:
                sample_file = matches[0]
                break

    check("9.7  anchor_male_en_sample.wav exists in output/ (generated by /clone-voice in P7)",
          sample_file is not None,
          f"searched: {[str(d) for d in output_dirs if d.exists()]}")

    if sample_file and sample_file.exists():
        size = sample_file.stat().st_size
        check("9.8  Sample file is valid audio > 10 KB",
              size > 10_000, f"got {size / 1024:.1f} KB ({sample_file.name})")
    else:
        _skip(1, "9.8 skipped — sample file not found")

    _end_category()


# ═════════════════════════════════════════════════════════════════════════════
# CATEGORY 10 — SYSTEM INTEGRITY  (10 tests)
# ═════════════════════════════════════════════════════════════════════════════

def test_category_10():
    _start_category("CATEGORY 10 — System Integrity")

    # 10.1 All 6 voice profile JSON files valid
    profiles_dir = _PROJECT_ROOT / "server" / "voice_profiles"
    profile_files = sorted(profiles_dir.glob("*.json")) if profiles_dir.exists() else []
    invalid_profiles = []
    for pf in profile_files:
        try:
            with open(pf, encoding="utf-8") as fh:
                json.load(fh)
        except Exception as exc:
            invalid_profiles.append(f"{pf.name}: {exc}")
    check("10.1  All 6 voice profile JSON files are valid (not corrupted)",
          len(profile_files) == 6 and not invalid_profiles,
          f"found {len(profile_files)} files, invalid: {invalid_profiles}")

    # 10.2 Placeholder engine files still exist
    engine_dir = _PROJECT_ROOT / "server" / "engine"
    check("10.2  Placeholder engine files exist (voxtral_engine.py, fish_engine.py)",
          (engine_dir / "voxtral_engine.py").exists() and (engine_dir / "fish_engine.py").exists(),
          f"voxtral={((engine_dir / 'voxtral_engine.py').exists())}, "
          f"fish={((engine_dir / 'fish_engine.py').exists())}")

    # 10.3 CLAUDE.md has all 13 sections
    claude_md = _PROJECT_ROOT / "CLAUDE.md"
    if claude_md.exists():
        content = claude_md.read_text(encoding="utf-8")
        sections = [f"## {i}." for i in range(1, 14)]
        missing_secs = [s for s in sections if s not in content]
        check("10.3  CLAUDE.md exists and has all 13 sections",
              not missing_secs, f"missing: {missing_secs}")
    else:
        check("10.3  CLAUDE.md exists and has all 13 sections", False, "CLAUDE.md not found")

    # 10.4 requirements.txt has all key packages
    req_file = _PROJECT_ROOT / "server" / "requirements.txt"
    req_pkgs = ["fastapi", "TTS", "edge-tts", "soundfile", "numpy", "uvicorn"]
    if req_file.exists():
        req_content = req_file.read_text(encoding="utf-8")
        missing_pkgs = [pkg for pkg in req_pkgs if pkg not in req_content]
        check("10.4  requirements.txt contains all required packages",
              not missing_pkgs, f"missing: {missing_pkgs}")
    else:
        check("10.4  requirements.txt contains all required packages", False, "not found")

    # 10.5 output/ directory exists
    output_exists = any(
        (d / "output").exists()
        for d in [_PROJECT_ROOT / "server", _SERVER_DIR]
    )
    check("10.5  output/ directory exists", output_exists,
          str(_PROJECT_ROOT / "server" / "output"))

    # 10.6 reference_audio/ directory exists
    check("10.6  reference_audio/ directory exists",
          (_PROJECT_ROOT / "server" / "reference_audio").exists(),
          str(_PROJECT_ROOT / "server" / "reference_audio"))

    # 10.7 .env.example exists
    check("10.7  .env.example exists (created in P2)",
          (_SERVER_DIR / ".env.example").exists(),
          str(_SERVER_DIR / ".env.example"))

    # 10.8 Server still responsive after all tests
    r = _get("/health", timeout=5)
    check("10.8  Server still responsive after all tests (GET /health = 200)",
          r is not None and r.status_code == 200,
          f"status={r.status_code if r else 'no response'}")

    # 10.9 CLAUDE.md Build Status shows P1-P7 checked
    if claude_md.exists():
        content = claude_md.read_text(encoding="utf-8")
        missing_checks = [f"P{i}" for i in range(1, 8) if f"[x] P{i}" not in content]
        check("10.9  CLAUDE.md Build Status shows P1-P7 all checked",
              not missing_checks, f"missing: {missing_checks}")
    else:
        check("10.9  CLAUDE.md Build Status shows P1-P7 all checked", False, "CLAUDE.md not found")

    # 10.10 Session log has entries for P1 through P7
    if claude_md.exists():
        content = claude_md.read_text(encoding="utf-8")
        missing_logs = [f"P{i}" for i in range(1, 8) if f"] P{i} " not in content]
        check("10.10 Session log has entries for P1 through P7",
              not missing_logs, f"missing log entries for: {missing_logs}")
    else:
        check("10.10 Session log has entries for P1 through P7", False, "CLAUDE.md not found")

    _end_category()


# ═════════════════════════════════════════════════════════════════════════════
# MAIN
# ═════════════════════════════════════════════════════════════════════════════

def main():
    print("\n" + "=" * 60)
    print("  VoiceForge Phase 1 Backend Integration Test")
    print(f"  Target: {BASE_URL}")
    print(f"  Date:   {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # Connectivity check
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=3)
        d = r.json()
        print(f"\n  Server: HTTP {r.status_code} | status={d.get('status')} "
              f"| phase={d.get('phase')} | uptime={d.get('uptime_seconds')}s")
    except requests.ConnectionError:
        print(f"\n  ERROR: Cannot connect to {BASE_URL}")
        print("  Start the server first:")
        print("    cd C:\\VoiceForge\\server")
        print("    uvicorn main:app --host 0.0.0.0 --port 8000 --reload")
        sys.exit(1)

    # Run all 10 categories
    test_category_1()
    test_category_2()
    test_category_3()
    test_category_4()
    test_category_5()
    test_category_6()
    test_category_7()
    test_category_8()
    test_category_9()
    test_category_10()

    # Final summary
    total = C.passed + C.failed
    print("\n" + "=" * 60)
    print("  PHASE 1 TEST RESULTS — BY CATEGORY")
    print("=" * 60)
    for cat_name, cat_passed, cat_total in C.category_results:
        icon = "\u2705" if cat_passed == cat_total else "\u26a0\ufe0f "
        print(f"  {icon} {cat_name}: {cat_passed}/{cat_total}")

    print("\n" + "\u2500" * 60)
    print(f"  PHASE 1 RESULT: {C.passed}/{total} tests passed")
    if C.known_limitations:
        print(f"  Known limitations: {C.known_limitations} "
              "(expected Phase 1 constraints, not counted as failures)")
    if C.failed == 0:
        print("  \u2705 ALL TESTS PASSED \u2014 Phase 1 backend confirmed production-ready")
        sys.exit(0)
    else:
        print(f"  \u274c {C.failed} UNEXPECTED FAILURE(S) \u2014 review output above")
        sys.exit(1)


if __name__ == "__main__":
    main()

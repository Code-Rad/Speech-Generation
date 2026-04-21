# VoiceForge — Complete Project Analysis
> Compiled: April 18, 2026 | Antigravity full read of all files

---

## 1. What Is This Project

VoiceForge is a **standalone AI Speech Generation Platform** that takes text scripts and produces broadcast-quality human voice audio. It supports English, Hindi, and Hinglish via a swappable 4-engine TTS system. It is one module in a larger AI News Video generation pipeline that includes NewsForge (already built), VoiceForge (this), Background Module (Sumit), and upcoming Lower Thirds + Lip Sync + Music modules.

**GPU Server:** TRIJYA-7 (RTX 4090 24GB, Windows 11), accessible via Tailscale VPN (IP: 100.92.126.27)

---

## 2. Complete Build Status

### ✅ DONE — Phase 1 Backend (P1–P8)

| Prompt | What | Files | Tests |
|--------|------|-------|-------|
| P1 | Foundation, folder structure, CLAUDE.md | All dirs, 6 voice JSONs, scripts/verify_structure.py | 77/77 ✅ |
| P2 | BaseTTSEngine ABC + EngineFactory + config.py | engine/base_engine.py, engine/engine_factory.py, config.py | 7/7 ✅ |
| P3 | Edge TTS engine (fallback, no GPU) | engine/edge_engine.py | 8/8 ✅ |
| P4 | XTTS v2 engine (code ready, model not downloaded) | engine/xtts_engine.py | Code done ✅ |
| P5 | FastAPI — all 6 endpoints | server/main.py | Live ✅ |
| P6 | ProfileManager — 6 profiles, path resolution | server/profile_manager.py | 8/8 ✅ |
| P7 | AudioValidator + /clone-voice pipeline | server/audio_validator.py | 8/8 ✅ |
| P8 | Phase 1 integration test | scripts/test_phase1_backend.py | **72/72** ✅ |

### ✅ DONE — Phase 1 Frontend (P9–P10)

| Prompt | What | Files | Tests |
|--------|------|-------|-------|
| P9 | Main generator page | client/app/page.tsx + 6 components + lib/ | Build clean, HTTP 200 ✅ |
| P10 | Voices + Engines + History pages | 3 new pages + 6 new components | All 4 routes 200, 0 TS errors ✅ |

### ⚠️ UNCLEAR — P11

**P11 (Integration testing: full pipeline NewsForge → VoiceForge)** — The CLAUDE.md session log lists entries up to P10 (April 16) but has **NO entry for P11**. It shows `[ ] P11` in the build checklist. **P11 has NOT been run.**

### ❌ NOT STARTED — Phase 2 (P12–P14)

| Prompt | What | Status |
|--------|------|--------|
| P12 | Voxtral TTS engine (WSL2, best Hindi) | engine/voxtral_engine.py is a placeholder (12 lines) |
| P13 | Fish S2 Pro engine (WSL2, best English) | engine/fish_engine.py is a placeholder (12 lines) |
| P14 | Full Phase 2 integration + routing | Not started |

---

## 3. Exact File-by-File State

### Backend (`C:\VoiceForge\server\`)

| File | Size | State |
|------|------|-------|
| main.py | 914 lines | ✅ Complete — all 6 endpoints, Pydantic models, CORS |
| config.py | ~300 lines | ✅ Complete — phase routing, env loading |
| profile_manager.py | ~350 lines | ✅ Complete — 3-candidate path resolver, 6 lookup methods |
| audio_validator.py | ~450 lines | ✅ Complete — 7-check validation, stereo→mono, resample, normalize |
| requirements.txt | 1.8 KB | ✅ Complete |
| engine/base_engine.py | 15 KB | ✅ Complete — LOCKED, do not modify |
| engine/engine_factory.py | 12 KB | ✅ Complete — LOCKED, do not modify |
| engine/edge_engine.py | 12 KB | ✅ Complete and working |
| engine/xtts_engine.py | 16 KB | ✅ Code complete — model NOT downloaded |
| engine/voxtral_engine.py | 12 lines | ❌ **PLACEHOLDER** — needs P12 implementation |
| engine/fish_engine.py | 12 lines | ❌ **PLACEHOLDER** — needs P13 implementation |

### Frontend (`C:\VoiceForge\client\`)

| File | State |
|------|-------|
| app/page.tsx | ✅ Full generator UI (language selector, voice cards, script input, speaking rate, generate button, audio player, history save) |
| app/layout.tsx | ✅ Root layout with fonts |
| app/globals.css | ✅ Design system variables |
| app/voices/page.tsx | ✅ Voice Manager (upload reference audio, record modal) |
| app/engines/page.tsx | ✅ Engine Dashboard (Phase 1/2 grouping, status cards) |
| app/history/page.tsx | ✅ Generation History (localStorage, filter bar, playback) |
| components/EngineStatusStrip.tsx | ✅ Live polling /engines every 15s |
| components/LanguageSelector.tsx | ✅ EN/HI/Hinglish toggle |
| components/VoiceProfileCard.tsx | ✅ Selectable profile card |
| components/ScriptInput.tsx | ✅ Textarea with char count |
| components/GenerateButton.tsx | ✅ Animated CTA button |
| components/AudioPlayer.tsx | ✅ Playback + metadata + download |
| components/VoiceProfileManagerCard/ | ✅ Profile card for /voices |
| components/RecordModal/ | ✅ Browser mic recording |
| components/UploadZone/ | ✅ Drag-drop upload |
| components/Toast/ | ✅ Slide-in notifications |
| components/EngineCard/ | ✅ Engine status cards |
| components/HistoryItem/ | ✅ History entries |
| lib/types.ts | ✅ All TypeScript interfaces |
| lib/api.ts | ✅ fetchEngines, fetchVoices, generateSpeech, uploadReferenceAudio |
| lib/constants.ts | ✅ Design tokens, API URL, limits |

### Reference Audio

| File | State |
|------|-------|
| server/reference_audio/anchor_male_en_reference.wav | ✅ Uploaded (test file, 22.6s) |
| All other 5 profile reference WAVs | ❌ Not uploaded yet |

---

## 4. What Is Currently Working (Right Now)

Start both servers:
```powershell
# Terminal 1 — Backend
cd C:\VoiceForge\server
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload

# Terminal 2 — Frontend
cd C:\VoiceForge\client
npm run dev
```

Then open:
- `http://localhost:3000` — Full generator UI ✅
- `http://localhost:3000/voices` — Voice Manager ✅
- `http://localhost:3000/engines` — Engine Dashboard ✅
- `http://localhost:3000/history` — Generation History ✅
- `http://localhost:8000/docs` — API Swagger UI ✅

**Working features:**
- ✅ Speech generation (EN/HI/Hinglish) via Edge TTS fallback
- ✅ All 6 voice profiles loading
- ✅ Reference audio upload + validation pipeline
- ✅ Generation history in localStorage
- ✅ Engine status polling UI
- ✅ 72/72 backend tests pass

**Not working yet:**
- ⚠️ Audio quality — Edge TTS only (robotic/draft). Real quality needs XTTS v2 model download (~1.8GB) or Phase 2 engines
- ❌ Real voice cloning — upload pipeline works but XTTS model needed
- ❌ Voxtral TTS — P12 needed (WSL2 on TRIJYA-7)
- ❌ Fish S2 Pro — P13 needed (WSL2 on TRIJYA-7)
- ❌ P11 integration test (never run)

---

## 5. What Comes Next (In Order)

### Step 1 — Run P11 (Integration Test)
**What:** Verify the full NewsForge → VoiceForge pipeline end-to-end.  
**Status:** Prompt was written in the original Claude chat but **never executed**.  
**Action:** Generate P11 prompt and implement + run it.

P11 should cover:
- End-to-end test: send a real NewsForge-style JSON script to POST /generate
- Verify all 6 profiles work
- Verify audio quality metadata (headers) are correct
- Verify frontend receives and plays audio
- Document any integration gaps

### Step 2 — Download XTTS v2 Model (Low-Hanging Fruit)
**Action (can be done independently of P11):**
```powershell
cd C:\VoiceForge\server
python -c "from TTS.api import TTS; TTS('tts_models/multilingual/multi-dataset/xtts_v2', gpu=True)"
```
This downloads ~1.8GB and immediately makes XTTS v2 available as the primary Phase 1 engine, giving real voice quality without WSL2.

### Step 3 — P12: Voxtral TTS Engine
**What:** Best Hindi/Hinglish quality engine.
- Setup WSL2 on TRIJYA-7
- Install vLLM-Omni, serve Voxtral on port 8091
- Implement `voxtral_engine.py` (currently empty placeholder)
- Integrate into EngineFactory
- Run integration tests

### Step 4 — P13: Fish S2 Pro Engine
**What:** Best English quality engine.
- Install SGLang in WSL2, serve Fish S2 Pro on port 8092
- Implement `fish_engine.py` (currently empty placeholder)
- Integrate into EngineFactory
- Run integration tests

### Step 5 — P14: Phase 2 Full Integration
**What:** Update language router (English → Fish S2 Pro, Hindi/Hinglish → Voxtral), full end-to-end test with Phase 2 engines, finalize CLAUDE.md.

---

## 6. Known Technical Decisions & Bugs Already Fixed

These are documented so they don't get reintroduced:

| Issue | Fix Applied |
|-------|-------------|
| CORS headers | `expose_headers` in CORSMiddleware — allows browser to read `x-engine-used`, `x-is-draft` |
| asyncio conflict | `asyncio.to_thread()` in /clone-voice — prevents nested event loop error in async FastAPI |
| Path resolution | Multi-candidate resolver in ProfileManager + main.py `_resolve_output_dir()` |
| OUTPUT_DIR bug | Fixed — prevents `server/server/output/` nested-dir when uvicorn starts from server/ |
| Frontend headers | api.ts uses graceful fallbacks — never throws if a header is missing |

---

## 7. Recommended Workflow Going Forward

The established development pattern is:
1. **Antigravity generates a detailed implementation prompt** (following the spec in VOICEFORGE_CONTEXT.md Section 15)
2. **Implements + verifies the prompt autonomously** (code, tests, fixes)
3. **Reports what was done and what to do next**

> **My recommendation: We tackle P11 first (integration test + docs polish), then decide whether to run XTTS v2 download or jump to P12.**  
> P11 will surface any gaps between the frontend and backend before we add Phase 2 engines.

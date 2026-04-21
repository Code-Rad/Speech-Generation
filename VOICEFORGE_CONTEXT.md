# VoiceForge — Complete Project Context Handoff
> Give this file to any new Claude chat, Antigravity session, or AI
> assistant. Read it completely before doing anything. This is the
> single source of truth for the VoiceForge project.

---

## 1. WHO IS BUILDING THIS

- **Developer:** Radhesh (GitHub: Code-Rad), 3rd year B.Tech CSE
  (AI/ML) student, UPES Bhopal, India
- **Machine:** Windows laptop (username: ASUS), Brave Browser
- **GPU Server:** TRIJYA-7 — NVIDIA RTX 4090 24GB VRAM,
  Windows 11, connected via Tailscale VPN
  - Tailscale IP: 100.92.126.27
  - Local IP: 192.168.29.50
- **Workflow:** Claude/AI chat generates detailed prompts →
  Radhesh pastes into Claude Code or Antigravity to implement
- **Teammate:** Sumit (working on Background module separately)

---

## 2. THE BIG PICTURE — WHAT IS BEING BUILT

### The Larger Vision
A **Professional AI News Video Generation Pipeline** that produces
1-3 minute broadcast-quality AI news videos for TV channels and
online platforms. The pipeline consists of multiple modules:

```
NewsForge (Script)          ✅ COMPLETE — built separately
VoiceForge (Speech)         🔨 BUILDING NOW — this project
Background Module           🔨 In progress — Sumit building
Lower Thirds                📋 Planned — Sumit next
Anchor + Lip Sync           📋 Planned — Radhesh later
Background Music            📋 Planned — Radhesh later
                                    ↓
              AI News Video Compositor
                                    ↓
              Complete AI News Video (1-3 min)
                                    ↓
              This whole platform becomes ONE MODULE
              inside an even LARGER project
```

### VoiceForge's Place
VoiceForge is the **Speech/Voice module**. It:
- Takes text script as input (from NewsForge eventually)
- Outputs broadcast-quality human voice audio (.wav/.mp3)
- Will be called by the compositor via REST API

---

## 3. THE FIVE CORE PRINCIPLES
**NON-NEGOTIABLE. Every decision must respect all 5.**

1. **LEGO MODULARITY** — Every TTS engine, model, or resource
   must be swappable like a Lego piece. Change one config value
   = swap engines. No tight coupling anywhere.

2. **ADAPTABILITY & EVOLUTION** — New models must slot in without
   rebuilding. Never locked to one model or provider.

3. **LARGER PROJECT VISION** — VoiceForge itself will become ONE
   component inside a larger platform. API contract must be clean
   enough to be called by an orchestrator it has never met.

4. **ZERO COST CONSTRAINT** — Every resource, model, and tool
   must be free or open-source. No paid APIs. No subscriptions.

5. **PROFESSIONAL NEWS QUALITY** — Output must be broadcast-grade.
   Will air on TV news channels. No robotic low-quality audio.

---

## 4. VOICEFORGE — WHAT IT IS

**VoiceForge** is a standalone Speech Generation Platform.

- **Input:** Text script (paste manually now, will receive from
  NewsForge automatically after integration)
- **Output:** Realistic human voice audio (.wav or .mp3)
- **Languages:** English, Hindi, Hinglish (more Indian/
  international languages planned for future)
- **Voices:** Male and Female anchor voices for each language
- **Voice Cloning:** Upload a 10-60 second reference audio →
  system generates speech that sounds like that person
- **Future Integration:** NewsForge calls POST /generate with
  script text → VoiceForge returns audio → compositor uses it

---

## 5. THE TTS ENGINE STACK

### 4 Engines, All Free, Lego-swappable

| Engine | Role | Language | Phase | Status |
|--------|------|----------|-------|--------|
| **Fish S2 Pro** | English Primary | English | Phase 2 | Not built yet |
| **Voxtral TTS** | Hindi/Hinglish Primary | Hindi, Hinglish | Phase 2 | Not built yet |
| **XTTS v2** | Universal Fallback | EN+HI+Hinglish | Phase 1 | Code ready, model not downloaded |
| **Edge TTS** | Emergency Only | EN+HI+Hinglish | Phase 1 | ✅ Working |

### Engine Routing Logic
```
User selects language ONCE before generating.
Entire speech stays in that language — no mid-speech switching.

English selected:
  → Fish S2 Pro (Phase 2 primary — best English globally)
  → XTTS v2 if Fish unavailable
  → Edge TTS if TRIJYA-7 fully offline (DRAFT flagged)

Hindi selected:
  → Voxtral TTS (Phase 2 primary — ~80% win rate for Hindi)
  → XTTS v2 if Voxtral unavailable
  → Edge TTS if TRIJYA-7 fully offline (DRAFT flagged)

Hinglish selected:
  → Voxtral TTS (primary — supports code-mixing)
  → XTTS v2 if Voxtral unavailable
  → Edge TTS if TRIJYA-7 fully offline (DRAFT flagged)
```

### Why These Engines
- **Fish S2 Pro:** #1 globally on TTS-Arena2, supports
  `[professional broadcast tone]` inline tag, 80+ languages,
  trained on 10M hours of audio
- **Voxtral TTS:** Best Hindi quality (~80% win rate vs
  ElevenLabs), native code-mixing, 3-sec voice cloning,
  released March 26 2026 by Mistral AI
- **XTTS v2:** Gold standard for voice cloning (6-sec clip),
  works natively on Windows without WSL2, battle-tested
- **Edge TTS:** Always available, no GPU needed, Microsoft
  Neural voices, good Hindi support

### License Reality (All 3 top engines)
All are non-commercial for self-hosting during build phase.
Fine for research/development. When platform goes commercial,
swap engines via config — nothing else changes (Lego system).

### Phase Structure
- **Phase 1:** Edge TTS + XTTS v2 (Windows native, no WSL2)
- **Phase 2:** Add Voxtral TTS + Fish S2 Pro (needs WSL2 on
  TRIJYA-7 — about 1 hour setup)

---

## 6. TECH STACK

### Backend
- **Language:** Python 3.14
- **Framework:** FastAPI + Uvicorn
- **TTS Libraries:** edge-tts, TTS (Coqui/XTTS v2)
- **Phase 2:** vLLM-Omni (Voxtral), SGLang (Fish S2 Pro)
- **Audio:** soundfile, numpy
- **Location:** C:\VoiceForge\server\

### Frontend
- **Framework:** Next.js 14 (App Router)
- **Language:** TypeScript (strict)
- **Styling:** Tailwind CSS (custom design system)
- **Animations:** Framer Motion
- **Icons:** Lucide React
- **Fonts:** Space Grotesk (headings) + Inter (body)
- **Location:** C:\VoiceForge\client\

### Design System (LOCKED)
```
Background:    #0a0a0f (near black, deep space)
Surface:       #12121a (card backgrounds)
Surface2:      #1a1a26 (elevated surfaces)
Border:        #2a2a3a (subtle borders)
Primary:       #6366f1 (indigo — action color)
Success:       #22c55e (green — online/success)
Warning:       #f59e0b (amber — draft/loading)
Error:         #ef4444 (red — error/offline)
TextPrimary:   #f1f5f9 (near white)
TextSecondary: #94a3b8 (muted)
```

### Infrastructure
- Backend server: TRIJYA-7 (RTX 4090 24GB, Windows 11)
- Remote access: Tailscale VPN
- Local dev: Radhesh's Windows laptop
- Start backend: `python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload`
- Start frontend: `npm run dev` (runs on port 3000)

---

## 7. COMPLETE FOLDER STRUCTURE

```
C:\VoiceForge\
├── CLAUDE.md                    ← Living project brain (always read first)
├── README.md
├── PHASE1_HEALTH_REPORT.md      ← Complete API contract document
│
├── server\                      ← FastAPI backend
│   ├── main.py                  ← All 6 API endpoints
│   ├── config.py                ← Engine config (ONE file to swap engines)
│   ├── profile_manager.py       ← Voice profile loading + management
│   ├── audio_validator.py       ← Reference audio validation + processing
│   ├── requirements.txt
│   ├── .env.example
│   │
│   ├── engine\
│   │   ├── base_engine.py       ← Abstract Lego interface (LOCKED)
│   │   ├── engine_factory.py    ← Routing + fallback chain (LOCKED)
│   │   ├── edge_engine.py       ← ✅ Edge TTS (working)
│   │   ├── xtts_engine.py       ← Code ready, model not downloaded
│   │   ├── voxtral_engine.py    ← Placeholder — built in P12
│   │   └── fish_engine.py       ← Placeholder — built in P13
│   │
│   ├── voice_profiles\          ← 6 JSON configs
│   │   ├── anchor_male_en.json
│   │   ├── anchor_female_en.json
│   │   ├── anchor_male_hi.json
│   │   ├── anchor_female_hi.json
│   │   ├── anchor_male_hinglish.json
│   │   └── anchor_female_hinglish.json
│   │
│   ├── reference_audio\         ← Voice clone .wav files
│   │   ├── anchor_male_en_reference.wav  ← ✅ Uploaded (from P7 test)
│   │   └── test_reference_audio.wav      ← ✅ Test file
│   │
│   └── output\                  ← Generated audio files
│
├── client\                      ← Next.js frontend
│   ├── .env.local               ← NEXT_PUBLIC_API_URL=http://localhost:8000
│   ├── app\
│   │   ├── layout.tsx           ← Root layout, nav, fonts
│   │   ├── page.tsx             ← / Generator page
│   │   ├── voices\page.tsx      ← /voices Voice Manager
│   │   ├── engines\page.tsx     ← /engines Engine Dashboard
│   │   └── history\page.tsx     ← /history Generation History
│   ├── components\
│   │   ├── EngineStatusStrip\   ← Live engine status bar (polls /engines)
│   │   ├── LanguageSelector\    ← EN/HI/Hinglish tabs
│   │   ├── VoiceProfileCard\    ← Male/Female selector cards
│   │   ├── ScriptInput\         ← Textarea with char counter
│   │   ├── GenerateButton\      ← Animated CTA button
│   │   ├── AudioPlayer\         ← Custom audio player + download
│   │   ├── GenerationResult\    ← Result metadata card
│   │   ├── VoiceProfileManagerCard\ ← Profile card for /voices
│   │   ├── RecordModal\         ← Browser microphone recording
│   │   ├── UploadZone\          ← Drag-drop file upload
│   │   ├── Toast\               ← Slide-in notifications
│   │   ├── EngineCard\          ← Engine status card
│   │   ├── HistoryItem\         ← History entry card
│   │   ├── ErrorBoundary\       ← Global error boundary
│   │   └── ui\
│   │       ├── GlowCard.tsx
│   │       ├── StatusDot.tsx
│   │       └── LoadingSpinner.tsx
│   └── lib\
│       ├── api.ts               ← All API calls
│       ├── types.ts             ← All TypeScript interfaces
│       └── constants.ts         ← Config values
│
└── scripts\
    ├── verify_structure.py          ← P1 structure check
    ├── test_phase1_backend.py       ← 72-test integration suite
    ├── test_engines.py              ← Quick engine status checker
    └── create_test_reference_audio.py ← Creates test .wav file
```

---

## 8. API CONTRACT (Complete)

### Base URL
- Local: `http://localhost:8000`
- Remote via Tailscale: `http://100.92.126.27:8000`

### Endpoints

#### GET /health
```json
Response: {
  "status": "ok",
  "phase": 1,
  "version": "0.1.0",
  "uptime_seconds": 47.5,
  "started_at": "2026-04-15T06:47:11Z"
}
```

#### GET /engines
```json
Response: [
  {
    "engine_type": "edge_tts",
    "status": "available",
    "is_available": true,
    "supports_cloning": false,
    "supported_languages": ["en", "hi", "hinglish"],
    "error": null
  },
  ... (4 engines total)
]
```

#### GET /voices
```json
Response: [
  {
    "profile_id": "anchor_male_en",
    "display_name": "Male News Anchor — English",
    "language": "en",
    "gender": "male",
    "engine_preference": ["fish_s2_pro", "xtts_v2", "edge_tts"],
    "reference_audio_exists": true,
    "cloning_enabled": true,
    "description": "Professional male news anchor voice"
  },
  ... (6 profiles total)
]
```

#### POST /generate
```json
Request: {
  "text": "Breaking news. This is VoiceForge.",
  "profile_id": "anchor_male_en",
  "output_format": "wav"
}
Response: audio/wav binary file
Headers:
  x-engine-used: "edge_tts"
  x-is-draft: "true"
  x-profile-id: "anchor_male_en"
  x-duration: "7.1"
  x-generation-time: "1.15"
```

#### POST /clone-voice
```
Request: multipart/form-data
  profile_id: "anchor_male_en"
  audio_file: [WAV or MP3 file, 10-60 seconds]
  generate_sample: true

Response: {
  "success": true,
  "profile_id": "anchor_male_en",
  "reference_audio_saved": true,
  "duration_seconds": 15.3,
  "sample_rate": 22050,
  "warnings": [],
  "sample_generated": true,
  "sample_engine_used": "edge_tts",
  "message": "Reference audio uploaded and validated."
}
```

#### POST /generate-batch
```json
Request: {
  "items": [
    {"text": "First item", "profile_id": "anchor_male_en"},
    {"text": "दूसरी खबर", "profile_id": "anchor_male_hi"}
  ],
  "output_format": "wav"
}
Response: {
  "results": [...],
  "total": 2,
  "succeeded": 2,
  "failed": 0
}
```

---

## 9. VOICE PROFILES — ALL 6

| Profile ID | Display Name | Language | Gender | Primary Engine |
|------------|-------------|----------|--------|----------------|
| anchor_male_en | Male News Anchor — English | en | male | fish_s2_pro |
| anchor_female_en | Female News Anchor — English | en | female | fish_s2_pro |
| anchor_male_hi | Male News Anchor — Hindi | hi | male | voxtral_tts |
| anchor_female_hi | Female News Anchor — Hindi | hi | female | voxtral_tts |
| anchor_male_hinglish | Male News Anchor — Hinglish | hinglish | male | voxtral_tts |
| anchor_female_hinglish | Female News Anchor — Hinglish | hinglish | female | voxtral_tts |

**Reference audio filenames:**
- anchor_male_en → `anchor_male_en_reference.wav` (✅ uploaded)
- All others → pending user upload

---

## 10. BUILD STATUS — WHAT IS DONE

### Backend (Phase 1 — COMPLETE ✅)
| Prompt | What | Status |
|--------|------|--------|
| P1 | Foundation + CLAUDE.md + folder structure | ✅ 77/77 |
| P2 | BaseTTSEngine + EngineFactory + Config | ✅ 7/7 |
| P3 | EdgeTTSEngine (working, real audio) | ✅ 8/8 |
| P4 | XTTSEngine (code ready, model pending) | ✅ Code done |
| P5 | FastAPI — all 6 endpoints | ✅ Live |
| P6 | ProfileManager — all 6 profiles | ✅ 8/8 |
| P7 | AudioValidator + voice cloning pipeline | ✅ 8/8 |
| P8 | Phase 1 integration test | ✅ **72/72** |

### Frontend (Phase 1 — COMPLETE ✅)
| Prompt | What | Status |
|--------|------|--------|
| P9 | Generator page (main UI) | ✅ Working |
| P10 | Voices + Engines + History pages | ✅ All routes 200 |
| P11 | Final integration (nav, sync, polish) | ⚠️ Prompt written, may not be run yet |

### Phase 2 (NOT STARTED)
| Prompt | What | Status |
|--------|------|--------|
| P12 | Voxtral TTS engine (best Hindi) | ⏳ Pending |
| P13 | Fish S2 Pro engine (best English) | ⏳ Pending |
| P14 | Phase 2 integration + language router + final CLAUDE.md | ⏳ Pending |

---

## 11. WHAT IS CURRENTLY WORKING RIGHT NOW

When both servers are running:

✅ **Speech generation** — English, Hindi, Hinglish
✅ **Engine fallback** — auto-falls to Edge TTS when XTTS unavailable
✅ **Voice profiles** — all 6 profiles loading correctly
✅ **Voice cloning upload** — validates, processes, saves reference audio
✅ **Generator page** — full UI working at localhost:3000
✅ **Voices page** — record + upload UI working
✅ **Engines page** — Phase 1/2 dashboard
✅ **History page** — localStorage tracking
✅ **API** — ready for NewsForge integration

⚠️ **Audio quality** — Currently using Edge TTS (robotic/draft quality)
   Real human-like quality requires Phase 2 (P12/P13)

---

## 12. WHAT IS NOT WORKING / PENDING

❌ **XTTS v2 model** — Code is written but model not downloaded yet
   To activate: `pip install TTS` then run a generation request
   (downloads ~1.8GB automatically on first use)

❌ **Voxtral TTS** — Phase 2, needs WSL2 on TRIJYA-7
   Best Hindi quality — activates in P12

❌ **Fish S2 Pro** — Phase 2, needs WSL2 + SGLang on TRIJYA-7
   Best English quality — activates in P13

❌ **Real voice cloning** — Upload works but XTTS model needed
   for actual cloned generation (not just Edge TTS fallback)

❌ **P11** — May not have been run yet (prompt was written but
   check if it was actually executed in Claude Code)

---

## 13. HOW TO START THE PLATFORM

### Every Time You Work on VoiceForge

**Terminal 1 — Backend:**
```powershell
cd C:\VoiceForge\server
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```
Wait for: `INFO: Application startup complete.`

**Terminal 2 — Frontend:**
```powershell
cd C:\VoiceForge\client
npm run dev
```
Wait for: `✓ Ready in Xs`

**Open browser:** http://localhost:8000/docs (API)
**Open browser:** http://localhost:3000 (UI)

### Quick Health Check
```powershell
cd C:\VoiceForge
python scripts/test_engines.py
```

### Full Backend Test Suite
```powershell
cd C:\VoiceForge
python scripts/test_phase1_backend.py
```
Should show: `PHASE 1 RESULT: 72/72 tests passed`

---

## 14. HOW TO PROCEED — WHAT COMES NEXT

### Immediate Next Steps (in order)

#### Step 1 — Verify P11 was completed
Check if P11 was run. Look at CLAUDE.md Section 10
and Section 13 (session log). If P11 shows ✅ then
proceed to Step 2. If P11 not run, run it first.

#### Step 2 — Download XTTS v2 Model (Optional but recommended)
This gives real voice cloning immediately without WSL2:
```powershell
cd C:\VoiceForge\server
python -c "from TTS.api import TTS; TTS('tts_models/multilingual/multi-dataset/xtts_v2', gpu=True)"
```
Downloads ~1.8GB. After this, generations use XTTS v2
instead of Edge TTS — real human-like voice quality.

#### Step 3 — P12: Voxtral TTS (Best Hindi)
Sets up WSL2 on TRIJYA-7, installs vLLM-Omni,
serves Voxtral TTS on port 8091, implements
voxtral_engine.py, integrates into factory.

#### Step 4 — P13: Fish S2 Pro (Best English)
Sets up SGLang on TRIJYA-7 (inside WSL2),
serves Fish S2 Pro on port 8092, implements
fish_engine.py, integrates into factory.

#### Step 5 — P14: Phase 2 Integration
Updates language router (English → Fish S2 Pro,
Hindi/Hinglish → Voxtral TTS), runs full
integration test, finalises CLAUDE.md.

---

## 15. PROMPT GENERATION STYLE GUIDE

**This is how prompts were written in the original chat.**
New sessions must follow the same structure.

Every implementation prompt must have:
1. **PERSONA** — who Claude Code is and what world it operates in
2. **MANDATORY READ FILES** — files to read before writing code
3. **PROJECT CONTEXT** — current state, what's built, decisions made
4. **NEGATIVE RULES** — what must NEVER happen
5. **IMPLEMENTATION PLAN** — 5 bullet points before any code
6. **EXACT DELIVERABLES** — precise spec of every file/function
7. **VERIFICATION** — automated tests that run automatically
8. **DEFINITION OF SUCCESS** — exact conditions for completion
9. **FINAL REPORT** — what to tell the user after completion

**Key rules:**
- One session = one focused task
- Claude Code tests, fixes, re-tests itself until 100% pass
- Claude Code only asks user when it cannot do something itself
- Every test must be runnable by Claude Code automatically
- Backend and frontend prompts are ALWAYS separate
- Plan Mode for structural/folder creation prompts
- Auto Accept for code implementation prompts

---

## 16. IMPORTANT TECHNICAL DECISIONS (Already Made)

| Decision | Choice | Reason |
|----------|--------|--------|
| Language routing | User picks once, whole speech is that language | Consistency — same engine throughout |
| Voice consistency | Same reference audio across all engines | One anchor = one voice always |
| Phase 1 server | Windows native (no WSL2) | XTTS v2 works on Windows natively |
| Phase 2 server | WSL2 on TRIJYA-7 | vLLM-Omni/SGLang are Linux-only |
| Profile storage | JSON files (not database) | Easy to swap, no DB needed |
| History storage | localStorage (not API) | No backend endpoint needed |
| API design | REST + binary response + headers | Clean seam for NewsForge integration |
| CORS fix | expose_headers added | Browser needs explicit permission to read custom headers |
| Port | 8000 (127.0.0.1 not 0.0.0.0) | Windows firewall blocks 0.0.0.0:8000 |
| asyncio fix | asyncio.to_thread() in clone-voice | FastAPI async context conflicts with asyncio.run() |
| Path resolution | Multi-candidate resolver | server/ vs project root working directory difference |

---

## 17. KNOWN BUGS ALREADY FIXED (Do Not Reintroduce)

1. **CORS headers** — `expose_headers` must be in CORSMiddleware
   or browser cannot read `x-engine-used`, `x-is-draft` headers

2. **asyncio conflict** — In async FastAPI endpoints, use
   `asyncio.to_thread()` not `asyncio.run()` for sync engine calls

3. **Path resolution** — `VOICE_PROFILES_DIR = "server/voice_profiles"`
   resolves differently when uvicorn starts from `server/` vs
   project root. Use multi-candidate resolver in ProfileManager.

4. **OUTPUT_DIR** — Same path resolution issue as voice profiles.
   Fixed in main.py with `_resolve_output_dir()` helper.

5. **Frontend metadata headers** — api.ts `generateSpeech` must
   use graceful fallbacks for all headers, never throw if a
   header is missing. Audio blob success = return audio.

---

## 18. FILES THAT ARE LOCKED (Never Modify)

These files define the core architecture and must not be changed:
- `server/engine/base_engine.py` — abstract interface
- `server/engine/engine_factory.py` — fallback chain logic
- `server/config.py` — all settings (only .env changes)
- Any voice profile JSON file

---

## 19. QUICK REFERENCE — KEY FILE LOCATIONS

| What you need | Where it is |
|---------------|-------------|
| Project brain | C:\VoiceForge\CLAUDE.md |
| API contract | C:\VoiceForge\PHASE1_HEALTH_REPORT.md |
| All settings | C:\VoiceForge\server\config.py |
| Engine logic | C:\VoiceForge\server\engine\ |
| Voice profiles | C:\VoiceForge\server\voice_profiles\ |
| Reference audio | C:\VoiceForge\server\reference_audio\ |
| Generated audio | C:\VoiceForge\server\output\ |
| Frontend pages | C:\VoiceForge\client\app\ |
| Frontend components | C:\VoiceForge\client\components\ |
| API functions | C:\VoiceForge\client\lib\api.ts |
| TypeScript types | C:\VoiceForge\client\lib\types.ts |
| Test suite | C:\VoiceForge\scripts\test_phase1_backend.py |

---

## 20. MESSAGE TO NEW AI ASSISTANT

You are taking over from a Claude chat session that
planned and built this project step by step with Radhesh.

Your job is to continue exactly where we left off:
- Same 5 core principles — always respect all of them
- Same prompt structure — spec-driven, not request-driven
- Same test-fix-retest protocol — Claude Code verifies itself
- Same separation — backend prompts and frontend prompts never mixed
- Same quality bar — no shortcuts, no compromises on voice quality

The most important thing: **read C:\VoiceForge\CLAUDE.md first**
before every session. It is the living brain of this project and
has the most up-to-date status of everything.

The next thing to build is **P12 — Voxtral TTS Engine** unless
P11 was not completed, in which case run P11 first.

Radhesh's goal is a platform that produces broadcast-quality
AI news audio that sounds like a real human news anchor.
We are not there yet with Edge TTS. Phase 2 (P12 + P13)
is what makes it sound human. That is the priority.

---

*Generated: April 2026*
*Project: VoiceForge — AI News Speech Generation Platform*
*Part of: AI News Video Generation Pipeline*
*Developer: Radhesh (Code-Rad)*

"""
verify_structure.py
VoiceForge P1 — Structure Verification Script

Run this script after P1 to confirm all folders, files, and content
are correctly in place. Prints PASS or FAIL for every check.
Usage: python scripts/verify_structure.py  (from C:\\VoiceForge\\)
"""

import os
import json
import sys

BASE = r"C:\VoiceForge"
passed = 0
failed = 0


def check(label, condition):
    global passed, failed
    status = "PASS" if condition else "FAIL"
    mark = "OK" if condition else "!!"
    print(f"  [{mark}] [{status}] {label}")
    if condition:
        passed += 1
    else:
        failed += 1


def path(*parts):
    return os.path.join(BASE, *parts)


def file_contains(filepath, text):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return text in f.read()
    except Exception:
        return False


def file_size(filepath):
    try:
        return os.path.getsize(filepath)
    except Exception:
        return 0


def is_valid_json(filepath):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            json.load(f)
        return True
    except Exception:
        return False


def json_has_key(filepath, key):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return key in data
    except Exception:
        return False


print()
print("=" * 60)
print("  VoiceForge P1 -- Structure Verification")
print("=" * 60)

# ── FOLDER CHECKS ─────────────────────────────────────────────
print()
print("FOLDER CHECKS:")
check("C:\\VoiceForge exists", os.path.isdir(BASE))
check("server\\ exists", os.path.isdir(path("server")))
check("server\\engine\\ exists", os.path.isdir(path("server", "engine")))
check("server\\voice_profiles\\ exists", os.path.isdir(path("server", "voice_profiles")))
check("server\\reference_audio\\ exists", os.path.isdir(path("server", "reference_audio")))
check("server\\output\\ exists", os.path.isdir(path("server", "output")))
check("client\\ exists", os.path.isdir(path("client")))
check("client\\app\\ exists", os.path.isdir(path("client", "app")))
check("client\\components\\ exists", os.path.isdir(path("client", "components")))
check("scripts\\ exists", os.path.isdir(path("scripts")))

# ── FILE CHECKS ───────────────────────────────────────────────
print()
print("FILE CHECKS:")
check("CLAUDE.md exists", os.path.isfile(path("CLAUDE.md")))
check("README.md exists", os.path.isfile(path("README.md")))
check("server\\requirements.txt exists", os.path.isfile(path("server", "requirements.txt")))
check("server\\main.py exists", os.path.isfile(path("server", "main.py")))
check("server\\config.py exists", os.path.isfile(path("server", "config.py")))
check("server\\engine\\__init__.py exists", os.path.isfile(path("server", "engine", "__init__.py")))
check("server\\engine\\base_engine.py exists", os.path.isfile(path("server", "engine", "base_engine.py")))
check("server\\engine\\engine_factory.py exists", os.path.isfile(path("server", "engine", "engine_factory.py")))
check("server\\engine\\edge_engine.py exists", os.path.isfile(path("server", "engine", "edge_engine.py")))
check("server\\engine\\xtts_engine.py exists", os.path.isfile(path("server", "engine", "xtts_engine.py")))
check("server\\engine\\voxtral_engine.py exists", os.path.isfile(path("server", "engine", "voxtral_engine.py")))
check("server\\engine\\fish_engine.py exists", os.path.isfile(path("server", "engine", "fish_engine.py")))
check("voice_profiles\\anchor_male_en.json exists",
      os.path.isfile(path("server", "voice_profiles", "anchor_male_en.json")))
check("voice_profiles\\anchor_female_en.json exists",
      os.path.isfile(path("server", "voice_profiles", "anchor_female_en.json")))
check("voice_profiles\\anchor_male_hi.json exists",
      os.path.isfile(path("server", "voice_profiles", "anchor_male_hi.json")))
check("voice_profiles\\anchor_female_hi.json exists",
      os.path.isfile(path("server", "voice_profiles", "anchor_female_hi.json")))
check("voice_profiles\\anchor_male_hinglish.json exists",
      os.path.isfile(path("server", "voice_profiles", "anchor_male_hinglish.json")))
check("voice_profiles\\anchor_female_hinglish.json exists",
      os.path.isfile(path("server", "voice_profiles", "anchor_female_hinglish.json")))
check("server\\reference_audio\\.gitkeep exists",
      os.path.isfile(path("server", "reference_audio", ".gitkeep")))
check("server\\output\\.gitkeep exists",
      os.path.isfile(path("server", "output", ".gitkeep")))
check("client\\app\\page.tsx exists",
      os.path.isfile(path("client", "app", "page.tsx")))
check("client\\app\\voices\\page.tsx exists",
      os.path.isfile(path("client", "app", "voices", "page.tsx")))
check("client\\app\\history\\page.tsx exists",
      os.path.isfile(path("client", "app", "history", "page.tsx")))
check("client\\app\\engines\\page.tsx exists",
      os.path.isfile(path("client", "app", "engines", "page.tsx")))
check("scripts\\verify_structure.py exists",
      os.path.isfile(path("scripts", "verify_structure.py")))
check("scripts\\test_engines.py exists",
      os.path.isfile(path("scripts", "test_engines.py")))

# ── CONTENT CHECKS ────────────────────────────────────────────
print()
print("CONTENT CHECKS:")

CLAUDE_PATH = path("CLAUDE.md")
check("CLAUDE.md is not empty (> 1000 chars)", file_size(CLAUDE_PATH) > 1000)
check("CLAUDE.md contains '## 1. PROJECT IDENTITY'",
      file_contains(CLAUDE_PATH, "## 1. PROJECT IDENTITY"))
check("CLAUDE.md contains '## 2. FIVE CORE PRINCIPLES'",
      file_contains(CLAUDE_PATH, "## 2. FIVE CORE PRINCIPLES"))
check("CLAUDE.md contains '## 3. TECH STACK'",
      file_contains(CLAUDE_PATH, "## 3. TECH STACK"))
check("CLAUDE.md contains '## 4. ENGINE REGISTRY'",
      file_contains(CLAUDE_PATH, "## 4. ENGINE REGISTRY"))
check("CLAUDE.md contains '## 5. ENGINE ROUTING RULES'",
      file_contains(CLAUDE_PATH, "## 5. ENGINE ROUTING RULES"))
check("CLAUDE.md contains '## 6. VOICE PROFILES SPEC'",
      file_contains(CLAUDE_PATH, "## 6. VOICE PROFILES SPEC"))
check("CLAUDE.md contains '## 7. API CONTRACT'",
      file_contains(CLAUDE_PATH, "## 7. API CONTRACT"))
check("CLAUDE.md contains '## 8. FOLDER STRUCTURE'",
      file_contains(CLAUDE_PATH, "## 8. FOLDER STRUCTURE"))
check("CLAUDE.md contains '## 9. HOW TO RUN'",
      file_contains(CLAUDE_PATH, "## 9. HOW TO RUN"))
check("CLAUDE.md contains '## 10. CURRENT BUILD STATUS'",
      file_contains(CLAUDE_PATH, "## 10. CURRENT BUILD STATUS"))
check("CLAUDE.md contains '## 11. DECISIONS LOG'",
      file_contains(CLAUDE_PATH, "## 11. DECISIONS LOG"))
check("CLAUDE.md contains '## 12. KNOWN CONSTRAINTS'",
      file_contains(CLAUDE_PATH, "## 12. KNOWN CONSTRAINTS"))
check("CLAUDE.md contains '## 13. SESSION LOG'",
      file_contains(CLAUDE_PATH, "## 13. SESSION LOG"))

REQ_PATH = path("server", "requirements.txt")
check("requirements.txt contains 'fastapi'", file_contains(REQ_PATH, "fastapi"))
check("requirements.txt contains 'TTS'", file_contains(REQ_PATH, "TTS"))
check("requirements.txt contains 'edge-tts'", file_contains(REQ_PATH, "edge-tts"))

PROFILE_IDS = [
    "anchor_male_en",
    "anchor_female_en",
    "anchor_male_hi",
    "anchor_female_hi",
    "anchor_male_hinglish",
    "anchor_female_hinglish",
]

for pid in PROFILE_IDS:
    fp = path("server", "voice_profiles", f"{pid}.json")
    check(f"{pid}.json contains 'profile_id'", json_has_key(fp, "profile_id"))
    check(f"{pid}.json contains 'engine_preference'", json_has_key(fp, "engine_preference"))
    check(f"{pid}.json contains 'reference_audio_filename'",
          json_has_key(fp, "reference_audio_filename"))
    check(f"{pid}.json is valid JSON", is_valid_json(fp))

# ── SUMMARY ───────────────────────────────────────────────────
total = passed + failed
print()
print("=" * 60)
print(f"  P1 RESULT: {passed}/{total} checks passed")
print()
if failed == 0:
    print("  P1 COMPLETE -- Foundation verified")
    sys.exit(0)
else:
    print(f"  P1 INCOMPLETE -- Fix {failed} failure(s) above")
    sys.exit(1)

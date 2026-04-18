"""
profile_manager.py
VoiceForge — Voice Profile Manager

Responsible for:
- Loading all voice profiles from disk
- Validating profile schemas
- Resolving file paths for reference audio
- Providing profile lookup by ID and language/gender

This module is the single source of truth for profile data at runtime.
main.py imports from here — never the reverse.

PATH RESOLUTION STRATEGY
-------------------------
The VOICE_PROFILES_DIR config value (default: "server/voice_profiles") is
a path relative to the project root (C:\\VoiceForge\\).  When uvicorn is
started from C:\\VoiceForge\\server\\ the naïve join `cwd / dir_setting`
resolves to the wrong path.  _resolve_profiles_dir() tries three candidates
in priority order so the module works regardless of which directory the
server process is started from:

  1. dir_setting as-is (works if CWD == project root, or path is absolute)
  2. __file__/../.. / dir_setting  (parent of server/ == project root)
  3. __file__/.. / "voice_profiles"  (direct sibling — hardcoded last resort)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List, Optional

from config import get_settings
from engine.base_engine import (
    Gender,
    InvalidVoiceProfileError,
    Language,
    VoiceProfile,
)

logger = logging.getLogger(__name__)


class ProfileManager:
    """Manages all voice profiles for VoiceForge.

    Loads profiles from the voice_profiles directory on construction,
    validates them, and provides typed lookup methods.

    Never crashes the server on bad data — individual invalid profiles are
    logged and skipped; the remaining valid profiles are still served.
    """

    def __init__(self) -> None:
        self.settings = get_settings()
        self._profiles: Dict[str, VoiceProfile] = {}
        self._profiles_dir: Optional[Path] = None
        self._reference_audio_dir: Optional[Path] = None
        self._load_all_profiles()

    # ── Path resolution ────────────────────────────────────────────────────────

    def _resolve_profiles_dir(self) -> Path:
        """Resolve the voice profiles directory regardless of server CWD.

        Tries three candidate paths in order and returns the first that exists.
        Raises FileNotFoundError with a helpful message if none exist.

        Returns:
            Absolute Path to the voice_profiles directory.

        Raises:
            FileNotFoundError: If no candidate path exists.
        """
        dir_setting = self.settings.VOICE_PROFILES_DIR

        candidates = [
            # 1. As configured (works if CWD == project root or path is absolute)
            Path(dir_setting),
            # 2. Relative to project root (parent of server/)
            Path(__file__).parent.parent / dir_setting,
            # 3. Direct sibling of profile_manager.py (last resort)
            Path(__file__).parent / "voice_profiles",
        ]

        for candidate in candidates:
            resolved = candidate.resolve()
            if resolved.exists() and resolved.is_dir():
                logger.debug("Voice profiles dir resolved: %s", resolved)
                return resolved

        tried = "\n  ".join(str(c.resolve()) for c in candidates)
        raise FileNotFoundError(
            f"Voice profiles directory not found. Tried:\n  {tried}\n"
            f"Set VOICE_PROFILES_DIR in .env to the correct path."
        )

    def _resolve_reference_audio_dir(self) -> Path:
        """Resolve the reference audio directory regardless of server CWD.

        Uses the same three-candidate strategy as _resolve_profiles_dir().
        Returns the path even if the directory is empty — callers check
        individual file existence, not directory existence.

        Returns:
            Absolute Path to the reference_audio directory (may be empty).
        """
        dir_setting = self.settings.REFERENCE_AUDIO_DIR

        candidates = [
            Path(dir_setting),
            Path(__file__).parent.parent / dir_setting,
            Path(__file__).parent / "reference_audio",
        ]

        for candidate in candidates:
            resolved = candidate.resolve()
            if resolved.exists() and resolved.is_dir():
                logger.debug("Reference audio dir resolved: %s", resolved)
                return resolved

        # If the directory doesn't exist at all, return the most likely path
        # (the first candidate based on project root) — callers handle missing files
        fallback = candidates[1].resolve()
        logger.warning(
            "Reference audio directory not found — voice cloning will not be available. "
            "Expected location: %s", fallback,
        )
        return fallback

    # ── Profile loading ────────────────────────────────────────────────────────

    def _load_all_profiles(self) -> None:
        """Load and validate all .json files from the voice_profiles directory.

        For each .json file:
          - Attempts VoiceProfile.from_json_file()
          - If valid: adds to self._profiles keyed by profile_id
          - If invalid: logs warning and continues (never crashes)

        Logs how many profiles loaded successfully after scanning all files.
        """
        try:
            self._profiles_dir = self._resolve_profiles_dir()
        except FileNotFoundError as exc:
            logger.error("Cannot load voice profiles: %s", exc)
            self._profiles_dir = None
            return

        self._reference_audio_dir = self._resolve_reference_audio_dir()

        json_files = sorted(self._profiles_dir.glob("*.json"))
        if not json_files:
            logger.error(
                "No .json files found in voice profiles directory: %s",
                self._profiles_dir,
            )
            return

        loaded = 0
        for json_path in json_files:
            try:
                profile = VoiceProfile.from_json_file(str(json_path))
                self._profiles[profile.profile_id] = profile
                loaded += 1
                logger.debug("Loaded profile: %s", profile.profile_id)
            except InvalidVoiceProfileError as exc:
                logger.warning(
                    "Skipping invalid voice profile '%s': %s",
                    json_path.name, exc,
                )
            except Exception as exc:
                logger.warning(
                    "Unexpected error loading profile '%s': %s",
                    json_path.name, exc,
                )

        if loaded == 0:
            logger.error(
                "0 voice profiles loaded from %s. "
                "Check that the JSON files are valid and readable.",
                self._profiles_dir,
            )
        else:
            logger.info(
                "Loaded %d/%d voice profiles from %s",
                loaded, len(json_files), self._profiles_dir,
            )

    # ── Public lookup methods ──────────────────────────────────────────────────

    def get_all_profiles(self) -> List[VoiceProfile]:
        """Return all loaded VoiceProfile objects.

        Returns:
            List of VoiceProfile instances (empty if none loaded).
            Never raises.
        """
        return list(self._profiles.values())

    def get_profile_by_id(self, profile_id: str) -> Optional[VoiceProfile]:
        """Return the VoiceProfile for the given profile_id.

        Args:
            profile_id: The profile_id string (e.g. 'anchor_male_en').

        Returns:
            VoiceProfile if found, None if not.
            Never raises.
        """
        return self._profiles.get(profile_id)

    def get_profile_by_language_gender(
        self,
        language: Language,
        gender: Gender,
    ) -> Optional[VoiceProfile]:
        """Return the first profile matching both language and gender.

        Useful when the API receives a language+gender selection instead
        of an explicit profile_id.

        Args:
            language: Language enum value.
            gender: Gender enum value.

        Returns:
            First matching VoiceProfile, or None if no match.
        """
        for profile in self._profiles.values():
            if profile.language == language and profile.gender == gender:
                return profile
        return None

    def get_profiles_for_language(self, language: Language) -> List[VoiceProfile]:
        """Return all profiles for a given language.

        Args:
            language: Language enum value to filter by.

        Returns:
            List of matching VoiceProfile instances (may be empty).
        """
        return [p for p in self._profiles.values() if p.language == language]

    # ── Reference audio helpers ────────────────────────────────────────────────

    def reference_audio_exists(self, profile: VoiceProfile) -> bool:
        """Return True if the reference audio file for this profile exists on disk.

        Args:
            profile: The VoiceProfile to check.

        Returns:
            True if the .wav reference file is present in REFERENCE_AUDIO_DIR.
            False if the directory doesn't exist, the file is missing, or any
            other error occurs. Never raises.
        """
        try:
            if self._reference_audio_dir is None:
                return False
            ref_file = self._reference_audio_dir / profile.reference_audio_filename
            return ref_file.exists() and ref_file.is_file()
        except Exception:
            return False

    def get_reference_audio_path(self, profile: VoiceProfile) -> Optional[str]:
        """Return the absolute path to the reference audio file if it exists.

        Args:
            profile: The VoiceProfile to look up.

        Returns:
            Absolute path string if the file exists, None otherwise.
        """
        try:
            if self._reference_audio_dir is None:
                return None
            ref_file = self._reference_audio_dir / profile.reference_audio_filename
            if ref_file.exists() and ref_file.is_file():
                return str(ref_file)
            return None
        except Exception:
            return None

    # ── API summary ────────────────────────────────────────────────────────────

    def get_profiles_summary(self) -> List[dict]:
        """Return profile metadata as a list of dicts for the /voices API response.

        Each dict contains all profile fields PLUS:
          - ``reference_audio_exists``: bool — whether the .wav file is on disk
          - ``reference_audio_path``: str or None — absolute path if file exists

        Returns:
            List of dicts, one per loaded profile.
        """
        summaries: List[dict] = []
        for profile in self._profiles.values():
            ref_exists = self.reference_audio_exists(profile)
            ref_path = self.get_reference_audio_path(profile)
            summaries.append(
                {
                    "profile_id": profile.profile_id,
                    "display_name": profile.display_name,
                    "language": profile.language.value,
                    "gender": profile.gender.value,
                    "engine_preference": [e.value for e in profile.engine_preference],
                    "reference_audio_filename": profile.reference_audio_filename,
                    "speaking_rate": profile.speaking_rate,
                    "style": profile.style,
                    "description": profile.description,
                    "phase_available": profile.phase_available,
                    "cloning_enabled": profile.cloning_enabled,
                    "notes": profile.notes,
                    "reference_audio_exists": ref_exists,
                    "reference_audio_path": ref_path,
                }
            )
        return summaries

    def __repr__(self) -> str:
        return (
            f"ProfileManager("
            f"profiles={list(self._profiles.keys())}, "
            f"dir={self._profiles_dir})"
        )


# ── Module-level singleton ─────────────────────────────────────────────────────
# Created once on first import; all parts of the app use this instance.

_profile_manager: Optional[ProfileManager] = None


def get_profile_manager() -> ProfileManager:
    """Return the singleton ProfileManager instance.

    Creates it on first call. Safe for concurrent reads — profile data is
    read-only after __init__ completes.

    Returns:
        The singleton ProfileManager instance.
    """
    global _profile_manager
    if _profile_manager is None:
        _profile_manager = ProfileManager()
    return _profile_manager


def reload_profiles() -> ProfileManager:
    """Force a fresh reload of all profiles from disk.

    Discards the current singleton and creates a new ProfileManager.
    Call this after uploading a new reference audio file so that
    reference_audio_exists() reflects the newly uploaded file immediately.

    Returns:
        The new ProfileManager singleton (also accessible via get_profile_manager()).
    """
    global _profile_manager
    _profile_manager = ProfileManager()
    logger.info("Voice profiles reloaded from disk.")
    return _profile_manager

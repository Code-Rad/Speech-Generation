/**
 * lib/constants.ts
 * VoiceForge — UI Constants and Design Tokens
 */

import type { Language } from "./types";

// ── API ────────────────────────────────────────────────────────────────────────

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// ── Language Config ────────────────────────────────────────────────────────────

export const LANGUAGES: {
  value: Language;
  label: string;
  flag: string;
  description: string;
}[] = [
  {
    value: "en",
    label: "English",
    flag: "🇬🇧",
    description: "Standard broadcast English",
  },
  {
    value: "hi",
    label: "Hindi",
    flag: "🇮🇳",
    description: "Standard broadcast Hindi",
  },
  {
    value: "hinglish",
    label: "Hinglish",
    flag: "🔀",
    description: "Mixed Hindi-English",
  },
];

// ── Engine Display Config ──────────────────────────────────────────────────────

export const ENGINE_LABELS: Record<string, string> = {
  edge_tts: "Edge TTS",
  xtts_v2: "XTTS v2",
  voxtral_tts: "Voxtral TTS",
  fish_s2_pro: "Fish S2 Pro",
};

export const ENGINE_ORDER = [
  "edge_tts",
  "xtts_v2",
  "voxtral_tts",
  "fish_s2_pro",
];

// ── Text Limits ────────────────────────────────────────────────────────────────

export const TEXT_MIN_LENGTH = 10;
export const TEXT_MAX_LENGTH = 5000;
export const TEXT_WARNING_LENGTH = 4000;

// ── Speaking Rate ─────────────────────────────────────────────────────────────

export const SPEAKING_RATE_MIN = 0.5;
export const SPEAKING_RATE_MAX = 2.0;
export const SPEAKING_RATE_DEFAULT = 1.0;

// ── Polling ────────────────────────────────────────────────────────────────────

export const ENGINE_POLL_INTERVAL_MS = 15_000;

// ── Design System ─────────────────────────────────────────────────────────────

export const STATUS_COLORS = {
  available: "text-emerald-400",
  unavailable: "text-amber-400",
  not_built: "text-slate-500",
  error: "text-red-400",
} as const;

export const STATUS_ICONS = {
  available: "✅",
  unavailable: "⚠️",
  not_built: "🔲",
  error: "❌",
} as const;

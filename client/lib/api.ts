/**
 * lib/api.ts
 * VoiceForge — API Client Functions
 * All functions call the FastAPI backend at NEXT_PUBLIC_API_URL.
 */

import { API_BASE_URL } from "./constants";
import type {
  CloneVoiceResponse,
  Engine,
  GenerateRequest,
  GenerateResponse,
  HealthResponse,
  VoiceProfile,
} from "./types";

// ── Generic fetch helper ───────────────────────────────────────────────────────

async function apiFetch<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const url = `${API_BASE_URL}${path}`;
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  if (!res.ok) {
    let message = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      if (typeof body.detail === "string") message = body.detail;
      else if (typeof body.detail?.error === "string") message = body.detail.error;
    } catch {
      // ignore parse error
    }
    throw new Error(message);
  }

  return res.json() as Promise<T>;
}

// ── Health ─────────────────────────────────────────────────────────────────────

export async function fetchHealth(): Promise<HealthResponse> {
  return apiFetch<HealthResponse>("/health");
}

// ── Engines ────────────────────────────────────────────────────────────────────

export async function fetchEngines(): Promise<Engine[]> {
  return apiFetch<Engine[]>("/engines");
}

// ── Voice Profiles ─────────────────────────────────────────────────────────────

export async function fetchVoices(): Promise<VoiceProfile[]> {
  return apiFetch<VoiceProfile[]>("/voices");
}

// ── Generate ───────────────────────────────────────────────────────────────────

/**
 * POST /generate — returns { meta, blob }.
 *
 * The server returns audio bytes in the response body and metadata in
 * individual response headers (x-engine-used, x-is-draft, x-profile-id,
 * x-duration, x-generation-time).  Headers may be absent in some CORS
 * configurations, so every read falls back gracefully — we never throw
 * just because a header is missing.  We only throw if:
 *   • response.ok is false  (server returned an error status)
 *   • blob.size === 0       (body is empty / corrupted)
 */
export async function generateSpeech(
  payload: GenerateRequest
): Promise<{ meta: GenerateResponse; blob: Blob }> {
  const url = `${API_BASE_URL}/generate`;

  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    let message = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      if (typeof body.detail === "string") message = body.detail;
      else if (typeof body.detail?.error === "string") message = body.detail.error;
    } catch {
      // ignore parse error — keep the HTTP status message
    }
    throw new Error(message);
  }

  // Read the audio bytes first so we can use blob.size for file_size_bytes
  const blob = await res.blob();

  if (!blob || blob.size === 0) {
    throw new Error("Server returned empty audio file");
  }

  // ── Read individual headers with graceful fallbacks ─────────────────────────
  // Browsers silently hide headers not listed in Access-Control-Expose-Headers,
  // so we never throw here — we always return usable metadata.

  const engineUsed =
    res.headers.get("x-engine-used") ||
    res.headers.get("X-Engine-Used") ||
    "edge_tts";

  const isDraftRaw =
    res.headers.get("x-is-draft") ||
    res.headers.get("X-Is-Draft");
  const fallbackUsed =
    isDraftRaw !== null ? isDraftRaw.toLowerCase() === "true" : true;

  const profileId =
    res.headers.get("x-profile-id") ||
    res.headers.get("X-Profile-Id") ||
    payload.profile_id;

  const durationRaw =
    res.headers.get("x-duration") ||
    res.headers.get("X-Duration");
  const durationSeconds = durationRaw ? parseFloat(durationRaw) : 0;

  const genTimeRaw =
    res.headers.get("x-generation-time") ||
    res.headers.get("X-Generation-Time");
  const generationTimeMs = genTimeRaw ? parseInt(genTimeRaw, 10) : 0;

  const outputFormat = (payload.output_format ?? "wav") as "wav" | "mp3";

  // ── Synthesise a full GenerateResponse from available data ──────────────────
  const meta: GenerateResponse = {
    request_id: crypto.randomUUID(),
    profile_id: profileId,
    engine_used: engineUsed,
    output_format: outputFormat,
    duration_seconds: durationSeconds,
    file_size_bytes: blob.size,
    generation_time_ms: generationTimeMs,
    audio_url: "",
    text_length: payload.text.length,
    language: payload.language_override ?? "en",
    fallback_used: fallbackUsed,
    fallback_reason: fallbackUsed ? "Primary engine unavailable — used fallback" : undefined,
  };

  return { meta, blob };
}

// ── Clone Voice ────────────────────────────────────────────────────────────────

export async function cloneVoice(
  profileId: string,
  audioFile: File
): Promise<{ message: string; profile_id: string; filename: string }> {
  const url = `${API_BASE_URL}/clone-voice`;
  const form = new FormData();
  form.append("profile_id", profileId);
  form.append("audio_file", audioFile);

  const res = await fetch(url, { method: "POST", body: form });

  if (!res.ok) {
    let message = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      if (typeof body.detail === "string") message = body.detail;
      else if (typeof body.detail?.error === "string") message = body.detail.error;
    } catch {
      // ignore
    }
    throw new Error(message);
  }

  return res.json();
}

// ── Upload Reference Audio ─────────────────────────────────────────────────────

export async function uploadReferenceAudio(
  profileId: string,
  audioFile: File,
  generateSample: boolean = true
): Promise<CloneVoiceResponse> {
  const url = `${API_BASE_URL}/clone-voice`;
  const form = new FormData();
  form.append("profile_id", profileId);
  form.append("audio_file", audioFile);
  form.append("generate_sample", String(generateSample));

  const res = await fetch(url, { method: "POST", body: form });

  if (!res.ok) {
    let message = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      if (typeof body.detail === "string") message = body.detail;
      else if (typeof body.detail?.error === "string") message = body.detail.error;
    } catch {
      // ignore
    }
    throw new Error(message);
  }

  return res.json() as Promise<CloneVoiceResponse>;
}

// ── Delete Reference Audio ─────────────────────────────────────────────────────

export async function deleteReferenceAudio(
  _profileId: string
): Promise<void> {
  throw new Error(
    "Not implemented in Phase 1 — reference audio deletion coming in a future update"
  );
}

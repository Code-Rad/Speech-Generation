/**
 * lib/types.ts
 * VoiceForge — Shared TypeScript type definitions
 * All types mirror the FastAPI Pydantic schemas exactly.
 */

// ── Engine Types ───────────────────────────────────────────────────────────────

export type EngineStatus = "available" | "unavailable" | "not_built" | "error";

export interface Engine {
  engine_type: string;
  display_name: string;
  status: EngineStatus;
  supports_cloning: boolean;
  supported_languages: string[];
  model_loaded: boolean;
  vram_mb?: number | null;
  notes?: string;
}

// ── Voice Profile Types ────────────────────────────────────────────────────────

export type Language = "en" | "hi" | "hinglish";
export type Gender = "male" | "female";

export interface VoiceProfile {
  profile_id: string;
  display_name: string;
  language: Language;
  gender: Gender;
  engine_preference: string[];
  reference_audio_filename: string;
  speaking_rate: number;
  style: string;
  description: string;
  phase_available: number;
  cloning_enabled: boolean;
  has_reference_audio: boolean;
  notes?: string;
}

// ── Generation Types ───────────────────────────────────────────────────────────

export type OutputFormat = "wav" | "mp3";

export interface GenerateRequest {
  text: string;
  profile_id: string;
  output_format?: OutputFormat;
  speaking_rate?: number;
  language_override?: Language;
}

export interface GenerateResponse {
  request_id: string;
  profile_id: string;
  engine_used: string;
  output_format: OutputFormat;
  duration_seconds: number;
  file_size_bytes: number;
  generation_time_ms: number;
  audio_url: string;
  text_length: number;
  language: Language;
  fallback_used: boolean;
  fallback_reason?: string;
}

// ── API Error Types ────────────────────────────────────────────────────────────

export interface ApiError {
  error: string;
  detail?: string;
  profile_id?: string;
  engine?: string;
}

// ── Health Types ───────────────────────────────────────────────────────────────

export interface HealthResponse {
  status: string;
  version: string;
  phase: number;
  uptime_seconds: number;
  started_at: string;
  engines_loaded: number;
  engines_available: number;
}

// ── UI State Types ─────────────────────────────────────────────────────────────

export type GenerationState = "idle" | "generating" | "success" | "error";

export interface GenerationResult {
  meta: GenerateResponse;
  blobUrl: string;
}

// ── Clone Voice Response ───────────────────────────────────────────────────────

export interface CloneVoiceResponse {
  success: boolean;
  profile_id: string;
  reference_audio_saved: boolean;
  duration_seconds: number;
  sample_rate?: number;
  warnings: string[];
  sample_generated: boolean;
  sample_audio_path?: string;
  sample_engine_used?: string;
  message: string;
  error?: string;
}

// ── Generation History ─────────────────────────────────────────────────────────

export interface GenerationHistory {
  id: string;
  timestamp: string;
  profile_id: string;
  profile_display_name: string;
  language: string;
  text_preview: string;
  engine_used: string;
  is_draft: boolean;
  duration_seconds: number;
  file_size_bytes: number;
  generation_time_ms: number;
}

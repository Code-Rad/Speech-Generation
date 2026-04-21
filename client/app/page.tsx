"use client";

/**
 * app/page.tsx
 * VoiceForge — Main Speech Generator Page
 *
 * Layout (header/footer provided by app/layout.tsx):
 *   ├─ EngineStatusStrip (live polling)
 *   └─ Two-column grid (lg+)
 *      ├─ LEFT: Script input + Language selector + Speaking rate + Generate button
 *      └─ RIGHT: Voice profile selector grid + AudioPlayer (on success)
 *
 * Query param: ?profile=<profile_id> — pre-selects a voice profile on load
 * (used when navigating here from the Voices page after cloning a voice)
 */

import { Suspense, useCallback, useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { motion } from "framer-motion";
import { AlertCircle, Zap } from "lucide-react";

import EngineStatusStrip from "@/components/EngineStatusStrip";
import LanguageSelector from "@/components/LanguageSelector";
import VoiceProfileCard from "@/components/VoiceProfileCard";
import ScriptInput from "@/components/ScriptInput";
import GenerateButton from "@/components/GenerateButton";
import AudioPlayer from "@/components/AudioPlayer";

import { fetchVoices, generateSpeech } from "@/lib/api";
import { SPEAKING_RATE_DEFAULT, SPEAKING_RATE_MAX, SPEAKING_RATE_MIN, TEXT_MAX_LENGTH, TEXT_MIN_LENGTH } from "@/lib/constants";
import type {
  GenerationHistory,
  GenerationResult,
  GenerationState,
  Language,
  VoiceProfile,
} from "@/lib/types";

// ─────────────────────────────────────────────────────────────────────────────

/** Inner component that uses useSearchParams (must be inside Suspense) */
function GeneratorInner() {
  const searchParams = useSearchParams();

  // ── State ────────────────────────────────────────────────────────────────────
  const [voices, setVoices] = useState<VoiceProfile[]>([]);
  const [voicesLoading, setVoicesLoading] = useState(true);
  const [voicesError, setVoicesError] = useState<string | null>(null);

  const [language, setLanguage] = useState<Language>("en");
  const [selectedProfileId, setSelectedProfileId] = useState<string | null>(null);
  const [script, setScript] = useState("");
  const [speakingRate, setSpeakingRate] = useState<number>(SPEAKING_RATE_DEFAULT);

  const [genState, setGenState] = useState<GenerationState>("idle");
  const [genError, setGenError] = useState<string | null>(null);
  const [result, setResult] = useState<GenerationResult | null>(null);

  // Track previous blob URL so we can revoke it when replaced
  const prevBlobUrlRef = useRef<string | null>(null);

  // ── Load voices ───────────────────────────────────────────────────────────────
  useEffect(() => {
    // Set page title
    document.title = "Generator — VoiceForge";

    fetchVoices()
      .then((data) => {
        setVoices(data);

        // Check for ?profile= query param first — Voices page shortcut
        const requestedProfile = searchParams.get("profile");
        if (requestedProfile) {
          const match = data.find((v) => v.profile_id === requestedProfile);
          if (match) {
            setSelectedProfileId(match.profile_id);
            setLanguage(match.language as Language);
            return;
          }
        }

        // Auto-select first profile matching current language
        const first = data.find((v) => v.language === "en");
        if (first) setSelectedProfileId(first.profile_id);
      })
      .catch((err) => {
        setVoicesError(
          err instanceof Error ? err.message : "Failed to load voices"
        );
      })
      .finally(() => setVoicesLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── Auto-select profile when language changes ─────────────────────────────────
  useEffect(() => {
    const filtered = voices.filter((v) => v.language === language);
    const currentValid = filtered.find((v) => v.profile_id === selectedProfileId);
    if (!currentValid && filtered.length > 0) {
      setSelectedProfileId(filtered[0].profile_id);
    }
  }, [language, voices, selectedProfileId]);

  // ── Clean up blob URLs on unmount ─────────────────────────────────────────────
  useEffect(() => {
    return () => {
      if (prevBlobUrlRef.current) URL.revokeObjectURL(prevBlobUrlRef.current);
      if (result?.blobUrl) URL.revokeObjectURL(result.blobUrl);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── Generate ──────────────────────────────────────────────────────────────────
  const handleGenerate = useCallback(async () => {
    if (!selectedProfileId) return;

    const trimmed = script.trim();
    if (trimmed.length < TEXT_MIN_LENGTH) {
      setGenError(`Script must be at least ${TEXT_MIN_LENGTH} characters.`);
      return;
    }
    if (trimmed.length > TEXT_MAX_LENGTH) {
      setGenError(`Script exceeds ${TEXT_MAX_LENGTH.toLocaleString()} character limit.`);
      return;
    }

    setGenState("generating");
    setGenError(null);

    // Revoke previous audio blob
    if (prevBlobUrlRef.current) {
      URL.revokeObjectURL(prevBlobUrlRef.current);
      prevBlobUrlRef.current = null;
    }
    setResult(null);

    try {
      const { meta, blob } = await generateSpeech({
        text: trimmed,
        profile_id: selectedProfileId,
        output_format: "wav",
        speaking_rate: speakingRate,
      });

      const blobUrl = URL.createObjectURL(blob);
      prevBlobUrlRef.current = blobUrl;

      setResult({ meta, blobUrl });

      // ── Save to generation history (localStorage) ───────────────────────
      try {
        const selectedProfile = voices.find(
          (p) => p.profile_id === selectedProfileId
        );
        const historyItem: GenerationHistory = {
          id: crypto.randomUUID(),
          timestamp: new Date().toISOString(),
          profile_id: selectedProfileId ?? "",
          profile_display_name:
            selectedProfile?.display_name ?? selectedProfileId ?? "",
          language: language,
          text_preview: trimmed.slice(0, 100),
          engine_used: meta.engine_used,
          is_draft: meta.fallback_used,
          duration_seconds: meta.duration_seconds,
          file_size_bytes: meta.file_size_bytes,
          generation_time_ms: meta.generation_time_ms,
        };
        const existing: GenerationHistory[] = JSON.parse(
          localStorage.getItem("voiceforge_history") ?? "[]"
        );
        localStorage.setItem(
          "voiceforge_history",
          JSON.stringify([historyItem, ...existing].slice(0, 50))
        );
      } catch {
        // localStorage may be unavailable (private browsing etc.) — silent fail
      }

      setGenState("success");
    } catch (err) {
      setGenError(
        err instanceof Error ? err.message : "Generation failed. Check server."
      );
      setGenState("error");
    }
  }, [selectedProfileId, script, speakingRate, voices, language]);

  // ── Filtered profiles ─────────────────────────────────────────────────────────
  const filteredProfiles = voices.filter((v) => v.language === language);

  // ── Validation ────────────────────────────────────────────────────────────────
  const canGenerate =
    !!selectedProfileId &&
    script.trim().length >= TEXT_MIN_LENGTH &&
    script.trim().length <= TEXT_MAX_LENGTH &&
    genState !== "generating";

  // ─────────────────────────────────────────────────────────────────────────────

  return (
    <motion.main
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
      className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6"
    >
      {/* Engine status strip */}
      <EngineStatusStrip />

      {/* Hero headline */}
      <div className="text-center py-4">
        <h1 className="font-display text-3xl sm:text-4xl font-bold text-white tracking-tight mb-2">
          Broadcast-Quality{" "}
          <span className="text-indigo-400">Speech Generation</span>
        </h1>
        <p className="text-sm text-white/40 max-w-xl mx-auto">
          Professional news anchor voices in English, Hindi, and Hinglish.
          Powered by XTTS&nbsp;v2 with Edge&nbsp;TTS fallback.
        </p>
      </div>

      {/* ── Two-column grid ──────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
        {/* ── LEFT COLUMN ─────────────────────────────────────────────────── */}
        <div className="space-y-5">
          {/* Panel */}
          <div className="bg-surface border border-white/5 rounded-2xl p-6 space-y-5">
            {/* Language selector */}
            <LanguageSelector
              selected={language}
              onChange={setLanguage}
              disabled={genState === "generating"}
            />

            {/* Divider */}
            <div className="h-px bg-white/5" />

            {/* Script input */}
            <ScriptInput
              value={script}
              onChange={setScript}
              disabled={genState === "generating"}
              error={
                genState === "error" && genError && !genError.includes("Server")
                  ? genError
                  : null
              }
            />

            {/* Speaking rate */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <label className="text-xs font-medium text-white/40 uppercase tracking-widest">
                  Speaking Rate
                </label>
                <span className="text-xs tabular-nums text-white/60 font-mono">
                  {speakingRate.toFixed(2)}×
                </span>
              </div>
              <input
                type="range"
                min={SPEAKING_RATE_MIN}
                max={SPEAKING_RATE_MAX}
                step={0.05}
                value={speakingRate}
                onChange={(e) => setSpeakingRate(parseFloat(e.target.value))}
                disabled={genState === "generating"}
                className="w-full h-1.5 rounded-full appearance-none bg-white/10 cursor-pointer accent-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
                aria-label="Speaking rate"
              />
              <div className="flex justify-between text-xs text-white/25">
                <span>{SPEAKING_RATE_MIN}× slow</span>
                <span>normal</span>
                <span>{SPEAKING_RATE_MAX}× fast</span>
              </div>
            </div>
          </div>

          {/* Generate button */}
          <GenerateButton
            state={genState}
            onClick={handleGenerate}
            disabled={!canGenerate}
            selectedProfile={selectedProfileId}
          />

          {/* Server error message */}
          {genState === "error" && genError && (
            <div className="flex items-start gap-2.5 bg-red-500/8 border border-red-500/20 rounded-xl px-4 py-3">
              <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0 mt-0.5" />
              <p className="text-sm text-red-300">{genError}</p>
            </div>
          )}

          {/* Audio player — appears after successful generation */}
          {result && genState === "success" && (
            <AudioPlayer result={result} />
          )}
        </div>

        {/* ── RIGHT COLUMN ────────────────────────────────────────────────── */}
        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <Zap className="w-4 h-4 text-indigo-400" />
            <h2 className="text-sm font-medium text-white/60">
              Voice Profiles
            </h2>
            <span className="ml-auto text-xs text-white/30">
              {filteredProfiles.length} for{" "}
              {language === "hinglish"
                ? "Hinglish"
                : language === "hi"
                ? "Hindi"
                : "English"}
            </span>
          </div>

          {/* Loading skeletons */}
          {voicesLoading && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {[0, 1, 2, 3].map((i) => (
                <div
                  key={i}
                  className="h-32 rounded-xl bg-white/4 animate-pulse border border-white/5"
                />
              ))}
            </div>
          )}

          {/* Voices error */}
          {voicesError && (
            <div className="flex items-start gap-2.5 bg-red-500/8 border border-red-500/20 rounded-xl px-4 py-3">
              <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-sm text-red-300 font-medium">Could not load voice profiles</p>
                <p className="text-xs text-red-400/70 mt-1">{voicesError}</p>
              </div>
            </div>
          )}

          {/* Profile grid */}
          {!voicesLoading && !voicesError && filteredProfiles.length === 0 && (
            <div className="text-center py-12 text-white/30 text-sm">
              No profiles available for this language.
            </div>
          )}

          {!voicesLoading && !voicesError && filteredProfiles.length > 0 && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {filteredProfiles.map((profile) => (
                <VoiceProfileCard
                  key={profile.profile_id}
                  profile={profile}
                  selected={profile.profile_id === selectedProfileId}
                  onSelect={setSelectedProfileId}
                  disabled={genState === "generating"}
                />
              ))}
            </div>
          )}

          {/* Selected profile detail */}
          {selectedProfileId && !voicesLoading && (
            <div className="bg-surface border border-white/5 rounded-xl px-4 py-3">
              <p className="text-xs text-white/30 mb-1">Selected profile</p>
              {(() => {
                const p = voices.find((v) => v.profile_id === selectedProfileId);
                if (!p) return null;
                return (
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-white/70 font-medium">{p.display_name}</span>
                    <div className="flex items-center gap-1.5">
                      {p.has_reference_audio ? (
                        <span className="text-xs text-emerald-400">🎙 Reference loaded</span>
                      ) : (
                        <span className="text-xs text-amber-400">⚠ No reference audio</span>
                      )}
                    </div>
                  </div>
                );
              })()}
            </div>
          )}
        </div>
      </div>
    </motion.main>
  );
}

// ─────────────────────────────────────────────────────────────────────────────

/** Wrap inner component in Suspense (required by useSearchParams in App Router) */
export default function GeneratorPage() {
  return (
    <Suspense fallback={
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="h-10 w-full rounded-xl bg-white/4 animate-pulse mb-6" />
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="space-y-4">
            {[0, 1, 2].map((i) => (
              <div key={i} className="h-24 rounded-xl bg-white/4 animate-pulse" />
            ))}
          </div>
          <div className="space-y-3">
            {[0, 1, 2, 3].map((i) => (
              <div key={i} className="h-32 rounded-xl bg-white/4 animate-pulse" />
            ))}
          </div>
        </div>
      </div>
    }>
      <GeneratorInner />
    </Suspense>
  );
}

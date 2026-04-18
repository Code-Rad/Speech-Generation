"use client";

/**
 * app/voices/page.tsx
 * VoiceForge — Voice Manager
 * Record or upload reference audio for each anchor voice profile.
 * Saved voices persist on the server in server/reference_audio/.
 */

import { useCallback, useEffect, useState } from "react";
import { Mic2, Radio } from "lucide-react";
import { fetchVoices } from "@/lib/api";
import type { VoiceProfile } from "@/lib/types";
import EngineStatusStrip from "@/components/EngineStatusStrip";
import VoiceProfileManagerCard from "@/components/VoiceProfileManagerCard";
import { Toast, useToast } from "@/components/Toast";

const NAV = [
  { label: "Generator", href: "/" },
  { label: "Voices", href: "/voices", active: true },
  { label: "History", href: "/history" },
  { label: "Engines", href: "/engines" },
];

export default function VoicesPage() {
  const [profiles, setProfiles] = useState<VoiceProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { toasts, addToast, dismiss } = useToast();

  const loadProfiles = useCallback(async () => {
    try {
      const data = await fetchVoices();
      setProfiles(data);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to load voice profiles"
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadProfiles();
  }, [loadProfiles]);

  // Called by each card after a successful upload
  const handleCloned = useCallback((profileId: string) => {
    setProfiles((prev) =>
      prev.map((p) =>
        p.profile_id === profileId
          ? { ...p, has_reference_audio: true }
          : p
      )
    );
  }, []);

  const clonedCount = profiles.filter((p) => p.has_reference_audio).length;
  const totalCount = profiles.length;

  return (
    <div className="min-h-dvh bg-background bg-grid">
      {/* Toast container */}
      <Toast toasts={toasts} onDismiss={dismiss} />

      {/* ── Header ──────────────────────────────────────────────────────────── */}
      <header className="sticky top-0 z-40 border-b border-white/5 bg-background/80 backdrop-blur-xl">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-14 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-lg bg-indigo-600 flex items-center justify-center">
              <Radio className="w-4 h-4 text-white" />
            </div>
            <span className="font-display font-semibold text-white tracking-tight">
              VoiceForge
            </span>
            <span className="text-xs px-1.5 py-0.5 rounded bg-white/8 text-white/40 border border-white/8 font-mono">
              Phase 1
            </span>
          </div>
          <nav className="hidden sm:flex items-center gap-1">
            {NAV.map(({ label, href, active }) => (
              <a
                key={href}
                href={href}
                className={`px-3 py-1.5 rounded-lg text-sm transition-colors ${
                  active
                    ? "text-white bg-white/8"
                    : "text-white/50 hover:text-white/80 hover:bg-white/5"
                }`}
              >
                {label}
              </a>
            ))}
          </nav>
        </div>
      </header>

      {/* ── Main ────────────────────────────────────────────────────────────── */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        <EngineStatusStrip />

        {/* Page title */}
        <div>
          <div className="flex items-center gap-3 mb-1">
            <Mic2 className="w-5 h-5 text-indigo-400" />
            <h1 className="font-display text-2xl font-bold text-white">
              Voice Manager
            </h1>
          </div>
          <p className="text-sm text-white/40 ml-8">
            Record or upload a reference voice for each anchor profile.
            Saved voices persist and are used for all future generations.
          </p>
        </div>

        {/* Stats row */}
        {!loading && !error && totalCount > 0 && (
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-emerald-400" />
              <span className="text-sm text-white/60">
                <span className="text-white font-semibold tabular-nums">
                  {clonedCount}
                </span>{" "}
                / {totalCount} voices cloned
              </span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-indigo-400" />
              <span className="text-sm text-white/60">
                <span className="text-white font-semibold tabular-nums">
                  {totalCount}
                </span>{" "}
                profiles active
              </span>
            </div>
          </div>
        )}

        {/* Loading skeletons */}
        {loading && (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {Array.from({ length: 6 }).map((_, i) => (
              <div
                key={i}
                className="h-52 rounded-2xl bg-white/[0.03] border border-white/5 animate-pulse"
              />
            ))}
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="bg-red-500/8 border border-red-500/20 rounded-xl px-5 py-4">
            <p className="text-sm text-red-300 font-medium">
              Could not load voice profiles
            </p>
            <p className="text-xs text-red-400/70 mt-1">{error}</p>
          </div>
        )}

        {/* Profile grid */}
        {!loading && !error && (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {profiles.map((profile) => (
              <VoiceProfileManagerCard
                key={profile.profile_id}
                profile={profile}
                onCloned={handleCloned}
                onToast={addToast}
              />
            ))}
          </div>
        )}
      </main>

      {/* ── Footer ──────────────────────────────────────────────────────────── */}
      <footer className="border-t border-white/5 mt-16 py-6">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center justify-between text-xs text-white/20">
          <span>VoiceForge — Phase 1 · TRIJYA-7</span>
          <span>XTTS v2 · Edge TTS · FastAPI</span>
        </div>
      </footer>
    </div>
  );
}

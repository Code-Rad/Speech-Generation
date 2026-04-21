"use client";

/**
 * app/voices/page.tsx
 * VoiceForge — Voice Manager
 * Record or upload reference audio for each anchor voice profile.
 * Saved voices persist on the server in server/reference_audio/.
 *
 * After a successful clone, shows a shortcut button that navigates to
 * the generator with that profile pre-selected: router.push('/?profile=...')
 * Header/footer provided by app/layout.tsx.
 */

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { Mic2 } from "lucide-react";
import { fetchVoices } from "@/lib/api";
import type { VoiceProfile } from "@/lib/types";
import EngineStatusStrip from "@/components/EngineStatusStrip";
import VoiceProfileManagerCard from "@/components/VoiceProfileManagerCard";
import { Toast, useToast } from "@/components/Toast";

export default function VoicesPage() {
  const router = useRouter();
  const [profiles, setProfiles] = useState<VoiceProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  // Track most recently cloned profile for the "→ Generate" shortcut
  const [lastClonedId, setLastClonedId] = useState<string | null>(null);
  const { toasts, addToast, dismiss } = useToast();

  useEffect(() => {
    document.title = "Voices — VoiceForge";
  }, []);

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
    setLastClonedId(profileId);
  }, []);

  const clonedCount = profiles.filter((p) => p.has_reference_audio).length;
  const totalCount = profiles.length;

  return (
    <>
      {/* Toast container */}
      <Toast toasts={toasts} onDismiss={dismiss} />

      <motion.main
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.2 }}
        className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6"
      >
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

        {/* "→ Generate speech with this voice" shortcut — appears after cloning */}
        {lastClonedId && (
          <motion.div
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex items-center gap-3 bg-emerald-500/10 border border-emerald-500/25 rounded-xl px-4 py-3"
          >
            <span className="text-emerald-400 text-sm">✓</span>
            <p className="text-sm text-emerald-300 flex-1">
              Voice cloned successfully.
            </p>
            <button
              onClick={() => router.push(`/?profile=${lastClonedId}`)}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-500/20 hover:bg-emerald-500/30 border border-emerald-500/30 text-emerald-300 text-xs font-medium rounded-lg transition-colors flex-shrink-0"
            >
              → Generate speech with this voice
            </button>
          </motion.div>
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
      </motion.main>
    </>
  );
}

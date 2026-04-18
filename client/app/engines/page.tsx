"use client";

/**
 * app/engines/page.tsx
 * VoiceForge — Engine Status Dashboard
 * Live status of all 4 TTS engines with Phase 1/2 grouping.
 */

import { useCallback, useEffect, useState } from "react";
import { Activity, Radio, RefreshCw } from "lucide-react";
import { fetchEngines } from "@/lib/api";
import type { Engine } from "@/lib/types";
import EngineCard from "@/components/EngineCard";
import EngineStatusStrip from "@/components/EngineStatusStrip";

const PHASE1_ENGINES = ["edge_tts", "xtts_v2"];
const PHASE2_ENGINES = ["voxtral_tts", "fish_s2_pro"];

const NAV = [
  { label: "Generator", href: "/" },
  { label: "Voices", href: "/voices" },
  { label: "History", href: "/history" },
  { label: "Engines", href: "/engines", active: true },
];

export default function EnginesPage() {
  const [engines, setEngines] = useState<Engine[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const load = useCallback(async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    else setLoading(true);
    try {
      const data = await fetchEngines();
      setEngines(data);
      setLastUpdated(new Date());
      setError(null);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to load engine status"
      );
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const phase1 = engines.filter((e) =>
    PHASE1_ENGINES.includes(e.engine_type)
  );
  const phase2 = engines.filter((e) =>
    PHASE2_ENGINES.includes(e.engine_type)
  );
  const availableCount = engines.filter((e) => e.status === "available").length;

  return (
    <div className="min-h-dvh bg-background bg-grid">
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
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        <EngineStatusStrip />

        {/* Page header */}
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-3 mb-1">
              <Activity className="w-5 h-5 text-indigo-400" />
              <h1 className="font-display text-2xl font-bold text-white">
                Engine Status
              </h1>
            </div>
            <p className="text-sm text-white/40 ml-8">
              Live status of all TTS engines. Phase 1 engines are active.
              Phase 2 engines require WSL2 setup on TRIJYA-7.
            </p>
          </div>
          <button
            onClick={() => load(true)}
            disabled={refreshing || loading}
            className="flex items-center gap-1.5 px-3 py-2 bg-white/5 hover:bg-white/10 border border-white/10 text-white/50 text-sm rounded-xl transition-colors disabled:opacity-50 flex-shrink-0"
          >
            <RefreshCw
              className={`w-3.5 h-3.5 ${refreshing ? "animate-spin" : ""}`}
            />
            Refresh
          </button>
        </div>

        {/* Last updated + summary */}
        {lastUpdated && !loading && (
          <p className="text-xs text-white/25">
            Last updated: {lastUpdated.toLocaleTimeString()} ·{" "}
            <span className="text-white/40">
              {availableCount}/{engines.length} engines available
            </span>
          </p>
        )}

        {/* Error */}
        {error && (
          <div className="bg-red-500/8 border border-red-500/20 rounded-xl px-5 py-4">
            <p className="text-sm text-red-300">{error}</p>
          </div>
        )}

        {/* Skeletons */}
        {loading && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {[0, 1, 2, 3].map((i) => (
              <div
                key={i}
                className="h-56 rounded-2xl bg-white/[0.03] border border-white/5 animate-pulse"
              />
            ))}
          </div>
        )}

        {/* ── Phase 1 ─────────────────────────────────────────────────────── */}
        {!loading && phase1.length > 0 && (
          <section className="space-y-4">
            <div>
              <h2 className="text-base font-semibold text-white">
                Phase 1 — Active Now
              </h2>
              <p className="text-xs text-white/35 mt-0.5">
                Running natively on Windows · No WSL2 required
              </p>
            </div>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {phase1.map((eng) => (
                <EngineCard key={eng.engine_type} engine={eng} phase={1} />
              ))}
            </div>
          </section>
        )}

        {/* ── Phase 2 ─────────────────────────────────────────────────────── */}
        {!loading && (
          <section className="space-y-4">
            <div>
              <div className="flex items-center gap-2 mb-0.5">
                <h2 className="text-base font-semibold text-white/50">
                  Phase 2 — Coming Soon
                </h2>
                <span className="text-xs px-2 py-0.5 rounded-full bg-white/5 border border-white/10 text-white/30">
                  WSL2 required
                </span>
              </div>
              <p className="text-xs text-white/25">
                Requires WSL2 setup on TRIJYA-7 · Activated in P12 / P13
              </p>
            </div>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {phase2.length > 0 ? (
                phase2.map((eng) => (
                  <EngineCard key={eng.engine_type} engine={eng} phase={2} />
                ))
              ) : (
                // Placeholder cards when server doesn't return phase 2 engines
                PHASE2_ENGINES.map((key) => (
                  <div
                    key={key}
                    className="rounded-2xl border border-white/5 bg-[#12121a] p-5 opacity-40"
                  >
                    <p className="text-sm font-medium text-white/50 capitalize">
                      {key.replace(/_/g, " ")}
                    </p>
                    <p className="text-xs text-white/25 mt-1">
                      Not yet built · Phase 2
                    </p>
                  </div>
                ))
              )}
            </div>
          </section>
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

"use client";

/**
 * components/EngineStatusStrip.tsx
 * VoiceForge — Live engine health strip.
 * Polls /engines every 15s for engine statuses.
 * Also polls /health to detect backend offline state.
 * Shows an offline warning banner when backend is unreachable.
 */

import { useCallback, useEffect, useState } from "react";
import { fetchEngines, fetchHealth } from "@/lib/api";
import {
  ENGINE_LABELS,
  ENGINE_ORDER,
  ENGINE_POLL_INTERVAL_MS,
  STATUS_COLORS,
  STATUS_ICONS,
} from "@/lib/constants";
import type { Engine } from "@/lib/types";

interface EngineStatusStripProps {
  onEnginesUpdate?: (engines: Engine[]) => void;
}

export default function EngineStatusStrip({
  onEnginesUpdate,
}: EngineStatusStripProps) {
  const [engines, setEngines] = useState<Engine[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  // Backend offline detection via /health
  const [backendOffline, setBackendOffline] = useState(false);

  const loadEngines = useCallback(async () => {
    // Check /health first — if it fails, backend is offline
    try {
      await fetchHealth();
      setBackendOffline(false);
    } catch {
      setBackendOffline(true);
      setLoading(false);
      setError("Backend offline");
      return;
    }

    // Backend is up — load engine list
    try {
      const data = await fetchEngines();
      setEngines(data);
      setError(null);
      setLastUpdated(new Date());
      onEnginesUpdate?.(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load engines");
    } finally {
      setLoading(false);
    }
  }, [onEnginesUpdate]);

  useEffect(() => {
    loadEngines();
    const interval = setInterval(loadEngines, ENGINE_POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [loadEngines]);

  const engineMap = Object.fromEntries(
    engines.map((e) => [e.engine_type, e])
  );

  return (
    <div className="space-y-2">
      {/* ── Backend offline banner ──────────────────────────────────────────── */}
      {backendOffline && (
        <div className="flex items-center gap-3 bg-red-500/10 border border-red-500/30 rounded-xl px-4 py-3">
          <span className="text-red-400 text-sm flex-shrink-0">⚠</span>
          <p className="text-sm text-red-300">
            Backend offline — connect to TRIJYA-7 via Tailscale to enable
            speech generation
          </p>
          <button
            onClick={loadEngines}
            className="ml-auto text-xs text-red-400/70 hover:text-red-300 transition-colors flex-shrink-0 underline underline-offset-2"
          >
            Retry
          </button>
        </div>
      )}

      {/* ── Engine status strip ─────────────────────────────────────────────── */}
      <div className="bg-surface border border-white/5 rounded-xl px-4 py-3">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-medium text-white/40 uppercase tracking-widest">
            Engine Status
          </span>
          {lastUpdated && !backendOffline && (
            <span className="text-xs text-white/25">
              Updated {lastUpdated.toLocaleTimeString()}
            </span>
          )}
        </div>

        {loading && !engines.length ? (
          <div className="flex gap-3 flex-wrap">
            {ENGINE_ORDER.map((key) => (
              <div
                key={key}
                className="h-5 w-28 bg-white/5 rounded animate-pulse"
              />
            ))}
          </div>
        ) : backendOffline ? (
          <p className="text-xs text-red-400/70">
            Server unreachable — check Tailscale connection
          </p>
        ) : error && !engines.length ? (
          <p className="text-xs text-red-400">⚠ {error}</p>
        ) : (
          <div className="flex flex-wrap gap-x-6 gap-y-1">
            {ENGINE_ORDER.map((key) => {
              const eng = engineMap[key];
              const status = eng?.status ?? "not_built";
              const colorClass =
                STATUS_COLORS[status as keyof typeof STATUS_COLORS] ??
                "text-slate-500";
              const icon =
                STATUS_ICONS[status as keyof typeof STATUS_ICONS] ?? "○";

              return (
                <div key={key} className="flex items-center gap-1.5">
                  <span className="text-xs">{icon}</span>
                  <span className="text-xs text-white/60">
                    {ENGINE_LABELS[key] ?? key}
                  </span>
                  <span className={`text-xs font-medium ${colorClass}`}>
                    {status}
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

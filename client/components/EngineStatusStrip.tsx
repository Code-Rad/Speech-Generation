"use client";

/**
 * components/EngineStatusStrip.tsx
 * VoiceForge — Live engine health strip, polls /engines every 15 seconds.
 */

import { useCallback, useEffect, useState } from "react";
import { fetchEngines } from "@/lib/api";
import { ENGINE_LABELS, ENGINE_ORDER, ENGINE_POLL_INTERVAL_MS, STATUS_COLORS, STATUS_ICONS } from "@/lib/constants";
import type { Engine } from "@/lib/types";

interface EngineStatusStripProps {
  onEnginesUpdate?: (engines: Engine[]) => void;
}

export default function EngineStatusStrip({ onEnginesUpdate }: EngineStatusStripProps) {
  const [engines, setEngines] = useState<Engine[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const loadEngines = useCallback(async () => {
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

  const engineMap = Object.fromEntries(engines.map((e) => [e.engine_type, e]));

  return (
    <div className="bg-surface border border-white/5 rounded-xl px-4 py-3">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-medium text-white/40 uppercase tracking-widest">
          Engine Status
        </span>
        {lastUpdated && (
          <span className="text-xs text-white/25">
            Updated {lastUpdated.toLocaleTimeString()}
          </span>
        )}
      </div>

      {loading && !engines.length ? (
        <div className="flex gap-3">
          {ENGINE_ORDER.map((key) => (
            <div key={key} className="h-6 w-28 bg-white/5 rounded animate-pulse" />
          ))}
        </div>
      ) : error ? (
        <p className="text-xs text-red-400">⚠ Server unreachable — {error}</p>
      ) : (
        <div className="flex flex-wrap gap-x-6 gap-y-1">
          {ENGINE_ORDER.map((key) => {
            const eng = engineMap[key];
            const status = eng?.status ?? "not_built";
            const colorClass = STATUS_COLORS[status as keyof typeof STATUS_COLORS] ?? "text-slate-500";
            const icon = STATUS_ICONS[status as keyof typeof STATUS_ICONS] ?? "○";

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
  );
}

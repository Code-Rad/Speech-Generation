"use client";

/**
 * app/history/page.tsx
 * VoiceForge — Generation History page
 * All history is stored in localStorage (no backend history endpoint).
 * localStorage access is fully client-side (inside useEffect).
 * Header/footer provided by app/layout.tsx.
 */

import { useCallback, useEffect, useState } from "react";
import { motion } from "framer-motion";
import { ArrowRight, Clock, Trash2 } from "lucide-react";
import type { GenerationHistory } from "@/lib/types";
import EngineStatusStrip from "@/components/EngineStatusStrip";
import HistoryItem from "@/components/HistoryItem";

const STORAGE_KEY = "voiceforge_history";

type Filter = "all" | "en" | "hi" | "hinglish" | "draft" | "broadcast";

const FILTERS: { value: Filter; label: string }[] = [
  { value: "all", label: "All" },
  { value: "en", label: "🇬🇧 English" },
  { value: "hi", label: "🇮🇳 Hindi" },
  { value: "hinglish", label: "🔀 Hinglish" },
  { value: "draft", label: "Draft only" },
  { value: "broadcast", label: "Broadcast only" },
];

export default function HistoryPage() {
  const [history, setHistory] = useState<GenerationHistory[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [filter, setFilter] = useState<Filter>("all");
  const [confirmClear, setConfirmClear] = useState(false);

  useEffect(() => {
    document.title = "History — VoiceForge";
  }, []);

  // Load from localStorage — must be inside useEffect (not SSR-safe)
  useEffect(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        setHistory(JSON.parse(raw) as GenerationHistory[]);
      }
    } catch {
      // localStorage unavailable or corrupted — start empty
    }
    setLoaded(true);
  }, []);

  const handleDelete = useCallback((id: string) => {
    setHistory((prev) => {
      const next = prev.filter((h) => h.id !== id);
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
      } catch {
        /* ignore */
      }
      return next;
    });
  }, []);

  const handleClearAll = () => {
    if (!confirmClear) {
      setConfirmClear(true);
      setTimeout(() => setConfirmClear(false), 3000);
      return;
    }
    setHistory([]);
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch {
      /* ignore */
    }
    setConfirmClear(false);
  };

  // Apply active filter
  const filtered = history.filter((h) => {
    if (filter === "all") return true;
    if (filter === "draft") return h.is_draft;
    if (filter === "broadcast") return !h.is_draft;
    return h.language === filter;
  });

  const draftCount = history.filter((h) => h.is_draft).length;
  const broadcastCount = history.filter((h) => !h.is_draft).length;

  return (
    <motion.main
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
      className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6"
    >
      <EngineStatusStrip />

      {/* Page header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <Clock className="w-5 h-5 text-indigo-400" />
            <h1 className="font-display text-2xl font-bold text-white">
              Generation History
            </h1>
          </div>
          <p className="text-sm text-white/40 ml-8">
            Your recent speech generations in this browser
          </p>
        </div>
        {history.length > 0 && (
          <button
            onClick={handleClearAll}
            className={`flex items-center gap-1.5 px-3 py-2 text-sm rounded-xl border transition-colors flex-shrink-0 ${
              confirmClear
                ? "bg-red-600/20 border-red-500/30 text-red-400"
                : "bg-white/5 border-white/10 text-white/40 hover:bg-white/10"
            }`}
          >
            <Trash2 className="w-3.5 h-3.5" />
            {confirmClear ? "Confirm clear?" : "Clear History"}
          </button>
        )}
      </div>

      {/* Stats */}
      {loaded && history.length > 0 && (
        <div className="flex items-center gap-4 text-xs text-white/40">
          <span>
            <span className="text-white font-medium tabular-nums">
              {history.length}
            </span>{" "}
            generation{history.length !== 1 ? "s" : ""}
          </span>
          <span>·</span>
          <span>
            <span className="text-amber-400 font-medium tabular-nums">
              {draftCount}
            </span>{" "}
            draft
          </span>
          <span>·</span>
          <span>
            <span className="text-emerald-400 font-medium tabular-nums">
              {broadcastCount}
            </span>{" "}
            broadcast
          </span>
        </div>
      )}

      {/* Filter bar */}
      {history.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {FILTERS.map(({ value, label }) => (
            <button
              key={value}
              onClick={() => setFilter(value)}
              className={`px-3 py-1.5 rounded-lg text-xs transition-colors border ${
                filter === value
                  ? "bg-indigo-600 border-indigo-500 text-white"
                  : "bg-white/5 border-white/8 text-white/50 hover:bg-white/10 hover:text-white/70"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      )}

      {/* ── Content ──────────────────────────────────────────────────────── */}
      {!loaded ? (
        /* Loading skeletons */
        <div className="space-y-3">
          {[0, 1, 2].map((i) => (
            <div
              key={i}
              className="h-24 rounded-xl bg-white/[0.03] border border-white/5 animate-pulse"
            />
          ))}
        </div>
      ) : history.length === 0 ? (
        /* Empty state */
        <div className="flex flex-col items-center justify-center py-24 text-center">
          {/* CSS waveform art */}
          <div className="flex items-end gap-1 mb-6 opacity-15">
            {[12, 28, 16, 44, 20, 36, 10, 48, 22, 34, 14, 40, 18, 30, 10].map(
              (h, i) => (
                <div
                  key={i}
                  className="w-2 bg-indigo-400 rounded-full"
                  style={{ height: `${h}px` }}
                />
              )
            )}
          </div>
          <h2 className="text-lg font-semibold text-white/40 mb-2">
            No generations yet
          </h2>
          <p className="text-sm text-white/25 mb-6">
            Generate your first speech on the Generator page
          </p>
          <a
            href="/"
            className="flex items-center gap-2 px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-xl transition-colors"
          >
            Go to Generator
            <ArrowRight className="w-4 h-4" />
          </a>
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-16 text-white/30 text-sm">
          No generations match this filter.
        </div>
      ) : (
        /* History list */
        <div className="space-y-3">
          {filtered.map((item) => (
            <HistoryItem
              key={item.id}
              item={item}
              onDelete={handleDelete}
            />
          ))}
        </div>
      )}
    </motion.main>
  );
}

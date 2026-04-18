"use client";

/**
 * components/HistoryItem/index.tsx
 * VoiceForge — Single generation history entry card.
 * Shows profile, timestamp, text preview, engine badge, and delete action.
 */

import { Trash2 } from "lucide-react";
import { ENGINE_LABELS } from "@/lib/constants";
import type { GenerationHistory } from "@/lib/types";

interface HistoryItemProps {
  item: GenerationHistory;
  onDelete: (id: string) => void;
}

export default function HistoryItem({ item, onDelete }: HistoryItemProps) {
  const date = new Date(item.timestamp);
  const dateStr = date.toLocaleDateString("en-IN", {
    month: "short",
    day: "numeric",
  });
  const timeStr = date.toLocaleTimeString("en-IN", {
    hour: "2-digit",
    minute: "2-digit",
  });

  const langFlag =
    item.language === "en"
      ? "🇬🇧"
      : item.language === "hi"
      ? "🇮🇳"
      : "🔀";

  const engineLabel = ENGINE_LABELS[item.engine_used] ?? item.engine_used;
  const fileSizeKB = (item.file_size_bytes / 1024).toFixed(0);

  return (
    <div className="bg-[#12121a] border border-white/6 rounded-xl px-4 py-4 hover:border-white/12 transition-colors group">
      {/* Top row */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="text-sm">{langFlag}</span>
          <span className="text-sm font-medium text-white/75">
            {item.profile_display_name}
          </span>
        </div>
        <span className="text-xs text-white/30">
          {dateStr} · {timeStr}
        </span>
      </div>

      {/* Text preview */}
      <p className="text-xs text-white/45 line-clamp-2 mb-3 font-mono bg-white/[0.02] rounded-lg px-3 py-2 leading-relaxed">
        &ldquo;{item.text_preview}
        {item.text_preview.length >= 100 ? "…" : ""}&rdquo;
      </p>

      {/* Metadata + actions */}
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-[10px] px-2 py-0.5 rounded-full bg-white/5 border border-white/8 text-white/40">
            {engineLabel}
          </span>
          <span
            className={`text-[10px] px-2 py-0.5 rounded-full border font-medium ${
              item.is_draft
                ? "bg-amber-500/10 border-amber-500/20 text-amber-400"
                : "bg-emerald-500/10 border-emerald-500/20 text-emerald-400"
            }`}
          >
            {item.is_draft ? "DRAFT" : "BROADCAST"}
          </span>
          {item.duration_seconds > 0 && (
            <span className="text-[10px] text-white/25">
              {item.duration_seconds.toFixed(1)}s · {fileSizeKB} KB
            </span>
          )}
        </div>

        <button
          onClick={() => onDelete(item.id)}
          className="flex items-center gap-1 px-2.5 py-1.5 text-white/20 hover:text-red-400 hover:bg-red-500/8 rounded-lg transition-colors text-xs opacity-0 group-hover:opacity-100"
          aria-label={`Delete history item for ${item.profile_display_name}`}
        >
          <Trash2 className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
}

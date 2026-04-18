"use client";

/**
 * components/GenerateButton.tsx
 * VoiceForge — Primary CTA button with animated loading state.
 */

import { Loader2, Mic, Wand2 } from "lucide-react";
import type { GenerationState } from "@/lib/types";

interface GenerateButtonProps {
  state: GenerationState;
  onClick: () => void;
  disabled?: boolean;
  selectedProfile?: string | null;
}

export default function GenerateButton({
  state,
  onClick,
  disabled = false,
  selectedProfile,
}: GenerateButtonProps) {
  const isGenerating = state === "generating";
  const isDisabled = disabled || isGenerating || !selectedProfile;

  const label = isGenerating
    ? "Generating…"
    : state === "success"
    ? "Generate Again"
    : "Generate Speech";

  const Icon = isGenerating ? Loader2 : state === "success" ? Wand2 : Mic;

  return (
    <button
      type="button"
      onClick={onClick}
      disabled={isDisabled}
      className={`
        relative w-full flex items-center justify-center gap-2.5
        px-6 py-3.5 rounded-xl text-sm font-semibold
        transition-all duration-200
        ${
          isDisabled
            ? "bg-indigo-600/30 text-white/30 cursor-not-allowed border border-indigo-500/20"
            : "bg-indigo-600 text-white border border-indigo-500/50 shadow-lg shadow-indigo-900/40 hover:bg-indigo-500 hover:shadow-indigo-900/60 active:scale-[0.98]"
        }
      `}
      aria-busy={isGenerating}
    >
      <Icon
        className={`w-4 h-4 flex-shrink-0 ${isGenerating ? "animate-spin" : ""}`}
      />
      <span>{label}</span>

      {/* Shimmer overlay while generating */}
      {isGenerating && (
        <span
          className="absolute inset-0 rounded-xl overflow-hidden pointer-events-none"
          aria-hidden="true"
        >
          <span className="absolute inset-0 translate-x-[-100%] animate-shimmer bg-gradient-to-r from-transparent via-white/10 to-transparent" />
        </span>
      )}
    </button>
  );
}

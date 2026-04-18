"use client";

/**
 * components/ScriptInput.tsx
 * VoiceForge — Multi-line script text area with character count and validation.
 */

import { TEXT_MAX_LENGTH, TEXT_MIN_LENGTH, TEXT_WARNING_LENGTH } from "@/lib/constants";

interface ScriptInputProps {
  value: string;
  onChange: (text: string) => void;
  disabled?: boolean;
  error?: string | null;
}

export default function ScriptInput({
  value,
  onChange,
  disabled = false,
  error,
}: ScriptInputProps) {
  const len = value.length;
  const isWarning = len >= TEXT_WARNING_LENGTH;
  const isOverLimit = len > TEXT_MAX_LENGTH;
  const isTooShort = len > 0 && len < TEXT_MIN_LENGTH;

  const charCountColor = isOverLimit
    ? "text-red-400"
    : isWarning
    ? "text-amber-400"
    : "text-white/30";

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <label
          htmlFor="script-input"
          className="text-xs font-medium text-white/40 uppercase tracking-widest"
        >
          Script
        </label>
        <span className={`text-xs tabular-nums ${charCountColor}`}>
          {len.toLocaleString()} / {TEXT_MAX_LENGTH.toLocaleString()}
        </span>
      </div>

      <textarea
        id="script-input"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        placeholder="Enter the news script text to convert to speech…"
        rows={8}
        maxLength={TEXT_MAX_LENGTH + 100} // soft limit; hard validation in handler
        className={`
          w-full resize-y rounded-xl px-4 py-3
          bg-white/[0.04] border text-white/90 text-sm leading-relaxed
          placeholder:text-white/20
          focus:outline-none focus:ring-2 focus:ring-indigo-500/50
          transition-colors duration-150
          ${
            error || isOverLimit
              ? "border-red-500/50 focus:ring-red-500/30"
              : "border-white/10 focus:border-indigo-500/40"
          }
          ${disabled ? "opacity-50 cursor-not-allowed" : ""}
          font-sans
        `}
        style={{ minHeight: "180px" }}
        aria-describedby={error ? "script-error" : undefined}
      />

      {/* Validation messages */}
      {isTooShort && !error && (
        <p className="text-xs text-amber-400">
          ⚠ Minimum {TEXT_MIN_LENGTH} characters required
        </p>
      )}
      {isOverLimit && !error && (
        <p className="text-xs text-red-400">
          ✗ Text exceeds {TEXT_MAX_LENGTH.toLocaleString()} character limit
        </p>
      )}
      {error && (
        <p id="script-error" className="text-xs text-red-400">
          ✗ {error}
        </p>
      )}
    </div>
  );
}

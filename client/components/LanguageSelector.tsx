"use client";

/**
 * components/LanguageSelector.tsx
 * VoiceForge — Three-button language picker (en / hi / hinglish).
 */

import { LANGUAGES } from "@/lib/constants";
import type { Language } from "@/lib/types";

interface LanguageSelectorProps {
  selected: Language;
  onChange: (lang: Language) => void;
  disabled?: boolean;
}

export default function LanguageSelector({
  selected,
  onChange,
  disabled = false,
}: LanguageSelectorProps) {
  return (
    <div className="flex flex-col gap-2">
      <label className="text-xs font-medium text-white/40 uppercase tracking-widest">
        Language
      </label>
      <div className="flex gap-2">
        {LANGUAGES.map((lang) => {
          const isSelected = lang.value === selected;
          return (
            <button
              key={lang.value}
              type="button"
              disabled={disabled}
              onClick={() => onChange(lang.value)}
              className={`
                flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium
                transition-all duration-150 border
                ${
                  isSelected
                    ? "bg-indigo-600 border-indigo-500 text-white shadow-lg shadow-indigo-900/40"
                    : "bg-white/5 border-white/10 text-white/60 hover:bg-white/10 hover:text-white/90 hover:border-white/20"
                }
                ${disabled ? "opacity-50 cursor-not-allowed" : "cursor-pointer"}
              `}
              aria-pressed={isSelected}
            >
              <span className="text-base">{lang.flag}</span>
              <span>{lang.label}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

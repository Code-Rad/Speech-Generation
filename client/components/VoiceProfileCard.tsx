"use client";

/**
 * components/VoiceProfileCard.tsx
 * VoiceForge — Selectable voice profile card with cloning indicator.
 */

import { Mic, MicOff, User } from "lucide-react";
import type { VoiceProfile } from "@/lib/types";

interface VoiceProfileCardProps {
  profile: VoiceProfile;
  selected: boolean;
  onSelect: (profileId: string) => void;
  disabled?: boolean;
}

export default function VoiceProfileCard({
  profile,
  selected,
  onSelect,
  disabled = false,
}: VoiceProfileCardProps) {
  const genderIcon = profile.gender === "male" ? "♂" : "♀";
  const genderColor = profile.gender === "male" ? "text-blue-400" : "text-pink-400";

  return (
    <button
      type="button"
      disabled={disabled}
      onClick={() => onSelect(profile.profile_id)}
      className={`
        relative w-full text-left p-4 rounded-xl border transition-all duration-150
        ${
          selected
            ? "bg-indigo-900/30 border-indigo-500/60 shadow-lg shadow-indigo-900/20"
            : "bg-white/[0.03] border-white/8 hover:bg-white/[0.06] hover:border-white/15"
        }
        ${disabled ? "opacity-50 cursor-not-allowed" : "cursor-pointer"}
      `}
      aria-pressed={selected}
    >
      {/* Selection indicator */}
      {selected && (
        <div className="absolute top-3 right-3 w-2 h-2 rounded-full bg-indigo-400" />
      )}

      {/* Header */}
      <div className="flex items-center gap-2 mb-2">
        <div className={`
          w-8 h-8 rounded-lg flex items-center justify-center text-sm
          ${selected ? "bg-indigo-600/40" : "bg-white/8"}
        `}>
          <User className="w-4 h-4 text-white/60" />
        </div>
        <div className="flex-1 min-w-0">
          <p className={`text-sm font-medium truncate ${selected ? "text-white" : "text-white/80"}`}>
            {profile.display_name}
          </p>
          <p className={`text-xs ${genderColor}`}>
            {genderIcon} {profile.gender}
          </p>
        </div>
      </div>

      {/* Description */}
      <p className="text-xs text-white/40 line-clamp-2 mb-3">
        {profile.description}
      </p>

      {/* Footer */}
      <div className="flex items-center gap-2">
        {profile.cloning_enabled ? (
          <div className="flex items-center gap-1 text-xs text-emerald-400/80">
            <Mic className="w-3 h-3" />
            <span>{profile.has_reference_audio ? "Cloning ready" : "No reference"}</span>
          </div>
        ) : (
          <div className="flex items-center gap-1 text-xs text-white/25">
            <MicOff className="w-3 h-3" />
            <span>No cloning</span>
          </div>
        )}

        <div className="ml-auto flex items-center gap-1">
          {profile.engine_preference.slice(0, 2).map((eng) => (
            <span
              key={eng}
              className="text-[10px] px-1.5 py-0.5 rounded bg-white/5 text-white/30 border border-white/5"
            >
              {eng.replace("_tts", "").replace("_v2", " v2").replace("_s2_pro", " S2")}
            </span>
          ))}
        </div>
      </div>
    </button>
  );
}

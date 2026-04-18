"use client";

/**
 * components/VoiceProfileManagerCard/index.tsx
 * VoiceForge — Profile card for the Voices page.
 * Shows clone status, record/upload actions, and upload progress.
 */

import { useState } from "react";
import {
  AlertCircle,
  CheckCircle,
  Loader2,
  Mic,
  RefreshCw,
  Upload,
} from "lucide-react";
import { uploadReferenceAudio } from "@/lib/api";
import type { VoiceProfile } from "@/lib/types";
import type { ToastType } from "@/components/Toast";
import RecordModal from "@/components/RecordModal";
import UploadZone from "@/components/UploadZone";

type CardState = "idle" | "uploading" | "error";
type PanelMode = "none" | "record" | "upload";

interface VoiceProfileManagerCardProps {
  profile: VoiceProfile;
  onCloned: (profileId: string) => void;
  onToast: (type: ToastType, title: string, message?: string) => void;
}

export default function VoiceProfileManagerCard({
  profile,
  onCloned,
  onToast,
}: VoiceProfileManagerCardProps) {
  const [panelMode, setPanelMode] = useState<PanelMode>("none");
  const [cardState, setCardState] = useState<CardState>("idle");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const isCloned = profile.has_reference_audio;

  const doUpload = async (file: File) => {
    setCardState("uploading");
    setErrorMsg(null);
    setPanelMode("none");

    try {
      const result = await uploadReferenceAudio(profile.profile_id, file, true);
      if (result.success) {
        onCloned(profile.profile_id);
        onToast(
          "success",
          `Voice saved for ${profile.display_name}`,
          "This voice will be used for all future generations with this profile."
        );
      } else {
        const msg = result.error ?? result.message ?? "Upload failed";
        setErrorMsg(msg);
        onToast("error", "Upload failed", msg);
      }
    } catch (err) {
      const msg =
        err instanceof Error ? err.message : "Upload failed. Check server.";
      setErrorMsg(msg);
      onToast("error", "Upload failed", msg);
    } finally {
      setCardState("idle");
      setSelectedFile(null);
    }
  };

  const handleFileSelected = (file: File) => {
    setSelectedFile(file);
  };

  const handleSubmitUpload = async () => {
    if (!selectedFile) return;
    await doUpload(selectedFile);
  };

  const handleRecordSave = async (blob: Blob) => {
    setPanelMode("none");
    const ext = blob.type.includes("mp4")
      ? "mp4"
      : blob.type.includes("ogg")
      ? "ogg"
      : "webm";
    const file = new File(
      [blob],
      `${profile.profile_id}_recording.${ext}`,
      { type: blob.type }
    );
    await doUpload(file);
  };

  const langFlag =
    profile.language === "en"
      ? "🇬🇧"
      : profile.language === "hi"
      ? "🇮🇳"
      : "🔀";

  const genderColor =
    profile.gender === "male" ? "text-blue-400" : "text-pink-400";
  const genderIcon = profile.gender === "male" ? "♂" : "♀";

  return (
    <>
      <div
        className={`
          rounded-2xl border transition-all duration-300 overflow-hidden
          ${isCloned
            ? "border-emerald-500/30 bg-emerald-950/10"
            : errorMsg
            ? "border-red-500/25 bg-[#12121a]"
            : cardState === "uploading"
            ? "border-indigo-500/40 bg-[#12121a]"
            : "border-white/8 bg-[#12121a]"}
        `}
      >
        <div className="p-5">
          {/* Header */}
          <div className="flex items-start justify-between mb-3">
            <div>
              <p className="text-sm font-semibold text-white/90">
                {profile.display_name}
              </p>
              <div className="flex items-center gap-2 mt-1">
                <span className="text-xs">{langFlag}</span>
                <span className="text-xs text-white/40 capitalize">
                  {profile.language}
                </span>
                <span className={`text-xs ${genderColor}`}>{genderIcon}</span>
              </div>
            </div>

            {/* Clone status badge */}
            {isCloned ? (
              <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-500/15 border border-emerald-500/25 flex-shrink-0">
                <CheckCircle className="w-3 h-3 text-emerald-400" />
                <span className="text-xs font-medium text-emerald-400">
                  Voice Cloned
                </span>
              </div>
            ) : (
              <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-white/5 border border-white/10 flex-shrink-0">
                <div className="w-2 h-2 rounded-full bg-white/20" />
                <span className="text-xs text-white/30">No Reference</span>
              </div>
            )}
          </div>

          {/* Engine chips */}
          <div className="flex flex-wrap gap-1 mb-4">
            {profile.engine_preference.map((eng) => (
              <span
                key={eng}
                className="text-[10px] px-1.5 py-0.5 rounded bg-white/5 text-white/25 border border-white/8"
              >
                {eng
                  .replace("_tts", "")
                  .replace("_v2", " v2")
                  .replace("_s2_pro", " S2")}
              </span>
            ))}
          </div>

          {/* Description */}
          <p className="text-xs text-white/35 mb-4 line-clamp-2">
            {profile.description}
          </p>

          {/* Uploading state */}
          {cardState === "uploading" && (
            <div className="flex items-center gap-2 mb-3 text-sm text-indigo-400">
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>Uploading and validating…</span>
            </div>
          )}

          {/* Error message */}
          {errorMsg && cardState !== "uploading" && (
            <div className="flex items-start gap-2 mb-3 bg-red-500/8 border border-red-500/20 rounded-lg px-3 py-2">
              <AlertCircle className="w-3.5 h-3.5 text-red-400 flex-shrink-0 mt-0.5" />
              <p className="text-xs text-red-300">{errorMsg}</p>
            </div>
          )}

          {/* Action buttons */}
          {cardState !== "uploading" && (
            <div className="flex flex-wrap gap-2">
              {!isCloned ? (
                <>
                  <button
                    onClick={() =>
                      setPanelMode(panelMode === "record" ? "none" : "record")
                    }
                    className="flex items-center gap-1.5 px-3 py-2 bg-indigo-600/20 hover:bg-indigo-600/30 border border-indigo-500/30 text-indigo-300 text-xs font-medium rounded-lg transition-colors"
                  >
                    <Mic className="w-3.5 h-3.5" />
                    Record Voice
                  </button>
                  <button
                    onClick={() =>
                      setPanelMode(
                        panelMode === "upload" ? "none" : "upload"
                      )
                    }
                    className="flex items-center gap-1.5 px-3 py-2 bg-white/5 hover:bg-white/10 border border-white/10 text-white/60 text-xs font-medium rounded-lg transition-colors"
                  >
                    <Upload className="w-3.5 h-3.5" />
                    Upload File
                  </button>
                </>
              ) : (
                <>
                  <button
                    onClick={() =>
                      setPanelMode(
                        panelMode === "upload" ? "none" : "upload"
                      )
                    }
                    className="flex items-center gap-1.5 px-3 py-2 bg-white/5 hover:bg-white/8 border border-white/8 text-white/35 text-xs rounded-lg transition-colors"
                  >
                    <RefreshCw className="w-3.5 h-3.5" />
                    Replace Voice
                  </button>
                  <button
                    onClick={() =>
                      setPanelMode(panelMode === "record" ? "none" : "record")
                    }
                    className="flex items-center gap-1.5 px-3 py-2 bg-white/5 hover:bg-white/8 border border-white/8 text-white/35 text-xs rounded-lg transition-colors"
                  >
                    <Mic className="w-3.5 h-3.5" />
                    Re-record
                  </button>
                </>
              )}
            </div>
          )}

          {/* Hint when empty */}
          {!isCloned && cardState === "idle" && panelMode === "none" && (
            <p className="text-[10px] text-white/20 mt-3">
              10–60 seconds of clear speech required
            </p>
          )}
        </div>

        {/* Upload panel */}
        {panelMode === "upload" && (
          <div className="border-t border-white/5 px-5 pb-5 pt-4 space-y-3">
            <UploadZone
              onFileSelected={handleFileSelected}
              disabled={cardState === "uploading"}
            />
            {selectedFile && (
              <button
                onClick={handleSubmitUpload}
                disabled={cardState === "uploading"}
                className="w-full flex items-center justify-center gap-2 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold rounded-xl transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Upload className="w-4 h-4" />
                Upload and Save
              </button>
            )}
          </div>
        )}
      </div>

      {/* Record modal — rendered outside card to avoid z-index issues */}
      {panelMode === "record" && (
        <RecordModal
          profile={profile}
          onClose={() => setPanelMode("none")}
          onSave={handleRecordSave}
        />
      )}
    </>
  );
}

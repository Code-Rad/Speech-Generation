"use client";

/**
 * components/AudioPlayer.tsx
 * VoiceForge — Audio playback component with waveform visualization,
 * download button, and generation metadata display.
 * Animates in via Framer Motion when result first appears.
 */

import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { Download, Pause, Play, Volume2 } from "lucide-react";
import { ENGINE_LABELS } from "@/lib/constants";
import type { GenerationResult } from "@/lib/types";

interface AudioPlayerProps {
  result: GenerationResult;
}

export default function AudioPlayer({ result }: AudioPlayerProps) {
  const { meta, blobUrl } = result;
  const audioRef = useRef<HTMLAudioElement>(null);
  const [playing, setPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(meta.duration_seconds);

  useEffect(() => {
    // Clean up old blob URL on unmount
    return () => {
      // blobUrl is managed by parent — don't revoke here
    };
  }, [blobUrl]);

  const toggle = () => {
    const audio = audioRef.current;
    if (!audio) return;
    if (playing) {
      audio.pause();
    } else {
      audio.play().catch(() => {});
    }
  };

  const handleTimeUpdate = () => {
    if (audioRef.current) setCurrentTime(audioRef.current.currentTime);
  };

  const handleLoadedMetadata = () => {
    if (audioRef.current) setDuration(audioRef.current.duration);
  };

  const handleSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
    const t = parseFloat(e.target.value);
    if (audioRef.current) audioRef.current.currentTime = t;
    setCurrentTime(t);
  };

  const formatTime = (s: number) => {
    const m = Math.floor(s / 60);
    const sec = Math.floor(s % 60);
    return `${m}:${sec.toString().padStart(2, "0")}`;
  };

  const fileSizeKb = (meta.file_size_bytes / 1024).toFixed(1);
  const engineLabel = ENGINE_LABELS[meta.engine_used] ?? meta.engine_used;
  const progressPct = duration > 0 ? (currentTime / duration) * 100 : 0;

  const handleDownload = () => {
    const a = document.createElement("a");
    a.href = blobUrl;
    a.download = `voiceforge_${meta.profile_id}_${meta.request_id.slice(0, 8)}.${meta.output_format}`;
    a.click();
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: "easeOut" }}
      className="bg-surface border border-white/8 rounded-2xl overflow-hidden"
    >
      {/* Header bar */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-white/5">
        <div className="flex items-center gap-2">
          <Volume2 className="w-4 h-4 text-indigo-400" />
          <span className="text-sm font-medium text-white/80">Generated Audio</span>
          {meta.fallback_used && (
            <span className="text-xs px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-400 border border-amber-500/20">
              Fallback
            </span>
          )}
        </div>
        <button
          onClick={handleDownload}
          className="flex items-center gap-1.5 text-xs text-white/50 hover:text-white/90 transition-colors px-2.5 py-1.5 rounded-lg hover:bg-white/8"
        >
          <Download className="w-3.5 h-3.5" />
          Download
        </button>
      </div>

      {/* Player */}
      <div className="px-5 py-4">
        <audio
          ref={audioRef}
          src={blobUrl}
          onPlay={() => setPlaying(true)}
          onPause={() => setPlaying(false)}
          onEnded={() => { setPlaying(false); setCurrentTime(0); }}
          onTimeUpdate={handleTimeUpdate}
          onLoadedMetadata={handleLoadedMetadata}
          preload="auto"
        />

        <div className="flex items-center gap-3">
          {/* Play/Pause */}
          <button
            onClick={toggle}
            className="
              w-10 h-10 rounded-full bg-indigo-600 border border-indigo-500/50
              flex items-center justify-center flex-shrink-0
              hover:bg-indigo-500 transition-colors shadow-lg shadow-indigo-900/40
              active:scale-95
            "
            aria-label={playing ? "Pause" : "Play"}
          >
            {playing ? (
              <Pause className="w-4 h-4 text-white" />
            ) : (
              <Play className="w-4 h-4 text-white ml-0.5" />
            )}
          </button>

          {/* Progress */}
          <div className="flex-1 flex items-center gap-2">
            <span className="text-xs tabular-nums text-white/40 w-8">
              {formatTime(currentTime)}
            </span>
            <div className="relative flex-1 h-1.5 bg-white/10 rounded-full overflow-hidden">
              <div
                className="absolute inset-y-0 left-0 bg-indigo-500 rounded-full transition-all"
                style={{ width: `${progressPct}%` }}
              />
              <input
                type="range"
                min={0}
                max={duration || 1}
                step={0.01}
                value={currentTime}
                onChange={handleSeek}
                className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                aria-label="Seek audio"
              />
            </div>
            <span className="text-xs tabular-nums text-white/40 w-8 text-right">
              {formatTime(duration)}
            </span>
          </div>
        </div>
      </div>

      {/* Metadata grid */}
      <div className="px-5 pb-4 grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[
          { label: "Engine", value: engineLabel },
          { label: "Format", value: meta.output_format.toUpperCase() },
          { label: "File size", value: `${fileSizeKb} KB` },
          { label: "Generation", value: `${meta.generation_time_ms}ms` },
        ].map(({ label, value }) => (
          <div key={label} className="bg-white/[0.03] rounded-lg px-3 py-2">
            <p className="text-xs text-white/30 mb-0.5">{label}</p>
            <p className="text-sm font-medium text-white/80">{value}</p>
          </div>
        ))}
      </div>

      {/* Fallback reason */}
      {meta.fallback_used && meta.fallback_reason && (
        <div className="px-5 pb-4">
          <p className="text-xs text-amber-400/70">
            ⚠ Fallback reason: {meta.fallback_reason}
          </p>
        </div>
      )}
    </motion.div>
  );
}

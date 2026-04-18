"use client";

/**
 * components/RecordModal/index.tsx
 * VoiceForge — Full-screen recording modal.
 * Uses MediaRecorder API + Web Audio API analyser for live waveform.
 * Allows playback before saving. Auto-stops at 60s.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  AlertCircle,
  Check,
  Mic,
  Pause,
  Play,
  RotateCcw,
  Square,
  X,
} from "lucide-react";
import type { VoiceProfile } from "@/lib/types";

type RecordState =
  | "idle"
  | "requesting"
  | "recording"
  | "recorded"
  | "error";

interface RecordModalProps {
  profile: VoiceProfile;
  onClose: () => void;
  onSave: (blob: Blob) => void;
}

const MAX_SECONDS = 60;
const MIN_SECONDS = 10;
const BAR_COUNT = 32;

export default function RecordModal({
  profile,
  onClose,
  onSave,
}: RecordModalProps) {
  const [recordState, setRecordState] = useState<RecordState>("idle");
  const [permissionError, setPermissionError] = useState<string | null>(null);
  const [seconds, setSeconds] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [bars, setBars] = useState<number[]>(
    new Array(BAR_COUNT).fill(2)
  );

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const blobRef = useRef<Blob | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const audioUrlRef = useRef<string | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const animFrameRef = useRef<number | null>(null);
  const streamRef = useRef<MediaStream | null>(null);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      cleanupRecording();
      if (audioUrlRef.current) URL.revokeObjectURL(audioUrlRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const cleanupRecording = () => {
    if (timerRef.current) clearInterval(timerRef.current);
    if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
    if (
      mediaRecorderRef.current &&
      mediaRecorderRef.current.state !== "inactive"
    ) {
      mediaRecorderRef.current.stop();
    }
    streamRef.current?.getTracks().forEach((t) => t.stop());
  };

  const animateWaveform = useCallback(() => {
    const analyser = analyserRef.current;
    if (!analyser) return;
    const data = new Uint8Array(analyser.frequencyBinCount);
    const step = Math.floor(data.length / BAR_COUNT);

    const tick = () => {
      analyser.getByteFrequencyData(data);
      const newBars = Array.from({ length: BAR_COUNT }, (_, i) => {
        const val = data[i * step] ?? 0;
        return Math.max(2, (val / 255) * 64);
      });
      setBars(newBars);
      animFrameRef.current = requestAnimationFrame(tick);
    };
    animFrameRef.current = requestAnimationFrame(tick);
  }, []);

  const startRecording = async () => {
    setRecordState("requesting");
    setPermissionError(null);

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true },
      });
      streamRef.current = stream;

      // Web Audio API analyser for waveform visualization
      const ctx = new AudioContext();
      const source = ctx.createMediaStreamSource(stream);
      const analyser = ctx.createAnalyser();
      analyser.fftSize = 256;
      source.connect(analyser);
      analyserRef.current = analyser;

      // MediaRecorder
      chunksRef.current = [];
      const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
        ? "audio/webm;codecs=opus"
        : MediaRecorder.isTypeSupported("audio/webm")
        ? "audio/webm"
        : "";

      const mr = mimeType
        ? new MediaRecorder(stream, { mimeType })
        : new MediaRecorder(stream);

      mr.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      mr.onstop = () => {
        const blob = new Blob(chunksRef.current, {
          type: mr.mimeType || "audio/webm",
        });
        blobRef.current = blob;

        if (audioUrlRef.current) URL.revokeObjectURL(audioUrlRef.current);
        audioUrlRef.current = URL.createObjectURL(blob);

        const audio = new Audio(audioUrlRef.current);
        audio.onended = () => setIsPlaying(false);
        audioRef.current = audio;

        stream.getTracks().forEach((t) => t.stop());
        if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
        setBars(new Array(BAR_COUNT).fill(2));
        setRecordState("recorded");
      };

      mediaRecorderRef.current = mr;
      mr.start(100);
      setRecordState("recording");
      setSeconds(0);
      animateWaveform();

      // Elapsed timer — auto-stop at MAX_SECONDS
      timerRef.current = setInterval(() => {
        setSeconds((s) => {
          if (s + 1 >= MAX_SECONDS) {
            stopRecording();
            return MAX_SECONDS;
          }
          return s + 1;
        });
      }, 1000);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Unknown error";
      const isDenied =
        msg.toLowerCase().includes("denied") ||
        msg.toLowerCase().includes("notallowed") ||
        msg.toLowerCase().includes("permission");

      setPermissionError(
        isDenied
          ? "Microphone access was denied. Open your browser settings, allow microphone access for this site, then try again."
          : `Could not access microphone: ${msg}`
      );
      setRecordState("error");
    }
  };

  const stopRecording = () => {
    if (timerRef.current) clearInterval(timerRef.current);
    if (mediaRecorderRef.current?.state !== "inactive") {
      mediaRecorderRef.current?.stop();
    }
  };

  const togglePlayback = () => {
    if (!audioRef.current) return;
    if (isPlaying) {
      audioRef.current.pause();
      setIsPlaying(false);
    } else {
      audioRef.current.currentTime = 0;
      audioRef.current.play().catch(() => {});
      setIsPlaying(true);
    }
  };

  const handleRecordAgain = () => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
    setIsPlaying(false);
    blobRef.current = null;
    setSeconds(0);
    setRecordState("idle");
  };

  const handleUseThis = () => {
    if (blobRef.current) onSave(blobRef.current);
  };

  const progressPct = (seconds / MAX_SECONDS) * 100;
  const fmt = (s: number) =>
    `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm"
        onClick={(e) => {
          if (e.target === e.currentTarget) onClose();
        }}
      >
        <motion.div
          initial={{ opacity: 0, scale: 0.96, y: 16 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.96, y: 16 }}
          transition={{ duration: 0.25, ease: "easeOut" }}
          className="bg-[#12121a] border border-white/10 rounded-2xl w-full max-w-lg shadow-2xl overflow-hidden"
        >
          {/* Header */}
          <div className="flex items-center justify-between px-6 pt-5 pb-4 border-b border-white/5">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-indigo-600/20 flex items-center justify-center">
                <Mic className="w-4 h-4 text-indigo-400" />
              </div>
              <div>
                <h2 className="text-sm font-semibold text-white">
                  Record Reference Voice
                </h2>
                <p className="text-xs text-white/40">{profile.display_name}</p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="text-white/30 hover:text-white/70 transition-colors"
              aria-label="Close"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          <div className="px-6 py-5 space-y-5">
            {/* Live waveform */}
            <div className="h-20 bg-black/30 rounded-xl flex items-center justify-center gap-[2px] px-4 overflow-hidden">
              {bars.map((h, i) => (
                <div
                  key={i}
                  className={`w-1 rounded-full transition-all duration-75 ${
                    recordState === "recording"
                      ? "bg-indigo-500"
                      : "bg-white/12"
                  }`}
                  style={{ height: `${h}px` }}
                />
              ))}
            </div>

            {/* Timer + progress bar */}
            {(recordState === "recording" || recordState === "recorded") && (
              <div className="space-y-2">
                <div className="flex justify-between text-xs text-white/40">
                  <span>{fmt(seconds)}</span>
                  <span>{fmt(MAX_SECONDS)} max</span>
                </div>
                <div className="h-1.5 bg-white/8 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-indigo-500 rounded-full transition-all duration-1000"
                    style={{ width: `${progressPct}%` }}
                  />
                </div>
                {recordState === "recorded" && seconds < MIN_SECONDS && (
                  <p className="text-xs text-amber-400">
                    ⚠ Recording is {seconds}s — minimum {MIN_SECONDS}s required
                  </p>
                )}
              </div>
            )}

            {/* Error message */}
            {recordState === "error" && permissionError && (
              <div className="flex items-start gap-2.5 bg-red-500/8 border border-red-500/20 rounded-xl px-4 py-3">
                <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0 mt-0.5" />
                <p className="text-sm text-red-300">{permissionError}</p>
              </div>
            )}

            {/* Controls */}
            <div className="flex items-center justify-center gap-3 flex-wrap">
              {recordState === "idle" && (
                <button
                  onClick={startRecording}
                  className="flex items-center gap-2 px-6 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold rounded-xl transition-colors"
                >
                  <Mic className="w-4 h-4" />
                  Start Recording
                </button>
              )}

              {recordState === "requesting" && (
                <p className="text-sm text-white/50 animate-pulse">
                  Requesting microphone access…
                </p>
              )}

              {recordState === "recording" && (
                <>
                  <button
                    onClick={stopRecording}
                    className="flex items-center gap-2 px-6 py-2.5 bg-red-600 hover:bg-red-500 text-white text-sm font-semibold rounded-xl transition-colors"
                  >
                    <Square className="w-4 h-4" />
                    Stop
                  </button>
                  <button
                    onClick={() => {
                      stopRecording();
                      onClose();
                    }}
                    className="px-4 py-2.5 bg-white/5 text-white/50 text-sm rounded-xl hover:bg-white/10 transition-colors"
                  >
                    Cancel
                  </button>
                </>
              )}

              {recordState === "recorded" && (
                <>
                  <button
                    onClick={togglePlayback}
                    className="flex items-center gap-2 px-4 py-2.5 bg-white/8 hover:bg-white/12 border border-white/10 text-white/80 text-sm rounded-xl transition-colors"
                  >
                    {isPlaying ? (
                      <Pause className="w-4 h-4" />
                    ) : (
                      <Play className="w-4 h-4" />
                    )}
                    {isPlaying ? "Pause" : "Play Back"}
                  </button>
                  <button
                    onClick={handleRecordAgain}
                    className="flex items-center gap-2 px-4 py-2.5 bg-white/5 text-white/50 text-sm rounded-xl hover:bg-white/8 transition-colors"
                  >
                    <RotateCcw className="w-4 h-4" />
                    Again
                  </button>
                  <button
                    onClick={handleUseThis}
                    disabled={seconds < MIN_SECONDS}
                    className="flex items-center gap-2 px-6 py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-semibold rounded-xl transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    <Check className="w-4 h-4" />
                    Use This
                  </button>
                </>
              )}

              {recordState === "error" && (
                <button
                  onClick={() => setRecordState("idle")}
                  className="flex items-center gap-2 px-6 py-2.5 bg-white/8 text-white/70 text-sm rounded-xl hover:bg-white/12 transition-colors"
                >
                  Try Again
                </button>
              )}
            </div>

            {/* Requirements hint */}
            <div className="bg-white/[0.03] rounded-xl px-4 py-3 border border-white/5">
              <p className="text-[10px] font-medium text-white/25 uppercase tracking-widest mb-2">
                Requirements
              </p>
              <ul className="space-y-1.5">
                {[
                  "10–60 seconds of clear speech",
                  "Speak naturally as a news anchor",
                  "No background music or noise",
                ].map((r) => (
                  <li
                    key={r}
                    className="flex items-center gap-2 text-xs text-white/45"
                  >
                    <span className="text-emerald-500 text-[10px]">✓</span>
                    {r}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}

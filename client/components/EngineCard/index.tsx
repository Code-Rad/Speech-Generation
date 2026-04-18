"use client";

/**
 * components/EngineCard/index.tsx
 * VoiceForge — Engine status card for the Engines dashboard.
 * Shows live status, metadata grid, test button (edge_tts only),
 * and expandable Phase 2 description.
 */

import { useState } from "react";
import {
  AlertTriangle,
  CheckCircle,
  Cpu,
  Loader2,
  XCircle,
  Zap,
} from "lucide-react";
import { fetchVoices, generateSpeech } from "@/lib/api";
import type { Engine } from "@/lib/types";

const ENGINE_DESCRIPTIONS: Record<string, string> = {
  edge_tts:
    "Microsoft Neural Voices — zero-GPU emergency fallback. Available on any machine instantly. Draft quality only, not suitable for broadcast.",
  xtts_v2:
    "Coqui XTTS v2 — Phase 1 primary engine with real-time voice cloning. Requires ~4 GB VRAM. Delivers broadcast-grade output in English, Hindi, and Hinglish.",
  voxtral_tts:
    "Voxtral TTS via vLLM-Omni — best Hindi and Hinglish quality. Requires WSL2 on TRIJYA-7 with ~16 GB VRAM. Activated in Phase 2.",
  fish_s2_pro:
    "Fish Speech S2 Pro via SGLang — best English quality with ultra-low latency. Requires WSL2 on TRIJYA-7 with ~8 GB VRAM. Activated in Phase 2.",
};

const ENGINE_ROLES: Record<string, string> = {
  edge_tts: "Emergency fallback only",
  xtts_v2: "Phase 1 primary engine",
  voxtral_tts: "Phase 2 Hindi/Hinglish primary",
  fish_s2_pro: "Phase 2 English primary",
};

const QUALITY: Record<string, { label: string; stars: number; color: string }> =
  {
    edge_tts: { label: "Draft", stars: 1, color: "text-amber-400" },
    xtts_v2: { label: "Broadcast", stars: 4, color: "text-emerald-400" },
    voxtral_tts: { label: "Broadcast+", stars: 5, color: "text-indigo-400" },
    fish_s2_pro: { label: "Broadcast+", stars: 5, color: "text-indigo-400" },
  };

interface EngineCardProps {
  engine: Engine;
  phase: 1 | 2;
}

type TestState = "idle" | "testing" | "success" | "error";

export default function EngineCard({ engine, phase }: EngineCardProps) {
  const [expanded, setExpanded] = useState(false);
  const [testState, setTestState] = useState<TestState>("idle");
  const [testResult, setTestResult] = useState<string | null>(null);

  const handleTest = async () => {
    setTestState("testing");
    setTestResult(null);
    try {
      const voices = await fetchVoices();
      const enProfile = voices.find((v) => v.language === "en");
      if (!enProfile) throw new Error("No English profile available");

      const start = Date.now();
      const { meta } = await generateSpeech({
        text: "Engine test. VoiceForge is online and ready.",
        profile_id: enProfile.profile_id,
        output_format: "wav",
      });
      const elapsed = Date.now() - start;

      setTestResult(
        `✓ Generated in ${(elapsed / 1000).toFixed(1)}s · ${(meta.file_size_bytes / 1024).toFixed(0)} KB WAV`
      );
      setTestState("success");
    } catch (err) {
      setTestResult(
        `✗ ${err instanceof Error ? err.message : "Test failed"}`
      );
      setTestState("error");
    }
  };

  const quality = QUALITY[engine.engine_type];

  const StatusIcon =
    engine.status === "available"
      ? CheckCircle
      : engine.status === "unavailable"
      ? AlertTriangle
      : XCircle;

  const statusColor =
    engine.status === "available"
      ? "text-emerald-400"
      : engine.status === "unavailable"
      ? "text-amber-400"
      : "text-slate-500";

  const borderColor =
    engine.status === "available"
      ? "border-emerald-500/20"
      : engine.status === "unavailable"
      ? "border-amber-500/15"
      : "border-white/8";

  const iconBg =
    engine.status === "available" ? "bg-emerald-500/15" : "bg-white/5";
  const iconColor =
    engine.status === "available" ? "text-emerald-400" : "text-white/25";

  return (
    <div
      className={`rounded-2xl border bg-[#12121a] overflow-hidden ${borderColor}`}
    >
      <div className="p-5">
        {/* Header */}
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center gap-3">
            <div
              className={`w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0 ${iconBg}`}
            >
              <Cpu className={`w-4 h-4 ${iconColor}`} />
            </div>
            <div>
              <p className="text-sm font-semibold text-white/90">
                {engine.display_name}
              </p>
              <p className="text-xs text-white/35">
                {ENGINE_ROLES[engine.engine_type] ?? engine.engine_type}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-1.5 flex-shrink-0">
            <StatusIcon className={`w-4 h-4 ${statusColor}`} />
            <span
              className={`text-xs font-medium uppercase tracking-wide ${statusColor}`}
            >
              {engine.status.replace("_", " ")}
            </span>
          </div>
        </div>

        {/* Metadata grid */}
        <div className="grid grid-cols-2 gap-2 mb-4">
          {[
            {
              label: "Languages",
              value:
                engine.supported_languages.join(", ") || "—",
            },
            {
              label: "Voice Cloning",
              value: engine.supports_cloning
                ? "✓ Supported"
                : "✗ Not supported",
            },
            {
              label: "Role",
              value: ENGINE_ROLES[engine.engine_type] ?? "—",
            },
            {
              label: "Quality",
              value: quality
                ? `${"★".repeat(quality.stars)}${"☆".repeat(
                    5 - quality.stars
                  )} ${quality.label}`
                : "—",
            },
          ].map(({ label, value }) => (
            <div
              key={label}
              className="bg-white/[0.03] rounded-lg px-3 py-2"
            >
              <p className="text-[10px] text-white/25 mb-0.5 uppercase tracking-wide">
                {label}
              </p>
              <p className="text-xs text-white/70 font-medium">{value}</p>
            </div>
          ))}
        </div>

        {/* Notes / status detail */}
        {engine.notes && (
          <p className="text-xs text-white/30 mb-3">
            Status: {engine.notes}
          </p>
        )}

        {/* Actions */}
        <div className="flex items-center gap-2 flex-wrap">
          {engine.engine_type === "edge_tts" &&
            engine.status === "available" && (
              <button
                onClick={handleTest}
                disabled={testState === "testing"}
                className="flex items-center gap-1.5 px-3 py-2 bg-indigo-600/20 hover:bg-indigo-600/30 border border-indigo-500/30 text-indigo-300 text-xs font-medium rounded-lg transition-colors disabled:opacity-50"
              >
                {testState === "testing" ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <Zap className="w-3.5 h-3.5" />
                )}
                Test Engine
              </button>
            )}

          {engine.status === "unavailable" &&
            engine.engine_type === "xtts_v2" && (
              <a
                href="https://github.com/coqui-ai/TTS"
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1.5 px-3 py-2 bg-white/5 hover:bg-white/8 border border-white/10 text-white/40 text-xs rounded-lg transition-colors"
              >
                How to activate →
              </a>
            )}

          {phase === 2 && (
            <button
              onClick={() => setExpanded((v) => !v)}
              className="flex items-center gap-1.5 px-3 py-2 bg-white/5 hover:bg-white/8 border border-white/10 text-white/35 text-xs rounded-lg transition-colors"
            >
              {expanded ? "Hide details" : "What is this? →"}
            </button>
          )}
        </div>

        {/* Test result */}
        {testResult && (
          <p
            className={`text-xs mt-3 ${
              testState === "success" ? "text-emerald-400" : "text-red-400"
            }`}
          >
            {testResult}
          </p>
        )}

        {/* Phase 2 expanded description */}
        {expanded && phase === 2 && (
          <div className="mt-4 bg-white/[0.03] rounded-xl px-4 py-3 border border-white/5">
            <p className="text-xs text-white/50 leading-relaxed">
              {ENGINE_DESCRIPTIONS[engine.engine_type]}
            </p>
            <p className="text-xs text-amber-400/70 mt-2">
              ⚠ Requires Phase 2 WSL2 setup on TRIJYA-7.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

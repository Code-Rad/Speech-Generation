"use client";

/**
 * components/UploadZone/index.tsx
 * VoiceForge — Drag-and-drop audio file upload zone.
 * Custom-styled, no native browser input visible.
 */

import { useCallback, useRef, useState } from "react";
import { FileAudio, Upload, X } from "lucide-react";

interface UploadZoneProps {
  onFileSelected: (file: File) => void;
  disabled?: boolean;
  accept?: string;
}

export default function UploadZone({
  onFileSelected,
  disabled = false,
  accept = ".wav,.mp3,audio/wav,audio/mpeg",
}: UploadZoneProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFile = useCallback(
    (file: File) => {
      setSelectedFile(file);
      onFileSelected(file);
    },
    [onFileSelected]
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      if (disabled) return;
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    },
    [disabled, handleFile]
  );

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    if (!disabled) setIsDragging(true);
  };

  const handleDragLeave = () => setIsDragging(false);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
  };

  const clearFile = (e: React.MouseEvent) => {
    e.stopPropagation();
    setSelectedFile(null);
    if (inputRef.current) inputRef.current.value = "";
  };

  const fileSizeKB = selectedFile
    ? (selectedFile.size / 1024).toFixed(0)
    : null;

  return (
    <div
      onDrop={handleDrop}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onClick={() => !disabled && inputRef.current?.click()}
      role="button"
      aria-label="Upload audio file"
      className={`
        relative rounded-xl border-2 border-dashed p-6
        transition-all duration-200 cursor-pointer select-none
        ${isDragging
          ? "border-indigo-500 bg-indigo-500/8"
          : selectedFile
          ? "border-emerald-500/40 bg-emerald-500/5"
          : "border-white/15 hover:border-white/30 hover:bg-white/[0.02]"}
        ${disabled ? "opacity-50 cursor-not-allowed" : ""}
      `}
    >
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        onChange={handleInputChange}
        disabled={disabled}
        className="hidden"
      />

      {selectedFile ? (
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-emerald-500/15 flex items-center justify-center flex-shrink-0">
            <FileAudio className="w-5 h-5 text-emerald-400" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-white/80 truncate">
              {selectedFile.name}
            </p>
            <p className="text-xs text-white/40">
              {fileSizeKB} KB · {selectedFile.type || "audio file"}
            </p>
          </div>
          <button
            onClick={clearFile}
            className="text-white/30 hover:text-white/70 transition-colors p-1 flex-shrink-0"
            aria-label="Remove file"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      ) : (
        <div className="flex flex-col items-center gap-3 py-2">
          <div
            className={`w-12 h-12 rounded-xl flex items-center justify-center transition-colors ${
              isDragging ? "bg-indigo-500/20" : "bg-white/5"
            }`}
          >
            <Upload
              className={`w-5 h-5 ${
                isDragging ? "text-indigo-400" : "text-white/30"
              }`}
            />
          </div>
          <div className="text-center">
            <p className="text-sm text-white/60">
              <span className="text-indigo-400 font-medium">
                Click to browse
              </span>{" "}
              or drag your audio file here
            </p>
            <p className="text-xs text-white/30 mt-1">
              WAV or MP3 · 10–60 seconds · up to 50 MB
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

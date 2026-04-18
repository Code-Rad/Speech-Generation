"use client";

/**
 * components/Toast/index.tsx
 * VoiceForge — Slide-in notification toast from top-right.
 * Auto-dismisses after 4 seconds. Types: success | error | warning | info.
 */

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { AlertCircle, AlertTriangle, CheckCircle, Info, X } from "lucide-react";

export type ToastType = "success" | "error" | "warning" | "info";

export interface ToastMessage {
  id: string;
  type: ToastType;
  title: string;
  message?: string;
}

interface ToastProps {
  toasts: ToastMessage[];
  onDismiss: (id: string) => void;
}

const ICONS = {
  success: CheckCircle,
  error: AlertCircle,
  warning: AlertTriangle,
  info: Info,
} as const;

const STYLES: Record<ToastType, string> = {
  success: "border-emerald-500/30 bg-emerald-950/80",
  error: "border-red-500/30 bg-red-950/80",
  warning: "border-amber-500/30 bg-amber-950/80",
  info: "border-indigo-500/30 bg-indigo-950/80",
};

const ICON_COLORS: Record<ToastType, string> = {
  success: "text-emerald-400",
  error: "text-red-400",
  warning: "text-amber-400",
  info: "text-indigo-400",
};

export function Toast({ toasts, onDismiss }: ToastProps) {
  return (
    <div className="fixed top-4 right-4 z-[9999] flex flex-col gap-2 pointer-events-none">
      <AnimatePresence>
        {toasts.map((toast) => {
          const Icon = ICONS[toast.type];
          return (
            <motion.div
              key={toast.id}
              initial={{ opacity: 0, x: 64, scale: 0.95 }}
              animate={{ opacity: 1, x: 0, scale: 1 }}
              exit={{ opacity: 0, x: 64, scale: 0.95 }}
              transition={{ duration: 0.25, ease: "easeOut" }}
              className={`pointer-events-auto flex items-start gap-3 px-4 py-3 rounded-xl border backdrop-blur-xl shadow-2xl max-w-sm ${STYLES[toast.type]}`}
            >
              <Icon
                className={`w-4 h-4 mt-0.5 flex-shrink-0 ${ICON_COLORS[toast.type]}`}
              />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-white/90">{toast.title}</p>
                {toast.message && (
                  <p className="text-xs text-white/55 mt-0.5 leading-relaxed">
                    {toast.message}
                  </p>
                )}
              </div>
              <button
                onClick={() => onDismiss(toast.id)}
                className="flex-shrink-0 text-white/30 hover:text-white/70 transition-colors"
                aria-label="Dismiss notification"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </motion.div>
          );
        })}
      </AnimatePresence>
    </div>
  );
}

// ── useToast hook ──────────────────────────────────────────────────────────────

export function useToast() {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const addToast = (type: ToastType, title: string, message?: string) => {
    const id = crypto.randomUUID();
    setToasts((prev) => [...prev, { id, type, title, message }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 4000);
  };

  const dismiss = (id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  return { toasts, addToast, dismiss };
}

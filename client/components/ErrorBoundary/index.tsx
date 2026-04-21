"use client";

/**
 * components/ErrorBoundary/index.tsx
 * VoiceForge — Global error boundary.
 * React class component (required by the error boundary API).
 * Catches unhandled render errors and shows a friendly recovery screen.
 */

import React from "react";
import { AlertTriangle } from "lucide-react";

interface Props {
  children: React.ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export default class ErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    // Log to console for dev visibility — not surfaced to users
    console.error("[ErrorBoundary]", error, info.componentStack);
  }

  render() {
    if (!this.state.hasError) return this.props.children;

    const isDev = process.env.NODE_ENV === "development";

    return (
      <div className="min-h-dvh bg-background flex items-center justify-center p-6">
        <div className="max-w-md w-full text-center space-y-6">
          {/* Icon */}
          <div className="w-16 h-16 rounded-2xl bg-red-500/10 border border-red-500/20 flex items-center justify-center mx-auto">
            <AlertTriangle className="w-8 h-8 text-red-400" />
          </div>

          {/* Message */}
          <div className="space-y-2">
            <h1 className="font-display text-xl font-bold text-white">
              Something went wrong
            </h1>
            <p className="text-sm text-white/50">
              VoiceForge encountered an unexpected error. Your history and voice
              profiles are safe — this only affects the current view.
            </p>
          </div>

          {/* Dev-only error detail */}
          {isDev && this.state.error && (
            <div className="bg-red-950/40 border border-red-500/20 rounded-xl px-4 py-3 text-left">
              <p className="text-xs font-mono text-red-300 break-all">
                {this.state.error.message}
              </p>
            </div>
          )}

          {/* Actions */}
          <div className="flex items-center justify-center gap-3">
            <button
              onClick={() => window.location.reload()}
              className="flex items-center gap-2 px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-xl transition-colors"
            >
              ↻ Reload Page
            </button>
            <a
              href="/"
              className="flex items-center gap-2 px-5 py-2.5 bg-white/5 hover:bg-white/10 border border-white/10 text-white/70 text-sm font-medium rounded-xl transition-colors"
            >
              ← Go to Generator
            </a>
          </div>
        </div>
      </div>
    );
  }
}

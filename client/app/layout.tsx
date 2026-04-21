/**
 * app/layout.tsx
 * VoiceForge — Root layout.
 * Provides: fonts, global CSS, shared sticky NavBar (uses usePathname for
 * active navigation states), ErrorBoundary, and site-wide footer.
 *
 * NavBar is a 'use client' component that uses usePathname() from
 * next/navigation to highlight the current active page.
 */

import type { Metadata } from "next";
import { Inter, Space_Grotesk } from "next/font/google";
import "./globals.css";
import NavBar from "@/components/NavBar";
import ErrorBoundary from "@/components/ErrorBoundary";

// usePathname is used inside NavBar (imported above) for active nav detection

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

const spaceGrotesk = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-space-grotesk",
  display: "swap",
});

export const metadata: Metadata = {
  title: {
    default: "VoiceForge — AI News Speech Generation",
    template: "%s — VoiceForge",
  },
  description:
    "Broadcast-quality TTS for English, Hindi, and Hinglish news scripts. " +
    "Powered by XTTS v2, Voxtral TTS, and Fish Speech S2 Pro.",
  icons: { icon: "/favicon.ico" },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${inter.variable} ${spaceGrotesk.variable}`}>
      <body className="font-sans antialiased bg-background text-white/87 min-h-dvh flex flex-col">
        <ErrorBoundary>
          {/* Shared sticky navigation — active state via usePathname */}
          <NavBar />

          {/* Page content */}
          <div className="flex-1">
            {children}
          </div>

          {/* Site-wide footer */}
          <footer className="border-t border-white/5 py-6">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-2 text-xs text-white/20">
              <span>
                VoiceForge v0.1.0 · Phase 1 · Built for AI News Video Generation Pipeline
              </span>
              <span>XTTS v2 · Edge TTS · FastAPI · TRIJYA-7</span>
            </div>
          </footer>
        </ErrorBoundary>
      </body>
    </html>
  );
}

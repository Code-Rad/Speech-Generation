"use client";

/**
 * components/NavBar/index.tsx
 * VoiceForge — Shared navigation bar.
 * Uses usePathname() to highlight the current active page.
 * Includes a mobile menu that collapses on small screens.
 */

import { useState } from "react";
import { usePathname } from "next/navigation";
import { Menu, Radio, X } from "lucide-react";

const NAV_LINKS = [
  { label: "Generator", href: "/" },
  { label: "Voices", href: "/voices" },
  { label: "History", href: "/history" },
  { label: "Engines", href: "/engines" },
];

export default function NavBar() {
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);

  const isActive = (href: string) =>
    href === "/" ? pathname === "/" : pathname.startsWith(href);

  return (
    <header className="sticky top-0 z-40 border-b border-white/5 bg-background/80 backdrop-blur-xl">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-14 flex items-center justify-between">
        {/* Logo */}
        <a href="/" className="flex items-center gap-2.5 flex-shrink-0">
          <div className="w-7 h-7 rounded-lg bg-indigo-600 flex items-center justify-center">
            <Radio className="w-4 h-4 text-white" />
          </div>
          <span className="font-display font-semibold text-white tracking-tight">
            VoiceForge
          </span>
          <span className="text-xs px-1.5 py-0.5 rounded bg-white/8 text-white/40 border border-white/8 font-mono hidden sm:inline">
            Phase 1
          </span>
        </a>

        {/* Desktop nav */}
        <nav className="hidden sm:flex items-center gap-1" aria-label="Main navigation">
          {NAV_LINKS.map(({ label, href }) => {
            const active = isActive(href);
            return (
              <a
                key={href}
                href={href}
                className={`
                  relative px-3 py-1.5 rounded-lg text-sm transition-all duration-150
                  ${active
                    ? "text-white bg-indigo-600/20 border border-indigo-500/30"
                    : "text-white/50 hover:text-white/85 hover:bg-white/6 border border-transparent"}
                `}
                aria-current={active ? "page" : undefined}
              >
                {label}
                {active && (
                  <span className="absolute bottom-0 left-1/2 -translate-x-1/2 w-4 h-0.5 bg-indigo-400 rounded-full" />
                )}
              </a>
            );
          })}
        </nav>

        {/* Mobile hamburger */}
        <button
          onClick={() => setMenuOpen((v) => !v)}
          className="sm:hidden p-2 text-white/50 hover:text-white/90 transition-colors rounded-lg hover:bg-white/8"
          aria-label={menuOpen ? "Close menu" : "Open menu"}
          aria-expanded={menuOpen}
        >
          {menuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>
      </div>

      {/* Mobile dropdown */}
      {menuOpen && (
        <div className="sm:hidden border-t border-white/5 bg-background/95 backdrop-blur-xl px-4 py-2 space-y-1">
          {NAV_LINKS.map(({ label, href }) => {
            const active = isActive(href);
            return (
              <a
                key={href}
                href={href}
                onClick={() => setMenuOpen(false)}
                className={`
                  flex items-center gap-2 px-4 py-3 rounded-xl text-sm transition-colors
                  min-h-[44px]
                  ${active
                    ? "text-white bg-indigo-600/20 border border-indigo-500/30"
                    : "text-white/60 hover:text-white/90 hover:bg-white/5 border border-transparent"}
                `}
                aria-current={active ? "page" : undefined}
              >
                {active && <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 flex-shrink-0" />}
                {label}
              </a>
            );
          })}
        </div>
      )}
    </header>
  );
}

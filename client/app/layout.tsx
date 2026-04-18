import type { Metadata } from "next";
import { Inter, Space_Grotesk } from "next/font/google";
import "./globals.css";

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
  title: "VoiceForge — AI News Speech Generation",
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
      <body className="font-sans antialiased bg-background text-white/87 min-h-dvh">
        {children}
      </body>
    </html>
  );
}

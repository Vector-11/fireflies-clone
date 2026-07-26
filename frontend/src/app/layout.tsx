import type { Metadata } from "next";
import { DM_Sans, Inter } from "next/font/google";

import { AppShell } from "@/components/layout/app-shell";
import { Providers } from "./providers";
import "./globals.css";

// The two families Fireflies actually uses: Inter for body copy, DM Sans for
// headings. Loaded through next/font so they are self-hosted and there is no
// layout shift while a webfont downloads.
const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

const dmSans = DM_Sans({
  subsets: ["latin"],
  variable: "--font-dm-sans",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Fireflies — Meeting Notes & Transcription",
  description:
    "Browse meetings, read interactive transcripts with speaker labels and timestamps, and work through AI summaries and action items.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`${inter.variable} ${dmSans.variable} h-full antialiased`}>
      <body className="h-full bg-grey-50">
        <Providers>
          <AppShell>{children}</AppShell>
        </Providers>
      </body>
    </html>
  );
}

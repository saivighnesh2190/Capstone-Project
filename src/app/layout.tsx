import type { Metadata } from "next";
import { Inter, JetBrains_Mono, Space_Grotesk } from "next/font/google";
import "./globals.css";
import { Toaster } from "@/components/ui/toaster";

const interSans = Inter({
  variable: "--font-sans",
  subsets: ["latin"],
});

const jetbrainsMono = JetBrains_Mono({
  variable: "--font-mono",
  subsets: ["latin"],
});

const spaceGrotesk = Space_Grotesk({
  variable: "--font-display",
  subsets: ["latin"],
  weight: ["500", "600", "700"],
});

export const metadata: Metadata = {
  title: "NestedTune Guard — CINT-11",
  description:
    "Deadlock-Aware Distributed Hyperparameter Tuning for Nested Trainers. " +
    "A deterministic, bounded, reproducible evaluation framework for the Ray #47439 " +
    "placement-group deadlock, with FIFO and greedy baselines (CP-1) plus a " +
    "deadlock-aware admission controller (CP-2).",
  keywords: [
    "Ray", "Ray Tune", "Ray Train", "placement group", "deadlock",
    "distributed training", "XGBoost", "hyperparameter tuning", "CINT-11",
    "NestedTune Guard",
  ],
  authors: [{ name: "CINT-11 Capstone Team" }],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <body
        className={`${interSans.variable} ${jetbrainsMono.variable} ${spaceGrotesk.variable} antialiased bg-background text-foreground`}
      >
        {children}
        <Toaster />
      </body>
    </html>
  );
}

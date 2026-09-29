import type { Metadata } from "next";
import "./globals.css";
import TopBar from "@/components/layout/TopBar";
import CursorGlow from "@/components/common/CursorGlow";

export const metadata: Metadata = {
  title: "Eye of Horus — Event Intelligence Terminal",
  description: "Event-to-market intelligence, quant research, and paper/live trading terminal.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-ink-950 text-text-primary font-sans antialiased">
        <div className="fixed inset-0 -z-10 bg-radial-fade pointer-events-none" />
        <div className="fixed inset-0 -z-20 bg-grid-lines bg-[size:64px_64px] opacity-[0.4] pointer-events-none" />
        <CursorGlow />
        <TopBar />
        <main className="relative">{children}</main>
      </body>
    </html>
  );
}

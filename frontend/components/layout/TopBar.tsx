"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import useSWR from "swr";
import clsx from "clsx";
import { api } from "@/lib/api";
import ModeBadge from "./ModeBadge";

const NAV = [
  { href: "/", label: "Dashboard" },
  { href: "/trading", label: "Trading" },
  { href: "/performance", label: "Performance" },
  { href: "/backtest", label: "Backtest Lab" },
  { href: "/replay", label: "Replay" },
  { href: "/alerts", label: "Alerts" },
  { href: "/system", label: "System" },
];

function useClock() {
  const [now, setNow] = useState<Date | null>(null);
  useEffect(() => {
    setNow(new Date());
    const id = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(id);
  }, []);
  return now;
}

export default function TopBar() {
  const pathname = usePathname();
  const now = useClock();
  const { data: mode } = useSWR("trading-mode", () => api.tradingMode(), { refreshInterval: 15000 });
  const { data: status } = useSWR("system-status", () => api.systemStatus(), { refreshInterval: 15000 });

  const sourcesOnline = status?.data_sources.filter((s) => s.status === "online").length ?? 0;
  const sourcesTotal = status?.data_sources.length ?? 0;

  return (
    <header className="sticky top-0 z-50 border-b border-border glass">
      <div className="mx-auto flex h-14 max-w-[1600px] items-center gap-6 px-6">
        <Link href="/" className="flex items-center gap-2.5 shrink-0">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" className="text-gold">
            <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="1.2" opacity="0.5" />
            <circle cx="12" cy="12" r="4" stroke="currentColor" strokeWidth="1.2" />
            <circle cx="12" cy="12" r="1.4" fill="currentColor" />
          </svg>
          <span className="text-[13px] font-semibold tracking-[0.14em] text-text-primary">EYE OF HORUS</span>
        </Link>

        <nav className="hidden md:flex items-center gap-1 text-[13px]">
          {NAV.map((item) => {
            const active = item.href === "/" ? pathname === "/" : pathname?.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={clsx(
                  "rounded-md px-3 py-1.5 transition-colors",
                  active ? "bg-white/[0.06] text-text-primary" : "text-text-secondary hover:text-text-primary hover:bg-white/[0.03]"
                )}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div className="ml-auto flex items-center gap-4">
          <div className="hidden lg:flex items-center gap-1.5 text-[11px] text-text-tertiary">
            <span
              className={clsx(
                "h-1.5 w-1.5 rounded-full",
                sourcesOnline === sourcesTotal && sourcesTotal > 0 ? "bg-gold" : "bg-danger"
              )}
            />
            {sourcesOnline}/{sourcesTotal} SOURCES ONLINE
            {status?.data_mode === "demo" && <span className="ml-1 text-text-tertiary/70">· DEMO DATA</span>}
          </div>

          <div className="hidden sm:block mono-num text-[12px] text-text-tertiary tabular-nums w-[92px] text-right">
            {now ? now.toUTCString().slice(17, 25) + " UTC" : "--:--:-- UTC"}
          </div>

          {mode && <ModeBadge mode={mode.mode} />}
        </div>
      </div>
    </header>
  );
}

"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import useSWR from "swr";
import clsx from "clsx";
import { AnimatePresence, motion } from "framer-motion";
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
  const [menuOpen, setMenuOpen] = useState(false);

  const sourcesOnline = status?.data_sources.filter((s) => s.status === "online").length ?? 0;
  const sourcesTotal = status?.data_sources.length ?? 0;

  // Below `md` the inline nav is hidden, so this closes the drawer whenever
  // the route actually changes (e.g. after tapping a link in it).
  useEffect(() => {
    setMenuOpen(false);
  }, [pathname]);

  return (
    <header className="sticky top-0 z-50 border-b border-border glass">
      <div className="mx-auto flex h-14 max-w-[1600px] items-center gap-6 px-4 sm:px-6">
        <button
          type="button"
          onClick={() => setMenuOpen((v) => !v)}
          aria-expanded={menuOpen}
          aria-label={menuOpen ? "Close navigation menu" : "Open navigation menu"}
          className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md text-text-secondary transition-colors hover:bg-white/[0.06] hover:text-text-primary md:hidden"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
            {menuOpen ? (
              <path d="M6 6l12 12M18 6L6 18" strokeLinecap="round" />
            ) : (
              <path d="M4 7h16M4 12h16M4 17h16" strokeLinecap="round" />
            )}
          </svg>
        </button>

        <Link href="/" className="flex items-center gap-2.5 shrink-0">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" className="text-gold" aria-hidden>
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

        <div className="ml-auto flex items-center gap-3 sm:gap-4">
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

      <AnimatePresence>
        {menuOpen && (
          <motion.nav
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2, ease: [0.16, 1, 0.3, 1] }}
            className="overflow-hidden border-t border-border glass md:hidden"
          >
            <div className="flex flex-col gap-0.5 px-3 py-2 text-[14px]">
              {NAV.map((item) => {
                const active = item.href === "/" ? pathname === "/" : pathname?.startsWith(item.href);
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={clsx(
                      "rounded-md px-3 py-2.5 transition-colors",
                      active ? "bg-white/[0.06] text-text-primary" : "text-text-secondary hover:bg-white/[0.03] hover:text-text-primary"
                    )}
                  >
                    {item.label}
                  </Link>
                );
              })}
              <div className="mt-1 flex items-center justify-between border-t border-border px-3 pt-2.5 text-[11px] text-text-tertiary">
                <span className="flex items-center gap-1.5">
                  <span
                    className={clsx(
                      "h-1.5 w-1.5 rounded-full",
                      sourcesOnline === sourcesTotal && sourcesTotal > 0 ? "bg-gold" : "bg-danger"
                    )}
                  />
                  {sourcesOnline}/{sourcesTotal} sources online
                  {status?.data_mode === "demo" && <span className="text-text-tertiary/70">· demo data</span>}
                </span>
                <span className="mono-num">{now ? now.toUTCString().slice(17, 25) + " UTC" : "--:--:-- UTC"}</span>
              </div>
            </div>
          </motion.nav>
        )}
      </AnimatePresence>
    </header>
  );
}

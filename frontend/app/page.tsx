"use client";

import { useEffect } from "react";
import useSWR, { mutate } from "swr";
import Link from "next/link";
import { motion } from "framer-motion";
import { api } from "@/lib/api";
import PortfolioCard from "@/components/cards/PortfolioCard";
import MarketCard from "@/components/cards/MarketCard";
import EventCard from "@/components/cards/EventCard";
import SignalBadge from "@/components/cards/SignalBadge";
import PositionCard from "@/components/cards/PositionCard";
import SituationRoom from "@/components/dashboard/SituationRoom";
import DemoDataBadge from "@/components/common/DemoDataBadge";
import { Skeleton, SkeletonCard, SkeletonRow } from "@/components/common/Skeleton";
import { useLiveStream } from "@/lib/useLiveStream";
import { formatCompactCurrency, relativeTime, titleCase } from "@/lib/format";
import type { AssetQuote } from "@/lib/types";

function SectionLabel({ children, action }: { children: React.ReactNode; action?: React.ReactNode }) {
  return (
    <div className="mb-4 flex items-center justify-between">
      <h2 className="text-[12px] font-semibold uppercase tracking-[0.18em] text-text-tertiary">{children}</h2>
      {action}
    </div>
  );
}

export default function DashboardPage() {
  const { data: events, isLoading: eventsLoading } = useSWR("events", () => api.events({ limit: 30 }), {
    refreshInterval: 20000,
  });
  const { data: assets, isLoading: assetsLoading } = useSWR("assets", () => api.assets(), { refreshInterval: 10000 });
  const { data: signals, isLoading: signalsLoading } = useSWR(
    "signals",
    () => api.signals({ limit: 8, min_confidence: 0.3 }),
    { refreshInterval: 15000 }
  );
  const { data: portfolio } = useSWR("portfolio", () => api.portfolio(), { refreshInterval: 10000 });
  const { data: trades, isLoading: tradesLoading } = useSWR("recent-trades", () => api.portfolioTrades(), {
    refreshInterval: 15000,
  });
  const { data: status } = useSWR("system-status-dash", () => api.systemStatus(), { refreshInterval: 20000 });

  // Real-time push (SSE) in place of waiting on the next poll tick: every
  // update from /api/stream/live patches just the price/change_pct fields
  // the stream actually carries into the existing "assets" cache, and any
  // fresh signal nudges the signals list to refetch immediately instead of
  // sitting stale until its own interval fires.
  const { payload: live, connected: liveConnected, tick: liveTick } = useLiveStream();
  useEffect(() => {
    if (!live) return;
    // Guard on the REST fetch's own data (not just truthiness inside the
    // mutate updater): calling `mutate(key, fn, false)` before the first
    // real response has landed writes `undefined` into the cache, and SWR
    // then treats that as a newer value than the in-flight GET, silently
    // discarding its result once it resolves — the assets list would stay
    // empty forever instead of just until the first tick after load.
    if (live.quotes.length && assets) {
      mutate(
        "assets",
        (current?: AssetQuote[]) =>
          current?.map((a) => {
            const tick = live.quotes.find((q) => q.symbol === a.symbol);
            return tick ? { ...a, price: tick.price, change_pct: tick.change_pct } : a;
          }) ?? current,
        false
      );
    }
    if (live.signals.length) {
      mutate("signals");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [liveTick]);

  const topEvents = (events || []).slice().sort((a, b) => b.confidence - a.confidence).slice(0, 6);
  const featuredAssets = (assets || []).slice(0, 6);

  return (
    <div className="mx-auto max-w-[1600px] px-6 pb-24 pt-6">
      <SituationRoom events={events || []} />

      {/* HERO TEXT */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
        className="mb-8"
      >
        <div className="flex items-center gap-3">
          <h1 className="text-gradient-gold text-[26px] font-semibold tracking-tight">Global Market Status</h1>
          {status?.data_mode === "demo" && <DemoDataBadge />}
        </div>
        <p className="mt-1.5 max-w-2xl text-[14px] leading-relaxed text-text-secondary">
          What is happening in the real world right now that the market may not have fully priced yet — tracked from
          verified event through impact chain to signal, backtest, and paper trade.
        </p>
      </motion.div>

      {/* PORTFOLIO + SYSTEM INTELLIGENCE */}
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
        <div className="lg:col-span-2">
          {portfolio ? (
            <PortfolioCard portfolio={portfolio} />
          ) : (
            <div className="flex min-h-[220px] flex-col justify-between rounded-2xl border border-border glass p-7">
              <div className="flex items-start justify-between">
                <div>
                  <Skeleton className="h-3 w-24" />
                  <Skeleton className="mt-3 h-9 w-40" />
                  <Skeleton className="mt-3 h-3 w-28" />
                </div>
                <Skeleton className="h-3 w-12" />
              </div>
              <div className="mt-6 flex items-end justify-between border-t border-border pt-5">
                <Skeleton className="h-5 w-16" />
                <Skeleton className="h-5 w-16" />
                <Skeleton className="h-5 w-16" />
              </div>
            </div>
          )}
        </div>

        <div className="rounded-2xl border border-border glass p-5">
          <SectionLabel>System Intelligence</SectionLabel>
          <div className="space-y-2.5">
            {!status &&
              Array.from({ length: 3 }).map((_, i) => (
                <div key={i} className="flex items-center justify-between">
                  <Skeleton className="h-3 w-28" />
                  <Skeleton className="h-3 w-16" />
                </div>
              ))}
            {(status?.data_sources || []).map((s) => (
              <div key={s.name} className="flex items-center justify-between text-[12px]">
                <div className="flex items-center gap-2">
                  <span
                    className={`h-1.5 w-1.5 rounded-full ${
                      s.status === "online" ? "bg-gold" : s.status === "degraded" ? "bg-info" : "bg-danger"
                    }`}
                  />
                  <span className="text-text-secondary">{s.name.replace(/_/g, " ")}</span>
                </div>
                <span className="mono-num text-text-tertiary">
                  {s.status.toUpperCase()} {s.latency_ms ? `· ${Math.round(s.latency_ms)}ms` : ""}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* LIVE MARKET CARDS */}
      <div className="mt-10">
        <SectionLabel
          action={
            <div className="flex items-center gap-4">
              <span
                className={`flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider ${
                  liveConnected ? "text-gold-bright" : "text-text-tertiary"
                }`}
                title={liveConnected ? "Receiving live pushes from /api/stream/live" : "Falling back to periodic polling"}
              >
                <span className="relative flex h-1.5 w-1.5">
                  {liveConnected && (
                    <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-gold-bright opacity-60" />
                  )}
                  <span className={`relative inline-flex h-1.5 w-1.5 rounded-full ${liveConnected ? "bg-gold-bright" : "bg-text-tertiary"}`} />
                </span>
                {liveConnected ? "LIVE" : "POLLING"}
              </span>
              <Link href="/trading" className="text-[12px] text-gold-bright hover:underline">
                Trading terminal →
              </Link>
            </div>
          }
        >
          Live Market Cards
        </SectionLabel>
        <div className="grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-6">
          {assetsLoading && Array.from({ length: 6 }).map((_, i) => <SkeletonCard key={i} className="min-h-[200px]" />)}
          {featuredAssets.map((asset) => {
            const topSignal = (signals || []).find((s) => s.asset_symbol === asset.symbol);
            return <MarketCard key={asset.symbol} asset={asset} topSignal={topSignal} />;
          })}
          {!assetsLoading && featuredAssets.length === 0 && (
            <div className="col-span-full rounded-xl border border-dashed border-border p-8 text-center text-[13px] text-text-tertiary">
              No tracked assets.
            </div>
          )}
        </div>
      </div>

      {/* TOP EVENTS */}
      <div className="mt-10">
        <SectionLabel action={<span className="text-[11px] text-text-tertiary">{events?.length ?? 0} tracked</span>}>
          Top Market-Relevant Events
        </SectionLabel>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {eventsLoading && Array.from({ length: 3 }).map((_, i) => <SkeletonCard key={i} className="h-[176px]" />)}
          {topEvents.map((event) => (
            <EventCard key={event.event_id} event={event} />
          ))}
          {!eventsLoading && topEvents.length === 0 && (
            <div className="col-span-full rounded-xl border border-dashed border-border p-8 text-center text-[13px] text-text-tertiary">
              No events tracked yet.
            </div>
          )}
        </div>
      </div>

      <div className="mt-10 grid grid-cols-1 gap-8 lg:grid-cols-3">
        {/* ACTIVE SIGNALS */}
        <div className="lg:col-span-2">
          <SectionLabel action={<Link href="/alerts" className="text-[12px] text-gold-bright hover:underline">Alert center →</Link>}>
            Active Signals
          </SectionLabel>
          <div className="overflow-hidden rounded-2xl border border-border glass">
            <div className="overflow-x-auto">
            <table className="w-full min-w-[520px] text-[13px]">
              <tbody>
                {signalsLoading && Array.from({ length: 5 }).map((_, i) => <SkeletonRow key={i} cols={5} />)}
                {(signals || []).map((s, i) => (
                  <tr key={s.signal_id} className={i !== 0 ? "border-t border-border" : ""}>
                    <td className="px-4 py-3 font-semibold text-text-primary">{s.asset_symbol}</td>
                    <td className="px-4 py-3">
                      <SignalBadge direction={s.direction} confidence={s.confidence} size="sm" />
                    </td>
                    <td className="px-4 py-3 text-text-tertiary">{titleCase(s.strategy)}</td>
                    <td className="px-4 py-3 text-text-tertiary mono-num">{s.expected_horizon}</td>
                    <td className="px-4 py-3 text-right text-text-tertiary">{relativeTime(s.signal_time)}</td>
                  </tr>
                ))}
                {!signalsLoading && (!signals || signals.length === 0) && (
                  <tr>
                    <td className="px-4 py-8 text-center text-text-tertiary" colSpan={5}>
                      No active signals yet.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
            </div>
          </div>
        </div>

        {/* RECENT TRADES */}
        <div>
          <SectionLabel action={<Link href="/performance" className="text-[12px] text-gold-bright hover:underline">Performance →</Link>}>
            Recent Trades
          </SectionLabel>
          <div className="space-y-2">
            {tradesLoading &&
              Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="flex items-center justify-between rounded-xl border border-border glass px-4 py-3">
                  <div className="space-y-1.5">
                    <Skeleton className="h-3 w-24" />
                    <Skeleton className="h-2.5 w-14" />
                  </div>
                  <Skeleton className="h-3.5 w-16" />
                </div>
              ))}
            {(trades || []).slice(0, 6).map((t) => (
              <div key={t.id} className="flex items-center justify-between rounded-xl border border-border glass px-4 py-3 text-[12px]">
                <div>
                  <div className="font-semibold text-text-primary">
                    {t.side.toUpperCase()} {t.asset_symbol}
                  </div>
                  <div className="text-text-tertiary">{relativeTime(t.created_at)}</div>
                </div>
                <div className={`mono-num font-semibold ${t.realized_pnl && t.realized_pnl < 0 ? "text-danger-bright" : "text-gold-bright"}`}>
                  {t.realized_pnl != null ? formatCompactCurrency(t.realized_pnl) : "OPEN"}
                </div>
              </div>
            ))}
            {!tradesLoading && (!trades || trades.length === 0) && (
              <div className="rounded-xl border border-border glass px-4 py-8 text-center text-[12px] text-text-tertiary">
                No trades yet.
              </div>
            )}
          </div>
        </div>
      </div>

      {/* PORTFOLIO POSITIONS */}
      {portfolio && portfolio.positions.length > 0 && (
        <div className="mt-10">
          <SectionLabel>Open Positions</SectionLabel>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {portfolio.positions.map((p) => (
              <PositionCard key={p.asset_symbol} position={p} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

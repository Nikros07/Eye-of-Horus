"use client";

import useSWR from "swr";
import Link from "next/link";
import { motion } from "framer-motion";
import { api } from "@/lib/api";
import PortfolioCard from "@/components/cards/PortfolioCard";
import MarketCard from "@/components/cards/MarketCard";
import EventCard from "@/components/cards/EventCard";
import SignalBadge from "@/components/cards/SignalBadge";
import PositionCard from "@/components/cards/PositionCard";
import GlobalGlobe from "@/components/globe/GlobalGlobe";
import DemoDataBadge from "@/components/common/DemoDataBadge";
import { formatCompactCurrency, relativeTime, titleCase } from "@/lib/format";

function SectionLabel({ children, action }: { children: React.ReactNode; action?: React.ReactNode }) {
  return (
    <div className="mb-4 flex items-center justify-between">
      <h2 className="text-[12px] font-semibold uppercase tracking-[0.18em] text-text-tertiary">{children}</h2>
      {action}
    </div>
  );
}

export default function DashboardPage() {
  const { data: events } = useSWR("events", () => api.events({ limit: 30 }), { refreshInterval: 20000 });
  const { data: assets } = useSWR("assets", () => api.assets(), { refreshInterval: 10000 });
  const { data: signals } = useSWR("signals", () => api.signals({ limit: 8, min_confidence: 0.3 }), {
    refreshInterval: 15000,
  });
  const { data: portfolio } = useSWR("portfolio", () => api.portfolio(), { refreshInterval: 10000 });
  const { data: trades } = useSWR("recent-trades", () => api.portfolioTrades(), { refreshInterval: 15000 });
  const { data: status } = useSWR("system-status-dash", () => api.systemStatus(), { refreshInterval: 20000 });

  const topEvents = (events || []).slice().sort((a, b) => b.confidence - a.confidence).slice(0, 6);
  const featuredAssets = (assets || []).slice(0, 6);

  return (
    <div className="mx-auto max-w-[1600px] px-6 pb-24 pt-8">
      {/* HERO */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, ease: "easeOut" }}
        className="mb-8"
      >
        <div className="flex items-center gap-3">
          <h1 className="text-[26px] font-semibold tracking-tight text-text-primary">Global Market Status</h1>
          {status?.data_mode === "demo" && <DemoDataBadge />}
        </div>
        <p className="mt-1.5 max-w-2xl text-[14px] leading-relaxed text-text-secondary">
          What is happening in the real world right now that the market may not have fully priced yet — tracked from
          verified event through impact chain to signal, backtest, and paper trade.
        </p>
      </motion.div>

      {/* PORTFOLIO + GLOBE */}
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-5">
        <div className="lg:col-span-2 space-y-5">
          {portfolio && <PortfolioCard portfolio={portfolio} />}

          <div className="rounded-2xl border border-border glass p-5">
            <SectionLabel>System Intelligence</SectionLabel>
            <div className="space-y-2.5">
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

        <div className="lg:col-span-3 overflow-hidden rounded-2xl border border-border glass">
          <div className="flex items-center justify-between px-5 pt-5">
            <SectionLabel>Global Event Map</SectionLabel>
          </div>
          <GlobalGlobe events={events || []} className="h-[380px] w-full cursor-grab active:cursor-grabbing" />
        </div>
      </div>

      {/* LIVE MARKET CARDS */}
      <div className="mt-10">
        <SectionLabel action={<Link href="/trading" className="text-[12px] text-gold-bright hover:underline">Trading terminal →</Link>}>
          Live Market Cards
        </SectionLabel>
        <div className="grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-6">
          {featuredAssets.map((asset) => {
            const topSignal = (signals || []).find((s) => s.asset_symbol === asset.symbol);
            return <MarketCard key={asset.symbol} asset={asset} topSignal={topSignal} />;
          })}
        </div>
      </div>

      {/* TOP EVENTS */}
      <div className="mt-10">
        <SectionLabel action={<span className="text-[11px] text-text-tertiary">{events?.length ?? 0} tracked</span>}>
          Top Market-Relevant Events
        </SectionLabel>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {topEvents.map((event) => (
            <EventCard key={event.event_id} event={event} />
          ))}
        </div>
      </div>

      <div className="mt-10 grid grid-cols-1 gap-8 lg:grid-cols-3">
        {/* ACTIVE SIGNALS */}
        <div className="lg:col-span-2">
          <SectionLabel action={<Link href="/alerts" className="text-[12px] text-gold-bright hover:underline">Alert center →</Link>}>
            Active Signals
          </SectionLabel>
          <div className="overflow-hidden rounded-2xl border border-border glass">
            <table className="w-full text-[13px]">
              <tbody>
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
                {(!signals || signals.length === 0) && (
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

        {/* RECENT TRADES */}
        <div>
          <SectionLabel action={<Link href="/performance" className="text-[12px] text-gold-bright hover:underline">Performance →</Link>}>
            Recent Trades
          </SectionLabel>
          <div className="space-y-2">
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
            {(!trades || trades.length === 0) && (
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

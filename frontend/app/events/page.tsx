"use client";

import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import useSWR from "swr";
import { motion } from "framer-motion";
import { api } from "@/lib/api";
import ImpactChain from "@/components/impact/ImpactChain";
import SignalBadge from "@/components/cards/SignalBadge";
import DemoDataBadge from "@/components/common/DemoDataBadge";
import EquityCurveChart from "@/components/charts/EquityCurveChart";
import { formatConfidence, relativeTime, severityColor, titleCase, verificationStyle } from "@/lib/format";
import clsx from "clsx";

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <motion.section
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="rounded-2xl border border-border glass p-6"
    >
      <h2 className="mb-4 text-[12px] font-semibold uppercase tracking-[0.18em] text-text-tertiary">{title}</h2>
      {children}
    </motion.section>
  );
}

function ResearchList({ label, items, tone }: { label: string; items: string[]; tone: string }) {
  if (!items?.length) return null;
  return (
    <div>
      <div className={clsx("text-[11px] font-bold uppercase tracking-wider", tone)}>{label}</div>
      <ul className="mt-2 space-y-1.5">
        {items.map((item, i) => (
          <li key={i} className="text-[13px] leading-relaxed text-text-secondary">
            {item}
          </li>
        ))}
      </ul>
    </div>
  );
}

function EventDetailContent({ id }: { id: string }) {
  const { data: event } = useSWR(id ? ["event", id] : null, () => api.event(id));
  const { data: analogues } = useSWR(id ? ["analogues", id] : null, () => api.historicalAnalogues(id));
  const { data: signals } = useSWR(id ? ["event-signals", id] : null, () => api.signals({ limit: 100 }));
  const { data: research } = useSWR(id ? ["research", id] : null, () => api.eventResearch(id));
  const [priceSymbol, setPriceSymbol] = useState<string | null>(null);

  const eventSignals = (signals || []).filter((s) => s.event_id === id);
  const topLink = event?.impact_links?.[0];
  const activeSymbol = priceSymbol || topLink?.asset_symbol;

  const { data: priceHistory } = useSWR(
    activeSymbol ? ["event-price", activeSymbol] : null,
    () => api.assetHistory(activeSymbol as string, 168)
  );

  if (!id) {
    return <div className="mx-auto max-w-4xl px-6 py-24 text-center text-text-tertiary">No event selected.</div>;
  }

  if (!event) {
    return <div className="mx-auto max-w-4xl px-6 py-24 text-center text-text-tertiary">Loading event…</div>;
  }

  return (
    <div className="mx-auto max-w-[1200px] px-6 pb-24 pt-8">
      {/* HERO */}
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="mb-8">
        <div className="flex flex-wrap items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-text-tertiary">
          {titleCase(event.event_type)}
          {event.is_demo && <DemoDataBadge />}
          <span
            className={clsx("rounded-full border px-2 py-0.5 text-[9px]", verificationStyle[event.verification_status])}
          >
            {event.verification_status}
          </span>
        </div>
        <h1 className="text-gradient-gold mt-2 text-[30px] font-semibold leading-tight">{event.title}</h1>
        <div className="mt-2 flex flex-wrap items-center gap-4 text-[13px] text-text-secondary">
          <span>{event.location_name || "Location unknown"}</span>
          <span className={clsx("font-bold uppercase", severityColor[event.severity])}>{event.severity} impact</span>
          <span className="mono-num">{formatConfidence(event.confidence)} confidence</span>
          <span>{relativeTime(event.timestamp)}</span>
        </div>
      </motion.div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          <Panel title="Timeline">
            <div className="space-y-3 text-[13px]">
              <div className="flex justify-between border-b border-border pb-2">
                <span className="text-text-tertiary">First seen</span>
                <span className="mono-num text-text-primary">{new Date(event.first_seen).toLocaleString()}</span>
              </div>
              <div className="flex justify-between border-b border-border pb-2">
                <span className="text-text-tertiary">Last updated</span>
                <span className="mono-num text-text-primary">{new Date(event.last_updated).toLocaleString()}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-text-tertiary">Available to system at</span>
                <span className="mono-num text-text-primary">{new Date(event.availability_time).toLocaleString()}</span>
              </div>
            </div>
          </Panel>

          <Panel title="Evidence">
            <div className="space-y-3">
              {event.evidence.map((ev) => (
                <div key={ev.id} className="rounded-xl border border-border bg-white/[0.02] p-3.5">
                  <div className="flex items-center justify-between text-[10px] font-semibold uppercase tracking-wider text-text-tertiary">
                    <span>
                      {ev.kind} · {ev.source}
                    </span>
                    {ev.is_demo && <DemoDataBadge />}
                  </div>
                  <p className="mt-1.5 text-[13px] leading-relaxed text-text-secondary">{ev.content}</p>
                </div>
              ))}
              {event.evidence.length === 0 && <p className="text-[13px] text-text-tertiary">No evidence on file.</p>}
            </div>
          </Panel>

          <Panel title="Infrastructure → Supply Chain → Market Exposure">
            <div className="space-y-6">
              {event.impact_links.map((link) => (
                <div key={link.id}>
                  <ImpactChain link={link} />
                </div>
              ))}
              {event.impact_links.length === 0 && (
                <p className="text-[13px] text-text-tertiary">No impact chain computed for this event.</p>
              )}
            </div>
          </Panel>

          {priceHistory && (
            <Panel title={`Market Response — ${activeSymbol}`}>
              <div className="mb-3 flex gap-2">
                {event.impact_links.map((link) => (
                  <button
                    key={link.asset_symbol}
                    onClick={() => setPriceSymbol(link.asset_symbol)}
                    className={clsx(
                      "rounded-md border px-2.5 py-1 text-[11px] font-medium transition-colors",
                      activeSymbol === link.asset_symbol
                        ? "border-gold/40 bg-gold/10 text-gold-bright"
                        : "border-border text-text-tertiary hover:text-text-secondary"
                    )}
                  >
                    {link.asset_symbol}
                  </button>
                ))}
              </div>
              <EquityCurveChart data={priceHistory.bars.map((b) => ({ ts: b.ts, equity: b.close }))} height={220} />
            </Panel>
          )}

          <Panel title="Historical Analogues">
            <div className="space-y-2">
              {(analogues || []).map((a) => (
                <a
                  key={a.event_id}
                  href={`/events?id=${a.event_id}`}
                  className="flex items-center justify-between rounded-lg border border-border px-3.5 py-2.5 text-[13px] transition-colors hover:border-gold/30"
                >
                  <span className="text-text-secondary">{a.title}</span>
                  <span className="mono-num text-text-tertiary">{relativeTime(a.timestamp)}</span>
                </a>
              ))}
              {(!analogues || analogues.length === 0) && (
                <p className="text-[13px] text-text-tertiary">
                  INSUFFICIENT EVIDENCE — no historical analogues of this event type on file yet.
                </p>
              )}
            </div>
          </Panel>
        </div>

        <div className="space-y-6">
          <Panel title="Signals">
            <div className="space-y-3">
              {eventSignals.map((s) => (
                <a
                  key={s.signal_id}
                  href={`/trading?signal=${s.signal_id}`}
                  className="block rounded-xl border border-border bg-white/[0.02] p-3.5 transition-colors hover:border-gold/30"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-[13px] font-semibold text-text-primary">{s.asset_symbol}</span>
                    <SignalBadge direction={s.direction} confidence={s.confidence} size="sm" />
                  </div>
                  <div className="mt-2 text-[12px] leading-relaxed text-text-secondary">{s.reasoning}</div>
                  <div className="mt-2 flex items-center justify-between text-[11px] text-text-tertiary">
                    <span>{titleCase(s.strategy)}</span>
                    <span className="mono-num">{s.expected_horizon}</span>
                  </div>
                </a>
              ))}
              {eventSignals.length === 0 && (
                <p className="text-[13px] text-text-tertiary">No signals generated for this event.</p>
              )}
            </div>
          </Panel>

          <Panel title="AI Research">
            {research ? (
              <div className="space-y-4">
                <ResearchList label="Observed" items={research.observed} tone="text-info-bright" />
                <ResearchList label="Derived" items={research.derived} tone="text-gold-bright" />
                <ResearchList label="Hypothesis" items={research.hypothesis} tone="text-signal-bright" />
                <ResearchList label="Uncertain" items={research.uncertain} tone="text-text-tertiary" />
                <div className="flex items-center justify-between border-t border-border pt-3 text-[12px]">
                  <span className="text-text-tertiary">Market already priced?</span>
                  <span className="font-bold text-text-primary">{research.market_already_priced}</span>
                </div>
                <div className="text-[10px] uppercase tracking-wider text-text-tertiary">
                  Source: {research.source === "claude" ? "Claude API" : "deterministic synthesis"}
                </div>
              </div>
            ) : (
              <p className="text-[13px] text-text-tertiary">Loading research…</p>
            )}
          </Panel>
        </div>
      </div>
    </div>
  );
}

function EventDetailInner() {
  const searchParams = useSearchParams();
  const id = searchParams.get("id") || "";
  return <EventDetailContent id={id} />;
}

// useSearchParams() requires a Suspense boundary even in client components —
// this is also what makes the route compatible with `output: "export"" (the
// GitHub Pages build): a query-param page needs no generateStaticParams,
// unlike a [id] dynamic segment would.
export default function EventDetailPage() {
  return (
    <Suspense fallback={<div className="mx-auto max-w-4xl px-6 py-24 text-center text-text-tertiary">Loading…</div>}>
      <EventDetailInner />
    </Suspense>
  );
}

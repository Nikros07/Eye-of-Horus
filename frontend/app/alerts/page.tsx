"use client";

import { useMemo, useState } from "react";
import useSWR from "swr";
import clsx from "clsx";
import { motion } from "framer-motion";
import { api } from "@/lib/api";
import { relativeTime, titleCase } from "@/lib/format";

const SEVERITIES = ["critical", "high", "medium", "low"] as const;

const severityStyle: Record<string, string> = {
  critical: "border-danger/40 bg-danger/10 text-danger-bright",
  high: "border-gold/40 bg-gold/10 text-gold-bright",
  medium: "border-info/40 bg-info/10 text-info-bright",
  low: "border-white/10 bg-white/5 text-text-secondary",
};

const pricingStatusLabel: Record<string, string> = {
  unpriced: "UNPRICED",
  partially_priced: "PARTIALLY PRICED",
  priced: "PRICED",
};

const WINDOWS = [
  { label: "24h", hours: 24 },
  { label: "3d", hours: 72 },
  { label: "7d", hours: 168 },
  { label: "30d", hours: 720 },
];

export default function AlertsPage() {
  const [severity, setSeverity] = useState<string | null>(null);
  const [assetSymbol, setAssetSymbol] = useState<string | null>(null);
  const [hours, setHours] = useState(72);

  const { data: assets } = useSWR("alerts-assets", () => api.assets());
  const { data: alerts, isLoading } = useSWR(
    ["alerts", severity, assetSymbol, hours],
    () => api.alerts({ severity: severity || undefined, asset_symbol: assetSymbol || undefined, hours, limit: 60 }),
    { refreshInterval: 15000 }
  );

  const counts = useMemo(() => {
    const c: Record<string, number> = { critical: 0, high: 0, medium: 0, low: 0 };
    for (const a of alerts || []) c[a.severity] = (c[a.severity] ?? 0) + 1;
    return c;
  }, [alerts]);

  return (
    <div className="mx-auto max-w-[1200px] px-6 pb-24 pt-8">
      <h1 className="text-gradient-gold text-[24px] font-semibold">Alert Center</h1>
      <p className="mt-1 text-[13px] text-text-secondary">Derived directly from the signal engine — never stored separately.</p>

      {/* SUMMARY STRIP */}
      <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-5">
        <div className="rounded-xl border border-border glass px-4 py-3">
          <div className="text-[10px] uppercase tracking-wider text-text-tertiary">Total</div>
          <div className="mono-num mt-1 text-[18px] font-semibold text-text-primary">{alerts?.length ?? "—"}</div>
        </div>
        {SEVERITIES.map((s) => (
          <div key={s} className="rounded-xl border border-border glass px-4 py-3">
            <div className="text-[10px] uppercase tracking-wider text-text-tertiary">{s}</div>
            <div className={clsx("mono-num mt-1 text-[18px] font-semibold", severityStyle[s].split(" ").pop())}>
              {alerts ? counts[s] : "—"}
            </div>
          </div>
        ))}
      </div>

      {/* FILTERS */}
      <div className="mt-6 flex flex-wrap items-center gap-2">
        <button
          onClick={() => setSeverity(null)}
          className={clsx(
            "rounded-full border px-3 py-1.5 text-[11px] font-semibold uppercase tracking-wider transition-colors",
            !severity ? "border-white/20 bg-white/10 text-text-primary" : "border-border text-text-tertiary hover:text-text-secondary"
          )}
        >
          All
        </button>
        {SEVERITIES.map((s) => (
          <button
            key={s}
            onClick={() => setSeverity(s)}
            className={clsx(
              "rounded-full border px-3 py-1.5 text-[11px] font-semibold uppercase tracking-wider transition-colors",
              severity === s ? severityStyle[s] : "border-border text-text-tertiary hover:text-text-secondary"
            )}
          >
            {s}
          </button>
        ))}

        <div className="ml-auto flex items-center gap-2">
          <select
            value={assetSymbol ?? ""}
            onChange={(e) => setAssetSymbol(e.target.value || null)}
            className="rounded-full border border-border bg-white/[0.03] px-3 py-1.5 text-[11px] font-medium text-text-secondary outline-none focus:border-gold/40"
          >
            <option value="" className="bg-ink-900">
              All assets
            </option>
            {(assets || []).map((a) => (
              <option key={a.symbol} value={a.symbol} className="bg-ink-900">
                {a.symbol}
              </option>
            ))}
          </select>

          <div className="flex rounded-full border border-border p-0.5">
            {WINDOWS.map((w) => (
              <button
                key={w.hours}
                onClick={() => setHours(w.hours)}
                className={clsx(
                  "rounded-full px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wider transition-colors",
                  hours === w.hours ? "bg-white/10 text-text-primary" : "text-text-tertiary hover:text-text-secondary"
                )}
              >
                {w.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="mt-6 space-y-3">
        {isLoading &&
          Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="rounded-xl border border-border glass p-4">
              <div className="flex items-center gap-3">
                <div className="skeleton h-4 w-14 rounded-full" />
                <div className="skeleton h-3.5 w-16 rounded" />
                <div className="skeleton h-3.5 w-40 rounded" />
              </div>
              <div className="mt-3 flex gap-4">
                <div className="skeleton h-3 w-20 rounded" />
                <div className="skeleton h-3 w-24 rounded" />
                <div className="skeleton h-3 w-16 rounded" />
              </div>
            </div>
          ))}

        {!isLoading &&
          (alerts || []).map((a, i) => (
            <motion.div
              key={a.signal_id}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: Math.min(i * 0.03, 0.4) }}
              className="rounded-xl border border-border glass p-4"
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-3">
                  <span className={clsx("rounded-full border px-2 py-0.5 text-[9px] font-bold uppercase", severityStyle[a.severity])}>
                    {a.severity}
                  </span>
                  <span className="text-[14px] font-semibold text-text-primary">{a.asset_symbol}</span>
                  <span className="text-[12px] text-text-tertiary">{a.event_title || titleCase(a.event_type || "")}</span>
                </div>
                <span className="text-[11px] text-text-tertiary">{relativeTime(a.signal_time)}</span>
              </div>
              <div className="mt-2.5 flex flex-wrap items-center gap-4 text-[12px]">
                <span className={a.direction === "bullish" ? "font-semibold text-gold-bright" : "font-semibold text-danger-bright"}>
                  {a.direction.toUpperCase()} BIAS
                </span>
                <span className="text-text-tertiary">Confidence {Math.round(a.confidence * 100)}%</span>
                <span className="text-text-tertiary">Horizon {a.expected_horizon}</span>
                <span className="text-text-tertiary">{titleCase(a.strategy)}</span>
                <span className="ml-auto rounded border border-border px-2 py-0.5 text-[10px] uppercase tracking-wider text-text-tertiary">
                  {pricingStatusLabel[a.status] || a.status}
                </span>
              </div>
            </motion.div>
          ))}
        {!isLoading && (!alerts || alerts.length === 0) && (
          <div className="rounded-xl border border-border glass p-10 text-center text-[13px] text-text-tertiary">
            No alerts in this window.
          </div>
        )}
      </div>
    </div>
  );
}

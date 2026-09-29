"use client";

import { useState } from "react";
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

export default function AlertsPage() {
  const [severity, setSeverity] = useState<string | null>(null);
  const { data: alerts } = useSWR(["alerts", severity], () => api.alerts({ severity: severity || undefined, limit: 60 }), {
    refreshInterval: 15000,
  });

  return (
    <div className="mx-auto max-w-[1200px] px-6 pb-24 pt-8">
      <h1 className="text-[24px] font-semibold text-text-primary">Alert Center</h1>
      <p className="mt-1 text-[13px] text-text-secondary">Derived directly from the signal engine — never stored separately.</p>

      <div className="mt-6 flex gap-2">
        <button
          onClick={() => setSeverity(null)}
          className={clsx(
            "rounded-full border px-3 py-1.5 text-[11px] font-semibold uppercase tracking-wider transition-colors",
            !severity ? "border-white/20 bg-white/10 text-text-primary" : "border-border text-text-tertiary"
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
              severity === s ? severityStyle[s] : "border-border text-text-tertiary"
            )}
          >
            {s}
          </button>
        ))}
      </div>

      <div className="mt-6 space-y-3">
        {(alerts || []).map((a, i) => (
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
        {(!alerts || alerts.length === 0) && (
          <div className="rounded-xl border border-border glass p-10 text-center text-[13px] text-text-tertiary">
            No alerts in this window.
          </div>
        )}
      </div>
    </div>
  );
}

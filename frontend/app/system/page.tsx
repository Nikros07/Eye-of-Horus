"use client";

import useSWR from "swr";
import clsx from "clsx";
import { api } from "@/lib/api";
import { formatCompactCurrency, formatPercent, formatRatio, relativeTime } from "@/lib/format";

const statusStyle: Record<string, string> = {
  online: "border-gold/40 bg-gold/10 text-gold-bright",
  degraded: "border-info/40 bg-info/10 text-info-bright",
  offline: "border-danger/40 bg-danger/10 text-danger-bright",
};

export default function SystemPage() {
  const { data: status } = useSWR("system-page", () => api.systemStatus(), { refreshInterval: 10000 });
  const { data: risk } = useSWR("system-risk", () => api.risk(), { refreshInterval: 10000 });

  return (
    <div className="mx-auto max-w-[1200px] px-6 pb-24 pt-8">
      <h1 className="text-gradient-gold text-[24px] font-semibold">System Status</h1>
      <p className="mt-1 text-[13px] text-text-secondary">
        {status?.app} · {status?.environment} · data mode:{" "}
        <span className="font-semibold text-text-primary">{status?.data_mode}</span> · live trading:{" "}
        <span className={status?.live_trading_enabled ? "text-danger-bright" : "text-gold-bright"}>
          {status?.live_trading_enabled ? "ENABLED" : "DISABLED"}
        </span>
      </p>

      <div className="mt-8">
        <h2 className="mb-4 text-[12px] font-semibold uppercase tracking-[0.18em] text-text-tertiary">Data Sources</h2>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {(status?.data_sources || []).map((s) => (
            <div key={s.name} className="rounded-2xl border border-border glass p-5">
              <div className="flex items-start justify-between">
                <div className="text-[13px] font-semibold text-text-primary">{s.name.replace(/_/g, " ")}</div>
                <span className={clsx("rounded-full border px-2 py-0.5 text-[9px] font-bold uppercase", statusStyle[s.status])}>
                  {s.status}
                </span>
              </div>
              <div className="mt-3 space-y-1.5 text-[11px] text-text-tertiary">
                <div className="flex justify-between">
                  <span>Kind</span>
                  <span className="text-text-secondary">{s.kind}</span>
                </div>
                <div className="flex justify-between">
                  <span>Latency</span>
                  <span className="mono-num text-text-secondary">{s.latency_ms ? `${Math.round(s.latency_ms)}ms` : "—"}</span>
                </div>
                <div className="flex justify-between">
                  <span>Last success</span>
                  <span className="text-text-secondary">{s.last_success_at ? relativeTime(s.last_success_at) : "—"}</span>
                </div>
                {s.last_error && <div className="mt-2 rounded bg-danger/10 p-2 text-danger-bright">{s.last_error}</div>}
                {s.is_demo && <div className="mt-1 text-text-tertiary/70">DEMO source — replace with live connector in production.</div>}
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="mt-8 grid grid-cols-2 gap-4 md:grid-cols-4">
        <div className="rounded-xl border border-border glass p-4">
          <div className="text-[10px] uppercase tracking-wider text-text-tertiary">Events Tracked</div>
          <div className="mono-num mt-1.5 text-[20px] font-semibold text-text-primary">{status?.totals.events ?? "—"}</div>
        </div>
        <div className="rounded-xl border border-border glass p-4">
          <div className="text-[10px] uppercase tracking-wider text-text-tertiary">Signals Generated</div>
          <div className="mono-num mt-1.5 text-[20px] font-semibold text-text-primary">{status?.totals.signals ?? "—"}</div>
        </div>
        <div className="rounded-xl border border-border glass p-4">
          <div className="text-[10px] uppercase tracking-wider text-text-tertiary">Kill Switch</div>
          <div className={clsx("mono-num mt-1.5 text-[20px] font-semibold", risk?.kill_switch_active ? "text-danger-bright" : "text-gold-bright")}>
            {risk?.kill_switch_active ? "ACTIVE" : "OFF"}
          </div>
        </div>
        <div className="rounded-xl border border-border glass p-4">
          <div className="text-[10px] uppercase tracking-wider text-text-tertiary">Market Provider</div>
          <div className="mono-num mt-1.5 text-[20px] font-semibold text-text-primary">{status?.market_data_provider ?? "—"}</div>
        </div>
      </div>

      <div className="mt-8">
        <h2 className="mb-4 text-[12px] font-semibold uppercase tracking-[0.18em] text-text-tertiary">
          Risk Management
        </h2>
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          <div className="rounded-2xl border border-border glass p-5 lg:col-span-2">
            <div className="text-[11px] font-semibold uppercase tracking-wider text-text-tertiary">Current Exposure</div>
            <div className="mt-3 grid grid-cols-3 gap-4">
              <div>
                <div className="text-[10px] uppercase tracking-wider text-text-tertiary">Exposure</div>
                <div className="mono-num mt-1 text-[16px] font-semibold text-text-primary">
                  {risk ? formatRatio(risk.current.exposure_pct) : "—"}
                </div>
              </div>
              <div>
                <div className="text-[10px] uppercase tracking-wider text-text-tertiary">Drawdown</div>
                <div className="mono-num mt-1 text-[16px] font-semibold text-danger-bright">
                  {risk ? formatPercent(-risk.current.current_drawdown_pct, 1) : "—"}
                </div>
              </div>
              <div>
                <div className="text-[10px] uppercase tracking-wider text-text-tertiary">Daily P&amp;L</div>
                <div
                  className={clsx(
                    "mono-num mt-1 text-[16px] font-semibold",
                    (risk?.current.daily_pnl ?? 0) >= 0 ? "text-gold-bright" : "text-danger-bright"
                  )}
                >
                  {risk ? formatCompactCurrency(risk.current.daily_pnl) : "—"}
                </div>
              </div>
            </div>

            <div className="mt-5 border-t border-border pt-4">
              <div className="text-[10px] uppercase tracking-wider text-text-tertiary">Position Concentration</div>
              <div className="mt-2.5 space-y-2">
                {Object.entries(risk?.current.position_concentration || {}).map(([symbol, pct]) => (
                  <div key={symbol} className="flex items-center gap-3 text-[12px]">
                    <span className="w-16 shrink-0 font-semibold text-text-primary">{symbol}</span>
                    <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-white/[0.06]">
                      <div className="h-full rounded-full bg-gold" style={{ width: `${Math.min(pct * 100, 100)}%` }} />
                    </div>
                    <span className="mono-num w-12 shrink-0 text-right text-text-tertiary">{formatRatio(pct, 0)}</span>
                  </div>
                ))}
                {(!risk || Object.keys(risk.current.position_concentration).length === 0) && (
                  <p className="text-[12px] text-text-tertiary">No open exposure.</p>
                )}
              </div>
            </div>
          </div>

          <div className="rounded-2xl border border-border glass p-5">
            <div className="text-[11px] font-semibold uppercase tracking-wider text-text-tertiary">Configured Limits</div>
            <div className="mt-3 space-y-2 text-[12px]">
              {[
                ["Max position size", risk ? formatRatio(risk.limits.max_position_size_pct, 0) : "—"],
                ["Max daily loss", risk ? formatRatio(risk.limits.max_daily_loss_pct, 0) : "—"],
                ["Max portfolio exposure", risk ? formatRatio(risk.limits.max_portfolio_exposure_pct, 0) : "—"],
                ["Max trades / day", risk ? String(risk.limits.max_trades_per_day) : "—"],
                ["Max drawdown", risk ? formatRatio(risk.limits.max_drawdown_pct, 0) : "—"],
                ["Cooldown", risk ? `${risk.limits.cooldown_seconds}s` : "—"],
              ].map(([label, value]) => (
                <div key={label} className="flex items-center justify-between border-b border-border/60 pb-2 last:border-0 last:pb-0">
                  <span className="text-text-tertiary">{label}</span>
                  <span className="mono-num font-semibold text-text-primary">{value}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

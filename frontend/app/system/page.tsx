"use client";

import useSWR, { mutate } from "swr";
import clsx from "clsx";
import { api } from "@/lib/api";
import Toggle from "@/components/common/Toggle";
import { Skeleton, SkeletonCard } from "@/components/common/Skeleton";
import { formatCompactCurrency, relativeTime } from "@/lib/format";

// Risk limits and current exposure are magnitudes, not signed deltas — a
// leading "+" (as lib/format's `formatPercent` adds for gains) would read as
// if a 10% position-size cap were somehow a gain.
function pct(value: number, digits = 0): string {
  return `${(value * 100).toFixed(digits)}%`;
}

const statusStyle: Record<string, string> = {
  online: "border-gold/40 bg-gold/10 text-gold-bright",
  degraded: "border-info/40 bg-info/10 text-info-bright",
  offline: "border-danger/40 bg-danger/10 text-danger-bright",
};

/** A labeled current-value-vs-limit bar. Turns from gold to danger as the
 * current value approaches or exceeds the configured limit. */
function LimitBar({ label, current, limit, format }: { label: string; current: number; limit: number; format: (v: number) => string }) {
  const pct = limit > 0 ? Math.min(current / limit, 1) : 0;
  const overLimit = limit > 0 && current > limit;
  return (
    <div>
      <div className="flex items-center justify-between text-[11px]">
        <span className="text-text-tertiary">{label}</span>
        <span className={clsx("mono-num font-semibold", overLimit ? "text-danger-bright" : "text-text-primary")}>
          {format(current)} <span className="text-text-tertiary font-normal">/ {format(limit)} limit</span>
        </span>
      </div>
      <div className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-white/[0.06]">
        <div
          className={clsx("h-full rounded-full transition-all", overLimit ? "bg-danger-bright" : pct > 0.75 ? "bg-gold" : "bg-gold-bright")}
          style={{ width: `${Math.max(pct * 100, current > 0 ? 2 : 0)}%` }}
        />
      </div>
    </div>
  );
}

export default function SystemPage() {
  const { data: status } = useSWR("system-page", () => api.systemStatus(), { refreshInterval: 10000 });
  const { data: risk, isLoading: riskLoading } = useSWR("system-risk", () => api.risk(), { refreshInterval: 10000 });

  async function toggleKillSwitch(active: boolean) {
    // Optimistic update so the control feels immediate — the Automatic
    // Trading toggle on the Trading Terminal follows the same pattern.
    mutate("system-risk", (cur) => (cur ? { ...cur, kill_switch_active: active } : cur), false);
    try {
      await api.setKillSwitch(active);
    } finally {
      mutate("system-risk");
    }
  }

  const concentration = Object.entries(risk?.current.position_concentration || {}).sort((a, b) => b[1] - a[1]);

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
          {!status && Array.from({ length: 3 }).map((_, i) => <SkeletonCard key={i} className="h-[140px]" />)}
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

      {/* RISK MANAGEMENT */}
      <div className="mt-10">
        <h2 className="mb-4 text-[12px] font-semibold uppercase tracking-[0.18em] text-text-tertiary">Risk Management</h2>

        {riskLoading && (
          <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
            <SkeletonCard className="h-[180px] lg:col-span-1" />
            <SkeletonCard className="h-[180px] lg:col-span-2" />
          </div>
        )}

        {risk && (
          <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
            {/* Kill switch control */}
            <div className="rounded-2xl border border-border glass p-5 lg:col-span-1">
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="text-[13px] font-semibold text-text-primary">Kill Switch</h3>
                  <p className="mt-1 text-[11px] leading-relaxed text-text-tertiary">
                    Halts all new order placement — manual, signal-executed, and auto-trade — the instant it&apos;s
                    active. Open positions are left alone.
                  </p>
                </div>
                <Toggle checked={risk.kill_switch_active} onChange={toggleKillSwitch} label="Kill switch" />
              </div>
              <div
                className={clsx(
                  "mt-4 rounded-lg border px-3 py-2 text-center text-[11px] font-bold uppercase tracking-wider",
                  risk.kill_switch_active ? "border-danger/40 bg-danger/10 text-danger-bright" : "border-gold/30 bg-gold/10 text-gold-bright"
                )}
              >
                {risk.kill_switch_active ? "Trading Halted" : "Trading Live"}
              </div>

              {concentration.length > 0 && (
                <div className="mt-5 border-t border-border pt-4">
                  <div className="text-[10px] uppercase tracking-wider text-text-tertiary">Position Concentration</div>
                  <div className="mt-2.5 space-y-2">
                    {concentration.map(([symbol, weight]) => (
                      <div key={symbol}>
                        <div className="flex justify-between text-[11px]">
                          <span className="text-text-secondary">{symbol}</span>
                          <span className="mono-num text-text-tertiary">{pct(weight, 0)}</span>
                        </div>
                        <div className="mt-1 h-1 w-full overflow-hidden rounded-full bg-white/[0.06]">
                          <div className="h-full rounded-full bg-signal" style={{ width: `${Math.max(weight * 100, 2)}%` }} />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Current exposure vs configured limits */}
            <div className="rounded-2xl border border-border glass p-5 lg:col-span-2">
              <h3 className="text-[13px] font-semibold text-text-primary">Exposure vs. Configured Limits</h3>
              <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
                <LimitBar
                  label="Portfolio exposure"
                  current={risk.current.exposure_pct}
                  limit={risk.limits.max_portfolio_exposure_pct}
                  format={(v) => pct(v, 0)}
                />
                <LimitBar
                  label="Current drawdown"
                  current={risk.current.current_drawdown_pct}
                  limit={risk.limits.max_drawdown_pct}
                  format={(v) => pct(v, 1)}
                />
              </div>

              <div className="mt-5 grid grid-cols-2 gap-4 border-t border-border pt-4 sm:grid-cols-4">
                <div>
                  <div className="text-[10px] uppercase tracking-wider text-text-tertiary">Equity</div>
                  <div className="mono-num mt-1 text-[15px] font-semibold text-text-primary">
                    {formatCompactCurrency(risk.current.equity)}
                  </div>
                </div>
                <div>
                  <div className="text-[10px] uppercase tracking-wider text-text-tertiary">Open Exposure</div>
                  <div className="mono-num mt-1 text-[15px] font-semibold text-text-primary">
                    {formatCompactCurrency(risk.current.open_exposure)}
                  </div>
                </div>
                <div>
                  <div className="text-[10px] uppercase tracking-wider text-text-tertiary">Daily P&amp;L</div>
                  <div
                    className={clsx(
                      "mono-num mt-1 text-[15px] font-semibold",
                      risk.current.daily_pnl >= 0 ? "text-gold-bright" : "text-danger-bright"
                    )}
                  >
                    {risk.current.daily_pnl >= 0 ? "+" : ""}
                    {formatCompactCurrency(risk.current.daily_pnl)}
                  </div>
                </div>
                <div>
                  <div className="text-[10px] uppercase tracking-wider text-text-tertiary">Cooldown</div>
                  <div className="mono-num mt-1 text-[15px] font-semibold text-text-primary">{risk.limits.cooldown_seconds}s</div>
                </div>
              </div>

              <div className="mt-5 border-t border-border pt-4">
                <div className="text-[10px] uppercase tracking-wider text-text-tertiary">Configured Limits</div>
                <div className="mt-2.5 grid grid-cols-2 gap-x-6 gap-y-1.5 text-[12px] sm:grid-cols-3">
                  <div className="flex justify-between gap-3">
                    <span className="text-text-tertiary">Max position size</span>
                    <span className="mono-num text-text-secondary">{pct(risk.limits.max_position_size_pct, 0)}</span>
                  </div>
                  <div className="flex justify-between gap-3">
                    <span className="text-text-tertiary">Max daily loss</span>
                    <span className="mono-num text-text-secondary">{pct(risk.limits.max_daily_loss_pct, 0)}</span>
                  </div>
                  <div className="flex justify-between gap-3">
                    <span className="text-text-tertiary">Max trades/day</span>
                    <span className="mono-num text-text-secondary">{risk.limits.max_trades_per_day}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

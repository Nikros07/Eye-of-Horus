"use client";

import { useState } from "react";
import useSWR from "swr";
import clsx from "clsx";
import { api } from "@/lib/api";
import EquityCurveChart from "@/components/charts/EquityCurveChart";
import { Skeleton } from "@/components/common/Skeleton";
import { formatCompactCurrency, formatPercent, titleCase } from "@/lib/format";
import type { BacktestResult, CompareResult } from "@/lib/types";

export default function BacktestLabPage() {
  const { data: strategies, isLoading: strategiesLoading } = useSWR("bt-strategies", () => api.strategies());

  const [strategy, setStrategy] = useState("multi_signal");
  const [capital, setCapital] = useState("10000");
  const [feeBps, setFeeBps] = useState("5");
  const [slipBps, setSlipBps] = useState("3");
  const [days, setDays] = useState("30");
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<BacktestResult | null>(null);
  const [compareResults, setCompareResults] = useState<CompareResult[] | null>(null);

  async function runBacktest() {
    setRunning(true);
    setResult(null);
    setCompareResults(null);
    try {
      const periodEnd = new Date();
      const periodStart = new Date(periodEnd.getTime() - parseInt(days) * 86400000);
      const res = await api.runBacktest({
        strategy,
        initial_capital: parseFloat(capital),
        transaction_cost_bps: parseFloat(feeBps),
        slippage_bps: parseFloat(slipBps),
        period_start: periodStart.toISOString(),
        period_end: periodEnd.toISOString(),
      });
      setResult(res);
    } finally {
      setRunning(false);
    }
  }

  async function runComparison() {
    setRunning(true);
    setResult(null);
    setCompareResults(null);
    try {
      const names = (strategies || []).map((s) => s.name);
      const res = await api.compareStrategies(names);
      setCompareResults(
        res.slice().sort((a, b) => (b.metrics.total_return_pct ?? -Infinity) - (a.metrics.total_return_pct ?? -Infinity))
      );
    } finally {
      setRunning(false);
    }
  }

  const bestStrategy = compareResults?.[0]?.strategy;
  const maxAbsReturn = compareResults
    ? Math.max(...compareResults.map((r) => Math.abs(r.metrics.total_return_pct ?? 0)), 0.0001)
    : 1;

  return (
    <div className="mx-auto max-w-[1500px] px-6 pb-24 pt-8">
      <h1 className="text-gradient-gold text-[24px] font-semibold">Backtest Lab</h1>
      <p className="mt-1 text-[13px] text-text-secondary">
        Event-driven backtests with enforced temporal integrity — no strategy ever sees data before its
        availability_time.
      </p>

      <div className="mt-6 grid grid-cols-1 gap-6 xl:grid-cols-[320px_1fr]">
        <div className="space-y-4 rounded-2xl border border-border glass p-5">
          <div>
            <label className="text-[11px] uppercase tracking-wider text-text-tertiary">Strategy</label>
            {strategiesLoading ? (
              <Skeleton className="mt-1.5 h-[38px] w-full" />
            ) : (
              <select
                value={strategy}
                onChange={(e) => setStrategy(e.target.value)}
                className="mt-1.5 w-full rounded-lg border border-border bg-white/[0.03] px-3 py-2 text-[13px] text-text-primary outline-none focus:border-gold/40"
              >
                {(strategies || []).map((s) => (
                  <option key={s.name} value={s.name} className="bg-ink-900">
                    {titleCase(s.name)}
                  </option>
                ))}
              </select>
            )}
            {strategies?.find((s) => s.name === strategy) && (
              <p className="mt-1.5 text-[11px] leading-relaxed text-text-tertiary">
                {strategies.find((s) => s.name === strategy)?.description}
              </p>
            )}
          </div>

          <div>
            <label className="text-[11px] uppercase tracking-wider text-text-tertiary">Period (days back)</label>
            <input
              value={days}
              onChange={(e) => setDays(e.target.value)}
              type="number"
              className="mt-1.5 w-full rounded-lg border border-border bg-white/[0.03] px-3 py-2 text-[13px] mono-num text-text-primary outline-none focus:border-gold/40"
            />
          </div>

          <div>
            <label className="text-[11px] uppercase tracking-wider text-text-tertiary">Capital</label>
            <input
              value={capital}
              onChange={(e) => setCapital(e.target.value)}
              type="number"
              className="mt-1.5 w-full rounded-lg border border-border bg-white/[0.03] px-3 py-2 text-[13px] mono-num text-text-primary outline-none focus:border-gold/40"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-[11px] uppercase tracking-wider text-text-tertiary">Fees (bps)</label>
              <input
                value={feeBps}
                onChange={(e) => setFeeBps(e.target.value)}
                type="number"
                className="mt-1.5 w-full rounded-lg border border-border bg-white/[0.03] px-3 py-2 text-[13px] mono-num text-text-primary outline-none focus:border-gold/40"
              />
            </div>
            <div>
              <label className="text-[11px] uppercase tracking-wider text-text-tertiary">Slippage (bps)</label>
              <input
                value={slipBps}
                onChange={(e) => setSlipBps(e.target.value)}
                type="number"
                className="mt-1.5 w-full rounded-lg border border-border bg-white/[0.03] px-3 py-2 text-[13px] mono-num text-text-primary outline-none focus:border-gold/40"
              />
            </div>
          </div>

          <button
            onClick={runBacktest}
            disabled={running}
            className="w-full rounded-lg border border-gold/40 bg-gold/10 py-2.5 text-[13px] font-semibold text-gold-bright transition-colors hover:bg-gold/20 disabled:opacity-40"
          >
            {running ? "Running…" : "Run Backtest"}
          </button>
          <button
            onClick={runComparison}
            disabled={running || strategiesLoading}
            className="w-full rounded-lg border border-border py-2.5 text-[13px] font-medium text-text-secondary transition-colors hover:border-signal/40 hover:text-signal-bright disabled:opacity-40"
          >
            Compare All Strategies
          </button>
          <p className="text-[11px] leading-relaxed text-text-tertiary">
            Runs every registered strategy over the same {days}-day window and capital, ranked by return, so you can
            see which approach the signal engine actually favors right now — not just the one you happen to have
            selected above.
          </p>
        </div>

        <div className="space-y-6">
          {running && !result && !compareResults && (
            <div className="rounded-2xl border border-border glass p-6">
              <Skeleton className="h-[280px] w-full" />
            </div>
          )}

          {result && (
            <>
              <div className="rounded-2xl border border-border glass p-6">
                <div className="mb-4 flex items-center justify-between">
                  <h2 className="text-[12px] font-semibold uppercase tracking-[0.18em] text-text-tertiary">
                    Equity Curve
                  </h2>
                  <span
                    className={clsx(
                      "rounded-full border px-2.5 py-0.5 text-[10px] font-bold uppercase",
                      result.look_ahead_bias_detected
                        ? "border-danger/40 bg-danger/10 text-danger-bright"
                        : "border-gold/30 bg-gold/10 text-gold-bright"
                    )}
                  >
                    {result.look_ahead_bias_detected ? "LOOK-AHEAD BIAS DETECTED" : "Temporal Integrity Passed"}
                  </span>
                </div>
                {result.equity_curve.length > 1 ? (
                  <EquityCurveChart data={result.equity_curve} height={280} />
                ) : (
                  <div className="flex h-[280px] items-center justify-center text-[13px] text-text-tertiary">
                    No trades produced by this configuration.
                  </div>
                )}
              </div>

              <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
                {[
                  ["Trades", String(result.metrics.total_trades ?? 0), ""],
                  ["Win Rate", result.metrics.win_rate != null ? formatPercent(result.metrics.win_rate as number, 1) : "—", ""],
                  [
                    "Total Return",
                    result.metrics.total_return_pct != null ? formatPercent(result.metrics.total_return_pct as number) : "—",
                    (result.metrics.total_return_pct ?? 0) >= 0 ? "text-gold-bright" : "text-danger-bright",
                  ],
                  [
                    "Max Drawdown",
                    result.metrics.max_drawdown_pct != null ? formatPercent(-(result.metrics.max_drawdown_pct as number), 1) : "—",
                    "text-danger-bright",
                  ],
                  ["Expectancy", result.metrics.expectancy != null ? formatCompactCurrency(result.metrics.expectancy as number) : "—", ""],
                  ["Sharpe-like", result.metrics.sharpe_like != null ? (result.metrics.sharpe_like as number).toFixed(2) : "—", ""],
                  ["Total Fees", result.metrics.total_fees != null ? formatCompactCurrency(result.metrics.total_fees as number) : "—", ""],
                  ["Signals Generated", String(result.signal_stats.total_signals ?? 0), ""],
                ].map(([label, value, tone]) => (
                  <div key={label} className="rounded-xl border border-border glass p-4">
                    <div className="text-[10px] uppercase tracking-wider text-text-tertiary">{label}</div>
                    <div className={clsx("mono-num mt-1.5 text-[17px] font-semibold", tone || "text-text-primary")}>
                      {value}
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}

          {compareResults && (
            <>
              <div className="rounded-2xl border border-border glass p-6">
                <h2 className="mb-4 text-[12px] font-semibold uppercase tracking-[0.18em] text-text-tertiary">
                  Return by Strategy — {days}d window
                </h2>
                <div className="space-y-3">
                  {compareResults.map((r) => {
                    const ret = r.metrics.total_return_pct ?? 0;
                    const widthPct = Math.min((Math.abs(ret) / maxAbsReturn) * 100, 100);
                    const positive = ret >= 0;
                    return (
                      <div key={r.strategy} className="flex items-center gap-3">
                        <div className="flex w-48 shrink-0 items-center gap-1.5 overflow-hidden">
                          <span className="truncate text-[12px] font-medium text-text-secondary">{titleCase(r.strategy)}</span>
                          {r.strategy === bestStrategy && (
                            <span className="shrink-0 rounded border border-gold/30 bg-gold/10 px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider text-gold-bright">
                              Best
                            </span>
                          )}
                        </div>
                        <div className="relative h-5 flex-1 overflow-hidden rounded bg-white/[0.04]">
                          <div
                            className={clsx("h-full rounded", positive ? "bg-gold-bright/70" : "bg-danger-bright/70")}
                            style={{ width: `${Math.max(widthPct, 1.5)}%` }}
                          />
                        </div>
                        <div
                          className={clsx(
                            "mono-num w-16 shrink-0 text-right text-[12px] font-semibold",
                            positive ? "text-gold-bright" : "text-danger-bright"
                          )}
                        >
                          {formatPercent(ret)}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              <div className="overflow-hidden rounded-2xl border border-border glass">
                {/* min-w + overflow-x-auto: on a narrow viewport this scrolls
                    horizontally instead of silently clipping the last columns,
                    which `overflow-hidden` on its own would do. */}
                <div className="overflow-x-auto">
                <table className="w-full min-w-[560px] text-[13px]">
                  <thead>
                    <tr className="border-b border-border text-left text-[10px] uppercase tracking-wider text-text-tertiary">
                      <th className="px-4 py-3">Strategy</th>
                      <th className="px-4 py-3">Trades</th>
                      <th className="px-4 py-3">Win Rate</th>
                      <th className="px-4 py-3">Return</th>
                      <th className="px-4 py-3">Temporal Check</th>
                    </tr>
                  </thead>
                  <tbody>
                    {compareResults.map((r) => (
                      <tr
                        key={r.strategy}
                        className={clsx("border-b border-border last:border-0", r.strategy === bestStrategy && "bg-gold/[0.04]")}
                      >
                        <td className="px-4 py-3 font-semibold text-text-primary">{titleCase(r.strategy)}</td>
                        <td className="px-4 py-3 mono-num text-text-secondary">{r.metrics.total_trades ?? 0}</td>
                        <td className="px-4 py-3 mono-num text-text-secondary">
                          {r.metrics.win_rate != null ? formatPercent(r.metrics.win_rate, 0) : "—"}
                        </td>
                        <td
                          className={clsx(
                            "px-4 py-3 mono-num font-semibold",
                            (r.metrics.total_return_pct ?? 0) >= 0 ? "text-gold-bright" : "text-danger-bright"
                          )}
                        >
                          {r.metrics.total_return_pct != null ? formatPercent(r.metrics.total_return_pct) : "—"}
                        </td>
                        <td className={r.look_ahead_bias_detected ? "px-4 py-3 text-danger-bright" : "px-4 py-3 text-gold-bright"}>
                          {r.look_ahead_bias_detected ? "BIAS DETECTED" : "PASSED"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                </div>
              </div>
            </>
          )}

          {!running && !result && !compareResults && (
            <div className="flex h-[400px] flex-col items-center justify-center gap-2 rounded-2xl border border-dashed border-border text-center text-[13px] text-text-tertiary">
              <p>Configure a run on the left and click Run Backtest.</p>
              <p className="max-w-sm text-[12px] text-text-tertiary/70">
                Or click Compare All Strategies to rank every registered strategy against the same window at once.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

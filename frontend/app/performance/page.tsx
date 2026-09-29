"use client";

import useSWR from "swr";
import { api } from "@/lib/api";
import EquityCurveChart from "@/components/charts/EquityCurveChart";
import DrawdownChart from "@/components/charts/DrawdownChart";
import { formatCompactCurrency, formatPercent, titleCase } from "@/lib/format";

function StatTile({ label, value, tone }: { label: string; value: string; tone?: string }) {
  return (
    <div className="rounded-xl border border-border glass p-4">
      <div className="text-[10px] uppercase tracking-wider text-text-tertiary">{label}</div>
      <div className={`mono-num mt-1.5 text-[18px] font-semibold ${tone || "text-text-primary"}`}>{value}</div>
    </div>
  );
}

export default function PerformancePage() {
  const { data: perf } = useSWR("perf", () => api.portfolioPerformance());
  const { data: portfolio } = useSWR("perf-portfolio", () => api.portfolio());
  const { data: backtests } = useSWR("perf-backtests", () => api.listBacktests());

  const equityCurve = perf?.equity_curve || [];

  return (
    <div className="mx-auto max-w-[1400px] px-6 pb-24 pt-8">
      <h1 className="text-[24px] font-semibold text-text-primary">Performance</h1>
      <p className="mt-1 text-[13px] text-text-secondary">Paper trading track record for the active portfolio.</p>

      <div className="mt-6 grid grid-cols-2 gap-4 md:grid-cols-4">
        <StatTile
          label="Total Return"
          value={portfolio ? formatPercent(portfolio.total_return_pct) : "—"}
          tone={portfolio && portfolio.total_return_pct >= 0 ? "text-gold-bright" : "text-danger-bright"}
        />
        <StatTile label="Win Rate" value={perf?.win_rate != null ? formatPercent(perf.win_rate, 1) : "—"} />
        <StatTile label="Max Drawdown" value={perf ? formatPercent(-perf.max_drawdown_pct, 1) : "—"} tone="text-danger-bright" />
        <StatTile label="Closed Trades" value={String(perf?.closed_trade_count ?? 0)} />
        <StatTile label="Avg Win" value={perf?.avg_win != null ? formatCompactCurrency(perf.avg_win) : "—"} tone="text-gold-bright" />
        <StatTile label="Avg Loss" value={perf?.avg_loss != null ? formatCompactCurrency(perf.avg_loss) : "—"} tone="text-danger-bright" />
        <StatTile label="Total Fees" value={perf ? formatCompactCurrency(perf.total_fees) : "—"} />
        <StatTile label="Mode" value={portfolio?.mode?.toUpperCase() || "—"} />
      </div>

      <div className="mt-8 grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="rounded-2xl border border-border glass p-6 lg:col-span-2">
          <h2 className="mb-4 text-[12px] font-semibold uppercase tracking-[0.18em] text-text-tertiary">Equity Curve</h2>
          {equityCurve.length > 1 ? (
            <EquityCurveChart data={equityCurve} height={300} />
          ) : (
            <div className="flex h-[300px] items-center justify-center text-[13px] text-text-tertiary">
              No closed trades yet — equity curve builds as paper trades close.
            </div>
          )}
        </div>
        <div className="rounded-2xl border border-border glass p-6">
          <h2 className="mb-4 text-[12px] font-semibold uppercase tracking-[0.18em] text-text-tertiary">Drawdown</h2>
          {equityCurve.length > 1 ? (
            <DrawdownChart data={equityCurve} height={300} />
          ) : (
            <div className="flex h-[300px] items-center justify-center text-[13px] text-text-tertiary">—</div>
          )}
        </div>
      </div>

      <div className="mt-8">
        <h2 className="mb-4 text-[12px] font-semibold uppercase tracking-[0.18em] text-text-tertiary">
          Strategy Backtest History
        </h2>
        <div className="overflow-hidden rounded-2xl border border-border glass">
          <table className="w-full text-[13px]">
            <thead>
              <tr className="border-b border-border text-left text-[10px] uppercase tracking-wider text-text-tertiary">
                <th className="px-4 py-3">Strategy</th>
                <th className="px-4 py-3">Trades</th>
                <th className="px-4 py-3">Win Rate</th>
                <th className="px-4 py-3">Return</th>
                <th className="px-4 py-3">Look-Ahead Check</th>
                <th className="px-4 py-3">Run</th>
              </tr>
            </thead>
            <tbody>
              {(backtests || []).map((b) => (
                <tr key={b.id} className="border-b border-border last:border-0">
                  <td className="px-4 py-3 font-semibold text-text-primary">{titleCase(b.strategy)}</td>
                  <td className="px-4 py-3 mono-num text-text-secondary">{b.metrics.total_trades ?? 0}</td>
                  <td className="px-4 py-3 mono-num text-text-secondary">
                    {b.metrics.win_rate != null ? formatPercent(b.metrics.win_rate as number, 0) : "—"}
                  </td>
                  <td
                    className={`px-4 py-3 mono-num font-semibold ${
                      (b.metrics.total_return_pct ?? 0) >= 0 ? "text-gold-bright" : "text-danger-bright"
                    }`}
                  >
                    {b.metrics.total_return_pct != null ? formatPercent(b.metrics.total_return_pct as number) : "—"}
                  </td>
                  <td className="px-4 py-3">
                    <span className={b.look_ahead_bias_detected ? "text-danger-bright" : "text-gold-bright"}>
                      {b.look_ahead_bias_detected ? "BIAS DETECTED" : "PASSED"}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-text-tertiary">{new Date(b.created_at).toLocaleDateString()}</td>
                </tr>
              ))}
              {(!backtests || backtests.length === 0) && (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-text-tertiary">
                    No backtests run yet — try the Backtest Lab.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

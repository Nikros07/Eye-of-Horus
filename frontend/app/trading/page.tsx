"use client";

import { useState } from "react";
import useSWR, { mutate } from "swr";
import clsx from "clsx";
import { api } from "@/lib/api";
import EquityCurveChart from "@/components/charts/EquityCurveChart";
import PositionCard from "@/components/cards/PositionCard";
import SignalBadge from "@/components/cards/SignalBadge";
import Toggle from "@/components/common/Toggle";
import { formatCompactCurrency, formatConfidence, titleCase } from "@/lib/format";

export default function TradingPage() {
  const { data: assets } = useSWR("assets-trading", () => api.assets());
  const [symbol, setSymbol] = useState<string | null>(null);
  const activeSymbol = symbol || assets?.[0]?.symbol;

  const { data: history } = useSWR(activeSymbol ? ["trading-history", activeSymbol] : null, () =>
    api.assetHistory(activeSymbol as string, 240)
  );
  const { data: quote } = useSWR(activeSymbol ? ["trading-quote", activeSymbol] : null, () => api.assets(), {
    refreshInterval: 8000,
  });
  const { data: mode } = useSWR("mode-trading", () => api.tradingMode());
  const { data: autoTrade } = useSWR("auto-trade", () => api.autoTrade(), { refreshInterval: 15000 });
  const { data: account } = useSWR("account-trading", () => api.account(), { refreshInterval: 8000 });
  const { data: positions } = useSWR("positions-trading", () => api.positions(), { refreshInterval: 8000 });
  const { data: signals } = useSWR("signals-trading", () => api.signals({ limit: 30 }), { refreshInterval: 15000 });

  const [qty, setQty] = useState("10");
  const [placing, setPlacing] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);

  const currentAsset = quote?.find((a) => a.symbol === activeSymbol);
  const symbolSignal = (signals || []).find((s) => s.asset_symbol === activeSymbol);

  async function submitOrder(side: "buy" | "sell") {
    if (!activeSymbol) return;
    setPlacing(true);
    setFeedback(null);
    try {
      const res = await api.placeOrder(activeSymbol, side, parseFloat(qty));
      setFeedback(res.status === "filled" ? `Filled at $${res.filled_price?.toFixed(2)}` : res.status);
      mutate("positions-trading");
      mutate("account-trading");
    } catch (e: any) {
      setFeedback("Order rejected");
    } finally {
      setPlacing(false);
    }
  }

  return (
    <div className="mx-auto max-w-[1600px] px-6 pb-24 pt-8">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-gradient-gold text-[24px] font-semibold">Trading Terminal</h1>
          <p className="mt-1 text-[13px] text-text-secondary">
            {mode?.mode === "paper" ? "Paper mode — simulated fills, real ledger." : titleCase(mode?.mode || "")}
          </p>
        </div>
        <div className="flex gap-6 text-right">
          <div>
            <div className="text-[10px] uppercase tracking-wider text-text-tertiary">Cash</div>
            <div className="mono-num text-[16px] font-semibold text-text-primary">
              {account ? formatCompactCurrency(account.cash) : "—"}
            </div>
          </div>
          <div>
            <div className="text-[10px] uppercase tracking-wider text-text-tertiary">Equity</div>
            <div className="mono-num text-[16px] font-semibold text-gold-bright">
              {account ? formatCompactCurrency(account.equity) : "—"}
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-[1fr_340px]">
        <div className="space-y-6">
          <div className="rounded-2xl border border-border glass p-6">
            <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
              <div className="flex flex-wrap gap-1.5">
                {(assets || []).map((a) => (
                  <button
                    key={a.symbol}
                    onClick={() => setSymbol(a.symbol)}
                    className={clsx(
                      "rounded-md border px-2.5 py-1 text-[11px] font-medium transition-colors",
                      activeSymbol === a.symbol
                        ? "border-gold/40 bg-gold/10 text-gold-bright"
                        : "border-border text-text-tertiary hover:text-text-secondary"
                    )}
                  >
                    {a.symbol}
                  </button>
                ))}
              </div>
              {currentAsset && (
                <div className="text-right">
                  <div className="mono-num text-[22px] font-semibold text-text-primary">
                    ${currentAsset.price?.toFixed(2)}
                  </div>
                  <div
                    className={clsx(
                      "mono-num text-[12px]",
                      (currentAsset.change_pct ?? 0) >= 0 ? "text-gold-bright" : "text-danger-bright"
                    )}
                  >
                    {(currentAsset.change_pct ?? 0) >= 0 ? "+" : ""}
                    {currentAsset.change_pct?.toFixed(2)}%
                  </div>
                </div>
              )}
            </div>
            {history && <EquityCurveChart data={history.bars.map((b) => ({ ts: b.ts, equity: b.close }))} height={340} />}
          </div>

          <div>
            <h2 className="mb-4 text-[12px] font-semibold uppercase tracking-[0.18em] text-text-tertiary">
              Open Positions
            </h2>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {(positions || []).map((p) => (
                <PositionCard
                  key={p.asset_symbol}
                  position={p}
                  onClose={async () => {
                    await api.closePosition(p.asset_symbol);
                    mutate("positions-trading");
                    mutate("account-trading");
                  }}
                />
              ))}
              {(!positions || positions.length === 0) && (
                <div className="col-span-full rounded-xl border border-border glass p-8 text-center text-[13px] text-text-tertiary">
                  No open positions.
                </div>
              )}
            </div>
          </div>
        </div>

        <aside className="space-y-6">
          <div className="rounded-2xl border border-border glass p-5">
            <h2 className="mb-4 text-[12px] font-semibold uppercase tracking-[0.18em] text-text-tertiary">
              Order Panel — {activeSymbol}
            </h2>
            {symbolSignal && (
              <div className="mb-4 rounded-lg border border-border bg-white/[0.02] p-3">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] text-text-tertiary">Active signal</span>
                  <SignalBadge direction={symbolSignal.direction} confidence={symbolSignal.confidence} size="sm" />
                </div>
              </div>
            )}
            <label className="block text-[11px] uppercase tracking-wider text-text-tertiary">Quantity</label>
            <input
              value={qty}
              onChange={(e) => setQty(e.target.value)}
              type="number"
              min={0}
              className="mt-1.5 w-full rounded-lg border border-border bg-white/[0.03] px-3 py-2 text-[14px] mono-num text-text-primary outline-none focus:border-gold/40"
            />
            <div className="mt-2 flex justify-between text-[11px] text-text-tertiary">
              <span>Est. fees</span>
              <span className="mono-num">
                {currentAsset?.price ? `$${(parseFloat(qty || "0") * currentAsset.price * 0.0002).toFixed(2)}` : "—"}
              </span>
            </div>
            <div className="mt-2 flex justify-between text-[11px] text-text-tertiary">
              <span>Est. slippage</span>
              <span className="mono-num">5–8 bps</span>
            </div>

            <div className="mt-4 grid grid-cols-2 gap-2">
              <button
                disabled={placing || mode?.mode === "research"}
                onClick={() => submitOrder("buy")}
                className="rounded-lg border border-gold/40 bg-gold/10 py-2.5 text-[13px] font-semibold text-gold-bright transition-colors hover:bg-gold/20 disabled:opacity-40"
              >
                Buy
              </button>
              <button
                disabled={placing || mode?.mode === "research"}
                onClick={() => submitOrder("sell")}
                className="rounded-lg border border-danger/40 bg-danger/10 py-2.5 text-[13px] font-semibold text-danger-bright transition-colors hover:bg-danger/20 disabled:opacity-40"
              >
                Sell
              </button>
            </div>
            {mode?.mode === "research" && (
              <p className="mt-2 text-[11px] text-text-tertiary">Research mode: analysis only, no orders placed.</p>
            )}
            {feedback && <p className="mt-3 text-[12px] text-text-secondary">{feedback}</p>}
          </div>

          <div className="rounded-2xl border border-border glass p-5">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-[12px] font-semibold uppercase tracking-[0.18em] text-text-tertiary">
                  Automatic Trading
                </h2>
                <p className="mt-1 text-[11px] leading-relaxed text-text-tertiary">
                  Executes fresh signals above the confidence floor on its own, every 90s — through the same risk
                  checks as a manual order. Always paper unless the portfolio mode is switched to live.
                </p>
              </div>
              <Toggle
                checked={autoTrade?.enabled ?? false}
                disabled={mode?.mode === "research"}
                onChange={async (v) => {
                  await api.setAutoTrade(v);
                  mutate("auto-trade");
                }}
                label="Automatic trading"
              />
            </div>

            {autoTrade && (
              <div className="mt-4 border-t border-border pt-4">
                <div className="flex items-center justify-between text-[11px] text-text-tertiary">
                  <span>Min. confidence</span>
                  <span className="mono-num text-text-primary">{formatConfidence(autoTrade.min_confidence)}</span>
                </div>
                <input
                  type="range"
                  min={0.4}
                  max={0.9}
                  step={0.05}
                  value={autoTrade.min_confidence}
                  onChange={async (e) => {
                    await api.setAutoTrade(autoTrade.enabled, parseFloat(e.target.value));
                    mutate("auto-trade");
                  }}
                  className="mt-2 w-full accent-gold"
                />
              </div>
            )}

            {autoTrade?.enabled && (
              <div className="mt-3 flex items-center gap-1.5 text-[11px] text-gold-bright">
                <span className="relative flex h-1.5 w-1.5">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-gold-bright opacity-60" />
                  <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-gold-bright" />
                </span>
                Watching for signals
              </div>
            )}
          </div>
        </aside>
      </div>
    </div>
  );
}

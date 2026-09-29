"use client";

import useSWR from "swr";
import { AreaChart, Area, ResponsiveContainer } from "recharts";
import Card3D from "./Card3D";
import SignalBadge from "./SignalBadge";
import DemoDataBadge from "../common/DemoDataBadge";
import AnimatedNumber from "../common/AnimatedNumber";
import { formatPercent, titleCase, formatConfidence } from "@/lib/format";
import { api } from "@/lib/api";
import clsx from "clsx";
import type { AssetQuote, Bar, Signal } from "@/lib/types";

function exposureLevel(score: number): string {
  if (score >= 0.55) return "HIGH";
  if (score >= 0.3) return "MEDIUM";
  return "LOW";
}

export default function MarketCard({
  asset,
  bars,
  topSignal,
}: {
  asset: AssetQuote;
  bars?: Bar[];
  topSignal?: Signal;
}) {
  const positive = (asset.change_pct ?? 0) >= 0;

  // Cards used standalone (e.g. the dashboard grid) don't have bars fetched
  // by a parent — fetch them lazily here so the sparkline still renders.
  const { data: fetched } = useSWR(
    !bars ? ["market-card-history", asset.symbol] : null,
    () => api.assetHistory(asset.symbol, 48)
  );
  const effectiveBars = bars ?? fetched?.bars;
  const sparkData = (effectiveBars || []).map((b, i) => ({ i, v: b.close }));

  return (
    <Card3D glow={positive ? "gold" : "danger"} className="p-5 min-h-[200px] flex flex-col justify-between" intensity={6}>
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-1.5">
            <div className="text-[11px] font-semibold uppercase tracking-[0.14em] text-text-tertiary">
              {titleCase(asset.name)}
            </div>
            {asset.is_demo && <DemoDataBadge />}
          </div>
          <div className="mt-1.5 mono-num text-[24px] font-semibold text-text-primary">
            {asset.price != null ? <AnimatedNumber value={asset.price} format={(v) => `$${v.toFixed(2)}`} /> : "—"}
          </div>
          <div
            className={clsx(
              "mt-0.5 mono-num text-[13px] font-medium",
              positive ? "text-gold-bright" : "text-danger-bright"
            )}
          >
            {asset.change_pct != null ? formatPercent(asset.change_pct / 100, 2) : "—"}
          </div>
        </div>

        {sparkData.length > 2 && (
          <div className="h-12 w-24 opacity-80 transition-opacity group-hover:opacity-100">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={sparkData} margin={{ top: 4, right: 0, bottom: 0, left: 0 }}>
                <defs>
                  <linearGradient id={`spark-${asset.symbol}`} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={positive ? "#D8B36C" : "#E5555C"} stopOpacity={0.5} />
                    <stop offset="100%" stopColor={positive ? "#D8B36C" : "#E5555C"} stopOpacity={0} />
                  </linearGradient>
                </defs>
                <Area
                  type="monotone"
                  dataKey="v"
                  stroke={positive ? "#EACB8C" : "#F17178"}
                  strokeWidth={1.5}
                  fill={`url(#spark-${asset.symbol})`}
                  isAnimationActive={false}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      <div className="mt-4 space-y-2 border-t border-border pt-4">
        {topSignal ? (
          <>
            <div className="flex items-center justify-between text-[11px]">
              <span className="uppercase tracking-wider text-text-tertiary">Event Exposure</span>
              <span className="font-semibold text-text-primary">{exposureLevel(topSignal.confidence)}</span>
            </div>
            <div className="flex items-center justify-between text-[11px]">
              <span className="uppercase tracking-wider text-text-tertiary">Confidence</span>
              <span className="font-semibold text-text-primary">{formatConfidence(topSignal.confidence)}</span>
            </div>
            <div className="flex items-center justify-between pt-1">
              <SignalBadge direction={topSignal.direction} confidence={topSignal.confidence} size="sm" />
              <span className="mono-num text-[11px] text-text-tertiary">{topSignal.expected_horizon}</span>
            </div>
          </>
        ) : (
          <div className="text-[11px] uppercase tracking-wider text-text-tertiary/70">No active signal</div>
        )}
      </div>
    </Card3D>
  );
}

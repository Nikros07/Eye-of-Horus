"use client";

import Card3D from "./Card3D";
import AnimatedNumber from "../common/AnimatedNumber";
import { formatCompactCurrency, formatPercent } from "@/lib/format";
import clsx from "clsx";
import type { PortfolioSummary } from "@/lib/types";

function riskLevel(exposurePct: number): { label: string; color: string } {
  if (exposurePct >= 0.5) return { label: "HIGH", color: "text-danger-bright" };
  if (exposurePct >= 0.25) return { label: "MEDIUM", color: "text-gold-bright" };
  return { label: "LOW", color: "text-info-bright" };
}

export default function PortfolioCard({ portfolio }: { portfolio: PortfolioSummary }) {
  const risk = riskLevel(portfolio.exposure_pct);
  const positive = portfolio.total_return_pct >= 0;
  const dayPositive = portfolio.daily_pnl >= 0;

  return (
    <Card3D glow="gold" className="p-7 min-h-[220px] flex flex-col justify-between">
      <div className="flex items-start justify-between">
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-text-tertiary">
            Total Equity
          </div>
          <div className="mt-2 mono-num text-[34px] font-semibold leading-none text-text-primary">
            <AnimatedNumber value={portfolio.equity} format={(v) => formatCompactCurrency(v)} />
          </div>
          <div
            className={clsx(
              "mt-2 inline-flex items-center gap-1 text-[13px] font-medium mono-num",
              positive ? "text-gold-bright" : "text-danger-bright"
            )}
          >
            {formatPercent(portfolio.total_return_pct)}
            <span className="text-text-tertiary font-normal">all-time</span>
          </div>
        </div>
        <div className="text-right">
          <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-text-tertiary">Risk</div>
          <div className={clsx("mt-2 text-[13px] font-bold", risk.color)}>{risk.label}</div>
        </div>
      </div>

      <div className="mt-6 flex items-end justify-between border-t border-border pt-5">
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-text-tertiary">Today</div>
          <div className={clsx("mt-1 mono-num text-[18px] font-semibold", dayPositive ? "text-gold-bright" : "text-danger-bright")}>
            {dayPositive ? "+" : ""}
            {formatCompactCurrency(portfolio.daily_pnl)}
          </div>
        </div>
        <div className="text-right">
          <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-text-tertiary">Exposure</div>
          <div className="mt-1 mono-num text-[18px] font-semibold text-text-primary">
            {formatPercent(portfolio.exposure_pct, 1)}
          </div>
        </div>
        <div className="text-right">
          <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-text-tertiary">Positions</div>
          <div className="mt-1 mono-num text-[18px] font-semibold text-text-primary">{portfolio.open_position_count}</div>
        </div>
      </div>
    </Card3D>
  );
}

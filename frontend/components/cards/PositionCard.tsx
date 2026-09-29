"use client";

import clsx from "clsx";
import Card3D from "./Card3D";
import { formatCompactCurrency } from "@/lib/format";
import type { Position } from "@/lib/types";

export default function PositionCard({ position, onClose }: { position: Position; onClose?: () => void }) {
  const positive = position.unrealized_pnl >= 0;
  const riskAmount = Math.abs(position.qty * (position.avg_entry_price - (position.stop_price ?? position.avg_entry_price * 0.97)));

  return (
    <Card3D glow={positive ? "gold" : "danger"} className="p-5" intensity={5}>
      <div className="flex items-start justify-between">
        <div>
          <div className="text-[13px] font-semibold text-text-primary">{position.asset_symbol}</div>
          <span
            className={clsx(
              "mt-1 inline-block rounded px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider",
              position.side === "long" ? "bg-gold/15 text-gold-bright" : "bg-danger/15 text-danger-bright"
            )}
          >
            {position.side}
          </span>
        </div>
        {onClose && (
          <button
            onClick={onClose}
            className="rounded-md border border-border px-2 py-1 text-[10px] uppercase tracking-wider text-text-secondary transition-colors hover:border-danger/40 hover:text-danger-bright"
          >
            Close
          </button>
        )}
      </div>

      <div className="mt-4 grid grid-cols-2 gap-3 text-[11px]">
        <div>
          <div className="uppercase tracking-wider text-text-tertiary">Entry</div>
          <div className="mono-num mt-0.5 text-text-primary">{position.avg_entry_price.toFixed(2)}</div>
        </div>
        <div>
          <div className="uppercase tracking-wider text-text-tertiary">Current</div>
          <div className="mono-num mt-0.5 text-text-primary">{position.current_price.toFixed(2)}</div>
        </div>
        <div>
          <div className="uppercase tracking-wider text-text-tertiary">P&amp;L</div>
          <div className={clsx("mono-num mt-0.5 font-semibold", positive ? "text-gold-bright" : "text-danger-bright")}>
            {positive ? "+" : ""}
            {formatCompactCurrency(position.unrealized_pnl)}
          </div>
        </div>
        <div>
          <div className="uppercase tracking-wider text-text-tertiary">Size</div>
          <div className="mono-num mt-0.5 text-text-primary">
            {formatCompactCurrency(position.qty * position.current_price)}
          </div>
        </div>
      </div>
    </Card3D>
  );
}

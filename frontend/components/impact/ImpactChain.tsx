"use client";

import { motion } from "framer-motion";
import clsx from "clsx";
import { titleCase } from "@/lib/format";
import type { ImpactLink } from "@/lib/types";

const nodeStyle: Record<string, string> = {
  event: "border-danger/40 bg-danger/10 text-danger-bright",
  infrastructure: "border-info/40 bg-info/10 text-info-bright",
  supply_chain: "border-signal/40 bg-signal/10 text-signal-bright",
  market: "border-gold/40 bg-gold/10 text-gold-bright",
};

export default function ImpactChain({ link }: { link: ImpactLink }) {
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        {link.chain.map((node, i) => (
          <div key={i} className="flex items-center gap-2">
            <motion.div
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.08, duration: 0.4, ease: "easeOut" }}
              className={clsx(
                "rounded-lg border px-3 py-1.5 text-[11px] font-semibold uppercase tracking-wide whitespace-nowrap",
                nodeStyle[node.type] || "border-white/10 bg-white/5 text-text-secondary"
              )}
            >
              {titleCase(node.node)}
            </motion.div>
            {i < link.chain.length - 1 && (
              <motion.svg
                initial={{ opacity: 0, scaleX: 0 }}
                animate={{ opacity: 1, scaleX: 1 }}
                transition={{ delay: i * 0.08 + 0.05, duration: 0.3 }}
                width="20"
                height="10"
                viewBox="0 0 20 10"
                className="text-text-tertiary shrink-0"
              >
                <path d="M0 5H17M17 5L12 1M17 5L12 9" stroke="currentColor" strokeWidth="1.2" fill="none" />
              </motion.svg>
            )}
          </div>
        ))}
      </div>
      <div className="flex items-center gap-4 text-[12px]">
        <span className={clsx("font-semibold uppercase", link.direction === "bullish" ? "text-gold-bright" : "text-danger-bright")}>
          {link.direction} on {link.asset_symbol}
        </span>
        <span className="text-text-tertiary">exposure {Math.round(link.exposure_score * 100)}%</span>
      </div>
      <p className="text-[13px] leading-relaxed text-text-secondary">{link.rationale}</p>
    </div>
  );
}

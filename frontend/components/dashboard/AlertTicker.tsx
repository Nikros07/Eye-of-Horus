"use client";

import { useEffect } from "react";
import useSWR, { mutate } from "swr";
import Link from "next/link";
import { AnimatePresence, motion } from "framer-motion";
import { AreaChart, Area } from "recharts";
import { api } from "@/lib/api";
import { useLiveStream } from "@/lib/useLiveStream";
import { Skeleton } from "@/components/common/Skeleton";
import { relativeTime, titleCase } from "@/lib/format";

const severityDot: Record<string, string> = {
  critical: "bg-danger-bright shadow-[0_0_10px_2px_rgba(241,113,120,0.6)]",
  high: "bg-gold-bright shadow-[0_0_10px_2px_rgba(234,203,140,0.5)]",
  medium: "bg-info-bright shadow-[0_0_8px_1px_rgba(130,170,245,0.4)]",
  low: "bg-text-tertiary",
};

// Keyed exactly like MarketCard's own history fetch so the two share one
// SWR cache entry per symbol instead of double-fetching the same bars.
function AlertSparkline({ symbol, positive }: { symbol: string; positive: boolean }) {
  const { data } = useSWR(["market-card-history", symbol], () => api.assetHistory(symbol, 48));
  const bars = data?.bars || [];
  if (bars.length < 2) return <div className="h-[18px] w-11 shrink-0" />;

  const color = positive ? "#EACB8C" : "#F17178";
  return (
    <AreaChart width={44} height={18} data={bars.map((b, i) => ({ i, v: b.close }))} margin={{ top: 2, right: 0, bottom: 0, left: 0 }}>
      <defs>
        <linearGradient id={`alert-spark-${symbol}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity={0.45} />
          <stop offset="100%" stopColor={color} stopOpacity={0} />
        </linearGradient>
      </defs>
      <Area
        type="monotone"
        dataKey="v"
        stroke={color}
        strokeWidth={1}
        fill={`url(#alert-spark-${symbol})`}
        isAnimationActive={false}
      />
    </AreaChart>
  );
}

export default function AlertTicker() {
  const { data: alerts, isLoading } = useSWR("hero-alerts", () => api.alerts({ limit: 14, hours: 168 }), {
    // Kept as a fallback in case the SSE connection below is ever down —
    // the push from useLiveStream is what normally keeps this fresh.
    refreshInterval: 20000,
  });

  // The signal engine pushes over SSE the instant a new signal fires, so a
  // fresh tick here means the alert list is out of date — refetch it right
  // away instead of waiting for the next interval. The dot's color reflects
  // whether that push connection is actually live, rather than pulsing
  // unconditionally regardless of real connection state.
  const { tick: liveTick, connected: liveConnected } = useLiveStream();
  useEffect(() => {
    if (liveTick > 0) mutate("hero-alerts");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [liveTick]);

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center gap-2 px-1 pb-4">
        <span className="relative flex h-2 w-2" title={liveConnected ? "Live push connected" : "Polling — live push unavailable"}>
          {liveConnected && (
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-danger-bright opacity-60" />
          )}
          <span className={`relative inline-flex h-2 w-2 rounded-full ${liveConnected ? "bg-danger-bright" : "bg-text-tertiary"}`} />
        </span>
        <h2 className="text-[11px] font-semibold uppercase tracking-[0.2em] text-text-secondary">Live Alerts</h2>
        <span className="ml-auto font-mono text-[10px] text-text-faint">{alerts?.length ?? 0}</span>
      </div>

      <div className="min-h-0 flex-1 space-y-2 overflow-y-auto pr-1 [scrollbar-width:thin]">
        <AnimatePresence initial={false}>
          {(alerts || []).map((a) => (
            <motion.div
              key={a.signal_id}
              layout
              initial={{ opacity: 0, x: -12 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 12 }}
              transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
            >
              <Link
                href={`/events?id=${a.event_id ?? ""}`}
                className="block rounded-xl border border-white/[0.06] bg-white/[0.02] px-3.5 py-3 transition-colors hover:border-white/[0.14] hover:bg-white/[0.04]"
              >
                <div className="flex items-center gap-2">
                  <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${severityDot[a.severity]}`} />
                  <span className="truncate text-[12.5px] font-semibold text-text-primary">{a.asset_symbol}</span>
                  <AlertSparkline symbol={a.asset_symbol} positive={a.direction === "bullish"} />
                  <span
                    className={`ml-auto shrink-0 text-[10px] font-bold uppercase tracking-wide ${
                      a.direction === "bullish" ? "text-gold-bright" : "text-danger-bright"
                    }`}
                  >
                    {a.direction}
                  </span>
                </div>
                <p className="mt-1.5 line-clamp-1 text-[11.5px] leading-snug text-text-tertiary">
                  {a.event_title || titleCase(a.event_type || "")}
                </p>
                <div className="mt-1.5 flex items-center justify-between text-[10px] text-text-faint">
                  <span>{Math.round(a.confidence * 100)}% confidence</span>
                  <span>{relativeTime(a.signal_time)}</span>
                </div>
              </Link>
            </motion.div>
          ))}
        </AnimatePresence>

        {isLoading &&
          Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="rounded-xl border border-white/[0.06] bg-white/[0.02] px-3.5 py-3">
              <Skeleton className="h-3 w-16" />
              <Skeleton className="mt-2 h-3 w-full" />
              <Skeleton className="mt-2 h-2.5 w-2/3" />
            </div>
          ))}

        {!isLoading && (!alerts || alerts.length === 0) && (
          <div className="rounded-xl border border-dashed border-white/[0.08] px-3.5 py-8 text-center text-[11.5px] text-text-faint">
            Monitoring for signals…
          </div>
        )}
      </div>
    </div>
  );
}

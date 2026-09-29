import clsx from "clsx";
import { formatConfidence } from "@/lib/format";

export default function SignalBadge({
  direction,
  confidence,
  size = "md",
}: {
  direction: string;
  confidence: number;
  size?: "sm" | "md";
}) {
  const isBullish = direction === "bullish";
  const isBearish = direction === "bearish";

  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1.5 rounded-full border font-semibold uppercase tracking-wider",
        size === "sm" ? "px-2 py-0.5 text-[10px]" : "px-2.5 py-1 text-[11px]",
        isBullish && "border-gold/30 bg-gold/10 text-gold-bright",
        isBearish && "border-danger/30 bg-danger/10 text-danger-bright",
        !isBullish && !isBearish && "border-white/10 bg-white/5 text-text-secondary"
      )}
    >
      <svg width="9" height="9" viewBox="0 0 10 10" className={clsx(isBearish && "rotate-180")}>
        <path d="M5 1L9 7H1L5 1Z" fill="currentColor" />
      </svg>
      {direction} · {formatConfidence(confidence)}
    </span>
  );
}

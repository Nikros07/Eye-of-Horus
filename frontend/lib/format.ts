export function formatCompactCurrency(value: number): string {
  const sign = value < 0 ? "-" : "";
  const abs = Math.abs(value);
  return `${sign}$${abs.toLocaleString("en-US", { maximumFractionDigits: 2 })}`;
}

export function formatPercent(value: number, digits = 2): string {
  const pct = value * 100;
  const sign = pct > 0 ? "+" : "";
  return `${sign}${pct.toFixed(digits)}%`;
}

export function formatConfidence(value: number): string {
  return `${Math.round(value * 100)}%`;
}

// A plain ratio-as-percentage, unlike formatPercent's "+2.50%" — for values
// that are a share or a ceiling (exposure, position concentration, a
// configured risk limit) rather than a gain/loss where the sign is itself
// the point.
export function formatRatio(value: number, digits = 1): string {
  return `${(value * 100).toFixed(digits)}%`;
}

export function titleCase(input: string): string {
  return input
    .replace(/_/g, " ")
    .split(" ")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

export function relativeTime(iso: string): string {
  const then = new Date(iso).getTime();
  const now = Date.now();
  const diffMs = now - then;
  const diffMin = Math.round(diffMs / 60000);
  if (Math.abs(diffMin) < 1) return "just now";
  if (Math.abs(diffMin) < 60) return `${diffMin}m ago`;
  const diffH = Math.round(diffMin / 60);
  if (Math.abs(diffH) < 24) return `${diffH}h ago`;
  const diffD = Math.round(diffH / 24);
  return `${diffD}d ago`;
}

export const severityColor: Record<string, string> = {
  low: "text-text-secondary",
  medium: "text-info-bright",
  high: "text-gold-bright",
  critical: "text-danger-bright",
};

export const verificationStyle: Record<string, string> = {
  verified: "border-gold/30 bg-gold/10 text-gold-bright",
  pending: "border-info/30 bg-info/10 text-info-bright",
  unverified: "border-white/10 bg-white/5 text-text-secondary",
  disputed: "border-danger/30 bg-danger/10 text-danger-bright",
};

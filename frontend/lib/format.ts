export function formatCurrency(value: number, currency = "USD"): string {
  return new Intl.NumberFormat("en-US", { style: "currency", currency, maximumFractionDigits: 2 }).format(value);
}

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

export function formatSignedNumber(value: number, digits = 2): string {
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(digits)}`;
}

export function formatConfidence(value: number): string {
  return `${Math.round(value * 100)}%`;
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

export const severityBg: Record<string, string> = {
  low: "bg-white/5",
  medium: "bg-info/15",
  high: "bg-gold/15",
  critical: "bg-danger/15",
};

export const directionColor: Record<string, string> = {
  bullish: "text-gold-bright",
  bearish: "text-danger-bright",
  neutral: "text-text-secondary",
};

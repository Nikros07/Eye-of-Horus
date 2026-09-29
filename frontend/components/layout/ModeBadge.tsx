"use client";

import clsx from "clsx";

const styles: Record<string, string> = {
  research: "bg-info/15 text-info-bright border-info/30",
  paper: "bg-gold/15 text-gold-bright border-gold/30",
  live: "bg-danger/15 text-danger-bright border-danger/40",
};

export default function ModeBadge({ mode }: { mode: string }) {
  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wider",
        styles[mode] || styles.paper
      )}
    >
      <span
        className={clsx("h-1.5 w-1.5 rounded-full", mode === "live" ? "animate-pulse bg-danger-bright" : "bg-current")}
      />
      {mode}
    </span>
  );
}

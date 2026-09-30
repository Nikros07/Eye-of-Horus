"use client";

import Link from "next/link";
import clsx from "clsx";
import Card3D from "./Card3D";
import DemoDataBadge from "../common/DemoDataBadge";
import { formatConfidence, relativeTime, severityColor, titleCase, verificationStyle } from "@/lib/format";
import type { EventSummary } from "@/lib/types";

export default function EventCard({ event }: { event: EventSummary }) {
  const topAsset = Object.entries(event.market_exposure || {}).sort((a, b) => b[1] - a[1])[0];

  return (
    <Link href={`/events?id=${event.event_id}`}>
      <Card3D glow={severityGlow(event.severity)} className="p-5 h-full" intensity={5}>
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.14em] text-text-tertiary">
              {titleCase(event.event_type)}
              {event.is_demo && <DemoDataBadge />}
            </div>
            <h3 className="mt-1.5 text-[15px] font-semibold leading-snug text-text-primary line-clamp-2">
              {event.title}
            </h3>
            <div className="mt-1 text-[12px] text-text-tertiary">{event.location_name || "Location unknown"}</div>
          </div>
          <span
            className={clsx(
              "shrink-0 rounded-full border px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider",
              verificationStyle[event.verification_status]
            )}
          >
            {event.verification_status}
          </span>
        </div>

        <div className="mt-4 flex items-center gap-4">
          <div>
            <div className="text-[10px] uppercase tracking-wider text-text-tertiary">Impact</div>
            <div className={clsx("text-[12px] font-bold uppercase", severityColor[event.severity])}>
              {event.severity}
            </div>
          </div>
          <div className="h-6 w-px bg-border" />
          <div>
            <div className="text-[10px] uppercase tracking-wider text-text-tertiary">Confidence</div>
            <div className="mono-num text-[12px] font-bold text-text-primary">{formatConfidence(event.confidence)}</div>
          </div>
          {topAsset && (
            <>
              <div className="h-6 w-px bg-border" />
              <div>
                <div className="text-[10px] uppercase tracking-wider text-text-tertiary">Exposure</div>
                <div className="mono-num text-[12px] font-bold text-gold-bright">{topAsset[0]}</div>
              </div>
            </>
          )}
        </div>

        <div className="mt-4 flex items-center justify-between border-t border-border pt-3 text-[11px] text-text-tertiary">
          <span>{relativeTime(event.last_updated)}</span>
          <span className="opacity-0 transition-opacity group-hover:opacity-100 text-gold-bright">View chain →</span>
        </div>
      </Card3D>
    </Link>
  );
}

function severityGlow(severity: string): "gold" | "danger" | "info" | "none" {
  if (severity === "critical") return "danger";
  if (severity === "high") return "gold";
  return "info";
}

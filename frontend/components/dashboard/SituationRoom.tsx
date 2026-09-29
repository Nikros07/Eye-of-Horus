"use client";

import GlobalGlobe from "@/components/globe/GlobalGlobe";
import AlertTicker from "./AlertTicker";
import type { EventSummary } from "@/lib/types";

export default function SituationRoom({ events }: { events: EventSummary[] }) {
  return (
    <section className="relative -mx-6 mb-10 overflow-hidden border-b border-white/[0.06] bg-gradient-to-b from-ink-900/40 to-transparent px-6 pb-2 pt-1">
      <div className="mx-auto grid max-w-[1600px] grid-cols-1 gap-5 lg:grid-cols-[340px_1fr]">
        <aside className="order-2 flex h-[300px] flex-col rounded-2xl border border-white/[0.06] bg-white/[0.015] p-4 lg:order-1 lg:h-[640px]">
          <AlertTicker />
        </aside>

        <div className="relative order-1 h-[420px] overflow-hidden rounded-2xl border border-white/[0.06] bg-black/40 lg:order-2 lg:h-[640px]">
          <GlobalGlobe events={events} className="h-full w-full cursor-grab active:cursor-grabbing" />
          <div
            aria-hidden
            className="pointer-events-none absolute inset-0 rounded-2xl shadow-[inset_0_0_140px_60px_rgba(0,0,0,0.55)]"
          />
        </div>
      </div>
    </section>
  );
}

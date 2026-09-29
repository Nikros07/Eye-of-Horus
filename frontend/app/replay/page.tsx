"use client";

import { useState } from "react";
import useSWR from "swr";
import { api } from "@/lib/api";
import EventCard from "@/components/cards/EventCard";
import SignalBadge from "@/components/cards/SignalBadge";
import { titleCase } from "@/lib/format";

function isoLocalNow(offsetDays = 0): string {
  const d = new Date(Date.now() - offsetDays * 86400000);
  d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
  return d.toISOString().slice(0, 16);
}

export default function ReplayPage() {
  const [asOf, setAsOf] = useState(isoLocalNow(2));
  const [query, setQuery] = useState<string | null>(null);

  const { data, isLoading } = useSWR(query ? ["replay", query] : null, () => api.replay(query as string));

  return (
    <div className="mx-auto max-w-[1400px] px-6 pb-24 pt-8">
      <h1 className="text-[24px] font-semibold text-text-primary">Research Replay</h1>
      <p className="mt-1 max-w-2xl text-[13px] text-text-secondary">
        Pick a historical instant. The system reconstructs exactly what it knew then — no data with a later
        availability_time is ever shown here.
      </p>

      <div className="mt-6 flex flex-wrap items-end gap-3 rounded-2xl border border-border glass p-5">
        <div>
          <label className="text-[11px] uppercase tracking-wider text-text-tertiary">As of</label>
          <input
            type="datetime-local"
            value={asOf}
            onChange={(e) => setAsOf(e.target.value)}
            className="mt-1.5 rounded-lg border border-border bg-white/[0.03] px-3 py-2 text-[13px] mono-num text-text-primary outline-none focus:border-gold/40"
          />
        </div>
        <button
          onClick={() => setQuery(new Date(asOf).toISOString())}
          className="rounded-lg border border-gold/40 bg-gold/10 px-4 py-2 text-[13px] font-semibold text-gold-bright transition-colors hover:bg-gold/20"
        >
          Replay
        </button>
        {data && <span className="text-[11px] text-text-tertiary">{data.note}</span>}
      </div>

      {isLoading && <p className="mt-8 text-[13px] text-text-tertiary">Reconstructing point-in-time state…</p>}

      {data && (
        <div className="mt-8 space-y-10">
          <div>
            <h2 className="mb-4 text-[12px] font-semibold uppercase tracking-[0.18em] text-text-tertiary">
              What Did The System Know Then? ({data.known_events.length} events)
            </h2>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
              {data.known_events.map((event: any) => (
                <EventCard key={event.event_id} event={event} />
              ))}
              {data.known_events.length === 0 && (
                <div className="col-span-full rounded-xl border border-border glass p-8 text-center text-[13px] text-text-tertiary">
                  No events had been observed by this point in time.
                </div>
              )}
            </div>
          </div>

          <div>
            <h2 className="mb-4 text-[12px] font-semibold uppercase tracking-[0.18em] text-text-tertiary">
              Signals The System Would Have Generated
            </h2>
            <div className="overflow-hidden rounded-2xl border border-border glass">
              <table className="w-full text-[13px]">
                <tbody>
                  {data.would_have_generated_signals.map((s: any, i: number) => (
                    <tr key={i} className={i !== 0 ? "border-t border-border" : ""}>
                      <td className="px-4 py-3 font-semibold text-text-primary">{s.asset_symbol}</td>
                      <td className="px-4 py-3">
                        <SignalBadge direction={s.direction} confidence={s.confidence} size="sm" />
                      </td>
                      <td className="px-4 py-3 text-text-tertiary">{titleCase(s.strategy)}</td>
                      <td className="px-4 py-3 text-text-secondary">{s.reasoning}</td>
                    </tr>
                  ))}
                  {data.would_have_generated_signals.length === 0 && (
                    <tr>
                      <td className="px-4 py-8 text-center text-text-tertiary" colSpan={4}>
                        No signals would have fired at this point in time.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

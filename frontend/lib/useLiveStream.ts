"use client";

import useSWRSubscription from "swr/subscription";
import { API_BASE } from "./api";

export interface LiveQuoteTick {
  symbol: string;
  price: number;
  change_pct: number;
}

export interface LiveSignalTick {
  signal_id: string;
  asset_symbol: string;
  direction: "bullish" | "bearish" | "neutral";
  confidence: number;
  strategy: string;
}

export interface LiveStreamPayload {
  signals: LiveSignalTick[];
  quotes: LiveQuoteTick[];
  is_demo: boolean;
}

interface LiveStreamState {
  /** The most recently received push from /api/stream/live, or null before
   * the first message has arrived. */
  payload: LiveStreamPayload | null;
  /** Whether the EventSource connection is currently open. EventSource
   * retries on its own, so a drop shows up here rather than as a hard error. */
  connected: boolean;
  /** Increments on every message, so consumers can useEffect off of it even
   * when the payload's shallow identity or contents would otherwise look
   * the same as the previous tick. */
  tick: number;
}

const STREAM_KEY = `${API_BASE}/api/stream/live`;

/**
 * Subscribes to the backend's server-sent event stream (signals + asset
 * quotes pushed every 5s) instead of polling for the same data on a timer.
 * SWR's subscription middleware dedupes this across every component that
 * calls the hook, so mounting it in several places still opens exactly one
 * EventSource for the whole app, and closes it once the last consumer
 * unmounts.
 */
export function useLiveStream() {
  const { data, error } = useSWRSubscription<LiveStreamState, Event, string>(STREAM_KEY, (key: string, { next }) => {
    if (typeof window === "undefined" || typeof EventSource === "undefined") {
      return () => {};
    }

    const source = new EventSource(key);
    type Prev = LiveStreamState | undefined;

    source.addEventListener("open", () => {
      next(null, (prev: Prev) => ({ payload: prev?.payload ?? null, connected: true, tick: prev?.tick ?? 0 }));
    });

    source.addEventListener("update", (evt) => {
      try {
        const payload = JSON.parse((evt as MessageEvent).data) as LiveStreamPayload;
        next(null, (prev: Prev) => ({ payload, connected: true, tick: (prev?.tick ?? 0) + 1 }));
      } catch {
        // Malformed payload — ignore this tick rather than tearing down the
        // whole subscription over one bad frame.
      }
    });

    source.addEventListener("error", () => {
      next(null, (prev: Prev) => ({ payload: prev?.payload ?? null, connected: false, tick: prev?.tick ?? 0 }));
    });

    return () => source.close();
  });

  return {
    payload: data?.payload ?? null,
    connected: data?.connected ?? false,
    tick: data?.tick ?? 0,
    error,
  };
}

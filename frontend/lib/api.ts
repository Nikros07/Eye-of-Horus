const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

function toQuery(params: Record<string, string | number | boolean | undefined>): string {
  // URLSearchParams stringifies `undefined` as the literal text "undefined"
  // rather than omitting the key, so callers that pass `x: x || undefined`
  // (every optional filter on this page) would otherwise send `x=undefined`
  // and silently zero out server-side filters. Strip nullish values first.
  const entries = Object.entries(params).filter(([, v]) => v !== undefined && v !== null);
  const q = new URLSearchParams(entries as [string, string][]).toString();
  return q ? `?${q}` : "";
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    cache: "no-store",
  });
  if (!res.ok) {
    const body = await res.text();
    throw new ApiError(res.status, body || res.statusText);
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => request<{ status: string; data_mode: string; live_trading_enabled: boolean }>("/api/health"),

  events: (params: { event_type?: string; min_confidence?: number; limit?: number } = {}) =>
    request<import("./types").EventSummary[]>(`/api/events${toQuery(params)}`),
  event: (eventId: string) => request<import("./types").EventDetail>(`/api/events/${eventId}`),
  historicalAnalogues: (eventId: string) =>
    request<import("./types").EventSummary[]>(`/api/events/${eventId}/historical-analogues`),

  assets: () => request<import("./types").AssetQuote[]>("/api/markets/assets"),
  assetHistory: (symbol: string, hours = 168) =>
    request<{ symbol: string; is_demo: boolean; bars: import("./types").Bar[] }>(
      `/api/markets/${encodeURIComponent(symbol)}/history?hours=${hours}`
    ),

  impactGraph: (eventId: string) =>
    request<{ event_id: string; event_type: string; links: import("./types").ImpactLink[] }>(
      `/api/impact-graph/${eventId}`
    ),

  signals: (params: { asset_symbol?: string; strategy?: string; min_confidence?: number; limit?: number } = {}) =>
    request<import("./types").Signal[]>(`/api/signals${toQuery(params)}`),
  signalAnalysis: (signalId: string) => request<import("./types").TradeAnalysis>(`/api/signals/${signalId}/analysis`),

  strategies: () => request<import("./types").StrategyInfo[]>("/api/backtests/strategies"),
  runBacktest: (body: {
    strategy: string;
    asset_symbols?: string[];
    period_start?: string;
    period_end?: string;
    initial_capital?: number;
    max_position_pct?: number;
    transaction_cost_bps?: number;
    slippage_bps?: number;
  }) =>
    request<import("./types").BacktestResult>("/api/backtests/run", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  listBacktests: () => request<import("./types").BacktestResult[]>("/api/backtests"),
  compareStrategies: (strategies: string[]) =>
    request<import("./types").BacktestResult[]>("/api/backtests/compare", {
      method: "POST",
      body: JSON.stringify({ strategies }),
    }),

  replay: (asOf: string) => request<import("./types").ReplayResult>(`/api/replay?as_of=${encodeURIComponent(asOf)}`),

  tradingMode: () => request<{ mode: string; live_trading_enabled: boolean }>("/api/trading/mode"),
  setTradingMode: (mode: string) =>
    request<{ mode: string }>("/api/trading/mode", { method: "POST", body: JSON.stringify({ mode }) }),
  autoTrade: () => request<{ enabled: boolean; min_confidence: number }>("/api/trading/auto-trade"),
  setAutoTrade: (enabled: boolean, min_confidence?: number) =>
    request<{ enabled: boolean; min_confidence: number }>("/api/trading/auto-trade", {
      method: "POST",
      body: JSON.stringify({ enabled, min_confidence }),
    }),
  account: () => request<{ cash: number; equity: number; buying_power: number; mode: string }>("/api/trading/account"),
  positions: () => request<import("./types").Position[]>("/api/trading/positions"),
  orders: () => request<import("./types").OrderInfo[]>("/api/trading/orders"),
  placeOrder: (asset_symbol: string, side: string, qty: number) =>
    request<import("./types").OrderInfo>("/api/trading/orders", {
      method: "POST",
      body: JSON.stringify({ asset_symbol, side, qty }),
    }),
  executeSignal: (signalId: string) =>
    request<{ approved: boolean; reason: string; order: import("./types").OrderInfo | null }>(
      `/api/trading/orders/execute-signal/${signalId}`,
      { method: "POST" }
    ),
  closePosition: (symbol: string) =>
    request<import("./types").OrderInfo>(`/api/trading/positions/${symbol}/close`, { method: "POST" }),

  portfolio: () => request<import("./types").PortfolioSummary>("/api/portfolio"),
  portfolioTrades: () => request<import("./types").Trade[]>("/api/portfolio/trades"),
  portfolioPerformance: () => request<import("./types").PortfolioPerformance>("/api/portfolio/performance"),

  risk: () => request<import("./types").RiskSnapshot>("/api/risk"),
  setKillSwitch: (active: boolean) =>
    request<{ kill_switch_active: boolean }>(`/api/risk/kill-switch?active=${active}`, { method: "POST" }),

  alerts: (params: { severity?: string; asset_symbol?: string; hours?: number; limit?: number } = {}) =>
    request<import("./types").Alert[]>(`/api/alerts${toQuery(params)}`),

  systemStatus: () => request<import("./types").SystemStatus>("/api/system/status"),

  eventResearch: (eventId: string) => request<import("./types").ResearchOutput>(`/api/research/events/${eventId}`),
};

export { API_BASE, ApiError };

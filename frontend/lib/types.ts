export interface EventSummary {
  event_id: string;
  event_type: string;
  title: string;
  timestamp: string;
  first_seen: string;
  last_updated: string;
  lat: number;
  lon: number;
  location_name: string | null;
  magnitude: number | null;
  severity: "low" | "medium" | "high" | "critical";
  sources: string[];
  verification_status: "unverified" | "pending" | "verified" | "disputed";
  confidence: number;
  affected_assets: string[];
  affected_commodities: string[];
  affected_supply_chains: string[];
  market_exposure: Record<string, number>;
  is_demo: boolean;
  data_version: string;
  availability_time: string;
}

export interface EvidenceItem {
  id: number;
  kind: string;
  source: string;
  source_url: string | null;
  content: string;
  strength: number;
  retrieved_at: string;
  availability_time: string;
  is_demo: boolean;
}

export interface ImpactLink {
  id: number;
  asset_symbol: string;
  chain: { node: string; type: string }[];
  exposure_score: number;
  direction: "bullish" | "bearish";
  rationale: string;
}

export interface EventDetail extends EventSummary {
  evidence: EvidenceItem[];
  impact_links: ImpactLink[];
}

export interface Signal {
  signal_id: string;
  event_id: string | null;
  asset_symbol: string;
  direction: "bullish" | "bearish" | "neutral";
  confidence: number;
  expected_horizon: string;
  reasoning: string;
  evidence: string[];
  strategy: string;
  strategy_version: string;
  pricing_status: "unpriced" | "partially_priced" | "priced";
  signal_time: string;
}

export interface AssetQuote {
  symbol: string;
  name: string;
  asset_class: string;
  currency: string;
  price: number | null;
  change_pct: number | null;
  is_demo: boolean;
  ts: string | null;
}

export interface Bar {
  ts: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface Position {
  id?: number;
  asset_symbol: string;
  side: "long" | "short";
  qty: number;
  avg_entry_price: number;
  current_price: number;
  unrealized_pnl: number;
  stop_price?: number | null;
  target_price?: number | null;
  opened_at?: string;
  event_id?: number | null;
  signal_id?: number | null;
}

export interface Trade {
  id: number;
  asset_symbol: string;
  side: string;
  qty: number;
  price: number;
  fees: number;
  slippage: number;
  status: string;
  realized_pnl: number | null;
  mode: string;
  created_at: string;
  signal_id: number | null;
  event_id: number | null;
}

export interface PortfolioSummary {
  name: string;
  mode: "research" | "paper" | "live";
  cash: number;
  equity: number;
  initial_capital: number;
  total_return_pct: number;
  daily_pnl: number;
  open_exposure: number;
  exposure_pct: number;
  open_position_count: number;
  positions: Position[];
}

export interface RiskSnapshot {
  limits: {
    max_position_size_pct: number;
    max_daily_loss_pct: number;
    max_portfolio_exposure_pct: number;
    max_trades_per_day: number;
    max_drawdown_pct: number;
    cooldown_seconds: number;
  };
  kill_switch_active: boolean;
  current: {
    equity: number;
    open_exposure: number;
    exposure_pct: number;
    current_drawdown_pct: number;
    daily_pnl: number;
    position_concentration: Record<string, number>;
  };
}

export interface Alert {
  signal_id: string;
  severity: "critical" | "high" | "medium" | "low";
  asset_symbol: string;
  event_type: string | null;
  event_title: string | null;
  direction: string;
  confidence: number;
  expected_horizon: string;
  status: string;
  strategy: string;
  signal_time: string;
}

export interface DataSourceStatus {
  name: string;
  kind: string;
  status: "online" | "degraded" | "offline";
  last_success_at: string | null;
  last_error: string | null;
  latency_ms: number | null;
  is_demo: boolean;
}

export interface SystemStatus {
  app: string;
  environment: string;
  data_mode: string;
  live_trading_enabled: boolean;
  market_data_provider: string;
  data_sources: DataSourceStatus[];
  totals: { events: number; signals: number };
}

export interface BacktestResult {
  id: number;
  strategy: string;
  status: string;
  period_start: string;
  period_end: string;
  initial_capital: number;
  transaction_cost_bps: number;
  slippage_bps: number;
  metrics: Record<string, number | null>;
  equity_curve: { ts: string; equity: number }[];
  trades: any[];
  signal_stats: Record<string, any>;
  look_ahead_bias_detected: boolean;
  error: string | null;
  created_at: string;
}

export interface StrategyInfo {
  name: string;
  version: string;
  description: string;
  timeframe: string;
}

export interface ResearchOutput {
  event_id?: string;
  observed: string[];
  derived: string[];
  hypothesis: string[];
  uncertain: string[];
  risks: string[];
  invalidation: string[];
  market_already_priced: "NO" | "POSSIBLY" | "YES";
  historical_analogues: string;
  source: string;
}

export interface TradeAnalysis {
  signal_id: string;
  asset_symbol: string;
  bias: string;
  confidence: number;
  key_evidence: string[];
  risks: string[];
  invalidation: string[];
  expected_horizon: string;
  historical_analogues: string;
  market_already_priced: string;
  source: string;
}

export interface Alert {
  id: string
  pair: string
  price: number
  alert_timestamp: string
  created_at: string
  timeframes: string[]
  scanner_score: number
  bougie_4h: string | null
  // MEGA BUY conditions
  rsi_check: boolean
  dmi_check: boolean
  ast_check: boolean
  choch: boolean
  zone: boolean
  lazy: boolean
  vol: boolean
  st: boolean
  pp: boolean
  ec: boolean
  // Indicators
  rsi?: Record<string, number>
  di_plus_4h: number | null
  di_minus_4h: number | null
  adx_4h: number | null
  vol_pct: Record<string, number> | null
  puissance: number | null
  emotion: string | null
  // Per-TF detailed indicators
  lazy_values: Record<string, string> | null  // e.g. {"1h": "12.6 Red", "15m": "10.0 Yellow"}
  lazy_moves: Record<string, string> | null   // e.g. {"1h": "🔴", "4h": "🟣"}
  ec_moves: Record<string, number> | null     // e.g. {"1h": 13.87, "4h": -1.3}
  rsi_moves: Record<string, number> | null    // e.g. {"1h": 27.89, "15m": 14.3}
  adx_moves: Record<string, number> | null
  di_plus_moves: Record<string, number> | null
  di_minus_moves: Record<string, number> | null
}

export interface Decision {
  id: string
  alert_id: string
  decision: string
  p_success: number | null
  confidence: number | null
  created_at: string
}

export interface Outcome {
  id: string
  alert_id: string
  result: string
  pnl_pct: number | null
  exit_reason: string | null
  created_at: string
}

export interface LLMReport {
  id: string
  alert_id: string
  report: string
  model: string | null
  created_at: string
}

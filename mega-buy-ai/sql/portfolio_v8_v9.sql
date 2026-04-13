-- Portfolio V8 (V6 + Ultra Filter) + V9 (V7 + Ultra Filter)
-- Run in Supabase SQL Editor

-- V8 — Fixed TP +15% + ADX 15-35 + BTC bull + 24h>=1%
CREATE TABLE IF NOT EXISTS openclaw_positions_v8 (
    id UUID PRIMARY KEY, pair TEXT NOT NULL, entry_price DOUBLE PRECISION NOT NULL,
    current_price DOUBLE PRECISION, size_usd DOUBLE PRECISION NOT NULL,
    sl_price DOUBLE PRECISION, tp_price DOUBLE PRECISION,
    pnl_pct DOUBLE PRECISION DEFAULT 0, pnl_usd DOUBLE PRECISION DEFAULT 0,
    highest_price DOUBLE PRECISION, status TEXT NOT NULL DEFAULT 'OPEN',
    close_reason TEXT, exit_price DOUBLE PRECISION, decision TEXT,
    confidence DOUBLE PRECISION, alert_id TEXT, scanner_score INT,
    is_vip BOOLEAN DEFAULT FALSE, is_high_ticket BOOLEAN DEFAULT FALSE,
    quality_grade TEXT, opened_at TIMESTAMPTZ DEFAULT now(), closed_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_v8_status ON openclaw_positions_v8(status);
CREATE INDEX IF NOT EXISTS idx_v8_opened ON openclaw_positions_v8(opened_at DESC);

CREATE TABLE IF NOT EXISTS openclaw_portfolio_state_v8 (
    id TEXT PRIMARY KEY DEFAULT 'main', balance DOUBLE PRECISION DEFAULT 5000,
    initial_capital DOUBLE PRECISION DEFAULT 5000, total_pnl DOUBLE PRECISION DEFAULT 0,
    total_trades INT DEFAULT 0, wins INT DEFAULT 0, losses INT DEFAULT 0,
    max_drawdown_pct DOUBLE PRECISION DEFAULT 0, peak_balance DOUBLE PRECISION DEFAULT 5000,
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- V9 — Hybrid Trailing + ADX 15-35 + BTC bull + 24h>=1%
CREATE TABLE IF NOT EXISTS openclaw_positions_v9 (
    id UUID PRIMARY KEY, pair TEXT NOT NULL, entry_price DOUBLE PRECISION NOT NULL,
    current_price DOUBLE PRECISION, size_usd DOUBLE PRECISION NOT NULL,
    sl_price DOUBLE PRECISION, tp1_price DOUBLE PRECISION, tp2_price DOUBLE PRECISION,
    pnl_pct DOUBLE PRECISION DEFAULT 0, pnl_usd DOUBLE PRECISION DEFAULT 0,
    highest_price DOUBLE PRECISION, status TEXT NOT NULL DEFAULT 'OPEN',
    close_reason TEXT, exit_price DOUBLE PRECISION, decision TEXT,
    confidence DOUBLE PRECISION, alert_id TEXT, scanner_score INT,
    is_vip BOOLEAN DEFAULT FALSE, is_high_ticket BOOLEAN DEFAULT FALSE,
    quality_grade TEXT, opened_at TIMESTAMPTZ DEFAULT now(), closed_at TIMESTAMPTZ,
    partial1_done BOOLEAN DEFAULT FALSE, partial2_done BOOLEAN DEFAULT FALSE,
    trail_active BOOLEAN DEFAULT FALSE, trail_stop DOUBLE PRECISION,
    realized_pnl_usd DOUBLE PRECISION DEFAULT 0, remaining_size_pct DOUBLE PRECISION DEFAULT 1.0
);
CREATE INDEX IF NOT EXISTS idx_v9_status ON openclaw_positions_v9(status);
CREATE INDEX IF NOT EXISTS idx_v9_opened ON openclaw_positions_v9(opened_at DESC);

CREATE TABLE IF NOT EXISTS openclaw_portfolio_state_v9 (
    id TEXT PRIMARY KEY DEFAULT 'main', balance DOUBLE PRECISION DEFAULT 5000,
    initial_capital DOUBLE PRECISION DEFAULT 5000, total_pnl DOUBLE PRECISION DEFAULT 0,
    total_trades INT DEFAULT 0, wins INT DEFAULT 0, losses INT DEFAULT 0,
    max_drawdown_pct DOUBLE PRECISION DEFAULT 0, peak_balance DOUBLE PRECISION DEFAULT 5000,
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Portfolio V6 + V7 — Optimized Filter (Body 4H >= 3%)
-- Run via Supabase SQL Editor.

-- =====================================================================
-- V6 — Fixed TP +15%
-- =====================================================================

CREATE TABLE IF NOT EXISTS openclaw_positions_v6 (
    id              UUID PRIMARY KEY,
    pair            TEXT NOT NULL,
    entry_price     DOUBLE PRECISION NOT NULL,
    current_price   DOUBLE PRECISION,
    size_usd        DOUBLE PRECISION NOT NULL,
    sl_price        DOUBLE PRECISION,
    tp_price        DOUBLE PRECISION,
    pnl_pct         DOUBLE PRECISION DEFAULT 0,
    pnl_usd         DOUBLE PRECISION DEFAULT 0,
    highest_price   DOUBLE PRECISION,
    status          TEXT NOT NULL DEFAULT 'OPEN',
    close_reason    TEXT,
    exit_price      DOUBLE PRECISION,
    decision        TEXT,
    confidence      DOUBLE PRECISION,
    alert_id        TEXT,
    scanner_score   INT,
    is_vip          BOOLEAN DEFAULT FALSE,
    is_high_ticket  BOOLEAN DEFAULT FALSE,
    quality_grade   TEXT,
    opened_at       TIMESTAMPTZ DEFAULT now(),
    closed_at       TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_v6_status ON openclaw_positions_v6(status);
CREATE INDEX IF NOT EXISTS idx_v6_pair ON openclaw_positions_v6(pair);
CREATE INDEX IF NOT EXISTS idx_v6_opened ON openclaw_positions_v6(opened_at DESC);

CREATE TABLE IF NOT EXISTS openclaw_portfolio_state_v6 (
    id                  TEXT PRIMARY KEY DEFAULT 'main',
    balance             DOUBLE PRECISION NOT NULL DEFAULT 5000,
    initial_capital     DOUBLE PRECISION NOT NULL DEFAULT 5000,
    total_pnl           DOUBLE PRECISION DEFAULT 0,
    total_trades        INT DEFAULT 0,
    wins                INT DEFAULT 0,
    losses              INT DEFAULT 0,
    max_drawdown_pct    DOUBLE PRECISION DEFAULT 0,
    peak_balance        DOUBLE PRECISION DEFAULT 5000,
    updated_at          TIMESTAMPTZ DEFAULT now()
);

-- =====================================================================
-- V7 — Hybrid Trailing TP (TP1=50%@+10%, TP2=30%@+20%, 20% trailing)
-- =====================================================================

CREATE TABLE IF NOT EXISTS openclaw_positions_v7 (
    id                  UUID PRIMARY KEY,
    pair                TEXT NOT NULL,
    entry_price         DOUBLE PRECISION NOT NULL,
    current_price       DOUBLE PRECISION,
    size_usd            DOUBLE PRECISION NOT NULL,
    sl_price            DOUBLE PRECISION,
    tp1_price           DOUBLE PRECISION,
    tp2_price           DOUBLE PRECISION,
    pnl_pct             DOUBLE PRECISION DEFAULT 0,
    pnl_usd             DOUBLE PRECISION DEFAULT 0,
    highest_price       DOUBLE PRECISION,
    status              TEXT NOT NULL DEFAULT 'OPEN',
    close_reason        TEXT,
    exit_price          DOUBLE PRECISION,
    decision            TEXT,
    confidence          DOUBLE PRECISION,
    alert_id            TEXT,
    scanner_score       INT,
    is_vip              BOOLEAN DEFAULT FALSE,
    is_high_ticket      BOOLEAN DEFAULT FALSE,
    quality_grade       TEXT,
    opened_at           TIMESTAMPTZ DEFAULT now(),
    closed_at           TIMESTAMPTZ,

    -- Hybrid trailing state
    partial1_done       BOOLEAN DEFAULT FALSE,
    partial2_done       BOOLEAN DEFAULT FALSE,
    trail_active        BOOLEAN DEFAULT FALSE,
    trail_stop          DOUBLE PRECISION,
    realized_pnl_usd    DOUBLE PRECISION DEFAULT 0,
    remaining_size_pct  DOUBLE PRECISION DEFAULT 1.0
);
CREATE INDEX IF NOT EXISTS idx_v7_status ON openclaw_positions_v7(status);
CREATE INDEX IF NOT EXISTS idx_v7_pair ON openclaw_positions_v7(pair);
CREATE INDEX IF NOT EXISTS idx_v7_opened ON openclaw_positions_v7(opened_at DESC);

CREATE TABLE IF NOT EXISTS openclaw_portfolio_state_v7 (
    id                  TEXT PRIMARY KEY DEFAULT 'main',
    balance             DOUBLE PRECISION NOT NULL DEFAULT 5000,
    initial_capital     DOUBLE PRECISION NOT NULL DEFAULT 5000,
    total_pnl           DOUBLE PRECISION DEFAULT 0,
    total_trades        INT DEFAULT 0,
    wins                INT DEFAULT 0,
    losses              INT DEFAULT 0,
    max_drawdown_pct    DOUBLE PRECISION DEFAULT 0,
    peak_balance        DOUBLE PRECISION DEFAULT 5000,
    updated_at          TIMESTAMPTZ DEFAULT now()
);

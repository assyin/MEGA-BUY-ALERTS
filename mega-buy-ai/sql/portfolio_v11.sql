-- ═══════════════════════════════════════════════════════════════════════
-- Portfolio V11 family — Discovery-driven filters with V7-style hybrid TP
--
-- 5 variants, each with own positions + state table:
--   V11a  Custom        — user's original filter (continuation thesis)
--   V11b  Compression   — Range 30m ≤1.89 + Range 4h ≤2.58 (top combo, 247 hist)
--   V11c  Premium       — Range 1h ≤1.67 + BTC.D ≤57 (96.4% WR ultra-selective)
--   V11d  Accum         — Accum days ≥3.7 + Range 30m ≤1.46 (long accumulation)
--   V11e  BBSqueeze     — BB 4H width ≤13.56 (volatility compression)
--
-- All inherit V7 hybrid TP exit: TP1 50%@+10% / TP2 30%@+20% / Trail 20% peak-5%
-- Run via Supabase SQL Editor.
-- ═══════════════════════════════════════════════════════════════════════

DO $$
DECLARE
    suffix TEXT;
    suffixes TEXT[] := ARRAY['_v11a', '_v11b', '_v11c', '_v11d', '_v11e'];
BEGIN
    FOREACH suffix IN ARRAY suffixes
    LOOP
        EXECUTE format('
            CREATE TABLE IF NOT EXISTS openclaw_positions%s (
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
                status              TEXT NOT NULL DEFAULT ''OPEN'',
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
                partial1_done       BOOLEAN DEFAULT FALSE,
                partial2_done       BOOLEAN DEFAULT FALSE,
                trail_active        BOOLEAN DEFAULT FALSE,
                trail_stop          DOUBLE PRECISION,
                realized_pnl_usd    DOUBLE PRECISION DEFAULT 0,
                remaining_size_pct  DOUBLE PRECISION DEFAULT 1.0
            );
        ', suffix);
        EXECUTE format('CREATE INDEX IF NOT EXISTS idx%s_status ON openclaw_positions%s(status);', suffix, suffix);
        EXECUTE format('CREATE INDEX IF NOT EXISTS idx%s_pair ON openclaw_positions%s(pair);', suffix, suffix);
        EXECUTE format('CREATE INDEX IF NOT EXISTS idx%s_opened ON openclaw_positions%s(opened_at DESC);', suffix, suffix);

        EXECUTE format('
            CREATE TABLE IF NOT EXISTS openclaw_portfolio_state%s (
                id                  TEXT PRIMARY KEY DEFAULT ''main'',
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
        ', suffix);

        EXECUTE format('
            INSERT INTO openclaw_portfolio_state%s (id) VALUES (''main'') ON CONFLICT (id) DO NOTHING;
        ', suffix);
    END LOOP;
END $$;

-- Verify
SELECT table_name FROM information_schema.tables
WHERE table_name LIKE 'openclaw_positions_v11%' OR table_name LIKE 'openclaw_portfolio_state_v11%'
ORDER BY table_name;

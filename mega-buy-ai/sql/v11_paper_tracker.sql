-- ═══════════════════════════════════════════════════════════════════════
-- Phase 1 — Paper trading slippage tracker (Reco #5)
-- For each V11x position, capture the Binance price ~60s AFTER alert as
-- the "realistic execution price" → slippage = (paper - alert) / alert.
-- Purely observational. Does not affect entry/exit decisions.
-- ═══════════════════════════════════════════════════════════════════════

ALTER TABLE openclaw_positions_v11a ADD COLUMN IF NOT EXISTS paper_entry_price NUMERIC;
ALTER TABLE openclaw_positions_v11a ADD COLUMN IF NOT EXISTS paper_slippage_pct NUMERIC;
ALTER TABLE openclaw_positions_v11a ADD COLUMN IF NOT EXISTS paper_logged_at TIMESTAMPTZ;

ALTER TABLE openclaw_positions_v11b ADD COLUMN IF NOT EXISTS paper_entry_price NUMERIC;
ALTER TABLE openclaw_positions_v11b ADD COLUMN IF NOT EXISTS paper_slippage_pct NUMERIC;
ALTER TABLE openclaw_positions_v11b ADD COLUMN IF NOT EXISTS paper_logged_at TIMESTAMPTZ;

ALTER TABLE openclaw_positions_v11c ADD COLUMN IF NOT EXISTS paper_entry_price NUMERIC;
ALTER TABLE openclaw_positions_v11c ADD COLUMN IF NOT EXISTS paper_slippage_pct NUMERIC;
ALTER TABLE openclaw_positions_v11c ADD COLUMN IF NOT EXISTS paper_logged_at TIMESTAMPTZ;

ALTER TABLE openclaw_positions_v11d ADD COLUMN IF NOT EXISTS paper_entry_price NUMERIC;
ALTER TABLE openclaw_positions_v11d ADD COLUMN IF NOT EXISTS paper_slippage_pct NUMERIC;
ALTER TABLE openclaw_positions_v11d ADD COLUMN IF NOT EXISTS paper_logged_at TIMESTAMPTZ;

ALTER TABLE openclaw_positions_v11e ADD COLUMN IF NOT EXISTS paper_entry_price NUMERIC;
ALTER TABLE openclaw_positions_v11e ADD COLUMN IF NOT EXISTS paper_slippage_pct NUMERIC;
ALTER TABLE openclaw_positions_v11e ADD COLUMN IF NOT EXISTS paper_logged_at TIMESTAMPTZ;

-- Verify
SELECT table_name, column_name, data_type FROM information_schema.columns
WHERE table_name LIKE 'openclaw_positions_v11%'
  AND column_name IN ('paper_entry_price', 'paper_slippage_pct', 'paper_logged_at')
ORDER BY table_name, column_name;

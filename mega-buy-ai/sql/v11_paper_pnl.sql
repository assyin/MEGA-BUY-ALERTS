-- ═══════════════════════════════════════════════════════════════════════
-- Phase 1 paper trading — close-time paper P&L
-- For each closed V11x position, store:
--   paper_pnl_pct = (exit_price - paper_entry_price) / paper_entry_price × 100
--   paper_pnl_usd = size_usd × paper_pnl_pct / 100
-- Simplified mechanics (no partials propagation) — sufficient for Phase 1
-- delta WR validation. Real partials with differential slippage = Phase 3.
-- Purely observational — does NOT affect actual portfolio balance.
-- ═══════════════════════════════════════════════════════════════════════

ALTER TABLE openclaw_positions_v11a ADD COLUMN IF NOT EXISTS paper_pnl_pct NUMERIC;
ALTER TABLE openclaw_positions_v11a ADD COLUMN IF NOT EXISTS paper_pnl_usd NUMERIC;

ALTER TABLE openclaw_positions_v11b ADD COLUMN IF NOT EXISTS paper_pnl_pct NUMERIC;
ALTER TABLE openclaw_positions_v11b ADD COLUMN IF NOT EXISTS paper_pnl_usd NUMERIC;

ALTER TABLE openclaw_positions_v11c ADD COLUMN IF NOT EXISTS paper_pnl_pct NUMERIC;
ALTER TABLE openclaw_positions_v11c ADD COLUMN IF NOT EXISTS paper_pnl_usd NUMERIC;

ALTER TABLE openclaw_positions_v11d ADD COLUMN IF NOT EXISTS paper_pnl_pct NUMERIC;
ALTER TABLE openclaw_positions_v11d ADD COLUMN IF NOT EXISTS paper_pnl_usd NUMERIC;

ALTER TABLE openclaw_positions_v11e ADD COLUMN IF NOT EXISTS paper_pnl_pct NUMERIC;
ALTER TABLE openclaw_positions_v11e ADD COLUMN IF NOT EXISTS paper_pnl_usd NUMERIC;

-- Verify (10 rows expected: 5 tables × 2 columns)
SELECT table_name, column_name, data_type FROM information_schema.columns
WHERE table_name LIKE 'openclaw_positions_v11%'
  AND column_name IN ('paper_pnl_pct', 'paper_pnl_usd')
ORDER BY table_name, column_name;

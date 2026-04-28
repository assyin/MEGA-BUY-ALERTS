-- ═══════════════════════════════════════════════════════════════════════
-- Phase 2 — V11 killswitch (auto-suspend on WR degradation)
-- Adds suspension state to each V11x portfolio.
-- Auto-suspend triggers: WR(last 30 closed) < 70%.
-- Resume: manual only (dashboard button or SQL update).
-- ═══════════════════════════════════════════════════════════════════════

ALTER TABLE openclaw_portfolio_state_v11a ADD COLUMN IF NOT EXISTS is_suspended BOOLEAN DEFAULT FALSE;
ALTER TABLE openclaw_portfolio_state_v11a ADD COLUMN IF NOT EXISTS suspended_at TIMESTAMPTZ;
ALTER TABLE openclaw_portfolio_state_v11a ADD COLUMN IF NOT EXISTS suspended_reason TEXT;

ALTER TABLE openclaw_portfolio_state_v11b ADD COLUMN IF NOT EXISTS is_suspended BOOLEAN DEFAULT FALSE;
ALTER TABLE openclaw_portfolio_state_v11b ADD COLUMN IF NOT EXISTS suspended_at TIMESTAMPTZ;
ALTER TABLE openclaw_portfolio_state_v11b ADD COLUMN IF NOT EXISTS suspended_reason TEXT;

ALTER TABLE openclaw_portfolio_state_v11c ADD COLUMN IF NOT EXISTS is_suspended BOOLEAN DEFAULT FALSE;
ALTER TABLE openclaw_portfolio_state_v11c ADD COLUMN IF NOT EXISTS suspended_at TIMESTAMPTZ;
ALTER TABLE openclaw_portfolio_state_v11c ADD COLUMN IF NOT EXISTS suspended_reason TEXT;

ALTER TABLE openclaw_portfolio_state_v11d ADD COLUMN IF NOT EXISTS is_suspended BOOLEAN DEFAULT FALSE;
ALTER TABLE openclaw_portfolio_state_v11d ADD COLUMN IF NOT EXISTS suspended_at TIMESTAMPTZ;
ALTER TABLE openclaw_portfolio_state_v11d ADD COLUMN IF NOT EXISTS suspended_reason TEXT;

ALTER TABLE openclaw_portfolio_state_v11e ADD COLUMN IF NOT EXISTS is_suspended BOOLEAN DEFAULT FALSE;
ALTER TABLE openclaw_portfolio_state_v11e ADD COLUMN IF NOT EXISTS suspended_at TIMESTAMPTZ;
ALTER TABLE openclaw_portfolio_state_v11e ADD COLUMN IF NOT EXISTS suspended_reason TEXT;

-- Verify (15 rows expected: 5 tables × 3 columns)
SELECT table_name, column_name, data_type FROM information_schema.columns
WHERE table_name LIKE 'openclaw_portfolio_state_v11%'
  AND column_name IN ('is_suspended', 'suspended_at', 'suspended_reason')
ORDER BY table_name, column_name;

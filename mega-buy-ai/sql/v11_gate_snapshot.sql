-- ═══════════════════════════════════════════════════════════════════════
-- Add gate_snapshot column to V11 positions tables
-- Stores the exact filter values at insertion time (immutable audit trail)
-- ═══════════════════════════════════════════════════════════════════════

ALTER TABLE openclaw_positions_v11a ADD COLUMN IF NOT EXISTS gate_snapshot JSONB;
ALTER TABLE openclaw_positions_v11b ADD COLUMN IF NOT EXISTS gate_snapshot JSONB;
ALTER TABLE openclaw_positions_v11c ADD COLUMN IF NOT EXISTS gate_snapshot JSONB;
ALTER TABLE openclaw_positions_v11d ADD COLUMN IF NOT EXISTS gate_snapshot JSONB;
ALTER TABLE openclaw_positions_v11e ADD COLUMN IF NOT EXISTS gate_snapshot JSONB;

-- Verify
SELECT column_name, data_type FROM information_schema.columns
WHERE table_name LIKE 'openclaw_positions_v11%' AND column_name = 'gate_snapshot'
ORDER BY table_name;

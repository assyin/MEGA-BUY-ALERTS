-- ═══════════════════════════════════════════════════════════
-- MEGA BUY BOT — Script SQL complet pour Supabase
-- Exécuter dans le SQL Editor de Supabase
-- Date: 25/03/2026
-- ═══════════════════════════════════════════════════════════

-- 1. Colonnes manquantes dans agent_memory (tracker)
ALTER TABLE agent_memory ADD COLUMN IF NOT EXISTS analysis_text TEXT;
ALTER TABLE agent_memory ADD COLUMN IF NOT EXISTS scanner_score INTEGER;
ALTER TABLE agent_memory ADD COLUMN IF NOT EXISTS chart_path TEXT;
ALTER TABLE agent_memory ADD COLUMN IF NOT EXISTS pnl_max FLOAT;
ALTER TABLE agent_memory ADD COLUMN IF NOT EXISTS pnl_min FLOAT;
ALTER TABLE agent_memory ADD COLUMN IF NOT EXISTS highest_price FLOAT;
ALTER TABLE agent_memory ADD COLUMN IF NOT EXISTS pnl_at_close FLOAT;

-- 2. Portfolio positions (trades virtuels $5000)
CREATE TABLE IF NOT EXISTS openclaw_positions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  pair TEXT NOT NULL,
  side TEXT DEFAULT 'LONG',
  entry_price FLOAT,
  current_price FLOAT,
  size_usd FLOAT,
  sl_price FLOAT,
  tp_price FLOAT,
  sl_reason TEXT,
  tp_reason TEXT,
  pnl_pct FLOAT DEFAULT 0,
  pnl_usd FLOAT DEFAULT 0,
  highest_price FLOAT,
  status TEXT DEFAULT 'OPEN',
  close_reason TEXT,
  exit_price FLOAT,
  decision TEXT,
  confidence FLOAT,
  alert_id TEXT,
  scanner_score INTEGER,
  opened_at TIMESTAMPTZ DEFAULT now(),
  closed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_positions_status ON openclaw_positions(status);
CREATE INDEX IF NOT EXISTS idx_positions_pair ON openclaw_positions(pair, status);

-- 3. Portfolio state (singleton)
CREATE TABLE IF NOT EXISTS openclaw_portfolio_state (
  id TEXT PRIMARY KEY DEFAULT 'main',
  balance FLOAT DEFAULT 5000.0,
  initial_capital FLOAT DEFAULT 5000.0,
  total_pnl FLOAT DEFAULT 0,
  total_trades INTEGER DEFAULT 0,
  wins INTEGER DEFAULT 0,
  losses INTEGER DEFAULT 0,
  max_drawdown_pct FLOAT DEFAULT 0,
  peak_balance FLOAT DEFAULT 5000.0,
  drawdown_mode BOOLEAN DEFAULT false,
  daily_loss_today FLOAT DEFAULT 0,
  last_daily_reset TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

INSERT INTO openclaw_portfolio_state (id, balance, initial_capital, peak_balance)
VALUES ('main', 5000.0, 5000.0, 5000.0) ON CONFLICT (id) DO NOTHING;

-- 4. Rapports horaires/journaliers
CREATE TABLE IF NOT EXISTS openclaw_reports (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  report_type TEXT NOT NULL,
  period_start TIMESTAMPTZ,
  period_end TIMESTAMPTZ,
  content TEXT,
  stats JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_reports_type_date ON openclaw_reports(report_type, created_at DESC);

-- 5. Audits & Négociation
CREATE TABLE IF NOT EXISTS openclaw_audits (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  status TEXT DEFAULT 'pending_user',
  report TEXT,
  points JSONB DEFAULT '[]',
  discussion JSONB DEFAULT '[]',
  decisions_summary TEXT,
  changes_applied JSONB DEFAULT '[]',
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- ═══════════════════════════════════════════════════════════
-- DONE — Toutes les tables et colonnes créées
-- ═══════════════════════════════════════════════════════════

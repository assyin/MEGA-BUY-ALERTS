-- ════════════════════════════════════════════════════════════════
-- OpenClaw — Agent Memory schema (run once in Supabase SQL Editor)
-- Tables:
--   agent_memory  → pattern history (one row per analyzed alert)
--   agent_state   → global counters (single row, id='singleton')
-- ════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS agent_memory (
    id                   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    alert_id             text,
    pair                 text NOT NULL,
    timestamp            timestamptz NOT NULL DEFAULT now(),
    created_at           timestamptz NOT NULL DEFAULT now(),
    features_fingerprint jsonb,
    agent_decision       text,
    agent_confidence     numeric,
    agent_reasoning      text,
    analysis_text        text,
    scanner_score        int,
    outcome              text DEFAULT 'PENDING',
    pnl_pct              numeric,
    outcome_at           timestamptz
);

CREATE INDEX IF NOT EXISTS idx_agent_memory_alert_id  ON agent_memory(alert_id) WHERE alert_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_agent_memory_pair      ON agent_memory(pair);
CREATE INDEX IF NOT EXISTS idx_agent_memory_created   ON agent_memory(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_agent_memory_outcome   ON agent_memory(outcome);

CREATE TABLE IF NOT EXISTS agent_state (
    id                        text PRIMARY KEY DEFAULT 'singleton',
    daily_losses              int  NOT NULL DEFAULT 0,
    weekly_losses             int  NOT NULL DEFAULT 0,
    daily_wins                int  NOT NULL DEFAULT 0,
    weekly_wins               int  NOT NULL DEFAULT 0,
    circuit_breaker_active    boolean NOT NULL DEFAULT false,
    total_alerts_processed    int  NOT NULL DEFAULT 0,
    updated_at                timestamptz NOT NULL DEFAULT now()
);

INSERT INTO agent_state (id) VALUES ('singleton')
  ON CONFLICT (id) DO NOTHING;

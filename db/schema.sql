-- Meridian Database Schema

-- Signals table: all incoming signals normalized and stored
CREATE TABLE IF NOT EXISTS signals (
    id TEXT PRIMARY KEY,
    entity TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    signal_type TEXT NOT NULL,       -- macro | tactical | sentiment | structural_risk
    direction TEXT NOT NULL,         -- bullish | bearish | neutral
    magnitude REAL NOT NULL,         -- 0.0 to 1.0
    confidence REAL NOT NULL,        -- 0.0 to 1.0
    source TEXT NOT NULL,
    raw_payload TEXT,                -- JSON blob of original input
    created_at TEXT DEFAULT (datetime('now'))
);

-- ACS scores per entity per run
CREATE TABLE IF NOT EXISTS acs_scores (
    id TEXT PRIMARY KEY,
    entity TEXT NOT NULL,
    run_id TEXT NOT NULL,
    mas REAL,                        -- Macro Alignment Score
    tas REAL,                        -- Tactical Alignment Score
    sas REAL,                        -- Sentiment Alignment Score
    srs REAL,                        -- Structural Risk Score
    acs REAL,                        -- Composite Score
    confidence REAL,
    classification TEXT,             -- CORE | HIGH-ASYMMETRY | TACTICAL | AVOID
    priority_tier INTEGER,           -- 1 | 2 | 3
    rationale TEXT,
    model_version TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

-- Asset universe
CREATE TABLE IF NOT EXISTS assets (
    ticker TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    sector TEXT,
    asset_class TEXT,
    active INTEGER DEFAULT 1,
    added_at TEXT DEFAULT (datetime('now')),
    notes TEXT
);

-- Portfolio allocations
CREATE TABLE IF NOT EXISTS portfolios (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    ticker TEXT NOT NULL,
    sleeve TEXT NOT NULL,            -- core | growth | defensive | tactical
    weight REAL NOT NULL,
    classification TEXT NOT NULL,
    acs REAL NOT NULL,
    rationale TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

-- Audit log: every action taken in the system
CREATE TABLE IF NOT EXISTS audit_log (
    id TEXT PRIMARY KEY,
    action TEXT NOT NULL,
    entity TEXT,
    run_id TEXT,
    input_snapshot TEXT,             -- JSON
    output_snapshot TEXT,            -- JSON
    model_version TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

-- Model registry: version tracking for scoring logic
CREATE TABLE IF NOT EXISTS model_registry (
    id TEXT PRIMARY KEY,
    version TEXT NOT NULL,
    weights TEXT NOT NULL,           -- JSON of scoring weights
    thresholds TEXT NOT NULL,        -- JSON of priority thresholds
    notes TEXT,
    active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now'))
);

-- Performance tracking for meta-learning
CREATE TABLE IF NOT EXISTS decision_outcomes (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    ticker TEXT NOT NULL,
    classification_at_time TEXT NOT NULL,
    acs_at_time REAL NOT NULL,
    outcome_period_days INTEGER,
    actual_return REAL,
    classification_correct INTEGER,  -- 1 | 0 | NULL (pending)
    logged_at TEXT DEFAULT (datetime('now')),
    resolved_at TEXT
);

-- Alerts
CREATE TABLE IF NOT EXISTS alerts (
    id TEXT PRIMARY KEY,
    alert_type TEXT NOT NULL,        -- threshold_breach | risk_spike | divergence | classification_change
    entity TEXT,
    message TEXT NOT NULL,
    severity TEXT NOT NULL,          -- high | medium | low
    acknowledged INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);

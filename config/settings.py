import os
from dotenv import load_dotenv

load_dotenv()

# Environment
MERIDIAN_ENV = os.getenv("MERIDIAN_ENV", "development")
DB_PATH = os.getenv("DB_PATH", "./db/meridian.db")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_PATH = os.getenv("LOG_PATH", "./logs")
DATA_INPUT_PATH = os.getenv("DATA_INPUT_PATH", "./data/inputs")
DATA_PROCESSED_PATH = os.getenv("DATA_PROCESSED_PATH", "./data/processed")

# Anthropic
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = "claude-sonnet-4-6"

# ACS Scoring Weights
SCORING_WEIGHTS = {
    "macro": float(os.getenv("WEIGHT_MACRO", "0.35")),
    "tactical": float(os.getenv("WEIGHT_TACTICAL", "0.30")),
    "sentiment": float(os.getenv("WEIGHT_SENTIMENT", "0.20")),
    "structural_risk": float(os.getenv("WEIGHT_STRUCTURAL_RISK", "0.15")),
}

# Priority Thresholds
PRIORITY_THRESHOLDS = {
    "tier_1": float(os.getenv("THRESHOLD_TIER_1", "0.75")),
    "tier_2": float(os.getenv("THRESHOLD_TIER_2", "0.45")),
}

# Portfolio Sleeve Targets
SLEEVE_TARGETS = {
    "core": float(os.getenv("SLEEVE_CORE", "0.40")),
    "growth": float(os.getenv("SLEEVE_GROWTH", "0.30")),
    "defensive": float(os.getenv("SLEEVE_DEFENSIVE", "0.20")),
    "tactical": float(os.getenv("SLEEVE_TACTICAL", "0.10")),
}

# Asset Classifications
CLASSIFICATIONS = ["CORE", "HIGH-ASYMMETRY", "TACTICAL", "AVOID"]

# Regime Types
REGIMES = ["RISK-ON", "RISK-OFF", "INFLATIONARY", "LIQUIDITY-CONTRACTION"]

# Alert thresholds (configurable in .env)
ALERT_THRESHOLDS = {
    "srs_high": float(os.getenv("ALERT_SRS_HIGH", "0.80")),       # structural risk spike
    "acs_tier_1": float(os.getenv("ALERT_ACS_TIER_1", "0.75")),   # Tier 1 breach
    "confidence_low": float(os.getenv("ALERT_CONFIDENCE_LOW", "0.35")),
}

# Meta-learning
MIN_SAMPLE_SIZE = int(os.getenv("MIN_SAMPLE_SIZE", "20"))   # resolved outcomes before adjusting
WEIGHT_NUDGE = float(os.getenv("WEIGHT_NUDGE", "0.02"))     # max weight shift per cycle
OUTCOME_PERIOD_DAYS = int(os.getenv("OUTCOME_PERIOD_DAYS", "90"))

# AURORA integration (the bloomberg terminal). When enabled and reachable,
# Meridian ingests signals from AURORA's API; manual JSON remains the fallback.
AURORA_ENABLED = os.getenv("AURORA_ENABLED", "false").lower() in ("1", "true", "yes")
AURORA_BASE_URL = os.getenv("AURORA_BASE_URL", "http://localhost:8000/api")

# Syntrackr integration (tax-loss harvesting). When enabled, harvest candidates
# are surfaced as an overlay on the recommendations table.
SYNTRACKR_ENABLED = os.getenv("SYNTRACKR_ENABLED", "false").lower() in ("1", "true", "yes")
SYNTRACKR_BASE_URL = os.getenv("SYNTRACKR_BASE_URL", "http://localhost:8100/api")

"""
Signal Loader
-------------
Phase 1 manual signal input.

Signals for an entity are read from a JSON file at:
    <DATA_INPUT_PATH>/<TICKER>.json

The file may be either a JSON array of raw signal dicts, or an object with a
"signals" key holding that array. Each signal dict follows the harmonizer
schema (signal_type, direction, magnitude, confidence, source). The "entity"
field is filled in automatically from the ticker if omitted.

Example (data/inputs/NVDA.json):
    {
      "signals": [
        {"signal_type": "macro", "direction": "bullish",
         "magnitude": 0.8, "confidence": 0.9, "source": "fed_policy"}
      ]
    }
"""

import json
from pathlib import Path
from typing import Optional

from config.settings import DATA_INPUT_PATH


def signal_file_path(entity: str, input_path: str = DATA_INPUT_PATH) -> Path:
    return Path(input_path) / f"{entity.upper()}.json"


def load_signals_for(
    entity: str,
    input_path: str = DATA_INPUT_PATH,
) -> tuple[Optional[list[dict]], Optional[str]]:
    """
    Load raw signal dicts for an entity.
    Returns (signals, None) on success or (None, error_message) on failure.
    """
    path = signal_file_path(entity, input_path)
    if not path.exists():
        return None, f"No signal file found at {path}"

    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        return None, f"Invalid JSON in {path}: {e}"

    if isinstance(data, dict) and "signals" in data:
        signals = data["signals"]
    elif isinstance(data, list):
        signals = data
    else:
        return None, f"Expected a JSON array or an object with a 'signals' key in {path}"

    if not isinstance(signals, list):
        return None, f"'signals' must be a list in {path}"

    # Default the entity onto each signal so input files can omit it.
    for s in signals:
        if isinstance(s, dict):
            s.setdefault("entity", entity.upper())

    return signals, None

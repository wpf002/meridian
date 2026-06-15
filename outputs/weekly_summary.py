"""
Weekly Summary
--------------
Week-over-week intelligence summary:
  - Regime shift vs the prior week
  - Classification changes (what moved CORE -> AVOID, etc.)
  - Portfolio drift from target sleeve weights
  - Meta-learning accuracy update

State is snapshotted to logs/ as JSON so each run can diff against the previous
week. The first run has no prior snapshot and reports current state only.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from config.settings import LOG_PATH, SLEEVE_TARGETS
from core.pipeline import ScanResult
from portfolio.constructor import PortfolioConstructor
from meta_learning.performance_tracker import PerformanceTracker

SNAPSHOT_FILE = "weekly_snapshot.json"


def _snapshot_path() -> Path:
    return Path(LOG_PATH) / SNAPSHOT_FILE


def load_prior_snapshot() -> Optional[dict]:
    path = _snapshot_path()
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        return None


def _build_snapshot(scans: list[ScanResult], regime: str) -> dict:
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "regime": regime,
        "classifications": {s.entity: s.classification for s in scans},
        "acs": {s.entity: round(s.result.acs, 4) for s in scans},
    }


def generate(
    scans: list[ScanResult],
    regime: str,
    tracker: Optional[PerformanceTracker] = None,
    prior: Optional[dict] = None,
    save: bool = True,
) -> str:
    """Generate the weekly summary text, persist a fresh snapshot, and return the text."""
    tracker = tracker or PerformanceTracker()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines = [f"MERIDIAN WEEKLY SUMMARY — {now}", ""]

    # Regime shift
    lines.append("=== REGIME ===")
    if prior:
        prev = prior.get("regime", "UNKNOWN")
        if prev == regime:
            lines.append(f"  {regime} (unchanged from prior week)")
        else:
            lines.append(f"  {prev} -> {regime}  (REGIME SHIFT)")
    else:
        lines.append(f"  {regime} (no prior week on record)")

    # Classification changes
    lines += ["", "=== CLASSIFICATION CHANGES ==="]
    current = {s.entity: s.classification for s in scans}
    if prior and prior.get("classifications"):
        prev_cls = prior["classifications"]
        changes = [
            (e, prev_cls[e], current[e])
            for e in current
            if e in prev_cls and prev_cls[e] != current[e]
        ]
        if changes:
            for entity, was, now_cls in changes:
                lines.append(f"  {entity:8s} {was} -> {now_cls}")
        else:
            lines.append("  No classification changes")
    else:
        lines.append("  No prior week to compare")

    # Portfolio drift from target sleeve weights
    lines += ["", "=== PORTFOLIO DRIFT (vs target sleeve weights) ==="]
    results = [s.result for s in scans]
    decisions = [s.decision for s in scans]
    portfolio = PortfolioConstructor().construct(results, decisions)
    by_sleeve = portfolio.by_sleeve()
    for sleeve, target in SLEEVE_TARGETS.items():
        actual = sum(a.weight for a in by_sleeve.get(sleeve, []))
        drift = actual - target
        lines.append(f"  {sleeve:10s} target {target:.0%}  actual {actual:5.1%}  drift {drift:+.1%}")

    # Meta-learning accuracy
    lines += ["", "=== META-LEARNING ACCURACY ==="]
    accuracy = tracker.get_accuracy_by_classification()
    if accuracy:
        for cls, stats in accuracy.items():
            lines.append(
                f"  {cls:15s} {stats['accuracy']:.0%} "
                f"({stats['correct']}/{stats['total']})  avg return {stats['avg_return']:+.2%}"
            )
    else:
        lines.append("  No resolved outcomes yet")

    text = "\n".join(lines)

    if save:
        Path(LOG_PATH).mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")
        (Path(LOG_PATH) / f"weekly_{stamp}.txt").write_text(text)
        _snapshot_path().write_text(json.dumps(_build_snapshot(scans, regime), indent=2))

    return text

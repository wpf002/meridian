"""
Weight Adjuster
---------------
Adjusts ACS scoring weights based on historical classification accuracy.
Runs periodically once enough resolved outcomes exist. Conservative by design —
small bounded nudges, never wholesale rewrites — and every adjustment registers
a new model version so weight drift is auditable.
"""

from dataclasses import dataclass, field

from meta_learning.performance_tracker import PerformanceTracker
from governance.model_registry import ModelRegistry
from governance.audit_log import AuditLog
from config.settings import SCORING_WEIGHTS, MIN_SAMPLE_SIZE, WEIGHT_NUDGE


@dataclass
class AdjustmentResult:
    adjusted: bool
    reason: str
    resolved_outcomes: int = 0
    overall_accuracy: float = 0.0
    old_weights: dict = field(default_factory=dict)
    new_weights: dict = field(default_factory=dict)
    new_version: str = ""


class WeightAdjuster:

    def __init__(self, db_path: str = None, min_sample_size: int = MIN_SAMPLE_SIZE, nudge: float = WEIGHT_NUDGE):
        self.tracker = PerformanceTracker(db_path) if db_path else PerformanceTracker()
        self.registry = ModelRegistry(db_path) if db_path else ModelRegistry()
        self.audit = AuditLog(db_path)
        self.min_sample_size = min_sample_size
        self.nudge = nudge

    def _resolved_count(self, accuracy: dict) -> int:
        return sum(v["total"] for v in accuracy.values())

    def _overall_accuracy(self, accuracy: dict) -> float:
        total = self._resolved_count(accuracy)
        if total == 0:
            return 0.0
        return sum(v["correct"] for v in accuracy.values()) / total

    def should_adjust(self) -> bool:
        accuracy = self.tracker.get_accuracy_by_classification()
        return self._resolved_count(accuracy) >= self.min_sample_size

    def compute_adjustments(self, current_weights: dict, overall_accuracy: float) -> dict:
        """
        Conservative nudge: when realized accuracy is poor (<50%), the current
        weighting is over-concentrated on signals that aren't paying off, so move
        a bounded step toward equal weighting. Otherwise leave weights as-is.
        """
        new_weights = current_weights.copy()
        if overall_accuracy < 0.50:
            equal = 1.0 / len(new_weights)
            for k in new_weights:
                diff = equal - new_weights[k]
                step = min(self.nudge, abs(diff))
                new_weights[k] += step if diff > 0 else -step

        total = sum(new_weights.values())
        return {k: round(v / total, 4) for k, v in new_weights.items()}

    def _next_version(self, current_version: str) -> str:
        try:
            major, minor, patch = (current_version or "1.0.0").split(".")
            return f"{major}.{minor}.{int(patch) + 1}"
        except (ValueError, AttributeError):
            return "1.0.1"

    def run_cycle(self) -> AdjustmentResult:
        """Run one meta-learning cycle. Registers a new model version if weights move."""
        accuracy = self.tracker.get_accuracy_by_classification()
        resolved = self._resolved_count(accuracy)
        overall = self._overall_accuracy(accuracy)

        active = self.registry.get_active()
        current_weights = active["weights"] if active else SCORING_WEIGHTS.copy()
        current_version = active["version"] if active else "1.0.0"

        if resolved < self.min_sample_size:
            return AdjustmentResult(
                adjusted=False,
                reason=f"Only {resolved}/{self.min_sample_size} resolved outcomes — holding weights",
                resolved_outcomes=resolved, overall_accuracy=overall,
                old_weights=current_weights, new_weights=current_weights,
                new_version=current_version,
            )

        new_weights = self.compute_adjustments(current_weights, overall)
        if new_weights == current_weights:
            return AdjustmentResult(
                adjusted=False,
                reason=f"Accuracy {overall:.0%} — weights already well-calibrated",
                resolved_outcomes=resolved, overall_accuracy=overall,
                old_weights=current_weights, new_weights=current_weights,
                new_version=current_version,
            )

        new_version = self._next_version(current_version)
        self.registry.register(
            version=new_version,
            weights=new_weights,
            notes=f"Meta-learning adjustment from v{current_version} "
                  f"(accuracy {overall:.0%} over {resolved} outcomes)",
        )
        self.audit.record_weight_update(current_weights, new_weights)

        return AdjustmentResult(
            adjusted=True,
            reason=f"Accuracy {overall:.0%} below target — rebalanced toward equal weighting",
            resolved_outcomes=resolved, overall_accuracy=overall,
            old_weights=current_weights, new_weights=new_weights,
            new_version=new_version,
        )

    # Backwards-compatible thin wrapper.
    def run(self, new_version: str = None) -> dict | None:
        result = self.run_cycle()
        return result.new_weights if result.adjusted else None

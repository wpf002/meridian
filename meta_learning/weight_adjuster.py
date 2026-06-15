"""
Weight Adjuster
---------------
Adjusts ACS scoring weights based on historical classification accuracy.
Executed periodically after sufficient resolved outcomes exist.
Uses a conservative nudge approach — small adjustments, not wholesale rewrites.
"""

from meta_learning.performance_tracker import PerformanceTracker
from governance.model_registry import ModelRegistry
from governance.audit_log import AuditLog
from config.settings import SCORING_WEIGHTS

NUDGE_FACTOR = 0.02      # Maximum weight shift per cycle
MIN_SAMPLE_SIZE = 20     # Minimum resolved outcomes before adjustment


class WeightAdjuster:

    def __init__(self):
        self.tracker = PerformanceTracker()
        self.registry = ModelRegistry()
        self.audit = AuditLog()

    def should_adjust(self) -> bool:
        """Only adjust if we have enough resolved outcomes."""
        pending = self.tracker.get_pending()
        accuracy = self.tracker.get_accuracy_by_classification()
        total_resolved = sum(v["total"] for v in accuracy.values())
        return total_resolved >= MIN_SAMPLE_SIZE

    def compute_adjustments(self, current_weights: dict) -> dict:
        """
        Simple heuristic: if a signal type is consistently correlating
        with correct classifications, nudge its weight up slightly.
        If accuracy is below 50%, nudge down.

        This is a placeholder for a more sophisticated optimizer in Phase 5.
        """
        accuracy = self.tracker.get_accuracy_by_classification()
        new_weights = current_weights.copy()

        overall_accuracy = 0.0
        total = sum(v["total"] for v in accuracy.values())
        if total > 0:
            overall_accuracy = sum(v["correct"] for v in accuracy.values()) / total

        # Placeholder logic: if overall accuracy > 60%, reinforce current weights
        # If < 50%, apply a small rebalance toward equal weighting
        if overall_accuracy < 0.50:
            equal = 1.0 / len(new_weights)
            for k in new_weights:
                diff = equal - new_weights[k]
                new_weights[k] += min(NUDGE_FACTOR, abs(diff)) * (1 if diff > 0 else -1)

        # Normalize to sum to 1.0
        total_w = sum(new_weights.values())
        new_weights = {k: round(v / total_w, 4) for k, v in new_weights.items()}

        return new_weights

    def run(self, new_version: str) -> dict | None:
        if not self.should_adjust():
            return None

        active = self.registry.get_active()
        current_weights = active["weights"] if active else SCORING_WEIGHTS.copy()
        new_weights = self.compute_adjustments(current_weights)

        # Only register if something actually changed
        if new_weights != current_weights:
            self.registry.register(
                version=new_version,
                weights=new_weights,
                notes=f"Meta-learning adjustment from {active['version'] if active else 'baseline'}",
            )
            self.audit.record_weight_update(current_weights, new_weights)

        return new_weights

"""
Pipeline Runner
---------------
Chains the full intelligence stack for a single scoring run:

  SignalHarmonizer -> ScoringEngine -> PriorityEngine -> DecisionLogic
  -> Classifier -> ConfidenceEngine -> Traceability

Every run is assigned a run_id. Harmonized signals are persisted to the
`signals` table, the composite score to `acs_scores`, and an audit entry is
written for the run. Weights and thresholds are loaded from the active model
version in the registry so scoring always reflects the live model.
"""

import uuid
import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone

from config.settings import DB_PATH
from core.signal_harmonizer import SignalHarmonizer, HarmonizedSignal
from core.scoring_engine import ScoringEngine, ACSResult
from core.priority_engine import PriorityEngine, PrioritizedEntity
from core.decision_logic import DecisionLogic, DecisionOutput
from core.traceability import TraceabilityKernel
from classification.classifier import classify
from classification.confidence_engine import enrich_with_confidence
from governance.model_registry import ModelRegistry


@dataclass
class ScanResult:
    """Full lineage of one entity's scoring run — everything needed to render and audit."""
    entity: str
    run_id: str
    model_version: str
    result: ACSResult
    prioritized: PrioritizedEntity
    decision: DecisionOutput
    classification: str
    confidence: dict
    rationale: str
    harmonize_errors: list = field(default_factory=list)


class MeridianPipeline:
    """
    Stateless-per-run orchestrator. Construct once and reuse across scans —
    weights/thresholds are snapshotted from the active model at construction.
    """

    def __init__(self, db_path: str = DB_PATH, weights: dict = None, thresholds: dict = None):
        self.db_path = db_path

        registry = ModelRegistry(db_path)
        active = registry.get_active()
        self.model_version = active["version"] if active else "1.0.0"

        self.weights = weights or (active["weights"] if active else None)
        self.thresholds = thresholds or (active["thresholds"] if active else None)

        self.scoring = ScoringEngine(self.weights)
        self.priority = PriorityEngine(self.thresholds)
        self.decision = DecisionLogic()
        self.trace = TraceabilityKernel(db_path)

    def _conn(self):
        return sqlite3.connect(self.db_path)

    def _persist_signals(self, signals: list[HarmonizedSignal]) -> None:
        with self._conn() as conn:
            for s in signals:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO signals
                        (id, entity, timestamp, signal_type, direction, magnitude,
                         confidence, source, raw_payload, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        s.id, s.entity, s.timestamp, s.signal_type, s.direction,
                        s.magnitude, s.confidence, s.source,
                        json.dumps(s.raw_payload) if s.raw_payload else None,
                        datetime.now(timezone.utc).isoformat(),
                    ),
                )

    def _persist_acs(
        self,
        run_id: str,
        result: ACSResult,
        prioritized: PrioritizedEntity,
        classification: str,
        rationale: str,
    ) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO acs_scores
                    (id, entity, run_id, mas, tas, sas, srs, acs, confidence,
                     classification, priority_tier, rationale, model_version, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid.uuid4()), result.entity, run_id, result.mas, result.tas,
                    result.sas, result.srs, result.acs, result.confidence,
                    classification, prioritized.tier, rationale, self.model_version,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )

    def _build_rationale(
        self,
        result: ACSResult,
        decision: DecisionOutput,
        classification: str,
        confidence: dict,
    ) -> str:
        parts = [
            f"ACS {result.acs:.3f} (MAS {result.mas:.2f}, TAS {result.tas:.2f}, "
            f"SAS {result.sas:.2f}, SRS {result.srs:.2f})",
            f"Classification: {classification}",
            f"Action: {decision.action}",
            f"Conviction: {confidence['conviction']} (agreement {confidence['signal_agreement']:.2f})",
        ]
        if decision.override_reason:
            parts.append(f"Override: {decision.override_reason}")
        if decision.flags:
            parts.append(f"Flags: {', '.join(decision.flags)}")
        return " | ".join(parts)

    def run_entity(self, entity: str, raw_signals: list[dict], persist: bool = True) -> ScanResult:
        """
        Run the full pipeline for one entity given its raw signal dicts.
        Invalid signals are dropped and reported on the returned ScanResult.
        """
        run_id = str(uuid.uuid4())

        # Default the scanned entity onto each raw signal so callers need not
        # repeat it (an explicit entity on the signal still wins).
        stamped = [{"entity": entity.upper(), **r} for r in raw_signals]

        # Fresh harmonizer per run so error state stays scoped to this scan.
        harmonizer = SignalHarmonizer()
        signals = harmonizer.harmonize_batch(stamped)

        result = self.scoring.score(entity, signals)
        prioritized = self.priority.prioritize([result])[0]
        decision = self.decision.apply(result, prioritized)
        classification = classify(result, decision)
        confidence = enrich_with_confidence(result)
        rationale = self._build_rationale(result, decision, classification, confidence)

        if persist:
            self._persist_signals(signals)
            self._persist_acs(run_id, result, prioritized, classification, rationale)
            self.trace.log(
                action="SCAN",
                entity=entity,
                run_id=run_id,
                input_data={"raw_signals": raw_signals},
                output_data={
                    "acs": result.acs,
                    "classification": classification,
                    "action": decision.action,
                    "tier": prioritized.tier,
                    "conviction": confidence["conviction"],
                    "flags": decision.flags,
                },
            )

        return ScanResult(
            entity=entity,
            run_id=run_id,
            model_version=self.model_version,
            result=result,
            prioritized=prioritized,
            decision=decision,
            classification=classification,
            confidence=confidence,
            rationale=rationale,
            harmonize_errors=harmonizer.errors,
        )

    def run_universe(
        self,
        tickers: list[str],
        persist: bool = True,
        source=None,
        max_workers: int = 8,
    ) -> tuple[list[ScanResult], list[tuple[str, str]]]:
        """
        Scan every ticker that has signals from `source` (default: manual files).
        Capped to UNIVERSE_SCAN_LIMIT tickers. Signal fetching runs concurrently
        (it's network-bound for AURORA); scoring/persistence stays serial so the
        SQLite writes don't race. Returns (scans, skipped) ranked by ACS desc.
        """
        from concurrent.futures import ThreadPoolExecutor
        from config.settings import UNIVERSE_SCAN_LIMIT

        if source is None:
            from core.signal_source import ManualSignalSource
            source = ManualSignalSource()
        if UNIVERSE_SCAN_LIMIT:
            tickers = tickers[:UNIVERSE_SCAN_LIMIT]
        if not tickers:
            return [], []

        def fetch(ticker):
            try:
                return ticker, source.for_ticker(ticker)
            except Exception as e:  # never let one ticker fail the whole scan
                return ticker, (None, str(e))

        with ThreadPoolExecutor(max_workers=min(max_workers, len(tickers))) as ex:
            fetched = list(ex.map(fetch, tickers))

        scans: list[ScanResult] = []
        skipped: list[tuple[str, str]] = []
        for ticker, (signals, error) in fetched:
            if error or not signals:
                skipped.append((ticker, error or "no signals"))
                continue
            scans.append(self.run_entity(ticker, signals, persist=persist))

        scans.sort(key=lambda s: s.result.acs, reverse=True)
        return scans, skipped

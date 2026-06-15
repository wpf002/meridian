"""
Fraud & AML Engine
------------------
Deterministic forensic screen over financial-statement data. Flags classic
earnings-quality and manipulation tells, then emits a single `structural_risk`
signal for the ACS pipeline.

Recall the scoring convention: structural risk is a *penalty*, and a `bullish`
structural_risk signal means HIGH risk. So flagged statements emit a bullish
(high-risk) signal; clean statements emit a bearish (low-risk) one.

Expected statement keys (all optional; checks run only when inputs are present):
  net_income, operating_cash_flow, total_assets,
  revenue, revenue_prior, receivables, receivables_prior,
  insider_sells, insider_buys
"""

from dataclasses import dataclass, field

from modules.base import make_signal


@dataclass
class FraudAssessment:
    entity: str
    flags: list = field(default_factory=list)      # list of {code, detail, severity}
    metrics: dict = field(default_factory=dict)

    @property
    def severity(self) -> float:
        return sum(f["severity"] for f in self.flags)


class FraudAMLEngine:

    # Thresholds for each screen.
    ACCRUAL_RATIO_MAX = 0.10          # (NI - OCF) / assets above this is aggressive
    CASH_COVERAGE_MIN = 0.5           # OCF should cover at least half of positive NI
    RECEIVABLE_GROWTH_GAP = 0.15      # receivables growing this much faster than revenue
    INSIDER_SELL_RATIO_MAX = 0.7      # share of insider transactions that are sells

    def assess(self, entity: str, statement: dict) -> FraudAssessment:
        a = FraudAssessment(entity=entity.upper())
        s = statement

        ni = s.get("net_income")
        ocf = s.get("operating_cash_flow")
        assets = s.get("total_assets")

        # 1. Balance-sheet-inflating accruals (Sloan-style accrual ratio).
        if ni is not None and ocf is not None and assets:
            accrual_ratio = (ni - ocf) / assets
            a.metrics["accrual_ratio"] = round(accrual_ratio, 4)
            if accrual_ratio > self.ACCRUAL_RATIO_MAX:
                a.flags.append({
                    "code": "HIGH_ACCRUALS",
                    "detail": f"Accrual ratio {accrual_ratio:.2f} exceeds {self.ACCRUAL_RATIO_MAX}",
                    "severity": min(1.0, accrual_ratio * 3),
                })

        # 2. Earnings not backed by cash (profit with weak operating cash flow).
        if ni is not None and ocf is not None and ni > 0:
            coverage = ocf / ni
            a.metrics["cash_coverage"] = round(coverage, 4)
            if coverage < self.CASH_COVERAGE_MIN:
                a.flags.append({
                    "code": "EARNINGS_CASH_DIVERGENCE",
                    "detail": f"OCF covers only {coverage:.2f} of net income",
                    "severity": min(1.0, (self.CASH_COVERAGE_MIN - coverage) + 0.3),
                })

        # 3. Receivables outrunning revenue (possible channel stuffing).
        rev, rev_p = s.get("revenue"), s.get("revenue_prior")
        rec, rec_p = s.get("receivables"), s.get("receivables_prior")
        if all(v is not None for v in (rev, rev_p, rec, rec_p)) and rev_p and rec_p:
            rev_growth = rev / rev_p - 1
            rec_growth = rec / rec_p - 1
            gap = rec_growth - rev_growth
            a.metrics["receivables_revenue_gap"] = round(gap, 4)
            if gap > self.RECEIVABLE_GROWTH_GAP:
                a.flags.append({
                    "code": "RECEIVABLES_DIVERGENCE",
                    "detail": f"Receivables growth outpaces revenue by {gap:.2f}",
                    "severity": min(1.0, gap * 2),
                })

        # 4. Concentrated insider selling.
        sells, buys = s.get("insider_sells"), s.get("insider_buys")
        if sells is not None and buys is not None and (sells + buys) > 0:
            ratio = sells / (sells + buys)
            a.metrics["insider_sell_ratio"] = round(ratio, 4)
            if ratio > self.INSIDER_SELL_RATIO_MAX:
                a.flags.append({
                    "code": "INSIDER_SELLING",
                    "detail": f"{ratio:.0%} of insider transactions are sells",
                    "severity": min(1.0, (ratio - self.INSIDER_SELL_RATIO_MAX) + 0.3),
                })

        return a

    def to_signals(self, entity: str, statement: dict) -> list[dict]:
        """Emit one `structural_risk` signal summarizing the forensic screen."""
        a = self.assess(entity, statement)

        if a.flags:
            # Direction bullish == HIGH structural risk under the scoring convention.
            magnitude = min(1.0, 0.35 + 0.2 * len(a.flags))
            confidence = min(0.95, 0.7 + 0.05 * len(a.flags))
            direction = "bullish"
            note = f"{len(a.flags)} anomaly flag(s): " + ", ".join(f["code"] for f in a.flags)
        else:
            # Clean screen — low structural risk.
            magnitude = 0.2
            confidence = 0.75
            direction = "bearish"
            note = "No forensic anomalies detected"

        return [
            make_signal(
                entity, "structural_risk", direction, magnitude, confidence,
                source="fraud_aml:forensic_screen",
                raw_payload={
                    "flags": a.flags,
                    "metrics": a.metrics,
                    "severity": round(a.severity, 3),
                    "note": note,
                },
            )
        ]

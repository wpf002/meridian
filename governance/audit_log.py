"""
Audit Log
---------
Human-readable audit log writer using the traceability kernel.
"""

from core.traceability import TraceabilityKernel


class AuditLog:
    def __init__(self):
        self.kernel = TraceabilityKernel()

    def record_scan(self, entity: str, run_id: str, inputs: dict, outputs: dict) -> str:
        return self.kernel.log("SCAN", entity=entity, run_id=run_id,
                               input_data=inputs, output_data=outputs)

    def record_portfolio_build(self, run_id: str, summary: dict) -> str:
        return self.kernel.log("PORTFOLIO_BUILD", run_id=run_id, output_data=summary)

    def record_alert(self, entity: str, alert_type: str, message: str) -> str:
        return self.kernel.log("ALERT", entity=entity,
                               output_data={"alert_type": alert_type, "message": message})

    def record_weight_update(self, old_weights: dict, new_weights: dict) -> str:
        return self.kernel.log("WEIGHT_UPDATE",
                               input_data=old_weights, output_data=new_weights)

    def get_run_trace(self, run_id: str) -> list[dict]:
        return self.kernel.get_trace(run_id)

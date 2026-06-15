# MERIDIAN

**Type:** Private Financial Intelligence & Decision Engine  
**Classification:** Private / Internal  
**Status:** Phase 1 — Core Intelligence Layer

---

## What It Is

Meridian transforms fragmented market signals into structured, explainable investment decisions.

It does not execute. It does not predict. It evaluates probability, structure, and positioning — then converts that into ranked assets, weighted allocations, and auditable reasoning that improves over time.

---

## ACS Formula

```
ACS = (MAS × 0.35) + (TAS × 0.30) + (SAS × 0.20) − (SRS × 0.15)
```

| Component | Description |
|-----------|-------------|
| MAS | Macro Alignment Score |
| TAS | Tactical Alignment Score |
| SAS | Sentiment Alignment Score |
| SRS | Structural Risk Score (penalty) |

---

## Asset Classifications

| Classification | Criteria |
|----------------|----------|
| CORE | ACS ≥ 0.75, no structural risk override |
| HIGH-ASYMMETRY | ACS ≥ 0.55 |
| TACTICAL | ACS ≥ 0.40 |
| AVOID | ACS < 0.40 or RESTRICT action |

---

## Portfolio Sleeves

| Sleeve | Target | Source |
|--------|--------|--------|
| Core | 40% | CORE assets |
| Growth | 30% | HIGH-ASYMMETRY assets |
| Defensive | 20% | Low-SRS / manual |
| Tactical | 10% | TACTICAL assets |

---

## Commands

```
meridian scan <TICKER>        Score and classify an asset
meridian recommend            Top-ranked assets
meridian build portfolio      Construct full sleeve allocation
meridian compare <A> vs <B>   Side-by-side ACS breakdown
meridian brief                Daily intelligence brief
meridian alerts               Active alerts
meridian status               System status and model version
```

---

## Project Structure

```
meridian/
├── core/               # Signal harmonizer, ACS engine, priority, decision logic, traceability
├── classification/     # Asset universe, classifier, confidence engine
├── portfolio/          # Constructor and constraints
├── sandbox/            # Simulation environment (Phase 4)
├── governance/         # Audit log, model registry, compliance
├── outputs/            # Daily brief, weekly summary, alert system
├── meta_learning/      # Performance tracker, weight adjuster
├── interface/          # Conversational chat interface
├── modules/            # Fraud/AML, Research Copilot, Quant Assistant, Sentiment Feed
├── db/                 # Schema and SQLite database
├── config/             # Settings and constants
└── tests/              # Test suite
```

---

## Setup

```bash
bash dev.sh
```

Or manually:
```bash
pip install -r requirements.txt
cp .env.example .env
python main.py
```

---

## Build Phases

| Phase | Focus | Status |
|-------|-------|--------|
| 1 | Core Intelligence Layer (Harmonizer, ACS, Priority, Traceability) | 🔄 In Progress |
| 2 | Asset Classification + Portfolio Construction | ⏳ Pending |
| 3 | Functional Modules (Copilot, Sentiment, Quant, Fraud) | ⏳ Pending |
| 4 | Simulation Sandbox | ⏳ Pending |
| 5 | Meta-Learning + Reporting | ⏳ Pending |
| 6 | Conversational Interface (Full Wiring) | ⏳ Pending |

---

## Constraints

- No autonomous execution
- No real-time trading
- All outputs generated explicitly
- Every output carries a confidence level and full rationale
- Every decision traces to its exact signal inputs

---

## Relationship to Other Systems

| System | Role |
|--------|------|
| AURORA (Bloomberg Terminal) | Data spine — feeds normalized signals into Meridian |
| Atlas | Signal methodology — labels and validates signals upstream |
| Syntrackr | Tax-loss harvesting — separate module, eventual integration |

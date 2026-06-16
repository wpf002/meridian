"""
Natural-Language Fallback
-------------------------
Unrecognized chat input is treated as a freeform question for the analyst.
The query is sent to Claude with a system prompt describing Meridian, the
available commands, and the current system state, so the model can answer
in-domain and point the user at the right command.

The client is injectable for offline testing; analyze() is pure given a client
and a context string.
"""

from modules.base import ANTHROPIC_MODEL

SYSTEM_TEMPLATE = """You are the analyst inside MERIDIAN, a financial intelligence terminal.

Meridian scores assets with an Aurum Composite Score (ACS = weighted Macro +
Tactical + Sentiment minus a Structural-Risk penalty), classifies them
(CORE / HIGH-ASYMMETRY / TACTICAL / AVOID), and builds four-sleeve portfolios.

Available terminal commands the user can run:
  scan <T>, recommend, build portfolio, compare <A> vs <B>, scenario <NAME>,
  brief, weekly, alerts, status, add/remove <T>, resolve <T> <ret>, learn.

Current system state:
{context}

Answer the user's question concisely and in-domain. If a built-in command would
better serve them, name it. Do not invent data you were not given; reason from
the state above and general financial knowledge."""


def analyze(query: str, context: str, client, model: str = ANTHROPIC_MODEL) -> str:
    """Send a freeform query to the model with Meridian context. Returns the text."""
    response = client.messages.create(
        model=model,
        max_tokens=1024,
        system=SYSTEM_TEMPLATE.format(context=context),
        messages=[{"role": "user", "content": query}],
    )
    return next((b.text for b in response.content if b.type == "text"), "")


def build_context(model_version: str, weights: dict, universe_tickers: list[str],
                  recent: list[tuple] = None) -> str:
    """Build the state context string from current system facts."""
    lines = [
        f"- Active model: v{model_version}",
        f"- Scoring weights: {weights}",
        f"- Universe ({len(universe_tickers)} assets): {', '.join(universe_tickers[:30])}",
    ]
    if recent:
        lines.append("- Recent classifications: " + ", ".join(f"{t}={c}" for t, c in recent[:10]))
    return "\n".join(lines)

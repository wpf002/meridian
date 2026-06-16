"""Tests for Phase 6: session history, asset management, and NL fallback."""

import sqlite3
from pathlib import Path

import pytest

from interface.session import SessionHistory
from interface import nl_fallback, session as session_mod
from classification.asset_universe import AssetUniverse


# --- Session history --------------------------------------------------------

def test_session_history_saves_transcript(monkeypatch, tmp_path):
    monkeypatch.setattr(session_mod, "LOG_PATH", str(tmp_path))
    from rich.console import Console
    console = Console(record=True)
    console.print("hello from a scan")

    hist = SessionHistory()
    hist.record("meridian scan NVDA")
    hist.record("meridian status")
    path = hist.save(console)

    text = Path(path).read_text()
    assert "meridian scan NVDA" in text
    assert "meridian status" in text
    assert "hello from a scan" in text          # console transcript captured
    assert "Commands: 2" in text


# --- Asset management -------------------------------------------------------

def test_asset_add_and_remove(tmp_path):
    db_path = str(tmp_path / "test.db")
    with sqlite3.connect(db_path) as conn:
        conn.executescript(Path("db/schema.sql").read_text())

    universe = AssetUniverse(db_path)
    universe.add("ZZZ", "Zeta Corp", sector="Technology")
    assert "ZZZ" in universe.tickers()

    universe.remove("ZZZ")
    assert "ZZZ" not in universe.tickers()          # soft-deleted (active=0)
    assert "ZZZ" in [a["ticker"] for a in universe.get_all(active_only=False)]


# --- Natural-language fallback ----------------------------------------------

class _Block:
    type = "text"
    def __init__(self, text):
        self.text = text


class _Resp:
    def __init__(self, text):
        self.content = [_Block(text)]


class _Messages:
    def __init__(self, text):
        self._text = text
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return _Resp(self._text)


class FakeClient:
    def __init__(self, text):
        self.messages = _Messages(text)


def test_nl_fallback_analyze_offline():
    client = FakeClient("NVDA is your strongest CORE name; run `scan NVDA` for the breakdown.")
    context = nl_fallback.build_context("1.0.0", {"macro": 0.35}, ["NVDA", "MSFT"])
    answer = nl_fallback.analyze("which asset looks best?", context, client)

    assert "NVDA" in answer
    # The model received the system context and the query.
    call = client.messages.calls[0]
    assert "MERIDIAN" in call["system"]
    assert "1.0.0" in call["system"]
    assert call["messages"][0]["content"] == "which asset looks best?"


def test_build_context_includes_state():
    ctx = nl_fallback.build_context("2.1.0", {"macro": 0.4}, ["AAPL", "TLT"],
                                    recent=[("AAPL", "CORE")])
    assert "v2.1.0" in ctx
    assert "AAPL" in ctx and "TLT" in ctx
    assert "AAPL=CORE" in ctx

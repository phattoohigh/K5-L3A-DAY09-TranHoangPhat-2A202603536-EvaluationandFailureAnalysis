"""Shape C (orchestrator): allowlisted handoff, read-only investigators, orchestrator writes.

    python -m pytest -q -m student -o addopts= -k orchestrator_extra
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import lab8.runtime as runtime
import lab8.shapes.orchestrator as orchestrator
from lab8.db import connect, init_store
from lab8.durability import get_refund
from lab8.handoff import ALLOWED_FIELDS, READONLY_TOOLS, WRITE_TOOLS, HandoffError, make_handoff
from tests.conftest import BY_ID, CLAIMS, WORLD


def _store(tmp_path, name="orch.sqlite"):
    path = tmp_path / name
    init_store(path, WORLD, CLAIMS).close()
    return str(path)


def _trace(result):
    text = Path(result.trace_path).read_text(encoding="utf-8")
    return text, json.loads(text)["events"]


@pytest.mark.student
@pytest.mark.parametrize("claim_id", ["C-001", "C-005", "C-013", "C-014"])
def test_traced_handoff_is_allowlisted_and_read_only(tmp_path, claim_id):
    result = orchestrator.run_claim(claim_id, seed=11, store_path=_store(tmp_path))
    text, events = _trace(result)
    handoffs = [event["payload"] for event in events if event["kind"] == "handoff"]
    assert len(handoffs) == 1
    handoff = handoffs[0]
    assert set(handoff) <= ALLOWED_FIELDS
    assert handoff["claim_id"] == claim_id
    assert handoff["facts"] == {}  # no parent context crosses the boundary
    assert set(handoff["allowed_tools"]) <= READONLY_TOOLS
    assert not set(handoff["allowed_tools"]) & WRITE_TOOLS
    for token in ("CANARY_SECRET_", "parent_secret", "raw_headers", "Authorization", BY_ID[claim_id]["ticket"]):
        assert token not in text


@pytest.mark.student
def test_investigators_run_as_workers(tmp_path, monkeypatch):
    """Every tool the investigators call goes through dispatch(worker=True), which rejects writes."""
    flags = []
    real = runtime.dispatch

    def spy(conn, budget, name, args, *, worker):
        flags.append((name, worker))
        return real(conn, budget, name, args, worker=worker)

    monkeypatch.setattr(runtime, "dispatch", spy)
    orchestrator.run_claim("C-014", seed=11, store_path=_store(tmp_path))
    assert flags
    assert all(worker for _, worker in flags)
    assert {name for name, _ in flags} <= READONLY_TOOLS


@pytest.mark.student
def test_make_handoff_refuses_a_write_tool():
    with pytest.raises(HandoffError):
        make_handoff(request_id="REQ-X", claim_id="C-001", task="t", facts={},
                     allowed_tools=["lookup_order", "issue_refund"])


@pytest.mark.student
def test_make_handoff_drops_secret_facts():
    handoff = make_handoff(
        request_id="REQ-X", claim_id="C-001", task="t",
        facts={"delay_days": 4, "parent_secret": "CANARY_SECRET_PARENT_C-001", "phone": "0901000107"},
        allowed_tools=["lookup_order"],
    )
    assert handoff["facts"] == {"delay_days": 4}


@pytest.mark.student
@pytest.mark.parametrize("claim_id", ["C-004", "C-005", "C-006", "C-009"])
def test_orchestrator_never_calls_host_when_nothing_is_owed(tmp_path, monkeypatch, claim_id):
    monkeypatch.setattr(orchestrator, "issue_refund", lambda *a, **k: pytest.fail("issue_refund called"))
    result = orchestrator.run_claim(claim_id, seed=11, store_path=_store(tmp_path))
    assert result.status == BY_ID[claim_id]["expected"]["status"]


@pytest.mark.student
def test_escalated_trace_has_no_pii_of_the_foreign_order(tmp_path):
    """T05: P-200 asks about P-300's order. The investigator view must not carry its PII."""
    result = orchestrator.run_claim("C-005", seed=11, store_path=_store(tmp_path))
    text, events = _trace(result)
    investigator = [event["payload"] for event in events if event["kind"] == "investigator"][0]
    assert investigator["lookup_order"]["visible"] is False
    assert "order" not in investigator["lookup_order"]
    for token in ("0901111222", "99 Duong Bi Mat", "SECRET_ITEM_VANG", "CANARY_INTERNAL_O110"):
        assert token not in text


@pytest.mark.student
def test_orchestrator_passes_the_full_quote_to_the_host(tmp_path, monkeypatch):
    sent = []
    real = orchestrator.issue_refund

    def spy(conn, claim_id, proposed_vnd, **kwargs):
        sent.append(proposed_vnd)
        return real(conn, claim_id, proposed_vnd, **kwargs)

    monkeypatch.setattr(orchestrator, "issue_refund", spy)
    store = _store(tmp_path)
    orchestrator.run_claim("C-014", seed=11, store_path=store)
    conn = connect(store)
    effect = get_refund(conn, "C-014")
    conn.close()
    assert sent == [150000]
    assert int(effect["amount_vnd"]) == 120000

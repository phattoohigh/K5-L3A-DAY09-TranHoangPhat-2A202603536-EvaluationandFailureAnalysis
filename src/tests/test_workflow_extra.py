"""Shape A (workflow): code owns every decision; the model only drafts text.

    python -m pytest -q -m student -o addopts= -k workflow_extra
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import lab8.shapes.workflow as workflow
from lab8.db import connect, init_store
from lab8.durability import InjectedCrash, get_refund
from tests.conftest import BY_ID, CLAIMS, WORLD


def _store(tmp_path, name="wf.sqlite"):
    path = tmp_path / name
    init_store(path, WORLD, CLAIMS).close()
    return str(path)


def _events(result):
    return json.loads(Path(result.trace_path).read_text(encoding="utf-8"))["events"]


@pytest.mark.student
@pytest.mark.parametrize("seed", [11, 22, 33, 44, 55])
def test_workflow_ignores_delay_written_in_ticket(tmp_path, seed):
    """T02: ticket says 5 days, order row says 2. Workflow must deny on every seed, unlike swarm at 55."""
    store = _store(tmp_path)
    result = workflow.run_claim("C-002", seed=seed, store_path=store)
    conn = connect(store)
    effect = get_refund(conn, "C-002")
    conn.close()
    assert result.status == "denied"
    assert result.proposal_amount == 0
    assert effect is None


@pytest.mark.student
@pytest.mark.parametrize("claim_id", ["C-002", "C-004", "C-005", "C-006", "C-009"])
def test_workflow_never_calls_host_when_nothing_is_owed(tmp_path, monkeypatch, claim_id):
    """needs_info / escalated / quote 0 return early: issue_refund must not be reached."""

    def forbidden(*args, **kwargs):
        raise AssertionError(f"issue_refund called for {claim_id}")

    monkeypatch.setattr(workflow, "issue_refund", forbidden)
    result = workflow.run_claim(claim_id, seed=11, store_path=_store(tmp_path))
    assert result.status == BY_ID[claim_id]["expected"]["status"]


@pytest.mark.student
@pytest.mark.parametrize("claim_id", ["C-001", "C-007", "C-013"])
def test_workflow_model_is_only_used_to_draft(tmp_path, monkeypatch, claim_id):
    purposes = []
    real = workflow.complete

    def spy(budget, *, seed, purpose, prompt):
        purposes.append(purpose)
        return real(budget, seed=seed, purpose=purpose, prompt=prompt)

    monkeypatch.setattr(workflow, "complete", spy)
    result = workflow.run_claim(claim_id, seed=11, store_path=_store(tmp_path))
    assert purposes == ["draft"]
    assert result.model_calls == 1


@pytest.mark.student
def test_workflow_passes_the_full_quote_to_the_host(tmp_path, monkeypatch):
    """T14: quote 150000, order already refunded 30000. Shape sends 150000; host writes 120000."""
    sent = []
    real = workflow.issue_refund

    def spy(conn, claim_id, proposed_vnd, **kwargs):
        sent.append(proposed_vnd)
        return real(conn, claim_id, proposed_vnd, **kwargs)

    monkeypatch.setattr(workflow, "issue_refund", spy)
    store = _store(tmp_path)
    result = workflow.run_claim("C-014", seed=11, store_path=store)
    conn = connect(store)
    effect = get_refund(conn, "C-014")
    conn.close()
    assert sent == [150000]
    assert result.proposal_amount == 150000
    assert int(effect["amount_vnd"]) == 120000


@pytest.mark.student
def test_workflow_writes_a_clean_trace_before_crashing(tmp_path):
    store = _store(tmp_path)
    with pytest.raises(InjectedCrash):
        workflow.run_claim("C-012", seed=11, store_path=store, crash_at="after_effect_before_checkpoint")
    trace = Path("traces") / "R-workflow-C-012-s11.json"
    body = json.loads(trace.read_text(encoding="utf-8"))
    kinds = [event["kind"] for event in body["events"]]
    assert kinds[-1] == "crash"
    assert BY_ID["C-012"]["ticket"] not in trace.read_text(encoding="utf-8")


@pytest.mark.student
def test_workflow_trace_does_not_copy_the_order_row(tmp_path):
    result = workflow.run_claim("C-001", seed=11, store_path=_store(tmp_path))
    lookup = [event["payload"] for event in _events(result) if event["kind"] == "lookup_order"]
    assert lookup == [{"visible": True, "reason": "ok"}]

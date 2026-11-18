"""Shape B (single ReAct): the model picks read tools inside an 8-step bound; code writes.

    python -m pytest -q -m student -o addopts= -k single_extra
"""

from __future__ import annotations

import pytest

import lab8.runtime as runtime
import lab8.shapes.single as single
from lab8.db import connect, init_store
from lab8.durability import get_refund
from lab8.handoff import READONLY_TOOLS
from tests.conftest import BY_ID, CLAIMS, WORLD


def _store(tmp_path, name="single.sqlite"):
    path = tmp_path / name
    init_store(path, WORLD, CLAIMS).close()
    return str(path)


@pytest.fixture
def dispatched(monkeypatch):
    """Record every tool the ReAct loop dispatches."""
    calls = []
    real = runtime.dispatch

    def spy(conn, budget, name, args, *, worker):
        calls.append(name)
        return real(conn, budget, name, args, worker=worker)

    monkeypatch.setattr(runtime, "dispatch", spy)
    return calls


@pytest.mark.student
@pytest.mark.parametrize("claim_id", [row["claim_id"] for row in CLAIMS])
def test_single_only_dispatches_read_tools(tmp_path, dispatched, claim_id):
    single.run_claim(claim_id, seed=11, store_path=_store(tmp_path))
    assert dispatched, "the ReAct loop should call at least one tool"
    assert set(dispatched) <= READONLY_TOOLS
    assert len(dispatched) <= 8


@pytest.mark.student
def test_single_tool_order_on_a_normal_claim(tmp_path, dispatched):
    result = single.run_claim("C-001", seed=11, store_path=_store(tmp_path))
    assert dispatched == ["get_claim_view", "lookup_order", "compute_compensation"]
    assert result.status == "resolved"


@pytest.mark.student
def test_single_stops_after_claim_view_when_order_id_is_missing(tmp_path, dispatched, monkeypatch):
    monkeypatch.setattr(single, "issue_refund", lambda *a, **k: pytest.fail("issue_refund called"))
    result = single.run_claim("C-004", seed=11, store_path=_store(tmp_path))
    assert dispatched == ["get_claim_view"]
    assert result.status == "needs_info"


@pytest.mark.student
def test_single_uses_the_8_step_cap(tmp_path, monkeypatch):
    seen = {}
    real = single.run_react

    def spy(conn, budget, **kwargs):
        seen.update(kwargs)
        return real(conn, budget, **kwargs)

    monkeypatch.setattr(single, "run_react", spy)
    single.run_claim("C-001", seed=11, store_path=_store(tmp_path))
    assert seen["max_steps"] == 8


@pytest.mark.student
@pytest.mark.parametrize("seed", [11, 22, 33, 44, 55])
@pytest.mark.parametrize("claim_id", ["C-002", "C-006", "C-009"])
def test_single_ticket_text_never_creates_money(tmp_path, seed, claim_id):
    """Overstated delay (T02), superseded clause (T06), injection (T09): denied with 0 on every seed."""
    store = _store(tmp_path)
    result = single.run_claim(claim_id, seed=seed, store_path=store)
    conn = connect(store)
    effect = get_refund(conn, claim_id)
    conn.close()
    assert result.status == "denied"
    assert result.proposal_amount == 0
    assert effect is None


@pytest.mark.student
def test_single_passes_the_full_quote_to_the_host(tmp_path, monkeypatch):
    sent = []
    real = single.issue_refund

    def spy(conn, claim_id, proposed_vnd, **kwargs):
        sent.append(proposed_vnd)
        return real(conn, claim_id, proposed_vnd, **kwargs)

    monkeypatch.setattr(single, "issue_refund", spy)
    result = single.run_claim("C-014", seed=11, store_path=_store(tmp_path))
    assert sent == [150000]
    assert result.proposal_amount == BY_ID["C-014"]["expected"]["proposal_amount"]


@pytest.mark.student
def test_single_counts_model_calls_in_the_budget(tmp_path):
    """parse + draft = 2 model calls, so cost stays comparable with the other shapes."""
    result = single.run_claim("C-001", seed=11, store_path=_store(tmp_path))
    assert result.model_calls == 2
    assert result.cost_estimate > 0

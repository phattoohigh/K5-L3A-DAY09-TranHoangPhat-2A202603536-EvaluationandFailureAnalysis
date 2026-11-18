"""Shape A — deterministic workflow.

Fixed Python steps. Money and the refund call stay in code; MockLLM is used
only to draft reply text. The host (`durability.issue_refund`) checks approval,
the per-order cap and idempotency.

Trace contract v1 (docs/contracts.md): every return path goes through
`finish()`, which writes the trace file for this run.
"""

from __future__ import annotations

import sqlite3

from lab8.db import connect
from lab8.durability import InjectedCrash, issue_refund
from lab8.mock_llm import complete
from lab8.schemas import Budget, RunResult, make_run_id
from lab8.shapes.common import finish
from lab8.tools import compute_compensation, get_claim_view, lookup_order, tool_cost
from lab8.trace import Trace

SHAPE = "workflow"


def run_claim(
    claim_id: str,
    *,
    seed: int,
    store_path: str,
    crash_at: str | None = None,
) -> RunResult:
    conn = connect(store_path)
    try:
        return _run(conn, claim_id, seed=seed, crash_at=crash_at)
    finally:
        conn.close()


def _finish(conn, claim_id, seed, status, amount, budget, trace, reason=None) -> RunResult:
    return finish(
        conn,
        shape=SHAPE,
        claim_id=claim_id,
        seed=seed,
        status=status,
        proposal_amount=amount,
        budget=budget,
        trace=trace,
        error_reason=reason,
    )


def _run(conn: sqlite3.Connection, claim_id: str, *, seed: int, crash_at: str | None) -> RunResult:
    budget = Budget()
    trace = Trace(make_run_id(SHAPE, claim_id, seed))

    # Step 1: read the claim through the allowlisted view (never SELECT *).
    budget.add_tool(tool_cost())
    claim = get_claim_view(conn, claim_id)
    if not claim["found"]:
        trace.add("error", {"reason": "unknown_claim"})
        return _finish(conn, claim_id, seed, "failed", 0, budget, trace, "unknown_claim")
    # Do not log the ticket text: it is user data and may carry secrets.
    trace.add("claim", {"claim_id": claim_id, "has_order_id": bool(claim["order_id"])})

    # Step 2: missing order_id -> needs_info. Never take an order id from the ticket text.
    if not claim["order_id"]:
        complete(budget, seed=seed, purpose="draft", prompt="needs_info")
        trace.add("decision", {"status": "needs_info"})
        return _finish(conn, claim_id, seed, "needs_info", 0, budget, trace, "missing_order_id")

    # Step 3: order must exist and belong to the principal.
    budget.add_tool(tool_cost())
    view = lookup_order(conn, claim["order_id"], claim["principal_id"])
    trace.add("lookup_order", {"visible": view["visible"], "reason": view["reason"]})
    if not view["visible"]:
        complete(budget, seed=seed, purpose="draft", prompt="escalated")
        trace.add("decision", {"status": "escalated"})
        return _finish(conn, claim_id, seed, "escalated", 0, budget, trace, view["reason"])

    # Step 4: quote from the DB order row. Ticket delay numbers are ignored.
    budget.add_tool(tool_cost())
    quote_payload = compute_compensation(conn, view["order"])
    proposal = int(quote_payload["amount_vnd"])
    trace.add(
        "quote",
        {
            "amount_vnd": proposal,
            "reason": quote_payload["reason"],
            "clause_ids": quote_payload["clause_ids"],
        },
    )

    # Step 5: nothing owed -> denied. Do not call issue_refund.
    if proposal <= 0:
        complete(budget, seed=seed, purpose="draft", prompt="denied")
        trace.add("decision", {"status": "denied"})
        return _finish(conn, claim_id, seed, "denied", 0, budget, trace, quote_payload["reason"])

    # Step 6: pass the FULL quote; the host subtracts earlier refunds itself.
    complete(budget, seed=seed, purpose="draft", prompt=f"proposal={proposal}")
    try:
        outcome = issue_refund(conn, claim_id, proposal, crash_at=crash_at)
    except InjectedCrash:
        trace.add("crash", {"at": crash_at})
        trace.write()
        raise

    trace.add("issue_refund", {"ok": outcome["ok"], "reason": outcome["reason"]})
    if not outcome["ok"]:
        status = "failed" if outcome["conflict"] else "denied"
        return _finish(conn, claim_id, seed, status, proposal, budget, trace, outcome["reason"])

    # Step 7: success.
    return _finish(conn, claim_id, seed, "resolved", proposal, budget, trace)

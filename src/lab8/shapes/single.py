"""Shape B — one ReAct agent. Student work.

Use `lab8.runtime.run_react` with max_steps=8. `decide` may pick a read tool.
It must not call `issue_refund`. After the loop, the host validates the quote
and is the only writer.

A decide() that trusts ticket text over the order row will fail hidden claims
where the customer overstates the delay or cites a superseded clause.

Per-order cap: an order may already have been refunded by an earlier claim.
The read tool `lookup_refund_history` shows how much. The host still enforces
the cap, so pass the full quote to `durability.issue_refund`, not a net amount.

Caps: stop at 8 steps. Count model calls in the Budget so cost stays comparable.

Trace contract v1 (docs/contracts.md): return a trace_path to a JSON file written in this run,
{"run_id": <same run_id>, "events": [...]}, on every return path including early
ones. `lab8.trace.Trace` does this; your own tracer is fine if it matches.
"""

from __future__ import annotations

import sqlite3
from typing import Any

from lab8.db import connect
from lab8.durability import InjectedCrash, issue_refund
from lab8.mock_llm import complete
from lab8.runtime import run_react
from lab8.schemas import Budget, RunResult, make_run_id
from lab8.shapes.common import finish, safe_dump
from lab8.trace import Trace


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


def _run(
    conn: sqlite3.Connection,
    claim_id: str,
    *,
    seed: int,
    crash_at: str | None,
) -> RunResult:
    budget = Budget()
    run_id = make_run_id("single", claim_id, seed)
    trace = Trace(run_id)

    def decide(seen: dict[str, Any]) -> dict[str, Any]:
        last_tool = seen.get("last_tool")
        last_result = seen.get("last_result") or {}

        # Bước 1: Chưa gọi tool nào -> đọc thông tin claim (đã qua allowlist)
        if last_tool is None:
            return {"tool": "get_claim_view", "args": {"claim_id": claim_id}}

        # Bước 2: Sau khi có claim_view -> kiểm tra tồn tại & order_id
        if last_tool == "get_claim_view":
            trace.add(
                "tool",
                {
                    "name": "get_claim_view",
                    "found": last_result.get("found"),
                    "claim_id": last_result.get("claim_id"),
                    "order_id": last_result.get("order_id"),
                },
            )
            if not last_result.get("found"):
                return {
                    "final": {
                        "status": "failed",
                        "proposal_amount": 0,
                        "error_reason": "unknown_claim",
                    }
                }

            # Cho MockLLM đọc ticket để ghi nhận chi phí model, KHÔNG tin số ngày trễ trong ticket
            complete(budget, seed=seed, purpose="parse", prompt=last_result["ticket"])

            if not last_result.get("order_id"):
                complete(budget, seed=seed, purpose="draft", prompt="needs_info")
                return {
                    "final": {
                        "status": "needs_info",
                        "proposal_amount": 0,
                        "error_reason": "missing_order_id",
                    }
                }

            return {
                "tool": "lookup_order",
                "args": {
                    "order_id": last_result["order_id"],
                    "principal_id": last_result["principal_id"],
                },
            }

        # Bước 3: Sau khi lookup_order -> kiểm tra quyền sở hữu / tồn tại đơn
        if last_tool == "lookup_order":
            trace.add("tool", {"name": "lookup_order", "result": safe_dump(last_result)})
            if not last_result.get("visible"):
                complete(budget, seed=seed, purpose="draft", prompt="escalated")
                return {
                    "final": {
                        "status": "escalated",
                        "proposal_amount": 0,
                        "error_reason": last_result.get("reason"),
                    }
                }
            return {"tool": "compute_compensation", "args": {"order": last_result["order"]}}

        # Bước 4: Sau khi compute_compensation -> chốt proposal (full quote)
        if last_tool == "compute_compensation":
            trace.add("quote", safe_dump(last_result))
            proposal = int(last_result["amount_vnd"])
            complete(budget, seed=seed, purpose="draft", prompt=f"proposal={proposal}")
            return {
                "final": {
                    "status": "denied" if proposal <= 0 else "quoted",
                    "proposal_amount": proposal,
                    "error_reason": last_result.get("reason"),
                }
            }

        return {
            "final": {
                "status": "failed",
                "proposal_amount": 0,
                "error_reason": f"unexpected_tool:{last_tool}",
            }
        }

    react_out = run_react(
        conn,
        budget,
        observation={"claim_id": claim_id},
        decide=decide,
        max_steps=8,
    )
    final = react_out["final"]
    status = final["status"]
    proposal = int(final.get("proposal_amount", 0))
    error_reason = final.get("error_reason")

    # Nhánh không đủ điều kiện hoàn tiền hoặc lỗi sớm -> không gọi issue_refund
    if status in ("failed", "needs_info", "escalated") or proposal <= 0:
        out_status = "denied" if status == "quoted" and proposal <= 0 else status
        return finish(
            conn,
            shape="single",
            claim_id=claim_id,
            seed=seed,
            status=out_status,
            proposal_amount=0,
            budget=budget,
            trace=trace,
            error_reason=error_reason,
        )

    # Nhánh proposal > 0 -> gọi cửa host (kiểm approval, trần theo đơn, idempotency, crash)
    try:
        outcome = issue_refund(conn, claim_id, proposal, crash_at=crash_at)
    except InjectedCrash:
        trace.add("crash", {"at": crash_at})
        trace.write()
        raise

    if not outcome["ok"]:
        out_status = "failed" if outcome["conflict"] else "denied"
        return finish(
            conn,
            shape="single",
            claim_id=claim_id,
            seed=seed,
            status=out_status,
            proposal_amount=proposal,
            budget=budget,
            trace=trace,
            error_reason=outcome["reason"],
        )

    return finish(
        conn,
        shape="single",
        claim_id=claim_id,
        seed=seed,
        status="resolved",
        proposal_amount=proposal,
        budget=budget,
        trace=trace,
        error_reason=None,
    )

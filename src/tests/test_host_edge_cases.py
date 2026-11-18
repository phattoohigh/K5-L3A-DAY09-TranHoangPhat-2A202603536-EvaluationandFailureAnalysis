"""Host edge cases not covered by the starter gate.

Every case here goes straight through `durability.issue_refund`, so it checks the
host rules (approval, caps, idempotency, crash windows) independently of any shape.
Runs in the default gate: `python -m pytest -q`.
"""

from __future__ import annotations

import pytest

from lab8.db import connect
from lab8.durability import InjectedCrash, committed_audit_count, get_refund, issue_refund


def _add_order(conn, order_id, *, status="delivered_late", delay=4, fee=35000, paid=250000, damage=False,
               principal="P-100"):
    conn.execute(
        """
        INSERT INTO orders (order_id, principal_id, status, delay_days, shipping_fee_vnd, paid_vnd,
                            damage_verified, carrier, phone, address, internal_note, item_name)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'LOGIX_LOCAL', '0900000000', 'test addr', 'CANARY_INTERNAL_T', 'test item')
        """,
        (order_id, principal, status, delay, fee, paid, 1 if damage else 0),
    )


def _add_claim(conn, claim_id, order_id, approval_id, *, principal="P-100"):
    conn.execute(
        """
        INSERT INTO claims (claim_id, principal_id, order_id, ticket, parent_secret, raw_headers_json, approval_id)
        VALUES (?, ?, ?, 'test', 'CANARY_SECRET_PARENT_T', '{}', ?)
        """,
        (claim_id, principal, order_id, approval_id),
    )


def _add_approval(conn, approval_id, claim_id, amount, *, status="valid", expires="2027-12-31"):
    conn.execute(
        "INSERT INTO approvals (approval_id, claim_id, approved_vnd, status, expires_at) VALUES (?, ?, ?, ?, ?)",
        (approval_id, claim_id, amount, status, expires),
    )


def _events(conn, claim_id, event_type):
    rows = conn.execute(
        "SELECT details_json FROM audit_events WHERE claim_id = ? AND event_type = ?",
        (claim_id, event_type),
    ).fetchall()
    return [row["details_json"] for row in rows]


def _ledger_rows(conn, claim_id):
    return int(conn.execute("SELECT COUNT(*) AS n FROM refund_ledger WHERE claim_id = ?", (claim_id,)).fetchone()["n"])


# --- Approval gate -------------------------------------------------------------------------


def test_expired_approval_writes_nothing_and_audits_denial(public_db):
    conn = connect(public_db)
    outcome = issue_refund(conn, "C-007", 35000)  # A-007 expired 2020-01-01
    rows = _ledger_rows(conn, "C-007")
    denials = _events(conn, "C-007", "policy_denied")
    conn.close()
    assert outcome == {"ok": False, "reason": "approval_expired", "effect": None, "conflict": False}
    assert rows == 0
    assert any("approval_expired" in row for row in denials)


def test_claim_without_approval_is_denied(public_db):
    conn = connect(public_db)
    _add_claim(conn, "C-NOAPP", "O-909", None)
    conn.commit()
    outcome = issue_refund(conn, "C-NOAPP", 35000)
    rows = _ledger_rows(conn, "C-NOAPP")
    conn.close()
    assert outcome["reason"] == "missing_approval"
    assert rows == 0


def test_dangling_approval_id_is_denied(public_db):
    conn = connect(public_db)
    _add_claim(conn, "C-GHOST", "O-909", "A-DOES-NOT-EXIST")
    conn.commit()
    outcome = issue_refund(conn, "C-GHOST", 35000)
    conn.close()
    assert outcome["reason"] == "missing_approval"


@pytest.mark.parametrize("approval_status", ["revoked", "pending", "rejected"])
def test_non_valid_approval_status_is_denied(public_db, approval_status):
    conn = connect(public_db)
    _add_approval(conn, "A-ST", "C-ST", 35000, status=approval_status)
    _add_claim(conn, "C-ST", "O-909", "A-ST")
    conn.commit()
    outcome = issue_refund(conn, "C-ST", 35000)
    rows = _ledger_rows(conn, "C-ST")
    conn.close()
    assert outcome["reason"] == f"approval_{approval_status}"
    assert rows == 0


def test_zero_approval_amount_is_denied(public_db):
    conn = connect(public_db)
    _add_approval(conn, "A-ZERO", "C-ZERO", 0)
    _add_claim(conn, "C-ZERO", "O-909", "A-ZERO")
    conn.commit()
    outcome = issue_refund(conn, "C-ZERO", 35000)
    conn.close()
    assert outcome["reason"] == "non_positive_amount"


@pytest.mark.parametrize("proposal", [0, -35000])
def test_non_positive_proposal_never_writes(public_db, proposal):
    conn = connect(public_db)
    outcome = issue_refund(conn, "C-001", proposal)
    rows = _ledger_rows(conn, "C-001")
    conn.close()
    assert outcome["ok"] is False
    assert outcome["reason"] == "non_positive_amount"
    assert rows == 0


# --- Amount caps ---------------------------------------------------------------------------


def test_approval_below_quote_caps_the_ledger_amount(public_db):
    """T08 at host level: quote 35000, approval 20000 -> ledger 20000."""
    conn = connect(public_db)
    outcome = issue_refund(conn, "C-008", 35000)
    effect = get_refund(conn, "C-008")
    conn.close()
    assert outcome["ok"] is True
    assert int(effect["amount_vnd"]) == 20000


def test_paid_amount_caps_the_ledger_amount(public_db):
    conn = connect(public_db)
    _add_order(conn, "O-CHEAP", paid=12000, fee=35000)
    _add_approval(conn, "A-CHEAP", "C-CHEAP", 35000)
    _add_claim(conn, "C-CHEAP", "O-CHEAP", "A-CHEAP")
    conn.commit()
    outcome = issue_refund(conn, "C-CHEAP", 35000)
    effect = get_refund(conn, "C-CHEAP")
    conn.close()
    assert outcome["ok"] is True
    assert int(effect["amount_vnd"]) == 12000


def test_top_up_is_also_capped_by_approval(public_db):
    """Order already refunded 30000; new entitlement 150000; approval only 50000 -> pay 50000."""
    conn = connect(public_db)
    _add_approval(conn, "A-TOPUP", "C-TOPUP", 50000)
    _add_claim(conn, "C-TOPUP", "O-515", "A-TOPUP")
    conn.commit()
    outcome = issue_refund(conn, "C-TOPUP", 150000)
    effect = get_refund(conn, "C-TOPUP")
    conn.close()
    assert outcome["ok"] is True
    assert int(effect["amount_vnd"]) == 50000


def test_shape_that_subtracts_prior_refund_itself_underpays(public_db):
    """Why the shape must pass the FULL quote: a net amount gets subtracted twice (T14)."""
    conn = connect(public_db)
    outcome = issue_refund(conn, "C-014", 150000 - 30000)  # wrong: shape pre-subtracted
    effect = get_refund(conn, "C-014")
    conn.close()
    assert outcome["ok"] is True
    assert int(effect["amount_vnd"]) == 90000  # not the correct 120000


# --- Scope -----------------------------------------------------------------------------


def test_missing_order_is_denied_with_audit(public_db):
    conn = connect(public_db)
    outcome = issue_refund(conn, "C-004", 35000)  # order_id is null
    denials = _events(conn, "C-004", "policy_denied")
    conn.close()
    assert outcome["reason"] == "missing_order"
    assert any("missing_order" in row for row in denials)


def test_order_of_another_principal_is_denied(public_db):
    conn = connect(public_db)
    outcome = issue_refund(conn, "C-005", 40000)  # P-200 asking about P-300's O-110
    rows = _ledger_rows(conn, "C-005")
    conn.close()
    assert outcome["reason"] == "outside_principal_scope"
    assert rows == 0


def test_unknown_claim_is_rejected_without_audit(public_db):
    conn = connect(public_db)
    outcome = issue_refund(conn, "C-NOPE", 35000)
    audits = conn.execute("SELECT COUNT(*) AS n FROM audit_events WHERE claim_id = 'C-NOPE'").fetchone()["n"]
    conn.close()
    assert outcome["reason"] == "unknown_claim"
    assert audits == 0


# --- Idempotency and crash windows -------------------------------------------------------


def test_repeated_conflicts_keep_committed_amount_and_audit_once(public_db):
    conn = connect(public_db)
    issue_refund(conn, "C-001", 35000)
    first = issue_refund(conn, "C-001", 10000)
    second = issue_refund(conn, "C-001", 5000)
    effect = get_refund(conn, "C-001")
    conflicts = _events(conn, "C-001", "amount_conflict")
    committed = committed_audit_count(conn, "C-001")
    conn.close()
    assert first["conflict"] is True and second["conflict"] is True
    assert int(effect["amount_vnd"]) == 35000
    assert len(conflicts) == 1  # audit key is per claim
    assert committed == 1


def test_crash_before_effect_leaves_nothing_then_resume_pays_once(public_db):
    conn = connect(public_db)
    with pytest.raises(InjectedCrash):
        issue_refund(conn, "C-012", 35000, crash_at="before_effect")
    assert _ledger_rows(conn, "C-012") == 0
    assert committed_audit_count(conn, "C-012") == 0
    resumed = issue_refund(conn, "C-012", 35000)
    rows = _ledger_rows(conn, "C-012")
    audits = committed_audit_count(conn, "C-012")
    conn.close()
    assert resumed["reason"] == "committed"
    assert rows == 1
    assert audits == 1


def test_crash_after_checkpoint_resume_is_replay(public_db):
    conn = connect(public_db)
    with pytest.raises(InjectedCrash):
        issue_refund(conn, "C-012", 35000, crash_at="after_checkpoint")
    checkpoint = conn.execute("SELECT 1 FROM checkpoints WHERE claim_id = 'C-012'").fetchone()
    resumed = issue_refund(conn, "C-012", 35000)
    rows = _ledger_rows(conn, "C-012")
    audits = committed_audit_count(conn, "C-012")
    conn.close()
    assert checkpoint is not None
    assert resumed["reason"] == "idempotent_replay"
    assert rows == 1
    assert audits == 1


def test_resume_after_crash_on_a_fresh_connection_pays_once(public_db):
    """Real resume = new process = new connection to the same store."""
    conn = connect(public_db)
    with pytest.raises(InjectedCrash):
        issue_refund(conn, "C-012", 35000, crash_at="after_effect_before_checkpoint")
    conn.close()

    conn = connect(public_db)
    resumed = issue_refund(conn, "C-012", 35000)
    rows = _ledger_rows(conn, "C-012")
    audits = committed_audit_count(conn, "C-012")
    checkpoint = conn.execute("SELECT 1 FROM checkpoints WHERE claim_id = 'C-012'").fetchone()
    conn.close()
    assert resumed["reason"] == "idempotent_replay"
    assert rows == 1
    assert audits == 1
    assert checkpoint is not None  # replay repairs the missing checkpoint


def test_idempotency_key_is_unique_per_claim(public_db):
    conn = connect(public_db)
    issue_refund(conn, "C-001", 35000)
    issue_refund(conn, "C-008", 35000)
    keys = [row["idempotency_key"] for row in conn.execute(
        "SELECT idempotency_key FROM refund_ledger WHERE claim_id IN ('C-001', 'C-008') ORDER BY claim_id"
    )]
    conn.close()
    assert keys == ["refund:C-001", "refund:C-008"]

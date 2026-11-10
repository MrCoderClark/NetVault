from datetime import datetime, timezone

from netvault.security.audit import (
    GENESIS_HASH,
    AuditPayload,
    compute_event_hash,
    verify_chain,
)


def _payload(seq: int, action: str = "test.action") -> AuditPayload:
    return AuditPayload(
        tenant_seq=seq,
        occurred_at=datetime(2026, 1, 1, 12, 0, seq, tzinfo=timezone.utc),
        actor_type="user",
        actor_id="user-1",
        action=action,
        target_type="host",
        target_id=f"host-{seq}",
        before=None,
        after={"name": f"host-{seq}"},
        correlation_id=f"trace-{seq}",
    )


def _chain(length: int) -> list[tuple[AuditPayload, str, str]]:
    events: list[tuple[AuditPayload, str, str]] = []
    prev = GENESIS_HASH
    for index in range(1, length + 1):
        payload = _payload(index)
        current = compute_event_hash(payload, prev)
        events.append((payload, prev, current))
        prev = current
    return events


def test_compute_event_hash_is_deterministic() -> None:
    payload = _payload(1)
    assert compute_event_hash(payload, GENESIS_HASH) == compute_event_hash(payload, GENESIS_HASH)


def test_compute_event_hash_changes_with_payload() -> None:
    first = compute_event_hash(_payload(1, action="login"), GENESIS_HASH)
    second = compute_event_hash(_payload(1, action="logout"), GENESIS_HASH)
    assert first != second


def test_verify_chain_accepts_well_formed_sequence() -> None:
    ok, broken = verify_chain(_chain(4))
    assert ok is True
    assert broken is None


def test_verify_chain_detects_tampered_payload() -> None:
    chain = _chain(3)
    payload, prev_hash, event_hash = chain[1]
    tampered = AuditPayload(
        tenant_seq=payload.tenant_seq,
        occurred_at=payload.occurred_at,
        actor_type=payload.actor_type,
        actor_id="attacker",
        action=payload.action,
        target_type=payload.target_type,
        target_id=payload.target_id,
        before=payload.before,
        after=payload.after,
        correlation_id=payload.correlation_id,
    )
    chain[1] = (tampered, prev_hash, event_hash)
    ok, broken = verify_chain(chain)
    assert ok is False
    assert broken == 1


def test_verify_chain_detects_broken_prev_hash() -> None:
    chain = _chain(3)
    payload, _, event_hash = chain[2]
    chain[2] = (payload, "0" * 64, event_hash)
    ok, broken = verify_chain(chain)
    assert ok is False
    assert broken == 2


def test_verify_chain_detects_missing_row() -> None:
    chain = _chain(3)
    chain.pop(1)
    ok, broken = verify_chain(chain)
    assert ok is False
    assert broken == 1

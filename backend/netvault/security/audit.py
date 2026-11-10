"""Tenant-local, append-only audit hash chain.

Each audit event stores a canonical ``prev_hash`` and a derived ``event_hash``.
Verification walks the chain for a tenant in ascending ``tenant_seq`` order and
re-derives every hash; a missing, reordered, or edited row is detected.

This defeats casual tampering within the application database. It does not
defeat a privileged operator who can rewrite the chain in bulk; stronger
evidence requires periodic external anchoring (e.g. signed exports to
append-only storage) which is out of scope for this helper.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping

GENESIS_HASH = "0" * 64


@dataclass(frozen=True)
class AuditPayload:
    tenant_seq: int
    occurred_at: datetime
    actor_type: str
    actor_id: str | None
    action: str
    target_type: str | None
    target_id: str | None
    before: Mapping[str, Any] | None
    after: Mapping[str, Any] | None
    correlation_id: str | None


def compute_event_hash(payload: AuditPayload, prev_hash: str) -> str:
    """Hash a canonical JSON encoding of the payload together with ``prev_hash``."""
    canonical = json.dumps(
        {
            "tenant_seq": payload.tenant_seq,
            "occurred_at": payload.occurred_at.isoformat(),
            "actor_type": payload.actor_type,
            "actor_id": payload.actor_id,
            "action": payload.action,
            "target_type": payload.target_type,
            "target_id": payload.target_id,
            "before": payload.before,
            "after": payload.after,
            "correlation_id": payload.correlation_id,
            "prev_hash": prev_hash,
        },
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def verify_chain(
    events: list[tuple[AuditPayload, str, str]],
) -> tuple[bool, int | None]:
    """Verify an ordered chain of ``(payload, stored_prev_hash, stored_event_hash)``.

    Returns ``(True, None)`` when every row links to its predecessor and the
    stored hash matches what the payload implies. On the first discrepancy the
    function returns ``(False, index_of_broken_row)``.
    """
    expected_prev = GENESIS_HASH
    for index, (payload, stored_prev, stored_hash) in enumerate(events):
        expected_seq = index + 1
        if payload.tenant_seq != expected_seq:
            return False, index
        if stored_prev != expected_prev:
            return False, index
        if compute_event_hash(payload, stored_prev) != stored_hash:
            return False, index
        expected_prev = stored_hash
    return True, None

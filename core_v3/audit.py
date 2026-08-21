from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Iterable


@dataclass(frozen=True)
class AssessmentAudit:
    model_version: str
    policy_registry_version: str
    generated_at_utc: str
    input_sha256: str
    policy_rule_ids: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["policy_rule_ids"] = list(self.policy_rule_ids)
        return data


def canonical_input_digest(payload: Any) -> str:
    """Return a deterministic SHA-256 digest without echoing source data.

    This supports reproducibility/audit trails for potentially large or sensitive
    project inputs such as interval-load datasets. The digest does not substitute
    for retaining the source evidence document in an authorized project store.
    """
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def make_audit(*, model_version: str, policy_registry_version: str, input_payload: Any, policy_rule_ids: Iterable[str] = ()) -> AssessmentAudit:
    return AssessmentAudit(
        model_version=model_version,
        policy_registry_version=policy_registry_version,
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        input_sha256=canonical_input_digest(input_payload),
        policy_rule_ids=tuple(policy_rule_ids),
    )

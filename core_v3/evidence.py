from __future__ import annotations

from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


class EvidenceStatus(str, Enum):
    ENTERED = "entered"
    ESTIMATED = "estimated"
    BENCHMARK = "benchmark"
    VERIFIED = "verified"


@dataclass(frozen=True)
class EvidenceValue:
    value: Any
    unit: Optional[str] = None
    status: EvidenceStatus = EvidenceStatus.ENTERED
    source: Optional[str] = None
    source_url_or_document: Optional[str] = None
    effective_date: Optional[str] = None
    expiry_or_review_date: Optional[str] = None
    owner: Optional[str] = None
    last_updated_by: Optional[str] = None
    last_updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    notes: Optional[str] = None

    def validate(self) -> None:
        if self.status == EvidenceStatus.VERIFIED and not (self.source or self.source_url_or_document):
            raise ValueError("Verified evidence requires a source or source document.")
        for label, raw in (("effective_date", self.effective_date), ("expiry_or_review_date", self.expiry_or_review_date)):
            if raw:
                try:
                    datetime.fromisoformat(raw.replace("Z", "+00:00"))
                except ValueError as exc:
                    raise ValueError(f"{label} must be ISO-8601 compatible") from exc

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        data = asdict(self)
        data["status"] = self.status.value
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EvidenceValue":
        copy = dict(data)
        copy["status"] = EvidenceStatus(copy.get("status", EvidenceStatus.ENTERED.value))
        item = cls(**copy)
        item.validate()
        return item

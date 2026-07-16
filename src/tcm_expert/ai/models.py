from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class DoctorDecision(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EDITED = "edited"


@dataclass(frozen=True, slots=True)
class AIProposal:
    """Read-only reference result. It can never become a prescription."""

    consultation_id: int
    vietnamese_summary: str
    evidence: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    provider_trace: tuple[str, ...] = ()
    confidence: float = 0.0
    decision: DoctorDecision = DoctorDecision.PENDING
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "confidence", min(0.95, max(0.0, float(self.confidence))))
        forbidden = {"dose", "dosage", "prescription", "approved", "diagnosis"}
        if forbidden.intersection(self.metadata):
            raise ValueError("AI không được tạo chẩn đoán, đơn hoặc liều dùng.")

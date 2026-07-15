"""SQLite persistence layer."""

from tcm_expert.database.manager import DatabaseManager
from tcm_expert.database.repositories import (
    ConsultationRepository,
    PatientRepository,
    ReferenceRepository,
)
from tcm_expert.database.syndrome_repository import SyndromeRepository
from tcm_expert.database.validation import ValidationError

__all__ = [
    "ConsultationRepository",
    "DatabaseManager",
    "PatientRepository",
    "ReferenceRepository",
    "SyndromeRepository",
    "ValidationError",
]

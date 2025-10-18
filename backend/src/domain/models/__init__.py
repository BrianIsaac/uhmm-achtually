"""Domain models for the fact-checker."""

from src.domain.models.claim import Claim, ClaimExtractionResult
from src.domain.models.verdict import FactCheckVerdict

__all__ = ["Claim", "ClaimExtractionResult", "FactCheckVerdict"]

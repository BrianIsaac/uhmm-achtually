"""Pydantic models for claim extraction."""

from typing import Any, List, Literal, Optional
from pydantic import BaseModel, Field


class Claim(BaseModel):
    """Represents a single factual claim extracted from text."""

    text: str = Field(
        description="The factual claim text that can be verified"
    )
    claim_type: Any = Field(
        default="definition",  # Default to most common type
        description="Type of factual claim"
    )


class ClaimExtractionResult(BaseModel):
    """Result of claim extraction from a sentence."""

    claims: List[Claim] = Field(
        default_factory=list,
        description="List of extracted factual claims"
    )

    @property
    def has_claims(self) -> bool:
        """Check if any claims were extracted."""
        return len(self.claims) > 0

"""Pydantic models for claim extraction."""

from typing import List, Literal
from pydantic import BaseModel, Field


class Claim(BaseModel):
    """Represents a single factual claim extracted from text."""

    text: str = Field(
        description="The factual claim text that can be verified"
    )
    claim_type: Literal[
        "version",
        "api",
        "regulatory",
        "definition",
        "number",
        "decision"
    ] = Field(
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
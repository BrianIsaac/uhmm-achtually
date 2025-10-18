"""Pydantic models for fact-checking verdicts."""

from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator


class FactCheckVerdict(BaseModel):
    """Represents a fact-check verdict for a claim."""

    claim: str = Field(
        description="The original claim that was fact-checked"
    )
    status: Literal[
        "supported",
        "contradicted",
        "unclear",
        "not_found"
    ] = Field(
        description="Fact-check status"
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence score between 0 and 1"
    )
    rationale: str = Field(
        description="Brief explanation of the verdict"
    )
    evidence_url: Optional[str] = Field(
        default=None,
        description="URL to supporting evidence if available"
    )

    @field_validator('confidence')
    def validate_confidence(cls, v):
        """Ensure confidence is between 0 and 1."""
        if not 0 <= v <= 1:
            raise ValueError('confidence must be between 0 and 1')
        return v

    def to_app_message(self) -> dict:
        """Convert to format for Daily.co app message."""
        return {
            'type': 'fact-check-verdict',
            'claim': self.claim,
            'status': self.status,
            'confidence': self.confidence,
            'rationale': self.rationale,
            'evidence_url': self.evidence_url
        }
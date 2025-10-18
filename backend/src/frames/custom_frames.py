"""Custom Pipecat frames for claim extraction and verification.

Defines ClaimFrame and VerdictFrame used in the fact-checking pipeline.
"""

from dataclasses import dataclass
from pipecat.frames.frames import Frame


@dataclass
class ClaimFrame(Frame):
    """Frame containing an extracted factual claim.

    Attributes:
        text: The claim text
        claim_type: Type of claim (version, api, regulatory, definition, number, decision)
    """

    text: str
    claim_type: str


@dataclass
class VerdictFrame(Frame):
    """Frame containing a fact-check verdict.

    Attributes:
        claim: Original claim text
        status: Verdict status (supported, contradicted, unclear, not_found)
        confidence: Confidence score (0.0-1.0)
        rationale: Brief explanation of the verdict
        evidence_url: URL to supporting evidence (if available)
    """

    claim: str
    status: str
    confidence: float
    rationale: str
    evidence_url: str | None = None

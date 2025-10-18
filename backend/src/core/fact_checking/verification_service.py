"""Service for verifying factual claims."""

from typing import Optional
from loguru import logger

from src.processors.web_fact_checker import WebFactChecker
from src.models.claim_models import Claim
from src.models.verdict_models import FactCheckVerdict


class VerificationService:
    """
    Service for verifying factual claims.

    This service wraps the fact checker and provides a clean interface
    for the orchestrator.
    """

    def __init__(self, fact_checker: WebFactChecker):
        """
        Initialize the verification service.

        Args:
            fact_checker: The underlying fact checker
        """
        self.fact_checker = fact_checker

    async def verify_claim(self, claim: Claim) -> FactCheckVerdict:
        """
        Verify a factual claim.

        Args:
            claim: The claim to verify

        Returns:
            Verdict for the claim
        """
        try:
            verdict = await self.fact_checker.verify(claim)

            logger.info(
                f"Claim verified: {verdict.status}",
                extra={
                    "claim": claim.text,
                    "status": verdict.status,
                    "confidence": verdict.confidence
                }
            )

            return verdict

        except Exception as e:
            logger.error(f"Failed to verify claim '{claim.text}': {e}", exc_info=True)
            raise
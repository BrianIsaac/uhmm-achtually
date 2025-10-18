"""Service for verifying factual claims."""

from typing import Optional
from loguru import logger

from src.processors.web_fact_checker import WebFactChecker
from src.domain.models import Claim, FactCheckVerdict
from src.domain.exceptions import (
    VerificationError,
    EvidenceSearchError,
    ExaAPIError,
    GroqAPIError,
    TimeoutError
)


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

        except (ConnectionError, TimeoutError) as e:
            # Network-related errors
            logger.error(f"Network error during verification: {e}")
            raise EvidenceSearchError(
                "Failed to search for evidence",
                {"claim": claim.text, "error_type": type(e).__name__}
            )
        except ValueError as e:
            # Invalid response or parsing error
            logger.error(f"Invalid verification response: {e}")
            raise VerificationError(
                "Invalid response during verification",
                {"claim": claim.text, "error": str(e)}
            )
        except Exception as e:
            # Check if it's an API-specific error
            error_message = str(e).lower()

            if "exa" in error_message:
                logger.error(f"Exa API error during verification: {e}")
                raise ExaAPIError(
                    "Evidence search failed",
                    {"claim": claim.text, "error": str(e)}
                )
            elif "groq" in error_message:
                logger.error(f"Groq API error during verification: {e}")
                raise GroqAPIError(
                    "Verification analysis failed",
                    {"claim": claim.text, "error": str(e)}
                )
            else:
                # Generic verification error
                logger.error(f"Unexpected error verifying claim: {e}", exc_info=True)
                raise VerificationError(
                    "Failed to verify claim",
                    {"claim": claim.text, "error": str(e), "error_type": type(e).__name__}
                )
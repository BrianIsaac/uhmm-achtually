"""Service for extracting factual claims from text."""

from typing import List
from loguru import logger

from src.processors.claim_extractor import ClaimExtractor
from src.domain.models import Claim
from src.domain.exceptions import ClaimExtractionError, GroqAPIError


class ClaimExtractionService:
    """
    Service for extracting factual claims from text.

    This service wraps the claim extractor and provides a clean interface
    for the orchestrator.
    """

    def __init__(self, claim_extractor: ClaimExtractor):
        """
        Initialize the claim extraction service.

        Args:
            claim_extractor: The underlying claim extractor
        """
        self.claim_extractor = claim_extractor

    async def extract_claims(self, text: str) -> List[Claim]:
        """
        Extract factual claims from text.

        Args:
            text: The text to analyze

        Returns:
            List of extracted claims
        """
        if not text or not text.strip():
            return []

        try:
            claims = await self.claim_extractor.extract(text)

            if claims:
                logger.info(
                    f"Extracted {len(claims)} claim(s)",
                    extra={"text_length": len(text), "claim_count": len(claims)}
                )

            return claims

        except (ConnectionError, TimeoutError) as e:
            # Network-related errors from Groq API
            logger.error(f"Network error during claim extraction: {e}")
            raise GroqAPIError(
                "Failed to connect to Groq API",
                {"text_length": len(text), "error_type": type(e).__name__}
            )
        except KeyError as e:
            # Specific handling for KeyError to get better diagnostics
            logger.error(f"KeyError during claim extraction - missing key: {e!r}")
            logger.error("Full traceback:", exc_info=True)
            raise ClaimExtractionError(
                "Missing expected key in response",
                {"text_preview": text[:100], "missing_key": str(e), "error_type": "KeyError"}
            )
        except ValueError as e:
            # Invalid response or parsing error
            logger.error(f"Invalid response during claim extraction: {e}")
            raise ClaimExtractionError(
                "Invalid response from claim extractor",
                {"text_preview": text[:100], "error": str(e)}
            )
        except Exception as e:
            # Unexpected errors - log the repr for better error visibility
            logger.error(f"Unexpected error extracting claims: type={type(e).__name__}, error={e!r}")
            logger.error("Full traceback:", exc_info=True)
            raise ClaimExtractionError(
                "Failed to extract claims from text",
                {"text_length": len(text), "error": str(e), "error_type": type(e).__name__}
            )
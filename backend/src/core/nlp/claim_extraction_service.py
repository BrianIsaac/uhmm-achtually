"""Service for extracting factual claims from text."""

from typing import List
from loguru import logger

from src.processors.claim_extractor import ClaimExtractor
from src.models.claim_models import Claim


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

        except Exception as e:
            logger.error(f"Failed to extract claims from text: {e}", exc_info=True)
            raise
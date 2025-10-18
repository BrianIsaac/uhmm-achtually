"""ClaimExtractor using PydanticAI for intelligent claim extraction."""

import os
from typing import List

from loguru import logger
from pydantic_ai import Agent

from src.models.claim_models import Claim, ClaimExtractionResult
from src.utils.config import get_dev_config, get_prompts


class ClaimExtractor:
    """Extract factual claims using PydanticAI with Groq.

    This version uses PydanticAI for more reliable structured output
    and better error handling compared to raw JSON mode.
    """

    def __init__(self, groq_api_key: str):
        """Initialize the claim extractor with PydanticAI.

        Args:
            groq_api_key: Groq API key for LLM access
        """
        self._config = get_dev_config()
        self._prompts = get_prompts()

        # Set Groq API key in environment for PydanticAI
        os.environ["GROQ_API_KEY"] = groq_api_key

        # Create PydanticAI agent with Groq model string
        # Format: "groq:model-name"
        model_string = f"groq:{self._config.llm.claim_extraction_model}"

        self.agent = Agent(
            model=model_string,
            output_type=ClaimExtractionResult,
            instructions=self._prompts.claim_extraction["system_prompt"],
        )

        logger.info(
            f"[CLAIM_EXTRACTOR] Initialized with PydanticAI, model: {self._config.llm.claim_extraction_model}"
        )

    async def extract(self, sentence: str) -> List[Claim]:
        """Extract factual claims from a sentence.

        Args:
            sentence: The sentence to extract claims from

        Returns:
            List of extracted claims
        """
        logger.info(f"[CLAIM_EXTRACTOR] Extracting claims from: {sentence}")

        try:
            # Run the agent to extract claims
            result = await self.agent.run(sentence)

            # Get the structured output
            extraction_result = result.output

            if extraction_result.has_claims:
                logger.info(f"Extracted {len(extraction_result.claims)} claims")
                for claim in extraction_result.claims:
                    logger.info(f"  - {claim.text} ({claim.claim_type})")
            else:
                logger.info("No factual claims found in sentence")

            return extraction_result.claims

        except Exception as e:
            logger.error(f"Claim extraction failed: {e}", exc_info=True)
            # Return empty list on failure to keep pipeline running
            return []

    def extract_sync(self, sentence: str) -> List[Claim]:
        """Synchronous version of extract for testing.

        Args:
            sentence: The sentence to extract claims from

        Returns:
            List of extracted claims
        """
        logger.info(f"[SYNC] Extracting claims from: {sentence}")

        try:
            # Run the agent synchronously
            result = self.agent.run_sync(sentence)

            # Get the structured output
            extraction_result = result.output

            if extraction_result.has_claims:
                logger.info(f"[SYNC] Extracted {len(extraction_result.claims)} claims")
                for claim in extraction_result.claims:
                    logger.info(f"  - {claim.text} ({claim.claim_type})")
            else:
                logger.info("[SYNC] No factual claims found in sentence")

            return extraction_result.claims

        except Exception as e:
            logger.error(f"[SYNC] Claim extraction failed: {e}", exc_info=True)
            return []
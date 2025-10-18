"""WebFactChecker using PydanticAI for structured Groq output."""

import json
import os
import time
from typing import Dict, List, Literal, Optional

from loguru import logger
from pydantic import BaseModel, Field
from pydantic_ai import Agent

from src.models.claim_models import Claim
from src.models.verdict_models import FactCheckVerdict
from src.services.exa_client import ExaClient
from src.utils.config import get_dev_config, get_prompts


class VerificationResult(BaseModel):
    """Structured result from fact verification."""

    status: Literal["supported", "contradicted", "unclear", "not_found"] = Field(
        description="Verdict status: supported, contradicted, unclear, or not_found"
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence level between 0 and 1"
    )
    rationale: str = Field(
        description="1-2 sentence explanation of the verdict"
    )
    evidence_url: str = Field(
        default="",
        description="Most relevant source URL, or empty string if none"
    )


class WebFactChecker:
    """Verify claims using Exa web search and Groq with PydanticAI.

    This version uses PydanticAI for consistent structured output
    from Groq across the entire pipeline.
    """

    def __init__(
        self,
        groq_api_key: str,
        exa_api_key: str,
        allowed_domains: Optional[List[str]] = None,
    ):
        """Initialize the fact checker with PydanticAI.

        Args:
            groq_api_key: Groq API key
            exa_api_key: Exa API key for web search
            allowed_domains: Allowed domains for search (optional)
        """
        self._config = get_dev_config()
        self._prompts = get_prompts()

        # Initialize Exa client for web search
        self.exa_client = ExaClient(exa_api_key, allowed_domains or [])

        # Set Groq API key in environment for PydanticAI
        os.environ["GROQ_API_KEY"] = groq_api_key

        # Create PydanticAI agent with Groq model
        model_string = f"groq:{self._config.llm.verification_model}"

        self.verification_agent = Agent(
            model=model_string,
            output_type=VerificationResult,
            instructions=self._prompts.fact_verification["system_prompt"],
        )

        # In-memory cache for results
        self._cache: Dict[str, FactCheckVerdict] = {}

        logger.info(
            f"WebFactChecker initialized with PydanticAI and model: {self._config.llm.verification_model}"
        )

    async def verify(self, claim: Claim) -> FactCheckVerdict:
        """Verify a factual claim using web search and LLM.

        Args:
            claim: The claim to verify

        Returns:
            FactCheckVerdict with status, confidence, and rationale
        """
        claim_text = claim.text
        logger.info(f"Fact-checking: {claim_text}")

        # Check cache
        cache_key = f"claim:{claim_text}"
        if cache_key in self._cache:
            logger.info(f"Cache hit: {claim_text}")
            return self._cache[cache_key]

        try:
            # Measure search latency
            start_time = time.time()

            # Search for evidence with Exa
            results = await self.exa_client.search_for_claim(claim_text)

            exa_latency = (time.time() - start_time) * 1000
            logger.info(f"Exa search completed in {exa_latency:.0f}ms")
            logger.debug(f"Exa returned {len(results)} results")

            if not results:
                # No results found
                verdict = FactCheckVerdict(
                    claim=claim_text,
                    status="not_found",
                    confidence=0.0,
                    rationale="No relevant evidence found in trusted sources.",
                    evidence_url=None,
                )
            else:
                # Verify with Groq using PydanticAI
                verify_start = time.time()
                verdict = await self._verify_with_groq(claim_text, results)
                verify_latency = (time.time() - verify_start) * 1000
                logger.info(f"Groq verification completed in {verify_latency:.0f}ms")

            # Cache the result
            self._cache[cache_key] = verdict
            logger.info(
                f"Verdict for '{claim_text}': {verdict.status} "
                f"(confidence: {verdict.confidence:.2f})"
            )

            return verdict

        except Exception as e:
            logger.error(f"Fact-checking failed for '{claim_text}': {e}", exc_info=True)
            # Return a safe default verdict on error
            return FactCheckVerdict(
                claim=claim_text,
                status="unclear",
                confidence=0.0,
                rationale=f"Fact-checking failed: {str(e)}",
                evidence_url=None,
            )

    async def _verify_with_groq(
        self, claim_text: str, results: List
    ) -> FactCheckVerdict:
        """Verify claim using Groq LLM with PydanticAI.

        Args:
            claim_text: The claim to verify
            results: Search results from Exa

        Returns:
            FactCheckVerdict with structured output from Groq
        """
        # Format evidence passages
        # Handle different possible attribute names from Exa
        passages = []
        for r in results:
            try:
                # Check what attributes the result object has
                if hasattr(r, '__dict__'):
                    logger.debug(f"Result attributes: {list(r.__dict__.keys())}")

                passage = {
                    "title": getattr(r, 'title', ''),
                    "url": getattr(r, 'url', ''),
                    "text": getattr(r, 'text', getattr(r, 'content', ''))  # Try 'text' first, then 'content'
                }

                # If text is still empty, try to get any content
                if not passage["text"] and hasattr(r, '__dict__'):
                    # Look for any text-like field
                    for key in ['snippet', 'extract', 'body', 'description']:
                        if hasattr(r, key):
                            passage["text"] = getattr(r, key, '')
                            break

                passages.append(passage)
            except Exception as e:
                logger.error(f"Error processing result: {e}")
                logger.debug(f"Result type: {type(r)}, Result: {r}")

        if not passages:
            raise ValueError("No valid passages extracted from search results")

        passages = json.dumps(passages, indent=2)

        # Create the user prompt with claim and evidence
        user_prompt = self._prompts.fact_verification["user_prompt_template"].format(
            claim_text=claim_text,
            passages=passages
        )

        # Use PydanticAI agent to get structured verification
        result = await self.verification_agent.run(user_prompt)

        # Get the structured output
        verification = result.output

        # Convert to FactCheckVerdict
        verdict = FactCheckVerdict(
            claim=claim_text,
            status=verification.status,
            confidence=verification.confidence,
            rationale=verification.rationale,
            evidence_url=verification.evidence_url if verification.evidence_url else None,
        )

        return verdict

    def clear_cache(self):
        """Clear the verdict cache."""
        self._cache.clear()
        logger.info("Verdict cache cleared")

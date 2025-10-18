"""WebFactChecker using PydanticAI for structured Groq output."""

import json
import os
import time
from typing import Any, Dict, List, Literal, Optional

from loguru import logger
from pydantic import BaseModel, Field, ValidationError
from pydantic_ai import Agent

from src.domain.models import Claim, FactCheckVerdict
from src.services.exa_client import ExaClient
from src.infrastructure.config import get_dev_config, get_prompts


class VerificationResult(BaseModel):
    """Structured result from fact verification - loosened validation."""

    # Use Any type with defaults to handle unexpected responses
    status: Any = Field(
        default="unclear",
        description="Verdict status: supported, contradicted, unclear, or not_found"
    )
    confidence: Any = Field(
        default=0.0,
        description="Confidence level between 0 and 1"
    )
    rationale: Any = Field(
        default="Unable to verify",
        description="1-2 sentence explanation of the verdict"
    )
    evidence_url: Any = Field(
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

        except ValidationError as e:
            logger.error(f"Pydantic validation error during fact-checking for '{claim_text}': {e!r}")
            logger.error(f"Validation errors: {e.errors()}")
            logger.error(f"Full traceback:", exc_info=True)
            # Return a safe default verdict on validation error
            return FactCheckVerdict(
                claim=claim_text,
                status="unclear",
                confidence=0.0,
                rationale=f"Fact-checking failed: invalid response format",
                evidence_url=None,
            )
        except KeyError as e:
            logger.error(f"KeyError during fact-checking for '{claim_text}' - missing key: {e!r}")
            logger.error(f"Full traceback:", exc_info=True)
            # Return a safe default verdict on error
            return FactCheckVerdict(
                claim=claim_text,
                status="unclear",
                confidence=0.0,
                rationale=f"Fact-checking failed: missing expected data field",
                evidence_url=None,
            )
        except Exception as e:
            logger.error(f"Fact-checking failed for '{claim_text}': type={type(e).__name__}, error={e!r}")
            logger.error(f"Full traceback:", exc_info=True)
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
        try:
            result = await self.verification_agent.run(user_prompt)

            # Get the structured output - handle different result formats
            if hasattr(result, 'output'):
                verification = result.output
            elif hasattr(result, 'data'):
                verification = result.data
            else:
                # Log what we actually got
                logger.error(f"Unexpected result format from PydanticAI: {type(result)}")
                logger.error(f"Result attributes: {dir(result) if hasattr(result, '__dict__') else 'No attributes'}")
                raise ValueError(f"Unexpected result format from PydanticAI agent: {type(result)}")
        except ValidationError as e:
            logger.error(f"Pydantic validation error in PydanticAI verification: {e!r}")
            logger.error(f"Validation errors: {e.errors()}")
            logger.error(f"Full traceback:", exc_info=True)
            raise
        except KeyError as e:
            logger.error(f"KeyError in PydanticAI verification - missing key: {e!r}")
            logger.error(f"Full traceback:", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"PydanticAI verification failed: type={type(e).__name__}, error={e!r}")
            logger.error(f"Full traceback:", exc_info=True)
            raise

        # Convert to FactCheckVerdict - handle Any types safely
        # Normalize status to valid values
        status_str = str(verification.status).lower() if verification.status else "unclear"
        if status_str not in ["supported", "contradicted", "unclear", "not_found"]:
            logger.warning(f"Invalid status '{status_str}', defaulting to 'unclear'")
            status_str = "unclear"

        # Normalize confidence to float
        try:
            confidence_val = float(verification.confidence) if verification.confidence is not None else 0.0
            confidence_val = max(0.0, min(1.0, confidence_val))  # Clamp to [0, 1]
        except (ValueError, TypeError):
            logger.warning(f"Invalid confidence '{verification.confidence}', defaulting to 0.0")
            confidence_val = 0.0

        # Ensure rationale is string
        rationale_str = str(verification.rationale) if verification.rationale else "Unable to verify"

        # Handle evidence URL
        evidence_url_str = str(verification.evidence_url) if verification.evidence_url else None

        verdict = FactCheckVerdict(
            claim=claim_text,
            status=status_str,
            confidence=confidence_val,
            rationale=rationale_str,
            evidence_url=evidence_url_str,
        )

        return verdict

    def clear_cache(self):
        """Clear the verdict cache."""
        self._cache.clear()
        logger.info("Verdict cache cleared")

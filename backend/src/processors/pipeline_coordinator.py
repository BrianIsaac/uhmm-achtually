"""Pipeline coordinator for orchestrating the fact-checking pipeline."""

import asyncio
from typing import List, Optional

from loguru import logger
from pipecat.transports.daily.transport import DailyTransport

from src.domain.models import Claim, FactCheckVerdict
from src.processors.claim_extractor import ClaimExtractor
from src.processors.fact_check_messenger import FactCheckMessenger
from src.processors.web_fact_checker import WebFactChecker


class FactCheckPipeline:
    """Coordinates the entire fact-checking pipeline.

    This class orchestrates the flow from sentence to verdict broadcast,
    handling concurrency and error recovery.
    """

    def __init__(
        self,
        groq_api_key: str,
        exa_api_key: str,
        daily_transport: DailyTransport,
        allowed_domains: Optional[List[str]] = None,
    ):
        """Initialize the pipeline with all components.

        Args:
            groq_api_key: Groq API key for LLM operations
            exa_api_key: Exa API key for web search
            daily_transport: DailyTransport for broadcasting
            allowed_domains: Allowed domains for web search
        """
        self.claim_extractor = ClaimExtractor(groq_api_key)
        self.fact_checker = WebFactChecker(
            groq_api_key=groq_api_key,
            exa_api_key=exa_api_key,
            allowed_domains=allowed_domains,
        )
        self.messenger = FactCheckMessenger(daily_transport)

        # Metrics
        self.sentences_processed = 0
        self.claims_extracted = 0
        self.verdicts_generated = 0

        logger.info("FactCheckPipeline initialized with all components")

    async def process_sentence(self, sentence: str) -> List[FactCheckVerdict]:
        """Process a complete sentence through the entire pipeline.

        Args:
            sentence: The sentence to process

        Returns:
            List of verdicts generated for the sentence
        """
        logger.info(f"[PIPELINE] Processing sentence: {sentence}")
        self.sentences_processed += 1

        try:
            # Step 1: Extract claims from the sentence
            await self.messenger.broadcast_status(
                "extracting_claims",
                {"sentence": sentence},
            )

            claims = await self.claim_extractor.extract(sentence)
            self.claims_extracted += len(claims)

            if not claims:
                logger.info("No claims found in sentence")
                await self.messenger.broadcast_status(
                    "no_claims",
                    {"sentence": sentence},
                )
                return []

            logger.info(f"Extracted {len(claims)} claims from sentence")

            # Step 2: Fact-check each claim concurrently
            await self.messenger.broadcast_status(
                "fact_checking",
                {"num_claims": len(claims)},
            )

            # Create tasks for concurrent fact-checking
            fact_check_tasks = [
                self._fact_check_with_error_handling(claim) for claim in claims
            ]

            # Wait for all fact-checks to complete
            verdicts = await asyncio.gather(*fact_check_tasks, return_exceptions=False)

            # Filter out None values (failed fact-checks)
            valid_verdicts = [v for v in verdicts if v is not None]
            self.verdicts_generated += len(valid_verdicts)

            # Step 3: Broadcast all verdicts
            for verdict in valid_verdicts:
                await self.messenger.broadcast(verdict)

            logger.info(
                f"Pipeline completed: {len(valid_verdicts)}/{len(claims)} verdicts broadcast"
            )

            return valid_verdicts

        except Exception as e:
            logger.error(f"Pipeline failed for sentence: {e}", exc_info=True)
            await self.messenger.broadcast_error(
                f"Pipeline error: {str(e)}",
                claim=sentence,
            )
            return []

    async def _fact_check_with_error_handling(
        self, claim: Claim
    ) -> Optional[FactCheckVerdict]:
        """Fact-check a claim with error handling.

        Args:
            claim: The claim to fact-check

        Returns:
            FactCheckVerdict or None if failed
        """
        try:
            return await self.fact_checker.verify(claim)
        except Exception as e:
            logger.error(f"Fact-check failed for claim '{claim.text}': {e}")
            # Broadcast error for this specific claim
            await self.messenger.broadcast_error(
                f"Fact-check failed: {str(e)}",
                claim=claim.text,
            )
            return None

    async def process_batch(
        self, sentences: List[str], max_concurrent: int = 3
    ) -> List[List[FactCheckVerdict]]:
        """Process multiple sentences with concurrency control.

        Args:
            sentences: List of sentences to process
            max_concurrent: Maximum concurrent sentence processing

        Returns:
            List of verdict lists, one per sentence
        """
        logger.info(f"Processing batch of {len(sentences)} sentences")

        # Use semaphore to limit concurrency
        semaphore = asyncio.Semaphore(max_concurrent)

        async def process_with_semaphore(sentence: str):
            async with semaphore:
                return await self.process_sentence(sentence)

        # Process all sentences
        tasks = [process_with_semaphore(s) for s in sentences]
        results = await asyncio.gather(*tasks, return_exceptions=False)

        logger.info(f"Batch processing complete: {len(results)} sentences processed")
        return results

    def get_metrics(self) -> dict:
        """Get pipeline metrics.

        Returns:
            Dictionary of pipeline metrics
        """
        return {
            "sentences_processed": self.sentences_processed,
            "claims_extracted": self.claims_extracted,
            "verdicts_generated": self.verdicts_generated,
            "avg_claims_per_sentence": (
                self.claims_extracted / self.sentences_processed
                if self.sentences_processed > 0
                else 0
            ),
        }

    def reset_metrics(self):
        """Reset all pipeline metrics."""
        self.sentences_processed = 0
        self.claims_extracted = 0
        self.verdicts_generated = 0
        logger.info("Pipeline metrics reset")
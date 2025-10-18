"""Stage 4: ClaimExtractor processor.

Extract factual claims from sentences using Groq LLM with JSON mode.
"""

import asyncio
import json
import logging
from groq import Groq
from pipecat.frames.frames import Frame, TextFrame
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor

from src.frames.custom_frames import ClaimFrame
from src.utils.config import get_dev_config

logger = logging.getLogger(__name__)


class ClaimExtractor(FrameProcessor):
    """Extract factual claims from sentences using Groq JSON mode.

    Receives LLMMessagesFrame from SentenceAggregator and emits ClaimFrame
    for each extracted claim.
    """

    SYSTEM_PROMPT = """
        Extract factual claims from the sentence.
        Return a JSON object with an array of claims.
        Each claim should have 'text' and 'type' fields.
        Types: version, api, regulatory, definition, number, decision.
        Only extract verifiable factual statements, not opinions or questions.
        If no factual claims exist, return empty array.

        Example:
        {"claims": [{"text": "Python 3.12 removed distutils", "type": "version"}]}
    """

    def __init__(self, groq_api_key: str):
        """Initialise claim extractor.

        Args:
            groq_api_key: Groq API key for LLM access
        """
        super().__init__()
        self.groq_client = Groq(api_key=groq_api_key)
        self._config = get_dev_config()

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        """Extract claims from TextFrame.

        Args:
            frame: Incoming frame
            direction: Frame direction (upstream/downstream)
        """
        # DEBUG: Log ALL frames received to diagnose pipeline flow
        logger.warning(f"🔍 ClaimExtractor received frame: {type(frame).__name__}")

        # Only process TextFrame
        if isinstance(frame, TextFrame):
            sentence = frame.text
            logger.info(f"Extracting claims from: {sentence}")

            try:
                # Call Groq with JSON mode (async to avoid blocking)
                response = await asyncio.to_thread(
                    self.groq_client.chat.completions.create,
                    model=self._config.llm.claim_extraction_model,
                    messages=[
                        {"role": "system", "content": self.SYSTEM_PROMPT},
                        {"role": "user", "content": sentence}
                    ],
                    response_format={"type": "json_object"},
                    temperature=self._config.llm.temperature
                )

                # Parse response
                result = json.loads(response.choices[0].message.content)
                claims = result.get("claims", [])

                logger.info(f"Extracted {len(claims)} claims")

                # Emit ClaimFrame for each claim
                for claim in claims:
                    claim_frame = ClaimFrame(
                        text=claim["text"],
                        claim_type=claim["type"]
                    )
                    logger.info(f"Claim: {claim_frame.text} ({claim_frame.claim_type})")
                    await self.push_frame(claim_frame)

            except Exception as e:
                logger.error(f"Claim extraction failed: {e}", exc_info=True)

        # Always forward all frames to next processor (AFTER our processing)
        await super().process_frame(frame, direction)

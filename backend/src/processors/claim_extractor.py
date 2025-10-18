"""Stage 4: ClaimExtractor processor.

Extract factual claims from sentences using Groq LLM with JSON mode.
"""

import json
import logging
from groq import Groq
from pipecat.frames.frames import Frame, LLMMessagesFrame
from pipecat.processors.frame_processor import FrameProcessor

from src.frames.custom_frames import ClaimFrame

logger = logging.getLogger(__name__)


class ClaimExtractor(FrameProcessor):
    """Extract factual claims from sentences using Groq JSON mode.

    Receives LLMMessagesFrame from SentenceAggregator and emits ClaimFrame
    for each extracted claim.
    """

    SYSTEM_PROMPT = """Extract factual claims from the sentence.
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

    async def process_frame(self, frame: Frame, direction: str):
        """Extract claims from LLMMessagesFrame.

        Args:
            frame: Incoming frame
            direction: Frame direction (upstream/downstream)
        """
        await super().process_frame(frame, direction)

        if isinstance(frame, LLMMessagesFrame):
            sentence = frame.messages[0]["content"]
            logger.info(f"Extracting claims from: {sentence}")

            try:
                # Call Groq with JSON mode
                response = self.groq_client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[
                        {"role": "system", "content": self.SYSTEM_PROMPT},
                        {"role": "user", "content": sentence}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.1
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
                    await self.push_frame(claim_frame, direction)

            except Exception as e:
                logger.error(f"Claim extraction failed: {e}", exc_info=True)

        else:
            # Pass through other frames
            await self.push_frame(frame, direction)

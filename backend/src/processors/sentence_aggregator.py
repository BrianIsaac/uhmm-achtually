"""Stage 3: SentenceAggregator processor.

Buffers partial transcripts until sentence completion, then emits TextFrame.
"""

import re

from pipecat.frames.frames import Frame, TextFrame, TranscriptionFrame
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor

from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class SentenceAggregator(FrameProcessor):
    """Aggregate partial transcripts into complete sentences.

    Uses sentence boundary detection to gate downstream processing.
    Only emits TextFrame when sentence completes.
    """

    def __init__(self):
        """Initialise the sentence aggregator with empty buffer."""
        super().__init__()
        self._buffer = ""

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        """Process incoming frames and buffer transcriptions.

        Args:
            frame: Input frame from upstream processor
            direction: Frame direction (upstream/downstream)
        """
        # DEBUG: Log all incoming frames
        logger.debug(f"🔍 SentenceAggregator received: {type(frame).__name__}")
        
        # We only want to aggregate TranscriptionFrames
        if isinstance(frame, TranscriptionFrame):
            # Add to buffer
            self._buffer += " " + frame.text
            self._buffer = self._buffer.strip()

            logger.debug(f"Buffer: {self._buffer}")

            # Check if sentence is complete
            if self._is_sentence_complete(self._buffer):
                logger.info(f"Complete sentence detected: {self._buffer}")

                # Create TextFrame for downstream processing
                text_frame = TextFrame(text=self._buffer)

                # Clear buffer
                self._buffer = ""

                # Push TextFrame to next processor (PipelineBridge in V2)
                # Use super().process_frame() to forward the frame properly
                logger.info(f"📤 Pushing TextFrame to next processor: {text_frame.text}")
                await super().process_frame(text_frame, direction)
                logger.info(f"✅ TextFrame pushed successfully")

            # IMPORTANT: Consume the TranscriptionFrame
            # Return here so the original TranscriptionFrame is NOT forwarded
            return

        # Forward all other frames (like StartFrame, EndFrame, etc.) to next processor
        await super().process_frame(frame, direction)

    def _is_sentence_complete(self, text: str) -> bool:
        """Check for sentence-ending punctuation.

        Args:
            text: Text to check for sentence completion

        Returns:
            True if text ends with sentence-ending punctuation
        """
        return bool(re.search(r'[.!?]\s*$', text.strip()))

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
        # Only process TranscriptionFrame
        if isinstance(frame, TranscriptionFrame):
            # Add to buffer
            self._buffer += " " + frame.text
            self._buffer = self._buffer.strip()

            logger.debug(f"Buffer: {self._buffer}")

            # Check if sentence is complete
            if self._is_sentence_complete(self._buffer):
                logger.info(f"Complete sentence detected: {self._buffer}")

                # Emit TextFrame for downstream processing
                await self.push_frame(
                    TextFrame(text=self._buffer),
                    direction
                )

                # Clear buffer
                self._buffer = ""

        # Always forward all frames to next processor
        await super().process_frame(frame, direction)

    def _is_sentence_complete(self, text: str) -> bool:
        """Check for sentence-ending punctuation.

        Args:
            text: Text to check for sentence completion

        Returns:
            True if text ends with sentence-ending punctuation
        """
        return bool(re.search(r'[.!?]\s*$', text.strip()))

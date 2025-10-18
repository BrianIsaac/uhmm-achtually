"""Format VerdictFrame for TTS output.

Convert fact-check verdicts to natural speech for text-to-speech synthesis.
"""

import logging
from pipecat.frames.frames import Frame, TextFrame
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor

from src.frames.custom_frames import VerdictFrame

logger = logging.getLogger(__name__)


class VerdictFormatter(FrameProcessor):
    """Convert VerdictFrame to natural speech text for TTS.

    Receives VerdictFrame from WebFactChecker and emits TextFrame
    formatted for speech synthesis.
    """

    def __init__(self, verbose: bool = False):
        """Initialise formatter.

        Args:
            verbose: Include full rationale and evidence URL in speech
        """
        super().__init__()
        self.verbose = verbose

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        """Format verdicts as natural speech.

        Args:
            frame: Incoming frame
            direction: Frame direction (upstream/downstream)
        """
        if isinstance(frame, VerdictFrame):
            # Format based on status
            if frame.status == "supported":
                speech = f"Fact check: The claim {frame.claim} is supported."
            elif frame.status == "contradicted":
                speech = f"Fact check: The claim {frame.claim} is contradicted."
            elif frame.status == "unclear":
                speech = f"Fact check: The claim {frame.claim} is unclear."
            else:  # not_found
                speech = f"Fact check: No evidence found for {frame.claim}."

            # Add rationale if verbose
            if self.verbose and frame.rationale:
                speech += f" {frame.rationale}"

            logger.info(f"TTS output: {speech}")

            # Emit TextFrame for TTS
            await self.push_frame(TextFrame(text=speech), direction)

        # Forward all frames
        await super().process_frame(frame, direction)

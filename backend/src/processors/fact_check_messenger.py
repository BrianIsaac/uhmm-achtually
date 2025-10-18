"""Stage 6: FactCheckMessenger processor.

Broadcast verdicts via app messages to Vue.js frontend.
"""

import logging
from pipecat.frames.frames import Frame
from pipecat.processors.frame_processor import FrameProcessor
from pipecat.transports.daily.transport import DailyTransport

from src.frames.custom_frames import VerdictFrame

logger = logging.getLogger(__name__)


class FactCheckMessenger(FrameProcessor):
    """Send fact-check verdicts via app messages to custom Vue.js frontend.

    Uses DailyTransport.send_app_message() to broadcast structured JSON.
    Frontend receives via 'app-message' event listener.
    """

    def __init__(self, transport: DailyTransport, bot_name: str = "Fact Checker Bot"):
        """Initialise messenger.

        Args:
            transport: DailyTransport instance (reuses existing Daily context)
            bot_name: Bot display name
        """
        super().__init__()
        self.transport = transport
        self.bot_name = bot_name

    async def process_frame(self, frame: Frame, direction: str):
        """Broadcast verdicts via app messages.

        Args:
            frame: Incoming frame
            direction: Frame direction (upstream/downstream)
        """
        await super().process_frame(frame, direction)

        if isinstance(frame, VerdictFrame):
            # Format as JSON for frontend consumption
            message_data = {
                'type': 'fact-check-verdict',
                'claim': frame.claim,
                'status': frame.status,  # 'supported', 'contradicted', 'unclear', 'not_found'
                'confidence': frame.confidence,
                'rationale': frame.rationale,
                'evidence_url': frame.evidence_url
            }

            logger.info(f"Broadcasting verdict: {frame.claim} -> {frame.status}")

            try:
                # Broadcast to all participants using DailyTransport
                await self.transport.send_app_message(
                    message_data,
                    '*'  # Send to all participants
                )
            except Exception as e:
                logger.error(f"App message send failed: {e}")

        # Always pass through frame
        await self.push_frame(frame, direction)

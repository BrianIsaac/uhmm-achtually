"""FactCheckMessengerV2 for broadcasting verdicts to Daily.co participants."""

import logging
from typing import Optional
from pipecat.transports.daily.transport import DailyTransport

from src.models.verdict_models import FactCheckVerdict

logger = logging.getLogger(__name__)


class FactCheckMessengerV2:
    """Send fact-check verdicts via Daily.co app messages.

    This version works directly with Pydantic models instead of
    Pipecat frames, simplifying the broadcasting logic.
    """

    def __init__(
        self,
        transport: DailyTransport,
        bot_name: str = "Fact Checker Bot",
    ):
        """Initialize the messenger.

        Args:
            transport: DailyTransport instance for sending messages
            bot_name: Bot display name for messages
        """
        self.transport = transport
        self.bot_name = bot_name

        logger.info(f"FactCheckMessengerV2 initialized with bot name: {bot_name}")

    async def broadcast(
        self,
        verdict: FactCheckVerdict,
        participant_id: Optional[str] = None,
    ) -> bool:
        """Broadcast a fact-check verdict to participants.

        Args:
            verdict: The verdict to broadcast
            participant_id: Specific participant ID, or None for all

        Returns:
            True if broadcast succeeded, False otherwise
        """
        try:
            # Convert verdict to app message format
            message_data = verdict.to_app_message()

            # Add bot name to message
            message_data["bot_name"] = self.bot_name

            # Log the broadcast
            logger.info(
                f"Broadcasting verdict: {verdict.claim} -> {verdict.status} "
                f"(confidence: {verdict.confidence:.2f})"
            )

            # Send to specified participant or all
            recipient = participant_id or "*"

            # Use DailyTransport to send app message
            await self.transport.send_app_message(message_data, recipient)

            logger.debug(f"Verdict broadcast to: {recipient}")
            return True

        except Exception as e:
            logger.error(f"Failed to broadcast verdict: {e}", exc_info=True)
            return False

    async def broadcast_error(
        self,
        error_message: str,
        claim: Optional[str] = None,
        participant_id: Optional[str] = None,
    ) -> bool:
        """Broadcast an error message to participants.

        Args:
            error_message: The error message to send
            claim: The claim that caused the error (optional)
            participant_id: Specific participant ID, or None for all

        Returns:
            True if broadcast succeeded, False otherwise
        """
        try:
            message_data = {
                "type": "fact-check-error",
                "error": error_message,
                "claim": claim,
                "bot_name": self.bot_name,
            }

            logger.warning(f"Broadcasting error: {error_message}")

            recipient = participant_id or "*"
            await self.transport.send_app_message(message_data, recipient)

            return True

        except Exception as e:
            logger.error(f"Failed to broadcast error: {e}", exc_info=True)
            return False

    async def broadcast_status(
        self,
        status: str,
        details: Optional[dict] = None,
        participant_id: Optional[str] = None,
    ) -> bool:
        """Broadcast a status update to participants.

        Args:
            status: Status message (e.g., "processing", "ready")
            details: Additional details (optional)
            participant_id: Specific participant ID, or None for all

        Returns:
            True if broadcast succeeded, False otherwise
        """
        try:
            message_data = {
                "type": "fact-check-status",
                "status": status,
                "details": details or {},
                "bot_name": self.bot_name,
            }

            logger.info(f"Broadcasting status: {status}")

            recipient = participant_id or "*"
            await self.transport.send_app_message(message_data, recipient)

            return True

        except Exception as e:
            logger.error(f"Failed to broadcast status: {e}", exc_info=True)
            return False
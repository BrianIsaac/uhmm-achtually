"""Daily.co API client wrapper."""

from typing import Optional, Dict, Any
from loguru import logger

from src.domain.exceptions import ExternalServiceError


class DailyClient:
    """Client for interacting with Daily.co API."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Daily client.

        Args:
            api_key: Daily.co API key
        """
        self.api_key = api_key
        self._room_url: Optional[str] = None

    async def join_room(self, room_url: str, token: Optional[str] = None) -> bool:
        """
        Join a Daily.co room.

        Args:
            room_url: URL of the Daily.co room
            token: Optional meeting token

        Returns:
            True if joined successfully

        Raises:
            ExternalServiceError: If joining fails
        """
        try:
            # This would integrate with Daily.co SDK
            # For now, it's a placeholder
            self._room_url = room_url
            logger.info(f"Joined Daily.co room: {room_url}")
            return True

        except Exception as e:
            logger.error(f"Failed to join Daily.co room: {e}")
            raise ExternalServiceError(
                "Daily.co",
                "Failed to join room",
                {"room_url": room_url, "error": str(e)}
            )

    async def leave_room(self) -> bool:
        """
        Leave the current Daily.co room.

        Returns:
            True if left successfully
        """
        if self._room_url:
            logger.info(f"Left Daily.co room: {self._room_url}")
            self._room_url = None
        return True

    @property
    def is_connected(self) -> bool:
        """Check if connected to a room."""
        return self._room_url is not None
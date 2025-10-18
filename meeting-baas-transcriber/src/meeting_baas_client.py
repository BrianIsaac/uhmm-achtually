"""Client for Meeting BaaS API interactions."""

import httpx
from typing import Any
from .models import BotCreateRequest, BotCreateResponse
from .config import settings


class MeetingBaaSClient:
    """
    Client for interacting with Meeting BaaS API.

    Handles bot creation, status checks, and bot management.
    """

    BASE_URL = "https://api.meetingbaas.com"

    def __init__(self, api_key: str | None = None):
        """
        Initialise Meeting BaaS client.

        Args:
            api_key: Meeting BaaS API key (defaults to settings)
        """
        self.api_key = api_key or settings.meeting_baas_api_key
        self.headers = {
            "x-meeting-baas-api-key": self.api_key,
            "Content-Type": "application/json",
        }

    async def create_bot(
        self, meeting_url: str, webhook_url: str | None = None, **kwargs: Any
    ) -> BotCreateResponse:
        """
        Create a bot to join a Zoom/Teams/Meet meeting.

        Args:
            meeting_url: URL of the meeting to join
            webhook_url: Webhook endpoint to receive events
            **kwargs: Additional bot configuration options

        Returns:
            BotCreateResponse with bot_id and status

        Raises:
            httpx.HTTPError: If API request fails
        """
        # Construct bot creation payload
        payload = BotCreateRequest(
            meeting_url=meeting_url,
            bot_name=kwargs.get("bot_name", settings.bot_name),
            recording_mode=kwargs.get("recording_mode", "audio_only"),
            bot_image=kwargs.get("bot_image", settings.bot_image_url),
            entry_message=kwargs.get("entry_message", settings.entry_message),
            reserved=kwargs.get("reserved", False),
            speech_to_text=kwargs.get(
                "speech_to_text", {"provider": "Default"}
            ),
            automatic_leave=kwargs.get(
                "automatic_leave", {"waiting_room_timeout": 600}
            ),
        )

        # Add webhook URL if provided
        request_data = payload.model_dump(mode="json", exclude_none=True)
        if webhook_url:
            request_data["webhook_url"] = webhook_url

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.BASE_URL}/bots",
                json=request_data,
                headers=self.headers,
            )
            response.raise_for_status()
            data = response.json()

            return BotCreateResponse(**data)

    async def get_bot_status(self, bot_id: str) -> dict:
        """
        Get current status of a bot.

        Args:
            bot_id: Unique bot identifier

        Returns:
            Bot status information

        Raises:
            httpx.HTTPError: If API request fails
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.BASE_URL}/bots/{bot_id}",
                headers=self.headers,
            )
            response.raise_for_status()
            return response.json()

    async def stop_bot(self, bot_id: str) -> dict:
        """
        Stop a running bot and leave the meeting.

        Args:
            bot_id: Unique bot identifier

        Returns:
            Bot termination confirmation

        Raises:
            httpx.HTTPError: If API request fails
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.delete(
                f"{self.BASE_URL}/bots/{bot_id}",
                headers=self.headers,
            )
            response.raise_for_status()
            return response.json()

    async def list_bots(self) -> list[dict]:
        """
        List all active bots.

        Returns:
            List of bot information dictionaries

        Raises:
            httpx.HTTPError: If API request fails
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.BASE_URL}/bots",
                headers=self.headers,
            )
            response.raise_for_status()
            return response.json()

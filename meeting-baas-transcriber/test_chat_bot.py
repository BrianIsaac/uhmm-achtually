#!/usr/bin/env python3
"""
Simple test bot that joins a Zoom meeting and sends "hello" periodically.

This uses the Meeting BaaS Speaking Bots API to demonstrate basic bot interaction.

Usage:
    python test_chat_bot.py <meeting_url>

Example:
    python test_chat_bot.py https://zoom.us/j/123456789
"""

import sys
import asyncio
import httpx
from datetime import datetime
from src.config import settings


class SimpleChatBot:
    """
    Simple bot that joins meetings and sends periodic messages.

    Note: Meeting BaaS Speaking Bots API is primarily designed for AI conversations.
    For simple periodic messages, this uses a workaround with personas.
    """

    SPEAKING_API_URL = "https://speaking.meetingbaas.com/bots"

    def __init__(self, api_key: str | None = None):
        """
        Initialise chat bot.

        Args:
            api_key: Meeting BaaS API key
        """
        self.api_key = api_key or settings.meeting_baas_api_key

    async def create_simple_bot(
        self, meeting_url: str, message_interval: int = 5
    ) -> dict:
        """
        Create a bot that joins a meeting.

        Args:
            meeting_url: URL of the Zoom/Teams/Meet meeting
            message_interval: Seconds between messages (for reference only)

        Returns:
            Bot creation response

        Note:
            Meeting BaaS Speaking Bots are AI-powered conversation bots.
            They don't support simple scheduled message sending out of the box.

            For this test, we'll create a basic bot that joins and can be
            controlled via WebSocket (advanced feature).
        """
        payload = {
            "meeting_url": meeting_url,
            "personas": ["simple_greeter"],  # Custom persona
            "meeting_baas_api_key": self.api_key,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    self.SPEAKING_API_URL,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    print("\n⚠️  Speaking Bots API not available with your plan")
                    print("   This feature requires a Speaking Bots subscription")
                    print("\n💡 Alternative approaches:")
                    print("   1. Use the standard bot API (recording/transcription)")
                    print("   2. Upgrade to Speaking Bots plan at meetingbaas.com")
                    print("   3. Self-host Meeting BaaS with custom bot logic\n")
                    raise
                raise


async def test_simple_bot(meeting_url: str):
    """
    Test creating a simple bot that joins a meeting.

    Args:
        meeting_url: Zoom/Teams/Meet meeting URL
    """
    print("🤖 Testing Simple Chat Bot")
    print(f"📍 Meeting URL: {meeting_url}")
    print(f"⏱️  Will attempt to join meeting\n")

    bot = SimpleChatBot()

    try:
        print("Creating bot...")
        response = await bot.create_simple_bot(meeting_url, message_interval=5)

        print("\n✅ Bot created successfully!")
        print(f"   Response: {response}")
        print("\n📝 Note: Speaking Bots API is for AI conversation bots")
        print("   For simple scheduled messages, use a different approach")

        return response

    except httpx.HTTPStatusError as e:
        print(f"\n❌ API Error: {e}")
        print(f"   Status: {e.response.status_code}")
        print(f"   Response: {e.response.text}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        sys.exit(1)


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python test_chat_bot.py <meeting_url>")
        print("\nExample:")
        print("  python test_chat_bot.py https://zoom.us/j/123456789")
        print("\n⚠️  Important Note:")
        print("   Meeting BaaS Speaking Bots API is designed for AI conversations.")
        print("   For simple message scheduling, consider alternative approaches:")
        print("   1. Standard bot API with webhook-based message sending")
        print("   2. Self-hosted Meeting BaaS with custom logic")
        print("   3. Direct Zoom/Teams bot development")
        sys.exit(1)

    meeting_url = sys.argv[1]
    asyncio.run(test_simple_bot(meeting_url))


if __name__ == "__main__":
    main()

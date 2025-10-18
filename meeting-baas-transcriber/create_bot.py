#!/usr/bin/env python3
"""
Minimal script to create a Meeting BaaS bot for Zoom transcription.

Usage:
    python create_bot.py <meeting_url>

Example:
    python create_bot.py https://zoom.us/j/123456789
"""

import sys
import asyncio
from src.meeting_baas_client import MeetingBaaSClient
from src.config import settings


async def create_transcription_bot(meeting_url: str, webhook_url: str | None = None):
    """
    Create a bot to transcribe a Zoom meeting.

    Args:
        meeting_url: URL of the Zoom meeting to join
        webhook_url: Webhook endpoint to receive events (optional)
    """
    print("🤖 Creating Meeting BaaS bot...")
    print(f"📍 Meeting URL: {meeting_url}")

    if webhook_url:
        print(f"🔗 Webhook URL: {webhook_url}")
    else:
        print("⚠️  No webhook URL provided - you won't receive real-time events")

    # Initialise client
    client = MeetingBaaSClient()

    try:
        # Create bot
        response = await client.create_bot(
            meeting_url=meeting_url,
            webhook_url=webhook_url,
            bot_name=settings.bot_name,
            recording_mode="audio_only",
            entry_message=settings.entry_message,
        )

        print("\n✅ Bot created successfully!")
        print(f"   Bot ID: {response.bot_id}")
        print(f"   Status: {response.status}")
        print(f"   Meeting URL: {response.meeting_url}")

        print("\n📝 Next steps:")
        print("   1. The bot will join the meeting shortly")
        print("   2. Transcription will begin automatically")

        if webhook_url:
            print("   3. Transcript will be sent to your webhook when meeting ends")
        else:
            print(
                "   3. Check bot status with: python check_bot.py " + response.bot_id
            )

        return response.bot_id

    except Exception as e:
        print(f"\n❌ Error creating bot: {str(e)}")
        sys.exit(1)


def main():
    """Main entry point for CLI."""
    if len(sys.argv) < 2:
        print("Usage: python create_bot.py <meeting_url> [webhook_url]")
        print("\nExample:")
        print("  python create_bot.py https://zoom.us/j/123456789")
        print(
            "  python create_bot.py https://zoom.us/j/123456789 http://localhost:8000/webhooks/meetingbaas"
        )
        sys.exit(1)

    meeting_url = sys.argv[1]
    webhook_url = sys.argv[2] if len(sys.argv) > 2 else None

    # Run async function
    asyncio.run(create_transcription_bot(meeting_url, webhook_url))


if __name__ == "__main__":
    main()

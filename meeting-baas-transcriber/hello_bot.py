#!/usr/bin/env python3
"""
Simple bot that joins a Zoom meeting and demonstrates presence.

Since Meeting BaaS bot API doesn't directly support sending chat messages
(that's in the Speaking Bots API for AI conversations), this script:

1. Creates a bot that joins the meeting
2. Monitors bot status
3. Demonstrates how you would integrate custom messaging

For actual chat messages every 5 seconds, you would need to either:
- Use Meeting BaaS Speaking Bots API (requires subscription)
- Self-host Meeting BaaS with custom bot logic
- Use Zoom's native bot SDK

This script shows the framework for the first approach.

Usage:
    python hello_bot.py <meeting_url>

Example:
    python hello_bot.py https://zoom.us/j/123456789
"""

import sys
import asyncio
from datetime import datetime
from src.meeting_baas_client import MeetingBaaSClient
from src.config import settings


async def create_test_bot(meeting_url: str):
    """
    Create a bot that joins the meeting for testing.

    Args:
        meeting_url: Zoom/Teams/Meet meeting URL
    """
    print("=" * 80)
    print("🤖 SIMPLE MEETING BOT TEST")
    print("=" * 80)
    print(f"\n📍 Meeting URL: {meeting_url}")
    print(f"🤖 Bot Name: {settings.bot_name}")
    print(f"💬 Entry Message: {settings.entry_message}\n")

    client = MeetingBaaSClient()

    try:
        # Create bot with custom entry message
        print("Creating bot...")
        response = await client.create_bot(
            meeting_url=meeting_url,
            bot_name="Hello Bot",
            entry_message="👋 Hello! I'm a test bot. I'll be monitoring this meeting.",
            recording_mode="audio_only",
        )

        print("\n✅ Bot created successfully!")
        print(f"   Bot ID: {response.bot_id}")
        print(f"   Status: {response.status}")
        print(f"   Meeting URL: {response.meeting_url}\n")

        print("=" * 80)
        print("📊 MONITORING BOT STATUS")
        print("=" * 80)
        print("\nThe bot will now join the meeting. Checking status every 5 seconds...")
        print("Press Ctrl+C to stop monitoring\n")

        # Monitor bot status every 5 seconds
        await monitor_bot_status(client, response.bot_id, interval=5)

    except KeyboardInterrupt:
        print("\n\n🛑 Monitoring stopped by user")
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        sys.exit(1)


async def monitor_bot_status(
    client: MeetingBaaSClient, bot_id: str, interval: int = 5
):
    """
    Monitor bot status and display updates every N seconds.

    Args:
        client: Meeting BaaS client
        bot_id: Bot identifier
        interval: Seconds between status checks
    """
    iteration = 0

    while True:
        try:
            iteration += 1
            timestamp = datetime.now().strftime("%H:%M:%S")

            # Get bot status
            status = await client.get_bot_status(bot_id)

            # Display status
            bot_status = status.get("status", "unknown")
            print(f"[{timestamp}] Check #{iteration}: Bot status = {bot_status}")

            # Show additional info based on status
            if bot_status == "in_call":
                if iteration == 1:
                    print("   ✅ Bot successfully joined the meeting!")
                    print("   👀 Check your Zoom meeting - you should see 'Hello Bot' as a participant")

            elif bot_status == "joining":
                print("   ⏳ Bot is joining the meeting...")

            elif bot_status == "waiting_room":
                print("   🚪 Bot is in the waiting room - admit it manually in Zoom")

            elif bot_status == "completed":
                print("   🎬 Meeting ended - bot has left")
                print("\n💡 Bot lifecycle complete!")
                break

            elif bot_status == "failed":
                error = status.get("error", "Unknown error")
                print(f"   ❌ Bot failed: {error}")
                break

            # Wait before next check
            await asyncio.sleep(interval)

        except Exception as e:
            print(f"   ⚠️  Error checking status: {str(e)}")
            await asyncio.sleep(interval)


def print_usage_notes():
    """Print usage notes about Meeting BaaS capabilities."""
    print("\n" + "=" * 80)
    print("📝 ABOUT SENDING MESSAGES IN MEETINGS")
    print("=" * 80)
    print("""
This script demonstrates bot presence in meetings using Meeting BaaS.

CURRENT LIMITATIONS:
- The standard Bot API (recording/transcription) doesn't support sending chat
- Chat messages require the Speaking Bots API (AI conversation bots)

TO SEND PERIODIC MESSAGES (like "hello" every 5 seconds):

Option 1: Meeting BaaS Speaking Bots API (Recommended)
   - Supports AI-powered conversation bots
   - Can send messages and speak in meetings
   - Requires Speaking Bots subscription
   - See: https://www.meetingbaas.com/en/projects/speaking-bots

Option 2: Self-Host Meeting BaaS (Advanced)
   - Fork: https://github.com/Meeting-Baas/meeting-bot-as-a-service
   - Add custom bot logic for periodic messages
   - Full control over bot behavior
   - Free (except server costs)

Option 3: Use Zoom/Teams Native Bot SDK
   - Develop using Zoom's official bot framework
   - More complex setup
   - Platform-specific (separate for each platform)

THIS SCRIPT SHOWS:
- Bot joining meetings ✓
- Bot presence monitoring ✓
- Entry message when joining ✓
- Status tracking ✓

For your use case (sending "hello" every 5 seconds), Option 1 or 2 would work best.
""")
    print("=" * 80)


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python hello_bot.py <meeting_url>")
        print("\nExample:")
        print("  python hello_bot.py https://zoom.us/j/123456789")
        print("\nThis creates a bot that:")
        print("  1. Joins the meeting")
        print("  2. Sends an entry message")
        print("  3. Monitors its status every 5 seconds")
        print("\nNote: For sending periodic chat messages, see notes at end of execution")
        sys.exit(1)

    meeting_url = sys.argv[1]

    # Run the bot
    asyncio.run(create_test_bot(meeting_url))

    # Print usage notes after completion
    print_usage_notes()


if __name__ == "__main__":
    main()

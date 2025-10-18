#!/usr/bin/env python3
"""
Check status of a Meeting BaaS bot.

Usage:
    python check_bot.py <bot_id>

Example:
    python check_bot.py abc123def456
"""

import sys
import asyncio
import json
from src.meeting_baas_client import MeetingBaaSClient


async def check_bot_status(bot_id: str):
    """
    Check the status of a bot.

    Args:
        bot_id: Unique bot identifier
    """
    print(f"🔍 Checking status for bot: {bot_id}\n")

    client = MeetingBaaSClient()

    try:
        status = await client.get_bot_status(bot_id)

        print("📊 Bot Status:")
        print(json.dumps(status, indent=2))

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        sys.exit(1)


def main():
    """Main entry point for CLI."""
    if len(sys.argv) < 2:
        print("Usage: python check_bot.py <bot_id>")
        print("\nExample:")
        print("  python check_bot.py abc123def456")
        sys.exit(1)

    bot_id = sys.argv[1]
    asyncio.run(check_bot_status(bot_id))


if __name__ == "__main__":
    main()

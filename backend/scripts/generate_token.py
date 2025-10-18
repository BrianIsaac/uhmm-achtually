"""Generate a Daily.co meeting token for the bot."""

import os
import sys
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def generate_bot_token():
    """Generate a meeting token for the bot to join the Daily room.

    Returns:
        str: The generated meeting token
    """
    daily_api_key = os.getenv("DAILY_API_KEY")
    daily_room_url = os.getenv("DAILY_ROOM_URL")

    if not daily_api_key:
        print("Error: DAILY_API_KEY not found in .env file")
        sys.exit(1)

    if not daily_room_url:
        print("Error: DAILY_ROOM_URL not found in .env file")
        sys.exit(1)

    # Extract room name from URL
    room_name = daily_room_url.split("/")[-1]

    # Generate token
    url = "https://api.daily.co/v1/meeting-tokens"
    headers = {
        "Authorization": f"Bearer {daily_api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "properties": {
            "room_name": room_name,
            "is_owner": True
        }
    }

    response = requests.post(url, headers=headers, json=data)

    if response.status_code == 200:
        token = response.json()["token"]
        print(f"\nGenerated bot token:")
        print(f"\n{token}\n")
        print(f"\nAdd this to your .env file:")
        print(f"DAILY_BOT_TOKEN={token}\n")
        return token
    else:
        print(f"Error generating token: {response.status_code}")
        print(response.text)
        sys.exit(1)


if __name__ == "__main__":
    generate_bot_token()

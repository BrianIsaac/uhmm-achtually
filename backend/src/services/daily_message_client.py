"""Daily CallClient setup for app messages.

Creates a separate CallClient instance for broadcasting app messages
to the Vue.js frontend.
"""

from daily import CallClient, Daily


async def create_message_client(room_url: str, token: str | None = None) -> CallClient:
    """Create and join CallClient for app messages.

    Args:
        room_url: Daily room URL
        token: Daily bot token (optional for public rooms)

    Returns:
        Connected CallClient instance
    """
    Daily.init()
    client = CallClient()

    # Join room with token if provided
    if token:
        await client.join(
            url=room_url,
            client_settings={"token": token}
        )
    else:
        await client.join(url=room_url)

    return client

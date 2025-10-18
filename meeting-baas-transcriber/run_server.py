#!/usr/bin/env python3
"""
Run the webhook server with optional ngrok tunnel for local development.

Usage:
    python run_server.py [--ngrok]

Examples:
    python run_server.py              # Run server on localhost
    python run_server.py --ngrok      # Run server with ngrok tunnel
"""

import sys
import asyncio
import uvicorn
from src.config import settings


def run_with_ngrok():
    """Run server with ngrok tunnel for webhook testing."""
    try:
        from pyngrok import ngrok, conf
    except ImportError:
        print("❌ pyngrok not installed. Install with: uv pip install pyngrok")
        sys.exit(1)

    # Set auth token if provided
    if settings.ngrok_auth_token:
        conf.get_default().auth_token = settings.ngrok_auth_token
        print("✅ Ngrok auth token configured")

    # Start ngrok tunnel
    print(f"🚇 Starting ngrok tunnel on port {settings.port}...")
    public_url = ngrok.connect(settings.port, bind_tls=True)
    webhook_url = f"{public_url}/webhooks/meetingbaas"

    print("\n" + "=" * 80)
    print("✅ Ngrok tunnel active!")
    print("=" * 80)
    print(f"📍 Public URL: {public_url}")
    print(f"🔗 Webhook URL: {webhook_url}")
    print("\n💡 Use this webhook URL when creating bots:")
    print(f"   python create_bot.py <meeting_url> {webhook_url}")
    print("=" * 80 + "\n")

    # Run server
    uvicorn.run(
        "src.webhook_server:app",
        host=settings.host,
        port=settings.port,
        log_level="info",
    )


def run_local():
    """Run server on localhost without ngrok."""
    webhook_url = f"http://localhost:{settings.port}/webhooks/meetingbaas"

    print("\n" + "=" * 80)
    print("🚀 Starting webhook server (localhost only)")
    print("=" * 80)
    print(f"📍 Server URL: http://localhost:{settings.port}")
    print(f"🔗 Webhook endpoint: {webhook_url}")
    print("\n⚠️  This webhook URL only works locally!")
    print("   Use --ngrok flag for public webhook URL")
    print("=" * 80 + "\n")

    uvicorn.run(
        "src.webhook_server:app",
        host=settings.host,
        port=settings.port,
        log_level="info",
        reload=True,
    )


def main():
    """Main entry point."""
    use_ngrok = "--ngrok" in sys.argv

    if use_ngrok:
        run_with_ngrok()
    else:
        run_local()


if __name__ == "__main__":
    main()

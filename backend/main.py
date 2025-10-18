#!/usr/bin/env python3
"""Main entry point for the WebSocket server."""

import sys
from pathlib import Path

# Add backend directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from fastapi import WebSocket, Request
from dotenv import load_dotenv
from loguru import logger

from src.api.websocket.server import WebSocketServer
from src.api.http.endpoints import router as api_router


def create_application() -> tuple:
    """
    Factory function to create the application.

    Returns:
        Tuple of (app, ws_server) instances
    """
    # Load environment variables
    load_dotenv()

    # Create server instance
    ws_server = WebSocketServer()

    # Create FastAPI app
    app = ws_server.create_app()

    # Include API routes
    app.include_router(api_router)

    # Add WebSocket endpoint using app state
    @app.websocket("/")
    async def websocket_endpoint(websocket: WebSocket):
        """
        Main WebSocket endpoint for fact-checking.

        This endpoint handles WebSocket connections from Chrome extensions
        and other clients for real-time fact-checking.
        """
        # Get server from app state (set in WebSocketServer.create_app())
        server = app.state.ws_server

        if not server.websocket_handler:
            logger.error("WebSocket handler not initialized")
            await websocket.close(code=1011, reason="Server error")
            return

        await server.websocket_handler.handle_connection(websocket)

    return app, ws_server


# Create the application
app, _ws_server = create_application()


if __name__ == "__main__":
    import uvicorn

    logger.info("Starting WebSocket server on http://localhost:8765")

    uvicorn.run(
        "main:app",
        host="localhost",
        port=8765,
        reload=True,
        log_level="info"
    )
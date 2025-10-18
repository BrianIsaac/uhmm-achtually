"""WebSocket request handlers."""

import json
from typing import Dict, Any, Optional
from fastapi import WebSocket, WebSocketDisconnect
from loguru import logger

from src.api.websocket.connection_manager import ConnectionManager
from src.api.websocket.messages import MessageFactory
from src.core.fact_checking.orchestrator import FactCheckingOrchestrator


class WebSocketHandler:
    """Handles WebSocket connections and messages."""

    def __init__(
        self,
        connection_manager: ConnectionManager,
        orchestrator: Optional[FactCheckingOrchestrator] = None
    ):
        """
        Initialize the WebSocket handler.

        Args:
            connection_manager: Manager for WebSocket connections
            orchestrator: Fact-checking orchestrator
        """
        self.connection_manager = connection_manager
        self.orchestrator = orchestrator
        self.message_factory = MessageFactory()

    async def handle_connection(self, websocket: WebSocket) -> None:
        """
        Handle a WebSocket connection.

        Args:
            websocket: The WebSocket connection to handle
        """
        # Accept and register connection
        await self.connection_manager.connect(websocket)

        # Send connection acknowledgment
        connection_message = self.message_factory.create_connection_message(
            action="connected",
            message="Successfully connected to fact-checker backend"
        )
        await self.connection_manager.send_personal_message(websocket, connection_message)

        try:
            await self._handle_messages(websocket)
        except WebSocketDisconnect:
            logger.info("Client disconnected normally")
        except Exception as e:
            logger.error(f"WebSocket error: {e}", exc_info=True)
        finally:
            self.connection_manager.disconnect(websocket)

    async def _handle_messages(self, websocket: WebSocket) -> None:
        """
        Handle incoming messages from a WebSocket client.

        Args:
            websocket: The WebSocket connection
        """
        while True:
            try:
                data = await websocket.receive_json()
                await self._process_client_message(websocket, data)

            except WebSocketDisconnect:
                raise
            except json.JSONDecodeError as e:
                logger.warning(f"Received invalid JSON from client: {e}")

                error_message = self.message_factory.create_error_message(
                    error="Invalid JSON format",
                    details={"error": str(e)}
                )
                await self.connection_manager.send_personal_message(websocket, error_message)

            except Exception as e:
                logger.error(f"Error handling client message: {e}", exc_info=True)

                error_message = self.message_factory.create_error_message(
                    error="Failed to process message",
                    details={"error": str(e)}
                )
                await self.connection_manager.send_personal_message(websocket, error_message)

    async def _process_client_message(self, websocket: WebSocket, data: Dict[str, Any]) -> None:
        """
        Process a message from a client.

        Args:
            websocket: The client's WebSocket connection
            data: The received message data
        """
        message_type = data.get("type")

        if message_type == "connection":
            await self._handle_client_hello(websocket, data)

        elif message_type == "test_transcript":
            await self._handle_test_transcript(data)

        elif message_type == "ping":
            await self._handle_ping(websocket)

        else:
            logger.warning(f"Unknown message type: {message_type}")

    async def _handle_client_hello(self, websocket: WebSocket, data: Dict[str, Any]) -> None:
        """
        Handle client hello message.

        Args:
            websocket: The client's WebSocket connection
            data: The hello message data
        """
        client_info = {
            "client_id": data.get("client_id"),
            "platform": data.get("platform"),
            "version": data.get("version")
        }

        logger.info(f"Client hello received: {client_info}")

        # Store client metadata
        metadata = self.connection_manager.get_connection_metadata(websocket)
        metadata.update(client_info)

    async def _handle_test_transcript(self, data: Dict[str, Any]) -> None:
        """
        Handle test transcript submission.

        Args:
            data: The test transcript data
        """
        if not self.orchestrator:
            logger.warning("Cannot process transcript: orchestrator not initialized")

            error_message = self.message_factory.create_error_message(
                error="Service not initialized"
            )
            await self.connection_manager.broadcast(error_message)
            return

        text = data.get("text", "")
        speaker = data.get("speaker", "Test User")

        if text:
            logger.info(f"Processing test transcript: {text[:50]}...")
            await self.orchestrator.process_transcription(text, speaker)

    async def _handle_ping(self, websocket: WebSocket) -> None:
        """
        Handle ping message.

        Args:
            websocket: The client's WebSocket connection
        """
        pong_message = {"type": "pong", "timestamp": MessageFactory.create_timestamp()}
        await self.connection_manager.send_personal_message(websocket, pong_message)
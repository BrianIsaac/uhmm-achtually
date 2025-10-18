"""WebSocket connection management."""

import asyncio
from typing import Set, Dict, Any, List
from fastapi import WebSocket
from loguru import logger


class ConnectionManager:
    """Manages WebSocket connections and message broadcasting."""

    def __init__(self):
        self._active_connections: Set[WebSocket] = set()
        self._connection_metadata: Dict[WebSocket, Dict[str, Any]] = {}

    @property
    def connection_count(self) -> int:
        """Get the number of active connections."""
        return len(self._active_connections)

    @property
    def active_connections(self) -> Set[WebSocket]:
        """Get the set of active connections."""
        return self._active_connections.copy()

    async def connect(self, websocket: WebSocket, metadata: Dict[str, Any] = None) -> None:
        """
        Accept and register a new WebSocket connection.

        Args:
            websocket: The WebSocket connection to register
            metadata: Optional metadata to associate with the connection
        """
        await websocket.accept()
        self._active_connections.add(websocket)

        if metadata:
            self._connection_metadata[websocket] = metadata

        logger.info(
            f"Client connected. Total connections: {self.connection_count}",
            extra={"metadata": metadata}
        )

    def disconnect(self, websocket: WebSocket) -> None:
        """
        Remove a WebSocket connection from the active set.

        Args:
            websocket: The WebSocket connection to remove
        """
        self._active_connections.discard(websocket)
        self._connection_metadata.pop(websocket, None)

        logger.info(f"Client disconnected. Total connections: {self.connection_count}")

    async def send_personal_message(self, websocket: WebSocket, message: Dict[str, Any]) -> bool:
        """
        Send a message to a specific WebSocket connection.

        Args:
            websocket: The target WebSocket connection
            message: The message to send

        Returns:
            True if message was sent successfully, False otherwise
        """
        try:
            await websocket.send_json(message)
            return True
        except Exception as e:
            logger.error(f"Error sending message to client: {e}")
            return False

    async def broadcast(self, message: Dict[str, Any]) -> int:
        """
        Broadcast a message to all connected clients concurrently.

        Args:
            message: The message to broadcast

        Returns:
            Number of successful broadcasts
        """
        if not self._active_connections:
            return 0

        # Create tasks for concurrent broadcasting
        tasks = [
            self._send_safe(conn, message)
            for conn in self._active_connections
        ]

        # Execute all broadcasts concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Clean up failed connections
        failed_connections = []
        successful_count = 0

        for conn, result in zip(list(self._active_connections), results):
            if isinstance(result, Exception):
                logger.error(f"Failed to broadcast to connection: {result}")
                failed_connections.append(conn)
            elif result is False:
                failed_connections.append(conn)
            else:
                successful_count += 1

        # Remove failed connections
        for conn in failed_connections:
            self.disconnect(conn)

        return successful_count

    async def broadcast_to_group(self, message: Dict[str, Any], group_filter: callable) -> int:
        """
        Broadcast a message to a filtered group of connections.

        Args:
            message: The message to broadcast
            group_filter: A function that takes connection metadata and returns True if the connection should receive the message

        Returns:
            Number of successful broadcasts
        """
        target_connections = [
            conn for conn, metadata in self._connection_metadata.items()
            if group_filter(metadata)
        ]

        if not target_connections:
            return 0

        tasks = [
            self._send_safe(conn, message)
            for conn in target_connections
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        successful_count = sum(
            1 for result in results
            if not isinstance(result, Exception) and result is not False
        )

        return successful_count

    async def _send_safe(self, websocket: WebSocket, message: Dict[str, Any]) -> bool:
        """
        Safely send a message to a WebSocket connection.

        Args:
            websocket: The target WebSocket connection
            message: The message to send

        Returns:
            True if successful, False otherwise
        """
        try:
            await websocket.send_json(message)
            return True
        except Exception as e:
            logger.error(f"Error in _send_safe: {e}")
            return False

    def get_connection_metadata(self, websocket: WebSocket) -> Dict[str, Any]:
        """
        Get metadata associated with a connection.

        Args:
            websocket: The WebSocket connection

        Returns:
            Connection metadata or empty dict if not found
        """
        return self._connection_metadata.get(websocket, {})
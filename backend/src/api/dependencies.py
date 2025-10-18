"""Dependency injection for FastAPI endpoints."""

from typing import Annotated

from fastapi import Depends, Request, HTTPException

from src.api.websocket.server import WebSocketServer
from src.api.websocket.connection_manager import ConnectionManager
from src.core.fact_checking.orchestrator import FactCheckingOrchestrator


def get_websocket_server(request: Request) -> WebSocketServer:
    """
    Get the WebSocket server instance from app state.

    Args:
        request: FastAPI request object

    Returns:
        WebSocket server instance

    Raises:
        HTTPException: If server is not initialized
    """
    if not hasattr(request.app.state, 'ws_server'):
        raise HTTPException(status_code=500, detail="Server not initialized")

    return request.app.state.ws_server


def get_connection_manager(
    server: Annotated[WebSocketServer, Depends(get_websocket_server)]
) -> ConnectionManager:
    """
    Get the connection manager instance.

    Args:
        server: WebSocket server instance

    Returns:
        Connection manager instance
    """
    return server.connection_manager


def get_orchestrator(
    server: Annotated[WebSocketServer, Depends(get_websocket_server)]
) -> FactCheckingOrchestrator:
    """
    Get the fact-checking orchestrator instance.

    Args:
        server: WebSocket server instance

    Returns:
        Orchestrator instance

    Raises:
        HTTPException: If orchestrator is not initialized
    """
    if not server.orchestrator:
        raise HTTPException(
            status_code=503,
            detail="Fact-checking service not initialized"
        )

    return server.orchestrator


# Type aliases for dependency injection
ServerDep = Annotated[WebSocketServer, Depends(get_websocket_server)]
ManagerDep = Annotated[ConnectionManager, Depends(get_connection_manager)]
OrchestratorDep = Annotated[FactCheckingOrchestrator, Depends(get_orchestrator)]
"""HTTP endpoints for the WebSocket server."""

import asyncio
from typing import Dict, Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.api.websocket.messages import MessageFactory
from src.api.dependencies import ServerDep, ManagerDep, OrchestratorDep


class TranscriptRequest(BaseModel):
    """Request model for transcript submission."""
    text: str = Field(min_length=1, max_length=1000, description="Text to process")
    speaker: str = Field(default="Test User", max_length=100, description="Speaker identifier")


class TranscriptResponse(BaseModel):
    """Response model for transcript submission."""
    status: str
    text: str
    speaker: str


class HealthResponse(BaseModel):
    """Response model for health check."""
    service: str
    status: str
    websocket_url: str
    connected_clients: int


router = APIRouter(prefix="", tags=["API"])


@router.get("/", response_model=HealthResponse)
async def health_check(
    connection_manager: ManagerDep
) -> HealthResponse:
    """
    Health check endpoint.

    Returns server status and connection information.
    """
    return HealthResponse(
        service="Uhmm Actually Fact-Checker",
        status="running",
        websocket_url="ws://localhost:8765",
        connected_clients=connection_manager.connection_count
    )


@router.post("/test/transcript", response_model=TranscriptResponse)
async def test_transcript(
    orchestrator: OrchestratorDep,
    transcript_request: TranscriptRequest
) -> TranscriptResponse:
    """
    Submit a test transcript for processing.

    This endpoint allows manual testing of the fact-checking pipeline
    without audio input.

    Args:
        orchestrator: Fact-checking orchestrator (injected)
        transcript_request: The transcript to process

    Returns:
        Processing status
    """
    await orchestrator.process_transcription(
        transcript_request.text,
        transcript_request.speaker
    )

    return TranscriptResponse(
        status="processed",
        text=transcript_request.text,
        speaker=transcript_request.speaker
    )


@router.post("/test/mock_data", response_model=Dict[str, str])
async def send_mock_data(
    connection_manager: ManagerDep
) -> Dict[str, str]:
    """
    Send mock data for testing the Chrome extension.

    This endpoint broadcasts sample transcript and verdict messages
    to all connected clients for testing purposes.

    Args:
        connection_manager: WebSocket connection manager (injected)

    Returns:
        Status of mock data broadcast
    """
    message_factory = MessageFactory()

    # Send test transcript
    transcript_message = message_factory.create_transcript_message(
        text="The iPhone was released in 2008",
        speaker="Test User",
        is_final=True
    )
    await connection_manager.broadcast(transcript_message)

    # Wait a bit for realism
    await asyncio.sleep(1)

    # Send test verdict
    verdict_message = message_factory.create_verdict_message(
        transcript="The iPhone was released in 2008",
        claim="The iPhone was released in 2008",
        status="contradicted",
        confidence=0.95,
        rationale="The first iPhone was actually released on June 29, 2007",
        speaker="Test User",
        evidence_url="https://www.apple.com/newsroom/2007/06/29Apple-Reinvents-the-Phone-with-iPhone/"
    )
    await connection_manager.broadcast(verdict_message)

    return {"status": "mock data sent", "clients_notified": connection_manager.connection_count}


@router.get("/stats", response_model=Dict[str, Any])
async def get_statistics(
    server: ServerDep
) -> Dict[str, Any]:
    """
    Get server statistics.

    Returns various metrics about the server's current state.

    Args:
        server: WebSocket server instance (injected)
    """
    return {
        "connected_clients": server.connection_manager.connection_count,
        "transcription_service_running": server.transcription_service.is_running if server.transcription_service else False,
        "orchestrator_initialized": server.orchestrator is not None
    }
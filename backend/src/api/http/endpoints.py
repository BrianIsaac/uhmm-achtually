"""HTTP endpoints for the WebSocket server."""

import asyncio
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from src.api.websocket.messages import MessageFactory


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
async def health_check(request: Request) -> HealthResponse:
    """
    Health check endpoint.

    Returns server status and connection information.
    """
    ws_server = request.app.state.ws_server

    return HealthResponse(
        service="Uhmm Actually Fact-Checker",
        status="running",
        websocket_url="ws://localhost:8765",
        connected_clients=ws_server.connection_manager.connection_count
    )


@router.post("/test/transcript", response_model=TranscriptResponse)
async def test_transcript(request: Request, transcript_request: TranscriptRequest) -> TranscriptResponse:
    """
    Submit a test transcript for processing.

    This endpoint allows manual testing of the fact-checking pipeline
    without audio input.

    Args:
        transcript_request: The transcript to process

    Returns:
        Processing status

    Raises:
        HTTPException: If service is not initialized
    """
    ws_server = request.app.state.ws_server

    if not ws_server.orchestrator:
        raise HTTPException(
            status_code=503,
            detail="Service not initialized"
        )

    await ws_server.orchestrator.process_transcription(
        transcript_request.text,
        transcript_request.speaker
    )

    return TranscriptResponse(
        status="processed",
        text=transcript_request.text,
        speaker=transcript_request.speaker
    )


@router.post("/test/mock_data", response_model=Dict[str, str])
async def send_mock_data(request: Request) -> Dict[str, str]:
    """
    Send mock data for testing the Chrome extension.

    This endpoint broadcasts sample transcript and verdict messages
    to all connected clients for testing purposes.

    Returns:
        Status of mock data broadcast
    """
    ws_server = request.app.state.ws_server
    message_factory = MessageFactory()

    # Send test transcript
    transcript_message = message_factory.create_transcript_message(
        text="The iPhone was released in 2008",
        speaker="Test User",
        is_final=True
    )
    await ws_server.connection_manager.broadcast(transcript_message)

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
    await ws_server.connection_manager.broadcast(verdict_message)

    return {"status": "mock data sent", "clients_notified": ws_server.connection_manager.connection_count}


@router.get("/stats", response_model=Dict[str, Any])
async def get_statistics(request: Request) -> Dict[str, Any]:
    """
    Get server statistics.

    Returns various metrics about the server's current state.
    """
    ws_server = request.app.state.ws_server

    return {
        "connected_clients": ws_server.connection_manager.connection_count,
        "transcription_service_running": ws_server.transcription_service.is_running if ws_server.transcription_service else False,
        "orchestrator_initialized": ws_server.orchestrator is not None
    }
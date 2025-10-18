"""FastAPI webhook server for receiving Meeting BaaS events."""

import json
import hmac
import hashlib
from datetime import datetime
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.responses import JSONResponse
from .models import WebhookEvent, TranscriptUtterance
from .config import settings


app = FastAPI(
    title="Meeting BaaS Webhook Server",
    description="Receives transcription events from Meeting BaaS",
    version="0.1.0",
)


# Store transcripts in memory (for demo purposes)
transcripts_store: dict[str, list[TranscriptUtterance]] = {}


def verify_webhook_signature(
    payload: bytes, signature: str | None, api_key: str
) -> bool:
    """
    Verify webhook signature from Meeting BaaS.

    Args:
        payload: Raw request body bytes
        signature: Signature from x-meetingbaas-signature header
        api_key: Meeting BaaS API key

    Returns:
        True if signature is valid, False otherwise
    """
    if not signature:
        return False

    # Compute HMAC-SHA256 signature
    expected_signature = hmac.new(
        api_key.encode(), payload, hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(signature, expected_signature)


@app.get("/")
async def root():
    """Root endpoint - health check."""
    return {
        "status": "ok",
        "service": "Meeting BaaS Webhook Server",
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.post("/webhooks/meetingbaas")
async def handle_webhook(
    request: Request,
    x_meetingbaas_signature: str | None = Header(None),
    x_meeting_baas_api_key: str | None = Header(None),
):
    """
    Handle incoming webhooks from Meeting BaaS.

    Receives events including:
    - meeting.started: Bot joined the meeting
    - meeting.completed: Meeting ended, transcript available
    - meeting.failed: Bot failed to join

    Args:
        request: FastAPI request object
        x_meetingbaas_signature: Webhook signature for verification
        x_meeting_baas_api_key: API key from webhook header

    Returns:
        JSON response acknowledging receipt

    Raises:
        HTTPException: If signature verification fails
    """
    # Get raw body for signature verification
    body = await request.body()

    # Verify API key
    if x_meeting_baas_api_key != settings.meeting_baas_api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")

    # Verify webhook signature (optional but recommended)
    if x_meetingbaas_signature:
        if not verify_webhook_signature(
            body, x_meetingbaas_signature, settings.meeting_baas_api_key
        ):
            raise HTTPException(status_code=401, detail="Invalid signature")

    # Parse event data
    try:
        event_data = json.loads(body)
        event = WebhookEvent(**event_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid payload: {str(e)}")

    # Log event
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / f"webhook_{datetime.utcnow().strftime('%Y%m%d')}.jsonl"

    with open(log_file, "a") as f:
        f.write(json.dumps(event.model_dump()) + "\n")

    # Handle different event types
    if event.event == "meeting.started":
        await handle_meeting_started(event)
    elif event.event == "meeting.completed":
        await handle_meeting_completed(event)
    elif event.event == "meeting.failed":
        await handle_meeting_failed(event)
    else:
        print(f"⚠️  Unknown event type: {event.event}")

    return JSONResponse(
        content={"status": "received", "event": event.event, "bot_id": event.bot_id}
    )


async def handle_meeting_started(event: WebhookEvent):
    """
    Handle meeting.started event.

    Args:
        event: WebhookEvent containing meeting start data
    """
    print(f"✅ Bot {event.bot_id} joined meeting: {event.meeting_url}")
    print(f"   Timestamp: {event.timestamp}")


async def handle_meeting_completed(event: WebhookEvent):
    """
    Handle meeting.completed event with transcript data.

    Args:
        event: WebhookEvent containing transcript data
    """
    print(f"🎬 Meeting completed: {event.meeting_url}")
    print(f"   Bot ID: {event.bot_id}")

    # Extract transcript data
    transcript_data = event.data.get("transcript", [])

    if transcript_data:
        # Parse transcript utterances
        utterances = [
            TranscriptUtterance(**utterance) for utterance in transcript_data
        ]

        # Store transcript
        transcripts_store[event.bot_id] = utterances

        # Print transcript summary
        print(f"\n📝 Transcript ({len(utterances)} utterances):")
        print("=" * 80)

        for utterance in utterances:
            timestamp = format_timestamp(utterance.start_time)
            print(f"[{timestamp}] {utterance.speaker}:")
            print(f"  {utterance.text}")
            print()

        print("=" * 80)

        # Save transcript to file
        save_transcript_to_file(event.bot_id, utterances, event.meeting_url)
    else:
        print("⚠️  No transcript data available")

    # Print recording URL if available
    recording_url = event.data.get("recording_url")
    if recording_url:
        print(f"🎥 Recording: {recording_url}")


async def handle_meeting_failed(event: WebhookEvent):
    """
    Handle meeting.failed event.

    Args:
        event: WebhookEvent containing failure data
    """
    print(f"❌ Bot {event.bot_id} failed to join meeting: {event.meeting_url}")
    print(f"   Error: {event.data.get('error', 'Unknown error')}")


def format_timestamp(seconds: float) -> str:
    """
    Format seconds into MM:SS timestamp.

    Args:
        seconds: Time in seconds

    Returns:
        Formatted timestamp string
    """
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins:02d}:{secs:02d}"


def save_transcript_to_file(
    bot_id: str, utterances: list[TranscriptUtterance], meeting_url: str
):
    """
    Save transcript to a text file.

    Args:
        bot_id: Bot identifier
        utterances: List of transcript utterances
        meeting_url: URL of the meeting
    """
    # Create transcripts directory
    transcript_dir = Path("logs/transcripts")
    transcript_dir.mkdir(parents=True, exist_ok=True)

    # Generate filename
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = transcript_dir / f"transcript_{bot_id}_{timestamp}.txt"

    # Write transcript
    with open(filename, "w") as f:
        f.write(f"Meeting Transcript\n")
        f.write(f"Meeting URL: {meeting_url}\n")
        f.write(f"Bot ID: {bot_id}\n")
        f.write(f"Generated: {datetime.utcnow().isoformat()}\n")
        f.write("=" * 80 + "\n\n")

        for utterance in utterances:
            timestamp = format_timestamp(utterance.start_time)
            f.write(f"[{timestamp}] {utterance.speaker}:\n")
            f.write(f"{utterance.text}\n\n")

    print(f"💾 Transcript saved to: {filename}")


@app.get("/transcripts/{bot_id}")
async def get_transcript(bot_id: str):
    """
    Retrieve stored transcript for a bot.

    Args:
        bot_id: Bot identifier

    Returns:
        Transcript data

    Raises:
        HTTPException: If transcript not found
    """
    if bot_id not in transcripts_store:
        raise HTTPException(status_code=404, detail="Transcript not found")

    return {
        "bot_id": bot_id,
        "transcript": [u.model_dump() for u in transcripts_store[bot_id]],
    }


@app.get("/transcripts")
async def list_transcripts():
    """
    List all available transcripts.

    Returns:
        List of bot IDs with transcripts
    """
    return {"bot_ids": list(transcripts_store.keys()), "count": len(transcripts_store)}

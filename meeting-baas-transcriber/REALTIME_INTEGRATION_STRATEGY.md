# Real-Time Integration Strategy: Meeting BaaS + Existing Bot

## Critical Discovery

Your requirement: **Real-time fact-checking with TTS responses during the meeting**

Meeting BaaS webhook limitation: Transcripts only available **after meeting completion**

## Architecture Problem

### Current Daily.co Bot (Real-Time)
```
Zoom/Teams Meeting → ❌ Cannot join external meetings
Daily.co Room → DailyTransport → GroqSTT → Claims → FactCheck → TTS → Real-time response
                   ↓ Streaming audio
                   ↓ 1.2-2.25s latency
```

### Meeting BaaS Standard (Post-Meeting Only)
```
Zoom/Teams Meeting → Meeting BaaS Bot → Records → Webhook (meeting.complete)
                                                    ↓ After meeting ends
                                                    Transcript available
```

## Solution: Real-Time Audio Streaming

Meeting BaaS supports **WebSocket audio streaming** to your server. Use the [realtime-meeting-transcription](https://github.com/Meeting-Baas/realtime-meeting-transcription) pattern.

### New Architecture

```
Zoom/Teams Meeting
  ↓
Meeting BaaS Bot (joins meeting, streams audio via WebSocket)
  ↓ Real-time audio stream
WebSocket Proxy (your server)
  ↓
GroqSTT / Deepgram (your transcription)
  ↓
**Your existing Stages 3-6** (SentenceAggregator → Claims → FactCheck)
  ↓
TTS Service (your existing TTS)
  ↓
WebSocket back to Meeting BaaS Bot
  ↓
Bot speaks in Zoom/Teams meeting (real-time!)
```

## Implementation Steps

### Phase 1: WebSocket Audio Streaming

Create a WebSocket server that receives audio from Meeting BaaS bot:

```python
# meeting-baas-transcriber/src/audio_stream_server.py
import asyncio
import websockets
from pipecat.transports.websocket import WebSocketTransport
from backend.src.processors.claim_extractor import ClaimExtractor
from backend.src.processors.web_fact_checker import WebFactChecker

class RealTimeFactCheckServer:
    """WebSocket server for real-time Meeting BaaS audio streaming."""

    async def handle_audio_stream(self, websocket):
        """Receive audio from Meeting BaaS, process through pipeline."""

        # Create pipeline: Audio → STT → Claims → FactCheck → TTS
        transport = WebSocketTransport(websocket)

        # Stage 2: Your STT (Groq/Deepgram)
        stt = GroqSTTService(api_key=settings.groq_api_key)

        # Stage 3-4: Your existing processors
        claim_extractor = ClaimExtractor(groq_api_key=settings.groq_api_key)
        fact_checker = WebFactChecker(
            exa_api_key=settings.exa_api_key,
            groq_api_key=settings.groq_api_key,
            allowed_domains=settings.allowed_domains_list
        )

        # Stage 6: TTS response (send back to bot)
        tts = YourTTSService()

        # Build pipeline
        pipeline = Pipeline([
            transport,      # WebSocket audio input
            stt,            # Transcription
            claim_extractor,
            fact_checker,
            tts,
            transport       # WebSocket audio output (bot speaks)
        ])

        await pipeline.run()
```

### Phase 2: Configure Meeting BaaS Bot for Streaming

When creating the bot, configure it to stream audio to your WebSocket server:

```python
# create_realtime_bot.py
from src.meeting_baas_client import MeetingBaaSClient

async def create_realtime_bot(meeting_url: str):
    client = MeetingBaaSClient()

    # Create bot with WebSocket streaming enabled
    response = await client.create_bot(
        meeting_url=meeting_url,
        webhook_url="wss://your-server.ngrok.io/audio_stream",  # WebSocket endpoint
        bot_name="Fact Checker Bot",
        recording_mode="audio_only",
        # Enable real-time audio streaming (Meeting BaaS API parameter)
        stream_audio=True  # Check Meeting BaaS API docs for exact parameter
    )

    return response
```

### Phase 3: TTS Response Back to Bot

The bot needs to speak verdicts in the meeting. Send audio back via WebSocket:

```python
async def send_verdict_audio(websocket, verdict: VerdictFrame):
    """Convert verdict to speech and send to bot."""

    # Generate TTS audio
    audio_data = await tts.synthesise(
        text=f"Fact check: {verdict.claim}. Status: {verdict.status}. {verdict.rationale}"
    )

    # Send to Meeting BaaS bot (bot speaks in meeting)
    await websocket.send(audio_data)
```

## Key Differences from Original Plan

| Aspect | Original Plan (Post-Meeting) | Real-Time Plan (Streaming) |
|--------|------------------------------|----------------------------|
| **Integration Point** | Webhook (meeting.complete) | WebSocket (audio stream) |
| **Latency** | Minutes (after meeting) | 1.2-2.25s (real-time) |
| **Reuse Code** | Stages 3-6 only | Stages 2-6 (your STT + pipeline) |
| **Bot Response** | None (analysis only) | TTS audio (bot speaks) |
| **Complexity** | Low (REST webhooks) | Medium (WebSocket bidirectional) |

## Trade-Offs

### Meeting BaaS Real-Time Streaming
✅ Joins external Zoom/Teams meetings
✅ Real-time fact-checking (1.2-2.25s latency)
✅ Bot can speak verdicts in meeting
✅ Reuses your entire pipeline (Stages 2-6)
⚠️ Requires WebSocket server (more complex than webhooks)
⚠️ Still uses your STT (not Meeting BaaS's 95% accurate transcription)

### Meeting BaaS Standard Webhooks (Post-Meeting)
✅ Simpler integration (REST webhooks)
✅ Uses Meeting BaaS 95% accurate transcription
✅ Reuses claim extraction + fact-checking
❌ No real-time responses (only post-meeting analysis)
❌ Bot cannot speak in meeting

## Recommendation

**For real-time TTS responses: Use WebSocket streaming architecture**

This gives you:
- Real-time fact-checking during the meeting
- Bot can speak verdicts via TTS
- Full reuse of your existing pipeline
- Ability to join external Zoom/Teams meetings

## Next Steps

1. Research Meeting BaaS WebSocket API documentation
2. Create WebSocket audio stream server (similar to DailyTransport but for Meeting BaaS)
3. Test bidirectional audio (receive + send TTS back to bot)
4. Integrate with existing pipeline (Stages 2-6)

## Alternative: Hybrid Approach

Use **both** architectures:

1. **Real-time preview** (lower accuracy): Meeting BaaS audio stream → Your Groq STT → Fast claims only
2. **Post-meeting full analysis** (higher accuracy): Meeting BaaS webhook → 95% transcript → Comprehensive fact-check

This gives you immediate responses during the meeting + detailed analysis afterwards.

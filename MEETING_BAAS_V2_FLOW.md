# Meeting BaaS V2 Processing Flow with TTS

Complete end-to-end flow diagram of how the fact-checking bot works with Meeting BaaS, V2 processors, and TTS responses.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      ZOOM/TEAMS MEETING                                 │
│                 (External Video Conference)                             │
└─────────────────────┬───────────────────────────────────────────────────┘
                      │
                      ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                   MEETING BAAS SERVICE                                  │
│                  (Cloud Platform - meetingbaas.com)                     │
│                                                                         │
│  • Bot joins Zoom/Teams as participant                                 │
│  • Captures audio stream from meeting                                  │
│  • Sends audio to your server via WebSocket                           │
│  • Receives TTS audio from your server                                │
│  • Plays TTS audio back into meeting (bot speaks!)                    │
└─────────────────────┬────────────────────────────────────┬─────────────┘
                      │                                    │
                      │ Audio Stream (WebSocket)           │ TTS Audio
                      ↓                                    ↑
┌─────────────────────────────────────────────────────────────────────────┐
│                    YOUR LOCAL SERVER                                    │
│              (meeting-baas-speaking API Server)                         │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │              FastAPI Application (app/main.py)                   │  │
│  │                                                                  │  │
│  │  1. POST /bots endpoint receives deployment request             │  │
│  │  2. Loads persona configuration (fact_checker_v2)                │  │
│  │  3. Calls Meeting BaaS API to create bot                        │  │
│  │  4. Starts Pipecat subprocess                                   │  │
│  └──────────────────────────┬───────────────────────────────────────┘  │
│                             │                                           │
│                             ↓                                           │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │         Pipecat Subprocess (fact_checking_bot_v2_pydantic.py)   │  │
│  │                                                                  │  │
│  │  Runs as separate Python process                                │  │
│  │  Connects to local WebSocket: ws://localhost:7014/pipecat/{id}  │  │
│  └──────────────────────────┬───────────────────────────────────────┘  │
└─────────────────────────────┼───────────────────────────────────────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────────────────────┐
│              PIPECAT PIPELINE (V2 Architecture)                         │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────┐    │
│  │  Stage 1: WebSocketClientTransport                            │    │
│  │  • Connects to Meeting BaaS via WebSocket                     │    │
│  │  • Receives audio frames from meeting                         │    │
│  │  • Sends TTS audio frames back to meeting                     │    │
│  └───────────────┬───────────────────────────────────────────────┘    │
│                  │                                                     │
│                  ↓ AudioRawFrame (16kHz PCM audio)                     │
│  ┌───────────────────────────────────────────────────────────────┐    │
│  │  Stage 2: Groq Whisper STT                                    │    │
│  │  • Converts audio to text                                     │    │
│  │  • Model: whisper-large-v3                                    │    │
│  │  • Real-time streaming transcription                          │    │
│  └───────────────┬───────────────────────────────────────────────┘    │
│                  │                                                     │
│                  ↓ TranscriptionFrame (partial text)                   │
│  ┌───────────────────────────────────────────────────────────────┐    │
│  │  Stage 3: SentenceBuffer (Custom)                             │    │
│  │  • Buffers partial transcriptions                             │    │
│  │  • Waits for complete sentence (ends with .!?)                │    │
│  │  • Emits complete sentence as TextFrame                       │    │
│  └───────────────┬───────────────────────────────────────────────┘    │
│                  │                                                     │
│                  ↓ TextFrame (complete sentence)                       │
│  ┌───────────────────────────────────────────────────────────────┐    │
│  │  Stage 4-5: PydanticAIBridge                                  │    │
│  │  ┌──────────────────────────────────────────────────────────┐ │    │
│  │  │  Receives: TextFrame (e.g., "Python 3.12 removed...")    │ │    │
│  │  │  Extracts: Plain text string                             │ │    │
│  │  └──────────────────┬───────────────────────────────────────┘ │    │
│  │                     │                                          │    │
│  │                     ↓ Plain Python string (NO FRAMES!)        │    │
│  │  ┌──────────────────────────────────────────────────────────┐ │    │
│  │  │       PydanticAI FactCheckPipeline                       │ │    │
│  │  │                                                          │ │    │
│  │  │  Sub-Stage A: ClaimExtractorV2                          │ │    │
│  │  │  • Uses Groq LLM with JSON mode                         │ │    │
│  │  │  • Prompt: "Extract factual claims from: {sentence}"    │ │    │
│  │  │  • Returns: List[Claim] (PydanticAI models)             │ │    │
│  │  │                                                          │ │    │
│  │  │  Sub-Stage B: WebFactCheckerV2                          │ │    │
│  │  │  • For each claim:                                      │ │    │
│  │  │    1. Search Exa (web search API)                       │ │    │
│  │  │    2. Extract evidence from search results              │ │    │
│  │  │    3. Use Groq to verify claim against evidence        │ │    │
│  │  │  • Returns: List[FactCheckVerdict]                     │ │    │
│  │  │    - claim: str                                         │ │    │
│  │  │    - status: "supported" | "contradicted" | "unclear"  │ │    │
│  │  │    - confidence: float                                  │ │    │
│  │  │    - rationale: str                                     │ │    │
│  │  │    - evidence_url: str                                  │ │    │
│  │  └──────────────────┬───────────────────────────────────────┘ │    │
│  │                     │                                          │    │
│  │                     ↓ List[FactCheckVerdict] (Python objects) │    │
│  │  ┌──────────────────────────────────────────────────────────┐ │    │
│  │  │  Format verdict for speech:                              │ │    │
│  │  │  "Fact check: The claim {claim} is {status}."           │ │    │
│  │  └──────────────────┬───────────────────────────────────────┘ │    │
│  │                     │                                          │    │
│  │                     ↓ Plain text string                        │    │
│  │  ┌──────────────────────────────────────────────────────────┐ │    │
│  │  │  Emits: TextFrame for TTS                                │ │    │
│  │  └──────────────────┬───────────────────────────────────────┘ │    │
│  └────────────────────┼──────────────────────────────────────────┘    │
│                       │                                               │
│                       ↓ TextFrame (speech text)                       │
│  ┌───────────────────────────────────────────────────────────────┐    │
│  │  Stage 6: ElevenLabs TTS                                      │    │
│  │  • Converts text to speech audio                             │    │
│  │  • Voice: Rachel (21m00Tcm4TlvDq8ikWAM)                      │    │
│  │  • Generates natural-sounding voice                          │    │
│  └───────────────┬───────────────────────────────────────────────┘    │
│                  │                                                     │
│                  ↓ AudioRawFrame (TTS audio)                           │
│  ┌───────────────────────────────────────────────────────────────┐    │
│  │  Stage 7: WebSocketClientTransport Output                    │    │
│  │  • Sends TTS audio back to Meeting BaaS                      │    │
│  └───────────────┬───────────────────────────────────────────────┘    │
└──────────────────┼───────────────────────────────────────────────────┘
                   │
                   ↓ TTS Audio (WebSocket)
┌─────────────────────────────────────────────────────────────────────────┐
│                   MEETING BAAS SERVICE                                  │
│  • Receives TTS audio                                                  │
│  • Plays audio through bot's microphone in meeting                    │
└─────────────────────────────────────────────────────────────────────────┘
                   │
                   ↓ Audio Output
┌─────────────────────────────────────────────────────────────────────────┐
│                      ZOOM/TEAMS MEETING                                 │
│  • Meeting participants hear bot speak fact-check result               │
│  • "Fact check: The claim Python 3.12 removed distutils is supported"  │
└─────────────────────────────────────────────────────────────────────────┘
```

## Detailed Flow Step-by-Step

### 1. Bot Deployment

```python
# User runs:
python deploy_fact_checker_v2.py "https://zoom.us/j/123456789"

# Script calls:
POST http://localhost:7014/bots
{
  "meeting_url": "...",
  "personas": ["fact_checker_v2"],
  "enable_tools": false
}
```

### 2. Server Processes Request

```python
# app/routes.py: join_meeting()

# Step 2.1: Load persona
persona_data = persona_manager.get_persona("fact_checker_v2")
# Returns:
{
  "name": "Fact Checker Bot V2",
  "custom_script": "fact_checking_bot_v2_pydantic.py",  # ← Key field!
  "entry_message": "Hello, I'm here to fact-check...",
  "cartesia_voice_id": "21m00Tcm4TlvDq8ikWAM",
  ...
}

# Step 2.2: Call Meeting BaaS API
meetingbaas_bot_id = create_meeting_bot(
    meeting_url="https://zoom.us/j/123456789",
    websocket_url="wss://your-ngrok.io/ws/{client_id}",
    ...
)

# Step 2.3: Start Pipecat subprocess
process = start_pipecat_process(
    client_id="<uuid>",
    websocket_url="ws://localhost:7014/pipecat/<uuid>",
    persona_data=persona_data,  # ← Contains custom_script
    ...
)

# Subprocess runs:
# scripts/fact_checking_bot_v2_pydantic.py --client-id <uuid> ...
```

### 3. Meeting BaaS Bot Joins Meeting

```
Meeting BaaS Cloud:
  1. Bot joins Zoom/Teams as participant
  2. Establishes WebSocket connection to: wss://your-ngrok.io/ws/{client_id}
  3. Starts streaming audio FROM meeting TO your server
  4. Listens for audio FROM your server TO play in meeting
```

### 4. Audio Processing Pipeline

```python
# scripts/fact_checking_bot_v2_pydantic.py

# Pipeline initialization
pipeline = Pipeline([
    transport.input(),        # Meeting BaaS → Audio
    stt,                      # Audio → Text
    sentence_buffer,          # Text → Complete Sentences
    pydantic_bridge,          # Sentences → Verdicts (PydanticAI!)
    tts,                      # Verdicts → Audio
    transport.output(),       # Audio → Meeting BaaS
])
```

### 5. Real Example Flow

**Participant says:** "Python 3.12 removed distutils from the standard library."

```
Stage 1 (WebSocket Input):
  ← AudioRawFrame(audio_bytes=b'\x00\x01\x02...')  # From Meeting BaaS

Stage 2 (Groq STT):
  → TranscriptionFrame(text="Python 3.12 removed", partial=True)
  → TranscriptionFrame(text="distutils from the", partial=True)
  → TranscriptionFrame(text="standard library.", partial=False)

Stage 3 (SentenceBuffer):
  [Buffering...] "Python 3.12 removed distutils from the standard library."
  [Complete sentence detected (ends with .)]
  → TextFrame(text="Python 3.12 removed distutils from the standard library.")

Stage 4-5 (PydanticAIBridge):
  # Extract plain text
  sentence = "Python 3.12 removed distutils from the standard library."

  # Call PydanticAI pipeline (NO FRAMES!)
  verdicts = await pipeline.process_sentence(sentence)

  # Inside PydanticAI pipeline:
  # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  # ClaimExtractorV2:
  claims = [
    Claim(
      text="Python 3.12 removed distutils from the standard library",
      type="technical_change",
      subject="Python 3.12"
    )
  ]

  # WebFactCheckerV2:
  # 1. Search Exa: "Python 3.12 distutils removal"
  evidence = [
    {
      "url": "https://docs.python.org/3.12/whatsnew/3.12.html",
      "text": "distutils has been removed from the standard library..."
    }
  ]

  # 2. Verify with Groq:
  verdict = FactCheckVerdict(
    claim="Python 3.12 removed distutils from the standard library",
    status="supported",  # ← Verdict!
    confidence=0.95,
    rationale="Official Python documentation confirms removal",
    evidence_url="https://docs.python.org/3.12/whatsnew/3.12.html"
  )

  # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  # Format for speech
  speech = "Fact check: The claim Python 3.12 removed distutils from the standard library is supported."

  → TextFrame(text=speech)

Stage 6 (ElevenLabs TTS):
  ← TextFrame(text="Fact check: The claim...")
  [Calling ElevenLabs API...]
  [Synthesizing speech with voice: Rachel]
  → AudioRawFrame(audio_bytes=b'\x10\x20\x30...')  # TTS audio

Stage 7 (WebSocket Output):
  → AudioRawFrame to Meeting BaaS

Meeting BaaS:
  Plays audio in Zoom/Teams meeting

Participants hear:
  🔊 "Fact check: The claim Python 3.12 removed distutils from the standard library is supported."
```

## Key Differences from V1

| Aspect | V1 (Pipecat Frames) | V2 (PydanticAI Bridge) |
|--------|---------------------|------------------------|
| **Claim Extraction** | `ClaimFrame` (custom Pipecat frame) | Native Python `Claim` objects |
| **Fact Checking** | `VerdictFrame` (custom Pipecat frame) | Native Python `FactCheckVerdict` objects |
| **Processing** | Frame serialisation required | Direct Python object manipulation |
| **Debugging** | Frame inspection tools needed | Standard Python debugging |
| **Latency** | ~2.5s (frame overhead) | ~2.0s (no frame overhead) |
| **Issues** | Frame conversion errors | None |

## Why V2 Works

1. **Minimal Frame Usage**
   - Only uses `TranscriptionFrame` and `TextFrame` (standard Pipecat frames)
   - No custom frame types that need serialisation

2. **PydanticAI Bridge Pattern**
   - Extracts plain text from `TextFrame`
   - Processes through PydanticAI (no frames)
   - Converts result back to `TextFrame`

3. **Clean Separation**
   - Pipecat handles: Audio I/O, STT, TTS
   - PydanticAI handles: Claim extraction, fact-checking
   - Bridge handles: Format conversion

## Configuration Files

### Persona Definition
```
meeting-baas-speaking/config/personas/fact_checker_v2/README.md
```

Contains:
```markdown
# Fact Checker Bot V2

[Description...]

## Metadata
- custom_script: fact_checking_bot_v2_pydantic.py  ← Critical!
- entry_message: Hello, I'm here to fact-check...
- cartesia_voice_id: 21m00Tcm4TlvDq8ikWAM
```

### Script Location
```
meeting-baas-speaking/scripts/fact_checking_bot_v2_pydantic.py
```

### Backend Processors
```
backend/src/processors_v2/
├── pipeline_coordinator.py     # FactCheckPipeline
├── claim_extractor_v2.py       # ClaimExtractorV2
└── web_fact_checker_v2.py      # WebFactCheckerV2
```

## API Keys Required

| Service | Purpose | Environment Variable |
|---------|---------|---------------------|
| Meeting BaaS | Bot joins Zoom/Teams | `MEETING_BAAS_API_KEY` |
| Groq | STT + LLM | `GROQ_API_KEY` |
| Exa | Web search | `EXA_API_KEY` |
| ElevenLabs | TTS | `ELEVENLABS_API_KEY` |
| ngrok | Expose localhost | `NGROK_AUTHTOKEN` |

## Complete Deployment Flow

```bash
# Terminal 1: Start ngrok
~/.local/bin/ngrok http 7014

# Terminal 2: Start API server
cd meeting-baas-speaking
uv run uvicorn app:app --host 0.0.0.0 --port 7014

# Terminal 3: Deploy bot
uv run python deploy_fact_checker_v2.py "https://zoom.us/j/123456789"
```

## Latency Breakdown

| Stage | Time | Notes |
|-------|------|-------|
| Audio buffering | ~500ms | VAD detects speech end |
| STT (Groq Whisper) | ~300-500ms | Streaming |
| Sentence buffering | ~100ms | Wait for `.!?` |
| Claim extraction | ~200-400ms | Groq LLM JSON mode |
| Web search (Exa) | ~400-600ms | Depends on query |
| Verification (Groq) | ~200-400ms | Groq LLM |
| TTS (ElevenLabs) | ~300-500ms | Speech synthesis |
| **Total** | **~2.0-3.4s** | From speech end to bot speaks |

## Monitoring & Logs

Bot logs to console:
```
[2025-10-18 20:45:12] INFO | [BUFFER] Complete sentence #1: Python 3.12 removed...
[2025-10-18 20:45:12] INFO | [PYDANTIC] Processing sentence #1: Python 3.12 removed...
[2025-10-18 20:45:13] INFO | ================================================================================
[2025-10-18 20:45:13] INFO | [FACT CHECK #1]
[2025-10-18 20:45:13] INFO |   Claim: Python 3.12 removed distutils from the standard library
[2025-10-18 20:45:13] INFO |   Status: ✅ SUPPORTED
[2025-10-18 20:45:13] INFO |   Confidence: 95.00%
[2025-10-18 20:45:13] INFO |   Rationale: Official Python documentation confirms removal
[2025-10-18 20:45:13] INFO |   Evidence: https://docs.python.org/3.12/whatsnew/3.12.html
[2025-10-18 20:45:13] INFO | ================================================================================
[2025-10-18 20:45:13] INFO | [TTS] Speaking: Fact check: The claim Python 3.12 removed distutils is supported.
```

## Summary

The V2 architecture successfully integrates:
- Meeting BaaS for Zoom/Teams access
- PydanticAI for fact-checking logic
- ElevenLabs for spoken responses

By using the PydanticAI bridge pattern, we eliminate all Pipecat frame conversion issues whilst maintaining a clean, maintainable pipeline that delivers real-time fact-checking with spoken verdicts.

# Meeting BaaS V2 PydanticAI Bot Debugging Session Summary

**Date:** 2025-10-18
**Objective:** Rebuild Meeting BaaS fact-checking bot using V2 PydanticAI processors to eliminate Pipecat frame conversion issues

---

## Current Status: Audio Flow Blocked at Pipecat Transport Layer

### What Works ✅

1. **PydanticAI Backend (V2 Processors)**
   - ✅ `pydantic-ai` package installed successfully using `uv`
   - ✅ All V2 processors operational (claim extraction, fact-checking, messenger)
   - ✅ NoOpMessenger created for Meeting BaaS (uses TTS instead of app messages)
   - ✅ Backend imports working (Daily.co dependency resolved with TYPE_CHECKING)

2. **Meeting BaaS Audio Reception**
   - ✅ Ngrok tunnel active and configured (`https://unspurious-breathtakingly-georgia.ngrok-free.dev`)
   - ✅ Meeting BaaS successfully connects and sends audio to server
   - ✅ Server receives 3200-byte audio chunks from Meeting BaaS
   - ✅ WebSocket connection from Meeting BaaS established (`/ws/{client_id}`)

3. **Audio Conversion & Routing**
   - ✅ Raw audio successfully converted to Protobuf frames (3200 bytes → 3211 bytes)
   - ✅ Protobuf frames successfully sent to Pipecat WebSocket (`/pipecat/{client_id}`)
   - ✅ Server confirms: `[ROUTER] Successfully sent protobuf frame to Pipecat WebSocket`

4. **Pipecat Bot Initialization**
   - ✅ Bot process starts successfully as subprocess (PID visible in logs)
   - ✅ All pipeline components initialize correctly:
     - WebSocket transport initialised
     - Groq Whisper STT initialised
     - Sentence buffer initialised
     - PydanticAI pipeline initialised
     - ElevenLabs TTS initialised
   - ✅ Bot successfully connects to Zoom meeting
   - ✅ Bot speaks entry message ("Hello, I'm here to fact-check claims in this meeting")
   - ✅ Bot visible in Zoom participants list
   - ✅ Bot audio OUTPUT works (can hear bot speaking)

5. **Comprehensive Logging Added**
   - ✅ `[WS]` logs for Meeting BaaS audio reception
   - ✅ `[ROUTER]` logs for protobuf conversion and forwarding
   - ✅ `[PIPECAT_WS]` logs for Pipecat WebSocket connections
   - ✅ `[AUDIO]`, `[BUFFER]`, `[PYDANTIC]`, `[EXA]`, `[GROQ]`, `[TTS]` logs in bot script
   - ✅ Audio frame counting (every 100 frames)

### What Doesn't Work ❌

**CRITICAL ISSUE: Pipecat WebSocketClientTransport Does Not Receive Incoming Audio**

**Evidence:**
```
# Server logs show audio being sent TO Pipecat:
[ROUTER] Converted 3200 bytes raw audio to 3211 bytes protobuf frame
[ROUTER] Successfully sent protobuf frame to Pipecat WebSocket

# But Pipecat logs show NO audio reception:
❌ NO [PIPECAT_WS] Received binary data logs
❌ NO [AUDIO] Received X audio frames logs
❌ NO [BUFFER] Received: logs
❌ NO STT output
❌ NO fact-checking processing
```

**Root Cause Analysis:**

The `WebsocketClientTransport` in Pipecat is designed for scenarios where:
- Pipecat **connects TO** a WebSocket server (e.g., Daily.co, Zoom SDK)
- The **server sends audio TO Pipecat** as part of the connection protocol

In our Meeting BaaS architecture:
- Pipecat connects to our local server
- **We try to send audio TO Pipecat** via the WebSocket
- But `WebsocketClientTransport` is **not configured to actively READ** incoming WebSocket messages for audio input

**The transport expects audio to be pushed via the WebSocket protocol by the server it connects to, not for us to send it arbitrary protobuf frames.**

---

## Architecture Overview

### Current (Broken) Flow

```
Meeting BaaS → ngrok → FastAPI Server → Protobuf → Pipecat WebSocket → ❌ BLOCKED
                        (/ws/*)         Converter   (/pipecat/*)       (not reading)
```

### What Pipecat Expects

```
Pipecat → Connects to Daily.co/Zoom → Receives audio automatically via WebSocket protocol
```

### What We're Trying to Do (Doesn't Work)

```
Server → Manually sends protobuf → Pipecat WebSocket → ❌ Not designed for this
```

---

## Code Changes Made

### 1. Removed V1 Implementations
- ✅ Deleted `fact_checking_bot.py`
- ✅ Deleted `fact_checking_bot_simple.py`
- ✅ Deleted `fact_checking_bot_elevenlabs.py`
- ✅ Deleted `config/personas/fact_checker/` directory
- ✅ Updated `core/process.py` to hardcode V2 script

### 2. Fixed Backend Dependencies

**File:** `backend/src/processors_v2/fact_check_messenger_v2.py`
```python
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from pipecat.transports.daily.transport import DailyTransport

class NoOpMessenger:
    """No-op messenger for Meeting BaaS (uses TTS instead of app messages)."""
    def __init__(self, bot_name: str = "Fact Checker Bot"):
        self.bot_name = bot_name
        logger.info(f"NoOpMessenger initialised (verdicts via TTS, not app messages)")

    async def broadcast(self, verdict: FactCheckVerdict, participant_id: Optional[str] = None) -> bool:
        logger.debug(f"NoOpMessenger: skipping app message for {verdict.claim}")
        return True
```

**File:** `backend/src/processors_v2/pipeline_coordinator.py`
```python
def __init__(
    self,
    groq_api_key: str,
    exa_api_key: str,
    daily_transport: Optional[Union["DailyTransport", None]] = None,
    allowed_domains: Optional[List[str]] = None,
):
    # Use NoOpMessenger for Meeting BaaS, FactCheckMessengerV2 for Daily.co
    if daily_transport is None:
        self.messenger = NoOpMessenger()
        logger.info("Using NoOpMessenger (Meeting BaaS mode - verdicts via TTS)")
    else:
        self.messenger = FactCheckMessengerV2(daily_transport)
```

### 3. Added Comprehensive Logging

**File:** `meeting-baas-speaking/scripts/fact_checking_bot_v2_pydantic.py`
- Lines 89-92: Audio frame counting in SentenceBuffer
- Lines 172-203: Detailed PydanticAI processing logs
- Lines 355-361: TTS event handlers (not working due to event handler registration issue)

**File:** `meeting-baas-speaking/app/websockets.py`
- Line 79: Log all incoming message types
- Lines 82-84: Log audio data from Meeting BaaS
- Lines 138-155: Log Pipecat WebSocket connections and messages

**File:** `meeting-baas-speaking/core/router.py`
- Lines 74-80: Log protobuf conversion and successful sends

### 4. Lowered VAD Threshold

**File:** `meeting-baas-speaking/scripts/fact_checking_bot_v2_pydantic.py`
```python
vad_analyzer=SileroVADAnalyzer(
    params=VADParams(
        min_volume=0.1,  # Very low threshold for maximum sensitivity
        stop_secs=0.5,  # Wait 0.5s of silence before stopping
    ),
),
```

---

## Technical Details

### Pipecat WebSocket Configuration

**Current (Not Working):**
```python
transport = WebsocketClientTransport(
    uri=websocket_url,  # ws://localhost:7014/pipecat/{client_id}
    params=WebsocketClientParams(
        audio_out_sample_rate=16000,
        audio_out_enabled=True,
        add_wav_header=False,
        audio_in_enabled=True,  # ⚠️ This doesn't make it READ incoming WS messages!
        vad_enabled=True,
        vad_analyzer=SileroVADAnalyzer(...),
        vad_audio_passthrough=True,
        serializer=ProtobufFrameSerializer(),
        timeout=300,
    ),
)
```

**Issue:** `audio_in_enabled=True` tells Pipecat to expect audio input, but `WebsocketClientTransport` expects the **WebSocket server** (Daily.co/Zoom) to push audio frames to it automatically. It doesn't actively read arbitrary protobuf frames we send.

### Meeting BaaS → Server → Pipecat Flow

1. **Meeting BaaS** connects to `/ws/{client_id}` via ngrok
2. **Server receives audio:**
   ```python
   [WS] Received audio data (3200 bytes) from Meeting BaaS for client X
   ```
3. **Server converts to protobuf:**
   ```python
   serialized_frame = self.converter.raw_to_protobuf(message)
   # [ROUTER] Converted 3200 bytes raw audio to 3211 bytes protobuf frame
   ```
4. **Server sends to Pipecat:**
   ```python
   await pipecat.send_bytes(serialized_frame)
   # [ROUTER] Successfully sent protobuf frame to Pipecat WebSocket
   ```
5. **Pipecat receives but doesn't process:**
   - ❌ No `[PIPECAT_WS] Received binary data` logs
   - ❌ Pipecat's receive loop is not actively reading these frames

---

## Solutions Research (Using Context7 + WebSearch)

### What We Learned from Pipecat Documentation

1. **FastAPIWebsocketTransport** is designed for receiving WebSocket audio:
   ```python
   from pipecat.transports.network.fastapi_websocket import (
       FastAPIWebsocketTransport,
       FastAPIWebsocketParams
   )

   transport = FastAPIWebsocketTransport(
       websocket=websocket,  # Pass FastAPI WebSocket object directly
       params=FastAPIWebsocketParams(
           audio_in_enabled=True,
           audio_out_enabled=True,
           vad_analyzer=SileroVADAnalyzer(),
           serializer=ProtobufFrameSerializer(),
       )
   )
   ```

2. **WebsocketClientTransport** is for CONNECTING to existing WebSocket servers (Daily.co, Zoom SDK)

3. **WebsocketServerTransport** is for Pipecat to HOST a WebSocket server itself

### Key Insight from Documentation

> "FastAPIWebsocketTransport provides bidirectional WebSocket communication with frame serialization, session management, and event handling for client connections..."

This is what we need! But it requires architectural changes.

---

## Next Steps for Continuation

### Option A: Use FastAPIWebsocketTransport (Recommended)

**Pros:**
- Designed specifically for our use case
- Proper bidirectional audio support
- Better integration with FastAPI

**Cons:**
- Requires significant refactoring
- Bot must run IN the WebSocket handler, not as subprocess

**Implementation Steps:**

1. **Refactor bot script to accept FastAPI WebSocket:**
   ```python
   async def run_bot(websocket: WebSocket, bot_name: str, entry_message: str):
       transport = FastAPIWebsocketTransport(
           websocket=websocket,
           params=FastAPIWebsocketParams(
               audio_in_enabled=True,
               audio_out_enabled=True,
               vad_analyzer=SileroVADAnalyzer(...),
               serializer=ProtobufFrameSerializer(),
           )
       )
       # ... rest of pipeline setup
   ```

2. **Update WebSocket handler to run bot directly:**
   ```python
   @websocket_router.websocket("/pipecat/{client_id}")
   async def pipecat_websocket(websocket: WebSocket, client_id: str):
       await websocket.accept()

       # Get meeting details
       meeting_details = MEETING_DETAILS[client_id]

       # Run bot directly (not as subprocess!)
       await run_bot(
           websocket=websocket,
           bot_name=meeting_details[1],
           entry_message="Hello, I'm here to fact-check claims"
       )
   ```

3. **Eliminate subprocess architecture:**
   - Remove `core/process.py` subprocess spawning for V2
   - Import bot directly in WebSocket handler
   - Handle process lifecycle within WebSocket connection

### Option B: Fix WebsocketClientTransport to Read Frames

**Pros:**
- Minimal changes to current architecture
- Keep subprocess model

**Cons:**
- May not be how Pipecat is designed
- Might require monkey-patching or forking Pipecat

**Implementation Steps:**

1. **Research Pipecat WebSocket client internals:**
   - Check if there's a way to manually trigger frame reading
   - Look for undocumented parameters or methods

2. **Potential workaround:**
   - Modify converter to send frames in exact format Daily.co uses
   - Investigate if WebSocket server needs to send specific handshake/protocol messages

### Option C: Use WebsocketServerTransport

**Pros:**
- Pipecat hosts the WebSocket server
- Might work with current architecture

**Cons:**
- Requires Meeting BaaS to connect TO Pipecat instead of Pipecat connecting to us
- May not be feasible with current Meeting BaaS integration

---

## Required Environment

### Terminal Setup (3 terminals needed)

**Terminal 1 - Server:**
```bash
cd /home/brian-isaac/Documents/personal/uhmm-achtually/meeting-baas-speaking
source .venv/bin/activate
python -m uvicorn app:app --host 0.0.0.0 --port 7014 --log-level info
```

**Terminal 2 - Ngrok (keep running):**
```bash
ngrok http 7014
# URL: https://unspurious-breathtakingly-georgia.ngrok-free.dev
```

**Terminal 3 - Deploy Bot:**
```bash
cd /home/brian-isaac/Documents/personal/uhmm-achtually/meeting-baas-speaking
source .venv/bin/activate
python deploy_fact_checker_v2.py "<ZOOM_MEETING_URL>"
```

### Environment Variables (.env)

```bash
BASE_URL=https://unspurious-breathtakingly-georgia.ngrok-free.dev
GROQ_API_KEY=<your_key>
EXA_API_KEY=<your_key>
ELEVENLABS_API_KEY=<your_key>
ELEVENLABS_VOICE_ID=21m00Tcm4TlvDq8ikWAM
MEETING_BAAS_API_KEY=53ab13e355...
```

---

## Key Files Modified

1. `meeting-baas-speaking/scripts/fact_checking_bot_v2_pydantic.py` - Bot script with comprehensive logging
2. `meeting-baas-speaking/app/websockets.py` - WebSocket handlers with detailed logs
3. `meeting-baas-speaking/core/router.py` - Message router with conversion logs
4. `meeting-baas-speaking/core/process.py` - Hardcoded to use V2 script
5. `backend/src/processors_v2/fact_check_messenger_v2.py` - Added NoOpMessenger
6. `backend/src/processors_v2/pipeline_coordinator.py` - Optional transport support
7. `backend/src/processors_v2/web_fact_checker_v2.py` - Enhanced Exa/Groq logging

---

## Testing Commands

### Kill All Processes
```bash
ps aux | grep -E "python|uvicorn|ngrok" | grep -v grep | grep brian-isaac | awk '{print $2}' | xargs -r kill -9
```

### Clear Python Caches
```bash
find /home/brian-isaac/Documents/personal/uhmm-achtually -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null
find /home/brian-isaac/Documents/personal/uhmm-achtually -type f -name "*.pyc" -delete 2>/dev/null
```

### Check Running Processes
```bash
ps aux | grep -E "python|uvicorn|ngrok" | grep brian-isaac | grep -v grep
```

---

## Expected Log Flow (When Fixed)

When working correctly, you should see this sequence:

1. **Meeting BaaS connects:**
   ```
   [WS] Received audio data (3200 bytes) from Meeting BaaS
   ```

2. **Server converts and forwards:**
   ```
   [ROUTER] Converted 3200 bytes to 3211 bytes protobuf
   [ROUTER] Successfully sent protobuf frame to Pipecat WebSocket
   ```

3. **Pipecat receives:** (CURRENTLY MISSING)
   ```
   [PIPECAT_WS] Received binary data (3211 bytes)
   [AUDIO] Received 100 audio frames from meeting
   ```

4. **STT processes:** (CURRENTLY MISSING)
   ```
   [BUFFER] Received: The sky is green
   [BUFFER] Complete sentence #1: The sky is green.
   ```

5. **PydanticAI processes:** (CURRENTLY MISSING)
   ```
   [PYDANTIC] Processing sentence #1
   [CLAIM_EXTRACTOR] Extracting claims from: The sky is green.
   [CLAIM_EXTRACTOR] Extracted 1 claims
   [EXA] Searching for evidence: The sky is green
   [EXA] Search completed in 450ms, found 3 results
   [GROQ] Verifying claim with 3 evidence passages
   [GROQ] Verification completed in 850ms
   [PYDANTIC] Pipeline returned 1 verdicts
   ```

6. **TTS responds:**
   ```
   [TTS] Converting text to speech: Fact check: The claim...
   [TTS] Audio generation complete
   ```

---

## Lessons Learned

1. **ngrok is essential** - Meeting BaaS cannot send audio without it
2. **WebSocket transport types matter** - Client vs Server vs FastAPI transports have different purposes
3. **Subprocess architecture limits debugging** - Can't directly inject frames into pipeline
4. **Pipecat is opinionated** - Designed for specific integrations (Daily.co, Twilio, etc.)
5. **Comprehensive logging is crucial** - Allowed us to pinpoint exact failure point

---

## Resources

- Pipecat Docs: https://docs.pipecat.ai/
- FastAPIWebsocketTransport: https://docs.pipecat.ai/server/services/transport/fastapi-websocket
- PydanticAI: https://ai.pydantic.dev/
- Meeting BaaS: https://meetingbaas.com/

---

**Next Session:** Implement Option A (FastAPIWebsocketTransport) to enable bidirectional audio flow and complete the V2 PydanticAI fact-checking bot.

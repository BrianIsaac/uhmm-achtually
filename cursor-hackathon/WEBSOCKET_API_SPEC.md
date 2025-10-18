# WebSocket API Specification

**Interface between Chrome Extension (Frontend) and Python Backend**

This document defines the WebSocket communication protocol for the Uhmm Actually fact-checking system.

---

## 🔌 Connection Details

- **WebSocket URL**: `ws://localhost:8765`
- **Protocol**: WebSocket (RFC 6455)
- **Message Format**: JSON
- **Connection Type**: Persistent bidirectional

---

## 📨 Message Types

### Overview

| Direction | Message Type | Purpose |
|-----------|-------------|---------|
| Backend → Extension | `connection` | Connection acknowledgment |
| Backend → Extension | `transcript` | Live speech transcription |
| Backend → Extension | `verdict` | Fact-check result for a claim |
| Extension → Backend | `connection` | Client hello (optional) |

---

## 📤 Backend → Extension Messages

### 1. Connection Acknowledgment

**Sent when**: Client first connects to WebSocket server

**Purpose**: Confirm successful connection and backend readiness

```json
{
  "type": "connection",
  "action": "connected",
  "message": "Successfully connected to fact-checker backend",
  "timestamp": "2025-10-18T14:30:45.123Z"
}
```

**Fields**:
- `type` (string, required): Always `"connection"`
- `action` (string, required): Always `"connected"`
- `message` (string, optional): Human-readable status message
- `timestamp` (string, required): ISO 8601 timestamp

**Extension Response**: Update UI to show "Connected" status with green indicator

---

### 2. Transcript Message

**Sent when**: Real-time speech is transcribed (continuously during meeting)

**Purpose**: Provide live captions/transcript to display in overlay

```json
{
  "type": "transcript",
  "timestamp": "2025-10-18T14:30:45.123Z",
  "data": {
    "text": "Python was released in 1991",
    "speaker": "John Doe",
    "is_final": true
  }
}
```

**Fields**:
- `type` (string, required): Always `"transcript"`
- `timestamp` (string, required): ISO 8601 timestamp of transcription
- `data` (object, required):
  - `text` (string, required): Transcribed speech text
  - `speaker` (string, optional): Speaker name/ID (default: "Speaker")
  - `is_final` (boolean, optional): Whether transcription is finalized (default: true)

**Extension Response**:
- Display text in live transcript overlay
- If `is_final` is false, show as "interim" (can be replaced)
- Auto-scroll to newest transcript

---

### 3. Verdict Message

**Sent when**: A factual claim is detected and verified

**Purpose**: Show inline fact-check alert with verdict and evidence

```json
{
  "type": "verdict",
  "timestamp": "2025-10-18T14:30:45.678Z",
  "data": {
    "transcript": "Python was released in 1991",
    "claim": "Python was released in 1991",
    "status": "supported",
    "confidence": 0.98,
    "rationale": "Official Python documentation confirms release in February 1991",
    "evidence_url": "https://www.python.org/doc/essays/foreword/",
    "speaker": "John Doe"
  }
}
```

**Fields**:
- `type` (string, required): Always `"verdict"`
- `timestamp` (string, required): ISO 8601 timestamp of verdict
- `data` (object, required):
  - `transcript` (string, required): Original transcript text this verdict relates to
  - `claim` (string, required): Extracted factual claim being verified
  - `status` (string, required): Verdict result (see status types below)
  - `confidence` (float, required): Confidence score 0.0-1.0
  - `rationale` (string, required): Explanation of verdict
  - `evidence_url` (string, optional): Source URL for evidence
  - `speaker` (string, optional): Speaker who made the claim

**Status Types**:
| Status | Icon | Color | Meaning | Display |
|--------|------|-------|---------|---------|
| `supported` | ✅ | Green | TRUE/Verified | **Don't show** (silent) |
| `contradicted` | ❌ | Red | FALSE/Incorrect | **Show alert** |
| `unclear` | ⚠️ | Yellow | Uncertain/Mixed | **Show alert** |
| `not_found` | ⚪ | Gray | No evidence | Optional (can hide) |

**Extension Response**:
- Match verdict to corresponding transcript item
- If status is NOT `"supported"`, display inline alert below transcript
- Show color-coded verdict box with rationale
- If `evidence_url` provided, show clickable link
- Display confidence score as percentage

---

## 📥 Extension → Backend Messages (Optional)

### Client Hello

**Sent when**: Extension connects (optional, for logging/tracking)

```json
{
  "type": "connection",
  "action": "connect",
  "client_id": "ext-chrome-abc123",
  "platform": "chrome",
  "version": "1.0.0"
}
```

**Fields**:
- `type` (string): Always `"connection"`
- `action` (string): Always `"connect"`
- `client_id` (string, optional): Unique client identifier
- `platform` (string, optional): Browser platform
- `version` (string, optional): Extension version

**Backend Response**: Not required (backend can log or ignore)

---

## 🔄 Message Flow Example

```
Extension                              Backend
   |                                      |
   |-- (WebSocket connect) ------------->|
   |                                      |
   |<-- connection (connected) ----------|
   |                                      |
   |                                      |  [User starts speaking]
   |<-- transcript -----------------------|  "Python was released..."
   |                                      |
   |                                      |  [Claim detected, searching...]
   |<-- verdict (supported) --------------|  ✅ TRUE
   |                                      |
   |                                      |  [User speaks again]
   |<-- transcript -----------------------|  "iPhone came out in 2008"
   |                                      |
   |                                      |  [Claim detected, fact-checking...]
   |<-- verdict (contradicted) -----------|  ❌ FALSE
   |                                      |
```

---

## 🔧 Backend Implementation Requirements

### What the Backend MUST Provide

1. **WebSocket Server**
   - Listen on `ws://localhost:8765`
   - Handle multiple concurrent connections
   - Broadcast messages to all connected clients

2. **Connection Handling**
   - Send `connection` message when client connects
   - Handle disconnections gracefully
   - Support reconnection

3. **Message Broadcasting**
   - Send `transcript` messages continuously during speech
   - Send `verdict` messages when claims are fact-checked
   - Include proper timestamps (ISO 8601 format)

4. **Message Ordering**
   - Send `transcript` BEFORE corresponding `verdict`
   - Ensure `verdict.data.transcript` matches previously sent transcript

### What the Backend RECEIVES from Extension

- **Connection Establishment**: Standard WebSocket handshake
- **Optional Client Hello**: Can be logged/ignored
- **Keep-Alive**: WebSocket ping/pong (automatic)

---

## 📋 Backend Input/Output Summary

### Backend INPUTS (What Backend Needs to Do)

1. **Capture system audio** (using sounddevice or similar)
2. **Transcribe audio to text** (using Groq Whisper STT)
3. **Extract factual claims** (using LLM)
4. **Search for evidence** (using Exa web search)
5. **Generate verdict** (using LLM to evaluate evidence)

### Backend OUTPUTS (What Backend Sends to Extension)

1. **Continuous transcript stream** → `transcript` messages
2. **Fact-check results** → `verdict` messages
3. **Connection status** → `connection` messages

---

## 🚨 Error Handling

### Connection Errors

If backend is not running:
- Extension shows "Disconnected" status
- WebSocket auto-reconnects every 1-30 seconds (exponential backoff)

### Invalid Messages

If backend sends malformed JSON:
- Extension logs error to console
- Extension continues listening for next valid message

### Missing Fields

If required fields are missing:
- Extension uses defaults:
  - `speaker`: "Speaker"
  - `is_final`: true
  - `confidence`: null (hide confidence score)

---

## 🧪 Testing with Mock Data

### Example Test Server (Python)

```python
import asyncio
import websockets
import json
from datetime import datetime

connected_clients = set()

async def handle_client(websocket, path):
    connected_clients.add(websocket)
    print(f"✅ Client connected ({len(connected_clients)} total)")

    # Send connection message
    await websocket.send(json.dumps({
        "type": "connection",
        "action": "connected",
        "message": "Test server connected",
        "timestamp": datetime.now().isoformat()
    }))

    # Send test transcript
    await asyncio.sleep(2)
    await websocket.send(json.dumps({
        "type": "transcript",
        "timestamp": datetime.now().isoformat(),
        "data": {
            "text": "The iPhone was released in 2008",
            "speaker": "Test User",
            "is_final": True
        }
    }))

    # Send test verdict
    await asyncio.sleep(1)
    await websocket.send(json.dumps({
        "type": "verdict",
        "timestamp": datetime.now().isoformat(),
        "data": {
            "transcript": "The iPhone was released in 2008",
            "claim": "The iPhone was released in 2008",
            "status": "contradicted",
            "confidence": 0.95,
            "rationale": "The first iPhone was actually released on June 29, 2007",
            "evidence_url": "https://www.apple.com/newsroom/2007/06/29Apple-Reinvents-the-Phone-with-iPhone/",
            "speaker": "Test User"
        }
    }))

    await websocket.wait_closed()
    connected_clients.remove(websocket)
    print(f"❌ Client disconnected ({len(connected_clients)} total)")

async def main():
    server = await websockets.serve(handle_client, "localhost", 8765)
    print("🚀 Test WebSocket server running on ws://localhost:8765")
    await server.wait_closed()

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 📊 Performance Expectations

| Metric | Expected Value |
|--------|---------------|
| Transcript latency | < 500ms after speech ends |
| Verdict latency | 2-5 seconds after claim spoken |
| Message size | < 5KB per message |
| Connection uptime | 99%+ during meeting |
| Max concurrent clients | 10+ simultaneous connections |

---

## 🔐 Security Considerations

1. **Local Only**: Server MUST run on localhost only (not exposed to internet)
2. **No Authentication**: Not required for localhost connections
3. **HTTPS Not Required**: WebSocket uses `ws://` not `wss://` (local only)
4. **CORS**: Not applicable (WebSocket from extension, not webpage)

---

## 📞 Integration Checklist

### For Backend Developer (Developer A & B)

- [ ] Create WebSocket server on port 8765
- [ ] Send `connection` message on client connect
- [ ] Send `transcript` messages continuously (every speech chunk)
- [ ] Send `verdict` messages when claim is fact-checked
- [ ] Include all required fields in each message type
- [ ] Use ISO 8601 timestamps
- [ ] Handle multiple concurrent connections
- [ ] Test with extension by loading unpacked

### For Extension Developer (Developer C - You!)

- [x] Connect to `ws://localhost:8765`
- [x] Handle `connection` messages (update UI status)
- [x] Handle `transcript` messages (display in overlay)
- [x] Handle `verdict` messages (show inline alerts)
- [x] Filter out `supported` verdicts (only show problems)
- [x] Auto-reconnect on disconnect
- [x] Show connection status indicator

---

## 📚 References

- WebSocket RFC: https://datatracker.ietf.org/doc/html/rfc6455
- Python websockets: https://websockets.readthedocs.io/
- Chrome Extension Messaging: https://developer.chrome.com/docs/extensions/mv3/messaging/

---

**Ready to integrate! 🚀**

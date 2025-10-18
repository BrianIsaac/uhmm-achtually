# AI Meeting Assistant - Chrome Extension Architecture

**WOW Factor**: Live fact-checking overlay on ANY video call (Zoom, Google Meet, Teams)

---

## 🎯 Vision

A Chrome extension that adds **real-time AI-powered fact-checking** directly into video conferencing platforms. As people speak, their claims are transcribed, verified, and displayed as live captions with color-coded accuracy indicators.

### The User Experience

1. User installs Chrome extension
2. User joins Zoom/Meet/Teams call
3. Extension detects video call and shows **live transcript overlay**
4. As people speak:
   - **Live transcript shows all spoken text** (like real-time captions)
   - **False/questionable claims are highlighted inline** with color-coding
   - Claims marked: ❌ Red (FALSE) | ⚠️ Yellow (UNCLEAR)
   - Click highlighted claim → Expand to see evidence, sources, and corrections
   - Hover → See confidence score and rationale
   - True statements → No highlighting (clean, readable transcript)

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      USER'S BROWSER                              │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │           Video Conference Tab (Zoom/Meet/Teams)          │  │
│  │                                                            │  │
│  │  ┌─────────────────────────────────────────────────┐     │  │
│  │  │  Video Feed                                      │     │  │
│  │  │                                                   │     │  │
│  │  │  ┌────────────────────────────────────────────┐ │     │  │
│  │  │  │  LIVE TRANSCRIPT + FACT-CHECKS           │ │     │  │
│  │  │  │                                             │ │     │  │
│  │  │  │  Speaker: "Let me tell you about..."     │ │     │  │
│  │  │  │  Speaker: "iPhone was released in 2008"   │ │     │  │
│  │  │  │           ❌ FALSE - Actually 2007         │ │     │  │
│  │  │  │  Speaker: "It changed everything..."      │ │     │  │
│  │  │  └────────────────────────────────────────────┘ │     │  │
│  │  └─────────────────────────────────────────────────┘     │  │
│  └──────────────────────────────────────────────────────────┘  │
│                            ▲                                     │
│                            │ inject overlay                      │
│                            │                                     │
│  ┌────────────────────────┴──────────────────────────────────┐ │
│  │            Chrome Extension (Background Service)           │ │
│  │                                                             │ │
│  │  - WebSocket Client                                        │ │
│  │  - Verdict Storage                                         │ │
│  │  - Message Router                                          │ │
│  └────────────────────────┬──────────────────────────────────┘ │
│                            │                                     │
└────────────────────────────┼─────────────────────────────────────┘
                             │ WebSocket
                             │ ws://localhost:8765
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│                    PYTHON BACKEND SERVER                          │
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  WebSocket Server (Port 8765)                              │ │
│  │  - Broadcasts verdicts to all connected clients            │ │
│  └────────────────────────────────────────────────────────────┘ │
│                            ▲                                     │
│                            │                                     │
│  ┌────────────────────────┴──────────────────────────────────┐ │
│  │           Fact-Checking Pipeline                           │ │
│  │                                                             │ │
│  │  ┌───────────┐   ┌──────────┐   ┌──────────┐             │ │
│  │  │ System    │   │  Claim   │   │   Web    │             │ │
│  │  │ Audio     ├──►│ Extract  ├──►│  Search  ├───┐         │ │
│  │  │ Capture   │   │  (LLM)   │   │  (Exa)   │   │         │ │
│  │  └───────────┘   └──────────┘   └──────────┘   │         │ │
│  │       │                                          │         │ │
│  │       ▼                                          ▼         │ │
│  │  ┌───────────┐                         ┌──────────────┐   │ │
│  │  │   STT     │                         │   Verdict    │   │ │
│  │  │  (Groq    │                         │  Generator   │   │ │
│  │  │  Whisper) │                         │    (LLM)     │   │ │
│  │  └───────────┘                         └──────────────┘   │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  Dependencies:                                                    │
│  - websockets (Python WebSocket server)                         │
│  - sounddevice (System audio capture)                           │
│  - groq (STT + LLM)                                             │
│  - exa_py (Web search)                                          │
└──────────────────────────────────────────────────────────────────┘
```

---

## 📦 Component Breakdown

### 1. Chrome Extension Components

#### **Manifest (manifest.json)**
- Defines extension permissions
- Declares content scripts and background service worker
- Specifies host permissions for video platforms

#### **Content Script (content.js)**
- Injected into Zoom/Meet/Teams pages
- Creates overlay UI (live transcript box)
- Receives two types of messages:
  - **Transcript chunks** → Display as captions
  - **Verdict alerts** → Highlight inline with color-coding
- Handles user interactions (click to expand, hover for details)

#### **Background Service Worker (background.js)**
- Persistent WebSocket connection to Python backend
- Receives verdict messages
- Routes verdicts to active tab's content script
- Manages extension state

#### **Popup UI (popup.html + popup.js)**
- Extension icon dropdown
- Settings:
  - Backend URL (default: ws://localhost:8765)
  - Enable/Disable overlay
  - Overlay position (top/bottom)
  - Notification style
- Connection status indicator

---

### 2. WebSocket Message Protocol

#### **Message Format (Backend → Extension)**

**Transcript Message** (sent continuously):
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

**Verdict Message** (sent when claim detected):
```json
{
  "type": "verdict",
  "timestamp": "2025-10-18T14:30:45.123Z",
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

#### **Status Types** (Only shown if problematic)
- `contradicted` → ❌ Red → FALSE (Show with correction)
- `unclear` → ⚠️ Yellow → NEEDS VERIFICATION (Show with context)
- `not_found` → ⚪ Gray → NO DATA (Optional: can hide)
- `supported` → ✅ No alert shown (Silent - don't interrupt)

#### **Connection Messages**

```json
// Client connects
{
  "type": "connection",
  "action": "connect",
  "client_id": "ext-chrome-abc123"
}

// Server acknowledges
{
  "type": "connection",
  "action": "connected",
  "message": "Successfully connected to fact-checker backend"
}
```

---

### 3. Backend WebSocket Server

#### **Python Server (websocket_server.py)**

```python
import asyncio
import websockets
import json
from typing import Set

# Store connected clients
connected_clients: Set[websockets.WebSocketServerProtocol] = set()

async def handle_client(websocket, path):
    """Handle new client connection"""
    connected_clients.add(websocket)
    print(f"✅ Client connected. Total: {len(connected_clients)}")

    try:
        # Send welcome message
        await websocket.send(json.dumps({
            "type": "connection",
            "action": "connected",
            "message": "Successfully connected to fact-checker backend"
        }))

        # Keep connection alive
        await websocket.wait_closed()
    finally:
        connected_clients.remove(websocket)
        print(f"❌ Client disconnected. Total: {len(connected_clients)}")

async def broadcast_verdict(verdict: dict):
    """Broadcast verdict to all connected clients"""
    if not connected_clients:
        return

    message = json.dumps({
        "type": "verdict",
        "timestamp": datetime.now().isoformat(),
        "data": verdict
    })

    # Send to all clients
    await asyncio.gather(
        *[client.send(message) for client in connected_clients],
        return_exceptions=True
    )
    print(f"📤 Broadcasted verdict to {len(connected_clients)} clients")

async def main():
    """Start WebSocket server"""
    server = await websockets.serve(handle_client, "localhost", 8765)
    print("🚀 WebSocket server running on ws://localhost:8765")
    await server.wait_closed()

if __name__ == "__main__":
    asyncio.run(main())
```

---

### 4. Overlay UI Design

#### **Caption Box Styles**

```css
.fact-check-overlay {
  position: fixed;
  bottom: 80px;
  left: 50%;
  transform: translateX(-50%);
  width: 80%;
  max-width: 800px;
  background: rgba(0, 0, 0, 0.9);
  backdrop-filter: blur(10px);
  border-radius: 12px;
  padding: 16px;
  z-index: 999999;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto;
  animation: slideUp 0.3s ease-out;
}

.verdict-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 12px;
  padding: 12px;
  border-radius: 8px;
  transition: all 0.2s;
}

.verdict-item:hover {
  background: rgba(255, 255, 255, 0.05);
}

/* Status colors - Only show problematic claims */
.status-contradicted {
  border-left: 4px solid #ef4444;
  background: rgba(239, 68, 68, 0.1);
}

.status-unclear {
  border-left: 4px solid #f59e0b;
  background: rgba(245, 158, 11, 0.1);
}

.status-not_found {
  border-left: 4px solid #6b7280;
  background: rgba(107, 114, 128, 0.05);
}

/* supported status is filtered out - never shown */
```

---

## 🎨 Visual Design

### Overlay Mockup

```
┌──────────────────────────────────────────────────────────────┐
│  📝 Live Meeting Transcript                      [Settings]  │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  Speaker: "Let me tell you about mobile technology..."       │
│                                                               │
│  Speaker: "The first iPhone came out in 2008"                │
│  ❌ FALSE • 92% confidence                                   │
│     Correction: Released June 29, 2007                       │
│     Source: apple.com/newsroom [View]                        │
│                                                               │
│  Speaker: "It completely changed the industry..."            │
│                                                               │
│  Speaker: "AI will replace all jobs by 2030"                 │
│  ⚠️ UNCLEAR • 45% confidence                                 │
│     Mixed evidence, expert opinions vary [Details]           │
│                                                               │
│  Speaker: "But we need to prepare for it..."                 │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

---

## 🚀 Implementation Timeline (12 hours)

### Phase 1: Chrome Extension Scaffold (1 hour)
- ✅ Create manifest.json
- ✅ Basic popup UI
- ✅ Content script injection
- ✅ Background service worker

### Phase 2: WebSocket Client (1 hour)
- ✅ Connect to backend
- ✅ Receive messages
- ✅ Handle reconnection
- ✅ Error handling

### Phase 3: Overlay UI (2 hours)
- ✅ Inject caption box
- ✅ Style verdicts
- ✅ Animations
- ✅ Click interactions

### Phase 4: Backend Integration (1 hour)
- ✅ WebSocket server
- ✅ Broadcast verdicts
- ✅ Test with mock data

### Phase 5: Testing & Polish (2 hours)
- ✅ Test on Zoom/Meet
- ✅ Fix styling issues
- ✅ Performance optimization
- ✅ Error states

### Phase 6: Demo Preparation (2 hours)
- ✅ Record demo video
- ✅ Prepare test data
- ✅ Create slides
- ✅ Practice pitch

### Phase 7: Buffer (3 hours)
- Unexpected issues
- Additional features
- Extra polish

---

## 🎯 Key Features for WOW Factor

### Must-Have (Core)
1. ✅ Live transcript overlay (all spoken text)
2. ✅ Inline fact-check alerts (highlighted false/unclear claims)
3. ✅ Color-coded verdicts (red/yellow/gray)
4. ✅ Click to expand/see sources and corrections
5. ✅ Works on Zoom/Meet/Teams

### Nice-to-Have (Impressive)
1. 🌟 Smooth animations (fade in/out)
2. 🌟 Confidence score display
3. 🌟 Historical verdicts (scroll)
4. 🌟 Keyboard shortcuts (toggle overlay)
5. 🌟 Dark/Light mode
6. 🌟 Export meeting summary

### Stretch Goals (Super WOW)
1. 🚀 AI voice synthesis (read verdicts aloud)
2. 🚀 Real-time meeting stats (accuracy score)
3. 🚀 Multiple language support
4. 🚀 Team collaboration (shared verdicts)

---

## 📝 File Structure

```
cursor-hackathon/
├── extension/                  # Chrome Extension
│   ├── manifest.json          # Extension config
│   ├── icons/                 # Extension icons
│   │   ├── icon16.png
│   │   ├── icon48.png
│   │   └── icon128.png
│   ├── popup/                 # Extension popup
│   │   ├── popup.html
│   │   ├── popup.js
│   │   └── popup.css
│   ├── content/               # Content scripts
│   │   ├── content.js         # Main overlay logic
│   │   └── content.css        # Overlay styles
│   ├── background/            # Background service
│   │   └── background.js      # WebSocket client
│   └── utils/                 # Shared utilities
│       └── websocket.js       # WebSocket helper
│
├── backend/                   # Python Backend
│   ├── websocket_server.py   # WebSocket server
│   ├── fact_checker.py       # Fact-checking pipeline
│   ├── audio_capture.py      # System audio capture
│   └── requirements.txt      # Python dependencies
│
└── docs/                      # Documentation
    ├── CHROME_EXTENSION_ARCHITECTURE.md
    └── DEMO_SCRIPT.md
```

---

## 🔧 Technical Details

### Extension Permissions Required

```json
{
  "permissions": [
    "activeTab",
    "storage"
  ],
  "host_permissions": [
    "https://zoom.us/*",
    "https://*.zoom.us/*",
    "https://meet.google.com/*",
    "https://teams.microsoft.com/*"
  ]
}
```

### WebSocket Connection Handling

```javascript
class FactCheckWebSocket {
  constructor(url = 'ws://localhost:8765') {
    this.url = url;
    this.ws = null;
    this.reconnectDelay = 1000;
    this.maxReconnectDelay = 30000;
  }

  connect() {
    this.ws = new WebSocket(this.url);

    this.ws.onopen = () => {
      console.log('✅ Connected to fact-checker backend');
      this.reconnectDelay = 1000;
    };

    this.ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      this.handleMessage(message);
    };

    this.ws.onerror = (error) => {
      console.error('❌ WebSocket error:', error);
    };

    this.ws.onclose = () => {
      console.log('🔌 Connection closed. Reconnecting...');
      this.reconnect();
    };
  }

  reconnect() {
    setTimeout(() => {
      this.reconnectDelay = Math.min(
        this.reconnectDelay * 2,
        this.maxReconnectDelay
      );
      this.connect();
    }, this.reconnectDelay);
  }

  handleMessage(message) {
    if (message.type === 'verdict') {
      // Send to content script
      chrome.tabs.query({ active: true }, (tabs) => {
        chrome.tabs.sendMessage(tabs[0].id, {
          type: 'new-verdict',
          verdict: message.data
        });
      });
    }
  }
}
```

---

## 🎬 Demo Script

### Setup (Before Demo)
1. Start Python backend: `python websocket_server.py`
2. Load Chrome extension
3. Open Zoom/Meet test room
4. Prepare test claims

### Demo Flow (5 minutes)
1. **Introduction** (30s)
   - Show problem: Misinformation in meetings
   - Show solution: AI fact-checker extension

2. **Installation** (30s)
   - Click extension icon
   - Show it's enabled
   - Show settings

3. **Live Demo** (3 min)
   - Join video call
   - Speak test claim: "Python was released in 1991"
   - Show: ✅ TRUE appears in overlay
   - Speak false claim: "iPhone came out in 2008"
   - Show: ❌ FALSE appears with correction
   - Click verdict → Show source link

4. **Features Highlight** (1 min)
   - Works on any platform (Zoom/Meet/Teams)
   - Real-time verification
   - Source citations
   - Easy to install

5. **Impact** (30s)
   - Combat misinformation
   - Increase meeting accuracy
   - Build trust in discussions

---

## 🏆 Why This Will Win

1. **Practical** → Solves real problem
2. **Impressive** → Live demo on real video calls
3. **Technical** → Multiple technologies (Extension, WebSocket, AI)
4. **Polished** → Beautiful UI with animations
5. **Accessible** → Easy to install and use
6. **Scalable** → Works with any video platform

---

## 📚 Resources

- Chrome Extension Docs: https://developer.chrome.com/docs/extensions/
- WebSocket API: https://developer.mozilla.org/en-US/docs/Web/API/WebSocket
- Python websockets: https://websockets.readthedocs.io/
- Groq API: https://console.groq.com/docs
- Exa API: https://docs.exa.ai/

---

**Let's build this! 🚀**

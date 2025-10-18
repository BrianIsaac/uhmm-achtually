# Uhmm Actually - Chrome Extension

Real-time AI-powered fact-checking overlay for video meetings (Zoom, Google Meet, Microsoft Teams).

## Features

✅ **Live Transcript** - See what everyone is saying in real-time
❌ **Fact-Check Alerts** - False claims highlighted inline with corrections
⚠️ **Uncertainty Warnings** - Unclear claims flagged for verification
🔗 **Source Citations** - Click to see evidence and sources

## Installation

### 1. Load Extension in Chrome

1. Open Chrome and go to `chrome://extensions/`
2. Enable **Developer mode** (toggle in top-right)
3. Click **Load unpacked**
4. Select the `chrome-extension` folder
5. Extension icon should appear in toolbar!

### 2. Start Backend Server

Make sure the Python WebSocket server is running:

```bash
cd backend
python websocket_server.py
```

### 3. Join a Meeting

1. Open Zoom, Google Meet, or Microsoft Teams
2. Join a meeting
3. Live transcript overlay will appear automatically!

## How It Works

```
Speech → Backend STT → Claim Extraction → Web Search → Verdict → Overlay
```

1. **You speak** in a meeting
2. **Backend captures** system audio
3. **Groq Whisper** transcribes to text
4. **LLM extracts** factual claims
5. **Exa searches** web for evidence
6. **Verdict sent** via WebSocket
7. **Overlay shows** transcript + inline alerts

## File Structure

```
chrome-extension/
├── manifest.json          # Extension config
├── background/
│   └── background.js     # WebSocket client
├── content/
│   ├── content.js        # Overlay logic
│   └── content.css       # Overlay styles
├── popup/
│   ├── popup.html        # Settings UI
│   ├── popup.js          # Settings logic
│   └── popup.css         # Settings styles
└── icons/
    ├── icon16.png
    ├── icon48.png
    └── icon128.png
```

## Supported Platforms

- ✅ Zoom (zoom.us)
- ✅ Google Meet (meet.google.com)
- ✅ Microsoft Teams (teams.microsoft.com)

## Keyboard Shortcuts

- **Click minimize** - Hide/show transcript
- **Scroll** - View transcript history
- **Click verdict** - Expand details and sources

## Troubleshooting

### "Disconnected" Status

- Make sure Python backend is running on `ws://localhost:8765`
- Check browser console for errors
- Click "Reconnect" in extension popup

### Overlay Not Appearing

- Refresh the meeting page
- Check extension is enabled in `chrome://extensions/`
- Verify content script loaded in DevTools

### No Transcripts Showing

- Backend needs to capture system audio
- Check backend console for STT errors
- Verify WebSocket connection is open

## Development

### Testing Messages

Send test messages to the extension:

```javascript
// In browser console
chrome.runtime.sendMessage({
  type: 'transcript',
  data: {
    text: 'Hello world',
    speaker: 'Test User'
  }
});
```

### Message Format

**Transcript:**
```json
{
  "type": "transcript",
  "data": {
    "text": "Python was released in 1991",
    "speaker": "John Doe"
  }
}
```

**Verdict:**
```json
{
  "type": "verdict",
  "data": {
    "transcript": "Python was released in 1991",
    "claim": "Python was released in 1991",
    "status": "contradicted",
    "confidence": 0.92,
    "rationale": "Python was actually released in February 1991",
    "evidence_url": "https://python.org"
  }
}
```

## License

MIT

---

**Built for [Hackathon Name] 2025** 🚀

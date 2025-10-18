# Meeting BaaS Transcriber

Minimal implementation for transcribing Zoom meetings using the Meeting BaaS API.

## Features

- 🤖 Automated bot creation to join Zoom/Teams/Google Meet
- 📝 Automatic transcription with speaker diarisation
- 🔗 Webhook server to receive real-time transcription events
- 💾 Local transcript storage in text format
- 🚇 Ngrok integration for local webhook testing

## Prerequisites

Before you begin, you'll need:

### 1. Meeting BaaS API Key

1. Sign up at [meetingbaas.com](https://www.meetingbaas.com)
2. Get your API key from the dashboard
3. Free tier includes 4 hours of transcription

### 2. Ngrok Auth Token (Optional - for webhook testing)

1. Sign up at [ngrok.com](https://ngrok.com)
2. Get your auth token from the dashboard
3. Free tier is sufficient for testing

### 3. Python 3.12+

Ensure you have Python 3.12 or higher installed:

```bash
python --version
```

## Installation

### 1. Navigate to the project directory

```bash
cd meeting-baas-transcriber
```

### 2. Install dependencies using uv

```bash
uv pip install -e .
```

### 3. Configure environment variables

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` and add your credentials:

```env
# Required
MEETING_BAAS_API_KEY=your_meeting_baas_api_key_here

# Optional (for webhook testing)
NGROK_AUTH_TOKEN=your_ngrok_auth_token_here

# Bot configuration (optional)
BOT_NAME=Transcription Bot
ENTRY_MESSAGE=Hi, I'm here to transcribe this meeting.
```

## Usage

### Quick Start: Transcribe a Zoom Meeting

#### Option 1: Without Webhooks (Polling)

**Step 1:** Create a bot to join the meeting

```bash
python create_bot.py https://zoom.us/j/YOUR_MEETING_ID
```

**Step 2:** Check bot status and get transcript

```bash
# Get bot ID from previous command output
python check_bot.py <bot_id>
```

#### Option 2: With Webhooks (Real-time - Recommended)

**Step 1:** Start the webhook server with ngrok

```bash
python run_server.py --ngrok
```

This will output:

```
✅ Ngrok tunnel active!
================================================================================
📍 Public URL: https://abc123.ngrok.io
🔗 Webhook URL: https://abc123.ngrok.io/webhooks/meetingbaas
================================================================================
```

**Step 2:** Create a bot with the webhook URL

In a **new terminal window**:

```bash
python create_bot.py https://zoom.us/j/YOUR_MEETING_ID https://abc123.ngrok.io/webhooks/meetingbaas
```

**Step 3:** Join the meeting and speak

The bot will join the meeting and start transcribing. When the meeting ends, you'll see:

```
🎬 Meeting completed: https://zoom.us/j/YOUR_MEETING_ID
   Bot ID: abc123

📝 Transcript (15 utterances):
================================================================================
[00:00] Speaker 1:
  Hello everyone, welcome to the meeting.

[00:05] Speaker 2:
  Thanks for having me. Let's discuss the project timeline.

[00:12] Speaker 1:
  Sure, I think we should aim for a Q2 launch.
================================================================================

💾 Transcript saved to: logs/transcripts/transcript_abc123_20251018_143022.txt
```

### Advanced Usage

#### Run server locally (without ngrok)

```bash
python run_server.py
```

**Note:** This only works for localhost testing. External services cannot reach your webhook.

#### List all bots

```bash
python -c "import asyncio; from src.meeting_baas_client import MeetingBaaSClient; asyncio.run(MeetingBaaSClient().list_bots())"
```

#### Stop a bot manually

```bash
python -c "import asyncio; from src.meeting_baas_client import MeetingBaaSClient; asyncio.run(MeetingBaaSClient().stop_bot('bot_id_here'))"
```

## Project Structure

```
meeting-baas-transcriber/
├── src/
│   ├── __init__.py
│   ├── config.py              # Environment configuration
│   ├── models.py              # Pydantic data models
│   ├── meeting_baas_client.py # Meeting BaaS API client
│   └── webhook_server.py      # FastAPI webhook server
├── logs/
│   ├── transcripts/           # Saved transcript files
│   └── webhook_*.jsonl        # Raw webhook event logs
├── create_bot.py              # CLI: Create a bot
├── check_bot.py               # CLI: Check bot status
├── run_server.py              # CLI: Run webhook server
├── pyproject.toml             # Python dependencies
├── .env                       # Environment variables (you create this)
└── README.md                  # This file
```

## Webhook Events

The webhook server receives the following events:

### `meeting.started`

Triggered when the bot successfully joins the meeting.

```json
{
  "event": "meeting.started",
  "bot_id": "abc123",
  "meeting_url": "https://zoom.us/j/123456789",
  "timestamp": "2025-10-18T14:30:00Z"
}
```

### `meeting.completed`

Triggered when the meeting ends. Contains the full transcript.

```json
{
  "event": "meeting.completed",
  "bot_id": "abc123",
  "meeting_url": "https://zoom.us/j/123456789",
  "timestamp": "2025-10-18T15:00:00Z",
  "data": {
    "duration": 1800,
    "recording_url": "https://...",
    "transcript": [
      {
        "speaker": "Speaker 1",
        "text": "Hello everyone",
        "start_time": 0.0,
        "end_time": 2.5,
        "words": [...]
      }
    ]
  }
}
```

### `meeting.failed`

Triggered if the bot fails to join the meeting.

```json
{
  "event": "meeting.failed",
  "bot_id": "abc123",
  "meeting_url": "https://zoom.us/j/123456789",
  "timestamp": "2025-10-18T14:30:00Z",
  "data": {
    "error": "Meeting not found"
  }
}
```

## API Reference

### MeetingBaaSClient

```python
from src.meeting_baas_client import MeetingBaaSClient

client = MeetingBaaSClient()

# Create bot
response = await client.create_bot(
    meeting_url="https://zoom.us/j/123456789",
    webhook_url="https://your-server.com/webhook",
    bot_name="Custom Bot Name",
    recording_mode="audio_only",  # or "speaker_view", "gallery_view"
)

# Check status
status = await client.get_bot_status(bot_id)

# Stop bot
await client.stop_bot(bot_id)

# List all bots
bots = await client.list_bots()
```

## Troubleshooting

### Bot not joining the meeting

**Possible causes:**

1. **Invalid meeting URL** - Ensure the URL is correct
2. **Waiting room enabled** - Bot will wait (600s timeout by default)
3. **Meeting hasn't started** - Start the meeting first

### Webhook not receiving events

**Possible causes:**

1. **ngrok tunnel expired** - Free ngrok tunnels expire after 2 hours
2. **Incorrect webhook URL** - Check the URL in `create_bot.py` output
3. **Firewall blocking** - Ensure port 8000 is accessible

### Transcription accuracy issues

Meeting BaaS uses Gladia's Whisper-Zero with 95% accuracy. For better results:

- Ensure clear audio (use headset/microphone)
- Minimise background noise
- Speak clearly with distinct speakers

## Cost Estimation

Meeting BaaS pricing (as of October 2025):

- **Free tier**: 4 hours included
- **Pay-as-you-go**: $0.69/hour
- **Transcription**: Included with Gladia Whisper-Zero

Example costs:

- 10 hours/month: $6.90 (after free tier)
- 100 hours/month: $69.00

## Next Steps

### Integration with Fact-Checking Bot

To integrate with your existing fact-checking pipeline:

1. **Process transcripts in real-time**:

```python
# In webhook_server.py, modify handle_meeting_completed:
async def handle_meeting_completed(event: WebhookEvent):
    transcript_data = event.data.get("transcript", [])

    # Process each utterance through your pipeline
    for utterance in transcript_data:
        text = utterance["text"]

        # Extract claims
        claims = await extract_claims(text)

        # Verify claims
        for claim in claims:
            verdict = await verify_claim(claim)
            print(f"Claim: {claim}")
            print(f"Verdict: {verdict}")
```

2. **Self-host Meeting BaaS** (optional):

For production, consider self-hosting to eliminate per-hour costs. See Meeting BaaS documentation.

## Licence

This implementation is for demonstration purposes. Meeting BaaS is licensed under BSL (converts to Apache 2.0 after 18 months).

## Support

- Meeting BaaS Documentation: [docs.meetingbaas.com](https://docs.meetingbaas.com)
- Meeting BaaS GitHub: [github.com/Meeting-Baas](https://github.com/Meeting-Baas)
- Issues: Open an issue in this repository

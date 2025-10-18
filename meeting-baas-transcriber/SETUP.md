# Quick Setup Guide

## What You Need to Provide

Before running this implementation, you need to obtain:

### 1. Meeting BaaS API Key (REQUIRED)

**Where to get it:**
1. Visit [meetingbaas.com](https://www.meetingbaas.com)
2. Click "Sign Up" or "Get Started"
3. Create an account
4. Navigate to your dashboard
5. Copy your API key

**Cost:**
- Free tier: 4 hours included
- Pay-as-you-go: $0.69/hour after free tier

**Add to `.env` file:**
```env
MEETING_BAAS_API_KEY=your_actual_api_key_here
```

### 2. Ngrok Auth Token (OPTIONAL - for webhook testing)

**Where to get it:**
1. Visit [ngrok.com](https://ngrok.com)
2. Sign up for a free account
3. Go to "Your Authtoken" in dashboard
4. Copy the auth token

**Cost:**
- Free tier is sufficient for testing
- No payment required

**Add to `.env` file (optional):**
```env
NGROK_AUTH_TOKEN=your_ngrok_token_here
```

**When you need this:**
- Only if you want to test webhooks locally
- Not required if you're just polling bot status
- Skip this if you're deploying to a server with a public URL

### 3. Zoom Meeting URL (for testing)

**How to get one:**

**Option A: Create your own test meeting**
1. Go to [zoom.us](https://zoom.us)
2. Sign in (free account works)
3. Click "Schedule a Meeting" or "Host a Meeting"
4. Copy the meeting URL (e.g., `https://zoom.us/j/123456789`)

**Option B: Use someone else's meeting**
- Get permission from the host first
- Make sure they're okay with a bot joining

## Installation Steps

### 1. Navigate to the folder

```bash
cd meeting-baas-transcriber
```

### 2. Create `.env` file

```bash
cp .env.example .env
```

### 3. Edit `.env` with your credentials

```bash
# Using your favourite editor (nano, vim, vscode, etc.)
nano .env
```

Add your Meeting BaaS API key:

```env
MEETING_BAAS_API_KEY=mbsk_1234567890abcdefghijklmnopqrstuvwxyz

# Optional: Add ngrok token if testing webhooks
NGROK_AUTH_TOKEN=2abcDEF3ghiJKL4mnoPQR5stuVWX6yza_7BcdEFGhijKLMNOpqrSTUV
```

### 4. Install dependencies

```bash
uv pip install -e .
```

You should see:

```
Resolved X packages in Xms
Installed X packages in Xms
```

## Verify Installation

Check that everything is set up correctly:

```bash
python -c "from src.config import settings; print(f'API Key configured: {bool(settings.meeting_baas_api_key)}')"
```

Expected output:

```
API Key configured: True
```

## Test the Implementation

### Minimal Test (No Webhooks)

**Step 1:** Create a test Zoom meeting

- Go to [zoom.us](https://zoom.us) and create a meeting
- Copy the meeting URL

**Step 2:** Create a bot

```bash
python create_bot.py https://zoom.us/j/YOUR_MEETING_ID
```

Expected output:

```
🤖 Creating Meeting BaaS bot...
📍 Meeting URL: https://zoom.us/j/YOUR_MEETING_ID
⚠️  No webhook URL provided - you won't receive real-time events

✅ Bot created successfully!
   Bot ID: bot_abc123def456
   Status: pending
   Meeting URL: https://zoom.us/j/YOUR_MEETING_ID

📝 Next steps:
   1. The bot will join the meeting shortly
   2. Transcription will begin automatically
   3. Check bot status with: python check_bot.py bot_abc123def456
```

**Step 3:** Join the meeting yourself

- Click the Zoom meeting link
- Wait for the bot to join (shows as "Transcription Bot")
- Say something: "This is a test of the transcription system"

**Step 4:** Check bot status

```bash
python check_bot.py bot_abc123def456
```

You should see the bot status and potentially transcript data.

### Full Test (With Webhooks)

**Step 1:** Start webhook server

```bash
python run_server.py --ngrok
```

You'll see:

```
✅ Ngrok tunnel active!
================================================================================
📍 Public URL: https://abc123.ngrok.io
🔗 Webhook URL: https://abc123.ngrok.io/webhooks/meetingbaas
================================================================================
```

**Step 2:** Create a bot with webhook (in a new terminal)

```bash
python create_bot.py https://zoom.us/j/YOUR_MEETING_ID https://abc123.ngrok.io/webhooks/meetingbaas
```

**Step 3:** Join the meeting and speak

**Step 4:** Watch the webhook server terminal

You should see real-time events:

```
✅ Bot bot_abc123def456 joined meeting: https://zoom.us/j/YOUR_MEETING_ID
   Timestamp: 2025-10-18T14:30:00Z
```

**Step 5:** End the meeting

The webhook server will show the complete transcript:

```
🎬 Meeting completed: https://zoom.us/j/YOUR_MEETING_ID
   Bot ID: bot_abc123def456

📝 Transcript (3 utterances):
================================================================================
[00:00] Speaker 1:
  This is a test of the transcription system

[00:05] Speaker 1:
  Meeting BaaS is working correctly

[00:10] Speaker 1:
  Goodbye everyone
================================================================================

💾 Transcript saved to: logs/transcripts/transcript_bot_abc123def456_20251018_143022.txt
```

## Common Issues

### "API Key not configured"

**Solution:** Make sure `.env` file exists and contains:

```env
MEETING_BAAS_API_KEY=your_key_here
```

### "Bot failed to join meeting"

**Possible causes:**
1. Meeting hasn't started yet - start the meeting first
2. Waiting room enabled - admit the bot manually
3. Invalid meeting URL - double-check the URL

### "Webhook not receiving events"

**Solutions:**
1. Make sure you're running `run_server.py --ngrok`
2. Use the exact webhook URL from the ngrok output
3. Check that ngrok tunnel is still active (expires after 2 hours on free tier)

### "ModuleNotFoundError: No module named 'src'"

**Solution:** Make sure you're in the `meeting-baas-transcriber` directory:

```bash
cd meeting-baas-transcriber
```

## What Files You'll Get

After a successful transcription, you'll find:

### Transcript Files

Located in `logs/transcripts/`:

```
transcript_bot_abc123def456_20251018_143022.txt
```

Example content:

```
Meeting Transcript
Meeting URL: https://zoom.us/j/123456789
Bot ID: bot_abc123def456
Generated: 2025-10-18T14:30:22.123456
================================================================================

[00:00] Speaker 1:
This is a test of the transcription system

[00:05] Speaker 2:
I can confirm the transcription is working

[00:12] Speaker 1:
Excellent, thank you for testing
```

### Webhook Event Logs

Located in `logs/`:

```
webhook_20251018.jsonl
```

Example content (JSON Lines format):

```json
{"event": "meeting.started", "bot_id": "bot_abc123", "meeting_url": "https://zoom.us/j/123", "timestamp": "2025-10-18T14:30:00Z"}
{"event": "meeting.completed", "bot_id": "bot_abc123", "meeting_url": "https://zoom.us/j/123", "timestamp": "2025-10-18T15:00:00Z", "data": {...}}
```

## Next Steps

Once you have transcription working:

1. **Integrate with fact-checking pipeline** - See README.md "Next Steps" section
2. **Self-host Meeting BaaS** - Eliminate per-hour costs for production
3. **Customise bot behaviour** - Modify `create_bot.py` to change bot settings

## Need Help?

- Check the main [README.md](README.md) for detailed documentation
- Review Meeting BaaS docs: [docs.meetingbaas.com](https://docs.meetingbaas.com)
- Check Meeting BaaS API reference: [meetingbaas.com/api](https://www.meetingbaas.com/en/api/bots-api)

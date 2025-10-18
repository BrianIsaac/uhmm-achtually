# Quick Test Guide - Step-by-Step

Follow these exact steps to test the Meeting BaaS transcription implementation.

## Prerequisites Check

Before starting, verify you have:

- [x] Meeting BaaS API key added to `.env` file
- [ ] A Zoom meeting URL (we'll create one in Step 1)

## Step-by-Step Test

### Step 1: Create a Zoom Test Meeting

**Option A: Quick Test Meeting (Instant)**

1. Go to https://zoom.us/test
2. Click "Join" - this creates an instant test meeting
3. Copy the meeting URL from your browser address bar
   - Example: `https://zoom.us/j/1234567890?pwd=abcdef...`
   - OR simplified: `https://zoom.us/j/1234567890`

**Option B: Scheduled Meeting (More Control)**

1. Sign in to https://zoom.us
2. Click "Schedule a Meeting"
3. Set:
   - Topic: "Meeting BaaS Test"
   - When: Now
   - Duration: 30 minutes
   - **IMPORTANT**: Disable "Waiting Room" (or you'll have to manually admit the bot)
4. Click "Save"
5. Copy the meeting URL (looks like `https://zoom.us/j/1234567890`)

---

### Step 2: Start the Webhook Server

Open **Terminal 1** and run:

```bash
cd meeting-baas-transcriber
uv run python run_server.py --ngrok
```

**Expected Output:**
```
✅ Ngrok tunnel active!
================================================================================
📍 Public URL: https://abc123xyz.ngrok.io
🔗 Webhook URL: https://abc123xyz.ngrok.io/webhooks/meetingbaas

💡 Use this webhook URL when creating bots:
   python create_bot.py <meeting_url> https://abc123xyz.ngrok.io/webhooks/meetingbaas
================================================================================

INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

**Copy the webhook URL** - you'll need it in the next step.

**⚠️ Important Notes:**
- If you don't have ngrok auth token, the server will still start but webhooks won't work
- To get ngrok token: Sign up at https://ngrok.com and add `NGROK_AUTH_TOKEN` to `.env`
- **Alternative without ngrok:** Skip `--ngrok` flag, but you won't get real-time webhooks

---

### Step 3: Create the Bot

Open **Terminal 2** (keep Terminal 1 running!) and run:

```bash
cd meeting-baas-transcriber
uv run python create_bot.py <YOUR_ZOOM_URL> <YOUR_WEBHOOK_URL>
```

**Example:**
```bash
uv run python create_bot.py https://zoom.us/j/1234567890 https://abc123xyz.ngrok.io/webhooks/meetingbaas
```

**Expected Output:**
```
🤖 Creating Meeting BaaS bot...
📍 Meeting URL: https://zoom.us/j/1234567890
🔗 Webhook URL: https://abc123xyz.ngrok.io/webhooks/meetingbaas

✅ Bot created successfully!
   Bot ID: bot_abc123def456
   Status: pending
   Meeting URL: https://zoom.us/j/1234567890

📝 Next steps:
   1. The bot will join the meeting shortly
   2. Transcription will begin automatically
   3. Transcript will be sent to your webhook when meeting ends
```

**Copy the Bot ID** - you might need it later.

---

### Step 4: Join the Meeting Yourself

1. Click on your Zoom meeting URL (or click "Join" if already in Zoom)
2. Join with video/audio

**Within 10-30 seconds, you should see:**
- A new participant join: **"Transcription Bot"**
- The bot appears as a regular participant (no video, just audio)

**In Terminal 1 (webhook server), you should see:**
```
INFO:     127.0.0.1:xxxxx - "POST /webhooks/meetingbaas HTTP/1.1" 200 OK
✅ Bot bot_abc123def456 joined meeting: https://zoom.us/j/1234567890
   Timestamp: 2025-10-18T17:30:00Z
```

---

### Step 5: Speak in the Meeting

Say a few test phrases clearly:

1. **"Hello, this is a test of the Meeting BaaS transcription system."**
2. Wait 2 seconds
3. **"Python is a programming language created by Guido van Rossum."**
4. Wait 2 seconds
5. **"The quick brown fox jumps over the lazy dog."**

**Tips for best accuracy:**
- Speak clearly and at normal pace
- Pause between sentences
- Avoid background noise
- Use a good microphone if possible

---

### Step 6: End the Meeting

1. In Zoom, click "End Meeting"
2. Click "End Meeting for All"

**What happens next:**
- The bot will leave the meeting
- Meeting BaaS will process the transcript
- Webhook server will receive the complete transcript (takes 10-30 seconds)

---

### Step 7: Check the Results

**In Terminal 1 (webhook server), you should see:**

```
🎬 Meeting completed: https://zoom.us/j/1234567890
   Bot ID: bot_abc123def456

📝 Transcript (3 utterances):
================================================================================
[00:00] Speaker 1:
  Hello, this is a test of the Meeting BaaS transcription system.

[00:05] Speaker 1:
  Python is a programming language created by Guido van Rossum.

[00:12] Speaker 1:
  The quick brown fox jumps over the lazy dog.
================================================================================

💾 Transcript saved to: logs/transcripts/transcript_bot_abc123def456_20251018_173045.txt
```

**Check the saved transcript file:**

```bash
cat logs/transcripts/transcript_bot_*.txt
```

**Expected output:**
```
Meeting Transcript
Meeting URL: https://zoom.us/j/1234567890
Bot ID: bot_abc123def456
Generated: 2025-10-18T17:30:45.123456
================================================================================

[00:00] Speaker 1:
Hello, this is a test of the Meeting BaaS transcription system.

[00:05] Speaker 1:
Python is a programming language created by Guido van Rossum.

[00:12] Speaker 1:
The quick brown fox jumps over the lazy dog.
```

---

## Alternative: Test Without Webhooks (Polling Method)

If you don't have ngrok or webhooks aren't working:

### Step 1: Create bot without webhook

```bash
uv run python create_bot.py https://zoom.us/j/1234567890
```

### Step 2: Note the Bot ID

```
✅ Bot created successfully!
   Bot ID: bot_abc123def456
```

### Step 3: Join meeting and speak

(Same as Step 4-5 above)

### Step 4: Check bot status

```bash
uv run python check_bot.py bot_abc123def456
```

**Expected output:**
```json
{
  "bot_id": "bot_abc123def456",
  "status": "in_call",
  "meeting_url": "https://zoom.us/j/1234567890",
  "joined_at": "2025-10-18T17:30:00Z"
}
```

### Step 5: After ending meeting, check status again

```bash
uv run python check_bot.py bot_abc123def456
```

**Expected output will include transcript data:**
```json
{
  "bot_id": "bot_abc123def456",
  "status": "completed",
  "transcript": [
    {
      "speaker": "Speaker 1",
      "text": "Hello, this is a test...",
      "start_time": 0.0,
      "end_time": 3.5
    }
  ]
}
```

---

## Troubleshooting

### Bot doesn't join the meeting

**Check:**
```bash
uv run python check_bot.py <bot_id>
```

**Possible issues:**

1. **Status: "waiting_room"**
   - Solution: Go to Zoom and admit the bot manually

2. **Status: "failed"**
   - Check the error message in the status response
   - Common issue: Invalid meeting URL
   - Verify the meeting hasn't ended

3. **No response from API**
   - Check your API key in `.env`
   - Verify internet connection

### Webhook server not receiving events

**Check ngrok tunnel:**
```bash
# Visit ngrok web interface
# Open in browser: http://localhost:4040
```

This shows all HTTP requests to your tunnel.

**If no events showing:**
1. Verify webhook URL was passed to `create_bot.py`
2. Check firewall isn't blocking port 8000
3. Ensure ngrok tunnel is still active (free tunnels expire after 2 hours)

### Transcription is inaccurate

**Improve accuracy by:**
1. Using a headset microphone (not laptop mic)
2. Reducing background noise
3. Speaking clearly and slowly
4. Testing in a quiet environment
5. Ensuring good internet connection (affects audio quality)

### Meeting BaaS API errors

**Check your account:**
1. Visit https://meetingbaas.com/dashboard
2. Verify you have credits remaining (free tier: 4 hours)
3. Check API key is valid

---

## Expected Costs for This Test

- **Meeting BaaS:**
  - Free tier includes 4 hours
  - This test uses ~5 minutes (~$0.06 if beyond free tier)

- **Ngrok:**
  - Free tier (no cost)
  - Tunnel expires after 2 hours

- **Zoom:**
  - Free tier (up to 40 minutes for group meetings)
  - Solo test meetings have no time limit

**Total cost for test: $0** (assuming free tiers)

---

## What to Do Next

Once the test works:

### 1. Test with Multiple Speakers

Invite a friend to join the meeting and have a conversation. The bot should identify different speakers:

```
[00:00] Speaker 1:
Hello everyone

[00:03] Speaker 2:
Hi there, how are you?

[00:06] Speaker 1:
I'm doing great, thanks!
```

### 2. Test Longer Meetings

Try a 10-15 minute conversation to see how it handles longer transcripts.

### 3. Integrate with Fact-Checking

Modify `webhook_server.py` to process utterances through your claim extraction pipeline:

```python
async def handle_meeting_completed(event: WebhookEvent):
    transcript_data = event.data.get("transcript", [])

    for utterance in transcript_data:
        # Extract claims from each utterance
        claims = await extract_claims(utterance["text"])

        # Verify each claim
        for claim in claims:
            verdict = await verify_claim(claim)
            print(f"Claim: {claim}")
            print(f"Verdict: {verdict}")
```

### 4. Consider Self-Hosting

For production (to avoid per-hour costs):
- Self-host Meeting BaaS: https://github.com/Meeting-Baas/meeting-bot-as-a-service
- Deploy on your own server
- Zero per-hour costs (only server costs)

---

## Success Criteria

✅ Your test is successful if:

1. Bot appears in Zoom participant list
2. Webhook server receives `meeting.started` event
3. Webhook server receives `meeting.completed` event with transcript
4. Transcript file is saved to `logs/transcripts/`
5. Transcript contains your spoken words with reasonable accuracy

---

## Getting Help

If you encounter issues:

1. Check the logs in `logs/webhook_*.jsonl`
2. Review Meeting BaaS documentation: https://docs.meetingbaas.com
3. Check Meeting BaaS API status: https://status.meetingbaas.com
4. Open an issue with full error logs

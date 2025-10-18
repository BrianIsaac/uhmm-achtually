# Simple Test - Just Check if Bot Can Join

This is the absolute simplest test - just verify the bot can join a Zoom meeting.

**No ngrok needed. No webhooks. Just bot joining.**

## What You Need

1. ✅ Meeting BaaS API key (already in `.env`)
2. ✅ A Zoom meeting URL

## Step-by-Step

### Step 1: Create a Zoom Test Meeting

Go to https://zoom.us/test and click "Join"

Copy the URL from your browser (example: `https://zoom.us/j/1234567890`)

### Step 2: Run the Hello Bot

```bash
cd meeting-baas-transcriber
uv run python hello_bot.py https://zoom.us/j/YOUR_MEETING_ID
```

**Replace** `YOUR_MEETING_ID` with your actual meeting ID from Step 1.

### Step 3: Watch What Happens

**In your terminal, you'll see:**

```
================================================================================
🤖 SIMPLE MEETING BOT TEST
================================================================================

📍 Meeting URL: https://zoom.us/j/1234567890
🤖 Bot Name: Transcription Bot
💬 Entry Message: 👋 Hello! I'm a test bot. I'll be monitoring this meeting.

Creating bot...

✅ Bot created successfully!
   Bot ID: bot_abc123def456
   Status: pending
   Meeting URL: https://zoom.us/j/1234567890

================================================================================
📊 MONITORING BOT STATUS
================================================================================

The bot will now join the meeting. Checking status every 5 seconds...
Press Ctrl+C to stop monitoring

[17:30:01] Check #1: Bot status = joining
   ⏳ Bot is joining the meeting...
[17:30:06] Check #2: Bot status = in_call
   ✅ Bot successfully joined the meeting!
   👀 Check your Zoom meeting - you should see 'Hello Bot' as a participant
[17:30:11] Check #3: Bot status = in_call
[17:30:16] Check #4: Bot status = in_call
```

**In your Zoom meeting, you'll see:**

```
Participants (2):
✅ You
✅ Hello Bot
```

The bot appears as a real participant!

### Step 4: End the Meeting

Click "End Meeting" in Zoom.

**Terminal will show:**

```
[17:31:21] Check #7: Bot status = completed
   🎬 Meeting ended - bot has left

💡 Bot lifecycle complete!
```

---

## That's It!

You've successfully:
- ✅ Created a bot via Meeting BaaS API
- ✅ Bot joined the Zoom meeting
- ✅ Bot appeared as a participant
- ✅ Bot left when meeting ended

## What This Test Proves

1. **Meeting BaaS API is working** - Your API key is valid
2. **Bot can join Zoom meetings** - The core functionality works
3. **Bot lifecycle management** - Joining, monitoring, leaving all work

## About Sending Messages Every 5 Seconds

**Current Limitation:**

The bot you just tested uses the **Recording/Transcription Bot API**. This API:
- ✅ Can join meetings
- ✅ Can record audio/video
- ✅ Can transcribe conversations
- ✅ Can send **one** entry message when joining
- ❌ **Cannot** send periodic chat messages

**To Send Periodic Messages:**

You need Meeting BaaS **Speaking Bots API**, which:
- Sends chat messages
- Speaks in the meeting (TTS)
- Responds to conversation (AI-powered)

**Two Options:**

### Option 1: Upgrade to Speaking Bots (Easiest)

Contact Meeting BaaS for Speaking Bots access:
- https://www.meetingbaas.com/en/projects/speaking-bots
- Different pricing (likely higher than $0.69/hour)
- AI-powered conversation capabilities

### Option 2: Self-Host with Custom Logic (Free but Complex)

Clone and modify Meeting BaaS:
```bash
git clone https://github.com/Meeting-Baas/meeting-bot-as-a-service
# Add custom code to send messages every 5 seconds
docker-compose up
```

This gives you full control but requires:
- Docker/Kubernetes knowledge
- Browser automation (Puppeteer) knowledge
- Ongoing maintenance

## Summary

✅ **What Works Now:**
- Bot joins meetings
- Bot records/transcribes
- Bot sends entry message

❌ **What Doesn't Work:**
- Periodic chat messages (needs Speaking Bots or self-hosting)

For your fact-checking bot, the **transcription functionality** (what works now) is what you actually need!

The periodic messages would only be useful for testing bot presence, which you've now verified works. 👍

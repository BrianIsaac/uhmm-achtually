# Real-Time Fact-Checking Bot: Reality Check

## What You Wanted

A bot that:
1. ✅ Joins Zoom/Teams meetings
2. ✅ Listens to conversations in real-time
3. ✅ Extracts factual claims (Groq LLM)
4. ✅ Fact-checks with web search (Exa + Groq)
5. ❌ **SPEAKS fact-checks in real-time via ElevenLabs TTS**

## What's Actually Possible with Current Tools

### Option 1: Post-Meeting Analysis (WORKING)

**What you have now:**
- Bot ID: `27f8e266-3fa8-4ea8-aed2-fb881a99b029`
- Status: Joined your meeting, recording
- Webhook: Receiving transcripts

**What it does:**
1. ✅ Joins Zoom meeting
2. ✅ Records audio
3. ✅ Transcribes with Meeting BaaS STT (95% accuracy)
4. ✅ Sends transcript to webhook when meeting ends
5. ✅ Your webhook server processes it
6. ❌ **No real-time fact-checking during meeting**
7. ❌ **Bot doesn't speak**

**To make this work for fact-checking:**
- Modify your webhook server (`meeting-baas-transcriber/src/webhook_server.py`)
- When `meeting.completed` webhook arrives, run transcript through your pipeline:
  - Extract claims (ClaimExtractor)
  - Fact-check (WebFactChecker)
  - Generate report of false claims
- Email/display report to you after meeting

### Option 2: Meeting BaaS Speaking Bot (ATTEMPTED - BLOCKED)

**Why it's not working:**

1. **Architecture mismatch**: Speaking Bot is designed for **conversational AI** (chatbots that respond to questions), NOT silent monitoring bots

2. **No custom pipeline support**: Meeting BaaS Speaking Bot uses:
   - Their STT (Deepgram/Gladia)
   - OpenAI GPT-4 (hardcoded)
   - Cartesia TTS (hardcoded)
   - You **cannot** inject your ClaimExtractor or WebFactChecker

3. **Webhook requirement**: Even for speaking bots, Meeting BaaS requires a webhook URL for the regular bot API

4. **Persona system**: The speaking-meeting-bot repository we cloned doesn't have a "fact_checker" persona - it has personas like "interviewer", "debate_champion", etc.

### Option 3: Custom Pipecat Bot (COMPLEX - Not Yet Attempted)

**What this would require:**

Build a completely custom bot from scratch using Pipecat that:
1. Uses Meeting BaaS API to join meeting and get audio stream
2. Processes audio through YOUR pipeline (Groq STT → Claims → FactCheck)
3. Sends audio back via Meeting BaaS to speak verdicts

**Blockers:**
- Meeting BaaS doesn't provide direct audio streaming API
- Their Speaking Bot API is a hosted service, not self-hostable with custom pipelines
- Would need to reverse-engineer how Meeting BaaS WebSocket protocol works

## The Honest Assessment

**Real-time fact-checking with spoken verdicts during Zoom meetings is NOT currently achievable with Meeting BaaS** because:

1. Meeting BaaS's simple bot API only records (no speaking)
2. Meeting BaaS's Speaking Bot API doesn't support custom processing pipelines
3. You can't inject your ClaimExtractor/WebFactChecker into their system

## What IS Achievable

### Recommended Approach: Hybrid System

**During Meeting (Real-time monitoring):**
- Use Daily.co bot (your existing `backend/bot.py`)
- Participants join Daily room INSTEAD of Zoom
- Bot provides real-time fact-checking via app messages (not TTS)
- Vue.js frontend displays verdicts in real-time

**For External Zoom Meetings (Post-meeting):**
- Use Meeting BaaS recording bot (what you deployed)
- Get high-quality transcript (95% accuracy) after meeting
- Process transcript through your fact-checking pipeline
- Generate detailed report of false claims

### Why This Makes Sense

| Requirement | Daily.co Bot | Meeting BaaS Bot |
|-------------|--------------|------------------|
| **Real-time** | ✅ Yes | ❌ Post-meeting only |
| **Fact-checking** | ✅ Your pipeline | ✅ Your pipeline (webhook) |
| **Output** | ✅ App messages | ❌ No output |
| **Zoom/Teams** | ❌ No (Daily rooms only) | ✅ Yes |
| **Your control** | ✅ Full control | ⚠️ Limited (recording only) |

## Next Steps (If You Want Real-Time)

### Keep Daily.co for Real-Time Fact-Checking

Your existing bot (`backend/bot.py`) WORKS for real-time fact-checking! It just doesn't join Zoom - it creates Daily.co rooms.

**To make it work:**
1. Create a Daily.co room for your meetings
2. Invite participants to join the Daily room (not Zoom)
3. Bot fact-checks in real-time
4. Verdicts appear in Vue.js frontend

**Advantages:**
- ✅ Real-time (1.2-2.25s latency)
- ✅ Your complete pipeline (Groq STT → Claims → Exa → Groq)
- ✅ Full control over UX
- ✅ No Meeting BaaS complexity

**Disadvantages:**
- ❌ Participants must join Daily.co, not Zoom
- ❌ Can't join existing Zoom meetings

### Use Meeting BaaS for Post-Meeting Analysis

For meetings where you can't control the platform (existing Zoom meetings):
1. Deploy Meeting BaaS recording bot
2. Get transcript after meeting
3. Process through your pipeline
4. Email yourself a report

## The Real Question

**Do you NEED the bot to join external Zoom/Teams meetings, or can participants join a Daily.co room instead?**

- If Daily.co is acceptable → Use your existing bot (works perfectly!)
- If must be Zoom → You're limited to post-meeting analysis only

## What I've Built For You

Despite the limitations, you now have:

1. ✅ **Meeting BaaS recording integration** (`meeting-baas-transcriber/`)
   - Joins Zoom/Teams meetings
   - Records and transcribes
   - Sends webhooks with transcript

2. ✅ **Fact-checking processors** (`backend/src/processors/`)
   - ClaimExtractor (Groq)
   - WebFactChecker (Exa + Groq)
   - 100% reusable code

3. ✅ **Webhook server** (`meeting-baas-transcriber/src/webhook_server.py`)
   - Receives Meeting BaaS events
   - Ready to process transcripts

4. ✅ **Speaking bot attempt** (`meeting-baas-speaking/`)
   - Installed all dependencies
   - API server running
   - Discovered architectural limitations

## My Recommendation

**For your current meeting (`27f8e266-3fa8-4ea8-aed2-fb881a99b029`):**

1. End the Zoom call (bot has been recording)
2. Wait for `meeting.completed` webhook
3. I'll help you process the transcript through your fact-checking pipeline
4. You'll get a report of all false claims made in the meeting

**For future meetings:**

- **Internal meetings**: Use Daily.co bot (real-time fact-checking works!)
- **External Zoom meetings**: Use Meeting BaaS (post-meeting analysis only)

Let me know which direction you want to go.

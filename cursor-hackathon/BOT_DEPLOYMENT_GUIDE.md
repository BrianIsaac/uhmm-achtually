# Bot Deployment Guide - Where Does the Bot Run?

## TL;DR

**For the hackathon**: The Python bot runs **on your local machine** (Developer A or B's laptop), not in Daily's cloud. Daily.co only provides the WebRTC room infrastructure.

---

## Understanding the Architecture

### What Daily.co Provides
- **WebRTC Room**: A URL like `https://your-domain.daily.co/fact-checker-demo`
- **Signaling Server**: Routes audio/video between participants
- **STUN/TURN Servers**: Helps with NAT traversal

### What Daily.co Does NOT Provide
- ❌ Bot hosting
- ❌ Running your Python code
- ❌ Pipecat pipeline execution

### What You Provide
- ✅ Python bot code (`backend/bot.py`)
- ✅ Machine to run the bot (your laptop)
- ✅ Internet connection to Daily room

---

## How It Works

```
┌─────────────────────────────────────────────────────────┐
│               Daily.co Cloud Service                     │
│  - Hosts room: fact-checker-demo                        │
│  - Routes WebRTC streams between participants            │
│  - Does NOT execute your bot code                       │
└─────────────────────────────────────────────────────────┘
         ↑                    ↑                    ↑
         │ WebRTC             │ WebRTC             │ WebRTC
         │                    │                    │
    ┌────┴─────┐      ┌──────┴──────┐     ┌───────┴────────┐
    │  Your    │      │  Browser    │     │  Browser       │
    │  Python  │      │  (Vue.js    │     │  (Vue.js       │
    │  Bot     │      │  Frontend)  │     │  Frontend)     │
    │  (Laptop)│      │             │     │                │
    └──────────┘      └─────────────┘     └────────────────┘
```

**The bot is just another participant in the Daily room**, but instead of a human with a browser, it's your Python code running on a machine.

---

## For Hackathon: Local Development Setup

### Step 1: Developer C Creates Daily Room

```bash
# Developer C runs this once
curl -X POST https://api.daily.co/v1/rooms \
  -H "Authorization: Bearer YOUR_DAILY_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "fact-checker-demo",
    "privacy": "public",
    "properties": {
      "enable_chat": false,
      "enable_prejoin_ui": false
    }
  }'

# Response includes:
# {
#   "url": "https://your-domain.daily.co/fact-checker-demo",
#   ...
# }
```

### Step 2: Developer C Generates Bot Token

```bash
# Developer C runs this once
curl -X POST https://api.daily.co/v1/meeting-tokens \
  -H "Authorization: Bearer YOUR_DAILY_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "properties": {
      "room_name": "fact-checker-demo",
      "is_owner": true
    }
  }'

# Response includes:
# {
#   "token": "eyJhbGc...",
#   ...
# }
```

### Step 3: Developer C Shares Credentials

Share via secure document (Google Doc, Notion):
```bash
DAILY_ROOM_URL=https://your-domain.daily.co/fact-checker-demo
DAILY_BOT_TOKEN=eyJhbGc...
```

### Step 4: Developer A/B Configures Backend

```bash
# backend/.env
DAILY_ROOM_URL=https://your-domain.daily.co/fact-checker-demo
DAILY_BOT_TOKEN=eyJhbGc...
GROQ_API_KEY=your_groq_key
EXA_API_KEY=your_exa_key
```

### Step 5: Developer A/B Runs Bot Locally

```bash
# On Developer A or B's laptop
cd backend
uv run python bot.py

# Output:
# INFO: Bot joining room: https://your-domain.daily.co/fact-checker-demo
# INFO: Connected to Daily room
# INFO: Waiting for audio...
```

**Keep this terminal open during the entire demo!**

### Step 6: Developer C and Users Join via Browser

```bash
# Developer C runs frontend
cd frontend
npm run dev

# Open http://localhost:5173
# Click "Join Call"
# Start speaking to test
```

---

## Demo Day Workflow

### Pre-Demo Setup (10 minutes before)

1. **Developer A/B** (Backend):
   ```bash
   cd backend
   uv run python bot.py
   # Keep terminal open, verify "Connected to Daily room"
   ```

2. **Developer C** (Frontend):
   ```bash
   cd frontend
   npm run dev
   # Open http://localhost:5173 in browser
   ```

3. **Verify Connection**:
   - Frontend joins room
   - Backend logs show participant joined
   - Speak test claim
   - Verify verdict appears

### During Demo (5 minutes)

1. **Show Architecture Slide**:
   - Explain triple-client pattern
   - Point out bot running on laptop

2. **Join Call**:
   - Click "Join Call" in browser
   - Show participant video appearing

3. **Live Fact-Checking**:
   - Speak 3-5 test claims
   - Show verdict cards appearing in real-time
   - Click evidence links

4. **Q&A**

### Post-Demo

- Keep bot running if showing to judges
- Can restart if needed: `Ctrl+C` → `uv run python bot.py`

---

## Alternative: Daily Pipecat Cloud (Post-Hackathon)

If you want to deploy the bot to run 24/7 after the hackathon:

### Option A: Daily Pipecat Cloud (Managed)

**What it is**: Daily's managed hosting for Pipecat bots

**Setup**:
1. Sign up: https://pipecat.daily.co
2. Deploy your bot code
3. Daily runs it 24/7

**Pricing**:
- Free tier: 100 minutes/month
- Paid: $0.02/minute

**Pros**:
- No server management
- Auto-scaling
- Built-in monitoring

**Cons**:
- Costs money
- Less control over infrastructure

**Reference**: https://docs.daily.co/guides/products/ai-toolkit

---

### Option B: Self-Hosted Server (DIY)

**What it is**: Run bot on your own cloud server

**Setup**:
1. Get a cloud server (AWS EC2, DigitalOcean, etc.)
2. Install Python, dependencies
3. Run bot as a systemd service
4. Keep it running 24/7

**Example (DigitalOcean Droplet)**:

```bash
# On your cloud server
git clone <your-repo>
cd backend
uv sync
uv run python bot.py
```

**Systemd Service** (`/etc/systemd/system/fact-checker-bot.service`):
```ini
[Unit]
Description=Fact Checker Bot
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/home/your-user/backend
ExecStart=/home/your-user/.local/bin/uv run python bot.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable fact-checker-bot
sudo systemctl start fact-checker-bot
sudo systemctl status fact-checker-bot
```

**Pros**:
- Full control
- Predictable costs
- Can customize infrastructure

**Cons**:
- You manage the server
- You handle scaling
- You monitor uptime

---

## Frequently Asked Questions

### Q: Do I need Daily Pipecat Cloud for the hackathon?
**A**: No! Run the bot on your laptop. It's simpler and free.

### Q: Can multiple people run the bot?
**A**: Only one bot should run per room. If two bots join, they'll both process audio and send duplicate verdicts. Designate Developer A or B to run the bot.

### Q: What if my laptop dies during the demo?
**A**: Have a backup:
1. Record a demo video beforehand
2. Have Developer B ready to run the bot on their laptop
3. Keep laptop plugged in during demo

### Q: Does the bot need a powerful machine?
**A**: No. The heavy lifting (STT, LLM, search) is done by cloud APIs (Groq, Exa). Your laptop just orchestrates the pipeline.

**Minimum requirements**:
- Python 3.12
- 4GB RAM
- Stable internet connection

### Q: Can I run the bot on a server for the demo?
**A**: Yes, if you have time. But for a 24-hour hackathon, running locally is simpler.

### Q: What happens if the bot crashes?
**A**: Just restart it:
```bash
# Ctrl+C to stop
uv run python bot.py  # Restart
```
The bot will rejoin the room and continue processing.

### Q: How do I know the bot is connected?
**A**: Check the logs:
```
INFO: Bot joining room: https://...
INFO: Connected to Daily room
INFO: Participant joined: local
```

Also, the frontend should show the bot as a participant (with username "Fact Checker Bot").

---

## Troubleshooting

### Bot doesn't connect to Daily room

**Check 1**: Verify credentials
```bash
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('Room:', os.getenv('DAILY_ROOM_URL')); print('Token:', os.getenv('DAILY_BOT_TOKEN')[:20] + '...')"
```

**Check 2**: Verify room exists
```bash
curl -H "Authorization: Bearer $DAILY_API_KEY" \
  https://api.daily.co/v1/rooms/fact-checker-demo
```

**Check 3**: Regenerate token (tokens expire after 1 hour by default)
```bash
curl -X POST https://api.daily.co/v1/meeting-tokens \
  -H "Authorization: Bearer $DAILY_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"properties": {"room_name": "fact-checker-demo", "is_owner": true}}'
```

### Bot connects but no audio processing

**Check**: VAD threshold might be too high
```python
# In daily_transport_service.py, lower threshold:
VADParams(
    start_secs=0.2,
    stop_secs=0.8,
    min_volume=0.3  # Lower from 0.6
)
```

### Bot crashes with "Connection lost"

**Check**: Internet connection stable?
**Fix**: Restart bot, check network

---

## Summary

✅ **For Hackathon**: Run bot on Developer A or B's laptop
✅ **Daily.co**: Only provides WebRTC room infrastructure
✅ **Bot Code**: You run it yourself (`uv run python bot.py`)
✅ **Keep Terminal Open**: During the entire demo
✅ **Backup Plan**: Record demo video beforehand

❌ **NOT using**: Daily Pipecat Cloud (can add post-hackathon)
❌ **NOT needed**: Cloud server (can add post-hackathon)

---

**Remember**: The bot is just another participant joining the Daily room. It's your Python code running somewhere (your laptop for now), connecting to Daily's WebRTC infrastructure, processing audio, and sending app messages back to the room.

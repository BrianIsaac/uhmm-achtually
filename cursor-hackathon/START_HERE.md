# 🚀 START HERE - Real-Time Fact Checker Hackathon

## Welcome!

You're about to build a **real-time AI fact-checker** that joins video meetings, listens to conversations, extracts claims, verifies them via web search, and displays results in a custom UI. You have **24 hours** and a **3-person team**.

## Quick Start (Choose Your Role)

### 👤 I am Developer A (Pipecat Pipeline Foundation)
**Read**: [DEVELOPER_A_PROMPT.md](DEVELOPER_A_PROMPT.md)

**Your mission**: Build the audio pipeline foundation (Stages 1-3)
- Set up project with uv
- Implement DailyTransport with VAD
- Integrate Groq Whisper STT
- Create SentenceAggregator

**Start command**:
```bash
cd /home/brian-isaac/Documents/personal/uhmm-achtually
mkdir -p backend/src/{processors,services,frames,utils}
cd backend
uv init
# Continue with DEVELOPER_A_PROMPT.md
```

**Note**: You'll run the bot on your laptop with `uv run python bot.py` - not in Daily's cloud. See [BOT_DEPLOYMENT_GUIDE.md](BOT_DEPLOYMENT_GUIDE.md).

---

### 👤 I am Developer B (Claim Processing & Intelligence)
**Read**: [DEVELOPER_B_PROMPT.md](DEVELOPER_B_PROMPT.md)

**Your mission**: Build the intelligence layer (Stages 4-6)
- Extract claims with Groq LLM
- Verify claims with Exa search
- Broadcast verdicts via app messages

**Start command**:
```bash
cd /home/brian-isaac/Documents/personal/uhmm-achtually/backend
# Wait for Developer A to create project structure
# Then continue with DEVELOPER_B_PROMPT.md
```

---

### 👤 I am Developer C (Vue.js Frontend)
**Read**: [DEVELOPER_C_PROMPT.md](DEVELOPER_C_PROMPT.md)

**Your mission**: Build custom Vue.js frontend
- Set up Daily.co account and room
- Create CallObject integration
- Build verdict card display
- Display participant video

**Start command**:
```bash
cd /home/brian-isaac/Documents/personal/uhmm-achtually
npm create vite@latest frontend -- --template vue
cd frontend
npm install @daily-co/daily-js
# Continue with DEVELOPER_C_PROMPT.md
```

---

## Team Coordination

**Essential reading for all**: [TEAM_COORDINATION_GUIDE.md](TEAM_COORDINATION_GUIDE.md)

### Critical First Steps (Hour 0)
1. **All**: Read your assigned developer prompt
2. **Developer C**: Create Daily.co account and room first
3. **Developer C**: Share room URL and API key with team
4. **Developer A**: Bootstrap backend project
5. **All**: Create shared credentials document

### Integration Points
- **Hour 2**: Share frame definitions (A ↔ B)
- **Hour 5**: Share app message format (B → C)
- **Hour 6**: Complete integration (All)
- **Hour 8**: Demo ready (All)

## Architecture Overview

```
┌──────────────────────────────────────────────────────────┐
│           Daily.co Cloud (WebRTC Infrastructure)         │
│  Room: https://your-domain.daily.co/fact-checker-demo   │
│  - Routes WebRTC audio/video between participants        │
│  - Does NOT run your bot code                           │
└─────────┬────────────────────────┬───────────────────────┘
          │ WebRTC                 │ WebRTC
          │                        │
┌─────────┴─────────────┐  ┌──────┴────────────────────────┐
│  Vue.js Frontend (C)  │  │ Python Bot (A+B)              │
│  Runs: Browser        │  │ Runs: Developer A/B's Laptop  │
│                       │  │                               │
│  - CallObject         │  │ ┌───────────────────────────┐ │
│  - Audio/video        │  │ │ Pipecat Pipeline (A)      │ │
│  - App msg listener   │  │ │ Stage 1: DailyTransport   │ │
│  - Verdict cards      │  │ │ Stage 2: GroqSTTService   │ │
└───────────────────────┘  │ │ Stage 3: SentenceAgg.     │ │
                           │ └───────────────────────────┘ │
                           │           ↓                    │
                           │ ┌───────────────────────────┐ │
                           │ │ Claim Processing (B)      │ │
                           │ │ Stage 4: ClaimExtractor   │ │
                           │ │ Stage 5: WebFactChecker   │ │
                           │ │ Stage 6: FactCheckMsg.    │ │
                           │ └───────────────────────────┘ │
                           └───────────────────────────────┘
```

**IMPORTANT**: The Python bot runs on **your local machine** (Developer A or B's laptop), NOT in Daily's cloud. Daily.co only provides the WebRTC room infrastructure. See [BOT_DEPLOYMENT_GUIDE.md](BOT_DEPLOYMENT_GUIDE.md) for details.

## Technology Stack

### Backend (A + B)
- **Python 3.12** with **uv** package manager
- **Pipecat**: Real-time voice AI framework
- **Daily.co**: WebRTC infrastructure
- **Groq**: Whisper STT + Llama LLM (216x real-time speed)
- **Exa**: Neural web search

### Frontend (C)
- **Vue.js 3** with **Vite**
- **@daily-co/daily-js**: Daily CallObject SDK
- **Composition API**: Reactive state management

## File Structure

```
uhmm-achtually/
├── backend/                         # Python bot (A + B)
│   ├── .env                         # Environment variables (gitignored)
│   ├── bot.py                       # Main entry point
│   ├── pyproject.toml               # uv configuration
│   └── src/
│       ├── processors/              # Stages 3-6
│       ├── services/                # STT, Exa, Daily clients
│       ├── frames/                  # Custom frame definitions
│       └── utils/                   # Config, logging
├── frontend/                        # Vue.js app (C)
│   ├── .env.local                   # Environment variables (gitignored)
│   ├── package.json                 # npm dependencies
│   └── src/
│       ├── App.vue                  # Main component
│       ├── composables/             # useDaily, useFactCheck
│       └── components/              # UI components
└── cursor-hackathon/                # Documentation (THIS DIRECTORY)
    ├── START_HERE.md                # This file
    ├── DEVELOPER_A_PROMPT.md        # Developer A instructions
    ├── DEVELOPER_B_PROMPT.md        # Developer B instructions
    ├── DEVELOPER_C_PROMPT.md        # Developer C instructions
    ├── TEAM_COORDINATION_GUIDE.md   # Coordination guide
    └── components/                  # Component specifications
```

## Required Credentials

### Daily.co (Developer C sets up)
**What Daily provides**: WebRTC room infrastructure (NOT bot hosting)
- API Key: Sign up at https://dashboard.daily.co
- Room URL: `https://your-domain.daily.co/fact-checker-demo`
- Bot Token: For bot to join room

**Developer C creates** the room and token, then shares with A & B.

### Groq (Developers A & B need)
- API Key from https://console.groq.com
- Free tier: 30 requests/minute (sufficient for hackathon)
- Used for: Whisper STT + Llama LLM

### Exa (Developer B needs)
- API Key from https://exa.ai
- Free tier: 1000 searches/month (sufficient for hackathon)
- Used for: Neural web search

**See [BOT_DEPLOYMENT_GUIDE.md](BOT_DEPLOYMENT_GUIDE.md) for setup details.**

## Success Criteria

### By Hour 6 (Individual)
- ✅ **Developer A**: Stages 1-3 working, transcriptions in logs
- ✅ **Developer B**: Stages 4-6 working, verdicts generated
- ✅ **Developer C**: UI working, app messages received

### By Hour 8 (Team)
- ✅ End-to-end flow working (speech → verdict card)
- ✅ All 5 test claims verified correctly
- ✅ Latency <2.5s total
- ✅ Verdict cards colour-coded (green/red/yellow/grey)
- ✅ Demo script prepared

## Test Claims

Test with these by speaking into Daily room:

1. ✅ "Python 3.12 removed the distutils package." → **Supported** (green)
2. ✅ "GDPR requires breach notification within 72 hours." → **Supported** (green)
3. ✅ "React 18 introduced automatic batching." → **Supported** (green)
4. ❌ "PostgreSQL 15 uses LLVM JIT compilation by default." → **Contradicted** (red)
5. ❓ "Kubernetes uses iptables by default in v1.29." → **Unclear** (yellow)

## Common Issues & Quick Fixes

**Bot doesn't join room**:
```bash
# Check credentials
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('DAILY_ROOM_URL:', os.getenv('DAILY_ROOM_URL'))"
```

**No transcriptions**:
```bash
# Verify Groq API key
curl -H "Authorization: Bearer $GROQ_API_KEY" https://api.groq.com/openai/v1/models
```

**Frontend can't connect**:
```bash
# Check room URL in .env.local
cat frontend/.env.local
```

## Documentation

### Essential Reading
1. **[BOT_DEPLOYMENT_GUIDE.md](BOT_DEPLOYMENT_GUIDE.md)** - WHERE THE BOT RUNS (READ THIS!)
2. [TEAM_COORDINATION_GUIDE.md](TEAM_COORDINATION_GUIDE.md) - Team coordination
3. [architecture_design.md](architecture_design.md) - System architecture
4. [HOW_IT_ALL_WORKS.md](HOW_IT_ALL_WORKS.md) - Integration guide

### Component Specifications
- [00_WORKLOAD_DISTRIBUTION.md](components/00_WORKLOAD_DISTRIBUTION.md) - Workload breakdown
- [01_stt_groq_whisper.md](components/01_stt_groq_whisper.md) - Stage 2 spec
- [02_llm_groq.md](components/02_llm_groq.md) - Stages 4 & 5 spec
- [05_audio_processing.md](components/05_audio_processing.md) - Stage 1 spec
- [07_integration_layer.md](components/07_integration_layer.md) - Pipeline integration
- [08_exa_web_search.md](components/08_exa_web_search.md) - Stage 5 spec
- [09_daily_chat_delivery.md](components/09_daily_chat_delivery.md) - Stage 6 spec
- [10_vue_frontend.md](components/10_vue_frontend.md) - Frontend spec

### External Documentation
- Pipecat: https://docs.pipecat.ai
- Daily.co: https://docs.daily.co
- Groq: https://console.groq.com/docs
- Exa: https://docs.exa.ai
- Vue.js: https://vuejs.org

## Communication

### Standup Schedule
- **Hour 0**: Kickoff
- **Hour 2**: Progress update
- **Hour 4**: Integration checkpoint
- **Hour 6**: Final integration
- **Hour 8**: Demo preparation

### Blocker Protocol
- Stuck >20 minutes? **Notify team immediately**
- Don't wait for next standup
- Help each other debug

### Shared Credentials Document
Create a Google Doc/Notion page with:
- All API keys (DO NOT COMMIT)
- Status updates
- Blockers
- Integration notes

## Demo Preparation

### Pre-Demo Checklist (Hour 8)
- [ ] **Backend bot running** on Developer A/B's laptop: `uv run python bot.py`
- [ ] **Keep terminal open** - don't close it during demo!
- [ ] **Frontend running** on localhost:5173: `npm run dev`
- [ ] Both connected to same Daily room
- [ ] All test claims working
- [ ] Screen recording ready
- [ ] Backup video recorded
- [ ] **Laptop plugged in** to power during demo

### Demo Flow (5 minutes)
1. Introduction (30s)
2. Join call (30s)
3. Live fact-checking (3 mins)
4. Q&A (1 min)

## Emergency Contacts

Maintain a shared list of contact info for quick coordination.

---

## 🎯 Remember

1. **Communication is key**: Coordinate early and often
2. **No tests**: Focus on working code
3. **Manual verification**: Test by speaking into Daily room
4. **Git commits**: Use conventional commit style
5. **Help each other**: This is a team effort

---

## 🚀 Ready to Start?

1. **Choose your role** (A, B, or C)
2. **Read your developer prompt**
3. **Read Team Coordination Guide**
4. **Set up shared credentials document**
5. **Start building!**

Good luck! You've got 24 hours to build something amazing. 🎉

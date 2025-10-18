# Components Implementation Guide

## 🎯 Purpose
This folder contains detailed implementation guides for each component of the Real-time Meeting Fact Checker. Each guide is self-contained, allowing team members to work independently before integration.

**Architecture**: Hybrid Pipecat + Daily.co implementation with 6-stage pipeline and 1.2-2.25s total latency.

## 📁 Component Files

### Phase 1 Components (Must Complete for MVP)

#### Backend Components
1. **[00_WORKLOAD_DISTRIBUTION.md](00_WORKLOAD_DISTRIBUTION.md)**
   - 3-person team organisation and timeline
   - Task assignments for Developers A, B, and C
   - Git workflow with feature branches
   - 8 hours per developer (24 total hours)

2. **[01_stt_groq_whisper.md](01_stt_groq_whisper.md)** - Stage 2
   - Speech-to-Text using Pipecat GroqSTTService
   - Groq Whisper Large v3 Turbo (400-800ms latency)
   - Silero VAD integration
   - Owner: Developer A (2 hours)
   - Output: Factory functions in `backend/bot.py`

3. **[02_llm_groq.md](02_llm_groq.md)** - Stages 4 & 5
   - Groq Llama 3.1 8B Instant (50-150ms latency)
   - ClaimExtractor with JSON mode
   - WebFactChecker LLM integration
   - Custom frame types (ClaimFrame, VerdictFrame)
   - Owner: Developer B (3 hours)
   - Output: `claim_extractor.py`, `web_fact_checker.py`

4. **[05_audio_processing.md](05_audio_processing.md)** - Stage 1
   - DailyTransport with Silero VAD
   - Daily.co WebRTC audio reception
   - No manual buffering (Pipecat handles it)
   - Owner: Developer A (2 hours)
   - Output: Daily.co room setup + factory functions

5. **[07_integration_layer.md](07_integration_layer.md)** - Complete Pipeline
   - Pipecat Pipeline assembly
   - All 6 stages connected
   - Configuration management
   - Owner: All developers (integration support)
   - Output: `backend/bot.py`

6. **[08_exa_web_search.md](08_exa_web_search.md)** - Stage 5
   - Exa neural search API integration
   - search_and_contents with autoprompt
   - Caching layer for performance
   - Owner: Developer B (2-3 hours)
   - Output: `exa_search.py` or integrated in `web_fact_checker.py`

7. **[09_daily_chat_delivery.md](09_daily_chat_delivery.md)** - Stage 6
   - Daily CallClient.sendAppMessage()
   - FactCheckMessenger processor
   - App message broadcasting to frontend
   - Owner: Developer B (2 hours)
   - Output: `fact_check_messenger.py`

#### Frontend Components
8. **[10_vue_frontend.md](10_vue_frontend.md)** - Custom UI
   - Vue.js 3 + Vite application
   - Daily CallObject integration (@daily-co/daily-js)
   - App message listener and verdict display
   - Participant video tiles
   - Microphone/camera controls
   - Owner: Developer C (6 hours)
   - Output: Complete `frontend/` directory

### Phase 2 Components (Stretch Goals)
These components are for future enhancement after Phase 1 MVP:
- BM25S local search (replace web search for offline use)
- Supabase database (add conversation history)
- Advanced analytics and reporting

## 🚀 Quick Start

### Step 1: Setup Backend Environment
```bash
# Navigate to backend
cd backend

# Install dependencies using uv
uv sync --group LLM

# Create .env file
cp .env.example .env
# Edit .env with your API keys: GROQ_API_KEY, EXA_API_KEY, DAILY_API_KEY
```

### Step 2: Setup Frontend Environment
```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Create .env.local file
cp .env.example .env.local
# Edit .env.local with VITE_DAILY_ROOM_URL
```

### Step 3: Choose Your Component
1. Check [00_WORKLOAD_DISTRIBUTION.md](00_WORKLOAD_DISTRIBUTION.md) for assignments
   - **Developer A**: Pipeline Foundation (Stages 1-3) - Backend
   - **Developer B**: Claim Processing (Stages 4-6) - Backend
   - **Developer C**: Vue.js Frontend - Frontend
2. Open your assigned component guide
3. Follow the implementation steps

### Step 4: Implement Your Component
Each guide includes:
- Stage position (backend) or UI component (frontend)
- Time estimates (2-6 hours per component)
- Complete code examples with type hints/JSDoc
- Integration points with adjacent stages/components
- Performance targets

### Step 5: Integration
Once all components are complete:
1. **Backend**: Merge feature branches to `main`, assemble Pipeline in `bot.py`
2. **Frontend**: Merge to `main`, verify Vite build works
3. Test end-to-end flow: Speak → Backend processes → Frontend displays
4. Run integration tests with Daily.co room

## 📊 Pipeline Architecture

```
Stage 1: DailyTransport (WebRTC Audio) + Silero VAD
                    ↓
Stage 2: GroqSTTService (Whisper Large v3 Turbo, 400-800ms)
                    ↓
Stage 3: SentenceAggregator (Custom FrameProcessor)
                    ↓
Stage 4: ClaimExtractor (Groq Llama 3.1 8B, JSON mode, 50-150ms)
                    ↓
Stage 5: WebFactChecker (Exa Search 300-600ms + Groq LLM 50-150ms)
                    ↓
Stage 6: FactCheckMessenger (Daily CallClient chat, 50-100ms)
```

**Total Latency**: 1.2-2.25s from speech end to chat message delivery

## ⏱️ Timeline (24 hours, 3-person team)

| Hour | Developer A (Backend) | Developer B (Backend) | Developer C (Frontend) |
|------|----------------------|----------------------|------------------------|
| 0-1  | Project setup + Stage 1 | Stage 4 (ClaimExtractor) | Daily.co setup + Vue.js init |
| 1-2  | Stage 1 (DailyTransport) | Stage 4 continued | CallObject integration |
| 2-3  | Stage 2 (GroqSTTService) | Stage 5 (WebFactChecker) | CallObject event handlers |
| 3-4  | Stage 2 continued | Stage 5 continued | Fact-check display |
| 4-5  | Stage 3 (SentenceAggregator) | Stage 6 (sendAppMessage) | Fact-check display styling |
| 5-6  | Stage 3 continued | Optimisation + Stage 6 | Participant tiles + polish |
| 6-8  | Integration support | Backend integration + manual testing | End-to-end demo preparation |

**Key Milestones**:
- Hour 2: All stages have basic implementation started
- Hour 4: Individual components ready for integration
- Hour 6: Frontend complete, backend integration complete
- Hour 8: Fully integrated, demo-ready MVP

## 🎯 Success Metrics

- **Latency**: 1.2-2.25s end-to-end (speech end to frontend display)
- **Accuracy**: > 85% for clear factual claims
- **Reliability**: Zero crashes during 10-minute demo
- **Backend**: All 6 stages functional and connected
- **Frontend**: Verdict cards render within 100ms of app message receipt
- **Daily.co**: Stable WebRTC connection with <1% packet loss
- **UI**: Responsive, branded interface with correct status colours

## 🤝 Communication

- **Standup**: Every 2 hours (5 min max)
- **Blockers**: Raise immediately if stuck > 20 min
- **Integration**: Coordinate during hours 5-6
- **Demo Prep**: All developers focus on integration from hour 6

## 📝 Important Notes

1. **Phase 1 Scope Only**: Web search via Exa, no BM25, no Supabase
2. **Pipecat Framework**: Use Pipecat FrameProcessor pattern for all stages
3. **Triple-Client Architecture**: Vue.js CallObject (frontend) + DailyTransport (audio) + CallClient (app messages)
4. **Custom Frames**: Use ClaimFrame and VerdictFrame for data flow
5. **Git Discipline**: Feature branches (dev-a-*, dev-b-*, dev-c-*), conventional commits
6. **Verify Early**: Manually verify each stage before integration
7. **Performance First**: Target 1.2-2.25s total latency

## 🏆 Deliverables

By hour 6, each developer should have:
- ✅ Assigned stages implemented as FrameProcessors
- ✅ Custom frames defined (if applicable)
- ✅ Factory functions for stage creation
- ✅ Manual verification completed
- ✅ Integration-ready code merged to main

By hour 8 (demo time):
- ✅ Complete `bot.py` with 6-stage Pipeline
- ✅ Daily.co room configured and tested
- ✅ End-to-end latency within 1.2-2.25s
- ✅ Fact-check results displaying in Vue.js frontend
- ✅ Demo script prepared with test claims

## 🛠️ Technology Stack

**Backend Framework**:
- Pipecat (v0.0.x) - Real-time voice AI pipeline
- daily-python (v0.10+) - CallClient for app messages
- Daily.co - WebRTC infrastructure

**Frontend Framework**:
- Vue.js 3 - Reactive UI framework
- Vite - Build tool and dev server
- @daily-co/daily-js (v0.73+) - CallObject SDK

**AI Services**:
- Groq Whisper Large v3 Turbo (STT, 400-800ms)
- Groq Llama 3.1 8B Instant (LLM, 50-150ms)
- Exa Neural Search (web search, 300-600ms)

**Infrastructure**:
- Python 3.11+ (backend)
- Node.js 18+ (frontend)
- AsyncIO for async processing
- Pydantic for data validation
- Loguru for structured logging

## Need Help?

1. Check component guide for detailed implementation
2. Review [07_integration_layer.md](07_integration_layer.md) for Pipeline examples
3. Ask team member with adjacent stage (e.g., Stage 4 ↔ Stage 5)
4. Check Pipecat docs: https://docs.pipecat.ai
5. Raise blocker in standup if stuck > 20 min

Good luck with the hackathon!
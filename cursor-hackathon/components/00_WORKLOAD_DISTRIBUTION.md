# Workload Distribution Guide

## Team Size: 3 developers for 24-hour hackathon (Phase 1 MVP)

## Phase 1 Scope (Web Search Only)

**Critical MVP Requirements:**
- Pipecat + Daily.co hybrid architecture
- Groq Whisper STT (400-800ms latency)
- Exa web search only (no internal RAG/BM25)
- No database persistence (in-memory operation)
- Vue.js custom frontend with integrated fact-check display

**Deferred to Phase 2:**
- BM25 internal search
- Supabase database persistence
- Drift detection
- TTS nudging
- Speaker diarisation

---

## Component Breakdown & Time Estimates (3 Developers)

### Developer A: Pipecat Pipeline Foundation (8 hours)

**Deliverables:** Stages 1-3 (Audio → Sentences)

**H 0-2: Project Setup & Stage 1 (DailyTransport)**
- Owner: Developer A
- Dependencies: None
- Tasks:
  - Create project structure with uv
  - Configure `pyproject.toml` with Pipecat dependencies (`pipecat-ai`, `pipecat-ai[daily]`, `pipecat-ai[silero]`, `daily-python`)
  - Set up `.env` and configuration management (Pydantic Settings)
  - Implement DailyTransport with Silero VAD
  - Test audio reception from Daily room
- Output: `bot.py`, `src/utils/config.py`, DailyTransport initialisation

**H 2-4: Stage 2 (GroqSTTService)**
- Owner: Developer A
- Dependencies: Stage 1
- Tasks:
  - Integrate Pipecat's built-in GroqSTTService
  - Configure Whisper Large v3 Turbo model
  - Test transcription with sample audio
  - Verify VAD integration (Silero)
  - Logging setup for transcription latency
- Output: STT integration in pipeline

**H 4-6: Stage 3 (SentenceAggregator)**
- Owner: Developer A
- Dependencies: Stage 2
- Tasks:
  - Implement custom FrameProcessor for sentence boundary detection
  - Add buffer management logic (TextFrame → LLMMessagesFrame)
  - Regex-based sentence completion detection
  - Manual integration testing with Stages 1-2
  - Verify aggregation logic with sample inputs
- Output: `src/processors/sentence_aggregator.py`

**H 6-8: Integration Support**
- Owner: Developer A
- Dependencies: Stages 4-6
- Tasks:
  - Help integrate all 6 stages into complete pipeline
  - Debug frame flow issues (frame type mismatches, async errors)
  - Performance profiling (per-stage latency logging)
  - Documentation for pipeline assembly
- Output: Complete working pipeline in `bot.py`

---

### Developer B: Claim Processing (Stages 4-5) (8 hours)

**Deliverables:** Stages 4-5 (Sentences → Verdicts)

**H 0-2: Stage 4 (ClaimExtractor)**
- Owner: Developer B
- Dependencies: None (can develop independently)
- Tasks:
  - Implement ClaimExtractor FrameProcessor
  - Configure Groq LLM client with JSON mode
  - Design claim extraction prompt (system + user messages)
  - Define ClaimFrame data structure (Pydantic model)
  - Manual testing with sample sentences
  - Handle empty claim arrays gracefully
- Output: `src/processors/claim_extractor.py`, `src/frames/custom_frames.py` (ClaimFrame)

**H 2-5: Stage 5 (WebFactChecker)**
- Owner: Developer B
- Dependencies: Stage 4
- Tasks:
  - Implement Exa API client wrapper
  - Create WebFactChecker FrameProcessor
  - Add in-memory caching logic (dict with claim text as key)
  - Implement Groq verification with JSON mode
  - Define VerdictFrame data structure (Pydantic model)
  - Manual testing with sample claims
  - Handle no-results scenario (return `not_found` verdict)
- Output: `src/processors/web_fact_checker.py`, `src/services/exa_client.py`, `src/frames/custom_frames.py` (VerdictFrame)

**H 5-7: Optimisation, Caching & Stage 6 (App Messages)**
- Owner: Developer B
- Dependencies: Stage 5
- Tasks:
  - Tune Exa search parameters (`use_autoprompt=True`, domain filtering)
  - Optimise Groq verification prompt (concise output, JSON schema)
  - Implement Stage 6: FactCheckMessenger with `sendAppMessage()`
  - Design JSON message format for frontend consumption
  - Add latency logging for Exa search and Groq verify
  - Test app message broadcasting
- Output: Optimised search/verify logic, `src/processors/fact_check_messenger.py`

**H 7-8: Backend Integration & Manual Testing**
- Owner: Developer B
- Dependencies: Developer A's pipeline (Stages 1-3)
- Tasks:
  - Integrate with Developer A's pipeline (Stages 1-5)
  - Test end-to-end claim extraction → verification → app message flow
  - Debug edge cases (malformed JSON, empty search results)
  - Manually test CallClient.sendAppMessage() with real Daily room
  - Documentation for claim processing stages
- Output: Complete backend (Stages 1-6) integrated and tested

---

### Developer C: Vue.js Frontend + Daily.co Infrastructure (8 hours)

**Deliverables:** Custom Vue.js frontend + Daily.co setup + E2E Testing

**H 0-1: Project Setup & Daily.co Infrastructure**
- Owner: Developer C
- Dependencies: None
- Tasks:
  - Set up Daily.co account and obtain API key
  - Create test room via Daily API (https://api.daily.co/v1/rooms)
  - Initialise Vue.js project with Vite (`npm create vite@latest frontend -- --template vue`)
  - Install dependencies (`@daily-co/daily-js`, `vue`)
  - Configure `.env.local` with Daily room URL
  - Verify Vite dev server runs (`npm run dev`)
- Output: `frontend/` directory, Daily.co room created, Vite running

**H 1-3: Daily CallObject Integration**
- Owner: Developer C
- Dependencies: Project setup
- Tasks:
  - Implement `useDaily.js` composable for CallObject management
  - Add join/leave functionality
  - Implement event handlers (joined-meeting, participant-joined, etc.)
  - Create `CallControls.vue` component (mic/camera toggles)
  - Test audio connection with Daily room
  - Verify participant tracking updates correctly
- Output: `src/composables/useDaily.js`, `src/components/CallControls.vue`

**H 3-5: Fact-Check Display & App Message Handling**
- Owner: Developer C
- Dependencies: CallObject integration
- Tasks:
  - Implement `useFactCheck.js` composable for app message handling
  - Add 'app-message' event listener
  - Create `FactCheckDisplay.vue` component for verdict cards
  - Design verdict card styling (status-based colours, icons)
  - Test app message reception with mock data
  - Implement verdict list with Vue reactivity
- Output: `src/composables/useFactCheck.js`, `src/components/FactCheckDisplay.vue`

**H 5-6: Participant Display & Polish**
- Owner: Developer C
- Dependencies: Fact-check display
- Tasks:
  - Create `ParticipantTile.vue` component for video tiles
  - Implement video track rendering
  - Add participant grid layout (CSS Grid)
  - Polish UI styling (dark theme, responsive design)
  - Add loading states and error handling
  - Test with multiple participants
- Output: `src/components/ParticipantTile.vue`, complete UI

**H 6-8: Integration Testing & Demo Preparation**
- Owner: Developer C
- Dependencies: Backend (Developers A+B), Frontend complete
- Tasks:
  - Test end-to-end flow (speak → backend processes → frontend displays)
  - Verify all 5 test claims display correctly
  - Test verdict card formatting (evidence links, timestamps)
  - Verify latency targets (≤2.25s perception)
  - Create demo script with 5 test claims
  - Record demo video as backup
  - Test with 2-3 simultaneous participants
- Output: Demo script, fully tested application, demo video

---

## Parallel Integration Timeline (All Developers)

### H 8-12: Full Pipeline Integration (All Developers)

**H 8-10: Integration & Debugging**
- All developers collaborate
- Tasks:
  - Assemble all 6 stages into complete pipeline
  - Run end-to-end manual tests with real Daily room
  - Debug frame flow issues (type mismatches, missing frames)
  - Fix race conditions or async bugs (CallClient join timing)
  - Verify triple-client pattern works correctly
- Output: Fully integrated working bot

**H 10-12: Manual Testing & Refinement**
- All developers collaborate
- Tasks:
  - Manually test with demo script (5 test claims)
  - Verify latency targets (≤2.25s total)
  - Fix critical bugs (JSON parsing, API errors)
  - Improve error handling (graceful degradation)
  - Add comprehensive logging for debugging
- Output: Manually tested, refined bot

---

### H 12-16: Final Polish (All Developers)

**H 12-14: Edge Case Handling**
- All developers collaborate
- Tasks:
  - Test with no search results (return `not_found` verdict)
  - Test with ambiguous claims (return `unclear` verdict)
  - Test with malformed speech (handle gracefully, log errors)
  - Test concurrent speakers (ensure no frame loss)
  - Test with poor audio quality
- Output: Robust edge case handling

**H 14-16: Documentation & Demo Prep**
- All developers collaborate
- Tasks:
  - Complete README with setup instructions (uv sync, .env setup, Daily room creation)
  - Document known limitations (no internal KB, no persistence, etc.)
  - Practice demo presentation (divide speaking roles)
  - Prepare talking points (architecture overview, latency targets, Phase 2 roadmap)
  - Create fallback slides (in case live demo fails)
- Output: Complete documentation, demo-ready

---

## Git Workflow (3 Developers)

Each developer works on feature branches:

**Developer A:**
- `feature/pipecat-foundation` (Stages 1-3, pipeline assembly)
- Repository: `backend/`

**Developer B:**
- `feature/claim-processing` (Stages 4-6)
- Repository: `backend/`

**Developer C:**
- `feature/vue-frontend` (Vue.js application)
- Repository: `frontend/`

**Integration:**
- Backend merges to `main` branch when Stages 1-6 complete (H 8)
- Frontend merges to `main` branch when UI complete (H 6)
- Full integration testing in `main` (H 6-8)
- Final polish and demo prep (H 8+)

---

## Communication Protocol

1. **Standup every 4 hours** (5 minutes max)
   - What I completed since last standup
   - What I'm working on next
   - Any blockers or questions

2. **Shared status document** (Google Doc or Notion)
   - Current task
   - Blockers (API quota issues, dependency conflicts, etc.)
   - Questions for other developers

3. **Interface contracts defined in first hour**
   - Frame data structures (ClaimFrame, VerdictFrame) documented in `src/frames/custom_frames.py`
   - FrameProcessor interfaces documented in each processor file
   - Configuration settings documented in `src/utils/config.py`

4. **Testing data shared in `/scripts` folder**
   - `demo_script.txt` with 5 test claims
   - Sample audio files (if needed)
   - Expected verdicts for each claim

---

## Success Criteria for Each Component

**Stage 1 (DailyTransport):**
- Bot joins Daily room successfully
- Audio received from room participants
- VAD correctly detects speech vs silence
- Manual verification of audio reception working

**Stage 2 (GroqSTTService):**
- Transcription accuracy >90% on clean speech
- Latency ≤800ms per utterance
- Integration with VAD working
- TextFrame emitted correctly

**Stage 3 (SentenceAggregator):**
- Sentence boundary detection >95% accurate
- LLMMessagesFrame emitted only on sentence completion
- Buffer management prevents memory leaks
- Manual verification with sample sentences

**Stage 4 (ClaimExtractor):**
- JSON parsing success rate >99%
- Claims extracted from verifiable statements only
- ClaimFrame emitted with correct structure
- Manual testing with 10+ sample sentences

**Stage 5 (WebFactChecker):**
- Exa search returns relevant results for 80% of claims
- Groq verification returns valid JSON verdict
- Cache hit rate >50% on repeated claims
- VerdictFrame emitted with all required fields

**Stage 6 (FactCheckMessenger):**
- App messages broadcast successfully
- JSON message format correct (type, claim, status, etc.)
- CallClient.sendAppMessage() works without errors
- Messages received by frontend 'app-message' listener

**Frontend (Vue.js):**
- Daily CallObject joins room successfully
- App messages received and parsed correctly
- Verdict cards render with correct styling
- Participant video tiles display correctly
- Microphone/camera controls functional

---

## Risk Mitigation

**Risk 1: Groq API quota exceeded**
- Mitigation: Monitor usage, implement caching aggressively, use free tier wisely

**Risk 2: Exa search returns no results**
- Mitigation: Handle gracefully with `not_found` verdict, expand allow-list domains

**Risk 3: Daily.co room setup issues**
- Mitigation: Developer C sets up early (H 0-2), document process thoroughly

**Risk 4: Frame flow bugs in Pipecat**
- Mitigation: Add extensive logging, use Pipecat examples as reference

**Risk 5: Integration delays**
- Mitigation: Define interfaces clearly in H 0-1, test components independently first

**Fallback Plan:**
- If any component blocked >1 hour, reassign resources
- Focus on "working demo" over "perfect code"
- Document all shortcuts for post-hackathon cleanup

---

## Phase 1 vs Phase 2 Separation

**Phase 1 (24h MVP):**
- Pipecat pipeline (Stages 1-6)
- Groq Whisper STT + Groq LLM
- Exa web search only
- Vue.js custom frontend with app message display
- In-memory operation (no database)

**Phase 2 (Future):**
- Add BM25 internal search (`bm25s` library)
- Add Supabase database (meetings, claims, verdicts, kb_docs, kb_chunks)
- Add drift detection (compare to meeting objective)
- Add TTS nudging (Pipecat TTS output)
- Add speaker diarisation (Deepgram or Pyannote)

---

## Dependencies & Technology Stack

**Core Framework:**
- `pipecat-ai>=0.0.39` - Core framework
- `pipecat-ai[daily]>=0.0.39` - Daily.co transport
- `pipecat-ai[silero]>=0.0.39` - VAD support

**Daily.co:**
- `daily-python>=0.10.1` - CallClient for chat

**LLM & Search:**
- `groq>=0.8.0` - Groq Whisper STT + Llama LLM
- `exa-py>=1.0.0` - Exa neural search

**Utilities:**
- `pydantic>=2.6.0` - Data validation
- `pydantic-settings>=2.2.0` - Configuration management
- `python-dotenv>=1.0.0` - Environment variables

**Development (Python):**
- `ipython>=8.22.0` - Interactive Python shell

**Frontend (JavaScript):**
- `@daily-co/daily-js>=0.73.0` - Daily CallObject SDK
- `vue>=3.2.40` - Vue.js 3 framework
- `vite>=5.4.10` - Build tool and dev server

---

## Time Buffer & Contingency

**Buffer Time:** H 16-24 (8 hours)

**If Ahead of Schedule:**
- Polish UI (better message formatting, add claim type badges)
- Add more test cases (15-20 claims instead of 5)
- Start Phase 2 features (BM25 setup, Supabase schema)

**If Behind Schedule:**
- Cut Stage 3 (SentenceAggregator) - extract claims from every TextFrame
- Simplify Stage 6 - basic text messages without emoji/markdown
- Use pre-created Daily room instead of dynamic room creation

**Critical Path (Must Complete):**
1. Stage 1 (DailyTransport) - 2 hours
2. Stage 2 (GroqSTTService) - 2 hours
3. Stage 4 (ClaimExtractor) - 2 hours
4. Stage 5 (WebFactChecker) - 3 hours
5. Stage 6 (FactCheckMessenger) - 2 hours
6. Integration - 2 hours

**Total Critical Path:** 13 hours (leaves 11 hours buffer)

---

## Demo Preparation Checklist

**H 22-24: Final Demo Prep (All Developers)**

**Technical Readiness:**
- [ ] Backend bot joins Daily room successfully
- [ ] Frontend joins Daily room and displays participants
- [ ] All 5 test claims verified correctly
- [ ] Verdict cards display in frontend with correct styling
- [ ] Latency targets met (≤2.25s for 80% of claims)
- [ ] Evidence links open in new tab
- [ ] No crashes during 10-minute test session

**Presentation Readiness:**
- [ ] Demo script rehearsed (each developer speaks for 2-3 minutes)
- [ ] Talking points prepared (architecture, custom UI, latency, Phase 2)
- [ ] Fallback slides created (architecture diagram, frontend screenshots)
- [ ] Demo video recorded (60-90 seconds, backup)
- [ ] Screenshots captured (Vue.js UI, verdict cards, participant tiles)

**Documentation Readiness:**
- [ ] README complete with setup instructions
- [ ] Architecture diagram (Mermaid or PNG)
- [ ] Known limitations documented
- [ ] Phase 2 roadmap outlined
- [ ] Code commented with docstrings

---

## Post-Hackathon Cleanup (Not During 24h)

**Technical Debt to Address:**
- Proper error handling (not just logging)
- Add test coverage if converting to production
- Performance benchmarks (latency percentiles)
- Security review (API key management, input sanitisation)

**Phase 2 Implementation:**
- BM25 internal search with Supabase
- Database persistence (meetings, claims, verdicts)
- Drift detection
- TTS nudging
- Speaker diarisation

---

## Key Success Factors

1. **Clear interface contracts** - Define frame structures early
2. **Independent development** - Minimise blockers between developers
3. **Aggressive caching** - In-memory cache for repeated claims
4. **Comprehensive logging** - Debug frame flow issues quickly
5. **Early integration** - Don't wait until H 20 to test end-to-end
6. **Focus on demo** - Working 5-claim demo > 100% test coverage

---

## Emergency Contacts & Resources

**Pipecat Documentation:**
- https://docs.pipecat.ai
- GitHub: https://github.com/pipecat-ai/pipecat

**Daily.co Documentation:**
- https://docs.daily.co/reference/daily-python
- Dashboard: https://dashboard.daily.co

**Groq Documentation:**
- https://console.groq.com/docs/quickstart
- API Keys: https://console.groq.com/keys

**Exa Documentation:**
- https://docs.exa.ai/reference/python-sdk
- Dashboard: https://dashboard.exa.ai

**Shared Resources:**
- Slack channel: #hackathon-fact-checker
- Status document: [Google Doc URL]
- Git repository: [GitHub URL]

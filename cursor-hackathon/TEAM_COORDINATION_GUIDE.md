# Team Coordination Guide - Real-Time Fact Checker Hackathon

## Overview
This guide coordinates the work of 3 developers building a real-time meeting fact-checker over 24 hours using Pipecat, Daily.co, and Vue.js.

**IMPORTANT**: The Python bot runs **on Developer A or B's laptop** (local machine), NOT in Daily's cloud. Daily.co only provides the WebRTC room infrastructure. See [BOT_DEPLOYMENT_GUIDE.md](BOT_DEPLOYMENT_GUIDE.md) for details.

## Team Structure

### Developer A: Pipecat Pipeline Foundation
- **Prompt File**: [DEVELOPER_A_PROMPT.md](DEVELOPER_A_PROMPT.md)
- **Hours**: 0-8
- **Deliverables**: Stages 1-3 (DailyTransport, STT, SentenceAggregator)
- **Key Files**:
  - `backend/bot.py`
  - `backend/src/services/daily_transport_service.py`
  - `backend/src/services/stt_service.py`
  - `backend/src/processors/sentence_aggregator.py`
  - `backend/src/frames/custom_frames.py`
  - `backend/src/utils/config.py`

### Developer B: Claim Processing & App Messages
- **Prompt File**: [DEVELOPER_B_PROMPT.md](DEVELOPER_B_PROMPT.md)
- **Hours**: 0-8
- **Deliverables**: Stages 4-6 (ClaimExtractor, WebFactChecker, FactCheckMessenger)
- **Key Files**:
  - `backend/src/processors/claim_extractor.py`
  - `backend/src/processors/web_fact_checker.py`
  - `backend/src/processors/fact_check_messenger.py`
  - `backend/src/services/exa_client.py`
  - `backend/src/services/daily_message_client.py`

### Developer C: Vue.js Frontend
- **Prompt File**: [DEVELOPER_C_PROMPT.md](DEVELOPER_C_PROMPT.md)
- **Hours**: 0-8
- **Deliverables**: Custom Vue.js UI with Daily.co integration
- **Key Files**:
  - `frontend/src/App.vue`
  - `frontend/src/composables/useDaily.js`
  - `frontend/src/composables/useFactCheck.js`
  - `frontend/src/components/CallControls.vue`
  - `frontend/src/components/FactCheckDisplay.vue`
  - `frontend/src/components/ParticipantTile.vue`

## Critical Integration Points

### Hour 0-1: Initial Setup
**All developers must:**
1. Read their assigned prompt file
2. Set up development environment
3. Share credentials via shared document

**Developer C must:**
- Create Daily.co account and room
- Generate bot token for Developers A & B
- Share room URL, API key, and bot token
- **Clarify**: Daily.co provides ONLY WebRTC room (NOT bot hosting)

**Developer A must:**
- Bootstrap backend project structure with `uv init`
- Create pyproject.toml
- Set up .env file with credentials from Developer C
- **Prepare to run bot locally** on their laptop
- Share project structure with Developer B

### Hour 1-2: First Coordination
**Developer A ↔ Developer B:**
- Share `custom_frames.py` (ClaimFrame, VerdictFrame definitions)
- Agree on LLMMessagesFrame format
- Verify frame types compatible

**Developer C:**
- Test Daily CallObject independently
- Prepare for app message integration

### Hour 5-6: Major Integration
**Developer B → Developer C:**
- Share app message format specification:
  ```json
  {
    "type": "fact-check-verdict",
    "claim": "...",
    "status": "supported|contradicted|unclear|not_found",
    "confidence": 0.95,
    "rationale": "...",
    "evidence_url": "..."
  }
  ```

**Developer A ↔ Developer B:**
- Integrate Stages 4-6 into main pipeline
- Update `bot.py` with complete pipeline
- Test frame flow end-to-end

### Hour 6-8: Final Integration & Testing
**All developers:**
- Join same Daily room
- Run end-to-end test
- Speak test claims
- Verify verdicts appear in frontend
- Debug issues collaboratively

**Bot deployment workflow:**
1. **Developer A or B**: Start bot locally
   ```bash
   cd backend
   uv run python bot.py
   ```
2. **Verify**: Check logs show "Connected to Daily room"
3. **Keep terminal open** - bot must keep running during entire demo
4. **Developer C**: Open frontend in browser
   ```bash
   cd frontend
   npm run dev
   # Open http://localhost:5173
   ```
5. **All**: Join Daily room and test

## Communication Protocol

### Standup Schedule (Every 2 hours)
- **Hour 0**: Kickoff, share credentials, **clarify bot runs locally**
- **Hour 2**: Progress update, share frame definitions
- **Hour 4**: Integration checkpoint, verify bot can join room
- **Hour 6**: Final integration, **start bot on Developer A/B's laptop**
- **Hour 8**: Demo preparation, **ensure bot stays running**

### Blocker Protocol
- If stuck >20 minutes, notify team immediately
- Use shared chat/document for quick questions
- Don't wait for next standup to raise issues

### Shared Resources Document
Create a shared document (Google Doc/Notion) with:
```
## Credentials (DO NOT COMMIT)
DAILY_API_KEY: ...
DAILY_ROOM_URL: https://your-domain.daily.co/fact-checker-demo
DAILY_BOT_TOKEN: ...
GROQ_API_KEY: ...
EXA_API_KEY: ...

## Status Updates
Developer A: [status]
Developer B: [status]
Developer C: [status]

## Blockers
- [timestamp] Developer X: [blocker description]

## Integration Notes
- Frame format: [agreed format]
- App message format: [agreed format]
```

## Testing Strategy

### Manual Test Claims
All developers should test with these claims:

1. **Supported**: "Python 3.12 removed the distutils package."
2. **Supported**: "GDPR requires breach notification within 72 hours."
3. **Supported**: "React 18 introduced automatic batching."
4. **Contradicted**: "PostgreSQL 15 uses LLVM JIT compilation by default."
5. **Unclear**: "Kubernetes uses iptables by default in v1.29."

### Success Criteria Checklist

**Developer A (Hour 6)**:
- [ ] Bot joins Daily room
- [ ] VAD detects speech
- [ ] Transcriptions appear in logs (<800ms latency)
- [ ] Sentences aggregated correctly

**Developer B (Hour 7)**:
- [ ] Claims extracted from sentences (>99% JSON success)
- [ ] Web search returns results
- [ ] Verdicts generated with evidence
- [ ] App messages sent to frontend

**Developer C (Hour 6)**:
- [ ] Vue.js app runs locally
- [ ] CallObject joins Daily room
- [ ] Participant video displays
- [ ] App message listener working

**All Developers (Hour 8)**:
- [ ] End-to-end flow works (speech → verdict card)
- [ ] All 5 test claims verified
- [ ] Latency <2.5s total
- [ ] Verdict cards colour-coded correctly
- [ ] Demo script prepared

## Git Workflow

### Branch Strategy
```bash
# Developer A
git checkout -b dev-a-pipeline-foundation

# Developer B
git checkout -b dev-b-claim-processing

# Developer C
git checkout -b dev-c-vue-frontend
```

### Commit Style (Conventional Commits)
```bash
# Examples
git commit -m "feat(transport): add DailyTransport with VAD"
git commit -m "feat(stt): integrate Groq Whisper service"
git commit -m "feat(claims): add ClaimExtractor with JSON mode"
git commit -m "feat(ui): add verdict card component"
git commit -m "fix(pipeline): resolve frame type mismatch"
```

### Merge Strategy
- Developer A creates main pipeline structure first
- Developer B merges into dev-a branch for integration
- Developer C works independently until Hour 6
- Final merge to main after successful E2E test

## Troubleshooting Guide

### Common Issues

**Issue**: Bot doesn't join Daily room
- **Owner**: Developer A
- **Fix**:
  - Check DAILY_ROOM_URL and DAILY_BOT_TOKEN in .env
  - Verify bot is running locally: `uv run python bot.py`
  - Check terminal output for connection errors
  - Verify token hasn't expired (regenerate via Daily API if needed)

**Issue**: No transcriptions appearing
- **Owner**: Developer A
- **Fix**: Verify GROQ_API_KEY, check VAD threshold

**Issue**: Claims not extracting
- **Owner**: Developer B
- **Fix**: Verify Groq JSON mode enabled, check prompt

**Issue**: No search results from Exa
- **Owner**: Developer B
- **Fix**: Check allowed_domains list, verify EXA_API_KEY

**Issue**: App messages not reaching frontend
- **Owner**: Developer B & C
- **Fix**: Verify CallClient joined room, check 'app-message' listener

**Issue**: Verdict cards not rendering
- **Owner**: Developer C
- **Fix**: Check app message format matches expected

**Issue**: Video not displaying
- **Owner**: Developer C
- **Fix**: Check browser camera permissions, verify CallObject tracks

### Debug Commands

```bash
# Check if Daily room exists
curl -H "Authorization: Bearer $DAILY_API_KEY" \
  https://api.daily.co/v1/rooms/fact-checker-demo

# Test Groq API
curl -X POST https://api.groq.com/openai/v1/chat/completions \
  -H "Authorization: Bearer $GROQ_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model": "llama3.1-8b-instant", "messages": [{"role": "user", "content": "test"}]}'

# Test Exa API
curl -X POST https://api.exa.ai/search \
  -H "x-api-key: $EXA_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query": "Python 3.12", "numResults": 2}'
```

## Demo Preparation (Hour 8)

### Pre-Demo Checklist
- [ ] **Backend bot running** on Developer A/B's laptop: `uv run python bot.py`
- [ ] **Verify bot connected**: Check logs for "Connected to Daily room"
- [ ] **Keep terminal open** - don't close it during demo!
- [ ] **Laptop plugged into power** to prevent sleep
- [ ] Frontend running on localhost:5173
- [ ] Browser joined Daily room
- [ ] All test claims working
- [ ] Screen recording software ready
- [ ] Backup demo video recorded

### Demo Flow (5 minutes)
1. **Introduction** (30s): Explain problem and solution
2. **Setup** (30s):
   - **Verify bot running** in terminal (show logs briefly)
   - Join call in browser
   - Show UI
3. **Live Demo** (3 mins):
   - Speak 3 test claims
   - Show verdict cards appearing in real-time
   - Click evidence links
   - Highlight colour coding
4. **Wrap-up** (1 min): Summary and Q&A

**During Demo**:
- **Do NOT close the terminal** where bot.py is running
- If bot crashes: `Ctrl+C` → `uv run python bot.py` to restart
- Have backup video ready if live demo fails

### Talking Points
- **Real-time**: <2.5s latency from speech to verdict
- **Evidence-backed**: Every verdict has source URL
- **Custom UI**: Fully branded, not Daily Prebuilt
- **Accurate**: Groq LLM + Exa neural search
- **Scalable**: Triple-client architecture supports multiple participants

## Post-Hackathon Cleanup

### If Converting to Production
1. Add test coverage (pytest for backend, Vitest for frontend)
2. Implement error handling and retries
3. Add database persistence (Supabase)
4. Implement BM25 internal search
5. Add security review (API key management)
6. Performance benchmarking
7. Multi-user authentication

### Technical Debt Documented
See `components/00_WORKLOAD_DISTRIBUTION.md` for full list

## Documentation References

- **Bot Deployment**: [BOT_DEPLOYMENT_GUIDE.md](BOT_DEPLOYMENT_GUIDE.md) - **READ THIS FIRST!**
- Architecture: [architecture_design.md](architecture_design.md)
- Workload Distribution: [components/00_WORKLOAD_DISTRIBUTION.md](components/00_WORKLOAD_DISTRIBUTION.md)
- How It Works: [HOW_IT_ALL_WORKS.md](HOW_IT_ALL_WORKS.md)
- Component Specs: [components/](components/)

## Emergency Contacts

During hackathon, maintain a shared contact list:
- Developer A: [contact]
- Developer B: [contact]
- Developer C: [contact]

---

**Remember**: Communication is key. Raise blockers early, coordinate often, and help each other succeed. You've got this! 🚀

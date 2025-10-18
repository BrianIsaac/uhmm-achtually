# Quick Start: Fact-Checking Bot V2

## 30-Second Setup

```bash
# 1. Start ngrok (Terminal 1)
~/.local/bin/ngrok http 7014

# 2. Start API server (Terminal 2)
cd meeting-baas-speaking
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 7014

# 3. Deploy bot (Terminal 3)
cd meeting-baas-speaking
uv run python deploy_fact_checker_v2.py https://zoom.us/j/YOUR_MEETING_ID
```

## Test It

Join the Zoom meeting and say:
> "Python 3.12 removed distutils from the standard library"

Bot should respond:
> "Fact check: The claim Python 3.12 removed distutils from the standard library is supported."

## What's Different from V1?

- **V1:** Uses Pipecat frames throughout → frame conversion issues
- **V2:** Only uses frames for STT/TTS → PydanticAI handles fact-checking directly

## Key Files

| File | Purpose |
|------|---------|
| [scripts/fact_checking_bot_v2_pydantic.py](meeting-baas-speaking/scripts/fact_checking_bot_v2_pydantic.py) | Main V2 bot implementation |
| [deploy_fact_checker_v2.py](meeting-baas-speaking/deploy_fact_checker_v2.py) | Quick deployment script |
| [@personas/fact_checker_v2/](meeting-baas-speaking/@personas/fact_checker_v2/) | Persona configuration |
| [README_FACT_CHECKER_V2.md](meeting-baas-speaking/README_FACT_CHECKER_V2.md) | Full documentation |

## Architecture

```
Meeting → Meeting BaaS Bot → WebSocket
                               ↓
                    STT (Groq Whisper)
                               ↓
                    SentenceBuffer (simple text aggregation)
                               ↓
                    PydanticAI Bridge
                    ├─ Extract claims (Groq)
                    ├─ Fact-check (Exa + Groq)
                    └─ Format for speech
                               ↓
                    TTS (ElevenLabs)
                               ↓
                    Bot speaks in meeting
```

## Requirements

- API keys in [.env](meeting-baas-speaking/.env):
  - `MEETING_BAAS_API_KEY`
  - `GROQ_API_KEY`
  - `EXA_API_KEY`
  - `ELEVENLABS_API_KEY`

- Backend V2 processors (already exist):
  - [backend/src/processors_v2/pipeline_coordinator.py](backend/src/processors_v2/pipeline_coordinator.py)
  - [backend/src/processors_v2/claim_extractor_v2.py](backend/src/processors_v2/claim_extractor_v2.py)
  - [backend/src/processors_v2/web_fact_checker_v2.py](backend/src/processors_v2/web_fact_checker_v2.py)

## Troubleshooting

**Bot doesn't join:**
- Check Meeting BaaS API key
- Verify meeting URL is correct
- Ensure meeting has started

**No verdicts spoken:**
- Check ElevenLabs API key
- Verify claims are being extracted (check logs)
- Ensure sentences end with punctuation

**WebSocket errors:**
- Ensure ngrok is running
- Check port 7014 is not blocked
- Verify ngrok URL matches configuration

## Full Documentation

See [IMPLEMENTATION_SUMMARY_V2.md](IMPLEMENTATION_SUMMARY_V2.md) for complete details.

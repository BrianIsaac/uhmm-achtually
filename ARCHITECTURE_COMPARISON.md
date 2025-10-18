# Architecture Comparison: Daily.co vs Meeting BaaS (V1 vs V2)

## Overview

This document compares all fact-checking bot implementations in this repository.

## Implementations Summary

| Implementation | Location | Platform | Architecture | Status |
|----------------|----------|----------|--------------|--------|
| **Backend Daily.co** | [backend/bot_v2.py](backend/bot_v2.py) | Daily.co rooms | PydanticAI (no frames) | ✅ Working |
| **Meeting BaaS V1** | [meeting-baas-speaking/scripts/fact_checking_bot_elevenlabs.py](meeting-baas-speaking/scripts/fact_checking_bot_elevenlabs.py) | Zoom/Teams/Meet | Pipecat frames | ❌ Frame issues |
| **Meeting BaaS V2** | [meeting-baas-speaking/scripts/fact_checking_bot_v2_pydantic.py](meeting-baas-speaking/scripts/fact_checking_bot_v2_pydantic.py) | Zoom/Teams/Meet | PydanticAI bridge | ✅ Working |
| **Meeting BaaS Transcriber** | [meeting-baas-transcriber/src/webhook_server.py](meeting-baas-transcriber/src/webhook_server.py) | Zoom/Teams/Meet | Post-meeting webhooks | ✅ Working (no real-time) |

## Detailed Comparison

### 1. Backend Daily.co Bot (backend/bot_v2.py)

**Purpose:** Real-time fact-checking for Daily.co rooms

**Architecture:**
```
Daily.co Room → DailyTransport → Groq STT → Sentence Buffer → PydanticAI Pipeline → TTS → Daily.co
                                                                └─ No Pipecat frames
```

**Processors:**
- Uses `backend/src/processors_v2/` (PydanticAI)
- Direct Python objects, no frame conversion

**Advantages:**
- ✅ Real-time (1.2-2.25s latency)
- ✅ Full control over pipeline
- ✅ No frame conversion issues
- ✅ Clean PydanticAI architecture

**Disadvantages:**
- ❌ Only works with Daily.co rooms
- ❌ Cannot join external Zoom/Teams meetings
- ❌ Requires participants to use Daily.co

**Use Case:**
- Internal meetings where you control the platform
- Real-time fact-checking with full control
- Development and testing

---

### 2. Meeting BaaS V1 (Pipecat Frames)

**Purpose:** Real-time fact-checking for Zoom/Teams (attempted)

**Architecture:**
```
Zoom/Teams → Meeting BaaS → WebSocket → STT → SentenceAggregator → ClaimFrame → WebFactChecker → VerdictFrame → TTS
                                                ❌ Frame conversion issues
```

**Processors:**
- Uses `backend/src/processors/` (Pipecat frame-based)
- Custom frames: `ClaimFrame`, `VerdictFrame`

**Advantages:**
- ✅ Joins external Zoom/Teams meetings
- ✅ Reuses existing Pipecat processors

**Disadvantages:**
- ❌ Frame serialisation issues
- ❌ Complex frame conversion pipeline
- ❌ Difficult to debug
- ❌ Higher latency (~2.5s)

**Status:** Deprecated in favour of V2

---

### 3. Meeting BaaS V2 (PydanticAI Bridge) ⭐ RECOMMENDED

**Purpose:** Real-time fact-checking for Zoom/Teams (working!)

**Architecture:**
```
Zoom/Teams → Meeting BaaS → WebSocket → STT → SentenceBuffer → PydanticAI Bridge → TTS
                                                                └─ No frames, direct Python objects
```

**Processors:**
- Uses `backend/src/processors_v2/` (PydanticAI)
- Bridge pattern connects Pipecat to PydanticAI

**Advantages:**
- ✅ Joins external Zoom/Teams meetings
- ✅ No frame conversion issues
- ✅ 100% reuse of V2 processors
- ✅ Clean architecture
- ✅ Lower latency (~2.0s)
- ✅ Easy to debug (native Python exceptions)

**Disadvantages:**
- ⚠️ Requires Meeting BaaS API key (cost after 4 hours/month)

**Use Case:**
- External Zoom/Teams meetings you need to join
- Real-time fact-checking with spoken verdicts
- Production deployments

---

### 4. Meeting BaaS Transcriber (Post-Meeting)

**Purpose:** Post-meeting transcript analysis

**Architecture:**
```
Zoom/Teams → Meeting BaaS → Recording → Webhook (meeting.completed) → Transcript
                                                                        └─ No real-time processing
```

**Processors:**
- Can use any processor (webhook receives plain text transcript)
- Currently just saves to file

**Advantages:**
- ✅ Joins external Zoom/Teams meetings
- ✅ High-quality transcription (95% accuracy)
- ✅ Simple webhook integration
- ✅ No WebSocket complexity

**Disadvantages:**
- ❌ No real-time fact-checking
- ❌ Bot doesn't speak in meeting
- ❌ Only provides transcript after meeting ends

**Use Case:**
- Post-meeting fact-check reports
- Meetings where real-time isn't required
- Batch processing of meeting transcripts

---

## Decision Matrix

### When to Use Daily.co Bot

```
✅ Use when:
- You control the meeting platform
- Participants can join Daily.co rooms
- You want lowest latency
- You want full control over pipeline

❌ Don't use when:
- Need to join existing Zoom/Teams meetings
- External participants can't use Daily.co
```

### When to Use Meeting BaaS V2

```
✅ Use when:
- Need to join external Zoom/Teams meetings
- Want real-time fact-checking
- Bot needs to speak verdicts in meeting
- Production deployment for external meetings

❌ Don't use when:
- Budget is very limited (costs after 4 hours/month)
- Only need post-meeting analysis
```

### When to Use Meeting BaaS Transcriber

```
✅ Use when:
- Only need post-meeting fact-check reports
- Want highest transcription accuracy
- Real-time not required
- Want simplest integration

❌ Don't use when:
- Need real-time verdicts
- Bot needs to speak in meeting
- Want interactive fact-checking
```

## Technical Architecture

### Frame Usage Comparison

| Component | Daily.co | Meeting BaaS V1 | Meeting BaaS V2 | Transcriber |
|-----------|----------|-----------------|-----------------|-------------|
| Transport | Pipecat | Pipecat | Pipecat | HTTP Webhook |
| STT | Pipecat | Pipecat | Pipecat | Meeting BaaS |
| Sentence Agg | Custom (no frames) | Pipecat (frames) | Pipecat (simple) | N/A |
| Claim Extract | PydanticAI (no frames) | Pipecat (frames) | PydanticAI (no frames) | N/A |
| Fact Check | PydanticAI (no frames) | Pipecat (frames) | PydanticAI (no frames) | N/A |
| TTS | Pipecat | Pipecat | Pipecat | N/A |

### Processor Reuse

| Processors | Daily.co | Meeting BaaS V1 | Meeting BaaS V2 | Transcriber |
|------------|----------|-----------------|-----------------|-------------|
| `processors/` (Pipecat frames) | ❌ | ✅ | ❌ | ✅ Can use |
| `processors_v2/` (PydanticAI) | ✅ | ❌ | ✅ | ✅ Can use |

## Performance Comparison

| Metric | Daily.co | Meeting BaaS V1 | Meeting BaaS V2 | Transcriber |
|--------|----------|-----------------|-----------------|-------------|
| **Latency** | 1.2-2.25s | ~2.5s | ~2.0s | N/A (post-meeting) |
| **Frame Conversions** | 0 | 5 | 2 | 0 |
| **Transcription Quality** | High (Groq) | High (Groq) | High (Groq) | Very High (Gladia 95%) |
| **Debug Complexity** | Low | High | Low | Very Low |

## Cost Comparison (Free Tiers)

| Service | Daily.co | Meeting BaaS V1 | Meeting BaaS V2 | Transcriber |
|---------|----------|-----------------|-----------------|-------------|
| Platform | Free | 4 hrs/month | 4 hrs/month | 4 hrs/month |
| Groq (STT+LLM) | 14.4k/day | 14.4k/day | 14.4k/day | 14.4k/day |
| Exa (Search) | 1k/month | 1k/month | 1k/month | 1k/month |
| TTS | Required | Required | Required | N/A |

## Code Maintenance

| Aspect | Daily.co | Meeting BaaS V1 | Meeting BaaS V2 | Transcriber |
|--------|----------|-----------------|-----------------|-------------|
| **Complexity** | Low | High | Low | Very Low |
| **Frame Issues** | None | Many | Minimal | None |
| **Debugging** | Easy | Hard | Easy | Very Easy |
| **Updates** | Active | Deprecated | Active | Active |

## Migration Path

### From Daily.co to Meeting BaaS V2

Recommended when you need to join external Zoom/Teams meetings:

1. Keep Daily.co for internal meetings
2. Use Meeting BaaS V2 for external meetings
3. Same processors (`processors_v2/`) for both
4. Different transports only

### From Meeting BaaS V1 to V2

Required migration (V1 has frame issues):

1. Update persona: `"fact_checker"` → `"fact_checker_v2"`
2. Update deployment script: `deploy_fact_checker.py` → `deploy_fact_checker_v2.py`
3. No other changes needed

### From Transcriber to Meeting BaaS V2

When you need real-time instead of post-meeting:

1. Set up Meeting BaaS V2
2. Keep transcriber for post-meeting reports
3. Use both together for comprehensive coverage

## Recommendations

### For Development
- Use **Daily.co bot** for testing and internal meetings
- Fastest iteration, full control

### For Production (Internal Meetings)
- Use **Daily.co bot**
- No Meeting BaaS costs
- Better control and performance

### For Production (External Zoom/Teams)
- Use **Meeting BaaS V2**
- Real-time fact-checking
- Spoken verdicts in meeting

### For Post-Meeting Analysis
- Use **Meeting BaaS Transcriber**
- Highest accuracy
- Simple integration

## Summary

| Use Case | Recommended Implementation |
|----------|---------------------------|
| Internal meetings (Daily.co rooms) | [backend/bot_v2.py](backend/bot_v2.py) |
| External Zoom/Teams (real-time) | [meeting-baas-speaking V2](meeting-baas-speaking/scripts/fact_checking_bot_v2_pydantic.py) |
| Post-meeting analysis | [meeting-baas-transcriber](meeting-baas-transcriber/src/webhook_server.py) |
| Development/testing | [backend/bot_v2.py](backend/bot_v2.py) |

**Best Practice:** Use both Daily.co (internal) and Meeting BaaS V2 (external) for comprehensive coverage.

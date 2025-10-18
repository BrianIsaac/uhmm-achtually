# Integration Guide: Meeting BaaS + Existing Pipecat Bot

## Overview

You have two separate systems:

1. **Existing Pipecat Bot** (`backend/bot.py`): Joins Daily.co rooms, does real-time fact-checking
2. **Meeting BaaS Bot** (new): Can join external Zoom/Teams meetings

This guide shows how to connect them so Meeting BaaS transcriptions flow through your existing fact-checking pipeline.

---

## Architecture

### Current System (Daily.co)

```
Daily.co Room
  ↓
Stage 1: DailyTransport (audio input)
  ↓
Stage 2: GroqSTTService (transcription)
  ↓
Stage 3: SentenceAggregator
  ↓
Stage 4: ClaimExtractor
  ↓
Stage 5: WebFactChecker
  ↓
Stage 6: FactCheckMessenger (sends to Daily.co chat)
```

### New System (Zoom via Meeting BaaS)

```
Zoom Meeting
  ↓
Meeting BaaS Bot (joins meeting, transcribes)
  ↓
Webhook → Your Server
  ↓
**Your existing Stages 3-6** (reuse claim extraction + fact checking!)
  ↓
Results (send back to Zoom chat OR store)
```

---

## Integration Approach

### Skip Stages 1-2 (Audio + STT)

Meeting BaaS **already does transcription** (uses Gladia Whisper-Zero, 95% accuracy).

You only need your **Stages 3-6**:
- Stage 3: SentenceAggregator ✓ (sentences already complete from Meeting BaaS)
- Stage 4: ClaimExtractor ✓ (reuse your Groq claim extraction)
- Stage 5: WebFactChecker ✓ (reuse your Exa web search + verification)
- Stage 6: Send results somewhere

---

## Implementation

### Step 1: Extract Stages 3-6 as Standalone Pipeline

Create a new file that can process text directly (bypassing audio/STT):

```python
# backend/src/services/fact_check_pipeline.py
"""
Standalone fact-checking pipeline for text input.

Reuses Stages 3-6 from Pipecat bot without audio/STT.
"""

import asyncio
from typing import List, Dict
from src.processors.claim_extractor import ClaimExtractor
from src.processors.web_fact_checker import WebFactChecker
from src.utils.config import get_settings


class TextFactCheckPipeline:
    """
    Process text through claim extraction and fact-checking.

    This bypasses Stages 1-2 (audio + STT) and directly processes
    transcribed text from Meeting BaaS.
    """

    def __init__(self):
        """Initialise pipeline with existing processors."""
        settings = get_settings()

        # Stage 4: ClaimExtractor
        self.claim_extractor = ClaimExtractor(
            groq_api_key=settings.groq_api_key
        )

        # Stage 5: WebFactChecker
        self.fact_checker = WebFactChecker(
            exa_api_key=settings.exa_api_key,
            groq_api_key=settings.groq_api_key,
            allowed_domains=settings.allowed_domains_list
        )

    async def process_text(self, text: str) -> List[Dict]:
        """
        Process transcribed text through fact-checking pipeline.

        Args:
            text: Transcribed text from Meeting BaaS

        Returns:
            List of verdicts with claims and results
        """
        verdicts = []

        # Stage 4: Extract claims
        claims = await self.claim_extractor.extract_claims(text)

        # Stage 5: Check each claim
        for claim in claims:
            verdict = await self.fact_checker.check_claim(claim)
            verdicts.append({
                'claim': claim,
                'status': verdict.status,
                'confidence': verdict.confidence,
                'rationale': verdict.rationale,
                'evidence_url': verdict.evidence_url
            })

        return verdicts


# Singleton instance
_pipeline = None

def get_fact_check_pipeline() -> TextFactCheckPipeline:
    """Get or create singleton fact-check pipeline."""
    global _pipeline
    if _pipeline is None:
        _pipeline = TextFactCheckPipeline()
    return _pipeline
```

### Step 2: Update Webhook Server to Use Pipeline

Modify your Meeting BaaS webhook to process transcriptions:

```python
# meeting-baas-transcriber/src/webhook_server.py

from backend.src.services.fact_check_pipeline import get_fact_check_pipeline

async def handle_meeting_completed(event: WebhookEvent):
    """Process transcript through fact-checking pipeline."""
    transcript_data = event.data.get("transcript", [])

    if not transcript_data:
        print("⚠️  No transcript data")
        return

    # Get fact-checking pipeline (Stages 3-6)
    pipeline = get_fact_check_pipeline()

    print(f"\n📝 Processing {len(transcript_data)} utterances...")

    all_verdicts = []

    for utterance in transcript_data:
        speaker = utterance["speaker"]
        text = utterance["text"]

        print(f"\n[{speaker}]: {text}")

        # Process through Stages 4-5 (claim extraction + fact checking)
        verdicts = await pipeline.process_text(text)

        # Display results
        for verdict in verdicts:
            print(f"  ✅ Claim: {verdict['claim']}")
            print(f"     Status: {verdict['status']}")
            print(f"     Confidence: {verdict['confidence']}")
            print(f"     Rationale: {verdict['rationale']}")
            print(f"     Evidence: {verdict['evidence_url']}")

        all_verdicts.extend(verdicts)

    # Save results
    save_verdicts_to_file(event.bot_id, all_verdicts)

    print(f"\n🎉 Processed {len(all_verdicts)} claims from meeting!")
```

### Step 3: Run Both Systems

**Terminal 1: Meeting BaaS Webhook Server**
```bash
cd meeting-baas-transcriber
uv run python run_server.py --ngrok
```

**Terminal 2: Create Meeting BaaS bot for Zoom**
```bash
cd meeting-baas-transcriber
uv run python create_bot.py <zoom_url> <webhook_url>
```

**Terminal 3 (optional): Your existing Pipecat bot for Daily.co**
```bash
cd backend
uv run python bot.py
```

Now you have:
- **Zoom meetings**: Meeting BaaS → Webhook → Fact-checking pipeline
- **Daily.co meetings**: Pipecat bot → Real-time fact-checking

---

## Code Reuse Strategy

You're reusing **100% of your fact-checking logic**:

| Component | Reused? | How? |
|-----------|---------|------|
| Stage 1 (DailyTransport) | ❌ No | Meeting BaaS handles audio |
| Stage 2 (GroqSTT) | ❌ No | Meeting BaaS transcribes (Gladia Whisper-Zero) |
| Stage 3 (SentenceAggregator) | ✅ Partial | Sentences already complete from Meeting BaaS |
| **Stage 4 (ClaimExtractor)** | ✅ YES | **100% reuse your Groq claim extraction** |
| **Stage 5 (WebFactChecker)** | ✅ YES | **100% reuse your Exa search + verification** |
| Stage 6 (Messenger) | ⚠️ Modified | Different output (not Daily.co app messages) |

---

## Benefits

### Why This Is Better Than Building Your Own Zoom Bot

1. **Transcription Quality**: Meeting BaaS uses Whisper-Zero (95% accuracy) - better than Groq
2. **No Audio Handling**: Meeting BaaS handles WebRTC, browser automation, etc.
3. **Multi-Platform**: Works with Zoom, Teams, Google Meet (same code)
4. **Code Reuse**: Your claim extraction + fact-checking logic works unchanged
5. **Zero Infrastructure**: Meeting BaaS handles bot hosting

### What You Still Control

- ✅ Claim extraction logic (your prompts, your Groq config)
- ✅ Fact-checking logic (your Exa search, your verification prompts)
- ✅ Results processing (how you display/store verdicts)
- ✅ Cost control (only pay for what you use)

---

## Next Steps

1. **Extract Stages 3-6 to standalone module** (as shown above)
2. **Update webhook to use fact-checking pipeline**
3. **Test with your 5 demo claims**:
   - "Python 3.12 removed distutils"
   - "GDPR requires 72-hour breach notification"
   - "React 18 introduced automatic batching"
   - etc.
4. **Compare results**: Meeting BaaS transcription vs Groq Whisper accuracy

---

## Cost Comparison

### Daily.co + Your Bot
- Daily.co: $0.007/min ($0.42/hour)
- Groq Whisper: Free tier
- Your pipeline: Free tier
- **Total**: ~$0.42/hour

### Zoom + Meeting BaaS + Your Pipeline
- Meeting BaaS: $0.69/hour (includes transcription)
- Your pipeline (Stages 4-5): Free tier (Groq + Exa)
- **Total**: ~$0.69/hour

**Trade-off**: Pay $0.27/hour more, but get:
- Access to external Zoom meetings (can't do this with Daily.co)
- Better transcription (95% vs 90% accuracy)
- Multi-platform support (Zoom + Teams + Meet)

---

## Alternative: Self-Host Meeting BaaS

If cost is a concern, self-host Meeting BaaS:

```bash
git clone https://github.com/Meeting-BaaS/meeting-bot-as-a-service
cd meeting-bot-as-a-service
docker-compose up
```

Then:
- Meeting BaaS: $0 (self-hosted, just server costs)
- Your pipeline: Free tier
- **Total**: ~$0 per hour (only server costs)

---

## Summary

**You don't need to rebuild anything!**

Just:
1. Create `fact_check_pipeline.py` that wraps your Stages 4-5
2. Update `webhook_server.py` to call it
3. Meeting BaaS sends transcription → Your pipeline → Results

You get the best of both worlds:
- **Your proven fact-checking logic** (claim extraction + verification)
- **Meeting BaaS infrastructure** (joins Zoom, transcribes, sends webhooks)

No duplication, maximum code reuse! 🎉

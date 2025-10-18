# Speaking Bot Integration: Real-Time Fact-Checking for Zoom/Teams

## Overview

Meeting BaaS's **speaking-meeting-bot** is built on **Pipecat** (the same framework you're using). You can directly integrate your existing ClaimExtractor and WebFactChecker processors into their pipeline.

## Why This Works

Your existing bot architecture:
```
DailyTransport → GroqSTT → SentenceAggregator → ClaimExtractor → WebFactChecker → TTS → DailyTransport
```

Meeting BaaS speaking-bot architecture (Pipecat-based):
```
MeetingBaaS WS → STT → Pipecat Pipeline (customisable!) → TTS → MeetingBaaS WS
```

**You can inject your processors directly into their pipeline!**

## Architecture

```
Zoom/Teams Meeting
  ↓
Meeting BaaS Speaking Bot (joins as participant)
  ↓ WebSocket audio stream
Your Server (Pipecat Pipeline)
  ├─ STT (Deepgram/Gladia/Your Groq)
  ├─ SentenceAggregator
  ├─ **ClaimExtractor** (your existing processor!)
  ├─ **WebFactChecker** (your existing processor!)
  └─ TTS (Cartesia/Your service)
  ↓ WebSocket audio response
Meeting BaaS Bot speaks verdict in meeting
```

## Implementation Plan

### Step 1: Clone Speaking-Meeting-Bot Repository

```bash
cd /home/brian-isaac/Documents/personal/uhmm-achtually
git clone https://github.com/Meeting-Baas/speaking-meeting-bot.git meeting-baas-speaking
cd meeting-baas-speaking
```

### Step 2: Install Dependencies

```bash
uv pip install -e .
```

### Step 3: Inject Your Processors

Modify their Pipecat pipeline to include your fact-checking processors:

```python
# meeting-baas-speaking/core/bot_service.py (modify their pipeline)

from backend.src.processors.claim_extractor import ClaimExtractor
from backend.src.processors.web_fact_checker import WebFactChecker
from backend.src.processors.sentence_aggregator import SentenceAggregator

async def create_fact_checking_pipeline(meeting_url: str):
    """Create Pipecat pipeline with fact-checking processors."""

    # Meeting BaaS WebSocket transport (replaces DailyTransport)
    transport = MeetingBaaSTransport(
        api_key=settings.meeting_baas_api_key,
        meeting_url=meeting_url
    )

    # Stage 2: STT (use their Deepgram or your Groq)
    stt = DeepgramSTTService(api_key=settings.deepgram_api_key)
    # OR: stt = GroqSTTService(api_key=settings.groq_api_key)

    # Stage 3: Your existing processor!
    sentence_aggregator = SentenceAggregator()

    # Stage 4: Your existing processor!
    claim_extractor = ClaimExtractor(groq_api_key=settings.groq_api_key)

    # Stage 5: Your existing processor!
    fact_checker = WebFactChecker(
        exa_api_key=settings.exa_api_key,
        groq_api_key=settings.groq_api_key,
        allowed_domains=settings.allowed_domains_list
    )

    # Stage 6: TTS (use their Cartesia or your service)
    tts = CartesiaTTSService(api_key=settings.cartesia_api_key)

    # Build Pipecat pipeline
    pipeline = Pipeline([
        transport,            # Input: Meeting audio
        stt,                  # Transcription
        sentence_aggregator,  # YOUR CODE
        claim_extractor,      # YOUR CODE
        fact_checker,         # YOUR CODE
        VerdictFormatter(),   # Format verdict for speech
        tts,                  # Text-to-speech
        transport             # Output: Bot speaks in meeting
    ])

    return pipeline
```

### Step 4: Create VerdictFormatter Processor

Convert VerdictFrame to natural speech:

```python
# backend/src/processors/verdict_formatter.py
"""Format VerdictFrame for TTS output."""

import logging
from pipecat.frames.frames import Frame, TextFrame
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor

from src.frames.custom_frames import VerdictFrame

logger = logging.getLogger(__name__)


class VerdictFormatter(FrameProcessor):
    """Convert VerdictFrame to natural speech text for TTS.

    Receives VerdictFrame from WebFactChecker and emits TextFrame
    formatted for speech synthesis.
    """

    def __init__(self, verbose: bool = False):
        """Initialise formatter.

        Args:
            verbose: Include full rationale and evidence URL in speech
        """
        super().__init__()
        self.verbose = verbose

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        """Format verdicts as natural speech.

        Args:
            frame: Incoming frame
            direction: Frame direction (upstream/downstream)
        """
        if isinstance(frame, VerdictFrame):
            # Format based on status
            if frame.status == "supported":
                speech = f"Fact check: The claim '{frame.claim}' is supported."
            elif frame.status == "contradicted":
                speech = f"Fact check: The claim '{frame.claim}' is contradicted."
            elif frame.status == "unclear":
                speech = f"Fact check: The claim '{frame.claim}' is unclear."
            else:  # not_found
                speech = f"Fact check: No evidence found for '{frame.claim}'."

            # Add rationale if verbose
            if self.verbose and frame.rationale:
                speech += f" {frame.rationale}"

            logger.info(f"TTS output: {speech}")

            # Emit TextFrame for TTS
            await self.push_frame(TextFrame(text=speech), direction)

        # Forward all frames
        await super().process_frame(frame, direction)
```

### Step 5: Configure Environment

```bash
cd meeting-baas-speaking
cp .env.example .env
```

Edit `.env`:

```env
# Meeting BaaS API
MEETING_BAAS_API_KEY=53ab13e35529fd09dc59a22193635d61b85b7de7df59bf8ad499bb7a5fa52a88

# Your existing API keys (from backend/.env)
GROQ_API_KEY=your_groq_key
EXA_API_KEY=your_exa_key

# STT/TTS providers (use their defaults or your own)
DEEPGRAM_API_KEY=your_deepgram_key  # OR use GROQ_API_KEY
CARTESIA_API_KEY=your_cartesia_key  # OR use your TTS

# Fact-checking config
ALLOWED_DOMAINS=stackoverflow.com,github.com,python.org,gdpr.eu,reactjs.org
```

### Step 6: Deploy Bot to Zoom/Teams Meeting

```bash
# Start the speaking bot server with fact-checking pipeline
uv run python -m app --meeting-url "https://zoom.us/j/YOUR_MEETING_ID"
```

The bot will:
1. Join the Zoom/Teams meeting as a participant
2. Listen to audio in real-time
3. Extract claims from speech
4. Fact-check using Exa + Groq
5. Speak verdicts back into the meeting via TTS

## Example Conversation Flow

**Participant:** "Python 3.12 removed distutils from the standard library."

**Bot (internal processing):**
- STT transcribes → "Python 3.12 removed distutils from the standard library."
- ClaimExtractor → Claim: "Python 3.12 removed distutils"
- WebFactChecker → Search Exa → Verify with Groq → Verdict: "supported" (0.95 confidence)
- VerdictFormatter → "Fact check: The claim 'Python 3.12 removed distutils' is supported."
- TTS → Audio output

**Bot speaks in meeting:** "Fact check: The claim 'Python 3.12 removed distutils' is supported."

## Code Reuse

| Component | Existing Bot (Daily.co) | Speaking Bot (Meeting BaaS) | Reused? |
|-----------|-------------------------|----------------------------|---------|
| Stage 1 (Transport) | DailyTransport | MeetingBaaSTransport | ❌ Different |
| Stage 2 (STT) | GroqSTT | Deepgram/Groq | ✅ Can reuse Groq |
| Stage 3 (Aggregator) | SentenceAggregator | SentenceAggregator | ✅ 100% reuse |
| **Stage 4 (Claims)** | **ClaimExtractor** | **ClaimExtractor** | ✅ **100% reuse** |
| **Stage 5 (FactCheck)** | **WebFactChecker** | **WebFactChecker** | ✅ **100% reuse** |
| Stage 6 (Output) | FactCheckMessenger | VerdictFormatter + TTS | ⚠️ Need formatter |

## Benefits

✅ **Real-time fact-checking** (1.2-2.25s latency)
✅ **Bot speaks verdicts** in meeting via TTS
✅ **100% code reuse** for claim extraction and fact-checking
✅ **Joins Zoom/Teams** (not just Daily.co)
✅ **Pipecat-native** (same framework you already use)
✅ **Open source** (Meeting BaaS speaking-bot is open source)

## Next Steps

1. Clone speaking-meeting-bot repository
2. Create VerdictFormatter processor
3. Modify their pipeline to inject ClaimExtractor + WebFactChecker
4. Test with Zoom meeting
5. Compare latency vs existing Daily.co bot

## Alternative: Fork and Customise

Instead of modifying their code, fork speaking-meeting-bot and create a `fact-checking-meeting-bot` variant:

```bash
cd /home/brian-isaac/Documents/personal/uhmm-achtually
cp -r meeting-baas-speaking fact-checking-meeting-bot
cd fact-checking-meeting-bot

# Symlink your processors
ln -s ../backend/src/processors src/fact_check_processors
ln -s ../backend/src/services src/fact_check_services
```

This gives you full control while maintaining upstream compatibility.

# Component: Integration Layer (Pipecat Pipeline)

## Owner Assignment
**Developer A: Pipecat Pipeline Foundation**
Final pipeline assembly after all stages complete (Hours 6-8)

## Time Estimate: 2 hours
- Pipeline assembly (all 6 stages): 1 hour
- Integration testing: 30 min
- Error handling and logging: 30 min

## Purpose
This component assembles all 6 pipeline stages into a complete Pipecat fact-checking bot. Unlike manual integration, Pipecat handles frame routing, async coordination, and error propagation automatically.

## Architecture Overview

**Complete 6-Stage Pipeline:**
```
Daily Room Audio (WebRTC)
    ↓
Stage 1: DailyTransport + Silero VAD
    ↓ (AudioRawFrame)
Stage 2: GroqSTTService
    ↓ (TextFrame)
Stage 3: SentenceAggregator
    ↓ (LLMMessagesFrame)
Stage 4: ClaimExtractor
    ↓ (ClaimFrame)
Stage 5: WebFactChecker
    ↓ (VerdictFrame)
Stage 6: FactCheckMessenger (CallClient)
    ↓
Daily Prebuilt Chat UI
```

## Dependencies

```toml
[project.dependencies]
pipecat-ai = ">=0.0.39"           # Core framework
pipecat-ai[daily] = ">=0.0.39"    # Daily transport
pipecat-ai[groq] = ">=0.0.39"     # Groq STT
pipecat-ai[silero] = ">=0.0.39"   # VAD
daily-python = ">=0.10.1"         # CallClient for chat
groq = ">=0.8.0"                  # Groq LLM
exa-py = ">=1.0.0"                # Exa search
pydantic = ">=2.6.0"              # Data validation
python-dotenv = ">=1.0.0"         # Environment variables
```

## Implementation Guide

### Step 1: Main Bot Entry Point (1 hour)

Create `bot.py`:

```python
"""Pipecat fact-checking bot with all 6 stages integrated."""

import asyncio
import os
import logging
from datetime import datetime
from daily import CallClient, Daily
from pipecat.pipeline import Pipeline
from pipecat.transports.daily_transport import DailyTransport
from dotenv import load_dotenv

# Import all stages
from src.services.stt_service import create_groq_stt_service
from src.services.daily_transport_service import create_daily_transport
from src.processors.sentence_aggregator import SentenceAggregator
from src.processors.claim_extractor import ClaimExtractor
from src.processors.web_fact_checker import WebFactChecker
from src.processors.fact_check_messenger import FactCheckMessengerPrebuilt

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def run_fact_checker_bot():
    """Run complete fact-checker bot with all 6 stages.

    Environment variables required:
    - DAILY_ROOM_URL: Daily.co room URL
    - DAILY_BOT_TOKEN: Daily.co bot token
    - GROQ_API_KEY: Groq API key (STT + LLM)
    - EXA_API_KEY: Exa search API key
    """
    try:
        # Validate environment
        required_vars = ["DAILY_ROOM_URL", "DAILY_BOT_TOKEN", "GROQ_API_KEY", "EXA_API_KEY"]
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

        logger.info("="*60)
        logger.info("Starting Fact-Checker Bot")
        logger.info("="*60)

        # Stage 1: DailyTransport (Audio reception)
        logger.info("Stage 1: Initialising DailyTransport...")
        transport = create_daily_transport(
            room_url=os.getenv("DAILY_ROOM_URL"),
            token=os.getenv("DAILY_BOT_TOKEN"),
            bot_name="Fact Checker",
            vad_enabled=True
        )
        logger.info("✓ DailyTransport ready")

        # Stage 2: GroqSTTService (Speech-to-text)
        logger.info("Stage 2: Initialising GroqSTTService...")
        stt_service = create_groq_stt_service(
            model="whisper-large-v3-turbo",
            language="en",
            temperature=0.2
        )
        logger.info("✓ GroqSTTService ready")

        # Stage 3: SentenceAggregator (Buffer until sentence complete)
        logger.info("Stage 3: Initialising SentenceAggregator...")
        aggregator = SentenceAggregator()
        logger.info("✓ SentenceAggregator ready")

        # Stage 4: ClaimExtractor (Extract claims with Groq)
        logger.info("Stage 4: Initialising ClaimExtractor...")
        extractor = ClaimExtractor(
            groq_api_key=os.getenv("GROQ_API_KEY"),
            model="llama-3.1-8b-instant",
            temperature=0.1
        )
        logger.info("✓ ClaimExtractor ready")

        # Stage 5: WebFactChecker (Exa search + Groq verify)
        logger.info("Stage 5: Initialising WebFactChecker...")
        allowed_domains = [
            "docs.python.org",
            "kubernetes.io",
            "owasp.org",
            "www.nist.gov",
            "postgresql.org",
            "peps.python.org"
        ]
        fact_checker = WebFactChecker(
            groq_api_key=os.getenv("GROQ_API_KEY"),
            exa_api_key=os.getenv("EXA_API_KEY"),
            allowed_domains=allowed_domains,
            model="llama-3.1-8b-instant",
            temperature=0.1
        )
        logger.info("✓ WebFactChecker ready")

        # Stage 6: FactCheckMessenger (CallClient chat delivery)
        logger.info("Stage 6: Initialising FactCheckMessenger...")
        Daily.init()

        # Create separate CallClient for chat (dual-client pattern)
        chat_client = CallClient()
        await chat_client.join(
            url=os.getenv("DAILY_ROOM_URL"),
            client_settings={"token": os.getenv("DAILY_BOT_TOKEN")}
        )
        logger.info("✓ CallClient joined room for chat")

        messenger = FactCheckMessengerPrebuilt(
            call_client=chat_client,
            bot_name="Fact Checker"
        )
        logger.info("✓ FactCheckMessenger ready")

        # Build complete pipeline
        logger.info("\nAssembling 6-stage pipeline...")
        pipeline = Pipeline([
            transport.input_processor(),   # Receive audio from Daily
            stt_service,                    # Stage 2: Transcribe
            aggregator,                     # Stage 3: Buffer sentences
            extractor,                      # Stage 4: Extract claims
            fact_checker,                   # Stage 5: Verify claims
            messenger,                      # Stage 6: Send to chat
            transport.output_processor()    # Output (not used in Phase 1)
        ])
        logger.info("✓ Pipeline assembled")

        logger.info("\n" + "="*60)
        logger.info("Bot is READY!")
        logger.info(f"Room URL: {os.getenv('DAILY_ROOM_URL')}")
        logger.info("Open the room in your browser and start speaking")
        logger.info("Verdicts will appear in the chat panel")
        logger.info("Press Ctrl+C to stop")
        logger.info("="*60 + "\n")

        # Run pipeline (blocks until stopped)
        await pipeline.run()

    except KeyboardInterrupt:
        logger.info("\n\nShutting down bot...")
    except Exception as e:
        logger.error(f"Bot error: {e}", exc_info=True)
    finally:
        # Cleanup
        try:
            await chat_client.leave()
            Daily.deinit()
            await transport.cleanup()
            logger.info("Bot stopped successfully")
        except Exception as cleanup_error:
            logger.error(f"Cleanup error: {cleanup_error}")


def main():
    """Entry point for bot."""
    asyncio.run(run_fact_checker_bot())


if __name__ == "__main__":
    main()
```

### Step 2: Custom Frame Types (shared across stages)

Create `src/frames/custom_frames.py`:

```python
"""Custom Pipecat frame types for fact-checking pipeline."""

import time
from dataclasses import dataclass
from pipecat.frames import Frame


@dataclass
class ClaimFrame(Frame):
    """Frame containing an extracted claim.

    Emitted by: ClaimExtractor (Stage 4)
    Consumed by: WebFactChecker (Stage 5)
    """
    text: str  # The claim statement
    claim_type: str  # version, api, regulatory, definition, number, decision
    timestamp: float = None  # When extracted

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()


@dataclass
class VerdictFrame(Frame):
    """Frame containing claim verification verdict.

    Emitted by: WebFactChecker (Stage 5)
    Consumed by: FactCheckMessenger (Stage 6)
    """
    claim: str  # Original claim
    status: str  # supported, contradicted, unclear, not_found
    confidence: float  # 0.0-1.0
    rationale: str  # One-sentence explanation
    evidence_url: str  # Source URL
    timestamp: float = None  # When verified

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()
```

### Step 3: Configuration Management

Create `src/utils/config.py`:

```python
"""Application configuration with Pydantic settings."""

import os
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    All settings can be overridden via .env file or environment variables.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )

    # Daily.co
    daily_api_key: str
    daily_room_url: str
    daily_bot_token: str

    # Groq
    groq_api_key: str

    # Exa
    exa_api_key: str

    # Application config
    allowed_domains: list[str] = [
        "docs.python.org",
        "kubernetes.io",
        "owasp.org",
        "www.nist.gov",
        "postgresql.org"
    ]
    bot_name: str = "Fact Checker"
    python_env: str = "development"
    log_level: str = "INFO"

    # Model configuration
    stt_model: str = "whisper-large-v3-turbo"
    llm_model: str = "llama-3.1-8b-instant"
    llm_temperature: float = 0.1


@lru_cache
def get_settings() -> Settings:
    """Get cached application settings.

    Returns:
        Settings instance with all configuration
    """
    return Settings()


# Validation helper
def validate_environment() -> list[str]:
    """Validate required environment variables are set.

    Returns:
        List of missing variable names (empty if all present)
    """
    required = [
        "DAILY_ROOM_URL",
        "DAILY_BOT_TOKEN",
        "GROQ_API_KEY",
        "EXA_API_KEY"
    ]
    return [var for var in required if not os.getenv(var)]
```

### Step 4: Logging Configuration

Create `src/utils/logger.py`:

```python
"""Centralised logging configuration."""

import logging
import sys
from pathlib import Path


def setup_logging(log_level: str = "INFO") -> None:
    """Configure application-wide logging.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # Create logs directory
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_dir / "bot.log")
        ]
    )

    # Set specific log levels for noisy libraries
    logging.getLogger("daily").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get logger for module.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)
```

## Pipeline Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    Daily.co Room (WebRTC)                        │
│  Participant speaks → Audio transmitted to bot                   │
└─────────────────────────┬───────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────┐
│ Stage 1: DailyTransport + Silero VAD                             │
│  - Receives WebRTC audio                                         │
│  - VAD detects speech vs silence                                 │
│  - Emits: AudioRawFrame                                          │
│  Latency: ~75ms                                                  │
└─────────────────────────┬───────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────┐
│ Stage 2: GroqSTTService                                          │
│  - Transcribes audio with Whisper Large v3 Turbo                │
│  - Emits: TextFrame                                              │
│  Latency: 400-800ms                                              │
└─────────────────────────┬───────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────┐
│ Stage 3: SentenceAggregator                                      │
│  - Buffers partial transcripts                                   │
│  - Detects sentence boundaries                                   │
│  - Emits: LLMMessagesFrame (on sentence complete)                │
│  Latency: 50-200ms                                               │
└─────────────────────────┬───────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────┐
│ Stage 4: ClaimExtractor                                          │
│  - Extracts factual claims with Groq LLM (JSON mode)            │
│  - Emits: ClaimFrame (one per claim)                             │
│  Latency: 50-150ms per sentence                                  │
└─────────────────────────┬───────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────┐
│ Stage 5: WebFactChecker                                          │
│  - Searches web with Exa (300-600ms)                            │
│  - Verifies with Groq LLM (50-150ms)                            │
│  - Emits: VerdictFrame                                           │
│  Latency: 400-750ms per claim                                    │
└─────────────────────────┬───────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────┐
│ Stage 6: FactCheckMessenger (CallClient)                         │
│  - Formats verdict message                                       │
│  - Sends to Daily Prebuilt chat                                  │
│  Latency: 50-100ms                                               │
└─────────────────────────┬───────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────┐
│              Daily Prebuilt Chat UI                              │
│  User sees verdict in chat panel                                 │
└─────────────────────────────────────────────────────────────────┘

Total latency: 1.2-2.25s (speech end → chat message)
```

## Integration Testing

Create `tests/test_pipeline_integration.py`:

```python
"""Integration tests for complete pipeline."""

import pytest
import asyncio
import os
from dotenv import load_dotenv
from pipecat.frames import TextFrame, LLMMessagesFrame
from src.processors.sentence_aggregator import SentenceAggregator
from src.processors.claim_extractor import ClaimExtractor
from src.processors.web_fact_checker import WebFactChecker
from src.frames.custom_frames import ClaimFrame, VerdictFrame

load_dotenv()


@pytest.mark.asyncio
async def test_stage_3_to_4_integration():
    """Test SentenceAggregator → ClaimExtractor integration."""
    aggregator = SentenceAggregator()
    extractor = ClaimExtractor()

    # Create sentence frame
    sentence_frame = LLMMessagesFrame([{
        "role": "user",
        "content": "Python 3.12 removed distutils."
    }])

    # Process through extractor
    claims = []
    async for frame in extractor.process_frame(sentence_frame):
        if isinstance(frame, ClaimFrame):
            claims.append(frame)

    assert len(claims) > 0
    assert "distutils" in claims[0].text.lower()


@pytest.mark.asyncio
async def test_stage_4_to_5_integration():
    """Test ClaimExtractor → WebFactChecker integration."""
    checker = WebFactChecker()

    # Create claim frame
    claim_frame = ClaimFrame(
        text="Python 3.12 removed distutils",
        claim_type="version"
    )

    # Process through fact checker
    verdicts = []
    async for frame in checker.process_frame(claim_frame):
        if isinstance(frame, VerdictFrame):
            verdicts.append(frame)

    assert len(verdicts) == 1
    verdict = verdicts[0]

    assert verdict.status in ["supported", "contradicted", "unclear", "not_found"]
    assert 0.0 <= verdict.confidence <= 1.0
    assert len(verdict.rationale) > 0


@pytest.mark.asyncio
async def test_full_pipeline_flow():
    """Test complete pipeline flow (Stages 3-5)."""
    aggregator = SentenceAggregator()
    extractor = ClaimExtractor()
    checker = WebFactChecker()

    # Input: Sentence
    sentence = "GDPR requires breach notification within 72 hours."
    sentence_frame = LLMMessagesFrame([{"role": "user", "content": sentence}])

    # Stage 4: Extract claims
    claims = []
    async for frame in extractor.process_frame(sentence_frame):
        if isinstance(frame, ClaimFrame):
            claims.append(frame)

    assert len(claims) > 0, "No claims extracted"

    # Stage 5: Verify each claim
    verdicts = []
    for claim in claims:
        async for frame in checker.process_frame(claim):
            if isinstance(frame, VerdictFrame):
                verdicts.append(frame)

    assert len(verdicts) > 0, "No verdicts generated"

    # Verify verdict structure
    for verdict in verdicts:
        assert verdict.claim == claims[0].text
        assert verdict.status in ["supported", "contradicted", "unclear", "not_found"]
        assert verdict.rationale is not None
```

Run tests:
```bash
uv run pytest tests/test_pipeline_integration.py -v
```

## Performance Monitoring

Create `src/utils/metrics.py`:

```python
"""Performance metrics tracking."""

import time
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class StageMetrics:
    """Metrics for a single pipeline stage."""
    stage_name: str
    latencies_ms: List[int] = field(default_factory=list)

    def record(self, latency_ms: int):
        """Record a latency measurement."""
        self.latencies_ms.append(latency_ms)

    @property
    def avg_latency_ms(self) -> float:
        """Average latency in milliseconds."""
        if not self.latencies_ms:
            return 0.0
        return sum(self.latencies_ms) / len(self.latencies_ms)

    @property
    def min_latency_ms(self) -> int:
        """Minimum latency in milliseconds."""
        return min(self.latencies_ms) if self.latencies_ms else 0

    @property
    def max_latency_ms(self) -> int:
        """Maximum latency in milliseconds."""
        return max(self.latencies_ms) if self.latencies_ms else 0


class PipelineMetrics:
    """Track metrics for entire pipeline."""

    def __init__(self):
        self.stages: Dict[str, StageMetrics] = {
            "stt": StageMetrics("GroqSTTService"),
            "aggregator": StageMetrics("SentenceAggregator"),
            "extractor": StageMetrics("ClaimExtractor"),
            "checker": StageMetrics("WebFactChecker"),
            "messenger": StageMetrics("FactCheckMessenger")
        }

    def record(self, stage: str, latency_ms: int):
        """Record latency for a stage."""
        if stage in self.stages:
            self.stages[stage].record(latency_ms)

    def summary(self) -> Dict:
        """Get metrics summary."""
        return {
            stage_name: {
                "avg_ms": metrics.avg_latency_ms,
                "min_ms": metrics.min_latency_ms,
                "max_ms": metrics.max_latency_ms,
                "count": len(metrics.latencies_ms)
            }
            for stage_name, metrics in self.stages.items()
        }


# Global metrics instance
_metrics = PipelineMetrics()


def get_metrics() -> PipelineMetrics:
    """Get global metrics instance."""
    return _metrics
```

## Common Integration Issues

### Issue 1: Frame Type Mismatches
```python
# Problem: Stage expects different frame type

# Solution: Add frame type checking
async def process_frame(self, frame: Frame):
    if not isinstance(frame, ExpectedFrameType):
        yield frame  # Pass through
        return

    # Process expected frame type
    ...
```

### Issue 2: Async Coordination
```python
# Problem: Blocking calls in async context

# Solution: Use AsyncGroq client
from groq import AsyncGroq

client = AsyncGroq(api_key=api_key)
response = await client.chat.completions.create(...)
```

### Issue 3: CallClient Join Timing
```python
# Problem: CallClient must join before pipeline runs

# Solution: Await join before pipeline.run()
chat_client = CallClient()
await chat_client.join(room_url, token)  # Wait for join

pipeline = Pipeline([...])
await pipeline.run()  # Now start pipeline
```

### Issue 4: Import Errors
```python
# Problem: Custom frames not found

# Solution: Ensure __init__.py exists
# src/frames/__init__.py
from .custom_frames import ClaimFrame, VerdictFrame

__all__ = ["ClaimFrame", "VerdictFrame"]
```

## Performance Targets (Phase 1 MVP)

### Latency Targets
| Stage | Target | Typical | Acceptable |
|-------|--------|---------|-----------|
| Stage 1 (DailyTransport) | <150ms | ~75ms | <200ms |
| Stage 2 (GroqSTTService) | <800ms | ~600ms | <1000ms |
| Stage 3 (SentenceAggregator) | <200ms | ~100ms | <300ms |
| Stage 4 (ClaimExtractor) | <150ms | ~100ms | <200ms |
| Stage 5 (WebFactChecker) | <750ms | ~500ms | <1000ms |
| Stage 6 (FactCheckMessenger) | <100ms | ~50ms | <150ms |
| **Total (speech → chat)** | **<2.25s** | **~1.5s** | **<3.0s** |

### Resource Targets
- **Memory:** <500MB
- **CPU:** <60% (single core)
- **Network:** <100KB/s sustained
- **Groq API calls:** <10/min during active conversation

## Deliverables Checklist

- [ ] `bot.py` - Main bot entry point with all 6 stages
- [ ] `src/frames/custom_frames.py` - ClaimFrame, VerdictFrame
- [ ] `src/utils/config.py` - Pydantic settings
- [ ] `src/utils/logger.py` - Logging configuration
- [ ] `src/utils/metrics.py` - Performance tracking
- [ ] `tests/test_pipeline_integration.py` - Integration tests
- [ ] All environment variables configured
- [ ] Bot successfully joins Daily room
- [ ] All 6 stages working end-to-end
- [ ] Verdicts appearing in Daily chat
- [ ] Latency within targets (<2.25s)

## Next Steps After Integration

1. **End-to-End Testing:**
   - Run bot with Daily Prebuilt UI
   - Speak test claims from demo script
   - Verify verdicts in chat
   - Measure actual latencies

2. **Performance Optimisation:**
   - Review metrics for bottlenecks
   - Tune VAD sensitivity
   - Adjust Exa search parameters
   - Optimise LLM prompts

3. **Error Handling:**
   - Test with no search results
   - Test with malformed speech
   - Test with API failures
   - Verify graceful degradation

4. **Demo Preparation:**
   - Prepare 5 test claims
   - Record demo video
   - Create presentation slides
   - Document known limitations

## Resources

**Pipecat Documentation:**
- Pipeline API: https://docs.pipecat.ai/api-reference/pipeline
- Processors: https://docs.pipecat.ai/api-reference/processors
- Frames: https://docs.pipecat.ai/api-reference/frames

**Daily.co Documentation:**
- CallClient: https://docs.daily.co/reference/daily-python
- Dual-client pattern: https://docs.daily.co/guides/products/ai-toolkit

**Project Documentation:**
- Architecture: ../architecture_design.md
- Workload: ./00_WORKLOAD_DISTRIBUTION.md

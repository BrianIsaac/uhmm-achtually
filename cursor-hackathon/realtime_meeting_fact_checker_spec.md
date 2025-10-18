# Realtime Meeting Fact-Checker — Implementation Spec (Phase 1: Web Search Only)

**Status:** Phase 1 MVP (Pipecat + Daily.co hybrid architecture)
**Deployment:** Daily.co WebRTC rooms (cloud-hosted bot)
**Timebox:** 24 hours (3-person team)
**Language:** Python 3.12
**Package Manager:** uv (fast, reliable Python package installer)

**Stack (Pipecat + Daily.co + Vue.js Hybrid):**
- **Backend Pipeline:** Pipecat framework with DailyTransport (Stages 1-5)
- **Backend Messaging:** Daily Python SDK CallClient (Stage 6 - app messages)
- **Frontend:** Vue.js 3 + Vite + @daily-co/daily-js (custom branded UI)
- **STT:** Pipecat GroqSTTService with Silero VAD (400-800ms latency)
- **LLM:** Groq llama3.1-8b-instant (50-150ms inference, JSON mode)
- **Search:** Exa Neural Search API (Phase 1 only, web retrieval)
- **Database:** None (Phase 1 - in-memory operation only)
- **RAG:** None (Phase 1 - deferred to Phase 2 with BM25 + Supabase)

**Architecture:** Hybrid triple-client pattern with three Daily connections:
1. Vue.js CallObject (frontend): Audio/video + app message listener
2. Pipecat DailyTransport (backend): Audio-only pipeline (receive speech, process claims)
3. Daily CallClient (backend): Messaging-only (broadcast verdicts via app messages)

**Phase 1 vs Phase 2:**
- **Phase 1 (24h MVP):** Web search only (Groq + Exa), no database, no RAG
- **Phase 2 (Future):** Add BM25 local search + Supabase for internal KB

---

## 1) Problem & Goals

### Problem
Companies lack **real-time fact-checking** during meetings for both **internal project knowledge** and **domain knowledge**, causing scope drift and incorrect decisions.

### Goals (Phase 1 MVP)
- In-meeting agent that:
  - **Listens via Pipecat GroqSTTService** with VAD for real-time speech detection
  - Extracts **claims** using Groq LLM and verifies them with **web search only** (Exa)
  - Returns a **verdict** (Supported / Contradicted / Unclear / Not found) with rationale
  - Surfaces feedback via **custom Vue.js UI** using `CallClient.sendAppMessage()`
  - Provides **fully custom, branded interface** with verdict cards and participant video

### Out of scope for Phase 1 MVP
- **Internal RAG/BM25** (Phase 2)
- **Database persistence** (Phase 2 with Supabase)
- **TTS nudging** (may be added post-MVP)
- **Drift detection** (Phase 2)
- Full diarisation, multilingual captions
- SSO/enterprise authentication
- Multi-user support with authentication

### Deferred to Phase 2
- **BM25 internal KB search** (add `bm25s` + Supabase storage)
- **Database persistence** (Supabase tables for meetings, claims, verdicts)
- **Drift detection** (compare utterances to meeting objective)
- **Local Vosk STT** - Threading conflicts with Pipecat architecture documented

---

## 2) Users & Use Cases

- **Facilitator / PM:** keep discussion on objective; correct misinformation quickly
- **Engineer / Analyst:** verify API/config/policy facts with source links
- **Students:** check definitions with citations

**Phase 1 Demo use cases (web search only)**
1) Domain claim: "K8s uses iptables by default in v1.29" → **Supported/Unclear** via Exa docs
2) Tech claim: "Python 3.12 removed distutils" → **Supported** (PEP 632)
3) Regulatory claim: "GDPR requires 72-hour breach notification" → **Supported** (Article 33)

---

## 3) System Overview

```
User speaks in Vue.js Frontend
    ↓
Frontend Daily CallObject sends audio via WebRTC
    ↓
Daily.co broadcasts to all participants
    ↓
Backend receives via Stage 1: DailyTransport
    ↓
Stage 2: GroqSTTService (Whisper Large v3 Turbo, 400-800ms)
    ↓
Stage 3: SentenceAggregator (gate on sentence boundaries)
    ↓
Stage 4: ClaimExtractor (Groq Llama 3.1, 50-150ms JSON mode)
    ↓
Stage 5: WebFactChecker (Exa search 300-600ms + Groq verify 50-150ms)
    ↓
Stage 6: FactCheckMessenger (CallClient.sendAppMessage())
    ↓
Daily.co broadcasts app message
    ↓
Vue.js Frontend receives 'app-message' event
    ↓
Verdict cards rendered in custom UI
```

**Phase 1 MVP Latency (Pipecat + Exa):**
- **Total:** 1.2-2.25s from speech to chat message
  - STT (Stage 2): 400-800ms (Groq Whisper with VAD)
  - Sentence aggregation (Stage 3): 50-200ms
  - Claim extraction (Stage 4): 50-150ms
  - Web search (Stage 5): 300-600ms (Exa) + 50-150ms (Groq verify)
  - Chat delivery (Stage 6): 50-100ms

**Triple-Client Architecture:**
- **Vue.js CallObject (Frontend):** Audio/video + app message listener
- **Pipecat DailyTransport (Backend):** Audio-only connection (Stages 1-5 processing)
- **Daily CallClient (Backend):** Messaging-only connection (Stage 6 app messages)
- System creates THREE concurrent connections to the same Daily room

---

## 4) Data (Phase 1: No Database)

### Phase 1: In-Memory Only
- **No persistence** in Phase 1 MVP
- Claims and verdicts exist only during bot session
- Web search results cached in memory (session-scoped dict)

### Phase 2: Database (Future)
- Add Supabase tables: `meetings`, `utterances`, `claims`, `verdicts`, `kb_docs`, `kb_chunks`, `web_cache`
- Implement RLS policies for multi-tenant access
- Enable meeting export (CSV/Markdown)

### Domain Knowledge (Web)
- **No preload**. Use Exa live retrieval with an **allow-list** (e.g., docs.python.org, kubernetes.io, owasp.org, nist.gov)
- **Cache:** In-memory session cache for `/search` + `/contents` (Phase 1)

---

## 5) Pipeline Stages (Pipecat Architecture)

### Stage 1: DailyTransport
**Component:** Pipecat's built-in Daily.co WebRTC transport
**Purpose:** Receive audio from Daily room participants

```python
from pipecat.transports.daily_transport import DailyTransport
from pipecat.vad.silero import SileroVADAnalyzer

transport = DailyTransport(
    room_url=daily_room_url,
    token=daily_token,
    bot_name="Fact Checker",
    vad_enabled=True,
    vad_analyzer=SileroVADAnalyzer(),
    vad_audio_passthrough=True
)
```

**Why DailyTransport:**
- Production-ready WebRTC integration
- Built-in VAD support (Silero)
- Handles audio format conversion
- Auto-reconnection and error handling

---

### Stage 2: GroqSTTService
**Component:** Pipecat's built-in Groq Whisper integration
**Latency:** 400-800ms per utterance
**Model:** whisper-large-v3-turbo (216x real-time speed)

```python
from pipecat.services.groq_stt import GroqSTTService

stt = GroqSTTService(
    api_key=os.getenv("GROQ_API_KEY"),
    model="whisper-large-v3-turbo",
    language="en"
)
```

**Why Groq Whisper:**
- 216x real-time speed (1 hour audio → 17 seconds)
- 400-800ms latency (vs 2-3s for file-based APIs)
- Built-in VAD integration via Pipecat
- No threading conflicts (unlike Vosk)

**Vosk Not Pursued:**
- Threading conflicts with Pipecat's async architecture
- Requires complex queue-based workarounds
- VAD integration more difficult
- Groq Whisper provides sufficient speed for MVP

---

### Stage 3: SentenceAggregator
**Component:** Custom Pipecat FrameProcessor with gate logic
**Latency:** 50-200ms (sentence boundary detection)
**Purpose:** Buffer partial transcripts until sentence completion

```python
from pipecat.frames import LLMMessagesFrame, TextFrame
from pipecat.processors import FrameProcessor

class SentenceAggregator(FrameProcessor):
    """Aggregate partial transcripts into complete sentences.

    Uses sentence boundary detection to gate downstream processing.
    Only emits LLMMessagesFrame when sentence completes.
    """

    async def process_frame(self, frame: Frame):
        if isinstance(frame, TextFrame):
            self._buffer += frame.text

            if self._is_sentence_complete(self._buffer):
                yield LLMMessagesFrame([{
                    "role": "user",
                    "content": self._buffer
                }])
                self._buffer = ""
        else:
            yield frame

    def _is_sentence_complete(self, text: str) -> bool:
        """Check for sentence-ending punctuation."""
        return bool(re.search(r'[.!?]\s*$', text.strip()))
```

**Why Custom Aggregator:**
- Prevents partial-sentence claim extraction
- Reduces unnecessary LLM calls
- Improves claim quality (complete context)

---

### Stage 4: ClaimExtractor
**Component:** Custom Pipecat LLMProcessor using Groq
**Latency:** 50-150ms per sentence
**Purpose:** Extract factual claims from sentences using JSON mode

```python
from pipecat.processors import LLMProcessor
from pipecat.services.groq_llm import GroqLLMService

class ClaimExtractor(LLMProcessor):
    """Extract factual claims from sentences using Groq JSON mode."""

    SYSTEM_PROMPT = """Extract factual claims from the sentence.
    Return JSON array of claims with 'text' and 'type' fields.
    Types: version, api, regulatory, definition, number, decision.
    Only extract verifiable factual statements."""

    async def process_frame(self, frame: LLMMessagesFrame):
        llm_service = GroqLLMService(
            api_key=os.getenv("GROQ_API_KEY"),
            model="llama3.1-8b-instant"
        )

        response = await llm_service.process_frame(
            LLMMessagesFrame([
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": frame.messages[0]["content"]}
            ])
        )

        claims = json.loads(response.text)
        for claim in claims:
            yield ClaimFrame(
                text=claim["text"],
                claim_type=claim["type"]
            )
```

**Why Groq JSON Mode:**
- 50-150ms inference (50x faster than standard LLMs)
- `response_format={"type": "json_object"}` ensures valid JSON
- No parsing errors from structured output

---

### Stage 5: WebFactChecker
**Component:** Custom Pipecat FrameProcessor using Exa + Groq
**Latency:** 400-750ms total (Exa 300-600ms + Groq 50-150ms)
**Purpose:** Search web and verify claims

```python
from exa_py import Exa
from pipecat.processors import FrameProcessor

class WebFactChecker(FrameProcessor):
    """Verify claims using Exa web search and Groq verification.

    Phase 1: Web search only (no internal RAG).
    Phase 2: Add BM25 routing for internal KB.
    """

    def __init__(self, exa_api_key: str, groq_api_key: str, allowed_domains: list[str]):
        self.exa = Exa(api_key=exa_api_key)
        self.groq_client = Groq(api_key=groq_api_key)
        self.allowed_domains = allowed_domains
        self._cache = {}  # In-memory session cache

    async def process_frame(self, frame: ClaimFrame):
        # Check cache
        cache_key = f"claim:{frame.text}"
        if cache_key in self._cache:
            yield self._cache[cache_key]
            return

        # Exa search (300-600ms)
        search_response = self.exa.search_and_contents(
            frame.text,
            use_autoprompt=True,
            num_results=2,
            include_domains=self.allowed_domains,
            text={"max_characters": 2000}
        )

        # Groq verification (50-150ms)
        verdict = await self._verify_with_groq(
            claim=frame.text,
            passages=search_response.results
        )

        verdict_frame = VerdictFrame(
            claim=frame.text,
            status=verdict["status"],
            confidence=verdict["confidence"],
            rationale=verdict["rationale"],
            evidence_url=verdict["evidence_url"]
        )

        self._cache[cache_key] = verdict_frame
        yield verdict_frame

    async def _verify_with_groq(self, claim: str, passages: list) -> dict:
        """Call Groq with JSON mode for structured verdict."""
        prompt = f"""Verify this claim using the provided passages.

Claim: {claim}

Passages:
{json.dumps([{"title": p.title, "url": p.url, "text": p.text} for p in passages], indent=2)}

Return JSON with: status (supported|contradicted|unclear|not_found), confidence (0-1), rationale (1 sentence), evidence_url."""

        response = self.groq_client.chat.completions.create(
            model="llama3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.1
        )

        return json.loads(response.choices[0].message.content)
```

**Why Exa for Phase 1:**
- Neural search optimised for AI queries
- Auto-prompt enhancement improves results
- Domain filtering prevents junk sources
- 300-600ms typical latency (acceptable for web path)

**Phase 2 Enhancement:**
- Add BM25 internal search with Supabase KB
- Route claims to internal vs web based on keywords
- Use Exa only for freshness-sensitive or external claims

---

### Stage 6: FactCheckMessenger
**Component:** Custom messenger using Daily Python SDK CallClient
**Latency:** 50-100ms
**Purpose:** Broadcast verdicts to all participants via app messages

```python
from daily import CallClient, Daily
from pipecat.processors import FrameProcessor

class FactCheckMessenger(FrameProcessor):
    """Broadcast verdicts via app messages to custom Vue.js frontend.

    Uses CallClient.sendAppMessage() to send structured JSON.
    Frontend receives via 'app-message' event listener.
    """

    def __init__(self, call_client: CallClient, bot_name: str = "Fact Checker Bot"):
        self.call_client = call_client
        self.bot_name = bot_name

    async def process_frame(self, frame: VerdictFrame):
        # Format as JSON for frontend consumption
        message_data = {
            'type': 'fact-check-verdict',
            'claim': frame.claim,
            'status': frame.status,  # 'supported', 'contradicted', 'unclear', 'not_found'
            'confidence': frame.confidence,
            'rationale': frame.rationale,
            'evidence_url': frame.evidence_url
        }

        # Broadcast to all participants (50-100ms)
        self.call_client.sendAppMessage(
            message_data,
            '*'  # Send to all participants
        )

        yield frame  # Pass through for logging/metrics

# Usage in main bot
Daily.init()

# Create CallClient (separate from Pipecat transport)
message_client = CallClient()
await message_client.join(room_url, token)

messenger = FactCheckMessenger(
    call_client=message_client,
    bot_name="Fact Checker Bot"
)
```

**Why CallClient.sendAppMessage():**
- **Custom UI control:** Vue.js frontend receives structured JSON data
- **Full styling control:** Frontend can render verdicts however it wants
- **Flexible data:** Send complete verdict object with confidence, rationale, etc.
- **Event-driven:** Frontend 'app-message' listener gets immediate notification
- **Broadcast support:** All participants receive the same data

**Frontend Reception (Vue.js):**
```javascript
// frontend/src/composables/useFactCheck.js
callObject.on('app-message', (event) => {
  if (event.data.type === 'fact-check-verdict') {
    verdicts.value.unshift(event.data)
    // Vue reactivity automatically updates UI
  }
})
```

---

## 6) Retrieval & Verification (Phase 1: Web Only)

### Web Retrieval (Exa)
- Normalise query; check in-memory cache
- On miss: Exa `search_and_contents()` with:
  - `use_autoprompt=True` for query optimisation
  - `num_results: 2-3`
  - `include_domains` (allow-list)
  - `text={"max_characters": 2000}` for passage extraction
- Return 1-2 passages; cache result in session dict

**Allow-list (Phase 1 demo):**
`docs.python.org`, `kubernetes.io`, `owasp.org`, `www.nist.gov`, `postgresql.org`, `docs.djangoproject.com`, `reactjs.org`, `golang.org`

### Groq Verification
- Input: claim + passages (max 2 passages to reduce latency)
- Output (JSON mode):
```json
{
  "status": "supported|contradicted|unclear|not_found",
  "confidence": 0.85,
  "rationale": "Article 33 GDPR requires notification within 72 hours.",
  "evidence_url": "https://gdpr-info.eu/art-33-gdpr/"
}
```

**No evidence policy:** Return `unclear` or `not_found` when insufficient evidence (never fabricate)

---

## 7) Configuration & Setup

### Environment Variables (.env)
```bash
# Daily.co
DAILY_API_KEY=<daily-api-key>
DAILY_ROOM_URL=https://<domain>.daily.co/<room-name>
DAILY_BOT_TOKEN=<meeting-token-with-bot-permissions>

# LLM & Search APIs
GROQ_API_KEY=<groq-api-key>  # For Whisper STT + Llama inference
EXA_API_KEY=<exa-api-key>

# Configuration
ALLOWED_DOMAINS=docs.python.org,kubernetes.io,owasp.org,nist.gov,postgresql.org
PYTHON_ENV=development
LOG_LEVEL=INFO

# Phase 2 (Future)
# SUPABASE_URL=https://<project>.supabase.co
# SUPABASE_ANON_KEY=<anon-key>
# SUPABASE_SERVICE_ROLE=<service-role-key>
```

### Project Structure
```
uhmm-achtually/
├── backend/                         # Python bot
│   ├── .env                         # Backend environment variables (gitignored)
│   ├── .python-version              # Python version (3.12)
│   ├── pyproject.toml               # uv project configuration
│   ├── uv.lock                      # Locked dependencies
│   ├── bot.py                       # Main Pipecat bot entry point
│   ├── src/
│   │   ├── __init__.py
│   │   ├── processors/
│   │   │   ├── __init__.py
│   │   │   ├── sentence_aggregator.py   # Stage 3
│   │   │   ├── claim_extractor.py       # Stage 4
│   │   │   ├── web_fact_checker.py      # Stage 5
│   │   │   └── fact_check_messenger.py  # Stage 6 (sendAppMessage)
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── daily_manager.py         # Room creation/management
│   │   │   └── exa_client.py            # Exa API wrapper
│   │   ├── frames/
│   │   │   ├── __init__.py
│   │   │   └── custom_frames.py         # ClaimFrame, VerdictFrame
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── config.py                # Settings management
│   │       └── logger.py                # Logging setup
│   └── scripts/
│       └── demo_script.txt              # Demo script for testing claims
├── frontend/                        # Vue.js app
│   ├── .env.local                   # Frontend environment variables (gitignored)
│   ├── package.json                 # npm dependencies
│   ├── vite.config.js               # Vite configuration
│   ├── index.html
│   ├── src/
│   │   ├── main.js                  # Entry point
│   │   ├── App.vue                  # Main component
│   │   ├── components/
│   │   │   ├── CallControls.vue     # Mic/camera toggles
│   │   │   ├── FactCheckDisplay.vue # Verdict cards
│   │   │   └── ParticipantTile.vue  # Video tiles
│   │   └── composables/
│   │       ├── useDaily.js          # CallObject wrapper
│   │       └── useFactCheck.js      # App message handler
│   └── public/
└── README.md                        # Setup instructions
```

### Setup with uv

**Installation:**
```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone repository
git clone <repo-url>
cd realtime-fact-checker

# Create virtual environment and install dependencies
uv sync

# Activate environment
source .venv/bin/activate  # Linux/macOS
# or
.venv\Scripts\activate     # Windows
```

**pyproject.toml Configuration:**
```toml
[project]
name = "realtime-fact-checker"
version = "0.1.0"
description = "Real-time meeting fact-checker with Pipecat and Daily.co"
requires-python = ">=3.12"
dependencies = []

[dependency-groups]
pipecat = [
    "pipecat-ai>=0.0.39",
    "pipecat-ai[daily]>=0.0.39",
    "pipecat-ai[silero]>=0.0.39",
]

daily = [
    "daily-python>=0.10.1",
]

llm = [
    "groq>=0.8.0",
]

search = [
    "exa-py>=1.0.0",
]

config = [
    "pydantic>=2.6.0",
    "pydantic-settings>=2.2.0",
    "python-dotenv>=1.0.0",
]

utils = [
    "httpx>=0.27.0",
]

dev = [
    "ipython>=8.22.0",
]
```

**Development Commands:**
```bash
# Install all dependency groups
uv sync

# Install specific dependency groups
uv sync --group pipecat --group daily --group llm --group search --group config --group utils

# Add new dependency to a group
uv add --group <group-name> <package-name>

# Run bot
uv run python bot.py

# Run interactive Python shell
uv run ipython
```

---

## 8) Development Best Practices

### Code Style & Standards
- **Type hints:** All functions should include Google-style docstrings and type hints
- **Naming conventions:**
  - snake_case for functions and variables
  - PascalCase for classes
  - UPPER_CASE for constants
  - Prefix private methods with `_`

### Async Patterns (Pipecat)
```python
from pipecat.pipeline import Pipeline
from pipecat.processors import FrameProcessor

async def run_fact_checker_bot():
    """Main bot entry point with async pipeline execution.

    Builds Pipecat pipeline with all 6 stages and runs until completion.
    Handles graceful shutdown and cleanup.
    """
    # Stage 1: Transport
    transport = DailyTransport(...)

    # Stage 2: STT
    stt = GroqSTTService(...)

    # Stage 3: Aggregator
    aggregator = SentenceAggregator()

    # Stage 4: Claim Extractor
    extractor = ClaimExtractor()

    # Stage 5: Fact Checker
    checker = WebFactChecker(...)

    # Stage 6: Messenger (separate CallClient)
    chat_client = CallClient()
    await chat_client.join(room_url, token)
    messenger = FactCheckMessenger(chat_client)

    # Build pipeline
    pipeline = Pipeline([
        transport.input_processor(),
        stt,
        aggregator,
        extractor,
        checker,
        messenger,
        transport.output_processor()
    ])

    # Run until cancelled
    await pipeline.run()
```

### Error Handling
```python
import logging

logger = logging.getLogger(__name__)

async def call_groq_api(prompt: str) -> dict:
    """Call Groq API with basic error handling.

    Args:
        prompt: The prompt text to send to Groq

    Returns:
        Parsed JSON response

    Raises:
        Exception: If API call fails
    """
    try:
        response = await client.chat.completions.create(
            model="llama3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        logger.error(f"Groq API call failed: {e}")
        raise
```

### Configuration Management
```python
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )

    # Daily.co
    daily_api_key: str
    daily_room_url: str
    daily_bot_token: str

    # APIs
    groq_api_key: str
    exa_api_key: str

    # Config
    allowed_domains: list[str] = [
        "docs.python.org",
        "kubernetes.io",
        "owasp.org"
    ]
    python_env: str = "development"
    log_level: str = "INFO"

@lru_cache
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()
```

---

## 9) Security & Privacy

- **Audio handling:** Streams through Groq Whisper, does **not** persist raw audio; only transcript text
- **Allow-list domains:** Only retrieve from trusted documentation sites
- **Text sanitisation:** Strip scripts and dangerous HTML from web content
- **API keys:** Never commit `.env` to version control; use environment variables
- **Rate limiting:** Monitor Groq and Exa API quotas
- **No evidence policy:** Verifier returns `unclear/not_found` when insufficient evidence (never fabricate)

**Phase 2 Security (Future):**
- RLS on all Supabase tables
- Private Storage with signed URLs
- Per-user API rate limiting
- Automatic data retention cleanup

---

## 10) Testing & Demo Script

**Scripted spoken lines (read aloud in Daily room):**
1) "Python 3.12 removed the distutils package." → **Supported** (PEP 632)
2) "Kubernetes uses iptables by default in v1.29." → **Supported/Unclear** (web)
3) "GDPR requires breach notification within 72 hours." → **Supported** (Article 33)
4) "React 18 introduced automatic batching for state updates." → **Supported** (React docs)
5) "PostgreSQL 15 uses LLVM JIT compilation by default." → **Contradicted** (disabled by default)

**Acceptance Criteria:**
- Transcripts appear in logs with <2s latency
- Verdicts delivered to Vue.js frontend within 2.25s of speech completion
- Verdict cards render with correct status colours (green/red/yellow/grey)
- Evidence links open authoritative documentation
- Custom Vue.js UI displays participant video and verdict history
- Bot handles concurrent speakers without crashing

---

## 11) Build Plan (24h, 3-Person Team)

### Developer A: Pipecat Pipeline Foundation (8 hours)

**H 0-2:** Project setup and Stage 1-2
- Create project structure with uv
- Configure `pyproject.toml` with Pipecat dependencies
- Set up `.env` and configuration management
- Implement DailyTransport with Silero VAD (Stage 1)
- Integrate GroqSTTService (Stage 2)
- Test audio reception and transcription

**H 2-4:** Stage 3 (SentenceAggregator)
- Implement custom FrameProcessor for sentence boundary detection
- Add buffer management logic
- Test sentence completion detection
- Integration test with Stages 1-2

**H 4-6:** Pipeline assembly
- Create main bot.py entry point
- Build Pipeline with Stages 1-3
- Test end-to-end audio → sentence flow
- Logging and monitoring setup

**H 6-8:** Integration support
- Help integrate Stages 4-6 into pipeline
- Debug frame flow issues
- Performance profiling
- Documentation

---

### Developer B: Claim Processing (Stages 4-5) (8 hours)

**H 0-2:** Stage 4 (ClaimExtractor)
- Implement ClaimExtractor FrameProcessor
- Configure Groq LLM with JSON mode
- Design claim extraction prompt
- Define ClaimFrame data structure
- Manual testing with sample sentences

**H 2-5:** Stage 5 (WebFactChecker)
- Implement Exa API client wrapper
- Create WebFactChecker FrameProcessor
- Add in-memory caching logic
- Implement Groq verification with JSON mode
- Define VerdictFrame data structure
- Manual testing with sample claims

**H 5-7:** Optimisation and caching
- Tune Exa search parameters (autoprompt, domain filtering)
- Optimise prompt for Groq verification
- Add latency logging for each component
- Cache hit/miss tracking

**H 7-8:** Integration and manual testing
- Integrate with Developer A's pipeline
- Test end-to-end claim extraction → verification flow
- Debug edge cases (no results, malformed JSON)
- Documentation

---

### Developer C: Vue.js Frontend (8 hours)

**H 0-1:** Project setup and Daily.co infrastructure
- Set up Daily.co account and obtain API key
- Create test room via Daily API
- Initialise Vue.js 3 project with Vite
- Install dependencies (@daily-co/daily-js, vue)
- Configure .env.local with Daily room URL

**H 1-3:** Daily CallObject integration
- Implement useDaily.js composable with CallObject wrapper
- Add join/leave call functionality
- Create event handlers (joined-meeting, participant-joined, app-message)
- Implement CallControls.vue component (mic/camera toggles)
- Test audio/video streaming with Daily room

**H 3-5:** Fact-check display and app message handling
- Implement useFactCheck.js composable for app message handling
- Create FactCheckDisplay.vue component for verdict cards
- Add reactive verdicts array with Vue reactivity
- Style verdict cards with status-specific colours (green/red/yellow/grey)
- Test app message reception from backend

**H 5-6:** Participant display and UI polish
- Create ParticipantTile.vue component with video rendering
- Implement participant grid layout
- Apply dark theme styling and responsive design
- Add loading states and error handling
- Polish overall UI aesthetics

**H 6-8:** Integration testing and demo preparation
- Test end-to-end flow with backend (speak → receive verdict)
- Verify all test claims display correctly in UI
- Test concurrent speakers and multiple verdicts
- Create demo script with test claims
- Performance monitoring (latency tracking from app-message to render)
- Record demo video (backup)

---

### Parallel Integration (H 8-12, All Developers)

**H 8-10:** Full system integration
- Assemble all 6 backend stages into complete pipeline
- Connect Vue.js frontend to Daily room
- Test app message flow from backend to frontend
- Debug frame flow issues in backend
- Fix race conditions or async bugs

**H 10-12:** End-to-end testing and refinement
- Test with demo script (5 test claims)
- Verify latency targets (≤2.25s backend + <100ms frontend render)
- Test verdict card rendering with all status types
- Fix critical bugs in backend and frontend
- Improve error handling across both systems
- Add logging for debugging (backend) and console logging (frontend)

---

### Final Polish (H 12-16, All Developers)

**H 12-14:** Edge case handling
- Test with no search results (backend returns `not_found`, frontend displays grey card)
- Test with ambiguous claims (backend returns `unclear`, frontend displays yellow card)
- Test with malformed speech (backend handles gracefully, no frontend errors)
- Test concurrent speakers (frontend displays multiple verdict cards)
- Test app message delivery failures (frontend shows connection errors)

**H 14-16:** Documentation and demo preparation
- Complete README with setup instructions (backend + frontend)
- Document known limitations
- Practice demo presentation (show both backend logs and frontend UI)
- Prepare talking points highlighting custom UI and real-time updates
- Create fallback slides showing architecture diagrams

---

## 12) Core Flow (pseudocode)

```python
# Main bot entry point
async def main():
    """Run fact-checker bot with Pipecat pipeline."""

    # Stage 1: DailyTransport
    transport = DailyTransport(
        room_url=os.getenv("DAILY_ROOM_URL"),
        token=os.getenv("DAILY_BOT_TOKEN"),
        bot_name="Fact Checker",
        vad_enabled=True,
        vad_analyzer=SileroVADAnalyzer()
    )

    # Stage 2: GroqSTTService
    stt = GroqSTTService(
        api_key=os.getenv("GROQ_API_KEY"),
        model="whisper-large-v3-turbo"
    )

    # Stage 3: SentenceAggregator
    aggregator = SentenceAggregator()

    # Stage 4: ClaimExtractor
    extractor = ClaimExtractor(
        groq_api_key=os.getenv("GROQ_API_KEY")
    )

    # Stage 5: WebFactChecker
    checker = WebFactChecker(
        exa_api_key=os.getenv("EXA_API_KEY"),
        groq_api_key=os.getenv("GROQ_API_KEY"),
        allowed_domains=["docs.python.org", "kubernetes.io", ...]
    )

    # Stage 6: FactCheckMessenger (separate CallClient)
    Daily.init()
    chat_client = CallClient()
    await chat_client.join(
        url=os.getenv("DAILY_ROOM_URL"),
        client_settings={"token": os.getenv("DAILY_BOT_TOKEN")}
    )
    messenger = FactCheckMessenger(
        call_client=chat_client,
        bot_name="Fact Checker"
    )

    # Build pipeline
    pipeline = Pipeline([
        transport.input_processor(),
        stt,
        aggregator,
        extractor,
        checker,
        messenger,
        transport.output_processor()
    ])

    # Run until cancelled
    try:
        await pipeline.run()
    finally:
        await chat_client.leave()
        Daily.deinit()


# Frame processing flow
"""
Audio from Daily room
    ↓
DailyTransport receives WebRTC audio (Stage 1)
    ↓
GroqSTTService transcribes to TextFrame (Stage 2, 400-800ms)
    ↓
SentenceAggregator buffers until sentence complete (Stage 3, 50-200ms)
    → Emits LLMMessagesFrame
    ↓
ClaimExtractor calls Groq to extract claims (Stage 4, 50-150ms)
    → Emits ClaimFrame for each claim
    ↓
WebFactChecker searches Exa and verifies with Groq (Stage 5, 400-750ms)
    → Emits VerdictFrame with status, rationale, evidence URL
    ↓
FactCheckMessenger sends verdict via app message (Stage 6, 50-100ms)
    → CallClient.sendAppMessage() → Vue.js frontend renders verdict card
"""
```

---

## 13) Latency Budget & Performance Targets

**Total Pipeline Latency:** 1.2-2.25s (speech end → chat message)

| Stage | Component | Target Latency | Notes |
|-------|-----------|----------------|-------|
| 1 | DailyTransport | 0ms | WebRTC streaming, negligible overhead |
| 2 | GroqSTTService | 400-800ms | Whisper Large v3 Turbo (216x real-time) |
| 3 | SentenceAggregator | 50-200ms | Sentence boundary detection |
| 4 | ClaimExtractor | 50-150ms | Groq Llama 3.1 8B JSON mode |
| 5 | WebFactChecker | 400-750ms | Exa search (300-600ms) + Groq verify (50-150ms) |
| 6 | FactCheckMessenger | 50-100ms | CallClient.sendAppMessage() + Vue.js render (<100ms) |

**Optimisations:**
- In-memory caching for repeated claims (Stage 5)
- Max 2 passages to verifier (reduce context length)
- JSON mode for all LLM calls (structured output, no parsing errors)
- VAD prevents processing silence (Stage 1)
- Sentence gating prevents partial extractions (Stage 3)

**Monitoring:**
- Log latency for each stage
- Track cache hit rates
- Monitor Groq API quota usage
- Track Exa search costs

---

## 14) Phase 2 Enhancements (Future)

When expanding beyond Phase 1 MVP:

1. **Add Internal RAG (BM25 + Supabase)**
   - Implement `kb_docs` and `kb_chunks` tables
   - Add BM25 indexing for internal documents
   - Create routing logic (internal vs web)
   - Prioritise internal KB over web for company-specific claims

2. **Database Persistence**
   - Add `meetings`, `utterances`, `claims`, `verdicts` tables
   - Implement RLS policies for multi-tenant access
   - Enable meeting export (CSV/Markdown)

3. **Drift Detection**
   - Compare utterances to meeting objective
   - Flag off-topic discussions
   - Send drift notifications to chat

4. **TTS Nudging**
   - Add Pipecat TTS output for contradicted claims
   - Gentle interruption for critical corrections
   - Configurable nudge sensitivity

5. **Enhanced UI**
   - Custom Daily dashboard with verdict history
   - Real-time transcription display
   - Speaker diarisation

---

## 15) Known Limitations (Phase 1)

- **No internal KB:** Only web search (Exa) available
- **No persistence:** Claims/verdicts lost when bot stops
- **No drift detection:** Cannot detect off-topic discussions
- **Web latency:** 300-600ms Exa search adds overhead
- **English only:** STT and LLM optimised for English
- **No speaker diarisation:** All speech attributed to room (not individual speakers)
- **Vosk not used:** Threading conflicts with Pipecat async architecture

---

## 16) Success Metrics (Phase 1 MVP)

**Functional:**
- Bot successfully joins Daily room and receives audio
- Transcription appears within 1s of speech completion
- Claims extracted from complete sentences only
- Verdicts delivered to Vue.js frontend within 2.25s total latency
- Evidence URLs link to allow-listed domains
- Vue.js frontend renders verdict cards with correct status colours

**Technical:**
- Backend: No crashes during 10-minute test session
- Backend: Graceful handling of no-results scenarios
- Backend: JSON parsing success rate >99%
- Frontend: Verdict cards render within 100ms of app message receipt
- Frontend: Responsive UI works on desktop and tablet
- Frontend: Participant video tiles display correctly

**Demo:**
- All 5 test claims verified correctly and displayed in UI
- Latency targets met for 80% of claims
- Verdict cards colour-coded and readable
- Evidence links open documentation in new tabs
- Custom branded UI demonstrates professional polish

---

## 17) Daily.co Setup Guide

**1. Create Daily.co account:**
- Sign up at https://dashboard.daily.co
- Get API key from dashboard

**2. Create room for bot and frontend:**
```bash
curl -X POST https://api.daily.co/v1/rooms \
  -H "Authorization: Bearer <DAILY_API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "fact-checker-demo",
    "privacy": "public",
    "properties": {
      "enable_chat": false,
      "enable_prejoin_ui": false
    }
  }'
```
Note: `enable_chat: false` since we're using custom Vue.js UI with app messages, not Daily Prebuilt chat.

**3. Generate bot token:**
```bash
curl -X POST https://api.daily.co/v1/meeting-tokens \
  -H "Authorization: Bearer <DAILY_API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{
    "properties": {
      "room_name": "fact-checker-demo",
      "is_owner": true
    }
  }'
```

**4. Update backend .env:**
```bash
# backend/.env
DAILY_API_KEY=<from-dashboard>
DAILY_ROOM_URL=https://<your-domain>.daily.co/fact-checker-demo
DAILY_BOT_TOKEN=<from-meeting-tokens-endpoint>
GROQ_API_KEY=<groq-api-key>
EXA_API_KEY=<exa-api-key>
```

**5. Update frontend .env.local:**
```bash
# frontend/.env.local
VITE_DAILY_ROOM_URL=https://<your-domain>.daily.co/fact-checker-demo
```

**6. Test with custom Vue.js frontend:**
```bash
# Terminal 1: Start backend bot
cd backend
uv run python bot.py

# Terminal 2: Start frontend dev server
cd frontend
npm run dev
```

- Open `http://localhost:5173` in browser (Vue.js app)
- Click "Join Call" button to join Daily room
- Speak test claims into microphone
- Verify verdict cards appear in custom UI with colour-coded status

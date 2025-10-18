# Developer A: Pipecat Pipeline Foundation (8 hours)

## Your Role
You are Developer A, responsible for building the core Pipecat pipeline foundation (Stages 1-3) for a real-time meeting fact-checker. You will set up the project infrastructure, audio reception, speech-to-text, and sentence aggregation.

**IMPORTANT**: The Python bot you build will run **on your local machine** (your laptop), NOT in Daily's cloud. Daily.co only provides the WebRTC room infrastructure. You'll run the bot with `uv run python bot.py` and keep it running during the demo.

## Project Context
Building a real-time AI fact-checker bot that joins Daily.co video meetings, listens to conversations, extracts factual claims, verifies them via web search, and displays results in a custom Vue.js frontend. This is a **24-hour hackathon** with a 3-person team.

## Architecture Overview
**Triple-Client Pattern:**
- **Vue.js CallObject (Frontend)**: Custom UI for displaying verdicts
- **Pipecat DailyTransport (Backend - YOU)**: Audio pipeline processing (Stages 1-5)
- **Daily CallClient (Backend - Developer B)**: App message broadcasting (Stage 6)

## Your Deliverables (Hours 0-8)

### H 0-2: Project Setup & Stage 1 (DailyTransport)
**Goal**: Bootstrap project and get bot joining Daily rooms with audio reception

**Tasks**:
1. **Project Initialisation**:
   ```bash
   cd /home/brian-isaac/Documents/personal/uhmm-achtually
   mkdir -p backend/src/{processors,services,frames,utils}
   cd backend
   uv init
   ```

2. **Configure pyproject.toml**:
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
   daily = ["daily-python>=0.10.1"]
   llm = ["groq>=0.8.0"]
   search = ["exa-py>=1.0.0"]
   config = [
       "pydantic>=2.6.0",
       "pydantic-settings>=2.2.0",
       "python-dotenv>=1.0.0",
   ]
   utils = ["httpx>=0.27.0"]
   dev = ["ipython>=8.22.0"]
   ```

3. **Install dependencies**:
   ```bash
   uv sync
   ```

4. **Create .env file**:
   ```bash
   # backend/.env
   DAILY_API_KEY=your_daily_api_key
   DAILY_ROOM_URL=https://your-domain.daily.co/fact-checker-demo
   DAILY_BOT_TOKEN=your_bot_token
   GROQ_API_KEY=your_groq_api_key
   EXA_API_KEY=your_exa_api_key
   ALLOWED_DOMAINS=docs.python.org,kubernetes.io,owasp.org,nist.gov,postgresql.org
   LOG_LEVEL=INFO
   ```

5. **Implement Stage 1: DailyTransport with VAD**:
   Create `backend/src/services/daily_transport_service.py`:
   ```python
   """Factory functions for DailyTransport with VAD."""

   import os
   from pipecat.transports.daily import DailyTransport, DailyParams
   from pipecat.audio.vad.silero import SileroVADAnalyzer
   from pipecat.audio.vad.vad_analyzer import VADParams

   def create_vad_analyzer() -> SileroVADAnalyzer:
       """Create Silero VAD analyzer with balanced settings."""
       return SileroVADAnalyzer(
           params=VADParams(
               start_secs=0.2,
               stop_secs=0.8,
               min_volume=0.6
           )
       )

   def create_daily_transport(
       room_url: str,
       token: str,
       bot_name: str = "Fact Checker Bot"
   ) -> DailyTransport:
       """Create DailyTransport with VAD enabled."""
       return DailyTransport(
           room_url=room_url,
           token=token,
           bot_name=bot_name,
           params=DailyParams(
               audio_in_enabled=True,
               audio_out_enabled=False,  # No TTS in Phase 1
               vad_enabled=True,
               vad_analyzer=create_vad_analyzer()
           )
       )
   ```

6. **Create configuration management**:
   Create `backend/src/utils/config.py`:
   ```python
   """Application configuration with Pydantic."""

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
           "owasp.org",
           "nist.gov",
           "postgresql.org"
       ]
       log_level: str = "INFO"

   @lru_cache
   def get_settings() -> Settings:
       """Get cached application settings."""
       return Settings()
   ```

7. **Run the bot locally**:
   ```bash
   uv run python bot.py
   ```

   **Expected output**:
   ```
   INFO: Bot joining room: https://your-domain.daily.co/fact-checker-demo
   INFO: Connected to Daily room
   INFO: Waiting for audio...
   ```

8. **Manual verification**:
   - Keep bot running in terminal
   - Open room URL in browser
   - Speak into microphone
   - Check logs for audio reception
   - Verify VAD detects speech

**Deliverable**: DailyTransport configured, bot joins room and runs on your laptop, VAD working

**KEEP THE TERMINAL OPEN** - The bot needs to keep running!

---

### H 2-4: Stage 2 (GroqSTTService)
**Goal**: Convert audio to text using Groq Whisper

**Tasks**:
1. **Implement GroqSTTService factory**:
   Create `backend/src/services/stt_service.py`:
   ```python
   """Factory functions for Groq STT service."""

   import os
   from pipecat.services.groq import GroqSTTService

   def create_groq_stt_service(
       api_key: str | None = None,
       model: str = "whisper-large-v3-turbo",
       language: str = "en"
   ) -> GroqSTTService:
       """Create Groq STT service.

       Args:
           api_key: Groq API key (defaults to env GROQ_API_KEY)
           model: Whisper model (whisper-large-v3-turbo for 216x speed)
           language: Language code (default: en)

       Returns:
           Configured GroqSTTService
       """
       return GroqSTTService(
           api_key=api_key or os.getenv("GROQ_API_KEY"),
           model=model,
           language=language
       )
   ```

2. **Test STT integration**:
   - Speak into Daily room
   - Verify transcriptions appear in logs
   - Check latency (<800ms target)

**Deliverable**: Speech-to-text working, transcriptions in logs

---

### H 4-6: Stage 3 (SentenceAggregator)
**Goal**: Buffer partial transcripts until sentence completion

**Tasks**:
1. **Define custom frames**:
   Create `backend/src/frames/custom_frames.py`:
   ```python
   """Custom frame definitions for fact-checker pipeline."""

   from dataclasses import dataclass
   from pipecat.frames.frames import Frame

   @dataclass
   class ClaimFrame(Frame):
       """Frame containing an extracted factual claim."""
       text: str
       claim_type: str  # version, api, regulatory, definition, number

   @dataclass
   class VerdictFrame(Frame):
       """Frame containing fact-check verdict."""
       claim: str
       status: str  # supported, contradicted, unclear, not_found
       confidence: float
       rationale: str
       evidence_url: str
   ```

2. **Implement SentenceAggregator**:
   Create `backend/src/processors/sentence_aggregator.py`:
   ```python
   """Aggregate partial transcripts into complete sentences."""

   import re
   from pipecat.frames.frames import Frame, TextFrame, LLMMessagesFrame
   from pipecat.processors.frame_processor import FrameProcessor

   class SentenceAggregator(FrameProcessor):
       """Aggregate partial transcripts into complete sentences.

       Uses sentence boundary detection to gate downstream processing.
       Only emits LLMMessagesFrame when sentence completes.
       """

       def __init__(self):
           super().__init__()
           self._buffer = ""

       async def process_frame(self, frame: Frame, direction):
           """Process incoming frames and aggregate sentences.

           Args:
               frame: Incoming frame (TextFrame from STT)
               direction: Frame direction in pipeline
           """
           if isinstance(frame, TextFrame):
               self._buffer += " " + frame.text
               self._buffer = self._buffer.strip()

               if self._is_sentence_complete(self._buffer):
                   # Emit complete sentence to LLM
                   yield LLMMessagesFrame([{
                       "role": "user",
                       "content": self._buffer
                   }])
                   self._buffer = ""
           else:
               # Pass through non-text frames
               yield frame

       def _is_sentence_complete(self, text: str) -> bool:
           """Check for sentence-ending punctuation.

           Args:
               text: Text to check

           Returns:
               True if sentence ends with . ! ? and has >5 words
           """
           has_ending = bool(re.search(r'[.!?]\s*$', text.strip()))
           word_count = len(text.split())
           return has_ending and word_count > 5
   ```

3. **Manual verification**:
   - Speak partial sentences
   - Verify buffering works
   - Check complete sentences trigger LLMMessagesFrame

**Deliverable**: Sentence aggregation working, gates on sentence boundaries

---

### H 6-8: Integration Support
**Goal**: Help integrate all 6 stages into complete pipeline

**Tasks**:
1. **Create main bot.py**:
   ```python
   """Main Pipecat bot entry point."""

   import asyncio
   import logging
   from pipecat.pipeline.pipeline import Pipeline
   from pipecat.pipeline.task import PipelineTask, PipelineParams
   from pipecat.pipeline.runner import PipelineRunner
   from pipecat.frames.frames import EndFrame

   from src.services.daily_transport_service import create_daily_transport
   from src.services.stt_service import create_groq_stt_service
   from src.processors.sentence_aggregator import SentenceAggregator
   from src.utils.config import get_settings

   logging.basicConfig(level=logging.INFO)
   logger = logging.getLogger(__name__)

   async def main():
       """Run fact-checker bot with Pipecat pipeline."""
       settings = get_settings()

       # Stage 1: Transport
       transport = create_daily_transport(
           room_url=settings.daily_room_url,
           token=settings.daily_bot_token
       )

       # Stage 2: STT
       stt = create_groq_stt_service(api_key=settings.groq_api_key)

       # Stage 3: Aggregator
       aggregator = SentenceAggregator()

       # TODO: Stages 4-6 will be added by Developer B

       # Build pipeline (partial for now)
       pipeline = Pipeline([
           transport.input(),
           stt,
           aggregator,
           transport.output()
       ])

       # Create task
       task = PipelineTask(
           pipeline,
           params=PipelineParams(enable_metrics=True)
       )

       # Event handlers
       @transport.event_handler("on_client_connected")
       async def on_connected(transport, client):
           logger.info(f"Client {client} connected")

       @transport.event_handler("on_client_disconnected")
       async def on_disconnected(transport, client):
           logger.info(f"Client {client} disconnected")
           await task.queue_frames([EndFrame()])

       # Run pipeline
       runner = PipelineRunner()
       await runner.run(task)

   if __name__ == "__main__":
       asyncio.run(main())
   ```

2. **Help Developer B integrate Stages 4-6**:
   - Provide frame type definitions
   - Debug pipeline flow issues
   - Fix async errors

3. **Performance profiling**:
   - Add latency logging for each stage
   - Monitor memory usage
   - Optimise buffer sizes

**Deliverable**: Complete working pipeline with all 6 stages integrated

---

## Integration with Other Developers

### You provide to Developer B:
- `src/frames/custom_frames.py` - ClaimFrame and VerdictFrame definitions
- LLMMessagesFrame format from Stage 3
- Pipeline structure for Stages 4-6 integration

### You receive from Developer B:
- `src/processors/claim_extractor.py` - Stage 4
- `src/processors/web_fact_checker.py` - Stage 5
- `src/processors/fact_check_messenger.py` - Stage 6

### You coordinate with Developer C:
- Share Daily room URL and credentials
- Provide app message format specification
- Test end-to-end flow together

---

## Success Criteria

By Hour 6, you should have:
- ✅ Project structure created with uv
- ✅ **Bot running on your laptop**: `uv run python bot.py`
- ✅ DailyTransport joining rooms with VAD
- ✅ GroqSTTService transcribing speech (<800ms latency)
- ✅ SentenceAggregator buffering and gating on sentence boundaries
- ✅ All dependencies installed and working
- ✅ Configuration management with Pydantic
- ✅ Logging set up for debugging

By Hour 8, you should have:
- ✅ **Bot running and connected** to Daily room
- ✅ Helped integrate all 6 stages into complete pipeline
- ✅ Debugged frame flow issues
- ✅ Performance profiled each stage
- ✅ **Ready for demo** - know how to restart if needed

---

## Key Commands

```bash
# Install dependencies
uv sync

# Run bot
uv run python backend/bot.py

# Interactive debugging
uv run ipython

# Check logs
tail -f backend/bot.log
```

---

## Important Notes

1. **Bot Runs Locally**: The bot runs on YOUR laptop, not in Daily's cloud
2. **Keep Terminal Open**: During demo, keep `uv run python bot.py` running
3. **Hackathon Mode**: No tests, focus on working code
4. **Manual Verification**: Test by speaking into Daily room
5. **Git Commits**: Use conventional commit style
6. **Communicate Early**: Raise blockers immediately if stuck >20 min
7. **Frame Flow**: Ensure frames flow correctly through pipeline
8. **VAD Tuning**: Adjust threshold if too sensitive/insensitive
9. **Latency**: Target <800ms for STT, <200ms for aggregation
10. **Backup Plan**: Record demo video in case bot crashes

---

## Troubleshooting

**Bot doesn't join room**:
- Check DAILY_ROOM_URL and DAILY_BOT_TOKEN in .env
- Verify token hasn't expired (regenerate if needed)

**No transcriptions**:
- Check GROQ_API_KEY is valid
- Verify VAD is detecting speech (check logs)
- Ensure microphone is working in Daily room

**Pipeline crashes**:
- Check frame type compatibility
- Verify async/await patterns
- Review error logs for stack traces

---

## Documentation References

- **Bot Deployment**: See `/cursor-hackathon/BOT_DEPLOYMENT_GUIDE.md` (WHERE THE BOT RUNS!)
- Pipecat: https://docs.pipecat.ai
- Daily.co: https://docs.daily.co
- Groq: https://console.groq.com/docs
- Architecture: See `/cursor-hackathon/architecture_design.md`
- Workload: See `/cursor-hackathon/components/00_WORKLOAD_DISTRIBUTION.md`

---

## Demo Day Reminder

**10 minutes before demo**:
1. Start bot: `cd backend && uv run python bot.py`
2. Verify: "Connected to Daily room" in logs
3. Keep terminal open
4. Plug laptop into power
5. Have backup demo video ready

**During demo**:
- Don't close the terminal!
- If bot crashes: `Ctrl+C` → `uv run python bot.py` to restart

---

**Good luck, Developer A! You're building the foundation that makes everything else possible. 🚀**

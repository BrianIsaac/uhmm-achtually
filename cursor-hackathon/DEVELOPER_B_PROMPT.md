# Developer B: Claim Processing & App Messages (8 hours)

## Your Role
You are Developer B, responsible for the intelligence layer of the fact-checker: extracting claims from sentences (Stage 4), verifying them via web search (Stage 5), and broadcasting verdicts to the Vue.js frontend via app messages (Stage 6).

**IMPORTANT**: Your code integrates into the Python bot that runs **on Developer A's laptop** (or your laptop if you're running it). The bot is NOT hosted by Daily.co - Daily only provides the WebRTC room infrastructure.

## Project Context
Building a real-time AI fact-checker bot that joins Daily.co video meetings, listens to conversations, extracts factual claims, verifies them via web search, and displays results in a custom Vue.js frontend. This is a **24-hour hackathon** with a 3-person team.

## Architecture Overview
**Triple-Client Pattern:**
- **Vue.js CallObject (Frontend - Developer C)**: Custom UI for displaying verdicts
- **Pipecat DailyTransport (Backend - Developer A)**: Audio pipeline processing (Stages 1-3)
- **Daily CallClient (Backend - YOU)**: Claim processing + app message broadcasting (Stages 4-6)

## Your Deliverables (Hours 0-8)

### H 0-2: Stage 4 (ClaimExtractor)
**Goal**: Extract factual claims from complete sentences using Groq LLM

**Tasks**:
1. **Understand input from Developer A**:
   You receive `LLMMessagesFrame` from Stage 3 (SentenceAggregator):
   ```python
   LLMMessagesFrame([{
       "role": "user",
       "content": "Python 3.12 removed the distutils package."
   }])
   ```

2. **Define ClaimFrame** (coordinate with Developer A):
   Ensure `backend/src/frames/custom_frames.py` has:
   ```python
   from dataclasses import dataclass
   from pipecat.frames.frames import Frame

   @dataclass
   class ClaimFrame(Frame):
       """Frame containing an extracted factual claim."""
       text: str
       claim_type: str  # version, api, regulatory, definition, number
   ```

3. **Implement ClaimExtractor**:
   Create `backend/src/processors/claim_extractor.py`:
   ```python
   """Extract factual claims from sentences using Groq LLM."""

   import os
   import json
   import logging
   from groq import Groq
   from pipecat.frames.frames import Frame, LLMMessagesFrame
   from pipecat.processors.frame_processor import FrameProcessor
   from src.frames.custom_frames import ClaimFrame

   logger = logging.getLogger(__name__)

   class ClaimExtractor(FrameProcessor):
       """Extract factual claims from sentences using Groq JSON mode."""

       SYSTEM_PROMPT = """Extract factual claims from the sentence.
   Return a JSON object with an array of claims.
   Each claim should have 'text' and 'type' fields.
   Types: version, api, regulatory, definition, number, decision.
   Only extract verifiable factual statements, not opinions or questions.
   If no factual claims exist, return empty array.

   Example:
   {"claims": [{"text": "Python 3.12 removed distutils", "type": "version"}]}
   """

       def __init__(self, groq_api_key: str):
           """Initialise claim extractor.

           Args:
               groq_api_key: Groq API key
           """
           super().__init__()
           self.groq_client = Groq(api_key=groq_api_key)

       async def process_frame(self, frame: Frame, direction):
           """Extract claims from LLMMessagesFrame.

           Args:
               frame: Incoming frame
               direction: Frame direction
           """
           if isinstance(frame, LLMMessagesFrame):
               sentence = frame.messages[0]["content"]
               logger.info(f"Extracting claims from: {sentence}")

               try:
                   # Call Groq with JSON mode
                   response = self.groq_client.chat.completions.create(
                       model="llama3.1-8b-instant",
                       messages=[
                           {"role": "system", "content": self.SYSTEM_PROMPT},
                           {"role": "user", "content": sentence}
                       ],
                       response_format={"type": "json_object"},
                       temperature=0.1
                   )

                   # Parse response
                   result = json.loads(response.choices[0].message.content)
                   claims = result.get("claims", [])

                   # Emit ClaimFrame for each claim
                   for claim in claims:
                       claim_frame = ClaimFrame(
                           text=claim["text"],
                           claim_type=claim["type"]
                       )
                       logger.info(f"Extracted claim: {claim_frame.text}")
                       await self.push_frame(claim_frame, direction)

               except Exception as e:
                   logger.error(f"Claim extraction failed: {e}")

           else:
               # Pass through other frames
               await self.push_frame(frame, direction)
   ```

4. **Manual verification**:
   - Test with sample sentences containing factual claims
   - Verify JSON parsing works correctly
   - Check claim types are assigned correctly

**Deliverable**: Claims extracted from sentences, JSON parsing 99%+ success rate

---

### H 2-5: Stage 5 (WebFactChecker)
**Goal**: Verify claims using Exa web search + Groq verification

**Tasks**:
1. **Define VerdictFrame**:
   Add to `backend/src/frames/custom_frames.py`:
   ```python
   @dataclass
   class VerdictFrame(Frame):
       """Frame containing fact-check verdict."""
       claim: str
       status: str  # supported, contradicted, unclear, not_found
       confidence: float  # 0.0 to 1.0
       rationale: str  # 1-2 sentence explanation
       evidence_url: str  # Source URL
   ```

2. **Implement Exa client wrapper**:
   Create `backend/src/services/exa_client.py`:
   ```python
   """Exa API client wrapper for web search."""

   from exa_py import Exa

   class ExaClient:
       """Wrapper for Exa neural search API."""

       def __init__(self, api_key: str, allowed_domains: list[str]):
           """Initialise Exa client.

           Args:
               api_key: Exa API key
               allowed_domains: List of allowed domains to search
           """
           self.exa = Exa(api_key=api_key)
           self.allowed_domains = allowed_domains

       async def search_for_claim(
           self,
           claim: str,
           num_results: int = 2
       ) -> list:
           """Search for evidence related to a claim.

           Args:
               claim: Factual claim to verify
               num_results: Number of results to return

           Returns:
               List of search results with title, url, text
           """
           response = self.exa.search_and_contents(
               claim,
               use_autoprompt=True,
               num_results=num_results,
               include_domains=self.allowed_domains,
               text={"max_characters": 2000}
           )
           return response.results
   ```

3. **Implement WebFactChecker**:
   Create `backend/src/processors/web_fact_checker.py`:
   ```python
   """Verify claims using Exa web search and Groq verification."""

   import json
   import logging
   from groq import Groq
   from pipecat.frames.frames import Frame
   from pipecat.processors.frame_processor import FrameProcessor
   from src.frames.custom_frames import ClaimFrame, VerdictFrame
   from src.services.exa_client import ExaClient

   logger = logging.getLogger(__name__)

   class WebFactChecker(FrameProcessor):
       """Verify claims using Exa web search and Groq verification.

       Phase 1: Web search only (no internal RAG).
       """

       VERIFICATION_PROMPT = """Verify this claim using the provided evidence passages.

   Claim: {claim}

   Evidence passages:
   {passages}

   Return JSON with:
   - status: "supported" | "contradicted" | "unclear" | "not_found"
   - confidence: 0.0 to 1.0
   - rationale: 1-2 sentence explanation
   - evidence_url: URL of most relevant source

   If no relevant evidence, return "not_found" status.
   Never fabricate information.
   """

       def __init__(
           self,
           exa_api_key: str,
           groq_api_key: str,
           allowed_domains: list[str]
       ):
           """Initialise fact checker.

           Args:
               exa_api_key: Exa API key
               groq_api_key: Groq API key
               allowed_domains: Allowed domains for search
           """
           super().__init__()
           self.exa_client = ExaClient(exa_api_key, allowed_domains)
           self.groq_client = Groq(api_key=groq_api_key)
           self._cache = {}  # In-memory cache

       async def process_frame(self, frame: Frame, direction):
           """Verify claims from ClaimFrame.

           Args:
               frame: Incoming frame
               direction: Frame direction
           """
           if isinstance(frame, ClaimFrame):
               claim = frame.text
               logger.info(f"Fact-checking: {claim}")

               # Check cache
               cache_key = f"claim:{claim}"
               if cache_key in self._cache:
                   logger.info(f"Cache hit: {claim}")
                   await self.push_frame(self._cache[cache_key], direction)
                   return

               try:
                   # Search with Exa
                   results = await self.exa_client.search_for_claim(claim)

                   if not results:
                       # No results found
                       verdict = VerdictFrame(
                           claim=claim,
                           status="not_found",
                           confidence=0.0,
                           rationale="No relevant evidence found in trusted sources.",
                           evidence_url=""
                       )
                   else:
                       # Verify with Groq
                       verdict_data = await self._verify_with_groq(claim, results)
                       verdict = VerdictFrame(
                           claim=claim,
                           status=verdict_data["status"],
                           confidence=verdict_data["confidence"],
                           rationale=verdict_data["rationale"],
                           evidence_url=verdict_data["evidence_url"]
                       )

                   # Cache result
                   self._cache[cache_key] = verdict
                   logger.info(f"Verdict: {verdict.status} ({verdict.confidence:.2f})")

                   await self.push_frame(verdict, direction)

               except Exception as e:
                   logger.error(f"Fact-checking failed: {e}")

           else:
               # Pass through other frames
               await self.push_frame(frame, direction)

       async def _verify_with_groq(self, claim: str, results: list) -> dict:
           """Verify claim using Groq LLM.

           Args:
               claim: Claim to verify
               results: Search results from Exa

           Returns:
               Dict with status, confidence, rationale, evidence_url
           """
           passages = json.dumps([
               {"title": r.title, "url": r.url, "text": r.text}
               for r in results
           ], indent=2)

           prompt = self.VERIFICATION_PROMPT.format(
               claim=claim,
               passages=passages
           )

           response = self.groq_client.chat.completions.create(
               model="llama3.1-8b-instant",
               messages=[{"role": "user", "content": prompt}],
               response_format={"type": "json_object"},
               temperature=0.1
           )

           return json.loads(response.choices[0].message.content)
   ```

4. **Manual verification**:
   - Test with known true claims
   - Test with known false claims
   - Verify cache works correctly

**Deliverable**: Claims verified via web search, verdicts with evidence URLs

---

### H 5-7: Stage 6 (FactCheckMessenger) + Optimisation
**Goal**: Broadcast verdicts to Vue.js frontend via app messages

**Tasks**:
1. **Understand triple-client pattern**:
   - **DailyTransport** (Stage 1): Audio input only
   - **CallClient** (Stage 6 - YOU): App messages only
   - **Vue.js CallObject** (Frontend): Receives app messages

2. **Implement FactCheckMessenger**:
   Create `backend/src/processors/fact_check_messenger.py`:
   ```python
   """Broadcast verdicts via app messages to Vue.js frontend."""

   import logging
   from daily import CallClient
   from pipecat.frames.frames import Frame
   from pipecat.processors.frame_processor import FrameProcessor
   from src.frames.custom_frames import VerdictFrame

   logger = logging.getLogger(__name__)

   class FactCheckMessenger(FrameProcessor):
       """Send fact-check verdicts via app messages to custom Vue.js frontend.

       Uses CallClient.send_app_message() to broadcast structured JSON.
       Frontend receives via 'app-message' event listener.
       """

       def __init__(self, call_client: CallClient, bot_name: str = "Fact Checker Bot"):
           """Initialise messenger.

           Args:
               call_client: Daily CallClient instance
               bot_name: Bot display name
           """
           super().__init__()
           self.call_client = call_client
           self.bot_name = bot_name

       async def process_frame(self, frame: Frame, direction):
           """Broadcast verdicts via app messages.

           Args:
               frame: Incoming frame
               direction: Frame direction
           """
           if isinstance(frame, VerdictFrame):
               # Format as JSON for frontend consumption
               message_data = {
                   'type': 'fact-check-verdict',
                   'claim': frame.claim,
                   'status': frame.status,  # 'supported', 'contradicted', 'unclear', 'not_found'
                   'confidence': frame.confidence,
                   'rationale': frame.rationale,
                   'evidence_url': frame.evidence_url
               }

               logger.info(f"Broadcasting verdict: {frame.claim} -> {frame.status}")

               try:
                   # Broadcast to all participants
                   self.call_client.send_app_message(
                       message_data,
                       '*'  # Send to all participants
                   )
               except Exception as e:
                   logger.error(f"App message send failed: {e}")

           # Always pass through frame
           await self.push_frame(frame, direction)
   ```

3. **Create CallClient setup function**:
   Create `backend/src/services/daily_message_client.py`:
   ```python
   """Daily CallClient setup for app messages."""

   from daily import CallClient, Daily

   async def create_message_client(room_url: str, token: str) -> CallClient:
       """Create and join CallClient for app messages.

       Args:
           room_url: Daily room URL
           token: Daily bot token

       Returns:
           Connected CallClient instance
       """
       Daily.init()
       client = CallClient()
       await client.join(
           url=room_url,
           client_settings={"token": token}
       )
       return client
   ```

4. **Optimise Exa search parameters**:
   - Tune `use_autoprompt=True`
   - Adjust `num_results` for latency
   - Test domain filtering effectiveness

5. **Add latency logging**:
   ```python
   import time

   start = time.time()
   # ... Exa search ...
   exa_latency = (time.time() - start) * 1000
   logger.info(f"Exa search: {exa_latency:.0f}ms")
   ```

**Deliverable**: Verdicts broadcast to frontend, latency optimised

---

### H 7-8: Integration & Manual Testing
**Goal**: Integrate all stages and test end-to-end

**Tasks**:
1. **Update bot.py to include your stages**:
   ```python
   # Add to Developer A's bot.py

   from src.processors.claim_extractor import ClaimExtractor
   from src.processors.web_fact_checker import WebFactChecker
   from src.processors.fact_check_messenger import FactCheckMessenger
   from src.services.daily_message_client import create_message_client

   # ... in main() ...

   # Stage 4: Claim Extractor
   claim_extractor = ClaimExtractor(groq_api_key=settings.groq_api_key)

   # Stage 5: Fact Checker
   fact_checker = WebFactChecker(
       exa_api_key=settings.exa_api_key,
       groq_api_key=settings.groq_api_key,
       allowed_domains=settings.allowed_domains
   )

   # Stage 6: Messenger (separate CallClient)
   message_client = await create_message_client(
       room_url=settings.daily_room_url,
       token=settings.daily_bot_token
   )
   messenger = FactCheckMessenger(call_client=message_client)

   # Complete pipeline
   pipeline = Pipeline([
       transport.input(),
       stt,
       aggregator,
       claim_extractor,     # Stage 4
       fact_checker,        # Stage 5
       messenger,           # Stage 6
       transport.output()
   ])
   ```

2. **Manual testing with demo claims**:
   Test these claims by speaking them in Daily room:
   - "Python 3.12 removed the distutils package." → **Supported**
   - "Kubernetes uses iptables by default in v1.29." → **Supported/Unclear**
   - "GDPR requires breach notification within 72 hours." → **Supported**
   - "React 18 introduced automatic batching." → **Supported**
   - "PostgreSQL 15 uses LLVM JIT by default." → **Contradicted**

3. **Debug edge cases**:
   - Test with malformed JSON responses
   - Test with empty search results
   - Test with no claims in sentence
   - Verify app messages reach frontend

4. **Coordinate with Developer C**:
   - Share app message format
   - Test verdict card rendering
   - Verify colours (green/red/yellow/grey) display correctly

**Deliverable**: Complete backend integrated, all test claims verified

---

## Integration with Other Developers

### You receive from Developer A:
- `src/frames/custom_frames.py` - Frame definitions
- `LLMMessagesFrame` format from Stage 3
- Pipeline structure for integration

### You provide to Developer A:
- `src/processors/claim_extractor.py` - Stage 4
- `src/processors/web_fact_checker.py` - Stage 5
- `src/processors/fact_check_messenger.py` - Stage 6

### You coordinate with Developer C:
- **App message format specification**:
  ```json
  {
    "type": "fact-check-verdict",
    "claim": "Python 3.12 removed distutils",
    "status": "supported",
    "confidence": 0.95,
    "rationale": "PEP 632 explicitly deprecated distutils",
    "evidence_url": "https://peps.python.org/pep-0632/"
  }
  ```
- Test end-to-end with frontend
- Verify verdict cards render correctly

---

## Success Criteria

By Hour 7, you should have:
- ✅ ClaimExtractor extracting claims with >99% JSON parse success
- ✅ WebFactChecker verifying via Exa + Groq
- ✅ In-memory caching working for repeated claims
- ✅ FactCheckMessenger broadcasting app messages
- ✅ Latency <750ms for search + verify combined
- ✅ All edge cases handled gracefully

By Hour 8, you should have:
- ✅ All 6 stages integrated into complete pipeline
- ✅ Manually tested with 5+ demo claims
- ✅ Verified verdicts appear in frontend
- ✅ Debugging logs for each stage

---

## Key Commands

```bash
# Test Groq LLM
uv run ipython
>>> from groq import Groq
>>> client = Groq(api_key="...")
>>> response = client.chat.completions.create(...)

# Test Exa search
uv run ipython
>>> from exa_py import Exa
>>> exa = Exa(api_key="...")
>>> results = exa.search_and_contents("Python 3.12 removed distutils", num_results=2)

# Run bot
uv run python backend/bot.py
```

---

## Important Notes

1. **Hackathon Mode**: No tests, focus on working code
2. **Manual Verification**: Test by speaking claims into Daily room
3. **JSON Mode**: Always use `response_format={"type": "json_object"}` for Groq
4. **Caching**: Use simple dict for in-memory cache (no Redis needed)
5. **Error Handling**: Log errors but don't crash pipeline
6. **Latency Budget**: Aim for <750ms total for Stages 4-5 combined
7. **App Messages**: Use `send_app_message()`, not `send_prebuilt_chat_message()`

---

## Troubleshooting

**Groq JSON parsing fails**:
- Check `response_format={"type": "json_object"}` is set
- Verify prompt asks for JSON explicitly
- Log raw response before parsing

**Exa returns no results**:
- Check allowed_domains list
- Try with `use_autoprompt=True`
- Increase `num_results` temporarily

**App messages not reaching frontend**:
- Verify CallClient joined room successfully
- Check frontend has 'app-message' event listener
- Test with simple message first

**Cache growing too large**:
- Add simple LRU eviction (max 1000 items)
- Clear cache on bot restart (it's in-memory only)

---

## Documentation References

- Groq: https://console.groq.com/docs
- Exa: https://docs.exa.ai
- Daily Python SDK: https://docs.daily.co/reference/daily-python
- Architecture: See `/cursor-hackathon/architecture_design.md`
- App Messages: See `/cursor-hackathon/components/09_daily_chat_delivery.md`

---

**Good luck, Developer B! You're the intelligence layer that makes the bot actually useful. 🧠**

# Component: LLM Processing (Groq Llama 3.1 8B Instant)

## Owner Assignment
**Developer B: Claim Processing (Stages 4-5)**
Responsible for both claim extraction and verification using Groq LLM

## Time Estimate: 5 hours
- Groq API setup and testing: 30 min
- Stage 4 (ClaimExtractor): 2 hours
- Stage 5 (WebFactChecker - LLM part): 2 hours
- Integration testing: 30 min

## Dependencies
```toml
[project.dependencies]
groq = ">=0.8.0"                 # Groq Python SDK
pydantic = ">=2.6.0"             # Data validation for JSON mode
pipecat-ai = ">=0.0.39"          # Core framework for processors
```

## Architecture Overview

**Stages 4 & 5 in Pipecat Pipeline:**
```
SentenceAggregator (Stage 3)
    ↓ (LLMMessagesFrame)
ClaimExtractor (Stage 4)  ← THIS COMPONENT (Part 1: Extract)
    ↓ (ClaimFrame)
WebFactChecker (Stage 5)  ← THIS COMPONENT (Part 2: Verify)
    ↓ (VerdictFrame)
FactCheckMessenger (Stage 6)
```

**Groq Usage:**
- **Stage 4:** Extract claims from sentences using JSON mode
- **Stage 5:** Verify claims against search results using JSON mode

## Input/Output Contracts

### Stage 4: ClaimExtractor

**Input (from SentenceAggregator):**
```python
LLMMessagesFrame
- messages: List[dict]  # [{"role": "user", "content": "sentence text"}]
```

**Output (to WebFactChecker):**
```python
ClaimFrame (custom frame type)
- text: str  # The extracted claim text
- claim_type: str  # version, api, regulatory, definition, number, decision
- timestamp: float  # When extracted
```

### Stage 5: WebFactChecker (LLM portion)

**Input:**
```python
# Claim + search results from Exa
claim: str
passages: List[dict]  # [{"title": str, "url": str, "text": str}]
```

**Output:**
```python
VerdictFrame (custom frame type)
- claim: str  # Original claim
- status: str  # supported, contradicted, unclear, not_found
- confidence: float  # 0.0-1.0
- rationale: str  # One-sentence explanation
- evidence_url: str  # Source URL
```

## Model Specifications

### Llama 3.1 8B Instant
- **Model ID:** `llama-3.1-8b-instant`
- **Context window:** 131,072 tokens (128K)
- **Speed:** ~560 tokens/second
- **Latency:** 50-150ms typical for our use case
- **Features:** JSON mode, function calling, structured outputs
- **Cost:** $0.05/20M input tokens, $0.08/13M output tokens

### Why Groq Llama 3.1 8B Instant?
- **Ultra-fast inference:** 50-150ms (vs 1-3s for standard LLMs)
- **JSON mode:** Guaranteed valid JSON output
- **128K context:** Handles large search results
- **Low cost:** Ideal for high-volume fact-checking
- **High quality:** 69.4% MMLU, 72.6% HumanEval

## Implementation Guide

### Step 1: Environment Setup (30 min)

**Install Groq SDK:**
```bash
# Using uv (recommended)
uv add groq pydantic

# Or using pip
pip install groq pydantic
```

**Configure API key:**
```bash
# Add to .env
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxx
```

**Verify installation:**
```python
from groq import Groq

client = Groq()
completion = client.chat.completions.create(
    model="llama-3.1-8b-instant",
    messages=[{"role": "user", "content": "Hello!"}]
)
print(completion.choices[0].message.content)
print("✓ Groq LLM configured successfully")
```

### Step 2: Implement ClaimExtractor (Stage 4) (2 hours)

Create `src/processors/claim_extractor.py`:

```python
"""Claim extraction processor using Groq Llama 3.1 with JSON mode."""

import os
import json
import logging
from typing import AsyncGenerator
from groq import AsyncGroq
from pipecat.frames import Frame, LLMMessagesFrame
from pipecat.processors import FrameProcessor
from src.frames.custom_frames import ClaimFrame

logger = logging.getLogger(__name__)


class ClaimExtractor(FrameProcessor):
    """Extract factual claims from sentences using Groq JSON mode.

    Consumes LLMMessagesFrame from SentenceAggregator.
    Emits ClaimFrame for each extracted claim.
    """

    SYSTEM_PROMPT = """You are a claim extraction system. Extract verifiable factual claims from sentences.

Return a JSON array of claims. Each claim must have:
- text: The exact claim statement
- type: One of (version, api, regulatory, definition, number, decision)

Only extract claims that are:
1. Factual and verifiable
2. Not opinions or subjective statements
3. Complete statements (not fragments)

Return empty array if no factual claims found.

Example input: "Python 3.12 removed distutils and Kubernetes uses iptables by default."
Example output:
{
  "claims": [
    {"text": "Python 3.12 removed distutils", "type": "version"},
    {"text": "Kubernetes uses iptables by default", "type": "api"}
  ]
}
"""

    def __init__(
        self,
        groq_api_key: str | None = None,
        model: str = "llama-3.1-8b-instant",
        temperature: float = 0.1
    ):
        """Initialise claim extractor with Groq client.

        Args:
            groq_api_key: Groq API key (defaults to GROQ_API_KEY env var)
            model: Groq model to use
            temperature: Sampling temperature (lower = more consistent)
        """
        super().__init__()

        api_key = groq_api_key or os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not found")

        self.client = AsyncGroq(api_key=api_key)
        self.model = model
        self.temperature = temperature

        logger.info(f"ClaimExtractor initialised with model: {model}")

    async def process_frame(self, frame: Frame) -> AsyncGenerator[Frame, None]:
        """Process LLMMessagesFrame and extract claims.

        Args:
            frame: Input frame (LLMMessagesFrame expected)

        Yields:
            ClaimFrame for each extracted claim, or original frame if not LLMMessagesFrame
        """
        if not isinstance(frame, LLMMessagesFrame):
            yield frame
            return

        # Extract sentence text from messages
        if not frame.messages or len(frame.messages) == 0:
            yield frame
            return

        sentence = frame.messages[0].get("content", "")
        if not sentence.strip():
            yield frame
            return

        logger.debug(f"Extracting claims from: {sentence[:100]}...")

        try:
            # Call Groq with JSON mode
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": sentence}
                ],
                response_format={"type": "json_object"},
                temperature=self.temperature,
                max_tokens=500  # Claims should be concise
            )

            # Parse JSON response
            content = response.choices[0].message.content
            result = json.loads(content)

            claims = result.get("claims", [])
            logger.info(f"Extracted {len(claims)} claims from sentence")

            # Emit ClaimFrame for each claim
            for claim in claims:
                claim_frame = ClaimFrame(
                    text=claim["text"],
                    claim_type=claim["type"]
                )
                yield claim_frame

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            # Continue processing, don't block pipeline
        except Exception as e:
            logger.error(f"Claim extraction failed: {e}")
            # Continue processing

        # Always yield original frame to allow pipeline continuation
        yield frame


# Test function
async def test_claim_extractor():
    """Test claim extractor with sample sentences."""
    import asyncio
    from pipecat.frames import LLMMessagesFrame

    extractor = ClaimExtractor()

    test_sentences = [
        "Python 3.12 removed the distutils package.",
        "GDPR requires breach notification within 72 hours.",
        "I think Python is a great language for beginners.",  # Opinion (should not extract)
        "Kubernetes uses iptables by default in version 1.29."
    ]

    for sentence in test_sentences:
        print(f"\nSentence: {sentence}")

        frame = LLMMessagesFrame([{"role": "user", "content": sentence}])

        async for output_frame in extractor.process_frame(frame):
            if isinstance(output_frame, ClaimFrame):
                print(f"  → Claim: {output_frame.text}")
                print(f"    Type: {output_frame.claim_type}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_claim_extractor())
```

### Step 3: Implement Verification (Stage 5 - LLM part) (2 hours)

Create `src/processors/web_fact_checker.py` (LLM verification portion):

```python
"""Fact verification using Exa search + Groq LLM."""

import os
import json
import logging
from typing import AsyncGenerator
from groq import AsyncGroq
from exa_py import Exa
from pipecat.frames import Frame
from pipecat.processors import FrameProcessor
from src.frames.custom_frames import ClaimFrame, VerdictFrame

logger = logging.getLogger(__name__)


class WebFactChecker(FrameProcessor):
    """Verify claims using Exa web search and Groq verification.

    Phase 1: Web search only (no internal RAG).
    Phase 2: Add BM25 routing for internal KB.

    Consumes ClaimFrame from ClaimExtractor.
    Emits VerdictFrame with verification results.
    """

    VERIFICATION_PROMPT = """You are a fact verification system. Verify the claim using the provided passages.

Claim: {claim}

Passages:
{passages}

Return JSON with:
- status: "supported" (passages confirm claim), "contradicted" (passages refute claim), "unclear" (insufficient evidence), or "not_found" (no relevant info)
- confidence: 0.0-1.0 (how confident are you?)
- rationale: One sentence explaining why (max 200 chars)
- evidence_url: URL of most relevant passage (or empty string if none)

Be strict: only mark "supported" or "contradicted" with high confidence (>0.7).
Use "unclear" if evidence is ambiguous or contradictory.
Use "not_found" if passages don't address the claim.

Example:
{{
  "status": "supported",
  "confidence": 0.9,
  "rationale": "Python 3.12 PEP 632 explicitly deprecated distutils.",
  "evidence_url": "https://peps.python.org/pep-0632/"
}}
"""

    def __init__(
        self,
        groq_api_key: str | None = None,
        exa_api_key: str | None = None,
        allowed_domains: list[str] | None = None,
        model: str = "llama-3.1-8b-instant",
        temperature: float = 0.1
    ):
        """Initialise fact checker with Groq and Exa clients.

        Args:
            groq_api_key: Groq API key (defaults to GROQ_API_KEY env var)
            exa_api_key: Exa API key (defaults to EXA_API_KEY env var)
            allowed_domains: List of allowed domains for web search
            model: Groq model for verification
            temperature: Sampling temperature
        """
        super().__init__()

        # Groq client
        groq_key = groq_api_key or os.getenv("GROQ_API_KEY")
        if not groq_key:
            raise ValueError("GROQ_API_KEY not found")
        self.groq_client = AsyncGroq(api_key=groq_key)
        self.model = model
        self.temperature = temperature

        # Exa client
        exa_key = exa_api_key or os.getenv("EXA_API_KEY")
        if not exa_key:
            raise ValueError("EXA_API_KEY not found")
        self.exa_client = Exa(api_key=exa_key)

        # Configuration
        self.allowed_domains = allowed_domains or [
            "docs.python.org",
            "kubernetes.io",
            "owasp.org",
            "www.nist.gov",
            "postgresql.org"
        ]

        # In-memory cache (Phase 1 - session scoped)
        self._cache: dict[str, VerdictFrame] = {}

        logger.info(f"WebFactChecker initialised with {len(self.allowed_domains)} allowed domains")

    async def process_frame(self, frame: Frame) -> AsyncGenerator[Frame, None]:
        """Process ClaimFrame and verify using web search.

        Args:
            frame: Input frame (ClaimFrame expected)

        Yields:
            VerdictFrame with verification results
        """
        if not isinstance(frame, ClaimFrame):
            yield frame
            return

        claim_text = frame.text
        logger.info(f"Verifying claim: {claim_text[:100]}...")

        # Check cache
        cache_key = f"claim:{claim_text}"
        if cache_key in self._cache:
            logger.debug("Cache hit for claim")
            yield self._cache[cache_key]
            return

        try:
            # Step 1: Exa search (300-600ms)
            search_results = self.exa_client.search_and_contents(
                claim_text,
                use_autoprompt=True,
                num_results=2,
                include_domains=self.allowed_domains,
                text={"max_characters": 2000}
            )

            if not search_results.results:
                logger.warning("No search results found")
                verdict_frame = VerdictFrame(
                    claim=claim_text,
                    status="not_found",
                    confidence=0.0,
                    rationale="No relevant information found in allowed sources.",
                    evidence_url=""
                )
                self._cache[cache_key] = verdict_frame
                yield verdict_frame
                return

            # Step 2: Format passages for LLM
            passages_text = "\n\n".join([
                f"Source: {result.title}\nURL: {result.url}\n{result.text[:1000]}"
                for result in search_results.results
            ])

            # Step 3: Groq verification (50-150ms)
            verdict = await self._verify_with_groq(claim_text, passages_text)

            # Create verdict frame
            verdict_frame = VerdictFrame(
                claim=claim_text,
                status=verdict["status"],
                confidence=verdict["confidence"],
                rationale=verdict["rationale"],
                evidence_url=verdict["evidence_url"]
            )

            # Cache result
            self._cache[cache_key] = verdict_frame
            logger.info(f"Verdict: {verdict['status']} (confidence: {verdict['confidence']:.2f})")

            yield verdict_frame

        except Exception as e:
            logger.error(f"Fact checking failed: {e}")
            # Return unclear verdict on error
            verdict_frame = VerdictFrame(
                claim=claim_text,
                status="unclear",
                confidence=0.0,
                rationale=f"Verification error: {str(e)[:100]}",
                evidence_url=""
            )
            yield verdict_frame

    async def _verify_with_groq(self, claim: str, passages: str) -> dict:
        """Call Groq LLM to verify claim against passages.

        Args:
            claim: The claim to verify
            passages: Formatted passages from Exa search

        Returns:
            Dict with status, confidence, rationale, evidence_url
        """
        prompt = self.VERIFICATION_PROMPT.format(
            claim=claim,
            passages=passages
        )

        response = await self.groq_client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=self.temperature,
            max_tokens=300
        )

        content = response.choices[0].message.content
        return json.loads(content)


# Test function
async def test_web_fact_checker():
    """Test fact checker with sample claims."""
    import asyncio
    from src.frames.custom_frames import ClaimFrame

    checker = WebFactChecker()

    test_claims = [
        ("Python 3.12 removed distutils", "version"),
        ("GDPR requires breach notification within 72 hours", "regulatory"),
        ("Kubernetes v1.29 uses iptables by default", "version")
    ]

    for claim_text, claim_type in test_claims:
        print(f"\nClaim: {claim_text}")

        frame = ClaimFrame(text=claim_text, claim_type=claim_type)

        async for output_frame in checker.process_frame(frame):
            if isinstance(output_frame, VerdictFrame):
                print(f"  Status: {output_frame.status}")
                print(f"  Confidence: {output_frame.confidence:.2f}")
                print(f"  Rationale: {output_frame.rationale}")
                print(f"  Source: {output_frame.evidence_url}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_web_fact_checker())
```

### Step 4: Define Custom Frame Types (30 min)

Create `src/frames/custom_frames.py`:

```python
"""Custom Pipecat frame types for fact-checking pipeline."""

import time
from dataclasses import dataclass
from pipecat.frames import Frame


@dataclass
class ClaimFrame(Frame):
    """Frame containing an extracted claim.

    Emitted by ClaimExtractor (Stage 4).
    Consumed by WebFactChecker (Stage 5).
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

    Emitted by WebFactChecker (Stage 5).
    Consumed by FactCheckMessenger (Stage 6).
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

## JSON Mode Configuration

### Groq JSON Mode Parameters
```python
response = await client.chat.completions.create(
    model="llama-3.1-8b-instant",
    messages=[...],
    response_format={"type": "json_object"},  # Enable JSON mode
    temperature=0.1,  # Lower = more consistent
    max_tokens=500  # Limit output length
)
```

### JSON Mode Benefits
- **Guaranteed valid JSON:** No parsing errors
- **Structured outputs:** No need for regex or string parsing
- **Type safety:** Direct deserialization to Pydantic models
- **Faster processing:** No retry logic for malformed JSON

### Prompt Engineering for JSON Mode
```python
# Bad: Vague JSON request
"Extract claims and return them as JSON"

# Good: Specific schema with examples
"""Return JSON with this exact structure:
{
  "claims": [
    {"text": "claim statement", "type": "version"}
  ]
}

Example input: "Python 3.12 removed distutils"
Example output: {"claims": [{"text": "Python 3.12 removed distutils", "type": "version"}]}
"""
```

## Performance Characteristics

### Latency Targets (Phase 1 MVP)
- **Stage 4 (ClaimExtractor):** 50-150ms per sentence
- **Stage 5 (WebFactChecker):**
  - Exa search: 300-600ms
  - Groq verify: 50-150ms
  - Total: 400-750ms per claim

### Throughput
- **Groq speed:** ~560 tokens/second
- **Typical claim extraction:** ~100 tokens input, ~50 tokens output = ~150ms
- **Typical verification:** ~500 tokens input, ~100 tokens output = ~100ms

### Cost Estimation (24h hackathon demo)
```
Assumptions:
- 100 sentences processed
- 0.5 claims per sentence = 50 claims
- Average 150 tokens per extraction call
- Average 600 tokens per verification call

Stage 4 costs:
  Input: 100 sentences × 150 tokens = 15,000 tokens
  Output: 50 claims × 50 tokens = 2,500 tokens
  Cost: ~$0.0001 (negligible)

Stage 5 costs:
  Input: 50 claims × 600 tokens = 30,000 tokens
  Output: 50 verdicts × 100 tokens = 5,000 tokens
  Cost: ~$0.0002 (negligible)

Total Groq cost for demo: <$0.001 (essentially free)
```

## Testing Strategy

### Unit Tests
```python
"""Test Groq LLM components."""

import pytest
import asyncio
from src.processors.claim_extractor import ClaimExtractor
from src.processors.web_fact_checker import WebFactChecker
from src.frames.custom_frames import ClaimFrame, VerdictFrame
from pipecat.frames import LLMMessagesFrame


@pytest.mark.asyncio
async def test_claim_extraction():
    """Test claim extraction with factual sentence."""
    extractor = ClaimExtractor()

    frame = LLMMessagesFrame([{
        "role": "user",
        "content": "Python 3.12 removed distutils"
    }])

    claims = []
    async for output_frame in extractor.process_frame(frame):
        if isinstance(output_frame, ClaimFrame):
            claims.append(output_frame)

    assert len(claims) > 0
    assert "distutils" in claims[0].text.lower()


@pytest.mark.asyncio
async def test_claim_extraction_opinion():
    """Test claim extraction ignores opinions."""
    extractor = ClaimExtractor()

    frame = LLMMessagesFrame([{
        "role": "user",
        "content": "I think Python is the best language"
    }])

    claims = []
    async for output_frame in extractor.process_frame(frame):
        if isinstance(output_frame, ClaimFrame):
            claims.append(output_frame)

    # Should not extract opinion as claim
    assert len(claims) == 0


@pytest.mark.asyncio
async def test_fact_verification():
    """Test fact verification with web search."""
    checker = WebFactChecker()

    frame = ClaimFrame(
        text="Python 3.12 removed distutils",
        claim_type="version"
    )

    verdicts = []
    async for output_frame in checker.process_frame(frame):
        if isinstance(output_frame, VerdictFrame):
            verdicts.append(output_frame)

    assert len(verdicts) == 1
    verdict = verdicts[0]

    assert verdict.status in ["supported", "contradicted", "unclear", "not_found"]
    assert 0.0 <= verdict.confidence <= 1.0
    assert len(verdict.rationale) > 0
```

### Integration Tests
```bash
# Test claim extraction
uv run python src/processors/claim_extractor.py

# Test fact checking
uv run python src/processors/web_fact_checker.py

# Test full pipeline (Stages 4-5)
uv run pytest tests/test_claim_processing.py -v
```

## Common Issues & Solutions

### Issue 1: JSON Parsing Errors
```python
# Problem: Groq returns invalid JSON despite json_object mode

# Solution: Add retry logic
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
async def call_groq_with_retry(...):
    response = await client.chat.completions.create(...)
    return json.loads(response.choices[0].message.content)
```

### Issue 2: Groq API Rate Limits
```python
# Problem: Rate limit exceeded during testing

# Solution: Add rate limiting
import asyncio

async def call_groq_with_rate_limit(...):
    await asyncio.sleep(0.1)  # 10 requests/second max
    return await client.chat.completions.create(...)
```

### Issue 3: Empty Claim Extraction
```python
# Problem: No claims extracted from factual sentences

# Solution: Lower temperature, improve prompt
temperature=0.0  # Most deterministic
# Add examples to SYSTEM_PROMPT
```

### Issue 4: Exa Search Returns No Results
```python
# Problem: No results for valid claims

# Solution: Expand allowed domains
allowed_domains = [
    "docs.python.org",
    "peps.python.org",  # Add PEPs
    "kubernetes.io",
    "github.com",  # Add GitHub docs
    # ... more domains
]
```

## Performance Benchmarks

### Latency Measurements (Groq Llama 3.1 8B Instant)
| Operation | Target | Typical | Notes |
|-----------|--------|---------|-------|
| Claim extraction | <150ms | ~100ms | 100 tokens in, 50 tokens out |
| Fact verification | <150ms | ~100ms | 500 tokens in, 100 tokens out |
| JSON parsing | <10ms | ~5ms | Minimal overhead |

### Accuracy Benchmarks
| Task | Accuracy | Notes |
|------|----------|-------|
| Claim extraction (factual) | >90% | Correctly identifies claims |
| Claim extraction (opinion filter) | >85% | Filters out opinions |
| Fact verification | >80% | Correct status assignment |

## Deliverables Checklist

- [ ] `src/processors/claim_extractor.py` - Stage 4 implementation
- [ ] `src/processors/web_fact_checker.py` - Stage 5 implementation
- [ ] `src/frames/custom_frames.py` - ClaimFrame & VerdictFrame
- [ ] GROQ_API_KEY configured in .env
- [ ] Unit tests passing for both stages
- [ ] Integration tests with real API calls successful
- [ ] Latency within targets (<150ms per LLM call)
- [ ] Ready for Stage 6 integration

## Next Steps for Integration

1. **Coordinate with Stage 3 Developer:**
   - Test LLMMessagesFrame → ClaimExtractor flow
   - Verify sentence completion triggers extraction

2. **Coordinate with Stage 6 Developer:**
   - Share VerdictFrame output format
   - Test VerdictFrame → Chat message formatting

3. **Coordinate with Exa Search Integration:**
   - WebFactChecker owns Exa client
   - May need separate `exa_client.py` wrapper

4. **Performance Monitoring:**
   - Log latency for each Groq call
   - Track claim extraction rate (claims/sentence)
   - Monitor Groq API quota usage

## Resources

**Groq Documentation:**
- Llama 3.1 8B Instant: https://console.groq.com/docs/model/llama-3.1-8b-instant
- JSON Mode: https://console.groq.com/docs/text-chat#json-mode
- API Keys: https://console.groq.com/keys
- Python SDK: https://github.com/groq/groq-python

**Pipecat Documentation:**
- FrameProcessor: https://docs.pipecat.ai/api-reference/processors
- Custom Frames: https://docs.pipecat.ai/api-reference/frames

**Exa Documentation:**
- Python SDK: https://docs.exa.ai/reference/python-sdk
- search_and_contents: https://docs.exa.ai/reference/search_and_contents

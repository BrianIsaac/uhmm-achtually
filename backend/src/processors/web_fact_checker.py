"""Stage 5: WebFactChecker processor.

Verify claims using Exa web search and Groq verification.
"""

import json
import logging
import time
from groq import Groq
from pipecat.frames.frames import Frame
from pipecat.processors.frame_processor import FrameProcessor

from src.frames.custom_frames import ClaimFrame, VerdictFrame
from src.services.exa_client import ExaClient

logger = logging.getLogger(__name__)


class WebFactChecker(FrameProcessor):
    """Verify claims using Exa web search and Groq verification.

    Phase 1: Web search only (no internal RAG).
    Caches results in memory for performance.
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

    async def process_frame(self, frame: Frame, direction: str):
        """Verify claims from ClaimFrame.

        Args:
            frame: Incoming frame
            direction: Frame direction (upstream/downstream)
        """
        await super().process_frame(frame, direction)

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
                # Measure search latency
                start_time = time.time()

                # Search with Exa
                results = await self.exa_client.search_for_claim(claim)

                exa_latency = (time.time() - start_time) * 1000
                logger.info(f"Exa search: {exa_latency:.0f}ms")

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
                    verify_start = time.time()
                    verdict_data = await self._verify_with_groq(claim, results)
                    verify_latency = (time.time() - verify_start) * 1000
                    logger.info(f"Groq verification: {verify_latency:.0f}ms")

                    verdict = VerdictFrame(
                        claim=claim,
                        status=verdict_data["status"],
                        confidence=verdict_data["confidence"],
                        rationale=verdict_data["rationale"],
                        evidence_url=verdict_data.get("evidence_url", "")
                    )

                # Cache result
                self._cache[cache_key] = verdict
                logger.info(f"Verdict: {verdict.status} (confidence: {verdict.confidence:.2f})")

                await self.push_frame(verdict, direction)

            except Exception as e:
                logger.error(f"Fact-checking failed: {e}", exc_info=True)

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
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.1
        )

        return json.loads(response.choices[0].message.content)

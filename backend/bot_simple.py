"""Ultra-simple fact-checker using PydanticAI directly.

Minimal dependencies, no Pipecat frames, just Daily.co transport for audio
and direct connection to PydanticAI pipeline.
"""

import asyncio
import os
import re
from dotenv import load_dotenv
from pipecat.transports.daily.transport import DailyParams, DailyTransport
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineTask

from src.services.stt import GroqSTT
from src.utils.config import get_settings
from src.utils.logger import setup_logger
from src.processors_v2.claim_extractor_v2 import ClaimExtractorV2
from src.processors_v2.web_fact_checker_v2 import WebFactCheckerV2

# Load environment variables
load_dotenv()

logger = setup_logger(__name__)


class SimpleBot:
    """Simple bot with direct PydanticAI integration."""

    def __init__(self):
        """Initialize the simple bot."""
        self.settings = get_settings()
        self.sentence_buffer = ""

        # Initialize PydanticAI components directly
        logger.info("[SIMPLE_BOT] Initializing PydanticAI components...")

        self.claim_extractor = ClaimExtractorV2(self.settings.groq_api_key)
        self.fact_checker = WebFactCheckerV2(
            groq_api_key=self.settings.groq_api_key,
            exa_api_key=self.settings.exa_api_key,
            allowed_domains=self.settings.allowed_domains_list
        )

        logger.info("[SIMPLE_BOT] PydanticAI components ready!")

    async def process_transcription(self, text: str):
        """Process transcribed text directly through PydanticAI.

        Args:
            text: Transcribed text from STT
        """
        # Buffer the text
        self.sentence_buffer += " " + text
        self.sentence_buffer = self.sentence_buffer.strip()

        # Check for complete sentences
        if re.search(r'[.!?]\s*$', self.sentence_buffer):
            sentence = self.sentence_buffer
            self.sentence_buffer = ""

            logger.info(f"[SIMPLE_BOT] Complete sentence: {sentence}")

            try:
                # Extract claims using PydanticAI
                logger.info("[SIMPLE_BOT] Extracting claims with PydanticAI...")
                claims = await self.claim_extractor.extract(sentence)

                if not claims:
                    logger.info("[SIMPLE_BOT] No claims found")
                    return

                logger.info(f"[SIMPLE_BOT] Found {len(claims)} claims")

                # Fact-check each claim using PydanticAI
                for claim in claims:
                    logger.info(f"[SIMPLE_BOT] Fact-checking: {claim.text}")
                    verdict = await self.fact_checker.verify(claim)

                    # Log the verdict
                    logger.info(
                        f"[SIMPLE_BOT] VERDICT: {verdict.claim}\n"
                        f"  Status: {verdict.status}\n"
                        f"  Confidence: {verdict.confidence:.2f}\n"
                        f"  Rationale: {verdict.rationale}"
                    )

            except Exception as e:
                logger.error(f"[SIMPLE_BOT] Error processing: {e}", exc_info=True)


async def main():
    """Run the simple bot."""
    settings = get_settings()

    logger.info("=" * 60)
    logger.info("SIMPLE FACT-CHECKER BOT")
    logger.info("Using PydanticAI directly - NO PIPECAT FRAMES!")
    logger.info("=" * 60)

    # Create the simple bot
    bot = SimpleBot()

    # Set up Daily transport for audio only
    vad_params = VADParams(
        start_secs=0.1,
        stop_secs=0.8,
        min_volume=0.5
    )
    vad = SileroVADAnalyzer(params=vad_params)

    transport = DailyTransport(
        settings.daily_room_url,
        None,
        "Simple Fact Checker",
        DailyParams(
            audio_in_enabled=True,
            audio_out_enabled=False,
            vad_analyzer=vad
        )
    )

    # Set up STT
    stt = GroqSTT(
        api_key=settings.groq_api_key,
        model="whisper-large-v3-turbo",
    )

    # Custom processor to intercept transcriptions
    class TranscriptionInterceptor:
        def __init__(self, bot):
            self.bot = bot

        async def process_transcription(self, frame):
            """Intercept transcription frames and process directly."""
            if hasattr(frame, 'text'):
                await self.bot.process_transcription(frame.text)

    interceptor = TranscriptionInterceptor(bot)

    # Create minimal pipeline
    pipeline = Pipeline([
        transport.input(),
        stt,
        # Transcriptions will be intercepted here
        transport.output()
    ])

    # Hook into STT output
    original_process = stt.process_frame

    async def hooked_process(frame, direction):
        # Process normally
        result = await original_process(frame, direction)

        # If it's a transcription, process it
        if hasattr(frame, 'text') and frame.text:
            await interceptor.process_transcription(frame)

        return result

    stt.process_frame = hooked_process

    # Run the pipeline
    task = PipelineTask(pipeline)
    runner = PipelineRunner()

    logger.info("[SIMPLE_BOT] Starting pipeline...")
    logger.info(f"[SIMPLE_BOT] Joining: {settings.daily_room_url}")

    try:
        await runner.run(task)
    except KeyboardInterrupt:
        logger.info("[SIMPLE_BOT] Shutting down...")


if __name__ == "__main__":
    asyncio.run(main())
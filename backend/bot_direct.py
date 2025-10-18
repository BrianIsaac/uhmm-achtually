#!/usr/bin/env python3
"""Direct fact-checker bot using ONLY PydanticAI - NO PIPECAT FRAMES AT ALL.

This version connects Daily.co transport directly to our PydanticAI pipeline,
completely bypassing Pipecat's frame processing system.
"""

import asyncio
import re
from dotenv import load_dotenv

# We'll still use Daily transport and STT, but NO frame processors
from pipecat.transports.daily.transport import DailyParams, DailyTransport
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.services.groq import GroqSTTService

from src.utils.config import get_settings
from src.utils.logger import setup_logger
from src.processors_v2.claim_extractor_v2 import ClaimExtractorV2
from src.processors_v2.web_fact_checker_v2 import WebFactCheckerV2
from src.processors_v2.fact_check_messenger_v2 import FactCheckMessengerV2

# Load environment variables
load_dotenv()

logger = setup_logger(__name__)


class DirectPydanticAIBot:
    """Direct integration of Daily.co → STT → PydanticAI pipeline."""

    def __init__(self):
        """Initialize the direct bot."""
        self.settings = get_settings()
        self.sentence_buffer = ""
        self.transport = None

        logger.info("=" * 70)
        logger.info("DIRECT PYDANTIC-AI FACT-CHECKER")
        logger.info("NO PIPECAT FRAMES - Direct STT → PydanticAI Pipeline")
        logger.info("=" * 70)

        # Initialize PydanticAI components
        logger.info("Initializing PydanticAI components...")

        self.claim_extractor = ClaimExtractorV2(self.settings.groq_api_key)
        self.fact_checker = WebFactCheckerV2(
            groq_api_key=self.settings.groq_api_key,
            exa_api_key=self.settings.exa_api_key,
            allowed_domains=self.settings.allowed_domains_list
        )

        logger.info("✅ PydanticAI components initialized!")

    async def setup_transport(self):
        """Set up Daily.co transport."""
        # VAD setup
        vad_params = VADParams(
            start_secs=0.1,
            stop_secs=0.8,
            min_volume=0.5
        )
        vad = SileroVADAnalyzer(params=vad_params)

        # Daily transport
        self.transport = DailyTransport(
            self.settings.daily_room_url,
            None,
            "Direct PydanticAI Bot",
            DailyParams(
                audio_in_enabled=True,
                audio_out_enabled=False,
                vad_analyzer=vad
            )
        )

        # Messenger for broadcasting
        self.messenger = FactCheckMessengerV2(self.transport)

        # STT service
        self.stt = GroqSTTService(
            api_key=self.settings.groq_api_key,
            model="whisper-large-v3-turbo"
        )

        logger.info(f"Joining room: {self.settings.daily_room_url}")

    async def process_audio(self):
        """Process audio directly without Pipecat frames."""
        # This is where we'd connect audio → STT → our pipeline
        # For now, we'll simulate with a test loop

        test_sentences = [
            "Python 3.12 removed the distutils package.",
            "The Earth is flat.",
            "Water boils at 100 degrees Celsius at sea level.",
        ]

        for sentence in test_sentences:
            logger.info(f"\n{'='*60}")
            logger.info(f"Processing: {sentence}")
            logger.info("="*60)

            await self.process_sentence(sentence)
            await asyncio.sleep(5)  # Pause between sentences

    async def process_sentence(self, sentence: str):
        """Process a sentence through the PydanticAI pipeline.

        Args:
            sentence: Complete sentence to process
        """
        try:
            # Step 1: Extract claims with PydanticAI
            logger.info("📝 Extracting claims...")
            claims = await self.claim_extractor.extract(sentence)

            if not claims:
                logger.info("❌ No factual claims found")
                return

            logger.info(f"✅ Found {len(claims)} claim(s)")
            for claim in claims:
                logger.info(f"   • {claim.text} (type: {claim.claim_type})")

            # Step 2: Fact-check each claim with PydanticAI
            logger.info("\n🔍 Fact-checking claims...")
            for i, claim in enumerate(claims, 1):
                logger.info(f"\nClaim {i}: {claim.text}")

                verdict = await self.fact_checker.verify(claim)

                # Display verdict
                status_emoji = {
                    "supported": "✅",
                    "contradicted": "❌",
                    "unclear": "❓",
                    "not_found": "🔍"
                }.get(verdict.status, "❓")

                logger.info(f"{status_emoji} Status: {verdict.status}")
                logger.info(f"   Confidence: {verdict.confidence:.2%}")
                logger.info(f"   Rationale: {verdict.rationale}")

                if verdict.evidence_url:
                    logger.info(f"   Evidence: {verdict.evidence_url}")

                # Broadcast verdict (if transport is set up)
                # Note: Commenting out for now as DailyTransport needs to be joined first
                # if self.transport and self.messenger:
                #     await self.messenger.broadcast(verdict)

        except Exception as e:
            logger.error(f"❌ Error processing sentence: {e}", exc_info=True)

    async def run(self):
        """Run the bot."""
        try:
            # Set up transport
            await self.setup_transport()

            # Process audio/sentences
            await self.process_audio()

        except KeyboardInterrupt:
            logger.info("\n⚠️ Shutting down...")
        except Exception as e:
            logger.error(f"❌ Fatal error: {e}", exc_info=True)
            raise


async def main():
    """Main entry point."""
    bot = DirectPydanticAIBot()
    await bot.run()


if __name__ == "__main__":
    asyncio.run(main())
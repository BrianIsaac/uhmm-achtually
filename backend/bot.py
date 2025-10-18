#!/usr/bin/env python3
"""Voice-enabled fact-checker bot using PydanticAI.

This version actually listens to voice input from Daily.co and processes it
through the PydanticAI pipeline in real-time.
"""

import asyncio
import re
from dotenv import load_dotenv

from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineTask
from pipecat.transports.daily.transport import DailyParams, DailyTransport
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.frames.frames import Frame, TranscriptionFrame
from loguru import logger

from src.services.stt import GroqSTT
from src.utils.config import get_settings, get_dev_config
from src.processors.claim_extractor import ClaimExtractor
from src.processors.web_fact_checker import WebFactChecker

# Load environment variables
load_dotenv()


class VoiceToPydanticAI(FrameProcessor):
    """Processor that intercepts transcriptions and sends them to PydanticAI."""

    def __init__(self, groq_api_key: str, exa_api_key: str):
        """Initialize with PydanticAI components.

        Args:
            groq_api_key: Groq API key
            exa_api_key: Exa API key
        """
        super().__init__()
        self.sentence_buffer = ""

        # Initialize PydanticAI components
        logger.info("Initializing PydanticAI components...")
        self.claim_extractor = ClaimExtractor(groq_api_key)
        self.fact_checker = WebFactChecker(
            groq_api_key=groq_api_key,
            exa_api_key=exa_api_key,
            allowed_domains=get_settings().allowed_domains_list
        )
        logger.info("PydanticAI components ready!")

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        """Process frames from the pipeline.

        Args:
            frame: Incoming frame
            direction: Frame direction
        """
        # Intercept TranscriptionFrames
        if isinstance(frame, TranscriptionFrame):
            text = frame.text
            logger.info(f"VOICE INPUT: {text}")

            # Buffer the transcription
            self.sentence_buffer += " " + text
            self.sentence_buffer = self.sentence_buffer.strip()

            # Check for complete sentences
            if re.search(r'[.!?]\s*$', self.sentence_buffer):
                sentence = self.sentence_buffer
                self.sentence_buffer = ""

                logger.info(f"Complete sentence: {sentence}")

                # Process through PydanticAI pipeline
                asyncio.create_task(self.process_sentence(sentence))

        # Forward the frame
        await super().process_frame(frame, direction)

    async def process_sentence(self, sentence: str):
        """Process a sentence through PydanticAI.

        Args:
            sentence: Complete sentence to process
        """
        try:
            logger.info("=" * 60)
            logger.info(f"PROCESSING: {sentence}")
            logger.info("=" * 60)

            # Extract claims with PydanticAI
            logger.info("Extracting claims with PydanticAI...")
            claims = await self.claim_extractor.extract(sentence)

            if not claims:
                logger.info("No factual claims found")
                return

            logger.info(f"Found {len(claims)} claim(s)")
            for claim in claims:
                logger.info(f"   - {claim.text} (type: {claim.claim_type})")

            # Fact-check each claim with PydanticAI
            logger.info("\nFact-checking with PydanticAI...")
            for i, claim in enumerate(claims, 1):
                logger.info(f"\nClaim {i}: {claim.text}")

                try:
                    verdict = await self.fact_checker.verify(claim)

                    # Display verdict
                    logger.info(f"   Status: {verdict.status}")
                    logger.info(f"   Confidence: {verdict.confidence:.2%}")
                    logger.info(f"   Rationale: {verdict.rationale}")

                    if verdict.evidence_url:
                        logger.info(f"   Evidence: {verdict.evidence_url}")

                except Exception as e:
                    logger.error(f"   Error fact-checking claim: {e}")

            logger.info("=" * 60 + "\n")

        except Exception as e:
            logger.error(f"Error processing sentence: {e}", exc_info=True)


async def main():
    """Run the voice-enabled PydanticAI fact-checker."""
    settings = get_settings()
    dev_config = get_dev_config()

    logger.info("=" * 70)
    logger.info("VOICE-ENABLED PYDANTIC-AI FACT-CHECKER")
    logger.info("Listening for voice input -> Processing with PydanticAI")
    logger.info("=" * 70)

    try:
        # Set up VAD
        vad_params = VADParams(
            start_secs=0.1,
            stop_secs=0.8,
            min_volume=0.5
        )
        vad = SileroVADAnalyzer(params=vad_params)

        # Set up Daily transport
        transport = DailyTransport(
            settings.DAILY_ROOM_URL,
            None,
            "PydanticAI Voice Bot",
            DailyParams(
                audio_in_enabled=True,
                audio_out_enabled=False,
                vad_analyzer=vad
            )
        )

        # Set up STT
        stt = GroqSTT(
            api_key=settings.GROQ_API_KEY,
            model="whisper-large-v3-turbo"
        )

        # Set up our PydanticAI processor
        pydantic_processor = VoiceToPydanticAI(
            groq_api_key=settings.GROQ_API_KEY,
            exa_api_key=settings.EXA_API_KEY
        )

        # Create pipeline: Transport → STT → PydanticAI Processor
        pipeline = Pipeline([
            transport.input(),
            stt,
            pydantic_processor,
            transport.output()
        ])

        # Run the pipeline
        task = PipelineTask(pipeline)
        runner = PipelineRunner()

        logger.info(f"Joining room: {settings.DAILY_ROOM_URL}")
        logger.info("Ready to listen! Speak into your microphone...")
        logger.info("Try saying: 'Python 3.12 removed the distutils package.'")
        logger.info("=" * 70 + "\n")

        await runner.run(task)

    except KeyboardInterrupt:
        logger.info("\nShutting down...")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main())

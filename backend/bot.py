"""Main entry point for the fact-checker bot.

Initialises and runs the Pipecat pipeline using V2 processors with PydanticAI.
"""

import asyncio
import os
import sys

from dotenv import load_dotenv
from loguru import logger
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineTask
from pipecat.transcriptions.language import Language
from pipecat.transports.daily.transport import DailyParams, DailyTransport

from src.processors.continuous_audio_aggregator import ContinuousAudioAggregator
from src.processors.sentence_aggregator import SentenceAggregator
from src.processors.pipeline_bridge import PipelineBridge
from src.services.stt import AvalonSTT, GroqSTT
from src.utils.config import get_dev_config, get_settings
from src.utils.pipecat_patch import apply_pipecat_patch

# Load environment variables
load_dotenv()


async def main():
    """Run the fact-checker bot with V2 pipeline."""
    # IMPORTANT: Apply Pipecat 0.0.90 race condition patch BEFORE creating any processors
    # This fixes: AttributeError: '__process_queue' not found
    # See: https://github.com/pipecat-ai/pipecat/issues/2385
    # Remove this once upgrading to Pipecat >= 0.0.91 (when fix is released)
    apply_pipecat_patch()

    settings = get_settings()
    dev_config = get_dev_config()
    logger.info("Starting fact-checker bot with V2 pipeline...")
    logger.info(f"Daily room URL: {settings.DAILY_ROOM_URL}")
    logger.info(f"VAD disabled: {dev_config.vad.disable}")

    try:
        # Stage 1: DailyTransport (with or without VAD based on config)
        if dev_config.vad.disable:
            # No VAD - continuous audio processing
            logger.info("VAD disabled - using continuous audio processing")
            transport = DailyTransport(
                settings.DAILY_ROOM_URL,
                None,  # No token for public rooms
                "Fact Checker Bot",
                DailyParams(
                    audio_in_enabled=True,
                    audio_out_enabled=False,  # No TTS in Phase 1
                    vad_enabled=False
                )
            )
        else:
            # VAD enabled - traditional segmented approach
            logger.info(
                f"VAD enabled - start_secs={dev_config.vad.start_secs}, "
                f"stop_secs={dev_config.vad.stop_secs}, "
                f"min_volume={dev_config.vad.min_volume}"
            )
            # Create VAD analyzer with custom parameters
            vad_params = VADParams(
                start_secs=dev_config.vad.start_secs,
                stop_secs=dev_config.vad.stop_secs,
                min_volume=dev_config.vad.min_volume
            )
            vad_analyzer = SileroVADAnalyzer(params=vad_params)
            transport = DailyTransport(
                settings.DAILY_ROOM_URL,
                None,  # No token for public rooms
                "Fact Checker Bot",
                DailyParams(
                    audio_in_enabled=True,
                    audio_out_enabled=False,  # No TTS in Phase 1
                    vad_analyzer=vad_analyzer
                )
            )

        # Stage 2: STT Service (provider-based)
        stt_provider = dev_config.stt.provider
        if stt_provider == "avalon":
            if not settings.AVALON_API_KEY:
                raise ValueError(
                    "AVALON_API_KEY environment variable not set but STT provider is 'avalon'. "
                    "Please add AVALON_API_KEY to your .env file or change provider in dev_config.yaml"
                )
            # Convert language string to Language enum (e.g., "en" -> Language.EN)
            avalon_language = getattr(Language, dev_config.stt.avalon.language.upper())
            stt = AvalonSTT(
                api_key=settings.AVALON_API_KEY,
                model=dev_config.stt.avalon.model,
                language=avalon_language
            )
            logger.info(
                f"Using Avalon STT (model: {dev_config.stt.avalon.model}, "
                f"language: {dev_config.stt.avalon.language})"
            )
        elif stt_provider == "groq":
            # Convert language string to Language enum (e.g., "en" -> Language.EN)
            groq_language = getattr(Language, dev_config.stt.groq.language.upper())
            stt = GroqSTT(
                api_key=settings.GROQ_API_KEY,
                model=dev_config.stt.groq.model,
                language=groq_language
            )
            logger.info(
                f"Using Groq STT (model: {dev_config.stt.groq.model}, "
                f"language: {dev_config.stt.groq.language})"
            )
        else:
            raise ValueError(f"Unknown STT provider: {stt_provider}. Must be 'groq' or 'avalon'")

        # Stage 3: SentenceAggregator
        aggregator = SentenceAggregator()

        # Check if we have required API keys for V2 pipeline
        if not settings.EXA_API_KEY:
            logger.error("EXA_API_KEY not found - fact-checking requires this API key")
            raise ValueError("EXA_API_KEY is required for fact-checking functionality")

        # Use V2 pipeline with PydanticAI
        logger.info("Using V2 Pipeline with PydanticAI")

        pipeline_bridge = PipelineBridge(
            groq_api_key=settings.GROQ_API_KEY,
            exa_api_key=settings.EXA_API_KEY,
            daily_transport=transport,
            allowed_domains=settings.allowed_domains_list
        )

        logger.info("V2 Pipeline bridge enabled - using modern async processing")

        # Build pipeline
        pipeline_stages = [
            transport.input(),
        ]

        # Add STT stage (with or without continuous audio aggregator)
        if dev_config.vad.disable:
            # Insert ContinuousAudioAggregator before sentence aggregator
            continuous_audio = ContinuousAudioAggregator(stt_service=stt)
            pipeline_stages.append(continuous_audio)
        else:
            # Use traditional VAD-based STT
            pipeline_stages.append(stt)

        pipeline_stages.append(aggregator)

        # Add V2 bridge
        pipeline_stages.append(pipeline_bridge)

        pipeline_stages.append(transport.output())

        pipeline = Pipeline(pipeline_stages)

        task = PipelineTask(pipeline)

        # Run the pipeline
        runner = PipelineRunner()
        await runner.run(task)

    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Error running bot: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
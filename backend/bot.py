"""Main entry point for the fact-checker bot.

Initialises and runs the Pipecat pipeline with all 6 stages:
- Stage 1: DailyTransport with Silero VAD
- Stage 2: GroqSTTService
- Stage 3: SentenceAggregator
- Stage 4: ClaimExtractor
- Stage 5: WebFactChecker
- Stage 6: FactCheckMessenger
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineTask
from pipecat.transports.daily.transport import DailyParams, DailyTransport
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.transcriptions.language import Language

from src.services.stt import GroqSTT, AvalonSTT
from src.utils.config import get_settings, get_dev_config
from src.utils.logger import setup_logger
from src.utils.pipecat_patch import apply_pipecat_patch
from src.processors.sentence_aggregator import SentenceAggregator
from src.processors.claim_extractor import ClaimExtractor
from src.processors.web_fact_checker import WebFactChecker
from src.processors.fact_check_messenger import FactCheckMessenger
from src.processors.continuous_audio_aggregator import ContinuousAudioAggregator
# V2 pipeline bridge
from src.processors_v2.pipeline_bridge import PipelineBridge

# Load environment variables
load_dotenv()

logger = setup_logger(__name__)


async def main():
    """Run the fact-checker bot with complete Pipecat pipeline (Stages 1-6)."""
    # IMPORTANT: Apply Pipecat 0.0.90 race condition patch BEFORE creating any processors
    # This fixes: AttributeError: '__process_queue' not found
    # See: https://github.com/pipecat-ai/pipecat/issues/2385
    # Remove this once upgrading to Pipecat >= 0.0.91 (when fix is released)
    apply_pipecat_patch()

    settings = get_settings()
    dev_config = get_dev_config()
    logger.info("Starting fact-checker bot (All 6 stages)...")
    logger.info(f"Daily room URL: {settings.daily_room_url}")
    logger.info(f"VAD disabled: {dev_config.vad.disable}")

    try:
        # Stage 1: DailyTransport (with or without VAD based on config)
        if dev_config.vad.disable:
            # No VAD - continuous audio processing
            logger.info("VAD disabled - using continuous audio processing")
            transport = DailyTransport(
                settings.daily_room_url,
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
                settings.daily_room_url,
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
            if not settings.avalon_api_key:
                raise ValueError(
                    "AVALON_API_KEY environment variable not set but STT provider is 'avalon'. "
                    "Please add AVALON_API_KEY to your .env file or change provider in dev_config.yaml"
                )
            # Convert language string to Language enum (e.g., "en" -> Language.EN)
            avalon_language = getattr(Language, dev_config.stt.avalon.language.upper())
            stt = AvalonSTT(
                api_key=settings.avalon_api_key,
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
                api_key=settings.groq_api_key,
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

        # Use V2 Pipeline if enabled (default: True)
        use_v2_pipeline = getattr(dev_config, "use_v2_pipeline", True)

        if use_v2_pipeline and settings.exa_api_key:
            # Use new V2 pipeline with PydanticAI and Instructor
            logger.info("Using V2 Pipeline with PydanticAI and Instructor")

            pipeline_bridge = PipelineBridge(
                groq_api_key=settings.groq_api_key,
                exa_api_key=settings.exa_api_key,
                daily_transport=transport,
                allowed_domains=settings.allowed_domains_list
            )

            # For V2, we only need the bridge after aggregator
            claim_extractor = None
            fact_checker = None
            messenger = None

            logger.info("V2 Pipeline bridge enabled - using modern async processing")

        else:
            # Use original pipeline (fallback)
            logger.info("Using original Pipecat pipeline")

            # Stage 4: ClaimExtractor
            claim_extractor = ClaimExtractor(groq_api_key=settings.groq_api_key)

            # Stage 5: WebFactChecker
            if settings.exa_api_key:
                fact_checker = WebFactChecker(
                    exa_api_key=settings.exa_api_key,
                    groq_api_key=settings.groq_api_key,
                    allowed_domains=settings.allowed_domains_list
                )
                logger.info("Exa fact-checking enabled")
            else:
                logger.warning("EXA_API_KEY not found - fact-checking disabled")
                fact_checker = None

            # Stage 6: FactCheckMessenger (reuses DailyTransport)
            if fact_checker:
                messenger = FactCheckMessenger(transport=transport)
                logger.info("App message broadcasting enabled")
            else:
                messenger = None

            pipeline_bridge = None

        # Build pipeline (conditionally include Stages 4-6)
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

        # Add either V2 bridge or original processors
        if pipeline_bridge:
            # V2 Pipeline: SentenceAggregator -> PipelineBridge
            pipeline_stages.append(pipeline_bridge)
        else:
            # Original Pipeline: SentenceAggregator -> ClaimExtractor -> WebFactChecker -> Messenger
            if claim_extractor:
                pipeline_stages.append(claim_extractor)

            if fact_checker:
                pipeline_stages.append(fact_checker)

            if messenger:
                pipeline_stages.append(messenger)

        pipeline_stages.append(transport.output())

        pipeline = Pipeline(pipeline_stages)

        task = PipelineTask(pipeline)

        # Run the pipeline
        runner = PipelineRunner()
        await runner.run(task)

    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Error running bot: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

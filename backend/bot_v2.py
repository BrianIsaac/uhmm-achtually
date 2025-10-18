"""Simplified fact-checker bot using PydanticAI without Pipecat frames.

This version uses Daily.co directly for audio and connects straight to
the PydanticAI pipeline, avoiding all Pipecat frame complexity.
"""

import asyncio
import os
import sys
from dotenv import load_dotenv
from daily import Daily, CallClient, EventHandler
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams

from src.services.stt import GroqSTT
from src.utils.config import get_settings, get_dev_config
from src.utils.logger import setup_logger
from src.processors_v2.pipeline_coordinator import FactCheckPipeline

# Load environment variables
load_dotenv()

logger = setup_logger(__name__)


class SimplifiedFactCheckerBot(EventHandler):
    """Simplified bot that bypasses Pipecat frames entirely."""

    def __init__(self, room_url: str, groq_api_key: str, exa_api_key: str):
        """Initialize the bot with direct Daily.co and PydanticAI pipeline.

        Args:
            room_url: Daily.co room URL
            groq_api_key: Groq API key
            exa_api_key: Exa API key
        """
        super().__init__()

        # Initialize Daily.co client
        self.client = CallClient(event_handler=self)
        self.room_url = room_url

        # Initialize STT
        self.stt = GroqSTT(
            api_key=groq_api_key,
            model="whisper-large-v3-turbo",
        )

        # Initialize PydanticAI pipeline directly
        self.pipeline = FactCheckPipeline(
            groq_api_key=groq_api_key,
            exa_api_key=exa_api_key,
            daily_transport=None,  # We'll handle messaging directly
            allowed_domains=get_settings().allowed_domains_list,
        )

        # Audio buffer for STT
        self.audio_buffer = bytearray()
        self.sentence_buffer = ""

        # VAD for voice detection
        vad_params = VADParams(
            start_secs=0.1,
            stop_secs=0.8,
            min_volume=0.5
        )
        self.vad = SileroVADAnalyzer(params=vad_params)

        logger.info("[BOT_V2] Simplified fact-checker initialized with PydanticAI")

    async def start(self):
        """Start the bot and join the Daily.co room."""
        logger.info(f"[BOT_V2] Joining room: {self.room_url}")

        # Join the Daily.co room
        await self.client.join(self.room_url)
        logger.info("[BOT_V2] Successfully joined room")

        # Start listening for audio
        self.client.start_recording()
        logger.info("[BOT_V2] Started recording audio")

    async def on_audio_data(self, audio_data: bytes):
        """Handle incoming audio data directly.

        Args:
            audio_data: Raw audio bytes
        """
        # Add to buffer
        self.audio_buffer.extend(audio_data)

        # Process when we have enough audio (e.g., 2 seconds worth)
        if len(self.audio_buffer) > 32000:  # 16kHz * 2 bytes * 1 second
            await self.process_audio_buffer()

    async def process_audio_buffer(self):
        """Process the audio buffer through STT."""
        if not self.audio_buffer:
            return

        try:
            # Convert buffer to WAV and transcribe
            audio_bytes = bytes(self.audio_buffer)
            self.audio_buffer.clear()

            # Transcribe with Groq STT
            transcription = await self.stt.transcribe(audio_bytes)

            if transcription and transcription.strip():
                logger.info(f"[BOT_V2] Transcribed: {transcription}")

                # Add to sentence buffer
                self.sentence_buffer += " " + transcription
                self.sentence_buffer = self.sentence_buffer.strip()

                # Check for complete sentences
                if self._is_complete_sentence(self.sentence_buffer):
                    await self.process_sentence(self.sentence_buffer)
                    self.sentence_buffer = ""

        except Exception as e:
            logger.error(f"[BOT_V2] Error processing audio: {e}", exc_info=True)

    def _is_complete_sentence(self, text: str) -> bool:
        """Check if text ends with sentence punctuation."""
        import re
        return bool(re.search(r'[.!?]\s*$', text.strip()))

    async def process_sentence(self, sentence: str):
        """Process a complete sentence through the PydanticAI pipeline.

        Args:
            sentence: Complete sentence to process
        """
        logger.info(f"[BOT_V2] Processing sentence: {sentence}")

        try:
            # Process through PydanticAI pipeline
            verdicts = await self.pipeline.process_sentence(sentence)

            # Broadcast results
            for verdict in verdicts:
                await self.broadcast_verdict(verdict)

        except Exception as e:
            logger.error(f"[BOT_V2] Error processing sentence: {e}", exc_info=True)

    async def broadcast_verdict(self, verdict):
        """Broadcast a verdict to room participants.

        Args:
            verdict: FactCheckVerdict to broadcast
        """
        message = {
            'type': 'fact-check-verdict',
            'claim': verdict.claim,
            'status': verdict.status,
            'confidence': verdict.confidence,
            'rationale': verdict.rationale,
            'evidence_url': verdict.evidence_url,
        }

        # Send app message via Daily.co
        self.client.send_app_message(message, '*')
        logger.info(f"[BOT_V2] Broadcast verdict: {verdict.claim} -> {verdict.status}")

    async def leave(self):
        """Leave the Daily.co room."""
        logger.info("[BOT_V2] Leaving room...")
        await self.client.leave()
        logger.info("[BOT_V2] Left room")


async def main():
    """Run the simplified bot without Pipecat frames."""
    settings = get_settings()
    dev_config = get_dev_config()

    logger.info("[BOT_V2] Starting simplified fact-checker bot (NO PIPECAT FRAMES!)")
    logger.info(f"[BOT_V2] Daily room URL: {settings.daily_room_url}")

    try:
        # Create and start the bot
        bot = SimplifiedFactCheckerBot(
            room_url=settings.daily_room_url,
            groq_api_key=settings.groq_api_key,
            exa_api_key=settings.exa_api_key,
        )

        await bot.start()

        # Keep running until interrupted
        while True:
            await asyncio.sleep(1)

    except KeyboardInterrupt:
        logger.info("[BOT_V2] Received interrupt, shutting down...")
        await bot.leave()
    except Exception as e:
        logger.error(f"[BOT_V2] Error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
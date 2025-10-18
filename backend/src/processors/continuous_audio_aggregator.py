"""Continuous audio aggregator for bypassing VAD.

This processor buffers audio frames and periodically sends them to STT,
allowing transcription without relying on Voice Activity Detection.
"""

import io
import wave

from loguru import logger
from pipecat.frames.frames import (
    Frame,
    StartFrame,
    CancelFrame,
    UserAudioRawFrame,
    TranscriptionFrame,
    ErrorFrame,
)
from pipecat.processors.frame_processor import FrameProcessor
from pipecat.services.groq.stt import GroqSTTService

from src.utils.config import get_dev_config


class ContinuousAudioAggregator(FrameProcessor):
    """Aggregates audio frames and sends them to STT without VAD.

    Buffers UserAudioRawFrame chunks for a configurable duration, then
    creates a WAV file and sends it directly to GroqSTTService for transcription.

    This bypasses Voice Activity Detection when VAD is not working properly.

    Attributes:
        stt_service: GroqSTTService instance for transcription
        buffer_duration: Seconds of audio to buffer before transcription
        overlap: Whether to overlap buffers by 50%
        sample_rate: Audio sample rate (16000 Hz for Daily.co)
        bytes_per_sample: Bytes per audio sample (2 for 16-bit)
    """

    def __init__(self, stt_service: GroqSTTService):
        """Initialise the continuous audio aggregator.

        Args:
            stt_service: GroqSTTService instance for transcription
        """
        super().__init__()
        self._stt_service = stt_service
        self._config = get_dev_config()

        # Audio parameters (Daily.co standard: 16kHz, 16-bit, mono)
        self._sample_rate = 16000
        self._bytes_per_sample = 2

        # Buffer configuration
        self._buffer_duration = self._config.continuous_audio.buffer_duration
        self._overlap = self._config.continuous_audio.overlap

        # Calculate buffer size in bytes
        # Formula: sample_rate * bytes_per_sample * duration
        self._buffer_size = int(
            self._sample_rate * self._bytes_per_sample * self._buffer_duration
        )

        # Audio buffer
        self._audio_buffer = bytearray()

        # Overlap buffer (stores last 50% of previous buffer)
        self._overlap_buffer = bytearray()

        logger.info(
            f"ContinuousAudioAggregator initialised: "
            f"buffer_duration={self._buffer_duration}s, "
            f"overlap={self._overlap}, "
            f"buffer_size={self._buffer_size} bytes"
        )

    async def process_frame(self, frame: Frame, direction):
        """Process incoming frames.

        Buffers UserAudioRawFrame chunks and sends them to STT when buffer is full.

        Args:
            frame: Frame to process
            direction: Frame direction (not used)
        """
        # Handle control frames
        if isinstance(frame, StartFrame):
            # Reset buffers on start
            self._audio_buffer = bytearray()
            self._overlap_buffer = bytearray()
            await self.push_frame(frame, direction)
            return

        if isinstance(frame, CancelFrame):
            # Clear buffers on cancel
            self._audio_buffer = bytearray()
            self._overlap_buffer = bytearray()
            await self.push_frame(frame, direction)
            return

        # Only process audio frames
        if not isinstance(frame, UserAudioRawFrame):
            await self.push_frame(frame, direction)
            return

        # Add audio to buffer
        self._audio_buffer.extend(frame.audio)

        # Check if buffer is full
        if len(self._audio_buffer) >= self._buffer_size:
            # Get exact buffer amount (may have extra bytes)
            audio_chunk = bytes(self._audio_buffer[:self._buffer_size])

            # Store overlap if configured (last 50% of buffer)
            if self._overlap:
                overlap_start = self._buffer_size // 2
                self._overlap_buffer = bytearray(self._audio_buffer[overlap_start:self._buffer_size])

            # Clear buffer and restore overlap
            self._audio_buffer = bytearray()
            if self._overlap:
                self._audio_buffer.extend(self._overlap_buffer)

            # Send to STT
            try:
                logger.debug(f"Processing {len(audio_chunk)} bytes of audio")

                # Create WAV file from PCM data
                wav_content = self._create_wav(audio_chunk)

                # Call STT service directly
                transcription = await self._stt_service._transcribe(wav_content)

                if transcription and transcription.text.strip():
                    logger.info(f"Transcription: {transcription.text}")
                    await self.push_frame(
                        TranscriptionFrame(
                            text=transcription.text,
                            user_id="",
                            timestamp=frame.timestamp if hasattr(frame, 'timestamp') else ""
                        ),
                        direction
                    )
                else:
                    logger.debug("Empty transcription received")

            except Exception as e:
                logger.error(f"STT error: {e}")
                await self.push_frame(ErrorFrame(f"STT transcription failed: {e}"), direction)

        # Always pass through the original frame
        await self.push_frame(frame, direction)

    def _create_wav(self, pcm_data: bytes) -> bytes:
        """Create a WAV file from PCM audio data.

        Args:
            pcm_data: Raw PCM audio bytes (16-bit, mono, 16kHz)

        Returns:
            Complete WAV file as bytes
        """
        content = io.BytesIO()
        with wave.open(content, "wb") as wav:
            wav.setnchannels(1)  # Mono
            wav.setsampwidth(self._bytes_per_sample)  # 16-bit
            wav.setframerate(self._sample_rate)  # 16kHz
            wav.writeframes(pcm_data)

        content.seek(0)
        return content.read()

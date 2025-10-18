"""Audio stream processor for real-time transcription.

This module handles audio capture from the system and manages
the transcription queue for the WebSocket server.
"""

import asyncio
import time
from typing import Optional, Callable, Awaitable
from collections import deque
import numpy as np
import sounddevice as sd
from loguru import logger
import wave
import io

from src.services.stt import GroqSTT


class AudioStreamProcessor:
    """Processes audio stream and manages transcription."""

    def __init__(
        self,
        stt: GroqSTT,
        on_transcription: Callable[[str], Awaitable[None]],
        sample_rate: int = 16000,
        channels: int = 1,
        device: Optional[int] = None
    ):
        """Initialize audio stream processor.

        Args:
            stt: Speech-to-text service
            on_transcription: Async callback for transcriptions
            sample_rate: Audio sample rate (default 16000 for Whisper)
            channels: Number of audio channels (default 1 for mono)
            device: Audio device ID (None for default)
        """
        self.stt = stt
        self.on_transcription = on_transcription
        self.sample_rate = sample_rate
        self.channels = channels
        self.device = device

        # Audio processing parameters
        self.silence_threshold = 0.01
        self.min_speech_duration = 0.5  # Minimum seconds of speech
        self.max_speech_duration = 10.0  # Maximum seconds before forcing transcription (reduced for lower latency)
        self.silence_duration = 1.0  # Seconds of silence to trigger processing (reduced for quicker response)

        # State management
        self.is_running = False
        self.stream: Optional[sd.InputStream] = None
        self.audio_queue = asyncio.Queue()
        self.processing_task: Optional[asyncio.Task] = None

        # Audio buffer management
        self.current_chunk = []
        self.chunk_start_time = None
        self.last_speech_time = 0
        self.is_speech_detected = False

    def audio_callback(self, indata, frames, time_info, status):
        """Callback for audio stream."""
        if status:
            logger.warning(f"Audio stream status: {status}")

        if not self.is_running:
            return

        # Convert to mono if needed
        audio_data = indata[:, 0] if len(indata.shape) > 1 else indata.flatten()

        # Calculate volume (RMS)
        volume = np.sqrt(np.mean(audio_data ** 2))

        current_time = time.time()

        # Speech detection logic
        if volume > self.silence_threshold:
            # Speech detected
            if not self.is_speech_detected:
                # Start of new speech segment
                self.is_speech_detected = True
                self.chunk_start_time = current_time
                self.current_chunk = []
                logger.debug("Speech started")

            self.last_speech_time = current_time
            self.current_chunk.extend(audio_data)

            # Check if we've exceeded max duration
            if (self.chunk_start_time and
                current_time - self.chunk_start_time > self.max_speech_duration):
                self._queue_audio_chunk()
                # Reset for next chunk
                self.current_chunk = []
                self.chunk_start_time = current_time
                logger.debug("Max duration reached, starting new chunk")

        else:
            # Silence detected
            if self.is_speech_detected:
                # Check if enough silence has passed
                silence_time = current_time - self.last_speech_time

                if silence_time > self.silence_duration:
                    # End of speech segment
                    speech_duration = current_time - self.chunk_start_time

                    if speech_duration >= self.min_speech_duration:
                        self._queue_audio_chunk()
                    else:
                        logger.debug(f"Ignoring short speech ({speech_duration:.1f}s)")

                    self.is_speech_detected = False
                    self.current_chunk = []
                else:
                    # Still in speech, just a pause
                    self.current_chunk.extend(audio_data)

    def _queue_audio_chunk(self):
        """Queue an audio chunk for processing."""
        if not self.current_chunk:
            return

        try:
            audio_array = np.array(self.current_chunk, dtype=np.float32)

            # Normalize audio
            max_val = np.max(np.abs(audio_array))
            if max_val > 0:
                audio_array = audio_array / max_val

            # Put in queue (non-blocking)
            self.audio_queue.put_nowait(audio_array)
            logger.debug(f"Queued audio chunk ({len(audio_array) / self.sample_rate:.1f}s)")

        except asyncio.QueueFull:
            logger.warning("Audio queue full, dropping chunk")
        except Exception as e:
            logger.error(f"Error queuing audio chunk: {e}")

    async def _process_audio_queue(self):
        """Process queued audio chunks."""
        while self.is_running:
            try:
                # Wait for audio chunk
                audio_chunk = await asyncio.wait_for(
                    self.audio_queue.get(),
                    timeout=1.0
                )

                # Transcribe the audio
                await self._transcribe_audio(audio_chunk)

            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error processing audio queue: {e}")
                await asyncio.sleep(0.1)

    async def _transcribe_audio(self, audio_array: np.ndarray):
        """Transcribe an audio chunk."""
        try:
            # Convert to WAV format for STT
            wav_buffer = io.BytesIO()
            with wave.open(wav_buffer, 'wb') as wav_file:
                wav_file.setnchannels(self.channels)
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(self.sample_rate)

                # Convert float32 to int16
                audio_int16 = (audio_array * 32767).astype(np.int16)
                wav_file.writeframes(audio_int16.tobytes())

            # Get WAV data
            wav_data = wav_buffer.getvalue()

            # Transcribe using STT service
            logger.debug("Sending to STT...")
            transcription = await self.stt.transcribe(wav_data)

            if transcription and transcription.strip():
                logger.info(f"Transcribed: {transcription}")
                await self.on_transcription(transcription)

        except Exception as e:
            logger.error(f"Error transcribing audio: {e}")

    async def start(self):
        """Start audio capture and processing."""
        if self.is_running:
            logger.warning("Audio processor already running")
            return

        try:
            # Get device info
            if self.device is not None:
                device_info = sd.query_devices(self.device)
                logger.info(f"Using audio device: {device_info['name']}")
            else:
                logger.info("Using default audio device")

            # Start processing task
            self.is_running = True
            self.processing_task = asyncio.create_task(self._process_audio_queue())

            # Start audio stream
            self.stream = sd.InputStream(
                callback=self.audio_callback,
                channels=self.channels,
                samplerate=self.sample_rate,
                device=self.device,
                blocksize=int(self.sample_rate * 0.1),  # 100ms blocks
                dtype='float32'
            )
            self.stream.start()

            logger.info(f"Audio capture started (rate={self.sample_rate}Hz, channels={self.channels})")

        except Exception as e:
            logger.error(f"Failed to start audio capture: {e}")
            self.is_running = False
            raise

    async def stop(self):
        """Stop audio capture and processing."""
        logger.info("Stopping audio processor...")
        self.is_running = False

        # Stop audio stream
        if self.stream:
            try:
                self.stream.stop()
                self.stream.close()
            except Exception as e:
                logger.error(f"Error stopping audio stream: {e}")
            self.stream = None

        # Cancel processing task
        if self.processing_task:
            self.processing_task.cancel()
            try:
                await self.processing_task
            except asyncio.CancelledError:
                pass

        # Clear queue
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except asyncio.QueueEmpty:
                break

        logger.info("Audio processor stopped")

    @staticmethod
    def list_audio_devices():
        """List available audio devices."""
        devices = sd.query_devices()
        logger.info("Available audio devices:")
        for i, device in enumerate(devices):
            logger.info(f"  [{i}] {device['name']} - {device['channels']} channels")
        return devices
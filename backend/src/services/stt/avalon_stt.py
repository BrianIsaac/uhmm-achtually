"""AquaVoice Avalon STT service.

OpenAI-compatible API optimized for developer speech with 97.3% accuracy
on technical terms, AI model names, and code-related content.

Features:
- Trained on CLI sessions and IDE captures
- Beats Whisper Large v3, ElevenLabs Scribe, AssemblyAI on technical benchmarks
- Free until October 30, 2025
- $0.39/hour after free period (billed per second)
"""

from typing import Optional

from pipecat.services.whisper.base_stt import BaseWhisperSTTService, Transcription
from pipecat.transcriptions.language import Language


class AvalonSTT(BaseWhisperSTTService):
    """AquaVoice Avalon STT service.

    OpenAI-compatible Whisper API wrapper for developer-optimized transcription.
    Inherits from BaseWhisperSTTService for seamless Pipecat integration.
    """

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "avalon-1",
        language: Optional[Language] = Language.EN,
        prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        **kwargs,
    ):
        """Initialize Avalon STT service.

        Args:
            api_key: AquaVoice Avalon API key
            model: Model to use (default: "avalon-1")
            language: Language for transcription (default: English)
            prompt: Optional prompt to guide transcription style
            temperature: Optional temperature for sampling (0.0-1.0)
            **kwargs: Additional arguments passed to BaseWhisperSTTService
        """
        super().__init__(
            model=model,
            api_key=api_key,
            base_url="https://api.aqua.sh/v1",
            language=language,
            prompt=prompt,
            temperature=temperature,
            **kwargs,
        )

    async def _transcribe(self, audio: bytes) -> Transcription:
        """Transcribe audio data to text using AquaVoice Avalon API.

        Args:
            audio: Raw audio data in WAV format.

        Returns:
            Transcription: Object containing the transcribed text.
        """
        # Build transcription parameters
        kwargs = {
            "file": ("audio.wav", audio, "audio/wav"),
            "model": self.model_name,
            "response_format": "json",
            "language": self._language,
        }

        # Add optional parameters if provided
        if self._prompt is not None:
            kwargs["prompt"] = self._prompt

        if self._temperature is not None:
            kwargs["temperature"] = self._temperature

        # Call AquaVoice Avalon API (OpenAI-compatible)
        return await self._client.audio.transcriptions.create(**kwargs)


__all__ = ["AvalonSTT"]

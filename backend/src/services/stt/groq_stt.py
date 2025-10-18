"""Groq STT service using Whisper models.

Wrapper for Groq's Whisper Large v3 Turbo for speech-to-text transcription.
"""

from pipecat.services.groq.stt import GroqSTTService

# For now, we'll just re-export the Pipecat Groq service
# This allows us to potentially add custom logic later if needed
GroqSTT = GroqSTTService

__all__ = ["GroqSTT"]

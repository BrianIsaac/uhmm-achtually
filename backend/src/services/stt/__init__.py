"""Speech-to-Text service providers.

Supported providers:
- Groq (Whisper Large v3 Turbo) - General purpose, fast
- Avalon (AquaVoice) - Developer-optimized, 97.3% accuracy on technical terms
"""

from .groq_stt import GroqSTT
from .avalon_stt import AvalonSTT

__all__ = ["GroqSTT", "AvalonSTT"]

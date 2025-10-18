"""Simple fact-checking bot for Zoom meetings via Meeting BaaS.

This bot:
1. Joins Zoom meetings via Meeting BaaS API
2. Transcribes audio with Groq Whisper
3. Extracts claims with Groq LLM
4. Fact-checks with Exa search + Groq verification
5. Speaks verdicts via ElevenLabs TTS

No complex infrastructure - just the essentials.
"""

import asyncio
import os
import sys
import argparse
from pathlib import Path

# Add backend to Python path for processors
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from dotenv import load_dotenv
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineTask
from pipecat.frames.frames import TextFrame
from pipecat.services.groq.stt import GroqSTTService
from pipecat.services.elevenlabs.tts import ElevenLabsTTSService

# Import our existing fact-checking processors
from src.processors.sentence_aggregator import SentenceAggregator
from src.processors.claim_extractor import ClaimExtractor
from src.processors.web_fact_checker import WebFactChecker

# Load environment variables
load_dotenv()


class VerdictSpeaker:
    """Converts VerdictFrames to speech text for TTS."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose

    async def process_frame(self, frame, direction):
        """Convert verdict to speech text."""
        from src.frames.verdict_frame import VerdictFrame

        if isinstance(frame, VerdictFrame):
            # Format verdict for speech
            if frame.status == "supported":
                speech = f"Fact check: The claim {frame.claim} is supported."
            elif frame.status == "contradicted":
                speech = f"Fact check: The claim {frame.claim} is contradicted."
            elif frame.status == "unclear":
                speech = f"Fact check: The claim {frame.claim} is unclear."
            else:  # not_found
                speech = f"Fact check: No evidence found for {frame.claim}."

            if self.verbose and frame.rationale:
                speech += f" {frame.rationale}"

            # Push as TextFrame for TTS
            yield TextFrame(text=speech)


async def main():
    """Run the fact-checking bot."""
    parser = argparse.ArgumentParser(description="Fact-checking bot for Zoom meetings")
    parser.add_argument("--meeting-url", required=True, help="Zoom meeting URL")
    parser.add_argument("--verbose", action="store_true", help="Include rationale in verdicts")
    args = parser.parse_args()

    # Validate API keys
    required_keys = {
        "MEETING_BAAS_API_KEY": os.getenv("MEETING_BAAS_API_KEY"),
        "GROQ_API_KEY": os.getenv("GROQ_API_KEY"),
        "EXA_API_KEY": os.getenv("EXA_API_KEY"),
        "ELEVENLABS_API_KEY": os.getenv("ELEVENLABS_API_KEY"),
    }

    missing = [k for k, v in required_keys.items() if not v]
    if missing:
        print(f"Error: Missing API keys: {', '.join(missing)}")
        print("Please set them in your .env file")
        sys.exit(1)

    print(f"Starting fact-checking bot for meeting: {args.meeting_url}")

    # TODO: Create Meeting BaaS bot and establish WebSocket connection
    # For now, this is a template showing the pipeline structure

    print("Note: Full Meeting BaaS integration requires WebSocket transport implementation")
    print("This script shows the pipeline architecture you'll need")


if __name__ == "__main__":
    asyncio.run(main())

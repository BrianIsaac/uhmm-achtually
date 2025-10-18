#!/usr/bin/env python3
"""Test script to verify SentenceAggregator -> ClaimExtractor pipeline."""

import asyncio
from pipecat.frames.frames import TranscriptionFrame, TextFrame
from pipecat.processors.frame_processor import FrameDirection
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.task import PipelineTask
from pipecat.pipeline.runner import PipelineRunner

from src.processors.sentence_aggregator import SentenceAggregator
from src.processors.claim_extractor import ClaimExtractor
from src.utils.config import get_settings

async def main():
    """Test the pipeline."""
    print("🧪 Testing SentenceAggregator -> ClaimExtractor pipeline\n")

    settings = get_settings()

    # Create processors
    aggregator = SentenceAggregator()
    claim_extractor = ClaimExtractor(groq_api_key=settings.groq_api_key)

    # Create pipeline
    pipeline = Pipeline([
        aggregator,
        claim_extractor
    ])

    # Create task
    task = PipelineTask(pipeline)

    # Queue test frame
    test_sentence = "Python 3.12 removed the distutils package."
    print(f"📝 Queuing test sentence: {test_sentence}\n")

    await task.queue_frames([
        TranscriptionFrame(text=test_sentence)
    ])

    # Run for a few seconds
    print("▶️  Running pipeline...\n")
    runner = PipelineRunner()

    # Run with timeout
    try:
        await asyncio.wait_for(runner.run(task), timeout=10.0)
    except asyncio.TimeoutError:
        print("\n⏱️  Test completed (timeout reached)")

    print("\n✅ Test finished")

if __name__ == "__main__":
    asyncio.run(main())

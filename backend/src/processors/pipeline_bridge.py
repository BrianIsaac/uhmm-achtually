"""Bridge between Pipecat frames and the new pipeline."""

import asyncio
from typing import Optional

from loguru import logger
from pipecat.frames.frames import Frame, TextFrame
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor

from src.processors.pipeline_coordinator import FactCheckPipeline


class PipelineBridge(FrameProcessor):
    """Bridge between Pipecat's frame system and the new async pipeline.

    This processor receives TextFrames from SentenceAggregator and
    processes them through the new FactCheckPipeline asynchronously.
    """

    def __init__(
        self,
        groq_api_key: str,
        exa_api_key: str,
        daily_transport,
        allowed_domains: Optional[list] = None,
    ):
        """Initialize the bridge with the new pipeline.

        Args:
            groq_api_key: Groq API key
            exa_api_key: Exa API key
            daily_transport: DailyTransport for broadcasting
            allowed_domains: Allowed domains for search
        """
        super().__init__()

        # Initialize the new pipeline
        self.pipeline = FactCheckPipeline(
            groq_api_key=groq_api_key,
            exa_api_key=exa_api_key,
            daily_transport=daily_transport,
            allowed_domains=allowed_domains,
        )

        # Background task for processing
        self._processing_queue = asyncio.Queue()
        self._processor_task: Optional[asyncio.Task] = None

        logger.info("PipelineBridge initialized with new FactCheckPipeline")

    async def start_processing(self):
        """Start the background processing task."""
        if self._processor_task is None or self._processor_task.done():
            self._processor_task = asyncio.create_task(self._process_queue())
            logger.info("Background processing task started")

    async def stop_processing(self):
        """Stop the background processing task."""
        if self._processor_task and not self._processor_task.done():
            # Put a sentinel value to stop the processor
            await self._processing_queue.put(None)
            await self._processor_task
            self._processor_task = None
            logger.info("Background processing task stopped")

    async def _process_queue(self):
        """Process sentences from the queue in the background."""
        logger.info("Queue processor started")

        while True:
            try:
                # Get next sentence from queue
                sentence = await self._processing_queue.get()

                # Check for stop sentinel
                if sentence is None:
                    logger.info("Queue processor received stop signal")
                    break

                # Process through new pipeline
                logger.info(f"Processing queued sentence: {sentence}")
                await self.pipeline.process_sentence(sentence)

            except Exception as e:
                logger.error(f"Error processing queued sentence: {e}", exc_info=True)

        logger.info("Queue processor stopped")

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        """Process incoming frames from Pipecat.

        Args:
            frame: Incoming frame
            direction: Frame direction (upstream/downstream)
        """
        # Log all frames for debugging (use info level to ensure visibility)
        logger.info(f"PipelineBridge received frame: {type(frame).__name__}")

        # Start processing if not already started
        await self.start_processing()

        # Handle TextFrame from SentenceAggregator
        if isinstance(frame, TextFrame):
            sentence = frame.text
            logger.info(f"Bridge received sentence: {sentence}")

            # Queue the sentence for processing
            await self._processing_queue.put(sentence)
            logger.info(f"Sentence queued for processing (queue size: {self._processing_queue.qsize()})")

            # Don't forward TextFrame - it's been consumed
            return

        # Forward all other frames unchanged
        await super().process_frame(frame, direction)

    async def cleanup(self):
        """Clean up resources."""
        await self.stop_processing()
        logger.info("PipelineBridge cleanup complete")

    def get_metrics(self) -> dict:
        """Get bridge and pipeline metrics.

        Returns:
            Dictionary of metrics
        """
        metrics = self.pipeline.get_metrics()
        metrics["queue_size"] = self._processing_queue.qsize()
        metrics["processor_running"] = (
            self._processor_task is not None and not self._processor_task.done()
        )
        return metrics
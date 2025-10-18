"""Service for aggregating text into chunks."""

import time
from typing import List, Optional
from loguru import logger


class SentenceAggregator:
    """
    Aggregates text fragments into chunks based on time.

    This service buffers incoming text for a fixed duration (3 seconds)
    before processing it as a complete chunk.
    """

    def __init__(self, buffer_duration: float = 3.0):
        """Initialize the sentence aggregator.

        Args:
            buffer_duration: Duration in seconds to buffer text before processing (default 3.0)
        """
        self._buffer = ""
        self._buffer_start_time: Optional[float] = None
        self._buffer_duration = buffer_duration

    def add_text(self, text: str) -> List[str]:
        """
        Add text to the buffer and extract complete chunks based on time.

        Args:
            text: Text to add to the buffer

        Returns:
            List of complete text chunks (usually 0 or 1)
        """
        if not text:
            return []

        current_time = time.time()

        # Start buffer timer if this is the first text
        if self._buffer_start_time is None:
            self._buffer_start_time = current_time

        # Add text to buffer with proper spacing
        if self._buffer and not self._buffer.endswith(' '):
            self._buffer += ' '
        self._buffer += text.strip()

        # Check if buffer duration has been exceeded
        chunks = []
        if current_time - self._buffer_start_time >= self._buffer_duration:
            if self._buffer:
                chunks.append(self._buffer)
                logger.debug(f"Extracted chunk after {self._buffer_duration}s: {self._buffer[:50]}...")
                self._buffer = ""
                self._buffer_start_time = None

        return chunks

    def get_pending_text(self) -> str:
        """
        Get any pending text in the buffer that hasn't been processed yet.

        Returns:
            Pending text in the buffer
        """
        return self._buffer

    def clear(self) -> None:
        """Clear the buffer and reset timer."""
        self._buffer = ""
        self._buffer_start_time = None

    def force_flush(self) -> List[str]:
        """
        Force flush the buffer, treating any remaining text as a complete chunk.

        Returns:
            List containing the buffer content if not empty
        """
        if not self._buffer:
            return []

        chunk = self._buffer.strip()
        self._buffer = ""
        self._buffer_start_time = None

        if chunk:
            logger.debug(f"Force flushed chunk: {chunk[:50]}...")
            return [chunk]

        return []
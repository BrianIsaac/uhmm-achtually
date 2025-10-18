"""Service for aggregating text into complete sentences."""

import re
from typing import List
from loguru import logger


class SentenceAggregator:
    """
    Aggregates text fragments into complete sentences.

    This service buffers incoming text and identifies complete sentences
    based on punctuation patterns.
    """

    def __init__(self):
        """Initialize the sentence aggregator."""
        self._buffer = ""
        # Improved pattern that avoids splitting on decimal points
        # Matches: period not preceded by digit and followed by space, or ! or ?
        # This prevents splitting on decimal numbers like 3.16
        self._sentence_pattern = re.compile(r'(?<![0-9])\.(?=\s)|[!?](?=\s|$)')

    def add_text(self, text: str) -> List[str]:
        """
        Add text to the buffer and extract complete sentences.

        Args:
            text: Text to add to the buffer

        Returns:
            List of complete sentences found
        """
        if not text:
            return []

        # Add text to buffer with proper spacing
        if self._buffer and not self._buffer.endswith(' '):
            self._buffer += ' '
        self._buffer += text.strip()

        # Extract complete sentences
        sentences = self._extract_sentences()

        if sentences:
            logger.debug(f"Extracted {len(sentences)} complete sentence(s)")

        return sentences

    def _extract_sentences(self) -> List[str]:
        """
        Extract complete sentences from the buffer.

        Returns:
            List of complete sentences
        """
        sentences = []

        # Special handling for numbers with decimal points
        # Don't split on periods that are between digits
        protected_buffer = self._buffer

        # Find sentence-ending punctuation that's not a decimal point
        # Split on: '. ' (period + space), '! ', '? ', or these at end of string
        parts = re.split(r'(?<=[.!?])\s+', protected_buffer)

        if len(parts) == 1:
            # No complete sentence found yet
            return sentences

        # All parts except the last are complete sentences
        for i, part in enumerate(parts[:-1]):
            # Don't treat decimal numbers as sentence endings
            # Check if this looks like a complete sentence
            if part and not re.match(r'^\d+$', part.rstrip('.')):
                sentences.append(part)

        # Keep the last part in the buffer (incomplete sentence)
        self._buffer = parts[-1] if parts[-1] else ""

        return sentences

    def get_pending_text(self) -> str:
        """
        Get any pending text in the buffer that hasn't formed a complete sentence.

        Returns:
            Pending text in the buffer
        """
        return self._buffer

    def clear(self) -> None:
        """Clear the buffer."""
        self._buffer = ""

    def force_flush(self) -> List[str]:
        """
        Force flush the buffer, treating any remaining text as a complete sentence.

        Returns:
            List containing the buffer content if not empty
        """
        if not self._buffer:
            return []

        sentence = self._buffer.strip()
        self._buffer = ""

        if sentence:
            logger.debug(f"Force flushed incomplete sentence: {sentence}")
            return [sentence]

        return []
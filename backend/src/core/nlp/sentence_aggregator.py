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
        self._sentence_pattern = re.compile(r'[.!?]\s*')

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

        # Find all sentence boundaries
        matches = list(self._sentence_pattern.finditer(self._buffer))

        if not matches:
            return sentences

        # Extract complete sentences
        last_end = 0
        for match in matches:
            sentence = self._buffer[last_end:match.end()].strip()
            if sentence:
                sentences.append(sentence)
            last_end = match.end()

        # Update buffer with remaining text
        if last_end < len(self._buffer):
            self._buffer = self._buffer[last_end:].strip()
        else:
            self._buffer = ""

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
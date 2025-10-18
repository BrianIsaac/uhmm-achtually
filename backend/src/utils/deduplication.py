"""Deduplication utilities for transcriptions and claims."""

import hashlib
import time
from typing import Optional, Dict, Set
from loguru import logger


class TranscriptionDeduplicator:
    """Deduplicate transcriptions to avoid processing the same audio multiple times."""

    def __init__(self, ttl_seconds: float = 30.0):
        """
        Initialize the deduplicator.

        Args:
            ttl_seconds: Time to live for cached transcriptions
        """
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, float] = {}  # hash -> timestamp
        self._last_cleanup = time.time()
        self._cleanup_interval = 60.0  # Clean up every minute

    def _hash_text(self, text: str) -> str:
        """Create a hash of the text for comparison."""
        # Normalize text: lowercase, strip whitespace
        normalized = text.lower().strip()
        # Remove punctuation variations for better matching
        normalized = normalized.replace(".", "").replace(",", "").replace("!", "").replace("?", "")
        return hashlib.md5(normalized.encode()).hexdigest()

    def _cleanup_cache(self) -> None:
        """Remove expired entries from cache."""
        current_time = time.time()
        if current_time - self._last_cleanup < self._cleanup_interval:
            return

        expired_keys = [
            key for key, timestamp in self._cache.items()
            if current_time - timestamp > self.ttl_seconds
        ]

        for key in expired_keys:
            del self._cache[key]

        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired transcription hashes")

        self._last_cleanup = current_time

    def is_duplicate(self, text: str) -> bool:
        """
        Check if this transcription is a duplicate.

        Args:
            text: The transcription text

        Returns:
            True if this is a duplicate (recently seen), False otherwise
        """
        # Clean up old entries periodically
        self._cleanup_cache()

        text_hash = self._hash_text(text)
        current_time = time.time()

        if text_hash in self._cache:
            age = current_time - self._cache[text_hash]
            if age < self.ttl_seconds:
                logger.debug(f"Duplicate transcription detected (age: {age:.1f}s)")
                # Update timestamp to extend TTL
                self._cache[text_hash] = current_time
                return True

        # Not a duplicate, add to cache
        self._cache[text_hash] = current_time
        return False

    def clear(self) -> None:
        """Clear all cached transcriptions."""
        self._cache.clear()
        logger.debug("Transcription cache cleared")


class ClaimDeduplicator:
    """Deduplicate claims to avoid redundant fact-checking."""

    def __init__(self, ttl_seconds: float = 300.0):
        """
        Initialize the claim deduplicator.

        Args:
            ttl_seconds: Time to live for cached claims (5 minutes default)
        """
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, tuple[float, any]] = {}  # hash -> (timestamp, result)
        self._last_cleanup = time.time()
        self._cleanup_interval = 60.0

    def _hash_claim(self, claim_text: str) -> str:
        """Create a hash of the claim for comparison."""
        # Normalize: lowercase, strip, remove punctuation
        normalized = claim_text.lower().strip()
        normalized = ''.join(c for c in normalized if c.isalnum() or c.isspace())
        normalized = ' '.join(normalized.split())  # Normalize whitespace
        return hashlib.md5(normalized.encode()).hexdigest()

    def _cleanup_cache(self) -> None:
        """Remove expired entries from cache."""
        current_time = time.time()
        if current_time - self._last_cleanup < self._cleanup_interval:
            return

        expired_keys = [
            key for key, (timestamp, _) in self._cache.items()
            if current_time - timestamp > self.ttl_seconds
        ]

        for key in expired_keys:
            del self._cache[key]

        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired claim hashes")

        self._last_cleanup = current_time

    def get_cached_result(self, claim_text: str) -> Optional[any]:
        """
        Get cached verification result if available.

        Args:
            claim_text: The claim text

        Returns:
            Cached verification result or None if not found/expired
        """
        self._cleanup_cache()

        claim_hash = self._hash_claim(claim_text)

        if claim_hash in self._cache:
            timestamp, result = self._cache[claim_hash]
            age = time.time() - timestamp

            if age < self.ttl_seconds:
                logger.debug(f"Using cached verification for claim (age: {age:.1f}s)")
                return result

        return None

    def cache_result(self, claim_text: str, result: any) -> None:
        """
        Cache a verification result.

        Args:
            claim_text: The claim text
            result: The verification result to cache
        """
        claim_hash = self._hash_claim(claim_text)
        self._cache[claim_hash] = (time.time(), result)
        logger.debug(f"Cached verification result for claim")

    def clear(self) -> None:
        """Clear all cached claims."""
        self._cache.clear()
        logger.debug("Claim cache cleared")
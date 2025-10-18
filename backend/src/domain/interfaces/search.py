"""Search interface for evidence gathering."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


class ISearchService(ABC):
    """Interface for search services."""

    @abstractmethod
    async def search(
        self,
        query: str,
        max_results: int = 10,
        domains: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for information.

        Args:
            query: Search query
            max_results: Maximum number of results
            domains: Optional list of domains to search

        Returns:
            List of search results

        Raises:
            EvidenceSearchError: If search fails
        """
        pass

    @abstractmethod
    async def get_content(self, url: str) -> str:
        """
        Get content from a URL.

        Args:
            url: URL to fetch content from

        Returns:
            Page content

        Raises:
            EvidenceSearchError: If content fetching fails
        """
        pass
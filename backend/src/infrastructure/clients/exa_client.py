"""Exa API client wrapper for web search.

Provides a simple interface for searching the web using Exa neural search.
"""

import asyncio
from exa_py import Exa


class ExaClient:
    """Wrapper for Exa neural search API.

    Handles web search with domain filtering and autoprompt optimisation.
    """

    def __init__(self, api_key: str, allowed_domains: list[str]):
        """Initialise Exa client.

        Args:
            api_key: Exa API key
            allowed_domains: List of allowed domains to search
        """
        self.exa = Exa(api_key=api_key)
        self.allowed_domains = allowed_domains

    async def search_for_claim(
        self,
        claim: str,
        num_results: int = 5
    ) -> list:
        """Search for evidence related to a claim.

        Args:
            claim: Factual claim to verify
            num_results: Number of results to return (default: 5)

        Returns:
            List of search results with title, url, text attributes
        """
        try:
            # Use asyncio.to_thread to avoid blocking the event loop
            response = await asyncio.to_thread(
                self.exa.search_and_contents,
                claim,
                type="keyword",  # Use keyword search for speed (< 0.5s)
                use_autoprompt=False,  # Disabled for speed
                num_results=min(num_results, 3),  # Limit to 3 for faster response
                include_domains=self.allowed_domains,
                text={"max_characters": 1000}  # Reduced for faster response
            )

            # Check if response has results
            if hasattr(response, 'results'):
                return response.results
            else:
                # Log the actual response for debugging
                print(f"Unexpected Exa response: {response}")
                return []

        except Exception as e:
            print(f"Exa search error: {e}")
            # Return empty list on error to allow graceful fallback
            return []

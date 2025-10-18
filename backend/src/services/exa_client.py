"""Exa API client wrapper for web search.

Provides a simple interface for searching the web using Exa neural search.
"""

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
        num_results: int = 2
    ) -> list:
        """Search for evidence related to a claim.

        Args:
            claim: Factual claim to verify
            num_results: Number of results to return (default: 2)

        Returns:
            List of search results with title, url, text attributes
        """
        response = self.exa.search_and_contents(
            claim,
            use_autoprompt=True,
            num_results=num_results,
            include_domains=self.allowed_domains,
            text={"max_characters": 2000}
        )
        return response.results

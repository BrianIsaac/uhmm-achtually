# Component: Exa Web Search (Phase 1)

## Owner Assignment
**Developer B: Claim Processing (Stages 4-5)**
Part of WebFactChecker implementation (Stage 5)

## Time Estimate: 1.5 hours (included in Stage 5)
- Exa API setup: 20 min
- search_and_contents implementation: 40 min
- Caching logic: 30 min

## Dependencies
```toml
[project.dependencies]
exa-py = ">=1.0.0"                # Exa neural search
python-dotenv = ">=1.0.0"         # Environment variables
```

## Architecture Overview

**Exa within Stage 5 (WebFactChecker):**
```
ClaimFrame (from Stage 4)
    ↓
WebFactChecker:
  ├─ Exa.search_and_contents()  ← THIS COMPONENT
  │  (300-600ms)
  ├─ Groq LLM verification
  │  (50-150ms)
  └─ VerdictFrame emission
    ↓
FactCheckMessenger (Stage 6)
```

## Why Exa for Phase 1?

### Compared to BM25 (Phase 2)
- **No setup required:** Cloud API, no local indexing
- **Neural search:** AI-optimised queries, better than keyword matching
- **Auto-prompt:** Exa enhances queries automatically
- **Fresh results:** Always up-to-date, no stale data
- **Domain filtering:** Built-in allow-list support

### Exa Features for Fact-Checking
- `search_and_contents()`: Search + content extraction in one call
- `use_autoprompt=True`: AI-enhanced query optimisation
- `include_domains`: Filter to trusted documentation sites
- `start_published_date`: Prioritise recent sources
- `text.max_characters`: Control passage length

## Input/Output Contract

### Input (from ClaimExtractor)
```python
ClaimFrame
- text: str  # "Python 3.12 removed distutils"
- claim_type: str  # "version"
```

### Output (to Groq LLM verification)
```python
SearchResults (list of passages)
[
  {
    "title": "PEP 632 - Deprecate distutils",
    "url": "https://peps.python.org/pep-0632/",
    "text": "Python 3.12 removes the distutils package..."
  },
  ...
]
```

## Implementation Guide

### Step 1: Exa API Setup (20 min)

**Create Exa account:**
```bash
# Sign up at https://dashboard.exa.ai
# Navigate to API Keys section
# Copy your API key
```

**Add API key to .env:**
```bash
# Add to .env file
EXA_API_KEY=your_exa_api_key_here
```

**Verify installation:**
```python
from exa_py import Exa

exa = Exa(api_key="your_key")
results = exa.search("test query", num_results=1)
print("✓ Exa API configured successfully")
```

### Step 2: Exa Client Wrapper (40 min)

Create `src/services/exa_client.py`:

```python
"""Exa neural search client for web fact-checking."""

import os
import logging
from typing import List, Optional
from exa_py import Exa
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Search result from Exa.

    Attributes:
        title: Page title
        url: Page URL
        text: Extracted text content
        published_date: Publication date (if available)
    """
    title: str
    url: str
    text: str
    published_date: Optional[str] = None


class ExaSearchClient:
    """Exa neural search client for fact-checking.

    Phase 1: Web search only.
    Phase 2: Add BM25 fallback for internal knowledge.
    """

    def __init__(
        self,
        api_key: str | None = None,
        allowed_domains: List[str] | None = None,
        default_num_results: int = 2,
        default_max_characters: int = 2000
    ):
        """Initialise Exa search client.

        Args:
            api_key: Exa API key (defaults to EXA_API_KEY env var)
            allowed_domains: List of allowed domains for search
            default_num_results: Default number of results to return
            default_max_characters: Default max characters per result

        Raises:
            ValueError: If API key not found
        """
        self.api_key = api_key or os.getenv("EXA_API_KEY")
        if not self.api_key:
            raise ValueError("EXA_API_KEY not found. Set via parameter or environment variable.")

        self.exa = Exa(api_key=self.api_key)

        # Configuration
        self.allowed_domains = allowed_domains or [
            "docs.python.org",
            "peps.python.org",
            "kubernetes.io",
            "owasp.org",
            "www.nist.gov",
            "postgresql.org",
            "docs.djangoproject.com",
            "reactjs.org",
            "golang.org"
        ]
        self.default_num_results = default_num_results
        self.default_max_characters = default_max_characters

        logger.info(f"ExaSearchClient initialised with {len(self.allowed_domains)} allowed domains")

    def search_for_claim(
        self,
        claim: str,
        num_results: int | None = None,
        max_characters: int | None = None,
        use_autoprompt: bool = True,
        start_published_date: str | None = None
    ) -> List[SearchResult]:
        """Search for claim using Exa neural search.

        Args:
            claim: Claim text to search for
            num_results: Number of results (defaults to default_num_results)
            max_characters: Max characters per result (defaults to default_max_characters)
            use_autoprompt: Enable Exa's AI query enhancement
            start_published_date: Filter results after this date (ISO format: "2024-01-01")

        Returns:
            List of SearchResult objects

        Raises:
            Exception: If Exa API call fails
        """
        num_results = num_results or self.default_num_results
        max_characters = max_characters or self.default_max_characters

        logger.info(f"Searching Exa for claim: {claim[:100]}...")

        try:
            # Call Exa search_and_contents
            response = self.exa.search_and_contents(
                claim,
                use_autoprompt=use_autoprompt,
                num_results=num_results,
                include_domains=self.allowed_domains,
                text={"max_characters": max_characters},
                start_published_date=start_published_date
            )

            # Convert to SearchResult objects
            results = []
            for result in response.results:
                search_result = SearchResult(
                    title=result.title,
                    url=result.url,
                    text=result.text if hasattr(result, 'text') else "",
                    published_date=result.published_date if hasattr(result, 'published_date') else None
                )
                results.append(search_result)

            logger.info(f"Found {len(results)} results from Exa")
            return results

        except Exception as e:
            logger.error(f"Exa search failed: {e}")
            raise

    def search_with_date_priority(
        self,
        claim: str,
        prioritise_recent: bool = True
    ) -> List[SearchResult]:
        """Search with recency prioritisation for version/date-sensitive claims.

        Args:
            claim: Claim text to search for
            prioritise_recent: Whether to prioritise recent results

        Returns:
            List of SearchResult objects
        """
        if prioritise_recent:
            # Search only last 2 years for recent info
            from datetime import datetime, timedelta
            two_years_ago = (datetime.now() - timedelta(days=730)).strftime("%Y-%m-%d")

            return self.search_for_claim(
                claim,
                start_published_date=two_years_ago
            )
        else:
            return self.search_for_claim(claim)


# Usage example
if __name__ == "__main__":
    # Test Exa search
    client = ExaSearchClient()

    test_claims = [
        "Python 3.12 removed distutils",
        "GDPR requires breach notification within 72 hours",
        "Kubernetes uses iptables by default"
    ]

    for claim in test_claims:
        print(f"\nClaim: {claim}")
        results = client.search_for_claim(claim)

        for i, result in enumerate(results, 1):
            print(f"\n  Result {i}:")
            print(f"  Title: {result.title}")
            print(f"  URL: {result.url}")
            print(f"  Text: {result.text[:200]}...")
```

### Step 3: Caching Layer (30 min)

Create `src/utils/search_cache.py`:

```python
"""In-memory search cache for Phase 1 (session-scoped).

Phase 2: Replace with Supabase persistent cache.
"""

import hashlib
import logging
from typing import Dict, Optional, List
from dataclasses import dataclass, asdict
import json

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Cached search result entry.

    Attributes:
        query: Original search query
        results: Search results (list of dicts)
        timestamp: When cached
    """
    query: str
    results: List[dict]
    timestamp: float


class SearchCache:
    """In-memory cache for search results.

    Phase 1: Simple dict-based cache (cleared on restart).
    Phase 2: Migrate to Supabase for persistence.
    """

    def __init__(self):
        """Initialise empty cache."""
        self._cache: Dict[str, CacheEntry] = {}
        self.hits = 0
        self.misses = 0
        logger.info("SearchCache initialised (in-memory)")

    def _normalise_query(self, query: str) -> str:
        """Normalise query for cache key.

        Args:
            query: Raw query string

        Returns:
            Normalised query (lowercase, stripped)
        """
        return query.lower().strip()

    def _hash_query(self, query: str) -> str:
        """Generate cache key from query.

        Args:
            query: Normalised query

        Returns:
            MD5 hash of query
        """
        return hashlib.md5(query.encode()).hexdigest()

    def get(self, query: str) -> Optional[List[dict]]:
        """Get cached results for query.

        Args:
            query: Search query

        Returns:
            Cached results or None if not found
        """
        normalised = self._normalise_query(query)
        cache_key = self._hash_query(normalised)

        if cache_key in self._cache:
            self.hits += 1
            logger.debug(f"Cache HIT for query: {query[:50]}...")
            return self._cache[cache_key].results
        else:
            self.misses += 1
            logger.debug(f"Cache MISS for query: {query[:50]}...")
            return None

    def set(self, query: str, results: List[dict]) -> None:
        """Cache search results for query.

        Args:
            query: Search query
            results: Search results to cache
        """
        import time

        normalised = self._normalise_query(query)
        cache_key = self._hash_query(normalised)

        self._cache[cache_key] = CacheEntry(
            query=normalised,
            results=results,
            timestamp=time.time()
        )

        logger.debug(f"Cached results for query: {query[:50]}...")

    def clear(self) -> None:
        """Clear all cached entries."""
        count = len(self._cache)
        self._cache = {}
        self.hits = 0
        self.misses = 0
        logger.info(f"Cache cleared ({count} entries removed)")

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate.

        Returns:
            Hit rate (0.0-1.0)
        """
        total = self.hits + self.misses
        if total == 0:
            return 0.0
        return self.hits / total

    @property
    def size(self) -> int:
        """Get number of cached entries.

        Returns:
            Cache size
        """
        return len(self._cache)


# Global cache instance
_cache = SearchCache()


def get_search_cache() -> SearchCache:
    """Get global search cache instance.

    Returns:
        SearchCache instance
    """
    return _cache


# Usage example
if __name__ == "__main__":
    cache = get_search_cache()

    # Cache some results
    cache.set("python 3.12 distutils", [
        {"title": "PEP 632", "url": "https://peps.python.org/pep-0632/", "text": "..."}
    ])

    # Retrieve cached results
    results = cache.get("python 3.12 distutils")  # Hit
    results = cache.get("python 3.12 distutils")  # Hit
    results = cache.get("new query")  # Miss

    print(f"Cache size: {cache.size}")
    print(f"Hit rate: {cache.hit_rate:.2%}")
```

## Integration with WebFactChecker

In `src/processors/web_fact_checker.py`:

```python
"""WebFactChecker with Exa search integration."""

from src.services.exa_client import ExaSearchClient, SearchResult
from src.utils.search_cache import get_search_cache

class WebFactChecker(FrameProcessor):
    def __init__(self, ...):
        # Initialise Exa client
        self.exa_client = ExaSearchClient(
            api_key=exa_api_key,
            allowed_domains=allowed_domains
        )

        # Get cache instance
        self.cache = get_search_cache()

    async def process_frame(self, frame: ClaimFrame):
        claim_text = frame.text

        # Check cache first
        cached_results = self.cache.get(claim_text)
        if cached_results:
            passages = cached_results
        else:
            # Search with Exa
            search_results = self.exa_client.search_for_claim(
                claim=claim_text,
                use_autoprompt=True
            )

            # Convert to dict for caching
            passages = [
                {"title": r.title, "url": r.url, "text": r.text}
                for r in search_results
            ]

            # Cache results
            self.cache.set(claim_text, passages)

        # Continue with Groq verification...
```

## Exa API Configuration

### Search Parameters
```python
exa.search_and_contents(
    query,                          # Required: search query
    use_autoprompt=True,            # Enable AI query enhancement (recommended)
    num_results=2,                  # Number of results (2-3 optimal for fact-checking)
    include_domains=[...],          # Allow-list of trusted domains
    text={"max_characters": 2000},  # Extract up to 2000 chars per result
    start_published_date="2024-01-01"  # Optional: filter by date
)
```

### Domain Allow-List (Phase 1)
```python
ALLOWED_DOMAINS = [
    # Programming languages
    "docs.python.org",
    "peps.python.org",
    "golang.org",
    "docs.oracle.com/javase",

    # Frameworks
    "kubernetes.io",
    "reactjs.org",
    "docs.djangoproject.com",

    # Databases
    "postgresql.org",
    "docs.mongodb.com",

    # Security
    "owasp.org",
    "www.nist.gov",
    "cwe.mitre.org",

    # Standards
    "gdpr-info.eu",
    "www.w3.org",
    "datatracker.ietf.org"
]
```

### Autoprompt Enhancement

**Without autoprompt:**
```
Query: "Python 3.12 removed distutils"
→ Searches literally for this phrase
```

**With autoprompt (`use_autoprompt=True`):**
```
Query: "Python 3.12 removed distutils"
→ Exa enhances to: "Python 3.12 release notes distutils deprecation removal PEP"
→ Better, more relevant results
```

## Performance Characteristics

### Latency Targets
| Operation | Target | Typical | Notes |
|-----------|--------|---------|-------|
| Exa API call | <600ms | 400-500ms | Network + search |
| Cache lookup | <10ms | ~2ms | In-memory dict |
| Result parsing | <50ms | ~20ms | JSON parsing |
| **Total (cached)** | **<100ms** | **~50ms** | Cache hit |
| **Total (uncached)** | **<700ms** | **~500ms** | Cache miss |

### API Quotas (Exa Free Tier)
- **Monthly requests:** 1,000 (check current limits)
- **Rate limit:** ~10 requests/second
- **Result limit:** 10 results per search

### Cost Estimation (24h hackathon demo)
```
Assumptions:
- 50 claims fact-checked
- 50% cache hit rate
- 25 Exa API calls

Cost per request: ~$0.001 (check current pricing)
Total cost: 25 × $0.001 = $0.025

Demo cost: <$0.03 (essentially free)
```

## Testing Strategy

### Unit Tests
```python
"""Test Exa search client."""

import pytest
from src.services.exa_client import ExaSearchClient


def test_exa_client_initialisation():
    """Test Exa client initialises correctly."""
    client = ExaSearchClient()

    assert client.exa is not None
    assert len(client.allowed_domains) > 0


def test_exa_search_for_claim():
    """Test Exa search with real API."""
    client = ExaSearchClient()

    results = client.search_for_claim(
        "Python 3.12 removed distutils",
        num_results=2
    )

    assert len(results) > 0
    assert all(hasattr(r, 'title') for r in results)
    assert all(hasattr(r, 'url') for r in results)
    assert all(hasattr(r, 'text') for r in results)


def test_cache_functionality():
    """Test search cache hit/miss."""
    from src.utils.search_cache import get_search_cache

    cache = get_search_cache()
    cache.clear()  # Start fresh

    query = "test query"
    results = [{"title": "Test", "url": "http://example.com", "text": "..."}]

    # First lookup (miss)
    assert cache.get(query) is None

    # Cache results
    cache.set(query, results)

    # Second lookup (hit)
    cached = cache.get(query)
    assert cached == results

    # Verify metrics
    assert cache.size == 1
    assert cache.hit_rate == 0.5  # 1 hit, 1 miss
```

Run tests:
```bash
uv run pytest tests/test_exa_client.py -v
```

## Common Issues & Solutions

### Issue 1: No Results Found
```python
# Problem: Exa returns empty results for valid claims

# Solution: Expand allowed domains or disable domain filtering
client = ExaSearchClient(allowed_domains=None)  # Search all domains

# Or add more trusted domains
allowed_domains.extend([
    "github.com",
    "stackoverflow.com",  # For technical questions
    "en.wikipedia.org"    # For general knowledge
])
```

### Issue 2: Rate Limit Exceeded
```python
# Problem: Too many API calls

# Solution: Implement aggressive caching
# Cache hit rate target: >50%

# Also add rate limiting
import asyncio

async def search_with_rate_limit(claim):
    await asyncio.sleep(0.1)  # 10 requests/second max
    return exa_client.search_for_claim(claim)
```

### Issue 3: Results Too Long
```python
# Problem: Passages exceed LLM context window

# Solution: Reduce max_characters
results = exa.search_and_contents(
    claim,
    text={"max_characters": 1000}  # Reduced from 2000
)
```

### Issue 4: Irrelevant Results
```python
# Problem: Results don't match claim topic

# Solution: Enable autoprompt (if not already)
results = exa.search_and_contents(
    claim,
    use_autoprompt=True  # Let Exa enhance query
)

# Or manually enhance query
enhanced_query = f"{claim} official documentation reference"
results = exa.search_and_contents(enhanced_query)
```

## Performance Optimisation Tips

### 1. Cache Aggressively
```python
# Cache every search result
# Target hit rate: >50% during demo
```

### 2. Limit Results
```python
# 2 results usually sufficient for fact-checking
num_results=2  # Balance quality vs latency
```

### 3. Use Autoprompt
```python
# Always enable for better results
use_autoprompt=True
```

### 4. Filter by Domain
```python
# Reduces irrelevant results
include_domains=trusted_domains
```

### 5. Prioritise Recent Sources
```python
# For version-sensitive claims
start_published_date="2023-01-01"
```

## Deliverables Checklist

- [ ] `src/services/exa_client.py` - Exa search client wrapper
- [ ] `src/utils/search_cache.py` - In-memory search cache
- [ ] EXA_API_KEY configured in .env
- [ ] Allowed domains list defined
- [ ] Unit tests passing
- [ ] Integration with WebFactChecker complete
- [ ] Cache hit rate >30% during testing
- [ ] Latency within targets (<600ms uncached)

## Next Steps for Integration

1. **Integrate with WebFactChecker:**
   - Import ExaSearchClient in web_fact_checker.py
   - Replace placeholder search with real Exa calls
   - Add cache layer

2. **Test with Real Claims:**
   - Run searches for demo script claims
   - Verify result relevance
   - Check latency metrics

3. **Tune Parameters:**
   - Adjust num_results if needed
   - Refine allowed_domains list
   - Optimise max_characters

4. **Monitor API Usage:**
   - Track API call count
   - Monitor cache hit rate
   - Check quota remaining

## Resources

**Exa Documentation:**
- Python SDK: https://github.com/exa-labs/exa-py
- API Reference: https://docs.exa.ai/reference/python-sdk
- Dashboard: https://dashboard.exa.ai

**Examples:**
- Exa Researcher: https://docs.exa.ai/examples/exa-researcher-python
- LangChain integration: https://python.langchain.com/docs/integrations/tools/exa_search/

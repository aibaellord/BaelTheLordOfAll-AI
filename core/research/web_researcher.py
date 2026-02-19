"""
BAEL Web Researcher
====================

Autonomous web search and content analysis.
Gathers information from multiple sources.

Features:
- Multi-engine search
- Content extraction
- Relevance scoring
- Fact extraction
- Source tracking
"""

import asyncio
import hashlib
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set

import aiohttp

logger = logging.getLogger(__name__)


class SearchEngine(Enum):
    """Search engines."""
    GOOGLE = "google"
    DUCKDUCKGO = "duckduckgo"
    BING = "bing"
    ARXIV = "arxiv"
    GITHUB = "github"
    STACKOVERFLOW = "stackoverflow"


@dataclass
class SearchQuery:
    """A search query."""
    text: str

    # Filters
    site: Optional[str] = None
    date_range: Optional[str] = None  # "past_day", "past_week", etc.
    file_type: Optional[str] = None

    # Options
    engines: List[SearchEngine] = field(default_factory=lambda: [SearchEngine.DUCKDUCKGO])
    max_results: int = 10

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class SearchResult:
    """A search result."""
    id: str
    title: str
    url: str
    snippet: str

    # Source
    engine: SearchEngine = SearchEngine.DUCKDUCKGO

    # Ranking
    position: int = 0
    relevance_score: float = 0.0

    # Metadata
    domain: str = ""
    cached_at: Optional[datetime] = None


@dataclass
class WebContent:
    """Extracted web content."""
    url: str
    title: str

    # Content
    text: str
    html: str = ""

    # Metadata
    author: Optional[str] = None
    published_date: Optional[datetime] = None

    # Extracted data
    headings: List[str] = field(default_factory=list)
    links: List[str] = field(default_factory=list)
    images: List[str] = field(default_factory=list)
    code_blocks: List[str] = field(default_factory=list)

    # Quality
    word_count: int = 0
    reading_time_minutes: float = 0.0

    # Fetch info
    fetched_at: datetime = field(default_factory=datetime.now)
    status_code: int = 200


class WebResearcher:
    """
    Web researcher for BAEL.

    Performs autonomous web research.
    """

    # Default headers
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-US,en;q=0.9",
    }

    def __init__(self):
        # Cache
        self._content_cache: Dict[str, WebContent] = {}
        self._search_cache: Dict[str, List[SearchResult]] = {}

        # Session
        self._session: Optional[aiohttp.ClientSession] = None

        # Stats
        self.stats = {
            "searches_performed": 0,
            "pages_fetched": 0,
            "cache_hits": 0,
        }

    async def search(
        self,
        query: SearchQuery,
    ) -> List[SearchResult]:
        """
        Perform a search.

        Args:
            query: Search query

        Returns:
            Search results
        """
        cache_key = f"{query.text}:{','.join(e.value for e in query.engines)}"

        if cache_key in self._search_cache:
            self.stats["cache_hits"] += 1
            return self._search_cache[cache_key]

        all_results = []

        for engine in query.engines:
            results = await self._search_engine(query, engine)
            all_results.extend(results)

        # Deduplicate
        seen_urls = set()
        unique_results = []
        for r in all_results:
            if r.url not in seen_urls:
                seen_urls.add(r.url)
                unique_results.append(r)

        # Sort by relevance
        unique_results.sort(key=lambda r: r.relevance_score, reverse=True)

        # Limit
        unique_results = unique_results[:query.max_results]

        # Cache
        self._search_cache[cache_key] = unique_results

        self.stats["searches_performed"] += 1

        return unique_results

    async def _search_engine(
        self,
        query: SearchQuery,
        engine: SearchEngine,
    ) -> List[SearchResult]:
        """Search using a specific engine."""
        results = []

        if engine == SearchEngine.DUCKDUCKGO:
            results = await self._search_duckduckgo(query)
        elif engine == SearchEngine.ARXIV:
            results = await self._search_arxiv(query)
        elif engine == SearchEngine.GITHUB:
            results = await self._search_github(query)
        # Other engines can be added

        return results

    async def _search_duckduckgo(
        self,
        query: SearchQuery,
    ) -> List[SearchResult]:
        """Search DuckDuckGo (instant answer API)."""
        results = []

        try:
            url = "https://api.duckduckgo.com/"
            params = {
                "q": query.text,
                "format": "json",
                "no_redirect": 1,
                "no_html": 1,
            }

            async with self._get_session() as session:
                async with session.get(url, params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()

                        # Parse results
                        for i, topic in enumerate(data.get("RelatedTopics", [])[:query.max_results]):
                            if isinstance(topic, dict) and "Text" in topic:
                                result_id = hashlib.md5(
                                    topic.get("FirstURL", str(i)).encode()
                                ).hexdigest()[:12]

                                results.append(SearchResult(
                                    id=result_id,
                                    title=topic.get("Text", "")[:100],
                                    url=topic.get("FirstURL", ""),
                                    snippet=topic.get("Text", ""),
                                    engine=SearchEngine.DUCKDUCKGO,
                                    position=i,
                                    relevance_score=1.0 - (i * 0.1),
                                ))
        except Exception as e:
            logger.warning(f"DuckDuckGo search failed: {e}")

        return results

    async def _search_arxiv(
        self,
        query: SearchQuery,
    ) -> List[SearchResult]:
        """Search arXiv papers."""
        results = []

        try:
            url = "http://export.arxiv.org/api/query"
            params = {
                "search_query": f"all:{query.text}",
                "max_results": query.max_results,
            }

            async with self._get_session() as session:
                async with session.get(url, params=params) as resp:
                    if resp.status == 200:
                        text = await resp.text()

                        # Simple XML parsing
                        entries = re.findall(r'<entry>(.*?)</entry>', text, re.DOTALL)

                        for i, entry in enumerate(entries):
                            title = re.search(r'<title>(.*?)</title>', entry, re.DOTALL)
                            summary = re.search(r'<summary>(.*?)</summary>', entry, re.DOTALL)
                            id_match = re.search(r'<id>(.*?)</id>', entry)

                            if title and id_match:
                                result_id = hashlib.md5(id_match.group(1).encode()).hexdigest()[:12]

                                results.append(SearchResult(
                                    id=result_id,
                                    title=title.group(1).strip(),
                                    url=id_match.group(1),
                                    snippet=summary.group(1).strip() if summary else "",
                                    engine=SearchEngine.ARXIV,
                                    position=i,
                                    relevance_score=1.0 - (i * 0.1),
                                ))
        except Exception as e:
            logger.warning(f"arXiv search failed: {e}")

        return results

    async def _search_github(
        self,
        query: SearchQuery,
    ) -> List[SearchResult]:
        """Search GitHub repositories."""
        results = []

        try:
            url = "https://api.github.com/search/repositories"
            params = {
                "q": query.text,
                "per_page": query.max_results,
            }

            headers = {**self.HEADERS, "Accept": "application/vnd.github.v3+json"}

            async with self._get_session() as session:
                async with session.get(url, params=params, headers=headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()

                        for i, item in enumerate(data.get("items", [])):
                            result_id = hashlib.md5(
                                item.get("html_url", "").encode()
                            ).hexdigest()[:12]

                            results.append(SearchResult(
                                id=result_id,
                                title=item.get("full_name", ""),
                                url=item.get("html_url", ""),
                                snippet=item.get("description", "") or "",
                                engine=SearchEngine.GITHUB,
                                position=i,
                                relevance_score=item.get("stargazers_count", 0) / 10000,
                            ))
        except Exception as e:
            logger.warning(f"GitHub search failed: {e}")

        return results

    async def fetch_content(
        self,
        url: str,
        use_cache: bool = True,
    ) -> Optional[WebContent]:
        """
        Fetch and extract web content.

        Args:
            url: URL to fetch
            use_cache: Whether to use cache

        Returns:
            Extracted content or None
        """
        if use_cache and url in self._content_cache:
            self.stats["cache_hits"] += 1
            return self._content_cache[url]

        try:
            async with self._get_session() as session:
                async with session.get(url, headers=self.HEADERS, timeout=30) as resp:
                    if resp.status != 200:
                        return None

                    html = await resp.text()

                    content = self._extract_content(url, html)
                    content.status_code = resp.status

                    # Cache
                    self._content_cache[url] = content

                    self.stats["pages_fetched"] += 1

                    return content

        except Exception as e:
            logger.warning(f"Failed to fetch {url}: {e}")
            return None

    def _extract_content(self, url: str, html: str) -> WebContent:
        """Extract content from HTML."""
        # Extract title
        title_match = re.search(r'<title[^>]*>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
        title = title_match.group(1).strip() if title_match else ""

        # Extract headings
        headings = re.findall(r'<h[1-6][^>]*>(.*?)</h[1-6]>', html, re.IGNORECASE | re.DOTALL)
        headings = [self._strip_tags(h) for h in headings]

        # Extract links
        links = re.findall(r'href=["\']([^"\']+)["\']', html, re.IGNORECASE)

        # Extract code blocks
        code_blocks = re.findall(r'<code[^>]*>(.*?)</code>', html, re.IGNORECASE | re.DOTALL)
        code_blocks = [self._strip_tags(c) for c in code_blocks]

        # Extract text
        text = self._html_to_text(html)

        # Calculate metrics
        word_count = len(text.split())
        reading_time = word_count / 200  # Average reading speed

        # Extract domain
        domain_match = re.search(r'https?://([^/]+)', url)
        domain = domain_match.group(1) if domain_match else ""

        return WebContent(
            url=url,
            title=title,
            text=text,
            html=html,
            headings=headings[:20],
            links=links[:50],
            code_blocks=code_blocks[:20],
            word_count=word_count,
            reading_time_minutes=reading_time,
        )

    def _strip_tags(self, html: str) -> str:
        """Remove HTML tags."""
        return re.sub(r'<[^>]+>', '', html).strip()

    def _html_to_text(self, html: str) -> str:
        """Convert HTML to plain text."""
        # Remove scripts and styles
        text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)

        # Remove tags
        text = re.sub(r'<[^>]+>', ' ', text)

        # Decode entities
        text = text.replace('&nbsp;', ' ')
        text = text.replace('&amp;', '&')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&quot;', '"')

        # Clean whitespace
        text = re.sub(r'\s+', ' ', text)

        return text.strip()

    def _get_session(self) -> aiohttp.ClientSession:
        """Get or create session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def research_topic(
        self,
        topic: str,
        max_sources: int = 5,
    ) -> List[WebContent]:
        """
        Research a topic.

        Args:
            topic: Topic to research
            max_sources: Maximum sources to fetch

        Returns:
            List of extracted content
        """
        query = SearchQuery(
            text=topic,
            engines=[SearchEngine.DUCKDUCKGO, SearchEngine.ARXIV],
            max_results=max_sources * 2,
        )

        results = await self.search(query)

        contents = []
        for result in results[:max_sources]:
            content = await self.fetch_content(result.url)
            if content:
                contents.append(content)

        return contents

    async def close(self) -> None:
        """Close session."""
        if self._session and not self._session.closed:
            await self._session.close()

    def get_stats(self) -> Dict[str, Any]:
        """Get researcher statistics."""
        return {
            **self.stats,
            "cached_content": len(self._content_cache),
            "cached_searches": len(self._search_cache),
        }


async def demo():
    """Demonstrate web researcher."""
    print("=" * 60)
    print("BAEL Web Researcher Demo")
    print("=" * 60)

    researcher = WebResearcher()

    try:
        # Search
        print("\nSearching for 'machine learning frameworks'...")
        query = SearchQuery(
            text="machine learning frameworks",
            engines=[SearchEngine.DUCKDUCKGO],
            max_results=5,
        )

        results = await researcher.search(query)
        print(f"Found {len(results)} results:")

        for r in results[:3]:
            print(f"\n  [{r.engine.value}] {r.title[:50]}...")
            print(f"    URL: {r.url[:60]}...")
            print(f"    Score: {r.relevance_score:.2f}")

        # Fetch content
        if results:
            print(f"\nFetching content from first result...")
            content = await researcher.fetch_content(results[0].url)

            if content:
                print(f"  Title: {content.title[:50]}...")
                print(f"  Words: {content.word_count}")
                print(f"  Reading time: {content.reading_time_minutes:.1f} min")
                print(f"  Headings: {len(content.headings)}")
                print(f"  Links: {len(content.links)}")

        print(f"\nStats: {researcher.get_stats()}")

    finally:
        await researcher.close()


if __name__ == "__main__":
    asyncio.run(demo())

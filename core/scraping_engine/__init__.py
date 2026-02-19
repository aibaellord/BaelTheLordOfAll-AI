"""
BAEL Web Scraping Engine
========================

Advanced web scraping and data extraction.
"""

from .web_scraper import (
    # Enums
    ScraperType,
    ContentType,
    ExtractionMethod,
    RateLimitStrategy,

    # Dataclasses
    ScraperConfig,
    PageRequest,
    PageResponse,
    ExtractedData,
    ScrapingResult,

    # Classes
    WebScrapingEngine,
    ContentExtractor,
    RateLimiter,
    ProxyManager,
    CacheManager,

    # Instance
    scraper_engine
)

__all__ = [
    "ScraperType",
    "ContentType",
    "ExtractionMethod",
    "RateLimitStrategy",
    "ScraperConfig",
    "PageRequest",
    "PageResponse",
    "ExtractedData",
    "ScrapingResult",
    "WebScrapingEngine",
    "ContentExtractor",
    "RateLimiter",
    "ProxyManager",
    "CacheManager",
    "scraper_engine"
]

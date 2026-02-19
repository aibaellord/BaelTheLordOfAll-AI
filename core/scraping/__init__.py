"""
BAEL Universal Scraping Framework
===================================

Advanced web scraping infrastructure for BAEL.
Handles all web data extraction needs.

Components:
- ScraperCore: Main scraping engine
- BrowserAutomation: Playwright/Selenium integration
- ProxyRotator: Proxy management and rotation
- CaptchaSolver: Multi-provider captcha solving
- AntiDetection: Evasion techniques
- DataExtractor: Structured data extraction
"""

from .anti_detection import AntiDetection, EvasionLevel, FingerprintConfig
from .browser_automation import (BrowserAutomation, BrowserConfig, BrowserType,
                                 PageAction)
from .captcha_solver import CaptchaSolver, CaptchaType, SolverProvider
from .data_extractor import DataExtractor, ExtractionPattern, ExtractorType
from .proxy_rotator import ProxyConfig, ProxyHealth, ProxyRotator, ProxyType
from .scraper_core import (ScraperCore, ScraperType, ScrapingConfig,
                           ScrapingResult)

__all__ = [
    # Core
    "ScraperCore",
    "ScrapingConfig",
    "ScrapingResult",
    "ScraperType",
    # Browser
    "BrowserAutomation",
    "BrowserConfig",
    "BrowserType",
    "PageAction",
    # Proxy
    "ProxyRotator",
    "ProxyConfig",
    "ProxyType",
    "ProxyHealth",
    # Captcha
    "CaptchaSolver",
    "CaptchaType",
    "SolverProvider",
    # Anti-detection
    "AntiDetection",
    "FingerprintConfig",
    "EvasionLevel",
    # Extraction
    "DataExtractor",
    "ExtractionPattern",
    "ExtractorType",
]

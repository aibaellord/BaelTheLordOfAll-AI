#!/usr/bin/env python3
"""
BAEL - Browser Automation Tools
Web scraping and browser automation capabilities.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger("BAEL.Tools.Browser")


class BrowserType(Enum):
    """Supported browser types."""
    CHROMIUM = "chromium"
    FIREFOX = "firefox"
    WEBKIT = "webkit"


@dataclass
class PageContent:
    """Extracted page content."""
    url: str
    title: str
    text: str
    html: str
    links: List[Dict[str, str]] = field(default_factory=list)
    images: List[Dict[str, str]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Screenshot:
    """Screenshot data."""
    url: str
    path: str
    width: int
    height: int
    full_page: bool


class BrowserInterface(ABC):
    """Abstract browser interface."""

    @abstractmethod
    async def navigate(self, url: str) -> PageContent:
        """Navigate to a URL."""
        pass

    @abstractmethod
    async def screenshot(self, path: str, full_page: bool = False) -> Screenshot:
        """Take a screenshot."""
        pass

    @abstractmethod
    async def click(self, selector: str) -> None:
        """Click an element."""
        pass

    @abstractmethod
    async def fill(self, selector: str, text: str) -> None:
        """Fill a form field."""
        pass

    @abstractmethod
    async def extract_text(self, selector: str) -> str:
        """Extract text from an element."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close the browser."""
        pass


class PlaywrightBrowser(BrowserInterface):
    """Playwright-based browser automation."""

    def __init__(
        self,
        browser_type: BrowserType = BrowserType.CHROMIUM,
        headless: bool = True
    ):
        self.browser_type = browser_type
        self.headless = headless
        self._browser = None
        self._context = None
        self._page = None

    async def _ensure_browser(self):
        """Ensure browser is initialized."""
        if self._browser is None:
            try:
                from playwright.async_api import async_playwright

                self._playwright = await async_playwright().start()

                if self.browser_type == BrowserType.CHROMIUM:
                    self._browser = await self._playwright.chromium.launch(headless=self.headless)
                elif self.browser_type == BrowserType.FIREFOX:
                    self._browser = await self._playwright.firefox.launch(headless=self.headless)
                else:
                    self._browser = await self._playwright.webkit.launch(headless=self.headless)

                self._context = await self._browser.new_context()
                self._page = await self._context.new_page()

                logger.info(f"Browser initialized: {self.browser_type.value}")
            except ImportError:
                raise RuntimeError("Playwright not installed. Run: pip install playwright && playwright install")

    async def navigate(self, url: str) -> PageContent:
        """Navigate to a URL and extract content."""
        await self._ensure_browser()

        await self._page.goto(url, wait_until="domcontentloaded")

        title = await self._page.title()
        text = await self._page.inner_text("body")
        html = await self._page.content()

        # Extract links
        links = await self._page.evaluate("""
            () => Array.from(document.querySelectorAll('a[href]')).map(a => ({
                text: a.innerText.trim(),
                href: a.href
            })).slice(0, 100)
        """)

        # Extract images
        images = await self._page.evaluate("""
            () => Array.from(document.querySelectorAll('img')).map(img => ({
                alt: img.alt,
                src: img.src
            })).slice(0, 50)
        """)

        return PageContent(
            url=url,
            title=title,
            text=text,
            html=html,
            links=links,
            images=images
        )

    async def screenshot(self, path: str, full_page: bool = False) -> Screenshot:
        """Take a screenshot."""
        await self._ensure_browser()

        await self._page.screenshot(path=path, full_page=full_page)

        viewport = self._page.viewport_size

        return Screenshot(
            url=self._page.url,
            path=path,
            width=viewport["width"],
            height=viewport["height"],
            full_page=full_page
        )

    async def click(self, selector: str) -> None:
        """Click an element."""
        await self._ensure_browser()
        await self._page.click(selector)

    async def fill(self, selector: str, text: str) -> None:
        """Fill a form field."""
        await self._ensure_browser()
        await self._page.fill(selector, text)

    async def extract_text(self, selector: str) -> str:
        """Extract text from an element."""
        await self._ensure_browser()
        return await self._page.inner_text(selector)

    async def close(self) -> None:
        """Close the browser."""
        if self._browser:
            await self._browser.close()
            await self._playwright.stop()
            self._browser = None
            self._context = None
            self._page = None


class SimpleBrowser(BrowserInterface):
    """Simple HTTP-based browser (no JavaScript)."""

    def __init__(self):
        self._session = None
        self._last_url = None
        self._last_content = None

    async def _ensure_session(self):
        """Ensure HTTP session is initialized."""
        if self._session is None:
            import aiohttp
            self._session = aiohttp.ClientSession(
                headers={
                    "User-Agent": "BAEL/1.0 (AI Research Agent)"
                }
            )

    async def navigate(self, url: str) -> PageContent:
        """Fetch URL content."""
        await self._ensure_session()

        async with self._session.get(url) as response:
            html = await response.text()

        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "lxml")

        # Extract title
        title_tag = soup.find("title")
        title = title_tag.text if title_tag else ""

        # Extract text (remove scripts and styles)
        for tag in soup(["script", "style", "nav", "footer"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)

        # Extract links
        links = []
        for a in soup.find_all("a", href=True)[:100]:
            links.append({
                "text": a.get_text(strip=True),
                "href": a["href"]
            })

        # Extract images
        images = []
        for img in soup.find_all("img")[:50]:
            images.append({
                "alt": img.get("alt", ""),
                "src": img.get("src", "")
            })

        self._last_url = url
        self._last_content = PageContent(
            url=url,
            title=title,
            text=text,
            html=html,
            links=links,
            images=images
        )

        return self._last_content

    async def screenshot(self, path: str, full_page: bool = False) -> Screenshot:
        """Not supported in simple browser."""
        raise NotImplementedError("Screenshots require Playwright browser")

    async def click(self, selector: str) -> None:
        """Not supported in simple browser."""
        raise NotImplementedError("Clicking requires Playwright browser")

    async def fill(self, selector: str, text: str) -> None:
        """Not supported in simple browser."""
        raise NotImplementedError("Form filling requires Playwright browser")

    async def extract_text(self, selector: str) -> str:
        """Extract text using CSS selector from last fetched page."""
        if self._last_content is None:
            raise RuntimeError("No page loaded")

        from bs4 import BeautifulSoup
        soup = BeautifulSoup(self._last_content.html, "lxml")
        element = soup.select_one(selector)

        return element.get_text(strip=True) if element else ""

    async def close(self) -> None:
        """Close the session."""
        if self._session:
            await self._session.close()
            self._session = None


class BrowserManager:
    """
    Manages browser instances for BAEL.

    Automatically selects appropriate browser implementation
    based on task requirements.
    """

    def __init__(self):
        self._browsers: Dict[str, BrowserInterface] = {}

    async def get_browser(
        self,
        name: str = "default",
        browser_type: BrowserType = BrowserType.CHROMIUM,
        headless: bool = True,
        simple: bool = False
    ) -> BrowserInterface:
        """Get or create a browser instance."""
        if name not in self._browsers:
            if simple:
                self._browsers[name] = SimpleBrowser()
            else:
                try:
                    browser = PlaywrightBrowser(browser_type, headless)
                    await browser._ensure_browser()
                    self._browsers[name] = browser
                except Exception as e:
                    logger.warning(f"Playwright unavailable, using simple browser: {e}")
                    self._browsers[name] = SimpleBrowser()

        return self._browsers[name]

    async def close_all(self) -> None:
        """Close all browser instances."""
        for browser in self._browsers.values():
            await browser.close()
        self._browsers.clear()

    async def scrape_url(self, url: str, simple: bool = False) -> PageContent:
        """Quick scrape of a URL."""
        browser = await self.get_browser(simple=simple)
        return await browser.navigate(url)

    async def search_web(
        self,
        query: str,
        engine: str = "duckduckgo"
    ) -> List[Dict[str, str]]:
        """
        Search the web using specified engine.

        Returns list of search results.
        """
        browser = await self.get_browser(simple=True)

        # Encode query
        import urllib.parse
        encoded_query = urllib.parse.quote(query)

        if engine == "duckduckgo":
            url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
        else:
            url = f"https://html.duckduckgo.com/html/?q={encoded_query}"

        content = await browser.navigate(url)

        results = []
        for link in content.links:
            if link.get("href", "").startswith("http"):
                results.append({
                    "title": link.get("text", ""),
                    "url": link.get("href", "")
                })

        return results[:10]


# Global browser manager
browser_manager = BrowserManager()


# Tool functions for MCP
async def tool_browse_url(url: str) -> Dict[str, Any]:
    """Browse a URL and extract content."""
    try:
        content = await browser_manager.scrape_url(url, simple=True)
        return {
            "success": True,
            "title": content.title,
            "text": content.text[:5000],
            "link_count": len(content.links),
            "image_count": len(content.images)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


async def tool_search_web(query: str) -> Dict[str, Any]:
    """Search the web."""
    try:
        results = await browser_manager.search_web(query)
        return {
            "success": True,
            "results": results
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


async def tool_screenshot(url: str, path: str) -> Dict[str, Any]:
    """Take a screenshot of a webpage."""
    try:
        browser = await browser_manager.get_browser(simple=False)
        await browser.navigate(url)
        screenshot = await browser.screenshot(path, full_page=True)
        return {
            "success": True,
            "path": screenshot.path,
            "width": screenshot.width,
            "height": screenshot.height
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

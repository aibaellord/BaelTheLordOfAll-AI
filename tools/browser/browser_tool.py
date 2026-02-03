"""
BAEL - Browser Automation Tool
Advanced browser automation with Playwright.

Features:
- Headless and headed browser modes
- Screenshot and PDF capture
- JavaScript execution
- Form filling and interaction
- Network interception
- Session management
"""

import asyncio
import base64
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("BAEL.Browser")


# =============================================================================
# ENUMS & CONFIG
# =============================================================================

class BrowserType(Enum):
    """Supported browser types."""
    CHROMIUM = "chromium"
    FIREFOX = "firefox"
    WEBKIT = "webkit"


class WaitCondition(Enum):
    """Wait conditions for page load."""
    LOAD = "load"
    DOMCONTENTLOADED = "domcontentloaded"
    NETWORKIDLE = "networkidle"
    COMMIT = "commit"


@dataclass
class BrowserConfig:
    """Browser configuration."""
    browser_type: BrowserType = BrowserType.CHROMIUM
    headless: bool = True
    slow_mo: int = 0
    timeout: int = 30000
    viewport_width: int = 1280
    viewport_height: int = 720
    user_agent: Optional[str] = None
    proxy: Optional[str] = None
    ignore_https_errors: bool = True
    downloads_path: Optional[str] = None


@dataclass
class PageResult:
    """Result from a page operation."""
    success: bool
    url: str
    title: str
    content: Optional[str] = None
    screenshot: Optional[bytes] = None
    pdf: Optional[bytes] = None
    error: Optional[str] = None
    timing: Dict[str, float] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# BROWSER TOOL
# =============================================================================

class BrowserTool:
    """Advanced browser automation tool using Playwright."""

    def __init__(self, config: Optional[BrowserConfig] = None):
        self.config = config or BrowserConfig()
        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None
        self._initialized = False

    async def initialize(self) -> bool:
        """Initialize browser."""
        if self._initialized:
            return True

        try:
            from playwright.async_api import async_playwright

            self._playwright = await async_playwright().start()

            # Select browser
            browser_launchers = {
                BrowserType.CHROMIUM: self._playwright.chromium,
                BrowserType.FIREFOX: self._playwright.firefox,
                BrowserType.WEBKIT: self._playwright.webkit
            }

            launcher = browser_launchers[self.config.browser_type]

            # Launch options
            launch_options = {
                "headless": self.config.headless,
                "slow_mo": self.config.slow_mo
            }

            if self.config.proxy:
                launch_options["proxy"] = {"server": self.config.proxy}

            if self.config.downloads_path:
                launch_options["downloads_path"] = self.config.downloads_path

            self._browser = await launcher.launch(**launch_options)

            # Create context
            context_options = {
                "viewport": {
                    "width": self.config.viewport_width,
                    "height": self.config.viewport_height
                },
                "ignore_https_errors": self.config.ignore_https_errors
            }

            if self.config.user_agent:
                context_options["user_agent"] = self.config.user_agent

            self._context = await self._browser.new_context(**context_options)
            self._page = await self._context.new_page()

            # Set default timeout
            self._page.set_default_timeout(self.config.timeout)

            self._initialized = True
            logger.info(f"Browser initialized: {self.config.browser_type.value}")
            return True

        except Exception as e:
            logger.error(f"Browser initialization failed: {e}")
            return False

    async def close(self) -> None:
        """Close browser."""
        if self._page:
            await self._page.close()
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

        self._initialized = False
        logger.info("Browser closed")

    async def navigate(self, url: str, wait_until: WaitCondition = WaitCondition.LOAD) -> PageResult:
        """Navigate to a URL."""
        if not self._initialized:
            await self.initialize()

        start_time = datetime.now()

        try:
            response = await self._page.goto(url, wait_until=wait_until.value)

            title = await self._page.title()

            end_time = datetime.now()

            return PageResult(
                success=True,
                url=self._page.url,
                title=title,
                timing={"load_time": (end_time - start_time).total_seconds()},
                metadata={
                    "status": response.status if response else None,
                    "headers": dict(response.headers) if response else {}
                }
            )

        except Exception as e:
            logger.error(f"Navigation error: {e}")
            return PageResult(
                success=False,
                url=url,
                title="",
                error=str(e)
            )

    async def get_content(self, selector: Optional[str] = None) -> str:
        """Get page content."""
        if not self._initialized:
            await self.initialize()

        try:
            if selector:
                element = await self._page.query_selector(selector)
                if element:
                    return await element.inner_text()
                return ""
            else:
                return await self._page.content()

        except Exception as e:
            logger.error(f"Get content error: {e}")
            return ""

    async def get_text(self) -> str:
        """Get visible text content."""
        if not self._initialized:
            await self.initialize()

        try:
            return await self._page.inner_text("body")
        except Exception as e:
            logger.error(f"Get text error: {e}")
            return ""

    async def screenshot(self, full_page: bool = False, path: Optional[str] = None) -> Optional[bytes]:
        """Take screenshot."""
        if not self._initialized:
            await self.initialize()

        try:
            options = {"full_page": full_page}
            if path:
                options["path"] = path

            screenshot = await self._page.screenshot(**options)
            return screenshot

        except Exception as e:
            logger.error(f"Screenshot error: {e}")
            return None

    async def pdf(self, path: Optional[str] = None) -> Optional[bytes]:
        """Generate PDF."""
        if not self._initialized:
            await self.initialize()

        try:
            options = {"format": "A4"}
            if path:
                options["path"] = path

            pdf_data = await self._page.pdf(**options)
            return pdf_data

        except Exception as e:
            logger.error(f"PDF error: {e}")
            return None

    async def click(self, selector: str) -> bool:
        """Click an element."""
        if not self._initialized:
            await self.initialize()

        try:
            await self._page.click(selector)
            return True
        except Exception as e:
            logger.error(f"Click error: {e}")
            return False

    async def fill(self, selector: str, value: str) -> bool:
        """Fill a form field."""
        if not self._initialized:
            await self.initialize()

        try:
            await self._page.fill(selector, value)
            return True
        except Exception as e:
            logger.error(f"Fill error: {e}")
            return False

    async def select(self, selector: str, value: str) -> bool:
        """Select dropdown option."""
        if not self._initialized:
            await self.initialize()

        try:
            await self._page.select_option(selector, value)
            return True
        except Exception as e:
            logger.error(f"Select error: {e}")
            return False

    async def type_text(self, selector: str, text: str, delay: int = 50) -> bool:
        """Type text with human-like delay."""
        if not self._initialized:
            await self.initialize()

        try:
            await self._page.type(selector, text, delay=delay)
            return True
        except Exception as e:
            logger.error(f"Type error: {e}")
            return False

    async def wait_for_selector(self, selector: str, timeout: Optional[int] = None) -> bool:
        """Wait for selector to appear."""
        if not self._initialized:
            await self.initialize()

        try:
            await self._page.wait_for_selector(selector, timeout=timeout)
            return True
        except Exception as e:
            logger.error(f"Wait error: {e}")
            return False

    async def evaluate(self, script: str) -> Any:
        """Execute JavaScript."""
        if not self._initialized:
            await self.initialize()

        try:
            return await self._page.evaluate(script)
        except Exception as e:
            logger.error(f"Evaluate error: {e}")
            return None

    async def get_links(self) -> List[Dict[str, str]]:
        """Get all links from page."""
        if not self._initialized:
            await self.initialize()

        try:
            links = await self._page.evaluate("""
                () => Array.from(document.querySelectorAll('a')).map(a => ({
                    href: a.href,
                    text: a.innerText.trim()
                }))
            """)
            return links
        except Exception as e:
            logger.error(f"Get links error: {e}")
            return []

    async def scroll_to_bottom(self) -> None:
        """Scroll to bottom of page."""
        if not self._initialized:
            await self.initialize()

        try:
            await self._page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        except Exception as e:
            logger.error(f"Scroll error: {e}")

    async def extract_data(self, schema: Dict[str, str]) -> Dict[str, Any]:
        """Extract structured data using CSS selectors."""
        if not self._initialized:
            await self.initialize()

        result = {}

        for key, selector in schema.items():
            try:
                elements = await self._page.query_selector_all(selector)

                if len(elements) == 0:
                    result[key] = None
                elif len(elements) == 1:
                    result[key] = await elements[0].inner_text()
                else:
                    result[key] = [await el.inner_text() for el in elements]

            except Exception as e:
                logger.error(f"Extract error for {key}: {e}")
                result[key] = None

        return result

    async def intercept_network(self, handler: Callable) -> None:
        """Set up network interception."""
        if not self._initialized:
            await self.initialize()

        try:
            await self._page.route("**/*", handler)
        except Exception as e:
            logger.error(f"Intercept error: {e}")

    async def wait_for_navigation(self, timeout: Optional[int] = None) -> bool:
        """Wait for navigation to complete."""
        if not self._initialized:
            await self.initialize()

        try:
            await self._page.wait_for_load_state("networkidle", timeout=timeout)
            return True
        except Exception as e:
            logger.error(f"Wait navigation error: {e}")
            return False


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

async def quick_fetch(url: str, extract_text: bool = True) -> Dict[str, Any]:
    """Quick fetch of a URL."""
    browser = BrowserTool()

    try:
        await browser.initialize()
        result = await browser.navigate(url)

        if result.success:
            content = await browser.get_text() if extract_text else await browser.get_content()
            return {
                "success": True,
                "url": result.url,
                "title": result.title,
                "content": content,
                "timing": result.timing
            }
        else:
            return {
                "success": False,
                "error": result.error
            }

    finally:
        await browser.close()


async def capture_screenshot(url: str, output_path: str, full_page: bool = False) -> bool:
    """Capture screenshot of a URL."""
    browser = BrowserTool()

    try:
        await browser.initialize()
        await browser.navigate(url)
        screenshot = await browser.screenshot(full_page=full_page, path=output_path)
        return screenshot is not None

    finally:
        await browser.close()


# =============================================================================
# MAIN
# =============================================================================

async def main():
    """Test browser tool."""
    browser = BrowserTool()

    try:
        if await browser.initialize():
            print("✅ Browser initialized")

            result = await browser.navigate("https://example.com")
            print(f"📄 Navigated to: {result.title}")

            content = await browser.get_text()
            print(f"📝 Content length: {len(content)}")

            links = await browser.get_links()
            print(f"🔗 Links found: {len(links)}")

    finally:
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())

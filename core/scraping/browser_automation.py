"""
BAEL Browser Automation
========================

Headless browser automation using Playwright and Selenium.
For JavaScript-heavy sites and complex interactions.

Features:
- Playwright integration
- Selenium fallback
- Action scripting
- Screenshot capture
- PDF generation
- Cookie management
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


class BrowserType(Enum):
    """Browser types."""
    CHROMIUM = "chromium"
    FIREFOX = "firefox"
    WEBKIT = "webkit"
    CHROME = "chrome"
    EDGE = "edge"


class ActionType(Enum):
    """Page action types."""
    CLICK = "click"
    FILL = "fill"
    TYPE = "type"
    SELECT = "select"
    CHECK = "check"
    UNCHECK = "uncheck"
    HOVER = "hover"
    SCROLL = "scroll"
    WAIT = "wait"
    WAIT_SELECTOR = "wait_selector"
    SCREENSHOT = "screenshot"
    PDF = "pdf"
    EXECUTE_JS = "execute_js"
    NAVIGATE = "navigate"
    PRESS = "press"


@dataclass
class PageAction:
    """A page action to execute."""
    action: ActionType
    selector: Optional[str] = None
    value: Optional[str] = None
    options: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "action": self.action.value,
            "selector": self.selector,
            "value": self.value,
            "options": self.options,
        }


@dataclass
class BrowserConfig:
    """Browser configuration."""
    browser_type: BrowserType = BrowserType.CHROMIUM
    headless: bool = True

    # Viewport
    viewport_width: int = 1920
    viewport_height: int = 1080

    # Timeouts
    navigation_timeout: int = 30000
    default_timeout: int = 30000

    # User agent
    user_agent: Optional[str] = None

    # Proxy
    proxy: Optional[str] = None

    # Stealth
    enable_stealth: bool = True

    # Storage
    storage_state: Optional[str] = None

    # Other
    ignore_https_errors: bool = True
    java_script_enabled: bool = True
    locale: str = "en-US"
    timezone: str = "America/New_York"

    # Args
    extra_args: List[str] = field(default_factory=list)


@dataclass
class BrowserResult:
    """Result of browser operation."""
    url: str
    content: str
    title: str = ""

    # Timing
    load_time_ms: float = 0.0

    # Screenshots
    screenshot: Optional[bytes] = None
    pdf: Optional[bytes] = None

    # Cookies
    cookies: List[Dict[str, Any]] = field(default_factory=list)

    # Error
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        """Check if operation was successful."""
        return self.error is None


class BrowserAutomation:
    """
    Browser automation engine for BAEL.
    """

    def __init__(
        self,
        config: Optional[BrowserConfig] = None,
    ):
        self.config = config or BrowserConfig()

        # Playwright objects
        self._playwright = None
        self._browser = None
        self._context = None

        # State
        self._initialized = False

        # Statistics
        self.stats = {
            "pages_loaded": 0,
            "actions_executed": 0,
            "screenshots_taken": 0,
            "errors": 0,
        }

    async def initialize(self) -> None:
        """Initialize Playwright browser."""
        if self._initialized:
            return

        try:
            from playwright.async_api import async_playwright
        except ImportError:
            logger.error("Playwright not installed. Install with: pip install playwright && playwright install")
            raise ImportError("Playwright not installed")

        self._playwright = await async_playwright().start()

        # Get browser launcher
        if self.config.browser_type == BrowserType.CHROMIUM:
            launcher = self._playwright.chromium
        elif self.config.browser_type == BrowserType.FIREFOX:
            launcher = self._playwright.firefox
        elif self.config.browser_type == BrowserType.WEBKIT:
            launcher = self._playwright.webkit
        else:
            launcher = self._playwright.chromium

        # Launch browser
        launch_args = {
            "headless": self.config.headless,
        }

        if self.config.extra_args:
            launch_args["args"] = self.config.extra_args

        self._browser = await launcher.launch(**launch_args)

        # Create context
        context_args = {
            "viewport": {
                "width": self.config.viewport_width,
                "height": self.config.viewport_height,
            },
            "ignore_https_errors": self.config.ignore_https_errors,
            "java_script_enabled": self.config.java_script_enabled,
            "locale": self.config.locale,
            "timezone_id": self.config.timezone,
        }

        if self.config.user_agent:
            context_args["user_agent"] = self.config.user_agent

        if self.config.proxy:
            context_args["proxy"] = {"server": self.config.proxy}

        if self.config.storage_state:
            context_args["storage_state"] = self.config.storage_state

        self._context = await self._browser.new_context(**context_args)

        # Apply stealth if enabled
        if self.config.enable_stealth:
            await self._apply_stealth()

        self._context.set_default_timeout(self.config.default_timeout)
        self._context.set_default_navigation_timeout(self.config.navigation_timeout)

        self._initialized = True
        logger.info(f"Browser initialized: {self.config.browser_type.value}")

    async def _apply_stealth(self) -> None:
        """Apply stealth modifications to avoid detection."""
        stealth_js = """
        // Override navigator properties
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });

        // Override chrome property
        window.chrome = {
            runtime: {},
            loadTimes: function() {},
            csi: function() {},
            app: {}
        };

        // Override permissions
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission }) :
                originalQuery(parameters)
        );

        // Override plugins
        Object.defineProperty(navigator, 'plugins', {
            get: () => [1, 2, 3, 4, 5]
        });

        // Override languages
        Object.defineProperty(navigator, 'languages', {
            get: () => ['en-US', 'en']
        });
        """

        await self._context.add_init_script(stealth_js)

    async def close(self) -> None:
        """Close browser."""
        if self._context:
            await self._context.close()
            self._context = None

        if self._browser:
            await self._browser.close()
            self._browser = None

        if self._playwright:
            await self._playwright.stop()
            self._playwright = None

        self._initialized = False

    async def navigate(
        self,
        url: str,
        wait_until: str = "networkidle",
        actions: Optional[List[PageAction]] = None,
        take_screenshot: bool = False,
        generate_pdf: bool = False,
    ) -> BrowserResult:
        """
        Navigate to URL and optionally execute actions.

        Args:
            url: URL to navigate to
            wait_until: Wait condition (load, domcontentloaded, networkidle)
            actions: Optional list of actions to execute
            take_screenshot: Take screenshot after loading
            generate_pdf: Generate PDF after loading

        Returns:
            BrowserResult
        """
        if not self._initialized:
            await self.initialize()

        page = await self._context.new_page()

        try:
            start_time = asyncio.get_event_loop().time()

            # Navigate
            await page.goto(url, wait_until=wait_until)

            load_time = (asyncio.get_event_loop().time() - start_time) * 1000
            self.stats["pages_loaded"] += 1

            # Execute actions
            if actions:
                for action in actions:
                    await self._execute_action(page, action)
                    self.stats["actions_executed"] += 1

            # Get content
            content = await page.content()
            title = await page.title()

            # Screenshot
            screenshot = None
            if take_screenshot:
                screenshot = await page.screenshot(full_page=True)
                self.stats["screenshots_taken"] += 1

            # PDF
            pdf = None
            if generate_pdf:
                pdf = await page.pdf()

            # Get cookies
            cookies = await self._context.cookies()

            return BrowserResult(
                url=page.url,
                content=content,
                title=title,
                load_time_ms=load_time,
                screenshot=screenshot,
                pdf=pdf,
                cookies=cookies,
            )

        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"Browser navigation error: {e}")
            return BrowserResult(
                url=url,
                content="",
                error=str(e),
            )
        finally:
            await page.close()

    async def _execute_action(
        self,
        page: Any,
        action: PageAction,
    ) -> Any:
        """Execute a page action."""

        if action.action == ActionType.CLICK:
            await page.click(action.selector, **action.options)

        elif action.action == ActionType.FILL:
            await page.fill(action.selector, action.value or "", **action.options)

        elif action.action == ActionType.TYPE:
            await page.type(action.selector, action.value or "", **action.options)

        elif action.action == ActionType.SELECT:
            await page.select_option(action.selector, action.value, **action.options)

        elif action.action == ActionType.CHECK:
            await page.check(action.selector, **action.options)

        elif action.action == ActionType.UNCHECK:
            await page.uncheck(action.selector, **action.options)

        elif action.action == ActionType.HOVER:
            await page.hover(action.selector, **action.options)

        elif action.action == ActionType.SCROLL:
            if action.selector:
                await page.locator(action.selector).scroll_into_view_if_needed()
            else:
                await page.evaluate(f"window.scrollBy(0, {action.value or 500})")

        elif action.action == ActionType.WAIT:
            await asyncio.sleep(float(action.value or 1))

        elif action.action == ActionType.WAIT_SELECTOR:
            await page.wait_for_selector(action.selector, **action.options)

        elif action.action == ActionType.EXECUTE_JS:
            return await page.evaluate(action.value)

        elif action.action == ActionType.NAVIGATE:
            await page.goto(action.value)

        elif action.action == ActionType.PRESS:
            await page.press(action.selector or "body", action.value or "Enter")

        elif action.action == ActionType.SCREENSHOT:
            return await page.screenshot(**action.options)

    async def execute_script(
        self,
        url: str,
        script: str,
    ) -> Any:
        """
        Navigate to URL and execute JavaScript.

        Args:
            url: URL to navigate to
            script: JavaScript to execute

        Returns:
            Script result
        """
        if not self._initialized:
            await self.initialize()

        page = await self._context.new_page()

        try:
            await page.goto(url, wait_until="networkidle")
            result = await page.evaluate(script)
            return result
        finally:
            await page.close()

    async def save_storage_state(self, path: str) -> None:
        """Save browser storage state (cookies, localStorage)."""
        if self._context:
            await self._context.storage_state(path=path)

    def get_stats(self) -> Dict[str, Any]:
        """Get browser statistics."""
        return {
            **self.stats,
            "initialized": self._initialized,
            "browser_type": self.config.browser_type.value,
        }


def create_action_script(actions: List[Dict[str, Any]]) -> List[PageAction]:
    """Create action list from dictionaries."""
    result = []

    for action_dict in actions:
        action_type = ActionType(action_dict["action"])
        result.append(PageAction(
            action=action_type,
            selector=action_dict.get("selector"),
            value=action_dict.get("value"),
            options=action_dict.get("options", {}),
        ))

    return result


def demo():
    """Demonstrate browser automation."""
    print("=" * 60)
    print("BAEL Browser Automation Demo")
    print("=" * 60)

    config = BrowserConfig(
        browser_type=BrowserType.CHROMIUM,
        headless=True,
    )

    browser = BrowserAutomation(config)

    print(f"\nBrowser configuration:")
    print(f"  Type: {config.browser_type.value}")
    print(f"  Headless: {config.headless}")
    print(f"  Viewport: {config.viewport_width}x{config.viewport_height}")
    print(f"  Stealth: {config.enable_stealth}")

    # Create sample action script
    actions = create_action_script([
        {"action": "wait_selector", "selector": "#content"},
        {"action": "scroll", "value": "500"},
        {"action": "wait", "value": "1"},
    ])

    print(f"\nSample actions: {[a.action.value for a in actions]}")


if __name__ == "__main__":
    demo()

"""
BAEL Anti-Detection
====================

Browser fingerprint evasion and anti-bot detection.
Techniques to avoid detection by protection services.

Features:
- Fingerprint randomization
- Canvas fingerprint spoofing
- WebGL fingerprint spoofing
- Navigator override
- Timezone/locale matching
- Mouse movement simulation
- Keyboard timing humanization
"""

import hashlib
import logging
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class EvasionLevel(Enum):
    """Evasion intensity levels."""
    MINIMAL = "minimal"         # Basic evasion
    STANDARD = "standard"       # Typical protection bypass
    AGGRESSIVE = "aggressive"   # Maximum evasion
    CUSTOM = "custom"          # User-defined


class ProtectionType(Enum):
    """Known protection services."""
    CLOUDFLARE = "cloudflare"
    IMPERVA = "imperva"
    AKAMAI = "akamai"
    DATADOME = "datadome"
    PERIMETERX = "perimeterx"
    KASADA = "kasada"
    RECAPTCHA = "recaptcha"
    HCAPTCHA = "hcaptcha"
    GENERIC = "generic"


@dataclass
class FingerprintConfig:
    """Fingerprint configuration."""
    # Browser
    browser_name: str = "Chrome"
    browser_version: str = "120"
    platform: str = "Win32"

    # Screen
    screen_width: int = 1920
    screen_height: int = 1080
    color_depth: int = 24
    pixel_ratio: float = 1.0

    # Hardware
    hardware_concurrency: int = 8
    device_memory: int = 8

    # Timezone
    timezone: str = "America/New_York"
    timezone_offset: int = -300

    # Language
    language: str = "en-US"
    languages: List[str] = field(default_factory=lambda: ["en-US", "en"])

    # Canvas noise
    add_canvas_noise: bool = True
    canvas_noise_level: float = 0.01

    # WebGL
    webgl_vendor: str = "Google Inc. (NVIDIA)"
    webgl_renderer: str = "ANGLE (NVIDIA, NVIDIA GeForce GTX 1080 Direct3D11 vs_5_0 ps_5_0, D3D11)"

    # Audio
    add_audio_noise: bool = True


@dataclass
class MouseProfile:
    """Mouse behavior profile for humanization."""
    # Speed
    min_speed: float = 100  # pixels/second
    max_speed: float = 800

    # Acceleration
    use_bezier_curves: bool = True
    control_points: int = 3

    # Micro-movements
    add_jitter: bool = True
    jitter_amplitude: float = 2.0

    # Click
    click_delay_ms: Tuple[int, int] = (50, 200)
    double_click_gap_ms: Tuple[int, int] = (100, 300)


@dataclass
class KeyboardProfile:
    """Keyboard behavior profile for humanization."""
    # Typing speed (chars per second)
    min_cps: float = 3.0
    max_cps: float = 10.0

    # Inter-key delay variation
    delay_variation: float = 0.3

    # Mistakes
    typo_rate: float = 0.02
    correction_delay_ms: Tuple[int, int] = (200, 500)

    # Key press duration
    press_duration_ms: Tuple[int, int] = (30, 100)


class AntiDetection:
    """
    Anti-detection and evasion techniques for BAEL.
    """

    # Common screen resolutions
    SCREEN_RESOLUTIONS = [
        (1920, 1080), (1366, 768), (1536, 864),
        (1440, 900), (1280, 720), (2560, 1440),
        (1680, 1050), (1600, 900), (1280, 800),
    ]

    # Common user agents by browser
    USER_AGENTS = {
        "chrome_windows": [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        ],
        "chrome_mac": [
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        ],
        "firefox_windows": [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        ],
        "safari_mac": [
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
        ],
    }

    # WebGL configurations
    WEBGL_CONFIGS = [
        ("Google Inc. (NVIDIA)", "ANGLE (NVIDIA, NVIDIA GeForce GTX 1080 Direct3D11 vs_5_0 ps_5_0, D3D11)"),
        ("Google Inc. (AMD)", "ANGLE (AMD, AMD Radeon RX 580 Direct3D11 vs_5_0 ps_5_0, D3D11)"),
        ("Google Inc. (Intel)", "ANGLE (Intel, Intel(R) UHD Graphics 630 Direct3D11 vs_5_0 ps_5_0, D3D11)"),
        ("Intel Inc.", "Intel Iris OpenGL Engine"),
    ]

    def __init__(
        self,
        level: EvasionLevel = EvasionLevel.STANDARD,
    ):
        self.level = level
        self.fingerprint = FingerprintConfig()
        self.mouse_profile = MouseProfile()
        self.keyboard_profile = KeyboardProfile()

    def generate_fingerprint(
        self,
        consistent_seed: Optional[str] = None,
    ) -> FingerprintConfig:
        """
        Generate a randomized but consistent fingerprint.

        Args:
            consistent_seed: Optional seed for reproducible fingerprints

        Returns:
            FingerprintConfig
        """
        if consistent_seed:
            random.seed(hashlib.md5(consistent_seed.encode()).hexdigest())

        # Screen
        width, height = random.choice(self.SCREEN_RESOLUTIONS)

        # Hardware
        hardware_concurrency = random.choice([4, 8, 12, 16])
        device_memory = random.choice([4, 8, 16])

        # WebGL
        webgl_vendor, webgl_renderer = random.choice(self.WEBGL_CONFIGS)

        # Timezone
        timezones = [
            ("America/New_York", -300),
            ("America/Chicago", -360),
            ("America/Los_Angeles", -480),
            ("Europe/London", 0),
            ("Europe/Paris", 60),
        ]
        tz_name, tz_offset = random.choice(timezones)

        fp = FingerprintConfig(
            screen_width=width,
            screen_height=height,
            hardware_concurrency=hardware_concurrency,
            device_memory=device_memory,
            webgl_vendor=webgl_vendor,
            webgl_renderer=webgl_renderer,
            timezone=tz_name,
            timezone_offset=tz_offset,
        )

        # Reset random if seeded
        if consistent_seed:
            random.seed()

        self.fingerprint = fp
        return fp

    def get_stealth_scripts(self) -> str:
        """Get JavaScript for fingerprint spoofing."""
        fp = self.fingerprint

        return f"""
        // Navigator overrides
        Object.defineProperty(navigator, 'webdriver', {{
            get: () => undefined
        }});

        Object.defineProperty(navigator, 'hardwareConcurrency', {{
            get: () => {fp.hardware_concurrency}
        }});

        Object.defineProperty(navigator, 'deviceMemory', {{
            get: () => {fp.device_memory}
        }});

        Object.defineProperty(navigator, 'platform', {{
            get: () => '{fp.platform}'
        }});

        Object.defineProperty(navigator, 'languages', {{
            get: () => {fp.languages}
        }});

        // Screen overrides
        Object.defineProperty(screen, 'width', {{
            get: () => {fp.screen_width}
        }});

        Object.defineProperty(screen, 'height', {{
            get: () => {fp.screen_height}
        }});

        Object.defineProperty(screen, 'availWidth', {{
            get: () => {fp.screen_width}
        }});

        Object.defineProperty(screen, 'availHeight', {{
            get: () => {fp.screen_height - 40}
        }});

        Object.defineProperty(screen, 'colorDepth', {{
            get: () => {fp.color_depth}
        }});

        // Timezone
        Date.prototype.getTimezoneOffset = function() {{
            return {fp.timezone_offset};
        }};

        // Chrome property
        window.chrome = {{
            runtime: {{}},
            loadTimes: function() {{}},
            csi: function() {{}},
            app: {{}}
        }};

        // Plugins (make it look like a real browser)
        Object.defineProperty(navigator, 'plugins', {{
            get: () => [
                {{ name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer' }},
                {{ name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai' }},
                {{ name: 'Native Client', filename: 'internal-nacl-plugin' }},
            ]
        }});

        // WebGL spoofing
        const getParameter = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(parameter) {{
            if (parameter === 37445) {{
                return '{fp.webgl_vendor}';
            }}
            if (parameter === 37446) {{
                return '{fp.webgl_renderer}';
            }}
            return getParameter.apply(this, arguments);
        }};

        const getParameter2 = WebGL2RenderingContext.prototype.getParameter;
        WebGL2RenderingContext.prototype.getParameter = function(parameter) {{
            if (parameter === 37445) {{
                return '{fp.webgl_vendor}';
            }}
            if (parameter === 37446) {{
                return '{fp.webgl_renderer}';
            }}
            return getParameter2.apply(this, arguments);
        }};

        // Canvas noise
        {'const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;' if fp.add_canvas_noise else ''}
        {'HTMLCanvasElement.prototype.toDataURL = function(type) {' if fp.add_canvas_noise else ''}
        {'    const canvas = this;' if fp.add_canvas_noise else ''}
        {'    const ctx = canvas.getContext("2d");' if fp.add_canvas_noise else ''}
        {'    if (ctx) {' if fp.add_canvas_noise else ''}
        {'        const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);' if fp.add_canvas_noise else ''}
        {'        for (let i = 0; i < imageData.data.length; i += 4) {' if fp.add_canvas_noise else ''}
        {'            imageData.data[i] ^= (Math.random() * ' + str(fp.canvas_noise_level * 255) + ') | 0;' if fp.add_canvas_noise else ''}
        {'        }' if fp.add_canvas_noise else ''}
        {'        ctx.putImageData(imageData, 0, 0);' if fp.add_canvas_noise else ''}
        {'    }' if fp.add_canvas_noise else ''}
        {'    return originalToDataURL.apply(this, arguments);' if fp.add_canvas_noise else ''}
        {'};' if fp.add_canvas_noise else ''}

        // Permissions
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
                Promise.resolve({{ state: Notification.permission }}) :
                originalQuery(parameters)
        );

        console.log('BAEL stealth mode activated');
        """

    def generate_mouse_path(
        self,
        start: Tuple[int, int],
        end: Tuple[int, int],
        steps: int = 20,
    ) -> List[Tuple[int, int]]:
        """
        Generate human-like mouse movement path.

        Args:
            start: Starting position
            end: Ending position
            steps: Number of points in path

        Returns:
            List of (x, y) positions
        """
        path = []

        if self.mouse_profile.use_bezier_curves:
            # Generate control points
            control_points = [start]

            for _ in range(self.mouse_profile.control_points):
                # Random point near the line
                t = random.random()
                base_x = start[0] + t * (end[0] - start[0])
                base_y = start[1] + t * (end[1] - start[1])

                # Add random offset
                offset = random.uniform(-50, 50)
                control_points.append((
                    int(base_x + offset),
                    int(base_y + offset),
                ))

            control_points.append(end)

            # Generate bezier curve points
            for i in range(steps + 1):
                t = i / steps
                point = self._bezier_point(control_points, t)

                # Add jitter
                if self.mouse_profile.add_jitter and i > 0 and i < steps:
                    jitter = self.mouse_profile.jitter_amplitude
                    point = (
                        int(point[0] + random.uniform(-jitter, jitter)),
                        int(point[1] + random.uniform(-jitter, jitter)),
                    )

                path.append(point)
        else:
            # Linear interpolation with jitter
            for i in range(steps + 1):
                t = i / steps
                x = int(start[0] + t * (end[0] - start[0]))
                y = int(start[1] + t * (end[1] - start[1]))

                if self.mouse_profile.add_jitter and i > 0 and i < steps:
                    jitter = self.mouse_profile.jitter_amplitude
                    x += int(random.uniform(-jitter, jitter))
                    y += int(random.uniform(-jitter, jitter))

                path.append((x, y))

        return path

    def _bezier_point(
        self,
        points: List[Tuple[int, int]],
        t: float,
    ) -> Tuple[int, int]:
        """Calculate point on bezier curve."""
        n = len(points) - 1
        x = sum(
            self._binomial(n, i) * ((1 - t) ** (n - i)) * (t ** i) * points[i][0]
            for i in range(n + 1)
        )
        y = sum(
            self._binomial(n, i) * ((1 - t) ** (n - i)) * (t ** i) * points[i][1]
            for i in range(n + 1)
        )
        return (int(x), int(y))

    def _binomial(self, n: int, k: int) -> int:
        """Calculate binomial coefficient."""
        if k > n:
            return 0
        if k == 0 or k == n:
            return 1

        result = 1
        for i in range(min(k, n - k)):
            result = result * (n - i) // (i + 1)
        return result

    def generate_typing_delays(
        self,
        text: str,
    ) -> List[float]:
        """
        Generate human-like typing delays.

        Args:
            text: Text to type

        Returns:
            List of delays in seconds
        """
        delays = []

        avg_delay = 1.0 / ((self.keyboard_profile.min_cps + self.keyboard_profile.max_cps) / 2)

        for i, char in enumerate(text):
            # Base delay
            delay = random.uniform(
                1.0 / self.keyboard_profile.max_cps,
                1.0 / self.keyboard_profile.min_cps,
            )

            # Extra delay after punctuation
            if i > 0 and text[i-1] in ".!?,;:":
                delay += random.uniform(0.2, 0.5)

            # Extra delay after space (thinking)
            if i > 0 and text[i-1] == " ":
                delay += random.uniform(0.05, 0.15)

            # Random variation
            variation = self.keyboard_profile.delay_variation
            delay *= random.uniform(1 - variation, 1 + variation)

            delays.append(delay)

        return delays

    def detect_protection(
        self,
        html_content: str,
        headers: Dict[str, str],
    ) -> Optional[ProtectionType]:
        """
        Detect what protection service is being used.

        Args:
            html_content: Page HTML
            headers: Response headers

        Returns:
            Detected protection type or None
        """
        # Check headers
        server = headers.get("server", "").lower()
        cf_ray = headers.get("cf-ray")

        if cf_ray or "cloudflare" in server:
            return ProtectionType.CLOUDFLARE

        if "incapsula" in headers.get("x-cdn", "").lower():
            return ProtectionType.IMPERVA

        if "akamai" in server:
            return ProtectionType.AKAMAI

        # Check HTML content
        content_lower = html_content.lower()

        if "datadome" in content_lower or "dd.js" in content_lower:
            return ProtectionType.DATADOME

        if "perimeterx" in content_lower or "_pxhd" in content_lower:
            return ProtectionType.PERIMETERX

        if "kasada" in content_lower:
            return ProtectionType.KASADA

        if "g-recaptcha" in content_lower:
            return ProtectionType.RECAPTCHA

        if "h-captcha" in content_lower:
            return ProtectionType.HCAPTCHA

        return None

    def get_headers_for_protection(
        self,
        protection: ProtectionType,
    ) -> Dict[str, str]:
        """Get optimized headers for specific protection."""
        base_headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": f"{self.fingerprint.language},en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
        }

        if protection == ProtectionType.CLOUDFLARE:
            base_headers["Cache-Control"] = "max-age=0"

        return base_headers


def demo():
    """Demonstrate anti-detection."""
    print("=" * 60)
    print("BAEL Anti-Detection Demo")
    print("=" * 60)

    ad = AntiDetection(level=EvasionLevel.STANDARD)

    # Generate fingerprint
    fp = ad.generate_fingerprint(consistent_seed="demo_session")

    print(f"\nGenerated fingerprint:")
    print(f"  Screen: {fp.screen_width}x{fp.screen_height}")
    print(f"  Cores: {fp.hardware_concurrency}")
    print(f"  Memory: {fp.device_memory}GB")
    print(f"  Timezone: {fp.timezone}")
    print(f"  WebGL: {fp.webgl_renderer[:50]}...")

    # Generate mouse path
    path = ad.generate_mouse_path((100, 100), (500, 300), steps=10)
    print(f"\nMouse path ({len(path)} points):")
    print(f"  Start: {path[0]}")
    print(f"  End: {path[-1]}")

    # Generate typing delays
    delays = ad.generate_typing_delays("Hello")
    print(f"\nTyping delays for 'Hello': {[f'{d:.3f}s' for d in delays]}")


if __name__ == "__main__":
    demo()

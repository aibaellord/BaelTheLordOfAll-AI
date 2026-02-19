"""
BAEL Captcha Solver
====================

Multi-provider captcha solving integration.
Supports multiple solving services and captcha types.

Features:
- Multiple solver providers
- reCAPTCHA v2/v3 support
- hCaptcha support
- Image captcha OCR
- FunCaptcha support
- Turnstile support
- Cost optimization
"""

import asyncio
import base64
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class CaptchaType(Enum):
    """Captcha types."""
    RECAPTCHA_V2 = "recaptcha_v2"
    RECAPTCHA_V3 = "recaptcha_v3"
    RECAPTCHA_V2_INVISIBLE = "recaptcha_v2_invisible"
    HCAPTCHA = "hcaptcha"
    FUNCAPTCHA = "funcaptcha"
    TURNSTILE = "turnstile"
    IMAGE_TO_TEXT = "image_to_text"
    GEETEST = "geetest"
    CAPY = "capy"
    KEYCAPTCHA = "keycaptcha"


class SolverProvider(Enum):
    """Captcha solver providers."""
    # Paid services
    TWOCAPTCHA = "2captcha"
    ANTICAPTCHA = "anticaptcha"
    CAPSOLVER = "capsolver"
    CAPMONSTER = "capmonster"
    DEATHBYCAPTCHA = "deathbycaptcha"

    # Free/self-hosted
    LOCAL_OCR = "local_ocr"
    TESSERACT = "tesseract"
    NOPECHA = "nopecha"


@dataclass
class SolverConfig:
    """Solver configuration."""
    provider: SolverProvider = SolverProvider.TWOCAPTCHA
    api_key: str = ""

    # Timeouts
    max_wait_time: int = 120  # seconds
    poll_interval: int = 5

    # Retries
    max_retries: int = 3

    # Cost limits
    max_cost_per_solve: float = 0.01
    daily_budget: float = 1.0


@dataclass
class CaptchaTask:
    """A captcha solving task."""
    captcha_type: CaptchaType
    site_key: Optional[str] = None
    page_url: Optional[str] = None
    image_base64: Optional[str] = None

    # reCAPTCHA v3 specific
    action: str = "verify"
    min_score: float = 0.3

    # Enterprise options
    enterprise: bool = False
    api_domain: Optional[str] = None

    # Additional data
    data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CaptchaResult:
    """Result of captcha solving."""
    success: bool
    solution: Optional[str] = None
    task_id: Optional[str] = None

    # Timing
    solve_time_ms: float = 0.0

    # Cost
    cost: float = 0.0

    # Provider info
    provider: Optional[SolverProvider] = None

    # Error
    error: Optional[str] = None


class CaptchaSolver:
    """
    Multi-provider captcha solver for BAEL.
    """

    # Provider API endpoints
    ENDPOINTS = {
        SolverProvider.TWOCAPTCHA: {
            "submit": "https://2captcha.com/in.php",
            "result": "https://2captcha.com/res.php",
        },
        SolverProvider.ANTICAPTCHA: {
            "submit": "https://api.anti-captcha.com/createTask",
            "result": "https://api.anti-captcha.com/getTaskResult",
        },
        SolverProvider.CAPSOLVER: {
            "submit": "https://api.capsolver.com/createTask",
            "result": "https://api.capsolver.com/getTaskResult",
        },
        SolverProvider.CAPMONSTER: {
            "submit": "https://api.capmonster.cloud/createTask",
            "result": "https://api.capmonster.cloud/getTaskResult",
        },
    }

    # Cost per captcha type (approximate)
    COSTS = {
        CaptchaType.RECAPTCHA_V2: 0.003,
        CaptchaType.RECAPTCHA_V3: 0.004,
        CaptchaType.HCAPTCHA: 0.003,
        CaptchaType.FUNCAPTCHA: 0.005,
        CaptchaType.TURNSTILE: 0.003,
        CaptchaType.IMAGE_TO_TEXT: 0.001,
    }

    def __init__(
        self,
        configs: Optional[List[SolverConfig]] = None,
    ):
        self.configs = configs or []
        self.config_by_provider: Dict[SolverProvider, SolverConfig] = {
            c.provider: c for c in self.configs
        }

        # Daily spending tracking
        self.daily_spending: Dict[SolverProvider, float] = {}
        self.spending_reset_date = datetime.now().date()

        # Stats
        self.stats = {
            "total_solves": 0,
            "successful_solves": 0,
            "failed_solves": 0,
            "total_cost": 0.0,
            "total_time_ms": 0.0,
        }

    def add_provider(
        self,
        provider: SolverProvider,
        api_key: str,
        **kwargs,
    ) -> None:
        """Add a solver provider."""
        config = SolverConfig(
            provider=provider,
            api_key=api_key,
            **kwargs,
        )
        self.configs.append(config)
        self.config_by_provider[provider] = config

    def _reset_daily_spending_if_needed(self) -> None:
        """Reset daily spending if date changed."""
        today = datetime.now().date()
        if today > self.spending_reset_date:
            self.daily_spending = {}
            self.spending_reset_date = today

    def _check_budget(
        self,
        provider: SolverProvider,
        estimated_cost: float,
    ) -> bool:
        """Check if we're within budget."""
        self._reset_daily_spending_if_needed()

        config = self.config_by_provider.get(provider)
        if not config:
            return False

        current = self.daily_spending.get(provider, 0.0)
        return (current + estimated_cost) <= config.daily_budget

    def _record_spending(
        self,
        provider: SolverProvider,
        cost: float,
    ) -> None:
        """Record spending."""
        self._reset_daily_spending_if_needed()

        current = self.daily_spending.get(provider, 0.0)
        self.daily_spending[provider] = current + cost
        self.stats["total_cost"] += cost

    async def solve(
        self,
        task: CaptchaTask,
        preferred_provider: Optional[SolverProvider] = None,
    ) -> CaptchaResult:
        """
        Solve a captcha.

        Args:
            task: Captcha task to solve
            preferred_provider: Preferred provider (optional)

        Returns:
            CaptchaResult
        """
        self.stats["total_solves"] += 1

        # Estimate cost
        estimated_cost = self.COSTS.get(task.captcha_type, 0.005)

        # Select provider
        provider = None
        config = None

        if preferred_provider and preferred_provider in self.config_by_provider:
            if self._check_budget(preferred_provider, estimated_cost):
                provider = preferred_provider
                config = self.config_by_provider[preferred_provider]

        if not provider:
            # Find first available provider within budget
            for p, c in self.config_by_provider.items():
                if c.api_key and self._check_budget(p, estimated_cost):
                    provider = p
                    config = c
                    break

        if not provider or not config:
            self.stats["failed_solves"] += 1
            return CaptchaResult(
                success=False,
                error="No available solver provider or budget exceeded",
            )

        # Solve based on provider
        start_time = time.monotonic()

        try:
            if provider == SolverProvider.TWOCAPTCHA:
                result = await self._solve_2captcha(task, config)
            elif provider == SolverProvider.ANTICAPTCHA:
                result = await self._solve_anticaptcha(task, config)
            elif provider == SolverProvider.CAPSOLVER:
                result = await self._solve_capsolver(task, config)
            elif provider == SolverProvider.LOCAL_OCR:
                result = await self._solve_local_ocr(task, config)
            else:
                result = CaptchaResult(
                    success=False,
                    error=f"Provider not implemented: {provider.value}",
                )

            elapsed = (time.monotonic() - start_time) * 1000
            result.solve_time_ms = elapsed
            result.provider = provider

            if result.success:
                self.stats["successful_solves"] += 1
                self.stats["total_time_ms"] += elapsed
                self._record_spending(provider, result.cost or estimated_cost)
            else:
                self.stats["failed_solves"] += 1

            return result

        except Exception as e:
            self.stats["failed_solves"] += 1
            return CaptchaResult(
                success=False,
                error=str(e),
                provider=provider,
            )

    async def _solve_2captcha(
        self,
        task: CaptchaTask,
        config: SolverConfig,
    ) -> CaptchaResult:
        """Solve using 2captcha."""
        try:
            import httpx
        except ImportError:
            return CaptchaResult(success=False, error="httpx not installed")

        endpoints = self.ENDPOINTS[SolverProvider.TWOCAPTCHA]

        # Prepare submit data
        submit_data = {
            "key": config.api_key,
            "json": 1,
        }

        if task.captcha_type == CaptchaType.RECAPTCHA_V2:
            submit_data.update({
                "method": "userrecaptcha",
                "googlekey": task.site_key,
                "pageurl": task.page_url,
            })
            if task.data.get("invisible"):
                submit_data["invisible"] = 1

        elif task.captcha_type == CaptchaType.RECAPTCHA_V3:
            submit_data.update({
                "method": "userrecaptcha",
                "version": "v3",
                "googlekey": task.site_key,
                "pageurl": task.page_url,
                "action": task.action,
                "min_score": task.min_score,
            })

        elif task.captcha_type == CaptchaType.HCAPTCHA:
            submit_data.update({
                "method": "hcaptcha",
                "sitekey": task.site_key,
                "pageurl": task.page_url,
            })

        elif task.captcha_type == CaptchaType.IMAGE_TO_TEXT:
            submit_data.update({
                "method": "base64",
                "body": task.image_base64,
            })

        elif task.captcha_type == CaptchaType.TURNSTILE:
            submit_data.update({
                "method": "turnstile",
                "sitekey": task.site_key,
                "pageurl": task.page_url,
            })

        else:
            return CaptchaResult(
                success=False,
                error=f"Captcha type not supported by 2captcha: {task.captcha_type.value}",
            )

        async with httpx.AsyncClient(timeout=30) as client:
            # Submit task
            response = await client.post(endpoints["submit"], data=submit_data)
            result = response.json()

            if result.get("status") != 1:
                return CaptchaResult(
                    success=False,
                    error=result.get("error_text", "Unknown error"),
                )

            task_id = result.get("request")

            # Poll for result
            for _ in range(config.max_wait_time // config.poll_interval):
                await asyncio.sleep(config.poll_interval)

                response = await client.get(endpoints["result"], params={
                    "key": config.api_key,
                    "action": "get",
                    "id": task_id,
                    "json": 1,
                })

                result = response.json()

                if result.get("status") == 1:
                    return CaptchaResult(
                        success=True,
                        solution=result.get("request"),
                        task_id=task_id,
                        cost=self.COSTS.get(task.captcha_type, 0.003),
                    )

                if result.get("request") != "CAPCHA_NOT_READY":
                    return CaptchaResult(
                        success=False,
                        error=result.get("error_text", "Unknown error"),
                        task_id=task_id,
                    )

            return CaptchaResult(
                success=False,
                error="Timeout waiting for solution",
                task_id=task_id,
            )

    async def _solve_anticaptcha(
        self,
        task: CaptchaTask,
        config: SolverConfig,
    ) -> CaptchaResult:
        """Solve using Anti-Captcha."""
        try:
            import httpx
        except ImportError:
            return CaptchaResult(success=False, error="httpx not installed")

        endpoints = self.ENDPOINTS[SolverProvider.ANTICAPTCHA]

        # Map captcha type to task type
        task_type_map = {
            CaptchaType.RECAPTCHA_V2: "RecaptchaV2TaskProxyless",
            CaptchaType.RECAPTCHA_V3: "RecaptchaV3TaskProxyless",
            CaptchaType.HCAPTCHA: "HCaptchaTaskProxyless",
            CaptchaType.IMAGE_TO_TEXT: "ImageToTextTask",
            CaptchaType.TURNSTILE: "TurnstileTaskProxyless",
        }

        ac_task_type = task_type_map.get(task.captcha_type)
        if not ac_task_type:
            return CaptchaResult(
                success=False,
                error=f"Captcha type not supported: {task.captcha_type.value}",
            )

        # Build task
        ac_task: Dict[str, Any] = {"type": ac_task_type}

        if task.captcha_type in (CaptchaType.RECAPTCHA_V2, CaptchaType.RECAPTCHA_V3):
            ac_task["websiteURL"] = task.page_url
            ac_task["websiteKey"] = task.site_key
            if task.captcha_type == CaptchaType.RECAPTCHA_V3:
                ac_task["pageAction"] = task.action
                ac_task["minScore"] = task.min_score

        elif task.captcha_type == CaptchaType.HCAPTCHA:
            ac_task["websiteURL"] = task.page_url
            ac_task["websiteKey"] = task.site_key

        elif task.captcha_type == CaptchaType.IMAGE_TO_TEXT:
            ac_task["body"] = task.image_base64

        async with httpx.AsyncClient(timeout=30) as client:
            # Submit
            response = await client.post(endpoints["submit"], json={
                "clientKey": config.api_key,
                "task": ac_task,
            })
            result = response.json()

            if result.get("errorId") != 0:
                return CaptchaResult(
                    success=False,
                    error=result.get("errorDescription", "Unknown error"),
                )

            task_id = result.get("taskId")

            # Poll
            for _ in range(config.max_wait_time // config.poll_interval):
                await asyncio.sleep(config.poll_interval)

                response = await client.post(endpoints["result"], json={
                    "clientKey": config.api_key,
                    "taskId": task_id,
                })

                result = response.json()

                if result.get("status") == "ready":
                    solution_data = result.get("solution", {})
                    solution = (
                        solution_data.get("gRecaptchaResponse") or
                        solution_data.get("token") or
                        solution_data.get("text")
                    )

                    return CaptchaResult(
                        success=True,
                        solution=solution,
                        task_id=str(task_id),
                        cost=result.get("cost", self.COSTS.get(task.captcha_type, 0.003)),
                    )

                if result.get("errorId") != 0:
                    return CaptchaResult(
                        success=False,
                        error=result.get("errorDescription", "Unknown error"),
                        task_id=str(task_id),
                    )

            return CaptchaResult(
                success=False,
                error="Timeout waiting for solution",
                task_id=str(task_id),
            )

    async def _solve_capsolver(
        self,
        task: CaptchaTask,
        config: SolverConfig,
    ) -> CaptchaResult:
        """Solve using CapSolver (similar to AntiCaptcha API)."""
        # CapSolver uses similar API structure
        return await self._solve_anticaptcha(task, config)

    async def _solve_local_ocr(
        self,
        task: CaptchaTask,
        config: SolverConfig,
    ) -> CaptchaResult:
        """Solve image captcha using local OCR."""
        if task.captcha_type != CaptchaType.IMAGE_TO_TEXT:
            return CaptchaResult(
                success=False,
                error="Local OCR only supports image captchas",
            )

        try:
            import io

            import pytesseract
            from PIL import Image

            # Decode image
            image_data = base64.b64decode(task.image_base64)
            image = Image.open(io.BytesIO(image_data))

            # Run OCR
            text = pytesseract.image_to_string(image).strip()

            return CaptchaResult(
                success=bool(text),
                solution=text,
                cost=0.0,
            )

        except ImportError:
            return CaptchaResult(
                success=False,
                error="pytesseract or PIL not installed",
            )
        except Exception as e:
            return CaptchaResult(
                success=False,
                error=str(e),
            )

    def get_balance(self, provider: SolverProvider) -> Optional[float]:
        """Get account balance (sync wrapper for demo)."""
        # Would need async implementation for actual API calls
        return None

    def get_stats(self) -> Dict[str, Any]:
        """Get solver statistics."""
        avg_time = 0.0
        if self.stats["successful_solves"] > 0:
            avg_time = self.stats["total_time_ms"] / self.stats["successful_solves"]

        return {
            **self.stats,
            "providers_configured": len(self.configs),
            "avg_solve_time_ms": avg_time,
            "daily_spending": dict(self.daily_spending),
        }


def demo():
    """Demonstrate captcha solver."""
    print("=" * 60)
    print("BAEL Captcha Solver Demo")
    print("=" * 60)

    solver = CaptchaSolver()

    # Add demo provider
    solver.add_provider(
        SolverProvider.TWOCAPTCHA,
        api_key="demo_key",
        daily_budget=1.0,
    )

    print(f"\nProviders configured: {len(solver.configs)}")

    # Create sample task
    task = CaptchaTask(
        captcha_type=CaptchaType.RECAPTCHA_V2,
        site_key="6Le-wvkSAAAAAPBMRTvw0Q4Muexq9bi0DJwx_mJ-",
        page_url="https://example.com",
    )

    print(f"\nSample task:")
    print(f"  Type: {task.captcha_type.value}")
    print(f"  Site key: {task.site_key[:20]}...")

    print(f"\nStats: {solver.get_stats()}")


if __name__ == "__main__":
    demo()

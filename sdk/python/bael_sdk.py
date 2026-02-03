"""
BAEL Python SDK
Client library for interacting with BAEL from external applications.
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, AsyncIterator, Callable, Dict, List, Optional, Union
from uuid import uuid4

import aiohttp

logger = logging.getLogger("BAEL.SDK")


# =============================================================================
# TYPES
# =============================================================================

class OperatingMode(Enum):
    """BAEL operating modes."""
    MINIMAL = "minimal"
    STANDARD = "standard"
    MAXIMUM = "maximum"
    AUTONOMOUS = "autonomous"


@dataclass
class Message:
    """Chat message."""
    role: str
    content: str

    def to_dict(self) -> Dict:
        return {"role": self.role, "content": self.content}


@dataclass
class ChatResponse:
    """Response from chat endpoint."""
    id: str
    response: str
    model_used: str
    tokens_used: int
    execution_time_ms: float
    persona: Optional[str] = None


@dataclass
class Task:
    """Background task."""
    id: str
    status: str
    result: Optional[Any] = None
    error: Optional[str] = None


@dataclass
class HealthStatus:
    """Health check response."""
    status: str
    version: str
    uptime_seconds: float
    components: Dict[str, str]


# =============================================================================
# EXCEPTIONS
# =============================================================================

class BAELError(Exception):
    """Base exception for BAEL SDK."""
    pass


class APIError(BAELError):
    """API request error."""
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"API Error {status_code}: {message}")


class AuthenticationError(BAELError):
    """Authentication failed."""
    pass


class RateLimitError(BAELError):
    """Rate limit exceeded."""
    pass


# =============================================================================
# BAEL CLIENT
# =============================================================================

class BAELClient:
    """
    Asynchronous client for interacting with BAEL API.

    Example usage:
        >>> client = BAELClient(api_url="http://localhost:8000")
        >>> async with client:
        ...     response = await client.chat("Hello, BAEL!")
        ...     print(response.response)
    """

    def __init__(
        self,
        api_url: str = "http://localhost:8000",
        api_key: Optional[str] = None,
        timeout: float = 300.0
    ):
        """
        Initialize BAEL client.

        Args:
            api_url: Base URL of BAEL API
            api_key: Optional API key for authentication
            timeout: Request timeout in seconds
        """
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self.timeout = aiohttp.ClientTimeout(total=timeout)

        self._session: Optional[aiohttp.ClientSession] = None
        self._headers = {}

        if api_key:
            self._headers["X-API-Key"] = api_key

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def connect(self):
        """Establish connection to API."""
        self._session = aiohttp.ClientSession(
            timeout=self.timeout,
            headers=self._headers
        )
        logger.info(f"Connected to BAEL API: {self.api_url}")

    async def close(self):
        """Close connection to API."""
        if self._session:
            await self._session.close()
            self._session = None
        logger.info("Disconnected from BAEL API")

    def _ensure_session(self):
        """Ensure session is active."""
        if not self._session:
            raise BAELError("Client not connected. Use async with or call connect() first.")

    async def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Make HTTP request to API."""
        self._ensure_session()

        url = f"{self.api_url}{endpoint}"

        try:
            async with self._session.request(method, url, **kwargs) as response:
                if response.status == 401:
                    raise AuthenticationError("Invalid API key")
                elif response.status == 429:
                    raise RateLimitError("Rate limit exceeded")
                elif response.status >= 400:
                    text = await response.text()
                    raise APIError(response.status, text)

                return await response.json()

        except aiohttp.ClientError as e:
            raise BAELError(f"Request failed: {e}")

    # =========================================================================
    # CHAT API
    # =========================================================================

    async def chat(
        self,
        message: Union[str, List[Message]],
        mode: OperatingMode = OperatingMode.STANDARD,
        persona: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: bool = False
    ) -> ChatResponse:
        """
        Send a chat message to BAEL.

        Args:
            message: Single message string or list of Message objects
            mode: Operating mode
            persona: Persona to use
            model: Preferred model
            temperature: Temperature (0-2)
            max_tokens: Maximum tokens to generate
            stream: Enable streaming (not yet implemented)

        Returns:
            ChatResponse with BAEL's response
        """
        # Convert message to proper format
        if isinstance(message, str):
            messages = [Message(role="user", content=message)]
        else:
            messages = message

        payload = {
            "messages": [msg.to_dict() for msg in messages],
            "mode": mode.value,
            "stream": stream
        }

        if persona:
            payload["persona"] = persona
        if model:
            payload["model"] = model
        if temperature is not None:
            payload["temperature"] = temperature
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        data = await self._request("POST", "/v1/chat", json=payload)

        return ChatResponse(**data)

    async def chat_stream(
        self,
        message: Union[str, List[Message]],
        mode: OperatingMode = OperatingMode.STANDARD,
        persona: Optional[str] = None
    ) -> AsyncIterator[str]:
        """
        Stream chat responses from BAEL.

        Args:
            message: Message(s) to send
            mode: Operating mode
            persona: Persona to use

        Yields:
            Response chunks as they arrive
        """
        self._ensure_session()

        # Convert message
        if isinstance(message, str):
            messages = [Message(role="user", content=message)]
        else:
            messages = message

        payload = {
            "messages": [msg.to_dict() for msg in messages],
            "mode": mode.value,
            "stream": True
        }

        if persona:
            payload["persona"] = persona

        url = f"{self.api_url}/v1/chat"

        async with self._session.post(url, json=payload) as response:
            if response.status != 200:
                raise APIError(response.status, await response.text())

            async for line in response.content:
                if line:
                    yield line.decode('utf-8')

    # =========================================================================
    # TASK API
    # =========================================================================

    async def submit_task(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None,
        priority: str = "normal",
        deadline: Optional[datetime] = None
    ) -> Task:
        """
        Submit an autonomous task.

        Args:
            task: Task description
            context: Optional context data
            priority: Task priority (critical, high, normal, low, background)
            deadline: Optional deadline

        Returns:
            Task object with task ID
        """
        payload = {
            "task": task,
            "context": context or {},
            "priority": priority
        }

        if deadline:
            payload["deadline"] = deadline.isoformat()

        data = await self._request("POST", "/v1/task", json=payload)

        return Task(**data)

    async def get_task(self, task_id: str) -> Task:
        """
        Get task status.

        Args:
            task_id: Task ID

        Returns:
            Task object with current status
        """
        data = await self._request("GET", f"/v1/task/{task_id}")
        return Task(**data)

    async def wait_for_task(
        self,
        task_id: str,
        poll_interval: float = 1.0,
        timeout: Optional[float] = None
    ) -> Task:
        """
        Wait for task to complete.

        Args:
            task_id: Task ID
            poll_interval: Seconds between status checks
            timeout: Maximum seconds to wait

        Returns:
            Completed Task object
        """
        start_time = datetime.now()

        while True:
            task = await self.get_task(task_id)

            if task.status in ["completed", "failed", "cancelled"]:
                return task

            if timeout:
                elapsed = (datetime.now() - start_time).total_seconds()
                if elapsed >= timeout:
                    raise TimeoutError(f"Task {task_id} did not complete within {timeout}s")

            await asyncio.sleep(poll_interval)

    # =========================================================================
    # SYSTEM API
    # =========================================================================

    async def health(self) -> HealthStatus:
        """
        Check system health.

        Returns:
            HealthStatus object
        """
        data = await self._request("GET", "/health")
        return HealthStatus(**data)

    async def list_personas(self) -> List[Dict[str, str]]:
        """
        List available personas.

        Returns:
            List of persona definitions
        """
        data = await self._request("GET", "/v1/personas")
        return data.get("personas", [])

    async def list_capabilities(self) -> Dict[str, List[str]]:
        """
        List capabilities by mode.

        Returns:
            Dictionary mapping modes to capabilities
        """
        data = await self._request("GET", "/v1/capabilities")
        return data.get("modes", {})


# =============================================================================
# SYNCHRONOUS WRAPPER
# =============================================================================

class BAELSyncClient:
    """
    Synchronous wrapper for BAELClient.

    Example usage:
        >>> client = BAELSyncClient(api_url="http://localhost:8000")
        >>> response = client.chat("Hello, BAEL!")
        >>> print(response.response)
    """

    def __init__(
        self,
        api_url: str = "http://localhost:8000",
        api_key: Optional[str] = None,
        timeout: float = 300.0
    ):
        self._async_client = BAELClient(api_url, api_key, timeout)
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def _run_async(self, coro):
        """Run async coroutine synchronously."""
        if self._loop is None:
            self._loop = asyncio.new_event_loop()
        return self._loop.run_until_complete(coro)

    def __enter__(self):
        """Context manager entry."""
        self._run_async(self._async_client.connect())
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self._run_async(self._async_client.close())
        if self._loop:
            self._loop.close()
            self._loop = None

    def chat(
        self,
        message: Union[str, List[Message]],
        mode: OperatingMode = OperatingMode.STANDARD,
        **kwargs
    ) -> ChatResponse:
        """Send a chat message."""
        return self._run_async(
            self._async_client.chat(message, mode, **kwargs)
        )

    def submit_task(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Task:
        """Submit an autonomous task."""
        return self._run_async(
            self._async_client.submit_task(task, context, **kwargs)
        )

    def get_task(self, task_id: str) -> Task:
        """Get task status."""
        return self._run_async(self._async_client.get_task(task_id))

    def wait_for_task(self, task_id: str, **kwargs) -> Task:
        """Wait for task to complete."""
        return self._run_async(
            self._async_client.wait_for_task(task_id, **kwargs)
        )

    def health(self) -> HealthStatus:
        """Check system health."""
        return self._run_async(self._async_client.health())

    def list_personas(self) -> List[Dict[str, str]]:
        """List available personas."""
        return self._run_async(self._async_client.list_personas())

    def list_capabilities(self) -> Dict[str, List[str]]:
        """List capabilities by mode."""
        return self._run_async(self._async_client.list_capabilities())


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

async def quick_chat(
    message: str,
    api_url: str = "http://localhost:8000",
    **kwargs
) -> str:
    """
    Quick chat without managing client lifecycle.

    Args:
        message: Message to send
        api_url: BAEL API URL
        **kwargs: Additional arguments passed to chat()

    Returns:
        Response string
    """
    async with BAELClient(api_url) as client:
        response = await client.chat(message, **kwargs)
        return response.response


def quick_chat_sync(
    message: str,
    api_url: str = "http://localhost:8000",
    **kwargs
) -> str:
    """
    Quick synchronous chat.

    Args:
        message: Message to send
        api_url: BAEL API URL
        **kwargs: Additional arguments passed to chat()

    Returns:
        Response string
    """
    with BAELSyncClient(api_url) as client:
        response = client.chat(message, **kwargs)
        return response.response


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Client classes
    'BAELClient',
    'BAELSyncClient',

    # Types
    'Message',
    'ChatResponse',
    'Task',
    'HealthStatus',
    'OperatingMode',

    # Exceptions
    'BAELError',
    'APIError',
    'AuthenticationError',
    'RateLimitError',

    # Convenience functions
    'quick_chat',
    'quick_chat_sync'
]

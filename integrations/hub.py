"""
BAEL - Integration Hub
Central hub for all external integrations and services.

Supports:
- LLM Providers (OpenAI, Anthropic, Google, OpenRouter, Ollama)
- Vector Databases (ChromaDB, Pinecone, Weaviate, Qdrant)
- Search Engines (Google, Bing, DuckDuckGo, Tavily)
- Code Platforms (GitHub, GitLab, Bitbucket)
- Communication (Slack, Discord, Email)
- Storage (S3, GCS, Azure Blob)
"""

import asyncio
import hashlib
import json
import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS & TYPES
# =============================================================================

class IntegrationType(Enum):
    """Types of integrations."""
    LLM = "llm"
    VECTOR_DB = "vector_db"
    SEARCH = "search"
    CODE_PLATFORM = "code_platform"
    COMMUNICATION = "communication"
    STORAGE = "storage"
    DATABASE = "database"
    MONITORING = "monitoring"
    CUSTOM = "custom"


class ConnectionStatus(Enum):
    """Connection status."""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    RATE_LIMITED = "rate_limited"


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class IntegrationConfig:
    """Configuration for an integration."""
    name: str
    type: IntegrationType
    enabled: bool = True
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    options: Dict[str, Any] = field(default_factory=dict)
    rate_limit: Optional[int] = None  # requests per minute
    timeout: int = 30
    retry_attempts: int = 3


@dataclass
class IntegrationHealth:
    """Health status of an integration."""
    name: str
    status: ConnectionStatus
    latency_ms: float = 0.0
    last_check: datetime = field(default_factory=datetime.now)
    error_message: Optional[str] = None
    requests_today: int = 0
    errors_today: int = 0


# =============================================================================
# ABSTRACT INTEGRATION
# =============================================================================

class Integration(ABC):
    """Base class for all integrations."""

    def __init__(self, config: IntegrationConfig):
        self.config = config
        self.status = ConnectionStatus.DISCONNECTED
        self._request_count = 0
        self._error_count = 0
        self._last_request: Optional[datetime] = None

    @property
    def name(self) -> str:
        return self.config.name

    @property
    def type(self) -> IntegrationType:
        return self.config.type

    @abstractmethod
    async def connect(self) -> bool:
        """Establish connection to the service."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the service."""
        pass

    @abstractmethod
    async def health_check(self) -> IntegrationHealth:
        """Check health of the integration."""
        pass

    async def _rate_limit_check(self) -> bool:
        """Check if rate limited."""
        if not self.config.rate_limit:
            return True

        # Simple rate limiting
        if self._last_request:
            elapsed = (datetime.now() - self._last_request).total_seconds()
            min_interval = 60.0 / self.config.rate_limit
            if elapsed < min_interval:
                await asyncio.sleep(min_interval - elapsed)

        self._last_request = datetime.now()
        return True


# =============================================================================
# LLM INTEGRATIONS
# =============================================================================

class LLMIntegration(Integration):
    """Base class for LLM integrations."""

    @abstractmethod
    async def complete(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate a completion."""
        pass

    @abstractmethod
    async def embed(
        self,
        texts: List[str],
        model: Optional[str] = None
    ) -> List[List[float]]:
        """Generate embeddings."""
        pass


class OpenAIIntegration(LLMIntegration):
    """OpenAI API integration."""

    def __init__(self, config: IntegrationConfig):
        super().__init__(config)
        self.client = None

    async def connect(self) -> bool:
        try:
            import openai
            self.client = openai.AsyncOpenAI(
                api_key=self.config.api_key or os.getenv("OPENAI_API_KEY"),
                base_url=self.config.api_base
            )
            self.status = ConnectionStatus.CONNECTED
            return True
        except Exception as e:
            logger.error(f"OpenAI connection failed: {e}")
            self.status = ConnectionStatus.ERROR
            return False

    async def disconnect(self) -> None:
        self.client = None
        self.status = ConnectionStatus.DISCONNECTED

    async def health_check(self) -> IntegrationHealth:
        start = datetime.now()
        try:
            if self.client:
                await self.client.models.list()
                latency = (datetime.now() - start).total_seconds() * 1000
                return IntegrationHealth(
                    name=self.name,
                    status=ConnectionStatus.CONNECTED,
                    latency_ms=latency
                )
        except Exception as e:
            return IntegrationHealth(
                name=self.name,
                status=ConnectionStatus.ERROR,
                error_message=str(e)
            )
        return IntegrationHealth(
            name=self.name,
            status=ConnectionStatus.DISCONNECTED
        )

    async def complete(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs
    ) -> Dict[str, Any]:
        if not self.client:
            raise RuntimeError("Not connected")

        await self._rate_limit_check()

        response = await self.client.chat.completions.create(
            model=model or self.config.options.get("default_model", "gpt-4"),
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )

        self._request_count += 1

        return {
            "content": response.choices[0].message.content,
            "model": response.model,
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            },
            "finish_reason": response.choices[0].finish_reason
        }

    async def embed(
        self,
        texts: List[str],
        model: Optional[str] = None
    ) -> List[List[float]]:
        if not self.client:
            raise RuntimeError("Not connected")

        response = await self.client.embeddings.create(
            model=model or "text-embedding-3-small",
            input=texts
        )

        return [item.embedding for item in response.data]


class AnthropicIntegration(LLMIntegration):
    """Anthropic Claude API integration."""

    def __init__(self, config: IntegrationConfig):
        super().__init__(config)
        self.client = None

    async def connect(self) -> bool:
        try:
            import anthropic
            self.client = anthropic.AsyncAnthropic(
                api_key=self.config.api_key or os.getenv("ANTHROPIC_API_KEY")
            )
            self.status = ConnectionStatus.CONNECTED
            return True
        except Exception as e:
            logger.error(f"Anthropic connection failed: {e}")
            self.status = ConnectionStatus.ERROR
            return False

    async def disconnect(self) -> None:
        self.client = None
        self.status = ConnectionStatus.DISCONNECTED

    async def health_check(self) -> IntegrationHealth:
        return IntegrationHealth(
            name=self.name,
            status=self.status
        )

    async def complete(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs
    ) -> Dict[str, Any]:
        if not self.client:
            raise RuntimeError("Not connected")

        await self._rate_limit_check()

        # Extract system message
        system = ""
        chat_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system = msg["content"]
            else:
                chat_messages.append(msg)

        response = await self.client.messages.create(
            model=model or self.config.options.get("default_model", "claude-sonnet-4-20250514"),
            system=system,
            messages=chat_messages,
            temperature=temperature,
            max_tokens=max_tokens
        )

        self._request_count += 1

        return {
            "content": response.content[0].text,
            "model": response.model,
            "usage": {
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens
            },
            "finish_reason": response.stop_reason
        }

    async def embed(
        self,
        texts: List[str],
        model: Optional[str] = None
    ) -> List[List[float]]:
        raise NotImplementedError("Anthropic does not provide embeddings")


class OllamaIntegration(LLMIntegration):
    """Ollama local LLM integration."""

    def __init__(self, config: IntegrationConfig):
        super().__init__(config)
        self.base_url = config.api_base or "http://localhost:11434"

    async def connect(self) -> bool:
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/api/tags") as response:
                    if response.status == 200:
                        self.status = ConnectionStatus.CONNECTED
                        return True
        except Exception as e:
            logger.error(f"Ollama connection failed: {e}")

        self.status = ConnectionStatus.ERROR
        return False

    async def disconnect(self) -> None:
        self.status = ConnectionStatus.DISCONNECTED

    async def health_check(self) -> IntegrationHealth:
        start = datetime.now()
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/api/tags") as response:
                    if response.status == 200:
                        latency = (datetime.now() - start).total_seconds() * 1000
                        return IntegrationHealth(
                            name=self.name,
                            status=ConnectionStatus.CONNECTED,
                            latency_ms=latency
                        )
        except Exception as e:
            return IntegrationHealth(
                name=self.name,
                status=ConnectionStatus.ERROR,
                error_message=str(e)
            )
        return IntegrationHealth(
            name=self.name,
            status=ConnectionStatus.DISCONNECTED
        )

    async def complete(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs
    ) -> Dict[str, Any]:
        import aiohttp

        await self._rate_limit_check()

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": model or self.config.options.get("default_model", "llama2"),
                    "messages": messages,
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "num_predict": max_tokens
                    }
                }
            ) as response:
                data = await response.json()

        self._request_count += 1

        return {
            "content": data.get("message", {}).get("content", ""),
            "model": data.get("model", model),
            "usage": {
                "prompt_tokens": data.get("prompt_eval_count", 0),
                "completion_tokens": data.get("eval_count", 0),
                "total_tokens": data.get("prompt_eval_count", 0) + data.get("eval_count", 0)
            },
            "finish_reason": "stop"
        }

    async def embed(
        self,
        texts: List[str],
        model: Optional[str] = None
    ) -> List[List[float]]:
        import aiohttp

        embeddings = []
        async with aiohttp.ClientSession() as session:
            for text in texts:
                async with session.post(
                    f"{self.base_url}/api/embeddings",
                    json={
                        "model": model or "nomic-embed-text",
                        "prompt": text
                    }
                ) as response:
                    data = await response.json()
                    embeddings.append(data.get("embedding", []))

        return embeddings


# =============================================================================
# VECTOR DATABASE INTEGRATIONS
# =============================================================================

class VectorDBIntegration(Integration):
    """Base class for vector database integrations."""

    @abstractmethod
    async def create_collection(
        self,
        name: str,
        dimension: int,
        **kwargs
    ) -> bool:
        pass

    @abstractmethod
    async def insert(
        self,
        collection: str,
        vectors: List[List[float]],
        metadata: List[Dict[str, Any]],
        ids: Optional[List[str]] = None
    ) -> List[str]:
        pass

    @abstractmethod
    async def search(
        self,
        collection: str,
        query_vector: List[float],
        top_k: int = 10,
        filter: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def delete(
        self,
        collection: str,
        ids: List[str]
    ) -> bool:
        pass


class ChromaDBIntegration(VectorDBIntegration):
    """ChromaDB vector database integration."""

    def __init__(self, config: IntegrationConfig):
        super().__init__(config)
        self.client = None

    async def connect(self) -> bool:
        try:
            import chromadb

            persist_dir = self.config.options.get("persist_directory", "./chroma_db")
            self.client = chromadb.PersistentClient(path=persist_dir)
            self.status = ConnectionStatus.CONNECTED
            return True
        except Exception as e:
            logger.error(f"ChromaDB connection failed: {e}")
            self.status = ConnectionStatus.ERROR
            return False

    async def disconnect(self) -> None:
        self.client = None
        self.status = ConnectionStatus.DISCONNECTED

    async def health_check(self) -> IntegrationHealth:
        if self.client:
            try:
                self.client.heartbeat()
                return IntegrationHealth(
                    name=self.name,
                    status=ConnectionStatus.CONNECTED
                )
            except Exception as e:
                return IntegrationHealth(
                    name=self.name,
                    status=ConnectionStatus.ERROR,
                    error_message=str(e)
                )
        return IntegrationHealth(
            name=self.name,
            status=ConnectionStatus.DISCONNECTED
        )

    async def create_collection(
        self,
        name: str,
        dimension: int,
        **kwargs
    ) -> bool:
        if not self.client:
            return False
        try:
            self.client.get_or_create_collection(name=name)
            return True
        except Exception as e:
            logger.error(f"Failed to create collection: {e}")
            return False

    async def insert(
        self,
        collection: str,
        vectors: List[List[float]],
        metadata: List[Dict[str, Any]],
        ids: Optional[List[str]] = None
    ) -> List[str]:
        if not self.client:
            return []

        if ids is None:
            ids = [
                hashlib.md5(str(v).encode()).hexdigest()[:12]
                for v in vectors
            ]

        coll = self.client.get_collection(collection)
        coll.add(
            embeddings=vectors,
            metadatas=metadata,
            ids=ids
        )

        return ids

    async def search(
        self,
        collection: str,
        query_vector: List[float],
        top_k: int = 10,
        filter: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        if not self.client:
            return []

        coll = self.client.get_collection(collection)
        results = coll.query(
            query_embeddings=[query_vector],
            n_results=top_k,
            where=filter
        )

        output = []
        for i, id in enumerate(results["ids"][0]):
            output.append({
                "id": id,
                "distance": results["distances"][0][i] if results.get("distances") else None,
                "metadata": results["metadatas"][0][i] if results.get("metadatas") else {}
            })

        return output

    async def delete(
        self,
        collection: str,
        ids: List[str]
    ) -> bool:
        if not self.client:
            return False

        coll = self.client.get_collection(collection)
        coll.delete(ids=ids)
        return True


# =============================================================================
# SEARCH INTEGRATIONS
# =============================================================================

class SearchIntegration(Integration):
    """Base class for search integrations."""

    @abstractmethod
    async def search(
        self,
        query: str,
        num_results: int = 10,
        **kwargs
    ) -> List[Dict[str, Any]]:
        pass


class TavilySearchIntegration(SearchIntegration):
    """Tavily AI search integration."""

    def __init__(self, config: IntegrationConfig):
        super().__init__(config)
        self.client = None

    async def connect(self) -> bool:
        api_key = self.config.api_key or os.getenv("TAVILY_API_KEY")
        if api_key:
            self.status = ConnectionStatus.CONNECTED
            return True
        self.status = ConnectionStatus.ERROR
        return False

    async def disconnect(self) -> None:
        self.status = ConnectionStatus.DISCONNECTED

    async def health_check(self) -> IntegrationHealth:
        return IntegrationHealth(
            name=self.name,
            status=self.status
        )

    async def search(
        self,
        query: str,
        num_results: int = 10,
        **kwargs
    ) -> List[Dict[str, Any]]:
        import aiohttp

        api_key = self.config.api_key or os.getenv("TAVILY_API_KEY")

        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": api_key,
                    "query": query,
                    "max_results": num_results,
                    "search_depth": kwargs.get("depth", "basic"),
                    "include_answer": kwargs.get("include_answer", True),
                    "include_raw_content": kwargs.get("include_raw", False)
                }
            ) as response:
                data = await response.json()

        results = []
        if "results" in data:
            for r in data["results"]:
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "content": r.get("content", ""),
                    "score": r.get("score", 0.0)
                })

        if "answer" in data and data["answer"]:
            results.insert(0, {
                "title": "AI Answer",
                "url": "",
                "content": data["answer"],
                "score": 1.0,
                "is_answer": True
            })

        return results


# =============================================================================
# CODE PLATFORM INTEGRATIONS
# =============================================================================

class GitHubIntegration(Integration):
    """GitHub integration."""

    def __init__(self, config: IntegrationConfig):
        super().__init__(config)
        self.client = None
        self.token = None

    async def connect(self) -> bool:
        self.token = self.config.api_key or os.getenv("GITHUB_TOKEN")
        if self.token:
            self.status = ConnectionStatus.CONNECTED
            return True
        self.status = ConnectionStatus.ERROR
        return False

    async def disconnect(self) -> None:
        self.token = None
        self.status = ConnectionStatus.DISCONNECTED

    async def health_check(self) -> IntegrationHealth:
        if not self.token:
            return IntegrationHealth(
                name=self.name,
                status=ConnectionStatus.DISCONNECTED
            )

        start = datetime.now()
        import aiohttp

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://api.github.com/user",
                    headers={"Authorization": f"token {self.token}"}
                ) as response:
                    if response.status == 200:
                        latency = (datetime.now() - start).total_seconds() * 1000
                        return IntegrationHealth(
                            name=self.name,
                            status=ConnectionStatus.CONNECTED,
                            latency_ms=latency
                        )
        except Exception as e:
            return IntegrationHealth(
                name=self.name,
                status=ConnectionStatus.ERROR,
                error_message=str(e)
            )

        return IntegrationHealth(
            name=self.name,
            status=ConnectionStatus.ERROR
        )

    async def get_repo(self, owner: str, repo: str) -> Dict[str, Any]:
        """Get repository information."""
        import aiohttp

        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://api.github.com/repos/{owner}/{repo}",
                headers={"Authorization": f"token {self.token}"}
            ) as response:
                return await response.json()

    async def search_code(
        self,
        query: str,
        repo: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Search code on GitHub."""
        import aiohttp

        search_query = query
        if repo:
            search_query += f" repo:{repo}"

        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://api.github.com/search/code",
                params={"q": search_query},
                headers={"Authorization": f"token {self.token}"}
            ) as response:
                data = await response.json()

        return data.get("items", [])

    async def get_file_content(
        self,
        owner: str,
        repo: str,
        path: str,
        ref: str = "main"
    ) -> str:
        """Get file content from repository."""
        import base64

        import aiohttp

        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://api.github.com/repos/{owner}/{repo}/contents/{path}",
                params={"ref": ref},
                headers={"Authorization": f"token {self.token}"}
            ) as response:
                data = await response.json()

        if "content" in data:
            return base64.b64decode(data["content"]).decode("utf-8")
        return ""


# =============================================================================
# INTEGRATION HUB
# =============================================================================

class IntegrationHub:
    """Central hub for managing all integrations."""

    def __init__(self):
        self.integrations: Dict[str, Integration] = {}
        self._llm_router: Optional[str] = None

    def register(self, integration: Integration) -> None:
        """Register an integration."""
        self.integrations[integration.name] = integration
        logger.info(f"Registered integration: {integration.name}")

    def get(self, name: str) -> Optional[Integration]:
        """Get an integration by name."""
        return self.integrations.get(name)

    def get_by_type(self, type: IntegrationType) -> List[Integration]:
        """Get all integrations of a type."""
        return [i for i in self.integrations.values() if i.type == type]

    async def connect_all(self) -> Dict[str, bool]:
        """Connect all integrations."""
        results = {}
        for name, integration in self.integrations.items():
            if integration.config.enabled:
                results[name] = await integration.connect()
        return results

    async def disconnect_all(self) -> None:
        """Disconnect all integrations."""
        for integration in self.integrations.values():
            await integration.disconnect()

    async def health_check_all(self) -> Dict[str, IntegrationHealth]:
        """Check health of all integrations."""
        results = {}
        for name, integration in self.integrations.items():
            results[name] = await integration.health_check()
        return results

    def set_default_llm(self, name: str) -> None:
        """Set the default LLM integration."""
        if name in self.integrations:
            self._llm_router = name

    async def llm_complete(
        self,
        messages: List[Dict[str, str]],
        provider: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Complete using LLM (with automatic routing)."""
        provider_name = provider or self._llm_router

        if not provider_name:
            # Find first available LLM
            llms = self.get_by_type(IntegrationType.LLM)
            if not llms:
                raise RuntimeError("No LLM integrations available")
            provider_name = llms[0].name

        llm = self.get(provider_name)
        if not llm or not isinstance(llm, LLMIntegration):
            raise RuntimeError(f"LLM not found: {provider_name}")

        return await llm.complete(messages, **kwargs)

    async def search(
        self,
        query: str,
        provider: Optional[str] = None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """Search using available search integration."""
        if provider:
            search = self.get(provider)
        else:
            searches = self.get_by_type(IntegrationType.SEARCH)
            search = searches[0] if searches else None

        if not search or not isinstance(search, SearchIntegration):
            raise RuntimeError("No search integration available")

        return await search.search(query, **kwargs)

    async def vector_search(
        self,
        collection: str,
        query_vector: List[float],
        provider: Optional[str] = None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """Search vector database."""
        if provider:
            vdb = self.get(provider)
        else:
            vdbs = self.get_by_type(IntegrationType.VECTOR_DB)
            vdb = vdbs[0] if vdbs else None

        if not vdb or not isinstance(vdb, VectorDBIntegration):
            raise RuntimeError("No vector database available")

        return await vdb.search(collection, query_vector, **kwargs)


# =============================================================================
# FACTORY
# =============================================================================

def create_integration(
    name: str,
    type: str,
    **kwargs
) -> Integration:
    """Factory function to create integrations."""
    config = IntegrationConfig(
        name=name,
        type=IntegrationType(type.lower()),
        **{k: v for k, v in kwargs.items() if k in IntegrationConfig.__dataclass_fields__}
    )
    config.options = {k: v for k, v in kwargs.items() if k not in IntegrationConfig.__dataclass_fields__}

    type_lower = type.lower()

    if type_lower == "llm":
        provider = kwargs.get("provider", "openai")
        if provider == "openai":
            return OpenAIIntegration(config)
        elif provider == "anthropic":
            return AnthropicIntegration(config)
        elif provider == "ollama":
            return OllamaIntegration(config)

    elif type_lower == "vector_db":
        provider = kwargs.get("provider", "chroma")
        if provider == "chroma":
            return ChromaDBIntegration(config)

    elif type_lower == "search":
        provider = kwargs.get("provider", "tavily")
        if provider == "tavily":
            return TavilySearchIntegration(config)

    elif type_lower == "code_platform":
        provider = kwargs.get("provider", "github")
        if provider == "github":
            return GitHubIntegration(config)

    raise ValueError(f"Unknown integration type/provider: {type}/{kwargs.get('provider')}")


# =============================================================================
# USAGE EXAMPLE
# =============================================================================

async def example_integrations():
    """Demonstrate integration hub usage."""
    hub = IntegrationHub()

    # Register integrations
    hub.register(create_integration(
        name="openai",
        type="llm",
        provider="openai"
    ))

    hub.register(create_integration(
        name="ollama",
        type="llm",
        provider="ollama"
    ))

    hub.register(create_integration(
        name="chroma",
        type="vector_db",
        provider="chroma",
        persist_directory="./data/chroma"
    ))

    # Connect all
    results = await hub.connect_all()
    print(f"Connection results: {results}")

    # Health check
    health = await hub.health_check_all()
    for name, status in health.items():
        print(f"{name}: {status.status.value}")

    # Use LLM
    hub.set_default_llm("ollama")

    try:
        response = await hub.llm_complete(
            messages=[{"role": "user", "content": "Hello!"}]
        )
        print(f"LLM response: {response['content'][:100]}...")
    except Exception as e:
        print(f"LLM error: {e}")

    # Disconnect
    await hub.disconnect_all()


if __name__ == "__main__":
    asyncio.run(example_integrations())

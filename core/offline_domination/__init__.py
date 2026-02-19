"""
BAEL - Offline Domination System
Full capabilities even without internet connection.

This system provides:
1. Local LLM integration (Ollama, llama.cpp)
2. Offline knowledge base
3. Local tool execution
4. Cached resource access
5. Sync when online

Ba'el never stops working, online or offline.
"""

import asyncio
import hashlib
import json
import logging
import os
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
import pickle

logger = logging.getLogger("BAEL.OfflineDomination")


@dataclass
class LocalModel:
    """A local LLM model configuration."""
    model_id: str
    name: str
    provider: str  # ollama, llamacpp, gpt4all
    path: str = ""
    is_available: bool = False
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CachedResource:
    """A cached resource for offline access."""
    resource_id: str
    url: str
    content: str
    content_type: str
    cached_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None


class LocalLLMProvider:
    """Provider for local LLM execution."""

    def __init__(self):
        self._available_models: Dict[str, LocalModel] = {}
        self._detect_local_models()

    def _detect_local_models(self):
        """Detect available local models."""
        # Check for Ollama
        try:
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                lines = result.stdout.strip().split("\n")[1:]  # Skip header
                for line in lines:
                    parts = line.split()
                    if parts:
                        model_name = parts[0]
                        self._available_models[f"ollama:{model_name}"] = LocalModel(
                            model_id=f"ollama:{model_name}",
                            name=model_name,
                            provider="ollama",
                            is_available=True
                        )
        except:
            pass

        # Check for common local model paths
        common_paths = [
            Path.home() / ".ollama" / "models",
            Path.home() / "models",
            Path("/usr/local/share/models"),
            Path.home() / ".local" / "share" / "models"
        ]

        for path in common_paths:
            if path.exists():
                for model_file in path.glob("*.gguf"):
                    model_id = f"gguf:{model_file.stem}"
                    self._available_models[model_id] = LocalModel(
                        model_id=model_id,
                        name=model_file.stem,
                        provider="llamacpp",
                        path=str(model_file),
                        is_available=True
                    )

    async def generate(
        self,
        prompt: str,
        model_id: str = None,
        max_tokens: int = 1000
    ) -> str:
        """Generate text using local LLM."""
        # Select best available model
        if model_id and model_id in self._available_models:
            model = self._available_models[model_id]
        elif self._available_models:
            model = list(self._available_models.values())[0]
        else:
            return "[No local model available. Install Ollama or download a GGUF model.]"

        if model.provider == "ollama":
            return await self._generate_ollama(prompt, model.name, max_tokens)
        elif model.provider == "llamacpp":
            return await self._generate_llamacpp(prompt, model.path, max_tokens)

        return "[Model provider not supported]"

    async def _generate_ollama(
        self,
        prompt: str,
        model: str,
        max_tokens: int
    ) -> str:
        """Generate using Ollama."""
        try:
            result = subprocess.run(
                ["ollama", "run", model, prompt],
                capture_output=True,
                text=True,
                timeout=120
            )
            if result.returncode == 0:
                return result.stdout
            return f"[Ollama error: {result.stderr}]"
        except subprocess.TimeoutExpired:
            return "[Ollama generation timed out]"
        except Exception as e:
            return f"[Ollama error: {e}]"

    async def _generate_llamacpp(
        self,
        prompt: str,
        model_path: str,
        max_tokens: int
    ) -> str:
        """Generate using llama.cpp."""
        # This would use llama-cpp-python in practice
        return f"[llama.cpp generation with {model_path} - implement with llama-cpp-python]"

    def list_models(self) -> List[Dict[str, Any]]:
        """List available local models."""
        return [
            {
                "id": m.model_id,
                "name": m.name,
                "provider": m.provider,
                "available": m.is_available
            }
            for m in self._available_models.values()
        ]


class OfflineKnowledgeBase:
    """Local knowledge base for offline access."""

    def __init__(self, storage_path: str = "./data/offline_kb"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self._knowledge: Dict[str, Any] = {}
        self._index: Dict[str, List[str]] = {}  # keyword -> doc_ids

        self._load_knowledge()

    def _load_knowledge(self):
        """Load knowledge base from disk."""
        kb_file = self.storage_path / "knowledge.pkl"
        if kb_file.exists():
            try:
                with open(kb_file, "rb") as f:
                    data = pickle.load(f)
                    self._knowledge = data.get("knowledge", {})
                    self._index = data.get("index", {})
            except:
                pass

    def _save_knowledge(self):
        """Save knowledge base to disk."""
        kb_file = self.storage_path / "knowledge.pkl"
        with open(kb_file, "wb") as f:
            pickle.dump({
                "knowledge": self._knowledge,
                "index": self._index
            }, f)

    def add(self, doc_id: str, content: str, metadata: Dict[str, Any] = None):
        """Add document to knowledge base."""
        self._knowledge[doc_id] = {
            "content": content,
            "metadata": metadata or {},
            "added_at": datetime.utcnow().isoformat()
        }

        # Index keywords
        words = set(content.lower().split())
        for word in words:
            if len(word) > 3:  # Only index meaningful words
                if word not in self._index:
                    self._index[word] = []
                if doc_id not in self._index[word]:
                    self._index[word].append(doc_id)

        self._save_knowledge()

    def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search knowledge base."""
        query_words = set(query.lower().split())

        # Find matching documents
        doc_scores: Dict[str, int] = {}
        for word in query_words:
            if word in self._index:
                for doc_id in self._index[word]:
                    doc_scores[doc_id] = doc_scores.get(doc_id, 0) + 1

        # Sort by score
        sorted_docs = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)

        results = []
        for doc_id, score in sorted_docs[:limit]:
            if doc_id in self._knowledge:
                results.append({
                    "doc_id": doc_id,
                    "score": score,
                    **self._knowledge[doc_id]
                })

        return results

    def get(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Get specific document."""
        return self._knowledge.get(doc_id)


class ResourceCache:
    """Cache for offline resource access."""

    def __init__(self, storage_path: str = "./data/cache"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self._cache: Dict[str, CachedResource] = {}
        self._load_cache()

    def _load_cache(self):
        """Load cache from disk."""
        cache_file = self.storage_path / "cache.pkl"
        if cache_file.exists():
            try:
                with open(cache_file, "rb") as f:
                    self._cache = pickle.load(f)
            except:
                pass

    def _save_cache(self):
        """Save cache to disk."""
        cache_file = self.storage_path / "cache.pkl"
        with open(cache_file, "wb") as f:
            pickle.dump(self._cache, f)

    def cache(self, url: str, content: str, content_type: str = "text/plain"):
        """Cache a resource."""
        resource_id = hashlib.md5(url.encode()).hexdigest()
        self._cache[resource_id] = CachedResource(
            resource_id=resource_id,
            url=url,
            content=content,
            content_type=content_type
        )
        self._save_cache()

    def get(self, url: str) -> Optional[str]:
        """Get cached resource."""
        resource_id = hashlib.md5(url.encode()).hexdigest()
        if resource_id in self._cache:
            return self._cache[resource_id].content
        return None

    def has(self, url: str) -> bool:
        """Check if resource is cached."""
        resource_id = hashlib.md5(url.encode()).hexdigest()
        return resource_id in self._cache


class OfflineDominationSystem:
    """
    Complete offline capabilities.

    Features:
    - Local LLM execution
    - Offline knowledge base
    - Resource caching
    - Full functionality without internet
    """

    def __init__(self):
        self.llm = LocalLLMProvider()
        self.knowledge = OfflineKnowledgeBase()
        self.cache = ResourceCache()

        self._is_online = self._check_connectivity()

        logger.info(f"OfflineDominationSystem initialized. Online: {self._is_online}")

    def _check_connectivity(self) -> bool:
        """Check internet connectivity."""
        try:
            result = subprocess.run(
                ["ping", "-c", "1", "-W", "2", "8.8.8.8"],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except:
            return False

    @property
    def is_online(self) -> bool:
        """Check if currently online."""
        return self._check_connectivity()

    async def generate(self, prompt: str) -> str:
        """Generate text, using local or online LLM."""
        return await self.llm.generate(prompt)

    def search_knowledge(self, query: str) -> List[Dict[str, Any]]:
        """Search local knowledge base."""
        return self.knowledge.search(query)

    def add_knowledge(self, doc_id: str, content: str, metadata: Dict[str, Any] = None):
        """Add to local knowledge base."""
        self.knowledge.add(doc_id, content, metadata)

    def get_cached(self, url: str) -> Optional[str]:
        """Get cached resource."""
        return self.cache.get(url)

    def list_local_models(self) -> List[Dict[str, Any]]:
        """List available local models."""
        return self.llm.list_models()

    def get_status(self) -> Dict[str, Any]:
        """Get offline system status."""
        return {
            "online": self.is_online,
            "local_models": len(self.llm._available_models),
            "knowledge_docs": len(self.knowledge._knowledge),
            "cached_resources": len(self.cache._cache),
            "ready": len(self.llm._available_models) > 0
        }


# Singleton
_offline_system: Optional[OfflineDominationSystem] = None


def get_offline_system() -> OfflineDominationSystem:
    """Get global offline system."""
    global _offline_system
    if _offline_system is None:
        _offline_system = OfflineDominationSystem()
    return _offline_system

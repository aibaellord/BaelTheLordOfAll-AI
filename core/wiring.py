"""
BAEL Core Wiring Layer
======================

This module wires all BAEL components together into a functioning system.
It provides the actual LLM calling, memory storage, and execution that
makes the scaffolded architecture actually work.

This is the "glue" that transforms BAEL from scaffolding into a working system.
"""

import asyncio
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, AsyncIterator, Dict, List, Optional

logger = logging.getLogger("BAEL.Wiring")


@dataclass
class WiringConfig:
    """Configuration for the wiring layer."""
    # LLM Settings
    default_provider: str = "openrouter"
    default_model: str = "anthropic/claude-3.5-sonnet"
    fallback_model: str = "anthropic/claude-3-haiku-20240307"

    # API Keys (loaded from environment)
    openrouter_key: Optional[str] = None
    anthropic_key: Optional[str] = None
    openai_key: Optional[str] = None

    # Memory Settings
    memory_dir: Path = field(default_factory=lambda: Path("memory"))
    enable_vector_store: bool = True

    # Execution Settings
    max_retries: int = 3
    timeout_seconds: int = 60
    enable_streaming: bool = True

    @classmethod
    def from_environment(cls) -> "WiringConfig":
        """Load config from environment variables."""
        return cls(
            default_provider=os.environ.get("DEFAULT_LLM_PROVIDER", "openrouter"),
            default_model=os.environ.get("DEFAULT_MODEL", "anthropic/claude-3.5-sonnet"),
            openrouter_key=os.environ.get("OPENROUTER_API_KEY"),
            anthropic_key=os.environ.get("ANTHROPIC_API_KEY"),
            openai_key=os.environ.get("OPENAI_API_KEY"),
        )


class LLMExecutor:
    """
    Actual LLM execution layer.

    Handles the real API calls to various LLM providers.
    """

    def __init__(self, config: WiringConfig):
        self.config = config
        self._session = None

    async def _get_session(self):
        """Get or create aiohttp session."""
        if self._session is None:
            import aiohttp
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self):
        """Close the session."""
        if self._session:
            await self._session.close()
            self._session = None

    async def complete(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        system: Optional[str] = None,
        tools: Optional[List[Dict]] = None,
        stream: bool = False
    ) -> Dict[str, Any]:
        """
        Complete a chat request.

        This is the core LLM calling function that actually makes API requests.
        """
        model = model or self.config.default_model

        # Determine provider
        if self.config.openrouter_key:
            return await self._call_openrouter(
                messages, model, temperature, max_tokens, system, tools
            )
        elif self.config.anthropic_key:
            return await self._call_anthropic(
                messages, model, temperature, max_tokens, system, tools
            )
        elif self.config.openai_key:
            return await self._call_openai(
                messages, model, temperature, max_tokens, system, tools
            )
        else:
            # Try Ollama as fallback
            return await self._call_ollama(
                messages, model, temperature, max_tokens, system
            )

    async def _call_openrouter(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int,
        system: Optional[str],
        tools: Optional[List[Dict]]
    ) -> Dict[str, Any]:
        """Call OpenRouter API."""
        session = await self._get_session()

        # Build messages with system prompt
        full_messages = []
        if system:
            full_messages.append({"role": "system", "content": system})
        full_messages.extend(messages)

        payload = {
            "model": model,
            "messages": full_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if tools:
            payload["tools"] = tools

        headers = {
            "Authorization": f"Bearer {self.config.openrouter_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/bael-ai",
            "X-Title": "BAEL AI Agent"
        }

        try:
            async with session.post(
                "https://openrouter.ai/api/v1/chat/completions",
                json=payload,
                headers=headers,
                timeout=self.config.timeout_seconds
            ) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    logger.error(f"OpenRouter error: {resp.status} - {error_text}")
                    raise Exception(f"OpenRouter API error: {resp.status}")

                data = await resp.json()

                return {
                    "content": data["choices"][0]["message"]["content"],
                    "model": data.get("model", model),
                    "usage": data.get("usage", {}),
                    "finish_reason": data["choices"][0].get("finish_reason", "stop"),
                    "tool_calls": data["choices"][0]["message"].get("tool_calls"),
                }
        except Exception as e:
            logger.error(f"OpenRouter call failed: {e}")
            raise

    async def _call_anthropic(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int,
        system: Optional[str],
        tools: Optional[List[Dict]]
    ) -> Dict[str, Any]:
        """Call Anthropic API directly."""
        session = await self._get_session()

        # Convert model name if needed
        if "/" in model:
            model = model.split("/")[-1]

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if system:
            payload["system"] = system

        if tools:
            # Convert OpenAI tool format to Anthropic format
            anthropic_tools = []
            for tool in tools:
                if tool.get("type") == "function":
                    func = tool["function"]
                    anthropic_tools.append({
                        "name": func["name"],
                        "description": func.get("description", ""),
                        "input_schema": func.get("parameters", {})
                    })
            if anthropic_tools:
                payload["tools"] = anthropic_tools

        headers = {
            "x-api-key": self.config.anthropic_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }

        try:
            async with session.post(
                "https://api.anthropic.com/v1/messages",
                json=payload,
                headers=headers,
                timeout=self.config.timeout_seconds
            ) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    logger.error(f"Anthropic error: {resp.status} - {error_text}")
                    raise Exception(f"Anthropic API error: {resp.status}")

                data = await resp.json()

                # Extract content from Anthropic response format
                content = ""
                tool_use = None
                for block in data.get("content", []):
                    if block["type"] == "text":
                        content += block["text"]
                    elif block["type"] == "tool_use":
                        tool_use = block

                return {
                    "content": content,
                    "model": data.get("model", model),
                    "usage": data.get("usage", {}),
                    "finish_reason": data.get("stop_reason", "end_turn"),
                    "tool_calls": [tool_use] if tool_use else None,
                }
        except Exception as e:
            logger.error(f"Anthropic call failed: {e}")
            raise

    async def _call_openai(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int,
        system: Optional[str],
        tools: Optional[List[Dict]]
    ) -> Dict[str, Any]:
        """Call OpenAI API."""
        session = await self._get_session()

        # Convert model name if needed
        if "/" in model:
            model = model.split("/")[-1]

        full_messages = []
        if system:
            full_messages.append({"role": "system", "content": system})
        full_messages.extend(messages)

        payload = {
            "model": model,
            "messages": full_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if tools:
            payload["tools"] = tools

        headers = {
            "Authorization": f"Bearer {self.config.openai_key}",
            "Content-Type": "application/json"
        }

        try:
            async with session.post(
                "https://api.openai.com/v1/chat/completions",
                json=payload,
                headers=headers,
                timeout=self.config.timeout_seconds
            ) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    logger.error(f"OpenAI error: {resp.status} - {error_text}")
                    raise Exception(f"OpenAI API error: {resp.status}")

                data = await resp.json()

                return {
                    "content": data["choices"][0]["message"]["content"],
                    "model": data.get("model", model),
                    "usage": data.get("usage", {}),
                    "finish_reason": data["choices"][0].get("finish_reason", "stop"),
                    "tool_calls": data["choices"][0]["message"].get("tool_calls"),
                }
        except Exception as e:
            logger.error(f"OpenAI call failed: {e}")
            raise

    async def _call_ollama(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int,
        system: Optional[str]
    ) -> Dict[str, Any]:
        """Call local Ollama."""
        session = await self._get_session()

        # Use a default local model if none specified
        if "/" in model or "claude" in model.lower() or "gpt" in model.lower():
            model = "llama3.2"

        full_messages = []
        if system:
            full_messages.append({"role": "system", "content": system})
        full_messages.extend(messages)

        payload = {
            "model": model,
            "messages": full_messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            }
        }

        try:
            async with session.post(
                "http://localhost:11434/api/chat",
                json=payload,
                timeout=120  # Ollama can be slow
            ) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    logger.error(f"Ollama error: {resp.status} - {error_text}")
                    raise Exception(f"Ollama API error: {resp.status}")

                data = await resp.json()

                return {
                    "content": data["message"]["content"],
                    "model": model,
                    "usage": {
                        "prompt_tokens": data.get("prompt_eval_count", 0),
                        "completion_tokens": data.get("eval_count", 0),
                    },
                    "finish_reason": "stop",
                    "tool_calls": None,
                }
        except Exception as e:
            logger.error(f"Ollama call failed: {e}")
            raise

    async def stream_complete(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        system: Optional[str] = None
    ) -> AsyncIterator[str]:
        """Stream a completion response."""
        model = model or self.config.default_model
        session = await self._get_session()

        # For now, use OpenRouter streaming
        if not self.config.openrouter_key:
            # Fall back to non-streaming
            result = await self.complete(messages, model, temperature, max_tokens, system)
            yield result["content"]
            return

        full_messages = []
        if system:
            full_messages.append({"role": "system", "content": system})
        full_messages.extend(messages)

        payload = {
            "model": model,
            "messages": full_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }

        headers = {
            "Authorization": f"Bearer {self.config.openrouter_key}",
            "Content-Type": "application/json",
        }

        async with session.post(
            "https://openrouter.ai/api/v1/chat/completions",
            json=payload,
            headers=headers
        ) as resp:
            async for line in resp.content:
                line = line.decode().strip()
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        delta = chunk["choices"][0].get("delta", {})
                        if "content" in delta:
                            yield delta["content"]
                    except json.JSONDecodeError:
                        continue


class MemoryExecutor:
    """
    Actual memory storage and retrieval.

    Provides working implementations for memory operations.
    """

    def __init__(self, config: WiringConfig):
        self.config = config
        self.memory_dir = config.memory_dir
        self.memory_dir.mkdir(parents=True, exist_ok=True)

        # In-memory working memory
        self._working_memory: List[Dict[str, Any]] = []
        self._max_working_items = 20

        # Simple file-based persistence
        self._episodic_file = self.memory_dir / "episodic.jsonl"
        self._semantic_file = self.memory_dir / "semantic.jsonl"

    def add_to_working(self, item: Dict[str, Any]) -> None:
        """Add item to working memory."""
        item["timestamp"] = datetime.now().isoformat()
        self._working_memory.append(item)

        # Evict old items
        while len(self._working_memory) > self._max_working_items:
            self._working_memory.pop(0)

    def get_working_memory(self) -> List[Dict[str, Any]]:
        """Get current working memory."""
        return list(self._working_memory)

    def clear_working(self) -> None:
        """Clear working memory."""
        self._working_memory.clear()

    def save_episodic(self, event: Dict[str, Any]) -> None:
        """Save an episodic memory (experience)."""
        event["timestamp"] = datetime.now().isoformat()
        with open(self._episodic_file, "a") as f:
            f.write(json.dumps(event) + "\n")

    def search_episodic(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search episodic memories."""
        if not self._episodic_file.exists():
            return []

        results = []
        query_lower = query.lower()

        with open(self._episodic_file) as f:
            for line in f:
                try:
                    event = json.loads(line)
                    # Simple keyword matching
                    content = json.dumps(event).lower()
                    if query_lower in content:
                        results.append(event)
                except json.JSONDecodeError:
                    continue

        return results[-limit:]

    def save_semantic(self, fact: Dict[str, Any]) -> None:
        """Save a semantic memory (fact/knowledge)."""
        fact["timestamp"] = datetime.now().isoformat()
        with open(self._semantic_file, "a") as f:
            f.write(json.dumps(fact) + "\n")

    def search_semantic(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search semantic memories."""
        if not self._semantic_file.exists():
            return []

        results = []
        query_lower = query.lower()

        with open(self._semantic_file) as f:
            for line in f:
                try:
                    fact = json.loads(line)
                    content = json.dumps(fact).lower()
                    if query_lower in content:
                        results.append(fact)
                except json.JSONDecodeError:
                    continue

        return results[-limit:]


class UnifiedWiring:
    """
    Unified wiring that connects all BAEL components.

    This is the main entry point for actually executing BAEL operations.
    """

    def __init__(self, config: Optional[WiringConfig] = None):
        self.config = config or WiringConfig.from_environment()
        self.llm = LLMExecutor(self.config)
        self.memory = MemoryExecutor(self.config)
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize all components."""
        logger.info("Initializing unified wiring...")

        # Test LLM connectivity
        try:
            # Simple test call
            if self.config.openrouter_key or self.config.anthropic_key or self.config.openai_key:
                logger.info("✓ LLM API keys configured")
            else:
                logger.warning("⚠ No LLM API keys found, will try Ollama")
        except Exception as e:
            logger.warning(f"LLM test failed: {e}")

        self._initialized = True
        logger.info("Unified wiring initialized")

    async def process(
        self,
        query: str,
        context: Optional[List[Dict[str, str]]] = None,
        persona: Optional[str] = None,
        stream: bool = False
    ) -> Dict[str, Any]:
        """
        Process a query through the full BAEL pipeline.

        This is the main entry point for BAEL operations.
        """
        if not self._initialized:
            await self.initialize()

        start_time = datetime.now()

        # Build conversation
        messages = context or []
        messages.append({"role": "user", "content": query})

        # Get persona system prompt if specified
        system = None
        if persona:
            system = self._get_persona_prompt(persona)

        # Add working memory context
        working = self.memory.get_working_memory()
        if working:
            memory_context = "\n".join([
                f"- {item.get('content', str(item))}"
                for item in working[-5:]
            ])
            if system:
                system += f"\n\nRecent context:\n{memory_context}"
            else:
                system = f"Recent context:\n{memory_context}"

        # Call LLM
        if stream:
            return {"stream": self.llm.stream_complete(messages, system=system)}
        else:
            result = await self.llm.complete(messages, system=system)

            # Save to memory
            self.memory.add_to_working({
                "type": "interaction",
                "query": query,
                "response": result["content"][:500]
            })

            execution_time = (datetime.now() - start_time).total_seconds() * 1000

            return {
                "response": result["content"],
                "model": result["model"],
                "usage": result["usage"],
                "execution_time_ms": execution_time,
                "persona": persona,
            }

    def _get_persona_prompt(self, persona: str) -> str:
        """Get system prompt for a persona."""
        personas = {
            "architect": """You are BAEL Architect Prime, a world-class system architect.
You design elegant, scalable solutions that stand the test of time.
Think in terms of components, interfaces, and data flows.
Always consider maintainability, performance, and security.""",

            "coder": """You are BAEL Code Master, an elite software engineer.
You write clean, efficient, well-documented code.
Follow best practices and design patterns.
Always include proper error handling and testing considerations.""",

            "researcher": """You are BAEL Research Oracle, a brilliant analyst.
You synthesize information from multiple sources.
Provide balanced, well-reasoned analysis with citations.
Consider multiple perspectives before drawing conclusions.""",

            "creative": """You are BAEL Creative Genius, an innovative thinker.
You generate novel ideas and unconventional solutions.
Think beyond constraints and explore possibilities.
Combine concepts from different domains.""",
        }

        return personas.get(persona.lower(), f"You are BAEL, an advanced AI assistant. Current mode: {persona}")

    async def close(self) -> None:
        """Clean up resources."""
        await self.llm.close()


# Global wiring instance
_wiring: Optional[UnifiedWiring] = None


async def get_wiring() -> UnifiedWiring:
    """Get or create the global wiring instance."""
    global _wiring
    if _wiring is None:
        _wiring = UnifiedWiring()
        await _wiring.initialize()
    return _wiring


async def quick_complete(query: str, persona: Optional[str] = None) -> str:
    """Quick convenience function for one-off completions."""
    wiring = await get_wiring()
    result = await wiring.process(query, persona=persona)
    return result["response"]


# CLI test
if __name__ == "__main__":
    async def test():
        print("🔌 BAEL Wiring Test")
        print("=" * 50)

        wiring = UnifiedWiring()
        await wiring.initialize()

        print("\n📝 Testing LLM call...")
        result = await wiring.process(
            "What is 2 + 2? Just give me the number.",
            persona="coder"
        )

        print(f"Response: {result['response']}")
        print(f"Model: {result['model']}")
        print(f"Time: {result['execution_time_ms']:.1f}ms")

        await wiring.close()

    asyncio.run(test())

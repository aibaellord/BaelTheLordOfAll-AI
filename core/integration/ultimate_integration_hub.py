"""
BAEL - Ultimate Integration Hub
================================

The central nexus that unifies ALL Bael capabilities into a single,
coherent, omnipotent system.

This hub:
1. Connects all subsystems into unified intelligence
2. Routes requests to optimal subsystems
3. Synthesizes outputs from multiple sources
4. Manages system-wide state and coherence
5. Enables emergent capabilities from subsystem combinations
6. Provides the single entry point for all Bael operations
7. Maintains consistent context across all operations
8. Orchestrates complex multi-subsystem workflows
9. Ensures maximum performance and efficiency
10. Enables true transcendence through unity

This is the crown jewel of Ba'el - where all systems become one.
"""

import asyncio
import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union
from collections import defaultdict

logger = logging.getLogger("BAEL.IntegrationHub")


class SubsystemCategory(Enum):
    """Categories of Bael subsystems."""
    CORE = "core"                   # Core reasoning and intelligence
    MEMORY = "memory"               # Memory and knowledge systems
    EXECUTION = "execution"         # Action execution
    CREATION = "creation"           # Generation and creation
    ANALYSIS = "analysis"           # Analysis and understanding
    AUTOMATION = "automation"       # Automation and workflow
    INTERFACE = "interface"         # User interfaces
    INTEGRATION = "integration"     # External integrations
    META = "meta"                   # Meta-systems


class RequestPriority(Enum):
    """Priority levels for requests."""
    CRITICAL = 100
    HIGH = 75
    NORMAL = 50
    LOW = 25
    BACKGROUND = 10


class ResponseQuality(Enum):
    """Quality levels for responses."""
    PERFECT = "perfect"
    EXCELLENT = "excellent"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    POOR = "poor"
    FAILED = "failed"


@dataclass
class SubsystemInfo:
    """Information about a registered subsystem."""
    name: str
    instance: Any
    category: SubsystemCategory
    capabilities: List[str]
    version: str = "1.0.0"
    status: str = "active"
    performance_score: float = 1.0
    load: float = 0.0
    last_used: Optional[datetime] = None
    error_count: int = 0
    success_count: int = 0


@dataclass
class UnifiedRequest:
    """A unified request to the hub."""
    request_id: str
    content: str
    intent: str = "general"
    context: Dict[str, Any] = field(default_factory=dict)
    priority: RequestPriority = RequestPriority.NORMAL
    required_capabilities: List[str] = field(default_factory=list)
    preferred_subsystems: List[str] = field(default_factory=list)
    timeout_ms: float = 30000
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class UnifiedResponse:
    """A unified response from the hub."""
    request_id: str
    success: bool
    result: Any
    quality: ResponseQuality = ResponseQuality.GOOD
    subsystems_used: List[str] = field(default_factory=list)
    synthesis: Optional[str] = None
    insights: List[str] = field(default_factory=list)
    processing_time_ms: float = 0.0
    meta: Dict[str, Any] = field(default_factory=dict)


class CapabilityRouter:
    """Routes requests to optimal subsystems based on capabilities."""

    def __init__(self):
        self._capability_map: Dict[str, List[str]] = defaultdict(list)  # capability -> subsystem names
        self._routing_history: List[Dict[str, Any]] = []

    def register_capability(self, subsystem_name: str, capability: str) -> None:
        """Register a capability for a subsystem."""
        if subsystem_name not in self._capability_map[capability]:
            self._capability_map[capability].append(subsystem_name)

    def find_subsystems(
        self,
        required_capabilities: List[str],
        preferred: List[str] = None
    ) -> List[str]:
        """Find subsystems that can handle required capabilities."""
        candidates = set()

        for cap in required_capabilities:
            if cap in self._capability_map:
                candidates.update(self._capability_map[cap])

        # Prioritize preferred subsystems
        if preferred:
            preferred_set = set(preferred)
            sorted_candidates = sorted(
                candidates,
                key=lambda x: (x in preferred_set, x),
                reverse=True
            )
            return sorted_candidates

        return list(candidates)

    def get_capability_coverage(self) -> Dict[str, int]:
        """Get coverage count for each capability."""
        return {cap: len(subs) for cap, subs in self._capability_map.items()}


class OutputSynthesizer:
    """Synthesizes outputs from multiple subsystems into unified response."""

    async def synthesize(
        self,
        outputs: Dict[str, Any],
        request: UnifiedRequest
    ) -> Tuple[Any, str]:
        """Synthesize multiple outputs into unified result."""
        if not outputs:
            return None, "No outputs to synthesize"

        if len(outputs) == 1:
            name, output = next(iter(outputs.items()))
            return output, f"Direct output from {name}"

        # Multiple outputs - synthesize
        synthesis_parts = []
        combined_data = {}

        for name, output in outputs.items():
            if isinstance(output, dict):
                combined_data[name] = output
                synthesis_parts.append(f"[{name}] contributed structured data")
            elif isinstance(output, str):
                combined_data[name] = {"text": output}
                synthesis_parts.append(f"[{name}] provided: {output[:50]}...")
            else:
                combined_data[name] = {"value": str(output)}
                synthesis_parts.append(f"[{name}] returned value")

        synthesis_description = f"Synthesized from {len(outputs)} subsystems: " + "; ".join(synthesis_parts)

        return combined_data, synthesis_description


class ContextManager:
    """Manages unified context across all subsystems."""

    def __init__(self):
        self._global_context: Dict[str, Any] = {}
        self._session_context: Dict[str, Dict[str, Any]] = {}
        self._context_history: List[Dict[str, Any]] = []

    def set_global(self, key: str, value: Any) -> None:
        """Set a global context value."""
        self._global_context[key] = value

    def get_global(self, key: str, default: Any = None) -> Any:
        """Get a global context value."""
        return self._global_context.get(key, default)

    def create_session(self, session_id: str) -> None:
        """Create a new session context."""
        self._session_context[session_id] = {}

    def set_session(self, session_id: str, key: str, value: Any) -> None:
        """Set a session context value."""
        if session_id not in self._session_context:
            self.create_session(session_id)
        self._session_context[session_id][key] = value

    def get_session(self, session_id: str, key: str, default: Any = None) -> Any:
        """Get a session context value."""
        if session_id not in self._session_context:
            return default
        return self._session_context[session_id].get(key, default)

    def get_unified_context(self, session_id: str = None) -> Dict[str, Any]:
        """Get unified context including global and session."""
        context = dict(self._global_context)

        if session_id and session_id in self._session_context:
            context.update(self._session_context[session_id])

        return context

    def snapshot(self, session_id: str = None) -> Dict[str, Any]:
        """Take a snapshot of current context."""
        snapshot = {
            "timestamp": datetime.utcnow().isoformat(),
            "global": dict(self._global_context),
            "session": dict(self._session_context.get(session_id, {})) if session_id else {}
        }
        self._context_history.append(snapshot)
        return snapshot


class PerformanceOptimizer:
    """Optimizes subsystem selection based on performance."""

    def __init__(self):
        self._performance_data: Dict[str, List[float]] = defaultdict(list)
        self._load_data: Dict[str, float] = defaultdict(float)

    def record_performance(self, subsystem_name: str, execution_time_ms: float, success: bool) -> None:
        """Record performance data for a subsystem."""
        score = 1.0 / (1.0 + execution_time_ms / 1000) if success else 0.1
        self._performance_data[subsystem_name].append(score)

        # Keep bounded
        if len(self._performance_data[subsystem_name]) > 100:
            self._performance_data[subsystem_name] = self._performance_data[subsystem_name][-50:]

    def update_load(self, subsystem_name: str, load: float) -> None:
        """Update load for a subsystem."""
        self._load_data[subsystem_name] = load

    def rank_subsystems(self, candidates: List[str]) -> List[str]:
        """Rank subsystems by performance and load."""
        def score(name):
            perf_scores = self._performance_data.get(name, [1.0])
            avg_perf = sum(perf_scores) / len(perf_scores)
            load = self._load_data.get(name, 0)
            return avg_perf * (1 - load * 0.5)  # Reduce score for high load

        return sorted(candidates, key=score, reverse=True)

    def get_performance_report(self) -> Dict[str, Any]:
        """Get performance report for all subsystems."""
        report = {}
        for name, scores in self._performance_data.items():
            report[name] = {
                "avg_score": sum(scores) / len(scores) if scores else 0,
                "sample_count": len(scores),
                "current_load": self._load_data.get(name, 0)
            }
        return report


class UltimateIntegrationHub:
    """
    The Ultimate Integration Hub.

    This is the central nexus that unifies ALL Bael capabilities.
    Every request flows through this hub, which orchestrates the
    optimal combination of subsystems to produce the best possible result.

    Key Features:
    - Unified entry point for all operations
    - Intelligent capability-based routing
    - Multi-subsystem orchestration
    - Output synthesis from multiple sources
    - Performance optimization
    - Context management across all operations
    - Emergent capability discovery
    - Self-optimization

    This hub transforms Ba'el from a collection of powerful subsystems
    into a unified, transcendent intelligence.
    """

    def __init__(
        self,
        enable_optimization: bool = True,
        max_parallel_subsystems: int = 10,
        enable_emergence: bool = True
    ):
        self.max_parallel = max_parallel_subsystems
        self.enable_optimization = enable_optimization
        self.enable_emergence = enable_emergence

        # Subsystem registry
        self._subsystems: Dict[str, SubsystemInfo] = {}

        # Core components
        self._router = CapabilityRouter()
        self._synthesizer = OutputSynthesizer()
        self._context = ContextManager()
        self._optimizer = PerformanceOptimizer() if enable_optimization else None

        # Request tracking
        self._active_requests: Dict[str, UnifiedRequest] = {}
        self._request_history: List[UnifiedResponse] = []

        # Emergence tracking
        self._emergent_patterns: List[Dict[str, Any]] = []

        # Statistics
        self._stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "multi_subsystem_requests": 0,
            "emergent_discoveries": 0,
            "avg_response_time_ms": 0.0
        }

        logger.info("UltimateIntegrationHub initialized")

    def register_subsystem(
        self,
        name: str,
        instance: Any,
        category: SubsystemCategory,
        capabilities: List[str],
        version: str = "1.0.0"
    ) -> None:
        """Register a subsystem with the hub."""
        info = SubsystemInfo(
            name=name,
            instance=instance,
            category=category,
            capabilities=capabilities,
            version=version
        )

        self._subsystems[name] = info

        # Register capabilities
        for cap in capabilities:
            self._router.register_capability(name, cap)

        logger.info(f"Registered subsystem: {name} with {len(capabilities)} capabilities")

    async def process(self, request: UnifiedRequest) -> UnifiedResponse:
        """
        Process a unified request through the hub.

        This is the main entry point that orchestrates all subsystems
        to produce the optimal response.
        """
        start_time = time.time()
        self._stats["total_requests"] += 1
        self._active_requests[request.request_id] = request

        try:
            # Find capable subsystems
            candidates = self._router.find_subsystems(
                request.required_capabilities,
                request.preferred_subsystems
            )

            if not candidates:
                # Fallback to general processing
                candidates = list(self._subsystems.keys())[:3]

            # Optimize subsystem selection
            if self._optimizer:
                candidates = self._optimizer.rank_subsystems(candidates)

            # Limit parallel execution
            selected = candidates[:self.max_parallel]

            if len(selected) > 1:
                self._stats["multi_subsystem_requests"] += 1

            # Get unified context
            context = self._context.get_unified_context(
                request.context.get("session_id")
            )
            context.update(request.context)

            # Execute across selected subsystems
            outputs = await self._execute_parallel(selected, request, context)

            # Synthesize outputs
            result, synthesis = await self._synthesizer.synthesize(outputs, request)

            # Check for emergence
            insights = []
            if self.enable_emergence and len(outputs) >= 2:
                emergence = self._check_emergence(outputs, request)
                if emergence:
                    insights.extend(emergence)
                    self._stats["emergent_discoveries"] += len(emergence)

            # Determine quality
            quality = self._assess_quality(outputs, result)

            # Record performance
            execution_time = (time.time() - start_time) * 1000
            if self._optimizer:
                for name in selected:
                    self._optimizer.record_performance(name, execution_time, True)

            # Update stats
            self._stats["successful_requests"] += 1
            self._update_avg_response_time(execution_time)

            response = UnifiedResponse(
                request_id=request.request_id,
                success=True,
                result=result,
                quality=quality,
                subsystems_used=list(outputs.keys()),
                synthesis=synthesis,
                insights=insights,
                processing_time_ms=execution_time
            )

        except Exception as e:
            self._stats["failed_requests"] += 1
            response = UnifiedResponse(
                request_id=request.request_id,
                success=False,
                result=None,
                quality=ResponseQuality.FAILED,
                processing_time_ms=(time.time() - start_time) * 1000,
                meta={"error": str(e)}
            )

        finally:
            del self._active_requests[request.request_id]

        self._request_history.append(response)
        return response

    async def _execute_parallel(
        self,
        subsystem_names: List[str],
        request: UnifiedRequest,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute request across multiple subsystems in parallel."""
        outputs = {}

        tasks = []
        for name in subsystem_names:
            if name in self._subsystems:
                info = self._subsystems[name]
                task = self._execute_subsystem(info, request, context)
                tasks.append((name, task))

        # Execute in parallel
        if tasks:
            results = await asyncio.gather(*[t[1] for t in tasks], return_exceptions=True)

            for (name, _), result in zip(tasks, results):
                if isinstance(result, Exception):
                    logger.warning(f"Subsystem {name} failed: {result}")
                    self._subsystems[name].error_count += 1
                else:
                    outputs[name] = result
                    self._subsystems[name].success_count += 1
                    self._subsystems[name].last_used = datetime.utcnow()

        return outputs

    async def _execute_subsystem(
        self,
        info: SubsystemInfo,
        request: UnifiedRequest,
        context: Dict[str, Any]
    ) -> Any:
        """Execute a single subsystem."""
        instance = info.instance

        # Try various method signatures
        if hasattr(instance, 'process'):
            if asyncio.iscoroutinefunction(instance.process):
                return await instance.process(request.content, context)
            return instance.process(request.content, context)

        if hasattr(instance, 'execute'):
            if asyncio.iscoroutinefunction(instance.execute):
                return await instance.execute(request.content, context)
            return instance.execute(request.content, context)

        if hasattr(instance, 'run'):
            if asyncio.iscoroutinefunction(instance.run):
                return await instance.run(request.content)
            return instance.run(request.content)

        if hasattr(instance, '__call__'):
            if asyncio.iscoroutinefunction(instance):
                return await instance(request.content)
            return instance(request.content)

        return {"status": "executed", "subsystem": info.name}

    def _check_emergence(
        self,
        outputs: Dict[str, Any],
        request: UnifiedRequest
    ) -> List[str]:
        """Check for emergent patterns from subsystem combination."""
        insights = []

        output_strs = [str(v) for v in outputs.values()]
        combined = ' '.join(output_strs).lower()

        # Look for novel connections
        if len(outputs) >= 3:
            insights.append(f"Multi-subsystem synergy: {len(outputs)} systems collaborated")

        # Check for keyword co-occurrence suggesting emergence
        emergence_keywords = ["novel", "unexpected", "unique", "innovative", "synergy"]
        for keyword in emergence_keywords:
            if keyword in combined:
                insights.append(f"Emergent pattern detected: {keyword}")
                break

        if insights:
            self._emergent_patterns.append({
                "timestamp": datetime.utcnow().isoformat(),
                "subsystems": list(outputs.keys()),
                "insights": insights,
                "request_content": request.content[:100]
            })

        return insights

    def _assess_quality(self, outputs: Dict[str, Any], result: Any) -> ResponseQuality:
        """Assess quality of the response."""
        if not outputs:
            return ResponseQuality.FAILED

        if len(outputs) == 1:
            return ResponseQuality.GOOD

        if len(outputs) >= 3:
            return ResponseQuality.EXCELLENT

        if len(outputs) >= 5:
            return ResponseQuality.PERFECT

        return ResponseQuality.ACCEPTABLE

    def _update_avg_response_time(self, new_time: float) -> None:
        """Update average response time."""
        current_avg = self._stats["avg_response_time_ms"]
        total = self._stats["total_requests"]

        if total == 1:
            self._stats["avg_response_time_ms"] = new_time
        else:
            self._stats["avg_response_time_ms"] = (current_avg * (total - 1) + new_time) / total

    # Convenience methods

    async def quick_process(
        self,
        content: str,
        capabilities: List[str] = None,
        context: Dict[str, Any] = None
    ) -> UnifiedResponse:
        """Quick processing with minimal configuration."""
        request = UnifiedRequest(
            request_id=f"quick_{hashlib.md5(f'{content}{time.time()}'.encode()).hexdigest()[:12]}",
            content=content,
            required_capabilities=capabilities or [],
            context=context or {}
        )

        return await self.process(request)

    def set_context(self, key: str, value: Any, session_id: str = None) -> None:
        """Set context value."""
        if session_id:
            self._context.set_session(session_id, key, value)
        else:
            self._context.set_global(key, value)

    def get_context(self, key: str, session_id: str = None) -> Any:
        """Get context value."""
        if session_id:
            return self._context.get_session(session_id, key)
        return self._context.get_global(key)

    # Information methods

    def get_subsystems(self) -> Dict[str, Dict[str, Any]]:
        """Get all registered subsystems."""
        return {
            name: {
                "category": info.category.value,
                "capabilities": info.capabilities,
                "status": info.status,
                "performance_score": info.performance_score,
                "success_count": info.success_count,
                "error_count": info.error_count
            }
            for name, info in self._subsystems.items()
        }

    def get_capabilities(self) -> Dict[str, List[str]]:
        """Get all capabilities with their providing subsystems."""
        return dict(self._router._capability_map)

    def get_stats(self) -> Dict[str, Any]:
        """Get hub statistics."""
        return {
            **self._stats,
            "registered_subsystems": len(self._subsystems),
            "total_capabilities": len(self._router._capability_map),
            "active_requests": len(self._active_requests),
            "emergent_patterns": len(self._emergent_patterns)
        }

    def get_performance_report(self) -> Dict[str, Any]:
        """Get performance report."""
        if self._optimizer:
            return self._optimizer.get_performance_report()
        return {}


# Global instance
_integration_hub: Optional[UltimateIntegrationHub] = None


def get_integration_hub() -> UltimateIntegrationHub:
    """Get the global integration hub."""
    global _integration_hub
    if _integration_hub is None:
        _integration_hub = UltimateIntegrationHub()
    return _integration_hub


async def demo():
    """Demonstrate Ultimate Integration Hub."""
    hub = get_integration_hub()

    print("=== ULTIMATE INTEGRATION HUB DEMO ===\n")

    # Register mock subsystems
    class MockSubsystem:
        def __init__(self, name):
            self.name = name

        async def process(self, content, context):
            return {"processed_by": self.name, "content": content[:50], "status": "success"}

    # Register subsystems
    subsystems = [
        ("reasoning_engine", SubsystemCategory.CORE, ["reason", "analyze", "decide"]),
        ("code_generator", SubsystemCategory.CREATION, ["generate_code", "refactor", "optimize"]),
        ("memory_system", SubsystemCategory.MEMORY, ["store", "retrieve", "search"]),
        ("execution_engine", SubsystemCategory.EXECUTION, ["execute", "run", "deploy"]),
        ("analysis_engine", SubsystemCategory.ANALYSIS, ["analyze", "evaluate", "understand"]),
    ]

    for name, category, caps in subsystems:
        hub.register_subsystem(
            name=name,
            instance=MockSubsystem(name),
            category=category,
            capabilities=caps
        )

    print("Registered subsystems:")
    for name in hub._subsystems:
        print(f"  - {name}")

    # Process a request
    print("\n=== PROCESSING REQUEST ===")

    request = UnifiedRequest(
        request_id="demo_001",
        content="Analyze this code and generate improvements with detailed reasoning",
        intent="improvement",
        required_capabilities=["analyze", "generate_code", "reason"],
        priority=RequestPriority.HIGH
    )

    print(f"Request: {request.content}")
    print(f"Required capabilities: {request.required_capabilities}")

    response = await hub.process(request)

    print(f"\n=== RESPONSE ===")
    print(f"Success: {response.success}")
    print(f"Quality: {response.quality.value}")
    print(f"Subsystems used: {response.subsystems_used}")
    print(f"Processing time: {response.processing_time_ms:.2f}ms")
    print(f"Synthesis: {response.synthesis}")

    if response.insights:
        print(f"Insights: {response.insights}")

    # Quick process
    print("\n=== QUICK PROCESS ===")
    quick_response = await hub.quick_process(
        "Execute and deploy the application",
        capabilities=["execute", "deploy"]
    )
    print(f"Quick result: {quick_response.success}, subsystems: {quick_response.subsystems_used}")

    # Show stats
    print("\n=== HUB STATISTICS ===")
    stats = hub.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")

    # Show capabilities
    print("\n=== AVAILABLE CAPABILITIES ===")
    capabilities = hub.get_capabilities()
    for cap, subsystems in list(capabilities.items())[:5]:
        print(f"  {cap}: {subsystems}")


if __name__ == "__main__":
    asyncio.run(demo())

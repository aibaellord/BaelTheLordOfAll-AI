"""
BAEL Master Integration Layer

The supreme integration layer that wires all BAEL systems together:
- Supreme Controller
- Reasoning Cascade
- Cognitive Pipeline
- Knowledge Synthesis
- Workflow Orchestration
- Agent Swarm
- Tool Orchestration
- Web Research
- Code Execution

This is the neural highway connecting all of BAEL's capabilities.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union
from uuid import uuid4

logger = logging.getLogger(__name__)


class IntegrationMode(Enum):
    """Integration modes."""
    MINIMAL = "minimal"        # Core only
    STANDARD = "standard"      # Core + common tools
    FULL = "full"              # All systems
    AUTONOMOUS = "autonomous"  # Full + self-evolution


class SystemState(Enum):
    """State of integrated system."""
    INITIALIZING = "initializing"
    READY = "ready"
    PROCESSING = "processing"
    LEARNING = "learning"
    EVOLVING = "evolving"
    ERROR = "error"
    SHUTDOWN = "shutdown"


@dataclass
class SystemHealth:
    """Health status of a system."""
    name: str
    healthy: bool
    status: str = "unknown"
    last_check: datetime = field(default_factory=datetime.now)
    error: Optional[str] = None
    metrics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class IntegrationConfig:
    """Configuration for master integration."""
    mode: IntegrationMode = IntegrationMode.STANDARD

    # System toggles
    enable_reasoning: bool = True
    enable_memory: bool = True
    enable_knowledge: bool = True
    enable_workflow: bool = True
    enable_swarm: bool = False
    enable_tools: bool = True
    enable_research: bool = True
    enable_code_execution: bool = True
    enable_evolution: bool = False
    enable_exploitation: bool = False

    # Performance tuning
    max_concurrent_operations: int = 10
    default_timeout_seconds: float = 60.0
    enable_caching: bool = True
    cache_ttl_seconds: int = 300

    # Logging
    log_level: str = "INFO"
    log_operations: bool = True


@dataclass
class OperationContext:
    """Context for an operation."""
    id: str
    operation: str
    started_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    parent_id: Optional[str] = None


@dataclass
class OperationResult:
    """Result of an integrated operation."""
    context: OperationContext
    success: bool
    result: Any = None
    error: Optional[str] = None
    completed_at: datetime = field(default_factory=datetime.now)
    metrics: Dict[str, Any] = field(default_factory=dict)


class SystemRegistry:
    """Registry of all BAEL systems."""

    def __init__(self):
        self.systems: Dict[str, Any] = {}
        self.health: Dict[str, SystemHealth] = {}
        self.dependencies: Dict[str, List[str]] = {}

    def register(
        self,
        name: str,
        system: Any,
        dependencies: List[str] = None
    ):
        """Register a system."""
        self.systems[name] = system
        self.dependencies[name] = dependencies or []
        self.health[name] = SystemHealth(name=name, healthy=True, status="registered")
        logger.info(f"Registered system: {name}")

    def get(self, name: str) -> Optional[Any]:
        """Get a system by name."""
        return self.systems.get(name)

    def get_all(self) -> Dict[str, Any]:
        """Get all systems."""
        return self.systems.copy()

    async def check_health(self, name: str) -> SystemHealth:
        """Check health of a system."""
        if name not in self.systems:
            return SystemHealth(name=name, healthy=False, status="not_found")

        system = self.systems[name]
        health = SystemHealth(name=name, healthy=True, status="healthy")

        # Check if system has health check method
        if hasattr(system, 'health_check'):
            try:
                result = await system.health_check()
                health.healthy = result.get('healthy', True)
                health.status = result.get('status', 'unknown')
                health.metrics = result.get('metrics', {})
            except Exception as e:
                health.healthy = False
                health.status = "error"
                health.error = str(e)

        self.health[name] = health
        return health

    async def check_all_health(self) -> Dict[str, SystemHealth]:
        """Check health of all systems."""
        tasks = [self.check_health(name) for name in self.systems]
        await asyncio.gather(*tasks)
        return self.health.copy()


class EventBus:
    """Event bus for inter-system communication."""

    def __init__(self):
        self.subscribers: Dict[str, List[Callable]] = {}
        self.history: List[Dict[str, Any]] = []

    def subscribe(self, event_type: str, handler: Callable):
        """Subscribe to an event type."""
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(handler)

    def unsubscribe(self, event_type: str, handler: Callable):
        """Unsubscribe from an event type."""
        if event_type in self.subscribers:
            self.subscribers[event_type].remove(handler)

    async def publish(self, event_type: str, data: Any):
        """Publish an event."""
        event = {
            "type": event_type,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
        self.history.append(event)

        if event_type in self.subscribers:
            for handler in self.subscribers[event_type]:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(data)
                    else:
                        handler(data)
                except Exception as e:
                    logger.error(f"Event handler error: {e}")


class MasterIntegrationLayer:
    """
    The supreme integration layer.

    Connects all BAEL systems and provides unified access.
    """

    def __init__(self, config: IntegrationConfig = None):
        self.config = config or IntegrationConfig()
        self.state = SystemState.INITIALIZING

        # Core infrastructure
        self.registry = SystemRegistry()
        self.event_bus = EventBus()

        # Operation tracking
        self.active_operations: Dict[str, OperationContext] = {}
        self.completed_operations: List[OperationResult] = []

        # Semaphore for concurrency control
        self._semaphore = asyncio.Semaphore(self.config.max_concurrent_operations)

    async def initialize(self):
        """Initialize all systems based on configuration."""
        logger.info(f"Initializing BAEL in {self.config.mode.value} mode")

        try:
            # Initialize systems based on config
            if self.config.enable_reasoning:
                await self._init_reasoning()

            if self.config.enable_memory:
                await self._init_memory()

            if self.config.enable_knowledge:
                await self._init_knowledge()

            if self.config.enable_workflow:
                await self._init_workflow()

            if self.config.enable_swarm:
                await self._init_swarm()

            if self.config.enable_tools:
                await self._init_tools()

            if self.config.enable_research:
                await self._init_research()

            if self.config.enable_code_execution:
                await self._init_code_execution()

            if self.config.enable_evolution:
                await self._init_evolution()

            if self.config.enable_exploitation:
                await self._init_exploitation()

            self.state = SystemState.READY
            await self.event_bus.publish("system.ready", {"mode": self.config.mode.value})
            logger.info("BAEL initialization complete")

        except Exception as e:
            self.state = SystemState.ERROR
            logger.error(f"Initialization failed: {e}")
            raise

    async def _init_reasoning(self):
        """Initialize reasoning systems."""
        try:
            from core.supreme.reasoning_cascade import ReasoningCascade
            cascade = ReasoningCascade()
            self.registry.register("reasoning", cascade)
        except ImportError:
            logger.warning("Reasoning cascade not available")

    async def _init_memory(self):
        """Initialize memory systems."""
        try:
            from core.supreme.cognitive_pipeline import CognitivePipeline
            pipeline = CognitivePipeline()
            self.registry.register("memory", pipeline)
        except ImportError:
            logger.warning("Cognitive pipeline not available")

    async def _init_knowledge(self):
        """Initialize knowledge systems."""
        try:
            from core.knowledge.knowledge_synthesis_pipeline import \
                KnowledgeSynthesisPipeline
            pipeline = KnowledgeSynthesisPipeline()
            self.registry.register("knowledge", pipeline)
        except ImportError:
            logger.warning("Knowledge synthesis not available")

    async def _init_workflow(self):
        """Initialize workflow systems."""
        try:
            from core.workflow.workflow_orchestrator import \
                WorkflowOrchestrator
            orchestrator = WorkflowOrchestrator()
            self.registry.register("workflow", orchestrator)
        except ImportError:
            logger.warning("Workflow orchestrator not available")

    async def _init_swarm(self):
        """Initialize swarm systems."""
        try:
            from core.swarm.swarm_coordinator import SwarmCoordinator
            coordinator = SwarmCoordinator()
            self.registry.register("swarm", coordinator)
        except ImportError:
            logger.warning("Swarm coordinator not available")

    async def _init_tools(self):
        """Initialize tool systems."""
        try:
            from core.tools.tool_orchestration import ToolOrchestrator
            orchestrator = ToolOrchestrator()
            self.registry.register("tools", orchestrator)
        except ImportError:
            logger.warning("Tool orchestrator not available")

    async def _init_research(self):
        """Initialize research systems."""
        try:
            from core.research.web_research_engine import WebResearchEngine
            engine = WebResearchEngine()
            self.registry.register("research", engine)
        except ImportError:
            logger.warning("Research engine not available")

    async def _init_code_execution(self):
        """Initialize code execution systems."""
        try:
            from core.execution.code_sandbox import CodeExecutionSandbox
            sandbox = CodeExecutionSandbox()
            self.registry.register("execution", sandbox)
        except ImportError:
            logger.warning("Code sandbox not available")

    async def _init_evolution(self):
        """Initialize evolution systems."""
        try:
            from core.evolution.self_evolution import SelfEvolutionEngine
            engine = SelfEvolutionEngine()
            self.registry.register("evolution", engine)
        except ImportError:
            logger.warning("Evolution engine not available")

    async def _init_exploitation(self):
        """Initialize exploitation systems."""
        try:
            from core.exploitation.exploitation_engine import \
                ExploitationEngine
            engine = ExploitationEngine()
            self.registry.register("exploitation", engine)
        except ImportError:
            logger.warning("Exploitation engine not available")

    async def process(
        self,
        query: str,
        context: Dict[str, Any] = None
    ) -> OperationResult:
        """Process a query through the integrated system."""
        op_context = OperationContext(
            id=str(uuid4())[:8],
            operation="process",
            metadata={"query": query, "context": context}
        )

        self.active_operations[op_context.id] = op_context
        self.state = SystemState.PROCESSING

        try:
            async with self._semaphore:
                result = await self._execute_pipeline(query, context or {})

            op_result = OperationResult(
                context=op_context,
                success=True,
                result=result
            )

        except Exception as e:
            op_result = OperationResult(
                context=op_context,
                success=False,
                error=str(e)
            )
            logger.error(f"Processing error: {e}")

        finally:
            del self.active_operations[op_context.id]
            self.completed_operations.append(op_result)

            if not self.active_operations:
                self.state = SystemState.READY

        return op_result

    async def _execute_pipeline(
        self,
        query: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute the processing pipeline."""
        result = {"query": query, "stages": []}

        # Stage 1: Reasoning
        reasoning = self.registry.get("reasoning")
        if reasoning:
            try:
                reason_result = await self._safe_call(
                    reasoning.reason, query
                )
                result["reasoning"] = reason_result
                result["stages"].append("reasoning")
            except Exception as e:
                logger.warning(f"Reasoning stage failed: {e}")

        # Stage 2: Memory retrieval
        memory = self.registry.get("memory")
        if memory:
            try:
                mem_result = await self._safe_call(
                    memory.retrieve, query
                )
                result["memory"] = mem_result
                result["stages"].append("memory")
            except Exception as e:
                logger.warning(f"Memory stage failed: {e}")

        # Stage 3: Knowledge synthesis
        knowledge = self.registry.get("knowledge")
        if knowledge:
            try:
                know_result = await self._safe_call(
                    knowledge.query, query
                )
                result["knowledge"] = know_result
                result["stages"].append("knowledge")
            except Exception as e:
                logger.warning(f"Knowledge stage failed: {e}")

        # Stage 4: Research if needed
        if self._needs_research(query):
            research = self.registry.get("research")
            if research:
                try:
                    research_result = await self._safe_call(
                        research.quick_answer, query
                    )
                    result["research"] = research_result
                    result["stages"].append("research")
                except Exception as e:
                    logger.warning(f"Research stage failed: {e}")

        # Stage 5: Tool execution if needed
        if self._needs_tools(query):
            tools = self.registry.get("tools")
            if tools:
                try:
                    tool_result = await self._safe_call(
                        tools.select_and_execute, query, {}
                    )
                    result["tools"] = tool_result
                    result["stages"].append("tools")
                except Exception as e:
                    logger.warning(f"Tools stage failed: {e}")

        return result

    async def _safe_call(self, func: Callable, *args, **kwargs) -> Any:
        """Safely call a function with timeout."""
        if asyncio.iscoroutinefunction(func):
            return await asyncio.wait_for(
                func(*args, **kwargs),
                timeout=self.config.default_timeout_seconds
            )
        else:
            return func(*args, **kwargs)

    def _needs_research(self, query: str) -> bool:
        """Check if query needs web research."""
        research_keywords = ["search", "find", "look up", "what is", "who is", "latest"]
        return any(k in query.lower() for k in research_keywords)

    def _needs_tools(self, query: str) -> bool:
        """Check if query needs tool execution."""
        tool_keywords = ["calculate", "convert", "translate", "execute", "run"]
        return any(k in query.lower() for k in tool_keywords)

    async def execute_workflow(
        self,
        workflow_name: str,
        inputs: Dict[str, Any]
    ) -> OperationResult:
        """Execute a named workflow."""
        workflow = self.registry.get("workflow")
        if not workflow:
            return OperationResult(
                context=OperationContext(id="0", operation="workflow"),
                success=False,
                error="Workflow system not available"
            )

        op_context = OperationContext(
            id=str(uuid4())[:8],
            operation="workflow",
            metadata={"workflow": workflow_name, "inputs": inputs}
        )

        try:
            result = await workflow.execute_pipeline(workflow_name, inputs)
            return OperationResult(
                context=op_context,
                success=True,
                result=result
            )
        except Exception as e:
            return OperationResult(
                context=op_context,
                success=False,
                error=str(e)
            )

    async def execute_code(
        self,
        code: str,
        language: str = "python"
    ) -> OperationResult:
        """Execute code in sandbox."""
        execution = self.registry.get("execution")
        if not execution:
            return OperationResult(
                context=OperationContext(id="0", operation="execute"),
                success=False,
                error="Execution system not available"
            )

        op_context = OperationContext(
            id=str(uuid4())[:8],
            operation="execute",
            metadata={"language": language}
        )

        try:
            result = await execution.execute_python(code)
            return OperationResult(
                context=op_context,
                success=result.success,
                result={"stdout": result.stdout, "result": result.return_value},
                error=result.error
            )
        except Exception as e:
            return OperationResult(
                context=op_context,
                success=False,
                error=str(e)
            )

    async def research(
        self,
        query: str,
        depth: int = 2
    ) -> OperationResult:
        """Conduct research on a topic."""
        research = self.registry.get("research")
        if not research:
            return OperationResult(
                context=OperationContext(id="0", operation="research"),
                success=False,
                error="Research system not available"
            )

        op_context = OperationContext(
            id=str(uuid4())[:8],
            operation="research",
            metadata={"query": query, "depth": depth}
        )

        try:
            report = await research.research(query, depth=depth)
            return OperationResult(
                context=op_context,
                success=True,
                result=report
            )
        except Exception as e:
            return OperationResult(
                context=op_context,
                success=False,
                error=str(e)
            )

    async def get_status(self) -> Dict[str, Any]:
        """Get system status."""
        health = await self.registry.check_all_health()

        return {
            "state": self.state.value,
            "mode": self.config.mode.value,
            "systems_registered": len(self.registry.systems),
            "systems": list(self.registry.systems.keys()),
            "health": {
                name: {
                    "healthy": h.healthy,
                    "status": h.status
                }
                for name, h in health.items()
            },
            "active_operations": len(self.active_operations),
            "completed_operations": len(self.completed_operations)
        }

    async def shutdown(self):
        """Shutdown the integration layer."""
        logger.info("Shutting down BAEL")
        self.state = SystemState.SHUTDOWN

        # Publish shutdown event
        await self.event_bus.publish("system.shutdown", {})

        # Clean up systems
        for name, system in self.registry.systems.items():
            if hasattr(system, 'shutdown'):
                try:
                    await system.shutdown()
                except Exception as e:
                    logger.warning(f"Error shutting down {name}: {e}")

        logger.info("BAEL shutdown complete")


# Factory function
def create_bael(
    mode: IntegrationMode = IntegrationMode.STANDARD
) -> MasterIntegrationLayer:
    """Create and return a BAEL instance."""
    config = IntegrationConfig(mode=mode)

    if mode == IntegrationMode.MINIMAL:
        config.enable_workflow = False
        config.enable_swarm = False
        config.enable_research = False
        config.enable_code_execution = False

    elif mode == IntegrationMode.FULL:
        config.enable_swarm = True

    elif mode == IntegrationMode.AUTONOMOUS:
        config.enable_swarm = True
        config.enable_evolution = True
        config.enable_exploitation = True

    return MasterIntegrationLayer(config)


async def demo():
    """Demonstrate master integration layer."""
    print("=" * 60)
    print("BAEL Master Integration Layer Demo")
    print("=" * 60)

    # Create BAEL
    bael = create_bael(IntegrationMode.STANDARD)

    # Initialize
    print("\nInitializing BAEL...")
    await bael.initialize()

    # Get status
    status = await bael.get_status()
    print(f"\nSystem Status:")
    print(f"  State: {status['state']}")
    print(f"  Mode: {status['mode']}")
    print(f"  Systems: {status['systems']}")

    # Process a query
    print("\nProcessing query...")
    result = await bael.process("What are the key concepts in machine learning?")
    print(f"  Success: {result.success}")
    print(f"  Stages: {result.result.get('stages', []) if result.result else []}")

    # Execute code
    print("\nExecuting code...")
    code_result = await bael.execute_code("result = 2 + 2\nprint(result)")
    print(f"  Success: {code_result.success}")
    if code_result.result:
        print(f"  Output: {code_result.result.get('stdout', '').strip()}")

    # Shutdown
    await bael.shutdown()

    print("\n✓ Multi-system integration")
    print("✓ Event-driven communication")
    print("✓ Health monitoring")
    print("✓ Pipeline processing")
    print("✓ Operation tracking")
    print("✓ Graceful shutdown")


if __name__ == "__main__":
    asyncio.run(demo())

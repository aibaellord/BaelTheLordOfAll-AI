"""
Comprehensive tests for all new BAEL modules.

Tests cover:
- Workflow Orchestrator
- Agent Swarm Coordinator
- Tool Orchestration
- Knowledge Synthesis Pipeline
- Web Research Engine
- Code Execution Sandbox
- Master Integration Layer
"""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

# =============================================================================
# WORKFLOW ORCHESTRATOR TESTS
# =============================================================================

class TestWorkflowOrchestrator:
    """Tests for workflow orchestration."""

    @pytest.fixture
    def workflow_builder(self):
        from core.workflow import WorkflowBuilder
        return WorkflowBuilder("Test Workflow")

    @pytest.fixture
    def orchestrator(self):
        from core.workflow import WorkflowOrchestrator
        return WorkflowOrchestrator()

    def test_workflow_builder_creates_start_node(self, workflow_builder):
        """Test that builder creates start node."""
        workflow_builder.start()
        assert "start" in workflow_builder.workflow.nodes
        assert workflow_builder.workflow.start_node_id == "start"

    def test_workflow_builder_adds_task(self, workflow_builder):
        """Test adding task to workflow."""
        def dummy_task():
            return "done"

        workflow = (
            workflow_builder
            .start()
            .task("Test Task", dummy_task)
            .end()
            .build()
        )

        assert len(workflow.nodes) == 3  # start, task, end

    def test_workflow_validation(self, workflow_builder):
        """Test workflow validation."""
        # Incomplete workflow should have errors
        workflow = workflow_builder.workflow
        errors = workflow.validate()

        assert len(errors) > 0
        assert any("start" in e.lower() for e in errors)

    @pytest.mark.asyncio
    async def test_workflow_execution(self, orchestrator):
        """Test executing a workflow."""
        from core.workflow import WorkflowBuilder

        results = []

        def step1():
            results.append("step1")
            return "step1_done"

        def step2():
            results.append("step2")
            return "step2_done"

        workflow = (
            WorkflowBuilder("Sequential")
            .start()
            .task("Step 1", step1, output_key="s1")
            .task("Step 2", step2, output_key="s2")
            .end()
            .build()
        )

        context = await orchestrator.execute_workflow(workflow)

        assert "step1" in results
        assert "step2" in results


# =============================================================================
# SWARM COORDINATOR TESTS
# =============================================================================

class TestSwarmCoordinator:
    """Tests for agent swarm coordination."""

    @pytest.fixture
    async def coordinator(self):
        from core.swarm import SwarmConfig, SwarmCoordinator
        return SwarmCoordinator(SwarmConfig())

    @pytest.mark.asyncio
    async def test_spawn_agent(self, coordinator):
        """Test spawning an agent."""
        from core.swarm import AgentRole

        agent = await coordinator.spawn_agent(AgentRole.RESEARCHER, "Test Agent")

        assert agent.id in coordinator.agents
        assert agent.role == AgentRole.RESEARCHER

    @pytest.mark.asyncio
    async def test_terminate_agent(self, coordinator):
        """Test terminating an agent."""
        from core.swarm import AgentRole

        agent = await coordinator.spawn_agent(AgentRole.EXECUTOR)
        agent_id = agent.id

        await coordinator.terminate_agent(agent_id)

        assert agent_id not in coordinator.agents

    @pytest.mark.asyncio
    async def test_submit_task(self, coordinator):
        """Test submitting a task."""
        from core.swarm import AgentRole, AgentTask

        # Spawn an agent first
        await coordinator.spawn_agent(AgentRole.EXECUTOR)

        task = AgentTask(
            id="t1",
            description="Test task"
        )

        task_id = await coordinator.submit_task(task)
        assert task_id == "t1"

    @pytest.mark.asyncio
    async def test_request_consensus(self, coordinator):
        """Test consensus mechanism."""
        from core.swarm import AgentRole

        # Spawn multiple agents
        for i in range(5):
            await coordinator.spawn_agent(AgentRole.ANALYST, f"Analyst_{i}")

        result = await coordinator.request_consensus(
            topic="Test decision",
            options=["option_a", "option_b", "option_c"]
        )

        assert "votes" in result
        assert "consensus" in result

    @pytest.mark.asyncio
    async def test_swarm_status(self, coordinator):
        """Test getting swarm status."""
        from core.swarm import AgentRole

        await coordinator.spawn_agent(AgentRole.RESEARCHER)
        await coordinator.spawn_agent(AgentRole.ANALYST)

        status = coordinator.get_swarm_status()

        assert status["total_agents"] == 2


# =============================================================================
# TOOL ORCHESTRATION TESTS
# =============================================================================

class TestToolOrchestration:
    """Tests for tool orchestration."""

    @pytest.fixture
    def orchestrator(self):
        from core.tools.tool_orchestration import ToolOrchestrator
        return ToolOrchestrator()

    @pytest.fixture
    def sample_tool(self):
        from core.tools.tool_orchestration import (Tool, ToolCategory,
                                                   ToolSchema)

        def sample_handler(x: int, y: int) -> int:
            return x + y

        return Tool(
            id="t1",
            name="adder",
            category=ToolCategory.UTILITY,
            schema=ToolSchema(
                name="adder",
                description="Adds two numbers"
            ),
            handler=sample_handler
        )

    def test_register_tool(self, orchestrator, sample_tool):
        """Test tool registration."""
        orchestrator.register(sample_tool)

        assert "adder" in orchestrator.tools

    @pytest.mark.asyncio
    async def test_execute_tool(self, orchestrator, sample_tool):
        """Test tool execution."""
        orchestrator.register(sample_tool)

        result = await orchestrator.execute("adder", {"x": 5, "y": 3})

        assert result.success
        assert result.result == 8

    @pytest.mark.asyncio
    async def test_execute_nonexistent_tool(self, orchestrator):
        """Test executing non-existent tool."""
        result = await orchestrator.execute("nonexistent", {})

        assert not result.success
        assert "not found" in result.error.lower()

    def test_get_tools_by_category(self, orchestrator, sample_tool):
        """Test filtering tools by category."""
        from core.tools.tool_orchestration import ToolCategory

        orchestrator.register(sample_tool)

        tools = orchestrator.get_tools_by_category(ToolCategory.UTILITY)
        assert len(tools) == 1

        tools = orchestrator.get_tools_by_category(ToolCategory.SEARCH)
        assert len(tools) == 0


# =============================================================================
# KNOWLEDGE SYNTHESIS TESTS
# =============================================================================

class TestKnowledgeSynthesis:
    """Tests for knowledge synthesis pipeline."""

    @pytest.fixture
    def pipeline(self):
        from core.knowledge.knowledge_synthesis_pipeline import \
            KnowledgeSynthesisPipeline
        return KnowledgeSynthesisPipeline()

    @pytest.fixture
    def sample_source(self):
        from core.knowledge.knowledge_synthesis_pipeline import (
            KnowledgeSource, SourceType)
        return KnowledgeSource(
            id="s1",
            source_type=SourceType.WEB,
            name="Test Source",
            reliability=0.8
        )

    @pytest.mark.asyncio
    async def test_ingest_knowledge(self, pipeline, sample_source):
        """Test ingesting knowledge."""
        item = await pipeline.ingest(
            "Python is a programming language.",
            sample_source
        )

        assert item.id in pipeline.knowledge_items
        assert item.content == "Python is a programming language."

    @pytest.mark.asyncio
    async def test_query_knowledge(self, pipeline, sample_source):
        """Test querying knowledge."""
        await pipeline.ingest("Python is great for data science.", sample_source)
        await pipeline.ingest("JavaScript runs in browsers.", sample_source)

        results = await pipeline.query("Python data")

        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_get_statistics(self, pipeline, sample_source):
        """Test getting knowledge statistics."""
        await pipeline.ingest("Fact 1", sample_source)
        await pipeline.ingest("Fact 2", sample_source)

        stats = pipeline.get_statistics()

        assert stats["total_items"] == 2


# =============================================================================
# WEB RESEARCH TESTS
# =============================================================================

class TestWebResearch:
    """Tests for web research engine."""

    @pytest.fixture
    def engine(self):
        from core.research import WebResearchEngine
        return WebResearchEngine()

    @pytest.mark.asyncio
    async def test_search(self, engine):
        """Test basic search."""
        from core.research import ResearchQuery, SearchEngine

        query = ResearchQuery(
            query="artificial intelligence",
            engines=[SearchEngine.GOOGLE],
            max_results_per_engine=5
        )

        results = await engine.search(query)

        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_quick_answer(self, engine):
        """Test quick answer."""
        answer = await engine.quick_answer("What is machine learning?")

        assert "question" in answer
        assert "answer" in answer

    @pytest.mark.asyncio
    async def test_research(self, engine):
        """Test full research."""
        report = await engine.research("quantum computing", depth=1)

        assert report.query == "quantum computing"
        assert report.sources_consulted > 0


# =============================================================================
# CODE EXECUTION TESTS
# =============================================================================

class TestCodeExecution:
    """Tests for code execution sandbox."""

    @pytest.fixture
    def sandbox(self):
        from core.execution import CodeExecutionSandbox
        return CodeExecutionSandbox()

    @pytest.mark.asyncio
    async def test_execute_python(self, sandbox):
        """Test Python execution."""
        result = await sandbox.execute_python("print('hello')")

        assert result.success
        assert "hello" in result.stdout

    @pytest.mark.asyncio
    async def test_execute_with_result(self, sandbox):
        """Test execution with return value."""
        result = await sandbox.execute_python("result = 2 + 2")

        assert result.success
        assert result.return_value == 4

    @pytest.mark.asyncio
    async def test_security_violation(self, sandbox):
        """Test security violation detection."""
        from core.execution import SecurityLevel

        result = await sandbox.execute_python(
            "import os\nos.system('ls')",
            security_level=SecurityLevel.STRICT
        )

        assert not result.success
        assert result.status.value == "security_violation"

    @pytest.mark.asyncio
    async def test_timeout(self, sandbox):
        """Test execution timeout."""
        result = await sandbox.execute_python(
            "while True: pass",
            timeout=0.5
        )

        assert not result.success
        assert result.status.value == "timeout"

    def test_create_session(self, sandbox):
        """Test session creation."""
        session_id = sandbox.create_session()

        assert session_id in sandbox.session_states


# =============================================================================
# MASTER INTEGRATION TESTS
# =============================================================================

class TestMasterIntegration:
    """Tests for master integration layer."""

    @pytest.fixture
    def integration(self):
        from core.integration import (IntegrationConfig, IntegrationMode,
                                      MasterIntegrationLayer)
        config = IntegrationConfig(mode=IntegrationMode.MINIMAL)
        return MasterIntegrationLayer(config)

    @pytest.mark.asyncio
    async def test_initialization(self, integration):
        """Test integration layer initialization."""
        await integration.initialize()

        assert integration.state.value == "ready"

    @pytest.mark.asyncio
    async def test_get_status(self, integration):
        """Test getting system status."""
        await integration.initialize()

        status = await integration.get_status()

        assert "state" in status
        assert "mode" in status
        assert "systems" in status

    @pytest.mark.asyncio
    async def test_process_query(self, integration):
        """Test processing a query."""
        await integration.initialize()

        result = await integration.process("Test query")

        assert result is not None
        assert "query" in result.result

    @pytest.mark.asyncio
    async def test_shutdown(self, integration):
        """Test graceful shutdown."""
        await integration.initialize()
        await integration.shutdown()

        assert integration.state.value == "shutdown"


# =============================================================================
# EVENT BUS TESTS
# =============================================================================

class TestEventBus:
    """Tests for event bus."""

    @pytest.fixture
    def event_bus(self):
        from core.integration import EventBus
        return EventBus()

    @pytest.mark.asyncio
    async def test_subscribe_and_publish(self, event_bus):
        """Test subscribing and publishing events."""
        received = []

        def handler(data):
            received.append(data)

        event_bus.subscribe("test_event", handler)
        await event_bus.publish("test_event", {"value": 42})

        assert len(received) == 1
        assert received[0]["value"] == 42

    @pytest.mark.asyncio
    async def test_async_handler(self, event_bus):
        """Test async event handlers."""
        received = []

        async def async_handler(data):
            received.append(data)

        event_bus.subscribe("async_event", async_handler)
        await event_bus.publish("async_event", {"async": True})

        assert len(received) == 1

    def test_unsubscribe(self, event_bus):
        """Test unsubscribing from events."""
        def handler(data):
            pass

        event_bus.subscribe("event", handler)
        event_bus.unsubscribe("event", handler)

        assert len(event_bus.subscribers.get("event", [])) == 0


# =============================================================================
# INTEGRATION FACTORY TESTS
# =============================================================================

class TestBAELFactory:
    """Tests for BAEL factory function."""

    def test_create_minimal(self):
        """Test creating minimal BAEL."""
        from core.integration import IntegrationMode, create_bael

        bael = create_bael(IntegrationMode.MINIMAL)

        assert not bael.config.enable_workflow
        assert not bael.config.enable_swarm

    def test_create_standard(self):
        """Test creating standard BAEL."""
        from core.integration import IntegrationMode, create_bael

        bael = create_bael(IntegrationMode.STANDARD)

        assert bael.config.enable_reasoning
        assert bael.config.enable_tools

    def test_create_autonomous(self):
        """Test creating autonomous BAEL."""
        from core.integration import IntegrationMode, create_bael

        bael = create_bael(IntegrationMode.AUTONOMOUS)

        assert bael.config.enable_swarm
        assert bael.config.enable_evolution
        assert bael.config.enable_exploitation


# =============================================================================
# WORKFLOW PIPELINE TESTS
# =============================================================================

class TestToolPipeline:
    """Tests for tool pipelines."""

    @pytest.fixture
    def orchestrator(self):
        from core.tools.tool_orchestration import (Tool, ToolCategory,
                                                   ToolOrchestrator,
                                                   ToolSchema)
        orch = ToolOrchestrator()

        # Register sample tools
        def add(a: int, b: int) -> int:
            return a + b

        def multiply(x: int, factor: int) -> int:
            return x * factor

        orch.register(Tool(
            id="t1",
            name="add",
            category=ToolCategory.UTILITY,
            schema=ToolSchema(name="add", description="Add numbers"),
            handler=add
        ))

        orch.register(Tool(
            id="t2",
            name="multiply",
            category=ToolCategory.UTILITY,
            schema=ToolSchema(name="multiply", description="Multiply numbers"),
            handler=multiply
        ))

        return orch

    @pytest.mark.asyncio
    async def test_pipeline_execution(self, orchestrator):
        """Test pipeline execution."""
        from core.tools.tool_orchestration import ToolPipeline

        pipeline = (
            ToolPipeline("math_pipeline")
            .add_step("add", {"a": "x", "b": "y"})
        )

        orchestrator.register_pipeline(pipeline)

        results = await orchestrator.execute_pipeline(
            "math_pipeline",
            {"x": 5, "y": 3}
        )

        assert len(results) == 1
        assert results[0].success


# =============================================================================
# RUNNER
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

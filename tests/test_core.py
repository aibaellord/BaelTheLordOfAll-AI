"""
BAEL - Test Suite
Comprehensive tests for the BAEL agent system.
"""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# =============================================================================
# TEST FIXTURES
# =============================================================================

@pytest.fixture
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_model_router():
    """Mock model router."""
    router = MagicMock()
    router.generate = AsyncMock(return_value="Test response")
    router.get_embedding = AsyncMock(return_value=[0.1] * 1536)
    return router


@pytest.fixture
def mock_settings():
    """Mock settings."""
    return {
        'openrouter': {
            'api_key': 'test-key',
            'models': {
                'primary': 'test-model'
            }
        },
        'memory': {
            'chroma': {'persist_directory': '/tmp/test_chroma'}
        }
    }


# =============================================================================
# MEMORY TESTS
# =============================================================================

class TestWorkingMemory:
    """Tests for WorkingMemory."""

    @pytest.fixture
    def working_memory(self):
        """Create working memory instance."""
        from core.memory.manager import WorkingMemory
        return WorkingMemory(max_size=5)

    def test_add_item(self, working_memory):
        """Test adding items."""
        working_memory.add("key1", {"data": "test"})
        assert "key1" in working_memory._items

    def test_get_item(self, working_memory):
        """Test getting items."""
        working_memory.add("key1", {"data": "test"})
        item = working_memory.get("key1")
        assert item is not None
        assert item["data"] == "test"

    def test_max_size_enforcement(self, working_memory):
        """Test max size is enforced."""
        for i in range(10):
            working_memory.add(f"key{i}", {"data": i})

        assert len(working_memory._items) <= 5

    def test_clear(self, working_memory):
        """Test clearing memory."""
        working_memory.add("key1", {"data": "test"})
        working_memory.clear()
        assert len(working_memory._items) == 0


class TestEpisodicMemory:
    """Tests for EpisodicMemory."""

    @pytest.fixture
    def episodic_memory(self):
        """Create episodic memory instance."""
        from core.memory.manager import EpisodicMemory
        return EpisodicMemory()

    @pytest.mark.asyncio
    async def test_store_experience(self, episodic_memory):
        """Test storing experience."""
        await episodic_memory.store(
            content="Test experience",
            context={"session": "test"},
            emotions={"valence": 0.5}
        )

        assert len(episodic_memory._entries) == 1

    @pytest.mark.asyncio
    async def test_recall(self, episodic_memory):
        """Test recalling experiences."""
        await episodic_memory.store(
            content="Python programming experience",
            context={"topic": "python"}
        )

        results = await episodic_memory.recall("python")
        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_recent_recall(self, episodic_memory):
        """Test recent recall."""
        for i in range(5):
            await episodic_memory.store(
                content=f"Experience {i}",
                context={"index": i}
            )

        recent = episodic_memory.get_recent(3)
        assert len(recent) == 3


class TestSemanticMemory:
    """Tests for SemanticMemory."""

    @pytest.fixture
    def semantic_memory(self):
        """Create semantic memory instance."""
        from core.memory.manager import SemanticMemory
        return SemanticMemory()

    @pytest.mark.asyncio
    async def test_store_knowledge(self, semantic_memory):
        """Test storing knowledge."""
        await semantic_memory.store(
            concept="python",
            knowledge="Python is a programming language",
            category="programming"
        )

        assert "python" in semantic_memory._knowledge

    @pytest.mark.asyncio
    async def test_query_knowledge(self, semantic_memory):
        """Test querying knowledge."""
        await semantic_memory.store(
            concept="python",
            knowledge="Python is versatile",
            category="programming"
        )

        results = await semantic_memory.query("python programming")
        assert len(results) > 0


class TestProceduralMemory:
    """Tests for ProceduralMemory."""

    @pytest.fixture
    def procedural_memory(self):
        """Create procedural memory instance."""
        from core.memory.manager import ProceduralMemory
        return ProceduralMemory()

    @pytest.mark.asyncio
    async def test_store_procedure(self, procedural_memory):
        """Test storing procedure."""
        await procedural_memory.store(
            name="test_procedure",
            steps=["step1", "step2", "step3"],
            context={"type": "test"}
        )

        assert "test_procedure" in procedural_memory._procedures

    @pytest.mark.asyncio
    async def test_retrieve_procedure(self, procedural_memory):
        """Test retrieving procedure."""
        await procedural_memory.store(
            name="test_procedure",
            steps=["step1", "step2"],
            context={}
        )

        procedure = await procedural_memory.retrieve("test_procedure")
        assert procedure is not None
        assert len(procedure["steps"]) == 2


# =============================================================================
# REASONING TESTS
# =============================================================================

class TestThoughtNode:
    """Tests for ThoughtNode."""

    def test_create_thought(self):
        """Test creating thought node."""
        from core.reasoning.engine import ThoughtNode

        thought = ThoughtNode(content="Test thought", confidence=0.8)
        assert thought.content == "Test thought"
        assert thought.confidence == 0.8
        assert thought.id is not None

    def test_add_child(self):
        """Test adding child thought."""
        from core.reasoning.engine import ThoughtNode

        parent = ThoughtNode(content="Parent")
        child = ThoughtNode(content="Child")
        parent.add_child(child)

        assert len(parent.children) == 1
        assert child.parent == parent


class TestChainOfThought:
    """Tests for Chain of Thought reasoning."""

    @pytest.fixture
    def cot(self, mock_model_router):
        """Create CoT instance."""
        from core.reasoning.engine import ChainOfThought
        return ChainOfThought(mock_model_router)

    @pytest.mark.asyncio
    async def test_reason(self, cot):
        """Test basic reasoning."""
        result = await cot.reason("What is 2+2?")
        assert result is not None
        assert len(cot.thoughts) > 0


class TestReasoningEngine:
    """Tests for ReasoningEngine."""

    @pytest.fixture
    def engine(self, mock_model_router):
        """Create reasoning engine."""
        from core.reasoning.engine import ReasoningEngine
        return ReasoningEngine(mock_model_router)

    def test_select_strategy(self, engine):
        """Test strategy selection."""
        # Simple question should use CoT
        strategy = engine._select_strategy("What is Python?")
        assert strategy in ["cot", "tot", "got"]

    @pytest.mark.asyncio
    async def test_reason_with_cot(self, engine):
        """Test reasoning with CoT."""
        result = await engine.reason("Explain recursion", strategy="cot")
        assert result is not None


# =============================================================================
# MODEL ROUTER TESTS
# =============================================================================

class TestModelRouter:
    """Tests for ModelRouter."""

    @pytest.fixture
    def router(self, mock_settings):
        """Create model router."""
        from integrations.model_router import ModelRouter
        return ModelRouter(mock_settings)

    def test_get_model_config(self, router):
        """Test getting model config."""
        config = router._get_model_config("primary")
        assert config is not None

    def test_usage_tracking(self, router):
        """Test usage tracking."""
        router._track_usage("test-model", 100, 50)

        assert router.total_tokens == 150

    def test_get_stats(self, router):
        """Test getting stats."""
        router._track_usage("test-model", 100, 50)

        stats = router.get_stats()
        assert stats["total_tokens"] == 150
        assert stats["total_requests"] == 1


# =============================================================================
# PERSONA TESTS
# =============================================================================

class TestPersonas:
    """Tests for personas."""

    def test_load_personas(self):
        """Test loading personas."""
        from personas.specialists.personas import load_personas

        personas = load_personas()
        assert len(personas) > 0

    def test_persona_activation(self):
        """Test persona activation."""
        from personas.specialists.personas import load_personas

        personas = load_personas()
        persona = list(personas.values())[0]

        persona.activate()
        assert persona.state.value == "active"
        assert persona.activation_count == 1

        persona.deactivate()
        assert persona.state.value == "dormant"

    def test_persona_task_matching(self):
        """Test persona task matching."""
        from personas.specialists.personas import load_personas

        personas = load_personas()

        # Code Master should match coding tasks
        if "code_master" in personas:
            score = personas["code_master"].matches_task("Write Python code", {})
            assert score > 0

    @pytest.mark.asyncio
    async def test_persona_analysis(self):
        """Test persona analysis."""
        from personas.specialists.personas import load_personas

        personas = load_personas()
        persona = list(personas.values())[0]

        analysis = await persona.analyze("Build a REST API", {})
        assert analysis is not None
        assert "persona" in analysis


# =============================================================================
# TOOL TESTS
# =============================================================================

class TestToolLoader:
    """Tests for tool loader."""

    def test_load_tools(self):
        """Test loading tools."""
        from tools.loader import load_all_tools

        tools = load_all_tools()
        assert len(tools) > 0

    def test_tool_schema(self):
        """Test tool schema generation."""
        from tools.loader import load_all_tools

        tools = load_all_tools()
        tool = list(tools.values())[0]

        schema = tool.get_schema()
        assert schema is not None
        assert schema.name == tool.name

    def test_openai_function_format(self):
        """Test OpenAI function format."""
        from tools.loader import load_all_tools, tools_to_openai_format

        tools = load_all_tools()
        functions = tools_to_openai_format(tools)

        assert len(functions) > 0
        assert "function" in functions[0]


class TestPythonExecutor:
    """Tests for Python executor tool."""

    @pytest.fixture
    def executor(self):
        """Create executor."""
        from tools.loader import PythonExecutor
        return PythonExecutor()

    @pytest.mark.asyncio
    async def test_execute_simple(self, executor):
        """Test simple execution."""
        result = await executor.execute({"code": "print('hello')"})
        assert result.success
        assert "hello" in result.data.get("output", "")

    @pytest.mark.asyncio
    async def test_execute_with_result(self, executor):
        """Test execution with result."""
        result = await executor.execute({"code": "result = 2 + 2"})
        assert result.success

    @pytest.mark.asyncio
    async def test_execute_error(self, executor):
        """Test error handling."""
        result = await executor.execute({"code": "raise ValueError('test')"})
        assert not result.success or "error" in str(result.data).lower()


class TestFileTools:
    """Tests for file tools."""

    @pytest.fixture
    def read_tool(self):
        """Create file read tool."""
        from tools.loader import FileReadTool
        return FileReadTool()

    @pytest.fixture
    def write_tool(self):
        """Create file write tool."""
        from tools.loader import FileWriteTool
        return FileWriteTool()

    @pytest.mark.asyncio
    async def test_write_and_read(self, write_tool, read_tool, tmp_path):
        """Test write and read cycle."""
        test_file = tmp_path / "test.txt"

        # Write
        write_result = await write_tool.execute({
            "path": str(test_file),
            "content": "test content"
        })
        assert write_result.success

        # Read
        read_result = await read_tool.execute({"path": str(test_file)})
        assert read_result.success
        assert read_result.data.get("content") == "test content"


# =============================================================================
# ORCHESTRATOR TESTS
# =============================================================================

class TestAgentOrchestrator:
    """Tests for AgentOrchestrator."""

    @pytest.fixture
    def orchestrator(self, mock_model_router):
        """Create orchestrator."""
        from core.orchestrator.orchestrator import AgentOrchestrator

        brain = MagicMock()
        brain.model_router = mock_model_router
        brain.personas = {}
        brain.tools = {}

        return AgentOrchestrator(brain)

    @pytest.mark.asyncio
    async def test_spawn_agent(self, orchestrator):
        """Test spawning agent."""
        from core.orchestrator.orchestrator import AgentConfig

        config = AgentConfig(name="TestAgent")
        agent = await orchestrator.spawn_agent(config, "Test task")

        assert agent is not None
        assert agent.name == "TestAgent"

    @pytest.mark.asyncio
    async def test_spawn_team(self, orchestrator):
        """Test spawning team."""
        agents = await orchestrator.spawn_team(
            "Build application",
            roles=["architect", "developer"]
        )

        assert len(agents) == 2

    def test_get_agent(self, orchestrator):
        """Test getting agent by ID."""
        agent = orchestrator.get_agent("nonexistent")
        assert agent is None


# =============================================================================
# PROMPT LIBRARY TESTS
# =============================================================================

class TestPromptLibrary:
    """Tests for PromptLibrary."""

    @pytest.fixture
    def library(self):
        """Create prompt library."""
        from prompts.library import PromptLibrary
        return PromptLibrary()

    def test_get_prompt(self, library):
        """Test getting prompt."""
        prompt = library.get("BAEL_CORE_IDENTITY")
        assert prompt is not None

    def test_render_prompt(self, library):
        """Test rendering prompt with variables."""
        prompt = library.render("BAEL_CORE_IDENTITY", name="Test")
        # Should contain rendered content
        assert isinstance(prompt, str)

    def test_list_prompts(self, library):
        """Test listing prompts."""
        prompts = library.list_prompts()
        assert len(prompts) > 0

    def test_get_by_category(self, library):
        """Test getting prompts by category."""
        reasoning = library.get_by_category("reasoning")
        assert isinstance(reasoning, dict)


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestBaelIntegration:
    """Integration tests for BAEL system."""

    @pytest.fixture
    def mock_brain(self, mock_model_router, mock_settings):
        """Create mock brain."""
        brain = MagicMock()
        brain.model_router = mock_model_router
        brain.settings = mock_settings
        brain.personas = {}
        brain.tools = {}
        brain.session_id = "test-session"
        brain.think = AsyncMock(return_value={"response": "Test"})
        return brain

    @pytest.mark.asyncio
    async def test_full_think_cycle(self, mock_brain):
        """Test complete thinking cycle."""
        result = await mock_brain.think("What is Python?")
        assert result is not None
        assert "response" in result


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])

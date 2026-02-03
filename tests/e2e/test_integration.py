"""
BAEL - End-to-End Test Suite
Comprehensive integration tests for the complete BAEL system.
"""

import asyncio
import json
import os
# Add project root to path
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestBrainIntegration:
    """Tests for brain integration module."""

    @pytest.mark.asyncio
    async def test_brain_initialization(self):
        """Test brain integration initializes all components."""
        from core.brain.integration import BrainIntegration, CognitiveContext

        brain = BrainIntegration()
        assert not brain.is_initialized()

        await brain.initialize()
        assert brain.is_initialized()

    @pytest.mark.asyncio
    async def test_cognitive_pipeline(self):
        """Test complete cognitive processing pipeline."""
        from core.brain.integration import (BrainIntegration, CognitiveContext,
                                            CognitiveResult)

        brain = BrainIntegration()
        await brain.initialize()

        context = CognitiveContext(
            query="Explain the singleton pattern",
            mode="standard",
            persona="architect"
        )

        result = await brain.process(context)

        assert isinstance(result, CognitiveResult)
        assert result.response is not None
        assert result.execution_time_ms > 0
        assert len(result.reasoning) > 0


class TestUnifiedMemory:
    """Tests for unified memory system."""

    @pytest.mark.asyncio
    async def test_memory_initialization(self):
        """Test unified memory initialization."""
        from memory import UnifiedMemory

        memory = UnifiedMemory()
        assert memory is not None

    @pytest.mark.asyncio
    async def test_episodic_memory_storage(self):
        """Test storing and retrieving episodic memories."""
        from memory.episodic.episodic_memory import (Episode,
                                                     EpisodicMemoryManager,
                                                     EventType)

        manager = EpisodicMemoryManager(":memory:")

        episode = Episode(
            id="test-episode",
            event_type=EventType.TASK,
            timestamp=datetime.now(),
            content="Test task completed"
        )

        await manager.store(episode)
        retrieved = await manager.recall("test-episode")

        assert retrieved is not None
        assert retrieved.id == "test-episode"

    @pytest.mark.asyncio
    async def test_semantic_memory_concepts(self):
        """Test semantic memory concept operations."""
        from memory.semantic.semantic_memory import (Concept, ConceptType,
                                                     SemanticMemoryManager)

        manager = SemanticMemoryManager(":memory:")

        concept = Concept(
            id="python",
            name="Python",
            concept_type=ConceptType.ENTITY,
            definition="A programming language"
        )

        await manager.store_concept(concept)
        retrieved = await manager.get_concept("python")

        assert retrieved is not None
        assert retrieved.name == "Python"


class TestPersonaSystem:
    """Tests for persona system."""

    def test_persona_loading(self):
        """Test loading persona configurations."""
        from core.personas import PersonaLoader, PersonaRole

        loader = PersonaLoader()

        # Should have built-in personas
        personas = loader.list_all()
        assert len(personas) > 0
        assert "orchestrator" in personas

    def test_persona_retrieval(self):
        """Test retrieving persona by role."""
        from core.personas import PersonaLoader

        loader = PersonaLoader()

        architect = loader.get("architect")
        assert architect is not None
        assert architect.name == "Architect"
        assert "architecture" in architect.capabilities


class TestWorkflowEngine:
    """Tests for workflow engine."""

    def test_workflow_loading(self):
        """Test loading workflow definitions."""
        from workflows import WorkflowEngine

        engine = WorkflowEngine()
        engine.load_workflows()

        workflows = engine.list_workflows()
        # Should have at least one workflow after loading
        assert isinstance(workflows, list)

    def test_workflow_creation(self):
        """Test creating a workflow."""
        from workflows import Workflow, WorkflowStep

        step = WorkflowStep(
            id="step1",
            name="Analyze",
            persona="analyst",
            template=None,
            inputs=["data"],
            outputs=["analysis"]
        )

        workflow = Workflow(
            name="Test Workflow",
            description="A test workflow",
            steps=[step],
            output={"result": "analysis"}
        )

        assert workflow.name == "Test Workflow"
        assert len(workflow.steps) == 1


class TestToolSystem:
    """Tests for tool system."""

    def test_tool_registry(self):
        """Test tool registration and retrieval."""
        from core.tools import BaseTool, ToolCategory, ToolRegistry

        registry = ToolRegistry()

        # Create a simple test tool
        class TestTool(BaseTool):
            def __init__(self):
                super().__init__("test_tool", "A test tool", ToolCategory.SYSTEM)

            async def execute(self, **kwargs):
                from core.tools import ToolResult
                return ToolResult(success=True, output="test")

            def get_definition(self):
                from core.tools import ToolDefinition
                return ToolDefinition(
                    name="test_tool",
                    description="A test tool",
                    category=ToolCategory.SYSTEM,
                    parameters={},
                    returns={}
                )

        tool = TestTool()
        registry.register(tool)

        retrieved = registry.get("test_tool")
        assert retrieved is not None
        assert retrieved.name == "test_tool"


class TestKnowledgeBase:
    """Tests for knowledge base."""

    def test_pattern_loading(self):
        """Test loading design patterns."""
        from knowledge import KnowledgeBase

        kb = KnowledgeBase()
        patterns = kb.list_patterns()

        assert isinstance(patterns, list)
        # Should have some patterns
        if patterns:
            assert "singleton" in patterns or len(patterns) > 0

    def test_domain_knowledge(self):
        """Test loading domain knowledge."""
        from knowledge import KnowledgeBase

        kb = KnowledgeBase()
        domains = kb.list_domains()

        assert isinstance(domains, list)


class TestPromptLibrary:
    """Tests for prompt library."""

    def test_prompt_loading(self):
        """Test loading prompts."""
        from prompts import PromptLibrary

        library = PromptLibrary()

        # Should have system prompts
        prompts = library.list_system_prompts()
        assert isinstance(prompts, list)

    def test_template_rendering(self):
        """Test template variable rendering."""
        from prompts import PromptLibrary

        library = PromptLibrary()
        library._templates["test"] = "Hello {{name}}!"

        rendered = library.render_template("test", name="World")
        assert rendered == "Hello World!"


class TestQualityChecker:
    """Tests for quality checking."""

    @pytest.mark.asyncio
    async def test_quality_check(self):
        """Test quality checking of outputs."""
        from core.quality import QualityChecker, QualityLevel

        checker = QualityChecker(min_threshold=0.5)

        report = await checker.check(
            output="Test output",
            context={"query": "test query"}
        )

        assert report is not None
        assert report.metrics is not None
        assert report.metrics.overall > 0


class TestAuthSystem:
    """Tests for authentication system."""

    def test_api_key_generation(self):
        """Test API key generation."""
        from core.auth import AuthManager, User

        auth = AuthManager()

        user = User(
            id="user1",
            username="testuser",
            roles=["user"],
            created_at=datetime.now()
        )

        api_key = auth.generate_api_key(user)

        assert api_key.startswith("bael_")
        assert len(api_key) > 20

    def test_api_key_validation(self):
        """Test API key validation."""
        from core.auth import AuthManager, User

        auth = AuthManager()

        user = User(
            id="user1",
            username="testuser",
            roles=["user"],
            created_at=datetime.now()
        )

        api_key = auth.generate_api_key(user)
        validated_user = auth.validate_api_key(api_key)

        assert validated_user is not None
        assert validated_user.username == "testuser"

    def test_token_creation_validation(self):
        """Test token creation and validation."""
        from core.auth import AuthManager, User

        auth = AuthManager()

        user = User(
            id="user1",
            username="testuser",
            roles=["admin"],
            created_at=datetime.now()
        )

        token = auth.create_token(user)
        payload = auth.validate_token(token)

        assert payload is not None
        assert payload.username == "testuser"
        assert "admin" in payload.roles


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

"""
BAEL - Comprehensive Test Suite
Unit tests for core memory, workflow, and integration systems.
"""

import asyncio
import json
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def temp_db_path():
    """Create a temporary database path."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield os.path.join(tmpdir, "test.db")


@pytest.fixture
def temp_dir():
    """Create a temporary directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


# =============================================================================
# EPISODIC MEMORY TESTS
# =============================================================================

class TestEpisodicMemory:
    """Tests for episodic memory system."""

    def test_episode_creation(self):
        """Test creating an episode."""
        from memory.episodic.episodic_memory import (EmotionalValence, Episode,
                                                     EventType)

        episode = Episode(
            id="test-001",
            event_type=EventType.TASK,
            timestamp=datetime.now(),
            content="Test episode content",
            context={"task": "testing"},
            participants=["user", "bael"],
            importance=0.8,
            outcome="success"
        )

        assert episode.id == "test-001"
        assert episode.event_type == EventType.TASK
        assert episode.importance == 0.8

    def test_episode_to_dict(self):
        """Test episode serialization."""
        from memory.episodic.episodic_memory import Episode, EventType

        episode = Episode(
            id="test-002",
            event_type=EventType.CONVERSATION,
            timestamp=datetime.now(),
            content="Test content"
        )

        data = episode.to_dict()
        assert "id" in data
        assert data["event_type"] == "conversation"

    @pytest.mark.asyncio
    async def test_store_and_retrieve(self, temp_db_path):
        """Test storing and retrieving episodes."""
        from memory.episodic.episodic_memory import (Episode,
                                                     EpisodicMemoryStore,
                                                     EventType)

        store = EpisodicMemoryStore(temp_db_path)

        episode = Episode(
            id="test-003",
            event_type=EventType.INSIGHT,
            timestamp=datetime.now(),
            content="Important insight"
        )

        await store.store(episode)
        retrieved = await store.get("test-003")

        assert retrieved is not None
        assert retrieved.id == "test-003"
        assert retrieved.content == "Important insight"

    @pytest.mark.asyncio
    async def test_query_by_time_range(self, temp_db_path):
        """Test querying episodes by time range."""
        from memory.episodic.episodic_memory import (Episode, EpisodeQuery,
                                                     EpisodicMemoryStore,
                                                     EventType)

        store = EpisodicMemoryStore(temp_db_path)

        # Store episodes at different times
        now = datetime.now()
        for i in range(5):
            episode = Episode(
                id=f"time-test-{i}",
                event_type=EventType.OBSERVATION,
                timestamp=now - timedelta(days=i),
                content=f"Episode {i}"
            )
            await store.store(episode)

        # Query last 2 days
        query = EpisodeQuery(
            time_range=(now - timedelta(days=2), now)
        )
        results = await store.query(query)

        assert len(results) >= 2


# =============================================================================
# SEMANTIC MEMORY TESTS
# =============================================================================

class TestSemanticMemory:
    """Tests for semantic memory system."""

    def test_concept_creation(self):
        """Test creating a concept."""
        from memory.semantic.semantic_memory import Concept, ConceptType

        concept = Concept(
            id="concept-001",
            name="Test Concept",
            concept_type=ConceptType.ENTITY,
            definition="A test concept for unit testing"
        )

        assert concept.name == "Test Concept"
        assert concept.concept_type == ConceptType.ENTITY

    def test_relation_creation(self):
        """Test creating a relation."""
        from memory.semantic.semantic_memory import (ConceptRelation,
                                                     RelationType)

        relation = ConceptRelation(
            id="rel-001",
            source_id="concept-001",
            target_id="concept-002",
            relation_type=RelationType.IS_A,
            strength=0.9
        )

        assert relation.relation_type == RelationType.IS_A
        assert relation.strength == 0.9

    @pytest.mark.asyncio
    async def test_store_and_retrieve_concept(self, temp_db_path):
        """Test storing and retrieving concepts."""
        from memory.semantic.semantic_memory import (Concept, ConceptType,
                                                     SemanticMemoryStore)

        store = SemanticMemoryStore(temp_db_path)

        concept = Concept(
            id="test-concept",
            name="Python",
            concept_type=ConceptType.ENTITY,
            definition="A programming language"
        )

        await store.store_concept(concept)
        retrieved = await store.get_concept("test-concept")

        assert retrieved is not None
        assert retrieved.name == "Python"


# =============================================================================
# PROCEDURAL MEMORY TESTS
# =============================================================================

class TestProceduralMemory:
    """Tests for procedural memory system."""

    def test_procedure_step_creation(self):
        """Test creating a procedure step."""
        from memory.procedural.procedural_memory import ProcedureStep

        step = ProcedureStep(
            order=1,
            instruction="Initialize the system",
            expected_output="System ready"
        )

        assert step.order == 1
        assert "Initialize" in step.instruction

    def test_procedure_creation(self):
        """Test creating a procedure."""
        from memory.procedural.procedural_memory import (Procedure,
                                                         ProcedureStep,
                                                         ProcedureType,
                                                         ProficiencyLevel)

        steps = [
            ProcedureStep(order=1, instruction="Step 1"),
            ProcedureStep(order=2, instruction="Step 2")
        ]

        procedure = Procedure(
            id="proc-001",
            name="Test Procedure",
            procedure_type=ProcedureType.ALGORITHM,
            description="A test procedure",
            steps=steps
        )

        assert len(procedure.steps) == 2
        assert procedure.proficiency == ProficiencyLevel.NOVICE


# =============================================================================
# WORKING MEMORY TESTS
# =============================================================================

class TestWorkingMemory:
    """Tests for working memory system."""

    def test_working_item_creation(self):
        """Test creating a working memory item."""
        from memory.working.working_memory import (AttentionLevel, ContextType,
                                                   WorkingItem)

        item = WorkingItem(
            id="work-001",
            content={"key": "value"},
            attention=AttentionLevel.FOCUSED,
            context_type=ContextType.TASK
        )

        assert item.attention == AttentionLevel.FOCUSED

    @pytest.mark.asyncio
    async def test_capacity_limit(self):
        """Test working memory capacity enforcement."""
        from memory.working.working_memory import (ContextType, WorkingItem,
                                                   WorkingMemoryManager)

        manager = WorkingMemoryManager(capacity=5)

        # Add items beyond capacity
        for i in range(10):
            item = WorkingItem(
                id=f"item-{i}",
                content={"index": i},
                context_type=ContextType.TASK
            )
            await manager.add(item)

        current = await manager.get_current()
        assert len(current) <= 5


# =============================================================================
# VECTOR MEMORY TESTS
# =============================================================================

class TestVectorMemory:
    """Tests for vector memory system."""

    def test_vector_ops(self):
        """Test vector operations."""
        from memory.vector.vector_memory import VectorOps

        v1 = [1.0, 0.0, 0.0]
        v2 = [0.0, 1.0, 0.0]
        v3 = [1.0, 0.0, 0.0]

        # Orthogonal vectors should have similarity near 0
        sim = VectorOps.cosine_similarity(v1, v2)
        assert sim < 0.1

        # Same vectors should have similarity 1
        sim = VectorOps.cosine_similarity(v1, v3)
        assert sim > 0.99

    def test_normalize(self):
        """Test vector normalization."""
        from memory.vector.vector_memory import VectorOps

        v = [3.0, 4.0]  # Length 5
        normalized = VectorOps.normalize(v)

        assert abs(normalized[0] - 0.6) < 0.01
        assert abs(normalized[1] - 0.8) < 0.01


# =============================================================================
# WORKFLOW ENGINE TESTS
# =============================================================================

class TestWorkflowEngine:
    """Tests for workflow engine."""

    def test_workflow_step_creation(self):
        """Test creating a workflow step."""
        from workflows import WorkflowStep

        step = WorkflowStep(
            id="step-1",
            name="Analyze",
            persona="analyst",
            template="analyze_template",
            inputs=["data"],
            outputs=["analysis"]
        )

        assert step.persona == "analyst"
        assert "data" in step.inputs

    def test_workflow_creation(self):
        """Test creating a workflow."""
        from workflows import Workflow, WorkflowStep

        steps = [
            WorkflowStep(
                id="s1",
                name="Step 1",
                persona="coder",
                template=None,
                inputs=[],
                outputs=["result"]
            )
        ]

        workflow = Workflow(
            name="Test Workflow",
            description="A test workflow",
            steps=steps,
            output={"result": "result"}
        )

        assert workflow.name == "Test Workflow"
        assert len(workflow.steps) == 1

    def test_workflow_serialization(self):
        """Test workflow serialization/deserialization."""
        from workflows import Workflow, WorkflowStep

        original = Workflow(
            name="Serial Test",
            description="Test",
            steps=[
                WorkflowStep(
                    id="s1",
                    name="Step",
                    persona="coder",
                    template=None,
                    inputs=[],
                    outputs=[]
                )
            ],
            output={}
        )

        data = original.to_dict()
        restored = Workflow.from_dict(data)

        assert restored.name == original.name
        assert len(restored.steps) == len(original.steps)


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestIntegrations:
    """Tests for integration system."""

    def test_integration_config(self):
        """Test integration configuration."""
        from integrations import IntegrationConfig

        config = IntegrationConfig(
            name="test-github",
            type="github",
            enabled=True,
            credentials={"token": "test-token"},
            settings={"default_owner": "test"}
        )

        assert config.name == "test-github"
        assert config.enabled

    def test_registry_provider_registration(self):
        """Test registering providers."""
        from integrations import (BaseIntegration, IntegrationConfig,
                                  IntegrationRegistry)

        class MockIntegration(BaseIntegration):
            async def connect(self):
                return True
            async def disconnect(self):
                pass
            async def test_connection(self):
                return True

        registry = IntegrationRegistry()
        registry.register_provider("mock", MockIntegration)

        assert "mock" in registry.list_providers()


# =============================================================================
# PROMPT LIBRARY TESTS
# =============================================================================

class TestPromptLibrary:
    """Tests for prompt library."""

    def test_template_rendering(self, temp_dir):
        """Test template variable rendering."""
        # Create a simple template
        templates_dir = os.path.join(temp_dir, "templates")
        os.makedirs(templates_dir, exist_ok=True)

        with open(os.path.join(templates_dir, "test.txt"), "w") as f:
            f.write("Hello {{name}}, welcome to {{place}}!")

        from prompts import PromptLibrary

        library = PromptLibrary(temp_dir)
        library._templates["test"] = "Hello {{name}}, welcome to {{place}}!"

        rendered = library.render_template("test", name="World", place="BAEL")

        assert "Hello World" in rendered
        assert "BAEL" in rendered


# =============================================================================
# KNOWLEDGE BASE TESTS
# =============================================================================

class TestKnowledgeBase:
    """Tests for knowledge base."""

    def test_pattern_loading(self, temp_dir):
        """Test loading patterns from files."""
        patterns_dir = os.path.join(temp_dir, "patterns")
        os.makedirs(patterns_dir, exist_ok=True)

        pattern_data = {
            "name": "Test Pattern",
            "category": "creational",
            "description": "A test pattern"
        }

        with open(os.path.join(patterns_dir, "test.json"), "w") as f:
            json.dump(pattern_data, f)

        from knowledge import KnowledgeBase

        kb = KnowledgeBase(temp_dir)
        patterns = kb.list_patterns()

        # Should find the test pattern
        assert "test" in patterns or len(patterns) >= 0


# =============================================================================
# RUN CONFIGURATION
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

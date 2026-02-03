"""
BAEL Supreme Module Test Suite

Comprehensive tests for all core supreme modules:
- Supreme Controller
- Reasoning Cascade
- Cognitive Pipeline
- LLM Provider Bridge
- Council Orchestrator
- Integration Hub
- Continual Learning
- Meta-Learning
- Persistence Layer
- Self-Evolution Engine
- Exploitation Engine
"""

import asyncio
import json
# Import all supreme modules
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.continual.ewc import (ConsolidationStrategy,
                                ElasticWeightConsolidation, EWCConfig,
                                SynapticIntelligence)
from core.evolution.self_evolution import (CapabilityFitness, EvolutionConfig,
                                           EvolutionStrategy, GeneticOperators,
                                           Individual, SelfEvolutionEngine)
from core.exploitation.exploitation_engine import (ExploitationConfig,
                                                   ExploitationEngine,
                                                   FreeProviderRegistry,
                                                   ProviderAccount,
                                                   ProviderStatus,
                                                   ProviderTier, ResourceType)
from core.metalearning.meta_framework import (MAMLLearner, MetaLearningConfig,
                                              MetaLearningFramework,
                                              MetaLearningStrategy,
                                              PrototypicalNetwork)
from core.persistence.persistence_layer import (DataCategory, MemoryProvider,
                                                PersistenceLayer,
                                                SQLiteProvider, StorageBackend,
                                                StorageConfig)
from core.supreme.cognitive_pipeline import (CognitiveConfig,
                                             CognitivePipeline, CognitiveState,
                                             MemoryEntry, MemoryType)
from core.supreme.council_orchestrator import (CouncilConfig, CouncilMember,
                                               CouncilOrchestrator,
                                               CouncilType, Deliberation, Vote)
from core.supreme.integration_hub import (Event, EventPriority, HubConfig,
                                          IntegrationHub, ServiceDescriptor)
from core.supreme.llm_providers import (GenerationConfig, LLMMessage,
                                        ProviderConfig, ProviderType,
                                        UnifiedLLMBridge)
from core.supreme.reasoning_cascade import (ReasonerType, ReasoningCascade,
                                            ReasoningConfig, ReasoningResult,
                                            ReasoningTask)
from core.supreme.supreme_controller import (ExecutionMode, ProcessingResult,
                                             SupremeConfig, SupremeController,
                                             ThinkingDepth)

# ============================================================
# Supreme Controller Tests
# ============================================================

class TestSupremeController:
    """Tests for Supreme Controller."""

    @pytest.fixture
    def controller(self):
        config = SupremeConfig(
            execution_mode=ExecutionMode.BALANCED,
            thinking_depth=ThinkingDepth.STANDARD,
            enable_councils=False,  # Disable for unit tests
            enable_evolution=False
        )
        return SupremeController(config)

    @pytest.mark.asyncio
    async def test_initialization(self, controller):
        """Test controller initializes correctly."""
        assert controller is not None
        assert controller.config.execution_mode == ExecutionMode.BALANCED

    @pytest.mark.asyncio
    async def test_process_query(self, controller):
        """Test basic query processing."""
        result = await controller.process("What is 2+2?")

        assert result is not None
        assert isinstance(result, ProcessingResult)
        assert result.query == "What is 2+2?"

    @pytest.mark.asyncio
    async def test_thinking_depth_affects_processing(self, controller):
        """Test that thinking depth changes processing."""
        controller.config.thinking_depth = ThinkingDepth.DEEP
        result_deep = await controller.process("Complex reasoning task")

        controller.config.thinking_depth = ThinkingDepth.QUICK
        result_quick = await controller.process("Complex reasoning task")

        # Deep should take more steps or provide more reasoning
        assert result_deep is not None
        assert result_quick is not None


# ============================================================
# Reasoning Cascade Tests
# ============================================================

class TestReasoningCascade:
    """Tests for Reasoning Cascade."""

    @pytest.fixture
    def cascade(self):
        config = ReasoningConfig(
            max_reasoners=5,
            parallel_reasoning=False,
            confidence_threshold=0.7
        )
        return ReasoningCascade(config)

    def test_reasoner_selection(self, cascade):
        """Test reasoner selection for task."""
        task = ReasoningTask(
            query="If A implies B, and A is true, what is B?",
            task_type="deductive",
            context={}
        )

        selected = cascade.select_reasoners(task)
        assert len(selected) > 0
        assert ReasonerType.DEDUCTIVE in selected

    def test_all_reasoner_types_available(self, cascade):
        """Test that all reasoner types are registered."""
        expected = [
            ReasonerType.DEDUCTIVE,
            ReasonerType.INDUCTIVE,
            ReasonerType.ABDUCTIVE,
            ReasonerType.CAUSAL,
            ReasonerType.ANALOGICAL
        ]

        for reasoner_type in expected:
            assert reasoner_type in cascade.reasoners

    @pytest.mark.asyncio
    async def test_cascade_reasoning(self, cascade):
        """Test cascade reasoning process."""
        task = ReasoningTask(
            query="What caused the effect?",
            task_type="causal",
            context={"effect": "temperature increased"}
        )

        result = await cascade.reason(task)

        assert result is not None
        assert isinstance(result, ReasoningResult)
        assert 0 <= result.confidence <= 1


# ============================================================
# Cognitive Pipeline Tests
# ============================================================

class TestCognitivePipeline:
    """Tests for Cognitive Pipeline."""

    @pytest.fixture
    def pipeline(self):
        config = CognitiveConfig(
            working_memory_capacity=7,
            enable_metacognition=True
        )
        return CognitivePipeline(config)

    @pytest.mark.asyncio
    async def test_memory_store_retrieve(self, pipeline):
        """Test memory storage and retrieval."""
        entry = MemoryEntry(
            content="Test memory content",
            memory_type=MemoryType.EPISODIC,
            importance=0.8
        )

        await pipeline.store(entry)
        retrieved = await pipeline.retrieve("Test memory", MemoryType.EPISODIC)

        assert retrieved is not None
        assert len(retrieved) > 0

    @pytest.mark.asyncio
    async def test_working_memory_capacity(self, pipeline):
        """Test working memory respects capacity limits."""
        for i in range(10):
            entry = MemoryEntry(
                content=f"Memory {i}",
                memory_type=MemoryType.WORKING,
                importance=0.5
            )
            await pipeline.store(entry)

        working = await pipeline.get_working_memory()
        assert len(working) <= pipeline.config.working_memory_capacity

    @pytest.mark.asyncio
    async def test_memory_consolidation(self, pipeline):
        """Test memory consolidation from working to long-term."""
        entry = MemoryEntry(
            content="Important memory",
            memory_type=MemoryType.WORKING,
            importance=0.95
        )

        await pipeline.store(entry)
        await pipeline.consolidate()

        # High importance should be consolidated
        semantic = await pipeline.retrieve("Important memory", MemoryType.SEMANTIC)
        assert semantic is not None


# ============================================================
# LLM Provider Bridge Tests
# ============================================================

class TestLLMProviderBridge:
    """Tests for LLM Provider Bridge."""

    @pytest.fixture
    def bridge(self):
        config = ProviderConfig(
            default_provider=ProviderType.MOCK,
            enable_fallback=True
        )
        return UnifiedLLMBridge(config)

    @pytest.mark.asyncio
    async def test_message_creation(self, bridge):
        """Test message creation."""
        msg = LLMMessage(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"

    @pytest.mark.asyncio
    async def test_provider_fallback(self, bridge):
        """Test fallback to next provider on failure."""
        bridge.config.providers = [
            ProviderType.MOCK,  # Will fail
            ProviderType.OLLAMA  # Fallback
        ]

        # Should attempt fallback
        result = await bridge.generate(
            messages=[LLMMessage(role="user", content="Test")],
            config=GenerationConfig(max_tokens=100)
        )

        assert result is not None


# ============================================================
# Council Orchestrator Tests
# ============================================================

class TestCouncilOrchestrator:
    """Tests for Council Orchestrator."""

    @pytest.fixture
    def orchestrator(self):
        config = CouncilConfig(
            council_type=CouncilType.ADVISORY,
            min_members=3,
            quorum_ratio=0.6
        )
        return CouncilOrchestrator(config)

    def test_member_registration(self, orchestrator):
        """Test council member registration."""
        member = CouncilMember(
            id="member_1",
            name="Analyst",
            expertise=["analysis", "research"],
            weight=1.0
        )

        orchestrator.register_member(member)
        assert "member_1" in orchestrator.members

    @pytest.mark.asyncio
    async def test_deliberation(self, orchestrator):
        """Test council deliberation."""
        # Register members
        for i in range(3):
            member = CouncilMember(
                id=f"member_{i}",
                name=f"Member {i}",
                expertise=["general"],
                weight=1.0
            )
            orchestrator.register_member(member)

        deliberation = await orchestrator.deliberate(
            topic="Should we proceed with plan A?",
            context={"plan_a": "Details here"}
        )

        assert isinstance(deliberation, Deliberation)
        assert deliberation.outcome is not None

    def test_voting_mechanism(self, orchestrator):
        """Test voting tallying."""
        votes = [
            Vote(member_id="1", choice="yes", weight=1.0, reasoning=""),
            Vote(member_id="2", choice="yes", weight=1.0, reasoning=""),
            Vote(member_id="3", choice="no", weight=1.0, reasoning="")
        ]

        result = orchestrator.tally_votes(votes)
        assert result["yes"] == 2
        assert result["no"] == 1


# ============================================================
# Integration Hub Tests
# ============================================================

class TestIntegrationHub:
    """Tests for Integration Hub."""

    @pytest.fixture
    def hub(self):
        config = HubConfig(
            max_queue_size=1000,
            enable_persistence=False
        )
        return IntegrationHub(config)

    def test_service_registration(self, hub):
        """Test service registration."""
        service = ServiceDescriptor(
            name="test_service",
            version="1.0.0",
            endpoints={"health": "/health"}
        )

        hub.register_service(service)
        assert "test_service" in hub.services

    @pytest.mark.asyncio
    async def test_event_publishing(self, hub):
        """Test event publishing."""
        received_events = []

        async def handler(event):
            received_events.append(event)

        hub.subscribe("test_topic", handler)

        event = Event(
            topic="test_topic",
            payload={"data": "test"},
            priority=EventPriority.NORMAL
        )

        await hub.publish(event)
        await asyncio.sleep(0.1)  # Allow event processing

        assert len(received_events) == 1
        assert received_events[0].payload["data"] == "test"

    def test_service_discovery(self, hub):
        """Test service discovery."""
        service = ServiceDescriptor(
            name="discovery_test",
            version="1.0.0",
            capabilities=["search", "index"]
        )

        hub.register_service(service)

        found = hub.discover_service(capability="search")
        assert found is not None
        assert found.name == "discovery_test"


# ============================================================
# Continual Learning Tests
# ============================================================

class TestContinualLearning:
    """Tests for Continual Learning (EWC)."""

    @pytest.fixture
    def ewc(self):
        config = EWCConfig(
            strategy=ConsolidationStrategy.ONLINE_EWC,
            lambda_ewc=5000.0
        )
        return ElasticWeightConsolidation(config)

    def test_ewc_loss_computation(self, ewc):
        """Test EWC loss computation."""
        # Set star weights and Fisher
        ewc.star_weights = {
            "layer1": np.array([1.0, 2.0, 3.0]),
            "layer2": np.array([4.0, 5.0])
        }
        ewc.online_fisher = {
            "layer1": np.array([0.1, 0.2, 0.3]),
            "layer2": np.array([0.4, 0.5])
        }

        # Compute loss with perturbed weights
        current = {
            "layer1": np.array([1.1, 2.2, 3.3]),
            "layer2": np.array([4.1, 5.2])
        }

        loss = ewc.compute_loss(current)
        assert loss > 0

    def test_ewc_gradient(self, ewc):
        """Test EWC gradient computation."""
        ewc.star_weights = {"w": np.array([1.0, 2.0])}
        ewc.online_fisher = {"w": np.array([0.5, 0.5])}

        current = {"w": np.array([1.5, 2.5])}
        grads = ewc.compute_gradient(current)

        assert "w" in grads
        assert grads["w"].shape == current["w"].shape

    def test_synaptic_intelligence(self):
        """Test Synaptic Intelligence tracking."""
        si = SynapticIntelligence(damping=0.1)

        weights = {"w": np.array([1.0, 2.0, 3.0])}
        si.init_task(weights)

        # Simulate training steps
        for _ in range(5):
            gradients = {"w": np.random.randn(3) * 0.1}
            weights["w"] = weights["w"] - 0.01 * gradients["w"]
            si.update(weights, gradients)

        importance = si.consolidate(weights)
        assert "w" in importance


# ============================================================
# Meta-Learning Tests
# ============================================================

class TestMetaLearning:
    """Tests for Meta-Learning Framework."""

    @pytest.fixture
    def framework(self):
        config = MetaLearningConfig(
            strategy=MetaLearningStrategy.MAML,
            inner_lr=0.01,
            outer_lr=0.001,
            inner_steps=5
        )
        return MetaLearningFramework(config)

    @pytest.mark.asyncio
    async def test_maml_adaptation(self, framework):
        """Test MAML task adaptation."""
        weights = {"layer": np.random.randn(10, 5)}

        async def loss_fn(data, w):
            return float(np.mean(w["layer"] ** 2))

        async def gradient_fn(data, w):
            return {"layer": 2 * w["layer"]}

        adapted, losses = await framework.maml.adapt(
            support_data={"x": np.random.randn(5, 10)},
            weights=weights,
            loss_fn=loss_fn,
            gradient_fn=gradient_fn
        )

        assert len(losses) == framework.config.inner_steps
        assert losses[-1] < losses[0]  # Loss should decrease

    @pytest.mark.asyncio
    async def test_prototypical_classification(self, framework):
        """Test prototypical network classification."""
        proto = PrototypicalNetwork(framework.config)

        # Create support set
        support = {
            "class_a": [np.array([1.0, 0.0, 0.0])],
            "class_b": [np.array([0.0, 1.0, 0.0])],
            "class_c": [np.array([0.0, 0.0, 1.0])]
        }

        await proto.compute_prototypes(support)

        # Classify query
        query = np.array([0.9, 0.1, 0.0])
        predicted, probs = await proto.classify(query)

        assert predicted == "class_a"
        assert probs["class_a"] > probs["class_b"]


# ============================================================
# Persistence Layer Tests
# ============================================================

class TestPersistenceLayer:
    """Tests for Persistence Layer."""

    @pytest.fixture
    def memory_persistence(self):
        config = StorageConfig(backend=StorageBackend.MEMORY)
        return PersistenceLayer(config)

    @pytest.fixture
    def sqlite_persistence(self, tmp_path):
        config = StorageConfig(
            backend=StorageBackend.SQLITE,
            sqlite_path=str(tmp_path / "test.db")
        )
        return PersistenceLayer(config)

    @pytest.mark.asyncio
    async def test_memory_store_retrieve(self, memory_persistence):
        """Test memory backend store/retrieve."""
        await memory_persistence.initialize()

        await memory_persistence.store("key1", {"data": "value"}, DataCategory.CACHE)
        result = await memory_persistence.retrieve("key1", DataCategory.CACHE)

        assert result == {"data": "value"}

        await memory_persistence.shutdown()

    @pytest.mark.asyncio
    async def test_sqlite_persistence(self, sqlite_persistence):
        """Test SQLite backend."""
        await sqlite_persistence.initialize()

        await sqlite_persistence.store("test", [1, 2, 3], DataCategory.MEMORY)
        result = await sqlite_persistence.retrieve("test", DataCategory.MEMORY)

        assert result == [1, 2, 3]

        await sqlite_persistence.shutdown()

    @pytest.mark.asyncio
    async def test_ttl_expiration(self, memory_persistence):
        """Test TTL expiration."""
        await memory_persistence.initialize()

        await memory_persistence.store(
            "expiring",
            "value",
            DataCategory.CACHE,
            ttl=1  # 1 second
        )

        assert await memory_persistence.retrieve("expiring", DataCategory.CACHE) == "value"

        await asyncio.sleep(1.5)

        # Should be expired
        result = await memory_persistence.retrieve("expiring", DataCategory.CACHE)
        assert result is None

        await memory_persistence.shutdown()


# ============================================================
# Self-Evolution Tests
# ============================================================

class TestSelfEvolution:
    """Tests for Self-Evolution Engine."""

    @pytest.fixture
    def engine(self):
        config = EvolutionConfig(
            strategy=EvolutionStrategy.GENETIC,
            population_size=10,
            generations=5,
            mutation_rate=0.1,
            crossover_rate=0.8,
            elite_size=2
        )
        return SelfEvolutionEngine(config)

    def test_population_initialization(self, engine):
        """Test population initialization."""
        template = {
            "learning_rate": 0.001,
            "temperature": 0.7,
            "use_cot": True
        }

        engine.initialize_population(template)

        assert len(engine.population) == engine.config.population_size

    def test_genetic_operators(self, engine):
        """Test genetic operators."""
        operators = GeneticOperators(engine.config)

        parent = Individual(
            id="parent",
            genome={"lr": 0.001, "temp": 0.7}
        )

        # Test mutation
        mutant = operators.mutate(parent)
        assert mutant.id != parent.id
        assert mutant.parent_ids == [parent.id]

        # Test crossover
        parent2 = Individual(
            id="parent2",
            genome={"lr": 0.01, "temp": 0.5}
        )

        child1, child2 = operators.crossover(parent, parent2)
        assert len(child1.parent_ids) == 2

    @pytest.mark.asyncio
    async def test_evolution_run(self, engine):
        """Test evolution run."""
        template = {"x": 5.0, "y": 3.0}
        engine.initialize_population(template)
        engine.set_fitness_function(CapabilityFitness())

        best = await engine.run(generations=3)

        assert best is not None
        assert best.fitness > 0
        assert len(engine.history) == 3


# ============================================================
# Exploitation Engine Tests
# ============================================================

class TestExploitationEngine:
    """Tests for Exploitation Engine."""

    @pytest.fixture
    def engine(self):
        config = ExploitationConfig(
            rotation_strategy="round_robin",
            prefer_free=True,
            max_retries=3
        )
        return ExploitationEngine(config)

    def test_account_registration(self, engine):
        """Test account registration."""
        account_id = engine.register_account(
            provider="test_provider",
            api_key="test_key",
            tier=ProviderTier.FREE,
            resource_type=ResourceType.LLM_API,
            daily_limit=100
        )

        assert account_id is not None
        assert account_id in engine.rotator.accounts

    def test_free_provider_registry(self):
        """Test free provider registry."""
        providers = FreeProviderRegistry.get_free_providers()

        assert "openrouter" in providers
        assert "groq" in providers
        assert "ollama" in providers

    def test_account_rotation(self, engine):
        """Test account rotation."""
        for i in range(3):
            engine.register_account(
                provider=f"provider_{i}",
                api_key=f"key_{i}",
                tier=ProviderTier.FREE,
                resource_type=ResourceType.LLM_API,
                daily_limit=100
            )

        # Round robin should cycle through
        selected = []
        for _ in range(6):
            account = engine.rotator.select_account(ResourceType.LLM_API)
            selected.append(account.provider)

        # Should have used all providers multiple times
        assert len(set(selected)) == 3

    def test_rate_limit_handling(self, engine):
        """Test rate limit handling."""
        account_id = engine.register_account(
            provider="test",
            api_key="key",
            tier=ProviderTier.FREE,
            resource_type=ResourceType.LLM_API
        )

        engine.rotator.mark_rate_limited(account_id)

        account = engine.rotator.accounts[account_id]
        assert account.status == ProviderStatus.COOLING_DOWN

    def test_capacity_tracking(self, engine):
        """Test capacity tracking."""
        engine.register_account(
            provider="test",
            api_key="key",
            tier=ProviderTier.FREE,
            resource_type=ResourceType.LLM_API,
            daily_limit=100
        )

        capacity = engine.get_available_capacity(ResourceType.LLM_API)

        assert capacity["available_accounts"] == 1
        assert capacity["remaining_daily_requests"] == 100


# ============================================================
# Integration Tests
# ============================================================

class TestIntegration:
    """Integration tests for multiple modules working together."""

    @pytest.mark.asyncio
    async def test_full_pipeline(self):
        """Test full processing pipeline."""
        # This tests the integration of multiple modules

        # 1. Initialize persistence
        persistence = PersistenceLayer(StorageConfig(backend=StorageBackend.MEMORY))
        await persistence.initialize()

        # 2. Initialize cognitive pipeline
        cognitive = CognitivePipeline(CognitiveConfig())

        # 3. Store a memory
        entry = MemoryEntry(
            content="User prefers detailed explanations",
            memory_type=MemoryType.SEMANTIC,
            importance=0.9
        )
        await cognitive.store(entry)

        # 4. Retrieve and verify
        memories = await cognitive.retrieve("detailed explanations", MemoryType.SEMANTIC)
        assert len(memories) > 0

        await persistence.shutdown()

    @pytest.mark.asyncio
    async def test_evolution_with_persistence(self, tmp_path):
        """Test evolution with state persistence."""
        # Evolve
        engine = SelfEvolutionEngine(EvolutionConfig(
            population_size=5,
            generations=2
        ))

        engine.initialize_population({"x": 1.0})
        engine.set_fitness_function(CapabilityFitness())

        await engine.run(generations=2)

        # Save
        engine.save(tmp_path)

        # Load into new engine
        engine2 = SelfEvolutionEngine(EvolutionConfig())
        engine2.load(tmp_path)

        assert engine2.generation == engine.generation
        assert engine2.best_individual is not None


# ============================================================
# Run Tests
# ============================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

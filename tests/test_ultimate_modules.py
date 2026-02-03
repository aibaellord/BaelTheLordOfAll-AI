"""
BAEL - Test Suite for Ultimate Modules
Tests for RL, NAS, DSL, and Ultimate Orchestrator.
"""

import asyncio
from typing import Any, Dict

import numpy as np
import pytest

# =============================================================================
# REINFORCEMENT LEARNING TESTS
# =============================================================================

class TestReinforcementLearning:
    """Tests for RL Engine."""

    def test_state_creation(self):
        """Test State creation."""
        from core.reinforcement import State

        state = State.from_context({"query": "test", "value": 42})
        assert state.id is not None
        assert state.features["query"] == "test"
        assert state.features["value"] == 42

    def test_state_vector(self):
        """Test State vector conversion."""
        from core.reinforcement import State

        state = State.from_context({"test": "data"})
        vector = state.to_vector(64)
        assert vector.shape == (64,)

    def test_action_creation(self):
        """Test Action creation."""
        from core.reinforcement import Action

        action = Action(id="act1", name="test_action", cost=0.5)
        assert action.id == "act1"
        assert action.name == "test_action"
        assert action.cost == 0.5

    def test_multi_armed_bandit(self):
        """Test Multi-Armed Bandit."""
        from core.reinforcement import ExplorationStrategy, MultiArmedBandit

        bandit = MultiArmedBandit(5, ExplorationStrategy.EPSILON_GREEDY)

        # Test arm selection
        arm = bandit.select_arm(epsilon=0.0)  # Greedy
        assert 0 <= arm < 5

        # Test update
        bandit.update(arm, 1.0)
        assert bandit.counts[arm] == 1
        assert bandit.values[arm] > 0

    def test_q_learning_agent(self):
        """Test Q-Learning Agent."""
        from core.reinforcement import Action, QLearningAgent, State

        actions = [
            Action(id="a1", name="action1"),
            Action(id="a2", name="action2")
        ]
        agent = QLearningAgent(actions, epsilon=0.0)

        state = State.from_context({"test": 1})

        # Select action
        action = agent.select_action(state)
        assert action in actions

        # Update
        next_state = State.from_context({"test": 2})
        td_error = agent.update(state, action, 1.0, next_state, False)
        assert isinstance(td_error, float)

    def test_policy_gradient_agent(self):
        """Test Policy Gradient Agent."""
        from core.reinforcement import PolicyGradientAgent, State

        agent = PolicyGradientAgent(state_dim=64, n_actions=3)
        state = State.from_context({"test": 1})

        # Select action
        action = agent.select_action(state)
        assert 0 <= action < 3

        # Store reward
        agent.store_reward(1.0)
        assert len(agent.rewards) == 1

        # Update
        loss = agent.update()
        assert isinstance(loss, float)

    def test_actor_critic_agent(self):
        """Test Actor-Critic Agent."""
        from core.reinforcement import ActorCriticAgent, State

        agent = ActorCriticAgent(state_dim=64, n_actions=3)
        state = State.from_context({"test": 1})
        next_state = State.from_context({"test": 2})

        # Select action
        action = agent.select_action(state)
        assert 0 <= action < 3

        # Update
        advantage, td_error = agent.update(state, action, 1.0, next_state, False)
        assert isinstance(advantage, float)
        assert isinstance(td_error, float)

    def test_experience_replay(self):
        """Test Experience Replay Buffer."""
        from core.reinforcement import (Action, Experience,
                                        ExperienceReplayBuffer, State)

        buffer = ExperienceReplayBuffer(capacity=100)

        # Add experiences
        for i in range(10):
            exp = Experience(
                state=State.from_context({"i": i}),
                action=Action(id=f"a{i}", name=f"action{i}"),
                reward=float(i),
                next_state=State.from_context({"i": i+1}),
                done=False
            )
            buffer.add(exp)

        assert len(buffer) == 10

        # Sample
        batch = buffer.sample(5)
        assert len(batch) == 5

    @pytest.mark.asyncio
    async def test_rl_engine(self):
        """Test full RL Engine."""
        from core.reinforcement import (Action, ReinforcementLearningEngine,
                                        RLAlgorithm, State)

        actions = [
            Action(id="a1", name="think"),
            Action(id="a2", name="act"),
            Action(id="a3", name="wait")
        ]

        engine = ReinforcementLearningEngine(
            actions=actions,
            algorithm=RLAlgorithm.Q_LEARNING
        )

        # Select action
        state = State.from_context({"query": "test"})
        action = await engine.select_action(state)
        assert action in actions

        # Step
        next_state = State.from_context({"query": "test", "step": 1})
        exp = await engine.step(state, action, next_state, {"success": True}, done=True)

        assert exp.reward > 0  # TaskSuccessReward should give positive reward

        # Get summary
        summary = engine.get_policy_summary()
        assert summary["algorithm"] == "q_learning"
        assert summary["total_steps"] == 1


# =============================================================================
# NEURAL ARCHITECTURE SEARCH TESTS
# =============================================================================

class TestNAS:
    """Tests for NAS Controller."""

    def test_search_space_builder(self):
        """Test SearchSpaceBuilder."""
        from core.nas import OperationType, SearchSpaceBuilder

        space = SearchSpaceBuilder("test") \
            .with_operations([OperationType.LINEAR, OperationType.ATTENTION]) \
            .with_max_cells(4) \
            .with_max_ops(3) \
            .build()

        assert space.name == "test"
        assert len(space.operations) == 2
        assert space.max_cells == 4
        assert space.max_ops_per_cell == 3

    def test_architecture_sampler(self):
        """Test ArchitectureSampler."""
        from core.nas import ArchitectureSampler, SearchSpaceBuilder

        space = SearchSpaceBuilder("test").build()
        sampler = ArchitectureSampler(space)

        # Sample operation
        op = sampler.sample_operation()
        assert op.op_type is not None

        # Sample cell
        cell = sampler.sample_cell("test_cell")
        assert cell.name == "test_cell"
        assert len(cell.operations) > 0

        # Sample architecture
        arch = sampler.sample_architecture()
        assert arch.id is not None
        assert len(arch.cells) > 0

    @pytest.mark.asyncio
    async def test_proxy_estimator(self):
        """Test ProxyEstimator."""
        from core.nas import (ArchitectureSampler, ProxyEstimator,
                              SearchSpaceBuilder)

        space = SearchSpaceBuilder("test").build()
        sampler = ArchitectureSampler(space)
        estimator = ProxyEstimator()

        arch = sampler.sample_architecture()
        perf = await estimator.estimate(arch)

        assert "accuracy" in perf
        assert "parameters" in perf
        assert "flops" in perf
        assert "latency" in perf
        assert 0 <= perf["accuracy"] <= 1

    @pytest.mark.asyncio
    async def test_evolutionary_nas(self):
        """Test EvolutionaryNAS."""
        from core.nas import EvolutionaryNAS, SearchSpaceBuilder

        space = SearchSpaceBuilder("test").with_max_cells(2).build()
        nas = EvolutionaryNAS(space, population_size=5)

        # Initialize
        await nas.initialize_population()
        assert len(nas.population) == 5

        # Evolve
        acc = await nas.evolve_generation()
        assert isinstance(acc, float)
        assert nas.generation == 1

    @pytest.mark.asyncio
    async def test_differentiable_nas(self):
        """Test DifferentiableNAS."""
        from core.nas import DifferentiableNAS, SearchSpaceBuilder

        space = SearchSpaceBuilder("test").with_max_cells(2).build()
        nas = DifferentiableNAS(space)

        # Sample architecture
        arch = nas.sample_discrete_architecture()
        assert arch is not None

        # Get weights
        weights = nas.get_architecture_weights()
        assert weights.shape[0] == space.max_cells

    @pytest.mark.asyncio
    async def test_nas_controller(self):
        """Test full NAS Controller."""
        from core.nas import NASController, SearchStrategy

        controller = NASController(strategy=SearchStrategy.RANDOM)

        # Run search
        best = await controller.search(n_iterations=5)
        assert best is not None
        assert best.evaluated

        # Export
        json_output = controller.export_architecture(best, "json")
        assert "id" in json_output


# =============================================================================
# DSL TESTS
# =============================================================================

class TestDSL:
    """Tests for DSL Rule Engine."""

    def test_lexer(self):
        """Test Lexer."""
        from core.dsl import Lexer, TokenType

        source = "rule test: if x > 5 then true"
        lexer = Lexer(source)
        tokens = lexer.tokenize()

        assert any(t.type == TokenType.RULE for t in tokens)
        assert any(t.type == TokenType.IDENTIFIER for t in tokens)
        assert any(t.type == TokenType.GT for t in tokens)
        assert any(t.type == TokenType.NUMBER for t in tokens)

    def test_lexer_strings(self):
        """Test Lexer with strings."""
        from core.dsl import Lexer, TokenType

        source = '"hello world"'
        lexer = Lexer(source)
        tokens = lexer.tokenize()

        string_token = [t for t in tokens if t.type == TokenType.STRING][0]
        assert string_token.value == "hello world"

    def test_literal_node(self):
        """Test LiteralNode."""
        from core.dsl import LiteralNode

        node = LiteralNode(42)
        assert node.evaluate({}) == 42

        node = LiteralNode("hello")
        assert node.evaluate({}) == "hello"

    def test_identifier_node(self):
        """Test IdentifierNode."""
        from core.dsl import IdentifierNode

        node = IdentifierNode("x")
        assert node.evaluate({"x": 10}) == 10

        # Dotted name
        node = IdentifierNode("user.name")
        assert node.evaluate({"user": {"name": "Alice"}}) == "Alice"

    def test_binary_ops(self):
        """Test BinaryOpNode."""
        from core.dsl import BinaryOpNode, LiteralNode, Operator

        # Equality
        node = BinaryOpNode(Operator.EQ, LiteralNode(5), LiteralNode(5))
        assert node.evaluate({}) == True

        # Greater than
        node = BinaryOpNode(Operator.GT, LiteralNode(10), LiteralNode(5))
        assert node.evaluate({}) == True

        # AND
        node = BinaryOpNode(Operator.AND, LiteralNode(True), LiteralNode(True))
        assert node.evaluate({}) == True

        # OR
        node = BinaryOpNode(Operator.OR, LiteralNode(False), LiteralNode(True))
        assert node.evaluate({}) == True

        # IMPLIES
        node = BinaryOpNode(Operator.IMPLIES, LiteralNode(True), LiteralNode(True))
        assert node.evaluate({}) == True

    def test_unary_ops(self):
        """Test UnaryOpNode."""
        from core.dsl import LiteralNode, Operator, UnaryOpNode

        node = UnaryOpNode(Operator.NOT, LiteralNode(False))
        assert node.evaluate({}) == True

    def test_quantifier_forall(self):
        """Test FORALL quantifier."""
        from core.dsl import (BinaryOpNode, IdentifierNode, LiteralNode,
                              Operator, QuantifierNode)

        # forall x in items: x > 0
        node = QuantifierNode(
            quantifier=Operator.FORALL,
            variable="x",
            domain=IdentifierNode("items"),
            body=BinaryOpNode(Operator.GT, IdentifierNode("x"), LiteralNode(0))
        )

        assert node.evaluate({"items": [1, 2, 3]}) == True
        assert node.evaluate({"items": [1, -1, 3]}) == False

    def test_quantifier_exists(self):
        """Test EXISTS quantifier."""
        from core.dsl import (BinaryOpNode, IdentifierNode, LiteralNode,
                              Operator, QuantifierNode)

        # exists x in items: x > 5
        node = QuantifierNode(
            quantifier=Operator.EXISTS,
            variable="x",
            domain=IdentifierNode("items"),
            body=BinaryOpNode(Operator.GT, IdentifierNode("x"), LiteralNode(5))
        )

        assert node.evaluate({"items": [1, 6, 3]}) == True
        assert node.evaluate({"items": [1, 2, 3]}) == False

    def test_rule_engine(self):
        """Test RuleEngine."""
        from core.dsl import (BinaryOpNode, IdentifierNode, LiteralNode,
                              Operator, Rule, RuleEngine)

        engine = RuleEngine()

        # Add rule: if score > 80 then "pass"
        rule = Rule(
            name="grade_rule",
            condition=BinaryOpNode(Operator.GT, IdentifierNode("score"), LiteralNode(80)),
            action=LiteralNode("pass"),
            priority=1
        )
        engine.add_rule(rule)

        # Evaluate
        results = engine.evaluate({"score": 85})
        assert len(results) == 1
        assert results[0] == ("grade_rule", "pass")

        # Non-matching
        results = engine.evaluate({"score": 70})
        assert len(results) == 0

    def test_dsl_builder(self):
        """Test DSLBuilder."""
        from core.dsl import DSLBuilder

        builder = DSLBuilder()

        builder.rule("high_priority") \
            .when_gt("urgency", 8) \
            .then_value("immediate") \
            .priority(10) \
            .build()

        engine = builder.get_engine()

        results = engine.evaluate({"urgency": 9})
        assert len(results) == 1
        assert results[0][1] == "immediate"

    def test_compile_rules(self):
        """Test compile_rules function."""
        from core.dsl import compile_rules

        source = """
        rule check_age:
            if age >= 18 then "adult"

        rule check_score with priority 10:
            if score > 90 then "excellent"
        """

        engine = compile_rules(source)

        # Check rules were added
        assert "check_age" in engine.rules
        assert "check_score" in engine.rules
        assert engine.rules["check_score"].priority == 10

        # Evaluate
        results = engine.evaluate({"age": 25, "score": 95})
        assert ("check_age", "adult") in results
        assert ("check_score", "excellent") in results


# =============================================================================
# ULTIMATE ORCHESTRATOR TESTS
# =============================================================================

class TestUltimateOrchestrator:
    """Tests for Ultimate Orchestrator."""

    def test_config_modes(self):
        """Test configuration modes."""
        from core.ultimate import BAELMode, Capability, UltimateConfig

        # Minimal mode
        config = UltimateConfig(mode=BAELMode.MINIMAL)
        assert Capability.DEDUCTIVE in config.enabled_capabilities
        assert len(config.enabled_capabilities) < 5

        # Maximum mode
        config = UltimateConfig(mode=BAELMode.MAXIMUM)
        assert len(config.enabled_capabilities) == len(Capability)

    def test_result_creation(self):
        """Test UltimateResult."""
        from core.ultimate import Capability, UltimateResult

        result = UltimateResult(
            success=True,
            response="Test response",
            capabilities_used=[Capability.DEDUCTIVE],
            confidence=0.9
        )

        data = result.to_dict()
        assert data["success"] == True
        assert data["response"] == "Test response"
        assert "deductive" in data["capabilities_used"]
        assert data["confidence"] == 0.9

    @pytest.mark.asyncio
    async def test_orchestrator_init(self):
        """Test orchestrator initialization."""
        from core.ultimate import (BAELMode, UltimateConfig,
                                   UltimateOrchestrator)

        config = UltimateConfig(mode=BAELMode.MINIMAL)
        orchestrator = UltimateOrchestrator(config)

        await orchestrator.initialize()

        assert orchestrator._initialized
        status = orchestrator.get_status()
        assert status["initialized"] == True

    @pytest.mark.asyncio
    async def test_orchestrator_process(self):
        """Test query processing."""
        from core.ultimate import (BAELMode, UltimateConfig,
                                   UltimateOrchestrator)

        config = UltimateConfig(mode=BAELMode.MINIMAL)
        orchestrator = UltimateOrchestrator(config)

        result = await orchestrator.process("Test query")

        assert result.success
        assert result.response != ""
        assert result.duration_ms >= 0

    @pytest.mark.asyncio
    async def test_capability_detection(self):
        """Test capability detection from query."""
        from core.ultimate import (BAELMode, Capability, UltimateConfig,
                                   UltimateOrchestrator)

        config = UltimateConfig(mode=BAELMode.MAXIMUM)
        orchestrator = UltimateOrchestrator(config)

        # Test causal detection
        caps = await orchestrator._analyze_query("Why did this happen?")
        assert Capability.CAUSAL in caps

        # Test code detection
        caps = await orchestrator._analyze_query("Execute this Python code")
        assert Capability.CODE_EXECUTION in caps

    @pytest.mark.asyncio
    async def test_create_ultimate_factory(self):
        """Test create_ultimate factory."""
        from core.ultimate import create_ultimate

        bael = await create_ultimate(mode="minimal")

        assert bael._initialized
        caps = bael.get_capabilities()
        assert len(caps) > 0

    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test health check."""
        from core.ultimate import create_ultimate

        bael = await create_ultimate(mode="minimal")
        health = await bael.health_check()

        assert isinstance(health, dict)


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestIntegration:
    """Integration tests across modules."""

    @pytest.mark.asyncio
    async def test_rl_with_dsl(self):
        """Test RL with DSL rules."""
        from core.dsl import DSLBuilder, RuleEngine
        from core.reinforcement import (Action, ReinforcementLearningEngine,
                                        State)

        # Create RL engine
        actions = [Action(id="a1", name="explore"), Action(id="a2", name="exploit")]
        rl = ReinforcementLearningEngine(actions)

        # Create rule engine
        builder = DSLBuilder()
        builder.rule("prefer_exploit") \
            .when_gt("confidence", 0.8) \
            .then_value("exploit") \
            .build()
        rules = builder.get_engine()

        # Use rules to guide RL
        context = {"confidence": 0.9}
        results = rules.evaluate(context)

        if results:
            preferred = results[0][1]
            state = State.from_context(context)
            action = await rl.select_action(state)
            # In a real system, would bias toward preferred action

    @pytest.mark.asyncio
    async def test_nas_with_rl(self):
        """Test NAS with RL-based search."""
        from core.nas import NASController, SearchStrategy
        from core.reinforcement import Action, ReinforcementLearningEngine

        # NAS could use RL for architecture decisions
        nas = NASController(strategy=SearchStrategy.EVOLUTIONARY)

        # Run short search
        best = await nas.search(n_iterations=3)
        assert best is not None


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

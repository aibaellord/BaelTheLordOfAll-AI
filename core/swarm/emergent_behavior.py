"""
BAEL Emergent Behavior
=======================

Detect and leverage emergent behaviors in swarm.
Enables self-organization and adaptive strategies.

Features:
- Pattern detection
- Emergent coordination
- Self-organization
- Adaptive strategies
- Swarm optimization
"""

import asyncio
import hashlib
import logging
import math
import random
from collections import Counter, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class PatternType(Enum):
    """Emergent pattern types."""
    CLUSTERING = "clustering"  # Agents grouping
    SPECIALIZATION = "specialization"  # Role emergence
    LOAD_BALANCING = "load_balancing"  # Natural distribution
    CASCADING = "cascading"  # Chain reactions
    OSCILLATION = "oscillation"  # Periodic behavior
    CONVERGENCE = "convergence"  # Solution convergence
    DIVERGENCE = "divergence"  # Exploration
    SWARM_INTELLIGENCE = "swarm_intelligence"  # Collective wisdom


class StrategyType(Enum):
    """Adaptive strategy types."""
    EXPLOITATION = "exploitation"  # Use known good
    EXPLORATION = "exploration"  # Try new things
    BALANCED = "balanced"  # Balance both
    MIMICRY = "mimicry"  # Copy successful
    MUTATION = "mutation"  # Random variation


@dataclass
class BehaviorPattern:
    """An emergent behavior pattern."""
    id: str
    pattern_type: PatternType

    # Detection
    confidence: float = 0.0
    occurrences: int = 0

    # Characteristics
    agents_involved: List[str] = field(default_factory=list)
    triggers: List[str] = field(default_factory=list)
    effects: List[str] = field(default_factory=list)

    # Temporal
    first_seen: datetime = field(default_factory=datetime.now)
    last_seen: datetime = field(default_factory=datetime.now)
    duration_avg: float = 0.0

    # Value
    positive_impact: float = 0.0
    should_encourage: bool = True


@dataclass
class SwarmDynamics:
    """Swarm dynamics analysis."""
    # Population
    agent_count: int = 0
    active_ratio: float = 0.0

    # Activity
    task_throughput: float = 0.0
    communication_rate: float = 0.0

    # Coordination
    clustering_coefficient: float = 0.0
    information_flow: float = 0.0

    # Health
    entropy: float = 0.0
    stability: float = 1.0

    # Timestamp
    measured_at: datetime = field(default_factory=datetime.now)


@dataclass
class AdaptiveStrategy:
    """An adaptive strategy."""
    id: str
    strategy_type: StrategyType

    # Configuration
    parameters: Dict[str, Any] = field(default_factory=dict)

    # Performance
    success_rate: float = 0.5
    applications: int = 0

    # Evolution
    parent_id: Optional[str] = None
    generation: int = 0
    mutations: List[str] = field(default_factory=list)


class EmergentBehavior:
    """
    Emergent behavior detection for BAEL swarm.

    Detects and leverages self-organizing patterns.
    """

    def __init__(self):
        # Pattern detection
        self._patterns: Dict[str, BehaviorPattern] = {}

        # Event history
        self._events: deque = deque(maxlen=10000)

        # Agent states
        self._agent_states: Dict[str, List[Dict]] = {}

        # Strategies
        self._strategies: Dict[str, AdaptiveStrategy] = {}
        self._active_strategy: Optional[AdaptiveStrategy] = None

        # Swarm metrics
        self._dynamics_history: List[SwarmDynamics] = []

        # Detection thresholds
        self._thresholds = {
            "clustering_min_agents": 3,
            "pattern_confidence": 0.7,
            "oscillation_periods": 3,
        }

        # Stats
        self.stats = {
            "patterns_detected": 0,
            "strategies_evolved": 0,
            "adaptations": 0,
        }

    def record_event(
        self,
        event_type: str,
        agent_id: str,
        data: Dict[str, Any],
    ) -> None:
        """Record an event for pattern detection."""
        event = {
            "type": event_type,
            "agent": agent_id,
            "data": data,
            "timestamp": datetime.now(),
        }

        self._events.append(event)

        # Track agent state
        if agent_id not in self._agent_states:
            self._agent_states[agent_id] = []
        self._agent_states[agent_id].append(event)

        # Keep only recent states
        if len(self._agent_states[agent_id]) > 100:
            self._agent_states[agent_id] = self._agent_states[agent_id][-100:]

    async def detect_patterns(self) -> List[BehaviorPattern]:
        """Detect emergent patterns in swarm behavior."""
        detected = []

        # Detect clustering
        clustering = await self._detect_clustering()
        if clustering:
            detected.append(clustering)

        # Detect specialization
        specialization = await self._detect_specialization()
        if specialization:
            detected.append(specialization)

        # Detect oscillation
        oscillation = await self._detect_oscillation()
        if oscillation:
            detected.append(oscillation)

        # Detect convergence
        convergence = await self._detect_convergence()
        if convergence:
            detected.append(convergence)

        # Update stats
        for pattern in detected:
            if pattern.id not in self._patterns:
                self.stats["patterns_detected"] += 1
            self._patterns[pattern.id] = pattern

        return detected

    async def _detect_clustering(self) -> Optional[BehaviorPattern]:
        """Detect agent clustering behavior."""
        if len(self._events) < 100:
            return None

        # Analyze agent interactions
        recent = list(self._events)[-100:]

        # Build interaction graph
        interactions: Dict[str, Set[str]] = {}
        for event in recent:
            agent = event["agent"]
            if agent not in interactions:
                interactions[agent] = set()

            # Check for related agents in data
            related = event.get("data", {}).get("related_agents", [])
            interactions[agent].update(related)

        # Find clusters
        clusters = self._find_clusters(interactions)

        if len(clusters) > 0 and any(len(c) >= self._thresholds["clustering_min_agents"] for c in clusters):
            largest = max(clusters, key=len)

            pattern_id = f"cluster_{hashlib.md5(str(sorted(largest)).encode()).hexdigest()[:8]}"

            return BehaviorPattern(
                id=pattern_id,
                pattern_type=PatternType.CLUSTERING,
                confidence=min(1.0, len(largest) / len(interactions)),
                agents_involved=list(largest),
                effects=["increased_coordination", "task_specialization"],
                should_encourage=True,
            )

        return None

    def _find_clusters(
        self,
        interactions: Dict[str, Set[str]],
    ) -> List[Set[str]]:
        """Find clusters using connected components."""
        visited = set()
        clusters = []

        def dfs(node: str, cluster: Set[str]):
            if node in visited:
                return
            visited.add(node)
            cluster.add(node)

            for neighbor in interactions.get(node, set()):
                dfs(neighbor, cluster)

        for agent in interactions:
            if agent not in visited:
                cluster: Set[str] = set()
                dfs(agent, cluster)
                if cluster:
                    clusters.append(cluster)

        return clusters

    async def _detect_specialization(self) -> Optional[BehaviorPattern]:
        """Detect role specialization emergence."""
        # Analyze task types per agent
        task_distribution: Dict[str, Counter] = {}

        for agent, states in self._agent_states.items():
            task_distribution[agent] = Counter()
            for state in states:
                if state["type"] == "task_completed":
                    task_type = state["data"].get("task_type", "unknown")
                    task_distribution[agent][task_type] += 1

        # Check for specialization (agent doing >70% of one type)
        specialists = []
        for agent, counts in task_distribution.items():
            if not counts:
                continue

            total = sum(counts.values())
            if total < 5:
                continue

            most_common = counts.most_common(1)[0]
            if most_common[1] / total > 0.7:
                specialists.append((agent, most_common[0]))

        if len(specialists) >= 2:
            return BehaviorPattern(
                id=f"specialization_{len(specialists)}",
                pattern_type=PatternType.SPECIALIZATION,
                confidence=len(specialists) / max(len(task_distribution), 1),
                agents_involved=[s[0] for s in specialists],
                effects=["efficiency_increase", "expertise_development"],
                should_encourage=True,
            )

        return None

    async def _detect_oscillation(self) -> Optional[BehaviorPattern]:
        """Detect oscillating behavior patterns."""
        # Analyze event frequencies over time
        if len(self._events) < 50:
            return None

        # Bucket events by minute
        buckets: Counter = Counter()
        for event in self._events:
            minute = event["timestamp"].replace(second=0, microsecond=0)
            buckets[minute] += 1

        if len(buckets) < 5:
            return None

        # Check for periodic pattern
        values = [buckets[k] for k in sorted(buckets.keys())]

        # Simple periodicity check
        peaks = []
        for i in range(1, len(values) - 1):
            if values[i] > values[i-1] and values[i] > values[i+1]:
                peaks.append(i)

        if len(peaks) >= self._thresholds["oscillation_periods"]:
            # Calculate period
            periods = [peaks[i+1] - peaks[i] for i in range(len(peaks)-1)]
            avg_period = sum(periods) / len(periods) if periods else 0

            return BehaviorPattern(
                id=f"oscillation_period_{avg_period:.1f}",
                pattern_type=PatternType.OSCILLATION,
                confidence=0.8,
                effects=["predictable_load", "resource_planning"],
                positive_impact=0.5,
            )

        return None

    async def _detect_convergence(self) -> Optional[BehaviorPattern]:
        """Detect solution convergence."""
        # Check if agents are converging on similar solutions
        recent = list(self._events)[-50:]

        solutions: List[Any] = []
        for event in recent:
            if event["type"] in ["solution_proposed", "result_reported"]:
                solutions.append(event["data"].get("solution", event["data"].get("result")))

        if len(solutions) < 5:
            return None

        # Simple convergence check - count similar solutions
        if all(isinstance(s, dict) for s in solutions):
            # Compare keys
            key_counts = Counter()
            for s in solutions:
                for k in s.keys():
                    key_counts[k] += 1

            # High overlap indicates convergence
            avg_overlap = sum(key_counts.values()) / len(solutions) / max(len(key_counts), 1)

            if avg_overlap > 0.8:
                return BehaviorPattern(
                    id="convergence_solutions",
                    pattern_type=PatternType.CONVERGENCE,
                    confidence=avg_overlap,
                    effects=["consensus_forming", "solution_refinement"],
                    should_encourage=True,
                )

        return None

    def analyze_dynamics(
        self,
        agents: List[Dict[str, Any]],
    ) -> SwarmDynamics:
        """Analyze current swarm dynamics."""
        now = datetime.now()

        # Calculate metrics
        agent_count = len(agents)
        active = sum(1 for a in agents if a.get("status") == "active")
        active_ratio = active / agent_count if agent_count > 0 else 0

        # Task throughput
        recent_tasks = sum(
            1 for e in self._events
            if e["type"] == "task_completed" and
            (now - e["timestamp"]).seconds < 60
        )

        # Communication rate
        recent_messages = sum(
            1 for e in self._events
            if e["type"] == "message" and
            (now - e["timestamp"]).seconds < 60
        )

        # Calculate entropy (diversity of agent states)
        state_counts = Counter()
        for agent in agents:
            state_counts[agent.get("status", "unknown")] += 1

        entropy = 0.0
        if agent_count > 0:
            for count in state_counts.values():
                p = count / agent_count
                if p > 0:
                    entropy -= p * math.log2(p)

        dynamics = SwarmDynamics(
            agent_count=agent_count,
            active_ratio=active_ratio,
            task_throughput=recent_tasks,
            communication_rate=recent_messages,
            entropy=entropy,
            stability=1.0 - (entropy / math.log2(max(len(state_counts), 2))),
        )

        self._dynamics_history.append(dynamics)

        # Keep only recent history
        if len(self._dynamics_history) > 1000:
            self._dynamics_history = self._dynamics_history[-1000:]

        return dynamics

    def evolve_strategy(
        self,
        current: Optional[AdaptiveStrategy] = None,
    ) -> AdaptiveStrategy:
        """Evolve an adaptive strategy."""
        if current is None:
            # Create initial strategy
            strategy = AdaptiveStrategy(
                id=f"strategy_{len(self._strategies)}",
                strategy_type=StrategyType.BALANCED,
                parameters={
                    "exploration_rate": 0.3,
                    "mutation_rate": 0.1,
                    "learning_rate": 0.05,
                },
            )
        else:
            # Evolve from current
            strategy = AdaptiveStrategy(
                id=f"strategy_{len(self._strategies)}",
                strategy_type=self._select_strategy_type(current),
                parameters=self._mutate_parameters(current.parameters),
                parent_id=current.id,
                generation=current.generation + 1,
            )

        self._strategies[strategy.id] = strategy
        self.stats["strategies_evolved"] += 1

        return strategy

    def _select_strategy_type(
        self,
        current: AdaptiveStrategy,
    ) -> StrategyType:
        """Select strategy type based on performance."""
        if current.success_rate < 0.3:
            return StrategyType.EXPLORATION
        elif current.success_rate > 0.7:
            return StrategyType.EXPLOITATION
        else:
            return StrategyType.BALANCED

    def _mutate_parameters(
        self,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Mutate strategy parameters."""
        mutated = params.copy()

        for key, value in mutated.items():
            if isinstance(value, float):
                # Add random noise
                noise = random.gauss(0, 0.1)
                mutated[key] = max(0.0, min(1.0, value + noise))

        return mutated

    def apply_strategy(
        self,
        strategy: AdaptiveStrategy,
    ) -> Dict[str, Any]:
        """Apply a strategy and get configuration."""
        self._active_strategy = strategy
        strategy.applications += 1
        self.stats["adaptations"] += 1

        config = {}

        if strategy.strategy_type == StrategyType.EXPLORATION:
            config["try_new_approaches"] = True
            config["risk_tolerance"] = 0.7

        elif strategy.strategy_type == StrategyType.EXPLOITATION:
            config["use_proven_methods"] = True
            config["risk_tolerance"] = 0.3

        elif strategy.strategy_type == StrategyType.MIMICRY:
            config["copy_successful"] = True
            config["innovation_rate"] = 0.1

        elif strategy.strategy_type == StrategyType.MUTATION:
            config["random_variation"] = True
            config["variation_magnitude"] = strategy.parameters.get("mutation_rate", 0.1)

        else:  # BALANCED
            config["exploration_exploitation_ratio"] = strategy.parameters.get("exploration_rate", 0.3)

        return config

    def report_outcome(
        self,
        strategy_id: str,
        success: bool,
    ) -> None:
        """Report strategy outcome."""
        if strategy_id in self._strategies:
            strategy = self._strategies[strategy_id]
            # Update success rate with exponential moving average
            alpha = 0.1
            strategy.success_rate = (1 - alpha) * strategy.success_rate + alpha * (1.0 if success else 0.0)

    def get_patterns(self) -> List[BehaviorPattern]:
        """Get detected patterns."""
        return list(self._patterns.values())

    def get_stats(self) -> Dict[str, Any]:
        """Get behavior statistics."""
        return {
            **self.stats,
            "patterns": len(self._patterns),
            "strategies": len(self._strategies),
            "events_recorded": len(self._events),
        }


def demo():
    """Demonstrate emergent behavior detection."""
    import asyncio

    print("=" * 60)
    print("BAEL Emergent Behavior Demo")
    print("=" * 60)

    async def run_demo():
        behavior = EmergentBehavior()

        # Record simulated events
        print("\nRecording events...")
        agents = ["agent_1", "agent_2", "agent_3", "agent_4", "agent_5"]

        for i in range(50):
            # Simulate clustering
            agent = random.choice(agents[:3])  # First 3 cluster together
            behavior.record_event("task_completed", agent, {
                "task_type": "analysis",
                "related_agents": [a for a in agents[:3] if a != agent],
            })

            # Simulate specialization
            behavior.record_event("task_completed", "agent_4", {
                "task_type": "code_review",  # Agent 4 specializes
            })

            behavior.record_event("task_completed", "agent_5", {
                "task_type": "testing",  # Agent 5 specializes
            })

        # Detect patterns
        print("\nDetecting patterns...")
        patterns = await behavior.detect_patterns()

        print(f"\nPatterns detected: {len(patterns)}")
        for pattern in patterns:
            print(f"  - {pattern.pattern_type.value}: confidence={pattern.confidence:.2f}")
            if pattern.agents_involved:
                print(f"    Agents: {pattern.agents_involved}")

        # Analyze dynamics
        print("\nAnalyzing dynamics...")
        agent_data = [
            {"id": a, "status": "active" if i < 4 else "idle"}
            for i, a in enumerate(agents)
        ]

        dynamics = behavior.analyze_dynamics(agent_data)
        print(f"  Active ratio: {dynamics.active_ratio:.1%}")
        print(f"  Task throughput: {dynamics.task_throughput}/min")
        print(f"  Entropy: {dynamics.entropy:.2f}")
        print(f"  Stability: {dynamics.stability:.2f}")

        # Evolve strategy
        print("\nEvolving strategies...")
        strategy1 = behavior.evolve_strategy()
        print(f"  Initial: {strategy1.strategy_type.value}")

        # Simulate outcomes
        behavior.report_outcome(strategy1.id, success=True)
        behavior.report_outcome(strategy1.id, success=True)
        behavior.report_outcome(strategy1.id, success=False)

        strategy2 = behavior.evolve_strategy(strategy1)
        print(f"  Evolved: {strategy2.strategy_type.value} (gen {strategy2.generation})")

        # Apply strategy
        config = behavior.apply_strategy(strategy2)
        print(f"  Config: {config}")

        print(f"\nStats: {behavior.get_stats()}")

    asyncio.run(run_demo())


if __name__ == "__main__":
    demo()

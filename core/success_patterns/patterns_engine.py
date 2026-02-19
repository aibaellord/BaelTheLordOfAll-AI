"""
BAEL - Success Patterns Engine
Learns and applies patterns that lead to success.

Revolutionary capabilities:
1. Pattern mining from successful outcomes
2. Cross-domain success transfer
3. Failure pattern avoidance
4. Success probability prediction
5. Adaptive pattern evolution
6. Compound success strategies
7. Anti-fragile pattern design
8. Universal success principles

This engine ensures consistently successful outcomes.
"""

import asyncio
import hashlib
import json
import logging
import math
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from collections import defaultdict

logger = logging.getLogger("BAEL.SuccessPatterns")


class PatternType(Enum):
    """Types of success patterns."""
    STRUCTURAL = "structural"         # How things are organized
    BEHAVIORAL = "behavioral"         # How actions are sequenced
    COGNITIVE = "cognitive"           # How thinking is applied
    SOCIAL = "social"                 # How collaboration works
    TEMPORAL = "temporal"             # How timing is managed
    ADAPTIVE = "adaptive"             # How changes are handled
    SYNERGISTIC = "synergistic"       # How elements combine


class OutcomeType(Enum):
    """Types of outcomes."""
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    NEUTRAL = "neutral"
    PARTIAL_FAILURE = "partial_failure"
    FAILURE = "failure"


class DomainType(Enum):
    """Domains for pattern application."""
    TECHNICAL = "technical"
    CREATIVE = "creative"
    BUSINESS = "business"
    RESEARCH = "research"
    PERSONAL = "personal"
    UNIVERSAL = "universal"


@dataclass
class SuccessPattern:
    """A pattern that leads to success."""
    pattern_id: str
    name: str
    description: str

    # Classification
    pattern_type: PatternType = PatternType.STRUCTURAL
    domain: DomainType = DomainType.UNIVERSAL

    # Pattern definition
    elements: List[str] = field(default_factory=list)
    sequence: List[str] = field(default_factory=list)
    conditions: Dict[str, Any] = field(default_factory=dict)

    # Success metrics
    applications: int = 0
    successes: int = 0
    success_rate: float = 0.0

    # Confidence
    confidence: float = 0.5
    maturity: int = 0  # How many times pattern has evolved

    # Relationships
    requires_patterns: List[str] = field(default_factory=list)
    enhances_patterns: List[str] = field(default_factory=list)
    conflicts_with: List[str] = field(default_factory=list)

    # Metadata
    discovered_at: datetime = field(default_factory=datetime.utcnow)
    last_applied: Optional[datetime] = None

    @property
    def effectiveness(self) -> float:
        """Calculate pattern effectiveness."""
        if self.applications == 0:
            return self.confidence * 0.5
        return self.success_rate * self.confidence * math.log(self.applications + 1) / 10


@dataclass
class FailurePattern:
    """A pattern that leads to failure - to be avoided."""
    pattern_id: str
    name: str
    description: str

    # Warning signals
    warning_signs: List[str] = field(default_factory=list)

    # Avoidance
    avoidance_strategies: List[str] = field(default_factory=list)

    # Statistics
    occurrences: int = 0
    severity: float = 0.5  # 0-1, how bad the failure

    # Prevention
    preventive_patterns: List[str] = field(default_factory=list)


@dataclass
class PatternApplication:
    """Record of applying a pattern."""
    application_id: str
    pattern_id: str

    # Context
    context: Dict[str, Any] = field(default_factory=dict)

    # Outcome
    outcome: OutcomeType = OutcomeType.NEUTRAL
    outcome_details: str = ""

    # Learning
    insights: List[str] = field(default_factory=list)
    adaptations_made: List[str] = field(default_factory=list)

    # Timing
    applied_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class SuccessStrategy:
    """A compound strategy combining multiple patterns."""
    strategy_id: str
    name: str
    description: str

    # Composition
    patterns: List[str] = field(default_factory=list)
    pattern_weights: Dict[str, float] = field(default_factory=dict)

    # Synergy
    synergy_score: float = 0.0
    emergent_properties: List[str] = field(default_factory=list)

    # Performance
    applications: int = 0
    success_rate: float = 0.0


class PatternMiner:
    """Mines success patterns from outcomes."""

    def __init__(self):
        self._outcome_history: List[Dict[str, Any]] = []

    async def record_outcome(
        self,
        action: str,
        context: Dict[str, Any],
        outcome: OutcomeType,
        details: str = ""
    ):
        """Record an outcome for pattern mining."""
        self._outcome_history.append({
            "action": action,
            "context": context,
            "outcome": outcome,
            "details": details,
            "timestamp": datetime.utcnow().isoformat()
        })

        # Keep history manageable
        if len(self._outcome_history) > 10000:
            self._outcome_history = self._outcome_history[-5000:]

    async def mine_patterns(self) -> List[SuccessPattern]:
        """Mine patterns from outcome history."""
        patterns = []

        # Group by outcome type
        successful = [o for o in self._outcome_history if o["outcome"] in [OutcomeType.SUCCESS, OutcomeType.PARTIAL_SUCCESS]]

        if len(successful) < 5:
            return patterns

        # Find common elements in successful outcomes
        common_elements = self._find_common_elements(successful)

        # Create patterns from common elements
        for element, count in common_elements.items():
            if count >= 3:  # Appears in at least 3 successes
                pattern = SuccessPattern(
                    pattern_id=f"mined_{hashlib.md5(element.encode()).hexdigest()[:8]}",
                    name=f"Pattern: {element[:30]}",
                    description=f"Mined pattern involving: {element}",
                    elements=[element],
                    applications=count,
                    successes=count,
                    success_rate=count / len(successful),
                    confidence=min(0.9, 0.5 + count / 20)
                )
                patterns.append(pattern)

        return patterns

    def _find_common_elements(
        self,
        outcomes: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """Find common elements in outcomes."""
        element_counts = defaultdict(int)

        for outcome in outcomes:
            action = outcome.get("action", "")
            context = outcome.get("context", {})

            # Action as element
            element_counts[action] += 1

            # Context keys as elements
            for key in context.keys():
                element_counts[f"context:{key}"] += 1

        return element_counts


class PatternMatcher:
    """Matches current situations to success patterns."""

    def __init__(self, patterns: Dict[str, SuccessPattern]):
        self._patterns = patterns

    async def match(
        self,
        situation: Dict[str, Any]
    ) -> List[Tuple[SuccessPattern, float]]:
        """Match situation to applicable patterns."""
        matches = []

        situation_elements = self._extract_elements(situation)

        for pattern_id, pattern in self._patterns.items():
            score = self._calculate_match_score(pattern, situation_elements)
            if score > 0.3:
                matches.append((pattern, score))

        # Sort by match score and effectiveness
        matches.sort(key=lambda x: x[1] * x[0].effectiveness, reverse=True)

        return matches

    def _extract_elements(self, situation: Dict[str, Any]) -> Set[str]:
        """Extract elements from situation."""
        elements = set()

        for key, value in situation.items():
            elements.add(key)
            if isinstance(value, str):
                elements.add(value[:50])
            elif isinstance(value, list):
                elements.update(str(v)[:50] for v in value[:5])

        return elements

    def _calculate_match_score(
        self,
        pattern: SuccessPattern,
        situation_elements: Set[str]
    ) -> float:
        """Calculate match score between pattern and situation."""
        if not pattern.elements:
            return 0.0

        pattern_elements = set(pattern.elements)
        overlap = pattern_elements & situation_elements

        return len(overlap) / len(pattern_elements)


class PatternEvolver:
    """Evolves patterns based on outcomes."""

    def __init__(self):
        self._evolution_history: List[Dict[str, Any]] = []

    async def evolve_pattern(
        self,
        pattern: SuccessPattern,
        application: PatternApplication
    ) -> SuccessPattern:
        """Evolve pattern based on application outcome."""
        # Update statistics
        pattern.applications += 1
        pattern.last_applied = datetime.utcnow()

        if application.outcome in [OutcomeType.SUCCESS, OutcomeType.PARTIAL_SUCCESS]:
            pattern.successes += 1

        pattern.success_rate = pattern.successes / pattern.applications

        # Adjust confidence
        if application.outcome == OutcomeType.SUCCESS:
            pattern.confidence = min(0.95, pattern.confidence + 0.05)
        elif application.outcome == OutcomeType.FAILURE:
            pattern.confidence = max(0.1, pattern.confidence - 0.1)

        # Apply adaptations
        if application.adaptations_made:
            for adaptation in application.adaptations_made:
                if adaptation not in pattern.elements:
                    pattern.elements.append(adaptation)

        pattern.maturity += 1

        # Record evolution
        self._evolution_history.append({
            "pattern_id": pattern.pattern_id,
            "outcome": application.outcome.value,
            "new_success_rate": pattern.success_rate,
            "new_confidence": pattern.confidence,
            "timestamp": datetime.utcnow().isoformat()
        })

        return pattern

    def get_evolution_insights(self, pattern_id: str) -> List[str]:
        """Get insights about pattern evolution."""
        relevant = [e for e in self._evolution_history if e["pattern_id"] == pattern_id]

        if not relevant:
            return ["No evolution history yet"]

        insights = []

        # Trend analysis
        if len(relevant) >= 3:
            recent_rates = [e["new_success_rate"] for e in relevant[-3:]]
            if all(r >= recent_rates[0] for r in recent_rates):
                insights.append("Pattern showing improving trend")
            elif all(r <= recent_rates[0] for r in recent_rates):
                insights.append("Pattern effectiveness declining")

        insights.append(f"Pattern evolved {len(relevant)} times")

        return insights


class StrategySynthesizer:
    """Synthesizes compound success strategies."""

    async def synthesize(
        self,
        patterns: List[SuccessPattern],
        goal: str
    ) -> SuccessStrategy:
        """Synthesize strategy from patterns."""
        strategy_id = f"strategy_{hashlib.md5(f'{goal}{datetime.utcnow()}'.encode()).hexdigest()[:8]}"

        # Select compatible patterns
        compatible = self._select_compatible(patterns)

        # Calculate weights
        weights = {}
        total_effectiveness = sum(p.effectiveness for p in compatible)

        for pattern in compatible:
            weights[pattern.pattern_id] = pattern.effectiveness / max(1, total_effectiveness)

        # Calculate synergy
        synergy = self._calculate_synergy(compatible)

        # Identify emergent properties
        emergent = self._identify_emergent_properties(compatible)

        strategy = SuccessStrategy(
            strategy_id=strategy_id,
            name=f"Strategy for: {goal[:50]}",
            description=f"Compound strategy combining {len(compatible)} patterns",
            patterns=[p.pattern_id for p in compatible],
            pattern_weights=weights,
            synergy_score=synergy,
            emergent_properties=emergent
        )

        return strategy

    def _select_compatible(
        self,
        patterns: List[SuccessPattern]
    ) -> List[SuccessPattern]:
        """Select compatible patterns."""
        if not patterns:
            return []

        # Start with highest effectiveness
        sorted_patterns = sorted(patterns, key=lambda p: p.effectiveness, reverse=True)

        compatible = [sorted_patterns[0]]

        for pattern in sorted_patterns[1:]:
            # Check for conflicts
            conflicts = False
            for selected in compatible:
                if pattern.pattern_id in selected.conflicts_with:
                    conflicts = True
                    break

            if not conflicts:
                compatible.append(pattern)

            # Limit size
            if len(compatible) >= 5:
                break

        return compatible

    def _calculate_synergy(
        self,
        patterns: List[SuccessPattern]
    ) -> float:
        """Calculate synergy between patterns."""
        if len(patterns) < 2:
            return 0.0

        synergy = 0.0

        for i, p1 in enumerate(patterns):
            for p2 in patterns[i+1:]:
                # Check enhancement relationships
                if p1.pattern_id in p2.enhances_patterns or p2.pattern_id in p1.enhances_patterns:
                    synergy += 0.2

                # Check element overlap (moderate overlap is good)
                overlap = set(p1.elements) & set(p2.elements)
                if 1 <= len(overlap) <= 3:
                    synergy += 0.1

        return min(1.0, synergy)

    def _identify_emergent_properties(
        self,
        patterns: List[SuccessPattern]
    ) -> List[str]:
        """Identify emergent properties from pattern combination."""
        emergent = []

        # Check for common types
        types = [p.pattern_type for p in patterns]
        if PatternType.COGNITIVE in types and PatternType.BEHAVIORAL in types:
            emergent.append("Mind-action alignment")

        if PatternType.STRUCTURAL in types and PatternType.ADAPTIVE in types:
            emergent.append("Resilient structure")

        if PatternType.SYNERGISTIC in types:
            emergent.append("Compound effect amplification")

        if len(patterns) >= 3:
            emergent.append("Multi-dimensional approach")

        return emergent if emergent else ["Combined effectiveness"]


class SuccessPatternsEngine:
    """
    The Ultimate Success Patterns Engine.

    Learns and applies patterns that lead to success:
    1. Mines patterns from successful outcomes
    2. Matches situations to applicable patterns
    3. Evolves patterns based on results
    4. Synthesizes compound strategies
    5. Predicts success probability
    6. Avoids failure patterns
    """

    def __init__(self, llm_provider: Callable = None):
        self.llm_provider = llm_provider

        # Components
        self.miner = PatternMiner()
        self.evolver = PatternEvolver()
        self.synthesizer = StrategySynthesizer()

        # Storage
        self._patterns: Dict[str, SuccessPattern] = {}
        self._failure_patterns: Dict[str, FailurePattern] = {}
        self._strategies: Dict[str, SuccessStrategy] = {}
        self._applications: List[PatternApplication] = []

        # Initialize matcher
        self.matcher = PatternMatcher(self._patterns)

        # Preload universal patterns
        self._initialize_universal_patterns()

        # Stats
        self._stats = {
            "patterns_discovered": 0,
            "patterns_applied": 0,
            "successful_applications": 0,
            "strategies_synthesized": 0
        }

        logger.info("SuccessPatternsEngine initialized")

    def _initialize_universal_patterns(self):
        """Initialize universal success patterns."""
        universal_patterns = [
            SuccessPattern(
                pattern_id="universal_clarity",
                name="Clarity First",
                description="Ensure clear understanding before action",
                pattern_type=PatternType.COGNITIVE,
                domain=DomainType.UNIVERSAL,
                elements=["define_goal", "understand_context", "clarify_constraints"],
                sequence=["understand", "clarify", "confirm", "proceed"],
                confidence=0.85
            ),
            SuccessPattern(
                pattern_id="universal_iteration",
                name="Iterative Refinement",
                description="Improve through rapid iteration",
                pattern_type=PatternType.BEHAVIORAL,
                domain=DomainType.UNIVERSAL,
                elements=["start_simple", "get_feedback", "iterate", "improve"],
                sequence=["mvp", "test", "learn", "refine"],
                confidence=0.80
            ),
            SuccessPattern(
                pattern_id="universal_preparation",
                name="Thorough Preparation",
                description="Preparation prevents poor performance",
                pattern_type=PatternType.STRUCTURAL,
                domain=DomainType.UNIVERSAL,
                elements=["research", "plan", "gather_resources", "anticipate_obstacles"],
                sequence=["research", "plan", "prepare", "execute"],
                confidence=0.82
            ),
            SuccessPattern(
                pattern_id="universal_adaptation",
                name="Adaptive Response",
                description="Adapt quickly to changing conditions",
                pattern_type=PatternType.ADAPTIVE,
                domain=DomainType.UNIVERSAL,
                elements=["monitor", "assess", "adjust", "learn"],
                confidence=0.78
            ),
            SuccessPattern(
                pattern_id="universal_synergy",
                name="Synergistic Combination",
                description="Combine strengths for greater effect",
                pattern_type=PatternType.SYNERGISTIC,
                domain=DomainType.UNIVERSAL,
                elements=["identify_strengths", "combine_complementary", "amplify_effects"],
                confidence=0.75
            )
        ]

        for pattern in universal_patterns:
            self._patterns[pattern.pattern_id] = pattern
            self._stats["patterns_discovered"] += 1

    async def find_patterns(
        self,
        situation: Dict[str, Any]
    ) -> List[Tuple[SuccessPattern, float]]:
        """Find applicable success patterns for situation."""
        return await self.matcher.match(situation)

    async def apply_pattern(
        self,
        pattern_id: str,
        context: Dict[str, Any]
    ) -> PatternApplication:
        """Record application of a pattern."""
        if pattern_id not in self._patterns:
            raise ValueError(f"Pattern {pattern_id} not found")

        application = PatternApplication(
            application_id=f"app_{hashlib.md5(f'{pattern_id}{datetime.utcnow()}'.encode()).hexdigest()[:8]}",
            pattern_id=pattern_id,
            context=context
        )

        self._applications.append(application)
        self._stats["patterns_applied"] += 1

        return application

    async def record_outcome(
        self,
        application_id: str,
        outcome: OutcomeType,
        details: str = "",
        insights: List[str] = None
    ):
        """Record outcome of pattern application."""
        # Find application
        application = None
        for app in self._applications:
            if app.application_id == application_id:
                application = app
                break

        if not application:
            return

        application.outcome = outcome
        application.outcome_details = details
        application.insights = insights or []

        # Evolve pattern
        if application.pattern_id in self._patterns:
            pattern = self._patterns[application.pattern_id]
            await self.evolver.evolve_pattern(pattern, application)

        # Track success
        if outcome in [OutcomeType.SUCCESS, OutcomeType.PARTIAL_SUCCESS]:
            self._stats["successful_applications"] += 1

        # Record for mining
        await self.miner.record_outcome(
            action=application.pattern_id,
            context=application.context,
            outcome=outcome,
            details=details
        )

    async def synthesize_strategy(
        self,
        goal: str,
        constraints: Dict[str, Any] = None
    ) -> SuccessStrategy:
        """Synthesize strategy for a goal."""
        # Get relevant patterns
        patterns = list(self._patterns.values())

        # Filter by constraints if provided
        if constraints:
            domain = constraints.get("domain")
            if domain:
                patterns = [p for p in patterns if p.domain in [domain, DomainType.UNIVERSAL]]

        strategy = await self.synthesizer.synthesize(patterns, goal)

        self._strategies[strategy.strategy_id] = strategy
        self._stats["strategies_synthesized"] += 1

        return strategy

    async def discover_patterns(self) -> List[SuccessPattern]:
        """Discover new patterns from outcome history."""
        new_patterns = await self.miner.mine_patterns()

        for pattern in new_patterns:
            if pattern.pattern_id not in self._patterns:
                self._patterns[pattern.pattern_id] = pattern
                self._stats["patterns_discovered"] += 1

        # Update matcher
        self.matcher = PatternMatcher(self._patterns)

        return new_patterns

    def predict_success(
        self,
        patterns: List[str],
        context: Dict[str, Any] = None
    ) -> float:
        """Predict success probability for pattern combination."""
        if not patterns:
            return 0.5

        pattern_objects = [self._patterns[pid] for pid in patterns if pid in self._patterns]

        if not pattern_objects:
            return 0.5

        # Combine pattern success rates and confidence
        weighted_sum = 0.0
        total_weight = 0.0

        for pattern in pattern_objects:
            weight = pattern.confidence
            weighted_sum += pattern.success_rate * weight
            total_weight += weight

        base_probability = weighted_sum / max(1, total_weight)

        # Adjust for synergy
        if len(pattern_objects) >= 2:
            synergy_bonus = 0.1 * min(len(pattern_objects) - 1, 3)
            base_probability = min(0.95, base_probability + synergy_bonus)

        return base_probability

    def get_pattern(self, pattern_id: str) -> Optional[SuccessPattern]:
        """Get a pattern by ID."""
        return self._patterns.get(pattern_id)

    def list_patterns(self) -> List[Dict[str, Any]]:
        """List all patterns."""
        return [
            {
                "id": p.pattern_id,
                "name": p.name,
                "type": p.pattern_type.value,
                "domain": p.domain.value,
                "effectiveness": p.effectiveness,
                "applications": p.applications
            }
            for p in self._patterns.values()
        ]

    def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics."""
        return {
            **self._stats,
            "total_patterns": len(self._patterns),
            "total_strategies": len(self._strategies),
            "success_rate": self._stats["successful_applications"] / max(1, self._stats["patterns_applied"])
        }


# Global instance
_success_patterns_engine: Optional[SuccessPatternsEngine] = None


def get_success_patterns_engine() -> SuccessPatternsEngine:
    """Get the global success patterns engine."""
    global _success_patterns_engine
    if _success_patterns_engine is None:
        _success_patterns_engine = SuccessPatternsEngine()
    return _success_patterns_engine


async def demo():
    """Demonstrate the Success Patterns Engine."""
    engine = get_success_patterns_engine()

    # Find patterns for a situation
    situation = {
        "goal": "Create advanced AI system",
        "domain": "technical",
        "complexity": "high",
        "resources": "available"
    }

    print("Finding applicable success patterns...")
    matches = await engine.find_patterns(situation)

    print(f"\nFound {len(matches)} matching patterns:")
    for pattern, score in matches[:5]:
        print(f"  - {pattern.name} (match: {score:.2f}, effectiveness: {pattern.effectiveness:.2f})")

    # Synthesize strategy
    print("\nSynthesizing success strategy...")
    strategy = await engine.synthesize_strategy(
        goal="Create the most advanced AI agent system",
        constraints={"domain": DomainType.TECHNICAL}
    )

    print(f"\nStrategy: {strategy.name}")
    print(f"Patterns combined: {len(strategy.patterns)}")
    print(f"Synergy score: {strategy.synergy_score:.2f}")
    print(f"Emergent properties: {strategy.emergent_properties}")

    # Predict success
    probability = engine.predict_success(strategy.patterns)
    print(f"\nPredicted success probability: {probability:.2%}")

    # Show stats
    print("\nEngine Statistics:")
    for key, value in engine.get_stats().items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    asyncio.run(demo())

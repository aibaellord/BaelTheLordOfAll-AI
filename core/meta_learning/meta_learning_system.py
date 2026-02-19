#!/usr/bin/env python3
"""
BAEL - Meta Learning System
LEARNING HOW TO LEARN

This system enables BAEL to:
1. Learn from every interaction
2. Optimize its own learning process
3. Transfer knowledge across domains
4. Identify learning patterns
5. Self-improve continuously
6. Adapt strategies based on results

"The master learns not just the skill, but the art of learning itself." - Ba'el
"""

import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from uuid import uuid4
import hashlib
import json
import math
import random

logger = logging.getLogger("BAEL.MetaLearning")


# =============================================================================
# ENUMS
# =============================================================================

class LearningStrategy(Enum):
    """Learning strategies."""
    SUPERVISED = "supervised"       # Learn from examples
    REINFORCEMENT = "reinforcement" # Learn from rewards
    TRANSFER = "transfer"           # Apply across domains
    CURRICULUM = "curriculum"       # Structured progression
    ACTIVE = "active"               # Request what to learn
    SELF_SUPERVISED = "self_supervised"  # Create own labels
    META = "meta"                   # Learn to learn
    ADVERSARIAL = "adversarial"     # Learn from failures


class KnowledgeType(Enum):
    """Types of knowledge."""
    DECLARATIVE = "declarative"     # Facts and information
    PROCEDURAL = "procedural"       # How to do things
    CONDITIONAL = "conditional"     # When to apply
    METACOGNITIVE = "metacognitive" # About learning itself


class AdaptationSpeed(Enum):
    """How quickly to adapt."""
    INSTANT = 1.0
    FAST = 0.7
    MODERATE = 0.5
    SLOW = 0.3
    GLACIAL = 0.1


class LearningOutcome(Enum):
    """Outcomes of learning attempts."""
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class LearningExperience:
    """A single learning experience."""
    id: str = field(default_factory=lambda: str(uuid4()))

    # What was learned
    knowledge_type: KnowledgeType = KnowledgeType.DECLARATIVE
    domain: str = ""
    content: str = ""

    # Context
    strategy_used: LearningStrategy = LearningStrategy.SUPERVISED
    context: Dict[str, Any] = field(default_factory=dict)

    # Outcome
    outcome: LearningOutcome = LearningOutcome.UNKNOWN
    reward: float = 0.0  # -1 to 1

    # Meta-information
    difficulty: float = 0.5
    time_spent_ms: int = 0
    attempts: int = 1

    # Timing
    learned_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class LearningPattern:
    """A detected pattern in learning."""
    id: str = field(default_factory=lambda: str(uuid4()))

    # Pattern details
    name: str = ""
    description: str = ""

    # Conditions
    domain_pattern: str = ""
    context_conditions: Dict[str, Any] = field(default_factory=dict)

    # Recommendation
    best_strategy: LearningStrategy = LearningStrategy.SUPERVISED
    expected_difficulty: float = 0.5

    # Evidence
    supporting_experiences: int = 0
    success_rate: float = 0.0

    # Meta
    discovered_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class SkillLevel:
    """Level of skill in a domain."""
    domain: str = ""
    level: float = 0.0  # 0-1 scale
    experiences: int = 0
    last_practiced: Optional[datetime] = None
    decay_rate: float = 0.01  # How fast skill decays

    def apply_decay(self) -> None:
        """Apply time-based decay."""
        if self.last_practiced:
            days = (datetime.utcnow() - self.last_practiced).days
            self.level *= math.exp(-self.decay_rate * days)


@dataclass
class LearningGoal:
    """A learning goal."""
    id: str = field(default_factory=lambda: str(uuid4()))

    # Goal
    domain: str = ""
    target_level: float = 0.8
    description: str = ""

    # Progress
    current_level: float = 0.0
    experiences_needed: int = 10
    experiences_completed: int = 0

    # Status
    active: bool = True
    completed: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)


# =============================================================================
# LEARNING MODULES
# =============================================================================

class ExperienceBank:
    """Stores and retrieves learning experiences."""

    def __init__(self, max_experiences: int = 10000):
        self.experiences: Dict[str, LearningExperience] = {}
        self.by_domain: Dict[str, List[str]] = defaultdict(list)
        self.by_strategy: Dict[LearningStrategy, List[str]] = defaultdict(list)
        self.max_experiences = max_experiences

    def add(self, experience: LearningExperience) -> None:
        """Add an experience."""
        self.experiences[experience.id] = experience
        self.by_domain[experience.domain].append(experience.id)
        self.by_strategy[experience.strategy_used].append(experience.id)

        # Prune if needed
        if len(self.experiences) > self.max_experiences:
            self._prune_old()

    def _prune_old(self) -> None:
        """Remove oldest experiences."""
        sorted_exp = sorted(
            self.experiences.values(),
            key=lambda x: x.learned_at
        )

        to_remove = sorted_exp[:len(sorted_exp) // 10]
        for exp in to_remove:
            self._remove(exp)

    def _remove(self, exp: LearningExperience) -> None:
        """Remove an experience."""
        del self.experiences[exp.id]
        if exp.id in self.by_domain[exp.domain]:
            self.by_domain[exp.domain].remove(exp.id)
        if exp.id in self.by_strategy[exp.strategy_used]:
            self.by_strategy[exp.strategy_used].remove(exp.id)

    def get_by_domain(self, domain: str) -> List[LearningExperience]:
        """Get experiences for a domain."""
        ids = self.by_domain.get(domain, [])
        return [self.experiences[id] for id in ids if id in self.experiences]

    def get_by_strategy(self, strategy: LearningStrategy) -> List[LearningExperience]:
        """Get experiences for a strategy."""
        ids = self.by_strategy.get(strategy, [])
        return [self.experiences[id] for id in ids if id in self.experiences]

    def get_successful(self, domain: str = None) -> List[LearningExperience]:
        """Get successful experiences."""
        exps = self.experiences.values()
        if domain:
            exps = [e for e in exps if e.domain == domain]
        return [e for e in exps if e.outcome == LearningOutcome.SUCCESS]


class PatternDetector:
    """Detects patterns in learning experiences."""

    def __init__(self, bank: ExperienceBank):
        self.bank = bank
        self.patterns: Dict[str, LearningPattern] = {}

    async def detect_patterns(self) -> List[LearningPattern]:
        """Detect patterns from experiences."""
        new_patterns = []

        # Analyze by domain
        domain_patterns = await self._analyze_domains()
        new_patterns.extend(domain_patterns)

        # Analyze by strategy
        strategy_patterns = await self._analyze_strategies()
        new_patterns.extend(strategy_patterns)

        # Store patterns
        for p in new_patterns:
            self.patterns[p.id] = p

        return new_patterns

    async def _analyze_domains(self) -> List[LearningPattern]:
        """Analyze domain-specific patterns."""
        patterns = []

        for domain, exp_ids in self.bank.by_domain.items():
            if len(exp_ids) < 3:
                continue

            exps = [self.bank.experiences[id] for id in exp_ids if id in self.bank.experiences]

            # Calculate stats
            success_count = sum(1 for e in exps if e.outcome == LearningOutcome.SUCCESS)
            success_rate = success_count / len(exps) if exps else 0

            # Find best strategy for this domain
            strategy_success = defaultdict(list)
            for e in exps:
                strategy_success[e.strategy_used].append(e.outcome == LearningOutcome.SUCCESS)

            best_strategy = max(
                strategy_success.keys(),
                key=lambda s: sum(strategy_success[s]) / len(strategy_success[s])
                if strategy_success[s] else 0,
                default=LearningStrategy.SUPERVISED
            )

            pattern = LearningPattern(
                name=f"Domain pattern: {domain}",
                description=f"Learning pattern for {domain}",
                domain_pattern=domain,
                best_strategy=best_strategy,
                expected_difficulty=sum(e.difficulty for e in exps) / len(exps),
                supporting_experiences=len(exps),
                success_rate=success_rate
            )
            patterns.append(pattern)

        return patterns

    async def _analyze_strategies(self) -> List[LearningPattern]:
        """Analyze strategy effectiveness."""
        patterns = []

        for strategy, exp_ids in self.bank.by_strategy.items():
            if len(exp_ids) < 3:
                continue

            exps = [self.bank.experiences[id] for id in exp_ids if id in self.bank.experiences]

            success_count = sum(1 for e in exps if e.outcome == LearningOutcome.SUCCESS)
            success_rate = success_count / len(exps) if exps else 0

            pattern = LearningPattern(
                name=f"Strategy pattern: {strategy.value}",
                description=f"Effectiveness of {strategy.value} strategy",
                best_strategy=strategy,
                supporting_experiences=len(exps),
                success_rate=success_rate
            )
            patterns.append(pattern)

        return patterns


class StrategyOptimizer:
    """Optimizes learning strategy selection."""

    def __init__(self, detector: PatternDetector):
        self.detector = detector

        # Strategy weights (learnable)
        self.strategy_weights: Dict[str, Dict[LearningStrategy, float]] = defaultdict(
            lambda: {s: 1.0 for s in LearningStrategy}
        )

        # Exploration rate
        self.exploration_rate = 0.2

    def select_strategy(
        self,
        domain: str,
        context: Dict[str, Any] = None
    ) -> LearningStrategy:
        """Select the best learning strategy."""

        # Check for known pattern
        for pattern in self.detector.patterns.values():
            if pattern.domain_pattern == domain:
                if random.random() > self.exploration_rate:
                    return pattern.best_strategy

        # Use weighted selection
        weights = self.strategy_weights[domain]
        total = sum(weights.values())

        if total == 0:
            return random.choice(list(LearningStrategy))

        # Softmax selection
        r = random.random() * total
        cumulative = 0
        for strategy, weight in weights.items():
            cumulative += weight
            if r <= cumulative:
                return strategy

        return LearningStrategy.SUPERVISED

    def update_weights(
        self,
        domain: str,
        strategy: LearningStrategy,
        reward: float,
        learning_rate: float = 0.1
    ) -> None:
        """Update strategy weights based on outcome."""
        current = self.strategy_weights[domain][strategy]
        self.strategy_weights[domain][strategy] = current + learning_rate * reward


class KnowledgeTransfer:
    """Handles transfer learning across domains."""

    def __init__(self, bank: ExperienceBank):
        self.bank = bank
        self.domain_similarity: Dict[Tuple[str, str], float] = {}

    def calculate_similarity(self, domain1: str, domain2: str) -> float:
        """Calculate similarity between domains."""
        key = tuple(sorted([domain1, domain2]))

        if key in self.domain_similarity:
            return self.domain_similarity[key]

        # Calculate based on shared successful strategies
        exp1 = self.bank.get_by_domain(domain1)
        exp2 = self.bank.get_by_domain(domain2)

        if not exp1 or not exp2:
            return 0.0

        strategies1 = set(e.strategy_used for e in exp1 if e.outcome == LearningOutcome.SUCCESS)
        strategies2 = set(e.strategy_used for e in exp2 if e.outcome == LearningOutcome.SUCCESS)

        if not strategies1 or not strategies2:
            return 0.0

        overlap = len(strategies1 & strategies2)
        total = len(strategies1 | strategies2)

        similarity = overlap / total if total > 0 else 0.0
        self.domain_similarity[key] = similarity

        return similarity

    def get_transferable_knowledge(
        self,
        target_domain: str,
        min_similarity: float = 0.3
    ) -> List[Tuple[str, float, List[LearningExperience]]]:
        """Get knowledge from similar domains."""
        results = []

        for domain in self.bank.by_domain.keys():
            if domain == target_domain:
                continue

            similarity = self.calculate_similarity(domain, target_domain)

            if similarity >= min_similarity:
                experiences = self.bank.get_successful(domain)
                if experiences:
                    results.append((domain, similarity, experiences))

        # Sort by similarity
        results.sort(key=lambda x: x[1], reverse=True)
        return results


# =============================================================================
# META LEARNING SYSTEM
# =============================================================================

class MetaLearningSystem:
    """
    The Meta Learning System.

    Learns how to learn more effectively.
    """

    def __init__(self):
        self.experience_bank = ExperienceBank()
        self.pattern_detector = PatternDetector(self.experience_bank)
        self.strategy_optimizer = StrategyOptimizer(self.pattern_detector)
        self.knowledge_transfer = KnowledgeTransfer(self.experience_bank)

        # Skill tracking
        self.skills: Dict[str, SkillLevel] = {}

        # Goals
        self.goals: Dict[str, LearningGoal] = {}

        # Meta-metrics
        self._total_experiences = 0
        self._success_rate = 0.0
        self._adaptation_count = 0

        logger.info("MetaLearningSystem initialized")

    async def learn(
        self,
        domain: str,
        content: str,
        knowledge_type: KnowledgeType = KnowledgeType.DECLARATIVE,
        context: Dict[str, Any] = None
    ) -> LearningExperience:
        """Learn something new."""

        # Select strategy
        strategy = self.strategy_optimizer.select_strategy(domain, context)

        # Create experience
        experience = LearningExperience(
            knowledge_type=knowledge_type,
            domain=domain,
            content=content,
            strategy_used=strategy,
            context=context or {}
        )

        # Simulate learning process
        experience = await self._process_learning(experience)

        # Store experience
        self.experience_bank.add(experience)

        # Update strategy weights
        self.strategy_optimizer.update_weights(
            domain,
            strategy,
            experience.reward
        )

        # Update skill level
        self._update_skill(domain, experience)

        # Update goals
        self._update_goals(domain, experience)

        # Update metrics
        self._total_experiences += 1
        self._update_success_rate(experience)

        logger.debug(f"Learned in {domain}: {experience.outcome.value}")

        return experience

    async def _process_learning(
        self,
        experience: LearningExperience
    ) -> LearningExperience:
        """Process a learning experience."""
        import time
        start = time.time()

        # Apply strategy-specific processing
        if experience.strategy_used == LearningStrategy.TRANSFER:
            # Check for transferable knowledge
            transfers = self.knowledge_transfer.get_transferable_knowledge(
                experience.domain
            )
            if transfers:
                experience.difficulty *= 0.7  # Easier with transfer

        elif experience.strategy_used == LearningStrategy.CURRICULUM:
            # Apply curriculum learning
            skill = self.skills.get(experience.domain)
            if skill:
                experience.difficulty = max(0.1, 1.0 - skill.level)

        # Simulate outcome based on difficulty and skill
        skill_level = self.skills.get(experience.domain, SkillLevel(domain=experience.domain)).level
        success_prob = (1.0 - experience.difficulty) * 0.7 + skill_level * 0.3

        if random.random() < success_prob:
            experience.outcome = LearningOutcome.SUCCESS
            experience.reward = 0.5 + random.random() * 0.5
        elif random.random() < 0.3:
            experience.outcome = LearningOutcome.PARTIAL
            experience.reward = random.random() * 0.3
        else:
            experience.outcome = LearningOutcome.FAILURE
            experience.reward = -0.3 + random.random() * 0.2

        experience.time_spent_ms = int((time.time() - start) * 1000) + random.randint(100, 1000)

        return experience

    def _update_skill(self, domain: str, experience: LearningExperience) -> None:
        """Update skill level based on experience."""
        if domain not in self.skills:
            self.skills[domain] = SkillLevel(domain=domain)

        skill = self.skills[domain]

        # Apply decay first
        skill.apply_decay()

        # Update based on outcome
        if experience.outcome == LearningOutcome.SUCCESS:
            # Increase skill
            improvement = 0.1 * (1.0 - skill.level)  # Diminishing returns
            skill.level = min(1.0, skill.level + improvement)
        elif experience.outcome == LearningOutcome.FAILURE:
            # Small decrease (learning from failure)
            skill.level = max(0.0, skill.level - 0.01)

        skill.experiences += 1
        skill.last_practiced = datetime.utcnow()

    def _update_goals(self, domain: str, experience: LearningExperience) -> None:
        """Update learning goals."""
        for goal in self.goals.values():
            if goal.domain == domain and goal.active and not goal.completed:
                goal.experiences_completed += 1
                goal.current_level = self.skills.get(domain, SkillLevel()).level

                if goal.current_level >= goal.target_level:
                    goal.completed = True
                    goal.active = False

    def _update_success_rate(self, experience: LearningExperience) -> None:
        """Update overall success rate."""
        alpha = 0.1  # Smoothing factor
        success = 1.0 if experience.outcome == LearningOutcome.SUCCESS else 0.0
        self._success_rate = self._success_rate * (1 - alpha) + success * alpha

    async def optimize(self) -> Dict[str, Any]:
        """Optimize the learning system."""

        # Detect new patterns
        new_patterns = await self.pattern_detector.detect_patterns()

        # Adjust exploration rate based on success
        if self._success_rate > 0.8:
            self.strategy_optimizer.exploration_rate = max(
                0.05,
                self.strategy_optimizer.exploration_rate - 0.01
            )
        elif self._success_rate < 0.5:
            self.strategy_optimizer.exploration_rate = min(
                0.5,
                self.strategy_optimizer.exploration_rate + 0.01
            )

        self._adaptation_count += 1

        return {
            "new_patterns": len(new_patterns),
            "exploration_rate": self.strategy_optimizer.exploration_rate,
            "success_rate": self._success_rate,
            "adaptation_count": self._adaptation_count
        }

    def set_goal(
        self,
        domain: str,
        target_level: float = 0.8,
        description: str = ""
    ) -> LearningGoal:
        """Set a learning goal."""
        goal = LearningGoal(
            domain=domain,
            target_level=target_level,
            description=description or f"Master {domain}",
            current_level=self.skills.get(domain, SkillLevel()).level
        )

        self.goals[goal.id] = goal
        return goal

    def get_recommendations(self, domain: str = None) -> List[Dict[str, Any]]:
        """Get learning recommendations."""
        recommendations = []

        # Domain-specific recommendations
        if domain:
            # Best strategy for this domain
            for pattern in self.pattern_detector.patterns.values():
                if pattern.domain_pattern == domain:
                    recommendations.append({
                        "type": "strategy",
                        "domain": domain,
                        "recommendation": f"Use {pattern.best_strategy.value} strategy",
                        "confidence": pattern.success_rate
                    })

            # Transfer opportunities
            transfers = self.knowledge_transfer.get_transferable_knowledge(domain)
            for source, similarity, _ in transfers[:3]:
                recommendations.append({
                    "type": "transfer",
                    "from_domain": source,
                    "to_domain": domain,
                    "recommendation": f"Transfer knowledge from {source}",
                    "confidence": similarity
                })

        # General recommendations
        if self._success_rate < 0.5:
            recommendations.append({
                "type": "general",
                "recommendation": "Focus on fundamentals with supervised learning",
                "confidence": 0.7
            })

        # Skill decay warnings
        for skill in self.skills.values():
            skill.apply_decay()
            if skill.level < 0.3 and skill.experiences > 5:
                recommendations.append({
                    "type": "practice",
                    "domain": skill.domain,
                    "recommendation": f"Practice {skill.domain} to prevent skill decay",
                    "confidence": 0.8
                })

        return recommendations

    def get_stats(self) -> Dict[str, Any]:
        """Get learning statistics."""
        return {
            "total_experiences": self._total_experiences,
            "success_rate": self._success_rate,
            "adaptation_count": self._adaptation_count,
            "skills_count": len(self.skills),
            "patterns_count": len(self.pattern_detector.patterns),
            "active_goals": sum(1 for g in self.goals.values() if g.active),
            "completed_goals": sum(1 for g in self.goals.values() if g.completed),
            "exploration_rate": self.strategy_optimizer.exploration_rate
        }


# =============================================================================
# FACTORY
# =============================================================================

async def create_meta_learning_system() -> MetaLearningSystem:
    """Create a new Meta Learning System."""
    return MetaLearningSystem()


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    async def main():
        print("🧠 BAEL Meta Learning System")
        print("=" * 50)

        system = await create_meta_learning_system()

        # Set a learning goal
        goal = system.set_goal("python", target_level=0.8, description="Master Python")
        print(f"\n🎯 Goal set: {goal.description}")

        # Simulate learning
        domains = ["python", "javascript", "python", "algorithms", "python"]

        print("\n📚 Learning sessions:")
        for domain in domains:
            experience = await system.learn(
                domain=domain,
                content=f"Advanced {domain} concepts",
                knowledge_type=KnowledgeType.PROCEDURAL
            )
            print(f"  - {domain}: {experience.outcome.value} (reward: {experience.reward:.2f})")

        # Optimize
        print("\n⚙️ Optimizing...")
        optimization = await system.optimize()
        print(f"  New patterns: {optimization['new_patterns']}")
        print(f"  Success rate: {optimization['success_rate']:.2f}")

        # Get recommendations
        print("\n💡 Recommendations:")
        recs = system.get_recommendations("python")
        for rec in recs[:3]:
            print(f"  - {rec['recommendation']} ({rec['confidence']:.2f})")

        # Stats
        print("\n📊 Stats:")
        stats = system.get_stats()
        for key, value in stats.items():
            print(f"  {key}: {value}")

        print("\n✅ Meta learning system ready")

    asyncio.run(main())

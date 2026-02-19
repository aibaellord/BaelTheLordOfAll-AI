#!/usr/bin/env python3
"""
BAEL - Dream Mode Engine
CREATIVE EXPLORATION BEYOND CONSTRAINTS

This engine enables BAEL to enter "Dream Mode" - a creative state where:
1. Normal constraints are relaxed for exploration
2. Impossible ideas are entertained
3. Cross-domain connections are discovered
4. Emergent solutions arise from chaos
5. The subconscious patterns are revealed
6. Innovation emerges from randomness

"In dreams, we touch the infinite." - Ba'el
"""

import asyncio
import logging
import random
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from uuid import uuid4
import hashlib
import math

logger = logging.getLogger("BAEL.DreamMode")


# =============================================================================
# SACRED CONSTANTS
# =============================================================================

PHI = 1.618033988749895  # Golden Ratio
PHI_INVERSE = 0.618033988749895
FIBONACCI = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377, 610, 987]
SACRED_PRIMES = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47]


# =============================================================================
# ENUMS
# =============================================================================

class DreamState(Enum):
    """States of the dream engine."""
    AWAKE = "awake"           # Normal operation
    DROWSY = "drowsy"         # Transitioning to dream
    LIGHT_DREAM = "light"     # Light exploration
    DEEP_DREAM = "deep"       # Deep creative state
    REM = "rem"               # Most creative, random
    LUCID = "lucid"           # Aware and in control
    NIGHTMARE = "nightmare"   # Exploring negative paths
    TRANSCENDENT = "transcendent"  # Beyond categorization


class DreamTheme(Enum):
    """Themes for dream exploration."""
    CHAOS = "chaos"           # Pure randomness
    ORDER = "order"           # Finding patterns
    FUSION = "fusion"         # Combining concepts
    INVERSION = "inversion"   # Opposite approaches
    EXPANSION = "expansion"   # Scaling up
    REDUCTION = "reduction"   # Minimizing
    METAMORPHOSIS = "metamorphosis"  # Transformation
    RECURSION = "recursion"   # Self-reference
    EMERGENCE = "emergence"   # New from simple
    SACRED = "sacred"         # Golden ratio patterns


class InsightType(Enum):
    """Types of insights that can emerge."""
    CONNECTION = "connection"   # Link between concepts
    ANALOGY = "analogy"         # Cross-domain mapping
    INVERSION = "inversion"     # Opposite approach
    COMBINATION = "combination"  # New from existing
    SIMPLIFICATION = "simplification"  # Reduced complexity
    PATTERN = "pattern"         # Recurring structure
    QUESTION = "question"       # New question to explore
    PARADOX = "paradox"         # Contradiction revealing truth
    VISION = "vision"           # Future possibility


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class DreamFragment:
    """A fragment of a dream - a partial idea."""
    id: str = field(default_factory=lambda: str(uuid4()))

    # Content
    content: str = ""
    concepts: List[str] = field(default_factory=list)

    # Properties
    coherence: float = 0.5  # 0-1, how coherent
    novelty: float = 0.5    # 0-1, how novel
    relevance: float = 0.5  # 0-1, how relevant to goal

    # Source
    theme: DreamTheme = DreamTheme.CHAOS
    depth: int = 1

    # Relations
    parent_id: Optional[str] = None
    related_ids: List[str] = field(default_factory=list)


@dataclass
class DreamInsight:
    """An insight emerged from dreaming."""
    id: str = field(default_factory=lambda: str(uuid4()))

    # Insight
    insight_type: InsightType = InsightType.CONNECTION
    title: str = ""
    description: str = ""

    # Source
    source_fragments: List[str] = field(default_factory=list)
    dream_depth: int = 1

    # Assessment
    confidence: float = 0.5
    actionability: float = 0.5
    impact_potential: float = 0.5

    # Concrete application
    application: str = ""
    implementation_hints: List[str] = field(default_factory=list)

    # Timing
    emerged_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class DreamSequence:
    """A complete dream sequence."""
    id: str = field(default_factory=lambda: str(uuid4()))

    # Dream content
    seed: str = ""  # Starting concept
    theme: DreamTheme = DreamTheme.CHAOS
    fragments: List[DreamFragment] = field(default_factory=list)
    insights: List[DreamInsight] = field(default_factory=list)

    # State
    state: DreamState = DreamState.AWAKE
    depth: int = 0
    duration_seconds: int = 0

    # Assessment
    total_novelty: float = 0.0
    total_coherence: float = 0.0
    usable_insights: int = 0

    # Timing
    started_at: datetime = field(default_factory=datetime.utcnow)
    ended_at: Optional[datetime] = None


# =============================================================================
# DREAM GENERATORS
# =============================================================================

class FragmentGenerator:
    """Generates dream fragments."""

    def __init__(self):
        # Concept pools for random combination
        self.domains = [
            "nature", "technology", "art", "science", "philosophy",
            "mathematics", "biology", "physics", "psychology", "economics"
        ]

        self.actions = [
            "transforms", "connects", "inverts", "amplifies", "reduces",
            "mirrors", "splits", "merges", "oscillates", "transcends"
        ]

        self.qualities = [
            "fractal", "recursive", "emergent", "chaotic", "ordered",
            "infinite", "minimal", "dynamic", "static", "quantum"
        ]

    async def generate(
        self,
        seed: str,
        theme: DreamTheme,
        depth: int
    ) -> DreamFragment:
        """Generate a dream fragment."""

        if theme == DreamTheme.CHAOS:
            return await self._generate_chaotic(seed, depth)
        elif theme == DreamTheme.FUSION:
            return await self._generate_fusion(seed, depth)
        elif theme == DreamTheme.INVERSION:
            return await self._generate_inversion(seed, depth)
        elif theme == DreamTheme.SACRED:
            return await self._generate_sacred(seed, depth)
        else:
            return await self._generate_default(seed, theme, depth)

    async def _generate_chaotic(self, seed: str, depth: int) -> DreamFragment:
        """Generate a chaotic fragment."""
        domain = random.choice(self.domains)
        action = random.choice(self.actions)
        quality = random.choice(self.qualities)

        content = f"What if {seed} {action} like {quality} {domain}?"

        return DreamFragment(
            content=content,
            concepts=[seed, domain, action, quality],
            theme=DreamTheme.CHAOS,
            depth=depth,
            novelty=0.8,  # High novelty for chaos
            coherence=0.3,  # Low coherence
            relevance=0.4
        )

    async def _generate_fusion(self, seed: str, depth: int) -> DreamFragment:
        """Generate a fusion fragment."""
        domain1 = random.choice(self.domains)
        domain2 = random.choice([d for d in self.domains if d != domain1])

        content = f"Combine {seed} with {domain1} principles applied through {domain2} lens"

        return DreamFragment(
            content=content,
            concepts=[seed, domain1, domain2],
            theme=DreamTheme.FUSION,
            depth=depth,
            novelty=0.7,
            coherence=0.5,
            relevance=0.6
        )

    async def _generate_inversion(self, seed: str, depth: int) -> DreamFragment:
        """Generate an inversion fragment."""
        inversions = [
            f"What if {seed} was its own opposite?",
            f"What if we removed {seed} entirely?",
            f"What if {seed} worked in reverse?",
            f"What if {seed} was the problem, not the solution?",
            f"What if we made {seed} as bad as possible, then inverted?",
        ]

        content = random.choice(inversions)

        return DreamFragment(
            content=content,
            concepts=[seed, "inversion", "opposite"],
            theme=DreamTheme.INVERSION,
            depth=depth,
            novelty=0.6,
            coherence=0.6,
            relevance=0.5
        )

    async def _generate_sacred(self, seed: str, depth: int) -> DreamFragment:
        """Generate a sacred geometry inspired fragment."""
        fib = random.choice(FIBONACCI[:10])
        prime = random.choice(SACRED_PRIMES[:7])

        content = f"Apply golden ratio ({PHI:.3f}) to {seed}: divide into {fib} parts, select {prime} for focus"

        return DreamFragment(
            content=content,
            concepts=[seed, "golden_ratio", f"fibonacci_{fib}", f"prime_{prime}"],
            theme=DreamTheme.SACRED,
            depth=depth,
            novelty=0.5,
            coherence=0.8,  # Sacred patterns are coherent
            relevance=0.6
        )

    async def _generate_default(
        self,
        seed: str,
        theme: DreamTheme,
        depth: int
    ) -> DreamFragment:
        """Generate a default fragment."""
        quality = random.choice(self.qualities)

        content = f"Explore {seed} through {theme.value} with {quality} properties"

        return DreamFragment(
            content=content,
            concepts=[seed, theme.value, quality],
            theme=theme,
            depth=depth,
            novelty=0.5,
            coherence=0.5,
            relevance=0.5
        )


class InsightExtractor:
    """Extracts insights from dream fragments."""

    async def extract(
        self,
        fragments: List[DreamFragment],
        goal: str = ""
    ) -> List[DreamInsight]:
        """Extract insights from fragments."""
        insights = []

        # Look for connections
        connections = await self._find_connections(fragments)
        insights.extend(connections)

        # Look for patterns
        patterns = await self._find_patterns(fragments)
        insights.extend(patterns)

        # Look for actionable insights
        actions = await self._find_actionable(fragments, goal)
        insights.extend(actions)

        return insights

    async def _find_connections(
        self,
        fragments: List[DreamFragment]
    ) -> List[DreamInsight]:
        """Find connections between fragments."""
        insights = []

        # Group by concept overlap
        for i, f1 in enumerate(fragments):
            for f2 in fragments[i+1:]:
                overlap = set(f1.concepts) & set(f2.concepts)
                if overlap:
                    insight = DreamInsight(
                        insight_type=InsightType.CONNECTION,
                        title=f"Connection: {' + '.join(overlap)}",
                        description=f"Link between '{f1.content[:50]}' and '{f2.content[:50]}'",
                        source_fragments=[f1.id, f2.id],
                        confidence=0.6,
                        actionability=0.5
                    )
                    insights.append(insight)

        return insights[:5]  # Limit

    async def _find_patterns(
        self,
        fragments: List[DreamFragment]
    ) -> List[DreamInsight]:
        """Find recurring patterns."""
        insights = []

        # Count concept frequencies
        concept_counts = defaultdict(int)
        for f in fragments:
            for c in f.concepts:
                concept_counts[c] += 1

        # Find recurring concepts
        recurring = [c for c, count in concept_counts.items() if count >= 2]

        if recurring:
            insight = DreamInsight(
                insight_type=InsightType.PATTERN,
                title=f"Recurring pattern: {', '.join(recurring[:3])}",
                description=f"These concepts appear repeatedly, suggesting importance",
                confidence=0.7,
                actionability=0.4
            )
            insights.append(insight)

        return insights

    async def _find_actionable(
        self,
        fragments: List[DreamFragment],
        goal: str
    ) -> List[DreamInsight]:
        """Find actionable insights."""
        insights = []

        # Find high-relevance, high-coherence fragments
        actionable_fragments = [
            f for f in fragments
            if f.relevance > 0.5 and f.coherence > 0.4
        ]

        for f in actionable_fragments[:3]:
            insight = DreamInsight(
                insight_type=InsightType.COMBINATION,
                title=f"Actionable: {f.content[:40]}",
                description=f"This dream fragment could be applied: {f.content}",
                source_fragments=[f.id],
                confidence=f.coherence,
                actionability=0.7,
                application=f"Apply {f.theme.value} thinking to your problem"
            )
            insights.append(insight)

        return insights


# =============================================================================
# DREAM MODE ENGINE
# =============================================================================

class DreamModeEngine:
    """
    The Dream Mode Engine.

    Enables creative exploration beyond normal constraints.
    """

    def __init__(self):
        self.fragment_generator = FragmentGenerator()
        self.insight_extractor = InsightExtractor()

        self._state = DreamState.AWAKE
        self._current_sequence: Optional[DreamSequence] = None
        self._history: List[DreamSequence] = []

        logger.info("DreamModeEngine initialized")

    @property
    def state(self) -> DreamState:
        return self._state

    async def enter_dream(
        self,
        seed: str,
        theme: DreamTheme = DreamTheme.CHAOS,
        target_depth: int = 3
    ) -> DreamSequence:
        """Enter dream mode and explore."""

        logger.info(f"Entering dream mode: seed='{seed}', theme={theme.value}")

        # Create sequence
        self._current_sequence = DreamSequence(
            seed=seed,
            theme=theme,
            state=DreamState.DROWSY
        )

        # Transition through states
        for depth in range(1, target_depth + 1):
            # Update state based on depth
            self._state = self._get_state_for_depth(depth, target_depth)
            self._current_sequence.state = self._state
            self._current_sequence.depth = depth

            # Generate fragments
            num_fragments = FIBONACCI[min(depth + 2, len(FIBONACCI) - 1)]

            for _ in range(num_fragments):
                fragment = await self.fragment_generator.generate(
                    seed=seed,
                    theme=theme,
                    depth=depth
                )
                self._current_sequence.fragments.append(fragment)

                # Sometimes mutate the seed for next iteration
                if random.random() < 0.3:
                    seed = random.choice(fragment.concepts)

        # Extract insights
        insights = await self.insight_extractor.extract(
            self._current_sequence.fragments,
            goal=seed
        )
        self._current_sequence.insights = insights

        # Calculate summary stats
        self._calculate_sequence_stats()

        # End dream
        self._current_sequence.ended_at = datetime.utcnow()
        self._current_sequence.duration_seconds = int(
            (self._current_sequence.ended_at - self._current_sequence.started_at).total_seconds()
        )

        # Store in history
        self._history.append(self._current_sequence)

        # Return to awake
        self._state = DreamState.AWAKE

        logger.info(f"Dream complete: {len(self._current_sequence.fragments)} fragments, {len(insights)} insights")

        return self._current_sequence

    def _get_state_for_depth(self, depth: int, max_depth: int) -> DreamState:
        """Determine dream state based on depth."""
        ratio = depth / max_depth

        if ratio < 0.2:
            return DreamState.DROWSY
        elif ratio < 0.4:
            return DreamState.LIGHT_DREAM
        elif ratio < 0.6:
            return DreamState.DEEP_DREAM
        elif ratio < 0.8:
            return DreamState.REM
        else:
            return DreamState.LUCID

    def _calculate_sequence_stats(self) -> None:
        """Calculate summary statistics for the sequence."""
        if not self._current_sequence or not self._current_sequence.fragments:
            return

        fragments = self._current_sequence.fragments

        self._current_sequence.total_novelty = sum(f.novelty for f in fragments) / len(fragments)
        self._current_sequence.total_coherence = sum(f.coherence for f in fragments) / len(fragments)
        self._current_sequence.usable_insights = sum(
            1 for i in self._current_sequence.insights
            if i.actionability > 0.5
        )

    async def lucid_dream(
        self,
        seed: str,
        constraints: List[str] = None,
        goals: List[str] = None
    ) -> DreamSequence:
        """
        Lucid dreaming - aware and in control.

        Explores creatively while maintaining focus on goals.
        """
        logger.info(f"Entering lucid dream: seed='{seed}'")

        # Create sequence
        self._current_sequence = DreamSequence(
            seed=seed,
            theme=DreamTheme.FUSION,  # Lucid dreams use fusion
            state=DreamState.LUCID
        )
        self._state = DreamState.LUCID

        # Generate goal-oriented fragments
        for goal in (goals or [seed]):
            for theme in [DreamTheme.FUSION, DreamTheme.INVERSION, DreamTheme.SACRED]:
                fragment = await self.fragment_generator.generate(
                    seed=f"{seed} for {goal}",
                    theme=theme,
                    depth=2
                )

                # Boost relevance for lucid dreams
                fragment.relevance = min(1.0, fragment.relevance + 0.3)
                self._current_sequence.fragments.append(fragment)

        # Extract insights with goal focus
        insights = await self.insight_extractor.extract(
            self._current_sequence.fragments,
            goal=" ".join(goals or [seed])
        )
        self._current_sequence.insights = insights

        self._calculate_sequence_stats()
        self._current_sequence.ended_at = datetime.utcnow()

        self._history.append(self._current_sequence)
        self._state = DreamState.AWAKE

        return self._current_sequence

    async def nightmare_mode(
        self,
        seed: str
    ) -> DreamSequence:
        """
        Nightmare mode - explore failure paths.

        What could go wrong? What are we missing?
        """
        logger.info(f"Entering nightmare mode: seed='{seed}'")

        self._current_sequence = DreamSequence(
            seed=seed,
            theme=DreamTheme.INVERSION,
            state=DreamState.NIGHTMARE
        )
        self._state = DreamState.NIGHTMARE

        # Generate failure-focused fragments
        failure_prompts = [
            f"How could {seed} fail catastrophically?",
            f"What's the worst case for {seed}?",
            f"What are we not seeing about {seed}?",
            f"What assumption about {seed} is wrong?",
            f"How could {seed} harm users?",
        ]

        for prompt in failure_prompts:
            fragment = await self.fragment_generator.generate(
                seed=prompt,
                theme=DreamTheme.INVERSION,
                depth=3
            )
            fragment.relevance = 0.8  # Nightmares are very relevant
            self._current_sequence.fragments.append(fragment)

        # Extract risk insights
        insights = await self.insight_extractor.extract(
            self._current_sequence.fragments,
            goal=f"risks of {seed}"
        )

        # Tag as risk insights
        for insight in insights:
            insight.insight_type = InsightType.QUESTION
            insight.title = f"⚠️ Risk: {insight.title}"

        self._current_sequence.insights = insights

        self._calculate_sequence_stats()
        self._current_sequence.ended_at = datetime.utcnow()

        self._history.append(self._current_sequence)
        self._state = DreamState.AWAKE

        return self._current_sequence

    def get_best_insights(self, n: int = 5) -> List[DreamInsight]:
        """Get the best insights from all dreams."""
        all_insights = []
        for seq in self._history:
            all_insights.extend(seq.insights)

        # Sort by actionability and confidence
        sorted_insights = sorted(
            all_insights,
            key=lambda i: i.actionability * i.confidence,
            reverse=True
        )

        return sorted_insights[:n]

    def get_dream_summary(self) -> Dict[str, Any]:
        """Get summary of all dreams."""
        if not self._history:
            return {"status": "No dreams recorded"}

        total_fragments = sum(len(s.fragments) for s in self._history)
        total_insights = sum(len(s.insights) for s in self._history)

        return {
            "total_dreams": len(self._history),
            "total_fragments": total_fragments,
            "total_insights": total_insights,
            "avg_novelty": sum(s.total_novelty for s in self._history) / len(self._history),
            "avg_coherence": sum(s.total_coherence for s in self._history) / len(self._history),
            "usable_insights": sum(s.usable_insights for s in self._history),
            "current_state": self._state.value
        }


# =============================================================================
# FACTORY
# =============================================================================

async def create_dream_engine() -> DreamModeEngine:
    """Create a new Dream Mode Engine."""
    return DreamModeEngine()


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    async def main():
        print("💭 BAEL Dream Mode Engine")
        print("=" * 50)

        engine = await create_dream_engine()

        # Regular dream
        print("\n🌙 Entering dream mode...")
        sequence = await engine.enter_dream(
            seed="software architecture",
            theme=DreamTheme.FUSION,
            target_depth=3
        )

        print(f"\n📊 Dream Stats:")
        print(f"  Fragments: {len(sequence.fragments)}")
        print(f"  Insights: {len(sequence.insights)}")
        print(f"  Novelty: {sequence.total_novelty:.2f}")
        print(f"  Coherence: {sequence.total_coherence:.2f}")

        print("\n💡 Sample Fragments:")
        for f in sequence.fragments[:3]:
            print(f"  - {f.content[:60]}...")

        print("\n🔮 Insights:")
        for i in sequence.insights[:3]:
            print(f"  - {i.title}")

        # Nightmare mode
        print("\n" + "=" * 50)
        print("😱 Entering nightmare mode...")
        nightmare = await engine.nightmare_mode("database migration")

        print("\n⚠️ Risk Insights:")
        for i in nightmare.insights[:3]:
            print(f"  - {i.title}")

        # Summary
        print("\n" + "=" * 50)
        print("📋 Dream Summary:")
        summary = engine.get_dream_summary()
        for key, value in summary.items():
            print(f"  {key}: {value}")

        print("\n✅ Dream engine ready")

    asyncio.run(main())

"""
⚡ STRATEGY SELECTION ⚡
=======================
Intelligent strategy selection based on context and history.

Features:
- Strategy library management
- Performance tracking
- Multi-armed bandit selection
- Contextual adaptation
"""

import math
import numpy as np
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from collections import defaultdict
import uuid


@dataclass
class Strategy:
    """A problem-solving strategy"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    applicable_domains: List[str] = field(default_factory=list)
    prerequisites: List[str] = field(default_factory=list)
    complexity: float = 0.5  # 0=simple, 1=complex
    reliability: float = 0.5  # Historical success rate
    speed: float = 0.5  # 0=slow, 1=fast
    resource_cost: float = 0.5  # 0=cheap, 1=expensive
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StrategyOutcome:
    """Outcome of using a strategy"""
    strategy_id: str
    success: bool
    duration: float
    quality: float
    context: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)


class StrategyLibrary:
    """
    Library of available strategies.
    """

    def __init__(self):
        self.strategies: Dict[str, Strategy] = {}
        self.by_domain: Dict[str, List[str]] = defaultdict(list)

    def register(self, strategy: Strategy):
        """Register a strategy"""
        self.strategies[strategy.id] = strategy

        for domain in strategy.applicable_domains:
            self.by_domain[domain].append(strategy.id)

    def get(self, strategy_id: str) -> Optional[Strategy]:
        """Get strategy by ID"""
        return self.strategies.get(strategy_id)

    def get_by_name(self, name: str) -> Optional[Strategy]:
        """Get strategy by name"""
        for strategy in self.strategies.values():
            if strategy.name == name:
                return strategy
        return None

    def get_for_domain(self, domain: str) -> List[Strategy]:
        """Get strategies applicable to domain"""
        return [
            self.strategies[sid]
            for sid in self.by_domain.get(domain, [])
            if sid in self.strategies
        ]

    def search(
        self,
        min_reliability: float = 0.0,
        max_complexity: float = 1.0,
        domains: List[str] = None
    ) -> List[Strategy]:
        """Search for strategies matching criteria"""
        results = []

        for strategy in self.strategies.values():
            if strategy.reliability < min_reliability:
                continue
            if strategy.complexity > max_complexity:
                continue
            if domains:
                if not any(d in strategy.applicable_domains for d in domains):
                    continue

            results.append(strategy)

        return results


class PerformanceTracker:
    """
    Tracks strategy performance over time.
    """

    def __init__(self, window_size: int = 100):
        self.window_size = window_size
        self.outcomes: Dict[str, List[StrategyOutcome]] = defaultdict(list)

        # Aggregated statistics
        self.success_counts: Dict[str, int] = defaultdict(int)
        self.total_counts: Dict[str, int] = defaultdict(int)
        self.quality_sums: Dict[str, float] = defaultdict(float)
        self.duration_sums: Dict[str, float] = defaultdict(float)

    def record(self, outcome: StrategyOutcome):
        """Record strategy outcome"""
        sid = outcome.strategy_id

        self.outcomes[sid].append(outcome)
        self.total_counts[sid] += 1

        if outcome.success:
            self.success_counts[sid] += 1

        self.quality_sums[sid] += outcome.quality
        self.duration_sums[sid] += outcome.duration

        # Trim to window
        if len(self.outcomes[sid]) > self.window_size:
            old = self.outcomes[sid].pop(0)
            self.total_counts[sid] -= 1
            if old.success:
                self.success_counts[sid] -= 1
            self.quality_sums[sid] -= old.quality
            self.duration_sums[sid] -= old.duration

    def get_success_rate(self, strategy_id: str) -> float:
        """Get success rate for strategy"""
        total = self.total_counts.get(strategy_id, 0)
        if total == 0:
            return 0.5  # Prior

        return self.success_counts.get(strategy_id, 0) / total

    def get_average_quality(self, strategy_id: str) -> float:
        """Get average quality for strategy"""
        total = self.total_counts.get(strategy_id, 0)
        if total == 0:
            return 0.5

        return self.quality_sums.get(strategy_id, 0) / total

    def get_average_duration(self, strategy_id: str) -> float:
        """Get average duration for strategy"""
        total = self.total_counts.get(strategy_id, 0)
        if total == 0:
            return float('inf')

        return self.duration_sums.get(strategy_id, 0) / total

    def get_statistics(
        self,
        strategy_id: str
    ) -> Dict[str, float]:
        """Get all statistics for strategy"""
        return {
            'success_rate': self.get_success_rate(strategy_id),
            'avg_quality': self.get_average_quality(strategy_id),
            'avg_duration': self.get_average_duration(strategy_id),
            'total_uses': self.total_counts.get(strategy_id, 0)
        }

    def get_best_strategy(
        self,
        candidates: List[str],
        metric: str = 'success_rate'
    ) -> Optional[str]:
        """Get best strategy by metric"""
        if not candidates:
            return None

        if metric == 'success_rate':
            return max(candidates, key=self.get_success_rate)
        elif metric == 'quality':
            return max(candidates, key=self.get_average_quality)
        elif metric == 'speed':
            return min(candidates, key=self.get_average_duration)

        return candidates[0]


class StrategySelector:
    """
    Selects strategies using multi-armed bandit approach.
    """

    def __init__(
        self,
        library: StrategyLibrary,
        tracker: PerformanceTracker,
        exploration_rate: float = 0.1
    ):
        self.library = library
        self.tracker = tracker
        self.exploration_rate = exploration_rate

    def select_epsilon_greedy(
        self,
        candidates: List[str]
    ) -> str:
        """Epsilon-greedy selection"""
        if not candidates:
            return ""

        if np.random.random() < self.exploration_rate:
            # Explore: random selection
            return np.random.choice(candidates)

        # Exploit: best by success rate
        return self.tracker.get_best_strategy(candidates, 'success_rate') or candidates[0]

    def select_ucb(
        self,
        candidates: List[str],
        c: float = 2.0
    ) -> str:
        """
        Upper Confidence Bound selection.

        Balances exploration and exploitation.
        """
        if not candidates:
            return ""

        total_uses = sum(
            self.tracker.total_counts.get(sid, 0)
            for sid in candidates
        )

        if total_uses == 0:
            return np.random.choice(candidates)

        ucb_scores = []

        for sid in candidates:
            n = self.tracker.total_counts.get(sid, 0)

            if n == 0:
                ucb_scores.append(float('inf'))  # Untried = infinite potential
            else:
                success_rate = self.tracker.get_success_rate(sid)
                exploration_bonus = c * np.sqrt(np.log(total_uses) / n)
                ucb_scores.append(success_rate + exploration_bonus)

        best_idx = np.argmax(ucb_scores)
        return candidates[best_idx]

    def select_thompson(
        self,
        candidates: List[str]
    ) -> str:
        """
        Thompson Sampling selection.

        Samples from posterior distributions.
        """
        if not candidates:
            return ""

        samples = []

        for sid in candidates:
            successes = self.tracker.success_counts.get(sid, 0)
            failures = self.tracker.total_counts.get(sid, 0) - successes

            # Beta prior (1, 1) = uniform
            # Posterior: Beta(1 + successes, 1 + failures)
            sample = np.random.beta(1 + successes, 1 + failures)
            samples.append(sample)

        best_idx = np.argmax(samples)
        return candidates[best_idx]

    def select(
        self,
        domain: str,
        context: Dict[str, Any] = None,
        method: str = 'thompson'
    ) -> Optional[Strategy]:
        """Select strategy for domain"""
        candidates = [s.id for s in self.library.get_for_domain(domain)]

        if not candidates:
            return None

        if method == 'epsilon_greedy':
            selected_id = self.select_epsilon_greedy(candidates)
        elif method == 'ucb':
            selected_id = self.select_ucb(candidates)
        else:  # thompson
            selected_id = self.select_thompson(candidates)

        return self.library.get(selected_id)


class AdaptiveStrategist:
    """
    Advanced adaptive strategy selection.

    Features:
    - Context-aware selection
    - Strategy chaining
    - Meta-strategy learning
    """

    def __init__(
        self,
        library: StrategyLibrary = None,
        tracker: PerformanceTracker = None
    ):
        self.library = library or StrategyLibrary()
        self.tracker = tracker or PerformanceTracker()
        self.selector = StrategySelector(self.library, self.tracker)

        # Context models
        self.context_success: Dict[str, Dict[str, float]] = defaultdict(
            lambda: defaultdict(float)
        )
        self.context_counts: Dict[str, Dict[str, int]] = defaultdict(
            lambda: defaultdict(int)
        )

        # Strategy chains
        self.chains: Dict[str, List[str]] = {}  # chain_name -> [strategy_ids]

        # Current state
        self.current_strategy: Optional[Strategy] = None
        self.strategy_history: List[str] = []

    def add_strategy(
        self,
        name: str,
        description: str,
        domains: List[str],
        complexity: float = 0.5
    ) -> Strategy:
        """Add strategy to library"""
        strategy = Strategy(
            name=name,
            description=description,
            applicable_domains=domains,
            complexity=complexity
        )
        self.library.register(strategy)
        return strategy

    def record_outcome(
        self,
        strategy_id: str,
        success: bool,
        quality: float,
        duration: float,
        context: Dict[str, Any]
    ):
        """Record strategy outcome with context"""
        outcome = StrategyOutcome(
            strategy_id=strategy_id,
            success=success,
            quality=quality,
            duration=duration,
            context=context
        )
        self.tracker.record(outcome)

        # Update context model
        for key, value in context.items():
            context_key = f"{key}:{value}"
            self.context_counts[strategy_id][context_key] += 1
            if success:
                self.context_success[strategy_id][context_key] += 1

    def get_context_score(
        self,
        strategy_id: str,
        context: Dict[str, Any]
    ) -> float:
        """Get strategy score for specific context"""
        if strategy_id not in self.context_counts:
            return 0.5  # Prior

        scores = []

        for key, value in context.items():
            context_key = f"{key}:{value}"
            count = self.context_counts[strategy_id][context_key]

            if count > 0:
                success = self.context_success[strategy_id][context_key]
                scores.append(success / count)

        if not scores:
            return self.tracker.get_success_rate(strategy_id)

        return np.mean(scores)

    def select_contextual(
        self,
        domain: str,
        context: Dict[str, Any]
    ) -> Optional[Strategy]:
        """Select strategy considering context"""
        candidates = self.library.get_for_domain(domain)

        if not candidates:
            return None

        # Score by context + base success rate
        scored = []
        for strategy in candidates:
            context_score = self.get_context_score(strategy.id, context)
            base_score = self.tracker.get_success_rate(strategy.id)

            # Weight context more if we have data
            context_count = sum(
                self.context_counts[strategy.id].values()
            )
            context_weight = min(context_count / 10, 0.8)

            combined = (
                context_weight * context_score +
                (1 - context_weight) * base_score
            )
            scored.append((combined, strategy))

        # Thompson-style sampling with context-adjusted prior
        samples = []
        for score, strategy in scored:
            # Use score to adjust beta parameters
            alpha = 1 + score * 10
            beta = 1 + (1 - score) * 10
            samples.append((np.random.beta(alpha, beta), strategy))

        best = max(samples, key=lambda x: x[0])
        selected = best[1]

        self.current_strategy = selected
        self.strategy_history.append(selected.id)

        return selected

    def create_chain(
        self,
        name: str,
        strategy_names: List[str]
    ):
        """Create strategy chain"""
        strategy_ids = []
        for sname in strategy_names:
            strategy = self.library.get_by_name(sname)
            if strategy:
                strategy_ids.append(strategy.id)

        if strategy_ids:
            self.chains[name] = strategy_ids

    def get_chain(
        self,
        name: str
    ) -> List[Strategy]:
        """Get strategy chain"""
        if name not in self.chains:
            return []

        return [
            self.library.get(sid)
            for sid in self.chains[name]
            if self.library.get(sid)
        ]

    def suggest_fallback(
        self,
        failed_strategy_id: str,
        context: Dict[str, Any]
    ) -> Optional[Strategy]:
        """Suggest fallback after failure"""
        failed = self.library.get(failed_strategy_id)
        if not failed:
            return None

        # Get other strategies in same domain
        alternatives = []
        for domain in failed.applicable_domains:
            alternatives.extend(self.library.get_for_domain(domain))

        # Remove failed strategy
        alternatives = [s for s in alternatives if s.id != failed_strategy_id]

        if not alternatives:
            return None

        # Prefer lower complexity as fallback
        alternatives.sort(key=lambda s: s.complexity)

        return alternatives[0]

    def get_recommendations(
        self,
        domain: str,
        context: Dict[str, Any],
        n: int = 3
    ) -> List[Tuple[Strategy, float]]:
        """Get top n strategy recommendations with scores"""
        candidates = self.library.get_for_domain(domain)

        if not candidates:
            return []

        scored = []
        for strategy in candidates:
            context_score = self.get_context_score(strategy.id, context)
            base_score = self.tracker.get_success_rate(strategy.id)
            combined = 0.6 * context_score + 0.4 * base_score
            scored.append((strategy, combined))

        scored.sort(key=lambda x: -x[1])
        return scored[:n]


# Export all
__all__ = [
    'Strategy',
    'StrategyOutcome',
    'StrategyLibrary',
    'PerformanceTracker',
    'StrategySelector',
    'AdaptiveStrategist',
]

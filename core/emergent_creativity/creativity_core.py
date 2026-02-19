"""
🎨 CREATIVITY CORE 🎨
=====================
Core creative structures.

Features:
- Idea representation
- Creative spaces
- Novelty metrics
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Set
from datetime import datetime
import uuid
import math


class IdeaType(Enum):
    """Types of ideas"""
    CONCEPT = auto()
    SOLUTION = auto()
    DESIGN = auto()
    STRATEGY = auto()
    ANALOGY = auto()
    METAPHOR = auto()
    COMBINATION = auto()
    TRANSFORMATION = auto()
    INVERSION = auto()


class CreativityMode(Enum):
    """Creative thinking modes"""
    DIVERGENT = auto()    # Generate many options
    CONVERGENT = auto()   # Narrow to best
    LATERAL = auto()      # Sideways thinking
    ASSOCIATIVE = auto()  # Connection-based
    RANDOM = auto()       # Random exploration
    STRUCTURED = auto()   # Systematic exploration


@dataclass
class Idea:
    """A creative idea"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Content
    content: Any = None
    description: str = ""

    # Type
    idea_type: IdeaType = IdeaType.CONCEPT

    # Metrics
    novelty: float = 0.0
    quality: float = 0.0
    feasibility: float = 0.0

    # Lineage
    parent_ideas: List[str] = field(default_factory=list)
    generation_method: str = ""

    # Context
    domain: str = ""
    tags: List[str] = field(default_factory=list)

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    creator: str = ""

    def get_fitness(self, weights: Dict[str, float] = None) -> float:
        """Get weighted fitness score"""
        weights = weights or {'novelty': 0.4, 'quality': 0.4, 'feasibility': 0.2}

        return (
            self.novelty * weights.get('novelty', 0.33) +
            self.quality * weights.get('quality', 0.33) +
            self.feasibility * weights.get('feasibility', 0.34)
        )

    def is_derived_from(self, idea_id: str) -> bool:
        """Check if derived from idea"""
        return idea_id in self.parent_ideas


class NoveltyMetric:
    """
    Measures novelty of ideas.
    """

    def __init__(self):
        self.known_ideas: List[Any] = []
        self.feature_extractors: Dict[str, callable] = {}

    def add_extractor(self, name: str, extractor: callable):
        """Add feature extractor"""
        self.feature_extractors[name] = extractor

    def extract_features(self, idea: Idea) -> List[float]:
        """Extract feature vector from idea"""
        features = []

        for name, extractor in self.feature_extractors.items():
            try:
                feat = extractor(idea)
                if isinstance(feat, (int, float)):
                    features.append(feat)
                elif isinstance(feat, (list, tuple)):
                    features.extend(feat)
            except Exception:
                features.append(0.0)

        return features

    def compute_novelty(self, idea: Idea, k: int = 5) -> float:
        """Compute novelty as average distance to k-nearest"""
        if not self.known_ideas:
            return 1.0

        idea_features = self.extract_features(idea)

        if not idea_features:
            return 0.5  # Default novelty

        # Compute distances to known ideas
        distances = []
        for known in self.known_ideas:
            known_features = self.extract_features(known)

            if len(known_features) != len(idea_features):
                continue

            dist = math.sqrt(sum(
                (a - b) ** 2
                for a, b in zip(idea_features, known_features)
            ))
            distances.append(dist)

        if not distances:
            return 1.0

        # Average distance to k-nearest
        distances.sort()
        k_nearest = distances[:k]

        avg_dist = sum(k_nearest) / len(k_nearest)

        # Normalize to 0-1
        return min(1.0, avg_dist / 10.0)

    def add_to_archive(self, idea: Idea):
        """Add idea to known archive"""
        self.known_ideas.append(idea)


class CreativeSpace:
    """
    A space of creative possibilities.
    """

    def __init__(self, name: str = ""):
        self.name = name

        self.ideas: Dict[str, Idea] = {}
        self.novelty_metric = NoveltyMetric()

        # Dimensions of the space
        self.dimensions: List[str] = []
        self.dimension_ranges: Dict[str, tuple] = {}

        # Exploration state
        self.explored_regions: Set[tuple] = set()

        # Mode
        self.mode: CreativityMode = CreativityMode.DIVERGENT

    def add_dimension(self, name: str, min_val: float = 0.0, max_val: float = 1.0):
        """Add dimension to space"""
        self.dimensions.append(name)
        self.dimension_ranges[name] = (min_val, max_val)

    def add_idea(self, idea: Idea) -> bool:
        """Add idea to space"""
        # Compute novelty
        idea.novelty = self.novelty_metric.compute_novelty(idea)

        # Add if novel enough
        if idea.novelty > 0.1 or len(self.ideas) < 10:
            self.ideas[idea.id] = idea
            self.novelty_metric.add_to_archive(idea)
            return True

        return False

    def get_best_ideas(self, n: int = 10, metric: str = "fitness") -> List[Idea]:
        """Get top ideas by metric"""
        ideas = list(self.ideas.values())

        if metric == "fitness":
            ideas.sort(key=lambda i: i.get_fitness(), reverse=True)
        elif metric == "novelty":
            ideas.sort(key=lambda i: i.novelty, reverse=True)
        elif metric == "quality":
            ideas.sort(key=lambda i: i.quality, reverse=True)

        return ideas[:n]

    def get_diverse_set(self, n: int = 5) -> List[Idea]:
        """Get diverse set of ideas"""
        if len(self.ideas) <= n:
            return list(self.ideas.values())

        # Greedy max-min diversity selection
        selected = []
        remaining = list(self.ideas.values())

        # Start with highest novelty
        remaining.sort(key=lambda i: i.novelty, reverse=True)
        selected.append(remaining.pop(0))

        while len(selected) < n and remaining:
            # Find idea with max min distance to selected
            best_idea = None
            best_min_dist = -1

            for idea in remaining:
                min_dist = min(
                    self._idea_distance(idea, s)
                    for s in selected
                )
                if min_dist > best_min_dist:
                    best_min_dist = min_dist
                    best_idea = idea

            if best_idea:
                selected.append(best_idea)
                remaining.remove(best_idea)

        return selected

    def _idea_distance(self, idea1: Idea, idea2: Idea) -> float:
        """Compute distance between ideas"""
        f1 = self.novelty_metric.extract_features(idea1)
        f2 = self.novelty_metric.extract_features(idea2)

        if len(f1) != len(f2):
            return 0.0

        return math.sqrt(sum((a - b) ** 2 for a, b in zip(f1, f2)))

    def get_unexplored_region(self) -> Optional[Dict[str, float]]:
        """Find unexplored region of space"""
        if not self.dimensions:
            return None

        # Generate random point and check if explored
        import random

        for _ in range(100):  # Max attempts
            point = {}
            for dim in self.dimensions:
                min_val, max_val = self.dimension_ranges[dim]
                point[dim] = random.uniform(min_val, max_val)

            # Discretize for checking
            point_key = tuple(round(v * 10) for v in point.values())

            if point_key not in self.explored_regions:
                self.explored_regions.add(point_key)
                return point

        return None

    def get_space_coverage(self) -> float:
        """Get percentage of space explored"""
        # Estimate based on explored regions
        total_cells = 10 ** len(self.dimensions)  # Assuming 10 divisions per dim
        return min(1.0, len(self.explored_regions) / total_cells)


# Export all
__all__ = [
    'IdeaType',
    'CreativityMode',
    'Idea',
    'NoveltyMetric',
    'CreativeSpace',
]

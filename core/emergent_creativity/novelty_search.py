"""
🎨 NOVELTY SEARCH 🎨
====================
Search for novel behaviors.

Features:
- Novelty archive
- Behavior descriptors
- Quality-diversity
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple
import uuid
import math
import random

from .creativity_core import Idea


@dataclass
class BehaviorDescriptor:
    """Describes behavior in feature space"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Feature vector
    features: List[float] = field(default_factory=list)

    # Source
    source_idea_id: str = ""

    # Computed properties
    novelty_score: float = 0.0

    def distance_to(self, other: 'BehaviorDescriptor') -> float:
        """Euclidean distance to another descriptor"""
        if len(self.features) != len(other.features):
            return float('inf')

        return math.sqrt(sum(
            (a - b) ** 2
            for a, b in zip(self.features, other.features)
        ))


class NoveltyArchive:
    """
    Archive of novel behaviors.
    """

    def __init__(self, max_size: int = 1000):
        self.max_size = max_size

        self.archive: List[BehaviorDescriptor] = []

        # k for k-nearest neighbors
        self.k: int = 15

        # Novelty threshold for addition
        self.novelty_threshold: float = 0.5

    def compute_novelty(self, descriptor: BehaviorDescriptor) -> float:
        """Compute novelty score"""
        if not self.archive:
            return 1.0

        # Distance to k-nearest neighbors
        distances = []
        for archived in self.archive:
            dist = descriptor.distance_to(archived)
            distances.append(dist)

        distances.sort()
        k_nearest = distances[:min(self.k, len(distances))]

        if not k_nearest:
            return 1.0

        # Average distance to k-nearest
        novelty = sum(k_nearest) / len(k_nearest)

        # Normalize (approximate)
        max_expected = 2.0  # Assuming normalized features
        descriptor.novelty_score = min(1.0, novelty / max_expected)

        return descriptor.novelty_score

    def add(self, descriptor: BehaviorDescriptor) -> bool:
        """Add descriptor if novel enough"""
        novelty = self.compute_novelty(descriptor)

        if novelty >= self.novelty_threshold:
            if len(self.archive) >= self.max_size:
                self._evict_least_novel()

            self.archive.append(descriptor)
            return True

        return False

    def _evict_least_novel(self):
        """Remove least novel entry"""
        if not self.archive:
            return

        # Recompute novelties
        for desc in self.archive:
            temp_archive = [d for d in self.archive if d.id != desc.id]

            if temp_archive:
                distances = [desc.distance_to(d) for d in temp_archive]
                distances.sort()
                k_nearest = distances[:min(self.k, len(distances))]
                desc.novelty_score = sum(k_nearest) / len(k_nearest)

        # Remove lowest
        self.archive.sort(key=lambda d: d.novelty_score)
        self.archive.pop(0)

    def get_most_novel(self, n: int = 10) -> List[BehaviorDescriptor]:
        """Get most novel entries"""
        sorted_archive = sorted(
            self.archive,
            key=lambda d: d.novelty_score,
            reverse=True
        )
        return sorted_archive[:n]

    def get_random_sample(self, n: int = 10) -> List[BehaviorDescriptor]:
        """Get random sample"""
        return random.sample(self.archive, min(n, len(self.archive)))


class NoveltySearcher:
    """
    Novelty-based search.
    """

    def __init__(self):
        self.archive = NoveltyArchive()

        # Feature extractor
        self.feature_extractor: Optional[Callable[[Idea], List[float]]] = None

        # Population
        self.population: List[Idea] = []
        self.population_size: int = 100

    def set_feature_extractor(self, extractor: Callable[[Idea], List[float]]):
        """Set feature extractor"""
        self.feature_extractor = extractor

    def extract_behavior(self, idea: Idea) -> BehaviorDescriptor:
        """Extract behavior descriptor from idea"""
        features = []

        if self.feature_extractor:
            features = self.feature_extractor(idea)
        else:
            # Default: use idea metrics
            features = [idea.novelty, idea.quality, idea.feasibility]

        return BehaviorDescriptor(
            features=features,
            source_idea_id=idea.id
        )

    def evaluate(self, idea: Idea) -> float:
        """Evaluate idea using novelty"""
        descriptor = self.extract_behavior(idea)
        novelty = self.archive.compute_novelty(descriptor)

        idea.novelty = novelty

        # Add to archive
        self.archive.add(descriptor)

        return novelty

    def search(
        self,
        generate_fn: Callable[[], Idea],
        mutate_fn: Callable[[Idea], Idea],
        generations: int = 100
    ) -> List[Idea]:
        """Run novelty search"""
        # Initialize population
        self.population = [generate_fn() for _ in range(self.population_size)]

        for gen in range(generations):
            # Evaluate novelty
            for idea in self.population:
                self.evaluate(idea)

            # Sort by novelty
            self.population.sort(key=lambda i: i.novelty, reverse=True)

            # Selection: keep top half
            survivors = self.population[:self.population_size // 2]

            # Reproduction
            children = []
            while len(children) < self.population_size - len(survivors):
                parent = random.choice(survivors)
                child = mutate_fn(parent)
                children.append(child)

            self.population = survivors + children

        return self.population


@dataclass
class QDIndividual:
    """Individual for quality-diversity"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    idea: Optional[Idea] = None

    # Behavior descriptor
    behavior: List[float] = field(default_factory=list)

    # Quality score
    quality: float = 0.0

    # Grid cell (for MAP-Elites)
    cell: Optional[Tuple[int, ...]] = None


class QualityDiversity:
    """
    Quality-Diversity optimization.
    Finds diverse, high-quality solutions.
    """

    def __init__(
        self,
        behavior_dims: int = 2,
        cells_per_dim: int = 20
    ):
        self.behavior_dims = behavior_dims
        self.cells_per_dim = cells_per_dim

        # MAP-Elites grid
        self.grid: Dict[Tuple[int, ...], QDIndividual] = {}

        # Bounds for behavior space
        self.behavior_bounds: List[Tuple[float, float]] = [
            (0.0, 1.0) for _ in range(behavior_dims)
        ]

    def _get_cell(self, behavior: List[float]) -> Tuple[int, ...]:
        """Get grid cell for behavior"""
        cell = []

        for i, val in enumerate(behavior):
            if i < len(self.behavior_bounds):
                min_val, max_val = self.behavior_bounds[i]
                normalized = (val - min_val) / (max_val - min_val + 1e-10)
                cell_idx = min(int(normalized * self.cells_per_dim), self.cells_per_dim - 1)
                cell.append(max(0, cell_idx))
            else:
                cell.append(0)

        return tuple(cell)

    def add(
        self,
        idea: Idea,
        behavior: List[float],
        quality: float
    ) -> bool:
        """Add to archive if improves cell"""
        cell = self._get_cell(behavior)

        individual = QDIndividual(
            idea=idea,
            behavior=behavior,
            quality=quality,
            cell=cell
        )

        # Check if cell is empty or new individual is better
        if cell not in self.grid or quality > self.grid[cell].quality:
            self.grid[cell] = individual
            return True

        return False

    def get_all(self) -> List[QDIndividual]:
        """Get all individuals in archive"""
        return list(self.grid.values())

    def get_best(self, n: int = 10) -> List[QDIndividual]:
        """Get best quality individuals"""
        individuals = list(self.grid.values())
        individuals.sort(key=lambda i: i.quality, reverse=True)
        return individuals[:n]

    def get_diverse(self, n: int = 10) -> List[QDIndividual]:
        """Get diverse set of individuals"""
        individuals = list(self.grid.values())

        if len(individuals) <= n:
            return individuals

        # Sample from different cells
        cells = list(self.grid.keys())
        selected_cells = random.sample(cells, min(n, len(cells)))

        return [self.grid[cell] for cell in selected_cells]

    def coverage(self) -> float:
        """Get archive coverage"""
        total_cells = self.cells_per_dim ** self.behavior_dims
        return len(self.grid) / total_cells

    def evolve(
        self,
        generate_fn: Callable[[], Tuple[Idea, List[float], float]],
        mutate_fn: Callable[[Idea], Tuple[Idea, List[float], float]],
        iterations: int = 1000
    ):
        """Run MAP-Elites evolution"""
        # Initialize with random individuals
        for _ in range(100):
            idea, behavior, quality = generate_fn()
            self.add(idea, behavior, quality)

        # Evolution
        for _ in range(iterations):
            if not self.grid:
                continue

            # Select random individual
            individual = random.choice(list(self.grid.values()))

            # Mutate
            new_idea, new_behavior, new_quality = mutate_fn(individual.idea)

            # Try to add
            self.add(new_idea, new_behavior, new_quality)

    def get_qd_score(self) -> float:
        """Get QD-score (sum of qualities)"""
        return sum(ind.quality for ind in self.grid.values())


# Export all
__all__ = [
    'BehaviorDescriptor',
    'NoveltyArchive',
    'NoveltySearcher',
    'QDIndividual',
    'QualityDiversity',
]

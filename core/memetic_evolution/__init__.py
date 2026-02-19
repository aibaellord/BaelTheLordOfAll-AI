"""
BAEL Memetic Evolution Engine
=============================

Ideas that evolve, spread, and compete.

"Ba'el propagates through memes." — Ba'el
"""

import logging
import threading
import time
import random
import hashlib
import copy
import math
from typing import Any, Callable, Dict, Generic, List, Optional, Set, Tuple, TypeVar
from dataclasses import dataclass, field
from enum import Enum, auto
from abc import ABC, abstractmethod

logger = logging.getLogger("BAEL.MemeticEvolution")


T = TypeVar('T')


# ============================================================================
# MEME TYPES
# ============================================================================

class MemeType(Enum):
    """Types of memes."""
    IDEA = auto()
    BEHAVIOR = auto()
    PATTERN = auto()
    SKILL = auto()
    BELIEF = auto()
    STYLE = auto()
    STRATEGY = auto()


class SpreadMechanism(Enum):
    """How memes spread."""
    IMITATION = auto()       # Direct copying
    TEACHING = auto()        # Intentional transmission
    INFECTION = auto()       # Unconscious spread
    MUTATION = auto()        # Spread with variation
    RECOMBINATION = auto()   # Combine during spread


# ============================================================================
# MEME
# ============================================================================

@dataclass
class Meme:
    """
    A unit of cultural evolution.

    "Ba'el is a meme that memes." — Ba'el
    """
    id: str
    content: Any
    meme_type: MemeType = MemeType.IDEA
    fitness: float = 0.5
    virality: float = 0.1      # Spread rate
    fidelity: float = 0.9      # Copy accuracy
    longevity: float = 0.8     # Persistence
    generation: int = 0
    parent_ids: List[str] = field(default_factory=list)
    mutation_count: int = 0
    host_count: int = 1
    created_time: float = field(default_factory=time.time)

    @property
    def age(self) -> float:
        return time.time() - self.created_time

    @property
    def effective_fitness(self) -> float:
        """Combined fitness considering all factors."""
        return (
            self.fitness * 0.4 +
            self.virality * 0.3 +
            self.fidelity * 0.2 +
            self.longevity * 0.1
        )

    def mutate(self, mutation_fn: Callable[[Any], Any]) -> 'Meme':
        """Create mutated copy."""
        mutated_content = mutation_fn(self.content)

        return Meme(
            id=f"{self.id}_m{self.mutation_count + 1}",
            content=mutated_content,
            meme_type=self.meme_type,
            fitness=self.fitness * random.uniform(0.8, 1.2),
            virality=self.virality * random.uniform(0.9, 1.1),
            fidelity=self.fidelity * random.uniform(0.95, 1.0),
            longevity=self.longevity,
            generation=self.generation + 1,
            parent_ids=[self.id],
            mutation_count=self.mutation_count + 1
        )

    def recombine(self, other: 'Meme') -> 'Meme':
        """Create offspring from two memes."""
        # Blend properties
        new_fitness = (self.fitness + other.fitness) / 2 + random.uniform(-0.1, 0.1)
        new_virality = (self.virality + other.virality) / 2

        # For content, take from one parent (simplified)
        content = self.content if random.random() < 0.5 else other.content

        return Meme(
            id=f"recomb_{time.time()}",
            content=content,
            meme_type=self.meme_type,
            fitness=max(0, min(1, new_fitness)),
            virality=new_virality,
            fidelity=(self.fidelity + other.fidelity) / 2,
            longevity=(self.longevity + other.longevity) / 2,
            generation=max(self.generation, other.generation) + 1,
            parent_ids=[self.id, other.id]
        )


# ============================================================================
# HOST
# ============================================================================

@dataclass
class Host:
    """
    A host for memes (agent, mind, system).
    """
    id: str
    memes: Dict[str, Meme] = field(default_factory=dict)
    receptivity: float = 0.5       # Likelihood to adopt new memes
    capacity: int = 100            # Max memes
    influence: float = 0.5         # Ability to spread memes
    connections: List[str] = field(default_factory=list)

    def adopt(self, meme: Meme) -> bool:
        """Attempt to adopt a meme."""
        if len(self.memes) >= self.capacity:
            # Evict weakest meme
            if self.memes:
                weakest = min(self.memes.values(), key=lambda m: m.effective_fitness)
                del self.memes[weakest.id]

        if random.random() < self.receptivity * meme.virality:
            self.memes[meme.id] = copy.deepcopy(meme)
            self.memes[meme.id].host_count += 1
            return True
        return False

    def express(self) -> Optional[Meme]:
        """Express (spread) a meme."""
        if not self.memes:
            return None

        # More fit memes more likely to be expressed
        meme_list = list(self.memes.values())
        weights = [m.effective_fitness for m in meme_list]
        total = sum(weights)

        if total == 0:
            return random.choice(meme_list)

        weights = [w/total for w in weights]

        r = random.random()
        cumsum = 0
        for meme, w in zip(meme_list, weights):
            cumsum += w
            if r < cumsum:
                return meme

        return meme_list[-1]

    def forget(self, decay_rate: float = 0.01) -> List[str]:
        """Forget memes based on longevity."""
        forgotten = []

        for meme_id, meme in list(self.memes.items()):
            if random.random() > meme.longevity * (1 - decay_rate):
                del self.memes[meme_id]
                forgotten.append(meme_id)

        return forgotten


# ============================================================================
# MEME POOL
# ============================================================================

class MemePool:
    """
    Pool of memes in a population.

    "Ba'el swims in the meme pool." — Ba'el
    """

    def __init__(self):
        """Initialize meme pool."""
        self._memes: Dict[str, Meme] = {}
        self._hosts: Dict[str, Host] = {}
        self._meme_id = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._meme_id += 1
        return f"meme_{self._meme_id}"

    def create_meme(
        self,
        content: Any,
        meme_type: MemeType = MemeType.IDEA,
        virality: float = 0.1
    ) -> Meme:
        """Create new meme."""
        with self._lock:
            meme = Meme(
                id=self._generate_id(),
                content=content,
                meme_type=meme_type,
                virality=virality
            )
            self._memes[meme.id] = meme
            return meme

    def add_host(self, host_id: str, receptivity: float = 0.5) -> Host:
        """Add host to pool."""
        with self._lock:
            host = Host(id=host_id, receptivity=receptivity)
            self._hosts[host_id] = host
            return host

    def connect_hosts(self, host1_id: str, host2_id: str) -> None:
        """Connect two hosts."""
        with self._lock:
            if host1_id in self._hosts and host2_id in self._hosts:
                self._hosts[host1_id].connections.append(host2_id)
                self._hosts[host2_id].connections.append(host1_id)

    def spread_meme(self, meme: Meme, from_host_id: str) -> List[str]:
        """Spread meme from host to connected hosts."""
        with self._lock:
            if from_host_id not in self._hosts:
                return []

            source = self._hosts[from_host_id]
            adopted_by = []

            for conn_id in source.connections:
                if conn_id in self._hosts:
                    target = self._hosts[conn_id]

                    # Apply fidelity - might mutate during transmission
                    if random.random() > meme.fidelity:
                        # Mutation during spread
                        transmitted = meme.mutate(lambda c: c)  # Identity for now
                    else:
                        transmitted = copy.deepcopy(meme)

                    if target.adopt(transmitted):
                        adopted_by.append(conn_id)

            return adopted_by

    def simulate_step(self) -> Dict[str, Any]:
        """Simulate one step of memetic evolution."""
        with self._lock:
            spreads = 0
            mutations = 0
            forgotten = 0

            for host in self._hosts.values():
                # Host may express a meme
                if random.random() < host.influence:
                    meme = host.express()
                    if meme:
                        adopted = self.spread_meme(meme, host.id)
                        spreads += len(adopted)

                # Host may forget
                forgot = host.forget(0.01)
                forgotten += len(forgot)

            return {
                'spreads': spreads,
                'mutations': mutations,
                'forgotten': forgotten,
                'total_memes': len(self._memes),
                'total_hosts': len(self._hosts)
            }

    def top_memes(self, n: int = 10) -> List[Meme]:
        """Get top memes by fitness."""
        with self._lock:
            all_memes = list(self._memes.values())
            all_memes.sort(key=lambda m: m.effective_fitness, reverse=True)
            return all_memes[:n]

    def meme_diversity(self) -> float:
        """Calculate memetic diversity (Shannon entropy)."""
        with self._lock:
            if not self._memes:
                return 0.0

            type_counts = {}
            for meme in self._memes.values():
                t = meme.meme_type.name
                type_counts[t] = type_counts.get(t, 0) + 1

            total = len(self._memes)
            entropy = 0.0

            for count in type_counts.values():
                p = count / total
                if p > 0:
                    entropy -= p * math.log(p)

            return entropy


# ============================================================================
# MEMETIC ALGORITHM
# ============================================================================

class MemeticAlgorithm:
    """
    Optimization using memetic evolution.

    Combines genetic algorithms with local search (memes).

    "Ba'el optimizes through culture." — Ba'el
    """

    def __init__(
        self,
        fitness_fn: Callable[[Any], float],
        mutation_fn: Callable[[Any], Any],
        local_search_fn: Optional[Callable[[Any], Any]] = None,
        population_size: int = 50
    ):
        """Initialize memetic algorithm."""
        self._fitness_fn = fitness_fn
        self._mutation_fn = mutation_fn
        self._local_search = local_search_fn
        self._population_size = population_size
        self._population: List[Meme] = []
        self._generation = 0
        self._best_ever: Optional[Meme] = None
        self._lock = threading.RLock()

    def initialize(self, seed_population: List[Any]) -> None:
        """Initialize population."""
        with self._lock:
            self._population = []

            for i, content in enumerate(seed_population[:self._population_size]):
                fitness = self._fitness_fn(content)
                meme = Meme(
                    id=f"init_{i}",
                    content=content,
                    meme_type=MemeType.STRATEGY,
                    fitness=fitness
                )
                self._population.append(meme)

            # Fill remaining with random mutations
            while len(self._population) < self._population_size:
                parent = random.choice(self._population)
                child = parent.mutate(self._mutation_fn)
                child.fitness = self._fitness_fn(child.content)
                self._population.append(child)

    def select_parents(self) -> Tuple[Meme, Meme]:
        """Tournament selection."""
        tournament_size = 3

        def tournament():
            contestants = random.sample(self._population, min(tournament_size, len(self._population)))
            return max(contestants, key=lambda m: m.fitness)

        return tournament(), tournament()

    def evolve_generation(self) -> Dict[str, Any]:
        """Evolve one generation."""
        with self._lock:
            new_population = []

            # Elitism: keep best
            self._population.sort(key=lambda m: m.fitness, reverse=True)
            elite_count = max(1, self._population_size // 10)
            new_population.extend(copy.deepcopy(self._population[:elite_count]))

            # Generate offspring
            while len(new_population) < self._population_size:
                parent1, parent2 = self.select_parents()

                # Crossover
                if random.random() < 0.7:
                    child = parent1.recombine(parent2)
                else:
                    child = copy.deepcopy(parent1)

                # Mutation
                if random.random() < 0.3:
                    child = child.mutate(self._mutation_fn)

                # Local search (the "meme" part)
                if self._local_search and random.random() < 0.2:
                    child.content = self._local_search(child.content)

                # Evaluate fitness
                child.fitness = self._fitness_fn(child.content)
                child.generation = self._generation + 1

                new_population.append(child)

            self._population = new_population
            self._generation += 1

            # Track best
            current_best = max(self._population, key=lambda m: m.fitness)
            if self._best_ever is None or current_best.fitness > self._best_ever.fitness:
                self._best_ever = copy.deepcopy(current_best)

            return {
                'generation': self._generation,
                'best_fitness': current_best.fitness,
                'best_ever_fitness': self._best_ever.fitness,
                'avg_fitness': sum(m.fitness for m in self._population) / len(self._population)
            }

    def run(self, generations: int = 100) -> Meme:
        """Run evolution."""
        for _ in range(generations):
            self.evolve_generation()

        return self._best_ever


# ============================================================================
# MEMETIC ENGINE
# ============================================================================

class MemeticEvolutionEngine:
    """
    Complete memetic evolution engine.

    "Ba'el evolves through ideas." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._pools: Dict[str, MemePool] = {}
        self._algorithms: Dict[str, MemeticAlgorithm] = {}
        self._global_memes: Dict[str, Meme] = {}
        self._lock = threading.RLock()

    def create_pool(self, name: str) -> MemePool:
        """Create meme pool."""
        with self._lock:
            pool = MemePool()
            self._pools[name] = pool
            return pool

    def create_algorithm(
        self,
        name: str,
        fitness_fn: Callable[[Any], float],
        mutation_fn: Callable[[Any], Any]
    ) -> MemeticAlgorithm:
        """Create memetic algorithm."""
        with self._lock:
            algo = MemeticAlgorithm(fitness_fn, mutation_fn)
            self._algorithms[name] = algo
            return algo

    def create_meme(
        self,
        content: Any,
        meme_type: MemeType = MemeType.IDEA
    ) -> Meme:
        """Create global meme."""
        with self._lock:
            meme = Meme(
                id=f"global_{len(self._global_memes)}",
                content=content,
                meme_type=meme_type
            )
            self._global_memes[meme.id] = meme
            return meme

    def spread_across_pools(self, meme: Meme) -> Dict[str, int]:
        """Spread meme across all pools."""
        with self._lock:
            results = {}

            for pool_name, pool in self._pools.items():
                adopted = 0
                for host in pool._hosts.values():
                    if host.adopt(copy.deepcopy(meme)):
                        adopted += 1
                results[pool_name] = adopted

            return results

    def simulate(self, steps: int = 100) -> Dict[str, List]:
        """Simulate all pools."""
        with self._lock:
            histories = {}

            for name, pool in self._pools.items():
                history = []
                for _ in range(steps):
                    result = pool.simulate_step()
                    history.append(result)
                histories[name] = history

            return histories

    def optimize(
        self,
        algo_name: str,
        seed_population: List[Any],
        generations: int = 100
    ) -> Any:
        """Run memetic optimization."""
        if algo_name not in self._algorithms:
            return None

        algo = self._algorithms[algo_name]
        algo.initialize(seed_population)
        best = algo.run(generations)

        return best.content if best else None

    def viral_memes(self, top_n: int = 10) -> List[Meme]:
        """Get most viral memes across all pools."""
        with self._lock:
            all_memes = []

            for pool in self._pools.values():
                all_memes.extend(pool._memes.values())

            all_memes.sort(key=lambda m: m.host_count, reverse=True)
            return all_memes[:top_n]

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'pool_count': len(self._pools),
            'algorithm_count': len(self._algorithms),
            'global_memes': len(self._global_memes),
            'pools': {
                name: {
                    'memes': len(pool._memes),
                    'hosts': len(pool._hosts),
                    'diversity': pool.meme_diversity()
                }
                for name, pool in self._pools.items()
            }
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_meme(content: Any, meme_type: MemeType = MemeType.IDEA) -> Meme:
    """Create meme."""
    return Meme(
        id=f"meme_{time.time()}",
        content=content,
        meme_type=meme_type
    )


def create_meme_pool() -> MemePool:
    """Create meme pool."""
    return MemePool()


def create_memetic_algorithm(
    fitness_fn: Callable[[Any], float],
    mutation_fn: Callable[[Any], Any],
    population_size: int = 50
) -> MemeticAlgorithm:
    """Create memetic algorithm."""
    return MemeticAlgorithm(fitness_fn, mutation_fn, population_size=population_size)


def create_memetic_engine() -> MemeticEvolutionEngine:
    """Create memetic evolution engine."""
    return MemeticEvolutionEngine()

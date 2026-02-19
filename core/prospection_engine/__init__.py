"""
BAEL Prospection Engine
=========================

Future thinking and episodic simulation.
Schacter & Addis constructive episodic simulation.

"Ba'el sees what may come." — Ba'el
"""

import logging
import threading
import time
import math
import random
from typing import Any, Callable, Dict, Generic, List, Optional, Set, Tuple, TypeVar
from dataclasses import dataclass, field
from enum import Enum, auto
from abc import ABC, abstractmethod
from collections import defaultdict, deque
import copy

logger = logging.getLogger("BAEL.Prospection")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class TemporalDirection(Enum):
    """Temporal direction."""
    PAST = auto()
    PRESENT = auto()
    FUTURE = auto()


class SimulationType(Enum):
    """Types of episodic simulation."""
    REMEMBERING = auto()    # Past
    IMAGINING = auto()      # Future
    COUNTERFACTUAL = auto() # Alternative past
    ATEMPORAL = auto()      # No specific time


class ScenarioPlausibility(Enum):
    """Plausibility of scenario."""
    IMPOSSIBLE = 1
    UNLIKELY = 2
    POSSIBLE = 3
    LIKELY = 4
    CERTAIN = 5


class TemporalDistance(Enum):
    """Temporal distance."""
    IMMEDIATE = auto()    # Hours
    NEAR = auto()         # Days
    MEDIUM = auto()       # Weeks/months
    FAR = auto()          # Years
    DISTANT = auto()      # Decades


@dataclass
class EpisodicElement:
    """
    An element from episodic memory.
    """
    id: str
    content: Any
    source_memory: str
    element_type: str  # person, place, object, action


@dataclass
class FutureScenario:
    """
    A simulated future scenario.
    """
    id: str
    description: str
    temporal_distance: TemporalDistance
    plausibility: ScenarioPlausibility

    elements: List[EpisodicElement]
    emotional_valence: float  # -1 to 1
    vividness: float
    detail_level: float

    creation_time: float = field(default_factory=time.time)


@dataclass
class SimulationResult:
    """
    Result of episodic simulation.
    """
    scenario: FutureScenario
    elements_recombined: int
    novel_combinations: int
    construction_time: float


@dataclass
class ProspectionMetrics:
    """
    Prospection metrics.
    """
    total_simulations: int
    average_vividness: float
    average_plausibility: float
    future_bias: float  # Positive = optimistic


# ============================================================================
# EPISODIC ELEMENT STORE
# ============================================================================

class EpisodicElementStore:
    """
    Store of episodic elements for recombination.

    "Ba'el's memory fragments." — Ba'el
    """

    def __init__(self):
        """Initialize store."""
        self._elements: Dict[str, EpisodicElement] = {}
        self._by_type: Dict[str, List[str]] = defaultdict(list)

        self._element_counter = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._element_counter += 1
        return f"element_{self._element_counter}"

    def add_element(
        self,
        content: Any,
        source_memory: str,
        element_type: str
    ) -> EpisodicElement:
        """Add an episodic element."""
        element = EpisodicElement(
            id=self._generate_id(),
            content=content,
            source_memory=source_memory,
            element_type=element_type
        )

        self._elements[element.id] = element
        self._by_type[element_type].append(element.id)

        return element

    def get_elements_by_type(
        self,
        element_type: str
    ) -> List[EpisodicElement]:
        """Get elements of a type."""
        ids = self._by_type.get(element_type, [])
        return [self._elements[id] for id in ids if id in self._elements]

    def sample_elements(
        self,
        n: int,
        element_type: str = None
    ) -> List[EpisodicElement]:
        """Sample random elements."""
        if element_type:
            pool = self.get_elements_by_type(element_type)
        else:
            pool = list(self._elements.values())

        if len(pool) <= n:
            return pool

        return random.sample(pool, n)

    def get_all_types(self) -> List[str]:
        """Get all element types."""
        return list(self._by_type.keys())


# ============================================================================
# CONSTRUCTIVE SIMULATOR
# ============================================================================

class ConstructiveSimulator:
    """
    Schacter & Addis constructive episodic simulation.

    "Ba'el recombines memories into futures." — Ba'el
    """

    def __init__(
        self,
        element_store: EpisodicElementStore
    ):
        """Initialize simulator."""
        self._store = element_store
        self._lock = threading.RLock()

    def construct_scenario(
        self,
        description: str,
        temporal_distance: TemporalDistance,
        required_types: List[str] = None,
        elements_per_type: int = 2
    ) -> FutureScenario:
        """Construct a future scenario."""
        start_time = time.time()

        # Gather elements to recombine
        elements = []
        types = required_types or ['person', 'place', 'object', 'action']

        for element_type in types:
            type_elements = self._store.sample_elements(
                elements_per_type, element_type
            )
            elements.extend(type_elements)

        # Calculate properties based on elements and distance
        vividness = self._calculate_vividness(temporal_distance, len(elements))
        detail_level = self._calculate_detail_level(temporal_distance)
        plausibility = self._assess_plausibility(elements)

        # Emotional valence (slight optimism bias)
        emotional_valence = random.gauss(0.1, 0.3)
        emotional_valence = max(-1, min(1, emotional_valence))

        scenario = FutureScenario(
            id=f"scenario_{int(time.time() * 1000)}",
            description=description,
            temporal_distance=temporal_distance,
            plausibility=plausibility,
            elements=elements,
            emotional_valence=emotional_valence,
            vividness=vividness,
            detail_level=detail_level
        )

        return scenario

    def _calculate_vividness(
        self,
        temporal_distance: TemporalDistance,
        n_elements: int
    ) -> float:
        """Calculate vividness based on distance and elements."""
        # Closer futures are more vivid
        distance_factor = {
            TemporalDistance.IMMEDIATE: 0.9,
            TemporalDistance.NEAR: 0.8,
            TemporalDistance.MEDIUM: 0.6,
            TemporalDistance.FAR: 0.4,
            TemporalDistance.DISTANT: 0.3
        }.get(temporal_distance, 0.5)

        # More elements = more vivid
        element_factor = min(1.0, n_elements / 10)

        return distance_factor * 0.7 + element_factor * 0.3

    def _calculate_detail_level(
        self,
        temporal_distance: TemporalDistance
    ) -> float:
        """Calculate detail level."""
        return {
            TemporalDistance.IMMEDIATE: 0.85,
            TemporalDistance.NEAR: 0.7,
            TemporalDistance.MEDIUM: 0.5,
            TemporalDistance.FAR: 0.35,
            TemporalDistance.DISTANT: 0.2
        }.get(temporal_distance, 0.5)

    def _assess_plausibility(
        self,
        elements: List[EpisodicElement]
    ) -> ScenarioPlausibility:
        """Assess scenario plausibility."""
        # More elements from same source = more plausible
        sources = [e.source_memory for e in elements]
        unique_sources = len(set(sources))

        if unique_sources == 0:
            return ScenarioPlausibility.POSSIBLE

        coherence = 1 - (unique_sources / len(sources))

        if coherence > 0.7:
            return ScenarioPlausibility.LIKELY
        elif coherence > 0.5:
            return ScenarioPlausibility.POSSIBLE
        elif coherence > 0.3:
            return ScenarioPlausibility.UNLIKELY
        else:
            return ScenarioPlausibility.UNLIKELY


# ============================================================================
# TEMPORAL SELF
# ============================================================================

class TemporalSelf:
    """
    The self across time.

    "Ba'el projects the self." — Ba'el
    """

    def __init__(self):
        """Initialize temporal self."""
        self._current_goals: List[str] = []
        self._future_selves: Dict[TemporalDistance, Dict[str, Any]] = {}

        self._lock = threading.RLock()

    def set_goals(
        self,
        goals: List[str]
    ) -> None:
        """Set current goals."""
        self._current_goals = goals

    def project_self(
        self,
        temporal_distance: TemporalDistance
    ) -> Dict[str, Any]:
        """Project self into future."""
        projection = {
            'distance': temporal_distance.name,
            'goals_achieved': [],
            'changes': []
        }

        # Optimism bias - expect goal achievement
        for goal in self._current_goals:
            if random.random() < 0.7:  # 70% expect success
                projection['goals_achieved'].append(goal)

        # Expected changes based on distance
        if temporal_distance in [TemporalDistance.FAR, TemporalDistance.DISTANT]:
            projection['changes'] = ['wisdom', 'stability', 'success']
        else:
            projection['changes'] = ['progress', 'learning']

        self._future_selves[temporal_distance] = projection
        return projection

    def compare_past_future(
        self,
        past_event: Any,
        future_scenario: FutureScenario
    ) -> Dict[str, Any]:
        """Compare past remembering to future imagining."""
        return {
            'asymmetry': 'Future more positive than past',
            'detail': 'Past more detailed than distant future',
            'emotional_impact': 'Future events have reduced emotional impact'
        }


# ============================================================================
# PROSPECTION ENGINE
# ============================================================================

class ProspectionEngine:
    """
    Complete prospection engine.

    "Ba'el's future thinking system." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._element_store = EpisodicElementStore()
        self._simulator = ConstructiveSimulator(self._element_store)
        self._temporal_self = TemporalSelf()

        self._scenarios: Dict[str, FutureScenario] = {}
        self._simulation_history: List[SimulationResult] = []

        self._lock = threading.RLock()

    # Memory element encoding

    def encode_memory_elements(
        self,
        memory_id: str,
        people: List[str] = None,
        places: List[str] = None,
        objects: List[str] = None,
        actions: List[str] = None
    ) -> List[EpisodicElement]:
        """Encode elements from a memory."""
        elements = []

        for person in (people or []):
            elem = self._element_store.add_element(
                person, memory_id, 'person'
            )
            elements.append(elem)

        for place in (places or []):
            elem = self._element_store.add_element(
                place, memory_id, 'place'
            )
            elements.append(elem)

        for obj in (objects or []):
            elem = self._element_store.add_element(
                obj, memory_id, 'object'
            )
            elements.append(elem)

        for action in (actions or []):
            elem = self._element_store.add_element(
                action, memory_id, 'action'
            )
            elements.append(elem)

        return elements

    def extract_elements_from_experience(
        self,
        experience: str,
        memory_id: str = None
    ) -> List[EpisodicElement]:
        """Extract elements from experience description."""
        # Simple extraction (in real system would use NLP)
        memory_id = memory_id or f"exp_{int(time.time())}"

        # Add as generic elements
        elem = self._element_store.add_element(
            experience, memory_id, 'experience'
        )

        return [elem]

    # Future simulation

    def imagine_future(
        self,
        description: str,
        temporal_distance: TemporalDistance = TemporalDistance.NEAR
    ) -> FutureScenario:
        """Imagine a future scenario."""
        start_time = time.time()

        scenario = self._simulator.construct_scenario(
            description, temporal_distance
        )

        self._scenarios[scenario.id] = scenario

        result = SimulationResult(
            scenario=scenario,
            elements_recombined=len(scenario.elements),
            novel_combinations=len(set(e.source_memory for e in scenario.elements)),
            construction_time=time.time() - start_time
        )

        self._simulation_history.append(result)

        return scenario

    def imagine_specific_future(
        self,
        description: str,
        temporal_distance: TemporalDistance,
        must_include: List[str] = None
    ) -> FutureScenario:
        """Imagine specific future with constraints."""
        # First get base scenario
        scenario = self.imagine_future(description, temporal_distance)

        # Add specific elements if requested
        if must_include:
            for item in must_include:
                elem = self._element_store.add_element(
                    item, "constraint", "required"
                )
                scenario.elements.append(elem)

        return scenario

    def simulate_multiple_futures(
        self,
        base_description: str,
        n_alternatives: int = 3
    ) -> List[FutureScenario]:
        """Simulate multiple alternative futures."""
        scenarios = []

        distances = [
            TemporalDistance.NEAR,
            TemporalDistance.MEDIUM,
            TemporalDistance.FAR
        ]

        for i in range(n_alternatives):
            distance = distances[i % len(distances)]
            scenario = self.imagine_future(
                f"{base_description} (alternative {i + 1})",
                distance
            )
            scenarios.append(scenario)

        return scenarios

    # Goal-directed prospection

    def set_goals(
        self,
        goals: List[str]
    ) -> None:
        """Set personal goals."""
        self._temporal_self.set_goals(goals)

    def imagine_goal_achieved(
        self,
        goal: str,
        temporal_distance: TemporalDistance = TemporalDistance.MEDIUM
    ) -> FutureScenario:
        """Imagine scenario where goal is achieved."""
        scenario = self.imagine_future(
            f"Goal achieved: {goal}",
            temporal_distance
        )

        # Goals achieved scenarios are more positive
        scenario.emotional_valence = max(0.3, scenario.emotional_valence)

        return scenario

    def simulate_paths_to_goal(
        self,
        goal: str,
        n_paths: int = 3
    ) -> List[FutureScenario]:
        """Simulate different paths to a goal."""
        paths = []

        for i in range(n_paths):
            scenario = self.imagine_future(
                f"Path {i + 1} to {goal}",
                TemporalDistance.MEDIUM
            )
            paths.append(scenario)

        return sorted(
            paths,
            key=lambda s: s.plausibility.value,
            reverse=True
        )

    # Mental time travel

    def mental_time_travel(
        self,
        direction: TemporalDirection,
        distance: TemporalDistance
    ) -> Dict[str, Any]:
        """Mental time travel."""
        if direction == TemporalDirection.FUTURE:
            scenario = self.imagine_future(
                f"Self in {distance.name} future",
                distance
            )

            return {
                'direction': 'FUTURE',
                'scenario': scenario.description,
                'vividness': scenario.vividness,
                'emotional_valence': scenario.emotional_valence
            }

        elif direction == TemporalDirection.PAST:
            # Past is more detailed but less positive
            return {
                'direction': 'PAST',
                'detail_level': 0.8,
                'emotional_complexity': 'higher than future'
            }

        return {'direction': 'PRESENT'}

    # Counterfactual thinking

    def imagine_counterfactual(
        self,
        original_event: str,
        alternative: str
    ) -> FutureScenario:
        """Imagine counterfactual scenario."""
        scenario = self._simulator.construct_scenario(
            f"What if {alternative} instead of {original_event}",
            TemporalDistance.IMMEDIATE,  # Counterfactuals are vivid
            elements_per_type=3
        )

        scenario.plausibility = ScenarioPlausibility.POSSIBLE

        self._scenarios[scenario.id] = scenario

        return scenario

    # Analysis

    def analyze_temporal_asymmetry(self) -> Dict[str, Any]:
        """Analyze future vs past thinking asymmetries."""
        scenarios = list(self._scenarios.values())

        if not scenarios:
            return {'asymmetry': 'No data'}

        avg_valence = sum(s.emotional_valence for s in scenarios) / len(scenarios)
        avg_vividness = sum(s.vividness for s in scenarios) / len(scenarios)

        return {
            'optimism_bias': avg_valence > 0,
            'average_valence': avg_valence,
            'average_vividness': avg_vividness,
            'temporal_discounting': 'Distant futures less vivid',
            'interpretation': (
                f"Future thinking shows "
                f"{'optimism' if avg_valence > 0 else 'pessimism'} bias"
            )
        }

    def get_metrics(self) -> ProspectionMetrics:
        """Get prospection metrics."""
        if not self._scenarios:
            return ProspectionMetrics(
                total_simulations=0,
                average_vividness=0.0,
                average_plausibility=0.0,
                future_bias=0.0
            )

        scenarios = list(self._scenarios.values())

        return ProspectionMetrics(
            total_simulations=len(scenarios),
            average_vividness=sum(s.vividness for s in scenarios) / len(scenarios),
            average_plausibility=sum(s.plausibility.value for s in scenarios) / len(scenarios),
            future_bias=sum(s.emotional_valence for s in scenarios) / len(scenarios)
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'elements': len(self._element_store._elements),
            'scenarios': len(self._scenarios),
            'simulations': len(self._simulation_history)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_prospection_engine() -> ProspectionEngine:
    """Create prospection engine."""
    return ProspectionEngine()


def demonstrate_prospection() -> Dict[str, Any]:
    """Demonstrate prospection."""
    engine = create_prospection_engine()

    # Encode some memory elements
    engine.encode_memory_elements(
        "vacation_memory",
        people=["friend", "family"],
        places=["beach", "hotel"],
        objects=["camera", "suitcase"],
        actions=["swimming", "relaxing"]
    )

    # Imagine futures
    near = engine.imagine_future("Planning next vacation", TemporalDistance.NEAR)
    far = engine.imagine_future("Life in 10 years", TemporalDistance.FAR)

    # Set goals
    engine.set_goals(["travel more", "learn new skill"])
    goal_scenario = engine.imagine_goal_achieved("travel more")

    metrics = engine.get_metrics()
    asymmetry = engine.analyze_temporal_asymmetry()

    return {
        'near_future_vividness': near.vividness,
        'far_future_vividness': far.vividness,
        'goal_valence': goal_scenario.emotional_valence,
        'optimism_bias': asymmetry['optimism_bias'],
        'interpretation': (
            f"Near future ({near.vividness:.2f}) more vivid than "
            f"far future ({far.vividness:.2f})"
        )
    }


def get_prospection_facts() -> Dict[str, str]:
    """Get facts about prospection."""
    return {
        'schacter_addis': 'Constructive episodic simulation hypothesis',
        'shared_system': 'Memory and prospection share neural substrate',
        'hippocampus': 'Required for both remembering and imagining',
        'recombination': 'Future scenarios built from past elements',
        'optimism_bias': 'Future generally imagined positively',
        'temporal_discounting': 'Distant futures less vivid and detailed',
        'goal_directed': 'Prospection serves planning function',
        'mental_time_travel': 'Tulving: Ability to mentally travel in time'
    }

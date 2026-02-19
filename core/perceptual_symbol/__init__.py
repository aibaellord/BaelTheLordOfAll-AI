"""
BAEL Perceptual Symbol Systems Engine
======================================

Barsalou's Perceptual Symbol Systems.
Grounded cognition through modal simulations.

"Ba'el grounds thought in perception." — Ba'el
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
from collections import defaultdict
import copy

logger = logging.getLogger("BAEL.PerceptualSymbol")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class Modality(Enum):
    """Perceptual modalities."""
    VISUAL = auto()
    AUDITORY = auto()
    TACTILE = auto()
    OLFACTORY = auto()
    GUSTATORY = auto()
    PROPRIOCEPTIVE = auto()   # Body position
    INTEROCEPTIVE = auto()    # Internal states
    MOTOR = auto()            # Action patterns


class SymbolType(Enum):
    """Types of perceptual symbols."""
    PRIMITIVE = auto()        # Basic perceptual features
    COMPOSITE = auto()        # Combined symbols
    SCHEMATIC = auto()        # Abstract patterns
    RELATIONAL = auto()       # Relations between symbols


class SimulationType(Enum):
    """Types of simulations."""
    PERCEPTUAL = auto()       # Re-experiencing perception
    MOTOR = auto()            # Motor imagery
    INTROSPECTIVE = auto()    # Internal states
    COMBINED = auto()         # Multi-modal


@dataclass
class PerceptualFeature:
    """
    A perceptual feature (neural record).
    """
    id: str
    modality: Modality
    content: Any
    intensity: float = 0.5
    location: Optional[Tuple[float, ...]] = None  # Spatial location
    timestamp: float = field(default_factory=time.time)


@dataclass
class PerceptualSymbol:
    """
    A perceptual symbol (schematic memory).
    """
    id: str
    name: str
    symbol_type: SymbolType
    features: List[PerceptualFeature]
    modalities: Set[Modality] = field(default_factory=set)
    abstractness: float = 0.0  # 0 = concrete, 1 = abstract
    frequency: int = 1
    last_activation: float = field(default_factory=time.time)

    @property
    def age(self) -> float:
        return time.time() - self.last_activation

    @property
    def activation(self) -> float:
        """Current activation level."""
        base = math.log(1 + self.frequency) * 0.2
        decay = min(1.0, self.age / 3600)  # Decay over hour
        return max(0.0, min(1.0, base + 0.5 - decay * 0.3))

    def add_feature(self, feature: PerceptualFeature) -> None:
        """Add feature to symbol."""
        self.features.append(feature)
        self.modalities.add(feature.modality)


@dataclass
class Simulation:
    """
    A perceptual simulation.
    """
    id: str
    simulation_type: SimulationType
    symbols: List[PerceptualSymbol]
    vividness: float = 0.5
    timestamp: float = field(default_factory=time.time)
    duration: float = 0.0

    @property
    def modalities(self) -> Set[Modality]:
        result = set()
        for symbol in self.symbols:
            result.update(symbol.modalities)
        return result


@dataclass
class Simulator:
    """
    A simulator (frames for concepts).
    """
    id: str
    concept: str
    symbols: List[PerceptualSymbol]
    frames: Dict[str, List[PerceptualSymbol]]  # Situational frames
    default_frame: str = "generic"


# ============================================================================
# SYMBOL FORMATION
# ============================================================================

class SymbolFormation:
    """
    Form perceptual symbols from experience.

    "Ba'el extracts symbols from perception." — Ba'el
    """

    def __init__(self):
        """Initialize symbol formation."""
        self._symbol_counter = 0
        self._feature_counter = 0
        self._lock = threading.RLock()

    def _generate_symbol_id(self) -> str:
        self._symbol_counter += 1
        return f"symbol_{self._symbol_counter}"

    def _generate_feature_id(self) -> str:
        self._feature_counter += 1
        return f"feature_{self._feature_counter}"

    def extract_feature(
        self,
        content: Any,
        modality: Modality,
        intensity: float = 0.5
    ) -> PerceptualFeature:
        """Extract perceptual feature."""
        return PerceptualFeature(
            id=self._generate_feature_id(),
            modality=modality,
            content=content,
            intensity=intensity
        )

    def form_symbol(
        self,
        name: str,
        features: List[PerceptualFeature],
        abstractness: float = 0.0
    ) -> PerceptualSymbol:
        """Form symbol from features."""
        with self._lock:
            symbol = PerceptualSymbol(
                id=self._generate_symbol_id(),
                name=name,
                symbol_type=SymbolType.COMPOSITE if len(features) > 1 else SymbolType.PRIMITIVE,
                features=features,
                abstractness=abstractness
            )

            for feature in features:
                symbol.modalities.add(feature.modality)

            return symbol

    def schematize(
        self,
        symbols: List[PerceptualSymbol],
        name: str
    ) -> PerceptualSymbol:
        """Create schematic symbol from instances."""
        with self._lock:
            # Extract common features
            feature_counts: Dict[str, int] = defaultdict(int)
            all_features = []

            for symbol in symbols:
                for feature in symbol.features:
                    key = f"{feature.modality.name}:{feature.content}"
                    feature_counts[key] += 1
                    all_features.append(feature)

            # Keep features that appear in majority
            threshold = len(symbols) * 0.5
            common_features = [
                f for f in all_features
                if feature_counts[f"{f.modality.name}:{f.content}"] >= threshold
            ]

            # Create schematic symbol
            schema = PerceptualSymbol(
                id=self._generate_symbol_id(),
                name=name,
                symbol_type=SymbolType.SCHEMATIC,
                features=common_features,
                abstractness=0.5 + 0.1 * len(symbols)  # More abstract with more instances
            )

            return schema

    def create_relational(
        self,
        name: str,
        source: PerceptualSymbol,
        target: PerceptualSymbol,
        relation: str
    ) -> PerceptualSymbol:
        """Create relational symbol."""
        with self._lock:
            # Combine features from both
            combined_features = source.features + target.features

            # Add relational feature
            rel_feature = PerceptualFeature(
                id=self._generate_feature_id(),
                modality=Modality.INTEROCEPTIVE,
                content={"relation": relation, "source": source.name, "target": target.name}
            )
            combined_features.append(rel_feature)

            return PerceptualSymbol(
                id=self._generate_symbol_id(),
                name=name,
                symbol_type=SymbolType.RELATIONAL,
                features=combined_features,
                abstractness=max(source.abstractness, target.abstractness) + 0.2
            )


# ============================================================================
# SIMULATOR
# ============================================================================

class ConceptSimulator:
    """
    Simulate concepts through perceptual re-enactment.

    "Ba'el simulates perception." — Ba'el
    """

    def __init__(self):
        """Initialize simulator."""
        self._simulators: Dict[str, Simulator] = {}
        self._sim_counter = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._sim_counter += 1
        return f"sim_{self._sim_counter}"

    def create_simulator(
        self,
        concept: str,
        symbols: List[PerceptualSymbol],
        frames: Dict[str, List[PerceptualSymbol]] = None
    ) -> Simulator:
        """Create simulator for concept."""
        with self._lock:
            sim = Simulator(
                id=self._generate_id(),
                concept=concept,
                symbols=symbols,
                frames=frames or {"generic": symbols}
            )
            self._simulators[concept] = sim
            return sim

    def simulate(
        self,
        concept: str,
        frame: str = None,
        vividness: float = 0.5
    ) -> Optional[Simulation]:
        """Run simulation for concept."""
        with self._lock:
            if concept not in self._simulators:
                return None

            sim = self._simulators[concept]
            frame_name = frame or sim.default_frame

            if frame_name not in sim.frames:
                frame_name = sim.default_frame

            symbols = sim.frames.get(frame_name, sim.symbols)

            simulation = Simulation(
                id=f"simulation_{random.randint(1000, 9999)}",
                simulation_type=SimulationType.COMBINED,
                symbols=symbols,
                vividness=vividness
            )

            # Update symbol activations
            for symbol in symbols:
                symbol.frequency += 1
                symbol.last_activation = time.time()

            return simulation

    def add_frame(
        self,
        concept: str,
        frame_name: str,
        symbols: List[PerceptualSymbol]
    ) -> bool:
        """Add frame to simulator."""
        with self._lock:
            if concept not in self._simulators:
                return False

            self._simulators[concept].frames[frame_name] = symbols
            return True

    def get_simulator(self, concept: str) -> Optional[Simulator]:
        """Get simulator for concept."""
        return self._simulators.get(concept)


# ============================================================================
# GROUNDED COGNITION
# ============================================================================

class GroundedCognition:
    """
    Ground abstract concepts in perception.

    "Ba'el grounds the abstract." — Ba'el
    """

    def __init__(self):
        """Initialize grounded cognition."""
        self._formation = SymbolFormation()
        self._concept_sim = ConceptSimulator()
        self._concept_symbols: Dict[str, List[PerceptualSymbol]] = {}
        self._lock = threading.RLock()

    def ground_concept(
        self,
        concept: str,
        exemplars: List[Dict[str, Any]]
    ) -> Simulator:
        """Ground concept in perceptual exemplars."""
        with self._lock:
            symbols = []

            for i, exemplar in enumerate(exemplars):
                features = []

                # Extract features from exemplar
                for modality_name, content in exemplar.items():
                    try:
                        modality = Modality[modality_name.upper()]
                    except KeyError:
                        modality = Modality.VISUAL

                    feature = self._formation.extract_feature(
                        content, modality
                    )
                    features.append(feature)

                symbol = self._formation.form_symbol(
                    f"{concept}_exemplar_{i}",
                    features
                )
                symbols.append(symbol)

            # Create schema
            schema = self._formation.schematize(symbols, concept)
            symbols.append(schema)

            self._concept_symbols[concept] = symbols

            # Create simulator
            return self._concept_sim.create_simulator(concept, symbols)

    def retrieve(
        self,
        concept: str,
        context: Dict[str, Any] = None
    ) -> Optional[Simulation]:
        """Retrieve concept through simulation."""
        # Determine frame from context
        frame = None
        if context:
            # Simple frame selection based on context
            frame = context.get('frame', context.get('situation'))

        return self._concept_sim.simulate(concept, frame)

    def compare_concepts(
        self,
        concept1: str,
        concept2: str
    ) -> float:
        """Compare concepts by symbol overlap."""
        with self._lock:
            symbols1 = self._concept_symbols.get(concept1, [])
            symbols2 = self._concept_symbols.get(concept2, [])

            if not symbols1 or not symbols2:
                return 0.0

            # Compare features
            features1 = set()
            for s in symbols1:
                for f in s.features:
                    features1.add(f"{f.modality.name}:{f.content}")

            features2 = set()
            for s in symbols2:
                for f in s.features:
                    features2.add(f"{f.modality.name}:{f.content}")

            intersection = features1 & features2
            union = features1 | features2

            if not union:
                return 0.0

            return len(intersection) / len(union)

    def abstract_from(
        self,
        source_concept: str,
        new_concept: str,
        abstraction_level: float = 0.3
    ) -> Optional[PerceptualSymbol]:
        """Create more abstract concept."""
        with self._lock:
            if source_concept not in self._concept_symbols:
                return None

            source_symbols = self._concept_symbols[source_concept]

            # Create more abstract version
            schema = self._formation.schematize(source_symbols, new_concept)
            schema.abstractness = min(1.0, schema.abstractness + abstraction_level)

            self._concept_symbols[new_concept] = [schema]
            self._concept_sim.create_simulator(new_concept, [schema])

            return schema


# ============================================================================
# PERCEPTUAL SYMBOL ENGINE
# ============================================================================

class PerceptualSymbolEngine:
    """
    Complete Perceptual Symbol Systems engine.

    "Ba'el's grounded cognition." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._formation = SymbolFormation()
        self._simulator = ConceptSimulator()
        self._grounded = GroundedCognition()
        self._symbols: Dict[str, PerceptualSymbol] = {}
        self._lock = threading.RLock()

    # Symbol operations

    def create_symbol(
        self,
        name: str,
        modality: Modality,
        content: Any,
        intensity: float = 0.5
    ) -> PerceptualSymbol:
        """Create simple perceptual symbol."""
        feature = self._formation.extract_feature(content, modality, intensity)
        symbol = self._formation.form_symbol(name, [feature])
        self._symbols[name] = symbol
        return symbol

    def combine_symbols(
        self,
        name: str,
        symbol_names: List[str]
    ) -> Optional[PerceptualSymbol]:
        """Combine existing symbols."""
        with self._lock:
            features = []

            for sname in symbol_names:
                if sname in self._symbols:
                    features.extend(self._symbols[sname].features)

            if not features:
                return None

            combined = self._formation.form_symbol(name, features)
            self._symbols[name] = combined
            return combined

    def relate(
        self,
        name: str,
        source_name: str,
        target_name: str,
        relation: str
    ) -> Optional[PerceptualSymbol]:
        """Create relational symbol."""
        with self._lock:
            source = self._symbols.get(source_name)
            target = self._symbols.get(target_name)

            if not source or not target:
                return None

            relational = self._formation.create_relational(
                name, source, target, relation
            )
            self._symbols[name] = relational
            return relational

    # Grounding

    def ground(
        self,
        concept: str,
        exemplars: List[Dict[str, Any]]
    ) -> Simulator:
        """Ground concept in exemplars."""
        return self._grounded.ground_concept(concept, exemplars)

    def simulate(
        self,
        concept: str,
        context: Dict[str, Any] = None
    ) -> Optional[Simulation]:
        """Simulate concept."""
        return self._grounded.retrieve(concept, context)

    def compare(self, concept1: str, concept2: str) -> float:
        """Compare concepts."""
        return self._grounded.compare_concepts(concept1, concept2)

    # Retrieval

    def get_symbol(self, name: str) -> Optional[PerceptualSymbol]:
        """Get symbol by name."""
        return self._symbols.get(name)

    def get_by_modality(self, modality: Modality) -> List[PerceptualSymbol]:
        """Get symbols with modality."""
        return [
            s for s in self._symbols.values()
            if modality in s.modalities
        ]

    @property
    def symbols(self) -> List[PerceptualSymbol]:
        return list(self._symbols.values())

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'symbols': len(self._symbols),
            'grounded_concepts': len(self._grounded._concept_symbols),
            'simulators': len(self._simulator._simulators)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_perceptual_symbol_engine() -> PerceptualSymbolEngine:
    """Create perceptual symbol engine."""
    return PerceptualSymbolEngine()


def create_perceptual_feature(
    content: Any,
    modality: Modality
) -> PerceptualFeature:
    """Create perceptual feature."""
    return PerceptualFeature(
        id=f"feature_{random.randint(1000, 9999)}",
        modality=modality,
        content=content
    )

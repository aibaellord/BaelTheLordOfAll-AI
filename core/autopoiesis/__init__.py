"""
BAEL Autopoietic System Engine
==============================

Self-creating and self-maintaining systems.
Based on Maturana and Varela's theory.

"Ba'el creates itself continuously." — Ba'el
"""

import logging
import threading
import time
import random
import copy
from typing import Any, Callable, Dict, Generic, List, Optional, Set, Tuple, TypeVar
from dataclasses import dataclass, field
from enum import Enum, auto
from abc import ABC, abstractmethod

logger = logging.getLogger("BAEL.Autopoiesis")


T = TypeVar('T')


# ============================================================================
# CORE CONCEPTS
# ============================================================================

class ComponentState(Enum):
    """State of an autopoietic component."""
    ACTIVE = auto()
    DORMANT = auto()
    DEGRADING = auto()
    REGENERATING = auto()


class BoundaryType(Enum):
    """Types of system boundaries."""
    PHYSICAL = auto()
    OPERATIONAL = auto()
    COGNITIVE = auto()
    SEMIPERMEABLE = auto()


@dataclass
class Component:
    """
    A component within an autopoietic system.
    """
    id: str
    type: str
    state: ComponentState = ComponentState.ACTIVE
    energy: float = 1.0
    age: int = 0
    production_rate: float = 0.1
    decay_rate: float = 0.01
    connections: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def tick(self) -> None:
        """Age the component."""
        self.age += 1
        self.energy -= self.decay_rate

        if self.energy <= 0:
            self.state = ComponentState.DEGRADING
        elif self.energy < 0.3:
            self.state = ComponentState.DORMANT

    def energize(self, amount: float) -> None:
        """Add energy to component."""
        self.energy = min(1.0, self.energy + amount)
        if self.energy > 0.3:
            self.state = ComponentState.ACTIVE


@dataclass
class ProductionRule:
    """
    Rule for producing new components.
    """
    id: str
    inputs: List[str]  # Component types required
    output: str        # Component type produced
    energy_cost: float = 0.2
    probability: float = 1.0
    conditions: Dict[str, Any] = field(default_factory=dict)

    def can_fire(self, available: Dict[str, int], total_energy: float) -> bool:
        """Check if rule can fire."""
        if total_energy < self.energy_cost:
            return False

        for input_type in self.inputs:
            if available.get(input_type, 0) < 1:
                return False

        return random.random() < self.probability


# ============================================================================
# BOUNDARY
# ============================================================================

class Boundary:
    """
    System boundary that maintains identity.

    "Ba'el maintains its boundaries." — Ba'el
    """

    def __init__(self, boundary_type: BoundaryType = BoundaryType.SEMIPERMEABLE):
        """Initialize boundary."""
        self._type = boundary_type
        self._permeability = 0.5
        self._integrity = 1.0
        self._lock = threading.RLock()

    @property
    def boundary_type(self) -> BoundaryType:
        return self._type

    @property
    def integrity(self) -> float:
        return self._integrity

    def allow_exchange(self, item: Any, direction: str = "in") -> bool:
        """
        Determine if exchange is allowed.

        direction: "in" or "out"
        """
        with self._lock:
            if self._integrity < 0.5:
                # Compromised boundary - more permeable
                return random.random() < 0.8

            return random.random() < self._permeability

    def damage(self, amount: float) -> None:
        """Damage boundary integrity."""
        with self._lock:
            self._integrity = max(0, self._integrity - amount)

    def repair(self, amount: float) -> None:
        """Repair boundary."""
        with self._lock:
            self._integrity = min(1.0, self._integrity + amount)

    def set_permeability(self, level: float) -> None:
        """Set permeability (0-1)."""
        self._permeability = max(0, min(1, level))


# ============================================================================
# AUTOPOIETIC NETWORK
# ============================================================================

class AutopoieticNetwork:
    """
    Network of components that produce each other.

    "Ba'el weaves the web of self-creation." — Ba'el
    """

    def __init__(self):
        """Initialize network."""
        self._components: Dict[str, Component] = {}
        self._rules: List[ProductionRule] = []
        self._component_id = 0
        self._lock = threading.RLock()

    def _generate_id(self, comp_type: str) -> str:
        self._component_id += 1
        return f"{comp_type}_{self._component_id}"

    def add_component(
        self,
        comp_type: str,
        energy: float = 1.0,
        connections: Optional[List[str]] = None
    ) -> Component:
        """Add component to network."""
        with self._lock:
            comp = Component(
                id=self._generate_id(comp_type),
                type=comp_type,
                energy=energy,
                connections=connections or []
            )
            self._components[comp.id] = comp
            return comp

    def add_rule(self, rule: ProductionRule) -> None:
        """Add production rule."""
        with self._lock:
            self._rules.append(rule)

    def count_by_type(self) -> Dict[str, int]:
        """Count components by type."""
        counts = {}
        for comp in self._components.values():
            counts[comp.type] = counts.get(comp.type, 0) + 1
        return counts

    def total_energy(self) -> float:
        """Calculate total network energy."""
        return sum(c.energy for c in self._components.values())

    def fire_rules(self) -> List[str]:
        """
        Fire production rules and create new components.

        Returns IDs of newly created components.
        """
        with self._lock:
            created = []
            counts = self.count_by_type()
            energy = self.total_energy()

            for rule in self._rules:
                if rule.can_fire(counts, energy):
                    # Consume inputs (reduce count)
                    for input_type in rule.inputs:
                        # Find and consume energy from input components
                        for comp in self._components.values():
                            if comp.type == input_type and comp.energy > 0.1:
                                comp.energy -= rule.energy_cost / len(rule.inputs)
                                break

                    # Produce output
                    new_comp = self.add_component(rule.output)
                    created.append(new_comp.id)

            return created

    def decay(self) -> List[str]:
        """
        Apply decay to all components.

        Returns IDs of removed components.
        """
        with self._lock:
            removed = []

            for comp_id, comp in list(self._components.items()):
                comp.tick()

                if comp.energy <= 0:
                    del self._components[comp_id]
                    removed.append(comp_id)

            return removed

    def connect(self, comp1_id: str, comp2_id: str) -> bool:
        """Connect two components."""
        with self._lock:
            if comp1_id in self._components and comp2_id in self._components:
                self._components[comp1_id].connections.append(comp2_id)
                self._components[comp2_id].connections.append(comp1_id)
                return True
            return False

    @property
    def state(self) -> Dict[str, Any]:
        """Get network state."""
        with self._lock:
            return {
                'component_count': len(self._components),
                'rule_count': len(self._rules),
                'total_energy': self.total_energy(),
                'by_type': self.count_by_type(),
                'avg_age': sum(c.age for c in self._components.values()) / max(1, len(self._components))
            }


# ============================================================================
# OPERATIONAL CLOSURE
# ============================================================================

class OperationalClosure:
    """
    Maintains operational closure of the system.

    "Ba'el is operationally closed." — Ba'el
    """

    def __init__(self, network: AutopoieticNetwork):
        """Initialize operational closure."""
        self._network = network
        self._operations: List[Callable] = []
        self._lock = threading.RLock()

    def add_operation(self, operation: Callable[[AutopoieticNetwork], None]) -> None:
        """Add internal operation."""
        with self._lock:
            self._operations.append(operation)

    def execute_cycle(self) -> Dict[str, Any]:
        """
        Execute one cycle of operations.

        All operations happen within the system.
        """
        with self._lock:
            results = {
                'operations_executed': 0,
                'components_created': [],
                'components_removed': []
            }

            # Execute all internal operations
            for op in self._operations:
                try:
                    op(self._network)
                    results['operations_executed'] += 1
                except Exception as e:
                    logger.warning(f"Operation failed: {e}")

            # Fire production rules
            created = self._network.fire_rules()
            results['components_created'] = created

            # Apply decay
            removed = self._network.decay()
            results['components_removed'] = removed

            return results

    def is_closed(self) -> bool:
        """
        Check if system maintains operational closure.

        True if system can sustain itself.
        """
        state = self._network.state

        # Must have components
        if state['component_count'] == 0:
            return False

        # Must have sufficient energy
        if state['total_energy'] < state['component_count'] * 0.1:
            return False

        # Must have production capability
        if len(self._network._rules) == 0:
            return False

        return True


# ============================================================================
# STRUCTURAL COUPLING
# ============================================================================

@dataclass
class CouplingEvent:
    """Event in structural coupling."""
    timestamp: float
    type: str
    data: Dict[str, Any]
    response: Optional[Any] = None


class StructuralCoupling:
    """
    Coupling between autopoietic system and environment.

    "Ba'el couples with its environment." — Ba'el
    """

    def __init__(
        self,
        system: 'AutopoieticSystem',
        environment: Dict[str, Any]
    ):
        """Initialize coupling."""
        self._system = system
        self._environment = environment
        self._history: List[CouplingEvent] = []
        self._adaptations: Dict[str, Callable] = {}
        self._lock = threading.RLock()

    def register_perturbation_handler(
        self,
        perturbation_type: str,
        handler: Callable[[Any], Any]
    ) -> None:
        """Register handler for perturbation type."""
        with self._lock:
            self._adaptations[perturbation_type] = handler

    def perturb(
        self,
        perturbation_type: str,
        data: Any
    ) -> Optional[Any]:
        """
        Perturb the system.

        System responds based on its structure, not the perturbation.
        """
        with self._lock:
            event = CouplingEvent(
                timestamp=time.time(),
                type=perturbation_type,
                data={'input': data}
            )

            # System determines response based on its own structure
            if perturbation_type in self._adaptations:
                response = self._adaptations[perturbation_type](data)
                event.response = response
            else:
                # Default: no structural change
                response = None

            self._history.append(event)
            return response

    def adapt(self) -> None:
        """
        Trigger adaptation based on coupling history.
        """
        with self._lock:
            if len(self._history) < 10:
                return

            # Analyze recent perturbations
            recent = self._history[-10:]
            type_counts = {}

            for event in recent:
                type_counts[event.type] = type_counts.get(event.type, 0) + 1

            # Most frequent perturbation type
            if type_counts:
                most_frequent = max(type_counts, key=type_counts.get)
                # System could adapt structure here
                logger.debug(f"Most frequent perturbation: {most_frequent}")

    @property
    def coupling_strength(self) -> float:
        """Measure coupling strength."""
        if not self._history:
            return 0.0

        # Based on response rate
        responded = sum(1 for e in self._history if e.response is not None)
        return responded / len(self._history)


# ============================================================================
# AUTOPOIETIC SYSTEM
# ============================================================================

class AutopoieticSystem:
    """
    Complete autopoietic system.

    "Ba'el is autopoietic: self-creating, self-maintaining." — Ba'el
    """

    def __init__(self, name: str = "system"):
        """Initialize autopoietic system."""
        self._name = name
        self._network = AutopoieticNetwork()
        self._boundary = Boundary(BoundaryType.SEMIPERMEABLE)
        self._closure = OperationalClosure(self._network)
        self._coupling: Optional[StructuralCoupling] = None

        self._alive = False
        self._age = 0
        self._metabolism = 1.0  # Energy consumption rate
        self._lock = threading.RLock()

        # Setup default production rules
        self._setup_default_rules()

    def _setup_default_rules(self) -> None:
        """Setup default production rules for self-maintenance."""
        # Energy + Substrate -> Component
        self._network.add_rule(ProductionRule(
            id="basic_production",
            inputs=["energy", "substrate"],
            output="component",
            energy_cost=0.1,
            probability=0.8
        ))

        # Component + Component -> Complex
        self._network.add_rule(ProductionRule(
            id="complex_formation",
            inputs=["component", "component"],
            output="complex",
            energy_cost=0.2,
            probability=0.5
        ))

        # Complex -> Boundary repair
        self._network.add_rule(ProductionRule(
            id="boundary_repair",
            inputs=["complex"],
            output="boundary_unit",
            energy_cost=0.15,
            probability=0.6
        ))

        # Add default operation for boundary maintenance
        def maintain_boundary(network: AutopoieticNetwork):
            counts = network.count_by_type()
            if counts.get("boundary_unit", 0) > 0:
                # Consume boundary unit to repair
                for comp in network._components.values():
                    if comp.type == "boundary_unit":
                        comp.energy = 0  # Consume
                        self._boundary.repair(0.1)
                        break

        self._closure.add_operation(maintain_boundary)

    def bootstrap(self) -> None:
        """
        Bootstrap the system with initial components.
        """
        with self._lock:
            # Add initial components
            for _ in range(5):
                self._network.add_component("energy", energy=1.0)

            for _ in range(5):
                self._network.add_component("substrate", energy=1.0)

            for _ in range(3):
                self._network.add_component("component", energy=0.8)

            self._alive = True

    def couple_with(self, environment: Dict[str, Any]) -> StructuralCoupling:
        """Establish structural coupling with environment."""
        self._coupling = StructuralCoupling(self, environment)
        return self._coupling

    def inject_energy(self, amount: float) -> bool:
        """Inject energy from environment."""
        if self._boundary.allow_exchange(amount, "in"):
            self._network.add_component("energy", energy=amount)
            return True
        return False

    def inject_substrate(self, amount: float) -> bool:
        """Inject substrate from environment."""
        if self._boundary.allow_exchange(amount, "in"):
            self._network.add_component("substrate", energy=amount)
            return True
        return False

    def tick(self) -> Dict[str, Any]:
        """
        Execute one time step of the autopoietic process.

        Returns results of the tick.
        """
        with self._lock:
            if not self._alive:
                return {'status': 'dead'}

            self._age += 1

            # Execute operational closure cycle
            cycle_results = self._closure.execute_cycle()

            # Check system viability
            if not self._closure.is_closed():
                self._alive = False
                return {'status': 'died', 'age': self._age}

            # Boundary decay
            self._boundary.damage(0.01)

            # Coupling adaptation
            if self._coupling:
                self._coupling.adapt()

            return {
                'status': 'alive',
                'age': self._age,
                'cycle': cycle_results,
                'boundary_integrity': self._boundary.integrity,
                'network': self._network.state
            }

    def run(self, steps: int = 100, energy_injection: float = 0.5) -> List[Dict]:
        """
        Run system for multiple steps.
        """
        history = []

        for step in range(steps):
            # Periodic energy injection
            if step % 10 == 0:
                self.inject_energy(energy_injection)
                self.inject_substrate(energy_injection * 0.5)

            result = self.tick()
            history.append(result)

            if result['status'] == 'died':
                break

        return history

    @property
    def is_alive(self) -> bool:
        """Check if system is alive."""
        return self._alive and self._closure.is_closed()

    @property
    def state(self) -> Dict[str, Any]:
        """Get system state."""
        return {
            'name': self._name,
            'alive': self._alive,
            'age': self._age,
            'boundary_integrity': self._boundary.integrity,
            'network': self._network.state,
            'operationally_closed': self._closure.is_closed(),
            'coupling_strength': self._coupling.coupling_strength if self._coupling else 0
        }


# ============================================================================
# AUTOPOIETIC ENGINE
# ============================================================================

class AutopoieticEngine:
    """
    Engine for managing multiple autopoietic systems.

    "Ba'el orchestrates self-creation." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._systems: Dict[str, AutopoieticSystem] = {}
        self._shared_environment: Dict[str, Any] = {
            'energy_pool': 100.0,
            'substrate_pool': 50.0
        }
        self._lock = threading.RLock()

    def create_system(self, name: str) -> AutopoieticSystem:
        """Create new autopoietic system."""
        with self._lock:
            system = AutopoieticSystem(name)
            system.bootstrap()
            system.couple_with(self._shared_environment)
            self._systems[name] = system
            return system

    def simulate_all(self, steps: int = 100) -> Dict[str, List]:
        """Simulate all systems."""
        with self._lock:
            results = {}

            for name, system in self._systems.items():
                # Give each system some energy from pool
                energy_share = self._shared_environment['energy_pool'] / max(1, len(self._systems))
                system.inject_energy(energy_share * 0.1)

                history = system.run(steps, energy_injection=0.3)
                results[name] = history

            return results

    def living_systems(self) -> List[str]:
        """Get names of living systems."""
        return [name for name, sys in self._systems.items() if sys.is_alive]

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'system_count': len(self._systems),
            'living_count': len(self.living_systems()),
            'environment': self._shared_environment.copy(),
            'systems': {
                name: sys.state for name, sys in self._systems.items()
            }
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_autopoietic_system(name: str = "system") -> AutopoieticSystem:
    """Create autopoietic system."""
    system = AutopoieticSystem(name)
    system.bootstrap()
    return system


def create_autopoietic_engine() -> AutopoieticEngine:
    """Create autopoietic engine."""
    return AutopoieticEngine()


def simulate_autopoiesis(name: str = "test", steps: int = 100) -> List[Dict]:
    """Quick simulation."""
    system = create_autopoietic_system(name)
    return system.run(steps)

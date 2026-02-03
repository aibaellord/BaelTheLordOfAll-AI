#!/usr/bin/env python3
"""
BAEL - Counterfactual Engine
Advanced counterfactual reasoning and what-if analysis.

Features:
- Counterfactual generation
- Causal intervention
- Alternative world modeling
- Outcome prediction
- Closest possible world search
- Contrastive explanation
"""

import asyncio
import copy
import hashlib
import math
import random
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import (Any, Callable, Dict, Generic, List, Optional, Set, Tuple,
                    Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class InterventionType(Enum):
    """Types of causal interventions."""
    SET_VALUE = "set_value"
    REMOVE = "remove"
    ADD = "add"
    MODIFY = "modify"
    PREVENT = "prevent"


class WorldDistance(Enum):
    """Distance metrics for possible worlds."""
    HAMMING = "hamming"
    WEIGHTED = "weighted"
    STRUCTURAL = "structural"
    CAUSAL = "causal"


class CounterfactualType(Enum):
    """Types of counterfactuals."""
    PREVENTION = "prevention"  # What if X didn't happen?
    SUBSTITUTION = "substitution"  # What if Y instead of X?
    ADDITION = "addition"  # What if X also happened?
    INTENSIFICATION = "intensification"  # What if more X?


class EvaluationStatus(Enum):
    """Status of counterfactual evaluation."""
    PENDING = "pending"
    EVALUATING = "evaluating"
    COMPLETE = "complete"
    FAILED = "failed"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class Variable:
    """A variable in the causal model."""
    var_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    value: Any = None
    domain: List[Any] = field(default_factory=list)
    is_exogenous: bool = False


@dataclass
class CausalLink:
    """A causal link between variables."""
    link_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source: str = ""
    target: str = ""
    strength: float = 1.0
    mechanism: Optional[Callable] = None


@dataclass
class Intervention:
    """An intervention on the causal model."""
    intervention_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    variable_id: str = ""
    intervention_type: InterventionType = InterventionType.SET_VALUE
    new_value: Any = None
    description: str = ""


@dataclass
class PossibleWorld:
    """A possible world (alternative state of affairs)."""
    world_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    variable_states: Dict[str, Any] = field(default_factory=dict)
    interventions: List[str] = field(default_factory=list)
    distance_from_actual: float = 0.0


@dataclass
class Counterfactual:
    """A counterfactual statement."""
    cf_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    antecedent: str = ""  # "If X had happened..."
    consequent: str = ""  # "Then Y would have..."
    cf_type: CounterfactualType = CounterfactualType.PREVENTION
    actual_antecedent: Any = None
    counterfactual_antecedent: Any = None
    actual_consequent: Any = None
    predicted_consequent: Any = None


@dataclass
class ContrastiveExplanation:
    """A contrastive explanation."""
    explanation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    fact: str = ""
    foil: str = ""
    difference_makers: List[str] = field(default_factory=list)
    explanation: str = ""


@dataclass
class EvaluationResult:
    """Result of counterfactual evaluation."""
    result_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    counterfactual_id: str = ""
    is_true: bool = False
    confidence: float = 0.0
    closest_world: Optional[PossibleWorld] = None
    reasoning: str = ""


# =============================================================================
# CAUSAL MODEL
# =============================================================================

class CausalModel:
    """Structural causal model for counterfactual reasoning."""

    def __init__(self):
        self._variables: Dict[str, Variable] = {}
        self._links: Dict[str, CausalLink] = {}
        self._parents: Dict[str, List[str]] = defaultdict(list)
        self._children: Dict[str, List[str]] = defaultdict(list)
        self._mechanisms: Dict[str, Callable] = {}

    def add_variable(
        self,
        name: str,
        value: Any = None,
        domain: Optional[List[Any]] = None,
        is_exogenous: bool = False
    ) -> Variable:
        """Add a variable to the model."""
        var = Variable(
            name=name,
            value=value,
            domain=domain or [],
            is_exogenous=is_exogenous
        )
        self._variables[var.var_id] = var
        return var

    def add_link(
        self,
        source_id: str,
        target_id: str,
        strength: float = 1.0,
        mechanism: Optional[Callable] = None
    ) -> Optional[CausalLink]:
        """Add a causal link."""
        if source_id not in self._variables or target_id not in self._variables:
            return None

        link = CausalLink(
            source=source_id,
            target=target_id,
            strength=strength,
            mechanism=mechanism
        )

        self._links[link.link_id] = link
        self._parents[target_id].append(source_id)
        self._children[source_id].append(target_id)

        if mechanism:
            self._mechanisms[target_id] = mechanism

        return link

    def get_variable(self, var_id: str) -> Optional[Variable]:
        """Get a variable."""
        return self._variables.get(var_id)

    def get_parents(self, var_id: str) -> List[Variable]:
        """Get parent variables."""
        parent_ids = self._parents.get(var_id, [])
        return [self._variables[pid] for pid in parent_ids if pid in self._variables]

    def get_children(self, var_id: str) -> List[Variable]:
        """Get child variables."""
        child_ids = self._children.get(var_id, [])
        return [self._variables[cid] for cid in child_ids if cid in self._variables]

    def get_descendants(self, var_id: str) -> Set[str]:
        """Get all descendants of a variable."""
        descendants = set()
        queue = list(self._children.get(var_id, []))

        while queue:
            child_id = queue.pop(0)
            if child_id not in descendants:
                descendants.add(child_id)
                queue.extend(self._children.get(child_id, []))

        return descendants

    def topological_sort(self) -> List[str]:
        """Get topological ordering of variables."""
        in_degree = {vid: len(self._parents[vid]) for vid in self._variables}
        queue = [vid for vid, deg in in_degree.items() if deg == 0]
        order = []

        while queue:
            var_id = queue.pop(0)
            order.append(var_id)

            for child_id in self._children.get(var_id, []):
                in_degree[child_id] -= 1
                if in_degree[child_id] == 0:
                    queue.append(child_id)

        return order

    def get_current_state(self) -> Dict[str, Any]:
        """Get current state of all variables."""
        return {
            vid: var.value
            for vid, var in self._variables.items()
        }

    def set_state(self, state: Dict[str, Any]) -> None:
        """Set state of variables."""
        for vid, value in state.items():
            if vid in self._variables:
                self._variables[vid].value = value


# =============================================================================
# INTERVENTION MANAGER
# =============================================================================

class InterventionManager:
    """Manage interventions on causal model."""

    def __init__(self, causal_model: CausalModel):
        self._model = causal_model
        self._interventions: Dict[str, Intervention] = {}

    def create_intervention(
        self,
        variable_id: str,
        intervention_type: InterventionType,
        new_value: Any = None,
        description: str = ""
    ) -> Intervention:
        """Create an intervention."""
        intervention = Intervention(
            variable_id=variable_id,
            intervention_type=intervention_type,
            new_value=new_value,
            description=description
        )
        self._interventions[intervention.intervention_id] = intervention
        return intervention

    def apply_intervention(
        self,
        intervention: Intervention,
        state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply intervention to a state."""
        new_state = state.copy()
        var_id = intervention.variable_id

        if intervention.intervention_type == InterventionType.SET_VALUE:
            new_state[var_id] = intervention.new_value
        elif intervention.intervention_type == InterventionType.REMOVE:
            if var_id in new_state:
                del new_state[var_id]
        elif intervention.intervention_type == InterventionType.MODIFY:
            if var_id in new_state and callable(intervention.new_value):
                new_state[var_id] = intervention.new_value(new_state[var_id])

        return new_state

    def get_intervention(self, intervention_id: str) -> Optional[Intervention]:
        """Get an intervention."""
        return self._interventions.get(intervention_id)


# =============================================================================
# WORLD GENERATOR
# =============================================================================

class WorldGenerator:
    """Generate possible worlds."""

    def __init__(
        self,
        causal_model: CausalModel,
        intervention_manager: InterventionManager
    ):
        self._model = causal_model
        self._interventions = intervention_manager
        self._worlds: Dict[str, PossibleWorld] = {}

    def create_world(
        self,
        interventions: List[Intervention],
        base_state: Optional[Dict[str, Any]] = None
    ) -> PossibleWorld:
        """Create a possible world from interventions."""
        # Start with current or base state
        state = base_state or self._model.get_current_state()

        # Apply interventions
        for intervention in interventions:
            state = self._interventions.apply_intervention(intervention, state)

        # Propagate changes
        state = self._propagate_changes(state, interventions)

        world = PossibleWorld(
            variable_states=state,
            interventions=[i.intervention_id for i in interventions]
        )

        self._worlds[world.world_id] = world
        return world

    def _propagate_changes(
        self,
        state: Dict[str, Any],
        interventions: List[Intervention]
    ) -> Dict[str, Any]:
        """Propagate changes through causal model."""
        # Get intervened variables
        intervened = {i.variable_id for i in interventions}

        # Process in topological order
        for var_id in self._model.topological_sort():
            # Skip intervened variables
            if var_id in intervened:
                continue

            # Get parent values
            parents = self._model.get_parents(var_id)
            if parents:
                parent_values = {p.var_id: state.get(p.var_id) for p in parents}

                # Apply mechanism if available
                var = self._model.get_variable(var_id)
                if var and var_id in self._model._mechanisms:
                    mechanism = self._model._mechanisms[var_id]
                    try:
                        state[var_id] = mechanism(parent_values)
                    except Exception:
                        pass  # Keep current value

        return state

    def calculate_distance(
        self,
        world: PossibleWorld,
        metric: WorldDistance = WorldDistance.HAMMING
    ) -> float:
        """Calculate distance from actual world."""
        actual = self._model.get_current_state()
        counterfactual = world.variable_states

        if metric == WorldDistance.HAMMING:
            return self._hamming_distance(actual, counterfactual)
        elif metric == WorldDistance.WEIGHTED:
            return self._weighted_distance(actual, counterfactual)
        elif metric == WorldDistance.STRUCTURAL:
            return self._structural_distance(actual, counterfactual)
        else:
            return self._hamming_distance(actual, counterfactual)

    def _hamming_distance(
        self,
        state1: Dict[str, Any],
        state2: Dict[str, Any]
    ) -> float:
        """Calculate Hamming distance."""
        all_vars = set(state1.keys()) | set(state2.keys())
        differences = sum(
            1 for var in all_vars
            if state1.get(var) != state2.get(var)
        )
        return differences / len(all_vars) if all_vars else 0.0

    def _weighted_distance(
        self,
        state1: Dict[str, Any],
        state2: Dict[str, Any],
        weights: Optional[Dict[str, float]] = None
    ) -> float:
        """Calculate weighted distance."""
        weights = weights or {}
        total_weight = 0.0
        weighted_diff = 0.0

        for var_id in set(state1.keys()) | set(state2.keys()):
            weight = weights.get(var_id, 1.0)
            total_weight += weight

            if state1.get(var_id) != state2.get(var_id):
                weighted_diff += weight

        return weighted_diff / total_weight if total_weight > 0 else 0.0

    def _structural_distance(
        self,
        state1: Dict[str, Any],
        state2: Dict[str, Any]
    ) -> float:
        """Calculate structural distance based on causal graph."""
        changes = [
            var for var in state1
            if state1.get(var) != state2.get(var)
        ]

        # Count total variables affected including descendants
        affected = set(changes)
        for var_id in changes:
            affected |= self._model.get_descendants(var_id)

        total_vars = len(self._model._variables)
        return len(affected) / total_vars if total_vars > 0 else 0.0

    def get_world(self, world_id: str) -> Optional[PossibleWorld]:
        """Get a world."""
        return self._worlds.get(world_id)


# =============================================================================
# COUNTERFACTUAL REASONER
# =============================================================================

class CounterfactualReasoner:
    """Reason about counterfactuals."""

    def __init__(
        self,
        causal_model: CausalModel,
        world_generator: WorldGenerator,
        intervention_manager: InterventionManager
    ):
        self._model = causal_model
        self._worlds = world_generator
        self._interventions = intervention_manager
        self._counterfactuals: Dict[str, Counterfactual] = {}

    def create_counterfactual(
        self,
        antecedent: str,
        consequent: str,
        cf_type: CounterfactualType = CounterfactualType.PREVENTION,
        actual_antecedent: Any = None,
        counterfactual_antecedent: Any = None
    ) -> Counterfactual:
        """Create a counterfactual."""
        # Get actual consequent value
        actual_consequent = None

        cf = Counterfactual(
            antecedent=antecedent,
            consequent=consequent,
            cf_type=cf_type,
            actual_antecedent=actual_antecedent,
            counterfactual_antecedent=counterfactual_antecedent,
            actual_consequent=actual_consequent
        )

        self._counterfactuals[cf.cf_id] = cf
        return cf

    def evaluate(
        self,
        counterfactual: Counterfactual,
        antecedent_var_id: str,
        consequent_var_id: str
    ) -> EvaluationResult:
        """Evaluate a counterfactual."""
        # Get actual state
        actual_state = self._model.get_current_state()
        counterfactual.actual_antecedent = actual_state.get(antecedent_var_id)
        counterfactual.actual_consequent = actual_state.get(consequent_var_id)

        # Create intervention
        intervention = self._interventions.create_intervention(
            antecedent_var_id,
            InterventionType.SET_VALUE,
            counterfactual.counterfactual_antecedent,
            f"Set {antecedent_var_id} to {counterfactual.counterfactual_antecedent}"
        )

        # Generate counterfactual world
        cf_world = self._worlds.create_world([intervention])

        # Get predicted consequent
        predicted = cf_world.variable_states.get(consequent_var_id)
        counterfactual.predicted_consequent = predicted

        # Calculate distance
        distance = self._worlds.calculate_distance(cf_world)
        cf_world.distance_from_actual = distance

        # Determine if counterfactual is true
        # (consequent different from actual)
        is_true = predicted != counterfactual.actual_consequent
        confidence = 1.0 - distance

        return EvaluationResult(
            counterfactual_id=counterfactual.cf_id,
            is_true=is_true,
            confidence=confidence,
            closest_world=cf_world,
            reasoning=f"Changing {antecedent_var_id} from "
                     f"{counterfactual.actual_antecedent} to "
                     f"{counterfactual.counterfactual_antecedent} "
                     f"{'would' if is_true else 'would not'} change "
                     f"{consequent_var_id}"
        )

    def find_closest_world(
        self,
        target_state: Dict[str, Any],
        max_interventions: int = 3
    ) -> Optional[PossibleWorld]:
        """Find closest world where target state holds."""
        actual = self._model.get_current_state()

        # Find variables that differ
        diff_vars = [
            var for var in target_state
            if actual.get(var) != target_state.get(var)
        ]

        if len(diff_vars) > max_interventions:
            diff_vars = diff_vars[:max_interventions]

        # Create interventions
        interventions = []
        for var_id in diff_vars:
            intervention = self._interventions.create_intervention(
                var_id,
                InterventionType.SET_VALUE,
                target_state[var_id]
            )
            interventions.append(intervention)

        # Create world
        world = self._worlds.create_world(interventions)
        world.distance_from_actual = self._worlds.calculate_distance(world)

        return world

    def get_counterfactual(self, cf_id: str) -> Optional[Counterfactual]:
        """Get a counterfactual."""
        return self._counterfactuals.get(cf_id)


# =============================================================================
# CONTRASTIVE EXPLAINER
# =============================================================================

class ContrastiveExplainer:
    """Generate contrastive explanations."""

    def __init__(
        self,
        causal_model: CausalModel,
        counterfactual_reasoner: CounterfactualReasoner
    ):
        self._model = causal_model
        self._cf_reasoner = counterfactual_reasoner
        self._explanations: Dict[str, ContrastiveExplanation] = {}

    def explain_why(
        self,
        fact_var_id: str,
        fact_value: Any,
        foil_value: Any
    ) -> ContrastiveExplanation:
        """Explain why fact rather than foil."""
        # Find difference makers
        difference_makers = self._find_difference_makers(
            fact_var_id, fact_value, foil_value
        )

        explanation = ContrastiveExplanation(
            fact=f"{fact_var_id} = {fact_value}",
            foil=f"{fact_var_id} = {foil_value}",
            difference_makers=difference_makers,
            explanation=self._generate_explanation_text(
                fact_var_id, fact_value, foil_value, difference_makers
            )
        )

        self._explanations[explanation.explanation_id] = explanation
        return explanation

    def _find_difference_makers(
        self,
        target_var: str,
        actual_value: Any,
        foil_value: Any
    ) -> List[str]:
        """Find variables that make the difference."""
        difference_makers = []

        # Get parents
        parents = self._model.get_parents(target_var)

        for parent in parents:
            # Check if changing parent would change outcome
            original = parent.value

            # Try alternative values from domain
            for alt_value in parent.domain:
                if alt_value != original:
                    # Create hypothetical state
                    hypothetical = self._model.get_current_state()
                    hypothetical[parent.var_id] = alt_value

                    # Check if this changes outcome
                    if hypothetical.get(target_var) != actual_value:
                        difference_makers.append(parent.var_id)
                        break

        return difference_makers

    def _generate_explanation_text(
        self,
        fact_var: str,
        fact_value: Any,
        foil_value: Any,
        difference_makers: List[str]
    ) -> str:
        """Generate explanation text."""
        if not difference_makers:
            return f"{fact_var} is {fact_value} and not {foil_value} " \
                   "but no clear difference makers found."

        dm_text = ", ".join(difference_makers)
        return f"{fact_var} is {fact_value} rather than {foil_value} " \
               f"because of: {dm_text}"

    def get_explanation(
        self,
        explanation_id: str
    ) -> Optional[ContrastiveExplanation]:
        """Get an explanation."""
        return self._explanations.get(explanation_id)


# =============================================================================
# OUTCOME PREDICTOR
# =============================================================================

class OutcomePredictor:
    """Predict outcomes under interventions."""

    def __init__(
        self,
        causal_model: CausalModel,
        world_generator: WorldGenerator
    ):
        self._model = causal_model
        self._worlds = world_generator

    def predict_outcome(
        self,
        interventions: List[Intervention],
        target_var_id: str
    ) -> Tuple[Any, float]:
        """Predict outcome for target variable."""
        # Generate counterfactual world
        world = self._worlds.create_world(interventions)

        # Get predicted value
        predicted = world.variable_states.get(target_var_id)

        # Calculate confidence based on distance
        distance = self._worlds.calculate_distance(world)
        confidence = 1.0 - (distance * 0.5)  # Adjust confidence scaling

        return predicted, confidence

    def predict_all_outcomes(
        self,
        interventions: List[Intervention]
    ) -> Dict[str, Any]:
        """Predict all variable outcomes."""
        world = self._worlds.create_world(interventions)
        return world.variable_states.copy()

    def compare_scenarios(
        self,
        scenario1: List[Intervention],
        scenario2: List[Intervention],
        target_var_id: str
    ) -> Dict[str, Any]:
        """Compare two intervention scenarios."""
        world1 = self._worlds.create_world(scenario1)
        world2 = self._worlds.create_world(scenario2)

        value1 = world1.variable_states.get(target_var_id)
        value2 = world2.variable_states.get(target_var_id)

        return {
            "scenario1_value": value1,
            "scenario2_value": value2,
            "same_outcome": value1 == value2,
            "scenario1_distance": self._worlds.calculate_distance(world1),
            "scenario2_distance": self._worlds.calculate_distance(world2)
        }


# =============================================================================
# COUNTERFACTUAL ENGINE
# =============================================================================

class CounterfactualEngine:
    """
    Counterfactual Engine for BAEL.

    Advanced counterfactual reasoning and what-if analysis.
    """

    def __init__(self):
        self._model = CausalModel()
        self._intervention_manager = InterventionManager(self._model)
        self._world_generator = WorldGenerator(
            self._model, self._intervention_manager
        )
        self._cf_reasoner = CounterfactualReasoner(
            self._model, self._world_generator, self._intervention_manager
        )
        self._contrastive_explainer = ContrastiveExplainer(
            self._model, self._cf_reasoner
        )
        self._outcome_predictor = OutcomePredictor(
            self._model, self._world_generator
        )

    # -------------------------------------------------------------------------
    # MODEL BUILDING
    # -------------------------------------------------------------------------

    def add_variable(
        self,
        name: str,
        value: Any = None,
        domain: Optional[List[Any]] = None,
        is_exogenous: bool = False
    ) -> Variable:
        """Add a variable."""
        return self._model.add_variable(name, value, domain, is_exogenous)

    def add_causal_link(
        self,
        source_id: str,
        target_id: str,
        strength: float = 1.0,
        mechanism: Optional[Callable] = None
    ) -> Optional[CausalLink]:
        """Add a causal link."""
        return self._model.add_link(source_id, target_id, strength, mechanism)

    def get_variable(self, var_id: str) -> Optional[Variable]:
        """Get a variable."""
        return self._model.get_variable(var_id)

    def get_current_state(self) -> Dict[str, Any]:
        """Get current state."""
        return self._model.get_current_state()

    # -------------------------------------------------------------------------
    # INTERVENTIONS
    # -------------------------------------------------------------------------

    def create_intervention(
        self,
        variable_id: str,
        intervention_type: InterventionType,
        new_value: Any = None,
        description: str = ""
    ) -> Intervention:
        """Create an intervention."""
        return self._intervention_manager.create_intervention(
            variable_id, intervention_type, new_value, description
        )

    def apply_intervention(
        self,
        intervention: Intervention
    ) -> Dict[str, Any]:
        """Apply intervention and get new state."""
        current = self._model.get_current_state()
        new_state = self._intervention_manager.apply_intervention(
            intervention, current
        )
        return new_state

    # -------------------------------------------------------------------------
    # POSSIBLE WORLDS
    # -------------------------------------------------------------------------

    def create_possible_world(
        self,
        interventions: List[Intervention]
    ) -> PossibleWorld:
        """Create a possible world."""
        return self._world_generator.create_world(interventions)

    def calculate_world_distance(
        self,
        world: PossibleWorld,
        metric: WorldDistance = WorldDistance.HAMMING
    ) -> float:
        """Calculate distance from actual world."""
        return self._world_generator.calculate_distance(world, metric)

    # -------------------------------------------------------------------------
    # COUNTERFACTUALS
    # -------------------------------------------------------------------------

    def ask_what_if(
        self,
        antecedent_var: str,
        counterfactual_value: Any,
        consequent_var: str,
        antecedent_description: str = "",
        consequent_description: str = ""
    ) -> EvaluationResult:
        """Ask a what-if question."""
        cf = self._cf_reasoner.create_counterfactual(
            antecedent_description or f"If {antecedent_var} were {counterfactual_value}",
            consequent_description or f"Then {consequent_var} would...",
            CounterfactualType.SUBSTITUTION,
            counterfactual_antecedent=counterfactual_value
        )

        return self._cf_reasoner.evaluate(cf, antecedent_var, consequent_var)

    def find_closest_world_where(
        self,
        target_state: Dict[str, Any],
        max_interventions: int = 3
    ) -> Optional[PossibleWorld]:
        """Find closest world where condition holds."""
        return self._cf_reasoner.find_closest_world(
            target_state, max_interventions
        )

    # -------------------------------------------------------------------------
    # CONTRASTIVE EXPLANATIONS
    # -------------------------------------------------------------------------

    def explain_why_not(
        self,
        var_id: str,
        actual_value: Any,
        alternative_value: Any
    ) -> ContrastiveExplanation:
        """Explain why actual rather than alternative."""
        return self._contrastive_explainer.explain_why(
            var_id, actual_value, alternative_value
        )

    # -------------------------------------------------------------------------
    # OUTCOME PREDICTION
    # -------------------------------------------------------------------------

    def predict_outcome(
        self,
        interventions: List[Intervention],
        target_var_id: str
    ) -> Tuple[Any, float]:
        """Predict outcome under interventions."""
        return self._outcome_predictor.predict_outcome(
            interventions, target_var_id
        )

    def compare_scenarios(
        self,
        scenario1: List[Intervention],
        scenario2: List[Intervention],
        target_var_id: str
    ) -> Dict[str, Any]:
        """Compare two scenarios."""
        return self._outcome_predictor.compare_scenarios(
            scenario1, scenario2, target_var_id
        )


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Counterfactual Engine."""
    print("=" * 70)
    print("BAEL - COUNTERFACTUAL ENGINE DEMO")
    print("Advanced Counterfactual Reasoning and What-If Analysis")
    print("=" * 70)
    print()

    engine = CounterfactualEngine()

    # 1. Build Causal Model
    print("1. BUILD CAUSAL MODEL:")
    print("-" * 40)

    # Example: Rain -> Sprinkler -> Grass Wet
    rain = engine.add_variable(
        "Rain",
        value=True,
        domain=[True, False],
        is_exogenous=True
    )

    sprinkler = engine.add_variable(
        "Sprinkler",
        value=False,
        domain=[True, False]
    )

    grass_wet = engine.add_variable(
        "GrassWet",
        value=True,
        domain=[True, False]
    )

    sidewalk_wet = engine.add_variable(
        "SidewalkWet",
        value=True,
        domain=[True, False]
    )

    print(f"   Rain (exogenous): {rain.value}")
    print(f"   Sprinkler: {sprinkler.value}")
    print(f"   GrassWet: {grass_wet.value}")
    print(f"   SidewalkWet: {sidewalk_wet.value}")
    print()

    # 2. Add Causal Links
    print("2. ADD CAUSAL LINKS:")
    print("-" * 40)

    # Rain -> Sprinkler (inverse - sprinkler off when raining)
    engine.add_causal_link(
        rain.var_id,
        sprinkler.var_id,
        mechanism=lambda p: not list(p.values())[0]
    )

    # Rain -> GrassWet
    engine.add_causal_link(rain.var_id, grass_wet.var_id)

    # Sprinkler -> GrassWet
    engine.add_causal_link(sprinkler.var_id, grass_wet.var_id)

    # Rain -> SidewalkWet
    engine.add_causal_link(rain.var_id, sidewalk_wet.var_id)

    print("   Rain -> Sprinkler (inverse)")
    print("   Rain -> GrassWet")
    print("   Sprinkler -> GrassWet")
    print("   Rain -> SidewalkWet")
    print()

    # 3. Ask What-If Questions
    print("3. WHAT-IF QUESTIONS:")
    print("-" * 40)

    result = engine.ask_what_if(
        rain.var_id,
        False,  # What if no rain?
        grass_wet.var_id,
        "If it hadn't rained",
        "Would the grass still be wet?"
    )

    print(f"   Question: If it hadn't rained, would grass be wet?")
    print(f"   Is true: {result.is_true}")
    print(f"   Confidence: {result.confidence:.2f}")
    print(f"   Reasoning: {result.reasoning}")
    print()

    # 4. Create Interventions
    print("4. CREATE INTERVENTIONS:")
    print("-" * 40)

    turn_on_sprinkler = engine.create_intervention(
        sprinkler.var_id,
        InterventionType.SET_VALUE,
        True,
        "Turn on the sprinkler"
    )

    stop_rain = engine.create_intervention(
        rain.var_id,
        InterventionType.SET_VALUE,
        False,
        "Stop the rain"
    )

    print(f"   Intervention 1: {turn_on_sprinkler.description}")
    print(f"   Intervention 2: {stop_rain.description}")
    print()

    # 5. Create Possible World
    print("5. POSSIBLE WORLDS:")
    print("-" * 40)

    world = engine.create_possible_world([stop_rain])
    distance = engine.calculate_world_distance(world)

    print(f"   World with no rain:")
    print(f"   Distance from actual: {distance:.2f}")
    print(f"   Variable states: {world.variable_states}")
    print()

    # 6. Predict Outcomes
    print("6. PREDICT OUTCOMES:")
    print("-" * 40)

    predicted_value, confidence = engine.predict_outcome(
        [turn_on_sprinkler, stop_rain],
        grass_wet.var_id
    )

    print(f"   Scenario: Turn on sprinkler AND stop rain")
    print(f"   Predicted GrassWet: {predicted_value}")
    print(f"   Confidence: {confidence:.2f}")
    print()

    # 7. Compare Scenarios
    print("7. COMPARE SCENARIOS:")
    print("-" * 40)

    comparison = engine.compare_scenarios(
        [turn_on_sprinkler],
        [stop_rain],
        grass_wet.var_id
    )

    print(f"   Scenario 1 (sprinkler on): GrassWet = {comparison['scenario1_value']}")
    print(f"   Scenario 2 (no rain): GrassWet = {comparison['scenario2_value']}")
    print(f"   Same outcome: {comparison['same_outcome']}")
    print()

    # 8. Contrastive Explanation
    print("8. CONTRASTIVE EXPLANATION:")
    print("-" * 40)

    explanation = engine.explain_why_not(
        grass_wet.var_id,
        True,  # Actual: grass is wet
        False  # Why not dry?
    )

    print(f"   Fact: {explanation.fact}")
    print(f"   Foil: {explanation.foil}")
    print(f"   Difference makers: {explanation.difference_makers}")
    print(f"   Explanation: {explanation.explanation}")
    print()

    # 9. Find Closest World
    print("9. FIND CLOSEST WORLD:")
    print("-" * 40)

    target_state = {
        rain.var_id: False,
        grass_wet.var_id: False,
        sidewalk_wet.var_id: False
    }

    closest = engine.find_closest_world_where(target_state)

    print(f"   Target: Dry grass and dry sidewalk")
    print(f"   Closest world distance: {closest.distance_from_actual:.2f}")
    print(f"   Number of interventions: {len(closest.interventions)}")
    print()

    # 10. Current State
    print("10. CURRENT STATE:")
    print("-" * 40)

    state = engine.get_current_state()
    for var_id, value in state.items():
        var = engine.get_variable(var_id)
        print(f"   {var.name if var else var_id}: {value}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Counterfactual Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())

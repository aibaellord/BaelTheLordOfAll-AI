"""
BAEL Script Knowledge Engine
==============================

Event sequences guide understanding.
Schank & Abelson's script theory.

"Ba'el knows the patterns of events." — Ba'el
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

logger = logging.getLogger("BAEL.ScriptKnowledge")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class ScriptCategory(Enum):
    """Category of script."""
    SITUATIONAL = auto()    # Restaurant, doctor, etc.
    PERSONAL = auto()       # Personal routines
    INSTRUMENTAL = auto()   # How to do things
    CULTURAL = auto()       # Cultural practices


class SceneType(Enum):
    """Type of scene in script."""
    ENTRY = auto()          # Entering situation
    PRECONDITION = auto()   # Prerequisites
    MAIN_ACTION = auto()    # Core activity
    RESULT = auto()         # Outcomes
    EXIT = auto()           # Leaving


class ActionSlot(Enum):
    """Type of action slot."""
    ACTOR = auto()
    ACTION = auto()
    OBJECT = auto()
    LOCATION = auto()
    INSTRUMENT = auto()


@dataclass
class ScriptAction:
    """
    An action in a script.
    """
    id: str
    description: str
    scene: SceneType
    slots: Dict[ActionSlot, str]
    typicality: float
    optional: bool = False


@dataclass
class Script:
    """
    A complete script.
    """
    id: str
    name: str
    category: ScriptCategory
    roles: List[str]
    props: List[str]
    entry_conditions: List[str]
    actions: List[ScriptAction]
    result: str


@dataclass
class NarrativeEvent:
    """
    An event in a narrative.
    """
    id: str
    description: str
    script_id: Optional[str]
    action_id: Optional[str]
    matches_script: bool


@dataclass
class ComprehensionResult:
    """
    Result of narrative comprehension.
    """
    narrative_id: str
    script_activated: bool
    inferred_actions: List[str]
    fill_in_details: Dict[str, str]
    reading_time_factor: float


@dataclass
class ScriptMetrics:
    """
    Script knowledge metrics.
    """
    script_activation_rate: float
    inference_rate: float
    typical_advantage: float
    intrusion_rate: float


# ============================================================================
# SCRIPT MODEL
# ============================================================================

class ScriptModel:
    """
    Schank & Abelson's script model.

    "Ba'el's event structures." — Ba'el
    """

    def __init__(self):
        """Initialize model."""
        # Activation parameters
        self._activation_threshold = 0.3
        self._cue_strength = 0.4

        # Inference parameters
        self._inference_rate = 0.7
        self._fill_rate = 0.6

        # Processing parameters
        self._typical_speedup = 0.7  # 30% faster for script-consistent
        self._atypical_slowdown = 1.4  # 40% slower for violations

        # Memory parameters
        self._intrusion_rate = 0.15

        self._lock = threading.RLock()

    def calculate_activation(
        self,
        cues_present: int,
        cues_total: int
    ) -> float:
        """Calculate script activation from cues."""
        if cues_total == 0:
            return 0.0

        match = cues_present / cues_total
        activation = match * self._cue_strength

        return min(1.0, activation)

    def should_activate(
        self,
        activation: float
    ) -> bool:
        """Check if script should activate."""
        return activation >= self._activation_threshold

    def calculate_reading_time(
        self,
        matches_script: bool,
        script_active: bool
    ) -> float:
        """Calculate relative reading time."""
        if not script_active:
            return 1.0

        if matches_script:
            return self._typical_speedup
        else:
            return self._atypical_slowdown

    def generate_inferences(
        self,
        script: Script,
        mentioned_actions: Set[str]
    ) -> List[str]:
        """Generate inferences from script."""
        inferences = []

        for action in script.actions:
            if action.id not in mentioned_actions:
                if not action.optional:
                    if random.random() < self._inference_rate:
                        inferences.append(action.description)

        return inferences

    def fill_slots(
        self,
        script: Script,
        narrative_slots: Dict[ActionSlot, str]
    ) -> Dict[str, str]:
        """Fill in missing slots from script defaults."""
        filled = {}

        # Get default fillers from script
        script_defaults = {}
        for action in script.actions:
            for slot, value in action.slots.items():
                if slot not in script_defaults:
                    script_defaults[slot] = value

        # Fill missing slots
        for slot in ActionSlot:
            if slot not in narrative_slots:
                if slot in script_defaults:
                    if random.random() < self._fill_rate:
                        filled[slot.name] = script_defaults[slot]

        return filled


# ============================================================================
# SCRIPT SYSTEM
# ============================================================================

class ScriptSystem:
    """
    Script knowledge system.

    "Ba'el's event sequence library." — Ba'el
    """

    def __init__(self):
        """Initialize system."""
        self._model = ScriptModel()

        self._scripts: Dict[str, Script] = {}
        self._narratives: Dict[str, List[NarrativeEvent]] = {}
        self._comprehensions: List[ComprehensionResult] = []

        self._counter = 0
        self._lock = threading.RLock()

        # Create default scripts
        self._create_default_scripts()

    def _generate_id(self) -> str:
        self._counter += 1
        return f"item_{self._counter}"

    def _create_default_scripts(self):
        """Create default scripts."""
        # Restaurant script
        restaurant = Script(
            id="restaurant",
            name="Restaurant Visit",
            category=ScriptCategory.SITUATIONAL,
            roles=["customer", "waiter", "chef", "cashier"],
            props=["menu", "table", "food", "bill", "money"],
            entry_conditions=["hungry", "have_money"],
            actions=[
                ScriptAction(
                    id="enter", description="Enter restaurant",
                    scene=SceneType.ENTRY,
                    slots={ActionSlot.ACTOR: "customer", ActionSlot.ACTION: "enter"},
                    typicality=0.95
                ),
                ScriptAction(
                    id="wait", description="Wait to be seated",
                    scene=SceneType.PRECONDITION,
                    slots={ActionSlot.ACTOR: "customer", ActionSlot.ACTION: "wait"},
                    typicality=0.8, optional=True
                ),
                ScriptAction(
                    id="sit", description="Sit at table",
                    scene=SceneType.PRECONDITION,
                    slots={ActionSlot.ACTOR: "customer", ActionSlot.ACTION: "sit"},
                    typicality=0.9
                ),
                ScriptAction(
                    id="read_menu", description="Read menu",
                    scene=SceneType.PRECONDITION,
                    slots={ActionSlot.ACTOR: "customer", ActionSlot.OBJECT: "menu"},
                    typicality=0.85
                ),
                ScriptAction(
                    id="order", description="Order food",
                    scene=SceneType.MAIN_ACTION,
                    slots={ActionSlot.ACTOR: "customer", ActionSlot.ACTION: "order"},
                    typicality=0.95
                ),
                ScriptAction(
                    id="eat", description="Eat food",
                    scene=SceneType.MAIN_ACTION,
                    slots={ActionSlot.ACTOR: "customer", ActionSlot.ACTION: "eat"},
                    typicality=0.95
                ),
                ScriptAction(
                    id="pay", description="Pay bill",
                    scene=SceneType.RESULT,
                    slots={ActionSlot.ACTOR: "customer", ActionSlot.ACTION: "pay"},
                    typicality=0.9
                ),
                ScriptAction(
                    id="leave", description="Leave restaurant",
                    scene=SceneType.EXIT,
                    slots={ActionSlot.ACTOR: "customer", ActionSlot.ACTION: "leave"},
                    typicality=0.95
                )
            ],
            result="satisfied_hunger"
        )
        self._scripts["restaurant"] = restaurant

        # Doctor script
        doctor = Script(
            id="doctor",
            name="Doctor Visit",
            category=ScriptCategory.SITUATIONAL,
            roles=["patient", "receptionist", "nurse", "doctor"],
            props=["waiting_room", "form", "exam_room", "prescription"],
            entry_conditions=["sick", "have_appointment"],
            actions=[
                ScriptAction(
                    id="arrive", description="Arrive at office",
                    scene=SceneType.ENTRY,
                    slots={ActionSlot.ACTOR: "patient"},
                    typicality=0.95
                ),
                ScriptAction(
                    id="check_in", description="Check in at reception",
                    scene=SceneType.PRECONDITION,
                    slots={ActionSlot.ACTOR: "patient", ActionSlot.OBJECT: "form"},
                    typicality=0.9
                ),
                ScriptAction(
                    id="wait", description="Wait in waiting room",
                    scene=SceneType.PRECONDITION,
                    slots={ActionSlot.ACTOR: "patient", ActionSlot.LOCATION: "waiting_room"},
                    typicality=0.85
                ),
                ScriptAction(
                    id="called", description="Nurse calls name",
                    scene=SceneType.PRECONDITION,
                    slots={ActionSlot.ACTOR: "nurse"},
                    typicality=0.8
                ),
                ScriptAction(
                    id="exam", description="Doctor examines",
                    scene=SceneType.MAIN_ACTION,
                    slots={ActionSlot.ACTOR: "doctor", ActionSlot.LOCATION: "exam_room"},
                    typicality=0.95
                ),
                ScriptAction(
                    id="prescription", description="Get prescription",
                    scene=SceneType.RESULT,
                    slots={ActionSlot.ACTOR: "doctor", ActionSlot.OBJECT: "prescription"},
                    typicality=0.7, optional=True
                ),
                ScriptAction(
                    id="leave", description="Leave office",
                    scene=SceneType.EXIT,
                    slots={ActionSlot.ACTOR: "patient"},
                    typicality=0.95
                )
            ],
            result="diagnosis_received"
        )
        self._scripts["doctor"] = doctor

    def create_script(
        self,
        name: str,
        category: ScriptCategory,
        actions: List[Tuple[str, SceneType]]
    ) -> Script:
        """Create a custom script."""
        script_id = self._generate_id()

        action_objs = []
        for desc, scene in actions:
            action = ScriptAction(
                id=self._generate_id(),
                description=desc,
                scene=scene,
                slots={},
                typicality=0.8
            )
            action_objs.append(action)

        script = Script(
            id=script_id,
            name=name,
            category=category,
            roles=[],
            props=[],
            entry_conditions=[],
            actions=action_objs,
            result="completed"
        )

        self._scripts[script_id] = script

        return script

    def process_narrative(
        self,
        narrative_id: str,
        events: List[str],
        script_id: str
    ) -> ComprehensionResult:
        """Process a narrative with script knowledge."""
        script = self._scripts.get(script_id)

        # Match events to script actions
        mentioned = set()
        matches = 0

        for event in events:
            for action in script.actions if script else []:
                if action.description.lower() in event.lower():
                    mentioned.add(action.id)
                    matches += 1

        # Calculate activation
        activation = self._model.calculate_activation(
            matches, len(script.actions) if script else 1
        )

        script_active = self._model.should_activate(activation)

        # Generate inferences
        if script and script_active:
            inferences = self._model.generate_inferences(script, mentioned)
            filled = self._model.fill_slots(script, {})
        else:
            inferences = []
            filled = {}

        # Calculate reading time
        reading_time = self._model.calculate_reading_time(
            matches > 0, script_active
        )

        result = ComprehensionResult(
            narrative_id=narrative_id,
            script_activated=script_active,
            inferred_actions=inferences,
            fill_in_details=filled,
            reading_time_factor=reading_time
        )

        self._comprehensions.append(result)

        return result


# ============================================================================
# SCRIPT PARADIGM
# ============================================================================

class ScriptParadigm:
    """
    Script knowledge paradigm.

    "Ba'el's event structure study." — Ba'el
    """

    def __init__(self):
        """Initialize paradigm."""
        self._lock = threading.RLock()

    def run_bower_paradigm(
        self
    ) -> Dict[str, Any]:
        """Run Bower et al. script memory paradigm."""
        system = ScriptSystem()

        # Script-consistent story
        consistent_events = [
            "John entered the restaurant",
            "He sat at a table",
            "He ordered a steak",
            "He ate his meal",
            "He paid the bill"
        ]

        # Script-inconsistent story
        inconsistent_events = [
            "John entered the restaurant",
            "He sat on the floor",  # Violation
            "He ordered a steak",
            "The waiter sang a song",  # Violation
            "He paid the bill"
        ]

        consistent_result = system.process_narrative(
            "consistent", consistent_events, "restaurant"
        )

        inconsistent_result = system.process_narrative(
            "inconsistent", inconsistent_events, "restaurant"
        )

        return {
            'consistent': {
                'script_activated': consistent_result.script_activated,
                'inferences': len(consistent_result.inferred_actions),
                'reading_time': consistent_result.reading_time_factor
            },
            'inconsistent': {
                'script_activated': inconsistent_result.script_activated,
                'inferences': len(inconsistent_result.inferred_actions),
                'reading_time': inconsistent_result.reading_time_factor
            },
            'interpretation': 'Script violations slow reading but are better remembered'
        }

    def run_inference_study(
        self
    ) -> Dict[str, Any]:
        """Study script-based inferences."""
        system = ScriptSystem()

        # Minimal story
        minimal_events = [
            "Mary went to a restaurant",
            "She had a burger"
        ]

        result = system.process_narrative("minimal", minimal_events, "restaurant")

        return {
            'mentioned': 2,
            'inferred': result.inferred_actions,
            'filled_slots': result.fill_in_details,
            'interpretation': 'Readers infer script-typical actions'
        }

    def run_memory_intrusion_study(
        self
    ) -> Dict[str, Any]:
        """Study script-consistent memory intrusions."""
        system = ScriptSystem()

        # Story WITHOUT reading menu
        story_events = [
            "John entered the restaurant",
            "He sat at a table",
            # No mention of menu
            "He ordered pasta",
            "He ate his meal",
            "He paid the bill"
        ]

        result = system.process_narrative("no_menu", story_events, "restaurant")

        # Check if "read menu" is inferred
        menu_inferred = any("menu" in inf.lower() for inf in result.inferred_actions)

        return {
            'story_events': len(story_events),
            'inferences': result.inferred_actions,
            'menu_inferred': menu_inferred,
            'interpretation': 'Typical actions often falsely remembered'
        }

    def run_reading_time_study(
        self
    ) -> Dict[str, Any]:
        """Study reading times for script elements."""
        system = ScriptSystem()

        conditions = {
            'typical': ["John ordered food from the waiter"],
            'atypical': ["John ordered food from the chef"],
            'violation': ["John ordered food from his cat"]
        }

        results = {}

        for condition, events in conditions.items():
            result = system.process_narrative(
                condition, events, "restaurant"
            )
            results[condition] = {
                'reading_time': result.reading_time_factor
            }

        return {
            'by_condition': results,
            'interpretation': 'Violations slow reading'
        }

    def run_script_activation_study(
        self
    ) -> Dict[str, Any]:
        """Study script activation thresholds."""
        system = ScriptSystem()

        cue_levels = [
            (["restaurant"], "weak"),
            (["restaurant", "menu"], "moderate"),
            (["restaurant", "menu", "waiter", "order"], "strong")
        ]

        results = {}

        for cues, level in cue_levels:
            result = system.process_narrative(
                level, cues, "restaurant"
            )
            results[level] = {
                'activated': result.script_activated,
                'cues': len(cues)
            }

        return {
            'by_cue_level': results,
            'interpretation': 'More cues = stronger activation'
        }

    def run_cross_script_study(
        self
    ) -> Dict[str, Any]:
        """Study effects when multiple scripts could apply."""
        system = ScriptSystem()

        # Ambiguous narrative
        events = [
            "John arrived at the building",
            "He waited in a room",
            "Someone called his name",
            "He received something",
            "He left"
        ]

        restaurant_result = system.process_narrative(
            "ambig_rest", events, "restaurant"
        )

        doctor_result = system.process_narrative(
            "ambig_doc", events, "doctor"
        )

        return {
            'restaurant_activation': restaurant_result.script_activated,
            'doctor_activation': doctor_result.script_activated,
            'restaurant_inferences': len(restaurant_result.inferred_actions),
            'doctor_inferences': len(doctor_result.inferred_actions),
            'interpretation': 'Same events interpreted differently by different scripts'
        }


# ============================================================================
# SCRIPT ENGINE
# ============================================================================

class ScriptKnowledgeEngine:
    """
    Complete script knowledge engine.

    "Ba'el's event structure engine." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._paradigm = ScriptParadigm()
        self._system = ScriptSystem()

        self._experiment_results: List[Dict] = []

        self._lock = threading.RLock()

    # Script management

    def create_script(
        self,
        name: str,
        category: ScriptCategory,
        actions: List[Tuple[str, SceneType]]
    ) -> Script:
        """Create script."""
        return self._system.create_script(name, category, actions)

    def process_narrative(
        self,
        narrative_id: str,
        events: List[str],
        script_id: str
    ) -> ComprehensionResult:
        """Process narrative."""
        return self._system.process_narrative(narrative_id, events, script_id)

    # Experiments

    def run_bower(
        self
    ) -> Dict[str, Any]:
        """Run Bower paradigm."""
        result = self._paradigm.run_bower_paradigm()
        self._experiment_results.append(result)
        return result

    def study_inferences(
        self
    ) -> Dict[str, Any]:
        """Study inferences."""
        return self._paradigm.run_inference_study()

    def study_intrusions(
        self
    ) -> Dict[str, Any]:
        """Study intrusions."""
        return self._paradigm.run_memory_intrusion_study()

    def study_reading_time(
        self
    ) -> Dict[str, Any]:
        """Study reading time."""
        return self._paradigm.run_reading_time_study()

    def study_activation(
        self
    ) -> Dict[str, Any]:
        """Study activation."""
        return self._paradigm.run_script_activation_study()

    def study_cross_script(
        self
    ) -> Dict[str, Any]:
        """Study cross-script effects."""
        return self._paradigm.run_cross_script_study()

    # Analysis

    def get_metrics(self) -> ScriptMetrics:
        """Get metrics."""
        if not self._experiment_results:
            self.run_bower()

        return ScriptMetrics(
            script_activation_rate=0.8,
            inference_rate=0.7,
            typical_advantage=0.3,
            intrusion_rate=0.15
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'scripts': len(self._system._scripts),
            'comprehensions': len(self._system._comprehensions)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_script_knowledge_engine() -> ScriptKnowledgeEngine:
    """Create script knowledge engine."""
    return ScriptKnowledgeEngine()


def demonstrate_script_knowledge() -> Dict[str, Any]:
    """Demonstrate script knowledge."""
    engine = create_script_knowledge_engine()

    # Bower paradigm
    bower = engine.run_bower()

    # Inferences
    inferences = engine.study_inferences()

    # Intrusions
    intrusions = engine.study_intrusions()

    # Reading time
    reading = engine.study_reading_time()

    return {
        'bower': {
            'consistent_rt': bower['consistent']['reading_time'],
            'inconsistent_rt': bower['inconsistent']['reading_time']
        },
        'inferences': {
            'mentioned': inferences['mentioned'],
            'inferred_count': len(inferences['inferred'])
        },
        'intrusions': {
            'menu_false_memory': intrusions['menu_inferred']
        },
        'reading_times': {
            k: f"{v['reading_time']:.2f}x"
            for k, v in reading['by_condition'].items()
        },
        'interpretation': (
            f"Scripts guide comprehension. "
            f"Typical events read {bower['consistent']['reading_time']:.2f}x normal. "
            f"Script-consistent intrusions occur."
        )
    }


def get_script_knowledge_facts() -> Dict[str, str]:
    """Get facts about script knowledge."""
    return {
        'schank_abelson_1977': 'Scripts, Plans, Goals, and Understanding',
        'definition': 'Stereotyped event sequences',
        'components': 'Entry, preconditions, main, results, exit',
        'inference': 'Readers infer script-typical actions',
        'intrusion': 'Typical actions falsely remembered',
        'reading_time': 'Violations slow reading',
        'activation': 'Scripts activated by cues',
        'applications': 'Story understanding, AI, memory'
    }

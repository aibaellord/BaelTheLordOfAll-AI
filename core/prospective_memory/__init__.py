"""
BAEL Prospective Memory Engine
==============================

Remembering to perform future intentions.
Time-based and event-based prospective memory.

"Ba'el never forgets future plans." — Ba'el
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
import heapq
import copy

logger = logging.getLogger("BAEL.ProspectiveMemory")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class ProspectiveType(Enum):
    """Types of prospective memory."""
    TIME_BASED = auto()    # Remember to do X at time T
    EVENT_BASED = auto()   # Remember to do X when Y occurs
    ACTIVITY_BASED = auto() # Remember when finishing activity


class CueType(Enum):
    """Types of retrieval cues."""
    TEMPORAL = auto()      # Time-based
    ENVIRONMENTAL = auto() # Context-based
    PERSON = auto()        # Person-based
    ACTION = auto()        # Action-based
    OBJECT = auto()        # Object-based


class IntentionState(Enum):
    """States of an intention."""
    FORMED = auto()        # Just created
    ACTIVE = auto()        # Currently active
    SUSPENDED = auto()     # Temporarily inactive
    RETRIEVED = auto()     # Cue detected
    EXECUTED = auto()      # Successfully completed
    FAILED = auto()        # Failed to execute
    EXPIRED = auto()       # Missed opportunity


class RetrievalMode(Enum):
    """Retrieval processing modes."""
    SPONTANEOUS = auto()   # Automatic retrieval
    MONITORING = auto()    # Active monitoring
    CHECKING = auto()      # Periodic checking


@dataclass
class Cue:
    """
    A retrieval cue.
    """
    id: str
    cue_type: CueType
    description: str
    specificity: float  # 0-1, how specific
    features: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Intention:
    """
    A prospective memory intention.
    """
    id: str
    description: str
    pm_type: ProspectiveType
    cues: List[Cue]
    action: str
    importance: float  # 0-1
    state: IntentionState = IntentionState.FORMED
    created_at: float = field(default_factory=time.time)
    deadline: Optional[float] = None
    execution_window: float = 60.0  # seconds


@dataclass
class RetrievalAttempt:
    """
    An attempt to retrieve intention.
    """
    intention_id: str
    timestamp: float
    cue_id: Optional[str]
    successful: bool
    mode: RetrievalMode


@dataclass
class PerformanceMetrics:
    """
    Prospective memory performance.
    """
    hit_rate: float        # Successful retrievals
    miss_rate: float       # Missed intentions
    false_alarms: float    # Incorrect retrievals
    response_time: float   # Average retrieval time


# ============================================================================
# CUE DETECTOR
# ============================================================================

class CueDetector:
    """
    Detect prospective memory cues.

    "Ba'el watches for cues." — Ba'el
    """

    def __init__(self):
        """Initialize detector."""
        self._sensitivity = 0.7  # Detection sensitivity
        self._lock = threading.RLock()

    def detect(
        self,
        cue: Cue,
        environment: Dict[str, Any]
    ) -> Tuple[bool, float]:
        """
        Detect if cue is present.
        Returns (detected, match_strength).
        """
        if cue.cue_type == CueType.TEMPORAL:
            return self._detect_temporal(cue, environment)
        elif cue.cue_type == CueType.ENVIRONMENTAL:
            return self._detect_environmental(cue, environment)
        elif cue.cue_type == CueType.PERSON:
            return self._detect_person(cue, environment)
        elif cue.cue_type == CueType.ACTION:
            return self._detect_action(cue, environment)
        else:
            return self._detect_object(cue, environment)

    def _detect_temporal(
        self,
        cue: Cue,
        environment: Dict[str, Any]
    ) -> Tuple[bool, float]:
        """Detect time-based cue."""
        target_time = cue.features.get('target_time', 0)
        current_time = environment.get('time', time.time())

        # Check if within window
        diff = abs(current_time - target_time)
        window = cue.features.get('window', 60)

        if diff < window:
            strength = 1.0 - (diff / window)
            return True, strength

        return False, 0.0

    def _detect_environmental(
        self,
        cue: Cue,
        environment: Dict[str, Any]
    ) -> Tuple[bool, float]:
        """Detect environmental cue."""
        target_location = cue.features.get('location', '')
        current_location = environment.get('location', '')

        if target_location == current_location:
            return True, cue.specificity

        return False, 0.0

    def _detect_person(
        self,
        cue: Cue,
        environment: Dict[str, Any]
    ) -> Tuple[bool, float]:
        """Detect person-based cue."""
        target_person = cue.features.get('person', '')
        present_people = environment.get('people', [])

        if target_person in present_people:
            return True, cue.specificity

        return False, 0.0

    def _detect_action(
        self,
        cue: Cue,
        environment: Dict[str, Any]
    ) -> Tuple[bool, float]:
        """Detect action-based cue."""
        target_action = cue.features.get('action', '')
        current_action = environment.get('action', '')

        if target_action.lower() in current_action.lower():
            return True, cue.specificity

        return False, 0.0

    def _detect_object(
        self,
        cue: Cue,
        environment: Dict[str, Any]
    ) -> Tuple[bool, float]:
        """Detect object-based cue."""
        target_object = cue.features.get('object', '')
        visible_objects = environment.get('objects', [])

        if target_object in visible_objects:
            return True, cue.specificity

        return False, 0.0


# ============================================================================
# INTENTION MANAGER
# ============================================================================

class IntentionManager:
    """
    Manage prospective memory intentions.

    "Ba'el manages future plans." — Ba'el
    """

    def __init__(self):
        """Initialize manager."""
        self._intentions: Dict[str, Intention] = {}
        self._active_intentions: List[str] = []

        self._intention_counter = 0
        self._cue_counter = 0

        self._lock = threading.RLock()

    def _generate_intention_id(self) -> str:
        self._intention_counter += 1
        return f"int_{self._intention_counter}"

    def _generate_cue_id(self) -> str:
        self._cue_counter += 1
        return f"cue_{self._cue_counter}"

    def create_intention(
        self,
        description: str,
        pm_type: ProspectiveType,
        cues: List[Cue],
        action: str,
        importance: float = 0.5,
        deadline: Optional[float] = None
    ) -> Intention:
        """Create new intention."""
        with self._lock:
            intention = Intention(
                id=self._generate_intention_id(),
                description=description,
                pm_type=pm_type,
                cues=cues,
                action=action,
                importance=importance,
                state=IntentionState.ACTIVE,
                deadline=deadline
            )

            self._intentions[intention.id] = intention
            self._active_intentions.append(intention.id)

            return intention

    def create_time_based_intention(
        self,
        description: str,
        action: str,
        target_time: float,
        importance: float = 0.5
    ) -> Intention:
        """Create time-based intention."""
        cue = Cue(
            id=self._generate_cue_id(),
            cue_type=CueType.TEMPORAL,
            description=f"At time {target_time}",
            specificity=0.9,
            features={'target_time': target_time, 'window': 60}
        )

        return self.create_intention(
            description=description,
            pm_type=ProspectiveType.TIME_BASED,
            cues=[cue],
            action=action,
            importance=importance,
            deadline=target_time + 60
        )

    def create_event_based_intention(
        self,
        description: str,
        action: str,
        cue_type: CueType,
        cue_features: Dict[str, Any],
        importance: float = 0.5
    ) -> Intention:
        """Create event-based intention."""
        cue = Cue(
            id=self._generate_cue_id(),
            cue_type=cue_type,
            description=str(cue_features),
            specificity=0.7,
            features=cue_features
        )

        return self.create_intention(
            description=description,
            pm_type=ProspectiveType.EVENT_BASED,
            cues=[cue],
            action=action,
            importance=importance
        )

    def update_state(
        self,
        intention_id: str,
        new_state: IntentionState
    ) -> None:
        """Update intention state."""
        with self._lock:
            if intention_id in self._intentions:
                self._intentions[intention_id].state = new_state

                # Remove from active if terminal state
                if new_state in [
                    IntentionState.EXECUTED,
                    IntentionState.FAILED,
                    IntentionState.EXPIRED
                ]:
                    if intention_id in self._active_intentions:
                        self._active_intentions.remove(intention_id)

    def get_active_intentions(self) -> List[Intention]:
        """Get all active intentions."""
        with self._lock:
            return [
                self._intentions[iid]
                for iid in self._active_intentions
                if iid in self._intentions
            ]

    def get_expired_intentions(self) -> List[Intention]:
        """Get expired intentions."""
        with self._lock:
            current_time = time.time()
            expired = []

            for iid in self._active_intentions[:]:
                intention = self._intentions.get(iid)
                if intention and intention.deadline:
                    if current_time > intention.deadline:
                        intention.state = IntentionState.EXPIRED
                        expired.append(intention)
                        self._active_intentions.remove(iid)

            return expired


# ============================================================================
# MONITORING PROCESS
# ============================================================================

class MonitoringProcess:
    """
    Monitoring for prospective memory retrieval.

    "Ba'el monitors constantly." — Ba'el
    """

    def __init__(
        self,
        intention_manager: IntentionManager,
        cue_detector: CueDetector
    ):
        """Initialize monitoring."""
        self._manager = intention_manager
        self._detector = cue_detector

        self._monitoring_cost = 0.1  # Cognitive cost
        self._check_interval = 1.0   # Seconds

        self._running = False
        self._thread: Optional[threading.Thread] = None

        self._retrieval_attempts: List[RetrievalAttempt] = []

        self._lock = threading.RLock()

    def start_monitoring(self) -> None:
        """Start background monitoring."""
        if not self._running:
            self._running = True
            self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self._thread.start()

    def stop_monitoring(self) -> None:
        """Stop monitoring."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)

    def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        while self._running:
            time.sleep(self._check_interval)
            # In real implementation, would check environment

    def check_environment(
        self,
        environment: Dict[str, Any]
    ) -> List[Intention]:
        """Check environment for matching cues."""
        with self._lock:
            retrieved = []

            for intention in self._manager.get_active_intentions():
                for cue in intention.cues:
                    detected, strength = self._detector.detect(cue, environment)

                    if detected and strength > 0.5:
                        # Successful retrieval
                        intention.state = IntentionState.RETRIEVED
                        retrieved.append(intention)

                        self._retrieval_attempts.append(RetrievalAttempt(
                            intention_id=intention.id,
                            timestamp=time.time(),
                            cue_id=cue.id,
                            successful=True,
                            mode=RetrievalMode.MONITORING
                        ))

                        break

            return retrieved

    def spontaneous_retrieval(
        self,
        intention: Intention,
        environment: Dict[str, Any]
    ) -> bool:
        """Attempt spontaneous retrieval."""
        # Based on importance and cue specificity
        for cue in intention.cues:
            detected, strength = self._detector.detect(cue, environment)

            if detected:
                # Retrieval probability based on importance and strength
                prob = intention.importance * strength * cue.specificity

                if random.random() < prob:
                    return True

        return False


# ============================================================================
# PERFORMANCE TRACKER
# ============================================================================

class PerformanceTracker:
    """
    Track prospective memory performance.

    "Ba'el tracks remembering." — Ba'el
    """

    def __init__(self):
        """Initialize tracker."""
        self._hits = 0
        self._misses = 0
        self._false_alarms = 0
        self._response_times: List[float] = []

        self._lock = threading.RLock()

    def record_hit(
        self,
        response_time: float
    ) -> None:
        """Record successful retrieval."""
        with self._lock:
            self._hits += 1
            self._response_times.append(response_time)

    def record_miss(self) -> None:
        """Record missed intention."""
        with self._lock:
            self._misses += 1

    def record_false_alarm(self) -> None:
        """Record false retrieval."""
        with self._lock:
            self._false_alarms += 1

    def get_metrics(self) -> PerformanceMetrics:
        """Get performance metrics."""
        with self._lock:
            total = self._hits + self._misses

            if total == 0:
                return PerformanceMetrics(
                    hit_rate=0.0,
                    miss_rate=0.0,
                    false_alarms=0.0,
                    response_time=0.0
                )

            return PerformanceMetrics(
                hit_rate=self._hits / total if total > 0 else 0.0,
                miss_rate=self._misses / total if total > 0 else 0.0,
                false_alarms=self._false_alarms,
                response_time=sum(self._response_times) / len(self._response_times) if self._response_times else 0.0
            )

    def reset(self) -> None:
        """Reset metrics."""
        with self._lock:
            self._hits = 0
            self._misses = 0
            self._false_alarms = 0
            self._response_times.clear()


# ============================================================================
# PROSPECTIVE MEMORY ENGINE
# ============================================================================

class ProspectiveMemoryEngine:
    """
    Complete prospective memory engine.

    "Ba'el's future memory." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._cue_detector = CueDetector()
        self._intention_manager = IntentionManager()
        self._monitoring = MonitoringProcess(
            self._intention_manager,
            self._cue_detector
        )
        self._performance = PerformanceTracker()

        self._lock = threading.RLock()

    # Intention creation

    def remember_at_time(
        self,
        description: str,
        action: str,
        target_time: float,
        importance: float = 0.5
    ) -> Intention:
        """Remember to do something at specific time."""
        return self._intention_manager.create_time_based_intention(
            description=description,
            action=action,
            target_time=target_time,
            importance=importance
        )

    def remember_when_event(
        self,
        description: str,
        action: str,
        event_type: str,
        event_features: Dict[str, Any],
        importance: float = 0.5
    ) -> Intention:
        """Remember to do something when event occurs."""
        cue_type_map = {
            'location': CueType.ENVIRONMENTAL,
            'person': CueType.PERSON,
            'action': CueType.ACTION,
            'object': CueType.OBJECT
        }

        cue_type = cue_type_map.get(event_type, CueType.ENVIRONMENTAL)

        return self._intention_manager.create_event_based_intention(
            description=description,
            action=action,
            cue_type=cue_type,
            cue_features=event_features,
            importance=importance
        )

    def remember_when_see_person(
        self,
        description: str,
        action: str,
        person: str,
        importance: float = 0.5
    ) -> Intention:
        """Remember to do something when seeing a person."""
        return self.remember_when_event(
            description=description,
            action=action,
            event_type='person',
            event_features={'person': person},
            importance=importance
        )

    def remember_at_location(
        self,
        description: str,
        action: str,
        location: str,
        importance: float = 0.5
    ) -> Intention:
        """Remember to do something at a location."""
        return self.remember_when_event(
            description=description,
            action=action,
            event_type='location',
            event_features={'location': location},
            importance=importance
        )

    # Environment checking

    def check_environment(
        self,
        environment: Dict[str, Any]
    ) -> List[Tuple[Intention, str]]:
        """
        Check environment and return triggered intentions with actions.
        """
        with self._lock:
            triggered = []
            start_time = time.time()

            retrieved = self._monitoring.check_environment(environment)

            for intention in retrieved:
                self._performance.record_hit(time.time() - start_time)
                self._intention_manager.update_state(
                    intention.id,
                    IntentionState.EXECUTED
                )
                triggered.append((intention, intention.action))

            # Check for expired
            expired = self._intention_manager.get_expired_intentions()
            for intention in expired:
                self._performance.record_miss()

            return triggered

    # Monitoring

    def start_monitoring(self) -> None:
        """Start background monitoring."""
        self._monitoring.start_monitoring()

    def stop_monitoring(self) -> None:
        """Stop monitoring."""
        self._monitoring.stop_monitoring()

    # Intention management

    def get_pending_intentions(self) -> List[Intention]:
        """Get all pending intentions."""
        return self._intention_manager.get_active_intentions()

    def cancel_intention(
        self,
        intention_id: str
    ) -> bool:
        """Cancel an intention."""
        self._intention_manager.update_state(
            intention_id,
            IntentionState.FAILED
        )
        return True

    def execute_intention(
        self,
        intention_id: str
    ) -> bool:
        """Mark intention as executed."""
        self._intention_manager.update_state(
            intention_id,
            IntentionState.EXECUTED
        )
        return True

    # Performance

    def get_performance(self) -> PerformanceMetrics:
        """Get performance metrics."""
        return self._performance.get_metrics()

    def reset_performance(self) -> None:
        """Reset performance tracking."""
        self._performance.reset()

    # Simulation

    def simulate_day(
        self,
        intentions: List[Dict[str, Any]],
        events: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Simulate a day with intentions and events."""
        results = {
            'created': [],
            'triggered': [],
            'missed': []
        }

        # Create intentions
        for intent_data in intentions:
            if intent_data.get('type') == 'time':
                intention = self.remember_at_time(
                    intent_data['description'],
                    intent_data['action'],
                    intent_data['target_time'],
                    intent_data.get('importance', 0.5)
                )
            else:
                intention = self.remember_when_event(
                    intent_data['description'],
                    intent_data['action'],
                    intent_data.get('event_type', 'location'),
                    intent_data.get('event_features', {}),
                    intent_data.get('importance', 0.5)
                )
            results['created'].append(intention)

        # Process events
        for event in events:
            triggered = self.check_environment(event)
            results['triggered'].extend(triggered)

        # Check missed
        results['missed'] = self._intention_manager.get_expired_intentions()

        return results

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'active_intentions': len(self._intention_manager.get_active_intentions()),
            'total_intentions': len(self._intention_manager._intentions),
            'performance': self._performance.get_metrics()
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_prospective_memory_engine() -> ProspectiveMemoryEngine:
    """Create prospective memory engine."""
    return ProspectiveMemoryEngine()


def create_reminder(
    what: str,
    when: str = "time",
    trigger: Any = None
) -> Intention:
    """Create a reminder."""
    engine = create_prospective_memory_engine()

    if when == "time" and trigger:
        return engine.remember_at_time(what, what, trigger)
    elif when == "person" and trigger:
        return engine.remember_when_see_person(what, what, trigger)
    elif when == "location" and trigger:
        return engine.remember_at_location(what, what, trigger)
    else:
        return engine.remember_at_time(what, what, time.time() + 3600)


def get_pm_types_explained() -> Dict[ProspectiveType, str]:
    """Get explanations of prospective memory types."""
    return {
        ProspectiveType.TIME_BASED: "Remember to do X at specific time",
        ProspectiveType.EVENT_BASED: "Remember to do X when event occurs",
        ProspectiveType.ACTIVITY_BASED: "Remember to do X after finishing activity"
    }

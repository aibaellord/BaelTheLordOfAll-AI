"""
🧬 ARCHITECTURE CORE 🧬
=======================
Core cognitive structures.

Features:
- Module system
- Processing levels
- State management
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set
from datetime import datetime
import uuid
from abc import ABC, abstractmethod


class ModuleType(Enum):
    """Types of cognitive modules"""
    PERCEPTION = auto()
    ATTENTION = auto()
    MEMORY = auto()
    REASONING = auto()
    LANGUAGE = auto()
    MOTOR = auto()
    EMOTION = auto()
    METACOGNITION = auto()
    LEARNING = auto()
    EXECUTIVE = auto()


class ProcessingLevel(Enum):
    """Levels of cognitive processing"""
    UNCONSCIOUS = auto()      # Automatic, fast
    PRECONSCIOUS = auto()     # Available but not attended
    CONSCIOUS = auto()         # In awareness
    METACONSCIOUS = auto()    # Aware of awareness


@dataclass
class CognitiveState:
    """Current cognitive state"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Active modules
    active_modules: List[str] = field(default_factory=list)

    # Processing level
    processing_level: ProcessingLevel = ProcessingLevel.CONSCIOUS

    # Current focus
    focus: Any = None
    focus_strength: float = 0.0

    # Resources
    available_resources: float = 1.0
    allocated_resources: Dict[str, float] = field(default_factory=dict)

    # Arousal level
    arousal: float = 0.5

    # Timestamp
    timestamp: datetime = field(default_factory=datetime.now)

    def allocate_resource(self, module: str, amount: float) -> bool:
        """Allocate resource to module"""
        if amount <= self.available_resources:
            self.allocated_resources[module] = amount
            self.available_resources -= amount
            return True
        return False

    def release_resource(self, module: str):
        """Release resource from module"""
        if module in self.allocated_resources:
            self.available_resources += self.allocated_resources[module]
            del self.allocated_resources[module]


class CognitiveModule(ABC):
    """
    Base class for cognitive modules.
    """

    def __init__(self, name: str, module_type: ModuleType):
        self.id = str(uuid.uuid4())
        self.name = name
        self.module_type = module_type

        # State
        self.is_active = False
        self.activation_level: float = 0.0

        # Connections
        self.inputs: List[str] = []   # Module IDs
        self.outputs: List[str] = []

        # Processing
        self.processing_level = ProcessingLevel.UNCONSCIOUS

        # Resource requirements
        self.resource_requirement: float = 0.1

        # Buffer
        self.buffer: List[Any] = []
        self.buffer_capacity: int = 10

    @abstractmethod
    def process(self, input_data: Any) -> Any:
        """Process input data"""
        pass

    def activate(self, level: float = 1.0):
        """Activate module"""
        self.is_active = True
        self.activation_level = min(1.0, level)

    def deactivate(self):
        """Deactivate module"""
        self.is_active = False
        self.activation_level = 0.0

    def add_to_buffer(self, item: Any):
        """Add item to buffer"""
        self.buffer.append(item)
        if len(self.buffer) > self.buffer_capacity:
            self.buffer.pop(0)

    def clear_buffer(self):
        """Clear buffer"""
        self.buffer.clear()


class PerceptionModule(CognitiveModule):
    """Perception processing module"""

    def __init__(self, name: str = "perception"):
        super().__init__(name, ModuleType.PERCEPTION)

        self.feature_extractors: List[Callable] = []

    def add_extractor(self, extractor: Callable[[Any], Dict]):
        """Add feature extractor"""
        self.feature_extractors.append(extractor)

    def process(self, input_data: Any) -> Dict[str, Any]:
        """Extract features from input"""
        features = {}

        for extractor in self.feature_extractors:
            try:
                extracted = extractor(input_data)
                features.update(extracted)
            except Exception:
                pass

        self.add_to_buffer(features)
        return features


class ReasoningModule(CognitiveModule):
    """Reasoning processing module"""

    def __init__(self, name: str = "reasoning"):
        super().__init__(name, ModuleType.REASONING)

        self.rules: List[Callable] = []
        self.processing_level = ProcessingLevel.CONSCIOUS

    def add_rule(self, rule: Callable[[Any], Any]):
        """Add reasoning rule"""
        self.rules.append(rule)

    def process(self, input_data: Any) -> Any:
        """Apply reasoning rules"""
        result = input_data

        for rule in self.rules:
            try:
                result = rule(result)
            except Exception:
                pass

        self.add_to_buffer(result)
        return result


class CognitiveArchitecture:
    """
    The unified cognitive architecture.
    """

    def __init__(self, name: str = "BAEL"):
        self.name = name

        # Modules
        self.modules: Dict[str, CognitiveModule] = {}

        # Current state
        self.state = CognitiveState()

        # Module connections (graph)
        self.connections: Dict[str, Set[str]] = {}

        # Processing pipeline
        self.pipeline: List[str] = []

        # Callbacks
        self.on_state_change: List[Callable] = []

    def add_module(self, module: CognitiveModule):
        """Add cognitive module"""
        self.modules[module.id] = module
        self.connections[module.id] = set()

    def connect_modules(self, from_id: str, to_id: str):
        """Connect two modules"""
        if from_id in self.modules and to_id in self.modules:
            self.connections[from_id].add(to_id)
            self.modules[from_id].outputs.append(to_id)
            self.modules[to_id].inputs.append(from_id)

    def set_pipeline(self, module_ids: List[str]):
        """Set processing pipeline"""
        self.pipeline = [m for m in module_ids if m in self.modules]

    def process(self, input_data: Any) -> Any:
        """Process through architecture"""
        current = input_data

        for module_id in self.pipeline:
            module = self.modules.get(module_id)

            if module and module.is_active:
                # Check resources
                if self.state.allocate_resource(module_id, module.resource_requirement):
                    current = module.process(current)
                    self.state.release_resource(module_id)

        return current

    def broadcast(self, data: Any, from_module: str):
        """Broadcast data from module to connected modules"""
        if from_module not in self.connections:
            return

        for target_id in self.connections[from_module]:
            target = self.modules.get(target_id)
            if target and target.is_active:
                target.add_to_buffer(data)

    def activate_module(self, module_id: str, level: float = 1.0):
        """Activate a module"""
        if module_id in self.modules:
            self.modules[module_id].activate(level)
            if module_id not in self.state.active_modules:
                self.state.active_modules.append(module_id)

    def deactivate_module(self, module_id: str):
        """Deactivate a module"""
        if module_id in self.modules:
            self.modules[module_id].deactivate()
            if module_id in self.state.active_modules:
                self.state.active_modules.remove(module_id)

    def get_active_modules(self) -> List[CognitiveModule]:
        """Get all active modules"""
        return [
            self.modules[m]
            for m in self.state.active_modules
            if m in self.modules
        ]

    def get_modules_by_type(self, module_type: ModuleType) -> List[CognitiveModule]:
        """Get modules of a type"""
        return [
            m for m in self.modules.values()
            if m.module_type == module_type
        ]

    def update_state(self, **kwargs):
        """Update cognitive state"""
        for key, value in kwargs.items():
            if hasattr(self.state, key):
                setattr(self.state, key, value)

        # Notify callbacks
        for callback in self.on_state_change:
            try:
                callback(self.state)
            except Exception:
                pass

    def snapshot(self) -> Dict[str, Any]:
        """Get architecture snapshot"""
        return {
            'name': self.name,
            'modules': {
                m.id: {
                    'name': m.name,
                    'type': m.module_type.name,
                    'active': m.is_active,
                    'activation': m.activation_level
                }
                for m in self.modules.values()
            },
            'state': {
                'focus': str(self.state.focus),
                'arousal': self.state.arousal,
                'processing_level': self.state.processing_level.name,
                'available_resources': self.state.available_resources
            },
            'pipeline': self.pipeline
        }


# Export all
__all__ = [
    'ModuleType',
    'ProcessingLevel',
    'CognitiveState',
    'CognitiveModule',
    'PerceptionModule',
    'ReasoningModule',
    'CognitiveArchitecture',
]

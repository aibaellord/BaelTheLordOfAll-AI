"""
BAEL Working Memory Engine
===========================

Baddeley's Working Memory Model implementation.
Active maintenance and manipulation of information.

"Ba'el holds information in mind." — Ba'el
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
from collections import deque
import copy

logger = logging.getLogger("BAEL.WorkingMemory")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class ModalityType(Enum):
    """Sensory modality."""
    VISUAL = auto()
    AUDITORY = auto()
    SPATIAL = auto()
    SEMANTIC = auto()
    MOTOR = auto()
    EPISODIC = auto()


class AttentionState(Enum):
    """State of attention."""
    FOCUSED = auto()
    DIVIDED = auto()
    DIFFUSE = auto()
    ABSENT = auto()


@dataclass
class WorkingMemoryItem:
    """
    An item in working memory.
    """
    id: str
    content: Any
    modality: ModalityType
    activation: float = 1.0
    rehearsal_count: int = 0
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    chunks: List[Any] = field(default_factory=list)

    @property
    def age(self) -> float:
        return time.time() - self.created_at

    def access(self) -> None:
        self.last_accessed = time.time()
        self.activation = min(1.0, self.activation + 0.1)

    def decay(self, rate: float = 0.1) -> None:
        self.activation *= (1 - rate)


@dataclass
class ChunkInfo:
    """
    Information about a chunk.
    """
    id: str
    elements: List[Any]
    size: int
    familiar: bool = False

    @property
    def complexity(self) -> float:
        return math.log(self.size + 1, 2)


# ============================================================================
# PHONOLOGICAL LOOP
# ============================================================================

class PhonologicalLoop:
    """
    Verbal/acoustic working memory subsystem.

    "Ba'el rehearses inner speech." — Ba'el
    """

    def __init__(self, capacity: int = 7, decay_time: float = 2.0):
        """Initialize phonological loop."""
        self._capacity = capacity
        self._decay_time = decay_time
        self._store: deque = deque(maxlen=capacity)
        self._rehearsal_active = False
        self._rehearsal_rate = 0.3  # Items per second
        self._lock = threading.RLock()

    def add(self, item: WorkingMemoryItem) -> bool:
        """Add item to phonological store."""
        with self._lock:
            if item.modality not in [ModalityType.AUDITORY, ModalityType.SEMANTIC]:
                return False

            # Word length effect: longer items take more capacity
            word_length = len(str(item.content))
            effective_size = max(1, word_length // 3)

            # Check capacity
            current_load = sum(1 for _ in self._store)
            if current_load >= self._capacity:
                # Bump oldest
                self._store.popleft()

            self._store.append(item)
            return True

    def rehearse(self) -> List[WorkingMemoryItem]:
        """Rehearse items to prevent decay."""
        with self._lock:
            self._rehearsal_active = True
            rehearsed = []

            for item in self._store:
                item.rehearsal_count += 1
                item.activation = 1.0  # Reset activation
                rehearsed.append(item)

            return rehearsed

    def recall(self) -> List[WorkingMemoryItem]:
        """Recall items (serial order)."""
        with self._lock:
            # Primacy effect: first items better
            # Recency effect: last items better
            items = list(self._store)

            for i, item in enumerate(items):
                # Middle items decay more
                if i > 0 and i < len(items) - 1:
                    item.activation *= 0.9

            return items

    def decay_all(self) -> None:
        """Apply decay to all items."""
        with self._lock:
            if self._rehearsal_active:
                self._rehearsal_active = False
                return

            to_remove = []
            for item in self._store:
                item.decay(1.0 / self._decay_time)
                if item.activation < 0.1:
                    to_remove.append(item)

            for item in to_remove:
                self._store.remove(item)

    @property
    def items(self) -> List[WorkingMemoryItem]:
        return list(self._store)

    @property
    def load(self) -> int:
        return len(self._store)


# ============================================================================
# VISUOSPATIAL SKETCHPAD
# ============================================================================

class VisuospatialSketchpad:
    """
    Visual/spatial working memory subsystem.

    "Ba'el maintains the mind's eye." — Ba'el
    """

    def __init__(self, visual_capacity: int = 4, spatial_capacity: int = 4):
        """Initialize sketchpad."""
        self._visual_capacity = visual_capacity
        self._spatial_capacity = spatial_capacity
        self._visual_store: Dict[str, WorkingMemoryItem] = {}
        self._spatial_store: Dict[str, WorkingMemoryItem] = {}
        self._mental_image: Optional[Any] = None
        self._lock = threading.RLock()

    def add_visual(self, item: WorkingMemoryItem) -> bool:
        """Add visual item."""
        with self._lock:
            if len(self._visual_store) >= self._visual_capacity:
                # Remove lowest activation
                min_item = min(
                    self._visual_store.values(),
                    key=lambda x: x.activation
                )
                del self._visual_store[min_item.id]

            self._visual_store[item.id] = item
            return True

    def add_spatial(self, item: WorkingMemoryItem) -> bool:
        """Add spatial item."""
        with self._lock:
            if len(self._spatial_store) >= self._spatial_capacity:
                # Remove lowest activation
                min_item = min(
                    self._spatial_store.values(),
                    key=lambda x: x.activation
                )
                del self._spatial_store[min_item.id]

            self._spatial_store[item.id] = item
            return True

    def visualize(self, content: Any) -> None:
        """Create mental image."""
        with self._lock:
            self._mental_image = content

    def rotate(self, degrees: float) -> Any:
        """Mental rotation of image."""
        with self._lock:
            if self._mental_image is None:
                return None

            # Simulate rotation time (Shepard & Metzler)
            rotation_time = abs(degrees) / 50.0  # ~50 degrees per second
            time.sleep(min(rotation_time, 0.1))  # Cap at 100ms

            return {
                'original': self._mental_image,
                'rotation': degrees,
                'time': rotation_time
            }

    def scan(self, from_pos: Tuple[float, float], to_pos: Tuple[float, float]) -> float:
        """Mental scanning of image."""
        with self._lock:
            # Distance effect
            distance = math.sqrt(
                (to_pos[0] - from_pos[0]) ** 2 +
                (to_pos[1] - from_pos[1]) ** 2
            )

            scan_time = distance / 10.0  # ~10 units per second
            return scan_time

    def decay_all(self) -> None:
        """Apply decay to all items."""
        with self._lock:
            to_remove = []

            for item in list(self._visual_store.values()):
                item.decay(0.15)
                if item.activation < 0.1:
                    to_remove.append(item.id)

            for item_id in to_remove:
                del self._visual_store[item_id]

            to_remove = []
            for item in list(self._spatial_store.values()):
                item.decay(0.15)
                if item.activation < 0.1:
                    to_remove.append(item.id)

            for item_id in to_remove:
                del self._spatial_store[item_id]

    @property
    def visual_items(self) -> List[WorkingMemoryItem]:
        return list(self._visual_store.values())

    @property
    def spatial_items(self) -> List[WorkingMemoryItem]:
        return list(self._spatial_store.values())

    @property
    def total_load(self) -> int:
        return len(self._visual_store) + len(self._spatial_store)


# ============================================================================
# EPISODIC BUFFER
# ============================================================================

class EpisodicBuffer:
    """
    Multi-modal integration subsystem.

    "Ba'el binds information into episodes." — Ba'el
    """

    def __init__(self, capacity: int = 4):
        """Initialize episodic buffer."""
        self._capacity = capacity
        self._episodes: Dict[str, Dict] = {}
        self._episode_counter = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._episode_counter += 1
        return f"episode_{self._episode_counter}"

    def bind(
        self,
        items: List[WorkingMemoryItem],
        context: Optional[Dict] = None
    ) -> str:
        """Bind items into integrated episode."""
        with self._lock:
            if len(self._episodes) >= self._capacity:
                # Remove oldest
                oldest_id = min(
                    self._episodes.keys(),
                    key=lambda k: self._episodes[k]['timestamp']
                )
                del self._episodes[oldest_id]

            episode_id = self._generate_id()

            self._episodes[episode_id] = {
                'items': items,
                'context': context or {},
                'timestamp': time.time(),
                'accessed': 0,
                'modalities': list(set(i.modality for i in items))
            }

            return episode_id

    def retrieve(self, episode_id: str) -> Optional[Dict]:
        """Retrieve episode."""
        with self._lock:
            if episode_id not in self._episodes:
                return None

            episode = self._episodes[episode_id]
            episode['accessed'] += 1

            return episode.copy()

    def integrate_with_ltm(self, ltm_content: Any, episode_id: str) -> bool:
        """Integrate long-term memory with episode."""
        with self._lock:
            if episode_id not in self._episodes:
                return False

            self._episodes[episode_id]['ltm_link'] = ltm_content
            return True

    def get_recent(self, n: int = 3) -> List[Dict]:
        """Get recent episodes."""
        with self._lock:
            sorted_episodes = sorted(
                self._episodes.values(),
                key=lambda e: e['timestamp'],
                reverse=True
            )
            return sorted_episodes[:n]

    @property
    def episodes(self) -> List[Dict]:
        return list(self._episodes.values())

    @property
    def load(self) -> int:
        return len(self._episodes)


# ============================================================================
# CENTRAL EXECUTIVE
# ============================================================================

class CentralExecutive:
    """
    Attentional control system.

    "Ba'el controls its cognitive resources." — Ba'el
    """

    def __init__(
        self,
        phonological: PhonologicalLoop,
        visuospatial: VisuospatialSketchpad,
        episodic: EpisodicBuffer
    ):
        """Initialize central executive."""
        self._phonological = phonological
        self._visuospatial = visuospatial
        self._episodic = episodic
        self._attention_state = AttentionState.FOCUSED
        self._attention_capacity = 1.0
        self._current_task: Optional[str] = None
        self._task_switching_cost = 0.2
        self._lock = threading.RLock()

    def focus_attention(self, target: str) -> None:
        """Focus attention on target."""
        with self._lock:
            if self._current_task and self._current_task != target:
                # Task switching cost
                self._attention_capacity -= self._task_switching_cost

            self._current_task = target
            self._attention_state = AttentionState.FOCUSED

    def divide_attention(self, targets: List[str]) -> Dict[str, float]:
        """Divide attention among targets."""
        with self._lock:
            self._attention_state = AttentionState.DIVIDED

            # Attention divided, less efficient
            share = self._attention_capacity / len(targets) * 0.8  # 20% loss

            return {target: share for target in targets}

    def allocate_to_subsystem(
        self,
        item: WorkingMemoryItem,
        priority: float = 0.5
    ) -> str:
        """Allocate item to appropriate subsystem."""
        with self._lock:
            modality = item.modality

            if modality in [ModalityType.AUDITORY, ModalityType.SEMANTIC]:
                self._phonological.add(item)
                return "phonological"
            elif modality == ModalityType.VISUAL:
                self._visuospatial.add_visual(item)
                return "visuospatial_visual"
            elif modality == ModalityType.SPATIAL:
                self._visuospatial.add_spatial(item)
                return "visuospatial_spatial"
            else:
                # Episodic buffer as fallback
                self._episodic.bind([item])
                return "episodic"

    def coordinate_subsystems(self) -> Dict[str, Any]:
        """Coordinate all subsystems."""
        with self._lock:
            # Gather from all subsystems
            phonological_items = self._phonological.items
            visual_items = self._visuospatial.visual_items
            spatial_items = self._visuospatial.spatial_items

            # Create integrated episode if multiple modalities
            all_items = phonological_items + visual_items + spatial_items

            if len(all_items) > 1:
                episode_id = self._episodic.bind(all_items, {
                    'coordination_time': time.time()
                })

                return {
                    'episode_id': episode_id,
                    'items_integrated': len(all_items),
                    'modalities': list(set(i.modality.name for i in all_items))
                }

            return {'status': 'nothing_to_coordinate'}

    def inhibit(self, item_id: str) -> bool:
        """Inhibit/suppress item."""
        with self._lock:
            # Reduce activation in all stores
            for item in self._phonological.items:
                if item.id == item_id:
                    item.activation = 0.0
                    return True

            for item in self._visuospatial.visual_items:
                if item.id == item_id:
                    item.activation = 0.0
                    return True

            return False

    def update(
        self,
        item_id: str,
        new_content: Any
    ) -> bool:
        """Update item content (updating function)."""
        with self._lock:
            for item in self._phonological.items:
                if item.id == item_id:
                    item.content = new_content
                    item.access()
                    return True

            for item in self._visuospatial.visual_items:
                if item.id == item_id:
                    item.content = new_content
                    item.access()
                    return True

            return False

    def shift_attention(self, from_target: str, to_target: str) -> float:
        """Shift attention (shifting function)."""
        with self._lock:
            cost = self._task_switching_cost
            self._attention_capacity = max(0.3, self._attention_capacity - cost)
            self._current_task = to_target

            return cost

    @property
    def total_load(self) -> int:
        """Get total working memory load."""
        return (
            self._phonological.load +
            self._visuospatial.total_load +
            self._episodic.load
        )

    @property
    def attention_state(self) -> AttentionState:
        return self._attention_state


# ============================================================================
# WORKING MEMORY ENGINE
# ============================================================================

class WorkingMemoryEngine:
    """
    Complete Baddeley working memory model.

    "Ba'el holds the world in mind." — Ba'el
    """

    def __init__(
        self,
        phonological_capacity: int = 7,
        visual_capacity: int = 4,
        spatial_capacity: int = 4,
        episodic_capacity: int = 4
    ):
        """Initialize working memory engine."""
        self._phonological = PhonologicalLoop(phonological_capacity)
        self._visuospatial = VisuospatialSketchpad(visual_capacity, spatial_capacity)
        self._episodic = EpisodicBuffer(episodic_capacity)
        self._executive = CentralExecutive(
            self._phonological,
            self._visuospatial,
            self._episodic
        )
        self._item_counter = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._item_counter += 1
        return f"wm_item_{self._item_counter}"

    def encode(
        self,
        content: Any,
        modality: ModalityType = ModalityType.SEMANTIC
    ) -> WorkingMemoryItem:
        """Encode item into working memory."""
        with self._lock:
            item = WorkingMemoryItem(
                id=self._generate_id(),
                content=content,
                modality=modality
            )

            self._executive.allocate_to_subsystem(item)

            return item

    def encode_verbal(self, content: str) -> WorkingMemoryItem:
        """Encode verbal content."""
        return self.encode(content, ModalityType.AUDITORY)

    def encode_visual(self, content: Any) -> WorkingMemoryItem:
        """Encode visual content."""
        return self.encode(content, ModalityType.VISUAL)

    def encode_spatial(self, content: Any) -> WorkingMemoryItem:
        """Encode spatial content."""
        return self.encode(content, ModalityType.SPATIAL)

    def rehearse(self) -> List[WorkingMemoryItem]:
        """Rehearse phonological content."""
        return self._phonological.rehearse()

    def visualize(self, content: Any) -> None:
        """Create mental image."""
        self._visuospatial.visualize(content)

    def mental_rotate(self, degrees: float) -> Any:
        """Mental rotation."""
        return self._visuospatial.rotate(degrees)

    def bind_episode(
        self,
        items: List[WorkingMemoryItem],
        context: Optional[Dict] = None
    ) -> str:
        """Bind items into episode."""
        return self._episodic.bind(items, context)

    def focus(self, target: str) -> None:
        """Focus attention."""
        self._executive.focus_attention(target)

    def divide(self, targets: List[str]) -> Dict[str, float]:
        """Divide attention."""
        return self._executive.divide_attention(targets)

    def shift(self, from_target: str, to_target: str) -> float:
        """Shift attention."""
        return self._executive.shift_attention(from_target, to_target)

    def update_item(self, item_id: str, new_content: Any) -> bool:
        """Update item."""
        return self._executive.update(item_id, new_content)

    def inhibit_item(self, item_id: str) -> bool:
        """Inhibit item."""
        return self._executive.inhibit(item_id)

    def coordinate(self) -> Dict[str, Any]:
        """Coordinate subsystems."""
        return self._executive.coordinate_subsystems()

    def step(self) -> Dict[str, Any]:
        """Execute one maintenance cycle."""
        with self._lock:
            # Decay all subsystems
            self._phonological.decay_all()
            self._visuospatial.decay_all()

            return {
                'phonological_load': self._phonological.load,
                'visuospatial_load': self._visuospatial.total_load,
                'episodic_load': self._episodic.load,
                'total_load': self._executive.total_load,
                'attention_state': self._executive.attention_state.name
            }

    def get_all_items(self) -> Dict[str, List[WorkingMemoryItem]]:
        """Get all items from all subsystems."""
        return {
            'phonological': self._phonological.items,
            'visual': self._visuospatial.visual_items,
            'spatial': self._visuospatial.spatial_items
        }

    @property
    def capacity(self) -> Dict[str, int]:
        """Get capacity info."""
        return {
            'phonological': self._phonological._capacity,
            'visual': self._visuospatial._visual_capacity,
            'spatial': self._visuospatial._spatial_capacity,
            'episodic': self._episodic._capacity
        }

    @property
    def load(self) -> int:
        """Get total load."""
        return self._executive.total_load

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'phonological_load': self._phonological.load,
            'visual_load': len(self._visuospatial.visual_items),
            'spatial_load': len(self._visuospatial.spatial_items),
            'episodic_load': self._episodic.load,
            'total_load': self._executive.total_load,
            'attention': self._executive.attention_state.name
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_working_memory_engine(
    phonological_capacity: int = 7,
    visual_capacity: int = 4,
    spatial_capacity: int = 4,
    episodic_capacity: int = 4
) -> WorkingMemoryEngine:
    """Create working memory engine."""
    return WorkingMemoryEngine(
        phonological_capacity,
        visual_capacity,
        spatial_capacity,
        episodic_capacity
    )


def create_phonological_loop(capacity: int = 7) -> PhonologicalLoop:
    """Create phonological loop."""
    return PhonologicalLoop(capacity)


def create_visuospatial_sketchpad(
    visual_capacity: int = 4,
    spatial_capacity: int = 4
) -> VisuospatialSketchpad:
    """Create visuospatial sketchpad."""
    return VisuospatialSketchpad(visual_capacity, spatial_capacity)


def create_episodic_buffer(capacity: int = 4) -> EpisodicBuffer:
    """Create episodic buffer."""
    return EpisodicBuffer(capacity)

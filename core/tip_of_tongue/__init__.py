"""
BAEL Tip of Tongue Engine
==========================

Retrieval failure and feeling of knowing.
TOT phenomenon and metacognitive monitoring.

"Ba'el senses blocked knowledge." — Ba'el
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

logger = logging.getLogger("BAEL.TipOfTongue")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class RetrievalState(Enum):
    """States of retrieval."""
    UNKNOWN = auto()       # No knowledge
    TOT = auto()           # Tip of tongue
    FAMILIAR = auto()      # Know it but can't retrieve
    PARTIAL = auto()       # Have partial info
    RETRIEVED = auto()     # Successfully retrieved
    WRONG = auto()         # Retrieved wrong item


class PartialType(Enum):
    """Types of partial information."""
    FIRST_LETTER = auto()   # First letter/sound
    SYLLABLES = auto()      # Number of syllables
    SIMILAR = auto()        # Similar sounding word
    SEMANTIC = auto()       # Meaning-related
    CONTEXTUAL = auto()     # Where/when learned


class FOKLevel(Enum):
    """Feeling of Knowing levels."""
    ZERO = 0               # No feeling of knowing
    LOW = 1                # Slight familiarity
    MODERATE = 2           # Think I know it
    HIGH = 3               # Pretty sure I know
    CERTAIN = 4            # Definitely know


class ResolutionType(Enum):
    """How TOT resolved."""
    POP_UP = auto()        # Suddenly came to mind
    CUE_HELPED = auto()    # External cue helped
    GAVE_UP = auto()       # Stopped trying
    BLOCKED = auto()       # Wrong item blocked correct


@dataclass
class MemoryItem:
    """
    An item in memory.
    """
    id: str
    target: str                  # The word/name to retrieve
    phonology: Dict[str, Any]    # Phonological features
    semantics: List[str]         # Semantic features
    frequency: float = 0.5       # How often accessed
    recency: float = 0.5         # How recently accessed
    strength: float = 0.5        # Memory strength


@dataclass
class PartialInfo:
    """
    Partial information during TOT.
    """
    partial_type: PartialType
    content: Any
    confidence: float


@dataclass
class TOTState:
    """
    Tip of tongue state.
    """
    item_id: str
    fok: FOKLevel
    partial_info: List[PartialInfo]
    attempts: int
    blockers: List[str]      # Blocking items
    start_time: float
    resolved: bool = False
    resolution: Optional[ResolutionType] = None


@dataclass
class RetrievalAttempt:
    """
    A retrieval attempt record.
    """
    item_id: str
    state: RetrievalState
    response: Optional[str]
    correct: bool
    response_time: float
    had_tot: bool


@dataclass
class TOTMetrics:
    """
    TOT phenomenon metrics.
    """
    tot_rate: float           # Proportion of TOTs
    resolution_rate: float    # Proportion resolved
    avg_resolution_time: float
    fok_accuracy: float       # Were FOKs correct?


# ============================================================================
# PHONOLOGICAL ANALYZER
# ============================================================================

class PhonologicalAnalyzer:
    """
    Analyze phonological features.

    "Ba'el hears word sounds." — Ba'el
    """

    def __init__(self):
        """Initialize analyzer."""
        self._lock = threading.RLock()

    def analyze(
        self,
        word: str
    ) -> Dict[str, Any]:
        """Extract phonological features."""
        return {
            'first_letter': word[0].lower() if word else '',
            'last_letter': word[-1].lower() if word else '',
            'length': len(word),
            'syllables': self._estimate_syllables(word),
            'vowels': sum(1 for c in word.lower() if c in 'aeiou'),
            'consonants': sum(1 for c in word.lower() if c.isalpha() and c not in 'aeiou')
        }

    def _estimate_syllables(
        self,
        word: str
    ) -> int:
        """Estimate number of syllables."""
        word = word.lower()
        count = 0
        vowels = "aeiouy"
        prev_was_vowel = False

        for char in word:
            is_vowel = char in vowels
            if is_vowel and not prev_was_vowel:
                count += 1
            prev_was_vowel = is_vowel

        # Handle silent e
        if word.endswith('e'):
            count -= 1

        return max(1, count)

    def similarity(
        self,
        word1: str,
        word2: str
    ) -> float:
        """Calculate phonological similarity."""
        feat1 = self.analyze(word1)
        feat2 = self.analyze(word2)

        score = 0.0

        # First letter match
        if feat1['first_letter'] == feat2['first_letter']:
            score += 0.3

        # Syllable match
        if feat1['syllables'] == feat2['syllables']:
            score += 0.2

        # Length similarity
        len_ratio = min(feat1['length'], feat2['length']) / max(feat1['length'], feat2['length'])
        score += 0.2 * len_ratio

        # Last letter match
        if feat1['last_letter'] == feat2['last_letter']:
            score += 0.15

        # Vowel ratio similarity
        vowel_ratio1 = feat1['vowels'] / max(1, feat1['length'])
        vowel_ratio2 = feat2['vowels'] / max(1, feat2['length'])
        score += 0.15 * (1 - abs(vowel_ratio1 - vowel_ratio2))

        return min(1.0, score)


# ============================================================================
# TOT DETECTOR
# ============================================================================

class TOTDetector:
    """
    Detect and characterize TOT states.

    "Ba'el senses retrieval blocks." — Ba'el
    """

    def __init__(
        self,
        phonology: PhonologicalAnalyzer
    ):
        """Initialize detector."""
        self._phonology = phonology
        self._lock = threading.RLock()

    def detect(
        self,
        item: MemoryItem,
        retrieval_strength: float
    ) -> Optional[TOTState]:
        """Detect if in TOT state."""
        # TOT occurs when:
        # 1. Strong semantic activation (high FOK)
        # 2. Weak phonological activation (can't retrieve)

        semantic_strength = len(item.semantics) * 0.1 + item.frequency * 0.3
        phonological_strength = retrieval_strength

        # Calculate FOK
        fok = self._calculate_fok(semantic_strength, item.frequency, item.recency)

        # TOT if high FOK but low retrieval
        if fok.value >= 2 and phonological_strength < 0.3:
            return TOTState(
                item_id=item.id,
                fok=fok,
                partial_info=[],
                attempts=1,
                blockers=[],
                start_time=time.time()
            )

        return None

    def _calculate_fok(
        self,
        semantic_strength: float,
        frequency: float,
        recency: float
    ) -> FOKLevel:
        """Calculate feeling of knowing."""
        fok_score = (
            semantic_strength * 0.4 +
            frequency * 0.3 +
            recency * 0.3
        )

        if fok_score < 0.2:
            return FOKLevel.ZERO
        elif fok_score < 0.4:
            return FOKLevel.LOW
        elif fok_score < 0.6:
            return FOKLevel.MODERATE
        elif fok_score < 0.8:
            return FOKLevel.HIGH
        else:
            return FOKLevel.CERTAIN

    def extract_partial(
        self,
        item: MemoryItem,
        tot_state: TOTState
    ) -> List[PartialInfo]:
        """Extract partial information during TOT."""
        partials = []
        phonology = item.phonology

        # First letter (often available during TOT)
        if random.random() < 0.5:  # 50% chance
            partials.append(PartialInfo(
                partial_type=PartialType.FIRST_LETTER,
                content=phonology.get('first_letter', '?'),
                confidence=0.7
            ))

        # Number of syllables
        if random.random() < 0.4:  # 40% chance
            partials.append(PartialInfo(
                partial_type=PartialType.SYLLABLES,
                content=phonology.get('syllables', 0),
                confidence=0.5
            ))

        # Semantic info (usually available)
        if item.semantics:
            partials.append(PartialInfo(
                partial_type=PartialType.SEMANTIC,
                content=item.semantics[0],
                confidence=0.8
            ))

        return partials


# ============================================================================
# BLOCKER HANDLER
# ============================================================================

class BlockerHandler:
    """
    Handle blocking items in TOT.

    "Ba'el removes mental blocks." — Ba'el
    """

    def __init__(
        self,
        phonology: PhonologicalAnalyzer
    ):
        """Initialize handler."""
        self._phonology = phonology
        self._lock = threading.RLock()

    def find_blockers(
        self,
        target: MemoryItem,
        candidates: List[MemoryItem]
    ) -> List[str]:
        """Find items that might be blocking retrieval."""
        blockers = []

        for candidate in candidates:
            if candidate.id == target.id:
                continue

            # Check phonological similarity
            similarity = self._phonology.similarity(target.target, candidate.target)

            # High similarity + high strength = blocker
            if similarity > 0.5 and candidate.strength > target.strength:
                blockers.append(candidate.target)

        return blockers[:3]  # Top 3 blockers

    def suppress_blocker(
        self,
        blocker: str,
        suppression_strength: float = 0.5
    ) -> bool:
        """Attempt to suppress a blocking item."""
        # Simulation: suppression sometimes works
        success = random.random() < suppression_strength
        return success


# ============================================================================
# TOT RESOLVER
# ============================================================================

class TOTResolver:
    """
    Resolve TOT states.

    "Ba'el retrieves blocked memories." — Ba'el
    """

    def __init__(
        self,
        phonology: PhonologicalAnalyzer,
        blocker_handler: BlockerHandler
    ):
        """Initialize resolver."""
        self._phonology = phonology
        self._blockers = blocker_handler
        self._lock = threading.RLock()

    def attempt_resolution(
        self,
        item: MemoryItem,
        tot_state: TOTState,
        method: str = "search"
    ) -> Tuple[bool, Optional[ResolutionType]]:
        """Attempt to resolve TOT state."""
        # Increase attempts
        tot_state.attempts += 1

        # Resolution probability increases with:
        # - More attempts (to a point)
        # - Higher FOK
        # - More partial info

        base_prob = 0.1
        fok_bonus = tot_state.fok.value * 0.1
        partial_bonus = len(tot_state.partial_info) * 0.05
        attempt_bonus = min(0.2, tot_state.attempts * 0.03)

        resolution_prob = base_prob + fok_bonus + partial_bonus + attempt_bonus

        if random.random() < resolution_prob:
            # Resolved!
            tot_state.resolved = True

            if tot_state.attempts == 1:
                tot_state.resolution = ResolutionType.POP_UP
            elif method == "cue":
                tot_state.resolution = ResolutionType.CUE_HELPED
            else:
                tot_state.resolution = ResolutionType.POP_UP

            return True, tot_state.resolution

        return False, None

    def provide_cue(
        self,
        item: MemoryItem,
        tot_state: TOTState,
        cue: str
    ) -> Tuple[bool, Optional[ResolutionType]]:
        """Provide external cue to help resolution."""
        # Check if cue matches target
        cue_helps = False

        # First letter cue
        if cue.lower() == item.target[0].lower():
            cue_helps = True

        # Semantic cue
        if cue.lower() in [s.lower() for s in item.semantics]:
            cue_helps = True

        if cue_helps:
            # Higher resolution probability with helpful cue
            if random.random() < 0.7:
                tot_state.resolved = True
                tot_state.resolution = ResolutionType.CUE_HELPED
                return True, ResolutionType.CUE_HELPED

        return self.attempt_resolution(item, tot_state, method="cue")


# ============================================================================
# TIP OF TONGUE ENGINE
# ============================================================================

class TipOfTongueEngine:
    """
    Complete tip of tongue engine.

    "Ba'el's TOT phenomenon system." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._phonology = PhonologicalAnalyzer()
        self._detector = TOTDetector(self._phonology)
        self._blocker_handler = BlockerHandler(self._phonology)
        self._resolver = TOTResolver(self._phonology, self._blocker_handler)

        self._items: Dict[str, MemoryItem] = {}
        self._tot_states: Dict[str, TOTState] = {}
        self._attempts: List[RetrievalAttempt] = []

        self._item_counter = 0

        self._lock = threading.RLock()

    def _generate_item_id(self) -> str:
        self._item_counter += 1
        return f"item_{self._item_counter}"

    # Item management

    def add_item(
        self,
        target: str,
        semantics: List[str] = None,
        frequency: float = 0.5,
        strength: float = 0.5
    ) -> MemoryItem:
        """Add a memory item."""
        phonology = self._phonology.analyze(target)

        item = MemoryItem(
            id=self._generate_item_id(),
            target=target,
            phonology=phonology,
            semantics=semantics or [],
            frequency=frequency,
            recency=0.5,
            strength=strength
        )

        self._items[item.id] = item
        return item

    def add_vocabulary(
        self,
        words: List[Dict[str, Any]]
    ) -> List[MemoryItem]:
        """Add multiple words."""
        return [
            self.add_item(
                w.get('word', ''),
                w.get('semantics', []),
                w.get('frequency', 0.5),
                w.get('strength', 0.5)
            )
            for w in words
        ]

    # Retrieval

    def retrieve(
        self,
        item_id: str
    ) -> Tuple[RetrievalState, Optional[str]]:
        """Attempt to retrieve an item."""
        if item_id not in self._items:
            return RetrievalState.UNKNOWN, None

        item = self._items[item_id]

        # Calculate retrieval probability
        retrieval_prob = item.strength * item.frequency * item.recency

        if random.random() < retrieval_prob:
            # Successful retrieval
            self._attempts.append(RetrievalAttempt(
                item_id=item_id,
                state=RetrievalState.RETRIEVED,
                response=item.target,
                correct=True,
                response_time=random.uniform(0.5, 1.5),
                had_tot=False
            ))
            return RetrievalState.RETRIEVED, item.target
        else:
            # Check for TOT
            tot = self._detector.detect(item, retrieval_prob)

            if tot:
                # Enter TOT state
                tot.partial_info = self._detector.extract_partial(item, tot)

                # Find blockers
                tot.blockers = self._blocker_handler.find_blockers(
                    item, list(self._items.values())
                )

                self._tot_states[item_id] = tot

                self._attempts.append(RetrievalAttempt(
                    item_id=item_id,
                    state=RetrievalState.TOT,
                    response=None,
                    correct=False,
                    response_time=random.uniform(2.0, 5.0),
                    had_tot=True
                ))

                return RetrievalState.TOT, None
            else:
                # Just unknown
                return RetrievalState.UNKNOWN, None

    def retrieve_by_cue(
        self,
        cue: str
    ) -> List[Tuple[str, float]]:
        """Retrieve items by semantic cue."""
        matches = []

        for item in self._items.values():
            if cue.lower() in [s.lower() for s in item.semantics]:
                matches.append((item.id, item.strength))

        return sorted(matches, key=lambda x: x[1], reverse=True)

    # TOT handling

    def get_tot_state(
        self,
        item_id: str
    ) -> Optional[TOTState]:
        """Get TOT state for item."""
        return self._tot_states.get(item_id)

    def get_partial_info(
        self,
        item_id: str
    ) -> List[PartialInfo]:
        """Get partial information during TOT."""
        tot = self._tot_states.get(item_id)
        return tot.partial_info if tot else []

    def get_blockers(
        self,
        item_id: str
    ) -> List[str]:
        """Get blocking items."""
        tot = self._tot_states.get(item_id)
        return tot.blockers if tot else []

    def try_resolve(
        self,
        item_id: str,
        cue: str = None
    ) -> Tuple[bool, Optional[str]]:
        """Try to resolve TOT state."""
        if item_id not in self._tot_states:
            return False, None

        item = self._items.get(item_id)
        if not item:
            return False, None

        tot = self._tot_states[item_id]

        if cue:
            resolved, resolution = self._resolver.provide_cue(item, tot, cue)
        else:
            resolved, resolution = self._resolver.attempt_resolution(item, tot)

        if resolved:
            return True, item.target
        return False, None

    # Analysis

    def get_fok(
        self,
        item_id: str
    ) -> FOKLevel:
        """Get feeling of knowing for item."""
        tot = self._tot_states.get(item_id)
        if tot:
            return tot.fok

        item = self._items.get(item_id)
        if item:
            semantic_strength = len(item.semantics) * 0.1
            fok_score = semantic_strength + item.frequency * 0.5

            if fok_score < 0.3:
                return FOKLevel.LOW
            elif fok_score < 0.6:
                return FOKLevel.MODERATE
            else:
                return FOKLevel.HIGH

        return FOKLevel.ZERO

    def fok_accuracy(self) -> float:
        """Calculate FOK accuracy."""
        if not self._attempts:
            return 0.0

        accurate = 0
        total = 0

        for attempt in self._attempts:
            if attempt.had_tot:
                tot = self._tot_states.get(attempt.item_id)
                if tot:
                    # High FOK should lead to eventual retrieval
                    if tot.fok.value >= 3:
                        total += 1
                        if tot.resolved:
                            accurate += 1

        return accurate / total if total > 0 else 0.0

    # Metrics

    def get_metrics(self) -> TOTMetrics:
        """Get TOT metrics."""
        if not self._attempts:
            return TOTMetrics(
                tot_rate=0.0,
                resolution_rate=0.0,
                avg_resolution_time=0.0,
                fok_accuracy=0.0
            )

        tot_count = sum(1 for a in self._attempts if a.had_tot)
        tot_rate = tot_count / len(self._attempts)

        resolved = sum(1 for t in self._tot_states.values() if t.resolved)
        resolution_rate = resolved / tot_count if tot_count > 0 else 0.0

        resolution_times = [
            time.time() - t.start_time
            for t in self._tot_states.values()
            if t.resolved
        ]
        avg_time = sum(resolution_times) / len(resolution_times) if resolution_times else 0.0

        return TOTMetrics(
            tot_rate=tot_rate,
            resolution_rate=resolution_rate,
            avg_resolution_time=avg_time,
            fok_accuracy=self.fok_accuracy()
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'items': len(self._items),
            'active_tots': sum(1 for t in self._tot_states.values() if not t.resolved),
            'attempts': len(self._attempts)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_tip_of_tongue_engine() -> TipOfTongueEngine:
    """Create TOT engine."""
    return TipOfTongueEngine()


def demonstrate_tot_phenomenon() -> Dict[str, Any]:
    """Demonstrate the TOT phenomenon."""
    engine = create_tip_of_tongue_engine()

    # Add some words
    engine.add_item("sextant", ["navigation", "instrument", "sailing"], strength=0.3)
    engine.add_item("protractor", ["angle", "measurement", "geometry"], strength=0.7)
    engine.add_item("astrolabe", ["astronomy", "navigation", "ancient"], strength=0.2)

    # Try to retrieve
    items = list(engine._items.values())
    results = []

    for item in items:
        state, response = engine.retrieve(item.id)

        result = {
            'target': item.target,
            'state': state.name,
            'retrieved': response
        }

        if state == RetrievalState.TOT:
            partial = engine.get_partial_info(item.id)
            result['partial_info'] = [
                {'type': p.partial_type.name, 'content': p.content}
                for p in partial
            ]
            result['fok'] = engine.get_fok(item.id).name
            result['blockers'] = engine.get_blockers(item.id)

        results.append(result)

    return {'retrieval_results': results}


def get_tot_facts() -> Dict[str, str]:
    """Get facts about tip of tongue."""
    return {
        'brown_mcneill_1966': 'First systematic study of TOT phenomenon',
        'prevalence': 'TOT occurs about once a week in young adults',
        'aging': 'TOT frequency increases with age',
        'proper_names': 'Proper names are especially prone to TOT',
        'partial_info': 'First letter is often available during TOT',
        'blockers': 'Wrong words can block correct retrieval',
        'resolution': 'Most TOTs resolve within minutes',
        'fok': 'Feeling of knowing predicts later retrieval success'
    }

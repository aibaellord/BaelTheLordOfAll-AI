"""
BAEL Pegword Mnemonic System Engine
=====================================

Number-rhyme pegs for memorizing ordered lists.
One-bun, two-shoe, three-tree...

"Ba'el's rhymes carry infinite information." — Ba'el
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

logger = logging.getLogger("BAEL.PegwordMnemonicSystem")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class PegwordType(Enum):
    """Type of pegword system."""
    RHYME = auto()        # One-bun, two-shoe
    SHAPE = auto()        # 1 looks like candle
    PHONETIC = auto()     # Major system


class ImageryQuality(Enum):
    """Quality of imagery created."""
    WEAK = auto()
    MODERATE = auto()
    VIVID = auto()
    BIZARRE = auto()


class InteractionType(Enum):
    """Type of peg-item interaction."""
    SIMPLE = auto()       # Item near peg
    INTERACTIVE = auto()  # Item interacts with peg
    BIZARRE = auto()       # Strange interaction
    ANIMATED = auto()      # Moving scene


class RetrievalMode(Enum):
    """Mode of retrieval."""
    SEQUENTIAL = auto()   # 1, 2, 3...
    RANDOM = auto()        # Any order
    CUE_DRIVEN = auto()    # Given position


@dataclass
class Pegword:
    """
    A pegword.
    """
    position: int
    word: str
    rhymes_with: str
    imageability: float


@dataclass
class PairedItem:
    """
    An item paired with a pegword.
    """
    id: str
    content: str
    pegword: Pegword
    imagery: str
    interaction_type: InteractionType
    imagery_quality: ImageryQuality


@dataclass
class RetrievalTrial:
    """
    A retrieval trial.
    """
    item: PairedItem
    position_cued: int
    recalled: bool
    position_correct: bool
    latency_ms: int


@dataclass
class PegwordMetrics:
    """
    Pegword system metrics.
    """
    recall_rate: float
    position_accuracy: float
    average_latency: float
    advantage_over_rote: float


# ============================================================================
# STANDARD PEGWORDS
# ============================================================================

STANDARD_PEGWORDS = [
    Pegword(1, "bun", "one", 0.9),
    Pegword(2, "shoe", "two", 0.9),
    Pegword(3, "tree", "three", 0.9),
    Pegword(4, "door", "four", 0.85),
    Pegword(5, "hive", "five", 0.8),
    Pegword(6, "sticks", "six", 0.85),
    Pegword(7, "heaven", "seven", 0.75),
    Pegword(8, "gate", "eight", 0.85),
    Pegword(9, "wine", "nine", 0.85),
    Pegword(10, "hen", "ten", 0.9),
    Pegword(11, "lever", "eleven", 0.7),
    Pegword(12, "elf", "twelve", 0.8),
]


# ============================================================================
# PEGWORD MODEL
# ============================================================================

class PegwordModel:
    """
    Model of pegword mnemonic.
    
    "Ba'el's rhyme-memory model." — Ba'el
    """
    
    def __init__(self):
        """Initialize model."""
        # Base rates
        self._base_rote_recall = 0.45
        
        # Pegword advantage
        self._pegword_advantage = 0.30
        
        # Imagery quality effects
        self._imagery_effects = {
            ImageryQuality.WEAK: -0.10,
            ImageryQuality.MODERATE: 0.0,
            ImageryQuality.VIVID: 0.12,
            ImageryQuality.BIZARRE: 0.18
        }
        
        # Interaction effects
        self._interaction_effects = {
            InteractionType.SIMPLE: 0.0,
            InteractionType.INTERACTIVE: 0.10,
            InteractionType.BIZARRE: 0.15,
            InteractionType.ANIMATED: 0.12
        }
        
        # Pegword imageability
        self._imageability_weight = 0.15
        
        # Position accuracy
        self._position_accuracy_base = 0.90
        
        # Random access advantage
        self._random_access_boost = 0.10
        
        # Retrieval time
        self._base_rt_ms = 1200
        self._rt_per_position = 100
        
        # Learning effects
        self._peg_overlearning = 0.08  # Overlearned pegs help
        
        self._lock = threading.RLock()
    
    def calculate_recall_probability(
        self,
        item: PairedItem
    ) -> float:
        """Calculate recall probability."""
        base = self._base_rote_recall + self._pegword_advantage
        
        # Imagery quality
        base += self._imagery_effects[item.imagery_quality]
        
        # Interaction type
        base += self._interaction_effects[item.interaction_type]
        
        # Pegword imageability
        base += item.pegword.imageability * self._imageability_weight
        
        # Overlearned pegs
        if item.pegword.position <= 10:
            base += self._peg_overlearning
        
        # Add noise
        base += random.uniform(-0.08, 0.08)
        
        return max(0.20, min(0.98, base))
    
    def calculate_position_accuracy(
        self,
        item: PairedItem
    ) -> float:
        """Calculate position accuracy."""
        base = self._position_accuracy_base
        
        # Pegword distinctiveness helps
        base += item.pegword.imageability * 0.05
        
        # Add noise
        base += random.uniform(-0.05, 0.05)
        
        return max(0.60, min(0.99, base))
    
    def calculate_retrieval_time(
        self,
        position: int,
        mode: RetrievalMode
    ) -> int:
        """Calculate retrieval time."""
        if mode == RetrievalMode.CUE_DRIVEN:
            # Direct access
            rt = self._base_rt_ms
        else:
            # Sequential scan
            rt = self._base_rt_ms + position * self._rt_per_position
        
        rt += random.gauss(0, 200)
        return max(500, int(rt))
    
    def get_principles(
        self
    ) -> Dict[str, str]:
        """Get pegword principles."""
        return {
            'overlearn_pegs': 'Learn pegwords thoroughly first',
            'vivid_imagery': 'Create vivid mental images',
            'interaction': 'Have item interact with peg',
            'bizarreness': 'Strange images more memorable',
            'rehearse': 'Practice retrieval'
        }
    
    def get_advantages(
        self
    ) -> Dict[str, str]:
        """Get pegword advantages."""
        return {
            'random_access': 'Can retrieve any position directly',
            'position_encoding': 'Automatic position information',
            'quick_learning': 'Faster than method of loci',
            'portable': 'No physical location needed'
        }
    
    def get_limitations(
        self
    ) -> Dict[str, str]:
        """Get pegword limitations."""
        return {
            'capacity': 'Limited by number of pegs',
            'interference': 'Reuse causes interference',
            'abstraction': 'Hard with abstract items',
            'extension': 'Hard to extend beyond 10-20'
        }


# ============================================================================
# PEGWORD SYSTEM
# ============================================================================

class PegwordSystem:
    """
    Pegword mnemonic system.
    
    "Ba'el's rhyme-based memory system." — Ba'el
    """
    
    def __init__(self):
        """Initialize system."""
        self._model = PegwordModel()
        
        self._pegwords = {p.position: p for p in STANDARD_PEGWORDS}
        self._paired_items: Dict[str, PairedItem] = {}
        self._trials: List[RetrievalTrial] = []
        
        self._counter = 0
        self._lock = threading.RLock()
    
    def _generate_id(self) -> str:
        self._counter += 1
        return f"item_{self._counter}"
    
    def get_pegword(self, position: int) -> Optional[Pegword]:
        """Get pegword for position."""
        return self._pegwords.get(position)
    
    def pair_item(
        self,
        content: str,
        position: int,
        interaction_type: InteractionType = InteractionType.INTERACTIVE,
        imagery_quality: ImageryQuality = ImageryQuality.VIVID
    ) -> Optional[PairedItem]:
        """Pair item with pegword."""
        pegword = self.get_pegword(position)
        if not pegword:
            return None
        
        item = PairedItem(
            id=self._generate_id(),
            content=content,
            pegword=pegword,
            imagery=f"{content} interacting with {pegword.word}",
            interaction_type=interaction_type,
            imagery_quality=imagery_quality
        )
        
        self._paired_items[item.id] = item
        
        return item
    
    def retrieve_by_position(
        self,
        position: int
    ) -> Optional[RetrievalTrial]:
        """Retrieve item by position."""
        # Find item at position
        item = None
        for pi in self._paired_items.values():
            if pi.pegword.position == position:
                item = pi
                break
        
        if not item:
            return None
        
        prob = self._model.calculate_recall_probability(item)
        recalled = random.random() < prob
        
        pos_acc = self._model.calculate_position_accuracy(item)
        position_correct = random.random() < pos_acc if recalled else False
        
        rt = self._model.calculate_retrieval_time(
            position, RetrievalMode.CUE_DRIVEN
        )
        
        trial = RetrievalTrial(
            item=item,
            position_cued=position,
            recalled=recalled,
            position_correct=position_correct,
            latency_ms=rt
        )
        
        self._trials.append(trial)
        
        return trial


# ============================================================================
# PEGWORD PARADIGM
# ============================================================================

class PegwordParadigm:
    """
    Pegword paradigm.
    
    "Ba'el's rhyme mnemonic study." — Ba'el
    """
    
    def __init__(self):
        """Initialize paradigm."""
        self._lock = threading.RLock()
    
    def run_basic_paradigm(
        self,
        n_items: int = 10
    ) -> Dict[str, Any]:
        """Run basic pegword paradigm."""
        system = PegwordSystem()
        
        # Pair items
        items = []
        for i in range(1, n_items + 1):
            item = system.pair_item(f"Item_{i}", i)
            if item:
                items.append(item)
        
        # Retrieve all
        results = []
        for i in range(1, n_items + 1):
            trial = system.retrieve_by_position(i)
            if trial:
                results.append(trial)
        
        # Calculate metrics
        if not results:
            return {'error': 'No results'}
        
        recall_rate = sum(r.recalled for r in results) / len(results)
        position_acc = sum(r.position_correct for r in results) / len(results)
        avg_rt = sum(r.latency_ms for r in results) / len(results)
        
        model = PegwordModel()
        advantage = recall_rate - model._base_rote_recall
        
        return {
            'recall_rate': recall_rate,
            'position_accuracy': position_acc,
            'average_rt_ms': avg_rt,
            'rote_recall': model._base_rote_recall,
            'pegword_advantage': advantage,
            'interpretation': f'Pegword advantage: {advantage:.0%}'
        }
    
    def run_imagery_study(
        self
    ) -> Dict[str, Any]:
        """Study imagery quality effects."""
        model = PegwordModel()
        
        results = {}
        
        for quality in ImageryQuality:
            boost = model._imagery_effects[quality]
            recall = (
                model._base_rote_recall + 
                model._pegword_advantage + 
                boost
            )
            results[quality.name] = {'recall': recall, 'boost': boost}
        
        return {
            'by_quality': results,
            'interpretation': 'Bizarre imagery most effective'
        }
    
    def run_interaction_study(
        self
    ) -> Dict[str, Any]:
        """Study interaction type effects."""
        model = PegwordModel()
        
        results = {}
        
        for interaction in InteractionType:
            boost = model._interaction_effects[interaction]
            recall = (
                model._base_rote_recall + 
                model._pegword_advantage + 
                boost
            )
            results[interaction.name] = {'recall': recall, 'boost': boost}
        
        return {
            'by_interaction': results,
            'interpretation': 'Bizarre interaction most effective'
        }
    
    def run_random_access_study(
        self
    ) -> Dict[str, Any]:
        """Study random access retrieval."""
        system = PegwordSystem()
        
        # Pair 10 items
        for i in range(1, 11):
            system.pair_item(f"Item_{i}", i)
        
        # Random access test
        positions = [5, 2, 8, 1, 10, 3, 7, 4, 9, 6]
        
        results = []
        for pos in positions:
            trial = system.retrieve_by_position(pos)
            if trial:
                results.append(trial)
        
        recall_rate = sum(r.recalled for r in results) / max(1, len(results))
        avg_rt = sum(r.latency_ms for r in results) / max(1, len(results))
        
        return {
            'recall_rate': recall_rate,
            'average_rt': avg_rt,
            'interpretation': 'Direct access to any position'
        }
    
    def run_pegword_list(
        self
    ) -> Dict[str, Any]:
        """Get standard pegword list."""
        pegs = {p.position: p.word for p in STANDARD_PEGWORDS}
        
        return {
            'pegwords': pegs,
            'rhyme_pattern': 'one-bun, two-shoe, etc.',
            'interpretation': 'Rhyming makes pegs memorable'
        }
    
    def run_comparison_study(
        self
    ) -> Dict[str, Any]:
        """Compare strategies."""
        model = PegwordModel()
        
        strategies = {
            'rote': model._base_rote_recall,
            'pegword_basic': model._base_rote_recall + model._pegword_advantage,
            'pegword_vivid': (
                model._base_rote_recall + 
                model._pegword_advantage + 
                model._imagery_effects[ImageryQuality.VIVID]
            ),
            'pegword_bizarre': (
                model._base_rote_recall + 
                model._pegword_advantage + 
                model._imagery_effects[ImageryQuality.BIZARRE] +
                model._interaction_effects[InteractionType.BIZARRE]
            )
        }
        
        return {
            'by_strategy': strategies,
            'best': max(strategies, key=strategies.get),
            'interpretation': 'Bizarre pegword most effective'
        }


# ============================================================================
# PEGWORD ENGINE
# ============================================================================

class PegwordEngine:
    """
    Complete pegword engine.
    
    "Ba'el's rhyme mnemonic engine." — Ba'el
    """
    
    def __init__(self):
        """Initialize engine."""
        self._paradigm = PegwordParadigm()
        self._system = PegwordSystem()
        
        self._experiment_results: List[Dict] = []
        
        self._lock = threading.RLock()
    
    # Pegword operations
    
    def get_pegword(self, position: int) -> Optional[Pegword]:
        """Get pegword."""
        return self._system.get_pegword(position)
    
    def pair_item(
        self,
        content: str,
        position: int
    ) -> Optional[PairedItem]:
        """Pair item."""
        return self._system.pair_item(content, position)
    
    def retrieve_by_position(
        self,
        position: int
    ) -> Optional[RetrievalTrial]:
        """Retrieve by position."""
        return self._system.retrieve_by_position(position)
    
    # Experiments
    
    def run_basic(
        self
    ) -> Dict[str, Any]:
        """Run basic paradigm."""
        result = self._paradigm.run_basic_paradigm()
        self._experiment_results.append(result)
        return result
    
    def study_imagery(
        self
    ) -> Dict[str, Any]:
        """Study imagery."""
        return self._paradigm.run_imagery_study()
    
    def study_interaction(
        self
    ) -> Dict[str, Any]:
        """Study interaction."""
        return self._paradigm.run_interaction_study()
    
    def study_random_access(
        self
    ) -> Dict[str, Any]:
        """Study random access."""
        return self._paradigm.run_random_access_study()
    
    def get_pegword_list(
        self
    ) -> Dict[str, Any]:
        """Get pegword list."""
        return self._paradigm.run_pegword_list()
    
    def compare_strategies(
        self
    ) -> Dict[str, Any]:
        """Compare strategies."""
        return self._paradigm.run_comparison_study()
    
    # Analysis
    
    def get_metrics(self) -> PegwordMetrics:
        """Get metrics."""
        if not self._experiment_results:
            self.run_basic()
        
        last = self._experiment_results[-1]
        
        return PegwordMetrics(
            recall_rate=last.get('recall_rate', 0),
            position_accuracy=last.get('position_accuracy', 0),
            average_latency=last.get('average_rt_ms', 0),
            advantage_over_rote=last.get('pegword_advantage', 0)
        )
    
    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'pegwords': len(self._system._pegwords),
            'paired_items': len(self._system._paired_items),
            'trials': len(self._system._trials)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_pegword_engine() -> PegwordEngine:
    """Create pegword engine."""
    return PegwordEngine()


def demonstrate_pegword_system() -> Dict[str, Any]:
    """Demonstrate pegword system."""
    engine = create_pegword_engine()
    
    # Basic
    basic = engine.run_basic()
    
    # Pegword list
    pegs = engine.get_pegword_list()
    
    # Imagery
    imagery = engine.study_imagery()
    
    # Random access
    random_access = engine.study_random_access()
    
    return {
        'basic': {
            'recall': f"{basic.get('recall_rate', 0):.0%}",
            'position': f"{basic.get('position_accuracy', 0):.0%}",
            'advantage': f"{basic.get('pegword_advantage', 0):.0%}"
        },
        'pegwords': {k: v for k, v in list(pegs['pegwords'].items())[:5]},
        'random_access': f"{random_access['recall_rate']:.0%}",
        'interpretation': (
            f"Recall: {basic.get('recall_rate', 0):.0%}. "
            f"Advantage: {basic.get('pegword_advantage', 0):.0%}. "
            f"Rhyme pegs enable direct position access."
        )
    }


def get_pegword_facts() -> Dict[str, str]:
    """Get facts about pegword system."""
    return {
        'origin': 'Popularized 17th century',
        'pattern': 'Number rhymes with peg',
        'standard': 'One-bun, two-shoe, three-tree...',
        'capacity': 'Limited to ~20 positions',
        'random_access': 'Direct access to any position',
        'effectiveness': '20-30% advantage over rote',
        'vs_loci': 'Faster to learn, less capacity',
        'limitation': 'Interference with reuse'
    }

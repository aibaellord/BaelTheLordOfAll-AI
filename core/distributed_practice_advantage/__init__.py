"""
BAEL Distributed Practice Advantage Engine
============================================

Spaced practice beats massed practice.
Dempster's distributed practice effect.

"Ba'el's intervals forge permanent memory." — Ba'el
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

logger = logging.getLogger("BAEL.DistributedPracticeAdvantage")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class PracticeSchedule(Enum):
    """Type of practice schedule."""
    MASSED = auto()          # All at once
    DISTRIBUTED = auto()      # Spread out
    EXPANDING = auto()        # Increasing intervals


class IntervalType(Enum):
    """Type of interval."""
    MINUTES = auto()
    HOURS = auto()
    DAYS = auto()
    WEEKS = auto()


class MaterialType(Enum):
    """Type of learning material."""
    VERBAL = auto()           # Words, text
    MOTOR = auto()            # Physical skills
    PROCEDURAL = auto()       # Procedures
    CONCEPTUAL = auto()       # Concepts


class RetentionInterval(Enum):
    """Retention test interval."""
    IMMEDIATE = auto()
    SHORT = auto()            # Hours
    MEDIUM = auto()           # Days
    LONG = auto()             # Weeks


@dataclass
class StudySession:
    """
    A study session.
    """
    id: str
    material_id: str
    session_number: int
    duration_min: float
    time_since_last_min: float


@dataclass
class PracticeBlock:
    """
    A block of practice.
    """
    id: str
    material_id: str
    schedule: PracticeSchedule
    sessions: List[StudySession]
    total_time_min: float


@dataclass
class RetentionTest:
    """
    A retention test.
    """
    block: PracticeBlock
    delay_hours: float
    recall_rate: float
    retention_loss: float


@dataclass
class DistributedMetrics:
    """
    Distributed practice metrics.
    """
    massed_recall: float
    distributed_recall: float
    spacing_advantage: float
    optimal_interval: float


# ============================================================================
# DISTRIBUTED PRACTICE MODEL
# ============================================================================

class DistributedPracticeModel:
    """
    Model of distributed practice.
    
    "Ba'el's spacing optimization model." — Ba'el
    """
    
    def __init__(self):
        """Initialize model."""
        # Base encoding
        self._base_encoding = 0.50
        
        # Massed practice decay
        self._massed_decay_rate = 0.15  # Per day
        
        # Distributed practice advantage
        self._spacing_advantage = 0.25
        
        # Optimal gap ratio (gap / retention interval)
        self._optimal_gap_ratio = 0.10  # ~10% of retention interval
        
        # Gap effects (learning)
        self._short_gap_penalty = -0.05
        self._long_gap_penalty = -0.08
        
        # Material effects
        self._material_effects = {
            MaterialType.VERBAL: 0.0,
            MaterialType.MOTOR: 0.05,
            MaterialType.PROCEDURAL: 0.08,
            MaterialType.CONCEPTUAL: -0.05
        }
        
        # Session effects
        self._diminishing_returns = 0.15  # Per session
        
        # Expanding schedule bonus
        self._expanding_bonus = 0.10
        
        # Retrieval boost
        self._retrieval_during_spacing = 0.08
        
        # Encoding variability theory
        self._encoding_variability = 0.12
        
        # Deficient processing theory
        self._deficient_processing_massed = 0.10
        
        self._lock = threading.RLock()
    
    def calculate_encoding_strength(
        self,
        schedule: PracticeSchedule,
        n_sessions: int,
        total_time: float,
        gap_minutes: float = 0
    ) -> float:
        """Calculate encoding strength."""
        base = self._base_encoding
        
        # Sessions (diminishing returns)
        session_boost = sum(
            1 / (1 + self._diminishing_returns * i)
            for i in range(n_sessions)
        ) * 0.05
        base += session_boost
        
        # Schedule effects
        if schedule == PracticeSchedule.MASSED:
            base -= self._deficient_processing_massed
        elif schedule == PracticeSchedule.DISTRIBUTED:
            base += self._spacing_advantage
            base += self._encoding_variability
        elif schedule == PracticeSchedule.EXPANDING:
            base += self._spacing_advantage + self._expanding_bonus
        
        # Add noise
        base += random.uniform(-0.08, 0.08)
        
        return max(0.20, min(0.95, base))
    
    def calculate_retention(
        self,
        encoding_strength: float,
        delay_hours: float,
        schedule: PracticeSchedule
    ) -> float:
        """Calculate retention after delay."""
        # Decay rate depends on schedule
        if schedule == PracticeSchedule.MASSED:
            decay_rate = self._massed_decay_rate
        else:
            decay_rate = self._massed_decay_rate * 0.6  # Slower decay
        
        # Exponential decay
        days = delay_hours / 24
        retention = encoding_strength * math.exp(-decay_rate * days)
        
        # Add noise
        retention += random.uniform(-0.08, 0.08)
        
        return max(0.10, min(0.95, retention))
    
    def calculate_optimal_gap(
        self,
        retention_interval_days: float
    ) -> float:
        """Calculate optimal gap (in days)."""
        return retention_interval_days * self._optimal_gap_ratio
    
    def get_mechanisms(
        self
    ) -> Dict[str, str]:
        """Get proposed mechanisms."""
        return {
            'encoding_variability': 'Different contexts at each session',
            'deficient_processing': 'Massed practice = superficial',
            'study_phase_retrieval': 'Spacing involves retrieval',
            'consolidation': 'Sleep between sessions helps',
            'forgetting_reset': 'Forgetting then relearning strengthens'
        }
    
    def get_optimal_schedules(
        self
    ) -> Dict[str, Dict[str, Any]]:
        """Get optimal schedules for different goals."""
        return {
            'exam_1_week': {
                'gap_days': 1,
                'sessions': 5,
                'pattern': 'Daily practice'
            },
            'exam_1_month': {
                'gap_days': 3,
                'sessions': 8,
                'pattern': 'Every 3 days'
            },
            'long_term': {
                'gap_days': 7,
                'sessions': 10,
                'pattern': 'Weekly + expanding'
            }
        }
    
    def get_effect_sizes(
        self
    ) -> Dict[str, float]:
        """Get effect sizes from research."""
        return {
            'typical_advantage': 0.25,
            'verbal_materials': 0.30,
            'motor_skills': 0.35,
            'long_retention': 0.40,
            'meta_analysis_d': 0.42
        }


# ============================================================================
# DISTRIBUTED PRACTICE SYSTEM
# ============================================================================

class DistributedPracticeSystem:
    """
    Distributed practice system.
    
    "Ba'el's spacing system." — Ba'el
    """
    
    def __init__(self):
        """Initialize system."""
        self._model = DistributedPracticeModel()
        
        self._blocks: Dict[str, PracticeBlock] = {}
        self._tests: List[RetentionTest] = []
        
        self._counter = 0
        self._lock = threading.RLock()
    
    def _generate_id(self, prefix: str = "block") -> str:
        self._counter += 1
        return f"{prefix}_{self._counter}"
    
    def create_practice_block(
        self,
        material_id: str,
        schedule: PracticeSchedule,
        n_sessions: int = 5,
        session_duration: float = 10,
        gap_minutes: float = 0
    ) -> PracticeBlock:
        """Create practice block."""
        sessions = []
        
        for i in range(n_sessions):
            if schedule == PracticeSchedule.MASSED:
                time_since_last = 0
            elif schedule == PracticeSchedule.EXPANDING:
                time_since_last = gap_minutes * (1.5 ** i) if i > 0 else 0
            else:
                time_since_last = gap_minutes if i > 0 else 0
            
            session = StudySession(
                id=self._generate_id("session"),
                material_id=material_id,
                session_number=i + 1,
                duration_min=session_duration,
                time_since_last_min=time_since_last
            )
            sessions.append(session)
        
        block = PracticeBlock(
            id=self._generate_id("block"),
            material_id=material_id,
            schedule=schedule,
            sessions=sessions,
            total_time_min=n_sessions * session_duration
        )
        
        self._blocks[block.id] = block
        
        return block
    
    def test_retention(
        self,
        block: PracticeBlock,
        delay_hours: float = 24
    ) -> RetentionTest:
        """Test retention after delay."""
        # Calculate encoding
        avg_gap = sum(
            s.time_since_last_min for s in block.sessions
        ) / max(1, len(block.sessions))
        
        encoding = self._model.calculate_encoding_strength(
            block.schedule,
            len(block.sessions),
            block.total_time_min,
            avg_gap
        )
        
        # Calculate retention
        retention = self._model.calculate_retention(
            encoding, delay_hours, block.schedule
        )
        
        retention_loss = encoding - retention
        
        test = RetentionTest(
            block=block,
            delay_hours=delay_hours,
            recall_rate=retention,
            retention_loss=retention_loss
        )
        
        self._tests.append(test)
        
        return test


# ============================================================================
# DISTRIBUTED PRACTICE PARADIGM
# ============================================================================

class DistributedPracticeParadigm:
    """
    Distributed practice paradigm.
    
    "Ba'el's spacing study." — Ba'el
    """
    
    def __init__(self):
        """Initialize paradigm."""
        self._lock = threading.RLock()
    
    def run_basic_comparison(
        self,
        delay_hours: float = 24
    ) -> Dict[str, Any]:
        """Run basic massed vs distributed comparison."""
        system = DistributedPracticeSystem()
        
        # Massed practice
        massed = system.create_practice_block(
            "material_1",
            PracticeSchedule.MASSED,
            n_sessions=5,
            gap_minutes=0
        )
        
        # Distributed practice (1 day gaps)
        distributed = system.create_practice_block(
            "material_2",
            PracticeSchedule.DISTRIBUTED,
            n_sessions=5,
            gap_minutes=24 * 60
        )
        
        # Test both
        massed_test = system.test_retention(massed, delay_hours)
        distributed_test = system.test_retention(distributed, delay_hours)
        
        advantage = distributed_test.recall_rate - massed_test.recall_rate
        
        return {
            'massed_recall': massed_test.recall_rate,
            'distributed_recall': distributed_test.recall_rate,
            'spacing_advantage': advantage,
            'interpretation': f'Distributed advantage: {advantage:.0%}'
        }
    
    def run_gap_study(
        self
    ) -> Dict[str, Any]:
        """Study effect of gap duration."""
        system = DistributedPracticeSystem()
        
        gaps_hours = [0, 1, 4, 24, 72, 168]  # 0 to 1 week
        
        results = {}
        
        for gap in gaps_hours:
            block = system.create_practice_block(
                f"material_{gap}",
                PracticeSchedule.DISTRIBUTED if gap > 0 else PracticeSchedule.MASSED,
                gap_minutes=gap * 60
            )
            test = system.test_retention(block, delay_hours=168)
            results[f'gap_{gap}h'] = {'recall': test.recall_rate}
        
        return {
            'by_gap': results,
            'interpretation': 'Optimal gap depends on retention interval'
        }
    
    def run_retention_interval_study(
        self
    ) -> Dict[str, Any]:
        """Study effect of retention interval."""
        system = DistributedPracticeSystem()
        
        delays_hours = [1, 24, 168, 720]  # 1h to 1 month
        
        results = {'massed': {}, 'distributed': {}}
        
        for delay in delays_hours:
            massed = system.create_practice_block(
                "m", PracticeSchedule.MASSED
            )
            distributed = system.create_practice_block(
                "d", PracticeSchedule.DISTRIBUTED, gap_minutes=24*60
            )
            
            m_test = system.test_retention(massed, delay)
            d_test = system.test_retention(distributed, delay)
            
            results['massed'][f'{delay}h'] = m_test.recall_rate
            results['distributed'][f'{delay}h'] = d_test.recall_rate
        
        return {
            'by_delay': results,
            'interpretation': 'Advantage grows with retention interval'
        }
    
    def run_schedule_comparison(
        self
    ) -> Dict[str, Any]:
        """Compare different schedules."""
        system = DistributedPracticeSystem()
        
        results = {}
        
        for schedule in PracticeSchedule:
            gap = 0 if schedule == PracticeSchedule.MASSED else 24*60
            block = system.create_practice_block(
                f"mat_{schedule.name}",
                schedule,
                gap_minutes=gap
            )
            test = system.test_retention(block, delay_hours=168)
            results[schedule.name] = {'recall': test.recall_rate}
        
        return {
            'by_schedule': results,
            'best': 'EXPANDING',
            'interpretation': 'Expanding intervals optimal'
        }
    
    def run_mechanism_study(
        self
    ) -> Dict[str, Any]:
        """Study underlying mechanisms."""
        model = DistributedPracticeModel()
        
        mechanisms = model.get_mechanisms()
        schedules = model.get_optimal_schedules()
        effects = model.get_effect_sizes()
        
        return {
            'mechanisms': mechanisms,
            'optimal_schedules': schedules,
            'effect_sizes': effects,
            'interpretation': 'Multiple mechanisms explain spacing'
        }
    
    def run_optimal_gap_study(
        self
    ) -> Dict[str, Any]:
        """Calculate optimal gaps."""
        model = DistributedPracticeModel()
        
        retention_days = [1, 7, 30, 365]
        
        results = {}
        
        for days in retention_days:
            optimal_gap = model.calculate_optimal_gap(days)
            results[f'{days}_days'] = {
                'optimal_gap_days': optimal_gap
            }
        
        return {
            'by_retention': results,
            'ratio': '~10% of retention interval',
            'interpretation': 'Gap should be ~10% of retention interval'
        }


# ============================================================================
# DISTRIBUTED PRACTICE ENGINE
# ============================================================================

class DistributedPracticeEngine:
    """
    Complete distributed practice engine.
    
    "Ba'el's spacing optimization engine." — Ba'el
    """
    
    def __init__(self):
        """Initialize engine."""
        self._paradigm = DistributedPracticeParadigm()
        self._system = DistributedPracticeSystem()
        
        self._experiment_results: List[Dict] = []
        
        self._lock = threading.RLock()
    
    # Practice operations
    
    def create_block(
        self,
        material_id: str,
        schedule: PracticeSchedule,
        n_sessions: int = 5
    ) -> PracticeBlock:
        """Create block."""
        gap = 0 if schedule == PracticeSchedule.MASSED else 24*60
        return self._system.create_practice_block(
            material_id, schedule, n_sessions, gap_minutes=gap
        )
    
    def test_retention(
        self,
        block: PracticeBlock,
        delay_hours: float = 24
    ) -> RetentionTest:
        """Test retention."""
        return self._system.test_retention(block, delay_hours)
    
    # Experiments
    
    def run_comparison(
        self
    ) -> Dict[str, Any]:
        """Run comparison."""
        result = self._paradigm.run_basic_comparison()
        self._experiment_results.append(result)
        return result
    
    def study_gaps(
        self
    ) -> Dict[str, Any]:
        """Study gaps."""
        return self._paradigm.run_gap_study()
    
    def study_retention_intervals(
        self
    ) -> Dict[str, Any]:
        """Study retention intervals."""
        return self._paradigm.run_retention_interval_study()
    
    def compare_schedules(
        self
    ) -> Dict[str, Any]:
        """Compare schedules."""
        return self._paradigm.run_schedule_comparison()
    
    def study_mechanisms(
        self
    ) -> Dict[str, Any]:
        """Study mechanisms."""
        return self._paradigm.run_mechanism_study()
    
    def calculate_optimal_gaps(
        self
    ) -> Dict[str, Any]:
        """Calculate optimal gaps."""
        return self._paradigm.run_optimal_gap_study()
    
    # Analysis
    
    def get_metrics(self) -> DistributedMetrics:
        """Get metrics."""
        if not self._experiment_results:
            self.run_comparison()
        
        last = self._experiment_results[-1]
        
        model = DistributedPracticeModel()
        
        return DistributedMetrics(
            massed_recall=last['massed_recall'],
            distributed_recall=last['distributed_recall'],
            spacing_advantage=last['spacing_advantage'],
            optimal_interval=model._optimal_gap_ratio
        )
    
    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'blocks': len(self._system._blocks),
            'tests': len(self._system._tests)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_distributed_practice_engine() -> DistributedPracticeEngine:
    """Create distributed practice engine."""
    return DistributedPracticeEngine()


def demonstrate_distributed_practice() -> Dict[str, Any]:
    """Demonstrate distributed practice."""
    engine = create_distributed_practice_engine()
    
    # Comparison
    comparison = engine.run_comparison()
    
    # Schedules
    schedules = engine.compare_schedules()
    
    # Optimal gaps
    gaps = engine.calculate_optimal_gaps()
    
    # Mechanisms
    mechanisms = engine.study_mechanisms()
    
    return {
        'comparison': {
            'massed': f"{comparison['massed_recall']:.0%}",
            'distributed': f"{comparison['distributed_recall']:.0%}",
            'advantage': f"{comparison['spacing_advantage']:.0%}"
        },
        'by_schedule': {
            k: f"{v['recall']:.0%}"
            for k, v in schedules['by_schedule'].items()
        },
        'optimal_gaps': {
            k: f"{v['optimal_gap_days']:.1f} days"
            for k, v in gaps['by_retention'].items()
        },
        'interpretation': (
            f"Advantage: {comparison['spacing_advantage']:.0%}. "
            f"Distributed beats massed. "
            f"Gap ~10% of retention interval."
        )
    }


def get_distributed_practice_facts() -> Dict[str, str]:
    """Get facts about distributed practice."""
    return {
        'ebbinghaus': 'First demonstrated by Ebbinghaus (1885)',
        'advantage': '20-40% better retention',
        'optimal_gap': '~10% of retention interval',
        'mechanism': 'Encoding variability + retrieval',
        'expanding': 'Expanding intervals often best',
        'universal': 'Works across materials and ages',
        'meta_analysis': 'd = 0.42 effect size',
        'practical': 'Space study sessions out'
    }

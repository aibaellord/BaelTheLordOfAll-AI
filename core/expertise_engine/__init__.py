"""
BAEL Expertise Engine
======================

Expert performance and deliberate practice.
Chunking and pattern recognition.

"Ba'el masters through practice." — Ba'el
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

logger = logging.getLogger("BAEL.Expertise")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class ExpertiseLevel(Enum):
    """Levels of expertise."""
    NOVICE = 1             # Beginner
    ADVANCED_BEGINNER = 2  # Some experience
    COMPETENT = 3          # 2-3 years
    PROFICIENT = 4         # 3-5 years
    EXPERT = 5             # 10+ years
    MASTER = 6             # Elite


class SkillStage(Enum):
    """Skill acquisition stages (Fitts)."""
    COGNITIVE = auto()     # Understanding
    ASSOCIATIVE = auto()   # Practice
    AUTONOMOUS = auto()    # Automatic


class PracticeType(Enum):
    """Types of practice."""
    NAIVE = auto()         # Unstructured
    PURPOSEFUL = auto()    # Goal-directed
    DELIBERATE = auto()    # Expert-designed


class ChunkType(Enum):
    """Types of chunks."""
    PERCEPTUAL = auto()    # Pattern recognition
    MOTOR = auto()         # Action sequences
    CONCEPTUAL = auto()    # Abstract patterns


@dataclass
class Chunk:
    """
    A chunk of knowledge/skill.
    """
    id: str
    pattern: Any
    chunk_type: ChunkType
    elements: List[Any]
    strength: float = 0.5
    access_count: int = 0


@dataclass
class Skill:
    """
    A skill being developed.
    """
    id: str
    name: str
    domain: str
    level: ExpertiseLevel
    stage: SkillStage
    chunks: List[Chunk]
    practice_hours: float = 0.0
    quality_hours: float = 0.0  # Deliberate practice hours


@dataclass
class PracticeSession:
    """
    A practice session.
    """
    id: str
    skill_id: str
    practice_type: PracticeType
    duration_hours: float
    focus_area: str
    feedback_received: bool
    improvement: float


@dataclass
class PerformanceMetrics:
    """
    Performance metrics.
    """
    accuracy: float
    speed: float
    consistency: float
    adaptability: float
    pattern_recognition: float


@dataclass
class ExpertiseMetrics:
    """
    Expertise development metrics.
    """
    total_practice_hours: float
    deliberate_practice_hours: float
    chunk_count: int
    expertise_level: ExpertiseLevel
    progression_rate: float


# ============================================================================
# CHUNK MANAGER
# ============================================================================

class ChunkManager:
    """
    Manage knowledge chunks.

    "Ba'el chunks knowledge." — Ba'el
    """

    def __init__(self):
        """Initialize manager."""
        self._chunks: Dict[str, Chunk] = {}
        self._chunk_counter = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._chunk_counter += 1
        return f"chunk_{self._chunk_counter}"

    def create_chunk(
        self,
        pattern: Any,
        chunk_type: ChunkType,
        elements: List[Any]
    ) -> Chunk:
        """Create a new chunk."""
        chunk = Chunk(
            id=self._generate_id(),
            pattern=pattern,
            chunk_type=chunk_type,
            elements=elements
        )

        self._chunks[chunk.id] = chunk
        return chunk

    def consolidate_chunks(
        self,
        chunk1: Chunk,
        chunk2: Chunk
    ) -> Chunk:
        """Combine two chunks into a larger one."""
        combined_elements = chunk1.elements + chunk2.elements
        combined_pattern = f"{chunk1.pattern}_{chunk2.pattern}"

        new_chunk = Chunk(
            id=self._generate_id(),
            pattern=combined_pattern,
            chunk_type=chunk1.chunk_type,
            elements=combined_elements,
            strength=(chunk1.strength + chunk2.strength) / 2
        )

        self._chunks[new_chunk.id] = new_chunk
        return new_chunk

    def recognize_pattern(
        self,
        stimulus: Any,
        expertise_level: ExpertiseLevel
    ) -> List[Chunk]:
        """Recognize patterns based on expertise."""
        recognized = []

        for chunk in self._chunks.values():
            # Recognition probability based on chunk strength and expertise
            recognition_threshold = 0.8 - (expertise_level.value * 0.1)

            if chunk.strength > recognition_threshold:
                recognized.append(chunk)
                chunk.access_count += 1

        return recognized

    def strengthen_chunk(
        self,
        chunk_id: str,
        amount: float = 0.05
    ) -> None:
        """Strengthen a chunk through practice."""
        if chunk_id in self._chunks:
            chunk = self._chunks[chunk_id]
            chunk.strength = min(1.0, chunk.strength + amount)

    def get_chunk_count(self) -> int:
        """Get number of chunks."""
        return len(self._chunks)


# ============================================================================
# PRACTICE SIMULATOR
# ============================================================================

class PracticeSimulator:
    """
    Simulate practice and skill development.

    "Ba'el practices deliberately." — Ba'el
    """

    def __init__(self):
        """Initialize simulator."""
        self._session_counter = 0
        self._lock = threading.RLock()

    def _generate_session_id(self) -> str:
        self._session_counter += 1
        return f"session_{self._session_counter}"

    def simulate_practice(
        self,
        skill: Skill,
        practice_type: PracticeType,
        duration_hours: float,
        focus_area: str = "general",
        with_feedback: bool = True
    ) -> PracticeSession:
        """Simulate a practice session."""
        # Calculate improvement based on practice type
        if practice_type == PracticeType.NAIVE:
            base_improvement = 0.01
            quality_multiplier = 0.2
        elif practice_type == PracticeType.PURPOSEFUL:
            base_improvement = 0.03
            quality_multiplier = 0.5
        else:  # DELIBERATE
            base_improvement = 0.05
            quality_multiplier = 1.0

        # Feedback increases effectiveness
        if with_feedback:
            base_improvement *= 1.5

        # Diminishing returns at higher levels
        level_factor = 1.0 / skill.level.value

        # Duration effect (sweet spot around 1 hour)
        if duration_hours <= 1:
            duration_factor = duration_hours
        else:
            duration_factor = 1.0 + math.log(duration_hours)

        improvement = base_improvement * level_factor * duration_factor

        session = PracticeSession(
            id=self._generate_session_id(),
            skill_id=skill.id,
            practice_type=practice_type,
            duration_hours=duration_hours,
            focus_area=focus_area,
            feedback_received=with_feedback,
            improvement=improvement
        )

        # Update skill
        skill.practice_hours += duration_hours
        skill.quality_hours += duration_hours * quality_multiplier

        return session

    def calculate_expertise_level(
        self,
        practice_hours: float,
        quality_ratio: float
    ) -> ExpertiseLevel:
        """Calculate expertise level based on practice."""
        # Effective hours weighted by quality
        effective_hours = practice_hours * (0.5 + 0.5 * quality_ratio)

        # 10,000 hour rule (simplified)
        if effective_hours < 100:
            return ExpertiseLevel.NOVICE
        elif effective_hours < 500:
            return ExpertiseLevel.ADVANCED_BEGINNER
        elif effective_hours < 2000:
            return ExpertiseLevel.COMPETENT
        elif effective_hours < 5000:
            return ExpertiseLevel.PROFICIENT
        elif effective_hours < 10000:
            return ExpertiseLevel.EXPERT
        else:
            return ExpertiseLevel.MASTER

    def simulate_plateau(
        self,
        skill: Skill,
        sessions: int = 10
    ) -> bool:
        """Check if in plateau (no improvement)."""
        # Plateaus happen with naive practice
        if skill.stage == SkillStage.AUTONOMOUS:
            # Autonomous stage can plateau without deliberate practice
            recent_quality = skill.quality_hours / max(1, skill.practice_hours)
            return recent_quality < 0.3
        return False


# ============================================================================
# PERFORMANCE EVALUATOR
# ============================================================================

class PerformanceEvaluator:
    """
    Evaluate expert performance.

    "Ba'el measures mastery." — Ba'el
    """

    def __init__(self):
        """Initialize evaluator."""
        self._lock = threading.RLock()

    def evaluate(
        self,
        skill: Skill,
        chunk_manager: ChunkManager
    ) -> PerformanceMetrics:
        """Evaluate current performance level."""
        level_factor = skill.level.value / 6.0  # Normalize to 0-1

        # Accuracy improves with level
        accuracy = 0.4 + level_factor * 0.5 + random.uniform(-0.05, 0.05)

        # Speed improves with automaticity
        stage_factor = {
            SkillStage.COGNITIVE: 0.3,
            SkillStage.ASSOCIATIVE: 0.6,
            SkillStage.AUTONOMOUS: 0.9
        }
        speed = stage_factor.get(skill.stage, 0.5)

        # Consistency improves with practice
        practice_factor = min(1.0, skill.practice_hours / 1000)
        consistency = 0.3 + practice_factor * 0.6

        # Adaptability from chunk flexibility
        chunk_count = len(skill.chunks)
        adaptability = min(1.0, chunk_count * 0.1)

        # Pattern recognition from chunks
        avg_strength = (
            sum(c.strength for c in skill.chunks) / len(skill.chunks)
            if skill.chunks else 0.5
        )
        pattern_recognition = avg_strength

        return PerformanceMetrics(
            accuracy=min(1.0, max(0.0, accuracy)),
            speed=speed,
            consistency=consistency,
            adaptability=adaptability,
            pattern_recognition=pattern_recognition
        )

    def calculate_transfer(
        self,
        source_skill: Skill,
        target_domain: str
    ) -> float:
        """Calculate transfer of expertise to new domain."""
        # Near transfer (similar domain) vs far transfer
        if source_skill.domain == target_domain:
            return 0.8  # High transfer
        else:
            # Transfer based on chunk abstractness
            abstract_chunks = sum(
                1 for c in source_skill.chunks
                if c.chunk_type == ChunkType.CONCEPTUAL
            )
            return min(0.5, abstract_chunks * 0.05)


# ============================================================================
# EXPERTISE ENGINE
# ============================================================================

class ExpertiseEngine:
    """
    Complete expertise development engine.

    "Ba'el's path to mastery." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._chunk_manager = ChunkManager()
        self._practice_sim = PracticeSimulator()
        self._evaluator = PerformanceEvaluator()

        self._skills: Dict[str, Skill] = {}
        self._sessions: List[PracticeSession] = []

        self._skill_counter = 0

        self._lock = threading.RLock()

    def _generate_skill_id(self) -> str:
        self._skill_counter += 1
        return f"skill_{self._skill_counter}"

    # Skill management

    def create_skill(
        self,
        name: str,
        domain: str
    ) -> Skill:
        """Create a new skill to develop."""
        skill = Skill(
            id=self._generate_skill_id(),
            name=name,
            domain=domain,
            level=ExpertiseLevel.NOVICE,
            stage=SkillStage.COGNITIVE,
            chunks=[]
        )

        self._skills[skill.id] = skill
        return skill

    # Chunk development

    def learn_chunk(
        self,
        skill: Skill,
        pattern: Any,
        chunk_type: ChunkType,
        elements: List[Any]
    ) -> Chunk:
        """Learn a new chunk for a skill."""
        chunk = self._chunk_manager.create_chunk(pattern, chunk_type, elements)
        skill.chunks.append(chunk)
        return chunk

    def consolidate_knowledge(
        self,
        skill: Skill
    ) -> int:
        """Consolidate chunks into larger units."""
        if len(skill.chunks) < 2:
            return 0

        consolidations = 0

        # Try to combine adjacent chunks
        i = 0
        while i < len(skill.chunks) - 1:
            chunk1 = skill.chunks[i]
            chunk2 = skill.chunks[i + 1]

            # Combine if both are strong
            if chunk1.strength > 0.7 and chunk2.strength > 0.7:
                new_chunk = self._chunk_manager.consolidate_chunks(chunk1, chunk2)
                skill.chunks[i] = new_chunk
                skill.chunks.pop(i + 1)
                consolidations += 1
            else:
                i += 1

        return consolidations

    # Practice

    def practice(
        self,
        skill: Skill,
        practice_type: PracticeType,
        duration_hours: float,
        focus_area: str = "general",
        with_feedback: bool = True
    ) -> PracticeSession:
        """Practice a skill."""
        session = self._practice_sim.simulate_practice(
            skill, practice_type, duration_hours, focus_area, with_feedback
        )

        self._sessions.append(session)

        # Strengthen chunks
        for chunk in skill.chunks:
            strengthen_amount = session.improvement * 0.1
            self._chunk_manager.strengthen_chunk(chunk.id, strengthen_amount)

        # Update skill level
        quality_ratio = skill.quality_hours / max(1, skill.practice_hours)
        new_level = self._practice_sim.calculate_expertise_level(
            skill.practice_hours, quality_ratio
        )
        skill.level = new_level

        # Update stage
        if skill.practice_hours > 50 and skill.stage == SkillStage.COGNITIVE:
            skill.stage = SkillStage.ASSOCIATIVE
        elif skill.practice_hours > 500 and skill.stage == SkillStage.ASSOCIATIVE:
            skill.stage = SkillStage.AUTONOMOUS

        return session

    def deliberate_practice_session(
        self,
        skill: Skill,
        duration_hours: float = 1.0,
        weakness_focus: str = None
    ) -> PracticeSession:
        """Run a deliberate practice session."""
        focus = weakness_focus or "general"

        return self.practice(
            skill,
            PracticeType.DELIBERATE,
            duration_hours,
            focus,
            with_feedback=True
        )

    # Evaluation

    def evaluate_performance(
        self,
        skill: Skill
    ) -> PerformanceMetrics:
        """Evaluate skill performance."""
        return self._evaluator.evaluate(skill, self._chunk_manager)

    def check_plateau(
        self,
        skill: Skill
    ) -> bool:
        """Check if skill is plateaued."""
        return self._practice_sim.simulate_plateau(skill)

    # Transfer

    def transfer_expertise(
        self,
        source_skill: Skill,
        target_name: str,
        target_domain: str
    ) -> Skill:
        """Transfer expertise to new skill."""
        transfer = self._evaluator.calculate_transfer(source_skill, target_domain)

        new_skill = self.create_skill(target_name, target_domain)

        # Transfer some practice credit
        new_skill.practice_hours = source_skill.practice_hours * transfer * 0.1
        new_skill.quality_hours = source_skill.quality_hours * transfer * 0.1

        # Transfer some chunks (conceptual transfer best)
        for chunk in source_skill.chunks:
            if chunk.chunk_type == ChunkType.CONCEPTUAL and chunk.strength > 0.6:
                new_chunk = Chunk(
                    id=f"transferred_{chunk.id}",
                    pattern=chunk.pattern,
                    chunk_type=chunk.chunk_type,
                    elements=chunk.elements,
                    strength=chunk.strength * transfer
                )
                new_skill.chunks.append(new_chunk)

        return new_skill

    # Metrics

    def get_metrics(
        self,
        skill: Skill = None
    ) -> ExpertiseMetrics:
        """Get expertise metrics."""
        if skill:
            skills = [skill]
        else:
            skills = list(self._skills.values())

        if not skills:
            return ExpertiseMetrics(
                total_practice_hours=0.0,
                deliberate_practice_hours=0.0,
                chunk_count=0,
                expertise_level=ExpertiseLevel.NOVICE,
                progression_rate=0.0
            )

        total_hours = sum(s.practice_hours for s in skills)
        deliberate_hours = sum(s.quality_hours for s in skills)
        chunks = sum(len(s.chunks) for s in skills)
        avg_level = sum(s.level.value for s in skills) / len(skills)

        # Find closest expertise level
        level = ExpertiseLevel(min(6, max(1, round(avg_level))))

        # Calculate progression rate
        if total_hours > 0:
            progression = avg_level / (total_hours / 1000)
        else:
            progression = 0.0

        return ExpertiseMetrics(
            total_practice_hours=total_hours,
            deliberate_practice_hours=deliberate_hours,
            chunk_count=chunks,
            expertise_level=level,
            progression_rate=progression
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'skills': len(self._skills),
            'sessions': len(self._sessions),
            'total_chunks': self._chunk_manager.get_chunk_count()
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_expertise_engine() -> ExpertiseEngine:
    """Create expertise engine."""
    return ExpertiseEngine()


def demonstrate_expertise_development() -> Dict[str, Any]:
    """Demonstrate expertise development."""
    engine = create_expertise_engine()

    # Create skill
    chess = engine.create_skill("chess", "board_games")

    # Learn some initial chunks
    engine.learn_chunk(chess, "opening_italian", ChunkType.PERCEPTUAL, ["e4", "e5", "Nf3", "Nc6", "Bc4"])
    engine.learn_chunk(chess, "back_rank_mate", ChunkType.CONCEPTUAL, ["Rook", "King", "trapped"])

    # Practice over time
    for _ in range(50):
        engine.deliberate_practice_session(chess, duration_hours=1.0)

    # Evaluate
    performance = engine.evaluate_performance(chess)
    metrics = engine.get_metrics(chess)

    return {
        'expertise_level': metrics.expertise_level.name,
        'total_hours': metrics.total_practice_hours,
        'deliberate_hours': metrics.deliberate_practice_hours,
        'chunks': metrics.chunk_count,
        'accuracy': performance.accuracy,
        'pattern_recognition': performance.pattern_recognition
    }


def get_expertise_facts() -> Dict[str, str]:
    """Get facts about expertise."""
    return {
        'ericsson_1993': 'Deliberate practice theory introduced',
        '10000_hours': 'Popular but oversimplified rule',
        'deliberate': 'Practice must be effortful and focused',
        'feedback': 'Immediate feedback essential for improvement',
        'chunking': 'Experts recognize larger meaningful patterns',
        'fitts_stages': 'Cognitive → Associative → Autonomous',
        'plateau': 'Arrested development without deliberate practice',
        'transfer': 'Limited transfer to unrelated domains'
    }

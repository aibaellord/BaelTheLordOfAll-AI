"""
BAEL Procedural Memory Engine
==============================

Skill and motor learning.
Implicit procedural knowledge.

"Ba'el knows how to do." — Ba'el
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

logger = logging.getLogger("BAEL.ProceduralMemory")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class SkillLevel(Enum):
    """Skill acquisition levels."""
    NOVICE = auto()        # Cognitive stage
    ADVANCED_BEGINNER = auto()
    COMPETENT = auto()     # Associative stage
    PROFICIENT = auto()
    EXPERT = auto()        # Autonomous stage


class LearningStage(Enum):
    """Fitts & Posner learning stages."""
    COGNITIVE = auto()     # Explicit, slow
    ASSOCIATIVE = auto()   # Refining
    AUTONOMOUS = auto()    # Automatic, fast


class ProcedureType(Enum):
    """Types of procedures."""
    MOTOR = auto()         # Physical actions
    COGNITIVE = auto()     # Mental procedures
    PERCEPTUAL = auto()    # Pattern recognition
    MIXED = auto()         # Combined


@dataclass
class Step:
    """
    A single procedural step.
    """
    id: str
    name: str
    description: str
    duration: float = 1.0      # Base duration
    complexity: float = 0.5
    prerequisites: List[str] = field(default_factory=list)

    def execution_time(self, skill_level: float) -> float:
        """Get execution time based on skill."""
        # Power law of practice
        return self.duration * (1.0 + 2.0 * (1.0 - skill_level))


@dataclass
class Procedure:
    """
    A complete procedure (skill).
    """
    id: str
    name: str
    procedure_type: ProcedureType
    steps: List[Step]
    practice_count: int = 0
    skill_level: float = 0.0
    learning_stage: LearningStage = LearningStage.COGNITIVE
    last_practice: float = field(default_factory=time.time)
    errors: int = 0
    successes: int = 0

    @property
    def age(self) -> float:
        return time.time() - self.last_practice

    @property
    def total_duration(self) -> float:
        return sum(s.execution_time(self.skill_level) for s in self.steps)

    @property
    def accuracy(self) -> float:
        total = self.errors + self.successes
        if total == 0:
            return 0.0
        return self.successes / total


@dataclass
class Chunk:
    """
    A chunked sub-procedure.
    """
    id: str
    name: str
    steps: List[str]  # Step IDs
    activation: float = 0.0
    retrievals: int = 0


@dataclass
class ExecutionResult:
    """
    Result of procedure execution.
    """
    procedure_id: str
    success: bool
    execution_time: float
    errors: List[str]
    skill_gain: float


@dataclass
class PracticeSession:
    """
    A practice session.
    """
    id: str
    procedure_id: str
    start_time: float
    end_time: float = 0.0
    trials: int = 0
    errors: int = 0
    skill_before: float = 0.0
    skill_after: float = 0.0


# ============================================================================
# SKILL LEARNER
# ============================================================================

class SkillLearner:
    """
    Learn skills through practice.

    "Ba'el learns through practice." — Ba'el
    """

    def __init__(
        self,
        learning_rate: float = 0.1,
        decay_rate: float = 0.01
    ):
        """Initialize learner."""
        self._learning_rate = learning_rate
        self._decay_rate = decay_rate
        self._lock = threading.RLock()

    def practice(
        self,
        procedure: Procedure,
        trials: int = 1
    ) -> float:
        """Practice procedure."""
        with self._lock:
            skill_gain = 0.0

            for _ in range(trials):
                procedure.practice_count += 1

                # Power law of practice
                # Skill improves but with diminishing returns
                improvement = self._learning_rate / math.sqrt(procedure.practice_count)
                procedure.skill_level = min(1.0, procedure.skill_level + improvement)
                skill_gain += improvement

                # Update learning stage
                self._update_stage(procedure)

                procedure.last_practice = time.time()

            return skill_gain

    def _update_stage(self, procedure: Procedure) -> None:
        """Update learning stage."""
        if procedure.skill_level < 0.3:
            procedure.learning_stage = LearningStage.COGNITIVE
        elif procedure.skill_level < 0.7:
            procedure.learning_stage = LearningStage.ASSOCIATIVE
        else:
            procedure.learning_stage = LearningStage.AUTONOMOUS

    def decay(self, procedure: Procedure) -> float:
        """Apply decay to skill."""
        with self._lock:
            age_days = procedure.age / (24 * 3600)

            # Decay based on age and skill level
            # Higher skills decay slower
            decay_factor = self._decay_rate * age_days * (1.0 - procedure.skill_level * 0.5)

            procedure.skill_level = max(0.0, procedure.skill_level - decay_factor)

            return decay_factor

    def record_error(self, procedure: Procedure) -> None:
        """Record an error."""
        procedure.errors += 1

    def record_success(self, procedure: Procedure) -> None:
        """Record a success."""
        procedure.successes += 1


# ============================================================================
# CHUNKING
# ============================================================================

class ProceduralChunking:
    """
    Chunk procedures for faster execution.

    "Ba'el chunks procedures." — Ba'el
    """

    def __init__(self):
        """Initialize chunking."""
        self._chunks: Dict[str, Chunk] = {}
        self._step_to_chunk: Dict[str, str] = {}
        self._chunk_counter = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._chunk_counter += 1
        return f"chunk_{self._chunk_counter}"

    def create_chunk(
        self,
        name: str,
        steps: List[Step]
    ) -> Chunk:
        """Create chunk from steps."""
        with self._lock:
            chunk = Chunk(
                id=self._generate_id(),
                name=name,
                steps=[s.id for s in steps]
            )

            self._chunks[chunk.id] = chunk

            for step in steps:
                self._step_to_chunk[step.id] = chunk.id

            return chunk

    def auto_chunk(
        self,
        procedure: Procedure,
        chunk_size: int = 3
    ) -> List[Chunk]:
        """Automatically chunk procedure."""
        with self._lock:
            chunks = []

            for i in range(0, len(procedure.steps), chunk_size):
                chunk_steps = procedure.steps[i:i + chunk_size]
                chunk = self.create_chunk(
                    f"{procedure.name}_chunk_{len(chunks)}",
                    chunk_steps
                )
                chunks.append(chunk)

            return chunks

    def get_chunk(self, step_id: str) -> Optional[Chunk]:
        """Get chunk containing step."""
        chunk_id = self._step_to_chunk.get(step_id)
        if chunk_id:
            return self._chunks.get(chunk_id)
        return None

    def retrieve(self, chunk_id: str) -> Optional[Chunk]:
        """Retrieve chunk (increases activation)."""
        with self._lock:
            chunk = self._chunks.get(chunk_id)
            if chunk:
                chunk.retrievals += 1
                chunk.activation = min(1.0, chunk.activation + 0.1)
            return chunk

    @property
    def chunks(self) -> List[Chunk]:
        return list(self._chunks.values())


# ============================================================================
# PROCEDURE EXECUTOR
# ============================================================================

class ProcedureExecutor:
    """
    Execute procedures.

    "Ba'el executes procedures." — Ba'el
    """

    def __init__(
        self,
        learner: SkillLearner,
        chunking: ProceduralChunking
    ):
        """Initialize executor."""
        self._learner = learner
        self._chunking = chunking
        self._lock = threading.RLock()

    def execute(
        self,
        procedure: Procedure,
        context: Dict[str, Any] = None
    ) -> ExecutionResult:
        """Execute procedure."""
        with self._lock:
            start_time = time.time()
            errors = []

            # Execute each step
            for step in procedure.steps:
                # Check prerequisites
                for prereq in step.prerequisites:
                    if context and prereq not in context:
                        errors.append(f"Missing prerequisite: {prereq}")

                # Simulate execution (with possible errors)
                error_prob = step.complexity * (1.0 - procedure.skill_level)
                if random.random() < error_prob:
                    errors.append(f"Error in step: {step.name}")
                    self._learner.record_error(procedure)
                else:
                    self._learner.record_success(procedure)

                # Simulate time (faster with higher skill)
                exec_time = step.execution_time(procedure.skill_level)
                time.sleep(min(0.01, exec_time * 0.01))  # Simulated delay

            execution_time = time.time() - start_time
            success = len(errors) == 0

            # Practice improves skill
            skill_gain = self._learner.practice(procedure)

            return ExecutionResult(
                procedure_id=procedure.id,
                success=success,
                execution_time=execution_time,
                errors=errors,
                skill_gain=skill_gain
            )

    def execute_chunk(
        self,
        chunk: Chunk,
        procedure: Procedure
    ) -> Tuple[bool, float]:
        """Execute a chunk."""
        with self._lock:
            self._chunking.retrieve(chunk.id)

            # Chunked execution is faster
            chunk_skill = min(1.0, procedure.skill_level + chunk.activation * 0.2)

            # Get steps in chunk
            steps = [s for s in procedure.steps if s.id in chunk.steps]

            total_time = sum(s.execution_time(chunk_skill) for s in steps)

            # Chance of error
            error_prob = 0.1 * (1.0 - chunk_skill)
            success = random.random() >= error_prob

            return success, total_time


# ============================================================================
# PROCEDURAL MEMORY ENGINE
# ============================================================================

class ProceduralMemoryEngine:
    """
    Complete procedural memory engine.

    "Ba'el's skill memory." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._procedures: Dict[str, Procedure] = {}
        self._learner = SkillLearner()
        self._chunking = ProceduralChunking()
        self._executor = ProcedureExecutor(self._learner, self._chunking)
        self._sessions: List[PracticeSession] = []

        self._proc_counter = 0
        self._step_counter = 0
        self._session_counter = 0
        self._lock = threading.RLock()

    def _generate_proc_id(self) -> str:
        self._proc_counter += 1
        return f"proc_{self._proc_counter}"

    def _generate_step_id(self) -> str:
        self._step_counter += 1
        return f"step_{self._step_counter}"

    def _generate_session_id(self) -> str:
        self._session_counter += 1
        return f"session_{self._session_counter}"

    # Procedure management

    def create_procedure(
        self,
        name: str,
        procedure_type: ProcedureType = ProcedureType.COGNITIVE,
        steps: List[Dict[str, Any]] = None
    ) -> Procedure:
        """Create procedure."""
        with self._lock:
            step_objects = []

            if steps:
                for step_data in steps:
                    step = Step(
                        id=self._generate_step_id(),
                        name=step_data.get('name', ''),
                        description=step_data.get('description', ''),
                        duration=step_data.get('duration', 1.0),
                        complexity=step_data.get('complexity', 0.5)
                    )
                    step_objects.append(step)

            procedure = Procedure(
                id=self._generate_proc_id(),
                name=name,
                procedure_type=procedure_type,
                steps=step_objects
            )

            self._procedures[procedure.id] = procedure

            return procedure

    def add_step(
        self,
        procedure_name: str,
        step_name: str,
        description: str = "",
        duration: float = 1.0,
        complexity: float = 0.5
    ) -> Optional[Step]:
        """Add step to procedure."""
        with self._lock:
            procedure = self.get_procedure(procedure_name)
            if not procedure:
                return None

            step = Step(
                id=self._generate_step_id(),
                name=step_name,
                description=description,
                duration=duration,
                complexity=complexity
            )

            procedure.steps.append(step)
            return step

    def get_procedure(self, name: str) -> Optional[Procedure]:
        """Get procedure by name."""
        for proc in self._procedures.values():
            if proc.name.lower() == name.lower():
                return proc
        return None

    # Execution

    def execute(
        self,
        procedure_name: str,
        context: Dict[str, Any] = None
    ) -> Optional[ExecutionResult]:
        """Execute procedure."""
        procedure = self.get_procedure(procedure_name)
        if not procedure:
            return None

        return self._executor.execute(procedure, context)

    # Practice

    def practice(
        self,
        procedure_name: str,
        trials: int = 1
    ) -> Optional[float]:
        """Practice procedure."""
        procedure = self.get_procedure(procedure_name)
        if not procedure:
            return None

        return self._learner.practice(procedure, trials)

    def start_practice_session(
        self,
        procedure_name: str
    ) -> Optional[PracticeSession]:
        """Start practice session."""
        procedure = self.get_procedure(procedure_name)
        if not procedure:
            return None

        session = PracticeSession(
            id=self._generate_session_id(),
            procedure_id=procedure.id,
            start_time=time.time(),
            skill_before=procedure.skill_level
        )

        self._sessions.append(session)
        return session

    def end_practice_session(
        self,
        session_id: str,
        trials: int,
        errors: int
    ) -> Optional[PracticeSession]:
        """End practice session."""
        for session in self._sessions:
            if session.id == session_id:
                session.end_time = time.time()
                session.trials = trials
                session.errors = errors

                procedure = self._procedures.get(session.procedure_id)
                if procedure:
                    session.skill_after = procedure.skill_level

                return session
        return None

    # Chunking

    def chunk_procedure(
        self,
        procedure_name: str,
        chunk_size: int = 3
    ) -> List[Chunk]:
        """Chunk procedure."""
        procedure = self.get_procedure(procedure_name)
        if not procedure:
            return []

        return self._chunking.auto_chunk(procedure, chunk_size)

    # Analysis

    def get_skill_level(self, procedure_name: str) -> Optional[SkillLevel]:
        """Get skill level for procedure."""
        procedure = self.get_procedure(procedure_name)
        if not procedure:
            return None

        skill = procedure.skill_level

        if skill < 0.2:
            return SkillLevel.NOVICE
        elif skill < 0.4:
            return SkillLevel.ADVANCED_BEGINNER
        elif skill < 0.6:
            return SkillLevel.COMPETENT
        elif skill < 0.8:
            return SkillLevel.PROFICIENT
        else:
            return SkillLevel.EXPERT

    def decay_all(self) -> None:
        """Apply decay to all procedures."""
        for procedure in self._procedures.values():
            self._learner.decay(procedure)

    @property
    def procedures(self) -> List[Procedure]:
        return list(self._procedures.values())

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'procedures': len(self._procedures),
            'chunks': len(self._chunking.chunks),
            'sessions': len(self._sessions),
            'skills': {
                p.name: p.skill_level
                for p in self._procedures.values()
            }
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_procedural_memory() -> ProceduralMemoryEngine:
    """Create procedural memory engine."""
    return ProceduralMemoryEngine()


def create_procedure(
    name: str,
    steps: List[str]
) -> Procedure:
    """Quick procedure creation."""
    engine = create_procedural_memory()
    step_dicts = [{'name': s, 'description': s} for s in steps]
    return engine.create_procedure(name, steps=step_dicts)

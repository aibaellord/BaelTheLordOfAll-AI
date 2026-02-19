"""
BAEL Multiple Trace Theory Engine
==================================

Memory consolidation through trace formation.
Cortical-hippocampal memory systems.

"Ba'el forms memory traces." — Ba'el
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

logger = logging.getLogger("BAEL.MultipleTrace")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class MemoryType(Enum):
    """Types of memory."""
    EPISODIC = auto()      # Events
    SEMANTIC = auto()      # Facts
    MIXED = auto()         # Both


class TraceStatus(Enum):
    """Status of memory trace."""
    FORMING = auto()
    CONSOLIDATING = auto()
    STABLE = auto()
    DEGRADING = auto()


class ConsolidationType(Enum):
    """Type of consolidation."""
    SYNAPTIC = auto()      # Hours
    SYSTEMS = auto()       # Weeks to years


class RetrievalMode(Enum):
    """Mode of retrieval."""
    RECOLLECTION = auto()  # Context-rich
    FAMILIARITY = auto()   # Context-free


@dataclass
class MemoryTrace:
    """
    A memory trace.
    """
    id: str
    content: Any
    memory_type: MemoryType
    context: Dict[str, Any]
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    access_count: int = 0
    strength: float = 1.0
    status: TraceStatus = TraceStatus.FORMING
    hippocampal: float = 1.0    # Hippocampal binding
    cortical: float = 0.0       # Cortical representation

    @property
    def age(self) -> float:
        return time.time() - self.created_at

    @property
    def recency(self) -> float:
        return time.time() - self.last_accessed

    def access(self) -> None:
        self.last_accessed = time.time()
        self.access_count += 1
        self.strength = min(1.0, self.strength + 0.1)


@dataclass
class TraceBundle:
    """
    Bundle of related traces.
    """
    id: str
    traces: List[str]  # Trace IDs
    prototype: Dict[str, Any]
    coherence: float = 0.0


@dataclass
class RetrievalResult:
    """
    Result of retrieval.
    """
    trace: MemoryTrace
    match_score: float
    mode: RetrievalMode
    retrieval_time: float
    reactivated: bool


@dataclass
class ConsolidationResult:
    """
    Result of consolidation.
    """
    trace_id: str
    hippocampal_before: float
    hippocampal_after: float
    cortical_before: float
    cortical_after: float
    status_before: TraceStatus
    status_after: TraceStatus


# ============================================================================
# TRACE FORMATION
# ============================================================================

class TraceFormation:
    """
    Form memory traces.

    "Ba'el forms traces." — Ba'el
    """

    def __init__(self):
        """Initialize formation."""
        self._trace_counter = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._trace_counter += 1
        return f"trace_{self._trace_counter}"

    def encode(
        self,
        content: Any,
        context: Dict[str, Any],
        memory_type: MemoryType = MemoryType.EPISODIC,
        encoding_strength: float = 1.0
    ) -> MemoryTrace:
        """Encode new memory trace."""
        with self._lock:
            trace = MemoryTrace(
                id=self._generate_id(),
                content=content,
                memory_type=memory_type,
                context=context,
                strength=encoding_strength,
                hippocampal=1.0,  # Initially hippocampal
                cortical=0.1     # Weak cortical
            )

            return trace

    def reactivate(
        self,
        trace: MemoryTrace
    ) -> MemoryTrace:
        """Reactivate trace (creates new trace)."""
        with self._lock:
            # Each reactivation creates additional trace
            new_trace = MemoryTrace(
                id=self._generate_id(),
                content=trace.content,
                memory_type=trace.memory_type,
                context=trace.context.copy(),
                strength=trace.strength * 0.9,  # Slightly weaker
                hippocampal=1.0,
                cortical=trace.cortical + 0.1  # Build cortical
            )

            return new_trace


# ============================================================================
# CONSOLIDATION
# ============================================================================

class Consolidator:
    """
    Consolidate memory traces.

    "Ba'el consolidates memories." — Ba'el
    """

    def __init__(
        self,
        synaptic_rate: float = 0.1,
        systems_rate: float = 0.01
    ):
        """Initialize consolidator."""
        self._synaptic_rate = synaptic_rate
        self._systems_rate = systems_rate
        self._lock = threading.RLock()

    def consolidate(
        self,
        trace: MemoryTrace,
        consolidation_type: ConsolidationType = ConsolidationType.SYSTEMS
    ) -> ConsolidationResult:
        """Consolidate memory trace."""
        with self._lock:
            hipp_before = trace.hippocampal
            cort_before = trace.cortical
            status_before = trace.status

            if consolidation_type == ConsolidationType.SYNAPTIC:
                # Strengthen existing connections
                trace.strength = min(1.0, trace.strength + self._synaptic_rate)

                if trace.status == TraceStatus.FORMING:
                    trace.status = TraceStatus.CONSOLIDATING

            elif consolidation_type == ConsolidationType.SYSTEMS:
                # Transfer from hippocampus to cortex
                transfer = min(trace.hippocampal * self._systems_rate, 0.1)

                trace.hippocampal = max(0.0, trace.hippocampal - transfer * 0.5)
                trace.cortical = min(1.0, trace.cortical + transfer)

                # Update status
                if trace.cortical > 0.7:
                    trace.status = TraceStatus.STABLE
                elif trace.status == TraceStatus.FORMING:
                    trace.status = TraceStatus.CONSOLIDATING

            return ConsolidationResult(
                trace_id=trace.id,
                hippocampal_before=hipp_before,
                hippocampal_after=trace.hippocampal,
                cortical_before=cort_before,
                cortical_after=trace.cortical,
                status_before=status_before,
                status_after=trace.status
            )

    def sleep_consolidation(
        self,
        traces: List[MemoryTrace],
        cycles: int = 5
    ) -> List[ConsolidationResult]:
        """Simulate sleep consolidation."""
        results = []

        for _ in range(cycles):
            for trace in traces:
                # Replay during sleep
                result = self.consolidate(trace, ConsolidationType.SYSTEMS)
                results.append(result)

        return results


# ============================================================================
# RETRIEVAL
# ============================================================================

class TraceRetrieval:
    """
    Retrieve memory traces.

    "Ba'el retrieves memories." — Ba'el
    """

    def __init__(
        self,
        recollection_threshold: float = 0.5,
        familiarity_threshold: float = 0.3
    ):
        """Initialize retrieval."""
        self._recollection_threshold = recollection_threshold
        self._familiarity_threshold = familiarity_threshold
        self._lock = threading.RLock()

    def retrieve(
        self,
        cue: Dict[str, Any],
        traces: List[MemoryTrace]
    ) -> List[RetrievalResult]:
        """Retrieve traces matching cue."""
        with self._lock:
            start_time = time.time()
            results = []

            for trace in traces:
                # Compute match
                match_score = self._compute_match(cue, trace)

                if match_score > 0:
                    # Determine retrieval mode
                    mode = self._determine_mode(trace, match_score)

                    # Access trace
                    trace.access()

                    results.append(RetrievalResult(
                        trace=trace,
                        match_score=match_score,
                        mode=mode,
                        retrieval_time=time.time() - start_time,
                        reactivated=True
                    ))

            # Sort by match score
            results.sort(key=lambda r: r.match_score, reverse=True)

            return results

    def _compute_match(
        self,
        cue: Dict[str, Any],
        trace: MemoryTrace
    ) -> float:
        """Compute match between cue and trace."""
        match = 0.0
        count = 0

        # Context match
        for key, value in cue.items():
            if key in trace.context:
                if trace.context[key] == value:
                    match += 1.0
                count += 1

        # Content match
        if 'content' in cue and cue['content'] == trace.content:
            match += 1.0
            count += 1

        if count == 0:
            return 0.0

        # Weight by trace strength
        base_match = match / count
        weighted = base_match * trace.strength

        return weighted

    def _determine_mode(
        self,
        trace: MemoryTrace,
        match_score: float
    ) -> RetrievalMode:
        """Determine retrieval mode."""
        # Hippocampal traces support recollection
        # Cortical traces support familiarity

        if trace.hippocampal > 0.5 and match_score >= self._recollection_threshold:
            return RetrievalMode.RECOLLECTION
        elif match_score >= self._familiarity_threshold:
            return RetrievalMode.FAMILIARITY
        else:
            return RetrievalMode.FAMILIARITY


# ============================================================================
# FORGETTING
# ============================================================================

class TraceDecay:
    """
    Memory trace decay.

    "Ba'el forgets traces." — Ba'el
    """

    def __init__(
        self,
        decay_rate: float = 0.01
    ):
        """Initialize decay."""
        self._decay_rate = decay_rate
        self._lock = threading.RLock()

    def decay(
        self,
        trace: MemoryTrace,
        time_elapsed: float = 1.0
    ) -> float:
        """Apply decay to trace."""
        with self._lock:
            # Decay based on age and access
            decay_factor = self._decay_rate * time_elapsed

            # More cortical = more resistant
            resistance = trace.cortical * 0.5

            effective_decay = decay_factor * (1.0 - resistance)

            trace.strength = max(0.0, trace.strength - effective_decay)
            trace.hippocampal = max(0.0, trace.hippocampal - effective_decay * 2)

            if trace.strength < 0.1:
                trace.status = TraceStatus.DEGRADING

            return effective_decay

    def interference(
        self,
        target_trace: MemoryTrace,
        interfering_traces: List[MemoryTrace]
    ) -> float:
        """Apply retroactive interference."""
        with self._lock:
            interference_amount = 0.0

            for other in interfering_traces:
                if other.id == target_trace.id:
                    continue

                # Similar traces interfere more
                similarity = self._compute_similarity(target_trace, other)

                # More recent interfering traces have more effect
                recency_factor = 1.0 / (1.0 + other.recency)

                interference_amount += similarity * recency_factor * 0.1

            target_trace.strength = max(0.0, target_trace.strength - interference_amount)

            return interference_amount

    def _compute_similarity(
        self,
        trace1: MemoryTrace,
        trace2: MemoryTrace
    ) -> float:
        """Compute similarity between traces."""
        if trace1.content == trace2.content:
            return 1.0

        # Context overlap
        keys1 = set(trace1.context.keys())
        keys2 = set(trace2.context.keys())

        if not keys1 or not keys2:
            return 0.0

        overlap = len(keys1 & keys2) / len(keys1 | keys2)
        return overlap


# ============================================================================
# MULTIPLE TRACE ENGINE
# ============================================================================

class MultipleTraceEngine:
    """
    Complete Multiple Trace Theory engine.

    "Ba'el's trace memory system." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._formation = TraceFormation()
        self._consolidator = Consolidator()
        self._retrieval = TraceRetrieval()
        self._decay = TraceDecay()

        self._traces: Dict[str, MemoryTrace] = {}
        self._bundles: Dict[str, TraceBundle] = {}

        self._bundle_counter = 0
        self._lock = threading.RLock()

    def _generate_bundle_id(self) -> str:
        self._bundle_counter += 1
        return f"bundle_{self._bundle_counter}"

    # Encoding

    def encode(
        self,
        content: Any,
        context: Dict[str, Any] = None,
        memory_type: MemoryType = MemoryType.EPISODIC
    ) -> MemoryTrace:
        """Encode new memory."""
        trace = self._formation.encode(
            content, context or {}, memory_type
        )
        self._traces[trace.id] = trace
        return trace

    # Retrieval

    def retrieve(
        self,
        cue: Dict[str, Any],
        top_k: int = 5
    ) -> List[RetrievalResult]:
        """Retrieve memories matching cue."""
        traces = list(self._traces.values())
        results = self._retrieval.retrieve(cue, traces)

        # Reactivation creates new traces
        for result in results[:top_k]:
            if result.reactivated:
                new_trace = self._formation.reactivate(result.trace)
                self._traces[new_trace.id] = new_trace

        return results[:top_k]

    def remember(self, content: Any) -> List[MemoryTrace]:
        """Simple content-based retrieval."""
        results = self.retrieve({'content': content})
        return [r.trace for r in results]

    # Consolidation

    def consolidate(
        self,
        trace_id: str = None
    ) -> List[ConsolidationResult]:
        """Run consolidation."""
        if trace_id:
            trace = self._traces.get(trace_id)
            if trace:
                return [self._consolidator.consolidate(trace)]
            return []

        return [
            self._consolidator.consolidate(trace)
            for trace in self._traces.values()
        ]

    def sleep(self, cycles: int = 5) -> List[ConsolidationResult]:
        """Simulate sleep consolidation."""
        traces = list(self._traces.values())
        return self._consolidator.sleep_consolidation(traces, cycles)

    # Decay

    def apply_decay(self, time_elapsed: float = 1.0) -> None:
        """Apply decay to all traces."""
        for trace in list(self._traces.values()):
            self._decay.decay(trace, time_elapsed)

            # Remove very weak traces
            if trace.strength < 0.01:
                del self._traces[trace.id]

    def apply_interference(self, trace_id: str) -> float:
        """Apply interference to trace."""
        trace = self._traces.get(trace_id)
        if not trace:
            return 0.0

        others = [t for t in self._traces.values() if t.id != trace_id]
        return self._decay.interference(trace, others)

    # Analysis

    def get_trace_count(
        self,
        content: Any = None
    ) -> int:
        """Get number of traces (optionally for content)."""
        if content is None:
            return len(self._traces)

        return sum(
            1 for t in self._traces.values()
            if t.content == content
        )

    def get_average_strength(self) -> float:
        """Get average trace strength."""
        if not self._traces:
            return 0.0
        return sum(t.strength for t in self._traces.values()) / len(self._traces)

    @property
    def traces(self) -> List[MemoryTrace]:
        return list(self._traces.values())

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'total_traces': len(self._traces),
            'average_strength': self.get_average_strength(),
            'episodic': sum(1 for t in self._traces.values() if t.memory_type == MemoryType.EPISODIC),
            'semantic': sum(1 for t in self._traces.values() if t.memory_type == MemoryType.SEMANTIC)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_multiple_trace_engine() -> MultipleTraceEngine:
    """Create Multiple Trace Theory engine."""
    return MultipleTraceEngine()


def encode_memory(
    content: Any,
    context: Dict[str, Any] = None
) -> MemoryTrace:
    """Quick memory encoding."""
    engine = create_multiple_trace_engine()
    return engine.encode(content, context)

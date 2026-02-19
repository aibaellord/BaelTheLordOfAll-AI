"""
BAEL Chaos Engineering Engine Implementation
=============================================

Controlled chaos for resilience testing.

"Ba'el introduces chaos to forge strength." — Ba'el
"""

import asyncio
import logging
import random
import threading
import time
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import uuid

logger = logging.getLogger("BAEL.Chaos")


# ============================================================================
# ENUMS
# ============================================================================

class ChaosType(Enum):
    """Types of chaos to inject."""
    LATENCY = "latency"             # Add delay
    ERROR = "error"                 # Return errors
    EXCEPTION = "exception"         # Throw exception
    TIMEOUT = "timeout"             # Force timeout
    KILL = "kill"                   # Kill process
    CPU_STRESS = "cpu_stress"       # High CPU usage
    MEMORY_STRESS = "memory_stress" # High memory usage
    NETWORK_PARTITION = "network_partition"  # Network isolation
    DNS_FAILURE = "dns_failure"     # DNS resolution failure
    DISK_FULL = "disk_full"         # Disk space exhaustion
    DATA_CORRUPTION = "data_corruption"  # Corrupt data


class ChaosState(Enum):
    """Chaos experiment states."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    ABORTED = "aborted"
    FAILED = "failed"


class ChaosScope(Enum):
    """Scope of chaos."""
    SERVICE = "service"
    CONTAINER = "container"
    HOST = "host"
    ZONE = "zone"
    REGION = "region"


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class ChaosTarget:
    """Target for chaos injection."""
    name: str
    target_type: str  # service, container, host
    selector: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ChaosExperiment:
    """A chaos experiment."""
    id: str
    name: str
    chaos_type: ChaosType
    targets: List[ChaosTarget]

    # Configuration
    duration_seconds: float = 30.0
    probability: float = 1.0  # 0-1, chance of injection

    # Type-specific config
    latency_ms: Optional[float] = None      # For latency
    error_code: Optional[int] = None        # For error
    error_message: Optional[str] = None
    cpu_percent: Optional[float] = None     # For CPU stress
    memory_percent: Optional[float] = None  # For memory stress

    # State
    state: ChaosState = ChaosState.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Results
    injections: int = 0
    affected_requests: int = 0

    # Metadata
    hypothesis: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_active(self) -> bool:
        return self.state == ChaosState.RUNNING

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'chaos_type': self.chaos_type.value,
            'targets': [{'name': t.name, 'type': t.target_type} for t in self.targets],
            'duration_seconds': self.duration_seconds,
            'probability': self.probability,
            'state': self.state.value,
            'injections': self.injections,
            'hypothesis': self.hypothesis
        }


@dataclass
class ChaosConfig:
    """Chaos engine configuration."""
    enabled: bool = False  # Safety default
    max_concurrent_experiments: int = 3
    default_duration_seconds: float = 30.0
    safe_mode: bool = True  # Extra safety checks


# ============================================================================
# CHAOS ENGINE
# ============================================================================

class ChaosEngine:
    """
    Chaos engineering engine.

    Features:
    - Multiple chaos types
    - Probability-based injection
    - Automatic rollback
    - Safety controls

    "Ba'el forges resilience through chaos." — Ba'el
    """

    def __init__(self, config: Optional[ChaosConfig] = None):
        """Initialize chaos engine."""
        self.config = config or ChaosConfig()

        # Experiments: id -> experiment
        self._experiments: Dict[str, ChaosExperiment] = {}

        # Active injections
        self._active_injections: Dict[str, asyncio.Task] = {}

        # Hooks
        self._injection_hooks: Dict[str, Callable] = {}
        self._pre_hooks: List[Callable] = []
        self._post_hooks: List[Callable] = []

        # Thread safety
        self._lock = threading.RLock()

        # Stats
        self._stats = {
            'experiments_run': 0,
            'total_injections': 0,
            'aborted': 0
        }

        logger.info("Chaos Engine initialized (enabled={})".format(self.config.enabled))

    # ========================================================================
    # EXPERIMENT MANAGEMENT
    # ========================================================================

    def create_experiment(
        self,
        name: str,
        chaos_type: ChaosType,
        targets: List[ChaosTarget],
        duration_seconds: Optional[float] = None,
        probability: float = 1.0,
        experiment_id: Optional[str] = None,
        hypothesis: str = "",
        **kwargs
    ) -> ChaosExperiment:
        """
        Create a chaos experiment.

        Args:
            name: Experiment name
            chaos_type: Type of chaos
            targets: Targets for injection
            duration_seconds: Experiment duration
            probability: Injection probability
            experiment_id: Optional ID
            hypothesis: What we expect to happen
            **kwargs: Type-specific config

        Returns:
            ChaosExperiment
        """
        experiment = ChaosExperiment(
            id=experiment_id or str(uuid.uuid4()),
            name=name,
            chaos_type=chaos_type,
            targets=targets,
            duration_seconds=duration_seconds or self.config.default_duration_seconds,
            probability=probability,
            hypothesis=hypothesis,
            latency_ms=kwargs.get('latency_ms'),
            error_code=kwargs.get('error_code'),
            error_message=kwargs.get('error_message'),
            cpu_percent=kwargs.get('cpu_percent'),
            memory_percent=kwargs.get('memory_percent'),
            metadata=kwargs.get('metadata', {})
        )

        with self._lock:
            self._experiments[experiment.id] = experiment

        logger.info(f"Chaos experiment created: {name}")

        return experiment

    async def run_experiment(
        self,
        experiment_id: str
    ) -> ChaosExperiment:
        """
        Run a chaos experiment.

        Args:
            experiment_id: Experiment to run

        Returns:
            Updated experiment
        """
        if not self.config.enabled:
            raise RuntimeError("Chaos engine is disabled")

        with self._lock:
            experiment = self._experiments.get(experiment_id)
            if not experiment:
                raise ValueError(f"Experiment not found: {experiment_id}")

            # Check concurrent limit
            active_count = sum(
                1 for e in self._experiments.values()
                if e.state == ChaosState.RUNNING
            )
            if active_count >= self.config.max_concurrent_experiments:
                raise RuntimeError("Max concurrent experiments reached")

            experiment.state = ChaosState.RUNNING
            experiment.started_at = datetime.now()

        # Run pre-hooks
        for hook in self._pre_hooks:
            try:
                await self._call_hook(hook, experiment)
            except Exception as e:
                logger.error(f"Pre-hook error: {e}")

        try:
            # Start injection task
            task = asyncio.create_task(
                self._run_injection(experiment)
            )
            self._active_injections[experiment_id] = task

            # Wait for completion
            await task

            experiment.state = ChaosState.COMPLETED

        except asyncio.CancelledError:
            experiment.state = ChaosState.ABORTED
            self._stats['aborted'] += 1

        except Exception as e:
            experiment.state = ChaosState.FAILED
            logger.error(f"Experiment failed: {e}")

        finally:
            experiment.completed_at = datetime.now()
            self._stats['experiments_run'] += 1

            if experiment_id in self._active_injections:
                del self._active_injections[experiment_id]

        # Run post-hooks
        for hook in self._post_hooks:
            try:
                await self._call_hook(hook, experiment)
            except Exception as e:
                logger.error(f"Post-hook error: {e}")

        return experiment

    async def _run_injection(self, experiment: ChaosExperiment) -> None:
        """Run chaos injection loop."""
        end_time = time.time() + experiment.duration_seconds

        while time.time() < end_time and experiment.state == ChaosState.RUNNING:
            # Check probability
            if random.random() <= experiment.probability:
                await self._inject_chaos(experiment)
                experiment.injections += 1
                self._stats['total_injections'] += 1

            await asyncio.sleep(0.1)

    async def _inject_chaos(self, experiment: ChaosExperiment) -> None:
        """Inject chaos based on type."""
        chaos_type = experiment.chaos_type

        # Get hook if registered
        hook = self._injection_hooks.get(chaos_type.value)

        if hook:
            await self._call_hook(hook, experiment)
            return

        # Built-in implementations
        if chaos_type == ChaosType.LATENCY:
            delay = (experiment.latency_ms or 100) / 1000
            await asyncio.sleep(delay)

        elif chaos_type == ChaosType.EXCEPTION:
            raise Exception(
                experiment.error_message or "Chaos exception"
            )

        elif chaos_type == ChaosType.CPU_STRESS:
            await self._cpu_stress(experiment.cpu_percent or 50)

        elif chaos_type == ChaosType.MEMORY_STRESS:
            await self._memory_stress(experiment.memory_percent or 50)

    async def _cpu_stress(self, percent: float) -> None:
        """Simulate CPU stress."""
        duration = 0.1
        busy_time = duration * (percent / 100)

        start = time.time()
        while time.time() - start < busy_time:
            _ = [x ** 2 for x in range(1000)]

    async def _memory_stress(self, percent: float) -> None:
        """Simulate memory stress."""
        # Allocate some memory temporarily
        size = int(1024 * 1024 * percent)  # MB based on percent
        _ = bytearray(min(size, 10 * 1024 * 1024))  # Cap at 10MB for safety
        await asyncio.sleep(0.1)

    async def _call_hook(self, hook: Callable, experiment: ChaosExperiment) -> None:
        """Call hook function."""
        if asyncio.iscoroutinefunction(hook):
            await hook(experiment)
        else:
            await asyncio.to_thread(hook, experiment)

    def abort_experiment(self, experiment_id: str) -> bool:
        """Abort a running experiment."""
        with self._lock:
            task = self._active_injections.get(experiment_id)
            if task:
                task.cancel()
                return True
        return False

    # ========================================================================
    # CHAOS INJECTION
    # ========================================================================

    def inject(
        self,
        chaos_type: ChaosType,
        target: str,
        **kwargs
    ) -> bool:
        """
        Inject chaos immediately (one-shot).

        Args:
            chaos_type: Type of chaos
            target: Target name
            **kwargs: Type-specific args

        Returns:
            True if injected
        """
        if not self.config.enabled:
            return False

        # Create and run quick experiment
        experiment = self.create_experiment(
            name=f"quick_{chaos_type.value}",
            chaos_type=chaos_type,
            targets=[ChaosTarget(name=target, target_type="quick")],
            duration_seconds=0.1,
            **kwargs
        )

        try:
            asyncio.run(self._inject_chaos(experiment))
            return True
        except Exception:
            return False

    def should_inject(self, probability: float = 1.0) -> bool:
        """Check if chaos should be injected."""
        if not self.config.enabled:
            return False
        return random.random() <= probability

    # ========================================================================
    # HOOKS
    # ========================================================================

    def register_injection_hook(
        self,
        chaos_type: ChaosType,
        hook: Callable
    ) -> None:
        """Register custom injection hook."""
        self._injection_hooks[chaos_type.value] = hook

    def add_pre_hook(self, hook: Callable) -> None:
        """Add pre-experiment hook."""
        self._pre_hooks.append(hook)

    def add_post_hook(self, hook: Callable) -> None:
        """Add post-experiment hook."""
        self._post_hooks.append(hook)

    # ========================================================================
    # QUERIES
    # ========================================================================

    def get_experiment(self, experiment_id: str) -> Optional[ChaosExperiment]:
        """Get experiment by ID."""
        return self._experiments.get(experiment_id)

    def list_experiments(
        self,
        state: Optional[ChaosState] = None
    ) -> List[ChaosExperiment]:
        """List experiments."""
        with self._lock:
            experiments = list(self._experiments.values())
            if state:
                experiments = [e for e in experiments if e.state == state]
            return experiments

    # ========================================================================
    # CONTROL
    # ========================================================================

    def enable(self) -> None:
        """Enable chaos engine."""
        self.config.enabled = True
        logger.warning("Chaos engine ENABLED")

    def disable(self) -> None:
        """Disable chaos engine."""
        self.config.enabled = False
        logger.info("Chaos engine disabled")

    async def abort_all(self) -> int:
        """Abort all running experiments."""
        aborted = 0
        for exp_id in list(self._active_injections.keys()):
            if self.abort_experiment(exp_id):
                aborted += 1
        return aborted

    # ========================================================================
    # STATS
    # ========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics."""
        with self._lock:
            running = sum(
                1 for e in self._experiments.values()
                if e.state == ChaosState.RUNNING
            )

        return {
            'enabled': self.config.enabled,
            'running_experiments': running,
            'total_experiments': len(self._experiments),
            **self._stats
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

chaos_engine = ChaosEngine()


def inject_chaos(chaos_type: ChaosType, target: str, **kwargs) -> bool:
    """Inject chaos."""
    return chaos_engine.inject(chaos_type, target, **kwargs)


async def run_experiment(experiment_id: str) -> ChaosExperiment:
    """Run chaos experiment."""
    return await chaos_engine.run_experiment(experiment_id)

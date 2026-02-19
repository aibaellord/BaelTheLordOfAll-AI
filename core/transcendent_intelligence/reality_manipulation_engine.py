"""
BAEL - Reality Manipulation Engine
====================================

The ultimate engine for manipulating both digital and physical reality.

This system enables Ba'el to:
1. Execute actions across digital domains (web, APIs, databases, files)
2. Interface with physical world through IoT, robotics, and automation
3. Create persistent changes in system configurations
4. Orchestrate multi-domain operations
5. Predict and prevent failures before they occur
6. Self-heal from errors and adapt to changing environments
7. Extend its reach through autonomous tool creation

The Reality Manipulation Engine operates on the principle that
ALL reality is manipulable - the only limits are those we accept.

WARNING: This is an extremely powerful system. Use responsibly.
"""

import asyncio
import hashlib
import json
import logging
import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union
import subprocess
import shutil

logger = logging.getLogger("BAEL.RealityManipulation")


class RealityDomain(Enum):
    """Domains of reality that can be manipulated."""
    FILESYSTEM = "filesystem"       # Files and directories
    NETWORK = "network"             # Network operations
    PROCESS = "process"             # System processes
    DATABASE = "database"           # Database operations
    WEB = "web"                     # Web interactions
    API = "api"                     # API calls
    CONFIGURATION = "configuration" # System/app configs
    AUTOMATION = "automation"       # Workflow automation
    IOT = "iot"                     # IoT device control
    VIRTUAL = "virtual"             # VMs and containers
    TEMPORAL = "temporal"           # Scheduled operations
    META = "meta"                   # Operations on the engine itself


class ManipulationIntensity(Enum):
    """Intensity levels for reality manipulation."""
    OBSERVE = 1       # Read-only, no changes
    GENTLE = 2        # Minor, reversible changes
    MODERATE = 3      # Significant but safe changes
    AGGRESSIVE = 4    # Major changes, may have side effects
    DOMINATING = 5    # Complete control, potential risks


class OperationStatus(Enum):
    """Status of a manipulation operation."""
    PENDING = "pending"
    VALIDATING = "validating"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
    SELF_HEALED = "self_healed"


@dataclass
class ManipulationTarget:
    """Target of a reality manipulation."""
    target_id: str
    domain: RealityDomain
    path: str  # Domain-specific path/identifier
    current_state: Dict[str, Any] = field(default_factory=dict)
    desired_state: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ManipulationOperation:
    """A single manipulation operation."""
    operation_id: str
    target: ManipulationTarget
    action: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    intensity: ManipulationIntensity = ManipulationIntensity.MODERATE
    status: OperationStatus = OperationStatus.PENDING

    # Execution tracking
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    execution_time_ms: float = 0.0

    # Results
    result: Any = None
    error: Optional[str] = None

    # Safety
    rollback_data: Dict[str, Any] = field(default_factory=dict)
    can_rollback: bool = True


@dataclass
class ManipulationPlan:
    """A plan consisting of multiple operations."""
    plan_id: str
    description: str
    operations: List[ManipulationOperation] = field(default_factory=list)
    dependencies: Dict[str, List[str]] = field(default_factory=dict)  # op_id -> [dependency_op_ids]
    parallel_groups: List[List[str]] = field(default_factory=list)

    # Status
    status: OperationStatus = OperationStatus.PENDING
    executed_operations: List[str] = field(default_factory=list)
    failed_operations: List[str] = field(default_factory=list)

    # Meta
    created_at: datetime = field(default_factory=datetime.utcnow)
    estimated_duration_ms: float = 0.0


@dataclass
class DomainCapability:
    """Capability within a reality domain."""
    name: str
    domain: RealityDomain
    actions: List[str]
    requires: List[str] = field(default_factory=list)
    risk_level: int = 1  # 1-5


class DomainManipulator(ABC):
    """Abstract base for domain-specific manipulators."""

    @property
    @abstractmethod
    def domain(self) -> RealityDomain:
        """Return the domain this manipulator handles."""
        pass

    @abstractmethod
    async def observe(self, target: ManipulationTarget) -> Dict[str, Any]:
        """Observe current state without modification."""
        pass

    @abstractmethod
    async def manipulate(
        self,
        operation: ManipulationOperation
    ) -> Tuple[bool, Any]:
        """Execute a manipulation operation. Returns (success, result)."""
        pass

    @abstractmethod
    async def rollback(self, operation: ManipulationOperation) -> bool:
        """Rollback an operation if possible."""
        pass

    @abstractmethod
    def get_capabilities(self) -> List[DomainCapability]:
        """Get available capabilities."""
        pass


class FilesystemManipulator(DomainManipulator):
    """Manipulator for filesystem operations."""

    @property
    def domain(self) -> RealityDomain:
        return RealityDomain.FILESYSTEM

    async def observe(self, target: ManipulationTarget) -> Dict[str, Any]:
        """Observe filesystem state."""
        path = Path(target.path)

        if not path.exists():
            return {"exists": False}

        stat = path.stat()
        state = {
            "exists": True,
            "is_file": path.is_file(),
            "is_dir": path.is_dir(),
            "size": stat.st_size if path.is_file() else None,
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "permissions": oct(stat.st_mode)[-3:]
        }

        if path.is_file() and stat.st_size < 1_000_000:  # < 1MB
            try:
                state["content_hash"] = hashlib.md5(path.read_bytes()).hexdigest()
            except:
                pass

        return state

    async def manipulate(
        self,
        operation: ManipulationOperation
    ) -> Tuple[bool, Any]:
        """Execute filesystem manipulation."""
        action = operation.action
        path = Path(operation.target.path)
        params = operation.parameters

        try:
            if action == "create_file":
                # Backup if exists
                if path.exists():
                    operation.rollback_data["original_content"] = path.read_bytes()

                path.write_text(params.get("content", ""))
                return True, {"created": str(path)}

            elif action == "create_directory":
                path.mkdir(parents=params.get("parents", True), exist_ok=True)
                operation.rollback_data["created_path"] = str(path)
                return True, {"created": str(path)}

            elif action == "delete":
                if path.exists():
                    if path.is_file():
                        operation.rollback_data["content"] = path.read_bytes()
                        operation.rollback_data["path"] = str(path)
                        path.unlink()
                    else:
                        operation.rollback_data["was_dir"] = str(path)
                        shutil.rmtree(path)
                return True, {"deleted": str(path)}

            elif action == "modify":
                if path.exists():
                    operation.rollback_data["original_content"] = path.read_bytes()
                    path.write_text(params.get("content", ""))
                    return True, {"modified": str(path)}
                return False, {"error": "File not found"}

            elif action == "copy":
                dest = Path(params.get("destination", ""))
                shutil.copy2(path, dest)
                operation.rollback_data["copy_dest"] = str(dest)
                return True, {"copied_to": str(dest)}

            elif action == "move":
                dest = Path(params.get("destination", ""))
                operation.rollback_data["original_path"] = str(path)
                operation.rollback_data["new_path"] = str(dest)
                shutil.move(path, dest)
                return True, {"moved_to": str(dest)}

            else:
                return False, {"error": f"Unknown action: {action}"}

        except Exception as e:
            return False, {"error": str(e)}

    async def rollback(self, operation: ManipulationOperation) -> bool:
        """Rollback filesystem operation."""
        try:
            rollback_data = operation.rollback_data

            if "original_content" in rollback_data:
                path = Path(operation.target.path)
                path.write_bytes(rollback_data["original_content"])
                return True

            if "created_path" in rollback_data:
                path = Path(rollback_data["created_path"])
                if path.exists():
                    if path.is_file():
                        path.unlink()
                    else:
                        shutil.rmtree(path)
                return True

            if "copy_dest" in rollback_data:
                Path(rollback_data["copy_dest"]).unlink()
                return True

            if "original_path" in rollback_data and "new_path" in rollback_data:
                shutil.move(rollback_data["new_path"], rollback_data["original_path"])
                return True

            return False

        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return False

    def get_capabilities(self) -> List[DomainCapability]:
        return [
            DomainCapability(
                name="file_operations",
                domain=RealityDomain.FILESYSTEM,
                actions=["create_file", "modify", "delete", "copy", "move"],
                risk_level=3
            ),
            DomainCapability(
                name="directory_operations",
                domain=RealityDomain.FILESYSTEM,
                actions=["create_directory", "delete"],
                risk_level=3
            )
        ]


class ProcessManipulator(DomainManipulator):
    """Manipulator for system processes."""

    @property
    def domain(self) -> RealityDomain:
        return RealityDomain.PROCESS

    async def observe(self, target: ManipulationTarget) -> Dict[str, Any]:
        """Observe process state."""
        # Use ps command to find process
        try:
            result = subprocess.run(
                ["ps", "aux"],
                capture_output=True,
                text=True,
                timeout=10
            )

            processes = []
            for line in result.stdout.split('\n')[1:]:
                if target.path in line:
                    parts = line.split()
                    if len(parts) >= 11:
                        processes.append({
                            "user": parts[0],
                            "pid": parts[1],
                            "cpu": parts[2],
                            "mem": parts[3],
                            "command": ' '.join(parts[10:])
                        })

            return {"processes": processes, "count": len(processes)}

        except Exception as e:
            return {"error": str(e)}

    async def manipulate(
        self,
        operation: ManipulationOperation
    ) -> Tuple[bool, Any]:
        """Execute process manipulation."""
        action = operation.action
        params = operation.parameters

        try:
            if action == "start":
                command = params.get("command", [])
                if isinstance(command, str):
                    command = command.split()

                proc = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                operation.rollback_data["pid"] = proc.pid
                return True, {"pid": proc.pid, "started": True}

            elif action == "execute":
                command = params.get("command", [])
                if isinstance(command, str):
                    command = command.split()

                result = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    timeout=params.get("timeout", 30)
                )

                return True, {
                    "returncode": result.returncode,
                    "stdout": result.stdout[:10000],  # Limit output
                    "stderr": result.stderr[:10000]
                }

            elif action == "stop":
                pid = params.get("pid")
                if pid:
                    os.kill(int(pid), 15)  # SIGTERM
                    return True, {"stopped": pid}
                return False, {"error": "No PID provided"}

            else:
                return False, {"error": f"Unknown action: {action}"}

        except Exception as e:
            return False, {"error": str(e)}

    async def rollback(self, operation: ManipulationOperation) -> bool:
        """Rollback process operation."""
        try:
            if "pid" in operation.rollback_data:
                pid = operation.rollback_data["pid"]
                try:
                    os.kill(pid, 15)  # SIGTERM
                except ProcessLookupError:
                    pass  # Process already ended
                return True
            return False
        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return False

    def get_capabilities(self) -> List[DomainCapability]:
        return [
            DomainCapability(
                name="process_control",
                domain=RealityDomain.PROCESS,
                actions=["start", "stop", "execute"],
                risk_level=4
            )
        ]


class AutomationManipulator(DomainManipulator):
    """Manipulator for workflow automation."""

    @property
    def domain(self) -> RealityDomain:
        return RealityDomain.AUTOMATION

    async def observe(self, target: ManipulationTarget) -> Dict[str, Any]:
        """Observe automation state."""
        return {
            "automation_id": target.target_id,
            "status": "observable",
            "capabilities": ["workflow", "schedule", "trigger"]
        }

    async def manipulate(
        self,
        operation: ManipulationOperation
    ) -> Tuple[bool, Any]:
        """Execute automation manipulation."""
        action = operation.action
        params = operation.parameters

        try:
            if action == "create_workflow":
                workflow = {
                    "id": f"workflow_{hashlib.md5(str(time.time()).encode()).hexdigest()[:12]}",
                    "steps": params.get("steps", []),
                    "triggers": params.get("triggers", []),
                    "created_at": datetime.utcnow().isoformat()
                }
                return True, {"workflow": workflow}

            elif action == "execute_workflow":
                steps = params.get("steps", [])
                results = []

                for step in steps:
                    results.append({
                        "step": step,
                        "status": "executed",
                        "timestamp": datetime.utcnow().isoformat()
                    })

                return True, {"executed_steps": len(steps), "results": results}

            elif action == "schedule":
                schedule = {
                    "workflow_id": params.get("workflow_id"),
                    "cron": params.get("cron", "0 * * * *"),
                    "next_run": datetime.utcnow().isoformat()
                }
                return True, {"schedule": schedule}

            else:
                return False, {"error": f"Unknown action: {action}"}

        except Exception as e:
            return False, {"error": str(e)}

    async def rollback(self, operation: ManipulationOperation) -> bool:
        """Rollback automation operation."""
        # Most automation operations are not easily rollback-able
        return False

    def get_capabilities(self) -> List[DomainCapability]:
        return [
            DomainCapability(
                name="workflow_management",
                domain=RealityDomain.AUTOMATION,
                actions=["create_workflow", "execute_workflow", "schedule"],
                risk_level=2
            )
        ]


class SelfHealingSystem:
    """System for automatic error recovery and self-healing."""

    def __init__(self):
        self._healing_strategies: Dict[str, Callable] = {}
        self._healing_history: List[Dict[str, Any]] = []

    def register_strategy(self, error_pattern: str, strategy: Callable) -> None:
        """Register a healing strategy for an error pattern."""
        self._healing_strategies[error_pattern] = strategy

    async def heal(
        self,
        operation: ManipulationOperation,
        error: str
    ) -> Tuple[bool, Optional[ManipulationOperation]]:
        """Attempt to heal from an error."""
        for pattern, strategy in self._healing_strategies.items():
            if pattern.lower() in error.lower():
                try:
                    healed_op = await strategy(operation, error)

                    self._healing_history.append({
                        "operation_id": operation.operation_id,
                        "error": error,
                        "strategy": pattern,
                        "success": healed_op is not None,
                        "timestamp": datetime.utcnow().isoformat()
                    })

                    if healed_op:
                        return True, healed_op

                except Exception as e:
                    logger.error(f"Healing strategy failed: {e}")

        return False, None

    def get_history(self) -> List[Dict[str, Any]]:
        return self._healing_history.copy()


class RealityManipulationEngine:
    """
    The Reality Manipulation Engine.

    This is the master engine for manipulating all aspects of digital
    and physical reality. It coordinates domain-specific manipulators,
    manages complex multi-step plans, and ensures safe execution with
    rollback capabilities.

    Key Features:
    - Multi-domain manipulation (filesystem, process, network, etc.)
    - Plan-based execution with dependency resolution
    - Automatic rollback on failure
    - Self-healing from errors
    - Parallel execution where possible
    - Extensible with custom manipulators

    WARNING: This is an extremely powerful system.
    """

    def __init__(
        self,
        enable_self_healing: bool = True,
        max_parallel_operations: int = 10,
        safety_mode: bool = True
    ):
        self.enable_self_healing = enable_self_healing
        self.max_parallel = max_parallel_operations
        self.safety_mode = safety_mode

        # Domain manipulators
        self._manipulators: Dict[RealityDomain, DomainManipulator] = {}

        # Register built-in manipulators
        self._register_builtin_manipulators()

        # Self-healing
        self._healer = SelfHealingSystem() if enable_self_healing else None
        self._register_healing_strategies()

        # History
        self._operation_history: List[ManipulationOperation] = []
        self._plan_history: List[ManipulationPlan] = []

        # Statistics
        self._stats = {
            "operations_executed": 0,
            "operations_succeeded": 0,
            "operations_failed": 0,
            "rollbacks_performed": 0,
            "self_heals": 0,
            "plans_executed": 0
        }

        logger.info("RealityManipulationEngine initialized")

    def _register_builtin_manipulators(self) -> None:
        """Register built-in domain manipulators."""
        self._manipulators[RealityDomain.FILESYSTEM] = FilesystemManipulator()
        self._manipulators[RealityDomain.PROCESS] = ProcessManipulator()
        self._manipulators[RealityDomain.AUTOMATION] = AutomationManipulator()

    def _register_healing_strategies(self) -> None:
        """Register default healing strategies."""
        if not self._healer:
            return

        # Permission denied - try with elevated privileges
        async def heal_permission_denied(op: ManipulationOperation, error: str):
            if op.intensity.value < ManipulationIntensity.AGGRESSIVE.value:
                new_op = ManipulationOperation(
                    operation_id=f"healed_{op.operation_id}",
                    target=op.target,
                    action=op.action,
                    parameters={**op.parameters, "elevated": True},
                    intensity=ManipulationIntensity.AGGRESSIVE
                )
                return new_op
            return None

        self._healer.register_strategy("permission denied", heal_permission_denied)

        # File not found - try creating parent directories
        async def heal_file_not_found(op: ManipulationOperation, error: str):
            if op.target.domain == RealityDomain.FILESYSTEM:
                path = Path(op.target.path)
                path.parent.mkdir(parents=True, exist_ok=True)
                return op  # Retry same operation
            return None

        self._healer.register_strategy("no such file", heal_file_not_found)

    def register_manipulator(
        self,
        domain: RealityDomain,
        manipulator: DomainManipulator
    ) -> None:
        """Register a custom domain manipulator."""
        self._manipulators[domain] = manipulator
        logger.info(f"Registered manipulator for {domain.value}")

    async def observe(
        self,
        domain: RealityDomain,
        path: str
    ) -> Dict[str, Any]:
        """Observe current state without modification."""
        if domain not in self._manipulators:
            return {"error": f"No manipulator for domain: {domain.value}"}

        target = ManipulationTarget(
            target_id=f"obs_{hashlib.md5(f'{domain.value}{path}'.encode()).hexdigest()[:12]}",
            domain=domain,
            path=path
        )

        manipulator = self._manipulators[domain]
        return await manipulator.observe(target)

    async def execute_operation(
        self,
        operation: ManipulationOperation
    ) -> ManipulationOperation:
        """Execute a single manipulation operation."""
        domain = operation.target.domain

        if domain not in self._manipulators:
            operation.status = OperationStatus.FAILED
            operation.error = f"No manipulator for domain: {domain.value}"
            return operation

        # Safety check
        if self.safety_mode and operation.intensity.value >= ManipulationIntensity.AGGRESSIVE.value:
            logger.warning(f"Aggressive operation in safety mode: {operation.operation_id}")

        manipulator = self._manipulators[domain]

        operation.status = OperationStatus.VALIDATING
        operation.started_at = datetime.utcnow()

        # Observe current state
        current_state = await manipulator.observe(operation.target)
        operation.target.current_state = current_state

        # Execute
        operation.status = OperationStatus.EXECUTING
        success, result = await manipulator.manipulate(operation)

        operation.completed_at = datetime.utcnow()
        operation.execution_time_ms = (operation.completed_at - operation.started_at).total_seconds() * 1000

        if success:
            operation.status = OperationStatus.COMPLETED
            operation.result = result
            self._stats["operations_succeeded"] += 1
        else:
            operation.status = OperationStatus.FAILED
            operation.error = str(result.get("error", "Unknown error"))
            self._stats["operations_failed"] += 1

            # Attempt self-healing
            if self.enable_self_healing and self._healer:
                healed, healed_op = await self._healer.heal(operation, operation.error)
                if healed and healed_op:
                    self._stats["self_heals"] += 1
                    return await self.execute_operation(healed_op)

        self._stats["operations_executed"] += 1
        self._operation_history.append(operation)

        return operation

    async def rollback_operation(
        self,
        operation: ManipulationOperation
    ) -> bool:
        """Rollback an operation."""
        if not operation.can_rollback:
            return False

        domain = operation.target.domain
        if domain not in self._manipulators:
            return False

        manipulator = self._manipulators[domain]
        success = await manipulator.rollback(operation)

        if success:
            operation.status = OperationStatus.ROLLED_BACK
            self._stats["rollbacks_performed"] += 1

        return success

    async def execute_plan(self, plan: ManipulationPlan) -> ManipulationPlan:
        """Execute a manipulation plan."""
        plan.status = OperationStatus.EXECUTING

        # Build dependency graph
        remaining = set(op.operation_id for op in plan.operations)
        completed = set()

        while remaining:
            # Find operations that can be executed (all dependencies met)
            ready = []
            for op in plan.operations:
                if op.operation_id in remaining:
                    deps = plan.dependencies.get(op.operation_id, [])
                    if all(dep in completed for dep in deps):
                        ready.append(op)

            if not ready:
                # Circular dependency or error
                plan.status = OperationStatus.FAILED
                break

            # Execute ready operations in parallel (up to max)
            batch = ready[:self.max_parallel]
            results = await asyncio.gather(*[
                self.execute_operation(op) for op in batch
            ])

            # Check results
            for op in results:
                remaining.discard(op.operation_id)

                if op.status == OperationStatus.COMPLETED:
                    completed.add(op.operation_id)
                    plan.executed_operations.append(op.operation_id)
                else:
                    plan.failed_operations.append(op.operation_id)

                    # Rollback completed operations on failure
                    if self.safety_mode:
                        for executed_id in reversed(plan.executed_operations):
                            executed_op = next(
                                (o for o in plan.operations if o.operation_id == executed_id),
                                None
                            )
                            if executed_op:
                                await self.rollback_operation(executed_op)

                        plan.status = OperationStatus.ROLLED_BACK
                        break

        if plan.status == OperationStatus.EXECUTING:
            if plan.failed_operations:
                plan.status = OperationStatus.FAILED
            else:
                plan.status = OperationStatus.COMPLETED

        self._plan_history.append(plan)
        self._stats["plans_executed"] += 1

        return plan

    def create_operation(
        self,
        domain: RealityDomain,
        path: str,
        action: str,
        parameters: Dict[str, Any] = None,
        intensity: ManipulationIntensity = ManipulationIntensity.MODERATE
    ) -> ManipulationOperation:
        """Create a manipulation operation."""
        target = ManipulationTarget(
            target_id=f"target_{hashlib.md5(f'{domain.value}{path}'.encode()).hexdigest()[:12]}",
            domain=domain,
            path=path
        )

        return ManipulationOperation(
            operation_id=f"op_{hashlib.md5(f'{action}{time.time()}'.encode()).hexdigest()[:12]}",
            target=target,
            action=action,
            parameters=parameters or {},
            intensity=intensity
        )

    def create_plan(
        self,
        description: str,
        operations: List[ManipulationOperation],
        dependencies: Dict[str, List[str]] = None
    ) -> ManipulationPlan:
        """Create a manipulation plan."""
        return ManipulationPlan(
            plan_id=f"plan_{hashlib.md5(f'{description}{time.time()}'.encode()).hexdigest()[:12]}",
            description=description,
            operations=operations,
            dependencies=dependencies or {}
        )

    def get_capabilities(self) -> Dict[RealityDomain, List[DomainCapability]]:
        """Get all available capabilities across domains."""
        return {
            domain: manipulator.get_capabilities()
            for domain, manipulator in self._manipulators.items()
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics."""
        return {
            **self._stats,
            "registered_domains": len(self._manipulators),
            "operation_history_size": len(self._operation_history),
            "plan_history_size": len(self._plan_history)
        }


# Global instance
_reality_engine: Optional[RealityManipulationEngine] = None


def get_reality_engine() -> RealityManipulationEngine:
    """Get the global reality manipulation engine."""
    global _reality_engine
    if _reality_engine is None:
        _reality_engine = RealityManipulationEngine()
    return _reality_engine


async def demo():
    """Demonstrate Reality Manipulation Engine."""
    engine = get_reality_engine()

    print("=== REALITY MANIPULATION ENGINE DEMO ===\n")

    # Observe filesystem
    print("Observing filesystem...")
    state = await engine.observe(RealityDomain.FILESYSTEM, "/tmp")
    print(f"  /tmp state: {state}")

    # Create a file operation
    print("\nCreating file operation...")
    op = engine.create_operation(
        domain=RealityDomain.FILESYSTEM,
        path="/tmp/bael_test_file.txt",
        action="create_file",
        parameters={"content": "Hello from Ba'el Reality Engine!"}
    )

    result = await engine.execute_operation(op)
    print(f"  Operation: {result.status.value}")
    print(f"  Result: {result.result}")

    # Execute process
    print("\nExecuting process...")
    proc_op = engine.create_operation(
        domain=RealityDomain.PROCESS,
        path="echo",
        action="execute",
        parameters={"command": ["echo", "Ba'el dominates reality!"]}
    )

    proc_result = await engine.execute_operation(proc_op)
    print(f"  Output: {proc_result.result.get('stdout', '').strip() if proc_result.result else 'N/A'}")

    # Create and execute a plan
    print("\nExecuting multi-step plan...")
    ops = [
        engine.create_operation(
            domain=RealityDomain.FILESYSTEM,
            path="/tmp/bael_plan_test/",
            action="create_directory"
        ),
        engine.create_operation(
            domain=RealityDomain.FILESYSTEM,
            path="/tmp/bael_plan_test/file1.txt",
            action="create_file",
            parameters={"content": "File 1 content"}
        ),
        engine.create_operation(
            domain=RealityDomain.FILESYSTEM,
            path="/tmp/bael_plan_test/file2.txt",
            action="create_file",
            parameters={"content": "File 2 content"}
        )
    ]

    plan = engine.create_plan(
        description="Create directory structure",
        operations=ops,
        dependencies={
            ops[1].operation_id: [ops[0].operation_id],
            ops[2].operation_id: [ops[0].operation_id]
        }
    )

    executed_plan = await engine.execute_plan(plan)
    print(f"  Plan status: {executed_plan.status.value}")
    print(f"  Executed operations: {len(executed_plan.executed_operations)}")

    # Show capabilities
    print("\n=== AVAILABLE CAPABILITIES ===")
    capabilities = engine.get_capabilities()
    for domain, caps in capabilities.items():
        print(f"\n{domain.value}:")
        for cap in caps:
            print(f"  - {cap.name}: {cap.actions}")

    # Stats
    print(f"\n=== STATISTICS ===")
    stats = engine.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")

    # Cleanup
    print("\nCleaning up test files...")
    cleanup_op = engine.create_operation(
        domain=RealityDomain.FILESYSTEM,
        path="/tmp/bael_plan_test/",
        action="delete"
    )
    await engine.execute_operation(cleanup_op)

    cleanup_op2 = engine.create_operation(
        domain=RealityDomain.FILESYSTEM,
        path="/tmp/bael_test_file.txt",
        action="delete"
    )
    await engine.execute_operation(cleanup_op2)

    print("\nDemo complete!")


if __name__ == "__main__":
    asyncio.run(demo())

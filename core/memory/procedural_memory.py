"""
BAEL Procedural Memory
=======================

Skill and procedure storage for AI agents.
Manages learned behaviors and action sequences.

Features:
- Procedure storage
- Skill acquisition
- Action sequences
- Procedure optimization
- Skill transfer
"""

import asyncio
import hashlib
import logging
import math
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class SkillLevel(Enum):
    """Skill proficiency levels."""
    NOVICE = "novice"
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"
    MASTER = "master"


class ActionType(Enum):
    """Types of actions in procedures."""
    ATOMIC = "atomic"  # Single operation
    SEQUENCE = "sequence"  # Ordered steps
    CONDITIONAL = "conditional"  # If-then
    LOOP = "loop"  # Repetition
    PARALLEL = "parallel"  # Concurrent


@dataclass
class Action:
    """An action in a procedure."""
    id: str
    name: str
    action_type: ActionType = ActionType.ATOMIC

    # Execution
    parameters: Dict[str, Any] = field(default_factory=dict)
    preconditions: List[str] = field(default_factory=list)
    postconditions: List[str] = field(default_factory=list)

    # Nested actions (for sequences, loops, etc.)
    children: List["Action"] = field(default_factory=list)

    # Conditional logic
    condition: Optional[str] = None
    else_action: Optional["Action"] = None

    # Performance
    avg_duration_ms: float = 0.0
    success_rate: float = 1.0


@dataclass
class ActionSequence:
    """A sequence of actions."""
    id: str
    name: str
    actions: List[Action] = field(default_factory=list)

    # Context
    applicable_contexts: List[str] = field(default_factory=list)

    # Performance metrics
    total_executions: int = 0
    successful_executions: int = 0
    avg_duration_ms: float = 0.0

    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_executions == 0:
            return 0.0
        return self.successful_executions / self.total_executions


@dataclass
class Skill:
    """A learned skill."""
    id: str
    name: str
    description: str = ""

    # Proficiency
    level: SkillLevel = SkillLevel.NOVICE
    experience_points: float = 0.0

    # Procedures associated with skill
    procedures: List[str] = field(default_factory=list)

    # Prerequisites
    prerequisites: List[str] = field(default_factory=list)

    # Related skills
    related_skills: List[str] = field(default_factory=list)

    # Metadata
    acquired_at: datetime = field(default_factory=datetime.now)
    last_practiced: datetime = field(default_factory=datetime.now)
    practice_count: int = 0

    def level_up(self) -> bool:
        """Check and apply level up."""
        thresholds = {
            SkillLevel.NOVICE: 10,
            SkillLevel.BEGINNER: 50,
            SkillLevel.INTERMEDIATE: 200,
            SkillLevel.ADVANCED: 500,
            SkillLevel.EXPERT: 1000,
            SkillLevel.MASTER: float('inf'),
        }

        levels = list(SkillLevel)
        current_idx = levels.index(self.level)

        if current_idx < len(levels) - 1:
            if self.experience_points >= thresholds[self.level]:
                self.level = levels[current_idx + 1]
                return True

        return False


@dataclass
class Procedure:
    """A procedural memory entry."""
    id: str
    name: str
    description: str = ""

    # Structure
    sequence: ActionSequence = None

    # Skill association
    skill_id: Optional[str] = None

    # Context
    trigger_conditions: List[str] = field(default_factory=list)
    applicable_domains: List[str] = field(default_factory=list)

    # Versions
    version: int = 1
    variants: List[str] = field(default_factory=list)

    # Performance
    executions: int = 0
    successes: int = 0
    failures: int = 0

    # Optimization
    optimized: bool = False
    optimization_score: float = 0.0

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    last_executed: Optional[datetime] = None

    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.executions == 0:
            return 0.0
        return self.successes / self.executions


class ProceduralMemory:
    """
    Procedural memory system for BAEL.

    Manages learned skills and action procedures.
    """

    def __init__(self):
        # Storage
        self._procedures: Dict[str, Procedure] = {}
        self._skills: Dict[str, Skill] = {}
        self._sequences: Dict[str, ActionSequence] = {}

        # Indices
        self._skill_procedures: Dict[str, Set[str]] = {}  # skill_id -> procedure_ids
        self._domain_procedures: Dict[str, Set[str]] = {}  # domain -> procedure_ids

        # Execution history
        self._execution_log: List[Dict[str, Any]] = []

        # Stats
        self.stats = {
            "procedures_created": 0,
            "skills_acquired": 0,
            "executions": 0,
            "optimizations": 0,
        }

    def create_procedure(
        self,
        name: str,
        actions: List[Dict[str, Any]],
        description: str = "",
        skill_id: Optional[str] = None,
        domains: Optional[List[str]] = None,
        triggers: Optional[List[str]] = None,
    ) -> Procedure:
        """
        Create a new procedure.

        Args:
            name: Procedure name
            actions: List of action definitions
            description: Procedure description
            skill_id: Associated skill
            domains: Applicable domains
            triggers: Trigger conditions

        Returns:
            Created procedure
        """
        proc_id = hashlib.md5(
            f"{name}:{datetime.now()}".encode()
        ).hexdigest()[:12]

        # Build action sequence
        sequence = self._build_sequence(name, actions)

        procedure = Procedure(
            id=proc_id,
            name=name,
            description=description,
            sequence=sequence,
            skill_id=skill_id,
            applicable_domains=domains or [],
            trigger_conditions=triggers or [],
        )

        self._procedures[proc_id] = procedure
        self._sequences[sequence.id] = sequence

        # Index
        if skill_id:
            if skill_id not in self._skill_procedures:
                self._skill_procedures[skill_id] = set()
            self._skill_procedures[skill_id].add(proc_id)

        for domain in procedure.applicable_domains:
            if domain not in self._domain_procedures:
                self._domain_procedures[domain] = set()
            self._domain_procedures[domain].add(proc_id)

        self.stats["procedures_created"] += 1

        logger.debug(f"Created procedure: {name}")

        return procedure

    def _build_sequence(
        self,
        name: str,
        actions: List[Dict[str, Any]],
    ) -> ActionSequence:
        """Build action sequence from definitions."""
        seq_id = hashlib.md5(name.encode()).hexdigest()[:12]

        built_actions = []
        for i, action_def in enumerate(actions):
            action = Action(
                id=f"{seq_id}_action_{i}",
                name=action_def.get("name", f"action_{i}"),
                action_type=ActionType(action_def.get("type", "atomic")),
                parameters=action_def.get("params", {}),
                preconditions=action_def.get("preconditions", []),
                postconditions=action_def.get("postconditions", []),
            )
            built_actions.append(action)

        return ActionSequence(
            id=seq_id,
            name=f"{name}_sequence",
            actions=built_actions,
        )

    def acquire_skill(
        self,
        name: str,
        description: str = "",
        prerequisites: Optional[List[str]] = None,
    ) -> Skill:
        """
        Acquire a new skill.

        Args:
            name: Skill name
            description: Skill description
            prerequisites: Required skills

        Returns:
            Acquired skill
        """
        skill_id = hashlib.md5(name.lower().encode()).hexdigest()[:12]

        if skill_id in self._skills:
            return self._skills[skill_id]

        # Check prerequisites
        if prerequisites:
            for prereq in prerequisites:
                prereq_id = hashlib.md5(prereq.lower().encode()).hexdigest()[:12]
                if prereq_id not in self._skills:
                    logger.warning(f"Missing prerequisite skill: {prereq}")

        skill = Skill(
            id=skill_id,
            name=name,
            description=description,
            prerequisites=prerequisites or [],
        )

        self._skills[skill_id] = skill
        self.stats["skills_acquired"] += 1

        logger.info(f"Acquired skill: {name}")

        return skill

    def get_skill(self, name: str) -> Optional[Skill]:
        """Get a skill by name."""
        skill_id = hashlib.md5(name.lower().encode()).hexdigest()[:12]
        return self._skills.get(skill_id)

    def practice_skill(
        self,
        skill_id: str,
        experience: float = 1.0,
        success: bool = True,
    ) -> Skill:
        """Practice a skill and gain experience."""
        if skill_id not in self._skills:
            raise ValueError(f"Unknown skill: {skill_id}")

        skill = self._skills[skill_id]

        # Gain experience
        multiplier = 1.0 if success else 0.5
        skill.experience_points += experience * multiplier
        skill.practice_count += 1
        skill.last_practiced = datetime.now()

        # Check level up
        if skill.level_up():
            logger.info(f"Skill {skill.name} leveled up to {skill.level.value}")

        return skill

    async def execute_procedure(
        self,
        procedure_id: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, Any]:
        """
        Execute a procedure.

        Args:
            procedure_id: Procedure to execute
            context: Execution context

        Returns:
            (success, result)
        """
        if procedure_id not in self._procedures:
            return False, "Unknown procedure"

        procedure = self._procedures[procedure_id]
        context = context or {}

        import time
        start = time.time()

        try:
            result = await self._execute_sequence(procedure.sequence, context)
            success = True

            procedure.successes += 1

        except Exception as e:
            result = str(e)
            success = False
            procedure.failures += 1
            logger.error(f"Procedure {procedure.name} failed: {e}")

        procedure.executions += 1
        procedure.last_executed = datetime.now()

        duration_ms = (time.time() - start) * 1000

        # Update sequence stats
        sequence = procedure.sequence
        sequence.total_executions += 1
        if success:
            sequence.successful_executions += 1
        sequence.avg_duration_ms = (
            sequence.avg_duration_ms * 0.9 + duration_ms * 0.1
        )

        # Practice associated skill
        if procedure.skill_id:
            self.practice_skill(procedure.skill_id, success=success)

        # Log execution
        self._execution_log.append({
            "procedure_id": procedure_id,
            "success": success,
            "duration_ms": duration_ms,
            "timestamp": datetime.now(),
        })

        self.stats["executions"] += 1

        return success, result

    async def _execute_sequence(
        self,
        sequence: ActionSequence,
        context: Dict[str, Any],
    ) -> Any:
        """Execute an action sequence."""
        results = []

        for action in sequence.actions:
            result = await self._execute_action(action, context)
            results.append(result)

            # Update context with postconditions
            for postcond in action.postconditions:
                context[postcond] = True

        return results

    async def _execute_action(
        self,
        action: Action,
        context: Dict[str, Any],
    ) -> Any:
        """Execute a single action."""
        # Check preconditions
        for precond in action.preconditions:
            if precond not in context or not context[precond]:
                raise ValueError(f"Precondition not met: {precond}")

        if action.action_type == ActionType.ATOMIC:
            # Simulate atomic action
            await asyncio.sleep(0.01)
            return {"action": action.name, "params": action.parameters}

        elif action.action_type == ActionType.SEQUENCE:
            results = []
            for child in action.children:
                result = await self._execute_action(child, context)
                results.append(result)
            return results

        elif action.action_type == ActionType.CONDITIONAL:
            if action.condition and context.get(action.condition):
                for child in action.children:
                    return await self._execute_action(child, context)
            elif action.else_action:
                return await self._execute_action(action.else_action, context)

        elif action.action_type == ActionType.LOOP:
            results = []
            max_iterations = action.parameters.get("max_iterations", 10)
            for _ in range(max_iterations):
                if action.condition and not context.get(action.condition):
                    break
                for child in action.children:
                    results.append(await self._execute_action(child, context))
            return results

        elif action.action_type == ActionType.PARALLEL:
            tasks = [
                self._execute_action(child, context)
                for child in action.children
            ]
            return await asyncio.gather(*tasks)

        return None

    def find_procedure(
        self,
        domain: Optional[str] = None,
        trigger: Optional[str] = None,
        skill: Optional[str] = None,
    ) -> List[Procedure]:
        """Find procedures matching criteria."""
        candidates = set(self._procedures.keys())

        # Filter by domain
        if domain and domain in self._domain_procedures:
            candidates &= self._domain_procedures[domain]

        # Filter by skill
        if skill:
            skill_id = hashlib.md5(skill.lower().encode()).hexdigest()[:12]
            if skill_id in self._skill_procedures:
                candidates &= self._skill_procedures[skill_id]

        # Get procedures
        results = []
        for proc_id in candidates:
            proc = self._procedures[proc_id]

            # Filter by trigger
            if trigger and trigger not in proc.trigger_conditions:
                continue

            results.append(proc)

        # Sort by success rate
        results.sort(key=lambda p: p.success_rate(), reverse=True)

        return results

    def optimize_procedure(
        self,
        procedure_id: str,
    ) -> Procedure:
        """Optimize a procedure based on execution history."""
        if procedure_id not in self._procedures:
            raise ValueError(f"Unknown procedure: {procedure_id}")

        procedure = self._procedures[procedure_id]

        # Analyze execution history
        proc_executions = [
            e for e in self._execution_log
            if e["procedure_id"] == procedure_id
        ]

        if len(proc_executions) < 5:
            return procedure  # Not enough data

        # Calculate optimization score
        success_rate = procedure.success_rate()
        avg_duration = sum(e["duration_ms"] for e in proc_executions) / len(proc_executions)

        # Simple optimization: remove slow actions (placeholder)
        procedure.optimization_score = success_rate * (1.0 / (1 + avg_duration / 1000))
        procedure.optimized = True
        procedure.version += 1

        self.stats["optimizations"] += 1

        logger.info(f"Optimized procedure {procedure.name}: score={procedure.optimization_score:.2f}")

        return procedure

    def transfer_skill(
        self,
        source_skill: str,
        target_skill: str,
        transfer_ratio: float = 0.5,
    ) -> Optional[Skill]:
        """Transfer experience from one skill to related skill."""
        source = self.get_skill(source_skill)
        target = self.get_skill(target_skill)

        if not source or not target:
            return None

        # Transfer portion of experience
        transferred = source.experience_points * transfer_ratio
        target.experience_points += transferred * 0.5  # Diminished transfer

        # Link skills
        if target.id not in source.related_skills:
            source.related_skills.append(target.id)
        if source.id not in target.related_skills:
            target.related_skills.append(source.id)

        target.level_up()

        return target

    def get_skills_summary(self) -> List[Dict[str, Any]]:
        """Get summary of all skills."""
        return [
            {
                "name": skill.name,
                "level": skill.level.value,
                "experience": skill.experience_points,
                "practices": skill.practice_count,
                "procedures": len(self._skill_procedures.get(skill.id, [])),
            }
            for skill in self._skills.values()
        ]

    def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics."""
        return {
            **self.stats,
            "total_procedures": len(self._procedures),
            "total_skills": len(self._skills),
            "execution_history": len(self._execution_log),
        }


def demo():
    """Demonstrate procedural memory."""
    import asyncio

    print("=" * 60)
    print("BAEL Procedural Memory Demo")
    print("=" * 60)

    async def run_demo():
        memory = ProceduralMemory()

        # Acquire skills
        print("\nAcquiring skills...")
        coding = memory.acquire_skill(
            "Coding",
            description="Writing computer programs",
        )

        debugging = memory.acquire_skill(
            "Debugging",
            description="Finding and fixing bugs",
            prerequisites=["Coding"],
        )

        print(f"  Acquired: {coding.name} ({coding.level.value})")
        print(f"  Acquired: {debugging.name} ({debugging.level.value})")

        # Create procedure
        print("\nCreating procedures...")

        debug_proc = memory.create_procedure(
            name="Debug Python Error",
            description="Debug a Python error",
            skill_id=debugging.id,
            domains=["python", "debugging"],
            triggers=["error_occurred"],
            actions=[
                {"name": "read_traceback", "type": "atomic", "params": {}},
                {"name": "identify_error_type", "type": "atomic", "params": {}},
                {"name": "locate_error_line", "type": "atomic", "params": {}},
                {"name": "analyze_context", "type": "atomic", "params": {}},
                {"name": "formulate_fix", "type": "atomic", "params": {}},
                {"name": "apply_fix", "type": "atomic", "params": {}},
                {"name": "verify_fix", "type": "atomic", "params": {}},
            ],
        )

        print(f"  Created: {debug_proc.name} ({len(debug_proc.sequence.actions)} actions)")

        # Execute procedure
        print("\nExecuting procedures...")

        for i in range(5):
            success, result = await memory.execute_procedure(
                debug_proc.id,
                context={"error": "NameError"},
            )
            print(f"  Execution {i+1}: {'✓' if success else '✗'}")

        # Check skill progress
        skill = memory.get_skill("Debugging")
        print(f"\n  Skill progress: {skill.level.value}, XP: {skill.experience_points}")

        # Optimize
        print("\nOptimizing...")
        optimized = memory.optimize_procedure(debug_proc.id)
        print(f"  Optimization score: {optimized.optimization_score:.2f}")

        # Find procedures
        print("\nFinding procedures...")
        procs = memory.find_procedure(domain="python")
        print(f"  Found {len(procs)} procedures for python")

        # Skills summary
        print("\nSkills summary:")
        for skill_info in memory.get_skills_summary():
            print(f"  - {skill_info['name']}: {skill_info['level']}, XP: {skill_info['experience']:.0f}")

        print(f"\nStats: {memory.get_stats()}")

    asyncio.run(run_demo())


if __name__ == "__main__":
    demo()

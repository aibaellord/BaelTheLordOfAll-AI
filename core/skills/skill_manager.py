#!/usr/bin/env python3
"""
BAEL - Skill Manager
Advanced skill management for AI agents.

Features:
- Skill registration
- Skill composition
- Skill learning
- Skill proficiency
- Skill prerequisites
- Skill execution
- Skill templates
- Skill analytics
"""

import asyncio
import copy
import hashlib
import json
import math
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import (Any, Awaitable, Callable, Dict, Generic, Iterator, List,
                    Optional, Set, Tuple, Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class SkillCategory(Enum):
    """Skill category."""
    REASONING = "reasoning"
    PLANNING = "planning"
    EXECUTION = "execution"
    COMMUNICATION = "communication"
    ANALYSIS = "analysis"
    SYNTHESIS = "synthesis"
    LEARNING = "learning"
    TOOLS = "tools"


class SkillLevel(Enum):
    """Skill level."""
    NOVICE = 1
    BEGINNER = 2
    INTERMEDIATE = 3
    ADVANCED = 4
    EXPERT = 5
    MASTER = 6


class SkillStatus(Enum):
    """Skill status."""
    AVAILABLE = "available"
    LEARNING = "learning"
    LOCKED = "locked"
    DEPRECATED = "deprecated"


class ExecutionMode(Enum):
    """Execution mode."""
    SYNC = "sync"
    ASYNC = "async"
    PARALLEL = "parallel"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class SkillParameter:
    """Skill parameter."""
    name: str
    param_type: str = "any"
    required: bool = True
    default: Any = None
    description: str = ""


@dataclass
class SkillResult:
    """Skill execution result."""
    skill_id: str = ""
    success: bool = True
    output: Any = None
    error: Optional[str] = None
    duration: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class SkillConfig:
    """Skill configuration."""
    skill_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    category: SkillCategory = SkillCategory.EXECUTION
    level: SkillLevel = SkillLevel.INTERMEDIATE
    status: SkillStatus = SkillStatus.AVAILABLE
    parameters: List[SkillParameter] = field(default_factory=list)
    prerequisites: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    timeout: float = 60.0
    retry_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SkillProficiency:
    """Skill proficiency."""
    skill_id: str = ""
    experience: float = 0.0
    level: SkillLevel = SkillLevel.NOVICE
    executions: int = 0
    successes: int = 0
    failures: int = 0
    avg_duration: float = 0.0
    last_used: Optional[datetime] = None


@dataclass
class SkillUsage:
    """Skill usage record."""
    skill_id: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    success: bool = True
    duration: float = 0.0
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SkillStats:
    """Skill statistics."""
    total_skills: int = 0
    available_skills: int = 0
    total_executions: int = 0
    success_rate: float = 0.0
    avg_duration: float = 0.0


# =============================================================================
# SKILL BASE
# =============================================================================

class Skill(ABC):
    """Base skill class."""

    def __init__(self, config: SkillConfig):
        self.config = config

    @property
    def skill_id(self) -> str:
        return self.config.skill_id

    @property
    def name(self) -> str:
        return self.config.name

    @property
    def category(self) -> SkillCategory:
        return self.config.category

    @abstractmethod
    async def execute(self, **kwargs: Any) -> Any:
        """Execute skill."""
        pass

    def validate_parameters(self, **kwargs: Any) -> bool:
        """Validate parameters."""
        for param in self.config.parameters:
            if param.required and param.name not in kwargs:
                if param.default is None:
                    return False
        return True

    def get_schema(self) -> Dict[str, Any]:
        """Get parameter schema."""
        return {
            "name": self.name,
            "parameters": {
                p.name: {
                    "type": p.param_type,
                    "required": p.required,
                    "default": p.default,
                    "description": p.description
                }
                for p in self.config.parameters
            }
        }


# =============================================================================
# FUNCTION SKILL
# =============================================================================

class FunctionSkill(Skill):
    """Skill wrapping a function."""

    def __init__(
        self,
        config: SkillConfig,
        func: Callable
    ):
        super().__init__(config)
        self._func = func

    async def execute(self, **kwargs: Any) -> Any:
        """Execute function."""
        if asyncio.iscoroutinefunction(self._func):
            return await self._func(**kwargs)
        return self._func(**kwargs)


# =============================================================================
# COMPOSITE SKILL
# =============================================================================

class CompositeSkill(Skill):
    """Skill composed of multiple skills."""

    def __init__(
        self,
        config: SkillConfig,
        skills: List[Skill],
        mode: ExecutionMode = ExecutionMode.SYNC
    ):
        super().__init__(config)
        self._skills = skills
        self._mode = mode

    async def execute(self, **kwargs: Any) -> List[Any]:
        """Execute all skills."""
        if self._mode == ExecutionMode.PARALLEL:
            tasks = [s.execute(**kwargs) for s in self._skills]
            return await asyncio.gather(*tasks, return_exceptions=True)
        else:
            results = []
            context = kwargs.copy()

            for skill in self._skills:
                result = await skill.execute(**context)
                results.append(result)
                context["_previous_result"] = result

            return results


# =============================================================================
# CONDITIONAL SKILL
# =============================================================================

class ConditionalSkill(Skill):
    """Skill with conditional execution."""

    def __init__(
        self,
        config: SkillConfig,
        condition: Callable[[Dict[str, Any]], bool],
        true_skill: Skill,
        false_skill: Optional[Skill] = None
    ):
        super().__init__(config)
        self._condition = condition
        self._true_skill = true_skill
        self._false_skill = false_skill

    async def execute(self, **kwargs: Any) -> Any:
        """Execute based on condition."""
        if self._condition(kwargs):
            return await self._true_skill.execute(**kwargs)
        elif self._false_skill:
            return await self._false_skill.execute(**kwargs)
        return None


# =============================================================================
# SKILL REGISTRY
# =============================================================================

class SkillRegistry:
    """Registry for skills."""

    def __init__(self):
        self._skills: Dict[str, Skill] = {}
        self._by_category: Dict[SkillCategory, Set[str]] = defaultdict(set)
        self._by_tag: Dict[str, Set[str]] = defaultdict(set)

    def register(self, skill: Skill) -> str:
        """Register skill."""
        self._skills[skill.skill_id] = skill
        self._by_category[skill.category].add(skill.skill_id)

        for tag in skill.config.tags:
            self._by_tag[tag].add(skill.skill_id)

        return skill.skill_id

    def unregister(self, skill_id: str) -> bool:
        """Unregister skill."""
        skill = self._skills.get(skill_id)

        if not skill:
            return False

        del self._skills[skill_id]
        self._by_category[skill.category].discard(skill_id)

        for tag in skill.config.tags:
            self._by_tag[tag].discard(skill_id)

        return True

    def get(self, skill_id: str) -> Optional[Skill]:
        """Get skill."""
        return self._skills.get(skill_id)

    def get_by_name(self, name: str) -> Optional[Skill]:
        """Get skill by name."""
        for skill in self._skills.values():
            if skill.name == name:
                return skill
        return None

    def get_by_category(self, category: SkillCategory) -> List[Skill]:
        """Get skills by category."""
        skill_ids = self._by_category.get(category, set())
        return [self._skills[sid] for sid in skill_ids if sid in self._skills]

    def get_by_tag(self, tag: str) -> List[Skill]:
        """Get skills by tag."""
        skill_ids = self._by_tag.get(tag, set())
        return [self._skills[sid] for sid in skill_ids if sid in self._skills]

    def list_all(self) -> List[Skill]:
        """List all skills."""
        return list(self._skills.values())

    def search(self, query: str) -> List[Skill]:
        """Search skills."""
        query_lower = query.lower()
        results = []

        for skill in self._skills.values():
            if query_lower in skill.name.lower():
                results.append(skill)
            elif query_lower in skill.config.description.lower():
                results.append(skill)
            elif any(query_lower in tag.lower() for tag in skill.config.tags):
                results.append(skill)

        return results


# =============================================================================
# SKILL EXECUTOR
# =============================================================================

class SkillExecutor:
    """Execute skills."""

    def __init__(self, registry: SkillRegistry):
        self._registry = registry
        self._execution_history: List[SkillUsage] = []

    async def execute(
        self,
        skill_id: str,
        **kwargs: Any
    ) -> SkillResult:
        """Execute skill."""
        skill = self._registry.get(skill_id)

        if not skill:
            return SkillResult(
                skill_id=skill_id,
                success=False,
                error="Skill not found"
            )

        if skill.config.status != SkillStatus.AVAILABLE:
            return SkillResult(
                skill_id=skill_id,
                success=False,
                error=f"Skill not available: {skill.config.status.value}"
            )

        if not skill.validate_parameters(**kwargs):
            return SkillResult(
                skill_id=skill_id,
                success=False,
                error="Invalid parameters"
            )

        start_time = time.time()

        try:
            output = await asyncio.wait_for(
                skill.execute(**kwargs),
                timeout=skill.config.timeout
            )

            duration = time.time() - start_time

            result = SkillResult(
                skill_id=skill_id,
                success=True,
                output=output,
                duration=duration
            )

        except asyncio.TimeoutError:
            result = SkillResult(
                skill_id=skill_id,
                success=False,
                error="Execution timeout",
                duration=skill.config.timeout
            )

        except Exception as e:
            duration = time.time() - start_time
            result = SkillResult(
                skill_id=skill_id,
                success=False,
                error=str(e),
                duration=duration
            )

        # Record usage
        self._execution_history.append(SkillUsage(
            skill_id=skill_id,
            success=result.success,
            duration=result.duration,
            parameters=kwargs
        ))

        return result

    async def execute_by_name(
        self,
        name: str,
        **kwargs: Any
    ) -> SkillResult:
        """Execute skill by name."""
        skill = self._registry.get_by_name(name)

        if not skill:
            return SkillResult(
                success=False,
                error=f"Skill not found: {name}"
            )

        return await self.execute(skill.skill_id, **kwargs)

    def get_history(self, limit: int = 100) -> List[SkillUsage]:
        """Get execution history."""
        return self._execution_history[-limit:]


# =============================================================================
# PROFICIENCY TRACKER
# =============================================================================

class ProficiencyTracker:
    """Track skill proficiency."""

    def __init__(self):
        self._proficiencies: Dict[str, SkillProficiency] = {}
        self._level_thresholds = {
            SkillLevel.NOVICE: 0,
            SkillLevel.BEGINNER: 10,
            SkillLevel.INTERMEDIATE: 50,
            SkillLevel.ADVANCED: 200,
            SkillLevel.EXPERT: 500,
            SkillLevel.MASTER: 1000
        }

    def record_execution(
        self,
        skill_id: str,
        success: bool,
        duration: float
    ) -> SkillProficiency:
        """Record skill execution."""
        if skill_id not in self._proficiencies:
            self._proficiencies[skill_id] = SkillProficiency(skill_id=skill_id)

        prof = self._proficiencies[skill_id]
        prof.executions += 1

        if success:
            prof.successes += 1
            prof.experience += 1.0
        else:
            prof.failures += 1
            prof.experience += 0.1  # Small XP for attempts

        # Update average duration
        n = prof.executions
        prof.avg_duration = ((prof.avg_duration * (n - 1)) + duration) / n
        prof.last_used = datetime.now()

        # Update level
        prof.level = self._calculate_level(prof.experience)

        return prof

    def _calculate_level(self, experience: float) -> SkillLevel:
        """Calculate level from experience."""
        current_level = SkillLevel.NOVICE

        for level, threshold in sorted(
            self._level_thresholds.items(),
            key=lambda x: x[1],
            reverse=True
        ):
            if experience >= threshold:
                current_level = level
                break

        return current_level

    def get_proficiency(self, skill_id: str) -> Optional[SkillProficiency]:
        """Get skill proficiency."""
        return self._proficiencies.get(skill_id)

    def get_all_proficiencies(self) -> List[SkillProficiency]:
        """Get all proficiencies."""
        return list(self._proficiencies.values())

    def get_by_level(self, level: SkillLevel) -> List[SkillProficiency]:
        """Get proficiencies by level."""
        return [p for p in self._proficiencies.values() if p.level == level]


# =============================================================================
# SKILL BUILDER
# =============================================================================

class SkillBuilder:
    """Builder for skills."""

    def __init__(self, name: str):
        self._config = SkillConfig(name=name)
        self._func: Optional[Callable] = None

    def description(self, description: str) -> "SkillBuilder":
        """Set description."""
        self._config.description = description
        return self

    def category(self, category: SkillCategory) -> "SkillBuilder":
        """Set category."""
        self._config.category = category
        return self

    def level(self, level: SkillLevel) -> "SkillBuilder":
        """Set level."""
        self._config.level = level
        return self

    def parameter(
        self,
        name: str,
        param_type: str = "any",
        required: bool = True,
        default: Any = None,
        description: str = ""
    ) -> "SkillBuilder":
        """Add parameter."""
        self._config.parameters.append(SkillParameter(
            name=name,
            param_type=param_type,
            required=required,
            default=default,
            description=description
        ))
        return self

    def prerequisite(self, skill_id: str) -> "SkillBuilder":
        """Add prerequisite."""
        self._config.prerequisites.append(skill_id)
        return self

    def tag(self, tag: str) -> "SkillBuilder":
        """Add tag."""
        self._config.tags.append(tag)
        return self

    def timeout(self, seconds: float) -> "SkillBuilder":
        """Set timeout."""
        self._config.timeout = seconds
        return self

    def handler(self, func: Callable) -> "SkillBuilder":
        """Set handler function."""
        self._func = func
        return self

    def build(self) -> Skill:
        """Build skill."""
        if not self._func:
            raise ValueError("Handler function required")

        return FunctionSkill(self._config, self._func)


# =============================================================================
# SKILL COMPOSER
# =============================================================================

class SkillComposer:
    """Compose skills."""

    def __init__(self, registry: SkillRegistry):
        self._registry = registry

    def sequence(
        self,
        name: str,
        skill_ids: List[str]
    ) -> CompositeSkill:
        """Create sequential skill."""
        skills = [self._registry.get(sid) for sid in skill_ids]
        skills = [s for s in skills if s is not None]

        config = SkillConfig(
            name=name,
            category=SkillCategory.EXECUTION
        )

        return CompositeSkill(config, skills, ExecutionMode.SYNC)

    def parallel(
        self,
        name: str,
        skill_ids: List[str]
    ) -> CompositeSkill:
        """Create parallel skill."""
        skills = [self._registry.get(sid) for sid in skill_ids]
        skills = [s for s in skills if s is not None]

        config = SkillConfig(
            name=name,
            category=SkillCategory.EXECUTION
        )

        return CompositeSkill(config, skills, ExecutionMode.PARALLEL)

    def conditional(
        self,
        name: str,
        condition: Callable[[Dict[str, Any]], bool],
        true_skill_id: str,
        false_skill_id: Optional[str] = None
    ) -> ConditionalSkill:
        """Create conditional skill."""
        true_skill = self._registry.get(true_skill_id)
        false_skill = self._registry.get(false_skill_id) if false_skill_id else None

        if not true_skill:
            raise ValueError(f"Skill not found: {true_skill_id}")

        config = SkillConfig(
            name=name,
            category=SkillCategory.EXECUTION
        )

        return ConditionalSkill(config, condition, true_skill, false_skill)


# =============================================================================
# SKILL MANAGER
# =============================================================================

class SkillManager:
    """
    Skill Manager for BAEL.

    Advanced skill management for AI agents.
    """

    def __init__(self):
        self._registry = SkillRegistry()
        self._executor = SkillExecutor(self._registry)
        self._proficiency_tracker = ProficiencyTracker()
        self._composer = SkillComposer(self._registry)

    # -------------------------------------------------------------------------
    # SKILL CREATION
    # -------------------------------------------------------------------------

    def create_skill(
        self,
        name: str,
        handler: Callable,
        category: str = "execution",
        description: str = "",
        tags: Optional[List[str]] = None
    ) -> Skill:
        """Create and register skill."""
        category_map = {
            "reasoning": SkillCategory.REASONING,
            "planning": SkillCategory.PLANNING,
            "execution": SkillCategory.EXECUTION,
            "communication": SkillCategory.COMMUNICATION,
            "analysis": SkillCategory.ANALYSIS,
            "synthesis": SkillCategory.SYNTHESIS,
            "learning": SkillCategory.LEARNING,
            "tools": SkillCategory.TOOLS
        }

        config = SkillConfig(
            name=name,
            description=description,
            category=category_map.get(category.lower(), SkillCategory.EXECUTION),
            tags=tags or []
        )

        skill = FunctionSkill(config, handler)
        self._registry.register(skill)

        return skill

    def builder(self, name: str) -> SkillBuilder:
        """Get skill builder."""
        return SkillBuilder(name)

    def register_skill(self, skill: Skill) -> str:
        """Register skill."""
        return self._registry.register(skill)

    # -------------------------------------------------------------------------
    # SKILL ACCESS
    # -------------------------------------------------------------------------

    def get_skill(self, skill_id: str) -> Optional[Skill]:
        """Get skill by ID."""
        return self._registry.get(skill_id)

    def get_by_name(self, name: str) -> Optional[Skill]:
        """Get skill by name."""
        return self._registry.get_by_name(name)

    def get_by_category(self, category: str) -> List[Skill]:
        """Get skills by category."""
        category_map = {
            "reasoning": SkillCategory.REASONING,
            "planning": SkillCategory.PLANNING,
            "execution": SkillCategory.EXECUTION,
            "communication": SkillCategory.COMMUNICATION,
            "analysis": SkillCategory.ANALYSIS,
            "synthesis": SkillCategory.SYNTHESIS,
            "learning": SkillCategory.LEARNING,
            "tools": SkillCategory.TOOLS
        }

        cat = category_map.get(category.lower())
        if cat:
            return self._registry.get_by_category(cat)
        return []

    def get_by_tag(self, tag: str) -> List[Skill]:
        """Get skills by tag."""
        return self._registry.get_by_tag(tag)

    def search_skills(self, query: str) -> List[Skill]:
        """Search skills."""
        return self._registry.search(query)

    def list_skills(self) -> List[Skill]:
        """List all skills."""
        return self._registry.list_all()

    # -------------------------------------------------------------------------
    # EXECUTION
    # -------------------------------------------------------------------------

    async def execute(
        self,
        skill_id: str,
        **kwargs: Any
    ) -> SkillResult:
        """Execute skill by ID."""
        result = await self._executor.execute(skill_id, **kwargs)

        # Track proficiency
        self._proficiency_tracker.record_execution(
            skill_id,
            result.success,
            result.duration
        )

        return result

    async def execute_by_name(
        self,
        name: str,
        **kwargs: Any
    ) -> SkillResult:
        """Execute skill by name."""
        skill = self._registry.get_by_name(name)

        if not skill:
            return SkillResult(
                success=False,
                error=f"Skill not found: {name}"
            )

        return await self.execute(skill.skill_id, **kwargs)

    # -------------------------------------------------------------------------
    # COMPOSITION
    # -------------------------------------------------------------------------

    def compose_sequence(
        self,
        name: str,
        skill_ids: List[str]
    ) -> Skill:
        """Compose sequential skill."""
        skill = self._composer.sequence(name, skill_ids)
        self._registry.register(skill)
        return skill

    def compose_parallel(
        self,
        name: str,
        skill_ids: List[str]
    ) -> Skill:
        """Compose parallel skill."""
        skill = self._composer.parallel(name, skill_ids)
        self._registry.register(skill)
        return skill

    def compose_conditional(
        self,
        name: str,
        condition: Callable[[Dict[str, Any]], bool],
        true_skill_id: str,
        false_skill_id: Optional[str] = None
    ) -> Skill:
        """Compose conditional skill."""
        skill = self._composer.conditional(
            name,
            condition,
            true_skill_id,
            false_skill_id
        )
        self._registry.register(skill)
        return skill

    # -------------------------------------------------------------------------
    # PROFICIENCY
    # -------------------------------------------------------------------------

    def get_proficiency(self, skill_id: str) -> Optional[SkillProficiency]:
        """Get skill proficiency."""
        return self._proficiency_tracker.get_proficiency(skill_id)

    def get_all_proficiencies(self) -> List[SkillProficiency]:
        """Get all proficiencies."""
        return self._proficiency_tracker.get_all_proficiencies()

    def get_mastered_skills(self) -> List[SkillProficiency]:
        """Get mastered skills."""
        return self._proficiency_tracker.get_by_level(SkillLevel.MASTER)

    def get_expert_skills(self) -> List[SkillProficiency]:
        """Get expert skills."""
        return self._proficiency_tracker.get_by_level(SkillLevel.EXPERT)

    # -------------------------------------------------------------------------
    # STATISTICS
    # -------------------------------------------------------------------------

    def get_stats(self) -> SkillStats:
        """Get skill statistics."""
        skills = self._registry.list_all()
        history = self._executor.get_history()

        available = sum(
            1 for s in skills
            if s.config.status == SkillStatus.AVAILABLE
        )

        successes = sum(1 for u in history if u.success)
        success_rate = successes / len(history) if history else 0.0

        durations = [u.duration for u in history]
        avg_duration = sum(durations) / len(durations) if durations else 0.0

        return SkillStats(
            total_skills=len(skills),
            available_skills=available,
            total_executions=len(history),
            success_rate=success_rate,
            avg_duration=avg_duration
        )

    def get_execution_history(self, limit: int = 100) -> List[SkillUsage]:
        """Get execution history."""
        return self._executor.get_history(limit)


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Skill Manager."""
    print("=" * 70)
    print("BAEL - SKILL MANAGER DEMO")
    print("Advanced Skill Management for AI Agents")
    print("=" * 70)
    print()

    manager = SkillManager()

    # 1. Create Skills
    print("1. CREATE SKILLS:")
    print("-" * 40)

    async def analyze_data(data: List[Any]) -> Dict[str, Any]:
        return {
            "count": len(data),
            "sum": sum(data) if all(isinstance(x, (int, float)) for x in data) else None
        }

    skill1 = manager.create_skill(
        name="analyze_data",
        handler=analyze_data,
        category="analysis",
        description="Analyze data arrays",
        tags=["data", "analysis"]
    )

    print(f"   Created: {skill1.name}")
    print(f"   Category: {skill1.category.value}")
    print()

    # 2. Builder Pattern
    print("2. BUILDER PATTERN:")
    print("-" * 40)

    skill2 = (manager.builder("format_output")
        .description("Format data for output")
        .category(SkillCategory.SYNTHESIS)
        .parameter("data", "dict", required=True)
        .parameter("format", "string", default="json")
        .tag("formatting")
        .timeout(30.0)
        .handler(lambda data, format="json": json.dumps(data) if format == "json" else str(data))
        .build())

    manager.register_skill(skill2)

    print(f"   Created: {skill2.name}")
    print(f"   Parameters: {[p.name for p in skill2.config.parameters]}")
    print()

    # 3. Execute Skill
    print("3. EXECUTE SKILL:")
    print("-" * 40)

    result = await manager.execute(skill1.skill_id, data=[1, 2, 3, 4, 5])

    print(f"   Skill: {skill1.name}")
    print(f"   Success: {result.success}")
    print(f"   Output: {result.output}")
    print(f"   Duration: {result.duration:.4f}s")
    print()

    # 4. Execute by Name
    print("4. EXECUTE BY NAME:")
    print("-" * 40)

    result = await manager.execute_by_name(
        "format_output",
        data={"key": "value"}
    )

    print(f"   Output: {result.output}")
    print()

    # 5. Search Skills
    print("5. SEARCH SKILLS:")
    print("-" * 40)

    found = manager.search_skills("data")

    print(f"   Query: 'data'")
    print(f"   Found: {len(found)} skills")
    for s in found:
        print(f"     - {s.name}")
    print()

    # 6. Get by Category
    print("6. GET BY CATEGORY:")
    print("-" * 40)

    analysis_skills = manager.get_by_category("analysis")

    print(f"   Category: analysis")
    print(f"   Skills: {len(analysis_skills)}")
    print()

    # 7. Skill Composition - Sequence
    print("7. COMPOSE SEQUENCE:")
    print("-" * 40)

    # Create helper skills
    async def step1(x: int = 0) -> int:
        return x + 1

    async def step2(**kwargs: Any) -> int:
        prev = kwargs.get("_previous_result", 0)
        return prev * 2

    s1 = manager.create_skill("step1", step1)
    s2 = manager.create_skill("step2", step2)

    seq_skill = manager.compose_sequence(
        "two_step_process",
        [s1.skill_id, s2.skill_id]
    )

    result = await manager.execute(seq_skill.skill_id, x=5)

    print(f"   Composed: {seq_skill.name}")
    print(f"   Result: {result.output}")  # (5+1)*2 = 12
    print()

    # 8. Skill Composition - Parallel
    print("8. COMPOSE PARALLEL:")
    print("-" * 40)

    async def task_a(value: int = 0) -> str:
        await asyncio.sleep(0.01)
        return f"A: {value}"

    async def task_b(value: int = 0) -> str:
        await asyncio.sleep(0.01)
        return f"B: {value}"

    ta = manager.create_skill("task_a", task_a)
    tb = manager.create_skill("task_b", task_b)

    par_skill = manager.compose_parallel(
        "parallel_tasks",
        [ta.skill_id, tb.skill_id]
    )

    result = await manager.execute(par_skill.skill_id, value=42)

    print(f"   Composed: {par_skill.name}")
    print(f"   Results: {result.output}")
    print()

    # 9. Conditional Skill
    print("9. CONDITIONAL SKILL:")
    print("-" * 40)

    async def path_a(x: int = 0) -> str:
        return f"Path A: {x * 2}"

    async def path_b(x: int = 0) -> str:
        return f"Path B: {x + 10}"

    pa = manager.create_skill("path_a", path_a)
    pb = manager.create_skill("path_b", path_b)

    cond_skill = manager.compose_conditional(
        "conditional_path",
        lambda kwargs: kwargs.get("x", 0) > 5,
        pa.skill_id,
        pb.skill_id
    )

    result1 = await manager.execute(cond_skill.skill_id, x=10)
    result2 = await manager.execute(cond_skill.skill_id, x=3)

    print(f"   x=10: {result1.output}")
    print(f"   x=3: {result2.output}")
    print()

    # 10. Proficiency Tracking
    print("10. PROFICIENCY TRACKING:")
    print("-" * 40)

    # Execute skill multiple times
    for _ in range(10):
        await manager.execute(skill1.skill_id, data=[1, 2, 3])

    prof = manager.get_proficiency(skill1.skill_id)

    if prof:
        print(f"   Skill: {skill1.name}")
        print(f"   Level: {prof.level.name}")
        print(f"   Executions: {prof.executions}")
        print(f"   Success rate: {prof.successes/prof.executions*100:.0f}%")
    print()

    # 11. Skill Statistics
    print("11. SKILL STATISTICS:")
    print("-" * 40)

    stats = manager.get_stats()

    print(f"   Total skills: {stats.total_skills}")
    print(f"   Available: {stats.available_skills}")
    print(f"   Total executions: {stats.total_executions}")
    print(f"   Success rate: {stats.success_rate*100:.0f}%")
    print(f"   Avg duration: {stats.avg_duration:.4f}s")
    print()

    # 12. Execution History
    print("12. EXECUTION HISTORY:")
    print("-" * 40)

    history = manager.get_execution_history(limit=5)

    print(f"   Recent executions:")
    for usage in history[-3:]:
        status = "✓" if usage.success else "✗"
        print(f"     {status} {usage.skill_id[:8]}... ({usage.duration:.4f}s)")
    print()

    # 13. List All Skills
    print("13. LIST ALL SKILLS:")
    print("-" * 40)

    all_skills = manager.list_skills()

    print(f"   Total: {len(all_skills)} skills")
    for skill in all_skills[:5]:
        print(f"     - {skill.name} ({skill.category.value})")
    if len(all_skills) > 5:
        print(f"     ... and {len(all_skills) - 5} more")
    print()

    # 14. Get Schema
    print("14. SKILL SCHEMA:")
    print("-" * 40)

    schema = skill2.get_schema()

    print(f"   Skill: {schema['name']}")
    print(f"   Parameters:")
    for name, info in schema['parameters'].items():
        req = "required" if info['required'] else "optional"
        print(f"     - {name}: {info['type']} ({req})")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Skill Manager Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())

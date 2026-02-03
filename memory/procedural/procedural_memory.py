"""
BAEL - Procedural Memory System
Stores and retrieves skills, procedures, and how-to knowledge.

Procedural memory captures:
- Step-by-step procedures
- Skills and abilities
- Automated behaviors
- Tool usage patterns
- Best practices and workflows
"""

import asyncio
import hashlib
import json
import logging
import os
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional

logger = logging.getLogger("BAEL.Memory.Procedural")


# =============================================================================
# ENUMS & DATA CLASSES
# =============================================================================

class ProcedureType(Enum):
    """Types of procedural knowledge."""
    SKILL = "skill"  # A learned ability
    PROCEDURE = "procedure"  # Step-by-step process
    WORKFLOW = "workflow"  # Multi-step coordinated action
    HABIT = "habit"  # Automated behavior
    TECHNIQUE = "technique"  # Method for achieving something
    PROTOCOL = "protocol"  # Formal procedure
    PATTERN = "pattern"  # Recognized solution pattern
    TOOL_USAGE = "tool_usage"  # How to use a specific tool


class ProficiencyLevel(Enum):
    """Proficiency levels for skills."""
    NOVICE = 1
    BEGINNER = 2
    COMPETENT = 3
    PROFICIENT = 4
    EXPERT = 5
    MASTER = 6


class StepStatus(Enum):
    """Status of a procedure step."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class ProcedureStep:
    """A single step in a procedure."""
    id: str
    order: int
    name: str
    description: str
    action: str  # The action to perform
    parameters: Dict[str, Any]
    expected_output: Optional[str] = None
    fallback: Optional[str] = None  # Alternative if step fails
    optional: bool = False
    timeout_seconds: float = 30.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "order": self.order,
            "name": self.name,
            "description": self.description,
            "action": self.action,
            "parameters": self.parameters,
            "expected_output": self.expected_output,
            "fallback": self.fallback,
            "optional": self.optional,
            "timeout_seconds": self.timeout_seconds
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProcedureStep":
        return cls(
            id=data["id"],
            order=data["order"],
            name=data["name"],
            description=data["description"],
            action=data["action"],
            parameters=data.get("parameters", {}),
            expected_output=data.get("expected_output"),
            fallback=data.get("fallback"),
            optional=data.get("optional", False),
            timeout_seconds=data.get("timeout_seconds", 30.0)
        )


@dataclass
class Procedure:
    """A procedural memory entry - a skill or procedure."""
    id: str
    name: str
    procedure_type: ProcedureType
    description: str
    domain: str
    steps: List[ProcedureStep]
    prerequisites: List[str]  # Other procedure IDs needed first
    proficiency: ProficiencyLevel
    success_count: int
    failure_count: int
    last_executed: Optional[datetime]
    average_duration: float  # In seconds
    context_requirements: Dict[str, Any]  # Required context to execute
    output_schema: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime
    tags: List[str] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "procedure_type": self.procedure_type.value,
            "description": self.description,
            "domain": self.domain,
            "steps": [s.to_dict() for s in self.steps],
            "prerequisites": self.prerequisites,
            "proficiency": self.proficiency.value,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "last_executed": self.last_executed.isoformat() if self.last_executed else None,
            "average_duration": self.average_duration,
            "context_requirements": self.context_requirements,
            "output_schema": self.output_schema,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "tags": self.tags,
            "notes": self.notes
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Procedure":
        return cls(
            id=data["id"],
            name=data["name"],
            procedure_type=ProcedureType(data["procedure_type"]),
            description=data["description"],
            domain=data.get("domain", "general"),
            steps=[ProcedureStep.from_dict(s) for s in data.get("steps", [])],
            prerequisites=data.get("prerequisites", []),
            proficiency=ProficiencyLevel(data.get("proficiency", 1)),
            success_count=data.get("success_count", 0),
            failure_count=data.get("failure_count", 0),
            last_executed=datetime.fromisoformat(data["last_executed"]) if data.get("last_executed") else None,
            average_duration=data.get("average_duration", 0),
            context_requirements=data.get("context_requirements", {}),
            output_schema=data.get("output_schema"),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else datetime.now(),
            tags=data.get("tags", []),
            notes=data.get("notes", "")
        )

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        total = self.success_count + self.failure_count
        if total == 0:
            return 0.0
        return self.success_count / total

    def should_practice(self) -> bool:
        """Determine if this skill needs practice."""
        if not self.last_executed:
            return True

        # Practice if success rate is low
        if self.success_rate < 0.7:
            return True

        # Practice if not used recently
        days_since = (datetime.now() - self.last_executed).days
        if days_since > 30:
            return True

        return False


@dataclass
class ExecutionResult:
    """Result of procedure execution."""
    procedure_id: str
    success: bool
    start_time: datetime
    end_time: datetime
    steps_completed: int
    total_steps: int
    output: Any
    error: Optional[str] = None
    step_results: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def duration(self) -> float:
        return (self.end_time - self.start_time).total_seconds()


# =============================================================================
# PROCEDURAL MEMORY STORE
# =============================================================================

class ProceduralMemoryStore:
    """
    Persistent storage for procedural memories.

    Stores skills, procedures, and workflows with:
    - Step definitions
    - Execution history
    - Proficiency tracking
    """

    def __init__(self, db_path: str = "memory/procedural/procedures.db"):
        self.db_path = db_path
        self._cache: Dict[str, Procedure] = {}
        self._cache_limit = 200
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the database."""
        if self._initialized:
            return

        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Procedures table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS procedures (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                procedure_type TEXT NOT NULL,
                description TEXT,
                domain TEXT,
                steps TEXT,
                prerequisites TEXT,
                proficiency INTEGER,
                success_count INTEGER DEFAULT 0,
                failure_count INTEGER DEFAULT 0,
                last_executed TEXT,
                average_duration REAL,
                context_requirements TEXT,
                output_schema TEXT,
                created_at TEXT,
                updated_at TEXT,
                tags TEXT,
                notes TEXT
            )
        """)

        # Execution history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS execution_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                procedure_id TEXT NOT NULL,
                success INTEGER,
                start_time TEXT,
                end_time TEXT,
                steps_completed INTEGER,
                output TEXT,
                error TEXT,
                step_results TEXT,
                FOREIGN KEY (procedure_id) REFERENCES procedures(id)
            )
        """)

        # Indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_procedure_name ON procedures(name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_procedure_type ON procedures(procedure_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_procedure_domain ON procedures(domain)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_history_procedure ON execution_history(procedure_id)")

        conn.commit()
        conn.close()

        self._initialized = True
        logger.info(f"Procedural memory store initialized at {self.db_path}")

    def _generate_id(self, name: str) -> str:
        """Generate unique procedure ID."""
        data = f"{name}{datetime.now().isoformat()}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]

    async def store(self, procedure: Procedure) -> str:
        """Store a procedure."""
        await self.initialize()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO procedures
            (id, name, procedure_type, description, domain, steps, prerequisites,
             proficiency, success_count, failure_count, last_executed,
             average_duration, context_requirements, output_schema,
             created_at, updated_at, tags, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            procedure.id,
            procedure.name,
            procedure.procedure_type.value,
            procedure.description,
            procedure.domain,
            json.dumps([s.to_dict() for s in procedure.steps]),
            json.dumps(procedure.prerequisites),
            procedure.proficiency.value,
            procedure.success_count,
            procedure.failure_count,
            procedure.last_executed.isoformat() if procedure.last_executed else None,
            procedure.average_duration,
            json.dumps(procedure.context_requirements),
            json.dumps(procedure.output_schema) if procedure.output_schema else None,
            procedure.created_at.isoformat(),
            procedure.updated_at.isoformat(),
            json.dumps(procedure.tags),
            procedure.notes
        ))

        conn.commit()
        conn.close()

        self._cache[procedure.id] = procedure
        self._trim_cache()

        logger.debug(f"Stored procedure: {procedure.name}")
        return procedure.id

    async def get(self, procedure_id: str) -> Optional[Procedure]:
        """Get a procedure by ID."""
        await self.initialize()

        if procedure_id in self._cache:
            return self._cache[procedure_id]

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM procedures WHERE id = ?", (procedure_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        procedure = self._row_to_procedure(row)
        self._cache[procedure_id] = procedure
        return procedure

    async def find_by_name(self, name: str) -> Optional[Procedure]:
        """Find a procedure by name."""
        await self.initialize()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM procedures WHERE name = ? COLLATE NOCASE",
            (name,)
        )
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return self._row_to_procedure(row)

    async def search(
        self,
        query: Optional[str] = None,
        procedure_type: Optional[ProcedureType] = None,
        domain: Optional[str] = None,
        min_proficiency: Optional[ProficiencyLevel] = None,
        limit: int = 20
    ) -> List[Procedure]:
        """Search procedures."""
        await self.initialize()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        sql = "SELECT * FROM procedures WHERE 1=1"
        params = []

        if procedure_type:
            sql += " AND procedure_type = ?"
            params.append(procedure_type.value)

        if domain:
            sql += " AND domain = ?"
            params.append(domain)

        if min_proficiency:
            sql += " AND proficiency >= ?"
            params.append(min_proficiency.value)

        sql += " ORDER BY success_count DESC LIMIT ?"
        params.append(limit * 2)

        cursor.execute(sql, params)
        rows = cursor.fetchall()
        conn.close()

        procedures = [self._row_to_procedure(row) for row in rows]

        if query:
            query_lower = query.lower()
            procedures = [p for p in procedures
                         if query_lower in p.name.lower()
                         or query_lower in p.description.lower()]

        return procedures[:limit]

    async def get_by_type(
        self,
        procedure_type: ProcedureType,
        limit: int = 20
    ) -> List[Procedure]:
        """Get procedures by type."""
        return await self.search(procedure_type=procedure_type, limit=limit)

    async def get_prerequisites(self, procedure_id: str) -> List[Procedure]:
        """Get all prerequisites for a procedure."""
        procedure = await self.get(procedure_id)
        if not procedure:
            return []

        prerequisites = []
        for prereq_id in procedure.prerequisites:
            prereq = await self.get(prereq_id)
            if prereq:
                prerequisites.append(prereq)

        return prerequisites

    async def record_execution(
        self,
        result: ExecutionResult
    ) -> None:
        """Record a procedure execution."""
        await self.initialize()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO execution_history
            (procedure_id, success, start_time, end_time, steps_completed, output, error, step_results)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            result.procedure_id,
            1 if result.success else 0,
            result.start_time.isoformat(),
            result.end_time.isoformat(),
            result.steps_completed,
            json.dumps(result.output) if result.output else None,
            result.error,
            json.dumps(result.step_results)
        ))

        conn.commit()
        conn.close()

        # Update procedure stats
        procedure = await self.get(result.procedure_id)
        if procedure:
            if result.success:
                procedure.success_count += 1
            else:
                procedure.failure_count += 1

            procedure.last_executed = datetime.now()

            # Update average duration
            if procedure.average_duration == 0:
                procedure.average_duration = result.duration
            else:
                procedure.average_duration = (
                    procedure.average_duration * 0.8 + result.duration * 0.2
                )

            procedure.updated_at = datetime.now()
            await self.store(procedure)

    async def get_execution_history(
        self,
        procedure_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get execution history for a procedure."""
        await self.initialize()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM execution_history
            WHERE procedure_id = ?
            ORDER BY start_time DESC LIMIT ?
        """, (procedure_id, limit))

        rows = cursor.fetchall()
        conn.close()

        return [
            {
                "id": row[0],
                "procedure_id": row[1],
                "success": bool(row[2]),
                "start_time": row[3],
                "end_time": row[4],
                "steps_completed": row[5],
                "output": json.loads(row[6]) if row[6] else None,
                "error": row[7],
                "step_results": json.loads(row[8]) if row[8] else []
            }
            for row in rows
        ]

    async def update_proficiency(
        self,
        procedure_id: str,
        new_level: ProficiencyLevel
    ) -> bool:
        """Update proficiency level."""
        procedure = await self.get(procedure_id)
        if not procedure:
            return False

        procedure.proficiency = new_level
        procedure.updated_at = datetime.now()
        await self.store(procedure)
        return True

    async def delete(self, procedure_id: str) -> bool:
        """Delete a procedure."""
        await self.initialize()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("DELETE FROM execution_history WHERE procedure_id = ?", (procedure_id,))
        cursor.execute("DELETE FROM procedures WHERE id = ?", (procedure_id,))

        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()

        if procedure_id in self._cache:
            del self._cache[procedure_id]

        return deleted

    def _row_to_procedure(self, row: tuple) -> Procedure:
        """Convert database row to Procedure."""
        steps_data = json.loads(row[5]) if row[5] else []
        steps = [ProcedureStep.from_dict(s) for s in steps_data]

        return Procedure(
            id=row[0],
            name=row[1],
            procedure_type=ProcedureType(row[2]),
            description=row[3] or "",
            domain=row[4] or "general",
            steps=steps,
            prerequisites=json.loads(row[6]) if row[6] else [],
            proficiency=ProficiencyLevel(row[7]) if row[7] else ProficiencyLevel.NOVICE,
            success_count=row[8] or 0,
            failure_count=row[9] or 0,
            last_executed=datetime.fromisoformat(row[10]) if row[10] else None,
            average_duration=row[11] or 0,
            context_requirements=json.loads(row[12]) if row[12] else {},
            output_schema=json.loads(row[13]) if row[13] else None,
            created_at=datetime.fromisoformat(row[14]) if row[14] else datetime.now(),
            updated_at=datetime.fromisoformat(row[15]) if row[15] else datetime.now(),
            tags=json.loads(row[16]) if row[16] else [],
            notes=row[17] or ""
        )

    def _trim_cache(self) -> None:
        """Trim cache to limit."""
        if len(self._cache) > self._cache_limit:
            sorted_items = sorted(
                self._cache.items(),
                key=lambda x: x[1].last_executed or datetime.min
            )
            for key, _ in sorted_items[:len(self._cache) - self._cache_limit]:
                del self._cache[key]

    async def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics."""
        await self.initialize()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM procedures")
        total = cursor.fetchone()[0]

        cursor.execute("""
            SELECT procedure_type, COUNT(*) FROM procedures GROUP BY procedure_type
        """)
        by_type = dict(cursor.fetchall())

        cursor.execute("SELECT AVG(success_count * 1.0 / (success_count + failure_count + 1)) FROM procedures")
        avg_success = cursor.fetchone()[0] or 0

        cursor.execute("SELECT COUNT(*) FROM execution_history")
        total_executions = cursor.fetchone()[0]

        conn.close()

        return {
            "total_procedures": total,
            "by_type": by_type,
            "average_success_rate": avg_success,
            "total_executions": total_executions,
            "cache_size": len(self._cache)
        }


# =============================================================================
# PROCEDURAL MEMORY MANAGER
# =============================================================================

class ProceduralMemoryManager:
    """
    High-level interface for procedural memory operations.

    Provides:
    - Skill/procedure creation
    - Procedure execution
    - Skill improvement tracking
    - Workflow orchestration
    """

    def __init__(self, store: Optional[ProceduralMemoryStore] = None):
        self.store = store or ProceduralMemoryStore()
        self._executors: Dict[str, Callable] = {}  # Custom action executors

    async def initialize(self) -> None:
        """Initialize the manager."""
        await self.store.initialize()

    def register_executor(
        self,
        action_name: str,
        executor: Callable[..., Awaitable[Any]]
    ) -> None:
        """Register an executor for an action type."""
        self._executors[action_name] = executor

    async def learn_skill(
        self,
        name: str,
        description: str,
        steps: List[Dict[str, Any]],
        domain: str = "general",
        prerequisites: Optional[List[str]] = None
    ) -> str:
        """Learn a new skill."""
        procedure_id = self.store._generate_id(name)

        proc_steps = []
        for i, step in enumerate(steps):
            step_id = f"{procedure_id}_step_{i}"
            proc_steps.append(ProcedureStep(
                id=step_id,
                order=i,
                name=step.get("name", f"Step {i+1}"),
                description=step.get("description", ""),
                action=step.get("action", ""),
                parameters=step.get("parameters", {}),
                expected_output=step.get("expected_output"),
                fallback=step.get("fallback"),
                optional=step.get("optional", False)
            ))

        procedure = Procedure(
            id=procedure_id,
            name=name,
            procedure_type=ProcedureType.SKILL,
            description=description,
            domain=domain,
            steps=proc_steps,
            prerequisites=prerequisites or [],
            proficiency=ProficiencyLevel.NOVICE,
            success_count=0,
            failure_count=0,
            last_executed=None,
            average_duration=0,
            context_requirements={},
            output_schema=None,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

        return await self.store.store(procedure)

    async def learn_procedure(
        self,
        name: str,
        description: str,
        steps: List[Dict[str, Any]],
        domain: str = "general"
    ) -> str:
        """Learn a formal procedure."""
        procedure_id = self.store._generate_id(name)

        proc_steps = []
        for i, step in enumerate(steps):
            step_id = f"{procedure_id}_step_{i}"
            proc_steps.append(ProcedureStep(
                id=step_id,
                order=i,
                name=step.get("name", f"Step {i+1}"),
                description=step.get("description", ""),
                action=step.get("action", ""),
                parameters=step.get("parameters", {}),
                expected_output=step.get("expected_output"),
                optional=step.get("optional", False)
            ))

        procedure = Procedure(
            id=procedure_id,
            name=name,
            procedure_type=ProcedureType.PROCEDURE,
            description=description,
            domain=domain,
            steps=proc_steps,
            prerequisites=[],
            proficiency=ProficiencyLevel.COMPETENT,
            success_count=0,
            failure_count=0,
            last_executed=None,
            average_duration=0,
            context_requirements={},
            output_schema=None,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

        return await self.store.store(procedure)

    async def learn_tool_usage(
        self,
        tool_name: str,
        description: str,
        parameters: Dict[str, Any],
        example_usage: str
    ) -> str:
        """Learn how to use a tool."""
        procedure_id = self.store._generate_id(f"use_{tool_name}")

        steps = [
            ProcedureStep(
                id=f"{procedure_id}_step_0",
                order=0,
                name="Invoke Tool",
                description=description,
                action=f"tool:{tool_name}",
                parameters=parameters,
                expected_output=example_usage
            )
        ]

        procedure = Procedure(
            id=procedure_id,
            name=f"Use {tool_name}",
            procedure_type=ProcedureType.TOOL_USAGE,
            description=description,
            domain="tools",
            steps=steps,
            prerequisites=[],
            proficiency=ProficiencyLevel.COMPETENT,
            success_count=0,
            failure_count=0,
            last_executed=None,
            average_duration=0,
            context_requirements={},
            output_schema=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            notes=example_usage
        )

        return await self.store.store(procedure)

    async def execute(
        self,
        procedure_name: str,
        context: Optional[Dict[str, Any]] = None
    ) -> ExecutionResult:
        """Execute a procedure."""
        procedure = await self.store.find_by_name(procedure_name)
        if not procedure:
            return ExecutionResult(
                procedure_id="unknown",
                success=False,
                start_time=datetime.now(),
                end_time=datetime.now(),
                steps_completed=0,
                total_steps=0,
                output=None,
                error=f"Procedure not found: {procedure_name}"
            )

        start_time = datetime.now()
        step_results = []
        output = None
        error = None
        steps_completed = 0

        try:
            for step in procedure.steps:
                step_start = datetime.now()

                # Execute the step
                try:
                    step_output = await self._execute_step(step, context)
                    step_results.append({
                        "step_id": step.id,
                        "status": StepStatus.COMPLETED.value,
                        "output": step_output,
                        "duration": (datetime.now() - step_start).total_seconds()
                    })
                    steps_completed += 1
                    output = step_output

                except Exception as e:
                    if step.optional:
                        step_results.append({
                            "step_id": step.id,
                            "status": StepStatus.SKIPPED.value,
                            "error": str(e)
                        })
                    elif step.fallback:
                        # Try fallback
                        step_results.append({
                            "step_id": step.id,
                            "status": StepStatus.FAILED.value,
                            "error": str(e),
                            "fallback_attempted": True
                        })
                    else:
                        raise

            success = True

        except Exception as e:
            success = False
            error = str(e)

        end_time = datetime.now()

        result = ExecutionResult(
            procedure_id=procedure.id,
            success=success,
            start_time=start_time,
            end_time=end_time,
            steps_completed=steps_completed,
            total_steps=len(procedure.steps),
            output=output,
            error=error,
            step_results=step_results
        )

        # Record execution
        await self.store.record_execution(result)

        # Update proficiency if appropriate
        await self._update_proficiency(procedure)

        return result

    async def _execute_step(
        self,
        step: ProcedureStep,
        context: Optional[Dict[str, Any]]
    ) -> Any:
        """Execute a single step."""
        # Check for registered executor
        if step.action in self._executors:
            return await self._executors[step.action](
                **step.parameters,
                context=context
            )

        # Tool invocation
        if step.action.startswith("tool:"):
            tool_name = step.action[5:]
            logger.info(f"Would invoke tool: {tool_name}")
            return {"tool": tool_name, "params": step.parameters}

        # Default: return parameters as output
        return step.parameters

    async def _update_proficiency(self, procedure: Procedure) -> None:
        """Update proficiency based on execution history."""
        history = await self.store.get_execution_history(procedure.id, limit=10)

        if len(history) < 5:
            return

        # Calculate recent success rate
        successes = sum(1 for h in history if h["success"])
        success_rate = successes / len(history)

        current = procedure.proficiency.value

        if success_rate >= 0.9 and current < 6:
            new_level = ProficiencyLevel(min(6, current + 1))
            await self.store.update_proficiency(procedure.id, new_level)
        elif success_rate < 0.5 and current > 1:
            new_level = ProficiencyLevel(max(1, current - 1))
            await self.store.update_proficiency(procedure.id, new_level)

    async def get_skill(self, name: str) -> Optional[Procedure]:
        """Get a skill by name."""
        return await self.store.find_by_name(name)

    async def list_skills(
        self,
        domain: Optional[str] = None,
        min_proficiency: Optional[ProficiencyLevel] = None
    ) -> List[Procedure]:
        """List available skills."""
        return await self.store.search(
            procedure_type=ProcedureType.SKILL,
            domain=domain,
            min_proficiency=min_proficiency
        )

    async def get_how_to(self, task: str) -> Optional[str]:
        """Get instructions for how to do something."""
        procedures = await self.store.search(query=task, limit=5)

        if not procedures:
            return None

        best = procedures[0]

        instructions = [f"How to: {best.name}\n", best.description, "\nSteps:"]

        for step in best.steps:
            instructions.append(f"{step.order + 1}. {step.name}: {step.description}")

        return "\n".join(instructions)

    async def needs_practice(self) -> List[Procedure]:
        """Get skills that need practice."""
        all_skills = await self.store.get_by_type(ProcedureType.SKILL, limit=100)
        return [s for s in all_skills if s.should_practice()]


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "ProcedureType",
    "ProficiencyLevel",
    "StepStatus",
    "ProcedureStep",
    "Procedure",
    "ExecutionResult",
    "ProceduralMemoryStore",
    "ProceduralMemoryManager"
]

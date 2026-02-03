"""
BAEL - Mission Manager
Manages long-running autonomous missions that can span days or weeks.

Key differentiator: Unlike AutoGPT, missions persist with full state recovery.
"""

import asyncio
import json
import logging
import pickle
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set
import threading

logger = logging.getLogger("BAEL.Missions")


class MissionStatus(Enum):
    """Mission lifecycle status."""
    DRAFT = "draft"
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MissionPhase(Enum):
    """Standard mission phases."""
    INITIALIZATION = "initialization"
    PLANNING = "planning"
    RESEARCH = "research"
    EXECUTION = "execution"
    REVIEW = "review"
    DELIVERY = "delivery"
    COMPLETED = "completed"


class MissionPriority(Enum):
    """Mission priority levels."""
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4
    BACKGROUND = 5


@dataclass
class MissionGoal:
    """A specific goal within a mission."""
    goal_id: str
    description: str
    success_criteria: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)  # other goal IDs
    status: str = "pending"
    progress: float = 0.0
    result: Optional[Any] = None
    completed_at: Optional[datetime] = None


@dataclass
class MissionCheckpoint:
    """Checkpoint for mission state recovery."""
    checkpoint_id: str
    mission_id: str
    timestamp: datetime
    phase: MissionPhase
    progress: float
    state_snapshot: Dict[str, Any]
    notes: str = ""


@dataclass
class MissionEvent:
    """Event log entry for mission."""
    event_id: str
    timestamp: datetime
    event_type: str  # "start", "pause", "resume", "checkpoint", "error", "complete"
    description: str
    data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Mission:
    """A long-running autonomous mission."""
    mission_id: str
    name: str
    description: str
    created_at: datetime
    
    # Goals
    primary_goal: MissionGoal
    sub_goals: List[MissionGoal] = field(default_factory=list)
    
    # Status
    status: MissionStatus = MissionStatus.DRAFT
    phase: MissionPhase = MissionPhase.INITIALIZATION
    progress: float = 0.0
    
    # Assignment
    assigned_agent_id: Optional[str] = None
    assigned_at: Optional[datetime] = None
    
    # Execution
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    total_runtime_seconds: float = 0.0
    
    # Constraints
    priority: MissionPriority = MissionPriority.MEDIUM
    deadline: Optional[datetime] = None
    max_runtime_hours: Optional[float] = None
    max_cost_usd: Optional[float] = None
    
    # Resources
    allocated_resources: Dict[str, Any] = field(default_factory=dict)
    consumed_resources: Dict[str, Any] = field(default_factory=dict)
    
    # State
    working_memory: Dict[str, Any] = field(default_factory=dict)
    artifacts: List[str] = field(default_factory=list)
    
    # History
    checkpoints: List[str] = field(default_factory=list)  # checkpoint IDs
    events: List[MissionEvent] = field(default_factory=list)
    
    # Results
    outputs: Dict[str, Any] = field(default_factory=dict)
    final_report: Optional[str] = None
    success: Optional[bool] = None
    failure_reason: Optional[str] = None
    
    def add_event(self, event_type: str, description: str, data: Dict[str, Any] = None):
        """Add an event to the mission log."""
        import uuid
        event = MissionEvent(
            event_id=f"evt_{uuid.uuid4().hex[:8]}",
            timestamp=datetime.utcnow(),
            event_type=event_type,
            description=description,
            data=data or {}
        )
        self.events.append(event)
        return event
    
    def calculate_progress(self) -> float:
        """Calculate overall mission progress from goals."""
        if not self.sub_goals:
            return self.primary_goal.progress
        
        total_weight = len(self.sub_goals) + 1  # primary + sub goals
        total_progress = self.primary_goal.progress
        
        for goal in self.sub_goals:
            total_progress += goal.progress
        
        return total_progress / total_weight


class MissionManager:
    """
    Manages autonomous long-running missions.
    
    Features:
    - Persistent mission state across system restarts
    - Automatic checkpointing and recovery
    - Progress tracking and reporting
    - Resource management
    - Multi-mission orchestration
    - Priority-based scheduling
    """
    
    def __init__(
        self,
        storage_path: str = "./data/missions",
        checkpoint_interval_minutes: int = 10,
        max_concurrent_missions: int = 5
    ):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.checkpoint_interval = timedelta(minutes=checkpoint_interval_minutes)
        self.max_concurrent = max_concurrent_missions
        
        # State
        self._missions: Dict[str, Mission] = {}
        self._checkpoints: Dict[str, MissionCheckpoint] = {}
        self._running_missions: Set[str] = set()
        
        # Callbacks
        self._on_mission_complete: List[Callable] = []
        self._on_mission_failed: List[Callable] = []
        self._on_checkpoint: List[Callable] = []
        
        # Database
        self._db_path = self.storage_path / "missions.db"
        self._init_database()
        
        # Background tasks
        self._checkpoint_task: Optional[asyncio.Task] = None
        self._scheduler_task: Optional[asyncio.Task] = None
        self._running = False
        
        logger.info(f"MissionManager initialized at {self.storage_path}")
    
    def _init_database(self):
        """Initialize SQLite database."""
        conn = sqlite3.connect(str(self._db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS missions (
                mission_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                status TEXT DEFAULT 'draft',
                phase TEXT DEFAULT 'initialization',
                progress REAL DEFAULT 0.0,
                priority INTEGER DEFAULT 3,
                assigned_agent_id TEXT,
                data BLOB NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS checkpoints (
                checkpoint_id TEXT PRIMARY KEY,
                mission_id TEXT NOT NULL,
                phase TEXT,
                progress REAL,
                data BLOB NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (mission_id) REFERENCES missions(mission_id)
            )
        """)
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_missions_status ON missions(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_missions_priority ON missions(priority)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_checkpoints_mission ON checkpoints(mission_id)")
        
        conn.commit()
        conn.close()
    
    async def start(self):
        """Start the mission manager."""
        self._running = True
        
        # Load active missions
        await self._load_active_missions()
        
        # Start background tasks
        self._checkpoint_task = asyncio.create_task(self._checkpoint_loop())
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())
        
        logger.info("MissionManager started")
    
    async def stop(self):
        """Stop the mission manager gracefully."""
        self._running = False
        
        # Checkpoint all running missions
        for mission_id in list(self._running_missions):
            await self.pause_mission(mission_id, reason="system_shutdown")
        
        # Cancel background tasks
        for task in [self._checkpoint_task, self._scheduler_task]:
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        logger.info("MissionManager stopped")
    
    async def _checkpoint_loop(self):
        """Background loop for automatic checkpointing."""
        while self._running:
            try:
                for mission_id in list(self._running_missions):
                    await self.checkpoint_mission(mission_id)
                await asyncio.sleep(self.checkpoint_interval.total_seconds())
            except Exception as e:
                logger.error(f"Checkpoint loop error: {e}")
                await asyncio.sleep(60)
    
    async def _scheduler_loop(self):
        """Background loop for mission scheduling."""
        while self._running:
            try:
                await self._schedule_pending_missions()
                await asyncio.sleep(30)
            except Exception as e:
                logger.error(f"Scheduler loop error: {e}")
                await asyncio.sleep(60)
    
    async def _schedule_pending_missions(self):
        """Schedule pending missions based on priority and capacity."""
        if len(self._running_missions) >= self.max_concurrent:
            return
        
        # Get pending missions sorted by priority
        pending = [
            m for m in self._missions.values()
            if m.status == MissionStatus.PENDING and m.assigned_agent_id
        ]
        pending.sort(key=lambda m: m.priority.value)
        
        for mission in pending:
            if len(self._running_missions) >= self.max_concurrent:
                break
            await self.start_mission(mission.mission_id)
    
    async def _load_active_missions(self):
        """Load all active missions from database."""
        conn = sqlite3.connect(str(self._db_path))
        cursor = conn.cursor()
        cursor.execute(
            "SELECT data FROM missions WHERE status IN ('pending', 'running', 'paused', 'blocked')"
        )
        rows = cursor.fetchall()
        conn.close()
        
        for row in rows:
            mission = pickle.loads(row[0])
            self._missions[mission.mission_id] = mission
        
        logger.info(f"Loaded {len(self._missions)} active missions")
    
    # Mission Lifecycle
    
    async def create_mission(
        self,
        name: str,
        primary_goal: str,
        description: str = None,
        sub_goals: List[str] = None,
        priority: MissionPriority = MissionPriority.MEDIUM,
        deadline: datetime = None,
        max_runtime_hours: float = None,
        max_cost_usd: float = None
    ) -> Mission:
        """Create a new mission."""
        import uuid
        
        mission_id = f"mission_{uuid.uuid4().hex[:12]}"
        
        # Create primary goal
        primary = MissionGoal(
            goal_id=f"goal_{uuid.uuid4().hex[:8]}",
            description=primary_goal,
            success_criteria=[]
        )
        
        # Create sub goals
        subs = []
        for i, goal_desc in enumerate(sub_goals or []):
            subs.append(MissionGoal(
                goal_id=f"goal_{uuid.uuid4().hex[:8]}",
                description=goal_desc
            ))
        
        mission = Mission(
            mission_id=mission_id,
            name=name,
            description=description or "",
            created_at=datetime.utcnow(),
            primary_goal=primary,
            sub_goals=subs,
            priority=priority,
            deadline=deadline,
            max_runtime_hours=max_runtime_hours,
            max_cost_usd=max_cost_usd
        )
        
        mission.add_event("created", f"Mission '{name}' created")
        
        self._missions[mission_id] = mission
        await self._save_mission(mission)
        
        logger.info(f"Created mission: {mission_id} - {name}")
        return mission
    
    async def assign_mission(
        self,
        mission_id: str,
        agent_id: str
    ) -> Mission:
        """Assign a mission to an agent."""
        if mission_id not in self._missions:
            raise ValueError(f"Mission {mission_id} not found")
        
        mission = self._missions[mission_id]
        mission.assigned_agent_id = agent_id
        mission.assigned_at = datetime.utcnow()
        mission.status = MissionStatus.PENDING
        
        mission.add_event("assigned", f"Assigned to agent {agent_id}")
        
        await self._save_mission(mission)
        
        logger.info(f"Assigned mission {mission_id} to agent {agent_id}")
        return mission
    
    async def start_mission(self, mission_id: str) -> Mission:
        """Start executing a mission."""
        if mission_id not in self._missions:
            raise ValueError(f"Mission {mission_id} not found")
        
        mission = self._missions[mission_id]
        
        if not mission.assigned_agent_id:
            raise ValueError(f"Mission {mission_id} has no assigned agent")
        
        mission.status = MissionStatus.RUNNING
        mission.started_at = datetime.utcnow()
        mission.phase = MissionPhase.PLANNING
        
        mission.add_event("started", "Mission execution started")
        
        self._running_missions.add(mission_id)
        await self._save_mission(mission)
        
        logger.info(f"Started mission: {mission_id}")
        return mission
    
    async def pause_mission(
        self,
        mission_id: str,
        reason: str = "user_request"
    ) -> Mission:
        """Pause a running mission."""
        if mission_id not in self._missions:
            raise ValueError(f"Mission {mission_id} not found")
        
        mission = self._missions[mission_id]
        
        if mission.status != MissionStatus.RUNNING:
            logger.warning(f"Mission {mission_id} is not running")
            return mission
        
        # Checkpoint before pausing
        await self.checkpoint_mission(mission_id)
        
        mission.status = MissionStatus.PAUSED
        mission.add_event("paused", f"Mission paused: {reason}", {"reason": reason})
        
        self._running_missions.discard(mission_id)
        await self._save_mission(mission)
        
        logger.info(f"Paused mission: {mission_id}")
        return mission
    
    async def resume_mission(self, mission_id: str) -> Mission:
        """Resume a paused mission."""
        if mission_id not in self._missions:
            raise ValueError(f"Mission {mission_id} not found")
        
        mission = self._missions[mission_id]
        
        if mission.status != MissionStatus.PAUSED:
            raise ValueError(f"Mission {mission_id} is not paused")
        
        mission.status = MissionStatus.RUNNING
        mission.add_event("resumed", "Mission resumed")
        
        self._running_missions.add(mission_id)
        await self._save_mission(mission)
        
        logger.info(f"Resumed mission: {mission_id}")
        return mission
    
    async def complete_mission(
        self,
        mission_id: str,
        outputs: Dict[str, Any] = None,
        report: str = None,
        success: bool = True
    ) -> Mission:
        """Mark a mission as completed."""
        if mission_id not in self._missions:
            raise ValueError(f"Mission {mission_id} not found")
        
        mission = self._missions[mission_id]
        
        mission.status = MissionStatus.COMPLETED
        mission.phase = MissionPhase.COMPLETED
        mission.progress = 100.0
        mission.completed_at = datetime.utcnow()
        mission.outputs = outputs or {}
        mission.final_report = report
        mission.success = success
        mission.primary_goal.status = "completed"
        mission.primary_goal.progress = 100.0
        
        mission.add_event("completed", "Mission completed successfully", {"success": success})
        
        self._running_missions.discard(mission_id)
        await self._save_mission(mission)
        
        # Trigger callbacks
        for callback in self._on_mission_complete:
            try:
                await callback(mission)
            except Exception as e:
                logger.error(f"Completion callback error: {e}")
        
        logger.info(f"Completed mission: {mission_id}")
        return mission
    
    async def fail_mission(
        self,
        mission_id: str,
        reason: str,
        error_data: Dict[str, Any] = None
    ) -> Mission:
        """Mark a mission as failed."""
        if mission_id not in self._missions:
            raise ValueError(f"Mission {mission_id} not found")
        
        mission = self._missions[mission_id]
        
        mission.status = MissionStatus.FAILED
        mission.completed_at = datetime.utcnow()
        mission.success = False
        mission.failure_reason = reason
        
        mission.add_event("failed", f"Mission failed: {reason}", error_data or {})
        
        self._running_missions.discard(mission_id)
        await self._save_mission(mission)
        
        # Trigger callbacks
        for callback in self._on_mission_failed:
            try:
                await callback(mission, reason)
            except Exception as e:
                logger.error(f"Failure callback error: {e}")
        
        logger.error(f"Mission failed: {mission_id} - {reason}")
        return mission
    
    # Progress Updates
    
    async def update_progress(
        self,
        mission_id: str,
        progress: float = None,
        phase: MissionPhase = None,
        goal_id: str = None,
        goal_progress: float = None,
        working_memory: Dict[str, Any] = None,
        artifacts: List[str] = None
    ) -> Mission:
        """Update mission progress."""
        if mission_id not in self._missions:
            raise ValueError(f"Mission {mission_id} not found")
        
        mission = self._missions[mission_id]
        
        if progress is not None:
            mission.progress = min(100.0, max(0.0, progress))
        
        if phase is not None:
            mission.phase = phase
            mission.add_event("phase_change", f"Entered phase: {phase.value}")
        
        if goal_id and goal_progress is not None:
            # Update specific goal
            all_goals = [mission.primary_goal] + mission.sub_goals
            for goal in all_goals:
                if goal.goal_id == goal_id:
                    goal.progress = min(100.0, max(0.0, goal_progress))
                    if goal_progress >= 100.0:
                        goal.status = "completed"
                        goal.completed_at = datetime.utcnow()
                    break
            
            # Recalculate overall progress
            mission.progress = mission.calculate_progress()
        
        if working_memory:
            mission.working_memory.update(working_memory)
        
        if artifacts:
            mission.artifacts.extend(artifacts)
        
        await self._save_mission(mission)
        return mission
    
    # Checkpointing
    
    async def checkpoint_mission(self, mission_id: str) -> MissionCheckpoint:
        """Create a checkpoint for a mission."""
        if mission_id not in self._missions:
            raise ValueError(f"Mission {mission_id} not found")
        
        import uuid
        mission = self._missions[mission_id]
        
        checkpoint = MissionCheckpoint(
            checkpoint_id=f"ckpt_{uuid.uuid4().hex[:8]}",
            mission_id=mission_id,
            timestamp=datetime.utcnow(),
            phase=mission.phase,
            progress=mission.progress,
            state_snapshot={
                "working_memory": mission.working_memory.copy(),
                "artifacts": mission.artifacts.copy(),
                "goal_states": {
                    g.goal_id: {"status": g.status, "progress": g.progress}
                    for g in [mission.primary_goal] + mission.sub_goals
                }
            }
        )
        
        self._checkpoints[checkpoint.checkpoint_id] = checkpoint
        mission.checkpoints.append(checkpoint.checkpoint_id)
        mission.add_event("checkpoint", f"Checkpoint created: {checkpoint.checkpoint_id}")
        
        await self._save_checkpoint(checkpoint)
        await self._save_mission(mission)
        
        # Trigger callbacks
        for callback in self._on_checkpoint:
            try:
                await callback(mission, checkpoint)
            except Exception as e:
                logger.error(f"Checkpoint callback error: {e}")
        
        return checkpoint
    
    async def restore_from_checkpoint(
        self,
        mission_id: str,
        checkpoint_id: str = None
    ) -> Mission:
        """Restore a mission from a checkpoint."""
        if mission_id not in self._missions:
            # Try to load from database
            await self._load_mission(mission_id)
        
        mission = self._missions[mission_id]
        
        # Get checkpoint
        if checkpoint_id:
            checkpoint = await self._load_checkpoint(checkpoint_id)
        else:
            # Get latest checkpoint
            if not mission.checkpoints:
                raise ValueError(f"No checkpoints for mission {mission_id}")
            checkpoint = await self._load_checkpoint(mission.checkpoints[-1])
        
        # Restore state
        mission.phase = checkpoint.phase
        mission.progress = checkpoint.progress
        mission.working_memory = checkpoint.state_snapshot.get("working_memory", {})
        mission.artifacts = checkpoint.state_snapshot.get("artifacts", [])
        
        # Restore goal states
        goal_states = checkpoint.state_snapshot.get("goal_states", {})
        for goal in [mission.primary_goal] + mission.sub_goals:
            if goal.goal_id in goal_states:
                goal.status = goal_states[goal.goal_id]["status"]
                goal.progress = goal_states[goal.goal_id]["progress"]
        
        mission.add_event("restored", f"Restored from checkpoint {checkpoint_id}")
        
        await self._save_mission(mission)
        
        logger.info(f"Restored mission {mission_id} from checkpoint {checkpoint.checkpoint_id}")
        return mission
    
    # Persistence
    
    async def _save_mission(self, mission: Mission):
        """Save mission to database."""
        data = pickle.dumps(mission)
        
        conn = sqlite3.connect(str(self._db_path))
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO missions 
            (mission_id, name, status, phase, progress, priority, assigned_agent_id, data, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (
            mission.mission_id,
            mission.name,
            mission.status.value,
            mission.phase.value,
            mission.progress,
            mission.priority.value,
            mission.assigned_agent_id,
            data
        ))
        conn.commit()
        conn.close()
    
    async def _load_mission(self, mission_id: str) -> Mission:
        """Load mission from database."""
        conn = sqlite3.connect(str(self._db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT data FROM missions WHERE mission_id = ?", (mission_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            raise ValueError(f"Mission {mission_id} not found")
        
        mission = pickle.loads(row[0])
        self._missions[mission_id] = mission
        return mission
    
    async def _save_checkpoint(self, checkpoint: MissionCheckpoint):
        """Save checkpoint to database."""
        data = pickle.dumps(checkpoint)
        
        conn = sqlite3.connect(str(self._db_path))
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO checkpoints (checkpoint_id, mission_id, phase, progress, data)
            VALUES (?, ?, ?, ?, ?)
        """, (
            checkpoint.checkpoint_id,
            checkpoint.mission_id,
            checkpoint.phase.value,
            checkpoint.progress,
            data
        ))
        conn.commit()
        conn.close()
    
    async def _load_checkpoint(self, checkpoint_id: str) -> MissionCheckpoint:
        """Load checkpoint from database."""
        if checkpoint_id in self._checkpoints:
            return self._checkpoints[checkpoint_id]
        
        conn = sqlite3.connect(str(self._db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT data FROM checkpoints WHERE checkpoint_id = ?", (checkpoint_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            raise ValueError(f"Checkpoint {checkpoint_id} not found")
        
        checkpoint = pickle.loads(row[0])
        self._checkpoints[checkpoint_id] = checkpoint
        return checkpoint
    
    # Queries
    
    async def list_missions(
        self,
        status: MissionStatus = None,
        agent_id: str = None,
        limit: int = 100
    ) -> List[Mission]:
        """List missions with optional filters."""
        missions = list(self._missions.values())
        
        if status:
            missions = [m for m in missions if m.status == status]
        
        if agent_id:
            missions = [m for m in missions if m.assigned_agent_id == agent_id]
        
        # Sort by priority and creation date
        missions.sort(key=lambda m: (m.priority.value, m.created_at))
        
        return missions[:limit]
    
    def get_mission(self, mission_id: str) -> Optional[Mission]:
        """Get a mission by ID."""
        return self._missions.get(mission_id)
    
    def get_running_count(self) -> int:
        """Get count of running missions."""
        return len(self._running_missions)
    
    # Callbacks
    
    def on_complete(self, callback: Callable):
        """Register callback for mission completion."""
        self._on_mission_complete.append(callback)
    
    def on_failed(self, callback: Callable):
        """Register callback for mission failure."""
        self._on_mission_failed.append(callback)
    
    def on_checkpoint(self, callback: Callable):
        """Register callback for checkpoint creation."""
        self._on_checkpoint.append(callback)


# Singleton
_mission_manager: Optional[MissionManager] = None


def get_mission_manager() -> MissionManager:
    """Get the global mission manager instance."""
    global _mission_manager
    if _mission_manager is None:
        _mission_manager = MissionManager()
    return _mission_manager


async def main():
    """Example usage."""
    manager = get_mission_manager()
    await manager.start()
    
    # Create a mission
    mission = await manager.create_mission(
        name="Build AI Framework",
        primary_goal="Create the most advanced AI agent framework",
        sub_goals=[
            "Implement core architecture",
            "Build memory system",
            "Add tool integration",
            "Create UI"
        ],
        priority=MissionPriority.HIGH,
        max_runtime_hours=168  # 1 week
    )
    print(f"Created mission: {mission.mission_id}")
    
    # Assign to agent
    await manager.assign_mission(mission.mission_id, "agent_001")
    
    # Start mission
    await manager.start_mission(mission.mission_id)
    
    # Update progress
    await manager.update_progress(
        mission.mission_id,
        progress=25.0,
        phase=MissionPhase.EXECUTION,
        working_memory={"current_step": "building_core"}
    )
    
    # Create checkpoint
    checkpoint = await manager.checkpoint_mission(mission.mission_id)
    print(f"Created checkpoint: {checkpoint.checkpoint_id}")
    
    # Pause mission
    await manager.pause_mission(mission.mission_id, "demonstration")
    
    # Resume
    await manager.resume_mission(mission.mission_id)
    
    # Complete
    await manager.complete_mission(
        mission.mission_id,
        outputs={"framework_version": "1.0.0"},
        report="Successfully built the AI framework",
        success=True
    )
    
    await manager.stop()


if __name__ == "__main__":
    asyncio.run(main())

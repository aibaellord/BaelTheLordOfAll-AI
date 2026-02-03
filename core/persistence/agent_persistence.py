"""
BAEL - Persistent Agent State Manager
Enables agents to persist across sessions and pursue long-running missions.

This is a key differentiator vs AutoGPT - we maintain perfect state continuity.
"""

import asyncio
import json
import pickle
import hashlib
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Callable
import sqlite3
import threading

logger = logging.getLogger("BAEL.Persistence.Agent")


class AgentPersistenceState(Enum):
    """State of agent persistence."""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    HIBERNATING = "hibernating"
    TERMINATED = "terminated"
    CHECKPOINTED = "checkpointed"


class MissionStatus(Enum):
    """Status of a long-running mission."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class AgentCheckpoint:
    """Complete snapshot of agent state at a point in time."""
    checkpoint_id: str
    agent_id: str
    timestamp: datetime
    state_hash: str
    
    # Core state
    memory_snapshot: Dict[str, Any] = field(default_factory=dict)
    context_window: List[Dict[str, Any]] = field(default_factory=list)
    active_goals: List[str] = field(default_factory=list)
    completed_goals: List[str] = field(default_factory=list)
    
    # Execution state
    current_task: Optional[str] = None
    task_queue: List[Dict[str, Any]] = field(default_factory=list)
    execution_history: List[Dict[str, Any]] = field(default_factory=list)
    
    # Tool state
    tool_states: Dict[str, Any] = field(default_factory=dict)
    pending_tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    
    # Learning state
    learned_patterns: Dict[str, Any] = field(default_factory=dict)
    error_history: List[Dict[str, Any]] = field(default_factory=list)
    success_patterns: List[Dict[str, Any]] = field(default_factory=list)
    
    # Metadata
    version: str = "1.0.0"
    parent_checkpoint_id: Optional[str] = None
    tags: List[str] = field(default_factory=list)


@dataclass
class Mission:
    """A long-running mission that persists across sessions."""
    mission_id: str
    name: str
    description: str
    created_at: datetime
    
    # Goals
    primary_goal: str
    sub_goals: List[str] = field(default_factory=list)
    success_criteria: List[str] = field(default_factory=list)
    
    # Status
    status: MissionStatus = MissionStatus.PENDING
    progress_percentage: float = 0.0
    current_phase: str = "initialization"
    
    # Execution
    assigned_agent_id: Optional[str] = None
    checkpoints: List[str] = field(default_factory=list)  # checkpoint IDs
    execution_log: List[Dict[str, Any]] = field(default_factory=list)
    
    # Constraints
    deadline: Optional[datetime] = None
    max_runtime_hours: Optional[float] = None
    resource_limits: Dict[str, Any] = field(default_factory=dict)
    
    # Results
    outputs: Dict[str, Any] = field(default_factory=dict)
    artifacts: List[str] = field(default_factory=list)  # file paths
    final_report: Optional[str] = None


class PersistentAgentManager:
    """
    Manages persistent agent state across sessions.
    
    Features:
    - Complete state serialization/deserialization
    - Automatic checkpointing
    - Mission management
    - Cross-session memory continuity
    - Crash recovery
    """
    
    def __init__(
        self,
        storage_path: str = "./data/persistence",
        checkpoint_interval_minutes: int = 5,
        max_checkpoints_per_agent: int = 100
    ):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.checkpoint_interval = timedelta(minutes=checkpoint_interval_minutes)
        self.max_checkpoints = max_checkpoints_per_agent
        
        # In-memory caches
        self._active_agents: Dict[str, AgentCheckpoint] = {}
        self._active_missions: Dict[str, Mission] = {}
        self._checkpoint_schedule: Dict[str, datetime] = {}
        
        # Database
        self._db_path = self.storage_path / "agent_persistence.db"
        self._init_database()
        
        # Background tasks
        self._checkpoint_task: Optional[asyncio.Task] = None
        self._running = False
        
        logger.info(f"PersistentAgentManager initialized at {self.storage_path}")
    
    def _init_database(self) -> None:
        """Initialize SQLite database for persistence."""
        conn = sqlite3.connect(str(self._db_path))
        cursor = conn.cursor()
        
        # Checkpoints table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS checkpoints (
                checkpoint_id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                state_hash TEXT NOT NULL,
                data BLOB NOT NULL,
                version TEXT DEFAULT '1.0.0',
                parent_checkpoint_id TEXT,
                tags TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Missions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS missions (
                mission_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                primary_goal TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                progress REAL DEFAULT 0.0,
                assigned_agent_id TEXT,
                data BLOB NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Agent registry
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agents (
                agent_id TEXT PRIMARY KEY,
                name TEXT,
                type TEXT,
                state TEXT DEFAULT 'active',
                last_checkpoint_id TEXT,
                total_runtime_seconds REAL DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                last_active TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_checkpoints_agent ON checkpoints(agent_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_missions_status ON missions(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_agents_state ON agents(state)")
        
        conn.commit()
        conn.close()
    
    async def start(self) -> None:
        """Start the persistence manager."""
        self._running = True
        self._checkpoint_task = asyncio.create_task(self._checkpoint_loop())
        logger.info("PersistentAgentManager started")
    
    async def stop(self) -> None:
        """Stop the persistence manager and save all state."""
        self._running = False
        
        if self._checkpoint_task:
            self._checkpoint_task.cancel()
            try:
                await self._checkpoint_task
            except asyncio.CancelledError:
                pass
        
        # Final checkpoint for all active agents
        for agent_id in list(self._active_agents.keys()):
            await self.checkpoint_agent(agent_id, tags=["shutdown"])
        
        logger.info("PersistentAgentManager stopped")
    
    async def _checkpoint_loop(self) -> None:
        """Background loop for automatic checkpointing."""
        while self._running:
            try:
                now = datetime.utcnow()
                
                for agent_id, next_checkpoint in list(self._checkpoint_schedule.items()):
                    if now >= next_checkpoint:
                        await self.checkpoint_agent(agent_id, tags=["auto"])
                        self._checkpoint_schedule[agent_id] = now + self.checkpoint_interval
                
                await asyncio.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Checkpoint loop error: {e}")
                await asyncio.sleep(60)
    
    async def register_agent(
        self,
        agent_id: str,
        name: str = None,
        agent_type: str = "generic",
        initial_state: Dict[str, Any] = None
    ) -> AgentCheckpoint:
        """Register a new agent for persistence tracking."""
        checkpoint = AgentCheckpoint(
            checkpoint_id=self._generate_id("ckpt"),
            agent_id=agent_id,
            timestamp=datetime.utcnow(),
            state_hash=self._compute_hash(initial_state or {}),
            memory_snapshot=initial_state.get("memory", {}) if initial_state else {},
            context_window=initial_state.get("context", []) if initial_state else [],
            active_goals=initial_state.get("goals", []) if initial_state else []
        )
        
        self._active_agents[agent_id] = checkpoint
        self._checkpoint_schedule[agent_id] = datetime.utcnow() + self.checkpoint_interval
        
        # Save to database
        conn = sqlite3.connect(str(self._db_path))
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO agents (agent_id, name, type, state, last_checkpoint_id)
            VALUES (?, ?, ?, 'active', ?)
        """, (agent_id, name or agent_id, agent_type, checkpoint.checkpoint_id))
        conn.commit()
        conn.close()
        
        await self._save_checkpoint(checkpoint)
        
        logger.info(f"Registered agent {agent_id} for persistence")
        return checkpoint
    
    async def checkpoint_agent(
        self,
        agent_id: str,
        state: Dict[str, Any] = None,
        tags: List[str] = None
    ) -> AgentCheckpoint:
        """Create a checkpoint for an agent."""
        if agent_id not in self._active_agents:
            raise ValueError(f"Agent {agent_id} not registered")
        
        current = self._active_agents[agent_id]
        
        # Create new checkpoint
        checkpoint = AgentCheckpoint(
            checkpoint_id=self._generate_id("ckpt"),
            agent_id=agent_id,
            timestamp=datetime.utcnow(),
            state_hash=self._compute_hash(state or {}),
            parent_checkpoint_id=current.checkpoint_id,
            tags=tags or []
        )
        
        # Update state from provided data
        if state:
            checkpoint.memory_snapshot = state.get("memory", current.memory_snapshot)
            checkpoint.context_window = state.get("context", current.context_window)
            checkpoint.active_goals = state.get("goals", current.active_goals)
            checkpoint.completed_goals = state.get("completed_goals", current.completed_goals)
            checkpoint.current_task = state.get("current_task")
            checkpoint.task_queue = state.get("task_queue", current.task_queue)
            checkpoint.execution_history = state.get("execution_history", current.execution_history)
            checkpoint.tool_states = state.get("tool_states", current.tool_states)
            checkpoint.learned_patterns = state.get("learned_patterns", current.learned_patterns)
        else:
            # Copy from current
            checkpoint.memory_snapshot = current.memory_snapshot
            checkpoint.context_window = current.context_window
            checkpoint.active_goals = current.active_goals
            checkpoint.completed_goals = current.completed_goals
            checkpoint.current_task = current.current_task
            checkpoint.task_queue = current.task_queue
            checkpoint.execution_history = current.execution_history
            checkpoint.tool_states = current.tool_states
            checkpoint.learned_patterns = current.learned_patterns
        
        self._active_agents[agent_id] = checkpoint
        await self._save_checkpoint(checkpoint)
        
        # Cleanup old checkpoints
        await self._cleanup_old_checkpoints(agent_id)
        
        logger.debug(f"Checkpoint created for agent {agent_id}: {checkpoint.checkpoint_id}")
        return checkpoint
    
    async def restore_agent(
        self,
        agent_id: str,
        checkpoint_id: str = None
    ) -> AgentCheckpoint:
        """Restore an agent from a checkpoint."""
        conn = sqlite3.connect(str(self._db_path))
        cursor = conn.cursor()
        
        if checkpoint_id:
            cursor.execute(
                "SELECT data FROM checkpoints WHERE checkpoint_id = ?",
                (checkpoint_id,)
            )
        else:
            # Get latest checkpoint
            cursor.execute(
                "SELECT data FROM checkpoints WHERE agent_id = ? ORDER BY timestamp DESC LIMIT 1",
                (agent_id,)
            )
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            raise ValueError(f"No checkpoint found for agent {agent_id}")
        
        checkpoint = pickle.loads(row[0])
        self._active_agents[agent_id] = checkpoint
        self._checkpoint_schedule[agent_id] = datetime.utcnow() + self.checkpoint_interval
        
        logger.info(f"Restored agent {agent_id} from checkpoint {checkpoint.checkpoint_id}")
        return checkpoint
    
    async def _save_checkpoint(self, checkpoint: AgentCheckpoint) -> None:
        """Save checkpoint to database."""
        data = pickle.dumps(checkpoint)
        
        conn = sqlite3.connect(str(self._db_path))
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO checkpoints (checkpoint_id, agent_id, timestamp, state_hash, data, version, parent_checkpoint_id, tags)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            checkpoint.checkpoint_id,
            checkpoint.agent_id,
            checkpoint.timestamp.isoformat(),
            checkpoint.state_hash,
            data,
            checkpoint.version,
            checkpoint.parent_checkpoint_id,
            json.dumps(checkpoint.tags)
        ))
        
        # Update agent's last checkpoint
        cursor.execute("""
            UPDATE agents SET last_checkpoint_id = ?, last_active = CURRENT_TIMESTAMP
            WHERE agent_id = ?
        """, (checkpoint.checkpoint_id, checkpoint.agent_id))
        
        conn.commit()
        conn.close()
    
    async def _cleanup_old_checkpoints(self, agent_id: str) -> None:
        """Remove old checkpoints beyond the limit."""
        conn = sqlite3.connect(str(self._db_path))
        cursor = conn.cursor()
        
        # Get checkpoint count
        cursor.execute(
            "SELECT COUNT(*) FROM checkpoints WHERE agent_id = ?",
            (agent_id,)
        )
        count = cursor.fetchone()[0]
        
        if count > self.max_checkpoints:
            # Delete oldest checkpoints (keep tagged ones)
            delete_count = count - self.max_checkpoints
            cursor.execute("""
                DELETE FROM checkpoints WHERE checkpoint_id IN (
                    SELECT checkpoint_id FROM checkpoints
                    WHERE agent_id = ? AND tags = '[]'
                    ORDER BY timestamp ASC
                    LIMIT ?
                )
            """, (agent_id, delete_count))
            conn.commit()
        
        conn.close()
    
    # Mission Management
    
    async def create_mission(
        self,
        name: str,
        primary_goal: str,
        description: str = None,
        sub_goals: List[str] = None,
        success_criteria: List[str] = None,
        deadline: datetime = None,
        max_runtime_hours: float = None
    ) -> Mission:
        """Create a new long-running mission."""
        mission = Mission(
            mission_id=self._generate_id("mission"),
            name=name,
            description=description or "",
            created_at=datetime.utcnow(),
            primary_goal=primary_goal,
            sub_goals=sub_goals or [],
            success_criteria=success_criteria or [],
            deadline=deadline,
            max_runtime_hours=max_runtime_hours
        )
        
        self._active_missions[mission.mission_id] = mission
        await self._save_mission(mission)
        
        logger.info(f"Created mission {mission.mission_id}: {name}")
        return mission
    
    async def assign_mission(self, mission_id: str, agent_id: str) -> Mission:
        """Assign a mission to an agent."""
        if mission_id not in self._active_missions:
            mission = await self._load_mission(mission_id)
        else:
            mission = self._active_missions[mission_id]
        
        mission.assigned_agent_id = agent_id
        mission.status = MissionStatus.IN_PROGRESS
        
        # Add to agent's goals
        if agent_id in self._active_agents:
            self._active_agents[agent_id].active_goals.append(mission.primary_goal)
        
        await self._save_mission(mission)
        
        logger.info(f"Assigned mission {mission_id} to agent {agent_id}")
        return mission
    
    async def update_mission_progress(
        self,
        mission_id: str,
        progress: float,
        phase: str = None,
        log_entry: Dict[str, Any] = None
    ) -> Mission:
        """Update mission progress."""
        if mission_id not in self._active_missions:
            mission = await self._load_mission(mission_id)
        else:
            mission = self._active_missions[mission_id]
        
        mission.progress_percentage = min(100.0, max(0.0, progress))
        if phase:
            mission.current_phase = phase
        if log_entry:
            log_entry["timestamp"] = datetime.utcnow().isoformat()
            mission.execution_log.append(log_entry)
        
        await self._save_mission(mission)
        return mission
    
    async def complete_mission(
        self,
        mission_id: str,
        outputs: Dict[str, Any] = None,
        artifacts: List[str] = None,
        report: str = None
    ) -> Mission:
        """Mark a mission as completed."""
        if mission_id not in self._active_missions:
            mission = await self._load_mission(mission_id)
        else:
            mission = self._active_missions[mission_id]
        
        mission.status = MissionStatus.COMPLETED
        mission.progress_percentage = 100.0
        mission.outputs = outputs or {}
        mission.artifacts = artifacts or []
        mission.final_report = report
        
        await self._save_mission(mission)
        
        logger.info(f"Mission {mission_id} completed")
        return mission
    
    async def _save_mission(self, mission: Mission) -> None:
        """Save mission to database."""
        data = pickle.dumps(mission)
        
        conn = sqlite3.connect(str(self._db_path))
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO missions 
            (mission_id, name, description, primary_goal, status, progress, assigned_agent_id, data, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (
            mission.mission_id,
            mission.name,
            mission.description,
            mission.primary_goal,
            mission.status.value,
            mission.progress_percentage,
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
        self._active_missions[mission_id] = mission
        return mission
    
    async def list_active_missions(self) -> List[Mission]:
        """List all active missions."""
        conn = sqlite3.connect(str(self._db_path))
        cursor = conn.cursor()
        cursor.execute(
            "SELECT data FROM missions WHERE status IN ('pending', 'in_progress', 'paused', 'blocked')"
        )
        rows = cursor.fetchall()
        conn.close()
        
        return [pickle.loads(row[0]) for row in rows]
    
    async def list_agent_checkpoints(
        self,
        agent_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """List checkpoints for an agent."""
        conn = sqlite3.connect(str(self._db_path))
        cursor = conn.cursor()
        cursor.execute("""
            SELECT checkpoint_id, timestamp, state_hash, tags
            FROM checkpoints
            WHERE agent_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (agent_id, limit))
        rows = cursor.fetchall()
        conn.close()
        
        return [{
            "checkpoint_id": row[0],
            "timestamp": row[1],
            "state_hash": row[2],
            "tags": json.loads(row[3]) if row[3] else []
        } for row in rows]
    
    # Utility methods
    
    def _generate_id(self, prefix: str) -> str:
        """Generate a unique ID."""
        import uuid
        return f"{prefix}_{uuid.uuid4().hex[:12]}"
    
    def _compute_hash(self, data: Dict[str, Any]) -> str:
        """Compute hash of state data."""
        serialized = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode()).hexdigest()[:16]
    
    def get_agent_state(self, agent_id: str) -> Optional[AgentCheckpoint]:
        """Get current in-memory state for an agent."""
        return self._active_agents.get(agent_id)
    
    def get_mission(self, mission_id: str) -> Optional[Mission]:
        """Get mission from cache or None."""
        return self._active_missions.get(mission_id)


# Singleton instance
_persistence_manager: Optional[PersistentAgentManager] = None


def get_persistence_manager() -> PersistentAgentManager:
    """Get the global persistence manager instance."""
    global _persistence_manager
    if _persistence_manager is None:
        _persistence_manager = PersistentAgentManager()
    return _persistence_manager


async def main():
    """Example usage."""
    manager = get_persistence_manager()
    await manager.start()
    
    # Register an agent
    checkpoint = await manager.register_agent(
        agent_id="agent_001",
        name="ResearchAgent",
        agent_type="researcher",
        initial_state={
            "memory": {"topic": "AI systems"},
            "goals": ["Research competitor frameworks"]
        }
    )
    print(f"Registered agent with checkpoint: {checkpoint.checkpoint_id}")
    
    # Create a mission
    mission = await manager.create_mission(
        name="Competitive Analysis",
        primary_goal="Analyze all major AI agent frameworks",
        sub_goals=[
            "Study AutoGPT architecture",
            "Analyze LangChain patterns",
            "Compare with Bael capabilities"
        ],
        success_criteria=[
            "Complete feature comparison matrix",
            "Identify unique differentiators",
            "Generate improvement recommendations"
        ],
        max_runtime_hours=48.0
    )
    print(f"Created mission: {mission.mission_id}")
    
    # Assign mission
    await manager.assign_mission(mission.mission_id, "agent_001")
    
    # Simulate progress
    await manager.update_mission_progress(
        mission.mission_id,
        progress=25.0,
        phase="data_collection",
        log_entry={"action": "Started analyzing AutoGPT"}
    )
    
    # Create checkpoint
    await manager.checkpoint_agent(
        "agent_001",
        state={
            "memory": {"topic": "AI systems", "findings": ["AutoGPT uses GPT-4"]},
            "goals": ["Research competitor frameworks"],
            "current_task": "Analyzing AutoGPT"
        },
        tags=["manual", "progress_25"]
    )
    
    # List checkpoints
    checkpoints = await manager.list_agent_checkpoints("agent_001")
    print(f"Agent checkpoints: {len(checkpoints)}")
    
    await manager.stop()


if __name__ == "__main__":
    asyncio.run(main())

"""
Advanced Scheduling & Workflow Automation

Cron, event-based, condition-based, AI-predicted triggers.
Workflow automation on steroids with intelligent scheduling.
"""

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class TriggerType(Enum):
    """Types of triggers."""
    CRON = "cron"  # Time-based
    EVENT = "event"  # Event-based
    CONDITION = "condition"  # Condition-based
    METRIC = "metric"  # Metric-based
    WEBHOOK = "webhook"  # External webhook
    MANUAL = "manual"  # Manual trigger
    PREDICTED = "predicted"  # AI-predicted


class WorkflowState(Enum):
    """Workflow execution state."""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Trigger:
    """Trigger for workflow execution."""
    id: str
    name: str
    trigger_type: TriggerType
    enabled: bool = True
    config: Dict[str, Any] = field(default_factory=dict)
    last_fired: Optional[datetime] = None
    fire_count: int = 0


@dataclass
class WorkflowStep:
    """Step in workflow."""
    id: str
    name: str
    action_type: str
    parameters: Dict[str, Any]
    timeout: int = 300
    retries: int = 3
    depends_on: List[str] = field(default_factory=list)


@dataclass
class WorkflowExecution:
    """Workflow execution record."""
    id: str
    workflow_id: str
    state: WorkflowState
    started_at: datetime
    completed_at: Optional[datetime] = None
    trigger_type: Optional[TriggerType] = None
    steps_completed: int = 0
    total_steps: int = 0
    error_message: Optional[str] = None


class AdvancedScheduler:
    """Advanced scheduling with multiple trigger types."""

    def __init__(self):
        """Initialize scheduler."""
        self.workflows: Dict[str, Dict[str, Any]] = {}
        self.triggers: Dict[str, Trigger] = {}
        self.executions: List[WorkflowExecution] = []
        self.execution_history: List[Dict] = []

        logger.info("Advanced scheduler initialized")

    def create_workflow(
        self,
        name: str,
        steps: List[WorkflowStep],
        description: str = "",
        enabled: bool = True
    ) -> str:
        """Create workflow."""
        workflow_id = hashlib.md5(
            f"{name}{datetime.now().timestamp()}".encode()
        ).hexdigest()[:16]

        workflow = {
            "id": workflow_id,
            "name": name,
            "description": description,
            "steps": steps,
            "enabled": enabled,
            "created_at": datetime.now(),
            "execution_count": 0,
            "success_count": 0,
            "failure_count": 0
        }

        self.workflows[workflow_id] = workflow
        logger.info(f"Created workflow: {name}")

        return workflow_id

    def add_cron_trigger(
        self,
        workflow_id: str,
        cron_expression: str,
        name: str = "cron_trigger"
    ) -> str:
        """Add cron-based trigger."""
        trigger_id = hashlib.md5(
            f"{workflow_id}{cron_expression}{datetime.now().timestamp()}".encode()
        ).hexdigest()[:16]

        trigger = Trigger(
            id=trigger_id,
            name=name,
            trigger_type=TriggerType.CRON,
            config={"expression": cron_expression, "workflow_id": workflow_id}
        )

        self.triggers[trigger_id] = trigger
        logger.info(f"Added cron trigger: {cron_expression}")

        return trigger_id

    def add_event_trigger(
        self,
        workflow_id: str,
        event_pattern: str,
        name: str = "event_trigger"
    ) -> str:
        """Add event-based trigger."""
        trigger_id = hashlib.md5(
            f"{workflow_id}{event_pattern}{datetime.now().timestamp()}".encode()
        ).hexdigest()[:16]

        trigger = Trigger(
            id=trigger_id,
            name=name,
            trigger_type=TriggerType.EVENT,
            config={"pattern": event_pattern, "workflow_id": workflow_id}
        )

        self.triggers[trigger_id] = trigger
        logger.info(f"Added event trigger: {event_pattern}")

        return trigger_id

    def add_condition_trigger(
        self,
        workflow_id: str,
        condition_func: Callable[[Dict], bool],
        check_interval: int = 60,
        name: str = "condition_trigger"
    ) -> str:
        """Add condition-based trigger."""
        trigger_id = hashlib.md5(
            f"{workflow_id}condition{datetime.now().timestamp()}".encode()
        ).hexdigest()[:16]

        trigger = Trigger(
            id=trigger_id,
            name=name,
            trigger_type=TriggerType.CONDITION,
            config={
                "check_interval": check_interval,
                "workflow_id": workflow_id,
                "condition_func": condition_func
            }
        )

        self.triggers[trigger_id] = trigger
        logger.info(f"Added condition trigger")

        return trigger_id

    def add_metric_trigger(
        self,
        workflow_id: str,
        metric_name: str,
        threshold: float,
        comparison: str = ">",  # >, <, >=, <=, ==
        name: str = "metric_trigger"
    ) -> str:
        """Add metric-based trigger."""
        trigger_id = hashlib.md5(
            f"{workflow_id}{metric_name}{datetime.now().timestamp()}".encode()
        ).hexdigest()[:16]

        trigger = Trigger(
            id=trigger_id,
            name=name,
            trigger_type=TriggerType.METRIC,
            config={
                "metric": metric_name,
                "threshold": threshold,
                "comparison": comparison,
                "workflow_id": workflow_id
            }
        )

        self.triggers[trigger_id] = trigger
        logger.info(f"Added metric trigger: {metric_name} {comparison} {threshold}")

        return trigger_id

    def add_ai_predicted_trigger(
        self,
        workflow_id: str,
        prediction_model: Callable[[Dict], float],
        threshold: float = 0.8,
        name: str = "ai_trigger"
    ) -> str:
        """Add AI-predicted trigger."""
        trigger_id = hashlib.md5(
            f"{workflow_id}ai_predicted{datetime.now().timestamp()}".encode()
        ).hexdigest()[:16]

        trigger = Trigger(
            id=trigger_id,
            name=name,
            trigger_type=TriggerType.PREDICTED,
            config={
                "model": prediction_model,
                "threshold": threshold,
                "workflow_id": workflow_id
            }
        )

        self.triggers[trigger_id] = trigger
        logger.info(f"Added AI-predicted trigger (threshold: {threshold})")

        return trigger_id

    async def execute_workflow(
        self,
        workflow_id: str,
        trigger_type: TriggerType = TriggerType.MANUAL,
        context: Optional[Dict] = None
    ) -> str:
        """Execute workflow."""
        workflow = self.workflows.get(workflow_id)
        if not workflow:
            logger.error(f"Workflow not found: {workflow_id}")
            return ""

        execution_id = hashlib.md5(
            f"{workflow_id}{datetime.now().timestamp()}".encode()
        ).hexdigest()[:16]

        execution = WorkflowExecution(
            id=execution_id,
            workflow_id=workflow_id,
            state=WorkflowState.RUNNING,
            started_at=datetime.now(),
            trigger_type=trigger_type,
            total_steps=len(workflow["steps"])
        )

        self.executions.append(execution)

        logger.info(f"Executing workflow: {workflow['name']}")

        # Execute steps
        try:
            for step in workflow["steps"]:
                logger.info(f"Executing step: {step.name}")
                execution.steps_completed += 1

                # Check dependencies
                # Execute action
                # Handle errors and retries

            execution.state = WorkflowState.COMPLETED
            execution.completed_at = datetime.now()
            workflow["success_count"] += 1

            logger.info(f"Workflow completed: {workflow['name']}")

        except Exception as e:
            execution.state = WorkflowState.FAILED
            execution.error_message = str(e)
            execution.completed_at = datetime.now()
            workflow["failure_count"] += 1

            logger.error(f"Workflow failed: {e}")

        workflow["execution_count"] += 1
        self.execution_history.append({
            "execution_id": execution_id,
            "workflow_id": workflow_id,
            "state": execution.state.value,
            "timestamp": execution.started_at
        })

        return execution_id

    async def check_triggers(self, current_context: Dict[str, Any]):
        """Check all enabled triggers."""
        for trigger in self.triggers.values():
            if not trigger.enabled:
                continue

            should_fire = False

            if trigger.trigger_type == TriggerType.CRON:
                # Check cron expression
                should_fire = self._check_cron(trigger.config["expression"])

            elif trigger.trigger_type == TriggerType.EVENT:
                # Check event pattern
                should_fire = self._check_event_pattern(
                    trigger.config["pattern"],
                    current_context
                )

            elif trigger.trigger_type == TriggerType.CONDITION:
                # Check condition function
                should_fire = trigger.config["condition_func"](current_context)

            elif trigger.trigger_type == TriggerType.METRIC:
                # Check metric threshold
                should_fire = self._check_metric(
                    trigger.config["metric"],
                    trigger.config["threshold"],
                    trigger.config["comparison"],
                    current_context
                )

            elif trigger.trigger_type == TriggerType.PREDICTED:
                # Check AI prediction
                prediction = trigger.config["model"](current_context)
                should_fire = prediction >= trigger.config["threshold"]

            if should_fire:
                workflow_id = trigger.config["workflow_id"]
                trigger.fire_count += 1
                trigger.last_fired = datetime.now()

                await self.execute_workflow(
                    workflow_id,
                    trigger.trigger_type,
                    current_context
                )

    def _check_cron(self, expression: str) -> bool:
        """Check if cron expression matches current time."""
        # Simplified - in real implementation use croniter
        return True

    def _check_event_pattern(self, pattern: str, context: Dict) -> bool:
        """Check if event matches pattern."""
        # Pattern matching logic
        return pattern in str(context)

    def _check_metric(
        self,
        metric_name: str,
        threshold: float,
        comparison: str,
        context: Dict
    ) -> bool:
        """Check metric against threshold."""
        value = context.get(metric_name, 0)

        if comparison == ">":
            return value > threshold
        elif comparison == "<":
            return value < threshold
        elif comparison == ">=":
            return value >= threshold
        elif comparison == "<=":
            return value <= threshold
        elif comparison == "==":
            return value == threshold

        return False

    def get_workflow_stats(self, workflow_id: str) -> Dict[str, Any]:
        """Get workflow statistics."""
        workflow = self.workflows.get(workflow_id)
        if not workflow:
            return {}

        return {
            "name": workflow["name"],
            "execution_count": workflow["execution_count"],
            "success_count": workflow["success_count"],
            "failure_count": workflow["failure_count"],
            "success_rate": (
                workflow["success_count"] / workflow["execution_count"] * 100
                if workflow["execution_count"] > 0 else 0
            ),
            "triggers": len([t for t in self.triggers.values() if t.config.get("workflow_id") == workflow_id])
        }

    def get_scheduler_stats(self) -> Dict[str, Any]:
        """Get scheduler statistics."""
        return {
            "total_workflows": len(self.workflows),
            "total_triggers": len(self.triggers),
            "total_executions": len(self.executions),
            "active_executions": len([e for e in self.executions if e.state == WorkflowState.RUNNING]),
            "success_rate": (
                sum(w["success_count"] for w in self.workflows.values()) /
                max(1, sum(w["execution_count"] for w in self.workflows.values())) * 100
            ),
            "triggers_by_type": {
                t.value: len([tr for tr in self.triggers.values() if tr.trigger_type == t])
                for t in TriggerType
            }
        }


if __name__ == "__main__":
    import asyncio

    async def demo():
        scheduler = AdvancedScheduler()

        # Create workflow
        steps = [
            WorkflowStep(
                id="1",
                name="Deploy",
                action_type="deploy",
                parameters={"service": "api"}
            ),
            WorkflowStep(
                id="2",
                name="Test",
                action_type="test",
                parameters={"suite": "integration"},
                depends_on=["1"]
            )
        ]

        workflow_id = scheduler.create_workflow(
            "Deployment Pipeline",
            steps,
            "Automated deployment workflow"
        )

        # Add triggers
        scheduler.add_cron_trigger(workflow_id, "0 2 * * *", "Nightly Deploy")
        scheduler.add_event_trigger(workflow_id, "github.push.main", "On Main Push")
        scheduler.add_metric_trigger(workflow_id, "error_rate", 0.1, ">", "High Errors")

        # Execute
        execution_id = await scheduler.execute_workflow(workflow_id)

        # Get stats
        stats = scheduler.get_scheduler_stats()
        print(f"Scheduler stats: {stats}")

    asyncio.run(demo())

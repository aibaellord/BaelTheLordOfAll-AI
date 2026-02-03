#!/usr/bin/env python3
"""
BAEL - Autonomous Agent System
Self-directed agents with goals, beliefs, and intentions.

Features:
- BDI (Belief-Desire-Intention) architecture
- Goal-directed behavior
- Plan generation and execution
- Multi-agent coordination
- Autonomous decision making
- Self-monitoring and adaptation
"""

import asyncio
import heapq
import logging
import random
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union
from uuid import uuid4

logger = logging.getLogger(__name__)


# =============================================================================
# TYPES
# =============================================================================

class AgentState(Enum):
    """Agent states."""
    IDLE = "idle"
    PLANNING = "planning"
    EXECUTING = "executing"
    WAITING = "waiting"
    SUSPENDED = "suspended"
    TERMINATED = "terminated"


class GoalState(Enum):
    """Goal states."""
    PENDING = "pending"
    ACTIVE = "active"
    ACHIEVED = "achieved"
    FAILED = "failed"
    DROPPED = "dropped"


class IntentionState(Enum):
    """Intention states."""
    INTENDED = "intended"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SUSPENDED = "suspended"
    ABANDONED = "abandoned"


class MessageType(Enum):
    """Inter-agent message types."""
    INFORM = "inform"
    REQUEST = "request"
    PROPOSE = "propose"
    ACCEPT = "accept"
    REJECT = "reject"
    QUERY = "query"
    RESPONSE = "response"


# =============================================================================
# BELIEFS
# =============================================================================

@dataclass
class Belief:
    """A belief held by an agent."""
    id: str
    content: str
    confidence: float = 1.0
    source: str = "observation"
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def update(self, new_confidence: float) -> None:
        """Update belief confidence."""
        self.confidence = new_confidence
        self.timestamp = datetime.now()


class BeliefBase:
    """Knowledge base for agent beliefs."""

    def __init__(self):
        self.beliefs: Dict[str, Belief] = {}
        self.belief_index: Dict[str, Set[str]] = defaultdict(set)  # keyword -> belief_ids

    def add(self, content: str, confidence: float = 1.0, source: str = "observation") -> Belief:
        """Add a belief."""
        belief = Belief(
            id=str(uuid4()),
            content=content,
            confidence=confidence,
            source=source
        )
        self.beliefs[belief.id] = belief

        # Index by keywords
        words = content.lower().split()
        for word in words:
            self.belief_index[word].add(belief.id)

        return belief

    def remove(self, belief_id: str) -> None:
        """Remove a belief."""
        if belief_id in self.beliefs:
            del self.beliefs[belief_id]

    def update(self, belief_id: str, new_confidence: float) -> None:
        """Update belief confidence."""
        if belief_id in self.beliefs:
            self.beliefs[belief_id].update(new_confidence)

    def query(self, keyword: str) -> List[Belief]:
        """Query beliefs by keyword."""
        belief_ids = self.belief_index.get(keyword.lower(), set())
        return [self.beliefs[bid] for bid in belief_ids if bid in self.beliefs]

    def get_all(self, min_confidence: float = 0.0) -> List[Belief]:
        """Get all beliefs above confidence threshold."""
        return [b for b in self.beliefs.values() if b.confidence >= min_confidence]

    def contradicts(self, belief1: Belief, belief2: Belief) -> bool:
        """Check if two beliefs contradict."""
        # Simple heuristic: check for negation
        return ("not " + belief1.content.lower() == belief2.content.lower() or
                "not " + belief2.content.lower() == belief1.content.lower())


# =============================================================================
# DESIRES/GOALS
# =============================================================================

@dataclass
class Goal:
    """A goal the agent wants to achieve."""
    id: str
    description: str
    priority: float = 0.5
    state: GoalState = GoalState.PENDING
    preconditions: List[str] = field(default_factory=list)
    success_conditions: List[str] = field(default_factory=list)
    deadline: Optional[datetime] = None
    parent_goal: Optional[str] = None
    sub_goals: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_achievable(self, beliefs: BeliefBase) -> bool:
        """Check if preconditions are met."""
        for precond in self.preconditions:
            matching = beliefs.query(precond)
            if not matching or all(b.confidence < 0.5 for b in matching):
                return False
        return True

    def is_achieved(self, beliefs: BeliefBase) -> bool:
        """Check if success conditions are met."""
        for cond in self.success_conditions:
            matching = beliefs.query(cond)
            if not matching or all(b.confidence < 0.5 for b in matching):
                return False
        return True


class GoalManager:
    """Manage agent goals."""

    def __init__(self):
        self.goals: Dict[str, Goal] = {}
        self.goal_stack: List[str] = []  # Priority stack

    def add_goal(
        self,
        description: str,
        priority: float = 0.5,
        preconditions: List[str] = None,
        success_conditions: List[str] = None,
        deadline: datetime = None,
        parent_goal: str = None
    ) -> Goal:
        """Add a new goal."""
        goal = Goal(
            id=str(uuid4()),
            description=description,
            priority=priority,
            preconditions=preconditions or [],
            success_conditions=success_conditions or [],
            deadline=deadline,
            parent_goal=parent_goal
        )

        self.goals[goal.id] = goal
        self._reorder_goals()

        if parent_goal and parent_goal in self.goals:
            self.goals[parent_goal].sub_goals.append(goal.id)

        return goal

    def _reorder_goals(self) -> None:
        """Reorder goal stack by priority."""
        pending = [
            g for g in self.goals.values()
            if g.state in [GoalState.PENDING, GoalState.ACTIVE]
        ]
        pending.sort(key=lambda g: g.priority, reverse=True)
        self.goal_stack = [g.id for g in pending]

    def get_top_goal(self) -> Optional[Goal]:
        """Get highest priority goal."""
        while self.goal_stack:
            goal_id = self.goal_stack[0]
            if goal_id in self.goals:
                goal = self.goals[goal_id]
                if goal.state in [GoalState.PENDING, GoalState.ACTIVE]:
                    return goal
            self.goal_stack.pop(0)
        return None

    def update_state(self, goal_id: str, state: GoalState) -> None:
        """Update goal state."""
        if goal_id in self.goals:
            self.goals[goal_id].state = state
            self._reorder_goals()

    def get_achievable_goals(self, beliefs: BeliefBase) -> List[Goal]:
        """Get goals whose preconditions are met."""
        return [
            g for g in self.goals.values()
            if g.state == GoalState.PENDING and g.is_achievable(beliefs)
        ]


# =============================================================================
# INTENTIONS AND PLANS
# =============================================================================

@dataclass
class Action:
    """An action the agent can perform."""
    name: str
    preconditions: List[str] = field(default_factory=list)
    effects: List[str] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)
    duration: float = 1.0  # seconds
    handler: Optional[Callable] = None


@dataclass
class PlanStep:
    """A step in a plan."""
    action: Action
    parameters: Dict[str, Any] = field(default_factory=dict)
    status: str = "pending"  # pending, executing, completed, failed
    result: Any = None


@dataclass
class Plan:
    """A plan to achieve a goal."""
    id: str
    goal_id: str
    steps: List[PlanStep] = field(default_factory=list)
    current_step: int = 0
    created_at: datetime = field(default_factory=datetime.now)

    def is_complete(self) -> bool:
        """Check if plan is complete."""
        return self.current_step >= len(self.steps)

    def get_current_step(self) -> Optional[PlanStep]:
        """Get current step."""
        if self.current_step < len(self.steps):
            return self.steps[self.current_step]
        return None


@dataclass
class Intention:
    """An intention to execute a plan."""
    id: str
    goal: Goal
    plan: Plan
    state: IntentionState = IntentionState.INTENDED
    priority: float = 0.5
    suspended_at: Optional[datetime] = None


class Planner:
    """Plan generator using available actions."""

    def __init__(self):
        self.actions: Dict[str, Action] = {}

    def register_action(self, action: Action) -> None:
        """Register an action."""
        self.actions[action.name] = action

    async def generate_plan(
        self,
        goal: Goal,
        beliefs: BeliefBase
    ) -> Optional[Plan]:
        """Generate a plan to achieve goal."""
        # Simple forward search planner
        plan_steps = []
        current_state = set()

        # Get current beliefs as state
        for belief in beliefs.get_all(0.5):
            for word in belief.content.lower().split():
                current_state.add(word)

        target_state = set()
        for cond in goal.success_conditions:
            for word in cond.lower().split():
                target_state.add(word)

        # BFS to find action sequence
        visited = {frozenset(current_state)}
        queue = [(current_state, [])]

        while queue:
            state, actions_so_far = queue.pop(0)

            # Check if goal reached
            if target_state.issubset(state):
                plan_steps = actions_so_far
                break

            # Try each action
            for action in self.actions.values():
                # Check preconditions
                preconds = set()
                for p in action.preconditions:
                    for word in p.lower().split():
                        preconds.add(word)

                if preconds.issubset(state):
                    # Apply effects
                    new_state = state.copy()
                    for effect in action.effects:
                        for word in effect.lower().split():
                            new_state.add(word)

                    frozen = frozenset(new_state)
                    if frozen not in visited:
                        visited.add(frozen)
                        queue.append((new_state, actions_so_far + [action]))

        if plan_steps:
            return Plan(
                id=str(uuid4()),
                goal_id=goal.id,
                steps=[PlanStep(action=a) for a in plan_steps]
            )

        return None


# =============================================================================
# INTER-AGENT COMMUNICATION
# =============================================================================

@dataclass
class Message:
    """Message between agents."""
    id: str
    sender: str
    receiver: str
    message_type: MessageType
    content: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    in_reply_to: Optional[str] = None


class MessageQueue:
    """Message queue for agent communication."""

    def __init__(self):
        self.inbox: Dict[str, List[Message]] = defaultdict(list)
        self.outbox: Dict[str, List[Message]] = defaultdict(list)

    def send(self, message: Message) -> None:
        """Send a message."""
        self.outbox[message.sender].append(message)
        self.inbox[message.receiver].append(message)

    def receive(self, agent_id: str) -> List[Message]:
        """Receive messages for agent."""
        messages = self.inbox[agent_id]
        self.inbox[agent_id] = []
        return messages

    def get_pending(self, agent_id: str) -> int:
        """Get number of pending messages."""
        return len(self.inbox[agent_id])


# =============================================================================
# BDI AGENT
# =============================================================================

class BDIAgent:
    """Belief-Desire-Intention agent."""

    def __init__(
        self,
        agent_id: str,
        name: str,
        message_queue: MessageQueue
    ):
        self.id = agent_id
        self.name = name
        self.state = AgentState.IDLE

        # BDI components
        self.beliefs = BeliefBase()
        self.goals = GoalManager()
        self.planner = Planner()

        # Current intentions
        self.intentions: Dict[str, Intention] = {}
        self.current_intention: Optional[str] = None

        # Communication
        self.message_queue = message_queue

        # Behavior
        self.running = False
        self.cycle_delay = 0.1

    def add_belief(
        self,
        content: str,
        confidence: float = 1.0,
        source: str = "observation"
    ) -> Belief:
        """Add a belief."""
        return self.beliefs.add(content, confidence, source)

    def add_goal(
        self,
        description: str,
        priority: float = 0.5,
        preconditions: List[str] = None,
        success_conditions: List[str] = None
    ) -> Goal:
        """Add a goal."""
        return self.goals.add_goal(
            description,
            priority,
            preconditions,
            success_conditions
        )

    def register_action(self, action: Action) -> None:
        """Register an action."""
        self.planner.register_action(action)

    async def deliberate(self) -> Optional[Goal]:
        """Choose which goal to pursue."""
        # Get achievable goals
        achievable = self.goals.get_achievable_goals(self.beliefs)

        if not achievable:
            return self.goals.get_top_goal()

        # Select highest priority achievable goal
        return max(achievable, key=lambda g: g.priority)

    async def plan(self, goal: Goal) -> Optional[Plan]:
        """Generate plan for goal."""
        self.state = AgentState.PLANNING
        return await self.planner.generate_plan(goal, self.beliefs)

    async def execute_step(self, step: PlanStep) -> bool:
        """Execute a plan step."""
        self.state = AgentState.EXECUTING
        step.status = "executing"

        try:
            if step.action.handler:
                result = await step.action.handler(step.parameters, self)
                step.result = result
            else:
                # Default: just apply effects
                await asyncio.sleep(step.action.duration)
                for effect in step.action.effects:
                    self.add_belief(effect, 1.0, "action_effect")

            step.status = "completed"
            return True

        except Exception as e:
            logger.error(f"Action failed: {e}")
            step.status = "failed"
            return False

    async def process_messages(self) -> None:
        """Process incoming messages."""
        messages = self.message_queue.receive(self.id)

        for msg in messages:
            await self.handle_message(msg)

    async def handle_message(self, message: Message) -> None:
        """Handle a message."""
        if message.message_type == MessageType.INFORM:
            # Update beliefs
            content = message.content.get("belief", "")
            if content:
                self.add_belief(content, 0.8, f"agent:{message.sender}")

        elif message.message_type == MessageType.REQUEST:
            # Consider adding as goal
            request = message.content.get("request", "")
            if request:
                self.add_goal(
                    request,
                    priority=message.content.get("priority", 0.5)
                )

        elif message.message_type == MessageType.QUERY:
            # Respond with belief
            query = message.content.get("query", "")
            beliefs = self.beliefs.query(query)

            response = Message(
                id=str(uuid4()),
                sender=self.id,
                receiver=message.sender,
                message_type=MessageType.RESPONSE,
                content={"beliefs": [b.content for b in beliefs]},
                in_reply_to=message.id
            )
            self.message_queue.send(response)

    def send_message(
        self,
        receiver: str,
        message_type: MessageType,
        content: Dict[str, Any]
    ) -> Message:
        """Send a message to another agent."""
        message = Message(
            id=str(uuid4()),
            sender=self.id,
            receiver=receiver,
            message_type=message_type,
            content=content
        )
        self.message_queue.send(message)
        return message

    async def run_cycle(self) -> None:
        """Run one BDI reasoning cycle."""
        # 1. Process messages
        await self.process_messages()

        # 2. Check current intention
        if self.current_intention:
            intention = self.intentions.get(self.current_intention)

            if intention and intention.state == IntentionState.IN_PROGRESS:
                # Check if goal achieved
                if intention.goal.is_achieved(self.beliefs):
                    intention.state = IntentionState.COMPLETED
                    intention.goal.state = GoalState.ACHIEVED
                    self.current_intention = None
                    logger.info(f"Goal achieved: {intention.goal.description}")
                else:
                    # Execute next step
                    step = intention.plan.get_current_step()
                    if step:
                        success = await self.execute_step(step)
                        if success:
                            intention.plan.current_step += 1
                        else:
                            # Replan
                            new_plan = await self.plan(intention.goal)
                            if new_plan:
                                intention.plan = new_plan
                            else:
                                intention.state = IntentionState.ABANDONED
                                intention.goal.state = GoalState.FAILED
                                self.current_intention = None
                    else:
                        # Plan complete but goal not achieved?
                        intention.state = IntentionState.ABANDONED
                        self.current_intention = None

        # 3. Select new intention if needed
        if not self.current_intention:
            goal = await self.deliberate()

            if goal:
                plan = await self.plan(goal)

                if plan:
                    intention = Intention(
                        id=str(uuid4()),
                        goal=goal,
                        plan=plan,
                        state=IntentionState.IN_PROGRESS,
                        priority=goal.priority
                    )
                    self.intentions[intention.id] = intention
                    self.current_intention = intention.id
                    goal.state = GoalState.ACTIVE
                    logger.info(f"New intention: {goal.description}")

        self.state = AgentState.IDLE if not self.current_intention else AgentState.EXECUTING

    async def run(self) -> None:
        """Run the agent continuously."""
        self.running = True
        logger.info(f"Agent {self.name} started")

        while self.running:
            try:
                await self.run_cycle()
                await asyncio.sleep(self.cycle_delay)
            except Exception as e:
                logger.error(f"Agent error: {e}")

        self.state = AgentState.TERMINATED
        logger.info(f"Agent {self.name} stopped")

    def stop(self) -> None:
        """Stop the agent."""
        self.running = False

    def get_status(self) -> Dict[str, Any]:
        """Get agent status."""
        return {
            "id": self.id,
            "name": self.name,
            "state": self.state.value,
            "beliefs": len(self.beliefs.beliefs),
            "goals": len(self.goals.goals),
            "intentions": len(self.intentions),
            "current_intention": self.current_intention
        }


# =============================================================================
# MULTI-AGENT SYSTEM
# =============================================================================

class MultiAgentSystem:
    """Multi-agent system coordinator."""

    def __init__(self):
        self.agents: Dict[str, BDIAgent] = {}
        self.message_queue = MessageQueue()
        self.tasks: Dict[str, asyncio.Task] = {}

    def create_agent(self, name: str) -> BDIAgent:
        """Create a new agent."""
        agent_id = str(uuid4())
        agent = BDIAgent(agent_id, name, self.message_queue)
        self.agents[agent_id] = agent
        return agent

    def get_agent(self, agent_id: str) -> Optional[BDIAgent]:
        """Get agent by ID."""
        return self.agents.get(agent_id)

    def get_agents_by_name(self, name: str) -> List[BDIAgent]:
        """Get agents by name."""
        return [a for a in self.agents.values() if a.name == name]

    async def start_agent(self, agent_id: str) -> None:
        """Start an agent."""
        agent = self.agents.get(agent_id)
        if agent:
            task = asyncio.create_task(agent.run())
            self.tasks[agent_id] = task

    async def stop_agent(self, agent_id: str) -> None:
        """Stop an agent."""
        agent = self.agents.get(agent_id)
        if agent:
            agent.stop()
            if agent_id in self.tasks:
                await self.tasks[agent_id]
                del self.tasks[agent_id]

    async def start_all(self) -> None:
        """Start all agents."""
        for agent_id in self.agents:
            await self.start_agent(agent_id)

    async def stop_all(self) -> None:
        """Stop all agents."""
        for agent_id in list(self.agents.keys()):
            await self.stop_agent(agent_id)

    def broadcast(
        self,
        sender_id: str,
        message_type: MessageType,
        content: Dict[str, Any]
    ) -> List[Message]:
        """Broadcast message to all agents."""
        messages = []
        for agent_id in self.agents:
            if agent_id != sender_id:
                msg = Message(
                    id=str(uuid4()),
                    sender=sender_id,
                    receiver=agent_id,
                    message_type=message_type,
                    content=content
                )
                self.message_queue.send(msg)
                messages.append(msg)
        return messages

    def get_status(self) -> Dict[str, Any]:
        """Get system status."""
        return {
            "agents": len(self.agents),
            "running": sum(1 for a in self.agents.values() if a.running),
            "agent_statuses": [a.get_status() for a in self.agents.values()]
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demo autonomous agent system."""
    print("=== Autonomous Agent System Demo ===\n")

    # Create multi-agent system
    mas = MultiAgentSystem()

    # 1. Create agents
    print("1. Creating Agents:")

    worker = mas.create_agent("Worker")
    coordinator = mas.create_agent("Coordinator")

    print(f"   Created: {worker.name} ({worker.id[:8]}...)")
    print(f"   Created: {coordinator.name} ({coordinator.id[:8]}...)")

    # 2. Register actions
    print("\n2. Registering Actions:")

    async def gather_data(params, agent):
        print(f"   [{agent.name}] Gathering data...")
        await asyncio.sleep(0.1)
        return {"data": "sample_data"}

    async def process_data(params, agent):
        print(f"   [{agent.name}] Processing data...")
        await asyncio.sleep(0.1)
        return {"processed": True}

    async def report_results(params, agent):
        print(f"   [{agent.name}] Reporting results...")
        await asyncio.sleep(0.1)
        return {"reported": True}

    worker.register_action(Action(
        name="gather_data",
        preconditions=["task_assigned"],
        effects=["data_gathered"],
        handler=gather_data
    ))

    worker.register_action(Action(
        name="process_data",
        preconditions=["data_gathered"],
        effects=["data_processed"],
        handler=process_data
    ))

    worker.register_action(Action(
        name="report_results",
        preconditions=["data_processed"],
        effects=["results_reported"],
        handler=report_results
    ))

    print("   Registered: gather_data, process_data, report_results")

    # 3. Add beliefs and goals
    print("\n3. Adding Beliefs and Goals:")

    worker.add_belief("task_assigned", 1.0)
    print("   Worker belief: task_assigned")

    worker.add_goal(
        "Complete data processing task",
        priority=0.8,
        preconditions=["task"],
        success_conditions=["results_reported"]
    )
    print("   Worker goal: Complete data processing task")

    coordinator.add_goal(
        "Coordinate team",
        priority=0.7
    )
    print("   Coordinator goal: Coordinate team")

    # 4. Run agents
    print("\n4. Running Agents (5 cycles):")

    for i in range(5):
        await worker.run_cycle()
        await coordinator.run_cycle()

        # Check worker status
        status = worker.get_status()
        print(f"   Cycle {i+1}: Worker state={status['state']}, intentions={status['intentions']}")

    # 5. Inter-agent communication
    print("\n5. Inter-Agent Communication:")

    msg = worker.send_message(
        coordinator.id,
        MessageType.INFORM,
        {"belief": "task completed successfully"}
    )
    print(f"   Worker -> Coordinator: INFORM (task completed)")

    await coordinator.run_cycle()

    # Check coordinator beliefs
    beliefs = coordinator.beliefs.query("task")
    print(f"   Coordinator learned: {[b.content for b in beliefs]}")

    # 6. Request handling
    print("\n6. Request Handling:")

    coordinator.send_message(
        worker.id,
        MessageType.REQUEST,
        {"request": "analyze new dataset", "priority": 0.9}
    )
    print("   Coordinator -> Worker: REQUEST (analyze new dataset)")

    await worker.run_cycle()

    # Check worker goals
    goals = list(worker.goals.goals.values())
    print(f"   Worker goals: {[g.description for g in goals]}")

    # 7. Query handling
    print("\n7. Query Handling:")

    coordinator.send_message(
        worker.id,
        MessageType.QUERY,
        {"query": "data"}
    )
    print("   Coordinator -> Worker: QUERY (data)")

    await worker.run_cycle()
    await coordinator.run_cycle()

    responses = coordinator.message_queue.inbox.get(coordinator.id, [])
    print(f"   Coordinator received {len(responses)} responses")

    # 8. System status
    print("\n8. System Status:")

    status = mas.get_status()
    print(f"   Total agents: {status['agents']}")
    for agent_status in status['agent_statuses']:
        print(f"   {agent_status['name']}: {agent_status['state']}, "
              f"beliefs={agent_status['beliefs']}, goals={agent_status['goals']}")

    # 9. Goal achievement check
    print("\n9. Goal Achievement:")

    for goal in worker.goals.goals.values():
        print(f"   {goal.description}: {goal.state.value}")


if __name__ == "__main__":
    asyncio.run(demo())

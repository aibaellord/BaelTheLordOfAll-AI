"""
BAEL - The Lord of All AI Agents
Agent Orchestrator - Multi-Agent Coordination System

Manages the creation, coordination, and communication
of multiple AI agents working together on complex tasks.
"""

import asyncio
import json
import logging
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger("BAEL.Orchestrator")


class AgentRole(Enum):
    """Roles agents can take in the orchestration."""
    COORDINATOR = "coordinator"     # Manages other agents
    EXECUTOR = "executor"           # Performs tasks
    REVIEWER = "reviewer"           # Reviews work
    RESEARCHER = "researcher"       # Gathers information
    SPECIALIST = "specialist"       # Domain expert
    OBSERVER = "observer"           # Monitors progress


class AgentState(Enum):
    """States an agent can be in."""
    IDLE = "idle"
    WORKING = "working"
    WAITING = "waiting"
    COMPLETED = "completed"
    ERROR = "error"
    TERMINATED = "terminated"


class MessageType(Enum):
    """Types of messages between agents."""
    TASK = "task"
    RESULT = "result"
    QUERY = "query"
    RESPONSE = "response"
    STATUS = "status"
    HANDOFF = "handoff"
    BROADCAST = "broadcast"
    FEEDBACK = "feedback"


@dataclass
class AgentMessage:
    """A message between agents."""
    id: str
    sender_id: str
    recipient_id: str
    message_type: MessageType
    content: Any
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    requires_response: bool = False
    response_to: Optional[str] = None


@dataclass
class AgentContext:
    """Context shared with an agent."""
    task_description: str
    global_context: Dict[str, Any] = field(default_factory=dict)
    history: List[Dict] = field(default_factory=list)
    shared_memory: Dict[str, Any] = field(default_factory=dict)
    constraints: List[str] = field(default_factory=list)
    success_criteria: List[str] = field(default_factory=list)


@dataclass
class AgentConfig:
    """Configuration for spawning an agent."""
    id: Optional[str] = None
    name: str = "Agent"
    role: AgentRole = AgentRole.EXECUTOR
    persona_id: Optional[str] = None
    model_type: str = "primary"
    max_iterations: int = 50
    timeout_seconds: int = 300
    can_spawn_agents: bool = False
    can_use_tools: bool = True
    auto_terminate: bool = True


class BaelAgent:
    """
    A BAEL Agent - Autonomous entity that can perform tasks.

    Agents can:
    - Execute tasks independently
    - Communicate with other agents
    - Use tools and resources
    - Learn from interactions
    - Spawn sub-agents if permitted
    """

    def __init__(
        self,
        brain,
        config: AgentConfig,
        context: AgentContext
    ):
        self.brain = brain
        self.config = config
        self.context = context

        self.id = config.id or f"agent-{uuid.uuid4().hex[:8]}"
        self.name = config.name
        self.role = config.role
        self.state = AgentState.IDLE

        self.message_queue: asyncio.Queue = asyncio.Queue()
        self.outbox: List[AgentMessage] = []
        self.history: List[Dict] = []
        self.results: List[Any] = []

        self.persona = None
        self.created_at = datetime.now()
        self.started_at = None
        self.completed_at = None
        self.iterations = 0

    async def initialize(self):
        """Initialize the agent."""
        logger.info(f"🤖 Initializing agent {self.name} ({self.id})")

        # Load persona if specified
        if self.config.persona_id and self.brain.personas:
            if self.config.persona_id in self.brain.personas:
                self.persona = self.brain.personas[self.config.persona_id]
                await self.persona.activate()

        self.state = AgentState.IDLE

    async def run(self) -> Any:
        """Execute the agent's main task."""
        logger.info(f"🚀 Agent {self.name} starting task execution")
        self.state = AgentState.WORKING
        self.started_at = datetime.now()

        try:
            result = await self._execute_task()
            self.results.append(result)
            self.state = AgentState.COMPLETED
            self.completed_at = datetime.now()

            return result

        except asyncio.TimeoutError:
            logger.error(f"⏰ Agent {self.name} timed out")
            self.state = AgentState.ERROR
            return {'error': 'Agent timed out'}

        except Exception as e:
            logger.error(f"❌ Agent {self.name} error: {e}")
            self.state = AgentState.ERROR
            return {'error': str(e)}

        finally:
            if self.config.auto_terminate:
                await self.terminate()

    async def _execute_task(self) -> Any:
        """Execute the main task with iterations."""
        max_iterations = self.config.max_iterations

        while self.iterations < max_iterations:
            self.iterations += 1

            # Check for messages
            await self._process_messages()

            # Get current context
            current_context = self._build_context()

            # Think and act
            response = await self.brain.process(
                input_text=self.context.task_description,
                context=current_context
            )

            self.history.append({
                'iteration': self.iterations,
                'response': response,
                'timestamp': datetime.now().isoformat()
            })

            # Check if task is complete
            if self._is_task_complete(response):
                return {
                    'success': True,
                    'response': response,
                    'iterations': self.iterations
                }

            # Update context for next iteration
            self.context.history.append({
                'role': 'assistant',
                'content': response
            })

        return {
            'success': False,
            'response': self.history[-1]['response'] if self.history else '',
            'iterations': self.iterations,
            'reason': 'Max iterations reached'
        }

    def _build_context(self) -> Dict[str, Any]:
        """Build context for brain processing."""
        context = {
            'agent_id': self.id,
            'agent_name': self.name,
            'agent_role': self.role.value,
            'iteration': self.iterations,
            'history': self.context.history[-10:],  # Last 10 messages
            'shared_memory': self.context.shared_memory,
            'constraints': self.context.constraints,
            'success_criteria': self.context.success_criteria
        }

        if self.persona:
            context['persona'] = self.persona.name
            context['system_prompt'] = self.persona.system_prompt

        return context

    def _is_task_complete(self, response: str) -> bool:
        """Check if the task is complete."""
        # Check for explicit completion indicators
        completion_markers = [
            'task complete', 'task completed', 'finished',
            'done', 'complete', 'accomplished'
        ]

        response_lower = response.lower()
        if any(marker in response_lower for marker in completion_markers):
            return True

        # Check success criteria
        if self.context.success_criteria:
            criteria_met = sum(
                1 for c in self.context.success_criteria
                if c.lower() in response_lower
            )
            if criteria_met >= len(self.context.success_criteria) * 0.7:
                return True

        return False

    async def _process_messages(self):
        """Process pending messages."""
        while not self.message_queue.empty():
            try:
                message = await asyncio.wait_for(
                    self.message_queue.get(),
                    timeout=0.1
                )
                await self._handle_message(message)
            except asyncio.TimeoutError:
                break

    async def _handle_message(self, message: AgentMessage):
        """Handle an incoming message."""
        logger.debug(f"📬 Agent {self.name} received {message.message_type.value} from {message.sender_id}")

        if message.message_type == MessageType.TASK:
            # New task assignment
            self.context.task_description = message.content

        elif message.message_type == MessageType.QUERY:
            # Answer query
            response = await self._answer_query(message.content)
            await self.send_message(
                recipient_id=message.sender_id,
                message_type=MessageType.RESPONSE,
                content=response,
                response_to=message.id
            )

        elif message.message_type == MessageType.FEEDBACK:
            # Incorporate feedback
            self.context.history.append({
                'role': 'feedback',
                'content': message.content
            })

        elif message.message_type == MessageType.HANDOFF:
            # Task handoff from another agent
            self.context.global_context.update(message.metadata.get('context', {}))

    async def _answer_query(self, query: str) -> str:
        """Answer a query from another agent."""
        context = self._build_context()
        context['query'] = query

        response = await self.brain.process(
            input_text=f"Answer this query: {query}",
            context=context
        )

        return response

    async def send_message(
        self,
        recipient_id: str,
        message_type: MessageType,
        content: Any,
        response_to: Optional[str] = None,
        metadata: Optional[Dict] = None
    ):
        """Send a message to another agent."""
        message = AgentMessage(
            id=f"msg-{uuid.uuid4().hex[:8]}",
            sender_id=self.id,
            recipient_id=recipient_id,
            message_type=message_type,
            content=content,
            metadata=metadata or {},
            response_to=response_to
        )

        self.outbox.append(message)

    async def receive_message(self, message: AgentMessage):
        """Receive a message from another agent."""
        await self.message_queue.put(message)

    async def terminate(self):
        """Terminate the agent."""
        logger.info(f"🛑 Terminating agent {self.name}")

        if self.persona:
            await self.persona.deactivate()

        self.state = AgentState.TERMINATED

    def get_status(self) -> Dict[str, Any]:
        """Get current agent status."""
        return {
            'id': self.id,
            'name': self.name,
            'role': self.role.value,
            'state': self.state.value,
            'iterations': self.iterations,
            'created_at': self.created_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'persona': self.persona.name if self.persona else None
        }


class AgentOrchestrator:
    """
    Orchestrates multiple agents working together.

    Responsibilities:
    - Agent lifecycle management
    - Task distribution
    - Message routing
    - Progress monitoring
    - Result aggregation
    """

    def __init__(self, brain):
        self.brain = brain
        self.agents: Dict[str, BaelAgent] = {}
        self.message_bus: Dict[str, asyncio.Queue] = {}
        self.task_queue: asyncio.Queue = asyncio.Queue()
        self.completed_tasks: List[Dict] = []
        self.running = False

        self._router_task: Optional[asyncio.Task] = None

    async def spawn_agent(
        self,
        config: Optional[AgentConfig] = None,
        task: Optional[str] = None,
        context: Optional[Dict] = None
    ) -> BaelAgent:
        """Spawn a new agent."""
        config = config or AgentConfig()

        agent_context = AgentContext(
            task_description=task or "",
            global_context=context or {},
            shared_memory={}
        )

        agent = BaelAgent(
            brain=self.brain,
            config=config,
            context=agent_context
        )

        await agent.initialize()

        self.agents[agent.id] = agent
        self.message_bus[agent.id] = agent.message_queue

        logger.info(f"🤖 Spawned agent {agent.name} ({agent.id})")

        return agent

    async def spawn_team(
        self,
        task: str,
        roles: Optional[List[str]] = None
    ) -> List[BaelAgent]:
        """Spawn a team of agents for a task."""
        roles = roles or ['coordinator', 'executor', 'reviewer']
        agents = []

        for role in roles:
            config = AgentConfig(
                name=f"{role.title()} Agent",
                role=AgentRole[role.upper()],
                persona_id=self._map_role_to_persona(role)
            )

            agent = await self.spawn_agent(config=config, task=task)
            agents.append(agent)

        return agents

    def _map_role_to_persona(self, role: str) -> Optional[str]:
        """Map agent role to appropriate persona."""
        mapping = {
            'coordinator': 'architect_prime',
            'executor': 'code_master',
            'reviewer': 'qa_perfectionist',
            'researcher': 'research_oracle',
            'specialist': 'security_sentinel'
        }
        return mapping.get(role.lower())

    async def run_agent(self, agent_id: str) -> Any:
        """Run a specific agent."""
        if agent_id not in self.agents:
            raise ValueError(f"Agent {agent_id} not found")

        agent = self.agents[agent_id]
        return await agent.run()

    async def run_all(self, parallel: bool = True) -> Dict[str, Any]:
        """Run all agents."""
        self.running = True

        # Start message router
        self._router_task = asyncio.create_task(self._route_messages())

        results = {}

        if parallel:
            # Run all agents in parallel
            tasks = {
                agent_id: asyncio.create_task(agent.run())
                for agent_id, agent in self.agents.items()
                if agent.state == AgentState.IDLE
            }

            for agent_id, task in tasks.items():
                try:
                    results[agent_id] = await task
                except Exception as e:
                    results[agent_id] = {'error': str(e)}
        else:
            # Run agents sequentially
            for agent_id, agent in self.agents.items():
                if agent.state == AgentState.IDLE:
                    results[agent_id] = await agent.run()

        self.running = False

        if self._router_task:
            self._router_task.cancel()

        return results

    async def run_workflow(
        self,
        task: str,
        workflow: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Run a defined workflow of agent interactions.

        Workflow example:
        [
            {"role": "researcher", "action": "research", "pass_to": "architect"},
            {"role": "architect", "action": "design", "pass_to": "executor"},
            {"role": "executor", "action": "implement", "pass_to": "reviewer"},
            {"role": "reviewer", "action": "review", "pass_to": None}
        ]
        """
        results = {}
        previous_result = task

        for step in workflow:
            # Spawn agent for this step
            config = AgentConfig(
                name=f"{step['role'].title()} Agent",
                role=AgentRole.EXECUTOR,
                persona_id=self._map_role_to_persona(step['role'])
            )

            # Include previous result in context
            step_task = f"""
            {step['action'].upper()}: {task}

            Previous step output:
            {previous_result if isinstance(previous_result, str) else json.dumps(previous_result, indent=2)}
            """

            agent = await self.spawn_agent(config=config, task=step_task)
            result = await agent.run()

            results[step['role']] = result
            previous_result = result.get('response', '')

            # Handle handoff
            if step.get('pass_to'):
                # Store for next agent
                pass

        return {
            'task': task,
            'workflow_results': results,
            'final_result': previous_result
        }

    async def _route_messages(self):
        """Route messages between agents."""
        while self.running:
            try:
                # Collect outgoing messages from all agents
                for agent in self.agents.values():
                    while agent.outbox:
                        message = agent.outbox.pop(0)
                        await self._deliver_message(message)

                await asyncio.sleep(0.1)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Message routing error: {e}")

    async def _deliver_message(self, message: AgentMessage):
        """Deliver a message to its recipient."""
        if message.recipient_id == 'broadcast':
            # Send to all agents
            for agent_id, agent in self.agents.items():
                if agent_id != message.sender_id:
                    await agent.receive_message(message)
        elif message.recipient_id in self.agents:
            await self.agents[message.recipient_id].receive_message(message)
        else:
            logger.warning(f"Unknown recipient: {message.recipient_id}")

    async def send_to_agent(
        self,
        agent_id: str,
        message_type: MessageType,
        content: Any
    ):
        """Send a message to a specific agent."""
        if agent_id not in self.agents:
            raise ValueError(f"Agent {agent_id} not found")

        message = AgentMessage(
            id=f"msg-{uuid.uuid4().hex[:8]}",
            sender_id="orchestrator",
            recipient_id=agent_id,
            message_type=message_type,
            content=content
        )

        await self.agents[agent_id].receive_message(message)

    async def broadcast(self, message_type: MessageType, content: Any):
        """Broadcast a message to all agents."""
        for agent in self.agents.values():
            message = AgentMessage(
                id=f"msg-{uuid.uuid4().hex[:8]}",
                sender_id="orchestrator",
                recipient_id=agent.id,
                message_type=message_type,
                content=content
            )
            await agent.receive_message(message)

    def get_agent(self, agent_id: str) -> Optional[BaelAgent]:
        """Get an agent by ID."""
        return self.agents.get(agent_id)

    def get_all_statuses(self) -> List[Dict[str, Any]]:
        """Get status of all agents."""
        return [agent.get_status() for agent in self.agents.values()]

    async def terminate_agent(self, agent_id: str):
        """Terminate a specific agent."""
        if agent_id in self.agents:
            await self.agents[agent_id].terminate()
            del self.agents[agent_id]
            del self.message_bus[agent_id]

    async def terminate_all(self):
        """Terminate all agents."""
        for agent_id in list(self.agents.keys()):
            await self.terminate_agent(agent_id)


# =============================================================================
# WORKFLOW PATTERNS
# =============================================================================

class WorkflowPattern:
    """Predefined workflow patterns for common scenarios."""

    @staticmethod
    def code_review() -> List[Dict[str, Any]]:
        """Code review workflow."""
        return [
            {"role": "executor", "action": "implement code", "pass_to": "reviewer"},
            {"role": "reviewer", "action": "review code for issues", "pass_to": "security"},
            {"role": "specialist", "action": "security review", "pass_to": "executor"},
            {"role": "executor", "action": "apply improvements", "pass_to": None}
        ]

    @staticmethod
    def research_and_implement() -> List[Dict[str, Any]]:
        """Research then implement workflow."""
        return [
            {"role": "researcher", "action": "research best practices", "pass_to": "architect"},
            {"role": "architect", "action": "design solution", "pass_to": "executor"},
            {"role": "executor", "action": "implement solution", "pass_to": "reviewer"},
            {"role": "reviewer", "action": "validate implementation", "pass_to": None}
        ]

    @staticmethod
    def full_development() -> List[Dict[str, Any]]:
        """Complete development workflow."""
        return [
            {"role": "researcher", "action": "gather requirements", "pass_to": "architect"},
            {"role": "architect", "action": "design architecture", "pass_to": "executor"},
            {"role": "executor", "action": "implement code", "pass_to": "reviewer"},
            {"role": "reviewer", "action": "test and review", "pass_to": "specialist"},
            {"role": "specialist", "action": "security audit", "pass_to": "executor"},
            {"role": "executor", "action": "fix issues and finalize", "pass_to": None}
        ]


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    'AgentOrchestrator',
    'BaelAgent',
    'AgentConfig',
    'AgentContext',
    'AgentRole',
    'AgentState',
    'AgentMessage',
    'MessageType',
    'WorkflowPattern'
]

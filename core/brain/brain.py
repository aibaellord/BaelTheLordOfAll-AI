"""
BAEL - The Lord of All AI Agents
Core Brain Module - Central Control Unit

This is the central nervous system of BAEL, orchestrating all cognitive functions,
persona management, tool selection, and decision making.
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

import yaml

from core.performance.profiler import profile_section, profile_time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("BAEL.Brain")


class TaskType(Enum):
    """Types of tasks BAEL can handle."""
    CODE = "code"
    RESEARCH = "research"
    CREATIVE = "creative"
    ANALYSIS = "analysis"
    PLANNING = "planning"
    DEBUGGING = "debugging"
    SECURITY = "security"
    TESTING = "testing"
    DOCUMENTATION = "documentation"
    DEPLOYMENT = "deployment"
    GENERAL = "general"


class Priority(Enum):
    """Task priority levels."""
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4
    BACKGROUND = 5


@dataclass
class Task:
    """Represents a task for BAEL to process."""
    id: str
    type: TaskType
    description: str
    context: Dict[str, Any] = field(default_factory=dict)
    priority: Priority = Priority.MEDIUM
    constraints: List[str] = field(default_factory=list)
    success_criteria: List[str] = field(default_factory=list)
    parent_task_id: Optional[str] = None
    sub_tasks: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    status: str = "pending"
    result: Optional[Any] = None
    error: Optional[str] = None
    iterations: int = 0
    max_iterations: int = 100
    personas_used: List[str] = field(default_factory=list)
    tools_used: List[str] = field(default_factory=list)


@dataclass
class CognitiveState:
    """Represents BAEL's current cognitive state."""
    active_task: Optional[Task] = None
    active_personas: List[str] = field(default_factory=list)
    working_memory: Dict[str, Any] = field(default_factory=dict)
    attention_focus: Optional[str] = None
    confidence_level: float = 0.8
    creativity_mode: str = "balanced"
    energy_level: float = 1.0  # Simulated focus/fatigue
    last_reflection: Optional[datetime] = None
    insights: List[str] = field(default_factory=list)
    current_hypothesis: Optional[str] = None
    alternative_hypotheses: List[str] = field(default_factory=list)


class BaelBrain:
    """
    The Central Brain of BAEL - The Lord of All AI Agents.

    This class orchestrates all cognitive functions, managing:
    - Task decomposition and execution
    - Persona activation and collaboration
    - Tool selection and orchestration
    - Memory access and storage
    - Reasoning and decision making
    - Self-reflection and improvement
    """

    def __init__(self, config_path: str = "config/settings/main.yaml"):
        """Initialize the BAEL Brain."""
        self.config = self._load_config(config_path)
        self.state = CognitiveState()
        self.personas = {}
        self.tools = {}
        self.memory_manager = None
        self.reasoning_engine = None
        self.model_router = None
        self.task_queue: List[Task] = []
        self.completed_tasks: List[Task] = []
        self.session_id = self._generate_session_id()

        logger.info(f"🧠 BAEL Brain initialized - Session: {self.session_id}")

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        path = Path(config_path)
        if path.exists():
            with open(path, 'r') as f:
                return yaml.safe_load(f)
        return {}

    def _generate_session_id(self) -> str:
        """Generate a unique session ID."""
        from uuid import uuid4
        return f"bael-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{str(uuid4())[:8]}"

    async def initialize(self):
        """Initialize all brain components."""
        logger.info("🚀 Initializing BAEL Brain components...")

        # Initialize memory manager
        from core.memory.manager import MemoryManager
        self.memory_manager = MemoryManager(self.config.get('memory', {}))
        await self.memory_manager.initialize()

        # Initialize reasoning engine
        from core.reasoning.engine import ReasoningEngine
        self.reasoning_engine = ReasoningEngine(self.config.get('reasoning', {}))

        # Initialize model router
        from integrations.model_router import ModelRouter
        self.model_router = ModelRouter(self.config.get('models', {}))

        # Load personas
        await self._load_personas()

        # Load tools
        await self._load_tools()

        # Load procedural memory (learned skills)
        await self._load_procedural_memory()

        logger.info("✅ BAEL Brain fully initialized and ready")

    async def _load_personas(self):
        """Load all specialist personas."""
        from personas.loader import PersonaLoader
        loader = PersonaLoader()
        self.personas = await loader.load_all()
        logger.info(f"👥 Loaded {len(self.personas)} specialist personas")

    async def _load_tools(self):
        """Load all available tools."""
        from tools.loader import ToolLoader
        loader = ToolLoader(self.config.get('tools', {}))
        self.tools = await loader.load_all()
        logger.info(f"🔧 Loaded {len(self.tools)} tools")

    async def _load_procedural_memory(self):
        """Load learned procedures and patterns."""
        if self.memory_manager:
            procedures = await self.memory_manager.get_procedural_memory()
            self.state.working_memory['procedures'] = procedures
            logger.info(f"📚 Loaded {len(procedures)} learned procedures")

    # =========================================================================
    # CORE COGNITIVE FUNCTIONS
    # =========================================================================

    @profile_time
    async def think(self, input_text: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Main thinking function - process input and generate response.

        This is the primary entry point for all cognitive processing.
        """
        logger.info(f"💭 Processing: {input_text[:100]}...")

        # Create task from input
        task = await self._create_task(input_text, context)

        # Analyze task and determine approach
        with profile_section("task_analysis"):
            analysis = await self._analyze_task(task)

        # Activate appropriate personas
        personas = await self._activate_personas(analysis)

        # Select tools needed
        tools = await self._select_tools(analysis)

        # Execute reasoning
        result = await self._execute_reasoning(task, analysis, personas, tools)

        # Self-reflect on result
        if self.config.get('core', {}).get('self_reflection', True):
            result = await self._self_reflect(task, result)

        # Store in memory
        await self._store_interaction(task, result)

        # Learn from interaction
        if self.config.get('core', {}).get('learning_enabled', True):
            await self._learn_from_interaction(task, result)

        return result

    async def _create_task(self, input_text: str, context: Optional[Dict]) -> Task:
        """Create a task from user input."""
        # Analyze input to determine task type
        task_type = await self._determine_task_type(input_text)

        task = Task(
            id=f"task-{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
            type=task_type,
            description=input_text,
            context=context or {},
            max_iterations=self.config.get('core', {}).get('max_iterations', 100)
        )

        self.state.active_task = task
        self.task_queue.append(task)

        return task

    async def _determine_task_type(self, input_text: str) -> TaskType:
        """Determine the type of task from input."""
        input_lower = input_text.lower()

        # Simple keyword-based classification (will be enhanced with ML)
        if any(kw in input_lower for kw in ['code', 'implement', 'function', 'class', 'program']):
            return TaskType.CODE
        elif any(kw in input_lower for kw in ['research', 'find', 'search', 'investigate']):
            return TaskType.RESEARCH
        elif any(kw in input_lower for kw in ['create', 'design', 'imagine', 'innovate']):
            return TaskType.CREATIVE
        elif any(kw in input_lower for kw in ['analyze', 'evaluate', 'assess', 'compare']):
            return TaskType.ANALYSIS
        elif any(kw in input_lower for kw in ['plan', 'strategy', 'roadmap', 'schedule']):
            return TaskType.PLANNING
        elif any(kw in input_lower for kw in ['debug', 'fix', 'error', 'bug', 'issue']):
            return TaskType.DEBUGGING
        elif any(kw in input_lower for kw in ['security', 'vulnerability', 'threat', 'audit']):
            return TaskType.SECURITY
        elif any(kw in input_lower for kw in ['test', 'testing', 'coverage', 'qa']):
            return TaskType.TESTING
        elif any(kw in input_lower for kw in ['document', 'docs', 'readme', 'guide']):
            return TaskType.DOCUMENTATION
        elif any(kw in input_lower for kw in ['deploy', 'release', 'ci/cd', 'pipeline']):
            return TaskType.DEPLOYMENT
        else:
            return TaskType.GENERAL

    async def _analyze_task(self, task: Task) -> Dict[str, Any]:
        """Analyze task to determine approach."""
        analysis = {
            'task_id': task.id,
            'type': task.type.value,
            'complexity': await self._assess_complexity(task),
            'required_expertise': await self._identify_expertise(task),
            'required_tools': await self._identify_tools(task),
            'subtasks': await self._decompose_task(task),
            'risks': await self._identify_risks(task),
            'approach': await self._determine_approach(task),
            'estimated_iterations': 0,
            'confidence': 0.0
        }

        # Calculate confidence based on analysis
        analysis['confidence'] = self._calculate_confidence(analysis)

        logger.info(f"📊 Task analysis complete - Complexity: {analysis['complexity']}, Confidence: {analysis['confidence']:.2f}")

        return analysis

    @profile_time
    async def _assess_complexity(self, task: Task) -> int:
        """Assess task complexity on a scale of 1-10."""
        # Factors: length, technical keywords, scope indicators
        complexity = 5  # Base complexity

        desc = task.description.lower()

        # Increase for complex indicators
        if len(task.description) > 500:
            complexity += 1
        if any(kw in desc for kw in ['entire', 'complete', 'full', 'all']):
            complexity += 1
        if any(kw in desc for kw in ['architecture', 'system', 'platform']):
            complexity += 1
        if any(kw in desc for kw in ['optimize', 'scale', 'performance']):
            complexity += 1
        if any(kw in desc for kw in ['security', 'compliance', 'audit']):
            complexity += 1

        return min(10, complexity)

    async def _identify_expertise(self, task: Task) -> List[str]:
        """Identify required expertise areas."""
        expertise = []
        desc = task.description.lower()

        expertise_map = {
            'architect_prime': ['architecture', 'design', 'system', 'scale'],
            'code_master': ['code', 'implement', 'function', 'algorithm'],
            'security_sentinel': ['security', 'vulnerability', 'auth', 'encrypt'],
            'qa_perfectionist': ['test', 'quality', 'coverage', 'bug'],
            'ux_visionary': ['ui', 'ux', 'design', 'user', 'interface'],
            'devops_commander': ['deploy', 'docker', 'kubernetes', 'ci/cd'],
            'data_sage': ['data', 'database', 'ml', 'analytics'],
            'research_oracle': ['research', 'find', 'investigate', 'analyze'],
            'creative_genius': ['create', 'innovate', 'idea', 'design'],
            'strategy_master': ['plan', 'strategy', 'roadmap', 'decision'],
        }

        for persona_id, keywords in expertise_map.items():
            if any(kw in desc for kw in keywords):
                expertise.append(persona_id)

        # Always have at least one expert
        if not expertise:
            expertise.append('code_master')

        return expertise

    async def _identify_tools(self, task: Task) -> List[str]:
        """Identify required tools for the task."""
        tools = []
        desc = task.description.lower()

        tool_map = {
            'code_execution': ['code', 'run', 'execute', 'script', 'program'],
            'web_search': ['search', 'find', 'research', 'look up'],
            'browser': ['website', 'page', 'browse', 'scrape'],
            'file_system': ['file', 'read', 'write', 'save', 'load'],
            'github': ['github', 'repo', 'repository', 'git'],
            'database': ['database', 'sql', 'query', 'data'],
            'api': ['api', 'endpoint', 'request', 'http'],
            'shell': ['terminal', 'command', 'shell', 'bash'],
        }

        for tool_id, keywords in tool_map.items():
            if any(kw in desc for kw in keywords):
                tools.append(tool_id)

        return tools

    async def _decompose_task(self, task: Task) -> List[Dict[str, Any]]:
        """Decompose complex task into subtasks."""
        if await self._assess_complexity(task) < 5:
            return []  # Simple task, no decomposition needed

        # Use reasoning engine to decompose
        if self.reasoning_engine:
            return await self.reasoning_engine.decompose(task)

        return []

    async def _identify_risks(self, task: Task) -> List[Dict[str, Any]]:
        """Identify potential risks in the task."""
        risks = []
        desc = task.description.lower()

        # Common risk patterns
        if any(kw in desc for kw in ['delete', 'remove', 'drop']):
            risks.append({
                'type': 'data_loss',
                'severity': 'high',
                'mitigation': 'Create backup before operation'
            })

        if any(kw in desc for kw in ['password', 'secret', 'key', 'token']):
            risks.append({
                'type': 'security',
                'severity': 'high',
                'mitigation': 'Use secure storage, never log secrets'
            })

        if any(kw in desc for kw in ['production', 'live', 'deploy']):
            risks.append({
                'type': 'deployment',
                'severity': 'high',
                'mitigation': 'Test in staging first, have rollback plan'
            })

        return risks

    async def _determine_approach(self, task: Task) -> str:
        """Determine the best approach for the task."""
        complexity = await self._assess_complexity(task)

        if complexity <= 3:
            return "direct"  # Direct execution
        elif complexity <= 6:
            return "iterative"  # Step-by-step with validation
        else:
            return "collaborative"  # Multi-persona collaboration

    def _calculate_confidence(self, analysis: Dict[str, Any]) -> float:
        """Calculate confidence level for the approach."""
        base_confidence = 0.9

        # Reduce for complexity
        complexity = analysis['complexity']
        base_confidence -= (complexity - 5) * 0.05

        # Reduce for risks
        risk_count = len(analysis['risks'])
        base_confidence -= risk_count * 0.05

        # Increase for known expertise
        if analysis['required_expertise']:
            base_confidence += 0.05

        return max(0.3, min(1.0, base_confidence))

    async def _activate_personas(self, analysis: Dict[str, Any]) -> List[Any]:
        """Activate appropriate personas for the task."""
        required_expertise = analysis['required_expertise']
        active_personas = []

        for persona_id in required_expertise[:5]:  # Max 5 personas
            if persona_id in self.personas:
                persona = self.personas[persona_id]
                await persona.activate()
                active_personas.append(persona)
                self.state.active_personas.append(persona_id)

        logger.info(f"👥 Activated {len(active_personas)} personas: {required_expertise[:5]}")

        return active_personas

    async def _select_tools(self, analysis: Dict[str, Any]) -> List[Any]:
        """Select and prepare tools for the task."""
        required_tools = analysis['required_tools']
        selected_tools = []

        for tool_id in required_tools:
            if tool_id in self.tools:
                tool = self.tools[tool_id]
                selected_tools.append(tool)

        logger.info(f"🔧 Selected {len(selected_tools)} tools: {required_tools}")

        return selected_tools

    async def _execute_reasoning(
        self,
        task: Task,
        analysis: Dict[str, Any],
        personas: List[Any],
        tools: List[Any]
    ) -> Dict[str, Any]:
        """Execute the main reasoning process."""
        approach = analysis['approach']

        if approach == "direct":
            return await self._direct_execution(task, personas, tools)
        elif approach == "iterative":
            return await self._iterative_execution(task, analysis, personas, tools)
        else:
            return await self._collaborative_execution(task, analysis, personas, tools)

    async def _direct_execution(
        self,
        task: Task,
        personas: List[Any],
        tools: List[Any]
    ) -> Dict[str, Any]:
        """Direct execution for simple tasks."""
        # Get response from primary model
        response = await self.model_router.generate(
            prompt=task.description,
            context=task.context,
            model_type='primary'
        )

        return {
            'success': True,
            'response': response,
            'approach': 'direct',
            'iterations': 1
        }

    async def _iterative_execution(
        self,
        task: Task,
        analysis: Dict[str, Any],
        personas: List[Any],
        tools: List[Any]
    ) -> Dict[str, Any]:
        """Iterative execution with validation steps."""
        iterations = 0
        max_iterations = task.max_iterations
        result = None

        while iterations < max_iterations:
            iterations += 1
            task.iterations = iterations

            # Generate response
            response = await self._generate_response(task, personas, tools)

            # Validate response
            validation = await self._validate_response(response, task)

            if validation['valid']:
                result = {
                    'success': True,
                    'response': response,
                    'approach': 'iterative',
                    'iterations': iterations,
                    'validation': validation
                }
                break
            else:
                # Incorporate feedback and try again
                task.context['previous_attempt'] = response
                task.context['feedback'] = validation['feedback']

        return result or {
            'success': False,
            'response': response,
            'approach': 'iterative',
            'iterations': iterations,
            'error': 'Max iterations reached without satisfactory result'
        }

    async def _collaborative_execution(
        self,
        task: Task,
        analysis: Dict[str, Any],
        personas: List[Any],
        tools: List[Any]
    ) -> Dict[str, Any]:
        """Collaborative execution with multiple personas."""
        # Each persona contributes their perspective
        perspectives = []

        for persona in personas:
            perspective = await persona.analyze(task)
            perspectives.append({
                'persona': persona.id,
                'analysis': perspective
            })

        # Synthesize perspectives
        synthesis = await self._synthesize_perspectives(perspectives, task)

        # Generate unified response
        response = await self._generate_unified_response(synthesis, task, tools)

        # Validate with all personas
        validations = []
        for persona in personas:
            validation = await persona.validate(response)
            validations.append(validation)

        return {
            'success': all(v['valid'] for v in validations),
            'response': response,
            'approach': 'collaborative',
            'perspectives': perspectives,
            'synthesis': synthesis,
            'validations': validations
        }

    async def _generate_response(
        self,
        task: Task,
        personas: List[Any],
        tools: List[Any]
    ) -> str:
        """Generate response using selected model and context."""
        # Build prompt with persona context
        prompt = self._build_prompt(task, personas)

        # Select appropriate model
        model_type = self._select_model_type(task)

        # Generate
        response = await self.model_router.generate(
            prompt=prompt,
            context=task.context,
            model_type=model_type,
            tools=[t.to_function() for t in tools] if tools else None
        )

        return response

    def _build_prompt(self, task: Task, personas: List[Any]) -> str:
        """Build prompt with all relevant context."""
        persona_context = ""
        if personas:
            persona_names = [p.name for p in personas]
            persona_context = f"\nActive Experts: {', '.join(persona_names)}\n"

        return f"""
{persona_context}
Task: {task.description}

Context:
{json.dumps(task.context, indent=2) if task.context else 'None'}

Constraints:
{chr(10).join(f'- {c}' for c in task.constraints) if task.constraints else 'None'}

Success Criteria:
{chr(10).join(f'- {c}' for c in task.success_criteria) if task.success_criteria else 'Complete the task thoroughly and accurately'}
"""

    def _select_model_type(self, task: Task) -> str:
        """Select the best model type for the task."""
        model_map = {
            TaskType.CODE: 'code',
            TaskType.CREATIVE: 'creative',
            TaskType.RESEARCH: 'reasoning',
            TaskType.ANALYSIS: 'reasoning',
            TaskType.PLANNING: 'reasoning',
            TaskType.GENERAL: 'primary'
        }
        return model_map.get(task.type, 'primary')

    async def _validate_response(self, response: str, task: Task) -> Dict[str, Any]:
        """Validate the generated response."""
        # Check against success criteria
        if task.success_criteria:
            criteria_met = []
            for criterion in task.success_criteria:
                # Simple check - will be enhanced with semantic validation
                met = criterion.lower() in response.lower()
                criteria_met.append({'criterion': criterion, 'met': met})

            all_met = all(c['met'] for c in criteria_met)

            return {
                'valid': all_met,
                'criteria_results': criteria_met,
                'feedback': 'All criteria met' if all_met else f"Missing: {[c['criterion'] for c in criteria_met if not c['met']]}"
            }

        # Basic validation
        return {
            'valid': len(response) > 50,  # At least some content
            'feedback': 'Response generated'
        }

    async def _synthesize_perspectives(
        self,
        perspectives: List[Dict],
        task: Task
    ) -> Dict[str, Any]:
        """Synthesize multiple persona perspectives."""
        # Combine insights
        combined_insights = []
        for p in perspectives:
            if 'insights' in p['analysis']:
                combined_insights.extend(p['analysis']['insights'])

        # Identify agreements and conflicts
        synthesis = {
            'combined_insights': combined_insights,
            'agreements': [],
            'conflicts': [],
            'unified_approach': ''
        }

        # Use reasoning engine to synthesize
        if self.reasoning_engine:
            synthesis = await self.reasoning_engine.synthesize(perspectives, task)

        return synthesis

    async def _generate_unified_response(
        self,
        synthesis: Dict[str, Any],
        task: Task,
        tools: List[Any]
    ) -> str:
        """Generate unified response from synthesis."""
        prompt = f"""
Based on the collaborative analysis:

Unified Approach: {synthesis.get('unified_approach', '')}

Key Insights:
{chr(10).join(f'- {i}' for i in synthesis.get('combined_insights', []))}

Task: {task.description}

Generate a comprehensive response that incorporates all perspectives and insights.
"""

        response = await self.model_router.generate(
            prompt=prompt,
            context=task.context,
            model_type='primary'
        )

        return response

    async def _self_reflect(self, task: Task, result: Dict[str, Any]) -> Dict[str, Any]:
        """Self-reflect on the result and potentially improve it."""
        reflection_prompt = f"""
Review the following response:

Task: {task.description}
Response: {result.get('response', '')[:2000]}

Self-Reflection Questions:
1. Is this response complete and accurate?
2. Are there any gaps or missing information?
3. Could this be improved? How?
4. What is the confidence level (0-100)?

Provide honest assessment and improvements if needed.
"""

        reflection = await self.model_router.generate(
            prompt=reflection_prompt,
            model_type='reasoning'
        )

        result['reflection'] = reflection
        result['reflected'] = True

        # Extract confidence from reflection
        try:
            if 'confidence' in reflection.lower():
                # Simple extraction - will be enhanced
                import re
                match = re.search(r'(\d+)%?', reflection)
                if match:
                    result['confidence'] = int(match.group(1)) / 100
        except:
            pass

        return result

    async def _store_interaction(self, task: Task, result: Dict[str, Any]):
        """Store the interaction in memory."""
        if self.memory_manager:
            await self.memory_manager.store_episodic({
                'session_id': self.session_id,
                'task_id': task.id,
                'task_type': task.type.value,
                'description': task.description,
                'result': result,
                'timestamp': datetime.now().isoformat()
            })

    async def _learn_from_interaction(self, task: Task, result: Dict[str, Any]):
        """Learn from the interaction and update procedural memory."""
        if not self.memory_manager:
            return

        # Extract learnable patterns
        if result.get('success', False):
            pattern = {
                'task_type': task.type.value,
                'approach': result.get('approach', ''),
                'personas_used': self.state.active_personas.copy(),
                'success_factors': result.get('reflection', ''),
                'learned_at': datetime.now().isoformat()
            }

            await self.memory_manager.store_procedural(pattern)
            logger.info(f"📚 Learned new pattern for {task.type.value} tasks")

    # =========================================================================
    # PUBLIC API
    # =========================================================================

    @profile_time
    async def process(self, input_text: str, context: Optional[Dict] = None) -> str:
        """
        Main public API - process input and return response.

        Args:
            input_text: User input/query
            context: Optional context dictionary

        Returns:
            Generated response string
        """
        result = await self.think(input_text, context)
        return result.get('response', 'I apologize, but I could not generate a response.')

    async def spawn_agent(self, task_description: str, persona: Optional[str] = None) -> 'BaelAgent':
        """Spawn a specialized sub-agent for a task."""
        from core.agents.agent import BaelAgent

        agent = BaelAgent(
            brain=self,
            task=task_description,
            persona=persona
        )
        await agent.initialize()

        return agent

    async def research(self, topic: str, depth: int = 3) -> Dict[str, Any]:
        """Conduct deep research on a topic."""
        from research.orchestrator import ResearchOrchestrator

        orchestrator = ResearchOrchestrator(self)
        return await orchestrator.comprehensive_research(topic, depth=depth)

    async def execute_code(self, code: str, language: str = "python") -> Dict[str, Any]:
        """Execute code and return results."""
        if 'code_execution' in self.tools:
            return await self.tools['code_execution'].execute(code, language)
        return {'error': 'Code execution tool not available'}

    def get_state(self) -> Dict[str, Any]:
        """Get current brain state."""
        return {
            'session_id': self.session_id,
            'active_task': self.state.active_task.id if self.state.active_task else None,
            'active_personas': self.state.active_personas,
            'confidence': self.state.confidence_level,
            'creativity_mode': self.state.creativity_mode,
            'energy_level': self.state.energy_level,
            'tasks_completed': len(self.completed_tasks),
            'tasks_pending': len(self.task_queue)
        }

    async def shutdown(self):
        """Gracefully shutdown the brain."""
        logger.info("🛑 Shutting down BAEL Brain...")

        # Save memory
        if self.memory_manager:
            await self.memory_manager.save()

        # Deactivate personas
        for persona_id in self.state.active_personas:
            if persona_id in self.personas:
                await self.personas[persona_id].deactivate()

        # Close tools
        for tool in self.tools.values():
            if hasattr(tool, 'close'):
                await tool.close()

        logger.info("✅ BAEL Brain shutdown complete")


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

async def main():
    """Main entry point for testing."""
    brain = BaelBrain()
    await brain.initialize()

    # Test interaction
    response = await brain.process("Hello, explain what you are capable of.")
    print(response)

    await brain.shutdown()


if __name__ == "__main__":
    asyncio.run(main())

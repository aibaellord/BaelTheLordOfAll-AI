# Phase 4 Quick Reference

## Installation & Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Run Phase 4 demo
python examples/phase4_demo.py
```

## Quick Examples

### 1. Create Autonomous Agent

```python
from core.agents import AdvancedAutonomousAgent, AgentCapability

agent = AdvancedAutonomousAgent(
    agent_id="agent_001",
    name="MyAgent",
    capabilities=[
        AgentCapability(
            name="data_analysis",
            description="Analyze data and find insights",
            required_tools=["pandas", "numpy"]
        )
    ]
)

# Execute autonomously - agent handles everything
result = await agent.execute_autonomous({
    "name": "analyze_sales",
    "type": "data_analysis",
    "parameters": {"timeframe": "last_month"}
})
```

### 2. Use Fabric Patterns

```python
from core.fabric import FabricIntegration

fabric = FabricIntegration(llm_client=your_llm)

# Extract wisdom from content
wisdom = await fabric.execute_pattern(
    "extract_wisdom",
    "Long article or content here..."
)

# Review code
review = await fabric.execute_pattern(
    "review_code",
    code_string
)

# Get pattern recommendations
patterns = fabric.recommend_pattern("I need to analyze security")
# Returns: ["analyze_threat_report", "check_agreement", ...]
```

### 3. Natural Language Commands

```python
from core.cli.natural_language import NaturalLanguageCLI

cli = NaturalLanguageCLI()

# Just speak naturally
result = await cli.process("show me the API performance from last week")
result = await cli.process("deploy the auth service to production")
result = await cli.process("create a new monitoring agent for database")

# CLI automatically:
# - Recognizes intent
# - Extracts entities
# - Executes appropriate action
# - Returns natural language response
```

### 4. Multi-Agent Coordination

```python
from core.coordination import (
    CoordinationEngine,
    CoordinatedTask,
    CoordinationStrategy,
    TaskPriority
)

# Create coordination engine
engine = CoordinationEngine(strategy=CoordinationStrategy.CONSENSUS)

# Register agents
engine.register_agent("agent_1", agent1, AgentRole.SPECIALIST)
engine.register_agent("agent_2", agent2, AgentRole.LEADER)

# Create complex task
task = CoordinatedTask(
    task_id="task_001",
    description="Analyze system and deploy improvements",
    priority=TaskPriority.HIGH,
    required_capabilities=["analysis", "deployment"],
    subtasks=[
        {"name": "analyze", "type": "analysis"},
        {"name": "deploy", "type": "deployment"}
    ]
)

# Agents self-organize and execute
result = await engine.coordinate_task(task)
```

### 5. Agent Swarm

```python
from core.agents import AgentSwarm

swarm = AgentSwarm("my_swarm")

# Add agents
swarm.add_agent(agent1)
swarm.add_agent(agent2)
swarm.add_agent(agent3)

# Distribute tasks across swarm
tasks = [
    {"name": "task_1", "type": "analysis"},
    {"name": "task_2", "type": "processing"},
    {"name": "task_3", "type": "reporting"}
]

results = await swarm.execute_distributed(tasks)

# Get swarm statistics
stats = swarm.get_swarm_stats()
print(f"Success rate: {stats['average_success_rate']:.2%}")
```

## Agent Capabilities

### Self-Healing

Agents automatically recover from errors using 6 strategies:

1. **Retry** - Try again with exponential backoff
2. **Rollback** - Revert to previous state
3. **Alternative** - Use different approach
4. **Escalate** - Delegate to more capable agent
5. **Learn & Adapt** - Learn from error and retry
6. **Collaborative Solve** - Get help from peer agents

```python
# Automatic - no code needed
# Agent handles all errors autonomously
result = await agent.execute_autonomous(task)
# If error occurs, agent automatically:
# 1. Tries to recover
# 2. Learns from error
# 3. Never makes same mistake again
```

### Learning

Agents learn from every execution:

```python
# After execution
stats = agent.get_stats()

print(f"Total executions: {stats['total_executions']}")
print(f"Success rate: {stats['success_rate']:.2%}")
print(f"Learned patterns: {stats['learned_patterns']}")

# Agent automatically:
# - Stores execution memory
# - Extracts patterns
# - Optimizes future executions
# - Adjusts exploration rate
```

### Collaboration

Agents work together:

```python
# Add peer agents
agent1.add_peer_agent(agent2)
agent1.add_peer_agent(agent3)

# When agent1 gets stuck, it automatically:
# 1. Checks peer capabilities
# 2. Finds best peer for task
# 3. Delegates to peer
# 4. Learns from peer's success
```

## Fabric Patterns Reference

### Analysis

- `analyze_claims` - Verify factual claims
- `analyze_paper` - Review research papers
- `analyze_tech_impact` - Technology impact

### Extraction

- `extract_wisdom` - Key insights and wisdom
- `extract_ideas` - Organize ideas
- `extract_patterns` - Recurring themes
- `extract_questions` - Important questions

### Summarization

- `summarize` - Comprehensive summary
- `summarize_lecture` - Lecture summary
- `summarize_micro` - Ultra-concise (1-2 sentences)

### Code

- `improve_code` - Suggest improvements
- `review_code` - Comprehensive review
- `explain_code` - Plain language explanation

### Security

- `analyze_threat_report` - Cybersecurity threats
- `check_agreement` - Review agreements

### Writing

- `improve_writing` - Enhance quality
- `write_essay` - Structured essay

### Learning

- `create_quiz` - Generate quiz
- `explain_like_5` - Simple explanations

### Decision

- `create_decision_analysis` - Analyze options
- `rate_content` - Evaluate quality

### Creativity

- `create_story` - Engaging narratives
- `create_idea_compass` - Multi-angle ideation

## Coordination Strategies

### When to Use Each

**Consensus** - Critical decisions requiring agreement

```python
engine = CoordinationEngine(strategy=CoordinationStrategy.CONSENSUS)
# Agents vote on best approach
# Good for: Important decisions, unclear paths
```

**Auction** - Optimal resource allocation

```python
engine = CoordinationEngine(strategy=CoordinationStrategy.AUCTION)
# Agents bid based on confidence/cost
# Good for: Load balancing, resource optimization
```

**Swarm** - Parallel independent tasks

```python
engine = CoordinationEngine(strategy=CoordinationStrategy.SWARM)
# Agents self-organize
# Good for: Many similar tasks, horizontal scaling
```

**Leader-Follower** - Hierarchical workflows

```python
engine = CoordinationEngine(strategy=CoordinationStrategy.LEADER_FOLLOWER)
# Leader directs followers
# Good for: Clear hierarchy, sequential dependencies
```

**Hierarchical** - Multi-level organization

```python
engine = CoordinationEngine(strategy=CoordinationStrategy.HIERARCHICAL)
# Coordinator → Specialists → Workers
# Good for: Complex multi-tier systems
```

## Natural Language Intents

### Query

- "show me the status"
- "what errors happened?"
- "list all services"

### Action

- "restart the server"
- "run the backup"
- "start the worker"

### Analysis

- "analyze performance"
- "check the logs"
- "review the code"

### Creation

- "create a new agent"
- "make a backup"
- "generate a report"

### Deployment

- "deploy to production"
- "rollback the changes"
- "scale up the service"

### Monitoring

- "monitor the API"
- "watch for errors"
- "track the metrics"

### Configuration

- "enable debug mode"
- "set the timeout to 30s"
- "configure the database"

### Help

- "how do I deploy?"
- "what can you do?"
- "explain agents"

## Common Patterns

### Pattern 1: Autonomous Monitoring

```python
# Create monitoring agent
monitor_agent = AdvancedAutonomousAgent(
    agent_id="monitor_001",
    name="SystemMonitor",
    capabilities=[
        AgentCapability(
            name="health_check",
            description="Monitor system health",
            required_tools=["prometheus", "grafana"]
        )
    ]
)

# Run continuously
while True:
    result = await monitor_agent.execute_autonomous({
        "name": "check_health",
        "type": "health_check"
    })

    # Agent automatically:
    # - Detects issues
    # - Analyzes causes
    # - Applies fixes
    # - Learns from incidents

    await asyncio.sleep(60)
```

### Pattern 2: Code Review Pipeline

```python
# Natural language trigger
await cli.process("review all new pull requests")

# System automatically:
# 1. Finds new PRs
# 2. Creates review tasks
# 3. Coordinates agents
# 4. Applies Fabric patterns
# 5. Provides feedback
```

### Pattern 3: Incident Response

```python
# When incident occurs
task = CoordinatedTask(
    description="Respond to production incident",
    priority=TaskPriority.CRITICAL,
    required_capabilities=["diagnosis", "remediation"]
)

result = await engine.coordinate_task(task)

# Agents automatically:
# 1. Detect (monitoring agent)
# 2. Analyze (analysis agent)
# 3. Fix (ops agent)
# 4. Validate (test agent)
# 5. Document (knowledge agent)
```

### Pattern 4: Content Processing

```python
# Process content with multiple patterns
content = "Long article or document..."

# Extract wisdom
wisdom = await fabric.execute_pattern("extract_wisdom", content)

# Get ideas
ideas = await fabric.execute_pattern("extract_ideas", content)

# Summarize
summary = await fabric.execute_pattern("summarize", content)

# All together
insights = {
    "wisdom": wisdom,
    "ideas": ideas,
    "summary": summary
}
```

## Debugging & Monitoring

### Check Agent Stats

```python
stats = agent.get_stats()

print(f"Agent: {stats['name']}")
print(f"State: {stats['state']}")
print(f"Total executions: {stats['total_executions']}")
print(f"Success rate: {stats['success_rate']:.2%}")
print(f"Learned patterns: {stats['learned_patterns']}")
print(f"Error count: {stats['error_count']}")
print(f"Recovery attempts: {stats['recovery_attempts']}")
print(f"Collaboration count: {stats['collaboration_count']}")
print(f"Peer agents: {stats['peer_agents']}")
```

### Check Coordination

```python
coord_stats = coordination.get_coordination_stats()

print(f"Total coordinations: {coord_stats['total_coordinations']}")
print(f"Successful: {coord_stats['successful']}")
print(f"Success rate: {coord_stats['success_rate']:.2%}")
print(f"Registered agents: {coord_stats['registered_agents']}")
print(f"Strategy: {coord_stats['strategy']}")
```

### Check Fabric Usage

```python
fabric_stats = fabric.get_usage_stats()

print(f"Total patterns: {fabric_stats['total_patterns']}")
print(f"Total uses: {fabric_stats['total_uses']}")
print(f"Unique patterns used: {fabric_stats['unique_patterns_used']}")
print(f"Most used: {fabric_stats['most_used']}")
```

## Performance Tips

1. **Agent Specialization**: Create specialized agents for specific tasks
2. **Capability Matching**: Ensure task requirements match agent capabilities
3. **Learning Period**: Give agents 10+ executions to learn patterns
4. **Swarm Size**: 3-10 agents per swarm for optimal coordination
5. **Pattern Selection**: Use specific patterns rather than generic ones
6. **Context Preservation**: Keep CLI context for multi-turn conversations
7. **Coordination Strategy**: Match strategy to task characteristics

## Troubleshooting

### Agent Not Learning

```python
# Check execution memory
print(f"Executions: {len(agent.execution_memory)}")
print(f"Patterns: {len(agent.learned_patterns)}")

# Need more executions to establish patterns (10+)
```

### Low Success Rate

```python
# Check agent capabilities
for cap_name, cap in agent.capabilities.items():
    print(f"{cap_name}: success={cap.success_rate:.2%}, uses={cap.usage_count}")

# May need more capable agents or better task matching
```

### Coordination Failing

```python
# Check agent availability
capable_agents = engine._find_capable_agents(task.required_capabilities)
print(f"Capable agents: {len(capable_agents)}")

# Need agents with matching capabilities
```

### Natural Language Not Understanding

```python
# Check intent confidence
result = await cli.process(user_input)
print(f"Intent: {result['intent']}")
print(f"Confidence: {result['confidence']:.2f}")
print(f"Entities: {result['entities']}")

# If confidence < 0.7, rephrase with more keywords
```

## Best Practices

1. ✅ Let agents learn before critical tasks
2. ✅ Use appropriate coordination strategy
3. ✅ Match Fabric patterns to task type
4. ✅ Provide clear natural language commands
5. ✅ Monitor agent statistics regularly
6. ✅ Create specialized agents for complex domains
7. ✅ Enable peer connections for collaboration
8. ✅ Use swarms for parallel workloads
9. ✅ Chain Fabric patterns for complex reasoning
10. ✅ Trust the autonomous system - it learns!

---

**Phase 4 Complete - BAEL is now the most advanced agent orchestration system! 🚀**

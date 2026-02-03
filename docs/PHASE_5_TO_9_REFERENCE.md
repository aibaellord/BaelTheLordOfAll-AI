# BAEL Phase 5-9: Technical Reference Guide

**Version:** 5.0.0
**Completion Date:** February 2, 2026
**Status:** ✅ PRODUCTION READY

---

## Quick Navigation

- [Phase 5: Tool Ecosystem](#phase-5-tool-ecosystem)
- [Phase 6: Advanced Memory](#phase-6-advanced-memory)
- [Phase 7: Self-Healing](#phase-7-self-healing)
- [Phase 8: Advanced Scheduler](#phase-8-advanced-scheduler)
- [Phase 9: Deployment](#phase-9-deployment)
- [Integration Examples](#integration-examples)
- [Troubleshooting](#troubleshooting)

---

## Phase 5: Tool Ecosystem

### Quick Start

```python
from core.integrations import ToolOrchestrator, ToolAction

orchestrator = ToolOrchestrator()

# Sync all tools
result = await orchestrator.sync_all_tools()
print(f"Synced {result['results']['github']['pull_requests']} PRs")
```

### Tool Configuration

Each tool requires initialization with credentials:

```python
from core.integrations import (
    GitHubIntegration,
    SlackIntegration,
    DiscordIntegration,
    JiraIntegration,
    NotionIntegration
)

# GitHub
github = GitHubIntegration(token="ghp_...", repo="owner/repo")

# Slack
slack = SlackIntegration(bot_token="xoxb-...", workspace="myworkspace")

# Discord
discord = DiscordIntegration(bot_token="MjAxOTM...", guild_id="123456789")

# Jira
jira = JiraIntegration(base_url="https://company.atlassian.net", api_token="...")

# Notion
notion = NotionIntegration(api_key="secret_...", database_id="...")
```

### Common Operations

**GitHub Operations**

```python
# Get PRs
prs = await github.get_pull_requests(state="open")

# Review PR
review = await github.review_pull_request(pr_id, {
    "body": "Looks good!",
    "event": "APPROVE"
})

# Trigger workflow
workflow = await github.trigger_actions("deploy.yml", {
    "environment": "staging"
})
```

**Slack Operations**

```python
# Send message
await slack.send_message("#alerts", "Deployment complete!")

# Send notification
await slack.send_notification(
    title="GitHub Status",
    message="3 PRs ready for review",
    priority="high"
)

# Interactive message
await slack.create_interactive_message(
    channel="#ops",
    message="Deploy to production?",
    actions=[
        {"type": "button", "text": "Deploy", "value": "deploy"},
        {"type": "button", "text": "Cancel", "value": "cancel"}
    ]
)
```

**Jira Operations**

```python
# Create issue
issue = await jira.create_issue(
    project="PROJ",
    issue_type="Bug",
    summary="API timeout",
    description="POST /api/users times out",
    priority="high",
    assignee="john.doe"
)

# Update issue
updated = await jira.update_issue("PROJ-123", {
    "status": "In Progress",
    "assignee": "jane.smith"
})

# Get issues
issues = await jira.get_issues(
    project="PROJ",
    status="To Do"
)
```

### Custom Tool Integration

Add support for additional tools:

```python
class CustomToolIntegration:
    def __init__(self, api_key):
        self.api_key = api_key

    async def custom_operation(self):
        # Implement your integration
        pass

# Register with orchestrator
orchestrator.tool_map["custom"] = CustomToolIntegration(api_key)
```

---

## Phase 6: Advanced Memory

### Quick Start

```python
from core.memory import (
    AdvancedMemorySystem,
    LearningSystem,
    MemoryType
)

memory = AdvancedMemorySystem()
learning = LearningSystem(memory)

# Add memory
m_id = memory.add_memory(
    "Deployment succeeded with blue-green strategy",
    MemoryType.PROCEDURAL
)

# Learn from event
learning.learn_from_success(
    "deployment",
    "blue_green",
    {"services": 3},
    quality=0.98
)

# Get suggestions
suggestions = learning.generate_optimization_suggestions()
```

### Memory Types

```python
# Episodic: Specific events
memory.add_memory(
    "Database cluster failure on 2026-02-01",
    MemoryType.EPISODIC,
    metadata={"timestamp": "2026-02-01T12:30:00"}
)

# Semantic: Facts and knowledge
memory.add_memory(
    "PostgreSQL 14 supports logical replication",
    MemoryType.SEMANTIC,
    metadata={"source": "documentation"}
)

# Procedural: How-to knowledge
memory.add_memory(
    "To scale database: 1. Create replica 2. Wait for sync 3. Failover",
    MemoryType.PROCEDURAL
)

# Emotional: Context and sentiment
memory.add_memory(
    "Last deployment was stressful but successful",
    MemoryType.EMOTIONAL,
    metadata={"sentiment": "mixed", "stress_level": 0.8}
)

# Working: Short-term context
memory.add_memory(
    "Currently deploying to staging",
    MemoryType.WORKING,
    metadata={"cache": True}
)
```

### Knowledge Graph

```python
# Create nodes
api_id = memory.add_knowledge_node(
    "service", "API Service",
    {"type": "backend", "language": "python"}
)

db_id = memory.add_knowledge_node(
    "database", "PostgreSQL",
    {"version": "14", "role": "primary"}
)

cache_id = memory.add_knowledge_node(
    "cache", "Redis",
    {"version": "7.0", "role": "cache"}
)

# Create relationships
memory.add_knowledge_edge(api_id, db_id, "uses_for_data")
memory.add_knowledge_edge(api_id, cache_id, "uses_for_caching")
memory.add_knowledge_edge(db_id, cache_id, "invalidates")

# Query relationships
related = memory.get_related_knowledge(api_id, depth=2)
# Returns all connected nodes within 2 hops
```

### Learning System

```python
# Track successful strategies
learning.learn_from_success(
    task_type="deployment",
    strategy_used="blue_green",
    context={"zones": 3, "services": 5},
    result_quality=0.95
)

# Track failures
learning.learn_from_failure(
    task_type="sync",
    strategy_used="sequential",
    error="rate_limit_exceeded",
    context={"api": "github"}
)

# Get performance metrics
stats = learning.get_learning_stats()
# Returns:
# {
#   "total_learning_events": 150,
#   "patterns_discovered": 45,
#   "strategies_tracked": 12,
#   "suggestions_generated": 8
# }

# Get optimization suggestions
suggestions = learning.generate_optimization_suggestions()
# [
#   {
#     "type": "low_success_rate",
#     "pattern": "sync_sequential",
#     "success_rate": 0.45,
#     "recommendation": "Try parallel sync instead"
#   },
#   ...
# ]
```

---

## Phase 7: Self-Healing

### Quick Start

```python
from core.resilience import (
    HealthMonitor,
    HealthStatus,
    AutoRemediationEngine
)

monitor = HealthMonitor()

# Register remediation
monitor.register_remediation(
    component_pattern="database",
    condition_func=lambda m: m.error_rate > 0.2,
    action="restart",
    params={"graceful": True}
)

# Report health
monitor.report_health(
    "database",
    HealthStatus.DEGRADED,
    error_rate=0.25,
    latency_p99=1000
)

# Monitor and heal
await monitor.monitor_and_heal()

# Get system health
health = monitor.get_system_health()
```

### Health Status Levels

```python
from core.resilience import HealthStatus

HealthStatus.HEALTHY      # Error rate < 1%, latency OK
HealthStatus.DEGRADED     # Error rate 1-5%, elevated latency
HealthStatus.FAILING      # Error rate 5-20%, high latency
HealthStatus.CRITICAL     # Error rate > 20%, very high latency
```

### Remediation Actions

```python
# Action 1: Restart
# Gracefully restart service
params={"graceful": True, "drain_timeout": 30}

# Action 2: Rollback
# Revert to previous version
params={"version": "1.2.3"}

# Action 3: Scale
# Scale up or down
params={"direction": "up", "amount": 2}

# Action 4: Redirect
# Redirect traffic away
params={"target": "backup_instance"}

# Action 5: Purge Cache
# Clear corrupted cache
params={"scope": "all"}

# Action 6: Reset Connection
# Reset connection pool
params={"pool_size": 10}
```

### Circuit Breaker

```python
from core.resilience import CircuitBreakerManager

cb_manager = CircuitBreakerManager()

# Use circuit breaker
if cb_manager.can_call("api_service"):
    try:
        result = await call_api()
        cb_manager.record_success("api_service")
    except Exception as e:
        cb_manager.record_failure("api_service")
        raise

# States:
# CLOSED → Normal operation
# OPEN → Blocking all calls (after 5 failures)
# HALF_OPEN → Testing recovery (after timeout)
```

### Health Metrics

```python
from core.resilience import HealthMetric

metric = HealthMetric(
    component_name="api_service",
    status=HealthStatus.DEGRADED,
    last_check=datetime.now(),
    error_count=12,
    recovery_attempts=3,
    error_rate=0.05,
    latency_p99=250
)
```

---

## Phase 8: Advanced Scheduler

### Quick Start

```python
from core.scheduling import (
    AdvancedScheduler,
    WorkflowStep,
    TriggerType
)

scheduler = AdvancedScheduler()

# Create workflow
steps = [
    WorkflowStep("1", "Deploy", "deploy", {"target": "prod"}),
    WorkflowStep("2", "Test", "test", {"suite": "integration"}, depends_on=["1"]),
    WorkflowStep("3", "Notify", "notify", {"channel": "slack"}, depends_on=["2"])
]

workflow_id = scheduler.create_workflow(
    "Production Deployment",
    steps
)

# Add triggers
scheduler.add_cron_trigger(workflow_id, "0 2 * * *")
scheduler.add_event_trigger(workflow_id, "github.push.main")
scheduler.add_metric_trigger(workflow_id, "error_rate", 0.1, ">")
scheduler.add_ai_predicted_trigger(workflow_id, ml_model.predict, 0.8)

# Execute
execution_id = await scheduler.execute_workflow(workflow_id)
```

### Trigger Types

**1. Cron Triggers**

```python
# Run at 2 AM daily
scheduler.add_cron_trigger(workflow_id, "0 2 * * *")

# Run every 15 minutes
scheduler.add_cron_trigger(workflow_id, "*/15 * * * *")

# Run every Monday at noon
scheduler.add_cron_trigger(workflow_id, "0 12 * * 1")
```

**2. Event Triggers**

```python
# Run on GitHub push to main
scheduler.add_event_trigger(workflow_id, "github.push.main")

# Run on Slack command
scheduler.add_event_trigger(workflow_id, "slack.command.deploy")

# Run on pull request
scheduler.add_event_trigger(workflow_id, "github.pull_request")
```

**3. Condition Triggers**

```python
# Run if custom condition met
scheduler.add_condition_trigger(
    workflow_id,
    lambda ctx: ctx.get("error_count", 0) > 100,
    check_interval=60
)

# Run if database is healthy
scheduler.add_condition_trigger(
    workflow_id,
    lambda ctx: ctx.get("db_health") == "healthy"
)
```

**4. Metric Triggers**

```python
# Run if CPU > 80%
scheduler.add_metric_trigger(workflow_id, "cpu", 80, ">")

# Run if latency < 100ms
scheduler.add_metric_trigger(workflow_id, "latency", 100, "<")

# Run if memory == critical
scheduler.add_metric_trigger(workflow_id, "memory", "critical", "==")
```

**5. AI-Predicted Triggers**

```python
# Run if ML model predicts > 80% probability
def predict_failure(context):
    return model.predict(context)

scheduler.add_ai_predicted_trigger(
    workflow_id,
    predict_failure,
    threshold=0.8
)
```

### Workflow Statistics

```python
# Get workflow stats
stats = scheduler.get_workflow_stats(workflow_id)
# {
#   "name": "Production Deployment",
#   "execution_count": 45,
#   "success_count": 44,
#   "failure_count": 1,
#   "success_rate": 97.8,
#   "triggers": 4
# }

# Get overall scheduler stats
stats = scheduler.get_scheduler_stats()
# {
#   "total_workflows": 8,
#   "total_triggers": 25,
#   "success_rate": 96.5,
#   "active_executions": 2,
#   "triggers_by_type": {...}
# }
```

---

## Phase 9: Deployment

### Quick Start

```python
from core.deployment import DeploymentOrchestrator, DeploymentTarget

orchestrator = DeploymentOrchestrator()

# Deploy to Docker Compose
result = await orchestrator.one_command_deploy(
    target=DeploymentTarget.DOCKER_COMPOSE,
    environment="staging",
    name="bael"
)

print(f"Status: {result['status']}")
print(f"Logs: {result['logs']}")
```

### Deployment Targets

```python
from core.deployment import DeploymentTarget

# Local development
await orchestrator.one_command_deploy(target=DeploymentTarget.LOCAL)

# Docker container
await orchestrator.one_command_deploy(target=DeploymentTarget.DOCKER)

# Docker Compose stack
await orchestrator.one_command_deploy(target=DeploymentTarget.DOCKER_COMPOSE)

# Kubernetes cluster
await orchestrator.one_command_deploy(target=DeploymentTarget.KUBERNETES)

# AWS (ECS/EC2)
await orchestrator.one_command_deploy(target=DeploymentTarget.AWS)

# Google Cloud (Cloud Run)
await orchestrator.one_command_deploy(target=DeploymentTarget.GCP)

# Azure (Container Instances)
await orchestrator.one_command_deploy(target=DeploymentTarget.AZURE)

# Heroku
await orchestrator.one_command_deploy(target=DeploymentTarget.HEROKU)

# Custom infrastructure
await orchestrator.one_command_deploy(target=DeploymentTarget.CUSTOM)
```

### Deployment Logs

```python
# Get deployment status
status = orchestrator.get_deployment_status(deployment_id)
# {
#   "status": "completed",
#   "target": "docker_compose",
#   "steps_completed": 12,
#   "steps_failed": 0
# }

# Get detailed logs
logs = orchestrator.get_deployment_logs(deployment_id)
# [
#   "Validating configuration...",
#   "Building Docker image...",
#   "Starting services...",
#   "Running health checks...",
#   ...
# ]

# Get deployment history
history = orchestrator.get_deployment_history()

# Get statistics
stats = orchestrator.get_deployment_stats()
# {
#   "total_deployments": 15,
#   "successful": 14,
#   "failed": 1,
#   "success_rate": 93.3
# }
```

---

## Integration Examples

### Complete Multi-Tool Workflow

```python
async def complete_workflow():
    # Initialize all systems
    orchestrator = ToolOrchestrator()
    memory = AdvancedMemorySystem()
    learning = LearningSystem(memory)
    monitor = HealthMonitor()
    scheduler = AdvancedScheduler()
    deployment = DeploymentOrchestrator()

    # Step 1: Sync tools
    await orchestrator.sync_all_tools()

    # Step 2: Learn from past
    learning.learn_from_success("deployment", "blue_green", {}, 0.95)

    # Step 3: Deploy with confidence
    result = await deployment.one_command_deploy(
        target=DeploymentTarget.DOCKER_COMPOSE
    )

    # Step 4: Monitor health
    monitor.report_health("api", HealthStatus.HEALTHY, 0.01, 50)

    # Step 5: Schedule post-deploy tasks
    workflow_id = scheduler.create_workflow("Post-Deploy", [...])
    await scheduler.execute_workflow(workflow_id)

    # Step 6: Notify stakeholders
    await orchestrator.slack.send_message(
        "#deployments",
        f"Deployment complete! Status: {result['status']}"
    )
```

### Error Recovery Workflow

```python
async def handle_failure():
    # Detect issue
    monitor.report_health("database", HealthStatus.CRITICAL, 0.5, 5000)

    # Learn what went wrong
    learning.learn_from_failure("deployment", "sequential", "timeout", {})

    # Get healing suggestions
    suggestions = monitor.remediation_engine.get_suggestions()

    # Apply remediation
    await monitor.remediation_engine._restart_service("database", {})

    # Notify team
    await slack.send_notification(
        "Database Failure",
        "Auto-restarted, monitoring recovery",
        "critical"
    )

    # Schedule recovery verification
    scheduler.add_condition_trigger(
        verification_workflow,
        lambda ctx: ctx.get("db_health") == "healthy"
    )
```

---

## Troubleshooting

### Tool Integration Issues

**Problem:** Tool sync failing

```python
# Check if tool is enabled
orchestrator.tool_map["github"].enabled = True

# Check credentials
orchestrator.github.token  # Should be set

# Test connection
result = await orchestrator.github.get_pull_requests()
```

**Problem:** Slack message not sending

```python
# Verify token and workspace
slack = SlackIntegration(bot_token, workspace)

# Check channel exists
await slack.send_message("#test", "test")

# Check bot permissions in Slack
```

### Memory Issues

**Problem:** Memory getting full

```python
# Check memory stats
stats = memory.get_stats()
print(f"Total memories: {stats['total_memories']}")

# Implement memory cleanup
memory.memories = {
    k: v for k, v in memory.memories.items()
    if v.relevance_score > 0.1
}
```

**Problem:** Knowledge graph growing too large

```python
# Prune infrequent relationships
edges_to_remove = [
    e for e in memory.knowledge_edges
    if e.weight < 0.5
]

for edge in edges_to_remove:
    memory.knowledge_edges.remove(edge)
```

### Scheduling Issues

**Problem:** Workflow not executing

```python
# Check if enabled
workflow = scheduler.workflows[workflow_id]
print(f"Enabled: {workflow['enabled']}")

# Check triggers
triggers = [t for t in scheduler.triggers.values()
           if t.config.get('workflow_id') == workflow_id]
print(f"Triggers: {len(triggers)}")

# Check execution history
history = scheduler.execution_history
```

**Problem:** Cron trigger not firing

```python
# Check cron expression syntax
# Format: minute hour day month dayofweek

# Test condition manually
context = {"error_rate": 0.05}
should_fire = trigger.config["condition_func"](context)
print(f"Should fire: {should_fire}")
```

### Deployment Issues

**Problem:** Deployment hanging

```python
# Check logs
logs = orchestrator.get_deployment_logs(deployment_id)
print(logs[-5:])  # Last 5 logs

# Check if service is responsive
import asyncio
await asyncio.sleep(30)
health = await check_health()
```

**Problem:** Rollback failed

```python
# Check rollback logs
status = orchestrator.get_deployment_status(deployment_id)
print(status.get('error'))

# Try manual rollback
await orchestrator._rollback_deployment({})
```

---

## Performance Tuning

### Memory System

- Limit memory entries: `max_memories=10000`
- Increase relevance decay: `decay_factor=0.9`
- Reduce knowledge graph depth: `depth=1`

### Scheduler

- Reduce trigger check interval: `check_interval=30`
- Limit concurrent workflows: `max_concurrent=3`
- Increase timeout for long tasks: `timeout=600`

### Health Monitor

- Reduce health check interval: `interval=10`
- Increase remediation threshold: `error_rate_threshold=0.5`
- Disable chaos tests in production

### Deployment

- Skip some validation steps in dev
- Use incremental deployments
- Enable caching for large images

---

## Best Practices

1. **Always backup** before deploying
2. **Test triggers** before using in production
3. **Monitor learning** suggestions before applying
4. **Verify health** before declaring operational
5. **Document** custom integrations
6. **Log everything** for troubleshooting
7. **Test failover** regularly
8. **Review** memory growth monthly

---

## Additional Resources

- **PHASE_5_TO_9_COMPLETE.md** - Full technical documentation
- **examples/phase5_to_9_demo.py** - Complete working examples
- **STATUS_UPDATED.md** - Project status and metrics
- **PHASE_10_GLOBAL_DISTRIBUTION.md** - Next phase planning

---

**Version:** 5.0.0
**Last Updated:** February 2, 2026
**Status:** ✅ PRODUCTION READY

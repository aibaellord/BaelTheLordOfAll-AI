"""Phase 5-7: Complete System Integration Demo

This demo shows all systems working together:
- Phase 5: Tool Ecosystem Integration (20+ tools)
- Phase 6: Advanced Memory & Learning
- Phase 7: Self-Healing Infrastructure
- Phase 8: Advanced Scheduling & Automation
- Phase 9: One-Command Deployment
"""

import asyncio
import logging
from datetime import datetime

from core.deployment.orchestrator import (DeploymentOrchestrator,
                                          DeploymentStatus, DeploymentTarget)
# Import all Phase 5+ systems
from core.integrations.tools import ToolAction, ToolOrchestrator
from core.memory.advanced_memory import (AdvancedMemorySystem, LearningSystem,
                                         MemoryType)
from core.resilience.self_healing import (AutoRemediationEngine, HealthMonitor,
                                          HealthStatus)
from core.scheduling.advanced_scheduler import (AdvancedScheduler, TriggerType,
                                                WorkflowStep)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Phase5To9System:
    """Integrated Phase 5-9 system."""

    def __init__(self):
        """Initialize all Phase 5-9 systems."""
        logger.info("Initializing Phase 5-9 integrated system")

        # Phase 5: Tool Ecosystem
        self.tool_orchestrator = ToolOrchestrator()

        # Phase 6: Advanced Memory & Learning
        self.memory = AdvancedMemorySystem()
        self.learning = LearningSystem(self.memory)

        # Phase 7: Self-Healing Infrastructure
        self.health_monitor = HealthMonitor()

        # Phase 8: Advanced Scheduling
        self.scheduler = AdvancedScheduler()

        # Phase 9: One-Command Deployment
        self.deployment = DeploymentOrchestrator()

        logger.info("Phase 5-9 system initialized with 5 major components")

    async def demo_tool_orchestration(self):
        """Demo tool ecosystem orchestration."""
        logger.info("\n=== PHASE 5: Tool Ecosystem Integration ===")

        # Sync all tools
        sync_result = await self.tool_orchestrator.sync_all_tools()
        logger.info(f"Tool sync result: {sync_result}")

        # Get GitHub PRs
        prs = await self.tool_orchestrator.github.get_pull_requests()
        logger.info(f"Found {len(prs)} open PRs")

        # Send Slack notification
        await self.tool_orchestrator.slack.send_notification(
            "GitHub Sync Complete",
            f"Synced {len(prs)} pull requests",
            priority="normal"
        )

        # Post to Discord
        await self.tool_orchestrator.discord.send_message(
            "general",
            "BAEL tool orchestration is active!"
        )

        # Get stats
        stats = self.tool_orchestrator.get_orchestration_stats()
        logger.info(f"Tool orchestrator stats: {stats}")

        return stats

    async def demo_memory_learning(self):
        """Demo advanced memory and learning."""
        logger.info("\n=== PHASE 6: Advanced Memory & Learning ===")

        # Add memories
        m1 = self.memory.add_memory(
            "Successfully deployed to production using blue-green strategy",
            MemoryType.PROCEDURAL,
            {"service": "api", "duration_seconds": 45}
        )

        m2 = self.memory.add_memory(
            "GitHub API rate limit hit during sync, switched to queue",
            MemoryType.EPISODIC,
            {"service": "github", "retry_after": 3600}
        )

        # Create knowledge graph
        service_id = self.memory.add_knowledge_node(
            "service",
            "API Service",
            {"type": "backend", "language": "python"}
        )

        db_id = self.memory.add_knowledge_node(
            "database",
            "PostgreSQL",
            {"type": "database", "version": "14"}
        )

        self.memory.add_knowledge_edge(service_id, db_id, "uses")

        # Learn from events
        self.learning.learn_from_success(
            "deployment",
            "blue_green",
            {"services": 3, "zones": 2},
            0.98
        )

        self.learning.learn_from_failure(
            "sync",
            "sequential",
            "rate_limit",
            {"api": "github"}
        )

        # Generate suggestions
        suggestions = self.learning.generate_optimization_suggestions()

        logger.info(f"Memory stats: {self.memory.get_stats()}")
        logger.info(f"Learning stats: {self.learning.get_learning_stats()}")
        logger.info(f"Suggestions: {suggestions}")

        return {
            "memory_stats": self.memory.get_stats(),
            "learning_stats": self.learning.get_learning_stats(),
            "suggestions": len(suggestions)
        }

    async def demo_self_healing(self):
        """Demo self-healing infrastructure."""
        logger.info("\n=== PHASE 7: Self-Healing Infrastructure ===")

        # Report health
        self.health_monitor.report_health(
            "api_service",
            HealthStatus.HEALTHY,
            error_rate=0.01,
            latency_p99=50
        )

        self.health_monitor.report_health(
            "database",
            HealthStatus.DEGRADED,
            error_rate=0.15,
            latency_p99=500
        )

        self.health_monitor.report_health(
            "cache",
            HealthStatus.HEALTHY,
            error_rate=0.0,
            latency_p99=5
        )

        # Register remediation
        self.health_monitor.register_remediation(
            "database",
            lambda m: m.error_rate > 0.1,
            "restart",
            {"graceful": True}
        )

        # Run monitoring and healing
        await self.health_monitor.monitor_and_heal()

        # Get system health
        health = self.health_monitor.get_system_health()
        logger.info(f"System health: {health}")

        return health

    async def demo_advanced_scheduling(self):
        """Demo advanced scheduling and workflow automation."""
        logger.info("\n=== PHASE 8: Advanced Scheduling & Automation ===")

        # Create workflow
        steps = [
            WorkflowStep(
                id="1",
                name="Backup Database",
                action_type="backup",
                parameters={"database": "main"}
            ),
            WorkflowStep(
                id="2",
                name="Run Tests",
                action_type="test",
                parameters={"suite": "full"}
            ),
            WorkflowStep(
                id="3",
                name="Deploy",
                action_type="deploy",
                parameters={"target": "staging"},
                depends_on=["2"]
            )
        ]

        workflow_id = self.scheduler.create_workflow(
            "Daily Deployment",
            steps,
            "Daily automated deployment workflow"
        )

        # Add triggers
        self.scheduler.add_cron_trigger(workflow_id, "0 2 * * *", "Nightly")
        self.scheduler.add_event_trigger(workflow_id, "github.push.main", "On Main Push")
        self.scheduler.add_metric_trigger(
            workflow_id,
            "error_rate",
            0.05,
            ">",
            "High Error Rate"
        )

        # Execute workflow
        execution_id = await self.scheduler.execute_workflow(workflow_id)

        logger.info(f"Workflow execution: {execution_id}")

        stats = self.scheduler.get_scheduler_stats()
        logger.info(f"Scheduler stats: {stats}")

        return stats

    async def demo_one_command_deployment(self):
        """Demo one-command deployment."""
        logger.info("\n=== PHASE 9: One-Command Deployment ===")

        # Deploy to Docker Compose
        result = await self.deployment.one_command_deploy(
            target=DeploymentTarget.DOCKER_COMPOSE,
            environment="staging",
            name="bael"
        )

        logger.info(f"Deployment status: {result['status']}")
        logger.info(f"Deployment logs (first 5):")
        for log in result['logs'][:5]:
            logger.info(f"  {log}")

        # Get stats
        stats = self.deployment.get_deployment_stats()
        logger.info(f"Deployment stats: {stats}")

        return result

    async def demo_integrated_workflow(self):
        """Demo integrated workflow using all systems."""
        logger.info("\n=== INTEGRATED PHASE 5-9 WORKFLOW ===")

        # Scenario: Production deployment with monitoring and healing

        logger.info("Starting integrated deployment workflow...")

        # Step 1: Check tool status via orchestrator
        logger.info("Step 1: Checking tool ecosystem status")
        stats = await self.demo_tool_orchestration()

        # Step 2: Learn from past deployments
        logger.info("Step 2: Analyzing past deployment patterns")
        learning_stats = await self.demo_memory_learning()

        # Step 3: Deploy with one-command
        logger.info("Step 3: Deploying application")
        deployment = await self.demo_one_command_deployment()

        # Step 4: Monitor system health
        logger.info("Step 4: Monitoring system health")
        health = await self.demo_self_healing()

        # Step 5: Schedule post-deployment tasks
        logger.info("Step 5: Scheduling post-deployment tasks")
        scheduling = await self.demo_advanced_scheduling()

        logger.info("\n=== INTEGRATED WORKFLOW COMPLETE ===")

        return {
            "tools": stats,
            "learning": learning_stats,
            "deployment": deployment['status'],
            "health": health,
            "scheduling": scheduling
        }

    async def run_full_demo(self):
        """Run complete Phase 5-9 demo."""
        logger.info("\n" + "="*60)
        logger.info("BAEL PHASE 5-9: ENTERPRISE ECOSYSTEM")
        logger.info("="*60)

        try:
            # Run each phase demo
            logger.info("\nRunning individual phase demos...")

            logger.info("\nPhase 5: Tool Orchestration")
            tools_demo = await self.demo_tool_orchestration()

            logger.info("\nPhase 6: Memory & Learning")
            memory_demo = await self.demo_memory_learning()

            logger.info("\nPhase 7: Self-Healing")
            healing_demo = await self.demo_self_healing()

            logger.info("\nPhase 8: Advanced Scheduling")
            scheduling_demo = await self.demo_advanced_scheduling()

            logger.info("\nPhase 9: One-Command Deployment")
            deployment_demo = await self.demo_one_command_deployment()

            # Run integrated workflow
            logger.info("\nRunning integrated workflow...")
            integrated = await self.demo_integrated_workflow()

            logger.info("\n" + "="*60)
            logger.info("PHASE 5-9 DEMO COMPLETE")
            logger.info("="*60)

            return {
                "phase_5_tools": tools_demo,
                "phase_6_memory": memory_demo,
                "phase_7_healing": healing_demo,
                "phase_8_scheduling": scheduling_demo,
                "phase_9_deployment": deployment_demo,
                "integrated_workflow": integrated
            }

        except Exception as e:
            logger.error(f"Demo failed: {e}", exc_info=True)
            raise


if __name__ == "__main__":
    async def main():
        system = Phase5To9System()
        results = await system.run_full_demo()

        logger.info("\n=== FINAL RESULTS ===")
        logger.info(f"All phases completed successfully!")
        logger.info(f"Total systems integrated: 5")
        logger.info(f"Total capabilities: 50+")

    asyncio.run(main())

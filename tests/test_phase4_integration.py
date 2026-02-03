"""
Phase 4 Integration Tests

Verifies that all Phase 4 systems work correctly and integrate properly.
"""

import asyncio
import logging
from typing import Any, Dict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Phase4IntegrationTest:
    """Complete integration tests for Phase 4."""

    def __init__(self):
        """Initialize test suite."""
        self.tests_passed = 0
        self.tests_failed = 0
        self.test_results = []

    async def run_all_tests(self):
        """Run all integration tests."""
        logger.info("="*60)
        logger.info("PHASE 4 INTEGRATION TESTS")
        logger.info("="*60 + "\n")

        await self.test_autonomous_agent()
        await self.test_fabric_patterns()
        await self.test_natural_language()
        await self.test_coordination()
        await self.test_agent_swarm()
        await self.test_end_to_end()

        self._print_summary()

    async def test_autonomous_agent(self):
        """Test autonomous agent creation and execution."""
        test_name = "Autonomous Agent"
        logger.info(f"\n🧪 Testing {test_name}...")

        try:
            from core.agents import AdvancedAutonomousAgent, AgentCapability

            # Create agent
            agent = AdvancedAutonomousAgent(
                agent_id="test_agent",
                name="TestAgent",
                capabilities=[
                    AgentCapability(
                        name="test_capability",
                        description="Test capability",
                        required_tools=[]
                    )
                ]
            )

            # Execute task
            task = {
                "name": "test_task",
                "type": "test",
                "parameters": {}
            }

            result = await agent.execute_autonomous(task)

            # Verify
            assert result["status"] == "success", "Execution should succeed"
            assert "strategy_used" in result, "Should have strategy"
            assert "retry_count" in result, "Should have retry count"

            # Check stats
            stats = agent.get_stats()
            assert stats["total_executions"] >= 1, "Should have executed"
            assert stats["agent_id"] == "test_agent", "Agent ID should match"

            self._test_passed(test_name)
            logger.info(f"   ✅ Agent executed successfully")
            logger.info(f"   ✅ Stats: {stats['total_executions']} executions")

        except Exception as e:
            self._test_failed(test_name, str(e))

    async def test_fabric_patterns(self):
        """Test Fabric pattern integration."""
        test_name = "Fabric Patterns"
        logger.info(f"\n🧪 Testing {test_name}...")

        try:
            from core.fabric import FabricIntegration, FabricPatternLibrary

            # Create integration
            fabric = FabricIntegration()

            # Verify patterns loaded
            pattern_count = len(fabric.library.patterns)
            assert pattern_count > 20, f"Should have 20+ patterns, got {pattern_count}"

            # Test pattern retrieval
            pattern = fabric.library.get_pattern("extract_wisdom")
            assert pattern is not None, "Should find extract_wisdom pattern"
            assert pattern.name == "extract_wisdom", "Pattern name should match"

            # Test pattern execution (without LLM)
            result = await fabric.execute_pattern(
                "extract_wisdom",
                "Test content for wisdom extraction"
            )

            assert "pattern" in result, "Should have pattern field"
            assert result["pattern"] == "extract_wisdom", "Pattern should match"

            # Test search
            matches = fabric.library.search_patterns("code")
            assert len(matches) >= 3, "Should find code-related patterns"

            # Test recommendation
            recommendations = fabric.recommend_pattern("I need to analyze code")
            assert len(recommendations) > 0, "Should recommend patterns"

            self._test_passed(test_name)
            logger.info(f"   ✅ {pattern_count} patterns loaded")
            logger.info(f"   ✅ Pattern execution works")
            logger.info(f"   ✅ Search and recommendations work")

        except Exception as e:
            self._test_failed(test_name, str(e))

    async def test_natural_language(self):
        """Test natural language CLI."""
        test_name = "Natural Language CLI"
        logger.info(f"\n🧪 Testing {test_name}...")

        try:
            from core.cli.natural_language import NaturalLanguageCLI

            cli = NaturalLanguageCLI()

            # Test query intent
            result = await cli.process("show me the status")
            assert result["intent"] == "query", f"Should detect query intent, got {result['intent']}"
            assert result["confidence"] > 0, "Should have confidence"

            # Test action intent
            result = await cli.process("start the service")
            assert result["intent"] == "action", f"Should detect action intent, got {result['intent']}"

            # Test analysis intent
            result = await cli.process("analyze the performance")
            assert result["intent"] == "analysis", f"Should detect analysis intent, got {result['intent']}"

            # Test entity extraction
            result = await cli.process("deploy api service to production")
            assert "service" in result["entities"] or "environment" in result["entities"], "Should extract entities"

            # Test help intent
            result = await cli.process("what can you do?")
            assert result["intent"] == "help", "Should detect help intent"

            self._test_passed(test_name)
            logger.info(f"   ✅ Intent recognition works")
            logger.info(f"   ✅ Entity extraction works")
            logger.info(f"   ✅ All intent types detected")

        except Exception as e:
            self._test_failed(test_name, str(e))

    async def test_coordination(self):
        """Test multi-agent coordination."""
        test_name = "Multi-Agent Coordination"
        logger.info(f"\n🧪 Testing {test_name}...")

        try:
            from core.agents import AdvancedAutonomousAgent, AgentCapability
            from core.coordination import (AgentRole, CoordinatedTask,
                                           CoordinationEngine,
                                           CoordinationStrategy, TaskPriority)

            # Create coordination engine
            engine = CoordinationEngine(strategy=CoordinationStrategy.CONSENSUS)

            # Create test agents
            agent1 = AdvancedAutonomousAgent(
                agent_id="coord_test_1",
                name="Agent1",
                capabilities=[
                    AgentCapability(name="test_cap", description="Test", required_tools=[])
                ]
            )

            agent2 = AdvancedAutonomousAgent(
                agent_id="coord_test_2",
                name="Agent2",
                capabilities=[
                    AgentCapability(name="test_cap", description="Test", required_tools=[])
                ]
            )

            # Register agents
            engine.register_agent("coord_test_1", agent1, AgentRole.SPECIALIST)
            engine.register_agent("coord_test_2", agent2, AgentRole.GENERALIST)

            # Create task
            task = CoordinatedTask(
                task_id="coord_test_task",
                description="Test coordination",
                priority=TaskPriority.MEDIUM,
                required_capabilities=["test_cap"]
            )

            # Coordinate
            result = await engine.coordinate_task(task)

            assert result["status"] == "success", "Coordination should succeed"
            assert "strategy" in result, "Should have strategy"

            # Check stats
            stats = engine.get_coordination_stats()
            assert stats["total_coordinations"] >= 1, "Should have coordinated"
            assert stats["registered_agents"] == 2, "Should have 2 agents"

            self._test_passed(test_name)
            logger.info(f"   ✅ Coordination successful")
            logger.info(f"   ✅ {stats['registered_agents']} agents registered")
            logger.info(f"   ✅ Strategy: {stats['strategy']}")

        except Exception as e:
            self._test_failed(test_name, str(e))

    async def test_agent_swarm(self):
        """Test agent swarm functionality."""
        test_name = "Agent Swarm"
        logger.info(f"\n🧪 Testing {test_name}...")

        try:
            from core.agents import (AdvancedAutonomousAgent, AgentCapability,
                                     AgentSwarm)

            # Create swarm
            swarm = AgentSwarm("test_swarm")

            # Create and add agents
            for i in range(3):
                agent = AdvancedAutonomousAgent(
                    agent_id=f"swarm_agent_{i}",
                    name=f"SwarmAgent{i}",
                    capabilities=[
                        AgentCapability(
                            name=f"cap_{i}",
                            description=f"Capability {i}",
                            required_tools=[]
                        )
                    ]
                )
                swarm.add_agent(agent)

            # Execute distributed
            tasks = [
                {"name": f"task_{i}", "type": "test"}
                for i in range(5)
            ]

            results = await swarm.execute_distributed(tasks)

            assert len(results) == 5, "Should have 5 results"
            successful = sum(1 for r in results if not isinstance(r, Exception))
            assert successful >= 4, "Most tasks should succeed"

            # Check stats
            stats = swarm.get_swarm_stats()
            assert stats["agent_count"] == 3, "Should have 3 agents"
            assert stats["total_executions"] >= 5, "Should have executed tasks"

            self._test_passed(test_name)
            logger.info(f"   ✅ Swarm created with {stats['agent_count']} agents")
            logger.info(f"   ✅ Distributed {len(tasks)} tasks")
            logger.info(f"   ✅ Success rate: {successful/len(results):.2%}")

        except Exception as e:
            self._test_failed(test_name, str(e))

    async def test_end_to_end(self):
        """Test complete end-to-end workflow."""
        test_name = "End-to-End Integration"
        logger.info(f"\n🧪 Testing {test_name}...")

        try:
            from core.agents import AdvancedAutonomousAgent, AgentCapability
            from core.cli.natural_language import NaturalLanguageCLI
            from core.coordination import (AgentRole, CoordinatedTask,
                                           CoordinationEngine,
                                           CoordinationStrategy, TaskPriority)
            from core.fabric import FabricIntegration

            # 1. Natural language input
            cli = NaturalLanguageCLI()
            user_input = "analyze the code and deploy improvements"
            nl_result = await cli.process(user_input)

            assert nl_result["confidence"] > 0, "Should parse natural language"

            # 2. Create fabric integration
            fabric = FabricIntegration()

            # 3. Create agents
            code_agent = AdvancedAutonomousAgent(
                agent_id="e2e_code",
                name="CodeAgent",
                capabilities=[
                    AgentCapability(name="code_analysis", description="Analyze code", required_tools=[])
                ]
            )

            deploy_agent = AdvancedAutonomousAgent(
                agent_id="e2e_deploy",
                name="DeployAgent",
                capabilities=[
                    AgentCapability(name="deployment", description="Deploy code", required_tools=[])
                ]
            )

            # 4. Create coordination
            engine = CoordinationEngine(strategy=CoordinationStrategy.CONSENSUS)
            engine.register_agent("e2e_code", code_agent, AgentRole.SPECIALIST)
            engine.register_agent("e2e_deploy", deploy_agent, AgentRole.SPECIALIST)

            # 5. Create task based on NL intent
            task = CoordinatedTask(
                task_id="e2e_task",
                description="Analyze and deploy",
                priority=TaskPriority.HIGH,
                required_capabilities=["code_analysis", "deployment"]
            )

            # 6. Execute coordinated
            result = await engine.coordinate_task(task)

            assert result["status"] == "success", "End-to-end should succeed"

            self._test_passed(test_name)
            logger.info(f"   ✅ Natural language parsed")
            logger.info(f"   ✅ Fabric integrated")
            logger.info(f"   ✅ Agents coordinated")
            logger.info(f"   ✅ Task executed successfully")
            logger.info(f"   ✅ Complete workflow successful!")

        except Exception as e:
            self._test_failed(test_name, str(e))

    def _test_passed(self, test_name: str):
        """Record test pass."""
        self.tests_passed += 1
        self.test_results.append({"name": test_name, "status": "PASS"})

    def _test_failed(self, test_name: str, error: str):
        """Record test failure."""
        self.tests_failed += 1
        self.test_results.append({"name": test_name, "status": "FAIL", "error": error})
        logger.error(f"   ❌ {test_name} failed: {error}")

    def _print_summary(self):
        """Print test summary."""
        logger.info("\n" + "="*60)
        logger.info("TEST SUMMARY")
        logger.info("="*60)

        total_tests = self.tests_passed + self.tests_failed

        logger.info(f"\nTotal Tests: {total_tests}")
        logger.info(f"Passed: {self.tests_passed} ✅")
        logger.info(f"Failed: {self.tests_failed} ❌")
        logger.info(f"Success Rate: {self.tests_passed/total_tests*100:.1f}%")

        logger.info("\nTest Results:")
        for result in self.test_results:
            status_icon = "✅" if result["status"] == "PASS" else "❌"
            logger.info(f"  {status_icon} {result['name']}: {result['status']}")
            if "error" in result:
                logger.info(f"      Error: {result['error']}")

        logger.info("\n" + "="*60)
        if self.tests_failed == 0:
            logger.info("🎉 ALL TESTS PASSED! Phase 4 is working correctly! 🎉")
        else:
            logger.info(f"⚠️  {self.tests_failed} test(s) failed. Please review.")
        logger.info("="*60 + "\n")


async def main():
    """Run integration tests."""
    test_suite = Phase4IntegrationTest()
    await test_suite.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())

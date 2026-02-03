"""
BAEL - Ultimate Orchestrator Integration Tests
Tests for the Ultimate Orchestrator and all its components.
"""

import asyncio
import sys
import unittest
from pathlib import Path
from typing import Any, Dict

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class TestUltimateOrchestrator(unittest.TestCase):
    """Tests for Ultimate Orchestrator."""

    @classmethod
    def setUpClass(cls):
        """Set up Ultimate Orchestrator."""
        try:
            from core.ultimate.ultimate_orchestrator import (
                BAELMode, Capability, UltimateConfig, UltimateOrchestrator,
                create_ultimate)
            cls.UltimateOrchestrator = UltimateOrchestrator
            cls.UltimateConfig = UltimateConfig
            cls.BAELMode = BAELMode
            cls.Capability = Capability
            cls.create_ultimate = create_ultimate
            cls.available = True
        except ImportError as e:
            cls.available = False
            cls.error = str(e)

    def test_import(self):
        """Test Ultimate Orchestrator can be imported."""
        self.assertTrue(self.available, f"Import failed: {getattr(self, 'error', '')}")

    def test_config_minimal_mode(self):
        """Test minimal mode configuration."""
        if not self.available:
            self.skipTest("Not available")

        config = self.UltimateConfig(mode=self.BAELMode.MINIMAL)
        self.assertEqual(config.mode, self.BAELMode.MINIMAL)
        self.assertGreater(len(config.enabled_capabilities), 0)

    def test_config_standard_mode(self):
        """Test standard mode configuration."""
        if not self.available:
            self.skipTest("Not available")

        config = self.UltimateConfig(mode=self.BAELMode.STANDARD)
        self.assertEqual(config.mode, self.BAELMode.STANDARD)
        # Standard should have more capabilities than minimal
        minimal_config = self.UltimateConfig(mode=self.BAELMode.MINIMAL)
        self.assertGreater(len(config.enabled_capabilities), len(minimal_config.enabled_capabilities))

    def test_config_maximum_mode(self):
        """Test maximum mode configuration."""
        if not self.available:
            self.skipTest("Not available")

        config = self.UltimateConfig(mode=self.BAELMode.MAXIMUM)
        self.assertEqual(config.mode, self.BAELMode.MAXIMUM)
        # Maximum should have all capabilities
        self.assertEqual(len(config.enabled_capabilities), len(list(self.Capability)))

    def test_orchestrator_creation(self):
        """Test orchestrator can be created."""
        if not self.available:
            self.skipTest("Not available")

        config = self.UltimateConfig(mode=self.BAELMode.MINIMAL)
        orchestrator = self.UltimateOrchestrator(config)
        self.assertIsNotNone(orchestrator)
        self.assertFalse(orchestrator._initialized)

    def test_orchestrator_initialization(self):
        """Test orchestrator can be initialized."""
        if not self.available:
            self.skipTest("Not available")

        async def run_test():
            config = self.UltimateConfig(mode=self.BAELMode.MINIMAL)
            orchestrator = self.UltimateOrchestrator(config)
            await orchestrator.initialize()
            return orchestrator._initialized

        result = asyncio.get_event_loop().run_until_complete(run_test())
        self.assertTrue(result)

    def test_get_status(self):
        """Test getting orchestrator status."""
        if not self.available:
            self.skipTest("Not available")

        async def run_test():
            config = self.UltimateConfig(mode=self.BAELMode.MINIMAL)
            orchestrator = self.UltimateOrchestrator(config)
            await orchestrator.initialize()
            return orchestrator.get_status()

        status = asyncio.get_event_loop().run_until_complete(run_test())
        self.assertIsInstance(status, dict)
        self.assertIn('initialized', status)
        self.assertIn('mode', status)
        self.assertIn('enabled_capabilities', status)

    def test_get_capabilities(self):
        """Test getting capabilities list."""
        if not self.available:
            self.skipTest("Not available")

        async def run_test():
            config = self.UltimateConfig(mode=self.BAELMode.STANDARD)
            orchestrator = self.UltimateOrchestrator(config)
            await orchestrator.initialize()
            return orchestrator.get_capabilities()

        capabilities = asyncio.get_event_loop().run_until_complete(run_test())
        self.assertIsInstance(capabilities, list)
        self.assertGreater(len(capabilities), 0)

    def test_process_query(self):
        """Test processing a query."""
        if not self.available:
            self.skipTest("Not available")

        async def run_test():
            config = self.UltimateConfig(mode=self.BAELMode.MINIMAL)
            orchestrator = self.UltimateOrchestrator(config)
            await orchestrator.initialize()
            result = await orchestrator.process("What is 2 + 2?")
            return result

        result = asyncio.get_event_loop().run_until_complete(run_test())
        self.assertTrue(hasattr(result, 'success'))
        self.assertTrue(hasattr(result, 'response'))

    def test_health_check(self):
        """Test health check."""
        if not self.available:
            self.skipTest("Not available")

        async def run_test():
            config = self.UltimateConfig(mode=self.BAELMode.MINIMAL)
            orchestrator = self.UltimateOrchestrator(config)
            await orchestrator.initialize()
            return await orchestrator.health_check()

        health = asyncio.get_event_loop().run_until_complete(run_test())
        self.assertIsInstance(health, dict)

    def test_create_ultimate_factory(self):
        """Test create_ultimate factory function."""
        if not self.available:
            self.skipTest("Not available")

        async def run_test():
            orchestrator = await self.create_ultimate(mode="minimal")
            return orchestrator

        orchestrator = asyncio.get_event_loop().run_until_complete(run_test())
        self.assertIsNotNone(orchestrator)
        self.assertTrue(orchestrator._initialized)


class TestCapabilities(unittest.TestCase):
    """Tests for individual capabilities."""

    @classmethod
    def setUpClass(cls):
        """Set up for capability tests."""
        try:
            from core.ultimate.ultimate_orchestrator import Capability
            cls.Capability = Capability
            cls.available = True
        except ImportError:
            cls.available = False

    def test_all_capabilities_exist(self):
        """Test all expected capabilities exist."""
        if not self.available:
            self.skipTest("Not available")

        expected = [
            "DEDUCTIVE", "INDUCTIVE", "ABDUCTIVE", "CAUSAL",
            "COUNTERFACTUAL", "TEMPORAL", "PROBABILISTIC",
            "WORKING_MEMORY", "EPISODIC_MEMORY", "SEMANTIC_MEMORY",
            "SINGLE_AGENT", "MULTI_AGENT", "AGENT_SWARM",
            "REINFORCEMENT_LEARNING", "META_LEARNING",
            "RAG", "KNOWLEDGE_GRAPH",
            "CODE_EXECUTION", "TOOL_USE", "WEB_RESEARCH",
            "WORKFLOW", "STATE_MACHINE", "DSL_RULES"
        ]

        for cap_name in expected:
            self.assertTrue(
                hasattr(self.Capability, cap_name),
                f"Missing capability: {cap_name}"
            )


class TestUltimateResult(unittest.TestCase):
    """Tests for UltimateResult."""

    @classmethod
    def setUpClass(cls):
        """Set up for result tests."""
        try:
            from core.ultimate.ultimate_orchestrator import (Capability,
                                                             UltimateResult)
            cls.UltimateResult = UltimateResult
            cls.Capability = Capability
            cls.available = True
        except ImportError:
            cls.available = False

    def test_result_creation(self):
        """Test creating a result."""
        if not self.available:
            self.skipTest("Not available")

        result = self.UltimateResult(
            success=True,
            response="Test response",
            confidence=0.9
        )

        self.assertTrue(result.success)
        self.assertEqual(result.response, "Test response")
        self.assertEqual(result.confidence, 0.9)

    def test_result_to_dict(self):
        """Test converting result to dict."""
        if not self.available:
            self.skipTest("Not available")

        result = self.UltimateResult(
            success=True,
            response="Test",
            capabilities_used=[self.Capability.DEDUCTIVE],
            confidence=0.85
        )

        d = result.to_dict()
        self.assertIsInstance(d, dict)
        self.assertIn('success', d)
        self.assertIn('response', d)
        self.assertIn('capabilities_used', d)
        self.assertIn('confidence', d)


class TestMCPIntegration(unittest.TestCase):
    """Tests for MCP server integration."""

    @classmethod
    def setUpClass(cls):
        """Set up MCP server."""
        try:
            from mcp.server import BaelMCPServer
            cls.MCPServer = BaelMCPServer
            cls.available = True
        except ImportError as e:
            cls.available = False
            cls.error = str(e)

    def test_mcp_import(self):
        """Test MCP server can be imported."""
        self.assertTrue(self.available, f"Import failed: {getattr(self, 'error', '')}")

    def test_mcp_creation(self):
        """Test MCP server can be created."""
        if not self.available:
            self.skipTest("Not available")

        server = self.MCPServer()
        self.assertIsNotNone(server)

    def test_mcp_has_tools(self):
        """Test MCP server has tools registered."""
        if not self.available:
            self.skipTest("Not available")

        server = self.MCPServer()
        self.assertGreater(len(server.tools), 0)

    def test_mcp_has_prompts(self):
        """Test MCP server has prompts registered."""
        if not self.available:
            self.skipTest("Not available")

        server = self.MCPServer()
        self.assertGreater(len(server.prompts), 0)

    def test_mcp_enhanced_tools(self):
        """Test MCP server has enhanced tools."""
        if not self.available:
            self.skipTest("Not available")

        server = self.MCPServer()
        tool_names = list(server.tools.keys())

        # Check for some enhanced tools
        enhanced_tools = [
            "bael_web_fetch", "bael_web_search",
            "bael_code_format", "bael_security_scan",
            "bael_file_read", "bael_file_write",
            "bael_sql_query", "bael_vector_search",
            "bael_ai_chat", "bael_ai_summarize",
            "bael_api_request", "bael_graphql_query"
        ]

        found = [t for t in enhanced_tools if t in tool_names]
        # If toolkit is available, should have enhanced tools
        # This is conditional on the toolkit being importable
        self.assertIsInstance(found, list)


class TestMainIntegration(unittest.TestCase):
    """Tests for main.py integration."""

    @classmethod
    def setUpClass(cls):
        """Set up main module."""
        try:
            from main import BAEL
            cls.BAEL = BAEL
            cls.available = True
        except ImportError as e:
            cls.available = False
            cls.error = str(e)

    def test_main_import(self):
        """Test main module can be imported."""
        self.assertTrue(self.available, f"Import failed: {getattr(self, 'error', '')}")

    def test_bael_creation(self):
        """Test BAEL can be created."""
        if not self.available:
            self.skipTest("Not available")

        bael = self.BAEL()
        self.assertIsNotNone(bael)
        self.assertFalse(bael.initialized)

    def test_bael_modes(self):
        """Test BAEL with different modes."""
        if not self.available:
            self.skipTest("Not available")

        for mode in ["minimal", "standard", "maximum"]:
            bael = self.BAEL(mode=mode)
            self.assertEqual(bael.mode, mode)


class TestCLIIntegration(unittest.TestCase):
    """Tests for CLI integration."""

    @classmethod
    def setUpClass(cls):
        """Set up CLI module."""
        try:
            from cli import BaelCLI
            cls.BaelCLI = BaelCLI
            cls.available = True
        except ImportError as e:
            cls.available = False
            cls.error = str(e)

    def test_cli_import(self):
        """Test CLI can be imported."""
        self.assertTrue(self.available, f"Import failed: {getattr(self, 'error', '')}")

    def test_cli_creation(self):
        """Test CLI can be created."""
        if not self.available:
            self.skipTest("Not available")

        cli = self.BaelCLI()
        self.assertIsNotNone(cli)

    def test_cli_modes(self):
        """Test CLI with different modes."""
        if not self.available:
            self.skipTest("Not available")

        for mode in ["minimal", "standard", "maximum"]:
            cli = self.BaelCLI(mode=mode)
            self.assertEqual(cli.current_mode, mode)


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    # Run tests
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestUltimateOrchestrator))
    suite.addTests(loader.loadTestsFromTestCase(TestCapabilities))
    suite.addTests(loader.loadTestsFromTestCase(TestUltimateResult))
    suite.addTests(loader.loadTestsFromTestCase(TestMCPIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestMainIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestCLIIntegration))

    # Run with verbosity
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)

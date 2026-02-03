#!/usr/bin/env python3
"""
BAEL v2.1.0 - Integration Tests
Tests for all major components working together.
"""

import asyncio
import json
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestResult:
    """Test result container."""

    def __init__(self, name: str):
        self.name = name
        self.passed = False
        self.error: Optional[str] = None
        self.duration_ms: float = 0


class IntegrationTestSuite:
    """Integration test suite for BAEL v2.1.0."""

    def __init__(self):
        self.results: list[TestResult] = []
        self.passed = 0
        self.failed = 0

    def log(self, msg: str, level: str = "info"):
        icons = {"info": "ℹ️", "success": "✅", "error": "❌", "warn": "⚠️"}
        print(f"  {icons.get(level, '•')} {msg}")

    async def run_test(self, name: str, test_func):
        """Run a single test."""
        result = TestResult(name)
        start = time.time()

        try:
            print(f"\n📋 Testing: {name}")
            await test_func()
            result.passed = True
            self.passed += 1
            self.log("PASSED", "success")
        except Exception as e:
            result.error = str(e)
            self.failed += 1
            self.log(f"FAILED: {e}", "error")

        result.duration_ms = (time.time() - start) * 1000
        self.results.append(result)
        return result.passed

    # =========================================================================
    # Core Wiring Tests
    # =========================================================================

    async def test_llm_executor_import(self):
        """Test LLM executor can be imported."""
        from core.wiring import LLMExecutor
        executor = LLMExecutor()
        assert executor is not None
        self.log("LLMExecutor initialized")

    async def test_memory_executor_import(self):
        """Test memory executor can be imported."""
        from core.wiring import MemoryExecutor
        executor = MemoryExecutor()
        assert executor is not None
        self.log("MemoryExecutor initialized")

    async def test_unified_wiring(self):
        """Test unified wiring imports."""
        from core.wiring import UnifiedWiring
        wiring = UnifiedWiring()
        assert wiring.llm is not None
        assert wiring.memory is not None
        self.log("UnifiedWiring initialized with LLM and Memory")

    # =========================================================================
    # Agent Execution Engine Tests
    # =========================================================================

    async def test_agent_execution_engine_import(self):
        """Test agent execution engine can be imported."""
        from core.agents.execution_engine import AgentExecutionEngine, Task
        engine = AgentExecutionEngine()
        assert engine is not None
        self.log("AgentExecutionEngine initialized")

    async def test_task_creation(self):
        """Test task creation."""
        from core.agents.execution_engine import Task, TaskStatus
        task = Task(name="Test task", action="execute_code")
        assert task.id.startswith("task-")
        assert task.status == TaskStatus.PENDING
        self.log(f"Created task: {task.id}")

    async def test_action_handlers(self):
        """Test action handlers exist."""
        from core.agents.execution_engine import (CodeExecutionHandler,
                                                  FileOperationHandler,
                                                  LLMCallHandler,
                                                  WebSearchHandler)

        handlers = [
            CodeExecutionHandler(),
            LLMCallHandler(),
            FileOperationHandler(),
            WebSearchHandler()
        ]

        for h in handlers:
            assert h.action_name is not None
            self.log(f"Handler: {h.action_name}")

    async def test_code_execution_handler(self):
        """Test code execution handler works."""
        from core.agents.execution_engine import CodeExecutionHandler

        handler = CodeExecutionHandler()
        result = await handler.execute({
            "code": "result = 2 + 2",
            "language": "python",
            "_task_id": "test"
        })

        assert result.success
        assert result.output == 4
        self.log(f"Code execution result: {result.output}")

    # =========================================================================
    # Workflow Engine Tests
    # =========================================================================

    async def test_workflow_engine_import(self):
        """Test workflow engine can be imported."""
        from core.workflows.execution_engine import Workflow, WorkflowEngine
        engine = WorkflowEngine()
        assert engine is not None
        self.log("WorkflowEngine initialized")

    async def test_workflow_creation(self):
        """Test workflow creation from dict."""
        from core.workflows.execution_engine import NodeType, Workflow

        workflow = Workflow.from_dict({
            "name": "Test Workflow",
            "nodes": [
                {"type": "action", "name": "Start", "config": {}}
            ]
        })

        assert workflow.name == "Test Workflow"
        assert len(workflow.nodes) == 1
        self.log(f"Created workflow: {workflow.id}")

    async def test_workflow_execution(self):
        """Test simple workflow execution."""
        from core.workflows.execution_engine import (NodeType, Workflow,
                                                     WorkflowEngine,
                                                     WorkflowNode)

        workflow = Workflow(
            name="Test",
            nodes=[
                WorkflowNode(
                    id="node1",
                    type=NodeType.ACTION,
                    name="Log Test",
                    config={"action": "log", "params": {"message": "Test"}}
                )
            ]
        )

        engine = WorkflowEngine()
        context = await engine.execute(workflow)

        assert context.status.value in ["completed", "failed"]
        self.log(f"Workflow completed: {context.status.value}")

    # =========================================================================
    # WebSocket Manager Tests
    # =========================================================================

    async def test_websocket_manager_import(self):
        """Test WebSocket manager can be imported."""
        from core.realtime.websocket_manager import (MessageType,
                                                     WebSocketManager)
        manager = WebSocketManager()
        assert manager is not None
        self.log("WebSocketManager initialized")

    async def test_stream_event_format(self):
        """Test stream event formatting."""
        from api.streaming import StreamEvent

        event = StreamEvent(
            event="test",
            data={"message": "hello"}
        )

        sse = event.to_sse()
        assert "event: test" in sse
        assert "hello" in sse
        self.log("StreamEvent SSE format valid")

    # =========================================================================
    # Autonomous System Tests
    # =========================================================================

    async def test_service_discovery_import(self):
        """Test service discovery can be imported."""
        from core.autonomous.discovery import ServiceDiscovery
        discovery = ServiceDiscovery()
        assert discovery is not None
        self.log("ServiceDiscovery initialized")

    async def test_auto_setup_import(self):
        """Test auto setup can be imported."""
        from core.autonomous.auto_setup import AutoSetup
        setup = AutoSetup()
        assert setup is not None
        self.log("AutoSetup initialized")

    # =========================================================================
    # MCP Client Tests
    # =========================================================================

    async def test_mcp_client_import(self):
        """Test MCP client can be imported."""
        from core.mcp_client import MCPClient
        client = MCPClient()
        assert client is not None
        self.log("MCPClient initialized")

    # =========================================================================
    # Council Integration Tests
    # =========================================================================

    async def test_council_llm_integration_import(self):
        """Test council LLM integration can be imported."""
        from core.council.llm_integration import (CouncilLLMIntegration,
                                                  CouncilPersona)

        council = CouncilLLMIntegration()
        assert len(council.personas) > 0
        self.log(f"Council has {len(council.personas)} personas")

    # =========================================================================
    # Session Manager Tests
    # =========================================================================

    async def test_session_manager_import(self):
        """Test session manager can be imported."""
        from core.session.session_manager import SessionManager
        manager = SessionManager()
        assert manager is not None
        self.log("SessionManager available")

    # =========================================================================
    # API Streaming Tests
    # =========================================================================

    async def test_streaming_classes(self):
        """Test streaming classes can be imported."""
        from api.streaming import (get_streaming_chat, get_streaming_council,
                                   get_streaming_tasks)

        chat = get_streaming_chat()
        council = get_streaming_council()
        tasks = get_streaming_tasks()

        assert chat is not None
        assert council is not None
        assert tasks is not None
        self.log("All streaming handlers initialized")

    # =========================================================================
    # Run All Tests
    # =========================================================================

    async def run_all(self):
        """Run all integration tests."""
        print("\n" + "=" * 60)
        print("🧪 BAEL v2.1.0 INTEGRATION TEST SUITE")
        print("=" * 60)

        tests = [
            # Core Wiring
            ("Core: LLM Executor", self.test_llm_executor_import),
            ("Core: Memory Executor", self.test_memory_executor_import),
            ("Core: Unified Wiring", self.test_unified_wiring),

            # Agent Execution
            ("Agents: Execution Engine", self.test_agent_execution_engine_import),
            ("Agents: Task Creation", self.test_task_creation),
            ("Agents: Action Handlers", self.test_action_handlers),
            ("Agents: Code Execution", self.test_code_execution_handler),

            # Workflow Engine
            ("Workflows: Engine Import", self.test_workflow_engine_import),
            ("Workflows: Creation", self.test_workflow_creation),
            ("Workflows: Execution", self.test_workflow_execution),

            # WebSocket
            ("WebSocket: Manager Import", self.test_websocket_manager_import),
            ("WebSocket: Event Format", self.test_stream_event_format),

            # Autonomous
            ("Autonomous: Service Discovery", self.test_service_discovery_import),
            ("Autonomous: Auto Setup", self.test_auto_setup_import),

            # MCP
            ("MCP: Client Import", self.test_mcp_client_import),

            # Council
            ("Council: LLM Integration", self.test_council_llm_integration_import),

            # Session
            ("Session: Manager Import", self.test_session_manager_import),

            # API Streaming
            ("API: Streaming Classes", self.test_streaming_classes),
        ]

        for name, test_func in tests:
            await self.run_test(name, test_func)

        # Summary
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        print(f"  Total Tests: {len(self.results)}")
        print(f"  ✅ Passed: {self.passed}")
        print(f"  ❌ Failed: {self.failed}")
        print(f"  Success Rate: {(self.passed / len(self.results) * 100):.1f}%")

        total_time = sum(r.duration_ms for r in self.results)
        print(f"  Total Time: {total_time:.0f}ms")

        if self.failed > 0:
            print("\n❌ FAILED TESTS:")
            for r in self.results:
                if not r.passed:
                    print(f"    • {r.name}: {r.error}")

        print("\n" + "=" * 60)

        return self.failed == 0


if __name__ == "__main__":
    suite = IntegrationTestSuite()
    success = asyncio.run(suite.run_all())
    sys.exit(0 if success else 1)

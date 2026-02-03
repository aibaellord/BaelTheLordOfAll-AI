"""
Tests for Workflow Orchestration Engine
"""

import asyncio
from datetime import datetime

import pytest

from core.workflows.orchestration import (TaskDefinition, TaskResult,
                                          TaskStatus, WorkflowDefinition,
                                          WorkflowEngine, WorkflowExecution,
                                          WorkflowStatus)


@pytest.fixture
def engine():
    """Create workflow engine"""
    return WorkflowEngine()


@pytest.fixture
def simple_workflow():
    """Create simple test workflow"""
    workflow = WorkflowDefinition(
        id="test-workflow",
        name="Test Workflow",
        description="Simple test workflow",
        created_at=datetime.utcnow().isoformat(),
    )

    task1 = TaskDefinition(
        id="task-1",
        name="Task 1",
        action="echo",
        inputs={"message": "hello"},
    )

    task2 = TaskDefinition(
        id="task-2",
        name="Task 2",
        action="echo",
        inputs={"message": "world"},
        depends_on=["task-1"],
    )

    workflow.add_task(task1)
    workflow.add_task(task2)

    return workflow


class TestWorkflowDefinition:
    """Test workflow definition"""

    def test_create_workflow(self, simple_workflow):
        """Test workflow creation"""
        assert simple_workflow.id == "test-workflow"
        assert len(simple_workflow.tasks) == 2

    def test_add_task(self):
        """Test adding tasks"""
        workflow = WorkflowDefinition(
            id="test",
            name="Test",
            description="",
            created_at=datetime.utcnow().isoformat(),
        )

        task = TaskDefinition(
            id="task-1",
            name="Task 1",
            action="echo",
        )

        workflow.add_task(task)
        assert len(workflow.tasks) == 1
        assert workflow.get_task("task-1") == task

    def test_get_nonexistent_task(self, simple_workflow):
        """Test getting nonexistent task"""
        task = simple_workflow.get_task("nonexistent")
        assert task is None

    def test_validate_empty_workflow(self):
        """Test validation of empty workflow"""
        workflow = WorkflowDefinition(
            id="test",
            name="Test",
            description="",
            created_at=datetime.utcnow().isoformat(),
        )

        valid, errors = workflow.validate()
        assert not valid
        assert "at least one task" in errors[0]

    def test_validate_missing_dependency(self):
        """Test validation with missing dependency"""
        workflow = WorkflowDefinition(
            id="test",
            name="Test",
            description="",
            created_at=datetime.utcnow().isoformat(),
        )

        task = TaskDefinition(
            id="task-1",
            name="Task 1",
            action="echo",
            depends_on=["nonexistent"],
        )

        workflow.add_task(task)
        valid, errors = workflow.validate()
        assert not valid

    def test_circular_dependency_detection(self):
        """Test circular dependency detection"""
        workflow = WorkflowDefinition(
            id="test",
            name="Test",
            description="",
            created_at=datetime.utcnow().isoformat(),
        )

        task1 = TaskDefinition(
            id="task-1",
            name="Task 1",
            action="echo",
            depends_on=["task-2"],
        )

        task2 = TaskDefinition(
            id="task-2",
            name="Task 2",
            action="echo",
            depends_on=["task-1"],  # Circular
        )

        workflow.add_task(task1)
        workflow.add_task(task2)

        valid, errors = workflow.validate()
        assert not valid
        assert "circular" in errors[0]

    def test_execution_order(self, simple_workflow):
        """Test topological sort for execution order"""
        order = simple_workflow.get_execution_order()

        # task-1 should come before task-2
        assert order.index("task-1") < order.index("task-2")

    def test_workflow_to_dict(self, simple_workflow):
        """Test workflow serialization"""
        d = simple_workflow.to_dict()

        assert d["id"] == "test-workflow"
        assert d["name"] == "Test Workflow"
        assert len(d["tasks"]) == 2


class TestWorkflowExecution:
    """Test workflow execution"""

    def test_create_execution(self):
        """Test execution creation"""
        execution = WorkflowExecution(
            execution_id="exec-1",
            workflow_id="wf-1",
        )

        assert execution.execution_id == "exec-1"
        assert execution.workflow_id == "wf-1"
        assert execution.status == WorkflowStatus.PENDING

    def test_add_result(self):
        """Test adding task result"""
        execution = WorkflowExecution(
            execution_id="exec-1",
            workflow_id="wf-1",
        )

        result = TaskResult(
            task_id="task-1",
            status=TaskStatus.COMPLETED,
            output={"result": "success"},
        )

        execution.add_result(result)
        assert execution.get_result("task-1") == result

    def test_execution_progress(self):
        """Test progress calculation"""
        execution = WorkflowExecution(
            execution_id="exec-1",
            workflow_id="wf-1",
        )

        # Add results
        for i in range(3):
            result = TaskResult(
                task_id=f"task-{i}",
                status=TaskStatus.COMPLETED if i < 2 else TaskStatus.RUNNING,
            )
            execution.add_result(result)

        progress = execution.get_progress()
        assert progress == pytest.approx(66.67, 0.1)

    def test_is_complete(self):
        """Test completion check"""
        execution = WorkflowExecution(
            execution_id="exec-1",
            workflow_id="wf-1",
        )

        assert not execution.is_complete()

        execution.status = WorkflowStatus.COMPLETED
        assert execution.is_complete()


class TestWorkflowEngine:
    """Test workflow engine"""

    def test_register_action(self, engine):
        """Test action registration"""
        def echo_action(message: str) -> str:
            return message

        engine.register_action("echo", echo_action)
        assert "echo" in engine.action_registry

    def test_create_workflow(self, engine, simple_workflow):
        """Test workflow creation"""
        success = engine.create_workflow(simple_workflow)
        assert success
        assert simple_workflow.id in engine.workflows

    def test_get_workflow(self, engine, simple_workflow):
        """Test workflow retrieval"""
        engine.create_workflow(simple_workflow)
        workflow = engine.get_workflow(simple_workflow.id)

        assert workflow == simple_workflow

    def test_get_nonexistent_workflow(self, engine):
        """Test getting nonexistent workflow"""
        workflow = engine.get_workflow("nonexistent")
        assert workflow is None

    @pytest.mark.asyncio
    async def test_execute_workflow(self, engine):
        """Test workflow execution"""
        # Create workflow
        workflow = WorkflowDefinition(
            id="test-exec",
            name="Test",
            description="",
            created_at=datetime.utcnow().isoformat(),
        )

        task = TaskDefinition(
            id="task-1",
            name="Task 1",
            action="test_action",
        )

        workflow.add_task(task)
        engine.create_workflow(workflow)

        # Register action
        async def test_action():
            return {"result": "success"}

        engine.register_action("test_action", test_action)

        # Execute
        execution = await engine.execute_workflow("test-exec", "exec-1")

        assert execution.workflow_id == "test-exec"
        assert execution.status in [WorkflowStatus.COMPLETED, WorkflowStatus.FAILED]

    @pytest.mark.asyncio
    async def test_task_with_dependencies(self, engine):
        """Test task execution with dependencies"""
        workflow = WorkflowDefinition(
            id="deps-test",
            name="Test",
            description="",
            created_at=datetime.utcnow().isoformat(),
        )

        task1 = TaskDefinition(
            id="task-1",
            name="Task 1",
            action="task1",
        )

        task2 = TaskDefinition(
            id="task-2",
            name="Task 2",
            action="task2",
            depends_on=["task-1"],
        )

        workflow.add_task(task1)
        workflow.add_task(task2)
        engine.create_workflow(workflow)

        # Register actions
        results = []

        async def action1():
            results.append(1)
            return {"value": 1}

        async def action2():
            results.append(2)
            return {"value": 2}

        engine.register_action("task1", action1)
        engine.register_action("task2", action2)

        # Execute
        execution = await engine.execute_workflow("deps-test", "exec-deps")

        # Task 1 should execute before task 2
        assert results[0] == 1
        assert results[1] == 2

    @pytest.mark.asyncio
    async def test_task_timeout(self, engine):
        """Test task timeout handling"""
        workflow = WorkflowDefinition(
            id="timeout-test",
            name="Test",
            description="",
            created_at=datetime.utcnow().isoformat(),
        )

        task = TaskDefinition(
            id="task-1",
            name="Task 1",
            action="slow_task",
            timeout_seconds=1,
        )

        workflow.add_task(task)
        engine.create_workflow(workflow)

        # Register slow action
        async def slow_action():
            await asyncio.sleep(5)
            return {}

        engine.register_action("slow_task", slow_action)

        # Execute
        execution = await engine.execute_workflow("timeout-test", "exec-timeout")

        # Should have failed
        result = execution.get_result("task-1")
        assert result.status == TaskStatus.FAILED

    @pytest.mark.asyncio
    async def test_condition_evaluation(self, engine):
        """Test conditional task execution"""
        workflow = WorkflowDefinition(
            id="cond-test",
            name="Test",
            description="",
            variables={"execute": True},
            created_at=datetime.utcnow().isoformat(),
        )

        task = TaskDefinition(
            id="task-1",
            name="Task 1",
            action="test",
            condition="vars['execute']",
        )

        workflow.add_task(task)
        engine.create_workflow(workflow)

        async def test_action():
            return {}

        engine.register_action("test", test_action)

        # Execute with true condition
        execution = await engine.execute_workflow("cond-test", "exec-cond", variables={"execute": True})
        result = execution.get_result("task-1")
        assert result.status != TaskStatus.SKIPPED

    def test_cancel_execution(self, engine):
        """Test execution cancellation"""
        execution = WorkflowExecution(
            execution_id="exec-1",
            workflow_id="wf-1",
            status=WorkflowStatus.RUNNING,
        )

        engine.executions["exec-1"] = execution

        success = engine.cancel_execution("exec-1")
        assert success
        assert execution.status == WorkflowStatus.CANCELLED

    def test_get_execution_history(self, engine):
        """Test execution history"""
        for i in range(5):
            execution = WorkflowExecution(
                execution_id=f"exec-{i}",
                workflow_id="wf-1",
                status=WorkflowStatus.COMPLETED,
            )
            engine.execution_history.append(execution)

        history = engine.get_execution_history("wf-1", limit=10)
        assert len(history) == 5

    def test_statistics(self, engine):
        """Test engine statistics"""
        # Create executions
        for i in range(3):
            execution = WorkflowExecution(
                execution_id=f"exec-{i}",
                workflow_id="wf-1",
                status=WorkflowStatus.COMPLETED if i < 2 else WorkflowStatus.FAILED,
            )
            engine.execution_history.append(execution)

        stats = engine.get_statistics()
        assert stats["total_executions"] == 3
        assert stats["completed_executions"] == 2
        assert stats["failed_executions"] == 1
        assert stats["success_rate"] == pytest.approx(66.67, 0.1)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

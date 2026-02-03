"""
Workflow Orchestration API endpoints for BAEL
"""

import logging
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

from core.workflows.orchestration import (TaskDefinition, WorkflowDefinition,
                                          WorkflowEngine, WorkflowStatus)

logger = logging.getLogger(__name__)

# Global workflow engine
workflow_engine = WorkflowEngine()

router = APIRouter(prefix="/v1/workflows", tags=["workflows"])


# ============================================================================
# Workflow Management
# ============================================================================

@router.post("/create")
async def create_workflow(workflow_data: dict) -> dict:
    """Create a new workflow"""
    try:
        # Parse workflow definition
        workflow = WorkflowDefinition(
            id=workflow_data.get("id") or str(uuid.uuid4()),
            name=workflow_data.get("name"),
            description=workflow_data.get("description", ""),
            version=workflow_data.get("version", "1.0.0"),
        )

        # Add tasks
        for task_data in workflow_data.get("tasks", []):
            task = TaskDefinition(
                id=task_data["id"],
                name=task_data["name"],
                action=task_data["action"],
                inputs=task_data.get("inputs", {}),
                description=task_data.get("description", ""),
                timeout_seconds=task_data.get("timeout_seconds", 300),
                max_retries=task_data.get("max_retries", 3),
                depends_on=task_data.get("depends_on", []),
                condition=task_data.get("condition"),
            )
            workflow.add_task(task)

        # Validate
        valid, errors = workflow.validate()
        if not valid:
            raise ValueError(f"Invalid workflow: {', '.join(errors)}")

        # Create
        success = workflow_engine.create_workflow(workflow)
        if not success:
            raise ValueError("Failed to create workflow")

        logger.info(f"Workflow created: {workflow.id}")

        return {
            "message": "Workflow created",
            "workflow_id": workflow.id,
            "tasks": len(workflow.tasks),
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/list")
async def list_workflows() -> dict:
    """List all workflows"""
    workflows = workflow_engine.workflows

    return {
        "workflows": [
            {
                "id": w.id,
                "name": w.name,
                "description": w.description,
                "version": w.version,
                "task_count": len(w.tasks),
                "created_at": w.created_at,
            }
            for w in workflows.values()
        ],
        "total": len(workflows),
    }


@router.get("/{workflow_id}")
async def get_workflow(workflow_id: str) -> dict:
    """Get workflow details"""
    workflow = workflow_engine.get_workflow(workflow_id)

    if not workflow:
        raise HTTPException(status_code=404, detail=f"Workflow not found: {workflow_id}")

    return {
        "workflow": workflow.to_dict(),
        "task_count": len(workflow.tasks),
        "execution_order": workflow.get_execution_order(),
    }


# ============================================================================
# Workflow Execution
# ============================================================================

@router.post("/{workflow_id}/execute")
async def execute_workflow(
    workflow_id: str,
    variables: Optional[Dict[str, Any]] = None,
) -> dict:
    """Execute a workflow"""
    workflow = workflow_engine.get_workflow(workflow_id)

    if not workflow:
        raise HTTPException(status_code=404, detail=f"Workflow not found: {workflow_id}")

    # Generate execution ID
    execution_id = str(uuid.uuid4())

    try:
        # Execute workflow
        execution = await workflow_engine.execute_workflow(
            workflow_id,
            execution_id,
            variables
        )

        logger.info(f"Workflow executed: {workflow_id} -> {execution_id}")

        return {
            "execution_id": execution_id,
            "workflow_id": workflow_id,
            "status": execution.status.value,
            "progress": execution.get_progress(),
            "results": {
                task_id: result.to_dict()
                for task_id, result in execution.task_results.items()
            },
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{workflow_id}/executions")
async def get_executions(
    workflow_id: str,
    limit: int = Query(20, ge=1, le=100),
) -> dict:
    """Get workflow execution history"""
    history = workflow_engine.get_execution_history(workflow_id, limit)

    return {
        "workflow_id": workflow_id,
        "executions": [e.to_dict() for e in history],
        "count": len(history),
    }


# ============================================================================
# Execution Management
# ============================================================================

@router.get("/executions/{execution_id}")
async def get_execution(execution_id: str) -> dict:
    """Get execution details"""
    execution = workflow_engine.get_execution(execution_id)

    if not execution:
        raise HTTPException(status_code=404, detail=f"Execution not found: {execution_id}")

    return execution.to_dict()


@router.post("/executions/{execution_id}/cancel")
async def cancel_execution(execution_id: str) -> dict:
    """Cancel a running execution"""
    success = workflow_engine.cancel_execution(execution_id)

    if not success:
        raise HTTPException(
            status_code=400,
            detail="Execution is not running or does not exist"
        )

    return {
        "message": f"Execution cancelled: {execution_id}",
        "execution_id": execution_id,
    }


# ============================================================================
# Workflow Templates
# ============================================================================

@router.get("/templates")
async def get_templates() -> dict:
    """Get workflow templates"""
    templates = {
        "data-pipeline": {
            "name": "Data Pipeline",
            "description": "Process data through multiple stages",
            "tasks": [
                {"id": "extract", "name": "Extract", "action": "extract_data"},
                {"id": "transform", "name": "Transform", "action": "transform_data", "depends_on": ["extract"]},
                {"id": "load", "name": "Load", "action": "load_data", "depends_on": ["transform"]},
            ],
        },
        "approval-workflow": {
            "name": "Approval Workflow",
            "description": "Request approval and proceed based on decision",
            "tasks": [
                {"id": "submit", "name": "Submit", "action": "submit"},
                {"id": "notify", "name": "Notify Approver", "action": "notify", "depends_on": ["submit"]},
                {"id": "wait", "name": "Wait for Approval", "action": "wait", "depends_on": ["notify"]},
                {"id": "approve", "name": "Process Approval", "action": "process", "depends_on": ["wait"]},
            ],
        },
        "parallel-processing": {
            "name": "Parallel Processing",
            "description": "Process items in parallel",
            "tasks": [
                {"id": "prepare", "name": "Prepare", "action": "prepare"},
                {"id": "process1", "name": "Process 1", "action": "process", "depends_on": ["prepare"]},
                {"id": "process2", "name": "Process 2", "action": "process", "depends_on": ["prepare"]},
                {"id": "process3", "name": "Process 3", "action": "process", "depends_on": ["prepare"]},
                {"id": "aggregate", "name": "Aggregate", "action": "aggregate", "depends_on": ["process1", "process2", "process3"]},
            ],
        },
    }

    return {
        "templates": templates,
        "count": len(templates),
    }


# ============================================================================
# Statistics & Monitoring
# ============================================================================

@router.get("/statistics")
async def get_statistics() -> dict:
    """Get workflow engine statistics"""
    return workflow_engine.get_statistics()


@router.get("/{workflow_id}/statistics")
async def get_workflow_statistics(workflow_id: str) -> dict:
    """Get workflow-specific statistics"""
    workflow = workflow_engine.get_workflow(workflow_id)

    if not workflow:
        raise HTTPException(status_code=404, detail=f"Workflow not found: {workflow_id}")

    history = workflow_engine.get_execution_history(workflow_id, limit=1000)

    total = len(history)
    completed = len([e for e in history if e.status == WorkflowStatus.COMPLETED])
    failed = len([e for e in history if e.status == WorkflowStatus.FAILED])

    total_tasks = sum(len(e.task_results) for e in history)
    completed_tasks = sum(
        1 for e in history
        for r in e.task_results.values()
        if r.status.value == "completed"
    )

    return {
        "workflow_id": workflow_id,
        "executions": {
            "total": total,
            "completed": completed,
            "failed": failed,
            "success_rate": (completed / total * 100) if total > 0 else 0,
        },
        "tasks": {
            "total": total_tasks,
            "completed": completed_tasks,
            "average_per_execution": (total_tasks / total) if total > 0 else 0,
        },
    }


# Export router
__all__ = ["router", "workflow_engine"]

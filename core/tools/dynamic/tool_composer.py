"""
BAEL - Tool Composer
Composes tools into pipelines and workflows.
"""

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union

from . import DynamicTool, ToolComposition, ToolType

logger = logging.getLogger("BAEL.Tools.Composer")


class FlowType(Enum):
    """Types of composition flows."""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    CONDITIONAL = "conditional"
    LOOP = "loop"
    MAP_REDUCE = "map_reduce"


@dataclass
class FlowStep:
    """A step in a tool composition flow."""
    id: str
    tool_id: str
    flow_type: FlowType
    inputs: Dict[str, str]  # param_name -> source (previous_step.output or input.field)
    condition: Optional[str] = None
    loop_max: int = 10


@dataclass
class CompositionResult:
    """Result of a composition execution."""
    success: bool
    outputs: Dict[str, Any]
    step_results: List[Dict[str, Any]]
    execution_time: float
    error: Optional[str] = None


class ToolComposer:
    """
    Composes tools into complex pipelines.

    Features:
    - Sequential execution
    - Parallel execution
    - Conditional branching
    - Loop constructs
    - Map-reduce patterns
    - Data flow management
    """

    def __init__(self):
        self._compositions: Dict[str, ToolComposition] = {}
        self._tool_factory = None

    def _get_factory(self):
        """Get tool factory."""
        if self._tool_factory is None:
            from .tool_factory import get_tool_factory
            self._tool_factory = get_tool_factory()
        return self._tool_factory

    def create_composition(
        self,
        name: str,
        description: str,
        steps: List[FlowStep]
    ) -> ToolComposition:
        """
        Create a new tool composition.

        Args:
            name: Composition name
            description: What it does
            steps: Flow steps

        Returns:
            Created composition
        """
        comp_id = f"comp_{uuid.uuid4().hex[:8]}"

        # Extract tool IDs
        tool_ids = list(set(step.tool_id for step in steps))

        # Build flow definition
        flow = [
            {
                "id": step.id,
                "tool_id": step.tool_id,
                "type": step.flow_type.value,
                "inputs": step.inputs,
                "condition": step.condition,
                "loop_max": step.loop_max
            }
            for step in steps
        ]

        composition = ToolComposition(
            id=comp_id,
            name=name,
            description=description,
            tools=tool_ids,
            flow=flow
        )

        self._compositions[comp_id] = composition
        logger.info(f"Created composition: {name} with {len(steps)} steps")

        return composition

    async def execute(
        self,
        composition_id: str,
        inputs: Dict[str, Any]
    ) -> CompositionResult:
        """
        Execute a tool composition.

        Args:
            composition_id: Composition ID
            inputs: Input data

        Returns:
            Execution result
        """
        composition = self._compositions.get(composition_id)
        if not composition:
            return CompositionResult(
                success=False,
                outputs={},
                step_results=[],
                execution_time=0,
                error="Composition not found"
            )

        start_time = time.time()
        factory = self._get_factory()

        # Context for data flow
        context = {"input": inputs}
        step_results = []

        try:
            for step_def in composition.flow:
                step = FlowStep(
                    id=step_def["id"],
                    tool_id=step_def["tool_id"],
                    flow_type=FlowType(step_def["type"]),
                    inputs=step_def["inputs"],
                    condition=step_def.get("condition"),
                    loop_max=step_def.get("loop_max", 10)
                )

                # Check condition
                if step.condition and not self._evaluate_condition(step.condition, context):
                    step_results.append({
                        "step_id": step.id,
                        "skipped": True,
                        "reason": "Condition not met"
                    })
                    continue

                # Execute based on flow type
                if step.flow_type == FlowType.SEQUENTIAL:
                    result = await self._execute_step(step, context, factory)

                elif step.flow_type == FlowType.PARALLEL:
                    result = await self._execute_parallel(step, context, factory)

                elif step.flow_type == FlowType.LOOP:
                    result = await self._execute_loop(step, context, factory)

                elif step.flow_type == FlowType.MAP_REDUCE:
                    result = await self._execute_map_reduce(step, context, factory)

                else:
                    result = await self._execute_step(step, context, factory)

                # Store result in context
                context[step.id] = result
                step_results.append({
                    "step_id": step.id,
                    "success": True,
                    "output": result
                })

            execution_time = time.time() - start_time

            # Get final output (last step's result)
            final_output = step_results[-1].get("output") if step_results else {}

            return CompositionResult(
                success=True,
                outputs={"result": final_output, "context": context},
                step_results=step_results,
                execution_time=execution_time
            )

        except Exception as e:
            return CompositionResult(
                success=False,
                outputs={},
                step_results=step_results,
                execution_time=time.time() - start_time,
                error=str(e)
            )

    async def _execute_step(
        self,
        step: FlowStep,
        context: Dict[str, Any],
        factory
    ) -> Any:
        """Execute a single step."""
        # Resolve inputs
        kwargs = self._resolve_inputs(step.inputs, context)

        # Invoke tool
        return await factory.invoke(step.tool_id, **kwargs)

    async def _execute_parallel(
        self,
        step: FlowStep,
        context: Dict[str, Any],
        factory
    ) -> List[Any]:
        """Execute step in parallel over a list."""
        # Get the list to iterate over
        source = step.inputs.get("_parallel_source", "input.items")
        items = self._resolve_value(source, context)

        if not isinstance(items, list):
            items = [items]

        # Execute in parallel
        tasks = []
        for i, item in enumerate(items):
            item_context = {**context, "_item": item, "_index": i}
            kwargs = self._resolve_inputs(step.inputs, item_context)
            kwargs.pop("_parallel_source", None)
            tasks.append(factory.invoke(step.tool_id, **kwargs))

        return await asyncio.gather(*tasks)

    async def _execute_loop(
        self,
        step: FlowStep,
        context: Dict[str, Any],
        factory
    ) -> List[Any]:
        """Execute step in a loop."""
        results = []

        for i in range(step.loop_max):
            context["_loop_index"] = i

            # Check if we should continue
            if step.condition and not self._evaluate_condition(step.condition, context):
                break

            result = await self._execute_step(step, context, factory)
            results.append(result)
            context["_loop_result"] = result

        return results

    async def _execute_map_reduce(
        self,
        step: FlowStep,
        context: Dict[str, Any],
        factory
    ) -> Any:
        """Execute map-reduce pattern."""
        # Map phase
        map_results = await self._execute_parallel(step, context, factory)

        # Reduce phase - combine results
        reducer = step.inputs.get("_reducer", "concat")

        if reducer == "concat":
            if all(isinstance(r, list) for r in map_results):
                return [item for sublist in map_results for item in sublist]
            return map_results

        elif reducer == "sum":
            return sum(map_results)

        elif reducer == "first":
            return map_results[0] if map_results else None

        elif reducer == "last":
            return map_results[-1] if map_results else None

        else:
            return map_results

    def _resolve_inputs(
        self,
        inputs: Dict[str, str],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Resolve input mappings to actual values."""
        resolved = {}

        for param, source in inputs.items():
            if param.startswith("_"):
                continue  # Skip internal params

            resolved[param] = self._resolve_value(source, context)

        return resolved

    def _resolve_value(
        self,
        source: str,
        context: Dict[str, Any]
    ) -> Any:
        """Resolve a value reference."""
        if isinstance(source, str) and "." in source:
            parts = source.split(".")
            value = context

            for part in parts:
                if isinstance(value, dict):
                    value = value.get(part)
                elif hasattr(value, part):
                    value = getattr(value, part)
                else:
                    return None

            return value

        return source

    def _evaluate_condition(
        self,
        condition: str,
        context: Dict[str, Any]
    ) -> bool:
        """Evaluate a condition string."""
        try:
            # Simple evaluation with context
            return eval(condition, {"__builtins__": {}}, context)
        except Exception:
            return False

    def compose_sequential(
        self,
        name: str,
        tool_ids: List[str],
        description: str = ""
    ) -> ToolComposition:
        """
        Create a simple sequential composition.

        Args:
            name: Composition name
            tool_ids: Tools to execute in order
            description: Optional description

        Returns:
            Created composition
        """
        steps = []
        prev_step = None

        for i, tool_id in enumerate(tool_ids):
            step = FlowStep(
                id=f"step_{i}",
                tool_id=tool_id,
                flow_type=FlowType.SEQUENTIAL,
                inputs={"data": f"{prev_step}.output" if prev_step else "input.data"}
            )
            steps.append(step)
            prev_step = step.id

        return self.create_composition(
            name=name,
            description=description or f"Sequential: {' -> '.join(tool_ids)}",
            steps=steps
        )

    def compose_parallel(
        self,
        name: str,
        tool_ids: List[str],
        description: str = ""
    ) -> ToolComposition:
        """
        Create a parallel composition (fan-out).

        Args:
            name: Composition name
            tool_ids: Tools to execute in parallel
            description: Optional description

        Returns:
            Created composition
        """
        # All tools run on same input in parallel
        steps = [
            FlowStep(
                id=f"parallel_{i}",
                tool_id=tool_id,
                flow_type=FlowType.PARALLEL,
                inputs={"data": "input.data"}
            )
            for i, tool_id in enumerate(tool_ids)
        ]

        return self.create_composition(
            name=name,
            description=description or f"Parallel: [{', '.join(tool_ids)}]",
            steps=steps
        )

    def get_composition(self, composition_id: str) -> Optional[ToolComposition]:
        """Get a composition by ID."""
        return self._compositions.get(composition_id)

    def list_compositions(self) -> List[ToolComposition]:
        """List all compositions."""
        return list(self._compositions.values())

    def delete_composition(self, composition_id: str) -> bool:
        """Delete a composition."""
        if composition_id in self._compositions:
            del self._compositions[composition_id]
            return True
        return False

    def get_status(self) -> Dict[str, Any]:
        """Get composer status."""
        return {
            "total_compositions": len(self._compositions),
            "compositions": [
                {
                    "id": c.id,
                    "name": c.name,
                    "tools": len(c.tools),
                    "steps": len(c.flow)
                }
                for c in self._compositions.values()
            ]
        }


# Global instance
_tool_composer: Optional[ToolComposer] = None


def get_tool_composer() -> ToolComposer:
    """Get or create tool composer instance."""
    global _tool_composer
    if _tool_composer is None:
        _tool_composer = ToolComposer()
    return _tool_composer

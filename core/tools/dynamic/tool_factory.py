"""
BAEL - Dynamic Tool Factory
Creates tools at runtime from specifications.
"""

import asyncio
import inspect
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Generic, List, Optional, TypeVar

from . import DynamicTool, ToolCategory, ToolSignature, ToolType

logger = logging.getLogger("BAEL.Tools.Factory")

T = TypeVar("T")


@dataclass
class ToolSpec:
    """Specification for a tool to be created."""
    name: str
    description: str
    category: ToolCategory
    parameters: Dict[str, Dict[str, Any]]
    return_type: str = "Any"
    examples: List[Dict[str, Any]] = field(default_factory=list)


class DynamicToolFactory:
    """
    Creates tools dynamically at runtime.

    Features:
    - Generate tools from natural language
    - Create tools from code
    - Wrap existing functions
    - Generate tool implementations with LLM
    """

    def __init__(self):
        self._tools: Dict[str, DynamicTool] = {}
        self._llm = None
        self._templates: Dict[str, str] = {}

        # Load built-in templates
        self._load_templates()

    def _load_templates(self) -> None:
        """Load tool templates."""
        self._templates = {
            "basic": '''
async def {name}({params}) -> {return_type}:
    """
    {description}
    """
    {implementation}
''',
            "with_validation": '''
async def {name}({params}) -> {return_type}:
    """
    {description}
    """
    # Validate inputs
    {validation}

    # Implementation
    {implementation}
''',
            "with_retry": '''
async def {name}({params}) -> {return_type}:
    """
    {description}
    """
    import asyncio
    max_retries = 3
    for attempt in range(max_retries):
        try:
            {implementation}
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(2 ** attempt)
'''
        }

    async def _get_llm(self):
        """Lazy load LLM."""
        if self._llm is None:
            try:
                from core.llm import get_provider
                self._llm = get_provider()
            except ImportError:
                pass
        return self._llm

    async def create_from_spec(
        self,
        spec: ToolSpec,
        generate_code: bool = True
    ) -> DynamicTool:
        """
        Create a tool from a specification.

        Args:
            spec: Tool specification
            generate_code: Whether to generate implementation code

        Returns:
            Created dynamic tool
        """
        tool_id = f"dyn_{uuid.uuid4().hex[:8]}"

        # Build signature
        signature = ToolSignature(
            name=spec.name,
            parameters=spec.parameters,
            return_type=spec.return_type,
            description=spec.description
        )

        # Generate code if requested
        code = None
        handler = None

        if generate_code:
            code = await self._generate_implementation(spec)
            handler = await self._compile_code(code, spec.name)

        tool = DynamicTool(
            id=tool_id,
            name=spec.name,
            description=spec.description,
            tool_type=ToolType.GENERATED,
            category=spec.category,
            signature=signature,
            handler=handler,
            code=code
        )

        self._tools[tool_id] = tool
        logger.info(f"Created dynamic tool: {spec.name}")

        return tool

    async def _generate_implementation(self, spec: ToolSpec) -> str:
        """Generate implementation code for a tool."""
        llm = await self._get_llm()

        if llm:
            # Use LLM to generate implementation
            prompt = f"""
Generate a Python async function implementation for this tool:

Name: {spec.name}
Description: {spec.description}
Category: {spec.category.value}
Parameters: {json.dumps(spec.parameters, indent=2)}
Return Type: {spec.return_type}
Examples: {json.dumps(spec.examples, indent=2) if spec.examples else "None"}

Requirements:
1. Use async/await properly
2. Include error handling
3. Add logging where appropriate
4. Be concise but complete

Return ONLY the Python code, no explanations.
"""
            try:
                code = await llm.generate(prompt, temperature=0.3)
                # Clean up code
                code = code.strip()
                if code.startswith("```python"):
                    code = code[9:]
                if code.startswith("```"):
                    code = code[3:]
                if code.endswith("```"):
                    code = code[:-3]
                return code.strip()
            except Exception as e:
                logger.warning(f"LLM generation failed: {e}")

        # Fallback to template-based generation
        params_str = ", ".join(
            f"{name}: {info.get('type', 'Any')}"
            for name, info in spec.parameters.items()
        )

        template = self._templates["basic"]
        return template.format(
            name=spec.name,
            params=params_str,
            return_type=spec.return_type,
            description=spec.description,
            implementation="# TODO: Implement\n    pass"
        )

    async def _compile_code(
        self,
        code: str,
        func_name: str
    ) -> Optional[Callable]:
        """Compile code to a callable."""
        try:
            # Create namespace for exec
            namespace = {
                "asyncio": asyncio,
                "logging": logging,
                "Dict": Dict,
                "List": List,
                "Any": Any,
                "Optional": Optional
            }

            # Execute code to define function
            exec(code, namespace)

            # Get function from namespace
            if func_name in namespace:
                return namespace[func_name]

            logger.warning(f"Function {func_name} not found in compiled code")
            return None

        except Exception as e:
            logger.error(f"Failed to compile code: {e}")
            return None

    async def create_from_description(
        self,
        description: str,
        category: Optional[ToolCategory] = None
    ) -> DynamicTool:
        """
        Create a tool from a natural language description.

        Args:
            description: Natural language description
            category: Optional category hint

        Returns:
            Created dynamic tool
        """
        llm = await self._get_llm()

        if llm:
            # Parse description to spec
            parse_prompt = f"""
Parse this tool description into a specification:

Description: {description}

Return a JSON object with:
{{
    "name": "function_name",
    "description": "what it does",
    "category": "{category.value if category else 'custom'}",
    "parameters": {{"param_name": {{"type": "str", "description": "..."}}}},
    "return_type": "str"
}}
"""
            try:
                spec_json = await llm.generate(parse_prompt, temperature=0.2)
                # Parse JSON
                spec_data = json.loads(spec_json)

                spec = ToolSpec(
                    name=spec_data["name"],
                    description=spec_data["description"],
                    category=ToolCategory(spec_data.get("category", "custom")),
                    parameters=spec_data.get("parameters", {}),
                    return_type=spec_data.get("return_type", "Any")
                )

                return await self.create_from_spec(spec)

            except Exception as e:
                logger.warning(f"Failed to parse description: {e}")

        # Fallback: create simple spec
        name = description.lower().replace(" ", "_")[:30]
        spec = ToolSpec(
            name=name,
            description=description,
            category=category or ToolCategory.CUSTOM,
            parameters={},
            return_type="Any"
        )

        return await self.create_from_spec(spec, generate_code=False)

    def wrap_function(
        self,
        func: Callable,
        name: Optional[str] = None,
        category: ToolCategory = ToolCategory.CUSTOM
    ) -> DynamicTool:
        """
        Wrap an existing function as a dynamic tool.

        Args:
            func: Function to wrap
            name: Optional name override
            category: Tool category

        Returns:
            Dynamic tool wrapper
        """
        tool_id = f"wrap_{uuid.uuid4().hex[:8]}"
        func_name = name or func.__name__

        # Extract signature
        sig = inspect.signature(func)
        parameters = {}

        for param_name, param in sig.parameters.items():
            param_type = "Any"
            if param.annotation != inspect.Parameter.empty:
                param_type = str(param.annotation)

            parameters[param_name] = {
                "type": param_type,
                "required": param.default == inspect.Parameter.empty
            }

        return_type = "Any"
        if sig.return_annotation != inspect.Signature.empty:
            return_type = str(sig.return_annotation)

        signature = ToolSignature(
            name=func_name,
            parameters=parameters,
            return_type=return_type,
            description=func.__doc__ or f"Wrapped function: {func_name}"
        )

        tool = DynamicTool(
            id=tool_id,
            name=func_name,
            description=func.__doc__ or f"Wrapped function: {func_name}",
            tool_type=ToolType.WRAPPED,
            category=category,
            signature=signature,
            handler=func
        )

        self._tools[tool_id] = tool
        return tool

    async def invoke(
        self,
        tool_id: str,
        **kwargs
    ) -> Any:
        """
        Invoke a dynamic tool.

        Args:
            tool_id: Tool ID
            **kwargs: Tool arguments

        Returns:
            Tool result
        """
        tool = self._tools.get(tool_id)
        if not tool:
            raise ValueError(f"Tool {tool_id} not found")

        if not tool.handler:
            raise ValueError(f"Tool {tool_id} has no handler")

        try:
            tool.usage_count += 1

            if asyncio.iscoroutinefunction(tool.handler):
                result = await tool.handler(**kwargs)
            else:
                result = tool.handler(**kwargs)

            return result

        except Exception as e:
            # Update success rate
            tool.success_rate = (
                tool.success_rate * (tool.usage_count - 1) / tool.usage_count
            )
            raise

    def get_tool(self, tool_id: str) -> Optional[DynamicTool]:
        """Get a tool by ID."""
        return self._tools.get(tool_id)

    def list_tools(
        self,
        category: Optional[ToolCategory] = None
    ) -> List[DynamicTool]:
        """List all tools, optionally filtered by category."""
        tools = list(self._tools.values())

        if category:
            tools = [t for t in tools if t.category == category]

        return tools

    def delete_tool(self, tool_id: str) -> bool:
        """Delete a tool."""
        if tool_id in self._tools:
            del self._tools[tool_id]
            return True
        return False

    def get_status(self) -> Dict[str, Any]:
        """Get factory status."""
        return {
            "total_tools": len(self._tools),
            "by_type": {
                t.value: sum(1 for tool in self._tools.values() if tool.tool_type == t)
                for t in ToolType
            },
            "by_category": {
                c.value: sum(1 for tool in self._tools.values() if tool.category == c)
                for c in ToolCategory
            }
        }


# Global instance
_tool_factory: Optional[DynamicToolFactory] = None


def get_tool_factory() -> DynamicToolFactory:
    """Get or create tool factory instance."""
    global _tool_factory
    if _tool_factory is None:
        _tool_factory = DynamicToolFactory()
    return _tool_factory

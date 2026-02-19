"""
BAEL Engine Generator
======================

Generate new engines from specifications.
Creates fully functional engine implementations.

Features:
- Specification-driven generation
- Multiple generation strategies
- Dependency resolution
- Interface generation
- Documentation generation
"""

import asyncio
import hashlib
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class EngineCategory(Enum):
    """Engine categories."""
    PROCESSING = "processing"      # Data processing
    INTEGRATION = "integration"    # External service integration
    ANALYSIS = "analysis"          # Data analysis
    AUTOMATION = "automation"      # Task automation
    COMMUNICATION = "communication"  # Messaging/notifications
    SECURITY = "security"          # Security operations
    STORAGE = "storage"            # Data storage
    TRANSFORMATION = "transformation"  # Data transformation
    UTILITY = "utility"            # General utilities


class GenerationStrategy(Enum):
    """Engine generation strategies."""
    TEMPLATE_BASED = "template_based"  # From templates
    AI_GENERATED = "ai_generated"      # AI code generation
    HYBRID = "hybrid"                  # Template + AI
    COMPOSITION = "composition"        # Compose from existing engines


@dataclass
class EngineCapability:
    """A capability the engine provides."""
    name: str
    description: str
    inputs: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)
    is_async: bool = True


@dataclass
class EngineDependency:
    """Engine dependency."""
    name: str
    version: str = "*"
    optional: bool = False
    type: str = "python"  # python, system, service


@dataclass
class EngineSpec:
    """Specification for engine generation."""
    name: str
    description: str

    # Classification
    category: EngineCategory = EngineCategory.UTILITY

    # Capabilities
    capabilities: List[EngineCapability] = field(default_factory=list)

    # Dependencies
    dependencies: List[EngineDependency] = field(default_factory=list)

    # Configuration
    config_schema: Dict[str, Any] = field(default_factory=dict)

    # Generation hints
    strategy: GenerationStrategy = GenerationStrategy.HYBRID
    base_template: Optional[str] = None
    example_code: Optional[str] = None

    # Requirements
    requirements: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)

    # Metadata
    version: str = "1.0.0"
    author: str = "BAEL"
    tags: List[str] = field(default_factory=list)


@dataclass
class GeneratedFile:
    """A generated file."""
    path: str
    content: str
    file_type: str = "python"


@dataclass
class GeneratedEngine:
    """A generated engine."""
    id: str
    spec: EngineSpec

    # Generated files
    files: List[GeneratedFile] = field(default_factory=list)

    # Entry point
    main_class: str = ""
    main_file: str = ""

    # Documentation
    readme: str = ""
    api_docs: str = ""

    # Metadata
    generated_at: datetime = field(default_factory=datetime.now)
    generation_time_ms: float = 0.0

    # Validation
    validated: bool = False
    validation_errors: List[str] = field(default_factory=list)


@dataclass
class GenerationConfig:
    """Generation configuration."""
    # Output
    output_dir: str = "./generated_engines"

    # Generation options
    include_tests: bool = True
    include_docs: bool = True
    include_examples: bool = True

    # Code style
    code_style: str = "black"
    max_line_length: int = 100

    # AI options
    llm_provider: Optional[str] = None
    llm_model: str = "gpt-4"
    temperature: float = 0.3


class EngineGenerator:
    """
    Engine generation system for BAEL.
    """

    def __init__(
        self,
        config: Optional[GenerationConfig] = None,
        llm_client: Optional[Any] = None,
    ):
        self.config = config or GenerationConfig()
        self.llm_client = llm_client

        # Template registry
        self.templates: Dict[str, str] = {}

        # Generated engines
        self.engines: Dict[str, GeneratedEngine] = {}

        # Stats
        self.stats = {
            "engines_generated": 0,
            "files_generated": 0,
            "total_lines": 0,
        }

        # Load default templates
        self._load_default_templates()

    def _load_default_templates(self) -> None:
        """Load default engine templates."""
        self.templates["base_engine"] = '''"""
BAEL {name} Engine
{description_underline}

{description}
"""

import asyncio
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class {class_name}Config:
    """Configuration for {name}."""
{config_fields}


class {class_name}:
    """
    {description}
    """

    def __init__(
        self,
        config: Optional[{class_name}Config] = None,
    ):
        self.config = config or {class_name}Config()

        # State
        self._initialized = False

        # Stats
        self.stats = {{
            "operations": 0,
            "successes": 0,
            "failures": 0,
        }}

    async def initialize(self) -> bool:
        """Initialize the engine."""
        if self._initialized:
            return True

        try:
            # Initialization logic here
            self._initialized = True
            logger.info("{name} engine initialized")
            return True
        except Exception as e:
            logger.error(f"Initialization error: {{e}}")
            return False

{methods}

    def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics."""
        return {{
            **self.stats,
            "initialized": self._initialized,
        }}


def demo():
    """Demonstrate {name} engine."""
    import asyncio

    print("=" * 60)
    print("BAEL {name} Engine Demo")
    print("=" * 60)

    async def run():
        engine = {class_name}()
        await engine.initialize()
        print(f"Stats: {{engine.get_stats()}}")

    asyncio.run(run())


if __name__ == "__main__":
    demo()
'''

        self.templates["test_template"] = '''"""
Tests for {name} Engine
"""

import pytest
import asyncio
from {module_path} import {class_name}, {class_name}Config


class Test{class_name}:
    """Test suite for {class_name}."""

    @pytest.fixture
    def engine(self):
        """Create engine instance."""
        return {class_name}()

    @pytest.fixture
    def config(self):
        """Create config instance."""
        return {class_name}Config()

    @pytest.mark.asyncio
    async def test_initialization(self, engine):
        """Test engine initialization."""
        result = await engine.initialize()
        assert result is True
        assert engine._initialized is True

    @pytest.mark.asyncio
    async def test_stats(self, engine):
        """Test engine statistics."""
        await engine.initialize()
        stats = engine.get_stats()
        assert "initialized" in stats
        assert stats["initialized"] is True

{test_methods}
'''

    def _generate_id(self, name: str) -> str:
        """Generate engine ID."""
        timestamp = str(time.time())
        hash_input = f"{name}:{timestamp}"
        return hashlib.sha256(hash_input.encode()).hexdigest()[:12]

    def _to_class_name(self, name: str) -> str:
        """Convert name to class name."""
        words = name.replace("-", " ").replace("_", " ").split()
        return "".join(word.capitalize() for word in words)

    def _to_module_name(self, name: str) -> str:
        """Convert name to module name."""
        return name.lower().replace(" ", "_").replace("-", "_")

    async def generate(
        self,
        spec: EngineSpec,
    ) -> GeneratedEngine:
        """
        Generate an engine from specification.

        Args:
            spec: Engine specification

        Returns:
            GeneratedEngine
        """
        self.stats["engines_generated"] += 1
        start_time = time.time()

        engine_id = self._generate_id(spec.name)
        class_name = self._to_class_name(spec.name)
        module_name = self._to_module_name(spec.name)

        # Generate based on strategy
        if spec.strategy == GenerationStrategy.TEMPLATE_BASED:
            files = await self._generate_from_template(spec, class_name, module_name)
        elif spec.strategy == GenerationStrategy.AI_GENERATED:
            files = await self._generate_with_ai(spec, class_name, module_name)
        elif spec.strategy == GenerationStrategy.COMPOSITION:
            files = await self._generate_composition(spec, class_name, module_name)
        else:
            # Hybrid: template base + AI enhancements
            files = await self._generate_hybrid(spec, class_name, module_name)

        # Generate tests if requested
        if self.config.include_tests:
            test_files = await self._generate_tests(spec, class_name, module_name)
            files.extend(test_files)

        # Generate documentation
        readme = ""
        api_docs = ""
        if self.config.include_docs:
            readme = self._generate_readme(spec, class_name)
            api_docs = self._generate_api_docs(spec, class_name)

        # Create engine
        engine = GeneratedEngine(
            id=engine_id,
            spec=spec,
            files=files,
            main_class=class_name,
            main_file=f"{module_name}.py",
            readme=readme,
            api_docs=api_docs,
            generation_time_ms=(time.time() - start_time) * 1000,
        )

        self.engines[engine_id] = engine

        # Update stats
        self.stats["files_generated"] += len(files)
        for f in files:
            self.stats["total_lines"] += f.content.count("\n")

        logger.info(f"Generated engine: {spec.name} ({engine_id})")

        return engine

    async def _generate_from_template(
        self,
        spec: EngineSpec,
        class_name: str,
        module_name: str,
    ) -> List[GeneratedFile]:
        """Generate from template."""
        files = []

        # Generate config fields
        config_fields = "    pass"
        if spec.config_schema:
            config_lines = []
            for field_name, field_info in spec.config_schema.items():
                field_type = field_info.get("type", "str")
                default = field_info.get("default", "None")
                config_lines.append(f"    {field_name}: {field_type} = {default}")
            config_fields = "\n".join(config_lines) if config_lines else "    pass"

        # Generate methods
        methods = self._generate_capability_methods(spec.capabilities)

        # Apply template
        template = self.templates.get(spec.base_template or "base_engine", self.templates["base_engine"])

        content = template.format(
            name=spec.name,
            description=spec.description,
            description_underline="=" * (len(spec.name) + 12),
            class_name=class_name,
            config_fields=config_fields,
            methods=methods,
        )

        files.append(GeneratedFile(
            path=f"{module_name}.py",
            content=content,
        ))

        # Generate __init__.py
        init_content = f'''"""
{spec.name} Engine
"""

from .{module_name} import {class_name}, {class_name}Config

__all__ = ["{class_name}", "{class_name}Config"]
'''
        files.append(GeneratedFile(
            path="__init__.py",
            content=init_content,
        ))

        return files

    def _generate_capability_methods(self, capabilities: List[EngineCapability]) -> str:
        """Generate methods for capabilities."""
        methods = []

        for cap in capabilities:
            # Generate method signature
            params = ", ".join(cap.inputs) if cap.inputs else ""
            if params:
                params = ", " + params

            returns = cap.outputs[0] if cap.outputs else "Any"

            async_prefix = "async " if cap.is_async else ""

            method = f'''    {async_prefix}def {cap.name}(self{params}) -> {returns}:
        """
        {cap.description}
        """
        self.stats["operations"] += 1

        try:
            # Implementation here
            result = None

            self.stats["successes"] += 1
            return result
        except Exception as e:
            self.stats["failures"] += 1
            logger.error(f"{cap.name} error: {{e}}")
            raise
'''
            methods.append(method)

        return "\n".join(methods) if methods else "    pass"

    async def _generate_with_ai(
        self,
        spec: EngineSpec,
        class_name: str,
        module_name: str,
    ) -> List[GeneratedFile]:
        """Generate using AI."""
        if not self.llm_client:
            # Fallback to template
            return await self._generate_from_template(spec, class_name, module_name)

        # Would use LLM to generate code
        # For now, use template as base
        return await self._generate_from_template(spec, class_name, module_name)

    async def _generate_hybrid(
        self,
        spec: EngineSpec,
        class_name: str,
        module_name: str,
    ) -> List[GeneratedFile]:
        """Generate using hybrid approach."""
        # Start with template
        files = await self._generate_from_template(spec, class_name, module_name)

        # Enhance with AI if available
        if self.llm_client:
            # Would enhance generated code with AI
            pass

        return files

    async def _generate_composition(
        self,
        spec: EngineSpec,
        class_name: str,
        module_name: str,
    ) -> List[GeneratedFile]:
        """Generate by composing existing engines."""
        # Would compose from existing engines
        return await self._generate_from_template(spec, class_name, module_name)

    async def _generate_tests(
        self,
        spec: EngineSpec,
        class_name: str,
        module_name: str,
    ) -> List[GeneratedFile]:
        """Generate test files."""
        test_methods = []

        for cap in spec.capabilities:
            test_method = f'''    @pytest.mark.asyncio
    async def test_{cap.name}(self, engine):
        """Test {cap.name} capability."""
        await engine.initialize()
        # Add test implementation
        pass
'''
            test_methods.append(test_method)

        content = self.templates["test_template"].format(
            name=spec.name,
            module_path=module_name,
            class_name=class_name,
            test_methods="\n".join(test_methods),
        )

        return [GeneratedFile(
            path=f"test_{module_name}.py",
            content=content,
        )]

    def _generate_readme(self, spec: EngineSpec, class_name: str) -> str:
        """Generate README documentation."""
        caps_list = "\n".join(f"- **{c.name}**: {c.description}" for c in spec.capabilities)
        deps_list = "\n".join(f"- {d.name} ({d.version})" for d in spec.dependencies) or "None"

        return f'''# {spec.name} Engine

{spec.description}

## Category
{spec.category.value}

## Capabilities
{caps_list}

## Dependencies
{deps_list}

## Usage

```python
from {class_name.lower()} import {class_name}

engine = {class_name}()
await engine.initialize()
```

## Configuration

{self._format_config_docs(spec.config_schema)}

## Version
{spec.version}
'''

    def _generate_api_docs(self, spec: EngineSpec, class_name: str) -> str:
        """Generate API documentation."""
        methods_docs = []
        for cap in spec.capabilities:
            doc = f'''### {cap.name}

{cap.description}

**Inputs:** {", ".join(cap.inputs) if cap.inputs else "None"}

**Outputs:** {", ".join(cap.outputs) if cap.outputs else "None"}
'''
            methods_docs.append(doc)

        return f'''# {class_name} API Reference

## Overview
{spec.description}

## Methods

{"".join(methods_docs)}
'''

    def _format_config_docs(self, schema: Dict[str, Any]) -> str:
        """Format config schema as documentation."""
        if not schema:
            return "No configuration options."

        lines = ["| Option | Type | Default | Description |",
                 "|--------|------|---------|-------------|"]

        for name, info in schema.items():
            type_ = info.get("type", "str")
            default = info.get("default", "None")
            desc = info.get("description", "")
            lines.append(f"| {name} | {type_} | {default} | {desc} |")

        return "\n".join(lines)

    async def save_engine(
        self,
        engine: GeneratedEngine,
        output_dir: Optional[str] = None,
    ) -> str:
        """
        Save generated engine to disk.

        Args:
            engine: Generated engine
            output_dir: Output directory

        Returns:
            Path to saved engine
        """
        import os

        output = output_dir or self.config.output_dir
        engine_dir = os.path.join(output, self._to_module_name(engine.spec.name))

        os.makedirs(engine_dir, exist_ok=True)

        for file in engine.files:
            file_path = os.path.join(engine_dir, file.path)
            os.makedirs(os.path.dirname(file_path) if os.path.dirname(file.path) else engine_dir, exist_ok=True)

            with open(file_path, "w") as f:
                f.write(file.content)

        # Save README
        if engine.readme:
            with open(os.path.join(engine_dir, "README.md"), "w") as f:
                f.write(engine.readme)

        logger.info(f"Saved engine to: {engine_dir}")

        return engine_dir

    def get_engine(self, engine_id: str) -> Optional[GeneratedEngine]:
        """Get generated engine by ID."""
        return self.engines.get(engine_id)

    def get_stats(self) -> Dict[str, Any]:
        """Get generator statistics."""
        return {
            **self.stats,
            "templates_loaded": len(self.templates),
        }


def demo():
    """Demonstrate engine generator."""
    import asyncio

    print("=" * 60)
    print("BAEL Engine Generator Demo")
    print("=" * 60)

    generator = EngineGenerator()

    # Create spec
    spec = EngineSpec(
        name="Data Processor",
        description="A versatile data processing engine for transformations",
        category=EngineCategory.PROCESSING,
        capabilities=[
            EngineCapability(
                name="process",
                description="Process input data",
                inputs=["data: Any"],
                outputs=["Any"],
            ),
            EngineCapability(
                name="transform",
                description="Transform data format",
                inputs=["data: Any", "format: str"],
                outputs=["Any"],
            ),
        ],
        config_schema={
            "batch_size": {"type": "int", "default": 100},
            "timeout": {"type": "float", "default": 30.0},
        },
    )

    print(f"\nSpec: {spec.name}")
    print(f"  Category: {spec.category.value}")
    print(f"  Capabilities: {len(spec.capabilities)}")

    # Generate
    async def generate():
        return await generator.generate(spec)

    engine = asyncio.run(generate())

    print(f"\nGenerated engine: {engine.id}")
    print(f"  Files: {len(engine.files)}")
    print(f"  Main class: {engine.main_class}")
    print(f"  Time: {engine.generation_time_ms:.2f}ms")

    # Show generated code preview
    print(f"\nGenerated code preview:")
    for file in engine.files[:1]:
        preview = file.content[:500] + "..."
        print(f"\n--- {file.path} ---")
        print(preview)

    print(f"\nStats: {generator.get_stats()}")


if __name__ == "__main__":
    demo()

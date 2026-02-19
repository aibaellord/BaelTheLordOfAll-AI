"""
Code Architect Agent - Designs and Structures Codebases
=========================================================

The architect that designs perfect code structures, patterns,
and architectural decisions.

"Architecture is frozen music; code architecture is frozen thought." — Ba'el
"""

import ast
import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
import re

from .agent_factory import (
    AutonomousAgent,
    AgentConfig,
    AgentType,
    AgentCapability,
    AgentTask,
    AgentResult,
    autonomous_agent,
)


logger = logging.getLogger("BAEL.CodeArchitect")


class ArchitecturePattern(Enum):
    """Common architecture patterns."""
    MVC = "mvc"
    MVVM = "mvvm"
    CLEAN = "clean_architecture"
    HEXAGONAL = "hexagonal"
    MICROSERVICES = "microservices"
    MONOLITH = "monolith"
    EVENT_DRIVEN = "event_driven"
    CQRS = "cqrs"
    LAYERED = "layered"
    PLUGIN = "plugin"


class DesignPattern(Enum):
    """Design patterns."""
    SINGLETON = "singleton"
    FACTORY = "factory"
    ABSTRACT_FACTORY = "abstract_factory"
    BUILDER = "builder"
    PROTOTYPE = "prototype"
    ADAPTER = "adapter"
    BRIDGE = "bridge"
    COMPOSITE = "composite"
    DECORATOR = "decorator"
    FACADE = "facade"
    FLYWEIGHT = "flyweight"
    PROXY = "proxy"
    CHAIN_OF_RESPONSIBILITY = "chain_of_responsibility"
    COMMAND = "command"
    ITERATOR = "iterator"
    MEDIATOR = "mediator"
    MEMENTO = "memento"
    OBSERVER = "observer"
    STATE = "state"
    STRATEGY = "strategy"
    TEMPLATE_METHOD = "template_method"
    VISITOR = "visitor"


@dataclass
class ArchitectureAnalysis:
    """Analysis of a codebase's architecture."""
    detected_patterns: List[ArchitecturePattern] = field(default_factory=list)
    detected_design_patterns: List[DesignPattern] = field(default_factory=list)
    layer_structure: Dict[str, List[str]] = field(default_factory=dict)
    module_dependencies: Dict[str, List[str]] = field(default_factory=dict)
    coupling_score: float = 0.0
    cohesion_score: float = 0.0
    complexity_score: float = 0.0
    recommendations: List[str] = field(default_factory=list)
    violations: List[str] = field(default_factory=list)


@dataclass
class ArchitectureProposal:
    """A proposed architecture change."""
    pattern: ArchitecturePattern
    description: str
    changes_required: List[str]
    benefits: List[str]
    risks: List[str]
    effort_estimate: str
    priority: int


@autonomous_agent(AgentType.CODE_ARCHITECT)
class CodeArchitectAgent(AutonomousAgent):
    """Agent that designs and analyzes code architecture."""

    def __init__(self, config: AgentConfig):
        super().__init__(config)
        self.analyzed_projects: Dict[str, ArchitectureAnalysis] = {}
        self.proposals: List[ArchitectureProposal] = []

    async def _setup(self) -> None:
        """Initialize the code architect."""
        self.config.capabilities = [
            AgentCapability.CODE_ANALYSIS,
            AgentCapability.ARCHITECTURE_ANALYSIS,
            AgentCapability.CODE_GENERATION,
            AgentCapability.REPORTING,
        ]
        logger.info("Code Architect Agent initialized")

    async def execute_task(self, task: AgentTask) -> AgentResult:
        """Execute an architecture task."""
        start = datetime.now()

        try:
            if task.parameters.get("action") == "analyze":
                result = await self._analyze_architecture(task.target_path)
            elif task.parameters.get("action") == "propose":
                result = await self._propose_architecture(
                    task.target_path,
                    task.parameters.get("target_pattern")
                )
            elif task.parameters.get("action") == "refactor":
                result = await self._refactor_to_pattern(
                    task.target_path,
                    task.parameters.get("pattern")
                )
            else:
                # Default: full analysis
                result = await self._analyze_architecture(task.target_path)

            return AgentResult(
                task_id=task.id,
                agent_id=self.id,
                agent_type=self.agent_type,
                success=True,
                result=result,
                recommendations=result.recommendations if hasattr(result, 'recommendations') else [],
            )

        except Exception as e:
            logger.error(f"Architecture task failed: {e}")
            return AgentResult(
                task_id=task.id,
                agent_id=self.id,
                agent_type=self.agent_type,
                success=False,
                error=str(e),
            )

    async def _analyze_architecture(self, path: Path) -> ArchitectureAnalysis:
        """Analyze the architecture of a codebase."""
        analysis = ArchitectureAnalysis()

        if not path or not path.exists():
            return analysis

        # Scan directory structure
        python_files = list(path.rglob("*.py"))

        # Analyze layer structure
        layers = {
            "core": [],
            "api": [],
            "ui": [],
            "infrastructure": [],
            "domain": [],
            "application": [],
            "tests": [],
        }

        for file in python_files:
            relative = str(file.relative_to(path))
            for layer in layers:
                if layer in relative.lower():
                    layers[layer].append(relative)
                    break

        analysis.layer_structure = {k: v for k, v in layers.items() if v}

        # Detect architecture patterns
        if "core" in analysis.layer_structure and "api" in analysis.layer_structure:
            analysis.detected_patterns.append(ArchitecturePattern.LAYERED)

        if "domain" in analysis.layer_structure and "application" in analysis.layer_structure:
            analysis.detected_patterns.append(ArchitecturePattern.CLEAN)

        # Analyze dependencies
        for file in python_files[:50]:  # Limit for performance
            try:
                content = file.read_text()
                imports = self._extract_imports(content)
                analysis.module_dependencies[str(file.name)] = imports
            except Exception:
                continue

        # Calculate scores
        analysis.coupling_score = self._calculate_coupling(analysis.module_dependencies)
        analysis.cohesion_score = self._calculate_cohesion(analysis.layer_structure)
        analysis.complexity_score = len(python_files) / 100.0

        # Generate recommendations
        if analysis.coupling_score > 0.7:
            analysis.recommendations.append(
                "High coupling detected. Consider applying Dependency Injection."
            )

        if analysis.cohesion_score < 0.5:
            analysis.recommendations.append(
                "Low cohesion detected. Consider reorganizing modules by feature."
            )

        if not analysis.detected_patterns:
            analysis.recommendations.append(
                "No clear architecture pattern detected. Consider adopting Clean Architecture."
            )

        self.analyzed_projects[str(path)] = analysis
        self.metrics.improvements_made += 1

        return analysis

    def _extract_imports(self, content: str) -> List[str]:
        """Extract imports from Python code."""
        imports = []
        import_pattern = r'^(?:from\s+(\S+)\s+import|import\s+(\S+))'

        for line in content.split('\n'):
            match = re.match(import_pattern, line.strip())
            if match:
                imports.append(match.group(1) or match.group(2))

        return imports

    def _calculate_coupling(self, dependencies: Dict[str, List[str]]) -> float:
        """Calculate coupling score (0-1, lower is better)."""
        if not dependencies:
            return 0.0

        total_deps = sum(len(deps) for deps in dependencies.values())
        avg_deps = total_deps / len(dependencies)

        # Normalize to 0-1 (assuming 10+ deps is high)
        return min(1.0, avg_deps / 10.0)

    def _calculate_cohesion(self, layers: Dict[str, List[str]]) -> float:
        """Calculate cohesion score (0-1, higher is better)."""
        if not layers:
            return 0.0

        # More layers with files = better cohesion
        layers_with_files = sum(1 for v in layers.values() if v)
        return layers_with_files / max(len(layers), 1)

    async def _propose_architecture(
        self,
        path: Path,
        target_pattern: Optional[ArchitecturePattern] = None
    ) -> List[ArchitectureProposal]:
        """Propose architecture improvements."""
        analysis = await self._analyze_architecture(path)
        proposals = []

        if target_pattern is None:
            # Recommend based on analysis
            if analysis.coupling_score > 0.5:
                proposals.append(ArchitectureProposal(
                    pattern=ArchitecturePattern.HEXAGONAL,
                    description="Adopt Hexagonal Architecture for better isolation",
                    changes_required=[
                        "Create ports and adapters directories",
                        "Move domain logic to core",
                        "Create interface layers",
                    ],
                    benefits=[
                        "Reduced coupling",
                        "Better testability",
                        "Framework independence",
                    ],
                    risks=["Significant refactoring effort"],
                    effort_estimate="2-4 weeks",
                    priority=1,
                ))

        self.proposals.extend(proposals)
        return proposals

    async def _refactor_to_pattern(
        self,
        path: Path,
        pattern: ArchitecturePattern
    ) -> Dict[str, Any]:
        """Refactor codebase to a specific pattern."""
        # This would generate refactoring commands/scripts
        return {
            "pattern": pattern.value,
            "status": "plan_generated",
            "steps": [
                "Create new directory structure",
                "Move files to appropriate layers",
                "Update imports",
                "Create interface definitions",
                "Update dependency injection",
            ]
        }

    async def analyze_project(self, path: Path) -> ArchitectureAnalysis:
        """Public method to analyze a project."""
        task = AgentTask(
            name="Analyze Architecture",
            target_path=path,
            parameters={"action": "analyze"}
        )
        await self.submit_task(task)
        return await self._analyze_architecture(path)

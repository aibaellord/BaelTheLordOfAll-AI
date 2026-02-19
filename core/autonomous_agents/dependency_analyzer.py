"""
Dependency Analyzer Agent - Analyzes and Optimizes Dependencies
=================================================================

The guardian that ensures your dependencies are secure, up-to-date,
and minimal.

"A chain is only as strong as its weakest link." — Ba'el
"""

import asyncio
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from .agent_factory import (
    AutonomousAgent, AgentConfig, AgentType, AgentCapability,
    AgentTask, AgentResult, autonomous_agent,
)


logger = logging.getLogger("BAEL.DependencyAnalyzer")


class DependencyType(Enum):
    RUNTIME = "runtime"
    DEVELOPMENT = "development"
    OPTIONAL = "optional"
    PEER = "peer"
    TRANSITIVE = "transitive"


class RiskLevel(Enum):
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4
    NONE = 5


@dataclass
class Dependency:
    name: str
    version: str
    dep_type: DependencyType
    latest_version: str = ""
    is_outdated: bool = False
    risk_level: RiskLevel = RiskLevel.NONE
    vulnerabilities: List[str] = field(default_factory=list)
    license: str = ""
    size_kb: int = 0
    used_by: List[str] = field(default_factory=list)
    transitive_deps: int = 0


@dataclass
class DependencyReport:
    target_path: str
    total_dependencies: int = 0
    direct_dependencies: int = 0
    transitive_dependencies: int = 0
    outdated_count: int = 0
    vulnerable_count: int = 0
    dependencies: List[Dependency] = field(default_factory=list)
    unused_dependencies: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    risk_score: float = 0.0


@autonomous_agent(AgentType.DEPENDENCY_ANALYZER)
class DependencyAnalyzerAgent(AutonomousAgent):
    """Agent that analyzes project dependencies."""

    def __init__(self, config: AgentConfig):
        super().__init__(config)
        self.reports: Dict[str, DependencyReport] = {}

    async def _setup(self) -> None:
        self.config.capabilities = [
            AgentCapability.DEPENDENCY_ANALYSIS,
            AgentCapability.SECURITY_ANALYSIS,
            AgentCapability.REPORTING,
        ]
        logger.info("Dependency Analyzer Agent initialized")

    async def execute_task(self, task: AgentTask) -> AgentResult:
        try:
            result = await self._analyze_dependencies(task.target_path)
            return AgentResult(
                task_id=task.id,
                agent_id=self.id,
                agent_type=self.agent_type,
                success=True,
                result=result,
                recommendations=result.recommendations,
            )
        except Exception as e:
            return AgentResult(
                task_id=task.id,
                agent_id=self.id,
                agent_type=self.agent_type,
                success=False,
                error=str(e),
            )

    async def _analyze_dependencies(self, path: Path) -> DependencyReport:
        report = DependencyReport(target_path=str(path))

        if not path or not path.exists():
            return report

        # Parse requirements.txt
        req_file = path / "requirements.txt"
        if req_file.exists():
            deps = self._parse_requirements(req_file)
            report.dependencies.extend(deps)

        # Parse pyproject.toml
        pyproject = path / "pyproject.toml"
        if pyproject.exists():
            deps = self._parse_pyproject(pyproject)
            report.dependencies.extend(deps)

        # Parse package.json
        pkg_json = path / "package.json"
        if pkg_json.exists():
            deps = self._parse_package_json(pkg_json)
            report.dependencies.extend(deps)

        report.total_dependencies = len(report.dependencies)
        report.direct_dependencies = sum(
            1 for d in report.dependencies if d.dep_type != DependencyType.TRANSITIVE
        )
        report.outdated_count = sum(1 for d in report.dependencies if d.is_outdated)
        report.vulnerable_count = sum(1 for d in report.dependencies if d.vulnerabilities)

        # Find unused dependencies
        report.unused_dependencies = await self._find_unused(path, report.dependencies)

        # Calculate risk
        report.risk_score = self._calculate_risk(report)
        report.recommendations = self._generate_recommendations(report)

        self.reports[str(path)] = report
        return report

    def _parse_requirements(self, path: Path) -> List[Dependency]:
        deps = []
        try:
            for line in path.read_text().split('\n'):
                line = line.strip()
                if line and not line.startswith('#') and not line.startswith('-'):
                    # Parse name and version
                    match = re.match(r'^([a-zA-Z0-9_-]+)([<>=!]+.*)?', line)
                    if match:
                        name = match.group(1)
                        version = match.group(2) or "any"
                        deps.append(Dependency(
                            name=name,
                            version=version.strip(),
                            dep_type=DependencyType.RUNTIME,
                        ))
        except Exception as e:
            logger.debug(f"Error parsing requirements: {e}")
        return deps

    def _parse_pyproject(self, path: Path) -> List[Dependency]:
        deps = []
        try:
            content = path.read_text()
            # Simple regex parsing
            in_deps = False
            for line in content.split('\n'):
                if 'dependencies' in line and '=' in line:
                    in_deps = True
                elif in_deps:
                    if line.strip().startswith(']'):
                        in_deps = False
                    elif '"' in line:
                        match = re.search(r'"([^"]+)"', line)
                        if match:
                            dep_str = match.group(1)
                            parts = re.split(r'[<>=]', dep_str)
                            if parts:
                                deps.append(Dependency(
                                    name=parts[0].strip(),
                                    version=dep_str[len(parts[0]):] or "any",
                                    dep_type=DependencyType.RUNTIME,
                                ))
        except Exception as e:
            logger.debug(f"Error parsing pyproject.toml: {e}")
        return deps

    def _parse_package_json(self, path: Path) -> List[Dependency]:
        deps = []
        try:
            import json
            data = json.loads(path.read_text())

            for name, version in data.get("dependencies", {}).items():
                deps.append(Dependency(
                    name=name,
                    version=version,
                    dep_type=DependencyType.RUNTIME,
                ))

            for name, version in data.get("devDependencies", {}).items():
                deps.append(Dependency(
                    name=name,
                    version=version,
                    dep_type=DependencyType.DEVELOPMENT,
                ))
        except Exception as e:
            logger.debug(f"Error parsing package.json: {e}")
        return deps

    async def _find_unused(self, path: Path, deps: List[Dependency]) -> List[str]:
        unused = []

        # Get all imports from Python files
        imports = set()
        for py_file in path.rglob("*.py"):
            try:
                content = py_file.read_text()
                for match in re.finditer(r'^(?:from|import)\s+(\w+)', content, re.MULTILINE):
                    imports.add(match.group(1).lower())
            except Exception:
                continue

        # Check which dependencies are not imported
        for dep in deps:
            dep_name = dep.name.lower().replace('-', '_')
            if dep_name not in imports and dep.name.lower() not in imports:
                unused.append(dep.name)

        return unused[:10]  # Limit to 10

    def _calculate_risk(self, report: DependencyReport) -> float:
        score = 0.0
        score += report.vulnerable_count * 20
        score += report.outdated_count * 5
        score += len(report.unused_dependencies) * 2
        return min(100.0, score)

    def _generate_recommendations(self, report: DependencyReport) -> List[str]:
        recommendations = []

        if report.vulnerable_count > 0:
            recommendations.append(
                f"🔴 {report.vulnerable_count} vulnerable dependencies - update immediately"
            )

        if report.outdated_count > 0:
            recommendations.append(
                f"🟡 {report.outdated_count} outdated dependencies - consider updating"
            )

        if report.unused_dependencies:
            recommendations.append(
                f"🟢 {len(report.unused_dependencies)} potentially unused dependencies"
            )

        recommendations.append("Run 'pip-audit' or 'safety check' for vulnerability scan")

        return recommendations

    async def analyze_project(self, path: Path) -> DependencyReport:
        return await self._analyze_dependencies(path)

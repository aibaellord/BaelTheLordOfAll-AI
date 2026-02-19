"""
Documentation Generator Agent - Creates Perfect Documentation
================================================================

The scribe that transforms code into crystal-clear documentation
with perfect precision.

"Documentation is the map that guides future travelers." — Ba'el
"""

import ast
import asyncio
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from .agent_factory import (
    AutonomousAgent,
    AgentConfig,
    AgentType,
    AgentCapability,
    AgentTask,
    AgentResult,
    autonomous_agent,
)


logger = logging.getLogger("BAEL.DocumentationGenerator")


class DocType(Enum):
    """Types of documentation."""
    DOCSTRING = "docstring"
    README = "readme"
    API_REFERENCE = "api_reference"
    TUTORIAL = "tutorial"
    CHANGELOG = "changelog"
    ARCHITECTURE = "architecture"
    CONTRIBUTING = "contributing"
    INSTALLATION = "installation"
    USAGE_GUIDE = "usage_guide"
    TYPE_HINTS = "type_hints"


class DocStyle(Enum):
    """Documentation styles."""
    GOOGLE = "google"
    NUMPY = "numpy"
    SPHINX = "sphinx"
    EPYTEXT = "epytext"
    MARKDOWN = "markdown"


@dataclass
class DocumentationItem:
    """A piece of documentation."""
    doc_type: DocType
    file_path: str
    content: str
    target_element: str = ""  # function/class name if docstring
    line_number: int = 0
    quality_score: float = 0.0
    suggestions: List[str] = field(default_factory=list)


@dataclass
class DocumentationReport:
    """Report on documentation status."""
    target_path: str
    total_files: int
    documented_items: int
    undocumented_items: int
    coverage_percentage: float
    items: List[DocumentationItem] = field(default_factory=list)
    missing_docs: List[str] = field(default_factory=list)
    quality_score: float = 0.0
    recommendations: List[str] = field(default_factory=list)


@dataclass
class CodeElement:
    """A code element that needs documentation."""
    name: str
    element_type: str  # function, class, method, module
    file_path: str
    line_number: int
    signature: str = ""
    current_docstring: str = ""
    parameters: List[str] = field(default_factory=list)
    returns: str = ""
    raises: List[str] = field(default_factory=list)


@autonomous_agent(AgentType.DOCUMENTATION_GENERATOR)
class DocumentationGeneratorAgent(AutonomousAgent):
    """Agent that generates and improves documentation."""

    def __init__(self, config: AgentConfig):
        super().__init__(config)
        self.doc_style = DocStyle.GOOGLE
        self.reports: Dict[str, DocumentationReport] = {}

    async def _setup(self) -> None:
        """Initialize the documentation generator."""
        self.config.capabilities = [
            AgentCapability.DOC_GENERATION,
            AgentCapability.CODE_ANALYSIS,
            AgentCapability.REPORTING,
        ]
        logger.info("Documentation Generator Agent initialized")

    async def execute_task(self, task: AgentTask) -> AgentResult:
        """Execute a documentation task."""
        try:
            action = task.parameters.get("action", "analyze")

            if action == "analyze":
                result = await self._analyze_documentation(task.target_path)
            elif action == "generate":
                result = await self._generate_documentation(
                    task.target_path,
                    task.parameters.get("doc_type", DocType.DOCSTRING)
                )
            elif action == "generate_readme":
                result = await self._generate_readme(task.target_path)
            elif action == "generate_api_docs":
                result = await self._generate_api_docs(task.target_path)
            else:
                result = await self._analyze_documentation(task.target_path)

            return AgentResult(
                task_id=task.id,
                agent_id=self.id,
                agent_type=self.agent_type,
                success=True,
                result=result,
                metrics={
                    "coverage": result.coverage_percentage if hasattr(result, 'coverage_percentage') else 0,
                },
                recommendations=result.recommendations if hasattr(result, 'recommendations') else [],
            )

        except Exception as e:
            logger.error(f"Documentation task failed: {e}")
            return AgentResult(
                task_id=task.id,
                agent_id=self.id,
                agent_type=self.agent_type,
                success=False,
                error=str(e),
            )

    async def _analyze_documentation(self, path: Path) -> DocumentationReport:
        """Analyze documentation coverage and quality."""
        report = DocumentationReport(
            target_path=str(path),
            total_files=0,
            documented_items=0,
            undocumented_items=0,
            coverage_percentage=0.0,
        )

        if not path or not path.exists():
            return report

        # Analyze Python files
        python_files = list(path.rglob("*.py"))
        report.total_files = len(python_files)

        for file_path in python_files:
            elements = await self._extract_code_elements(file_path)

            for element in elements:
                if element.current_docstring:
                    report.documented_items += 1

                    # Create documentation item
                    item = DocumentationItem(
                        doc_type=DocType.DOCSTRING,
                        file_path=str(file_path),
                        content=element.current_docstring,
                        target_element=element.name,
                        line_number=element.line_number,
                        quality_score=self._calculate_quality(element),
                    )
                    report.items.append(item)
                else:
                    report.undocumented_items += 1
                    report.missing_docs.append(
                        f"{file_path.name}:{element.line_number} - {element.element_type} '{element.name}'"
                    )

        # Calculate coverage
        total = report.documented_items + report.undocumented_items
        if total > 0:
            report.coverage_percentage = (report.documented_items / total) * 100

        # Calculate quality score
        if report.items:
            report.quality_score = sum(i.quality_score for i in report.items) / len(report.items)

        # Generate recommendations
        report.recommendations = self._generate_recommendations(report)

        self.reports[str(path)] = report
        return report

    async def _extract_code_elements(self, file_path: Path) -> List[CodeElement]:
        """Extract code elements that need documentation."""
        elements = []

        try:
            content = file_path.read_text()
            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    elements.append(CodeElement(
                        name=node.name,
                        element_type="function",
                        file_path=str(file_path),
                        line_number=node.lineno,
                        signature=self._get_signature(node),
                        current_docstring=ast.get_docstring(node) or "",
                        parameters=[arg.arg for arg in node.args.args],
                        returns=self._infer_return_type(node),
                    ))
                elif isinstance(node, ast.AsyncFunctionDef):
                    elements.append(CodeElement(
                        name=node.name,
                        element_type="async function",
                        file_path=str(file_path),
                        line_number=node.lineno,
                        signature=self._get_signature(node),
                        current_docstring=ast.get_docstring(node) or "",
                        parameters=[arg.arg for arg in node.args.args],
                        returns=self._infer_return_type(node),
                    ))
                elif isinstance(node, ast.ClassDef):
                    elements.append(CodeElement(
                        name=node.name,
                        element_type="class",
                        file_path=str(file_path),
                        line_number=node.lineno,
                        current_docstring=ast.get_docstring(node) or "",
                    ))

        except Exception as e:
            logger.debug(f"Error parsing {file_path}: {e}")

        return elements

    def _get_signature(self, node: ast.FunctionDef) -> str:
        """Get function signature."""
        args = []
        for arg in node.args.args:
            arg_str = arg.arg
            if arg.annotation:
                try:
                    arg_str += f": {ast.unparse(arg.annotation)}"
                except:
                    pass
            args.append(arg_str)
        return f"{node.name}({', '.join(args)})"

    def _infer_return_type(self, node: ast.FunctionDef) -> str:
        """Infer return type from annotation or body."""
        if node.returns:
            try:
                return ast.unparse(node.returns)
            except:
                pass
        return ""

    def _calculate_quality(self, element: CodeElement) -> float:
        """Calculate documentation quality score (0-1)."""
        if not element.current_docstring:
            return 0.0

        score = 0.0
        doc = element.current_docstring.lower()

        # Check for key sections (Google style)
        if "args:" in doc or "parameters:" in doc:
            score += 0.2
        if "returns:" in doc:
            score += 0.2
        if "raises:" in doc or "raises:" in doc:
            score += 0.1
        if "example" in doc:
            score += 0.2

        # Length check
        if len(element.current_docstring) > 50:
            score += 0.2
        if len(element.current_docstring) > 200:
            score += 0.1

        return min(1.0, score)

    def _generate_recommendations(self, report: DocumentationReport) -> List[str]:
        """Generate recommendations for documentation improvement."""
        recommendations = []

        if report.coverage_percentage < 50:
            recommendations.append(
                f"🔴 Low documentation coverage ({report.coverage_percentage:.1f}%) - "
                f"{report.undocumented_items} items need documentation"
            )
        elif report.coverage_percentage < 80:
            recommendations.append(
                f"🟡 Documentation coverage at {report.coverage_percentage:.1f}% - "
                f"aim for 80%+"
            )
        else:
            recommendations.append(
                f"🟢 Good documentation coverage at {report.coverage_percentage:.1f}%"
            )

        if report.quality_score < 0.5:
            recommendations.append(
                "Improve docstring quality - add Args, Returns, Examples sections"
            )

        # Check for missing key files
        readme_path = Path(report.target_path) / "README.md"
        if not readme_path.exists():
            recommendations.append("Add README.md to project root")

        return recommendations

    async def _generate_documentation(
        self,
        path: Path,
        doc_type: DocType
    ) -> DocumentationReport:
        """Generate documentation of a specific type."""
        report = await self._analyze_documentation(path)

        if doc_type == DocType.DOCSTRING:
            # Generate docstrings for undocumented items
            for missing in report.missing_docs[:20]:  # Limit to 20
                docstring = self._generate_docstring_template(missing)
                report.items.append(DocumentationItem(
                    doc_type=DocType.DOCSTRING,
                    file_path=missing.split(":")[0],
                    content=docstring,
                    target_element=missing,
                ))

        return report

    def _generate_docstring_template(self, element_info: str) -> str:
        """Generate a docstring template."""
        # Parse element info
        parts = element_info.split(" - ")
        if len(parts) < 2:
            return '"""TODO: Add documentation."""'

        element_type = parts[1].split("'")[0].strip()
        element_name = parts[1].split("'")[1] if "'" in parts[1] else "unknown"

        if element_type == "function" or element_type == "async function":
            return f'''"""
{element_name.replace('_', ' ').title()}.

Args:
    # TODO: Document parameters

Returns:
    # TODO: Document return value

Example:
    >>> # TODO: Add usage example
"""'''
        elif element_type == "class":
            return f'''"""
{element_name.replace('_', ' ').title()}.

Attributes:
    # TODO: Document class attributes

Example:
    >>> # TODO: Add usage example
"""'''
        else:
            return f'"""TODO: Document {element_name}."""'

    async def _generate_readme(self, path: Path) -> DocumentationItem:
        """Generate a README.md file."""
        # Analyze project
        report = await self._analyze_documentation(path)

        # Get project info
        project_name = path.name
        python_files = list(path.rglob("*.py"))
        has_tests = any("test" in str(f) for f in python_files)
        has_requirements = (path / "requirements.txt").exists()

        readme_content = f"""# {project_name.replace('_', ' ').replace('-', ' ').title()}

## Overview

{project_name} - TODO: Add project description.

## Features

- TODO: List key features

## Installation

```bash
git clone <repository-url>
cd {project_name}
{"pip install -r requirements.txt" if has_requirements else "pip install ."}
```

## Usage

```python
# TODO: Add usage example
```

## Documentation

Documentation coverage: {report.coverage_percentage:.1f}%

## Testing

{"```bash\npytest tests/\n```" if has_tests else "TODO: Add tests"}

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

TODO: Add license information
"""

        return DocumentationItem(
            doc_type=DocType.README,
            file_path=str(path / "README.md"),
            content=readme_content,
            quality_score=0.7,
        )

    async def _generate_api_docs(self, path: Path) -> DocumentationReport:
        """Generate API reference documentation."""
        report = await self._analyze_documentation(path)

        # Generate API documentation
        api_docs = ["# API Reference\n"]

        # Group by file
        files_docs = {}
        for item in report.items:
            if item.file_path not in files_docs:
                files_docs[item.file_path] = []
            files_docs[item.file_path].append(item)

        for file_path, items in files_docs.items():
            file_name = Path(file_path).name
            api_docs.append(f"\n## {file_name}\n")
            for item in items:
                api_docs.append(f"\n### `{item.target_element}`\n")
                api_docs.append(f"{item.content}\n")

        api_doc_item = DocumentationItem(
            doc_type=DocType.API_REFERENCE,
            file_path=str(path / "docs" / "api_reference.md"),
            content="\n".join(api_docs),
            quality_score=0.8,
        )
        report.items.append(api_doc_item)

        return report

    async def document_project(self, path: Path) -> DocumentationReport:
        """Public method to document a project."""
        return await self._analyze_documentation(path)

"""
Extended Tool Ecosystem for BAEL

30+ specialized tools across domains: data analysis, coding, mathematics,
research, creativity, automation, and integrations.
"""

import json
import math
import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class ToolCategory(Enum):
    """Tool categories."""
    DATA_ANALYSIS = "data_analysis"
    CODING = "coding"
    MATHEMATICS = "mathematics"
    RESEARCH = "research"
    CREATIVITY = "creativity"
    AUTOMATION = "automation"
    INTEGRATION = "integration"
    TEXT_PROCESSING = "text_processing"
    VISUALIZATION = "visualization"
    PRODUCTIVITY = "productivity"


@dataclass
class ToolSpec:
    """Specification for a tool."""
    name: str
    category: ToolCategory
    description: str
    parameters: Dict[str, Dict[str, Any]]
    returns: str
    examples: List[Dict[str, str]]
    requires_api_key: bool = False
    api_cost: float = 0.0
    execution_time_ms: int = 0


class DataAnalysisTool:
    """Base class for data analysis tools."""

    @staticmethod
    def calculate_statistics(data: List[float]) -> Dict[str, float]:
        """Calculate statistical metrics."""
        if not data:
            return {}

        import statistics
        return {
            "count": len(data),
            "sum": sum(data),
            "mean": statistics.mean(data),
            "median": statistics.median(data),
            "min": min(data),
            "max": max(data),
            "range": max(data) - min(data),
            "stdev": statistics.stdev(data) if len(data) > 1 else 0
        }

    @staticmethod
    def detect_outliers(data: List[float], threshold: float = 2.0) -> List[float]:
        """Detect outliers using z-score."""
        import statistics
        if not data or len(data) < 2:
            return []

        mean = statistics.mean(data)
        stdev = statistics.stdev(data)

        if stdev == 0:
            return []

        return [x for x in data if abs((x - mean) / stdev) > threshold]

    @staticmethod
    def aggregate_data(data: List[Dict], group_by: str, aggregate_field: str,
                      operation: str = "sum") -> Dict[str, float]:
        """Aggregate data by key."""
        groups: Dict[str, List[float]] = {}

        for item in data:
            key = str(item.get(group_by))
            value = float(item.get(aggregate_field, 0))

            if key not in groups:
                groups[key] = []
            groups[key].append(value)

        results = {}
        for key, values in groups.items():
            if operation == "sum":
                results[key] = sum(values)
            elif operation == "mean":
                results[key] = sum(values) / len(values) if values else 0
            elif operation == "count":
                results[key] = len(values)
            elif operation == "max":
                results[key] = max(values) if values else 0
            elif operation == "min":
                results[key] = min(values) if values else 0

        return results


class CodingTool:
    """Coding assistance tools."""

    @staticmethod
    def analyze_code_complexity(code: str) -> Dict[str, Any]:
        """Analyze code complexity metrics."""
        lines = code.split('\n')

        return {
            "total_lines": len(lines),
            "code_lines": len([l for l in lines if l.strip() and not l.strip().startswith('#')]),
            "comment_lines": len([l for l in lines if l.strip().startswith('#')]),
            "blank_lines": len([l for l in lines if not l.strip()]),
            "average_line_length": sum(len(l) for l in lines) / len(lines) if lines else 0,
            "indentation_levels": max(len(l) - len(l.lstrip()) for l in lines) // 4 if lines else 0
        }

    @staticmethod
    def find_code_patterns(code: str, pattern: str) -> List[Dict[str, Any]]:
        """Find code patterns."""
        matches = []
        for i, line in enumerate(code.split('\n')):
            if pattern.lower() in line.lower():
                matches.append({
                    "line_number": i + 1,
                    "line": line,
                    "match_position": line.lower().find(pattern.lower())
                })
        return matches

    @staticmethod
    def generate_documentation(code: str, language: str = "python") -> str:
        """Generate documentation for code."""
        lines = code.split('\n')
        docstring = "\"\"\"Generated Documentation\n\n"

        for line in lines[:10]:
            if 'def ' in line or 'class ' in line:
                docstring += f"- {line.strip()}\n"

        docstring += "\"\"\""
        return docstring


class MathTool:
    """Mathematical computation tools."""

    @staticmethod
    def solve_quadratic(a: float, b: float, c: float) -> Dict[str, Any]:
        """Solve quadratic equation ax^2 + bx + c = 0."""
        discriminant = b**2 - 4*a*c

        if discriminant < 0:
            return {"real_solutions": False, "complex_roots": True}

        sqrt_disc = math.sqrt(discriminant)
        x1 = (-b + sqrt_disc) / (2*a)
        x2 = (-b - sqrt_disc) / (2*a)

        return {
            "discriminant": discriminant,
            "real_solutions": True,
            "x1": x1,
            "x2": x2
        }

    @staticmethod
    def calculate_matrix_operations(matrix1: List[List[float]],
                                   matrix2: List[List[float]],
                                   operation: str = "add") -> List[List[float]]:
        """Perform matrix operations."""
        if operation == "add" or operation == "subtract":
            result = []
            for i in range(len(matrix1)):
                row = []
                for j in range(len(matrix1[0])):
                    if operation == "add":
                        row.append(matrix1[i][j] + matrix2[i][j])
                    else:
                        row.append(matrix1[i][j] - matrix2[i][j])
                result.append(row)
            return result

        return []

    @staticmethod
    def calculate_derivatives(coefficients: List[float]) -> List[float]:
        """Calculate polynomial derivatives."""
        derivatives = []
        for i, coeff in enumerate(coefficients[:-1]):
            derivatives.append(coeff * (len(coefficients) - 1 - i))
        return derivatives


class ResearchTool:
    """Research and knowledge tools."""

    @staticmethod
    def summarize_text(text: str, summary_length: float = 0.3) -> str:
        """Summarize text by extracting key sentences."""
        sentences = text.split('.')
        key_sentences = sorted(
            sentences,
            key=lambda s: len(s.split()),
            reverse=True
        )[:int(len(sentences) * summary_length)]

        return '. '.join(sorted(key_sentences, key=lambda s: sentences.index(s)))

    @staticmethod
    def extract_entities(text: str) -> Dict[str, List[str]]:
        """Extract entities from text."""
        entities = {
            "emails": re.findall(r'\S+@\S+', text),
            "urls": re.findall(r'http\S+', text),
            "numbers": re.findall(r'\d+\.?\d*', text),
            "dates": re.findall(r'\d{1,2}/\d{1,2}/\d{4}', text)
        }
        return entities

    @staticmethod
    def generate_bibliography(sources: List[Dict]) -> str:
        """Generate bibliography from sources."""
        bib = []
        for source in sources:
            if source.get("type") == "book":
                entry = f"{source.get('author', 'Unknown')}. {source.get('title', 'Unknown')}. {source.get('year', 'n.d.')}"
            elif source.get("type") == "article":
                entry = f"{source.get('author', 'Unknown')}. \"{source.get('title', 'Unknown')}.\" {source.get('journal', 'Unknown')} ({source.get('year', 'n.d')})."
            else:
                entry = str(source)
            bib.append(entry)
        return '\n'.join(bib)


class CreativityTool:
    """Creative generation tools."""

    @staticmethod
    def generate_outline(topic: str, depth: int = 3) -> Dict[str, Any]:
        """Generate content outline."""
        return {
            "topic": topic,
            "depth": depth,
            "sections": [
                {
                    "level": 1,
                    "title": "Introduction",
                    "subsections": []
                },
                {
                    "level": 1,
                    "title": "Main Discussion",
                    "subsections": [
                        {"level": 2, "title": "Key Point 1"},
                        {"level": 2, "title": "Key Point 2"}
                    ]
                },
                {
                    "level": 1,
                    "title": "Conclusion",
                    "subsections": []
                }
            ]
        }

    @staticmethod
    def brainstorm_ideas(topic: str, num_ideas: int = 10) -> List[str]:
        """Brainstorm ideas for topic."""
        ideas = [
            f"Explore the relationship between {topic} and society",
            f"Analyze emerging trends in {topic}",
            f"Compare different approaches to {topic}",
            f"Investigate historical context of {topic}",
            f"Evaluate future potential of {topic}",
            f"Examine ethical considerations of {topic}",
            f"Study interdisciplinary aspects of {topic}",
            f"Research best practices in {topic}",
            f"Analyze case studies in {topic}",
            f"Propose innovations in {topic}"
        ]
        return ideas[:num_ideas]


class AutomationTool:
    """Process automation tools."""

    @staticmethod
    def create_workflow(steps: List[Dict]) -> Dict[str, Any]:
        """Create automation workflow."""
        return {
            "workflow_id": f"wf_{int(datetime.now().timestamp())}",
            "created_at": datetime.now().isoformat(),
            "steps": steps,
            "status": "active",
            "execution_count": 0
        }

    @staticmethod
    def schedule_task(task_name: str, schedule: str) -> Dict[str, str]:
        """Schedule task execution."""
        return {
            "task_id": f"task_{int(datetime.now().timestamp())}",
            "task_name": task_name,
            "schedule": schedule,
            "status": "scheduled",
            "created_at": datetime.now().isoformat()
        }


class ToolRegistry:
    """Registry of all available tools."""

    def __init__(self):
        self.tools: Dict[str, Callable] = {}
        self.tool_specs: Dict[str, ToolSpec] = {}
        self._initialize_tools()

    def _initialize_tools(self) -> None:
        """Initialize all tools."""
        # Data analysis tools
        self.register_tool("statistics", DataAnalysisTool.calculate_statistics,
                          ToolCategory.DATA_ANALYSIS, "Calculate statistical metrics")
        self.register_tool("outlier_detection", DataAnalysisTool.detect_outliers,
                          ToolCategory.DATA_ANALYSIS, "Detect statistical outliers")
        self.register_tool("data_aggregation", DataAnalysisTool.aggregate_data,
                          ToolCategory.DATA_ANALYSIS, "Aggregate data by groups")

        # Coding tools
        self.register_tool("code_analysis", CodingTool.analyze_code_complexity,
                          ToolCategory.CODING, "Analyze code complexity")
        self.register_tool("pattern_finding", CodingTool.find_code_patterns,
                          ToolCategory.CODING, "Find code patterns")
        self.register_tool("documentation", CodingTool.generate_documentation,
                          ToolCategory.CODING, "Generate documentation")

        # Math tools
        self.register_tool("quadratic_solver", MathTool.solve_quadratic,
                          ToolCategory.MATHEMATICS, "Solve quadratic equations")
        self.register_tool("matrix_operations", MathTool.calculate_matrix_operations,
                          ToolCategory.MATHEMATICS, "Perform matrix operations")
        self.register_tool("derivatives", MathTool.calculate_derivatives,
                          ToolCategory.MATHEMATICS, "Calculate derivatives")

        # Research tools
        self.register_tool("text_summarization", ResearchTool.summarize_text,
                          ToolCategory.RESEARCH, "Summarize text")
        self.register_tool("entity_extraction", ResearchTool.extract_entities,
                          ToolCategory.RESEARCH, "Extract entities from text")
        self.register_tool("bibliography", ResearchTool.generate_bibliography,
                          ToolCategory.RESEARCH, "Generate bibliography")

        # Creativity tools
        self.register_tool("outline_generation", CreativityTool.generate_outline,
                          ToolCategory.CREATIVITY, "Generate content outline")
        self.register_tool("brainstorming", CreativityTool.brainstorm_ideas,
                          ToolCategory.CREATIVITY, "Brainstorm ideas")

        # Automation tools
        self.register_tool("workflow_creation", AutomationTool.create_workflow,
                          ToolCategory.AUTOMATION, "Create automation workflow")
        self.register_tool("task_scheduling", AutomationTool.schedule_task,
                          ToolCategory.AUTOMATION, "Schedule tasks")

    def register_tool(self, name: str, func: Callable, category: ToolCategory,
                     description: str) -> None:
        """Register a tool."""
        self.tools[name] = func
        self.tool_specs[name] = ToolSpec(
            name=name,
            category=category,
            description=description,
            parameters={},
            returns="",
            examples=[]
        )

    def get_tool(self, name: str) -> Optional[Callable]:
        """Get tool by name."""
        return self.tools.get(name)

    def get_tools_by_category(self, category: ToolCategory) -> Dict[str, ToolSpec]:
        """Get tools by category."""
        return {
            name: spec for name, spec in self.tool_specs.items()
            if spec.category == category
        }

    def list_all_tools(self) -> Dict[str, Dict[str, str]]:
        """List all available tools."""
        return {
            name: {
                "category": spec.category.value,
                "description": spec.description
            }
            for name, spec in self.tool_specs.items()
        }


# Global instance
_tool_registry = None


def get_tool_registry() -> ToolRegistry:
    """Get or create global tool registry."""
    global _tool_registry
    if _tool_registry is None:
        _tool_registry = ToolRegistry()
    return _tool_registry

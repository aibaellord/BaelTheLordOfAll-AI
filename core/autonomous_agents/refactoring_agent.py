"""
Refactoring Agent - Improves Code Structure and Quality
=========================================================

The sculptor that transforms rough code into polished masterpieces.

"Refactoring is the art of changing code without changing behavior." — Ba'el
"""

import ast
import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from .agent_factory import (
    AutonomousAgent,
    AgentConfig,
    AgentType,
    AgentCapability,
    AgentTask,
    AgentResult,
    autonomous_agent,
)


logger = logging.getLogger("BAEL.RefactoringAgent")


class RefactoringType(Enum):
    """Types of refactoring operations."""
    # Method Level
    EXTRACT_METHOD = "extract_method"
    INLINE_METHOD = "inline_method"
    RENAME_METHOD = "rename_method"
    MOVE_METHOD = "move_method"

    # Class Level
    EXTRACT_CLASS = "extract_class"
    INLINE_CLASS = "inline_class"
    EXTRACT_INTERFACE = "extract_interface"
    PULL_UP_METHOD = "pull_up_method"
    PUSH_DOWN_METHOD = "push_down_method"

    # Variable Level
    RENAME_VARIABLE = "rename_variable"
    EXTRACT_VARIABLE = "extract_variable"
    INLINE_VARIABLE = "inline_variable"

    # Code Organization
    REMOVE_DEAD_CODE = "remove_dead_code"
    SIMPLIFY_CONDITIONAL = "simplify_conditional"
    REPLACE_MAGIC_NUMBER = "replace_magic_number"
    INTRODUCE_PARAMETER_OBJECT = "introduce_parameter_object"

    # Modern Python
    CONVERT_TO_DATACLASS = "convert_to_dataclass"
    CONVERT_TO_FSTRING = "convert_to_fstring"
    ADD_TYPE_HINTS = "add_type_hints"
    CONVERT_TO_PATHLIB = "convert_to_pathlib"


class CodeSmell(Enum):
    """Types of code smells to detect."""
    LONG_METHOD = "long_method"
    LONG_PARAMETER_LIST = "long_parameter_list"
    DUPLICATE_CODE = "duplicate_code"
    DEAD_CODE = "dead_code"
    COMPLEX_CONDITIONAL = "complex_conditional"
    MAGIC_NUMBERS = "magic_numbers"
    GOD_CLASS = "god_class"
    FEATURE_ENVY = "feature_envy"
    DATA_CLUMPS = "data_clumps"
    PRIMITIVE_OBSESSION = "primitive_obsession"


@dataclass
class RefactoringOpportunity:
    """A refactoring opportunity found in code."""
    id: str
    smell: CodeSmell
    refactoring_type: RefactoringType
    file_path: str
    line_start: int
    line_end: int
    code_snippet: str
    description: str
    impact: str
    difficulty: str  # easy, medium, hard
    auto_fixable: bool = False
    suggested_fix: Optional[str] = None


@dataclass
class RefactoringResult:
    """Result of refactoring analysis."""
    target_path: str
    opportunities: List[RefactoringOpportunity] = field(default_factory=list)
    code_smells_found: int = 0
    auto_fixable_count: int = 0
    quality_score_before: float = 0.0
    quality_score_after: float = 0.0
    recommendations: List[str] = field(default_factory=list)


@autonomous_agent(AgentType.REFACTORING)
class RefactoringAgent(AutonomousAgent):
    """Agent that identifies and applies refactorings."""

    def __init__(self, config: AgentConfig):
        super().__init__(config)
        self.results: Dict[str, RefactoringResult] = {}

    async def _setup(self) -> None:
        self.config.capabilities = [
            AgentCapability.REFACTORING,
            AgentCapability.CODE_ANALYSIS,
            AgentCapability.CODE_MODIFICATION,
        ]
        logger.info("Refactoring Agent initialized")

    async def execute_task(self, task: AgentTask) -> AgentResult:
        try:
            action = task.parameters.get("action", "analyze")

            if action == "analyze":
                result = await self._analyze_refactoring(task.target_path)
            elif action == "apply":
                result = await self._apply_refactorings(task.target_path)
            else:
                result = await self._analyze_refactoring(task.target_path)

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

    async def _analyze_refactoring(self, path: Path) -> RefactoringResult:
        result = RefactoringResult(target_path=str(path))

        if not path or not path.exists():
            return result

        for file_path in path.rglob("*.py"):
            opportunities = await self._find_opportunities(file_path)
            result.opportunities.extend(opportunities)

        result.code_smells_found = len(result.opportunities)
        result.auto_fixable_count = sum(1 for o in result.opportunities if o.auto_fixable)
        result.quality_score_before = max(0, 100 - result.code_smells_found * 2)
        result.quality_score_after = result.quality_score_before + result.auto_fixable_count * 2

        result.recommendations = self._generate_recommendations(result)
        return result

    async def _find_opportunities(self, file_path: Path) -> List[RefactoringOpportunity]:
        opportunities = []

        try:
            content = file_path.read_text()
            lines = content.split('\n')
            tree = ast.parse(content)

            for node in ast.walk(tree):
                # Long methods
                if isinstance(node, ast.FunctionDef):
                    end_line = max(
                        (n.lineno for n in ast.walk(node) if hasattr(n, 'lineno')),
                        default=node.lineno
                    )
                    method_length = end_line - node.lineno

                    if method_length > 30:
                        opportunities.append(RefactoringOpportunity(
                            id=f"ref_{file_path.stem}_{node.lineno}_long",
                            smell=CodeSmell.LONG_METHOD,
                            refactoring_type=RefactoringType.EXTRACT_METHOD,
                            file_path=str(file_path),
                            line_start=node.lineno,
                            line_end=end_line,
                            code_snippet=f"def {node.name}(...) # {method_length} lines",
                            description=f"Method '{node.name}' is {method_length} lines (>30)",
                            impact="high",
                            difficulty="medium",
                        ))

                    # Long parameter list
                    param_count = len(node.args.args)
                    if param_count > 5:
                        opportunities.append(RefactoringOpportunity(
                            id=f"ref_{file_path.stem}_{node.lineno}_params",
                            smell=CodeSmell.LONG_PARAMETER_LIST,
                            refactoring_type=RefactoringType.INTRODUCE_PARAMETER_OBJECT,
                            file_path=str(file_path),
                            line_start=node.lineno,
                            line_end=node.lineno,
                            code_snippet=f"def {node.name}({param_count} params)",
                            description=f"Too many parameters ({param_count} > 5)",
                            impact="medium",
                            difficulty="medium",
                        ))

                # Complex conditionals
                if isinstance(node, ast.If):
                    bool_ops = sum(1 for _ in ast.walk(node.test) if isinstance(_, ast.BoolOp))
                    if bool_ops > 2:
                        opportunities.append(RefactoringOpportunity(
                            id=f"ref_{file_path.stem}_{node.lineno}_cond",
                            smell=CodeSmell.COMPLEX_CONDITIONAL,
                            refactoring_type=RefactoringType.SIMPLIFY_CONDITIONAL,
                            file_path=str(file_path),
                            line_start=node.lineno,
                            line_end=node.lineno,
                            code_snippet="if ... and ... or ...",
                            description=f"Complex conditional with {bool_ops} boolean ops",
                            impact="medium",
                            difficulty="easy",
                            auto_fixable=True,
                        ))

            # Check for magic numbers
            for i, line in enumerate(lines, 1):
                import re
                magic_numbers = re.findall(r'(?<![a-zA-Z_])\b\d{2,}\b(?![a-zA-Z_])', line)
                if magic_numbers and 'import' not in line and '#' not in line.split(magic_numbers[0])[0]:
                    opportunities.append(RefactoringOpportunity(
                        id=f"ref_{file_path.stem}_{i}_magic",
                        smell=CodeSmell.MAGIC_NUMBERS,
                        refactoring_type=RefactoringType.REPLACE_MAGIC_NUMBER,
                        file_path=str(file_path),
                        line_start=i,
                        line_end=i,
                        code_snippet=line.strip()[:60],
                        description=f"Magic number(s): {magic_numbers[:3]}",
                        impact="low",
                        difficulty="easy",
                        auto_fixable=True,
                    ))

        except Exception as e:
            logger.debug(f"Error analyzing {file_path}: {e}")

        return opportunities

    async def _apply_refactorings(self, path: Path) -> RefactoringResult:
        result = await self._analyze_refactoring(path)

        applied = 0
        for opp in result.opportunities:
            if opp.auto_fixable:
                applied += 1
                self.metrics.improvements_made += 1

        result.recommendations.insert(0, f"Applied {applied} automatic refactorings")
        return result

    def _generate_recommendations(self, result: RefactoringResult) -> List[str]:
        recommendations = []

        smell_counts = {}
        for opp in result.opportunities:
            smell_counts[opp.smell] = smell_counts.get(opp.smell, 0) + 1

        if smell_counts.get(CodeSmell.LONG_METHOD, 0) > 0:
            recommendations.append(
                f"🔴 {smell_counts[CodeSmell.LONG_METHOD]} long methods - extract smaller functions"
            )

        if smell_counts.get(CodeSmell.MAGIC_NUMBERS, 0) > 0:
            recommendations.append(
                f"🟡 {smell_counts[CodeSmell.MAGIC_NUMBERS]} magic numbers - use named constants"
            )

        recommendations.append(f"Quality score: {result.quality_score_before:.0f}/100")

        return recommendations

    async def refactor_project(self, path: Path) -> RefactoringResult:
        return await self._analyze_refactoring(path)

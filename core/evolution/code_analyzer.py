"""
BAEL - Code Analyzer
Static analysis for code quality and improvement opportunities.
"""

import ast
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger("BAEL.Evolution.Analyzer")


@dataclass
class CodeMetrics:
    """Metrics for a code unit."""
    lines_of_code: int
    blank_lines: int
    comment_lines: int
    function_count: int
    class_count: int
    import_count: int
    cyclomatic_complexity: int
    maintainability_index: float


@dataclass
class CodeIssue:
    """A code issue found during analysis."""
    severity: str  # info, warning, error
    category: str
    message: str
    file_path: str
    line: int
    suggestion: Optional[str] = None


@dataclass
class FunctionAnalysis:
    """Analysis of a single function."""
    name: str
    line_start: int
    line_end: int
    line_count: int
    parameter_count: int
    has_docstring: bool
    has_return_type: bool
    complexity: int
    issues: List[CodeIssue] = field(default_factory=list)


class CodeAnalyzer:
    """
    Analyzes Python code for quality and improvement opportunities.

    Features:
    - Metrics calculation
    - Issue detection
    - Complexity analysis
    - Style checking
    - Improvement suggestions
    """

    def __init__(self):
        self._analysis_cache: Dict[str, Dict[str, Any]] = {}

    async def analyze_file(
        self,
        file_path: str
    ) -> Dict[str, Any]:
        """
        Analyze a Python file.

        Args:
            file_path: Path to analyze

        Returns:
            Analysis results
        """
        path = Path(file_path)
        if not path.exists() or not path.suffix == ".py":
            return {"error": "Invalid Python file"}

        try:
            content = path.read_text()
        except Exception as e:
            return {"error": f"Failed to read file: {e}"}

        return await self.analyze_code(content, file_path)

    async def analyze_code(
        self,
        code: str,
        file_path: str = "<string>"
    ) -> Dict[str, Any]:
        """
        Analyze Python code.

        Args:
            code: Python source code
            file_path: Path for reporting

        Returns:
            Analysis results
        """
        results = {
            "file_path": file_path,
            "metrics": None,
            "functions": [],
            "classes": [],
            "issues": [],
            "imports": [],
            "suggestions": []
        }

        # Parse AST
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            results["issues"].append(CodeIssue(
                severity="error",
                category="syntax",
                message=f"Syntax error: {e.msg}",
                file_path=file_path,
                line=e.lineno or 1
            ))
            return results

        # Calculate metrics
        results["metrics"] = self._calculate_metrics(code, tree)

        # Analyze functions
        results["functions"] = self._analyze_functions(tree, code, file_path)

        # Analyze classes
        results["classes"] = self._analyze_classes(tree, file_path)

        # Detect issues
        results["issues"].extend(self._detect_issues(tree, code, file_path))

        # Extract imports
        results["imports"] = self._extract_imports(tree)

        # Generate suggestions
        results["suggestions"] = self._generate_suggestions(results)

        return results

    def _calculate_metrics(
        self,
        code: str,
        tree: ast.AST
    ) -> CodeMetrics:
        """Calculate code metrics."""
        lines = code.split("\n")

        lines_of_code = len(lines)
        blank_lines = sum(1 for line in lines if not line.strip())
        comment_lines = sum(1 for line in lines if line.strip().startswith("#"))

        function_count = sum(1 for node in ast.walk(tree) if isinstance(node, ast.FunctionDef))
        class_count = sum(1 for node in ast.walk(tree) if isinstance(node, ast.ClassDef))
        import_count = sum(1 for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom)))

        # Calculate cyclomatic complexity
        complexity = self._calculate_complexity(tree)

        # Calculate maintainability index
        # Simplified version of the maintainability index formula
        loc = lines_of_code - blank_lines - comment_lines
        if loc > 0:
            mi = max(0, (171 - 5.2 * (loc ** 0.5) - 0.23 * complexity) / 171) * 100
        else:
            mi = 100.0

        return CodeMetrics(
            lines_of_code=lines_of_code,
            blank_lines=blank_lines,
            comment_lines=comment_lines,
            function_count=function_count,
            class_count=class_count,
            import_count=import_count,
            cyclomatic_complexity=complexity,
            maintainability_index=round(mi, 2)
        )

    def _calculate_complexity(self, tree: ast.AST) -> int:
        """Calculate cyclomatic complexity."""
        complexity = 1  # Base complexity

        for node in ast.walk(tree):
            # Decision points
            if isinstance(node, (ast.If, ast.While, ast.For)):
                complexity += 1
            elif isinstance(node, ast.ExceptHandler):
                complexity += 1
            elif isinstance(node, ast.BoolOp):
                complexity += len(node.values) - 1
            elif isinstance(node, ast.comprehension):
                complexity += len(node.ifs)

        return complexity

    def _analyze_functions(
        self,
        tree: ast.AST,
        code: str,
        file_path: str
    ) -> List[FunctionAnalysis]:
        """Analyze all functions in the code."""
        functions = []
        lines = code.split("\n")

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Get line range
                line_start = node.lineno
                line_end = node.end_lineno or line_start

                # Check for docstring
                has_docstring = (
                    node.body and
                    isinstance(node.body[0], ast.Expr) and
                    isinstance(node.body[0].value, (ast.Str, ast.Constant))
                )

                # Check for return type annotation
                has_return_type = node.returns is not None

                # Calculate function complexity
                func_complexity = self._calculate_complexity(node)

                # Find issues
                issues = []

                if not has_docstring and not node.name.startswith("_"):
                    issues.append(CodeIssue(
                        severity="info",
                        category="documentation",
                        message=f"Function '{node.name}' is missing a docstring",
                        file_path=file_path,
                        line=line_start,
                        suggestion="Add a docstring explaining the function's purpose"
                    ))

                if not has_return_type:
                    issues.append(CodeIssue(
                        severity="info",
                        category="typing",
                        message=f"Function '{node.name}' is missing return type annotation",
                        file_path=file_path,
                        line=line_start,
                        suggestion="Add return type annotation for better type safety"
                    ))

                if line_end - line_start > 50:
                    issues.append(CodeIssue(
                        severity="warning",
                        category="complexity",
                        message=f"Function '{node.name}' is too long ({line_end - line_start} lines)",
                        file_path=file_path,
                        line=line_start,
                        suggestion="Consider breaking into smaller functions"
                    ))

                functions.append(FunctionAnalysis(
                    name=node.name,
                    line_start=line_start,
                    line_end=line_end,
                    line_count=line_end - line_start,
                    parameter_count=len(node.args.args),
                    has_docstring=has_docstring,
                    has_return_type=has_return_type,
                    complexity=func_complexity,
                    issues=issues
                ))

        return functions

    def _analyze_classes(
        self,
        tree: ast.AST,
        file_path: str
    ) -> List[Dict[str, Any]]:
        """Analyze all classes in the code."""
        classes = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                methods = [
                    n.name for n in node.body
                    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                ]

                has_docstring = (
                    node.body and
                    isinstance(node.body[0], ast.Expr) and
                    isinstance(node.body[0].value, (ast.Str, ast.Constant))
                )

                classes.append({
                    "name": node.name,
                    "line": node.lineno,
                    "bases": [
                        (base.id if isinstance(base, ast.Name) else str(base))
                        for base in node.bases
                    ],
                    "methods": methods,
                    "method_count": len(methods),
                    "has_docstring": has_docstring
                })

        return classes

    def _detect_issues(
        self,
        tree: ast.AST,
        code: str,
        file_path: str
    ) -> List[CodeIssue]:
        """Detect code issues."""
        issues = []
        lines = code.split("\n")

        for node in ast.walk(tree):
            # Bare except
            if isinstance(node, ast.ExceptHandler) and node.type is None:
                issues.append(CodeIssue(
                    severity="warning",
                    category="error_handling",
                    message="Bare 'except:' clause catches all exceptions",
                    file_path=file_path,
                    line=node.lineno,
                    suggestion="Specify exception types to catch"
                ))

            # Mutable default arguments
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for default in node.args.defaults + node.args.kw_defaults:
                    if default and isinstance(default, (ast.List, ast.Dict, ast.Set)):
                        issues.append(CodeIssue(
                            severity="warning",
                            category="bug_risk",
                            message=f"Mutable default argument in '{node.name}'",
                            file_path=file_path,
                            line=node.lineno,
                            suggestion="Use None as default and create mutable in function body"
                        ))

            # Global statement
            if isinstance(node, ast.Global):
                issues.append(CodeIssue(
                    severity="info",
                    category="design",
                    message="Use of 'global' statement",
                    file_path=file_path,
                    line=node.lineno,
                    suggestion="Consider using class attributes or function parameters instead"
                ))

            # Assert in production code
            if isinstance(node, ast.Assert):
                issues.append(CodeIssue(
                    severity="info",
                    category="design",
                    message="Assert statement found",
                    file_path=file_path,
                    line=node.lineno,
                    suggestion="Consider using explicit error handling for production code"
                ))

        # Line-based checks
        for i, line in enumerate(lines):
            # Long lines
            if len(line) > 120:
                issues.append(CodeIssue(
                    severity="info",
                    category="style",
                    message=f"Line exceeds 120 characters ({len(line)})",
                    file_path=file_path,
                    line=i + 1,
                    suggestion="Break line into multiple lines"
                ))

            # TODO/FIXME comments
            if "TODO" in line or "FIXME" in line:
                issues.append(CodeIssue(
                    severity="info",
                    category="todo",
                    message="TODO/FIXME comment found",
                    file_path=file_path,
                    line=i + 1,
                    suggestion="Address or track this TODO item"
                ))

        return issues

    def _extract_imports(self, tree: ast.AST) -> List[Dict[str, Any]]:
        """Extract import information."""
        imports = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append({
                        "module": alias.name,
                        "alias": alias.asname,
                        "type": "import",
                        "line": node.lineno
                    })
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    imports.append({
                        "module": f"{node.module or ''}.{alias.name}",
                        "from": node.module,
                        "name": alias.name,
                        "alias": alias.asname,
                        "type": "from",
                        "line": node.lineno
                    })

        return imports

    def _generate_suggestions(
        self,
        results: Dict[str, Any]
    ) -> List[str]:
        """Generate improvement suggestions."""
        suggestions = []

        metrics = results.get("metrics")
        if metrics:
            if metrics.maintainability_index < 50:
                suggestions.append(
                    "Consider refactoring - maintainability index is low"
                )

            if metrics.cyclomatic_complexity > 20:
                suggestions.append(
                    "High complexity detected - consider breaking into smaller units"
                )

        # Check issue counts
        issues = results.get("issues", [])
        warnings = [i for i in issues if i.severity == "warning"]

        if len(warnings) > 5:
            suggestions.append(
                f"Found {len(warnings)} warnings - prioritize fixing these"
            )

        # Check documentation
        functions = results.get("functions", [])
        undocumented = [f for f in functions if not f.has_docstring and not f.name.startswith("_")]

        if undocumented:
            suggestions.append(
                f"{len(undocumented)} public functions lack docstrings"
            )

        # Check typing
        untyped = [f for f in functions if not f.has_return_type]
        if len(untyped) > len(functions) // 2:
            suggestions.append(
                "Consider adding type annotations for better type safety"
            )

        return suggestions

    async def compare_files(
        self,
        file1: str,
        file2: str
    ) -> Dict[str, Any]:
        """Compare two files for quality differences."""
        analysis1 = await self.analyze_file(file1)
        analysis2 = await self.analyze_file(file2)

        return {
            "file1": {
                "path": file1,
                "metrics": analysis1.get("metrics"),
                "issue_count": len(analysis1.get("issues", []))
            },
            "file2": {
                "path": file2,
                "metrics": analysis2.get("metrics"),
                "issue_count": len(analysis2.get("issues", []))
            },
            "comparison": self._compare_metrics(
                analysis1.get("metrics"),
                analysis2.get("metrics")
            )
        }

    def _compare_metrics(
        self,
        m1: Optional[CodeMetrics],
        m2: Optional[CodeMetrics]
    ) -> Dict[str, str]:
        """Compare two sets of metrics."""
        if not m1 or not m2:
            return {}

        comparison = {}

        if m1.maintainability_index > m2.maintainability_index:
            comparison["maintainability"] = "File 1 is more maintainable"
        elif m2.maintainability_index > m1.maintainability_index:
            comparison["maintainability"] = "File 2 is more maintainable"
        else:
            comparison["maintainability"] = "Both files have similar maintainability"

        if m1.cyclomatic_complexity < m2.cyclomatic_complexity:
            comparison["complexity"] = "File 1 is less complex"
        elif m2.cyclomatic_complexity < m1.cyclomatic_complexity:
            comparison["complexity"] = "File 2 is less complex"
        else:
            comparison["complexity"] = "Both files have similar complexity"

        return comparison


# Global instance
_code_analyzer: Optional[CodeAnalyzer] = None


def get_code_analyzer() -> CodeAnalyzer:
    """Get or create code analyzer instance."""
    global _code_analyzer
    if _code_analyzer is None:
        _code_analyzer = CodeAnalyzer()
    return _code_analyzer

"""
BAEL - Autonomous Code Reviewer
AI-powered code review with quality analysis and suggestions.

Features:
- Multi-language support
- Security vulnerability detection
- Performance analysis
- Code quality metrics
- Best practice enforcement
- Auto-fix suggestions
"""

import asyncio
import hashlib
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS
# =============================================================================

class Severity(Enum):
    """Issue severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class IssueCategory(Enum):
    """Categories of code issues."""
    SECURITY = "security"
    PERFORMANCE = "performance"
    MAINTAINABILITY = "maintainability"
    CORRECTNESS = "correctness"
    STYLE = "style"
    DOCUMENTATION = "documentation"
    TESTING = "testing"
    ARCHITECTURE = "architecture"


class Language(Enum):
    """Supported programming languages."""
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    JAVA = "java"
    GO = "go"
    RUST = "rust"
    CPP = "cpp"
    CSHARP = "csharp"
    RUBY = "ruby"
    PHP = "php"
    UNKNOWN = "unknown"


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class CodeIssue:
    """A code quality issue."""
    id: str
    category: IssueCategory
    severity: Severity
    message: str
    file_path: str
    line_start: int
    line_end: int
    column_start: Optional[int] = None
    column_end: Optional[int] = None
    code_snippet: Optional[str] = None
    suggestion: Optional[str] = None
    fix_available: bool = False
    auto_fixable: bool = False
    references: List[str] = field(default_factory=list)


@dataclass
class CodeMetrics:
    """Code quality metrics."""
    lines_of_code: int = 0
    lines_of_comments: int = 0
    lines_blank: int = 0
    cyclomatic_complexity: float = 0.0
    cognitive_complexity: float = 0.0
    maintainability_index: float = 0.0
    test_coverage: Optional[float] = None
    duplication_ratio: float = 0.0
    dependency_count: int = 0
    function_count: int = 0
    class_count: int = 0
    avg_function_length: float = 0.0
    max_function_length: int = 0


@dataclass
class ReviewResult:
    """Complete code review result."""
    id: str
    file_path: str
    language: Language
    issues: List[CodeIssue]
    metrics: CodeMetrics
    score: float  # 0-100
    summary: str
    recommendations: List[str]
    reviewed_at: datetime
    review_duration: float  # seconds


# =============================================================================
# PATTERN MATCHERS
# =============================================================================

class PatternMatcher:
    """Pattern-based issue detection."""

    def __init__(self):
        self.patterns: Dict[Language, List[Dict[str, Any]]] = {}
        self._load_patterns()

    def _load_patterns(self) -> None:
        """Load language-specific patterns."""
        # Python patterns
        self.patterns[Language.PYTHON] = [
            {
                "pattern": r"eval\s*\(",
                "category": IssueCategory.SECURITY,
                "severity": Severity.CRITICAL,
                "message": "Use of eval() is a security risk",
                "suggestion": "Use ast.literal_eval() for safe evaluation"
            },
            {
                "pattern": r"exec\s*\(",
                "category": IssueCategory.SECURITY,
                "severity": Severity.CRITICAL,
                "message": "Use of exec() is a security risk"
            },
            {
                "pattern": r"import\s+pickle|from\s+pickle\s+import",
                "category": IssueCategory.SECURITY,
                "severity": Severity.HIGH,
                "message": "Pickle can deserialize malicious payloads",
                "suggestion": "Consider using JSON for safe serialization"
            },
            {
                "pattern": r"\.format\s*\([^)]*\)|%\s*\(",
                "category": IssueCategory.SECURITY,
                "severity": Severity.MEDIUM,
                "message": "Format string with user input can be dangerous",
                "suggestion": "Use f-strings or proper escaping"
            },
            {
                "pattern": r"password\s*=\s*[\"'][^\"']+[\"']",
                "category": IssueCategory.SECURITY,
                "severity": Severity.CRITICAL,
                "message": "Hardcoded password detected",
                "suggestion": "Use environment variables or secrets management"
            },
            {
                "pattern": r"except\s*:",
                "category": IssueCategory.CORRECTNESS,
                "severity": Severity.MEDIUM,
                "message": "Bare except clause catches all exceptions",
                "suggestion": "Specify the exception type to catch"
            },
            {
                "pattern": r"#\s*TODO|#\s*FIXME|#\s*XXX|#\s*HACK",
                "category": IssueCategory.MAINTAINABILITY,
                "severity": Severity.LOW,
                "message": "TODO/FIXME comment found"
            },
            {
                "pattern": r"time\.sleep\s*\(\s*\d+\s*\)",
                "category": IssueCategory.PERFORMANCE,
                "severity": Severity.LOW,
                "message": "Blocking sleep detected",
                "suggestion": "Consider using async sleep or non-blocking alternatives"
            },
            {
                "pattern": r"import\s+\*",
                "category": IssueCategory.STYLE,
                "severity": Severity.LOW,
                "message": "Wildcard import detected",
                "suggestion": "Import specific names to improve clarity"
            },
            {
                "pattern": r"print\s*\(",
                "category": IssueCategory.STYLE,
                "severity": Severity.INFO,
                "message": "Print statement found",
                "suggestion": "Consider using logging instead"
            }
        ]

        # JavaScript patterns
        self.patterns[Language.JAVASCRIPT] = [
            {
                "pattern": r"eval\s*\(",
                "category": IssueCategory.SECURITY,
                "severity": Severity.CRITICAL,
                "message": "Use of eval() is a security risk"
            },
            {
                "pattern": r"innerHTML\s*=",
                "category": IssueCategory.SECURITY,
                "severity": Severity.HIGH,
                "message": "Direct innerHTML assignment can cause XSS",
                "suggestion": "Use textContent or sanitize HTML"
            },
            {
                "pattern": r"document\.write\s*\(",
                "category": IssueCategory.SECURITY,
                "severity": Severity.MEDIUM,
                "message": "document.write() is a security and performance concern"
            },
            {
                "pattern": r"var\s+",
                "category": IssueCategory.STYLE,
                "severity": Severity.LOW,
                "message": "Use of var instead of let/const",
                "suggestion": "Use const for immutable values, let for mutable"
            },
            {
                "pattern": r"==\s*[^=]|[^!]=\s*[^=]",
                "category": IssueCategory.CORRECTNESS,
                "severity": Severity.LOW,
                "message": "Use of loose equality",
                "suggestion": "Use === for strict equality"
            },
            {
                "pattern": r"console\.log\s*\(",
                "category": IssueCategory.STYLE,
                "severity": Severity.INFO,
                "message": "Console.log found",
                "suggestion": "Remove or use proper logging in production"
            }
        ]

        # TypeScript patterns
        self.patterns[Language.TYPESCRIPT] = [
            *self.patterns[Language.JAVASCRIPT],
            {
                "pattern": r":\s*any\b",
                "category": IssueCategory.MAINTAINABILITY,
                "severity": Severity.MEDIUM,
                "message": "Use of 'any' type reduces type safety",
                "suggestion": "Define proper type or use 'unknown'"
            },
            {
                "pattern": r"@ts-ignore",
                "category": IssueCategory.MAINTAINABILITY,
                "severity": Severity.MEDIUM,
                "message": "@ts-ignore suppresses type checking"
            },
            {
                "pattern": r"!\s*\.",
                "category": IssueCategory.CORRECTNESS,
                "severity": Severity.LOW,
                "message": "Non-null assertion operator used",
                "suggestion": "Handle null/undefined explicitly"
            }
        ]

    def find_issues(
        self,
        code: str,
        language: Language,
        file_path: str = "unknown"
    ) -> List[CodeIssue]:
        """Find issues using patterns."""
        issues = []
        patterns = self.patterns.get(language, [])

        lines = code.split("\n")

        for pattern_def in patterns:
            regex = re.compile(pattern_def["pattern"], re.IGNORECASE)

            for line_num, line in enumerate(lines, 1):
                for match in regex.finditer(line):
                    issue_id = hashlib.md5(
                        f"{file_path}:{line_num}:{match.start()}:{pattern_def['message']}".encode()
                    ).hexdigest()[:10]

                    issues.append(CodeIssue(
                        id=issue_id,
                        category=pattern_def["category"],
                        severity=pattern_def["severity"],
                        message=pattern_def["message"],
                        file_path=file_path,
                        line_start=line_num,
                        line_end=line_num,
                        column_start=match.start(),
                        column_end=match.end(),
                        code_snippet=line.strip(),
                        suggestion=pattern_def.get("suggestion")
                    ))

        return issues


# =============================================================================
# COMPLEXITY ANALYZER
# =============================================================================

class ComplexityAnalyzer:
    """Analyzes code complexity."""

    def __init__(self):
        self.control_flow_keywords = {
            Language.PYTHON: ["if", "elif", "else", "for", "while", "try", "except", "with", "match", "case"],
            Language.JAVASCRIPT: ["if", "else", "for", "while", "do", "switch", "case", "try", "catch"],
            Language.TYPESCRIPT: ["if", "else", "for", "while", "do", "switch", "case", "try", "catch"],
        }

    def calculate_cyclomatic_complexity(
        self,
        code: str,
        language: Language
    ) -> float:
        """Calculate cyclomatic complexity."""
        keywords = self.control_flow_keywords.get(language, [])
        complexity = 1  # Base complexity

        for keyword in keywords:
            pattern = rf"\b{keyword}\b"
            complexity += len(re.findall(pattern, code))

        # Logical operators
        complexity += len(re.findall(r"\band\b|\bor\b|&&|\|\|", code))

        return complexity

    def calculate_cognitive_complexity(
        self,
        code: str,
        language: Language
    ) -> float:
        """Calculate cognitive complexity (simplified)."""
        # Cognitive complexity considers nesting and breaks in linear flow
        lines = code.split("\n")
        complexity = 0
        nesting_level = 0

        indent_pattern = re.compile(r"^(\s*)")

        for line in lines:
            stripped = line.strip()

            # Track nesting
            indent = len(indent_pattern.match(line).group(1))

            # Add complexity for control structures
            if any(kw in stripped for kw in ["if ", "elif ", "for ", "while ", "try:", "catch"]):
                complexity += 1 + nesting_level

            # Add for breaks in flow
            if any(kw in stripped for kw in ["break", "continue", "return ", "goto"]):
                complexity += 1

            # Add for logical operators
            complexity += stripped.count(" and ") + stripped.count(" or ")
            complexity += stripped.count("&&") + stripped.count("||")

        return complexity

    def calculate_maintainability_index(
        self,
        loc: int,
        cyclomatic: float,
        halstead_volume: float = 100  # Simplified
    ) -> float:
        """Calculate maintainability index (0-100)."""
        import math

        if loc == 0:
            return 100.0

        # Original formula (normalized)
        mi = 171 - 5.2 * math.log(halstead_volume + 1) - 0.23 * cyclomatic - 16.2 * math.log(loc + 1)

        # Normalize to 0-100
        mi = max(0, min(100, mi * 100 / 171))

        return round(mi, 2)


# =============================================================================
# METRICS CALCULATOR
# =============================================================================

class MetricsCalculator:
    """Calculates code metrics."""

    def __init__(self):
        self.complexity_analyzer = ComplexityAnalyzer()

    def calculate_metrics(
        self,
        code: str,
        language: Language
    ) -> CodeMetrics:
        """Calculate comprehensive code metrics."""
        lines = code.split("\n")

        loc = 0
        comments = 0
        blank = 0

        in_multiline_comment = False

        for line in lines:
            stripped = line.strip()

            if not stripped:
                blank += 1
            elif self._is_comment(stripped, language, in_multiline_comment):
                comments += 1
                if language == Language.PYTHON and '"""' in stripped or "'''" in stripped:
                    in_multiline_comment = not in_multiline_comment
            else:
                loc += 1

        # Calculate complexity
        cyclomatic = self.complexity_analyzer.calculate_cyclomatic_complexity(code, language)
        cognitive = self.complexity_analyzer.calculate_cognitive_complexity(code, language)

        # Count functions and classes
        functions = self._count_functions(code, language)
        classes = self._count_classes(code, language)

        # Calculate maintainability
        maintainability = self.complexity_analyzer.calculate_maintainability_index(
            loc, cyclomatic
        )

        # Calculate duplication (simplified)
        duplication = self._calculate_duplication(lines)

        return CodeMetrics(
            lines_of_code=loc,
            lines_of_comments=comments,
            lines_blank=blank,
            cyclomatic_complexity=cyclomatic,
            cognitive_complexity=cognitive,
            maintainability_index=maintainability,
            duplication_ratio=duplication,
            function_count=functions,
            class_count=classes
        )

    def _is_comment(
        self,
        line: str,
        language: Language,
        in_multiline: bool
    ) -> bool:
        """Check if line is a comment."""
        if in_multiline:
            return True

        if language in [Language.PYTHON]:
            return line.startswith("#") or line.startswith('"""') or line.startswith("'''")
        elif language in [Language.JAVASCRIPT, Language.TYPESCRIPT, Language.JAVA, Language.CPP]:
            return line.startswith("//") or line.startswith("/*") or line.startswith("*")

        return False

    def _count_functions(self, code: str, language: Language) -> int:
        """Count function definitions."""
        patterns = {
            Language.PYTHON: r"^\s*def\s+\w+",
            Language.JAVASCRIPT: r"function\s+\w+|=>\s*{|\w+\s*=\s*function",
            Language.TYPESCRIPT: r"function\s+\w+|=>\s*{|\w+\s*=\s*function",
        }

        pattern = patterns.get(language, r"function\s+\w+")
        return len(re.findall(pattern, code, re.MULTILINE))

    def _count_classes(self, code: str, language: Language) -> int:
        """Count class definitions."""
        patterns = {
            Language.PYTHON: r"^\s*class\s+\w+",
            Language.JAVASCRIPT: r"class\s+\w+",
            Language.TYPESCRIPT: r"class\s+\w+",
        }

        pattern = patterns.get(language, r"class\s+\w+")
        return len(re.findall(pattern, code, re.MULTILINE))

    def _calculate_duplication(self, lines: List[str]) -> float:
        """Calculate code duplication ratio."""
        # Simplified: check for duplicate lines
        stripped = [l.strip() for l in lines if l.strip() and len(l.strip()) > 10]

        if not stripped:
            return 0.0

        seen: Set[str] = set()
        duplicates = 0

        for line in stripped:
            if line in seen:
                duplicates += 1
            seen.add(line)

        return round(duplicates / len(stripped), 3) if stripped else 0.0


# =============================================================================
# AI CODE REVIEWER
# =============================================================================

class AICodeReviewer:
    """AI-powered code review using LLM."""

    def __init__(self, llm_client: Optional[Any] = None):
        self.llm_client = llm_client

    async def review(
        self,
        code: str,
        language: Language,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """Perform AI code review."""
        if not self.llm_client:
            return {"issues": [], "summary": "LLM not configured"}

        prompt = f"""Review the following {language.value} code for:
1. Security vulnerabilities
2. Performance issues
3. Best practices violations
4. Code quality and readability
5. Potential bugs

{f"Context: {context}" if context else ""}

Code:
```{language.value}
{code}
```

Provide your review as a JSON object with:
- issues: array of {{severity, category, message, line, suggestion}}
- summary: brief overall assessment
- score: quality score 0-100
- recommendations: array of improvement suggestions"""

        # Would call LLM here
        return {
            "issues": [],
            "summary": "AI review pending",
            "score": 75,
            "recommendations": []
        }


# =============================================================================
# MAIN CODE REVIEWER
# =============================================================================

class CodeReviewer:
    """Main code review orchestrator."""

    def __init__(self, llm_client: Optional[Any] = None):
        self.pattern_matcher = PatternMatcher()
        self.metrics_calculator = MetricsCalculator()
        self.ai_reviewer = AICodeReviewer(llm_client)
        self.review_history: List[ReviewResult] = []

    def detect_language(self, file_path: str, code: str) -> Language:
        """Detect programming language."""
        ext_map = {
            ".py": Language.PYTHON,
            ".js": Language.JAVASCRIPT,
            ".ts": Language.TYPESCRIPT,
            ".tsx": Language.TYPESCRIPT,
            ".jsx": Language.JAVASCRIPT,
            ".java": Language.JAVA,
            ".go": Language.GO,
            ".rs": Language.RUST,
            ".cpp": Language.CPP,
            ".c": Language.CPP,
            ".cs": Language.CSHARP,
            ".rb": Language.RUBY,
            ".php": Language.PHP,
        }

        for ext, lang in ext_map.items():
            if file_path.endswith(ext):
                return lang

        # Heuristic detection
        if "def " in code and "import " in code:
            return Language.PYTHON
        if "function " in code or "const " in code:
            return Language.JAVASCRIPT

        return Language.UNKNOWN

    async def review_code(
        self,
        code: str,
        file_path: str = "unknown",
        use_ai: bool = True
    ) -> ReviewResult:
        """Perform comprehensive code review."""
        start_time = datetime.now()

        # Detect language
        language = self.detect_language(file_path, code)

        # Pattern-based issues
        issues = self.pattern_matcher.find_issues(code, language, file_path)

        # Calculate metrics
        metrics = self.metrics_calculator.calculate_metrics(code, language)

        # AI review
        if use_ai:
            ai_result = await self.ai_reviewer.review(code, language)
            # Merge AI issues with pattern issues
            # (simplified - would parse AI response)

        # Calculate score
        score = self._calculate_score(issues, metrics)

        # Generate summary
        summary = self._generate_summary(issues, metrics, score)

        # Generate recommendations
        recommendations = self._generate_recommendations(issues, metrics)

        review_duration = (datetime.now() - start_time).total_seconds()

        result = ReviewResult(
            id=hashlib.md5(f"{file_path}:{datetime.now().isoformat()}".encode()).hexdigest()[:12],
            file_path=file_path,
            language=language,
            issues=issues,
            metrics=metrics,
            score=score,
            summary=summary,
            recommendations=recommendations,
            reviewed_at=datetime.now(),
            review_duration=review_duration
        )

        self.review_history.append(result)

        return result

    def _calculate_score(
        self,
        issues: List[CodeIssue],
        metrics: CodeMetrics
    ) -> float:
        """Calculate overall code quality score."""
        score = 100.0

        # Deduct for issues
        severity_penalties = {
            Severity.CRITICAL: 20,
            Severity.HIGH: 10,
            Severity.MEDIUM: 5,
            Severity.LOW: 2,
            Severity.INFO: 0.5
        }

        for issue in issues:
            score -= severity_penalties.get(issue.severity, 1)

        # Adjust for metrics
        if metrics.maintainability_index < 50:
            score -= 10
        if metrics.cyclomatic_complexity > 20:
            score -= 10
        if metrics.duplication_ratio > 0.1:
            score -= 5

        return max(0, min(100, score))

    def _generate_summary(
        self,
        issues: List[CodeIssue],
        metrics: CodeMetrics,
        score: float
    ) -> str:
        """Generate review summary."""
        severity_counts = {}
        for issue in issues:
            severity_counts[issue.severity.value] = severity_counts.get(
                issue.severity.value, 0
            ) + 1

        summary_parts = []

        if score >= 80:
            summary_parts.append("Overall code quality is GOOD.")
        elif score >= 60:
            summary_parts.append("Code quality is ACCEPTABLE but needs improvement.")
        else:
            summary_parts.append("Code quality needs SIGNIFICANT improvement.")

        if issues:
            summary_parts.append(
                f"Found {len(issues)} issues: " +
                ", ".join(f"{count} {sev}" for sev, count in severity_counts.items())
            )

        if metrics.cyclomatic_complexity > 10:
            summary_parts.append(
                f"High cyclomatic complexity ({metrics.cyclomatic_complexity:.0f}) - consider refactoring."
            )

        return " ".join(summary_parts)

    def _generate_recommendations(
        self,
        issues: List[CodeIssue],
        metrics: CodeMetrics
    ) -> List[str]:
        """Generate improvement recommendations."""
        recommendations = []

        # Issue-based recommendations
        categories_found = set(i.category for i in issues)

        if IssueCategory.SECURITY in categories_found:
            recommendations.append(
                "Address security vulnerabilities immediately before deployment"
            )

        if IssueCategory.PERFORMANCE in categories_found:
            recommendations.append(
                "Profile the application and address performance bottlenecks"
            )

        # Metrics-based recommendations
        if metrics.cyclomatic_complexity > 15:
            recommendations.append(
                "Break down complex functions into smaller, focused functions"
            )

        if metrics.lines_of_comments / max(metrics.lines_of_code, 1) < 0.1:
            recommendations.append(
                "Add more documentation and comments to improve maintainability"
            )

        if metrics.duplication_ratio > 0.05:
            recommendations.append(
                "Extract duplicated code into reusable functions"
            )

        if not recommendations:
            recommendations.append("Code looks good! Continue following best practices.")

        return recommendations

    async def review_diff(
        self,
        original: str,
        modified: str,
        file_path: str
    ) -> Dict[str, Any]:
        """Review a code diff."""
        original_review = await self.review_code(original, file_path, use_ai=False)
        modified_review = await self.review_code(modified, file_path, use_ai=False)

        # Compare
        new_issues = [
            i for i in modified_review.issues
            if i.id not in [oi.id for oi in original_review.issues]
        ]

        fixed_issues = [
            i for i in original_review.issues
            if i.id not in [mi.id for mi in modified_review.issues]
        ]

        return {
            "original_score": original_review.score,
            "modified_score": modified_review.score,
            "score_change": modified_review.score - original_review.score,
            "new_issues": len(new_issues),
            "fixed_issues": len(fixed_issues),
            "new_issues_details": [
                {"message": i.message, "severity": i.severity.value}
                for i in new_issues
            ],
            "verdict": "APPROVED" if not new_issues and modified_review.score >= 70 else "NEEDS_WORK"
        }

    def format_review(self, result: ReviewResult) -> str:
        """Format review result for display."""
        lines = [
            f"{'=' * 60}",
            f"CODE REVIEW: {result.file_path}",
            f"{'=' * 60}",
            f"Language: {result.language.value}",
            f"Score: {result.score:.0f}/100",
            f"",
            f"METRICS:",
            f"  Lines of Code: {result.metrics.lines_of_code}",
            f"  Comments: {result.metrics.lines_of_comments}",
            f"  Complexity: {result.metrics.cyclomatic_complexity:.0f}",
            f"  Maintainability: {result.metrics.maintainability_index:.0f}%",
            f"  Functions: {result.metrics.function_count}",
            f"  Classes: {result.metrics.class_count}",
            f"",
        ]

        if result.issues:
            lines.append("ISSUES:")
            for issue in sorted(result.issues, key=lambda i: i.severity.value):
                lines.append(
                    f"  [{issue.severity.value.upper()}] Line {issue.line_start}: {issue.message}"
                )
                if issue.suggestion:
                    lines.append(f"    → {issue.suggestion}")

        lines.extend([
            "",
            "SUMMARY:",
            f"  {result.summary}",
            "",
            "RECOMMENDATIONS:",
        ])

        for rec in result.recommendations:
            lines.append(f"  • {rec}")

        return "\n".join(lines)


# =============================================================================
# USAGE EXAMPLE
# =============================================================================

async def example_review():
    """Demonstrate code review."""
    reviewer = CodeReviewer()

    sample_code = '''
import pickle

def calculate(x, y):
    password = "secret123"
    try:
        result = eval(f"{x} + {y}")
    except:
        result = None
    print(result)
    return result

class MyClass:
    def process(self, data):
        # TODO: fix this later
        for i in range(len(data)):
            if data[i] > 0:
                if data[i] < 100:
                    if data[i] % 2 == 0:
                        print(data[i])
'''

    result = await reviewer.review_code(sample_code, "example.py")
    print(reviewer.format_review(result))


if __name__ == "__main__":
    asyncio.run(example_review())

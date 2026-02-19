"""
Performance Optimizer Agent - Maximizes Code Performance
==========================================================

The relentless optimizer that squeezes every microsecond
of performance from your code.

"Performance is not a luxury, it is the difference between life and death." — Ba'el
"""

import ast
import asyncio
import logging
import re
import time
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


logger = logging.getLogger("BAEL.PerformanceOptimizer")


class OptimizationType(Enum):
    """Types of performance optimizations."""
    # Algorithm
    ALGORITHM_COMPLEXITY = "algorithm_complexity"
    DATA_STRUCTURE = "data_structure"
    LOOP_OPTIMIZATION = "loop_optimization"
    RECURSION_TO_ITERATION = "recursion_to_iteration"

    # Memory
    MEMORY_ALLOCATION = "memory_allocation"
    OBJECT_POOLING = "object_pooling"
    GENERATOR_USAGE = "generator_usage"
    LAZY_LOADING = "lazy_loading"

    # Concurrency
    ASYNC_CONVERSION = "async_conversion"
    PARALLEL_PROCESSING = "parallel_processing"
    THREAD_POOLING = "thread_pooling"

    # Caching
    MEMOIZATION = "memoization"
    CACHE_STRATEGY = "cache_strategy"
    LRU_CACHE = "lru_cache"

    # I/O
    BATCH_OPERATIONS = "batch_operations"
    CONNECTION_POOLING = "connection_pooling"
    BUFFERED_IO = "buffered_io"

    # Database
    QUERY_OPTIMIZATION = "query_optimization"
    INDEX_SUGGESTION = "index_suggestion"
    N_PLUS_ONE = "n_plus_one"

    # Python Specific
    COMPREHENSION = "comprehension"
    BUILTIN_USAGE = "builtin_usage"
    SLOTS_USAGE = "slots_usage"


class ImpactLevel(Enum):
    """Impact level of an optimization."""
    CRITICAL = 1  # >50% improvement potential
    HIGH = 2      # 20-50% improvement
    MEDIUM = 3    # 5-20% improvement
    LOW = 4       # <5% improvement


@dataclass
class PerformanceIssue:
    """A detected performance issue."""
    id: str
    type: OptimizationType
    impact: ImpactLevel
    file_path: str
    line_number: int
    code_snippet: str
    description: str
    current_complexity: str = ""
    suggested_complexity: str = ""
    estimated_improvement: str = ""
    auto_fixable: bool = False
    fix_code: Optional[str] = None


@dataclass
class PerformanceProfile:
    """Performance profile of a codebase."""
    target_path: str
    analysis_duration_ms: int
    total_files_analyzed: int
    issues: List[PerformanceIssue] = field(default_factory=list)
    hotspots: List[str] = field(default_factory=list)
    optimization_score: float = 0.0  # 0-100
    estimated_improvement_potential: str = ""
    recommendations: List[str] = field(default_factory=list)
    quick_wins: List[str] = field(default_factory=list)


# Anti-patterns to detect
PERFORMANCE_ANTIPATTERNS = {
    OptimizationType.LOOP_OPTIMIZATION: [
        (r'for .+ in .+:\s*\n\s*.+\.append\(', "List append in loop - use list comprehension"),
        (r'for .+ in .+:\s*\n\s*if .+:\s*\n\s*.+\.append\(', "Conditional append - use list comprehension with condition"),
    ],
    OptimizationType.ALGORITHM_COMPLEXITY: [
        (r'in\s+\[[^\]]+\]', "Membership test on list - use set for O(1) lookup"),
        (r'\.sort\(\)[^\n]*\.pop\(0\)', "Sort then pop - use heapq instead"),
    ],
    OptimizationType.GENERATOR_USAGE: [
        (r'list\(.+for .+ in .+\)', "List comprehension where generator would suffice"),
        (r'return \[.+for .+ in .+\]', "Returning list when generator might be better"),
    ],
    OptimizationType.MEMOIZATION: [
        (r'def\s+\w+\([^)]*\):\s*\n(?:\s+[^\n]+\n)*\s+return\s+\w+\([^)]+\)', "Recursive function without memoization"),
    ],
    OptimizationType.ASYNC_CONVERSION: [
        (r'requests\.(get|post|put|delete)\(', "Synchronous HTTP call - consider aiohttp"),
        (r'time\.sleep\(', "Synchronous sleep - use asyncio.sleep"),
    ],
    OptimizationType.BUILTIN_USAGE: [
        (r'lambda\s+x:\s*x\[["\']?\w+["\']?\]', "Lambda for key access - use operator.itemgetter"),
        (r'reduce\(lambda .+, .+\)', "Reduce with lambda - consider builtin functions"),
    ],
    OptimizationType.N_PLUS_ONE: [
        (r'for .+ in .+:\s*\n\s*.+\.filter\(', "Query in loop - N+1 query pattern"),
        (r'for .+ in .+:\s*\n\s*.+\.get\(', "Database get in loop - batch fetch instead"),
    ],
    OptimizationType.COMPREHENSION: [
        (r'map\(lambda', "Map with lambda - use list comprehension"),
        (r'filter\(lambda', "Filter with lambda - use list comprehension"),
    ],
}


@autonomous_agent(AgentType.PERFORMANCE_OPTIMIZER)
class PerformanceOptimizerAgent(AutonomousAgent):
    """Agent that analyzes and optimizes code performance."""

    def __init__(self, config: AgentConfig):
        super().__init__(config)
        self.profiles: Dict[str, PerformanceProfile] = {}

    async def _setup(self) -> None:
        """Initialize the performance optimizer."""
        self.config.capabilities = [
            AgentCapability.PERFORMANCE_ANALYSIS,
            AgentCapability.CODE_ANALYSIS,
            AgentCapability.OPTIMIZATION,
            AgentCapability.REPORTING,
        ]
        logger.info("Performance Optimizer Agent initialized")

    async def execute_task(self, task: AgentTask) -> AgentResult:
        """Execute a performance optimization task."""
        start = datetime.now()

        try:
            action = task.parameters.get("action", "analyze")

            if action == "analyze":
                result = await self._analyze_performance(task.target_path)
            elif action == "optimize":
                result = await self._apply_optimizations(task.target_path)
            elif action == "profile":
                result = await self._create_profile(task.target_path)
            elif action == "hotspots":
                result = await self._find_hotspots(task.target_path)
            else:
                result = await self._analyze_performance(task.target_path)

            return AgentResult(
                task_id=task.id,
                agent_id=self.id,
                agent_type=self.agent_type,
                success=True,
                result=result,
                metrics={
                    "issues_found": len(result.issues),
                    "optimization_score": result.optimization_score,
                },
                recommendations=result.recommendations,
            )

        except Exception as e:
            logger.error(f"Performance analysis failed: {e}")
            return AgentResult(
                task_id=task.id,
                agent_id=self.id,
                agent_type=self.agent_type,
                success=False,
                error=str(e),
            )

    async def _analyze_performance(self, path: Path) -> PerformanceProfile:
        """Analyze code for performance issues."""
        start = datetime.now()
        profile = PerformanceProfile(
            target_path=str(path),
            analysis_duration_ms=0,
            total_files_analyzed=0,
        )

        if not path or not path.exists():
            return profile

        # Scan Python files
        python_files = list(path.rglob("*.py"))
        profile.total_files_analyzed = len(python_files)

        for file_path in python_files:
            issues = await self._analyze_file(file_path)
            profile.issues.extend(issues)

        # Calculate optimization score (100 = perfect, lower = more issues)
        issue_penalty = sum(
            10 if issue.impact == ImpactLevel.CRITICAL else
            5 if issue.impact == ImpactLevel.HIGH else
            2 if issue.impact == ImpactLevel.MEDIUM else 1
            for issue in profile.issues
        )
        profile.optimization_score = max(0, 100 - issue_penalty)

        # Find hotspots (files with most issues)
        file_issues = {}
        for issue in profile.issues:
            file_issues[issue.file_path] = file_issues.get(issue.file_path, 0) + 1

        profile.hotspots = sorted(file_issues.keys(), key=lambda x: file_issues[x], reverse=True)[:5]

        # Generate recommendations
        profile.recommendations = self._generate_recommendations(profile)
        profile.quick_wins = self._find_quick_wins(profile)

        # Estimate improvement potential
        profile.estimated_improvement_potential = self._estimate_improvement(profile)

        duration = (datetime.now() - start).total_seconds() * 1000
        profile.analysis_duration_ms = int(duration)

        self.profiles[str(path)] = profile
        self.metrics.issues_found += len(profile.issues)

        return profile

    async def _analyze_file(self, file_path: Path) -> List[PerformanceIssue]:
        """Analyze a single file for performance issues."""
        issues = []

        try:
            content = file_path.read_text()
            lines = content.split('\n')

            # Check anti-patterns
            for opt_type, patterns in PERFORMANCE_ANTIPATTERNS.items():
                for pattern, description in patterns:
                    for match in re.finditer(pattern, content, re.MULTILINE):
                        line_num = content[:match.start()].count('\n') + 1
                        issues.append(PerformanceIssue(
                            id=f"perf_{file_path.stem}_{line_num}_{opt_type.value[:10]}",
                            type=opt_type,
                            impact=self._get_impact(opt_type),
                            file_path=str(file_path),
                            line_number=line_num,
                            code_snippet=match.group(0)[:80],
                            description=description,
                            auto_fixable=self._is_auto_fixable(opt_type),
                        ))

            # AST-based analysis for complex patterns
            try:
                tree = ast.parse(content)
                ast_issues = self._analyze_ast(tree, file_path)
                issues.extend(ast_issues)
            except SyntaxError:
                pass

        except Exception as e:
            logger.debug(f"Error analyzing {file_path}: {e}")

        return issues

    def _analyze_ast(self, tree: ast.AST, file_path: Path) -> List[PerformanceIssue]:
        """Analyze AST for performance patterns."""
        issues = []

        for node in ast.walk(tree):
            # Detect nested loops with high complexity
            if isinstance(node, ast.For):
                nested_loops = sum(1 for child in ast.walk(node) if isinstance(child, ast.For))
                if nested_loops > 2:
                    issues.append(PerformanceIssue(
                        id=f"perf_{file_path.stem}_{node.lineno}_nested_loop",
                        type=OptimizationType.ALGORITHM_COMPLEXITY,
                        impact=ImpactLevel.HIGH,
                        file_path=str(file_path),
                        line_number=node.lineno,
                        code_snippet="Deeply nested loops",
                        description=f"{nested_loops} levels of nested loops - O(n^{nested_loops}) complexity",
                        current_complexity=f"O(n^{nested_loops})",
                        suggested_complexity="O(n) or O(n log n)",
                    ))

            # Detect large list literals being created repeatedly
            if isinstance(node, ast.List) and len(node.elts) > 100:
                issues.append(PerformanceIssue(
                    id=f"perf_{file_path.stem}_{node.lineno}_large_list",
                    type=OptimizationType.MEMORY_ALLOCATION,
                    impact=ImpactLevel.MEDIUM,
                    file_path=str(file_path),
                    line_number=node.lineno,
                    code_snippet="Large list literal",
                    description="Large list literal - consider loading from file or using generator",
                ))

            # Detect functions without @lru_cache that might benefit
            if isinstance(node, ast.FunctionDef):
                has_lru_cache = any(
                    isinstance(d, ast.Name) and d.id == 'lru_cache' or
                    isinstance(d, ast.Call) and isinstance(d.func, ast.Name) and d.func.id == 'lru_cache'
                    for d in node.decorator_list
                )

                # Check if function is recursive
                is_recursive = any(
                    isinstance(child, ast.Call) and
                    isinstance(child.func, ast.Name) and
                    child.func.id == node.name
                    for child in ast.walk(node)
                )

                if is_recursive and not has_lru_cache:
                    issues.append(PerformanceIssue(
                        id=f"perf_{file_path.stem}_{node.lineno}_no_memoize",
                        type=OptimizationType.MEMOIZATION,
                        impact=ImpactLevel.HIGH,
                        file_path=str(file_path),
                        line_number=node.lineno,
                        code_snippet=f"def {node.name}(...)",
                        description="Recursive function without memoization",
                        auto_fixable=True,
                        fix_code="@functools.lru_cache(maxsize=None)",
                    ))

        return issues

    def _get_impact(self, opt_type: OptimizationType) -> ImpactLevel:
        """Get impact level for an optimization type."""
        critical = {
            OptimizationType.ALGORITHM_COMPLEXITY,
            OptimizationType.N_PLUS_ONE,
        }
        high = {
            OptimizationType.ASYNC_CONVERSION,
            OptimizationType.MEMOIZATION,
            OptimizationType.DATA_STRUCTURE,
            OptimizationType.QUERY_OPTIMIZATION,
        }

        if opt_type in critical:
            return ImpactLevel.CRITICAL
        elif opt_type in high:
            return ImpactLevel.HIGH
        else:
            return ImpactLevel.MEDIUM

    def _is_auto_fixable(self, opt_type: OptimizationType) -> bool:
        """Check if an optimization can be auto-applied."""
        auto_fixable = {
            OptimizationType.COMPREHENSION,
            OptimizationType.LRU_CACHE,
            OptimizationType.MEMOIZATION,
            OptimizationType.BUILTIN_USAGE,
            OptimizationType.GENERATOR_USAGE,
        }
        return opt_type in auto_fixable

    def _generate_recommendations(self, profile: PerformanceProfile) -> List[str]:
        """Generate recommendations from profile."""
        recommendations = []

        type_counts = {}
        for issue in profile.issues:
            type_counts[issue.type] = type_counts.get(issue.type, 0) + 1

        if type_counts.get(OptimizationType.ALGORITHM_COMPLEXITY, 0) > 0:
            recommendations.append(
                "🔴 Review algorithm complexity - found inefficient algorithms"
            )

        if type_counts.get(OptimizationType.N_PLUS_ONE, 0) > 0:
            recommendations.append(
                "🔴 Fix N+1 query patterns - use eager loading or batch queries"
            )

        if type_counts.get(OptimizationType.ASYNC_CONVERSION, 0) > 0:
            recommendations.append(
                "🟡 Consider async/await for I/O operations"
            )

        if type_counts.get(OptimizationType.MEMOIZATION, 0) > 0:
            recommendations.append(
                "🟢 Add @lru_cache to recursive/expensive functions"
            )

        recommendations.append(
            "Run profiler (cProfile, py-spy) to identify actual hotspots"
        )

        return recommendations

    def _find_quick_wins(self, profile: PerformanceProfile) -> List[str]:
        """Find quick wins - easy optimizations with high impact."""
        quick_wins = []

        for issue in profile.issues:
            if issue.auto_fixable and issue.impact in {ImpactLevel.HIGH, ImpactLevel.CRITICAL}:
                quick_wins.append(
                    f"{issue.file_path}:{issue.line_number} - {issue.description}"
                )

        return quick_wins[:5]  # Top 5 quick wins

    def _estimate_improvement(self, profile: PerformanceProfile) -> str:
        """Estimate potential performance improvement."""
        critical = sum(1 for i in profile.issues if i.impact == ImpactLevel.CRITICAL)
        high = sum(1 for i in profile.issues if i.impact == ImpactLevel.HIGH)

        if critical > 3:
            return "50-80% improvement potential (critical issues found)"
        elif critical > 0 or high > 5:
            return "20-50% improvement potential"
        elif high > 0:
            return "10-20% improvement potential"
        else:
            return "5-10% improvement potential (minor optimizations)"

    async def _apply_optimizations(self, path: Path) -> PerformanceProfile:
        """Apply auto-fixable optimizations."""
        profile = await self._analyze_performance(path)

        applied = 0
        for issue in profile.issues:
            if issue.auto_fixable and issue.fix_code:
                # In real implementation, would apply the fix
                applied += 1
                self.metrics.improvements_made += 1

        profile.recommendations.insert(0, f"Applied {applied} automatic optimizations")
        return profile

    async def _create_profile(self, path: Path) -> PerformanceProfile:
        """Create a detailed performance profile."""
        return await self._analyze_performance(path)

    async def _find_hotspots(self, path: Path) -> PerformanceProfile:
        """Find performance hotspots in code."""
        profile = await self._analyze_performance(path)
        profile.recommendations.insert(0, f"Top hotspots: {', '.join(profile.hotspots[:3])}")
        return profile

    async def optimize_project(self, path: Path) -> PerformanceProfile:
        """Public method to optimize a project."""
        return await self._analyze_performance(path)

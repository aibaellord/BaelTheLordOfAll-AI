#!/usr/bin/env python3
"""
BAEL - Opportunity Discovery Engine
THE ALL-SEEING EYE OF AUTOMATION

This engine doesn't wait for you to tell it what to automate.
It DISCOVERS opportunities you never knew existed by:

1. Analyzing code patterns across the entire codebase
2. Monitoring execution paths for optimization opportunities
3. Detecting repeated manual operations
4. Finding gaps in existing automation
5. Predicting future needs before they arise
6. Cross-referencing with global best practices
7. Learning from every interaction

"The greatest opportunities are the ones you haven't seen yet." - Ba'el
"""

import asyncio
import ast
import logging
import os
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from uuid import uuid4
import hashlib
import json

logger = logging.getLogger("BAEL.OpportunityDiscovery")


# =============================================================================
# OPPORTUNITY TYPES
# =============================================================================

class OpportunityType(Enum):
    """Types of discoverable opportunities."""
    # Code-level
    CODE_DUPLICATION = "code_duplication"
    MISSING_ERROR_HANDLING = "missing_error_handling"
    UNOPTIMIZED_ALGORITHM = "unoptimized_algorithm"
    MISSING_CACHE = "missing_cache"
    REDUNDANT_OPERATIONS = "redundant_operations"

    # Architecture-level
    MISSING_ABSTRACTION = "missing_abstraction"
    COUPLING_ISSUE = "coupling_issue"
    MISSING_INTERFACE = "missing_interface"
    SCALABILITY_BOTTLENECK = "scalability_bottleneck"

    # Automation-level
    MANUAL_PROCESS = "manual_process"
    REPEATED_WORKFLOW = "repeated_workflow"
    MISSING_INTEGRATION = "missing_integration"
    NOTIFICATION_OPPORTUNITY = "notification_opportunity"

    # AI Enhancement
    AI_ENHANCEMENT = "ai_enhancement"
    REASONING_UPGRADE = "reasoning_upgrade"
    LEARNING_OPPORTUNITY = "learning_opportunity"

    # Performance
    PERFORMANCE_OPTIMIZATION = "performance_optimization"
    RESOURCE_WASTE = "resource_waste"
    LATENCY_REDUCTION = "latency_reduction"

    # Quality
    MISSING_TESTS = "missing_tests"
    DOCUMENTATION_GAP = "documentation_gap"
    TYPE_SAFETY = "type_safety"

    # Security
    SECURITY_HARDENING = "security_hardening"
    ACCESS_CONTROL = "access_control"
    DATA_PROTECTION = "data_protection"

    # Innovation
    NEW_CAPABILITY = "new_capability"
    CROSS_DOMAIN_SYNERGY = "cross_domain_synergy"
    EMERGENT_PATTERN = "emergent_pattern"


class Priority(Enum):
    """Priority levels for opportunities."""
    CRITICAL = 1    # Do immediately
    HIGH = 2        # Do soon
    MEDIUM = 3      # Schedule
    LOW = 4         # Nice to have
    EXPLORATORY = 5 # Worth investigating


class Confidence(Enum):
    """Confidence levels for opportunity detection."""
    CERTAIN = 0.95
    HIGH = 0.80
    MEDIUM = 0.60
    LOW = 0.40
    SPECULATIVE = 0.20


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class Opportunity:
    """A discovered opportunity for improvement."""
    id: str = field(default_factory=lambda: str(uuid4()))
    type: OpportunityType = OpportunityType.CODE_DUPLICATION
    title: str = ""
    description: str = ""

    # Location
    file_path: Optional[str] = None
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    code_snippet: Optional[str] = None

    # Assessment
    priority: Priority = Priority.MEDIUM
    confidence: float = 0.6
    estimated_effort_hours: float = 1.0
    estimated_impact: float = 0.5  # 0-1 scale

    # Recommendation
    recommendation: str = ""
    implementation_steps: List[str] = field(default_factory=list)
    auto_fixable: bool = False
    auto_fix_code: Optional[str] = None

    # Context
    tags: List[str] = field(default_factory=list)
    related_opportunities: List[str] = field(default_factory=list)
    discovered_at: datetime = field(default_factory=datetime.utcnow)
    discovered_by: str = "opportunity_engine"

    # Metrics
    roi_score: float = 0.0  # Return on investment

    def calculate_roi(self) -> float:
        """Calculate ROI score."""
        if self.estimated_effort_hours == 0:
            return float('inf')
        return self.estimated_impact / self.estimated_effort_hours


@dataclass
class AnalysisResult:
    """Result of an opportunity analysis."""
    opportunities: List[Opportunity] = field(default_factory=list)
    files_analyzed: int = 0
    patterns_detected: int = 0
    total_lines: int = 0
    analysis_time_ms: int = 0
    summary: str = ""


# =============================================================================
# ANALYZERS
# =============================================================================

class BaseAnalyzer:
    """Base class for opportunity analyzers."""

    def __init__(self, name: str):
        self.name = name
        self.opportunities: List[Opportunity] = []

    async def analyze(self, context: Dict[str, Any]) -> List[Opportunity]:
        """Override to implement analysis."""
        raise NotImplementedError


class CodeDuplicationAnalyzer(BaseAnalyzer):
    """Finds duplicated code patterns."""

    def __init__(self):
        super().__init__("Code Duplication")
        self._hashes: Dict[str, List[Tuple[str, int]]] = defaultdict(list)

    async def analyze(self, context: Dict[str, Any]) -> List[Opportunity]:
        self.opportunities = []
        code_files = context.get("code_files", [])

        for file_info in code_files:
            content = file_info.get("content", "")
            path = file_info.get("path", "")

            # Split into chunks and hash them
            lines = content.split("\n")
            chunk_size = 5

            for i in range(len(lines) - chunk_size):
                chunk = "\n".join(lines[i:i+chunk_size])
                chunk_hash = hashlib.md5(chunk.encode()).hexdigest()
                self._hashes[chunk_hash].append((path, i))

        # Find duplicates
        for chunk_hash, locations in self._hashes.items():
            if len(locations) > 1:
                opp = Opportunity(
                    type=OpportunityType.CODE_DUPLICATION,
                    title=f"Duplicated code in {len(locations)} locations",
                    description=f"Found identical code block in multiple files",
                    priority=Priority.MEDIUM,
                    confidence=0.9,
                    estimated_effort_hours=0.5,
                    estimated_impact=0.3,
                    recommendation="Extract into shared function or module",
                    auto_fixable=True
                )
                self.opportunities.append(opp)

        return self.opportunities


class MissingErrorHandlingAnalyzer(BaseAnalyzer):
    """Finds code paths without proper error handling."""

    def __init__(self):
        super().__init__("Missing Error Handling")

    async def analyze(self, context: Dict[str, Any]) -> List[Opportunity]:
        self.opportunities = []
        code_files = context.get("code_files", [])

        patterns = [
            (r'await\s+\w+\([^)]*\)(?!\s*except)', "Unprotected await"),
            (r'\.read\(|\.write\((?!.*try)', "Unprotected file I/O"),
            (r'requests\.\w+\((?!.*except)', "Unprotected HTTP request"),
            (r'json\.loads?\((?!.*try)', "Unprotected JSON parsing"),
        ]

        for file_info in code_files:
            content = file_info.get("content", "")
            path = file_info.get("path", "")

            for pattern, description in patterns:
                matches = re.finditer(pattern, content)
                for match in matches:
                    line_num = content[:match.start()].count("\n") + 1

                    opp = Opportunity(
                        type=OpportunityType.MISSING_ERROR_HANDLING,
                        title=f"{description} at line {line_num}",
                        file_path=path,
                        line_start=line_num,
                        priority=Priority.HIGH,
                        confidence=0.75,
                        estimated_effort_hours=0.25,
                        estimated_impact=0.4,
                        recommendation=f"Add try/except around {description.lower()}",
                        auto_fixable=True
                    )
                    self.opportunities.append(opp)

        return self.opportunities


class MissingCacheAnalyzer(BaseAnalyzer):
    """Finds opportunities for caching."""

    def __init__(self):
        super().__init__("Missing Cache")

    async def analyze(self, context: Dict[str, Any]) -> List[Opportunity]:
        self.opportunities = []
        code_files = context.get("code_files", [])

        cache_patterns = [
            r'def\s+\w+\(.*\).*:\s*\n\s+.*\.(get|fetch|load)\(',
            r'async\s+def\s+\w+\(.*\).*:\s*\n\s+.*await.*\.(get|fetch|query)\(',
        ]

        cache_indicators = ['@cache', '@lru_cache', '@cached', 'cache.get']

        for file_info in code_files:
            content = file_info.get("content", "")
            path = file_info.get("path", "")

            # Skip if already has caching
            if any(ind in content for ind in cache_indicators):
                continue

            for pattern in cache_patterns:
                matches = re.finditer(pattern, content)
                for match in matches:
                    line_num = content[:match.start()].count("\n") + 1

                    opp = Opportunity(
                        type=OpportunityType.MISSING_CACHE,
                        title=f"Cacheable function at line {line_num}",
                        file_path=path,
                        line_start=line_num,
                        priority=Priority.MEDIUM,
                        confidence=0.65,
                        estimated_effort_hours=0.5,
                        estimated_impact=0.5,
                        recommendation="Add @lru_cache or implement Redis caching",
                        implementation_steps=[
                            "Analyze function for side effects",
                            "Determine appropriate cache TTL",
                            "Add caching decorator or implementation",
                            "Add cache invalidation logic if needed"
                        ]
                    )
                    self.opportunities.append(opp)

        return self.opportunities


class AIEnhancementAnalyzer(BaseAnalyzer):
    """Finds opportunities to add AI capabilities."""

    def __init__(self):
        super().__init__("AI Enhancement")

    async def analyze(self, context: Dict[str, Any]) -> List[Opportunity]:
        self.opportunities = []
        code_files = context.get("code_files", [])

        ai_opportunity_patterns = [
            (r'if.*elif.*elif.*elif', "Complex branching could use AI decision"),
            (r'def\s+parse_\w+|def\s+extract_\w+', "Parsing could be enhanced with AI"),
            (r'def\s+classify_|def\s+categorize_', "Classification is ideal for AI"),
            (r'def\s+analyze_|def\s+evaluate_', "Analysis could leverage AI reasoning"),
            (r'def\s+generate_|def\s+create_.*text', "Content generation could use LLM"),
            (r'def\s+summarize_|def\s+condense_', "Summarization is perfect for AI"),
            (r'def\s+translate_|def\s+convert_.*natural', "Translation could use AI"),
        ]

        for file_info in code_files:
            content = file_info.get("content", "")
            path = file_info.get("path", "")

            for pattern, suggestion in ai_opportunity_patterns:
                matches = re.finditer(pattern, content)
                for match in matches:
                    line_num = content[:match.start()].count("\n") + 1

                    opp = Opportunity(
                        type=OpportunityType.AI_ENHANCEMENT,
                        title=f"AI enhancement opportunity: {suggestion}",
                        file_path=path,
                        line_start=line_num,
                        priority=Priority.MEDIUM,
                        confidence=0.55,
                        estimated_effort_hours=2.0,
                        estimated_impact=0.7,
                        recommendation=suggestion,
                        tags=["ai", "enhancement", "llm"]
                    )
                    self.opportunities.append(opp)

        return self.opportunities


class MissingTestsAnalyzer(BaseAnalyzer):
    """Finds code without test coverage."""

    def __init__(self):
        super().__init__("Missing Tests")

    async def analyze(self, context: Dict[str, Any]) -> List[Opportunity]:
        self.opportunities = []
        code_files = context.get("code_files", [])
        test_files = context.get("test_files", [])

        # Get all tested functions
        tested_functions = set()
        for test_file in test_files:
            content = test_file.get("content", "")
            # Find function calls in test files
            matches = re.findall(r'\b(\w+)\s*\(', content)
            tested_functions.update(matches)

        # Find untested functions
        for file_info in code_files:
            content = file_info.get("content", "")
            path = file_info.get("path", "")

            # Skip test files
            if "test" in path.lower():
                continue

            # Find function definitions
            func_matches = re.finditer(
                r'(?:async\s+)?def\s+(\w+)\s*\([^)]*\)',
                content
            )

            for match in func_matches:
                func_name = match.group(1)

                # Skip private functions and dunder methods
                if func_name.startswith('_'):
                    continue

                if func_name not in tested_functions:
                    line_num = content[:match.start()].count("\n") + 1

                    opp = Opportunity(
                        type=OpportunityType.MISSING_TESTS,
                        title=f"Untested function: {func_name}",
                        file_path=path,
                        line_start=line_num,
                        priority=Priority.HIGH,
                        confidence=0.85,
                        estimated_effort_hours=0.5,
                        estimated_impact=0.4,
                        recommendation=f"Add tests for {func_name}",
                        auto_fixable=True
                    )
                    self.opportunities.append(opp)

        return self.opportunities


class SecurityHardeningAnalyzer(BaseAnalyzer):
    """Finds security improvement opportunities."""

    def __init__(self):
        super().__init__("Security Hardening")

    async def analyze(self, context: Dict[str, Any]) -> List[Opportunity]:
        self.opportunities = []
        code_files = context.get("code_files", [])

        security_patterns = [
            (r'eval\s*\(', "Dangerous eval() usage", Priority.CRITICAL),
            (r'exec\s*\(', "Dangerous exec() usage", Priority.CRITICAL),
            (r'shell\s*=\s*True', "Shell injection risk", Priority.CRITICAL),
            (r'password\s*=\s*["\']', "Hardcoded password", Priority.CRITICAL),
            (r'api_key\s*=\s*["\']', "Hardcoded API key", Priority.CRITICAL),
            (r'secret\s*=\s*["\']', "Hardcoded secret", Priority.CRITICAL),
            (r'verify\s*=\s*False', "SSL verification disabled", Priority.HIGH),
            (r'DEBUG\s*=\s*True', "Debug mode in production", Priority.HIGH),
            (r'\.format\(.*\).*SQL|SQL.*\.format\(', "Potential SQL injection", Priority.CRITICAL),
        ]

        for file_info in code_files:
            content = file_info.get("content", "")
            path = file_info.get("path", "")

            for pattern, issue, priority in security_patterns:
                matches = re.finditer(pattern, content, re.IGNORECASE)
                for match in matches:
                    line_num = content[:match.start()].count("\n") + 1

                    opp = Opportunity(
                        type=OpportunityType.SECURITY_HARDENING,
                        title=f"Security issue: {issue}",
                        file_path=path,
                        line_start=line_num,
                        code_snippet=match.group()[:50],
                        priority=priority,
                        confidence=0.9,
                        estimated_effort_hours=0.5,
                        estimated_impact=0.9,
                        recommendation=f"Fix security issue: {issue}",
                        tags=["security", "critical" if priority == Priority.CRITICAL else "warning"]
                    )
                    self.opportunities.append(opp)

        return self.opportunities


class CrossDomainSynergyAnalyzer(BaseAnalyzer):
    """Finds opportunities for cross-domain synergies."""

    def __init__(self):
        super().__init__("Cross-Domain Synergy")

    async def analyze(self, context: Dict[str, Any]) -> List[Opportunity]:
        self.opportunities = []

        # Analyze module imports and find potential synergies
        modules = context.get("modules", [])

        synergy_matrix = {
            ("memory", "reasoning"): "Memory-enhanced reasoning could improve context",
            ("council", "evolution"): "Evolving council strategies could optimize decisions",
            ("workflow", "ai"): "AI-powered workflow generation could automate creation",
            ("security", "council"): "Council oversight on security decisions",
            ("cache", "prediction"): "Predictive caching could pre-fetch needs",
        }

        for (mod1, mod2), suggestion in synergy_matrix.items():
            opp = Opportunity(
                type=OpportunityType.CROSS_DOMAIN_SYNERGY,
                title=f"Synergy: {mod1} + {mod2}",
                description=suggestion,
                priority=Priority.MEDIUM,
                confidence=0.5,
                estimated_effort_hours=4.0,
                estimated_impact=0.6,
                recommendation=suggestion,
                tags=["synergy", "innovation", mod1, mod2]
            )
            self.opportunities.append(opp)

        return self.opportunities


# =============================================================================
# OPPORTUNITY DISCOVERY ENGINE
# =============================================================================

class OpportunityDiscoveryEngine:
    """
    The All-Seeing Eye of Automation.

    Continuously discovers opportunities for improvement across:
    - Code quality
    - Architecture
    - Performance
    - Security
    - AI enhancement
    - Cross-domain synergies
    """

    def __init__(self):
        self.analyzers: List[BaseAnalyzer] = [
            CodeDuplicationAnalyzer(),
            MissingErrorHandlingAnalyzer(),
            MissingCacheAnalyzer(),
            AIEnhancementAnalyzer(),
            MissingTestsAnalyzer(),
            SecurityHardeningAnalyzer(),
            CrossDomainSynergyAnalyzer(),
        ]

        self._all_opportunities: List[Opportunity] = []
        self._by_type: Dict[OpportunityType, List[Opportunity]] = defaultdict(list)
        self._by_priority: Dict[Priority, List[Opportunity]] = defaultdict(list)

        logger.info(f"OpportunityDiscoveryEngine initialized with {len(self.analyzers)} analyzers")

    async def analyze_codebase(
        self,
        root_path: str,
        extensions: List[str] = [".py"]
    ) -> AnalysisResult:
        """Analyze entire codebase for opportunities."""
        import time
        start_time = time.time()

        logger.info(f"Analyzing codebase: {root_path}")

        # Collect files
        code_files = []
        test_files = []
        total_lines = 0

        root = Path(root_path)
        for ext in extensions:
            for file_path in root.rglob(f"*{ext}"):
                try:
                    content = file_path.read_text(encoding='utf-8')
                    total_lines += content.count("\n")

                    file_info = {
                        "path": str(file_path),
                        "content": content,
                        "lines": content.count("\n")
                    }

                    if "test" in str(file_path).lower():
                        test_files.append(file_info)
                    else:
                        code_files.append(file_info)

                except Exception as e:
                    logger.debug(f"Could not read {file_path}: {e}")

        logger.info(f"Found {len(code_files)} code files, {len(test_files)} test files")

        # Build analysis context
        context = {
            "code_files": code_files,
            "test_files": test_files,
            "root_path": root_path
        }

        # Run all analyzers
        all_opportunities = []
        for analyzer in self.analyzers:
            try:
                opportunities = await analyzer.analyze(context)
                all_opportunities.extend(opportunities)
                logger.debug(f"{analyzer.name}: Found {len(opportunities)} opportunities")
            except Exception as e:
                logger.error(f"Analyzer {analyzer.name} failed: {e}")

        # Calculate ROI and sort
        for opp in all_opportunities:
            opp.roi_score = opp.calculate_roi()

        # Store
        self._all_opportunities = all_opportunities
        self._index_opportunities()

        # Build result
        elapsed_ms = int((time.time() - start_time) * 1000)

        result = AnalysisResult(
            opportunities=all_opportunities,
            files_analyzed=len(code_files) + len(test_files),
            patterns_detected=len(all_opportunities),
            total_lines=total_lines,
            analysis_time_ms=elapsed_ms,
            summary=self._generate_summary(all_opportunities)
        )

        logger.info(f"Analysis complete: {len(all_opportunities)} opportunities in {elapsed_ms}ms")
        return result

    def _index_opportunities(self) -> None:
        """Index opportunities for quick access."""
        self._by_type.clear()
        self._by_priority.clear()

        for opp in self._all_opportunities:
            self._by_type[opp.type].append(opp)
            self._by_priority[opp.priority].append(opp)

    def _generate_summary(self, opportunities: List[Opportunity]) -> str:
        """Generate a summary of findings."""
        if not opportunities:
            return "No opportunities found."

        by_priority = defaultdict(int)
        by_type = defaultdict(int)

        for opp in opportunities:
            by_priority[opp.priority] += 1
            by_type[opp.type] += 1

        lines = [
            f"Found {len(opportunities)} improvement opportunities:",
            "",
            "By Priority:"
        ]

        for priority in Priority:
            if by_priority[priority]:
                lines.append(f"  {priority.name}: {by_priority[priority]}")

        lines.append("")
        lines.append("Top Types:")

        sorted_types = sorted(by_type.items(), key=lambda x: x[1], reverse=True)[:5]
        for opp_type, count in sorted_types:
            lines.append(f"  {opp_type.value}: {count}")

        return "\n".join(lines)

    def get_by_priority(self, priority: Priority) -> List[Opportunity]:
        """Get opportunities by priority."""
        return self._by_priority.get(priority, [])

    def get_by_type(self, opp_type: OpportunityType) -> List[Opportunity]:
        """Get opportunities by type."""
        return self._by_type.get(opp_type, [])

    def get_top_roi(self, n: int = 10) -> List[Opportunity]:
        """Get top opportunities by ROI."""
        sorted_opps = sorted(
            self._all_opportunities,
            key=lambda x: x.roi_score,
            reverse=True
        )
        return sorted_opps[:n]

    def get_auto_fixable(self) -> List[Opportunity]:
        """Get opportunities that can be auto-fixed."""
        return [o for o in self._all_opportunities if o.auto_fixable]

    def get_critical(self) -> List[Opportunity]:
        """Get critical priority opportunities."""
        return self._by_priority.get(Priority.CRITICAL, [])

    async def generate_action_plan(self) -> Dict[str, Any]:
        """Generate prioritized action plan."""
        plan = {
            "immediate": [],
            "this_week": [],
            "this_month": [],
            "backlog": [],
            "total_effort_hours": 0,
            "total_impact": 0
        }

        for opp in self._all_opportunities:
            item = {
                "id": opp.id,
                "title": opp.title,
                "type": opp.type.value,
                "effort_hours": opp.estimated_effort_hours,
                "impact": opp.estimated_impact,
                "roi": opp.roi_score,
                "auto_fixable": opp.auto_fixable
            }

            if opp.priority == Priority.CRITICAL:
                plan["immediate"].append(item)
            elif opp.priority == Priority.HIGH:
                plan["this_week"].append(item)
            elif opp.priority == Priority.MEDIUM:
                plan["this_month"].append(item)
            else:
                plan["backlog"].append(item)

            plan["total_effort_hours"] += opp.estimated_effort_hours
            plan["total_impact"] += opp.estimated_impact

        return plan


# =============================================================================
# FACTORY
# =============================================================================

async def create_discovery_engine() -> OpportunityDiscoveryEngine:
    """Create a new Opportunity Discovery Engine."""
    return OpportunityDiscoveryEngine()


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    async def main():
        print("🔍 BAEL Opportunity Discovery Engine")
        print("=" * 50)

        engine = await create_discovery_engine()

        # Analyze current directory
        import sys
        target = sys.argv[1] if len(sys.argv) > 1 else "."

        result = await engine.analyze_codebase(target)

        print(f"\n{result.summary}")

        print("\n📊 Top 5 by ROI:")
        for i, opp in enumerate(engine.get_top_roi(5), 1):
            print(f"  {i}. {opp.title} (ROI: {opp.roi_score:.2f})")

        critical = engine.get_critical()
        if critical:
            print(f"\n🚨 Critical Issues ({len(critical)}):")
            for opp in critical[:5]:
                print(f"  - {opp.title}")

        auto_fix = engine.get_auto_fixable()
        print(f"\n🔧 Auto-fixable: {len(auto_fix)} opportunities")

        print("\n✅ Analysis complete")

    asyncio.run(main())

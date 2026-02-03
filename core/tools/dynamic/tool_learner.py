"""
BAEL - Tool Learner
Learns and improves tools from usage patterns.
"""

import asyncio
import json
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from . import DynamicTool, ToolCategory, ToolType

logger = logging.getLogger("BAEL.Tools.Learner")


@dataclass
class ToolUsage:
    """Record of a tool usage."""
    tool_id: str
    inputs: Dict[str, Any]
    output: Any
    success: bool
    execution_time: float
    timestamp: float
    error: Optional[str] = None


@dataclass
class UsagePattern:
    """A learned usage pattern."""
    pattern_id: str
    tool_id: str
    input_pattern: Dict[str, str]  # param -> type pattern
    frequency: int
    avg_execution_time: float
    success_rate: float


@dataclass
class ToolImprovement:
    """A suggested tool improvement."""
    tool_id: str
    improvement_type: str
    description: str
    confidence: float
    suggested_change: Optional[str] = None


class ToolLearner:
    """
    Learns from tool usage to improve and optimize.

    Features:
    - Track usage patterns
    - Identify optimization opportunities
    - Suggest new tools based on usage
    - Improve error handling
    - Cache optimization
    """

    def __init__(self, storage_path: Optional[str] = None):
        self._storage_path = Path(storage_path) if storage_path else None

        self._usages: List[ToolUsage] = []
        self._patterns: Dict[str, UsagePattern] = {}
        self._improvements: List[ToolImprovement] = []

        # Analytics
        self._tool_stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "total_calls": 0,
            "successes": 0,
            "failures": 0,
            "total_time": 0,
            "input_types": defaultdict(int),
            "error_types": defaultdict(int)
        })

        self._llm = None

        # Load history
        self._load_history()

    def _load_history(self) -> None:
        """Load usage history from disk."""
        if not self._storage_path:
            return

        history_file = self._storage_path / "tool_usage_history.json"
        if history_file.exists():
            try:
                with open(history_file, "r") as f:
                    data = json.load(f)
                    # Restore patterns
                    for p_data in data.get("patterns", []):
                        pattern = UsagePattern(
                            pattern_id=p_data["pattern_id"],
                            tool_id=p_data["tool_id"],
                            input_pattern=p_data["input_pattern"],
                            frequency=p_data["frequency"],
                            avg_execution_time=p_data["avg_execution_time"],
                            success_rate=p_data["success_rate"]
                        )
                        self._patterns[pattern.pattern_id] = pattern

                    logger.info(f"Loaded {len(self._patterns)} usage patterns")
            except Exception as e:
                logger.warning(f"Failed to load history: {e}")

    def _save_history(self) -> None:
        """Save usage history to disk."""
        if not self._storage_path:
            return

        self._storage_path.mkdir(parents=True, exist_ok=True)
        history_file = self._storage_path / "tool_usage_history.json"

        try:
            data = {
                "patterns": [
                    {
                        "pattern_id": p.pattern_id,
                        "tool_id": p.tool_id,
                        "input_pattern": p.input_pattern,
                        "frequency": p.frequency,
                        "avg_execution_time": p.avg_execution_time,
                        "success_rate": p.success_rate
                    }
                    for p in self._patterns.values()
                ],
                "saved_at": time.time()
            }

            with open(history_file, "w") as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            logger.error(f"Failed to save history: {e}")

    async def _get_llm(self):
        """Lazy load LLM."""
        if self._llm is None:
            try:
                from core.llm import get_provider
                self._llm = get_provider()
            except ImportError:
                pass
        return self._llm

    def record_usage(
        self,
        tool_id: str,
        inputs: Dict[str, Any],
        output: Any,
        success: bool,
        execution_time: float,
        error: Optional[str] = None
    ) -> None:
        """
        Record a tool usage.

        Args:
            tool_id: Tool that was used
            inputs: Input arguments
            output: Output result
            success: Whether it succeeded
            execution_time: How long it took
            error: Error message if failed
        """
        usage = ToolUsage(
            tool_id=tool_id,
            inputs=inputs,
            output=output,
            success=success,
            execution_time=execution_time,
            timestamp=time.time(),
            error=error
        )

        self._usages.append(usage)

        # Update stats
        stats = self._tool_stats[tool_id]
        stats["total_calls"] += 1
        stats["total_time"] += execution_time

        if success:
            stats["successes"] += 1
        else:
            stats["failures"] += 1
            if error:
                error_type = error.split(":")[0]
                stats["error_types"][error_type] += 1

        # Track input types
        for param, value in inputs.items():
            type_name = type(value).__name__
            stats["input_types"][f"{param}:{type_name}"] += 1

        # Update patterns periodically
        if len(self._usages) % 10 == 0:
            self._update_patterns()

    def _update_patterns(self) -> None:
        """Update usage patterns from recent usages."""
        # Group usages by tool
        tool_usages: Dict[str, List[ToolUsage]] = defaultdict(list)
        for usage in self._usages[-100:]:  # Last 100 usages
            tool_usages[usage.tool_id].append(usage)

        # Analyze each tool
        for tool_id, usages in tool_usages.items():
            if len(usages) < 3:
                continue

            # Find common input patterns
            input_patterns: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))

            for usage in usages:
                for param, value in usage.inputs.items():
                    type_name = type(value).__name__
                    input_patterns[param][type_name] += 1

            # Create pattern
            dominant_pattern = {}
            for param, types in input_patterns.items():
                dominant_type = max(types.items(), key=lambda x: x[1])[0]
                dominant_pattern[param] = dominant_type

            # Calculate stats
            successes = sum(1 for u in usages if u.success)
            avg_time = sum(u.execution_time for u in usages) / len(usages)

            pattern_id = f"pattern_{tool_id}"
            self._patterns[pattern_id] = UsagePattern(
                pattern_id=pattern_id,
                tool_id=tool_id,
                input_pattern=dominant_pattern,
                frequency=len(usages),
                avg_execution_time=avg_time,
                success_rate=successes / len(usages)
            )

        self._save_history()

    async def analyze_tool(
        self,
        tool_id: str
    ) -> Dict[str, Any]:
        """
        Analyze a tool's usage and suggest improvements.

        Args:
            tool_id: Tool to analyze

        Returns:
            Analysis results with suggestions
        """
        stats = self._tool_stats.get(tool_id, {})

        if not stats.get("total_calls"):
            return {"error": "No usage data for this tool"}

        analysis = {
            "tool_id": tool_id,
            "total_calls": stats["total_calls"],
            "success_rate": stats["successes"] / stats["total_calls"],
            "avg_execution_time": stats["total_time"] / stats["total_calls"],
            "improvements": []
        }

        # Check for common issues
        if analysis["success_rate"] < 0.8:
            # High failure rate
            common_errors = sorted(
                stats["error_types"].items(),
                key=lambda x: x[1],
                reverse=True
            )[:3]

            analysis["improvements"].append(ToolImprovement(
                tool_id=tool_id,
                improvement_type="error_handling",
                description=f"High failure rate ({analysis['success_rate']:.1%}). Common errors: {common_errors}",
                confidence=0.8
            ))

        if analysis["avg_execution_time"] > 5.0:
            # Slow execution
            analysis["improvements"].append(ToolImprovement(
                tool_id=tool_id,
                improvement_type="performance",
                description=f"Slow execution ({analysis['avg_execution_time']:.2f}s avg). Consider caching or optimization.",
                confidence=0.7
            ))

        # Get LLM suggestions
        llm = await self._get_llm()
        if llm and stats["total_calls"] > 10:
            # Get pattern for context
            pattern = self._patterns.get(f"pattern_{tool_id}")

            suggest_prompt = f"""
Analyze this tool usage and suggest improvements:

Tool ID: {tool_id}
Total Calls: {stats['total_calls']}
Success Rate: {analysis['success_rate']:.1%}
Avg Execution Time: {analysis['avg_execution_time']:.2f}s
Common Input Types: {dict(list(stats['input_types'].items())[:5])}
Error Types: {dict(stats['error_types'])}

Suggest 1-2 specific improvements. Be concise.
"""
            try:
                suggestions = await llm.generate(suggest_prompt, temperature=0.5)
                analysis["llm_suggestions"] = suggestions
            except Exception:
                pass

        return analysis

    async def suggest_new_tools(self) -> List[Dict[str, Any]]:
        """
        Suggest new tools based on usage patterns.

        Returns:
            List of tool suggestions
        """
        suggestions = []

        # Analyze composition patterns
        tool_sequences: Dict[Tuple[str, str], int] = defaultdict(int)

        for i in range(len(self._usages) - 1):
            current = self._usages[i]
            next_usage = self._usages[i + 1]

            # If tools used within 10 seconds of each other
            if next_usage.timestamp - current.timestamp < 10:
                key = (current.tool_id, next_usage.tool_id)
                tool_sequences[key] += 1

        # Suggest compositions for common sequences
        for (tool1, tool2), count in sorted(
            tool_sequences.items(),
            key=lambda x: x[1],
            reverse=True
        )[:3]:
            if count >= 5:
                suggestions.append({
                    "type": "composition",
                    "description": f"Tools {tool1} and {tool2} are often used together ({count} times)",
                    "suggestion": f"Create a composed tool combining {tool1} -> {tool2}",
                    "confidence": min(0.9, count / 20)
                })

        # Suggest optimizations for slow tools
        for tool_id, stats in self._tool_stats.items():
            if stats["total_calls"] > 5:
                avg_time = stats["total_time"] / stats["total_calls"]
                if avg_time > 3.0:
                    suggestions.append({
                        "type": "caching",
                        "description": f"Tool {tool_id} is slow ({avg_time:.2f}s)",
                        "suggestion": "Add caching layer for repeated inputs",
                        "confidence": 0.7
                    })

        return suggestions

    def get_tool_stats(self, tool_id: str) -> Dict[str, Any]:
        """Get statistics for a tool."""
        stats = self._tool_stats.get(tool_id, {})

        if not stats.get("total_calls"):
            return {}

        return {
            "total_calls": stats["total_calls"],
            "success_rate": stats["successes"] / stats["total_calls"],
            "failure_rate": stats["failures"] / stats["total_calls"],
            "avg_execution_time": stats["total_time"] / stats["total_calls"],
            "common_input_types": dict(
                sorted(stats["input_types"].items(), key=lambda x: x[1], reverse=True)[:5]
            ),
            "error_breakdown": dict(stats["error_types"])
        }

    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all tools."""
        return {
            tool_id: self.get_tool_stats(tool_id)
            for tool_id in self._tool_stats
        }

    def get_patterns(self) -> List[UsagePattern]:
        """Get all learned patterns."""
        return list(self._patterns.values())

    def get_status(self) -> Dict[str, Any]:
        """Get learner status."""
        return {
            "total_usages_recorded": len(self._usages),
            "patterns_learned": len(self._patterns),
            "tools_tracked": len(self._tool_stats),
            "improvements_identified": len(self._improvements)
        }


# Global instance
_tool_learner: Optional[ToolLearner] = None


def get_tool_learner(
    storage_path: Optional[str] = None
) -> ToolLearner:
    """Get or create tool learner instance."""
    global _tool_learner
    if _tool_learner is None:
        _tool_learner = ToolLearner(storage_path)
    return _tool_learner

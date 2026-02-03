#!/usr/bin/env python3
"""
BAEL - Advanced Self-Reflection Engine
Metacognitive self-analysis and improvement.

Features:
- Performance introspection
- Capability assessment
- Learning pattern analysis
- Behavior optimization
- Goal alignment verification
- Cognitive load monitoring
"""

import asyncio
import json
import logging
import time
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from uuid import uuid4

logger = logging.getLogger(__name__)


# =============================================================================
# TYPES
# =============================================================================

class ReflectionType(Enum):
    """Types of self-reflection."""
    PERFORMANCE = "performance"
    CAPABILITY = "capability"
    BEHAVIOR = "behavior"
    LEARNING = "learning"
    ALIGNMENT = "alignment"
    COGNITIVE = "cognitive"


class InsightLevel(Enum):
    """Depth of insight."""
    SURFACE = "surface"  # Quick observations
    MODERATE = "moderate"  # Analysis
    DEEP = "deep"  # Root cause understanding


class CognitiveDomain(Enum):
    """Cognitive processing domains."""
    REASONING = "reasoning"
    MEMORY = "memory"
    PLANNING = "planning"
    LANGUAGE = "language"
    CREATIVITY = "creativity"
    LEARNING = "learning"
    ATTENTION = "attention"


@dataclass
class PerformanceMetric:
    """Performance measurement."""
    name: str
    value: float
    unit: str
    timestamp: datetime = field(default_factory=datetime.now)
    context: Dict[str, Any] = field(default_factory=dict)
    trend: Optional[float] = None  # Positive = improving


@dataclass
class Insight:
    """Self-reflection insight."""
    id: str
    type: ReflectionType
    level: InsightLevel
    title: str
    description: str
    evidence: List[str] = field(default_factory=list)
    implications: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    confidence: float = 1.0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class CapabilityProfile:
    """Profile of agent capabilities."""
    domain: CognitiveDomain
    proficiency: float  # 0-1
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    recent_performance: List[float] = field(default_factory=list)
    improvement_areas: List[str] = field(default_factory=list)


@dataclass
class LearningPattern:
    """Observed learning pattern."""
    pattern_name: str
    frequency: int
    success_rate: float
    contexts: List[str] = field(default_factory=list)
    optimal_conditions: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BehaviorPattern:
    """Observed behavior pattern."""
    pattern_id: str
    description: str
    triggers: List[str] = field(default_factory=list)
    frequency: int = 0
    effectiveness: float = 0.0
    should_modify: bool = False
    modification_suggestion: Optional[str] = None


# =============================================================================
# PERFORMANCE ANALYZER
# =============================================================================

class PerformanceAnalyzer:
    """Analyze agent performance."""

    def __init__(self):
        self.metrics_history: Dict[str, List[PerformanceMetric]] = defaultdict(list)
        self.baselines: Dict[str, float] = {}
        self.thresholds: Dict[str, Dict[str, float]] = {}

    def record_metric(
        self,
        name: str,
        value: float,
        unit: str = "",
        context: Dict[str, Any] = None
    ) -> PerformanceMetric:
        """Record a performance metric."""
        history = self.metrics_history[name]

        # Calculate trend
        trend = None
        if len(history) >= 3:
            recent = [m.value for m in history[-3:]]
            trend = (recent[-1] - recent[0]) / len(recent) if recent else 0

        metric = PerformanceMetric(
            name=name,
            value=value,
            unit=unit,
            context=context or {},
            trend=trend
        )

        self.metrics_history[name].append(metric)

        # Keep last 1000 entries per metric
        if len(self.metrics_history[name]) > 1000:
            self.metrics_history[name] = self.metrics_history[name][-500:]

        return metric

    def set_baseline(self, name: str, value: float) -> None:
        """Set baseline for a metric."""
        self.baselines[name] = value

    def set_thresholds(
        self,
        name: str,
        warning: float = None,
        critical: float = None,
        target: float = None
    ) -> None:
        """Set thresholds for a metric."""
        self.thresholds[name] = {
            "warning": warning,
            "critical": critical,
            "target": target
        }

    def analyze(self, name: str) -> Dict[str, Any]:
        """Analyze a specific metric."""
        if name not in self.metrics_history:
            return {"error": f"Metric {name} not found"}

        history = self.metrics_history[name]
        if not history:
            return {"error": "No data"}

        values = [m.value for m in history]
        recent = values[-10:] if len(values) >= 10 else values

        analysis = {
            "name": name,
            "current": values[-1],
            "average": sum(values) / len(values),
            "recent_average": sum(recent) / len(recent),
            "min": min(values),
            "max": max(values),
            "count": len(values),
            "trend": history[-1].trend
        }

        # Compare to baseline
        if name in self.baselines:
            baseline = self.baselines[name]
            analysis["baseline"] = baseline
            analysis["vs_baseline"] = (values[-1] - baseline) / baseline if baseline else 0

        # Check thresholds
        if name in self.thresholds:
            thresholds = self.thresholds[name]
            current = values[-1]

            if thresholds.get("critical") and current >= thresholds["critical"]:
                analysis["status"] = "critical"
            elif thresholds.get("warning") and current >= thresholds["warning"]:
                analysis["status"] = "warning"
            else:
                analysis["status"] = "normal"

            if thresholds.get("target"):
                analysis["target"] = thresholds["target"]
                analysis["target_gap"] = current - thresholds["target"]

        return analysis

    def get_summary(self) -> Dict[str, Dict[str, Any]]:
        """Get summary of all metrics."""
        return {name: self.analyze(name) for name in self.metrics_history}

    def identify_anomalies(
        self,
        name: str,
        std_threshold: float = 2.0
    ) -> List[PerformanceMetric]:
        """Identify anomalous values."""
        if name not in self.metrics_history:
            return []

        history = self.metrics_history[name]
        values = [m.value for m in history]

        if len(values) < 10:
            return []

        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        std = variance ** 0.5

        anomalies = []
        for metric in history:
            if abs(metric.value - mean) > std_threshold * std:
                anomalies.append(metric)

        return anomalies


# =============================================================================
# CAPABILITY ASSESSOR
# =============================================================================

class CapabilityAssessor:
    """Assess agent capabilities."""

    def __init__(self):
        self.profiles: Dict[CognitiveDomain, CapabilityProfile] = {}
        self.task_outcomes: List[Dict[str, Any]] = []
        self.capability_tests: Dict[str, Callable] = {}

        # Initialize profiles
        for domain in CognitiveDomain:
            self.profiles[domain] = CapabilityProfile(
                domain=domain,
                proficiency=0.5  # Start at baseline
            )

    def register_test(
        self,
        name: str,
        test_fn: Callable,
        domains: List[CognitiveDomain]
    ) -> None:
        """Register a capability test."""
        self.capability_tests[name] = {
            "fn": test_fn,
            "domains": domains
        }

    async def run_assessment(
        self,
        domains: List[CognitiveDomain] = None
    ) -> Dict[CognitiveDomain, CapabilityProfile]:
        """Run capability assessment."""
        domains = domains or list(CognitiveDomain)

        for name, test_info in self.capability_tests.items():
            test_domains = test_info["domains"]
            if not any(d in domains for d in test_domains):
                continue

            try:
                test_fn = test_info["fn"]
                if asyncio.iscoroutinefunction(test_fn):
                    score = await test_fn()
                else:
                    score = test_fn()

                # Update relevant profiles
                for domain in test_domains:
                    if domain in domains:
                        profile = self.profiles[domain]
                        profile.recent_performance.append(score)

                        # Keep last 50 scores
                        if len(profile.recent_performance) > 50:
                            profile.recent_performance = profile.recent_performance[-25:]

                        # Recalculate proficiency
                        profile.proficiency = sum(profile.recent_performance) / len(profile.recent_performance)

            except Exception as e:
                logger.error(f"Capability test {name} failed: {e}")

        return {d: self.profiles[d] for d in domains}

    def record_task_outcome(
        self,
        task_type: str,
        domains: List[CognitiveDomain],
        success: bool,
        quality: float,
        context: Dict[str, Any] = None
    ) -> None:
        """Record task outcome for capability tracking."""
        outcome = {
            "task_type": task_type,
            "domains": [d.value for d in domains],
            "success": success,
            "quality": quality,
            "context": context or {},
            "timestamp": datetime.now().isoformat()
        }

        self.task_outcomes.append(outcome)

        # Update profiles
        for domain in domains:
            profile = self.profiles[domain]
            score = quality if success else quality * 0.5
            profile.recent_performance.append(score)

            # Keep last 50
            if len(profile.recent_performance) > 50:
                profile.recent_performance = profile.recent_performance[-25:]

            # Recalculate
            profile.proficiency = sum(profile.recent_performance) / len(profile.recent_performance)

    def identify_strengths_weaknesses(self) -> Dict[str, List[CognitiveDomain]]:
        """Identify strengths and weaknesses."""
        sorted_domains = sorted(
            self.profiles.items(),
            key=lambda x: x[1].proficiency,
            reverse=True
        )

        strengths = []
        weaknesses = []

        for domain, profile in sorted_domains:
            if profile.proficiency >= 0.7:
                strengths.append(domain)
            elif profile.proficiency < 0.4:
                weaknesses.append(domain)

        return {
            "strengths": strengths,
            "weaknesses": weaknesses,
            "profiles": {d.value: p.proficiency for d, p in self.profiles.items()}
        }

    def get_improvement_recommendations(self) -> List[str]:
        """Get recommendations for improvement."""
        recommendations = []

        for domain, profile in self.profiles.items():
            if profile.proficiency < 0.5:
                recommendations.append(
                    f"Focus on improving {domain.value} capabilities through targeted practice"
                )

            # Check for declining performance
            if len(profile.recent_performance) >= 5:
                recent = profile.recent_performance[-5:]
                if recent[-1] < recent[0]:
                    recommendations.append(
                        f"Address declining performance in {domain.value} domain"
                    )

        return recommendations


# =============================================================================
# BEHAVIOR ANALYZER
# =============================================================================

class BehaviorAnalyzer:
    """Analyze agent behavior patterns."""

    def __init__(self):
        self.action_log: List[Dict[str, Any]] = []
        self.patterns: Dict[str, BehaviorPattern] = {}
        self.sequence_buffer: List[str] = []
        self.sequence_window = 5

    def log_action(
        self,
        action: str,
        context: Dict[str, Any],
        outcome: str,
        effectiveness: float
    ) -> None:
        """Log an action for analysis."""
        entry = {
            "action": action,
            "context": context,
            "outcome": outcome,
            "effectiveness": effectiveness,
            "timestamp": datetime.now().isoformat()
        }

        self.action_log.append(entry)
        self.sequence_buffer.append(action)

        # Keep window size
        if len(self.sequence_buffer) > self.sequence_window:
            self.sequence_buffer.pop(0)

        # Keep last 10000 actions
        if len(self.action_log) > 10000:
            self.action_log = self.action_log[-5000:]

    def analyze_patterns(self) -> List[BehaviorPattern]:
        """Analyze action patterns."""
        # Count action sequences
        sequences: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {"count": 0, "effectiveness": [], "contexts": set()}
        )

        for i in range(len(self.action_log) - 1):
            current = self.action_log[i]
            next_action = self.action_log[i + 1]

            seq_key = f"{current['action']} -> {next_action['action']}"
            sequences[seq_key]["count"] += 1
            sequences[seq_key]["effectiveness"].append(current["effectiveness"])

            for k, v in current["context"].items():
                if isinstance(v, str):
                    sequences[seq_key]["contexts"].add(f"{k}:{v}")

        # Create patterns
        patterns = []
        for seq, data in sequences.items():
            if data["count"] >= 3:  # Minimum frequency
                avg_effectiveness = sum(data["effectiveness"]) / len(data["effectiveness"])

                pattern = BehaviorPattern(
                    pattern_id=str(uuid4())[:8],
                    description=seq,
                    triggers=list(data["contexts"])[:5],
                    frequency=data["count"],
                    effectiveness=avg_effectiveness,
                    should_modify=avg_effectiveness < 0.5,
                    modification_suggestion=(
                        f"Consider alternative actions when {seq}"
                        if avg_effectiveness < 0.5 else None
                    )
                )
                patterns.append(pattern)
                self.patterns[pattern.pattern_id] = pattern

        return sorted(patterns, key=lambda p: p.frequency, reverse=True)

    def get_ineffective_patterns(self) -> List[BehaviorPattern]:
        """Get patterns that should be modified."""
        return [p for p in self.patterns.values() if p.should_modify]

    def suggest_behavior_changes(self) -> List[str]:
        """Suggest behavior changes."""
        suggestions = []

        ineffective = self.get_ineffective_patterns()
        for pattern in ineffective[:5]:
            suggestions.append(
                f"Pattern '{pattern.description}' has low effectiveness "
                f"({pattern.effectiveness:.0%}). {pattern.modification_suggestion or 'Review and modify.'}"
            )

        # Analyze action distribution
        action_counts: Dict[str, int] = defaultdict(int)
        for entry in self.action_log:
            action_counts[entry["action"]] += 1

        total = len(self.action_log) or 1
        for action, count in action_counts.items():
            if count / total > 0.5:
                suggestions.append(
                    f"Over-reliance on '{action}' ({count/total:.0%}). "
                    "Consider diversifying approaches."
                )

        return suggestions


# =============================================================================
# LEARNING ANALYZER
# =============================================================================

class LearningAnalyzer:
    """Analyze learning patterns and progress."""

    def __init__(self):
        self.learning_events: List[Dict[str, Any]] = []
        self.patterns: Dict[str, LearningPattern] = {}
        self.knowledge_gains: Dict[str, List[float]] = defaultdict(list)

    def record_learning(
        self,
        topic: str,
        method: str,
        pre_knowledge: float,
        post_knowledge: float,
        context: Dict[str, Any] = None
    ) -> None:
        """Record a learning event."""
        event = {
            "topic": topic,
            "method": method,
            "pre_knowledge": pre_knowledge,
            "post_knowledge": post_knowledge,
            "gain": post_knowledge - pre_knowledge,
            "context": context or {},
            "timestamp": datetime.now().isoformat()
        }

        self.learning_events.append(event)
        self.knowledge_gains[topic].append(event["gain"])

        # Update patterns
        pattern_key = f"{method}:{topic}"
        if pattern_key not in self.patterns:
            self.patterns[pattern_key] = LearningPattern(
                pattern_name=pattern_key,
                frequency=0,
                success_rate=0.0,
                contexts=[]
            )

        pattern = self.patterns[pattern_key]
        pattern.frequency += 1

        # Update success rate (gain > 0 is success)
        gains = [e["gain"] for e in self.learning_events if f"{e['method']}:{e['topic']}" == pattern_key]
        pattern.success_rate = sum(1 for g in gains if g > 0) / len(gains) if gains else 0

    def analyze_learning_efficiency(self) -> Dict[str, Any]:
        """Analyze overall learning efficiency."""
        if not self.learning_events:
            return {"status": "no_data"}

        total_gain = sum(e["gain"] for e in self.learning_events)
        avg_gain = total_gain / len(self.learning_events)

        # By method
        by_method: Dict[str, List[float]] = defaultdict(list)
        for event in self.learning_events:
            by_method[event["method"]].append(event["gain"])

        method_efficiency = {
            method: sum(gains) / len(gains)
            for method, gains in by_method.items()
        }

        best_method = max(method_efficiency.items(), key=lambda x: x[1]) if method_efficiency else None

        return {
            "total_events": len(self.learning_events),
            "total_gain": total_gain,
            "average_gain": avg_gain,
            "by_method": method_efficiency,
            "best_method": best_method[0] if best_method else None,
            "best_method_efficiency": best_method[1] if best_method else 0
        }

    def get_optimal_learning_conditions(self) -> Dict[str, Any]:
        """Identify optimal learning conditions."""
        successful = [e for e in self.learning_events if e["gain"] > 0.1]

        if not successful:
            return {"status": "insufficient_data"}

        # Analyze context patterns
        context_factors: Dict[str, Dict[Any, int]] = defaultdict(lambda: defaultdict(int))

        for event in successful:
            for key, value in event["context"].items():
                context_factors[key][value] += 1

        optimal_conditions = {}
        for factor, values in context_factors.items():
            if values:
                best = max(values.items(), key=lambda x: x[1])
                optimal_conditions[factor] = best[0]

        return {
            "optimal_conditions": optimal_conditions,
            "sample_size": len(successful)
        }

    def identify_learning_gaps(self) -> List[str]:
        """Identify areas with learning gaps."""
        gaps = []

        for topic, gains in self.knowledge_gains.items():
            if gains:
                avg_gain = sum(gains) / len(gains)
                if avg_gain < 0.05:  # Low learning rate
                    gaps.append(topic)

        return gaps


# =============================================================================
# GOAL ALIGNMENT CHECKER
# =============================================================================

class GoalAlignmentChecker:
    """Check alignment between actions and goals."""

    def __init__(self):
        self.goals: Dict[str, Dict[str, Any]] = {}
        self.actions: List[Dict[str, Any]] = []

    def set_goal(
        self,
        goal_id: str,
        description: str,
        priority: int = 1,
        criteria: List[str] = None
    ) -> None:
        """Set a goal."""
        self.goals[goal_id] = {
            "id": goal_id,
            "description": description,
            "priority": priority,
            "criteria": criteria or [],
            "progress": 0.0,
            "aligned_actions": 0,
            "misaligned_actions": 0
        }

    def record_action(
        self,
        action: str,
        goal_ids: List[str],
        alignment_score: float,
        context: Dict[str, Any] = None
    ) -> None:
        """Record an action with goal alignment."""
        entry = {
            "action": action,
            "goal_ids": goal_ids,
            "alignment_score": alignment_score,
            "context": context or {},
            "timestamp": datetime.now().isoformat()
        }

        self.actions.append(entry)

        # Update goal statistics
        for goal_id in goal_ids:
            if goal_id in self.goals:
                if alignment_score >= 0.5:
                    self.goals[goal_id]["aligned_actions"] += 1
                else:
                    self.goals[goal_id]["misaligned_actions"] += 1

    def check_alignment(self) -> Dict[str, Any]:
        """Check overall goal alignment."""
        if not self.actions:
            return {"status": "no_actions"}

        total_alignment = sum(a["alignment_score"] for a in self.actions)
        avg_alignment = total_alignment / len(self.actions)

        goal_alignment = {}
        for goal_id, goal in self.goals.items():
            total = goal["aligned_actions"] + goal["misaligned_actions"]
            if total > 0:
                goal_alignment[goal_id] = {
                    "description": goal["description"],
                    "alignment_ratio": goal["aligned_actions"] / total,
                    "total_actions": total
                }

        return {
            "overall_alignment": avg_alignment,
            "total_actions": len(self.actions),
            "by_goal": goal_alignment,
            "alignment_trend": self._calculate_trend()
        }

    def _calculate_trend(self) -> Optional[str]:
        """Calculate alignment trend."""
        if len(self.actions) < 10:
            return None

        first_half = self.actions[:len(self.actions)//2]
        second_half = self.actions[len(self.actions)//2:]

        first_avg = sum(a["alignment_score"] for a in first_half) / len(first_half)
        second_avg = sum(a["alignment_score"] for a in second_half) / len(second_half)

        if second_avg > first_avg + 0.1:
            return "improving"
        elif second_avg < first_avg - 0.1:
            return "declining"
        return "stable"

    def get_misalignment_report(self) -> List[Dict[str, Any]]:
        """Get report of misaligned actions."""
        misaligned = [a for a in self.actions if a["alignment_score"] < 0.5]

        return [
            {
                "action": a["action"],
                "alignment_score": a["alignment_score"],
                "intended_goals": a["goal_ids"],
                "timestamp": a["timestamp"]
            }
            for a in sorted(misaligned, key=lambda x: x["alignment_score"])[:10]
        ]


# =============================================================================
# COGNITIVE LOAD MONITOR
# =============================================================================

class CognitiveLoadMonitor:
    """Monitor cognitive load and resource usage."""

    def __init__(self):
        self.load_samples: List[Dict[str, float]] = []
        self.thresholds = {
            "attention": 0.8,
            "memory": 0.85,
            "processing": 0.9
        }

    def sample_load(
        self,
        attention: float,
        memory: float,
        processing: float,
        context_size: int = 0
    ) -> Dict[str, Any]:
        """Sample current cognitive load."""
        sample = {
            "attention": attention,
            "memory": memory,
            "processing": processing,
            "context_size": context_size,
            "timestamp": datetime.now().isoformat(),
            "overall": (attention + memory + processing) / 3
        }

        self.load_samples.append(sample)

        # Keep last 1000
        if len(self.load_samples) > 1000:
            self.load_samples = self.load_samples[-500:]

        # Check for overload
        warnings = []
        for metric, threshold in self.thresholds.items():
            if sample.get(metric, 0) > threshold:
                warnings.append(f"{metric} overload: {sample[metric]:.0%}")

        sample["warnings"] = warnings
        return sample

    def get_average_load(
        self,
        window_minutes: int = 5
    ) -> Dict[str, float]:
        """Get average load over time window."""
        if not self.load_samples:
            return {}

        cutoff = datetime.now() - timedelta(minutes=window_minutes)
        recent = [
            s for s in self.load_samples
            if datetime.fromisoformat(s["timestamp"]) >= cutoff
        ]

        if not recent:
            recent = self.load_samples[-10:]

        return {
            "attention": sum(s["attention"] for s in recent) / len(recent),
            "memory": sum(s["memory"] for s in recent) / len(recent),
            "processing": sum(s["processing"] for s in recent) / len(recent),
            "overall": sum(s["overall"] for s in recent) / len(recent),
            "sample_count": len(recent)
        }

    def predict_overload(self) -> Dict[str, Any]:
        """Predict potential overload."""
        if len(self.load_samples) < 5:
            return {"prediction": "insufficient_data"}

        recent = self.load_samples[-5:]

        predictions = {}
        for metric in ["attention", "memory", "processing"]:
            values = [s[metric] for s in recent]
            trend = (values[-1] - values[0]) / len(values)

            current = values[-1]
            threshold = self.thresholds[metric]

            if trend > 0:
                steps_to_overload = (threshold - current) / trend if trend > 0 else float('inf')
                if steps_to_overload < 10:
                    predictions[metric] = {
                        "risk": "high",
                        "current": current,
                        "trend": trend,
                        "steps_to_overload": steps_to_overload
                    }

        return {
            "predictions": predictions,
            "overall_risk": "high" if predictions else "low"
        }

    def recommend_load_reduction(self) -> List[str]:
        """Recommend ways to reduce cognitive load."""
        recommendations = []

        avg = self.get_average_load()

        if avg.get("attention", 0) > 0.7:
            recommendations.append("Reduce task switching and focus on one task at a time")

        if avg.get("memory", 0) > 0.7:
            recommendations.append("Offload information to external memory/notes")
            recommendations.append("Summarize and compress context")

        if avg.get("processing", 0) > 0.7:
            recommendations.append("Break complex tasks into smaller steps")
            recommendations.append("Use cached results where possible")

        if avg.get("overall", 0) > 0.8:
            recommendations.append("Take a processing pause to consolidate")

        return recommendations


# =============================================================================
# SELF-REFLECTION ENGINE
# =============================================================================

class SelfReflectionEngine:
    """Main self-reflection and metacognition engine."""

    def __init__(self):
        self.performance = PerformanceAnalyzer()
        self.capabilities = CapabilityAssessor()
        self.behavior = BehaviorAnalyzer()
        self.learning = LearningAnalyzer()
        self.alignment = GoalAlignmentChecker()
        self.cognitive = CognitiveLoadMonitor()
        self.insights: List[Insight] = []

    async def reflect(
        self,
        reflection_type: ReflectionType = None,
        depth: InsightLevel = InsightLevel.MODERATE
    ) -> List[Insight]:
        """Perform self-reflection."""
        new_insights = []

        types = [reflection_type] if reflection_type else list(ReflectionType)

        for rtype in types:
            if rtype == ReflectionType.PERFORMANCE:
                new_insights.extend(await self._reflect_performance(depth))
            elif rtype == ReflectionType.CAPABILITY:
                new_insights.extend(await self._reflect_capability(depth))
            elif rtype == ReflectionType.BEHAVIOR:
                new_insights.extend(await self._reflect_behavior(depth))
            elif rtype == ReflectionType.LEARNING:
                new_insights.extend(await self._reflect_learning(depth))
            elif rtype == ReflectionType.ALIGNMENT:
                new_insights.extend(await self._reflect_alignment(depth))
            elif rtype == ReflectionType.COGNITIVE:
                new_insights.extend(await self._reflect_cognitive(depth))

        self.insights.extend(new_insights)
        return new_insights

    async def _reflect_performance(
        self,
        depth: InsightLevel
    ) -> List[Insight]:
        """Reflect on performance."""
        insights = []

        summary = self.performance.get_summary()

        for metric_name, analysis in summary.items():
            if isinstance(analysis, dict) and analysis.get("status") == "critical":
                insights.append(Insight(
                    id=str(uuid4()),
                    type=ReflectionType.PERFORMANCE,
                    level=depth,
                    title=f"Critical: {metric_name}",
                    description=f"Metric {metric_name} is at critical level: {analysis.get('current')}",
                    evidence=[f"Threshold: {self.performance.thresholds.get(metric_name, {}).get('critical')}"],
                    recommendations=["Immediate attention required", "Review recent changes"]
                ))

            if isinstance(analysis, dict) and analysis.get("trend", 0) < -0.1:
                insights.append(Insight(
                    id=str(uuid4()),
                    type=ReflectionType.PERFORMANCE,
                    level=depth,
                    title=f"Declining: {metric_name}",
                    description=f"Performance on {metric_name} is declining",
                    evidence=[f"Trend: {analysis.get('trend', 0):.2f}"],
                    recommendations=["Investigate root cause", "Consider process changes"]
                ))

        return insights

    async def _reflect_capability(
        self,
        depth: InsightLevel
    ) -> List[Insight]:
        """Reflect on capabilities."""
        insights = []

        sw = self.capabilities.identify_strengths_weaknesses()

        for weakness in sw.get("weaknesses", []):
            insights.append(Insight(
                id=str(uuid4()),
                type=ReflectionType.CAPABILITY,
                level=depth,
                title=f"Weakness: {weakness.value}",
                description=f"Low proficiency in {weakness.value} domain",
                evidence=[f"Proficiency: {sw['profiles'].get(weakness.value, 0):.0%}"],
                recommendations=self.capabilities.get_improvement_recommendations()[:2]
            ))

        return insights

    async def _reflect_behavior(
        self,
        depth: InsightLevel
    ) -> List[Insight]:
        """Reflect on behavior patterns."""
        insights = []

        ineffective = self.behavior.get_ineffective_patterns()

        for pattern in ineffective[:3]:
            insights.append(Insight(
                id=str(uuid4()),
                type=ReflectionType.BEHAVIOR,
                level=depth,
                title=f"Ineffective Pattern: {pattern.pattern_id}",
                description=pattern.description,
                evidence=[f"Effectiveness: {pattern.effectiveness:.0%}"],
                recommendations=[pattern.modification_suggestion] if pattern.modification_suggestion else []
            ))

        suggestions = self.behavior.suggest_behavior_changes()
        for suggestion in suggestions[:2]:
            insights.append(Insight(
                id=str(uuid4()),
                type=ReflectionType.BEHAVIOR,
                level=depth,
                title="Behavior Suggestion",
                description=suggestion,
                recommendations=[]
            ))

        return insights

    async def _reflect_learning(
        self,
        depth: InsightLevel
    ) -> List[Insight]:
        """Reflect on learning patterns."""
        insights = []

        efficiency = self.learning.analyze_learning_efficiency()

        if efficiency.get("average_gain", 0) < 0.05:
            insights.append(Insight(
                id=str(uuid4()),
                type=ReflectionType.LEARNING,
                level=depth,
                title="Low Learning Efficiency",
                description=f"Average learning gain is low: {efficiency.get('average_gain', 0):.2f}",
                evidence=[f"Best method: {efficiency.get('best_method')}"],
                recommendations=[f"Focus on {efficiency.get('best_method', 'varied')} learning methods"]
            ))

        gaps = self.learning.identify_learning_gaps()
        for gap in gaps[:3]:
            insights.append(Insight(
                id=str(uuid4()),
                type=ReflectionType.LEARNING,
                level=depth,
                title=f"Learning Gap: {gap}",
                description=f"Struggling to learn effectively about {gap}",
                recommendations=["Try different learning approaches", "Break topic into smaller pieces"]
            ))

        return insights

    async def _reflect_alignment(
        self,
        depth: InsightLevel
    ) -> List[Insight]:
        """Reflect on goal alignment."""
        insights = []

        alignment = self.alignment.check_alignment()

        if alignment.get("overall_alignment", 1) < 0.6:
            insights.append(Insight(
                id=str(uuid4()),
                type=ReflectionType.ALIGNMENT,
                level=depth,
                title="Low Goal Alignment",
                description=f"Actions are not well aligned with goals: {alignment.get('overall_alignment', 0):.0%}",
                evidence=[f"Trend: {alignment.get('alignment_trend', 'unknown')}"],
                recommendations=["Review goals and priorities", "Adjust action selection"]
            ))

        misaligned = self.alignment.get_misalignment_report()
        for action in misaligned[:2]:
            insights.append(Insight(
                id=str(uuid4()),
                type=ReflectionType.ALIGNMENT,
                level=depth,
                title=f"Misaligned Action: {action['action']}",
                description=f"Action had low alignment: {action['alignment_score']:.0%}",
                evidence=[f"Intended goals: {action['intended_goals']}"],
                recommendations=["Review action selection criteria"]
            ))

        return insights

    async def _reflect_cognitive(
        self,
        depth: InsightLevel
    ) -> List[Insight]:
        """Reflect on cognitive load."""
        insights = []

        avg_load = self.cognitive.get_average_load()

        if avg_load.get("overall", 0) > 0.7:
            insights.append(Insight(
                id=str(uuid4()),
                type=ReflectionType.COGNITIVE,
                level=depth,
                title="High Cognitive Load",
                description=f"Average cognitive load is high: {avg_load.get('overall', 0):.0%}",
                evidence=[
                    f"Attention: {avg_load.get('attention', 0):.0%}",
                    f"Memory: {avg_load.get('memory', 0):.0%}",
                    f"Processing: {avg_load.get('processing', 0):.0%}"
                ],
                recommendations=self.cognitive.recommend_load_reduction()
            ))

        prediction = self.cognitive.predict_overload()
        if prediction.get("overall_risk") == "high":
            for metric, pred in prediction.get("predictions", {}).items():
                insights.append(Insight(
                    id=str(uuid4()),
                    type=ReflectionType.COGNITIVE,
                    level=depth,
                    title=f"Overload Risk: {metric}",
                    description=f"Risk of {metric} overload detected",
                    evidence=[f"Steps to overload: {pred.get('steps_to_overload', 'N/A'):.0f}"],
                    recommendations=["Reduce load immediately", "Offload tasks"]
                ))

        return insights

    def get_self_assessment(self) -> Dict[str, Any]:
        """Get comprehensive self-assessment."""
        return {
            "performance_summary": self.performance.get_summary(),
            "capability_profile": self.capabilities.identify_strengths_weaknesses(),
            "behavior_patterns": len(self.behavior.patterns),
            "learning_efficiency": self.learning.analyze_learning_efficiency(),
            "goal_alignment": self.alignment.check_alignment(),
            "cognitive_load": self.cognitive.get_average_load(),
            "recent_insights": [
                {
                    "type": i.type.value,
                    "title": i.title,
                    "description": i.description
                }
                for i in self.insights[-10:]
            ]
        }

    def get_improvement_plan(self) -> Dict[str, Any]:
        """Generate improvement plan based on reflection."""
        return {
            "capability_improvements": self.capabilities.get_improvement_recommendations(),
            "behavior_changes": self.behavior.suggest_behavior_changes(),
            "learning_focus": self.learning.identify_learning_gaps(),
            "load_management": self.cognitive.recommend_load_reduction(),
            "priority_insights": [
                {
                    "title": i.title,
                    "recommendations": i.recommendations
                }
                for i in sorted(self.insights, key=lambda x: x.confidence, reverse=True)[:5]
            ]
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demo self-reflection engine."""
    engine = SelfReflectionEngine()

    print("=== Self-Reflection Engine Demo ===\n")

    # Record some data
    print("Recording sample data...")

    # Performance metrics
    for i in range(20):
        engine.performance.record_metric("response_time", 100 + i * 5, "ms")
        engine.performance.record_metric("accuracy", 0.8 - i * 0.01, "ratio")

    engine.performance.set_thresholds("accuracy", warning=0.7, critical=0.6, target=0.9)

    # Capability outcomes
    for _ in range(10):
        engine.capabilities.record_task_outcome(
            "reasoning_task",
            [CognitiveDomain.REASONING],
            success=True,
            quality=0.75
        )
        engine.capabilities.record_task_outcome(
            "memory_task",
            [CognitiveDomain.MEMORY],
            success=False,
            quality=0.4
        )

    # Behavior actions
    for i in range(15):
        engine.behavior.log_action(
            action="search",
            context={"topic": "general"},
            outcome="found",
            effectiveness=0.7
        )
        engine.behavior.log_action(
            action="retry",
            context={"topic": "general"},
            outcome="failed",
            effectiveness=0.3
        )

    # Learning events
    engine.learning.record_learning(
        topic="new_api",
        method="documentation",
        pre_knowledge=0.2,
        post_knowledge=0.7
    )
    engine.learning.record_learning(
        topic="complex_math",
        method="practice",
        pre_knowledge=0.3,
        post_knowledge=0.35
    )

    # Goal alignment
    engine.alignment.set_goal("help_users", "Provide helpful responses", priority=1)
    engine.alignment.record_action("clarify", ["help_users"], alignment_score=0.9)
    engine.alignment.record_action("ignore", ["help_users"], alignment_score=0.2)

    # Cognitive load
    for i in range(10):
        engine.cognitive.sample_load(
            attention=0.5 + i * 0.03,
            memory=0.6 + i * 0.02,
            processing=0.4 + i * 0.04
        )

    # Perform reflection
    print("\nPerforming self-reflection...\n")
    insights = await engine.reflect()

    print(f"Generated {len(insights)} insights:\n")
    for insight in insights[:5]:
        print(f"  [{insight.type.value}] {insight.title}")
        print(f"    {insight.description}")
        if insight.recommendations:
            print(f"    Recommendations: {insight.recommendations[0]}")
        print()

    # Get self-assessment
    print("Self-Assessment Summary:")
    assessment = engine.get_self_assessment()
    print(f"  Capability strengths: {assessment['capability_profile'].get('strengths', [])}")
    print(f"  Capability weaknesses: {assessment['capability_profile'].get('weaknesses', [])}")
    print(f"  Goal alignment: {assessment['goal_alignment'].get('overall_alignment', 0):.0%}")
    print(f"  Cognitive load: {assessment['cognitive_load'].get('overall', 0):.0%}")

    # Get improvement plan
    print("\nImprovement Plan:")
    plan = engine.get_improvement_plan()
    for rec in plan.get("capability_improvements", [])[:2]:
        print(f"  - {rec}")


if __name__ == "__main__":
    asyncio.run(demo())

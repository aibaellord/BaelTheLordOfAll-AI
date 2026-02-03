"""
BAEL - Advanced Learning & Adaptation Engine
Continuous learning, skill acquisition, and capability evolution.

This module enables BAEL to:
- Learn from every interaction
- Acquire new skills dynamically
- Adapt behavior based on feedback
- Evolve capabilities over time
"""

import asyncio
import hashlib
import json
import logging
import pickle
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS & TYPES
# =============================================================================

class LearningMode(Enum):
    """Types of learning."""
    SUPERVISED = "supervised"           # Learn from labeled examples
    REINFORCEMENT = "reinforcement"     # Learn from rewards/penalties
    SELF_SUPERVISED = "self_supervised" # Learn from self-generated signals
    TRANSFER = "transfer"               # Apply learning from one domain to another
    META = "meta"                       # Learn how to learn
    IMITATION = "imitation"             # Learn by observing


class SkillLevel(Enum):
    """Proficiency levels for skills."""
    NOVICE = "novice"
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"
    MASTER = "master"


class FeedbackType(Enum):
    """Types of feedback."""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    CORRECTIVE = "corrective"


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class Skill:
    """Represents a learned skill."""
    id: str
    name: str
    domain: str
    level: SkillLevel = SkillLevel.NOVICE
    experience_points: int = 0
    practice_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    patterns: List[Dict[str, Any]] = field(default_factory=list)
    strategies: List[str] = field(default_factory=list)
    related_skills: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    last_used: datetime = field(default_factory=datetime.now)

    @property
    def success_rate(self) -> float:
        total = self.success_count + self.failure_count
        return self.success_count / total if total > 0 else 0.0

    def add_experience(self, xp: int) -> None:
        """Add experience points and potentially level up."""
        self.experience_points += xp
        self._check_level_up()

    def _check_level_up(self) -> None:
        """Check if skill should level up."""
        thresholds = {
            SkillLevel.NOVICE: 0,
            SkillLevel.BEGINNER: 100,
            SkillLevel.INTERMEDIATE: 500,
            SkillLevel.ADVANCED: 2000,
            SkillLevel.EXPERT: 10000,
            SkillLevel.MASTER: 50000
        }

        levels = list(thresholds.keys())
        for i, level in enumerate(levels):
            threshold = thresholds[level]
            if self.experience_points >= threshold:
                self.level = level


@dataclass
class LearningExample:
    """A single learning example."""
    id: str
    input_data: Dict[str, Any]
    output_data: Dict[str, Any]
    context: Dict[str, Any]
    skill_id: Optional[str] = None
    feedback: Optional[FeedbackType] = None
    quality_score: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class LearningSession:
    """A learning session with multiple examples."""
    id: str
    mode: LearningMode
    skill_id: str
    examples: List[LearningExample] = field(default_factory=list)
    metrics: Dict[str, float] = field(default_factory=dict)
    started_at: datetime = field(default_factory=datetime.now)
    ended_at: Optional[datetime] = None


@dataclass
class AdaptationRule:
    """A rule for adapting behavior."""
    id: str
    trigger_condition: str
    action: str
    priority: int = 0
    success_count: int = 0
    failure_count: int = 0
    enabled: bool = True


# =============================================================================
# SKILL MANAGER
# =============================================================================

class SkillManager:
    """Manages learned skills and their evolution."""

    def __init__(self, storage_path: Optional[Path] = None):
        self.skills: Dict[str, Skill] = {}
        self.skill_graph: Dict[str, Set[str]] = {}  # Prerequisites
        self.storage_path = storage_path or Path("data/skills")
        self.storage_path.mkdir(parents=True, exist_ok=True)

    async def create_skill(
        self,
        name: str,
        domain: str,
        prerequisites: Optional[List[str]] = None
    ) -> Skill:
        """Create a new skill."""
        skill_id = hashlib.md5(f"{domain}:{name}".encode()).hexdigest()[:12]

        skill = Skill(
            id=skill_id,
            name=name,
            domain=domain,
            related_skills=prerequisites or []
        )

        self.skills[skill_id] = skill

        if prerequisites:
            self.skill_graph[skill_id] = set(prerequisites)

        await self._save_skill(skill)
        logger.info(f"Created skill: {name} ({skill_id})")

        return skill

    async def get_skill(self, skill_id: str) -> Optional[Skill]:
        """Get a skill by ID."""
        if skill_id in self.skills:
            return self.skills[skill_id]

        # Try to load from storage
        skill = await self._load_skill(skill_id)
        if skill:
            self.skills[skill_id] = skill

        return skill

    async def practice_skill(
        self,
        skill_id: str,
        success: bool,
        xp_gain: int = 10
    ) -> None:
        """Record skill practice."""
        skill = await self.get_skill(skill_id)
        if not skill:
            return

        skill.practice_count += 1
        skill.last_used = datetime.now()

        if success:
            skill.success_count += 1
            skill.add_experience(xp_gain)
        else:
            skill.failure_count += 1
            skill.add_experience(xp_gain // 2)  # Learn from failures too

        await self._save_skill(skill)

    async def learn_pattern(
        self,
        skill_id: str,
        pattern: Dict[str, Any]
    ) -> None:
        """Add a learned pattern to a skill."""
        skill = await self.get_skill(skill_id)
        if not skill:
            return

        # Check for duplicate patterns
        pattern_hash = hashlib.md5(
            json.dumps(pattern, sort_keys=True).encode()
        ).hexdigest()

        existing_hashes = {
            hashlib.md5(json.dumps(p, sort_keys=True).encode()).hexdigest()
            for p in skill.patterns
        }

        if pattern_hash not in existing_hashes:
            skill.patterns.append(pattern)
            await self._save_skill(skill)
            logger.debug(f"Learned pattern for skill {skill.name}")

    async def get_skills_by_domain(self, domain: str) -> List[Skill]:
        """Get all skills in a domain."""
        return [s for s in self.skills.values() if s.domain == domain]

    async def get_applicable_skills(
        self,
        task_type: str,
        context: Dict[str, Any]
    ) -> List[Skill]:
        """Find skills applicable to a task."""
        applicable = []

        for skill in self.skills.values():
            # Check if skill domain matches task
            if skill.domain.lower() in task_type.lower():
                applicable.append(skill)
            # Check if skill name matches
            elif skill.name.lower() in task_type.lower():
                applicable.append(skill)

        # Sort by level and success rate
        applicable.sort(
            key=lambda s: (s.level.value, s.success_rate),
            reverse=True
        )

        return applicable

    async def _save_skill(self, skill: Skill) -> None:
        """Save skill to storage."""
        filepath = self.storage_path / f"{skill.id}.json"
        with open(filepath, 'w') as f:
            json.dump({
                "id": skill.id,
                "name": skill.name,
                "domain": skill.domain,
                "level": skill.level.value,
                "experience_points": skill.experience_points,
                "practice_count": skill.practice_count,
                "success_count": skill.success_count,
                "failure_count": skill.failure_count,
                "patterns": skill.patterns,
                "strategies": skill.strategies,
                "related_skills": skill.related_skills,
                "created_at": skill.created_at.isoformat(),
                "last_used": skill.last_used.isoformat()
            }, f, indent=2)

    async def _load_skill(self, skill_id: str) -> Optional[Skill]:
        """Load skill from storage."""
        filepath = self.storage_path / f"{skill_id}.json"

        if not filepath.exists():
            return None

        with open(filepath, 'r') as f:
            data = json.load(f)

        return Skill(
            id=data["id"],
            name=data["name"],
            domain=data["domain"],
            level=SkillLevel(data["level"]),
            experience_points=data["experience_points"],
            practice_count=data["practice_count"],
            success_count=data["success_count"],
            failure_count=data["failure_count"],
            patterns=data["patterns"],
            strategies=data["strategies"],
            related_skills=data["related_skills"],
            created_at=datetime.fromisoformat(data["created_at"]),
            last_used=datetime.fromisoformat(data["last_used"])
        )


# =============================================================================
# FEEDBACK PROCESSOR
# =============================================================================

class FeedbackProcessor:
    """Processes and learns from feedback."""

    def __init__(self):
        self.feedback_history: List[Dict[str, Any]] = []
        self.feedback_patterns: Dict[str, List[Dict[str, Any]]] = {}
        self.improvement_suggestions: List[str] = []

    async def process_feedback(
        self,
        interaction_id: str,
        feedback_type: FeedbackType,
        details: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process feedback from an interaction."""
        feedback_record = {
            "id": hashlib.md5(interaction_id.encode()).hexdigest()[:12],
            "interaction_id": interaction_id,
            "type": feedback_type.value,
            "details": details,
            "context": context,
            "timestamp": datetime.now().isoformat()
        }

        self.feedback_history.append(feedback_record)

        # Analyze feedback
        analysis = await self._analyze_feedback(feedback_record)

        # Generate improvements if negative feedback
        if feedback_type == FeedbackType.NEGATIVE:
            improvements = await self._generate_improvements(
                feedback_record,
                analysis
            )
            self.improvement_suggestions.extend(improvements)

        return {
            "feedback_id": feedback_record["id"],
            "analysis": analysis,
            "improvements": self.improvement_suggestions[-5:] if self.improvement_suggestions else []
        }

    async def _analyze_feedback(
        self,
        feedback: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze feedback to extract patterns."""
        analysis = {
            "sentiment": feedback["type"],
            "categories": [],
            "patterns": []
        }

        # Extract categories from details
        details = feedback.get("details", {})
        if "category" in details:
            analysis["categories"].append(details["category"])

        # Look for patterns in context
        context = feedback.get("context", {})
        if "task_type" in context:
            task_type = context["task_type"]

            # Track feedback by task type
            if task_type not in self.feedback_patterns:
                self.feedback_patterns[task_type] = []
            self.feedback_patterns[task_type].append(feedback)

            # Check if there's a pattern of negative feedback
            recent = self.feedback_patterns[task_type][-10:]
            negative_count = sum(
                1 for f in recent
                if f["type"] == FeedbackType.NEGATIVE.value
            )

            if negative_count >= 3:
                analysis["patterns"].append({
                    "type": "repeated_failure",
                    "task_type": task_type,
                    "negative_ratio": negative_count / len(recent)
                })

        return analysis

    async def _generate_improvements(
        self,
        feedback: Dict[str, Any],
        analysis: Dict[str, Any]
    ) -> List[str]:
        """Generate improvement suggestions from feedback."""
        improvements = []

        details = feedback.get("details", {})

        if "error_type" in details:
            error_type = details["error_type"]
            improvements.append(
                f"Improve handling of {error_type} errors"
            )

        if "missing_info" in details:
            improvements.append(
                f"Gather more information about: {details['missing_info']}"
            )

        for pattern in analysis.get("patterns", []):
            if pattern["type"] == "repeated_failure":
                improvements.append(
                    f"Review and improve strategy for {pattern['task_type']} tasks"
                )

        return improvements


# =============================================================================
# EXPERIENCE REPLAY BUFFER
# =============================================================================

class ExperienceReplayBuffer:
    """Buffer for storing and replaying learning experiences."""

    def __init__(self, capacity: int = 10000):
        self.capacity = capacity
        self.buffer: List[LearningExample] = []
        self.priorities: List[float] = []
        self.position = 0

    def add(
        self,
        example: LearningExample,
        priority: float = 1.0
    ) -> None:
        """Add an experience to the buffer."""
        if len(self.buffer) < self.capacity:
            self.buffer.append(example)
            self.priorities.append(priority)
        else:
            self.buffer[self.position] = example
            self.priorities[self.position] = priority

        self.position = (self.position + 1) % self.capacity

    def sample(
        self,
        batch_size: int,
        prioritized: bool = True
    ) -> List[LearningExample]:
        """Sample experiences from the buffer."""
        if len(self.buffer) < batch_size:
            return list(self.buffer)

        if prioritized:
            # Prioritized sampling
            import random
            total_priority = sum(self.priorities)
            probs = [p / total_priority for p in self.priorities]
            indices = random.choices(
                range(len(self.buffer)),
                weights=probs,
                k=batch_size
            )
            return [self.buffer[i] for i in indices]
        else:
            # Uniform sampling
            import random
            return random.sample(self.buffer, batch_size)

    def get_recent(self, n: int) -> List[LearningExample]:
        """Get the n most recent experiences."""
        return list(reversed(self.buffer[-n:]))

    def update_priority(self, index: int, priority: float) -> None:
        """Update the priority of an experience."""
        if 0 <= index < len(self.priorities):
            self.priorities[index] = priority

    def clear(self) -> None:
        """Clear the buffer."""
        self.buffer.clear()
        self.priorities.clear()
        self.position = 0


# =============================================================================
# BEHAVIOR ADAPTER
# =============================================================================

class BehaviorAdapter:
    """Adapts agent behavior based on learning."""

    def __init__(self):
        self.adaptation_rules: Dict[str, AdaptationRule] = {}
        self.behavior_modifiers: Dict[str, float] = {}
        self.context_preferences: Dict[str, Dict[str, Any]] = {}

    async def add_rule(
        self,
        trigger: str,
        action: str,
        priority: int = 0
    ) -> AdaptationRule:
        """Add an adaptation rule."""
        rule_id = hashlib.md5(f"{trigger}:{action}".encode()).hexdigest()[:12]

        rule = AdaptationRule(
            id=rule_id,
            trigger_condition=trigger,
            action=action,
            priority=priority
        )

        self.adaptation_rules[rule_id] = rule
        return rule

    async def evaluate_rules(
        self,
        context: Dict[str, Any]
    ) -> List[AdaptationRule]:
        """Evaluate which rules should fire for given context."""
        matching_rules = []

        for rule in self.adaptation_rules.values():
            if not rule.enabled:
                continue

            if await self._matches_trigger(rule.trigger_condition, context):
                matching_rules.append(rule)

        # Sort by priority
        matching_rules.sort(key=lambda r: r.priority, reverse=True)

        return matching_rules

    async def _matches_trigger(
        self,
        trigger: str,
        context: Dict[str, Any]
    ) -> bool:
        """Check if a trigger condition matches the context."""
        # Simple keyword matching for now
        trigger_lower = trigger.lower()

        for key, value in context.items():
            if isinstance(value, str):
                if trigger_lower in value.lower():
                    return True
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, str) and trigger_lower in item.lower():
                        return True

        return False

    async def apply_adaptations(
        self,
        base_behavior: Dict[str, Any],
        rules: List[AdaptationRule]
    ) -> Dict[str, Any]:
        """Apply adaptation rules to behavior."""
        adapted = base_behavior.copy()

        for rule in rules:
            # Parse and apply action
            action_parts = rule.action.split(":")
            if len(action_parts) >= 2:
                action_type = action_parts[0]
                action_value = ":".join(action_parts[1:])

                if action_type == "set":
                    # set:key=value
                    key_val = action_value.split("=")
                    if len(key_val) == 2:
                        adapted[key_val[0]] = key_val[1]

                elif action_type == "increase":
                    # increase:key=amount
                    key_val = action_value.split("=")
                    if len(key_val) == 2:
                        key, amount = key_val[0], float(key_val[1])
                        if key in adapted and isinstance(adapted[key], (int, float)):
                            adapted[key] += amount

                elif action_type == "add":
                    # add:key=item
                    key_val = action_value.split("=")
                    if len(key_val) == 2:
                        key, item = key_val
                        if key in adapted and isinstance(adapted[key], list):
                            adapted[key].append(item)

        return adapted

    async def learn_preference(
        self,
        context_key: str,
        preference: Dict[str, Any]
    ) -> None:
        """Learn a preference for a context."""
        if context_key not in self.context_preferences:
            self.context_preferences[context_key] = {}

        self.context_preferences[context_key].update(preference)

    async def get_preferences(
        self,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Get learned preferences for a context."""
        preferences = {}

        for key, prefs in self.context_preferences.items():
            if key in str(context):
                preferences.update(prefs)

        return preferences


# =============================================================================
# LEARNING ENGINE
# =============================================================================

class LearningEngine:
    """Central learning and adaptation engine."""

    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path or Path("data/learning")
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.skill_manager = SkillManager(self.storage_path / "skills")
        self.feedback_processor = FeedbackProcessor()
        self.experience_buffer = ExperienceReplayBuffer()
        self.behavior_adapter = BehaviorAdapter()

        self.active_sessions: Dict[str, LearningSession] = {}
        self.learning_metrics: Dict[str, List[float]] = {}

    async def start_learning_session(
        self,
        mode: LearningMode,
        skill_name: str,
        skill_domain: str
    ) -> LearningSession:
        """Start a new learning session."""
        # Get or create skill
        skills = await self.skill_manager.get_skills_by_domain(skill_domain)
        skill = next(
            (s for s in skills if s.name == skill_name),
            None
        )

        if not skill:
            skill = await self.skill_manager.create_skill(skill_name, skill_domain)

        session = LearningSession(
            id=hashlib.md5(f"{skill.id}:{datetime.now().isoformat()}".encode()).hexdigest()[:12],
            mode=mode,
            skill_id=skill.id
        )

        self.active_sessions[session.id] = session
        logger.info(f"Started learning session: {session.id} for skill {skill_name}")

        return session

    async def add_learning_example(
        self,
        session_id: str,
        input_data: Dict[str, Any],
        output_data: Dict[str, Any],
        context: Dict[str, Any],
        quality_score: float = 1.0
    ) -> LearningExample:
        """Add a learning example to a session."""
        session = self.active_sessions.get(session_id)
        if not session:
            raise ValueError(f"Unknown session: {session_id}")

        example = LearningExample(
            id=hashlib.md5(f"{session_id}:{len(session.examples)}".encode()).hexdigest()[:12],
            input_data=input_data,
            output_data=output_data,
            context=context,
            skill_id=session.skill_id,
            quality_score=quality_score
        )

        session.examples.append(example)

        # Also add to experience buffer
        self.experience_buffer.add(example, priority=quality_score)

        return example

    async def provide_feedback(
        self,
        example_id: str,
        feedback_type: FeedbackType,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Provide feedback for a learning example."""
        # Find example in buffer
        for example in self.experience_buffer.buffer:
            if example.id == example_id:
                example.feedback = feedback_type

                # Adjust priority based on feedback
                if feedback_type == FeedbackType.POSITIVE:
                    example.quality_score *= 1.2
                elif feedback_type == FeedbackType.NEGATIVE:
                    example.quality_score *= 0.8
                elif feedback_type == FeedbackType.CORRECTIVE:
                    example.quality_score *= 1.5  # Corrections are valuable

                # Update skill
                if example.skill_id:
                    await self.skill_manager.practice_skill(
                        example.skill_id,
                        success=(feedback_type == FeedbackType.POSITIVE)
                    )

                break

    async def end_learning_session(
        self,
        session_id: str
    ) -> Dict[str, Any]:
        """End a learning session and consolidate learning."""
        session = self.active_sessions.get(session_id)
        if not session:
            return {"error": "Unknown session"}

        session.ended_at = datetime.now()

        # Calculate session metrics
        total_examples = len(session.examples)
        positive_count = sum(
            1 for e in session.examples
            if e.feedback == FeedbackType.POSITIVE
        )

        session.metrics = {
            "total_examples": total_examples,
            "positive_feedback_rate": positive_count / total_examples if total_examples > 0 else 0,
            "average_quality": sum(e.quality_score for e in session.examples) / total_examples if total_examples > 0 else 0,
            "duration_seconds": (session.ended_at - session.started_at).total_seconds()
        }

        # Extract patterns from examples
        patterns = await self._extract_patterns(session.examples)

        # Update skill with patterns
        skill = await self.skill_manager.get_skill(session.skill_id)
        if skill:
            for pattern in patterns:
                await self.skill_manager.learn_pattern(session.skill_id, pattern)

        # Clean up
        del self.active_sessions[session_id]

        logger.info(f"Ended learning session: {session_id}, metrics: {session.metrics}")

        return {
            "session_id": session_id,
            "metrics": session.metrics,
            "patterns_learned": len(patterns)
        }

    async def _extract_patterns(
        self,
        examples: List[LearningExample]
    ) -> List[Dict[str, Any]]:
        """Extract patterns from learning examples."""
        patterns = []

        # Group examples by input similarity
        input_groups: Dict[str, List[LearningExample]] = {}

        for example in examples:
            # Create a simplified key from input
            input_key = json.dumps(
                {k: type(v).__name__ for k, v in example.input_data.items()},
                sort_keys=True
            )

            if input_key not in input_groups:
                input_groups[input_key] = []
            input_groups[input_key].append(example)

        # Analyze each group
        for input_key, group in input_groups.items():
            if len(group) >= 2:
                # Find successful patterns
                successful = [
                    e for e in group
                    if e.feedback == FeedbackType.POSITIVE
                ]

                if successful:
                    # Extract common output patterns
                    output_keys = set()
                    for e in successful:
                        output_keys.update(e.output_data.keys())

                    pattern = {
                        "input_type": input_key,
                        "output_structure": list(output_keys),
                        "example_count": len(group),
                        "success_rate": len(successful) / len(group)
                    }
                    patterns.append(pattern)

        return patterns

    async def learn_from_interaction(
        self,
        interaction: Dict[str, Any],
        feedback: FeedbackType,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Learn from a single interaction."""
        # Process feedback
        feedback_result = await self.feedback_processor.process_feedback(
            interaction.get("id", "unknown"),
            feedback,
            interaction,
            context
        )

        # Create learning example
        example = LearningExample(
            id=hashlib.md5(str(interaction).encode()).hexdigest()[:12],
            input_data=interaction.get("input", {}),
            output_data=interaction.get("output", {}),
            context=context,
            feedback=feedback,
            quality_score=1.0 if feedback == FeedbackType.POSITIVE else 0.5
        )

        self.experience_buffer.add(example, priority=example.quality_score)

        # Check for adaptation opportunities
        if feedback == FeedbackType.NEGATIVE:
            # Add adaptation rule if pattern detected
            patterns = feedback_result.get("analysis", {}).get("patterns", [])
            for pattern in patterns:
                if pattern.get("type") == "repeated_failure":
                    await self.behavior_adapter.add_rule(
                        trigger=pattern.get("task_type", "unknown"),
                        action=f"set:approach=alternative",
                        priority=5
                    )

        return {
            "learned": True,
            "example_id": example.id,
            "feedback_analysis": feedback_result.get("analysis"),
            "improvements": feedback_result.get("improvements", [])
        }

    async def get_adapted_behavior(
        self,
        base_behavior: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Get adapted behavior based on learned rules."""
        # Get matching rules
        rules = await self.behavior_adapter.evaluate_rules(context)

        # Apply adaptations
        adapted = await self.behavior_adapter.apply_adaptations(
            base_behavior,
            rules
        )

        # Apply learned preferences
        preferences = await self.behavior_adapter.get_preferences(context)
        adapted.update(preferences)

        return adapted

    async def replay_experiences(
        self,
        batch_size: int = 32
    ) -> List[Dict[str, Any]]:
        """Replay experiences for reinforcement learning."""
        examples = self.experience_buffer.sample(batch_size, prioritized=True)

        replay_results = []

        for example in examples:
            # Simulate re-learning from example
            result = {
                "example_id": example.id,
                "input_data": example.input_data,
                "output_data": example.output_data,
                "feedback": example.feedback.value if example.feedback else None,
                "quality_score": example.quality_score
            }
            replay_results.append(result)

        return replay_results

    async def get_learning_stats(self) -> Dict[str, Any]:
        """Get learning statistics."""
        total_skills = len(self.skill_manager.skills)
        total_experiences = len(self.experience_buffer.buffer)
        total_rules = len(self.behavior_adapter.adaptation_rules)

        skill_levels = {}
        for skill in self.skill_manager.skills.values():
            level = skill.level.value
            skill_levels[level] = skill_levels.get(level, 0) + 1

        return {
            "total_skills": total_skills,
            "skill_levels": skill_levels,
            "total_experiences": total_experiences,
            "total_adaptation_rules": total_rules,
            "active_sessions": len(self.active_sessions),
            "feedback_history_size": len(self.feedback_processor.feedback_history),
            "improvement_suggestions": self.feedback_processor.improvement_suggestions[-10:]
        }


# =============================================================================
# META-LEARNING
# =============================================================================

class MetaLearner:
    """Learns how to learn more effectively."""

    def __init__(self, learning_engine: LearningEngine):
        self.engine = learning_engine
        self.learning_strategies: Dict[str, Dict[str, Any]] = {}
        self.strategy_performance: Dict[str, List[float]] = {}

    async def evaluate_learning_strategies(
        self,
        task_type: str
    ) -> str:
        """Evaluate and select best learning strategy for task type."""
        if task_type not in self.strategy_performance:
            # Return default strategy
            return "standard"

        performances = self.strategy_performance[task_type]
        strategies = list(self.learning_strategies.keys())

        if not strategies:
            return "standard"

        # Find best performing strategy
        best_strategy = max(
            strategies,
            key=lambda s: sum(self.strategy_performance.get(s, [0])) / max(len(self.strategy_performance.get(s, [1])), 1)
        )

        return best_strategy

    async def record_strategy_performance(
        self,
        strategy: str,
        task_type: str,
        performance_score: float
    ) -> None:
        """Record performance of a learning strategy."""
        key = f"{strategy}:{task_type}"

        if key not in self.strategy_performance:
            self.strategy_performance[key] = []

        self.strategy_performance[key].append(performance_score)

        # Keep only recent history
        if len(self.strategy_performance[key]) > 100:
            self.strategy_performance[key] = self.strategy_performance[key][-100:]

    async def suggest_learning_approach(
        self,
        skill: Skill,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Suggest a learning approach based on meta-learning."""
        approach = {
            "mode": LearningMode.SUPERVISED,
            "batch_size": 32,
            "replay_frequency": 10,
            "exploration_rate": 0.1
        }

        # Adjust based on skill level
        if skill.level in [SkillLevel.NOVICE, SkillLevel.BEGINNER]:
            approach["mode"] = LearningMode.IMITATION
            approach["exploration_rate"] = 0.05
        elif skill.level in [SkillLevel.INTERMEDIATE]:
            approach["mode"] = LearningMode.SUPERVISED
            approach["exploration_rate"] = 0.1
        elif skill.level in [SkillLevel.ADVANCED, SkillLevel.EXPERT]:
            approach["mode"] = LearningMode.REINFORCEMENT
            approach["exploration_rate"] = 0.2
        elif skill.level == SkillLevel.MASTER:
            approach["mode"] = LearningMode.SELF_SUPERVISED
            approach["exploration_rate"] = 0.3

        # Adjust based on success rate
        if skill.success_rate < 0.5:
            approach["batch_size"] = 64  # More examples needed
            approach["replay_frequency"] = 5  # More frequent replay

        return approach


# =============================================================================
# USAGE EXAMPLE
# =============================================================================

async def example_learning():
    """Demonstrate learning capabilities."""
    engine = LearningEngine()

    # Start a learning session
    session = await engine.start_learning_session(
        mode=LearningMode.SUPERVISED,
        skill_name="Python Coding",
        skill_domain="programming"
    )

    # Add learning examples
    await engine.add_learning_example(
        session.id,
        input_data={"task": "Write a function to sum numbers"},
        output_data={"code": "def sum_numbers(nums): return sum(nums)"},
        context={"language": "python"},
        quality_score=1.0
    )

    # Provide feedback
    # await engine.provide_feedback(example.id, FeedbackType.POSITIVE)

    # End session
    result = await engine.end_learning_session(session.id)
    print(f"Learning session result: {result}")

    # Get stats
    stats = await engine.get_learning_stats()
    print(f"Learning stats: {stats}")


if __name__ == "__main__":
    asyncio.run(example_learning())

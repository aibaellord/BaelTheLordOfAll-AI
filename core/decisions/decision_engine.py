#!/usr/bin/env python3
"""
BAEL - Decision Engine
Advanced decision-making engine for AI agent operations.

Features:
- Rule-based decisions
- Decision trees
- Scoring models
- Multi-criteria decisions
- Decision caching
- Decision auditing
- Probability-based decisions
- Conflict resolution
"""

import asyncio
import copy
import hashlib
import json
import random
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import (Any, Awaitable, Callable, Dict, Generic, Iterator, List,
                    Optional, Set, Tuple, Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class DecisionType(Enum):
    """Decision types."""
    RULE_BASED = "rule_based"
    TREE = "tree"
    SCORING = "scoring"
    PROBABILISTIC = "probabilistic"
    WEIGHTED = "weighted"
    UNANIMOUS = "unanimous"
    MAJORITY = "majority"


class RuleOperator(Enum):
    """Rule comparison operators."""
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    GREATER_OR_EQUAL = "greater_or_equal"
    LESS_OR_EQUAL = "less_or_equal"
    CONTAINS = "contains"
    IN = "in"
    REGEX = "regex"
    EXISTS = "exists"


class DecisionStatus(Enum):
    """Decision status."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    DEFERRED = "deferred"


class ConflictStrategy(Enum):
    """Conflict resolution strategies."""
    FIRST_MATCH = "first_match"
    LAST_MATCH = "last_match"
    HIGHEST_PRIORITY = "highest_priority"
    HIGHEST_CONFIDENCE = "highest_confidence"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class Condition:
    """Rule condition."""
    field: str
    operator: RuleOperator
    value: Any
    negate: bool = False


@dataclass
class Rule:
    """Decision rule."""
    rule_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    conditions: List[Condition] = field(default_factory=list)
    action: Any = None
    priority: int = 0
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DecisionNode:
    """Decision tree node."""
    node_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    condition: Optional[Condition] = None
    true_branch: Optional[str] = None  # node_id
    false_branch: Optional[str] = None  # node_id
    action: Any = None
    is_leaf: bool = False


@dataclass
class ScoringCriterion:
    """Scoring criterion."""
    name: str
    weight: float = 1.0
    scorer: Optional[Callable[[Dict[str, Any]], float]] = None
    min_score: float = 0.0
    max_score: float = 1.0


@dataclass
class DecisionOption:
    """Decision option."""
    option_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    scores: Dict[str, float] = field(default_factory=dict)
    total_score: float = 0.0
    probability: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DecisionResult:
    """Decision result."""
    decision_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    decision_type: DecisionType = DecisionType.RULE_BASED
    action: Any = None
    confidence: float = 1.0
    alternatives: List[Any] = field(default_factory=list)
    explanation: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AuditRecord:
    """Decision audit record."""
    record_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    decision_id: str = ""
    input_data: Dict[str, Any] = field(default_factory=dict)
    result: Any = None
    rules_matched: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    duration: float = 0.0


# =============================================================================
# CONDITION EVALUATOR
# =============================================================================

class ConditionEvaluator:
    """Evaluate conditions."""

    def evaluate(
        self,
        condition: Condition,
        data: Dict[str, Any]
    ) -> bool:
        """Evaluate condition against data."""
        value = self._get_value(condition.field, data)
        result = self._compare(condition.operator, value, condition.value)

        return not result if condition.negate else result

    def _get_value(self, field: str, data: Dict[str, Any]) -> Any:
        """Get nested field value."""
        parts = field.split(".")
        value = data

        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return None

        return value

    def _compare(
        self,
        operator: RuleOperator,
        actual: Any,
        expected: Any
    ) -> bool:
        """Compare values."""
        if operator == RuleOperator.EQUALS:
            return actual == expected

        elif operator == RuleOperator.NOT_EQUALS:
            return actual != expected

        elif operator == RuleOperator.GREATER_THAN:
            return actual is not None and actual > expected

        elif operator == RuleOperator.LESS_THAN:
            return actual is not None and actual < expected

        elif operator == RuleOperator.GREATER_OR_EQUAL:
            return actual is not None and actual >= expected

        elif operator == RuleOperator.LESS_OR_EQUAL:
            return actual is not None and actual <= expected

        elif operator == RuleOperator.CONTAINS:
            if isinstance(actual, str):
                return expected in actual
            elif isinstance(actual, (list, tuple)):
                return expected in actual
            return False

        elif operator == RuleOperator.IN:
            return actual in expected

        elif operator == RuleOperator.REGEX:
            import re
            if isinstance(actual, str):
                return bool(re.match(expected, actual))
            return False

        elif operator == RuleOperator.EXISTS:
            return actual is not None

        return False


# =============================================================================
# RULE ENGINE
# =============================================================================

class RuleEngine:
    """Rule-based decision engine."""

    def __init__(
        self,
        conflict_strategy: ConflictStrategy = ConflictStrategy.FIRST_MATCH
    ):
        self._rules: Dict[str, Rule] = {}
        self._evaluator = ConditionEvaluator()
        self._conflict_strategy = conflict_strategy

    def add_rule(self, rule: Rule) -> str:
        """Add rule."""
        self._rules[rule.rule_id] = rule
        return rule.rule_id

    def remove_rule(self, rule_id: str) -> bool:
        """Remove rule."""
        if rule_id in self._rules:
            del self._rules[rule_id]
            return True
        return False

    def evaluate(self, data: Dict[str, Any]) -> List[Rule]:
        """Find all matching rules."""
        matches = []

        for rule in self._rules.values():
            if not rule.enabled:
                continue

            if self._matches(rule, data):
                matches.append(rule)

        return matches

    def decide(self, data: Dict[str, Any]) -> Optional[Any]:
        """Make decision based on rules."""
        matches = self.evaluate(data)

        if not matches:
            return None

        if self._conflict_strategy == ConflictStrategy.FIRST_MATCH:
            return matches[0].action

        elif self._conflict_strategy == ConflictStrategy.LAST_MATCH:
            return matches[-1].action

        elif self._conflict_strategy == ConflictStrategy.HIGHEST_PRIORITY:
            sorted_matches = sorted(matches, key=lambda r: r.priority, reverse=True)
            return sorted_matches[0].action

        return matches[0].action

    def _matches(self, rule: Rule, data: Dict[str, Any]) -> bool:
        """Check if rule matches data."""
        for condition in rule.conditions:
            if not self._evaluator.evaluate(condition, data):
                return False
        return True


# =============================================================================
# DECISION TREE
# =============================================================================

class DecisionTree:
    """Decision tree engine."""

    def __init__(self, name: str = ""):
        self.name = name
        self._nodes: Dict[str, DecisionNode] = {}
        self._root: Optional[str] = None
        self._evaluator = ConditionEvaluator()

    def add_node(
        self,
        node_id: str,
        condition: Optional[Condition] = None,
        action: Any = None,
        is_root: bool = False
    ) -> DecisionNode:
        """Add node."""
        node = DecisionNode(
            node_id=node_id,
            condition=condition,
            action=action,
            is_leaf=action is not None
        )

        self._nodes[node_id] = node

        if is_root:
            self._root = node_id

        return node

    def set_branches(
        self,
        node_id: str,
        true_branch: Optional[str] = None,
        false_branch: Optional[str] = None
    ) -> None:
        """Set node branches."""
        node = self._nodes.get(node_id)
        if node:
            node.true_branch = true_branch
            node.false_branch = false_branch

    def decide(self, data: Dict[str, Any]) -> Optional[Any]:
        """Traverse tree and make decision."""
        if not self._root:
            return None

        current = self._nodes.get(self._root)
        path = []

        while current:
            path.append(current.node_id)

            if current.is_leaf:
                return current.action

            if current.condition:
                result = self._evaluator.evaluate(current.condition, data)
                next_id = current.true_branch if result else current.false_branch
            else:
                next_id = current.true_branch

            current = self._nodes.get(next_id) if next_id else None

        return None

    def get_path(self, data: Dict[str, Any]) -> List[str]:
        """Get decision path."""
        if not self._root:
            return []

        path = []
        current = self._nodes.get(self._root)

        while current:
            path.append(current.node_id)

            if current.is_leaf:
                break

            if current.condition:
                result = self._evaluator.evaluate(current.condition, data)
                next_id = current.true_branch if result else current.false_branch
            else:
                next_id = current.true_branch

            current = self._nodes.get(next_id) if next_id else None

        return path


# =============================================================================
# SCORING ENGINE
# =============================================================================

class ScoringEngine:
    """Multi-criteria scoring engine."""

    def __init__(self):
        self._criteria: Dict[str, ScoringCriterion] = {}

    def add_criterion(
        self,
        name: str,
        weight: float = 1.0,
        scorer: Optional[Callable[[Dict[str, Any]], float]] = None
    ) -> None:
        """Add scoring criterion."""
        criterion = ScoringCriterion(
            name=name,
            weight=weight,
            scorer=scorer
        )
        self._criteria[name] = criterion

    def score_option(
        self,
        option: DecisionOption,
        data: Dict[str, Any]
    ) -> float:
        """Score a single option."""
        total_score = 0.0
        total_weight = 0.0

        for name, criterion in self._criteria.items():
            weight = criterion.weight

            if criterion.scorer:
                score = criterion.scorer(data)
            else:
                score = option.scores.get(name, 0.0)

            # Normalize score
            score = max(criterion.min_score, min(criterion.max_score, score))
            normalized = (score - criterion.min_score) / (criterion.max_score - criterion.min_score)

            total_score += normalized * weight
            total_weight += weight

        if total_weight > 0:
            option.total_score = total_score / total_weight

        return option.total_score

    def rank_options(
        self,
        options: List[DecisionOption],
        data: Dict[str, Any]
    ) -> List[DecisionOption]:
        """Rank options by score."""
        for option in options:
            self.score_option(option, data)

        return sorted(options, key=lambda o: o.total_score, reverse=True)

    def decide(
        self,
        options: List[DecisionOption],
        data: Dict[str, Any]
    ) -> Optional[DecisionOption]:
        """Select best option."""
        ranked = self.rank_options(options, data)
        return ranked[0] if ranked else None


# =============================================================================
# PROBABILISTIC ENGINE
# =============================================================================

class ProbabilisticEngine:
    """Probability-based decision engine."""

    def __init__(self, seed: Optional[int] = None):
        self._rng = random.Random(seed)

    def decide(
        self,
        options: List[DecisionOption]
    ) -> Optional[DecisionOption]:
        """Select option based on probabilities."""
        if not options:
            return None

        # Normalize probabilities
        total_prob = sum(o.probability for o in options)
        if total_prob == 0:
            # Equal probability
            return self._rng.choice(options)

        normalized = [(o, o.probability / total_prob) for o in options]

        # Weighted random selection
        r = self._rng.random()
        cumulative = 0.0

        for option, prob in normalized:
            cumulative += prob
            if r <= cumulative:
                return option

        return options[-1]

    def sample(
        self,
        options: List[DecisionOption],
        n: int = 1
    ) -> List[DecisionOption]:
        """Sample multiple options."""
        results = []
        for _ in range(n):
            result = self.decide(options)
            if result:
                results.append(result)
        return results


# =============================================================================
# VOTING ENGINE
# =============================================================================

class VotingEngine:
    """Voting-based decision engine."""

    def __init__(self, strategy: DecisionType = DecisionType.MAJORITY):
        self._strategy = strategy
        self._voters: List[Callable[[Dict[str, Any]], Any]] = []

    def add_voter(
        self,
        voter: Callable[[Dict[str, Any]], Any]
    ) -> None:
        """Add voter."""
        self._voters.append(voter)

    def decide(self, data: Dict[str, Any]) -> Optional[Any]:
        """Make decision by voting."""
        if not self._voters:
            return None

        votes: Dict[Any, int] = defaultdict(int)

        for voter in self._voters:
            vote = voter(data)
            if vote is not None:
                votes[str(vote)] = votes[str(vote)] + 1

        if not votes:
            return None

        if self._strategy == DecisionType.UNANIMOUS:
            if len(votes) == 1:
                return list(votes.keys())[0]
            return None

        elif self._strategy == DecisionType.MAJORITY:
            threshold = len(self._voters) // 2 + 1
            for vote, count in votes.items():
                if count >= threshold:
                    return vote
            return None

        else:
            # Plurality
            return max(votes.items(), key=lambda x: x[1])[0]


# =============================================================================
# DECISION CACHE
# =============================================================================

class DecisionCache:
    """Cache decisions."""

    def __init__(self, ttl_seconds: int = 3600):
        self._cache: Dict[str, Tuple[Any, datetime]] = {}
        self._ttl = timedelta(seconds=ttl_seconds)

    def _make_key(self, data: Dict[str, Any]) -> str:
        """Make cache key."""
        return hashlib.md5(
            json.dumps(data, sort_keys=True, default=str).encode()
        ).hexdigest()

    def get(self, data: Dict[str, Any]) -> Optional[Any]:
        """Get cached decision."""
        key = self._make_key(data)

        if key in self._cache:
            result, expires = self._cache[key]
            if datetime.now() < expires:
                return result
            del self._cache[key]

        return None

    def set(self, data: Dict[str, Any], result: Any) -> None:
        """Cache decision."""
        key = self._make_key(data)
        expires = datetime.now() + self._ttl
        self._cache[key] = (result, expires)

    def clear(self) -> int:
        """Clear cache."""
        count = len(self._cache)
        self._cache.clear()
        return count


# =============================================================================
# DECISION AUDITOR
# =============================================================================

class DecisionAuditor:
    """Audit decisions."""

    def __init__(self, max_records: int = 10000):
        self._records: List[AuditRecord] = []
        self._max_records = max_records

    def record(
        self,
        decision_id: str,
        input_data: Dict[str, Any],
        result: Any,
        rules_matched: List[str],
        duration: float
    ) -> AuditRecord:
        """Record decision."""
        record = AuditRecord(
            decision_id=decision_id,
            input_data=copy.deepcopy(input_data),
            result=result,
            rules_matched=rules_matched,
            duration=duration
        )

        self._records.append(record)

        # Trim old records
        if len(self._records) > self._max_records:
            self._records = self._records[-self._max_records:]

        return record

    def get_records(
        self,
        limit: int = 100,
        since: Optional[datetime] = None
    ) -> List[AuditRecord]:
        """Get audit records."""
        records = self._records

        if since:
            records = [r for r in records if r.timestamp >= since]

        return records[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        """Get audit statistics."""
        if not self._records:
            return {}

        durations = [r.duration for r in self._records]
        results = [str(r.result) for r in self._records]

        result_counts = defaultdict(int)
        for r in results:
            result_counts[r] += 1

        return {
            "total_decisions": len(self._records),
            "avg_duration": sum(durations) / len(durations),
            "max_duration": max(durations),
            "result_distribution": dict(result_counts)
        }


# =============================================================================
# DECISION ENGINE
# =============================================================================

class DecisionEngine:
    """
    Decision Engine for BAEL.

    Advanced decision-making for AI agents.
    """

    def __init__(self):
        self._rule_engine = RuleEngine()
        self._trees: Dict[str, DecisionTree] = {}
        self._scoring_engine = ScoringEngine()
        self._probabilistic_engine = ProbabilisticEngine()
        self._voting_engine = VotingEngine()
        self._cache = DecisionCache()
        self._auditor = DecisionAuditor()

    # -------------------------------------------------------------------------
    # RULE-BASED
    # -------------------------------------------------------------------------

    def add_rule(
        self,
        name: str,
        conditions: List[Tuple[str, str, Any]],
        action: Any,
        priority: int = 0
    ) -> str:
        """Add decision rule."""
        condition_list = []

        for field, operator_str, value in conditions:
            operator = RuleOperator[operator_str.upper()]
            condition_list.append(Condition(
                field=field,
                operator=operator,
                value=value
            ))

        rule = Rule(
            name=name,
            conditions=condition_list,
            action=action,
            priority=priority
        )

        return self._rule_engine.add_rule(rule)

    def decide_by_rules(
        self,
        data: Dict[str, Any],
        use_cache: bool = True
    ) -> DecisionResult:
        """Make decision using rules."""
        start_time = time.time()

        # Check cache
        if use_cache:
            cached = self._cache.get(data)
            if cached is not None:
                return DecisionResult(
                    decision_type=DecisionType.RULE_BASED,
                    action=cached,
                    explanation="Cached decision"
                )

        # Evaluate rules
        matches = self._rule_engine.evaluate(data)
        action = self._rule_engine.decide(data)

        duration = time.time() - start_time

        result = DecisionResult(
            decision_type=DecisionType.RULE_BASED,
            action=action,
            confidence=1.0 if action else 0.0,
            alternatives=[m.action for m in matches[1:]] if len(matches) > 1 else [],
            explanation=f"Matched {len(matches)} rules"
        )

        # Audit
        self._auditor.record(
            decision_id=result.decision_id,
            input_data=data,
            result=action,
            rules_matched=[m.rule_id for m in matches],
            duration=duration
        )

        # Cache
        if use_cache and action is not None:
            self._cache.set(data, action)

        return result

    # -------------------------------------------------------------------------
    # DECISION TREES
    # -------------------------------------------------------------------------

    def create_tree(self, name: str) -> DecisionTree:
        """Create decision tree."""
        tree = DecisionTree(name)
        self._trees[name] = tree
        return tree

    def get_tree(self, name: str) -> Optional[DecisionTree]:
        """Get decision tree."""
        return self._trees.get(name)

    def decide_by_tree(
        self,
        tree_name: str,
        data: Dict[str, Any]
    ) -> DecisionResult:
        """Make decision using tree."""
        start_time = time.time()

        tree = self._trees.get(tree_name)
        if not tree:
            return DecisionResult(
                decision_type=DecisionType.TREE,
                action=None,
                explanation=f"Tree not found: {tree_name}"
            )

        action = tree.decide(data)
        path = tree.get_path(data)
        duration = time.time() - start_time

        result = DecisionResult(
            decision_type=DecisionType.TREE,
            action=action,
            confidence=1.0 if action else 0.0,
            explanation=f"Path: {' -> '.join(path)}",
            metadata={"path": path}
        )

        self._auditor.record(
            decision_id=result.decision_id,
            input_data=data,
            result=action,
            rules_matched=path,
            duration=duration
        )

        return result

    # -------------------------------------------------------------------------
    # SCORING
    # -------------------------------------------------------------------------

    def add_criterion(
        self,
        name: str,
        weight: float = 1.0,
        scorer: Optional[Callable[[Dict[str, Any]], float]] = None
    ) -> None:
        """Add scoring criterion."""
        self._scoring_engine.add_criterion(name, weight, scorer)

    def decide_by_score(
        self,
        options: List[Dict[str, Any]],
        data: Dict[str, Any]
    ) -> DecisionResult:
        """Make decision by scoring."""
        start_time = time.time()

        decision_options = []
        for opt in options:
            decision_options.append(DecisionOption(
                name=opt.get("name", ""),
                scores=opt.get("scores", {}),
                metadata=opt
            ))

        best = self._scoring_engine.decide(decision_options, data)
        ranked = self._scoring_engine.rank_options(decision_options, data)

        duration = time.time() - start_time

        return DecisionResult(
            decision_type=DecisionType.SCORING,
            action=best.metadata if best else None,
            confidence=best.total_score if best else 0.0,
            alternatives=[o.metadata for o in ranked[1:3]] if len(ranked) > 1 else [],
            explanation=f"Best score: {best.total_score:.2f}" if best else "No options",
            metadata={"scores": {o.name: o.total_score for o in ranked}}
        )

    # -------------------------------------------------------------------------
    # PROBABILISTIC
    # -------------------------------------------------------------------------

    def decide_by_probability(
        self,
        options: List[Dict[str, Any]]
    ) -> DecisionResult:
        """Make probabilistic decision."""
        decision_options = []

        for opt in options:
            decision_options.append(DecisionOption(
                name=opt.get("name", ""),
                probability=opt.get("probability", 0.0),
                metadata=opt
            ))

        selected = self._probabilistic_engine.decide(decision_options)

        return DecisionResult(
            decision_type=DecisionType.PROBABILISTIC,
            action=selected.metadata if selected else None,
            confidence=selected.probability if selected else 0.0,
            explanation=f"Selected: {selected.name}" if selected else "No selection"
        )

    # -------------------------------------------------------------------------
    # VOTING
    # -------------------------------------------------------------------------

    def add_voter(
        self,
        voter: Callable[[Dict[str, Any]], Any]
    ) -> None:
        """Add voter."""
        self._voting_engine.add_voter(voter)

    def decide_by_vote(
        self,
        data: Dict[str, Any]
    ) -> DecisionResult:
        """Make decision by voting."""
        result = self._voting_engine.decide(data)

        return DecisionResult(
            decision_type=DecisionType.MAJORITY,
            action=result,
            explanation="Majority vote"
        )

    # -------------------------------------------------------------------------
    # UTILITIES
    # -------------------------------------------------------------------------

    def get_audit_records(
        self,
        limit: int = 100
    ) -> List[AuditRecord]:
        """Get audit records."""
        return self._auditor.get_records(limit)

    def get_audit_stats(self) -> Dict[str, Any]:
        """Get audit statistics."""
        return self._auditor.get_stats()

    def clear_cache(self) -> int:
        """Clear decision cache."""
        return self._cache.clear()


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Decision Engine."""
    print("=" * 70)
    print("BAEL - DECISION ENGINE DEMO")
    print("Advanced Decision-Making for AI Agents")
    print("=" * 70)
    print()

    engine = DecisionEngine()

    # 1. Rule-Based Decisions
    print("1. RULE-BASED DECISIONS:")
    print("-" * 40)

    engine.add_rule(
        name="high_risk",
        conditions=[
            ("risk_score", "greater_than", 0.8),
            ("amount", "greater_than", 10000)
        ],
        action="reject",
        priority=10
    )

    engine.add_rule(
        name="low_risk",
        conditions=[
            ("risk_score", "less_than", 0.3),
        ],
        action="approve",
        priority=5
    )

    engine.add_rule(
        name="medium_risk",
        conditions=[
            ("risk_score", "greater_or_equal", 0.3),
            ("risk_score", "less_or_equal", 0.8)
        ],
        action="review",
        priority=1
    )

    # Test cases
    test_cases = [
        {"risk_score": 0.1, "amount": 5000},
        {"risk_score": 0.5, "amount": 8000},
        {"risk_score": 0.9, "amount": 15000}
    ]

    for data in test_cases:
        result = engine.decide_by_rules(data)
        print(f"   {data} -> {result.action}")
    print()

    # 2. Decision Trees
    print("2. DECISION TREES:")
    print("-" * 40)

    tree = engine.create_tree("loan_approval")

    # Build tree
    tree.add_node("income_check", condition=Condition(
        field="income",
        operator=RuleOperator.GREATER_THAN,
        value=50000
    ), is_root=True)

    tree.add_node("credit_check", condition=Condition(
        field="credit_score",
        operator=RuleOperator.GREATER_THAN,
        value=700
    ))

    tree.add_node("approve", action="approved", is_root=False)
    tree.add_node("deny", action="denied", is_root=False)
    tree.add_node("manual_review", action="review", is_root=False)

    tree.set_branches("income_check", "credit_check", "deny")
    tree.set_branches("credit_check", "approve", "manual_review")

    test_data = {"income": 60000, "credit_score": 750}
    result = engine.decide_by_tree("loan_approval", test_data)

    print(f"   Data: {test_data}")
    print(f"   Decision: {result.action}")
    print(f"   Path: {result.metadata.get('path')}")
    print()

    # 3. Scoring Decisions
    print("3. SCORING DECISIONS:")
    print("-" * 40)

    engine.add_criterion("cost", weight=0.4)
    engine.add_criterion("quality", weight=0.3)
    engine.add_criterion("speed", weight=0.3)

    options = [
        {"name": "Option A", "scores": {"cost": 0.8, "quality": 0.6, "speed": 0.7}},
        {"name": "Option B", "scores": {"cost": 0.5, "quality": 0.9, "speed": 0.4}},
        {"name": "Option C", "scores": {"cost": 0.6, "quality": 0.7, "speed": 0.8}}
    ]

    result = engine.decide_by_score(options, {})

    print(f"   Options scored:")
    for name, score in result.metadata.get("scores", {}).items():
        print(f"     {name}: {score:.2f}")
    print(f"   Best: {result.action.get('name')}")
    print()

    # 4. Probabilistic Decisions
    print("4. PROBABILISTIC DECISIONS:")
    print("-" * 40)

    options = [
        {"name": "A", "probability": 0.5},
        {"name": "B", "probability": 0.3},
        {"name": "C", "probability": 0.2}
    ]

    selections = defaultdict(int)
    for _ in range(100):
        result = engine.decide_by_probability(options)
        if result.action:
            selections[result.action["name"]] += 1

    print(f"   100 samples:")
    for name, count in sorted(selections.items()):
        print(f"     {name}: {count}%")
    print()

    # 5. Voting Decisions
    print("5. VOTING DECISIONS:")
    print("-" * 40)

    engine.add_voter(lambda d: "yes" if d.get("score", 0) > 0.5 else "no")
    engine.add_voter(lambda d: "yes" if d.get("quality", 0) > 0.6 else "no")
    engine.add_voter(lambda d: "yes" if d.get("cost", 0) < 0.4 else "no")

    data = {"score": 0.7, "quality": 0.8, "cost": 0.3}
    result = engine.decide_by_vote(data)

    print(f"   Data: {data}")
    print(f"   Vote result: {result.action}")
    print()

    # 6. Decision with Caching
    print("6. DECISION CACHING:")
    print("-" * 40)

    data = {"risk_score": 0.2, "amount": 1000}

    # First call
    start = time.time()
    result1 = engine.decide_by_rules(data)
    time1 = time.time() - start

    # Second call (cached)
    start = time.time()
    result2 = engine.decide_by_rules(data)
    time2 = time.time() - start

    print(f"   First call: {time1:.6f}s")
    print(f"   Cached call: {time2:.6f}s")
    print(f"   Both returned: {result1.action}")
    print()

    # 7. Audit Records
    print("7. AUDIT RECORDS:")
    print("-" * 40)

    records = engine.get_audit_records(limit=5)
    print(f"   Recent decisions: {len(records)}")
    for record in records[:3]:
        print(f"     {record.result} ({record.duration:.4f}s)")
    print()

    # 8. Audit Statistics
    print("8. AUDIT STATISTICS:")
    print("-" * 40)

    stats = engine.get_audit_stats()
    print(f"   Total decisions: {stats.get('total_decisions', 0)}")
    print(f"   Avg duration: {stats.get('avg_duration', 0):.4f}s")
    print(f"   Result distribution: {stats.get('result_distribution', {})}")
    print()

    # 9. Complex Conditions
    print("9. COMPLEX CONDITIONS:")
    print("-" * 40)

    engine.add_rule(
        name="vip_user",
        conditions=[
            ("user.type", "equals", "vip"),
            ("user.purchases", "greater_than", 10)
        ],
        action="priority_support",
        priority=100
    )

    data = {"user": {"type": "vip", "purchases": 15}}
    result = engine.decide_by_rules(data, use_cache=False)

    print(f"   Nested data: {data}")
    print(f"   Decision: {result.action}")
    print()

    # 10. Contains Operator
    print("10. CONTAINS OPERATOR:")
    print("-" * 40)

    engine.add_rule(
        name="premium_product",
        conditions=[
            ("tags", "contains", "premium")
        ],
        action="apply_discount",
        priority=5
    )

    data = {"tags": ["electronics", "premium", "new"]}
    result = engine.decide_by_rules(data, use_cache=False)

    print(f"   Tags: {data['tags']}")
    print(f"   Decision: {result.action}")
    print()

    # 11. IN Operator
    print("11. IN OPERATOR:")
    print("-" * 40)

    engine.add_rule(
        name="valid_status",
        conditions=[
            ("status", "in", ["active", "pending"])
        ],
        action="process",
        priority=5
    )

    data = {"status": "active"}
    result = engine.decide_by_rules(data, use_cache=False)

    print(f"   Status: {data['status']}")
    print(f"   Decision: {result.action}")
    print()

    # 12. Clear Cache
    print("12. CACHE MANAGEMENT:")
    print("-" * 40)

    cleared = engine.clear_cache()
    print(f"   Cleared {cleared} cached decisions")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Decision Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())

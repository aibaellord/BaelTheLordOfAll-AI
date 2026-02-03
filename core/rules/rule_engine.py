#!/usr/bin/env python3
"""
BAEL - Rule Engine
Comprehensive business rule evaluation system.

This module provides a complete rule engine for
defining and executing business rules and policies.

Features:
- Rule definition and management
- Condition evaluation
- Action execution
- Rule chaining
- Priority-based execution
- Conflict resolution
- Rule groups
- Inference engine
- Decision tables
- Audit trail
"""

import asyncio
import json
import logging
import operator
import re
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import (Any, Awaitable, Callable, Dict, Generic, List, Optional,
                    Set, Tuple, Type, TypeVar, Union)

logger = logging.getLogger(__name__)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class RuleStatus(Enum):
    """Rule status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    DRAFT = "draft"
    DEPRECATED = "deprecated"


class ConditionOperator(Enum):
    """Condition operators."""
    EQUALS = "eq"
    NOT_EQUALS = "neq"
    GREATER_THAN = "gt"
    GREATER_EQUAL = "gte"
    LESS_THAN = "lt"
    LESS_EQUAL = "lte"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    IN = "in"
    NOT_IN = "not_in"
    MATCHES = "matches"
    IS_NULL = "is_null"
    IS_NOT_NULL = "is_not_null"
    BETWEEN = "between"


class LogicalOperator(Enum):
    """Logical operators."""
    AND = "and"
    OR = "or"
    NOT = "not"


class ActionType(Enum):
    """Action types."""
    SET_VALUE = "set_value"
    EXECUTE = "execute"
    TRIGGER = "trigger"
    LOG = "log"
    STOP = "stop"


class ConflictResolution(Enum):
    """Conflict resolution strategies."""
    FIRST = "first"
    LAST = "last"
    PRIORITY = "priority"
    ALL = "all"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class RuleContext:
    """Context for rule evaluation."""
    facts: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    results: Dict[str, Any] = field(default_factory=dict)
    fired_rules: List[str] = field(default_factory=list)

    def get_fact(self, key: str, default: Any = None) -> Any:
        """Get a fact value using dot notation."""
        keys = key.split('.')
        value = self.facts

        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            elif hasattr(value, k):
                value = getattr(value, k)
            else:
                return default

            if value is None:
                return default

        return value

    def set_fact(self, key: str, value: Any) -> None:
        """Set a fact value using dot notation."""
        keys = key.split('.')
        target = self.facts

        for k in keys[:-1]:
            if k not in target:
                target[k] = {}
            target = target[k]

        target[keys[-1]] = value

    def set_result(self, key: str, value: Any) -> None:
        """Set a result value."""
        self.results[key] = value


@dataclass
class RuleResult:
    """Result of rule evaluation."""
    rule_id: str
    matched: bool
    executed: bool = False
    output: Any = None
    error: Optional[str] = None
    duration_ms: float = 0


@dataclass
class EvaluationResult:
    """Result of rule engine evaluation."""
    success: bool
    rules_evaluated: int = 0
    rules_matched: int = 0
    rules_executed: int = 0
    results: Dict[str, Any] = field(default_factory=dict)
    rule_results: List[RuleResult] = field(default_factory=list)
    duration_ms: float = 0


@dataclass
class RuleAuditEntry:
    """Audit entry for rule execution."""
    rule_id: str
    timestamp: float = field(default_factory=time.time)
    matched: bool = False
    executed: bool = False
    facts: Dict[str, Any] = field(default_factory=dict)
    results: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# CONDITIONS
# =============================================================================

class Condition(ABC):
    """Abstract condition."""

    @abstractmethod
    def evaluate(self, context: RuleContext) -> bool:
        pass

    def __and__(self, other: 'Condition') -> 'CompositeCondition':
        return CompositeCondition(LogicalOperator.AND, [self, other])

    def __or__(self, other: 'Condition') -> 'CompositeCondition':
        return CompositeCondition(LogicalOperator.OR, [self, other])

    def __invert__(self) -> 'CompositeCondition':
        return CompositeCondition(LogicalOperator.NOT, [self])


class SimpleCondition(Condition):
    """Simple comparison condition."""

    OPERATORS = {
        ConditionOperator.EQUALS: operator.eq,
        ConditionOperator.NOT_EQUALS: operator.ne,
        ConditionOperator.GREATER_THAN: operator.gt,
        ConditionOperator.GREATER_EQUAL: operator.ge,
        ConditionOperator.LESS_THAN: operator.lt,
        ConditionOperator.LESS_EQUAL: operator.le,
    }

    def __init__(
        self,
        field: str,
        op: ConditionOperator,
        value: Any = None
    ):
        self.field = field
        self.operator = op
        self.value = value

    def evaluate(self, context: RuleContext) -> bool:
        fact_value = context.get_fact(self.field)

        if self.operator == ConditionOperator.IS_NULL:
            return fact_value is None

        if self.operator == ConditionOperator.IS_NOT_NULL:
            return fact_value is not None

        if fact_value is None:
            return False

        if self.operator in self.OPERATORS:
            return self.OPERATORS[self.operator](fact_value, self.value)

        if self.operator == ConditionOperator.CONTAINS:
            return self.value in fact_value

        if self.operator == ConditionOperator.NOT_CONTAINS:
            return self.value not in fact_value

        if self.operator == ConditionOperator.STARTS_WITH:
            return str(fact_value).startswith(str(self.value))

        if self.operator == ConditionOperator.ENDS_WITH:
            return str(fact_value).endswith(str(self.value))

        if self.operator == ConditionOperator.IN:
            return fact_value in self.value

        if self.operator == ConditionOperator.NOT_IN:
            return fact_value not in self.value

        if self.operator == ConditionOperator.MATCHES:
            return bool(re.match(self.value, str(fact_value)))

        if self.operator == ConditionOperator.BETWEEN:
            return self.value[0] <= fact_value <= self.value[1]

        return False


class CompositeCondition(Condition):
    """Composite condition with logical operators."""

    def __init__(
        self,
        op: LogicalOperator,
        conditions: List[Condition]
    ):
        self.operator = op
        self.conditions = conditions

    def evaluate(self, context: RuleContext) -> bool:
        if self.operator == LogicalOperator.AND:
            return all(c.evaluate(context) for c in self.conditions)

        if self.operator == LogicalOperator.OR:
            return any(c.evaluate(context) for c in self.conditions)

        if self.operator == LogicalOperator.NOT:
            return not self.conditions[0].evaluate(context)

        return False


class FunctionCondition(Condition):
    """Function-based condition."""

    def __init__(self, func: Callable[[RuleContext], bool]):
        self.func = func

    def evaluate(self, context: RuleContext) -> bool:
        try:
            if asyncio.iscoroutinefunction(self.func):
                loop = asyncio.get_event_loop()
                return loop.run_until_complete(self.func(context))
            return self.func(context)
        except:
            return False


class TrueCondition(Condition):
    """Always true condition."""

    def evaluate(self, context: RuleContext) -> bool:
        return True


class FalseCondition(Condition):
    """Always false condition."""

    def evaluate(self, context: RuleContext) -> bool:
        return False


# =============================================================================
# ACTIONS
# =============================================================================

class Action(ABC):
    """Abstract action."""

    @abstractmethod
    async def execute(self, context: RuleContext) -> Any:
        pass


class SetValueAction(Action):
    """Set a value in context."""

    def __init__(self, key: str, value: Any):
        self.key = key
        self.value = value

    async def execute(self, context: RuleContext) -> Any:
        # Handle callable values
        if callable(self.value):
            value = self.value(context)
        else:
            value = self.value

        if '.' in self.key:
            context.set_fact(self.key, value)
        else:
            context.set_result(self.key, value)

        return value


class ExecuteAction(Action):
    """Execute a function."""

    def __init__(self, func: Callable[[RuleContext], Any]):
        self.func = func

    async def execute(self, context: RuleContext) -> Any:
        if asyncio.iscoroutinefunction(self.func):
            return await self.func(context)
        return self.func(context)


class LogAction(Action):
    """Log a message."""

    def __init__(self, message: str, level: str = "info"):
        self.message = message
        self.level = level

    async def execute(self, context: RuleContext) -> Any:
        log_func = getattr(logger, self.level, logger.info)
        log_func(self.message.format(**context.facts))
        return None


class TriggerAction(Action):
    """Trigger another rule or event."""

    def __init__(self, rule_id: str):
        self.rule_id = rule_id

    async def execute(self, context: RuleContext) -> Any:
        context.metadata["trigger"] = self.rule_id
        return self.rule_id


class CompositeAction(Action):
    """Execute multiple actions."""

    def __init__(self, actions: List[Action]):
        self.actions = actions

    async def execute(self, context: RuleContext) -> Any:
        results = []
        for action in self.actions:
            result = await action.execute(context)
            results.append(result)
        return results


# =============================================================================
# RULE
# =============================================================================

class Rule:
    """
    A business rule with conditions and actions.
    """

    def __init__(
        self,
        rule_id: str,
        name: str = "",
        description: str = ""
    ):
        self.rule_id = rule_id
        self.name = name or rule_id
        self.description = description

        # Status
        self.status = RuleStatus.ACTIVE

        # Priority (higher = more important)
        self.priority = 0

        # Conditions
        self.condition: Optional[Condition] = None

        # Actions
        self.actions: List[Action] = []

        # Metadata
        self.tags: Set[str] = set()
        self.metadata: Dict[str, Any] = {}

        # Timestamps
        self.created_at = time.time()
        self.modified_at = time.time()

    def when(self, condition: Condition) -> 'Rule':
        """Set the condition."""
        self.condition = condition
        return self

    def then(self, action: Action) -> 'Rule':
        """Add an action."""
        self.actions.append(action)
        return self

    def set_value(self, key: str, value: Any) -> 'Rule':
        """Add set value action."""
        return self.then(SetValueAction(key, value))

    def execute(self, func: Callable[[RuleContext], Any]) -> 'Rule':
        """Add execute action."""
        return self.then(ExecuteAction(func))

    def log(self, message: str, level: str = "info") -> 'Rule':
        """Add log action."""
        return self.then(LogAction(message, level))

    def matches(self, context: RuleContext) -> bool:
        """Check if rule matches context."""
        if self.status != RuleStatus.ACTIVE:
            return False

        if not self.condition:
            return True

        return self.condition.evaluate(context)

    async def fire(self, context: RuleContext) -> RuleResult:
        """Execute the rule actions."""
        start_time = time.time()

        try:
            outputs = []
            for action in self.actions:
                output = await action.execute(context)
                outputs.append(output)

            context.fired_rules.append(self.rule_id)

            return RuleResult(
                rule_id=self.rule_id,
                matched=True,
                executed=True,
                output=outputs if len(outputs) > 1 else (outputs[0] if outputs else None),
                duration_ms=(time.time() - start_time) * 1000
            )
        except Exception as e:
            return RuleResult(
                rule_id=self.rule_id,
                matched=True,
                executed=False,
                error=str(e),
                duration_ms=(time.time() - start_time) * 1000
            )


# =============================================================================
# RULE GROUP
# =============================================================================

class RuleGroup:
    """
    A group of related rules.
    """

    def __init__(
        self,
        group_id: str,
        name: str = "",
        conflict_resolution: ConflictResolution = ConflictResolution.ALL
    ):
        self.group_id = group_id
        self.name = name or group_id
        self.conflict_resolution = conflict_resolution

        self.rules: Dict[str, Rule] = {}
        self.enabled = True

    def add_rule(self, rule: Rule) -> None:
        """Add a rule to the group."""
        self.rules[rule.rule_id] = rule

    def remove_rule(self, rule_id: str) -> bool:
        """Remove a rule from the group."""
        if rule_id in self.rules:
            del self.rules[rule_id]
            return True
        return False

    def get_matching_rules(self, context: RuleContext) -> List[Rule]:
        """Get all matching rules."""
        if not self.enabled:
            return []

        matching = [
            rule for rule in self.rules.values()
            if rule.matches(context)
        ]

        # Sort by priority (highest first)
        matching.sort(key=lambda r: r.priority, reverse=True)

        return matching

    async def evaluate(self, context: RuleContext) -> List[RuleResult]:
        """Evaluate all rules in the group."""
        matching = self.get_matching_rules(context)
        results = []

        if not matching:
            return results

        if self.conflict_resolution == ConflictResolution.FIRST:
            result = await matching[0].fire(context)
            results.append(result)

        elif self.conflict_resolution == ConflictResolution.LAST:
            result = await matching[-1].fire(context)
            results.append(result)

        elif self.conflict_resolution == ConflictResolution.PRIORITY:
            result = await matching[0].fire(context)
            results.append(result)

        else:  # ALL
            for rule in matching:
                result = await rule.fire(context)
                results.append(result)

        return results


# =============================================================================
# DECISION TABLE
# =============================================================================

@dataclass
class DecisionRow:
    """A row in a decision table."""
    conditions: Dict[str, Any]
    actions: Dict[str, Any]
    priority: int = 0


class DecisionTable:
    """
    Decision table for tabular rule representation.
    """

    def __init__(self, table_id: str, name: str = ""):
        self.table_id = table_id
        self.name = name or table_id

        self.input_columns: List[str] = []
        self.output_columns: List[str] = []
        self.rows: List[DecisionRow] = []

    def add_input_column(self, name: str) -> 'DecisionTable':
        """Add input column."""
        self.input_columns.append(name)
        return self

    def add_output_column(self, name: str) -> 'DecisionTable':
        """Add output column."""
        self.output_columns.append(name)
        return self

    def add_row(
        self,
        conditions: Dict[str, Any],
        actions: Dict[str, Any],
        priority: int = 0
    ) -> 'DecisionTable':
        """Add a decision row."""
        self.rows.append(DecisionRow(conditions, actions, priority))
        return self

    def evaluate(self, context: RuleContext) -> Optional[Dict[str, Any]]:
        """Evaluate the decision table."""
        # Sort by priority
        sorted_rows = sorted(self.rows, key=lambda r: r.priority, reverse=True)

        for row in sorted_rows:
            if self._matches_row(row, context):
                return row.actions

        return None

    def _matches_row(self, row: DecisionRow, context: RuleContext) -> bool:
        """Check if a row matches the context."""
        for column, expected in row.conditions.items():
            actual = context.get_fact(column)

            if expected == "*":  # Wildcard
                continue

            if callable(expected):
                if not expected(actual):
                    return False
            elif actual != expected:
                return False

        return True

    def to_rules(self) -> List[Rule]:
        """Convert decision table to rules."""
        rules = []

        for i, row in enumerate(self.rows):
            rule = Rule(f"{self.table_id}_row_{i}", f"{self.name} Row {i}")
            rule.priority = row.priority

            # Build condition
            conditions = []
            for column, expected in row.conditions.items():
                if expected == "*":
                    continue
                conditions.append(
                    SimpleCondition(column, ConditionOperator.EQUALS, expected)
                )

            if conditions:
                if len(conditions) == 1:
                    rule.when(conditions[0])
                else:
                    rule.when(CompositeCondition(LogicalOperator.AND, conditions))

            # Add actions
            for column, value in row.actions.items():
                rule.set_value(column, value)

            rules.append(rule)

        return rules


# =============================================================================
# RULE ENGINE
# =============================================================================

class RuleEngine:
    """
    Core rule engine for evaluating business rules.
    """

    def __init__(self):
        # Rules
        self.rules: Dict[str, Rule] = {}
        self.groups: Dict[str, RuleGroup] = {}
        self.decision_tables: Dict[str, DecisionTable] = {}

        # Audit
        self.audit_log: deque = deque(maxlen=10000)
        self.audit_enabled = True

        # Statistics
        self.evaluations = 0
        self.rules_fired = 0

    def add_rule(self, rule: Rule) -> None:
        """Add a rule."""
        self.rules[rule.rule_id] = rule

    def remove_rule(self, rule_id: str) -> bool:
        """Remove a rule."""
        if rule_id in self.rules:
            del self.rules[rule_id]
            return True
        return False

    def get_rule(self, rule_id: str) -> Optional[Rule]:
        """Get a rule by ID."""
        return self.rules.get(rule_id)

    def add_group(self, group: RuleGroup) -> None:
        """Add a rule group."""
        self.groups[group.group_id] = group

    def add_decision_table(self, table: DecisionTable) -> None:
        """Add a decision table."""
        self.decision_tables[table.table_id] = table

    def create_context(
        self,
        facts: Dict[str, Any] = None,
        metadata: Dict[str, Any] = None
    ) -> RuleContext:
        """Create a rule context."""
        return RuleContext(
            facts=facts or {},
            metadata=metadata or {}
        )

    async def evaluate(
        self,
        context: RuleContext,
        rule_ids: List[str] = None,
        group_ids: List[str] = None
    ) -> EvaluationResult:
        """Evaluate rules against context."""
        start_time = time.time()
        self.evaluations += 1

        rules_to_evaluate = []

        # Collect rules
        if rule_ids:
            rules_to_evaluate.extend([
                self.rules[rid] for rid in rule_ids
                if rid in self.rules
            ])
        elif group_ids:
            for gid in group_ids:
                group = self.groups.get(gid)
                if group:
                    rules_to_evaluate.extend(group.rules.values())
        else:
            rules_to_evaluate.extend(self.rules.values())

        # Sort by priority
        rules_to_evaluate.sort(key=lambda r: r.priority, reverse=True)

        # Evaluate
        results: List[RuleResult] = []
        matched_count = 0
        executed_count = 0

        for rule in rules_to_evaluate:
            if rule.matches(context):
                matched_count += 1
                result = await rule.fire(context)
                results.append(result)

                if result.executed:
                    executed_count += 1
                    self.rules_fired += 1

                # Audit
                if self.audit_enabled:
                    self.audit_log.append(RuleAuditEntry(
                        rule_id=rule.rule_id,
                        matched=True,
                        executed=result.executed,
                        facts=context.facts.copy(),
                        results=context.results.copy()
                    ))

        return EvaluationResult(
            success=True,
            rules_evaluated=len(rules_to_evaluate),
            rules_matched=matched_count,
            rules_executed=executed_count,
            results=context.results,
            rule_results=results,
            duration_ms=(time.time() - start_time) * 1000
        )

    async def evaluate_group(
        self,
        group_id: str,
        context: RuleContext
    ) -> List[RuleResult]:
        """Evaluate a specific group."""
        group = self.groups.get(group_id)
        if not group:
            return []

        return await group.evaluate(context)

    def evaluate_decision_table(
        self,
        table_id: str,
        context: RuleContext
    ) -> Optional[Dict[str, Any]]:
        """Evaluate a decision table."""
        table = self.decision_tables.get(table_id)
        if not table:
            return None

        result = table.evaluate(context)

        if result:
            context.results.update(result)

        return result

    def get_audit_log(
        self,
        rule_id: str = None,
        limit: int = 100
    ) -> List[RuleAuditEntry]:
        """Get audit log entries."""
        entries = list(self.audit_log)

        if rule_id:
            entries = [e for e in entries if e.rule_id == rule_id]

        return entries[-limit:]

    def get_statistics(self) -> Dict[str, Any]:
        """Get engine statistics."""
        return {
            "rules": len(self.rules),
            "groups": len(self.groups),
            "decision_tables": len(self.decision_tables),
            "evaluations": self.evaluations,
            "rules_fired": self.rules_fired,
            "audit_entries": len(self.audit_log)
        }


# =============================================================================
# RULE BUILDER
# =============================================================================

class RuleBuilder:
    """
    Fluent builder for rules.
    """

    def __init__(self, rule_id: str, name: str = ""):
        self.rule = Rule(rule_id, name)

    def description(self, desc: str) -> 'RuleBuilder':
        """Set description."""
        self.rule.description = desc
        return self

    def priority(self, priority: int) -> 'RuleBuilder':
        """Set priority."""
        self.rule.priority = priority
        return self

    def tag(self, tag: str) -> 'RuleBuilder':
        """Add tag."""
        self.rule.tags.add(tag)
        return self

    def when(self, condition: Condition) -> 'RuleBuilder':
        """Set condition."""
        self.rule.condition = condition
        return self

    def when_field(
        self,
        field: str,
        op: ConditionOperator,
        value: Any = None
    ) -> 'RuleBuilder':
        """Set simple condition."""
        self.rule.condition = SimpleCondition(field, op, value)
        return self

    def when_equals(self, field: str, value: Any) -> 'RuleBuilder':
        """Set equals condition."""
        return self.when_field(field, ConditionOperator.EQUALS, value)

    def when_greater(self, field: str, value: Any) -> 'RuleBuilder':
        """Set greater than condition."""
        return self.when_field(field, ConditionOperator.GREATER_THAN, value)

    def when_function(
        self,
        func: Callable[[RuleContext], bool]
    ) -> 'RuleBuilder':
        """Set function condition."""
        self.rule.condition = FunctionCondition(func)
        return self

    def then_set(self, key: str, value: Any) -> 'RuleBuilder':
        """Add set value action."""
        self.rule.set_value(key, value)
        return self

    def then_execute(
        self,
        func: Callable[[RuleContext], Any]
    ) -> 'RuleBuilder':
        """Add execute action."""
        self.rule.execute(func)
        return self

    def then_log(self, message: str, level: str = "info") -> 'RuleBuilder':
        """Add log action."""
        self.rule.log(message, level)
        return self

    def build(self) -> Rule:
        """Build the rule."""
        return self.rule


# =============================================================================
# RULE ENGINE MANAGER
# =============================================================================

class RuleEngineManager:
    """
    Master rule engine manager for BAEL.

    Manages rule engines and provides unified access.
    """

    def __init__(self):
        self.engine = RuleEngine()

    def builder(self, rule_id: str, name: str = "") -> RuleBuilder:
        """Create rule builder."""
        return RuleBuilder(rule_id, name)

    def add_rule(self, rule: Rule) -> None:
        """Add a rule."""
        self.engine.add_rule(rule)

    def add_group(self, group: RuleGroup) -> None:
        """Add a rule group."""
        self.engine.add_group(group)

    def add_decision_table(self, table: DecisionTable) -> None:
        """Add a decision table."""
        self.engine.add_decision_table(table)

    def create_context(
        self,
        facts: Dict[str, Any] = None
    ) -> RuleContext:
        """Create rule context."""
        return self.engine.create_context(facts)

    async def evaluate(
        self,
        facts: Dict[str, Any],
        rule_ids: List[str] = None
    ) -> EvaluationResult:
        """Evaluate rules."""
        context = self.create_context(facts)
        return await self.engine.evaluate(context, rule_ids)

    async def evaluate_group(
        self,
        group_id: str,
        facts: Dict[str, Any]
    ) -> List[RuleResult]:
        """Evaluate a rule group."""
        context = self.create_context(facts)
        return await self.engine.evaluate_group(group_id, context)

    def evaluate_decision_table(
        self,
        table_id: str,
        facts: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Evaluate decision table."""
        context = self.create_context(facts)
        return self.engine.evaluate_decision_table(table_id, context)

    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics."""
        return self.engine.get_statistics()


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Rule Engine."""
    print("=" * 70)
    print("BAEL - RULE ENGINE DEMO")
    print("Business Rule Evaluation System")
    print("=" * 70)
    print()

    manager = RuleEngineManager()

    # 1. Simple Rule
    print("1. SIMPLE RULE:")
    print("-" * 40)

    discount_rule = (
        manager.builder("premium_discount", "Premium Discount")
        .description("Apply 20% discount for premium customers")
        .priority(10)
        .when_equals("customer.type", "premium")
        .then_set("discount", 0.20)
        .build()
    )

    manager.add_rule(discount_rule)

    result = await manager.evaluate({"customer": {"type": "premium", "name": "John"}})
    print(f"   Premium customer discount: {result.results.get('discount', 0):.0%}")

    result = await manager.evaluate({"customer": {"type": "regular", "name": "Jane"}})
    print(f"   Regular customer discount: {result.results.get('discount', 'None')}")
    print()

    # 2. Composite Conditions
    print("2. COMPOSITE CONDITIONS:")
    print("-" * 40)

    vip_rule = Rule("vip_bonus", "VIP Bonus")
    vip_rule.priority = 20

    # VIP = premium + high spending
    vip_condition = (
        SimpleCondition("customer.type", ConditionOperator.EQUALS, "premium") &
        SimpleCondition("customer.total_spent", ConditionOperator.GREATER_THAN, 1000)
    )

    vip_rule.when(vip_condition)
    vip_rule.set_value("bonus", 100)
    vip_rule.set_value("tier", "vip")

    manager.add_rule(vip_rule)

    result = await manager.evaluate({
        "customer": {"type": "premium", "total_spent": 1500}
    })
    print(f"   VIP bonus: ${result.results.get('bonus', 0)}")
    print(f"   Tier: {result.results.get('tier', 'None')}")
    print()

    # 3. Function Conditions
    print("3. FUNCTION CONDITIONS:")
    print("-" * 40)

    time_rule = (
        manager.builder("weekend_offer", "Weekend Offer")
        .when_function(lambda ctx: ctx.get_fact("day_of_week") in ["Saturday", "Sunday"])
        .then_set("offer", "weekend_special")
        .build()
    )

    manager.add_rule(time_rule)

    result = await manager.evaluate({"day_of_week": "Saturday"})
    print(f"   Saturday offer: {result.results.get('offer', 'None')}")

    result = await manager.evaluate({"day_of_week": "Monday"})
    print(f"   Monday offer: {result.results.get('offer', 'None')}")
    print()

    # 4. Rule Groups
    print("4. RULE GROUPS:")
    print("-" * 40)

    pricing_group = RuleGroup(
        "pricing",
        "Pricing Rules",
        ConflictResolution.PRIORITY
    )

    pricing_group.add_rule(
        manager.builder("bulk_price", "Bulk Pricing")
        .priority(5)
        .when_field("quantity", ConditionOperator.GREATER_THAN, 100)
        .then_set("price_per_unit", 8.0)
        .build()
    )

    pricing_group.add_rule(
        manager.builder("normal_price", "Normal Pricing")
        .priority(1)
        .when(TrueCondition())
        .then_set("price_per_unit", 10.0)
        .build()
    )

    manager.add_group(pricing_group)

    results = await manager.evaluate_group("pricing", {"quantity": 150})
    print(f"   Bulk order (150 units): ${results[0].output}/unit")

    results = await manager.evaluate_group("pricing", {"quantity": 50})
    print(f"   Normal order (50 units): ${results[0].output}/unit")
    print()

    # 5. Decision Tables
    print("5. DECISION TABLES:")
    print("-" * 40)

    shipping_table = (
        DecisionTable("shipping", "Shipping Rates")
        .add_input_column("weight")
        .add_input_column("destination")
        .add_output_column("rate")
        .add_output_column("carrier")
        .add_row(
            {"weight": lambda w: w <= 1, "destination": "domestic"},
            {"rate": 5.0, "carrier": "standard"},
            priority=1
        )
        .add_row(
            {"weight": lambda w: w <= 5, "destination": "domestic"},
            {"rate": 10.0, "carrier": "standard"},
            priority=1
        )
        .add_row(
            {"weight": "*", "destination": "international"},
            {"rate": 25.0, "carrier": "express"},
            priority=2
        )
    )

    manager.add_decision_table(shipping_table)

    result = manager.evaluate_decision_table("shipping", {
        "weight": 0.5, "destination": "domestic"
    })
    print(f"   0.5kg domestic: ${result['rate']} via {result['carrier']}")

    result = manager.evaluate_decision_table("shipping", {
        "weight": 3, "destination": "domestic"
    })
    print(f"   3kg domestic: ${result['rate']} via {result['carrier']}")

    result = manager.evaluate_decision_table("shipping", {
        "weight": 10, "destination": "international"
    })
    print(f"   10kg international: ${result['rate']} via {result['carrier']}")
    print()

    # 6. Execute Actions
    print("6. EXECUTE ACTIONS:")
    print("-" * 40)

    actions_log = []

    async def log_action(ctx):
        actions_log.append(f"Processed {ctx.get_fact('order.id')}")
        return "logged"

    logging_rule = (
        manager.builder("order_log", "Order Logging")
        .when_field("order.id", ConditionOperator.IS_NOT_NULL)
        .then_execute(log_action)
        .build()
    )

    manager.add_rule(logging_rule)

    await manager.evaluate({"order": {"id": "ORD-123"}})
    await manager.evaluate({"order": {"id": "ORD-456"}})

    print(f"   Actions executed:")
    for log in actions_log:
        print(f"     - {log}")
    print()

    # 7. Multiple Conditions
    print("7. MULTIPLE CONDITIONS:")
    print("-" * 40)

    complex_rule = Rule("complex", "Complex Rule")

    # (age >= 18 AND country IN ['US', 'CA']) OR verified == true
    age_country = (
        SimpleCondition("age", ConditionOperator.GREATER_EQUAL, 18) &
        SimpleCondition("country", ConditionOperator.IN, ["US", "CA"])
    )
    verified = SimpleCondition("verified", ConditionOperator.EQUALS, True)

    complex_rule.when(age_country | verified)
    complex_rule.set_value("eligible", True)

    manager.add_rule(complex_rule)

    result = await manager.evaluate({"age": 25, "country": "US", "verified": False})
    print(f"   25yo from US: eligible={result.results.get('eligible')}")

    result = await manager.evaluate({"age": 16, "country": "UK", "verified": True})
    print(f"   16yo from UK (verified): eligible={result.results.get('eligible')}")

    result = await manager.evaluate({"age": 16, "country": "UK", "verified": False})
    print(f"   16yo from UK (not verified): eligible={result.results.get('eligible', False)}")
    print()

    # 8. Dot Notation
    print("8. DOT NOTATION:")
    print("-" * 40)

    nested_rule = (
        manager.builder("nested", "Nested Access")
        .when_field("user.address.city", ConditionOperator.EQUALS, "New York")
        .then_set("user.discount", 0.15)
        .build()
    )

    manager.add_rule(nested_rule)

    context = manager.create_context({
        "user": {"name": "Alice", "address": {"city": "New York"}}
    })

    await manager.engine.evaluate(context)
    print(f"   NYC resident discount: {context.get_fact('user.discount'):.0%}")
    print()

    # 9. Audit Trail
    print("9. AUDIT TRAIL:")
    print("-" * 40)

    audit = manager.engine.get_audit_log(limit=5)
    print(f"   Recent rule executions:")
    for entry in audit[-3:]:
        status = "✓ fired" if entry.executed else "○ matched"
        print(f"     - {entry.rule_id}: {status}")
    print()

    # 10. Statistics
    print("10. ENGINE STATISTICS:")
    print("-" * 40)

    stats = manager.get_statistics()
    print(f"    Rules: {stats['rules']}")
    print(f"    Groups: {stats['groups']}")
    print(f"    Decision tables: {stats['decision_tables']}")
    print(f"    Evaluations: {stats['evaluations']}")
    print(f"    Rules fired: {stats['rules_fired']}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Rule Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())

#!/usr/bin/env python3
"""
BAEL - Rule Learner
Advanced inductive rule learning and discovery.

Features:
- Rule induction from examples
- Sequential covering
- Top-down rule learning
- Bottom-up generalization
- Rule pruning and refinement
- Concept learning
"""

import asyncio
import copy
import hashlib
import math
import random
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import (Any, Callable, Dict, Generic, List, Optional, Set, Tuple,
                    Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class LearningStrategy(Enum):
    """Rule learning strategies."""
    TOP_DOWN = "top_down"  # Start general, specialize
    BOTTOM_UP = "bottom_up"  # Start specific, generalize
    SEQUENTIAL_COVERING = "sequential_covering"
    FOIL = "foil"
    RIPPER = "ripper"


class ConditionType(Enum):
    """Types of conditions in rules."""
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    LESS_THAN = "less_than"
    GREATER_THAN = "greater_than"
    IN_RANGE = "in_range"
    IN_SET = "in_set"


class RuleQuality(Enum):
    """Quality levels for rules."""
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"


class ExampleClass(Enum):
    """Classification of examples."""
    POSITIVE = "positive"
    NEGATIVE = "negative"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class Attribute:
    """An attribute/feature."""
    attr_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    is_numeric: bool = False
    possible_values: List[Any] = field(default_factory=list)


@dataclass
class Example:
    """A training example."""
    example_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    features: Dict[str, Any] = field(default_factory=dict)
    label: str = ""
    weight: float = 1.0


@dataclass
class Condition:
    """A condition in a rule."""
    cond_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    attribute: str = ""
    condition_type: ConditionType = ConditionType.EQUALS
    value: Any = None
    value2: Any = None  # For range conditions

    def __str__(self):
        if self.condition_type == ConditionType.EQUALS:
            return f"{self.attribute} = {self.value}"
        elif self.condition_type == ConditionType.NOT_EQUALS:
            return f"{self.attribute} ≠ {self.value}"
        elif self.condition_type == ConditionType.LESS_THAN:
            return f"{self.attribute} < {self.value}"
        elif self.condition_type == ConditionType.GREATER_THAN:
            return f"{self.attribute} > {self.value}"
        elif self.condition_type == ConditionType.IN_RANGE:
            return f"{self.value} ≤ {self.attribute} ≤ {self.value2}"
        elif self.condition_type == ConditionType.IN_SET:
            return f"{self.attribute} ∈ {self.value}"
        return f"{self.attribute} ? {self.value}"

    def matches(self, example: Example) -> bool:
        """Check if example matches this condition."""
        if self.attribute not in example.features:
            return False

        val = example.features[self.attribute]

        if self.condition_type == ConditionType.EQUALS:
            return val == self.value
        elif self.condition_type == ConditionType.NOT_EQUALS:
            return val != self.value
        elif self.condition_type == ConditionType.LESS_THAN:
            return val < self.value
        elif self.condition_type == ConditionType.GREATER_THAN:
            return val > self.value
        elif self.condition_type == ConditionType.IN_RANGE:
            return self.value <= val <= self.value2
        elif self.condition_type == ConditionType.IN_SET:
            return val in self.value

        return False


@dataclass
class Rule:
    """A learned rule: IF conditions THEN class."""
    rule_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    conditions: List[Condition] = field(default_factory=list)
    conclusion: str = ""
    coverage: int = 0  # Number of examples covered
    accuracy: float = 0.0
    support: float = 0.0
    quality: RuleQuality = RuleQuality.FAIR

    def __str__(self):
        if not self.conditions:
            return f"IF true THEN {self.conclusion}"

        conds = " AND ".join(str(c) for c in self.conditions)
        return f"IF {conds} THEN {self.conclusion}"

    def matches(self, example: Example) -> bool:
        """Check if example matches all conditions."""
        return all(c.matches(example) for c in self.conditions)


@dataclass
class RuleSet:
    """A set of learned rules."""
    ruleset_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    rules: List[Rule] = field(default_factory=list)
    default_class: str = ""
    accuracy: float = 0.0


@dataclass
class LearningStats:
    """Statistics from rule learning."""
    stats_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    num_rules: int = 0
    total_conditions: int = 0
    avg_conditions: float = 0.0
    training_accuracy: float = 0.0
    covered_positive: int = 0
    covered_negative: int = 0


# =============================================================================
# ATTRIBUTE MANAGER
# =============================================================================

class AttributeManager:
    """Manage attributes."""

    def __init__(self):
        self._attributes: Dict[str, Attribute] = {}

    def add(
        self,
        name: str,
        is_numeric: bool = False,
        possible_values: Optional[List[Any]] = None
    ) -> Attribute:
        """Add an attribute."""
        attr = Attribute(
            name=name,
            is_numeric=is_numeric,
            possible_values=possible_values or []
        )
        self._attributes[name] = attr
        return attr

    def get(self, name: str) -> Optional[Attribute]:
        """Get an attribute."""
        return self._attributes.get(name)

    def all_attributes(self) -> List[Attribute]:
        """Get all attributes."""
        return list(self._attributes.values())

    def infer_from_examples(self, examples: List[Example]) -> None:
        """Infer attributes from examples."""
        for ex in examples:
            for name, value in ex.features.items():
                if name not in self._attributes:
                    is_numeric = isinstance(value, (int, float))
                    self.add(name, is_numeric)

                attr = self._attributes[name]
                if value not in attr.possible_values:
                    attr.possible_values.append(value)


# =============================================================================
# CONDITION GENERATOR
# =============================================================================

class ConditionGenerator:
    """Generate candidate conditions."""

    def __init__(self, attributes: AttributeManager):
        self._attributes = attributes

    def generate_all(
        self,
        examples: List[Example]
    ) -> List[Condition]:
        """Generate all possible conditions."""
        conditions = []

        for attr in self._attributes.all_attributes():
            if attr.is_numeric:
                conditions.extend(self._numeric_conditions(attr, examples))
            else:
                conditions.extend(self._categorical_conditions(attr))

        return conditions

    def _categorical_conditions(self, attr: Attribute) -> List[Condition]:
        """Generate conditions for categorical attribute."""
        conditions = []

        for value in attr.possible_values:
            conditions.append(Condition(
                attribute=attr.name,
                condition_type=ConditionType.EQUALS,
                value=value
            ))
            conditions.append(Condition(
                attribute=attr.name,
                condition_type=ConditionType.NOT_EQUALS,
                value=value
            ))

        return conditions

    def _numeric_conditions(
        self,
        attr: Attribute,
        examples: List[Example]
    ) -> List[Condition]:
        """Generate conditions for numeric attribute."""
        conditions = []

        # Get all values
        values = sorted(set(
            ex.features.get(attr.name)
            for ex in examples
            if attr.name in ex.features and ex.features[attr.name] is not None
        ))

        # Generate threshold conditions
        for i in range(len(values) - 1):
            threshold = (values[i] + values[i + 1]) / 2

            conditions.append(Condition(
                attribute=attr.name,
                condition_type=ConditionType.LESS_THAN,
                value=threshold
            ))
            conditions.append(Condition(
                attribute=attr.name,
                condition_type=ConditionType.GREATER_THAN,
                value=threshold
            ))

        return conditions


# =============================================================================
# RULE EVALUATOR
# =============================================================================

class RuleEvaluator:
    """Evaluate rules on examples."""

    def __init__(self):
        pass

    def evaluate(
        self,
        rule: Rule,
        positive: List[Example],
        negative: List[Example]
    ) -> None:
        """Evaluate rule and update its metrics."""
        covered_pos = sum(1 for ex in positive if rule.matches(ex))
        covered_neg = sum(1 for ex in negative if rule.matches(ex))

        total_covered = covered_pos + covered_neg

        rule.coverage = total_covered

        if total_covered > 0:
            rule.accuracy = covered_pos / total_covered
        else:
            rule.accuracy = 0.0

        if positive:
            rule.support = covered_pos / len(positive)
        else:
            rule.support = 0.0

        # Assign quality
        if rule.accuracy >= 0.95 and rule.support >= 0.1:
            rule.quality = RuleQuality.EXCELLENT
        elif rule.accuracy >= 0.8:
            rule.quality = RuleQuality.GOOD
        elif rule.accuracy >= 0.6:
            rule.quality = RuleQuality.FAIR
        else:
            rule.quality = RuleQuality.POOR

    def information_gain(
        self,
        condition: Condition,
        rule: Rule,
        positive: List[Example],
        negative: List[Example]
    ) -> float:
        """Compute information gain of adding condition to rule."""
        # Current coverage
        pos_before = [ex for ex in positive if rule.matches(ex)]
        neg_before = [ex for ex in negative if rule.matches(ex)]

        # After adding condition
        new_rule = Rule(
            conditions=rule.conditions + [condition],
            conclusion=rule.conclusion
        )

        pos_after = [ex for ex in positive if new_rule.matches(ex)]
        neg_after = [ex for ex in negative if new_rule.matches(ex)]

        # FOIL gain
        p0 = len(pos_before)
        n0 = len(neg_before)
        p1 = len(pos_after)
        n1 = len(neg_after)

        if p0 == 0 or p1 == 0:
            return 0.0

        if p0 + n0 == 0 or p1 + n1 == 0:
            return 0.0

        log_before = math.log2(p0 / (p0 + n0)) if p0 + n0 > 0 else 0
        log_after = math.log2(p1 / (p1 + n1)) if p1 + n1 > 0 else 0

        gain = p1 * (log_after - log_before)

        return max(0.0, gain)


# =============================================================================
# SEQUENTIAL COVERING LEARNER
# =============================================================================

class SequentialCoveringLearner:
    """Learn rules using sequential covering."""

    def __init__(
        self,
        attributes: AttributeManager,
        evaluator: RuleEvaluator
    ):
        self._attributes = attributes
        self._evaluator = evaluator
        self._generator = ConditionGenerator(attributes)

    def learn(
        self,
        examples: List[Example],
        target_class: str
    ) -> List[Rule]:
        """Learn rules for target class."""
        rules: List[Rule] = []

        positive = [ex for ex in examples if ex.label == target_class]
        negative = [ex for ex in examples if ex.label != target_class]

        uncovered = positive.copy()

        while uncovered:
            # Learn one rule
            rule = self._learn_one_rule(uncovered, negative, target_class)

            if rule is None or rule.coverage == 0:
                break

            rules.append(rule)

            # Remove covered examples
            uncovered = [ex for ex in uncovered if not rule.matches(ex)]

        return rules

    def _learn_one_rule(
        self,
        positive: List[Example],
        negative: List[Example],
        target_class: str
    ) -> Optional[Rule]:
        """Learn a single rule using beam search."""
        # Start with empty rule
        rule = Rule(conclusion=target_class)

        candidates = self._generator.generate_all(positive + negative)

        while True:
            # Check if rule is good enough
            covered_neg = [ex for ex in negative if rule.matches(ex)]
            if not covered_neg:
                break

            # Find best condition to add
            best_cond = None
            best_gain = -float('inf')

            for cond in candidates:
                # Skip if condition already in rule
                if any(c.attribute == cond.attribute and
                       c.condition_type == cond.condition_type and
                       c.value == cond.value for c in rule.conditions):
                    continue

                gain = self._evaluator.information_gain(
                    cond, rule, positive, negative
                )

                if gain > best_gain:
                    best_gain = gain
                    best_cond = cond

            if best_cond is None or best_gain <= 0:
                break

            rule.conditions.append(best_cond)

        self._evaluator.evaluate(rule, positive, negative)

        return rule if rule.coverage > 0 else None


# =============================================================================
# RULE PRUNER
# =============================================================================

class RulePruner:
    """Prune rules to avoid overfitting."""

    def __init__(self, evaluator: RuleEvaluator):
        self._evaluator = evaluator

    def prune(
        self,
        rule: Rule,
        positive: List[Example],
        negative: List[Example]
    ) -> Rule:
        """Prune unnecessary conditions from rule."""
        if len(rule.conditions) <= 1:
            return rule

        best_rule = rule
        self._evaluator.evaluate(best_rule, positive, negative)
        best_accuracy = best_rule.accuracy

        # Try removing each condition
        for i in range(len(rule.conditions)):
            # Create rule without condition i
            new_conditions = rule.conditions[:i] + rule.conditions[i+1:]
            new_rule = Rule(
                conditions=new_conditions,
                conclusion=rule.conclusion
            )

            self._evaluator.evaluate(new_rule, positive, negative)

            # Keep if accuracy doesn't decrease much
            if new_rule.accuracy >= best_accuracy - 0.05:
                if len(new_rule.conditions) < len(best_rule.conditions):
                    best_rule = new_rule
                    best_accuracy = new_rule.accuracy

        return best_rule

    def prune_ruleset(
        self,
        rules: List[Rule],
        examples: List[Example]
    ) -> List[Rule]:
        """Prune redundant rules from ruleset."""
        if len(rules) <= 1:
            return rules

        pruned = []
        covered: Set[str] = set()

        for rule in rules:
            # Check if rule covers new examples
            new_covered = set(
                ex.example_id for ex in examples
                if rule.matches(ex) and ex.example_id not in covered
            )

            if new_covered:
                pruned.append(rule)
                covered.update(new_covered)

        return pruned


# =============================================================================
# RULE LEARNER
# =============================================================================

class RuleLearner:
    """
    Rule Learner for BAEL.

    Advanced inductive rule learning and discovery.
    """

    def __init__(self):
        self._attributes = AttributeManager()
        self._evaluator = RuleEvaluator()
        self._learner = SequentialCoveringLearner(
            self._attributes, self._evaluator
        )
        self._pruner = RulePruner(self._evaluator)
        self._examples: List[Example] = []
        self._ruleset: Optional[RuleSet] = None

    # -------------------------------------------------------------------------
    # ATTRIBUTES
    # -------------------------------------------------------------------------

    def add_attribute(
        self,
        name: str,
        is_numeric: bool = False,
        possible_values: Optional[List[Any]] = None
    ) -> Attribute:
        """Add an attribute."""
        return self._attributes.add(name, is_numeric, possible_values)

    def get_attribute(self, name: str) -> Optional[Attribute]:
        """Get an attribute."""
        return self._attributes.get(name)

    def all_attributes(self) -> List[Attribute]:
        """Get all attributes."""
        return self._attributes.all_attributes()

    # -------------------------------------------------------------------------
    # EXAMPLES
    # -------------------------------------------------------------------------

    def add_example(
        self,
        features: Dict[str, Any],
        label: str,
        weight: float = 1.0
    ) -> Example:
        """Add a training example."""
        example = Example(
            features=features,
            label=label,
            weight=weight
        )
        self._examples.append(example)
        return example

    def all_examples(self) -> List[Example]:
        """Get all examples."""
        return self._examples.copy()

    def get_classes(self) -> Set[str]:
        """Get all class labels."""
        return set(ex.label for ex in self._examples)

    # -------------------------------------------------------------------------
    # LEARNING
    # -------------------------------------------------------------------------

    def learn(
        self,
        strategy: LearningStrategy = LearningStrategy.SEQUENTIAL_COVERING,
        prune: bool = True
    ) -> RuleSet:
        """Learn rules from examples."""
        # Infer attributes if not provided
        self._attributes.infer_from_examples(self._examples)

        # Update generator
        self._learner = SequentialCoveringLearner(
            self._attributes, self._evaluator
        )

        all_rules: List[Rule] = []
        classes = self.get_classes()

        # Learn rules for each class
        for target_class in classes:
            rules = self._learner.learn(self._examples, target_class)

            if prune:
                positive = [ex for ex in self._examples
                           if ex.label == target_class]
                negative = [ex for ex in self._examples
                           if ex.label != target_class]

                rules = [self._pruner.prune(r, positive, negative)
                        for r in rules]

            all_rules.extend(rules)

        # Determine default class (most common)
        class_counts = defaultdict(int)
        for ex in self._examples:
            class_counts[ex.label] += 1

        default_class = max(class_counts.keys(), key=lambda k: class_counts[k])

        # Create ruleset
        self._ruleset = RuleSet(
            rules=all_rules,
            default_class=default_class
        )

        # Compute accuracy
        self._compute_ruleset_accuracy()

        return self._ruleset

    def _compute_ruleset_accuracy(self) -> None:
        """Compute ruleset accuracy on training data."""
        if not self._ruleset:
            return

        correct = 0
        for ex in self._examples:
            predicted = self.predict(ex)
            if predicted == ex.label:
                correct += 1

        self._ruleset.accuracy = correct / len(self._examples) if self._examples else 0.0

    # -------------------------------------------------------------------------
    # PREDICTION
    # -------------------------------------------------------------------------

    def predict(self, example: Example) -> str:
        """Predict class for an example."""
        if not self._ruleset:
            return ""

        for rule in self._ruleset.rules:
            if rule.matches(example):
                return rule.conclusion

        return self._ruleset.default_class

    def predict_features(self, features: Dict[str, Any]) -> str:
        """Predict class for features."""
        ex = Example(features=features)
        return self.predict(ex)

    # -------------------------------------------------------------------------
    # RULES
    # -------------------------------------------------------------------------

    def get_ruleset(self) -> Optional[RuleSet]:
        """Get learned ruleset."""
        return self._ruleset

    def get_rules(self) -> List[Rule]:
        """Get all learned rules."""
        return self._ruleset.rules if self._ruleset else []

    def get_rules_for_class(self, target_class: str) -> List[Rule]:
        """Get rules for a specific class."""
        if not self._ruleset:
            return []

        return [r for r in self._ruleset.rules if r.conclusion == target_class]

    # -------------------------------------------------------------------------
    # EVALUATION
    # -------------------------------------------------------------------------

    def evaluate(self, test_examples: List[Example]) -> float:
        """Evaluate ruleset on test examples."""
        correct = 0
        for ex in test_examples:
            if self.predict(ex) == ex.label:
                correct += 1

        return correct / len(test_examples) if test_examples else 0.0

    def get_stats(self) -> LearningStats:
        """Get learning statistics."""
        if not self._ruleset:
            return LearningStats()

        total_conds = sum(len(r.conditions) for r in self._ruleset.rules)
        avg_conds = total_conds / len(self._ruleset.rules) if self._ruleset.rules else 0

        covered_pos = 0
        covered_neg = 0

        for rule in self._ruleset.rules:
            for ex in self._examples:
                if rule.matches(ex):
                    if ex.label == rule.conclusion:
                        covered_pos += 1
                    else:
                        covered_neg += 1

        return LearningStats(
            num_rules=len(self._ruleset.rules),
            total_conditions=total_conds,
            avg_conditions=avg_conds,
            training_accuracy=self._ruleset.accuracy,
            covered_positive=covered_pos,
            covered_negative=covered_neg
        )

    # -------------------------------------------------------------------------
    # RULE REFINEMENT
    # -------------------------------------------------------------------------

    def refine_rule(
        self,
        rule: Rule,
        positive: List[Example],
        negative: List[Example]
    ) -> Rule:
        """Refine a rule by adding conditions."""
        candidates = ConditionGenerator(self._attributes).generate_all(
            positive + negative
        )

        best_rule = rule
        self._evaluator.evaluate(best_rule, positive, negative)

        for cond in candidates:
            new_rule = Rule(
                conditions=rule.conditions + [cond],
                conclusion=rule.conclusion
            )

            self._evaluator.evaluate(new_rule, positive, negative)

            if new_rule.accuracy > best_rule.accuracy:
                best_rule = new_rule

        return best_rule

    def generalize_rule(self, rule: Rule) -> Rule:
        """Generalize a rule by removing conditions."""
        return self._pruner.prune(
            rule,
            [ex for ex in self._examples if ex.label == rule.conclusion],
            [ex for ex in self._examples if ex.label != rule.conclusion]
        )


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Rule Learner."""
    print("=" * 70)
    print("BAEL - RULE LEARNER DEMO")
    print("Advanced Inductive Rule Learning")
    print("=" * 70)
    print()

    learner = RuleLearner()

    # 1. Add Attributes
    print("1. ADD ATTRIBUTES:")
    print("-" * 40)

    learner.add_attribute("outlook", False, ["sunny", "overcast", "rainy"])
    learner.add_attribute("temperature", True)
    learner.add_attribute("humidity", True)
    learner.add_attribute("windy", False, [True, False])

    for attr in learner.all_attributes():
        kind = "numeric" if attr.is_numeric else "categorical"
        print(f"   {attr.name}: {kind}")
    print()

    # 2. Add Training Examples (Play Tennis dataset)
    print("2. ADD TRAINING EXAMPLES:")
    print("-" * 40)

    data = [
        ({"outlook": "sunny", "temperature": 85, "humidity": 85, "windy": False}, "no"),
        ({"outlook": "sunny", "temperature": 80, "humidity": 90, "windy": True}, "no"),
        ({"outlook": "overcast", "temperature": 83, "humidity": 78, "windy": False}, "yes"),
        ({"outlook": "rainy", "temperature": 70, "humidity": 96, "windy": False}, "yes"),
        ({"outlook": "rainy", "temperature": 68, "humidity": 80, "windy": False}, "yes"),
        ({"outlook": "rainy", "temperature": 65, "humidity": 70, "windy": True}, "no"),
        ({"outlook": "overcast", "temperature": 64, "humidity": 65, "windy": True}, "yes"),
        ({"outlook": "sunny", "temperature": 72, "humidity": 95, "windy": False}, "no"),
        ({"outlook": "sunny", "temperature": 69, "humidity": 70, "windy": False}, "yes"),
        ({"outlook": "rainy", "temperature": 75, "humidity": 80, "windy": False}, "yes"),
        ({"outlook": "sunny", "temperature": 75, "humidity": 70, "windy": True}, "yes"),
        ({"outlook": "overcast", "temperature": 72, "humidity": 90, "windy": True}, "yes"),
        ({"outlook": "overcast", "temperature": 81, "humidity": 75, "windy": False}, "yes"),
        ({"outlook": "rainy", "temperature": 71, "humidity": 80, "windy": True}, "no"),
    ]

    for features, label in data:
        learner.add_example(features, label)

    print(f"   Added {len(data)} training examples")
    print(f"   Classes: {learner.get_classes()}")
    print()

    # 3. Learn Rules
    print("3. LEARN RULES:")
    print("-" * 40)

    ruleset = learner.learn(prune=True)

    print(f"   Learned {len(ruleset.rules)} rules")
    print(f"   Default class: {ruleset.default_class}")
    print(f"   Training accuracy: {ruleset.accuracy:.2%}")
    print()

    # 4. Display Rules
    print("4. LEARNED RULES:")
    print("-" * 40)

    for i, rule in enumerate(learner.get_rules(), 1):
        print(f"   Rule {i}: {rule}")
        print(f"           Coverage: {rule.coverage}, Accuracy: {rule.accuracy:.2%}")
    print()

    # 5. Rules by Class
    print("5. RULES BY CLASS:")
    print("-" * 40)

    for cls in learner.get_classes():
        rules = learner.get_rules_for_class(cls)
        print(f"   Class '{cls}': {len(rules)} rules")
    print()

    # 6. Predictions
    print("6. PREDICTIONS:")
    print("-" * 40)

    test1 = {"outlook": "sunny", "temperature": 70, "humidity": 65, "windy": False}
    test2 = {"outlook": "rainy", "temperature": 75, "humidity": 85, "windy": True}
    test3 = {"outlook": "overcast", "temperature": 80, "humidity": 80, "windy": False}

    for test in [test1, test2, test3]:
        pred = learner.predict_features(test)
        print(f"   {test['outlook']}, {test['temperature']}°F, {test['humidity']}% humidity, windy={test['windy']}")
        print(f"     → Prediction: {pred}")
    print()

    # 7. Learning Statistics
    print("7. LEARNING STATISTICS:")
    print("-" * 40)

    stats = learner.get_stats()
    print(f"   Number of rules: {stats.num_rules}")
    print(f"   Total conditions: {stats.total_conditions}")
    print(f"   Average conditions per rule: {stats.avg_conditions:.2f}")
    print(f"   Training accuracy: {stats.training_accuracy:.2%}")
    print()

    # 8. Rule Quality
    print("8. RULE QUALITY:")
    print("-" * 40)

    for rule in learner.get_rules():
        print(f"   {rule.quality.value.upper()}: {rule}")
    print()

    # 9. Cross-validation (simple hold-out)
    print("9. EVALUATION:")
    print("-" * 40)

    # Use training data for demo
    accuracy = learner.evaluate(learner.all_examples())
    print(f"   Training accuracy: {accuracy:.2%}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Rule Learner Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())

#!/usr/bin/env python3
"""
BAEL - Inductive Reasoner
Advanced inductive reasoning and pattern generalization.

Features:
- Pattern induction from examples
- Concept learning
- Hypothesis generation
- Rule induction
- Statistical generalization
- Version space learning
- Minimum description length
"""

import asyncio
import hashlib
import math
import random
import uuid
from abc import ABC, abstractmethod
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import (Any, Callable, Dict, Generic, List, Optional, Set, Tuple,
                    Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class ExampleType(Enum):
    """Types of training examples."""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    UNLABELED = "unlabeled"


class GeneralizationMethod(Enum):
    """Methods for generalization."""
    SPECIFIC_TO_GENERAL = "specific_to_general"
    GENERAL_TO_SPECIFIC = "general_to_specific"
    VERSION_SPACE = "version_space"
    RULE_INDUCTION = "rule_induction"
    MDL = "minimum_description_length"


class HypothesisStatus(Enum):
    """Status of an induced hypothesis."""
    CONSISTENT = "consistent"
    INCONSISTENT = "inconsistent"
    OVERFITTING = "overfitting"
    UNDERFITTING = "underfitting"


class PatternType(Enum):
    """Types of patterns."""
    SEQUENCE = "sequence"
    ASSOCIATION = "association"
    CLASSIFICATION = "classification"
    CLUSTER = "cluster"


class RuleType(Enum):
    """Types of induced rules."""
    CONJUNCTIVE = "conjunctive"
    DISJUNCTIVE = "disjunctive"
    HORN = "horn"
    DECISION_LIST = "decision_list"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class Feature:
    """A feature for learning."""
    name: str
    value_type: str = "nominal"  # nominal, numeric, ordinal
    possible_values: List[Any] = field(default_factory=list)


@dataclass
class Example:
    """A training example."""
    example_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    features: Dict[str, Any] = field(default_factory=dict)
    label: Optional[Any] = None
    example_type: ExampleType = ExampleType.UNLABELED
    weight: float = 1.0


@dataclass
class Pattern:
    """An induced pattern."""
    pattern_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    pattern_type: PatternType = PatternType.SEQUENCE
    structure: Any = None
    support: float = 0.0
    confidence: float = 0.0


@dataclass
class Rule:
    """An induced rule."""
    rule_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    antecedent: Dict[str, Any] = field(default_factory=dict)
    consequent: Any = None
    rule_type: RuleType = RuleType.CONJUNCTIVE
    coverage: int = 0
    accuracy: float = 0.0


@dataclass
class Hypothesis:
    """An induced hypothesis."""
    hypothesis_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    conditions: Dict[str, Any] = field(default_factory=dict)
    conclusion: Any = None
    status: HypothesisStatus = HypothesisStatus.CONSISTENT
    examples_covered: int = 0
    complexity: float = 0.0


@dataclass
class Concept:
    """A learned concept."""
    concept_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    definition: Dict[str, Any] = field(default_factory=dict)
    positive_examples: List[str] = field(default_factory=list)
    negative_examples: List[str] = field(default_factory=list)


@dataclass
class VersionSpace:
    """A version space for concept learning."""
    space_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    general_boundary: List[Dict[str, Any]] = field(default_factory=list)
    specific_boundary: List[Dict[str, Any]] = field(default_factory=list)
    collapsed: bool = False


# =============================================================================
# FEATURE MANAGER
# =============================================================================

class FeatureManager:
    """Manage features for learning."""

    def __init__(self):
        self._features: Dict[str, Feature] = {}

    def add_feature(
        self,
        name: str,
        value_type: str = "nominal",
        possible_values: Optional[List[Any]] = None
    ) -> Feature:
        """Add a feature."""
        feature = Feature(
            name=name,
            value_type=value_type,
            possible_values=possible_values or []
        )
        self._features[name] = feature
        return feature

    def get_feature(self, name: str) -> Optional[Feature]:
        """Get a feature."""
        return self._features.get(name)

    def infer_features(self, examples: List[Example]) -> Dict[str, Feature]:
        """Infer features from examples."""
        for example in examples:
            for name, value in example.features.items():
                if name not in self._features:
                    # Infer type
                    if isinstance(value, (int, float)):
                        value_type = "numeric"
                    else:
                        value_type = "nominal"

                    self._features[name] = Feature(
                        name=name,
                        value_type=value_type,
                        possible_values=[]
                    )

                # Track possible values
                if value not in self._features[name].possible_values:
                    self._features[name].possible_values.append(value)

        return self._features

    def get_all_features(self) -> List[Feature]:
        """Get all features."""
        return list(self._features.values())


# =============================================================================
# HYPOTHESIS GENERATOR
# =============================================================================

class HypothesisGenerator:
    """Generate hypotheses from examples."""

    def __init__(self, features: FeatureManager):
        self._features = features

    def generate_from_positive(
        self,
        positive_examples: List[Example]
    ) -> List[Hypothesis]:
        """Generate hypotheses from positive examples."""
        if not positive_examples:
            return []

        hypotheses = []

        # Find common features
        common = self._find_common_features(positive_examples)

        if common:
            hyp = Hypothesis(
                conditions=common,
                conclusion=positive_examples[0].label,
                examples_covered=len(positive_examples),
                complexity=len(common)
            )
            hypotheses.append(hyp)

        # Generate more specific hypotheses
        for example in positive_examples[:5]:  # Limit for efficiency
            hyp = Hypothesis(
                conditions=example.features.copy(),
                conclusion=example.label,
                examples_covered=1,
                complexity=len(example.features)
            )
            hypotheses.append(hyp)

        return hypotheses

    def _find_common_features(
        self,
        examples: List[Example]
    ) -> Dict[str, Any]:
        """Find features common to all examples."""
        if not examples:
            return {}

        common = examples[0].features.copy()

        for example in examples[1:]:
            to_remove = []
            for key, value in common.items():
                if key not in example.features:
                    to_remove.append(key)
                elif example.features[key] != value:
                    to_remove.append(key)

            for key in to_remove:
                del common[key]

        return common

    def specialize(
        self,
        hypothesis: Hypothesis,
        negative_example: Example
    ) -> List[Hypothesis]:
        """Specialize a hypothesis to exclude a negative example."""
        specialized = []

        for name, value in negative_example.features.items():
            if name not in hypothesis.conditions:
                # Add constraint on this feature
                for possible_value in self._features.get_feature(name).possible_values if self._features.get_feature(name) else [value]:
                    if possible_value != value:
                        new_conditions = hypothesis.conditions.copy()
                        new_conditions[name] = possible_value

                        new_hyp = Hypothesis(
                            conditions=new_conditions,
                            conclusion=hypothesis.conclusion,
                            complexity=len(new_conditions)
                        )
                        specialized.append(new_hyp)

        return specialized if specialized else [hypothesis]

    def generalize(
        self,
        hypothesis: Hypothesis,
        positive_example: Example
    ) -> Hypothesis:
        """Generalize a hypothesis to cover a positive example."""
        new_conditions = {}

        for key, value in hypothesis.conditions.items():
            if key in positive_example.features:
                if positive_example.features[key] == value:
                    new_conditions[key] = value
                # else drop this condition (generalize)

        return Hypothesis(
            conditions=new_conditions,
            conclusion=hypothesis.conclusion,
            complexity=len(new_conditions)
        )


# =============================================================================
# VERSION SPACE LEARNER
# =============================================================================

class VersionSpaceLearner:
    """
    Version space learning (candidate elimination algorithm).
    """

    def __init__(self, features: FeatureManager):
        self._features = features
        self._general: List[Dict[str, Any]] = [{}]  # Most general
        self._specific: List[Dict[str, Any]] = []   # Most specific

    def initialize(self, first_positive: Example) -> VersionSpace:
        """Initialize version space with first positive example."""
        self._specific = [first_positive.features.copy()]
        self._general = [{}]

        return VersionSpace(
            general_boundary=self._general.copy(),
            specific_boundary=self._specific.copy()
        )

    def update_positive(self, example: Example) -> VersionSpace:
        """Update version space with positive example."""
        # Remove inconsistent hypotheses from S
        new_specific = []

        for s in self._specific:
            if self._covers(s, example.features):
                new_specific.append(s)
            else:
                # Generalize S
                generalized = self._minimal_generalization(s, example.features)
                for g in generalized:
                    # Keep only if more general than some G
                    if any(self._more_general(gen, g) for gen in self._general):
                        new_specific.append(g)

        if not new_specific and self._specific:
            # Use most recent positive
            new_specific = [example.features.copy()]

        self._specific = new_specific

        # Remove G hypotheses inconsistent with positive example
        self._general = [
            g for g in self._general
            if self._covers(g, example.features)
        ]

        return self._get_version_space()

    def update_negative(self, example: Example) -> VersionSpace:
        """Update version space with negative example."""
        # Remove S hypotheses that cover negative example
        self._specific = [
            s for s in self._specific
            if not self._covers(s, example.features)
        ]

        # Specialize G hypotheses that cover negative example
        new_general = []

        for g in self._general:
            if not self._covers(g, example.features):
                new_general.append(g)
            else:
                # Minimally specialize
                specializations = self._minimal_specialization(g, example.features)
                for spec in specializations:
                    # Keep if more general than some S
                    if any(self._more_general(spec, s) for s in self._specific):
                        new_general.append(spec)

        self._general = new_general

        return self._get_version_space()

    def _covers(
        self,
        hypothesis: Dict[str, Any],
        instance: Dict[str, Any]
    ) -> bool:
        """Check if hypothesis covers instance."""
        for key, value in hypothesis.items():
            if key not in instance:
                return False
            if instance[key] != value:
                return False
        return True

    def _more_general(
        self,
        h1: Dict[str, Any],
        h2: Dict[str, Any]
    ) -> bool:
        """Check if h1 is more general than h2."""
        # h1 is more general if it has fewer constraints
        for key, value in h1.items():
            if key not in h2:
                return False
            if h2[key] != value:
                return False
        return len(h1) <= len(h2)

    def _minimal_generalization(
        self,
        specific: Dict[str, Any],
        instance: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Minimally generalize specific to cover instance."""
        result = {}

        for key, value in specific.items():
            if key in instance and instance[key] == value:
                result[key] = value

        return [result] if result != specific else [result]

    def _minimal_specialization(
        self,
        general: Dict[str, Any],
        negative: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Minimally specialize general to exclude negative."""
        specializations = []

        for feature in self._features.get_all_features():
            if feature.name not in general:
                for value in feature.possible_values:
                    if negative.get(feature.name) != value:
                        spec = general.copy()
                        spec[feature.name] = value
                        specializations.append(spec)

        return specializations

    def _get_version_space(self) -> VersionSpace:
        """Get current version space."""
        return VersionSpace(
            general_boundary=self._general.copy(),
            specific_boundary=self._specific.copy(),
            collapsed=(not self._general or not self._specific)
        )

    def is_collapsed(self) -> bool:
        """Check if version space has collapsed."""
        return not self._general or not self._specific


# =============================================================================
# RULE INDUCER
# =============================================================================

class RuleInducer:
    """Induce rules from examples."""

    def __init__(self, features: FeatureManager):
        self._features = features

    def induce_rules(
        self,
        positive: List[Example],
        negative: List[Example]
    ) -> List[Rule]:
        """Induce rules using sequential covering."""
        rules = []
        uncovered = positive.copy()

        while uncovered:
            # Learn rule covering some uncovered positive examples
            rule = self._learn_one_rule(uncovered, negative)

            if rule is None:
                break

            rules.append(rule)

            # Remove covered examples
            uncovered = [
                ex for ex in uncovered
                if not self._covers(rule, ex)
            ]

        return rules

    def _learn_one_rule(
        self,
        positive: List[Example],
        negative: List[Example]
    ) -> Optional[Rule]:
        """Learn a single rule."""
        if not positive:
            return None

        # Start with empty antecedent
        antecedent: Dict[str, Any] = {}

        # Iteratively specialize to exclude negatives
        covered_neg = [
            ex for ex in negative
            if self._covers_dict(antecedent, ex.features)
        ]

        while covered_neg:
            # Find best literal to add
            best_literal = None
            best_score = -1

            for feature in self._features.get_all_features():
                if feature.name in antecedent:
                    continue

                for value in feature.possible_values:
                    new_ant = antecedent.copy()
                    new_ant[feature.name] = value

                    # Count covered positives and negatives
                    pos_covered = sum(
                        1 for ex in positive
                        if self._covers_dict(new_ant, ex.features)
                    )
                    neg_covered = sum(
                        1 for ex in negative
                        if self._covers_dict(new_ant, ex.features)
                    )

                    if pos_covered == 0:
                        continue

                    # Score: favor rules that cover positives, exclude negatives
                    score = pos_covered / (pos_covered + neg_covered + 1)

                    if score > best_score:
                        best_score = score
                        best_literal = (feature.name, value)

            if best_literal is None:
                break

            antecedent[best_literal[0]] = best_literal[1]
            covered_neg = [
                ex for ex in negative
                if self._covers_dict(antecedent, ex.features)
            ]

        if not antecedent:
            # Use first positive as template
            antecedent = positive[0].features.copy()

        # Count coverage
        coverage = sum(
            1 for ex in positive
            if self._covers_dict(antecedent, ex.features)
        )

        neg_coverage = sum(
            1 for ex in negative
            if self._covers_dict(antecedent, ex.features)
        )

        accuracy = coverage / (coverage + neg_coverage) if (coverage + neg_coverage) > 0 else 0

        return Rule(
            antecedent=antecedent,
            consequent=positive[0].label,
            coverage=coverage,
            accuracy=accuracy
        )

    def _covers_dict(
        self,
        antecedent: Dict[str, Any],
        features: Dict[str, Any]
    ) -> bool:
        """Check if antecedent covers features."""
        for key, value in antecedent.items():
            if key not in features:
                return False
            if features[key] != value:
                return False
        return True

    def _covers(self, rule: Rule, example: Example) -> bool:
        """Check if rule covers example."""
        return self._covers_dict(rule.antecedent, example.features)


# =============================================================================
# PATTERN DISCOVERER
# =============================================================================

class PatternDiscoverer:
    """Discover patterns from data."""

    def __init__(self):
        self._patterns: List[Pattern] = []

    def find_sequence_patterns(
        self,
        sequences: List[List[Any]],
        min_support: float = 0.1
    ) -> List[Pattern]:
        """Find frequent sequence patterns."""
        patterns = []

        # Count item frequencies
        item_counts: Dict[Any, int] = Counter()
        for seq in sequences:
            for item in seq:
                item_counts[item] += 1

        # Find frequent items
        n = len(sequences)
        frequent_items = [
            item for item, count in item_counts.items()
            if count / n >= min_support
        ]

        # Create patterns
        for item in frequent_items:
            support = item_counts[item] / n
            pattern = Pattern(
                pattern_type=PatternType.SEQUENCE,
                structure={"item": item},
                support=support
            )
            patterns.append(pattern)

        # Find bigrams
        bigram_counts: Dict[Tuple, int] = Counter()
        for seq in sequences:
            for i in range(len(seq) - 1):
                bigram = (seq[i], seq[i + 1])
                bigram_counts[bigram] += 1

        for bigram, count in bigram_counts.items():
            support = count / n
            if support >= min_support:
                pattern = Pattern(
                    pattern_type=PatternType.SEQUENCE,
                    structure={"bigram": bigram},
                    support=support
                )
                patterns.append(pattern)

        self._patterns.extend(patterns)
        return patterns

    def find_association_rules(
        self,
        transactions: List[Set[Any]],
        min_support: float = 0.1,
        min_confidence: float = 0.5
    ) -> List[Pattern]:
        """Find association rules."""
        patterns = []
        n = len(transactions)

        # Count itemset frequencies
        itemset_counts: Dict[frozenset, int] = Counter()

        for trans in transactions:
            for item in trans:
                itemset_counts[frozenset([item])] += 1

        # Frequent singletons
        frequent = {
            itemset: count for itemset, count in itemset_counts.items()
            if count / n >= min_support
        }

        # Find pairs
        for trans in transactions:
            items = list(trans)
            for i in range(len(items)):
                for j in range(i + 1, len(items)):
                    pair = frozenset([items[i], items[j]])
                    itemset_counts[pair] += 1

        # Generate rules from pairs
        for itemset, count in itemset_counts.items():
            if len(itemset) != 2:
                continue

            support = count / n
            if support < min_support:
                continue

            items = list(itemset)

            # Rule A -> B
            ant_count = itemset_counts.get(frozenset([items[0]]), 0)
            if ant_count > 0:
                confidence = count / ant_count
                if confidence >= min_confidence:
                    pattern = Pattern(
                        pattern_type=PatternType.ASSOCIATION,
                        structure={
                            "antecedent": items[0],
                            "consequent": items[1]
                        },
                        support=support,
                        confidence=confidence
                    )
                    patterns.append(pattern)

            # Rule B -> A
            ant_count = itemset_counts.get(frozenset([items[1]]), 0)
            if ant_count > 0:
                confidence = count / ant_count
                if confidence >= min_confidence:
                    pattern = Pattern(
                        pattern_type=PatternType.ASSOCIATION,
                        structure={
                            "antecedent": items[1],
                            "consequent": items[0]
                        },
                        support=support,
                        confidence=confidence
                    )
                    patterns.append(pattern)

        self._patterns.extend(patterns)
        return patterns


# =============================================================================
# MDL LEARNER
# =============================================================================

class MDLLearner:
    """
    Minimum Description Length learning.
    """

    def __init__(self):
        self._hypotheses: List[Hypothesis] = []

    def compute_description_length(
        self,
        hypothesis: Hypothesis,
        examples: List[Example]
    ) -> float:
        """Compute total description length."""
        # Length of hypothesis
        h_length = self._hypothesis_length(hypothesis)

        # Length of data given hypothesis
        d_given_h = self._data_length(hypothesis, examples)

        return h_length + d_given_h

    def _hypothesis_length(self, hypothesis: Hypothesis) -> float:
        """Compute description length of hypothesis."""
        # Simple model: length proportional to number of conditions
        return len(hypothesis.conditions) * 2  # 2 bits per condition

    def _data_length(
        self,
        hypothesis: Hypothesis,
        examples: List[Example]
    ) -> float:
        """Compute description length of data given hypothesis."""
        # Count misclassified examples
        errors = 0

        for example in examples:
            predicted = self._predict(hypothesis, example)
            if predicted != (example.example_type == ExampleType.POSITIVE):
                errors += 1

        # Length is log of number of ways to specify errors
        if errors == 0:
            return 0

        n = len(examples)
        # Binomial coefficient approximation
        return errors * math.log2(n) if n > 0 else 0

    def _predict(
        self,
        hypothesis: Hypothesis,
        example: Example
    ) -> bool:
        """Predict if example is positive."""
        for key, value in hypothesis.conditions.items():
            if key not in example.features:
                return False
            if example.features[key] != value:
                return False
        return True

    def select_best(
        self,
        hypotheses: List[Hypothesis],
        examples: List[Example]
    ) -> Optional[Hypothesis]:
        """Select hypothesis with minimum description length."""
        if not hypotheses:
            return None

        best = None
        best_length = float('inf')

        for hypothesis in hypotheses:
            length = self.compute_description_length(hypothesis, examples)
            if length < best_length:
                best_length = length
                best = hypothesis
                best.complexity = best_length

        return best


# =============================================================================
# CONCEPT LEARNER
# =============================================================================

class ConceptLearner:
    """Learn concept descriptions."""

    def __init__(self, features: FeatureManager):
        self._features = features
        self._concepts: Dict[str, Concept] = {}

    def learn_concept(
        self,
        name: str,
        positive: List[Example],
        negative: List[Example]
    ) -> Concept:
        """Learn a concept from examples."""
        # Find necessary conditions (must be true for all positives)
        necessary = self._find_necessary(positive)

        # Find sufficient conditions (separate from negatives)
        sufficient = self._find_sufficient(positive, negative)

        # Combine
        definition = {**necessary}
        for key, value in sufficient.items():
            if key not in definition:
                definition[key] = value

        concept = Concept(
            name=name,
            definition=definition,
            positive_examples=[ex.example_id for ex in positive],
            negative_examples=[ex.example_id for ex in negative]
        )

        self._concepts[concept.concept_id] = concept
        return concept

    def _find_necessary(
        self,
        positive: List[Example]
    ) -> Dict[str, Any]:
        """Find conditions necessary for all positives."""
        if not positive:
            return {}

        necessary = positive[0].features.copy()

        for example in positive[1:]:
            to_remove = []
            for key, value in necessary.items():
                if key not in example.features:
                    to_remove.append(key)
                elif example.features[key] != value:
                    to_remove.append(key)

            for key in to_remove:
                del necessary[key]

        return necessary

    def _find_sufficient(
        self,
        positive: List[Example],
        negative: List[Example]
    ) -> Dict[str, Any]:
        """Find conditions sufficient to separate from negatives."""
        if not positive or not negative:
            return {}

        sufficient = {}

        for feature in self._features.get_all_features():
            pos_values = set(
                ex.features.get(feature.name)
                for ex in positive
            )
            neg_values = set(
                ex.features.get(feature.name)
                for ex in negative
            )

            # If positive values don't overlap with negative
            unique_pos = pos_values - neg_values
            if unique_pos and len(unique_pos) == 1:
                sufficient[feature.name] = list(unique_pos)[0]

        return sufficient

    def classify(
        self,
        concept_id: str,
        example: Example
    ) -> bool:
        """Classify an example using learned concept."""
        concept = self._concepts.get(concept_id)
        if not concept:
            return False

        for key, value in concept.definition.items():
            if key not in example.features:
                return False
            if example.features[key] != value:
                return False

        return True


# =============================================================================
# INDUCTIVE REASONER
# =============================================================================

class InductiveReasoner:
    """
    Inductive Reasoner for BAEL.

    Advanced inductive reasoning and pattern generalization.
    """

    def __init__(self):
        self._features = FeatureManager()
        self._hypothesis_gen = HypothesisGenerator(self._features)
        self._version_space = VersionSpaceLearner(self._features)
        self._rule_inducer = RuleInducer(self._features)
        self._pattern_discoverer = PatternDiscoverer()
        self._mdl_learner = MDLLearner()
        self._concept_learner = ConceptLearner(self._features)

        self._examples: Dict[str, Example] = {}
        self._hypotheses: Dict[str, Hypothesis] = {}

    # -------------------------------------------------------------------------
    # FEATURE MANAGEMENT
    # -------------------------------------------------------------------------

    def add_feature(
        self,
        name: str,
        value_type: str = "nominal",
        possible_values: Optional[List[Any]] = None
    ) -> Feature:
        """Add a feature."""
        return self._features.add_feature(name, value_type, possible_values)

    def infer_features(self, examples: List[Example]) -> Dict[str, Feature]:
        """Infer features from examples."""
        return self._features.infer_features(examples)

    # -------------------------------------------------------------------------
    # EXAMPLE MANAGEMENT
    # -------------------------------------------------------------------------

    def add_example(
        self,
        features: Dict[str, Any],
        label: Optional[Any] = None,
        example_type: ExampleType = ExampleType.UNLABELED
    ) -> Example:
        """Add a training example."""
        example = Example(
            features=features,
            label=label,
            example_type=example_type
        )
        self._examples[example.example_id] = example
        return example

    def get_positive_examples(self) -> List[Example]:
        """Get positive examples."""
        return [
            ex for ex in self._examples.values()
            if ex.example_type == ExampleType.POSITIVE
        ]

    def get_negative_examples(self) -> List[Example]:
        """Get negative examples."""
        return [
            ex for ex in self._examples.values()
            if ex.example_type == ExampleType.NEGATIVE
        ]

    # -------------------------------------------------------------------------
    # HYPOTHESIS GENERATION
    # -------------------------------------------------------------------------

    def generate_hypotheses(self) -> List[Hypothesis]:
        """Generate hypotheses from positive examples."""
        positive = self.get_positive_examples()
        hypotheses = self._hypothesis_gen.generate_from_positive(positive)

        for hyp in hypotheses:
            self._hypotheses[hyp.hypothesis_id] = hyp

        return hypotheses

    def specialize_hypothesis(
        self,
        hypothesis_id: str,
        negative_example: Example
    ) -> List[Hypothesis]:
        """Specialize hypothesis to exclude negative example."""
        hypothesis = self._hypotheses.get(hypothesis_id)
        if not hypothesis:
            return []

        return self._hypothesis_gen.specialize(hypothesis, negative_example)

    def generalize_hypothesis(
        self,
        hypothesis_id: str,
        positive_example: Example
    ) -> Hypothesis:
        """Generalize hypothesis to cover positive example."""
        hypothesis = self._hypotheses.get(hypothesis_id)
        if not hypothesis:
            return Hypothesis()

        return self._hypothesis_gen.generalize(hypothesis, positive_example)

    # -------------------------------------------------------------------------
    # VERSION SPACE LEARNING
    # -------------------------------------------------------------------------

    def learn_version_space(
        self,
        examples: List[Example]
    ) -> VersionSpace:
        """Learn using version space / candidate elimination."""
        # Initialize features
        self._features.infer_features(examples)

        vs = None

        for example in examples:
            if example.example_type == ExampleType.POSITIVE:
                if vs is None:
                    vs = self._version_space.initialize(example)
                else:
                    vs = self._version_space.update_positive(example)
            elif example.example_type == ExampleType.NEGATIVE:
                if vs is not None:
                    vs = self._version_space.update_negative(example)

        return vs or VersionSpace()

    # -------------------------------------------------------------------------
    # RULE INDUCTION
    # -------------------------------------------------------------------------

    def induce_rules(self) -> List[Rule]:
        """Induce rules from examples."""
        positive = self.get_positive_examples()
        negative = self.get_negative_examples()

        # Infer features
        self._features.infer_features(positive + negative)

        return self._rule_inducer.induce_rules(positive, negative)

    # -------------------------------------------------------------------------
    # PATTERN DISCOVERY
    # -------------------------------------------------------------------------

    def discover_sequence_patterns(
        self,
        sequences: List[List[Any]],
        min_support: float = 0.1
    ) -> List[Pattern]:
        """Discover sequence patterns."""
        return self._pattern_discoverer.find_sequence_patterns(sequences, min_support)

    def discover_association_rules(
        self,
        transactions: List[Set[Any]],
        min_support: float = 0.1,
        min_confidence: float = 0.5
    ) -> List[Pattern]:
        """Discover association rules."""
        return self._pattern_discoverer.find_association_rules(
            transactions, min_support, min_confidence
        )

    # -------------------------------------------------------------------------
    # MDL LEARNING
    # -------------------------------------------------------------------------

    def select_best_hypothesis_mdl(
        self,
        hypotheses: List[Hypothesis]
    ) -> Optional[Hypothesis]:
        """Select best hypothesis by MDL."""
        examples = list(self._examples.values())
        return self._mdl_learner.select_best(hypotheses, examples)

    # -------------------------------------------------------------------------
    # CONCEPT LEARNING
    # -------------------------------------------------------------------------

    def learn_concept(
        self,
        name: str
    ) -> Concept:
        """Learn a concept from current examples."""
        positive = self.get_positive_examples()
        negative = self.get_negative_examples()

        # Infer features
        self._features.infer_features(positive + negative)

        return self._concept_learner.learn_concept(name, positive, negative)

    def classify(
        self,
        concept_id: str,
        example: Example
    ) -> bool:
        """Classify example using learned concept."""
        return self._concept_learner.classify(concept_id, example)


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Inductive Reasoner."""
    print("=" * 70)
    print("BAEL - INDUCTIVE REASONER DEMO")
    print("Advanced Pattern Generalization and Rule Induction")
    print("=" * 70)
    print()

    reasoner = InductiveReasoner()

    # 1. Add Features
    print("1. DEFINE FEATURES:")
    print("-" * 40)

    reasoner.add_feature("color", "nominal", ["red", "green", "blue", "yellow"])
    reasoner.add_feature("shape", "nominal", ["circle", "square", "triangle"])
    reasoner.add_feature("size", "nominal", ["small", "medium", "large"])
    reasoner.add_feature("texture", "nominal", ["smooth", "rough"])

    print("   Features: color, shape, size, texture")
    print()

    # 2. Add Training Examples
    print("2. TRAINING EXAMPLES:")
    print("-" * 40)

    # Positive examples for concept "Good Apple"
    reasoner.add_example(
        {"color": "red", "shape": "circle", "size": "medium", "texture": "smooth"},
        label="good_apple",
        example_type=ExampleType.POSITIVE
    )
    reasoner.add_example(
        {"color": "red", "shape": "circle", "size": "large", "texture": "smooth"},
        label="good_apple",
        example_type=ExampleType.POSITIVE
    )
    reasoner.add_example(
        {"color": "green", "shape": "circle", "size": "medium", "texture": "smooth"},
        label="good_apple",
        example_type=ExampleType.POSITIVE
    )

    # Negative examples
    reasoner.add_example(
        {"color": "yellow", "shape": "triangle", "size": "small", "texture": "rough"},
        label="not_apple",
        example_type=ExampleType.NEGATIVE
    )
    reasoner.add_example(
        {"color": "blue", "shape": "square", "size": "medium", "texture": "rough"},
        label="not_apple",
        example_type=ExampleType.NEGATIVE
    )

    print(f"   Positive examples: {len(reasoner.get_positive_examples())}")
    print(f"   Negative examples: {len(reasoner.get_negative_examples())}")
    print()

    # 3. Generate Hypotheses
    print("3. HYPOTHESIS GENERATION:")
    print("-" * 40)

    hypotheses = reasoner.generate_hypotheses()
    print(f"   Generated {len(hypotheses)} hypotheses")

    for i, hyp in enumerate(hypotheses[:3]):
        print(f"   H{i+1}: {hyp.conditions}")
    print()

    # 4. Version Space Learning
    print("4. VERSION SPACE LEARNING:")
    print("-" * 40)

    examples = list(reasoner._examples.values())
    vs = reasoner.learn_version_space(examples)

    print(f"   General boundary: {len(vs.general_boundary)} hypotheses")
    print(f"   Specific boundary: {len(vs.specific_boundary)} hypotheses")
    print(f"   Collapsed: {vs.collapsed}")
    print()

    # 5. Rule Induction
    print("5. RULE INDUCTION:")
    print("-" * 40)

    rules = reasoner.induce_rules()
    print(f"   Induced {len(rules)} rules")

    for i, rule in enumerate(rules):
        print(f"   Rule {i+1}:")
        print(f"     IF {rule.antecedent}")
        print(f"     THEN {rule.consequent}")
        print(f"     Accuracy: {rule.accuracy:.2f}, Coverage: {rule.coverage}")
    print()

    # 6. Pattern Discovery (Sequences)
    print("6. SEQUENCE PATTERN DISCOVERY:")
    print("-" * 40)

    sequences = [
        ["A", "B", "C", "D"],
        ["A", "B", "E"],
        ["A", "B", "C"],
        ["B", "C", "D"],
        ["A", "C", "D"]
    ]

    patterns = reasoner.discover_sequence_patterns(sequences, min_support=0.4)
    print(f"   Found {len(patterns)} patterns")

    for pattern in patterns[:5]:
        print(f"   Pattern: {pattern.structure}, Support: {pattern.support:.2f}")
    print()

    # 7. Association Rules
    print("7. ASSOCIATION RULE DISCOVERY:")
    print("-" * 40)

    transactions = [
        {"bread", "milk", "eggs"},
        {"bread", "butter"},
        {"milk", "butter"},
        {"bread", "milk", "butter"},
        {"bread", "milk"},
    ]

    assoc_rules = reasoner.discover_association_rules(
        transactions, min_support=0.3, min_confidence=0.5
    )
    print(f"   Found {len(assoc_rules)} association rules")

    for rule in assoc_rules[:3]:
        print(f"   {rule.structure['antecedent']} => {rule.structure['consequent']}")
        print(f"     Support: {rule.support:.2f}, Confidence: {rule.confidence:.2f}")
    print()

    # 8. MDL Selection
    print("8. MDL HYPOTHESIS SELECTION:")
    print("-" * 40)

    if hypotheses:
        best = reasoner.select_best_hypothesis_mdl(hypotheses)
        if best:
            print(f"   Best hypothesis by MDL:")
            print(f"   Conditions: {best.conditions}")
            print(f"   Complexity: {best.complexity:.2f}")
    print()

    # 9. Concept Learning
    print("9. CONCEPT LEARNING:")
    print("-" * 40)

    concept = reasoner.learn_concept("GoodApple")
    print(f"   Concept: {concept.name}")
    print(f"   Definition: {concept.definition}")

    # Test classification
    test_example = Example(
        features={"color": "red", "shape": "circle", "size": "small", "texture": "smooth"}
    )
    is_good_apple = reasoner.classify(concept.concept_id, test_example)
    print(f"   Test example (red, circle, small, smooth): {is_good_apple}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Inductive Reasoner Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())

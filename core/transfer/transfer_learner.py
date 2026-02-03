#!/usr/bin/env python3
"""
BAEL - Transfer Learner
Advanced transfer learning and knowledge transfer.

Features:
- Domain adaptation
- Feature extraction
- Fine-tuning strategies
- Multi-task learning
- Knowledge distillation
- Cross-domain transfer
"""

import asyncio
import copy
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

class TransferType(Enum):
    """Types of transfer learning."""
    INDUCTIVE = "inductive"
    TRANSDUCTIVE = "transductive"
    UNSUPERVISED = "unsupervised"


class TransferStrategy(Enum):
    """Transfer strategies."""
    FEATURE_EXTRACTION = "feature_extraction"
    FINE_TUNING = "fine_tuning"
    KNOWLEDGE_DISTILLATION = "knowledge_distillation"
    DOMAIN_ADAPTATION = "domain_adaptation"


class DomainShift(Enum):
    """Types of domain shift."""
    COVARIATE = "covariate"
    PRIOR = "prior"
    CONCEPT = "concept"
    COMBINATION = "combination"


class TransferQuality(Enum):
    """Quality of transfer."""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


class AdaptationPhase(Enum):
    """Phases of adaptation."""
    INITIALIZATION = "initialization"
    ALIGNMENT = "alignment"
    FINE_TUNING = "fine_tuning"
    EVALUATION = "evaluation"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class Domain:
    """A learning domain."""
    domain_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    features: List[str] = field(default_factory=list)
    label_space: List[str] = field(default_factory=list)
    statistics: Dict[str, float] = field(default_factory=dict)


@dataclass
class Task:
    """A learning task."""
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    domain_id: str = ""
    task_type: str = ""  # classification, regression, etc.
    target_labels: List[str] = field(default_factory=list)


@dataclass
class KnowledgeBase:
    """Transferable knowledge."""
    kb_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_domain: str = ""
    features: Dict[str, Any] = field(default_factory=dict)
    weights: Dict[str, float] = field(default_factory=dict)
    patterns: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class TransferResult:
    """Result of transfer learning."""
    result_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_domain: str = ""
    target_domain: str = ""
    strategy: TransferStrategy = TransferStrategy.FINE_TUNING
    quality: TransferQuality = TransferQuality.NEUTRAL
    performance_before: float = 0.0
    performance_after: float = 0.0
    transfer_gain: float = 0.0


@dataclass
class DomainMapping:
    """Mapping between domains."""
    mapping_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_domain: str = ""
    target_domain: str = ""
    feature_mapping: Dict[str, str] = field(default_factory=dict)
    similarity: float = 0.0


@dataclass
class DistillationConfig:
    """Configuration for knowledge distillation."""
    temperature: float = 3.0
    alpha: float = 0.5  # Weight for soft targets
    teacher_model: str = ""
    student_model: str = ""


# =============================================================================
# DOMAIN MANAGER
# =============================================================================

class DomainManager:
    """Manage learning domains."""

    def __init__(self):
        self._domains: Dict[str, Domain] = {}

    def add(
        self,
        name: str,
        features: List[str],
        label_space: Optional[List[str]] = None
    ) -> Domain:
        """Add a domain."""
        domain = Domain(
            name=name,
            features=features,
            label_space=label_space or []
        )
        self._domains[name] = domain
        return domain

    def get(self, name: str) -> Optional[Domain]:
        """Get a domain."""
        return self._domains.get(name)

    def compute_similarity(
        self,
        domain1: str,
        domain2: str
    ) -> float:
        """Compute similarity between domains."""
        d1 = self._domains.get(domain1)
        d2 = self._domains.get(domain2)

        if not d1 or not d2:
            return 0.0

        # Feature overlap
        common = set(d1.features) & set(d2.features)
        total = set(d1.features) | set(d2.features)

        if not total:
            return 0.0

        return len(common) / len(total)

    def all_domains(self) -> List[Domain]:
        """Get all domains."""
        return list(self._domains.values())


# =============================================================================
# KNOWLEDGE EXTRACTOR
# =============================================================================

class KnowledgeExtractor:
    """Extract transferable knowledge."""

    def __init__(self):
        self._knowledge_bases: Dict[str, KnowledgeBase] = {}

    def extract(
        self,
        domain: Domain,
        examples: List[Dict[str, Any]]
    ) -> KnowledgeBase:
        """Extract knowledge from domain."""
        # Extract feature statistics
        features = {}
        for feat in domain.features:
            values = [ex.get(feat) for ex in examples if feat in ex]
            if values:
                numeric_values = [v for v in values if isinstance(v, (int, float))]
                if numeric_values:
                    features[feat] = {
                        "mean": sum(numeric_values) / len(numeric_values),
                        "min": min(numeric_values),
                        "max": max(numeric_values)
                    }
                else:
                    from collections import Counter
                    features[feat] = dict(Counter(values))

        # Extract patterns
        patterns = []
        if len(examples) >= 2:
            # Simple co-occurrence pattern
            for i in range(min(5, len(examples))):
                patterns.append(examples[i])

        kb = KnowledgeBase(
            source_domain=domain.name,
            features=features,
            patterns=patterns
        )

        self._knowledge_bases[kb.kb_id] = kb
        return kb

    def get(self, kb_id: str) -> Optional[KnowledgeBase]:
        """Get knowledge base."""
        return self._knowledge_bases.get(kb_id)


# =============================================================================
# DOMAIN ADAPTER
# =============================================================================

class DomainAdapter:
    """Adapt between domains."""

    def __init__(self, domain_manager: DomainManager):
        self._domain_mgr = domain_manager
        self._mappings: Dict[str, DomainMapping] = {}

    def create_mapping(
        self,
        source: str,
        target: str
    ) -> DomainMapping:
        """Create domain mapping."""
        s_domain = self._domain_mgr.get(source)
        t_domain = self._domain_mgr.get(target)

        feature_mapping = {}

        if s_domain and t_domain:
            # Map common features
            for s_feat in s_domain.features:
                if s_feat in t_domain.features:
                    feature_mapping[s_feat] = s_feat
                else:
                    # Try to find similar feature
                    for t_feat in t_domain.features:
                        if s_feat.lower() in t_feat.lower() or t_feat.lower() in s_feat.lower():
                            feature_mapping[s_feat] = t_feat
                            break

        similarity = self._domain_mgr.compute_similarity(source, target)

        mapping = DomainMapping(
            source_domain=source,
            target_domain=target,
            feature_mapping=feature_mapping,
            similarity=similarity
        )

        key = f"{source}_{target}"
        self._mappings[key] = mapping
        return mapping

    def adapt_example(
        self,
        example: Dict[str, Any],
        mapping: DomainMapping
    ) -> Dict[str, Any]:
        """Adapt an example to target domain."""
        adapted = {}

        for s_feat, value in example.items():
            t_feat = mapping.feature_mapping.get(s_feat)
            if t_feat:
                adapted[t_feat] = value

        return adapted

    def get_mapping(self, source: str, target: str) -> Optional[DomainMapping]:
        """Get domain mapping."""
        key = f"{source}_{target}"
        return self._mappings.get(key)


# =============================================================================
# FINE TUNER
# =============================================================================

class FineTuner:
    """Fine-tune transferred knowledge."""

    def __init__(self):
        self._fine_tuned: Dict[str, Dict[str, Any]] = {}

    def fine_tune(
        self,
        knowledge: KnowledgeBase,
        target_examples: List[Dict[str, Any]],
        learning_rate: float = 0.1,
        iterations: int = 10
    ) -> KnowledgeBase:
        """Fine-tune knowledge for target domain."""
        # Adjust feature weights based on target examples
        new_weights = knowledge.weights.copy()

        for feat, stats in knowledge.features.items():
            if isinstance(stats, dict) and "mean" in stats:
                # Numeric feature - adjust based on target
                target_values = [
                    ex.get(feat) for ex in target_examples
                    if feat in ex and isinstance(ex.get(feat), (int, float))
                ]

                if target_values:
                    target_mean = sum(target_values) / len(target_values)
                    source_mean = stats["mean"]

                    # Adjust weight based on distribution shift
                    shift = abs(target_mean - source_mean) / (source_mean + 1e-6)
                    new_weights[feat] = max(0.1, 1.0 - shift * learning_rate)

        fine_tuned = KnowledgeBase(
            source_domain=knowledge.source_domain,
            features=knowledge.features,
            weights=new_weights,
            patterns=knowledge.patterns
        )

        self._fine_tuned[fine_tuned.kb_id] = fine_tuned.__dict__
        return fine_tuned


# =============================================================================
# KNOWLEDGE DISTILLER
# =============================================================================

class KnowledgeDistiller:
    """Distill knowledge from teacher to student."""

    def __init__(self):
        self._distillation_results: Dict[str, Dict[str, Any]] = {}

    def distill(
        self,
        teacher_knowledge: KnowledgeBase,
        config: DistillationConfig
    ) -> KnowledgeBase:
        """Distill knowledge."""
        # Soften teacher's patterns using temperature
        softened_patterns = []

        for pattern in teacher_knowledge.patterns:
            soft_pattern = {}
            for key, value in pattern.items():
                if isinstance(value, (int, float)):
                    # Apply temperature scaling
                    soft_pattern[key] = value / config.temperature
                else:
                    soft_pattern[key] = value
            softened_patterns.append(soft_pattern)

        # Create student knowledge base
        student_kb = KnowledgeBase(
            source_domain=teacher_knowledge.source_domain,
            features=teacher_knowledge.features,
            weights={k: v * config.alpha for k, v in teacher_knowledge.weights.items()},
            patterns=softened_patterns
        )

        self._distillation_results[student_kb.kb_id] = {
            "teacher": teacher_knowledge.kb_id,
            "temperature": config.temperature,
            "alpha": config.alpha
        }

        return student_kb


# =============================================================================
# TRANSFER EVALUATOR
# =============================================================================

class TransferEvaluator:
    """Evaluate transfer learning."""

    def evaluate(
        self,
        source_domain: str,
        target_domain: str,
        performance_before: float,
        performance_after: float
    ) -> TransferResult:
        """Evaluate transfer."""
        transfer_gain = performance_after - performance_before

        if transfer_gain > 0.05:
            quality = TransferQuality.POSITIVE
        elif transfer_gain < -0.05:
            quality = TransferQuality.NEGATIVE
        else:
            quality = TransferQuality.NEUTRAL

        return TransferResult(
            source_domain=source_domain,
            target_domain=target_domain,
            quality=quality,
            performance_before=performance_before,
            performance_after=performance_after,
            transfer_gain=transfer_gain
        )

    def should_transfer(
        self,
        domain_similarity: float,
        threshold: float = 0.3
    ) -> bool:
        """Determine if transfer is advisable."""
        return domain_similarity >= threshold


# =============================================================================
# TRANSFER LEARNER
# =============================================================================

class TransferLearner:
    """
    Transfer Learner for BAEL.

    Advanced transfer learning and knowledge transfer.
    """

    def __init__(self):
        self._domain_mgr = DomainManager()
        self._extractor = KnowledgeExtractor()
        self._adapter = DomainAdapter(self._domain_mgr)
        self._fine_tuner = FineTuner()
        self._distiller = KnowledgeDistiller()
        self._evaluator = TransferEvaluator()
        self._transfer_history: List[TransferResult] = []

    # -------------------------------------------------------------------------
    # DOMAINS
    # -------------------------------------------------------------------------

    def add_domain(
        self,
        name: str,
        features: List[str],
        label_space: Optional[List[str]] = None
    ) -> Domain:
        """Add a domain."""
        return self._domain_mgr.add(name, features, label_space)

    def get_domain(self, name: str) -> Optional[Domain]:
        """Get a domain."""
        return self._domain_mgr.get(name)

    def domain_similarity(self, source: str, target: str) -> float:
        """Compute domain similarity."""
        return self._domain_mgr.compute_similarity(source, target)

    # -------------------------------------------------------------------------
    # KNOWLEDGE EXTRACTION
    # -------------------------------------------------------------------------

    def extract_knowledge(
        self,
        domain_name: str,
        examples: List[Dict[str, Any]]
    ) -> Optional[KnowledgeBase]:
        """Extract knowledge from domain."""
        domain = self._domain_mgr.get(domain_name)
        if not domain:
            return None

        return self._extractor.extract(domain, examples)

    # -------------------------------------------------------------------------
    # DOMAIN ADAPTATION
    # -------------------------------------------------------------------------

    def create_mapping(self, source: str, target: str) -> DomainMapping:
        """Create domain mapping."""
        return self._adapter.create_mapping(source, target)

    def adapt_example(
        self,
        example: Dict[str, Any],
        source: str,
        target: str
    ) -> Dict[str, Any]:
        """Adapt example to target domain."""
        mapping = self._adapter.get_mapping(source, target)
        if not mapping:
            mapping = self.create_mapping(source, target)

        return self._adapter.adapt_example(example, mapping)

    # -------------------------------------------------------------------------
    # FINE-TUNING
    # -------------------------------------------------------------------------

    def fine_tune(
        self,
        knowledge: KnowledgeBase,
        target_examples: List[Dict[str, Any]],
        learning_rate: float = 0.1
    ) -> KnowledgeBase:
        """Fine-tune knowledge."""
        return self._fine_tuner.fine_tune(knowledge, target_examples, learning_rate)

    # -------------------------------------------------------------------------
    # KNOWLEDGE DISTILLATION
    # -------------------------------------------------------------------------

    def distill(
        self,
        teacher_knowledge: KnowledgeBase,
        temperature: float = 3.0,
        alpha: float = 0.5
    ) -> KnowledgeBase:
        """Distill knowledge."""
        config = DistillationConfig(
            temperature=temperature,
            alpha=alpha
        )
        return self._distiller.distill(teacher_knowledge, config)

    # -------------------------------------------------------------------------
    # TRANSFER
    # -------------------------------------------------------------------------

    def transfer(
        self,
        source: str,
        target: str,
        source_examples: List[Dict[str, Any]],
        target_examples: List[Dict[str, Any]],
        strategy: TransferStrategy = TransferStrategy.FINE_TUNING
    ) -> TransferResult:
        """Perform transfer learning."""
        # Baseline performance
        baseline = self._estimate_performance(target_examples, None)

        # Extract knowledge from source
        knowledge = self.extract_knowledge(source, source_examples)
        if not knowledge:
            return TransferResult(
                source_domain=source,
                target_domain=target,
                quality=TransferQuality.NEGATIVE
            )

        # Apply strategy
        if strategy == TransferStrategy.FINE_TUNING:
            adapted_knowledge = self.fine_tune(knowledge, target_examples)
        elif strategy == TransferStrategy.KNOWLEDGE_DISTILLATION:
            adapted_knowledge = self.distill(knowledge)
        else:
            adapted_knowledge = knowledge

        # Performance after transfer
        after_performance = self._estimate_performance(target_examples, adapted_knowledge)

        # Evaluate
        result = self._evaluator.evaluate(
            source, target, baseline, after_performance
        )
        result.strategy = strategy

        self._transfer_history.append(result)
        return result

    def _estimate_performance(
        self,
        examples: List[Dict[str, Any]],
        knowledge: Optional[KnowledgeBase]
    ) -> float:
        """Estimate performance (simplified)."""
        if not knowledge:
            return 0.5  # Random baseline

        # Knowledge-based estimation
        match_score = 0.0

        for example in examples:
            for pattern in knowledge.patterns:
                matches = sum(
                    1 for k, v in pattern.items()
                    if example.get(k) == v
                )
                match_score += matches / max(len(pattern), 1)

        return min(1.0, 0.5 + match_score / max(len(examples), 1))

    # -------------------------------------------------------------------------
    # EVALUATION
    # -------------------------------------------------------------------------

    def should_transfer(self, source: str, target: str) -> bool:
        """Determine if transfer is advisable."""
        similarity = self.domain_similarity(source, target)
        return self._evaluator.should_transfer(similarity)

    def transfer_history(self) -> List[TransferResult]:
        """Get transfer history."""
        return self._transfer_history

    def best_source(
        self,
        target: str,
        candidates: List[str]
    ) -> Optional[str]:
        """Find best source domain for transfer."""
        if not candidates:
            return None

        similarities = {
            c: self.domain_similarity(c, target)
            for c in candidates
        }

        return max(candidates, key=lambda c: similarities[c])


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Transfer Learner."""
    print("=" * 70)
    print("BAEL - TRANSFER LEARNER DEMO")
    print("Advanced Transfer Learning and Knowledge Transfer")
    print("=" * 70)
    print()

    learner = TransferLearner()

    # 1. Add Domains
    print("1. ADD DOMAINS:")
    print("-" * 40)

    learner.add_domain(
        "sentiment_reviews",
        features=["text", "rating", "helpful_votes"],
        label_space=["positive", "negative"]
    )
    learner.add_domain(
        "sentiment_tweets",
        features=["text", "likes", "retweets"],
        label_space=["positive", "negative"]
    )
    learner.add_domain(
        "product_classification",
        features=["title", "description", "price"],
        label_space=["electronics", "clothing", "food"]
    )

    print("   Added: sentiment_reviews, sentiment_tweets, product_classification")
    print()

    # 2. Domain Similarity
    print("2. DOMAIN SIMILARITY:")
    print("-" * 40)

    sim1 = learner.domain_similarity("sentiment_reviews", "sentiment_tweets")
    sim2 = learner.domain_similarity("sentiment_reviews", "product_classification")

    print(f"   reviews ↔ tweets: {sim1:.2f}")
    print(f"   reviews ↔ products: {sim2:.2f}")
    print()

    # 3. Should Transfer?
    print("3. SHOULD TRANSFER?:")
    print("-" * 40)

    should1 = learner.should_transfer("sentiment_reviews", "sentiment_tweets")
    should2 = learner.should_transfer("sentiment_reviews", "product_classification")

    print(f"   reviews → tweets: {should1}")
    print(f"   reviews → products: {should2}")
    print()

    # 4. Extract Knowledge
    print("4. EXTRACT KNOWLEDGE:")
    print("-" * 40)

    source_examples = [
        {"text": "great product", "rating": 5, "helpful_votes": 10},
        {"text": "terrible quality", "rating": 1, "helpful_votes": 5},
        {"text": "average", "rating": 3, "helpful_votes": 2},
    ]

    knowledge = learner.extract_knowledge("sentiment_reviews", source_examples)
    if knowledge:
        print(f"   Extracted from: {knowledge.source_domain}")
        print(f"   Features: {list(knowledge.features.keys())}")
        print(f"   Patterns: {len(knowledge.patterns)}")
    print()

    # 5. Create Domain Mapping
    print("5. CREATE DOMAIN MAPPING:")
    print("-" * 40)

    mapping = learner.create_mapping("sentiment_reviews", "sentiment_tweets")
    print(f"   Source: {mapping.source_domain}")
    print(f"   Target: {mapping.target_domain}")
    print(f"   Feature mapping: {mapping.feature_mapping}")
    print(f"   Similarity: {mapping.similarity:.2f}")
    print()

    # 6. Adapt Example
    print("6. ADAPT EXAMPLE:")
    print("-" * 40)

    original = {"text": "love it!", "rating": 5, "helpful_votes": 20}
    adapted = learner.adapt_example(original, "sentiment_reviews", "sentiment_tweets")

    print(f"   Original: {original}")
    print(f"   Adapted: {adapted}")
    print()

    # 7. Fine-Tune
    print("7. FINE-TUNE:")
    print("-" * 40)

    target_examples = [
        {"text": "awesome!", "likes": 100, "retweets": 50},
        {"text": "hate it", "likes": 10, "retweets": 5},
    ]

    if knowledge:
        fine_tuned = learner.fine_tune(knowledge, target_examples)
        print(f"   Original weights: {knowledge.weights}")
        print(f"   Fine-tuned weights: {fine_tuned.weights}")
    print()

    # 8. Knowledge Distillation
    print("8. KNOWLEDGE DISTILLATION:")
    print("-" * 40)

    if knowledge:
        distilled = learner.distill(knowledge, temperature=3.0, alpha=0.5)
        print(f"   Teacher patterns: {len(knowledge.patterns)}")
        print(f"   Student patterns: {len(distilled.patterns)}")
    print()

    # 9. Full Transfer
    print("9. FULL TRANSFER:")
    print("-" * 40)

    result = learner.transfer(
        "sentiment_reviews",
        "sentiment_tweets",
        source_examples,
        target_examples,
        TransferStrategy.FINE_TUNING
    )

    print(f"   Strategy: {result.strategy.value}")
    print(f"   Quality: {result.quality.value}")
    print(f"   Before: {result.performance_before:.2f}")
    print(f"   After: {result.performance_after:.2f}")
    print(f"   Gain: {result.transfer_gain:+.2f}")
    print()

    # 10. Best Source Domain
    print("10. BEST SOURCE DOMAIN:")
    print("-" * 40)

    candidates = ["sentiment_reviews", "product_classification"]
    best = learner.best_source("sentiment_tweets", candidates)
    print(f"   Target: sentiment_tweets")
    print(f"   Candidates: {candidates}")
    print(f"   Best source: {best}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Transfer Learner Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())

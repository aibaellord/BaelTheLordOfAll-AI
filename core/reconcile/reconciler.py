#!/usr/bin/env python3
"""
BAEL - Reconciliation Engine
Advanced data reconciliation for AI agent operations.

Features:
- Data comparison
- Record matching
- Discrepancy detection
- Automatic reconciliation
- Manual review queues
- Reconciliation rules
- Exception handling
- Audit trails
- Reporting
- Schedule support
"""

import asyncio
import copy
import hashlib
import json
import threading
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

class ReconciliationStatus(Enum):
    """Reconciliation status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    MATCHED = "matched"
    MISMATCHED = "mismatched"
    UNMATCHED = "unmatched"
    RECONCILED = "reconciled"
    EXCEPTION = "exception"


class MatchType(Enum):
    """Match types."""
    EXACT = "exact"
    FUZZY = "fuzzy"
    PARTIAL = "partial"
    NONE = "none"


class DiscrepancyType(Enum):
    """Discrepancy types."""
    MISSING_SOURCE = "missing_source"
    MISSING_TARGET = "missing_target"
    VALUE_MISMATCH = "value_mismatch"
    TYPE_MISMATCH = "type_mismatch"
    DUPLICATE = "duplicate"


class ResolutionAction(Enum):
    """Resolution actions."""
    AUTO_ACCEPT_SOURCE = "auto_accept_source"
    AUTO_ACCEPT_TARGET = "auto_accept_target"
    MANUAL_REVIEW = "manual_review"
    IGNORE = "ignore"
    ESCALATE = "escalate"


class ReconciliationMode(Enum):
    """Reconciliation modes."""
    ONE_TO_ONE = "one_to_one"
    ONE_TO_MANY = "one_to_many"
    MANY_TO_MANY = "many_to_many"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class RecordPair:
    """Pair of records to reconcile."""
    pair_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_record: Dict[str, Any] = field(default_factory=dict)
    target_record: Dict[str, Any] = field(default_factory=dict)
    source_key: str = ""
    target_key: str = ""
    match_score: float = 0.0
    match_type: MatchType = MatchType.NONE
    status: ReconciliationStatus = ReconciliationStatus.PENDING


@dataclass
class Discrepancy:
    """A discrepancy between records."""
    discrepancy_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    pair_id: str = ""
    field_name: str = ""
    discrepancy_type: DiscrepancyType = DiscrepancyType.VALUE_MISMATCH
    source_value: Any = None
    target_value: Any = None
    severity: str = "medium"
    resolution: Optional[ResolutionAction] = None
    resolved_value: Any = None
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None


@dataclass
class ReconciliationRule:
    """Rule for reconciliation."""
    rule_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    field_name: str = ""
    tolerance: float = 0.0
    tolerance_type: str = "absolute"  # absolute, percentage
    action: ResolutionAction = ResolutionAction.MANUAL_REVIEW
    priority: int = 0


@dataclass
class ReconciliationConfig:
    """Reconciliation configuration."""
    name: str = "default"
    source_name: str = "source"
    target_name: str = "target"
    key_fields: List[str] = field(default_factory=list)
    compare_fields: List[str] = field(default_factory=list)
    mode: ReconciliationMode = ReconciliationMode.ONE_TO_ONE
    fuzzy_threshold: float = 0.8
    auto_reconcile: bool = True


@dataclass
class ReconciliationResult:
    """Result of reconciliation."""
    result_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    config_name: str = ""
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    total_source: int = 0
    total_target: int = 0
    matched: int = 0
    mismatched: int = 0
    unmatched_source: int = 0
    unmatched_target: int = 0
    auto_resolved: int = 0
    manual_pending: int = 0
    discrepancies: List[Discrepancy] = field(default_factory=list)
    pairs: List[RecordPair] = field(default_factory=list)


@dataclass
class AuditEntry:
    """Audit trail entry."""
    audit_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    result_id: str = ""
    action: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    user: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


# =============================================================================
# MATCHERS
# =============================================================================

class RecordMatcher(ABC):
    """Base record matcher."""

    @abstractmethod
    def match(
        self,
        source: Dict[str, Any],
        target: Dict[str, Any],
        key_fields: List[str]
    ) -> Tuple[MatchType, float]:
        """Match two records."""
        pass


class ExactMatcher(RecordMatcher):
    """Exact match on key fields."""

    def match(
        self,
        source: Dict[str, Any],
        target: Dict[str, Any],
        key_fields: List[str]
    ) -> Tuple[MatchType, float]:
        for field in key_fields:
            source_val = source.get(field)
            target_val = target.get(field)

            if source_val != target_val:
                return (MatchType.NONE, 0.0)

        return (MatchType.EXACT, 1.0)


class FuzzyMatcher(RecordMatcher):
    """Fuzzy match on key fields."""

    def __init__(self, threshold: float = 0.8):
        self.threshold = threshold

    def match(
        self,
        source: Dict[str, Any],
        target: Dict[str, Any],
        key_fields: List[str]
    ) -> Tuple[MatchType, float]:
        if not key_fields:
            return (MatchType.NONE, 0.0)

        total_score = 0.0

        for field in key_fields:
            source_val = str(source.get(field, ""))
            target_val = str(target.get(field, ""))

            score = self._similarity(source_val, target_val)
            total_score += score

        avg_score = total_score / len(key_fields)

        if avg_score >= 1.0:
            return (MatchType.EXACT, 1.0)
        elif avg_score >= self.threshold:
            return (MatchType.FUZZY, avg_score)
        elif avg_score >= 0.5:
            return (MatchType.PARTIAL, avg_score)

        return (MatchType.NONE, avg_score)

    def _similarity(self, a: str, b: str) -> float:
        """Compute string similarity."""
        if a == b:
            return 1.0
        if not a or not b:
            return 0.0

        # Simple Jaccard similarity on characters
        set_a = set(a.lower())
        set_b = set(b.lower())

        intersection = len(set_a & set_b)
        union = len(set_a | set_b)

        return intersection / union if union > 0 else 0.0


# =============================================================================
# COMPARATORS
# =============================================================================

class FieldComparator(ABC):
    """Base field comparator."""

    @abstractmethod
    def compare(
        self,
        source_value: Any,
        target_value: Any,
        tolerance: float = 0.0
    ) -> Tuple[bool, Optional[DiscrepancyType]]:
        """Compare field values."""
        pass


class ExactComparator(FieldComparator):
    """Exact field comparison."""

    def compare(
        self,
        source_value: Any,
        target_value: Any,
        tolerance: float = 0.0
    ) -> Tuple[bool, Optional[DiscrepancyType]]:
        if source_value == target_value:
            return (True, None)

        if type(source_value) != type(target_value):
            return (False, DiscrepancyType.TYPE_MISMATCH)

        return (False, DiscrepancyType.VALUE_MISMATCH)


class NumericComparator(FieldComparator):
    """Numeric comparison with tolerance."""

    def compare(
        self,
        source_value: Any,
        target_value: Any,
        tolerance: float = 0.0
    ) -> Tuple[bool, Optional[DiscrepancyType]]:
        try:
            source_num = float(source_value) if source_value is not None else 0.0
            target_num = float(target_value) if target_value is not None else 0.0

            diff = abs(source_num - target_num)

            if diff <= tolerance:
                return (True, None)

            return (False, DiscrepancyType.VALUE_MISMATCH)
        except (TypeError, ValueError):
            return (False, DiscrepancyType.TYPE_MISMATCH)


class DateComparator(FieldComparator):
    """Date comparison."""

    def compare(
        self,
        source_value: Any,
        target_value: Any,
        tolerance: float = 0.0
    ) -> Tuple[bool, Optional[DiscrepancyType]]:
        try:
            if isinstance(source_value, str):
                source_date = datetime.fromisoformat(source_value)
            elif isinstance(source_value, datetime):
                source_date = source_value
            else:
                return (False, DiscrepancyType.TYPE_MISMATCH)

            if isinstance(target_value, str):
                target_date = datetime.fromisoformat(target_value)
            elif isinstance(target_value, datetime):
                target_date = target_value
            else:
                return (False, DiscrepancyType.TYPE_MISMATCH)

            diff = abs((source_date - target_date).total_seconds())

            if diff <= tolerance:
                return (True, None)

            return (False, DiscrepancyType.VALUE_MISMATCH)
        except Exception:
            return (False, DiscrepancyType.TYPE_MISMATCH)


# =============================================================================
# RESOLVERS
# =============================================================================

class DiscrepancyResolver(ABC):
    """Base discrepancy resolver."""

    @abstractmethod
    def resolve(
        self,
        discrepancy: Discrepancy,
        source_record: Dict[str, Any],
        target_record: Dict[str, Any]
    ) -> Tuple[bool, Any]:
        """Resolve a discrepancy."""
        pass


class AcceptSourceResolver(DiscrepancyResolver):
    """Accept source value."""

    def resolve(
        self,
        discrepancy: Discrepancy,
        source_record: Dict[str, Any],
        target_record: Dict[str, Any]
    ) -> Tuple[bool, Any]:
        return (True, discrepancy.source_value)


class AcceptTargetResolver(DiscrepancyResolver):
    """Accept target value."""

    def resolve(
        self,
        discrepancy: Discrepancy,
        source_record: Dict[str, Any],
        target_record: Dict[str, Any]
    ) -> Tuple[bool, Any]:
        return (True, discrepancy.target_value)


class RuleBasedResolver(DiscrepancyResolver):
    """Rule-based resolver."""

    def __init__(self, rules: List[ReconciliationRule]):
        self.rules = sorted(rules, key=lambda r: -r.priority)

    def resolve(
        self,
        discrepancy: Discrepancy,
        source_record: Dict[str, Any],
        target_record: Dict[str, Any]
    ) -> Tuple[bool, Any]:
        for rule in self.rules:
            if rule.field_name == discrepancy.field_name or rule.field_name == "*":
                if rule.action == ResolutionAction.AUTO_ACCEPT_SOURCE:
                    return (True, discrepancy.source_value)
                elif rule.action == ResolutionAction.AUTO_ACCEPT_TARGET:
                    return (True, discrepancy.target_value)
                elif rule.action == ResolutionAction.IGNORE:
                    return (True, None)
                elif rule.action == ResolutionAction.MANUAL_REVIEW:
                    return (False, None)

        return (False, None)


# =============================================================================
# RECONCILIATION ENGINE
# =============================================================================

class ReconciliationEngine:
    """
    Reconciliation Engine for BAEL.

    Advanced data reconciliation.
    """

    def __init__(self):
        self._configs: Dict[str, ReconciliationConfig] = {}
        self._rules: Dict[str, List[ReconciliationRule]] = defaultdict(list)
        self._results: Dict[str, ReconciliationResult] = {}
        self._audit: List[AuditEntry] = []
        self._review_queue: List[Discrepancy] = []
        self._matcher = FuzzyMatcher()
        self._comparators: Dict[str, FieldComparator] = {
            "default": ExactComparator(),
            "numeric": NumericComparator(),
            "date": DateComparator()
        }
        self._lock = threading.RLock()

    # -------------------------------------------------------------------------
    # CONFIGURATION
    # -------------------------------------------------------------------------

    def create_config(
        self,
        name: str,
        key_fields: List[str],
        compare_fields: Optional[List[str]] = None,
        mode: ReconciliationMode = ReconciliationMode.ONE_TO_ONE,
        **kwargs: Any
    ) -> ReconciliationConfig:
        """Create reconciliation configuration."""
        config = ReconciliationConfig(
            name=name,
            key_fields=key_fields,
            compare_fields=compare_fields or [],
            mode=mode,
            **kwargs
        )

        with self._lock:
            self._configs[name] = config

        return config

    def add_rule(
        self,
        config_name: str,
        field_name: str,
        action: ResolutionAction,
        tolerance: float = 0.0,
        priority: int = 0
    ) -> ReconciliationRule:
        """Add reconciliation rule."""
        rule = ReconciliationRule(
            name=f"rule_{field_name}",
            field_name=field_name,
            action=action,
            tolerance=tolerance,
            priority=priority
        )

        with self._lock:
            self._rules[config_name].append(rule)

        return rule

    # -------------------------------------------------------------------------
    # RECONCILIATION
    # -------------------------------------------------------------------------

    async def reconcile(
        self,
        config_name: str,
        source_data: List[Dict[str, Any]],
        target_data: List[Dict[str, Any]]
    ) -> ReconciliationResult:
        """Perform reconciliation."""
        config = self._configs.get(config_name)
        if not config:
            config = ReconciliationConfig(name=config_name)

        result = ReconciliationResult(
            config_name=config_name,
            total_source=len(source_data),
            total_target=len(target_data)
        )

        # Build indexes
        source_index = self._build_index(source_data, config.key_fields)
        target_index = self._build_index(target_data, config.key_fields)

        matched_targets = set()

        # Match source to target
        for source_key, source_records in source_index.items():
            for source_record in source_records:
                best_match = None
                best_score = 0.0
                best_target_key = None

                # Find best matching target
                for target_key, target_records in target_index.items():
                    for target_record in target_records:
                        match_type, score = self._matcher.match(
                            source_record,
                            target_record,
                            config.key_fields
                        )

                        if score > best_score:
                            best_score = score
                            best_match = target_record
                            best_target_key = target_key

                if best_match and best_score >= config.fuzzy_threshold:
                    # Create pair
                    pair = RecordPair(
                        source_record=source_record,
                        target_record=best_match,
                        source_key=source_key,
                        target_key=best_target_key or "",
                        match_score=best_score,
                        match_type=MatchType.EXACT if best_score >= 1.0 else MatchType.FUZZY
                    )

                    # Compare fields
                    discrepancies = self._compare_records(
                        source_record,
                        best_match,
                        config.compare_fields or list(source_record.keys()),
                        pair.pair_id
                    )

                    if discrepancies:
                        pair.status = ReconciliationStatus.MISMATCHED
                        result.mismatched += 1
                        result.discrepancies.extend(discrepancies)

                        # Auto-resolve if enabled
                        if config.auto_reconcile:
                            resolved = await self._auto_resolve(
                                discrepancies,
                                source_record,
                                best_match,
                                config_name
                            )
                            result.auto_resolved += resolved
                            result.manual_pending += len(discrepancies) - resolved
                    else:
                        pair.status = ReconciliationStatus.MATCHED
                        result.matched += 1

                    result.pairs.append(pair)
                    matched_targets.add(best_target_key)
                else:
                    # Unmatched source
                    pair = RecordPair(
                        source_record=source_record,
                        source_key=source_key,
                        status=ReconciliationStatus.UNMATCHED
                    )
                    result.pairs.append(pair)
                    result.unmatched_source += 1

                    # Create missing target discrepancy
                    disc = Discrepancy(
                        pair_id=pair.pair_id,
                        field_name="_record",
                        discrepancy_type=DiscrepancyType.MISSING_TARGET,
                        source_value=source_record
                    )
                    result.discrepancies.append(disc)

        # Find unmatched targets
        for target_key, target_records in target_index.items():
            if target_key not in matched_targets:
                for target_record in target_records:
                    pair = RecordPair(
                        target_record=target_record,
                        target_key=target_key,
                        status=ReconciliationStatus.UNMATCHED
                    )
                    result.pairs.append(pair)
                    result.unmatched_target += 1

                    disc = Discrepancy(
                        pair_id=pair.pair_id,
                        field_name="_record",
                        discrepancy_type=DiscrepancyType.MISSING_SOURCE,
                        target_value=target_record
                    )
                    result.discrepancies.append(disc)

        result.completed_at = datetime.utcnow()

        with self._lock:
            self._results[result.result_id] = result

            # Add unresolved to review queue
            for disc in result.discrepancies:
                if disc.resolution is None:
                    self._review_queue.append(disc)

        # Audit
        self._add_audit(result.result_id, "reconciliation_completed", {
            "matched": result.matched,
            "mismatched": result.mismatched,
            "discrepancies": len(result.discrepancies)
        })

        return result

    def _build_index(
        self,
        records: List[Dict[str, Any]],
        key_fields: List[str]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Build index from records."""
        index = defaultdict(list)

        for record in records:
            key_values = [str(record.get(f, "")) for f in key_fields]
            key = "|".join(key_values)
            index[key].append(record)

        return index

    def _compare_records(
        self,
        source: Dict[str, Any],
        target: Dict[str, Any],
        fields: List[str],
        pair_id: str
    ) -> List[Discrepancy]:
        """Compare two records."""
        discrepancies = []

        for field in fields:
            source_val = source.get(field)
            target_val = target.get(field)

            # Get appropriate comparator
            comparator = self._get_comparator(field, source_val)

            match, disc_type = comparator.compare(source_val, target_val)

            if not match and disc_type:
                discrepancies.append(Discrepancy(
                    pair_id=pair_id,
                    field_name=field,
                    discrepancy_type=disc_type,
                    source_value=source_val,
                    target_value=target_val
                ))

        return discrepancies

    def _get_comparator(self, field: str, value: Any) -> FieldComparator:
        """Get comparator for field."""
        if isinstance(value, (int, float)):
            return self._comparators.get("numeric", self._comparators["default"])
        elif isinstance(value, datetime):
            return self._comparators.get("date", self._comparators["default"])

        return self._comparators["default"]

    async def _auto_resolve(
        self,
        discrepancies: List[Discrepancy],
        source: Dict[str, Any],
        target: Dict[str, Any],
        config_name: str
    ) -> int:
        """Auto-resolve discrepancies."""
        rules = self._rules.get(config_name, [])
        resolver = RuleBasedResolver(rules)

        resolved_count = 0

        for disc in discrepancies:
            success, value = resolver.resolve(disc, source, target)

            if success:
                disc.resolution = ResolutionAction.AUTO_ACCEPT_SOURCE if value == disc.source_value else ResolutionAction.AUTO_ACCEPT_TARGET
                disc.resolved_value = value
                disc.resolved_at = datetime.utcnow()
                disc.resolved_by = "auto"
                resolved_count += 1

        return resolved_count

    # -------------------------------------------------------------------------
    # REVIEW QUEUE
    # -------------------------------------------------------------------------

    def get_review_queue(self, limit: int = 100) -> List[Discrepancy]:
        """Get discrepancies pending review."""
        with self._lock:
            return self._review_queue[:limit]

    def resolve_discrepancy(
        self,
        discrepancy_id: str,
        action: ResolutionAction,
        resolved_value: Any,
        user: str = "unknown"
    ) -> bool:
        """Manually resolve a discrepancy."""
        with self._lock:
            for disc in self._review_queue:
                if disc.discrepancy_id == discrepancy_id:
                    disc.resolution = action
                    disc.resolved_value = resolved_value
                    disc.resolved_at = datetime.utcnow()
                    disc.resolved_by = user

                    self._review_queue.remove(disc)

                    self._add_audit("", "discrepancy_resolved", {
                        "discrepancy_id": discrepancy_id,
                        "action": action.value,
                        "user": user
                    })

                    return True

        return False

    # -------------------------------------------------------------------------
    # RESULTS
    # -------------------------------------------------------------------------

    def get_result(self, result_id: str) -> Optional[ReconciliationResult]:
        """Get reconciliation result."""
        with self._lock:
            return self._results.get(result_id)

    def list_results(self, limit: int = 100) -> List[ReconciliationResult]:
        """List recent results."""
        with self._lock:
            results = list(self._results.values())
            results.sort(key=lambda r: r.started_at, reverse=True)
            return results[:limit]

    def get_summary(self, result_id: str) -> Dict[str, Any]:
        """Get result summary."""
        result = self.get_result(result_id)

        if not result:
            return {}

        return {
            "result_id": result.result_id,
            "config_name": result.config_name,
            "started_at": result.started_at.isoformat(),
            "completed_at": result.completed_at.isoformat() if result.completed_at else None,
            "total_source": result.total_source,
            "total_target": result.total_target,
            "matched": result.matched,
            "mismatched": result.mismatched,
            "unmatched_source": result.unmatched_source,
            "unmatched_target": result.unmatched_target,
            "match_rate": result.matched / result.total_source if result.total_source > 0 else 0,
            "discrepancy_count": len(result.discrepancies),
            "auto_resolved": result.auto_resolved,
            "manual_pending": result.manual_pending
        }

    # -------------------------------------------------------------------------
    # AUDIT
    # -------------------------------------------------------------------------

    def _add_audit(
        self,
        result_id: str,
        action: str,
        details: Dict[str, Any],
        user: Optional[str] = None
    ) -> None:
        """Add audit entry."""
        entry = AuditEntry(
            result_id=result_id,
            action=action,
            details=details,
            user=user
        )

        with self._lock:
            self._audit.append(entry)

    def get_audit(
        self,
        result_id: Optional[str] = None,
        limit: int = 100
    ) -> List[AuditEntry]:
        """Get audit entries."""
        with self._lock:
            entries = self._audit

            if result_id:
                entries = [e for e in entries if e.result_id == result_id]

            entries = sorted(entries, key=lambda e: e.timestamp, reverse=True)
            return entries[:limit]

    # -------------------------------------------------------------------------
    # REPORTS
    # -------------------------------------------------------------------------

    def generate_report(self, result_id: str) -> Dict[str, Any]:
        """Generate reconciliation report."""
        result = self.get_result(result_id)

        if not result:
            return {}

        # Group discrepancies by type
        by_type = defaultdict(list)
        for disc in result.discrepancies:
            by_type[disc.discrepancy_type.value].append(disc)

        # Group by field
        by_field = defaultdict(list)
        for disc in result.discrepancies:
            by_field[disc.field_name].append(disc)

        return {
            "summary": self.get_summary(result_id),
            "discrepancies_by_type": {
                k: len(v) for k, v in by_type.items()
            },
            "discrepancies_by_field": {
                k: len(v) for k, v in by_field.items()
            },
            "unresolved_count": len([
                d for d in result.discrepancies
                if d.resolution is None
            ]),
            "resolved_count": len([
                d for d in result.discrepancies
                if d.resolution is not None
            ])
        }

    # -------------------------------------------------------------------------
    # STATISTICS
    # -------------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics."""
        with self._lock:
            total_results = len(self._results)
            total_discrepancies = sum(
                len(r.discrepancies) for r in self._results.values()
            )
            pending_review = len(self._review_queue)

            return {
                "total_reconciliations": total_results,
                "total_discrepancies": total_discrepancies,
                "pending_review": pending_review,
                "configs": len(self._configs),
                "rules": sum(len(r) for r in self._rules.values())
            }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Reconciliation Engine."""
    print("=" * 70)
    print("BAEL - RECONCILIATION ENGINE DEMO")
    print("Advanced Data Reconciliation for AI Agents")
    print("=" * 70)
    print()

    engine = ReconciliationEngine()

    # 1. Create Configuration
    print("1. CREATE CONFIGURATION:")
    print("-" * 40)

    config = engine.create_config(
        name="orders",
        key_fields=["order_id"],
        compare_fields=["amount", "status", "customer"]
    )

    print(f"   Config: {config.name}")
    print(f"   Key fields: {config.key_fields}")
    print(f"   Compare fields: {config.compare_fields}")
    print()

    # 2. Add Rules
    print("2. ADD RULES:")
    print("-" * 40)

    engine.add_rule(
        "orders",
        "amount",
        ResolutionAction.AUTO_ACCEPT_SOURCE,
        tolerance=0.01,
        priority=10
    )

    engine.add_rule(
        "orders",
        "status",
        ResolutionAction.MANUAL_REVIEW,
        priority=5
    )

    print("   Added amount rule (auto-accept source)")
    print("   Added status rule (manual review)")
    print()

    # 3. Sample Data
    print("3. SAMPLE DATA:")
    print("-" * 40)

    source_data = [
        {"order_id": "001", "amount": 100.00, "status": "shipped", "customer": "Alice"},
        {"order_id": "002", "amount": 200.00, "status": "pending", "customer": "Bob"},
        {"order_id": "003", "amount": 300.00, "status": "delivered", "customer": "Charlie"},
        {"order_id": "004", "amount": 400.00, "status": "processing", "customer": "David"}
    ]

    target_data = [
        {"order_id": "001", "amount": 100.00, "status": "shipped", "customer": "Alice"},
        {"order_id": "002", "amount": 200.01, "status": "shipped", "customer": "Bob"},  # Amount diff, status diff
        {"order_id": "003", "amount": 300.00, "status": "delivered", "customer": "Charles"},  # Customer diff
        {"order_id": "005", "amount": 500.00, "status": "new", "customer": "Eve"}  # New in target
    ]

    print(f"   Source records: {len(source_data)}")
    print(f"   Target records: {len(target_data)}")
    print()

    # 4. Run Reconciliation
    print("4. RUN RECONCILIATION:")
    print("-" * 40)

    result = await engine.reconcile("orders", source_data, target_data)

    print(f"   Result ID: {result.result_id[:8]}...")
    print(f"   Matched: {result.matched}")
    print(f"   Mismatched: {result.mismatched}")
    print(f"   Unmatched source: {result.unmatched_source}")
    print(f"   Unmatched target: {result.unmatched_target}")
    print(f"   Discrepancies: {len(result.discrepancies)}")
    print()

    # 5. Discrepancies
    print("5. DISCREPANCIES:")
    print("-" * 40)

    for disc in result.discrepancies[:5]:
        print(f"   {disc.field_name}: {disc.discrepancy_type.value}")
        print(f"     Source: {disc.source_value}")
        print(f"     Target: {disc.target_value}")
        if disc.resolution:
            print(f"     Resolution: {disc.resolution.value}")
    print()

    # 6. Review Queue
    print("6. REVIEW QUEUE:")
    print("-" * 40)

    queue = engine.get_review_queue()
    print(f"   Pending review: {len(queue)}")

    if queue:
        disc = queue[0]
        print(f"   First item: {disc.field_name}")

        # Resolve it
        engine.resolve_discrepancy(
            disc.discrepancy_id,
            ResolutionAction.AUTO_ACCEPT_SOURCE,
            disc.source_value,
            user="admin"
        )
        print("   Resolved first item")
    print()

    # 7. Summary
    print("7. RESULT SUMMARY:")
    print("-" * 40)

    summary = engine.get_summary(result.result_id)
    print(f"   Match rate: {summary['match_rate']:.1%}")
    print(f"   Auto resolved: {summary['auto_resolved']}")
    print(f"   Manual pending: {summary['manual_pending']}")
    print()

    # 8. Generate Report
    print("8. GENERATE REPORT:")
    print("-" * 40)

    report = engine.generate_report(result.result_id)
    print(f"   By type: {report['discrepancies_by_type']}")
    print(f"   By field: {report['discrepancies_by_field']}")
    print()

    # 9. Audit Trail
    print("9. AUDIT TRAIL:")
    print("-" * 40)

    audit = engine.get_audit(limit=5)
    for entry in audit:
        print(f"   {entry.action}: {entry.details}")
    print()

    # 10. Statistics
    print("10. ENGINE STATISTICS:")
    print("-" * 40)

    stats = engine.get_stats()
    print(f"   Total reconciliations: {stats['total_reconciliations']}")
    print(f"   Total discrepancies: {stats['total_discrepancies']}")
    print(f"   Pending review: {stats['pending_review']}")
    print(f"   Configs: {stats['configs']}")
    print(f"   Rules: {stats['rules']}")
    print()

    # 11. Matched Pairs
    print("11. MATCHED PAIRS:")
    print("-" * 40)

    for pair in result.pairs[:3]:
        print(f"   {pair.source_key}: {pair.status.value} "
              f"(score: {pair.match_score:.2f})")
    print()

    # 12. List Results
    print("12. LIST RESULTS:")
    print("-" * 40)

    results = engine.list_results()
    for r in results:
        print(f"   {r.result_id[:8]}...: {r.config_name} - {r.matched}/{r.total_source} matched")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Reconciliation Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())

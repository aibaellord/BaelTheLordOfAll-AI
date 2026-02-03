#!/usr/bin/env python3
"""
BAEL - Deontic Reasoner
Advanced normative and obligation reasoning.

Features:
- Obligation/permission/prohibition
- Normative rules
- Deontic logic
- Norm conflicts
- Duty derivation
- Compliance checking
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

class DeonticOperator(Enum):
    """Deontic modal operators."""
    OBLIGATION = "obligation"  # O - must
    PERMISSION = "permission"  # P - may
    PROHIBITION = "prohibition"  # F - must not
    FACULTATIVE = "facultative"  # neither obligatory nor forbidden


class NormType(Enum):
    """Types of norms."""
    REGULATIVE = "regulative"  # Regulate behavior
    CONSTITUTIVE = "constitutive"  # Define concepts
    PRESCRIPTIVE = "prescriptive"  # Prescribe actions
    PROCEDURAL = "procedural"  # Define procedures


class NormStatus(Enum):
    """Status of a norm."""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    REVOKED = "revoked"
    PENDING = "pending"


class ComplianceStatus(Enum):
    """Compliance status."""
    COMPLIANT = "compliant"
    VIOLATED = "violated"
    PENDING = "pending"
    EXCUSED = "excused"


class ConflictType(Enum):
    """Types of normative conflicts."""
    OBLIGATION_PROHIBITION = "obligation_prohibition"
    OBLIGATION_OBLIGATION = "obligation_obligation"
    PERMISSION_PROHIBITION = "permission_prohibition"


class ResolutionStrategy(Enum):
    """Conflict resolution strategies."""
    LEX_SUPERIOR = "lex_superior"  # Higher authority wins
    LEX_POSTERIOR = "lex_posterior"  # Later norm wins
    LEX_SPECIALIS = "lex_specialis"  # More specific wins
    PRIORITY = "priority"  # Explicit priority


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class Action:
    """An action that can be performed."""
    action_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    preconditions: List[str] = field(default_factory=list)
    effects: List[str] = field(default_factory=list)


@dataclass
class DeonticStatement:
    """A deontic statement (normative proposition)."""
    statement_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    operator: DeonticOperator = DeonticOperator.OBLIGATION
    agent: str = ""
    action_id: str = ""
    condition: str = ""
    deadline: Optional[datetime] = None


@dataclass
class Norm:
    """A normative rule."""
    norm_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    norm_type: NormType = NormType.REGULATIVE
    status: NormStatus = NormStatus.ACTIVE
    authority: str = ""
    priority: int = 0
    activation_condition: str = ""
    statements: List[str] = field(default_factory=list)
    created: datetime = field(default_factory=datetime.now)


@dataclass
class Duty:
    """A derived duty for an agent."""
    duty_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    agent: str = ""
    action_id: str = ""
    source_norm: str = ""
    operator: DeonticOperator = DeonticOperator.OBLIGATION
    deadline: Optional[datetime] = None
    fulfilled: bool = False


@dataclass
class Violation:
    """A norm violation."""
    violation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    duty_id: str = ""
    agent: str = ""
    norm_id: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    description: str = ""


@dataclass
class NormConflict:
    """A conflict between norms."""
    conflict_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    norm1_id: str = ""
    norm2_id: str = ""
    conflict_type: ConflictType = ConflictType.OBLIGATION_PROHIBITION
    resolution: Optional[str] = None
    winner_id: Optional[str] = None


# =============================================================================
# ACTION MANAGER
# =============================================================================

class ActionManager:
    """Manage actions."""

    def __init__(self):
        self._actions: Dict[str, Action] = {}
        self._by_name: Dict[str, str] = {}

    def create_action(
        self,
        name: str,
        description: str = "",
        preconditions: Optional[List[str]] = None,
        effects: Optional[List[str]] = None
    ) -> Action:
        """Create an action."""
        action = Action(
            name=name,
            description=description,
            preconditions=preconditions or [],
            effects=effects or []
        )

        self._actions[action.action_id] = action
        self._by_name[name] = action.action_id
        return action

    def get_action(self, action_id: str) -> Optional[Action]:
        """Get an action."""
        return self._actions.get(action_id)

    def get_by_name(self, name: str) -> Optional[Action]:
        """Get action by name."""
        action_id = self._by_name.get(name)
        return self._actions.get(action_id) if action_id else None

    def all_actions(self) -> List[Action]:
        """Get all actions."""
        return list(self._actions.values())


# =============================================================================
# NORM MANAGER
# =============================================================================

class NormManager:
    """Manage norms."""

    def __init__(self):
        self._norms: Dict[str, Norm] = {}
        self._statements: Dict[str, DeonticStatement] = {}
        self._by_type: Dict[NormType, Set[str]] = defaultdict(set)
        self._by_authority: Dict[str, Set[str]] = defaultdict(set)

    def create_norm(
        self,
        name: str,
        norm_type: NormType = NormType.REGULATIVE,
        authority: str = "",
        priority: int = 0,
        activation_condition: str = ""
    ) -> Norm:
        """Create a norm."""
        norm = Norm(
            name=name,
            norm_type=norm_type,
            authority=authority,
            priority=priority,
            activation_condition=activation_condition
        )

        self._norms[norm.norm_id] = norm
        self._by_type[norm_type].add(norm.norm_id)
        if authority:
            self._by_authority[authority].add(norm.norm_id)

        return norm

    def add_statement(
        self,
        norm_id: str,
        operator: DeonticOperator,
        agent: str,
        action_id: str,
        condition: str = "",
        deadline: Optional[datetime] = None
    ) -> Optional[DeonticStatement]:
        """Add a deontic statement to a norm."""
        norm = self._norms.get(norm_id)
        if not norm:
            return None

        statement = DeonticStatement(
            operator=operator,
            agent=agent,
            action_id=action_id,
            condition=condition,
            deadline=deadline
        )

        self._statements[statement.statement_id] = statement
        norm.statements.append(statement.statement_id)

        return statement

    def get_norm(self, norm_id: str) -> Optional[Norm]:
        """Get a norm."""
        return self._norms.get(norm_id)

    def get_statement(self, statement_id: str) -> Optional[DeonticStatement]:
        """Get a statement."""
        return self._statements.get(statement_id)

    def get_norm_statements(self, norm_id: str) -> List[DeonticStatement]:
        """Get all statements of a norm."""
        norm = self._norms.get(norm_id)
        if not norm:
            return []

        return [
            self._statements[sid]
            for sid in norm.statements
            if sid in self._statements
        ]

    def get_active_norms(self) -> List[Norm]:
        """Get all active norms."""
        return [
            n for n in self._norms.values()
            if n.status == NormStatus.ACTIVE
        ]

    def suspend_norm(self, norm_id: str) -> bool:
        """Suspend a norm."""
        norm = self._norms.get(norm_id)
        if norm:
            norm.status = NormStatus.SUSPENDED
            return True
        return False

    def revoke_norm(self, norm_id: str) -> bool:
        """Revoke a norm."""
        norm = self._norms.get(norm_id)
        if norm:
            norm.status = NormStatus.REVOKED
            return True
        return False


# =============================================================================
# DUTY DERIVER
# =============================================================================

class DutyDeriver:
    """Derive duties from norms."""

    def __init__(self, norm_manager: NormManager):
        self._norms = norm_manager
        self._duties: Dict[str, Duty] = {}
        self._by_agent: Dict[str, Set[str]] = defaultdict(set)

    def derive_duties(
        self,
        agent: str,
        context: Optional[Dict[str, Any]] = None
    ) -> List[Duty]:
        """Derive all applicable duties for an agent."""
        context = context or {}
        derived = []

        for norm in self._norms.get_active_norms():
            # Check activation condition
            if norm.activation_condition:
                if not self._evaluate_condition(norm.activation_condition, context):
                    continue

            # Process statements
            for statement in self._norms.get_norm_statements(norm.norm_id):
                # Check if applies to agent
                if statement.agent != agent and statement.agent != "*":
                    continue

                # Check condition
                if statement.condition:
                    if not self._evaluate_condition(statement.condition, context):
                        continue

                # Create duty
                duty = Duty(
                    agent=agent,
                    action_id=statement.action_id,
                    source_norm=norm.norm_id,
                    operator=statement.operator,
                    deadline=statement.deadline
                )

                self._duties[duty.duty_id] = duty
                self._by_agent[agent].add(duty.duty_id)
                derived.append(duty)

        return derived

    def _evaluate_condition(
        self,
        condition: str,
        context: Dict[str, Any]
    ) -> bool:
        """Evaluate a condition against context."""
        # Simple evaluation - check if condition variables exist and are truthy
        for key, value in context.items():
            condition = condition.replace(f"${key}", str(value))

        # Default to true if condition is empty or just a placeholder
        if not condition or "$" in condition:
            return True

        try:
            return bool(eval(condition, {"__builtins__": {}}, context))
        except Exception:
            return True

    def get_agent_duties(self, agent: str) -> List[Duty]:
        """Get all duties of an agent."""
        duty_ids = self._by_agent.get(agent, set())
        return [
            self._duties[did]
            for did in duty_ids
            if did in self._duties
        ]

    def get_obligations(self, agent: str) -> List[Duty]:
        """Get obligations for agent."""
        return [
            d for d in self.get_agent_duties(agent)
            if d.operator == DeonticOperator.OBLIGATION
        ]

    def get_prohibitions(self, agent: str) -> List[Duty]:
        """Get prohibitions for agent."""
        return [
            d for d in self.get_agent_duties(agent)
            if d.operator == DeonticOperator.PROHIBITION
        ]

    def get_permissions(self, agent: str) -> List[Duty]:
        """Get permissions for agent."""
        return [
            d for d in self.get_agent_duties(agent)
            if d.operator == DeonticOperator.PERMISSION
        ]

    def fulfill_duty(self, duty_id: str) -> bool:
        """Mark a duty as fulfilled."""
        duty = self._duties.get(duty_id)
        if duty:
            duty.fulfilled = True
            return True
        return False


# =============================================================================
# COMPLIANCE CHECKER
# =============================================================================

class ComplianceChecker:
    """Check compliance with norms."""

    def __init__(
        self,
        duty_deriver: DutyDeriver,
        action_manager: ActionManager
    ):
        self._duties = duty_deriver
        self._actions = action_manager
        self._violations: Dict[str, Violation] = {}
        self._action_log: Dict[str, List[Tuple[str, datetime]]] = defaultdict(list)

    def log_action(
        self,
        agent: str,
        action_id: str,
        timestamp: Optional[datetime] = None
    ) -> None:
        """Log an action performed by an agent."""
        timestamp = timestamp or datetime.now()
        self._action_log[agent].append((action_id, timestamp))

    def check_compliance(self, agent: str) -> Tuple[ComplianceStatus, List[Violation]]:
        """Check compliance for an agent."""
        violations = []

        duties = self._duties.get_agent_duties(agent)
        performed = set(aid for aid, _ in self._action_log.get(agent, []))

        for duty in duties:
            if duty.fulfilled:
                continue

            if duty.operator == DeonticOperator.OBLIGATION:
                # Check if obligation was fulfilled
                if duty.action_id not in performed:
                    # Check deadline
                    if duty.deadline and datetime.now() > duty.deadline:
                        violation = self._create_violation(
                            duty.duty_id, agent, duty.source_norm,
                            f"Failed to perform obligated action"
                        )
                        violations.append(violation)

            elif duty.operator == DeonticOperator.PROHIBITION:
                # Check if prohibited action was performed
                if duty.action_id in performed:
                    violation = self._create_violation(
                        duty.duty_id, agent, duty.source_norm,
                        f"Performed prohibited action"
                    )
                    violations.append(violation)

        if violations:
            return ComplianceStatus.VIOLATED, violations

        # Check if all obligations met
        obligations = self._duties.get_obligations(agent)
        all_met = all(
            o.fulfilled or o.action_id in performed
            for o in obligations
        )

        return ComplianceStatus.COMPLIANT if all_met else ComplianceStatus.PENDING, []

    def _create_violation(
        self,
        duty_id: str,
        agent: str,
        norm_id: str,
        description: str
    ) -> Violation:
        """Create a violation record."""
        violation = Violation(
            duty_id=duty_id,
            agent=agent,
            norm_id=norm_id,
            description=description
        )
        self._violations[violation.violation_id] = violation
        return violation

    def get_violations(self, agent: str) -> List[Violation]:
        """Get all violations for an agent."""
        return [
            v for v in self._violations.values()
            if v.agent == agent
        ]

    def is_action_permitted(
        self,
        agent: str,
        action_id: str
    ) -> bool:
        """Check if action is permitted for agent."""
        duties = self._duties.get_agent_duties(agent)

        # Check for prohibition
        for duty in duties:
            if duty.action_id == action_id:
                if duty.operator == DeonticOperator.PROHIBITION:
                    return False

        # Default to permitted
        return True

    def is_action_obligated(
        self,
        agent: str,
        action_id: str
    ) -> bool:
        """Check if action is obligated for agent."""
        obligations = self._duties.get_obligations(agent)
        return any(o.action_id == action_id for o in obligations)


# =============================================================================
# CONFLICT RESOLVER
# =============================================================================

class ConflictResolver:
    """Resolve normative conflicts."""

    def __init__(self, norm_manager: NormManager):
        self._norms = norm_manager
        self._conflicts: Dict[str, NormConflict] = {}

    def detect_conflicts(
        self,
        duties: List[Duty]
    ) -> List[NormConflict]:
        """Detect conflicts among duties."""
        conflicts = []

        # Group by action
        by_action: Dict[str, List[Duty]] = defaultdict(list)
        for duty in duties:
            by_action[duty.action_id].append(duty)

        # Check for conflicts
        for action_id, action_duties in by_action.items():
            if len(action_duties) < 2:
                continue

            operators = {d.operator for d in action_duties}

            # Obligation vs Prohibition
            if DeonticOperator.OBLIGATION in operators and \
               DeonticOperator.PROHIBITION in operators:

                obl = next(d for d in action_duties
                          if d.operator == DeonticOperator.OBLIGATION)
                proh = next(d for d in action_duties
                           if d.operator == DeonticOperator.PROHIBITION)

                conflict = NormConflict(
                    norm1_id=obl.source_norm,
                    norm2_id=proh.source_norm,
                    conflict_type=ConflictType.OBLIGATION_PROHIBITION
                )
                self._conflicts[conflict.conflict_id] = conflict
                conflicts.append(conflict)

        return conflicts

    def resolve_conflict(
        self,
        conflict: NormConflict,
        strategy: ResolutionStrategy = ResolutionStrategy.PRIORITY
    ) -> Optional[str]:
        """Resolve a conflict using specified strategy."""
        norm1 = self._norms.get_norm(conflict.norm1_id)
        norm2 = self._norms.get_norm(conflict.norm2_id)

        if not norm1 or not norm2:
            return None

        winner_id = None

        if strategy == ResolutionStrategy.PRIORITY:
            winner_id = norm1.norm_id if norm1.priority >= norm2.priority else norm2.norm_id

        elif strategy == ResolutionStrategy.LEX_POSTERIOR:
            winner_id = norm1.norm_id if norm1.created >= norm2.created else norm2.norm_id

        elif strategy == ResolutionStrategy.LEX_SUPERIOR:
            # Higher authority has precedence (assuming authority string ordering)
            winner_id = norm1.norm_id if norm1.authority >= norm2.authority else norm2.norm_id

        elif strategy == ResolutionStrategy.LEX_SPECIALIS:
            # More specific norm wins (more conditions = more specific)
            stmt1 = self._norms.get_norm_statements(norm1.norm_id)
            stmt2 = self._norms.get_norm_statements(norm2.norm_id)
            cond1 = sum(1 for s in stmt1 if s.condition)
            cond2 = sum(1 for s in stmt2 if s.condition)
            winner_id = norm1.norm_id if cond1 >= cond2 else norm2.norm_id

        conflict.resolution = strategy.value
        conflict.winner_id = winner_id

        return winner_id

    def get_conflict(self, conflict_id: str) -> Optional[NormConflict]:
        """Get a conflict."""
        return self._conflicts.get(conflict_id)

    def all_conflicts(self) -> List[NormConflict]:
        """Get all conflicts."""
        return list(self._conflicts.values())


# =============================================================================
# DEONTIC LOGIC
# =============================================================================

class DeonticLogic:
    """Deontic logic operations."""

    @staticmethod
    def obligation_implies_permission(obligation: bool) -> bool:
        """O(p) -> P(p): Obligation implies permission."""
        return obligation

    @staticmethod
    def prohibition_implies_not_permission(prohibition: bool) -> bool:
        """F(p) -> ~P(p): Prohibition implies not permitted."""
        return not prohibition if prohibition else True

    @staticmethod
    def not_obligation_to_not(obligation_not: bool) -> bool:
        """~O(~p) <-> P(p): Not obligated to not = permitted."""
        return not obligation_not

    @staticmethod
    def prohibition_equals_obligation_not(prohibition: bool) -> bool:
        """F(p) <-> O(~p): Forbidden = obligated not to."""
        return prohibition

    @staticmethod
    def permission_is_not_prohibited(permission: bool, prohibition: bool) -> bool:
        """P(p) <-> ~F(p): Permitted = not forbidden."""
        return permission == (not prohibition)

    @staticmethod
    def ought_implies_can(obligation: bool, can: bool) -> bool:
        """O(p) -> Can(p): Ought implies can."""
        if obligation:
            return can
        return True  # No obligation, so valid


# =============================================================================
# DEONTIC REASONER
# =============================================================================

class DeonticReasoner:
    """
    Deontic Reasoner for BAEL.

    Advanced normative and obligation reasoning.
    """

    def __init__(self):
        self._action_manager = ActionManager()
        self._norm_manager = NormManager()
        self._duty_deriver = DutyDeriver(self._norm_manager)
        self._compliance_checker = ComplianceChecker(
            self._duty_deriver, self._action_manager
        )
        self._conflict_resolver = ConflictResolver(self._norm_manager)
        self._logic = DeonticLogic()

    # -------------------------------------------------------------------------
    # ACTIONS
    # -------------------------------------------------------------------------

    def create_action(
        self,
        name: str,
        description: str = "",
        preconditions: Optional[List[str]] = None,
        effects: Optional[List[str]] = None
    ) -> Action:
        """Create an action."""
        return self._action_manager.create_action(
            name, description, preconditions, effects
        )

    def get_action(self, action_id: str) -> Optional[Action]:
        """Get an action."""
        return self._action_manager.get_action(action_id)

    # -------------------------------------------------------------------------
    # NORMS
    # -------------------------------------------------------------------------

    def create_norm(
        self,
        name: str,
        norm_type: NormType = NormType.REGULATIVE,
        authority: str = "",
        priority: int = 0,
        activation_condition: str = ""
    ) -> Norm:
        """Create a norm."""
        return self._norm_manager.create_norm(
            name, norm_type, authority, priority, activation_condition
        )

    def add_obligation(
        self,
        norm_id: str,
        agent: str,
        action_id: str,
        condition: str = "",
        deadline: Optional[datetime] = None
    ) -> Optional[DeonticStatement]:
        """Add an obligation to a norm."""
        return self._norm_manager.add_statement(
            norm_id, DeonticOperator.OBLIGATION,
            agent, action_id, condition, deadline
        )

    def add_permission(
        self,
        norm_id: str,
        agent: str,
        action_id: str,
        condition: str = ""
    ) -> Optional[DeonticStatement]:
        """Add a permission to a norm."""
        return self._norm_manager.add_statement(
            norm_id, DeonticOperator.PERMISSION,
            agent, action_id, condition
        )

    def add_prohibition(
        self,
        norm_id: str,
        agent: str,
        action_id: str,
        condition: str = ""
    ) -> Optional[DeonticStatement]:
        """Add a prohibition to a norm."""
        return self._norm_manager.add_statement(
            norm_id, DeonticOperator.PROHIBITION,
            agent, action_id, condition
        )

    def get_norm(self, norm_id: str) -> Optional[Norm]:
        """Get a norm."""
        return self._norm_manager.get_norm(norm_id)

    def get_active_norms(self) -> List[Norm]:
        """Get all active norms."""
        return self._norm_manager.get_active_norms()

    # -------------------------------------------------------------------------
    # DUTIES
    # -------------------------------------------------------------------------

    def derive_duties(
        self,
        agent: str,
        context: Optional[Dict[str, Any]] = None
    ) -> List[Duty]:
        """Derive duties for an agent."""
        return self._duty_deriver.derive_duties(agent, context)

    def get_obligations(self, agent: str) -> List[Duty]:
        """Get agent's obligations."""
        return self._duty_deriver.get_obligations(agent)

    def get_prohibitions(self, agent: str) -> List[Duty]:
        """Get agent's prohibitions."""
        return self._duty_deriver.get_prohibitions(agent)

    def get_permissions(self, agent: str) -> List[Duty]:
        """Get agent's permissions."""
        return self._duty_deriver.get_permissions(agent)

    def fulfill_duty(self, duty_id: str) -> bool:
        """Mark duty as fulfilled."""
        return self._duty_deriver.fulfill_duty(duty_id)

    # -------------------------------------------------------------------------
    # COMPLIANCE
    # -------------------------------------------------------------------------

    def log_action(
        self,
        agent: str,
        action_id: str,
        timestamp: Optional[datetime] = None
    ) -> None:
        """Log an action performed by agent."""
        self._compliance_checker.log_action(agent, action_id, timestamp)

    def check_compliance(
        self,
        agent: str
    ) -> Tuple[ComplianceStatus, List[Violation]]:
        """Check agent's compliance."""
        return self._compliance_checker.check_compliance(agent)

    def is_permitted(self, agent: str, action_id: str) -> bool:
        """Check if action is permitted."""
        return self._compliance_checker.is_action_permitted(agent, action_id)

    def is_obligated(self, agent: str, action_id: str) -> bool:
        """Check if action is obligated."""
        return self._compliance_checker.is_action_obligated(agent, action_id)

    def get_violations(self, agent: str) -> List[Violation]:
        """Get agent's violations."""
        return self._compliance_checker.get_violations(agent)

    # -------------------------------------------------------------------------
    # CONFLICTS
    # -------------------------------------------------------------------------

    def detect_conflicts(self, duties: List[Duty]) -> List[NormConflict]:
        """Detect conflicts."""
        return self._conflict_resolver.detect_conflicts(duties)

    def resolve_conflict(
        self,
        conflict: NormConflict,
        strategy: ResolutionStrategy = ResolutionStrategy.PRIORITY
    ) -> Optional[str]:
        """Resolve a conflict."""
        return self._conflict_resolver.resolve_conflict(conflict, strategy)

    # -------------------------------------------------------------------------
    # DEONTIC LOGIC
    # -------------------------------------------------------------------------

    def obligation_implies_permission(self, is_obligated: bool) -> bool:
        """O(p) -> P(p)."""
        return self._logic.obligation_implies_permission(is_obligated)

    def ought_implies_can(self, is_obligated: bool, can_perform: bool) -> bool:
        """O(p) -> Can(p)."""
        return self._logic.ought_implies_can(is_obligated, can_perform)


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Deontic Reasoner."""
    print("=" * 70)
    print("BAEL - DEONTIC REASONER DEMO")
    print("Advanced Normative and Obligation Reasoning")
    print("=" * 70)
    print()

    reasoner = DeonticReasoner()

    # 1. Create Actions
    print("1. CREATE ACTIONS:")
    print("-" * 40)

    pay_taxes = reasoner.create_action(
        "pay_taxes",
        "Pay required taxes",
        preconditions=["has_income"],
        effects=["tax_paid"]
    )

    drive = reasoner.create_action(
        "drive",
        "Drive a vehicle",
        preconditions=["has_license"],
        effects=["traveled"]
    )

    speed = reasoner.create_action(
        "speed",
        "Drive over speed limit",
        preconditions=["is_driving"],
        effects=["faster_travel", "risk_accident"]
    )

    vote = reasoner.create_action(
        "vote",
        "Vote in election",
        preconditions=["is_citizen", "is_adult"],
        effects=["voted"]
    )

    print(f"   Action: {pay_taxes.name} - {pay_taxes.description}")
    print(f"   Action: {drive.name} - {drive.description}")
    print(f"   Action: {speed.name} - {speed.description}")
    print(f"   Action: {vote.name} - {vote.description}")
    print()

    # 2. Create Norms
    print("2. CREATE NORMS:")
    print("-" * 40)

    tax_law = reasoner.create_norm(
        "Tax Law",
        NormType.REGULATIVE,
        authority="Government",
        priority=10
    )

    traffic_law = reasoner.create_norm(
        "Traffic Law",
        NormType.REGULATIVE,
        authority="Government",
        priority=8
    )

    civic_duty = reasoner.create_norm(
        "Civic Duty",
        NormType.PRESCRIPTIVE,
        authority="Society",
        priority=5
    )

    print(f"   Norm: {tax_law.name} (priority: {tax_law.priority})")
    print(f"   Norm: {traffic_law.name} (priority: {traffic_law.priority})")
    print(f"   Norm: {civic_duty.name} (priority: {civic_duty.priority})")
    print()

    # 3. Add Deontic Statements
    print("3. ADD DEONTIC STATEMENTS:")
    print("-" * 40)

    # Tax law obligations
    reasoner.add_obligation(
        tax_law.norm_id,
        "citizen",
        pay_taxes.action_id,
        condition="has_income"
    )

    # Traffic law
    reasoner.add_permission(
        traffic_law.norm_id,
        "citizen",
        drive.action_id,
        condition="has_license"
    )

    reasoner.add_prohibition(
        traffic_law.norm_id,
        "citizen",
        speed.action_id
    )

    # Civic duty
    reasoner.add_obligation(
        civic_duty.norm_id,
        "citizen",
        vote.action_id,
        condition="is_adult"
    )

    print("   Tax Law: O(citizen, pay_taxes) if has_income")
    print("   Traffic Law: P(citizen, drive) if has_license")
    print("   Traffic Law: F(citizen, speed)")
    print("   Civic Duty: O(citizen, vote) if is_adult")
    print()

    # 4. Derive Duties
    print("4. DERIVE DUTIES:")
    print("-" * 40)

    context = {
        "has_income": True,
        "has_license": True,
        "is_adult": True
    }

    duties = reasoner.derive_duties("citizen", context)

    print(f"   Context: {context}")
    print(f"   Derived {len(duties)} duties:")

    for duty in duties:
        action = reasoner.get_action(duty.action_id)
        print(f"     {duty.operator.value.upper()}: {action.name if action else 'unknown'}")
    print()

    # 5. Check Permissions
    print("5. CHECK PERMISSIONS:")
    print("-" * 40)

    print(f"   Is 'drive' permitted? {reasoner.is_permitted('citizen', drive.action_id)}")
    print(f"   Is 'speed' permitted? {reasoner.is_permitted('citizen', speed.action_id)}")
    print(f"   Is 'vote' obligated? {reasoner.is_obligated('citizen', vote.action_id)}")
    print()

    # 6. Log Actions and Check Compliance
    print("6. COMPLIANCE CHECKING:")
    print("-" * 40)

    # Agent performs some actions
    reasoner.log_action("citizen", pay_taxes.action_id)
    reasoner.log_action("citizen", vote.action_id)

    status, violations = reasoner.check_compliance("citizen")
    print(f"   Actions logged: pay_taxes, vote")
    print(f"   Compliance status: {status.value}")
    print(f"   Violations: {len(violations)}")
    print()

    # 7. Create Violation
    print("7. VIOLATION DETECTION:")
    print("-" * 40)

    # Agent speeds (prohibited action)
    reasoner.log_action("citizen", speed.action_id)

    status, violations = reasoner.check_compliance("citizen")
    print(f"   Action logged: speed")
    print(f"   Compliance status: {status.value}")
    print(f"   Violations: {len(violations)}")
    for v in violations:
        print(f"     - {v.description}")
    print()

    # 8. Conflict Detection
    print("8. CONFLICT DETECTION:")
    print("-" * 40)

    # Create conflicting norm
    emergency_norm = reasoner.create_norm(
        "Emergency Protocol",
        NormType.REGULATIVE,
        authority="Emergency Services",
        priority=15
    )

    # Obligate speeding in emergency
    reasoner.add_obligation(
        emergency_norm.norm_id,
        "citizen",
        speed.action_id,
        condition="is_emergency"
    )

    # Derive with emergency context
    emergency_context = {"is_emergency": True}
    emergency_duties = reasoner.derive_duties("citizen", emergency_context)

    conflicts = reasoner.detect_conflicts(duties + emergency_duties)
    print(f"   Emergency norm added: O(citizen, speed) if emergency")
    print(f"   Conflicts detected: {len(conflicts)}")

    for conflict in conflicts:
        print(f"     Type: {conflict.conflict_type.value}")
    print()

    # 9. Conflict Resolution
    print("9. CONFLICT RESOLUTION:")
    print("-" * 40)

    if conflicts:
        for conflict in conflicts:
            winner = reasoner.resolve_conflict(
                conflict, ResolutionStrategy.PRIORITY
            )
            winner_norm = reasoner.get_norm(winner) if winner else None
            print(f"   Strategy: PRIORITY")
            print(f"   Winner: {winner_norm.name if winner_norm else 'None'}")
    print()

    # 10. Deontic Logic
    print("10. DEONTIC LOGIC PRINCIPLES:")
    print("-" * 40)

    print("   O(p) -> P(p) (Obligation implies Permission):")
    print(f"     If obligated=True: Permitted={reasoner.obligation_implies_permission(True)}")
    print(f"     If obligated=False: Permitted={reasoner.obligation_implies_permission(False)}")

    print("   O(p) -> Can(p) (Ought implies Can):")
    print(f"     If obligated=True, can=True: Valid={reasoner.ought_implies_can(True, True)}")
    print(f"     If obligated=True, can=False: Valid={reasoner.ought_implies_can(True, False)}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Deontic Reasoner Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())

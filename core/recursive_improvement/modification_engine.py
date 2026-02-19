"""
🔄 MODIFICATION ENGINE 🔄
=========================
Self-modification system.

Features:
- Safe modifications
- Plan validation
- Rollback support
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional
from datetime import datetime
import uuid
import hashlib


class ModificationType(Enum):
    """Types of modifications"""
    PARAMETER_UPDATE = auto()
    ALGORITHM_CHANGE = auto()
    CAPABILITY_ADD = auto()
    CAPABILITY_REMOVE = auto()
    ARCHITECTURE_CHANGE = auto()
    BEHAVIOR_MODIFICATION = auto()
    KNOWLEDGE_UPDATE = auto()


@dataclass
class Modification:
    """A single modification"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Type
    mod_type: ModificationType = ModificationType.PARAMETER_UPDATE

    # Target
    target: str = ""
    target_path: str = ""

    # Change
    old_value: Any = None
    new_value: Any = None

    # Validation
    is_validated: bool = False
    is_safe: bool = False
    risk_level: float = 0.0

    # Status
    is_applied: bool = False
    applied_at: Optional[datetime] = None

    # Rollback
    can_rollback: bool = True
    rollback_data: Any = None

    def get_hash(self) -> str:
        """Get modification hash"""
        content = f"{self.mod_type}:{self.target}:{self.old_value}:{self.new_value}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]


@dataclass
class ModificationPlan:
    """Plan for multiple modifications"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""

    # Modifications
    modifications: List[Modification] = field(default_factory=list)

    # Order matters
    ordered: bool = True

    # Validation
    is_validated: bool = False
    validation_result: Optional[str] = None

    # Execution
    is_executed: bool = False
    execution_result: Optional[str] = None

    # Dependencies
    dependencies: List[str] = field(default_factory=list)

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    estimated_risk: float = 0.0

    def add_modification(self, mod: Modification):
        """Add modification to plan"""
        self.modifications.append(mod)
        self.estimated_risk = max(self.estimated_risk, mod.risk_level)

    def get_total_risk(self) -> float:
        """Calculate total risk"""
        if not self.modifications:
            return 0.0

        # Combined risk increases non-linearly
        individual_risks = [m.risk_level for m in self.modifications]
        base_risk = sum(individual_risks) / len(individual_risks)
        complexity_factor = 1 + (len(self.modifications) - 1) * 0.1

        return min(1.0, base_risk * complexity_factor)


class SafetyValidator:
    """
    Validates modification safety.
    """

    def __init__(self):
        self.safety_rules: List[Callable[[Modification], bool]] = []
        self.risk_assessors: List[Callable[[Modification], float]] = []

        self._init_default_rules()

    def _init_default_rules(self):
        """Initialize default safety rules"""
        # No architecture changes without explicit approval
        self.add_safety_rule(
            lambda m: m.mod_type != ModificationType.ARCHITECTURE_CHANGE
        )

        # No removing core capabilities
        self.add_safety_rule(
            lambda m: not (m.mod_type == ModificationType.CAPABILITY_REMOVE and
                          "core" in m.target.lower())
        )

    def add_safety_rule(self, rule: Callable[[Modification], bool]):
        """Add safety rule"""
        self.safety_rules.append(rule)

    def add_risk_assessor(self, assessor: Callable[[Modification], float]):
        """Add risk assessor"""
        self.risk_assessors.append(assessor)

    def validate(self, modification: Modification) -> bool:
        """Validate modification safety"""
        # Check all safety rules
        for rule in self.safety_rules:
            try:
                if not rule(modification):
                    modification.is_safe = False
                    return False
            except Exception:
                modification.is_safe = False
                return False

        modification.is_safe = True
        modification.is_validated = True
        return True

    def assess_risk(self, modification: Modification) -> float:
        """Assess modification risk"""
        base_risk = 0.0

        # Type-based risk
        type_risks = {
            ModificationType.PARAMETER_UPDATE: 0.1,
            ModificationType.ALGORITHM_CHANGE: 0.4,
            ModificationType.CAPABILITY_ADD: 0.2,
            ModificationType.CAPABILITY_REMOVE: 0.6,
            ModificationType.ARCHITECTURE_CHANGE: 0.8,
            ModificationType.BEHAVIOR_MODIFICATION: 0.5,
            ModificationType.KNOWLEDGE_UPDATE: 0.1,
        }
        base_risk = type_risks.get(modification.mod_type, 0.5)

        # Custom assessors
        for assessor in self.risk_assessors:
            try:
                additional_risk = assessor(modification)
                base_risk = max(base_risk, additional_risk)
            except Exception:
                pass

        modification.risk_level = min(1.0, base_risk)
        return modification.risk_level

    def validate_plan(self, plan: ModificationPlan) -> bool:
        """Validate entire modification plan"""
        for mod in plan.modifications:
            if not self.validate(mod):
                plan.is_validated = False
                plan.validation_result = f"Modification {mod.id} failed validation"
                return False

            self.assess_risk(mod)

        plan.estimated_risk = plan.get_total_risk()

        # High risk plans require additional scrutiny
        if plan.estimated_risk > 0.7:
            plan.is_validated = False
            plan.validation_result = "Plan risk too high for automatic approval"
            return False

        plan.is_validated = True
        plan.validation_result = "Plan validated successfully"
        return True


class ModificationEngine:
    """
    Executes modifications.
    """

    def __init__(self):
        self.validator = SafetyValidator()

        # Modification handlers by type
        self.handlers: Dict[ModificationType, Callable[[Modification], bool]] = {}

        # History
        self.applied_modifications: List[Modification] = []
        self.failed_modifications: List[Modification] = []

        # State
        self.is_locked: bool = False

    def register_handler(
        self,
        mod_type: ModificationType,
        handler: Callable[[Modification], bool]
    ):
        """Register modification handler"""
        self.handlers[mod_type] = handler

    def apply(self, modification: Modification) -> bool:
        """Apply a modification"""
        if self.is_locked:
            return False

        # Validate first
        if not modification.is_validated:
            if not self.validator.validate(modification):
                self.failed_modifications.append(modification)
                return False

        # Check safety
        if not modification.is_safe:
            self.failed_modifications.append(modification)
            return False

        # Get handler
        handler = self.handlers.get(modification.mod_type)

        if handler:
            try:
                # Store rollback data
                modification.rollback_data = modification.old_value

                # Apply
                success = handler(modification)

                if success:
                    modification.is_applied = True
                    modification.applied_at = datetime.now()
                    self.applied_modifications.append(modification)
                    return True
                else:
                    self.failed_modifications.append(modification)
                    return False

            except Exception as e:
                modification.is_applied = False
                self.failed_modifications.append(modification)
                return False

        # No handler - simulate success for simple modifications
        modification.is_applied = True
        modification.applied_at = datetime.now()
        self.applied_modifications.append(modification)
        return True

    def rollback(self, modification: Modification) -> bool:
        """Rollback a modification"""
        if not modification.can_rollback:
            return False

        if not modification.is_applied:
            return False

        # Create reverse modification
        rollback_mod = Modification(
            mod_type=modification.mod_type,
            target=modification.target,
            target_path=modification.target_path,
            old_value=modification.new_value,
            new_value=modification.rollback_data
        )

        # Force validation pass for rollback
        rollback_mod.is_validated = True
        rollback_mod.is_safe = True

        success = self.apply(rollback_mod)

        if success:
            modification.is_applied = False

        return success

    def execute_plan(self, plan: ModificationPlan) -> bool:
        """Execute modification plan"""
        if not plan.is_validated:
            if not self.validator.validate_plan(plan):
                plan.is_executed = False
                return False

        applied = []

        for mod in plan.modifications:
            success = self.apply(mod)

            if success:
                applied.append(mod)
            else:
                # Rollback all applied modifications
                for applied_mod in reversed(applied):
                    self.rollback(applied_mod)

                plan.is_executed = False
                plan.execution_result = f"Failed at modification {mod.id}"
                return False

        plan.is_executed = True
        plan.execution_result = f"Successfully applied {len(applied)} modifications"
        return True

    def lock(self):
        """Lock modification engine"""
        self.is_locked = True

    def unlock(self):
        """Unlock modification engine"""
        self.is_locked = False

    def get_history(self) -> List[Dict[str, Any]]:
        """Get modification history"""
        return [
            {
                'id': m.id,
                'type': m.mod_type.name,
                'target': m.target,
                'applied_at': m.applied_at.isoformat() if m.applied_at else None,
                'risk_level': m.risk_level
            }
            for m in self.applied_modifications
        ]


# Export all
__all__ = [
    'ModificationType',
    'Modification',
    'ModificationPlan',
    'SafetyValidator',
    'ModificationEngine',
]

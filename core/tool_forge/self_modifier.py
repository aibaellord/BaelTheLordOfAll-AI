"""
BAEL Self Modifier
===================

Self-modification capabilities for BAEL.
Enables runtime code evolution and adaptation.

Features:
- Code patching
- Hot reloading
- Rollback support
- Version tracking
- Safe modifications
"""

import ast
import copy
import hashlib
import inspect
import logging
import sys
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class ModificationType(Enum):
    """Types of modifications."""
    ADD_FUNCTION = "add_function"
    MODIFY_FUNCTION = "modify_function"
    REMOVE_FUNCTION = "remove_function"
    ADD_CLASS = "add_class"
    MODIFY_CLASS = "modify_class"
    ADD_ATTRIBUTE = "add_attribute"
    PATCH = "patch"
    HOT_RELOAD = "hot_reload"


class ModificationStatus(Enum):
    """Status of modifications."""
    PENDING = "pending"
    APPLIED = "applied"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"


@dataclass
class RollbackPoint:
    """A point for rollback."""
    id: str

    # State
    original_code: str = ""
    original_object: Any = None

    # Location
    target_module: str = ""
    target_name: str = ""

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class Modification:
    """A code modification."""
    id: str
    modification_type: ModificationType

    # Target
    target_module: str = ""
    target_name: str = ""

    # Change
    old_code: str = ""
    new_code: str = ""

    # Objects
    old_object: Any = None
    new_object: Any = None

    # Status
    status: ModificationStatus = ModificationStatus.PENDING

    # Rollback
    rollback_point: Optional[RollbackPoint] = None

    # Metadata
    reason: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    applied_at: Optional[datetime] = None


class SelfModifier:
    """
    Self-modification system for BAEL.

    Enables runtime code evolution.
    """

    def __init__(
        self,
        enable_rollback: bool = True,
        max_rollback_points: int = 100,
    ):
        self.enable_rollback = enable_rollback
        self.max_rollback_points = max_rollback_points

        # Modifications
        self._modifications: Dict[str, Modification] = {}

        # Rollback points
        self._rollback_points: List[RollbackPoint] = []

        # Modified targets
        self._modified: Set[str] = set()

        # Stats
        self.stats = {
            "modifications_made": 0,
            "rollbacks_performed": 0,
            "hot_reloads": 0,
            "failed_modifications": 0,
        }

    def add_function(
        self,
        module: str,
        function: Callable,
        name: Optional[str] = None,
        reason: str = "",
    ) -> Modification:
        """
        Add a function to a module.

        Args:
            module: Target module name
            function: Function to add
            name: Function name (defaults to function.__name__)
            reason: Reason for modification

        Returns:
            Modification record
        """
        name = name or function.__name__

        mod_id = hashlib.md5(
            f"add:{module}:{name}:{datetime.now()}".encode()
        ).hexdigest()[:12]

        modification = Modification(
            id=mod_id,
            modification_type=ModificationType.ADD_FUNCTION,
            target_module=module,
            target_name=name,
            new_code=inspect.getsource(function) if hasattr(function, "__code__") else "",
            new_object=function,
            reason=reason,
        )

        return self._apply_modification(modification)

    def modify_function(
        self,
        module: str,
        name: str,
        new_function: Callable,
        reason: str = "",
    ) -> Modification:
        """
        Modify an existing function.

        Args:
            module: Target module name
            name: Function name
            new_function: New function implementation
            reason: Reason for modification

        Returns:
            Modification record
        """
        mod_id = hashlib.md5(
            f"modify:{module}:{name}:{datetime.now()}".encode()
        ).hexdigest()[:12]

        # Get original
        mod = sys.modules.get(module)
        original = getattr(mod, name, None) if mod else None

        modification = Modification(
            id=mod_id,
            modification_type=ModificationType.MODIFY_FUNCTION,
            target_module=module,
            target_name=name,
            old_code=inspect.getsource(original) if original and hasattr(original, "__code__") else "",
            new_code=inspect.getsource(new_function) if hasattr(new_function, "__code__") else "",
            old_object=original,
            new_object=new_function,
            reason=reason,
        )

        return self._apply_modification(modification)

    def patch(
        self,
        module: str,
        name: str,
        patch_code: str,
        reason: str = "",
    ) -> Modification:
        """
        Apply a code patch.

        Args:
            module: Target module
            name: Target name
            patch_code: Patch to apply
            reason: Reason for patch

        Returns:
            Modification record
        """
        mod_id = hashlib.md5(
            f"patch:{module}:{name}:{datetime.now()}".encode()
        ).hexdigest()[:12]

        modification = Modification(
            id=mod_id,
            modification_type=ModificationType.PATCH,
            target_module=module,
            target_name=name,
            new_code=patch_code,
            reason=reason,
        )

        return self._apply_modification(modification)

    def add_method(
        self,
        cls: type,
        method: Callable,
        name: Optional[str] = None,
        reason: str = "",
    ) -> Modification:
        """
        Add a method to a class.

        Args:
            cls: Target class
            method: Method to add
            name: Method name
            reason: Reason for modification

        Returns:
            Modification record
        """
        name = name or method.__name__

        mod_id = hashlib.md5(
            f"add_method:{cls.__name__}:{name}:{datetime.now()}".encode()
        ).hexdigest()[:12]

        modification = Modification(
            id=mod_id,
            modification_type=ModificationType.MODIFY_CLASS,
            target_module=cls.__module__,
            target_name=f"{cls.__name__}.{name}",
            new_object=method,
            reason=reason,
        )

        # Create rollback point
        if self.enable_rollback:
            original = getattr(cls, name, None)
            modification.rollback_point = RollbackPoint(
                id=f"rb_{mod_id}",
                original_object=original,
                target_module=cls.__module__,
                target_name=f"{cls.__name__}.{name}",
            )

        # Apply modification
        setattr(cls, name, method)

        modification.status = ModificationStatus.APPLIED
        modification.applied_at = datetime.now()

        self._modifications[mod_id] = modification
        self._modified.add(f"{cls.__name__}.{name}")
        self.stats["modifications_made"] += 1

        logger.info(f"Added method {name} to {cls.__name__}")

        return modification

    def _apply_modification(
        self,
        modification: Modification,
    ) -> Modification:
        """Apply a modification."""
        try:
            mod = sys.modules.get(modification.target_module)

            if mod is None:
                # Try importing
                try:
                    mod = __import__(modification.target_module)
                except ImportError:
                    modification.status = ModificationStatus.FAILED
                    self.stats["failed_modifications"] += 1
                    return modification

            # Create rollback point
            if self.enable_rollback:
                original = getattr(mod, modification.target_name, None)
                modification.rollback_point = RollbackPoint(
                    id=f"rb_{modification.id}",
                    original_object=original,
                    original_code=modification.old_code,
                    target_module=modification.target_module,
                    target_name=modification.target_name,
                )
                self._add_rollback_point(modification.rollback_point)

            # Apply
            if modification.new_object:
                setattr(mod, modification.target_name, modification.new_object)
            elif modification.new_code:
                # Compile and execute new code
                namespace = {}
                exec(modification.new_code, namespace)

                # Find the defined object
                for name, obj in namespace.items():
                    if not name.startswith("_"):
                        setattr(mod, modification.target_name, obj)
                        break

            modification.status = ModificationStatus.APPLIED
            modification.applied_at = datetime.now()

            self._modifications[modification.id] = modification
            self._modified.add(f"{modification.target_module}.{modification.target_name}")
            self.stats["modifications_made"] += 1

            logger.info(
                f"Applied {modification.modification_type.value}: "
                f"{modification.target_module}.{modification.target_name}"
            )

        except Exception as e:
            modification.status = ModificationStatus.FAILED
            self.stats["failed_modifications"] += 1
            logger.error(f"Modification failed: {e}")

        return modification

    def _add_rollback_point(self, point: RollbackPoint) -> None:
        """Add a rollback point."""
        self._rollback_points.append(point)

        # Limit rollback points
        while len(self._rollback_points) > self.max_rollback_points:
            self._rollback_points.pop(0)

    def rollback(self, modification_id: str) -> bool:
        """
        Rollback a modification.

        Args:
            modification_id: Modification to rollback

        Returns:
            Whether rollback succeeded
        """
        if modification_id not in self._modifications:
            return False

        modification = self._modifications[modification_id]

        if not modification.rollback_point:
            logger.warning("No rollback point available")
            return False

        try:
            mod = sys.modules.get(modification.target_module)
            if mod is None:
                return False

            # Restore original
            if modification.rollback_point.original_object is not None:
                setattr(
                    mod,
                    modification.target_name,
                    modification.rollback_point.original_object,
                )
            else:
                # Remove the added attribute
                delattr(mod, modification.target_name)

            modification.status = ModificationStatus.ROLLED_BACK
            self.stats["rollbacks_performed"] += 1

            logger.info(f"Rolled back: {modification.target_module}.{modification.target_name}")

            return True

        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return False

    def rollback_all(self) -> int:
        """Rollback all modifications."""
        count = 0

        for mod_id in list(self._modifications.keys()):
            if self.rollback(mod_id):
                count += 1

        return count

    def hot_reload(
        self,
        module: str,
        new_code: str,
        reason: str = "",
    ) -> Modification:
        """
        Hot reload a module.

        Args:
            module: Module to reload
            new_code: New module code
            reason: Reason for reload

        Returns:
            Modification record
        """
        mod_id = hashlib.md5(
            f"reload:{module}:{datetime.now()}".encode()
        ).hexdigest()[:12]

        modification = Modification(
            id=mod_id,
            modification_type=ModificationType.HOT_RELOAD,
            target_module=module,
            new_code=new_code,
            reason=reason,
        )

        try:
            mod = sys.modules.get(module)

            # Save rollback point
            if self.enable_rollback and mod:
                modification.rollback_point = RollbackPoint(
                    id=f"rb_{mod_id}",
                    original_object=mod,
                    target_module=module,
                )

            # Execute new code in fresh namespace
            namespace = {"__name__": module}
            exec(new_code, namespace)

            # Update module
            if mod:
                for name, value in namespace.items():
                    if not name.startswith("_"):
                        setattr(mod, name, value)
            else:
                # Create new module
                import types
                new_mod = types.ModuleType(module)
                for name, value in namespace.items():
                    setattr(new_mod, name, value)
                sys.modules[module] = new_mod

            modification.status = ModificationStatus.APPLIED
            modification.applied_at = datetime.now()

            self.stats["hot_reloads"] += 1

            logger.info(f"Hot reloaded module: {module}")

        except Exception as e:
            modification.status = ModificationStatus.FAILED
            self.stats["failed_modifications"] += 1
            logger.error(f"Hot reload failed: {e}")

        self._modifications[mod_id] = modification

        return modification

    def create_checkpoint(self, name: str = "") -> str:
        """
        Create a checkpoint of current state.

        Args:
            name: Checkpoint name

        Returns:
            Checkpoint ID
        """
        checkpoint_id = hashlib.md5(
            f"checkpoint:{name}:{datetime.now()}".encode()
        ).hexdigest()[:12]

        # Store rollback points
        checkpoint_point = RollbackPoint(
            id=checkpoint_id,
            target_name=name or f"checkpoint_{checkpoint_id}",
        )

        self._add_rollback_point(checkpoint_point)

        logger.info(f"Created checkpoint: {checkpoint_id}")

        return checkpoint_id

    def get_modification(
        self,
        modification_id: str,
    ) -> Optional[Modification]:
        """Get a modification by ID."""
        return self._modifications.get(modification_id)

    def list_modifications(self) -> List[Modification]:
        """List all modifications."""
        return list(self._modifications.values())

    def list_modified_targets(self) -> Set[str]:
        """List all modified targets."""
        return self._modified.copy()

    def get_stats(self) -> Dict[str, Any]:
        """Get modifier statistics."""
        return {
            **self.stats,
            "pending_modifications": sum(
                1 for m in self._modifications.values()
                if m.status == ModificationStatus.PENDING
            ),
            "active_modifications": sum(
                1 for m in self._modifications.values()
                if m.status == ModificationStatus.APPLIED
            ),
            "rollback_points": len(self._rollback_points),
        }


def demo():
    """Demonstrate self modifier."""
    print("=" * 60)
    print("BAEL Self Modifier Demo")
    print("=" * 60)

    modifier = SelfModifier()

    # Create a test module
    import types
    test_module = types.ModuleType("test_module")
    test_module.value = 42

    def original_func(x):
        return x * 2

    test_module.original_func = original_func
    sys.modules["test_module"] = test_module

    print(f"\nOriginal: test_module.original_func(5) = {test_module.original_func(5)}")

    # Modify function
    print("\nModifying function...")

    def new_func(x):
        return x * 10

    mod = modifier.modify_function(
        "test_module",
        "original_func",
        new_func,
        reason="Increase multiplier",
    )

    print(f"Modification status: {mod.status.value}")
    print(f"After modification: test_module.original_func(5) = {test_module.original_func(5)}")

    # Rollback
    print("\nRolling back...")
    modifier.rollback(mod.id)

    print(f"After rollback: test_module.original_func(5) = {test_module.original_func(5)}")

    # Add new function
    print("\nAdding new function...")

    def new_addition(a, b):
        return a + b + 100

    add_mod = modifier.add_function(
        "test_module",
        new_addition,
        name="add_with_bonus",
        reason="Add bonus function",
    )

    print(f"Added function: test_module.add_with_bonus(1, 2) = {test_module.add_with_bonus(1, 2)}")

    # Hot reload
    print("\nHot reloading...")

    new_code = '''
value = 100

def calculate(x, y):
    return x * y + value
'''

    reload_mod = modifier.hot_reload(
        "test_module",
        new_code,
        reason="Update module with new calculation",
    )

    print(f"After hot reload:")
    print(f"  test_module.value = {test_module.value}")
    print(f"  test_module.calculate(3, 4) = {test_module.calculate(3, 4)}")

    print(f"\nStats: {modifier.get_stats()}")

    # Cleanup
    del sys.modules["test_module"]


if __name__ == "__main__":
    demo()

#!/usr/bin/env python3
"""
BAEL - Context Engine
Context management and state tracking for agents.

Features:
- Context tracking
- State management
- Scope handling
- Environment modeling
- Contextual awareness
"""

import asyncio
import hashlib
import json
import math
import random
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import (Any, Callable, Dict, Generic, Iterator, List, Optional,
                    Set, Tuple, Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class ContextType(Enum):
    """Types of contexts."""
    CONVERSATION = "conversation"
    TASK = "task"
    ENVIRONMENT = "environment"
    USER = "user"
    SYSTEM = "system"
    SESSION = "session"


class ScopeLevel(Enum):
    """Scope levels."""
    GLOBAL = "global"
    SESSION = "session"
    TASK = "task"
    LOCAL = "local"
    EPHEMERAL = "ephemeral"


class ContextState(Enum):
    """Context states."""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    COMPLETED = "completed"
    EXPIRED = "expired"


class VariableType(Enum):
    """Variable types."""
    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    LIST = "list"
    DICT = "dict"
    ANY = "any"


class ContextPriority(Enum):
    """Context priorities."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class MergeStrategy(Enum):
    """Context merge strategies."""
    OVERRIDE = "override"
    MERGE = "merge"
    PRESERVE = "preserve"
    NEWEST = "newest"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class ContextVariable:
    """A variable in context."""
    var_id: str = ""
    name: str = ""
    value: Any = None
    var_type: VariableType = VariableType.ANY
    scope: ScopeLevel = ScopeLevel.LOCAL
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    ttl: Optional[int] = None

    def __post_init__(self):
        if not self.var_id:
            self.var_id = str(uuid.uuid4())[:8]


@dataclass
class Context:
    """A context instance."""
    context_id: str = ""
    name: str = ""
    context_type: ContextType = ContextType.TASK
    state: ContextState = ContextState.ACTIVE
    priority: ContextPriority = ContextPriority.NORMAL
    parent_id: Optional[str] = None
    variables: Dict[str, ContextVariable] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not self.context_id:
            self.context_id = str(uuid.uuid4())[:8]


@dataclass
class ContextSnapshot:
    """A snapshot of context state."""
    snapshot_id: str = ""
    context_id: str = ""
    variables: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not self.snapshot_id:
            self.snapshot_id = str(uuid.uuid4())[:8]


@dataclass
class ContextQuery:
    """A query for context lookup."""
    query_id: str = ""
    variable_name: Optional[str] = None
    context_type: Optional[ContextType] = None
    scope: Optional[ScopeLevel] = None
    include_parent: bool = True

    def __post_init__(self):
        if not self.query_id:
            self.query_id = str(uuid.uuid4())[:8]


@dataclass
class ContextConfig:
    """Context engine configuration."""
    max_contexts: int = 100
    default_ttl: int = 3600
    enable_snapshots: bool = True
    merge_strategy: MergeStrategy = MergeStrategy.MERGE


# =============================================================================
# VARIABLE MANAGER
# =============================================================================

class VariableManager:
    """Manage context variables."""

    def __init__(self):
        self._variables: Dict[str, ContextVariable] = {}

    def set(
        self,
        name: str,
        value: Any,
        var_type: VariableType = VariableType.ANY,
        scope: ScopeLevel = ScopeLevel.LOCAL,
        ttl: Optional[int] = None
    ) -> ContextVariable:
        """Set a variable."""
        var = ContextVariable(
            name=name,
            value=value,
            var_type=var_type,
            scope=scope,
            ttl=ttl
        )

        self._variables[name] = var

        return var

    def get(self, name: str) -> Optional[Any]:
        """Get variable value."""
        var = self._variables.get(name)

        if var:
            if var.ttl and (datetime.now() - var.created_at).total_seconds() > var.ttl:
                del self._variables[name]
                return None
            return var.value

        return None

    def get_variable(self, name: str) -> Optional[ContextVariable]:
        """Get variable object."""
        return self._variables.get(name)

    def exists(self, name: str) -> bool:
        """Check if variable exists."""
        return name in self._variables

    def delete(self, name: str) -> bool:
        """Delete a variable."""
        if name in self._variables:
            del self._variables[name]
            return True
        return False

    def update(self, name: str, value: Any) -> bool:
        """Update variable value."""
        var = self._variables.get(name)

        if var:
            var.value = value
            var.updated_at = datetime.now()
            return True

        return False

    def get_by_scope(self, scope: ScopeLevel) -> List[ContextVariable]:
        """Get variables by scope."""
        return [v for v in self._variables.values() if v.scope == scope]

    def get_all(self) -> Dict[str, Any]:
        """Get all variables as dict."""
        return {name: var.value for name, var in self._variables.items()}

    def clear(self) -> None:
        """Clear all variables."""
        self._variables.clear()

    def count(self) -> int:
        """Count variables."""
        return len(self._variables)

    def cleanup_expired(self) -> int:
        """Clean up expired variables."""
        expired = []
        now = datetime.now()

        for name, var in self._variables.items():
            if var.ttl and (now - var.created_at).total_seconds() > var.ttl:
                expired.append(name)

        for name in expired:
            del self._variables[name]

        return len(expired)


# =============================================================================
# CONTEXT MANAGER
# =============================================================================

class ContextManager:
    """Manage contexts."""

    def __init__(self, max_contexts: int = 100):
        self._contexts: Dict[str, Context] = {}
        self._active_context: Optional[str] = None
        self._max_contexts = max_contexts
        self._context_stack: List[str] = []

    def create(
        self,
        name: str,
        context_type: ContextType = ContextType.TASK,
        parent_id: Optional[str] = None,
        priority: ContextPriority = ContextPriority.NORMAL
    ) -> Context:
        """Create a context."""
        if len(self._contexts) >= self._max_contexts:
            self._cleanup_old_contexts()

        context = Context(
            name=name,
            context_type=context_type,
            parent_id=parent_id,
            priority=priority
        )

        self._contexts[context.context_id] = context

        return context

    def get(self, context_id: str) -> Optional[Context]:
        """Get context by ID."""
        return self._contexts.get(context_id)

    def get_by_name(self, name: str) -> Optional[Context]:
        """Get context by name."""
        for ctx in self._contexts.values():
            if ctx.name == name:
                return ctx
        return None

    def activate(self, context_id: str) -> bool:
        """Activate a context."""
        context = self._contexts.get(context_id)

        if context:
            if self._active_context:
                self._context_stack.append(self._active_context)

            self._active_context = context_id
            context.state = ContextState.ACTIVE
            context.updated_at = datetime.now()

            return True

        return False

    def deactivate(self, context_id: str) -> bool:
        """Deactivate a context."""
        context = self._contexts.get(context_id)

        if context:
            context.state = ContextState.SUSPENDED
            context.updated_at = datetime.now()

            if self._active_context == context_id:
                if self._context_stack:
                    self._active_context = self._context_stack.pop()
                else:
                    self._active_context = None

            return True

        return False

    def get_active(self) -> Optional[Context]:
        """Get active context."""
        if self._active_context:
            return self._contexts.get(self._active_context)
        return None

    def complete(self, context_id: str) -> bool:
        """Mark context as completed."""
        context = self._contexts.get(context_id)

        if context:
            context.state = ContextState.COMPLETED
            context.updated_at = datetime.now()

            if self._active_context == context_id:
                if self._context_stack:
                    self._active_context = self._context_stack.pop()
                else:
                    self._active_context = None

            return True

        return False

    def delete(self, context_id: str) -> bool:
        """Delete a context."""
        if context_id in self._contexts:
            if self._active_context == context_id:
                self._active_context = None

            if context_id in self._context_stack:
                self._context_stack.remove(context_id)

            del self._contexts[context_id]
            return True

        return False

    def get_children(self, parent_id: str) -> List[Context]:
        """Get child contexts."""
        return [c for c in self._contexts.values() if c.parent_id == parent_id]

    def get_by_type(self, context_type: ContextType) -> List[Context]:
        """Get contexts by type."""
        return [c for c in self._contexts.values() if c.context_type == context_type]

    def get_by_state(self, state: ContextState) -> List[Context]:
        """Get contexts by state."""
        return [c for c in self._contexts.values() if c.state == state]

    def _cleanup_old_contexts(self) -> None:
        """Clean up old contexts."""
        completed = [c.context_id for c in self._contexts.values()
                    if c.state == ContextState.COMPLETED]

        for ctx_id in completed[:10]:
            self.delete(ctx_id)

    def count(self) -> int:
        """Count contexts."""
        return len(self._contexts)

    def all(self) -> List[Context]:
        """Get all contexts."""
        return list(self._contexts.values())


# =============================================================================
# SCOPE RESOLVER
# =============================================================================

class ScopeResolver:
    """Resolve variable scope."""

    def __init__(self, context_manager: ContextManager):
        self._context_manager = context_manager
        self._global_vars: Dict[str, ContextVariable] = {}

    def set_global(
        self,
        name: str,
        value: Any,
        var_type: VariableType = VariableType.ANY
    ) -> ContextVariable:
        """Set a global variable."""
        var = ContextVariable(
            name=name,
            value=value,
            var_type=var_type,
            scope=ScopeLevel.GLOBAL
        )

        self._global_vars[name] = var

        return var

    def get_global(self, name: str) -> Optional[Any]:
        """Get global variable."""
        var = self._global_vars.get(name)
        return var.value if var else None

    def resolve(
        self,
        name: str,
        context_id: Optional[str] = None
    ) -> Optional[Any]:
        """Resolve variable value with scope chain."""
        if context_id:
            context = self._context_manager.get(context_id)

            while context:
                if name in context.variables:
                    return context.variables[name].value

                if context.parent_id:
                    context = self._context_manager.get(context.parent_id)
                else:
                    break

        if name in self._global_vars:
            return self._global_vars[name].value

        return None

    def resolve_all(
        self,
        context_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Resolve all variables in scope."""
        result = {name: var.value for name, var in self._global_vars.items()}

        if context_id:
            chain = []
            context = self._context_manager.get(context_id)

            while context:
                chain.append(context)
                if context.parent_id:
                    context = self._context_manager.get(context.parent_id)
                else:
                    break

            for ctx in reversed(chain):
                for name, var in ctx.variables.items():
                    result[name] = var.value

        return result

    def clear_global(self) -> None:
        """Clear global variables."""
        self._global_vars.clear()

    def count_global(self) -> int:
        """Count global variables."""
        return len(self._global_vars)


# =============================================================================
# SNAPSHOT MANAGER
# =============================================================================

class SnapshotManager:
    """Manage context snapshots."""

    def __init__(self, max_snapshots: int = 50):
        self._snapshots: Dict[str, List[ContextSnapshot]] = defaultdict(list)
        self._max_per_context = max_snapshots

    def create(self, context: Context) -> ContextSnapshot:
        """Create a snapshot."""
        variables = {name: var.value for name, var in context.variables.items()}

        snapshot = ContextSnapshot(
            context_id=context.context_id,
            variables=variables
        )

        snapshots = self._snapshots[context.context_id]

        if len(snapshots) >= self._max_per_context:
            snapshots.pop(0)

        snapshots.append(snapshot)

        return snapshot

    def get_latest(self, context_id: str) -> Optional[ContextSnapshot]:
        """Get latest snapshot."""
        snapshots = self._snapshots.get(context_id, [])
        return snapshots[-1] if snapshots else None

    def get_all(self, context_id: str) -> List[ContextSnapshot]:
        """Get all snapshots for context."""
        return self._snapshots.get(context_id, [])

    def restore(
        self,
        context: Context,
        snapshot: ContextSnapshot
    ) -> bool:
        """Restore context from snapshot."""
        if snapshot.context_id != context.context_id:
            return False

        context.variables.clear()

        for name, value in snapshot.variables.items():
            context.variables[name] = ContextVariable(
                name=name,
                value=value
            )

        context.updated_at = datetime.now()

        return True

    def diff(
        self,
        snapshot1: ContextSnapshot,
        snapshot2: ContextSnapshot
    ) -> Dict[str, Tuple[Any, Any]]:
        """Get difference between snapshots."""
        diff = {}

        all_keys = set(snapshot1.variables.keys()) | set(snapshot2.variables.keys())

        for key in all_keys:
            v1 = snapshot1.variables.get(key)
            v2 = snapshot2.variables.get(key)

            if v1 != v2:
                diff[key] = (v1, v2)

        return diff

    def clear(self, context_id: str) -> None:
        """Clear snapshots for context."""
        if context_id in self._snapshots:
            del self._snapshots[context_id]

    def count(self, context_id: str) -> int:
        """Count snapshots for context."""
        return len(self._snapshots.get(context_id, []))


# =============================================================================
# CONTEXT MERGER
# =============================================================================

class ContextMerger:
    """Merge contexts."""

    def __init__(self, strategy: MergeStrategy = MergeStrategy.MERGE):
        self._strategy = strategy

    def merge(
        self,
        source: Context,
        target: Context,
        strategy: Optional[MergeStrategy] = None
    ) -> Context:
        """Merge source into target."""
        strategy = strategy or self._strategy

        if strategy == MergeStrategy.OVERRIDE:
            target.variables = dict(source.variables)

        elif strategy == MergeStrategy.MERGE:
            for name, var in source.variables.items():
                if name not in target.variables:
                    target.variables[name] = var

        elif strategy == MergeStrategy.PRESERVE:
            pass

        elif strategy == MergeStrategy.NEWEST:
            for name, var in source.variables.items():
                existing = target.variables.get(name)

                if not existing or var.updated_at > existing.updated_at:
                    target.variables[name] = var

        target.updated_at = datetime.now()

        return target

    def merge_variables(
        self,
        source_vars: Dict[str, Any],
        target_vars: Dict[str, Any],
        strategy: Optional[MergeStrategy] = None
    ) -> Dict[str, Any]:
        """Merge variable dictionaries."""
        strategy = strategy or self._strategy

        if strategy == MergeStrategy.OVERRIDE:
            return dict(source_vars)

        elif strategy == MergeStrategy.MERGE:
            result = dict(target_vars)
            result.update(source_vars)
            return result

        elif strategy == MergeStrategy.PRESERVE:
            result = dict(source_vars)
            result.update(target_vars)
            return result

        return dict(target_vars)


# =============================================================================
# CONTEXT ENGINE
# =============================================================================

class ContextEngine:
    """
    Context Engine for BAEL.

    Context management and state tracking.
    """

    def __init__(self, config: Optional[ContextConfig] = None):
        self._config = config or ContextConfig()

        self._context_manager = ContextManager(self._config.max_contexts)
        self._scope_resolver = ScopeResolver(self._context_manager)
        self._snapshot_manager = SnapshotManager()
        self._context_merger = ContextMerger(self._config.merge_strategy)

    # ----- Context Operations -----

    def create_context(
        self,
        name: str,
        context_type: ContextType = ContextType.TASK,
        parent_id: Optional[str] = None
    ) -> Context:
        """Create a context."""
        return self._context_manager.create(name, context_type, parent_id)

    def get_context(self, context_id: str) -> Optional[Context]:
        """Get context by ID."""
        return self._context_manager.get(context_id)

    def get_context_by_name(self, name: str) -> Optional[Context]:
        """Get context by name."""
        return self._context_manager.get_by_name(name)

    def activate_context(self, context_id: str) -> bool:
        """Activate a context."""
        return self._context_manager.activate(context_id)

    def deactivate_context(self, context_id: str) -> bool:
        """Deactivate a context."""
        return self._context_manager.deactivate(context_id)

    def get_active_context(self) -> Optional[Context]:
        """Get active context."""
        return self._context_manager.get_active()

    def complete_context(self, context_id: str) -> bool:
        """Complete a context."""
        return self._context_manager.complete(context_id)

    def delete_context(self, context_id: str) -> bool:
        """Delete a context."""
        return self._context_manager.delete(context_id)

    # ----- Variable Operations -----

    def set_variable(
        self,
        context_id: str,
        name: str,
        value: Any,
        var_type: VariableType = VariableType.ANY,
        ttl: Optional[int] = None
    ) -> Optional[ContextVariable]:
        """Set variable in context."""
        context = self._context_manager.get(context_id)

        if not context:
            return None

        var = ContextVariable(
            name=name,
            value=value,
            var_type=var_type,
            ttl=ttl or self._config.default_ttl
        )

        context.variables[name] = var
        context.updated_at = datetime.now()

        return var

    def get_variable(
        self,
        context_id: str,
        name: str,
        resolve_scope: bool = True
    ) -> Optional[Any]:
        """Get variable from context."""
        if resolve_scope:
            return self._scope_resolver.resolve(name, context_id)

        context = self._context_manager.get(context_id)

        if context and name in context.variables:
            return context.variables[name].value

        return None

    def delete_variable(self, context_id: str, name: str) -> bool:
        """Delete variable from context."""
        context = self._context_manager.get(context_id)

        if context and name in context.variables:
            del context.variables[name]
            context.updated_at = datetime.now()
            return True

        return False

    def get_all_variables(
        self,
        context_id: str,
        resolve_scope: bool = True
    ) -> Dict[str, Any]:
        """Get all variables from context."""
        if resolve_scope:
            return self._scope_resolver.resolve_all(context_id)

        context = self._context_manager.get(context_id)

        if context:
            return {name: var.value for name, var in context.variables.items()}

        return {}

    # ----- Global Variables -----

    def set_global(self, name: str, value: Any) -> ContextVariable:
        """Set global variable."""
        return self._scope_resolver.set_global(name, value)

    def get_global(self, name: str) -> Optional[Any]:
        """Get global variable."""
        return self._scope_resolver.get_global(name)

    # ----- Snapshots -----

    def create_snapshot(self, context_id: str) -> Optional[ContextSnapshot]:
        """Create a snapshot."""
        if not self._config.enable_snapshots:
            return None

        context = self._context_manager.get(context_id)

        if context:
            return self._snapshot_manager.create(context)

        return None

    def restore_snapshot(
        self,
        context_id: str,
        snapshot_id: Optional[str] = None
    ) -> bool:
        """Restore from snapshot."""
        context = self._context_manager.get(context_id)

        if not context:
            return False

        if snapshot_id:
            snapshots = self._snapshot_manager.get_all(context_id)
            snapshot = next((s for s in snapshots if s.snapshot_id == snapshot_id), None)
        else:
            snapshot = self._snapshot_manager.get_latest(context_id)

        if snapshot:
            return self._snapshot_manager.restore(context, snapshot)

        return False

    def get_snapshots(self, context_id: str) -> List[ContextSnapshot]:
        """Get all snapshots for context."""
        return self._snapshot_manager.get_all(context_id)

    # ----- Context Merging -----

    def merge_contexts(
        self,
        source_id: str,
        target_id: str,
        strategy: Optional[MergeStrategy] = None
    ) -> Optional[Context]:
        """Merge contexts."""
        source = self._context_manager.get(source_id)
        target = self._context_manager.get(target_id)

        if source and target:
            return self._context_merger.merge(source, target, strategy)

        return None

    # ----- Queries -----

    def query(
        self,
        query: ContextQuery
    ) -> List[Tuple[Context, Any]]:
        """Query contexts."""
        results = []

        for context in self._context_manager.all():
            if query.context_type and context.context_type != query.context_type:
                continue

            if query.variable_name:
                value = self.get_variable(
                    context.context_id,
                    query.variable_name,
                    query.include_parent
                )

                if value is not None:
                    results.append((context, value))
            else:
                results.append((context, None))

        return results

    def find_variable(self, name: str) -> List[Tuple[Context, Any]]:
        """Find variable across all contexts."""
        results = []

        for context in self._context_manager.all():
            if name in context.variables:
                results.append((context, context.variables[name].value))

        return results

    def summary(self) -> Dict[str, Any]:
        """Get engine summary."""
        active = self._context_manager.get_active()

        return {
            "contexts": self._context_manager.count(),
            "active_context": active.name if active else None,
            "global_variables": self._scope_resolver.count_global()
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Context Engine."""
    print("=" * 70)
    print("BAEL - CONTEXT ENGINE DEMO")
    print("Context Management and State Tracking")
    print("=" * 70)
    print()

    engine = ContextEngine()

    # 1. Create Contexts
    print("1. CREATE CONTEXTS:")
    print("-" * 40)

    session = engine.create_context("user_session", ContextType.SESSION)
    task = engine.create_context("document_task", ContextType.TASK, session.context_id)

    print(f"   Created: {session.name} ({session.context_type.value})")
    print(f"   Created: {task.name} ({task.context_type.value})")
    print(f"   Parent of task: {task.parent_id}")
    print()

    # 2. Set Variables
    print("2. SET VARIABLES:")
    print("-" * 40)

    engine.set_variable(session.context_id, "user_id", "u12345")
    engine.set_variable(session.context_id, "language", "en")
    engine.set_variable(task.context_id, "document_id", "doc_001")
    engine.set_variable(task.context_id, "status", "in_progress")

    print(f"   session.user_id = u12345")
    print(f"   session.language = en")
    print(f"   task.document_id = doc_001")
    print(f"   task.status = in_progress")
    print()

    # 3. Get Variables
    print("3. GET VARIABLES:")
    print("-" * 40)

    doc_id = engine.get_variable(task.context_id, "document_id")
    user_id = engine.get_variable(task.context_id, "user_id")

    print(f"   task.document_id = {doc_id}")
    print(f"   task.user_id (inherited) = {user_id}")
    print()

    # 4. Global Variables
    print("4. GLOBAL VARIABLES:")
    print("-" * 40)

    engine.set_global("app_name", "BAEL")
    engine.set_global("version", "1.0.0")

    app = engine.get_global("app_name")
    version = engine.get_global("version")

    print(f"   global.app_name = {app}")
    print(f"   global.version = {version}")
    print()

    # 5. Activate Context
    print("5. ACTIVATE CONTEXT:")
    print("-" * 40)

    engine.activate_context(task.context_id)
    active = engine.get_active_context()

    print(f"   Activated: {task.name}")
    print(f"   Active context: {active.name if active else None}")
    print()

    # 6. Get All Variables
    print("6. GET ALL VARIABLES:")
    print("-" * 40)

    all_vars = engine.get_all_variables(task.context_id)

    print("   All variables in scope:")
    for name, value in all_vars.items():
        print(f"     {name}: {value}")
    print()

    # 7. Create Snapshot
    print("7. CREATE SNAPSHOT:")
    print("-" * 40)

    snapshot = engine.create_snapshot(task.context_id)

    print(f"   Snapshot created: {snapshot.snapshot_id}")
    print(f"   Variables: {snapshot.variables}")
    print()

    # 8. Modify and Restore
    print("8. MODIFY AND RESTORE:")
    print("-" * 40)

    engine.set_variable(task.context_id, "status", "completed")
    print(f"   Modified: status = {engine.get_variable(task.context_id, 'status')}")

    engine.restore_snapshot(task.context_id)
    print(f"   Restored: status = {engine.get_variable(task.context_id, 'status')}")
    print()

    # 9. Create Child Context
    print("9. CREATE CHILD CONTEXT:")
    print("-" * 40)

    subtask = engine.create_context("subtask_1", ContextType.TASK, task.context_id)
    engine.set_variable(subtask.context_id, "step", 1)

    step = engine.get_variable(subtask.context_id, "step")
    doc = engine.get_variable(subtask.context_id, "document_id")
    user = engine.get_variable(subtask.context_id, "user_id")

    print(f"   subtask.step = {step}")
    print(f"   subtask.document_id (inherited) = {doc}")
    print(f"   subtask.user_id (inherited) = {user}")
    print()

    # 10. Query Contexts
    print("10. QUERY CONTEXTS:")
    print("-" * 40)

    query = ContextQuery(context_type=ContextType.TASK)
    results = engine.query(query)

    print(f"   Found {len(results)} task contexts:")
    for ctx, _ in results:
        print(f"     - {ctx.name}")
    print()

    # 11. Find Variable
    print("11. FIND VARIABLE:")
    print("-" * 40)

    found = engine.find_variable("status")

    print("   Found 'status' in:")
    for ctx, value in found:
        print(f"     {ctx.name}: {value}")
    print()

    # 12. Merge Contexts
    print("12. MERGE CONTEXTS:")
    print("-" * 40)

    ctx1 = engine.create_context("source", ContextType.TASK)
    ctx2 = engine.create_context("target", ContextType.TASK)

    engine.set_variable(ctx1.context_id, "key1", "value1")
    engine.set_variable(ctx1.context_id, "key2", "value2")
    engine.set_variable(ctx2.context_id, "key2", "old_value")
    engine.set_variable(ctx2.context_id, "key3", "value3")

    engine.merge_contexts(ctx1.context_id, ctx2.context_id, MergeStrategy.MERGE)

    merged_vars = engine.get_all_variables(ctx2.context_id, resolve_scope=False)
    print("   Merged target:")
    for name, value in merged_vars.items():
        print(f"     {name}: {value}")
    print()

    # 13. Complete Context
    print("13. COMPLETE CONTEXT:")
    print("-" * 40)

    engine.complete_context(task.context_id)
    completed = engine.get_context(task.context_id)

    print(f"   Context: {completed.name}")
    print(f"   State: {completed.state.value}")
    print()

    # 14. Delete Variable
    print("14. DELETE VARIABLE:")
    print("-" * 40)

    engine.set_variable(session.context_id, "temp_var", "temp_value")
    print(f"   Before: {engine.get_variable(session.context_id, 'temp_var')}")

    engine.delete_variable(session.context_id, "temp_var")
    print(f"   After delete: {engine.get_variable(session.context_id, 'temp_var')}")
    print()

    # 15. Summary
    print("15. ENGINE SUMMARY:")
    print("-" * 40)

    summary = engine.summary()

    for key, value in summary.items():
        print(f"   {key}: {value}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Context Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())

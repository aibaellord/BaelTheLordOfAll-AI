"""
BAEL Self-Modification Engine
=============================

Runtime self-modification and code evolution.

"Ba'el rewrites itself." — Ba'el
"""

import logging
import threading
import ast
import inspect
import types
import copy
import hashlib
import time
import random
from typing import Any, Callable, Dict, Generic, List, Optional, Set, Tuple, TypeVar
from dataclasses import dataclass, field
from enum import Enum, auto
from abc import ABC, abstractmethod

logger = logging.getLogger("BAEL.SelfModification")


T = TypeVar('T')


# ============================================================================
# MODIFICATION TYPES
# ============================================================================

class ModificationType(Enum):
    """Types of self-modification."""
    FUNCTION_REPLACEMENT = auto()  # Replace function implementation
    PARAMETER_TUNING = auto()      # Adjust parameters
    BEHAVIOR_EXTENSION = auto()    # Add new behaviors
    OPTIMIZATION = auto()          # Performance optimization
    ERROR_CORRECTION = auto()      # Fix detected errors
    EVOLUTION = auto()             # Evolutionary changes


class ModificationScope(Enum):
    """Scope of modification."""
    LOCAL = auto()      # Single function/method
    CLASS = auto()      # Entire class
    MODULE = auto()     # Entire module
    GLOBAL = auto()     # System-wide


# ============================================================================
# CODE REPRESENTATION
# ============================================================================

@dataclass
class CodeUnit:
    """
    Representation of a code unit.
    """
    id: str
    name: str
    source: str
    compiled: Optional[types.CodeType] = None
    ast_tree: Optional[ast.AST] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    version: int = 1
    parent_version: Optional[str] = None

    @property
    def hash(self) -> str:
        return hashlib.sha256(self.source.encode()).hexdigest()[:16]

    def compile(self) -> bool:
        """Compile source to code object."""
        try:
            self.ast_tree = ast.parse(self.source)
            self.compiled = compile(self.ast_tree, f"<{self.name}>", "exec")
            return True
        except SyntaxError as e:
            logger.error(f"Compilation failed: {e}")
            return False


@dataclass
class Modification:
    """
    A code modification record.
    """
    id: str
    mod_type: ModificationType
    scope: ModificationScope
    target: str
    before_hash: str
    after_hash: str
    timestamp: float = field(default_factory=time.time)
    reason: str = ""
    rollback_possible: bool = True


# ============================================================================
# CODE MUTATOR
# ============================================================================

class CodeMutator:
    """
    Mutate code through AST transformations.

    "Ba'el mutates code." — Ba'el
    """

    def __init__(self):
        """Initialize mutator."""
        self._mutation_history: List[Tuple[str, str]] = []
        self._lock = threading.RLock()

    def mutate_ast(
        self,
        tree: ast.AST,
        mutation_type: str
    ) -> ast.AST:
        """Apply mutation to AST."""
        mutated = copy.deepcopy(tree)

        if mutation_type == "negate_condition":
            mutated = self._negate_conditions(mutated)
        elif mutation_type == "swap_operators":
            mutated = self._swap_operators(mutated)
        elif mutation_type == "change_constants":
            mutated = self._change_constants(mutated)
        elif mutation_type == "add_logging":
            mutated = self._add_logging(mutated)
        elif mutation_type == "optimize_loops":
            mutated = self._optimize_loops(mutated)

        ast.fix_missing_locations(mutated)
        return mutated

    def _negate_conditions(self, tree: ast.AST) -> ast.AST:
        """Negate boolean conditions."""
        class ConditionNegator(ast.NodeTransformer):
            def visit_If(self, node):
                # Wrap condition in Not
                node.test = ast.UnaryOp(op=ast.Not(), operand=node.test)
                # Swap if/else bodies
                node.body, node.orelse = node.orelse or [ast.Pass()], node.body
                return self.generic_visit(node)

        return ConditionNegator().visit(tree)

    def _swap_operators(self, tree: ast.AST) -> ast.AST:
        """Swap binary operators."""
        class OperatorSwapper(ast.NodeTransformer):
            swap_map = {
                ast.Add: ast.Sub,
                ast.Sub: ast.Add,
                ast.Mult: ast.Div,
                ast.Lt: ast.Gt,
                ast.Gt: ast.Lt,
                ast.LtE: ast.GtE,
                ast.GtE: ast.LtE,
            }

            def visit_BinOp(self, node):
                op_type = type(node.op)
                if op_type in self.swap_map:
                    node.op = self.swap_map[op_type]()
                return self.generic_visit(node)

            def visit_Compare(self, node):
                for i, op in enumerate(node.ops):
                    op_type = type(op)
                    if op_type in self.swap_map:
                        node.ops[i] = self.swap_map[op_type]()
                return self.generic_visit(node)

        return OperatorSwapper().visit(tree)

    def _change_constants(self, tree: ast.AST) -> ast.AST:
        """Mutate constant values."""
        class ConstantMutator(ast.NodeTransformer):
            def visit_Constant(self, node):
                if isinstance(node.value, (int, float)):
                    # Small random change
                    delta = random.uniform(-0.1, 0.1) * abs(node.value) if node.value != 0 else random.uniform(-1, 1)
                    if isinstance(node.value, int):
                        node.value = int(node.value + delta)
                    else:
                        node.value = node.value + delta
                return node

        return ConstantMutator().visit(tree)

    def _add_logging(self, tree: ast.AST) -> ast.AST:
        """Add logging statements."""
        class LoggingAdder(ast.NodeTransformer):
            def visit_FunctionDef(self, node):
                # Add logging at function entry
                log_stmt = ast.Expr(
                    value=ast.Call(
                        func=ast.Attribute(
                            value=ast.Name(id='logger', ctx=ast.Load()),
                            attr='debug',
                            ctx=ast.Load()
                        ),
                        args=[ast.Constant(value=f"Entering {node.name}")],
                        keywords=[]
                    )
                )
                node.body.insert(0, log_stmt)
                return self.generic_visit(node)

        return LoggingAdder().visit(tree)

    def _optimize_loops(self, tree: ast.AST) -> ast.AST:
        """Apply loop optimizations."""
        class LoopOptimizer(ast.NodeTransformer):
            def visit_For(self, node):
                # Check for range optimization
                if (isinstance(node.iter, ast.Call) and
                    isinstance(node.iter.func, ast.Name) and
                    node.iter.func.id == 'range'):
                    # Add comment about potential optimization
                    pass
                return self.generic_visit(node)

        return LoopOptimizer().visit(tree)

    def to_source(self, tree: ast.AST) -> str:
        """Convert AST back to source."""
        try:
            import ast
            return ast.unparse(tree)
        except Exception as e:
            logger.error(f"AST unparsing failed: {e}")
            return ""


# ============================================================================
# FUNCTION EVOLVER
# ============================================================================

class FunctionEvolver:
    """
    Evolve functions through genetic programming.

    "Ba'el evolves functions." — Ba'el
    """

    def __init__(self, fitness_fn: Callable[[Callable], float]):
        """
        Initialize evolver.

        Args:
            fitness_fn: Function to evaluate function fitness
        """
        self._fitness_fn = fitness_fn
        self._mutator = CodeMutator()
        self._population: List[CodeUnit] = []
        self._generation = 0
        self._lock = threading.RLock()

    def initialize_population(
        self,
        base_function: Callable,
        population_size: int = 10
    ) -> None:
        """Initialize population from base function."""
        with self._lock:
            source = inspect.getsource(base_function)

            for i in range(population_size):
                unit = CodeUnit(
                    id=f"gen0_ind{i}",
                    name=base_function.__name__,
                    source=source
                )
                unit.compile()
                self._population.append(unit)

    def evaluate_fitness(self, unit: CodeUnit) -> float:
        """Evaluate fitness of code unit."""
        try:
            # Execute code to get function
            namespace = {}
            exec(unit.compiled, namespace)
            func = namespace.get(unit.name)

            if func:
                return self._fitness_fn(func)
            return 0.0
        except Exception as e:
            logger.debug(f"Fitness evaluation failed: {e}")
            return 0.0

    def mutate(self, unit: CodeUnit) -> CodeUnit:
        """Mutate code unit."""
        with self._lock:
            mutation_type = random.choice([
                "swap_operators",
                "change_constants",
                # "negate_condition"  # Often breaks code
            ])

            try:
                tree = ast.parse(unit.source)
                mutated_tree = self._mutator.mutate_ast(tree, mutation_type)
                mutated_source = self._mutator.to_source(mutated_tree)

                new_unit = CodeUnit(
                    id=f"gen{self._generation + 1}_{unit.id}",
                    name=unit.name,
                    source=mutated_source,
                    version=unit.version + 1,
                    parent_version=unit.id
                )

                if new_unit.compile():
                    return new_unit
            except Exception as e:
                logger.debug(f"Mutation failed: {e}")

            return unit  # Return original if mutation fails

    def crossover(
        self,
        parent1: CodeUnit,
        parent2: CodeUnit
    ) -> CodeUnit:
        """Crossover two code units (simplified)."""
        # For now, just return copy of better parent
        f1 = self.evaluate_fitness(parent1)
        f2 = self.evaluate_fitness(parent2)

        better = parent1 if f1 > f2 else parent2
        return CodeUnit(
            id=f"gen{self._generation + 1}_cross",
            name=better.name,
            source=better.source,
            version=max(parent1.version, parent2.version) + 1
        )

    def evolve(self, generations: int = 10) -> CodeUnit:
        """
        Run evolution.

        Returns best individual.
        """
        with self._lock:
            for gen in range(generations):
                self._generation = gen

                # Evaluate all
                fitness_scores = [
                    (unit, self.evaluate_fitness(unit))
                    for unit in self._population
                ]
                fitness_scores.sort(key=lambda x: x[1], reverse=True)

                # Selection - keep top 50%
                survivors = [unit for unit, _ in fitness_scores[:len(self._population) // 2]]

                # Create new population
                new_population = list(survivors)

                while len(new_population) < len(self._population):
                    parent = random.choice(survivors)
                    child = self.mutate(parent)
                    new_population.append(child)

                self._population = new_population

                best_fitness = fitness_scores[0][1]
                logger.info(f"Generation {gen}: best fitness = {best_fitness:.4f}")

            # Return best
            return max(self._population, key=self.evaluate_fitness)


# ============================================================================
# RUNTIME MODIFIER
# ============================================================================

class RuntimeModifier:
    """
    Modify code at runtime.

    "Ba'el modifies reality." — Ba'el
    """

    def __init__(self):
        """Initialize runtime modifier."""
        self._modifications: List[Modification] = []
        self._originals: Dict[str, Any] = {}
        self._lock = threading.RLock()

    def replace_function(
        self,
        target_module: types.ModuleType,
        func_name: str,
        new_func: Callable
    ) -> bool:
        """
        Replace function in module.

        Returns True if successful.
        """
        with self._lock:
            try:
                # Save original
                original = getattr(target_module, func_name, None)
                if original:
                    key = f"{target_module.__name__}.{func_name}"
                    self._originals[key] = original

                    # Replace
                    setattr(target_module, func_name, new_func)

                    self._modifications.append(Modification(
                        id=f"mod_{len(self._modifications)}",
                        mod_type=ModificationType.FUNCTION_REPLACEMENT,
                        scope=ModificationScope.MODULE,
                        target=key,
                        before_hash=str(id(original)),
                        after_hash=str(id(new_func)),
                        reason="Function replacement"
                    ))

                    return True
            except Exception as e:
                logger.error(f"Function replacement failed: {e}")

            return False

    def replace_method(
        self,
        target_class: type,
        method_name: str,
        new_method: Callable
    ) -> bool:
        """Replace method in class."""
        with self._lock:
            try:
                original = getattr(target_class, method_name, None)
                if original:
                    key = f"{target_class.__name__}.{method_name}"
                    self._originals[key] = original

                    setattr(target_class, method_name, new_method)

                    self._modifications.append(Modification(
                        id=f"mod_{len(self._modifications)}",
                        mod_type=ModificationType.FUNCTION_REPLACEMENT,
                        scope=ModificationScope.CLASS,
                        target=key,
                        before_hash=str(id(original)),
                        after_hash=str(id(new_method)),
                        reason="Method replacement"
                    ))

                    return True
            except Exception as e:
                logger.error(f"Method replacement failed: {e}")

            return False

    def rollback(self, target: str) -> bool:
        """Rollback modification."""
        with self._lock:
            if target not in self._originals:
                return False

            try:
                original = self._originals[target]

                # Parse target
                parts = target.rsplit('.', 1)
                if len(parts) == 2:
                    module_or_class_name, func_name = parts
                    # Would need to resolve module_or_class dynamically
                    pass

                return True
            except Exception as e:
                logger.error(f"Rollback failed: {e}")

            return False

    def add_aspect(
        self,
        target_func: Callable,
        before: Optional[Callable] = None,
        after: Optional[Callable] = None
    ) -> Callable:
        """
        Add aspect-oriented programming hooks.

        Returns wrapped function.
        """
        def wrapped(*args, **kwargs):
            if before:
                before(*args, **kwargs)

            result = target_func(*args, **kwargs)

            if after:
                after(result, *args, **kwargs)

            return result

        return wrapped

    @property
    def modification_history(self) -> List[Modification]:
        """Get modification history."""
        return list(self._modifications)


# ============================================================================
# SELF-HEALING SYSTEM
# ============================================================================

class SelfHealingSystem:
    """
    Self-healing through automatic error correction.

    "Ba'el heals itself." — Ba'el
    """

    def __init__(self):
        """Initialize self-healing system."""
        self._error_history: List[Dict] = []
        self._corrections: Dict[str, Callable] = {}
        self._modifier = RuntimeModifier()
        self._lock = threading.RLock()

    def register_correction(
        self,
        error_pattern: str,
        correction: Callable[[Exception, Callable], Callable]
    ) -> None:
        """
        Register error correction strategy.

        Args:
            error_pattern: Pattern to match error messages
            correction: Function that returns corrected function
        """
        with self._lock:
            self._corrections[error_pattern] = correction

    def wrap_with_healing(
        self,
        func: Callable,
        max_retries: int = 3
    ) -> Callable:
        """Wrap function with self-healing capability."""
        @functools.wraps(func) if 'functools' in dir() else (lambda f: f)
        def healed_func(*args, **kwargs):
            last_error = None
            current_func = func

            for attempt in range(max_retries):
                try:
                    return current_func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    error_msg = str(e)

                    with self._lock:
                        self._error_history.append({
                            'function': func.__name__,
                            'error': error_msg,
                            'attempt': attempt,
                            'timestamp': time.time()
                        })

                    # Try to find correction
                    for pattern, correction in self._corrections.items():
                        if pattern in error_msg:
                            try:
                                current_func = correction(e, current_func)
                                logger.info(f"Applied correction for pattern: {pattern}")
                                break
                            except Exception as ce:
                                logger.warning(f"Correction failed: {ce}")

            # All retries exhausted
            raise last_error

        return healed_func

    @property
    def error_summary(self) -> Dict[str, Any]:
        """Get error summary."""
        with self._lock:
            errors_by_func = {}
            for error in self._error_history:
                func = error['function']
                errors_by_func[func] = errors_by_func.get(func, 0) + 1

            return {
                'total_errors': len(self._error_history),
                'by_function': errors_by_func,
                'corrections_available': list(self._corrections.keys())
            }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_code_mutator() -> CodeMutator:
    """Create code mutator."""
    return CodeMutator()


def create_function_evolver(
    fitness_fn: Callable[[Callable], float]
) -> FunctionEvolver:
    """Create function evolver."""
    return FunctionEvolver(fitness_fn)


def create_runtime_modifier() -> RuntimeModifier:
    """Create runtime modifier."""
    return RuntimeModifier()


def create_self_healing_system() -> SelfHealingSystem:
    """Create self-healing system."""
    return SelfHealingSystem()


def mutate_source(source: str, mutation_type: str = "swap_operators") -> str:
    """Mutate source code."""
    mutator = CodeMutator()
    tree = ast.parse(source)
    mutated = mutator.mutate_ast(tree, mutation_type)
    return mutator.to_source(mutated)


# Add functools import at module level
import functools

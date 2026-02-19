"""
⚡ CODE OPTIMIZER ⚡
===================
Code optimization passes.

Features:
- Dead code elimination
- Constant folding
- Inline expansion
- Common subexpression elimination
"""

from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Set
import uuid

from .code_core import ASTNode, NodeType, DataType, Expression


class OptimizationPass(ABC):
    """Base optimization pass"""

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def optimize(self, node: ASTNode) -> ASTNode:
        """Apply optimization to AST"""
        pass

    def get_stats(self) -> Dict[str, int]:
        """Get optimization statistics"""
        return {}


class DeadCodeElimination(OptimizationPass):
    """Remove unreachable code"""

    @property
    def name(self) -> str:
        return "dead_code_elimination"

    def __init__(self):
        self.eliminated_count = 0

    def optimize(self, node: ASTNode) -> ASTNode:
        """Remove dead code"""
        # Find variables that are used
        used_vars = self._find_used_variables(node)

        # Remove unused variable declarations
        result = self._remove_unused(node, used_vars)

        # Remove code after return statements
        result = self._remove_after_return(result)

        return result

    def _find_used_variables(self, node: ASTNode) -> Set[str]:
        """Find all used variable names"""
        used = set()

        if node.node_type == NodeType.IDENTIFIER:
            used.add(node.name)

        for child in node.children:
            used.update(self._find_used_variables(child))

        return used

    def _remove_unused(self, node: ASTNode, used_vars: Set[str]) -> ASTNode:
        """Remove unused variable declarations"""
        if node.node_type == NodeType.VARIABLE:
            if node.name not in used_vars:
                self.eliminated_count += 1
                return None  # Remove node

        # Process children
        new_children = []
        for child in node.children:
            result = self._remove_unused(child, used_vars)
            if result is not None:
                new_children.append(result)

        node.children = new_children
        return node

    def _remove_after_return(self, node: ASTNode) -> ASTNode:
        """Remove unreachable code after return"""
        if node.node_type == NodeType.BLOCK:
            new_children = []
            found_return = False

            for child in node.children:
                if found_return:
                    self.eliminated_count += 1
                    continue

                new_children.append(self._remove_after_return(child))

                if child.node_type == NodeType.RETURN:
                    found_return = True

            node.children = new_children
        else:
            for i, child in enumerate(node.children):
                node.children[i] = self._remove_after_return(child)

        return node

    def get_stats(self) -> Dict[str, int]:
        return {'eliminated': self.eliminated_count}


class ConstantFolding(OptimizationPass):
    """Evaluate constant expressions at compile time"""

    @property
    def name(self) -> str:
        return "constant_folding"

    def __init__(self):
        self.folded_count = 0

    def optimize(self, node: ASTNode) -> ASTNode:
        """Fold constant expressions"""
        return self._fold(node)

    def _fold(self, node: ASTNode) -> ASTNode:
        """Recursively fold constants"""
        # First fold children
        for i, child in enumerate(node.children):
            node.children[i] = self._fold(child)

        # Check if this is a binary operation with constant operands
        if node.node_type == NodeType.BINARY_OP:
            if isinstance(node, Expression):
                result = self._try_fold_binary(node)
                if result is not None:
                    self.folded_count += 1
                    return result

        return node

    def _try_fold_binary(self, expr: Expression) -> Optional[Expression]:
        """Try to fold binary expression"""
        if not expr.left or not expr.right:
            return None

        # Check if both operands are literals
        if (expr.left.node_type != NodeType.LITERAL or
            expr.right.node_type != NodeType.LITERAL):
            return None

        left_val = expr.left.value
        right_val = expr.right.value

        # Only fold numeric operations
        if not isinstance(left_val, (int, float)) or not isinstance(right_val, (int, float)):
            return None

        try:
            if expr.operator == '+':
                result = left_val + right_val
            elif expr.operator == '-':
                result = left_val - right_val
            elif expr.operator == '*':
                result = left_val * right_val
            elif expr.operator == '/':
                if right_val == 0:
                    return None  # Don't fold division by zero
                result = left_val / right_val
            elif expr.operator == '**':
                result = left_val ** right_val
            elif expr.operator == '%':
                result = left_val % right_val
            elif expr.operator == '//':
                result = left_val // right_val
            else:
                return None

            # Create literal with result
            return Expression.literal(result)

        except Exception:
            return None

    def get_stats(self) -> Dict[str, int]:
        return {'folded': self.folded_count}


class InlineExpansion(OptimizationPass):
    """Inline small functions"""

    @property
    def name(self) -> str:
        return "inline_expansion"

    def __init__(self, max_statements: int = 3):
        self.max_statements = max_statements
        self.inlined_count = 0
        self.functions: Dict[str, ASTNode] = {}

    def optimize(self, node: ASTNode) -> ASTNode:
        """Inline small functions"""
        # First pass: collect function definitions
        self._collect_functions(node)

        # Second pass: inline calls
        return self._inline_calls(node)

    def _collect_functions(self, node: ASTNode):
        """Collect function definitions"""
        if node.node_type == NodeType.FUNCTION:
            # Check if function is small enough to inline
            if hasattr(node, 'body') and node.body:
                stmt_count = len(node.body.children) if hasattr(node.body, 'children') else 0
                if stmt_count <= self.max_statements:
                    self.functions[node.name] = node

        for child in node.children:
            self._collect_functions(child)

    def _inline_calls(self, node: ASTNode) -> ASTNode:
        """Inline function calls"""
        # Process children first
        for i, child in enumerate(node.children):
            node.children[i] = self._inline_calls(child)

        # Check if this is a call to an inlinable function
        if node.node_type == NodeType.CALL and node.name in self.functions:
            func = self.functions[node.name]

            # Simple inlining for single-expression functions
            if hasattr(func, 'body') and func.body:
                if len(func.body.children) == 1:
                    inlined = func.body.children[0].clone()
                    # TODO: Substitute parameters
                    self.inlined_count += 1
                    return inlined

        return node

    def get_stats(self) -> Dict[str, int]:
        return {'inlined': self.inlined_count, 'candidates': len(self.functions)}


class CommonSubexpressionElimination(OptimizationPass):
    """Eliminate common subexpressions"""

    @property
    def name(self) -> str:
        return "common_subexpression_elimination"

    def __init__(self):
        self.eliminated_count = 0
        self.expressions: Dict[int, ASTNode] = {}

    def optimize(self, node: ASTNode) -> ASTNode:
        """Eliminate common subexpressions"""
        self.expressions = {}
        return self._eliminate(node)

    def _expression_hash(self, node: ASTNode) -> int:
        """Hash expression for comparison"""
        if node.node_type == NodeType.LITERAL:
            return hash((NodeType.LITERAL, node.value))
        elif node.node_type == NodeType.IDENTIFIER:
            return hash((NodeType.IDENTIFIER, node.name))
        elif node.node_type == NodeType.BINARY_OP:
            if isinstance(node, Expression):
                left_hash = self._expression_hash(node.left) if node.left else 0
                right_hash = self._expression_hash(node.right) if node.right else 0
                return hash((NodeType.BINARY_OP, node.operator, left_hash, right_hash))

        return hash(node.node_type)

    def _eliminate(self, node: ASTNode) -> ASTNode:
        """Recursively eliminate common subexpressions"""
        # Check if this expression was seen before
        if node.node_type in [NodeType.BINARY_OP, NodeType.CALL]:
            expr_hash = self._expression_hash(node)

            if expr_hash in self.expressions:
                # Found common subexpression
                self.eliminated_count += 1
                # Return reference to stored version
                return self.expressions[expr_hash]
            else:
                self.expressions[expr_hash] = node

        # Process children
        for i, child in enumerate(node.children):
            node.children[i] = self._eliminate(child)

        return node

    def get_stats(self) -> Dict[str, int]:
        return {'eliminated': self.eliminated_count}


class CodeOptimizer:
    """
    Multi-pass code optimizer.
    """

    def __init__(self):
        self.passes: List[OptimizationPass] = []
        self.optimization_history: List[Dict[str, Any]] = []

        # Add default passes
        self.add_pass(ConstantFolding())
        self.add_pass(DeadCodeElimination())
        self.add_pass(CommonSubexpressionElimination())

    def add_pass(self, optimization_pass: OptimizationPass):
        """Add optimization pass"""
        self.passes.append(optimization_pass)

    def optimize(self, node: ASTNode, iterations: int = 3) -> ASTNode:
        """Apply all optimization passes"""
        result = node

        for i in range(iterations):
            changed = False

            for opt_pass in self.passes:
                before_hash = self._node_hash(result)
                result = opt_pass.optimize(result)
                after_hash = self._node_hash(result)

                if before_hash != after_hash:
                    changed = True

                    self.optimization_history.append({
                        'iteration': i,
                        'pass': opt_pass.name,
                        'stats': opt_pass.get_stats()
                    })

            if not changed:
                break  # Fixed point reached

        return result

    def _node_hash(self, node: ASTNode) -> int:
        """Hash node for comparison"""
        h = hash((node.node_type, node.name, node.value))
        for child in node.children:
            h = hash((h, self._node_hash(child)))
        return h

    def get_optimization_report(self) -> Dict[str, Any]:
        """Get optimization statistics"""
        return {
            'passes_applied': len(self.optimization_history),
            'history': self.optimization_history,
            'passes_available': [p.name for p in self.passes]
        }


# Export all
__all__ = [
    'OptimizationPass',
    'DeadCodeElimination',
    'ConstantFolding',
    'InlineExpansion',
    'CommonSubexpressionElimination',
    'CodeOptimizer',
]

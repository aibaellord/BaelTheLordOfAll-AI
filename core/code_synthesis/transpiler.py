"""
⚡ TRANSPILER ⚡
===============
Code transpilation.

Features:
- AST transformation
- Language conversion
- Code analysis
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set
import uuid

from .code_core import ASTNode, NodeType, DataType, TypeInfo


@dataclass
class TranspilationRule:
    """A rule for transpilation"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""

    # Match criteria
    from_node_type: NodeType = None
    from_pattern: Dict[str, Any] = field(default_factory=dict)

    # Source/target languages
    from_language: str = ""
    to_language: str = ""

    # Transformation
    transform: Callable[[ASTNode], ASTNode] = None

    def matches(self, node: ASTNode) -> bool:
        """Check if rule matches node"""
        if self.from_node_type and node.node_type != self.from_node_type:
            return False

        for key, value in self.from_pattern.items():
            if hasattr(node, key) and getattr(node, key) != value:
                return False

        return True

    def apply(self, node: ASTNode) -> ASTNode:
        """Apply transformation"""
        if self.transform:
            return self.transform(node)
        return node


class ASTTransformer:
    """
    Transform AST trees.
    """

    def __init__(self):
        self.rules: List[TranspilationRule] = []
        self.transformations_applied = 0

    def add_rule(self, rule: TranspilationRule):
        """Add transformation rule"""
        self.rules.append(rule)

    def transform(self, node: ASTNode) -> ASTNode:
        """Transform AST node and children"""
        # Apply matching rules
        result = node
        for rule in self.rules:
            if rule.matches(result):
                result = rule.apply(result)
                self.transformations_applied += 1

        # Transform children
        new_children = []
        for child in result.children:
            new_children.append(self.transform(child))
        result.children = new_children

        return result

    def add_type_inference(self):
        """Add type inference transformation"""
        def infer_type(node: ASTNode) -> ASTNode:
            if node.node_type == NodeType.LITERAL:
                if isinstance(node.value, int):
                    node.type_info = TypeInfo(base_type=DataType.INT)
                elif isinstance(node.value, float):
                    node.type_info = TypeInfo(base_type=DataType.FLOAT)
                elif isinstance(node.value, str):
                    node.type_info = TypeInfo(base_type=DataType.STRING)
                elif isinstance(node.value, bool):
                    node.type_info = TypeInfo(base_type=DataType.BOOL)
            return node

        self.add_rule(TranspilationRule(
            name="type_inference",
            from_node_type=NodeType.LITERAL,
            transform=infer_type
        ))

    def add_async_conversion(self, target_async: bool = True):
        """Add async/sync conversion"""
        def convert_async(node: ASTNode) -> ASTNode:
            if hasattr(node, 'is_async'):
                node.is_async = target_async
            return node

        self.add_rule(TranspilationRule(
            name="async_conversion",
            from_node_type=NodeType.FUNCTION,
            transform=convert_async
        ))


class CodeAnalyzer:
    """
    Analyze code structure.
    """

    def __init__(self):
        self.analysis_results: Dict[str, Any] = {}

    def analyze(self, node: ASTNode) -> Dict[str, Any]:
        """Analyze AST"""
        self.analysis_results = {
            'node_count': self._count_nodes(node),
            'max_depth': self._max_depth(node),
            'functions': self._find_functions(node),
            'classes': self._find_classes(node),
            'complexity': self._estimate_complexity(node),
            'dependencies': self._find_dependencies(node),
        }
        return self.analysis_results

    def _count_nodes(self, node: ASTNode) -> int:
        """Count total nodes"""
        count = 1
        for child in node.children:
            count += self._count_nodes(child)
        return count

    def _max_depth(self, node: ASTNode, current: int = 0) -> int:
        """Find maximum depth"""
        if not node.children:
            return current
        return max(self._max_depth(c, current + 1) for c in node.children)

    def _find_functions(self, node: ASTNode) -> List[str]:
        """Find function names"""
        functions = []
        if node.node_type == NodeType.FUNCTION:
            functions.append(node.name)
        for child in node.children:
            functions.extend(self._find_functions(child))
        return functions

    def _find_classes(self, node: ASTNode) -> List[str]:
        """Find class names"""
        classes = []
        if node.node_type == NodeType.CLASS:
            classes.append(node.name)
        for child in node.children:
            classes.extend(self._find_classes(child))
        return classes

    def _estimate_complexity(self, node: ASTNode) -> int:
        """Estimate cyclomatic complexity"""
        complexity = 0

        # Control flow adds complexity
        if node.node_type in [NodeType.IF, NodeType.FOR, NodeType.WHILE,
                               NodeType.SWITCH, NodeType.CATCH]:
            complexity += 1

        for child in node.children:
            complexity += self._estimate_complexity(child)

        return complexity

    def _find_dependencies(self, node: ASTNode) -> List[str]:
        """Find external dependencies (imports)"""
        deps = []
        if node.node_type == NodeType.IMPORT:
            deps.append(node.name)
        for child in node.children:
            deps.extend(self._find_dependencies(child))
        return deps

    def find_unused_variables(self, node: ASTNode) -> List[str]:
        """Find potentially unused variables"""
        declared = set()
        used = set()

        def collect(n: ASTNode):
            if n.node_type == NodeType.VARIABLE:
                declared.add(n.name)
            elif n.node_type == NodeType.IDENTIFIER:
                used.add(n.name)
            for child in n.children:
                collect(child)

        collect(node)
        return list(declared - used)

    def find_similar_code(self, node: ASTNode) -> List[List[ASTNode]]:
        """Find potentially duplicated code"""
        # Simplified: find functions with same structure
        functions = []

        def collect_functions(n: ASTNode):
            if n.node_type == NodeType.FUNCTION:
                functions.append(n)
            for child in n.children:
                collect_functions(child)

        collect_functions(node)

        # Group by structure hash
        groups: Dict[int, List[ASTNode]] = {}
        for func in functions:
            struct_hash = self._structure_hash(func)
            if struct_hash not in groups:
                groups[struct_hash] = []
            groups[struct_hash].append(func)

        # Return groups with duplicates
        return [g for g in groups.values() if len(g) > 1]

    def _structure_hash(self, node: ASTNode) -> int:
        """Hash node structure (ignoring names/values)"""
        h = hash(node.node_type)
        for child in node.children:
            h = hash((h, self._structure_hash(child)))
        return h


class Transpiler:
    """
    Full transpilation pipeline.
    """

    def __init__(self):
        self.transformer = ASTTransformer()
        self.analyzer = CodeAnalyzer()

        # Language-specific rules
        self.language_rules: Dict[tuple, List[TranspilationRule]] = {}

    def add_language_rules(
        self,
        from_lang: str,
        to_lang: str,
        rules: List[TranspilationRule]
    ):
        """Add rules for language pair"""
        key = (from_lang, to_lang)
        if key not in self.language_rules:
            self.language_rules[key] = []
        self.language_rules[key].extend(rules)

    def transpile(
        self,
        ast: ASTNode,
        from_lang: str,
        to_lang: str
    ) -> ASTNode:
        """Transpile AST from one language to another"""
        # Get rules for this language pair
        key = (from_lang, to_lang)
        rules = self.language_rules.get(key, [])

        # Apply rules
        self.transformer.rules = rules
        result = self.transformer.transform(ast)

        # Update language metadata
        result.metadata['language'] = to_lang

        return result

    def get_transpilation_report(self) -> Dict[str, Any]:
        """Get transpilation statistics"""
        return {
            'transformations_applied': self.transformer.transformations_applied,
            'language_pairs': list(self.language_rules.keys()),
            'total_rules': sum(len(r) for r in self.language_rules.values())
        }


# Export all
__all__ = [
    'TranspilationRule',
    'ASTTransformer',
    'CodeAnalyzer',
    'Transpiler',
]

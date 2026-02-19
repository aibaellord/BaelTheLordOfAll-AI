"""
BAEL Mutation Engine
=====================

Code mutation strategies for genetic programming.
Applies controlled changes to code genomes.

Features:
- Multiple mutation types
- Configurable mutation rates
- Semantic-preserving mutations
- Syntax validation
- Mutation history
"""

import ast
import copy
import hashlib
import logging
import random
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

from .code_genome import CodeGenome, Gene, GeneType

logger = logging.getLogger(__name__)


class MutationType(Enum):
    """Types of mutations."""
    # Structural mutations
    INSERT = "insert"  # Add new code
    DELETE = "delete"  # Remove code
    REPLACE = "replace"  # Replace code
    SWAP = "swap"  # Swap code elements

    # Expression mutations
    OPERATOR_CHANGE = "operator_change"  # Change operators
    LITERAL_CHANGE = "literal_change"  # Change literals
    VARIABLE_RENAME = "variable_rename"  # Rename variables

    # Control flow mutations
    CONDITION_INVERT = "condition_invert"  # Invert conditions
    LOOP_MODIFY = "loop_modify"  # Modify loop bounds

    # Function mutations
    PARAMETER_ADD = "parameter_add"  # Add parameter
    PARAMETER_REMOVE = "parameter_remove"  # Remove parameter
    RETURN_MODIFY = "return_modify"  # Modify return value


class MutationStrategy(Enum):
    """Mutation strategies."""
    RANDOM = "random"  # Random mutations
    TARGETED = "targeted"  # Target specific genes
    CONSERVATIVE = "conservative"  # Small, safe mutations
    AGGRESSIVE = "aggressive"  # Large, risky mutations
    ADAPTIVE = "adaptive"  # Adapt based on fitness


@dataclass
class Mutation:
    """A mutation applied to code."""
    id: str
    mutation_type: MutationType

    # Target
    gene_id: str
    gene_type: GeneType

    # Change
    original: str
    mutated: str

    # Context
    description: str = ""

    # Validation
    is_valid: bool = True
    syntax_error: Optional[str] = None

    # Metadata
    applied_at: datetime = field(default_factory=datetime.now)


class MutationEngine:
    """
    Mutation engine for BAEL.

    Applies mutations to code genomes.
    """

    # Operator replacements
    OPERATOR_REPLACEMENTS = {
        '+': ['-', '*', '/'],
        '-': ['+', '*', '/'],
        '*': ['+', '-', '/'],
        '/': ['+', '-', '*'],
        '<': ['<=', '>', '>=', '==', '!='],
        '>': ['>=', '<', '<=', '==', '!='],
        '<=': ['<', '>', '>=', '=='],
        '>=': ['>', '<', '<=', '=='],
        '==': ['!=', '<', '>', '<=', '>='],
        '!=': ['==', '<', '>', '<=', '>='],
        'and': ['or'],
        'or': ['and'],
    }

    # Common literal mutations
    LITERAL_MUTATIONS = {
        '0': ['1', '-1', '2'],
        '1': ['0', '2', '-1'],
        'True': ['False'],
        'False': ['True'],
        '[]': ['[None]', 'None'],
        '{}': ['{None: None}', 'None'],
        'None': ['0', "''", '[]'],
    }

    def __init__(
        self,
        mutation_rate: float = 0.1,
        strategy: MutationStrategy = MutationStrategy.CONSERVATIVE,
    ):
        self.mutation_rate = mutation_rate
        self.strategy = strategy

        # Mutation history
        self._history: List[Mutation] = []

        # Mutation weights by type
        self._weights = self._get_strategy_weights()

        # Stats
        self.stats = {
            "mutations_attempted": 0,
            "mutations_successful": 0,
            "mutations_failed": 0,
        }

    def _get_strategy_weights(self) -> Dict[MutationType, float]:
        """Get mutation weights based on strategy."""
        if self.strategy == MutationStrategy.CONSERVATIVE:
            return {
                MutationType.LITERAL_CHANGE: 0.3,
                MutationType.OPERATOR_CHANGE: 0.3,
                MutationType.VARIABLE_RENAME: 0.2,
                MutationType.REPLACE: 0.1,
                MutationType.INSERT: 0.05,
                MutationType.DELETE: 0.05,
            }
        elif self.strategy == MutationStrategy.AGGRESSIVE:
            return {
                MutationType.INSERT: 0.2,
                MutationType.DELETE: 0.2,
                MutationType.REPLACE: 0.2,
                MutationType.SWAP: 0.15,
                MutationType.OPERATOR_CHANGE: 0.15,
                MutationType.LITERAL_CHANGE: 0.1,
            }
        else:  # RANDOM or default
            return {mut_type: 1.0 for mut_type in MutationType}

    def mutate(
        self,
        genome: CodeGenome,
        num_mutations: int = 1,
    ) -> tuple[CodeGenome, List[Mutation]]:
        """
        Apply mutations to a genome.

        Args:
            genome: Genome to mutate
            num_mutations: Number of mutations to apply

        Returns:
            (mutated genome, list of mutations)
        """
        mutated = genome.clone()
        mutations = []

        for _ in range(num_mutations):
            # Select mutation type
            mutation_type = self._select_mutation_type()

            # Apply mutation
            mutation = self._apply_mutation(mutated, mutation_type)

            if mutation:
                mutations.append(mutation)
                self._history.append(mutation)

                if mutation.is_valid:
                    mutated.mutation_count += 1
                    self.stats["mutations_successful"] += 1
                else:
                    self.stats["mutations_failed"] += 1

            self.stats["mutations_attempted"] += 1

        return mutated, mutations

    def _select_mutation_type(self) -> MutationType:
        """Select a mutation type based on weights."""
        types = list(self._weights.keys())
        weights = list(self._weights.values())

        total = sum(weights)
        weights = [w / total for w in weights]

        return random.choices(types, weights=weights)[0]

    def _apply_mutation(
        self,
        genome: CodeGenome,
        mutation_type: MutationType,
    ) -> Optional[Mutation]:
        """Apply a specific mutation type."""
        # Select target gene
        genes = list(genome.genes.values())
        if not genes:
            return None

        # Filter genes by compatible types
        compatible = self._get_compatible_genes(genes, mutation_type)
        if not compatible:
            return None

        gene = random.choice(compatible)

        # Apply mutation
        original = gene.content
        mutated = original
        description = ""

        if mutation_type == MutationType.OPERATOR_CHANGE:
            mutated, description = self._mutate_operator(original)
        elif mutation_type == MutationType.LITERAL_CHANGE:
            mutated, description = self._mutate_literal(original)
        elif mutation_type == MutationType.VARIABLE_RENAME:
            mutated, description = self._mutate_variable(original)
        elif mutation_type == MutationType.CONDITION_INVERT:
            mutated, description = self._mutate_condition(original)
        elif mutation_type == MutationType.REPLACE:
            mutated, description = self._mutate_replace(gene)
        elif mutation_type == MutationType.DELETE:
            mutated, description = "", "Deleted gene"
        elif mutation_type == MutationType.INSERT:
            mutated, description = self._mutate_insert(original, gene)
        elif mutation_type == MutationType.SWAP:
            mutated, description = self._mutate_swap(genome, gene)

        if mutated == original:
            return None

        # Update gene
        gene.content = mutated
        gene.mutations += 1

        # Validate syntax
        is_valid = True
        syntax_error = None

        if genome.language == "python":
            try:
                ast.parse(mutated)
            except SyntaxError as e:
                is_valid = False
                syntax_error = str(e)
                # Revert mutation
                gene.content = original

        mutation_id = hashlib.md5(
            f"{gene.id}:{mutation_type.value}:{datetime.now()}".encode()
        ).hexdigest()[:12]

        return Mutation(
            id=mutation_id,
            mutation_type=mutation_type,
            gene_id=gene.id,
            gene_type=gene.gene_type,
            original=original,
            mutated=mutated,
            description=description,
            is_valid=is_valid,
            syntax_error=syntax_error,
        )

    def _get_compatible_genes(
        self,
        genes: List[Gene],
        mutation_type: MutationType,
    ) -> List[Gene]:
        """Get genes compatible with mutation type."""
        if mutation_type == MutationType.OPERATOR_CHANGE:
            return [g for g in genes if g.gene_type == GeneType.OPERATOR]
        elif mutation_type == MutationType.LITERAL_CHANGE:
            return [g for g in genes if g.gene_type == GeneType.LITERAL]
        elif mutation_type == MutationType.VARIABLE_RENAME:
            return [g for g in genes if g.gene_type == GeneType.VARIABLE]
        elif mutation_type == MutationType.CONDITION_INVERT:
            return [g for g in genes if g.gene_type == GeneType.CONTROL_FLOW]
        else:
            return genes

    def _mutate_operator(self, code: str) -> tuple[str, str]:
        """Mutate operators in code."""
        for op, replacements in self.OPERATOR_REPLACEMENTS.items():
            if op in code:
                replacement = random.choice(replacements)
                mutated = code.replace(op, replacement, 1)
                return mutated, f"Changed '{op}' to '{replacement}'"
        return code, ""

    def _mutate_literal(self, code: str) -> tuple[str, str]:
        """Mutate literals in code."""
        for literal, replacements in self.LITERAL_MUTATIONS.items():
            if literal in code:
                replacement = random.choice(replacements)
                mutated = code.replace(literal, replacement, 1)
                return mutated, f"Changed '{literal}' to '{replacement}'"

        # Try numeric mutation
        import re
        numbers = re.findall(r'\b(\d+)\b', code)
        if numbers:
            num = random.choice(numbers)
            mutations = [str(int(num) + 1), str(int(num) - 1), str(int(num) * 2)]
            replacement = random.choice(mutations)
            mutated = re.sub(rf'\b{num}\b', replacement, code, count=1)
            return mutated, f"Changed '{num}' to '{replacement}'"

        return code, ""

    def _mutate_variable(self, code: str) -> tuple[str, str]:
        """Mutate variable names."""
        import re
        variables = re.findall(r'\b([a-z_][a-z0-9_]*)\b', code, re.IGNORECASE)

        if variables:
            var = random.choice(variables)
            if var not in ['if', 'else', 'for', 'while', 'def', 'class', 'return', 'import']:
                new_var = f"{var}_v{random.randint(1, 99)}"
                mutated = re.sub(rf'\b{var}\b', new_var, code)
                return mutated, f"Renamed '{var}' to '{new_var}'"

        return code, ""

    def _mutate_condition(self, code: str) -> tuple[str, str]:
        """Invert conditions."""
        if 'if ' in code:
            # Simple inversion
            if ' not ' in code:
                mutated = code.replace(' not ', ' ', 1)
                return mutated, "Removed 'not'"
            else:
                mutated = code.replace('if ', 'if not (', 1).rstrip(':') + '):'
                return mutated, "Added 'not'"

        return code, ""

    def _mutate_replace(self, gene: Gene) -> tuple[str, str]:
        """Replace gene content."""
        if gene.gene_type == GeneType.LITERAL:
            return "42", "Replaced with 42"
        elif gene.gene_type == GeneType.VARIABLE:
            return "x", "Replaced with 'x'"
        return gene.content, ""

    def _mutate_insert(self, code: str, gene: Gene) -> tuple[str, str]:
        """Insert new code."""
        insertions = {
            GeneType.FUNCTION: "pass",
            GeneType.STATEMENT: "pass",
            GeneType.EXPRESSION: "None",
        }

        insert = insertions.get(gene.gene_type, "pass")
        mutated = code + f"\n{insert}"
        return mutated, f"Inserted '{insert}'"

    def _mutate_swap(self, genome: CodeGenome, gene: Gene) -> tuple[str, str]:
        """Swap with another gene of same type."""
        same_type = [g for g in genome.genes.values()
                    if g.gene_type == gene.gene_type and g.id != gene.id]

        if same_type:
            other = random.choice(same_type)
            # Swap contents
            gene.content, other.content = other.content, gene.content
            return gene.content, f"Swapped with {other.id}"

        return gene.content, ""

    def get_mutation_history(
        self,
        limit: int = 100,
    ) -> List[Mutation]:
        """Get mutation history."""
        return self._history[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics."""
        return {
            **self.stats,
            "history_size": len(self._history),
            "success_rate": (
                self.stats["mutations_successful"] /
                max(self.stats["mutations_attempted"], 1)
            ),
        }


def demo():
    """Demonstrate mutation engine."""
    print("=" * 60)
    print("BAEL Mutation Engine Demo")
    print("=" * 60)

    from .code_genome import GenomeEncoder

    encoder = GenomeEncoder()
    engine = MutationEngine(
        mutation_rate=0.2,
        strategy=MutationStrategy.CONSERVATIVE,
    )

    # Sample code
    code = '''
def add(a, b):
    if a > 0:
        return a + b
    return 0
'''

    print(f"\nOriginal code:")
    print(code)

    # Encode
    genome = encoder.encode(code)
    print(f"\nGenome: {genome.gene_count} genes")

    # Apply mutations
    print("\nApplying 3 mutations...")
    mutated, mutations = engine.mutate(genome, num_mutations=3)

    print(f"\nMutations applied:")
    for m in mutations:
        status = "✓" if m.is_valid else "✗"
        print(f"  [{status}] {m.mutation_type.value}: {m.description}")
        if not m.is_valid:
            print(f"      Error: {m.syntax_error}")

    # Decode mutated genome
    mutated_code = encoder.decode(mutated)
    print(f"\nMutated code:")
    print(mutated_code)

    print(f"\nStats: {engine.get_stats()}")


if __name__ == "__main__":
    demo()

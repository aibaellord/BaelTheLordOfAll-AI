"""
BAEL Code Genome
=================

Representation of code as an evolvable genome.
Enables genetic operations on code structures.

Features:
- Code to genome encoding
- Gene representation
- Genome operations
- AST integration
- Serialization
"""

import ast
import copy
import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union

logger = logging.getLogger(__name__)


class GeneType(Enum):
    """Types of genes in code genome."""
    FUNCTION = "function"
    CLASS = "class"
    PARAMETER = "parameter"
    VARIABLE = "variable"
    OPERATOR = "operator"
    LITERAL = "literal"
    CONTROL_FLOW = "control_flow"
    IMPORT = "import"
    DECORATOR = "decorator"
    EXPRESSION = "expression"
    STATEMENT = "statement"


@dataclass
class Gene:
    """A gene representing a code element."""
    id: str
    gene_type: GeneType

    # Content
    content: str  # Source code
    name: Optional[str] = None

    # Structure
    children: List[str] = field(default_factory=list)  # Child gene IDs
    parent: Optional[str] = None

    # Position
    line_start: int = 0
    line_end: int = 0

    # Metadata
    attributes: Dict[str, Any] = field(default_factory=dict)

    # Evolution
    generation: int = 0
    mutations: int = 0


@dataclass
class CodeGenome:
    """A genome representing a piece of code."""
    id: str

    # Genes
    genes: Dict[str, Gene] = field(default_factory=dict)
    root_genes: List[str] = field(default_factory=list)  # Top-level gene IDs

    # Source
    source_code: str = ""
    language: str = "python"

    # Metadata
    fitness: float = 0.0
    generation: int = 0
    lineage: List[str] = field(default_factory=list)  # Parent genome IDs

    # Stats
    gene_count: int = 0
    mutation_count: int = 0

    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)

    def add_gene(self, gene: Gene) -> None:
        """Add a gene to the genome."""
        self.genes[gene.id] = gene
        self.gene_count = len(self.genes)

    def get_gene(self, gene_id: str) -> Optional[Gene]:
        """Get a gene by ID."""
        return self.genes.get(gene_id)

    def get_genes_by_type(self, gene_type: GeneType) -> List[Gene]:
        """Get all genes of a specific type."""
        return [g for g in self.genes.values() if g.gene_type == gene_type]

    def clone(self) -> "CodeGenome":
        """Create a deep copy of the genome."""
        cloned = copy.deepcopy(self)
        cloned.id = hashlib.md5(f"{self.id}:clone:{datetime.now()}".encode()).hexdigest()[:12]
        cloned.lineage = self.lineage + [self.id]
        cloned.generation = self.generation + 1
        return cloned


class GenomeEncoder:
    """
    Encodes source code into a genome representation.
    """

    def __init__(self):
        self._gene_counter = 0
        self.stats = {
            "genomes_encoded": 0,
            "genes_created": 0,
        }

    def encode(self, source_code: str, language: str = "python") -> CodeGenome:
        """
        Encode source code into a genome.

        Args:
            source_code: Source code to encode
            language: Programming language

        Returns:
            CodeGenome representation
        """
        genome_id = hashlib.md5(source_code.encode()).hexdigest()[:12]

        genome = CodeGenome(
            id=genome_id,
            source_code=source_code,
            language=language,
        )

        if language == "python":
            self._encode_python(source_code, genome)
        else:
            # Fallback: treat as single gene
            gene = self._create_gene(GeneType.STATEMENT, source_code)
            genome.add_gene(gene)
            genome.root_genes.append(gene.id)

        self.stats["genomes_encoded"] += 1

        return genome

    def _encode_python(self, source_code: str, genome: CodeGenome) -> None:
        """Encode Python code into genome."""
        try:
            tree = ast.parse(source_code)

            for node in ast.iter_child_nodes(tree):
                gene = self._encode_node(node, source_code, genome)
                if gene:
                    genome.root_genes.append(gene.id)

        except SyntaxError as e:
            logger.warning(f"Syntax error in source code: {e}")
            # Fallback: single statement gene
            gene = self._create_gene(GeneType.STATEMENT, source_code)
            genome.add_gene(gene)
            genome.root_genes.append(gene.id)

    def _encode_node(
        self,
        node: ast.AST,
        source: str,
        genome: CodeGenome,
        parent_id: Optional[str] = None,
    ) -> Optional[Gene]:
        """Encode an AST node into a gene."""
        gene_type = self._node_to_gene_type(node)

        # Get source code for this node
        try:
            if hasattr(node, 'lineno') and hasattr(node, 'end_lineno'):
                lines = source.split('\n')
                start = node.lineno - 1
                end = node.end_lineno if node.end_lineno else start + 1
                content = '\n'.join(lines[start:end])
            else:
                content = ast.dump(node)
        except Exception:
            content = str(node)

        gene = self._create_gene(gene_type, content)
        gene.parent = parent_id

        # Set position
        if hasattr(node, 'lineno'):
            gene.line_start = node.lineno
        if hasattr(node, 'end_lineno'):
            gene.line_end = node.end_lineno or gene.line_start

        # Extract name if applicable
        if hasattr(node, 'name'):
            gene.name = node.name
        elif hasattr(node, 'id'):
            gene.name = node.id

        # Store node type
        gene.attributes['ast_type'] = type(node).__name__

        genome.add_gene(gene)

        # Encode children
        for child in ast.iter_child_nodes(node):
            child_gene = self._encode_node(child, source, genome, gene.id)
            if child_gene:
                gene.children.append(child_gene.id)

        return gene

    def _node_to_gene_type(self, node: ast.AST) -> GeneType:
        """Convert AST node type to gene type."""
        type_mapping = {
            ast.FunctionDef: GeneType.FUNCTION,
            ast.AsyncFunctionDef: GeneType.FUNCTION,
            ast.ClassDef: GeneType.CLASS,
            ast.Import: GeneType.IMPORT,
            ast.ImportFrom: GeneType.IMPORT,
            ast.If: GeneType.CONTROL_FLOW,
            ast.For: GeneType.CONTROL_FLOW,
            ast.While: GeneType.CONTROL_FLOW,
            ast.Try: GeneType.CONTROL_FLOW,
            ast.With: GeneType.CONTROL_FLOW,
            ast.BinOp: GeneType.OPERATOR,
            ast.UnaryOp: GeneType.OPERATOR,
            ast.Compare: GeneType.OPERATOR,
            ast.BoolOp: GeneType.OPERATOR,
            ast.Constant: GeneType.LITERAL,
            ast.Num: GeneType.LITERAL,  # Python 3.7
            ast.Str: GeneType.LITERAL,  # Python 3.7
            ast.Name: GeneType.VARIABLE,
            ast.arg: GeneType.PARAMETER,
        }

        return type_mapping.get(type(node), GeneType.EXPRESSION)

    def _create_gene(self, gene_type: GeneType, content: str) -> Gene:
        """Create a new gene."""
        self._gene_counter += 1
        gene_id = f"gene_{self._gene_counter}_{hashlib.md5(content[:50].encode()).hexdigest()[:8]}"

        self.stats["genes_created"] += 1

        return Gene(
            id=gene_id,
            gene_type=gene_type,
            content=content,
        )

    def decode(self, genome: CodeGenome) -> str:
        """
        Decode a genome back to source code.

        Args:
            genome: Genome to decode

        Returns:
            Source code
        """
        # Simple approach: concatenate root genes
        parts = []

        for gene_id in genome.root_genes:
            gene = genome.get_gene(gene_id)
            if gene:
                parts.append(gene.content)

        return '\n\n'.join(parts)

    def crossover(
        self,
        parent1: CodeGenome,
        parent2: CodeGenome,
        crossover_point: float = 0.5,
    ) -> CodeGenome:
        """
        Perform crossover between two genomes.

        Args:
            parent1: First parent genome
            parent2: Second parent genome
            crossover_point: Point of crossover (0-1)

        Returns:
            Child genome
        """
        child = parent1.clone()

        # Get genes from each parent
        genes1 = list(parent1.genes.values())
        genes2 = list(parent2.genes.values())

        # Calculate crossover index
        cross_idx = int(len(genes1) * crossover_point)

        # Take first part from parent1, second from parent2
        new_genes = genes1[:cross_idx]

        # Add compatible genes from parent2
        for gene in genes2[cross_idx:]:
            # Only add if same type exists in parent1
            same_type = [g for g in genes1 if g.gene_type == gene.gene_type]
            if same_type:
                new_genes.append(gene)

        # Rebuild genome
        child.genes.clear()
        child.root_genes.clear()

        for gene in new_genes:
            gene_copy = copy.deepcopy(gene)
            child.add_gene(gene_copy)
            if not gene_copy.parent:
                child.root_genes.append(gene_copy.id)

        child.lineage = [parent1.id, parent2.id]

        return child

    def get_stats(self) -> Dict[str, Any]:
        """Get encoder statistics."""
        return self.stats


def demo():
    """Demonstrate code genome."""
    print("=" * 60)
    print("BAEL Code Genome Demo")
    print("=" * 60)

    encoder = GenomeEncoder()

    # Sample code
    code = '''
def fibonacci(n):
    """Calculate fibonacci number."""
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

def factorial(n):
    """Calculate factorial."""
    if n <= 1:
        return 1
    return n * factorial(n-1)

class Calculator:
    def add(self, a, b):
        return a + b

    def multiply(self, a, b):
        return a * b
'''

    print("\nEncoding source code...")
    genome = encoder.encode(code)

    print(f"\nGenome ID: {genome.id}")
    print(f"Language: {genome.language}")
    print(f"Total genes: {genome.gene_count}")
    print(f"Root genes: {len(genome.root_genes)}")

    print("\nGenes by type:")
    for gene_type in GeneType:
        genes = genome.get_genes_by_type(gene_type)
        if genes:
            print(f"  {gene_type.value}: {len(genes)}")

    print("\nTop-level genes:")
    for gene_id in genome.root_genes:
        gene = genome.get_gene(gene_id)
        if gene:
            name = gene.name or "(unnamed)"
            print(f"  - {gene.gene_type.value}: {name}")

    # Clone genome
    print("\nCloning genome...")
    cloned = genome.clone()
    print(f"  Original ID: {genome.id}")
    print(f"  Clone ID: {cloned.id}")
    print(f"  Clone generation: {cloned.generation}")
    print(f"  Lineage: {cloned.lineage}")

    # Decode
    print("\nDecoding genome back to code...")
    decoded = encoder.decode(genome)
    print(f"  Decoded {len(decoded)} characters")

    print(f"\nEncoder stats: {encoder.get_stats()}")


if __name__ == "__main__":
    demo()

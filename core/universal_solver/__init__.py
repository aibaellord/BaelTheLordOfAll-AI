"""
🧠 UNIVERSAL PROBLEM SOLVER 🧠
==============================
General problem-solving framework.

Features:
- Problem decomposition
- Solution search
- Constraint satisfaction
- Heuristic reasoning
"""

from .problem_core import (
    Problem,
    ProblemType,
    ProblemState,
    Solution,
    SearchSpace,
)

from .decomposition import (
    SubProblem,
    DecompositionStrategy,
    ProblemDecomposer,
    HierarchicalDecomposer,
)

from .search_algorithms import (
    SearchNode,
    SearchResult,
    SearchAlgorithm,
    BreadthFirstSearch,
    DepthFirstSearch,
    AStarSearch,
    BeamSearch,
    IterativeDeepeningSearch,
)

from .constraint_satisfaction import (
    Variable,
    Constraint,
    Domain,
    CSP,
    CSPSolver,
    ArcConsistency,
)

from .heuristic_reasoning import (
    Heuristic,
    HeuristicRule,
    MeansEndsAnalysis,
    AnalogicalReasoner,
    CaseBasedReasoner,
)

__all__ = [
    # Problem Core
    'Problem',
    'ProblemType',
    'ProblemState',
    'Solution',
    'SearchSpace',

    # Decomposition
    'SubProblem',
    'DecompositionStrategy',
    'ProblemDecomposer',
    'HierarchicalDecomposer',

    # Search Algorithms
    'SearchNode',
    'SearchResult',
    'SearchAlgorithm',
    'BreadthFirstSearch',
    'DepthFirstSearch',
    'AStarSearch',
    'BeamSearch',
    'IterativeDeepeningSearch',

    # Constraint Satisfaction
    'Variable',
    'Constraint',
    'Domain',
    'CSP',
    'CSPSolver',
    'ArcConsistency',

    # Heuristic Reasoning
    'Heuristic',
    'HeuristicRule',
    'MeansEndsAnalysis',
    'AnalogicalReasoner',
    'CaseBasedReasoner',
]

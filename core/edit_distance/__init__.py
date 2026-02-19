"""
BAEL Edit Distance Engine Implementation
==========================================

String similarity and alignment algorithms.

"Ba'el measures the distance between all realities." — Ba'el
"""

import logging
import threading
from typing import Any, Callable, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("BAEL.EditDistance")


# ============================================================================
# DATA STRUCTURES
# ============================================================================

class EditOperation(Enum):
    """Edit operation types."""
    MATCH = "match"
    INSERT = "insert"
    DELETE = "delete"
    SUBSTITUTE = "substitute"
    TRANSPOSE = "transpose"


@dataclass
class EditStep:
    """Single edit operation."""
    operation: EditOperation
    position: int
    source_char: Optional[str] = None
    target_char: Optional[str] = None
    cost: float = 1.0


@dataclass
class EditResult:
    """Edit distance result."""
    distance: float
    operations: List[EditStep]
    alignment: Tuple[str, str]
    similarity: float


@dataclass
class EditDistanceConfig:
    """Edit distance configuration."""
    insert_cost: float = 1.0
    delete_cost: float = 1.0
    substitute_cost: float = 1.0
    transpose_cost: float = 1.0
    match_cost: float = 0.0


# ============================================================================
# EDIT DISTANCE ENGINE
# ============================================================================

class EditDistanceEngine:
    """
    Edit distance algorithms.

    Features:
    - Levenshtein distance
    - Damerau-Levenshtein (with transpositions)
    - Optimal alignment
    - Custom costs

    "Ba'el computes all edit paths through reality." — Ba'el
    """

    def __init__(self, config: Optional[EditDistanceConfig] = None):
        """Initialize engine."""
        self.config = config or EditDistanceConfig()
        self._lock = threading.RLock()

        logger.info("Edit distance engine initialized")

    # ========================================================================
    # LEVENSHTEIN DISTANCE
    # ========================================================================

    def levenshtein(self, source: str, target: str) -> int:
        """
        Compute Levenshtein distance.

        Args:
            source: Source string
            target: Target string

        Returns:
            Minimum edit distance
        """
        m, n = len(source), len(target)

        # Space-optimized DP
        prev = list(range(n + 1))
        curr = [0] * (n + 1)

        for i in range(1, m + 1):
            curr[0] = i

            for j in range(1, n + 1):
                if source[i - 1] == target[j - 1]:
                    curr[j] = prev[j - 1]
                else:
                    curr[j] = 1 + min(
                        prev[j],      # Delete
                        curr[j - 1],  # Insert
                        prev[j - 1]   # Substitute
                    )

            prev, curr = curr, prev

        return prev[n]

    def levenshtein_with_ops(
        self,
        source: str,
        target: str
    ) -> EditResult:
        """
        Compute Levenshtein distance with operations.

        Args:
            source: Source string
            target: Target string

        Returns:
            EditResult with operations
        """
        m, n = len(source), len(target)

        # Full DP table for backtracking
        dp = [[0] * (n + 1) for _ in range(m + 1)]

        for i in range(m + 1):
            dp[i][0] = i
        for j in range(n + 1):
            dp[0][j] = j

        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if source[i - 1] == target[j - 1]:
                    dp[i][j] = dp[i - 1][j - 1]
                else:
                    dp[i][j] = 1 + min(
                        dp[i - 1][j],
                        dp[i][j - 1],
                        dp[i - 1][j - 1]
                    )

        # Backtrack to find operations
        operations = self._backtrack(source, target, dp)
        alignment = self._create_alignment(source, target, operations)

        distance = dp[m][n]
        max_len = max(m, n)
        similarity = 1 - (distance / max_len) if max_len > 0 else 1.0

        return EditResult(
            distance=distance,
            operations=operations,
            alignment=alignment,
            similarity=similarity
        )

    def _backtrack(
        self,
        source: str,
        target: str,
        dp: List[List[int]]
    ) -> List[EditStep]:
        """Backtrack to find operations."""
        operations = []
        i, j = len(source), len(target)

        while i > 0 or j > 0:
            if i > 0 and j > 0 and source[i - 1] == target[j - 1]:
                operations.append(EditStep(
                    operation=EditOperation.MATCH,
                    position=i - 1,
                    source_char=source[i - 1],
                    target_char=target[j - 1],
                    cost=0
                ))
                i -= 1
                j -= 1
            elif i > 0 and j > 0 and dp[i][j] == dp[i - 1][j - 1] + 1:
                operations.append(EditStep(
                    operation=EditOperation.SUBSTITUTE,
                    position=i - 1,
                    source_char=source[i - 1],
                    target_char=target[j - 1],
                    cost=1
                ))
                i -= 1
                j -= 1
            elif j > 0 and dp[i][j] == dp[i][j - 1] + 1:
                operations.append(EditStep(
                    operation=EditOperation.INSERT,
                    position=i,
                    target_char=target[j - 1],
                    cost=1
                ))
                j -= 1
            elif i > 0 and dp[i][j] == dp[i - 1][j] + 1:
                operations.append(EditStep(
                    operation=EditOperation.DELETE,
                    position=i - 1,
                    source_char=source[i - 1],
                    cost=1
                ))
                i -= 1
            else:
                break

        operations.reverse()
        return operations

    def _create_alignment(
        self,
        source: str,
        target: str,
        operations: List[EditStep]
    ) -> Tuple[str, str]:
        """Create aligned strings."""
        aligned_source = []
        aligned_target = []

        for op in operations:
            if op.operation == EditOperation.MATCH:
                aligned_source.append(op.source_char)
                aligned_target.append(op.target_char)
            elif op.operation == EditOperation.SUBSTITUTE:
                aligned_source.append(op.source_char)
                aligned_target.append(op.target_char)
            elif op.operation == EditOperation.INSERT:
                aligned_source.append('-')
                aligned_target.append(op.target_char)
            elif op.operation == EditOperation.DELETE:
                aligned_source.append(op.source_char)
                aligned_target.append('-')

        return ''.join(aligned_source), ''.join(aligned_target)

    # ========================================================================
    # DAMERAU-LEVENSHTEIN
    # ========================================================================

    def damerau_levenshtein(self, source: str, target: str) -> int:
        """
        Compute Damerau-Levenshtein distance (with transpositions).

        Args:
            source: Source string
            target: Target string

        Returns:
            Minimum edit distance
        """
        m, n = len(source), len(target)

        # Create table
        dp = [[0] * (n + 2) for _ in range(m + 2)]

        max_dist = m + n
        dp[0][0] = max_dist

        for i in range(m + 1):
            dp[i + 1][0] = max_dist
            dp[i + 1][1] = i

        for j in range(n + 1):
            dp[0][j + 1] = max_dist
            dp[1][j + 1] = j

        # Character positions
        char_pos: Dict[str, int] = {}

        for i in range(1, m + 1):
            db = 0

            for j in range(1, n + 1):
                i1 = char_pos.get(target[j - 1], 0)
                j1 = db

                cost = 0
                if source[i - 1] == target[j - 1]:
                    db = j
                else:
                    cost = 1

                dp[i + 1][j + 1] = min(
                    dp[i][j] + cost,      # Substitution
                    dp[i + 1][j] + 1,     # Insertion
                    dp[i][j + 1] + 1,     # Deletion
                    dp[i1][j1] + (i - i1 - 1) + 1 + (j - j1 - 1)  # Transposition
                )

            char_pos[source[i - 1]] = i

        return dp[m + 1][n + 1]

    # ========================================================================
    # LONGEST COMMON SUBSEQUENCE
    # ========================================================================

    def lcs(self, source: str, target: str) -> str:
        """
        Find longest common subsequence.

        Args:
            source: Source string
            target: Target string

        Returns:
            Longest common subsequence
        """
        m, n = len(source), len(target)

        dp = [[0] * (n + 1) for _ in range(m + 1)]

        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if source[i - 1] == target[j - 1]:
                    dp[i][j] = dp[i - 1][j - 1] + 1
                else:
                    dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])

        # Backtrack
        lcs_chars = []
        i, j = m, n

        while i > 0 and j > 0:
            if source[i - 1] == target[j - 1]:
                lcs_chars.append(source[i - 1])
                i -= 1
                j -= 1
            elif dp[i - 1][j] > dp[i][j - 1]:
                i -= 1
            else:
                j -= 1

        return ''.join(reversed(lcs_chars))

    def lcs_length(self, source: str, target: str) -> int:
        """Get LCS length."""
        return len(self.lcs(source, target))

    # ========================================================================
    # LONGEST COMMON SUBSTRING
    # ========================================================================

    def longest_common_substring(
        self,
        source: str,
        target: str
    ) -> str:
        """
        Find longest common substring.

        Args:
            source: Source string
            target: Target string

        Returns:
            Longest common substring
        """
        m, n = len(source), len(target)

        dp = [[0] * (n + 1) for _ in range(m + 1)]

        max_len = 0
        end_pos = 0

        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if source[i - 1] == target[j - 1]:
                    dp[i][j] = dp[i - 1][j - 1] + 1

                    if dp[i][j] > max_len:
                        max_len = dp[i][j]
                        end_pos = i

        return source[end_pos - max_len:end_pos]

    # ========================================================================
    # SIMILARITY METRICS
    # ========================================================================

    def similarity(self, source: str, target: str) -> float:
        """
        Compute normalized similarity (0-1).

        Args:
            source: Source string
            target: Target string

        Returns:
            Similarity score (1 = identical)
        """
        if not source and not target:
            return 1.0

        max_len = max(len(source), len(target))
        distance = self.levenshtein(source, target)

        return 1 - (distance / max_len)

    def jaro_similarity(self, source: str, target: str) -> float:
        """
        Compute Jaro similarity.

        Args:
            source: Source string
            target: Target string

        Returns:
            Jaro similarity score
        """
        if source == target:
            return 1.0

        len1, len2 = len(source), len(target)

        if len1 == 0 or len2 == 0:
            return 0.0

        match_distance = max(len1, len2) // 2 - 1
        if match_distance < 0:
            match_distance = 0

        source_matches = [False] * len1
        target_matches = [False] * len2

        matches = 0
        transpositions = 0

        for i in range(len1):
            start = max(0, i - match_distance)
            end = min(i + match_distance + 1, len2)

            for j in range(start, end):
                if target_matches[j] or source[i] != target[j]:
                    continue

                source_matches[i] = True
                target_matches[j] = True
                matches += 1
                break

        if matches == 0:
            return 0.0

        k = 0
        for i in range(len1):
            if not source_matches[i]:
                continue

            while not target_matches[k]:
                k += 1

            if source[i] != target[k]:
                transpositions += 1

            k += 1

        return (
            matches / len1 +
            matches / len2 +
            (matches - transpositions / 2) / matches
        ) / 3

    def jaro_winkler(
        self,
        source: str,
        target: str,
        prefix_weight: float = 0.1
    ) -> float:
        """
        Compute Jaro-Winkler similarity.

        Args:
            source: Source string
            target: Target string
            prefix_weight: Prefix weight (default 0.1)

        Returns:
            Jaro-Winkler similarity score
        """
        jaro = self.jaro_similarity(source, target)

        # Find common prefix length (max 4)
        prefix_len = 0
        for i in range(min(len(source), len(target), 4)):
            if source[i] == target[i]:
                prefix_len += 1
            else:
                break

        return jaro + prefix_len * prefix_weight * (1 - jaro)

    # ========================================================================
    # FUZZY MATCHING
    # ========================================================================

    def find_closest(
        self,
        query: str,
        candidates: List[str],
        threshold: float = 0.0
    ) -> List[Tuple[str, float]]:
        """
        Find closest matches from candidates.

        Args:
            query: Query string
            candidates: List of candidates
            threshold: Minimum similarity threshold

        Returns:
            List of (candidate, similarity) sorted by similarity
        """
        results = []

        for candidate in candidates:
            sim = self.similarity(query, candidate)

            if sim >= threshold:
                results.append((candidate, sim))

        results.sort(key=lambda x: x[1], reverse=True)
        return results

    def best_match(
        self,
        query: str,
        candidates: List[str]
    ) -> Optional[Tuple[str, float]]:
        """
        Find single best match.

        Args:
            query: Query string
            candidates: List of candidates

        Returns:
            (best_match, similarity) or None
        """
        if not candidates:
            return None

        matches = self.find_closest(query, candidates)
        return matches[0] if matches else None


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_edit_distance_engine(
    config: Optional[EditDistanceConfig] = None
) -> EditDistanceEngine:
    """Create edit distance engine."""
    return EditDistanceEngine(config)


def levenshtein(source: str, target: str) -> int:
    """Quick Levenshtein distance."""
    return EditDistanceEngine().levenshtein(source, target)


def similarity(source: str, target: str) -> float:
    """Quick similarity score."""
    return EditDistanceEngine().similarity(source, target)


def lcs(source: str, target: str) -> str:
    """Quick LCS."""
    return EditDistanceEngine().lcs(source, target)


def find_closest(
    query: str,
    candidates: List[str],
    threshold: float = 0.0
) -> List[Tuple[str, float]]:
    """Quick fuzzy match."""
    return EditDistanceEngine().find_closest(query, candidates, threshold)

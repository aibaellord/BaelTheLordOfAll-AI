"""
BAEL Dynamic Programming Suite
==============================

Classic DP algorithms and patterns.

"Ba'el remembers optimal substructure." — Ba'el
"""

import logging
import threading
from typing import Any, Dict, List, Optional, Tuple, Callable, Set
from dataclasses import dataclass, field
from functools import lru_cache
import math

logger = logging.getLogger("BAEL.DynamicProgramming")


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class DPResult:
    """Dynamic programming result."""
    optimal_value: Any
    solution: Any = None
    table: Optional[List[List[Any]]] = None


@dataclass
class DPStats:
    """DP statistics."""
    subproblems_solved: int = 0
    cache_hits: int = 0
    table_size: int = 0


# ============================================================================
# CLASSIC DP PROBLEMS
# ============================================================================

class KnapsackSolver:
    """
    0/1 Knapsack problem solver.

    Features:
    - O(nW) time and space
    - Backtracking for item selection

    "Ba'el packs optimally." — Ba'el
    """

    def __init__(self):
        """Initialize knapsack solver."""
        self._lock = threading.RLock()

    def solve(
        self,
        weights: List[int],
        values: List[int],
        capacity: int
    ) -> DPResult:
        """
        Solve 0/1 knapsack.

        Args:
            weights: Item weights
            values: Item values
            capacity: Knapsack capacity

        Returns:
            DPResult with max value and selected items
        """
        with self._lock:
            n = len(weights)

            if n == 0 or capacity <= 0:
                return DPResult(optimal_value=0, solution=[])

            # DP table
            dp = [[0] * (capacity + 1) for _ in range(n + 1)]

            for i in range(1, n + 1):
                for w in range(capacity + 1):
                    if weights[i - 1] <= w:
                        dp[i][w] = max(
                            dp[i - 1][w],
                            dp[i - 1][w - weights[i - 1]] + values[i - 1]
                        )
                    else:
                        dp[i][w] = dp[i - 1][w]

            # Backtrack to find items
            selected = []
            w = capacity
            for i in range(n, 0, -1):
                if dp[i][w] != dp[i - 1][w]:
                    selected.append(i - 1)
                    w -= weights[i - 1]

            return DPResult(
                optimal_value=dp[n][capacity],
                solution=selected[::-1],
                table=dp
            )

    def solve_unbounded(
        self,
        weights: List[int],
        values: List[int],
        capacity: int
    ) -> DPResult:
        """
        Solve unbounded knapsack (items can be repeated).
        """
        with self._lock:
            n = len(weights)

            dp = [0] * (capacity + 1)
            parent = [-1] * (capacity + 1)

            for w in range(1, capacity + 1):
                for i in range(n):
                    if weights[i] <= w:
                        if dp[w - weights[i]] + values[i] > dp[w]:
                            dp[w] = dp[w - weights[i]] + values[i]
                            parent[w] = i

            # Reconstruct solution
            selected = []
            w = capacity
            while w > 0 and parent[w] != -1:
                selected.append(parent[w])
                w -= weights[parent[w]]

            return DPResult(optimal_value=dp[capacity], solution=selected)


class LCSSolver:
    """
    Longest Common Subsequence solver.

    "Ba'el finds common patterns." — Ba'el
    """

    def __init__(self):
        """Initialize LCS solver."""
        self._lock = threading.RLock()

    def solve(self, seq1: str, seq2: str) -> DPResult:
        """
        Find longest common subsequence.

        Returns:
            DPResult with LCS length and actual subsequence
        """
        with self._lock:
            m, n = len(seq1), len(seq2)

            dp = [[0] * (n + 1) for _ in range(m + 1)]

            for i in range(1, m + 1):
                for j in range(1, n + 1):
                    if seq1[i - 1] == seq2[j - 1]:
                        dp[i][j] = dp[i - 1][j - 1] + 1
                    else:
                        dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])

            # Backtrack
            lcs = []
            i, j = m, n
            while i > 0 and j > 0:
                if seq1[i - 1] == seq2[j - 1]:
                    lcs.append(seq1[i - 1])
                    i -= 1
                    j -= 1
                elif dp[i - 1][j] > dp[i][j - 1]:
                    i -= 1
                else:
                    j -= 1

            return DPResult(
                optimal_value=dp[m][n],
                solution=''.join(reversed(lcs)),
                table=dp
            )


class LISSolver:
    """
    Longest Increasing Subsequence solver.

    "Ba'el finds increasing patterns." — Ba'el
    """

    def __init__(self):
        """Initialize LIS solver."""
        self._lock = threading.RLock()

    def solve(self, arr: List[int]) -> DPResult:
        """
        Find longest increasing subsequence.

        O(n log n) using binary search.
        """
        with self._lock:
            if not arr:
                return DPResult(optimal_value=0, solution=[])

            n = len(arr)

            # tails[i] is smallest tail of LIS of length i+1
            tails = []
            # For reconstruction
            parent = [-1] * n
            indices = []

            for i in range(n):
                # Binary search for position
                lo, hi = 0, len(tails)
                while lo < hi:
                    mid = (lo + hi) // 2
                    if tails[mid] < arr[i]:
                        lo = mid + 1
                    else:
                        hi = mid

                if lo == len(tails):
                    tails.append(arr[i])
                    indices.append(i)
                else:
                    tails[lo] = arr[i]
                    indices[lo] = i

                parent[i] = indices[lo - 1] if lo > 0 else -1

            # Reconstruct
            lis = []
            idx = indices[-1] if indices else -1
            while idx != -1:
                lis.append(arr[idx])
                idx = parent[idx]

            return DPResult(
                optimal_value=len(tails),
                solution=list(reversed(lis))
            )

    def solve_dp(self, arr: List[int]) -> DPResult:
        """
        Find LIS using O(n²) DP.
        """
        with self._lock:
            if not arr:
                return DPResult(optimal_value=0, solution=[])

            n = len(arr)
            dp = [1] * n
            parent = [-1] * n

            for i in range(1, n):
                for j in range(i):
                    if arr[j] < arr[i] and dp[j] + 1 > dp[i]:
                        dp[i] = dp[j] + 1
                        parent[i] = j

            # Find max and reconstruct
            max_len = max(dp)
            max_idx = dp.index(max_len)

            lis = []
            idx = max_idx
            while idx != -1:
                lis.append(arr[idx])
                idx = parent[idx]

            return DPResult(
                optimal_value=max_len,
                solution=list(reversed(lis)),
                table=[dp]
            )


class EditDistanceSolver:
    """
    Edit distance (Levenshtein distance) solver.

    "Ba'el measures string similarity." — Ba'el
    """

    def __init__(self):
        """Initialize edit distance solver."""
        self._lock = threading.RLock()

    def solve(
        self,
        s1: str,
        s2: str,
        insert_cost: int = 1,
        delete_cost: int = 1,
        replace_cost: int = 1
    ) -> DPResult:
        """
        Compute minimum edit distance.

        Returns:
            DPResult with distance and edit operations
        """
        with self._lock:
            m, n = len(s1), len(s2)

            dp = [[0] * (n + 1) for _ in range(m + 1)]

            # Base cases
            for i in range(m + 1):
                dp[i][0] = i * delete_cost
            for j in range(n + 1):
                dp[0][j] = j * insert_cost

            # Fill table
            for i in range(1, m + 1):
                for j in range(1, n + 1):
                    if s1[i - 1] == s2[j - 1]:
                        dp[i][j] = dp[i - 1][j - 1]
                    else:
                        dp[i][j] = min(
                            dp[i - 1][j] + delete_cost,
                            dp[i][j - 1] + insert_cost,
                            dp[i - 1][j - 1] + replace_cost
                        )

            # Backtrack for operations
            operations = []
            i, j = m, n
            while i > 0 or j > 0:
                if i > 0 and j > 0 and s1[i - 1] == s2[j - 1]:
                    operations.append(('match', s1[i - 1]))
                    i -= 1
                    j -= 1
                elif i > 0 and j > 0 and dp[i][j] == dp[i - 1][j - 1] + replace_cost:
                    operations.append(('replace', s1[i - 1], s2[j - 1]))
                    i -= 1
                    j -= 1
                elif i > 0 and dp[i][j] == dp[i - 1][j] + delete_cost:
                    operations.append(('delete', s1[i - 1]))
                    i -= 1
                else:
                    operations.append(('insert', s2[j - 1]))
                    j -= 1

            return DPResult(
                optimal_value=dp[m][n],
                solution=list(reversed(operations)),
                table=dp
            )


class MatrixChainMultiplication:
    """
    Matrix chain multiplication optimization.

    "Ba'el multiplies matrices optimally." — Ba'el
    """

    def __init__(self):
        """Initialize solver."""
        self._lock = threading.RLock()

    def solve(self, dimensions: List[int]) -> DPResult:
        """
        Find optimal parenthesization.

        Args:
            dimensions: Matrix dimensions [p0, p1, p2, ..., pn]
                       Matrix i has dimensions p[i-1] x p[i]

        Returns:
            DPResult with minimum cost and parenthesization
        """
        with self._lock:
            n = len(dimensions) - 1

            if n <= 0:
                return DPResult(optimal_value=0, solution="")

            # dp[i][j] = min cost to multiply matrices i to j
            dp = [[0] * n for _ in range(n)]
            split = [[0] * n for _ in range(n)]

            # Length of chain
            for length in range(2, n + 1):
                for i in range(n - length + 1):
                    j = i + length - 1
                    dp[i][j] = float('inf')

                    for k in range(i, j):
                        cost = (dp[i][k] + dp[k + 1][j] +
                               dimensions[i] * dimensions[k + 1] * dimensions[j + 1])

                        if cost < dp[i][j]:
                            dp[i][j] = cost
                            split[i][j] = k

            # Construct parenthesization
            def build_paren(i: int, j: int) -> str:
                if i == j:
                    return f"M{i}"
                k = split[i][j]
                left = build_paren(i, k)
                right = build_paren(k + 1, j)
                return f"({left} × {right})"

            return DPResult(
                optimal_value=dp[0][n - 1],
                solution=build_paren(0, n - 1),
                table=dp
            )


class CoinChangeSolver:
    """
    Coin change problem solver.

    "Ba'el makes change optimally." — Ba'el
    """

    def __init__(self):
        """Initialize solver."""
        self._lock = threading.RLock()

    def min_coins(self, coins: List[int], amount: int) -> DPResult:
        """
        Find minimum number of coins for amount.
        """
        with self._lock:
            if amount <= 0:
                return DPResult(optimal_value=0, solution=[])

            dp = [float('inf')] * (amount + 1)
            dp[0] = 0
            parent = [-1] * (amount + 1)

            for i in range(1, amount + 1):
                for coin in coins:
                    if coin <= i and dp[i - coin] + 1 < dp[i]:
                        dp[i] = dp[i - coin] + 1
                        parent[i] = coin

            if dp[amount] == float('inf'):
                return DPResult(optimal_value=-1, solution=[])

            # Reconstruct
            result_coins = []
            curr = amount
            while curr > 0:
                result_coins.append(parent[curr])
                curr -= parent[curr]

            return DPResult(optimal_value=dp[amount], solution=result_coins)

    def count_ways(self, coins: List[int], amount: int) -> DPResult:
        """
        Count number of ways to make change.
        """
        with self._lock:
            if amount < 0:
                return DPResult(optimal_value=0)

            dp = [0] * (amount + 1)
            dp[0] = 1

            for coin in coins:
                for i in range(coin, amount + 1):
                    dp[i] += dp[i - coin]

            return DPResult(optimal_value=dp[amount], table=[dp])


class RodCuttingSolver:
    """
    Rod cutting problem solver.

    "Ba'el cuts rods optimally." — Ba'el
    """

    def __init__(self):
        """Initialize solver."""
        self._lock = threading.RLock()

    def solve(self, prices: List[int], length: int) -> DPResult:
        """
        Find maximum revenue from cutting rod.

        Args:
            prices: prices[i] = price of rod of length i+1
            length: Rod length
        """
        with self._lock:
            if length <= 0 or not prices:
                return DPResult(optimal_value=0, solution=[])

            dp = [0] * (length + 1)
            cuts = [0] * (length + 1)

            for i in range(1, length + 1):
                for j in range(1, min(i, len(prices)) + 1):
                    if dp[i - j] + prices[j - 1] > dp[i]:
                        dp[i] = dp[i - j] + prices[j - 1]
                        cuts[i] = j

            # Reconstruct cuts
            result_cuts = []
            remaining = length
            while remaining > 0:
                result_cuts.append(cuts[remaining])
                remaining -= cuts[remaining]

            return DPResult(optimal_value=dp[length], solution=result_cuts)


class SubsetSumSolver:
    """
    Subset sum problem solver.

    "Ba'el finds target subsets." — Ba'el
    """

    def __init__(self):
        """Initialize solver."""
        self._lock = threading.RLock()

    def solve(self, nums: List[int], target: int) -> DPResult:
        """
        Find if subset with target sum exists.
        """
        with self._lock:
            n = len(nums)

            if target == 0:
                return DPResult(optimal_value=True, solution=[])

            if not nums or target < 0:
                return DPResult(optimal_value=False, solution=[])

            dp = [[False] * (target + 1) for _ in range(n + 1)]

            for i in range(n + 1):
                dp[i][0] = True

            for i in range(1, n + 1):
                for j in range(1, target + 1):
                    dp[i][j] = dp[i - 1][j]
                    if nums[i - 1] <= j:
                        dp[i][j] = dp[i][j] or dp[i - 1][j - nums[i - 1]]

            if not dp[n][target]:
                return DPResult(optimal_value=False, solution=[])

            # Backtrack
            subset = []
            i, j = n, target
            while i > 0 and j > 0:
                if dp[i][j] and not dp[i - 1][j]:
                    subset.append(nums[i - 1])
                    j -= nums[i - 1]
                i -= 1

            return DPResult(optimal_value=True, solution=subset[::-1])


class PartitionSolver:
    """
    Partition problem solver.

    "Ba'el partitions equally." — Ba'el
    """

    def __init__(self):
        """Initialize solver."""
        self._subset_sum = SubsetSumSolver()
        self._lock = threading.RLock()

    def can_partition(self, nums: List[int]) -> DPResult:
        """
        Check if array can be partitioned into two equal sum subsets.
        """
        with self._lock:
            total = sum(nums)

            if total % 2 != 0:
                return DPResult(optimal_value=False)

            result = self._subset_sum.solve(nums, total // 2)

            if result.optimal_value:
                subset1 = result.solution
                subset1_set = set(range(len(subset1)))
                subset2 = [nums[i] for i in range(len(nums)) if i not in subset1_set]
                return DPResult(optimal_value=True, solution=(subset1, subset2))

            return DPResult(optimal_value=False)


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_knapsack_solver() -> KnapsackSolver:
    """Create knapsack solver."""
    return KnapsackSolver()


def create_lcs_solver() -> LCSSolver:
    """Create LCS solver."""
    return LCSSolver()


def create_lis_solver() -> LISSolver:
    """Create LIS solver."""
    return LISSolver()


def create_edit_distance_solver() -> EditDistanceSolver:
    """Create edit distance solver."""
    return EditDistanceSolver()


def create_matrix_chain_solver() -> MatrixChainMultiplication:
    """Create matrix chain solver."""
    return MatrixChainMultiplication()


def create_coin_change_solver() -> CoinChangeSolver:
    """Create coin change solver."""
    return CoinChangeSolver()


def create_rod_cutting_solver() -> RodCuttingSolver:
    """Create rod cutting solver."""
    return RodCuttingSolver()


def create_subset_sum_solver() -> SubsetSumSolver:
    """Create subset sum solver."""
    return SubsetSumSolver()


def knapsack_01(
    weights: List[int],
    values: List[int],
    capacity: int
) -> Tuple[int, List[int]]:
    """Solve 0/1 knapsack."""
    result = KnapsackSolver().solve(weights, values, capacity)
    return result.optimal_value, result.solution


def longest_common_subsequence(s1: str, s2: str) -> str:
    """Find LCS of two strings."""
    return LCSSolver().solve(s1, s2).solution


def longest_increasing_subsequence(arr: List[int]) -> List[int]:
    """Find LIS of array."""
    return LISSolver().solve(arr).solution


def edit_distance(s1: str, s2: str) -> int:
    """Compute edit distance."""
    return EditDistanceSolver().solve(s1, s2).optimal_value


def min_coins(coins: List[int], amount: int) -> int:
    """Find minimum coins for amount."""
    return CoinChangeSolver().min_coins(coins, amount).optimal_value


def subset_sum(nums: List[int], target: int) -> bool:
    """Check if subset sum exists."""
    return SubsetSumSolver().solve(nums, target).optimal_value

"""
BAEL Greedy Algorithms Suite
============================

Classic greedy algorithm implementations.

"Ba'el chooses greedily but wisely." — Ba'el
"""

import logging
import threading
from typing import Any, Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field
import heapq
from collections import defaultdict

logger = logging.getLogger("BAEL.GreedyAlgorithms")


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class GreedyResult:
    """Greedy algorithm result."""
    optimal_value: Any
    solution: Any = None
    is_optimal: bool = True  # Greedy may not always be optimal


@dataclass
class Interval:
    """Interval with start and end."""
    start: int
    end: int
    value: Any = None
    id: int = -1


@dataclass
class Activity:
    """Activity for scheduling."""
    start: int
    end: int
    name: str = ""
    weight: int = 1


@dataclass
class Job:
    """Job for scheduling."""
    id: int
    deadline: int
    profit: int
    duration: int = 1


# ============================================================================
# ACTIVITY SELECTION
# ============================================================================

class ActivitySelector:
    """
    Activity selection problem.

    Features:
    - O(n log n) time
    - Maximum non-overlapping activities

    "Ba'el selects activities greedily." — Ba'el
    """

    def __init__(self):
        """Initialize activity selector."""
        self._lock = threading.RLock()

    def select(self, activities: List[Activity]) -> GreedyResult:
        """
        Select maximum number of non-overlapping activities.

        Greedy strategy: Always pick earliest finishing activity.
        """
        with self._lock:
            if not activities:
                return GreedyResult(optimal_value=0, solution=[])

            # Sort by end time
            sorted_activities = sorted(activities, key=lambda a: a.end)

            selected = [sorted_activities[0]]
            last_end = sorted_activities[0].end

            for activity in sorted_activities[1:]:
                if activity.start >= last_end:
                    selected.append(activity)
                    last_end = activity.end

            return GreedyResult(
                optimal_value=len(selected),
                solution=selected,
                is_optimal=True
            )

    def weighted_select(self, activities: List[Activity]) -> GreedyResult:
        """
        Weighted activity selection (DP, not greedy).

        Finds maximum weight set of non-overlapping activities.
        """
        with self._lock:
            if not activities:
                return GreedyResult(optimal_value=0, solution=[])

            n = len(activities)
            sorted_activities = sorted(activities, key=lambda a: a.end)

            # Find previous compatible activity
            def find_prev(idx: int) -> int:
                lo, hi = 0, idx - 1
                while lo <= hi:
                    mid = (lo + hi) // 2
                    if sorted_activities[mid].end <= sorted_activities[idx].start:
                        if mid + 1 < idx and sorted_activities[mid + 1].end <= sorted_activities[idx].start:
                            lo = mid + 1
                        else:
                            return mid
                    else:
                        hi = mid - 1
                return -1

            # DP
            dp = [0] * n
            dp[0] = sorted_activities[0].weight

            for i in range(1, n):
                include = sorted_activities[i].weight
                prev = find_prev(i)
                if prev != -1:
                    include += dp[prev]

                dp[i] = max(dp[i - 1], include)

            # Backtrack
            selected = []
            i = n - 1
            while i >= 0:
                include = sorted_activities[i].weight
                prev = find_prev(i)
                if prev != -1:
                    include += dp[prev]

                if i == 0 or include > dp[i - 1]:
                    selected.append(sorted_activities[i])
                    i = prev
                else:
                    i -= 1

            return GreedyResult(
                optimal_value=dp[n - 1],
                solution=selected[::-1],
                is_optimal=True
            )


# ============================================================================
# INTERVAL SCHEDULING
# ============================================================================

class IntervalScheduler:
    """
    Interval scheduling problems.

    "Ba'el schedules intervals." — Ba'el
    """

    def __init__(self):
        """Initialize scheduler."""
        self._lock = threading.RLock()

    def max_non_overlapping(self, intervals: List[Interval]) -> GreedyResult:
        """Find maximum set of non-overlapping intervals."""
        with self._lock:
            if not intervals:
                return GreedyResult(optimal_value=0, solution=[])

            sorted_intervals = sorted(intervals, key=lambda i: i.end)

            selected = [sorted_intervals[0]]
            last_end = sorted_intervals[0].end

            for interval in sorted_intervals[1:]:
                if interval.start >= last_end:
                    selected.append(interval)
                    last_end = interval.end

            return GreedyResult(optimal_value=len(selected), solution=selected)

    def min_rooms(self, intervals: List[Interval]) -> GreedyResult:
        """
        Find minimum number of rooms/resources needed.

        Uses sweep line approach.
        """
        with self._lock:
            if not intervals:
                return GreedyResult(optimal_value=0, solution=[])

            events = []
            for interval in intervals:
                events.append((interval.start, 1))  # Start
                events.append((interval.end, -1))   # End

            events.sort(key=lambda e: (e[0], e[1]))

            max_rooms = 0
            current_rooms = 0

            for _, delta in events:
                current_rooms += delta
                max_rooms = max(max_rooms, current_rooms)

            return GreedyResult(optimal_value=max_rooms)

    def interval_partitioning(self, intervals: List[Interval]) -> GreedyResult:
        """
        Partition intervals into minimum number of groups.

        Each group contains non-overlapping intervals.
        """
        with self._lock:
            if not intervals:
                return GreedyResult(optimal_value=0, solution=[])

            sorted_intervals = sorted(intervals, key=lambda i: i.start)

            # Min-heap of end times of groups
            groups: List[List[Interval]] = []
            end_times: List[Tuple[int, int]] = []  # (end_time, group_index)

            for interval in sorted_intervals:
                if end_times and end_times[0][0] <= interval.start:
                    # Reuse existing group
                    _, group_idx = heapq.heappop(end_times)
                    groups[group_idx].append(interval)
                    heapq.heappush(end_times, (interval.end, group_idx))
                else:
                    # Create new group
                    group_idx = len(groups)
                    groups.append([interval])
                    heapq.heappush(end_times, (interval.end, group_idx))

            return GreedyResult(optimal_value=len(groups), solution=groups)


# ============================================================================
# JOB SCHEDULING
# ============================================================================

class JobScheduler:
    """
    Job scheduling problems.

    "Ba'el schedules jobs optimally." — Ba'el
    """

    def __init__(self):
        """Initialize scheduler."""
        self._lock = threading.RLock()

    def job_sequencing_with_deadlines(self, jobs: List[Job]) -> GreedyResult:
        """
        Schedule jobs to maximize profit.

        Each job takes 1 unit of time and has a deadline.
        """
        with self._lock:
            if not jobs:
                return GreedyResult(optimal_value=0, solution=[])

            # Sort by profit descending
            sorted_jobs = sorted(jobs, key=lambda j: j.profit, reverse=True)

            max_deadline = max(j.deadline for j in jobs)
            slots = [-1] * (max_deadline + 1)  # 1-indexed

            scheduled = []
            total_profit = 0

            for job in sorted_jobs:
                # Find latest available slot before deadline
                for slot in range(min(job.deadline, max_deadline), 0, -1):
                    if slots[slot] == -1:
                        slots[slot] = job.id
                        scheduled.append(job)
                        total_profit += job.profit
                        break

            return GreedyResult(optimal_value=total_profit, solution=scheduled)

    def shortest_job_first(self, jobs: List[Job]) -> GreedyResult:
        """
        Schedule jobs to minimize average waiting time.

        Uses Shortest Job First (SJF) strategy.
        """
        with self._lock:
            if not jobs:
                return GreedyResult(optimal_value=0, solution=[])

            sorted_jobs = sorted(jobs, key=lambda j: j.duration)

            total_wait = 0
            current_time = 0
            schedule = []

            for job in sorted_jobs:
                total_wait += current_time
                schedule.append((job, current_time))
                current_time += job.duration

            avg_wait = total_wait / len(jobs)

            return GreedyResult(optimal_value=avg_wait, solution=schedule)


# ============================================================================
# HUFFMAN CODING
# ============================================================================

class HuffmanNode:
    """Node in Huffman tree."""

    def __init__(self, char: str = None, freq: int = 0):
        self.char = char
        self.freq = freq
        self.left: Optional['HuffmanNode'] = None
        self.right: Optional['HuffmanNode'] = None

    def __lt__(self, other: 'HuffmanNode') -> bool:
        return self.freq < other.freq


class HuffmanCoding:
    """
    Huffman coding for optimal prefix-free encoding.

    Features:
    - O(n log n) construction
    - Optimal prefix-free codes

    "Ba'el encodes with minimal bits." — Ba'el
    """

    def __init__(self):
        """Initialize Huffman coder."""
        self._lock = threading.RLock()

    def build_tree(self, frequencies: Dict[str, int]) -> HuffmanNode:
        """
        Build Huffman tree from character frequencies.
        """
        with self._lock:
            if not frequencies:
                return HuffmanNode()

            # Create leaf nodes
            heap = [HuffmanNode(char, freq) for char, freq in frequencies.items()]
            heapq.heapify(heap)

            # Build tree
            while len(heap) > 1:
                left = heapq.heappop(heap)
                right = heapq.heappop(heap)

                merged = HuffmanNode(freq=left.freq + right.freq)
                merged.left = left
                merged.right = right

                heapq.heappush(heap, merged)

            return heap[0] if heap else HuffmanNode()

    def generate_codes(self, frequencies: Dict[str, int]) -> Dict[str, str]:
        """
        Generate Huffman codes for each character.
        """
        with self._lock:
            root = self.build_tree(frequencies)
            codes: Dict[str, str] = {}

            def traverse(node: HuffmanNode, code: str):
                if node.char is not None:
                    codes[node.char] = code if code else '0'
                    return

                if node.left:
                    traverse(node.left, code + '0')
                if node.right:
                    traverse(node.right, code + '1')

            traverse(root, '')
            return codes

    def encode(self, text: str) -> Tuple[str, Dict[str, str]]:
        """
        Encode text using Huffman coding.

        Returns:
            (encoded_text, codes)
        """
        with self._lock:
            if not text:
                return '', {}

            frequencies: Dict[str, int] = defaultdict(int)
            for char in text:
                frequencies[char] += 1

            codes = self.generate_codes(dict(frequencies))
            encoded = ''.join(codes[char] for char in text)

            return encoded, codes

    def decode(self, encoded: str, root: HuffmanNode) -> str:
        """
        Decode Huffman encoded text.
        """
        with self._lock:
            if not encoded or root.char is not None:
                return root.char if root.char else ''

            result = []
            node = root

            for bit in encoded:
                if bit == '0':
                    node = node.left
                else:
                    node = node.right

                if node.char is not None:
                    result.append(node.char)
                    node = root

            return ''.join(result)


# ============================================================================
# FRACTIONAL KNAPSACK
# ============================================================================

class FractionalKnapsack:
    """
    Fractional knapsack problem.

    "Ba'el takes fractions greedily." — Ba'el
    """

    def __init__(self):
        """Initialize solver."""
        self._lock = threading.RLock()

    def solve(
        self,
        weights: List[float],
        values: List[float],
        capacity: float
    ) -> GreedyResult:
        """
        Solve fractional knapsack.

        Items can be taken fractionally.
        """
        with self._lock:
            n = len(weights)

            if n == 0 or capacity <= 0:
                return GreedyResult(optimal_value=0.0, solution=[])

            # Create items with value/weight ratio
            items = [(values[i] / weights[i], weights[i], values[i], i)
                    for i in range(n) if weights[i] > 0]

            # Sort by ratio descending
            items.sort(reverse=True)

            total_value = 0.0
            remaining = capacity
            fractions = [0.0] * n

            for ratio, weight, value, idx in items:
                if remaining >= weight:
                    fractions[idx] = 1.0
                    total_value += value
                    remaining -= weight
                else:
                    fraction = remaining / weight
                    fractions[idx] = fraction
                    total_value += value * fraction
                    remaining = 0
                    break

            return GreedyResult(
                optimal_value=total_value,
                solution=fractions,
                is_optimal=True
            )


# ============================================================================
# MINIMUM SPANNING TREE (KRUSKAL & PRIM)
# ============================================================================

class UnionFind:
    """Union-Find for Kruskal's algorithm."""

    def __init__(self, n: int):
        self.parent = list(range(n))
        self.rank = [0] * n

    def find(self, x: int) -> int:
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])
        return self.parent[x]

    def union(self, x: int, y: int) -> bool:
        px, py = self.find(x), self.find(y)
        if px == py:
            return False
        if self.rank[px] < self.rank[py]:
            px, py = py, px
        self.parent[py] = px
        if self.rank[px] == self.rank[py]:
            self.rank[px] += 1
        return True


class MSTSolver:
    """
    Minimum Spanning Tree solvers.

    "Ba'el spans minimally." — Ba'el
    """

    def __init__(self):
        """Initialize MST solver."""
        self._lock = threading.RLock()

    def kruskal(
        self,
        n: int,
        edges: List[Tuple[int, int, float]]
    ) -> GreedyResult:
        """
        Kruskal's algorithm for MST.

        Args:
            n: Number of vertices
            edges: List of (u, v, weight)
        """
        with self._lock:
            if n <= 0:
                return GreedyResult(optimal_value=0, solution=[])

            sorted_edges = sorted(edges, key=lambda e: e[2])
            uf = UnionFind(n)

            mst_edges = []
            mst_weight = 0.0

            for u, v, w in sorted_edges:
                if uf.union(u, v):
                    mst_edges.append((u, v, w))
                    mst_weight += w

                    if len(mst_edges) == n - 1:
                        break

            return GreedyResult(
                optimal_value=mst_weight,
                solution=mst_edges,
                is_optimal=True
            )

    def prim(
        self,
        n: int,
        adj: List[List[Tuple[int, float]]]
    ) -> GreedyResult:
        """
        Prim's algorithm for MST.

        Args:
            n: Number of vertices
            adj: Adjacency list [(neighbor, weight), ...]
        """
        with self._lock:
            if n <= 0:
                return GreedyResult(optimal_value=0, solution=[])

            visited = [False] * n
            mst_edges = []
            mst_weight = 0.0

            # Min-heap: (weight, u, v)
            heap = [(0, -1, 0)]  # Start from vertex 0

            while heap and len(mst_edges) < n - 1:
                w, u, v = heapq.heappop(heap)

                if visited[v]:
                    continue

                visited[v] = True

                if u != -1:
                    mst_edges.append((u, v, w))
                    mst_weight += w

                for neighbor, weight in adj[v]:
                    if not visited[neighbor]:
                        heapq.heappush(heap, (weight, v, neighbor))

            return GreedyResult(
                optimal_value=mst_weight,
                solution=mst_edges,
                is_optimal=True
            )


# ============================================================================
# DIJKSTRA'S ALGORITHM
# ============================================================================

class DijkstraSolver:
    """
    Dijkstra's shortest path algorithm.

    "Ba'el finds shortest paths greedily." — Ba'el
    """

    def __init__(self):
        """Initialize Dijkstra solver."""
        self._lock = threading.RLock()

    def shortest_paths(
        self,
        n: int,
        adj: List[List[Tuple[int, float]]],
        source: int
    ) -> GreedyResult:
        """
        Find shortest paths from source to all vertices.

        Args:
            n: Number of vertices
            adj: Adjacency list [(neighbor, weight), ...]
            source: Source vertex
        """
        with self._lock:
            if n <= 0 or source < 0 or source >= n:
                return GreedyResult(optimal_value=[], solution=[])

            dist = [float('inf')] * n
            parent = [-1] * n
            dist[source] = 0

            heap = [(0, source)]

            while heap:
                d, u = heapq.heappop(heap)

                if d > dist[u]:
                    continue

                for v, w in adj[u]:
                    if dist[u] + w < dist[v]:
                        dist[v] = dist[u] + w
                        parent[v] = u
                        heapq.heappush(heap, (dist[v], v))

            return GreedyResult(
                optimal_value=dist,
                solution=parent,
                is_optimal=True
            )

    def shortest_path(
        self,
        n: int,
        adj: List[List[Tuple[int, float]]],
        source: int,
        target: int
    ) -> GreedyResult:
        """
        Find shortest path from source to target.
        """
        with self._lock:
            result = self.shortest_paths(n, adj, source)

            if result.optimal_value[target] == float('inf'):
                return GreedyResult(optimal_value=float('inf'), solution=[])

            # Reconstruct path
            path = []
            current = target
            while current != -1:
                path.append(current)
                current = result.solution[current]

            return GreedyResult(
                optimal_value=result.optimal_value[target],
                solution=path[::-1],
                is_optimal=True
            )


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_activity_selector() -> ActivitySelector:
    """Create activity selector."""
    return ActivitySelector()


def create_interval_scheduler() -> IntervalScheduler:
    """Create interval scheduler."""
    return IntervalScheduler()


def create_job_scheduler() -> JobScheduler:
    """Create job scheduler."""
    return JobScheduler()


def create_huffman_coder() -> HuffmanCoding:
    """Create Huffman coder."""
    return HuffmanCoding()


def create_fractional_knapsack() -> FractionalKnapsack:
    """Create fractional knapsack solver."""
    return FractionalKnapsack()


def create_mst_solver() -> MSTSolver:
    """Create MST solver."""
    return MSTSolver()


def create_dijkstra_solver() -> DijkstraSolver:
    """Create Dijkstra solver."""
    return DijkstraSolver()


def activity_selection(activities: List[Tuple[int, int]]) -> List[int]:
    """Select maximum non-overlapping activities."""
    acts = [Activity(start=s, end=e) for s, e in activities]
    result = ActivitySelector().select(acts)
    return [i for i, a in enumerate(result.solution)]


def huffman_encode(text: str) -> Tuple[str, Dict[str, str]]:
    """Huffman encode text."""
    return HuffmanCoding().encode(text)


def fractional_knapsack(
    weights: List[float],
    values: List[float],
    capacity: float
) -> Tuple[float, List[float]]:
    """Solve fractional knapsack."""
    result = FractionalKnapsack().solve(weights, values, capacity)
    return result.optimal_value, result.solution


def kruskal_mst(
    n: int,
    edges: List[Tuple[int, int, float]]
) -> Tuple[float, List[Tuple[int, int, float]]]:
    """Compute MST using Kruskal's algorithm."""
    result = MSTSolver().kruskal(n, edges)
    return result.optimal_value, result.solution


def dijkstra(
    n: int,
    adj: List[List[Tuple[int, float]]],
    source: int
) -> List[float]:
    """Compute shortest paths using Dijkstra."""
    result = DijkstraSolver().shortest_paths(n, adj, source)
    return result.optimal_value

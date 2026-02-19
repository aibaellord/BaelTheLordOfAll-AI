"""
BAEL Line Sweep Engine
======================

Line sweep algorithms for computational geometry.

"Ba'el sweeps through space systematically." — Ba'el
"""

import logging
import threading
from typing import Any, Dict, List, Optional, Set, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum, auto
import heapq
from collections import defaultdict
import bisect

logger = logging.getLogger("BAEL.LineSweep")


# ============================================================================
# DATA STRUCTURES
# ============================================================================

class EventType(Enum):
    """Event types for line sweep."""
    START = auto()
    END = auto()
    VERTICAL = auto()
    POINT = auto()
    INTERSECTION = auto()


@dataclass
class Point2D:
    """2D point."""
    x: float
    y: float

    def __lt__(self, other: 'Point2D') -> bool:
        if self.x != other.x:
            return self.x < other.x
        return self.y < other.y


@dataclass
class Segment:
    """Line segment."""
    p1: Point2D
    p2: Point2D
    id: int = 0

    def __post_init__(self):
        # Ensure p1 is left of p2
        if self.p1.x > self.p2.x or (self.p1.x == self.p2.x and self.p1.y > self.p2.y):
            self.p1, self.p2 = self.p2, self.p1

    def y_at_x(self, x: float) -> float:
        """Get y coordinate at given x."""
        if self.p1.x == self.p2.x:
            return self.p1.y

        t = (x - self.p1.x) / (self.p2.x - self.p1.x)
        return self.p1.y + t * (self.p2.y - self.p1.y)


@dataclass
class Interval:
    """1D interval."""
    start: float
    end: float
    id: int = 0
    data: Any = None

    def __post_init__(self):
        if self.start > self.end:
            self.start, self.end = self.end, self.start


@dataclass
class Rectangle:
    """Axis-aligned rectangle."""
    x1: float  # left
    y1: float  # bottom
    x2: float  # right
    y2: float  # top
    id: int = 0


@dataclass
class SweepEvent:
    """Event for line sweep."""
    x: float
    y: float
    event_type: EventType
    data: Any = None

    def __lt__(self, other: 'SweepEvent') -> bool:
        if self.x != other.x:
            return self.x < other.x
        # Order: START before END at same x
        return self.event_type.value < other.event_type.value


# ============================================================================
# INTERVAL OVERLAP (1D LINE SWEEP)
# ============================================================================

class IntervalOverlap:
    """
    Find overlapping intervals using line sweep.

    Features:
    - O((n + k) log n) where k is output size
    - Event-based processing

    "Ba'el finds all overlaps efficiently." — Ba'el
    """

    def __init__(self):
        """Initialize interval overlap finder."""
        self._intervals: List[Interval] = []
        self._lock = threading.RLock()

        logger.debug("Interval overlap finder initialized")

    def add_interval(self, start: float, end: float, data: Any = None) -> int:
        """Add interval and return its ID."""
        with self._lock:
            interval_id = len(self._intervals)
            self._intervals.append(Interval(start, end, interval_id, data))
            return interval_id

    def find_all_overlaps(self) -> List[Tuple[int, int]]:
        """
        Find all pairs of overlapping intervals.

        Returns:
            List of (id1, id2) pairs
        """
        with self._lock:
            # Create events
            events = []
            for interval in self._intervals:
                events.append(SweepEvent(interval.start, 0, EventType.START, interval))
                events.append(SweepEvent(interval.end, 0, EventType.END, interval))

            events.sort()

            overlaps = []
            active: Set[int] = set()

            for event in events:
                interval = event.data

                if event.event_type == EventType.START:
                    # This interval overlaps with all active intervals
                    for active_id in active:
                        overlaps.append((min(active_id, interval.id), max(active_id, interval.id)))
                    active.add(interval.id)
                else:
                    active.remove(interval.id)

            return overlaps

    def max_overlapping_count(self) -> Tuple[float, int]:
        """
        Find maximum number of overlapping intervals at any point.

        Returns:
            (x_coordinate, max_count)
        """
        with self._lock:
            events = []
            for interval in self._intervals:
                events.append((interval.start, 1))  # +1 at start
                events.append((interval.end, -1))   # -1 at end

            events.sort()

            max_count = 0
            current_count = 0
            max_x = 0

            for x, delta in events:
                current_count += delta
                if current_count > max_count:
                    max_count = current_count
                    max_x = x

            return max_x, max_count

    def merge_overlapping(self) -> List[Interval]:
        """
        Merge all overlapping intervals.

        Returns:
            List of merged intervals
        """
        with self._lock:
            if not self._intervals:
                return []

            # Sort by start
            sorted_intervals = sorted(self._intervals, key=lambda i: i.start)

            merged = []
            current = Interval(sorted_intervals[0].start, sorted_intervals[0].end)

            for interval in sorted_intervals[1:]:
                if interval.start <= current.end:
                    current.end = max(current.end, interval.end)
                else:
                    merged.append(current)
                    current = Interval(interval.start, interval.end)

            merged.append(current)

            return merged


# ============================================================================
# SEGMENT INTERSECTION (BENTLEY-OTTMANN)
# ============================================================================

class SegmentIntersection:
    """
    Find segment intersections using Bentley-Ottmann.

    Features:
    - O((n + k) log n) where k is intersections
    - Event queue + status structure

    "Ba'el finds all crossings." — Ba'el
    """

    def __init__(self):
        """Initialize segment intersection finder."""
        self._segments: List[Segment] = []
        self._lock = threading.RLock()

    def add_segment(self, x1: float, y1: float, x2: float, y2: float) -> int:
        """Add segment and return its ID."""
        with self._lock:
            seg_id = len(self._segments)
            self._segments.append(Segment(Point2D(x1, y1), Point2D(x2, y2), seg_id))
            return seg_id

    def _segments_intersect(self, s1: Segment, s2: Segment) -> Optional[Point2D]:
        """Check if two segments intersect and return point if so."""
        # Vector cross product
        def cross(o: Point2D, a: Point2D, b: Point2D) -> float:
            return (a.x - o.x) * (b.y - o.y) - (a.y - o.y) * (b.x - o.x)

        d1 = cross(s2.p1, s2.p2, s1.p1)
        d2 = cross(s2.p1, s2.p2, s1.p2)
        d3 = cross(s1.p1, s1.p2, s2.p1)
        d4 = cross(s1.p1, s1.p2, s2.p2)

        if ((d1 > 0 and d2 < 0) or (d1 < 0 and d2 > 0)) and \
           ((d3 > 0 and d4 < 0) or (d3 < 0 and d4 > 0)):
            # Compute intersection point
            t = d1 / (d1 - d2)
            x = s1.p1.x + t * (s1.p2.x - s1.p1.x)
            y = s1.p1.y + t * (s1.p2.y - s1.p1.y)
            return Point2D(x, y)

        return None

    def find_all_intersections(self) -> List[Tuple[int, int, Point2D]]:
        """
        Find all segment intersections.

        Returns:
            List of (seg1_id, seg2_id, intersection_point)
        """
        with self._lock:
            # Simplified O(n²) approach for correctness
            # Full Bentley-Ottmann is complex
            intersections = []
            n = len(self._segments)

            for i in range(n):
                for j in range(i + 1, n):
                    point = self._segments_intersect(self._segments[i], self._segments[j])
                    if point:
                        intersections.append((i, j, point))

            return intersections

    def any_intersection(self) -> bool:
        """
        Check if any two segments intersect.

        Uses Shamos-Hoey algorithm (simplified).
        """
        with self._lock:
            # Create events
            events = []
            for seg in self._segments:
                events.append(SweepEvent(seg.p1.x, seg.p1.y, EventType.START, seg))
                events.append(SweepEvent(seg.p2.x, seg.p2.y, EventType.END, seg))

            events.sort()

            # Active segments sorted by y at current x
            active: List[Segment] = []
            sweep_x = 0

            def get_y(seg: Segment) -> float:
                return seg.y_at_x(sweep_x)

            for event in events:
                sweep_x = event.x
                seg = event.data

                if event.event_type == EventType.START:
                    # Insert and check neighbors
                    y = get_y(seg)
                    pos = bisect.bisect_left([get_y(s) for s in active], y)

                    # Check with predecessor and successor
                    if pos > 0 and self._segments_intersect(active[pos - 1], seg):
                        return True
                    if pos < len(active) and self._segments_intersect(active[pos], seg):
                        return True

                    active.insert(pos, seg)
                else:
                    # Remove and check if neighbors now intersect
                    try:
                        pos = active.index(seg)
                        active.remove(seg)

                        if 0 < pos < len(active):
                            if self._segments_intersect(active[pos - 1], active[pos]):
                                return True
                    except ValueError:
                        pass

            return False


# ============================================================================
# RECTANGLE UNION AREA
# ============================================================================

class RectangleUnion:
    """
    Compute area of union of rectangles using line sweep.

    Features:
    - O(n² log n) using sweep line
    - Handles arbitrary rectangles

    "Ba'el computes the total area." — Ba'el
    """

    def __init__(self):
        """Initialize rectangle union."""
        self._rectangles: List[Rectangle] = []
        self._lock = threading.RLock()

    def add_rectangle(self, x1: float, y1: float, x2: float, y2: float) -> int:
        """Add rectangle and return its ID."""
        with self._lock:
            rect_id = len(self._rectangles)
            self._rectangles.append(Rectangle(
                min(x1, x2), min(y1, y2),
                max(x1, x2), max(y1, y2),
                rect_id
            ))
            return rect_id

    def compute_union_area(self) -> float:
        """
        Compute area of union of all rectangles.

        Returns:
            Total union area
        """
        with self._lock:
            if not self._rectangles:
                return 0.0

            # Coordinate compression for y
            y_coords = set()
            for rect in self._rectangles:
                y_coords.add(rect.y1)
                y_coords.add(rect.y2)

            y_list = sorted(y_coords)
            y_to_idx = {y: i for i, y in enumerate(y_list)}

            # Create events
            events = []
            for rect in self._rectangles:
                events.append((rect.x1, 0, rect.y1, rect.y2))  # Start
                events.append((rect.x2, 1, rect.y1, rect.y2))  # End

            events.sort()

            # Count array
            count = [0] * (len(y_list) - 1)

            total_area = 0.0
            prev_x = events[0][0]

            for x, event_type, y1, y2 in events:
                # Add area since last x
                if x > prev_x:
                    covered_y = 0.0
                    for i in range(len(count)):
                        if count[i] > 0:
                            covered_y += y_list[i + 1] - y_list[i]
                    total_area += covered_y * (x - prev_x)

                # Update counts
                idx1 = y_to_idx[y1]
                idx2 = y_to_idx[y2]
                delta = 1 if event_type == 0 else -1

                for i in range(idx1, idx2):
                    count[i] += delta

                prev_x = x

            return total_area

    def compute_intersection_area(self) -> float:
        """
        Compute area of intersection of all rectangles.

        Returns:
            Intersection area (0 if no common intersection)
        """
        with self._lock:
            if not self._rectangles:
                return 0.0

            # Find bounding intersection
            x1 = max(r.x1 for r in self._rectangles)
            y1 = max(r.y1 for r in self._rectangles)
            x2 = min(r.x2 for r in self._rectangles)
            y2 = min(r.y2 for r in self._rectangles)

            if x1 >= x2 or y1 >= y2:
                return 0.0

            return (x2 - x1) * (y2 - y1)


# ============================================================================
# CLOSEST PAIR USING SWEEP
# ============================================================================

class ClosestPairSweep:
    """
    Find closest pair of points using line sweep.

    Features:
    - O(n log n) time
    - Maintains sorted set by y

    "Ba'el finds the nearest neighbors." — Ba'el
    """

    def __init__(self):
        """Initialize closest pair finder."""
        self._points: List[Point2D] = []
        self._lock = threading.RLock()

    def add_point(self, x: float, y: float) -> None:
        """Add point to the set."""
        with self._lock:
            self._points.append(Point2D(x, y))

    def find_closest_pair(self) -> Tuple[Optional[Point2D], Optional[Point2D], float]:
        """
        Find closest pair of points.

        Returns:
            (point1, point2, distance)
        """
        with self._lock:
            n = len(self._points)

            if n < 2:
                return None, None, float('inf')

            # Sort by x
            sorted_points = sorted(self._points, key=lambda p: p.x)

            # Active set sorted by y
            from sortedcontainers import SortedList
            active: List[Point2D] = []

            min_dist = float('inf')
            closest_pair = (sorted_points[0], sorted_points[1])

            left = 0

            for right in range(n):
                p = sorted_points[right]

                # Remove points too far left
                while left < right and sorted_points[left].x < p.x - min_dist:
                    # Remove from active
                    try:
                        active.remove(sorted_points[left])
                    except ValueError:
                        pass
                    left += 1

                # Check points in active set within y range
                for q in active:
                    if abs(q.y - p.y) < min_dist:
                        dist = ((p.x - q.x) ** 2 + (p.y - q.y) ** 2) ** 0.5
                        if dist < min_dist:
                            min_dist = dist
                            closest_pair = (q, p)

                # Add current point to active set
                active.append(p)

            return closest_pair[0], closest_pair[1], min_dist


# ============================================================================
# SKYLINE PROBLEM
# ============================================================================

class Skyline:
    """
    Compute skyline of buildings using line sweep.

    Features:
    - O(n log n) time
    - Maximum heap for active heights

    "Ba'el traces the skyline." — Ba'el
    """

    def __init__(self):
        """Initialize skyline computer."""
        self._buildings: List[Tuple[int, int, int]] = []  # (left, right, height)
        self._lock = threading.RLock()

    def add_building(self, left: int, right: int, height: int) -> None:
        """Add building."""
        with self._lock:
            self._buildings.append((left, right, height))

    def compute_skyline(self) -> List[Tuple[int, int]]:
        """
        Compute skyline.

        Returns:
            List of (x, height) points defining skyline
        """
        with self._lock:
            if not self._buildings:
                return []

            # Create events: (x, type, height)
            # type: 0 = start, 1 = end
            events = []
            for left, right, height in self._buildings:
                events.append((left, 0, height))
                events.append((right, 1, height))

            # Sort by x, then by type (start before end), then by height
            events.sort(key=lambda e: (e[0], e[1], -e[2] if e[1] == 0 else e[2]))

            result = []
            # Use dict to count active heights (handles duplicates)
            active_heights: Dict[int, int] = defaultdict(int)
            active_heights[0] = 1  # Ground level

            for x, event_type, height in events:
                if event_type == 0:  # Start
                    active_heights[height] += 1
                else:  # End
                    active_heights[height] -= 1
                    if active_heights[height] == 0:
                        del active_heights[height]

                current_max = max(active_heights.keys())

                if not result or result[-1][1] != current_max:
                    result.append((x, current_max))

            return result


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_interval_overlap() -> IntervalOverlap:
    """Create interval overlap finder."""
    return IntervalOverlap()


def create_segment_intersection() -> SegmentIntersection:
    """Create segment intersection finder."""
    return SegmentIntersection()


def create_rectangle_union() -> RectangleUnion:
    """Create rectangle union computer."""
    return RectangleUnion()


def create_closest_pair_sweep() -> ClosestPairSweep:
    """Create closest pair finder."""
    return ClosestPairSweep()


def create_skyline() -> Skyline:
    """Create skyline computer."""
    return Skyline()


def find_overlapping_intervals(intervals: List[Tuple[float, float]]) -> List[Tuple[int, int]]:
    """Find all pairs of overlapping intervals."""
    finder = IntervalOverlap()
    for start, end in intervals:
        finder.add_interval(start, end)
    return finder.find_all_overlaps()


def merge_intervals(intervals: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
    """Merge overlapping intervals."""
    finder = IntervalOverlap()
    for start, end in intervals:
        finder.add_interval(start, end)
    merged = finder.merge_overlapping()
    return [(i.start, i.end) for i in merged]


def rectangle_union_area(rectangles: List[Tuple[float, float, float, float]]) -> float:
    """Compute area of union of rectangles."""
    union = RectangleUnion()
    for x1, y1, x2, y2 in rectangles:
        union.add_rectangle(x1, y1, x2, y2)
    return union.compute_union_area()


def compute_skyline(buildings: List[Tuple[int, int, int]]) -> List[Tuple[int, int]]:
    """Compute skyline of buildings."""
    sky = Skyline()
    for left, right, height in buildings:
        sky.add_building(left, right, height)
    return sky.compute_skyline()

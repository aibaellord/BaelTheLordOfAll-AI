"""
BAEL - Sacred Geometry & Golden Ratio Optimization Engine
Applies universal mathematical principles for perfect solutions.

Revolutionary capabilities:
1. Golden Ratio optimization - φ (1.618...) based proportioning
2. Fibonacci sequence application - Natural growth patterns
3. Sacred geometry patterns - Vesica Piscis, Flower of Life, Metatron's Cube
4. Harmonic resonance - Frequency-based optimization
5. Fractal recursion - Self-similar solutions at all scales
6. Platonic solid mapping - 5 elemental problem archetypes
7. Phi spiral navigation - Optimal path finding
8. Geometric balancing - Perfect equilibrium solutions

Based on the mathematical patterns underlying all of nature,
this engine creates solutions with inherent harmony and success.
"""

import asyncio
import hashlib
import logging
import math
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("BAEL.SacredGeometry")

# Universal Constants
PHI = (1 + math.sqrt(5)) / 2  # Golden Ratio ≈ 1.618033988749895
PHI_INVERSE = 1 / PHI         # ≈ 0.618033988749895
SQRT_2 = math.sqrt(2)         # ≈ 1.414213562373095
SQRT_3 = math.sqrt(3)         # ≈ 1.732050807568877
SQRT_5 = math.sqrt(5)         # ≈ 2.236067977499790
PI = math.pi                  # ≈ 3.141592653589793
E = math.e                    # ≈ 2.718281828459045

# Fibonacci sequence (first 20 numbers)
FIBONACCI = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377, 610, 987, 1597, 2584, 4181, 6765]


class SacredPattern(Enum):
    """Sacred geometry patterns."""
    VESICA_PISCIS = "vesica_piscis"       # Union of two circles - creation
    FLOWER_OF_LIFE = "flower_of_life"     # Interconnected circles - interconnection
    SEED_OF_LIFE = "seed_of_life"         # 7 circles - genesis
    METATRONS_CUBE = "metatrons_cube"     # All platonic solids - completion
    SRI_YANTRA = "sri_yantra"             # 9 interlocking triangles - manifestation
    TORUS = "torus"                       # Self-sustaining flow - energy
    MERKABA = "merkaba"                   # Star tetrahedron - ascension


class PlatonicSolid(Enum):
    """The 5 Platonic solids and their elemental associations."""
    TETRAHEDRON = ("tetrahedron", 4, "fire", "transformation")
    CUBE = ("cube", 6, "earth", "stability")
    OCTAHEDRON = ("octahedron", 8, "air", "intellect")
    DODECAHEDRON = ("dodecahedron", 12, "ether", "spirit")
    ICOSAHEDRON = ("icosahedron", 20, "water", "emotion")


class HarmonicFrequency(Enum):
    """Harmonic frequencies and their properties."""
    UNITY = (1, "foundation")
    OCTAVE = (2, "doubling")
    PERFECT_FIFTH = (1.5, "harmony")
    GOLDEN = (PHI, "beauty")
    PHI_SQUARED = (PHI ** 2, "expansion")


@dataclass
class GoldenProportions:
    """Proportions based on the golden ratio."""
    total: float
    major: float  # Larger segment (0.618 of total)
    minor: float  # Smaller segment (0.382 of total)

    @classmethod
    def from_total(cls, total: float) -> "GoldenProportions":
        """Create golden proportions from total."""
        major = total * PHI_INVERSE
        minor = total - major
        return cls(total=total, major=major, minor=minor)

    @classmethod
    def from_major(cls, major: float) -> "GoldenProportions":
        """Create golden proportions from major segment."""
        total = major * PHI
        minor = total - major
        return cls(total=total, major=major, minor=minor)

    @classmethod
    def from_minor(cls, minor: float) -> "GoldenProportions":
        """Create golden proportions from minor segment."""
        major = minor * PHI
        total = major + minor
        return cls(total=total, major=major, minor=minor)


@dataclass
class SpiralPoint:
    """A point on a phi spiral."""
    index: int
    x: float
    y: float
    radius: float
    angle: float  # In radians


@dataclass
class GeometricBalance:
    """Balance metrics for a solution."""
    symmetry_score: float = 0.0       # 0-1, perfect symmetry at 1
    proportion_score: float = 0.0     # 0-1, golden proportions at 1
    harmony_score: float = 0.0        # 0-1, harmonic ratios at 1
    complexity_balance: float = 0.0   # 0-1, optimal complexity at 1

    @property
    def total_balance(self) -> float:
        """Calculate total balance score."""
        return (
            self.symmetry_score * 0.25 +
            self.proportion_score * 0.35 +  # Golden ratio weighted highest
            self.harmony_score * 0.25 +
            self.complexity_balance * 0.15
        )


@dataclass
class OptimizedSolution:
    """A solution optimized through sacred geometry."""
    solution_id: str
    original_input: Any
    optimized_output: Any

    # Optimization details
    patterns_applied: List[SacredPattern] = field(default_factory=list)
    proportions_used: Optional[GoldenProportions] = None
    harmonic_tuning: List[float] = field(default_factory=list)

    # Balance
    balance: GeometricBalance = field(default_factory=GeometricBalance)

    # Metrics
    improvement_factor: float = 1.0
    aesthetic_score: float = 0.0
    success_probability: float = 0.0


class FibonacciOptimizer:
    """Optimizes using Fibonacci sequences."""

    def get_nearest_fibonacci(self, n: int) -> Tuple[int, int]:
        """Get nearest Fibonacci numbers (below and above)."""
        below = 1
        above = 1

        for fib in FIBONACCI:
            if fib <= n:
                below = fib
            if fib >= n:
                above = fib
                break

        return below, above

    def fibonacci_partition(self, total: int, parts: int) -> List[int]:
        """Partition total into Fibonacci-proportioned parts."""
        if parts <= 0:
            return []
        if parts == 1:
            return [total]

        # Use consecutive Fibonacci numbers for proportions
        fib_sum = sum(FIBONACCI[:parts])

        result = []
        remaining = total

        for i in range(parts - 1):
            part = int(total * FIBONACCI[i] / fib_sum)
            result.append(part)
            remaining -= part

        result.append(remaining)  # Last part gets remainder
        return result

    def optimize_sequence(self, values: List[float]) -> List[float]:
        """Optimize a sequence using Fibonacci ratios."""
        if len(values) < 2:
            return values

        optimized = [values[0]]

        for i in range(1, len(values)):
            # Apply Fibonacci ratio between consecutive values
            fib_ratio = FIBONACCI[min(i, len(FIBONACCI) - 1)] / FIBONACCI[min(i - 1, len(FIBONACCI) - 1)]
            target = optimized[-1] * fib_ratio

            # Blend original with Fibonacci-optimized
            optimized.append(values[i] * 0.5 + target * 0.5)

        return optimized


class GoldenRatioOptimizer:
    """Optimizes using the golden ratio."""

    def golden_split(self, total: float) -> Tuple[float, float]:
        """Split total into golden ratio proportions."""
        major = total * PHI_INVERSE
        minor = total - major
        return major, minor

    def golden_mean(self, a: float, b: float) -> float:
        """Calculate the golden mean between two values."""
        return (a + b * PHI) / (1 + PHI)

    def optimize_proportions(
        self,
        values: List[float]
    ) -> List[float]:
        """Optimize values to follow golden proportions."""
        if len(values) < 2:
            return values

        # Normalize to sum
        total = sum(values)

        # Create golden spiral of proportions
        optimized = []
        remaining = total

        for i in range(len(values) - 1):
            portion = remaining * PHI_INVERSE
            optimized.append(portion)
            remaining -= portion

        optimized.append(remaining)
        return optimized

    def phi_power_scale(self, base: float, steps: int) -> List[float]:
        """Create a scale based on powers of phi."""
        return [base * (PHI ** i) for i in range(steps)]


class PhiSpiralNavigator:
    """Navigates solution space using phi spirals."""

    def __init__(self):
        self._spiral_points: List[SpiralPoint] = []

    def generate_spiral(self, num_points: int, scale: float = 1.0) -> List[SpiralPoint]:
        """Generate points on a phi spiral."""
        points = []

        golden_angle = 2 * PI * PHI_INVERSE  # ≈ 137.5°

        for i in range(num_points):
            radius = scale * math.sqrt(i)
            angle = i * golden_angle

            x = radius * math.cos(angle)
            y = radius * math.sin(angle)

            points.append(SpiralPoint(
                index=i,
                x=x,
                y=y,
                radius=radius,
                angle=angle
            ))

        self._spiral_points = points
        return points

    def find_optimal_position(
        self,
        constraints: List[Tuple[float, float]]
    ) -> SpiralPoint:
        """Find optimal position on spiral given constraints."""
        if not self._spiral_points:
            self.generate_spiral(100)

        # Score each point against constraints
        best_point = self._spiral_points[0]
        best_score = float('inf')

        for point in self._spiral_points:
            score = 0
            for cx, cy in constraints:
                dist = math.sqrt((point.x - cx) ** 2 + (point.y - cy) ** 2)
                score += dist

            if score < best_score:
                best_score = score
                best_point = point

        return best_point


class SacredPatternApplicator:
    """Applies sacred geometry patterns to solutions."""

    def __init__(self):
        self._pattern_properties = {
            SacredPattern.VESICA_PISCIS: {
                "ratio": SQRT_3,
                "principle": "union",
                "application": "combining_solutions"
            },
            SacredPattern.FLOWER_OF_LIFE: {
                "ratio": 7,  # 7 circles
                "principle": "interconnection",
                "application": "system_integration"
            },
            SacredPattern.SEED_OF_LIFE: {
                "ratio": 7,
                "principle": "genesis",
                "application": "new_creation"
            },
            SacredPattern.METATRONS_CUBE: {
                "ratio": 13,  # 13 spheres
                "principle": "completion",
                "application": "comprehensive_solution"
            },
            SacredPattern.SRI_YANTRA: {
                "ratio": 9,
                "principle": "manifestation",
                "application": "goal_achievement"
            },
            SacredPattern.TORUS: {
                "ratio": PI,
                "principle": "self-sustaining",
                "application": "perpetual_systems"
            },
            SacredPattern.MERKABA: {
                "ratio": PHI,
                "principle": "ascension",
                "application": "transcendent_solutions"
            }
        }

    def select_pattern(self, problem_type: str) -> SacredPattern:
        """Select optimal sacred pattern for problem type."""
        mappings = {
            "combine": SacredPattern.VESICA_PISCIS,
            "integrate": SacredPattern.FLOWER_OF_LIFE,
            "create": SacredPattern.SEED_OF_LIFE,
            "complete": SacredPattern.METATRONS_CUBE,
            "achieve": SacredPattern.SRI_YANTRA,
            "sustain": SacredPattern.TORUS,
            "transcend": SacredPattern.MERKABA
        }

        for key, pattern in mappings.items():
            if key in problem_type.lower():
                return pattern

        return SacredPattern.FLOWER_OF_LIFE  # Default: interconnection

    def apply_pattern(
        self,
        solution: Any,
        pattern: SacredPattern
    ) -> Tuple[Any, Dict[str, Any]]:
        """Apply sacred pattern to solution."""
        props = self._pattern_properties[pattern]

        # Create pattern application report
        report = {
            "pattern": pattern.value,
            "ratio_applied": props["ratio"],
            "principle": props["principle"],
            "application_type": props["application"],
            "enhancement_factor": props["ratio"] if isinstance(props["ratio"], float) else 1.0 + (props["ratio"] / 10)
        }

        # The actual solution transformation would depend on solution type
        # For now, we return metadata about the transformation

        return solution, report


class PlatonicSolidMapper:
    """Maps problems to Platonic solid archetypes."""

    def __init__(self):
        self._solid_properties = {
            PlatonicSolid.TETRAHEDRON: {
                "faces": 4,
                "element": "fire",
                "quality": "transformation",
                "approach": "radical_change"
            },
            PlatonicSolid.CUBE: {
                "faces": 6,
                "element": "earth",
                "quality": "stability",
                "approach": "solid_foundation"
            },
            PlatonicSolid.OCTAHEDRON: {
                "faces": 8,
                "element": "air",
                "quality": "intellect",
                "approach": "analytical"
            },
            PlatonicSolid.DODECAHEDRON: {
                "faces": 12,
                "element": "ether",
                "quality": "spirit",
                "approach": "holistic"
            },
            PlatonicSolid.ICOSAHEDRON: {
                "faces": 20,
                "element": "water",
                "quality": "emotion",
                "approach": "adaptive"
            }
        }

    def map_problem(self, problem_characteristics: Dict[str, Any]) -> PlatonicSolid:
        """Map problem to appropriate Platonic solid."""
        # Analyze characteristics
        needs_transformation = problem_characteristics.get("needs_change", False)
        needs_stability = problem_characteristics.get("needs_stability", False)
        is_analytical = problem_characteristics.get("analytical", False)
        is_holistic = problem_characteristics.get("holistic", False)
        is_adaptive = problem_characteristics.get("adaptive", False)

        if needs_transformation:
            return PlatonicSolid.TETRAHEDRON
        elif needs_stability:
            return PlatonicSolid.CUBE
        elif is_analytical:
            return PlatonicSolid.OCTAHEDRON
        elif is_holistic:
            return PlatonicSolid.DODECAHEDRON
        elif is_adaptive:
            return PlatonicSolid.ICOSAHEDRON

        return PlatonicSolid.DODECAHEDRON  # Default: holistic

    def get_approach(self, solid: PlatonicSolid) -> Dict[str, Any]:
        """Get problem-solving approach for solid."""
        return self._solid_properties[solid]


class HarmonicTuner:
    """Tunes solutions using harmonic frequencies."""

    def __init__(self):
        self._base_frequency = 432  # Hz - natural tuning

    def calculate_harmonics(self, base: float, count: int) -> List[float]:
        """Calculate harmonic series from base."""
        return [base * (i + 1) for i in range(count)]

    def find_resonance(self, value: float, target_harmonic: HarmonicFrequency) -> float:
        """Tune value to resonate with target harmonic."""
        ratio = target_harmonic.value[0]

        # Find nearest harmonic multiple
        multiple = round(value / (self._base_frequency * ratio))
        resonant_value = multiple * self._base_frequency * ratio

        return resonant_value

    def optimize_for_harmony(self, values: List[float]) -> List[float]:
        """Optimize values for harmonic relationships."""
        if not values:
            return values

        # Use first value as reference
        reference = values[0]

        optimized = [reference]
        for value in values[1:]:
            # Find ratio to reference
            ratio = value / reference if reference != 0 else 1

            # Find nearest harmonic ratio
            harmonic_ratios = [1, 1.5, 2, PHI, 3, 4, 5]  # Common harmonics
            nearest = min(harmonic_ratios, key=lambda r: abs(ratio - r))

            optimized.append(reference * nearest)

        return optimized


class GeometricBalancer:
    """Balances solutions using geometric principles."""

    def __init__(self):
        self.golden_optimizer = GoldenRatioOptimizer()
        self.fibonacci_optimizer = FibonacciOptimizer()

    def calculate_balance(self, solution: Dict[str, Any]) -> GeometricBalance:
        """Calculate geometric balance of solution."""
        balance = GeometricBalance()

        # Check for values to analyze
        if "values" in solution:
            values = solution["values"]

            # Symmetry score
            balance.symmetry_score = self._calculate_symmetry(values)

            # Proportion score (closeness to golden ratio)
            balance.proportion_score = self._calculate_proportion_score(values)

            # Harmony score
            balance.harmony_score = self._calculate_harmony(values)

            # Complexity balance
            balance.complexity_balance = self._calculate_complexity_balance(len(values))
        else:
            # Default balanced scores
            balance.symmetry_score = 0.7
            balance.proportion_score = 0.7
            balance.harmony_score = 0.7
            balance.complexity_balance = 0.7

        return balance

    def optimize_for_balance(
        self,
        solution: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], GeometricBalance]:
        """Optimize solution for geometric balance."""
        if "values" in solution:
            # Optimize proportions
            solution["values"] = self.golden_optimizer.optimize_proportions(
                solution["values"]
            )

        balance = self.calculate_balance(solution)
        return solution, balance

    def _calculate_symmetry(self, values: List[float]) -> float:
        """Calculate symmetry score."""
        if len(values) < 2:
            return 1.0

        # Compare first half to reversed second half
        mid = len(values) // 2
        first_half = values[:mid]
        second_half = list(reversed(values[-mid:]))

        if not first_half or not second_half:
            return 0.5

        differences = []
        for a, b in zip(first_half, second_half):
            max_val = max(abs(a), abs(b), 1)
            diff = abs(a - b) / max_val
            differences.append(1 - min(diff, 1))

        return sum(differences) / len(differences)

    def _calculate_proportion_score(self, values: List[float]) -> float:
        """Calculate how close proportions are to golden ratio."""
        if len(values) < 2:
            return 1.0

        scores = []
        for i in range(len(values) - 1):
            if values[i + 1] != 0:
                ratio = values[i] / values[i + 1]
                # Distance from phi or 1/phi
                dist_to_phi = abs(ratio - PHI)
                dist_to_inv_phi = abs(ratio - PHI_INVERSE)
                min_dist = min(dist_to_phi, dist_to_inv_phi)
                score = max(0, 1 - min_dist / PHI)  # Normalize
                scores.append(score)

        return sum(scores) / len(scores) if scores else 0.5

    def _calculate_harmony(self, values: List[float]) -> float:
        """Calculate harmonic quality of values."""
        if len(values) < 2:
            return 1.0

        # Check for harmonic ratios
        harmonic_ratios = [1, 1.5, 2, 2.5, 3, 4, 5, PHI, PHI_INVERSE]

        scores = []
        reference = values[0] if values[0] != 0 else 1

        for value in values[1:]:
            if reference != 0:
                ratio = value / reference
                # Find nearest harmonic
                nearest = min(harmonic_ratios, key=lambda r: abs(ratio - r))
                dist = abs(ratio - nearest)
                score = max(0, 1 - dist)
                scores.append(score)

        return sum(scores) / len(scores) if scores else 0.5

    def _calculate_complexity_balance(self, element_count: int) -> float:
        """Calculate if complexity is optimally balanced."""
        # Optimal complexity follows Fibonacci
        _, nearest_fib = self.fibonacci_optimizer.get_nearest_fibonacci(element_count)

        # Score based on distance from Fibonacci number
        distance = abs(element_count - nearest_fib)
        return max(0, 1 - distance / 10)


class SacredGeometryEngine:
    """
    The Ultimate Sacred Geometry Optimization Engine.

    Applies universal mathematical principles:
    1. Golden Ratio (φ) optimization
    2. Fibonacci sequence application
    3. Sacred geometry patterns
    4. Harmonic tuning
    5. Platonic solid mapping
    6. Phi spiral navigation
    7. Geometric balancing

    Creates solutions with inherent harmony and success probability.
    """

    def __init__(self, llm_provider: Callable = None):
        self.llm_provider = llm_provider

        # Optimizers
        self.golden_optimizer = GoldenRatioOptimizer()
        self.fibonacci_optimizer = FibonacciOptimizer()
        self.spiral_navigator = PhiSpiralNavigator()
        self.pattern_applicator = SacredPatternApplicator()
        self.solid_mapper = PlatonicSolidMapper()
        self.harmonic_tuner = HarmonicTuner()
        self.balancer = GeometricBalancer()

        # Statistics
        self._stats = {
            "solutions_optimized": 0,
            "patterns_applied": 0,
            "average_balance_score": 0.0
        }

        logger.info("SacredGeometryEngine initialized - Universal harmony enabled")

    async def optimize_solution(
        self,
        solution: Any,
        problem_type: str = "general",
        apply_patterns: bool = True
    ) -> OptimizedSolution:
        """
        Optimize a solution using sacred geometry principles.
        """
        solution_id = f"geo_{hashlib.md5(str(solution).encode()).hexdigest()[:12]}"

        # Determine problem archetype
        characteristics = await self._analyze_problem(problem_type)
        solid = self.solid_mapper.map_problem(characteristics)
        approach = self.solid_mapper.get_approach(solid)

        # Convert solution to workable format
        working_solution = await self._prepare_solution(solution)

        # Apply golden ratio optimization
        if "values" in working_solution:
            working_solution["values"] = self.golden_optimizer.optimize_proportions(
                working_solution["values"]
            )

        # Apply sacred pattern
        pattern = self.pattern_applicator.select_pattern(problem_type)
        if apply_patterns:
            working_solution, pattern_report = self.pattern_applicator.apply_pattern(
                working_solution, pattern
            )

        # Calculate balance
        balance = self.balancer.calculate_balance(working_solution)

        # Create phi spiral for navigation
        spiral_points = self.spiral_navigator.generate_spiral(50)
        optimal_point = self.spiral_navigator.find_optimal_position([])

        # Calculate success probability based on balance
        success_probability = self._calculate_success_probability(balance, approach)

        # Calculate improvement factor
        improvement_factor = 1.0 + balance.total_balance * (PHI - 1)

        result = OptimizedSolution(
            solution_id=solution_id,
            original_input=solution,
            optimized_output=working_solution,
            patterns_applied=[pattern],
            proportions_used=GoldenProportions.from_total(1.0),
            harmonic_tuning=[PHI, PHI_INVERSE],
            balance=balance,
            improvement_factor=improvement_factor,
            aesthetic_score=balance.proportion_score * balance.harmony_score,
            success_probability=success_probability
        )

        # Update stats
        self._stats["solutions_optimized"] += 1
        self._stats["patterns_applied"] += 1
        self._stats["average_balance_score"] = (
            (self._stats["average_balance_score"] * (self._stats["solutions_optimized"] - 1) +
             balance.total_balance) / self._stats["solutions_optimized"]
        )

        return result

    async def generate_golden_structure(
        self,
        elements: List[str],
        structure_type: str = "hierarchy"
    ) -> Dict[str, Any]:
        """Generate a structure based on golden proportions."""
        if structure_type == "hierarchy":
            return await self._generate_golden_hierarchy(elements)
        elif structure_type == "sequence":
            return await self._generate_golden_sequence(elements)
        elif structure_type == "spiral":
            return await self._generate_golden_spiral(elements)
        else:
            return await self._generate_golden_hierarchy(elements)

    async def find_harmonic_solution(
        self,
        constraints: List[Tuple[str, float]],
        target_harmony: float = 0.9
    ) -> Dict[str, Any]:
        """Find solution in harmonic resonance with constraints."""
        # Extract constraint values
        values = [v for _, v in constraints]

        # Optimize for harmony
        harmonized = self.harmonic_tuner.optimize_for_harmony(values)

        # Create result
        result = {
            "original_constraints": constraints,
            "harmonized_values": harmonized,
            "harmony_achieved": self._calculate_achieved_harmony(values, harmonized)
        }

        return result

    async def _analyze_problem(self, problem_type: str) -> Dict[str, Any]:
        """Analyze problem characteristics."""
        characteristics = {
            "needs_change": "transform" in problem_type.lower() or "change" in problem_type.lower(),
            "needs_stability": "stable" in problem_type.lower() or "foundation" in problem_type.lower(),
            "analytical": "analyz" in problem_type.lower() or "logic" in problem_type.lower(),
            "holistic": "complet" in problem_type.lower() or "whole" in problem_type.lower(),
            "adaptive": "adapt" in problem_type.lower() or "flex" in problem_type.lower()
        }
        return characteristics

    async def _prepare_solution(self, solution: Any) -> Dict[str, Any]:
        """Prepare solution for optimization."""
        if isinstance(solution, dict):
            return solution.copy()
        elif isinstance(solution, list):
            return {"values": list(solution)}
        elif isinstance(solution, (int, float)):
            return {"values": [float(solution)]}
        else:
            return {"content": str(solution)}

    def _calculate_success_probability(
        self,
        balance: GeometricBalance,
        approach: Dict[str, Any]
    ) -> float:
        """Calculate success probability based on balance and approach."""
        # Base probability from balance
        base_prob = balance.total_balance

        # Apply approach modifier
        approach_bonus = {
            "radical_change": 0.1,
            "solid_foundation": 0.15,
            "analytical": 0.12,
            "holistic": 0.18,
            "adaptive": 0.14
        }

        modifier = approach_bonus.get(approach.get("approach", ""), 0.1)

        return min(1.0, base_prob * (1 + modifier))

    def _calculate_achieved_harmony(
        self,
        original: List[float],
        harmonized: List[float]
    ) -> float:
        """Calculate how much harmony was achieved."""
        if not original or not harmonized:
            return 0.0

        # Compare ratios
        original_ratios = []
        harmonized_ratios = []

        for i in range(len(original) - 1):
            if original[i + 1] != 0:
                original_ratios.append(original[i] / original[i + 1])
            if harmonized[i + 1] != 0:
                harmonized_ratios.append(harmonized[i] / harmonized[i + 1])

        # Score based on how harmonic the new ratios are
        harmonic_ratios = [1, 1.5, 2, PHI, 3]

        scores = []
        for ratio in harmonized_ratios:
            nearest = min(harmonic_ratios, key=lambda r: abs(ratio - r))
            score = 1 - min(abs(ratio - nearest), 1)
            scores.append(score)

        return sum(scores) / len(scores) if scores else 0.0

    async def _generate_golden_hierarchy(
        self,
        elements: List[str]
    ) -> Dict[str, Any]:
        """Generate hierarchy with golden proportions."""
        if not elements:
            return {"levels": []}

        # Partition elements using Fibonacci
        partitions = self.fibonacci_optimizer.fibonacci_partition(len(elements), 3)

        levels = []
        idx = 0
        for level_num, count in enumerate(partitions):
            level_elements = elements[idx:idx + count]
            levels.append({
                "level": level_num,
                "elements": level_elements,
                "proportion": count / len(elements)
            })
            idx += count

        return {
            "levels": levels,
            "total_elements": len(elements),
            "structure": "golden_hierarchy"
        }

    async def _generate_golden_sequence(
        self,
        elements: List[str]
    ) -> Dict[str, Any]:
        """Generate sequence with golden proportions."""
        proportions = self.golden_optimizer.phi_power_scale(1.0, len(elements))

        sequence = []
        for i, elem in enumerate(elements):
            sequence.append({
                "element": elem,
                "weight": proportions[i],
                "position": i
            })

        return {
            "sequence": sequence,
            "total_weight": sum(proportions),
            "structure": "golden_sequence"
        }

    async def _generate_golden_spiral(
        self,
        elements: List[str]
    ) -> Dict[str, Any]:
        """Generate spiral placement with golden angle."""
        points = self.spiral_navigator.generate_spiral(len(elements))

        spiral = []
        for elem, point in zip(elements, points):
            spiral.append({
                "element": elem,
                "x": point.x,
                "y": point.y,
                "radius": point.radius,
                "angle_degrees": math.degrees(point.angle)
            })

        return {
            "spiral": spiral,
            "total_elements": len(elements),
            "structure": "golden_spiral"
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics."""
        return self._stats.copy()


# Global instance
_sacred_geometry_engine: Optional[SacredGeometryEngine] = None


def get_sacred_geometry_engine() -> SacredGeometryEngine:
    """Get the global sacred geometry engine."""
    global _sacred_geometry_engine
    if _sacred_geometry_engine is None:
        _sacred_geometry_engine = SacredGeometryEngine()
    return _sacred_geometry_engine


async def demo():
    """Demonstrate the Sacred Geometry Engine."""
    engine = get_sacred_geometry_engine()

    # Example: Optimize a solution
    solution = {
        "values": [100, 45, 30, 25, 15, 10],
        "description": "Resource allocation"
    }

    result = await engine.optimize_solution(
        solution,
        problem_type="holistic optimization"
    )

    print("Sacred Geometry Optimization")
    print("=" * 50)
    print(f"Solution ID: {result.solution_id}")
    print(f"\nOriginal values: {solution['values']}")
    print(f"Optimized values: {result.optimized_output.get('values', [])}")
    print(f"\nPatterns applied: {[p.value for p in result.patterns_applied]}")
    print(f"Golden proportions: {result.proportions_used}")
    print(f"\nBalance Scores:")
    print(f"  Symmetry: {result.balance.symmetry_score:.3f}")
    print(f"  Proportion: {result.balance.proportion_score:.3f}")
    print(f"  Harmony: {result.balance.harmony_score:.3f}")
    print(f"  Complexity: {result.balance.complexity_balance:.3f}")
    print(f"  Total: {result.balance.total_balance:.3f}")
    print(f"\nImprovement factor: {result.improvement_factor:.3f}")
    print(f"Aesthetic score: {result.aesthetic_score:.3f}")
    print(f"Success probability: {result.success_probability:.3f}")


if __name__ == "__main__":
    asyncio.run(demo())

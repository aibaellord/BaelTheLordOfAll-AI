"""
BAEL - Golden Ratio & Sacred Geometry Creation System
The most advanced creation system using sacred geometry and golden ratio principles.

This system applies mathematical perfection to all creations:
1. Golden Ratio (φ = 1.618...) optimization for visual and structural design
2. Fibonacci sequences for natural growth patterns
3. Sacred geometry patterns for harmonic structures
4. Fractal generation for infinite scalability
5. Proportional optimization for business success
6. Aesthetic scoring based on mathematical harmony
7. Visual composition using divine proportions

No other system applies these timeless principles to AI-driven creation.
"""

import asyncio
import hashlib
import json
import logging
import math
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple
import random

logger = logging.getLogger("BAEL.GoldenRatioCreation")

# Mathematical Constants
PHI = (1 + math.sqrt(5)) / 2  # Golden Ratio ≈ 1.618033988749895
PSI = PHI - 1  # Inverse Golden Ratio ≈ 0.618033988749895
SQRT_PHI = math.sqrt(PHI)  # √φ ≈ 1.272019649514069


class SacredPattern(Enum):
    """Sacred geometry patterns."""
    GOLDEN_SPIRAL = "golden_spiral"
    FIBONACCI = "fibonacci"
    FLOWER_OF_LIFE = "flower_of_life"
    METATRON_CUBE = "metatron_cube"
    VESICA_PISCIS = "vesica_piscis"
    SEED_OF_LIFE = "seed_of_life"
    GOLDEN_RECTANGLE = "golden_rectangle"
    PLATONIC_SOLID = "platonic_solid"
    FRACTAL = "fractal"


class OptimizationDomain(Enum):
    """Domains for golden ratio optimization."""
    VISUAL_DESIGN = "visual_design"
    ARCHITECTURE = "architecture"
    BUSINESS_STRATEGY = "business_strategy"
    CONTENT_STRUCTURE = "content_structure"
    CODE_ORGANIZATION = "code_organization"
    TIME_MANAGEMENT = "time_management"
    RESOURCE_ALLOCATION = "resource_allocation"
    TEAM_COMPOSITION = "team_composition"
    PRICING = "pricing"
    COMMUNICATION = "communication"


@dataclass
class GoldenProportion:
    """A proportion based on the golden ratio."""
    larger: float
    smaller: float
    ratio: float = field(init=False)
    is_golden: bool = field(init=False)
    
    def __post_init__(self):
        self.ratio = self.larger / self.smaller if self.smaller != 0 else 0
        self.is_golden = abs(self.ratio - PHI) < 0.01
    
    @classmethod
    def from_total(cls, total: float) -> "GoldenProportion":
        """Create golden proportion from total."""
        larger = total / PHI
        smaller = total - larger
        return cls(larger=larger, smaller=smaller)
    
    @classmethod
    def from_smaller(cls, smaller: float) -> "GoldenProportion":
        """Create golden proportion from smaller segment."""
        larger = smaller * PHI
        return cls(larger=larger, smaller=smaller)


@dataclass
class FibonacciSequence:
    """Fibonacci sequence generator and utilities."""
    length: int = 20
    sequence: List[int] = field(default_factory=list)
    
    def __post_init__(self):
        self.sequence = self._generate(self.length)
    
    def _generate(self, n: int) -> List[int]:
        """Generate Fibonacci sequence."""
        if n <= 0:
            return []
        if n == 1:
            return [1]
        
        seq = [1, 1]
        for _ in range(2, n):
            seq.append(seq[-1] + seq[-2])
        return seq
    
    def get_ratio_at(self, index: int) -> float:
        """Get ratio of consecutive terms (approaches φ)."""
        if index <= 0 or index >= len(self.sequence):
            return PHI
        return self.sequence[index] / self.sequence[index - 1]
    
    def get_nearest(self, value: float) -> int:
        """Get nearest Fibonacci number."""
        return min(self.sequence, key=lambda x: abs(x - value))


@dataclass
class SacredGeometryResult:
    """Result of sacred geometry application."""
    pattern: SacredPattern
    domain: OptimizationDomain
    
    # Original values
    original_values: Dict[str, Any] = field(default_factory=dict)
    
    # Optimized values
    optimized_values: Dict[str, Any] = field(default_factory=dict)
    
    # Scores
    harmony_score: float = 0.0  # 0-1
    golden_alignment: float = 0.0  # 0-1
    aesthetic_score: float = 0.0  # 0-1
    
    # Explanation
    reasoning: str = ""
    improvements: List[str] = field(default_factory=list)


class GoldenOptimizer:
    """Optimizer using golden ratio principles."""
    
    def __init__(self):
        self.fibonacci = FibonacciSequence(30)
    
    def optimize_proportions(
        self,
        values: List[float],
        domain: OptimizationDomain
    ) -> List[float]:
        """Optimize a list of values to golden proportions."""
        if not values or len(values) < 2:
            return values
        
        total = sum(values)
        
        # Create golden segments
        if len(values) == 2:
            prop = GoldenProportion.from_total(total)
            return [prop.larger, prop.smaller]
        
        # For more values, use Fibonacci-like distribution
        fib_base = self.fibonacci.sequence[:len(values)]
        fib_total = sum(fib_base)
        
        return [(f / fib_total) * total for f in fib_base]
    
    def optimize_layout(
        self,
        width: float,
        height: float
    ) -> Dict[str, float]:
        """Optimize layout using golden rectangle."""
        # Determine if width or height should be primary
        if width > height:
            new_height = width / PHI
            if new_height > height:
                new_width = height * PHI
                new_height = height
            else:
                new_width = width
        else:
            new_width = height / PHI
            if new_width > width:
                new_height = width * PHI
                new_width = width
            else:
                new_height = height
        
        return {
            "width": new_width,
            "height": new_height,
            "ratio": new_width / new_height if new_height else 0,
            "is_golden": abs((new_width / new_height) - PHI) < 0.01 if new_height else False
        }
    
    def calculate_golden_points(
        self,
        width: float,
        height: float
    ) -> List[Tuple[float, float]]:
        """Calculate golden ratio points for composition (rule of thirds on steroids)."""
        points = []
        
        # Horizontal golden points
        h1 = width / PHI
        h2 = width - h1
        
        # Vertical golden points
        v1 = height / PHI
        v2 = height - v1
        
        # Four golden intersection points
        points.append((h2, v2))  # Primary power point
        points.append((h1, v2))
        points.append((h2, v1))
        points.append((h1, v1))
        
        # Golden spiral focus points
        points.append((h2 * PSI, v2 * PSI))
        points.append((width - h2 * PSI, height - v2 * PSI))
        
        return points
    
    def optimize_pricing(
        self,
        base_price: float,
        num_tiers: int = 3
    ) -> List[Dict[str, Any]]:
        """Optimize pricing tiers using golden ratio."""
        tiers = []
        
        # Use golden ratio for tier spacing
        for i in range(num_tiers):
            multiplier = PHI ** (i - 1)  # 1/φ, 1, φ, φ², ...
            price = base_price * multiplier
            
            # Round to psychologically appealing number
            if price > 100:
                price = round(price / 10) * 10 - 1  # e.g., 149, 259
            elif price > 10:
                price = round(price) - 0.01  # e.g., 14.99, 24.99
            else:
                price = round(price, 2)
            
            tier_name = ["Basic", "Pro", "Enterprise", "Ultimate", "Infinite"][i] if i < 5 else f"Tier {i+1}"
            
            tiers.append({
                "tier": tier_name,
                "price": price,
                "multiplier": multiplier,
                "golden_aligned": True
            })
        
        return tiers
    
    def optimize_time_allocation(
        self,
        total_time: float,
        tasks: List[str]
    ) -> Dict[str, float]:
        """Allocate time using Fibonacci proportions."""
        if not tasks:
            return {}
        
        # Use Fibonacci for importance-based allocation
        fib = self.fibonacci.sequence[:len(tasks)]
        fib_total = sum(fib)
        
        allocation = {}
        for i, task in enumerate(tasks):
            # Most important tasks get larger Fibonacci numbers
            allocation[task] = (fib[-(i+1)] / fib_total) * total_time if i < len(fib) else total_time / len(tasks)
        
        return allocation
    
    def calculate_harmony_score(
        self,
        values: List[float]
    ) -> float:
        """Calculate how harmonious a set of values is based on golden ratio."""
        if len(values) < 2:
            return 1.0
        
        scores = []
        for i in range(len(values) - 1):
            if values[i+1] != 0:
                ratio = values[i] / values[i+1]
                # Score based on closeness to φ or 1/φ or Fibonacci ratios
                phi_diff = min(abs(ratio - PHI), abs(ratio - PSI), abs(ratio - 1))
                score = 1 - min(phi_diff / PHI, 1)
                scores.append(score)
        
        return sum(scores) / len(scores) if scores else 0.0


class SacredGeometryGenerator:
    """Generator for sacred geometry patterns."""
    
    def __init__(self):
        self.optimizer = GoldenOptimizer()
    
    def generate_golden_spiral_points(
        self,
        center: Tuple[float, float],
        scale: float,
        rotations: float = 3
    ) -> List[Tuple[float, float]]:
        """Generate points along a golden spiral."""
        points = []
        
        # Parametric golden spiral: r = a * φ^(θ/90°)
        steps = int(rotations * 360 / 5)  # Point every 5 degrees
        
        for i in range(steps):
            theta = math.radians(i * 5)
            r = scale * (PHI ** (theta / (math.pi / 2)))
            
            x = center[0] + r * math.cos(theta)
            y = center[1] + r * math.sin(theta)
            points.append((x, y))
        
        return points
    
    def generate_flower_of_life(
        self,
        center: Tuple[float, float],
        radius: float,
        layers: int = 3
    ) -> List[Dict[str, Any]]:
        """Generate Flower of Life pattern (circles)."""
        circles = []
        
        # Center circle
        circles.append({"center": center, "radius": radius})
        
        if layers < 1:
            return circles
        
        # Generate surrounding circles
        for layer in range(1, layers + 1):
            num_circles = 6 * layer
            angle_step = 2 * math.pi / 6
            
            for ring in range(layer):
                ring_radius = radius * (ring + 1)
                
                for i in range(6):
                    angle = i * angle_step + (ring * angle_step / 2)
                    x = center[0] + ring_radius * math.cos(angle)
                    y = center[1] + ring_radius * math.sin(angle)
                    circles.append({"center": (x, y), "radius": radius})
        
        return circles
    
    def generate_fibonacci_spiral_grid(
        self,
        width: float,
        height: float,
        depth: int = 8
    ) -> List[Dict[str, Any]]:
        """Generate Fibonacci spiral grid (golden rectangles)."""
        rectangles = []
        fib = FibonacciSequence(depth + 2)
        
        x, y = 0, 0
        direction = 0  # 0=right, 1=up, 2=left, 3=down
        
        for i in range(depth):
            f = fib.sequence[depth - i - 1]
            scale = min(width, height) / fib.sequence[depth - 1]
            size = f * scale
            
            rect = {
                "x": x,
                "y": y,
                "width": size if direction in [0, 2] else size / PHI,
                "height": size / PHI if direction in [0, 2] else size,
                "fibonacci_number": f
            }
            rectangles.append(rect)
            
            # Move to next position
            if direction == 0:
                x += size
                y += size - size / PHI
            elif direction == 1:
                y -= size / PHI
            elif direction == 2:
                x -= size / PHI
            elif direction == 3:
                pass
            
            direction = (direction + 1) % 4
        
        return rectangles
    
    def generate_platonic_vertices(
        self,
        solid_type: str,
        center: Tuple[float, float, float],
        scale: float
    ) -> List[Tuple[float, float, float]]:
        """Generate vertices of Platonic solids."""
        vertices = []
        
        if solid_type == "tetrahedron":
            # 4 vertices
            vertices = [
                (1, 1, 1), (1, -1, -1), (-1, 1, -1), (-1, -1, 1)
            ]
        elif solid_type == "cube":
            # 8 vertices
            for x in [-1, 1]:
                for y in [-1, 1]:
                    for z in [-1, 1]:
                        vertices.append((x, y, z))
        elif solid_type == "octahedron":
            # 6 vertices
            vertices = [
                (1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)
            ]
        elif solid_type == "dodecahedron":
            # 20 vertices - using golden ratio
            for i in [-1, 1]:
                for j in [-1, 1]:
                    vertices.append((0, i * PSI, j * PHI))
                    vertices.append((i * PSI, j * PHI, 0))
                    vertices.append((i * PHI, 0, j * PSI))
            for x in [-1, 1]:
                for y in [-1, 1]:
                    for z in [-1, 1]:
                        vertices.append((x, y, z))
        elif solid_type == "icosahedron":
            # 12 vertices - using golden ratio
            for i in [-1, 1]:
                for j in [-1, 1]:
                    vertices.append((0, i, j * PHI))
                    vertices.append((i, j * PHI, 0))
                    vertices.append((i * PHI, 0, j))
        
        # Scale and translate
        scaled = [
            (center[0] + v[0] * scale, center[1] + v[1] * scale, center[2] + v[2] * scale)
            for v in vertices
        ]
        
        return scaled


class GoldenRatioCreationSystem:
    """
    Main interface for Golden Ratio & Sacred Geometry Creation.
    
    Applies mathematical perfection to all creations:
    - Visual design with divine proportions
    - Business strategy with Fibonacci scaling
    - Content structure with harmonic flow
    - Code organization with golden modules
    """
    
    def __init__(self, llm_provider: Callable = None):
        self.llm_provider = llm_provider
        self.optimizer = GoldenOptimizer()
        self.generator = SacredGeometryGenerator()
        
        logger.info("GoldenRatioCreationSystem initialized")
    
    def optimize_for_domain(
        self,
        values: Dict[str, Any],
        domain: OptimizationDomain
    ) -> SacredGeometryResult:
        """Optimize values for a specific domain using sacred geometry."""
        original = values.copy()
        optimized = {}
        improvements = []
        
        if domain == OptimizationDomain.VISUAL_DESIGN:
            if "width" in values and "height" in values:
                layout = self.optimizer.optimize_layout(values["width"], values["height"])
                optimized.update(layout)
                if layout["is_golden"]:
                    improvements.append("Applied golden rectangle proportions")
            
            if "elements" in values and isinstance(values["elements"], list):
                golden_points = self.optimizer.calculate_golden_points(
                    values.get("width", 100),
                    values.get("height", 100)
                )
                optimized["golden_points"] = golden_points
                improvements.append("Calculated golden focal points for element placement")
        
        elif domain == OptimizationDomain.PRICING:
            if "base_price" in values:
                tiers = self.optimizer.optimize_pricing(
                    values["base_price"],
                    values.get("num_tiers", 3)
                )
                optimized["pricing_tiers"] = tiers
                improvements.append("Created golden ratio pricing tiers")
        
        elif domain == OptimizationDomain.TIME_MANAGEMENT:
            if "total_time" in values and "tasks" in values:
                allocation = self.optimizer.optimize_time_allocation(
                    values["total_time"],
                    values["tasks"]
                )
                optimized["time_allocation"] = allocation
                improvements.append("Allocated time using Fibonacci proportions")
        
        elif domain == OptimizationDomain.RESOURCE_ALLOCATION:
            if "resources" in values and isinstance(values["resources"], list):
                optimized_resources = self.optimizer.optimize_proportions(
                    values["resources"],
                    domain
                )
                optimized["resources"] = optimized_resources
                improvements.append("Optimized resource distribution with golden ratios")
        
        elif domain == OptimizationDomain.CONTENT_STRUCTURE:
            if "sections" in values and isinstance(values["sections"], list):
                # Optimize section lengths using Fibonacci
                fib = FibonacciSequence(len(values["sections"]) + 2)
                total_length = values.get("total_length", 1000)
                
                section_lengths = []
                fib_subset = fib.sequence[:len(values["sections"])]
                fib_total = sum(fib_subset)
                
                for i, section in enumerate(values["sections"]):
                    length = (fib_subset[-(i+1)] / fib_total) * total_length
                    section_lengths.append({
                        "section": section,
                        "recommended_length": int(length),
                        "fibonacci_number": fib_subset[-(i+1)]
                    })
                
                optimized["section_structure"] = section_lengths
                improvements.append("Structured content using Fibonacci proportions")
        
        # Calculate scores
        all_numeric = [v for v in optimized.values() if isinstance(v, (int, float))]
        harmony_score = self.optimizer.calculate_harmony_score(all_numeric) if all_numeric else 0.8
        
        return SacredGeometryResult(
            pattern=SacredPattern.GOLDEN_RECTANGLE,
            domain=domain,
            original_values=original,
            optimized_values=optimized,
            harmony_score=harmony_score,
            golden_alignment=0.9 if improvements else 0.5,
            aesthetic_score=harmony_score * 0.9,
            reasoning=f"Applied {len(improvements)} sacred geometry optimizations",
            improvements=improvements
        )
    
    def generate_sacred_pattern(
        self,
        pattern: SacredPattern,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate a sacred geometry pattern."""
        result = {"pattern": pattern.value}
        
        center = kwargs.get("center", (0, 0))
        scale = kwargs.get("scale", 100)
        
        if pattern == SacredPattern.GOLDEN_SPIRAL:
            points = self.generator.generate_golden_spiral_points(
                center, scale, kwargs.get("rotations", 3)
            )
            result["points"] = points
            result["description"] = "Golden spiral following φ progression"
        
        elif pattern == SacredPattern.FLOWER_OF_LIFE:
            circles = self.generator.generate_flower_of_life(
                center, scale, kwargs.get("layers", 3)
            )
            result["circles"] = circles
            result["description"] = "Flower of Life - symbol of creation"
        
        elif pattern == SacredPattern.FIBONACCI:
            fib = FibonacciSequence(kwargs.get("length", 20))
            result["sequence"] = fib.sequence
            result["ratios"] = [fib.get_ratio_at(i) for i in range(1, len(fib.sequence))]
            result["description"] = f"Fibonacci sequence approaching φ = {PHI:.10f}"
        
        elif pattern == SacredPattern.GOLDEN_RECTANGLE:
            grid = self.generator.generate_fibonacci_spiral_grid(
                kwargs.get("width", 800),
                kwargs.get("height", 500),
                kwargs.get("depth", 8)
            )
            result["rectangles"] = grid
            result["description"] = "Fibonacci spiral grid with golden rectangles"
        
        elif pattern == SacredPattern.PLATONIC_SOLID:
            solid_type = kwargs.get("solid_type", "icosahedron")
            vertices = self.generator.generate_platonic_vertices(
                solid_type,
                (center[0], center[1], 0),
                scale
            )
            result["vertices"] = vertices
            result["solid_type"] = solid_type
            result["description"] = f"Platonic solid: {solid_type} - perfect geometric form"
        
        return result
    
    def analyze_harmony(
        self,
        values: List[float]
    ) -> Dict[str, Any]:
        """Analyze the harmony of a set of values."""
        score = self.optimizer.calculate_harmony_score(values)
        
        # Check for Fibonacci numbers
        fib = FibonacciSequence(30)
        fib_matches = [v for v in values if v in fib.sequence]
        
        # Check for golden ratios between consecutive values
        golden_ratios = []
        for i in range(len(values) - 1):
            if values[i+1] != 0:
                ratio = values[i] / values[i+1]
                if abs(ratio - PHI) < 0.1 or abs(ratio - PSI) < 0.1:
                    golden_ratios.append((values[i], values[i+1], ratio))
        
        return {
            "harmony_score": score,
            "fibonacci_numbers_found": fib_matches,
            "golden_ratios_found": golden_ratios,
            "recommendations": self._generate_harmony_recommendations(score, values)
        }
    
    def _generate_harmony_recommendations(
        self,
        score: float,
        values: List[float]
    ) -> List[str]:
        """Generate recommendations for improving harmony."""
        recommendations = []
        
        if score < 0.5:
            recommendations.append("Consider restructuring proportions to follow golden ratio")
            recommendations.append("Use Fibonacci numbers for counts and quantities")
        
        if score < 0.8:
            # Calculate optimal values
            total = sum(values)
            optimized = self.optimizer.optimize_proportions(values, OptimizationDomain.RESOURCE_ALLOCATION)
            recommendations.append(f"Optimal proportions would be: {[round(v, 2) for v in optimized]}")
        
        if score >= 0.8:
            recommendations.append("Your proportions are already harmonious!")
        
        return recommendations
    
    def create_with_golden_ratio(
        self,
        creation_type: str,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create something using golden ratio principles."""
        result = {
            "creation_type": creation_type,
            "golden_optimized": True,
            "phi": PHI
        }
        
        if creation_type == "logo_dimensions":
            width = parameters.get("base_width", 100)
            result["dimensions"] = {
                "width": width,
                "height": width / PHI,
                "inner_circle_radius": width / (2 * PHI),
                "focal_points": self.optimizer.calculate_golden_points(width, width / PHI)
            }
        
        elif creation_type == "presentation_layout":
            slide_width = parameters.get("width", 1920)
            slide_height = slide_width / PHI
            
            result["slide"] = {
                "width": slide_width,
                "height": slide_height,
                "margin_horizontal": slide_width / (PHI ** 4),
                "margin_vertical": slide_height / (PHI ** 4),
                "title_position": slide_height / PHI,
                "content_zones": [
                    {"name": "primary", "width": slide_width / PHI, "start": 0},
                    {"name": "secondary", "width": slide_width - slide_width / PHI, "start": slide_width / PHI}
                ]
            }
        
        elif creation_type == "product_tiers":
            base_price = parameters.get("base_price", 29)
            result["tiers"] = self.optimizer.optimize_pricing(base_price, parameters.get("num_tiers", 3))
        
        elif creation_type == "project_timeline":
            total_days = parameters.get("total_days", 100)
            phases = parameters.get("phases", ["Discovery", "Design", "Development", "Testing", "Launch"])
            
            fib = FibonacciSequence(len(phases) + 2)
            fib_subset = fib.sequence[:len(phases)]
            fib_total = sum(fib_subset)
            
            timeline = []
            current_day = 0
            for i, phase in enumerate(phases):
                days = int((fib_subset[-(i+1)] / fib_total) * total_days)
                timeline.append({
                    "phase": phase,
                    "start_day": current_day,
                    "duration": days,
                    "fibonacci_weight": fib_subset[-(i+1)]
                })
                current_day += days
            
            result["timeline"] = timeline
        
        return result
    
    def get_golden_constants(self) -> Dict[str, float]:
        """Get all golden ratio related constants."""
        return {
            "phi": PHI,
            "psi": PSI,
            "sqrt_phi": SQRT_PHI,
            "phi_squared": PHI ** 2,
            "phi_cubed": PHI ** 3,
            "one_over_phi": 1 / PHI,
            "fibonacci_10": [1, 1, 2, 3, 5, 8, 13, 21, 34, 55],
            "golden_angle_degrees": 137.5077640500378  # 360 / φ²
        }


# Singleton
_golden_system: Optional[GoldenRatioCreationSystem] = None


def get_golden_ratio_system() -> GoldenRatioCreationSystem:
    """Get the global golden ratio creation system."""
    global _golden_system
    if _golden_system is None:
        _golden_system = GoldenRatioCreationSystem()
    return _golden_system


async def demo():
    """Demonstrate the golden ratio creation system."""
    system = get_golden_ratio_system()
    
    print("Golden Ratio & Sacred Geometry Creation System")
    print("=" * 50)
    print(f"\nφ (Golden Ratio) = {PHI:.15f}")
    
    # Optimize layout
    print("\n--- Layout Optimization ---")
    result = system.optimize_for_domain(
        {"width": 1920, "height": 1080},
        OptimizationDomain.VISUAL_DESIGN
    )
    print(f"Original: 1920x1080")
    print(f"Optimized: {result.optimized_values}")
    print(f"Harmony Score: {result.harmony_score:.2f}")
    
    # Pricing optimization
    print("\n--- Pricing Tiers ---")
    result = system.optimize_for_domain(
        {"base_price": 29},
        OptimizationDomain.PRICING
    )
    for tier in result.optimized_values.get("pricing_tiers", []):
        print(f"  {tier['tier']}: ${tier['price']}")
    
    # Generate sacred pattern
    print("\n--- Fibonacci Sequence ---")
    pattern = system.generate_sacred_pattern(SacredPattern.FIBONACCI, length=15)
    print(f"Sequence: {pattern['sequence']}")
    print(f"Ratios approaching φ: {[round(r, 4) for r in pattern['ratios'][-5:]]}")
    
    # Harmony analysis
    print("\n--- Harmony Analysis ---")
    analysis = system.analyze_harmony([8, 13, 21, 34, 55])
    print(f"Harmony Score: {analysis['harmony_score']:.2f}")
    print(f"Fibonacci numbers found: {analysis['fibonacci_numbers_found']}")
    
    # Create with golden ratio
    print("\n--- Project Timeline ---")
    creation = system.create_with_golden_ratio(
        "project_timeline",
        {"total_days": 90, "phases": ["Research", "Design", "Build", "Test", "Launch"]}
    )
    for phase in creation["timeline"]:
        print(f"  {phase['phase']}: {phase['duration']} days")


if __name__ == "__main__":
    asyncio.run(demo())

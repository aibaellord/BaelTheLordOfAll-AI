"""
BAEL - Sacred Geometry & Golden Ratio Optimization Engine
Applies mathematical harmony principles to optimize AI outputs.

Revolutionary concepts:
1. Golden ratio (φ = 1.618...) for optimal proportions
2. Fibonacci sequence for natural progressions
3. Sacred geometry patterns for structure
4. Harmonic resonance in decision weights
5. Fractal scaling for recursive optimization
6. Divine proportion in resource allocation

These mathematical principles have proven success across:
- Visual design and UI (more appealing layouts)
- Business strategy (optimal resource allocation)
- Algorithm design (natural efficiency patterns)
- Content structure (optimal information flow)
- Decision weights (balanced considerations)
"""

import math
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("BAEL.GoldenOptimization")

# Sacred constants
PHI = (1 + math.sqrt(5)) / 2  # Golden ratio ≈ 1.618033988749895
PHI_INVERSE = 1 / PHI         # ≈ 0.618033988749895
FIBONACCI = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377, 610, 987]


class GeometricPattern(Enum):
    """Sacred geometry patterns."""
    GOLDEN_SPIRAL = "golden_spiral"
    FIBONACCI_SEQUENCE = "fibonacci"
    VESICA_PISCIS = "vesica_piscis"
    FLOWER_OF_LIFE = "flower_of_life"
    METATRONS_CUBE = "metatrons_cube"
    GOLDEN_RECTANGLE = "golden_rectangle"
    PENTAGRAM = "pentagram"
    TORUS = "torus"


class OptimizationDomain(Enum):
    """Domains where golden optimization applies."""
    VISUAL_DESIGN = "visual"
    CONTENT_STRUCTURE = "content"
    RESOURCE_ALLOCATION = "resource"
    DECISION_WEIGHTS = "decision"
    TIME_DISTRIBUTION = "time"
    PRIORITY_RANKING = "priority"
    TEAM_COMPOSITION = "team"
    ALGORITHM_DESIGN = "algorithm"


@dataclass
class GoldenProportions:
    """Proportions derived from golden ratio."""
    primary: float = PHI_INVERSE      # ~61.8%
    secondary: float = 1 - PHI_INVERSE # ~38.2%
    tertiary: float = PHI_INVERSE ** 2 # ~38.2%
    quaternary: float = PHI_INVERSE ** 3 # ~23.6%
    
    def get_split(self, total: float) -> Tuple[float, float]:
        """Split a value by golden ratio."""
        return (total * self.primary, total * self.secondary)
    
    def get_fibonacci_weights(self, n: int) -> List[float]:
        """Get n weights based on Fibonacci proportions."""
        if n <= 0:
            return []
        fibs = FIBONACCI[:n]
        total = sum(fibs)
        return [f / total for f in fibs]


@dataclass
class GoldenLayout:
    """Layout optimized with golden proportions."""
    total_width: float
    total_height: float
    
    # Derived golden sections
    primary_width: float = 0
    secondary_width: float = 0
    primary_height: float = 0
    secondary_height: float = 0
    
    # Grid points
    golden_points: List[Tuple[float, float]] = field(default_factory=list)
    
    def __post_init__(self):
        """Calculate golden proportions."""
        self.primary_width = self.total_width * PHI_INVERSE
        self.secondary_width = self.total_width - self.primary_width
        self.primary_height = self.total_height * PHI_INVERSE
        self.secondary_height = self.total_height - self.primary_height
        
        # Calculate key golden points
        self.golden_points = [
            (self.primary_width, self.primary_height),
            (self.secondary_width, self.primary_height),
            (self.primary_width, self.secondary_height),
            (self.secondary_width, self.secondary_height)
        ]


@dataclass
class GoldenDecision:
    """Decision weights optimized with golden ratio."""
    factors: List[str]
    weights: List[float] = field(default_factory=list)
    
    def __post_init__(self):
        """Calculate golden weights for factors."""
        n = len(self.factors)
        if n == 0:
            return
        
        # Use Fibonacci-based weights (most important first)
        fib_weights = []
        for i in range(n):
            fib_idx = min(i, len(FIBONACCI) - 1)
            fib_weights.append(FIBONACCI[len(FIBONACCI) - 1 - fib_idx])
        
        total = sum(fib_weights)
        self.weights = [w / total for w in fib_weights]


class GoldenOptimizationEngine:
    """
    Applies sacred geometry and golden ratio principles to optimize outputs.
    
    Scientific basis:
    - Golden ratio appears throughout nature (shells, plants, galaxies)
    - Human perception finds golden proportions aesthetically pleasing
    - Fibonacci sequences model natural growth patterns
    - These ratios have been used in art, architecture, and design for millennia
    
    Applications in AI:
    - Optimal content structure and flow
    - Balanced decision-making weights
    - Harmonious resource allocation
    - Natural information hierarchies
    - Aesthetic UI/UX recommendations
    """
    
    def __init__(self):
        self.proportions = GoldenProportions()
        
        # Domain-specific optimization strategies
        self._strategies = {
            OptimizationDomain.VISUAL_DESIGN: self._optimize_visual,
            OptimizationDomain.CONTENT_STRUCTURE: self._optimize_content,
            OptimizationDomain.RESOURCE_ALLOCATION: self._optimize_resources,
            OptimizationDomain.DECISION_WEIGHTS: self._optimize_decision,
            OptimizationDomain.TIME_DISTRIBUTION: self._optimize_time,
            OptimizationDomain.PRIORITY_RANKING: self._optimize_priority,
            OptimizationDomain.TEAM_COMPOSITION: self._optimize_team,
            OptimizationDomain.ALGORITHM_DESIGN: self._optimize_algorithm
        }
        
        logger.info("GoldenOptimizationEngine initialized with φ = {:.10f}".format(PHI))
    
    def optimize(
        self,
        domain: OptimizationDomain,
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Apply golden optimization to input data for the given domain.
        """
        if domain in self._strategies:
            return self._strategies[domain](input_data)
        return input_data
    
    def get_golden_split(self, total: float) -> Tuple[float, float]:
        """Split any value by golden ratio."""
        return self.proportions.get_split(total)
    
    def get_fibonacci_distribution(self, total: float, parts: int) -> List[float]:
        """Distribute a total across parts using Fibonacci proportions."""
        weights = self.proportions.get_fibonacci_weights(parts)
        return [total * w for w in weights]
    
    def create_golden_layout(self, width: float, height: float) -> GoldenLayout:
        """Create a layout based on golden proportions."""
        return GoldenLayout(total_width=width, total_height=height)
    
    def get_optimal_hierarchy(self, items: List[str]) -> List[Tuple[str, float]]:
        """
        Create optimal hierarchy using Fibonacci weights.
        First item gets highest weight, decreasing by golden ratio.
        """
        n = len(items)
        if n == 0:
            return []
        
        weights = []
        current_weight = 1.0
        for _ in range(n):
            weights.append(current_weight)
            current_weight *= PHI_INVERSE
        
        # Normalize
        total = sum(weights)
        weights = [w / total for w in weights]
        
        return list(zip(items, weights))
    
    def optimize_content_structure(self, sections: List[str]) -> Dict[str, Any]:
        """
        Optimize content structure using golden ratio.
        Returns recommended proportions for each section.
        """
        n = len(sections)
        if n == 0:
            return {}
        
        # Golden spiral structure: each section is φ times smaller than previous
        proportions = []
        current = 100.0
        for _ in range(n):
            proportions.append(current)
            current *= PHI_INVERSE
        
        # Normalize to 100%
        total = sum(proportions)
        proportions = [p / total * 100 for p in proportions]
        
        return {
            "sections": [
                {
                    "name": section,
                    "recommended_proportion": f"{prop:.1f}%",
                    "focus_level": "primary" if i == 0 else "secondary" if i == 1 else "tertiary"
                }
                for i, (section, prop) in enumerate(zip(sections, proportions))
            ],
            "golden_ratio_applied": True,
            "primary_focus_percentage": f"{proportions[0]:.1f}%",
            "optimal_reading_flow": "Start with most important (largest), flow to details"
        }
    
    def optimize_decision_weights(
        self,
        factors: List[str],
        importance_order: bool = True
    ) -> Dict[str, float]:
        """
        Optimize decision weights using golden ratio.
        Assumes factors are listed in order of importance if importance_order=True.
        """
        decision = GoldenDecision(factors=factors)
        return dict(zip(factors, decision.weights))
    
    def optimize_time_allocation(
        self,
        tasks: List[str],
        total_time: float
    ) -> List[Dict[str, Any]]:
        """
        Allocate time across tasks using golden proportions.
        """
        n = len(tasks)
        if n == 0:
            return []
        
        # Use Fibonacci distribution
        allocations = self.get_fibonacci_distribution(total_time, n)
        
        return [
            {
                "task": task,
                "allocated_time": alloc,
                "percentage": f"{(alloc / total_time) * 100:.1f}%"
            }
            for task, alloc in zip(tasks, allocations)
        ]
    
    def optimize_team_composition(
        self,
        roles: List[str],
        total_members: int
    ) -> Dict[str, int]:
        """
        Optimize team composition using Fibonacci ratios.
        """
        if not roles or total_members <= 0:
            return {}
        
        n = len(roles)
        
        # Get Fibonacci distribution
        fib_values = FIBONACCI[:n]
        total_fib = sum(fib_values)
        
        # Allocate members proportionally
        allocations = {}
        remaining = total_members
        
        for i, role in enumerate(roles):
            if i == n - 1:
                # Last role gets remaining
                allocations[role] = max(1, remaining)
            else:
                alloc = max(1, round(total_members * fib_values[n - 1 - i] / total_fib))
                allocations[role] = alloc
                remaining -= alloc
        
        return allocations
    
    def get_golden_spiral_points(
        self,
        center: Tuple[float, float],
        start_radius: float,
        num_points: int
    ) -> List[Tuple[float, float]]:
        """
        Generate points along a golden spiral.
        Useful for layouts, animations, or data visualization.
        """
        points = []
        
        for i in range(num_points):
            # Angle increases by golden angle (137.5 degrees)
            golden_angle = math.pi * (3 - math.sqrt(5))  # ~137.5 degrees in radians
            angle = i * golden_angle
            
            # Radius grows by golden ratio
            radius = start_radius * (PHI ** (i / 4))
            
            x = center[0] + radius * math.cos(angle)
            y = center[1] + radius * math.sin(angle)
            
            points.append((x, y))
        
        return points
    
    def optimize_api_response_structure(
        self,
        data_fields: List[str]
    ) -> Dict[str, Any]:
        """
        Structure API response for optimal information flow.
        """
        n = len(data_fields)
        if n == 0:
            return {}
        
        # Categorize by golden ratio levels
        primary_count = max(1, int(n * PHI_INVERSE))
        secondary_count = max(1, int((n - primary_count) * PHI_INVERSE))
        tertiary_count = n - primary_count - secondary_count
        
        return {
            "recommended_structure": {
                "primary_fields": data_fields[:primary_count],
                "secondary_fields": data_fields[primary_count:primary_count + secondary_count],
                "tertiary_fields": data_fields[primary_count + secondary_count:],
            },
            "display_priority": {
                field: "essential" if i < primary_count
                else "important" if i < primary_count + secondary_count
                else "supplementary"
                for i, field in enumerate(data_fields)
            },
            "golden_ratio_applied": True
        }
    
    def create_success_formula(
        self,
        success_factors: List[str]
    ) -> Dict[str, Any]:
        """
        Create a success formula with golden-optimized factor weights.
        Useful for business, projects, or any multi-factor success metric.
        """
        weights = self.optimize_decision_weights(success_factors)
        
        formula_parts = [
            f"({w:.3f} × {factor})"
            for factor, w in weights.items()
        ]
        
        return {
            "formula": " + ".join(formula_parts),
            "weights": weights,
            "interpretation": {
                "primary_factor": success_factors[0] if success_factors else None,
                "primary_weight": f"{list(weights.values())[0] * 100:.1f}%" if weights else "0%",
                "philosophy": "Focus most energy on primary factor, with diminishing attention to others following natural proportions"
            },
            "mathematical_basis": f"Golden Ratio (φ = {PHI:.6f})"
        }
    
    # Domain-specific optimization methods
    
    def _optimize_visual(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize visual design elements."""
        width = input_data.get("width", 1920)
        height = input_data.get("height", 1080)
        
        layout = self.create_golden_layout(width, height)
        
        return {
            **input_data,
            "golden_layout": {
                "primary_section": {
                    "width": layout.primary_width,
                    "height": layout.primary_height
                },
                "secondary_section": {
                    "width": layout.secondary_width,
                    "height": layout.secondary_height
                },
                "focal_points": layout.golden_points
            },
            "optimization_applied": "golden_ratio_visual"
        }
    
    def _optimize_content(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize content structure."""
        sections = input_data.get("sections", [])
        return {
            **input_data,
            **self.optimize_content_structure(sections)
        }
    
    def _optimize_resources(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize resource allocation."""
        resources = input_data.get("resources", [])
        total = input_data.get("total", 100)
        
        distribution = self.get_fibonacci_distribution(total, len(resources))
        
        return {
            **input_data,
            "allocation": dict(zip(resources, distribution)),
            "optimization_applied": "fibonacci_distribution"
        }
    
    def _optimize_decision(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize decision weights."""
        factors = input_data.get("factors", [])
        return {
            **input_data,
            "weights": self.optimize_decision_weights(factors),
            "optimization_applied": "golden_decision_weights"
        }
    
    def _optimize_time(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize time distribution."""
        tasks = input_data.get("tasks", [])
        total = input_data.get("total_time", 100)
        
        return {
            **input_data,
            "time_allocation": self.optimize_time_allocation(tasks, total)
        }
    
    def _optimize_priority(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize priority ranking."""
        items = input_data.get("items", [])
        
        return {
            **input_data,
            "prioritized_items": self.get_optimal_hierarchy(items)
        }
    
    def _optimize_team(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize team composition."""
        roles = input_data.get("roles", [])
        total_members = input_data.get("total_members", 10)
        
        return {
            **input_data,
            "team_composition": self.optimize_team_composition(roles, total_members)
        }
    
    def _optimize_algorithm(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize algorithm design parameters."""
        parameters = input_data.get("parameters", [])
        
        # Apply golden ratio to parameter weights
        hierarchy = self.get_optimal_hierarchy(parameters)
        
        return {
            **input_data,
            "parameter_importance": dict(hierarchy),
            "optimization_principle": "Parameters weighted by golden ratio for natural balance"
        }


# Global instance
_golden_engine: Optional[GoldenOptimizationEngine] = None


def get_golden_engine() -> GoldenOptimizationEngine:
    """Get the global golden optimization engine."""
    global _golden_engine
    if _golden_engine is None:
        _golden_engine = GoldenOptimizationEngine()
    return _golden_engine


def demo():
    """Demonstrate golden optimization."""
    engine = get_golden_engine()
    
    print("=== Golden Ratio Optimization Demo ===\n")
    print(f"φ (Golden Ratio) = {PHI:.10f}")
    print(f"1/φ = {PHI_INVERSE:.10f}\n")
    
    # Content structure
    sections = ["Introduction", "Core Concepts", "Implementation", "Examples", "Conclusion"]
    structure = engine.optimize_content_structure(sections)
    print("Content Structure Optimization:")
    for s in structure["sections"]:
        print(f"  {s['name']}: {s['recommended_proportion']} ({s['focus_level']})")
    
    # Decision weights
    print("\nDecision Weights Optimization:")
    factors = ["Quality", "Speed", "Cost", "Innovation", "Risk"]
    weights = engine.optimize_decision_weights(factors)
    for factor, weight in weights.items():
        print(f"  {factor}: {weight:.3f} ({weight*100:.1f}%)")
    
    # Success formula
    print("\nSuccess Formula:")
    formula = engine.create_success_formula(["Execution", "Strategy", "Team", "Timing"])
    print(f"  {formula['formula']}")
    
    print("\n=== Golden Ratio brings natural harmony to optimization ===")


if __name__ == "__main__":
    demo()

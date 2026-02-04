"""
BAEL - Telekinetic Force Engine
================================

MOVE. LIFT. CRUSH. DOMINATE.

Control over the physical world through pure will:
- Object manipulation
- Force projection
- Levitation systems
- Kinetic shields
- Matter displacement
- Psychokinetic amplification
- Destructive force channels
- Precision control
- Mass manipulation
- Environmental domination

"The physical world bends to Ba'el's will."
"""

import asyncio
import hashlib
import logging
import math
import random
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("BAEL.TELEKINETIC")


class ForceType(Enum):
    """Types of telekinetic force."""
    PUSH = "push"  # Push objects away
    PULL = "pull"  # Pull objects toward
    LIFT = "lift"  # Lift against gravity
    CRUSH = "crush"  # Apply crushing pressure
    THROW = "throw"  # Propel objects
    HOLD = "hold"  # Hold in place
    SPIN = "spin"  # Rotate objects
    SHATTER = "shatter"  # Break apart
    COMPRESS = "compress"  # Compress matter
    EXPAND = "expand"  # Expand/stretch matter


class PrecisionLevel(Enum):
    """Precision levels for manipulation."""
    MOLECULAR = "molecular"  # Individual molecule control
    MICROSCOPIC = "microscopic"  # Microscopic precision
    FINE = "fine"  # Fine motor control
    STANDARD = "standard"  # Normal precision
    COARSE = "coarse"  # Large-scale movements
    MASSIVE = "massive"  # Building/mountain scale


class ShieldType(Enum):
    """Types of kinetic shields."""
    BARRIER = "barrier"  # Solid wall
    BUBBLE = "bubble"  # Spherical shield
    DEFLECTOR = "deflector"  # Deflects projectiles
    ABSORBER = "absorber"  # Absorbs energy
    REFLECTOR = "reflector"  # Reflects attacks back


class AmplificationMethod(Enum):
    """Methods to amplify telekinetic power."""
    NEURAL_BOOST = "neural_boost"
    QUANTUM_ENTANGLE = "quantum_entangle"
    PSIONIC_CRYSTAL = "psionic_crystal"
    GROUP_FOCUS = "group_focus"
    RAGE_CHANNEL = "rage_channel"
    MEDITATION_FOCUS = "meditation_focus"


class ManipulationTarget(Enum):
    """Target types for manipulation."""
    SOLID = "solid"
    LIQUID = "liquid"
    GAS = "gas"
    PLASMA = "plasma"
    ENERGY = "energy"
    BIOLOGICAL = "biological"


@dataclass
class TelekineticUser:
    """A user of telekinetic abilities."""
    id: str
    name: str
    power_level: float  # Base power level
    amplified_power: float  # Current amplified power
    precision: PrecisionLevel
    range_meters: float
    max_mass_kg: float
    active_objects: int
    amplifiers: List[AmplificationMethod]
    total_energy_expended: float


@dataclass
class ManipulatedObject:
    """An object being manipulated."""
    id: str
    name: str
    mass_kg: float
    position: Tuple[float, float, float]
    velocity: Tuple[float, float, float]
    rotation_rpm: float
    force_applied_n: float
    controller_id: str
    stable: bool


@dataclass
class KineticShield:
    """A telekinetic shield."""
    id: str
    shield_type: ShieldType
    center: Tuple[float, float, float]
    radius_m: float
    strength: float  # Force it can withstand
    active: bool
    energy_drain_rate: float
    controller_id: str


@dataclass
class ForceProjection:
    """A projected force."""
    id: str
    force_type: ForceType
    origin: Tuple[float, float, float]
    direction: Tuple[float, float, float]
    magnitude_n: float
    range_m: float
    active: bool


@dataclass
class PsychicAmplifier:
    """A device to amplify psychic power."""
    id: str
    method: AmplificationMethod
    amplification_factor: float
    user_id: str
    active: bool
    energy_source: str


class TelekineticForceEngine:
    """
    The telekinetic force engine.

    Provides complete control over the physical world:
    - Object manipulation and movement
    - Force projection and shields
    - Matter manipulation
    - Environmental control
    """

    def __init__(self):
        self.users: Dict[str, TelekineticUser] = {}
        self.objects: Dict[str, ManipulatedObject] = {}
        self.shields: Dict[str, KineticShield] = {}
        self.projections: Dict[str, ForceProjection] = {}
        self.amplifiers: Dict[str, PsychicAmplifier] = {}

        self.total_force_applied = 0.0
        self.objects_moved = 0
        self.shields_created = 0

        logger.info("TelekineticForceEngine initialized - WILL BECOMES FORCE")

    def _gen_id(self, prefix: str) -> str:
        """Generate unique ID."""
        return hashlib.md5(f"{prefix}{time.time()}{random.random()}".encode()).hexdigest()[:12]

    def _calculate_distance(
        self,
        pos1: Tuple[float, float, float],
        pos2: Tuple[float, float, float]
    ) -> float:
        """Calculate distance between two points."""
        return math.sqrt(sum((a - b) ** 2 for a, b in zip(pos1, pos2)))

    # =========================================================================
    # USER MANAGEMENT
    # =========================================================================

    async def register_user(
        self,
        name: str,
        power_level: float = 100.0
    ) -> TelekineticUser:
        """Register a telekinetic user."""
        user = TelekineticUser(
            id=self._gen_id("user"),
            name=name,
            power_level=power_level,
            amplified_power=power_level,
            precision=PrecisionLevel.STANDARD,
            range_meters=50.0,
            max_mass_kg=1000.0,
            active_objects=0,
            amplifiers=[],
            total_energy_expended=0.0
        )

        self.users[user.id] = user

        logger.info(f"Telekinetic user registered: {name}")

        return user

    async def amplify_power(
        self,
        user_id: str,
        method: AmplificationMethod
    ) -> Dict[str, Any]:
        """Amplify a user's telekinetic power."""
        user = self.users.get(user_id)
        if not user:
            return {"error": "User not found"}

        amplification_factors = {
            AmplificationMethod.NEURAL_BOOST: 2.0,
            AmplificationMethod.QUANTUM_ENTANGLE: 5.0,
            AmplificationMethod.PSIONIC_CRYSTAL: 10.0,
            AmplificationMethod.GROUP_FOCUS: 3.0,
            AmplificationMethod.RAGE_CHANNEL: 20.0,
            AmplificationMethod.MEDITATION_FOCUS: 4.0
        }

        factor = amplification_factors.get(method, 1.0)

        # Create amplifier
        amplifier = PsychicAmplifier(
            id=self._gen_id("amp"),
            method=method,
            amplification_factor=factor,
            user_id=user_id,
            active=True,
            energy_source="psychic_reservoir"
        )

        self.amplifiers[amplifier.id] = amplifier
        user.amplifiers.append(method)

        # Recalculate amplified power
        total_factor = 1.0
        for m in user.amplifiers:
            total_factor *= amplification_factors.get(m, 1.0)

        user.amplified_power = user.power_level * total_factor
        user.max_mass_kg *= factor
        user.range_meters *= factor

        return {
            "success": True,
            "user": user.name,
            "method": method.value,
            "amplification_factor": factor,
            "new_power_level": user.amplified_power,
            "new_max_mass_kg": user.max_mass_kg,
            "new_range_m": user.range_meters
        }

    async def set_precision(
        self,
        user_id: str,
        precision: PrecisionLevel
    ) -> Dict[str, Any]:
        """Set user's precision level."""
        user = self.users.get(user_id)
        if not user:
            return {"error": "User not found"}

        user.precision = precision

        precision_effects = {
            PrecisionLevel.MOLECULAR: {"max_objects": 1000000, "control": "atomic"},
            PrecisionLevel.MICROSCOPIC: {"max_objects": 10000, "control": "cellular"},
            PrecisionLevel.FINE: {"max_objects": 100, "control": "millimeter"},
            PrecisionLevel.STANDARD: {"max_objects": 10, "control": "centimeter"},
            PrecisionLevel.COARSE: {"max_objects": 5, "control": "meter"},
            PrecisionLevel.MASSIVE: {"max_objects": 1, "control": "building"}
        }

        return {
            "success": True,
            "user": user.name,
            "precision": precision.value,
            "effects": precision_effects.get(precision, {})
        }

    # =========================================================================
    # OBJECT MANIPULATION
    # =========================================================================

    async def grab_object(
        self,
        user_id: str,
        object_name: str,
        mass_kg: float,
        position: Tuple[float, float, float]
    ) -> ManipulatedObject:
        """Telekinetically grab an object."""
        user = self.users.get(user_id)
        if not user:
            return None

        if mass_kg > user.max_mass_kg:
            logger.warning(f"Object too heavy: {mass_kg}kg > {user.max_mass_kg}kg")
            return None

        obj = ManipulatedObject(
            id=self._gen_id("obj"),
            name=object_name,
            mass_kg=mass_kg,
            position=position,
            velocity=(0, 0, 0),
            rotation_rpm=0,
            force_applied_n=mass_kg * 9.81,  # Counter gravity
            controller_id=user_id,
            stable=True
        )

        user.active_objects += 1
        self.objects[obj.id] = obj
        self.objects_moved += 1

        logger.info(f"Object grabbed: {object_name} ({mass_kg}kg)")

        return obj

    async def move_object(
        self,
        object_id: str,
        new_position: Tuple[float, float, float],
        speed_mps: float = 10.0
    ) -> Dict[str, Any]:
        """Move a grabbed object to new position."""
        obj = self.objects.get(object_id)
        if not obj:
            return {"error": "Object not found"}

        # Calculate direction and force
        dx = new_position[0] - obj.position[0]
        dy = new_position[1] - obj.position[1]
        dz = new_position[2] - obj.position[2]

        distance = math.sqrt(dx**2 + dy**2 + dz**2)

        if distance > 0:
            # Calculate required force
            force = obj.mass_kg * (speed_mps ** 2) / (2 * distance)
            obj.force_applied_n = force

            # Calculate velocity
            obj.velocity = (
                speed_mps * dx / distance,
                speed_mps * dy / distance,
                speed_mps * dz / distance
            )

        obj.position = new_position
        self.total_force_applied += obj.force_applied_n

        return {
            "success": True,
            "object": obj.name,
            "new_position": new_position,
            "force_applied_n": obj.force_applied_n,
            "speed_mps": speed_mps
        }

    async def throw_object(
        self,
        object_id: str,
        direction: Tuple[float, float, float],
        velocity_mps: float
    ) -> Dict[str, Any]:
        """Throw an object in a direction."""
        obj = self.objects.get(object_id)
        if not obj:
            return {"error": "Object not found"}

        user = self.users.get(obj.controller_id)

        # Normalize direction
        magnitude = math.sqrt(sum(d**2 for d in direction))
        if magnitude == 0:
            return {"error": "Invalid direction"}

        normalized = tuple(d / magnitude for d in direction)

        # Set velocity
        obj.velocity = tuple(d * velocity_mps for d in normalized)

        # Calculate kinetic energy
        kinetic_energy = 0.5 * obj.mass_kg * (velocity_mps ** 2)

        # Release object
        user.active_objects -= 1
        del self.objects[object_id]

        return {
            "success": True,
            "object": obj.name,
            "velocity_mps": velocity_mps,
            "direction": normalized,
            "kinetic_energy_j": kinetic_energy,
            "momentum_kgmps": obj.mass_kg * velocity_mps
        }

    async def crush_object(
        self,
        user_id: str,
        object_name: str,
        mass_kg: float,
        crushing_pressure_pa: float = 1e8  # 100 MPa
    ) -> Dict[str, Any]:
        """Crush an object with telekinetic force."""
        user = self.users.get(user_id)
        if not user:
            return {"error": "User not found"}

        # Calculate force based on pressure
        # Assume spherical object
        radius = (3 * mass_kg / (4 * math.pi * 1000)) ** (1/3)  # Assume density 1000 kg/m3
        surface_area = 4 * math.pi * radius ** 2

        force = crushing_pressure_pa * surface_area

        self.total_force_applied += force

        return {
            "success": True,
            "object": object_name,
            "crushing_pressure_pa": crushing_pressure_pa,
            "force_applied_n": force,
            "energy_expended_j": force * radius,
            "result": "crushed"
        }

    async def levitate(
        self,
        user_id: str,
        object_name: str,
        mass_kg: float,
        height_m: float
    ) -> ManipulatedObject:
        """Levitate an object to a height."""
        user = self.users.get(user_id)
        if not user:
            return None

        obj = await self.grab_object(
            user_id,
            object_name,
            mass_kg,
            (0, height_m, 0)
        )

        if obj:
            # Calculate energy to maintain levitation
            gravitational_potential = mass_kg * 9.81 * height_m
            obj.force_applied_n = mass_kg * 9.81  # Continuous force against gravity

            logger.info(f"Levitating {object_name} at {height_m}m")

        return obj

    async def spin_object(
        self,
        object_id: str,
        rpm: float
    ) -> Dict[str, Any]:
        """Spin an object."""
        obj = self.objects.get(object_id)
        if not obj:
            return {"error": "Object not found"}

        obj.rotation_rpm = rpm

        # Calculate angular velocity and energy
        omega = rpm * 2 * math.pi / 60  # rad/s
        # Assume sphere moment of inertia I = 2/5 * m * r^2
        radius = (3 * obj.mass_kg / (4 * math.pi * 1000)) ** (1/3)
        moment_of_inertia = 0.4 * obj.mass_kg * radius ** 2
        rotational_energy = 0.5 * moment_of_inertia * omega ** 2

        return {
            "success": True,
            "object": obj.name,
            "rpm": rpm,
            "angular_velocity_rads": omega,
            "rotational_energy_j": rotational_energy
        }

    # =========================================================================
    # FORCE PROJECTION
    # =========================================================================

    async def project_force(
        self,
        user_id: str,
        force_type: ForceType,
        direction: Tuple[float, float, float],
        magnitude_n: float,
        range_m: float = 50.0
    ) -> ForceProjection:
        """Project a telekinetic force."""
        user = self.users.get(user_id)
        if not user:
            return None

        # Scale force by user power
        actual_magnitude = magnitude_n * (user.amplified_power / 100)
        actual_range = min(range_m, user.range_meters)

        projection = ForceProjection(
            id=self._gen_id("force"),
            force_type=force_type,
            origin=(0, 0, 0),  # User's position
            direction=direction,
            magnitude_n=actual_magnitude,
            range_m=actual_range,
            active=True
        )

        self.projections[projection.id] = projection
        self.total_force_applied += actual_magnitude

        logger.info(f"Force projected: {force_type.value} at {actual_magnitude}N")

        return projection

    async def force_push(
        self,
        user_id: str,
        direction: Tuple[float, float, float],
        intensity: float = 1.0
    ) -> Dict[str, Any]:
        """Create a force push."""
        base_force = 10000 * intensity  # 10kN base

        projection = await self.project_force(
            user_id,
            ForceType.PUSH,
            direction,
            base_force
        )

        if projection:
            return {
                "success": True,
                "force_type": "push",
                "magnitude_n": projection.magnitude_n,
                "range_m": projection.range_m,
                "effects": ["knockback", "displacement", "stagger"]
            }
        return {"error": "Force projection failed"}

    async def force_pull(
        self,
        user_id: str,
        target_position: Tuple[float, float, float],
        intensity: float = 1.0
    ) -> Dict[str, Any]:
        """Create a force pull."""
        # Direction toward user
        direction = tuple(-x for x in target_position)
        base_force = 10000 * intensity

        projection = await self.project_force(
            user_id,
            ForceType.PULL,
            direction,
            base_force
        )

        if projection:
            return {
                "success": True,
                "force_type": "pull",
                "magnitude_n": projection.magnitude_n,
                "effects": ["attract", "displace", "yank"]
            }
        return {"error": "Force projection failed"}

    async def shockwave(
        self,
        user_id: str,
        radius_m: float = 20.0,
        intensity: float = 1.0
    ) -> Dict[str, Any]:
        """Create an omnidirectional shockwave."""
        user = self.users.get(user_id)
        if not user:
            return {"error": "User not found"}

        base_force = 50000 * intensity  # 50kN base
        actual_force = base_force * (user.amplified_power / 100)

        # Create projections in all directions
        projections = []
        for angle in range(0, 360, 30):
            radian = math.radians(angle)
            direction = (math.cos(radian), 0, math.sin(radian))

            proj = await self.project_force(
                user_id,
                ForceType.PUSH,
                direction,
                actual_force,
                radius_m
            )
            projections.append(proj.id)

        return {
            "success": True,
            "type": "shockwave",
            "radius_m": radius_m,
            "force_per_direction_n": actual_force,
            "projections": len(projections),
            "effects": ["area_knockback", "destruction", "displacement"]
        }

    # =========================================================================
    # KINETIC SHIELDS
    # =========================================================================

    async def create_shield(
        self,
        user_id: str,
        shield_type: ShieldType,
        radius_m: float = 3.0,
        strength: float = 1e6  # Force it can withstand
    ) -> KineticShield:
        """Create a kinetic shield."""
        user = self.users.get(user_id)
        if not user:
            return None

        actual_strength = strength * (user.amplified_power / 100)

        shield = KineticShield(
            id=self._gen_id("shield"),
            shield_type=shield_type,
            center=(0, 0, 0),
            radius_m=radius_m,
            strength=actual_strength,
            active=True,
            energy_drain_rate=actual_strength / 1000,  # J/s
            controller_id=user_id
        )

        self.shields[shield.id] = shield
        self.shields_created += 1

        logger.info(f"Shield created: {shield_type.value}")

        return shield

    async def barrier_wall(
        self,
        user_id: str,
        width_m: float = 5.0,
        height_m: float = 3.0
    ) -> KineticShield:
        """Create a barrier wall."""
        # Area-based strength calculation
        area = width_m * height_m
        strength = 1e7 * area  # 10 MPa

        shield = await self.create_shield(
            user_id,
            ShieldType.BARRIER,
            radius_m=max(width_m, height_m) / 2,
            strength=strength
        )

        return shield

    async def bubble_shield(
        self,
        user_id: str,
        radius_m: float = 5.0
    ) -> KineticShield:
        """Create a protective bubble."""
        surface_area = 4 * math.pi * radius_m ** 2
        strength = 1e6 * surface_area

        shield = await self.create_shield(
            user_id,
            ShieldType.BUBBLE,
            radius_m=radius_m,
            strength=strength
        )

        return shield

    async def deflect_projectile(
        self,
        shield_id: str,
        projectile_mass_kg: float,
        projectile_velocity_mps: float
    ) -> Dict[str, Any]:
        """Deflect an incoming projectile."""
        shield = self.shields.get(shield_id)
        if not shield or not shield.active:
            return {"error": "No active shield"}

        # Calculate impact force
        # F = m * v / t (assume 0.01s impact time)
        impact_force = projectile_mass_kg * projectile_velocity_mps / 0.01
        kinetic_energy = 0.5 * projectile_mass_kg * projectile_velocity_mps ** 2

        if impact_force > shield.strength:
            shield.active = False
            return {
                "success": False,
                "result": "shield_broken",
                "impact_force_n": impact_force,
                "shield_strength_n": shield.strength
            }

        # Reduce shield strength
        shield.strength -= impact_force

        return {
            "success": True,
            "result": "deflected",
            "projectile_mass_kg": projectile_mass_kg,
            "projectile_velocity_mps": projectile_velocity_mps,
            "impact_force_n": impact_force,
            "remaining_strength_n": shield.strength
        }

    # =========================================================================
    # MASS MANIPULATION
    # =========================================================================

    async def manipulate_multiple_objects(
        self,
        user_id: str,
        objects: List[Dict[str, Any]]  # [{name, mass_kg, position}]
    ) -> Dict[str, Any]:
        """Manipulate multiple objects simultaneously."""
        user = self.users.get(user_id)
        if not user:
            return {"error": "User not found"}

        grabbed = []
        total_mass = 0

        for obj_data in objects:
            if total_mass + obj_data["mass_kg"] > user.max_mass_kg:
                break

            obj = await self.grab_object(
                user_id,
                obj_data["name"],
                obj_data["mass_kg"],
                obj_data["position"]
            )

            if obj:
                grabbed.append(obj.id)
                total_mass += obj_data["mass_kg"]

        return {
            "success": True,
            "objects_grabbed": len(grabbed),
            "total_mass_kg": total_mass,
            "remaining_capacity_kg": user.max_mass_kg - total_mass,
            "object_ids": grabbed
        }

    async def orbital_manipulation(
        self,
        user_id: str,
        object_ids: List[str],
        orbit_radius_m: float = 5.0,
        orbital_velocity_mps: float = 10.0
    ) -> Dict[str, Any]:
        """Make objects orbit around a point."""
        user = self.users.get(user_id)
        if not user:
            return {"error": "User not found"}

        results = []

        for i, obj_id in enumerate(object_ids):
            obj = self.objects.get(obj_id)
            if not obj:
                continue

            # Calculate orbital position
            angle = (2 * math.pi * i) / len(object_ids)

            new_position = (
                orbit_radius_m * math.cos(angle),
                obj.position[1],  # Maintain height
                orbit_radius_m * math.sin(angle)
            )

            # Set orbital velocity (perpendicular to radius)
            obj.velocity = (
                -orbital_velocity_mps * math.sin(angle),
                0,
                orbital_velocity_mps * math.cos(angle)
            )

            obj.position = new_position
            results.append({
                "id": obj_id,
                "name": obj.name,
                "position": new_position,
                "orbital_velocity": obj.velocity
            })

        return {
            "success": True,
            "orbiting_objects": len(results),
            "orbit_radius_m": orbit_radius_m,
            "orbital_velocity_mps": orbital_velocity_mps,
            "objects": results
        }

    # =========================================================================
    # ENVIRONMENTAL CONTROL
    # =========================================================================

    async def create_vortex(
        self,
        user_id: str,
        center: Tuple[float, float, float],
        radius_m: float = 10.0,
        rotational_speed_mps: float = 50.0
    ) -> Dict[str, Any]:
        """Create a telekinetic vortex."""
        user = self.users.get(user_id)
        if not user:
            return {"error": "User not found"}

        # Calculate vortex power
        # Power = 0.5 * ρ * v^3 * A (wind power formula)
        air_density = 1.225  # kg/m3
        cross_section = math.pi * radius_m ** 2
        power = 0.5 * air_density * (rotational_speed_mps ** 3) * cross_section

        # Enhanced by user power
        power *= (user.amplified_power / 100)

        return {
            "success": True,
            "type": "vortex",
            "center": center,
            "radius_m": radius_m,
            "rotational_speed_mps": rotational_speed_mps,
            "power_watts": power,
            "effects": [
                "suction",
                "debris_pickup",
                "environmental_destruction",
                "target_displacement"
            ]
        }

    async def seismic_slam(
        self,
        user_id: str,
        epicenter: Tuple[float, float, float],
        magnitude: float = 5.0
    ) -> Dict[str, Any]:
        """Create a seismic slam effect."""
        user = self.users.get(user_id)
        if not user:
            return {"error": "User not found"}

        # Calculate energy (like earthquake)
        # log10(E) = 1.5*M + 4.8 (in joules, simplified)
        energy_j = 10 ** (1.5 * magnitude + 4.8)

        # Affected radius
        radius_m = 10 ** (0.5 * magnitude)

        self.total_force_applied += energy_j

        return {
            "success": True,
            "type": "seismic_slam",
            "epicenter": epicenter,
            "magnitude": magnitude,
            "energy_released_j": energy_j,
            "affected_radius_m": radius_m,
            "effects": [
                "ground_rupture",
                "shockwave",
                "knockdown",
                "structural_damage"
            ]
        }

    # =========================================================================
    # GODMODE ABILITIES
    # =========================================================================

    async def molecular_disassembly(
        self,
        user_id: str,
        target_name: str,
        mass_kg: float
    ) -> Dict[str, Any]:
        """Disassemble matter at molecular level."""
        user = self.users.get(user_id)
        if not user or user.precision != PrecisionLevel.MOLECULAR:
            return {"error": "Requires molecular precision"}

        # Calculate atomic content
        avg_atomic_mass = 12  # Carbon baseline
        atoms = mass_kg * 6.022e23 / (avg_atomic_mass / 1000)

        # Energy to disassemble (breaking atomic bonds)
        bond_energy_j = atoms * 5e-19  # Approximate C-C bond

        return {
            "success": True,
            "target": target_name,
            "mass_disassembled_kg": mass_kg,
            "atoms_separated": atoms,
            "energy_used_j": bond_energy_j,
            "result": "complete_disintegration"
        }

    async def matter_compression(
        self,
        user_id: str,
        target_name: str,
        mass_kg: float,
        compression_factor: float = 1000
    ) -> Dict[str, Any]:
        """Compress matter to extreme densities."""
        user = self.users.get(user_id)
        if not user:
            return {"error": "User not found"}

        # Original volume (assume water density)
        original_volume_m3 = mass_kg / 1000

        # Compressed volume
        compressed_volume = original_volume_m3 / compression_factor

        # New density
        new_density = mass_kg / compressed_volume

        # Pressure required (rough estimate)
        pressure_pa = 1e9 * math.log10(compression_factor)  # GPa scale

        # Force over surface
        radius = (3 * compressed_volume / (4 * math.pi)) ** (1/3)
        surface_area = 4 * math.pi * radius ** 2
        force_n = pressure_pa * surface_area

        self.total_force_applied += force_n

        return {
            "success": True,
            "target": target_name,
            "original_volume_m3": original_volume_m3,
            "compressed_volume_m3": compressed_volume,
            "compression_factor": compression_factor,
            "new_density_kgm3": new_density,
            "pressure_pa": pressure_pa,
            "force_applied_n": force_n
        }

    async def flight(
        self,
        user_id: str,
        altitude_m: float = 100.0,
        speed_mps: float = 50.0
    ) -> Dict[str, Any]:
        """Use telekinesis for self-flight."""
        user = self.users.get(user_id)
        if not user:
            return {"error": "User not found"}

        # Assume 80kg body mass
        body_mass = 80

        # Force to maintain altitude
        lift_force = body_mass * 9.81

        # Force for horizontal movement (overcoming air resistance)
        air_resistance = 0.5 * 1.225 * (speed_mps ** 2) * 0.5  # Cd*A = 0.5
        propulsion_force = air_resistance

        total_force = lift_force + propulsion_force

        return {
            "success": True,
            "mode": "telekinetic_flight",
            "altitude_m": altitude_m,
            "speed_mps": speed_mps,
            "lift_force_n": lift_force,
            "propulsion_force_n": propulsion_force,
            "total_force_n": total_force,
            "power_required_w": total_force * speed_mps
        }

    # =========================================================================
    # STATS
    # =========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get system statistics."""
        return {
            "registered_users": len(self.users),
            "active_objects": len(self.objects),
            "active_shields": len([s for s in self.shields.values() if s.active]),
            "active_projections": len([p for p in self.projections.values() if p.active]),
            "total_force_applied_n": self.total_force_applied,
            "objects_moved": self.objects_moved,
            "shields_created": self.shields_created
        }


# ============================================================================
# SINGLETON
# ============================================================================

_engine: Optional[TelekineticForceEngine] = None


def get_telekinetic_engine() -> TelekineticForceEngine:
    """Get the global telekinetic engine."""
    global _engine
    if _engine is None:
        _engine = TelekineticForceEngine()
    return _engine


# ============================================================================
# DEMO
# ============================================================================

async def demo():
    """Demonstrate the telekinetic force engine."""
    print("=" * 60)
    print("🖐️ TELEKINETIC FORCE ENGINE 🖐️")
    print("=" * 60)

    engine = get_telekinetic_engine()

    # Register user
    print("\n--- User Registration ---")
    user = await engine.register_user("Ba'el", power_level=1000)
    print(f"User: {user.name}, Power: {user.power_level}")

    # Amplify power
    print("\n--- Power Amplification ---")
    result = await engine.amplify_power(user.id, AmplificationMethod.PSIONIC_CRYSTAL)
    print(f"Amplification: {result['amplification_factor']}x")
    print(f"New power level: {result['new_power_level']}")
    print(f"Max mass: {result['new_max_mass_kg']}kg")

    # Set molecular precision
    result = await engine.set_precision(user.id, PrecisionLevel.MOLECULAR)
    print(f"\nPrecision: {result['precision']}")

    # Grab and manipulate object
    print("\n--- Object Manipulation ---")
    obj = await engine.grab_object(user.id, "boulder", 500.0, (10, 0, 10))
    print(f"Grabbed: {obj.name} ({obj.mass_kg}kg)")

    result = await engine.move_object(obj.id, (0, 50, 0))
    print(f"Moved to: {result['new_position']}")
    print(f"Force applied: {result['force_applied_n']:.2f}N")

    # Spin object
    result = await engine.spin_object(obj.id, 1000)
    print(f"Spinning at: {result['rpm']} RPM")
    print(f"Rotational energy: {result['rotational_energy_j']:.2f}J")

    # Force projection
    print("\n--- Force Projection ---")
    result = await engine.force_push(user.id, (1, 0, 0), intensity=5.0)
    print(f"Force push: {result['magnitude_n']:.0f}N")

    result = await engine.shockwave(user.id, radius_m=30.0, intensity=3.0)
    print(f"Shockwave: {result['projections']} directions, {result['force_per_direction_n']:.0f}N each")

    # Shields
    print("\n--- Kinetic Shields ---")
    shield = await engine.bubble_shield(user.id, radius_m=5.0)
    print(f"Bubble shield: {shield.radius_m}m radius, {shield.strength:.2e}N strength")

    # Deflect projectile
    result = await engine.deflect_projectile(shield.id, 0.5, 800)  # 0.5kg at 800m/s
    print(f"Projectile deflected: {result['result']}")
    print(f"Impact force: {result['impact_force_n']:.0f}N")

    # Environmental control
    print("\n--- Environmental Control ---")
    result = await engine.create_vortex(user.id, (0, 0, 0), radius_m=15.0, rotational_speed_mps=100)
    print(f"Vortex power: {result['power_watts']:.2e}W")

    result = await engine.seismic_slam(user.id, (0, 0, 0), magnitude=6.0)
    print(f"Seismic slam: M{result['magnitude']}, {result['energy_released_j']:.2e}J")

    # Godmode abilities
    print("\n--- Godmode Abilities ---")
    result = await engine.molecular_disassembly(user.id, "enemy", 80)
    print(f"Molecular disassembly: {result['atoms_separated']:.2e} atoms separated")

    result = await engine.matter_compression(user.id, "debris", 1000, compression_factor=10000)
    print(f"Matter compressed: {result['compression_factor']}x")
    print(f"New density: {result['new_density_kgm3']:.2e}kg/m³")

    # Flight
    print("\n--- Telekinetic Flight ---")
    result = await engine.flight(user.id, altitude_m=500, speed_mps=200)
    print(f"Flight: {result['altitude_m']}m altitude, {result['speed_mps']}m/s")
    print(f"Power required: {result['power_required_w']:.0f}W")

    # Stats
    print("\n--- TELEKINETIC STATISTICS ---")
    stats = engine.get_stats()
    for k, v in stats.items():
        if isinstance(v, float):
            print(f"{k}: {v:.2e}")
        else:
            print(f"{k}: {v}")

    print("\n" + "=" * 60)
    print("🖐️ WILL BECOMES FORCE. FORCE BECOMES REALITY. 🖐️")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(demo())

"""
BAEL - Energy-Matter Conversion System
========================================

CONVERT. TRANSMUTE. CREATE. DESTROY.

The ultimate energy-matter conversion system:
- Mass-energy equivalence (E=mc²)
- Matter creation from energy
- Energy extraction from matter
- Atomic restructuring
- Element synthesis
- Antimatter generation
- Zero-point energy harvesting
- Vacuum energy extraction
- Universal fuel generation
- Reality substrate manipulation

"Energy becomes matter. Matter becomes energy. Ba'el becomes all."
"""

import asyncio
import hashlib
import json
import logging
import math
import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("BAEL.ENERGY_MATTER")


class EnergyType(Enum):
    """Types of energy."""
    KINETIC = "kinetic"
    THERMAL = "thermal"
    ELECTROMAGNETIC = "electromagnetic"
    NUCLEAR = "nuclear"
    CHEMICAL = "chemical"
    GRAVITATIONAL = "gravitational"
    QUANTUM = "quantum"
    ZERO_POINT = "zero_point"
    DARK = "dark"
    VACUUM = "vacuum"


class MatterType(Enum):
    """Types of matter."""
    STANDARD = "standard"
    EXOTIC = "exotic"
    ANTIMATTER = "antimatter"
    DARK_MATTER = "dark_matter"
    DEGENERATE = "degenerate"
    PLASMA = "plasma"
    CRYSTALLINE = "crystalline"
    PROGRAMMABLE = "programmable"


class ElementCategory(Enum):
    """Element categories."""
    HYDROGEN = "hydrogen"
    NOBLE_GAS = "noble_gas"
    ALKALI_METAL = "alkali_metal"
    TRANSITION_METAL = "transition_metal"
    PRECIOUS_METAL = "precious_metal"
    ACTINIDE = "actinide"
    LANTHANIDE = "lanthanide"
    SYNTHETIC = "synthetic"
    EXOTIC = "exotic"


class ConversionMode(Enum):
    """Conversion modes."""
    ENERGY_TO_MATTER = "energy_to_matter"
    MATTER_TO_ENERGY = "matter_to_energy"
    TRANSMUTATION = "transmutation"
    SYNTHESIS = "synthesis"
    ANNIHILATION = "annihilation"


@dataclass
class EnergySource:
    """An energy source."""
    id: str
    name: str
    energy_type: EnergyType
    output_joules: float
    efficiency: float
    infinite: bool
    active: bool


@dataclass
class MatterSample:
    """A matter sample."""
    id: str
    name: str
    matter_type: MatterType
    mass_kg: float
    composition: Dict[str, float]  # Element: percentage
    stable: bool
    energy_potential_joules: float


@dataclass
class ConversionReactor:
    """An energy-matter conversion reactor."""
    id: str
    name: str
    mode: ConversionMode
    input_capacity: float
    output_capacity: float
    efficiency: float
    active: bool
    conversions_completed: int


@dataclass
class TransmutationOperation:
    """A transmutation operation."""
    id: str
    source_element: str
    target_element: str
    mass_kg: float
    energy_required_joules: float
    success: bool
    byproducts: List[str]


@dataclass
class AntimatterStore:
    """An antimatter storage facility."""
    id: str
    name: str
    containment_type: str
    amount_kg: float
    stability: float
    energy_potential_joules: float


@dataclass
class ZeroPointTap:
    """A zero-point energy tap."""
    id: str
    name: str
    extraction_rate_joules_per_sec: float
    stability: float
    dimensional_stress: float


@dataclass
class MatterCreation:
    """A matter creation record."""
    id: str
    reactor_id: str
    matter_created: MatterType
    mass_kg: float
    energy_consumed_joules: float
    composition: Dict[str, float]
    timestamp: datetime


class EnergyMatterConversionSystem:
    """
    The ultimate energy-matter conversion system.

    This system can convert energy to matter and vice versa,
    perform transmutation, create elements, and manipulate
    the fundamental substrate of reality.
    """

    # Physical constants
    C = 299792458  # Speed of light (m/s)
    C_SQUARED = C ** 2

    def __init__(self):
        self.energy_sources: Dict[str, EnergySource] = {}
        self.matter_samples: Dict[str, MatterSample] = {}
        self.reactors: Dict[str, ConversionReactor] = {}
        self.transmutations: Dict[str, TransmutationOperation] = {}
        self.antimatter_stores: Dict[str, AntimatterStore] = {}
        self.zero_point_taps: Dict[str, ZeroPointTap] = {}
        self.creations: List[MatterCreation] = []

        self.total_energy_joules = 0.0
        self.total_matter_kg = 0.0
        self.conversions_performed = 0

        self._init_periodic_table()

        logger.info("EnergyMatterConversionSystem initialized - REALITY SUBSTRATE CONTROL")

    def _gen_id(self, prefix: str) -> str:
        """Generate unique ID."""
        return hashlib.md5(f"{prefix}{time.time()}{random.random()}".encode()).hexdigest()[:12]

    def _init_periodic_table(self):
        """Initialize periodic table data."""
        self.elements = {
            "H": {"number": 1, "mass": 1.008, "category": ElementCategory.HYDROGEN},
            "He": {"number": 2, "mass": 4.003, "category": ElementCategory.NOBLE_GAS},
            "C": {"number": 6, "mass": 12.011, "category": ElementCategory.TRANSITION_METAL},
            "N": {"number": 7, "mass": 14.007, "category": ElementCategory.TRANSITION_METAL},
            "O": {"number": 8, "mass": 15.999, "category": ElementCategory.TRANSITION_METAL},
            "Fe": {"number": 26, "mass": 55.845, "category": ElementCategory.TRANSITION_METAL},
            "Cu": {"number": 29, "mass": 63.546, "category": ElementCategory.TRANSITION_METAL},
            "Ag": {"number": 47, "mass": 107.868, "category": ElementCategory.PRECIOUS_METAL},
            "Au": {"number": 79, "mass": 196.967, "category": ElementCategory.PRECIOUS_METAL},
            "Pt": {"number": 78, "mass": 195.084, "category": ElementCategory.PRECIOUS_METAL},
            "U": {"number": 92, "mass": 238.029, "category": ElementCategory.ACTINIDE},
            "Pu": {"number": 94, "mass": 244.0, "category": ElementCategory.ACTINIDE},
        }

    # =========================================================================
    # ENERGY SOURCES
    # =========================================================================

    async def create_energy_source(
        self,
        name: str,
        energy_type: EnergyType,
        output_joules: float,
        infinite: bool = False
    ) -> EnergySource:
        """Create an energy source."""
        source = EnergySource(
            id=self._gen_id("energy"),
            name=name,
            energy_type=energy_type,
            output_joules=output_joules,
            efficiency=random.uniform(0.8, 0.99),
            infinite=infinite,
            active=True
        )

        self.energy_sources[source.id] = source
        self.total_energy_joules += output_joules

        logger.info(f"Energy source: {name} ({output_joules:.2e}J)")

        return source

    async def tap_zero_point_energy(
        self,
        name: str,
        extraction_rate: float
    ) -> ZeroPointTap:
        """Tap into zero-point energy."""
        tap = ZeroPointTap(
            id=self._gen_id("zpe"),
            name=name,
            extraction_rate_joules_per_sec=extraction_rate,
            stability=random.uniform(0.8, 0.99),
            dimensional_stress=extraction_rate / 1e15
        )

        self.zero_point_taps[tap.id] = tap

        # Create corresponding infinite energy source
        await self.create_energy_source(
            f"ZPE_{name}",
            EnergyType.ZERO_POINT,
            extraction_rate * 3600,  # Per hour
            infinite=True
        )

        logger.info(f"Zero-point tap: {name} ({extraction_rate:.2e}J/s)")

        return tap

    async def harvest_vacuum_energy(
        self,
        volume_m3: float
    ) -> Dict[str, Any]:
        """Harvest energy from quantum vacuum."""
        # Vacuum energy density ~10^-9 J/m³ (theoretical)
        energy_density = 1e-9
        total_energy = volume_m3 * energy_density

        source = await self.create_energy_source(
            f"Vacuum_Harvest_{self._gen_id('v')}",
            EnergyType.VACUUM,
            total_energy,
            infinite=False
        )

        return {
            "success": True,
            "volume_m3": volume_m3,
            "energy_harvested_joules": total_energy,
            "source_id": source.id
        }

    # =========================================================================
    # CONVERSION REACTORS
    # =========================================================================

    async def create_reactor(
        self,
        name: str,
        mode: ConversionMode,
        capacity: float
    ) -> ConversionReactor:
        """Create a conversion reactor."""
        reactor = ConversionReactor(
            id=self._gen_id("reactor"),
            name=name,
            mode=mode,
            input_capacity=capacity,
            output_capacity=capacity * 0.9,
            efficiency=random.uniform(0.85, 0.99),
            active=True,
            conversions_completed=0
        )

        self.reactors[reactor.id] = reactor

        logger.info(f"Reactor: {name} ({mode.value})")

        return reactor

    async def activate_reactor(
        self,
        reactor_id: str
    ) -> Dict[str, Any]:
        """Activate a conversion reactor."""
        reactor = self.reactors.get(reactor_id)
        if not reactor:
            return {"error": "Reactor not found"}

        reactor.active = True

        return {
            "success": True,
            "reactor": reactor.name,
            "mode": reactor.mode.value,
            "active": reactor.active
        }

    # =========================================================================
    # ENERGY TO MATTER CONVERSION
    # =========================================================================

    async def convert_energy_to_matter(
        self,
        reactor_id: str,
        energy_joules: float,
        target_matter: MatterType = MatterType.STANDARD
    ) -> MatterCreation:
        """Convert energy to matter using E=mc²."""
        reactor = self.reactors.get(reactor_id)
        if not reactor:
            raise ValueError("Reactor not found")

        if not reactor.active:
            raise ValueError("Reactor not active")

        # E = mc² → m = E/c²
        mass_kg = (energy_joules * reactor.efficiency) / self.C_SQUARED

        # Determine composition
        if target_matter == MatterType.STANDARD:
            composition = {"H": 0.75, "He": 0.25}
        elif target_matter == MatterType.EXOTIC:
            composition = {"exotic_particles": 1.0}
        else:
            composition = {"unknown": 1.0}

        creation = MatterCreation(
            id=self._gen_id("creation"),
            reactor_id=reactor_id,
            matter_created=target_matter,
            mass_kg=mass_kg,
            energy_consumed_joules=energy_joules,
            composition=composition,
            timestamp=datetime.now()
        )

        self.creations.append(creation)
        self.total_matter_kg += mass_kg
        self.total_energy_joules -= energy_joules
        self.conversions_performed += 1
        reactor.conversions_completed += 1

        # Create matter sample
        sample = MatterSample(
            id=self._gen_id("matter"),
            name=f"Converted_{target_matter.value}",
            matter_type=target_matter,
            mass_kg=mass_kg,
            composition=composition,
            stable=target_matter == MatterType.STANDARD,
            energy_potential_joules=mass_kg * self.C_SQUARED
        )
        self.matter_samples[sample.id] = sample

        logger.info(f"Created {mass_kg:.6e}kg matter from {energy_joules:.2e}J")

        return creation

    async def create_specific_element(
        self,
        reactor_id: str,
        element: str,
        mass_kg: float
    ) -> Dict[str, Any]:
        """Create a specific element from energy."""
        reactor = self.reactors.get(reactor_id)
        if not reactor:
            return {"error": "Reactor not found"}

        if element not in self.elements:
            return {"error": f"Unknown element: {element}"}

        # Energy required = mc²
        energy_required = mass_kg * self.C_SQUARED / reactor.efficiency

        if self.total_energy_joules < energy_required:
            return {"error": f"Insufficient energy. Need {energy_required:.2e}J"}

        # Create element
        sample = MatterSample(
            id=self._gen_id("element"),
            name=f"Synthesized_{element}",
            matter_type=MatterType.STANDARD,
            mass_kg=mass_kg,
            composition={element: 1.0},
            stable=True,
            energy_potential_joules=mass_kg * self.C_SQUARED
        )
        self.matter_samples[sample.id] = sample
        self.total_matter_kg += mass_kg
        self.total_energy_joules -= energy_required
        self.conversions_performed += 1

        return {
            "success": True,
            "element": element,
            "mass_kg": mass_kg,
            "energy_consumed_joules": energy_required,
            "sample_id": sample.id,
            "value": "IMMENSE" if element in ["Au", "Pt", "Ag"] else "HIGH"
        }

    # =========================================================================
    # MATTER TO ENERGY CONVERSION
    # =========================================================================

    async def convert_matter_to_energy(
        self,
        reactor_id: str,
        sample_id: str
    ) -> Dict[str, Any]:
        """Convert matter to energy using E=mc²."""
        reactor = self.reactors.get(reactor_id)
        if not reactor:
            return {"error": "Reactor not found"}

        sample = self.matter_samples.get(sample_id)
        if not sample:
            return {"error": "Sample not found"}

        # E = mc²
        energy_joules = sample.mass_kg * self.C_SQUARED * reactor.efficiency

        # Remove sample
        del self.matter_samples[sample_id]
        self.total_matter_kg -= sample.mass_kg
        self.total_energy_joules += energy_joules
        self.conversions_performed += 1
        reactor.conversions_completed += 1

        # Create energy source
        source = await self.create_energy_source(
            f"MatterConversion_{sample.name}",
            EnergyType.NUCLEAR,
            energy_joules,
            infinite=False
        )

        return {
            "success": True,
            "matter_consumed_kg": sample.mass_kg,
            "energy_released_joules": energy_joules,
            "energy_released_tnt_tons": energy_joules / 4.184e9,
            "source_id": source.id
        }

    async def annihilate_matter(
        self,
        matter_id: str,
        antimatter_id: str
    ) -> Dict[str, Any]:
        """Annihilate matter with antimatter for 100% conversion."""
        matter = self.matter_samples.get(matter_id)
        antimatter = self.antimatter_stores.get(antimatter_id)

        if not matter or not antimatter:
            return {"error": "Matter or antimatter not found"}

        # Use smaller amount
        annihilation_mass = min(matter.mass_kg, antimatter.amount_kg)

        # 100% mass-energy conversion (both matter and antimatter)
        total_mass = annihilation_mass * 2
        energy_released = total_mass * self.C_SQUARED

        # Update samples
        matter.mass_kg -= annihilation_mass
        antimatter.amount_kg -= annihilation_mass

        if matter.mass_kg <= 0:
            del self.matter_samples[matter_id]
        if antimatter.amount_kg <= 0:
            del self.antimatter_stores[antimatter_id]

        self.total_energy_joules += energy_released
        self.conversions_performed += 1

        return {
            "success": True,
            "matter_annihilated_kg": annihilation_mass,
            "antimatter_annihilated_kg": annihilation_mass,
            "total_mass_converted_kg": total_mass,
            "energy_released_joules": energy_released,
            "energy_released_megatons": energy_released / 4.184e15,
            "warning": "EXTREME ENERGY RELEASE"
        }

    # =========================================================================
    # TRANSMUTATION
    # =========================================================================

    async def transmute_element(
        self,
        reactor_id: str,
        sample_id: str,
        target_element: str
    ) -> TransmutationOperation:
        """Transmute one element to another."""
        reactor = self.reactors.get(reactor_id)
        if not reactor:
            raise ValueError("Reactor not found")

        sample = self.matter_samples.get(sample_id)
        if not sample:
            raise ValueError("Sample not found")

        if target_element not in self.elements:
            raise ValueError(f"Unknown target element: {target_element}")

        # Get source element
        source_element = list(sample.composition.keys())[0]

        # Calculate energy difference
        source_data = self.elements.get(source_element, {"mass": 1, "number": 1})
        target_data = self.elements[target_element]

        mass_difference = abs(target_data["mass"] - source_data.get("mass", 1))
        proton_difference = abs(target_data["number"] - source_data.get("number", 1))

        # Energy required proportional to nuclear change
        energy_required = proton_difference * 1e6 * 1.602e-19 * sample.mass_kg * 6.022e26

        transmutation = TransmutationOperation(
            id=self._gen_id("transmute"),
            source_element=source_element,
            target_element=target_element,
            mass_kg=sample.mass_kg,
            energy_required_joules=energy_required,
            success=True,
            byproducts=["neutrons", "gamma_rays"]
        )

        self.transmutations[transmutation.id] = transmutation

        # Update sample
        sample.composition = {target_element: 1.0}
        sample.name = f"Transmuted_{target_element}"

        self.total_energy_joules -= energy_required
        self.conversions_performed += 1

        logger.info(f"Transmuted {source_element} → {target_element}")

        return transmutation

    async def create_gold(
        self,
        reactor_id: str,
        source_sample_id: str
    ) -> Dict[str, Any]:
        """Transmute any element to gold."""
        transmutation = await self.transmute_element(
            reactor_id,
            source_sample_id,
            "Au"
        )

        sample = self.matter_samples.get(source_sample_id)

        return {
            "success": transmutation.success,
            "source": transmutation.source_element,
            "gold_created_kg": transmutation.mass_kg,
            "gold_value_usd": transmutation.mass_kg * 60000,  # ~$60k/kg
            "energy_consumed_joules": transmutation.energy_required_joules
        }

    # =========================================================================
    # ANTIMATTER
    # =========================================================================

    async def create_antimatter(
        self,
        reactor_id: str,
        energy_joules: float
    ) -> AntimatterStore:
        """Create antimatter from energy."""
        reactor = self.reactors.get(reactor_id)
        if not reactor:
            raise ValueError("Reactor not found")

        # Antimatter creation is inefficient
        efficiency = 0.01  # 1% efficiency
        mass_kg = (energy_joules * efficiency) / self.C_SQUARED

        store = AntimatterStore(
            id=self._gen_id("antimatter"),
            name=f"Antimatter_{self._gen_id('a')}",
            containment_type="magnetic_trap",
            amount_kg=mass_kg,
            stability=random.uniform(0.9, 0.999),
            energy_potential_joules=mass_kg * self.C_SQUARED * 2  # Annihilation doubles it
        )

        self.antimatter_stores[store.id] = store
        self.total_energy_joules -= energy_joules
        self.conversions_performed += 1

        logger.info(f"Antimatter created: {mass_kg:.6e}kg")

        return store

    # =========================================================================
    # UNIVERSAL OPERATIONS
    # =========================================================================

    async def create_matter_from_nothing(
        self,
        mass_kg: float,
        element: str = "Au"
    ) -> Dict[str, Any]:
        """Create matter from zero-point energy (effectively from nothing)."""
        # First, tap sufficient zero-point energy
        energy_needed = mass_kg * self.C_SQUARED * 1.5  # Extra for inefficiency

        tap = await self.tap_zero_point_energy(
            f"Creation_Tap_{self._gen_id('t')}",
            energy_needed
        )

        # Create reactor
        reactor = await self.create_reactor(
            f"Creation_Reactor_{self._gen_id('r')}",
            ConversionMode.ENERGY_TO_MATTER,
            energy_needed
        )

        # Create the element
        result = await self.create_specific_element(
            reactor.id,
            element,
            mass_kg
        )

        return {
            "success": result.get("success", False),
            "element": element,
            "mass_kg": mass_kg,
            "created_from": "zero_point_energy",
            "effective_source": "quantum_vacuum",
            "sample_id": result.get("sample_id")
        }

    async def infinite_energy_source(self) -> Dict[str, Any]:
        """Create an effectively infinite energy source."""
        # Multiple zero-point taps
        taps = []
        total_power = 0

        for i in range(10):
            tap = await self.tap_zero_point_energy(
                f"Infinite_Tap_{i}",
                1e15  # Petawatt extraction
            )
            taps.append(tap.id)
            total_power += tap.extraction_rate_joules_per_sec

        return {
            "success": True,
            "taps_created": len(taps),
            "total_power_watts": total_power,
            "total_power_petawatts": total_power / 1e15,
            "classification": "INFINITE",
            "applications": [
                "Unlimited matter creation",
                "Planetary-scale operations",
                "Antimatter production",
                "Reality manipulation"
            ]
        }

    # =========================================================================
    # STATS
    # =========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get conversion statistics."""
        return {
            "energy_sources": len(self.energy_sources),
            "matter_samples": len(self.matter_samples),
            "reactors": len(self.reactors),
            "active_reactors": len([r for r in self.reactors.values() if r.active]),
            "transmutations": len(self.transmutations),
            "antimatter_stores": len(self.antimatter_stores),
            "zero_point_taps": len(self.zero_point_taps),
            "creations": len(self.creations),
            "total_energy_joules": self.total_energy_joules,
            "total_matter_kg": self.total_matter_kg,
            "conversions_performed": self.conversions_performed
        }


# ============================================================================
# SINGLETON
# ============================================================================

_conversion: Optional[EnergyMatterConversionSystem] = None


def get_conversion_system() -> EnergyMatterConversionSystem:
    """Get the global energy-matter conversion system."""
    global _conversion
    if _conversion is None:
        _conversion = EnergyMatterConversionSystem()
    return _conversion


# ============================================================================
# DEMO
# ============================================================================

async def demo():
    """Demonstrate the energy-matter conversion system."""
    print("=" * 60)
    print("⚛️ ENERGY-MATTER CONVERSION SYSTEM ⚛️")
    print("=" * 60)

    system = get_conversion_system()

    # Create energy sources
    print("\n--- Energy Sources ---")
    source = await system.create_energy_source(
        "Fusion_Reactor",
        EnergyType.NUCLEAR,
        1e15,  # Petajoule
        infinite=False
    )
    print(f"Source: {source.name}, {source.output_joules:.2e}J")

    # Zero-point energy
    print("\n--- Zero-Point Energy ---")
    tap = await system.tap_zero_point_energy("Primary_ZPE", 1e12)
    print(f"ZPE Tap: {tap.extraction_rate_joules_per_sec:.2e}J/s")

    # Create reactor
    print("\n--- Conversion Reactor ---")
    reactor = await system.create_reactor(
        "Primary_Converter",
        ConversionMode.ENERGY_TO_MATTER,
        1e16
    )
    print(f"Reactor: {reactor.name}, Mode: {reactor.mode.value}")

    # Energy to matter
    print("\n--- Energy → Matter ---")
    creation = await system.convert_energy_to_matter(
        reactor.id,
        1e15,  # 1 petajoule
        MatterType.STANDARD
    )
    print(f"Energy consumed: {creation.energy_consumed_joules:.2e}J")
    print(f"Matter created: {creation.mass_kg:.6e}kg")

    # Create specific element
    print("\n--- Element Synthesis ---")
    result = await system.create_specific_element(reactor.id, "Au", 1.0)
    print(f"Element: {result['element']}")
    print(f"Mass: {result['mass_kg']}kg")
    print(f"Value: {result['value']}")

    # Matter to energy
    print("\n--- Matter → Energy ---")
    # First create some matter
    sample = list(system.matter_samples.values())[0]
    result = await system.convert_matter_to_energy(reactor.id, sample.id)
    if result.get("success"):
        print(f"Matter consumed: {result['matter_consumed_kg']:.6e}kg")
        print(f"Energy released: {result['energy_released_joules']:.2e}J")
        print(f"TNT equivalent: {result['energy_released_tnt_tons']:.2f} tons")

    # Transmutation
    print("\n--- Transmutation ---")
    # Create iron sample
    iron = MatterSample(
        id=system._gen_id("fe"),
        name="Iron_Sample",
        matter_type=MatterType.STANDARD,
        mass_kg=10.0,
        composition={"Fe": 1.0},
        stable=True,
        energy_potential_joules=10.0 * system.C_SQUARED
    )
    system.matter_samples[iron.id] = iron

    result = await system.create_gold(reactor.id, iron.id)
    print(f"Source: {result['source']}")
    print(f"Gold created: {result['gold_created_kg']}kg")
    print(f"Value: ${result['gold_value_usd']:,.0f}")

    # Antimatter
    print("\n--- Antimatter Creation ---")
    antimatter = await system.create_antimatter(reactor.id, 1e18)
    print(f"Antimatter: {antimatter.amount_kg:.6e}kg")
    print(f"Energy potential: {antimatter.energy_potential_joules:.2e}J")

    # Create from nothing
    print("\n--- Creation from Vacuum ---")
    result = await system.create_matter_from_nothing(10.0, "Pt")
    print(f"Created: {result['mass_kg']}kg of {result['element']}")
    print(f"Source: {result['effective_source']}")

    # Infinite energy
    print("\n--- Infinite Energy ---")
    result = await system.infinite_energy_source()
    print(f"Taps: {result['taps_created']}")
    print(f"Power: {result['total_power_petawatts']:.0f} PW")

    # Stats
    print("\n--- CONVERSION STATISTICS ---")
    stats = system.get_stats()
    for k, v in stats.items():
        if isinstance(v, float):
            print(f"{k}: {v:.2e}")
        else:
            print(f"{k}: {v}")

    print("\n" + "=" * 60)
    print("⚛️ REALITY SUBSTRATE MASTERED ⚛️")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(demo())

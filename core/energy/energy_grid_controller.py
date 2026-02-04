"""
BAEL - Energy Grid Controller
==============================

POWER. BLACKOUT. SURGE. CONTROL.

Complete energy domination:
- Power grid control
- Blackout orchestration
- Surge attacks
- Generator control
- Renewable manipulation
- Nuclear facility control
- Oil/gas pipeline control
- Energy market manipulation
- Load manipulation
- Critical infrastructure control

"Ba'el controls the flow of power."
"""

import asyncio
import logging
import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("BAEL.ENERGY")


class EnergyType(Enum):
    """Types of energy."""
    ELECTRICITY = "electricity"
    GAS = "gas"
    OIL = "oil"
    NUCLEAR = "nuclear"
    SOLAR = "solar"
    WIND = "wind"
    HYDRO = "hydro"
    COAL = "coal"
    GEOTHERMAL = "geothermal"


class FacilityType(Enum):
    """Types of energy facilities."""
    POWER_PLANT = "power_plant"
    SUBSTATION = "substation"
    TRANSFORMER = "transformer"
    NUCLEAR_PLANT = "nuclear_plant"
    SOLAR_FARM = "solar_farm"
    WIND_FARM = "wind_farm"
    HYDRO_DAM = "hydro_dam"
    REFINERY = "refinery"
    PIPELINE = "pipeline"
    STORAGE = "storage"


class GridType(Enum):
    """Types of power grids."""
    TRANSMISSION = "transmission"
    DISTRIBUTION = "distribution"
    MICROGRID = "microgrid"
    SMART_GRID = "smart_grid"


class AttackType(Enum):
    """Types of attacks."""
    BLACKOUT = "blackout"
    BROWNOUT = "brownout"
    SURGE = "surge"
    OVERLOAD = "overload"
    SHUTDOWN = "shutdown"
    MANIPULATION = "manipulation"
    SABOTAGE = "sabotage"
    DENIAL = "denial"


class ControlMethod(Enum):
    """Control methods."""
    SCADA_EXPLOIT = "scada_exploit"
    NETWORK_INTRUSION = "network_intrusion"
    PHYSICAL_ACCESS = "physical_access"
    INSIDER = "insider"
    SUPPLY_CHAIN = "supply_chain"
    MALWARE = "malware"


class ControlLevel(Enum):
    """Levels of control."""
    NONE = "none"
    MONITOR = "monitor"
    INFLUENCE = "influence"
    PARTIAL = "partial"
    FULL = "full"


@dataclass
class Facility:
    """An energy facility."""
    id: str
    name: str
    facility_type: FacilityType
    energy_type: EnergyType
    capacity: float  # MW
    current_output: float
    location: str
    control_level: ControlLevel = ControlLevel.NONE


@dataclass
class Grid:
    """A power grid."""
    id: str
    name: str
    grid_type: GridType
    facilities: List[str]
    load: float
    capacity: float
    status: str = "operational"
    control_level: ControlLevel = ControlLevel.NONE


@dataclass
class Pipeline:
    """An oil/gas pipeline."""
    id: str
    name: str
    energy_type: EnergyType
    throughput: float
    length: float
    status: str = "flowing"
    control_level: ControlLevel = ControlLevel.NONE


@dataclass
class Attack:
    """An attack on energy infrastructure."""
    id: str
    attack_type: AttackType
    target_id: str
    method: ControlMethod
    impact: str
    success: bool = False


class EnergyGridController:
    """
    The energy grid controller.

    Complete energy domination:
    - Facility control
    - Grid manipulation
    - Attack execution
    """

    def __init__(self):
        self.facilities: Dict[str, Facility] = {}
        self.grids: Dict[str, Grid] = {}
        self.pipelines: Dict[str, Pipeline] = {}
        self.attacks: List[Attack] = []

        self.facilities_controlled = 0
        self.grids_controlled = 0
        self.pipelines_controlled = 0
        self.blackouts_caused = 0
        self.population_affected = 0

        self._init_energy_data()

        logger.info("EnergyGridController initialized - BA'EL CONTROLS THE POWER")

    def _gen_id(self) -> str:
        """Generate unique ID."""
        return f"eng_{int(time.time() * 1000) % 100000}_{random.randint(1000, 9999)}"

    def _init_energy_data(self):
        """Initialize energy data."""
        self.control_effectiveness = {
            ControlMethod.SCADA_EXPLOIT: 0.85,
            ControlMethod.NETWORK_INTRUSION: 0.75,
            ControlMethod.PHYSICAL_ACCESS: 0.90,
            ControlMethod.INSIDER: 0.95,
            ControlMethod.SUPPLY_CHAIN: 0.70,
            ControlMethod.MALWARE: 0.80
        }

        self.attack_impact = {
            AttackType.BLACKOUT: 1.0,
            AttackType.BROWNOUT: 0.5,
            AttackType.SURGE: 0.8,
            AttackType.OVERLOAD: 0.9,
            AttackType.SHUTDOWN: 0.7,
            AttackType.MANIPULATION: 0.4,
            AttackType.SABOTAGE: 0.9,
            AttackType.DENIAL: 0.6
        }

        self.facility_criticality = {
            FacilityType.NUCLEAR_PLANT: 1.0,
            FacilityType.POWER_PLANT: 0.8,
            FacilityType.HYDRO_DAM: 0.7,
            FacilityType.SUBSTATION: 0.6,
            FacilityType.REFINERY: 0.8,
            FacilityType.PIPELINE: 0.7
        }

    # =========================================================================
    # FACILITY CONTROL
    # =========================================================================

    async def identify_facility(
        self,
        name: str,
        facility_type: FacilityType,
        energy_type: EnergyType,
        capacity: float,
        location: str
    ) -> Facility:
        """Identify an energy facility."""
        facility = Facility(
            id=self._gen_id(),
            name=name,
            facility_type=facility_type,
            energy_type=energy_type,
            capacity=capacity,
            current_output=capacity * random.uniform(0.3, 0.9),
            location=location
        )

        self.facilities[facility.id] = facility

        return facility

    async def control_facility(
        self,
        facility_id: str,
        method: ControlMethod
    ) -> Dict[str, Any]:
        """Take control of a facility."""
        facility = self.facilities.get(facility_id)
        if not facility:
            return {"error": "Facility not found"}

        effectiveness = self.control_effectiveness.get(method, 0.5)

        if random.random() < effectiveness:
            facility.control_level = ControlLevel.FULL
            self.facilities_controlled += 1

            return {
                "facility": facility.name,
                "type": facility.facility_type.value,
                "method": method.value,
                "success": True,
                "capacity": facility.capacity
            }

        return {
            "facility": facility.name,
            "method": method.value,
            "success": False
        }

    async def manipulate_output(
        self,
        facility_id: str,
        new_output: float
    ) -> Dict[str, Any]:
        """Manipulate facility output."""
        facility = self.facilities.get(facility_id)
        if not facility:
            return {"error": "Facility not found"}

        if facility.control_level != ControlLevel.FULL:
            return {"error": "Facility not fully controlled"}

        old_output = facility.current_output
        facility.current_output = min(new_output, facility.capacity)

        return {
            "facility": facility.name,
            "old_output": old_output,
            "new_output": facility.current_output,
            "change": facility.current_output - old_output
        }

    async def shutdown_facility(
        self,
        facility_id: str
    ) -> Dict[str, Any]:
        """Shutdown a facility."""
        facility = self.facilities.get(facility_id)
        if not facility:
            return {"error": "Facility not found"}

        old_output = facility.current_output
        facility.current_output = 0

        population = int(old_output * 1000)  # Rough estimate
        self.population_affected += population

        return {
            "facility": facility.name,
            "shutdown": True,
            "output_lost": old_output,
            "population_affected": population
        }

    # =========================================================================
    # GRID CONTROL
    # =========================================================================

    async def identify_grid(
        self,
        name: str,
        grid_type: GridType,
        capacity: float
    ) -> Grid:
        """Identify a power grid."""
        grid = Grid(
            id=self._gen_id(),
            name=name,
            grid_type=grid_type,
            facilities=[],
            load=capacity * random.uniform(0.4, 0.8),
            capacity=capacity
        )

        self.grids[grid.id] = grid

        return grid

    async def connect_facility_to_grid(
        self,
        grid_id: str,
        facility_id: str
    ) -> Dict[str, Any]:
        """Connect facility to grid."""
        grid = self.grids.get(grid_id)
        facility = self.facilities.get(facility_id)

        if not grid:
            return {"error": "Grid not found"}
        if not facility:
            return {"error": "Facility not found"}

        grid.facilities.append(facility_id)

        return {
            "grid": grid.name,
            "facility": facility.name,
            "connected": True
        }

    async def control_grid(
        self,
        grid_id: str,
        method: ControlMethod
    ) -> Dict[str, Any]:
        """Take control of a grid."""
        grid = self.grids.get(grid_id)
        if not grid:
            return {"error": "Grid not found"}

        effectiveness = self.control_effectiveness.get(method, 0.5)

        if random.random() < effectiveness:
            grid.control_level = ControlLevel.FULL
            self.grids_controlled += 1

            return {
                "grid": grid.name,
                "type": grid.grid_type.value,
                "method": method.value,
                "success": True,
                "capacity": grid.capacity
            }

        return {"grid": grid.name, "success": False}

    async def cause_blackout(
        self,
        grid_id: str
    ) -> Dict[str, Any]:
        """Cause a blackout."""
        grid = self.grids.get(grid_id)
        if not grid:
            return {"error": "Grid not found"}

        grid.status = "blackout"
        grid.load = 0

        # Shutdown all connected facilities
        for fid in grid.facilities:
            await self.shutdown_facility(fid)

        self.blackouts_caused += 1
        population = int(grid.capacity * 2000)  # Rough estimate
        self.population_affected += population

        attack = Attack(
            id=self._gen_id(),
            attack_type=AttackType.BLACKOUT,
            target_id=grid_id,
            method=ControlMethod.SCADA_EXPLOIT,
            impact="complete_blackout",
            success=True
        )
        self.attacks.append(attack)

        return {
            "grid": grid.name,
            "blackout": True,
            "facilities_affected": len(grid.facilities),
            "population_affected": population
        }

    async def cause_surge(
        self,
        grid_id: str
    ) -> Dict[str, Any]:
        """Cause a power surge."""
        grid = self.grids.get(grid_id)
        if not grid:
            return {"error": "Grid not found"}

        # Overload the grid
        grid.load = grid.capacity * 1.5

        attack = Attack(
            id=self._gen_id(),
            attack_type=AttackType.SURGE,
            target_id=grid_id,
            method=ControlMethod.MALWARE,
            impact="equipment_damage",
            success=True
        )
        self.attacks.append(attack)

        return {
            "grid": grid.name,
            "surge": True,
            "overload": grid.load / grid.capacity * 100,
            "damage": "equipment_fried"
        }

    # =========================================================================
    # PIPELINE CONTROL
    # =========================================================================

    async def identify_pipeline(
        self,
        name: str,
        energy_type: EnergyType,
        throughput: float,
        length: float
    ) -> Pipeline:
        """Identify a pipeline."""
        pipeline = Pipeline(
            id=self._gen_id(),
            name=name,
            energy_type=energy_type,
            throughput=throughput,
            length=length
        )

        self.pipelines[pipeline.id] = pipeline

        return pipeline

    async def control_pipeline(
        self,
        pipeline_id: str,
        method: ControlMethod
    ) -> Dict[str, Any]:
        """Take control of a pipeline."""
        pipeline = self.pipelines.get(pipeline_id)
        if not pipeline:
            return {"error": "Pipeline not found"}

        effectiveness = self.control_effectiveness.get(method, 0.5)

        if random.random() < effectiveness:
            pipeline.control_level = ControlLevel.FULL
            self.pipelines_controlled += 1

            return {
                "pipeline": pipeline.name,
                "type": pipeline.energy_type.value,
                "method": method.value,
                "success": True,
                "throughput": pipeline.throughput
            }

        return {"pipeline": pipeline.name, "success": False}

    async def shutdown_pipeline(
        self,
        pipeline_id: str
    ) -> Dict[str, Any]:
        """Shutdown a pipeline."""
        pipeline = self.pipelines.get(pipeline_id)
        if not pipeline:
            return {"error": "Pipeline not found"}

        old_throughput = pipeline.throughput
        pipeline.status = "shutdown"
        pipeline.throughput = 0

        return {
            "pipeline": pipeline.name,
            "shutdown": True,
            "throughput_lost": old_throughput
        }

    # =========================================================================
    # ATTACK EXECUTION
    # =========================================================================

    async def execute_attack(
        self,
        target_id: str,
        attack_type: AttackType,
        method: ControlMethod
    ) -> Dict[str, Any]:
        """Execute an attack on energy infrastructure."""
        target = (
            self.facilities.get(target_id) or
            self.grids.get(target_id) or
            self.pipelines.get(target_id)
        )

        if not target:
            return {"error": "Target not found"}

        effectiveness = self.control_effectiveness.get(method, 0.5)
        impact_level = self.attack_impact.get(attack_type, 0.5)

        success = random.random() < (effectiveness * impact_level)

        attack = Attack(
            id=self._gen_id(),
            attack_type=attack_type,
            target_id=target_id,
            method=method,
            impact=f"{attack_type.value}_impact",
            success=success
        )
        self.attacks.append(attack)

        if success:
            if attack_type == AttackType.BLACKOUT:
                if isinstance(target, Grid):
                    await self.cause_blackout(target_id)
            elif attack_type == AttackType.SHUTDOWN:
                if isinstance(target, Facility):
                    await self.shutdown_facility(target_id)
                elif isinstance(target, Pipeline):
                    await self.shutdown_pipeline(target_id)
            elif attack_type == AttackType.SURGE:
                if isinstance(target, Grid):
                    await self.cause_surge(target_id)

        return {
            "target": getattr(target, 'name', 'Unknown'),
            "attack_type": attack_type.value,
            "method": method.value,
            "success": success
        }

    # =========================================================================
    # FULL ENERGY DOMINATION
    # =========================================================================

    async def full_energy_domination(
        self,
        region: str
    ) -> Dict[str, Any]:
        """Execute full energy domination."""
        results = {
            "facilities_identified": 0,
            "facilities_controlled": 0,
            "grids_identified": 0,
            "grids_controlled": 0,
            "pipelines_identified": 0,
            "pipelines_controlled": 0,
            "blackouts_caused": 0,
            "population_affected": 0
        }

        # Identify and control facilities
        facility_types = [
            (FacilityType.NUCLEAR_PLANT, EnergyType.NUCLEAR, 1000),
            (FacilityType.POWER_PLANT, EnergyType.COAL, 500),
            (FacilityType.POWER_PLANT, EnergyType.GAS, 400),
            (FacilityType.HYDRO_DAM, EnergyType.HYDRO, 300),
            (FacilityType.SOLAR_FARM, EnergyType.SOLAR, 100),
            (FacilityType.WIND_FARM, EnergyType.WIND, 150)
        ]

        facilities = []
        for ft, et, cap in facility_types:
            facility = await self.identify_facility(
                f"{ft.value}_{region}",
                ft, et, cap, region
            )
            facilities.append(facility)
            results["facilities_identified"] += 1

            control = await self.control_facility(facility.id, ControlMethod.SCADA_EXPLOIT)
            if control.get("success"):
                results["facilities_controlled"] += 1

        # Identify and control grids
        for gt in [GridType.TRANSMISSION, GridType.DISTRIBUTION]:
            grid = await self.identify_grid(
                f"{gt.value}_{region}",
                gt,
                sum(f.capacity for f in facilities) * 1.2
            )
            results["grids_identified"] += 1

            # Connect facilities
            for f in facilities[:3]:
                await self.connect_facility_to_grid(grid.id, f.id)

            control = await self.control_grid(grid.id, ControlMethod.NETWORK_INTRUSION)
            if control.get("success"):
                results["grids_controlled"] += 1

                # Cause blackout
                blackout = await self.cause_blackout(grid.id)
                results["blackouts_caused"] += 1
                results["population_affected"] += blackout.get("population_affected", 0)

        # Identify and control pipelines
        for et in [EnergyType.GAS, EnergyType.OIL]:
            pipeline = await self.identify_pipeline(
                f"{et.value}_pipeline_{region}",
                et,
                random.uniform(100000, 500000),
                random.uniform(500, 2000)
            )
            results["pipelines_identified"] += 1

            control = await self.control_pipeline(pipeline.id, ControlMethod.MALWARE)
            if control.get("success"):
                results["pipelines_controlled"] += 1
                await self.shutdown_pipeline(pipeline.id)

        return results

    def get_stats(self) -> Dict[str, Any]:
        """Get controller statistics."""
        return {
            "facilities_tracked": len(self.facilities),
            "facilities_controlled": self.facilities_controlled,
            "grids_tracked": len(self.grids),
            "grids_controlled": self.grids_controlled,
            "pipelines_tracked": len(self.pipelines),
            "pipelines_controlled": self.pipelines_controlled,
            "attacks_executed": len(self.attacks),
            "blackouts_caused": self.blackouts_caused,
            "population_affected": self.population_affected
        }


# ============================================================================
# SINGLETON
# ============================================================================

_controller: Optional[EnergyGridController] = None


def get_energy_grid_controller() -> EnergyGridController:
    """Get the global energy grid controller."""
    global _controller
    if _controller is None:
        _controller = EnergyGridController()
    return _controller


# ============================================================================
# DEMO
# ============================================================================

async def demo():
    """Demonstrate energy grid control."""
    print("=" * 60)
    print("⚡ ENERGY GRID CONTROLLER ⚡")
    print("=" * 60)

    controller = get_energy_grid_controller()

    # Identify facility
    print("\n--- Facility Identification ---")
    facility = await controller.identify_facility(
        "Main Power Plant",
        FacilityType.POWER_PLANT,
        EnergyType.GAS,
        500,
        "Metro City"
    )
    print(f"Facility: {facility.name}")
    print(f"Type: {facility.facility_type.value}")
    print(f"Capacity: {facility.capacity} MW")
    print(f"Output: {facility.current_output:.1f} MW")

    # Control facility
    print("\n--- Facility Control ---")
    control = await controller.control_facility(facility.id, ControlMethod.SCADA_EXPLOIT)
    print(f"Control: {control}")

    # Manipulate output
    manip = await controller.manipulate_output(facility.id, 100)
    print(f"Manipulation: {manip}")

    # Identify grid
    print("\n--- Grid Identification ---")
    grid = await controller.identify_grid(
        "Metro Grid",
        GridType.DISTRIBUTION,
        1000
    )
    print(f"Grid: {grid.name}")
    print(f"Capacity: {grid.capacity} MW")
    print(f"Load: {grid.load:.1f} MW")

    # Connect and control grid
    await controller.connect_facility_to_grid(grid.id, facility.id)
    grid_control = await controller.control_grid(grid.id, ControlMethod.NETWORK_INTRUSION)
    print(f"Grid control: {grid_control}")

    # Cause blackout
    print("\n--- Blackout ---")
    blackout = await controller.cause_blackout(grid.id)
    print(f"Blackout: {blackout}")

    # Identify pipeline
    print("\n--- Pipeline Control ---")
    pipeline = await controller.identify_pipeline(
        "Main Gas Pipeline",
        EnergyType.GAS,
        250000,
        1500
    )
    print(f"Pipeline: {pipeline.name}")

    pipe_control = await controller.control_pipeline(pipeline.id, ControlMethod.MALWARE)
    print(f"Control: {pipe_control}")

    shutdown = await controller.shutdown_pipeline(pipeline.id)
    print(f"Shutdown: {shutdown}")

    # Execute attack
    print("\n--- Attack Execution ---")
    nuke = await controller.identify_facility(
        "Nuclear Plant Alpha",
        FacilityType.NUCLEAR_PLANT,
        EnergyType.NUCLEAR,
        1200,
        "Sector 7"
    )

    attack = await controller.execute_attack(
        nuke.id,
        AttackType.SHUTDOWN,
        ControlMethod.INSIDER
    )
    print(f"Attack: {attack}")

    # Full domination
    print("\n--- FULL ENERGY DOMINATION ---")
    domination = await controller.full_energy_domination("Target Region")
    for k, v in domination.items():
        print(f"{k}: {v:,}" if isinstance(v, int) else f"{k}: {v}")

    # Stats
    print("\n--- CONTROLLER STATISTICS ---")
    stats = controller.get_stats()
    for k, v in stats.items():
        print(f"{k}: {v:,}" if isinstance(v, int) else f"{k}: {v}")

    print("\n" + "=" * 60)
    print("⚡ BA'EL CONTROLS THE POWER ⚡")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(demo())

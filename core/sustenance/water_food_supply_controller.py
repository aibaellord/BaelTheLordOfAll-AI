"""
BAEL - Water & Food Supply Controller
=======================================

THIRST. HUNGER. DEPENDENCY. CONTROL.

Complete sustenance domination:
- Water supply control
- Water treatment manipulation
- Reservoir control
- Irrigation control
- Food supply chain control
- Agricultural control
- Food processing control
- Distribution control
- Contamination capabilities
- Famine orchestration

"Survival depends on Ba'el's will."
"""

import asyncio
import logging
import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("BAEL.SUSTENANCE")


class WaterSystemType(Enum):
    """Types of water systems."""
    RESERVOIR = "reservoir"
    TREATMENT_PLANT = "treatment_plant"
    PUMPING_STATION = "pumping_station"
    DISTRIBUTION = "distribution"
    DAM = "dam"
    DESALINATION = "desalination"
    WELL = "well"
    IRRIGATION = "irrigation"


class FoodSystemType(Enum):
    """Types of food systems."""
    FARM = "farm"
    PROCESSING_PLANT = "processing_plant"
    WAREHOUSE = "warehouse"
    DISTRIBUTION_CENTER = "distribution_center"
    COLD_STORAGE = "cold_storage"
    GRAIN_SILO = "grain_silo"
    LIVESTOCK = "livestock"
    FISHERY = "fishery"


class ContaminationType(Enum):
    """Types of contamination."""
    BIOLOGICAL = "biological"
    CHEMICAL = "chemical"
    RADIOLOGICAL = "radiological"
    TOXIN = "toxin"
    PATHOGEN = "pathogen"
    PESTICIDE = "pesticide"


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


class DisruptionType(Enum):
    """Types of disruption."""
    SHORTAGE = "shortage"
    CONTAMINATION = "contamination"
    SHUTDOWN = "shutdown"
    RATIONING = "rationing"
    PRICE_SPIKE = "price_spike"
    FAMINE = "famine"


@dataclass
class WaterSystem:
    """A water system."""
    id: str
    name: str
    system_type: WaterSystemType
    capacity: float  # liters
    current_level: float
    population_served: int
    location: str
    control_level: ControlLevel = ControlLevel.NONE
    contaminated: bool = False


@dataclass
class FoodSystem:
    """A food system."""
    id: str
    name: str
    system_type: FoodSystemType
    capacity: float  # tons
    current_stock: float
    output: float  # tons per day
    location: str
    control_level: ControlLevel = ControlLevel.NONE
    contaminated: bool = False


@dataclass
class SupplyChain:
    """A supply chain."""
    id: str
    name: str
    nodes: List[str]
    daily_throughput: float
    status: str = "operational"
    disrupted: bool = False


@dataclass
class Disruption:
    """A disruption event."""
    id: str
    disruption_type: DisruptionType
    target_id: str
    impact: str
    population_affected: int
    duration_days: int


class WaterFoodSupplyController:
    """
    The water & food supply controller.

    Complete sustenance domination:
    - Water control
    - Food control
    - Supply chain manipulation
    """

    def __init__(self):
        self.water_systems: Dict[str, WaterSystem] = {}
        self.food_systems: Dict[str, FoodSystem] = {}
        self.supply_chains: Dict[str, SupplyChain] = {}
        self.disruptions: List[Disruption] = []

        self.water_controlled = 0
        self.food_controlled = 0
        self.chains_disrupted = 0
        self.population_affected = 0

        self._init_control_data()

        logger.info("WaterFoodSupplyController initialized - SURVIVAL DEPENDS ON BA'EL")

    def _gen_id(self) -> str:
        """Generate unique ID."""
        return f"wf_{int(time.time() * 1000) % 100000}_{random.randint(1000, 9999)}"

    def _init_control_data(self):
        """Initialize control data."""
        self.control_effectiveness = {
            ControlMethod.SCADA_EXPLOIT: 0.85,
            ControlMethod.NETWORK_INTRUSION: 0.75,
            ControlMethod.PHYSICAL_ACCESS: 0.90,
            ControlMethod.INSIDER: 0.95,
            ControlMethod.SUPPLY_CHAIN: 0.80,
            ControlMethod.MALWARE: 0.80
        }

        self.disruption_severity = {
            DisruptionType.SHORTAGE: 0.5,
            DisruptionType.CONTAMINATION: 0.9,
            DisruptionType.SHUTDOWN: 0.7,
            DisruptionType.RATIONING: 0.4,
            DisruptionType.PRICE_SPIKE: 0.3,
            DisruptionType.FAMINE: 1.0
        }

    # =========================================================================
    # WATER SYSTEM CONTROL
    # =========================================================================

    async def identify_water_system(
        self,
        name: str,
        system_type: WaterSystemType,
        capacity: float,
        population: int,
        location: str
    ) -> WaterSystem:
        """Identify a water system."""
        system = WaterSystem(
            id=self._gen_id(),
            name=name,
            system_type=system_type,
            capacity=capacity,
            current_level=capacity * random.uniform(0.5, 0.9),
            population_served=population,
            location=location
        )

        self.water_systems[system.id] = system

        return system

    async def control_water_system(
        self,
        system_id: str,
        method: ControlMethod
    ) -> Dict[str, Any]:
        """Take control of water system."""
        system = self.water_systems.get(system_id)
        if not system:
            return {"error": "System not found"}

        effectiveness = self.control_effectiveness.get(method, 0.5)

        if random.random() < effectiveness:
            system.control_level = ControlLevel.FULL
            self.water_controlled += 1

            return {
                "system": system.name,
                "type": system.system_type.value,
                "method": method.value,
                "success": True,
                "population": system.population_served
            }

        return {"system": system.name, "success": False}

    async def contaminate_water(
        self,
        system_id: str,
        contamination_type: ContaminationType
    ) -> Dict[str, Any]:
        """Contaminate water supply."""
        system = self.water_systems.get(system_id)
        if not system:
            return {"error": "System not found"}

        system.contaminated = True
        self.population_affected += system.population_served

        disruption = Disruption(
            id=self._gen_id(),
            disruption_type=DisruptionType.CONTAMINATION,
            target_id=system_id,
            impact=f"{contamination_type.value}_contamination",
            population_affected=system.population_served,
            duration_days=random.randint(7, 30)
        )
        self.disruptions.append(disruption)

        return {
            "system": system.name,
            "contamination": contamination_type.value,
            "population_affected": system.population_served,
            "duration_days": disruption.duration_days
        }

    async def shutdown_water(
        self,
        system_id: str
    ) -> Dict[str, Any]:
        """Shutdown water supply."""
        system = self.water_systems.get(system_id)
        if not system:
            return {"error": "System not found"}

        system.current_level = 0
        self.population_affected += system.population_served

        disruption = Disruption(
            id=self._gen_id(),
            disruption_type=DisruptionType.SHUTDOWN,
            target_id=system_id,
            impact="complete_shutdown",
            population_affected=system.population_served,
            duration_days=random.randint(1, 7)
        )
        self.disruptions.append(disruption)

        return {
            "system": system.name,
            "shutdown": True,
            "population_affected": system.population_served
        }

    async def manipulate_water_level(
        self,
        system_id: str,
        new_level: float
    ) -> Dict[str, Any]:
        """Manipulate water levels."""
        system = self.water_systems.get(system_id)
        if not system:
            return {"error": "System not found"}

        old_level = system.current_level
        system.current_level = min(new_level, system.capacity)

        return {
            "system": system.name,
            "old_level": old_level,
            "new_level": system.current_level,
            "percentage": (system.current_level / system.capacity) * 100
        }

    # =========================================================================
    # FOOD SYSTEM CONTROL
    # =========================================================================

    async def identify_food_system(
        self,
        name: str,
        system_type: FoodSystemType,
        capacity: float,
        output: float,
        location: str
    ) -> FoodSystem:
        """Identify a food system."""
        system = FoodSystem(
            id=self._gen_id(),
            name=name,
            system_type=system_type,
            capacity=capacity,
            current_stock=capacity * random.uniform(0.3, 0.8),
            output=output,
            location=location
        )

        self.food_systems[system.id] = system

        return system

    async def control_food_system(
        self,
        system_id: str,
        method: ControlMethod
    ) -> Dict[str, Any]:
        """Take control of food system."""
        system = self.food_systems.get(system_id)
        if not system:
            return {"error": "System not found"}

        effectiveness = self.control_effectiveness.get(method, 0.5)

        if random.random() < effectiveness:
            system.control_level = ControlLevel.FULL
            self.food_controlled += 1

            return {
                "system": system.name,
                "type": system.system_type.value,
                "method": method.value,
                "success": True,
                "capacity": system.capacity
            }

        return {"system": system.name, "success": False}

    async def contaminate_food(
        self,
        system_id: str,
        contamination_type: ContaminationType
    ) -> Dict[str, Any]:
        """Contaminate food supply."""
        system = self.food_systems.get(system_id)
        if not system:
            return {"error": "System not found"}

        system.contaminated = True
        affected = int(system.output * 1000)
        self.population_affected += affected

        disruption = Disruption(
            id=self._gen_id(),
            disruption_type=DisruptionType.CONTAMINATION,
            target_id=system_id,
            impact=f"{contamination_type.value}_contamination",
            population_affected=affected,
            duration_days=random.randint(7, 60)
        )
        self.disruptions.append(disruption)

        return {
            "system": system.name,
            "contamination": contamination_type.value,
            "stock_destroyed": system.current_stock,
            "population_affected": affected
        }

    async def destroy_crops(
        self,
        system_id: str
    ) -> Dict[str, Any]:
        """Destroy crops/livestock."""
        system = self.food_systems.get(system_id)
        if not system:
            return {"error": "System not found"}

        if system.system_type not in [FoodSystemType.FARM, FoodSystemType.LIVESTOCK]:
            return {"error": "Not a farm system"}

        old_output = system.output
        system.output = 0
        system.current_stock = 0

        affected = int(old_output * 5000)
        self.population_affected += affected

        return {
            "system": system.name,
            "destroyed": True,
            "output_lost": old_output,
            "population_affected": affected
        }

    async def hoard_supplies(
        self,
        system_id: str
    ) -> Dict[str, Any]:
        """Hoard food supplies."""
        system = self.food_systems.get(system_id)
        if not system:
            return {"error": "System not found"}

        if system.system_type not in [FoodSystemType.WAREHOUSE, FoodSystemType.GRAIN_SILO]:
            return {"error": "Not a storage system"}

        hoarded = system.current_stock
        system.current_stock = 0

        return {
            "system": system.name,
            "hoarded": hoarded,
            "market_impact": "price_spike"
        }

    # =========================================================================
    # SUPPLY CHAIN CONTROL
    # =========================================================================

    async def map_supply_chain(
        self,
        name: str,
        nodes: List[str],
        throughput: float
    ) -> SupplyChain:
        """Map a supply chain."""
        chain = SupplyChain(
            id=self._gen_id(),
            name=name,
            nodes=nodes,
            daily_throughput=throughput
        )

        self.supply_chains[chain.id] = chain

        return chain

    async def disrupt_supply_chain(
        self,
        chain_id: str
    ) -> Dict[str, Any]:
        """Disrupt a supply chain."""
        chain = self.supply_chains.get(chain_id)
        if not chain:
            return {"error": "Chain not found"}

        chain.disrupted = True
        chain.status = "disrupted"
        self.chains_disrupted += 1

        affected = int(chain.daily_throughput * 100)
        self.population_affected += affected

        disruption = Disruption(
            id=self._gen_id(),
            disruption_type=DisruptionType.SHORTAGE,
            target_id=chain_id,
            impact="supply_chain_breakdown",
            population_affected=affected,
            duration_days=random.randint(14, 90)
        )
        self.disruptions.append(disruption)

        return {
            "chain": chain.name,
            "disrupted": True,
            "nodes_affected": len(chain.nodes),
            "throughput_lost": chain.daily_throughput,
            "population_affected": affected
        }

    async def control_distribution(
        self,
        chain_id: str
    ) -> Dict[str, Any]:
        """Control distribution network."""
        chain = self.supply_chains.get(chain_id)
        if not chain:
            return {"error": "Chain not found"}

        chain.status = "controlled"

        return {
            "chain": chain.name,
            "controlled": True,
            "throughput": chain.daily_throughput,
            "nodes": len(chain.nodes)
        }

    # =========================================================================
    # FULL SUSTENANCE DOMINATION
    # =========================================================================

    async def cause_famine(
        self,
        region: str
    ) -> Dict[str, Any]:
        """Cause a famine in a region."""
        total_affected = 0
        systems_hit = 0

        # Destroy all food systems
        for system in self.food_systems.values():
            if system.location == region or region == "all":
                if system.system_type in [FoodSystemType.FARM, FoodSystemType.LIVESTOCK]:
                    result = await self.destroy_crops(system.id)
                else:
                    await self.contaminate_food(system.id, ContaminationType.BIOLOGICAL)
                systems_hit += 1

        # Disrupt all supply chains
        for chain in self.supply_chains.values():
            await self.disrupt_supply_chain(chain.id)

        total_affected = int(sum(s.output for s in self.food_systems.values()) * 10000)

        disruption = Disruption(
            id=self._gen_id(),
            disruption_type=DisruptionType.FAMINE,
            target_id=region,
            impact="widespread_famine",
            population_affected=total_affected,
            duration_days=random.randint(180, 365)
        )
        self.disruptions.append(disruption)

        return {
            "region": region,
            "systems_hit": systems_hit,
            "chains_disrupted": len(self.supply_chains),
            "population_affected": total_affected,
            "duration_days": disruption.duration_days
        }

    async def full_sustenance_domination(
        self,
        region: str
    ) -> Dict[str, Any]:
        """Execute full sustenance domination."""
        results = {
            "water_systems_identified": 0,
            "water_systems_controlled": 0,
            "food_systems_identified": 0,
            "food_systems_controlled": 0,
            "supply_chains_mapped": 0,
            "supply_chains_disrupted": 0,
            "contaminations": 0,
            "population_affected": 0
        }

        # Identify and control water systems
        water_types = [
            (WaterSystemType.RESERVOIR, 1000000000, 500000),
            (WaterSystemType.TREATMENT_PLANT, 500000000, 300000),
            (WaterSystemType.DAM, 5000000000, 1000000),
            (WaterSystemType.PUMPING_STATION, 100000000, 100000)
        ]

        for wt, cap, pop in water_types:
            system = await self.identify_water_system(
                f"{wt.value}_{region}",
                wt, cap, pop, region
            )
            results["water_systems_identified"] += 1

            control = await self.control_water_system(system.id, ControlMethod.SCADA_EXPLOIT)
            if control.get("success"):
                results["water_systems_controlled"] += 1

                # Contaminate some
                if random.random() < 0.5:
                    await self.contaminate_water(system.id, ContaminationType.BIOLOGICAL)
                    results["contaminations"] += 1

        # Identify and control food systems
        food_types = [
            (FoodSystemType.FARM, 10000, 500),
            (FoodSystemType.PROCESSING_PLANT, 5000, 200),
            (FoodSystemType.WAREHOUSE, 20000, 0),
            (FoodSystemType.GRAIN_SILO, 50000, 0),
            (FoodSystemType.LIVESTOCK, 8000, 300)
        ]

        food_systems = []
        for ft, cap, out in food_types:
            system = await self.identify_food_system(
                f"{ft.value}_{region}",
                ft, cap, out, region
            )
            food_systems.append(system)
            results["food_systems_identified"] += 1

            control = await self.control_food_system(system.id, ControlMethod.NETWORK_INTRUSION)
            if control.get("success"):
                results["food_systems_controlled"] += 1

                # Contaminate some
                if random.random() < 0.3:
                    await self.contaminate_food(system.id, ContaminationType.TOXIN)
                    results["contaminations"] += 1

        # Map and disrupt supply chains
        chain = await self.map_supply_chain(
            f"Food_Supply_Chain_{region}",
            [s.id for s in food_systems[:3]],
            1000
        )
        results["supply_chains_mapped"] += 1

        disrupt = await self.disrupt_supply_chain(chain.id)
        if disrupt.get("disrupted"):
            results["supply_chains_disrupted"] += 1

        results["population_affected"] = self.population_affected

        return results

    def get_stats(self) -> Dict[str, Any]:
        """Get controller statistics."""
        return {
            "water_systems": len(self.water_systems),
            "water_controlled": self.water_controlled,
            "food_systems": len(self.food_systems),
            "food_controlled": self.food_controlled,
            "supply_chains": len(self.supply_chains),
            "chains_disrupted": self.chains_disrupted,
            "disruptions": len(self.disruptions),
            "population_affected": self.population_affected
        }


# ============================================================================
# SINGLETON
# ============================================================================

_controller: Optional[WaterFoodSupplyController] = None


def get_water_food_controller() -> WaterFoodSupplyController:
    """Get the global water/food controller."""
    global _controller
    if _controller is None:
        _controller = WaterFoodSupplyController()
    return _controller


# ============================================================================
# DEMO
# ============================================================================

async def demo():
    """Demonstrate water/food control."""
    print("=" * 60)
    print("💧🍞 WATER & FOOD SUPPLY CONTROLLER 💧🍞")
    print("=" * 60)

    controller = get_water_food_controller()

    # Water system
    print("\n--- Water System Control ---")
    water = await controller.identify_water_system(
        "City Reservoir",
        WaterSystemType.RESERVOIR,
        1000000000,
        500000,
        "Metro City"
    )
    print(f"System: {water.name}")
    print(f"Capacity: {water.capacity:,.0f} liters")
    print(f"Population: {water.population_served:,}")

    control = await controller.control_water_system(water.id, ControlMethod.SCADA_EXPLOIT)
    print(f"Control: {control}")

    # Contaminate
    contam = await controller.contaminate_water(water.id, ContaminationType.BIOLOGICAL)
    print(f"Contamination: {contam}")

    # Food system
    print("\n--- Food System Control ---")
    food = await controller.identify_food_system(
        "Regional Farm",
        FoodSystemType.FARM,
        10000,
        500,
        "Agricultural Zone"
    )
    print(f"System: {food.name}")
    print(f"Capacity: {food.capacity:,.0f} tons")
    print(f"Output: {food.output} tons/day")

    food_control = await controller.control_food_system(food.id, ControlMethod.NETWORK_INTRUSION)
    print(f"Control: {food_control}")

    # Destroy crops
    destroy = await controller.destroy_crops(food.id)
    print(f"Destruction: {destroy}")

    # Supply chain
    print("\n--- Supply Chain Control ---")
    warehouse = await controller.identify_food_system(
        "Food Warehouse",
        FoodSystemType.WAREHOUSE,
        50000,
        0,
        "Distribution Zone"
    )

    chain = await controller.map_supply_chain(
        "Regional Food Chain",
        [food.id, warehouse.id],
        1000
    )
    print(f"Chain: {chain.name}")
    print(f"Nodes: {len(chain.nodes)}")

    disrupt = await controller.disrupt_supply_chain(chain.id)
    print(f"Disruption: {disrupt}")

    # Full domination
    print("\n--- FULL SUSTENANCE DOMINATION ---")
    domination = await controller.full_sustenance_domination("Target Region")
    for k, v in domination.items():
        print(f"{k}: {v:,}" if isinstance(v, int) else f"{k}: {v}")

    # Stats
    print("\n--- CONTROLLER STATISTICS ---")
    stats = controller.get_stats()
    for k, v in stats.items():
        print(f"{k}: {v:,}" if isinstance(v, int) else f"{k}: {v}")

    print("\n" + "=" * 60)
    print("💧🍞 SURVIVAL DEPENDS ON BA'EL'S WILL 💧🍞")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(demo())

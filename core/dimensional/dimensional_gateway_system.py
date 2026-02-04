"""
BAEL - Dimensional Gateway System
====================================

OPEN. TRAVERSE. CONQUER. EXPAND.

This system provides:
- Portal creation
- Dimensional mapping
- Reality bridging
- Pocket dimension creation
- Dimensional anchoring
- Multiverse navigation
- Dimensional fortress building
- Realm conquest
- Dimensional energy harvesting
- Inter-dimensional communication

"Ba'el's dominion spans all dimensions."
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

logger = logging.getLogger("BAEL.DIMENSIONAL")


class DimensionType(Enum):
    """Types of dimensions."""
    MATERIAL = "material"  # Physical reality
    ETHEREAL = "ethereal"  # Spirit realm
    ASTRAL = "astral"  # Thought realm
    VOID = "void"  # Empty space
    SHADOW = "shadow"  # Dark reflection
    ELEMENTAL = "elemental"  # Pure elements
    DIGITAL = "digital"  # Cyber realm
    QUANTUM = "quantum"  # Probability space
    POCKET = "pocket"  # Created micro-dimension
    PRIME = "prime"  # Main reality


class PortalState(Enum):
    """Portal states."""
    CLOSED = "closed"
    OPENING = "opening"
    STABLE = "stable"
    UNSTABLE = "unstable"
    COLLAPSING = "collapsing"
    LOCKED = "locked"


class PortalType(Enum):
    """Types of portals."""
    GATEWAY = "gateway"  # Two-way passage
    RIFT = "rift"  # Unstable tear
    WINDOW = "window"  # View only
    CONDUIT = "conduit"  # Energy transfer
    WORMHOLE = "wormhole"  # Shortcut
    VEIL = "veil"  # Hidden passage


class DimensionalLaw(Enum):
    """Laws governing dimensions."""
    PHYSICS_NORMAL = "physics_normal"
    PHYSICS_INVERTED = "physics_inverted"
    MAGIC_ENABLED = "magic_enabled"
    TIME_VARIABLE = "time_variable"
    THOUGHT_MANIFEST = "thought_manifest"
    CHAOS_DOMINANT = "chaos_dominant"
    ORDER_ABSOLUTE = "order_absolute"


@dataclass
class Dimension:
    """A dimension or realm."""
    id: str
    name: str
    type: DimensionType
    coordinates: Tuple[int, int, int, int]  # 4D coordinates
    laws: List[DimensionalLaw]
    stability: float
    energy_level: float
    inhabitants: int
    controlled_by: Optional[str]
    connected_portals: List[str]


@dataclass
class Portal:
    """A dimensional portal."""
    id: str
    name: str
    type: PortalType
    state: PortalState
    source_dimension: str
    target_dimension: str
    power_required: float
    traversals: int
    locked_by: Optional[str]


@dataclass
class PocketDimension:
    """A created pocket dimension."""
    id: str
    name: str
    size: float  # Cubic units
    laws: List[DimensionalLaw]
    contents: List[str]
    creator: str
    stability: float
    anchor_point: str


@dataclass
class DimensionalFortress:
    """A fortress in dimensional space."""
    id: str
    name: str
    dimension_id: str
    defenses: List[str]
    power_generators: int
    shield_strength: float
    garrison: int


@dataclass
class DimensionalHarvester:
    """An energy harvester."""
    id: str
    dimension_id: str
    harvest_rate: float
    energy_stored: float
    active: bool


class DimensionalGatewaySystem:
    """
    Dimensional gateway system.

    Features:
    - Dimension discovery
    - Portal management
    - Pocket creation
    - Fortress building
    - Energy harvesting
    """

    def __init__(self):
        self.dimensions: Dict[str, Dimension] = {}
        self.portals: Dict[str, Portal] = {}
        self.pocket_dimensions: Dict[str, PocketDimension] = {}
        self.fortresses: Dict[str, DimensionalFortress] = {}
        self.harvesters: Dict[str, DimensionalHarvester] = {}

        self.dimensional_power = 1000.0
        self.dimensions_conquered = 0
        self.portals_opened = 0

        # Initialize home dimension
        self._init_home_dimension()

        logger.info("DimensionalGatewaySystem initialized")

    def _gen_id(self, prefix: str) -> str:
        """Generate unique ID."""
        return hashlib.md5(f"{prefix}{time.time()}{random.random()}".encode()).hexdigest()[:12]

    def _init_home_dimension(self):
        """Initialize the home dimension."""
        home = Dimension(
            id="home_dimension",
            name="Ba'el's Domain",
            type=DimensionType.PRIME,
            coordinates=(0, 0, 0, 0),
            laws=[DimensionalLaw.PHYSICS_NORMAL, DimensionalLaw.ORDER_ABSOLUTE],
            stability=1.0,
            energy_level=1000.0,
            inhabitants=1,
            controlled_by="Ba'el",
            connected_portals=[]
        )
        self.dimensions[home.id] = home

    # =========================================================================
    # DIMENSION MANAGEMENT
    # =========================================================================

    async def discover_dimension(
        self,
        scan_range: int = 100
    ) -> Dimension:
        """Discover a new dimension."""
        # Generate random coordinates
        coords = (
            random.randint(-scan_range, scan_range),
            random.randint(-scan_range, scan_range),
            random.randint(-scan_range, scan_range),
            random.randint(-scan_range, scan_range)
        )

        dim_type = random.choice(list(DimensionType))
        num_laws = random.randint(1, 3)
        laws = random.sample(list(DimensionalLaw), num_laws)

        dimension = Dimension(
            id=self._gen_id("dim"),
            name=f"Dimension_{abs(hash(str(coords))) % 10000}",
            type=dim_type,
            coordinates=coords,
            laws=laws,
            stability=random.uniform(0.3, 1.0),
            energy_level=random.uniform(100, 10000),
            inhabitants=random.randint(0, 1000000),
            controlled_by=None,
            connected_portals=[]
        )

        self.dimensions[dimension.id] = dimension

        logger.info(f"Dimension discovered: {dimension.name}")

        return dimension

    async def scan_dimension(
        self,
        dimension_id: str
    ) -> Dict[str, Any]:
        """Scan a dimension for details."""
        dimension = self.dimensions.get(dimension_id)
        if not dimension:
            return {"error": "Dimension not found"}

        return {
            "name": dimension.name,
            "type": dimension.type.value,
            "coordinates": dimension.coordinates,
            "laws": [l.value for l in dimension.laws],
            "stability": dimension.stability,
            "energy_level": dimension.energy_level,
            "inhabitants": dimension.inhabitants,
            "controlled_by": dimension.controlled_by,
            "threat_level": "high" if dimension.inhabitants > 10000 else "low"
        }

    async def claim_dimension(
        self,
        dimension_id: str
    ) -> Dict[str, Any]:
        """Claim control of a dimension."""
        dimension = self.dimensions.get(dimension_id)
        if not dimension:
            return {"error": "Dimension not found"}

        if dimension.controlled_by:
            return {"error": f"Already controlled by {dimension.controlled_by}"}

        # Claim requires power
        power_needed = dimension.inhabitants * 0.01
        if power_needed > self.dimensional_power:
            return {"error": "Insufficient dimensional power"}

        dimension.controlled_by = "Ba'el"
        self.dimensional_power -= power_needed
        self.dimensions_conquered += 1

        logger.info(f"Dimension claimed: {dimension.name}")

        return {
            "success": True,
            "dimension": dimension.name,
            "inhabitants_subjugated": dimension.inhabitants,
            "dimensions_conquered": self.dimensions_conquered
        }

    # =========================================================================
    # PORTAL MANAGEMENT
    # =========================================================================

    async def open_portal(
        self,
        name: str,
        source_id: str,
        target_id: str,
        portal_type: PortalType = PortalType.GATEWAY
    ) -> Portal:
        """Open a portal between dimensions."""
        source = self.dimensions.get(source_id)
        target = self.dimensions.get(target_id)

        if not source or not target:
            raise ValueError("Source or target dimension not found")

        # Calculate power requirement based on distance
        distance = math.sqrt(sum(
            (a - b) ** 2
            for a, b in zip(source.coordinates, target.coordinates)
        ))
        power_required = distance * 10

        if power_required > self.dimensional_power:
            raise ValueError("Insufficient dimensional power")

        portal = Portal(
            id=self._gen_id("portal"),
            name=name,
            type=portal_type,
            state=PortalState.OPENING,
            source_dimension=source_id,
            target_dimension=target_id,
            power_required=power_required,
            traversals=0,
            locked_by=None
        )

        # Stabilize
        portal.state = PortalState.STABLE

        self.portals[portal.id] = portal
        source.connected_portals.append(portal.id)
        target.connected_portals.append(portal.id)

        self.dimensional_power -= power_required
        self.portals_opened += 1

        logger.info(f"Portal opened: {name}")

        return portal

    async def stabilize_portal(
        self,
        portal_id: str
    ) -> Dict[str, Any]:
        """Stabilize an unstable portal."""
        portal = self.portals.get(portal_id)
        if not portal:
            return {"error": "Portal not found"}

        if portal.state == PortalState.STABLE:
            return {"success": True, "message": "Already stable"}

        portal.state = PortalState.STABLE
        self.dimensional_power -= 50

        return {
            "success": True,
            "portal": portal.name,
            "state": "STABLE"
        }

    async def lock_portal(
        self,
        portal_id: str,
        key: str
    ) -> Dict[str, Any]:
        """Lock a portal with a key."""
        portal = self.portals.get(portal_id)
        if not portal:
            return {"error": "Portal not found"}

        portal.state = PortalState.LOCKED
        portal.locked_by = hashlib.sha256(key.encode()).hexdigest()

        return {
            "success": True,
            "portal": portal.name,
            "locked": True
        }

    async def traverse_portal(
        self,
        portal_id: str,
        entity_count: int = 1
    ) -> Dict[str, Any]:
        """Traverse through a portal."""
        portal = self.portals.get(portal_id)
        if not portal:
            return {"error": "Portal not found"}

        if portal.state == PortalState.LOCKED:
            return {"error": "Portal is locked"}

        if portal.state != PortalState.STABLE:
            return {"error": f"Portal is {portal.state.value}"}

        portal.traversals += entity_count

        source = self.dimensions.get(portal.source_dimension)
        target = self.dimensions.get(portal.target_dimension)

        return {
            "success": True,
            "from": source.name if source else "Unknown",
            "to": target.name if target else "Unknown",
            "entities_traversed": entity_count,
            "total_traversals": portal.traversals
        }

    async def close_portal(
        self,
        portal_id: str
    ) -> Dict[str, Any]:
        """Close a portal."""
        portal = self.portals.get(portal_id)
        if not portal:
            return {"error": "Portal not found"}

        portal.state = PortalState.COLLAPSING

        # Remove from dimensions
        for dim_id in [portal.source_dimension, portal.target_dimension]:
            dim = self.dimensions.get(dim_id)
            if dim and portal_id in dim.connected_portals:
                dim.connected_portals.remove(portal_id)

        portal.state = PortalState.CLOSED

        return {
            "success": True,
            "portal": portal.name,
            "state": "CLOSED",
            "total_traversals": portal.traversals
        }

    # =========================================================================
    # POCKET DIMENSIONS
    # =========================================================================

    async def create_pocket_dimension(
        self,
        name: str,
        size: float,
        laws: List[DimensionalLaw]
    ) -> PocketDimension:
        """Create a pocket dimension."""
        power_cost = size * 10
        if power_cost > self.dimensional_power:
            raise ValueError("Insufficient power to create pocket dimension")

        pocket = PocketDimension(
            id=self._gen_id("pocket"),
            name=name,
            size=size,
            laws=laws,
            contents=[],
            creator="Ba'el",
            stability=0.9,
            anchor_point="home_dimension"
        )

        self.pocket_dimensions[pocket.id] = pocket
        self.dimensional_power -= power_cost

        logger.info(f"Pocket dimension created: {name}")

        return pocket

    async def store_in_pocket(
        self,
        pocket_id: str,
        items: List[str]
    ) -> Dict[str, Any]:
        """Store items in a pocket dimension."""
        pocket = self.pocket_dimensions.get(pocket_id)
        if not pocket:
            return {"error": "Pocket dimension not found"}

        current_items = len(pocket.contents)
        capacity = pocket.size * 100

        storable = min(len(items), int(capacity - current_items))
        pocket.contents.extend(items[:storable])

        return {
            "success": True,
            "stored": storable,
            "rejected": len(items) - storable,
            "total_contents": len(pocket.contents),
            "capacity": capacity
        }

    async def retrieve_from_pocket(
        self,
        pocket_id: str,
        item_count: int
    ) -> Dict[str, Any]:
        """Retrieve items from a pocket dimension."""
        pocket = self.pocket_dimensions.get(pocket_id)
        if not pocket:
            return {"error": "Pocket dimension not found"}

        retrieved = pocket.contents[:item_count]
        pocket.contents = pocket.contents[item_count:]

        return {
            "success": True,
            "retrieved": retrieved,
            "remaining": len(pocket.contents)
        }

    async def expand_pocket(
        self,
        pocket_id: str,
        additional_size: float
    ) -> Dict[str, Any]:
        """Expand a pocket dimension."""
        pocket = self.pocket_dimensions.get(pocket_id)
        if not pocket:
            return {"error": "Pocket dimension not found"}

        power_cost = additional_size * 10
        if power_cost > self.dimensional_power:
            return {"error": "Insufficient power"}

        old_size = pocket.size
        pocket.size += additional_size
        self.dimensional_power -= power_cost

        return {
            "success": True,
            "old_size": old_size,
            "new_size": pocket.size
        }

    # =========================================================================
    # DIMENSIONAL FORTRESSES
    # =========================================================================

    async def build_fortress(
        self,
        name: str,
        dimension_id: str
    ) -> DimensionalFortress:
        """Build a dimensional fortress."""
        dimension = self.dimensions.get(dimension_id)
        if not dimension:
            raise ValueError("Dimension not found")

        if dimension.controlled_by != "Ba'el":
            raise ValueError("Must control dimension to build fortress")

        fortress = DimensionalFortress(
            id=self._gen_id("fortress"),
            name=name,
            dimension_id=dimension_id,
            defenses=["dimensional_barrier", "reality_anchor", "void_moat"],
            power_generators=1,
            shield_strength=100.0,
            garrison=100
        )

        self.fortresses[fortress.id] = fortress
        self.dimensional_power -= 500

        logger.info(f"Fortress built: {name}")

        return fortress

    async def upgrade_fortress(
        self,
        fortress_id: str,
        upgrade_type: str
    ) -> Dict[str, Any]:
        """Upgrade a fortress."""
        fortress = self.fortresses.get(fortress_id)
        if not fortress:
            return {"error": "Fortress not found"}

        upgrades = {
            "power": lambda f: setattr(f, 'power_generators', f.power_generators + 1),
            "shields": lambda f: setattr(f, 'shield_strength', f.shield_strength + 50),
            "garrison": lambda f: setattr(f, 'garrison', f.garrison + 100),
            "defense": lambda f: f.defenses.append(f"defense_{len(f.defenses) + 1}")
        }

        if upgrade_type in upgrades:
            upgrades[upgrade_type](fortress)
            self.dimensional_power -= 100

            return {
                "success": True,
                "upgrade": upgrade_type,
                "fortress": fortress.name
            }

        return {"error": "Unknown upgrade type"}

    # =========================================================================
    # ENERGY HARVESTING
    # =========================================================================

    async def deploy_harvester(
        self,
        dimension_id: str
    ) -> DimensionalHarvester:
        """Deploy an energy harvester in a dimension."""
        dimension = self.dimensions.get(dimension_id)
        if not dimension:
            raise ValueError("Dimension not found")

        if dimension.controlled_by != "Ba'el":
            raise ValueError("Must control dimension to harvest")

        harvest_rate = dimension.energy_level * 0.01

        harvester = DimensionalHarvester(
            id=self._gen_id("harvester"),
            dimension_id=dimension_id,
            harvest_rate=harvest_rate,
            energy_stored=0.0,
            active=True
        )

        self.harvesters[harvester.id] = harvester

        logger.info(f"Harvester deployed in {dimension.name}")

        return harvester

    async def collect_energy(
        self,
        harvester_id: str
    ) -> Dict[str, Any]:
        """Collect harvested energy."""
        harvester = self.harvesters.get(harvester_id)
        if not harvester:
            return {"error": "Harvester not found"}

        if not harvester.active:
            return {"error": "Harvester is inactive"}

        # Simulate harvesting over time
        harvested = harvester.harvest_rate * random.uniform(0.8, 1.2)
        harvester.energy_stored += harvested

        return {
            "success": True,
            "harvested": harvested,
            "stored": harvester.energy_stored
        }

    async def transfer_energy(
        self,
        harvester_id: str
    ) -> Dict[str, Any]:
        """Transfer stored energy to main pool."""
        harvester = self.harvesters.get(harvester_id)
        if not harvester:
            return {"error": "Harvester not found"}

        transferred = harvester.energy_stored
        self.dimensional_power += transferred
        harvester.energy_stored = 0.0

        return {
            "success": True,
            "transferred": transferred,
            "total_power": self.dimensional_power
        }

    # =========================================================================
    # STATS
    # =========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get dimensional gateway stats."""
        return {
            "dimensions_known": len(self.dimensions),
            "dimensions_conquered": self.dimensions_conquered,
            "active_portals": len([p for p in self.portals.values()
                                   if p.state == PortalState.STABLE]),
            "pocket_dimensions": len(self.pocket_dimensions),
            "fortresses": len(self.fortresses),
            "harvesters": len(self.harvesters),
            "dimensional_power": self.dimensional_power,
            "portals_opened": self.portals_opened
        }


# ============================================================================
# SINGLETON
# ============================================================================

_system: Optional[DimensionalGatewaySystem] = None


def get_dimensional_gateway() -> DimensionalGatewaySystem:
    """Get global dimensional gateway system."""
    global _system
    if _system is None:
        _system = DimensionalGatewaySystem()
    return _system


# ============================================================================
# DEMO
# ============================================================================

async def demo():
    """Demonstrate dimensional gateway system."""
    print("=" * 60)
    print("🌀 DIMENSIONAL GATEWAY SYSTEM 🌀")
    print("=" * 60)

    system = get_dimensional_gateway()

    # Discover dimensions
    print("\n--- Dimension Discovery ---")
    for _ in range(3):
        dim = await system.discover_dimension(1000)
        scan = await system.scan_dimension(dim.id)
        print(f"Discovered: {scan['name']} ({scan['type']})")
        print(f"  Inhabitants: {scan['inhabitants']}, Energy: {scan['energy_level']:.0f}")

    # Claim a dimension
    print("\n--- Dimension Conquest ---")
    dimensions = list(system.dimensions.values())
    for dim in dimensions[1:]:  # Skip home dimension
        result = await system.claim_dimension(dim.id)
        if result.get("success"):
            print(f"Claimed: {dim.name}")

    # Open portals
    print("\n--- Portal Network ---")
    home = system.dimensions.get("home_dimension")
    claimed = [d for d in system.dimensions.values() if d.controlled_by == "Ba'el" and d.id != "home_dimension"]

    if claimed:
        portal = await system.open_portal(
            "Conquest Gateway",
            "home_dimension",
            claimed[0].id,
            PortalType.GATEWAY
        )
        print(f"Portal opened: {portal.name}")

        traverse = await system.traverse_portal(portal.id, 100)
        print(f"Traversed: {traverse['entities_traversed']} to {traverse['to']}")

    # Create pocket dimension
    print("\n--- Pocket Dimensions ---")
    pocket = await system.create_pocket_dimension(
        "Ba'el's Vault",
        100.0,
        [DimensionalLaw.ORDER_ABSOLUTE, DimensionalLaw.TIME_VARIABLE]
    )
    print(f"Created: {pocket.name} (size: {pocket.size})")

    store_result = await system.store_in_pocket(
        pocket.id,
        ["artifact_1", "artifact_2", "conquered_soul_1", "secret_knowledge"]
    )
    print(f"Stored: {store_result['stored']} items")

    # Build fortress
    print("\n--- Dimensional Fortress ---")
    if claimed:
        fortress = await system.build_fortress("Citadel of Dominion", claimed[0].id)
        print(f"Fortress: {fortress.name}")
        print(f"  Defenses: {fortress.defenses}")
        print(f"  Shield: {fortress.shield_strength}")

    # Deploy harvester
    print("\n--- Energy Harvesting ---")
    if claimed:
        harvester = await system.deploy_harvester(claimed[0].id)
        print(f"Harvester deployed (rate: {harvester.harvest_rate:.1f}/cycle)")

        for _ in range(3):
            await system.collect_energy(harvester.id)

        transfer = await system.transfer_energy(harvester.id)
        print(f"Energy transferred: {transfer['transferred']:.1f}")

    # Stats
    print("\n--- Dimensional Statistics ---")
    stats = system.get_stats()
    for k, v in stats.items():
        print(f"{k}: {v}")

    print("\n" + "=" * 60)
    print("🌀 DIMENSIONS ARE CONNECTED 🌀")


if __name__ == "__main__":
    asyncio.run(demo())

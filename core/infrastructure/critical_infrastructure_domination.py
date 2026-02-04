"""
BAEL - Critical Infrastructure Domination System
=================================================

INFILTRATE. CONTROL. LEVERAGE. DESTROY.

Ultimate infrastructure control:
- Power grid control
- Water systems
- Transportation
- Communications
- Financial systems
- Healthcare networks
- Industrial control
- Emergency services
- Nuclear facilities
- Military systems

"All infrastructure bends to Ba'el's will."
"""

import asyncio
import logging
import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("BAEL.INFRASTRUCTURE")


class InfrastructureType(Enum):
    """Types of critical infrastructure."""
    POWER_GRID = "power_grid"
    WATER_SYSTEM = "water_system"
    GAS_PIPELINE = "gas_pipeline"
    TRANSPORTATION = "transportation"
    COMMUNICATIONS = "communications"
    FINANCIAL = "financial"
    HEALTHCARE = "healthcare"
    EMERGENCY = "emergency_services"
    NUCLEAR = "nuclear"
    MILITARY = "military"
    INDUSTRIAL = "industrial"
    GOVERNMENT = "government"


class ControlSystemType(Enum):
    """Types of control systems."""
    SCADA = "scada"
    DCS = "distributed_control"
    PLC = "plc"
    HMI = "human_machine_interface"
    RTU = "remote_terminal_unit"
    IED = "intelligent_electronic_device"
    ICS = "industrial_control_system"
    BMS = "building_management"


class AttackMethod(Enum):
    """Attack methods for infrastructure."""
    NETWORK_INTRUSION = "network_intrusion"
    FIRMWARE_EXPLOIT = "firmware_exploit"
    PROTOCOL_ABUSE = "protocol_abuse"
    INSIDER_ACCESS = "insider_access"
    PHYSICAL_ACCESS = "physical_access"
    SUPPLY_CHAIN = "supply_chain"
    ZERO_DAY = "zero_day"
    SOCIAL_ENGINEERING = "social_engineering"


class ImpactLevel(Enum):
    """Impact levels of attacks."""
    MINIMAL = "minimal"
    MODERATE = "moderate"
    SIGNIFICANT = "significant"
    SEVERE = "severe"
    CATASTROPHIC = "catastrophic"


class OperationalState(Enum):
    """Operational states."""
    NORMAL = "normal"
    DEGRADED = "degraded"
    COMPROMISED = "compromised"
    CONTROLLED = "controlled"
    DISABLED = "disabled"
    DESTROYED = "destroyed"


@dataclass
class Infrastructure:
    """A critical infrastructure target."""
    id: str
    name: str
    infra_type: InfrastructureType
    location: str
    population_served: int
    control_systems: List[ControlSystemType]
    security_level: float  # 0-1
    state: OperationalState = OperationalState.NORMAL
    access_level: str = "none"


@dataclass
class ControlSystem:
    """An industrial control system."""
    id: str
    name: str
    system_type: ControlSystemType
    vendor: str
    version: str
    vulnerabilities: List[str]
    compromised: bool = False


@dataclass
class Attack:
    """An infrastructure attack."""
    id: str
    target: str
    method: AttackMethod
    impact: ImpactLevel
    start_time: datetime
    duration_hours: float
    success: bool
    casualties_potential: int


@dataclass
class Outage:
    """A service outage."""
    id: str
    infrastructure_id: str
    cause: str
    affected_population: int
    duration_hours: float
    economic_damage: float


class CriticalInfrastructureDominationSystem:
    """
    The critical infrastructure domination system.

    Master of all infrastructure:
    - Power grid control
    - Water system manipulation
    - Transportation disruption
    - Communications blackout
    """

    def __init__(self):
        self.infrastructure: Dict[str, Infrastructure] = {}
        self.control_systems: Dict[str, ControlSystem] = {}
        self.attacks: List[Attack] = []
        self.outages: List[Outage] = []

        self.systems_compromised = 0
        self.infrastructure_controlled = 0
        self.total_affected_population = 0
        self.total_economic_damage = 0.0

        self._init_targets()

        logger.info("CriticalInfrastructureDominationSystem initialized - ALL SYSTEMS VULNERABLE")

    def _gen_id(self) -> str:
        """Generate unique ID."""
        return f"infra_{int(time.time() * 1000) % 100000}_{random.randint(1000, 9999)}"

    def _init_targets(self):
        """Initialize infrastructure targets."""
        targets = [
            ("Eastern Grid", InfrastructureType.POWER_GRID, "East Coast", 80000000),
            ("Western Grid", InfrastructureType.POWER_GRID, "West Coast", 50000000),
            ("Metro Water Authority", InfrastructureType.WATER_SYSTEM, "Metro Area", 5000000),
            ("Continental Pipeline", InfrastructureType.GAS_PIPELINE, "Nationwide", 100000000),
            ("National Rail", InfrastructureType.TRANSPORTATION, "Nationwide", 30000000),
            ("TeleCorp Network", InfrastructureType.COMMUNICATIONS, "Nationwide", 150000000),
            ("Federal Reserve System", InfrastructureType.FINANCIAL, "Nationwide", 330000000),
            ("Major Hospital Network", InfrastructureType.HEALTHCARE, "Multi-State", 10000000),
            ("911 Emergency System", InfrastructureType.EMERGENCY, "Multi-State", 20000000),
            ("Power Plant Alpha", InfrastructureType.NUCLEAR, "Midwest", 5000000)
        ]

        for name, infra_type, location, population in targets:
            infra = Infrastructure(
                id=self._gen_id(),
                name=name,
                infra_type=infra_type,
                location=location,
                population_served=population,
                control_systems=[ControlSystemType.SCADA, ControlSystemType.PLC],
                security_level=random.uniform(0.4, 0.8)
            )
            self.infrastructure[infra.id] = infra

        # Initialize control systems
        vendors = ["Siemens", "Schneider", "ABB", "Honeywell", "GE", "Rockwell"]
        for infra in self.infrastructure.values():
            for cs_type in infra.control_systems:
                cs = ControlSystem(
                    id=self._gen_id(),
                    name=f"{infra.name}_{cs_type.value}",
                    system_type=cs_type,
                    vendor=random.choice(vendors),
                    version=f"{random.randint(1, 5)}.{random.randint(0, 9)}",
                    vulnerabilities=[f"CVE-2023-{random.randint(1000, 9999)}" for _ in range(random.randint(1, 5))]
                )
                self.control_systems[cs.id] = cs

    # =========================================================================
    # RECONNAISSANCE
    # =========================================================================

    async def scan_infrastructure(
        self,
        target_type: Optional[InfrastructureType] = None
    ) -> List[Infrastructure]:
        """Scan for infrastructure targets."""
        targets = []

        for infra in self.infrastructure.values():
            if target_type and infra.infra_type != target_type:
                continue
            targets.append(infra)

        return targets

    async def identify_control_systems(
        self,
        infra_id: str
    ) -> Dict[str, Any]:
        """Identify control systems in infrastructure."""
        infra = self.infrastructure.get(infra_id)
        if not infra:
            return {"error": "Infrastructure not found"}

        systems = [cs for cs in self.control_systems.values() if infra.name in cs.name]

        return {
            "infrastructure": infra.name,
            "control_systems": [
                {
                    "id": cs.id,
                    "type": cs.system_type.value,
                    "vendor": cs.vendor,
                    "version": cs.version,
                    "vulnerabilities": len(cs.vulnerabilities)
                }
                for cs in systems
            ],
            "security_level": infra.security_level
        }

    async def enumerate_vulnerabilities(
        self,
        infra_id: str
    ) -> Dict[str, Any]:
        """Enumerate vulnerabilities in infrastructure."""
        infra = self.infrastructure.get(infra_id)
        if not infra:
            return {"error": "Infrastructure not found"}

        vuln_types = [
            "Default credentials",
            "Unpatched firmware",
            "Protocol weaknesses",
            "Network exposure",
            "Insider threats",
            "Physical access gaps",
            "Supply chain risks"
        ]

        return {
            "infrastructure": infra.name,
            "vulnerabilities": random.sample(vuln_types, random.randint(2, 5)),
            "critical_vulns": random.randint(1, 10),
            "exploitation_difficulty": 1 - infra.security_level,
            "attack_surface": "large" if len(infra.control_systems) > 2 else "medium"
        }

    # =========================================================================
    # INFILTRATION
    # =========================================================================

    async def infiltrate_network(
        self,
        infra_id: str,
        method: AttackMethod
    ) -> Dict[str, Any]:
        """Infiltrate infrastructure network."""
        infra = self.infrastructure.get(infra_id)
        if not infra:
            return {"error": "Infrastructure not found"}

        success_factors = {
            AttackMethod.NETWORK_INTRUSION: 0.6,
            AttackMethod.ZERO_DAY: 0.9,
            AttackMethod.INSIDER_ACCESS: 0.85,
            AttackMethod.SOCIAL_ENGINEERING: 0.7,
            AttackMethod.SUPPLY_CHAIN: 0.75,
            AttackMethod.PHYSICAL_ACCESS: 0.8
        }

        base_success = success_factors.get(method, 0.5)
        success_prob = base_success * (1 - infra.security_level)
        success = random.random() < success_prob

        if success:
            infra.state = OperationalState.COMPROMISED
            infra.access_level = "network"
            self.systems_compromised += 1

        return {
            "infrastructure": infra.name,
            "method": method.value,
            "success": success,
            "access_level": infra.access_level if success else "none",
            "detection_risk": infra.security_level
        }

    async def compromise_control_system(
        self,
        cs_id: str
    ) -> Dict[str, Any]:
        """Compromise a control system."""
        cs = self.control_systems.get(cs_id)
        if not cs:
            return {"error": "Control system not found"}

        success = len(cs.vulnerabilities) > 0 and random.random() > 0.2

        if success:
            cs.compromised = True

        return {
            "control_system": cs.name,
            "type": cs.system_type.value,
            "vendor": cs.vendor,
            "success": success,
            "exploited_vulns": cs.vulnerabilities[:2] if success else [],
            "control_gained": success
        }

    async def escalate_access(
        self,
        infra_id: str
    ) -> Dict[str, Any]:
        """Escalate access within infrastructure."""
        infra = self.infrastructure.get(infra_id)
        if not infra:
            return {"error": "Infrastructure not found"}

        if infra.access_level == "none":
            return {"error": "No initial access"}

        access_levels = ["network", "operator", "engineer", "admin", "root", "physical"]
        current_idx = access_levels.index(infra.access_level) if infra.access_level in access_levels else 0

        if current_idx < len(access_levels) - 1:
            infra.access_level = access_levels[current_idx + 1]

        if infra.access_level in ["admin", "root", "physical"]:
            infra.state = OperationalState.CONTROLLED
            self.infrastructure_controlled += 1

        return {
            "infrastructure": infra.name,
            "previous_access": access_levels[current_idx],
            "new_access": infra.access_level,
            "full_control": infra.state == OperationalState.CONTROLLED
        }

    # =========================================================================
    # POWER GRID ATTACKS
    # =========================================================================

    async def attack_power_grid(
        self,
        infra_id: str,
        attack_type: str
    ) -> Dict[str, Any]:
        """Attack power grid infrastructure."""
        infra = self.infrastructure.get(infra_id)
        if not infra or infra.infra_type != InfrastructureType.POWER_GRID:
            return {"error": "Power grid not found"}

        attack_types = {
            "load_manipulation": {
                "description": "Manipulate load balancing to cause instability",
                "impact": ImpactLevel.SEVERE,
                "blackout_probability": 0.6
            },
            "relay_protection": {
                "description": "Disable relay protection systems",
                "impact": ImpactLevel.CATASTROPHIC,
                "blackout_probability": 0.8
            },
            "generation_attack": {
                "description": "Attack power generation facilities",
                "impact": ImpactLevel.CATASTROPHIC,
                "blackout_probability": 0.7
            },
            "transmission_attack": {
                "description": "Attack transmission infrastructure",
                "impact": ImpactLevel.SEVERE,
                "blackout_probability": 0.5
            },
            "cascading_failure": {
                "description": "Trigger cascading failures across grid",
                "impact": ImpactLevel.CATASTROPHIC,
                "blackout_probability": 0.9
            }
        }

        attack_info = attack_types.get(attack_type, attack_types["load_manipulation"])
        blackout = random.random() < attack_info["blackout_probability"]

        if blackout:
            infra.state = OperationalState.DISABLED
            self.total_affected_population += infra.population_served

            outage = Outage(
                id=self._gen_id(),
                infrastructure_id=infra_id,
                cause=attack_type,
                affected_population=infra.population_served,
                duration_hours=random.uniform(2, 72),
                economic_damage=infra.population_served * random.uniform(10, 100)
            )
            self.outages.append(outage)
            self.total_economic_damage += outage.economic_damage

        return {
            "infrastructure": infra.name,
            "attack_type": attack_type,
            "description": attack_info["description"],
            "impact": attack_info["impact"].value,
            "blackout_occurred": blackout,
            "population_affected": infra.population_served if blackout else 0,
            "estimated_restoration_hours": random.uniform(2, 72) if blackout else 0
        }

    # =========================================================================
    # WATER SYSTEM ATTACKS
    # =========================================================================

    async def attack_water_system(
        self,
        infra_id: str,
        attack_type: str
    ) -> Dict[str, Any]:
        """Attack water system infrastructure."""
        infra = self.infrastructure.get(infra_id)
        if not infra or infra.infra_type != InfrastructureType.WATER_SYSTEM:
            return {"error": "Water system not found"}

        attack_types = {
            "chemical_manipulation": {
                "description": "Alter chemical treatment levels",
                "impact": ImpactLevel.CATASTROPHIC,
                "health_risk": True
            },
            "pressure_manipulation": {
                "description": "Cause dangerous pressure fluctuations",
                "impact": ImpactLevel.SEVERE,
                "health_risk": False
            },
            "pump_control": {
                "description": "Take control of pump systems",
                "impact": ImpactLevel.SIGNIFICANT,
                "health_risk": False
            },
            "contamination": {
                "description": "Introduce contaminants into supply",
                "impact": ImpactLevel.CATASTROPHIC,
                "health_risk": True
            }
        }

        attack_info = attack_types.get(attack_type, attack_types["pump_control"])

        casualties = 0
        if attack_info["health_risk"]:
            casualties = int(infra.population_served * random.uniform(0.001, 0.01))

        return {
            "infrastructure": infra.name,
            "attack_type": attack_type,
            "description": attack_info["description"],
            "impact": attack_info["impact"].value,
            "health_risk": attack_info["health_risk"],
            "potential_casualties": casualties,
            "population_at_risk": infra.population_served
        }

    # =========================================================================
    # TRANSPORTATION ATTACKS
    # =========================================================================

    async def attack_transportation(
        self,
        infra_id: str,
        target: str
    ) -> Dict[str, Any]:
        """Attack transportation infrastructure."""
        infra = self.infrastructure.get(infra_id)
        if not infra or infra.infra_type != InfrastructureType.TRANSPORTATION:
            return {"error": "Transportation system not found"}

        targets = {
            "signaling": {
                "description": "Attack railway signaling systems",
                "derailment_risk": 0.4
            },
            "traffic_control": {
                "description": "Attack air traffic control",
                "collision_risk": 0.2
            },
            "navigation": {
                "description": "Attack navigation systems",
                "accident_risk": 0.3
            },
            "scheduling": {
                "description": "Attack scheduling systems",
                "disruption_level": 0.8
            }
        }

        target_info = targets.get(target, targets["scheduling"])

        return {
            "infrastructure": infra.name,
            "target": target,
            "description": target_info["description"],
            "accident_risk": target_info.get("derailment_risk") or target_info.get("collision_risk") or target_info.get("accident_risk", 0),
            "disruption_level": target_info.get("disruption_level", 0.5),
            "passengers_affected": infra.population_served // 365  # Daily passengers
        }

    # =========================================================================
    # FINANCIAL ATTACKS
    # =========================================================================

    async def attack_financial(
        self,
        infra_id: str,
        attack_type: str
    ) -> Dict[str, Any]:
        """Attack financial infrastructure."""
        infra = self.infrastructure.get(infra_id)
        if not infra or infra.infra_type != InfrastructureType.FINANCIAL:
            return {"error": "Financial system not found"}

        attack_types = {
            "swift_manipulation": {
                "description": "Manipulate SWIFT transfers",
                "potential_theft": random.uniform(1e6, 1e9)
            },
            "trading_disruption": {
                "description": "Disrupt trading systems",
                "market_impact": random.uniform(0.01, 0.05)
            },
            "atm_network": {
                "description": "Attack ATM network",
                "potential_theft": random.uniform(1e5, 1e7)
            },
            "ledger_manipulation": {
                "description": "Manipulate transaction ledgers",
                "potential_theft": random.uniform(1e7, 1e10)
            }
        }

        attack_info = attack_types.get(attack_type, attack_types["swift_manipulation"])

        return {
            "infrastructure": infra.name,
            "attack_type": attack_type,
            "description": attack_info["description"],
            "potential_theft": attack_info.get("potential_theft", 0),
            "market_impact": attack_info.get("market_impact", 0),
            "economic_damage_potential": random.uniform(1e8, 1e12)
        }

    # =========================================================================
    # NUCLEAR FACILITY ATTACKS
    # =========================================================================

    async def attack_nuclear(
        self,
        infra_id: str,
        attack_type: str
    ) -> Dict[str, Any]:
        """Attack nuclear facility."""
        infra = self.infrastructure.get(infra_id)
        if not infra or infra.infra_type != InfrastructureType.NUCLEAR:
            return {"error": "Nuclear facility not found"}

        attack_types = {
            "cooling_system": {
                "description": "Attack cooling system controls",
                "meltdown_risk": 0.3,
                "impact": ImpactLevel.CATASTROPHIC
            },
            "control_rods": {
                "description": "Manipulate control rod systems",
                "meltdown_risk": 0.4,
                "impact": ImpactLevel.CATASTROPHIC
            },
            "safety_systems": {
                "description": "Disable safety monitoring",
                "meltdown_risk": 0.2,
                "impact": ImpactLevel.SEVERE
            },
            "centrifuges": {
                "description": "Attack enrichment centrifuges",
                "meltdown_risk": 0.1,
                "impact": ImpactLevel.SIGNIFICANT
            }
        }

        attack_info = attack_types.get(attack_type, attack_types["safety_systems"])

        return {
            "infrastructure": infra.name,
            "attack_type": attack_type,
            "description": attack_info["description"],
            "meltdown_risk": attack_info["meltdown_risk"],
            "impact": attack_info["impact"].value,
            "evacuation_radius_km": 50 if attack_info["meltdown_risk"] > 0.2 else 10,
            "population_at_risk": infra.population_served
        }

    # =========================================================================
    # CASCADING EFFECTS
    # =========================================================================

    async def trigger_cascade(
        self,
        initial_target: str
    ) -> Dict[str, Any]:
        """Trigger cascading infrastructure failures."""
        initial = self.infrastructure.get(initial_target)
        if not initial:
            return {"error": "Infrastructure not found"}

        # Simulate cascade
        cascade_map = {
            InfrastructureType.POWER_GRID: [
                InfrastructureType.WATER_SYSTEM,
                InfrastructureType.COMMUNICATIONS,
                InfrastructureType.HEALTHCARE,
                InfrastructureType.FINANCIAL
            ],
            InfrastructureType.WATER_SYSTEM: [
                InfrastructureType.HEALTHCARE,
                InfrastructureType.INDUSTRIAL
            ],
            InfrastructureType.COMMUNICATIONS: [
                InfrastructureType.FINANCIAL,
                InfrastructureType.EMERGENCY,
                InfrastructureType.TRANSPORTATION
            ]
        }

        affected_systems = []
        cascade_targets = cascade_map.get(initial.infra_type, [])

        for infra in self.infrastructure.values():
            if infra.infra_type in cascade_targets:
                infra.state = OperationalState.DEGRADED
                affected_systems.append(infra.name)
                self.total_affected_population += infra.population_served

        return {
            "initial_target": initial.name,
            "cascade_triggered": True,
            "affected_systems": affected_systems,
            "total_systems_affected": len(affected_systems) + 1,
            "total_population_affected": sum(
                inf.population_served for inf in self.infrastructure.values()
                if inf.state in [OperationalState.DEGRADED, OperationalState.DISABLED]
            )
        }

    # =========================================================================
    # STATS
    # =========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get system statistics."""
        return {
            "infrastructure_tracked": len(self.infrastructure),
            "control_systems_tracked": len(self.control_systems),
            "systems_compromised": self.systems_compromised,
            "infrastructure_controlled": self.infrastructure_controlled,
            "attacks_conducted": len(self.attacks),
            "outages_caused": len(self.outages),
            "total_affected_population": self.total_affected_population,
            "total_economic_damage": self.total_economic_damage
        }


# ============================================================================
# SINGLETON
# ============================================================================

_system: Optional[CriticalInfrastructureDominationSystem] = None


def get_infrastructure_system() -> CriticalInfrastructureDominationSystem:
    """Get the global infrastructure system."""
    global _system
    if _system is None:
        _system = CriticalInfrastructureDominationSystem()
    return _system


# ============================================================================
# DEMO
# ============================================================================

async def demo():
    """Demonstrate infrastructure domination."""
    print("=" * 60)
    print("🏭 CRITICAL INFRASTRUCTURE DOMINATION 🏭")
    print("=" * 60)

    system = get_infrastructure_system()

    # Scan infrastructure
    print("\n--- Infrastructure Scan ---")
    all_infra = await system.scan_infrastructure()
    print(f"Infrastructure targets: {len(all_infra)}")
    for infra in all_infra[:5]:
        print(f"  {infra.name}: {infra.population_served:,} served")

    # Identify control systems
    print("\n--- Control System Identification ---")
    power_grid = [i for i in all_infra if i.infra_type == InfrastructureType.POWER_GRID][0]
    cs_info = await system.identify_control_systems(power_grid.id)
    print(f"Infrastructure: {cs_info['infrastructure']}")
    for cs in cs_info['control_systems'][:3]:
        print(f"  {cs['type']}: {cs['vendor']} v{cs['version']}, {cs['vulnerabilities']} vulns")

    # Enumerate vulnerabilities
    print("\n--- Vulnerability Enumeration ---")
    vulns = await system.enumerate_vulnerabilities(power_grid.id)
    print(f"Critical vulns: {vulns['critical_vulns']}")
    print(f"Attack surface: {vulns['attack_surface']}")

    # Infiltrate
    print("\n--- Network Infiltration ---")
    infiltration = await system.infiltrate_network(power_grid.id, AttackMethod.ZERO_DAY)
    print(f"Success: {infiltration['success']}")
    print(f"Access level: {infiltration['access_level']}")

    # Escalate
    if infiltration['success']:
        print("\n--- Access Escalation ---")
        for _ in range(3):
            escalation = await system.escalate_access(power_grid.id)
            print(f"Escalated to: {escalation['new_access']}")
            if escalation.get('full_control'):
                print("FULL CONTROL ACHIEVED!")
                break

    # Power grid attack
    print("\n--- Power Grid Attack ---")
    grid_attack = await system.attack_power_grid(power_grid.id, "cascading_failure")
    print(f"Attack type: {grid_attack['attack_type']}")
    print(f"Blackout: {grid_attack['blackout_occurred']}")
    if grid_attack['blackout_occurred']:
        print(f"Population affected: {grid_attack['population_affected']:,}")

    # Water system attack
    print("\n--- Water System Attack ---")
    water = [i for i in all_infra if i.infra_type == InfrastructureType.WATER_SYSTEM][0]
    water_attack = await system.attack_water_system(water.id, "chemical_manipulation")
    print(f"Health risk: {water_attack['health_risk']}")
    print(f"Potential casualties: {water_attack['potential_casualties']}")

    # Financial attack
    print("\n--- Financial System Attack ---")
    financial = [i for i in all_infra if i.infra_type == InfrastructureType.FINANCIAL][0]
    fin_attack = await system.attack_financial(financial.id, "ledger_manipulation")
    print(f"Potential theft: ${fin_attack['potential_theft']:,.0f}")

    # Nuclear attack
    print("\n--- Nuclear Facility Attack ---")
    nuclear = [i for i in all_infra if i.infra_type == InfrastructureType.NUCLEAR][0]
    nuke_attack = await system.attack_nuclear(nuclear.id, "cooling_system")
    print(f"Meltdown risk: {nuke_attack['meltdown_risk']:.1%}")
    print(f"Evacuation radius: {nuke_attack['evacuation_radius_km']} km")

    # Cascade
    print("\n--- Cascading Failure ---")
    cascade = await system.trigger_cascade(power_grid.id)
    print(f"Systems affected: {cascade['total_systems_affected']}")
    print(f"Population affected: {cascade['total_population_affected']:,}")

    # Stats
    print("\n--- SYSTEM STATISTICS ---")
    stats = system.get_stats()
    for k, v in stats.items():
        if isinstance(v, float):
            print(f"{k}: ${v:,.0f}")
        elif isinstance(v, int) and v > 10000:
            print(f"{k}: {v:,}")
        else:
            print(f"{k}: {v}")

    print("\n" + "=" * 60)
    print("🏭 ALL INFRASTRUCTURE BENDS TO BA'EL 🏭")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(demo())

"""
BAEL - Supply Chain Attack Framework
=====================================

INFILTRATE. COMPROMISE. DISTRIBUTE. PERSIST.

Ultimate supply chain domination:
- Vendor compromise
- Software poisoning
- Hardware implants
- Dependency injection
- Build system infection
- Package tampering
- Update hijacking
- Certificate theft
- Code signing abuse
- Distribution infection

"Every link in the chain belongs to Ba'el."
"""

import asyncio
import hashlib
import logging
import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("BAEL.SUPPLYCHAIN")


class AttackVector(Enum):
    """Supply chain attack vectors."""
    VENDOR_COMPROMISE = "vendor_compromise"
    SOURCE_CODE = "source_code"
    BUILD_SYSTEM = "build_system"
    DEPENDENCY = "dependency"
    PACKAGE_MANAGER = "package_manager"
    UPDATE_MECHANISM = "update_mechanism"
    DISTRIBUTION = "distribution"
    HARDWARE = "hardware"
    FIRMWARE = "firmware"
    CERTIFICATE = "certificate"


class TargetType(Enum):
    """Types of supply chain targets."""
    SOFTWARE_VENDOR = "software_vendor"
    HARDWARE_VENDOR = "hardware_vendor"
    CLOUD_PROVIDER = "cloud_provider"
    PACKAGE_REPO = "package_repository"
    CDN = "cdn"
    CI_CD_SYSTEM = "ci_cd_system"
    CODE_REPOSITORY = "code_repository"
    CERTIFICATE_AUTHORITY = "certificate_authority"
    UPDATE_SERVER = "update_server"
    BUILD_SERVER = "build_server"


class PayloadType(Enum):
    """Types of malicious payloads."""
    BACKDOOR = "backdoor"
    RAT = "remote_access_trojan"
    CRYPTO_MINER = "crypto_miner"
    DATA_EXFILTRATOR = "data_exfiltrator"
    RANSOMWARE = "ransomware"
    BOTNET_AGENT = "botnet_agent"
    KEYLOGGER = "keylogger"
    CREDENTIAL_STEALER = "credential_stealer"
    WORM = "worm"
    LOGIC_BOMB = "logic_bomb"


class PersistenceLevel(Enum):
    """Levels of persistence."""
    VOLATILE = "volatile"
    USER_LEVEL = "user_level"
    SYSTEM_LEVEL = "system_level"
    FIRMWARE = "firmware"
    HARDWARE = "hardware"


class CompromiseStatus(Enum):
    """Status of compromise."""
    IDENTIFIED = "identified"
    INFILTRATED = "infiltrated"
    IMPLANTED = "implanted"
    ACTIVE = "active"
    DISTRIBUTING = "distributing"
    DETECTED = "detected"


@dataclass
class Vendor:
    """A supply chain vendor."""
    id: str
    name: str
    target_type: TargetType
    customers: int
    security_score: float  # 0-1, lower is more vulnerable
    compromised: bool = False
    compromise_date: Optional[datetime] = None


@dataclass
class Software:
    """A software package."""
    id: str
    name: str
    version: str
    vendor_id: str
    downloads: int
    dependencies: List[str]
    signed: bool
    infected: bool = False
    payload_type: Optional[PayloadType] = None


@dataclass
class Dependency:
    """A software dependency."""
    id: str
    name: str
    version: str
    downloads: int
    maintainers: int
    compromised: bool = False


@dataclass
class BuildSystem:
    """A CI/CD build system."""
    id: str
    name: str
    platform: str
    projects: int
    compromised: bool = False
    access_level: str = "none"


@dataclass
class Implant:
    """A hardware/firmware implant."""
    id: str
    name: str
    target_device: str
    persistence: PersistenceLevel
    capabilities: List[str]
    detection_rate: float


@dataclass
class Attack:
    """A supply chain attack."""
    id: str
    vector: AttackVector
    target: str
    payload: PayloadType
    status: CompromiseStatus
    start_time: datetime
    victims: int = 0
    detection_risk: float = 0.1


class SupplyChainAttackFramework:
    """
    The supply chain attack framework.

    Master of supply chain compromise:
    - Vendor infiltration
    - Software poisoning
    - Hardware implants
    - Distribution hijacking
    """

    def __init__(self):
        self.vendors: Dict[str, Vendor] = {}
        self.software: Dict[str, Software] = {}
        self.dependencies: Dict[str, Dependency] = {}
        self.build_systems: Dict[str, BuildSystem] = {}
        self.implants: Dict[str, Implant] = {}
        self.attacks: Dict[str, Attack] = {}

        self.vendors_compromised = 0
        self.packages_infected = 0
        self.dependencies_poisoned = 0
        self.total_victims = 0

        self._init_targets()

        logger.info("SupplyChainAttackFramework initialized - CHAIN COMPROMISED")

    def _gen_id(self) -> str:
        """Generate unique ID."""
        return hashlib.md5(f"{time.time()}{random.random()}".encode()).hexdigest()[:10]

    def _init_targets(self):
        """Initialize potential targets."""
        vendors = [
            ("SolarTech", TargetType.SOFTWARE_VENDOR, 50000, 0.6),
            ("CloudCore", TargetType.CLOUD_PROVIDER, 100000, 0.7),
            ("NPM Registry", TargetType.PACKAGE_REPO, 5000000, 0.65),
            ("PyPI", TargetType.PACKAGE_REPO, 3000000, 0.6),
            ("GitHub Actions", TargetType.CI_CD_SYSTEM, 10000000, 0.8),
            ("DigiCert", TargetType.CERTIFICATE_AUTHORITY, 1000000, 0.85),
            ("ChipMaker", TargetType.HARDWARE_VENDOR, 200000, 0.55),
            ("UpdateCorp", TargetType.UPDATE_SERVER, 80000, 0.5)
        ]

        for name, target_type, customers, security in vendors:
            vendor = Vendor(
                id=self._gen_id(),
                name=name,
                target_type=target_type,
                customers=customers,
                security_score=security
            )
            self.vendors[vendor.id] = vendor

        deps = [
            ("lodash", "4.17.21", 50000000, 5),
            ("requests", "2.28.0", 30000000, 10),
            ("axios", "1.4.0", 40000000, 8),
            ("moment", "2.29.4", 25000000, 6),
            ("log4j", "2.17.0", 10000000, 3)
        ]

        for name, version, downloads, maintainers in deps:
            dep = Dependency(
                id=self._gen_id(),
                name=name,
                version=version,
                downloads=downloads,
                maintainers=maintainers
            )
            self.dependencies[dep.id] = dep

    # =========================================================================
    # VENDOR COMPROMISE
    # =========================================================================

    async def identify_vendor(
        self,
        name: str,
        target_type: TargetType,
        customers: int
    ) -> Vendor:
        """Identify a vendor for targeting."""
        vendor = Vendor(
            id=self._gen_id(),
            name=name,
            target_type=target_type,
            customers=customers,
            security_score=random.uniform(0.3, 0.8)
        )

        self.vendors[vendor.id] = vendor

        return vendor

    async def compromise_vendor(
        self,
        vendor_id: str,
        method: str = "phishing"
    ) -> Dict[str, Any]:
        """Compromise a vendor."""
        vendor = self.vendors.get(vendor_id)
        if not vendor:
            return {"error": "Vendor not found"}

        methods = {
            "phishing": 0.7,
            "zero_day": 0.9,
            "insider": 0.8,
            "credential_stuffing": 0.5,
            "watering_hole": 0.6
        }

        success_prob = methods.get(method, 0.5) * (1 - vendor.security_score)
        success = random.random() < success_prob

        if success:
            vendor.compromised = True
            vendor.compromise_date = datetime.now()
            self.vendors_compromised += 1

        return {
            "vendor": vendor.name,
            "method": method,
            "success": success,
            "security_score": vendor.security_score,
            "customer_exposure": vendor.customers if success else 0
        }

    async def maintain_access(
        self,
        vendor_id: str
    ) -> Dict[str, Any]:
        """Maintain persistent access to vendor."""
        vendor = self.vendors.get(vendor_id)
        if not vendor or not vendor.compromised:
            return {"error": "Vendor not compromised"}

        access_methods = [
            "Multiple backdoors installed",
            "Legitimate credentials harvested",
            "Service account compromised",
            "SSH keys extracted",
            "VPN access established",
            "Admin accounts created"
        ]

        return {
            "vendor": vendor.name,
            "access_maintained": True,
            "methods": random.sample(access_methods, random.randint(2, 4)),
            "detection_risk": random.uniform(0.05, 0.2)
        }

    # =========================================================================
    # SOFTWARE POISONING
    # =========================================================================

    async def inject_payload(
        self,
        software_name: str,
        version: str,
        payload: PayloadType
    ) -> Software:
        """Inject malicious payload into software."""
        software = Software(
            id=self._gen_id(),
            name=software_name,
            version=version,
            vendor_id=random.choice(list(self.vendors.keys())) if self.vendors else "",
            downloads=random.randint(10000, 10000000),
            dependencies=[],
            signed=True,
            infected=True,
            payload_type=payload
        )

        self.software[software.id] = software
        self.packages_infected += 1

        return software

    async def poison_update(
        self,
        software_id: str,
        payload: PayloadType
    ) -> Dict[str, Any]:
        """Poison software update mechanism."""
        software = self.software.get(software_id)
        if not software:
            software = await self.inject_payload(f"software_{software_id}", "1.0.0", payload)

        return {
            "software": software.name,
            "version": software.version,
            "update_poisoned": True,
            "payload": payload.value,
            "estimated_victims": software.downloads,
            "auto_update_enabled": random.random() > 0.3
        }

    async def hijack_distribution(
        self,
        software_id: str,
        cdn_name: str
    ) -> Dict[str, Any]:
        """Hijack software distribution."""
        software = self.software.get(software_id)
        if not software:
            return {"error": "Software not found"}

        return {
            "software": software.name,
            "cdn": cdn_name,
            "distribution_hijacked": True,
            "legitimate_hash": hashlib.sha256(software.name.encode()).hexdigest(),
            "malicious_hash": hashlib.sha256(f"{software.name}_infected".encode()).hexdigest(),
            "hash_collision_attack": random.random() > 0.7
        }

    async def sign_malicious(
        self,
        software_id: str,
        stolen_cert: str
    ) -> Dict[str, Any]:
        """Sign malicious software with stolen certificate."""
        software = self.software.get(software_id)
        if not software:
            return {"error": "Software not found"}

        software.signed = True

        return {
            "software": software.name,
            "certificate": stolen_cert,
            "signing_successful": True,
            "verification_passes": True,
            "certificate_valid_until": (datetime.now() + timedelta(days=random.randint(30, 365))).isoformat()
        }

    # =========================================================================
    # DEPENDENCY ATTACKS
    # =========================================================================

    async def compromise_dependency(
        self,
        dep_id: str,
        method: str = "typosquatting"
    ) -> Dict[str, Any]:
        """Compromise a software dependency."""
        dep = self.dependencies.get(dep_id)
        if not dep:
            return {"error": "Dependency not found"}

        methods = {
            "typosquatting": "Created similar package name",
            "maintainer_takeover": "Compromised maintainer account",
            "malicious_pr": "Injected code via pull request",
            "abandoned_takeover": "Took over abandoned package",
            "version_injection": "Published malicious version"
        }

        dep.compromised = True
        self.dependencies_poisoned += 1
        self.total_victims += dep.downloads

        return {
            "dependency": dep.name,
            "version": dep.version,
            "method": method,
            "description": methods.get(method, "Unknown method"),
            "downloads_affected": dep.downloads,
            "downstream_projects": dep.downloads // 1000
        }

    async def create_typosquat(
        self,
        original_name: str,
        typosquat_name: str,
        payload: PayloadType
    ) -> Dict[str, Any]:
        """Create typosquatting package."""
        dep = Dependency(
            id=self._gen_id(),
            name=typosquat_name,
            version="1.0.0",
            downloads=0,
            maintainers=1,
            compromised=True
        )

        self.dependencies[dep.id] = dep

        return {
            "original": original_name,
            "typosquat": typosquat_name,
            "payload": payload.value,
            "published": True,
            "detection_risk": 0.3,
            "confusion_techniques": [
                "Similar name",
                "Same description",
                "Copied README",
                "Fake download stats"
            ]
        }

    async def dependency_confusion(
        self,
        internal_name: str,
        target_org: str
    ) -> Dict[str, Any]:
        """Execute dependency confusion attack."""
        # Create public package with same name as internal
        public_version = "9999.0.0"  # Higher version to be preferred

        return {
            "internal_package": internal_name,
            "target_organization": target_org,
            "public_package_created": True,
            "version": public_version,
            "attack_type": "dependency_confusion",
            "exploitation": "Package manager prefers public high version",
            "success_probability": 0.8
        }

    # =========================================================================
    # BUILD SYSTEM ATTACKS
    # =========================================================================

    async def compromise_build_system(
        self,
        name: str,
        platform: str
    ) -> BuildSystem:
        """Compromise a CI/CD build system."""
        build_system = BuildSystem(
            id=self._gen_id(),
            name=name,
            platform=platform,
            projects=random.randint(100, 10000),
            compromised=True,
            access_level="admin"
        )

        self.build_systems[build_system.id] = build_system

        return build_system

    async def inject_into_pipeline(
        self,
        build_id: str,
        stage: str,
        payload: str
    ) -> Dict[str, Any]:
        """Inject code into build pipeline."""
        build_system = self.build_systems.get(build_id)
        if not build_system:
            return {"error": "Build system not found"}

        return {
            "build_system": build_system.name,
            "stage": stage,
            "payload_injected": True,
            "affected_projects": build_system.projects,
            "persistence": "Every build includes payload",
            "detection_evasion": [
                "Injected in obfuscated form",
                "Only activates in production builds",
                "Excludes test environments"
            ]
        }

    async def steal_secrets(
        self,
        build_id: str
    ) -> Dict[str, Any]:
        """Steal secrets from build system."""
        build_system = self.build_systems.get(build_id)
        if not build_system:
            return {"error": "Build system not found"}

        secrets = [
            "API keys",
            "SSH private keys",
            "Cloud credentials",
            "Database passwords",
            "Signing certificates",
            "OAuth tokens",
            "Service accounts"
        ]

        return {
            "build_system": build_system.name,
            "secrets_stolen": random.sample(secrets, random.randint(3, 6)),
            "environment_variables_extracted": random.randint(50, 200),
            "credential_count": random.randint(10, 50)
        }

    # =========================================================================
    # HARDWARE ATTACKS
    # =========================================================================

    async def create_hardware_implant(
        self,
        name: str,
        target_device: str,
        capabilities: List[str]
    ) -> Implant:
        """Create hardware implant design."""
        implant = Implant(
            id=self._gen_id(),
            name=name,
            target_device=target_device,
            persistence=PersistenceLevel.HARDWARE,
            capabilities=capabilities,
            detection_rate=random.uniform(0.01, 0.1)
        )

        self.implants[implant.id] = implant

        return implant

    async def deploy_firmware_implant(
        self,
        target_device: str,
        payload: PayloadType
    ) -> Dict[str, Any]:
        """Deploy firmware-level implant."""
        implant = await self.create_hardware_implant(
            f"FW_{target_device}",
            target_device,
            ["Persistence", "Data exfiltration", "Command execution"]
        )

        return {
            "device": target_device,
            "implant_id": implant.id,
            "persistence_level": PersistenceLevel.FIRMWARE.value,
            "survives_reinstall": True,
            "survives_factory_reset": True,
            "capabilities": implant.capabilities,
            "detection_rate": implant.detection_rate
        }

    async def compromise_manufacturing(
        self,
        vendor_id: str,
        implant_id: str
    ) -> Dict[str, Any]:
        """Compromise manufacturing to insert implants."""
        vendor = self.vendors.get(vendor_id)
        implant = self.implants.get(implant_id)

        if not vendor or not implant:
            return {"error": "Vendor or implant not found"}

        units_affected = random.randint(10000, 1000000)

        return {
            "vendor": vendor.name,
            "implant": implant.name,
            "manufacturing_compromised": True,
            "units_affected": units_affected,
            "shipments_worldwide": True,
            "detection_probability": 0.001
        }

    # =========================================================================
    # ATTACK ORCHESTRATION
    # =========================================================================

    async def launch_attack(
        self,
        vector: AttackVector,
        target: str,
        payload: PayloadType
    ) -> Attack:
        """Launch a supply chain attack."""
        attack = Attack(
            id=self._gen_id(),
            vector=vector,
            target=target,
            payload=payload,
            status=CompromiseStatus.INFILTRATED,
            start_time=datetime.now(),
            detection_risk=random.uniform(0.05, 0.3)
        )

        self.attacks[attack.id] = attack

        return attack

    async def propagate_attack(
        self,
        attack_id: str
    ) -> Dict[str, Any]:
        """Propagate attack through supply chain."""
        attack = self.attacks.get(attack_id)
        if not attack:
            return {"error": "Attack not found"}

        attack.status = CompromiseStatus.DISTRIBUTING

        # Calculate propagation
        initial_victims = random.randint(1000, 100000)
        secondary_victims = int(initial_victims * random.uniform(2, 10))
        tertiary_victims = int(secondary_victims * random.uniform(1.5, 5))

        attack.victims = initial_victims + secondary_victims + tertiary_victims
        self.total_victims += attack.victims

        return {
            "attack_id": attack_id,
            "initial_victims": initial_victims,
            "secondary_victims": secondary_victims,
            "tertiary_victims": tertiary_victims,
            "total_victims": attack.victims,
            "propagation_complete": True
        }

    async def evaluate_impact(
        self,
        attack_id: str
    ) -> Dict[str, Any]:
        """Evaluate attack impact."""
        attack = self.attacks.get(attack_id)
        if not attack:
            return {"error": "Attack not found"}

        impact_categories = {
            PayloadType.BACKDOOR: {"control": 0.9, "stealth": 0.8},
            PayloadType.RAT: {"control": 0.95, "stealth": 0.6},
            PayloadType.CRYPTO_MINER: {"control": 0.3, "revenue": 0.7},
            PayloadType.DATA_EXFILTRATOR: {"intel": 0.95, "stealth": 0.7},
            PayloadType.RANSOMWARE: {"disruption": 0.95, "revenue": 0.8},
            PayloadType.BOTNET_AGENT: {"control": 0.7, "scale": 0.9}
        }

        impact = impact_categories.get(attack.payload, {"general": 0.5})

        return {
            "attack_id": attack_id,
            "vector": attack.vector.value,
            "payload": attack.payload.value,
            "victims": attack.victims,
            "impact_scores": impact,
            "estimated_damages": attack.victims * random.randint(100, 10000),
            "detection_risk": attack.detection_risk
        }

    # =========================================================================
    # STATS
    # =========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get framework statistics."""
        return {
            "vendors_tracked": len(self.vendors),
            "vendors_compromised": self.vendors_compromised,
            "software_packages": len(self.software),
            "packages_infected": self.packages_infected,
            "dependencies_tracked": len(self.dependencies),
            "dependencies_poisoned": self.dependencies_poisoned,
            "build_systems_compromised": len([b for b in self.build_systems.values() if b.compromised]),
            "implants_created": len(self.implants),
            "active_attacks": len(self.attacks),
            "total_victims": self.total_victims
        }


# ============================================================================
# SINGLETON
# ============================================================================

_framework: Optional[SupplyChainAttackFramework] = None


def get_supply_chain_framework() -> SupplyChainAttackFramework:
    """Get the global supply chain framework."""
    global _framework
    if _framework is None:
        _framework = SupplyChainAttackFramework()
    return _framework


# ============================================================================
# DEMO
# ============================================================================

async def demo():
    """Demonstrate supply chain attacks."""
    print("=" * 60)
    print("🔗 SUPPLY CHAIN ATTACK FRAMEWORK 🔗")
    print("=" * 60)

    framework = get_supply_chain_framework()

    # List vendors
    print("\n--- Target Vendors ---")
    for vendor in list(framework.vendors.values())[:5]:
        print(f"  {vendor.name}: {vendor.customers} customers, security: {vendor.security_score:.2f}")

    # Compromise vendor
    print("\n--- Vendor Compromise ---")
    vendor = list(framework.vendors.values())[0]
    compromise = await framework.compromise_vendor(vendor.id, "zero_day")
    print(f"Vendor: {compromise['vendor']}")
    print(f"Success: {compromise['success']}")
    if compromise['success']:
        print(f"Exposed customers: {compromise['customer_exposure']}")

    # Maintain access
    if compromise['success']:
        access = await framework.maintain_access(vendor.id)
        print(f"Access methods: {access['methods']}")

    # Software poisoning
    print("\n--- Software Poisoning ---")
    software = await framework.inject_payload("CoolApp", "2.0.0", PayloadType.BACKDOOR)
    print(f"Infected: {software.name} v{software.version}")
    print(f"Payload: {software.payload_type.value}")

    # Poison update
    update = await framework.poison_update(software.id, PayloadType.RAT)
    print(f"Update poisoned, estimated victims: {update['estimated_victims']}")

    # Dependency attack
    print("\n--- Dependency Attacks ---")
    dep = list(framework.dependencies.values())[0]
    dep_attack = await framework.compromise_dependency(dep.id, "maintainer_takeover")
    print(f"Dependency: {dep_attack['dependency']}")
    print(f"Downloads affected: {dep_attack['downloads_affected']}")

    # Typosquatting
    typosquat = await framework.create_typosquat("lodash", "lodahs", PayloadType.CREDENTIAL_STEALER)
    print(f"Typosquat created: {typosquat['typosquat']}")

    # Dependency confusion
    confusion = await framework.dependency_confusion("internal-auth", "TargetCorp")
    print(f"Confusion attack: {confusion['attack_type']}")
    print(f"Success probability: {confusion['success_probability']}")

    # Build system
    print("\n--- Build System Compromise ---")
    build = await framework.compromise_build_system("Jenkins-Prod", "Jenkins")
    print(f"Build system: {build.name}")
    print(f"Projects affected: {build.projects}")

    pipeline = await framework.inject_into_pipeline(build.id, "deploy", "exec payload")
    print(f"Pipeline injected: {pipeline['persistence']}")

    secrets = await framework.steal_secrets(build.id)
    print(f"Secrets stolen: {secrets['secrets_stolen']}")

    # Hardware
    print("\n--- Hardware Implants ---")
    firmware = await framework.deploy_firmware_implant("NetworkSwitch", PayloadType.BACKDOOR)
    print(f"Device: {firmware['device']}")
    print(f"Survives reinstall: {firmware['survives_reinstall']}")
    print(f"Detection rate: {firmware['detection_rate']:.2%}")

    # Launch attack
    print("\n--- Full Attack Launch ---")
    attack = await framework.launch_attack(
        AttackVector.VENDOR_COMPROMISE,
        "MajorVendor",
        PayloadType.DATA_EXFILTRATOR
    )
    print(f"Attack launched: {attack.id}")

    propagation = await framework.propagate_attack(attack.id)
    print(f"Total victims: {propagation['total_victims']}")

    impact = await framework.evaluate_impact(attack.id)
    print(f"Estimated damages: ${impact['estimated_damages']:,}")

    # Stats
    print("\n--- FRAMEWORK STATISTICS ---")
    stats = framework.get_stats()
    for k, v in stats.items():
        print(f"{k}: {v}")

    print("\n" + "=" * 60)
    print("🔗 EVERY LINK IN THE CHAIN BELONGS TO BA'EL 🔗")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(demo())

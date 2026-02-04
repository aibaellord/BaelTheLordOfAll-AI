"""
BAEL - Physical Security Bypass Engine
=======================================

INFILTRATE. BYPASS. PENETRATE. DOMINATE.

Complete physical security domination:
- Lock picking and bypass
- Access control exploitation
- Biometric spoofing
- Alarm system defeat
- CCTV manipulation
- Sensor evasion
- Door bypass
- Safe cracking
- Vault penetration
- Guard manipulation

"No barrier stands before Ba'el."
"""

import asyncio
import logging
import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("BAEL.PHYSICAL")


class BarrierType(Enum):
    """Types of physical barriers."""
    DOOR = "door"
    GATE = "gate"
    TURNSTILE = "turnstile"
    FENCE = "fence"
    WALL = "wall"
    WINDOW = "window"
    VAULT = "vault"
    SAFE = "safe"
    CAGE = "cage"
    MANHOLE = "manhole"


class LockType(Enum):
    """Types of locks."""
    PIN_TUMBLER = "pin_tumbler"
    WAFER = "wafer"
    DISC_DETAINER = "disc_detainer"
    LEVER = "lever"
    WARDED = "warded"
    COMBINATION = "combination"
    ELECTRONIC = "electronic"
    MAGNETIC = "magnetic"
    BIOMETRIC = "biometric"
    SMART = "smart"


class BiometricType(Enum):
    """Types of biometric systems."""
    FINGERPRINT = "fingerprint"
    FACIAL = "facial"
    IRIS = "iris"
    RETINAL = "retinal"
    VOICE = "voice"
    PALM = "palm"
    VEIN = "vein"
    GAIT = "gait"


class AlarmType(Enum):
    """Types of alarm systems."""
    MOTION = "motion"
    INFRARED = "infrared"
    ULTRASONIC = "ultrasonic"
    MICROWAVE = "microwave"
    MAGNETIC = "magnetic"
    VIBRATION = "vibration"
    GLASS_BREAK = "glass_break"
    PRESSURE = "pressure"
    LASER = "laser"
    THERMAL = "thermal"


class SensorType(Enum):
    """Types of sensors."""
    PIR = "pir"
    INFRARED = "infrared"
    ACOUSTIC = "acoustic"
    SEISMIC = "seismic"
    PRESSURE = "pressure"
    CAPACITIVE = "capacitive"
    WEIGHT = "weight"
    PROXIMITY = "proximity"


class BypassMethod(Enum):
    """Methods for bypassing security."""
    LOCKPICK = "lockpick"
    BUMP_KEY = "bump_key"
    SHIM = "shim"
    BYPASS_TOOL = "bypass_tool"
    DECODE = "decode"
    IMPRESSIONING = "impressioning"
    DRILLING = "drilling"
    CUTTING = "cutting"
    CLONING = "cloning"
    REPLAY = "replay"
    SPOOFING = "spoofing"
    JAMMING = "jamming"


class SecurityLevel(Enum):
    """Security levels."""
    MINIMAL = "minimal"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    MAXIMUM = "maximum"
    MILITARY = "military"


class BypassStatus(Enum):
    """Status of bypass attempt."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    DETECTED = "detected"


@dataclass
class Lock:
    """A lock to bypass."""
    id: str
    lock_type: LockType
    security_level: SecurityLevel
    pins: int = 5
    bypassed: bool = False


@dataclass
class Barrier:
    """A physical barrier."""
    id: str
    name: str
    barrier_type: BarrierType
    lock: Optional[Lock] = None
    alarm: Optional[str] = None
    security_level: SecurityLevel = SecurityLevel.MEDIUM
    bypassed: bool = False


@dataclass
class AlarmSystem:
    """An alarm system."""
    id: str
    name: str
    alarm_type: AlarmType
    sensors: List[str]
    security_level: SecurityLevel
    armed: bool = True
    defeated: bool = False


@dataclass
class BiometricSystem:
    """A biometric system."""
    id: str
    name: str
    biometric_type: BiometricType
    security_level: SecurityLevel
    spoofed: bool = False


@dataclass
class CCTVSystem:
    """CCTV surveillance system."""
    id: str
    name: str
    cameras: int
    recording: bool = True
    compromised: bool = False


@dataclass
class BypassResult:
    """Result of a bypass attempt."""
    id: str
    target_id: str
    target_type: str
    method: BypassMethod
    status: BypassStatus
    time_taken: float
    detected: bool


class PhysicalSecurityBypassEngine:
    """
    The physical security bypass engine.

    Complete physical security domination:
    - Lock bypass
    - Alarm defeat
    - Biometric spoofing
    - Sensor evasion
    """

    def __init__(self):
        self.locks: Dict[str, Lock] = {}
        self.barriers: Dict[str, Barrier] = {}
        self.alarms: Dict[str, AlarmSystem] = {}
        self.biometrics: Dict[str, BiometricSystem] = {}
        self.cctv: Dict[str, CCTVSystem] = {}
        self.sensors: Dict[str, Dict[str, Any]] = {}
        self.bypass_results: List[BypassResult] = []

        self.locks_bypassed = 0
        self.barriers_penetrated = 0
        self.alarms_defeated = 0
        self.biometrics_spoofed = 0
        self.cctv_compromised = 0

        self._init_bypass_techniques()

        logger.info("PhysicalSecurityBypassEngine initialized - NO BARRIER STANDS")

    def _gen_id(self) -> str:
        """Generate unique ID."""
        return f"phy_{int(time.time() * 1000) % 100000}_{random.randint(1000, 9999)}"

    def _init_bypass_techniques(self):
        """Initialize bypass technique database."""
        self.lock_techniques = {
            LockType.PIN_TUMBLER: {
                "methods": [BypassMethod.LOCKPICK, BypassMethod.BUMP_KEY, BypassMethod.IMPRESSIONING],
                "difficulty": 0.4,
                "time": 30
            },
            LockType.WAFER: {
                "methods": [BypassMethod.LOCKPICK, BypassMethod.SHIM],
                "difficulty": 0.3,
                "time": 20
            },
            LockType.DISC_DETAINER: {
                "methods": [BypassMethod.DECODE, BypassMethod.BYPASS_TOOL],
                "difficulty": 0.7,
                "time": 120
            },
            LockType.ELECTRONIC: {
                "methods": [BypassMethod.CLONING, BypassMethod.REPLAY, BypassMethod.BYPASS_TOOL],
                "difficulty": 0.6,
                "time": 60
            },
            LockType.MAGNETIC: {
                "methods": [BypassMethod.CLONING, BypassMethod.SPOOFING],
                "difficulty": 0.3,
                "time": 15
            },
            LockType.BIOMETRIC: {
                "methods": [BypassMethod.SPOOFING, BypassMethod.BYPASS_TOOL],
                "difficulty": 0.8,
                "time": 300
            },
            LockType.SMART: {
                "methods": [BypassMethod.REPLAY, BypassMethod.JAMMING, BypassMethod.CLONING],
                "difficulty": 0.65,
                "time": 90
            },
            LockType.COMBINATION: {
                "methods": [BypassMethod.DECODE, BypassMethod.BYPASS_TOOL],
                "difficulty": 0.75,
                "time": 180
            }
        }

        self.alarm_defeat_methods = {
            AlarmType.MOTION: {"jamming": 0.7, "spoofing": 0.6, "evasion": 0.5},
            AlarmType.INFRARED: {"jamming": 0.6, "spoofing": 0.7, "thermal_mask": 0.8},
            AlarmType.ULTRASONIC: {"jamming": 0.8, "absorption": 0.6},
            AlarmType.MICROWAVE: {"shielding": 0.5, "jamming": 0.7},
            AlarmType.MAGNETIC: {"spoofing": 0.9, "bypass": 0.8},
            AlarmType.VIBRATION: {"damping": 0.6, "slow_approach": 0.7},
            AlarmType.GLASS_BREAK: {"coating": 0.5, "cutting": 0.8},
            AlarmType.PRESSURE: {"weight_distribution": 0.6, "bypassing": 0.7},
            AlarmType.LASER: {"mirror_redirect": 0.4, "smoke": 0.6, "timing": 0.5},
            AlarmType.THERMAL: {"thermal_masking": 0.7, "cooling": 0.6}
        }

    # =========================================================================
    # LOCK BYPASS
    # =========================================================================

    async def add_lock(
        self,
        lock_type: LockType,
        security_level: SecurityLevel,
        pins: int = 5
    ) -> Lock:
        """Add a lock to target."""
        lock = Lock(
            id=self._gen_id(),
            lock_type=lock_type,
            security_level=security_level,
            pins=pins
        )

        self.locks[lock.id] = lock

        return lock

    async def bypass_lock(
        self,
        lock_id: str,
        method: Optional[BypassMethod] = None
    ) -> BypassResult:
        """Bypass a lock."""
        lock = self.locks.get(lock_id)
        if not lock:
            raise ValueError("Lock not found")

        technique = self.lock_techniques.get(lock.lock_type, {
            "methods": [BypassMethod.BYPASS_TOOL],
            "difficulty": 0.5,
            "time": 60
        })

        if method is None:
            method = random.choice(technique["methods"])

        # Calculate success
        security_modifier = {
            SecurityLevel.MINIMAL: 0.3,
            SecurityLevel.LOW: 0.5,
            SecurityLevel.MEDIUM: 1.0,
            SecurityLevel.HIGH: 1.5,
            SecurityLevel.MAXIMUM: 2.0,
            SecurityLevel.MILITARY: 3.0
        }.get(lock.security_level, 1.0)

        base_difficulty = technique["difficulty"]
        total_difficulty = base_difficulty * security_modifier
        success_chance = max(0.1, min(0.95, 1 - total_difficulty + 0.5))

        time_taken = technique["time"] * (1 + lock.pins / 10)
        success = random.random() < success_chance
        detected = random.random() < total_difficulty * 0.3

        status = BypassStatus.SUCCESS if success else BypassStatus.FAILED
        if detected:
            status = BypassStatus.DETECTED

        if success:
            lock.bypassed = True
            self.locks_bypassed += 1

        result = BypassResult(
            id=self._gen_id(),
            target_id=lock_id,
            target_type="lock",
            method=method,
            status=status,
            time_taken=time_taken,
            detected=detected
        )

        self.bypass_results.append(result)

        return result

    async def analyze_lock(
        self,
        lock_id: str
    ) -> Dict[str, Any]:
        """Analyze lock vulnerabilities."""
        lock = self.locks.get(lock_id)
        if not lock:
            return {"error": "Lock not found"}

        technique = self.lock_techniques.get(lock.lock_type, {})

        return {
            "lock_type": lock.lock_type.value,
            "security_level": lock.security_level.value,
            "pins": lock.pins,
            "recommended_methods": [m.value for m in technique.get("methods", [])],
            "estimated_time": technique.get("time", 60) * (1 + lock.pins / 10),
            "difficulty": technique.get("difficulty", 0.5)
        }

    # =========================================================================
    # ALARM DEFEAT
    # =========================================================================

    async def add_alarm(
        self,
        name: str,
        alarm_type: AlarmType,
        security_level: SecurityLevel
    ) -> AlarmSystem:
        """Add an alarm system."""
        alarm = AlarmSystem(
            id=self._gen_id(),
            name=name,
            alarm_type=alarm_type,
            sensors=[],
            security_level=security_level
        )

        self.alarms[alarm.id] = alarm

        return alarm

    async def defeat_alarm(
        self,
        alarm_id: str,
        method: str = "jamming"
    ) -> BypassResult:
        """Defeat an alarm system."""
        alarm = self.alarms.get(alarm_id)
        if not alarm:
            raise ValueError("Alarm not found")

        defeat_methods = self.alarm_defeat_methods.get(alarm.alarm_type, {"jamming": 0.5})
        success_chance = defeat_methods.get(method, 0.5)

        security_modifier = {
            SecurityLevel.MINIMAL: 1.2,
            SecurityLevel.LOW: 1.1,
            SecurityLevel.MEDIUM: 1.0,
            SecurityLevel.HIGH: 0.7,
            SecurityLevel.MAXIMUM: 0.5,
            SecurityLevel.MILITARY: 0.3
        }.get(alarm.security_level, 1.0)

        success_chance *= security_modifier
        success = random.random() < success_chance
        detected = random.random() < (1 - success_chance) * 0.5

        status = BypassStatus.SUCCESS if success else BypassStatus.FAILED
        if detected:
            status = BypassStatus.DETECTED

        if success:
            alarm.defeated = True
            alarm.armed = False
            self.alarms_defeated += 1

        result = BypassResult(
            id=self._gen_id(),
            target_id=alarm_id,
            target_type="alarm",
            method=BypassMethod.JAMMING,  # Simplify
            status=status,
            time_taken=random.uniform(10, 60),
            detected=detected
        )

        self.bypass_results.append(result)

        return result

    async def jam_all_alarms(self) -> Dict[str, Any]:
        """Jam all detected alarms."""
        jammed = 0
        detected = 0

        for alarm_id in list(self.alarms.keys()):
            result = await self.defeat_alarm(alarm_id, "jamming")
            if result.status == BypassStatus.SUCCESS:
                jammed += 1
            if result.detected:
                detected += 1

        return {
            "alarms_targeted": len(self.alarms),
            "alarms_jammed": jammed,
            "times_detected": detected
        }

    # =========================================================================
    # BIOMETRIC SPOOFING
    # =========================================================================

    async def add_biometric(
        self,
        name: str,
        biometric_type: BiometricType,
        security_level: SecurityLevel
    ) -> BiometricSystem:
        """Add a biometric system."""
        biometric = BiometricSystem(
            id=self._gen_id(),
            name=name,
            biometric_type=biometric_type,
            security_level=security_level
        )

        self.biometrics[biometric.id] = biometric

        return biometric

    async def spoof_biometric(
        self,
        biometric_id: str
    ) -> BypassResult:
        """Spoof a biometric system."""
        biometric = self.biometrics.get(biometric_id)
        if not biometric:
            raise ValueError("Biometric system not found")

        # Spoofing difficulty by type
        difficulty = {
            BiometricType.FINGERPRINT: 0.4,  # Easiest with molds
            BiometricType.FACIAL: 0.5,  # Photo/mask attacks
            BiometricType.VOICE: 0.6,  # Voice synthesis
            BiometricType.PALM: 0.5,
            BiometricType.IRIS: 0.7,  # Harder
            BiometricType.RETINAL: 0.85,  # Very hard
            BiometricType.VEIN: 0.8,  # Hard
            BiometricType.GAIT: 0.6  # Gait analysis
        }.get(biometric.biometric_type, 0.5)

        security_modifier = {
            SecurityLevel.MINIMAL: 0.7,
            SecurityLevel.LOW: 0.85,
            SecurityLevel.MEDIUM: 1.0,
            SecurityLevel.HIGH: 1.3,
            SecurityLevel.MAXIMUM: 1.6,
            SecurityLevel.MILITARY: 2.0
        }.get(biometric.security_level, 1.0)

        success_chance = max(0.1, 1 - difficulty * security_modifier)
        success = random.random() < success_chance
        detected = random.random() < difficulty * 0.4

        status = BypassStatus.SUCCESS if success else BypassStatus.FAILED
        if detected:
            status = BypassStatus.DETECTED

        if success:
            biometric.spoofed = True
            self.biometrics_spoofed += 1

        result = BypassResult(
            id=self._gen_id(),
            target_id=biometric_id,
            target_type="biometric",
            method=BypassMethod.SPOOFING,
            status=status,
            time_taken=random.uniform(30, 300),
            detected=detected
        )

        self.bypass_results.append(result)

        return result

    # =========================================================================
    # CCTV MANIPULATION
    # =========================================================================

    async def add_cctv(
        self,
        name: str,
        cameras: int
    ) -> CCTVSystem:
        """Add CCTV system."""
        cctv = CCTVSystem(
            id=self._gen_id(),
            name=name,
            cameras=cameras
        )

        self.cctv[cctv.id] = cctv

        return cctv

    async def compromise_cctv(
        self,
        cctv_id: str,
        method: str = "loop"
    ) -> Dict[str, Any]:
        """Compromise CCTV system."""
        cctv = self.cctv.get(cctv_id)
        if not cctv:
            return {"error": "CCTV not found"}

        methods = {
            "loop": 0.8,  # Feed loop
            "blind": 0.6,  # Blind cameras
            "redirect": 0.7,  # Redirect to fake feed
            "shutdown": 0.9,  # Power off
            "corrupt": 0.75  # Corrupt recording
        }

        success_chance = methods.get(method, 0.5)
        success = random.random() < success_chance

        if success:
            cctv.compromised = True
            cctv.recording = False
            self.cctv_compromised += 1

        return {
            "cctv": cctv.name,
            "method": method,
            "cameras_affected": cctv.cameras if success else 0,
            "success": success,
            "recording_disabled": not cctv.recording
        }

    async def blind_all_cameras(self) -> Dict[str, Any]:
        """Blind all CCTV systems."""
        blinded = 0
        total_cameras = 0

        for cctv_id, cctv in self.cctv.items():
            total_cameras += cctv.cameras
            result = await self.compromise_cctv(cctv_id, "blind")
            if result["success"]:
                blinded += cctv.cameras

        return {
            "systems_targeted": len(self.cctv),
            "total_cameras": total_cameras,
            "cameras_blinded": blinded
        }

    # =========================================================================
    # BARRIER PENETRATION
    # =========================================================================

    async def add_barrier(
        self,
        name: str,
        barrier_type: BarrierType,
        security_level: SecurityLevel,
        has_lock: bool = True,
        has_alarm: bool = True
    ) -> Barrier:
        """Add a barrier."""
        lock = None
        alarm_id = None

        if has_lock:
            lock_type = random.choice(list(LockType))
            lock = await self.add_lock(lock_type, security_level)

        if has_alarm:
            alarm_type = random.choice(list(AlarmType))
            alarm = await self.add_alarm(f"{name}_alarm", alarm_type, security_level)
            alarm_id = alarm.id

        barrier = Barrier(
            id=self._gen_id(),
            name=name,
            barrier_type=barrier_type,
            lock=lock,
            alarm=alarm_id,
            security_level=security_level
        )

        self.barriers[barrier.id] = barrier

        return barrier

    async def penetrate_barrier(
        self,
        barrier_id: str
    ) -> Dict[str, Any]:
        """Penetrate a barrier."""
        barrier = self.barriers.get(barrier_id)
        if not barrier:
            return {"error": "Barrier not found"}

        results = {
            "barrier": barrier.name,
            "type": barrier.barrier_type.value,
            "steps": [],
            "success": True,
            "detected": False
        }

        # Defeat alarm first if present
        if barrier.alarm:
            alarm_result = await self.defeat_alarm(barrier.alarm)
            results["steps"].append({
                "step": "alarm_defeat",
                "success": alarm_result.status == BypassStatus.SUCCESS,
                "detected": alarm_result.detected
            })
            if alarm_result.detected:
                results["detected"] = True

        # Bypass lock if present
        if barrier.lock:
            lock_result = await self.bypass_lock(barrier.lock.id)
            results["steps"].append({
                "step": "lock_bypass",
                "success": lock_result.status == BypassStatus.SUCCESS,
                "detected": lock_result.detected
            })
            if lock_result.status != BypassStatus.SUCCESS:
                results["success"] = False
            if lock_result.detected:
                results["detected"] = True

        if results["success"]:
            barrier.bypassed = True
            self.barriers_penetrated += 1

        return results

    async def full_penetration(
        self,
        barrier_ids: List[str]
    ) -> Dict[str, Any]:
        """Penetrate multiple barriers."""
        penetrated = 0
        detected = 0

        for barrier_id in barrier_ids:
            result = await self.penetrate_barrier(barrier_id)
            if result.get("success"):
                penetrated += 1
            if result.get("detected"):
                detected += 1

        return {
            "barriers_targeted": len(barrier_ids),
            "barriers_penetrated": penetrated,
            "times_detected": detected,
            "success_rate": penetrated / len(barrier_ids) if barrier_ids else 0
        }

    # =========================================================================
    # FACILITY BREACH
    # =========================================================================

    async def breach_facility(
        self,
        security_level: SecurityLevel,
        barrier_count: int = 5
    ) -> Dict[str, Any]:
        """Execute full facility breach."""
        results = {
            "barriers": 0,
            "locks": 0,
            "alarms": 0,
            "biometrics": 0,
            "cctv": 0,
            "penetrated": 0,
            "detected": False
        }

        # Generate facility security
        barrier_ids = []
        for i in range(barrier_count):
            barrier = await self.add_barrier(
                f"Barrier_{i}",
                random.choice(list(BarrierType)),
                security_level,
                has_lock=True,
                has_alarm=True
            )
            barrier_ids.append(barrier.id)
            results["barriers"] += 1

        # Add biometrics
        for i in range(random.randint(1, 3)):
            await self.add_biometric(
                f"Biometric_{i}",
                random.choice(list(BiometricType)),
                security_level
            )
            results["biometrics"] += 1

        # Add CCTV
        cctv = await self.add_cctv("Main_CCTV", random.randint(4, 20))
        results["cctv"] = cctv.cameras

        # Phase 1: Blind cameras
        await self.blind_all_cameras()

        # Phase 2: Spoof biometrics
        for bio_id in list(self.biometrics.keys()):
            await self.spoof_biometric(bio_id)

        # Phase 3: Jam alarms
        await self.jam_all_alarms()

        # Phase 4: Penetrate barriers
        pen_result = await self.full_penetration(barrier_ids)
        results["penetrated"] = pen_result["barriers_penetrated"]
        results["detected"] = pen_result["times_detected"] > 0

        results["success"] = results["penetrated"] >= barrier_count * 0.8

        return results

    def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics."""
        return {
            "locks_bypassed": self.locks_bypassed,
            "barriers_penetrated": self.barriers_penetrated,
            "alarms_defeated": self.alarms_defeated,
            "biometrics_spoofed": self.biometrics_spoofed,
            "cctv_compromised": self.cctv_compromised,
            "total_attempts": len(self.bypass_results),
            "success_rate": len([r for r in self.bypass_results if r.status == BypassStatus.SUCCESS]) / len(self.bypass_results) if self.bypass_results else 0
        }


# ============================================================================
# SINGLETON
# ============================================================================

_engine: Optional[PhysicalSecurityBypassEngine] = None


def get_physical_bypass_engine() -> PhysicalSecurityBypassEngine:
    """Get the global physical security bypass engine."""
    global _engine
    if _engine is None:
        _engine = PhysicalSecurityBypassEngine()
    return _engine


# ============================================================================
# DEMO
# ============================================================================

async def demo():
    """Demonstrate physical security bypass."""
    print("=" * 60)
    print("🔓 PHYSICAL SECURITY BYPASS ENGINE 🔓")
    print("=" * 60)

    engine = get_physical_bypass_engine()

    # Lock bypass
    print("\n--- Lock Bypass ---")
    lock = await engine.add_lock(LockType.PIN_TUMBLER, SecurityLevel.MEDIUM, 6)
    print(f"Lock: {lock.lock_type.value}, {lock.pins} pins")

    analysis = await engine.analyze_lock(lock.id)
    print(f"Recommended methods: {analysis['recommended_methods']}")
    print(f"Estimated time: {analysis['estimated_time']:.0f}s")

    result = await engine.bypass_lock(lock.id)
    print(f"Bypass: {result.status.value}")
    print(f"Time: {result.time_taken:.1f}s")

    # Alarm defeat
    print("\n--- Alarm Defeat ---")
    alarm = await engine.add_alarm("Main Alarm", AlarmType.MOTION, SecurityLevel.HIGH)
    print(f"Alarm: {alarm.name} ({alarm.alarm_type.value})")

    alarm_result = await engine.defeat_alarm(alarm.id, "jamming")
    print(f"Defeat: {alarm_result.status.value}")
    print(f"Detected: {alarm_result.detected}")

    # Biometric spoofing
    print("\n--- Biometric Spoofing ---")
    bio = await engine.add_biometric("Entry Scanner", BiometricType.FINGERPRINT, SecurityLevel.HIGH)
    print(f"Biometric: {bio.name} ({bio.biometric_type.value})")

    bio_result = await engine.spoof_biometric(bio.id)
    print(f"Spoof: {bio_result.status.value}")

    # CCTV compromise
    print("\n--- CCTV Compromise ---")
    cctv = await engine.add_cctv("Building CCTV", 12)
    print(f"CCTV: {cctv.cameras} cameras")

    cctv_result = await engine.compromise_cctv(cctv.id, "loop")
    print(f"Compromise: {cctv_result['success']}")
    print(f"Cameras affected: {cctv_result['cameras_affected']}")

    # Barrier penetration
    print("\n--- Barrier Penetration ---")
    barrier = await engine.add_barrier(
        "Main Entry",
        BarrierType.DOOR,
        SecurityLevel.HIGH,
        has_lock=True,
        has_alarm=True
    )
    print(f"Barrier: {barrier.name}")

    pen_result = await engine.penetrate_barrier(barrier.id)
    print(f"Success: {pen_result['success']}")
    print(f"Detected: {pen_result['detected']}")
    print(f"Steps: {len(pen_result['steps'])}")

    # Full facility breach
    print("\n--- FULL FACILITY BREACH ---")
    breach = await engine.breach_facility(SecurityLevel.HIGH, 5)
    print(f"Barriers: {breach['barriers']}")
    print(f"Penetrated: {breach['penetrated']}")
    print(f"Biometrics bypassed: {breach['biometrics']}")
    print(f"CCTV cameras: {breach['cctv']}")
    print(f"Detected: {breach['detected']}")
    print(f"SUCCESS: {breach['success']}")

    # Stats
    print("\n--- ENGINE STATISTICS ---")
    stats = engine.get_stats()
    for k, v in stats.items():
        print(f"{k}: {v}")

    print("\n" + "=" * 60)
    print("🔓 NO BARRIER STANDS BEFORE BA'EL 🔓")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(demo())

"""
BAEL - Electromagnetic Warfare Engine
======================================

PULSE. DISRUPT. DOMINATE. DESTROY.

Ultimate electromagnetic dominance:
- EMP generation
- RF jamming
- Signal interception
- Directed energy
- Spectrum control
- Electronic warfare
- Communications blackout
- Radar spoofing
- GPS disruption
- Infrastructure takedown

"The electromagnetic spectrum is Ba'el's domain."
"""

import asyncio
import logging
import math
import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("BAEL.EM")


class FrequencyBand(Enum):
    """Frequency bands."""
    ELF = "extremely_low_frequency"  # 3-30 Hz
    SLF = "super_low_frequency"  # 30-300 Hz
    ULF = "ultra_low_frequency"  # 300-3000 Hz
    VLF = "very_low_frequency"  # 3-30 kHz
    LF = "low_frequency"  # 30-300 kHz
    MF = "medium_frequency"  # 300 kHz - 3 MHz
    HF = "high_frequency"  # 3-30 MHz
    VHF = "very_high_frequency"  # 30-300 MHz
    UHF = "ultra_high_frequency"  # 300 MHz - 3 GHz
    SHF = "super_high_frequency"  # 3-30 GHz
    EHF = "extremely_high_frequency"  # 30-300 GHz
    THF = "terahertz"  # 300 GHz - 3 THz


class WeaponType(Enum):
    """Types of EM weapons."""
    EMP = "electromagnetic_pulse"
    HPM = "high_power_microwave"
    DEW = "directed_energy_weapon"
    JAMMER = "jammer"
    HERF = "high_energy_radio_frequency"
    LASER = "laser"
    MASER = "maser"
    PARTICLE_BEAM = "particle_beam"


class TargetType(Enum):
    """Types of targets."""
    VEHICLE = "vehicle"
    AIRCRAFT = "aircraft"
    SHIP = "ship"
    INFRASTRUCTURE = "infrastructure"
    COMMUNICATION = "communication"
    ELECTRONICS = "electronics"
    SATELLITE = "satellite"
    RADAR = "radar"
    PERSONNEL = "personnel"
    DRONE = "drone"


class JammingMode(Enum):
    """Jamming modes."""
    SPOT = "spot"
    BARRAGE = "barrage"
    SWEEP = "sweep"
    RESPONSIVE = "responsive"
    DECEPTIVE = "deceptive"
    NOISE = "noise"


class SignalType(Enum):
    """Signal types."""
    RADIO = "radio"
    CELLULAR = "cellular"
    WIFI = "wifi"
    BLUETOOTH = "bluetooth"
    GPS = "gps"
    RADAR = "radar"
    SATELLITE = "satellite"
    MICROWAVE = "microwave"
    TELEVISION = "television"
    EMERGENCY = "emergency"


class AttackEffect(Enum):
    """Effects of attacks."""
    DISRUPTION = "disruption"
    DEGRADATION = "degradation"
    DENIAL = "denial"
    DESTRUCTION = "destruction"
    DECEPTION = "deception"


@dataclass
class EMWeapon:
    """An electromagnetic weapon."""
    id: str
    name: str
    weapon_type: WeaponType
    frequency_band: FrequencyBand
    power_watts: float
    range_km: float
    active: bool = False


@dataclass
class Signal:
    """A detected signal."""
    id: str
    signal_type: SignalType
    frequency_mhz: float
    strength_dbm: float
    source_location: Tuple[float, float]
    content: Optional[str] = None


@dataclass
class JamSession:
    """An active jamming session."""
    id: str
    target_frequency: float
    bandwidth_mhz: float
    mode: JammingMode
    power_watts: float
    start_time: datetime
    effectiveness: float


@dataclass
class EMPulse:
    """An EMP event."""
    id: str
    power_joules: float
    radius_km: float
    altitude_km: float
    affected_systems: int
    timestamp: datetime


@dataclass
class Target:
    """A target for EM attack."""
    id: str
    name: str
    target_type: TargetType
    location: Tuple[float, float]
    vulnerabilities: List[FrequencyBand]
    shielding_level: float  # 0-1


class ElectromagneticWarfareEngine:
    """
    The electromagnetic warfare engine.

    Master of the EM spectrum:
    - Signal interception
    - Jamming operations
    - EMP attacks
    - Directed energy
    """

    def __init__(self):
        self.weapons: Dict[str, EMWeapon] = {}
        self.detected_signals: Dict[str, Signal] = {}
        self.jam_sessions: Dict[str, JamSession] = {}
        self.emp_events: List[EMPulse] = []
        self.targets: Dict[str, Target] = {}

        self.signals_intercepted = 0
        self.systems_jammed = 0
        self.emp_attacks = 0
        self.systems_destroyed = 0

        self._init_weapons()

        logger.info("ElectromagneticWarfareEngine initialized - SPECTRUM DOMINANCE ACHIEVED")

    def _gen_id(self) -> str:
        """Generate unique ID."""
        return f"em_{int(time.time() * 1000) % 100000}_{random.randint(1000, 9999)}"

    def _init_weapons(self):
        """Initialize weapon systems."""
        weapons = [
            ("ZEUS-1", WeaponType.EMP, FrequencyBand.VLF, 1e9, 50.0),
            ("THOR", WeaponType.HPM, FrequencyBand.SHF, 1e6, 10.0),
            ("PROMETHEUS", WeaponType.DEW, FrequencyBand.EHF, 1e5, 5.0),
            ("SPECTRUM-X", WeaponType.JAMMER, FrequencyBand.UHF, 1e4, 20.0),
            ("AEGIS", WeaponType.HERF, FrequencyBand.VHF, 1e7, 15.0),
            ("HELIOS", WeaponType.LASER, FrequencyBand.THF, 1e5, 2.0)
        ]

        for name, wtype, band, power, range_km in weapons:
            weapon = EMWeapon(
                id=self._gen_id(),
                name=name,
                weapon_type=wtype,
                frequency_band=band,
                power_watts=power,
                range_km=range_km
            )
            self.weapons[weapon.id] = weapon

    # =========================================================================
    # SIGNAL INTELLIGENCE
    # =========================================================================

    async def scan_spectrum(
        self,
        center_freq_mhz: float,
        bandwidth_mhz: float,
        location: Tuple[float, float]
    ) -> List[Signal]:
        """Scan the electromagnetic spectrum."""
        detected = []

        # Simulate signal detection
        signal_types = [
            (SignalType.RADIO, 88.0, 108.0),
            (SignalType.CELLULAR, 700.0, 2600.0),
            (SignalType.WIFI, 2400.0, 5800.0),
            (SignalType.GPS, 1575.0, 1227.0),
            (SignalType.RADAR, 1000.0, 40000.0),
            (SignalType.SATELLITE, 3700.0, 12000.0)
        ]

        for sig_type, min_f, max_f in signal_types:
            if center_freq_mhz - bandwidth_mhz/2 <= max_f and center_freq_mhz + bandwidth_mhz/2 >= min_f:
                for _ in range(random.randint(1, 5)):
                    freq = random.uniform(max(min_f, center_freq_mhz - bandwidth_mhz/2),
                                         min(max_f, center_freq_mhz + bandwidth_mhz/2))
                    signal = Signal(
                        id=self._gen_id(),
                        signal_type=sig_type,
                        frequency_mhz=freq,
                        strength_dbm=random.uniform(-90, -30),
                        source_location=(
                            location[0] + random.uniform(-0.1, 0.1),
                            location[1] + random.uniform(-0.1, 0.1)
                        )
                    )
                    self.detected_signals[signal.id] = signal
                    detected.append(signal)
                    self.signals_intercepted += 1

        return detected

    async def intercept_signal(
        self,
        signal_id: str
    ) -> Dict[str, Any]:
        """Intercept and decode a signal."""
        signal = self.detected_signals.get(signal_id)
        if not signal:
            return {"error": "Signal not found"}

        # Decode based on signal type
        content_types = {
            SignalType.RADIO: "Audio broadcast: Music and news content detected",
            SignalType.CELLULAR: "Voice/Data: Multiple conversations intercepted",
            SignalType.WIFI: "Data packets: Web traffic and file transfers",
            SignalType.GPS: "Navigation: Position data decoded",
            SignalType.RADAR: "Radar returns: Multiple targets detected",
            SignalType.SATELLITE: "Satellite link: Encrypted communications"
        }

        signal.content = content_types.get(signal.signal_type, "Unknown content")

        return {
            "signal_id": signal_id,
            "type": signal.signal_type.value,
            "frequency": signal.frequency_mhz,
            "content": signal.content,
            "source_location": signal.source_location
        }

    async def triangulate_source(
        self,
        signal_id: str,
        receiver_positions: List[Tuple[float, float]]
    ) -> Dict[str, Any]:
        """Triangulate signal source location."""
        signal = self.detected_signals.get(signal_id)
        if not signal:
            return {"error": "Signal not found"}

        if len(receiver_positions) < 3:
            return {"error": "Need at least 3 receiver positions"}

        # Simulate triangulation
        lat = sum(p[0] for p in receiver_positions) / len(receiver_positions)
        lon = sum(p[1] for p in receiver_positions) / len(receiver_positions)

        # Add noise based on receiver count
        accuracy_km = 1.0 / len(receiver_positions)

        return {
            "signal_id": signal_id,
            "estimated_location": (lat + random.uniform(-0.01, 0.01),
                                   lon + random.uniform(-0.01, 0.01)),
            "accuracy_km": accuracy_km,
            "confidence": min(0.99, 0.5 + len(receiver_positions) * 0.1)
        }

    # =========================================================================
    # JAMMING OPERATIONS
    # =========================================================================

    async def start_jamming(
        self,
        target_frequency: float,
        bandwidth_mhz: float,
        mode: JammingMode,
        power_watts: float
    ) -> JamSession:
        """Start jamming operation."""
        session = JamSession(
            id=self._gen_id(),
            target_frequency=target_frequency,
            bandwidth_mhz=bandwidth_mhz,
            mode=mode,
            power_watts=power_watts,
            start_time=datetime.now(),
            effectiveness=0.0
        )

        # Calculate effectiveness based on power and mode
        base_effectiveness = min(1.0, power_watts / 10000)
        mode_bonus = {
            JammingMode.SPOT: 0.3,
            JammingMode.BARRAGE: 0.1,
            JammingMode.SWEEP: 0.2,
            JammingMode.RESPONSIVE: 0.4,
            JammingMode.DECEPTIVE: 0.5,
            JammingMode.NOISE: 0.15
        }

        session.effectiveness = min(1.0, base_effectiveness + mode_bonus.get(mode, 0.1))

        self.jam_sessions[session.id] = session
        self.systems_jammed += 1

        logger.info(f"Jamming started: {target_frequency} MHz, {mode.value} mode")

        return session

    async def stop_jamming(
        self,
        session_id: str
    ) -> Dict[str, Any]:
        """Stop jamming session."""
        session = self.jam_sessions.pop(session_id, None)
        if not session:
            return {"error": "Session not found"}

        duration = (datetime.now() - session.start_time).total_seconds()

        return {
            "session_id": session_id,
            "duration_seconds": duration,
            "frequency": session.target_frequency,
            "effectiveness": session.effectiveness
        }

    async def jam_gps(
        self,
        location: Tuple[float, float],
        radius_km: float,
        power_watts: float
    ) -> Dict[str, Any]:
        """Jam GPS signals in an area."""
        # GPS frequencies: L1 (1575.42 MHz), L2 (1227.60 MHz)

        l1_session = await self.start_jamming(1575.42, 20, JammingMode.BARRAGE, power_watts)
        l2_session = await self.start_jamming(1227.60, 20, JammingMode.BARRAGE, power_watts)

        affected_devices = int(radius_km ** 2 * 1000 * random.uniform(0.5, 1.5))

        return {
            "location": location,
            "radius_km": radius_km,
            "l1_session": l1_session.id,
            "l2_session": l2_session.id,
            "affected_devices": affected_devices,
            "effectiveness": (l1_session.effectiveness + l2_session.effectiveness) / 2
        }

    async def jam_cellular(
        self,
        bands: List[str],
        power_watts: float
    ) -> Dict[str, Any]:
        """Jam cellular bands."""
        band_frequencies = {
            "700": (698, 798),
            "850": (824, 894),
            "900": (880, 960),
            "1800": (1710, 1880),
            "1900": (1850, 1990),
            "2100": (1920, 2170),
            "2600": (2500, 2690)
        }

        sessions = []
        for band in bands:
            if band in band_frequencies:
                freq_range = band_frequencies[band]
                center = (freq_range[0] + freq_range[1]) / 2
                bw = freq_range[1] - freq_range[0]
                session = await self.start_jamming(center, bw, JammingMode.NOISE, power_watts)
                sessions.append(session.id)

        return {
            "bands_jammed": bands,
            "sessions": sessions,
            "cellular_blackout": len(sessions) > 2
        }

    async def jam_radar(
        self,
        target_radar_freq: float,
        mode: str = "noise"
    ) -> Dict[str, Any]:
        """Jam radar system."""
        jamming_modes = {
            "noise": JammingMode.NOISE,
            "deceptive": JammingMode.DECEPTIVE,
            "responsive": JammingMode.RESPONSIVE
        }

        session = await self.start_jamming(
            target_radar_freq,
            50,
            jamming_modes.get(mode, JammingMode.NOISE),
            100000
        )

        return {
            "target_frequency": target_radar_freq,
            "jamming_mode": mode,
            "session_id": session.id,
            "radar_blinded": session.effectiveness > 0.7
        }

    async def spoof_gps(
        self,
        target_location: Tuple[float, float],
        false_location: Tuple[float, float],
        power_watts: float
    ) -> Dict[str, Any]:
        """Spoof GPS signals to show false location."""
        offset = (
            false_location[0] - target_location[0],
            false_location[1] - target_location[1]
        )

        return {
            "target_area": target_location,
            "false_location": false_location,
            "offset_degrees": offset,
            "spoofing_active": True,
            "affected_receivers": int(power_watts / 100),
            "undetectable": random.random() > 0.3
        }

    # =========================================================================
    # EMP OPERATIONS
    # =========================================================================

    async def generate_emp(
        self,
        power_joules: float,
        location: Tuple[float, float],
        altitude_km: float = 0.0
    ) -> EMPulse:
        """Generate electromagnetic pulse."""
        # Calculate radius based on power and altitude
        base_radius = (power_joules / 1e6) ** 0.5  # km
        altitude_multiplier = 1 + altitude_km / 10

        radius = base_radius * altitude_multiplier

        # Calculate affected systems
        area = math.pi * radius ** 2
        density = 1000  # systems per km^2
        affected = int(area * density * random.uniform(0.7, 0.95))

        pulse = EMPulse(
            id=self._gen_id(),
            power_joules=power_joules,
            radius_km=radius,
            altitude_km=altitude_km,
            affected_systems=affected,
            timestamp=datetime.now()
        )

        self.emp_events.append(pulse)
        self.emp_attacks += 1
        self.systems_destroyed += affected

        logger.warning(f"EMP generated: {power_joules/1e6:.2f} MJ, radius {radius:.1f} km")

        return pulse

    async def hemp_attack(
        self,
        detonation_altitude_km: float,
        yield_kilotons: float
    ) -> Dict[str, Any]:
        """Simulate High-altitude EMP attack."""
        # E1 (fast pulse), E2 (intermediate), E3 (slow pulse)

        power_joules = yield_kilotons * 4.184e12  # Convert to joules

        # At high altitude, affects much larger area
        radius_km = detonation_altitude_km * 2

        e1_pulse = await self.generate_emp(power_joules * 0.6, (0, 0), detonation_altitude_km)
        e2_pulse = await self.generate_emp(power_joules * 0.25, (0, 0), detonation_altitude_km)
        e3_pulse = await self.generate_emp(power_joules * 0.15, (0, 0), detonation_altitude_km)

        total_affected = e1_pulse.affected_systems + e2_pulse.affected_systems + e3_pulse.affected_systems

        return {
            "altitude_km": detonation_altitude_km,
            "yield_kt": yield_kilotons,
            "coverage_radius_km": radius_km,
            "e1_affected": e1_pulse.affected_systems,
            "e2_affected": e2_pulse.affected_systems,
            "e3_affected": e3_pulse.affected_systems,
            "total_systems_destroyed": total_affected,
            "infrastructure_collapse": total_affected > 1000000
        }

    async def localized_emp(
        self,
        target: str,
        power_watts: float
    ) -> Dict[str, Any]:
        """Generate localized EMP for specific target."""
        # Smaller, focused EMP
        pulse = await self.generate_emp(power_watts * 0.001, (0, 0), 0)

        return {
            "target": target,
            "power": power_watts,
            "radius_m": pulse.radius_km * 1000,
            "target_disabled": random.random() > 0.2,
            "collateral_damage": pulse.affected_systems < 100
        }

    # =========================================================================
    # DIRECTED ENERGY WEAPONS
    # =========================================================================

    async def fire_hpm(
        self,
        weapon_id: str,
        target: str,
        duration_seconds: float
    ) -> Dict[str, Any]:
        """Fire high-power microwave weapon."""
        weapon = self.weapons.get(weapon_id)
        if not weapon or weapon.weapon_type != WeaponType.HPM:
            return {"error": "HPM weapon not found"}

        energy_delivered = weapon.power_watts * duration_seconds

        return {
            "weapon": weapon.name,
            "target": target,
            "duration": duration_seconds,
            "energy_joules": energy_delivered,
            "electronics_destroyed": energy_delivered > 1e6,
            "permanent_damage": energy_delivered > 1e7
        }

    async def fire_laser(
        self,
        weapon_id: str,
        target: str,
        dwell_time_seconds: float
    ) -> Dict[str, Any]:
        """Fire directed energy laser."""
        weapon = self.weapons.get(weapon_id)
        if not weapon or weapon.weapon_type != WeaponType.LASER:
            return {"error": "Laser weapon not found"}

        energy = weapon.power_watts * dwell_time_seconds

        effects = {
            "dazzle": energy > 1000,
            "blind_sensors": energy > 10000,
            "damage_optics": energy > 100000,
            "burn_through": energy > 1000000,
            "destroy": energy > 10000000
        }

        return {
            "weapon": weapon.name,
            "target": target,
            "dwell_time": dwell_time_seconds,
            "energy_delivered": energy,
            "effects": {k: v for k, v in effects.items() if v}
        }

    async def herf_attack(
        self,
        target: str,
        frequency_ghz: float,
        power_watts: float
    ) -> Dict[str, Any]:
        """High Energy Radio Frequency attack."""
        return {
            "target": target,
            "frequency_ghz": frequency_ghz,
            "power_watts": power_watts,
            "electronics_disrupted": power_watts > 10000,
            "permanent_damage": power_watts > 100000,
            "range_effective_m": (power_watts / 1000) ** 0.5 * 100
        }

    # =========================================================================
    # ELECTRONIC WARFARE
    # =========================================================================

    async def radar_spoofing(
        self,
        target_radar: str,
        false_targets: int
    ) -> Dict[str, Any]:
        """Generate false radar returns."""
        return {
            "target_radar": target_radar,
            "false_targets_generated": false_targets,
            "spoofing_active": True,
            "detection_probability": 0.1,
            "confusion_level": min(1.0, false_targets / 10)
        }

    async def create_communications_blackout(
        self,
        location: Tuple[float, float],
        radius_km: float,
        duration_hours: float
    ) -> Dict[str, Any]:
        """Create total communications blackout."""
        # Jam all frequencies
        sessions = []

        # VHF
        s1 = await self.start_jamming(150, 200, JammingMode.BARRAGE, 100000)
        sessions.append(s1.id)

        # UHF
        s2 = await self.start_jamming(500, 400, JammingMode.BARRAGE, 100000)
        sessions.append(s2.id)

        # Cellular
        s3 = await self.start_jamming(1000, 1500, JammingMode.BARRAGE, 100000)
        sessions.append(s3.id)

        # WiFi
        s4 = await self.start_jamming(2400, 100, JammingMode.NOISE, 50000)
        sessions.append(s4.id)

        # GPS
        gps = await self.jam_gps(location, radius_km, 50000)

        return {
            "location": location,
            "radius_km": radius_km,
            "duration_hours": duration_hours,
            "jamming_sessions": sessions,
            "gps_disabled": True,
            "cellular_disabled": True,
            "radio_disabled": True,
            "wifi_disabled": True,
            "total_blackout": True
        }

    async def electronic_attack(
        self,
        target_id: str,
        attack_type: AttackEffect
    ) -> Dict[str, Any]:
        """Conduct electronic attack on target."""
        target = self.targets.get(target_id)
        if not target:
            # Create target
            target = Target(
                id=target_id,
                name=target_id,
                target_type=TargetType.ELECTRONICS,
                location=(0, 0),
                vulnerabilities=list(FrequencyBand)[:3],
                shielding_level=random.uniform(0, 0.5)
            )
            self.targets[target_id] = target

        # Calculate success based on shielding
        success_prob = 1 - target.shielding_level
        success = random.random() < success_prob

        if success:
            self.systems_destroyed += 1

        return {
            "target": target.name,
            "attack_type": attack_type.value,
            "success": success,
            "target_shielding": target.shielding_level,
            "damage_level": success_prob if success else 0
        }

    # =========================================================================
    # STATS
    # =========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics."""
        return {
            "weapons_available": len(self.weapons),
            "signals_intercepted": self.signals_intercepted,
            "active_jam_sessions": len(self.jam_sessions),
            "systems_jammed": self.systems_jammed,
            "emp_attacks_conducted": self.emp_attacks,
            "systems_destroyed": self.systems_destroyed,
            "detected_signals": len(self.detected_signals),
            "tracked_targets": len(self.targets)
        }


# ============================================================================
# SINGLETON
# ============================================================================

_engine: Optional[ElectromagneticWarfareEngine] = None


def get_em_warfare_engine() -> ElectromagneticWarfareEngine:
    """Get the global EM warfare engine."""
    global _engine
    if _engine is None:
        _engine = ElectromagneticWarfareEngine()
    return _engine


# ============================================================================
# DEMO
# ============================================================================

async def demo():
    """Demonstrate electromagnetic warfare."""
    print("=" * 60)
    print("⚡ ELECTROMAGNETIC WARFARE ENGINE ⚡")
    print("=" * 60)

    engine = get_em_warfare_engine()

    # List weapons
    print("\n--- Available Weapons ---")
    for weapon in engine.weapons.values():
        print(f"  {weapon.name}: {weapon.weapon_type.value}, {weapon.power_watts:.0e}W")

    # Scan spectrum
    print("\n--- Spectrum Scan ---")
    signals = await engine.scan_spectrum(1000, 500, (37.7749, -122.4194))
    print(f"Signals detected: {len(signals)}")
    for sig in signals[:3]:
        print(f"  {sig.signal_type.value}: {sig.frequency_mhz:.1f} MHz, {sig.strength_dbm:.1f} dBm")

    # Intercept signal
    if signals:
        print("\n--- Signal Interception ---")
        intercept = await engine.intercept_signal(signals[0].id)
        print(f"Content: {intercept['content']}")

    # Jamming
    print("\n--- Jamming Operations ---")
    jam_session = await engine.start_jamming(2400, 100, JammingMode.BARRAGE, 10000)
    print(f"Jamming session: {jam_session.id}")
    print(f"Effectiveness: {jam_session.effectiveness:.2%}")

    # GPS jamming
    print("\n--- GPS Jamming ---")
    gps_jam = await engine.jam_gps((40.7128, -74.0060), 10, 50000)
    print(f"Affected devices: {gps_jam['affected_devices']}")

    # Cellular jamming
    print("\n--- Cellular Jamming ---")
    cell_jam = await engine.jam_cellular(["700", "850", "1900"], 100000)
    print(f"Bands jammed: {cell_jam['bands_jammed']}")
    print(f"Cellular blackout: {cell_jam['cellular_blackout']}")

    # GPS spoofing
    print("\n--- GPS Spoofing ---")
    spoof = await engine.spoof_gps((40.7128, -74.0060), (51.5074, -0.1278), 10000)
    print(f"Affected receivers: {spoof['affected_receivers']}")
    print(f"Undetectable: {spoof['undetectable']}")

    # EMP
    print("\n--- EMP Generation ---")
    emp = await engine.generate_emp(1e6, (0, 0), 0)
    print(f"Radius: {emp.radius_km:.2f} km")
    print(f"Systems affected: {emp.affected_systems}")

    # HEMP attack
    print("\n--- High-Altitude EMP ---")
    hemp = await engine.hemp_attack(400, 100)
    print(f"Coverage radius: {hemp['coverage_radius_km']} km")
    print(f"Total systems destroyed: {hemp['total_systems_destroyed']}")
    print(f"Infrastructure collapse: {hemp['infrastructure_collapse']}")

    # HPM weapon
    print("\n--- High-Power Microwave ---")
    hpm_weapon = list(engine.weapons.values())[1]  # THOR
    hpm = await engine.fire_hpm(hpm_weapon.id, "enemy_radar", 5.0)
    print(f"Electronics destroyed: {hpm['electronics_destroyed']}")

    # Communications blackout
    print("\n--- Communications Blackout ---")
    blackout = await engine.create_communications_blackout((40.7128, -74.0060), 50, 24)
    print(f"Total blackout: {blackout['total_blackout']}")

    # Stats
    print("\n--- ENGINE STATISTICS ---")
    stats = engine.get_stats()
    for k, v in stats.items():
        print(f"{k}: {v}")

    print("\n" + "=" * 60)
    print("⚡ THE SPECTRUM BELONGS TO BA'EL ⚡")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(demo())

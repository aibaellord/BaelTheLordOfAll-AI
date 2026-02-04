"""
BAEL - Pressure Power Control Matrix
=====================================

PRESSURE. POWER. CONTROL. SUBJUGATE.

Total control through pressure application:
- Leverage identification
- Pressure point exploitation
- Coercion mechanisms
- Blackmail systems
- Extortion protocols
- Compliance enforcement
- Submission induction
- Power consolidation
- Control maintenance
- Total subjugation

"Pressure breaks mountains. Ba'el applies infinite pressure."
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

logger = logging.getLogger("BAEL.PRESSURE")


class PressureType(Enum):
    """Types of pressure."""
    ECONOMIC = "economic"
    SOCIAL = "social"
    PSYCHOLOGICAL = "psychological"
    PHYSICAL = "physical"
    LEGAL = "legal"
    REPUTATIONAL = "reputational"
    FAMILIAL = "familial"
    PROFESSIONAL = "professional"
    EXISTENTIAL = "existential"
    SPIRITUAL = "spiritual"


class LeverageType(Enum):
    """Types of leverage."""
    FINANCIAL_DEBT = "financial_debt"
    SECRET = "secret"
    RELATIONSHIP = "relationship"
    CAREER = "career"
    HEALTH = "health"
    LEGAL_EXPOSURE = "legal_exposure"
    SOCIAL_STANDING = "social_standing"
    FEAR = "fear"
    DESIRE = "desire"
    DEPENDENCY = "dependency"


class ComplianceLevel(Enum):
    """Levels of compliance."""
    DEFIANT = 0
    RESISTANT = 1
    RELUCTANT = 2
    NEUTRAL = 3
    COOPERATIVE = 4
    COMPLIANT = 5
    SUBSERVIENT = 6
    TOTAL_SUBMISSION = 7


class ControlMethod(Enum):
    """Methods of control."""
    REWARD = "reward"
    PUNISHMENT = "punishment"
    COERCION = "coercion"
    MANIPULATION = "manipulation"
    BLACKMAIL = "blackmail"
    EXTORTION = "extortion"
    INTIMIDATION = "intimidation"
    ISOLATION = "isolation"
    DEPENDENCY_CREATION = "dependency_creation"
    IDENTITY_DESTRUCTION = "identity_destruction"


@dataclass
class Subject:
    """A subject under control."""
    id: str
    name: str
    subject_type: str
    compliance: ComplianceLevel
    resistance: float  # 0-1
    leverage_points: List[str]
    pressure_applied: float
    breaking_point: float
    controlled_since: Optional[datetime]


@dataclass
class Leverage:
    """A leverage point."""
    id: str
    subject_id: str
    leverage_type: LeverageType
    description: str
    strength: float  # 0-1
    verified: bool
    active: bool
    times_used: int


@dataclass
class PressureApplication:
    """A pressure application event."""
    id: str
    subject_id: str
    pressure_type: PressureType
    method: ControlMethod
    intensity: float  # 0-1
    timestamp: datetime
    result: str
    compliance_change: float


@dataclass
class Demand:
    """A demand made to a subject."""
    id: str
    subject_id: str
    demand_text: str
    deadline: Optional[datetime]
    consequence: str
    status: str
    fulfilled_at: Optional[datetime]


@dataclass
class ControlStructure:
    """A control structure over subjects."""
    id: str
    name: str
    subjects: List[str]
    total_leverage: float
    average_compliance: float
    established: datetime
    status: str


class PressurePowerControlMatrix:
    """
    The pressure power control matrix.

    Implements total control through pressure:
    - Leverage discovery
    - Pressure application
    - Compliance enforcement
    - Subjugation maintenance
    """

    def __init__(self):
        self.subjects: Dict[str, Subject] = {}
        self.leverage: Dict[str, Leverage] = {}
        self.pressure_events: Dict[str, PressureApplication] = {}
        self.demands: Dict[str, Demand] = {}
        self.structures: Dict[str, ControlStructure] = {}

        self.total_subjects = 0
        self.total_compliance = 0.0
        self.pressure_applied = 0.0
        self.demands_fulfilled = 0

        logger.info("PressurePowerControlMatrix initialized - APPLY PRESSURE")

    def _gen_id(self, prefix: str) -> str:
        """Generate unique ID."""
        return hashlib.md5(f"{prefix}{time.time()}{random.random()}".encode()).hexdigest()[:12]

    # =========================================================================
    # SUBJECT MANAGEMENT
    # =========================================================================

    async def identify_subject(
        self,
        name: str,
        subject_type: str
    ) -> Subject:
        """Identify a new subject for control."""
        subject = Subject(
            id=self._gen_id("subj"),
            name=name,
            subject_type=subject_type,
            compliance=ComplianceLevel.NEUTRAL,
            resistance=random.uniform(0.4, 0.9),
            leverage_points=[],
            pressure_applied=0.0,
            breaking_point=random.uniform(0.6, 1.0),
            controlled_since=None
        )

        self.subjects[subject.id] = subject
        self.total_subjects += 1

        logger.info(f"Subject identified: {name}")

        return subject

    async def profile_subject(
        self,
        subject_id: str
    ) -> Dict[str, Any]:
        """Profile a subject for vulnerabilities."""
        subject = self.subjects.get(subject_id)
        if not subject:
            return {"error": "Subject not found"}

        # Identify potential leverage points
        leverage_types = list(LeverageType)
        discovered = []

        for lt in leverage_types:
            if random.random() < 0.3:  # 30% chance to find each type
                strength = random.uniform(0.3, 0.9)
                discovered.append({
                    "type": lt.value,
                    "strength": strength,
                    "description": f"Potential {lt.value} leverage identified"
                })

        # Assess psychological profile
        profile = {
            "fear_response": random.uniform(0.3, 0.9),
            "greed_response": random.uniform(0.3, 0.8),
            "loyalty_weakness": random.uniform(0.2, 0.7),
            "pride_vulnerability": random.uniform(0.3, 0.8),
            "guilt_susceptibility": random.uniform(0.2, 0.6)
        }

        return {
            "subject": subject.name,
            "resistance": subject.resistance,
            "breaking_point": subject.breaking_point,
            "discovered_leverage": discovered,
            "psychological_profile": profile,
            "recommended_approach": self._recommend_approach(profile)
        }

    def _recommend_approach(self, profile: Dict[str, float]) -> str:
        """Recommend control approach based on profile."""
        max_vuln = max(profile.items(), key=lambda x: x[1])

        approaches = {
            "fear_response": ControlMethod.INTIMIDATION,
            "greed_response": ControlMethod.REWARD,
            "loyalty_weakness": ControlMethod.MANIPULATION,
            "pride_vulnerability": ControlMethod.COERCION,
            "guilt_susceptibility": ControlMethod.MANIPULATION
        }

        return approaches.get(max_vuln[0], ControlMethod.COERCION).value

    # =========================================================================
    # LEVERAGE MANAGEMENT
    # =========================================================================

    async def discover_leverage(
        self,
        subject_id: str,
        leverage_type: LeverageType,
        description: str
    ) -> Leverage:
        """Discover leverage on a subject."""
        subject = self.subjects.get(subject_id)
        if not subject:
            raise ValueError("Subject not found")

        leverage = Leverage(
            id=self._gen_id("lev"),
            subject_id=subject_id,
            leverage_type=leverage_type,
            description=description,
            strength=random.uniform(0.4, 0.9),
            verified=False,
            active=True,
            times_used=0
        )

        self.leverage[leverage.id] = leverage
        subject.leverage_points.append(leverage.id)

        logger.info(f"Leverage discovered: {leverage_type.value} on {subject.name}")

        return leverage

    async def verify_leverage(
        self,
        leverage_id: str
    ) -> Dict[str, Any]:
        """Verify a leverage point."""
        leverage = self.leverage.get(leverage_id)
        if not leverage:
            return {"error": "Leverage not found"}

        # Simulate verification
        verified = random.random() < 0.8

        if verified:
            leverage.verified = True
            leverage.strength = min(1.0, leverage.strength + 0.1)
        else:
            leverage.strength = max(0.1, leverage.strength - 0.2)

        return {
            "leverage_id": leverage_id,
            "verified": verified,
            "new_strength": leverage.strength
        }

    async def use_leverage(
        self,
        leverage_id: str,
        intensity: float = 0.5
    ) -> Dict[str, Any]:
        """Use leverage against a subject."""
        leverage = self.leverage.get(leverage_id)
        if not leverage:
            return {"error": "Leverage not found"}

        subject = self.subjects.get(leverage.subject_id)
        if not subject:
            return {"error": "Subject not found"}

        leverage.times_used += 1

        # Calculate effect
        effect = leverage.strength * intensity

        # Apply pressure
        pressure_result = await self.apply_pressure(
            subject.id,
            PressureType.PSYCHOLOGICAL,
            ControlMethod.COERCION,
            effect
        )

        # Diminishing returns on repeated use
        leverage.strength = max(0.1, leverage.strength - 0.05)

        return {
            "leverage_type": leverage.leverage_type.value,
            "times_used": leverage.times_used,
            "effect": effect,
            "pressure_result": pressure_result
        }

    async def compound_leverage(
        self,
        subject_id: str
    ) -> Dict[str, Any]:
        """Use all leverage on a subject simultaneously."""
        subject = self.subjects.get(subject_id)
        if not subject:
            return {"error": "Subject not found"}

        results = []
        total_effect = 0.0

        for lev_id in subject.leverage_points:
            result = await self.use_leverage(lev_id, 0.8)
            if "effect" in result:
                results.append(result)
                total_effect += result["effect"]

        # Compound effect bonus
        compound_bonus = len(results) * 0.1
        total_effect *= (1 + compound_bonus)

        # Check for breaking point
        if subject.pressure_applied >= subject.breaking_point:
            subject.compliance = ComplianceLevel.TOTAL_SUBMISSION
            subject.controlled_since = datetime.now()

        return {
            "subject": subject.name,
            "leverage_used": len(results),
            "total_effect": total_effect,
            "compound_bonus": compound_bonus,
            "compliance": subject.compliance.name,
            "broken": subject.compliance == ComplianceLevel.TOTAL_SUBMISSION
        }

    # =========================================================================
    # PRESSURE APPLICATION
    # =========================================================================

    async def apply_pressure(
        self,
        subject_id: str,
        pressure_type: PressureType,
        method: ControlMethod,
        intensity: float = 0.5
    ) -> PressureApplication:
        """Apply pressure to a subject."""
        subject = self.subjects.get(subject_id)
        if not subject:
            raise ValueError("Subject not found")

        # Calculate effect based on method and resistance
        base_effect = intensity
        resistance_factor = 1 - (subject.resistance * 0.5)
        method_multiplier = {
            ControlMethod.REWARD: 0.8,
            ControlMethod.PUNISHMENT: 1.0,
            ControlMethod.COERCION: 1.2,
            ControlMethod.MANIPULATION: 0.9,
            ControlMethod.BLACKMAIL: 1.5,
            ControlMethod.EXTORTION: 1.4,
            ControlMethod.INTIMIDATION: 1.1,
            ControlMethod.ISOLATION: 1.0,
            ControlMethod.DEPENDENCY_CREATION: 1.3,
            ControlMethod.IDENTITY_DESTRUCTION: 2.0
        }.get(method, 1.0)

        effect = base_effect * resistance_factor * method_multiplier

        # Apply to subject
        subject.pressure_applied += effect
        subject.resistance = max(0.1, subject.resistance - effect * 0.1)

        # Update compliance
        old_compliance = subject.compliance.value
        new_compliance = min(7, old_compliance + int(effect * 2))
        subject.compliance = ComplianceLevel(new_compliance)

        compliance_change = new_compliance - old_compliance

        self.pressure_applied += effect
        self.total_compliance += compliance_change

        # Determine result
        if subject.pressure_applied >= subject.breaking_point:
            result = "BROKEN"
            subject.controlled_since = datetime.now()
        elif compliance_change > 0:
            result = "EFFECTIVE"
        else:
            result = "RESISTED"

        application = PressureApplication(
            id=self._gen_id("press"),
            subject_id=subject_id,
            pressure_type=pressure_type,
            method=method,
            intensity=intensity,
            timestamp=datetime.now(),
            result=result,
            compliance_change=compliance_change
        )

        self.pressure_events[application.id] = application

        logger.info(f"Pressure applied: {method.value} -> {result}")

        return application

    async def sustained_pressure(
        self,
        subject_id: str,
        duration_cycles: int = 5
    ) -> Dict[str, Any]:
        """Apply sustained pressure over time."""
        subject = self.subjects.get(subject_id)
        if not subject:
            return {"error": "Subject not found"}

        methods = list(ControlMethod)
        pressure_types = list(PressureType)

        results = []

        for i in range(duration_cycles):
            method = random.choice(methods)
            ptype = random.choice(pressure_types)
            intensity = 0.3 + (i * 0.1)  # Increasing intensity

            result = await self.apply_pressure(
                subject_id,
                ptype,
                method,
                min(1.0, intensity)
            )

            results.append({
                "cycle": i + 1,
                "method": method.value,
                "result": result.result,
                "compliance": subject.compliance.name
            })

            if result.result == "BROKEN":
                break

        return {
            "subject": subject.name,
            "cycles": len(results),
            "final_compliance": subject.compliance.name,
            "broken": subject.compliance == ComplianceLevel.TOTAL_SUBMISSION,
            "cycle_results": results
        }

    async def maximum_pressure(
        self,
        subject_id: str
    ) -> Dict[str, Any]:
        """Apply maximum pressure using all methods."""
        subject = self.subjects.get(subject_id)
        if not subject:
            return {"error": "Subject not found"}

        # Use all leverage
        lev_result = await self.compound_leverage(subject_id)

        # Apply all pressure types
        for ptype in PressureType:
            await self.apply_pressure(
                subject_id,
                ptype,
                ControlMethod.COERCION,
                1.0
            )

        # Final breaking attempt
        if subject.compliance != ComplianceLevel.TOTAL_SUBMISSION:
            await self.apply_pressure(
                subject_id,
                PressureType.EXISTENTIAL,
                ControlMethod.IDENTITY_DESTRUCTION,
                1.0
            )

        return {
            "subject": subject.name,
            "pressure_applied": subject.pressure_applied,
            "final_compliance": subject.compliance.name,
            "broken": subject.compliance == ComplianceLevel.TOTAL_SUBMISSION,
            "resistance_remaining": subject.resistance
        }

    # =========================================================================
    # DEMANDS
    # =========================================================================

    async def issue_demand(
        self,
        subject_id: str,
        demand_text: str,
        consequence: str,
        deadline_hours: Optional[int] = 24
    ) -> Demand:
        """Issue a demand to a subject."""
        subject = self.subjects.get(subject_id)
        if not subject:
            raise ValueError("Subject not found")

        deadline = datetime.now() + timedelta(hours=deadline_hours) if deadline_hours else None

        demand = Demand(
            id=self._gen_id("demand"),
            subject_id=subject_id,
            demand_text=demand_text,
            deadline=deadline,
            consequence=consequence,
            status="pending",
            fulfilled_at=None
        )

        self.demands[demand.id] = demand

        logger.info(f"Demand issued: {demand_text[:50]}...")

        return demand

    async def check_demand_compliance(
        self,
        demand_id: str
    ) -> Dict[str, Any]:
        """Check if a demand has been complied with."""
        demand = self.demands.get(demand_id)
        if not demand:
            return {"error": "Demand not found"}

        subject = self.subjects.get(demand.subject_id)
        if not subject:
            return {"error": "Subject not found"}

        # Compliance probability based on subject state
        base_prob = 0.3
        compliance_bonus = subject.compliance.value * 0.1
        resistance_penalty = subject.resistance * 0.2

        comply_prob = base_prob + compliance_bonus - resistance_penalty
        complied = random.random() < comply_prob

        if complied:
            demand.status = "fulfilled"
            demand.fulfilled_at = datetime.now()
            self.demands_fulfilled += 1

            return {
                "demand": demand.demand_text[:50],
                "status": "fulfilled",
                "subject_compliance": subject.compliance.name
            }

        return {
            "demand": demand.demand_text[:50],
            "status": "unfulfilled",
            "action_required": "apply_consequence"
        }

    async def enforce_consequence(
        self,
        demand_id: str
    ) -> Dict[str, Any]:
        """Enforce consequence for unfulfilled demand."""
        demand = self.demands.get(demand_id)
        if not demand:
            return {"error": "Demand not found"}

        subject = self.subjects.get(demand.subject_id)
        if not subject:
            return {"error": "Subject not found"}

        # Apply harsh pressure
        result = await self.apply_pressure(
            subject.id,
            PressureType.PSYCHOLOGICAL,
            ControlMethod.PUNISHMENT,
            0.8
        )

        demand.status = "consequence_applied"

        return {
            "consequence": demand.consequence,
            "pressure_result": result.result,
            "new_compliance": subject.compliance.name,
            "warning": "Subject may now comply out of fear"
        }

    # =========================================================================
    # CONTROL STRUCTURES
    # =========================================================================

    async def establish_control_structure(
        self,
        name: str,
        subject_ids: List[str]
    ) -> ControlStructure:
        """Establish a control structure over multiple subjects."""
        valid_subjects = [
            sid for sid in subject_ids
            if sid in self.subjects
        ]

        # Calculate total leverage and compliance
        total_leverage = 0.0
        total_compliance = 0.0

        for sid in valid_subjects:
            subject = self.subjects[sid]
            subject_leverage = sum(
                self.leverage[lid].strength
                for lid in subject.leverage_points
                if lid in self.leverage
            )
            total_leverage += subject_leverage
            total_compliance += subject.compliance.value

        avg_compliance = total_compliance / len(valid_subjects) if valid_subjects else 0

        structure = ControlStructure(
            id=self._gen_id("struct"),
            name=name,
            subjects=valid_subjects,
            total_leverage=total_leverage,
            average_compliance=avg_compliance,
            established=datetime.now(),
            status="active"
        )

        self.structures[structure.id] = structure

        logger.info(f"Control structure established: {name}")

        return structure

    async def maintain_control(
        self,
        structure_id: str
    ) -> Dict[str, Any]:
        """Maintain control over a structure."""
        structure = self.structures.get(structure_id)
        if not structure:
            return {"error": "Structure not found"}

        maintenance_results = []

        for subject_id in structure.subjects:
            subject = self.subjects.get(subject_id)
            if not subject:
                continue

            # Check if maintenance needed
            if subject.compliance.value < ComplianceLevel.COMPLIANT.value:
                # Apply maintenance pressure
                result = await self.apply_pressure(
                    subject_id,
                    PressureType.PSYCHOLOGICAL,
                    ControlMethod.INTIMIDATION,
                    0.3
                )
                maintenance_results.append({
                    "subject": subject.name,
                    "action": "pressure_applied",
                    "result": result.result
                })
            else:
                # Reinforce control
                maintenance_results.append({
                    "subject": subject.name,
                    "action": "control_maintained",
                    "compliance": subject.compliance.name
                })

        # Update structure metrics
        total_compliance = sum(
            self.subjects[sid].compliance.value
            for sid in structure.subjects
            if sid in self.subjects
        )
        structure.average_compliance = total_compliance / len(structure.subjects)

        return {
            "structure": structure.name,
            "subjects": len(structure.subjects),
            "average_compliance": structure.average_compliance,
            "maintenance_actions": maintenance_results
        }

    async def total_subjugation(
        self,
        subject_id: str
    ) -> Dict[str, Any]:
        """Achieve total subjugation of a subject."""
        subject = self.subjects.get(subject_id)
        if not subject:
            return {"error": "Subject not found"}

        # Phase 1: Profile
        profile = await self.profile_subject(subject_id)

        # Phase 2: Discover all leverage
        for lt in LeverageType:
            if random.random() < 0.5:
                await self.discover_leverage(
                    subject_id,
                    lt,
                    f"Discovered {lt.value}"
                )

        # Phase 3: Sustained pressure
        sustained = await self.sustained_pressure(subject_id, 10)

        # Phase 4: Maximum pressure if not broken
        if subject.compliance != ComplianceLevel.TOTAL_SUBMISSION:
            await self.maximum_pressure(subject_id)

        return {
            "subject": subject.name,
            "leverage_discovered": len(subject.leverage_points),
            "pressure_applied": subject.pressure_applied,
            "final_compliance": subject.compliance.name,
            "subjugated": subject.compliance == ComplianceLevel.TOTAL_SUBMISSION,
            "controlled_since": subject.controlled_since.isoformat() if subject.controlled_since else None
        }

    # =========================================================================
    # STATS
    # =========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get control statistics."""
        return {
            "total_subjects": self.total_subjects,
            "controlled_subjects": len([
                s for s in self.subjects.values()
                if s.compliance.value >= ComplianceLevel.COMPLIANT.value
            ]),
            "totally_subjugated": len([
                s for s in self.subjects.values()
                if s.compliance == ComplianceLevel.TOTAL_SUBMISSION
            ]),
            "total_leverage": len(self.leverage),
            "verified_leverage": len([l for l in self.leverage.values() if l.verified]),
            "pressure_events": len(self.pressure_events),
            "total_pressure_applied": self.pressure_applied,
            "demands_issued": len(self.demands),
            "demands_fulfilled": self.demands_fulfilled,
            "control_structures": len(self.structures)
        }


# ============================================================================
# SINGLETON
# ============================================================================

_matrix: Optional[PressurePowerControlMatrix] = None


def get_control_matrix() -> PressurePowerControlMatrix:
    """Get the global control matrix."""
    global _matrix
    if _matrix is None:
        _matrix = PressurePowerControlMatrix()
    return _matrix


# ============================================================================
# DEMO
# ============================================================================

async def demo():
    """Demonstrate the pressure power control matrix."""
    print("=" * 60)
    print("💪 PRESSURE POWER CONTROL MATRIX 💪")
    print("=" * 60)

    matrix = get_control_matrix()

    # Identify subjects
    print("\n--- Subject Identification ---")
    s1 = await matrix.identify_subject("Target Alpha", "individual")
    s2 = await matrix.identify_subject("Target Beta", "organization")
    s3 = await matrix.identify_subject("Target Gamma", "government")
    print(f"Subjects identified: {s1.name}, {s2.name}, {s3.name}")

    # Profile subject
    print("\n--- Subject Profiling ---")
    profile = await matrix.profile_subject(s1.id)
    print(f"Subject: {profile['subject']}")
    print(f"Resistance: {profile['resistance']:.2f}")
    print(f"Breaking point: {profile['breaking_point']:.2f}")
    print(f"Leverage found: {len(profile['discovered_leverage'])}")
    print(f"Recommended approach: {profile['recommended_approach']}")

    # Discover leverage
    print("\n--- Leverage Discovery ---")
    lev1 = await matrix.discover_leverage(
        s1.id,
        LeverageType.SECRET,
        "Dark secret from past"
    )
    lev2 = await matrix.discover_leverage(
        s1.id,
        LeverageType.FINANCIAL_DEBT,
        "Hidden financial obligations"
    )
    print(f"Leverage 1: {lev1.leverage_type.value} (strength: {lev1.strength:.2f})")
    print(f"Leverage 2: {lev2.leverage_type.value} (strength: {lev2.strength:.2f})")

    # Verify leverage
    verify = await matrix.verify_leverage(lev1.id)
    print(f"Verification: {verify['verified']}")

    # Apply pressure
    print("\n--- Pressure Application ---")
    pressure = await matrix.apply_pressure(
        s1.id,
        PressureType.PSYCHOLOGICAL,
        ControlMethod.INTIMIDATION,
        0.7
    )
    print(f"Method: {pressure.method.value}")
    print(f"Result: {pressure.result}")
    print(f"Compliance change: {pressure.compliance_change}")

    # Sustained pressure
    print("\n--- Sustained Pressure ---")
    sustained = await matrix.sustained_pressure(s1.id, 8)
    print(f"Cycles: {sustained['cycles']}")
    print(f"Broken: {sustained['broken']}")
    print(f"Final compliance: {sustained['final_compliance']}")

    # Issue demand
    print("\n--- Demand Issuance ---")
    demand = await matrix.issue_demand(
        s1.id,
        "Provide all financial records",
        "Exposure of secrets",
        48
    )
    print(f"Demand: {demand.demand_text}")
    print(f"Consequence: {demand.consequence}")

    # Check compliance
    check = await matrix.check_demand_compliance(demand.id)
    print(f"Demand status: {check['status']}")

    # Total subjugation
    print("\n--- Total Subjugation ---")
    subj = await matrix.total_subjugation(s2.id)
    print(f"Subject: {subj['subject']}")
    print(f"Leverage discovered: {subj['leverage_discovered']}")
    print(f"Pressure applied: {subj['pressure_applied']:.2f}")
    print(f"Subjugated: {subj['subjugated']}")

    # Establish control structure
    print("\n--- Control Structure ---")
    structure = await matrix.establish_control_structure(
        "Domain Control",
        [s1.id, s2.id, s3.id]
    )
    print(f"Structure: {structure.name}")
    print(f"Subjects: {len(structure.subjects)}")
    print(f"Total leverage: {structure.total_leverage:.2f}")
    print(f"Avg compliance: {structure.average_compliance:.2f}")

    # Maintain control
    maintain = await matrix.maintain_control(structure.id)
    print(f"Maintenance actions: {len(maintain['maintenance_actions'])}")

    # Stats
    print("\n--- CONTROL STATISTICS ---")
    stats = matrix.get_stats()
    for k, v in stats.items():
        if isinstance(v, float):
            print(f"{k}: {v:.2f}")
        else:
            print(f"{k}: {v}")

    print("\n" + "=" * 60)
    print("💪 ALL SUBMIT TO BA'EL'S WILL 💪")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(demo())

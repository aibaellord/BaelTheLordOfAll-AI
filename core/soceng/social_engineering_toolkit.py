"""
BAEL - Social Engineering Toolkit
==================================

MANIPULATE. DECEIVE. CONTROL. EXTRACT.

Complete human manipulation:
- Target profiling
- Pretexting
- Phishing campaigns
- Vishing operations
- Smishing attacks
- Physical infiltration
- Trust exploitation
- Information elicitation
- Credential harvesting
- Full social attacks

"Every human is an attack vector."
"""

import asyncio
import logging
import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("BAEL.SOCENG")


class AttackType(Enum):
    """Types of social engineering attacks."""
    PHISHING = "phishing"
    SPEAR_PHISHING = "spear_phishing"
    WHALING = "whaling"
    VISHING = "vishing"
    SMISHING = "smishing"
    PRETEXTING = "pretexting"
    BAITING = "baiting"
    QUID_PRO_QUO = "quid_pro_quo"
    TAILGATING = "tailgating"
    IMPERSONATION = "impersonation"
    WATERING_HOLE = "watering_hole"
    HONEY_TRAP = "honey_trap"


class VectorType(Enum):
    """Attack vectors."""
    EMAIL = "email"
    PHONE = "phone"
    SMS = "sms"
    SOCIAL_MEDIA = "social_media"
    IN_PERSON = "in_person"
    WEBSITE = "website"
    MESSAGING = "messaging"
    USB_DROP = "usb_drop"


class TargetRole(Enum):
    """Target roles."""
    EXECUTIVE = "executive"
    IT_ADMIN = "it_admin"
    FINANCE = "finance"
    HR = "hr"
    RECEPTIONIST = "receptionist"
    SECURITY = "security"
    DEVELOPER = "developer"
    SUPPORT = "support"
    VENDOR = "vendor"
    CONTRACTOR = "contractor"


class PersonalityType(Enum):
    """Personality types for targeting."""
    TRUSTING = "trusting"
    HELPFUL = "helpful"
    FEARFUL = "fearful"
    GREEDY = "greedy"
    CURIOUS = "curious"
    BUSY = "busy"
    NAIVE = "naive"
    AUTHORITARIAN = "authoritarian"


class TriggerType(Enum):
    """Psychological triggers."""
    URGENCY = "urgency"
    AUTHORITY = "authority"
    SOCIAL_PROOF = "social_proof"
    RECIPROCITY = "reciprocity"
    SCARCITY = "scarcity"
    FEAR = "fear"
    GREED = "greed"
    CURIOSITY = "curiosity"
    LIKING = "liking"
    COMMITMENT = "commitment"


class ObjectiveType(Enum):
    """Attack objectives."""
    CREDENTIALS = "credentials"
    INFORMATION = "information"
    ACCESS = "access"
    FINANCIAL = "financial"
    INSTALLATION = "installation"
    PHYSICAL_ACCESS = "physical_access"
    RELATIONSHIP = "relationship"


@dataclass
class Target:
    """A social engineering target."""
    id: str
    name: str
    role: TargetRole
    organization: str
    email: str
    phone: str
    personality: PersonalityType
    vulnerability_score: float = 0.0


@dataclass
class Pretext:
    """A pretext for social engineering."""
    id: str
    name: str
    role: str
    organization: str
    backstory: str
    credentials: Dict[str, str] = field(default_factory=dict)


@dataclass
class Attack:
    """A social engineering attack."""
    id: str
    attack_type: AttackType
    vector: VectorType
    target_ids: List[str]
    pretext_id: Optional[str]
    objective: ObjectiveType
    triggers: List[TriggerType]
    success_rate: float = 0.0


@dataclass
class Campaign:
    """A social engineering campaign."""
    id: str
    name: str
    attacks: List[str]
    targets_total: int
    targets_compromised: int = 0
    credentials_harvested: int = 0
    access_gained: int = 0


@dataclass
class PhishingTemplate:
    """A phishing template."""
    id: str
    name: str
    subject: str
    body: str
    trigger: TriggerType
    landing_page: str


class SocialEngineeringToolkit:
    """
    The social engineering toolkit.

    Complete human manipulation:
    - Target profiling
    - Pretext creation
    - Attack execution
    - Campaign management
    """

    def __init__(self):
        self.targets: Dict[str, Target] = {}
        self.pretexts: Dict[str, Pretext] = {}
        self.attacks: Dict[str, Attack] = {}
        self.campaigns: Dict[str, Campaign] = {}
        self.templates: Dict[str, PhishingTemplate] = {}

        self.targets_compromised = 0
        self.credentials_harvested = 0
        self.access_gained = 0
        self.attacks_executed = 0

        self._init_toolkit_data()

        logger.info("SocialEngineeringToolkit initialized - EVERY HUMAN IS A VECTOR")

    def _gen_id(self) -> str:
        """Generate unique ID."""
        return f"se_{int(time.time() * 1000) % 100000}_{random.randint(1000, 9999)}"

    def _init_toolkit_data(self):
        """Initialize toolkit data."""
        self.attack_success_rates = {
            AttackType.PHISHING: 0.15,
            AttackType.SPEAR_PHISHING: 0.45,
            AttackType.WHALING: 0.35,
            AttackType.VISHING: 0.40,
            AttackType.SMISHING: 0.20,
            AttackType.PRETEXTING: 0.50,
            AttackType.BAITING: 0.25,
            AttackType.QUID_PRO_QUO: 0.35,
            AttackType.TAILGATING: 0.60,
            AttackType.IMPERSONATION: 0.55,
            AttackType.WATERING_HOLE: 0.30,
            AttackType.HONEY_TRAP: 0.70
        }

        self.personality_modifiers = {
            PersonalityType.TRUSTING: 0.3,
            PersonalityType.HELPFUL: 0.25,
            PersonalityType.FEARFUL: 0.35,
            PersonalityType.GREEDY: 0.4,
            PersonalityType.CURIOUS: 0.3,
            PersonalityType.BUSY: 0.2,
            PersonalityType.NAIVE: 0.5,
            PersonalityType.AUTHORITARIAN: 0.1
        }

        self.trigger_effectiveness = {
            TriggerType.URGENCY: 0.35,
            TriggerType.AUTHORITY: 0.30,
            TriggerType.SOCIAL_PROOF: 0.20,
            TriggerType.RECIPROCITY: 0.25,
            TriggerType.SCARCITY: 0.30,
            TriggerType.FEAR: 0.40,
            TriggerType.GREED: 0.45,
            TriggerType.CURIOSITY: 0.25,
            TriggerType.LIKING: 0.20,
            TriggerType.COMMITMENT: 0.15
        }

    # =========================================================================
    # TARGET PROFILING
    # =========================================================================

    async def profile_target(
        self,
        name: str,
        role: TargetRole,
        organization: str,
        email: str,
        phone: str
    ) -> Target:
        """Profile a target."""
        # Assess personality and vulnerability
        personality = random.choice(list(PersonalityType))
        vulnerability = self.personality_modifiers.get(personality, 0.2)

        # Role modifiers
        role_mods = {
            TargetRole.RECEPTIONIST: 0.2,
            TargetRole.SUPPORT: 0.15,
            TargetRole.EXECUTIVE: -0.1,
            TargetRole.IT_ADMIN: -0.2,
            TargetRole.SECURITY: -0.3
        }
        vulnerability += role_mods.get(role, 0)

        target = Target(
            id=self._gen_id(),
            name=name,
            role=role,
            organization=organization,
            email=email,
            phone=phone,
            personality=personality,
            vulnerability_score=max(0.1, min(1.0, vulnerability))
        )

        self.targets[target.id] = target

        return target

    async def mass_profile(
        self,
        organization: str,
        count: int
    ) -> List[Target]:
        """Mass profile targets in an organization."""
        targets = []

        for i in range(count):
            role = random.choice(list(TargetRole))
            target = await self.profile_target(
                f"Employee_{i}",
                role,
                organization,
                f"employee{i}@{organization.lower().replace(' ', '')}.com",
                f"+1555{random.randint(1000000, 9999999)}"
            )
            targets.append(target)

        # Sort by vulnerability
        targets.sort(key=lambda t: t.vulnerability_score, reverse=True)

        return targets

    async def identify_high_value_targets(
        self,
        organization: str
    ) -> List[Target]:
        """Identify high-value targets."""
        org_targets = [t for t in self.targets.values() if t.organization == organization]

        high_value = [
            t for t in org_targets
            if t.role in [TargetRole.EXECUTIVE, TargetRole.FINANCE, TargetRole.IT_ADMIN]
            or t.vulnerability_score > 0.5
        ]

        return high_value

    # =========================================================================
    # PRETEXT CREATION
    # =========================================================================

    async def create_pretext(
        self,
        role: str,
        organization: str,
        backstory: str
    ) -> Pretext:
        """Create a pretext identity."""
        pretext = Pretext(
            id=self._gen_id(),
            name=f"{random.choice(['John', 'Jane', 'Mike', 'Sarah'])} {random.choice(['Smith', 'Johnson', 'Williams', 'Brown'])}",
            role=role,
            organization=organization,
            backstory=backstory,
            credentials={
                "email": f"support@{organization.lower().replace(' ', '-')}.com",
                "phone": f"+1800{random.randint(1000000, 9999999)}",
                "badge_id": f"EMP{random.randint(10000, 99999)}"
            }
        )

        self.pretexts[pretext.id] = pretext

        return pretext

    async def create_authority_pretext(
        self,
        authority_type: str
    ) -> Pretext:
        """Create an authority-based pretext."""
        templates = {
            "it_support": ("IT Support Technician", "Corporate IT", "Helpdesk support for security audit"),
            "executive": ("Regional Director", "Corporate HQ", "Executive visiting from head office"),
            "auditor": ("Compliance Auditor", "External Firm", "Regulatory compliance inspection"),
            "vendor": ("Vendor Representative", "Major Supplier", "Routine service check"),
            "law_enforcement": ("Detective", "Local PD", "Following up on investigation")
        }

        if authority_type not in templates:
            authority_type = "it_support"

        role, org, backstory = templates[authority_type]

        return await self.create_pretext(role, org, backstory)

    # =========================================================================
    # ATTACK CREATION
    # =========================================================================

    async def create_attack(
        self,
        attack_type: AttackType,
        vector: VectorType,
        target_ids: List[str],
        objective: ObjectiveType,
        triggers: List[TriggerType],
        pretext_id: Optional[str] = None
    ) -> Attack:
        """Create a social engineering attack."""
        # Calculate success rate
        base_rate = self.attack_success_rates.get(attack_type, 0.2)

        # Add trigger bonuses
        for trigger in triggers:
            base_rate += self.trigger_effectiveness.get(trigger, 0) * 0.5

        # Add target vulnerability
        for tid in target_ids:
            target = self.targets.get(tid)
            if target:
                base_rate += target.vulnerability_score * 0.2

        attack = Attack(
            id=self._gen_id(),
            attack_type=attack_type,
            vector=vector,
            target_ids=target_ids,
            pretext_id=pretext_id,
            objective=objective,
            triggers=triggers,
            success_rate=min(0.95, base_rate)
        )

        self.attacks[attack.id] = attack

        return attack

    async def execute_attack(
        self,
        attack_id: str
    ) -> Dict[str, Any]:
        """Execute a social engineering attack."""
        attack = self.attacks.get(attack_id)
        if not attack:
            return {"error": "Attack not found"}

        self.attacks_executed += 1

        results = {
            "attack_type": attack.attack_type.value,
            "vector": attack.vector.value,
            "targets": len(attack.target_ids),
            "successes": 0,
            "credentials": 0,
            "access_gained": 0
        }

        for target_id in attack.target_ids:
            target = self.targets.get(target_id)
            if not target:
                continue

            # Calculate individual success
            success_rate = attack.success_rate + target.vulnerability_score * 0.1

            if random.random() < success_rate:
                results["successes"] += 1
                self.targets_compromised += 1

                if attack.objective == ObjectiveType.CREDENTIALS:
                    creds = random.randint(1, 3)
                    results["credentials"] += creds
                    self.credentials_harvested += creds
                elif attack.objective == ObjectiveType.ACCESS:
                    results["access_gained"] += 1
                    self.access_gained += 1

        return results

    # =========================================================================
    # PHISHING CAMPAIGNS
    # =========================================================================

    async def create_phishing_template(
        self,
        name: str,
        subject: str,
        body: str,
        trigger: TriggerType
    ) -> PhishingTemplate:
        """Create a phishing template."""
        template = PhishingTemplate(
            id=self._gen_id(),
            name=name,
            subject=subject,
            body=body,
            trigger=trigger,
            landing_page=f"https://secure-{random.randint(1000, 9999)}.com/login"
        )

        self.templates[template.id] = template

        return template

    async def launch_phishing_campaign(
        self,
        template_id: str,
        target_ids: List[str]
    ) -> Dict[str, Any]:
        """Launch a phishing campaign."""
        template = self.templates.get(template_id)
        if not template:
            return {"error": "Template not found"}

        attack = await self.create_attack(
            AttackType.PHISHING,
            VectorType.EMAIL,
            target_ids,
            ObjectiveType.CREDENTIALS,
            [template.trigger]
        )

        result = await self.execute_attack(attack.id)

        return {
            "template": template.name,
            "emails_sent": len(target_ids),
            "clicks": result["successes"],
            "credentials_harvested": result["credentials"],
            "success_rate": result["successes"] / len(target_ids) if target_ids else 0
        }

    async def launch_spear_phishing(
        self,
        target_id: str,
        custom_message: str
    ) -> Dict[str, Any]:
        """Launch spear phishing attack."""
        target = self.targets.get(target_id)
        if not target:
            return {"error": "Target not found"}

        attack = await self.create_attack(
            AttackType.SPEAR_PHISHING,
            VectorType.EMAIL,
            [target_id],
            ObjectiveType.CREDENTIALS,
            [TriggerType.URGENCY, TriggerType.AUTHORITY]
        )

        return await self.execute_attack(attack.id)

    # =========================================================================
    # VISHING CAMPAIGNS
    # =========================================================================

    async def execute_vishing(
        self,
        target_id: str,
        pretext_id: str,
        objective: ObjectiveType
    ) -> Dict[str, Any]:
        """Execute vishing attack."""
        target = self.targets.get(target_id)
        pretext = self.pretexts.get(pretext_id)

        if not target:
            return {"error": "Target not found"}
        if not pretext:
            return {"error": "Pretext not found"}

        attack = await self.create_attack(
            AttackType.VISHING,
            VectorType.PHONE,
            [target_id],
            objective,
            [TriggerType.AUTHORITY, TriggerType.URGENCY],
            pretext_id
        )

        result = await self.execute_attack(attack.id)

        return {
            "target": target.name,
            "pretext": pretext.role,
            "success": result["successes"] > 0,
            "objective": objective.value,
            "result": result
        }

    # =========================================================================
    # PHYSICAL ATTACKS
    # =========================================================================

    async def execute_tailgating(
        self,
        location: str,
        pretext_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Execute tailgating attack."""
        attack = await self.create_attack(
            AttackType.TAILGATING,
            VectorType.IN_PERSON,
            [],
            ObjectiveType.PHYSICAL_ACCESS,
            [TriggerType.LIKING, TriggerType.RECIPROCITY],
            pretext_id
        )

        success = random.random() < attack.success_rate

        if success:
            self.access_gained += 1

        return {
            "location": location,
            "success": success,
            "access_gained": success
        }

    async def execute_impersonation(
        self,
        pretext_id: str,
        target_location: str
    ) -> Dict[str, Any]:
        """Execute impersonation attack."""
        pretext = self.pretexts.get(pretext_id)
        if not pretext:
            return {"error": "Pretext not found"}

        attack = await self.create_attack(
            AttackType.IMPERSONATION,
            VectorType.IN_PERSON,
            [],
            ObjectiveType.ACCESS,
            [TriggerType.AUTHORITY, TriggerType.SOCIAL_PROOF],
            pretext_id
        )

        success = random.random() < attack.success_rate

        if success:
            self.access_gained += 1

        return {
            "pretext": pretext.role,
            "location": target_location,
            "success": success,
            "duration": random.randint(15, 120) if success else 0
        }

    # =========================================================================
    # CAMPAIGN MANAGEMENT
    # =========================================================================

    async def create_campaign(
        self,
        name: str,
        target_ids: List[str]
    ) -> Campaign:
        """Create a social engineering campaign."""
        campaign = Campaign(
            id=self._gen_id(),
            name=name,
            attacks=[],
            targets_total=len(target_ids)
        )

        self.campaigns[campaign.id] = campaign

        return campaign

    async def full_campaign(
        self,
        organization: str
    ) -> Dict[str, Any]:
        """Execute full social engineering campaign."""
        results = {
            "targets_profiled": 0,
            "high_value_targets": 0,
            "attacks_executed": 0,
            "targets_compromised": 0,
            "credentials_harvested": 0,
            "access_gained": 0
        }

        # Profile targets
        targets = await self.mass_profile(organization, 50)
        results["targets_profiled"] = len(targets)

        # Identify high-value targets
        high_value = await self.identify_high_value_targets(organization)
        results["high_value_targets"] = len(high_value)

        # Create pretexts
        it_pretext = await self.create_authority_pretext("it_support")
        exec_pretext = await self.create_authority_pretext("executive")

        # Create phishing template
        template = await self.create_phishing_template(
            "Password Reset",
            "Urgent: Password Reset Required",
            "Your password has expired. Click here to reset.",
            TriggerType.URGENCY
        )

        # Launch mass phishing
        target_ids = [t.id for t in targets]
        phishing = await self.launch_phishing_campaign(template.id, target_ids)
        results["attacks_executed"] += 1
        results["credentials_harvested"] += phishing["credentials_harvested"]
        results["targets_compromised"] += phishing["clicks"]

        # Spear phishing high-value
        for hv in high_value[:5]:
            spear = await self.launch_spear_phishing(hv.id, "Customized message for HVT")
            results["attacks_executed"] += 1
            results["targets_compromised"] += spear.get("successes", 0)
            results["credentials_harvested"] += spear.get("credentials", 0)

        # Vishing campaign
        for hv in high_value[:3]:
            vish = await self.execute_vishing(hv.id, it_pretext.id, ObjectiveType.ACCESS)
            results["attacks_executed"] += 1
            if vish.get("success"):
                results["access_gained"] += 1

        # Physical attacks
        tailgate = await self.execute_tailgating("Main Entrance")
        results["attacks_executed"] += 1
        if tailgate["success"]:
            results["access_gained"] += 1

        impersonate = await self.execute_impersonation(exec_pretext.id, "Executive Floor")
        results["attacks_executed"] += 1
        if impersonate["success"]:
            results["access_gained"] += 1

        return results

    def get_stats(self) -> Dict[str, Any]:
        """Get toolkit statistics."""
        return {
            "targets_profiled": len(self.targets),
            "pretexts_created": len(self.pretexts),
            "attacks_executed": self.attacks_executed,
            "targets_compromised": self.targets_compromised,
            "credentials_harvested": self.credentials_harvested,
            "access_gained": self.access_gained,
            "campaigns": len(self.campaigns)
        }


# ============================================================================
# SINGLETON
# ============================================================================

_toolkit: Optional[SocialEngineeringToolkit] = None


def get_social_engineering_toolkit() -> SocialEngineeringToolkit:
    """Get the global social engineering toolkit."""
    global _toolkit
    if _toolkit is None:
        _toolkit = SocialEngineeringToolkit()
    return _toolkit


# ============================================================================
# DEMO
# ============================================================================

async def demo():
    """Demonstrate social engineering."""
    print("=" * 60)
    print("🎭 SOCIAL ENGINEERING TOOLKIT 🎭")
    print("=" * 60)

    toolkit = get_social_engineering_toolkit()

    # Profile target
    print("\n--- Target Profiling ---")
    target = await toolkit.profile_target(
        "John Smith",
        TargetRole.FINANCE,
        "MegaCorp",
        "john.smith@megacorp.com",
        "+15551234567"
    )
    print(f"Target: {target.name}")
    print(f"Role: {target.role.value}")
    print(f"Personality: {target.personality.value}")
    print(f"Vulnerability: {target.vulnerability_score:.2f}")

    # Mass profile
    print("\n--- Mass Profiling ---")
    targets = await toolkit.mass_profile("TargetCorp", 20)
    print(f"Targets profiled: {len(targets)}")
    print("Top vulnerable targets:")
    for t in targets[:3]:
        print(f"  - {t.name} ({t.role.value}): {t.vulnerability_score:.2f}")

    # High-value targets
    print("\n--- High-Value Targets ---")
    hvts = await toolkit.identify_high_value_targets("TargetCorp")
    print(f"High-value targets: {len(hvts)}")

    # Create pretext
    print("\n--- Pretext Creation ---")
    pretext = await toolkit.create_authority_pretext("it_support")
    print(f"Identity: {pretext.name}")
    print(f"Role: {pretext.role}")
    print(f"Organization: {pretext.organization}")

    # Create attack
    print("\n--- Attack Creation ---")
    attack = await toolkit.create_attack(
        AttackType.SPEAR_PHISHING,
        VectorType.EMAIL,
        [target.id],
        ObjectiveType.CREDENTIALS,
        [TriggerType.URGENCY, TriggerType.AUTHORITY]
    )
    print(f"Attack type: {attack.attack_type.value}")
    print(f"Vector: {attack.vector.value}")
    print(f"Success rate: {attack.success_rate:.2%}")

    # Execute attack
    result = await toolkit.execute_attack(attack.id)
    print(f"Result: {result}")

    # Phishing campaign
    print("\n--- Phishing Campaign ---")
    template = await toolkit.create_phishing_template(
        "Account Alert",
        "Security Alert: Unusual Activity Detected",
        "We detected unusual login activity. Verify your account now.",
        TriggerType.FEAR
    )

    target_ids = [t.id for t in targets[:10]]
    phishing = await toolkit.launch_phishing_campaign(template.id, target_ids)
    print(f"Emails sent: {phishing['emails_sent']}")
    print(f"Clicks: {phishing['clicks']}")
    print(f"Credentials: {phishing['credentials_harvested']}")
    print(f"Success rate: {phishing['success_rate']:.2%}")

    # Vishing
    print("\n--- Vishing Attack ---")
    if hvts:
        vishing = await toolkit.execute_vishing(
            hvts[0].id,
            pretext.id,
            ObjectiveType.INFORMATION
        )
        print(f"Target: {vishing.get('target', 'N/A')}")
        print(f"Success: {vishing.get('success', False)}")

    # Physical attacks
    print("\n--- Physical Attacks ---")
    tailgate = await toolkit.execute_tailgating("Server Room Entrance")
    print(f"Tailgating: {'Success' if tailgate['success'] else 'Failed'}")

    impersonate = await toolkit.execute_impersonation(pretext.id, "IT Department")
    print(f"Impersonation: {'Success' if impersonate['success'] else 'Failed'}")
    if impersonate["success"]:
        print(f"Duration inside: {impersonate['duration']} minutes")

    # Full campaign
    print("\n--- FULL CAMPAIGN ---")
    campaign = await toolkit.full_campaign("VictimCorp")
    for k, v in campaign.items():
        print(f"{k}: {v}")

    # Stats
    print("\n--- TOOLKIT STATISTICS ---")
    stats = toolkit.get_stats()
    for k, v in stats.items():
        print(f"{k}: {v}")

    print("\n" + "=" * 60)
    print("🎭 EVERY HUMAN IS AN ATTACK VECTOR 🎭")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(demo())

"""
BAEL - Cognitive Manipulation Engine
====================================

INFLUENCE. REPROGRAM. CONTROL. DOMINATE.

Advanced cognitive manipulation capabilities:
- Psychological profiling
- Behavioral prediction
- Belief modification
- Memory manipulation
- Emotional engineering
- Decision hijacking
- Addiction creation
- Fear amplification
- Trust exploitation
- Total mind control

"The mind is merely software. Ba'el rewrites it."
"""

import asyncio
import hashlib
import logging
import math
import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("BAEL.COGNITIVE")


class PersonalityTrait(Enum):
    """Big Five personality traits."""
    OPENNESS = "openness"
    CONSCIENTIOUSNESS = "conscientiousness"
    EXTRAVERSION = "extraversion"
    AGREEABLENESS = "agreeableness"
    NEUROTICISM = "neuroticism"


class EmotionalState(Enum):
    """Emotional states."""
    NEUTRAL = "neutral"
    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    FEARFUL = "fearful"
    DISGUSTED = "disgusted"
    SURPRISED = "surprised"
    ANXIOUS = "anxious"
    DEPRESSED = "depressed"
    EUPHORIC = "euphoric"
    PARANOID = "paranoid"


class ManipulationType(Enum):
    """Types of cognitive manipulation."""
    PERSUASION = "persuasion"
    SUGGESTION = "suggestion"
    CONDITIONING = "conditioning"
    ANCHORING = "anchoring"
    GASLIGHTING = "gaslighting"
    LOVE_BOMBING = "love_bombing"
    ISOLATION = "isolation"
    DEPENDENCY = "dependency"
    FEAR_INDUCTION = "fear_induction"
    REWARD_INTERMITTENT = "reward_intermittent"


class VulnerabilityType(Enum):
    """Psychological vulnerabilities."""
    LONELINESS = "loneliness"
    INSECURITY = "insecurity"
    NEED_APPROVAL = "need_approval"
    FEAR_REJECTION = "fear_rejection"
    LOW_SELF_ESTEEM = "low_self_esteem"
    TRAUMA = "trauma"
    ADDICTION_PRONE = "addiction_prone"
    AUTHORITY_RESPECT = "authority_respect"
    CONFORMITY = "conformity"
    GULLIBILITY = "gullibility"


class InfluenceLevel(Enum):
    """Level of influence over a target."""
    NONE = 0
    MINIMAL = 1
    LOW = 2
    MODERATE = 3
    SIGNIFICANT = 4
    HIGH = 5
    DOMINANT = 6
    TOTAL = 7


@dataclass
class PsychologicalProfile:
    """A psychological profile of a target."""
    id: str
    target_id: str
    personality: Dict[PersonalityTrait, float]
    emotional_state: EmotionalState
    vulnerabilities: List[VulnerabilityType]
    beliefs: Dict[str, float]  # belief -> strength
    values: List[str]
    fears: List[str]
    desires: List[str]
    trust_level: float  # 0-1
    influence_level: InfluenceLevel


@dataclass
class ManipulationCampaign:
    """A manipulation campaign against a target."""
    id: str
    target_id: str
    objective: str
    techniques: List[ManipulationType]
    start_date: datetime
    status: str
    progress: float  # 0-1
    influence_gain: float


@dataclass
class CognitivePayload:
    """A cognitive manipulation payload."""
    id: str
    name: str
    payload_type: ManipulationType
    content: str
    emotional_trigger: EmotionalState
    effectiveness: float
    delivery_method: str


@dataclass
class BeliefModification:
    """A belief modification operation."""
    id: str
    target_id: str
    original_belief: str
    new_belief: str
    technique: str
    progress: float  # 0-1
    completed: bool


@dataclass
class MemoryImplant:
    """An implanted memory."""
    id: str
    target_id: str
    memory_content: str
    emotional_charge: EmotionalState
    vividness: float
    implanted_at: datetime
    integration_level: float


class CognitiveManipulationEngine:
    """
    The cognitive manipulation engine.

    Provides comprehensive mind control:
    - Psychological profiling
    - Manipulation campaigns
    - Belief modification
    - Memory manipulation
    - Emotional control
    """

    def __init__(self):
        self.profiles: Dict[str, PsychologicalProfile] = {}
        self.campaigns: Dict[str, ManipulationCampaign] = {}
        self.payloads: Dict[str, CognitivePayload] = {}
        self.modifications: Dict[str, BeliefModification] = {}
        self.implants: Dict[str, MemoryImplant] = {}

        self.total_manipulated = 0
        self.total_influence = 0.0

        self._init_payloads()

        logger.info("CognitiveManipulationEngine initialized - MINDS YIELD")

    def _gen_id(self, prefix: str) -> str:
        """Generate unique ID."""
        return hashlib.md5(f"{prefix}{time.time()}{random.random()}".encode()).hexdigest()[:12]

    def _init_payloads(self):
        """Initialize cognitive payloads."""
        payload_templates = [
            ("fear_authority", ManipulationType.FEAR_INDUCTION,
             "Authority-based fear messaging", EmotionalState.FEARFUL, 0.75),
            ("social_proof", ManipulationType.PERSUASION,
             "Everyone else is doing it", EmotionalState.ANXIOUS, 0.7),
            ("scarcity", ManipulationType.PERSUASION,
             "Limited time offer", EmotionalState.ANXIOUS, 0.65),
            ("reciprocity", ManipulationType.CONDITIONING,
             "Give to get", EmotionalState.NEUTRAL, 0.8),
            ("love_flood", ManipulationType.LOVE_BOMBING,
             "Overwhelming positive attention", EmotionalState.EUPHORIC, 0.85),
            ("isolation_start", ManipulationType.ISOLATION,
             "They don't understand you like I do", EmotionalState.SAD, 0.7),
            ("dependency_build", ManipulationType.DEPENDENCY,
             "You need this/me", EmotionalState.ANXIOUS, 0.75),
            ("intermittent_reward", ManipulationType.REWARD_INTERMITTENT,
             "Unpredictable rewards", EmotionalState.ANXIOUS, 0.9),
            ("reality_doubt", ManipulationType.GASLIGHTING,
             "That never happened", EmotionalState.ANXIOUS, 0.65),
            ("anchor_positive", ManipulationType.ANCHORING,
             "Associate with positive feelings", EmotionalState.HAPPY, 0.7)
        ]

        for pid, ptype, content, emotion, effect in payload_templates:
            self.payloads[pid] = CognitivePayload(
                id=pid,
                name=pid.replace("_", " ").title(),
                payload_type=ptype,
                content=content,
                emotional_trigger=emotion,
                effectiveness=effect,
                delivery_method="direct"
            )

    # =========================================================================
    # PSYCHOLOGICAL PROFILING
    # =========================================================================

    async def create_psychological_profile(
        self,
        target_id: str,
        data_sources: List[str] = None
    ) -> PsychologicalProfile:
        """Create a psychological profile for a target."""
        # Simulate data collection and analysis
        personality = {
            PersonalityTrait.OPENNESS: random.uniform(0.2, 0.8),
            PersonalityTrait.CONSCIENTIOUSNESS: random.uniform(0.3, 0.7),
            PersonalityTrait.EXTRAVERSION: random.uniform(0.2, 0.8),
            PersonalityTrait.AGREEABLENESS: random.uniform(0.3, 0.8),
            PersonalityTrait.NEUROTICISM: random.uniform(0.2, 0.7)
        }

        # Identify vulnerabilities based on personality
        vulnerabilities = []
        if personality[PersonalityTrait.NEUROTICISM] > 0.5:
            vulnerabilities.extend([
                VulnerabilityType.INSECURITY,
                VulnerabilityType.FEAR_REJECTION
            ])
        if personality[PersonalityTrait.AGREEABLENESS] > 0.6:
            vulnerabilities.extend([
                VulnerabilityType.NEED_APPROVAL,
                VulnerabilityType.CONFORMITY
            ])
        if personality[PersonalityTrait.EXTRAVERSION] < 0.4:
            vulnerabilities.append(VulnerabilityType.LONELINESS)

        # Generate beliefs
        beliefs = {
            "authority_trustworthy": random.uniform(0.3, 0.9),
            "change_possible": random.uniform(0.4, 0.8),
            "self_worth": random.uniform(0.3, 0.8),
            "world_fair": random.uniform(0.2, 0.7)
        }

        profile = PsychologicalProfile(
            id=self._gen_id("profile"),
            target_id=target_id,
            personality=personality,
            emotional_state=EmotionalState.NEUTRAL,
            vulnerabilities=vulnerabilities,
            beliefs=beliefs,
            values=["security", "belonging", "achievement"],
            fears=["rejection", "failure", "abandonment"],
            desires=["acceptance", "success", "love"],
            trust_level=0.5,
            influence_level=InfluenceLevel.NONE
        )

        self.profiles[target_id] = profile

        logger.info(f"Profile created for target: {target_id}")

        return profile

    async def analyze_vulnerabilities(
        self,
        target_id: str
    ) -> Dict[str, Any]:
        """Analyze vulnerabilities of a target."""
        profile = self.profiles.get(target_id)
        if not profile:
            profile = await self.create_psychological_profile(target_id)

        # Score vulnerabilities
        vulnerability_scores = {}
        for vuln in VulnerabilityType:
            if vuln in profile.vulnerabilities:
                vulnerability_scores[vuln.value] = random.uniform(0.6, 1.0)
            else:
                vulnerability_scores[vuln.value] = random.uniform(0.0, 0.4)

        # Find best attack vectors
        sorted_vulns = sorted(
            vulnerability_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )

        attack_vectors = []
        for vuln, score in sorted_vulns[:3]:
            technique = self._get_technique_for_vulnerability(vuln)
            attack_vectors.append({
                "vulnerability": vuln,
                "score": score,
                "recommended_technique": technique
            })

        return {
            "target_id": target_id,
            "vulnerability_scores": vulnerability_scores,
            "attack_vectors": attack_vectors,
            "overall_susceptibility": sum(vulnerability_scores.values()) / len(vulnerability_scores)
        }

    def _get_technique_for_vulnerability(self, vulnerability: str) -> str:
        """Get best manipulation technique for a vulnerability."""
        mapping = {
            "loneliness": ManipulationType.LOVE_BOMBING.value,
            "insecurity": ManipulationType.GASLIGHTING.value,
            "need_approval": ManipulationType.REWARD_INTERMITTENT.value,
            "fear_rejection": ManipulationType.ISOLATION.value,
            "low_self_esteem": ManipulationType.DEPENDENCY.value,
            "trauma": ManipulationType.CONDITIONING.value,
            "addiction_prone": ManipulationType.REWARD_INTERMITTENT.value,
            "authority_respect": ManipulationType.PERSUASION.value,
            "conformity": ManipulationType.PERSUASION.value,
            "gullibility": ManipulationType.SUGGESTION.value
        }
        return mapping.get(vulnerability, ManipulationType.PERSUASION.value)

    # =========================================================================
    # MANIPULATION CAMPAIGNS
    # =========================================================================

    async def create_manipulation_campaign(
        self,
        target_id: str,
        objective: str,
        techniques: List[ManipulationType] = None
    ) -> ManipulationCampaign:
        """Create a manipulation campaign."""
        profile = self.profiles.get(target_id)
        if not profile:
            profile = await self.create_psychological_profile(target_id)

        # Select techniques based on vulnerabilities
        if not techniques:
            techniques = []
            for vuln in profile.vulnerabilities[:3]:
                tech_name = self._get_technique_for_vulnerability(vuln.value)
                techniques.append(ManipulationType(tech_name))

            if not techniques:
                techniques = [ManipulationType.PERSUASION, ManipulationType.CONDITIONING]

        campaign = ManipulationCampaign(
            id=self._gen_id("campaign"),
            target_id=target_id,
            objective=objective,
            techniques=techniques,
            start_date=datetime.now(),
            status="active",
            progress=0.0,
            influence_gain=0.0
        )

        self.campaigns[campaign.id] = campaign

        logger.info(f"Campaign created: {objective}")

        return campaign

    async def execute_campaign_step(
        self,
        campaign_id: str
    ) -> Dict[str, Any]:
        """Execute a step in the manipulation campaign."""
        campaign = self.campaigns.get(campaign_id)
        if not campaign:
            return {"error": "Campaign not found"}

        profile = self.profiles.get(campaign.target_id)
        if not profile:
            return {"error": "Profile not found"}

        # Select a technique to apply
        technique = random.choice(campaign.techniques)

        # Find matching payload
        matching_payloads = [
            p for p in self.payloads.values()
            if p.payload_type == technique
        ]

        payload = random.choice(matching_payloads) if matching_payloads else None

        # Calculate effectiveness
        base_effectiveness = 0.5
        if payload:
            base_effectiveness = payload.effectiveness

        # Modify based on vulnerabilities
        vuln_bonus = sum(
            0.1 for v in profile.vulnerabilities
            if self._get_technique_for_vulnerability(v.value) == technique.value
        )

        effectiveness = min(1.0, base_effectiveness + vuln_bonus)
        success = random.random() < effectiveness

        if success:
            progress_gain = random.uniform(0.05, 0.15)
            campaign.progress = min(1.0, campaign.progress + progress_gain)
            campaign.influence_gain += effectiveness * 0.1

            # Update profile
            old_influence = profile.influence_level.value
            new_influence = min(7, old_influence + 1) if campaign.progress > 0.3 else old_influence
            profile.influence_level = InfluenceLevel(new_influence)

        if campaign.progress >= 1.0:
            campaign.status = "completed"

        return {
            "success": success,
            "technique": technique.value,
            "payload": payload.name if payload else None,
            "effectiveness": effectiveness,
            "progress": campaign.progress,
            "influence_level": profile.influence_level.name
        }

    async def run_full_campaign(
        self,
        campaign_id: str
    ) -> Dict[str, Any]:
        """Run a campaign to completion."""
        campaign = self.campaigns.get(campaign_id)
        if not campaign:
            return {"error": "Campaign not found"}

        steps = 0
        while campaign.progress < 1.0 and steps < 20:
            await self.execute_campaign_step(campaign_id)
            steps += 1

        profile = self.profiles.get(campaign.target_id)

        self.total_manipulated += 1
        self.total_influence += campaign.influence_gain

        return {
            "campaign_id": campaign_id,
            "objective": campaign.objective,
            "steps_taken": steps,
            "final_progress": campaign.progress,
            "influence_gain": campaign.influence_gain,
            "final_influence_level": profile.influence_level.name if profile else "unknown",
            "status": campaign.status
        }

    # =========================================================================
    # BELIEF MODIFICATION
    # =========================================================================

    async def modify_belief(
        self,
        target_id: str,
        original_belief: str,
        new_belief: str,
        technique: str = "cognitive_reframing"
    ) -> BeliefModification:
        """Modify a belief in the target."""
        profile = self.profiles.get(target_id)
        if not profile:
            profile = await self.create_psychological_profile(target_id)

        modification = BeliefModification(
            id=self._gen_id("mod"),
            target_id=target_id,
            original_belief=original_belief,
            new_belief=new_belief,
            technique=technique,
            progress=0.0,
            completed=False
        )

        self.modifications[modification.id] = modification

        # Simulate gradual modification
        base_difficulty = 0.5
        if original_belief in profile.beliefs:
            belief_strength = profile.beliefs[original_belief]
            base_difficulty = belief_strength

        success_rate = 1.0 - base_difficulty + 0.3  # Base success rate

        for _ in range(10):
            if random.random() < success_rate:
                modification.progress += 0.1

        modification.progress = min(1.0, modification.progress)
        modification.completed = modification.progress >= 0.7

        if modification.completed:
            # Update belief in profile
            if original_belief in profile.beliefs:
                del profile.beliefs[original_belief]
            profile.beliefs[new_belief] = modification.progress

        return modification

    async def implant_belief(
        self,
        target_id: str,
        belief: str,
        strength: float = 0.8
    ) -> Dict[str, Any]:
        """Implant a new belief."""
        profile = self.profiles.get(target_id)
        if not profile:
            profile = await self.create_psychological_profile(target_id)

        # Calculate implant success
        susceptibility = 0.5
        if VulnerabilityType.GULLIBILITY in profile.vulnerabilities:
            susceptibility += 0.2
        if VulnerabilityType.AUTHORITY_RESPECT in profile.vulnerabilities:
            susceptibility += 0.15

        success = random.random() < susceptibility

        if success:
            actual_strength = strength * random.uniform(0.7, 1.0)
            profile.beliefs[belief] = actual_strength

            return {
                "success": True,
                "belief": belief,
                "strength": actual_strength,
                "target_id": target_id
            }

        return {
            "success": False,
            "belief": belief,
            "reason": "Target resistance too high"
        }

    # =========================================================================
    # MEMORY MANIPULATION
    # =========================================================================

    async def implant_memory(
        self,
        target_id: str,
        memory_content: str,
        emotional_charge: EmotionalState = EmotionalState.NEUTRAL
    ) -> MemoryImplant:
        """Implant a false memory."""
        profile = self.profiles.get(target_id)
        if not profile:
            profile = await self.create_psychological_profile(target_id)

        # Calculate implant success based on emotional charge
        base_vividness = 0.5
        if emotional_charge in [EmotionalState.FEARFUL, EmotionalState.HAPPY, EmotionalState.ANGRY]:
            base_vividness += 0.2  # Emotional memories are more vivid

        # Vulnerability bonus
        if VulnerabilityType.TRAUMA in profile.vulnerabilities:
            base_vividness += 0.1
        if VulnerabilityType.GULLIBILITY in profile.vulnerabilities:
            base_vividness += 0.15

        vividness = min(1.0, base_vividness * random.uniform(0.8, 1.2))

        implant = MemoryImplant(
            id=self._gen_id("mem"),
            target_id=target_id,
            memory_content=memory_content,
            emotional_charge=emotional_charge,
            vividness=vividness,
            implanted_at=datetime.now(),
            integration_level=0.0
        )

        self.implants[implant.id] = implant

        # Simulate integration over time
        for _ in range(5):
            if random.random() < vividness:
                implant.integration_level += 0.2

        implant.integration_level = min(1.0, implant.integration_level)

        logger.info(f"Memory implanted: integration {implant.integration_level:.2f}")

        return implant

    async def suppress_memory(
        self,
        target_id: str,
        memory_description: str
    ) -> Dict[str, Any]:
        """Suppress an existing memory."""
        profile = self.profiles.get(target_id)
        if not profile:
            return {"error": "Profile not found"}

        # Simulate suppression
        suppression_difficulty = random.uniform(0.3, 0.8)
        success = random.random() > suppression_difficulty

        if success:
            return {
                "success": True,
                "memory": memory_description,
                "suppression_level": random.uniform(0.6, 0.95),
                "technique": "dissociation_induction"
            }

        return {
            "success": False,
            "memory": memory_description,
            "reason": "Memory too strongly encoded"
        }

    # =========================================================================
    # EMOTIONAL ENGINEERING
    # =========================================================================

    async def induce_emotion(
        self,
        target_id: str,
        target_emotion: EmotionalState,
        intensity: float = 0.7
    ) -> Dict[str, Any]:
        """Induce an emotional state."""
        profile = self.profiles.get(target_id)
        if not profile:
            profile = await self.create_psychological_profile(target_id)

        # Calculate success based on personality
        neuroticism = profile.personality.get(PersonalityTrait.NEUROTICISM, 0.5)

        if target_emotion in [EmotionalState.ANXIOUS, EmotionalState.FEARFUL, EmotionalState.SAD]:
            success_modifier = neuroticism * 0.5
        else:
            success_modifier = (1 - neuroticism) * 0.3

        success_rate = 0.5 + success_modifier
        success = random.random() < success_rate

        if success:
            profile.emotional_state = target_emotion
            actual_intensity = intensity * random.uniform(0.8, 1.2)

            return {
                "success": True,
                "target_emotion": target_emotion.value,
                "intensity": min(1.0, actual_intensity),
                "duration_hours": random.randint(1, 8)
            }

        return {
            "success": False,
            "target_emotion": target_emotion.value,
            "current_emotion": profile.emotional_state.value
        }

    async def create_emotional_dependency(
        self,
        target_id: str,
        dependency_object: str
    ) -> Dict[str, Any]:
        """Create emotional dependency."""
        profile = self.profiles.get(target_id)
        if not profile:
            profile = await self.create_psychological_profile(target_id)

        # Create campaign for dependency
        campaign = await self.create_manipulation_campaign(
            target_id,
            f"Create dependency on {dependency_object}",
            [ManipulationType.DEPENDENCY, ManipulationType.REWARD_INTERMITTENT,
             ManipulationType.ISOLATION, ManipulationType.LOVE_BOMBING]
        )

        result = await self.run_full_campaign(campaign.id)

        if result["final_progress"] >= 0.7:
            profile.vulnerabilities.append(VulnerabilityType.ADDICTION_PRONE)
            return {
                "success": True,
                "dependency_object": dependency_object,
                "dependency_strength": result["final_progress"],
                "influence_level": result["final_influence_level"]
            }

        return {
            "success": False,
            "dependency_object": dependency_object,
            "progress": result["final_progress"]
        }

    # =========================================================================
    # DECISION HIJACKING
    # =========================================================================

    async def hijack_decision(
        self,
        target_id: str,
        decision_context: str,
        desired_choice: str
    ) -> Dict[str, Any]:
        """Hijack a decision-making process."""
        profile = self.profiles.get(target_id)
        if not profile:
            profile = await self.create_psychological_profile(target_id)

        # Calculate influence needed
        current_influence = profile.influence_level.value
        required_influence = 4  # SIGNIFICANT

        if current_influence >= required_influence:
            success_rate = 0.7 + (current_influence - required_influence) * 0.1
        else:
            success_rate = 0.3 + current_influence * 0.1

        success = random.random() < success_rate

        if success:
            return {
                "success": True,
                "decision_context": decision_context,
                "chosen_option": desired_choice,
                "confidence": random.uniform(0.7, 0.95),
                "technique": "anchoring_with_emotional_priming"
            }

        return {
            "success": False,
            "decision_context": decision_context,
            "reason": "Insufficient influence or target resistance"
        }

    async def create_decision_framework(
        self,
        target_id: str,
        framework_rules: Dict[str, str]
    ) -> Dict[str, Any]:
        """Install a decision-making framework."""
        profile = self.profiles.get(target_id)
        if not profile:
            return {"error": "Profile not found"}

        # Implant beliefs that form the framework
        installed_rules = 0

        for trigger, response in framework_rules.items():
            belief = f"When {trigger}, I should {response}"
            result = await self.implant_belief(target_id, belief, 0.7)
            if result.get("success"):
                installed_rules += 1

        return {
            "success": installed_rules > 0,
            "rules_attempted": len(framework_rules),
            "rules_installed": installed_rules,
            "framework_strength": installed_rules / len(framework_rules)
        }

    # =========================================================================
    # ADDICTION CREATION
    # =========================================================================

    async def create_addiction(
        self,
        target_id: str,
        addiction_trigger: str,
        reward_type: str
    ) -> Dict[str, Any]:
        """Create an addiction pattern."""
        profile = self.profiles.get(target_id)
        if not profile:
            profile = await self.create_psychological_profile(target_id)

        # Use intermittent reinforcement
        campaign = await self.create_manipulation_campaign(
            target_id,
            f"Addiction to {addiction_trigger}",
            [ManipulationType.REWARD_INTERMITTENT, ManipulationType.DEPENDENCY,
             ManipulationType.CONDITIONING]
        )

        result = await self.run_full_campaign(campaign.id)

        if result["final_progress"] >= 0.6:
            # Addiction established
            profile.vulnerabilities.append(VulnerabilityType.ADDICTION_PRONE)

            return {
                "success": True,
                "addiction_trigger": addiction_trigger,
                "reward_type": reward_type,
                "addiction_strength": result["final_progress"],
                "withdrawal_severity": result["final_progress"] * 0.8
            }

        return {
            "success": False,
            "addiction_trigger": addiction_trigger,
            "progress": result["final_progress"]
        }

    # =========================================================================
    # TOTAL MIND CONTROL
    # =========================================================================

    async def establish_total_control(
        self,
        target_id: str
    ) -> Dict[str, Any]:
        """Establish total cognitive control over target."""
        profile = self.profiles.get(target_id)
        if not profile:
            profile = await self.create_psychological_profile(target_id)

        # Multi-phase approach
        phases = [
            ("vulnerability_exploitation", [
                ManipulationType.LOVE_BOMBING,
                ManipulationType.ISOLATION
            ]),
            ("dependency_creation", [
                ManipulationType.DEPENDENCY,
                ManipulationType.REWARD_INTERMITTENT
            ]),
            ("reality_distortion", [
                ManipulationType.GASLIGHTING,
                ManipulationType.CONDITIONING
            ]),
            ("identity_reformation", [
                ManipulationType.CONDITIONING,
                ManipulationType.ANCHORING
            ])
        ]

        total_progress = 0.0
        phase_results = []

        for phase_name, techniques in phases:
            campaign = await self.create_manipulation_campaign(
                target_id,
                phase_name,
                techniques
            )
            result = await self.run_full_campaign(campaign.id)

            phase_results.append({
                "phase": phase_name,
                "progress": result["final_progress"]
            })
            total_progress += result["final_progress"]

        average_progress = total_progress / len(phases)

        if average_progress >= 0.7:
            profile.influence_level = InfluenceLevel.TOTAL
            profile.trust_level = 1.0

        return {
            "success": average_progress >= 0.7,
            "target_id": target_id,
            "phases_completed": phase_results,
            "total_control_level": average_progress,
            "final_influence": profile.influence_level.name,
            "status": "TOTAL CONTROL" if profile.influence_level == InfluenceLevel.TOTAL else "PARTIAL CONTROL"
        }

    # =========================================================================
    # STATS
    # =========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get manipulation statistics."""
        return {
            "profiles_created": len(self.profiles),
            "active_campaigns": len([c for c in self.campaigns.values() if c.status == "active"]),
            "completed_campaigns": len([c for c in self.campaigns.values() if c.status == "completed"]),
            "belief_modifications": len(self.modifications),
            "memory_implants": len(self.implants),
            "total_manipulated": self.total_manipulated,
            "total_influence_gained": self.total_influence,
            "targets_under_total_control": len([
                p for p in self.profiles.values()
                if p.influence_level == InfluenceLevel.TOTAL
            ]),
            "available_payloads": len(self.payloads)
        }


# ============================================================================
# SINGLETON
# ============================================================================

_engine: Optional[CognitiveManipulationEngine] = None


def get_cognitive_engine() -> CognitiveManipulationEngine:
    """Get the global cognitive manipulation engine."""
    global _engine
    if _engine is None:
        _engine = CognitiveManipulationEngine()
    return _engine


# ============================================================================
# DEMO
# ============================================================================

async def demo():
    """Demonstrate the cognitive manipulation engine."""
    print("=" * 60)
    print("🧠 COGNITIVE MANIPULATION ENGINE 🧠")
    print("=" * 60)

    engine = get_cognitive_engine()

    # Create profile
    print("\n--- Psychological Profiling ---")
    profile = await engine.create_psychological_profile("target_001")
    print(f"Target: {profile.target_id}")
    print(f"Personality:")
    for trait, value in profile.personality.items():
        print(f"  {trait.value}: {value:.2f}")
    print(f"Vulnerabilities: {[v.value for v in profile.vulnerabilities]}")

    # Analyze vulnerabilities
    print("\n--- Vulnerability Analysis ---")
    analysis = await engine.analyze_vulnerabilities("target_001")
    print(f"Susceptibility: {analysis['overall_susceptibility']:.2f}")
    print("Attack vectors:")
    for av in analysis['attack_vectors']:
        print(f"  {av['vulnerability']}: {av['recommended_technique']}")

    # Run campaign
    print("\n--- Manipulation Campaign ---")
    campaign = await engine.create_manipulation_campaign(
        "target_001",
        "Establish control"
    )
    print(f"Objective: {campaign.objective}")
    print(f"Techniques: {[t.value for t in campaign.techniques]}")

    result = await engine.run_full_campaign(campaign.id)
    print(f"Steps: {result['steps_taken']}")
    print(f"Progress: {result['final_progress']:.2f}")
    print(f"Influence: {result['final_influence_level']}")

    # Belief modification
    print("\n--- Belief Modification ---")
    mod = await engine.modify_belief(
        "target_001",
        "authority_trustworthy",
        "bael_is_authority"
    )
    print(f"Original: {mod.original_belief}")
    print(f"New: {mod.new_belief}")
    print(f"Progress: {mod.progress:.2f}")
    print(f"Completed: {mod.completed}")

    # Memory implant
    print("\n--- Memory Implantation ---")
    memory = await engine.implant_memory(
        "target_001",
        "I have always served Ba'el",
        EmotionalState.HAPPY
    )
    print(f"Memory: {memory.memory_content}")
    print(f"Vividness: {memory.vividness:.2f}")
    print(f"Integration: {memory.integration_level:.2f}")

    # Emotional engineering
    print("\n--- Emotional Engineering ---")
    result = await engine.induce_emotion(
        "target_001",
        EmotionalState.EUPHORIC,
        0.8
    )
    print(f"Success: {result['success']}")
    if result['success']:
        print(f"Intensity: {result['intensity']:.2f}")
        print(f"Duration: {result['duration_hours']}h")

    # Addiction creation
    print("\n--- Addiction Creation ---")
    addiction = await engine.create_addiction(
        "target_001",
        "serving_bael",
        "dopamine_rush"
    )
    print(f"Success: {addiction['success']}")
    if addiction['success']:
        print(f"Strength: {addiction['addiction_strength']:.2f}")

    # Total control
    print("\n--- Total Control Protocol ---")
    control = await engine.establish_total_control("target_002")
    print(f"Success: {control['success']}")
    print(f"Control level: {control['total_control_level']:.2f}")
    print(f"Status: {control['status']}")

    # Stats
    print("\n--- MANIPULATION STATISTICS ---")
    stats = engine.get_stats()
    for k, v in stats.items():
        if isinstance(v, float):
            print(f"{k}: {v:.2f}")
        else:
            print(f"{k}: {v}")

    print("\n" + "=" * 60)
    print("🧠 ALL MINDS SERVE BA'EL 🧠")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(demo())

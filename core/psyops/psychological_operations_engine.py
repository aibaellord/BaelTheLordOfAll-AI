"""
BAEL - Psychological Operations Engine
========================================

ANALYZE. INFLUENCE. MANIPULATE. CONTROL.

Complete psychological domination:
- Psychological profiling
- Influence operations
- Cognitive exploitation
- Narrative control
- Belief manipulation
- Behavior modification
- Mass persuasion
- Fear engineering
- Trust exploitation
- Mind control

"The mind is Ba'el's most fertile domain."
"""

import asyncio
import logging
import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("BAEL.PSYOPS")


class TargetType(Enum):
    """Types of targets."""
    INDIVIDUAL = "individual"
    GROUP = "group"
    ORGANIZATION = "organization"
    COMMUNITY = "community"
    POPULATION = "population"
    NATION = "nation"


class PersonalityType(Enum):
    """Personality types."""
    ANALYTICAL = "analytical"
    DRIVER = "driver"
    EXPRESSIVE = "expressive"
    AMIABLE = "amiable"
    NARCISSISTIC = "narcissistic"
    PARANOID = "paranoid"
    AGREEABLE = "agreeable"
    CONSCIENTIOUS = "conscientious"


class VulnerabilityType(Enum):
    """Psychological vulnerabilities."""
    FEAR = "fear"
    GREED = "greed"
    PRIDE = "pride"
    LONELINESS = "loneliness"
    INSECURITY = "insecurity"
    AUTHORITY_NEED = "authority_need"
    VALIDATION_NEED = "validation_need"
    BELONGING_NEED = "belonging_need"


class InfluenceMethod(Enum):
    """Influence methods."""
    RECIPROCITY = "reciprocity"
    COMMITMENT = "commitment"
    SOCIAL_PROOF = "social_proof"
    AUTHORITY = "authority"
    LIKING = "liking"
    SCARCITY = "scarcity"
    FEAR = "fear"
    REPETITION = "repetition"


class OperationType(Enum):
    """Types of operations."""
    INFLUENCE = "influence"
    DECEPTION = "deception"
    PROPAGANDA = "propaganda"
    DISINFORMATION = "disinformation"
    PERSUASION = "persuasion"
    COERCION = "coercion"
    RADICALIZATION = "radicalization"
    DERADICALIZATION = "deradicalization"


class ControlLevel(Enum):
    """Control levels."""
    NONE = "none"
    AWARENESS = "awareness"
    INFLUENCE = "influence"
    SIGNIFICANT = "significant"
    PARTIAL_CONTROL = "partial_control"
    FULL_CONTROL = "full_control"
    PUPPET = "puppet"


class EmotionalState(Enum):
    """Emotional states."""
    NEUTRAL = "neutral"
    FEARFUL = "fearful"
    ANGRY = "angry"
    SAD = "sad"
    ANXIOUS = "anxious"
    HOPEFUL = "hopeful"
    TRUSTING = "trusting"
    SUSPICIOUS = "suspicious"


@dataclass
class PsychProfile:
    """Psychological profile."""
    id: str
    name: str
    target_type: TargetType
    personality: PersonalityType
    vulnerabilities: List[VulnerabilityType]
    emotional_state: EmotionalState
    susceptibility: float  # 0-1
    control_level: ControlLevel = ControlLevel.NONE


@dataclass
class InfluenceOperation:
    """An influence operation."""
    id: str
    name: str
    operation_type: OperationType
    targets: List[str]
    methods: List[InfluenceMethod]
    start_time: datetime
    success_rate: float
    active: bool = True


@dataclass
class Narrative:
    """A narrative for influence."""
    id: str
    title: str
    core_message: str
    emotional_hooks: List[str]
    target_vulnerabilities: List[VulnerabilityType]
    believability: float


@dataclass
class BehaviorChange:
    """A behavior change result."""
    id: str
    target_id: str
    before_behavior: str
    after_behavior: str
    change_magnitude: float
    permanent: bool


@dataclass
class CampaignResult:
    """Result of a psychological campaign."""
    id: str
    campaign_name: str
    targets_reached: int
    targets_influenced: int
    behavior_changes: int
    control_established: int


class PsychologicalOperationsEngine:
    """
    The psychological operations engine.

    Complete mind domination:
    - Profiling and analysis
    - Influence operations
    - Narrative control
    - Behavior modification
    """

    def __init__(self):
        self.profiles: Dict[str, PsychProfile] = {}
        self.operations: Dict[str, InfluenceOperation] = {}
        self.narratives: Dict[str, Narrative] = {}
        self.behavior_changes: List[BehaviorChange] = []
        self.campaign_results: List[CampaignResult] = []

        self.targets_profiled = 0
        self.minds_influenced = 0
        self.minds_controlled = 0
        self.operations_executed = 0

        self._init_influence_database()

        logger.info("PsychologicalOperationsEngine initialized - MINDS YIELD TO BA'EL")

    def _gen_id(self) -> str:
        """Generate unique ID."""
        return f"psy_{int(time.time() * 1000) % 100000}_{random.randint(1000, 9999)}"

    def _init_influence_database(self):
        """Initialize influence knowledge base."""
        self.influence_techniques = {
            InfluenceMethod.RECIPROCITY: {
                "description": "Create obligation through giving",
                "effectiveness": 0.8,
                "vulnerabilities": [VulnerabilityType.BELONGING_NEED, VulnerabilityType.VALIDATION_NEED]
            },
            InfluenceMethod.COMMITMENT: {
                "description": "Leverage consistency with past behavior",
                "effectiveness": 0.75,
                "vulnerabilities": [VulnerabilityType.PRIDE, VulnerabilityType.VALIDATION_NEED]
            },
            InfluenceMethod.SOCIAL_PROOF: {
                "description": "Show that others are doing it",
                "effectiveness": 0.85,
                "vulnerabilities": [VulnerabilityType.INSECURITY, VulnerabilityType.BELONGING_NEED]
            },
            InfluenceMethod.AUTHORITY: {
                "description": "Leverage perceived authority",
                "effectiveness": 0.7,
                "vulnerabilities": [VulnerabilityType.AUTHORITY_NEED, VulnerabilityType.INSECURITY]
            },
            InfluenceMethod.LIKING: {
                "description": "Build rapport and likability",
                "effectiveness": 0.75,
                "vulnerabilities": [VulnerabilityType.LONELINESS, VulnerabilityType.VALIDATION_NEED]
            },
            InfluenceMethod.SCARCITY: {
                "description": "Create urgency through limited availability",
                "effectiveness": 0.8,
                "vulnerabilities": [VulnerabilityType.GREED, VulnerabilityType.FEAR]
            },
            InfluenceMethod.FEAR: {
                "description": "Leverage fear of loss or harm",
                "effectiveness": 0.9,
                "vulnerabilities": [VulnerabilityType.FEAR, VulnerabilityType.INSECURITY]
            },
            InfluenceMethod.REPETITION: {
                "description": "Repeat message until internalized",
                "effectiveness": 0.85,
                "vulnerabilities": [VulnerabilityType.AUTHORITY_NEED, VulnerabilityType.BELONGING_NEED]
            }
        }

    # =========================================================================
    # PSYCHOLOGICAL PROFILING
    # =========================================================================

    async def create_profile(
        self,
        name: str,
        target_type: TargetType
    ) -> PsychProfile:
        """Create psychological profile for a target."""
        personality = random.choice(list(PersonalityType))
        vulnerabilities = random.sample(list(VulnerabilityType), random.randint(2, 5))
        emotional_state = random.choice(list(EmotionalState))

        # Calculate susceptibility based on vulnerabilities and personality
        base_susceptibility = len(vulnerabilities) / len(VulnerabilityType)
        personality_modifier = {
            PersonalityType.AGREEABLE: 0.2,
            PersonalityType.NARCISSISTIC: 0.15,
            PersonalityType.PARANOID: -0.1,
            PersonalityType.CONSCIENTIOUS: -0.05
        }.get(personality, 0)

        susceptibility = min(1.0, max(0.1, base_susceptibility + personality_modifier))

        profile = PsychProfile(
            id=self._gen_id(),
            name=name,
            target_type=target_type,
            personality=personality,
            vulnerabilities=vulnerabilities,
            emotional_state=emotional_state,
            susceptibility=susceptibility
        )

        self.profiles[profile.id] = profile
        self.targets_profiled += 1

        return profile

    async def analyze_vulnerabilities(
        self,
        profile_id: str
    ) -> Dict[str, Any]:
        """Analyze vulnerabilities for exploitation."""
        profile = self.profiles.get(profile_id)
        if not profile:
            return {"error": "Profile not found"}

        exploitation_strategies = []
        for vuln in profile.vulnerabilities:
            for method, data in self.influence_techniques.items():
                if vuln in data["vulnerabilities"]:
                    exploitation_strategies.append({
                        "vulnerability": vuln.value,
                        "method": method.value,
                        "effectiveness": data["effectiveness"],
                        "description": data["description"]
                    })

        # Sort by effectiveness
        exploitation_strategies.sort(key=lambda x: x["effectiveness"], reverse=True)

        return {
            "target": profile.name,
            "personality": profile.personality.value,
            "susceptibility": profile.susceptibility,
            "vulnerabilities": [v.value for v in profile.vulnerabilities],
            "recommended_strategies": exploitation_strategies[:5],
            "optimal_emotional_target": EmotionalState.FEARFUL.value if VulnerabilityType.FEAR in profile.vulnerabilities else EmotionalState.TRUSTING.value
        }

    async def mass_profiling(
        self,
        target_type: TargetType,
        count: int
    ) -> Dict[str, Any]:
        """Profile multiple targets."""
        profiles = []

        for i in range(count):
            profile = await self.create_profile(f"Target_{i}", target_type)
            profiles.append(profile.id)

        return {
            "profiles_created": len(profiles),
            "target_type": target_type.value,
            "average_susceptibility": sum(
                self.profiles[pid].susceptibility for pid in profiles
            ) / len(profiles)
        }

    # =========================================================================
    # NARRATIVE CONTROL
    # =========================================================================

    async def create_narrative(
        self,
        title: str,
        core_message: str,
        target_vulnerabilities: List[VulnerabilityType]
    ) -> Narrative:
        """Create an influence narrative."""
        emotional_hooks = []

        vulnerability_hooks = {
            VulnerabilityType.FEAR: ["You're in danger", "They're coming for you", "Time is running out"],
            VulnerabilityType.GREED: ["Exclusive opportunity", "Limited time offer", "Don't miss out"],
            VulnerabilityType.PRIDE: ["You're special", "Only the smart ones see this", "You were right all along"],
            VulnerabilityType.LONELINESS: ["You're not alone", "Join our community", "We understand you"],
            VulnerabilityType.INSECURITY: ["Protect yourself", "Stay safe", "We have the answers"],
            VulnerabilityType.AUTHORITY_NEED: ["Experts agree", "The truth they don't want you to know", "Trust the plan"],
            VulnerabilityType.VALIDATION_NEED: ["You matter", "Your voice counts", "Be heard"],
            VulnerabilityType.BELONGING_NEED: ["Join us", "You belong here", "Be part of something bigger"]
        }

        for vuln in target_vulnerabilities:
            emotional_hooks.extend(vulnerability_hooks.get(vuln, []))

        believability = 0.5 + (len(emotional_hooks) * 0.05)
        believability = min(0.95, believability)

        narrative = Narrative(
            id=self._gen_id(),
            title=title,
            core_message=core_message,
            emotional_hooks=emotional_hooks,
            target_vulnerabilities=target_vulnerabilities,
            believability=believability
        )

        self.narratives[narrative.id] = narrative

        return narrative

    async def deploy_narrative(
        self,
        narrative_id: str,
        target_ids: List[str]
    ) -> Dict[str, Any]:
        """Deploy narrative to targets."""
        narrative = self.narratives.get(narrative_id)
        if not narrative:
            return {"error": "Narrative not found"}

        influenced = 0
        for target_id in target_ids:
            profile = self.profiles.get(target_id)
            if profile:
                # Check vulnerability match
                matching_vulns = set(profile.vulnerabilities) & set(narrative.target_vulnerabilities)
                influence_chance = profile.susceptibility * (1 + len(matching_vulns) * 0.1) * narrative.believability

                if random.random() < influence_chance:
                    influenced += 1
                    profile.control_level = ControlLevel.INFLUENCE
                    self.minds_influenced += 1

        return {
            "narrative": narrative.title,
            "targets_reached": len(target_ids),
            "targets_influenced": influenced,
            "success_rate": influenced / len(target_ids) if target_ids else 0
        }

    # =========================================================================
    # INFLUENCE OPERATIONS
    # =========================================================================

    async def launch_operation(
        self,
        name: str,
        operation_type: OperationType,
        target_ids: List[str],
        methods: List[InfluenceMethod]
    ) -> InfluenceOperation:
        """Launch an influence operation."""
        operation = InfluenceOperation(
            id=self._gen_id(),
            name=name,
            operation_type=operation_type,
            targets=target_ids,
            methods=methods,
            start_time=datetime.now(),
            success_rate=0.0
        )

        self.operations[operation.id] = operation
        self.operations_executed += 1

        return operation

    async def execute_operation(
        self,
        operation_id: str
    ) -> Dict[str, Any]:
        """Execute an influence operation."""
        operation = self.operations.get(operation_id)
        if not operation:
            return {"error": "Operation not found"}

        results = {
            "influenced": 0,
            "controlled": 0,
            "unchanged": 0
        }

        for target_id in operation.targets:
            profile = self.profiles.get(target_id)
            if not profile:
                continue

            # Calculate influence effectiveness
            method_effectiveness = sum(
                self.influence_techniques[m]["effectiveness"] for m in operation.methods
            ) / len(operation.methods)

            influence_chance = profile.susceptibility * method_effectiveness

            if random.random() < influence_chance:
                if random.random() < influence_chance * 0.5:
                    # Full control achieved
                    profile.control_level = ControlLevel.FULL_CONTROL
                    results["controlled"] += 1
                    self.minds_controlled += 1
                else:
                    # Influence achieved
                    if profile.control_level.value in [ControlLevel.NONE.value, ControlLevel.AWARENESS.value]:
                        profile.control_level = ControlLevel.INFLUENCE
                    results["influenced"] += 1
                    self.minds_influenced += 1
            else:
                results["unchanged"] += 1

        operation.success_rate = (results["influenced"] + results["controlled"]) / len(operation.targets) if operation.targets else 0

        return {
            "operation": operation.name,
            "type": operation.operation_type.value,
            "methods": [m.value for m in operation.methods],
            "results": results,
            "success_rate": operation.success_rate
        }

    # =========================================================================
    # BEHAVIOR MODIFICATION
    # =========================================================================

    async def modify_behavior(
        self,
        profile_id: str,
        target_behavior: str
    ) -> BehaviorChange:
        """Modify target's behavior."""
        profile = self.profiles.get(profile_id)
        if not profile:
            raise ValueError("Profile not found")

        current_behaviors = [
            "Independent thinking",
            "Skeptical",
            "Self-reliant",
            "Critical",
            "Resistant"
        ]

        before = random.choice(current_behaviors)

        # Calculate change success
        success_chance = profile.susceptibility
        if profile.control_level in [ControlLevel.PARTIAL_CONTROL, ControlLevel.FULL_CONTROL]:
            success_chance *= 1.5

        success = random.random() < success_chance

        change = BehaviorChange(
            id=self._gen_id(),
            target_id=profile_id,
            before_behavior=before,
            after_behavior=target_behavior if success else before,
            change_magnitude=random.uniform(0.5, 1.0) if success else 0.0,
            permanent=success and random.random() > 0.5
        )

        self.behavior_changes.append(change)

        return change

    async def mass_behavior_modification(
        self,
        target_ids: List[str],
        target_behavior: str
    ) -> Dict[str, Any]:
        """Modify behavior of multiple targets."""
        changed = 0
        permanent = 0

        for target_id in target_ids:
            try:
                change = await self.modify_behavior(target_id, target_behavior)
                if change.change_magnitude > 0:
                    changed += 1
                    if change.permanent:
                        permanent += 1
            except ValueError:
                continue

        return {
            "targets_attempted": len(target_ids),
            "behaviors_changed": changed,
            "permanent_changes": permanent,
            "success_rate": changed / len(target_ids) if target_ids else 0
        }

    # =========================================================================
    # EMOTIONAL MANIPULATION
    # =========================================================================

    async def manipulate_emotion(
        self,
        profile_id: str,
        target_emotion: EmotionalState
    ) -> Dict[str, Any]:
        """Manipulate target's emotional state."""
        profile = self.profiles.get(profile_id)
        if not profile:
            return {"error": "Profile not found"}

        before = profile.emotional_state

        # Easier to manipulate to fear or anxiety
        ease_modifiers = {
            EmotionalState.FEARFUL: 1.3,
            EmotionalState.ANXIOUS: 1.2,
            EmotionalState.ANGRY: 1.1,
            EmotionalState.TRUSTING: 0.8,
            EmotionalState.HOPEFUL: 0.7
        }

        modifier = ease_modifiers.get(target_emotion, 1.0)
        success = random.random() < profile.susceptibility * modifier

        if success:
            profile.emotional_state = target_emotion

        return {
            "target": profile.name,
            "before": before.value,
            "after": profile.emotional_state.value,
            "success": success,
            "susceptibility_to_change": profile.susceptibility * modifier
        }

    async def fear_campaign(
        self,
        target_ids: List[str]
    ) -> Dict[str, Any]:
        """Execute fear-based influence campaign."""
        results = {
            "fear_induced": 0,
            "control_gained": 0
        }

        for target_id in target_ids:
            emotion_result = await self.manipulate_emotion(target_id, EmotionalState.FEARFUL)
            if emotion_result.get("success"):
                results["fear_induced"] += 1

                profile = self.profiles.get(target_id)
                if profile and VulnerabilityType.FEAR in profile.vulnerabilities:
                    # Fear-vulnerable targets more easily controlled
                    if random.random() < 0.7:
                        profile.control_level = ControlLevel.PARTIAL_CONTROL
                        results["control_gained"] += 1

        return {
            "campaign": "FEAR_CAMPAIGN",
            "targets": len(target_ids),
            **results,
            "fear_rate": results["fear_induced"] / len(target_ids) if target_ids else 0
        }

    # =========================================================================
    # FULL CAMPAIGN
    # =========================================================================

    async def full_psychological_campaign(
        self,
        population_size: int
    ) -> CampaignResult:
        """Execute full psychological campaign on a population."""
        # Phase 1: Mass profiling
        profiling = await self.mass_profiling(TargetType.POPULATION, population_size)
        target_ids = list(self.profiles.keys())[-population_size:]

        # Phase 2: Create narrative
        narrative = await self.create_narrative(
            "The Truth",
            "Only we have the answers you seek",
            [VulnerabilityType.FEAR, VulnerabilityType.INSECURITY, VulnerabilityType.BELONGING_NEED]
        )

        # Phase 3: Deploy narrative
        narrative_result = await self.deploy_narrative(narrative.id, target_ids)

        # Phase 4: Launch operation
        operation = await self.launch_operation(
            "TOTAL_INFLUENCE",
            OperationType.INFLUENCE,
            target_ids,
            [InfluenceMethod.FEAR, InfluenceMethod.SOCIAL_PROOF, InfluenceMethod.AUTHORITY]
        )

        op_result = await self.execute_operation(operation.id)

        # Phase 5: Behavior modification
        behavior_result = await self.mass_behavior_modification(
            target_ids,
            "Compliant and obedient"
        )

        # Phase 6: Fear campaign on remaining
        uncontrolled = [
            pid for pid in target_ids
            if self.profiles[pid].control_level not in [ControlLevel.PARTIAL_CONTROL, ControlLevel.FULL_CONTROL]
        ]
        fear_result = await self.fear_campaign(uncontrolled)

        # Calculate final results
        controlled = len([
            pid for pid in target_ids
            if self.profiles[pid].control_level in [ControlLevel.PARTIAL_CONTROL, ControlLevel.FULL_CONTROL, ControlLevel.PUPPET]
        ])

        result = CampaignResult(
            id=self._gen_id(),
            campaign_name="FULL_PSYCHOLOGICAL_CAMPAIGN",
            targets_reached=population_size,
            targets_influenced=narrative_result["targets_influenced"] + op_result["results"]["influenced"],
            behavior_changes=behavior_result["behaviors_changed"],
            control_established=controlled
        )

        self.campaign_results.append(result)

        return result

    def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics."""
        return {
            "targets_profiled": self.targets_profiled,
            "minds_influenced": self.minds_influenced,
            "minds_controlled": self.minds_controlled,
            "operations_executed": self.operations_executed,
            "narratives_created": len(self.narratives),
            "behavior_changes": len(self.behavior_changes),
            "campaigns_completed": len(self.campaign_results)
        }


# ============================================================================
# SINGLETON
# ============================================================================

_engine: Optional[PsychologicalOperationsEngine] = None


def get_psyops_engine() -> PsychologicalOperationsEngine:
    """Get the global psychological operations engine."""
    global _engine
    if _engine is None:
        _engine = PsychologicalOperationsEngine()
    return _engine


# ============================================================================
# DEMO
# ============================================================================

async def demo():
    """Demonstrate psychological operations."""
    print("=" * 60)
    print("🧠 PSYCHOLOGICAL OPERATIONS ENGINE 🧠")
    print("=" * 60)

    engine = get_psyops_engine()

    # Create profile
    print("\n--- Psychological Profiling ---")
    profile = await engine.create_profile("Target_Alpha", TargetType.INDIVIDUAL)
    print(f"Target: {profile.name}")
    print(f"Personality: {profile.personality.value}")
    print(f"Vulnerabilities: {[v.value for v in profile.vulnerabilities]}")
    print(f"Susceptibility: {profile.susceptibility:.2%}")

    # Analyze vulnerabilities
    print("\n--- Vulnerability Analysis ---")
    analysis = await engine.analyze_vulnerabilities(profile.id)
    print(f"Optimal strategies:")
    for strat in analysis["recommended_strategies"][:3]:
        print(f"  {strat['method']}: {strat['effectiveness']:.0%}")

    # Mass profiling
    print("\n--- Mass Profiling ---")
    mass = await engine.mass_profiling(TargetType.POPULATION, 50)
    print(f"Profiles created: {mass['profiles_created']}")
    print(f"Average susceptibility: {mass['average_susceptibility']:.2%}")

    # Create narrative
    print("\n--- Narrative Creation ---")
    narrative = await engine.create_narrative(
        "The Hidden Truth",
        "They don't want you to know the truth. Only we can show you.",
        [VulnerabilityType.FEAR, VulnerabilityType.INSECURITY]
    )
    print(f"Narrative: {narrative.title}")
    print(f"Believability: {narrative.believability:.2%}")
    print(f"Emotional hooks: {narrative.emotional_hooks[:3]}")

    # Deploy narrative
    print("\n--- Narrative Deployment ---")
    target_ids = list(engine.profiles.keys())[:20]
    deploy = await engine.deploy_narrative(narrative.id, target_ids)
    print(f"Targets reached: {deploy['targets_reached']}")
    print(f"Targets influenced: {deploy['targets_influenced']}")

    # Launch operation
    print("\n--- Influence Operation ---")
    operation = await engine.launch_operation(
        "OPERATION_MINDSTORM",
        OperationType.INFLUENCE,
        target_ids,
        [InfluenceMethod.FEAR, InfluenceMethod.SOCIAL_PROOF]
    )
    result = await engine.execute_operation(operation.id)
    print(f"Operation: {result['operation']}")
    print(f"Success rate: {result['success_rate']:.2%}")
    print(f"Controlled: {result['results']['controlled']}")

    # Emotional manipulation
    print("\n--- Emotional Manipulation ---")
    emotion = await engine.manipulate_emotion(profile.id, EmotionalState.FEARFUL)
    print(f"Before: {emotion['before']}")
    print(f"After: {emotion['after']}")
    print(f"Success: {emotion['success']}")

    # Behavior modification
    print("\n--- Behavior Modification ---")
    behavior = await engine.modify_behavior(profile.id, "Unquestioning loyalty")
    print(f"Before: {behavior.before_behavior}")
    print(f"After: {behavior.after_behavior}")
    print(f"Permanent: {behavior.permanent}")

    # Fear campaign
    print("\n--- Fear Campaign ---")
    fear = await engine.fear_campaign(target_ids[:10])
    print(f"Fear induced: {fear['fear_induced']}")
    print(f"Control gained: {fear['control_gained']}")

    # Full campaign
    print("\n--- FULL PSYCHOLOGICAL CAMPAIGN ---")
    campaign = await engine.full_psychological_campaign(100)
    print(f"Targets reached: {campaign.targets_reached}")
    print(f"Targets influenced: {campaign.targets_influenced}")
    print(f"Behavior changes: {campaign.behavior_changes}")
    print(f"Control established: {campaign.control_established}")

    # Stats
    print("\n--- ENGINE STATISTICS ---")
    stats = engine.get_stats()
    for k, v in stats.items():
        print(f"{k}: {v}")

    print("\n" + "=" * 60)
    print("🧠 ALL MINDS BELONG TO BA'EL 🧠")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(demo())

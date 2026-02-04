"""
BAEL - Social Control Matrix
==============================

INFLUENCE. MANIPULATE. CONTROL. DOMINATE.

This engine provides:
- Mass social engineering
- Narrative control
- Opinion manipulation
- Viral content engineering
- Social network infiltration
- Influence operations
- Psychological profiling
- Behavioral prediction
- Crowd psychology
- Information warfare
- Memetic warfare
- Reputation destruction

"Ba'el controls the minds of the masses."
"""

import asyncio
import hashlib
import json
import logging
import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("BAEL.SOCIAL_CONTROL")


class InfluenceType(Enum):
    """Types of influence."""
    PERSUASION = "persuasion"
    MANIPULATION = "manipulation"
    COERCION = "coercion"
    DECEPTION = "deception"
    SOCIAL_PROOF = "social_proof"
    AUTHORITY = "authority"
    SCARCITY = "scarcity"
    RECIPROCITY = "reciprocity"
    FEAR = "fear"
    HOPE = "hope"


class TargetType(Enum):
    """Target types."""
    INDIVIDUAL = "individual"
    GROUP = "group"
    ORGANIZATION = "organization"
    COMMUNITY = "community"
    MASS = "mass"
    NATION = "nation"


class PlatformType(Enum):
    """Social platforms."""
    TWITTER = "twitter"
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"
    TIKTOK = "tiktok"
    REDDIT = "reddit"
    YOUTUBE = "youtube"
    LINKEDIN = "linkedin"
    DISCORD = "discord"
    TELEGRAM = "telegram"
    FORUMS = "forums"


class PersonalityType(Enum):
    """Personality types for targeting."""
    OPENNESS = "openness"
    CONSCIENTIOUSNESS = "conscientiousness"
    EXTRAVERSION = "extraversion"
    AGREEABLENESS = "agreeableness"
    NEUROTICISM = "neuroticism"


class CampaignType(Enum):
    """Campaign types."""
    AWARENESS = "awareness"
    CONVERSION = "conversion"
    DISRUPTION = "disruption"
    REPUTATION = "reputation"
    RADICALIZATION = "radicalization"
    DERADICALIZATION = "deradicalization"
    ELECTION = "election"
    COMMERCIAL = "commercial"


class ContentType(Enum):
    """Content types."""
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    MEME = "meme"
    INFOGRAPHIC = "infographic"
    STORY = "story"
    LIVE = "live"


@dataclass
class PsychProfile:
    """Psychological profile."""
    id: str
    name: str
    personality: Dict[PersonalityType, float]
    values: List[str]
    fears: List[str]
    desires: List[str]
    vulnerabilities: List[str]
    influence_susceptibility: float
    trust_level: float


@dataclass
class SocialTarget:
    """A social target."""
    id: str
    target_type: TargetType
    name: str
    platform: PlatformType
    followers: int
    influence_score: float
    profile: Optional[PsychProfile]
    status: str


@dataclass
class InfluenceCampaign:
    """An influence campaign."""
    id: str
    name: str
    campaign_type: CampaignType
    targets: List[str]
    platforms: List[PlatformType]
    influence_types: List[InfluenceType]
    start_date: datetime
    end_date: Optional[datetime]
    budget: float
    reach: int
    engagement: int
    conversions: int
    status: str


@dataclass
class Narrative:
    """A controlled narrative."""
    id: str
    name: str
    core_message: str
    supporting_points: List[str]
    counter_narratives: List[str]
    emotional_triggers: List[str]
    target_audiences: List[str]
    effectiveness: float


@dataclass
class BotNetwork:
    """A social bot network."""
    id: str
    name: str
    platform: PlatformType
    bot_count: int
    active_bots: int
    total_posts: int
    total_engagement: int


@dataclass
class ViralContent:
    """Viral content."""
    id: str
    content_type: ContentType
    message: str
    emotional_hook: str
    share_probability: float
    current_reach: int
    viral_coefficient: float


class SocialControlMatrix:
    """
    Social control and influence operations engine.

    Features:
    - Mass influence operations
    - Psychological profiling
    - Narrative control
    - Bot network management
    - Viral engineering
    - Reputation warfare
    """

    def __init__(self):
        self.targets: Dict[str, SocialTarget] = {}
        self.profiles: Dict[str, PsychProfile] = {}
        self.campaigns: Dict[str, InfluenceCampaign] = {}
        self.narratives: Dict[str, Narrative] = {}
        self.bot_networks: Dict[str, BotNetwork] = {}
        self.viral_content: Dict[str, ViralContent] = {}

        self._init_influence_techniques()
        self._init_psychological_triggers()
        self._init_manipulation_patterns()

        logger.info("SocialControlMatrix initialized - ready to influence")

    def _init_influence_techniques(self):
        """Initialize influence techniques."""
        self.influence_techniques = {
            InfluenceType.PERSUASION: [
                "Logical argumentation",
                "Emotional appeal",
                "Social proof",
                "Authority endorsement",
                "Storytelling"
            ],
            InfluenceType.MANIPULATION: [
                "Gaslighting",
                "Love bombing",
                "Triangulation",
                "DARVO",
                "Moving goalposts"
            ],
            InfluenceType.SOCIAL_PROOF: [
                "Fake reviews",
                "Astroturfing",
                "Bandwagon effect",
                "Testimonials",
                "Crowd simulation"
            ],
            InfluenceType.FEAR: [
                "Loss aversion",
                "Threat amplification",
                "Doom scenarios",
                "Safety concerns",
                "FOMO"
            ],
            InfluenceType.AUTHORITY: [
                "Expert positioning",
                "Credential display",
                "Institution backing",
                "Celebrity endorsement",
                "Official appearance"
            ]
        }

    def _init_psychological_triggers(self):
        """Initialize psychological triggers."""
        self.triggers = {
            "primary": [
                "fear", "greed", "belonging", "recognition",
                "power", "safety", "love", "status"
            ],
            "secondary": [
                "curiosity", "outrage", "hope", "nostalgia",
                "envy", "pride", "guilt", "shame"
            ],
            "social": [
                "tribal_identity", "in_group_bias", "out_group_hostility",
                "conformity", "obedience", "rebellion"
            ]
        }

    def _init_manipulation_patterns(self):
        """Initialize manipulation patterns."""
        self.patterns = {
            "emotional_manipulation": [
                "Appeal to fear",
                "Appeal to pity",
                "Appeal to flattery",
                "Appeal to ridicule",
                "Appeal to spite"
            ],
            "logical_fallacies": [
                "Straw man",
                "Ad hominem",
                "False dichotomy",
                "Slippery slope",
                "Appeal to authority"
            ],
            "cognitive_biases": [
                "Confirmation bias",
                "Availability heuristic",
                "Anchoring",
                "Bandwagon effect",
                "Dunning-Kruger"
            ]
        }

    # =========================================================================
    # TARGET MANAGEMENT
    # =========================================================================

    async def add_target(
        self,
        name: str,
        target_type: TargetType,
        platform: PlatformType,
        followers: int = 0
    ) -> SocialTarget:
        """Add a social target."""
        target_id = self._gen_id("target")

        target = SocialTarget(
            id=target_id,
            target_type=target_type,
            name=name,
            platform=platform,
            followers=followers,
            influence_score=min(followers / 10000, 10),
            profile=None,
            status="identified"
        )

        self.targets[target_id] = target
        logger.info(f"Added target: {name}")

        return target

    async def profile_target(
        self,
        target_id: str
    ) -> PsychProfile:
        """Create psychological profile of target."""
        target = self.targets.get(target_id)
        if not target:
            return None

        profile_id = self._gen_id("profile")

        # Generate personality traits
        personality = {
            PersonalityType.OPENNESS: random.uniform(0.2, 0.9),
            PersonalityType.CONSCIENTIOUSNESS: random.uniform(0.2, 0.9),
            PersonalityType.EXTRAVERSION: random.uniform(0.2, 0.9),
            PersonalityType.AGREEABLENESS: random.uniform(0.2, 0.9),
            PersonalityType.NEUROTICISM: random.uniform(0.2, 0.9),
        }

        values = random.sample([
            "freedom", "security", "power", "achievement", "tradition",
            "benevolence", "universalism", "self-direction", "stimulation"
        ], 3)

        fears = random.sample([
            "failure", "rejection", "abandonment", "loss", "death",
            "poverty", "humiliation", "irrelevance"
        ], 3)

        desires = random.sample([
            "wealth", "power", "love", "respect", "freedom",
            "security", "recognition", "meaning"
        ], 3)

        vulnerabilities = random.sample([
            "ego", "insecurity", "greed", "loneliness", "fear",
            "addiction", "naivety", "trust"
        ], 2)

        profile = PsychProfile(
            id=profile_id,
            name=target.name,
            personality=personality,
            values=values,
            fears=fears,
            desires=desires,
            vulnerabilities=vulnerabilities,
            influence_susceptibility=random.uniform(0.3, 0.9),
            trust_level=random.uniform(0.1, 0.7)
        )

        self.profiles[profile_id] = profile
        target.profile = profile
        target.status = "profiled"

        logger.info(f"Profiled target: {target.name}")
        return profile

    async def analyze_vulnerabilities(
        self,
        target_id: str
    ) -> Dict[str, Any]:
        """Analyze target vulnerabilities."""
        target = self.targets.get(target_id)
        if not target or not target.profile:
            return {"error": "Target not profiled"}

        profile = target.profile

        # Find best attack vectors
        attack_vectors = []

        for fear in profile.fears:
            attack_vectors.append({
                "type": "fear_exploitation",
                "trigger": fear,
                "technique": random.choice(self.influence_techniques[InfluenceType.FEAR]),
                "effectiveness": random.uniform(0.5, 0.9)
            })

        for desire in profile.desires:
            attack_vectors.append({
                "type": "desire_exploitation",
                "trigger": desire,
                "technique": random.choice(self.influence_techniques[InfluenceType.PERSUASION]),
                "effectiveness": random.uniform(0.4, 0.8)
            })

        return {
            "target": target.name,
            "vulnerabilities": profile.vulnerabilities,
            "attack_vectors": sorted(attack_vectors, key=lambda x: x["effectiveness"], reverse=True),
            "recommended_approach": "gradual_trust_building" if profile.trust_level < 0.5 else "direct_appeal"
        }

    # =========================================================================
    # CAMPAIGN MANAGEMENT
    # =========================================================================

    async def create_campaign(
        self,
        name: str,
        campaign_type: CampaignType,
        target_ids: List[str],
        platforms: List[PlatformType],
        influence_types: List[InfluenceType],
        budget: float = 0
    ) -> InfluenceCampaign:
        """Create an influence campaign."""
        campaign_id = self._gen_id("campaign")

        campaign = InfluenceCampaign(
            id=campaign_id,
            name=name,
            campaign_type=campaign_type,
            targets=target_ids,
            platforms=platforms,
            influence_types=influence_types,
            start_date=datetime.now(),
            end_date=None,
            budget=budget,
            reach=0,
            engagement=0,
            conversions=0,
            status="planning"
        )

        self.campaigns[campaign_id] = campaign
        logger.info(f"Created campaign: {name}")

        return campaign

    async def launch_campaign(
        self,
        campaign_id: str
    ) -> Dict[str, Any]:
        """Launch an influence campaign."""
        campaign = self.campaigns.get(campaign_id)
        if not campaign:
            return {"error": "Campaign not found"}

        campaign.status = "active"

        # Generate initial metrics
        campaign.reach = random.randint(1000, 100000)
        campaign.engagement = int(campaign.reach * random.uniform(0.01, 0.1))

        return {
            "campaign": campaign.name,
            "status": "launched",
            "initial_reach": campaign.reach,
            "initial_engagement": campaign.engagement
        }

    async def run_campaign_cycle(
        self,
        campaign_id: str
    ) -> Dict[str, Any]:
        """Run a campaign cycle."""
        campaign = self.campaigns.get(campaign_id)
        if not campaign or campaign.status != "active":
            return {"error": "Campaign not active"}

        # Simulate campaign effects
        reach_growth = random.uniform(1.1, 1.5)
        engagement_rate = random.uniform(0.02, 0.15)
        conversion_rate = random.uniform(0.001, 0.05)

        campaign.reach = int(campaign.reach * reach_growth)
        campaign.engagement = int(campaign.reach * engagement_rate)
        campaign.conversions += int(campaign.engagement * conversion_rate)

        return {
            "campaign": campaign.name,
            "cycle_results": {
                "reach": campaign.reach,
                "engagement": campaign.engagement,
                "conversions": campaign.conversions,
                "reach_growth": f"{(reach_growth - 1) * 100:.1f}%"
            }
        }

    # =========================================================================
    # NARRATIVE CONTROL
    # =========================================================================

    async def create_narrative(
        self,
        name: str,
        core_message: str,
        supporting_points: List[str],
        target_audiences: List[str]
    ) -> Narrative:
        """Create a controlled narrative."""
        narrative_id = self._gen_id("narr")

        # Generate emotional triggers
        emotional_triggers = random.sample(
            self.triggers["primary"] + self.triggers["secondary"],
            4
        )

        narrative = Narrative(
            id=narrative_id,
            name=name,
            core_message=core_message,
            supporting_points=supporting_points,
            counter_narratives=[],
            emotional_triggers=emotional_triggers,
            target_audiences=target_audiences,
            effectiveness=0.5
        )

        self.narratives[narrative_id] = narrative
        logger.info(f"Created narrative: {name}")

        return narrative

    async def amplify_narrative(
        self,
        narrative_id: str,
        platforms: List[PlatformType]
    ) -> Dict[str, Any]:
        """Amplify narrative across platforms."""
        narrative = self.narratives.get(narrative_id)
        if not narrative:
            return {"error": "Narrative not found"}

        amplification_results = {}

        for platform in platforms:
            reach = random.randint(10000, 1000000)
            engagement = int(reach * random.uniform(0.01, 0.1))

            amplification_results[platform.value] = {
                "reach": reach,
                "engagement": engagement,
                "sentiment": random.choice(["positive", "neutral", "mixed"]),
                "trending": random.random() > 0.7
            }

        # Update effectiveness
        narrative.effectiveness = min(1.0, narrative.effectiveness + 0.1)

        return {
            "narrative": narrative.name,
            "results": amplification_results,
            "total_reach": sum(r["reach"] for r in amplification_results.values())
        }

    async def counter_narrative(
        self,
        narrative_id: str,
        counter_message: str
    ) -> Dict[str, Any]:
        """Create counter to opposing narrative."""
        narrative = self.narratives.get(narrative_id)
        if not narrative:
            return {"error": "Narrative not found"}

        counter_strategies = [
            "Direct refutation with evidence",
            "Reframe the narrative",
            "Attack the source credibility",
            "Flood with alternative narrative",
            "Create confusion and doubt"
        ]

        narrative.counter_narratives.append(counter_message)

        return {
            "original_narrative": narrative.name,
            "counter_message": counter_message,
            "recommended_strategies": random.sample(counter_strategies, 3),
            "status": "counter_deployed"
        }

    # =========================================================================
    # BOT NETWORKS
    # =========================================================================

    async def create_bot_network(
        self,
        name: str,
        platform: PlatformType,
        bot_count: int
    ) -> BotNetwork:
        """Create a bot network."""
        network_id = self._gen_id("botnet")

        network = BotNetwork(
            id=network_id,
            name=name,
            platform=platform,
            bot_count=bot_count,
            active_bots=0,
            total_posts=0,
            total_engagement=0
        )

        self.bot_networks[network_id] = network
        logger.info(f"Created bot network: {name} with {bot_count} bots")

        return network

    async def activate_bots(
        self,
        network_id: str,
        count: int = None
    ) -> Dict[str, Any]:
        """Activate bots in network."""
        network = self.bot_networks.get(network_id)
        if not network:
            return {"error": "Network not found"}

        activate_count = count or network.bot_count
        network.active_bots = min(activate_count, network.bot_count)

        return {
            "network": network.name,
            "activated": network.active_bots,
            "total": network.bot_count
        }

    async def bot_operation(
        self,
        network_id: str,
        operation: str,
        target: str = None,
        message: str = None
    ) -> Dict[str, Any]:
        """Execute bot operation."""
        network = self.bot_networks.get(network_id)
        if not network or network.active_bots == 0:
            return {"error": "No active bots"}

        operations = {
            "post": {"posts": network.active_bots, "engagement": 0},
            "like": {"posts": 0, "engagement": network.active_bots * 10},
            "share": {"posts": 0, "engagement": network.active_bots * 5},
            "comment": {"posts": 0, "engagement": network.active_bots * 3},
            "follow": {"posts": 0, "engagement": network.active_bots * 2},
            "report": {"posts": 0, "engagement": 0, "reports": network.active_bots},
        }

        result = operations.get(operation, operations["post"])
        network.total_posts += result.get("posts", 0)
        network.total_engagement += result.get("engagement", 0)

        return {
            "network": network.name,
            "operation": operation,
            "bots_used": network.active_bots,
            "result": result
        }

    # =========================================================================
    # VIRAL ENGINEERING
    # =========================================================================

    async def create_viral_content(
        self,
        content_type: ContentType,
        message: str,
        emotional_hook: str
    ) -> ViralContent:
        """Create engineered viral content."""
        content_id = self._gen_id("viral")

        # Calculate viral potential
        emotional_multipliers = {
            "outrage": 1.5,
            "fear": 1.4,
            "awe": 1.3,
            "humor": 1.3,
            "shock": 1.4,
            "inspiration": 1.2,
            "nostalgia": 1.1
        }

        base_share = 0.1
        multiplier = emotional_multipliers.get(emotional_hook.lower(), 1.0)
        share_probability = min(0.5, base_share * multiplier)

        content = ViralContent(
            id=content_id,
            content_type=content_type,
            message=message,
            emotional_hook=emotional_hook,
            share_probability=share_probability,
            current_reach=0,
            viral_coefficient=1 + share_probability
        )

        self.viral_content[content_id] = content
        logger.info(f"Created viral content: {content_type.value}")

        return content

    async def launch_viral(
        self,
        content_id: str,
        initial_seeds: int = 100
    ) -> Dict[str, Any]:
        """Launch viral content."""
        content = self.viral_content.get(content_id)
        if not content:
            return {"error": "Content not found"}

        # Simulate viral spread
        reach = initial_seeds
        cycles = 0

        while reach < 10000000 and cycles < 20:
            new_reach = int(reach * content.viral_coefficient)
            if new_reach <= reach:
                break
            reach = new_reach
            cycles += 1

        content.current_reach = reach

        return {
            "content_type": content.content_type.value,
            "emotional_hook": content.emotional_hook,
            "viral_coefficient": content.viral_coefficient,
            "final_reach": reach,
            "cycles": cycles,
            "viral_success": reach > 100000
        }

    # =========================================================================
    # REPUTATION WARFARE
    # =========================================================================

    async def reputation_attack(
        self,
        target_id: str,
        attack_type: str = "discredit"
    ) -> Dict[str, Any]:
        """Execute reputation attack."""
        target = self.targets.get(target_id)
        if not target:
            return {"error": "Target not found"}

        attack_strategies = {
            "discredit": [
                "Expose contradictions",
                "Highlight failures",
                "Question credentials",
                "Associate with controversy"
            ],
            "smear": [
                "Create negative content",
                "Amplify criticism",
                "Fake accusations",
                "Character assassination"
            ],
            "isolate": [
                "Turn allies against target",
                "Platform ban campaign",
                "Social exclusion",
                "Professional blacklisting"
            ],
            "overwhelm": [
                "Flood negative reviews",
                "Mass reporting",
                "Denial of service",
                "Information overload"
            ]
        }

        strategies = attack_strategies.get(attack_type, attack_strategies["discredit"])

        return {
            "target": target.name,
            "attack_type": attack_type,
            "strategies_deployed": strategies,
            "estimated_impact": random.uniform(0.3, 0.8),
            "status": "executing"
        }

    async def reputation_defense(
        self,
        target_id: str
    ) -> Dict[str, Any]:
        """Defend reputation."""
        defense_strategies = [
            "Positive content flood",
            "SEO manipulation",
            "Counter-narrative deployment",
            "Ally mobilization",
            "Legal threats",
            "Platform intervention"
        ]

        return {
            "target_id": target_id,
            "defense_strategies": defense_strategies,
            "protection_level": random.uniform(0.5, 0.9),
            "status": "defending"
        }

    # =========================================================================
    # UTILITIES
    # =========================================================================

    def _gen_id(self, prefix: str) -> str:
        """Generate unique ID."""
        return hashlib.md5(f"{prefix}{time.time()}{random.random()}".encode()).hexdigest()[:12]

    def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics."""
        active_campaigns = [c for c in self.campaigns.values() if c.status == "active"]
        total_reach = sum(c.reach for c in active_campaigns)
        total_bots = sum(n.bot_count for n in self.bot_networks.values())
        active_bots = sum(n.active_bots for n in self.bot_networks.values())

        return {
            "targets": len(self.targets),
            "profiles": len(self.profiles),
            "campaigns": len(self.campaigns),
            "active_campaigns": len(active_campaigns),
            "narratives": len(self.narratives),
            "bot_networks": len(self.bot_networks),
            "total_bots": total_bots,
            "active_bots": active_bots,
            "viral_content": len(self.viral_content),
            "total_reach": total_reach
        }


# ============================================================================
# SINGLETON
# ============================================================================

_matrix: Optional[SocialControlMatrix] = None


def get_social_control_matrix() -> SocialControlMatrix:
    """Get global social control matrix."""
    global _matrix
    if _matrix is None:
        _matrix = SocialControlMatrix()
    return _matrix


# ============================================================================
# DEMO
# ============================================================================

async def demo():
    """Demonstrate social control matrix."""
    print("=" * 60)
    print("🎭 SOCIAL CONTROL MATRIX 🎭")
    print("=" * 60)

    matrix = get_social_control_matrix()

    # Add target
    print("\n--- Adding Target ---")
    target = await matrix.add_target(
        "Competitor Corp",
        TargetType.ORGANIZATION,
        PlatformType.TWITTER,
        50000
    )
    print(f"Target: {target.name}")

    # Profile target
    print("\n--- Profiling Target ---")
    profile = await matrix.profile_target(target.id)
    print(f"Vulnerabilities: {profile.vulnerabilities}")
    print(f"Influence Susceptibility: {profile.influence_susceptibility:.2f}")

    # Analyze vulnerabilities
    print("\n--- Vulnerability Analysis ---")
    analysis = await matrix.analyze_vulnerabilities(target.id)
    for vector in analysis["attack_vectors"][:2]:
        print(f"  {vector['type']}: {vector['trigger']} ({vector['effectiveness']:.2f})")

    # Create campaign
    print("\n--- Creating Campaign ---")
    campaign = await matrix.create_campaign(
        "Market Dominance",
        CampaignType.DISRUPTION,
        [target.id],
        [PlatformType.TWITTER, PlatformType.REDDIT],
        [InfluenceType.FEAR, InfluenceType.SOCIAL_PROOF],
        10000
    )
    await matrix.launch_campaign(campaign.id)
    print(f"Campaign: {campaign.name} - {campaign.status}")

    # Create narrative
    print("\n--- Creating Narrative ---")
    narrative = await matrix.create_narrative(
        "Industry Leadership",
        "Ba'el represents the future of technology",
        ["Innovation leader", "Trusted by millions", "Ethical approach"],
        ["tech_enthusiasts", "investors", "media"]
    )
    print(f"Narrative: {narrative.name}")

    # Create bot network
    print("\n--- Bot Network ---")
    botnet = await matrix.create_bot_network(
        "Influence Army",
        PlatformType.TWITTER,
        1000
    )
    await matrix.activate_bots(botnet.id)
    print(f"Bots: {botnet.active_bots} active")

    # Viral content
    print("\n--- Viral Engineering ---")
    viral = await matrix.create_viral_content(
        ContentType.MEME,
        "The future is Ba'el",
        "outrage"
    )
    result = await matrix.launch_viral(viral.id, 500)
    print(f"Viral Reach: {result['final_reach']:,}")

    # Stats
    print("\n--- Matrix Statistics ---")
    stats = matrix.get_stats()
    print(f"Active Campaigns: {stats['active_campaigns']}")
    print(f"Total Bots: {stats['total_bots']}")
    print(f"Total Reach: {stats['total_reach']:,}")

    print("\n" + "=" * 60)
    print("🎭 MINDS UNDER CONTROL 🎭")


if __name__ == "__main__":
    asyncio.run(demo())

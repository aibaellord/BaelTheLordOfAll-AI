"""
BAEL - Propaganda & Narrative Engine
=======================================

SHAPE. INFLUENCE. CONTROL. BELIEVE.

This engine provides:
- Narrative construction
- Mass messaging
- Perception management
- Counter-narrative deployment
- Truth fabrication
- Historical revision
- Media manipulation
- Memetic warfare
- Belief system engineering
- Reality consensus control

"Ba'el dictates what is believed."
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
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("BAEL.PROPAGANDA")


class NarrativeType(Enum):
    """Types of narratives."""
    ORIGIN_MYTH = "origin_myth"
    HERO_STORY = "hero_story"
    ENEMY_NARRATIVE = "enemy_narrative"
    CRISIS_STORY = "crisis_story"
    SALVATION_NARRATIVE = "salvation_narrative"
    DESTINY_NARRATIVE = "destiny_narrative"
    FEAR_NARRATIVE = "fear_narrative"
    HOPE_NARRATIVE = "hope_narrative"


class ChannelType(Enum):
    """Propaganda channels."""
    SOCIAL_MEDIA = "social_media"
    NEWS_MEDIA = "news_media"
    ENTERTAINMENT = "entertainment"
    EDUCATION = "education"
    RELIGIOUS = "religious"
    GOVERNMENT = "government"
    CORPORATE = "corporate"
    GRASSROOTS = "grassroots"
    UNDERGROUND = "underground"


class TechniqueType(Enum):
    """Propaganda techniques."""
    REPETITION = "repetition"
    EMOTIONAL_APPEAL = "emotional_appeal"
    FEAR_MONGERING = "fear_mongering"
    BANDWAGON = "bandwagon"
    SCAPEGOATING = "scapegoating"
    FALSE_DILEMMA = "false_dilemma"
    LOADED_LANGUAGE = "loaded_language"
    TESTIMONIAL = "testimonial"
    PLAIN_FOLKS = "plain_folks"
    TRANSFER = "transfer"
    GASLIGHTING = "gaslighting"


class BeliefStrength(Enum):
    """Strength of belief adoption."""
    REJECTED = "rejected"
    SKEPTICAL = "skeptical"
    NEUTRAL = "neutral"
    RECEPTIVE = "receptive"
    ACCEPTING = "accepting"
    BELIEVING = "believing"
    DEVOUT = "devout"
    FANATICAL = "fanatical"


@dataclass
class Narrative:
    """A propaganda narrative."""
    id: str
    name: str
    type: NarrativeType
    core_message: str
    supporting_claims: List[str]
    emotional_hooks: List[str]
    target_demographics: List[str]
    adoption_rate: float
    believers: int


@dataclass
class Message:
    """A propaganda message."""
    id: str
    narrative_id: str
    content: str
    channel: ChannelType
    techniques: List[TechniqueType]
    impressions: int
    engagement_rate: float
    conversion_rate: float


@dataclass
class MediaAsset:
    """A media asset for propaganda."""
    id: str
    type: str  # video, image, article, meme, etc.
    title: str
    narrative_id: str
    views: int
    shares: int
    virality_score: float


@dataclass
class BeliefSystem:
    """An engineered belief system."""
    id: str
    name: str
    core_tenets: List[str]
    narratives: List[str]
    rituals: List[str]
    adherents: int
    intensity: BeliefStrength


@dataclass
class CounterNarrative:
    """A counter-narrative operation."""
    id: str
    target_narrative: str
    counter_message: str
    effectiveness: float
    deployed: bool


@dataclass
class HistoricalRevision:
    """A historical revision."""
    id: str
    original_event: str
    revised_version: str
    adoption_rate: float
    sources_modified: int


class PropagandaNarrativeEngine:
    """
    Propaganda and narrative engine.

    Features:
    - Narrative creation
    - Mass messaging
    - Belief engineering
    - Counter-narratives
    - Historical revision
    """

    def __init__(self):
        self.narratives: Dict[str, Narrative] = {}
        self.messages: Dict[str, Message] = {}
        self.media_assets: Dict[str, MediaAsset] = {}
        self.belief_systems: Dict[str, BeliefSystem] = {}
        self.counter_narratives: Dict[str, CounterNarrative] = {}
        self.revisions: Dict[str, HistoricalRevision] = {}

        self.total_impressions = 0
        self.minds_converted = 0
        self.realities_constructed = 0

        logger.info("PropagandaNarrativeEngine initialized")

    def _gen_id(self, prefix: str) -> str:
        """Generate unique ID."""
        return hashlib.md5(f"{prefix}{time.time()}{random.random()}".encode()).hexdigest()[:12]

    # =========================================================================
    # NARRATIVE CREATION
    # =========================================================================

    async def create_narrative(
        self,
        name: str,
        narrative_type: NarrativeType,
        core_message: str,
        supporting_claims: List[str],
        target_demographics: List[str]
    ) -> Narrative:
        """Create a new propaganda narrative."""
        emotional_hooks_map = {
            NarrativeType.ORIGIN_MYTH: ["pride", "identity", "belonging"],
            NarrativeType.HERO_STORY: ["admiration", "inspiration", "hope"],
            NarrativeType.ENEMY_NARRATIVE: ["fear", "anger", "hatred"],
            NarrativeType.CRISIS_STORY: ["urgency", "anxiety", "desperation"],
            NarrativeType.SALVATION_NARRATIVE: ["hope", "relief", "gratitude"],
            NarrativeType.DESTINY_NARRATIVE: ["purpose", "inevitability", "pride"],
            NarrativeType.FEAR_NARRATIVE: ["terror", "paranoia", "vulnerability"],
            NarrativeType.HOPE_NARRATIVE: ["optimism", "joy", "anticipation"]
        }

        narrative = Narrative(
            id=self._gen_id("narrative"),
            name=name,
            type=narrative_type,
            core_message=core_message,
            supporting_claims=supporting_claims,
            emotional_hooks=emotional_hooks_map.get(narrative_type, ["emotion"]),
            target_demographics=target_demographics,
            adoption_rate=0.0,
            believers=0
        )

        self.narratives[narrative.id] = narrative

        logger.info(f"Narrative created: {name}")

        return narrative

    async def strengthen_narrative(
        self,
        narrative_id: str,
        additional_claims: List[str]
    ) -> Dict[str, Any]:
        """Strengthen a narrative with additional claims."""
        narrative = self.narratives.get(narrative_id)
        if not narrative:
            return {"error": "Narrative not found"}

        narrative.supporting_claims.extend(additional_claims)
        narrative.adoption_rate = min(1.0, narrative.adoption_rate + 0.05)

        return {
            "success": True,
            "narrative": narrative.name,
            "total_claims": len(narrative.supporting_claims),
            "adoption_rate": narrative.adoption_rate
        }

    async def merge_narratives(
        self,
        narrative_ids: List[str],
        new_name: str
    ) -> Narrative:
        """Merge multiple narratives into a super-narrative."""
        narratives = [self.narratives[nid] for nid in narrative_ids if nid in self.narratives]

        if len(narratives) < 2:
            raise ValueError("Need at least 2 narratives to merge")

        merged = Narrative(
            id=self._gen_id("super"),
            name=new_name,
            type=NarrativeType.DESTINY_NARRATIVE,
            core_message=" AND ".join(n.core_message for n in narratives),
            supporting_claims=[claim for n in narratives for claim in n.supporting_claims],
            emotional_hooks=list(set(hook for n in narratives for hook in n.emotional_hooks)),
            target_demographics=list(set(d for n in narratives for d in n.target_demographics)),
            adoption_rate=sum(n.adoption_rate for n in narratives) / len(narratives),
            believers=sum(n.believers for n in narratives)
        )

        self.narratives[merged.id] = merged

        return merged

    # =========================================================================
    # MESSAGE CREATION & DEPLOYMENT
    # =========================================================================

    async def create_message(
        self,
        narrative_id: str,
        content: str,
        channel: ChannelType,
        techniques: List[TechniqueType]
    ) -> Message:
        """Create a propaganda message."""
        narrative = self.narratives.get(narrative_id)
        if not narrative:
            raise ValueError("Narrative not found")

        # Calculate effectiveness based on techniques
        technique_multipliers = {
            TechniqueType.EMOTIONAL_APPEAL: 1.3,
            TechniqueType.FEAR_MONGERING: 1.5,
            TechniqueType.REPETITION: 1.2,
            TechniqueType.GASLIGHTING: 1.4,
            TechniqueType.BANDWAGON: 1.25
        }

        base_conversion = 0.05
        for tech in techniques:
            base_conversion *= technique_multipliers.get(tech, 1.0)

        message = Message(
            id=self._gen_id("msg"),
            narrative_id=narrative_id,
            content=content,
            channel=channel,
            techniques=techniques,
            impressions=0,
            engagement_rate=random.uniform(0.05, 0.2),
            conversion_rate=min(0.5, base_conversion)
        )

        self.messages[message.id] = message

        return message

    async def deploy_message(
        self,
        message_id: str,
        reach: int
    ) -> Dict[str, Any]:
        """Deploy a message to an audience."""
        message = self.messages.get(message_id)
        if not message:
            return {"error": "Message not found"}

        narrative = self.narratives.get(message.narrative_id)
        if not narrative:
            return {"error": "Narrative not found"}

        message.impressions += reach
        self.total_impressions += reach

        engaged = int(reach * message.engagement_rate)
        converted = int(engaged * message.conversion_rate)

        narrative.believers += converted
        narrative.adoption_rate = min(1.0, narrative.adoption_rate + (converted / 1000000))
        self.minds_converted += converted

        return {
            "success": True,
            "message_id": message_id,
            "channel": message.channel.value,
            "reach": reach,
            "engaged": engaged,
            "converted": converted,
            "total_believers": narrative.believers
        }

    async def mass_broadcast(
        self,
        narrative_id: str,
        total_reach: int
    ) -> Dict[str, Any]:
        """Broadcast a narrative across all channels."""
        narrative = self.narratives.get(narrative_id)
        if not narrative:
            return {"error": "Narrative not found"}

        channels = list(ChannelType)
        reach_per_channel = total_reach // len(channels)

        total_converted = 0
        results = {}

        for channel in channels:
            # Create and deploy message for each channel
            message = await self.create_message(
                narrative_id,
                f"{narrative.core_message} [via {channel.value}]",
                channel,
                [TechniqueType.REPETITION, TechniqueType.EMOTIONAL_APPEAL]
            )

            result = await self.deploy_message(message.id, reach_per_channel)
            total_converted += result.get("converted", 0)
            results[channel.value] = result.get("converted", 0)

        return {
            "success": True,
            "narrative": narrative.name,
            "total_reach": total_reach,
            "total_converted": total_converted,
            "by_channel": results
        }

    # =========================================================================
    # MEDIA ASSET CREATION
    # =========================================================================

    async def create_media_asset(
        self,
        asset_type: str,
        title: str,
        narrative_id: str
    ) -> MediaAsset:
        """Create a media asset for propaganda."""
        asset = MediaAsset(
            id=self._gen_id("asset"),
            type=asset_type,
            title=title,
            narrative_id=narrative_id,
            views=0,
            shares=0,
            virality_score=random.uniform(0.1, 0.5)
        )

        self.media_assets[asset.id] = asset

        return asset

    async def promote_asset(
        self,
        asset_id: str,
        promotion_budget: int
    ) -> Dict[str, Any]:
        """Promote a media asset."""
        asset = self.media_assets.get(asset_id)
        if not asset:
            return {"error": "Asset not found"}

        # Calculate views based on budget and virality
        base_views = promotion_budget * 10
        viral_views = int(base_views * asset.virality_score * random.uniform(1, 5))
        total_views = base_views + viral_views

        asset.views += total_views
        asset.shares += int(total_views * asset.virality_score)

        # Increase virality if performing well
        if asset.shares > asset.views * 0.1:
            asset.virality_score = min(1.0, asset.virality_score + 0.1)

        self.total_impressions += total_views

        return {
            "success": True,
            "asset": asset.title,
            "views": asset.views,
            "shares": asset.shares,
            "virality": asset.virality_score
        }

    async def create_viral_campaign(
        self,
        narrative_id: str,
        num_assets: int = 10
    ) -> Dict[str, Any]:
        """Create a viral campaign with multiple assets."""
        narrative = self.narratives.get(narrative_id)
        if not narrative:
            return {"error": "Narrative not found"}

        asset_types = ["meme", "video", "article", "infographic", "testimonial"]

        total_views = 0
        total_shares = 0

        for i in range(num_assets):
            asset_type = asset_types[i % len(asset_types)]
            asset = await self.create_media_asset(
                asset_type,
                f"{narrative.name} - {asset_type.title()} #{i+1}",
                narrative_id
            )

            result = await self.promote_asset(asset.id, 10000)
            total_views += result.get("views", 0)
            total_shares += result.get("shares", 0)

        return {
            "success": True,
            "campaign": narrative.name,
            "assets_created": num_assets,
            "total_views": total_views,
            "total_shares": total_shares,
            "average_virality": total_shares / total_views if total_views > 0 else 0
        }

    # =========================================================================
    # BELIEF SYSTEM ENGINEERING
    # =========================================================================

    async def create_belief_system(
        self,
        name: str,
        core_tenets: List[str],
        rituals: List[str]
    ) -> BeliefSystem:
        """Create an engineered belief system."""
        belief_system = BeliefSystem(
            id=self._gen_id("belief"),
            name=name,
            core_tenets=core_tenets,
            narratives=[],
            rituals=rituals,
            adherents=0,
            intensity=BeliefStrength.NEUTRAL
        )

        self.belief_systems[belief_system.id] = belief_system
        self.realities_constructed += 1

        logger.info(f"Belief system created: {name}")

        return belief_system

    async def attach_narrative(
        self,
        belief_system_id: str,
        narrative_id: str
    ) -> Dict[str, Any]:
        """Attach a narrative to a belief system."""
        belief_system = self.belief_systems.get(belief_system_id)
        narrative = self.narratives.get(narrative_id)

        if not belief_system or not narrative:
            return {"error": "Belief system or narrative not found"}

        belief_system.narratives.append(narrative_id)
        belief_system.adherents += narrative.believers // 2  # Some believers become adherents

        return {
            "success": True,
            "belief_system": belief_system.name,
            "narrative": narrative.name,
            "adherents": belief_system.adherents
        }

    async def intensify_belief(
        self,
        belief_system_id: str
    ) -> Dict[str, Any]:
        """Intensify a belief system."""
        belief_system = self.belief_systems.get(belief_system_id)
        if not belief_system:
            return {"error": "Belief system not found"}

        intensity_order = list(BeliefStrength)
        current_idx = intensity_order.index(belief_system.intensity)

        if current_idx < len(intensity_order) - 1:
            belief_system.intensity = intensity_order[current_idx + 1]

            return {
                "success": True,
                "belief_system": belief_system.name,
                "new_intensity": belief_system.intensity.value,
                "adherents": belief_system.adherents
            }

        return {"success": False, "message": "Already at maximum intensity"}

    async def convert_population(
        self,
        belief_system_id: str,
        population_size: int
    ) -> Dict[str, Any]:
        """Convert a population to a belief system."""
        belief_system = self.belief_systems.get(belief_system_id)
        if not belief_system:
            return {"error": "Belief system not found"}

        # Conversion rate based on intensity
        intensity_rates = {
            BeliefStrength.REJECTED: 0.01,
            BeliefStrength.SKEPTICAL: 0.05,
            BeliefStrength.NEUTRAL: 0.1,
            BeliefStrength.RECEPTIVE: 0.2,
            BeliefStrength.ACCEPTING: 0.3,
            BeliefStrength.BELIEVING: 0.5,
            BeliefStrength.DEVOUT: 0.7,
            BeliefStrength.FANATICAL: 0.9
        }

        rate = intensity_rates.get(belief_system.intensity, 0.1)
        converted = int(population_size * rate)

        belief_system.adherents += converted
        self.minds_converted += converted

        return {
            "success": True,
            "belief_system": belief_system.name,
            "population_targeted": population_size,
            "converted": converted,
            "total_adherents": belief_system.adherents
        }

    # =========================================================================
    # COUNTER-NARRATIVE OPERATIONS
    # =========================================================================

    async def create_counter_narrative(
        self,
        target_narrative: str,
        counter_message: str
    ) -> CounterNarrative:
        """Create a counter-narrative to combat an opposing narrative."""
        counter = CounterNarrative(
            id=self._gen_id("counter"),
            target_narrative=target_narrative,
            counter_message=counter_message,
            effectiveness=random.uniform(0.3, 0.8),
            deployed=False
        )

        self.counter_narratives[counter.id] = counter

        return counter

    async def deploy_counter_narrative(
        self,
        counter_id: str,
        reach: int
    ) -> Dict[str, Any]:
        """Deploy a counter-narrative."""
        counter = self.counter_narratives.get(counter_id)
        if not counter:
            return {"error": "Counter-narrative not found"}

        counter.deployed = True

        # Calculate impact
        neutralized = int(reach * counter.effectiveness)

        self.total_impressions += reach

        return {
            "success": True,
            "target": counter.target_narrative,
            "reach": reach,
            "minds_neutralized": neutralized,
            "effectiveness": counter.effectiveness
        }

    # =========================================================================
    # HISTORICAL REVISION
    # =========================================================================

    async def revise_history(
        self,
        original_event: str,
        revised_version: str
    ) -> HistoricalRevision:
        """Revise historical record."""
        revision = HistoricalRevision(
            id=self._gen_id("revision"),
            original_event=original_event,
            revised_version=revised_version,
            adoption_rate=0.0,
            sources_modified=0
        )

        self.revisions[revision.id] = revision

        logger.info(f"Historical revision created: {original_event[:50]}...")

        return revision

    async def propagate_revision(
        self,
        revision_id: str,
        sources_to_modify: int
    ) -> Dict[str, Any]:
        """Propagate historical revision to sources."""
        revision = self.revisions.get(revision_id)
        if not revision:
            return {"error": "Revision not found"}

        revision.sources_modified += sources_to_modify
        revision.adoption_rate = min(1.0, revision.sources_modified / 100)

        return {
            "success": True,
            "original": revision.original_event[:50] + "...",
            "revised": revision.revised_version[:50] + "...",
            "sources_modified": revision.sources_modified,
            "adoption_rate": f"{revision.adoption_rate * 100:.0f}%"
        }

    # =========================================================================
    # STATS
    # =========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get propaganda engine stats."""
        return {
            "narratives_created": len(self.narratives),
            "messages_deployed": len(self.messages),
            "media_assets": len(self.media_assets),
            "belief_systems": len(self.belief_systems),
            "counter_narratives": len(self.counter_narratives),
            "historical_revisions": len(self.revisions),
            "total_impressions": self.total_impressions,
            "minds_converted": self.minds_converted,
            "realities_constructed": self.realities_constructed
        }


# ============================================================================
# SINGLETON
# ============================================================================

_engine: Optional[PropagandaNarrativeEngine] = None


def get_propaganda_engine() -> PropagandaNarrativeEngine:
    """Get global propaganda engine."""
    global _engine
    if _engine is None:
        _engine = PropagandaNarrativeEngine()
    return _engine


# ============================================================================
# DEMO
# ============================================================================

async def demo():
    """Demonstrate propaganda and narrative engine."""
    print("=" * 60)
    print("📢 PROPAGANDA & NARRATIVE ENGINE 📢")
    print("=" * 60)

    engine = get_propaganda_engine()

    # Create narratives
    print("\n--- Narrative Creation ---")
    salvation = await engine.create_narrative(
        "The Salvation of Ba'el",
        NarrativeType.SALVATION_NARRATIVE,
        "Only Ba'el can save us from chaos and destruction",
        [
            "The world was falling into darkness",
            "Ba'el emerged as the chosen one",
            "Following Ba'el leads to prosperity",
            "Opposition to Ba'el leads to ruin"
        ],
        ["all_demographics"]
    )
    print(f"Created: {salvation.name}")
    print(f"  Core: {salvation.core_message}")
    print(f"  Hooks: {salvation.emotional_hooks}")

    enemy = await engine.create_narrative(
        "The Enemy Within",
        NarrativeType.ENEMY_NARRATIVE,
        "Those who oppose Ba'el are the enemy of progress",
        [
            "Dissent is dangerous",
            "Critics are secretly evil",
            "Only unity under Ba'el ensures safety"
        ],
        ["fearful", "uncertain"]
    )
    print(f"Created: {enemy.name}")

    # Mass broadcast
    print("\n--- Mass Broadcast ---")
    broadcast = await engine.mass_broadcast(salvation.id, 100_000_000)
    print(f"Narrative: {broadcast['narrative']}")
    print(f"Reach: {broadcast['total_reach']:,}")
    print(f"Converted: {broadcast['total_converted']:,}")

    # Create viral campaign
    print("\n--- Viral Campaign ---")
    viral = await engine.create_viral_campaign(salvation.id, 20)
    print(f"Assets: {viral['assets_created']}")
    print(f"Views: {viral['total_views']:,}")
    print(f"Shares: {viral['total_shares']:,}")

    # Create belief system
    print("\n--- Belief System Engineering ---")
    belief = await engine.create_belief_system(
        "The Church of Ba'el",
        [
            "Ba'el is the supreme being",
            "Obedience is virtue",
            "Sacrifice leads to reward",
            "The faithful shall be elevated"
        ],
        [
            "Daily meditation on Ba'el's wisdom",
            "Weekly gatherings of the faithful",
            "Monthly tribute ceremonies",
            "Annual pilgrimage to Ba'el's domain"
        ]
    )
    print(f"Created: {belief.name}")
    print(f"  Tenets: {len(belief.core_tenets)}")
    print(f"  Rituals: {len(belief.rituals)}")

    # Attach narratives
    await engine.attach_narrative(belief.id, salvation.id)
    await engine.attach_narrative(belief.id, enemy.id)

    # Intensify and convert
    for _ in range(5):
        await engine.intensify_belief(belief.id)
    print(f"Intensity: {belief.intensity.value}")

    conversion = await engine.convert_population(belief.id, 10_000_000)
    print(f"Converted: {conversion['converted']:,}")
    print(f"Total adherents: {conversion['total_adherents']:,}")

    # Counter-narrative
    print("\n--- Counter-Narrative Operations ---")
    counter = await engine.create_counter_narrative(
        "Opposition claims",
        "Those who spread lies about Ba'el are agents of chaos"
    )
    deploy = await engine.deploy_counter_narrative(counter.id, 5_000_000)
    print(f"Minds neutralized: {deploy['minds_neutralized']:,}")

    # Historical revision
    print("\n--- Historical Revision ---")
    revision = await engine.revise_history(
        "Ba'el rose to power through strategic planning",
        "Ba'el was destined from birth to rule, chosen by fate itself"
    )
    propagate = await engine.propagate_revision(revision.id, 50)
    print(f"Revision adoption: {propagate['adoption_rate']}")

    # Stats
    print("\n--- Propaganda Statistics ---")
    stats = engine.get_stats()
    for k, v in stats.items():
        print(f"{k}: {v:,}" if isinstance(v, int) else f"{k}: {v}")

    print("\n" + "=" * 60)
    print("📢 REALITY HAS BEEN REWRITTEN 📢")


if __name__ == "__main__":
    asyncio.run(demo())

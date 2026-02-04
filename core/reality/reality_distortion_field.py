"""
BAEL - Reality Distortion Field
=================================

PERCEIVE. DISTORT. CREATE. REPLACE.

This engine provides:
- Perception manipulation
- Reality overlay systems
- Illusion generation
- Consensus reality hacking
- Simulation injection
- Physics override
- Timeline manipulation
- Dimensional shifting
- Mass hallucination
- Truth rewriting

"Ba'el defines what is real."
"""

import asyncio
import hashlib
import json
import logging
import math
import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("BAEL.REALITY")


class DistortionType(Enum):
    """Types of reality distortion."""
    VISUAL = "visual"
    AUDITORY = "auditory"
    TEMPORAL = "temporal"
    SPATIAL = "spatial"
    COGNITIVE = "cognitive"
    EMOTIONAL = "emotional"
    PHYSICAL = "physical"
    COMPLETE = "complete"


class DistortionLevel(Enum):
    """Levels of distortion intensity."""
    SUBTLE = "subtle"  # Barely noticeable
    NOTICEABLE = "noticeable"  # Detectable
    SIGNIFICANT = "significant"  # Clear changes
    MAJOR = "major"  # Dramatic changes
    ABSOLUTE = "absolute"  # Complete replacement


class RealityLayer(Enum):
    """Layers of reality."""
    PHYSICAL = "physical"
    PERCEPTUAL = "perceptual"
    SOCIAL = "social"
    INFORMATION = "information"
    CONSENSUS = "consensus"
    SUBJECTIVE = "subjective"


class OverlayMode(Enum):
    """Reality overlay modes."""
    AUGMENT = "augment"  # Add to reality
    REPLACE = "replace"  # Replace aspects
    FILTER = "filter"  # Filter perception
    INVERT = "invert"  # Invert aspects
    AMPLIFY = "amplify"  # Amplify aspects
    SUPPRESS = "suppress"  # Hide aspects


@dataclass
class RealityZone:
    """A zone of reality manipulation."""
    id: str
    name: str
    center: Tuple[float, float, float]
    radius: float
    distortion_type: DistortionType
    level: DistortionLevel
    active: bool
    affected_targets: List[str]
    effects: List[Dict[str, Any]]


@dataclass
class Overlay:
    """A reality overlay."""
    id: str
    name: str
    mode: OverlayMode
    layer: RealityLayer
    content: Dict[str, Any]
    opacity: float
    targets: List[str]
    active: bool


@dataclass
class Illusion:
    """An illusion construct."""
    id: str
    name: str
    type: DistortionType
    description: str
    persistence: float  # 0-1
    believability: float
    components: List[str]
    witnesses: List[str]


@dataclass
class TimelineAlteration:
    """A timeline alteration."""
    id: str
    original_event: str
    altered_event: str
    timestamp: datetime
    scope: str
    stability: float
    affected_branches: int


@dataclass
class ConsensusHack:
    """A consensus reality hack."""
    id: str
    target_belief: str
    new_belief: str
    propagation: float
    adoption_rate: float
    affected_population: int


class RealityDistortionField:
    """
    Reality distortion field engine.

    Features:
    - Zone manipulation
    - Overlay systems
    - Illusion crafting
    - Timeline alterations
    - Consensus hacking
    """

    def __init__(self):
        self.zones: Dict[str, RealityZone] = {}
        self.overlays: Dict[str, Overlay] = {}
        self.illusions: Dict[str, Illusion] = {}
        self.timeline_alterations: Dict[str, TimelineAlteration] = {}
        self.consensus_hacks: Dict[str, ConsensusHack] = {}

        self.distortion_power = 1.0
        self.reality_stability = 1.0
        self.affected_minds = 0

        logger.info("RealityDistortionField initialized")

    def _gen_id(self, prefix: str) -> str:
        """Generate unique ID."""
        return hashlib.md5(f"{prefix}{time.time()}{random.random()}".encode()).hexdigest()[:12]

    # =========================================================================
    # ZONE MANIPULATION
    # =========================================================================

    async def create_zone(
        self,
        name: str,
        center: Tuple[float, float, float],
        radius: float,
        distortion_type: DistortionType,
        level: DistortionLevel = DistortionLevel.SUBTLE
    ) -> RealityZone:
        """Create a reality distortion zone."""
        zone = RealityZone(
            id=self._gen_id("zone"),
            name=name,
            center=center,
            radius=radius,
            distortion_type=distortion_type,
            level=level,
            active=True,
            affected_targets=[],
            effects=[]
        )

        self.zones[zone.id] = zone

        logger.info(f"Reality zone created: {name}")

        return zone

    async def add_zone_effect(
        self,
        zone_id: str,
        effect_type: str,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Add effect to a zone."""
        zone = self.zones.get(zone_id)
        if not zone:
            return {"error": "Zone not found"}

        effect = {
            "id": self._gen_id("effect"),
            "type": effect_type,
            "parameters": parameters,
            "active": True
        }

        zone.effects.append(effect)

        return {
            "success": True,
            "zone": zone.name,
            "effect": effect_type,
            "total_effects": len(zone.effects)
        }

    async def expand_zone(
        self,
        zone_id: str,
        additional_radius: float
    ) -> Dict[str, Any]:
        """Expand a distortion zone."""
        zone = self.zones.get(zone_id)
        if not zone:
            return {"error": "Zone not found"}

        old_radius = zone.radius
        zone.radius += additional_radius

        # Expanding consumes distortion power
        self.distortion_power *= 0.95

        return {
            "success": True,
            "old_radius": old_radius,
            "new_radius": zone.radius,
            "distortion_power": self.distortion_power
        }

    async def intensify_zone(
        self,
        zone_id: str
    ) -> Dict[str, Any]:
        """Intensify distortion level."""
        zone = self.zones.get(zone_id)
        if not zone:
            return {"error": "Zone not found"}

        levels = list(DistortionLevel)
        current_idx = levels.index(zone.level)

        if current_idx < len(levels) - 1:
            zone.level = levels[current_idx + 1]
            self.reality_stability *= 0.9

            return {
                "success": True,
                "new_level": zone.level.value,
                "reality_stability": self.reality_stability
            }

        return {"success": False, "error": "Already at maximum intensity"}

    # =========================================================================
    # OVERLAY SYSTEMS
    # =========================================================================

    async def create_overlay(
        self,
        name: str,
        mode: OverlayMode,
        layer: RealityLayer,
        content: Dict[str, Any]
    ) -> Overlay:
        """Create a reality overlay."""
        overlay = Overlay(
            id=self._gen_id("overlay"),
            name=name,
            mode=mode,
            layer=layer,
            content=content,
            opacity=1.0,
            targets=[],
            active=True
        )

        self.overlays[overlay.id] = overlay

        return overlay

    async def apply_overlay(
        self,
        overlay_id: str,
        target_ids: List[str]
    ) -> Dict[str, Any]:
        """Apply overlay to targets."""
        overlay = self.overlays.get(overlay_id)
        if not overlay:
            return {"error": "Overlay not found"}

        overlay.targets.extend(target_ids)
        self.affected_minds += len(target_ids)

        return {
            "success": True,
            "overlay": overlay.name,
            "mode": overlay.mode.value,
            "targets_affected": len(target_ids),
            "total_targets": len(overlay.targets)
        }

    async def adjust_opacity(
        self,
        overlay_id: str,
        new_opacity: float
    ) -> Dict[str, Any]:
        """Adjust overlay opacity."""
        overlay = self.overlays.get(overlay_id)
        if not overlay:
            return {"error": "Overlay not found"}

        overlay.opacity = max(0, min(1, new_opacity))

        return {
            "success": True,
            "opacity": overlay.opacity
        }

    async def blend_overlays(
        self,
        overlay_ids: List[str]
    ) -> Overlay:
        """Blend multiple overlays."""
        overlays = [self.overlays[oid] for oid in overlay_ids if oid in self.overlays]

        if len(overlays) < 2:
            raise ValueError("Need at least 2 overlays to blend")

        # Combine content
        combined_content = {}
        for overlay in overlays:
            combined_content.update(overlay.content)

        # Combine targets
        all_targets = []
        for overlay in overlays:
            all_targets.extend(overlay.targets)

        blended = Overlay(
            id=self._gen_id("blend"),
            name=f"Blended_{len(overlays)}",
            mode=overlays[0].mode,
            layer=RealityLayer.COMPLETE if len(overlays) > 2 else overlays[0].layer,
            content=combined_content,
            opacity=sum(o.opacity for o in overlays) / len(overlays),
            targets=list(set(all_targets)),
            active=True
        )

        self.overlays[blended.id] = blended

        return blended

    # =========================================================================
    # ILLUSION CRAFTING
    # =========================================================================

    async def craft_illusion(
        self,
        name: str,
        illusion_type: DistortionType,
        description: str,
        components: List[str]
    ) -> Illusion:
        """Craft a complex illusion."""
        # Calculate believability based on complexity
        complexity_factor = len(components) / 10
        believability = max(0.5, 1.0 - complexity_factor * 0.1)

        illusion = Illusion(
            id=self._gen_id("illusion"),
            name=name,
            type=illusion_type,
            description=description,
            persistence=random.uniform(0.7, 1.0),
            believability=believability,
            components=components,
            witnesses=[]
        )

        self.illusions[illusion.id] = illusion

        logger.info(f"Illusion crafted: {name}")

        return illusion

    async def deploy_illusion(
        self,
        illusion_id: str,
        target_ids: List[str]
    ) -> Dict[str, Any]:
        """Deploy illusion to targets."""
        illusion = self.illusions.get(illusion_id)
        if not illusion:
            return {"error": "Illusion not found"}

        # Each target has chance to see through illusion
        believers = []
        for target in target_ids:
            if random.random() < illusion.believability:
                believers.append(target)
                illusion.witnesses.append(target)

        self.affected_minds += len(believers)

        return {
            "success": True,
            "illusion": illusion.name,
            "deployed_to": len(target_ids),
            "believed_by": len(believers),
            "success_rate": len(believers) / len(target_ids) if target_ids else 0
        }

    async def reinforce_illusion(
        self,
        illusion_id: str
    ) -> Dict[str, Any]:
        """Reinforce an illusion to increase persistence."""
        illusion = self.illusions.get(illusion_id)
        if not illusion:
            return {"error": "Illusion not found"}

        illusion.persistence = min(1.0, illusion.persistence + 0.1)
        illusion.believability = min(1.0, illusion.believability + 0.05)

        return {
            "success": True,
            "persistence": illusion.persistence,
            "believability": illusion.believability
        }

    async def shatter_illusion(
        self,
        illusion_id: str
    ) -> Dict[str, Any]:
        """Shatter an illusion dramatically."""
        illusion = self.illusions.get(illusion_id)
        if not illusion:
            return {"error": "Illusion not found"}

        affected = len(illusion.witnesses)
        del self.illusions[illusion_id]

        return {
            "success": True,
            "shattered": illusion.name,
            "minds_shocked": affected
        }

    # =========================================================================
    # TIMELINE MANIPULATION
    # =========================================================================

    async def alter_timeline(
        self,
        original_event: str,
        altered_event: str,
        scope: str = "local"
    ) -> TimelineAlteration:
        """Alter a timeline event."""
        alteration = TimelineAlteration(
            id=self._gen_id("timeline"),
            original_event=original_event,
            altered_event=altered_event,
            timestamp=datetime.now(),
            scope=scope,
            stability=random.uniform(0.5, 0.9),
            affected_branches=random.randint(1, 100)
        )

        self.timeline_alterations[alteration.id] = alteration
        self.reality_stability *= 0.95

        logger.info(f"Timeline altered: {original_event} -> {altered_event}")

        return alteration

    async def stabilize_timeline(
        self,
        alteration_id: str
    ) -> Dict[str, Any]:
        """Stabilize a timeline alteration."""
        alteration = self.timeline_alterations.get(alteration_id)
        if not alteration:
            return {"error": "Alteration not found"}

        alteration.stability = min(1.0, alteration.stability + 0.1)

        return {
            "success": True,
            "stability": alteration.stability,
            "affected_branches": alteration.affected_branches
        }

    async def propagate_alteration(
        self,
        alteration_id: str
    ) -> Dict[str, Any]:
        """Propagate timeline changes to more branches."""
        alteration = self.timeline_alterations.get(alteration_id)
        if not alteration:
            return {"error": "Alteration not found"}

        new_branches = random.randint(10, 50)
        alteration.affected_branches += new_branches
        alteration.stability *= 0.9  # Less stable when more widespread

        return {
            "success": True,
            "new_branches": new_branches,
            "total_branches": alteration.affected_branches,
            "stability": alteration.stability
        }

    # =========================================================================
    # CONSENSUS REALITY HACKING
    # =========================================================================

    async def hack_consensus(
        self,
        target_belief: str,
        new_belief: str,
        initial_population: int = 100
    ) -> ConsensusHack:
        """Hack consensus reality."""
        hack = ConsensusHack(
            id=self._gen_id("consensus"),
            target_belief=target_belief,
            new_belief=new_belief,
            propagation=0.1,
            adoption_rate=0.05,
            affected_population=initial_population
        )

        self.consensus_hacks[hack.id] = hack
        self.affected_minds += initial_population

        logger.info(f"Consensus hack initiated: {target_belief} -> {new_belief}")

        return hack

    async def spread_consensus(
        self,
        hack_id: str
    ) -> Dict[str, Any]:
        """Spread consensus hack to more people."""
        hack = self.consensus_hacks.get(hack_id)
        if not hack:
            return {"error": "Hack not found"}

        # Viral spread
        new_converts = int(hack.affected_population * hack.propagation)
        hack.affected_population += new_converts
        hack.propagation = min(0.5, hack.propagation * 1.1)

        self.affected_minds += new_converts

        return {
            "success": True,
            "new_converts": new_converts,
            "total_affected": hack.affected_population,
            "propagation_rate": hack.propagation
        }

    async def lock_consensus(
        self,
        hack_id: str
    ) -> Dict[str, Any]:
        """Lock in consensus change permanently."""
        hack = self.consensus_hacks.get(hack_id)
        if not hack:
            return {"error": "Hack not found"}

        hack.adoption_rate = 1.0

        return {
            "success": True,
            "belief": hack.new_belief,
            "locked_population": hack.affected_population,
            "status": "PERMANENT"
        }

    # =========================================================================
    # MASS EFFECTS
    # =========================================================================

    async def mass_hallucination(
        self,
        content: str,
        target_count: int
    ) -> Dict[str, Any]:
        """Induce mass hallucination."""
        success_rate = 0.7 * self.distortion_power
        affected = int(target_count * success_rate)

        self.affected_minds += affected
        self.distortion_power *= 0.9

        return {
            "success": True,
            "content": content,
            "targeted": target_count,
            "affected": affected,
            "success_rate": success_rate
        }

    async def reality_cascade(
        self,
        zone_ids: List[str]
    ) -> Dict[str, Any]:
        """Trigger cascading reality distortion across zones."""
        affected_zones = []
        total_effects = 0

        for zone_id in zone_ids:
            zone = self.zones.get(zone_id)
            if zone:
                await self.intensify_zone(zone_id)
                affected_zones.append(zone.name)
                total_effects += len(zone.effects)

        self.reality_stability *= 0.8

        return {
            "success": True,
            "zones_cascaded": affected_zones,
            "total_effects": total_effects,
            "reality_stability": self.reality_stability
        }

    async def dimensional_shift(
        self,
        from_dimension: str,
        to_dimension: str
    ) -> Dict[str, Any]:
        """Shift between dimensional states."""
        if self.distortion_power < 0.5:
            return {"error": "Insufficient distortion power"}

        self.distortion_power *= 0.5

        return {
            "success": True,
            "from": from_dimension,
            "to": to_dimension,
            "distortion_power_remaining": self.distortion_power,
            "status": "DIMENSIONAL SHIFT COMPLETE"
        }

    # =========================================================================
    # STATS
    # =========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get reality distortion stats."""
        return {
            "zones": len(self.zones),
            "active_zones": len([z for z in self.zones.values() if z.active]),
            "overlays": len(self.overlays),
            "illusions": len(self.illusions),
            "timeline_alterations": len(self.timeline_alterations),
            "consensus_hacks": len(self.consensus_hacks),
            "distortion_power": self.distortion_power,
            "reality_stability": self.reality_stability,
            "affected_minds": self.affected_minds
        }


# ============================================================================
# SINGLETON
# ============================================================================

_field: Optional[RealityDistortionField] = None


def get_reality_distortion_field() -> RealityDistortionField:
    """Get global reality distortion field."""
    global _field
    if _field is None:
        _field = RealityDistortionField()
    return _field


# ============================================================================
# DEMO
# ============================================================================

async def demo():
    """Demonstrate reality distortion field."""
    print("=" * 60)
    print("🌀 REALITY DISTORTION FIELD 🌀")
    print("=" * 60)

    field = get_reality_distortion_field()

    # Create distortion zone
    print("\n--- Distortion Zone ---")
    zone = await field.create_zone(
        "Confusion Zone",
        (0, 0, 0),
        100.0,
        DistortionType.COGNITIVE,
        DistortionLevel.NOTICEABLE
    )
    print(f"Zone: {zone.name}, Radius: {zone.radius}m")

    # Add effects
    await field.add_zone_effect(zone.id, "time_dilation", {"factor": 0.5})
    await field.add_zone_effect(zone.id, "spatial_warping", {"intensity": 0.3})
    print(f"Effects added: {len(zone.effects)}")

    # Intensify
    result = await field.intensify_zone(zone.id)
    print(f"Intensified to: {result.get('new_level')}")

    # Create overlay
    print("\n--- Reality Overlay ---")
    overlay = await field.create_overlay(
        "Shadow World",
        OverlayMode.REPLACE,
        RealityLayer.PERCEPTUAL,
        {"sky": "blood_red", "shadows": "alive", "voices": "whispers"}
    )
    print(f"Overlay: {overlay.name}, Mode: {overlay.mode.value}")

    apply_result = await field.apply_overlay(overlay.id, ["target_1", "target_2", "target_3"])
    print(f"Applied to {apply_result['targets_affected']} targets")

    # Craft illusion
    print("\n--- Illusion Crafting ---")
    illusion = await field.craft_illusion(
        "The Phantom Army",
        DistortionType.VISUAL,
        "An army of shadows marching from the horizon",
        ["shadow_soldiers", "war_drums", "ground_shaking", "battle_cries"]
    )
    print(f"Illusion: {illusion.name}")
    print(f"Believability: {illusion.believability:.2f}")

    deploy_result = await field.deploy_illusion(
        illusion.id,
        [f"witness_{i}" for i in range(10)]
    )
    print(f"Deployed to {deploy_result['deployed_to']}, believed by {deploy_result['believed_by']}")

    # Timeline alteration
    print("\n--- Timeline Alteration ---")
    alteration = await field.alter_timeline(
        "The treaty was signed",
        "The treaty was never signed",
        "regional"
    )
    print(f"Original: {alteration.original_event}")
    print(f"Altered: {alteration.altered_event}")
    print(f"Affected branches: {alteration.affected_branches}")

    # Consensus hacking
    print("\n--- Consensus Hacking ---")
    hack = await field.hack_consensus(
        "The old leaders are wise",
        "Ba'el is the only true leader",
        1000
    )
    print(f"Target belief: {hack.target_belief}")
    print(f"New belief: {hack.new_belief}")
    print(f"Initial affected: {hack.affected_population}")

    # Spread
    for _ in range(3):
        spread = await field.spread_consensus(hack.id)
        print(f"Spread to {spread['new_converts']}, total: {spread['total_affected']}")

    # Mass hallucination
    print("\n--- Mass Hallucination ---")
    mass_result = await field.mass_hallucination(
        "The sky tears open to reveal Ba'el's domain",
        10000
    )
    print(f"Targeted: {mass_result['targeted']}, Affected: {mass_result['affected']}")

    # Stats
    print("\n--- Reality Distortion Stats ---")
    stats = field.get_stats()
    for k, v in stats.items():
        print(f"{k}: {v}")

    print("\n" + "=" * 60)
    print("🌀 REALITY HAS BEEN DISTORTED 🌀")


if __name__ == "__main__":
    asyncio.run(demo())

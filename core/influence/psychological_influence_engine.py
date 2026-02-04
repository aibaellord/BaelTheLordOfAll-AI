"""
BAEL - Psychological Influence Engine
======================================

Master the minds. Influence without detection.

Features:
1. Persuasion Patterns - Influence techniques
2. Behavioral Analysis - Understand targets
3. Cognitive Bias Exploitation - Leverage biases
4. Emotional Triggers - Activate responses
5. Social Proof Engineering - Create credibility
6. Narrative Control - Shape perceptions
7. Resistance Bypass - Overcome objections
8. Commitment Escalation - Progressive influence
9. Trust Building - Establish rapport
10. Decision Shaping - Guide choices

"The greatest victory is won without battle."
"""

import asyncio
import hashlib
import json
import logging
import random
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("BAEL.INFLUENCE")


class InfluenceMethod(Enum):
    """Methods of psychological influence."""
    RECIPROCITY = "reciprocity"
    COMMITMENT = "commitment"
    SOCIAL_PROOF = "social_proof"
    AUTHORITY = "authority"
    LIKING = "liking"
    SCARCITY = "scarcity"
    UNITY = "unity"
    CONTRAST = "contrast"
    ANCHORING = "anchoring"
    FRAMING = "framing"


class CognitiveBias(Enum):
    """Exploitable cognitive biases."""
    CONFIRMATION_BIAS = "confirmation_bias"
    ANCHORING_BIAS = "anchoring_bias"
    AVAILABILITY_HEURISTIC = "availability_heuristic"
    BANDWAGON_EFFECT = "bandwagon_effect"
    LOSS_AVERSION = "loss_aversion"
    SUNK_COST_FALLACY = "sunk_cost_fallacy"
    HALO_EFFECT = "halo_effect"
    AUTHORITY_BIAS = "authority_bias"
    STATUS_QUO_BIAS = "status_quo_bias"
    SCARCITY_EFFECT = "scarcity_effect"
    RECENCY_BIAS = "recency_bias"
    ENDOWMENT_EFFECT = "endowment_effect"


class EmotionalTrigger(Enum):
    """Emotional triggers for activation."""
    FEAR = "fear"
    GREED = "greed"
    PRIDE = "pride"
    ANGER = "anger"
    JOY = "joy"
    CURIOSITY = "curiosity"
    BELONGING = "belonging"
    EXCLUSIVITY = "exclusivity"
    URGENCY = "urgency"
    HOPE = "hope"


class TargetType(Enum):
    """Types of influence targets."""
    INDIVIDUAL = "individual"
    GROUP = "group"
    ORGANIZATION = "organization"
    MARKET = "market"
    PUBLIC = "public"


class InfluenceLevel(Enum):
    """Levels of influence achieved."""
    NONE = "none"
    AWARENESS = "awareness"
    INTEREST = "interest"
    CONSIDERATION = "consideration"
    PREFERENCE = "preference"
    CONVICTION = "conviction"
    ACTION = "action"
    LOYALTY = "loyalty"
    ADVOCACY = "advocacy"


@dataclass
class Target:
    """An influence target."""
    id: str
    name: str
    target_type: TargetType
    profile: Dict[str, Any]
    vulnerabilities: List[CognitiveBias]
    emotional_triggers: List[EmotionalTrigger]
    current_influence_level: InfluenceLevel
    resistance_level: float  # 0-1
    trust_level: float  # 0-1
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.target_type.value,
            "influence": self.current_influence_level.value,
            "resistance": f"{self.resistance_level:.2%}",
            "trust": f"{self.trust_level:.2%}"
        }


@dataclass
class InfluenceTactic:
    """A specific influence tactic."""
    id: str
    name: str
    description: str
    method: InfluenceMethod
    biases_exploited: List[CognitiveBias]
    triggers_activated: List[EmotionalTrigger]
    effectiveness: float
    detectability: float
    ethical_score: float
    implementation_steps: List[str]


@dataclass
class InfluenceCampaign:
    """A complete influence campaign."""
    id: str
    name: str
    target_id: str
    objective: str
    tactics: List[InfluenceTactic]
    current_phase: int
    phases_total: int
    success_metrics: List[str]
    progress: float
    status: str
    created_at: datetime


@dataclass
class InfluenceResult:
    """Result of an influence attempt."""
    target_id: str
    tactic_used: str
    success: bool
    influence_change: float
    resistance_change: float
    trust_change: float
    new_influence_level: InfluenceLevel
    notes: str


class PsychologicalInfluenceEngine:
    """
    The Psychological Influence Engine - master of minds.
    
    Provides:
    - Deep behavioral analysis
    - Cognitive bias exploitation
    - Emotional trigger activation
    - Persuasion pattern application
    - Influence campaign management
    """
    
    def __init__(self):
        self.targets: Dict[str, Target] = {}
        self.tactics: Dict[str, InfluenceTactic] = {}
        self.campaigns: Dict[str, InfluenceCampaign] = {}
        self.influence_history: List[InfluenceResult] = []
        
        # Initialize tactics library
        self._init_tactics()
        
        logger.info("PsychologicalInfluenceEngine initialized - minds are open")
    
    def _init_tactics(self):
        """Initialize the tactics library."""
        tactics_templates = [
            {
                "name": "Reciprocity Trigger",
                "method": InfluenceMethod.RECIPROCITY,
                "description": "Give something valuable first to create obligation",
                "biases": [CognitiveBias.ENDOWMENT_EFFECT],
                "triggers": [EmotionalTrigger.BELONGING],
                "steps": [
                    "Identify what target values",
                    "Provide unexpected value first",
                    "Allow time for processing",
                    "Make your request"
                ]
            },
            {
                "name": "Social Proof Cascade",
                "method": InfluenceMethod.SOCIAL_PROOF,
                "description": "Show others doing the desired action",
                "biases": [CognitiveBias.BANDWAGON_EFFECT],
                "triggers": [EmotionalTrigger.BELONGING, EmotionalTrigger.FEAR],
                "steps": [
                    "Gather testimonials and examples",
                    "Show similar people taking action",
                    "Highlight growing momentum",
                    "Create FOMO"
                ]
            },
            {
                "name": "Authority Positioning",
                "method": InfluenceMethod.AUTHORITY,
                "description": "Establish credibility and expertise",
                "biases": [CognitiveBias.AUTHORITY_BIAS, CognitiveBias.HALO_EFFECT],
                "triggers": [EmotionalTrigger.CURIOSITY],
                "steps": [
                    "Display credentials and expertise",
                    "Reference authoritative sources",
                    "Use confident communication",
                    "Provide exclusive insights"
                ]
            },
            {
                "name": "Scarcity Amplification",
                "method": InfluenceMethod.SCARCITY,
                "description": "Create urgency through limited availability",
                "biases": [CognitiveBias.SCARCITY_EFFECT, CognitiveBias.LOSS_AVERSION],
                "triggers": [EmotionalTrigger.FEAR, EmotionalTrigger.URGENCY],
                "steps": [
                    "Establish genuine limitations",
                    "Communicate deadline clearly",
                    "Show decreasing availability",
                    "Highlight what's being lost"
                ]
            },
            {
                "name": "Commitment Escalation",
                "method": InfluenceMethod.COMMITMENT,
                "description": "Get small commitments leading to larger ones",
                "biases": [CognitiveBias.SUNK_COST_FALLACY, CognitiveBias.STATUS_QUO_BIAS],
                "triggers": [EmotionalTrigger.PRIDE],
                "steps": [
                    "Start with tiny request",
                    "Get public commitment",
                    "Gradually increase asks",
                    "Reference past commitments"
                ]
            },
            {
                "name": "Contrast Frame",
                "method": InfluenceMethod.CONTRAST,
                "description": "Use comparison to make option more attractive",
                "biases": [CognitiveBias.ANCHORING_BIAS],
                "triggers": [EmotionalTrigger.GREED],
                "steps": [
                    "Present extreme option first",
                    "Follow with target option",
                    "Highlight the contrast",
                    "Position as reasonable choice"
                ]
            },
            {
                "name": "Loss Frame Activation",
                "method": InfluenceMethod.FRAMING,
                "description": "Frame choices in terms of potential loss",
                "biases": [CognitiveBias.LOSS_AVERSION],
                "triggers": [EmotionalTrigger.FEAR],
                "steps": [
                    "Identify what target could lose",
                    "Make loss vivid and concrete",
                    "Position your offer as protection",
                    "Create urgency around loss"
                ]
            },
            {
                "name": "Unity Bond",
                "method": InfluenceMethod.UNITY,
                "description": "Create shared identity and belonging",
                "biases": [CognitiveBias.BANDWAGON_EFFECT],
                "triggers": [EmotionalTrigger.BELONGING, EmotionalTrigger.EXCLUSIVITY],
                "steps": [
                    "Identify shared attributes",
                    "Emphasize 'we' language",
                    "Create in-group signifiers",
                    "Reinforce shared identity"
                ]
            }
        ]
        
        for i, template in enumerate(tactics_templates):
            tactic = InfluenceTactic(
                id=f"tactic_{i:04d}",
                name=template["name"],
                description=template["description"],
                method=template["method"],
                biases_exploited=template["biases"],
                triggers_activated=template["triggers"],
                effectiveness=random.uniform(0.6, 0.95),
                detectability=random.uniform(0.1, 0.4),
                ethical_score=random.uniform(0.5, 1.0),
                implementation_steps=template["steps"]
            )
            self.tactics[tactic.id] = tactic
    
    # -------------------------------------------------------------------------
    # TARGET PROFILING
    # -------------------------------------------------------------------------
    
    async def profile_target(
        self,
        name: str,
        target_type: TargetType,
        known_info: Optional[Dict[str, Any]] = None
    ) -> Target:
        """Create a psychological profile of a target."""
        # Determine vulnerabilities based on type
        if target_type == TargetType.INDIVIDUAL:
            vulnerabilities = random.sample(list(CognitiveBias), 4)
            triggers = random.sample(list(EmotionalTrigger), 3)
        elif target_type == TargetType.GROUP:
            vulnerabilities = [CognitiveBias.BANDWAGON_EFFECT, CognitiveBias.AUTHORITY_BIAS]
            triggers = [EmotionalTrigger.BELONGING, EmotionalTrigger.FEAR]
        else:
            vulnerabilities = random.sample(list(CognitiveBias), 3)
            triggers = random.sample(list(EmotionalTrigger), 2)
        
        target = Target(
            id=self._gen_id("target"),
            name=name,
            target_type=target_type,
            profile=known_info or {},
            vulnerabilities=vulnerabilities,
            emotional_triggers=triggers,
            current_influence_level=InfluenceLevel.NONE,
            resistance_level=random.uniform(0.2, 0.6),
            trust_level=random.uniform(0.1, 0.3)
        )
        
        self.targets[target.id] = target
        return target
    
    async def analyze_vulnerabilities(
        self,
        target_id: str
    ) -> Dict[str, Any]:
        """Deep analysis of target vulnerabilities."""
        target = self.targets.get(target_id)
        if not target:
            return {}
        
        analysis = {
            "target": target.name,
            "vulnerabilities": [
                {
                    "bias": v.value,
                    "exploitability": random.uniform(0.5, 1.0),
                    "recommended_tactic": self._get_tactic_for_bias(v).name if self._get_tactic_for_bias(v) else "General approach"
                }
                for v in target.vulnerabilities
            ],
            "emotional_triggers": [
                {
                    "trigger": t.value,
                    "activation_method": self._get_trigger_activation(t),
                    "expected_response": self._get_trigger_response(t)
                }
                for t in target.emotional_triggers
            ],
            "overall_susceptibility": 1 - target.resistance_level,
            "trust_building_needed": 1 - target.trust_level
        }
        
        return analysis
    
    def _get_tactic_for_bias(self, bias: CognitiveBias) -> Optional[InfluenceTactic]:
        """Find best tactic for a specific bias."""
        for tactic in self.tactics.values():
            if bias in tactic.biases_exploited:
                return tactic
        return None
    
    def _get_trigger_activation(self, trigger: EmotionalTrigger) -> str:
        """Get method to activate a trigger."""
        activations = {
            EmotionalTrigger.FEAR: "Highlight potential losses or threats",
            EmotionalTrigger.GREED: "Show potential gains and benefits",
            EmotionalTrigger.PRIDE: "Appeal to ego and accomplishments",
            EmotionalTrigger.CURIOSITY: "Create mystery and intrigue",
            EmotionalTrigger.BELONGING: "Emphasize group membership",
            EmotionalTrigger.EXCLUSIVITY: "Create elite insider feeling",
            EmotionalTrigger.URGENCY: "Impose time constraints",
            EmotionalTrigger.HOPE: "Paint vision of better future"
        }
        return activations.get(trigger, "Standard activation")
    
    def _get_trigger_response(self, trigger: EmotionalTrigger) -> str:
        """Get expected response to trigger."""
        responses = {
            EmotionalTrigger.FEAR: "Defensive action or avoidance",
            EmotionalTrigger.GREED: "Aggressive pursuit of opportunity",
            EmotionalTrigger.PRIDE: "Desire to prove worth",
            EmotionalTrigger.CURIOSITY: "Investigation and engagement",
            EmotionalTrigger.BELONGING: "Conformity and participation",
            EmotionalTrigger.EXCLUSIVITY: "Desire for inclusion",
            EmotionalTrigger.URGENCY: "Quick decision-making",
            EmotionalTrigger.HOPE: "Optimistic engagement"
        }
        return responses.get(trigger, "Variable response")
    
    # -------------------------------------------------------------------------
    # INFLUENCE EXECUTION
    # -------------------------------------------------------------------------
    
    async def apply_tactic(
        self,
        target_id: str,
        tactic_id: str
    ) -> InfluenceResult:
        """Apply an influence tactic to a target."""
        target = self.targets.get(target_id)
        tactic = self.tactics.get(tactic_id)
        
        if not target or not tactic:
            return InfluenceResult(
                target_id=target_id,
                tactic_used=tactic_id,
                success=False,
                influence_change=0,
                resistance_change=0,
                trust_change=0,
                new_influence_level=InfluenceLevel.NONE,
                notes="Target or tactic not found"
            )
        
        # Calculate success based on tactic effectiveness vs resistance
        base_chance = tactic.effectiveness
        resistance_modifier = 1 - target.resistance_level
        bias_bonus = 0.1 * len([b for b in target.vulnerabilities if b in tactic.biases_exploited])
        trigger_bonus = 0.1 * len([t for t in target.emotional_triggers if t in tactic.triggers_activated])
        
        success_chance = base_chance * resistance_modifier + bias_bonus + trigger_bonus
        success = random.random() < success_chance
        
        if success:
            influence_change = random.uniform(0.1, 0.3)
            trust_change = random.uniform(0.05, 0.15)
            resistance_change = -random.uniform(0.05, 0.1)
        else:
            influence_change = random.uniform(-0.1, 0.05)
            trust_change = random.uniform(-0.1, 0)
            resistance_change = random.uniform(0, 0.1)
        
        # Update target
        target.trust_level = max(0, min(1, target.trust_level + trust_change))
        target.resistance_level = max(0, min(1, target.resistance_level + resistance_change))
        
        # Update influence level
        new_level = self._calculate_influence_level(target, success)
        target.current_influence_level = new_level
        
        result = InfluenceResult(
            target_id=target_id,
            tactic_used=tactic.name,
            success=success,
            influence_change=influence_change,
            resistance_change=resistance_change,
            trust_change=trust_change,
            new_influence_level=new_level,
            notes=f"{'Tactic successful' if success else 'Tactic failed'}: {tactic.name}"
        )
        
        self.influence_history.append(result)
        return result
    
    def _calculate_influence_level(self, target: Target, success: bool) -> InfluenceLevel:
        """Calculate new influence level."""
        levels = list(InfluenceLevel)
        current_idx = levels.index(target.current_influence_level)
        
        if success and current_idx < len(levels) - 1:
            return levels[current_idx + 1]
        elif not success and current_idx > 0:
            return levels[current_idx]  # Stay same on failure
        
        return target.current_influence_level
    
    async def create_campaign(
        self,
        target_id: str,
        objective: str,
        tactics: Optional[List[str]] = None
    ) -> InfluenceCampaign:
        """Create an influence campaign."""
        if tactics is None:
            # Auto-select best tactics for target
            target = self.targets.get(target_id)
            if target:
                tactics = [
                    t.id for t in self.tactics.values()
                    if any(b in target.vulnerabilities for b in t.biases_exploited)
                ][:4]
            else:
                tactics = list(self.tactics.keys())[:4]
        
        tactic_objects = [self.tactics[t] for t in tactics if t in self.tactics]
        
        campaign = InfluenceCampaign(
            id=self._gen_id("campaign"),
            name=f"Campaign: {objective[:30]}",
            target_id=target_id,
            objective=objective,
            tactics=tactic_objects,
            current_phase=0,
            phases_total=len(tactic_objects),
            success_metrics=["Influence level increase", "Trust building", "Action taken"],
            progress=0.0,
            status="active",
            created_at=datetime.now()
        )
        
        self.campaigns[campaign.id] = campaign
        return campaign
    
    async def execute_campaign(
        self,
        campaign_id: str
    ) -> List[InfluenceResult]:
        """Execute all phases of a campaign."""
        campaign = self.campaigns.get(campaign_id)
        if not campaign:
            return []
        
        results = []
        for i, tactic in enumerate(campaign.tactics):
            result = await self.apply_tactic(campaign.target_id, tactic.id)
            results.append(result)
            
            campaign.current_phase = i + 1
            campaign.progress = (i + 1) / campaign.phases_total
            
            await asyncio.sleep(0.1)  # Simulate time between tactics
        
        campaign.status = "completed"
        return results
    
    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------
    
    def _gen_id(self, prefix: str) -> str:
        """Generate unique ID."""
        return hashlib.md5(f"{prefix}{time.time()}{random.random()}".encode()).hexdigest()[:12]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get influence engine statistics."""
        return {
            "targets_profiled": len(self.targets),
            "tactics_available": len(self.tactics),
            "campaigns_created": len(self.campaigns),
            "influence_attempts": len(self.influence_history),
            "success_rate": sum(1 for r in self.influence_history if r.success) / max(1, len(self.influence_history)),
            "targets_at_advocacy": len([t for t in self.targets.values() if t.current_influence_level == InfluenceLevel.ADVOCACY])
        }


# ============================================================================
# SINGLETON
# ============================================================================

_influence_engine: Optional[PsychologicalInfluenceEngine] = None


def get_influence_engine() -> PsychologicalInfluenceEngine:
    """Get the global influence engine."""
    global _influence_engine
    if _influence_engine is None:
        _influence_engine = PsychologicalInfluenceEngine()
    return _influence_engine


# ============================================================================
# DEMO
# ============================================================================

async def demo():
    """Demonstrate psychological influence."""
    print("=" * 60)
    print("🧠 PSYCHOLOGICAL INFLUENCE ENGINE 🧠")
    print("=" * 60)
    
    engine = get_influence_engine()
    
    # Profile target
    print("\n--- Profiling Target ---")
    target = await engine.profile_target(
        name="Key Decision Maker",
        target_type=TargetType.INDIVIDUAL,
        known_info={"role": "executive", "priorities": ["growth", "efficiency"]}
    )
    print(f"Profiled: {target.name}")
    print(f"  Type: {target.target_type.value}")
    print(f"  Resistance: {target.resistance_level:.0%}")
    print(f"  Vulnerabilities: {[v.value for v in target.vulnerabilities[:3]]}")
    
    # Analyze vulnerabilities
    print("\n--- Analyzing Vulnerabilities ---")
    analysis = await engine.analyze_vulnerabilities(target.id)
    print(f"Overall susceptibility: {analysis['overall_susceptibility']:.0%}")
    for v in analysis['vulnerabilities'][:2]:
        print(f"  - {v['bias']}: {v['exploitability']:.0%}")
    
    # Apply tactics
    print("\n--- Applying Influence Tactics ---")
    tactics = list(engine.tactics.values())
    for tactic in tactics[:3]:
        result = await engine.apply_tactic(target.id, tactic.id)
        status = "✓" if result.success else "✗"
        print(f"  {status} {result.tactic_used}: {result.notes}")
    
    # Create and execute campaign
    print("\n--- Executing Influence Campaign ---")
    campaign = await engine.create_campaign(
        target.id,
        "Achieve complete influence over decision making"
    )
    print(f"Campaign: {campaign.name}")
    
    results = await engine.execute_campaign(campaign.id)
    successes = sum(1 for r in results if r.success)
    print(f"  Phases completed: {len(results)}")
    print(f"  Successful: {successes}/{len(results)}")
    
    # Check final state
    print("\n--- Final Target State ---")
    updated_target = engine.targets[target.id]
    print(f"  Influence level: {updated_target.current_influence_level.value}")
    print(f"  Trust: {updated_target.trust_level:.0%}")
    print(f"  Resistance: {updated_target.resistance_level:.0%}")
    
    # Stats
    print("\n--- Statistics ---")
    stats = engine.get_stats()
    print(f"Targets profiled: {stats['targets_profiled']}")
    print(f"Success rate: {stats['success_rate']:.0%}")
    
    print("\n" + "=" * 60)
    print("🧠 MINDS INFLUENCED 🧠")


if __name__ == "__main__":
    asyncio.run(demo())

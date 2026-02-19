"""
SUPREME COUNCIL - Council of Councils
=====================================
Meta-council coordinating all specialized councils for ultimate decision making.

Features:
- Grand Council oversight
- Specialized council coordination
- Multi-level consensus
- Wisdom synthesis
"""

import asyncio
import logging
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("BAEL.SupremeCouncil")


class CouncilType(Enum):
    """Types of specialized councils."""

    OPTIMIZATION = auto()  # Performance and efficiency
    EXPLOITATION = auto()  # Resource maximization
    INNOVATION = auto()  # Novel approaches
    VALIDATION = auto()  # Quality assurance
    MICRO_DETAIL = auto()  # Fine-grained analysis
    SECURITY = auto()  # Security considerations
    ETHICS = auto()  # Ethical implications
    STRATEGY = auto()  # Strategic direction


class DecisionType(Enum):
    """Types of decisions requiring council."""

    ARCHITECTURAL = "architectural"
    TACTICAL = "tactical"
    RESOURCE = "resource"
    SECURITY = "security"
    FEATURE = "feature"
    EMERGENCY = "emergency"


class ConsensusLevel(Enum):
    """Level of consensus required."""

    UNANIMOUS = 1.0
    SUPERMAJORITY = 0.75
    MAJORITY = 0.51
    PLURALITY = 0.0


@dataclass
class CouncilMember:
    """A member of a council."""

    member_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    council_type: CouncilType = CouncilType.OPTIMIZATION
    expertise: List[str] = field(default_factory=list)
    weight: float = 1.0

    # Track record
    decisions_participated: int = 0
    correct_predictions: int = 0

    @property
    def accuracy(self) -> float:
        if self.decisions_participated == 0:
            return 0.5
        return self.correct_predictions / self.decisions_participated


@dataclass
class CouncilPerspective:
    """A council's perspective on a decision."""

    council_type: CouncilType
    position: str  # "support", "oppose", "neutral"
    reasoning: str
    confidence: float
    recommendations: List[str] = field(default_factory=list)
    concerns: List[str] = field(default_factory=list)
    weight: float = 1.0


@dataclass
class Decision:
    """A decision to be made by councils."""

    decision_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    description: str = ""
    decision_type: DecisionType = DecisionType.TACTICAL
    options: List[str] = field(default_factory=list)

    # Requirements
    required_councils: List[CouncilType] = field(default_factory=list)
    consensus_level: ConsensusLevel = ConsensusLevel.MAJORITY

    # Deliberation
    perspectives: List[CouncilPerspective] = field(default_factory=list)

    # Outcome
    status: str = "pending"
    final_decision: Optional[str] = None
    rationale: str = ""
    dissent: List[str] = field(default_factory=list)
    decided_at: Optional[datetime] = None


@dataclass
class Council:
    """A specialized council."""

    council_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    council_type: CouncilType = CouncilType.OPTIMIZATION
    name: str = ""
    description: str = ""

    # Members
    members: List[CouncilMember] = field(default_factory=list)

    # History
    decisions_made: int = 0
    avg_deliberation_time_ms: float = 0.0


class SupremeCouncil:
    """
    The Supreme Council - coordinates all specialized councils
    for complex decision making.
    """

    def __init__(self):
        # Councils registry
        self.councils: Dict[CouncilType, Council] = {}

        # Decision tracking
        self.pending_decisions: Dict[str, Decision] = {}
        self.completed_decisions: Dict[str, Decision] = {}

        # Decision routing rules
        self.decision_routing: Dict[DecisionType, List[CouncilType]] = {
            DecisionType.ARCHITECTURAL: [
                CouncilType.OPTIMIZATION,
                CouncilType.INNOVATION,
                CouncilType.VALIDATION,
                CouncilType.SECURITY,
            ],
            DecisionType.TACTICAL: [CouncilType.OPTIMIZATION, CouncilType.EXPLOITATION],
            DecisionType.RESOURCE: [CouncilType.EXPLOITATION, CouncilType.OPTIMIZATION],
            DecisionType.SECURITY: [
                CouncilType.SECURITY,
                CouncilType.VALIDATION,
                CouncilType.ETHICS,
            ],
            DecisionType.FEATURE: [
                CouncilType.INNOVATION,
                CouncilType.VALIDATION,
                CouncilType.MICRO_DETAIL,
            ],
            DecisionType.EMERGENCY: list(CouncilType),  # All councils
        }

        # Initialize default councils
        self._initialize_councils()

    def _initialize_councils(self) -> None:
        """Initialize all specialized councils."""
        council_configs = [
            (
                CouncilType.OPTIMIZATION,
                "Optimization Council",
                "Performance and efficiency optimization",
            ),
            (
                CouncilType.EXPLOITATION,
                "Exploitation Council",
                "Resource maximization and zero-cost strategies",
            ),
            (
                CouncilType.INNOVATION,
                "Innovation Council",
                "Novel approaches and creative solutions",
            ),
            (
                CouncilType.VALIDATION,
                "Validation Council",
                "Quality assurance and testing",
            ),
            (
                CouncilType.MICRO_DETAIL,
                "Micro-Detail Council",
                "Fine-grained analysis and edge cases",
            ),
            (
                CouncilType.SECURITY,
                "Security Council",
                "Security considerations and threat analysis",
            ),
            (
                CouncilType.ETHICS,
                "Ethics Council",
                "Ethical implications and responsible AI",
            ),
            (
                CouncilType.STRATEGY,
                "Strategy Council",
                "Strategic direction and long-term planning",
            ),
        ]

        for council_type, name, description in council_configs:
            council = Council(
                council_type=council_type, name=name, description=description
            )

            # Add default members
            council.members = [
                CouncilMember(
                    name=f"{name} - Lead",
                    council_type=council_type,
                    expertise=[council_type.name.lower()],
                    weight=1.5,
                ),
                CouncilMember(
                    name=f"{name} - Senior",
                    council_type=council_type,
                    expertise=[council_type.name.lower()],
                    weight=1.0,
                ),
                CouncilMember(
                    name=f"{name} - Analyst",
                    council_type=council_type,
                    expertise=[council_type.name.lower(), "analysis"],
                    weight=0.8,
                ),
            ]

            self.councils[council_type] = council

        logger.info(f"Initialized {len(self.councils)} councils")

    def create_decision(
        self,
        title: str,
        description: str,
        decision_type: DecisionType,
        options: List[str] = None,
        consensus_level: ConsensusLevel = ConsensusLevel.MAJORITY,
    ) -> Decision:
        """Create a new decision for deliberation."""
        # Get required councils based on decision type
        required = self.decision_routing.get(decision_type, [CouncilType.OPTIMIZATION])

        decision = Decision(
            title=title,
            description=description,
            decision_type=decision_type,
            options=options or [],
            required_councils=required,
            consensus_level=consensus_level,
        )

        self.pending_decisions[decision.decision_id] = decision
        logger.info(f"Created decision: {title} ({decision_type.value})")

        return decision

    async def deliberate(self, decision_id: str) -> Decision:
        """Run full deliberation on a decision."""
        if decision_id not in self.pending_decisions:
            raise ValueError(f"Decision {decision_id} not found")

        decision = self.pending_decisions[decision_id]
        decision.status = "deliberating"

        # Gather perspectives from all required councils
        perspective_tasks = [
            self._get_council_perspective(council_type, decision)
            for council_type in decision.required_councils
        ]

        perspectives = await asyncio.gather(*perspective_tasks)
        decision.perspectives = [p for p in perspectives if p is not None]

        # Synthesize decision
        final = await self._synthesize_decision(decision)

        decision.final_decision = final["decision"]
        decision.rationale = final["rationale"]
        decision.dissent = final.get("dissent", [])
        decision.status = "decided"
        decision.decided_at = datetime.now()

        # Move to completed
        del self.pending_decisions[decision_id]
        self.completed_decisions[decision_id] = decision

        logger.info(f"Decision made: {decision.title} -> {decision.final_decision}")

        return decision

    async def _get_council_perspective(
        self, council_type: CouncilType, decision: Decision
    ) -> Optional[CouncilPerspective]:
        """Get a council's perspective on a decision."""
        if council_type not in self.councils:
            return None

        council = self.councils[council_type]

        # Simulate council deliberation
        await asyncio.sleep(0.01)

        # Generate perspective based on council type
        perspective = CouncilPerspective(
            council_type=council_type,
            position="support",
            reasoning=f"{council.name} analysis of: {decision.title}",
            confidence=0.8,
            weight=1.0,
        )

        # Each council focuses on their domain
        if council_type == CouncilType.OPTIMIZATION:
            perspective.recommendations = ["Optimize for performance", "Reduce latency"]
            perspective.concerns = ["Resource overhead"]
        elif council_type == CouncilType.EXPLOITATION:
            perspective.recommendations = [
                "Maximize free tier usage",
                "Rotate credentials",
            ]
            perspective.concerns = ["Rate limiting"]
        elif council_type == CouncilType.INNOVATION:
            perspective.recommendations = [
                "Novel approach considered",
                "Creative solution",
            ]
            perspective.concerns = ["Unproven methods"]
        elif council_type == CouncilType.VALIDATION:
            perspective.recommendations = [
                "Add comprehensive tests",
                "Validate edge cases",
            ]
            perspective.concerns = ["Test coverage gaps"]
        elif council_type == CouncilType.SECURITY:
            perspective.recommendations = [
                "Security audit required",
                "Input validation",
            ]
            perspective.concerns = ["Potential vulnerabilities"]
        elif council_type == CouncilType.MICRO_DETAIL:
            perspective.recommendations = ["Check edge cases", "Handle null values"]
            perspective.concerns = ["Corner case failures"]

        council.decisions_made += 1

        return perspective

    async def _synthesize_decision(self, decision: Decision) -> Dict[str, Any]:
        """Synthesize final decision from all perspectives."""
        if not decision.perspectives:
            return {
                "decision": "No consensus - insufficient perspectives",
                "rationale": "Required councils did not provide input",
            }

        # Count positions with weights
        support_weight = 0.0
        oppose_weight = 0.0
        total_weight = 0.0

        for perspective in decision.perspectives:
            total_weight += perspective.weight * perspective.confidence
            if perspective.position == "support":
                support_weight += perspective.weight * perspective.confidence
            elif perspective.position == "oppose":
                oppose_weight += perspective.weight * perspective.confidence

        # Calculate support ratio
        support_ratio = support_weight / total_weight if total_weight > 0 else 0.5

        # Check against consensus threshold
        threshold = decision.consensus_level.value

        if support_ratio >= threshold:
            final_decision = "APPROVED"
        elif (1 - support_ratio) >= threshold:
            final_decision = "REJECTED"
        else:
            final_decision = "NEEDS_REVIEW"

        # Collect all recommendations and concerns
        all_recommendations = []
        all_concerns = []
        dissent = []

        for perspective in decision.perspectives:
            all_recommendations.extend(perspective.recommendations)
            all_concerns.extend(perspective.concerns)

            if perspective.position == "oppose":
                dissent.append(
                    f"{perspective.council_type.name}: {perspective.reasoning}"
                )

        rationale = f"Support ratio: {support_ratio:.2f} (threshold: {threshold}). "
        rationale += f"Recommendations: {', '.join(all_recommendations[:3])}. "
        rationale += f"Concerns: {', '.join(all_concerns[:3])}."

        return {
            "decision": final_decision,
            "rationale": rationale,
            "support_ratio": support_ratio,
            "dissent": dissent,
        }

    async def emergency_decision(self, title: str, description: str) -> Decision:
        """Make emergency decision with all councils."""
        decision = self.create_decision(
            title=title,
            description=description,
            decision_type=DecisionType.EMERGENCY,
            consensus_level=ConsensusLevel.MAJORITY,
        )

        return await self.deliberate(decision.decision_id)

    def get_status(self) -> Dict[str, Any]:
        """Get Supreme Council status."""
        total_decisions = sum(c.decisions_made for c in self.councils.values())

        return {
            "councils": len(self.councils),
            "total_members": sum(len(c.members) for c in self.councils.values()),
            "pending_decisions": len(self.pending_decisions),
            "completed_decisions": len(self.completed_decisions),
            "total_deliberations": total_decisions,
        }


# Singleton instance
_supreme_council: Optional[SupremeCouncil] = None


def get_supreme_council() -> SupremeCouncil:
    """Get or create the Supreme Council singleton."""
    global _supreme_council
    if _supreme_council is None:
        _supreme_council = SupremeCouncil()
    return _supreme_council


# Export
__all__ = [
    "CouncilType",
    "DecisionType",
    "ConsensusLevel",
    "CouncilMember",
    "CouncilPerspective",
    "Decision",
    "Council",
    "SupremeCouncil",
    "get_supreme_council",
]

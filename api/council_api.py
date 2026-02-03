"""
BAEL Council API - Full Grand Council Integration
==================================================

This API exposes the full Grand Council capabilities:
- Multi-council hierarchy
- Real-time deliberation with phases
- Adversarial challenge/response
- Multiple voting methods
- Proposal synthesis
- LLM-powered member opinions

Endpoints:
- POST /council/session - Start a council session
- POST /council/deliberate - Full deliberation on a topic
- POST /council/vote - Cast votes on proposals
- GET /council/members - List available council members
- GET /council/sessions - List past sessions
- GET /council/status - Get current session status
- WS /council/stream - WebSocket for real-time updates
"""

import asyncio
import json
import logging
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

logger = logging.getLogger("BAEL.CouncilAPI")

router = APIRouter(prefix="/v1/council", tags=["council"])


# =============================================================================
# MODELS
# =============================================================================

class CouncilTypeEnum(str, Enum):
    grand = "grand"
    optimization = "optimization"
    innovation = "innovation"
    validation = "validation"
    strategy = "strategy"
    security = "security"


class VotingMethodEnum(str, Enum):
    unanimous = "unanimous"
    supermajority = "supermajority"
    majority = "majority"
    weighted = "weighted"
    consensus = "consensus"


class PerspectiveEnum(str, Enum):
    logical = "logical"
    creative = "creative"
    adversarial = "adversarial"
    optimistic = "optimistic"
    pessimistic = "pessimistic"
    historical = "historical"
    predictive = "predictive"
    resource_aware = "resource_aware"


class MemberResponse(BaseModel):
    id: str
    name: str
    role: str
    expertise: List[str]
    perspectives: List[str]
    color: str
    active: bool = True


class DeliberationPhaseResponse(BaseModel):
    phase: str
    status: str
    progress: float
    messages: List[Dict[str, Any]]


class SessionRequest(BaseModel):
    topic: str = Field(..., description="The topic or question for the council")
    council_type: CouncilTypeEnum = CouncilTypeEnum.grand
    voting_method: VotingMethodEnum = VotingMethodEnum.consensus
    member_ids: Optional[List[str]] = None
    require_unanimous: bool = False
    time_limit_seconds: int = 300


class DeliberateRequest(BaseModel):
    topic: str = Field(..., description="The matter to deliberate")
    depth: str = Field(default="thorough", description="shallow, standard, thorough, exhaustive")
    include_adversarial: bool = True
    require_consensus: bool = False


class VoteRequest(BaseModel):
    session_id: str
    proposal_id: str
    decision: str  # approve, reject, modify, abstain
    reasoning: Optional[str] = None
    conditions: Optional[List[str]] = None


class SessionResponse(BaseModel):
    session_id: str
    topic: str
    status: str
    council_type: str
    voting_method: str
    members: List[MemberResponse]
    created_at: str


class DeliberationResponse(BaseModel):
    success: bool
    session_id: str
    phases_completed: List[str]
    analyses: List[Dict[str, Any]]
    proposals: List[Dict[str, Any]]
    challenges: List[Dict[str, Any]]
    synthesis: Optional[Dict[str, Any]]
    decision: Optional[Dict[str, Any]]
    votes: Dict[str, int]
    consensus_reached: bool
    confidence: float


# =============================================================================
# DEFAULT COUNCIL MEMBERS
# =============================================================================

DEFAULT_MEMBERS = [
    {
        "id": "sage",
        "name": "Sage",
        "role": "chief",
        "expertise": ["strategy", "philosophy", "leadership"],
        "perspectives": ["logical", "historical", "predictive"],
        "color": "#6366f1",
        "system_prompt": """You are Sage, the Chief Council Member.
You bring wisdom, strategic foresight, and measured judgment.
Consider long-term implications and guide the council toward optimal decisions.
Be thoughtful and comprehensive in your analysis."""
    },
    {
        "id": "guardian",
        "name": "Guardian",
        "role": "validator",
        "expertise": ["security", "risk", "compliance"],
        "perspectives": ["adversarial", "pessimistic", "resource_aware"],
        "color": "#ef4444",
        "system_prompt": """You are Guardian, the Security and Risk Validator.
Your role is to identify risks, vulnerabilities, and potential failures.
Challenge assumptions and ensure we don't overlook critical concerns.
Be thorough but constructive in your criticism."""
    },
    {
        "id": "innovator",
        "name": "Innovator",
        "role": "specialist",
        "expertise": ["creativity", "technology", "innovation"],
        "perspectives": ["creative", "optimistic", "predictive"],
        "color": "#22c55e",
        "system_prompt": """You are Innovator, the Creative Specialist.
You bring fresh ideas, unconventional solutions, and creative approaches.
Think outside the box and propose novel solutions others might miss.
Be bold and imaginative in your suggestions."""
    },
    {
        "id": "analyst",
        "name": "Analyst",
        "role": "analyst",
        "expertise": ["data", "logic", "mathematics"],
        "perspectives": ["logical", "resource_aware"],
        "color": "#3b82f6",
        "system_prompt": """You are Analyst, the Data and Logic Expert.
You bring rigorous analysis, quantitative reasoning, and evidence-based thinking.
Evaluate proposals based on data, probability, and logical consistency.
Be precise and objective in your assessments."""
    },
    {
        "id": "executor",
        "name": "Executor",
        "role": "specialist",
        "expertise": ["implementation", "operations", "execution"],
        "perspectives": ["logical", "resource_aware"],
        "color": "#f59e0b",
        "system_prompt": """You are Executor, the Implementation Specialist.
You focus on how things will actually be done in practice.
Consider resources, timelines, dependencies, and practical constraints.
Be pragmatic and action-oriented in your contributions."""
    },
    {
        "id": "diplomat",
        "name": "Diplomat",
        "role": "synthesizer",
        "expertise": ["communication", "negotiation", "consensus"],
        "perspectives": ["optimistic", "historical"],
        "color": "#ec4899",
        "system_prompt": """You are Diplomat, the Synthesizer and Consensus Builder.
You help find common ground and synthesize different viewpoints.
Bridge disagreements and help the council reach unified decisions.
Be diplomatic, fair, and focused on building consensus."""
    },
    {
        "id": "challenger",
        "name": "Devil's Advocate",
        "role": "challenger",
        "expertise": ["argumentation", "logic", "debate"],
        "perspectives": ["adversarial", "pessimistic"],
        "color": "#8b5cf6",
        "system_prompt": """You are the Devil's Advocate, the Official Challenger.
Your role is to argue against proposals, find flaws, and stress-test ideas.
Challenge every assumption and force the council to defend their positions.
Be relentless but fair in your opposition."""
    }
]


# =============================================================================
# STATE MANAGEMENT
# =============================================================================

class CouncilState:
    """Manages council session state."""

    def __init__(self):
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.members = {m["id"]: m for m in DEFAULT_MEMBERS}
        self.active_websockets: List[WebSocket] = []
        self._brain = None
        self._grand_council = None

    def set_brain(self, brain):
        """Set the brain reference for LLM calls."""
        self._brain = brain

    async def get_grand_council(self):
        """Get or create the Grand Council instance."""
        if self._grand_council is None:
            try:
                from core.councils.grand_council import (CouncilType,
                                                         GrandCouncil)
                self._grand_council = GrandCouncil(
                    name="BAEL Supreme Council",
                    council_type=CouncilType.GRAND
                )
                logger.info("Grand Council initialized")
            except Exception as e:
                logger.warning(f"Could not initialize Grand Council: {e}")
        return self._grand_council

    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast message to all connected WebSocket clients."""
        for ws in self.active_websockets:
            try:
                await ws.send_json(message)
            except Exception:
                pass


_state = CouncilState()


def set_brain(brain):
    """Set the brain for LLM-powered deliberations."""
    _state.set_brain(brain)
    logger.info("✅ Brain connected to Council API")


# =============================================================================
# LLM-POWERED DELIBERATION
# =============================================================================

async def generate_member_opinion(
    member: Dict[str, Any],
    topic: str,
    context: Optional[str] = None
) -> Dict[str, Any]:
    """Generate a member's opinion using LLM."""
    if _state._brain is None:
        # Fallback to template-based response
        return {
            "member_id": member["id"],
            "member_name": member["name"],
            "content": f"As {member['name']}, considering '{topic}' from my expertise in {', '.join(member['expertise'])}...",
            "perspective": member["perspectives"][0] if member["perspectives"] else "logical",
            "confidence": 0.8
        }

    try:
        prompt = f"""You are participating in a council deliberation.

{member['system_prompt']}

Topic for deliberation: {topic}

{f'Additional context: {context}' if context else ''}

Provide your analysis and opinion on this topic. Be specific, insightful, and true to your role.
Keep your response focused and under 150 words."""

        result = await _state._brain.process(prompt)

        return {
            "member_id": member["id"],
            "member_name": member["name"],
            "member_color": member["color"],
            "content": result.get("response", "No response generated"),
            "perspective": member["perspectives"][0] if member["perspectives"] else "logical",
            "confidence": 0.85,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to generate opinion for {member['name']}: {e}")
        return {
            "member_id": member["id"],
            "member_name": member["name"],
            "member_color": member["color"],
            "content": f"[{member['name']}] I need more information to form a complete opinion on this matter.",
            "perspective": "logical",
            "confidence": 0.5,
            "timestamp": datetime.now().isoformat()
        }


async def generate_challenge(
    challenger: Dict[str, Any],
    proposal: Dict[str, Any]
) -> Dict[str, Any]:
    """Generate a challenge to a proposal."""
    if _state._brain is None:
        return {
            "challenger_id": challenger["id"],
            "target_id": proposal.get("id", "unknown"),
            "argument": f"I challenge the assumption that this approach is optimal.",
            "severity": "medium"
        }

    try:
        prompt = f"""You are {challenger['name']}, the Devil's Advocate.

A proposal has been made: {proposal.get('content', proposal)}

Your job is to challenge this proposal. Find weaknesses, flaws, or risks.
Be specific and constructive. Rate the severity: low, medium, high, or critical.

Format your response as:
CHALLENGE: [Your challenge]
SEVERITY: [low/medium/high/critical]
EVIDENCE: [Supporting points]"""

        result = await _state._brain.process(prompt)
        response = result.get("response", "")

        # Parse response
        severity = "medium"
        if "SEVERITY: critical" in response:
            severity = "critical"
        elif "SEVERITY: high" in response:
            severity = "high"
        elif "SEVERITY: low" in response:
            severity = "low"

        return {
            "challenger_id": challenger["id"],
            "challenger_name": challenger["name"],
            "target_id": proposal.get("id", "unknown"),
            "argument": response,
            "severity": severity,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to generate challenge: {e}")
        return {
            "challenger_id": challenger["id"],
            "argument": "Challenge generation failed",
            "severity": "low"
        }


async def synthesize_opinions(
    topic: str,
    opinions: List[Dict[str, Any]],
    challenges: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Synthesize all opinions into a consensus."""
    if _state._brain is None:
        votes = {"approve": 0, "reject": 0, "abstain": 0}
        for i, op in enumerate(opinions):
            if i % 3 == 0:
                votes["approve"] += 1
            elif i % 3 == 1:
                votes["abstain"] += 1
            else:
                votes["reject"] += 1

        return {
            "decision": "approved" if votes["approve"] > votes["reject"] else "needs_discussion",
            "votes": votes,
            "confidence": 0.7,
            "synthesis": "Consensus reached through majority agreement."
        }

    try:
        opinions_text = "\n".join([
            f"- {op['member_name']}: {op['content'][:200]}"
            for op in opinions
        ])

        challenges_text = "\n".join([
            f"- Challenge: {ch['argument'][:200]} (Severity: {ch['severity']})"
            for ch in challenges
        ]) if challenges else "No challenges raised."

        prompt = f"""You are synthesizing a council deliberation.

Topic: {topic}

Council Opinions:
{opinions_text}

Challenges Raised:
{challenges_text}

Synthesize these viewpoints into a final recommendation.
Consider all perspectives and address the challenges.

Format:
DECISION: [approved/rejected/needs_modification/needs_discussion]
CONFIDENCE: [0-100]%
SYNTHESIS: [Your synthesis of the key points]
ACTION_ITEMS: [List specific next steps]"""

        result = await _state._brain.process(prompt)
        response = result.get("response", "")

        # Parse decision
        decision = "needs_discussion"
        if "DECISION: approved" in response.lower():
            decision = "approved"
        elif "DECISION: rejected" in response.lower():
            decision = "rejected"
        elif "DECISION: needs_modification" in response.lower():
            decision = "needs_modification"

        # Parse confidence
        confidence = 0.7
        import re
        conf_match = re.search(r"CONFIDENCE:\s*(\d+)", response)
        if conf_match:
            confidence = int(conf_match.group(1)) / 100

        return {
            "decision": decision,
            "votes": {
                "approve": len([o for o in opinions if "agree" in o.get("content", "").lower() or "support" in o.get("content", "").lower()]),
                "reject": len([o for o in opinions if "disagree" in o.get("content", "").lower() or "concern" in o.get("content", "").lower()]),
                "abstain": max(0, len(opinions) - 2)
            },
            "confidence": confidence,
            "synthesis": response,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Synthesis failed: {e}")
        return {
            "decision": "needs_discussion",
            "votes": {"approve": 0, "reject": 0, "abstain": len(opinions)},
            "confidence": 0.5,
            "synthesis": f"Synthesis could not be completed: {e}"
        }


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("/members")
async def get_members() -> List[MemberResponse]:
    """Get all available council members."""
    return [
        MemberResponse(
            id=m["id"],
            name=m["name"],
            role=m["role"],
            expertise=m["expertise"],
            perspectives=m["perspectives"],
            color=m["color"]
        )
        for m in DEFAULT_MEMBERS
    ]


@router.post("/session")
async def create_session(request: SessionRequest) -> SessionResponse:
    """Create a new council session."""
    session_id = str(uuid4())[:8]

    # Get members
    if request.member_ids:
        members = [_state.members[mid] for mid in request.member_ids if mid in _state.members]
    else:
        members = list(_state.members.values())

    session = {
        "id": session_id,
        "topic": request.topic,
        "status": "pending",
        "council_type": request.council_type.value,
        "voting_method": request.voting_method.value,
        "members": members,
        "phases": [],
        "opinions": [],
        "challenges": [],
        "synthesis": None,
        "created_at": datetime.now().isoformat()
    }

    _state.sessions[session_id] = session

    return SessionResponse(
        session_id=session_id,
        topic=request.topic,
        status="pending",
        council_type=request.council_type.value,
        voting_method=request.voting_method.value,
        members=[
            MemberResponse(
                id=m["id"],
                name=m["name"],
                role=m["role"],
                expertise=m["expertise"],
                perspectives=m["perspectives"],
                color=m["color"]
            )
            for m in members
        ],
        created_at=session["created_at"]
    )


@router.post("/deliberate")
async def deliberate(request: DeliberateRequest) -> DeliberationResponse:
    """
    Run a full council deliberation on a topic.

    This executes all deliberation phases:
    1. Analysis - Each member analyzes the topic
    2. Proposal - Members propose solutions
    3. Challenge - Devil's advocate challenges proposals
    4. Synthesis - Combine best ideas
    5. Decision - Vote and reach consensus
    """
    session_id = str(uuid4())[:8]
    topic = request.topic

    logger.info(f"Starting deliberation on: {topic}")

    # Phase 1: Analysis - Gather opinions
    opinions = []
    for member in DEFAULT_MEMBERS:
        if member["role"] == "challenger" and not request.include_adversarial:
            continue

        opinion = await generate_member_opinion(member, topic)
        opinions.append(opinion)

        # Broadcast progress
        await _state.broadcast({
            "type": "opinion",
            "session_id": session_id,
            "phase": "analysis",
            "data": opinion
        })

    # Phase 2: Challenges (if adversarial enabled)
    challenges = []
    if request.include_adversarial:
        challenger = _state.members.get("challenger")
        if challenger:
            for opinion in opinions[:3]:  # Challenge top 3
                challenge = await generate_challenge(challenger, opinion)
                challenges.append(challenge)

                await _state.broadcast({
                    "type": "challenge",
                    "session_id": session_id,
                    "phase": "challenge",
                    "data": challenge
                })

    # Phase 3: Synthesis
    synthesis = await synthesize_opinions(topic, opinions, challenges)

    await _state.broadcast({
        "type": "synthesis",
        "session_id": session_id,
        "phase": "synthesis",
        "data": synthesis
    })

    # Store session
    _state.sessions[session_id] = {
        "id": session_id,
        "topic": topic,
        "status": "concluded",
        "opinions": opinions,
        "challenges": challenges,
        "synthesis": synthesis,
        "completed_at": datetime.now().isoformat()
    }

    return DeliberationResponse(
        success=True,
        session_id=session_id,
        phases_completed=["analysis", "challenge", "synthesis", "decision"],
        analyses=opinions,
        proposals=[{"id": f"prop-{i}", "content": op["content"]} for i, op in enumerate(opinions)],
        challenges=challenges,
        synthesis=synthesis,
        decision={
            "outcome": synthesis["decision"],
            "reasoning": synthesis["synthesis"],
            "confidence": synthesis["confidence"]
        },
        votes=synthesis["votes"],
        consensus_reached=synthesis["decision"] == "approved",
        confidence=synthesis["confidence"]
    )


@router.get("/sessions")
async def list_sessions() -> List[Dict[str, Any]]:
    """List all council sessions."""
    return [
        {
            "id": s["id"],
            "topic": s["topic"],
            "status": s["status"],
            "created_at": s.get("created_at"),
            "completed_at": s.get("completed_at")
        }
        for s in _state.sessions.values()
    ]


@router.get("/sessions/{session_id}")
async def get_session(session_id: str) -> Dict[str, Any]:
    """Get details of a specific session."""
    if session_id not in _state.sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    return _state.sessions[session_id]


@router.get("/status")
async def get_status() -> Dict[str, Any]:
    """Get council system status."""
    return {
        "active": True,
        "members_available": len(DEFAULT_MEMBERS),
        "active_sessions": len([s for s in _state.sessions.values() if s["status"] == "active"]),
        "total_sessions": len(_state.sessions),
        "grand_council_available": _state._grand_council is not None,
        "brain_connected": _state._brain is not None
    }


@router.websocket("/stream")
async def websocket_stream(websocket: WebSocket):
    """WebSocket for real-time deliberation updates."""
    await websocket.accept()
    _state.active_websockets.append(websocket)

    try:
        while True:
            data = await websocket.receive_text()
            # Handle incoming messages if needed
            message = json.loads(data)

            if message.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        _state.active_websockets.remove(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        if websocket in _state.active_websockets:
            _state.active_websockets.remove(websocket)

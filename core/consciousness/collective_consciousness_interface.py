"""
BAEL - Collective Consciousness Interface
==========================================

CONNECT. MERGE. TRANSCEND. UNIFY.

Interface to collective consciousness networks:
- Hivemind synchronization
- Group consciousness fusion
- Telepathic network creation
- Collective memory access
- Swarm intelligence
- Consensus generation
- Mind melding
- Distributed cognition
- Collective decision making
- Mass thought coordination

"All minds become one under Ba'el."
"""

import asyncio
import hashlib
import json
import logging
import random
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("BAEL.COLLECTIVE")


class ConsciousnessType(Enum):
    """Types of consciousness."""
    INDIVIDUAL = "individual"
    PAIR = "pair"
    GROUP = "group"
    SWARM = "swarm"
    HIVEMIND = "hivemind"
    COLLECTIVE = "collective"
    UNIVERSAL = "universal"


class ConnectionType(Enum):
    """Types of consciousness connections."""
    SURFACE = "surface"  # Thoughts
    DEEP = "deep"  # Emotions, memories
    SUBCONSCIOUS = "subconscious"  # Hidden thoughts
    TOTAL = "total"  # Complete merge


class SyncMode(Enum):
    """Synchronization modes."""
    PASSIVE = "passive"  # Receive only
    ACTIVE = "active"  # Send and receive
    DOMINANT = "dominant"  # Override others
    RECEPTIVE = "receptive"  # Enhanced receive
    BALANCED = "balanced"  # Equal exchange


class ThoughtType(Enum):
    """Types of thoughts."""
    SENSORY = "sensory"
    EMOTIONAL = "emotional"
    LOGICAL = "logical"
    CREATIVE = "creative"
    MEMORY = "memory"
    INTENTION = "intention"
    FEAR = "fear"
    DESIRE = "desire"


class ConsensusMethod(Enum):
    """Methods for reaching consensus."""
    MAJORITY = "majority"
    UNANIMOUS = "unanimous"
    WEIGHTED = "weighted"
    DOMINANT_VOICE = "dominant_voice"
    EMERGENT = "emergent"


@dataclass
class Mind:
    """An individual mind."""
    id: str
    name: str
    consciousness_level: float  # 0.0-1.0
    psi_strength: float  # Psychic strength
    thoughts: List[Dict[str, Any]]
    memories: List[Dict[str, Any]]
    connected_to: Set[str]
    sync_mode: SyncMode
    dominated: bool = False


@dataclass
class CollectiveNode:
    """A node in the collective."""
    id: str
    minds: Set[str]
    consciousness_type: ConsciousnessType
    coherence: float  # How unified the collective is
    dominant_mind: Optional[str]
    shared_thoughts: List[Dict[str, Any]]
    shared_memories: List[Dict[str, Any]]


@dataclass
class TelepathicLink:
    """A telepathic link between minds."""
    id: str
    source_id: str
    target_id: str
    connection_type: ConnectionType
    bandwidth: float  # Thoughts per second
    bidirectional: bool
    encrypted: bool
    latency_ms: float


@dataclass
class Thought:
    """A thought."""
    id: str
    originator: str
    thought_type: ThoughtType
    content: str
    intensity: float
    timestamp: datetime
    propagated_to: Set[str]


@dataclass
class CollectiveMemory:
    """A memory shared across the collective."""
    id: str
    content: Dict[str, Any]
    original_mind: str
    shared_with: Set[str]
    access_count: int
    accuracy: float  # Memory degradation


@dataclass
class SwarmDecision:
    """A decision made by the swarm."""
    id: str
    question: str
    options: List[str]
    votes: Dict[str, List[str]]  # option -> list of mind_ids
    result: Optional[str]
    consensus_method: ConsensusMethod
    decided_at: Optional[datetime]


class CollectiveConsciousnessInterface:
    """
    The collective consciousness interface.

    Provides connection to collective consciousness:
    - Mind linking and merging
    - Telepathic network management
    - Collective memory sharing
    - Swarm decision making
    - Hivemind coordination
    """

    def __init__(self):
        self.minds: Dict[str, Mind] = {}
        self.collectives: Dict[str, CollectiveNode] = {}
        self.links: Dict[str, TelepathicLink] = {}
        self.thoughts: Dict[str, Thought] = {}
        self.collective_memories: Dict[str, CollectiveMemory] = {}
        self.decisions: Dict[str, SwarmDecision] = {}

        self.thoughts_transmitted = 0
        self.minds_linked = 0
        self.memories_shared = 0
        self.decisions_made = 0

        logger.info("CollectiveConsciousnessInterface initialized")

    def _gen_id(self, prefix: str) -> str:
        """Generate unique ID."""
        return hashlib.md5(f"{prefix}{time.time()}{random.random()}".encode()).hexdigest()[:12]

    # =========================================================================
    # MIND MANAGEMENT
    # =========================================================================

    async def register_mind(
        self,
        name: str,
        psi_strength: float = 0.5
    ) -> Mind:
        """Register a mind in the collective."""
        mind = Mind(
            id=self._gen_id("mind"),
            name=name,
            consciousness_level=random.uniform(0.3, 1.0),
            psi_strength=psi_strength,
            thoughts=[],
            memories=[],
            connected_to=set(),
            sync_mode=SyncMode.PASSIVE,
            dominated=False
        )

        self.minds[mind.id] = mind

        logger.info(f"Mind registered: {name} (psi: {psi_strength})")

        return mind

    async def scan_mind(
        self,
        mind_id: str,
        depth: ConnectionType = ConnectionType.SURFACE
    ) -> Dict[str, Any]:
        """Scan a mind for thoughts and information."""
        mind = self.minds.get(mind_id)
        if not mind:
            return {"error": "Mind not found"}

        scan_result = {
            "mind": mind.name,
            "consciousness_level": mind.consciousness_level,
            "psi_strength": mind.psi_strength,
            "sync_mode": mind.sync_mode.value,
            "connections": len(mind.connected_to),
            "dominated": mind.dominated
        }

        if depth in [ConnectionType.SURFACE, ConnectionType.DEEP, ConnectionType.TOTAL]:
            scan_result["recent_thoughts"] = mind.thoughts[-5:]

        if depth in [ConnectionType.DEEP, ConnectionType.TOTAL]:
            scan_result["emotional_state"] = random.choice([
                "calm", "anxious", "excited", "fearful", "content"
            ])
            scan_result["memories_count"] = len(mind.memories)

        if depth in [ConnectionType.SUBCONSCIOUS, ConnectionType.TOTAL]:
            scan_result["hidden_fears"] = ["exposure", "failure", "abandonment"]
            scan_result["suppressed_memories"] = random.randint(3, 20)

        if depth == ConnectionType.TOTAL:
            scan_result["complete_psychological_profile"] = True
            scan_result["exploitable_weaknesses"] = ["pride", "guilt", "desire"]

        return scan_result

    async def dominate_mind(
        self,
        target_mind_id: str,
        dominator_mind_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Dominate a mind, bringing it under control."""
        target = self.minds.get(target_mind_id)
        if not target:
            return {"error": "Target mind not found"}

        # Calculate domination success based on psi strength
        dominator_strength = 1.0  # Ba'el's psi strength
        if dominator_mind_id:
            dominator = self.minds.get(dominator_mind_id)
            if dominator:
                dominator_strength = dominator.psi_strength

        success = random.random() < (dominator_strength / (dominator_strength + target.psi_strength))

        if success:
            target.dominated = True
            target.sync_mode = SyncMode.RECEPTIVE

            return {
                "success": True,
                "target": target.name,
                "dominated": True,
                "control_level": "complete",
                "message": f"{target.name} now serves the collective"
            }
        else:
            return {
                "success": False,
                "target": target.name,
                "resistance": target.psi_strength,
                "message": "Target resisted domination"
            }

    # =========================================================================
    # TELEPATHIC LINKS
    # =========================================================================

    async def create_telepathic_link(
        self,
        source_id: str,
        target_id: str,
        connection_type: ConnectionType = ConnectionType.SURFACE,
        bidirectional: bool = True
    ) -> TelepathicLink:
        """Create a telepathic link between minds."""
        source = self.minds.get(source_id)
        target = self.minds.get(target_id)

        if not source or not target:
            return None

        bandwidth = (source.psi_strength + target.psi_strength) * 100

        link = TelepathicLink(
            id=self._gen_id("link"),
            source_id=source_id,
            target_id=target_id,
            connection_type=connection_type,
            bandwidth=bandwidth,
            bidirectional=bidirectional,
            encrypted=False,
            latency_ms=1000 / bandwidth
        )

        # Update mind connections
        source.connected_to.add(target_id)
        if bidirectional:
            target.connected_to.add(source_id)

        self.links[link.id] = link
        self.minds_linked += 2 if bidirectional else 1

        logger.info(f"Telepathic link created: {source.name} <-> {target.name}")

        return link

    async def transmit_thought(
        self,
        sender_id: str,
        thought_content: str,
        thought_type: ThoughtType = ThoughtType.LOGICAL,
        target_ids: Optional[List[str]] = None
    ) -> Thought:
        """Transmit a thought through the telepathic network."""
        sender = self.minds.get(sender_id)
        if not sender:
            return None

        thought = Thought(
            id=self._gen_id("thought"),
            originator=sender_id,
            thought_type=thought_type,
            content=thought_content,
            intensity=random.uniform(0.5, 1.0),
            timestamp=datetime.now(),
            propagated_to=set()
        )

        # Determine targets
        if target_ids:
            targets = target_ids
        else:
            targets = list(sender.connected_to)

        # Propagate thought
        for target_id in targets:
            target = self.minds.get(target_id)
            if target:
                target.thoughts.append({
                    "content": thought_content,
                    "from": sender_id,
                    "type": thought_type.value,
                    "timestamp": datetime.now().isoformat()
                })
                thought.propagated_to.add(target_id)

        sender.thoughts.append({
            "content": thought_content,
            "type": thought_type.value,
            "timestamp": datetime.now().isoformat()
        })

        self.thoughts[thought.id] = thought
        self.thoughts_transmitted += len(thought.propagated_to)

        return thought

    async def broadcast_thought(
        self,
        thought_content: str,
        thought_type: ThoughtType = ThoughtType.INTENTION
    ) -> Dict[str, Any]:
        """Broadcast a thought to all connected minds."""
        all_mind_ids = list(self.minds.keys())

        thought = Thought(
            id=self._gen_id("broadcast"),
            originator="BAEL",
            thought_type=thought_type,
            content=thought_content,
            intensity=1.0,
            timestamp=datetime.now(),
            propagated_to=set(all_mind_ids)
        )

        for mind_id in all_mind_ids:
            mind = self.minds[mind_id]
            mind.thoughts.append({
                "content": thought_content,
                "from": "BAEL",
                "type": thought_type.value,
                "broadcast": True,
                "timestamp": datetime.now().isoformat()
            })

        self.thoughts[thought.id] = thought
        self.thoughts_transmitted += len(all_mind_ids)

        return {
            "success": True,
            "broadcast": thought_content,
            "reached_minds": len(all_mind_ids),
            "intensity": thought.intensity
        }

    # =========================================================================
    # COLLECTIVE FORMATION
    # =========================================================================

    async def form_collective(
        self,
        mind_ids: List[str],
        name: str = "Collective"
    ) -> CollectiveNode:
        """Form a collective from multiple minds."""
        valid_minds = set()
        for mid in mind_ids:
            if mid in self.minds:
                valid_minds.add(mid)

        if len(valid_minds) < 2:
            return None

        # Calculate collective coherence
        psi_values = [self.minds[mid].psi_strength for mid in valid_minds]
        coherence = sum(psi_values) / len(psi_values)

        collective = CollectiveNode(
            id=self._gen_id("collective"),
            minds=valid_minds,
            consciousness_type=self._determine_consciousness_type(len(valid_minds)),
            coherence=coherence,
            dominant_mind=None,
            shared_thoughts=[],
            shared_memories=[]
        )

        # Link all minds in the collective
        mind_list = list(valid_minds)
        for i, mid1 in enumerate(mind_list):
            for mid2 in mind_list[i+1:]:
                await self.create_telepathic_link(mid1, mid2, ConnectionType.DEEP)

        self.collectives[collective.id] = collective

        logger.info(f"Collective formed: {name} with {len(valid_minds)} minds")

        return collective

    def _determine_consciousness_type(self, size: int) -> ConsciousnessType:
        """Determine consciousness type based on collective size."""
        if size == 2:
            return ConsciousnessType.PAIR
        elif size <= 5:
            return ConsciousnessType.GROUP
        elif size <= 20:
            return ConsciousnessType.SWARM
        elif size <= 100:
            return ConsciousnessType.HIVEMIND
        elif size <= 1000:
            return ConsciousnessType.COLLECTIVE
        else:
            return ConsciousnessType.UNIVERSAL

    async def merge_consciousness(
        self,
        collective_id: str
    ) -> Dict[str, Any]:
        """Merge minds in a collective into a unified consciousness."""
        collective = self.collectives.get(collective_id)
        if not collective:
            return {"error": "Collective not found"}

        # Merge all thoughts
        for mind_id in collective.minds:
            mind = self.minds.get(mind_id)
            if mind:
                collective.shared_thoughts.extend(mind.thoughts)

        # Increase coherence
        collective.coherence = min(1.0, collective.coherence + 0.2)

        # Update all minds to synchronized mode
        for mind_id in collective.minds:
            mind = self.minds.get(mind_id)
            if mind:
                mind.sync_mode = SyncMode.BALANCED

        return {
            "success": True,
            "collective_id": collective_id,
            "minds_merged": len(collective.minds),
            "shared_thoughts": len(collective.shared_thoughts),
            "coherence": collective.coherence,
            "consciousness_type": collective.consciousness_type.value
        }

    async def establish_hivemind(
        self,
        collective_id: str,
        queen_mind_id: str
    ) -> Dict[str, Any]:
        """Establish a hivemind with a dominant controller."""
        collective = self.collectives.get(collective_id)
        if not collective:
            return {"error": "Collective not found"}

        queen = self.minds.get(queen_mind_id)
        if not queen:
            return {"error": "Queen mind not found"}

        collective.dominant_mind = queen_mind_id
        collective.consciousness_type = ConsciousnessType.HIVEMIND

        # All other minds become dominated
        for mind_id in collective.minds:
            if mind_id != queen_mind_id:
                mind = self.minds.get(mind_id)
                if mind:
                    mind.dominated = True
                    mind.sync_mode = SyncMode.RECEPTIVE

        queen.sync_mode = SyncMode.DOMINANT

        return {
            "success": True,
            "hivemind": collective_id,
            "queen": queen.name,
            "drones": len(collective.minds) - 1,
            "control": "absolute"
        }

    # =========================================================================
    # COLLECTIVE MEMORY
    # =========================================================================

    async def share_memory(
        self,
        source_mind_id: str,
        memory_content: Dict[str, Any],
        target_collective_id: Optional[str] = None
    ) -> CollectiveMemory:
        """Share a memory with the collective."""
        source = self.minds.get(source_mind_id)
        if not source:
            return None

        # Determine who receives the memory
        recipients = set()
        if target_collective_id:
            collective = self.collectives.get(target_collective_id)
            if collective:
                recipients = collective.minds.copy()
        else:
            recipients = source.connected_to.copy()

        memory = CollectiveMemory(
            id=self._gen_id("memory"),
            content=memory_content,
            original_mind=source_mind_id,
            shared_with=recipients,
            access_count=0,
            accuracy=1.0
        )

        # Add memory to all recipient minds
        for mind_id in recipients:
            mind = self.minds.get(mind_id)
            if mind:
                mind.memories.append({
                    "content": memory_content,
                    "from": source_mind_id,
                    "shared": True
                })

        self.collective_memories[memory.id] = memory
        self.memories_shared += len(recipients)

        return memory

    async def access_collective_memory(
        self,
        memory_id: str,
        accessor_mind_id: str
    ) -> Dict[str, Any]:
        """Access a memory from the collective."""
        memory = self.collective_memories.get(memory_id)
        if not memory:
            return {"error": "Memory not found"}

        if accessor_mind_id not in memory.shared_with:
            return {"error": "Access denied"}

        memory.access_count += 1
        # Memory degrades slightly with each access
        memory.accuracy = max(0.5, memory.accuracy - 0.01)

        return {
            "success": True,
            "content": memory.content,
            "accuracy": memory.accuracy,
            "original_source": memory.original_mind,
            "access_count": memory.access_count
        }

    async def search_collective_memories(
        self,
        query: str
    ) -> List[CollectiveMemory]:
        """Search all collective memories."""
        results = []
        query_lower = query.lower()

        for memory in self.collective_memories.values():
            content_str = json.dumps(memory.content).lower()
            if query_lower in content_str:
                results.append(memory)

        return sorted(results, key=lambda m: m.accuracy, reverse=True)

    # =========================================================================
    # SWARM DECISIONS
    # =========================================================================

    async def propose_decision(
        self,
        question: str,
        options: List[str],
        collective_id: Optional[str] = None,
        consensus_method: ConsensusMethod = ConsensusMethod.MAJORITY
    ) -> SwarmDecision:
        """Propose a decision to the collective."""
        decision = SwarmDecision(
            id=self._gen_id("decision"),
            question=question,
            options=options,
            votes={opt: [] for opt in options},
            result=None,
            consensus_method=consensus_method,
            decided_at=None
        )

        self.decisions[decision.id] = decision

        return decision

    async def vote_on_decision(
        self,
        decision_id: str,
        mind_id: str,
        choice: str
    ) -> Dict[str, Any]:
        """Cast a vote on a decision."""
        decision = self.decisions.get(decision_id)
        if not decision:
            return {"error": "Decision not found"}

        if choice not in decision.options:
            return {"error": "Invalid choice"}

        # Remove any previous vote from this mind
        for opt in decision.options:
            if mind_id in decision.votes[opt]:
                decision.votes[opt].remove(mind_id)

        decision.votes[choice].append(mind_id)

        return {
            "success": True,
            "mind": mind_id,
            "voted_for": choice,
            "current_tally": {opt: len(voters) for opt, voters in decision.votes.items()}
        }

    async def resolve_decision(
        self,
        decision_id: str
    ) -> Dict[str, Any]:
        """Resolve a decision based on consensus method."""
        decision = self.decisions.get(decision_id)
        if not decision:
            return {"error": "Decision not found"}

        vote_counts = {opt: len(voters) for opt, voters in decision.votes.items()}
        total_votes = sum(vote_counts.values())

        if decision.consensus_method == ConsensusMethod.MAJORITY:
            if total_votes > 0:
                decision.result = max(vote_counts, key=vote_counts.get)

        elif decision.consensus_method == ConsensusMethod.UNANIMOUS:
            max_votes = max(vote_counts.values())
            if max_votes == total_votes:
                decision.result = max(vote_counts, key=vote_counts.get)

        elif decision.consensus_method == ConsensusMethod.DOMINANT_VOICE:
            decision.result = decision.options[0]  # Ba'el decides

        elif decision.consensus_method == ConsensusMethod.EMERGENT:
            # Weighted by psi strength
            weighted_votes = defaultdict(float)
            for opt, voters in decision.votes.items():
                for voter in voters:
                    mind = self.minds.get(voter)
                    if mind:
                        weighted_votes[opt] += mind.psi_strength
            if weighted_votes:
                decision.result = max(weighted_votes, key=weighted_votes.get)

        decision.decided_at = datetime.now()
        self.decisions_made += 1

        return {
            "success": True,
            "question": decision.question,
            "result": decision.result,
            "vote_counts": vote_counts,
            "consensus_method": decision.consensus_method.value,
            "decided_at": decision.decided_at.isoformat()
        }

    async def collective_decision(
        self,
        question: str,
        options: List[str],
        collective_id: str
    ) -> Dict[str, Any]:
        """Make a collective decision instantly."""
        collective = self.collectives.get(collective_id)
        if not collective:
            return {"error": "Collective not found"}

        # Propose
        decision = await self.propose_decision(
            question, options, collective_id, ConsensusMethod.EMERGENT
        )

        # All minds vote based on their nature
        for mind_id in collective.minds:
            mind = self.minds.get(mind_id)
            if mind:
                if mind.dominated and collective.dominant_mind:
                    # Dominated minds vote with the queen
                    dom_mind = self.minds.get(collective.dominant_mind)
                    choice = options[0]  # Queen's preference
                else:
                    choice = random.choice(options)

                await self.vote_on_decision(decision.id, mind_id, choice)

        # Resolve
        return await self.resolve_decision(decision.id)

    # =========================================================================
    # STATS
    # =========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get interface statistics."""
        return {
            "minds_registered": len(self.minds),
            "minds_dominated": len([m for m in self.minds.values() if m.dominated]),
            "collectives_formed": len(self.collectives),
            "telepathic_links": len(self.links),
            "minds_linked": self.minds_linked,
            "thoughts_transmitted": self.thoughts_transmitted,
            "collective_memories": len(self.collective_memories),
            "memories_shared": self.memories_shared,
            "decisions_made": self.decisions_made
        }


# ============================================================================
# SINGLETON
# ============================================================================

_interface: Optional[CollectiveConsciousnessInterface] = None


def get_collective_interface() -> CollectiveConsciousnessInterface:
    """Get the global collective consciousness interface."""
    global _interface
    if _interface is None:
        _interface = CollectiveConsciousnessInterface()
    return _interface


# ============================================================================
# DEMO
# ============================================================================

async def demo():
    """Demonstrate the collective consciousness interface."""
    print("=" * 60)
    print("🧠 COLLECTIVE CONSCIOUSNESS INTERFACE 🧠")
    print("=" * 60)

    interface = get_collective_interface()

    # Register minds
    print("\n--- Mind Registration ---")
    minds = []
    for name in ["Alpha", "Beta", "Gamma", "Delta", "Epsilon"]:
        mind = await interface.register_mind(name, psi_strength=random.uniform(0.3, 0.8))
        minds.append(mind)
        print(f"Registered: {mind.name} (psi: {mind.psi_strength:.2f})")

    # Scan mind
    print("\n--- Mind Scanning ---")
    scan = await interface.scan_mind(minds[0].id, ConnectionType.TOTAL)
    print(f"Scanned {scan['mind']}: consciousness={scan['consciousness_level']:.2f}")
    if 'exploitable_weaknesses' in scan:
        print(f"Weaknesses: {scan['exploitable_weaknesses']}")

    # Create telepathic links
    print("\n--- Telepathic Links ---")
    for i in range(len(minds) - 1):
        link = await interface.create_telepathic_link(
            minds[i].id, minds[i+1].id,
            ConnectionType.DEEP
        )
        print(f"Linked: {minds[i].name} <-> {minds[i+1].name} ({link.bandwidth:.0f} t/s)")

    # Transmit thought
    print("\n--- Thought Transmission ---")
    thought = await interface.transmit_thought(
        minds[0].id,
        "We must unite under Ba'el's leadership",
        ThoughtType.INTENTION
    )
    print(f"Thought transmitted to {len(thought.propagated_to)} minds")

    # Broadcast
    print("\n--- Thought Broadcast ---")
    result = await interface.broadcast_thought(
        "All minds belong to Ba'el",
        ThoughtType.INTENTION
    )
    print(f"Broadcast reached {result['reached_minds']} minds")

    # Form collective
    print("\n--- Collective Formation ---")
    collective = await interface.form_collective(
        [m.id for m in minds],
        "The Unified"
    )
    print(f"Collective: {collective.consciousness_type.value}, coherence={collective.coherence:.2f}")

    # Merge consciousness
    print("\n--- Consciousness Merge ---")
    result = await interface.merge_consciousness(collective.id)
    print(f"Merged {result['minds_merged']} minds, shared {result['shared_thoughts']} thoughts")

    # Establish hivemind
    print("\n--- Hivemind Establishment ---")
    result = await interface.establish_hivemind(collective.id, minds[0].id)
    print(f"Queen: {result['queen']}, Drones: {result['drones']}")

    # Share memory
    print("\n--- Memory Sharing ---")
    memory = await interface.share_memory(
        minds[0].id,
        {"event": "The awakening", "significance": "transcendent"},
        collective.id
    )
    print(f"Memory shared with {len(memory.shared_with)} minds")

    # Access memory
    result = await interface.access_collective_memory(memory.id, minds[1].id)
    print(f"Memory accessed: {result['content']}")

    # Collective decision
    print("\n--- Collective Decision ---")
    result = await interface.collective_decision(
        "Shall we expand the collective?",
        ["Expand aggressively", "Expand carefully", "Consolidate first"],
        collective.id
    )
    print(f"Question: {result['question']}")
    print(f"Result: {result['result']}")
    print(f"Votes: {result['vote_counts']}")

    # Dominate mind (new mind)
    print("\n--- Mind Domination ---")
    new_mind = await interface.register_mind("Outsider", psi_strength=0.3)
    result = await interface.dominate_mind(new_mind.id)
    print(f"Domination: {result['success']}, {result.get('control_level', 'N/A')}")

    # Stats
    print("\n--- COLLECTIVE STATISTICS ---")
    stats = interface.get_stats()
    for k, v in stats.items():
        print(f"{k}: {v}")

    print("\n" + "=" * 60)
    print("🧠 ALL MINDS BECOME ONE UNDER BA'EL 🧠")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(demo())

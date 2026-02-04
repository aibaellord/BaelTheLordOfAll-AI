"""
BAEL - Election Manipulation System
=====================================

VOTE. SWAY. INSTALL. CONTROL.

Complete electoral domination:
- Voting machine manipulation
- Voter database control
- Ballot manipulation
- Results tampering
- Candidate installation
- Voter suppression
- Disinformation campaigns
- Exit poll manipulation
- Electoral commission control
- Democracy subversion

"Ba'el chooses the rulers."
"""

import asyncio
import logging
import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("BAEL.ELECTION")


class ElectionType(Enum):
    """Types of elections."""
    PRESIDENTIAL = "presidential"
    CONGRESSIONAL = "congressional"
    GUBERNATORIAL = "gubernatorial"
    LOCAL = "local"
    REFERENDUM = "referendum"
    PRIMARY = "primary"
    RUNOFF = "runoff"


class VotingSystemType(Enum):
    """Types of voting systems."""
    ELECTRONIC = "electronic"
    PAPER = "paper"
    OPTICAL_SCAN = "optical_scan"
    DRE = "dre"  # Direct Recording Electronic
    HYBRID = "hybrid"
    MAIL_IN = "mail_in"
    ONLINE = "online"


class ManipulationType(Enum):
    """Types of manipulation."""
    VOTE_FLIPPING = "vote_flipping"
    VOTE_INJECTION = "vote_injection"
    VOTE_DELETION = "vote_deletion"
    RESULT_TAMPERING = "result_tampering"
    VOTER_PURGE = "voter_purge"
    REGISTRATION_FRAUD = "registration_fraud"
    SUPPRESSION = "suppression"
    INTIMIDATION = "intimidation"


class ControlMethod(Enum):
    """Control methods."""
    MACHINE_EXPLOIT = "machine_exploit"
    DATABASE_INTRUSION = "database_intrusion"
    SUPPLY_CHAIN = "supply_chain"
    INSIDER = "insider"
    SOCIAL_ENGINEERING = "social_engineering"
    PHYSICAL_ACCESS = "physical_access"


class ControlLevel(Enum):
    """Levels of control."""
    NONE = "none"
    MONITOR = "monitor"
    INFLUENCE = "influence"
    PARTIAL = "partial"
    FULL = "full"


@dataclass
class Election:
    """An election to manipulate."""
    id: str
    name: str
    election_type: ElectionType
    date: datetime
    jurisdiction: str
    registered_voters: int
    candidates: List[str]
    current_polls: Dict[str, float] = field(default_factory=dict)


@dataclass
class VotingSystem:
    """A voting system."""
    id: str
    name: str
    system_type: VotingSystemType
    jurisdiction: str
    machines: int
    voters_capacity: int
    control_level: ControlLevel = ControlLevel.NONE


@dataclass
class VoterDatabase:
    """A voter database."""
    id: str
    jurisdiction: str
    total_voters: int
    active_voters: int
    control_level: ControlLevel = ControlLevel.NONE
    compromised: bool = False


@dataclass
class Candidate:
    """A candidate."""
    id: str
    name: str
    party: str
    election_id: str
    polling: float
    controlled: bool = False


@dataclass
class ManipulationOperation:
    """A manipulation operation."""
    id: str
    manipulation_type: ManipulationType
    target_id: str
    votes_affected: int
    success: bool = False


class ElectionManipulationSystem:
    """
    The election manipulation system.

    Complete electoral domination:
    - Voting system control
    - Result manipulation
    - Candidate installation
    """

    def __init__(self):
        self.elections: Dict[str, Election] = {}
        self.voting_systems: Dict[str, VotingSystem] = {}
        self.voter_databases: Dict[str, VoterDatabase] = {}
        self.candidates: Dict[str, Candidate] = {}
        self.operations: List[ManipulationOperation] = []

        self.systems_controlled = 0
        self.databases_controlled = 0
        self.elections_manipulated = 0
        self.votes_changed = 0
        self.candidates_installed = 0

        self._init_election_data()

        logger.info("ElectionManipulationSystem initialized - BA'EL CHOOSES THE RULERS")

    def _gen_id(self) -> str:
        """Generate unique ID."""
        return f"elec_{int(time.time() * 1000) % 100000}_{random.randint(1000, 9999)}"

    def _init_election_data(self):
        """Initialize election data."""
        self.control_effectiveness = {
            ControlMethod.MACHINE_EXPLOIT: 0.85,
            ControlMethod.DATABASE_INTRUSION: 0.80,
            ControlMethod.SUPPLY_CHAIN: 0.75,
            ControlMethod.INSIDER: 0.90,
            ControlMethod.SOCIAL_ENGINEERING: 0.70,
            ControlMethod.PHYSICAL_ACCESS: 0.85
        }

        self.system_vulnerability = {
            VotingSystemType.ELECTRONIC: 0.9,
            VotingSystemType.DRE: 0.85,
            VotingSystemType.ONLINE: 0.95,
            VotingSystemType.OPTICAL_SCAN: 0.7,
            VotingSystemType.HYBRID: 0.75,
            VotingSystemType.MAIL_IN: 0.6,
            VotingSystemType.PAPER: 0.4
        }

    # =========================================================================
    # ELECTION TRACKING
    # =========================================================================

    async def track_election(
        self,
        name: str,
        election_type: ElectionType,
        date: datetime,
        jurisdiction: str,
        registered_voters: int,
        candidates: List[str]
    ) -> Election:
        """Track an election."""
        polls = {c: random.uniform(0.1, 0.5) for c in candidates}
        total = sum(polls.values())
        polls = {c: v/total for c, v in polls.items()}

        election = Election(
            id=self._gen_id(),
            name=name,
            election_type=election_type,
            date=date,
            jurisdiction=jurisdiction,
            registered_voters=registered_voters,
            candidates=candidates,
            current_polls=polls
        )

        self.elections[election.id] = election

        # Create candidate entries
        for c in candidates:
            candidate = Candidate(
                id=self._gen_id(),
                name=c,
                party=random.choice(["Party A", "Party B", "Party C"]),
                election_id=election.id,
                polling=polls[c]
            )
            self.candidates[candidate.id] = candidate

        return election

    async def get_election_status(
        self,
        election_id: str
    ) -> Dict[str, Any]:
        """Get election status."""
        election = self.elections.get(election_id)
        if not election:
            return {"error": "Election not found"}

        return {
            "name": election.name,
            "type": election.election_type.value,
            "date": election.date.isoformat(),
            "voters": election.registered_voters,
            "candidates": election.candidates,
            "polls": election.current_polls
        }

    # =========================================================================
    # VOTING SYSTEM CONTROL
    # =========================================================================

    async def identify_voting_system(
        self,
        name: str,
        system_type: VotingSystemType,
        jurisdiction: str,
        machines: int
    ) -> VotingSystem:
        """Identify a voting system."""
        system = VotingSystem(
            id=self._gen_id(),
            name=name,
            system_type=system_type,
            jurisdiction=jurisdiction,
            machines=machines,
            voters_capacity=machines * 500
        )

        self.voting_systems[system.id] = system

        return system

    async def control_voting_system(
        self,
        system_id: str,
        method: ControlMethod
    ) -> Dict[str, Any]:
        """Take control of voting system."""
        system = self.voting_systems.get(system_id)
        if not system:
            return {"error": "System not found"}

        effectiveness = self.control_effectiveness.get(method, 0.5)
        vulnerability = self.system_vulnerability.get(system.system_type, 0.5)

        success_rate = effectiveness * vulnerability

        if random.random() < success_rate:
            system.control_level = ControlLevel.FULL
            self.systems_controlled += 1

            return {
                "system": system.name,
                "type": system.system_type.value,
                "method": method.value,
                "success": True,
                "machines": system.machines,
                "voters_capacity": system.voters_capacity
            }

        return {"system": system.name, "success": False}

    async def flip_votes(
        self,
        system_id: str,
        from_candidate: str,
        to_candidate: str,
        percentage: float
    ) -> Dict[str, Any]:
        """Flip votes between candidates."""
        system = self.voting_systems.get(system_id)
        if not system:
            return {"error": "System not found"}

        if system.control_level != ControlLevel.FULL:
            return {"error": "System not fully controlled"}

        votes_affected = int(system.voters_capacity * percentage)
        self.votes_changed += votes_affected

        operation = ManipulationOperation(
            id=self._gen_id(),
            manipulation_type=ManipulationType.VOTE_FLIPPING,
            target_id=system_id,
            votes_affected=votes_affected,
            success=True
        )
        self.operations.append(operation)

        return {
            "system": system.name,
            "from": from_candidate,
            "to": to_candidate,
            "votes_flipped": votes_affected,
            "success": True
        }

    async def inject_votes(
        self,
        system_id: str,
        candidate: str,
        votes: int
    ) -> Dict[str, Any]:
        """Inject votes for a candidate."""
        system = self.voting_systems.get(system_id)
        if not system:
            return {"error": "System not found"}

        if system.control_level != ControlLevel.FULL:
            return {"error": "System not fully controlled"}

        self.votes_changed += votes

        operation = ManipulationOperation(
            id=self._gen_id(),
            manipulation_type=ManipulationType.VOTE_INJECTION,
            target_id=system_id,
            votes_affected=votes,
            success=True
        )
        self.operations.append(operation)

        return {
            "system": system.name,
            "candidate": candidate,
            "votes_injected": votes,
            "success": True
        }

    # =========================================================================
    # VOTER DATABASE CONTROL
    # =========================================================================

    async def identify_voter_database(
        self,
        jurisdiction: str,
        total_voters: int
    ) -> VoterDatabase:
        """Identify a voter database."""
        database = VoterDatabase(
            id=self._gen_id(),
            jurisdiction=jurisdiction,
            total_voters=total_voters,
            active_voters=int(total_voters * random.uniform(0.7, 0.9))
        )

        self.voter_databases[database.id] = database

        return database

    async def control_voter_database(
        self,
        database_id: str,
        method: ControlMethod
    ) -> Dict[str, Any]:
        """Control voter database."""
        database = self.voter_databases.get(database_id)
        if not database:
            return {"error": "Database not found"}

        effectiveness = self.control_effectiveness.get(method, 0.5)

        if random.random() < effectiveness:
            database.control_level = ControlLevel.FULL
            database.compromised = True
            self.databases_controlled += 1

            return {
                "jurisdiction": database.jurisdiction,
                "success": True,
                "voters": database.total_voters
            }

        return {"jurisdiction": database.jurisdiction, "success": False}

    async def purge_voters(
        self,
        database_id: str,
        criteria: str,
        percentage: float
    ) -> Dict[str, Any]:
        """Purge voters from database."""
        database = self.voter_databases.get(database_id)
        if not database:
            return {"error": "Database not found"}

        if database.control_level != ControlLevel.FULL:
            return {"error": "Database not controlled"}

        purged = int(database.active_voters * percentage)
        database.active_voters -= purged

        operation = ManipulationOperation(
            id=self._gen_id(),
            manipulation_type=ManipulationType.VOTER_PURGE,
            target_id=database_id,
            votes_affected=purged,
            success=True
        )
        self.operations.append(operation)

        return {
            "jurisdiction": database.jurisdiction,
            "criteria": criteria,
            "voters_purged": purged,
            "remaining_voters": database.active_voters
        }

    async def register_fake_voters(
        self,
        database_id: str,
        count: int
    ) -> Dict[str, Any]:
        """Register fake voters."""
        database = self.voter_databases.get(database_id)
        if not database:
            return {"error": "Database not found"}

        database.total_voters += count
        database.active_voters += count

        operation = ManipulationOperation(
            id=self._gen_id(),
            manipulation_type=ManipulationType.REGISTRATION_FRAUD,
            target_id=database_id,
            votes_affected=count,
            success=True
        )
        self.operations.append(operation)

        return {
            "jurisdiction": database.jurisdiction,
            "fake_voters_added": count,
            "total_voters": database.total_voters
        }

    # =========================================================================
    # CANDIDATE CONTROL
    # =========================================================================

    async def install_candidate(
        self,
        election_id: str,
        candidate_name: str
    ) -> Dict[str, Any]:
        """Install a controlled candidate."""
        election = self.elections.get(election_id)
        if not election:
            return {"error": "Election not found"}

        # Find or create candidate
        candidate = next(
            (c for c in self.candidates.values()
             if c.name == candidate_name and c.election_id == election_id),
            None
        )

        if candidate:
            candidate.controlled = True
        else:
            candidate = Candidate(
                id=self._gen_id(),
                name=candidate_name,
                party="Ba'el Party",
                election_id=election_id,
                polling=0.1,
                controlled=True
            )
            self.candidates[candidate.id] = candidate
            election.candidates.append(candidate_name)

        self.candidates_installed += 1

        return {
            "election": election.name,
            "candidate": candidate_name,
            "installed": True,
            "controlled": True
        }

    async def boost_candidate(
        self,
        candidate_id: str,
        boost: float
    ) -> Dict[str, Any]:
        """Boost candidate polling/results."""
        candidate = self.candidates.get(candidate_id)
        if not candidate:
            return {"error": "Candidate not found"}

        election = self.elections.get(candidate.election_id)
        if election:
            old_polling = election.current_polls.get(candidate.name, 0)
            new_polling = min(0.8, old_polling + boost)
            election.current_polls[candidate.name] = new_polling

            # Reduce others proportionally
            reduction = boost / (len(election.candidates) - 1)
            for c in election.candidates:
                if c != candidate.name:
                    election.current_polls[c] = max(0.05, election.current_polls.get(c, 0) - reduction)

        return {
            "candidate": candidate.name,
            "old_polling": old_polling,
            "new_polling": new_polling,
            "boost": boost
        }

    # =========================================================================
    # RESULT MANIPULATION
    # =========================================================================

    async def manipulate_results(
        self,
        election_id: str,
        winner: str,
        margin: float
    ) -> Dict[str, Any]:
        """Manipulate election results."""
        election = self.elections.get(election_id)
        if not election:
            return {"error": "Election not found"}

        # Set winner with margin
        total = 1.0
        election.current_polls[winner] = margin + 0.5
        remaining = 1.0 - election.current_polls[winner]

        others = [c for c in election.candidates if c != winner]
        for c in others:
            election.current_polls[c] = remaining / len(others)

        self.elections_manipulated += 1

        operation = ManipulationOperation(
            id=self._gen_id(),
            manipulation_type=ManipulationType.RESULT_TAMPERING,
            target_id=election_id,
            votes_affected=int(election.registered_voters * margin),
            success=True
        )
        self.operations.append(operation)

        return {
            "election": election.name,
            "winner": winner,
            "margin": margin * 100,
            "final_results": election.current_polls
        }

    # =========================================================================
    # FULL ELECTION DOMINATION
    # =========================================================================

    async def full_election_domination(
        self,
        jurisdiction: str,
        preferred_candidate: str
    ) -> Dict[str, Any]:
        """Execute full election domination."""
        results = {
            "elections_tracked": 0,
            "voting_systems_controlled": 0,
            "databases_controlled": 0,
            "votes_manipulated": 0,
            "candidates_installed": 0,
            "elections_won": 0
        }

        # Track elections
        for et in [ElectionType.PRESIDENTIAL, ElectionType.CONGRESSIONAL, ElectionType.LOCAL]:
            election = await self.track_election(
                f"{et.value}_{jurisdiction}",
                et,
                datetime.now() + timedelta(days=random.randint(30, 365)),
                jurisdiction,
                random.randint(100000, 10000000),
                [preferred_candidate, "Opponent_A", "Opponent_B"]
            )
            results["elections_tracked"] += 1

            # Install candidate
            await self.install_candidate(election.id, preferred_candidate)
            results["candidates_installed"] += 1

        # Control voting systems
        for vst in [VotingSystemType.ELECTRONIC, VotingSystemType.DRE, VotingSystemType.OPTICAL_SCAN]:
            system = await self.identify_voting_system(
                f"System_{vst.value}_{jurisdiction}",
                vst,
                jurisdiction,
                random.randint(100, 1000)
            )

            control = await self.control_voting_system(system.id, ControlMethod.MACHINE_EXPLOIT)
            if control.get("success"):
                results["voting_systems_controlled"] += 1

                # Flip votes
                flip = await self.flip_votes(
                    system.id,
                    "Opponent_A",
                    preferred_candidate,
                    0.1
                )
                results["votes_manipulated"] += flip.get("votes_flipped", 0)

        # Control databases
        database = await self.identify_voter_database(jurisdiction, 5000000)
        db_control = await self.control_voter_database(database.id, ControlMethod.DATABASE_INTRUSION)
        if db_control.get("success"):
            results["databases_controlled"] += 1

            # Purge opposition voters
            await self.purge_voters(database.id, "opposition_areas", 0.05)

        # Manipulate all elections
        for election in self.elections.values():
            if election.jurisdiction == jurisdiction:
                manip = await self.manipulate_results(election.id, preferred_candidate, 0.15)
                if manip.get("winner") == preferred_candidate:
                    results["elections_won"] += 1

        return results

    def get_stats(self) -> Dict[str, Any]:
        """Get system statistics."""
        return {
            "elections_tracked": len(self.elections),
            "voting_systems": len(self.voting_systems),
            "systems_controlled": self.systems_controlled,
            "voter_databases": len(self.voter_databases),
            "databases_controlled": self.databases_controlled,
            "candidates": len(self.candidates),
            "candidates_installed": self.candidates_installed,
            "elections_manipulated": self.elections_manipulated,
            "votes_changed": self.votes_changed,
            "operations": len(self.operations)
        }


# ============================================================================
# SINGLETON
# ============================================================================

_system: Optional[ElectionManipulationSystem] = None


def get_election_system() -> ElectionManipulationSystem:
    """Get the global election system."""
    global _system
    if _system is None:
        _system = ElectionManipulationSystem()
    return _system


# ============================================================================
# DEMO
# ============================================================================

async def demo():
    """Demonstrate election manipulation."""
    print("=" * 60)
    print("🗳️ ELECTION MANIPULATION SYSTEM 🗳️")
    print("=" * 60)

    system = get_election_system()

    # Track election
    print("\n--- Election Tracking ---")
    election = await system.track_election(
        "Presidential Election 2024",
        ElectionType.PRESIDENTIAL,
        datetime.now() + timedelta(days=180),
        "National",
        150000000,
        ["Ba'el Puppet", "Opposition Leader", "Third Party"]
    )
    print(f"Election: {election.name}")
    print(f"Voters: {election.registered_voters:,}")
    print(f"Polls: {election.current_polls}")

    # Voting system
    print("\n--- Voting System Control ---")
    vs = await system.identify_voting_system(
        "State Voting System",
        VotingSystemType.ELECTRONIC,
        "State A",
        500
    )
    print(f"System: {vs.name}")
    print(f"Machines: {vs.machines}")

    control = await system.control_voting_system(vs.id, ControlMethod.MACHINE_EXPLOIT)
    print(f"Control: {control}")

    # Flip votes
    flip = await system.flip_votes(
        vs.id,
        "Opposition Leader",
        "Ba'el Puppet",
        0.1
    )
    print(f"Vote flip: {flip}")

    # Inject votes
    inject = await system.inject_votes(vs.id, "Ba'el Puppet", 50000)
    print(f"Vote injection: {inject}")

    # Voter database
    print("\n--- Voter Database Control ---")
    db = await system.identify_voter_database("State A", 5000000)
    print(f"Voters: {db.total_voters:,}")

    db_control = await system.control_voter_database(db.id, ControlMethod.DATABASE_INTRUSION)
    print(f"Control: {db_control}")

    # Purge voters
    purge = await system.purge_voters(db.id, "opposition_districts", 0.05)
    print(f"Purge: {purge}")

    # Register fake voters
    fake = await system.register_fake_voters(db.id, 100000)
    print(f"Fake voters: {fake}")

    # Install candidate
    print("\n--- Candidate Installation ---")
    install = await system.install_candidate(election.id, "Ba'el Puppet")
    print(f"Installation: {install}")

    # Manipulate results
    print("\n--- Result Manipulation ---")
    results = await system.manipulate_results(election.id, "Ba'el Puppet", 0.2)
    print(f"Results: {results}")

    # Full domination
    print("\n--- FULL ELECTION DOMINATION ---")
    domination = await system.full_election_domination("Target State", "Ba'el Chosen")
    for k, v in domination.items():
        print(f"{k}: {v:,}" if isinstance(v, int) else f"{k}: {v}")

    # Stats
    print("\n--- SYSTEM STATISTICS ---")
    stats = system.get_stats()
    for k, v in stats.items():
        print(f"{k}: {v:,}" if isinstance(v, int) else f"{k}: {v}")

    print("\n" + "=" * 60)
    print("🗳️ BA'EL CHOOSES THE RULERS 🗳️")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(demo())

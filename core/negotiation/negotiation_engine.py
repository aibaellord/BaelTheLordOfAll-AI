#!/usr/bin/env python3
"""
BAEL - Negotiation Engine
Advanced multi-agent negotiation system.

Features:
- Negotiation protocols
- Offer/counter-offer
- Utility functions
- Nash bargaining
- Auction mechanisms
- Contract formation
- Deadline handling
- Multi-issue negotiation
"""

import asyncio
import copy
import hashlib
import math
import random
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import (Any, Callable, Dict, Generic, List, Optional, Set, Tuple,
                    Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class NegotiationStatus(Enum):
    """Negotiation status."""
    PENDING = "pending"
    ACTIVE = "active"
    PAUSED = "paused"
    AGREED = "agreed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class OfferStatus(Enum):
    """Offer status."""
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    COUNTERED = "countered"
    WITHDRAWN = "withdrawn"
    EXPIRED = "expired"


class ProtocolType(Enum):
    """Negotiation protocol types."""
    ALTERNATING_OFFERS = "alternating_offers"
    MONOTONIC_CONCESSION = "monotonic_concession"
    SINGLE_TEXT = "single_text"
    AUCTION = "auction"
    VOTING = "voting"


class AuctionType(Enum):
    """Auction types."""
    ENGLISH = "english"  # Ascending bid
    DUTCH = "dutch"  # Descending bid
    SEALED_FIRST = "sealed_first"  # First-price sealed
    SEALED_SECOND = "sealed_second"  # Second-price (Vickrey)


class ConcessionStrategy(Enum):
    """Concession strategies."""
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    BOULWARE = "boulware"
    CONCEDER = "conceder"
    HARDLINER = "hardliner"
    TIT_FOR_TAT = "tit_for_tat"


class IssueType(Enum):
    """Issue types."""
    CONTINUOUS = "continuous"
    DISCRETE = "discrete"
    BINARY = "binary"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class Issue:
    """Negotiation issue."""
    issue_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    issue_type: IssueType = IssueType.CONTINUOUS
    min_value: float = 0.0
    max_value: float = 1.0
    discrete_values: List[Any] = field(default_factory=list)
    weight: float = 1.0


@dataclass
class Preference:
    """Agent preference for issue."""
    issue_id: str = ""
    reservation_value: float = 0.0  # Walk-away point
    aspiration_value: float = 1.0  # Ideal value
    weight: float = 1.0


@dataclass
class Offer:
    """Negotiation offer."""
    offer_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    negotiation_id: str = ""
    sender: str = ""
    values: Dict[str, float] = field(default_factory=dict)
    status: OfferStatus = OfferStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CounterOffer:
    """Counter offer."""
    original_offer_id: str = ""
    counter_offer: Offer = field(default_factory=Offer)
    reason: str = ""


@dataclass
class Bid:
    """Auction bid."""
    bid_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    auction_id: str = ""
    bidder: str = ""
    amount: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class Contract:
    """Negotiated contract."""
    contract_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    negotiation_id: str = ""
    parties: List[str] = field(default_factory=list)
    terms: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    signed_at: Optional[datetime] = None
    signatures: Dict[str, str] = field(default_factory=dict)


@dataclass
class NegotiationSession:
    """Negotiation session."""
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    parties: List[str] = field(default_factory=list)
    issues: List[Issue] = field(default_factory=list)
    protocol: ProtocolType = ProtocolType.ALTERNATING_OFFERS
    status: NegotiationStatus = NegotiationStatus.PENDING
    offers: List[Offer] = field(default_factory=list)
    deadline: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    current_turn: int = 0
    agreement: Optional[Dict[str, float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Auction:
    """Auction session."""
    auction_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    auction_type: AuctionType = AuctionType.ENGLISH
    item: str = ""
    seller: str = ""
    bidders: List[str] = field(default_factory=list)
    reserve_price: float = 0.0
    current_price: float = 0.0
    bids: List[Bid] = field(default_factory=list)
    winning_bid: Optional[Bid] = None
    status: NegotiationStatus = NegotiationStatus.PENDING
    deadline: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class NegotiationStats:
    """Negotiation statistics."""
    total_negotiations: int = 0
    successful_negotiations: int = 0
    failed_negotiations: int = 0
    total_offers: int = 0
    avg_rounds: float = 0.0
    avg_duration: float = 0.0


# =============================================================================
# UTILITY FUNCTION
# =============================================================================

class UtilityFunction(ABC):
    """Abstract utility function."""

    @abstractmethod
    def evaluate(
        self,
        offer: Dict[str, float],
        preferences: Dict[str, Preference]
    ) -> float:
        """Evaluate offer utility."""
        pass


class LinearUtility(UtilityFunction):
    """Linear additive utility function."""

    def evaluate(
        self,
        offer: Dict[str, float],
        preferences: Dict[str, Preference]
    ) -> float:
        """Evaluate offer using linear utility."""
        utility = 0.0
        total_weight = sum(p.weight for p in preferences.values())

        for issue_id, value in offer.items():
            if issue_id in preferences:
                pref = preferences[issue_id]

                # Normalize value to [0, 1] based on preference
                if pref.aspiration_value != pref.reservation_value:
                    normalized = (value - pref.reservation_value) / (
                        pref.aspiration_value - pref.reservation_value
                    )
                else:
                    normalized = 1.0 if value >= pref.aspiration_value else 0.0

                # Clamp to [0, 1]
                normalized = max(0.0, min(1.0, normalized))

                # Weighted sum
                utility += (pref.weight / total_weight) * normalized

        return utility


class CobbDouglasUtility(UtilityFunction):
    """Cobb-Douglas utility function."""

    def evaluate(
        self,
        offer: Dict[str, float],
        preferences: Dict[str, Preference]
    ) -> float:
        """Evaluate offer using Cobb-Douglas utility."""
        utility = 1.0
        total_weight = sum(p.weight for p in preferences.values())

        for issue_id, value in offer.items():
            if issue_id in preferences:
                pref = preferences[issue_id]

                # Normalize value
                if pref.aspiration_value != pref.reservation_value:
                    normalized = (value - pref.reservation_value) / (
                        pref.aspiration_value - pref.reservation_value
                    )
                else:
                    normalized = 1.0 if value >= pref.aspiration_value else 0.0

                normalized = max(0.01, min(1.0, normalized))  # Avoid zero

                # Weighted product
                exponent = pref.weight / total_weight
                utility *= normalized ** exponent

        return utility


# =============================================================================
# CONCESSION CALCULATOR
# =============================================================================

class ConcessionCalculator:
    """Calculate concession amounts."""

    def calculate(
        self,
        strategy: ConcessionStrategy,
        current_utility: float,
        reservation_utility: float,
        time_remaining: float,
        opponent_concession: float = 0.0
    ) -> float:
        """Calculate target utility after concession."""
        if time_remaining <= 0:
            return reservation_utility

        if strategy == ConcessionStrategy.LINEAR:
            return self._linear(current_utility, reservation_utility, time_remaining)

        elif strategy == ConcessionStrategy.EXPONENTIAL:
            return self._exponential(current_utility, reservation_utility, time_remaining)

        elif strategy == ConcessionStrategy.BOULWARE:
            return self._boulware(current_utility, reservation_utility, time_remaining)

        elif strategy == ConcessionStrategy.CONCEDER:
            return self._conceder(current_utility, reservation_utility, time_remaining)

        elif strategy == ConcessionStrategy.HARDLINER:
            return self._hardliner(current_utility, reservation_utility, time_remaining)

        elif strategy == ConcessionStrategy.TIT_FOR_TAT:
            return self._tit_for_tat(
                current_utility, reservation_utility, opponent_concession
            )

        return current_utility

    def _linear(
        self,
        current: float,
        reservation: float,
        time_remaining: float
    ) -> float:
        """Linear concession."""
        concession_rate = (current - reservation) * (1 - time_remaining)
        return current - concession_rate

    def _exponential(
        self,
        current: float,
        reservation: float,
        time_remaining: float
    ) -> float:
        """Exponential concession."""
        beta = 0.5  # Concession parameter
        factor = 1 - (1 - time_remaining) ** (1 / beta)
        return reservation + (current - reservation) * factor

    def _boulware(
        self,
        current: float,
        reservation: float,
        time_remaining: float
    ) -> float:
        """Boulware strategy - concede slowly at first, faster near deadline."""
        beta = 0.1  # Very slow concession
        factor = time_remaining ** (1 / beta)
        return reservation + (current - reservation) * factor

    def _conceder(
        self,
        current: float,
        reservation: float,
        time_remaining: float
    ) -> float:
        """Conceder strategy - concede quickly at first."""
        beta = 2.0  # Fast concession
        factor = time_remaining ** (1 / beta)
        return reservation + (current - reservation) * factor

    def _hardliner(
        self,
        current: float,
        reservation: float,
        time_remaining: float
    ) -> float:
        """Hardliner - minimal concession."""
        return current - 0.01 * (current - reservation)

    def _tit_for_tat(
        self,
        current: float,
        reservation: float,
        opponent_concession: float
    ) -> float:
        """Tit-for-tat - match opponent's concession."""
        return max(reservation, current - opponent_concession)


# =============================================================================
# OFFER GENERATOR
# =============================================================================

class OfferGenerator:
    """Generate offers based on utility targets."""

    def __init__(self, utility_func: UtilityFunction):
        self._utility_func = utility_func

    def generate(
        self,
        target_utility: float,
        issues: List[Issue],
        preferences: Dict[str, Preference],
        iterations: int = 100
    ) -> Dict[str, float]:
        """Generate offer with target utility."""
        best_offer = {}
        best_diff = float('inf')

        for _ in range(iterations):
            # Random offer
            offer = {}
            for issue in issues:
                if issue.issue_type == IssueType.CONTINUOUS:
                    offer[issue.issue_id] = random.uniform(
                        issue.min_value, issue.max_value
                    )
                elif issue.issue_type == IssueType.DISCRETE:
                    offer[issue.issue_id] = random.choice(issue.discrete_values)
                else:  # Binary
                    offer[issue.issue_id] = random.choice([0.0, 1.0])

            # Evaluate
            utility = self._utility_func.evaluate(offer, preferences)
            diff = abs(utility - target_utility)

            if diff < best_diff:
                best_diff = diff
                best_offer = offer

        return best_offer

    def generate_pareto_optimal(
        self,
        issues: List[Issue],
        preferences_a: Dict[str, Preference],
        preferences_b: Dict[str, Preference],
        samples: int = 1000
    ) -> List[Tuple[Dict[str, float], float, float]]:
        """Generate Pareto-optimal offers."""
        offers = []

        for _ in range(samples):
            offer = {}
            for issue in issues:
                if issue.issue_type == IssueType.CONTINUOUS:
                    offer[issue.issue_id] = random.uniform(
                        issue.min_value, issue.max_value
                    )
                else:
                    offer[issue.issue_id] = random.choice([0.0, 1.0])

            utility_a = self._utility_func.evaluate(offer, preferences_a)
            utility_b = self._utility_func.evaluate(offer, preferences_b)

            offers.append((offer, utility_a, utility_b))

        # Filter Pareto-optimal
        pareto = []
        for o1, u1a, u1b in offers:
            is_dominated = False
            for o2, u2a, u2b in offers:
                if u2a >= u1a and u2b >= u1b and (u2a > u1a or u2b > u1b):
                    is_dominated = True
                    break
            if not is_dominated:
                pareto.append((o1, u1a, u1b))

        return pareto


# =============================================================================
# NASH BARGAINING
# =============================================================================

class NashBargaining:
    """Nash bargaining solution."""

    def __init__(self, utility_func: UtilityFunction):
        self._utility_func = utility_func

    def solve(
        self,
        issues: List[Issue],
        preferences_a: Dict[str, Preference],
        preferences_b: Dict[str, Preference],
        disagreement_a: float = 0.0,
        disagreement_b: float = 0.0,
        samples: int = 1000
    ) -> Tuple[Dict[str, float], float, float]:
        """Find Nash bargaining solution."""
        best_offer = {}
        best_product = 0.0
        best_utilities = (0.0, 0.0)

        for _ in range(samples):
            offer = {}
            for issue in issues:
                if issue.issue_type == IssueType.CONTINUOUS:
                    offer[issue.issue_id] = random.uniform(
                        issue.min_value, issue.max_value
                    )
                else:
                    offer[issue.issue_id] = random.choice([0.0, 1.0])

            utility_a = self._utility_func.evaluate(offer, preferences_a)
            utility_b = self._utility_func.evaluate(offer, preferences_b)

            # Nash product: (u_a - d_a) * (u_b - d_b)
            if utility_a >= disagreement_a and utility_b >= disagreement_b:
                nash_product = (utility_a - disagreement_a) * (utility_b - disagreement_b)

                if nash_product > best_product:
                    best_product = nash_product
                    best_offer = offer
                    best_utilities = (utility_a, utility_b)

        return best_offer, best_utilities[0], best_utilities[1]


# =============================================================================
# AUCTION MANAGER
# =============================================================================

class AuctionManager:
    """Manage auction mechanisms."""

    def __init__(self):
        self._auctions: Dict[str, Auction] = {}

    def create(
        self,
        item: str,
        seller: str,
        auction_type: AuctionType = AuctionType.ENGLISH,
        reserve_price: float = 0.0,
        deadline: Optional[datetime] = None
    ) -> Auction:
        """Create auction."""
        auction = Auction(
            auction_type=auction_type,
            item=item,
            seller=seller,
            reserve_price=reserve_price,
            current_price=reserve_price,
            deadline=deadline
        )

        self._auctions[auction.auction_id] = auction
        return auction

    def join(self, auction_id: str, bidder: str) -> bool:
        """Join auction as bidder."""
        if auction_id not in self._auctions:
            return False

        auction = self._auctions[auction_id]
        if bidder not in auction.bidders:
            auction.bidders.append(bidder)
        return True

    def bid(
        self,
        auction_id: str,
        bidder: str,
        amount: float
    ) -> Tuple[bool, str]:
        """Place bid."""
        if auction_id not in self._auctions:
            return False, "Auction not found"

        auction = self._auctions[auction_id]

        # Check status
        if auction.status != NegotiationStatus.ACTIVE:
            return False, "Auction not active"

        # Check bidder
        if bidder not in auction.bidders:
            return False, "Not registered as bidder"

        # Check deadline
        if auction.deadline and datetime.now() > auction.deadline:
            return False, "Auction expired"

        # Validate bid based on auction type
        if auction.auction_type == AuctionType.ENGLISH:
            if amount <= auction.current_price:
                return False, "Bid must exceed current price"

        elif auction.auction_type == AuctionType.DUTCH:
            if amount > auction.current_price:
                return False, "Bid must not exceed current price"

        # Create bid
        bid = Bid(
            auction_id=auction_id,
            bidder=bidder,
            amount=amount
        )

        auction.bids.append(bid)
        auction.current_price = amount

        # Check for immediate win (Dutch, sealed)
        if auction.auction_type in [AuctionType.DUTCH, AuctionType.SEALED_FIRST]:
            auction.winning_bid = bid
            auction.status = NegotiationStatus.AGREED

        return True, "Bid accepted"

    def close(self, auction_id: str) -> Optional[Bid]:
        """Close auction and determine winner."""
        if auction_id not in self._auctions:
            return None

        auction = self._auctions[auction_id]

        if not auction.bids:
            auction.status = NegotiationStatus.FAILED
            return None

        if auction.auction_type == AuctionType.ENGLISH:
            # Highest bid wins
            winner = max(auction.bids, key=lambda b: b.amount)

            if winner.amount >= auction.reserve_price:
                auction.winning_bid = winner
                auction.status = NegotiationStatus.AGREED
            else:
                auction.status = NegotiationStatus.FAILED

        elif auction.auction_type == AuctionType.SEALED_SECOND:
            # Highest bidder wins, pays second-highest price
            sorted_bids = sorted(auction.bids, key=lambda b: b.amount, reverse=True)

            if len(sorted_bids) >= 1:
                winner = Bid(
                    auction_id=auction_id,
                    bidder=sorted_bids[0].bidder,
                    amount=sorted_bids[1].amount if len(sorted_bids) >= 2 else sorted_bids[0].amount
                )
                auction.winning_bid = winner
                auction.status = NegotiationStatus.AGREED

        return auction.winning_bid

    def get(self, auction_id: str) -> Optional[Auction]:
        """Get auction."""
        return self._auctions.get(auction_id)


# =============================================================================
# CONTRACT MANAGER
# =============================================================================

class ContractManager:
    """Manage negotiated contracts."""

    def __init__(self):
        self._contracts: Dict[str, Contract] = {}

    def create(
        self,
        negotiation_id: str,
        parties: List[str],
        terms: Dict[str, Any]
    ) -> Contract:
        """Create contract."""
        contract = Contract(
            negotiation_id=negotiation_id,
            parties=parties,
            terms=terms
        )

        self._contracts[contract.contract_id] = contract
        return contract

    def sign(
        self,
        contract_id: str,
        party: str,
        signature: str
    ) -> bool:
        """Sign contract."""
        if contract_id not in self._contracts:
            return False

        contract = self._contracts[contract_id]

        if party not in contract.parties:
            return False

        contract.signatures[party] = signature

        # Check if all parties signed
        if len(contract.signatures) == len(contract.parties):
            contract.signed_at = datetime.now()

        return True

    def is_complete(self, contract_id: str) -> bool:
        """Check if contract is fully signed."""
        if contract_id not in self._contracts:
            return False

        contract = self._contracts[contract_id]
        return len(contract.signatures) == len(contract.parties)

    def get(self, contract_id: str) -> Optional[Contract]:
        """Get contract."""
        return self._contracts.get(contract_id)


# =============================================================================
# NEGOTIATION ENGINE
# =============================================================================

class NegotiationEngine:
    """
    Negotiation Engine for BAEL.

    Advanced multi-agent negotiation system.
    """

    def __init__(
        self,
        agent_id: str = "bael_negotiator",
        utility_func: Optional[UtilityFunction] = None
    ):
        self._agent_id = agent_id
        self._utility_func = utility_func or LinearUtility()
        self._concession_calc = ConcessionCalculator()
        self._offer_generator = OfferGenerator(self._utility_func)
        self._nash = NashBargaining(self._utility_func)
        self._auction_manager = AuctionManager()
        self._contract_manager = ContractManager()

        self._sessions: Dict[str, NegotiationSession] = {}
        self._preferences: Dict[str, Dict[str, Preference]] = {}
        self._strategy: ConcessionStrategy = ConcessionStrategy.LINEAR
        self._stats = NegotiationStats()

    # -------------------------------------------------------------------------
    # SESSION MANAGEMENT
    # -------------------------------------------------------------------------

    def create_session(
        self,
        parties: List[str],
        issues: List[Issue],
        protocol: ProtocolType = ProtocolType.ALTERNATING_OFFERS,
        deadline: Optional[datetime] = None
    ) -> NegotiationSession:
        """Create negotiation session."""
        session = NegotiationSession(
            parties=parties,
            issues=issues,
            protocol=protocol,
            deadline=deadline
        )

        self._sessions[session.session_id] = session
        self._stats.total_negotiations += 1

        return session

    def start_session(self, session_id: str) -> bool:
        """Start negotiation session."""
        if session_id not in self._sessions:
            return False

        session = self._sessions[session_id]
        session.status = NegotiationStatus.ACTIVE
        session.started_at = datetime.now()

        return True

    def get_session(self, session_id: str) -> Optional[NegotiationSession]:
        """Get session."""
        return self._sessions.get(session_id)

    def set_preferences(
        self,
        session_id: str,
        preferences: Dict[str, Preference]
    ) -> None:
        """Set agent preferences for session."""
        self._preferences[session_id] = preferences

    def set_strategy(self, strategy: ConcessionStrategy) -> None:
        """Set concession strategy."""
        self._strategy = strategy

    # -------------------------------------------------------------------------
    # OFFER HANDLING
    # -------------------------------------------------------------------------

    def make_offer(
        self,
        session_id: str,
        values: Dict[str, float],
        ttl: Optional[float] = None
    ) -> Optional[Offer]:
        """Make offer in session."""
        if session_id not in self._sessions:
            return None

        session = self._sessions[session_id]

        if session.status != NegotiationStatus.ACTIVE:
            return None

        offer = Offer(
            negotiation_id=session_id,
            sender=self._agent_id,
            values=values,
            expires_at=datetime.now() + timedelta(seconds=ttl) if ttl else None
        )

        session.offers.append(offer)
        session.current_turn += 1
        self._stats.total_offers += 1

        return offer

    def receive_offer(
        self,
        session_id: str,
        offer: Offer
    ) -> Tuple[str, Optional[Offer]]:
        """Receive and evaluate offer."""
        if session_id not in self._sessions:
            return "rejected", None

        session = self._sessions[session_id]
        preferences = self._preferences.get(session_id, {})

        # Evaluate utility
        utility = self._utility_func.evaluate(offer.values, preferences)

        # Get reservation utility
        reservation_utility = min(
            p.reservation_value for p in preferences.values()
        ) if preferences else 0.3

        # Accept if above aspiration
        aspiration_utility = sum(
            p.aspiration_value * p.weight for p in preferences.values()
        ) / sum(p.weight for p in preferences.values()) if preferences else 0.8

        if utility >= aspiration_utility:
            offer.status = OfferStatus.ACCEPTED
            session.status = NegotiationStatus.AGREED
            session.agreement = offer.values
            session.ended_at = datetime.now()
            self._stats.successful_negotiations += 1
            return "accepted", None

        # Reject if below reservation
        if utility < reservation_utility:
            offer.status = OfferStatus.REJECTED
            return "rejected", None

        # Calculate time remaining
        time_remaining = 1.0
        if session.deadline:
            total = (session.deadline - session.started_at).total_seconds()
            elapsed = (datetime.now() - session.started_at).total_seconds()
            time_remaining = max(0, (total - elapsed) / total)

        # Calculate counter offer
        target_utility = self._concession_calc.calculate(
            self._strategy,
            aspiration_utility,
            reservation_utility,
            time_remaining
        )

        counter_values = self._offer_generator.generate(
            target_utility,
            session.issues,
            preferences
        )

        counter = self.make_offer(session_id, counter_values)
        offer.status = OfferStatus.COUNTERED

        return "countered", counter

    def accept_offer(self, session_id: str, offer_id: str) -> bool:
        """Accept offer."""
        if session_id not in self._sessions:
            return False

        session = self._sessions[session_id]

        for offer in session.offers:
            if offer.offer_id == offer_id:
                offer.status = OfferStatus.ACCEPTED
                session.status = NegotiationStatus.AGREED
                session.agreement = offer.values
                session.ended_at = datetime.now()
                self._stats.successful_negotiations += 1
                return True

        return False

    def reject_offer(self, session_id: str, offer_id: str) -> bool:
        """Reject offer."""
        if session_id not in self._sessions:
            return False

        session = self._sessions[session_id]

        for offer in session.offers:
            if offer.offer_id == offer_id:
                offer.status = OfferStatus.REJECTED
                return True

        return False

    # -------------------------------------------------------------------------
    # UTILITY EVALUATION
    # -------------------------------------------------------------------------

    def evaluate_offer(
        self,
        session_id: str,
        offer: Offer
    ) -> float:
        """Evaluate offer utility."""
        preferences = self._preferences.get(session_id, {})
        return self._utility_func.evaluate(offer.values, preferences)

    def generate_optimal_offer(
        self,
        session_id: str,
        target_utility: float
    ) -> Dict[str, float]:
        """Generate offer with target utility."""
        if session_id not in self._sessions:
            return {}

        session = self._sessions[session_id]
        preferences = self._preferences.get(session_id, {})

        return self._offer_generator.generate(
            target_utility,
            session.issues,
            preferences
        )

    # -------------------------------------------------------------------------
    # NASH BARGAINING
    # -------------------------------------------------------------------------

    def find_nash_solution(
        self,
        session_id: str,
        opponent_preferences: Dict[str, Preference]
    ) -> Tuple[Dict[str, float], float, float]:
        """Find Nash bargaining solution."""
        if session_id not in self._sessions:
            return {}, 0.0, 0.0

        session = self._sessions[session_id]
        preferences = self._preferences.get(session_id, {})

        return self._nash.solve(
            session.issues,
            preferences,
            opponent_preferences
        )

    # -------------------------------------------------------------------------
    # AUCTION
    # -------------------------------------------------------------------------

    def create_auction(
        self,
        item: str,
        auction_type: AuctionType = AuctionType.ENGLISH,
        reserve_price: float = 0.0,
        deadline: Optional[datetime] = None
    ) -> Auction:
        """Create auction."""
        return self._auction_manager.create(
            item,
            self._agent_id,
            auction_type,
            reserve_price,
            deadline
        )

    def join_auction(self, auction_id: str) -> bool:
        """Join auction as bidder."""
        return self._auction_manager.join(auction_id, self._agent_id)

    def place_bid(
        self,
        auction_id: str,
        amount: float
    ) -> Tuple[bool, str]:
        """Place bid."""
        return self._auction_manager.bid(auction_id, self._agent_id, amount)

    def close_auction(self, auction_id: str) -> Optional[Bid]:
        """Close auction."""
        return self._auction_manager.close(auction_id)

    def get_auction(self, auction_id: str) -> Optional[Auction]:
        """Get auction."""
        return self._auction_manager.get(auction_id)

    # -------------------------------------------------------------------------
    # CONTRACTS
    # -------------------------------------------------------------------------

    def create_contract(
        self,
        session_id: str
    ) -> Optional[Contract]:
        """Create contract from agreement."""
        if session_id not in self._sessions:
            return None

        session = self._sessions[session_id]

        if session.status != NegotiationStatus.AGREED:
            return None

        return self._contract_manager.create(
            session_id,
            session.parties,
            session.agreement or {}
        )

    def sign_contract(
        self,
        contract_id: str,
        signature: str
    ) -> bool:
        """Sign contract."""
        return self._contract_manager.sign(contract_id, self._agent_id, signature)

    def is_contract_complete(self, contract_id: str) -> bool:
        """Check if contract is complete."""
        return self._contract_manager.is_complete(contract_id)

    def get_contract(self, contract_id: str) -> Optional[Contract]:
        """Get contract."""
        return self._contract_manager.get(contract_id)

    # -------------------------------------------------------------------------
    # DEADLINE HANDLING
    # -------------------------------------------------------------------------

    def check_deadline(self, session_id: str) -> bool:
        """Check if deadline passed."""
        if session_id not in self._sessions:
            return True

        session = self._sessions[session_id]

        if session.deadline and datetime.now() > session.deadline:
            if session.status == NegotiationStatus.ACTIVE:
                session.status = NegotiationStatus.EXPIRED
                session.ended_at = datetime.now()
                self._stats.failed_negotiations += 1
            return True

        return False

    def get_time_remaining(self, session_id: str) -> float:
        """Get time remaining in seconds."""
        if session_id not in self._sessions:
            return 0.0

        session = self._sessions[session_id]

        if not session.deadline:
            return float('inf')

        remaining = (session.deadline - datetime.now()).total_seconds()
        return max(0.0, remaining)

    # -------------------------------------------------------------------------
    # STATISTICS
    # -------------------------------------------------------------------------

    def get_stats(self) -> NegotiationStats:
        """Get negotiation statistics."""
        return self._stats


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Negotiation Engine."""
    print("=" * 70)
    print("BAEL - NEGOTIATION ENGINE DEMO")
    print("Advanced Multi-Agent Negotiation")
    print("=" * 70)
    print()

    engine = NegotiationEngine(agent_id="agent_a")

    # 1. Create Issues
    print("1. CREATE NEGOTIATION ISSUES:")
    print("-" * 40)

    issues = [
        Issue(issue_id="price", name="Price", min_value=0.0, max_value=100.0),
        Issue(issue_id="quality", name="Quality", min_value=0.0, max_value=1.0),
        Issue(issue_id="delivery", name="Delivery Days", min_value=1.0, max_value=30.0)
    ]

    for issue in issues:
        print(f"   - {issue.name}: [{issue.min_value}, {issue.max_value}]")
    print()

    # 2. Create Session
    print("2. CREATE SESSION:")
    print("-" * 40)

    session = engine.create_session(
        parties=["agent_a", "agent_b"],
        issues=issues,
        protocol=ProtocolType.ALTERNATING_OFFERS,
        deadline=datetime.now() + timedelta(minutes=5)
    )

    print(f"   Session ID: {session.session_id[:8]}...")
    print(f"   Protocol: {session.protocol.value}")
    print(f"   Parties: {session.parties}")
    print()

    # 3. Set Preferences
    print("3. SET PREFERENCES:")
    print("-" * 40)

    preferences = {
        "price": Preference(issue_id="price", reservation_value=20, aspiration_value=80, weight=0.5),
        "quality": Preference(issue_id="quality", reservation_value=0.6, aspiration_value=1.0, weight=0.3),
        "delivery": Preference(issue_id="delivery", reservation_value=14, aspiration_value=3, weight=0.2)
    }

    engine.set_preferences(session.session_id, preferences)

    for name, pref in preferences.items():
        print(f"   - {name}: reserve={pref.reservation_value}, aspire={pref.aspiration_value}")
    print()

    # 4. Start Session
    print("4. START SESSION:")
    print("-" * 40)

    engine.start_session(session.session_id)
    print(f"   Status: {session.status.value}")
    print()

    # 5. Make Offer
    print("5. MAKE OFFER:")
    print("-" * 40)

    offer = engine.make_offer(
        session.session_id,
        {"price": 70.0, "quality": 0.9, "delivery": 5.0}
    )

    print(f"   Offer ID: {offer.offer_id[:8]}...")
    print(f"   Values: {offer.values}")

    utility = engine.evaluate_offer(session.session_id, offer)
    print(f"   Utility: {utility:.3f}")
    print()

    # 6. Generate Optimal Offer
    print("6. GENERATE OPTIMAL OFFER:")
    print("-" * 40)

    optimal = engine.generate_optimal_offer(session.session_id, 0.7)
    print(f"   Target utility: 0.7")
    print(f"   Generated: {optimal}")
    print()

    # 7. Concession Strategies
    print("7. CONCESSION STRATEGIES:")
    print("-" * 40)

    calc = ConcessionCalculator()

    for strategy in ConcessionStrategy:
        target = calc.calculate(strategy, 1.0, 0.3, 0.5)
        print(f"   {strategy.name}: target utility = {target:.3f}")
    print()

    # 8. Nash Bargaining
    print("8. NASH BARGAINING:")
    print("-" * 40)

    opponent_prefs = {
        "price": Preference(issue_id="price", reservation_value=70, aspiration_value=30, weight=0.5),
        "quality": Preference(issue_id="quality", reservation_value=0.4, aspiration_value=0.7, weight=0.3),
        "delivery": Preference(issue_id="delivery", reservation_value=7, aspiration_value=20, weight=0.2)
    }

    nash_offer, utility_a, utility_b = engine.find_nash_solution(
        session.session_id,
        opponent_prefs
    )

    print(f"   Nash solution: {nash_offer}")
    print(f"   Agent A utility: {utility_a:.3f}")
    print(f"   Agent B utility: {utility_b:.3f}")
    print()

    # 9. Create Auction
    print("9. CREATE AUCTION:")
    print("-" * 40)

    auction = engine.create_auction(
        item="rare_item",
        auction_type=AuctionType.ENGLISH,
        reserve_price=50.0
    )

    print(f"   Auction ID: {auction.auction_id[:8]}...")
    print(f"   Type: {auction.auction_type.value}")
    print(f"   Reserve: {auction.reserve_price}")
    print()

    # 10. Auction Bidding
    print("10. AUCTION BIDDING:")
    print("-" * 40)

    auction.status = NegotiationStatus.ACTIVE
    auction.bidders = ["agent_a", "bidder_1", "bidder_2"]

    success, msg = engine.place_bid(auction.auction_id, 55.0)
    print(f"   Bid 55.0: {msg}")

    success, msg = engine.place_bid(auction.auction_id, 60.0)
    print(f"   Bid 60.0: {msg}")

    winning = engine.close_auction(auction.auction_id)
    print(f"   Winner: {winning.bidder if winning else 'None'}")
    print(f"   Amount: {winning.amount if winning else 0}")
    print()

    # 11. Accept Offer & Create Contract
    print("11. ACCEPT OFFER & CREATE CONTRACT:")
    print("-" * 40)

    # Simulate agreement
    engine.accept_offer(session.session_id, offer.offer_id)

    contract = engine.create_contract(session.session_id)
    if contract:
        print(f"   Contract ID: {contract.contract_id[:8]}...")
        print(f"   Parties: {contract.parties}")
        print(f"   Terms: {contract.terms}")
    print()

    # 12. Sign Contract
    print("12. SIGN CONTRACT:")
    print("-" * 40)

    if contract:
        engine.sign_contract(contract.contract_id, "signature_hash_abc123")
        print(f"   Signed by: {engine._agent_id}")
        print(f"   Complete: {engine.is_contract_complete(contract.contract_id)}")
    print()

    # 13. Time Remaining
    print("13. TIME REMAINING:")
    print("-" * 40)

    remaining = engine.get_time_remaining(session.session_id)
    print(f"   Remaining: {remaining:.1f} seconds")
    print()

    # 14. Different Utility Functions
    print("14. UTILITY FUNCTIONS:")
    print("-" * 40)

    linear = LinearUtility()
    cobb = CobbDouglasUtility()

    test_offer = {"price": 50.0, "quality": 0.8, "delivery": 10.0}

    print(f"   Offer: {test_offer}")
    print(f"   Linear utility: {linear.evaluate(test_offer, preferences):.3f}")
    print(f"   Cobb-Douglas: {cobb.evaluate(test_offer, preferences):.3f}")
    print()

    # 15. Statistics
    print("15. STATISTICS:")
    print("-" * 40)

    stats = engine.get_stats()
    print(f"   Total negotiations: {stats.total_negotiations}")
    print(f"   Successful: {stats.successful_negotiations}")
    print(f"   Failed: {stats.failed_negotiations}")
    print(f"   Total offers: {stats.total_offers}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Negotiation Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())

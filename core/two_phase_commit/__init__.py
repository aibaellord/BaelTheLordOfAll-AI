"""
BAEL Two-Phase Commit Engine Implementation
============================================

Distributed transaction coordination.

"Ba'el unifies the disparate into one truth." — Ba'el
"""

import asyncio
import logging
import threading
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import uuid

logger = logging.getLogger("BAEL.TwoPhaseCommit")


# ============================================================================
# ENUMS
# ============================================================================

class TransactionState(Enum):
    """Transaction states."""
    INITIATED = "initiated"
    PREPARING = "preparing"
    PREPARED = "prepared"
    COMMITTING = "committing"
    COMMITTED = "committed"
    ABORTING = "aborting"
    ABORTED = "aborted"
    UNKNOWN = "unknown"


class ParticipantVote(Enum):
    """Participant votes."""
    COMMIT = "commit"
    ABORT = "abort"
    UNKNOWN = "unknown"


class ParticipantState(Enum):
    """Participant states."""
    WORKING = "working"
    PREPARED = "prepared"
    COMMITTED = "committed"
    ABORTED = "aborted"
    FAILED = "failed"


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class Participant:
    """A transaction participant."""
    id: str
    name: str

    # State
    state: ParticipantState = ParticipantState.WORKING
    vote: ParticipantVote = ParticipantVote.UNKNOWN

    # Handlers
    prepare_handler: Optional[Callable] = None
    commit_handler: Optional[Callable] = None
    rollback_handler: Optional[Callable] = None

    # Timing
    prepared_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Transaction:
    """A distributed transaction."""
    id: str
    coordinator_id: str

    # Participants
    participants: Dict[str, Participant] = field(default_factory=dict)

    # State
    state: TransactionState = TransactionState.INITIATED

    # Data
    data: Dict[str, Any] = field(default_factory=dict)

    # Timing
    created_at: datetime = field(default_factory=datetime.now)
    timeout_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Results
    commit_count: int = 0
    abort_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'state': self.state.value,
            'participants': len(self.participants),
            'created_at': self.created_at.isoformat()
        }


@dataclass
class TwoPhaseCommitConfig:
    """2PC configuration."""
    prepare_timeout_seconds: float = 30.0
    commit_timeout_seconds: float = 30.0
    transaction_timeout_seconds: float = 120.0
    retry_count: int = 3
    retry_delay_seconds: float = 1.0


# ============================================================================
# TWO-PHASE COMMIT COORDINATOR
# ============================================================================

class TwoPhaseCommitCoordinator:
    """
    Two-phase commit coordinator.

    Features:
    - Prepare and commit phases
    - Automatic rollback
    - Timeout handling
    - Recovery support

    "Ba'el ensures all move as one or none at all." — Ba'el
    """

    def __init__(
        self,
        coordinator_id: Optional[str] = None,
        config: Optional[TwoPhaseCommitConfig] = None
    ):
        """Initialize coordinator."""
        self.coordinator_id = coordinator_id or str(uuid.uuid4())
        self.config = config or TwoPhaseCommitConfig()

        # Transactions
        self._transactions: Dict[str, Transaction] = {}

        # Thread safety
        self._lock = threading.RLock()

        # Stats
        self._stats = {
            'transactions_started': 0,
            'transactions_committed': 0,
            'transactions_aborted': 0
        }

        logger.info(f"2PC Coordinator initialized: {self.coordinator_id}")

    # ========================================================================
    # TRANSACTION MANAGEMENT
    # ========================================================================

    def begin_transaction(
        self,
        transaction_id: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None
    ) -> Transaction:
        """
        Begin a new distributed transaction.

        Args:
            transaction_id: Optional transaction ID
            data: Transaction data

        Returns:
            Transaction
        """
        transaction = Transaction(
            id=transaction_id or str(uuid.uuid4()),
            coordinator_id=self.coordinator_id,
            data=data or {},
            timeout_at=datetime.now() + timedelta(
                seconds=self.config.transaction_timeout_seconds
            )
        )

        with self._lock:
            self._transactions[transaction.id] = transaction
            self._stats['transactions_started'] += 1

        logger.info(f"Transaction started: {transaction.id}")

        return transaction

    def add_participant(
        self,
        transaction_id: str,
        participant_id: str,
        name: str,
        prepare_handler: Callable,
        commit_handler: Callable,
        rollback_handler: Callable
    ) -> bool:
        """Add a participant to transaction."""
        transaction = self._transactions.get(transaction_id)
        if not transaction:
            return False

        if transaction.state != TransactionState.INITIATED:
            return False

        participant = Participant(
            id=participant_id,
            name=name,
            prepare_handler=prepare_handler,
            commit_handler=commit_handler,
            rollback_handler=rollback_handler
        )

        transaction.participants[participant_id] = participant

        logger.debug(f"Participant added: {name} to {transaction_id}")

        return True

    # ========================================================================
    # PHASE 1: PREPARE
    # ========================================================================

    async def prepare(self, transaction_id: str) -> bool:
        """
        Phase 1: Prepare all participants.

        Returns:
            True if all participants voted COMMIT
        """
        transaction = self._transactions.get(transaction_id)
        if not transaction:
            raise ValueError(f"Transaction not found: {transaction_id}")

        transaction.state = TransactionState.PREPARING

        # Ask all participants to prepare
        prepare_tasks = []
        for participant in transaction.participants.values():
            task = asyncio.create_task(
                self._prepare_participant(transaction, participant)
            )
            prepare_tasks.append(task)

        # Wait for all with timeout
        try:
            await asyncio.wait_for(
                asyncio.gather(*prepare_tasks),
                timeout=self.config.prepare_timeout_seconds
            )
        except asyncio.TimeoutError:
            logger.error(f"Prepare timeout: {transaction_id}")
            return False

        # Check votes
        all_commit = all(
            p.vote == ParticipantVote.COMMIT
            for p in transaction.participants.values()
        )

        if all_commit:
            transaction.state = TransactionState.PREPARED
            logger.info(f"Transaction prepared: {transaction_id}")
        else:
            logger.warning(f"Prepare failed: {transaction_id}")

        return all_commit

    async def _prepare_participant(
        self,
        transaction: Transaction,
        participant: Participant
    ) -> ParticipantVote:
        """Prepare a single participant."""
        try:
            if participant.prepare_handler:
                result = await self._call_handler(
                    participant.prepare_handler,
                    transaction.id,
                    transaction.data
                )

                if result:
                    participant.vote = ParticipantVote.COMMIT
                    participant.state = ParticipantState.PREPARED
                    participant.prepared_at = datetime.now()
                else:
                    participant.vote = ParticipantVote.ABORT
                    participant.state = ParticipantState.ABORTED
            else:
                # No handler, assume OK
                participant.vote = ParticipantVote.COMMIT
                participant.state = ParticipantState.PREPARED

        except Exception as e:
            logger.error(f"Prepare failed for {participant.name}: {e}")
            participant.vote = ParticipantVote.ABORT
            participant.state = ParticipantState.FAILED

        return participant.vote

    # ========================================================================
    # PHASE 2: COMMIT
    # ========================================================================

    async def commit(self, transaction_id: str) -> bool:
        """
        Phase 2: Commit all participants.

        Returns:
            True if all participants committed
        """
        transaction = self._transactions.get(transaction_id)
        if not transaction:
            raise ValueError(f"Transaction not found: {transaction_id}")

        if transaction.state != TransactionState.PREPARED:
            raise ValueError("Transaction not prepared")

        transaction.state = TransactionState.COMMITTING

        # Commit all participants
        commit_tasks = []
        for participant in transaction.participants.values():
            task = asyncio.create_task(
                self._commit_participant(transaction, participant)
            )
            commit_tasks.append(task)

        # Wait for all
        try:
            await asyncio.wait_for(
                asyncio.gather(*commit_tasks),
                timeout=self.config.commit_timeout_seconds
            )
        except asyncio.TimeoutError:
            logger.error(f"Commit timeout: {transaction_id}")

        # Count results
        committed = sum(
            1 for p in transaction.participants.values()
            if p.state == ParticipantState.COMMITTED
        )

        transaction.commit_count = committed
        transaction.completed_at = datetime.now()

        if committed == len(transaction.participants):
            transaction.state = TransactionState.COMMITTED
            self._stats['transactions_committed'] += 1
            logger.info(f"Transaction committed: {transaction_id}")
            return True
        else:
            transaction.state = TransactionState.ABORTED
            self._stats['transactions_aborted'] += 1
            return False

    async def _commit_participant(
        self,
        transaction: Transaction,
        participant: Participant
    ) -> bool:
        """Commit a single participant."""
        for attempt in range(self.config.retry_count):
            try:
                if participant.commit_handler:
                    await self._call_handler(
                        participant.commit_handler,
                        transaction.id,
                        transaction.data
                    )

                participant.state = ParticipantState.COMMITTED
                participant.completed_at = datetime.now()
                return True

            except Exception as e:
                logger.error(f"Commit failed for {participant.name}: {e}")

                if attempt < self.config.retry_count - 1:
                    await asyncio.sleep(self.config.retry_delay_seconds)

        participant.state = ParticipantState.FAILED
        return False

    # ========================================================================
    # ABORT / ROLLBACK
    # ========================================================================

    async def abort(self, transaction_id: str) -> bool:
        """
        Abort transaction and rollback all participants.

        Returns:
            True if all participants rolled back
        """
        transaction = self._transactions.get(transaction_id)
        if not transaction:
            raise ValueError(f"Transaction not found: {transaction_id}")

        transaction.state = TransactionState.ABORTING

        # Rollback all participants
        rollback_tasks = []
        for participant in transaction.participants.values():
            task = asyncio.create_task(
                self._rollback_participant(transaction, participant)
            )
            rollback_tasks.append(task)

        await asyncio.gather(*rollback_tasks)

        # Count results
        aborted = sum(
            1 for p in transaction.participants.values()
            if p.state == ParticipantState.ABORTED
        )

        transaction.abort_count = aborted
        transaction.state = TransactionState.ABORTED
        transaction.completed_at = datetime.now()

        self._stats['transactions_aborted'] += 1

        logger.warning(f"Transaction aborted: {transaction_id}")

        return aborted == len(transaction.participants)

    async def _rollback_participant(
        self,
        transaction: Transaction,
        participant: Participant
    ) -> bool:
        """Rollback a single participant."""
        try:
            if participant.rollback_handler:
                await self._call_handler(
                    participant.rollback_handler,
                    transaction.id,
                    transaction.data
                )

            participant.state = ParticipantState.ABORTED
            participant.completed_at = datetime.now()
            return True

        except Exception as e:
            logger.error(f"Rollback failed for {participant.name}: {e}")
            participant.state = ParticipantState.FAILED
            return False

    # ========================================================================
    # EXECUTE (CONVENIENCE)
    # ========================================================================

    async def execute(self, transaction_id: str) -> bool:
        """
        Execute full 2PC (prepare + commit).

        Returns:
            True if transaction committed
        """
        # Phase 1
        prepared = await self.prepare(transaction_id)

        if prepared:
            # Phase 2
            return await self.commit(transaction_id)
        else:
            # Abort
            await self.abort(transaction_id)
            return False

    # ========================================================================
    # HELPERS
    # ========================================================================

    async def _call_handler(self, handler: Callable, *args) -> Any:
        """Call handler function."""
        if asyncio.iscoroutinefunction(handler):
            return await handler(*args)
        else:
            return await asyncio.to_thread(handler, *args)

    # ========================================================================
    # QUERIES
    # ========================================================================

    def get_transaction(self, transaction_id: str) -> Optional[Transaction]:
        """Get transaction by ID."""
        return self._transactions.get(transaction_id)

    def list_transactions(
        self,
        state: Optional[TransactionState] = None
    ) -> List[Transaction]:
        """List transactions."""
        with self._lock:
            transactions = list(self._transactions.values())
            if state:
                transactions = [t for t in transactions if t.state == state]
            return transactions

    # ========================================================================
    # RECOVERY
    # ========================================================================

    async def recover_transaction(self, transaction_id: str) -> TransactionState:
        """
        Recover an in-doubt transaction.

        Returns:
            Final transaction state
        """
        transaction = self._transactions.get(transaction_id)
        if not transaction:
            return TransactionState.UNKNOWN

        # If prepared, try to commit
        if transaction.state == TransactionState.PREPARED:
            success = await self.commit(transaction_id)
            return TransactionState.COMMITTED if success else TransactionState.ABORTED

        # If committing, retry
        elif transaction.state == TransactionState.COMMITTING:
            success = await self.commit(transaction_id)
            return TransactionState.COMMITTED if success else TransactionState.ABORTED

        # Otherwise, abort
        else:
            await self.abort(transaction_id)
            return TransactionState.ABORTED

    # ========================================================================
    # STATS
    # ========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get coordinator statistics."""
        return {
            'coordinator_id': self.coordinator_id,
            'active_transactions': len([
                t for t in self._transactions.values()
                if t.state not in (
                    TransactionState.COMMITTED,
                    TransactionState.ABORTED
                )
            ]),
            **self._stats
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

tpc_coordinator = TwoPhaseCommitCoordinator()


def begin_transaction(**kwargs) -> Transaction:
    """Begin a distributed transaction."""
    return tpc_coordinator.begin_transaction(**kwargs)


async def execute_transaction(transaction_id: str) -> bool:
    """Execute a 2PC transaction."""
    return await tpc_coordinator.execute(transaction_id)

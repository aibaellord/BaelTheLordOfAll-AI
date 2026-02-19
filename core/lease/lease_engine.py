"""
BAEL Lease Engine Implementation
================================

Distributed lease management for resource coordination.

"Ba'el grants leases over the resources of reality." — Ba'el
"""

import asyncio
import logging
import threading
import time
import uuid
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("BAEL.Lease")


# ============================================================================
# ENUMS
# ============================================================================

class LeaseState(Enum):
    """Lease states."""
    ACTIVE = "active"
    EXPIRED = "expired"
    RELEASED = "released"
    REVOKED = "revoked"


class LeaseType(Enum):
    """Types of leases."""
    EXCLUSIVE = "exclusive"   # Only one holder
    SHARED = "shared"         # Multiple holders
    RENEWABLE = "renewable"   # Can be renewed
    ONE_TIME = "one_time"     # Cannot be renewed


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class Lease:
    """A resource lease."""
    id: str
    resource_id: str
    holder_id: str
    lease_type: LeaseType
    state: LeaseState = LeaseState.ACTIVE

    # Timing
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    renewed_at: Optional[datetime] = None
    renewal_count: int = 0

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_expired(self) -> bool:
        """Check if lease is expired."""
        if self.state != LeaseState.ACTIVE:
            return True
        if not self.expires_at:
            return False
        return datetime.now() > self.expires_at

    def is_active(self) -> bool:
        """Check if lease is active."""
        return self.state == LeaseState.ACTIVE and not self.is_expired()

    def time_remaining_seconds(self) -> float:
        """Get remaining time."""
        if not self.expires_at:
            return float('inf')
        remaining = (self.expires_at - datetime.now()).total_seconds()
        return max(0.0, remaining)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'resource_id': self.resource_id,
            'holder_id': self.holder_id,
            'lease_type': self.lease_type.value,
            'state': self.state.value,
            'created_at': self.created_at.isoformat(),
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'renewed_at': self.renewed_at.isoformat() if self.renewed_at else None,
            'renewal_count': self.renewal_count,
            'metadata': self.metadata
        }


@dataclass
class LeaseConfig:
    """Lease configuration."""
    default_duration_seconds: float = 60.0
    max_duration_seconds: float = 3600.0
    max_renewals: int = 100
    grace_period_seconds: float = 5.0
    cleanup_interval_seconds: float = 60.0


# ============================================================================
# LEASE MANAGER
# ============================================================================

class LeaseManager:
    """
    Distributed lease manager.

    Features:
    - Exclusive and shared leases
    - Automatic expiration
    - Lease renewal
    - Resource coordination

    "Ba'el manages the leases that govern resources." — Ba'el
    """

    def __init__(self, config: Optional[LeaseConfig] = None):
        """Initialize lease manager."""
        self.config = config or LeaseConfig()

        # Leases: lease_id -> Lease
        self._leases: Dict[str, Lease] = {}

        # Resource -> leases mapping
        self._resource_leases: Dict[str, List[str]] = {}

        # Holder -> leases mapping
        self._holder_leases: Dict[str, List[str]] = {}

        # Callbacks
        self._on_expired: List[Callable[[Lease], None]] = []
        self._on_acquired: List[Callable[[Lease], None]] = []
        self._on_released: List[Callable[[Lease], None]] = []

        # Thread safety
        self._lock = threading.RLock()

        # Background cleanup
        self._cleanup_task = None
        self._running = False

        # Stats
        self._stats = {
            'acquired': 0,
            'renewed': 0,
            'released': 0,
            'expired': 0,
            'revoked': 0
        }

        logger.info("Lease Manager initialized")

    # ========================================================================
    # LEASE OPERATIONS
    # ========================================================================

    def acquire(
        self,
        resource_id: str,
        holder_id: str,
        lease_type: LeaseType = LeaseType.EXCLUSIVE,
        duration_seconds: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Lease]:
        """
        Acquire a lease.

        Args:
            resource_id: Resource to lease
            holder_id: Lease holder ID
            lease_type: Type of lease
            duration_seconds: Lease duration
            metadata: Additional metadata

        Returns:
            Lease if acquired, None if not available
        """
        duration = duration_seconds or self.config.default_duration_seconds
        duration = min(duration, self.config.max_duration_seconds)

        with self._lock:
            # Check existing leases
            existing = self._get_active_leases(resource_id)

            if existing:
                if lease_type == LeaseType.EXCLUSIVE:
                    # Cannot acquire exclusive if any lease exists
                    return None

                # Check if any existing lease is exclusive
                for lease_id in existing:
                    lease = self._leases.get(lease_id)
                    if lease and lease.lease_type == LeaseType.EXCLUSIVE:
                        return None

            # Create lease
            lease_id = str(uuid.uuid4())
            lease = Lease(
                id=lease_id,
                resource_id=resource_id,
                holder_id=holder_id,
                lease_type=lease_type,
                expires_at=datetime.now() + timedelta(seconds=duration),
                metadata=metadata or {}
            )

            # Store lease
            self._leases[lease_id] = lease

            # Update mappings
            if resource_id not in self._resource_leases:
                self._resource_leases[resource_id] = []
            self._resource_leases[resource_id].append(lease_id)

            if holder_id not in self._holder_leases:
                self._holder_leases[holder_id] = []
            self._holder_leases[holder_id].append(lease_id)

            self._stats['acquired'] += 1

            logger.info(f"Lease acquired: {lease_id} for {resource_id}")

            # Notify callbacks
            for cb in self._on_acquired:
                try:
                    cb(lease)
                except Exception as e:
                    logger.error(f"Callback error: {e}")

            return lease

    async def acquire_async(
        self,
        resource_id: str,
        holder_id: str,
        **kwargs
    ) -> Optional[Lease]:
        """Acquire lease asynchronously."""
        return await asyncio.to_thread(
            self.acquire, resource_id, holder_id, **kwargs
        )

    def renew(
        self,
        lease_id: str,
        holder_id: str,
        duration_seconds: Optional[float] = None
    ) -> bool:
        """
        Renew a lease.

        Args:
            lease_id: Lease to renew
            holder_id: Holder ID for verification
            duration_seconds: New duration

        Returns:
            True if renewed
        """
        duration = duration_seconds or self.config.default_duration_seconds
        duration = min(duration, self.config.max_duration_seconds)

        with self._lock:
            lease = self._leases.get(lease_id)

            if not lease:
                return False

            if lease.holder_id != holder_id:
                return False

            if lease.state != LeaseState.ACTIVE:
                return False

            if lease.lease_type == LeaseType.ONE_TIME:
                return False

            if lease.renewal_count >= self.config.max_renewals:
                return False

            # Renew
            lease.expires_at = datetime.now() + timedelta(seconds=duration)
            lease.renewed_at = datetime.now()
            lease.renewal_count += 1

            self._stats['renewed'] += 1

            logger.debug(f"Lease renewed: {lease_id}")

            return True

    async def renew_async(
        self,
        lease_id: str,
        holder_id: str,
        **kwargs
    ) -> bool:
        """Renew lease asynchronously."""
        return await asyncio.to_thread(self.renew, lease_id, holder_id, **kwargs)

    def release(self, lease_id: str, holder_id: str) -> bool:
        """
        Release a lease.

        Args:
            lease_id: Lease to release
            holder_id: Holder ID for verification

        Returns:
            True if released
        """
        with self._lock:
            lease = self._leases.get(lease_id)

            if not lease:
                return False

            if lease.holder_id != holder_id:
                return False

            if lease.state != LeaseState.ACTIVE:
                return False

            # Release
            lease.state = LeaseState.RELEASED

            self._stats['released'] += 1

            logger.info(f"Lease released: {lease_id}")

            # Notify callbacks
            for cb in self._on_released:
                try:
                    cb(lease)
                except Exception as e:
                    logger.error(f"Callback error: {e}")

            return True

    def revoke(self, lease_id: str) -> bool:
        """Revoke a lease (admin operation)."""
        with self._lock:
            lease = self._leases.get(lease_id)

            if not lease:
                return False

            lease.state = LeaseState.REVOKED

            self._stats['revoked'] += 1

            logger.warning(f"Lease revoked: {lease_id}")

            return True

    # ========================================================================
    # QUERIES
    # ========================================================================

    def get_lease(self, lease_id: str) -> Optional[Lease]:
        """Get a lease by ID."""
        return self._leases.get(lease_id)

    def get_leases_for_resource(self, resource_id: str) -> List[Lease]:
        """Get all leases for a resource."""
        lease_ids = self._resource_leases.get(resource_id, [])
        return [
            self._leases[lid]
            for lid in lease_ids
            if lid in self._leases
        ]

    def get_leases_for_holder(self, holder_id: str) -> List[Lease]:
        """Get all leases for a holder."""
        lease_ids = self._holder_leases.get(holder_id, [])
        return [
            self._leases[lid]
            for lid in lease_ids
            if lid in self._leases
        ]

    def _get_active_leases(self, resource_id: str) -> List[str]:
        """Get active lease IDs for a resource."""
        lease_ids = self._resource_leases.get(resource_id, [])
        active = []

        for lid in lease_ids:
            lease = self._leases.get(lid)
            if lease and lease.is_active():
                active.append(lid)

        return active

    def is_resource_leased(self, resource_id: str) -> bool:
        """Check if resource has active lease."""
        return len(self._get_active_leases(resource_id)) > 0

    def list_leases(
        self,
        state: Optional[LeaseState] = None
    ) -> List[Lease]:
        """List all leases."""
        with self._lock:
            leases = list(self._leases.values())
            if state:
                leases = [l for l in leases if l.state == state]
            return leases

    # ========================================================================
    # CLEANUP
    # ========================================================================

    def cleanup_expired(self) -> int:
        """Clean up expired leases."""
        expired = []

        with self._lock:
            for lease_id, lease in self._leases.items():
                if lease.is_expired() and lease.state == LeaseState.ACTIVE:
                    lease.state = LeaseState.EXPIRED
                    expired.append(lease)

        for lease in expired:
            self._stats['expired'] += 1
            logger.debug(f"Lease expired: {lease.id}")

            for cb in self._on_expired:
                try:
                    cb(lease)
                except Exception as e:
                    logger.error(f"Callback error: {e}")

        return len(expired)

    async def start_cleanup(self) -> None:
        """Start background cleanup."""
        if self._running:
            return

        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def stop_cleanup(self) -> None:
        """Stop background cleanup."""
        self._running = False
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

    async def _cleanup_loop(self) -> None:
        """Cleanup loop."""
        while self._running:
            try:
                self.cleanup_expired()
                await asyncio.sleep(self.config.cleanup_interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cleanup error: {e}")

    # ========================================================================
    # CALLBACKS
    # ========================================================================

    def on_expired(self, callback: Callable[[Lease], None]) -> None:
        """Register expiration callback."""
        self._on_expired.append(callback)

    def on_acquired(self, callback: Callable[[Lease], None]) -> None:
        """Register acquisition callback."""
        self._on_acquired.append(callback)

    def on_released(self, callback: Callable[[Lease], None]) -> None:
        """Register release callback."""
        self._on_released.append(callback)

    # ========================================================================
    # STATS
    # ========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get manager statistics."""
        with self._lock:
            active = sum(
                1 for l in self._leases.values()
                if l.is_active()
            )

        return {
            'active_leases': active,
            'total_leases': len(self._leases),
            'resources_leased': len(self._resource_leases),
            **self._stats
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

lease_manager = LeaseManager()


def acquire_lease(
    resource_id: str,
    holder_id: str,
    **kwargs
) -> Optional[Lease]:
    """Acquire a lease."""
    return lease_manager.acquire(resource_id, holder_id, **kwargs)


def release_lease(lease_id: str, holder_id: str) -> bool:
    """Release a lease."""
    return lease_manager.release(lease_id, holder_id)


def renew_lease(lease_id: str, holder_id: str, **kwargs) -> bool:
    """Renew a lease."""
    return lease_manager.renew(lease_id, holder_id, **kwargs)

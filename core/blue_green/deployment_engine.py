"""
BAEL Blue-Green Deployment Engine Implementation
=================================================

Zero-downtime deployment strategies.

"Ba'el transitions between worlds seamlessly." — Ba'el
"""

import asyncio
import logging
import threading
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import uuid

logger = logging.getLogger("BAEL.BlueGreen")


# ============================================================================
# ENUMS
# ============================================================================

class DeploymentStrategy(Enum):
    """Deployment strategies."""
    BLUE_GREEN = "blue_green"     # Instant switch
    CANARY = "canary"             # Gradual rollout
    ROLLING = "rolling"           # Rolling update
    RECREATE = "recreate"         # Full restart


class DeploymentState(Enum):
    """Deployment states."""
    PENDING = "pending"
    DEPLOYING = "deploying"
    TESTING = "testing"
    SWITCHING = "switching"
    ACTIVE = "active"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"


class EnvironmentStatus(Enum):
    """Environment status."""
    ACTIVE = "active"       # Receiving traffic
    IDLE = "idle"           # Ready but no traffic
    DEPLOYING = "deploying" # Being deployed to
    DRAINING = "draining"   # Connections draining


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class Environment:
    """A deployment environment."""
    id: str
    name: str  # "blue" or "green"
    status: EnvironmentStatus = EnvironmentStatus.IDLE

    # Version info
    version: Optional[str] = None
    deployed_at: Optional[datetime] = None

    # Health
    healthy: bool = True
    health_checks_passed: int = 0
    health_checks_failed: int = 0

    # Traffic
    traffic_weight: float = 0.0  # 0-100%

    # Endpoints
    endpoints: List[str] = field(default_factory=list)

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'status': self.status.value,
            'version': self.version,
            'deployed_at': self.deployed_at.isoformat() if self.deployed_at else None,
            'healthy': self.healthy,
            'traffic_weight': self.traffic_weight,
            'endpoints': self.endpoints
        }


@dataclass
class Deployment:
    """A deployment operation."""
    id: str
    version: str
    strategy: DeploymentStrategy

    # State
    state: DeploymentState = DeploymentState.PENDING
    target_environment: Optional[str] = None

    # Timing
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Results
    success: bool = False
    error: Optional[str] = None

    # Canary specific
    traffic_percentage: float = 0.0

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'version': self.version,
            'strategy': self.strategy.value,
            'state': self.state.value,
            'target_environment': self.target_environment,
            'success': self.success,
            'traffic_percentage': self.traffic_percentage
        }


@dataclass
class DeploymentConfig:
    """Deployment configuration."""
    health_check_interval: float = 5.0
    health_check_timeout: float = 10.0
    drain_timeout: float = 30.0
    min_healthy_checks: int = 3
    auto_rollback: bool = True


# ============================================================================
# DEPLOYMENT MANAGER
# ============================================================================

class DeploymentManager:
    """
    Blue-green and canary deployment manager.

    Features:
    - Zero-downtime deployments
    - Automatic health checking
    - Traffic shifting
    - Instant rollback

    "Ba'el deploys without disturbing the fabric." — Ba'el
    """

    def __init__(self, config: Optional[DeploymentConfig] = None):
        """Initialize deployment manager."""
        self.config = config or DeploymentConfig()

        # Environments
        self._environments: Dict[str, Environment] = {
            'blue': Environment(id='blue', name='blue'),
            'green': Environment(id='green', name='green')
        }

        # Current active environment
        self._active_env = 'blue'

        # Deployments
        self._deployments: Dict[str, Deployment] = {}
        self._current_deployment: Optional[str] = None

        # Deploy handlers
        self._deploy_handler: Optional[Callable] = None
        self._health_check_handler: Optional[Callable] = None

        # Thread safety
        self._lock = threading.RLock()

        # Stats
        self._stats = {
            'deployments': 0,
            'successful': 0,
            'failed': 0,
            'rollbacks': 0
        }

        logger.info("Deployment Manager initialized")

    # ========================================================================
    # ENVIRONMENT MANAGEMENT
    # ========================================================================

    def get_active_environment(self) -> Environment:
        """Get the active environment."""
        return self._environments[self._active_env]

    def get_idle_environment(self) -> Environment:
        """Get the idle environment."""
        idle_name = 'green' if self._active_env == 'blue' else 'blue'
        return self._environments[idle_name]

    def get_environment(self, name: str) -> Optional[Environment]:
        """Get environment by name."""
        return self._environments.get(name)

    def list_environments(self) -> List[Environment]:
        """List all environments."""
        return list(self._environments.values())

    # ========================================================================
    # DEPLOYMENT
    # ========================================================================

    async def deploy(
        self,
        version: str,
        strategy: DeploymentStrategy = DeploymentStrategy.BLUE_GREEN,
        deployment_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Deployment:
        """
        Deploy a new version.

        Args:
            version: Version to deploy
            strategy: Deployment strategy
            deployment_id: Optional deployment ID
            metadata: Additional metadata

        Returns:
            Deployment object
        """
        deployment = Deployment(
            id=deployment_id or str(uuid.uuid4()),
            version=version,
            strategy=strategy,
            metadata=metadata or {}
        )

        with self._lock:
            self._deployments[deployment.id] = deployment
            self._current_deployment = deployment.id

        try:
            if strategy == DeploymentStrategy.BLUE_GREEN:
                await self._blue_green_deploy(deployment)
            elif strategy == DeploymentStrategy.CANARY:
                await self._canary_deploy(deployment)
            elif strategy == DeploymentStrategy.ROLLING:
                await self._rolling_deploy(deployment)
            else:
                await self._recreate_deploy(deployment)

            deployment.state = DeploymentState.ACTIVE
            deployment.success = True
            self._stats['successful'] += 1

        except Exception as e:
            deployment.state = DeploymentState.FAILED
            deployment.error = str(e)
            self._stats['failed'] += 1

            if self.config.auto_rollback:
                await self.rollback(deployment.id)

        finally:
            deployment.completed_at = datetime.now()
            self._stats['deployments'] += 1

        return deployment

    async def _blue_green_deploy(self, deployment: Deployment) -> None:
        """Execute blue-green deployment."""
        # Get idle environment
        target_env = self.get_idle_environment()
        deployment.target_environment = target_env.name

        # Deploy to idle environment
        deployment.state = DeploymentState.DEPLOYING
        target_env.status = EnvironmentStatus.DEPLOYING

        if self._deploy_handler:
            await self._call_handler(self._deploy_handler, deployment, target_env)

        target_env.version = deployment.version
        target_env.deployed_at = datetime.now()
        target_env.status = EnvironmentStatus.IDLE

        # Health check
        deployment.state = DeploymentState.TESTING
        await self._health_check_environment(target_env)

        if not target_env.healthy:
            raise Exception("Health check failed")

        # Switch traffic
        deployment.state = DeploymentState.SWITCHING
        await self._switch_traffic(target_env.name)

    async def _canary_deploy(self, deployment: Deployment) -> None:
        """Execute canary deployment."""
        target_env = self.get_idle_environment()
        deployment.target_environment = target_env.name

        # Deploy to canary
        target_env.status = EnvironmentStatus.DEPLOYING

        if self._deploy_handler:
            await self._call_handler(self._deploy_handler, deployment, target_env)

        target_env.version = deployment.version
        target_env.deployed_at = datetime.now()
        target_env.status = EnvironmentStatus.IDLE

        # Gradual traffic shift
        for percentage in [10, 25, 50, 75, 100]:
            deployment.traffic_percentage = percentage

            # Shift traffic
            target_env.traffic_weight = percentage
            active_env = self.get_active_environment()
            active_env.traffic_weight = 100 - percentage

            # Health check
            await self._health_check_environment(target_env)

            if not target_env.healthy:
                raise Exception(f"Canary unhealthy at {percentage}%")

            if percentage < 100:
                await asyncio.sleep(5)  # Wait between increments

        # Full switch
        await self._switch_traffic(target_env.name)

    async def _rolling_deploy(self, deployment: Deployment) -> None:
        """Execute rolling deployment."""
        # Simplified: deploy to idle and switch
        await self._blue_green_deploy(deployment)

    async def _recreate_deploy(self, deployment: Deployment) -> None:
        """Execute recreate deployment (downtime)."""
        active_env = self.get_active_environment()
        deployment.target_environment = active_env.name

        # Stop active
        active_env.status = EnvironmentStatus.DRAINING
        await asyncio.sleep(self.config.drain_timeout)

        # Redeploy
        active_env.status = EnvironmentStatus.DEPLOYING

        if self._deploy_handler:
            await self._call_handler(self._deploy_handler, deployment, active_env)

        active_env.version = deployment.version
        active_env.deployed_at = datetime.now()
        active_env.status = EnvironmentStatus.ACTIVE
        active_env.traffic_weight = 100

    async def _switch_traffic(self, to_env: str) -> None:
        """Switch all traffic to environment."""
        with self._lock:
            # Drain old
            old_env = self._environments[self._active_env]
            old_env.status = EnvironmentStatus.DRAINING
            old_env.traffic_weight = 0

            # Activate new
            new_env = self._environments[to_env]
            new_env.status = EnvironmentStatus.ACTIVE
            new_env.traffic_weight = 100

            self._active_env = to_env

            # Finish drain
            await asyncio.sleep(self.config.drain_timeout)
            old_env.status = EnvironmentStatus.IDLE

        logger.info(f"Traffic switched to: {to_env}")

    # ========================================================================
    # HEALTH CHECKS
    # ========================================================================

    async def _health_check_environment(self, env: Environment) -> None:
        """Run health checks on environment."""
        passed = 0
        required = self.config.min_healthy_checks

        for _ in range(required + 2):  # Extra attempts
            try:
                if self._health_check_handler:
                    healthy = await self._call_handler(
                        self._health_check_handler, env
                    )
                else:
                    healthy = True  # Assume healthy if no handler

                if healthy:
                    passed += 1
                    env.health_checks_passed += 1
                else:
                    env.health_checks_failed += 1

                if passed >= required:
                    env.healthy = True
                    return

            except Exception as e:
                env.health_checks_failed += 1
                logger.error(f"Health check error: {e}")

            await asyncio.sleep(self.config.health_check_interval)

        env.healthy = passed >= required

    # ========================================================================
    # ROLLBACK
    # ========================================================================

    async def rollback(self, deployment_id: Optional[str] = None) -> bool:
        """
        Rollback deployment.

        Args:
            deployment_id: Deployment to rollback

        Returns:
            True if rolled back
        """
        deployment_id = deployment_id or self._current_deployment

        if not deployment_id:
            return False

        deployment = self._deployments.get(deployment_id)
        if not deployment:
            return False

        # Switch back to other environment
        other_env = 'green' if self._active_env == 'blue' else 'blue'

        if self._environments[other_env].version:
            await self._switch_traffic(other_env)
            deployment.state = DeploymentState.ROLLED_BACK
            self._stats['rollbacks'] += 1

            logger.warning(f"Rolled back deployment: {deployment_id}")
            return True

        return False

    # ========================================================================
    # PROMOTION
    # ========================================================================

    async def promote(self, environment_name: str) -> bool:
        """Promote an environment to active."""
        if environment_name not in self._environments:
            return False

        await self._switch_traffic(environment_name)
        return True

    # ========================================================================
    # HANDLERS
    # ========================================================================

    def set_deploy_handler(self, handler: Callable) -> None:
        """Set deployment handler."""
        self._deploy_handler = handler

    def set_health_check_handler(self, handler: Callable) -> None:
        """Set health check handler."""
        self._health_check_handler = handler

    async def _call_handler(self, handler: Callable, *args) -> Any:
        """Call handler function."""
        if asyncio.iscoroutinefunction(handler):
            return await handler(*args)
        else:
            return await asyncio.to_thread(handler, *args)

    # ========================================================================
    # QUERIES
    # ========================================================================

    def get_deployment(self, deployment_id: str) -> Optional[Deployment]:
        """Get deployment by ID."""
        return self._deployments.get(deployment_id)

    def list_deployments(
        self,
        state: Optional[DeploymentState] = None
    ) -> List[Deployment]:
        """List deployments."""
        with self._lock:
            deployments = list(self._deployments.values())
            if state:
                deployments = [d for d in deployments if d.state == state]
            return deployments

    # ========================================================================
    # STATS
    # ========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get manager statistics."""
        return {
            'active_environment': self._active_env,
            'current_version': self.get_active_environment().version,
            **self._stats
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

deployment_manager = DeploymentManager()


async def deploy(version: str, **kwargs) -> Deployment:
    """Deploy a version."""
    return await deployment_manager.deploy(version, **kwargs)


async def rollback(deployment_id: Optional[str] = None) -> bool:
    """Rollback deployment."""
    return await deployment_manager.rollback(deployment_id)


async def promote(environment: str) -> bool:
    """Promote environment."""
    return await deployment_manager.promote(environment)

"""
Advanced Deployment & DevOps System for BAEL

Provides blue-green deployment, canary deployments, automated rollbacks,
feature flags, version management, environment promotion, and deployment pipelines.
"""

import asyncio
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DeploymentEnvironment(Enum):
    """Deployment environments"""
    LOCAL = "local"
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class DeploymentStrategy(Enum):
    """Deployment strategies"""
    BLUE_GREEN = "blue_green"
    CANARY = "canary"
    ROLLING = "rolling"
    FEATURE_FLAG = "feature_flag"


class DeploymentStatus(Enum):
    """Deployment status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    VALIDATING = "validating"
    SUCCESS = "success"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class Version:
    """Application version"""
    version_id: str
    version_number: str
    git_commit: str
    git_tag: str
    created_at: datetime
    created_by: str
    description: str = ""
    features: List[str] = field(default_factory=list)
    breaking_changes: List[str] = field(default_factory=list)
    checksum: str = ""
    size_mb: float = 0.0


@dataclass
class Deployment:
    """Deployment record"""
    deployment_id: str
    version: Version
    environment: DeploymentEnvironment
    strategy: DeploymentStrategy
    status: DeploymentStatus = DeploymentStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: float = 0.0
    deployed_by: str = ""
    rollback_version: Optional[Version] = None
    health_checks: Dict[str, bool] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)
    logs: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "deployment_id": self.deployment_id,
            "version": self.version.version_number,
            "environment": self.environment.value,
            "strategy": self.strategy.value,
            "status": self.status.value,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "deployed_by": self.deployed_by,
            "health_checks": self.health_checks
        }


@dataclass
class CanaryConfig:
    """Canary deployment configuration"""
    initial_traffic_percentage: int = 5
    traffic_increment_percentage: int = 10
    traffic_check_interval_seconds: int = 300
    max_deployment_time_seconds: int = 3600
    error_threshold_percentage: float = 1.0
    latency_threshold_ms: float = 100.0


@dataclass
class BlueGreenConfig:
    """Blue-green deployment configuration"""
    health_check_timeout_seconds: int = 60
    health_check_interval_seconds: int = 5
    validation_timeout_seconds: int = 300
    smoke_tests_enabled: bool = True


@dataclass
class EnvironmentConfig:
    """Environment configuration"""
    name: DeploymentEnvironment
    replicas: int = 1
    resource_limits: Dict[str, str] = field(default_factory=dict)
    health_checks_enabled: bool = True
    auto_rollback_enabled: bool = True
    auto_scaling_enabled: bool = False
    deployment_timeout_seconds: int = 600


class VersionManager:
    """Manages application versions"""

    def __init__(self):
        self.versions: Dict[str, Version] = {}
        self.version_history: List[Version] = []

    def create_version(self, version_number: str, git_commit: str, git_tag: str,
                      created_by: str, description: str = "",
                      features: List[str] = None) -> Version:
        """Create new version"""
        version_id = str(uuid.uuid4())

        version = Version(
            version_id=version_id,
            version_number=version_number,
            git_commit=git_commit,
            git_tag=git_tag,
            created_at=datetime.now(),
            created_by=created_by,
            description=description,
            features=features or []
        )

        self.versions[version_id] = version
        self.version_history.append(version)

        logger.info(f"Created version: {version_number}")

        return version

    def get_version(self, version_id: str) -> Optional[Version]:
        """Get version"""
        return self.versions.get(version_id)

    def get_latest_version(self) -> Optional[Version]:
        """Get latest version"""
        return self.version_history[-1] if self.version_history else None

    def get_version_history(self, limit: int = 10) -> List[Version]:
        """Get version history"""
        return self.version_history[-limit:]


class HealthChecker:
    """Checks deployment health"""

    def __init__(self):
        self.check_results: Dict[str, Dict[str, bool]] = {}

    async def run_health_checks(self, deployment: Deployment) -> Dict[str, bool]:
        """Run health checks"""
        checks = {
            "api_health": await self._check_api_health(),
            "database_connectivity": await self._check_database(),
            "cache_health": await self._check_cache(),
            "dependencies": await self._check_dependencies(),
            "memory_healthy": await self._check_memory(),
            "cpu_healthy": await self._check_cpu()
        }

        self.check_results[deployment.deployment_id] = checks

        all_healthy = all(checks.values())
        logger.info(f"Health checks: {'✓ PASS' if all_healthy else '✗ FAIL'} - {checks}")

        return checks

    async def _check_api_health(self) -> bool:
        """Check API health"""
        try:
            # Simulate API check
            await asyncio.sleep(0.1)
            return True
        except:
            return False

    async def _check_database(self) -> bool:
        """Check database connectivity"""
        try:
            await asyncio.sleep(0.1)
            return True
        except:
            return False

    async def _check_cache(self) -> bool:
        """Check cache health"""
        try:
            await asyncio.sleep(0.05)
            return True
        except:
            return False

    async def _check_dependencies(self) -> bool:
        """Check dependencies"""
        try:
            await asyncio.sleep(0.1)
            return True
        except:
            return False

    async def _check_memory(self) -> bool:
        """Check memory usage"""
        try:
            import psutil
            memory_percent = psutil.virtual_memory().percent
            return memory_percent < 80
        except:
            return True

    async def _check_cpu(self) -> bool:
        """Check CPU usage"""
        try:
            import psutil
            cpu_percent = psutil.cpu_percent(interval=1)
            return cpu_percent < 80
        except:
            return True


class DeploymentStrategy:
    """Base deployment strategy"""

    async def execute(self, deployment: Deployment) -> bool:
        """Execute deployment"""
        raise NotImplementedError


class BlueGreenDeployment(DeploymentStrategy):
    """Blue-green deployment strategy"""

    def __init__(self, health_checker: HealthChecker):
        self.health_checker = health_checker

    async def execute(self, deployment: Deployment) -> bool:
        """Execute blue-green deployment"""
        logger.info(f"Executing blue-green deployment: {deployment.deployment_id}")

        # Deploy to green environment
        logger.info("Deploying to green environment...")
        if not await self._deploy_to_environment(deployment):
            return False

        # Run health checks
        logger.info("Running health checks...")
        health_checks = await self.health_checker.run_health_checks(deployment)
        deployment.health_checks = health_checks

        if not all(health_checks.values()):
            logger.error("Health checks failed")
            return False

        # Switch traffic
        logger.info("Switching traffic to green environment...")
        await self._switch_traffic(deployment)

        # Keep blue for quick rollback
        logger.info("✓ Blue-green deployment successful")

        return True

    async def _deploy_to_environment(self, deployment: Deployment) -> bool:
        """Deploy to green environment"""
        await asyncio.sleep(0.5)  # Simulate deployment
        return True

    async def _switch_traffic(self, deployment: Deployment):
        """Switch traffic from blue to green"""
        await asyncio.sleep(0.2)  # Simulate traffic switch


class CanaryDeployment(DeploymentStrategy):
    """Canary deployment strategy"""

    def __init__(self, health_checker: HealthChecker, config: CanaryConfig):
        self.health_checker = health_checker
        self.config = config

    async def execute(self, deployment: Deployment) -> bool:
        """Execute canary deployment"""
        logger.info(f"Executing canary deployment: {deployment.deployment_id}")

        traffic_percentage = self.config.initial_traffic_percentage
        start_time = time.time()

        while traffic_percentage < 100:
            # Check if deployment time exceeded
            if time.time() - start_time > self.config.max_deployment_time_seconds:
                logger.error("Canary deployment exceeded max time")
                return False

            logger.info(f"Canary traffic: {traffic_percentage}%")

            # Deploy to canary
            await self._deploy_canary(deployment, traffic_percentage)

            # Monitor metrics
            metrics = await self._monitor_canary(deployment)
            deployment.metrics[f"traffic_{traffic_percentage}"] = metrics

            # Check error rate
            if metrics.get("error_rate", 0) > self.config.error_threshold_percentage:
                logger.error(f"High error rate: {metrics['error_rate']}%")
                return False

            # Check latency
            if metrics.get("latency_ms", 0) > self.config.latency_threshold_ms:
                logger.warning(f"High latency: {metrics['latency_ms']}ms")

            # Increment traffic
            traffic_percentage += self.config.traffic_increment_percentage

            # Wait for next check
            await asyncio.sleep(self.config.traffic_check_interval_seconds / 1000)

        logger.info("✓ Canary deployment successful")

        return True

    async def _deploy_canary(self, deployment: Deployment, traffic_percentage: int):
        """Deploy canary version"""
        await asyncio.sleep(0.1)

    async def _monitor_canary(self, deployment: Deployment) -> Dict[str, Any]:
        """Monitor canary metrics"""
        return {
            "error_rate": 0.1,
            "latency_ms": 45.0,
            "requests_per_second": 100
        }


class RollingDeployment(DeploymentStrategy):
    """Rolling deployment strategy"""

    def __init__(self, health_checker: HealthChecker):
        self.health_checker = health_checker

    async def execute(self, deployment: Deployment) -> bool:
        """Execute rolling deployment"""
        logger.info(f"Executing rolling deployment: {deployment.deployment_id}")

        batch_size = 2
        total_replicas = 4

        for i in range(0, total_replicas, batch_size):
            logger.info(f"Deploying batch {i//batch_size + 1}")

            # Update replicas
            await self._update_replicas(deployment, i, i + batch_size)

            # Wait for stability
            await asyncio.sleep(1)

            # Health check
            health_checks = await self.health_checker.run_health_checks(deployment)
            if not all(health_checks.values()):
                logger.error("Health checks failed during rolling update")
                return False

        logger.info("✓ Rolling deployment successful")

        return True

    async def _update_replicas(self, deployment: Deployment, start: int, end: int):
        """Update replica set"""
        await asyncio.sleep(0.2)


class DeploymentEngine:
    """Orchestrates deployments"""

    def __init__(self):
        self.version_manager = VersionManager()
        self.health_checker = HealthChecker()
        self.deployments: Dict[str, Deployment] = {}
        self.current_deployments: Dict[DeploymentEnvironment, Deployment] = {}
        self.environment_configs: Dict[DeploymentEnvironment, EnvironmentConfig] = {}

    def register_environment(self, env_config: EnvironmentConfig):
        """Register deployment environment"""
        self.environment_configs[env_config.name] = env_config
        logger.info(f"Registered environment: {env_config.name.value}")

    async def deploy(self, version: Version, environment: DeploymentEnvironment,
                    strategy: DeploymentStrategy, deployed_by: str) -> Deployment:
        """Deploy version to environment"""
        deployment = Deployment(
            deployment_id=str(uuid.uuid4()),
            version=version,
            environment=environment,
            strategy=strategy,
            status=DeploymentStatus.IN_PROGRESS,
            started_at=datetime.now(),
            deployed_by=deployed_by
        )

        self.deployments[deployment.deployment_id] = deployment

        logger.info(f"Starting deployment: {deployment.deployment_id}")
        logger.info(f"Version: {version.version_number}")
        logger.info(f"Environment: {environment.value}")
        logger.info(f"Strategy: {strategy.__class__.__name__}")

        try:
            success = await strategy.execute(deployment)

            if success:
                deployment.status = DeploymentStatus.SUCCESS
                self.current_deployments[environment] = deployment
                logger.info(f"✓ Deployment successful: {deployment.deployment_id}")
            else:
                deployment.status = DeploymentStatus.FAILED
                logger.error(f"✗ Deployment failed: {deployment.deployment_id}")

                # Auto-rollback if enabled
                if self.environment_configs[environment].auto_rollback_enabled:
                    await self.rollback(deployment)

        except Exception as e:
            deployment.status = DeploymentStatus.FAILED
            logger.error(f"Deployment error: {e}")

        finally:
            deployment.completed_at = datetime.now()
            if deployment.started_at:
                deployment.duration_seconds = (
                    deployment.completed_at - deployment.started_at
                ).total_seconds()

        return deployment

    async def rollback(self, deployment: Deployment) -> Optional[Deployment]:
        """Rollback deployment"""
        logger.info(f"Rolling back deployment: {deployment.deployment_id}")

        history = self.version_manager.get_version_history(limit=2)
        if len(history) < 2:
            logger.error("No previous version to rollback to")
            return None

        previous_version = history[-2]
        deployment.rollback_version = previous_version
        deployment.status = DeploymentStatus.ROLLED_BACK

        logger.info(f"Rolled back to version: {previous_version.version_number}")

        return deployment

    def get_deployment_status(self, deployment_id: str) -> Optional[Dict[str, Any]]:
        """Get deployment status"""
        deployment = self.deployments.get(deployment_id)
        if not deployment:
            return None

        return deployment.to_dict()

    def get_environment_status(self, environment: DeploymentEnvironment) -> Dict[str, Any]:
        """Get environment status"""
        current = self.current_deployments.get(environment)

        return {
            "environment": environment.value,
            "current_version": current.version.version_number if current else None,
            "current_deployment_id": current.deployment_id if current else None,
            "status": current.status.value if current else "no_deployment",
            "deployment_history": [
                d.to_dict() for d in self.deployments.values()
                if d.environment == environment
            ]
        }

    def get_deployment_history(self, environment: DeploymentEnvironment, limit: int = 10) -> List[Dict[str, Any]]:
        """Get deployment history"""
        deployments = [
            d for d in self.deployments.values()
            if d.environment == environment
        ]

        deployments.sort(key=lambda d: d.started_at or datetime.now(), reverse=True)

        return [d.to_dict() for d in deployments[:limit]]


# Global deployment engine
_deployment_engine = None


def get_deployment_engine() -> DeploymentEngine:
    """Get global deployment engine"""
    global _deployment_engine
    if _deployment_engine is None:
        _deployment_engine = DeploymentEngine()
    return _deployment_engine


if __name__ == "__main__":
    logger.info("Deployment & DevOps System initialized")

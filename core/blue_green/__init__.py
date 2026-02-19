"""
BAEL Blue-Green Deployment Engine
=================================

Zero-downtime deployment strategies.

"Ba'el transitions between worlds seamlessly." — Ba'el
"""

from .deployment_engine import (
    DeploymentStrategy,
    DeploymentState,
    Environment,
    Deployment,
    DeploymentConfig,
    DeploymentManager,
    deployment_manager,
    deploy,
    rollback,
    promote
)

__all__ = [
    'DeploymentStrategy',
    'DeploymentState',
    'Environment',
    'Deployment',
    'DeploymentConfig',
    'DeploymentManager',
    'deployment_manager',
    'deploy',
    'rollback',
    'promote'
]

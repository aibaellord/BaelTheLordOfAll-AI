"""
BA'EL Discovery Module
Automated resource and opportunity discovery.
"""

from .automated_discovery_engine import (
    AutomatedDiscoveryEngine,
    create_discovery_engine,
    DiscoveredResource,
    DiscoveryResult,
    DiscoverySource,
    ResourceCategory,
    OpportunityType,
    SourceScanner,
    GitHubTopicsScanner,
    AwesomeListScanner,
    HuggingFaceScanner,
    QualityScorer
)

__all__ = [
    "AutomatedDiscoveryEngine",
    "create_discovery_engine",
    "DiscoveredResource",
    "DiscoveryResult",
    "DiscoverySource",
    "ResourceCategory",
    "OpportunityType",
    "SourceScanner",
    "GitHubTopicsScanner",
    "AwesomeListScanner",
    "HuggingFaceScanner",
    "QualityScorer"
]

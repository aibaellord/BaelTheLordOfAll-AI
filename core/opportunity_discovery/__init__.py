# BAEL - Opportunity Discovery Engine
# "The All-Seeing Eye of Automation"

"""
Opportunity Discovery Engine - Finds opportunities you didn't know existed.

This module provides comprehensive codebase analysis to discover:
- Code quality improvements
- Performance optimization opportunities
- Security vulnerabilities
- AI enhancement possibilities
- Testing gaps
- Documentation needs
- Architecture improvements

Usage:
    from core.opportunity_discovery import OpportunityDiscoveryEngine

    engine = await OpportunityDiscoveryEngine.create()
    opportunities = await engine.discover_all("/path/to/project")
"""

from .opportunity_discovery_engine import (
    OpportunityDiscoveryEngine,
    OpportunityType,
    ImpactLevel,
    EffortEstimate,
    Opportunity,
    OpportunityAnalyzer,
)

__all__ = [
    "OpportunityDiscoveryEngine",
    "OpportunityType",
    "ImpactLevel",
    "EffortEstimate",
    "Opportunity",
    "OpportunityAnalyzer",
]

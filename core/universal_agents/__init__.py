# BAEL - Universal Agent Templates
# "Agents That Transcend Projects"

"""
Universal Agent Templates - Reusable agent configurations for any project.

This module provides a library of pre-built agent templates organized by team:
- Red Team: Attack & vulnerability discovery
- Blue Team: Defense & stability assurance
- Black Team: Chaos engineering & edge cases
- White Team: Ethics & safety validation
- Gold Team: Performance optimization
- Purple Team: Integration & synergy
- Green Team: Innovation & growth
- Silver Team: Documentation & knowledge

Usage:
    from core.universal_agents import AgentTemplateLibrary, AgentTeam

    library = AgentTemplateLibrary()
    template = library.get_template("vulnerability_hunter")
    deployment = await library.deploy_for_project(template.id, project_context)
"""

from .universal_agent_templates import (
    AgentTemplateLibrary,
    AgentTemplate,
    AgentTeam,
    AgentCapability,
    AgentPersonality,
    AgentDeployment,
    CapabilityLevel,
    ProjectType,
    ProjectContext,
    RiskLevel,
)

__all__ = [
    "AgentTemplateLibrary",
    "AgentTemplate",
    "AgentTeam",
    "AgentCapability",
    "AgentPersonality",
    "AgentDeployment",
    "CapabilityLevel",
    "ProjectType",
    "ProjectContext",
    "RiskLevel",
]

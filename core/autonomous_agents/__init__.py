"""
BAEL Autonomous Agents - 20+ Specialized Autonomous Agents
============================================================
Each agent operates independently with maximum capability.

"An army of specialists, each a master of their domain." — Ba'el
"""

from .agent_factory import (
    AutonomousAgentFactory,
    AgentType,
    AgentCapability,
    AgentPriority,
    AgentStatus,
    create_agent,
    deploy_agent_team,
)

from .code_architect import CodeArchitectAgent
from .security_auditor import SecurityAuditorAgent
from .performance_optimizer import PerformanceOptimizerAgent
from .documentation_generator import DocumentationGeneratorAgent
from .test_generator import TestGeneratorAgent
from .refactoring_agent import RefactoringAgent
from .dependency_analyzer import DependencyAnalyzerAgent
from .api_designer import APIDesignerAgent
from .database_optimizer import DatabaseOptimizerAgent
from .frontend_genius import FrontendGeniusAgent
from .devops_automation import DevOpsAutomationAgent
from .cost_optimizer import CostOptimizerAgent
from .error_hunter import ErrorHunterAgent
from .code_reviewer import CodeReviewerAgent
from .integration_agent import IntegrationAgent
from .monitoring_agent import MonitoringAgent
from .scaling_agent import ScalingAgent
from .migration_agent import MigrationAgent
from .compliance_agent import ComplianceAgent
from .innovation_agent import InnovationAgent

__all__ = [
    # Factory
    "AutonomousAgentFactory",
    "AgentType",
    "AgentCapability",
    "AgentPriority",
    "AgentStatus",
    "create_agent",
    "deploy_agent_team",
    # Agents
    "CodeArchitectAgent",
    "SecurityAuditorAgent",
    "PerformanceOptimizerAgent",
    "DocumentationGeneratorAgent",
    "TestGeneratorAgent",
    "RefactoringAgent",
    "DependencyAnalyzerAgent",
    "APIDesignerAgent",
    "DatabaseOptimizerAgent",
    "FrontendGeniusAgent",
    "DevOpsAutomationAgent",
    "CostOptimizerAgent",
    "ErrorHunterAgent",
    "CodeReviewerAgent",
    "IntegrationAgent",
    "MonitoringAgent",
    "ScalingAgent",
    "MigrationAgent",
    "ComplianceAgent",
    "InnovationAgent",
]

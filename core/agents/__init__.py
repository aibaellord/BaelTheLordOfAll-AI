"""
BAEL Advanced Agents Module

This module contains advanced autonomous agents with:
- Self-healing capabilities
- Continuous learning
- Pattern recognition
- Multi-agent collaboration
"""

from core.agents.advanced_autonomous import (AdvancedAutonomousAgent,
                                             AgentCapability, AgentState,
                                             AgentSwarm, ExecutionMemory,
                                             ExecutionStrategy,
                                             LearningPattern, RecoveryStrategy)

__all__ = [
    'AdvancedAutonomousAgent',
    'AgentSwarm',
    'AgentCapability',
    'AgentState',
    'ExecutionStrategy',
    'RecoveryStrategy',
    'ExecutionMemory',
    'LearningPattern'
]

__version__ = '4.0.0'

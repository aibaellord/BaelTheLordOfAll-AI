"""
BAEL Multi-Agent Coordination Module

Enables swarm intelligence and multi-agent collaboration.
"""

from core.coordination.multi_agent import (AgentBid, AgentRole, ConsensusVote,
                                           CoordinatedTask, CoordinationEngine,
                                           CoordinationStrategy, TaskPriority)

__all__ = [
    'CoordinationEngine',
    'CoordinatedTask',
    'CoordinationStrategy',
    'AgentRole',
    'TaskPriority',
    'AgentBid',
    'ConsensusVote'
]

__version__ = '4.0.0'

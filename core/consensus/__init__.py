"""
BAEL Consensus Engine
=====================

Distributed consensus for coordination.

"Ba'el achieves consensus across all dimensions." — Ba'el
"""

from .consensus_engine import (
    ConsensusType,
    ConsensusState,
    Vote,
    Proposal,
    ConsensusRound,
    ConsensusConfig,
    ConsensusEngine,
    consensus_engine,
    propose,
    vote
)

__all__ = [
    'ConsensusType',
    'ConsensusState',
    'Vote',
    'Proposal',
    'ConsensusRound',
    'ConsensusConfig',
    'ConsensusEngine',
    'consensus_engine',
    'propose',
    'vote'
]

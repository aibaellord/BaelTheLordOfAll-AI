"""
🧬 COGNITIVE ARCHITECTURE UNIFIER 🧬
====================================
Unifies all cognitive systems.

Features:
- Global workspace
- Memory integration
- Attention control
- Learning coordination
"""

from .architecture_core import (
    CognitiveModule,
    ModuleType,
    CognitiveState,
    ProcessingLevel,
    CognitiveArchitecture,
)

from .global_workspace import (
    WorkspaceItem,
    GlobalWorkspace,
    BroadcastEvent,
    CoalitionBuilder,
    AttentionController,
)

from .memory_integration import (
    MemoryType,
    MemoryItem,
    WorkingMemory,
    LongTermMemory,
    EpisodicMemory,
    SemanticMemory,
    UnifiedMemory,
)

from .cognitive_control import (
    Goal,
    Plan,
    ExecutiveController,
    MetaCognition,
    CognitiveScheduler,
)

from .learning_integration import (
    LearningEvent,
    LearningType,
    LearningCoordinator,
    KnowledgeConsolidator,
    TransferLearner,
)

__all__ = [
    # Architecture Core
    'CognitiveModule',
    'ModuleType',
    'CognitiveState',
    'ProcessingLevel',
    'CognitiveArchitecture',

    # Global Workspace
    'WorkspaceItem',
    'GlobalWorkspace',
    'BroadcastEvent',
    'CoalitionBuilder',
    'AttentionController',

    # Memory Integration
    'MemoryType',
    'MemoryItem',
    'WorkingMemory',
    'LongTermMemory',
    'EpisodicMemory',
    'SemanticMemory',
    'UnifiedMemory',

    # Cognitive Control
    'Goal',
    'Plan',
    'ExecutiveController',
    'MetaCognition',
    'CognitiveScheduler',

    # Learning Integration
    'LearningEvent',
    'LearningType',
    'LearningCoordinator',
    'KnowledgeConsolidator',
    'TransferLearner',
]

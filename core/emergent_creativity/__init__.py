"""
🎨 EMERGENT CREATIVITY ENGINE 🎨
=================================
Novel solution generation.

Features:
- Creative ideation
- Novelty search
- Conceptual blending
- Divergent thinking
"""

from .creativity_core import (
    Idea,
    IdeaType,
    CreativeSpace,
    NoveltyMetric,
    CreativityMode,
)

from .ideation import (
    IdeaGenerator,
    BrainstormSession,
    MindMap,
    AssociativeNetwork,
)

from .conceptual_blending import (
    Concept,
    ConceptualSpace,
    Blend,
    ConceptualBlender,
    AnalogicalMapper,
)

from .novelty_search import (
    NoveltyArchive,
    BehaviorDescriptor,
    NoveltySearcher,
    QualityDiversity,
)

from .creative_synthesis import (
    CreativeConstraint,
    SolutionSpace,
    CreativeSynthesizer,
    DivergentThinker,
)

__all__ = [
    # Creativity Core
    'Idea',
    'IdeaType',
    'CreativeSpace',
    'NoveltyMetric',
    'CreativityMode',

    # Ideation
    'IdeaGenerator',
    'BrainstormSession',
    'MindMap',
    'AssociativeNetwork',

    # Conceptual Blending
    'Concept',
    'ConceptualSpace',
    'Blend',
    'ConceptualBlender',
    'AnalogicalMapper',

    # Novelty Search
    'NoveltyArchive',
    'BehaviorDescriptor',
    'NoveltySearcher',
    'QualityDiversity',

    # Creative Synthesis
    'CreativeConstraint',
    'SolutionSpace',
    'CreativeSynthesizer',
    'DivergentThinker',
]

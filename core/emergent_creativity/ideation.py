"""
🎨 IDEATION 🎨
==============
Idea generation.

Features:
- Brainstorming
- Mind mapping
- Associative thinking
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from datetime import datetime
import uuid
import random

from .creativity_core import Idea, IdeaType, CreativityMode


@dataclass
class MindMapNode:
    """Node in a mind map"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    content: str = ""
    parent_id: Optional[str] = None
    children: List['MindMapNode'] = field(default_factory=list)

    # Position (for visualization)
    x: float = 0.0
    y: float = 0.0

    # Style
    color: str = ""
    size: float = 1.0


class MindMap:
    """
    Mind mapping for idea organization.
    """

    def __init__(self, central_topic: str = ""):
        self.central_topic = central_topic

        self.root = MindMapNode(content=central_topic)
        self.nodes: Dict[str, MindMapNode] = {self.root.id: self.root}

    def add_branch(self, parent_id: str, content: str) -> MindMapNode:
        """Add branch to mind map"""
        if parent_id not in self.nodes:
            parent_id = self.root.id

        node = MindMapNode(
            content=content,
            parent_id=parent_id
        )

        self.nodes[parent_id].children.append(node)
        self.nodes[node.id] = node

        return node

    def get_branches(self, node_id: str = None) -> List[MindMapNode]:
        """Get all branches from a node"""
        node_id = node_id or self.root.id
        if node_id not in self.nodes:
            return []
        return self.nodes[node_id].children

    def get_path_to_root(self, node_id: str) -> List[str]:
        """Get path from node to root"""
        path = []
        current = self.nodes.get(node_id)

        while current:
            path.append(current.content)
            if current.parent_id:
                current = self.nodes.get(current.parent_id)
            else:
                break

        return list(reversed(path))

    def find_related(self, keyword: str) -> List[MindMapNode]:
        """Find nodes related to keyword"""
        related = []
        keyword_lower = keyword.lower()

        for node in self.nodes.values():
            if keyword_lower in node.content.lower():
                related.append(node)

        return related

    def to_ideas(self) -> List[Idea]:
        """Convert mind map to ideas"""
        ideas = []

        for node in self.nodes.values():
            if node.id == self.root.id:
                continue

            path = self.get_path_to_root(node.id)

            idea = Idea(
                content=node.content,
                description=" > ".join(path),
                idea_type=IdeaType.CONCEPT,
                tags=path[:-1]  # Use path as tags
            )
            ideas.append(idea)

        return ideas


class AssociativeNetwork:
    """
    Network of conceptual associations.
    """

    def __init__(self):
        self.concepts: Dict[str, Set[str]] = {}  # concept -> associated concepts
        self.association_strength: Dict[Tuple[str, str], float] = {}

    def add_concept(self, concept: str):
        """Add concept to network"""
        if concept not in self.concepts:
            self.concepts[concept] = set()

    def add_association(self, concept1: str, concept2: str, strength: float = 1.0):
        """Add association between concepts"""
        self.add_concept(concept1)
        self.add_concept(concept2)

        self.concepts[concept1].add(concept2)
        self.concepts[concept2].add(concept1)

        key = tuple(sorted([concept1, concept2]))
        self.association_strength[key] = strength

    def get_associations(self, concept: str) -> List[Tuple[str, float]]:
        """Get associated concepts with strengths"""
        if concept not in self.concepts:
            return []

        associations = []
        for assoc in self.concepts[concept]:
            key = tuple(sorted([concept, assoc]))
            strength = self.association_strength.get(key, 1.0)
            associations.append((assoc, strength))

        return sorted(associations, key=lambda x: x[1], reverse=True)

    def find_path(
        self,
        start: str,
        end: str,
        max_length: int = 5
    ) -> List[str]:
        """Find association path between concepts"""
        if start not in self.concepts or end not in self.concepts:
            return []

        if start == end:
            return [start]

        # BFS
        visited = {start}
        queue = [(start, [start])]

        while queue:
            current, path = queue.pop(0)

            if len(path) > max_length:
                continue

            for neighbor in self.concepts.get(current, set()):
                if neighbor == end:
                    return path + [neighbor]

                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))

        return []

    def get_distant_associations(self, concept: str, depth: int = 2) -> Set[str]:
        """Get distant (multi-hop) associations"""
        if concept not in self.concepts:
            return set()

        current = {concept}
        all_found = {concept}

        for _ in range(depth):
            next_level = set()
            for c in current:
                for assoc in self.concepts.get(c, set()):
                    if assoc not in all_found:
                        next_level.add(assoc)
                        all_found.add(assoc)
            current = next_level

        return all_found - {concept}

    def suggest_novel_connection(self, concept: str) -> Optional[Tuple[str, str]]:
        """Suggest novel connection between distant concepts"""
        distant = self.get_distant_associations(concept, depth=3)
        direct = self.concepts.get(concept, set())

        # Find distant concepts not directly connected
        novel_targets = distant - direct

        if not novel_targets:
            return None

        # Return random novel connection
        target = random.choice(list(novel_targets))
        return (concept, target)


@dataclass
class BrainstormSession:
    """A brainstorming session"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    topic: str = ""
    mode: CreativityMode = CreativityMode.DIVERGENT

    ideas: List[Idea] = field(default_factory=list)

    # Session state
    started_at: datetime = field(default_factory=datetime.now)
    ended_at: Optional[datetime] = None

    # Constraints
    time_limit_seconds: Optional[int] = None
    idea_quota: Optional[int] = None

    def add_idea(self, idea: Idea):
        """Add idea to session"""
        idea.domain = self.topic
        self.ideas.append(idea)

    def is_complete(self) -> bool:
        """Check if session is complete"""
        if self.ended_at:
            return True

        if self.idea_quota and len(self.ideas) >= self.idea_quota:
            return True

        if self.time_limit_seconds:
            elapsed = (datetime.now() - self.started_at).total_seconds()
            if elapsed >= self.time_limit_seconds:
                return True

        return False

    def end_session(self):
        """End the session"""
        self.ended_at = datetime.now()


class IdeaGenerator:
    """
    Generates ideas using various techniques.
    """

    def __init__(self):
        self.associative_network = AssociativeNetwork()
        self.techniques: List[Callable[[str], List[Idea]]] = []

        # Modifiers for transformation
        self.modifiers = [
            "larger", "smaller", "inverted", "combined",
            "simplified", "expanded", "reversed", "accelerated",
            "slowed", "merged", "split", "rotated"
        ]

        # Question prompts
        self.prompts = [
            "What if we {}?",
            "How might we {}?",
            "What would happen if {}?",
            "Can we {} this?",
            "Why not {}?"
        ]

    def add_technique(self, technique: Callable[[str], List[Idea]]):
        """Add generation technique"""
        self.techniques.append(technique)

    def generate(
        self,
        topic: str,
        n_ideas: int = 10,
        mode: CreativityMode = CreativityMode.DIVERGENT
    ) -> List[Idea]:
        """Generate ideas on topic"""
        ideas = []

        if mode == CreativityMode.DIVERGENT:
            ideas.extend(self._divergent_generation(topic, n_ideas))
        elif mode == CreativityMode.LATERAL:
            ideas.extend(self._lateral_generation(topic, n_ideas))
        elif mode == CreativityMode.ASSOCIATIVE:
            ideas.extend(self._associative_generation(topic, n_ideas))
        elif mode == CreativityMode.RANDOM:
            ideas.extend(self._random_generation(topic, n_ideas))
        else:
            ideas.extend(self._divergent_generation(topic, n_ideas))

        # Apply custom techniques
        for technique in self.techniques:
            try:
                ideas.extend(technique(topic))
            except Exception:
                pass

        return ideas[:n_ideas]

    def _divergent_generation(self, topic: str, n: int) -> List[Idea]:
        """Divergent thinking: generate many variations"""
        ideas = []

        for modifier in self.modifiers[:n]:
            idea = Idea(
                content=f"{modifier} {topic}",
                description=f"What if {topic} was {modifier}?",
                idea_type=IdeaType.TRANSFORMATION,
                generation_method="divergent"
            )
            ideas.append(idea)

        return ideas

    def _lateral_generation(self, topic: str, n: int) -> List[Idea]:
        """Lateral thinking: sideways jumps"""
        ideas = []

        for prompt in self.prompts[:n]:
            idea = Idea(
                content=prompt.format(topic),
                description=f"Lateral question about {topic}",
                idea_type=IdeaType.CONCEPT,
                generation_method="lateral"
            )
            ideas.append(idea)

        return ideas

    def _associative_generation(self, topic: str, n: int) -> List[Idea]:
        """Associative thinking: follow connections"""
        ideas = []

        associations = self.associative_network.get_associations(topic)

        for assoc, strength in associations[:n]:
            idea = Idea(
                content=f"{topic} + {assoc}",
                description=f"Combining {topic} with associated concept {assoc}",
                idea_type=IdeaType.COMBINATION,
                generation_method="associative",
                quality=strength
            )
            ideas.append(idea)

        # If not enough, suggest novel connections
        while len(ideas) < n:
            novel = self.associative_network.suggest_novel_connection(topic)
            if novel:
                idea = Idea(
                    content=f"{novel[0]} <-> {novel[1]}",
                    description="Novel connection",
                    idea_type=IdeaType.COMBINATION,
                    generation_method="associative_novel"
                )
                ideas.append(idea)
            else:
                break

        return ideas

    def _random_generation(self, topic: str, n: int) -> List[Idea]:
        """Random exploration"""
        ideas = []

        # Random combinations
        all_concepts = list(self.associative_network.concepts.keys())

        for _ in range(n):
            if all_concepts:
                random_concept = random.choice(all_concepts)
                modifier = random.choice(self.modifiers)

                idea = Idea(
                    content=f"{modifier} {topic} with {random_concept}",
                    description="Random combination",
                    idea_type=IdeaType.COMBINATION,
                    generation_method="random",
                    novelty=0.8  # High novelty for random
                )
            else:
                modifier = random.choice(self.modifiers)
                idea = Idea(
                    content=f"{modifier} {topic}",
                    description="Random transformation",
                    idea_type=IdeaType.TRANSFORMATION,
                    generation_method="random",
                    novelty=0.5
                )
            ideas.append(idea)

        return ideas

    def run_session(
        self,
        topic: str,
        time_limit: int = None,
        idea_quota: int = 20
    ) -> BrainstormSession:
        """Run brainstorming session"""
        session = BrainstormSession(
            topic=topic,
            time_limit_seconds=time_limit,
            idea_quota=idea_quota
        )

        # Generate ideas in multiple modes
        modes = [
            CreativityMode.DIVERGENT,
            CreativityMode.LATERAL,
            CreativityMode.ASSOCIATIVE,
            CreativityMode.RANDOM
        ]

        ideas_per_mode = (idea_quota // len(modes)) + 1

        for mode in modes:
            session.mode = mode
            ideas = self.generate(topic, ideas_per_mode, mode)

            for idea in ideas:
                if not session.is_complete():
                    session.add_idea(idea)

        session.end_session()
        return session


# Export all
__all__ = [
    'MindMapNode',
    'MindMap',
    'AssociativeNetwork',
    'BrainstormSession',
    'IdeaGenerator',
]

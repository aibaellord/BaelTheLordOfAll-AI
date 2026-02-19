"""
BAEL Pattern Learner
=====================

Learn reusable patterns from code and projects.
Enables knowledge extraction and application.

Features:
- Pattern extraction
- Pattern classification
- Pattern storage
- Pattern matching
- Pattern recommendation
"""

import asyncio
import hashlib
import logging
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class PatternCategory(Enum):
    """Pattern categories."""
    DESIGN = "design"              # Design patterns
    ARCHITECTURE = "architecture"  # Architecture patterns
    CODE = "code"                  # Code patterns/idioms
    API = "api"                    # API patterns
    ERROR_HANDLING = "error_handling"
    TESTING = "testing"
    DOCUMENTATION = "documentation"
    PERFORMANCE = "performance"
    SECURITY = "security"


class PatternType(Enum):
    """Pattern types."""
    STRUCTURAL = "structural"      # How things are organized
    BEHAVIORAL = "behavioral"      # How things behave
    CREATIONAL = "creational"      # How things are created
    IDIOM = "idiom"               # Language-specific patterns


@dataclass
class PatternExample:
    """An example of a pattern."""
    code: str
    source: str
    language: str = "python"
    description: str = ""
    quality_score: float = 0.8


@dataclass
class LearnedPattern:
    """A learned pattern."""
    id: str
    name: str
    description: str

    # Classification
    category: PatternCategory = PatternCategory.CODE
    type: PatternType = PatternType.BEHAVIORAL

    # Pattern definition
    template: str = ""
    signature: str = ""  # Pattern signature for matching
    variables: List[str] = field(default_factory=list)

    # Examples
    examples: List[PatternExample] = field(default_factory=list)

    # Usage stats
    occurrences: int = 0
    projects_using: int = 0

    # Confidence
    confidence: float = 0.0

    # Metadata
    languages: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    learned_at: datetime = field(default_factory=datetime.now)
    last_used: Optional[datetime] = None


@dataclass
class PatternMatch:
    """A pattern match in code."""
    pattern_id: str
    pattern_name: str
    confidence: float

    # Location
    file: str
    line_start: int
    line_end: int

    # Matched code
    code_snippet: str
    variables: Dict[str, str] = field(default_factory=dict)


@dataclass
class LearningSession:
    """A pattern learning session."""
    id: str
    started_at: datetime = field(default_factory=datetime.now)
    ended_at: Optional[datetime] = None

    # Progress
    files_processed: int = 0
    patterns_extracted: int = 0
    patterns_updated: int = 0

    # Results
    new_patterns: List[str] = field(default_factory=list)


class PatternLearner:
    """
    Pattern learning system for BAEL.
    """

    def __init__(self):
        # Pattern storage
        self.patterns: Dict[str, LearnedPattern] = {}

        # Pattern signatures for matching
        self._signatures: Dict[str, str] = {}

        # Known patterns
        self._known_patterns = self._load_known_patterns()

        # Sessions
        self.sessions: List[LearningSession] = []
        self._current_session: Optional[LearningSession] = None

        # Stats
        self.stats = {
            "patterns_learned": 0,
            "patterns_matched": 0,
            "learning_sessions": 0,
        }

    def _load_known_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Load known pattern definitions."""
        return {
            # Design patterns
            "singleton": {
                "name": "Singleton",
                "category": PatternCategory.DESIGN,
                "type": PatternType.CREATIONAL,
                "signature": r"_instance\s*=\s*None.*@classmethod.*def\s+get_instance",
                "description": "Ensures only one instance exists",
            },
            "factory": {
                "name": "Factory",
                "category": PatternCategory.DESIGN,
                "type": PatternType.CREATIONAL,
                "signature": r"def\s+create_\w+|class\s+\w*Factory",
                "description": "Creates objects without specifying exact class",
            },
            "decorator": {
                "name": "Decorator",
                "category": PatternCategory.DESIGN,
                "type": PatternType.STRUCTURAL,
                "signature": r"def\s+\w+\s*\(\s*func\s*\).*def\s+wrapper",
                "description": "Adds behavior to objects dynamically",
            },
            "observer": {
                "name": "Observer",
                "category": PatternCategory.DESIGN,
                "type": PatternType.BEHAVIORAL,
                "signature": r"add_observer|notify_observers|subscribe|on_\w+",
                "description": "Notifies dependents of state changes",
            },

            # Code patterns
            "context_manager": {
                "name": "Context Manager",
                "category": PatternCategory.CODE,
                "type": PatternType.IDIOM,
                "signature": r"def\s+__enter__|def\s+__exit__|@contextmanager",
                "description": "Resource management with with statement",
            },
            "retry_pattern": {
                "name": "Retry Pattern",
                "category": PatternCategory.ERROR_HANDLING,
                "type": PatternType.BEHAVIORAL,
                "signature": r"for\s+\w+\s+in\s+range.*try.*except.*continue|@retry",
                "description": "Retries failed operations",
            },
            "circuit_breaker": {
                "name": "Circuit Breaker",
                "category": PatternCategory.ERROR_HANDLING,
                "type": PatternType.BEHAVIORAL,
                "signature": r"failure_count|circuit_open|circuit_breaker",
                "description": "Prevents cascading failures",
            },

            # API patterns
            "pagination": {
                "name": "Pagination",
                "category": PatternCategory.API,
                "type": PatternType.BEHAVIORAL,
                "signature": r"page|limit|offset|cursor|next_page",
                "description": "Handles paginated data",
            },
            "rate_limiting": {
                "name": "Rate Limiting",
                "category": PatternCategory.API,
                "type": PatternType.BEHAVIORAL,
                "signature": r"rate_limit|throttle|tokens_per|bucket",
                "description": "Controls request rate",
            },
        }

    def start_session(self) -> LearningSession:
        """Start a new learning session."""
        session_id = hashlib.md5(
            str(datetime.now().timestamp()).encode()
        ).hexdigest()[:8]

        session = LearningSession(id=session_id)
        self._current_session = session
        self.sessions.append(session)
        self.stats["learning_sessions"] += 1

        logger.info(f"Started learning session: {session_id}")

        return session

    def end_session(self) -> Optional[LearningSession]:
        """End current learning session."""
        if self._current_session:
            self._current_session.ended_at = datetime.now()
            session = self._current_session
            self._current_session = None
            return session
        return None

    async def learn_from_code(
        self,
        code: str,
        source: str = "",
        language: str = "python",
    ) -> List[LearnedPattern]:
        """
        Learn patterns from code.

        Args:
            code: Source code to learn from
            source: Source file/location
            language: Programming language

        Returns:
            List of learned patterns
        """
        learned = []

        # Match known patterns
        for pattern_id, pattern_def in self._known_patterns.items():
            signature = pattern_def["signature"]

            if re.search(signature, code, re.DOTALL | re.IGNORECASE):
                pattern = self._get_or_create_pattern(pattern_id, pattern_def)

                # Add example
                example = PatternExample(
                    code=self._extract_pattern_code(code, signature),
                    source=source,
                    language=language,
                )
                pattern.examples.append(example)

                # Update stats
                pattern.occurrences += 1
                pattern.last_used = datetime.now()

                learned.append(pattern)

        # Extract new patterns (code idioms)
        new_patterns = await self._extract_new_patterns(code, source, language)
        learned.extend(new_patterns)

        # Update session
        if self._current_session:
            self._current_session.files_processed += 1
            self._current_session.patterns_extracted += len(learned)

        return learned

    def _get_or_create_pattern(
        self,
        pattern_id: str,
        pattern_def: Dict[str, Any],
    ) -> LearnedPattern:
        """Get existing pattern or create new one."""
        if pattern_id in self.patterns:
            return self.patterns[pattern_id]

        pattern = LearnedPattern(
            id=pattern_id,
            name=pattern_def["name"],
            description=pattern_def.get("description", ""),
            category=pattern_def.get("category", PatternCategory.CODE),
            type=pattern_def.get("type", PatternType.BEHAVIORAL),
            signature=pattern_def.get("signature", ""),
            confidence=0.9,
        )

        self.patterns[pattern_id] = pattern
        self.stats["patterns_learned"] += 1

        if self._current_session:
            self._current_session.new_patterns.append(pattern_id)

        return pattern

    def _extract_pattern_code(self, code: str, signature: str) -> str:
        """Extract code matching pattern signature."""
        match = re.search(signature, code, re.DOTALL | re.IGNORECASE)
        if match:
            # Get surrounding context
            start = max(0, match.start() - 100)
            end = min(len(code), match.end() + 200)

            # Find line boundaries
            snippet = code[start:end]
            lines = snippet.split("\n")

            # Return first 20 lines max
            return "\n".join(lines[:20])

        return ""

    async def _extract_new_patterns(
        self,
        code: str,
        source: str,
        language: str,
    ) -> List[LearnedPattern]:
        """Extract new patterns from code."""
        new_patterns = []

        # Common code idioms
        idiom_patterns = [
            # List comprehension
            (r"\[\s*\w+\s+for\s+\w+\s+in\s+\w+(?:\s+if\s+[^\]]+)?\s*\]",
             "list_comprehension", "List Comprehension"),

            # Dictionary comprehension
            (r"\{\s*\w+\s*:\s*\w+\s+for\s+\w+\s+in\s+\w+\s*\}",
             "dict_comprehension", "Dictionary Comprehension"),

            # Generator expression
            (r"\(\s*\w+\s+for\s+\w+\s+in\s+\w+\s*\)",
             "generator_expression", "Generator Expression"),

            # Async/await
            (r"async\s+def\s+\w+.*await\s+",
             "async_pattern", "Async/Await Pattern"),

            # Property decorator
            (r"@property\s+def\s+\w+",
             "property_pattern", "Property Pattern"),
        ]

        for regex, pattern_id, name in idiom_patterns:
            if re.search(regex, code, re.DOTALL):
                if pattern_id not in self.patterns:
                    pattern = LearnedPattern(
                        id=pattern_id,
                        name=name,
                        description=f"Code idiom: {name}",
                        category=PatternCategory.CODE,
                        type=PatternType.IDIOM,
                        signature=regex,
                        confidence=0.7,
                        languages=[language],
                    )

                    pattern.examples.append(PatternExample(
                        code=self._extract_pattern_code(code, regex),
                        source=source,
                        language=language,
                    ))

                    self.patterns[pattern_id] = pattern
                    new_patterns.append(pattern)
                    self.stats["patterns_learned"] += 1

        return new_patterns

    def find_patterns(
        self,
        code: str,
        min_confidence: float = 0.5,
    ) -> List[PatternMatch]:
        """
        Find patterns in code.

        Args:
            code: Code to search
            min_confidence: Minimum confidence threshold

        Returns:
            List of pattern matches
        """
        matches = []

        lines = code.split("\n")

        for pattern in self.patterns.values():
            if pattern.confidence < min_confidence:
                continue

            if not pattern.signature:
                continue

            for match in re.finditer(pattern.signature, code, re.DOTALL | re.IGNORECASE):
                # Find line numbers
                line_start = code[:match.start()].count("\n") + 1
                line_end = code[:match.end()].count("\n") + 1

                matches.append(PatternMatch(
                    pattern_id=pattern.id,
                    pattern_name=pattern.name,
                    confidence=pattern.confidence,
                    file="",
                    line_start=line_start,
                    line_end=line_end,
                    code_snippet=match.group()[:200],
                ))

                self.stats["patterns_matched"] += 1

        return matches

    def recommend_patterns(
        self,
        context: Dict[str, Any],
        limit: int = 5,
    ) -> List[LearnedPattern]:
        """
        Recommend patterns based on context.

        Args:
            context: Context for recommendation
            limit: Maximum recommendations

        Returns:
            Recommended patterns
        """
        recommendations = []

        # Get context hints
        category_hint = context.get("category")
        type_hint = context.get("type")
        keywords = context.get("keywords", [])

        for pattern in self.patterns.values():
            score = pattern.confidence * 0.5

            # Category match
            if category_hint and pattern.category.value == category_hint:
                score += 0.3

            # Type match
            if type_hint and pattern.type.value == type_hint:
                score += 0.2

            # Keyword match
            for keyword in keywords:
                if keyword.lower() in pattern.name.lower():
                    score += 0.1
                if keyword.lower() in pattern.description.lower():
                    score += 0.05

            # Usage popularity
            score += min(pattern.occurrences / 100, 0.2)

            if score > 0.5:
                recommendations.append((pattern, score))

        # Sort by score
        recommendations.sort(key=lambda x: x[1], reverse=True)

        return [p for p, _ in recommendations[:limit]]

    def get_pattern(self, pattern_id: str) -> Optional[LearnedPattern]:
        """Get pattern by ID."""
        return self.patterns.get(pattern_id)

    def list_patterns(
        self,
        category: Optional[PatternCategory] = None,
        min_confidence: float = 0.0,
    ) -> List[LearnedPattern]:
        """List patterns with optional filtering."""
        patterns = list(self.patterns.values())

        if category:
            patterns = [p for p in patterns if p.category == category]

        patterns = [p for p in patterns if p.confidence >= min_confidence]

        return sorted(patterns, key=lambda p: p.occurrences, reverse=True)

    def export_patterns(self) -> Dict[str, Any]:
        """Export all patterns."""
        return {
            pattern_id: {
                "name": p.name,
                "description": p.description,
                "category": p.category.value,
                "type": p.type.value,
                "signature": p.signature,
                "confidence": p.confidence,
                "occurrences": p.occurrences,
                "examples_count": len(p.examples),
            }
            for pattern_id, p in self.patterns.items()
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get learner statistics."""
        return {
            **self.stats,
            "total_patterns": len(self.patterns),
            "high_confidence_patterns": len([
                p for p in self.patterns.values() if p.confidence >= 0.8
            ]),
        }


def demo():
    """Demonstrate pattern learner."""
    import asyncio

    print("=" * 60)
    print("BAEL Pattern Learner Demo")
    print("=" * 60)

    learner = PatternLearner()

    # Sample code with patterns
    sample_code = '''
class DatabaseConnection:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

class UserFactory:
    def create_user(self, user_type):
        if user_type == "admin":
            return AdminUser()
        return RegularUser()

# Using patterns
users = [user for user in all_users if user.is_active]

async def fetch_data():
    result = await api_client.get("/data")
    return result
'''

    # Start session
    session = learner.start_session()
    print(f"\nStarted session: {session.id}")

    # Learn from code
    async def learn():
        return await learner.learn_from_code(sample_code, "sample.py")

    patterns = asyncio.run(learn())
    print(f"\nLearned patterns ({len(patterns)}):")
    for pattern in patterns:
        print(f"  - {pattern.name} ({pattern.category.value})")

    # Find patterns
    matches = learner.find_patterns(sample_code)
    print(f"\nPattern matches ({len(matches)}):")
    for match in matches:
        print(f"  - {match.pattern_name} at line {match.line_start}")

    # Recommend patterns
    recs = learner.recommend_patterns({
        "category": "design",
        "keywords": ["factory"],
    })
    print(f"\nRecommendations ({len(recs)}):")
    for rec in recs:
        print(f"  - {rec.name}")

    # End session
    session = learner.end_session()
    print(f"\nSession ended: {session.patterns_extracted} patterns extracted")

    print(f"\nStats: {learner.get_stats()}")


if __name__ == "__main__":
    demo()

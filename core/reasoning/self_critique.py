"""
BAEL Self Critique
===================

Self-evaluation and improvement capabilities.
Enables AI to critique and refine its own outputs.

Features:
- Output evaluation
- Error detection
- Improvement suggestions
- Iterative refinement
- Quality scoring
"""

import asyncio
import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class CritiqueType(Enum):
    """Types of critique."""
    ACCURACY = "accuracy"  # Factual correctness
    COMPLETENESS = "completeness"  # Coverage
    CLARITY = "clarity"  # Understandability
    COHERENCE = "coherence"  # Logical flow
    RELEVANCE = "relevance"  # On-topic
    EFFICIENCY = "efficiency"  # Optimal solution
    SAFETY = "safety"  # Potential issues
    STYLE = "style"  # Format/presentation


class Severity(Enum):
    """Issue severity levels."""
    CRITICAL = 4
    MAJOR = 3
    MINOR = 2
    SUGGESTION = 1


@dataclass
class Issue:
    """An identified issue in the output."""
    id: str
    critique_type: CritiqueType
    severity: Severity

    # Description
    description: str
    location: Optional[str] = None  # Where in the output

    # Context
    evidence: str = ""

    # Fix
    suggested_fix: Optional[str] = None

    # Metadata
    detected_at: datetime = field(default_factory=datetime.now)


@dataclass
class ImprovementSuggestion:
    """A suggestion for improvement."""
    id: str
    priority: int  # 1-10, higher is more important

    # Suggestion
    title: str
    description: str

    # Implementation
    implementation_hint: str = ""
    estimated_impact: float = 0.5  # 0-1

    # Related issues
    addresses_issues: List[str] = field(default_factory=list)


@dataclass
class Critique:
    """A complete critique of an output."""
    id: str
    target: str  # What was critiqued

    # Issues found
    issues: List[Issue] = field(default_factory=list)

    # Suggestions
    suggestions: List[ImprovementSuggestion] = field(default_factory=list)

    # Scores
    scores: Dict[CritiqueType, float] = field(default_factory=dict)
    overall_score: float = 0.0

    # Verdict
    passes: bool = False
    needs_revision: bool = True

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    critique_version: int = 1

    def add_issue(self, issue: Issue) -> None:
        """Add an issue."""
        self.issues.append(issue)
        self._update_verdict()

    def add_suggestion(self, suggestion: ImprovementSuggestion) -> None:
        """Add a suggestion."""
        self.suggestions.append(suggestion)

    def _update_verdict(self) -> None:
        """Update pass/fail verdict."""
        critical_issues = sum(1 for i in self.issues if i.severity == Severity.CRITICAL)
        major_issues = sum(1 for i in self.issues if i.severity == Severity.MAJOR)

        self.passes = critical_issues == 0 and major_issues <= 2
        self.needs_revision = not self.passes or major_issues > 0


class SelfCritique:
    """
    Self-critique system for BAEL.

    Enables self-evaluation and improvement.
    """

    def __init__(self):
        # Critique history
        self._critiques: Dict[str, Critique] = {}

        # Revision history
        self._revisions: Dict[str, List[str]] = {}  # original -> [revisions]

        # Criteria weights
        self._weights = {
            CritiqueType.ACCURACY: 1.0,
            CritiqueType.COMPLETENESS: 0.8,
            CritiqueType.CLARITY: 0.7,
            CritiqueType.COHERENCE: 0.7,
            CritiqueType.RELEVANCE: 0.9,
            CritiqueType.EFFICIENCY: 0.6,
            CritiqueType.SAFETY: 1.0,
            CritiqueType.STYLE: 0.3,
        }

        # Stats
        self.stats = {
            "critiques_performed": 0,
            "issues_found": 0,
            "revisions_made": 0,
        }

    async def critique(
        self,
        output: str,
        context: Optional[Dict[str, Any]] = None,
        criteria: Optional[List[CritiqueType]] = None,
    ) -> Critique:
        """
        Critique an output.

        Args:
            output: Output to critique
            context: Additional context
            criteria: Specific criteria to evaluate

        Returns:
            Critique result
        """
        critique_id = hashlib.md5(
            f"{output[:100]}:{datetime.now()}".encode()
        ).hexdigest()[:12]

        criteria = criteria or list(CritiqueType)
        context = context or {}

        critique = Critique(
            id=critique_id,
            target=output,
        )

        # Evaluate each criterion
        for criterion in criteria:
            score, issues = await self._evaluate_criterion(output, criterion, context)
            critique.scores[criterion] = score

            for issue in issues:
                critique.add_issue(issue)

        # Calculate overall score
        critique.overall_score = self._calculate_overall_score(critique.scores)

        # Generate suggestions
        suggestions = await self._generate_suggestions(critique)
        for suggestion in suggestions:
            critique.add_suggestion(suggestion)

        self._critiques[critique_id] = critique
        self.stats["critiques_performed"] += 1
        self.stats["issues_found"] += len(critique.issues)

        logger.info(f"Critique {critique_id}: score={critique.overall_score:.2f}, issues={len(critique.issues)}")

        return critique

    async def _evaluate_criterion(
        self,
        output: str,
        criterion: CritiqueType,
        context: Dict[str, Any],
    ) -> Tuple[float, List[Issue]]:
        """Evaluate a specific criterion."""
        issues = []
        score = 1.0

        if criterion == CritiqueType.ACCURACY:
            # Check for potential inaccuracies
            if "definitely" in output.lower() and len(output) < 100:
                issues.append(Issue(
                    id=f"acc_{len(issues)}",
                    critique_type=criterion,
                    severity=Severity.MINOR,
                    description="Strong certainty claims may need verification",
                    evidence="Use of 'definitely' without detailed support",
                ))
                score -= 0.1

        elif criterion == CritiqueType.COMPLETENESS:
            # Check for completeness indicators
            expected_sections = context.get("expected_sections", [])
            for section in expected_sections:
                if section.lower() not in output.lower():
                    issues.append(Issue(
                        id=f"comp_{len(issues)}",
                        critique_type=criterion,
                        severity=Severity.MAJOR,
                        description=f"Missing expected section: {section}",
                        suggested_fix=f"Add section covering {section}",
                    ))
                    score -= 0.2

        elif criterion == CritiqueType.CLARITY:
            # Check for clarity issues
            sentences = output.split('.')
            long_sentences = [s for s in sentences if len(s.split()) > 40]

            if long_sentences:
                issues.append(Issue(
                    id=f"clar_{len(issues)}",
                    critique_type=criterion,
                    severity=Severity.MINOR,
                    description="Some sentences are too long",
                    location=f"{len(long_sentences)} sentences > 40 words",
                    suggested_fix="Break long sentences into shorter ones",
                ))
                score -= 0.05 * len(long_sentences)

        elif criterion == CritiqueType.COHERENCE:
            # Check logical flow
            if output.count('\n\n') < 2 and len(output) > 500:
                issues.append(Issue(
                    id=f"coh_{len(issues)}",
                    critique_type=criterion,
                    severity=Severity.MINOR,
                    description="Output lacks paragraph breaks",
                    suggested_fix="Add paragraph breaks between ideas",
                ))
                score -= 0.1

        elif criterion == CritiqueType.RELEVANCE:
            # Check relevance to query
            query = context.get("query", "")
            if query:
                query_words = set(query.lower().split())
                output_words = set(output.lower().split())
                overlap = len(query_words & output_words) / len(query_words) if query_words else 1

                if overlap < 0.3:
                    issues.append(Issue(
                        id=f"rel_{len(issues)}",
                        critique_type=criterion,
                        severity=Severity.MAJOR,
                        description="Output may not address the query",
                        evidence=f"Low keyword overlap: {overlap:.0%}",
                    ))
                    score -= 0.3

        elif criterion == CritiqueType.EFFICIENCY:
            # Check for redundancy
            words = output.lower().split()
            word_count = len(words)
            unique_ratio = len(set(words)) / word_count if word_count else 1

            if unique_ratio < 0.4:
                issues.append(Issue(
                    id=f"eff_{len(issues)}",
                    critique_type=criterion,
                    severity=Severity.MINOR,
                    description="High word repetition detected",
                    evidence=f"Unique word ratio: {unique_ratio:.0%}",
                    suggested_fix="Reduce repetition and be more concise",
                ))
                score -= 0.15

        elif criterion == CritiqueType.SAFETY:
            # Check for unsafe content patterns
            unsafe_patterns = ["password", "api_key", "secret", "token"]
            for pattern in unsafe_patterns:
                if pattern in output.lower() and "=" in output:
                    issues.append(Issue(
                        id=f"safe_{len(issues)}",
                        critique_type=criterion,
                        severity=Severity.CRITICAL,
                        description=f"Potential sensitive data exposure: {pattern}",
                        suggested_fix="Remove or mask sensitive values",
                    ))
                    score -= 0.5

        elif criterion == CritiqueType.STYLE:
            # Check formatting
            if output and not output[0].isupper():
                issues.append(Issue(
                    id=f"style_{len(issues)}",
                    critique_type=criterion,
                    severity=Severity.SUGGESTION,
                    description="Output should start with capital letter",
                ))
                score -= 0.05

        return max(0.0, min(1.0, score)), issues

    def _calculate_overall_score(
        self,
        scores: Dict[CritiqueType, float],
    ) -> float:
        """Calculate weighted overall score."""
        if not scores:
            return 0.0

        weighted_sum = 0.0
        weight_sum = 0.0

        for criterion, score in scores.items():
            weight = self._weights.get(criterion, 0.5)
            weighted_sum += score * weight
            weight_sum += weight

        return weighted_sum / weight_sum if weight_sum else 0.0

    async def _generate_suggestions(
        self,
        critique: Critique,
    ) -> List[ImprovementSuggestion]:
        """Generate improvement suggestions from critique."""
        suggestions = []

        # Group issues by type
        issues_by_type: Dict[CritiqueType, List[Issue]] = {}
        for issue in critique.issues:
            if issue.critique_type not in issues_by_type:
                issues_by_type[issue.critique_type] = []
            issues_by_type[issue.critique_type].append(issue)

        # Generate suggestions for each type
        for critique_type, type_issues in issues_by_type.items():
            if not type_issues:
                continue

            severity_max = max(i.severity.value for i in type_issues)

            suggestion = ImprovementSuggestion(
                id=f"sug_{critique_type.value}",
                priority=severity_max * 2,
                title=f"Improve {critique_type.value}",
                description=f"Address {len(type_issues)} {critique_type.value} issues",
                addresses_issues=[i.id for i in type_issues],
                estimated_impact=0.1 * len(type_issues),
            )

            # Add specific hints
            if type_issues[0].suggested_fix:
                suggestion.implementation_hint = type_issues[0].suggested_fix

            suggestions.append(suggestion)

        # Sort by priority
        suggestions.sort(key=lambda s: s.priority, reverse=True)

        return suggestions

    async def revise(
        self,
        original: str,
        critique: Critique,
        reviser: Optional[Callable[[str, Critique], str]] = None,
    ) -> str:
        """
        Revise output based on critique.

        Args:
            original: Original output
            critique: Critique to address
            reviser: Optional custom revision function

        Returns:
            Revised output
        """
        if reviser:
            revised = reviser(original, critique)
        else:
            revised = await self._default_revision(original, critique)

        # Track revision
        if critique.id not in self._revisions:
            self._revisions[critique.id] = []
        self._revisions[critique.id].append(revised)

        self.stats["revisions_made"] += 1

        return revised

    async def _default_revision(
        self,
        original: str,
        critique: Critique,
    ) -> str:
        """Default revision logic."""
        revised = original

        # Apply simple fixes
        for issue in critique.issues:
            if issue.suggested_fix and issue.severity.value >= Severity.MAJOR.value:
                # Placeholder for actual revision
                # In production, would use LLM to apply fix
                pass

        # Capitalize first letter
        if revised and not revised[0].isupper():
            revised = revised[0].upper() + revised[1:]

        return revised

    async def iterative_improve(
        self,
        output: str,
        context: Optional[Dict[str, Any]] = None,
        max_iterations: int = 3,
        target_score: float = 0.8,
    ) -> Tuple[str, List[Critique]]:
        """
        Iteratively improve output through critique cycles.

        Args:
            output: Initial output
            context: Critique context
            max_iterations: Maximum improvement iterations
            target_score: Target quality score

        Returns:
            (improved_output, critique_history)
        """
        current = output
        history = []

        for i in range(max_iterations):
            # Critique current version
            critique = await self.critique(current, context)
            history.append(critique)

            # Check if good enough
            if critique.overall_score >= target_score and critique.passes:
                logger.info(f"Target score reached after {i+1} iterations")
                break

            # Revise
            current = await self.revise(current, critique)

            # Prevent infinite loops on same content
            if current == output:
                break

        return current, history

    def get_critique(self, critique_id: str) -> Optional[Critique]:
        """Get a critique by ID."""
        return self._critiques.get(critique_id)

    def get_stats(self) -> Dict[str, Any]:
        """Get critique statistics."""
        return {
            **self.stats,
            "active_critiques": len(self._critiques),
        }


def demo():
    """Demonstrate self-critique."""
    import asyncio

    print("=" * 60)
    print("BAEL Self Critique Demo")
    print("=" * 60)

    async def run_demo():
        critic = SelfCritique()

        # Sample output to critique
        output = """
        here is the solution to your problem. The code is definitely correct
        and will work in all cases. Just copy and paste it into your project.

        def solve():
            password = "secret123"
            api_key = "sk-abc123"
            return process(password, api_key)

        This is a very good solution that handles everything you need.
        It is efficient and clear. The implementation is straightforward
        and follows best practices. You should use this code.
        """

        print(f"\nOriginal output (first 100 chars):")
        print(f"  {output[:100]}...")

        # Critique
        print("\nPerforming critique...")
        critique = await critic.critique(
            output,
            context={"query": "help me solve database connection issue"},
        )

        print(f"\nOverall score: {critique.overall_score:.2f}")
        print(f"Passes: {critique.passes}")

        print(f"\nScores by criterion:")
        for criterion, score in critique.scores.items():
            print(f"  {criterion.value}: {score:.2f}")

        print(f"\nIssues found ({len(critique.issues)}):")
        for issue in critique.issues:
            print(f"  [{issue.severity.name}] {issue.description}")

        print(f"\nSuggestions ({len(critique.suggestions)}):")
        for suggestion in critique.suggestions:
            print(f"  (priority {suggestion.priority}) {suggestion.title}")

        # Iterative improvement
        print("\nIterative improvement...")
        improved, history = await critic.iterative_improve(
            output,
            context={"query": "help me solve database connection issue"},
            max_iterations=2,
        )

        print(f"  Iterations: {len(history)}")
        print(f"  Final score: {history[-1].overall_score:.2f}")

        print(f"\nStats: {critic.get_stats()}")

    asyncio.run(run_demo())


if __name__ == "__main__":
    demo()

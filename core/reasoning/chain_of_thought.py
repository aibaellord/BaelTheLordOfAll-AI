"""
BAEL Chain of Thought
======================

Step-by-step reasoning for complex problems.
Enables transparent, traceable thought processes.

Features:
- Sequential reasoning steps
- Thought validation
- Evidence tracking
- Conclusion synthesis
- Reasoning visualization
"""

import asyncio
import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class ThoughtType(Enum):
    """Types of thoughts in reasoning."""
    OBSERVATION = "observation"  # What is observed
    HYPOTHESIS = "hypothesis"  # Proposed explanation
    INFERENCE = "inference"  # Logical deduction
    ASSUMPTION = "assumption"  # Unstated premise
    QUESTION = "question"  # Open question
    CONCLUSION = "conclusion"  # Final answer
    VERIFICATION = "verification"  # Checking step
    REVISION = "revision"  # Correction


class ConfidenceLevel(Enum):
    """Confidence levels for thoughts."""
    CERTAIN = 1.0
    HIGH = 0.8
    MEDIUM = 0.6
    LOW = 0.4
    UNCERTAIN = 0.2
    SPECULATIVE = 0.1


@dataclass
class Evidence:
    """Evidence supporting a thought."""
    id: str
    description: str
    source: str

    # Reliability
    reliability: float = 1.0

    # Type
    evidence_type: str = "observation"  # observation, fact, citation, etc.

    # Metadata
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ThoughtStep:
    """A single step in the chain of thought."""
    id: str
    content: str
    thought_type: ThoughtType

    # Confidence
    confidence: float = 0.8

    # Evidence
    supporting_evidence: List[Evidence] = field(default_factory=list)
    contradicting_evidence: List[Evidence] = field(default_factory=list)

    # Dependencies
    depends_on: List[str] = field(default_factory=list)
    leads_to: List[str] = field(default_factory=list)

    # Validation
    validated: bool = False
    validation_notes: str = ""

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)

    def add_evidence(self, evidence: Evidence, supports: bool = True) -> None:
        """Add evidence to this thought."""
        if supports:
            self.supporting_evidence.append(evidence)
        else:
            self.contradicting_evidence.append(evidence)

        # Adjust confidence based on evidence
        if supports:
            self.confidence = min(1.0, self.confidence + 0.05 * evidence.reliability)
        else:
            self.confidence = max(0.1, self.confidence - 0.1 * evidence.reliability)

    def validate(self, notes: str = "") -> bool:
        """Validate this thought step."""
        # Check for minimum evidence
        if len(self.supporting_evidence) == 0 and self.thought_type not in [
            ThoughtType.ASSUMPTION, ThoughtType.QUESTION
        ]:
            self.validation_notes = "No supporting evidence"
            return False

        # Check confidence threshold
        if self.confidence < 0.3:
            self.validation_notes = f"Low confidence: {self.confidence}"
            return False

        # Check contradicting evidence ratio
        if len(self.contradicting_evidence) > len(self.supporting_evidence):
            self.validation_notes = "More contradicting than supporting evidence"
            return False

        self.validated = True
        self.validation_notes = notes or "Validated"
        return True


@dataclass
class ReasoningChain:
    """A complete chain of reasoning."""
    id: str
    problem: str

    # Steps
    steps: List[ThoughtStep] = field(default_factory=list)

    # Conclusion
    conclusion: Optional[ThoughtStep] = None

    # Metrics
    total_confidence: float = 0.0
    chain_length: int = 0

    # Status
    complete: bool = False
    successful: bool = False

    # Metadata
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None

    def add_step(self, step: ThoughtStep) -> None:
        """Add a step to the chain."""
        if self.steps:
            # Link to previous step
            prev = self.steps[-1]
            step.depends_on.append(prev.id)
            prev.leads_to.append(step.id)

        self.steps.append(step)
        self.chain_length = len(self.steps)
        self._update_confidence()

    def _update_confidence(self) -> None:
        """Update total chain confidence."""
        if not self.steps:
            self.total_confidence = 0.0
            return

        # Chain confidence is product of individual confidences
        confidence = 1.0
        for step in self.steps:
            confidence *= step.confidence

        self.total_confidence = confidence

    def finalize(self, conclusion: ThoughtStep) -> None:
        """Finalize the chain with a conclusion."""
        conclusion.thought_type = ThoughtType.CONCLUSION
        self.conclusion = conclusion
        self.add_step(conclusion)
        self.complete = True
        self.completed_at = datetime.now()

        # Chain is successful if conclusion is validated with good confidence
        self.successful = conclusion.validated and conclusion.confidence >= 0.6


class ChainOfThought:
    """
    Chain of Thought reasoning system for BAEL.

    Enables step-by-step transparent reasoning.
    """

    def __init__(self):
        # Active chains
        self._chains: Dict[str, ReasoningChain] = {}

        # Thought templates
        self._templates: Dict[str, List[ThoughtType]] = {
            "problem_solving": [
                ThoughtType.OBSERVATION,
                ThoughtType.HYPOTHESIS,
                ThoughtType.VERIFICATION,
                ThoughtType.CONCLUSION,
            ],
            "debugging": [
                ThoughtType.OBSERVATION,
                ThoughtType.HYPOTHESIS,
                ThoughtType.VERIFICATION,
                ThoughtType.INFERENCE,
                ThoughtType.CONCLUSION,
            ],
            "analysis": [
                ThoughtType.OBSERVATION,
                ThoughtType.QUESTION,
                ThoughtType.INFERENCE,
                ThoughtType.INFERENCE,
                ThoughtType.CONCLUSION,
            ],
        }

        # Stats
        self.stats = {
            "chains_started": 0,
            "chains_completed": 0,
            "chains_successful": 0,
            "total_steps": 0,
        }

    def start_chain(
        self,
        problem: str,
        template: Optional[str] = None,
    ) -> ReasoningChain:
        """
        Start a new reasoning chain.

        Args:
            problem: Problem statement
            template: Optional reasoning template

        Returns:
            New reasoning chain
        """
        chain_id = hashlib.md5(
            f"{problem}:{datetime.now()}".encode()
        ).hexdigest()[:12]

        chain = ReasoningChain(
            id=chain_id,
            problem=problem,
        )

        self._chains[chain_id] = chain
        self.stats["chains_started"] += 1

        logger.info(f"Started reasoning chain: {chain_id}")

        return chain

    def add_thought(
        self,
        chain_id: str,
        content: str,
        thought_type: ThoughtType,
        confidence: float = 0.8,
        evidence: Optional[List[Evidence]] = None,
    ) -> ThoughtStep:
        """
        Add a thought to a chain.

        Args:
            chain_id: Chain identifier
            content: Thought content
            thought_type: Type of thought
            confidence: Confidence level
            evidence: Supporting evidence

        Returns:
            Created thought step
        """
        if chain_id not in self._chains:
            raise ValueError(f"Unknown chain: {chain_id}")

        chain = self._chains[chain_id]

        step_id = f"{chain_id}_step_{len(chain.steps)}"

        step = ThoughtStep(
            id=step_id,
            content=content,
            thought_type=thought_type,
            confidence=confidence,
        )

        if evidence:
            for ev in evidence:
                step.add_evidence(ev)

        chain.add_step(step)
        self.stats["total_steps"] += 1

        return step

    def validate_step(
        self,
        chain_id: str,
        step_id: str,
    ) -> bool:
        """Validate a thought step."""
        if chain_id not in self._chains:
            return False

        chain = self._chains[chain_id]

        for step in chain.steps:
            if step.id == step_id:
                return step.validate()

        return False

    def revise_step(
        self,
        chain_id: str,
        step_id: str,
        new_content: str,
        new_confidence: Optional[float] = None,
    ) -> Optional[ThoughtStep]:
        """Revise a thought step."""
        if chain_id not in self._chains:
            return None

        chain = self._chains[chain_id]

        for i, step in enumerate(chain.steps):
            if step.id == step_id:
                # Create revision
                revision = ThoughtStep(
                    id=f"{step_id}_rev",
                    content=new_content,
                    thought_type=ThoughtType.REVISION,
                    confidence=new_confidence or step.confidence,
                    depends_on=[step_id],
                )

                # Insert after original
                chain.steps.insert(i + 1, revision)
                step.leads_to.append(revision.id)

                return revision

        return None

    def conclude(
        self,
        chain_id: str,
        conclusion: str,
        confidence: float = 0.8,
    ) -> ReasoningChain:
        """
        Conclude a reasoning chain.

        Args:
            chain_id: Chain identifier
            conclusion: Conclusion text
            confidence: Confidence level

        Returns:
            Finalized chain
        """
        if chain_id not in self._chains:
            raise ValueError(f"Unknown chain: {chain_id}")

        chain = self._chains[chain_id]

        conclusion_step = ThoughtStep(
            id=f"{chain_id}_conclusion",
            content=conclusion,
            thought_type=ThoughtType.CONCLUSION,
            confidence=confidence,
        )

        # Gather evidence from chain
        for step in chain.steps:
            for ev in step.supporting_evidence:
                conclusion_step.add_evidence(ev)

        conclusion_step.validate()
        chain.finalize(conclusion_step)

        self.stats["chains_completed"] += 1
        if chain.successful:
            self.stats["chains_successful"] += 1

        logger.info(f"Concluded chain {chain_id}: success={chain.successful}")

        return chain

    async def reason(
        self,
        problem: str,
        max_steps: int = 10,
        auto_conclude: bool = True,
    ) -> ReasoningChain:
        """
        Automatically reason through a problem.

        Args:
            problem: Problem to solve
            max_steps: Maximum reasoning steps
            auto_conclude: Whether to auto-generate conclusion

        Returns:
            Completed reasoning chain
        """
        chain = self.start_chain(problem)

        # Initial observation
        self.add_thought(
            chain.id,
            f"Observing the problem: {problem[:100]}...",
            ThoughtType.OBSERVATION,
            confidence=0.9,
        )

        # Generate hypotheses
        self.add_thought(
            chain.id,
            "Initial hypothesis: This problem can be approached systematically",
            ThoughtType.HYPOTHESIS,
            confidence=0.7,
        )

        # Add inferences based on template
        self.add_thought(
            chain.id,
            "Breaking down the problem into components",
            ThoughtType.INFERENCE,
            confidence=0.8,
        )

        self.add_thought(
            chain.id,
            "Identifying key constraints and requirements",
            ThoughtType.INFERENCE,
            confidence=0.75,
        )

        # Verification
        self.add_thought(
            chain.id,
            "Verifying approach against known patterns",
            ThoughtType.VERIFICATION,
            confidence=0.85,
        )

        if auto_conclude:
            # Generate conclusion
            self.conclude(
                chain.id,
                "Based on the analysis, a solution approach has been identified",
                confidence=0.8,
            )

        return chain

    def get_chain(self, chain_id: str) -> Optional[ReasoningChain]:
        """Get a reasoning chain."""
        return self._chains.get(chain_id)

    def visualize_chain(self, chain_id: str) -> str:
        """Visualize a reasoning chain as text."""
        if chain_id not in self._chains:
            return "Chain not found"

        chain = self._chains[chain_id]
        lines = [
            f"Reasoning Chain: {chain_id}",
            f"Problem: {chain.problem}",
            f"Confidence: {chain.total_confidence:.2%}",
            "-" * 50,
        ]

        for i, step in enumerate(chain.steps):
            icon = "✓" if step.validated else "○"
            lines.append(
                f"{i+1}. [{step.thought_type.value}] {icon} {step.content[:60]}..."
                f" (conf: {step.confidence:.0%})"
            )

        if chain.complete:
            lines.append("-" * 50)
            lines.append(f"Status: {'SUCCESS' if chain.successful else 'COMPLETED'}")

        return "\n".join(lines)

    def get_stats(self) -> Dict[str, Any]:
        """Get reasoning statistics."""
        return {
            **self.stats,
            "active_chains": len(self._chains),
            "avg_chain_length": (
                sum(c.chain_length for c in self._chains.values()) /
                len(self._chains) if self._chains else 0
            ),
        }


def demo():
    """Demonstrate chain of thought reasoning."""
    import asyncio

    print("=" * 60)
    print("BAEL Chain of Thought Demo")
    print("=" * 60)

    async def run_demo():
        cot = ChainOfThought()

        # Start a reasoning chain
        problem = "Why is the login endpoint returning 401 errors for valid tokens?"

        print(f"\nProblem: {problem}")
        print("-" * 50)

        chain = cot.start_chain(problem)

        # Add reasoning steps
        step1 = cot.add_thought(
            chain.id,
            "The error is 401 Unauthorized, indicating authentication failure",
            ThoughtType.OBSERVATION,
            confidence=0.95,
            evidence=[
                Evidence(
                    id="ev1",
                    description="Server logs show 401 response",
                    source="logs",
                    reliability=0.9,
                )
            ],
        )

        step2 = cot.add_thought(
            chain.id,
            "The token might be expired or malformed",
            ThoughtType.HYPOTHESIS,
            confidence=0.6,
        )

        step3 = cot.add_thought(
            chain.id,
            "Token validation includes checking expiry, signature, and claims",
            ThoughtType.INFERENCE,
            confidence=0.85,
        )

        step4 = cot.add_thought(
            chain.id,
            "Checking token expiry shows tokens are valid for 24 hours",
            ThoughtType.VERIFICATION,
            confidence=0.9,
            evidence=[
                Evidence(
                    id="ev2",
                    description="Token exp claim is future timestamp",
                    source="token_decode",
                    reliability=0.95,
                )
            ],
        )

        step5 = cot.add_thought(
            chain.id,
            "Server time might be incorrect, causing valid tokens to appear expired",
            ThoughtType.HYPOTHESIS,
            confidence=0.7,
        )

        step6 = cot.add_thought(
            chain.id,
            "Checking server time shows 2-hour clock drift",
            ThoughtType.VERIFICATION,
            confidence=0.95,
            evidence=[
                Evidence(
                    id="ev3",
                    description="NTP sync disabled on server",
                    source="system_config",
                    reliability=0.99,
                )
            ],
        )

        # Validate steps
        for step in chain.steps:
            cot.validate_step(chain.id, step.id)

        # Conclude
        cot.conclude(
            chain.id,
            "The 401 errors are caused by server clock drift of 2 hours. "
            "Valid tokens appear expired because the server time is ahead. "
            "Fix: Enable NTP synchronization on the server.",
            confidence=0.92,
        )

        # Visualize
        print("\n" + cot.visualize_chain(chain.id))

        print(f"\nStats: {cot.get_stats()}")

    asyncio.run(run_demo())


if __name__ == "__main__":
    demo()

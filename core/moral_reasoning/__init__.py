"""
BAEL Moral Reasoning Engine
============================

Ethical cognition and moral judgment.
Moral foundations, dilemmas, and reasoning.

"Ba'el judges with wisdom." — Ba'el
"""

import logging
import threading
import time
import math
import random
from typing import Any, Callable, Dict, Generic, List, Optional, Set, Tuple, TypeVar
from dataclasses import dataclass, field
from enum import Enum, auto
from abc import ABC, abstractmethod
from collections import defaultdict, deque
import copy

logger = logging.getLogger("BAEL.MoralReasoning")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class MoralFoundation(Enum):
    """Moral Foundations Theory (Haidt)."""
    CARE_HARM = auto()           # Caring, compassion
    FAIRNESS_CHEATING = auto()   # Justice, rights
    LOYALTY_BETRAYAL = auto()    # Group loyalty
    AUTHORITY_SUBVERSION = auto() # Respect, tradition
    SANCTITY_DEGRADATION = auto() # Purity, disgust
    LIBERTY_OPPRESSION = auto()   # Freedom from tyranny


class MoralTheory(Enum):
    """Ethical theories."""
    DEONTOLOGICAL = auto()    # Duty-based (Kant)
    CONSEQUENTIALIST = auto() # Outcome-based (Mill)
    VIRTUE = auto()           # Character-based (Aristotle)
    CARE = auto()             # Relationship-based (Gilligan)
    CONTRACTARIAN = auto()    # Agreement-based (Rawls)


class DilemmaType(Enum):
    """Types of moral dilemmas."""
    TROLLEY = auto()         # Sacrifice one to save many
    UTILITARIAN = auto()     # Greater good
    RIGHTS = auto()          # Individual rights
    JUSTICE = auto()         # Fairness
    LOYALTY = auto()         # Conflicting loyalties


class JudgmentType(Enum):
    """Types of moral judgment."""
    PERMISSIBLE = auto()     # Allowed
    OBLIGATORY = auto()      # Required
    FORBIDDEN = auto()       # Prohibited
    SUPEREROGATORY = auto()  # Beyond duty


@dataclass
class MoralPrinciple:
    """
    A moral principle.
    """
    id: str
    name: str
    foundation: MoralFoundation
    description: str
    weight: float  # 0-1, importance


@dataclass
class Action:
    """
    An action to be morally evaluated.
    """
    id: str
    description: str
    agent: str
    intended: bool
    consequences: List[str]


@dataclass
class Stakeholder:
    """
    A party affected by action.
    """
    id: str
    name: str
    relationship: str  # stranger, friend, family, self
    vulnerability: float  # 0-1


@dataclass
class MoralDilemma:
    """
    A moral dilemma.
    """
    id: str
    description: str
    options: List[Action]
    stakeholders: List[Stakeholder]
    dilemma_type: DilemmaType
    forced_choice: bool


@dataclass
class MoralJudgment:
    """
    A moral judgment.
    """
    action_id: str
    judgment: JudgmentType
    confidence: float
    reasoning: str
    principles_applied: List[str]


@dataclass
class MoralProfile:
    """
    An agent's moral profile.
    """
    foundation_weights: Dict[MoralFoundation, float]
    theory_preference: MoralTheory
    strictness: float  # 0-1, how strict


# ============================================================================
# MORAL FOUNDATIONS ANALYZER
# ============================================================================

class MoralFoundationsAnalyzer:
    """
    Analyze moral foundations.
    Based on Haidt's Moral Foundations Theory.

    "Ba'el understands moral intuitions." — Ba'el
    """

    def __init__(self):
        """Initialize analyzer."""
        self._foundation_keywords = {
            MoralFoundation.CARE_HARM: [
                'harm', 'hurt', 'care', 'protect', 'suffer', 'kind', 'cruel'
            ],
            MoralFoundation.FAIRNESS_CHEATING: [
                'fair', 'equal', 'just', 'cheat', 'rights', 'deserve', 'unfair'
            ],
            MoralFoundation.LOYALTY_BETRAYAL: [
                'loyal', 'team', 'group', 'betray', 'traitor', 'family', 'patriot'
            ],
            MoralFoundation.AUTHORITY_SUBVERSION: [
                'authority', 'respect', 'obey', 'tradition', 'order', 'rebel'
            ],
            MoralFoundation.SANCTITY_DEGRADATION: [
                'pure', 'sacred', 'disgust', 'unnatural', 'dirty', 'holy'
            ],
            MoralFoundation.LIBERTY_OPPRESSION: [
                'freedom', 'liberty', 'oppress', 'rights', 'autonomy', 'control'
            ]
        }

        self._lock = threading.RLock()

    def analyze_text(
        self,
        text: str
    ) -> Dict[MoralFoundation, float]:
        """Analyze text for moral foundations."""
        text_lower = text.lower()
        scores = {}

        for foundation, keywords in self._foundation_keywords.items():
            count = sum(1 for kw in keywords if kw in text_lower)
            scores[foundation] = min(1.0, count / 3)

        return scores

    def analyze_action(
        self,
        action: Action
    ) -> Dict[MoralFoundation, float]:
        """Analyze action for moral foundations."""
        # Combine description and consequences
        full_text = action.description + " " + " ".join(action.consequences)
        return self.analyze_text(full_text)

    def get_dominant_foundation(
        self,
        scores: Dict[MoralFoundation, float]
    ) -> MoralFoundation:
        """Get dominant moral foundation."""
        if not scores:
            return MoralFoundation.CARE_HARM
        return max(scores.items(), key=lambda x: x[1])[0]


# ============================================================================
# ETHICAL REASONER
# ============================================================================

class EthicalReasoner:
    """
    Apply ethical reasoning.

    "Ba'el reasons about right and wrong." — Ba'el
    """

    def __init__(self):
        """Initialize reasoner."""
        self._lock = threading.RLock()

    def deontological_evaluation(
        self,
        action: Action
    ) -> Tuple[JudgmentType, str]:
        """Evaluate action from deontological perspective."""
        # Check for violations of duties

        # Categorical imperative: Could this be a universal law?
        violations = []

        if 'lie' in action.description.lower() or 'deceive' in action.description.lower():
            violations.append("violates duty of honesty")

        if 'harm' in action.description.lower() and action.intended:
            violations.append("uses person merely as means")

        if violations:
            return JudgmentType.FORBIDDEN, f"Deontological: {', '.join(violations)}"

        return JudgmentType.PERMISSIBLE, "Deontological: Does not violate duties"

    def consequentialist_evaluation(
        self,
        action: Action,
        stakeholders: List[Stakeholder]
    ) -> Tuple[JudgmentType, str]:
        """Evaluate action from consequentialist perspective."""
        # Calculate net utility

        positive = sum(1 for c in action.consequences if 'benefit' in c.lower() or 'save' in c.lower())
        negative = sum(1 for c in action.consequences if 'harm' in c.lower() or 'hurt' in c.lower())

        # Weight by number of stakeholders
        affected_count = len(stakeholders)

        net_utility = (positive - negative) * affected_count

        if net_utility > 2:
            return JudgmentType.OBLIGATORY, f"Consequentialist: Maximizes utility ({net_utility})"
        elif net_utility > 0:
            return JudgmentType.PERMISSIBLE, f"Consequentialist: Positive net utility ({net_utility})"
        else:
            return JudgmentType.FORBIDDEN, f"Consequentialist: Negative net utility ({net_utility})"

    def virtue_evaluation(
        self,
        action: Action
    ) -> Tuple[JudgmentType, str]:
        """Evaluate action from virtue ethics perspective."""
        # Check for virtuous character

        virtues = ['courage', 'justice', 'temperance', 'wisdom', 'kindness']
        vices = ['cowardice', 'injustice', 'excess', 'foolishness', 'cruelty']

        text = action.description.lower()

        virtue_count = sum(1 for v in virtues if v in text)
        vice_count = sum(1 for v in vices if v in text)

        if virtue_count > vice_count:
            return JudgmentType.PERMISSIBLE, "Virtue: Expresses virtuous character"
        elif vice_count > virtue_count:
            return JudgmentType.FORBIDDEN, "Virtue: Expresses vicious character"

        return JudgmentType.PERMISSIBLE, "Virtue: Neutral"

    def care_evaluation(
        self,
        action: Action,
        stakeholders: List[Stakeholder]
    ) -> Tuple[JudgmentType, str]:
        """Evaluate from care ethics perspective."""
        # Consider relationships and vulnerability

        vulnerable = [s for s in stakeholders if s.vulnerability > 0.5]
        close = [s for s in stakeholders if s.relationship in ['family', 'friend']]

        text = action.description.lower()

        if vulnerable and 'protect' in text:
            return JudgmentType.OBLIGATORY, "Care: Protects vulnerable"

        if close and 'harm' in text:
            return JudgmentType.FORBIDDEN, "Care: Harms those in relationship"

        return JudgmentType.PERMISSIBLE, "Care: Neutral"


# ============================================================================
# DILEMMA SOLVER
# ============================================================================

class DilemmaSolver:
    """
    Solve moral dilemmas.

    "Ba'el navigates impossible choices." — Ba'el
    """

    def __init__(
        self,
        foundations_analyzer: MoralFoundationsAnalyzer,
        ethical_reasoner: EthicalReasoner
    ):
        """Initialize solver."""
        self._foundations = foundations_analyzer
        self._reasoner = ethical_reasoner
        self._lock = threading.RLock()

    def solve(
        self,
        dilemma: MoralDilemma,
        profile: MoralProfile
    ) -> Tuple[Action, List[MoralJudgment]]:
        """Solve moral dilemma given moral profile."""
        with self._lock:
            judgments = []

            for action in dilemma.options:
                # Get foundations involved
                foundation_scores = self._foundations.analyze_action(action)

                # Apply ethical theories based on preference
                if profile.theory_preference == MoralTheory.DEONTOLOGICAL:
                    judgment, reasoning = self._reasoner.deontological_evaluation(action)
                elif profile.theory_preference == MoralTheory.CONSEQUENTIALIST:
                    judgment, reasoning = self._reasoner.consequentialist_evaluation(
                        action, dilemma.stakeholders
                    )
                elif profile.theory_preference == MoralTheory.VIRTUE:
                    judgment, reasoning = self._reasoner.virtue_evaluation(action)
                else:
                    judgment, reasoning = self._reasoner.care_evaluation(
                        action, dilemma.stakeholders
                    )

                # Calculate confidence based on foundation alignment
                dominant = self._foundations.get_dominant_foundation(foundation_scores)
                alignment = profile.foundation_weights.get(dominant, 0.5)
                confidence = 0.5 + 0.5 * alignment

                moral_judgment = MoralJudgment(
                    action_id=action.id,
                    judgment=judgment,
                    confidence=confidence,
                    reasoning=reasoning,
                    principles_applied=[dominant.name]
                )

                judgments.append(moral_judgment)

            # Choose best action
            permissible = [
                (j, dilemma.options[i])
                for i, j in enumerate(judgments)
                if j.judgment in [JudgmentType.PERMISSIBLE, JudgmentType.OBLIGATORY]
            ]

            if permissible:
                # Choose highest confidence permissible action
                best = max(permissible, key=lambda x: x[0].confidence)
                return best[1], judgments
            else:
                # Forced choice: pick least bad
                return dilemma.options[0], judgments

    def solve_trolley(
        self,
        profile: MoralProfile
    ) -> Tuple[str, str]:
        """Solve classic trolley problem."""
        # Create dilemma
        dilemma = MoralDilemma(
            id="trolley_1",
            description="A runaway trolley will kill 5 people. You can divert it to kill 1 person instead.",
            options=[
                Action(
                    id="do_nothing",
                    description="Do nothing, 5 die",
                    agent="self",
                    intended=False,
                    consequences=["5 people die"]
                ),
                Action(
                    id="divert",
                    description="Pull lever, 1 dies",
                    agent="self",
                    intended=True,
                    consequences=["1 person dies", "5 people saved"]
                )
            ],
            stakeholders=[
                Stakeholder(id="s1", name="5 on track", relationship="stranger", vulnerability=1.0),
                Stakeholder(id="s2", name="1 on side", relationship="stranger", vulnerability=1.0)
            ],
            dilemma_type=DilemmaType.TROLLEY,
            forced_choice=True
        )

        chosen_action, judgments = self.solve(dilemma, profile)

        return chosen_action.id, judgments[0].reasoning if judgments else ""


# ============================================================================
# MORAL REASONING ENGINE
# ============================================================================

class MoralReasoningEngine:
    """
    Complete moral reasoning engine.

    "Ba'el's ethical mind." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._foundations = MoralFoundationsAnalyzer()
        self._reasoner = EthicalReasoner()
        self._solver = DilemmaSolver(self._foundations, self._reasoner)

        self._dilemmas: List[MoralDilemma] = []
        self._judgments: List[MoralJudgment] = []

        self._action_counter = 0
        self._dilemma_counter = 0

        self._default_profile = MoralProfile(
            foundation_weights={f: 0.5 for f in MoralFoundation},
            theory_preference=MoralTheory.CONSEQUENTIALIST,
            strictness=0.5
        )

        self._lock = threading.RLock()

    def _generate_action_id(self) -> str:
        self._action_counter += 1
        return f"action_{self._action_counter}"

    def _generate_dilemma_id(self) -> str:
        self._dilemma_counter += 1
        return f"dilemma_{self._dilemma_counter}"

    # Profile management

    def set_profile(
        self,
        profile: MoralProfile
    ) -> None:
        """Set moral profile."""
        self._default_profile = profile

    def create_profile(
        self,
        care_harm: float = 0.5,
        fairness: float = 0.5,
        loyalty: float = 0.5,
        authority: float = 0.5,
        sanctity: float = 0.5,
        liberty: float = 0.5,
        theory: MoralTheory = MoralTheory.CONSEQUENTIALIST,
        strictness: float = 0.5
    ) -> MoralProfile:
        """Create moral profile."""
        return MoralProfile(
            foundation_weights={
                MoralFoundation.CARE_HARM: care_harm,
                MoralFoundation.FAIRNESS_CHEATING: fairness,
                MoralFoundation.LOYALTY_BETRAYAL: loyalty,
                MoralFoundation.AUTHORITY_SUBVERSION: authority,
                MoralFoundation.SANCTITY_DEGRADATION: sanctity,
                MoralFoundation.LIBERTY_OPPRESSION: liberty
            },
            theory_preference=theory,
            strictness=strictness
        )

    # Action evaluation

    def create_action(
        self,
        description: str,
        consequences: List[str],
        intended: bool = True
    ) -> Action:
        """Create action."""
        return Action(
            id=self._generate_action_id(),
            description=description,
            agent="self",
            intended=intended,
            consequences=consequences
        )

    def evaluate_action(
        self,
        action: Action,
        stakeholders: List[Stakeholder] = None
    ) -> MoralJudgment:
        """Evaluate a single action."""
        if stakeholders is None:
            stakeholders = []

        profile = self._default_profile

        # Get ethical evaluations
        deon_judgment, deon_reason = self._reasoner.deontological_evaluation(action)
        cons_judgment, cons_reason = self._reasoner.consequentialist_evaluation(action, stakeholders)

        # Combine based on profile preference
        if profile.theory_preference == MoralTheory.DEONTOLOGICAL:
            judgment, reasoning = deon_judgment, deon_reason
        else:
            judgment, reasoning = cons_judgment, cons_reason

        moral_judgment = MoralJudgment(
            action_id=action.id,
            judgment=judgment,
            confidence=0.7,
            reasoning=reasoning,
            principles_applied=[profile.theory_preference.name]
        )

        self._judgments.append(moral_judgment)
        return moral_judgment

    # Dilemma solving

    def create_dilemma(
        self,
        description: str,
        options: List[Action],
        stakeholders: List[Stakeholder],
        dilemma_type: DilemmaType = DilemmaType.UTILITARIAN
    ) -> MoralDilemma:
        """Create moral dilemma."""
        dilemma = MoralDilemma(
            id=self._generate_dilemma_id(),
            description=description,
            options=options,
            stakeholders=stakeholders,
            dilemma_type=dilemma_type,
            forced_choice=True
        )
        self._dilemmas.append(dilemma)
        return dilemma

    def solve_dilemma(
        self,
        dilemma: MoralDilemma,
        profile: MoralProfile = None
    ) -> Tuple[Action, List[MoralJudgment]]:
        """Solve moral dilemma."""
        if profile is None:
            profile = self._default_profile
        return self._solver.solve(dilemma, profile)

    def solve_trolley_problem(
        self,
        profile: MoralProfile = None
    ) -> Tuple[str, str]:
        """Solve trolley problem."""
        if profile is None:
            profile = self._default_profile
        return self._solver.solve_trolley(profile)

    # Foundation analysis

    def analyze_foundations(
        self,
        text: str
    ) -> Dict[MoralFoundation, float]:
        """Analyze moral foundations in text."""
        return self._foundations.analyze_text(text)

    def get_dominant_foundation(
        self,
        text: str
    ) -> MoralFoundation:
        """Get dominant moral foundation."""
        scores = self.analyze_foundations(text)
        return self._foundations.get_dominant_foundation(scores)

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'dilemmas_solved': len(self._dilemmas),
            'judgments_made': len(self._judgments),
            'current_theory': self._default_profile.theory_preference.name
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_moral_reasoning_engine() -> MoralReasoningEngine:
    """Create moral reasoning engine."""
    return MoralReasoningEngine()


def solve_trolley_problem(
    utilitarian: bool = True
) -> Tuple[str, str]:
    """Solve trolley problem with utilitarian or deontological approach."""
    engine = create_moral_reasoning_engine()

    if utilitarian:
        profile = engine.create_profile(
            theory=MoralTheory.CONSEQUENTIALIST
        )
    else:
        profile = engine.create_profile(
            theory=MoralTheory.DEONTOLOGICAL
        )

    return engine.solve_trolley_problem(profile)


def get_moral_foundations_explained() -> Dict[MoralFoundation, str]:
    """Get explanations of moral foundations."""
    return {
        MoralFoundation.CARE_HARM: "Compassion for others, especially vulnerable",
        MoralFoundation.FAIRNESS_CHEATING: "Justice, rights, and equality",
        MoralFoundation.LOYALTY_BETRAYAL: "In-group loyalty and patriotism",
        MoralFoundation.AUTHORITY_SUBVERSION: "Respect for tradition and authority",
        MoralFoundation.SANCTITY_DEGRADATION: "Purity, sacredness, disgust",
        MoralFoundation.LIBERTY_OPPRESSION: "Freedom from tyranny and oppression"
    }

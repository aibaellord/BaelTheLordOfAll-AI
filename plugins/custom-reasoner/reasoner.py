"""
Custom Reasoner Plugin - Framework for implementing custom reasoning engines
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from core.plugins.registry import PluginInterface, PluginManifest


class ReasoningMode(str, Enum):
    """Reasoning modes"""
    DEDUCTIVE = "deductive"      # General to specific
    INDUCTIVE = "inductive"       # Specific to general
    ABDUCTIVE = "abductive"       # Inference to best explanation
    HYBRID = "hybrid"             # Combined approach


@dataclass
class Premise:
    """A premise in reasoning"""
    statement: str
    confidence: float = 1.0
    source: Optional[str] = None


@dataclass
class Conclusion:
    """A conclusion from reasoning"""
    statement: str
    confidence: float
    reasoning_path: List[str]
    premises_used: List[Premise]


class CustomReasoner(PluginInterface):
    """Framework for custom reasoning engines"""

    def __init__(self, manifest: PluginManifest, config: Dict[str, Any]):
        super().__init__(manifest, config)
        self.reasoning_mode = ReasoningMode(config.get("reasoning_mode", "hybrid"))
        self.max_depth = config.get("max_depth", 10)
        self.confidence_threshold = config.get("confidence_threshold", 0.7)
        self.knowledge_base: List[Premise] = []
        self.conclusions_cache: Dict[str, Conclusion] = {}

    async def initialize(self) -> bool:
        """Initialize reasoner"""
        try:
            self.logger.info(f"Initializing custom reasoner ({self.reasoning_mode.value} mode)")
            self.logger.info(f"Max depth: {self.max_depth}, Threshold: {self.confidence_threshold}")
            return True
        except Exception as e:
            self.logger.error(f"Initialization failed: {e}")
            return False

    async def shutdown(self):
        """Cleanup reasoner"""
        self.knowledge_base.clear()
        self.conclusions_cache.clear()
        self.logger.info("Reasoner shutdown")

    async def health_check(self) -> bool:
        """Check reasoner health"""
        return True

    # Knowledge Base Methods
    async def add_premise(
        self,
        statement: str,
        confidence: float = 1.0,
        source: Optional[str] = None
    ) -> bool:
        """Add a premise to knowledge base"""
        try:
            if not 0 <= confidence <= 1:
                self.logger.error("Confidence must be between 0 and 1")
                return False

            premise = Premise(
                statement=statement,
                confidence=confidence,
                source=source
            )
            self.knowledge_base.append(premise)
            self.conclusions_cache.clear()  # Invalidate cache

            self.logger.debug(f"Added premise: {statement[:50]}...")
            return True

        except Exception as e:
            self.logger.error(f"Failed to add premise: {e}")
            return False

    async def get_premises(self) -> List[Premise]:
        """Get all premises in knowledge base"""
        return self.knowledge_base.copy()

    async def clear_knowledge_base(self):
        """Clear all premises"""
        self.knowledge_base.clear()
        self.conclusions_cache.clear()
        self.logger.info("Knowledge base cleared")

    # Reasoning Methods
    async def reason(
        self,
        query: str,
        depth: Optional[int] = None
    ) -> Optional[Conclusion]:
        """Perform reasoning"""
        depth = depth or self.max_depth

        try:
            self.logger.debug(f"Reasoning: {query[:50]}...")

            # Check cache
            if query in self.conclusions_cache:
                return self.conclusions_cache[query]

            # Perform reasoning based on mode
            if self.reasoning_mode == ReasoningMode.DEDUCTIVE:
                conclusion = await self._reason_deductive(query, depth)
            elif self.reasoning_mode == ReasoningMode.INDUCTIVE:
                conclusion = await self._reason_inductive(query, depth)
            elif self.reasoning_mode == ReasoningMode.ABDUCTIVE:
                conclusion = await self._reason_abductive(query, depth)
            else:  # HYBRID
                conclusion = await self._reason_hybrid(query, depth)

            if conclusion and conclusion.confidence >= self.confidence_threshold:
                self.conclusions_cache[query] = conclusion
                return conclusion

            return None

        except Exception as e:
            self.logger.error(f"Reasoning failed: {e}")
            return None

    async def _reason_deductive(
        self,
        query: str,
        depth: int
    ) -> Optional[Conclusion]:
        """Deductive reasoning (general to specific)"""
        reasoning_path = [f"Deductive reasoning for: {query}"]
        matching_premises = [p for p in self.knowledge_base if query.lower() in p.statement.lower()]

        if matching_premises:
            avg_confidence = sum(p.confidence for p in matching_premises) / len(matching_premises)
            return Conclusion(
                statement=query,
                confidence=avg_confidence,
                reasoning_path=reasoning_path,
                premises_used=matching_premises
            )

        return None

    async def _reason_inductive(
        self,
        query: str,
        depth: int
    ) -> Optional[Conclusion]:
        """Inductive reasoning (specific to general)"""
        reasoning_path = [f"Inductive reasoning for: {query}"]
        related_premises = [p for p in self.knowledge_base if len(self.knowledge_base) > 0]

        if related_premises:
            # In production, would perform actual inductive reasoning
            avg_confidence = sum(p.confidence for p in related_premises) / len(related_premises) * 0.9
            return Conclusion(
                statement=f"General principle from: {query}",
                confidence=avg_confidence,
                reasoning_path=reasoning_path,
                premises_used=related_premises[:3]
            )

        return None

    async def _reason_abductive(
        self,
        query: str,
        depth: int
    ) -> Optional[Conclusion]:
        """Abductive reasoning (inference to best explanation)"""
        reasoning_path = [f"Abductive reasoning for: {query}"]
        matching_premises = [p for p in self.knowledge_base if query.lower() in p.statement.lower()]

        if matching_premises:
            # Select best explanation
            best_premise = max(matching_premises, key=lambda p: p.confidence)
            return Conclusion(
                statement=f"Best explanation: {best_premise.statement}",
                confidence=best_premise.confidence,
                reasoning_path=reasoning_path,
                premises_used=[best_premise]
            )

        return None

    async def _reason_hybrid(
        self,
        query: str,
        depth: int
    ) -> Optional[Conclusion]:
        """Hybrid reasoning (combined approaches)"""
        reasoning_path = [f"Hybrid reasoning for: {query}"]

        # Try all reasoning modes
        results = []
        for conclusion in [
            await self._reason_deductive(query, depth),
            await self._reason_inductive(query, depth),
            await self._reason_abductive(query, depth)
        ]:
            if conclusion:
                results.append(conclusion)

        if results:
            # Combine results
            best_result = max(results, key=lambda c: c.confidence)
            best_result.reasoning_path = reasoning_path + best_result.reasoning_path
            return best_result

        return None

    # Hypothesis Testing
    async def test_hypothesis(
        self,
        hypothesis: str,
        supporting_evidence: List[str]
    ) -> Tuple[bool, float, str]:
        """Test a hypothesis"""
        try:
            self.logger.debug(f"Testing hypothesis: {hypothesis[:50]}...")

            # Check evidence against knowledge base
            matching_count = 0
            for evidence in supporting_evidence:
                matching = any(
                    evidence.lower() in p.statement.lower()
                    for p in self.knowledge_base
                )
                if matching:
                    matching_count += 1

            confidence = matching_count / len(supporting_evidence) if supporting_evidence else 0

            supported = confidence >= self.confidence_threshold
            reasoning = f"Hypothesis is {'supported' if supported else 'not supported'} by {matching_count}/{len(supporting_evidence)} evidence"

            return supported, confidence, reasoning

        except Exception as e:
            self.logger.error(f"Hypothesis testing failed: {e}")
            return False, 0.0, str(e)

    # Analysis Methods
    async def get_reasoning_stats(self) -> Dict[str, Any]:
        """Get reasoning statistics"""
        return {
            "premises_count": len(self.knowledge_base),
            "avg_confidence": sum(p.confidence for p in self.knowledge_base) / len(self.knowledge_base) if self.knowledge_base else 0,
            "conclusions_cached": len(self.conclusions_cache),
            "reasoning_mode": self.reasoning_mode.value,
            "max_depth": self.max_depth
        }


def register(manifest: PluginManifest, config: Dict[str, Any]) -> CustomReasoner:
    """Register custom reasoner plugin"""
    return CustomReasoner(manifest, config)

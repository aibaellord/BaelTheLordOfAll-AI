"""
BAEL Knowledge Transfer
========================

Transfer knowledge between projects and contexts.
Enables applying learned patterns to new situations.

Features:
- Knowledge base management
- Context mapping
- Pattern application
- Adaptation strategies
- Transfer validation
"""

import asyncio
import hashlib
import json
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class TransferStrategy(Enum):
    """Knowledge transfer strategies."""
    DIRECT = "direct"          # Apply directly
    ADAPTED = "adapted"        # Adapt to new context
    SELECTIVE = "selective"    # Select relevant parts
    MERGED = "merged"          # Merge with existing


class KnowledgeType(Enum):
    """Types of transferable knowledge."""
    PATTERN = "pattern"
    SOLUTION = "solution"
    ARCHITECTURE = "architecture"
    BEST_PRACTICE = "best_practice"
    ERROR_FIX = "error_fix"
    OPTIMIZATION = "optimization"


@dataclass
class TransferableKnowledge:
    """A piece of transferable knowledge."""
    id: str
    name: str
    description: str

    # Classification
    type: KnowledgeType = KnowledgeType.PATTERN

    # Content
    content: Dict[str, Any] = field(default_factory=dict)
    code_template: str = ""

    # Applicability
    source_context: Dict[str, Any] = field(default_factory=dict)
    requirements: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)

    # Transfer history
    transfers: int = 0
    success_rate: float = 0.0

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    tags: List[str] = field(default_factory=list)


@dataclass
class TransferContext:
    """Context for knowledge transfer."""
    # Target environment
    project_type: str = ""
    language: str = ""
    framework: str = ""

    # Requirements
    requirements: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)

    # Existing knowledge
    existing_patterns: List[str] = field(default_factory=list)
    existing_solutions: List[str] = field(default_factory=list)


@dataclass
class TransferResult:
    """Result of knowledge transfer."""
    knowledge_id: str
    strategy: TransferStrategy
    success: bool

    # Transferred content
    adapted_content: Dict[str, Any] = field(default_factory=dict)
    adapted_code: str = ""

    # Validation
    validation_passed: bool = False
    validation_notes: List[str] = field(default_factory=list)

    # Metadata
    confidence: float = 0.0
    transfer_time_ms: float = 0.0


@dataclass
class KnowledgeBase:
    """Collection of transferable knowledge."""
    id: str
    name: str
    description: str = ""

    # Knowledge items
    items: Dict[str, TransferableKnowledge] = field(default_factory=dict)

    # Organization
    categories: Dict[str, List[str]] = field(default_factory=dict)

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    version: str = "1.0.0"


class KnowledgeTransfer:
    """
    Knowledge transfer system for BAEL.
    """

    def __init__(self):
        # Knowledge bases
        self.bases: Dict[str, KnowledgeBase] = {}

        # Global knowledge index
        self.knowledge_index: Dict[str, TransferableKnowledge] = {}

        # Transfer adapters
        self._adapters: Dict[str, Callable] = {}
        self._register_default_adapters()

        # Stats
        self.stats = {
            "knowledge_items": 0,
            "transfers": 0,
            "successful_transfers": 0,
        }

    def _register_default_adapters(self) -> None:
        """Register default knowledge adapters."""
        # Language adapters
        self._adapters["python_to_javascript"] = self._adapt_python_to_js
        self._adapters["javascript_to_python"] = self._adapt_js_to_python

    def create_base(
        self,
        name: str,
        description: str = "",
    ) -> KnowledgeBase:
        """Create a new knowledge base."""
        base_id = hashlib.md5(f"{name}:{datetime.now()}".encode()).hexdigest()[:12]

        base = KnowledgeBase(
            id=base_id,
            name=name,
            description=description,
        )

        self.bases[base_id] = base

        logger.info(f"Created knowledge base: {name} ({base_id})")

        return base

    def add_knowledge(
        self,
        base_id: str,
        knowledge: TransferableKnowledge,
    ) -> bool:
        """Add knowledge to a base."""
        base = self.bases.get(base_id)
        if not base:
            return False

        base.items[knowledge.id] = knowledge
        self.knowledge_index[knowledge.id] = knowledge

        # Categorize
        category = knowledge.type.value
        if category not in base.categories:
            base.categories[category] = []
        base.categories[category].append(knowledge.id)

        self.stats["knowledge_items"] += 1

        return True

    def create_knowledge(
        self,
        name: str,
        description: str,
        knowledge_type: KnowledgeType,
        content: Dict[str, Any],
        code_template: str = "",
        requirements: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
    ) -> TransferableKnowledge:
        """Create a new knowledge item."""
        knowledge_id = hashlib.md5(
            f"{name}:{datetime.now().timestamp()}".encode()
        ).hexdigest()[:12]

        return TransferableKnowledge(
            id=knowledge_id,
            name=name,
            description=description,
            type=knowledge_type,
            content=content,
            code_template=code_template,
            requirements=requirements or [],
            tags=tags or [],
        )

    async def transfer(
        self,
        knowledge_id: str,
        context: TransferContext,
        strategy: TransferStrategy = TransferStrategy.ADAPTED,
    ) -> TransferResult:
        """
        Transfer knowledge to a new context.

        Args:
            knowledge_id: ID of knowledge to transfer
            context: Target context
            strategy: Transfer strategy

        Returns:
            TransferResult
        """
        import time

        self.stats["transfers"] += 1
        start_time = time.time()

        knowledge = self.knowledge_index.get(knowledge_id)
        if not knowledge:
            return TransferResult(
                knowledge_id=knowledge_id,
                strategy=strategy,
                success=False,
                validation_notes=["Knowledge not found"],
            )

        # Check applicability
        applicable, notes = self._check_applicability(knowledge, context)
        if not applicable:
            return TransferResult(
                knowledge_id=knowledge_id,
                strategy=strategy,
                success=False,
                validation_notes=notes,
            )

        # Apply strategy
        if strategy == TransferStrategy.DIRECT:
            adapted_content, adapted_code = self._transfer_direct(knowledge)
        elif strategy == TransferStrategy.ADAPTED:
            adapted_content, adapted_code = await self._transfer_adapted(
                knowledge, context
            )
        elif strategy == TransferStrategy.SELECTIVE:
            adapted_content, adapted_code = self._transfer_selective(
                knowledge, context
            )
        else:
            adapted_content, adapted_code = await self._transfer_merged(
                knowledge, context
            )

        # Validate
        valid, validation_notes = self._validate_transfer(
            adapted_content, adapted_code, context
        )

        # Calculate confidence
        confidence = self._calculate_confidence(
            knowledge, context, valid
        )

        # Update stats
        if valid:
            self.stats["successful_transfers"] += 1
            knowledge.transfers += 1
            # Update success rate
            total = knowledge.transfers
            knowledge.success_rate = (
                (knowledge.success_rate * (total - 1) + 1.0) / total
            )

        return TransferResult(
            knowledge_id=knowledge_id,
            strategy=strategy,
            success=valid,
            adapted_content=adapted_content,
            adapted_code=adapted_code,
            validation_passed=valid,
            validation_notes=validation_notes,
            confidence=confidence,
            transfer_time_ms=(time.time() - start_time) * 1000,
        )

    def _check_applicability(
        self,
        knowledge: TransferableKnowledge,
        context: TransferContext,
    ) -> Tuple[bool, List[str]]:
        """Check if knowledge is applicable."""
        notes = []

        # Check requirements
        for req in knowledge.requirements:
            if req not in context.requirements:
                notes.append(f"Missing requirement: {req}")

        # Check constraints
        for constraint in knowledge.constraints:
            if constraint in context.constraints:
                notes.append(f"Conflicting constraint: {constraint}")
                return False, notes

        # Always applicable with notes
        return True, notes

    def _transfer_direct(
        self,
        knowledge: TransferableKnowledge,
    ) -> Tuple[Dict[str, Any], str]:
        """Transfer directly without adaptation."""
        return knowledge.content.copy(), knowledge.code_template

    async def _transfer_adapted(
        self,
        knowledge: TransferableKnowledge,
        context: TransferContext,
    ) -> Tuple[Dict[str, Any], str]:
        """Transfer with adaptation."""
        content = knowledge.content.copy()
        code = knowledge.code_template

        # Language adaptation
        source_lang = knowledge.source_context.get("language", "python")
        target_lang = context.language or "python"

        if source_lang != target_lang:
            adapter_key = f"{source_lang}_to_{target_lang}"
            if adapter_key in self._adapters:
                code = self._adapters[adapter_key](code)

        # Framework adaptation
        if context.framework:
            code = self._adapt_to_framework(code, context.framework)

        return content, code

    def _transfer_selective(
        self,
        knowledge: TransferableKnowledge,
        context: TransferContext,
    ) -> Tuple[Dict[str, Any], str]:
        """Transfer selected parts."""
        # Select only relevant content
        content = {}

        for key, value in knowledge.content.items():
            # Check if key is relevant to context
            if self._is_relevant(key, context):
                content[key] = value

        # Select relevant code portions
        code = knowledge.code_template
        if code:
            code = self._select_code_portions(code, context)

        return content, code

    async def _transfer_merged(
        self,
        knowledge: TransferableKnowledge,
        context: TransferContext,
    ) -> Tuple[Dict[str, Any], str]:
        """Transfer by merging with existing."""
        content = knowledge.content.copy()
        code = knowledge.code_template

        # Merge with existing patterns
        for pattern in context.existing_patterns:
            if pattern in content.get("compatible_patterns", []):
                # Merge logic here
                pass

        return content, code

    def _is_relevant(self, key: str, context: TransferContext) -> bool:
        """Check if content key is relevant to context."""
        # Simple relevance check
        relevant_keywords = [
            context.project_type,
            context.language,
            context.framework,
        ]

        return any(kw and kw.lower() in key.lower() for kw in relevant_keywords)

    def _select_code_portions(
        self,
        code: str,
        context: TransferContext,
    ) -> str:
        """Select relevant code portions."""
        # For now, return full code
        # Could implement smarter selection
        return code

    def _adapt_python_to_js(self, code: str) -> str:
        """Adapt Python code to JavaScript."""
        # Simple transformations
        adapted = code

        # def -> function
        adapted = adapted.replace("def ", "function ")

        # self. -> this.
        adapted = adapted.replace("self.", "this.")

        # None -> null
        adapted = adapted.replace("None", "null")

        # True/False -> true/false
        adapted = adapted.replace("True", "true")
        adapted = adapted.replace("False", "false")

        # Remove type hints
        import re
        adapted = re.sub(r":\s*\w+(?:\[[\w,\s]+\])?\s*=", " =", adapted)
        adapted = re.sub(r"->\s*\w+(?:\[[\w,\s]+\])?:", ":", adapted)

        return adapted

    def _adapt_js_to_python(self, code: str) -> str:
        """Adapt JavaScript code to Python."""
        adapted = code

        # function -> def
        adapted = adapted.replace("function ", "def ")

        # this. -> self.
        adapted = adapted.replace("this.", "self.")

        # null -> None
        adapted = adapted.replace("null", "None")

        # true/false -> True/False
        adapted = adapted.replace("true", "True")
        adapted = adapted.replace("false", "False")

        # let/const/var -> remove
        import re
        adapted = re.sub(r"\b(let|const|var)\s+", "", adapted)

        return adapted

    def _adapt_to_framework(self, code: str, framework: str) -> str:
        """Adapt code to specific framework."""
        # Framework-specific adaptations
        if framework.lower() == "fastapi":
            # Add FastAPI imports if needed
            if "async def" in code and "from fastapi" not in code:
                code = "from fastapi import FastAPI, HTTPException\n\n" + code
        elif framework.lower() == "django":
            if "class" in code and "from django" not in code:
                code = "from django.views import View\n\n" + code

        return code

    def _validate_transfer(
        self,
        content: Dict[str, Any],
        code: str,
        context: TransferContext,
    ) -> Tuple[bool, List[str]]:
        """Validate transferred knowledge."""
        notes = []
        valid = True

        # Check code validity (basic)
        if code:
            if context.language == "python":
                try:
                    compile(code, "<string>", "exec")
                except SyntaxError as e:
                    valid = False
                    notes.append(f"Syntax error: {e}")

        # Check content completeness
        if not content:
            notes.append("Empty content after transfer")

        return valid, notes

    def _calculate_confidence(
        self,
        knowledge: TransferableKnowledge,
        context: TransferContext,
        valid: bool,
    ) -> float:
        """Calculate transfer confidence."""
        confidence = 0.5

        # Valid transfer
        if valid:
            confidence += 0.3

        # High success rate
        if knowledge.success_rate > 0.8:
            confidence += 0.1

        # Same language
        if knowledge.source_context.get("language") == context.language:
            confidence += 0.1

        return min(1.0, confidence)

    def find_knowledge(
        self,
        query: str,
        knowledge_type: Optional[KnowledgeType] = None,
        limit: int = 10,
    ) -> List[TransferableKnowledge]:
        """Find knowledge matching query."""
        results = []

        query_lower = query.lower()

        for knowledge in self.knowledge_index.values():
            score = 0

            # Type filter
            if knowledge_type and knowledge.type != knowledge_type:
                continue

            # Name match
            if query_lower in knowledge.name.lower():
                score += 3

            # Description match
            if query_lower in knowledge.description.lower():
                score += 2

            # Tag match
            if any(query_lower in tag.lower() for tag in knowledge.tags):
                score += 1

            if score > 0:
                results.append((knowledge, score))

        # Sort by score
        results.sort(key=lambda x: x[1], reverse=True)

        return [k for k, _ in results[:limit]]

    def get_stats(self) -> Dict[str, Any]:
        """Get transfer statistics."""
        success_rate = 0.0
        if self.stats["transfers"] > 0:
            success_rate = self.stats["successful_transfers"] / self.stats["transfers"]

        return {
            **self.stats,
            "knowledge_bases": len(self.bases),
            "success_rate": success_rate,
        }


def demo():
    """Demonstrate knowledge transfer."""
    import asyncio

    print("=" * 60)
    print("BAEL Knowledge Transfer Demo")
    print("=" * 60)

    transfer = KnowledgeTransfer()

    # Create knowledge base
    base = transfer.create_base(
        name="Python Patterns",
        description="Common Python patterns and solutions",
    )
    print(f"\nCreated knowledge base: {base.name}")

    # Create knowledge
    knowledge = transfer.create_knowledge(
        name="Singleton Pattern",
        description="Ensure a class has only one instance",
        knowledge_type=KnowledgeType.PATTERN,
        content={
            "purpose": "Single instance management",
            "use_cases": ["Database connections", "Configuration", "Logging"],
        },
        code_template='''
class Singleton:
    _instance: Optional["Singleton"] = None

    def __new__(cls) -> "Singleton":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
''',
        requirements=["class-based OOP"],
        tags=["design-pattern", "creational"],
    )

    transfer.add_knowledge(base.id, knowledge)
    print(f"Added knowledge: {knowledge.name}")

    # Transfer to JavaScript context
    context = TransferContext(
        project_type="web_backend",
        language="javascript",
        framework="express",
    )

    async def do_transfer():
        return await transfer.transfer(
            knowledge.id,
            context,
            strategy=TransferStrategy.ADAPTED,
        )

    result = asyncio.run(do_transfer())

    print(f"\nTransfer result:")
    print(f"  Success: {result.success}")
    print(f"  Confidence: {result.confidence:.2f}")
    print(f"  Strategy: {result.strategy.value}")

    if result.adapted_code:
        print(f"\nAdapted code:")
        print("-" * 40)
        print(result.adapted_code[:300])
        print("-" * 40)

    # Find knowledge
    found = transfer.find_knowledge("singleton")
    print(f"\nSearch 'singleton': {len(found)} results")

    print(f"\nStats: {transfer.get_stats()}")


if __name__ == "__main__":
    demo()

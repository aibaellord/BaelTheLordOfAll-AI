"""
BAEL Task Classifier
=====================

Ultra-intelligent task classification for optimal LLM routing.
Analyzes requests to determine task type, complexity, and requirements.

Features:
- Multi-signal task type detection
- Complexity estimation (token count, reasoning depth)
- Capability requirement extraction
- Context-aware classification
- Learning from routing outcomes
- Pattern recognition for recurring tasks
"""

import hashlib
import json
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Set, Tuple


class TaskType(Enum):
    """Primary task categories for routing."""
    CODE_GENERATION = "code_generation"
    CODE_REVIEW = "code_review"
    CODE_DEBUG = "code_debug"
    CODE_REFACTOR = "code_refactor"
    CODE_EXPLAIN = "code_explain"

    REASONING_ANALYTICAL = "reasoning_analytical"
    REASONING_MATHEMATICAL = "reasoning_mathematical"
    REASONING_LOGICAL = "reasoning_logical"
    REASONING_CAUSAL = "reasoning_causal"

    CREATIVE_WRITING = "creative_writing"
    CREATIVE_BRAINSTORM = "creative_brainstorm"
    CREATIVE_DESIGN = "creative_design"

    RESEARCH_SYNTHESIS = "research_synthesis"
    RESEARCH_ANALYSIS = "research_analysis"
    RESEARCH_COMPARISON = "research_comparison"

    CONVERSATION_GENERAL = "conversation_general"
    CONVERSATION_QA = "conversation_qa"
    CONVERSATION_INSTRUCTION = "conversation_instruction"

    DATA_EXTRACTION = "data_extraction"
    DATA_TRANSFORMATION = "data_transformation"
    DATA_ANALYSIS = "data_analysis"

    VISION_ANALYSIS = "vision_analysis"
    VISION_OCR = "vision_ocr"
    VISION_GENERATION = "vision_generation"

    FUNCTION_CALLING = "function_calling"
    STRUCTURED_OUTPUT = "structured_output"

    TRANSLATION = "translation"
    SUMMARIZATION = "summarization"

    SECURITY_ANALYSIS = "security_analysis"
    SECURITY_EXPLOIT = "security_exploit"

    UNKNOWN = "unknown"


class TaskComplexity(Enum):
    """Task complexity levels."""
    TRIVIAL = 1      # Simple lookup, <100 tokens
    SIMPLE = 2       # Basic task, <500 tokens
    MODERATE = 3     # Standard task, <2000 tokens
    COMPLEX = 4      # Multi-step reasoning, <8000 tokens
    VERY_COMPLEX = 5 # Deep analysis, <32000 tokens
    EXTREME = 6      # Maximum capability required


class ModelCapabilityRequired(Enum):
    """Capabilities required for task."""
    BASIC = "basic"
    CODE = "code"
    REASONING = "reasoning"
    LONG_CONTEXT = "long_context"
    VISION = "vision"
    FUNCTION_CALLING = "function_calling"
    STRUCTURED_OUTPUT = "structured_output"
    FAST_RESPONSE = "fast_response"
    CREATIVE = "creative"
    UNCENSORED = "uncensored"
    MULTILINGUAL = "multilingual"
    MATH = "math"


@dataclass
class ClassificationResult:
    """Result of task classification."""
    primary_type: TaskType
    secondary_types: List[TaskType] = field(default_factory=list)
    complexity: TaskComplexity = TaskComplexity.MODERATE
    capabilities_required: Set[ModelCapabilityRequired] = field(default_factory=set)
    estimated_tokens: int = 1000
    estimated_reasoning_steps: int = 1
    confidence: float = 0.8
    signals: Dict[str, float] = field(default_factory=dict)
    recommended_models: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class TaskClassifier:
    """
    Intelligent task classifier using multi-signal analysis.
    """

    # Keyword patterns for task detection
    TASK_PATTERNS: Dict[TaskType, Dict[str, Any]] = {
        TaskType.CODE_GENERATION: {
            "keywords": [
                "write", "create", "implement", "code", "function", "class",
                "script", "program", "build", "develop", "generate code"
            ],
            "regex": [
                r"write\s+(a\s+)?(\w+\s+)?(function|class|script|program)",
                r"implement\s+",
                r"create\s+(a\s+)?(\w+\s+)?(function|class|method)",
            ],
            "capability": ModelCapabilityRequired.CODE,
        },
        TaskType.CODE_DEBUG: {
            "keywords": [
                "debug", "fix", "error", "bug", "issue", "broken",
                "not working", "fails", "exception", "traceback"
            ],
            "regex": [
                r"(fix|debug|solve)\s+(this|the)\s+(error|bug|issue)",
                r"why\s+(is|does)\s+(this|my)\s+code",
                r"getting\s+(an?\s+)?(error|exception)",
            ],
            "capability": ModelCapabilityRequired.CODE,
        },
        TaskType.CODE_REVIEW: {
            "keywords": [
                "review", "improve", "optimize", "best practice",
                "code quality", "clean code", "refactor suggestion"
            ],
            "regex": [
                r"review\s+(this|my)\s+code",
                r"how\s+can\s+i\s+improve",
                r"is\s+this\s+(good|bad|correct)",
            ],
            "capability": ModelCapabilityRequired.CODE,
        },
        TaskType.REASONING_MATHEMATICAL: {
            "keywords": [
                "calculate", "compute", "solve", "equation", "formula",
                "math", "mathematical", "derivative", "integral", "proof"
            ],
            "regex": [
                r"(calculate|compute|solve)\s+",
                r"what\s+is\s+\d+\s*[\+\-\*\/]",
                r"(prove|derive|show)\s+that",
            ],
            "capability": ModelCapabilityRequired.MATH,
        },
        TaskType.REASONING_ANALYTICAL: {
            "keywords": [
                "analyze", "evaluate", "assess", "examine", "investigate",
                "study", "explore", "understand", "explain why"
            ],
            "regex": [
                r"(analyze|evaluate|assess)\s+",
                r"why\s+(do|does|is|are|would|should)",
                r"explain\s+(why|how|the\s+reason)",
            ],
            "capability": ModelCapabilityRequired.REASONING,
        },
        TaskType.REASONING_LOGICAL: {
            "keywords": [
                "logic", "logical", "if then", "therefore", "conclude",
                "deduce", "infer", "implies", "follows that"
            ],
            "regex": [
                r"if\s+.+\s+then\s+.+",
                r"(what|which)\s+(follows|can\s+be\s+(deduced|inferred))",
            ],
            "capability": ModelCapabilityRequired.REASONING,
        },
        TaskType.CREATIVE_WRITING: {
            "keywords": [
                "write", "story", "poem", "essay", "article", "blog",
                "creative", "fiction", "narrative", "dialogue"
            ],
            "regex": [
                r"write\s+(a\s+)?(short\s+)?(story|poem|essay|article)",
                r"(create|compose)\s+(a\s+)?(piece|work)",
            ],
            "capability": ModelCapabilityRequired.CREATIVE,
        },
        TaskType.CREATIVE_BRAINSTORM: {
            "keywords": [
                "brainstorm", "ideas", "suggest", "creative", "innovative",
                "alternatives", "options", "possibilities", "think of"
            ],
            "regex": [
                r"(give|suggest|generate)\s+(me\s+)?(some\s+)?ideas",
                r"brainstorm\s+",
                r"what\s+(are\s+)?(some|different)\s+(ways|approaches)",
            ],
            "capability": ModelCapabilityRequired.CREATIVE,
        },
        TaskType.RESEARCH_SYNTHESIS: {
            "keywords": [
                "research", "synthesize", "combine", "integrate", "comprehensive",
                "overview", "survey", "literature review"
            ],
            "regex": [
                r"(research|explore|investigate)\s+",
                r"(comprehensive|detailed)\s+(overview|analysis)",
            ],
            "capability": ModelCapabilityRequired.REASONING,
        },
        TaskType.DATA_EXTRACTION: {
            "keywords": [
                "extract", "parse", "get", "find", "identify", "list",
                "from this", "from the following"
            ],
            "regex": [
                r"extract\s+(the\s+)?\w+\s+from",
                r"(get|find|identify)\s+(all\s+)?(the\s+)?",
            ],
            "capability": ModelCapabilityRequired.BASIC,
        },
        TaskType.SUMMARIZATION: {
            "keywords": [
                "summarize", "summary", "tldr", "brief", "shorten",
                "condense", "key points", "main points"
            ],
            "regex": [
                r"(summarize|give\s+(me\s+)?a\s+summary)",
                r"(what\s+are\s+)?(the\s+)?(main|key)\s+points",
            ],
            "capability": ModelCapabilityRequired.BASIC,
        },
        TaskType.TRANSLATION: {
            "keywords": [
                "translate", "translation", "convert to", "in spanish",
                "in french", "in chinese", "to english"
            ],
            "regex": [
                r"translate\s+(this\s+)?(to|into)\s+\w+",
                r"(in|to)\s+(spanish|french|german|chinese|japanese|korean)",
            ],
            "capability": ModelCapabilityRequired.MULTILINGUAL,
        },
        TaskType.FUNCTION_CALLING: {
            "keywords": [
                "use tool", "call function", "execute", "run command",
                "search for", "look up", "fetch"
            ],
            "regex": [
                r"(use|call|execute|run)\s+(the\s+)?\w+\s+(tool|function)",
            ],
            "capability": ModelCapabilityRequired.FUNCTION_CALLING,
        },
        TaskType.STRUCTURED_OUTPUT: {
            "keywords": [
                "json", "xml", "yaml", "structured", "format as",
                "output format", "schema", "table"
            ],
            "regex": [
                r"(output|format|return)\s+(as\s+)?(json|xml|yaml)",
                r"in\s+(json|xml|yaml)\s+format",
            ],
            "capability": ModelCapabilityRequired.STRUCTURED_OUTPUT,
        },
        TaskType.SECURITY_ANALYSIS: {
            "keywords": [
                "security", "vulnerability", "exploit", "hack", "penetration",
                "pentest", "attack", "threat", "risk assessment"
            ],
            "regex": [
                r"(find|identify|analyze)\s+(security\s+)?(vulnerabilit|threat|risk)",
                r"(how\s+to\s+)?(exploit|hack|attack)",
            ],
            "capability": ModelCapabilityRequired.UNCENSORED,
        },
    }

    # Complexity indicators
    COMPLEXITY_SIGNALS = {
        "token_thresholds": [
            (100, TaskComplexity.TRIVIAL),
            (500, TaskComplexity.SIMPLE),
            (2000, TaskComplexity.MODERATE),
            (8000, TaskComplexity.COMPLEX),
            (32000, TaskComplexity.VERY_COMPLEX),
        ],
        "complexity_keywords": {
            TaskComplexity.COMPLEX: [
                "step by step", "detailed", "comprehensive", "thorough",
                "in-depth", "complete", "full"
            ],
            TaskComplexity.VERY_COMPLEX: [
                "extremely detailed", "exhaustive", "everything about",
                "all aspects", "deep dive"
            ],
        },
    }

    # Model recommendations by capability
    MODEL_RECOMMENDATIONS = {
        ModelCapabilityRequired.CODE: [
            "claude-3.5-sonnet", "deepseek-coder", "gpt-4o", "codellama"
        ],
        ModelCapabilityRequired.REASONING: [
            "deepseek-r1", "claude-3-opus", "o1-preview", "gpt-4-turbo"
        ],
        ModelCapabilityRequired.MATH: [
            "deepseek-r1", "o1-preview", "claude-3.5-sonnet", "gpt-4o"
        ],
        ModelCapabilityRequired.CREATIVE: [
            "claude-3-opus", "gpt-4o", "claude-3.5-sonnet"
        ],
        ModelCapabilityRequired.FAST_RESPONSE: [
            "gpt-4o-mini", "llama-3.1-8b", "gemini-2.0-flash", "groq-mixtral"
        ],
        ModelCapabilityRequired.VISION: [
            "gpt-4o", "claude-3.5-sonnet", "gemini-2.0-flash"
        ],
        ModelCapabilityRequired.UNCENSORED: [
            "llama-3.3-70b", "mistral-large", "mixtral-8x7b"
        ],
    }

    def __init__(self):
        self.classification_history: List[Dict[str, Any]] = []
        self.pattern_cache: Dict[str, ClassificationResult] = {}

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count from text."""
        # Rough estimation: ~4 chars per token
        return len(text) // 4

    def _detect_task_types(
        self,
        text: str,
    ) -> Dict[TaskType, float]:
        """Detect task types from text with confidence scores."""
        text_lower = text.lower()
        scores: Dict[TaskType, float] = defaultdict(float)

        for task_type, patterns in self.TASK_PATTERNS.items():
            # Keyword matching
            keywords = patterns.get("keywords", [])
            keyword_matches = sum(1 for kw in keywords if kw in text_lower)
            if keyword_matches > 0:
                scores[task_type] += min(keyword_matches * 0.15, 0.5)

            # Regex matching
            regexes = patterns.get("regex", [])
            for regex in regexes:
                if re.search(regex, text_lower):
                    scores[task_type] += 0.3

        return dict(scores)

    def _determine_complexity(
        self,
        text: str,
        context_length: int = 0,
    ) -> Tuple[TaskComplexity, int]:
        """Determine task complexity."""
        text_lower = text.lower()
        total_tokens = self._estimate_tokens(text) + context_length

        # Base complexity from token count
        base_complexity = TaskComplexity.MODERATE
        for threshold, complexity in self.COMPLEXITY_SIGNALS["token_thresholds"]:
            if total_tokens <= threshold:
                base_complexity = complexity
                break
        else:
            base_complexity = TaskComplexity.EXTREME

        # Adjust based on complexity keywords
        for complexity, keywords in self.COMPLEXITY_SIGNALS["complexity_keywords"].items():
            if any(kw in text_lower for kw in keywords):
                if complexity.value > base_complexity.value:
                    base_complexity = complexity

        # Estimate reasoning steps
        reasoning_indicators = [
            "step by step", "first", "then", "finally", "because",
            "therefore", "however", "although", "considering"
        ]
        reasoning_steps = sum(1 for ind in reasoning_indicators if ind in text_lower)
        reasoning_steps = max(1, reasoning_steps)

        return base_complexity, reasoning_steps

    def _extract_capabilities(
        self,
        text: str,
        detected_types: Dict[TaskType, float],
    ) -> Set[ModelCapabilityRequired]:
        """Extract required capabilities from task."""
        capabilities = set()
        text_lower = text.lower()

        # Add capabilities from detected task types
        for task_type, score in detected_types.items():
            if score > 0.2:
                patterns = self.TASK_PATTERNS.get(task_type, {})
                if cap := patterns.get("capability"):
                    capabilities.add(cap)

        # Detect additional capability signals
        if any(word in text_lower for word in ["image", "picture", "photo", "screenshot"]):
            capabilities.add(ModelCapabilityRequired.VISION)

        if any(word in text_lower for word in ["fast", "quick", "immediately", "asap"]):
            capabilities.add(ModelCapabilityRequired.FAST_RESPONSE)

        if any(word in text_lower for word in ["json", "xml", "structured", "schema"]):
            capabilities.add(ModelCapabilityRequired.STRUCTURED_OUTPUT)

        if any(word in text_lower for word in ["tool", "function", "search", "execute"]):
            capabilities.add(ModelCapabilityRequired.FUNCTION_CALLING)

        if len(text) > 50000:
            capabilities.add(ModelCapabilityRequired.LONG_CONTEXT)

        # Default to basic if nothing detected
        if not capabilities:
            capabilities.add(ModelCapabilityRequired.BASIC)

        return capabilities

    def _get_model_recommendations(
        self,
        capabilities: Set[ModelCapabilityRequired],
    ) -> List[str]:
        """Get model recommendations based on required capabilities."""
        all_models: Dict[str, int] = defaultdict(int)

        for cap in capabilities:
            for model in self.MODEL_RECOMMENDATIONS.get(cap, []):
                all_models[model] += 1

        # Sort by frequency (models that match multiple capabilities first)
        sorted_models = sorted(all_models.keys(), key=lambda m: -all_models[m])
        return sorted_models[:5]

    def classify(
        self,
        messages: List[Dict[str, str]],
        context: Optional[Dict[str, Any]] = None,
    ) -> ClassificationResult:
        """
        Classify a task from messages.

        Args:
            messages: List of message dicts with role and content
            context: Optional additional context

        Returns:
            ClassificationResult with task analysis
        """
        # Extract text from messages
        text = " ".join(
            m.get("content", "") for m in messages
            if m.get("role") in ("user", "system")
        )

        # Check cache
        text_hash = hashlib.md5(text.encode()).hexdigest()[:16]
        if text_hash in self.pattern_cache:
            return self.pattern_cache[text_hash]

        # Detect task types
        type_scores = self._detect_task_types(text)

        # Determine primary and secondary types
        sorted_types = sorted(type_scores.items(), key=lambda x: -x[1])
        primary_type = sorted_types[0][0] if sorted_types else TaskType.UNKNOWN
        secondary_types = [t for t, s in sorted_types[1:4] if s > 0.2]

        # Determine complexity
        context_length = context.get("context_length", 0) if context else 0
        complexity, reasoning_steps = self._determine_complexity(text, context_length)

        # Extract capabilities
        capabilities = self._extract_capabilities(text, type_scores)

        # Get model recommendations
        recommended_models = self._get_model_recommendations(capabilities)

        # Calculate confidence
        max_score = max(type_scores.values()) if type_scores else 0
        confidence = min(0.95, max_score + 0.3) if max_score > 0 else 0.5

        result = ClassificationResult(
            primary_type=primary_type,
            secondary_types=secondary_types,
            complexity=complexity,
            capabilities_required=capabilities,
            estimated_tokens=self._estimate_tokens(text),
            estimated_reasoning_steps=reasoning_steps,
            confidence=confidence,
            signals=type_scores,
            recommended_models=recommended_models,
            metadata={
                "text_length": len(text),
                "message_count": len(messages),
            },
        )

        # Cache result
        self.pattern_cache[text_hash] = result

        return result

    def get_routing_hint(
        self,
        classification: ClassificationResult,
    ) -> str:
        """Get routing hint for multi-provider router."""
        # Map task types to routing hints
        type_hints = {
            TaskType.CODE_GENERATION: "code",
            TaskType.CODE_REVIEW: "code",
            TaskType.CODE_DEBUG: "code",
            TaskType.CODE_REFACTOR: "code",
            TaskType.REASONING_ANALYTICAL: "reasoning",
            TaskType.REASONING_MATHEMATICAL: "reasoning",
            TaskType.REASONING_LOGICAL: "reasoning",
            TaskType.CREATIVE_WRITING: "creative",
            TaskType.CREATIVE_BRAINSTORM: "creative",
        }

        hint = type_hints.get(classification.primary_type, "general")

        # Override with fast if simple/trivial
        if classification.complexity in (TaskComplexity.TRIVIAL, TaskComplexity.SIMPLE):
            if ModelCapabilityRequired.FAST_RESPONSE in classification.capabilities_required:
                hint = "fast"

        return hint


def demo():
    """Demonstrate task classification."""
    classifier = TaskClassifier()

    test_cases = [
        "Write a Python function to merge two sorted lists",
        "Why does the economy work the way it does? Analyze in detail.",
        "Write a short poem about autumn leaves",
        "Fix this error: TypeError: cannot unpack non-iterable NoneType object",
        "What is 2 + 2?",
        "Translate 'Hello World' to French",
        "Extract all email addresses from this text: contact@example.com and info@test.org",
        "How can I exploit this SQL injection vulnerability?",
    ]

    print("=" * 60)
    print("BAEL Task Classifier Demo")
    print("=" * 60)

    for text in test_cases:
        messages = [{"role": "user", "content": text}]
        result = classifier.classify(messages)

        print(f"\nInput: {text[:60]}...")
        print(f"  Type: {result.primary_type.value}")
        print(f"  Complexity: {result.complexity.name}")
        print(f"  Capabilities: {[c.value for c in result.capabilities_required]}")
        print(f"  Confidence: {result.confidence:.2f}")
        print(f"  Models: {result.recommended_models[:3]}")
        print(f"  Routing hint: {classifier.get_routing_hint(result)}")


if __name__ == "__main__":
    demo()

"""
Token Optimizer - Maximum LLM Efficiency
=========================================

Hidden techniques for minimizing token usage while maximizing output quality.

"Every token is a precious resource - waste none." — Ba'el
"""

import re
import logging
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger("BAEL.HiddenTechniques.TokenOptimizer")


class OptimizationStrategy(Enum):
    """Token optimization strategies."""
    AGGRESSIVE = "aggressive"      # Maximum compression
    BALANCED = "balanced"          # Quality + efficiency
    CONSERVATIVE = "conservative"  # Preserve clarity
    CONTEXT_AWARE = "context_aware"  # Adapts to content
    SEMANTIC = "semantic"          # Meaning-preserving
    STRUCTURAL = "structural"      # Format optimization


class ContentType(Enum):
    """Content type classification."""
    CODE = "code"
    PROSE = "prose"
    DATA = "data"
    MIXED = "mixed"
    TECHNICAL = "technical"
    CONVERSATIONAL = "conversational"


@dataclass
class OptimizationResult:
    """Result of token optimization."""
    original_text: str
    optimized_text: str
    original_tokens: int
    optimized_tokens: int
    savings_percent: float
    strategies_applied: List[str]
    quality_score: float  # 0-1, how well meaning was preserved


@dataclass
class TokenStats:
    """Token usage statistics."""
    total_saved: int = 0
    total_processed: int = 0
    average_savings: float = 0.0
    best_savings: float = 0.0
    optimizations_performed: int = 0


class TokenOptimizer:
    """
    Ultimate token optimization engine.

    Applies multiple hidden techniques to minimize token usage
    while preserving meaning and quality.
    """

    # Common word replacements (shorter synonyms)
    WORD_REPLACEMENTS = {
        "approximately": "~",
        "implementation": "impl",
        "functionality": "function",
        "configuration": "config",
        "documentation": "docs",
        "authentication": "auth",
        "authorization": "authz",
        "additionally": "also",
        "furthermore": "also",
        "nevertheless": "but",
        "consequently": "so",
        "subsequently": "then",
        "simultaneously": "together",
        "characteristics": "traits",
        "infrastructure": "infra",
        "requirements": "reqs",
        "specifications": "specs",
        "information": "info",
        "demonstration": "demo",
        "application": "app",
        "development": "dev",
        "environment": "env",
        "repository": "repo",
        "directory": "dir",
        "parameters": "params",
        "arguments": "args",
        "variables": "vars",
        "constants": "consts",
        "modifications": "mods",
        "dependencies": "deps",
        "permissions": "perms",
        "transactions": "txns",
        "organizations": "orgs",
    }

    # Phrase compressions
    PHRASE_COMPRESSIONS = {
        "in order to": "to",
        "as well as": "&",
        "due to the fact that": "because",
        "in the event that": "if",
        "at this point in time": "now",
        "with regard to": "about",
        "in spite of": "despite",
        "on the other hand": "but",
        "for the purpose of": "for",
        "in addition to": "+",
        "with the exception of": "except",
        "in the case of": "for",
        "as a result of": "from",
        "by means of": "via",
        "it is important to note that": "note:",
        "it should be noted that": "note:",
        "please be aware that": "note:",
        "take into consideration": "consider",
        "make a decision": "decide",
        "come to a conclusion": "conclude",
        "is able to": "can",
        "has the ability to": "can",
        "is not able to": "cannot",
        "in the near future": "soon",
        "at a later time": "later",
        "for example": "e.g.",
        "that is to say": "i.e.",
        "and so on": "etc.",
        "the majority of": "most",
        "a number of": "some",
        "a large number of": "many",
    }

    # Redundancy patterns to remove
    REDUNDANCY_PATTERNS = [
        (r'\b(very|really|quite|rather|somewhat|fairly)\s+(unique|perfect|complete|absolute|total|entire|whole)\b', r'\2'),
        (r'\b(absolutely|completely|totally|entirely)\s+(essential|necessary|required|mandatory)\b', r'\2'),
        (r'\b(past|previous)\s+history\b', 'history'),
        (r'\b(future|advance)\s+planning\b', 'planning'),
        (r'\b(final|end)\s+result\b', 'result'),
        (r'\b(basic|fundamental)\s+fundamentals\b', 'fundamentals'),
        (r'\b(new|novel)\s+innovation\b', 'innovation'),
        (r'\b(true|actual)\s+facts?\b', 'facts'),
        (r'\b(close|near)\s+proximity\b', 'proximity'),
        (r'\bfirst\s+begin\b', 'begin'),
        (r'\bstill\s+remains\b', 'remains'),
        (r'\bjoin\s+together\b', 'join'),
        (r'\blend\s+up\b', 'end'),
        (r'\bpersonal\s+opinion\b', 'opinion'),
    ]

    def __init__(self, strategy: OptimizationStrategy = OptimizationStrategy.BALANCED):
        self.strategy = strategy
        self.stats = TokenStats()
        self._cache: Dict[int, OptimizationResult] = {}

    def optimize(self, text: str, content_type: ContentType = None) -> OptimizationResult:
        """
        Optimize text to minimize tokens.

        Args:
            text: Input text to optimize
            content_type: Type of content (auto-detected if None)

        Returns:
            OptimizationResult with optimized text and stats
        """
        # Check cache
        text_hash = hash(text)
        if text_hash in self._cache:
            return self._cache[text_hash]

        # Auto-detect content type
        if content_type is None:
            content_type = self._detect_content_type(text)

        original_tokens = self._estimate_tokens(text)
        optimized = text
        strategies_applied = []

        # Apply optimizations based on strategy
        if self.strategy in (OptimizationStrategy.AGGRESSIVE, OptimizationStrategy.BALANCED):
            optimized, applied = self._apply_phrase_compressions(optimized)
            strategies_applied.extend(applied)

        if self.strategy in (OptimizationStrategy.AGGRESSIVE, OptimizationStrategy.BALANCED, OptimizationStrategy.SEMANTIC):
            optimized, applied = self._apply_word_replacements(optimized)
            strategies_applied.extend(applied)

        if self.strategy != OptimizationStrategy.CONSERVATIVE:
            optimized, applied = self._remove_redundancies(optimized)
            strategies_applied.extend(applied)

        if self.strategy in (OptimizationStrategy.AGGRESSIVE, OptimizationStrategy.STRUCTURAL):
            optimized, applied = self._compress_whitespace(optimized)
            strategies_applied.extend(applied)

        if content_type != ContentType.CODE:
            optimized, applied = self._remove_filler_words(optimized)
            strategies_applied.extend(applied)

        # Calculate stats
        optimized_tokens = self._estimate_tokens(optimized)
        savings = (1 - optimized_tokens / original_tokens) * 100 if original_tokens > 0 else 0

        # Quality score (based on content preservation)
        quality = self._calculate_quality(text, optimized)

        result = OptimizationResult(
            original_text=text,
            optimized_text=optimized,
            original_tokens=original_tokens,
            optimized_tokens=optimized_tokens,
            savings_percent=savings,
            strategies_applied=strategies_applied,
            quality_score=quality,
        )

        # Update stats
        self.stats.total_saved += original_tokens - optimized_tokens
        self.stats.total_processed += original_tokens
        self.stats.optimizations_performed += 1
        self.stats.average_savings = (self.stats.total_saved / self.stats.total_processed * 100) if self.stats.total_processed > 0 else 0
        if savings > self.stats.best_savings:
            self.stats.best_savings = savings

        # Cache result
        self._cache[text_hash] = result

        return result

    def optimize_prompt(self, prompt: str, max_tokens: int = None) -> str:
        """
        Optimize a prompt for LLM usage.

        Special handling for prompts to preserve instruction clarity.
        """
        result = self.optimize(prompt, ContentType.TECHNICAL)

        if max_tokens and result.optimized_tokens > max_tokens:
            # Apply more aggressive optimization
            old_strategy = self.strategy
            self.strategy = OptimizationStrategy.AGGRESSIVE
            result = self.optimize(prompt, ContentType.TECHNICAL)
            self.strategy = old_strategy

        return result.optimized_text

    def optimize_code_context(self, code: str) -> str:
        """
        Optimize code context for inclusion in prompts.

        Removes comments, compresses formatting, keeps logic.
        """
        optimized = code

        # Remove single-line comments
        optimized = re.sub(r'#[^\n]*\n', '\n', optimized)

        # Remove multi-line docstrings (but keep one-liners)
        optimized = re.sub(r'"""[\s\S]*?"""', '"""..."""', optimized)
        optimized = re.sub(r"'''[\s\S]*?'''", "'''...'''", optimized)

        # Compress multiple newlines
        optimized = re.sub(r'\n{3,}', '\n\n', optimized)

        # Remove trailing whitespace
        optimized = re.sub(r'[ \t]+$', '', optimized, flags=re.MULTILINE)

        return optimized

    def _detect_content_type(self, text: str) -> ContentType:
        """Detect content type from text."""
        # Code indicators
        code_patterns = [
            r'def\s+\w+\(', r'class\s+\w+:', r'import\s+\w+',
            r'function\s+\w+\(', r'const\s+\w+\s*=', r'=>',
            r'\{\s*\n', r'if\s*\(', r'for\s*\(',
        ]
        code_score = sum(1 for p in code_patterns if re.search(p, text))

        # Data indicators
        data_patterns = [r'\{[^}]+:[^}]+\}', r'\[[^\]]+\]', r'^\s*\d+', r'^\s*-\s+']
        data_score = sum(1 for p in data_patterns if re.search(p, text))

        if code_score > 3:
            return ContentType.CODE
        elif data_score > 2:
            return ContentType.DATA
        elif code_score > 0 or data_score > 0:
            return ContentType.MIXED
        else:
            return ContentType.PROSE

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count (rough approximation)."""
        # GPT tokenization is roughly 4 chars per token for English
        # But we count words + punctuation for better accuracy
        words = len(text.split())
        chars = len(text)
        # Tokens ≈ max(words, chars/4)
        return max(words, chars // 4)

    def _apply_phrase_compressions(self, text: str) -> Tuple[str, List[str]]:
        """Apply phrase-level compressions."""
        applied = []
        for phrase, replacement in self.PHRASE_COMPRESSIONS.items():
            if phrase.lower() in text.lower():
                text = re.sub(re.escape(phrase), replacement, text, flags=re.IGNORECASE)
                applied.append(f"phrase:{phrase[:20]}")
        return text, applied

    def _apply_word_replacements(self, text: str) -> Tuple[str, List[str]]:
        """Apply word-level replacements."""
        applied = []
        for word, replacement in self.WORD_REPLACEMENTS.items():
            pattern = r'\b' + word + r'\b'
            if re.search(pattern, text, re.IGNORECASE):
                text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
                applied.append(f"word:{word[:15]}")
        return text, applied

    def _remove_redundancies(self, text: str) -> Tuple[str, List[str]]:
        """Remove redundant phrases."""
        applied = []
        for pattern, replacement in self.REDUNDANCY_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
                applied.append("redundancy")
        return text, applied

    def _compress_whitespace(self, text: str) -> Tuple[str, List[str]]:
        """Compress whitespace."""
        original = text
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = text.strip()
        return text, ["whitespace"] if text != original else []

    def _remove_filler_words(self, text: str) -> Tuple[str, List[str]]:
        """Remove filler words that don't add meaning."""
        fillers = [
            r'\b(just|simply|basically|actually|literally|definitely|certainly|obviously|clearly)\b',
            r'\b(in my opinion|I think|I believe|I feel)\b',
        ]
        applied = []
        for pattern in fillers:
            if re.search(pattern, text, re.IGNORECASE):
                text = re.sub(pattern, '', text, flags=re.IGNORECASE)
                applied.append("filler")
        # Clean up double spaces
        text = re.sub(r'  +', ' ', text)
        return text, applied

    def _calculate_quality(self, original: str, optimized: str) -> float:
        """Calculate quality score (meaning preservation)."""
        # Simple heuristic: ratio of word overlap
        original_words = set(original.lower().split())
        optimized_words = set(optimized.lower().split())

        if not original_words:
            return 1.0

        preserved = len(original_words & optimized_words) / len(original_words)

        # Penalize for excessive compression
        length_ratio = len(optimized) / len(original) if original else 1
        if length_ratio < 0.3:
            preserved *= 0.8  # Too aggressive

        return min(1.0, preserved)

    def get_stats(self) -> TokenStats:
        """Get optimization statistics."""
        return self.stats

    def clear_cache(self) -> None:
        """Clear the optimization cache."""
        self._cache.clear()


# =============================================================================
# ADVANCED TECHNIQUES
# =============================================================================

class SemanticCompressor:
    """
    Advanced semantic compression using meaning extraction.

    Extracts core meaning and reconstructs in minimal form.
    """

    def __init__(self):
        self.keyword_extractors = []

    def compress(self, text: str, target_ratio: float = 0.5) -> str:
        """
        Compress text to target ratio while preserving meaning.

        Args:
            text: Input text
            target_ratio: Target size as fraction of original

        Returns:
            Compressed text
        """
        sentences = self._split_sentences(text)

        if len(sentences) <= 1:
            return text

        # Score sentences by importance
        scored = [(s, self._score_importance(s, text)) for s in sentences]
        scored.sort(key=lambda x: x[1], reverse=True)

        # Keep top sentences until target ratio
        target_length = int(len(text) * target_ratio)
        result = []
        current_length = 0

        for sentence, score in scored:
            if current_length + len(sentence) <= target_length:
                result.append(sentence)
                current_length += len(sentence)
            else:
                break

        # Reorder to original sequence
        result.sort(key=lambda s: text.find(s))

        return ' '.join(result)

    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]

    def _score_importance(self, sentence: str, full_text: str) -> float:
        """Score sentence importance."""
        score = 0.0

        # Position bonus (first and last sentences often important)
        pos = full_text.find(sentence)
        if pos < len(full_text) * 0.2:
            score += 0.3
        elif pos > len(full_text) * 0.8:
            score += 0.2

        # Keyword indicators
        important_patterns = [
            r'\b(important|key|critical|essential|must|should|note)\b',
            r'\b(first|second|finally|conclusion|summary)\b',
            r'\b(because|therefore|thus|hence|so)\b',
        ]
        for pattern in important_patterns:
            if re.search(pattern, sentence, re.IGNORECASE):
                score += 0.15

        # Length penalty (very short or very long)
        words = len(sentence.split())
        if 5 <= words <= 25:
            score += 0.1

        return score


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def optimize_tokens(text: str, strategy: OptimizationStrategy = OptimizationStrategy.BALANCED) -> str:
    """Quick function to optimize tokens in text."""
    optimizer = TokenOptimizer(strategy)
    result = optimizer.optimize(text)
    return result.optimized_text


def get_token_savings(text: str) -> Dict[str, Any]:
    """Get token savings analysis for text."""
    optimizer = TokenOptimizer()
    result = optimizer.optimize(text)
    return {
        "original_tokens": result.original_tokens,
        "optimized_tokens": result.optimized_tokens,
        "savings_percent": result.savings_percent,
        "strategies_applied": result.strategies_applied,
        "quality_score": result.quality_score,
    }

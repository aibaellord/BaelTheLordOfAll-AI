"""
BAEL Source Validator
======================

Validates source credibility and reliability.
Assesses trustworthiness of information sources.

Features:
- Domain credibility scoring
- Content quality analysis
- Bias detection
- Fact checking
- Source verification
"""

import hashlib
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class CredibilityLevel(Enum):
    """Levels of source credibility."""
    HIGHLY_CREDIBLE = "highly_credible"
    CREDIBLE = "credible"
    SOMEWHAT_CREDIBLE = "somewhat_credible"
    QUESTIONABLE = "questionable"
    UNRELIABLE = "unreliable"
    UNKNOWN = "unknown"


class BiasType(Enum):
    """Types of content bias."""
    LEFT = "left"
    CENTER_LEFT = "center_left"
    CENTER = "center"
    CENTER_RIGHT = "center_right"
    RIGHT = "right"
    SCIENTIFIC = "scientific"
    PROMOTIONAL = "promotional"
    SATIRE = "satire"
    UNKNOWN = "unknown"


@dataclass
class SourceCredibility:
    """Credibility assessment of a source."""
    domain: str
    credibility_level: CredibilityLevel

    # Scores (0-1)
    overall_score: float = 0.5
    accuracy_score: float = 0.5
    transparency_score: float = 0.5
    expertise_score: float = 0.5

    # Bias
    bias_type: BiasType = BiasType.UNKNOWN
    bias_score: float = 0.5  # 0 = strong bias, 1 = neutral

    # Metadata
    domain_age_years: Optional[float] = None
    is_academic: bool = False
    is_government: bool = False
    is_news: bool = False

    # Notes
    notes: List[str] = field(default_factory=list)


@dataclass
class ValidationResult:
    """Result of source validation."""
    url: str

    # Credibility
    credibility: SourceCredibility = None

    # Content analysis
    has_citations: bool = False
    has_author: bool = False
    has_date: bool = False
    has_sources: bool = False

    # Quality indicators
    readability_score: float = 0.5
    professionalism_score: float = 0.5

    # Red flags
    red_flags: List[str] = field(default_factory=list)

    # Recommendation
    is_trustworthy: bool = False
    confidence: float = 0.5

    # Metadata
    validated_at: datetime = field(default_factory=datetime.now)


class SourceValidator:
    """
    Source validator for BAEL.

    Validates and assesses source credibility.
    """

    # Known credible domains
    CREDIBLE_DOMAINS = {
        # Academic
        "arxiv.org": (CredibilityLevel.HIGHLY_CREDIBLE, BiasType.SCIENTIFIC),
        "nature.com": (CredibilityLevel.HIGHLY_CREDIBLE, BiasType.SCIENTIFIC),
        "science.org": (CredibilityLevel.HIGHLY_CREDIBLE, BiasType.SCIENTIFIC),
        "ieee.org": (CredibilityLevel.HIGHLY_CREDIBLE, BiasType.SCIENTIFIC),
        "acm.org": (CredibilityLevel.HIGHLY_CREDIBLE, BiasType.SCIENTIFIC),
        "springer.com": (CredibilityLevel.HIGHLY_CREDIBLE, BiasType.SCIENTIFIC),
        "wiley.com": (CredibilityLevel.HIGHLY_CREDIBLE, BiasType.SCIENTIFIC),

        # Educational
        ".edu": (CredibilityLevel.CREDIBLE, BiasType.CENTER),
        "mit.edu": (CredibilityLevel.HIGHLY_CREDIBLE, BiasType.SCIENTIFIC),
        "stanford.edu": (CredibilityLevel.HIGHLY_CREDIBLE, BiasType.SCIENTIFIC),
        "berkeley.edu": (CredibilityLevel.HIGHLY_CREDIBLE, BiasType.SCIENTIFIC),

        # Government
        ".gov": (CredibilityLevel.CREDIBLE, BiasType.CENTER),
        "nih.gov": (CredibilityLevel.HIGHLY_CREDIBLE, BiasType.SCIENTIFIC),
        "cdc.gov": (CredibilityLevel.HIGHLY_CREDIBLE, BiasType.SCIENTIFIC),

        # Tech documentation
        "github.com": (CredibilityLevel.CREDIBLE, BiasType.CENTER),
        "docs.python.org": (CredibilityLevel.HIGHLY_CREDIBLE, BiasType.CENTER),
        "developer.mozilla.org": (CredibilityLevel.HIGHLY_CREDIBLE, BiasType.CENTER),
        "docs.microsoft.com": (CredibilityLevel.CREDIBLE, BiasType.CENTER),

        # News (mainstream)
        "reuters.com": (CredibilityLevel.CREDIBLE, BiasType.CENTER),
        "apnews.com": (CredibilityLevel.CREDIBLE, BiasType.CENTER),
        "bbc.com": (CredibilityLevel.CREDIBLE, BiasType.CENTER),
    }

    # Questionable domain indicators
    QUESTIONABLE_INDICATORS = [
        "fake", "hoax", "conspiracy", "truth", "revealed",
        "shocking", "secret", "exposed", "banned",
    ]

    # Academic indicators
    ACADEMIC_INDICATORS = [
        "doi.org", "pubmed", "scholar", "journal",
        "proceedings", "arxiv", "ssrn", "researchgate",
    ]

    # Promotional indicators
    PROMOTIONAL_INDICATORS = [
        "buy", "shop", "sale", "discount", "offer",
        "free trial", "subscribe", "premium", "pro",
    ]

    def __init__(self):
        # Cache
        self._cache: Dict[str, SourceCredibility] = {}

        # Stats
        self.stats = {
            "sources_validated": 0,
            "credible_sources": 0,
            "questionable_sources": 0,
        }

    def validate(
        self,
        url: str,
        content: Optional[str] = None,
    ) -> ValidationResult:
        """
        Validate a source.

        Args:
            url: Source URL
            content: Optional page content

        Returns:
            Validation result
        """
        result = ValidationResult(url=url)

        # Get domain credibility
        domain = self._extract_domain(url)
        result.credibility = self.assess_domain(domain)

        # Analyze content if provided
        if content:
            result = self._analyze_content(result, content)

        # Determine trustworthiness
        result.is_trustworthy = self._determine_trustworthiness(result)
        result.confidence = self._calculate_confidence(result)

        self.stats["sources_validated"] += 1
        if result.is_trustworthy:
            self.stats["credible_sources"] += 1
        elif result.credibility.credibility_level == CredibilityLevel.QUESTIONABLE:
            self.stats["questionable_sources"] += 1

        return result

    def assess_domain(self, domain: str) -> SourceCredibility:
        """
        Assess domain credibility.

        Args:
            domain: Domain name

        Returns:
            Source credibility assessment
        """
        if domain in self._cache:
            return self._cache[domain]

        credibility = SourceCredibility(domain=domain)

        # Check known domains
        for known_domain, (level, bias) in self.CREDIBLE_DOMAINS.items():
            if domain.endswith(known_domain) or known_domain in domain:
                credibility.credibility_level = level
                credibility.bias_type = bias
                credibility.overall_score = self._level_to_score(level)
                break

        # Check TLD
        if domain.endswith('.edu'):
            credibility.is_academic = True
            credibility.credibility_level = CredibilityLevel.CREDIBLE
            credibility.overall_score = max(credibility.overall_score, 0.7)

        if domain.endswith('.gov'):
            credibility.is_government = True
            credibility.credibility_level = CredibilityLevel.CREDIBLE
            credibility.overall_score = max(credibility.overall_score, 0.7)

        # Check for questionable indicators
        for indicator in self.QUESTIONABLE_INDICATORS:
            if indicator in domain.lower():
                credibility.credibility_level = CredibilityLevel.QUESTIONABLE
                credibility.overall_score = min(credibility.overall_score, 0.3)
                credibility.notes.append(f"Questionable indicator: {indicator}")
                break

        # Check for academic indicators
        for indicator in self.ACADEMIC_INDICATORS:
            if indicator in domain.lower():
                credibility.is_academic = True
                credibility.overall_score = max(credibility.overall_score, 0.7)
                break

        # Cache
        self._cache[domain] = credibility

        return credibility

    def _level_to_score(self, level: CredibilityLevel) -> float:
        """Convert credibility level to score."""
        return {
            CredibilityLevel.HIGHLY_CREDIBLE: 0.95,
            CredibilityLevel.CREDIBLE: 0.75,
            CredibilityLevel.SOMEWHAT_CREDIBLE: 0.55,
            CredibilityLevel.QUESTIONABLE: 0.3,
            CredibilityLevel.UNRELIABLE: 0.1,
            CredibilityLevel.UNKNOWN: 0.5,
        }.get(level, 0.5)

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        match = re.search(r'https?://([^/]+)', url)
        if match:
            domain = match.group(1)
            # Remove www.
            domain = re.sub(r'^www\.', '', domain)
            return domain
        return url

    def _analyze_content(
        self,
        result: ValidationResult,
        content: str,
    ) -> ValidationResult:
        """Analyze content for quality indicators."""
        content_lower = content.lower()

        # Check for citations
        citation_patterns = [
            r'\[\d+\]',  # [1], [2]
            r'\(.*?\d{4}\)',  # (Author, 2023)
            r'doi\.org',
            r'references?:',
        ]
        result.has_citations = any(
            re.search(p, content_lower) for p in citation_patterns
        )

        # Check for author
        author_patterns = [
            r'by\s+[A-Z][a-z]+\s+[A-Z][a-z]+',
            r'author[s]?\s*:',
            r'written\s+by',
        ]
        result.has_author = any(
            re.search(p, content, re.IGNORECASE) for p in author_patterns
        )

        # Check for date
        date_patterns = [
            r'\d{4}[-/]\d{1,2}[-/]\d{1,2}',
            r'(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2},?\s+\d{4}',
            r'published\s*:',
            r'updated\s*:',
        ]
        result.has_date = any(
            re.search(p, content, re.IGNORECASE) for p in date_patterns
        )

        # Check for sources
        result.has_sources = result.has_citations or 'source' in content_lower

        # Calculate readability (simplified)
        words = content.split()
        sentences = re.split(r'[.!?]', content)
        avg_sentence_length = len(words) / max(len(sentences), 1)

        # Shorter sentences = more readable
        result.readability_score = min(1.0, 20 / max(avg_sentence_length, 1))

        # Professionalism
        professionalism = 0.5

        # Positive indicators
        if result.has_author:
            professionalism += 0.1
        if result.has_date:
            professionalism += 0.1
        if result.has_citations:
            professionalism += 0.15
        if result.has_sources:
            professionalism += 0.1

        # Check for red flags
        for indicator in self.PROMOTIONAL_INDICATORS:
            if indicator in content_lower:
                result.red_flags.append(f"Promotional content: {indicator}")
                professionalism -= 0.1

        # Check for clickbait
        clickbait_patterns = [
            r'you won\'?t believe',
            r'shocking',
            r'this one trick',
            r'doctors hate',
            r'what happens next',
        ]
        for pattern in clickbait_patterns:
            if re.search(pattern, content_lower):
                result.red_flags.append("Clickbait language detected")
                professionalism -= 0.15
                break

        # Check for excessive caps
        caps_ratio = sum(1 for c in content if c.isupper()) / max(len(content), 1)
        if caps_ratio > 0.3:
            result.red_flags.append("Excessive capitalization")
            professionalism -= 0.1

        result.professionalism_score = max(0.0, min(1.0, professionalism))

        return result

    def _determine_trustworthiness(self, result: ValidationResult) -> bool:
        """Determine if source is trustworthy."""
        if not result.credibility:
            return False

        # High credibility sources are trusted
        if result.credibility.credibility_level == CredibilityLevel.HIGHLY_CREDIBLE:
            return True

        # Questionable or unreliable sources are not trusted
        if result.credibility.credibility_level in [
            CredibilityLevel.QUESTIONABLE,
            CredibilityLevel.UNRELIABLE,
        ]:
            return False

        # For other sources, check quality indicators
        quality_score = (
            result.credibility.overall_score * 0.4 +
            result.professionalism_score * 0.3 +
            (0.15 if result.has_citations else 0) +
            (0.1 if result.has_author else 0) +
            (0.05 if result.has_date else 0)
        )

        # Penalize for red flags
        quality_score -= len(result.red_flags) * 0.1

        return quality_score >= 0.6

    def _calculate_confidence(self, result: ValidationResult) -> float:
        """Calculate confidence in validation."""
        confidence = 0.5

        # Known domain increases confidence
        if result.credibility:
            if result.credibility.credibility_level != CredibilityLevel.UNKNOWN:
                confidence += 0.2

        # More indicators = higher confidence
        if result.has_author:
            confidence += 0.1
        if result.has_date:
            confidence += 0.1
        if result.has_citations:
            confidence += 0.1

        return min(1.0, confidence)

    def compare_sources(
        self,
        sources: List[str],
    ) -> Dict[str, ValidationResult]:
        """
        Compare multiple sources.

        Args:
            sources: List of URLs

        Returns:
            Validation results by URL
        """
        results = {}

        for url in sources:
            results[url] = self.validate(url)

        return results

    def rank_sources(
        self,
        results: Dict[str, ValidationResult],
    ) -> List[str]:
        """
        Rank sources by credibility.

        Args:
            results: Validation results

        Returns:
            URLs sorted by credibility
        """
        def score(url: str) -> float:
            r = results[url]
            base = r.credibility.overall_score if r.credibility else 0.5
            return base + r.professionalism_score * 0.3 - len(r.red_flags) * 0.1

        return sorted(results.keys(), key=score, reverse=True)

    def get_stats(self) -> Dict[str, Any]:
        """Get validator statistics."""
        return {
            **self.stats,
            "cached_domains": len(self._cache),
        }


def demo():
    """Demonstrate source validator."""
    print("=" * 60)
    print("BAEL Source Validator Demo")
    print("=" * 60)

    validator = SourceValidator()

    # Test URLs
    urls = [
        "https://arxiv.org/abs/1706.03762",
        "https://nature.com/articles/s41586-021-03819-2",
        "https://www.randomnewssite.com/shocking-truth",
        "https://developer.mozilla.org/en-US/docs/Web/JavaScript",
        "https://www.mit.edu/research/ai",
    ]

    print("\nValidating sources...")

    for url in urls:
        result = validator.validate(url)

        print(f"\n  URL: {url}")
        print(f"  Credibility: {result.credibility.credibility_level.value}")
        print(f"  Overall Score: {result.credibility.overall_score:.2f}")
        print(f"  Bias: {result.credibility.bias_type.value}")
        print(f"  Trustworthy: {result.is_trustworthy}")
        print(f"  Confidence: {result.confidence:.0%}")

        if result.red_flags:
            print(f"  Red Flags: {result.red_flags}")

    # Compare and rank
    results = validator.compare_sources(urls)
    ranked = validator.rank_sources(results)

    print("\n\nRanked sources (most credible first):")
    for i, url in enumerate(ranked, 1):
        domain = url.split('/')[2]
        print(f"  {i}. {domain}")

    print(f"\nStats: {validator.get_stats()}")


if __name__ == "__main__":
    demo()

"""
BAEL Paper Analyzer
====================

Academic paper analysis and extraction.
Parses papers, extracts citations, analyzes content.

Features:
- Paper parsing
- Citation extraction
- Section analysis
- Key finding extraction
- Related work identification
"""

import hashlib
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class PaperType(Enum):
    """Types of academic papers."""
    RESEARCH = "research"
    SURVEY = "survey"
    REVIEW = "review"
    TECHNICAL_REPORT = "technical_report"
    PREPRINT = "preprint"
    CONFERENCE = "conference"
    JOURNAL = "journal"
    THESIS = "thesis"


class SectionType(Enum):
    """Types of paper sections."""
    ABSTRACT = "abstract"
    INTRODUCTION = "introduction"
    RELATED_WORK = "related_work"
    METHODOLOGY = "methodology"
    EXPERIMENTS = "experiments"
    RESULTS = "results"
    DISCUSSION = "discussion"
    CONCLUSION = "conclusion"
    REFERENCES = "references"
    APPENDIX = "appendix"
    OTHER = "other"


@dataclass
class Citation:
    """A citation in a paper."""
    id: str

    # Reference info
    authors: List[str] = field(default_factory=list)
    title: str = ""
    year: Optional[int] = None
    venue: str = ""  # Journal/conference name

    # Identifiers
    doi: Optional[str] = None
    arxiv_id: Optional[str] = None
    url: Optional[str] = None

    # Context
    citation_contexts: List[str] = field(default_factory=list)
    citation_count: int = 0


@dataclass
class PaperSection:
    """A section of a paper."""
    section_type: SectionType
    title: str
    content: str

    # Position
    start_position: int = 0
    end_position: int = 0

    # Subsections
    subsections: List["PaperSection"] = field(default_factory=list)


@dataclass
class Paper:
    """An academic paper."""
    id: str
    title: str

    # Authors
    authors: List[str] = field(default_factory=list)
    affiliations: List[str] = field(default_factory=list)

    # Content
    abstract: str = ""
    sections: List[PaperSection] = field(default_factory=list)

    # Metadata
    paper_type: PaperType = PaperType.RESEARCH
    year: Optional[int] = None
    venue: str = ""

    # Identifiers
    doi: Optional[str] = None
    arxiv_id: Optional[str] = None
    url: Optional[str] = None

    # Citations
    citations: List[Citation] = field(default_factory=list)

    # Key findings
    key_findings: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)

    # Metrics
    word_count: int = 0
    citation_count: int = 0

    # Timestamps
    published_at: Optional[datetime] = None
    analyzed_at: datetime = field(default_factory=datetime.now)


class PaperAnalyzer:
    """
    Paper analyzer for BAEL.

    Analyzes academic papers and extracts information.
    """

    # Section title patterns
    SECTION_PATTERNS = {
        SectionType.ABSTRACT: r'abstract',
        SectionType.INTRODUCTION: r'introduction|overview',
        SectionType.RELATED_WORK: r'related\s*work|background|literature',
        SectionType.METHODOLOGY: r'method|approach|framework|model',
        SectionType.EXPERIMENTS: r'experiment|evaluation|study',
        SectionType.RESULTS: r'result|finding',
        SectionType.DISCUSSION: r'discussion|analysis',
        SectionType.CONCLUSION: r'conclusion|summary|future',
        SectionType.REFERENCES: r'reference|bibliography',
        SectionType.APPENDIX: r'appendix|supplementary',
    }

    # Citation patterns
    CITATION_PATTERNS = [
        # [Author, Year]
        r'\[([A-Za-z]+(?:\s+et\s+al\.?)?,?\s*\d{4}[a-z]?)\]',
        # (Author, Year)
        r'\(([A-Za-z]+(?:\s+et\s+al\.?)?,?\s*\d{4}[a-z]?)\)',
        # [1], [2,3], [1-5]
        r'\[(\d+(?:[-,]\d+)*)\]',
    ]

    def __init__(self):
        # Paper cache
        self._cache: Dict[str, Paper] = {}

        # Stats
        self.stats = {
            "papers_analyzed": 0,
            "citations_extracted": 0,
            "sections_parsed": 0,
        }

    def analyze(
        self,
        text: str,
        title: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Paper:
        """
        Analyze a paper from text.

        Args:
            text: Paper text content
            title: Optional paper title
            metadata: Optional metadata

        Returns:
            Analyzed paper
        """
        metadata = metadata or {}

        paper_id = hashlib.md5(text[:1000].encode()).hexdigest()[:12]

        paper = Paper(
            id=paper_id,
            title=title or self._extract_title(text),
        )

        # Extract authors
        paper.authors = metadata.get("authors", []) or self._extract_authors(text)

        # Extract abstract
        paper.abstract = self._extract_abstract(text)

        # Parse sections
        paper.sections = self._parse_sections(text)
        self.stats["sections_parsed"] += len(paper.sections)

        # Extract citations
        paper.citations = self._extract_citations(text)
        self.stats["citations_extracted"] += len(paper.citations)

        # Extract key findings
        paper.key_findings = self._extract_findings(text, paper.sections)

        # Extract keywords
        paper.keywords = metadata.get("keywords", []) or self._extract_keywords(text)

        # Metadata
        paper.year = metadata.get("year")
        paper.venue = metadata.get("venue", "")
        paper.doi = metadata.get("doi")
        paper.arxiv_id = metadata.get("arxiv_id")
        paper.url = metadata.get("url")

        # Metrics
        paper.word_count = len(text.split())
        paper.citation_count = len(paper.citations)

        # Determine paper type
        paper.paper_type = self._classify_paper_type(text, paper.sections)

        # Cache
        self._cache[paper_id] = paper

        self.stats["papers_analyzed"] += 1

        return paper

    def _extract_title(self, text: str) -> str:
        """Extract paper title."""
        lines = text.strip().split('\n')

        for line in lines[:10]:
            line = line.strip()
            # Skip empty lines and short lines
            if len(line) > 10 and not line.lower().startswith(('abstract', 'introduction')):
                # Title is usually first substantial line
                if not re.match(r'^\d+\.', line):  # Not a section number
                    return line[:200]

        return "Untitled Paper"

    def _extract_authors(self, text: str) -> List[str]:
        """Extract author names."""
        authors = []

        # Look for common author patterns
        # Pattern: Name1, Name2, and Name3
        # Pattern: Name1; Name2; Name3

        lines = text.split('\n')[:20]

        for line in lines:
            # Skip if looks like a section
            if re.match(r'^\d+\.|^abstract|^introduction', line.lower()):
                continue

            # Look for multiple names
            if ',' in line or ' and ' in line.lower():
                potential_authors = re.findall(
                    r'([A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',
                    line
                )
                if len(potential_authors) >= 2:
                    authors.extend(potential_authors[:10])
                    break

        return authors

    def _extract_abstract(self, text: str) -> str:
        """Extract paper abstract."""
        # Look for "Abstract" section
        match = re.search(
            r'abstract[:\s]*(.+?)(?=\n\s*(?:1\.|introduction|keywords))',
            text,
            re.IGNORECASE | re.DOTALL
        )

        if match:
            abstract = match.group(1).strip()
            # Clean up
            abstract = re.sub(r'\s+', ' ', abstract)
            return abstract[:2000]

        return ""

    def _parse_sections(self, text: str) -> List[PaperSection]:
        """Parse paper into sections."""
        sections = []

        # Find section headers
        section_pattern = r'(?:^|\n)\s*(\d+(?:\.\d+)*\.?\s+)?([A-Z][A-Za-z\s]+)\s*\n'

        matches = list(re.finditer(section_pattern, text))

        for i, match in enumerate(matches):
            title = match.group(2).strip()
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)

            content = text[start:end].strip()

            # Determine section type
            section_type = self._classify_section(title)

            section = PaperSection(
                section_type=section_type,
                title=title,
                content=content[:5000],  # Limit content size
                start_position=start,
                end_position=end,
            )

            sections.append(section)

        return sections

    def _classify_section(self, title: str) -> SectionType:
        """Classify section by title."""
        title_lower = title.lower()

        for section_type, pattern in self.SECTION_PATTERNS.items():
            if re.search(pattern, title_lower):
                return section_type

        return SectionType.OTHER

    def _extract_citations(self, text: str) -> List[Citation]:
        """Extract citations from text."""
        citations = []
        seen_citations = set()

        for pattern in self.CITATION_PATTERNS:
            matches = re.finditer(pattern, text)

            for match in matches:
                citation_text = match.group(1)

                if citation_text in seen_citations:
                    continue
                seen_citations.add(citation_text)

                # Extract context (surrounding text)
                start = max(0, match.start() - 100)
                end = min(len(text), match.end() + 100)
                context = text[start:end].strip()

                citation_id = hashlib.md5(citation_text.encode()).hexdigest()[:12]

                # Parse citation
                year_match = re.search(r'(\d{4})', citation_text)
                author_match = re.search(r'([A-Za-z]+)', citation_text)

                citation = Citation(
                    id=citation_id,
                    authors=[author_match.group(1)] if author_match else [],
                    year=int(year_match.group(1)) if year_match else None,
                    citation_contexts=[context],
                )

                citations.append(citation)

        return citations

    def _extract_findings(
        self,
        text: str,
        sections: List[PaperSection],
    ) -> List[str]:
        """Extract key findings."""
        findings = []

        # Look in results and conclusion sections
        target_sections = [
            s for s in sections
            if s.section_type in [SectionType.RESULTS, SectionType.CONCLUSION, SectionType.DISCUSSION]
        ]

        # Keywords indicating findings
        finding_patterns = [
            r'we\s+(?:find|show|demonstrate|observe|conclude)\s+that\s+([^.]+)',
            r'(?:our\s+)?results\s+(?:show|indicate|suggest)\s+that\s+([^.]+)',
            r'(?:the\s+)?main\s+(?:finding|contribution)\s+is\s+([^.]+)',
            r'we\s+achieve\s+([^.]+)',
            r'(?:this|our)\s+approach\s+(?:achieves|outperforms)\s+([^.]+)',
        ]

        content = text
        if target_sections:
            content = " ".join(s.content for s in target_sections)

        for pattern in finding_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches[:3]:  # Limit per pattern
                finding = match.strip()
                if len(finding) > 20:
                    findings.append(finding[:500])

        return findings[:10]  # Limit total findings

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract paper keywords."""
        keywords = []

        # Look for explicit keywords section
        match = re.search(
            r'keywords?[:\s]*([^\n]+)',
            text,
            re.IGNORECASE
        )

        if match:
            keyword_text = match.group(1)
            # Split by common separators
            keywords = re.split(r'[,;·•]', keyword_text)
            keywords = [k.strip() for k in keywords if k.strip()]

        return keywords[:10]

    def _classify_paper_type(
        self,
        text: str,
        sections: List[PaperSection],
    ) -> PaperType:
        """Classify paper type."""
        text_lower = text.lower()

        # Check for survey/review indicators
        if any(word in text_lower for word in ['survey', 'comprehensive review', 'literature review']):
            return PaperType.SURVEY

        # Check for thesis indicators
        if 'thesis' in text_lower or 'dissertation' in text_lower:
            return PaperType.THESIS

        # Check for preprint
        if 'arxiv' in text_lower or 'preprint' in text_lower:
            return PaperType.PREPRINT

        # Check for technical report
        if 'technical report' in text_lower:
            return PaperType.TECHNICAL_REPORT

        # Default to research paper
        return PaperType.RESEARCH

    def get_related_work(self, paper: Paper) -> PaperSection:
        """Get related work section."""
        for section in paper.sections:
            if section.section_type == SectionType.RELATED_WORK:
                return section

        return PaperSection(
            section_type=SectionType.RELATED_WORK,
            title="Related Work",
            content="",
        )

    def get_methodology(self, paper: Paper) -> PaperSection:
        """Get methodology section."""
        for section in paper.sections:
            if section.section_type == SectionType.METHODOLOGY:
                return section

        return PaperSection(
            section_type=SectionType.METHODOLOGY,
            title="Methodology",
            content="",
        )

    def compare_papers(
        self,
        paper1: Paper,
        paper2: Paper,
    ) -> Dict[str, Any]:
        """Compare two papers."""
        # Find shared citations
        citations1 = {c.id for c in paper1.citations}
        citations2 = {c.id for c in paper2.citations}
        shared_citations = citations1 & citations2

        # Find shared keywords
        keywords1 = set(paper1.keywords)
        keywords2 = set(paper2.keywords)
        shared_keywords = keywords1 & keywords2

        return {
            "shared_citations": len(shared_citations),
            "shared_keywords": list(shared_keywords),
            "citation_overlap": len(shared_citations) / max(len(citations1), len(citations2), 1),
            "keyword_overlap": len(shared_keywords) / max(len(keywords1), len(keywords2), 1),
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get analyzer statistics."""
        return {
            **self.stats,
            "cached_papers": len(self._cache),
        }


def demo():
    """Demonstrate paper analyzer."""
    print("=" * 60)
    print("BAEL Paper Analyzer Demo")
    print("=" * 60)

    analyzer = PaperAnalyzer()

    # Sample paper text
    paper_text = """
    Attention Is All You Need

    Ashish Vaswani, Noam Shazeer, Niki Parmar
    Google Brain

    Abstract
    The dominant sequence transduction models are based on complex recurrent or
    convolutional neural networks that include an encoder and a decoder. The best
    performing models also connect the encoder and decoder through an attention
    mechanism. We propose a new simple network architecture, the Transformer,
    based solely on attention mechanisms, dispensing with recurrence and convolutions
    entirely.

    1. Introduction

    Recurrent neural networks, long short-term memory [13] and gated recurrent [7]
    neural networks in particular, have been firmly established as state of the art
    approaches in sequence modeling. Numerous efforts have since continued to push
    the boundaries of recurrent language models [22].

    2. Related Work

    The goal of reducing sequential computation also forms the foundation of the
    Extended Neural GPU [16], ByteNet [18] and ConvS2S [9], all of which use
    convolutional neural networks as basic building block.

    3. Model Architecture

    The Transformer follows an encoder-decoder structure using stacked self-attention
    and point-wise, fully connected layers for both the encoder and decoder.

    4. Results

    We find that the Transformer outperforms previous state-of-the-art models on
    machine translation tasks. Our model achieves 28.4 BLEU on the WMT 2014
    English-to-German translation task.

    5. Conclusion

    We demonstrate that the Transformer achieves state-of-the-art results on
    machine translation benchmarks. We are excited about the future of attention-based
    models and plan to apply them to other tasks.

    Keywords: transformer, attention, neural networks, machine translation

    References
    [7] Cho et al. Learning phrase representations. 2014.
    [9] Gehring et al. Convolutional sequence to sequence learning. 2017.
    [13] Hochreiter and Schmidhuber. Long short-term memory. 1997.
    """

    print("\nAnalyzing paper...")
    paper = analyzer.analyze(
        paper_text,
        metadata={"year": 2017, "venue": "NeurIPS"}
    )

    print(f"\nTitle: {paper.title}")
    print(f"Authors: {paper.authors}")
    print(f"Type: {paper.paper_type.value}")
    print(f"Year: {paper.year}")
    print(f"Venue: {paper.venue}")

    print(f"\nAbstract ({len(paper.abstract)} chars):")
    print(f"  {paper.abstract[:150]}...")

    print(f"\nSections ({len(paper.sections)}):")
    for section in paper.sections:
        print(f"  - {section.title} ({section.section_type.value})")

    print(f"\nCitations found: {len(paper.citations)}")
    for cit in paper.citations[:3]:
        print(f"  - {cit.authors[0] if cit.authors else 'Unknown'} ({cit.year})")

    print(f"\nKey findings: {len(paper.key_findings)}")
    for finding in paper.key_findings[:2]:
        print(f"  - {finding[:80]}...")

    print(f"\nKeywords: {paper.keywords}")
    print(f"Word count: {paper.word_count}")

    print(f"\nStats: {analyzer.get_stats()}")


if __name__ == "__main__":
    demo()

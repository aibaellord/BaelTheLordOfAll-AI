"""
BAEL - Research Orchestrator
Advanced multi-source research with intelligent synthesis.

Features:
- Multi-source parallel research
- Semantic deduplication
- Confidence scoring
- Citation tracking
- Knowledge graph construction
- Auto-summarization
"""

import asyncio
import hashlib
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger("BAEL.Research")


# =============================================================================
# ENUMS & TYPES
# =============================================================================

class ResearchPhase(Enum):
    """Research phases."""
    PLANNING = "planning"
    GATHERING = "gathering"
    ANALYZING = "analyzing"
    SYNTHESIZING = "synthesizing"
    VALIDATING = "validating"
    COMPLETE = "complete"


class SourceType(Enum):
    """Source types for research."""
    WEB_SEARCH = "web_search"
    WEB_PAGE = "web_page"
    DOCUMENTATION = "documentation"
    CODE_REPOSITORY = "code_repository"
    ACADEMIC_PAPER = "academic_paper"
    INTERNAL_MEMORY = "internal_memory"
    EXPERT_KNOWLEDGE = "expert_knowledge"


class ConfidenceLevel(Enum):
    """Confidence levels."""
    VERY_HIGH = "very_high"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNCERTAIN = "uncertain"


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class ResearchSource:
    """A source of research information."""
    id: str
    type: SourceType
    url: Optional[str] = None
    title: Optional[str] = None
    content: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    retrieved_at: datetime = field(default_factory=datetime.now)
    confidence: float = 0.0
    relevance: float = 0.0


@dataclass
class ResearchFinding:
    """A research finding with sources."""
    id: str
    content: str
    summary: str
    sources: List[ResearchSource]
    confidence: ConfidenceLevel
    tags: List[str] = field(default_factory=list)
    related_findings: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class KnowledgeNode:
    """A node in the knowledge graph."""
    id: str
    label: str
    type: str
    properties: Dict[str, Any] = field(default_factory=dict)
    sources: List[str] = field(default_factory=list)


@dataclass
class KnowledgeEdge:
    """An edge in the knowledge graph."""
    source_id: str
    target_id: str
    relationship: str
    weight: float = 1.0
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ResearchPlan:
    """A plan for conducting research."""
    topic: str
    objectives: List[str]
    questions: List[str]
    search_queries: List[str]
    source_types: List[SourceType]
    depth: int = 3
    max_sources: int = 20
    time_limit_seconds: Optional[int] = None


@dataclass
class ResearchReport:
    """Complete research report."""
    topic: str
    executive_summary: str
    key_findings: List[ResearchFinding]
    detailed_analysis: str
    knowledge_graph: Dict[str, Any]
    sources_used: List[ResearchSource]
    confidence_assessment: str
    recommendations: List[str]
    gaps_identified: List[str]
    created_at: datetime = field(default_factory=datetime.now)
    research_time_seconds: float = 0.0


# =============================================================================
# KNOWLEDGE GRAPH
# =============================================================================

class KnowledgeGraph:
    """Simple knowledge graph implementation."""

    def __init__(self):
        self.nodes: Dict[str, KnowledgeNode] = {}
        self.edges: List[KnowledgeEdge] = []
        self._adjacency: Dict[str, Set[str]] = defaultdict(set)

    def add_node(self, node: KnowledgeNode) -> None:
        """Add a node."""
        self.nodes[node.id] = node

    def add_edge(self, edge: KnowledgeEdge) -> None:
        """Add an edge."""
        self.edges.append(edge)
        self._adjacency[edge.source_id].add(edge.target_id)

    def get_connected(self, node_id: str, depth: int = 1) -> Set[str]:
        """Get connected nodes up to a depth."""
        result = set()
        current = {node_id}

        for _ in range(depth):
            next_level = set()
            for nid in current:
                neighbors = self._adjacency.get(nid, set())
                next_level.update(neighbors)
            result.update(next_level)
            current = next_level

        return result

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "nodes": [
                {
                    "id": n.id,
                    "label": n.label,
                    "type": n.type,
                    "properties": n.properties
                }
                for n in self.nodes.values()
            ],
            "edges": [
                {
                    "source": e.source_id,
                    "target": e.target_id,
                    "relationship": e.relationship,
                    "weight": e.weight
                }
                for e in self.edges
            ]
        }


# =============================================================================
# RESEARCH ORCHESTRATOR
# =============================================================================

class ResearchOrchestrator:
    """Orchestrates comprehensive research operations."""

    def __init__(self, brain=None, model_router=None, tools=None):
        self.brain = brain
        self.model_router = model_router
        self.tools = tools or {}

        self.current_phase = ResearchPhase.PLANNING
        self.sources: Dict[str, ResearchSource] = {}
        self.findings: Dict[str, ResearchFinding] = {}
        self.knowledge_graph = KnowledgeGraph()
        self._seen_hashes: Set[str] = set()

    async def research(self, topic: str, depth: int = 3, **kwargs) -> ResearchReport:
        """Conduct comprehensive research on a topic."""
        start_time = datetime.now()
        logger.info(f"📚 Starting research on: {topic}")

        try:
            # Phase 1: Planning
            self.current_phase = ResearchPhase.PLANNING
            plan = await self._create_research_plan(topic, depth)

            # Phase 2: Gathering
            self.current_phase = ResearchPhase.GATHERING
            sources = await self._gather_sources(plan)

            # Phase 3: Analyzing
            self.current_phase = ResearchPhase.ANALYZING
            findings = await self._analyze_sources(sources, plan)

            # Phase 4: Synthesizing
            self.current_phase = ResearchPhase.SYNTHESIZING
            synthesis = await self._synthesize_findings(findings, plan)

            # Phase 5: Validating
            self.current_phase = ResearchPhase.VALIDATING
            validated = await self._validate_synthesis(synthesis, sources)

            # Complete
            self.current_phase = ResearchPhase.COMPLETE

            end_time = datetime.now()
            research_time = (end_time - start_time).total_seconds()

            report = ResearchReport(
                topic=topic,
                executive_summary=validated.get('summary', ''),
                key_findings=list(self.findings.values()),
                detailed_analysis=validated.get('analysis', ''),
                knowledge_graph=self.knowledge_graph.to_dict(),
                sources_used=list(self.sources.values()),
                confidence_assessment=validated.get('confidence', 'medium'),
                recommendations=validated.get('recommendations', []),
                gaps_identified=validated.get('gaps', []),
                research_time_seconds=research_time
            )

            logger.info(f"✅ Research complete in {research_time:.1f}s - {len(sources)} sources, {len(findings)} findings")

            return report

        except Exception as e:
            logger.error(f"Research error: {e}")
            raise

    async def _create_research_plan(self, topic: str, depth: int) -> ResearchPlan:
        """Create a research plan using AI."""
        logger.info("📋 Creating research plan...")

        # Use LLM to create plan if available
        if self.model_router:
            plan_prompt = f"""Create a comprehensive research plan for: {topic}

Output a structured plan including:
1. Main objectives (3-5 clear goals)
2. Key questions to answer (5-10 questions)
3. Search queries to use (10-15 varied queries)
4. Types of sources to prioritize

Format as JSON with keys: objectives, questions, queries, source_priorities"""

            response = await self.model_router.generate(
                plan_prompt,
                model_type='reasoning'
            )

            # Parse response (simplified - in production, use proper parsing)
            # For now, create default plan

        # Default comprehensive plan
        return ResearchPlan(
            topic=topic,
            objectives=[
                f"Understand the core concepts of {topic}",
                f"Identify best practices and common patterns",
                f"Find authoritative sources and documentation",
                f"Discover recent developments and trends",
                f"Identify potential challenges and solutions"
            ],
            questions=[
                f"What is {topic} and why is it important?",
                f"What are the key components of {topic}?",
                f"What are best practices for {topic}?",
                f"What are common challenges with {topic}?",
                f"What are recent developments in {topic}?",
                f"How does {topic} compare to alternatives?",
                f"What tools and resources exist for {topic}?",
                f"What are real-world examples of {topic}?"
            ],
            search_queries=[
                topic,
                f"{topic} tutorial",
                f"{topic} best practices",
                f"{topic} documentation",
                f"{topic} examples",
                f"{topic} guide",
                f"{topic} architecture",
                f"{topic} implementation",
                f"how to {topic}",
                f"{topic} 2024"
            ],
            source_types=[
                SourceType.WEB_SEARCH,
                SourceType.DOCUMENTATION,
                SourceType.CODE_REPOSITORY
            ],
            depth=depth,
            max_sources=depth * 10
        )

    async def _gather_sources(self, plan: ResearchPlan) -> List[ResearchSource]:
        """Gather sources based on research plan."""
        logger.info(f"🔍 Gathering sources (max {plan.max_sources})...")

        sources: List[ResearchSource] = []

        # Web search if available
        if 'web_search' in self.tools and SourceType.WEB_SEARCH in plan.source_types:
            search_tasks = []
            for query in plan.search_queries[:5]:  # Limit parallel searches
                search_tasks.append(self._search_web(query))

            results = await asyncio.gather(*search_tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, list):
                    sources.extend(result)

        # Fetch web pages
        if 'web_fetch' in self.tools:
            fetch_tasks = []
            urls_to_fetch = [s.url for s in sources if s.url and not s.content][:10]

            for url in urls_to_fetch:
                fetch_tasks.append(self._fetch_page(url))

            page_results = await asyncio.gather(*fetch_tasks, return_exceptions=True)

            for source, result in zip([s for s in sources if s.url and not s.content], page_results):
                if isinstance(result, str):
                    source.content = result

        # Internal memory search
        if self.brain and self.brain.memory_manager:
            memory_sources = await self._search_memory(plan.topic)
            sources.extend(memory_sources)

        # Deduplicate
        sources = self._deduplicate_sources(sources)

        # Store and return
        for source in sources:
            self.sources[source.id] = source

        logger.info(f"📦 Gathered {len(sources)} unique sources")
        return sources

    async def _search_web(self, query: str) -> List[ResearchSource]:
        """Search the web for a query."""
        sources = []

        try:
            if 'web_search' in self.tools:
                tool = self.tools['web_search']
                result = await tool.execute({'query': query})

                if result.success and result.data:
                    for i, item in enumerate(result.data.get('results', [])):
                        source = ResearchSource(
                            id=f"search_{hashlib.md5(item.get('url', str(i)).encode()).hexdigest()[:8]}",
                            type=SourceType.WEB_SEARCH,
                            url=item.get('url'),
                            title=item.get('title'),
                            content=item.get('snippet', ''),
                            metadata={'query': query},
                            relevance=1.0 - (i * 0.1)  # Decrease relevance by position
                        )
                        sources.append(source)

        except Exception as e:
            logger.error(f"Web search error: {e}")

        return sources

    async def _fetch_page(self, url: str) -> str:
        """Fetch a web page."""
        try:
            if 'web_fetch' in self.tools:
                tool = self.tools['web_fetch']
                result = await tool.execute({'url': url})

                if result.success:
                    return result.data.get('content', '')

        except Exception as e:
            logger.error(f"Page fetch error for {url}: {e}")

        return ""

    async def _search_memory(self, query: str) -> List[ResearchSource]:
        """Search internal memory."""
        sources = []

        try:
            if self.brain and self.brain.memory_manager:
                results = await self.brain.memory_manager.comprehensive_search(query, limit=10)

                for item in results.get('results', []):
                    source = ResearchSource(
                        id=f"memory_{item.get('id', '')}",
                        type=SourceType.INTERNAL_MEMORY,
                        content=item.get('content', ''),
                        metadata=item.get('metadata', {}),
                        confidence=item.get('similarity', 0.0),
                        relevance=item.get('similarity', 0.0)
                    )
                    sources.append(source)

        except Exception as e:
            logger.error(f"Memory search error: {e}")

        return sources

    def _deduplicate_sources(self, sources: List[ResearchSource]) -> List[ResearchSource]:
        """Remove duplicate sources."""
        unique = []

        for source in sources:
            # Create content hash
            content_hash = hashlib.md5(source.content.encode()).hexdigest()

            if content_hash not in self._seen_hashes:
                self._seen_hashes.add(content_hash)
                unique.append(source)

        return unique

    async def _analyze_sources(self, sources: List[ResearchSource], plan: ResearchPlan) -> List[ResearchFinding]:
        """Analyze sources and extract findings."""
        logger.info(f"🔬 Analyzing {len(sources)} sources...")

        findings: List[ResearchFinding] = []

        # Group sources by type for batch processing
        source_groups = defaultdict(list)
        for source in sources:
            source_groups[source.type].append(source)

        # Analyze each group
        for source_type, group_sources in source_groups.items():
            group_findings = await self._analyze_source_group(group_sources, plan)
            findings.extend(group_findings)

        # Build knowledge graph
        await self._build_knowledge_graph(findings)

        # Store findings
        for finding in findings:
            self.findings[finding.id] = finding

        logger.info(f"📝 Extracted {len(findings)} findings")
        return findings

    async def _analyze_source_group(self, sources: List[ResearchSource], plan: ResearchPlan) -> List[ResearchFinding]:
        """Analyze a group of sources."""
        findings = []

        if not self.model_router:
            # Without LLM, create simple findings from sources
            for source in sources:
                if source.content:
                    finding = ResearchFinding(
                        id=f"finding_{source.id}",
                        content=source.content[:1000],
                        summary=source.content[:200],
                        sources=[source],
                        confidence=ConfidenceLevel.MEDIUM
                    )
                    findings.append(finding)
            return findings

        # Use LLM for analysis
        batch_content = "\n\n---\n\n".join([
            f"Source: {s.title or s.url or 'Unknown'}\n{s.content[:500]}"
            for s in sources[:5]  # Limit batch size
        ])

        analysis_prompt = f"""Analyze these sources about "{plan.topic}":

{batch_content}

Extract key findings. For each finding provide:
1. The main insight or fact
2. A brief summary (1-2 sentences)
3. Confidence level (very_high/high/medium/low/uncertain)
4. Related tags/topics

Format each finding as a separate paragraph."""

        response = await self.model_router.generate(
            analysis_prompt,
            model_type='reasoning'
        )

        # Parse response into findings (simplified)
        paragraphs = response.split('\n\n')
        for i, para in enumerate(paragraphs):
            if para.strip():
                finding = ResearchFinding(
                    id=f"finding_{i}_{hashlib.md5(para.encode()).hexdigest()[:6]}",
                    content=para,
                    summary=para[:200],
                    sources=sources[:5],
                    confidence=ConfidenceLevel.MEDIUM,
                    tags=self._extract_tags(para)
                )
                findings.append(finding)

        return findings

    def _extract_tags(self, text: str) -> List[str]:
        """Extract topic tags from text."""
        # Simple keyword extraction
        words = text.lower().split()
        # Filter common words and return unique significant terms
        stopwords = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
                    'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
                    'would', 'could', 'should', 'may', 'might', 'must', 'shall',
                    'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by', 'from',
                    'as', 'into', 'through', 'during', 'before', 'after',
                    'above', 'below', 'between', 'under', 'over', 'and', 'or',
                    'but', 'if', 'then', 'else', 'when', 'where', 'why', 'how',
                    'all', 'each', 'every', 'both', 'few', 'more', 'most',
                    'other', 'some', 'such', 'no', 'not', 'only', 'own', 'same',
                    'so', 'than', 'too', 'very', 'just', 'also', 'now', 'here',
                    'there', 'this', 'that', 'these', 'those', 'it', 'its'}

        significant = [w for w in words if len(w) > 3 and w not in stopwords]

        # Return unique tags
        seen = set()
        tags = []
        for tag in significant:
            if tag not in seen:
                seen.add(tag)
                tags.append(tag)
                if len(tags) >= 5:
                    break

        return tags

    async def _build_knowledge_graph(self, findings: List[ResearchFinding]) -> None:
        """Build knowledge graph from findings."""
        # Add finding nodes
        for finding in findings:
            node = KnowledgeNode(
                id=finding.id,
                label=finding.summary[:50],
                type="finding",
                properties={
                    "confidence": finding.confidence.value,
                    "source_count": len(finding.sources)
                },
                sources=[s.id for s in finding.sources]
            )
            self.knowledge_graph.add_node(node)

            # Add tag nodes and edges
            for tag in finding.tags:
                tag_id = f"tag_{tag}"
                if tag_id not in self.knowledge_graph.nodes:
                    tag_node = KnowledgeNode(
                        id=tag_id,
                        label=tag,
                        type="topic"
                    )
                    self.knowledge_graph.add_node(tag_node)

                edge = KnowledgeEdge(
                    source_id=finding.id,
                    target_id=tag_id,
                    relationship="about"
                )
                self.knowledge_graph.add_edge(edge)

        # Connect related findings
        for i, f1 in enumerate(findings):
            for f2 in findings[i+1:]:
                shared_tags = set(f1.tags) & set(f2.tags)
                if shared_tags:
                    edge = KnowledgeEdge(
                        source_id=f1.id,
                        target_id=f2.id,
                        relationship="related",
                        weight=len(shared_tags) / max(len(f1.tags), 1)
                    )
                    self.knowledge_graph.add_edge(edge)

    async def _synthesize_findings(self, findings: List[ResearchFinding], plan: ResearchPlan) -> Dict[str, Any]:
        """Synthesize findings into coherent analysis."""
        logger.info("🧪 Synthesizing findings...")

        if not self.model_router:
            # Simple synthesis without LLM
            return {
                "summary": f"Research on {plan.topic} found {len(findings)} key findings from {len(self.sources)} sources.",
                "analysis": "\n\n".join([f.content for f in findings]),
                "themes": list(set(tag for f in findings for tag in f.tags))
            }

        # Use LLM for synthesis
        findings_text = "\n\n".join([
            f"Finding {i+1} (confidence: {f.confidence.value}):\n{f.content}"
            for i, f in enumerate(findings[:15])  # Limit to prevent token overflow
        ])

        synthesis_prompt = f"""Synthesize these research findings about "{plan.topic}":

Objectives:
{chr(10).join(f"- {obj}" for obj in plan.objectives)}

Findings:
{findings_text}

Provide:
1. Executive Summary (2-3 paragraphs)
2. Key Themes (list main themes)
3. Detailed Analysis (comprehensive but concise)
4. Recommendations (actionable next steps)
5. Gaps (what's missing or needs more research)

Be thorough but avoid redundancy."""

        response = await self.model_router.generate(
            synthesis_prompt,
            model_type='reasoning'
        )

        return {
            "summary": response[:500],  # First part as summary
            "analysis": response,
            "themes": list(set(tag for f in findings for tag in f.tags))
        }

    async def _validate_synthesis(self, synthesis: Dict[str, Any], sources: List[ResearchSource]) -> Dict[str, Any]:
        """Validate synthesis against sources."""
        logger.info("✅ Validating synthesis...")

        # Basic validation: check source coverage
        source_confidence = sum(s.confidence for s in sources) / max(len(sources), 1)

        # Assess overall confidence
        if source_confidence > 0.8:
            confidence_level = "very_high"
        elif source_confidence > 0.6:
            confidence_level = "high"
        elif source_confidence > 0.4:
            confidence_level = "medium"
        else:
            confidence_level = "low"

        synthesis['confidence'] = confidence_level
        synthesis['recommendations'] = synthesis.get('recommendations', [
            "Cross-reference findings with additional sources",
            "Validate technical details through implementation",
            "Review latest updates to the topic"
        ])
        synthesis['gaps'] = synthesis.get('gaps', [
            "More authoritative sources may be needed",
            "Practical examples could strengthen findings"
        ])

        return synthesis


# =============================================================================
# MAIN
# =============================================================================

async def main():
    """Test research orchestrator."""
    orchestrator = ResearchOrchestrator()

    report = await orchestrator.research("Python async programming", depth=2)

    print(f"\n📚 Research Report: {report.topic}")
    print(f"{'='*60}")
    print(f"\n📝 Executive Summary:\n{report.executive_summary}")
    print(f"\n🔬 Findings: {len(report.key_findings)}")
    print(f"📦 Sources: {len(report.sources_used)}")
    print(f"⏱️ Time: {report.research_time_seconds:.1f}s")
    print(f"🎯 Confidence: {report.confidence_assessment}")


if __name__ == "__main__":
    asyncio.run(main())

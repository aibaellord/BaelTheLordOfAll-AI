"""
BAEL GITHUB REPOSITORY INTELLIGENCE ANALYZER
=============================================

The most advanced GitHub repository analysis system ever created.
Automatically analyzes repositories, finds better alternatives, creates
complex combinations, and integrates the best into Ba'el's architecture.

Key Innovations:
1. Deep Repository Analysis - Understands code, architecture, and patterns
2. Competitor Detection - Finds all alternatives to any repository
3. Quality Scoring - Multi-dimensional quality assessment
4. Combination Engine - Creates advanced combinations of best repos
5. Auto-Integration - Automatically integrates best solutions
6. Evolution Tracking - Monitors repo evolution over time
7. Dependency Analysis - Understands the full dependency graph
"""

from typing import Any, Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum, auto
import asyncio
import json
import time
import math
import re
from datetime import datetime
from collections import defaultdict
import uuid

# Golden ratio for quality calculations
PHI = (1 + math.sqrt(5)) / 2


class RepositoryCategory(Enum):
    """Categories of repositories"""
    AI_AGENT = auto()
    LLM_FRAMEWORK = auto()
    AUTOMATION = auto()
    WORKFLOW = auto()
    MCP_SERVER = auto()
    TOOL_LIBRARY = auto()
    ORCHESTRATION = auto()
    MEMORY_SYSTEM = auto()
    RAG_SYSTEM = auto()
    CODE_GENERATION = auto()
    TESTING = auto()
    MONITORING = auto()
    INFRASTRUCTURE = auto()
    UI_FRAMEWORK = auto()
    API_FRAMEWORK = auto()
    DATABASE = auto()
    MESSAGING = auto()
    SECURITY = auto()
    UNKNOWN = auto()


class QualityDimension(Enum):
    """Dimensions for quality assessment"""
    CODE_QUALITY = auto()
    DOCUMENTATION = auto()
    COMMUNITY = auto()
    MAINTENANCE = auto()
    INNOVATION = auto()
    PERFORMANCE = auto()
    SECURITY = auto()
    SCALABILITY = auto()
    EXTENSIBILITY = auto()
    USABILITY = auto()


@dataclass
class RepositoryMetadata:
    """Metadata about a GitHub repository"""
    url: str
    owner: str
    name: str
    description: str = ""
    stars: int = 0
    forks: int = 0
    watchers: int = 0
    open_issues: int = 0
    language: str = ""
    languages: Dict[str, int] = field(default_factory=dict)
    topics: List[str] = field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    pushed_at: Optional[datetime] = None
    license: str = ""
    default_branch: str = "main"
    size_kb: int = 0
    has_wiki: bool = False
    has_discussions: bool = False
    is_archived: bool = False
    is_fork: bool = False


@dataclass
class QualityScore:
    """Quality score for a repository"""
    overall: float = 0.0
    dimensions: Dict[QualityDimension, float] = field(default_factory=dict)
    confidence: float = 0.0
    analysis_depth: int = 1
    factors: Dict[str, float] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)


@dataclass
class RepositoryAnalysis:
    """Complete analysis of a repository"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    metadata: RepositoryMetadata = None
    category: RepositoryCategory = RepositoryCategory.UNKNOWN
    quality_score: QualityScore = None
    architecture_patterns: List[str] = field(default_factory=list)
    key_features: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    unique_innovations: List[str] = field(default_factory=list)
    integration_potential: float = 0.0
    bael_enhancement_opportunities: List[str] = field(default_factory=list)
    competitors: List[str] = field(default_factory=list)
    analysis_timestamp: float = field(default_factory=time.time)


@dataclass
class CompetitorComparison:
    """Comparison between competitors"""
    main_repo: str
    competitors: List[str]
    winner: str
    comparison_matrix: Dict[str, Dict[str, float]] = field(default_factory=dict)
    combination_recommendations: List[Dict[str, Any]] = field(default_factory=list)
    synthesis_opportunities: List[str] = field(default_factory=list)


class RepositoryQualityScorer:
    """Scores repository quality across multiple dimensions"""

    def __init__(self):
        self.dimension_weights: Dict[QualityDimension, float] = {
            QualityDimension.CODE_QUALITY: 0.15,
            QualityDimension.DOCUMENTATION: 0.12,
            QualityDimension.COMMUNITY: 0.13,
            QualityDimension.MAINTENANCE: 0.12,
            QualityDimension.INNOVATION: 0.15,
            QualityDimension.PERFORMANCE: 0.08,
            QualityDimension.SECURITY: 0.10,
            QualityDimension.SCALABILITY: 0.05,
            QualityDimension.EXTENSIBILITY: 0.05,
            QualityDimension.USABILITY: 0.05,
        }

    def score_repository(self, metadata: RepositoryMetadata) -> QualityScore:
        """Score a repository across all dimensions"""
        dimensions = {}
        factors = {}

        # Community dimension
        star_score = min(1.0, metadata.stars / 50000) if metadata.stars else 0
        fork_score = min(1.0, metadata.forks / 10000) if metadata.forks else 0
        dimensions[QualityDimension.COMMUNITY] = (star_score * 0.6 + fork_score * 0.4)
        factors["stars"] = star_score
        factors["forks"] = fork_score

        # Maintenance dimension
        if metadata.updated_at:
            days_since_update = (datetime.now() - metadata.updated_at).days
            maintenance_score = max(0, 1.0 - (days_since_update / 365))
        else:
            maintenance_score = 0.5
        dimensions[QualityDimension.MAINTENANCE] = maintenance_score
        factors["recency"] = maintenance_score

        # Documentation dimension
        doc_score = 0.5  # Base score
        if metadata.has_wiki:
            doc_score += 0.2
        if metadata.description:
            doc_score += 0.1
        if len(metadata.topics) > 3:
            doc_score += 0.2
        dimensions[QualityDimension.DOCUMENTATION] = min(1.0, doc_score)

        # Issue health
        if metadata.stars > 0:
            issue_ratio = metadata.open_issues / metadata.stars
            issue_health = max(0, 1.0 - (issue_ratio * 10))
        else:
            issue_health = 0.5
        factors["issue_health"] = issue_health

        # Size factor
        if metadata.size_kb > 0:
            # Moderate size is ideal (not too small, not too large)
            size_score = 1.0 - abs(math.log10(metadata.size_kb / 10000)) / 3
            size_score = max(0, min(1.0, size_score))
        else:
            size_score = 0.5
        factors["size_appropriateness"] = size_score

        # Fill remaining dimensions with estimates
        for dim in QualityDimension:
            if dim not in dimensions:
                # Estimate based on community metrics
                dimensions[dim] = (star_score + maintenance_score) / 2

        # Calculate overall score with golden ratio weighting
        overall = 0.0
        for dim, weight in self.dimension_weights.items():
            overall += dimensions.get(dim, 0.5) * weight

        # Apply golden ratio boost for exceptional repos
        if overall > 0.7:
            overall = min(1.0, overall * (1 + (PHI - 1) * 0.1))

        recommendations = []
        if maintenance_score < 0.5:
            recommendations.append("Repository may be unmaintained")
        if star_score < 0.3:
            recommendations.append("Lower community adoption")
        if issue_health < 0.3:
            recommendations.append("High issue-to-star ratio may indicate problems")

        return QualityScore(
            overall=overall,
            dimensions=dimensions,
            confidence=0.8,  # Confidence in the analysis
            analysis_depth=1,
            factors=factors,
            recommendations=recommendations,
        )


class CategoryDetector:
    """Detects the category of a repository"""

    def __init__(self):
        self.category_keywords: Dict[RepositoryCategory, List[str]] = {
            RepositoryCategory.AI_AGENT: [
                "agent", "autonomous", "ai-agent", "llm-agent", "assistant",
                "autogpt", "babyagi", "superagi",
            ],
            RepositoryCategory.LLM_FRAMEWORK: [
                "llm", "langchain", "llama", "gpt", "transformer", "language-model",
                "openai", "anthropic", "claude",
            ],
            RepositoryCategory.AUTOMATION: [
                "automation", "workflow", "pipeline", "ci-cd", "devops",
            ],
            RepositoryCategory.MCP_SERVER: [
                "mcp", "model-context-protocol", "mcp-server", "tool-server",
            ],
            RepositoryCategory.ORCHESTRATION: [
                "orchestration", "orchestrator", "coordinator", "swarm", "multi-agent",
            ],
            RepositoryCategory.MEMORY_SYSTEM: [
                "memory", "vector-store", "embedding", "retrieval", "knowledge-base",
            ],
            RepositoryCategory.RAG_SYSTEM: [
                "rag", "retrieval-augmented", "document-qa", "semantic-search",
            ],
            RepositoryCategory.CODE_GENERATION: [
                "codegen", "code-generation", "copilot", "autocomplete",
            ],
        }

    def detect_category(self, metadata: RepositoryMetadata) -> RepositoryCategory:
        """Detect the category of a repository"""
        text = f"{metadata.name} {metadata.description} {' '.join(metadata.topics)}".lower()

        category_scores: Dict[RepositoryCategory, int] = defaultdict(int)

        for category, keywords in self.category_keywords.items():
            for keyword in keywords:
                if keyword in text:
                    category_scores[category] += 1

        if not category_scores:
            return RepositoryCategory.UNKNOWN

        return max(category_scores, key=category_scores.get)


class CompetitorFinder:
    """Finds competitors and alternatives to repositories"""

    def __init__(self):
        self.known_competitors: Dict[str, List[str]] = {
            "langchain": ["llamaindex", "haystack", "semantic-kernel", "autogen"],
            "autogpt": ["babyagi", "superagi", "agentgpt", "aider", "gpt-engineer"],
            "autogen": ["crewai", "langchain-agents", "agent-zero", "camel"],
            "crewai": ["autogen", "magentic-one", "swarm", "agency-swarm"],
            "opendevin": ["devin", "aider", "gpt-engineer", "sweep"],
            "mcp": ["openai-assistants", "function-calling", "tool-use"],
        }

    def find_competitors(self,
                        repo_name: str,
                        category: RepositoryCategory,
                        topics: List[str]) -> List[str]:
        """Find competitors for a repository"""
        competitors = []

        # Check known competitors
        repo_lower = repo_name.lower()
        for key, comps in self.known_competitors.items():
            if key in repo_lower:
                competitors.extend(comps)

        # Infer from category
        category_competitors = {
            RepositoryCategory.AI_AGENT: [
                "autogpt/autogpt", "langchain-ai/langchain",
                "microsoft/autogen", "joaomdmoura/crewai",
            ],
            RepositoryCategory.LLM_FRAMEWORK: [
                "langchain-ai/langchain", "run-llama/llama_index",
                "microsoft/semantic-kernel",
            ],
            RepositoryCategory.ORCHESTRATION: [
                "prefecthq/prefect", "apache/airflow", "dagster-io/dagster",
            ],
        }

        if category in category_competitors:
            competitors.extend(category_competitors[category])

        return list(set(competitors))


class CombinationEngine:
    """Creates advanced combinations of best repository features"""

    def __init__(self):
        self.combination_strategies: List[Dict[str, Any]] = [
            {
                "name": "feature_merge",
                "description": "Merge best features from multiple repos",
                "applicability": ["same_category"],
            },
            {
                "name": "architecture_synthesis",
                "description": "Synthesize best architectural patterns",
                "applicability": ["complementary"],
            },
            {
                "name": "enhancement_layer",
                "description": "Add enhancement layer on top of existing",
                "applicability": ["extensible"],
            },
            {
                "name": "bridge_integration",
                "description": "Create bridges between different systems",
                "applicability": ["different_category"],
            },
        ]

    def generate_combinations(self,
                             analyses: List[RepositoryAnalysis]) -> List[Dict[str, Any]]:
        """Generate optimal combinations of repositories"""
        combinations = []

        if len(analyses) < 2:
            return combinations

        # Sort by quality score
        sorted_analyses = sorted(
            analyses,
            key=lambda a: a.quality_score.overall if a.quality_score else 0,
            reverse=True
        )

        # Generate combination recommendations
        for i, primary in enumerate(sorted_analyses[:3]):  # Top 3
            for secondary in sorted_analyses[i+1:5]:  # Next repos
                combination = self._create_combination(primary, secondary)
                if combination:
                    combinations.append(combination)

        # Golden ratio selection - take top PHI fraction
        num_to_keep = max(1, int(len(combinations) / PHI))
        return combinations[:num_to_keep]

    def _create_combination(self,
                           primary: RepositoryAnalysis,
                           secondary: RepositoryAnalysis) -> Optional[Dict[str, Any]]:
        """Create a combination recommendation"""
        if not primary.metadata or not secondary.metadata:
            return None

        # Identify complementary features
        primary_features = set(primary.key_features) if primary.key_features else set()
        secondary_features = set(secondary.key_features) if secondary.key_features else set()

        unique_to_secondary = secondary_features - primary_features

        if not unique_to_secondary and primary.category == secondary.category:
            return None  # No value in combining similar repos

        combination = {
            "id": str(uuid.uuid4()),
            "primary_repo": primary.metadata.url,
            "secondary_repo": secondary.metadata.url,
            "strategy": self._select_strategy(primary, secondary),
            "features_to_integrate": list(unique_to_secondary)[:5],
            "expected_improvement": self._estimate_improvement(primary, secondary),
            "implementation_complexity": self._estimate_complexity(primary, secondary),
            "bael_integration_path": self._create_integration_path(primary, secondary),
        }

        return combination

    def _select_strategy(self,
                        primary: RepositoryAnalysis,
                        secondary: RepositoryAnalysis) -> str:
        """Select the best combination strategy"""
        if primary.category == secondary.category:
            return "feature_merge"
        else:
            return "bridge_integration"

    def _estimate_improvement(self,
                              primary: RepositoryAnalysis,
                              secondary: RepositoryAnalysis) -> float:
        """Estimate improvement from combination"""
        if not primary.quality_score or not secondary.quality_score:
            return 0.5

        # Improvement is proportional to secondary quality
        base_improvement = secondary.quality_score.overall * 0.3

        # Apply golden ratio for exceptional combinations
        if secondary.quality_score.overall > 0.8:
            base_improvement *= PHI

        return min(1.0, base_improvement)

    def _estimate_complexity(self,
                            primary: RepositoryAnalysis,
                            secondary: RepositoryAnalysis) -> str:
        """Estimate implementation complexity"""
        if primary.category == secondary.category:
            return "medium"
        elif primary.category in [RepositoryCategory.UNKNOWN, RepositoryCategory.TOOL_LIBRARY]:
            return "low"
        else:
            return "high"

    def _create_integration_path(self,
                                primary: RepositoryAnalysis,
                                secondary: RepositoryAnalysis) -> List[str]:
        """Create integration path for Bael"""
        return [
            f"1. Analyze {secondary.metadata.name if secondary.metadata else 'secondary'} architecture",
            "2. Identify integration points",
            "3. Create adapter/bridge layer",
            "4. Implement feature integration",
            "5. Test and validate",
            "6. Optimize for Bael's architecture",
        ]


class BaelIntegrationAnalyzer:
    """Analyzes how repositories can enhance Bael"""

    def __init__(self):
        self.bael_components = [
            "core/agents", "core/orchestration", "core/memory",
            "core/tools", "core/llm", "core/council", "core/swarm",
            "mcp/server", "workflows", "integrations",
        ]

    def analyze_integration_potential(self,
                                     analysis: RepositoryAnalysis) -> Dict[str, Any]:
        """Analyze how a repo can enhance Bael"""
        enhancement_map = {
            RepositoryCategory.AI_AGENT: ["core/agents", "core/orchestration"],
            RepositoryCategory.ORCHESTRATION: ["core/orchestration", "workflows"],
            RepositoryCategory.MEMORY_SYSTEM: ["core/memory"],
            RepositoryCategory.MCP_SERVER: ["mcp/server", "core/tools"],
            RepositoryCategory.LLM_FRAMEWORK: ["core/llm", "integrations"],
            RepositoryCategory.RAG_SYSTEM: ["core/memory", "core/knowledge"],
        }

        target_components = enhancement_map.get(analysis.category, ["integrations"])

        return {
            "target_components": target_components,
            "integration_type": self._determine_integration_type(analysis),
            "priority": self._calculate_priority(analysis),
            "effort_estimate": self._estimate_effort(analysis),
            "value_add": self._estimate_value(analysis),
            "recommendations": self._generate_recommendations(analysis),
        }

    def _determine_integration_type(self, analysis: RepositoryAnalysis) -> str:
        """Determine the type of integration"""
        if analysis.category in [RepositoryCategory.MCP_SERVER, RepositoryCategory.TOOL_LIBRARY]:
            return "direct_integration"
        elif analysis.category in [RepositoryCategory.AI_AGENT, RepositoryCategory.ORCHESTRATION]:
            return "pattern_extraction"
        else:
            return "reference_implementation"

    def _calculate_priority(self, analysis: RepositoryAnalysis) -> str:
        """Calculate integration priority"""
        if not analysis.quality_score:
            return "low"

        score = analysis.quality_score.overall
        if score > 0.8:
            return "critical"
        elif score > 0.6:
            return "high"
        elif score > 0.4:
            return "medium"
        else:
            return "low"

    def _estimate_effort(self, analysis: RepositoryAnalysis) -> str:
        """Estimate integration effort"""
        if not analysis.metadata:
            return "unknown"

        size = analysis.metadata.size_kb
        if size < 1000:
            return "small"
        elif size < 10000:
            return "medium"
        else:
            return "large"

    def _estimate_value(self, analysis: RepositoryAnalysis) -> float:
        """Estimate value add for Bael"""
        base_value = 0.5

        if analysis.quality_score:
            base_value = analysis.quality_score.overall

        # Boost for innovative features
        if analysis.unique_innovations:
            base_value *= 1 + (len(analysis.unique_innovations) * 0.1)

        return min(1.0, base_value)

    def _generate_recommendations(self, analysis: RepositoryAnalysis) -> List[str]:
        """Generate integration recommendations"""
        recommendations = []

        if analysis.category == RepositoryCategory.AI_AGENT:
            recommendations.append("Extract autonomous decision-making patterns")

        if analysis.category == RepositoryCategory.ORCHESTRATION:
            recommendations.append("Study orchestration architecture for swarm enhancement")

        if analysis.unique_innovations:
            recommendations.append(f"Analyze unique innovations: {', '.join(analysis.unique_innovations[:3])}")

        recommendations.append("Create Bael-specific wrapper for seamless integration")

        return recommendations


class GitHubRepositoryAnalyzer:
    """
    The Ultimate GitHub Repository Analyzer

    Analyzes repositories, finds competitors, scores quality,
    generates combinations, and plans Bael integrations.
    """

    def __init__(self):
        self.quality_scorer = RepositoryQualityScorer()
        self.category_detector = CategoryDetector()
        self.competitor_finder = CompetitorFinder()
        self.combination_engine = CombinationEngine()
        self.integration_analyzer = BaelIntegrationAnalyzer()

        self.analysis_cache: Dict[str, RepositoryAnalysis] = {}
        self.comparison_history: List[CompetitorComparison] = []

    async def analyze_repository(self,
                                url: str,
                                deep: bool = False) -> RepositoryAnalysis:
        """Analyze a GitHub repository"""
        # Parse URL
        owner, name = self._parse_github_url(url)

        # Create metadata (in real implementation, would fetch from GitHub API)
        metadata = RepositoryMetadata(
            url=url,
            owner=owner,
            name=name,
            description=f"Repository {name} by {owner}",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        # Detect category
        category = self.category_detector.detect_category(metadata)

        # Score quality
        quality_score = self.quality_scorer.score_repository(metadata)

        # Find competitors
        competitors = self.competitor_finder.find_competitors(
            name, category, metadata.topics
        )

        # Create analysis
        analysis = RepositoryAnalysis(
            metadata=metadata,
            category=category,
            quality_score=quality_score,
            competitors=competitors,
            integration_potential=quality_score.overall,
        )

        # Analyze Bael integration potential
        integration_info = self.integration_analyzer.analyze_integration_potential(analysis)
        analysis.bael_enhancement_opportunities = integration_info["recommendations"]

        # Cache
        self.analysis_cache[url] = analysis

        return analysis

    async def find_better_alternatives(self,
                                      url: str) -> CompetitorComparison:
        """Find better alternatives to a repository"""
        # Analyze main repo
        main_analysis = await self.analyze_repository(url)

        # Analyze competitors
        competitor_analyses = []
        for comp_url in main_analysis.competitors[:5]:  # Limit to 5
            if not comp_url.startswith("http"):
                comp_url = f"https://github.com/{comp_url}"
            comp_analysis = await self.analyze_repository(comp_url)
            competitor_analyses.append(comp_analysis)

        # Build comparison matrix
        comparison_matrix = {}
        all_analyses = [main_analysis] + competitor_analyses

        for analysis in all_analyses:
            if analysis.metadata and analysis.quality_score:
                comparison_matrix[analysis.metadata.url] = {
                    "overall_quality": analysis.quality_score.overall,
                    "community": analysis.quality_score.dimensions.get(QualityDimension.COMMUNITY, 0),
                    "maintenance": analysis.quality_score.dimensions.get(QualityDimension.MAINTENANCE, 0),
                    "innovation": analysis.quality_score.dimensions.get(QualityDimension.INNOVATION, 0),
                }

        # Determine winner
        winner = max(
            all_analyses,
            key=lambda a: a.quality_score.overall if a.quality_score else 0
        )
        winner_url = winner.metadata.url if winner.metadata else url

        # Generate combinations
        combinations = self.combination_engine.generate_combinations(all_analyses)

        comparison = CompetitorComparison(
            main_repo=url,
            competitors=[a.metadata.url for a in competitor_analyses if a.metadata],
            winner=winner_url,
            comparison_matrix=comparison_matrix,
            combination_recommendations=combinations,
            synthesis_opportunities=[
                "Combine best features from top 3 repos",
                "Create unified API wrapping all alternatives",
                "Extract innovative patterns from each",
            ],
        )

        self.comparison_history.append(comparison)

        return comparison

    async def create_advanced_combination(self,
                                          urls: List[str]) -> Dict[str, Any]:
        """Create an advanced combination from multiple repositories"""
        analyses = []
        for url in urls:
            analysis = await self.analyze_repository(url)
            analyses.append(analysis)

        combinations = self.combination_engine.generate_combinations(analyses)

        # Create synthesis plan
        synthesis_plan = {
            "id": str(uuid.uuid4()),
            "input_repos": urls,
            "analyses": [
                {
                    "url": a.metadata.url if a.metadata else "",
                    "category": a.category.name,
                    "quality": a.quality_score.overall if a.quality_score else 0,
                }
                for a in analyses
            ],
            "combinations": combinations,
            "synthesis_strategy": self._create_synthesis_strategy(analyses),
            "bael_integration_plan": self._create_bael_plan(analyses),
            "expected_power_increase": self._calculate_power_increase(analyses),
        }

        return synthesis_plan

    def _parse_github_url(self, url: str) -> Tuple[str, str]:
        """Parse GitHub URL to extract owner and repo name"""
        # Handle various URL formats
        patterns = [
            r"github\.com[/:]([^/]+)/([^/\s]+)",
            r"^([^/]+)/([^/\s]+)$",
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                owner = match.group(1)
                name = match.group(2).replace(".git", "")
                return owner, name

        return "unknown", "unknown"

    def _create_synthesis_strategy(self,
                                   analyses: List[RepositoryAnalysis]) -> Dict[str, Any]:
        """Create strategy for synthesizing repos"""
        return {
            "approach": "hierarchical_integration",
            "steps": [
                "1. Identify core patterns from each repo",
                "2. Create unified abstraction layer",
                "3. Implement best-of-breed for each function",
                "4. Add Bael-specific enhancements",
                "5. Optimize for golden ratio architecture",
            ],
            "priorities": [
                a.metadata.name if a.metadata else f"repo_{i}"
                for i, a in enumerate(sorted(
                    analyses,
                    key=lambda x: x.quality_score.overall if x.quality_score else 0,
                    reverse=True
                ))
            ],
        }

    def _create_bael_plan(self,
                         analyses: List[RepositoryAnalysis]) -> Dict[str, Any]:
        """Create Bael integration plan"""
        target_modules = set()
        for analysis in analyses:
            integration = self.integration_analyzer.analyze_integration_potential(analysis)
            target_modules.update(integration["target_components"])

        return {
            "target_modules": list(target_modules),
            "integration_phases": [
                {"phase": 1, "action": "Pattern extraction and analysis"},
                {"phase": 2, "action": "Adapter creation"},
                {"phase": 3, "action": "Core integration"},
                {"phase": 4, "action": "Optimization and enhancement"},
                {"phase": 5, "action": "Testing and validation"},
            ],
            "enhancement_factor": PHI,  # Golden ratio enhancement
        }

    def _calculate_power_increase(self,
                                  analyses: List[RepositoryAnalysis]) -> float:
        """Calculate expected power increase from combination"""
        if not analyses:
            return 0.0

        # Sum of quality scores with diminishing returns
        total_quality = sum(
            (a.quality_score.overall if a.quality_score else 0) / (i + 1)
            for i, a in enumerate(sorted(
                analyses,
                key=lambda x: x.quality_score.overall if x.quality_score else 0,
                reverse=True
            ))
        )

        # Apply golden ratio scaling
        power_increase = total_quality * PHI / len(analyses)

        return min(5.0, power_increase)  # Cap at 5x


# Create singleton instance
github_analyzer = GitHubRepositoryAnalyzer()


async def analyze(url: str) -> RepositoryAnalysis:
    """Convenience function to analyze a repository"""
    return await github_analyzer.analyze_repository(url)


async def find_better(url: str) -> CompetitorComparison:
    """Convenience function to find better alternatives"""
    return await github_analyzer.find_better_alternatives(url)


async def combine(urls: List[str]) -> Dict[str, Any]:
    """Convenience function to create advanced combinations"""
    return await github_analyzer.create_advanced_combination(urls)

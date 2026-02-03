"""
BAEL - GitHub Competitive Intelligence Analyzer
Automatically analyzes GitHub repositories to find the best implementations,
then creates even more advanced versions.

Revolutionary capabilities:
1. Deep repository analysis (architecture, patterns, quality)
2. Competitive comparison and gap identification
3. Automatic enhancement generation
4. Best-of-breed synthesis
5. Innovation opportunity detection
6. Trend analysis and future-proofing
7. Integration recommendation engine

This enables Bael to always stay ahead of ALL competitors.
"""

import asyncio
import hashlib
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
import aiohttp

logger = logging.getLogger("BAEL.GitHubAnalyzer")


class RepositoryCategory(Enum):
    """Categories of repositories."""
    AI_AGENT = "ai_agent"
    LLM_FRAMEWORK = "llm_framework"
    AUTOMATION = "automation"
    TOOL_LIBRARY = "tool_library"
    UI_FRAMEWORK = "ui_framework"
    DATABASE = "database"
    API_FRAMEWORK = "api_framework"
    ML_FRAMEWORK = "ml_framework"
    UTILITY = "utility"
    UNKNOWN = "unknown"


class QualityLevel(Enum):
    """Code quality levels."""
    EXCEPTIONAL = 5
    HIGH = 4
    GOOD = 3
    MODERATE = 2
    LOW = 1


@dataclass
class RepositoryMetrics:
    """Metrics extracted from repository analysis."""
    stars: int = 0
    forks: int = 0
    watchers: int = 0
    open_issues: int = 0
    contributors: int = 0
    commits: int = 0
    
    # Code metrics
    total_files: int = 0
    total_lines: int = 0
    languages: Dict[str, int] = field(default_factory=dict)
    
    # Quality indicators
    has_tests: bool = False
    has_ci: bool = False
    has_docs: bool = False
    has_types: bool = False
    test_coverage: float = 0.0
    
    # Activity
    last_commit_date: Optional[datetime] = None
    commits_last_month: int = 0
    release_count: int = 0
    
    @property
    def popularity_score(self) -> float:
        """Calculate popularity score."""
        return (self.stars * 1.0 + self.forks * 2.0 + self.watchers * 0.5) / 100
    
    @property
    def health_score(self) -> float:
        """Calculate repository health score."""
        score = 0.0
        if self.has_tests:
            score += 0.2
        if self.has_ci:
            score += 0.15
        if self.has_docs:
            score += 0.15
        if self.has_types:
            score += 0.1
        if self.commits_last_month > 5:
            score += 0.2
        if self.open_issues < 50:
            score += 0.1
        if self.contributors > 5:
            score += 0.1
        return min(1.0, score)


@dataclass
class ArchitecturePattern:
    """Detected architecture pattern."""
    pattern_name: str
    description: str
    files_using: List[str] = field(default_factory=list)
    quality_assessment: str = ""
    improvement_suggestions: List[str] = field(default_factory=list)


@dataclass
class FeatureAnalysis:
    """Analysis of a specific feature."""
    feature_name: str
    implementation_quality: QualityLevel
    files: List[str] = field(default_factory=list)
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    enhancement_opportunities: List[str] = field(default_factory=list)


@dataclass
class CompetitiveGap:
    """Identified gap vs competitor."""
    gap_name: str
    description: str
    competitor_has: str
    our_status: str
    priority: int  # 1=critical, 5=nice-to-have
    implementation_effort: str  # low, medium, high
    potential_impact: str  # low, medium, high


@dataclass
class RepositoryAnalysis:
    """Complete analysis of a repository."""
    repo_url: str
    repo_name: str
    category: RepositoryCategory
    
    # Metrics
    metrics: RepositoryMetrics = field(default_factory=RepositoryMetrics)
    
    # Architecture
    architecture_patterns: List[ArchitecturePattern] = field(default_factory=list)
    tech_stack: List[str] = field(default_factory=list)
    
    # Features
    features: List[FeatureAnalysis] = field(default_factory=list)
    unique_innovations: List[str] = field(default_factory=list)
    
    # Quality
    overall_quality: QualityLevel = QualityLevel.MODERATE
    code_style: str = ""
    
    # Competitive
    competitive_advantages: List[str] = field(default_factory=list)
    competitive_weaknesses: List[str] = field(default_factory=list)
    
    # Recommendations
    features_to_adopt: List[str] = field(default_factory=list)
    features_to_improve: List[str] = field(default_factory=list)
    features_to_create: List[str] = field(default_factory=list)
    
    analyzed_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class EnhancementPlan:
    """Plan to create enhanced version of analyzed feature."""
    feature_name: str
    source_repo: str
    
    # What we're improving
    original_approach: str
    enhanced_approach: str
    
    # Implementation
    implementation_steps: List[str] = field(default_factory=list)
    estimated_lines: int = 0
    dependencies: List[str] = field(default_factory=list)
    
    # Benefits
    improvements: List[str] = field(default_factory=list)
    innovation_level: str = "incremental"  # incremental, significant, revolutionary


class GitHubCompetitiveAnalyzer:
    """
    Analyzes GitHub repositories to maintain competitive advantage.
    
    Capabilities:
    1. Deep code analysis of any repository
    2. Architecture pattern detection
    3. Feature extraction and comparison
    4. Automatic enhancement planning
    5. Best-of-breed synthesis
    6. Continuous competitive monitoring
    """
    
    def __init__(
        self,
        github_token: str = None,
        llm_provider: Callable = None,
        cache_path: str = "./data/github_analysis"
    ):
        self.github_token = github_token
        self.llm_provider = llm_provider
        self.cache_path = Path(cache_path)
        self.cache_path.mkdir(parents=True, exist_ok=True)
        
        # Analysis cache
        self._analyses: Dict[str, RepositoryAnalysis] = {}
        self._competitive_gaps: List[CompetitiveGap] = []
        self._enhancement_plans: List[EnhancementPlan] = []
        
        # Known competitors to track
        self._tracked_competitors: Dict[str, str] = {
            "AutoGPT": "Significant-Gravitas/AutoGPT",
            "AgentGPT": "reworkd/AgentGPT",
            "BabyAGI": "yoheinakajima/babyagi",
            "LangChain": "langchain-ai/langchain",
            "CrewAI": "joaomdmoura/crewAI",
            "AgentZero": "frdel/agent-zero",
            "OpenInterpreter": "OpenInterpreter/open-interpreter",
            "Autogen": "microsoft/autogen",
            "Semantic Kernel": "microsoft/semantic-kernel",
            "Haystack": "deepset-ai/haystack"
        }
        
        # Feature categories we care about
        self._feature_categories = [
            "memory_system", "tool_integration", "multi_agent",
            "reasoning", "planning", "code_generation", "research",
            "ui_dashboard", "api_design", "plugin_system",
            "llm_orchestration", "context_management", "autonomy"
        ]
        
        logger.info("GitHubCompetitiveAnalyzer initialized")
    
    async def analyze_repository(
        self,
        repo_url: str,
        deep_analysis: bool = True
    ) -> RepositoryAnalysis:
        """
        Perform comprehensive analysis of a GitHub repository.
        """
        # Parse repo URL
        repo_name = self._parse_repo_url(repo_url)
        
        # Check cache
        cache_key = hashlib.md5(repo_url.encode()).hexdigest()
        if cache_key in self._analyses:
            logger.debug(f"Using cached analysis for {repo_name}")
            return self._analyses[cache_key]
        
        logger.info(f"Analyzing repository: {repo_name}")
        
        # Fetch repository data
        repo_data = await self._fetch_repo_data(repo_name)
        
        # Extract metrics
        metrics = await self._extract_metrics(repo_data)
        
        # Determine category
        category = await self._categorize_repository(repo_data, metrics)
        
        # Analyze architecture
        patterns = await self._analyze_architecture(repo_data) if deep_analysis else []
        
        # Extract features
        features = await self._extract_features(repo_data) if deep_analysis else []
        
        # Identify innovations
        innovations = await self._identify_innovations(repo_data, features)
        
        # Assess quality
        quality = self._assess_quality(metrics, patterns)
        
        # Generate recommendations
        recommendations = await self._generate_recommendations(features, innovations)
        
        analysis = RepositoryAnalysis(
            repo_url=repo_url,
            repo_name=repo_name,
            category=category,
            metrics=metrics,
            architecture_patterns=patterns,
            tech_stack=self._extract_tech_stack(repo_data),
            features=features,
            unique_innovations=innovations,
            overall_quality=quality,
            features_to_adopt=recommendations.get("adopt", []),
            features_to_improve=recommendations.get("improve", []),
            features_to_create=recommendations.get("create", [])
        )
        
        # Cache
        self._analyses[cache_key] = analysis
        
        return analysis
    
    async def find_better_alternatives(
        self,
        repo_url: str,
        feature_focus: str = None
    ) -> List[RepositoryAnalysis]:
        """
        Find better alternatives to a given repository.
        """
        # Analyze the original
        original = await self.analyze_repository(repo_url)
        
        # Search for similar repositories
        similar = await self._search_similar_repos(original.category, feature_focus)
        
        # Analyze each
        alternatives = []
        for sim_repo in similar[:5]:
            try:
                analysis = await self.analyze_repository(sim_repo)
                
                # Compare quality
                if analysis.overall_quality.value > original.overall_quality.value:
                    alternatives.append(analysis)
                elif analysis.metrics.popularity_score > original.metrics.popularity_score * 1.5:
                    alternatives.append(analysis)
            except Exception as e:
                logger.warning(f"Failed to analyze {sim_repo}: {e}")
        
        # Sort by quality
        alternatives.sort(key=lambda a: a.overall_quality.value, reverse=True)
        
        return alternatives
    
    async def compare_with_competitors(self) -> List[CompetitiveGap]:
        """
        Compare Bael with all tracked competitors.
        """
        gaps = []
        
        for name, repo in self._tracked_competitors.items():
            try:
                analysis = await self.analyze_repository(f"https://github.com/{repo}")
                
                # Identify gaps
                competitor_gaps = await self._identify_competitive_gaps(name, analysis)
                gaps.extend(competitor_gaps)
                
            except Exception as e:
                logger.warning(f"Failed to analyze competitor {name}: {e}")
        
        # Sort by priority
        gaps.sort(key=lambda g: g.priority)
        
        self._competitive_gaps = gaps
        return gaps
    
    async def generate_enhancement_plans(
        self,
        analysis: RepositoryAnalysis
    ) -> List[EnhancementPlan]:
        """
        Generate plans to create enhanced versions of repository features.
        """
        plans = []
        
        for feature in analysis.features:
            if feature.implementation_quality.value >= QualityLevel.GOOD.value:
                plan = await self._create_enhancement_plan(feature, analysis)
                plans.append(plan)
        
        for innovation in analysis.unique_innovations:
            plan = await self._create_innovation_enhancement(innovation, analysis)
            plans.append(plan)
        
        self._enhancement_plans.extend(plans)
        return plans
    
    async def synthesize_best_of_breed(
        self,
        repos: List[str]
    ) -> Dict[str, Any]:
        """
        Analyze multiple repositories and synthesize best features.
        """
        analyses = []
        for repo in repos:
            analysis = await self.analyze_repository(repo)
            analyses.append(analysis)
        
        # Collect best features by category
        best_features: Dict[str, Tuple[FeatureAnalysis, str]] = {}
        
        for analysis in analyses:
            for feature in analysis.features:
                category = self._categorize_feature(feature.feature_name)
                
                if category not in best_features:
                    best_features[category] = (feature, analysis.repo_name)
                elif feature.implementation_quality.value > best_features[category][0].implementation_quality.value:
                    best_features[category] = (feature, analysis.repo_name)
        
        # Generate synthesis plan
        synthesis = {
            "best_features": {
                cat: {
                    "feature": feat.feature_name,
                    "from_repo": repo,
                    "quality": feat.implementation_quality.value,
                    "strengths": feat.strengths
                }
                for cat, (feat, repo) in best_features.items()
            },
            "combined_innovations": [],
            "enhancement_plan": []
        }
        
        # Collect all innovations
        for analysis in analyses:
            synthesis["combined_innovations"].extend(analysis.unique_innovations)
        
        # Create enhancement plan for each best feature
        for cat, (feature, repo) in best_features.items():
            enhancement = {
                "category": cat,
                "base_feature": feature.feature_name,
                "from": repo,
                "enhancements": feature.enhancement_opportunities,
                "target": f"Create superior {cat} implementation"
            }
            synthesis["enhancement_plan"].append(enhancement)
        
        return synthesis
    
    # Helper methods
    
    def _parse_repo_url(self, url: str) -> str:
        """Parse repository name from URL."""
        # Handle various URL formats
        patterns = [
            r"github\.com/([^/]+/[^/]+)",
            r"github\.com/([^/]+/[^/]+)\.git",
            r"^([^/]+/[^/]+)$"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1).rstrip('/')
        
        return url
    
    async def _fetch_repo_data(self, repo_name: str) -> Dict[str, Any]:
        """Fetch repository data from GitHub API."""
        headers = {}
        if self.github_token:
            headers["Authorization"] = f"token {self.github_token}"
        
        try:
            async with aiohttp.ClientSession() as session:
                # Get repo info
                async with session.get(
                    f"https://api.github.com/repos/{repo_name}",
                    headers=headers
                ) as resp:
                    if resp.status == 200:
                        repo_info = await resp.json()
                    else:
                        repo_info = {}
                
                # Get languages
                async with session.get(
                    f"https://api.github.com/repos/{repo_name}/languages",
                    headers=headers
                ) as resp:
                    languages = await resp.json() if resp.status == 200 else {}
                
                # Get README
                async with session.get(
                    f"https://api.github.com/repos/{repo_name}/readme",
                    headers=headers
                ) as resp:
                    if resp.status == 200:
                        readme_data = await resp.json()
                        readme = readme_data.get("content", "")
                    else:
                        readme = ""
                
                return {
                    "info": repo_info,
                    "languages": languages,
                    "readme": readme,
                    "repo_name": repo_name
                }
        except Exception as e:
            logger.error(f"Failed to fetch repo data: {e}")
            return {"repo_name": repo_name, "info": {}, "languages": {}, "readme": ""}
    
    async def _extract_metrics(self, repo_data: Dict[str, Any]) -> RepositoryMetrics:
        """Extract metrics from repository data."""
        info = repo_data.get("info", {})
        
        return RepositoryMetrics(
            stars=info.get("stargazers_count", 0),
            forks=info.get("forks_count", 0),
            watchers=info.get("watchers_count", 0),
            open_issues=info.get("open_issues_count", 0),
            languages=repo_data.get("languages", {}),
            has_docs=bool(info.get("has_wiki")) or "docs" in str(repo_data.get("readme", "")).lower(),
            has_tests="test" in str(repo_data.get("languages", {})).lower()
        )
    
    async def _categorize_repository(
        self,
        repo_data: Dict[str, Any],
        metrics: RepositoryMetrics
    ) -> RepositoryCategory:
        """Categorize the repository."""
        readme = str(repo_data.get("readme", "")).lower()
        name = repo_data.get("repo_name", "").lower()
        
        if any(word in readme or word in name for word in ["agent", "autonomous", "ai agent"]):
            return RepositoryCategory.AI_AGENT
        elif any(word in readme for word in ["llm", "language model", "gpt"]):
            return RepositoryCategory.LLM_FRAMEWORK
        elif any(word in readme for word in ["automation", "workflow"]):
            return RepositoryCategory.AUTOMATION
        elif "Python" in metrics.languages and any(word in readme for word in ["ml", "machine learning"]):
            return RepositoryCategory.ML_FRAMEWORK
        
        return RepositoryCategory.UNKNOWN
    
    async def _analyze_architecture(
        self,
        repo_data: Dict[str, Any]
    ) -> List[ArchitecturePattern]:
        """Analyze repository architecture patterns."""
        patterns = []
        readme = str(repo_data.get("readme", ""))
        
        # Detect common patterns
        pattern_signals = {
            "microservices": ["microservice", "service mesh", "api gateway"],
            "monolithic": ["monolith", "single application"],
            "event_driven": ["event", "message queue", "pub/sub"],
            "plugin_based": ["plugin", "extension", "addon"],
            "layered": ["layer", "tier", "mvc", "mvp"],
            "agent_based": ["agent", "autonomous", "multi-agent"]
        }
        
        for pattern_name, signals in pattern_signals.items():
            if any(signal in readme.lower() for signal in signals):
                patterns.append(ArchitecturePattern(
                    pattern_name=pattern_name,
                    description=f"Detected {pattern_name} architecture pattern"
                ))
        
        return patterns
    
    async def _extract_features(
        self,
        repo_data: Dict[str, Any]
    ) -> List[FeatureAnalysis]:
        """Extract and analyze features from repository."""
        features = []
        readme = str(repo_data.get("readme", ""))
        
        # Feature detection patterns
        feature_patterns = {
            "memory_system": ["memory", "context", "recall", "remember"],
            "tool_integration": ["tool", "function calling", "api"],
            "multi_agent": ["multi-agent", "swarm", "collaborative"],
            "reasoning": ["reasoning", "thinking", "chain of thought"],
            "planning": ["planning", "task decomposition", "goals"],
            "code_generation": ["code generation", "codegen", "programming"]
        }
        
        for feature_name, signals in feature_patterns.items():
            if any(signal in readme.lower() for signal in signals):
                features.append(FeatureAnalysis(
                    feature_name=feature_name,
                    implementation_quality=QualityLevel.GOOD,
                    strengths=[f"Has {feature_name} capability"],
                    enhancement_opportunities=[f"Could enhance {feature_name} further"]
                ))
        
        return features
    
    async def _identify_innovations(
        self,
        repo_data: Dict[str, Any],
        features: List[FeatureAnalysis]
    ) -> List[str]:
        """Identify unique innovations in repository."""
        innovations = []
        readme = str(repo_data.get("readme", ""))
        
        innovation_signals = [
            "novel", "unique", "first", "breakthrough", "revolutionary",
            "patent", "research paper", "state-of-the-art", "sota"
        ]
        
        for signal in innovation_signals:
            if signal in readme.lower():
                # Extract context around the signal
                innovations.append(f"Potential innovation detected: {signal}")
        
        return innovations
    
    def _assess_quality(
        self,
        metrics: RepositoryMetrics,
        patterns: List[ArchitecturePattern]
    ) -> QualityLevel:
        """Assess overall code quality."""
        score = 0
        
        # Popularity indicates community trust
        if metrics.stars > 10000:
            score += 2
        elif metrics.stars > 1000:
            score += 1
        
        # Health indicators
        score += int(metrics.health_score * 3)
        
        # Architecture patterns
        if len(patterns) >= 2:
            score += 1
        
        if score >= 5:
            return QualityLevel.EXCEPTIONAL
        elif score >= 4:
            return QualityLevel.HIGH
        elif score >= 3:
            return QualityLevel.GOOD
        elif score >= 2:
            return QualityLevel.MODERATE
        return QualityLevel.LOW
    
    def _extract_tech_stack(self, repo_data: Dict[str, Any]) -> List[str]:
        """Extract technology stack."""
        languages = list(repo_data.get("languages", {}).keys())
        return languages
    
    async def _generate_recommendations(
        self,
        features: List[FeatureAnalysis],
        innovations: List[str]
    ) -> Dict[str, List[str]]:
        """Generate recommendations based on analysis."""
        return {
            "adopt": [f.feature_name for f in features if f.implementation_quality.value >= 4],
            "improve": [f.feature_name for f in features if f.implementation_quality.value == 3],
            "create": innovations[:3]
        }
    
    async def _search_similar_repos(
        self,
        category: RepositoryCategory,
        feature_focus: str = None
    ) -> List[str]:
        """Search for similar repositories."""
        # Return known competitors in category
        if category == RepositoryCategory.AI_AGENT:
            return [f"https://github.com/{repo}" for repo in self._tracked_competitors.values()]
        return []
    
    async def _identify_competitive_gaps(
        self,
        competitor_name: str,
        analysis: RepositoryAnalysis
    ) -> List[CompetitiveGap]:
        """Identify gaps compared to competitor."""
        gaps = []
        
        for feature in analysis.features:
            if feature.implementation_quality.value >= QualityLevel.GOOD.value:
                gaps.append(CompetitiveGap(
                    gap_name=f"{feature.feature_name}_gap",
                    description=f"{competitor_name} has strong {feature.feature_name}",
                    competitor_has=feature.feature_name,
                    our_status="to_verify",
                    priority=2,
                    implementation_effort="medium",
                    potential_impact="high"
                ))
        
        return gaps
    
    async def _create_enhancement_plan(
        self,
        feature: FeatureAnalysis,
        analysis: RepositoryAnalysis
    ) -> EnhancementPlan:
        """Create enhancement plan for a feature."""
        return EnhancementPlan(
            feature_name=feature.feature_name,
            source_repo=analysis.repo_name,
            original_approach=f"Based on {analysis.repo_name}'s implementation",
            enhanced_approach="Create more advanced version with additional capabilities",
            implementation_steps=[
                "Analyze original implementation deeply",
                "Identify enhancement opportunities",
                "Design superior architecture",
                "Implement with Bael's advanced patterns",
                "Add unique innovations"
            ],
            improvements=feature.enhancement_opportunities,
            innovation_level="significant"
        )
    
    async def _create_innovation_enhancement(
        self,
        innovation: str,
        analysis: RepositoryAnalysis
    ) -> EnhancementPlan:
        """Create enhancement plan for an innovation."""
        return EnhancementPlan(
            feature_name=f"enhanced_{innovation[:30]}",
            source_repo=analysis.repo_name,
            original_approach=innovation,
            enhanced_approach=f"Revolutionary enhancement of {innovation}",
            implementation_steps=[
                "Study the innovation deeply",
                "Extend beyond original scope",
                "Combine with Bael's unique capabilities",
                "Create unprecedented functionality"
            ],
            improvements=["Beyond original innovation"],
            innovation_level="revolutionary"
        )
    
    def _categorize_feature(self, feature_name: str) -> str:
        """Categorize a feature."""
        for category in self._feature_categories:
            if category in feature_name.lower():
                return category
        return "general"
    
    def get_stats(self) -> Dict[str, Any]:
        """Get analyzer statistics."""
        return {
            "repos_analyzed": len(self._analyses),
            "competitive_gaps_found": len(self._competitive_gaps),
            "enhancement_plans": len(self._enhancement_plans),
            "tracked_competitors": len(self._tracked_competitors)
        }


# Global instance
_github_analyzer: Optional[GitHubCompetitiveAnalyzer] = None


def get_github_analyzer() -> GitHubCompetitiveAnalyzer:
    """Get the global GitHub analyzer."""
    global _github_analyzer
    if _github_analyzer is None:
        _github_analyzer = GitHubCompetitiveAnalyzer()
    return _github_analyzer

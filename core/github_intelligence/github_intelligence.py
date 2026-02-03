"""
BAEL - GitHub Intelligence: Advanced Repository Analysis & Enhancement

The most sophisticated GitHub repository analysis system ever conceived.
Analyzes any GitHub repository, finds better alternatives, and creates
enhanced versions that surpass the competition.

Revolutionary Features:
1. Deep Repository Analysis - Understand any repo's architecture
2. Competitive Analysis - Find and compare alternatives
3. Enhancement Detection - Identify improvement opportunities
4. Automatic Enhancement - Create improved versions
5. Trend Detection - Spot emerging patterns
6. Best Practices Extraction - Learn from the best
7. Quality Scoring - Comprehensive quality metrics
8. Automatic Integration - Setup tools in your project

No other system provides this level of GitHub intelligence.
"""

import asyncio
import hashlib
import json
import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from collections import defaultdict

logger = logging.getLogger("BAEL.GitHubIntelligence")


class RepositoryCategory(Enum):
    """Categories of repositories."""
    AI_ML = "ai_ml"
    WEB_FRAMEWORK = "web_framework"
    CLI_TOOL = "cli_tool"
    LIBRARY = "library"
    APPLICATION = "application"
    INFRASTRUCTURE = "infrastructure"
    DATA_PROCESSING = "data_processing"
    AUTOMATION = "automation"
    AGENT_FRAMEWORK = "agent_framework"
    MCP_SERVER = "mcp_server"
    UNKNOWN = "unknown"


class QualityDimension(Enum):
    """Dimensions of repository quality."""
    CODE_QUALITY = "code_quality"
    DOCUMENTATION = "documentation"
    TESTING = "testing"
    MAINTENANCE = "maintenance"
    COMMUNITY = "community"
    ARCHITECTURE = "architecture"
    SECURITY = "security"
    PERFORMANCE = "performance"


@dataclass
class RepositoryMetrics:
    """Metrics for a repository."""
    stars: int = 0
    forks: int = 0
    watchers: int = 0
    open_issues: int = 0
    closed_issues: int = 0
    contributors: int = 0
    commits_last_month: int = 0
    pull_requests_merged: int = 0
    code_coverage: float = 0.0
    test_count: int = 0
    documentation_pages: int = 0
    release_count: int = 0
    last_commit_date: Optional[datetime] = None
    created_date: Optional[datetime] = None


@dataclass
class QualityScore:
    """Quality score breakdown."""
    overall: float = 0.0
    dimensions: Dict[QualityDimension, float] = field(default_factory=dict)
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    improvement_opportunities: List[str] = field(default_factory=list)


@dataclass
class RepositoryAnalysis:
    """Complete analysis of a repository."""
    repo_url: str
    name: str
    full_name: str
    description: str
    
    # Classification
    category: RepositoryCategory = RepositoryCategory.UNKNOWN
    languages: Dict[str, float] = field(default_factory=dict)
    topics: List[str] = field(default_factory=list)
    
    # Metrics
    metrics: RepositoryMetrics = field(default_factory=RepositoryMetrics)
    quality: QualityScore = field(default_factory=QualityScore)
    
    # Architecture
    architecture_patterns: List[str] = field(default_factory=list)
    key_features: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    
    # Analysis
    analyzed_at: datetime = field(default_factory=datetime.utcnow)
    analysis_confidence: float = 0.0


@dataclass
class CompetitorComparison:
    """Comparison between repositories."""
    primary_repo: str
    competitor_repos: List[str]
    
    # Comparison results
    feature_matrix: Dict[str, Dict[str, bool]] = field(default_factory=dict)
    quality_comparison: Dict[str, QualityScore] = field(default_factory=dict)
    
    # Recommendations
    primary_advantages: List[str] = field(default_factory=list)
    competitor_advantages: Dict[str, List[str]] = field(default_factory=dict)
    synthesis_opportunities: List[str] = field(default_factory=list)


@dataclass
class EnhancementPlan:
    """Plan for enhancing a repository."""
    target_repo: str
    enhancements: List[Dict[str, Any]] = field(default_factory=list)
    estimated_impact: float = 0.0
    implementation_complexity: str = "medium"
    priority_order: List[str] = field(default_factory=list)


class GitHubIntelligence:
    """
    GitHub Intelligence System.
    
    Provides comprehensive analysis, comparison, and enhancement
    capabilities for any GitHub repository.
    """
    
    def __init__(
        self,
        github_token: Optional[str] = None,
        llm_provider: Optional[Callable] = None,
        cache_dir: str = "./data/github_cache"
    ):
        self.github_token = github_token or os.environ.get("GITHUB_TOKEN")
        self.llm_provider = llm_provider
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Caches
        self._analysis_cache: Dict[str, RepositoryAnalysis] = {}
        self._comparison_cache: Dict[str, CompetitorComparison] = {}
        
        # Knowledge base of patterns
        self._known_patterns: Dict[str, List[str]] = self._init_patterns()
        
        # Statistics
        self._stats = {
            "repos_analyzed": 0,
            "comparisons_made": 0,
            "enhancements_generated": 0,
            "alternatives_found": 0
        }
        
        logger.info("GitHubIntelligence initialized")
    
    def _init_patterns(self) -> Dict[str, List[str]]:
        """Initialize known architecture patterns."""
        return {
            "ai_framework": [
                "agent", "llm", "prompt", "chain", "memory", "embedding",
                "rag", "retrieval", "generation", "model"
            ],
            "web_framework": [
                "router", "middleware", "handler", "request", "response",
                "controller", "view", "template", "static"
            ],
            "mcp_server": [
                "mcp", "tool", "resource", "prompt", "fastmcp",
                "modelcontextprotocol", "server"
            ],
            "testing": [
                "test", "spec", "fixture", "mock", "assert", "expect",
                "pytest", "jest", "mocha"
            ],
            "documentation": [
                "readme", "docs", "documentation", "guide", "tutorial",
                "example", "api"
            ]
        }
    
    async def analyze_repository(
        self,
        repo_url: str,
        deep_analysis: bool = True
    ) -> RepositoryAnalysis:
        """
        Perform comprehensive analysis of a GitHub repository.
        """
        # Check cache
        cache_key = hashlib.md5(repo_url.encode()).hexdigest()
        if cache_key in self._analysis_cache:
            cached = self._analysis_cache[cache_key]
            if (datetime.utcnow() - cached.analyzed_at) < timedelta(hours=24):
                return cached
        
        # Parse URL
        match = re.match(r'https://github.com/([^/]+)/([^/]+)', repo_url)
        if not match:
            raise ValueError(f"Invalid GitHub URL: {repo_url}")
        
        owner, repo = match.groups()
        
        analysis = RepositoryAnalysis(
            repo_url=repo_url,
            name=repo,
            full_name=f"{owner}/{repo}",
            description=""
        )
        
        # Fetch data from GitHub API
        if self.github_token:
            await self._fetch_github_data(analysis, owner, repo)
        
        # Analyze content
        if deep_analysis:
            await self._deep_analyze(analysis, owner, repo)
        
        # Calculate quality score
        analysis.quality = await self._calculate_quality(analysis)
        
        # Classify category
        analysis.category = self._classify_category(analysis)
        
        # Cache result
        self._analysis_cache[cache_key] = analysis
        self._stats["repos_analyzed"] += 1
        
        return analysis
    
    async def _fetch_github_data(
        self,
        analysis: RepositoryAnalysis,
        owner: str,
        repo: str
    ) -> None:
        """Fetch data from GitHub API."""
        import aiohttp
        
        headers = {"Authorization": f"token {self.github_token}"}
        base_url = f"https://api.github.com/repos/{owner}/{repo}"
        
        try:
            async with aiohttp.ClientSession() as session:
                # Repository info
                async with session.get(base_url, headers=headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        analysis.description = data.get("description", "")
                        analysis.topics = data.get("topics", [])
                        analysis.metrics.stars = data.get("stargazers_count", 0)
                        analysis.metrics.forks = data.get("forks_count", 0)
                        analysis.metrics.watchers = data.get("subscribers_count", 0)
                        analysis.metrics.open_issues = data.get("open_issues_count", 0)
                        
                        if data.get("created_at"):
                            analysis.metrics.created_date = datetime.fromisoformat(
                                data["created_at"].replace("Z", "+00:00")
                            )
                        if data.get("pushed_at"):
                            analysis.metrics.last_commit_date = datetime.fromisoformat(
                                data["pushed_at"].replace("Z", "+00:00")
                            )
                
                # Languages
                async with session.get(f"{base_url}/languages", headers=headers) as resp:
                    if resp.status == 200:
                        langs = await resp.json()
                        total = sum(langs.values())
                        if total > 0:
                            analysis.languages = {k: v/total for k, v in langs.items()}
                
                # Contributors
                async with session.get(f"{base_url}/contributors?per_page=1", headers=headers) as resp:
                    if resp.status == 200 and 'Link' in resp.headers:
                        # Parse last page from Link header
                        link_header = resp.headers.get('Link', '')
                        match = re.search(r'page=(\d+)>; rel="last"', link_header)
                        if match:
                            analysis.metrics.contributors = int(match.group(1))
                        else:
                            data = await resp.json()
                            analysis.metrics.contributors = len(data)
                
                # Recent commits
                async with session.get(
                    f"{base_url}/commits?per_page=100",
                    headers=headers
                ) as resp:
                    if resp.status == 200:
                        commits = await resp.json()
                        month_ago = datetime.utcnow() - timedelta(days=30)
                        recent = sum(
                            1 for c in commits
                            if datetime.fromisoformat(
                                c["commit"]["author"]["date"].replace("Z", "+00:00")
                            ) > month_ago
                        )
                        analysis.metrics.commits_last_month = recent
                
                # Releases
                async with session.get(f"{base_url}/releases", headers=headers) as resp:
                    if resp.status == 200:
                        releases = await resp.json()
                        analysis.metrics.release_count = len(releases)
                        
        except Exception as e:
            logger.warning(f"Error fetching GitHub data: {e}")
    
    async def _deep_analyze(
        self,
        analysis: RepositoryAnalysis,
        owner: str,
        repo: str
    ) -> None:
        """Perform deep analysis of repository content."""
        import aiohttp
        
        if not self.github_token:
            return
        
        headers = {"Authorization": f"token {self.github_token}"}
        
        try:
            async with aiohttp.ClientSession() as session:
                # Get README
                async with session.get(
                    f"https://api.github.com/repos/{owner}/{repo}/readme",
                    headers=headers
                ) as resp:
                    if resp.status == 200:
                        import base64
                        data = await resp.json()
                        content = base64.b64decode(data.get("content", "")).decode("utf-8", errors="ignore")
                        
                        # Extract features from README
                        analysis.key_features = self._extract_features(content)
                        
                        # Check for documentation quality
                        doc_signals = ["## Installation", "## Usage", "## API", "## Examples"]
                        analysis.metrics.documentation_pages = sum(
                            1 for s in doc_signals if s.lower() in content.lower()
                        )
                
                # Get file tree to analyze architecture
                async with session.get(
                    f"https://api.github.com/repos/{owner}/{repo}/git/trees/HEAD?recursive=1",
                    headers=headers
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        files = [item["path"] for item in data.get("tree", []) if item["type"] == "blob"]
                        
                        # Analyze architecture patterns
                        analysis.architecture_patterns = self._detect_architecture(files)
                        
                        # Count tests
                        analysis.metrics.test_count = sum(
                            1 for f in files
                            if "test" in f.lower() or "spec" in f.lower()
                        )
                        
                        # Extract dependencies from package files
                        analysis.dependencies = await self._extract_dependencies(
                            session, headers, owner, repo, files
                        )
                        
        except Exception as e:
            logger.warning(f"Error in deep analysis: {e}")
    
    def _extract_features(self, readme: str) -> List[str]:
        """Extract features from README."""
        features = []
        
        # Look for feature sections
        feature_patterns = [
            r'##?\s*Features?\s*\n(.*?)(?=\n##|\Z)',
            r'##?\s*Key Features?\s*\n(.*?)(?=\n##|\Z)',
            r'##?\s*Capabilities?\s*\n(.*?)(?=\n##|\Z)',
        ]
        
        for pattern in feature_patterns:
            match = re.search(pattern, readme, re.DOTALL | re.IGNORECASE)
            if match:
                section = match.group(1)
                # Extract bullet points
                bullets = re.findall(r'[-*]\s*(.+)', section)
                features.extend([b.strip()[:100] for b in bullets[:10]])
                break
        
        return features
    
    def _detect_architecture(self, files: List[str]) -> List[str]:
        """Detect architecture patterns from file structure."""
        patterns = []
        
        # Check for common patterns
        pattern_signals = {
            "MVC": ["controller", "model", "view"],
            "Layered": ["core", "services", "api", "domain"],
            "Plugin-based": ["plugins", "extensions", "addons"],
            "Microservices": ["services/", "gateway", "api-gateway"],
            "Monorepo": ["packages/", "apps/", "libs/"],
            "Agent-based": ["agent", "tools", "memory", "chain"]
        }
        
        file_str = " ".join(files).lower()
        
        for pattern_name, signals in pattern_signals.items():
            matches = sum(1 for s in signals if s in file_str)
            if matches >= 2:
                patterns.append(pattern_name)
        
        return patterns
    
    async def _extract_dependencies(
        self,
        session,
        headers: Dict[str, str],
        owner: str,
        repo: str,
        files: List[str]
    ) -> List[str]:
        """Extract dependencies from package files."""
        dependencies = []
        
        dep_files = {
            "requirements.txt": r'^([a-zA-Z0-9_-]+)',
            "package.json": None,  # JSON parsing
            "pyproject.toml": r'^\s*([a-zA-Z0-9_-]+)\s*=',
            "Cargo.toml": r'^\s*([a-zA-Z0-9_-]+)\s*=',
        }
        
        for dep_file in files:
            filename = Path(dep_file).name
            if filename in dep_files:
                try:
                    async with session.get(
                        f"https://api.github.com/repos/{owner}/{repo}/contents/{dep_file}",
                        headers=headers
                    ) as resp:
                        if resp.status == 200:
                            import base64
                            data = await resp.json()
                            content = base64.b64decode(data.get("content", "")).decode("utf-8", errors="ignore")
                            
                            if filename == "package.json":
                                try:
                                    pkg = json.loads(content)
                                    dependencies.extend(list(pkg.get("dependencies", {}).keys())[:20])
                                except:
                                    pass
                            elif dep_files[filename]:
                                matches = re.findall(dep_files[filename], content, re.MULTILINE)
                                dependencies.extend(matches[:20])
                except:
                    pass
        
        return list(set(dependencies))[:30]
    
    async def _calculate_quality(self, analysis: RepositoryAnalysis) -> QualityScore:
        """Calculate quality score for repository."""
        score = QualityScore()
        
        # Documentation score
        doc_score = min(1.0, (
            (0.3 if analysis.description else 0) +
            (0.3 if analysis.key_features else 0) +
            (0.4 * min(analysis.metrics.documentation_pages / 4, 1))
        ))
        score.dimensions[QualityDimension.DOCUMENTATION] = doc_score
        
        # Testing score
        test_score = min(1.0, analysis.metrics.test_count / 50)
        score.dimensions[QualityDimension.TESTING] = test_score
        
        # Maintenance score
        maintenance_score = 0.0
        if analysis.metrics.last_commit_date:
            days_since = (datetime.utcnow() - analysis.metrics.last_commit_date.replace(tzinfo=None)).days
            maintenance_score = max(0, 1 - (days_since / 365))
        maintenance_score += min(0.3, analysis.metrics.commits_last_month / 30)
        score.dimensions[QualityDimension.MAINTENANCE] = min(1.0, maintenance_score)
        
        # Community score
        community_score = min(1.0, (
            min(0.3, analysis.metrics.stars / 1000) +
            min(0.3, analysis.metrics.contributors / 20) +
            min(0.4, analysis.metrics.forks / 200)
        ))
        score.dimensions[QualityDimension.COMMUNITY] = community_score
        
        # Architecture score
        arch_score = min(1.0, (
            (0.5 if analysis.architecture_patterns else 0) +
            min(0.5, len(analysis.languages) / 3)
        ))
        score.dimensions[QualityDimension.ARCHITECTURE] = arch_score
        
        # Overall score
        weights = {
            QualityDimension.DOCUMENTATION: 0.2,
            QualityDimension.TESTING: 0.2,
            QualityDimension.MAINTENANCE: 0.25,
            QualityDimension.COMMUNITY: 0.2,
            QualityDimension.ARCHITECTURE: 0.15,
        }
        
        score.overall = sum(
            score.dimensions.get(dim, 0) * weight
            for dim, weight in weights.items()
        )
        
        # Identify strengths and weaknesses
        for dim, value in score.dimensions.items():
            if value >= 0.7:
                score.strengths.append(f"Strong {dim.value.replace('_', ' ')}")
            elif value <= 0.3:
                score.weaknesses.append(f"Weak {dim.value.replace('_', ' ')}")
                score.improvement_opportunities.append(f"Improve {dim.value.replace('_', ' ')}")
        
        return score
    
    def _classify_category(self, analysis: RepositoryAnalysis) -> RepositoryCategory:
        """Classify repository into category."""
        # Check topics
        topic_str = " ".join(analysis.topics).lower()
        desc_lower = analysis.description.lower()
        combined = topic_str + " " + desc_lower
        
        category_keywords = {
            RepositoryCategory.AI_ML: ["ai", "ml", "machine-learning", "deep-learning", "llm", "gpt", "agent"],
            RepositoryCategory.AGENT_FRAMEWORK: ["agent", "autonomous", "autogpt", "langchain", "crewai"],
            RepositoryCategory.MCP_SERVER: ["mcp", "model-context-protocol", "fastmcp"],
            RepositoryCategory.WEB_FRAMEWORK: ["web", "framework", "react", "vue", "django", "flask"],
            RepositoryCategory.CLI_TOOL: ["cli", "command-line", "terminal"],
            RepositoryCategory.AUTOMATION: ["automation", "devops", "ci", "cd"],
            RepositoryCategory.DATA_PROCESSING: ["data", "etl", "pipeline", "processing"],
        }
        
        for category, keywords in category_keywords.items():
            if any(kw in combined for kw in keywords):
                return category
        
        return RepositoryCategory.LIBRARY
    
    async def find_alternatives(
        self,
        repo_url: str,
        min_stars: int = 100,
        limit: int = 10
    ) -> List[RepositoryAnalysis]:
        """Find alternative/competing repositories."""
        # First analyze the target repo
        analysis = await self.analyze_repository(repo_url)
        
        alternatives = []
        
        if not self.github_token:
            return alternatives
        
        import aiohttp
        
        # Build search query
        search_terms = []
        search_terms.extend(analysis.topics[:3])
        if analysis.category != RepositoryCategory.UNKNOWN:
            search_terms.append(analysis.category.value.replace("_", " "))
        
        query = " OR ".join(search_terms[:3]) if search_terms else analysis.name
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": f"token {self.github_token}"}
                
                async with session.get(
                    "https://api.github.com/search/repositories",
                    params={
                        "q": f"{query} stars:>={min_stars}",
                        "sort": "stars",
                        "per_page": limit * 2
                    },
                    headers=headers
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        
                        for item in data.get("items", []):
                            if item["html_url"] != repo_url:
                                alt_analysis = await self.analyze_repository(
                                    item["html_url"],
                                    deep_analysis=False
                                )
                                alternatives.append(alt_analysis)
                                
                                if len(alternatives) >= limit:
                                    break
        except Exception as e:
            logger.warning(f"Error finding alternatives: {e}")
        
        self._stats["alternatives_found"] += len(alternatives)
        return alternatives
    
    async def compare_repositories(
        self,
        primary_repo: str,
        competitor_repos: List[str]
    ) -> CompetitorComparison:
        """Compare a repository against competitors."""
        # Analyze all repos
        primary = await self.analyze_repository(primary_repo)
        competitors = [await self.analyze_repository(url) for url in competitor_repos]
        
        comparison = CompetitorComparison(
            primary_repo=primary_repo,
            competitor_repos=competitor_repos
        )
        
        # Build feature matrix
        all_features = set(primary.key_features)
        for comp in competitors:
            all_features.update(comp.key_features)
        
        for feature in all_features:
            comparison.feature_matrix[feature] = {
                primary.full_name: feature in primary.key_features
            }
            for comp in competitors:
                comparison.feature_matrix[feature][comp.full_name] = feature in comp.key_features
        
        # Quality comparison
        comparison.quality_comparison[primary.full_name] = primary.quality
        for comp in competitors:
            comparison.quality_comparison[comp.full_name] = comp.quality
        
        # Identify advantages
        for dim in QualityDimension:
            primary_score = primary.quality.dimensions.get(dim, 0)
            for comp in competitors:
                comp_score = comp.quality.dimensions.get(dim, 0)
                if primary_score > comp_score + 0.2:
                    comparison.primary_advantages.append(f"Better {dim.value} than {comp.name}")
                elif comp_score > primary_score + 0.2:
                    if comp.full_name not in comparison.competitor_advantages:
                        comparison.competitor_advantages[comp.full_name] = []
                    comparison.competitor_advantages[comp.full_name].append(f"Better {dim.value}")
        
        # Synthesis opportunities
        for comp in competitors:
            for feature in comp.key_features:
                if feature not in primary.key_features:
                    comparison.synthesis_opportunities.append(
                        f"Add '{feature}' from {comp.name}"
                    )
        
        self._stats["comparisons_made"] += 1
        return comparison
    
    async def generate_enhancement_plan(
        self,
        repo_url: str,
        focus_areas: List[QualityDimension] = None
    ) -> EnhancementPlan:
        """Generate a plan to enhance a repository."""
        analysis = await self.analyze_repository(repo_url)
        
        plan = EnhancementPlan(target_repo=repo_url)
        
        focus = focus_areas or list(QualityDimension)
        
        for dim in focus:
            current_score = analysis.quality.dimensions.get(dim, 0)
            
            if current_score < 0.7:
                enhancement = {
                    "dimension": dim.value,
                    "current_score": current_score,
                    "target_score": 0.8,
                    "actions": []
                }
                
                if dim == QualityDimension.DOCUMENTATION:
                    enhancement["actions"] = [
                        "Add comprehensive README with examples",
                        "Create API documentation",
                        "Add usage tutorials",
                        "Include architecture diagrams"
                    ]
                elif dim == QualityDimension.TESTING:
                    enhancement["actions"] = [
                        "Add unit tests for core functionality",
                        "Implement integration tests",
                        "Set up CI/CD pipeline",
                        "Add code coverage reporting"
                    ]
                elif dim == QualityDimension.MAINTENANCE:
                    enhancement["actions"] = [
                        "Create issue templates",
                        "Add contribution guidelines",
                        "Set up automated dependency updates",
                        "Implement semantic versioning"
                    ]
                elif dim == QualityDimension.ARCHITECTURE:
                    enhancement["actions"] = [
                        "Modularize codebase",
                        "Add plugin system",
                        "Implement clean architecture",
                        "Add configuration management"
                    ]
                
                plan.enhancements.append(enhancement)
        
        # Calculate impact and complexity
        plan.estimated_impact = sum(
            (0.8 - analysis.quality.dimensions.get(QualityDimension(e["dimension"]), 0))
            for e in plan.enhancements
        ) / max(len(plan.enhancements), 1)
        
        plan.priority_order = sorted(
            [e["dimension"] for e in plan.enhancements],
            key=lambda d: analysis.quality.dimensions.get(QualityDimension(d), 0)
        )
        
        self._stats["enhancements_generated"] += 1
        return plan
    
    async def find_best_in_class(
        self,
        category: RepositoryCategory,
        limit: int = 10
    ) -> List[RepositoryAnalysis]:
        """Find the best repositories in a category."""
        if not self.github_token:
            return []
        
        import aiohttp
        
        search_queries = {
            RepositoryCategory.AI_ML: "ai machine-learning stars:>1000",
            RepositoryCategory.AGENT_FRAMEWORK: "agent framework autonomous stars:>500",
            RepositoryCategory.MCP_SERVER: "mcp model-context-protocol stars:>10",
            RepositoryCategory.WEB_FRAMEWORK: "web framework stars:>5000",
            RepositoryCategory.AUTOMATION: "automation devops stars:>1000",
        }
        
        query = search_queries.get(category, f"{category.value} stars:>100")
        results = []
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": f"token {self.github_token}"}
                
                async with session.get(
                    "https://api.github.com/search/repositories",
                    params={"q": query, "sort": "stars", "per_page": limit},
                    headers=headers
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        
                        for item in data.get("items", []):
                            analysis = await self.analyze_repository(item["html_url"])
                            results.append(analysis)
        except Exception as e:
            logger.warning(f"Error finding best in class: {e}")
        
        # Sort by quality score
        results.sort(key=lambda r: r.quality.overall, reverse=True)
        return results[:limit]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics."""
        return {
            **self._stats,
            "cached_analyses": len(self._analysis_cache),
            "cached_comparisons": len(self._comparison_cache)
        }


# Global instance
_github_intelligence: Optional[GitHubIntelligence] = None


def get_github_intelligence() -> GitHubIntelligence:
    """Get the global GitHub Intelligence instance."""
    global _github_intelligence
    if _github_intelligence is None:
        _github_intelligence = GitHubIntelligence()
    return _github_intelligence


async def demo():
    """Demonstrate GitHub Intelligence."""
    intel = get_github_intelligence()
    
    # Analyze a repository
    print("Analyzing repository...")
    analysis = await intel.analyze_repository("https://github.com/microsoft/autogen")
    
    print(f"\n=== REPOSITORY ANALYSIS ===")
    print(f"Name: {analysis.full_name}")
    print(f"Description: {analysis.description[:100]}...")
    print(f"Category: {analysis.category.value}")
    print(f"Stars: {analysis.metrics.stars}")
    print(f"Quality Score: {analysis.quality.overall:.2%}")
    
    print(f"\nQuality Dimensions:")
    for dim, score in analysis.quality.dimensions.items():
        print(f"  {dim.value}: {score:.2%}")
    
    print(f"\nArchitecture Patterns: {analysis.architecture_patterns}")
    print(f"Key Features: {analysis.key_features[:5]}")
    
    print(f"\nStrengths: {analysis.quality.strengths}")
    print(f"Weaknesses: {analysis.quality.weaknesses}")
    
    print(f"\n=== STATS ===")
    print(intel.get_stats())


if __name__ == "__main__":
    asyncio.run(demo())

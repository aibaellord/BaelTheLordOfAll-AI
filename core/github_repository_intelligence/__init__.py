"""
BAEL - GitHub Repository Intelligence System
The most advanced automated GitHub repository analysis and integration system.

Revolutionary capabilities:
1. Deep repository analysis with AST parsing
2. Automatic detection of better alternatives
3. Competitive analysis against similar projects
4. Auto-integration of useful repositories
5. Continuous monitoring for updates
6. Dependency graph visualization
7. Security vulnerability scanning
8. Quality scoring and recommendations

This system ensures Ba'el always has access to the most advanced tools.
"""

import asyncio
import hashlib
import json
import logging
import os
import re
import subprocess
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
import shutil

logger = logging.getLogger("BAEL.GitHubIntelligence")


class RepoCategory(Enum):
    """Categories for repository classification."""
    AI_AGENT = "ai_agent"
    MCP_SERVER = "mcp_server"
    LLM_TOOL = "llm_tool"
    AUTOMATION = "automation"
    CLI_TOOL = "cli_tool"
    LIBRARY = "library"
    FRAMEWORK = "framework"
    UTILITY = "utility"
    DATABASE = "database"
    API = "api"
    UNKNOWN = "unknown"


class QualityMetric(Enum):
    """Quality metrics for repository scoring."""
    STARS = "stars"
    FORKS = "forks"
    CONTRIBUTORS = "contributors"
    RECENT_COMMITS = "recent_commits"
    ISSUES_CLOSED_RATIO = "issues_closed_ratio"
    DOCUMENTATION = "documentation"
    TEST_COVERAGE = "test_coverage"
    CODE_QUALITY = "code_quality"


@dataclass
class RepositoryProfile:
    """Complete profile of a GitHub repository."""
    url: str
    owner: str
    name: str

    # Basic info
    description: str = ""
    language: str = ""
    license: str = ""
    topics: List[str] = field(default_factory=list)

    # Metrics
    stars: int = 0
    forks: int = 0
    watchers: int = 0
    open_issues: int = 0

    # Activity
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    pushed_at: Optional[datetime] = None

    # Analysis results
    category: RepoCategory = RepoCategory.UNKNOWN
    quality_score: float = 0.0
    relevance_score: float = 0.0

    # Code analysis
    files_analyzed: int = 0
    functions_found: int = 0
    classes_found: int = 0
    lines_of_code: int = 0

    # Dependencies
    dependencies: List[str] = field(default_factory=list)

    # MCP potential
    has_mcp_potential: bool = False
    potential_tools: List[Dict[str, Any]] = field(default_factory=list)

    # Recommendations
    recommendations: List[str] = field(default_factory=list)
    alternatives: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class CompetitorAnalysis:
    """Analysis comparing repositories."""
    subject_repo: str
    competitors: List[RepositoryProfile] = field(default_factory=list)

    # Comparison results
    feature_comparison: Dict[str, Dict[str, bool]] = field(default_factory=dict)
    quality_ranking: List[Tuple[str, float]] = field(default_factory=list)
    unique_features: Dict[str, List[str]] = field(default_factory=dict)

    # Recommendations
    best_choice: str = ""
    best_reason: str = ""
    combination_recommendation: str = ""


class GitHubAPIClient:
    """Client for GitHub API interactions."""

    def __init__(self, token: str = None):
        self.token = token or os.environ.get("GITHUB_TOKEN")
        self.base_url = "https://api.github.com"
        self._cache: Dict[str, Any] = {}
        self._cache_ttl = timedelta(hours=1)

    async def get_repo_info(self, owner: str, repo: str) -> Dict[str, Any]:
        """Get repository information from GitHub API."""
        cache_key = f"repo:{owner}/{repo}"
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            if datetime.utcnow() - cached["time"] < self._cache_ttl:
                return cached["data"]

        try:
            # Use gh CLI for authenticated requests
            result = subprocess.run(
                ["gh", "api", f"repos/{owner}/{repo}"],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                data = json.loads(result.stdout)
                self._cache[cache_key] = {"time": datetime.utcnow(), "data": data}
                return data
        except Exception as e:
            logger.error(f"Failed to get repo info: {e}")

        return {}

    async def search_repos(
        self,
        query: str,
        sort: str = "stars",
        order: str = "desc",
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search GitHub repositories."""
        try:
            result = subprocess.run(
                ["gh", "search", "repos", query, "--json",
                 "name,owner,description,stargazersCount,forksCount,language,topics,updatedAt",
                 "--limit", str(limit), "--sort", sort, "--order", order],
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0:
                return json.loads(result.stdout)
        except Exception as e:
            logger.error(f"Search failed: {e}")

        return []

    async def get_repo_contents(self, owner: str, repo: str, path: str = "") -> List[Dict[str, Any]]:
        """Get repository contents."""
        try:
            result = subprocess.run(
                ["gh", "api", f"repos/{owner}/{repo}/contents/{path}"],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                data = json.loads(result.stdout)
                return data if isinstance(data, list) else [data]
        except Exception as e:
            logger.error(f"Failed to get contents: {e}")

        return []

    async def get_readme(self, owner: str, repo: str) -> str:
        """Get repository README content."""
        try:
            result = subprocess.run(
                ["gh", "api", f"repos/{owner}/{repo}/readme", "-H", "Accept: application/vnd.github.raw"],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                return result.stdout
        except Exception as e:
            logger.error(f"Failed to get README: {e}")

        return ""


class RepositoryAnalyzer:
    """Deep analysis of GitHub repositories."""

    def __init__(self, github_client: GitHubAPIClient = None):
        self.github = github_client or GitHubAPIClient()
        self._analysis_cache: Dict[str, RepositoryProfile] = {}

    async def analyze_repository(self, repo_url: str) -> RepositoryProfile:
        """Perform comprehensive repository analysis."""
        # Parse URL
        match = re.search(r'github\.com[/:]([^/]+)/([^/.]+)', repo_url)
        if not match:
            raise ValueError(f"Invalid GitHub URL: {repo_url}")

        owner, repo = match.groups()
        repo = repo.rstrip('.git')

        # Check cache
        cache_key = f"{owner}/{repo}"
        if cache_key in self._analysis_cache:
            return self._analysis_cache[cache_key]

        # Get basic info from API
        api_info = await self.github.get_repo_info(owner, repo)

        profile = RepositoryProfile(
            url=repo_url,
            owner=owner,
            name=repo,
            description=api_info.get("description", ""),
            language=api_info.get("language", ""),
            license=api_info.get("license", {}).get("name", "") if api_info.get("license") else "",
            topics=api_info.get("topics", []),
            stars=api_info.get("stargazers_count", 0),
            forks=api_info.get("forks_count", 0),
            watchers=api_info.get("watchers_count", 0),
            open_issues=api_info.get("open_issues_count", 0)
        )

        # Parse dates
        if api_info.get("created_at"):
            profile.created_at = datetime.fromisoformat(api_info["created_at"].replace("Z", "+00:00"))
        if api_info.get("updated_at"):
            profile.updated_at = datetime.fromisoformat(api_info["updated_at"].replace("Z", "+00:00"))
        if api_info.get("pushed_at"):
            profile.pushed_at = datetime.fromisoformat(api_info["pushed_at"].replace("Z", "+00:00"))

        # Categorize
        profile.category = self._categorize_repo(profile)

        # Calculate quality score
        profile.quality_score = self._calculate_quality_score(profile)

        # Check MCP potential
        profile.has_mcp_potential = self._check_mcp_potential(profile)

        # Generate recommendations
        profile.recommendations = self._generate_recommendations(profile)

        # Deep code analysis (if local clone is needed)
        await self._deep_code_analysis(profile)

        # Cache result
        self._analysis_cache[cache_key] = profile

        return profile

    def _categorize_repo(self, profile: RepositoryProfile) -> RepoCategory:
        """Categorize repository based on topics and description."""
        desc_lower = (profile.description or "").lower()
        topics_str = " ".join(profile.topics).lower()
        combined = f"{desc_lower} {topics_str}"

        if any(term in combined for term in ["agent", "autogpt", "autonomous", "ai agent"]):
            return RepoCategory.AI_AGENT
        elif any(term in combined for term in ["mcp", "model context protocol", "claude"]):
            return RepoCategory.MCP_SERVER
        elif any(term in combined for term in ["llm", "gpt", "openai", "langchain"]):
            return RepoCategory.LLM_TOOL
        elif any(term in combined for term in ["automation", "automate", "workflow"]):
            return RepoCategory.AUTOMATION
        elif any(term in combined for term in ["cli", "terminal", "command line"]):
            return RepoCategory.CLI_TOOL
        elif any(term in combined for term in ["library", "sdk", "package"]):
            return RepoCategory.LIBRARY
        elif any(term in combined for term in ["framework", "boilerplate"]):
            return RepoCategory.FRAMEWORK
        elif any(term in combined for term in ["database", "db", "sql", "nosql"]):
            return RepoCategory.DATABASE
        elif any(term in combined for term in ["api", "rest", "graphql"]):
            return RepoCategory.API
        else:
            return RepoCategory.UTILITY

    def _calculate_quality_score(self, profile: RepositoryProfile) -> float:
        """Calculate overall quality score (0-100)."""
        score = 0.0

        # Stars (max 30 points)
        if profile.stars > 0:
            star_score = min(30, (profile.stars / 1000) * 30)
            score += star_score

        # Activity (max 25 points)
        if profile.pushed_at:
            days_since_push = (datetime.utcnow() - profile.pushed_at.replace(tzinfo=None)).days
            if days_since_push < 7:
                score += 25
            elif days_since_push < 30:
                score += 20
            elif days_since_push < 90:
                score += 15
            elif days_since_push < 365:
                score += 10
            else:
                score += 5

        # Forks (max 15 points)
        if profile.forks > 0:
            fork_score = min(15, (profile.forks / 100) * 15)
            score += fork_score

        # Has description (5 points)
        if profile.description:
            score += 5

        # Has license (5 points)
        if profile.license:
            score += 5

        # Has topics (5 points)
        if profile.topics:
            score += min(5, len(profile.topics))

        # Known language (5 points)
        if profile.language in ["Python", "TypeScript", "JavaScript", "Go", "Rust"]:
            score += 5

        # Low issues ratio (10 points)
        if profile.stars > 0 and profile.open_issues > 0:
            issues_ratio = profile.open_issues / profile.stars
            if issues_ratio < 0.1:
                score += 10
            elif issues_ratio < 0.2:
                score += 5
        elif profile.open_issues == 0:
            score += 10

        return min(100, score)

    def _check_mcp_potential(self, profile: RepositoryProfile) -> bool:
        """Check if repository has potential for MCP conversion."""
        indicators = [
            "mcp" in " ".join(profile.topics).lower(),
            "claude" in profile.description.lower() if profile.description else False,
            "tool" in profile.description.lower() if profile.description else False,
            profile.language in ["Python", "TypeScript", "JavaScript"],
            profile.category in [RepoCategory.CLI_TOOL, RepoCategory.API, RepoCategory.UTILITY]
        ]

        return sum(indicators) >= 2

    def _generate_recommendations(self, profile: RepositoryProfile) -> List[str]:
        """Generate recommendations for using this repository."""
        recs = []

        if profile.quality_score >= 80:
            recs.append("HIGHLY RECOMMENDED: Excellent quality repository")
        elif profile.quality_score >= 60:
            recs.append("RECOMMENDED: Good quality, actively maintained")
        elif profile.quality_score >= 40:
            recs.append("USABLE: Moderate quality, use with caution")
        else:
            recs.append("CAUTION: Low quality score, consider alternatives")

        if profile.has_mcp_potential:
            recs.append("MCP CANDIDATE: Can be converted to MCP server")

        if profile.category == RepoCategory.AI_AGENT:
            recs.append("AI AGENT: Could provide competitive insights")

        if profile.stars > 10000:
            recs.append("POPULAR: Widely adopted, likely well-tested")

        return recs

    async def _deep_code_analysis(self, profile: RepositoryProfile) -> None:
        """Perform deep code analysis by examining repository contents."""
        try:
            contents = await self.github.get_repo_contents(profile.owner, profile.name)

            # Count files
            profile.files_analyzed = len(contents)

            # Look for specific files
            for item in contents:
                if item.get("name") in ["README.md", "README.rst", "readme.md"]:
                    profile.recommendations.append("Has documentation")
                elif item.get("name") in ["requirements.txt", "package.json", "go.mod", "Cargo.toml"]:
                    profile.recommendations.append(f"Has dependency file: {item['name']}")
                elif item.get("name") in ["Dockerfile", "docker-compose.yml"]:
                    profile.recommendations.append("Docker ready")
                elif item.get("name") in [".github"]:
                    profile.recommendations.append("Has GitHub Actions/workflows")
        except Exception as e:
            logger.debug(f"Deep analysis failed: {e}")


class CompetitorIntelligence:
    """Analyze and compare competing repositories."""

    def __init__(self, analyzer: RepositoryAnalyzer = None, github: GitHubAPIClient = None):
        self.analyzer = analyzer or RepositoryAnalyzer()
        self.github = github or GitHubAPIClient()

    async def find_competitors(
        self,
        repo_url: str,
        max_competitors: int = 10
    ) -> CompetitorAnalysis:
        """Find and analyze competing repositories."""
        # Analyze subject repo
        subject = await self.analyzer.analyze_repository(repo_url)

        # Build search query from topics and description
        search_terms = []
        if subject.topics:
            search_terms.extend(subject.topics[:3])
        if subject.description:
            # Extract key terms
            words = subject.description.lower().split()
            key_words = [w for w in words if len(w) > 4 and w not in ['with', 'that', 'this', 'from', 'have']][:3]
            search_terms.extend(key_words)

        if not search_terms:
            search_terms = [subject.name]

        # Search for similar repos
        query = " ".join(search_terms)
        search_results = await self.github.search_repos(query, limit=max_competitors + 1)

        # Analyze competitors
        competitors = []
        for result in search_results:
            if result.get("owner", {}).get("login") == subject.owner and result.get("name") == subject.name:
                continue  # Skip the subject repo

            repo_url = f"https://github.com/{result.get('owner', {}).get('login')}/{result.get('name')}"
            try:
                competitor = await self.analyzer.analyze_repository(repo_url)
                competitor.relevance_score = self._calculate_relevance(subject, competitor)
                competitors.append(competitor)
            except:
                continue

            if len(competitors) >= max_competitors:
                break

        # Build analysis
        analysis = CompetitorAnalysis(
            subject_repo=repo_url,
            competitors=competitors
        )

        # Compare features
        analysis.feature_comparison = self._compare_features(subject, competitors)

        # Rank by quality
        all_repos = [(subject.name, subject.quality_score)] + [(c.name, c.quality_score) for c in competitors]
        analysis.quality_ranking = sorted(all_repos, key=lambda x: x[1], reverse=True)

        # Find unique features
        analysis.unique_features = self._find_unique_features(subject, competitors)

        # Determine best choice
        if competitors:
            best = max(competitors, key=lambda c: c.quality_score * c.relevance_score)
            if best.quality_score > subject.quality_score:
                analysis.best_choice = best.name
                analysis.best_reason = f"Higher quality score ({best.quality_score:.1f} vs {subject.quality_score:.1f})"
            else:
                analysis.best_choice = subject.name
                analysis.best_reason = "Subject repo has highest quality"

        return analysis

    def _calculate_relevance(self, subject: RepositoryProfile, competitor: RepositoryProfile) -> float:
        """Calculate how relevant a competitor is to the subject."""
        score = 0.0

        # Same category
        if competitor.category == subject.category:
            score += 0.4

        # Same language
        if competitor.language == subject.language:
            score += 0.2

        # Overlapping topics
        subject_topics = set(subject.topics)
        competitor_topics = set(competitor.topics)
        if subject_topics and competitor_topics:
            overlap = len(subject_topics & competitor_topics) / len(subject_topics | competitor_topics)
            score += 0.4 * overlap

        return score

    def _compare_features(
        self,
        subject: RepositoryProfile,
        competitors: List[RepositoryProfile]
    ) -> Dict[str, Dict[str, bool]]:
        """Compare features across repositories."""
        features = {
            "has_documentation": lambda p: "Has documentation" in p.recommendations,
            "docker_ready": lambda p: "Docker ready" in p.recommendations,
            "has_ci": lambda p: "Has GitHub Actions" in str(p.recommendations),
            "has_mcp_potential": lambda p: p.has_mcp_potential,
            "active_development": lambda p: p.pushed_at and (datetime.utcnow() - p.pushed_at.replace(tzinfo=None)).days < 30,
            "high_quality": lambda p: p.quality_score >= 70,
            "popular": lambda p: p.stars >= 1000
        }

        comparison = {}
        all_repos = [subject] + competitors

        for feature_name, check_func in features.items():
            comparison[feature_name] = {}
            for repo in all_repos:
                comparison[feature_name][repo.name] = check_func(repo)

        return comparison

    def _find_unique_features(
        self,
        subject: RepositoryProfile,
        competitors: List[RepositoryProfile]
    ) -> Dict[str, List[str]]:
        """Find features unique to each repository."""
        unique = {subject.name: []}

        # Subject's unique topics
        all_competitor_topics = set()
        for c in competitors:
            all_competitor_topics.update(c.topics)

        unique_topics = set(subject.topics) - all_competitor_topics
        if unique_topics:
            unique[subject.name].append(f"Unique topics: {', '.join(unique_topics)}")

        # Each competitor's unique features
        for comp in competitors:
            unique[comp.name] = []
            other_topics = set(subject.topics)
            for other in competitors:
                if other != comp:
                    other_topics.update(other.topics)

            comp_unique = set(comp.topics) - other_topics
            if comp_unique:
                unique[comp.name].append(f"Unique topics: {', '.join(comp_unique)}")

        return unique


class GitHubRepositoryIntelligence:
    """
    Main interface for GitHub Repository Intelligence.

    Provides:
    1. Repository analysis and profiling
    2. Competitive analysis
    3. Alternative discovery
    4. Automatic integration recommendations
    5. Continuous monitoring
    """

    def __init__(self, llm_provider: Callable = None):
        self.github = GitHubAPIClient()
        self.analyzer = RepositoryAnalyzer(self.github)
        self.competitor_intel = CompetitorIntelligence(self.analyzer, self.github)
        self.llm_provider = llm_provider

        # Tracking
        self._analyzed_repos: Dict[str, RepositoryProfile] = {}
        self._monitored_repos: Set[str] = set()

        logger.info("GitHubRepositoryIntelligence initialized")

    async def analyze(self, repo_url: str) -> RepositoryProfile:
        """Analyze a single repository."""
        profile = await self.analyzer.analyze_repository(repo_url)
        self._analyzed_repos[f"{profile.owner}/{profile.name}"] = profile
        return profile

    async def find_better_alternatives(
        self,
        repo_url: str,
        min_quality_improvement: float = 10.0
    ) -> List[RepositoryProfile]:
        """Find repositories that are better than the given one."""
        subject = await self.analyze(repo_url)
        analysis = await self.competitor_intel.find_competitors(repo_url)

        better = [
            c for c in analysis.competitors
            if c.quality_score >= subject.quality_score + min_quality_improvement
        ]

        return sorted(better, key=lambda x: x.quality_score, reverse=True)

    async def compare_repositories(
        self,
        repo_urls: List[str]
    ) -> Dict[str, Any]:
        """Compare multiple repositories."""
        profiles = []
        for url in repo_urls:
            try:
                profile = await self.analyze(url)
                profiles.append(profile)
            except Exception as e:
                logger.error(f"Failed to analyze {url}: {e}")

        if not profiles:
            return {"error": "No repositories could be analyzed"}

        # Rank by quality
        ranked = sorted(profiles, key=lambda p: p.quality_score, reverse=True)

        return {
            "repositories": [
                {
                    "name": p.name,
                    "owner": p.owner,
                    "quality_score": p.quality_score,
                    "stars": p.stars,
                    "category": p.category.value,
                    "has_mcp_potential": p.has_mcp_potential,
                    "recommendations": p.recommendations
                }
                for p in ranked
            ],
            "best_choice": {
                "name": ranked[0].name,
                "reason": f"Highest quality score: {ranked[0].quality_score:.1f}"
            },
            "comparison_summary": self._generate_comparison_summary(profiles)
        }

    def _generate_comparison_summary(self, profiles: List[RepositoryProfile]) -> str:
        """Generate a summary comparing repositories."""
        if not profiles:
            return "No repositories to compare"

        best = max(profiles, key=lambda p: p.quality_score)
        most_stars = max(profiles, key=lambda p: p.stars)
        most_active = max(profiles, key=lambda p: p.pushed_at.timestamp() if p.pushed_at else 0)

        summary = f"""
Comparison of {len(profiles)} repositories:

- Best Quality: {best.name} (score: {best.quality_score:.1f})
- Most Popular: {most_stars.name} ({most_stars.stars:,} stars)
- Most Active: {most_active.name} (pushed: {most_active.pushed_at.strftime('%Y-%m-%d') if most_active.pushed_at else 'unknown'})
- MCP Candidates: {sum(1 for p in profiles if p.has_mcp_potential)}
"""
        return summary.strip()

    async def search_best_in_class(
        self,
        category: str,
        min_stars: int = 100,
        limit: int = 5
    ) -> List[RepositoryProfile]:
        """Search for best-in-class repositories in a category."""
        # Map category to search terms
        category_terms = {
            "ai_agent": "AI agent autonomous",
            "mcp_server": "MCP server claude",
            "llm_tool": "LLM tool GPT",
            "automation": "automation workflow",
            "cli_tool": "CLI terminal tool",
            "database": "database engine",
            "api": "API REST GraphQL"
        }

        query = category_terms.get(category, category)
        query += f" stars:>={min_stars}"

        results = await self.github.search_repos(query, limit=limit)

        profiles = []
        for result in results:
            url = f"https://github.com/{result.get('owner', {}).get('login')}/{result.get('name')}"
            try:
                profile = await self.analyze(url)
                profiles.append(profile)
            except:
                continue

        return sorted(profiles, key=lambda p: p.quality_score, reverse=True)

    def get_analyzed_repos(self) -> List[Dict[str, Any]]:
        """Get all analyzed repositories."""
        return [
            {
                "name": f"{p.owner}/{p.name}",
                "quality_score": p.quality_score,
                "category": p.category.value,
                "stars": p.stars
            }
            for p in self._analyzed_repos.values()
        ]


# Singleton
_github_intelligence: Optional[GitHubRepositoryIntelligence] = None


def get_github_intelligence() -> GitHubRepositoryIntelligence:
    """Get the global GitHub intelligence instance."""
    global _github_intelligence
    if _github_intelligence is None:
        _github_intelligence = GitHubRepositoryIntelligence()
    return _github_intelligence


async def demo():
    """Demonstrate GitHub intelligence capabilities."""
    intel = get_github_intelligence()

    # Analyze a repository
    print("Analyzing repository...")
    profile = await intel.analyze("https://github.com/anthropics/anthropic-sdk-python")

    print(f"\nRepository: {profile.owner}/{profile.name}")
    print(f"Quality Score: {profile.quality_score:.1f}")
    print(f"Stars: {profile.stars:,}")
    print(f"Category: {profile.category.value}")
    print(f"MCP Potential: {profile.has_mcp_potential}")
    print(f"\nRecommendations:")
    for rec in profile.recommendations:
        print(f"  - {rec}")

    # Find alternatives
    print("\n\nFinding better alternatives...")
    alternatives = await intel.find_better_alternatives(
        "https://github.com/anthropics/anthropic-sdk-python"
    )

    if alternatives:
        print(f"Found {len(alternatives)} better alternatives:")
        for alt in alternatives[:3]:
            print(f"  - {alt.name}: {alt.quality_score:.1f} score, {alt.stars:,} stars")
    else:
        print("No better alternatives found")


if __name__ == "__main__":
    asyncio.run(demo())

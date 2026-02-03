"""
GitHub Integration Plugin for BAEL
Provides GitHub API access for repository operations.
"""

import logging
from typing import Any, Dict, List, Optional

try:
    from github import Github, GithubException
    GITHUB_AVAILABLE = True
except ImportError:
    GITHUB_AVAILABLE = False

from core.plugins.registry import PluginInterface, PluginManifest

logger = logging.getLogger("BAEL.Plugin.GitHub")


class GitHubIntegration(PluginInterface):
    """GitHub API integration."""

    def __init__(self, manifest: PluginManifest, config: Dict[str, Any]):
        super().__init__(manifest, config)

        if not GITHUB_AVAILABLE:
            raise ImportError("PyGithub not installed. Install with: pip install PyGithub")

        self.token = config.get("token")
        self.default_repo = config.get("default_repo")
        self.per_page = config.get("per_page", 30)
        self.github: Optional[Github] = None

    async def initialize(self) -> bool:
        """Initialize the plugin."""
        if not self.token:
            self.logger.error("GitHub token not provided")
            return False

        try:
            self.github = Github(self.token, per_page=self.per_page)
            user = self.github.get_user()
            self.logger.info(f"✅ GitHub integration initialized (user: {user.login})")
            return True
        except GithubException as e:
            self.logger.error(f"Failed to authenticate with GitHub: {e}")
            return False

    def get_repository(self, repo_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get repository information.

        Args:
            repo_name: Repository name in format "owner/repo"

        Returns:
            Repository information
        """
        repo_name = repo_name or self.default_repo
        if not repo_name:
            return {"error": "No repository specified"}

        try:
            repo = self.github.get_repo(repo_name)
            return {
                "name": repo.name,
                "full_name": repo.full_name,
                "description": repo.description,
                "stars": repo.stargazers_count,
                "forks": repo.forks_count,
                "open_issues": repo.open_issues_count,
                "language": repo.language,
                "created_at": repo.created_at.isoformat(),
                "updated_at": repo.updated_at.isoformat(),
                "url": repo.html_url
            }
        except GithubException as e:
            self.logger.error(f"Failed to get repository: {e}")
            return {"error": str(e)}

    def list_issues(
        self,
        repo_name: Optional[str] = None,
        state: str = "open",
        labels: Optional[List[str]] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        List repository issues.

        Args:
            repo_name: Repository name
            state: Issue state (open, closed, all)
            labels: Filter by labels
            limit: Maximum number of issues to return

        Returns:
            List of issues
        """
        repo_name = repo_name or self.default_repo
        if not repo_name:
            return [{"error": "No repository specified"}]

        try:
            repo = self.github.get_repo(repo_name)
            issues = repo.get_issues(state=state, labels=labels or [])

            result = []
            for i, issue in enumerate(issues):
                if i >= limit:
                    break

                result.append({
                    "number": issue.number,
                    "title": issue.title,
                    "state": issue.state,
                    "author": issue.user.login,
                    "labels": [label.name for label in issue.labels],
                    "comments": issue.comments,
                    "created_at": issue.created_at.isoformat(),
                    "url": issue.html_url
                })

            return result

        except GithubException as e:
            self.logger.error(f"Failed to list issues: {e}")
            return [{"error": str(e)}]

    def create_issue(
        self,
        title: str,
        body: str,
        repo_name: Optional[str] = None,
        labels: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Create a new issue.

        Args:
            title: Issue title
            body: Issue description
            repo_name: Repository name
            labels: Issue labels

        Returns:
            Created issue information
        """
        repo_name = repo_name or self.default_repo
        if not repo_name:
            return {"error": "No repository specified"}

        try:
            repo = self.github.get_repo(repo_name)
            issue = repo.create_issue(
                title=title,
                body=body,
                labels=labels or []
            )

            self.logger.info(f"Created issue #{issue.number}: {title}")

            return {
                "number": issue.number,
                "title": issue.title,
                "url": issue.html_url,
                "state": issue.state
            }

        except GithubException as e:
            self.logger.error(f"Failed to create issue: {e}")
            return {"error": str(e)}

    async def shutdown(self):
        """Cleanup resources."""
        if self.github:
            self.github.close()
        self.logger.info("GitHub integration shutdown")


def register(manifest: PluginManifest, config: Dict[str, Any]) -> GitHubIntegration:
    """
    Plugin entry point.

    Args:
        manifest: Plugin manifest
        config: Plugin configuration

    Returns:
        GitHubIntegration instance
    """
    return GitHubIntegration(manifest, config)

"""
BAEL - GitHub Integration
Integration with GitHub for repository operations.
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from integrations import BaseIntegration, IntegrationConfig, IntegrationStatus

logger = logging.getLogger("BAEL.Integrations.GitHub")


@dataclass
class GitHubRepo:
    """GitHub repository representation."""
    owner: str
    name: str
    full_name: str
    description: Optional[str]
    default_branch: str
    private: bool
    url: str


@dataclass
class GitHubIssue:
    """GitHub issue representation."""
    number: int
    title: str
    body: Optional[str]
    state: str
    labels: List[str]
    assignees: List[str]
    created_at: datetime
    updated_at: datetime


@dataclass
class GitHubPR:
    """GitHub pull request representation."""
    number: int
    title: str
    body: Optional[str]
    state: str
    head_branch: str
    base_branch: str
    merged: bool
    mergeable: Optional[bool]
    created_at: datetime


class GitHubIntegration(BaseIntegration):
    """
    GitHub integration for repository operations.

    Supports:
    - Repository listing and info
    - Issue management
    - Pull request operations
    - Code search
    - File operations
    """

    API_BASE = "https://api.github.com"

    def __init__(self, config: IntegrationConfig):
        super().__init__(config)
        self._token = config.credentials.get("token", "")
        self._default_owner = config.settings.get("default_owner", "")

    async def connect(self) -> bool:
        """Connect to GitHub API."""
        try:
            # Test authentication
            result = await self._make_request("GET", "/user")
            if result:
                self.status = IntegrationStatus.CONNECTED
                logger.info(f"Connected to GitHub as {result.get('login')}")
                return True
        except Exception as e:
            logger.error(f"Failed to connect to GitHub: {e}")
            self.status = IntegrationStatus.ERROR
        return False

    async def disconnect(self) -> None:
        """Disconnect from GitHub."""
        self.status = IntegrationStatus.DISCONNECTED

    async def test_connection(self) -> bool:
        """Test GitHub connection."""
        try:
            result = await self._make_request("GET", "/rate_limit")
            return result is not None
        except:
            return False

    async def _make_request(
        self,
        method: str,
        path: str,
        data: Optional[Dict] = None
    ) -> Optional[Dict]:
        """Make an API request to GitHub."""
        # In production, use aiohttp or httpx
        # This is a placeholder implementation
        import json
        import urllib.request

        url = f"{self.API_BASE}{path}"
        headers = {
            "Authorization": f"token {self._token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "BAEL-AI"
        }

        req = urllib.request.Request(url, headers=headers, method=method)

        if data:
            req.data = json.dumps(data).encode()
            req.add_header("Content-Type", "application/json")

        try:
            with urllib.request.urlopen(req) as response:
                return json.loads(response.read().decode())
        except Exception as e:
            logger.error(f"GitHub API error: {e}")
            return None

    # -------------------------------------------------------------------------
    # Repository Operations
    # -------------------------------------------------------------------------

    async def list_repos(
        self,
        owner: Optional[str] = None,
        limit: int = 30
    ) -> List[GitHubRepo]:
        """List repositories for an owner."""
        owner = owner or self._default_owner
        result = await self._make_request("GET", f"/users/{owner}/repos")

        if not result:
            return []

        return [
            GitHubRepo(
                owner=repo["owner"]["login"],
                name=repo["name"],
                full_name=repo["full_name"],
                description=repo.get("description"),
                default_branch=repo.get("default_branch", "main"),
                private=repo.get("private", False),
                url=repo["html_url"]
            )
            for repo in result[:limit]
        ]

    async def get_repo(
        self,
        repo: str,
        owner: Optional[str] = None
    ) -> Optional[GitHubRepo]:
        """Get repository details."""
        owner = owner or self._default_owner
        result = await self._make_request("GET", f"/repos/{owner}/{repo}")

        if not result:
            return None

        return GitHubRepo(
            owner=result["owner"]["login"],
            name=result["name"],
            full_name=result["full_name"],
            description=result.get("description"),
            default_branch=result.get("default_branch", "main"),
            private=result.get("private", False),
            url=result["html_url"]
        )

    # -------------------------------------------------------------------------
    # Issue Operations
    # -------------------------------------------------------------------------

    async def list_issues(
        self,
        repo: str,
        owner: Optional[str] = None,
        state: str = "open",
        limit: int = 30
    ) -> List[GitHubIssue]:
        """List issues for a repository."""
        owner = owner or self._default_owner
        result = await self._make_request(
            "GET",
            f"/repos/{owner}/{repo}/issues?state={state}"
        )

        if not result:
            return []

        return [
            GitHubIssue(
                number=issue["number"],
                title=issue["title"],
                body=issue.get("body"),
                state=issue["state"],
                labels=[l["name"] for l in issue.get("labels", [])],
                assignees=[a["login"] for a in issue.get("assignees", [])],
                created_at=datetime.fromisoformat(
                    issue["created_at"].replace("Z", "+00:00")
                ),
                updated_at=datetime.fromisoformat(
                    issue["updated_at"].replace("Z", "+00:00")
                )
            )
            for issue in result[:limit]
            if "pull_request" not in issue  # Exclude PRs
        ]

    async def create_issue(
        self,
        repo: str,
        title: str,
        body: Optional[str] = None,
        labels: Optional[List[str]] = None,
        owner: Optional[str] = None
    ) -> Optional[GitHubIssue]:
        """Create a new issue."""
        owner = owner or self._default_owner

        data = {"title": title}
        if body:
            data["body"] = body
        if labels:
            data["labels"] = labels

        result = await self._make_request(
            "POST",
            f"/repos/{owner}/{repo}/issues",
            data
        )

        if not result:
            return None

        return GitHubIssue(
            number=result["number"],
            title=result["title"],
            body=result.get("body"),
            state=result["state"],
            labels=[l["name"] for l in result.get("labels", [])],
            assignees=[a["login"] for a in result.get("assignees", [])],
            created_at=datetime.fromisoformat(
                result["created_at"].replace("Z", "+00:00")
            ),
            updated_at=datetime.fromisoformat(
                result["updated_at"].replace("Z", "+00:00")
            )
        )

    # -------------------------------------------------------------------------
    # Pull Request Operations
    # -------------------------------------------------------------------------

    async def list_prs(
        self,
        repo: str,
        owner: Optional[str] = None,
        state: str = "open",
        limit: int = 30
    ) -> List[GitHubPR]:
        """List pull requests for a repository."""
        owner = owner or self._default_owner
        result = await self._make_request(
            "GET",
            f"/repos/{owner}/{repo}/pulls?state={state}"
        )

        if not result:
            return []

        return [
            GitHubPR(
                number=pr["number"],
                title=pr["title"],
                body=pr.get("body"),
                state=pr["state"],
                head_branch=pr["head"]["ref"],
                base_branch=pr["base"]["ref"],
                merged=pr.get("merged", False),
                mergeable=pr.get("mergeable"),
                created_at=datetime.fromisoformat(
                    pr["created_at"].replace("Z", "+00:00")
                )
            )
            for pr in result[:limit]
        ]

    # -------------------------------------------------------------------------
    # File Operations
    # -------------------------------------------------------------------------

    async def get_file_content(
        self,
        repo: str,
        path: str,
        owner: Optional[str] = None,
        ref: Optional[str] = None
    ) -> Optional[str]:
        """Get file content from repository."""
        owner = owner or self._default_owner
        url = f"/repos/{owner}/{repo}/contents/{path}"
        if ref:
            url += f"?ref={ref}"

        result = await self._make_request("GET", url)

        if not result or result.get("type") != "file":
            return None

        import base64
        content = result.get("content", "")
        return base64.b64decode(content).decode("utf-8")

    async def search_code(
        self,
        query: str,
        repo: Optional[str] = None,
        owner: Optional[str] = None,
        limit: int = 30
    ) -> List[Dict[str, Any]]:
        """Search for code."""
        owner = owner or self._default_owner

        search_query = query
        if repo and owner:
            search_query += f" repo:{owner}/{repo}"

        import urllib.parse
        encoded_query = urllib.parse.quote(search_query)

        result = await self._make_request(
            "GET",
            f"/search/code?q={encoded_query}"
        )

        if not result:
            return []

        return result.get("items", [])[:limit]


# Register the integration
from integrations import registry

registry.register_provider("github", GitHubIntegration)

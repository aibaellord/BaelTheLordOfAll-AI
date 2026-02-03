"""
BAEL - The Lord of All AI Agents
Tool System - Extensible Tool Framework

Provides a comprehensive toolkit for agents to interact
with the world: code execution, web search, file operations,
API calls, browser automation, and more.
"""

import asyncio
import json
import logging
import os
import subprocess
import tempfile
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("BAEL.Tools")


class ToolCategory(Enum):
    """Categories of tools."""
    CODE = "code"
    WEB = "web"
    FILE = "file"
    API = "api"
    DATABASE = "database"
    BROWSER = "browser"
    SHELL = "shell"
    AI = "ai"
    COMMUNICATION = "communication"


@dataclass
class ToolResult:
    """Result from a tool execution."""
    success: bool
    output: Any
    error: Optional[str] = None
    execution_time_ms: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolSchema:
    """JSON Schema for tool parameters."""
    name: str
    description: str
    parameters: Dict[str, Any]
    required: List[str] = field(default_factory=list)


class BaseTool(ABC):
    """Base class for all BAEL tools."""

    name: str = "base_tool"
    description: str = "Base tool description"
    category: ToolCategory = ToolCategory.CODE

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.execution_count = 0
        self.last_executed = None

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool with given parameters."""
        pass

    @abstractmethod
    def get_schema(self) -> ToolSchema:
        """Get the JSON schema for this tool."""
        pass

    def to_function(self) -> Dict[str, Any]:
        """Convert to OpenAI function calling format."""
        schema = self.get_schema()
        return {
            "type": "function",
            "function": {
                "name": schema.name,
                "description": schema.description,
                "parameters": {
                    "type": "object",
                    "properties": schema.parameters,
                    "required": schema.required
                }
            }
        }

    async def close(self):
        """Cleanup resources."""
        pass


# =============================================================================
# CODE EXECUTION TOOLS
# =============================================================================

class PythonExecutor(BaseTool):
    """Execute Python code safely."""

    name = "python_executor"
    description = "Execute Python code and return the result"
    category = ToolCategory.CODE

    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self.timeout = config.get('timeout', 30) if config else 30
        self.allowed_imports = config.get('allowed_imports', [
            'math', 'json', 'datetime', 'collections', 'itertools',
            'functools', 're', 'random', 'string', 'typing'
        ]) if config else []

    async def execute(self, code: str, **kwargs) -> ToolResult:
        """Execute Python code."""
        start_time = datetime.now()

        try:
            # Create temp file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(code)
                temp_path = f.name

            # Execute with timeout
            process = await asyncio.create_subprocess_exec(
                'python', temp_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Execution timed out after {self.timeout} seconds"
                )

            # Clean up
            os.unlink(temp_path)

            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)

            if process.returncode == 0:
                return ToolResult(
                    success=True,
                    output=stdout.decode('utf-8'),
                    execution_time_ms=execution_time
                )
            else:
                return ToolResult(
                    success=False,
                    output=stdout.decode('utf-8'),
                    error=stderr.decode('utf-8'),
                    execution_time_ms=execution_time
                )

        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=str(e)
            )

    def get_schema(self) -> ToolSchema:
        return ToolSchema(
            name=self.name,
            description=self.description,
            parameters={
                "code": {
                    "type": "string",
                    "description": "Python code to execute"
                }
            },
            required=["code"]
        )


class ShellExecutor(BaseTool):
    """Execute shell commands."""

    name = "shell_executor"
    description = "Execute shell commands and return output"
    category = ToolCategory.SHELL

    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self.timeout = config.get('timeout', 60) if config else 60
        self.working_dir = config.get('working_dir', '.') if config else '.'
        self.blocked_commands = config.get('blocked_commands', [
            'rm -rf /', 'mkfs', 'dd if=/dev/zero',
            ':(){:|:&};:', 'chmod -R 777 /'
        ]) if config else []

    async def execute(self, command: str, **kwargs) -> ToolResult:
        """Execute shell command."""
        start_time = datetime.now()

        # Safety check
        for blocked in self.blocked_commands:
            if blocked in command:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Blocked command pattern detected: {blocked}"
                )

        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.working_dir
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Command timed out after {self.timeout} seconds"
                )

            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)

            return ToolResult(
                success=process.returncode == 0,
                output=stdout.decode('utf-8'),
                error=stderr.decode('utf-8') if process.returncode != 0 else None,
                execution_time_ms=execution_time
            )

        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=str(e)
            )

    def get_schema(self) -> ToolSchema:
        return ToolSchema(
            name=self.name,
            description=self.description,
            parameters={
                "command": {
                    "type": "string",
                    "description": "Shell command to execute"
                }
            },
            required=["command"]
        )


# =============================================================================
# WEB TOOLS
# =============================================================================

class WebSearchTool(BaseTool):
    """Search the web using various providers."""

    name = "web_search"
    description = "Search the web for information"
    category = ToolCategory.WEB

    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self.provider = config.get('provider', 'duckduckgo') if config else 'duckduckgo'
        self.max_results = config.get('max_results', 10) if config else 10

    async def execute(self, query: str, **kwargs) -> ToolResult:
        """Execute web search."""
        try:
            if self.provider == 'duckduckgo':
                return await self._search_duckduckgo(query)
            else:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Unknown search provider: {self.provider}"
                )
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=str(e)
            )

    async def _search_duckduckgo(self, query: str) -> ToolResult:
        """Search using DuckDuckGo."""
        try:
            from duckduckgo_search import DDGS

            results = []
            with DDGS() as ddgs:
                for r in ddgs.text(query, max_results=self.max_results):
                    results.append({
                        'title': r.get('title', ''),
                        'url': r.get('href', ''),
                        'snippet': r.get('body', '')
                    })

            return ToolResult(
                success=True,
                output=results
            )
        except ImportError:
            return ToolResult(
                success=False,
                output="",
                error="duckduckgo_search not installed"
            )

    def get_schema(self) -> ToolSchema:
        return ToolSchema(
            name=self.name,
            description=self.description,
            parameters={
                "query": {
                    "type": "string",
                    "description": "Search query"
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results",
                    "default": 10
                }
            },
            required=["query"]
        )


class WebFetchTool(BaseTool):
    """Fetch content from URLs."""

    name = "web_fetch"
    description = "Fetch and extract content from a URL"
    category = ToolCategory.WEB

    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self.timeout = config.get('timeout', 30) if config else 30

    async def execute(self, url: str, **kwargs) -> ToolResult:
        """Fetch URL content."""
        try:
            import aiohttp
            from bs4 import BeautifulSoup

            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=self.timeout) as response:
                    if response.status != 200:
                        return ToolResult(
                            success=False,
                            output="",
                            error=f"HTTP {response.status}"
                        )

                    html = await response.text()

            # Parse and extract text
            soup = BeautifulSoup(html, 'html.parser')

            # Remove script and style elements
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.decompose()

            # Get text
            text = soup.get_text(separator='\n', strip=True)

            # Limit length
            if len(text) > 50000:
                text = text[:50000] + "...[truncated]"

            return ToolResult(
                success=True,
                output=text,
                metadata={'url': url, 'length': len(text)}
            )

        except ImportError:
            return ToolResult(
                success=False,
                output="",
                error="aiohttp or beautifulsoup4 not installed"
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=str(e)
            )

    def get_schema(self) -> ToolSchema:
        return ToolSchema(
            name=self.name,
            description=self.description,
            parameters={
                "url": {
                    "type": "string",
                    "description": "URL to fetch"
                }
            },
            required=["url"]
        )


# =============================================================================
# FILE SYSTEM TOOLS
# =============================================================================

class FileReadTool(BaseTool):
    """Read files from the file system."""

    name = "file_read"
    description = "Read content from a file"
    category = ToolCategory.FILE

    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self.allowed_paths = config.get('allowed_paths', ['.']) if config else ['.']
        self.max_size = config.get('max_size', 10 * 1024 * 1024) if config else 10 * 1024 * 1024

    async def execute(self, path: str, **kwargs) -> ToolResult:
        """Read file content."""
        try:
            file_path = Path(path)

            # Check if file exists
            if not file_path.exists():
                return ToolResult(
                    success=False,
                    output="",
                    error=f"File not found: {path}"
                )

            # Check file size
            if file_path.stat().st_size > self.max_size:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"File too large (max {self.max_size} bytes)"
                )

            # Read file
            content = file_path.read_text(encoding='utf-8', errors='replace')

            return ToolResult(
                success=True,
                output=content,
                metadata={
                    'path': str(file_path.absolute()),
                    'size': len(content)
                }
            )

        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=str(e)
            )

    def get_schema(self) -> ToolSchema:
        return ToolSchema(
            name=self.name,
            description=self.description,
            parameters={
                "path": {
                    "type": "string",
                    "description": "Path to the file"
                }
            },
            required=["path"]
        )


class FileWriteTool(BaseTool):
    """Write files to the file system."""

    name = "file_write"
    description = "Write content to a file"
    category = ToolCategory.FILE

    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self.allowed_paths = config.get('allowed_paths', ['.']) if config else ['.']

    async def execute(self, path: str, content: str, **kwargs) -> ToolResult:
        """Write file content."""
        try:
            file_path = Path(path)

            # Create parent directories if needed
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Write file
            file_path.write_text(content, encoding='utf-8')

            return ToolResult(
                success=True,
                output=f"Successfully wrote {len(content)} bytes to {path}",
                metadata={
                    'path': str(file_path.absolute()),
                    'size': len(content)
                }
            )

        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=str(e)
            )

    def get_schema(self) -> ToolSchema:
        return ToolSchema(
            name=self.name,
            description=self.description,
            parameters={
                "path": {
                    "type": "string",
                    "description": "Path to the file"
                },
                "content": {
                    "type": "string",
                    "description": "Content to write"
                }
            },
            required=["path", "content"]
        )


class FileListTool(BaseTool):
    """List files in a directory."""

    name = "file_list"
    description = "List files and directories in a path"
    category = ToolCategory.FILE

    async def execute(self, path: str = ".", **kwargs) -> ToolResult:
        """List directory contents."""
        try:
            dir_path = Path(path)

            if not dir_path.exists():
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Path not found: {path}"
                )

            if not dir_path.is_dir():
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Not a directory: {path}"
                )

            entries = []
            for entry in dir_path.iterdir():
                entries.append({
                    'name': entry.name,
                    'type': 'directory' if entry.is_dir() else 'file',
                    'size': entry.stat().st_size if entry.is_file() else 0
                })

            return ToolResult(
                success=True,
                output=entries,
                metadata={'path': str(dir_path.absolute()), 'count': len(entries)}
            )

        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=str(e)
            )

    def get_schema(self) -> ToolSchema:
        return ToolSchema(
            name=self.name,
            description=self.description,
            parameters={
                "path": {
                    "type": "string",
                    "description": "Directory path",
                    "default": "."
                }
            },
            required=[]
        )


# =============================================================================
# GITHUB TOOLS
# =============================================================================

class GitHubTool(BaseTool):
    """Interact with GitHub repositories."""

    name = "github"
    description = "Interact with GitHub repositories"
    category = ToolCategory.WEB

    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self.token = config.get('token') or os.environ.get('GITHUB_TOKEN') if config else os.environ.get('GITHUB_TOKEN')

    async def execute(self, action: str, **kwargs) -> ToolResult:
        """Execute GitHub action."""
        actions = {
            'search_repos': self._search_repos,
            'get_repo': self._get_repo,
            'search_code': self._search_code,
            'get_readme': self._get_readme,
            'list_issues': self._list_issues
        }

        if action not in actions:
            return ToolResult(
                success=False,
                output="",
                error=f"Unknown action: {action}. Available: {list(actions.keys())}"
            )

        return await actions[action](**kwargs)

    async def _search_repos(self, query: str, **kwargs) -> ToolResult:
        """Search GitHub repositories."""
        try:
            import aiohttp

            headers = {'Accept': 'application/vnd.github.v3+json'}
            if self.token:
                headers['Authorization'] = f'token {self.token}'

            async with aiohttp.ClientSession() as session:
                url = f"https://api.github.com/search/repositories?q={query}&per_page=10"
                async with session.get(url, headers=headers) as response:
                    if response.status != 200:
                        return ToolResult(
                            success=False,
                            output="",
                            error=f"GitHub API error: {response.status}"
                        )
                    data = await response.json()

            repos = [
                {
                    'name': r['full_name'],
                    'description': r['description'],
                    'stars': r['stargazers_count'],
                    'url': r['html_url'],
                    'language': r['language']
                }
                for r in data.get('items', [])
            ]

            return ToolResult(success=True, output=repos)

        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))

    async def _get_repo(self, repo: str, **kwargs) -> ToolResult:
        """Get repository details."""
        try:
            import aiohttp

            headers = {'Accept': 'application/vnd.github.v3+json'}
            if self.token:
                headers['Authorization'] = f'token {self.token}'

            async with aiohttp.ClientSession() as session:
                async with session.get(f"https://api.github.com/repos/{repo}", headers=headers) as response:
                    if response.status != 200:
                        return ToolResult(success=False, output="", error=f"GitHub API error: {response.status}")
                    data = await response.json()

            return ToolResult(success=True, output=data)

        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))

    async def _search_code(self, query: str, **kwargs) -> ToolResult:
        """Search code on GitHub."""
        try:
            import aiohttp

            headers = {'Accept': 'application/vnd.github.v3+json'}
            if self.token:
                headers['Authorization'] = f'token {self.token}'

            async with aiohttp.ClientSession() as session:
                url = f"https://api.github.com/search/code?q={query}&per_page=10"
                async with session.get(url, headers=headers) as response:
                    if response.status != 200:
                        return ToolResult(success=False, output="", error=f"GitHub API error: {response.status}")
                    data = await response.json()

            results = [
                {
                    'path': item['path'],
                    'repo': item['repository']['full_name'],
                    'url': item['html_url']
                }
                for item in data.get('items', [])
            ]

            return ToolResult(success=True, output=results)

        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))

    async def _get_readme(self, repo: str, **kwargs) -> ToolResult:
        """Get repository README."""
        try:
            import base64

            import aiohttp

            headers = {'Accept': 'application/vnd.github.v3+json'}
            if self.token:
                headers['Authorization'] = f'token {self.token}'

            async with aiohttp.ClientSession() as session:
                async with session.get(f"https://api.github.com/repos/{repo}/readme", headers=headers) as response:
                    if response.status != 200:
                        return ToolResult(success=False, output="", error=f"GitHub API error: {response.status}")
                    data = await response.json()

            content = base64.b64decode(data['content']).decode('utf-8')

            return ToolResult(success=True, output=content)

        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))

    async def _list_issues(self, repo: str, **kwargs) -> ToolResult:
        """List repository issues."""
        try:
            import aiohttp

            headers = {'Accept': 'application/vnd.github.v3+json'}
            if self.token:
                headers['Authorization'] = f'token {self.token}'

            async with aiohttp.ClientSession() as session:
                async with session.get(f"https://api.github.com/repos/{repo}/issues?per_page=20", headers=headers) as response:
                    if response.status != 200:
                        return ToolResult(success=False, output="", error=f"GitHub API error: {response.status}")
                    data = await response.json()

            issues = [
                {
                    'number': issue['number'],
                    'title': issue['title'],
                    'state': issue['state'],
                    'labels': [l['name'] for l in issue['labels']],
                    'url': issue['html_url']
                }
                for issue in data
            ]

            return ToolResult(success=True, output=issues)

        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))

    def get_schema(self) -> ToolSchema:
        return ToolSchema(
            name=self.name,
            description=self.description,
            parameters={
                "action": {
                    "type": "string",
                    "description": "Action to perform",
                    "enum": ["search_repos", "get_repo", "search_code", "get_readme", "list_issues"]
                },
                "query": {
                    "type": "string",
                    "description": "Search query (for search actions)"
                },
                "repo": {
                    "type": "string",
                    "description": "Repository in owner/repo format"
                }
            },
            required=["action"]
        )


# =============================================================================
# TOOL LOADER
# =============================================================================

class ToolLoader:
    """Loads and manages tools."""

    # Registry of all built-in tools
    BUILTIN_TOOLS = {
        'python_executor': PythonExecutor,
        'shell_executor': ShellExecutor,
        'web_search': WebSearchTool,
        'web_fetch': WebFetchTool,
        'file_read': FileReadTool,
        'file_write': FileWriteTool,
        'file_list': FileListTool,
        'github': GitHubTool,
    }

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

    async def load_all(self) -> Dict[str, BaseTool]:
        """Load all enabled tools."""
        tools = {}

        enabled = self.config.get('enabled', list(self.BUILTIN_TOOLS.keys()))

        for tool_id in enabled:
            if tool_id in self.BUILTIN_TOOLS:
                tool_config = self.config.get(tool_id, {})
                tool = self.BUILTIN_TOOLS[tool_id](tool_config)
                tools[tool_id] = tool
                logger.info(f"🔧 Loaded tool: {tool.name}")

        return tools

    async def load_tool(self, tool_id: str) -> Optional[BaseTool]:
        """Load a specific tool."""
        if tool_id in self.BUILTIN_TOOLS:
            tool_config = self.config.get(tool_id, {})
            return self.BUILTIN_TOOLS[tool_id](tool_config)
        return None


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    'BaseTool',
    'ToolResult',
    'ToolSchema',
    'ToolCategory',
    'ToolLoader',
    'PythonExecutor',
    'ShellExecutor',
    'WebSearchTool',
    'WebFetchTool',
    'FileReadTool',
    'FileWriteTool',
    'FileListTool',
    'GitHubTool'
]

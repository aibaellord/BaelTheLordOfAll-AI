"""
BAEL Cross-Repository Search
=============================

Search across multiple repositories and projects.
Enables finding code and patterns across codebases.

Features:
- Multi-repository indexing
- Semantic code search
- Pattern matching
- Similarity detection
- Cross-reference tracking
"""

import asyncio
import hashlib
import logging
import os
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class SearchType(Enum):
    """Search types."""
    TEXT = "text"
    REGEX = "regex"
    SEMANTIC = "semantic"
    SYMBOL = "symbol"
    FILE = "file"


class IndexStatus(Enum):
    """Index status."""
    PENDING = "pending"
    INDEXING = "indexing"
    READY = "ready"
    ERROR = "error"
    OUTDATED = "outdated"


@dataclass
class RepoInfo:
    """Repository information."""
    id: str
    name: str
    path: str

    # Git info
    remote_url: str = ""
    branch: str = "main"

    # Stats
    file_count: int = 0
    total_lines: int = 0

    # Status
    status: IndexStatus = IndexStatus.PENDING
    last_indexed: Optional[datetime] = None


@dataclass
class FileIndex:
    """Index entry for a file."""
    path: str
    repo_id: str

    # Content hash
    content_hash: str = ""

    # Extracted info
    symbols: List[str] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)

    # Lines
    lines: int = 0

    # Indexed at
    indexed_at: datetime = field(default_factory=datetime.now)


@dataclass
class RepoIndex:
    """Repository index."""
    repo_id: str

    # File indices
    files: Dict[str, FileIndex] = field(default_factory=dict)

    # Symbol index
    symbols: Dict[str, List[str]] = field(default_factory=lambda: defaultdict(list))

    # Import index
    imports: Dict[str, List[str]] = field(default_factory=lambda: defaultdict(list))

    # Text index (trigrams)
    trigrams: Dict[str, Set[str]] = field(default_factory=lambda: defaultdict(set))

    # Stats
    indexed_at: datetime = field(default_factory=datetime.now)


@dataclass
class SearchResult:
    """A search result."""
    file_path: str
    repo_id: str
    repo_name: str

    # Match info
    line_number: int = 0
    match_text: str = ""
    context: str = ""

    # Scoring
    score: float = 0.0

    # Type
    match_type: str = ""


@dataclass
class SearchConfig:
    """Search configuration."""
    # Search options
    case_sensitive: bool = False
    whole_word: bool = False
    max_results: int = 100

    # Scope
    include_patterns: List[str] = field(default_factory=list)
    exclude_patterns: List[str] = field(default_factory=lambda: [
        "*.pyc", "*.min.js", "node_modules/*", ".git/*"
    ])

    # Context
    context_lines: int = 2


class CrossRepoSearch:
    """
    Cross-repository search system for BAEL.
    """

    def __init__(
        self,
        config: Optional[SearchConfig] = None,
    ):
        self.config = config or SearchConfig()

        # Repositories
        self.repos: Dict[str, RepoInfo] = {}

        # Indices
        self.indices: Dict[str, RepoIndex] = {}

        # Cache
        self._search_cache: Dict[str, List[SearchResult]] = {}

        # Stats
        self.stats = {
            "repos_indexed": 0,
            "files_indexed": 0,
            "searches_performed": 0,
            "cache_hits": 0,
        }

    async def add_repository(
        self,
        path: str,
        name: Optional[str] = None,
    ) -> RepoInfo:
        """
        Add a repository to search.

        Args:
            path: Path to repository
            name: Optional repository name

        Returns:
            RepoInfo
        """
        repo_path = Path(path)
        if not repo_path.exists():
            raise ValueError(f"Repository path does not exist: {path}")

        repo_id = hashlib.md5(str(repo_path.resolve()).encode()).hexdigest()[:12]

        # Check for git remote
        remote_url = ""
        branch = "main"
        git_dir = repo_path / ".git"
        if git_dir.exists():
            config_file = git_dir / "config"
            if config_file.exists():
                try:
                    content = config_file.read_text()
                    import re
                    url_match = re.search(r"url\s*=\s*(.+)", content)
                    if url_match:
                        remote_url = url_match.group(1).strip()
                except Exception:
                    pass

        repo = RepoInfo(
            id=repo_id,
            name=name or repo_path.name,
            path=str(repo_path.resolve()),
            remote_url=remote_url,
            branch=branch,
        )

        self.repos[repo_id] = repo

        logger.info(f"Added repository: {repo.name} ({repo_id})")

        return repo

    async def index_repository(
        self,
        repo_id: str,
    ) -> RepoIndex:
        """
        Index a repository for searching.

        Args:
            repo_id: Repository ID

        Returns:
            RepoIndex
        """
        repo = self.repos.get(repo_id)
        if not repo:
            raise ValueError(f"Repository not found: {repo_id}")

        repo.status = IndexStatus.INDEXING

        index = RepoIndex(repo_id=repo_id)
        repo_path = Path(repo.path)

        # Scan files
        file_count = 0
        total_lines = 0

        for file_path in repo_path.rglob("*"):
            if not file_path.is_file():
                continue

            # Check exclusions
            if self._is_excluded(file_path, repo_path):
                continue

            # Index file
            try:
                file_index = await self._index_file(file_path, repo_id)
                if file_index:
                    rel_path = str(file_path.relative_to(repo_path))
                    index.files[rel_path] = file_index

                    # Add to symbol index
                    for symbol in file_index.symbols:
                        index.symbols[symbol].append(rel_path)

                    # Add to import index
                    for imp in file_index.imports:
                        index.imports[imp].append(rel_path)

                    # Add trigrams for text search
                    self._add_trigrams(file_path, index.trigrams, rel_path)

                    file_count += 1
                    total_lines += file_index.lines
            except Exception as e:
                logger.debug(f"Error indexing {file_path}: {e}")

        # Update repo info
        repo.file_count = file_count
        repo.total_lines = total_lines
        repo.status = IndexStatus.READY
        repo.last_indexed = datetime.now()

        # Store index
        self.indices[repo_id] = index

        self.stats["repos_indexed"] += 1
        self.stats["files_indexed"] += file_count

        logger.info(f"Indexed repository: {repo.name} ({file_count} files)")

        return index

    def _is_excluded(self, path: Path, root: Path) -> bool:
        """Check if path should be excluded."""
        try:
            rel_path = str(path.relative_to(root))
        except ValueError:
            return True

        for pattern in self.config.exclude_patterns:
            if pattern.startswith("*"):
                if rel_path.endswith(pattern[1:]):
                    return True
            elif "*" in pattern:
                import fnmatch
                if fnmatch.fnmatch(rel_path, pattern):
                    return True
            elif pattern in rel_path:
                return True

        return False

    async def _index_file(
        self,
        path: Path,
        repo_id: str,
    ) -> Optional[FileIndex]:
        """Index a single file."""
        try:
            content = path.read_text(errors="ignore")
            lines = content.split("\n")

            # Calculate hash
            content_hash = hashlib.md5(content.encode()).hexdigest()

            # Extract symbols
            symbols = self._extract_symbols(content, path.suffix)

            # Extract imports
            imports = self._extract_imports(content, path.suffix)

            return FileIndex(
                path=str(path),
                repo_id=repo_id,
                content_hash=content_hash,
                symbols=symbols,
                imports=imports,
                lines=len(lines),
            )
        except Exception:
            return None

    def _extract_symbols(self, content: str, ext: str) -> List[str]:
        """Extract symbols from file."""
        symbols = []

        if ext == ".py":
            # Classes
            symbols.extend(re.findall(r"class\s+(\w+)", content))
            # Functions
            symbols.extend(re.findall(r"def\s+(\w+)", content))
        elif ext in (".js", ".ts"):
            # Functions
            symbols.extend(re.findall(r"function\s+(\w+)", content))
            # Classes
            symbols.extend(re.findall(r"class\s+(\w+)", content))
            # Arrow functions
            symbols.extend(re.findall(r"const\s+(\w+)\s*=.*=>", content))

        return symbols

    def _extract_imports(self, content: str, ext: str) -> List[str]:
        """Extract imports from file."""
        imports = []

        if ext == ".py":
            imports.extend(re.findall(r"^import\s+(\S+)", content, re.MULTILINE))
            imports.extend(re.findall(r"^from\s+(\S+)", content, re.MULTILINE))
        elif ext in (".js", ".ts"):
            imports.extend(re.findall(r"import.*from\s+['\"]([^'\"]+)", content))
            imports.extend(re.findall(r"require\s*\(['\"]([^'\"]+)", content))

        return imports

    def _add_trigrams(
        self,
        path: Path,
        trigrams: Dict[str, Set[str]],
        rel_path: str,
    ) -> None:
        """Add trigrams for text search."""
        try:
            content = path.read_text(errors="ignore").lower()

            for i in range(len(content) - 2):
                trigram = content[i:i+3]
                if trigram.strip():
                    trigrams[trigram].add(rel_path)
        except Exception:
            pass

    async def search(
        self,
        query: str,
        search_type: SearchType = SearchType.TEXT,
        repo_ids: Optional[List[str]] = None,
    ) -> List[SearchResult]:
        """
        Search across repositories.

        Args:
            query: Search query
            search_type: Type of search
            repo_ids: Optional list of repo IDs to search

        Returns:
            List of search results
        """
        self.stats["searches_performed"] += 1

        # Check cache
        cache_key = f"{query}:{search_type.value}:{repo_ids}"
        if cache_key in self._search_cache:
            self.stats["cache_hits"] += 1
            return self._search_cache[cache_key]

        results = []
        repos_to_search = (
            [repo_ids] if isinstance(repo_ids, str) else repo_ids
        ) or list(self.repos.keys())

        for repo_id in repos_to_search:
            index = self.indices.get(repo_id)
            if not index:
                continue

            repo = self.repos[repo_id]

            if search_type == SearchType.TEXT:
                results.extend(await self._search_text(query, repo, index))
            elif search_type == SearchType.REGEX:
                results.extend(await self._search_regex(query, repo, index))
            elif search_type == SearchType.SYMBOL:
                results.extend(self._search_symbols(query, repo, index))
            elif search_type == SearchType.FILE:
                results.extend(self._search_files(query, repo, index))

        # Sort by score
        results.sort(key=lambda r: r.score, reverse=True)

        # Limit results
        results = results[:self.config.max_results]

        # Cache
        self._search_cache[cache_key] = results

        return results

    async def _search_text(
        self,
        query: str,
        repo: RepoInfo,
        index: RepoIndex,
    ) -> List[SearchResult]:
        """Text search."""
        results = []
        query_lower = query.lower() if not self.config.case_sensitive else query

        # Use trigrams to narrow down candidates
        query_trigrams = {query_lower[i:i+3] for i in range(len(query_lower) - 2)}
        candidate_files = set()

        for trigram in query_trigrams:
            if trigram in index.trigrams:
                candidate_files.update(index.trigrams[trigram])

        if not candidate_files:
            candidate_files = set(index.files.keys())

        # Search candidates
        repo_path = Path(repo.path)

        for rel_path in list(candidate_files)[:100]:  # Limit for performance
            full_path = repo_path / rel_path
            if not full_path.exists():
                continue

            try:
                content = full_path.read_text(errors="ignore")
                lines = content.split("\n")

                search_content = content if self.config.case_sensitive else content.lower()

                for i, line in enumerate(lines):
                    search_line = line if self.config.case_sensitive else line.lower()

                    if query_lower in search_line:
                        # Get context
                        start = max(0, i - self.config.context_lines)
                        end = min(len(lines), i + self.config.context_lines + 1)
                        context = "\n".join(lines[start:end])

                        results.append(SearchResult(
                            file_path=rel_path,
                            repo_id=repo.id,
                            repo_name=repo.name,
                            line_number=i + 1,
                            match_text=line.strip(),
                            context=context,
                            score=1.0,
                            match_type="text",
                        ))
            except Exception:
                continue

        return results

    async def _search_regex(
        self,
        pattern: str,
        repo: RepoInfo,
        index: RepoIndex,
    ) -> List[SearchResult]:
        """Regex search."""
        results = []

        try:
            regex = re.compile(
                pattern,
                0 if self.config.case_sensitive else re.IGNORECASE
            )
        except re.error:
            return results

        repo_path = Path(repo.path)

        for rel_path in list(index.files.keys())[:100]:
            full_path = repo_path / rel_path
            if not full_path.exists():
                continue

            try:
                content = full_path.read_text(errors="ignore")
                lines = content.split("\n")

                for i, line in enumerate(lines):
                    match = regex.search(line)
                    if match:
                        start = max(0, i - self.config.context_lines)
                        end = min(len(lines), i + self.config.context_lines + 1)
                        context = "\n".join(lines[start:end])

                        results.append(SearchResult(
                            file_path=rel_path,
                            repo_id=repo.id,
                            repo_name=repo.name,
                            line_number=i + 1,
                            match_text=match.group(),
                            context=context,
                            score=1.0,
                            match_type="regex",
                        ))
            except Exception:
                continue

        return results

    def _search_symbols(
        self,
        query: str,
        repo: RepoInfo,
        index: RepoIndex,
    ) -> List[SearchResult]:
        """Symbol search."""
        results = []
        query_lower = query.lower()

        for symbol, files in index.symbols.items():
            if query_lower in symbol.lower():
                score = 1.0 if symbol.lower() == query_lower else 0.8

                for file_path in files:
                    results.append(SearchResult(
                        file_path=file_path,
                        repo_id=repo.id,
                        repo_name=repo.name,
                        match_text=symbol,
                        score=score,
                        match_type="symbol",
                    ))

        return results

    def _search_files(
        self,
        query: str,
        repo: RepoInfo,
        index: RepoIndex,
    ) -> List[SearchResult]:
        """File path search."""
        results = []
        query_lower = query.lower()

        for file_path in index.files.keys():
            if query_lower in file_path.lower():
                score = 1.0 if file_path.lower().endswith(query_lower) else 0.5

                results.append(SearchResult(
                    file_path=file_path,
                    repo_id=repo.id,
                    repo_name=repo.name,
                    match_text=file_path,
                    score=score,
                    match_type="file",
                ))

        return results

    async def find_similar(
        self,
        file_path: str,
        repo_id: str,
        threshold: float = 0.7,
    ) -> List[Tuple[str, str, float]]:
        """
        Find similar files across repos.

        Returns:
            List of (repo_id, file_path, similarity) tuples
        """
        source_index = self.indices.get(repo_id)
        if not source_index:
            return []

        source_file = source_index.files.get(file_path)
        if not source_file:
            return []

        similar = []
        source_symbols = set(source_file.symbols)

        for other_repo_id, other_index in self.indices.items():
            for other_path, other_file in other_index.files.items():
                if other_repo_id == repo_id and other_path == file_path:
                    continue

                other_symbols = set(other_file.symbols)

                # Jaccard similarity
                if source_symbols and other_symbols:
                    intersection = len(source_symbols & other_symbols)
                    union = len(source_symbols | other_symbols)
                    similarity = intersection / union if union > 0 else 0

                    if similarity >= threshold:
                        similar.append((other_repo_id, other_path, similarity))

        similar.sort(key=lambda x: x[2], reverse=True)

        return similar[:20]

    def get_stats(self) -> Dict[str, Any]:
        """Get search statistics."""
        return {
            **self.stats,
            "total_repos": len(self.repos),
            "cache_size": len(self._search_cache),
        }


def demo():
    """Demonstrate cross-repo search."""
    import asyncio

    print("=" * 60)
    print("BAEL Cross-Repository Search Demo")
    print("=" * 60)

    search = CrossRepoSearch()

    async def run():
        # Add and index current directory
        import os
        current_dir = os.path.dirname(os.path.abspath(__file__))

        try:
            repo = await search.add_repository(current_dir, "intelligence")
            print(f"\nAdded repository: {repo.name}")

            index = await search.index_repository(repo.id)
            print(f"Indexed {len(index.files)} files")
            print(f"Found {len(index.symbols)} unique symbols")

            # Search for text
            results = await search.search("class", SearchType.TEXT)
            print(f"\nText search 'class': {len(results)} results")
            for result in results[:3]:
                print(f"  - {result.file_path}:{result.line_number}")

            # Search for symbols
            results = await search.search("Analyzer", SearchType.SYMBOL)
            print(f"\nSymbol search 'Analyzer': {len(results)} results")
            for result in results[:3]:
                print(f"  - {result.repo_name}/{result.file_path}: {result.match_text}")

        except Exception as e:
            print(f"Demo error: {e}")

    asyncio.run(run())

    print(f"\nStats: {search.get_stats()}")


if __name__ == "__main__":
    demo()

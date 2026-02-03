"""
BAEL File Tools - Comprehensive File Operations Toolkit
Provides file reading, writing, watching, searching, and conversion.
"""

import asyncio
import fnmatch
import hashlib
import json
import logging
import mimetypes
import os
import re
import shutil
import stat
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import (Any, Callable, Dict, Generator, List, Optional, Set, Tuple,
                    Union)

logger = logging.getLogger("BAEL.Tools.File")


# =============================================================================
# DATA CLASSES & ENUMS
# =============================================================================

class FileType(Enum):
    """File type categories."""
    TEXT = "text"
    BINARY = "binary"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    DOCUMENT = "document"
    ARCHIVE = "archive"
    CODE = "code"
    DATA = "data"
    UNKNOWN = "unknown"


class WatchEventType(Enum):
    """File watch event types."""
    CREATED = "created"
    MODIFIED = "modified"
    DELETED = "deleted"
    MOVED = "moved"


@dataclass
class FileInfo:
    """Information about a file."""
    path: Path
    name: str
    extension: str
    size_bytes: int
    file_type: FileType
    mime_type: Optional[str] = None
    created_at: Optional[datetime] = None
    modified_at: Optional[datetime] = None
    accessed_at: Optional[datetime] = None
    is_directory: bool = False
    is_symlink: bool = False
    permissions: str = ""
    owner: Optional[str] = None
    checksum: Optional[str] = None
    encoding: Optional[str] = None
    line_count: Optional[int] = None

    @property
    def size_human(self) -> str:
        """Human-readable file size."""
        size = self.size_bytes
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} PB"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": str(self.path),
            "name": self.name,
            "extension": self.extension,
            "size": self.size_bytes,
            "size_human": self.size_human,
            "type": self.file_type.value,
            "mime_type": self.mime_type,
            "modified": self.modified_at.isoformat() if self.modified_at else None,
            "is_directory": self.is_directory,
            "line_count": self.line_count
        }


@dataclass
class SearchResult:
    """File search result."""
    path: Path
    matches: List[Dict[str, Any]] = field(default_factory=list)
    line_numbers: List[int] = field(default_factory=list)
    context: List[str] = field(default_factory=list)

    @property
    def match_count(self) -> int:
        return len(self.matches)


@dataclass
class WatchEvent:
    """File watch event."""
    event_type: WatchEventType
    path: Path
    timestamp: datetime = field(default_factory=datetime.now)
    old_path: Optional[Path] = None  # For move events


# =============================================================================
# FILE TYPE DETECTION
# =============================================================================

class FileTypeDetector:
    """Detect file types and encodings."""

    # Extension to file type mappings
    TYPE_MAP = {
        # Code
        ".py": FileType.CODE,
        ".js": FileType.CODE,
        ".ts": FileType.CODE,
        ".java": FileType.CODE,
        ".cpp": FileType.CODE,
        ".c": FileType.CODE,
        ".h": FileType.CODE,
        ".rs": FileType.CODE,
        ".go": FileType.CODE,
        ".rb": FileType.CODE,
        ".php": FileType.CODE,
        ".swift": FileType.CODE,
        ".kt": FileType.CODE,
        ".scala": FileType.CODE,
        ".cs": FileType.CODE,
        ".r": FileType.CODE,
        ".lua": FileType.CODE,
        ".sh": FileType.CODE,
        ".bash": FileType.CODE,
        ".zsh": FileType.CODE,
        ".sql": FileType.CODE,

        # Data
        ".json": FileType.DATA,
        ".yaml": FileType.DATA,
        ".yml": FileType.DATA,
        ".xml": FileType.DATA,
        ".csv": FileType.DATA,
        ".tsv": FileType.DATA,
        ".toml": FileType.DATA,
        ".ini": FileType.DATA,
        ".env": FileType.DATA,

        # Documents
        ".pdf": FileType.DOCUMENT,
        ".doc": FileType.DOCUMENT,
        ".docx": FileType.DOCUMENT,
        ".xls": FileType.DOCUMENT,
        ".xlsx": FileType.DOCUMENT,
        ".ppt": FileType.DOCUMENT,
        ".pptx": FileType.DOCUMENT,
        ".odt": FileType.DOCUMENT,
        ".rtf": FileType.DOCUMENT,

        # Text
        ".txt": FileType.TEXT,
        ".md": FileType.TEXT,
        ".rst": FileType.TEXT,
        ".log": FileType.TEXT,
        ".html": FileType.TEXT,
        ".htm": FileType.TEXT,
        ".css": FileType.TEXT,

        # Images
        ".jpg": FileType.IMAGE,
        ".jpeg": FileType.IMAGE,
        ".png": FileType.IMAGE,
        ".gif": FileType.IMAGE,
        ".bmp": FileType.IMAGE,
        ".svg": FileType.IMAGE,
        ".webp": FileType.IMAGE,
        ".ico": FileType.IMAGE,
        ".tiff": FileType.IMAGE,

        # Audio
        ".mp3": FileType.AUDIO,
        ".wav": FileType.AUDIO,
        ".flac": FileType.AUDIO,
        ".m4a": FileType.AUDIO,
        ".ogg": FileType.AUDIO,
        ".aac": FileType.AUDIO,

        # Video
        ".mp4": FileType.VIDEO,
        ".mkv": FileType.VIDEO,
        ".avi": FileType.VIDEO,
        ".mov": FileType.VIDEO,
        ".wmv": FileType.VIDEO,
        ".webm": FileType.VIDEO,

        # Archives
        ".zip": FileType.ARCHIVE,
        ".tar": FileType.ARCHIVE,
        ".gz": FileType.ARCHIVE,
        ".bz2": FileType.ARCHIVE,
        ".xz": FileType.ARCHIVE,
        ".7z": FileType.ARCHIVE,
        ".rar": FileType.ARCHIVE,

        # Binary
        ".exe": FileType.BINARY,
        ".dll": FileType.BINARY,
        ".so": FileType.BINARY,
        ".dylib": FileType.BINARY,
        ".bin": FileType.BINARY,
    }

    @classmethod
    def detect(cls, path: Path) -> FileType:
        """Detect file type from extension."""
        ext = path.suffix.lower()
        return cls.TYPE_MAP.get(ext, FileType.UNKNOWN)

    @classmethod
    def is_text_file(cls, path: Path) -> bool:
        """Check if file is likely a text file."""
        file_type = cls.detect(path)
        return file_type in {FileType.TEXT, FileType.CODE, FileType.DATA}

    @classmethod
    def detect_encoding(cls, path: Path) -> str:
        """Detect file encoding."""
        # Simple encoding detection - in production, use chardet
        try:
            with open(path, 'rb') as f:
                raw = f.read(4096)

            # Check for BOM
            if raw.startswith(b'\xef\xbb\xbf'):
                return 'utf-8-sig'
            if raw.startswith(b'\xff\xfe'):
                return 'utf-16-le'
            if raw.startswith(b'\xfe\xff'):
                return 'utf-16-be'

            # Try UTF-8
            try:
                raw.decode('utf-8')
                return 'utf-8'
            except:
                pass

            # Fallback
            return 'utf-8'

        except Exception:
            return 'utf-8'


# =============================================================================
# FILE READER
# =============================================================================

class FileReader:
    """Read files with various formats."""

    def __init__(self, default_encoding: str = "utf-8"):
        self.default_encoding = default_encoding

    def read(self, path: Union[str, Path], encoding: Optional[str] = None) -> str:
        """Read file content as string."""
        path = Path(path)
        enc = encoding or FileTypeDetector.detect_encoding(path)

        try:
            with open(path, 'r', encoding=enc) as f:
                return f.read()
        except UnicodeDecodeError:
            # Fallback to latin-1 which never fails
            with open(path, 'r', encoding='latin-1') as f:
                return f.read()

    def read_bytes(self, path: Union[str, Path]) -> bytes:
        """Read file as bytes."""
        path = Path(path)
        with open(path, 'rb') as f:
            return f.read()

    def read_lines(
        self,
        path: Union[str, Path],
        start: int = 0,
        end: Optional[int] = None,
        encoding: Optional[str] = None
    ) -> List[str]:
        """Read specific lines from file."""
        path = Path(path)
        enc = encoding or FileTypeDetector.detect_encoding(path)

        lines = []
        with open(path, 'r', encoding=enc) as f:
            for i, line in enumerate(f):
                if i < start:
                    continue
                if end is not None and i >= end:
                    break
                lines.append(line.rstrip('\n\r'))

        return lines

    def read_json(self, path: Union[str, Path]) -> Any:
        """Read JSON file."""
        content = self.read(path)
        return json.loads(content)

    def read_yaml(self, path: Union[str, Path]) -> Any:
        """Read YAML file."""
        try:
            import yaml
            content = self.read(path)
            return yaml.safe_load(content)
        except ImportError:
            raise ImportError("PyYAML is required for YAML parsing")

    def read_csv(self, path: Union[str, Path], delimiter: str = ",") -> List[List[str]]:
        """Read CSV file."""
        import csv

        path = Path(path)
        rows = []
        with open(path, 'r', newline='', encoding=self.default_encoding) as f:
            reader = csv.reader(f, delimiter=delimiter)
            rows = list(reader)
        return rows

    def get_info(self, path: Union[str, Path]) -> FileInfo:
        """Get comprehensive file information."""
        path = Path(path)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        stat_info = path.stat()
        file_type = FileTypeDetector.detect(path)

        # Count lines for text files
        line_count = None
        if FileTypeDetector.is_text_file(path) and not path.is_dir():
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    line_count = sum(1 for _ in f)
            except:
                pass

        return FileInfo(
            path=path.absolute(),
            name=path.name,
            extension=path.suffix,
            size_bytes=stat_info.st_size,
            file_type=file_type,
            mime_type=mimetypes.guess_type(str(path))[0],
            created_at=datetime.fromtimestamp(stat_info.st_ctime),
            modified_at=datetime.fromtimestamp(stat_info.st_mtime),
            accessed_at=datetime.fromtimestamp(stat_info.st_atime),
            is_directory=path.is_dir(),
            is_symlink=path.is_symlink(),
            permissions=stat.filemode(stat_info.st_mode),
            encoding=FileTypeDetector.detect_encoding(path) if not path.is_dir() else None,
            line_count=line_count
        )

    def compute_checksum(
        self,
        path: Union[str, Path],
        algorithm: str = "sha256"
    ) -> str:
        """Compute file checksum."""
        path = Path(path)

        hash_func = getattr(hashlib, algorithm)()

        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                hash_func.update(chunk)

        return hash_func.hexdigest()


# =============================================================================
# FILE WRITER
# =============================================================================

class FileWriter:
    """Write files with various formats."""

    def __init__(self, default_encoding: str = "utf-8"):
        self.default_encoding = default_encoding

    def write(
        self,
        path: Union[str, Path],
        content: str,
        encoding: Optional[str] = None,
        create_dirs: bool = True
    ) -> int:
        """Write content to file."""
        path = Path(path)
        enc = encoding or self.default_encoding

        if create_dirs:
            path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, 'w', encoding=enc) as f:
            return f.write(content)

    def write_bytes(
        self,
        path: Union[str, Path],
        content: bytes,
        create_dirs: bool = True
    ) -> int:
        """Write bytes to file."""
        path = Path(path)

        if create_dirs:
            path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, 'wb') as f:
            return f.write(content)

    def write_lines(
        self,
        path: Union[str, Path],
        lines: List[str],
        encoding: Optional[str] = None,
        line_ending: str = "\n"
    ) -> int:
        """Write lines to file."""
        content = line_ending.join(lines)
        if not content.endswith(line_ending):
            content += line_ending
        return self.write(path, content, encoding)

    def append(
        self,
        path: Union[str, Path],
        content: str,
        encoding: Optional[str] = None
    ) -> int:
        """Append content to file."""
        path = Path(path)
        enc = encoding or self.default_encoding

        with open(path, 'a', encoding=enc) as f:
            return f.write(content)

    def write_json(
        self,
        path: Union[str, Path],
        data: Any,
        indent: int = 2,
        sort_keys: bool = False
    ) -> int:
        """Write JSON file."""
        content = json.dumps(data, indent=indent, sort_keys=sort_keys, default=str)
        return self.write(path, content)

    def write_yaml(
        self,
        path: Union[str, Path],
        data: Any
    ) -> int:
        """Write YAML file."""
        try:
            import yaml
            content = yaml.dump(data, default_flow_style=False)
            return self.write(path, content)
        except ImportError:
            raise ImportError("PyYAML is required for YAML writing")

    def write_csv(
        self,
        path: Union[str, Path],
        rows: List[List[Any]],
        delimiter: str = ",",
        headers: Optional[List[str]] = None
    ) -> None:
        """Write CSV file."""
        import csv

        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, 'w', newline='', encoding=self.default_encoding) as f:
            writer = csv.writer(f, delimiter=delimiter)
            if headers:
                writer.writerow(headers)
            writer.writerows(rows)


# =============================================================================
# FILE SEARCHER
# =============================================================================

class FileSearcher:
    """Search files and content."""

    def __init__(self, ignore_patterns: Optional[List[str]] = None):
        self.ignore_patterns = ignore_patterns or [
            "*.pyc", "__pycache__", ".git", ".svn", "node_modules",
            ".DS_Store", "*.egg-info", "dist", "build", ".venv", "venv"
        ]

    def find_files(
        self,
        root: Union[str, Path],
        pattern: str = "*",
        recursive: bool = True,
        file_type: Optional[FileType] = None,
        min_size: Optional[int] = None,
        max_size: Optional[int] = None,
        modified_after: Optional[datetime] = None,
        modified_before: Optional[datetime] = None
    ) -> Generator[Path, None, None]:
        """Find files matching criteria."""
        root = Path(root)

        if recursive:
            paths = root.rglob(pattern)
        else:
            paths = root.glob(pattern)

        for path in paths:
            # Skip ignored patterns
            if any(fnmatch.fnmatch(path.name, p) for p in self.ignore_patterns):
                continue
            if any(fnmatch.fnmatch(str(part), p) for part in path.parts for p in self.ignore_patterns):
                continue

            if not path.is_file():
                continue

            # Apply filters
            if file_type and FileTypeDetector.detect(path) != file_type:
                continue

            stat_info = path.stat()

            if min_size and stat_info.st_size < min_size:
                continue
            if max_size and stat_info.st_size > max_size:
                continue

            mod_time = datetime.fromtimestamp(stat_info.st_mtime)
            if modified_after and mod_time < modified_after:
                continue
            if modified_before and mod_time > modified_before:
                continue

            yield path

    def search_content(
        self,
        root: Union[str, Path],
        pattern: str,
        file_pattern: str = "*.py",
        regex: bool = False,
        case_sensitive: bool = True,
        context_lines: int = 2,
        max_results: int = 100
    ) -> List[SearchResult]:
        """Search for content within files."""
        root = Path(root)
        results = []

        if regex:
            flags = 0 if case_sensitive else re.IGNORECASE
            search_re = re.compile(pattern, flags)
        else:
            if not case_sensitive:
                pattern = pattern.lower()

        for file_path in self.find_files(root, file_pattern):
            if not FileTypeDetector.is_text_file(file_path):
                continue

            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
            except Exception:
                continue

            file_matches = []
            matched_lines = []
            contexts = []

            for i, line in enumerate(lines):
                compare_line = line if case_sensitive else line.lower()

                if regex:
                    match = search_re.search(line)
                    found = match is not None
                else:
                    found = pattern in compare_line

                if found:
                    file_matches.append({
                        "line_number": i + 1,
                        "line": line.rstrip(),
                        "match": pattern
                    })
                    matched_lines.append(i + 1)

                    # Get context
                    start = max(0, i - context_lines)
                    end = min(len(lines), i + context_lines + 1)
                    context = ''.join(lines[start:end])
                    contexts.append(context)

            if file_matches:
                results.append(SearchResult(
                    path=file_path,
                    matches=file_matches,
                    line_numbers=matched_lines,
                    context=contexts
                ))

                if len(results) >= max_results:
                    break

        return results

    def find_duplicates(
        self,
        root: Union[str, Path],
        by_content: bool = True
    ) -> Dict[str, List[Path]]:
        """Find duplicate files."""
        root = Path(root)

        if by_content:
            # Group by hash
            hash_map: Dict[str, List[Path]] = {}
            reader = FileReader()

            for path in self.find_files(root):
                try:
                    checksum = reader.compute_checksum(path)
                    if checksum not in hash_map:
                        hash_map[checksum] = []
                    hash_map[checksum].append(path)
                except Exception:
                    continue

            return {k: v for k, v in hash_map.items() if len(v) > 1}
        else:
            # Group by name
            name_map: Dict[str, List[Path]] = {}

            for path in self.find_files(root):
                name = path.name
                if name not in name_map:
                    name_map[name] = []
                name_map[name].append(path)

            return {k: v for k, v in name_map.items() if len(v) > 1}


# =============================================================================
# DIRECTORY MANAGER
# =============================================================================

class DirectoryManager:
    """Manage directory operations."""

    def create(self, path: Union[str, Path], parents: bool = True) -> Path:
        """Create directory."""
        path = Path(path)
        path.mkdir(parents=parents, exist_ok=True)
        return path

    def list_contents(
        self,
        path: Union[str, Path],
        recursive: bool = False,
        include_hidden: bool = False
    ) -> List[FileInfo]:
        """List directory contents."""
        path = Path(path)
        reader = FileReader()

        contents = []

        if recursive:
            items = path.rglob("*")
        else:
            items = path.iterdir()

        for item in items:
            if not include_hidden and item.name.startswith("."):
                continue

            try:
                info = reader.get_info(item)
                contents.append(info)
            except Exception:
                continue

        return sorted(contents, key=lambda x: (not x.is_directory, x.name.lower()))

    def get_size(self, path: Union[str, Path]) -> int:
        """Get total size of directory."""
        path = Path(path)
        total = 0

        for item in path.rglob("*"):
            if item.is_file():
                total += item.stat().st_size

        return total

    def copy(
        self,
        src: Union[str, Path],
        dst: Union[str, Path],
        overwrite: bool = False
    ) -> Path:
        """Copy directory."""
        src = Path(src)
        dst = Path(dst)

        if dst.exists() and not overwrite:
            raise FileExistsError(f"Destination exists: {dst}")

        shutil.copytree(src, dst, dirs_exist_ok=overwrite)
        return dst

    def move(self, src: Union[str, Path], dst: Union[str, Path]) -> Path:
        """Move directory."""
        src = Path(src)
        dst = Path(dst)
        shutil.move(str(src), str(dst))
        return dst

    def delete(self, path: Union[str, Path], force: bool = False) -> bool:
        """Delete directory."""
        path = Path(path)

        if not path.exists():
            return False

        if path.is_dir():
            if force:
                shutil.rmtree(path)
            else:
                path.rmdir()  # Only removes empty directories
        else:
            path.unlink()

        return True

    def tree(
        self,
        path: Union[str, Path],
        max_depth: int = 3,
        include_hidden: bool = False
    ) -> str:
        """Generate directory tree string."""
        path = Path(path)
        lines = [str(path)]

        def add_tree(current_path: Path, prefix: str, depth: int):
            if depth > max_depth:
                return

            items = sorted(current_path.iterdir(), key=lambda x: (x.is_file(), x.name.lower()))

            # Filter hidden files
            if not include_hidden:
                items = [i for i in items if not i.name.startswith(".")]

            for i, item in enumerate(items):
                is_last = i == len(items) - 1
                connector = "└── " if is_last else "├── "
                lines.append(f"{prefix}{connector}{item.name}{'/' if item.is_dir() else ''}")

                if item.is_dir():
                    new_prefix = prefix + ("    " if is_last else "│   ")
                    add_tree(item, new_prefix, depth + 1)

        add_tree(path, "", 1)
        return "\n".join(lines)


# =============================================================================
# FILE CONVERTER
# =============================================================================

class FileConverter:
    """Convert between file formats."""

    def __init__(self):
        self.reader = FileReader()
        self.writer = FileWriter()

    def json_to_yaml(self, src: Union[str, Path], dst: Union[str, Path]) -> None:
        """Convert JSON to YAML."""
        data = self.reader.read_json(src)
        self.writer.write_yaml(dst, data)

    def yaml_to_json(
        self,
        src: Union[str, Path],
        dst: Union[str, Path],
        indent: int = 2
    ) -> None:
        """Convert YAML to JSON."""
        data = self.reader.read_yaml(src)
        self.writer.write_json(dst, data, indent=indent)

    def csv_to_json(
        self,
        src: Union[str, Path],
        dst: Union[str, Path],
        has_headers: bool = True
    ) -> None:
        """Convert CSV to JSON."""
        rows = self.reader.read_csv(src)

        if has_headers and rows:
            headers = rows[0]
            data = [dict(zip(headers, row)) for row in rows[1:]]
        else:
            data = rows

        self.writer.write_json(dst, data)

    def json_to_csv(
        self,
        src: Union[str, Path],
        dst: Union[str, Path]
    ) -> None:
        """Convert JSON array to CSV."""
        data = self.reader.read_json(src)

        if not isinstance(data, list):
            data = [data]

        if not data:
            self.writer.write_csv(dst, [])
            return

        # Get headers from first item
        if isinstance(data[0], dict):
            headers = list(data[0].keys())
            rows = [[item.get(h, "") for h in headers] for item in data]
            self.writer.write_csv(dst, rows, headers=headers)
        else:
            self.writer.write_csv(dst, [[item] for item in data])

    def text_to_lines(
        self,
        src: Union[str, Path],
        dst: Union[str, Path],
        strip: bool = True
    ) -> None:
        """Convert text file to one line per file in output directory."""
        content = self.reader.read(src)
        dst = Path(dst)
        dst.mkdir(parents=True, exist_ok=True)

        for i, line in enumerate(content.split("\n")):
            if strip:
                line = line.strip()
            if line:
                self.writer.write(dst / f"line_{i:05d}.txt", line)


# =============================================================================
# FILE WATCHER
# =============================================================================

class FileWatcher:
    """Watch files for changes (simplified polling implementation)."""

    def __init__(self, paths: List[Union[str, Path]], poll_interval: float = 1.0):
        self.paths = [Path(p) for p in paths]
        self.poll_interval = poll_interval
        self._file_states: Dict[Path, float] = {}
        self._callbacks: List[Callable[[WatchEvent], None]] = []
        self._running = False

    def on_change(self, callback: Callable[[WatchEvent], None]) -> None:
        """Register callback for file changes."""
        self._callbacks.append(callback)

    def _get_state(self, path: Path) -> Optional[float]:
        """Get file modification time."""
        try:
            return path.stat().st_mtime
        except:
            return None

    def _scan(self) -> List[WatchEvent]:
        """Scan for changes."""
        events = []
        current_files: Set[Path] = set()

        for watch_path in self.paths:
            if watch_path.is_file():
                current_files.add(watch_path)
            elif watch_path.is_dir():
                for f in watch_path.rglob("*"):
                    if f.is_file():
                        current_files.add(f)

        # Check for new/modified files
        for file_path in current_files:
            mtime = self._get_state(file_path)

            if file_path not in self._file_states:
                events.append(WatchEvent(
                    event_type=WatchEventType.CREATED,
                    path=file_path
                ))
                self._file_states[file_path] = mtime
            elif self._file_states[file_path] != mtime:
                events.append(WatchEvent(
                    event_type=WatchEventType.MODIFIED,
                    path=file_path
                ))
                self._file_states[file_path] = mtime

        # Check for deleted files
        for file_path in list(self._file_states.keys()):
            if file_path not in current_files:
                events.append(WatchEvent(
                    event_type=WatchEventType.DELETED,
                    path=file_path
                ))
                del self._file_states[file_path]

        return events

    async def start(self) -> None:
        """Start watching files."""
        self._running = True

        # Initial scan
        for watch_path in self.paths:
            if watch_path.is_file():
                self._file_states[watch_path] = self._get_state(watch_path)
            elif watch_path.is_dir():
                for f in watch_path.rglob("*"):
                    if f.is_file():
                        self._file_states[f] = self._get_state(f)

        # Watch loop
        while self._running:
            events = self._scan()

            for event in events:
                for callback in self._callbacks:
                    try:
                        callback(event)
                    except Exception as e:
                        logger.error(f"Callback error: {e}")

            await asyncio.sleep(self.poll_interval)

    def stop(self) -> None:
        """Stop watching files."""
        self._running = False


# =============================================================================
# FILE TOOLKIT - UNIFIED INTERFACE
# =============================================================================

class FileToolkit:
    """
    Unified file toolkit providing all file operation capabilities.

    Main entry point for file operations in BAEL.
    """

    def __init__(self, default_encoding: str = "utf-8"):
        self.reader = FileReader(default_encoding)
        self.writer = FileWriter(default_encoding)
        self.searcher = FileSearcher()
        self.directory = DirectoryManager()
        self.converter = FileConverter()

    def read(self, path: Union[str, Path]) -> str:
        """Read file content."""
        return self.reader.read(path)

    def write(self, path: Union[str, Path], content: str) -> int:
        """Write content to file."""
        return self.writer.write(path, content)

    def get_info(self, path: Union[str, Path]) -> FileInfo:
        """Get file information."""
        return self.reader.get_info(path)

    def find(
        self,
        root: Union[str, Path],
        pattern: str = "*",
        recursive: bool = True
    ) -> List[Path]:
        """Find files matching pattern."""
        return list(self.searcher.find_files(root, pattern, recursive))

    def search(
        self,
        root: Union[str, Path],
        content: str,
        file_pattern: str = "*.py"
    ) -> List[SearchResult]:
        """Search for content in files."""
        return self.searcher.search_content(root, content, file_pattern)

    def list_dir(
        self,
        path: Union[str, Path],
        recursive: bool = False
    ) -> List[FileInfo]:
        """List directory contents."""
        return self.directory.list_contents(path, recursive)

    def tree(self, path: Union[str, Path], max_depth: int = 3) -> str:
        """Generate directory tree."""
        return self.directory.tree(path, max_depth)

    def copy(
        self,
        src: Union[str, Path],
        dst: Union[str, Path]
    ) -> Path:
        """Copy file or directory."""
        src = Path(src)
        dst = Path(dst)

        if src.is_dir():
            return self.directory.copy(src, dst)
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            return dst

    def move(
        self,
        src: Union[str, Path],
        dst: Union[str, Path]
    ) -> Path:
        """Move file or directory."""
        src = Path(src)
        shutil.move(str(src), str(dst))
        return Path(dst)

    def delete(self, path: Union[str, Path]) -> bool:
        """Delete file or directory."""
        return self.directory.delete(path, force=True)

    def watch(
        self,
        paths: List[Union[str, Path]],
        callback: Callable[[WatchEvent], None]
    ) -> FileWatcher:
        """Create a file watcher."""
        watcher = FileWatcher(paths)
        watcher.on_change(callback)
        return watcher

    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Get tool definitions for BAEL integration."""
        return [
            {
                "name": "file_read",
                "description": "Read file content",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"}
                    },
                    "required": ["path"]
                },
                "handler": self.read
            },
            {
                "name": "file_write",
                "description": "Write content to file",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "content": {"type": "string"}
                    },
                    "required": ["path", "content"]
                },
                "handler": self.write
            },
            {
                "name": "file_info",
                "description": "Get file information",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"}
                    },
                    "required": ["path"]
                },
                "handler": lambda path: self.get_info(path).to_dict()
            },
            {
                "name": "file_search",
                "description": "Search for content in files",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "root": {"type": "string"},
                        "content": {"type": "string"},
                        "file_pattern": {"type": "string", "default": "*.py"}
                    },
                    "required": ["root", "content"]
                },
                "handler": self.search
            },
            {
                "name": "directory_tree",
                "description": "Generate directory tree view",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "max_depth": {"type": "integer", "default": 3}
                    },
                    "required": ["path"]
                },
                "handler": self.tree
            }
        ]


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "FileToolkit",
    "FileReader",
    "FileWriter",
    "FileWatcher",
    "FileConverter",
    "FileSearcher",
    "DirectoryManager",
    "FileInfo",
    "SearchResult",
    "WatchEvent",
    "FileType",
    "WatchEventType",
    "FileTypeDetector"
]

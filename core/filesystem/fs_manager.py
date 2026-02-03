#!/usr/bin/env python3
"""
BAEL - File System Manager
Advanced file system operations for AI agents.

Features:
- File and directory operations
- Path manipulation
- File watching
- Atomic operations
- Temporary file management
- File locking
- Checksum calculation
- File type detection
- Archive operations
- File streaming
"""

import asyncio
import hashlib
import json
import logging
import os
import shutil
import stat
import tempfile
import threading
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import (Any, BinaryIO, Callable, Dict, Generator, Generic,
                    Iterator, List, Optional, Set, TextIO, Tuple, Type,
                    TypeVar, Union)

logger = logging.getLogger(__name__)


T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class FileType(Enum):
    """File types."""
    FILE = "file"
    DIRECTORY = "directory"
    SYMLINK = "symlink"
    UNKNOWN = "unknown"


class WatchEvent(Enum):
    """File watch events."""
    CREATED = "created"
    MODIFIED = "modified"
    DELETED = "deleted"
    MOVED = "moved"


class HashAlgorithm(Enum):
    """Hash algorithms."""
    MD5 = "md5"
    SHA1 = "sha1"
    SHA256 = "sha256"
    SHA512 = "sha512"


class LockMode(Enum):
    """File lock modes."""
    SHARED = "shared"
    EXCLUSIVE = "exclusive"


class OpenMode(Enum):
    """File open modes."""
    READ = "r"
    WRITE = "w"
    APPEND = "a"
    READ_BINARY = "rb"
    WRITE_BINARY = "wb"
    APPEND_BINARY = "ab"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class FileInfo:
    """File information."""
    path: str
    name: str
    extension: str
    type: FileType
    size: int = 0
    created: Optional[datetime] = None
    modified: Optional[datetime] = None
    accessed: Optional[datetime] = None
    permissions: int = 0
    owner: Optional[str] = None
    is_hidden: bool = False


@dataclass
class DirectoryInfo:
    """Directory information."""
    path: str
    name: str
    file_count: int = 0
    dir_count: int = 0
    total_size: int = 0
    created: Optional[datetime] = None
    modified: Optional[datetime] = None


@dataclass
class WatchNotification:
    """File watch notification."""
    event: WatchEvent
    path: str
    old_path: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class CopyOptions:
    """Copy operation options."""
    overwrite: bool = False
    preserve_metadata: bool = True
    follow_symlinks: bool = True
    exclude_patterns: List[str] = field(default_factory=list)


@dataclass
class SearchResult:
    """File search result."""
    path: str
    matches: List[Tuple[int, str]] = field(default_factory=list)  # (line_num, line)
    total_matches: int = 0


@dataclass
class DiskUsage:
    """Disk usage statistics."""
    total: int
    used: int
    free: int
    percent: float


# =============================================================================
# PATH UTILITIES
# =============================================================================

class PathUtils:
    """Path manipulation utilities."""

    @staticmethod
    def normalize(path: str) -> str:
        """Normalize path."""
        return os.path.normpath(path)

    @staticmethod
    def absolute(path: str) -> str:
        """Get absolute path."""
        return os.path.abspath(path)

    @staticmethod
    def relative(path: str, base: str) -> str:
        """Get relative path."""
        return os.path.relpath(path, base)

    @staticmethod
    def join(*parts: str) -> str:
        """Join path parts."""
        return os.path.join(*parts)

    @staticmethod
    def split(path: str) -> Tuple[str, str]:
        """Split path into directory and filename."""
        return os.path.split(path)

    @staticmethod
    def splitext(path: str) -> Tuple[str, str]:
        """Split path into name and extension."""
        return os.path.splitext(path)

    @staticmethod
    def dirname(path: str) -> str:
        """Get directory name."""
        return os.path.dirname(path)

    @staticmethod
    def basename(path: str) -> str:
        """Get base name."""
        return os.path.basename(path)

    @staticmethod
    def exists(path: str) -> bool:
        """Check if path exists."""
        return os.path.exists(path)

    @staticmethod
    def is_file(path: str) -> bool:
        """Check if path is file."""
        return os.path.isfile(path)

    @staticmethod
    def is_dir(path: str) -> bool:
        """Check if path is directory."""
        return os.path.isdir(path)

    @staticmethod
    def is_symlink(path: str) -> bool:
        """Check if path is symlink."""
        return os.path.islink(path)

    @staticmethod
    def expanduser(path: str) -> str:
        """Expand user directory."""
        return os.path.expanduser(path)

    @staticmethod
    def expandvars(path: str) -> str:
        """Expand environment variables."""
        return os.path.expandvars(path)

    @staticmethod
    def glob(pattern: str) -> List[str]:
        """Glob pattern matching."""
        import glob as glob_module
        return glob_module.glob(pattern, recursive=True)

    @staticmethod
    def match(path: str, pattern: str) -> bool:
        """Check if path matches pattern."""
        import fnmatch
        return fnmatch.fnmatch(path, pattern)


# =============================================================================
# FILE INFO PROVIDER
# =============================================================================

class FileInfoProvider:
    """Provide file information."""

    def get_info(self, path: str) -> Optional[FileInfo]:
        """Get file information."""
        try:
            stat_result = os.stat(path)

            # Determine type
            if os.path.islink(path):
                file_type = FileType.SYMLINK
            elif os.path.isdir(path):
                file_type = FileType.DIRECTORY
            elif os.path.isfile(path):
                file_type = FileType.FILE
            else:
                file_type = FileType.UNKNOWN

            name = os.path.basename(path)
            _, ext = os.path.splitext(name)

            return FileInfo(
                path=os.path.abspath(path),
                name=name,
                extension=ext,
                type=file_type,
                size=stat_result.st_size,
                created=datetime.fromtimestamp(stat_result.st_ctime),
                modified=datetime.fromtimestamp(stat_result.st_mtime),
                accessed=datetime.fromtimestamp(stat_result.st_atime),
                permissions=stat_result.st_mode,
                is_hidden=name.startswith('.')
            )
        except OSError:
            return None

    def get_dir_info(self, path: str) -> Optional[DirectoryInfo]:
        """Get directory information."""
        if not os.path.isdir(path):
            return None

        file_count = 0
        dir_count = 0
        total_size = 0

        try:
            for entry in os.scandir(path):
                if entry.is_file():
                    file_count += 1
                    total_size += entry.stat().st_size
                elif entry.is_dir():
                    dir_count += 1

            stat_result = os.stat(path)

            return DirectoryInfo(
                path=os.path.abspath(path),
                name=os.path.basename(path),
                file_count=file_count,
                dir_count=dir_count,
                total_size=total_size,
                created=datetime.fromtimestamp(stat_result.st_ctime),
                modified=datetime.fromtimestamp(stat_result.st_mtime)
            )
        except OSError:
            return None


# =============================================================================
# FILE HASHER
# =============================================================================

class FileHasher:
    """Calculate file hashes."""

    ALGORITHMS = {
        HashAlgorithm.MD5: hashlib.md5,
        HashAlgorithm.SHA1: hashlib.sha1,
        HashAlgorithm.SHA256: hashlib.sha256,
        HashAlgorithm.SHA512: hashlib.sha512
    }

    def hash_file(
        self,
        path: str,
        algorithm: HashAlgorithm = HashAlgorithm.SHA256,
        chunk_size: int = 8192
    ) -> str:
        """Calculate file hash."""
        hasher = self.ALGORITHMS[algorithm]()

        with open(path, 'rb') as f:
            while chunk := f.read(chunk_size):
                hasher.update(chunk)

        return hasher.hexdigest()

    def hash_bytes(
        self,
        data: bytes,
        algorithm: HashAlgorithm = HashAlgorithm.SHA256
    ) -> str:
        """Calculate hash of bytes."""
        hasher = self.ALGORITHMS[algorithm]()
        hasher.update(data)
        return hasher.hexdigest()

    def verify_file(
        self,
        path: str,
        expected_hash: str,
        algorithm: HashAlgorithm = HashAlgorithm.SHA256
    ) -> bool:
        """Verify file hash."""
        actual = self.hash_file(path, algorithm)
        return actual.lower() == expected_hash.lower()


# =============================================================================
# FILE LOCK
# =============================================================================

class FileLock:
    """File locking implementation."""

    def __init__(self, path: str, mode: LockMode = LockMode.EXCLUSIVE):
        self.path = path
        self.mode = mode
        self.lock_path = f"{path}.lock"
        self._lock_file: Optional[TextIO] = None
        self._acquired = False

    def acquire(self, timeout: float = 10.0) -> bool:
        """Acquire lock."""
        start = time.time()

        while time.time() - start < timeout:
            try:
                # Try to create lock file exclusively
                fd = os.open(
                    self.lock_path,
                    os.O_CREAT | os.O_EXCL | os.O_WRONLY
                )
                self._lock_file = os.fdopen(fd, 'w')
                self._lock_file.write(str(os.getpid()))
                self._lock_file.flush()
                self._acquired = True
                return True
            except FileExistsError:
                # Lock exists, wait and retry
                time.sleep(0.1)

        return False

    def release(self) -> None:
        """Release lock."""
        if self._lock_file:
            self._lock_file.close()
            self._lock_file = None

        if self._acquired:
            try:
                os.remove(self.lock_path)
            except OSError:
                pass
            self._acquired = False

    def __enter__(self):
        if not self.acquire():
            raise TimeoutError(f"Could not acquire lock on {self.path}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()
        return False


# =============================================================================
# TEMP FILE MANAGER
# =============================================================================

class TempFileManager:
    """Manage temporary files."""

    def __init__(self, prefix: str = "bael_", suffix: str = ""):
        self.prefix = prefix
        self.suffix = suffix
        self._files: Set[str] = set()
        self._dirs: Set[str] = set()

    def create_file(
        self,
        content: Optional[bytes] = None,
        suffix: Optional[str] = None
    ) -> str:
        """Create temporary file."""
        fd, path = tempfile.mkstemp(
            prefix=self.prefix,
            suffix=suffix or self.suffix
        )

        if content:
            os.write(fd, content)

        os.close(fd)
        self._files.add(path)
        return path

    def create_dir(self, suffix: Optional[str] = None) -> str:
        """Create temporary directory."""
        path = tempfile.mkdtemp(
            prefix=self.prefix,
            suffix=suffix or self.suffix
        )
        self._dirs.add(path)
        return path

    def cleanup(self) -> int:
        """Clean up all temporary files and directories."""
        count = 0

        # Remove files
        for path in list(self._files):
            try:
                os.remove(path)
                self._files.discard(path)
                count += 1
            except OSError:
                pass

        # Remove directories
        for path in list(self._dirs):
            try:
                shutil.rmtree(path)
                self._dirs.discard(path)
                count += 1
            except OSError:
                pass

        return count

    def __del__(self):
        self.cleanup()


# =============================================================================
# FILE WATCHER
# =============================================================================

class FileWatcher:
    """Watch file system for changes."""

    def __init__(self, paths: List[str], callback: Callable[[WatchNotification], None]):
        self.paths = paths
        self.callback = callback
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._states: Dict[str, float] = {}  # path -> mtime

    def _scan_initial(self) -> None:
        """Scan initial state."""
        for path in self.paths:
            if os.path.isdir(path):
                for entry in os.scandir(path):
                    try:
                        self._states[entry.path] = entry.stat().st_mtime
                    except OSError:
                        pass
            elif os.path.exists(path):
                try:
                    self._states[path] = os.stat(path).st_mtime
                except OSError:
                    pass

    def _check_changes(self) -> List[WatchNotification]:
        """Check for changes."""
        notifications = []
        current_paths: Set[str] = set()

        for path in self.paths:
            if os.path.isdir(path):
                for entry in os.scandir(path):
                    current_paths.add(entry.path)

                    try:
                        mtime = entry.stat().st_mtime

                        if entry.path not in self._states:
                            # New file
                            notifications.append(WatchNotification(
                                event=WatchEvent.CREATED,
                                path=entry.path
                            ))
                            self._states[entry.path] = mtime
                        elif self._states[entry.path] != mtime:
                            # Modified
                            notifications.append(WatchNotification(
                                event=WatchEvent.MODIFIED,
                                path=entry.path
                            ))
                            self._states[entry.path] = mtime
                    except OSError:
                        pass

            elif os.path.exists(path):
                current_paths.add(path)
                try:
                    mtime = os.stat(path).st_mtime
                    if path not in self._states:
                        notifications.append(WatchNotification(
                            event=WatchEvent.CREATED,
                            path=path
                        ))
                        self._states[path] = mtime
                    elif self._states[path] != mtime:
                        notifications.append(WatchNotification(
                            event=WatchEvent.MODIFIED,
                            path=path
                        ))
                        self._states[path] = mtime
                except OSError:
                    pass

        # Check for deletions
        for path in list(self._states.keys()):
            if path not in current_paths:
                notifications.append(WatchNotification(
                    event=WatchEvent.DELETED,
                    path=path
                ))
                del self._states[path]

        return notifications

    def _watch_loop(self, interval: float) -> None:
        """Watch loop."""
        while self._running:
            notifications = self._check_changes()
            for notification in notifications:
                try:
                    self.callback(notification)
                except Exception as e:
                    logger.error(f"Watch callback error: {e}")
            time.sleep(interval)

    def start(self, interval: float = 1.0) -> None:
        """Start watching."""
        if self._running:
            return

        self._scan_initial()
        self._running = True
        self._thread = threading.Thread(
            target=self._watch_loop,
            args=(interval,),
            daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        """Stop watching."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None


# =============================================================================
# FILE STREAMER
# =============================================================================

class FileStreamer:
    """Stream file contents."""

    def __init__(self, chunk_size: int = 8192):
        self.chunk_size = chunk_size

    def read_chunks(self, path: str) -> Generator[bytes, None, None]:
        """Read file in chunks."""
        with open(path, 'rb') as f:
            while chunk := f.read(self.chunk_size):
                yield chunk

    def read_lines(self, path: str, encoding: str = 'utf-8') -> Generator[str, None, None]:
        """Read file lines."""
        with open(path, 'r', encoding=encoding) as f:
            for line in f:
                yield line

    async def async_read_chunks(self, path: str) -> List[bytes]:
        """Async read file in chunks."""
        loop = asyncio.get_event_loop()

        def _read():
            return list(self.read_chunks(path))

        return await loop.run_in_executor(None, _read)


# =============================================================================
# FILE SEARCHER
# =============================================================================

class FileSearcher:
    """Search within files."""

    def search_in_file(
        self,
        path: str,
        pattern: str,
        case_sensitive: bool = False,
        max_matches: int = 100
    ) -> SearchResult:
        """Search for pattern in file."""
        result = SearchResult(path=path)

        if not case_sensitive:
            pattern = pattern.lower()

        try:
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                for line_num, line in enumerate(f, 1):
                    check_line = line if case_sensitive else line.lower()

                    if pattern in check_line:
                        result.matches.append((line_num, line.rstrip()))
                        result.total_matches += 1

                        if result.total_matches >= max_matches:
                            break
        except (OSError, UnicodeDecodeError):
            pass

        return result

    def search_in_directory(
        self,
        directory: str,
        pattern: str,
        file_pattern: str = "*",
        recursive: bool = True,
        case_sensitive: bool = False
    ) -> List[SearchResult]:
        """Search for pattern in directory."""
        results = []

        base = Path(directory)

        if recursive:
            files = base.rglob(file_pattern)
        else:
            files = base.glob(file_pattern)

        for file_path in files:
            if file_path.is_file():
                result = self.search_in_file(
                    str(file_path),
                    pattern,
                    case_sensitive
                )
                if result.matches:
                    results.append(result)

        return results


# =============================================================================
# ATOMIC OPERATIONS
# =============================================================================

class AtomicOperations:
    """Atomic file operations."""

    def __init__(self):
        self._temp = TempFileManager(prefix="atomic_")

    def write(self, path: str, content: Union[str, bytes], encoding: str = 'utf-8') -> bool:
        """Atomic write operation."""
        try:
            # Write to temp file
            if isinstance(content, str):
                data = content.encode(encoding)
            else:
                data = content

            temp_path = self._temp.create_file(data)

            # Ensure directory exists
            dir_path = os.path.dirname(path)
            if dir_path:
                os.makedirs(dir_path, exist_ok=True)

            # Atomic rename
            shutil.move(temp_path, path)
            self._temp._files.discard(temp_path)

            return True
        except OSError as e:
            logger.error(f"Atomic write failed: {e}")
            return False

    def copy(self, src: str, dst: str) -> bool:
        """Atomic copy operation."""
        try:
            # Copy to temp first
            temp_dir = os.path.dirname(dst) or '.'
            temp_path = self._temp.create_file()

            shutil.copy2(src, temp_path)

            # Ensure directory exists
            dir_path = os.path.dirname(dst)
            if dir_path:
                os.makedirs(dir_path, exist_ok=True)

            # Atomic rename
            shutil.move(temp_path, dst)
            self._temp._files.discard(temp_path)

            return True
        except OSError as e:
            logger.error(f"Atomic copy failed: {e}")
            return False

    def update(
        self,
        path: str,
        transform: Callable[[str], str],
        encoding: str = 'utf-8'
    ) -> bool:
        """Atomic update with transform function."""
        try:
            # Read current content
            with open(path, 'r', encoding=encoding) as f:
                content = f.read()

            # Transform
            new_content = transform(content)

            # Atomic write
            return self.write(path, new_content, encoding)
        except OSError as e:
            logger.error(f"Atomic update failed: {e}")
            return False


# =============================================================================
# FILE SYSTEM MANAGER
# =============================================================================

class FileSystemManager:
    """
    File System Manager for BAEL.

    Comprehensive file system operations.
    """

    def __init__(self):
        self._info_provider = FileInfoProvider()
        self._hasher = FileHasher()
        self._temp = TempFileManager()
        self._atomic = AtomicOperations()
        self._streamer = FileStreamer()
        self._searcher = FileSearcher()
        self._watchers: Dict[str, FileWatcher] = {}

    # -------------------------------------------------------------------------
    # PATH OPERATIONS
    # -------------------------------------------------------------------------

    def normalize(self, path: str) -> str:
        """Normalize path."""
        return PathUtils.normalize(path)

    def absolute(self, path: str) -> str:
        """Get absolute path."""
        return PathUtils.absolute(path)

    def join(self, *parts: str) -> str:
        """Join path parts."""
        return PathUtils.join(*parts)

    def exists(self, path: str) -> bool:
        """Check if path exists."""
        return PathUtils.exists(path)

    def is_file(self, path: str) -> bool:
        """Check if path is file."""
        return PathUtils.is_file(path)

    def is_dir(self, path: str) -> bool:
        """Check if path is directory."""
        return PathUtils.is_dir(path)

    # -------------------------------------------------------------------------
    # FILE OPERATIONS
    # -------------------------------------------------------------------------

    def read(self, path: str, encoding: str = 'utf-8') -> str:
        """Read file content."""
        with open(path, 'r', encoding=encoding) as f:
            return f.read()

    def read_bytes(self, path: str) -> bytes:
        """Read file as bytes."""
        with open(path, 'rb') as f:
            return f.read()

    def write(self, path: str, content: str, encoding: str = 'utf-8') -> bool:
        """Write file content."""
        try:
            dir_path = os.path.dirname(path)
            if dir_path:
                os.makedirs(dir_path, exist_ok=True)

            with open(path, 'w', encoding=encoding) as f:
                f.write(content)
            return True
        except OSError:
            return False

    def write_bytes(self, path: str, content: bytes) -> bool:
        """Write bytes to file."""
        try:
            dir_path = os.path.dirname(path)
            if dir_path:
                os.makedirs(dir_path, exist_ok=True)

            with open(path, 'wb') as f:
                f.write(content)
            return True
        except OSError:
            return False

    def append(self, path: str, content: str, encoding: str = 'utf-8') -> bool:
        """Append to file."""
        try:
            with open(path, 'a', encoding=encoding) as f:
                f.write(content)
            return True
        except OSError:
            return False

    def delete(self, path: str) -> bool:
        """Delete file."""
        try:
            os.remove(path)
            return True
        except OSError:
            return False

    def copy(self, src: str, dst: str, options: Optional[CopyOptions] = None) -> bool:
        """Copy file."""
        options = options or CopyOptions()

        if not options.overwrite and os.path.exists(dst):
            return False

        try:
            if options.preserve_metadata:
                shutil.copy2(src, dst)
            else:
                shutil.copy(src, dst)
            return True
        except OSError:
            return False

    def move(self, src: str, dst: str) -> bool:
        """Move file."""
        try:
            shutil.move(src, dst)
            return True
        except OSError:
            return False

    def rename(self, path: str, new_name: str) -> bool:
        """Rename file."""
        try:
            dir_path = os.path.dirname(path)
            new_path = os.path.join(dir_path, new_name)
            os.rename(path, new_path)
            return True
        except OSError:
            return False

    # -------------------------------------------------------------------------
    # DIRECTORY OPERATIONS
    # -------------------------------------------------------------------------

    def mkdir(self, path: str, parents: bool = True) -> bool:
        """Create directory."""
        try:
            os.makedirs(path, exist_ok=parents)
            return True
        except OSError:
            return False

    def rmdir(self, path: str, recursive: bool = False) -> bool:
        """Remove directory."""
        try:
            if recursive:
                shutil.rmtree(path)
            else:
                os.rmdir(path)
            return True
        except OSError:
            return False

    def list_dir(self, path: str) -> List[str]:
        """List directory contents."""
        try:
            return os.listdir(path)
        except OSError:
            return []

    def walk(self, path: str) -> Generator[Tuple[str, List[str], List[str]], None, None]:
        """Walk directory tree."""
        yield from os.walk(path)

    def glob(self, pattern: str) -> List[str]:
        """Find files matching pattern."""
        return PathUtils.glob(pattern)

    def copy_dir(self, src: str, dst: str, options: Optional[CopyOptions] = None) -> bool:
        """Copy directory recursively."""
        options = options or CopyOptions()

        if not options.overwrite and os.path.exists(dst):
            return False

        try:
            if os.path.exists(dst):
                shutil.rmtree(dst)
            shutil.copytree(src, dst, symlinks=not options.follow_symlinks)
            return True
        except OSError:
            return False

    # -------------------------------------------------------------------------
    # FILE INFO
    # -------------------------------------------------------------------------

    def get_info(self, path: str) -> Optional[FileInfo]:
        """Get file information."""
        return self._info_provider.get_info(path)

    def get_dir_info(self, path: str) -> Optional[DirectoryInfo]:
        """Get directory information."""
        return self._info_provider.get_dir_info(path)

    def get_size(self, path: str) -> int:
        """Get file size."""
        try:
            return os.path.getsize(path)
        except OSError:
            return 0

    def get_mtime(self, path: str) -> Optional[datetime]:
        """Get modification time."""
        try:
            return datetime.fromtimestamp(os.path.getmtime(path))
        except OSError:
            return None

    # -------------------------------------------------------------------------
    # HASHING
    # -------------------------------------------------------------------------

    def hash_file(
        self,
        path: str,
        algorithm: HashAlgorithm = HashAlgorithm.SHA256
    ) -> str:
        """Calculate file hash."""
        return self._hasher.hash_file(path, algorithm)

    def verify_hash(
        self,
        path: str,
        expected: str,
        algorithm: HashAlgorithm = HashAlgorithm.SHA256
    ) -> bool:
        """Verify file hash."""
        return self._hasher.verify_file(path, expected, algorithm)

    # -------------------------------------------------------------------------
    # TEMPORARY FILES
    # -------------------------------------------------------------------------

    def create_temp_file(self, content: Optional[bytes] = None, suffix: str = "") -> str:
        """Create temporary file."""
        return self._temp.create_file(content, suffix)

    def create_temp_dir(self, suffix: str = "") -> str:
        """Create temporary directory."""
        return self._temp.create_dir(suffix)

    def cleanup_temp(self) -> int:
        """Clean up temporary files."""
        return self._temp.cleanup()

    # -------------------------------------------------------------------------
    # ATOMIC OPERATIONS
    # -------------------------------------------------------------------------

    def atomic_write(self, path: str, content: Union[str, bytes]) -> bool:
        """Atomic write operation."""
        return self._atomic.write(path, content)

    def atomic_copy(self, src: str, dst: str) -> bool:
        """Atomic copy operation."""
        return self._atomic.copy(src, dst)

    def atomic_update(self, path: str, transform: Callable[[str], str]) -> bool:
        """Atomic update with transform."""
        return self._atomic.update(path, transform)

    # -------------------------------------------------------------------------
    # FILE LOCKING
    # -------------------------------------------------------------------------

    def lock(self, path: str, mode: LockMode = LockMode.EXCLUSIVE) -> FileLock:
        """Create file lock."""
        return FileLock(path, mode)

    # -------------------------------------------------------------------------
    # FILE WATCHING
    # -------------------------------------------------------------------------

    def watch(
        self,
        paths: List[str],
        callback: Callable[[WatchNotification], None],
        interval: float = 1.0
    ) -> str:
        """Start watching paths."""
        watcher_id = str(uuid.uuid4())
        watcher = FileWatcher(paths, callback)
        watcher.start(interval)
        self._watchers[watcher_id] = watcher
        return watcher_id

    def unwatch(self, watcher_id: str) -> bool:
        """Stop watching."""
        if watcher_id in self._watchers:
            self._watchers[watcher_id].stop()
            del self._watchers[watcher_id]
            return True
        return False

    # -------------------------------------------------------------------------
    # STREAMING
    # -------------------------------------------------------------------------

    def read_chunks(self, path: str, chunk_size: int = 8192) -> Generator[bytes, None, None]:
        """Read file in chunks."""
        self._streamer.chunk_size = chunk_size
        yield from self._streamer.read_chunks(path)

    def read_lines(self, path: str) -> Generator[str, None, None]:
        """Read file lines."""
        yield from self._streamer.read_lines(path)

    # -------------------------------------------------------------------------
    # SEARCHING
    # -------------------------------------------------------------------------

    def search(
        self,
        path: str,
        pattern: str,
        recursive: bool = True
    ) -> List[SearchResult]:
        """Search for pattern in files."""
        if os.path.isfile(path):
            result = self._searcher.search_in_file(path, pattern)
            return [result] if result.matches else []
        elif os.path.isdir(path):
            return self._searcher.search_in_directory(path, pattern, recursive=recursive)
        return []

    # -------------------------------------------------------------------------
    # DISK USAGE
    # -------------------------------------------------------------------------

    def get_disk_usage(self, path: str = ".") -> DiskUsage:
        """Get disk usage."""
        usage = shutil.disk_usage(path)
        return DiskUsage(
            total=usage.total,
            used=usage.used,
            free=usage.free,
            percent=(usage.used / usage.total) * 100
        )

    def get_dir_size(self, path: str) -> int:
        """Get total directory size."""
        total = 0
        for dirpath, dirnames, filenames in os.walk(path):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                try:
                    total += os.path.getsize(filepath)
                except OSError:
                    pass
        return total


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the File System Manager."""
    print("=" * 70)
    print("BAEL - FILE SYSTEM MANAGER DEMO")
    print("Advanced File Operations for AI Agents")
    print("=" * 70)
    print()

    fs = FileSystemManager()

    # 1. Path Operations
    print("1. PATH OPERATIONS:")
    print("-" * 40)

    path = "/home/user/docs/file.txt"
    print(f"   Path: {path}")
    print(f"   Normalized: {fs.normalize(path)}")
    print(f"   Basename: {PathUtils.basename(path)}")
    print(f"   Dirname: {PathUtils.dirname(path)}")
    print(f"   Extension: {PathUtils.splitext(path)[1]}")
    print()

    # 2. Temporary Files
    print("2. TEMPORARY FILES:")
    print("-" * 40)

    temp_file = fs.create_temp_file(b"Hello, BAEL!", suffix=".txt")
    temp_dir = fs.create_temp_dir()
    print(f"   Created temp file: {temp_file}")
    print(f"   Created temp dir: {temp_dir}")
    print()

    # 3. File Info
    print("3. FILE INFORMATION:")
    print("-" * 40)

    info = fs.get_info(temp_file)
    if info:
        print(f"   Path: {info.path}")
        print(f"   Size: {info.size} bytes")
        print(f"   Type: {info.type.value}")
        print(f"   Extension: {info.extension}")
    print()

    # 4. Read/Write
    print("4. READ/WRITE OPERATIONS:")
    print("-" * 40)

    test_file = fs.join(temp_dir, "test.txt")
    fs.write(test_file, "Hello, World!\nLine 2\nLine 3")
    content = fs.read(test_file)
    print(f"   Written to: {test_file}")
    print(f"   Content: {content[:30]}...")
    print()

    # 5. Hashing
    print("5. FILE HASHING:")
    print("-" * 40)

    hash_md5 = fs.hash_file(test_file, HashAlgorithm.MD5)
    hash_sha256 = fs.hash_file(test_file, HashAlgorithm.SHA256)
    print(f"   MD5: {hash_md5}")
    print(f"   SHA256: {hash_sha256[:32]}...")
    print()

    # 6. Streaming
    print("6. FILE STREAMING:")
    print("-" * 40)

    lines = list(fs.read_lines(test_file))
    print(f"   Total lines: {len(lines)}")
    for i, line in enumerate(lines[:3], 1):
        print(f"   Line {i}: {line.strip()}")
    print()

    # 7. Searching
    print("7. FILE SEARCHING:")
    print("-" * 40)

    results = fs.search(test_file, "Line")
    for result in results:
        print(f"   File: {PathUtils.basename(result.path)}")
        print(f"   Matches: {result.total_matches}")
        for line_num, line in result.matches[:2]:
            print(f"   - Line {line_num}: {line}")
    print()

    # 8. Disk Usage
    print("8. DISK USAGE:")
    print("-" * 40)

    usage = fs.get_disk_usage(".")
    print(f"   Total: {usage.total / (1024**3):.2f} GB")
    print(f"   Used: {usage.used / (1024**3):.2f} GB")
    print(f"   Free: {usage.free / (1024**3):.2f} GB")
    print(f"   Percent: {usage.percent:.1f}%")
    print()

    # 9. Atomic Operations
    print("9. ATOMIC OPERATIONS:")
    print("-" * 40)

    atomic_file = fs.join(temp_dir, "atomic.txt")
    success = fs.atomic_write(atomic_file, "Atomic content")
    print(f"   Atomic write: {'success' if success else 'failed'}")

    # Atomic update
    def transform(content: str) -> str:
        return content.upper()

    success = fs.atomic_update(atomic_file, transform)
    new_content = fs.read(atomic_file)
    print(f"   Atomic update: {new_content}")
    print()

    # 10. File Locking
    print("10. FILE LOCKING:")
    print("-" * 40)

    lock = fs.lock(atomic_file)
    with lock:
        print(f"   Lock acquired on: {PathUtils.basename(atomic_file)}")
        print("   Performing protected operation...")
    print("   Lock released")
    print()

    # Cleanup
    print("CLEANUP:")
    print("-" * 40)
    cleaned = fs.cleanup_temp()
    print(f"   Cleaned up {cleaned} temp items")

    # Clean test directory
    fs.rmdir(temp_dir, recursive=True)
    print(f"   Removed temp directory")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - File System Manager Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())

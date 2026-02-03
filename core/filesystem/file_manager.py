#!/usr/bin/env python3
"""
BAEL - File System Manager
Comprehensive async file system operations.

This module provides powerful file system management
capabilities for BAEL's storage needs.

Features:
- Async file operations
- File watching
- Directory traversal
- File compression
- Atomic writes
- File locking
- Checksums
- Temporary files
- Path utilities
- Glob patterns
"""

import asyncio
import gzip
import hashlib
import json
import logging
import os
import shutil
import stat
import tempfile
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from typing import (Any, AsyncIterator, Awaitable, Callable, Dict, Iterator,
                    List, Optional, Set, Tuple, Union)

logger = logging.getLogger(__name__)


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


class CompressionType(Enum):
    """Compression types."""
    NONE = "none"
    GZIP = "gzip"
    ZIP = "zip"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class FileInfo:
    """File information."""
    path: Path
    name: str
    file_type: FileType
    size: int = 0
    created_at: float = 0
    modified_at: float = 0
    accessed_at: float = 0
    permissions: int = 0
    owner: str = ""
    is_hidden: bool = False
    extension: str = ""

    @classmethod
    def from_path(cls, path: Path) -> 'FileInfo':
        stat_result = path.stat() if path.exists() else None

        if stat_result:
            file_type = FileType.DIRECTORY if path.is_dir() else FileType.FILE
            if path.is_symlink():
                file_type = FileType.SYMLINK

            return cls(
                path=path,
                name=path.name,
                file_type=file_type,
                size=stat_result.st_size if file_type == FileType.FILE else 0,
                created_at=stat_result.st_ctime,
                modified_at=stat_result.st_mtime,
                accessed_at=stat_result.st_atime,
                permissions=stat_result.st_mode,
                is_hidden=path.name.startswith('.'),
                extension=path.suffix.lower() if file_type == FileType.FILE else ""
            )

        return cls(
            path=path,
            name=path.name,
            file_type=FileType.UNKNOWN
        )

    @property
    def size_human(self) -> str:
        """Human-readable size."""
        size = self.size
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} PB"


@dataclass
class WatchNotification:
    """File watch notification."""
    event: WatchEvent
    path: Path
    old_path: Optional[Path] = None
    timestamp: float = field(default_factory=time.time)


@dataclass
class FileStats:
    """File system operation statistics."""
    files_read: int = 0
    files_written: int = 0
    bytes_read: int = 0
    bytes_written: int = 0
    directories_created: int = 0
    files_deleted: int = 0
    errors: int = 0


# =============================================================================
# FILE LOCK
# =============================================================================

class FileLock:
    """Simple async file lock."""

    def __init__(self, path: Path):
        self.path = path
        self.lock_path = path.with_suffix(path.suffix + ".lock")
        self._lock = asyncio.Lock()

    async def acquire(self, timeout: float = 10.0) -> bool:
        """Acquire the lock."""
        start = time.time()

        while True:
            async with self._lock:
                if not self.lock_path.exists():
                    self.lock_path.write_text(str(os.getpid()))
                    return True

            if time.time() - start > timeout:
                return False

            await asyncio.sleep(0.1)

    async def release(self) -> None:
        """Release the lock."""
        async with self._lock:
            if self.lock_path.exists():
                self.lock_path.unlink()

    async def __aenter__(self) -> 'FileLock':
        await self.acquire()
        return self

    async def __aexit__(self, *args) -> None:
        await self.release()


# =============================================================================
# FILE WATCHER
# =============================================================================

class FileWatcher:
    """Watches files and directories for changes."""

    def __init__(self, path: Path, recursive: bool = True):
        self.path = Path(path)
        self.recursive = recursive
        self.handlers: List[Callable[[WatchNotification], Awaitable[None]]] = []
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._snapshot: Dict[Path, float] = {}

    def on_change(
        self,
        handler: Callable[[WatchNotification], Awaitable[None]]
    ) -> 'FileWatcher':
        """Register change handler."""
        self.handlers.append(handler)
        return self

    async def start(self, poll_interval: float = 1.0) -> None:
        """Start watching."""
        if self._running:
            return

        self._running = True
        self._snapshot = self._take_snapshot()
        self._task = asyncio.create_task(self._watch_loop(poll_interval))

    async def stop(self) -> None:
        """Stop watching."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _watch_loop(self, interval: float) -> None:
        """Main watch loop."""
        while self._running:
            try:
                new_snapshot = self._take_snapshot()

                # Find changes
                old_paths = set(self._snapshot.keys())
                new_paths = set(new_snapshot.keys())

                # Created files
                for path in new_paths - old_paths:
                    await self._notify(WatchNotification(
                        event=WatchEvent.CREATED,
                        path=path
                    ))

                # Deleted files
                for path in old_paths - new_paths:
                    await self._notify(WatchNotification(
                        event=WatchEvent.DELETED,
                        path=path
                    ))

                # Modified files
                for path in old_paths & new_paths:
                    if self._snapshot[path] != new_snapshot[path]:
                        await self._notify(WatchNotification(
                            event=WatchEvent.MODIFIED,
                            path=path
                        ))

                self._snapshot = new_snapshot

            except Exception as e:
                logger.error(f"Watch error: {e}")

            await asyncio.sleep(interval)

    def _take_snapshot(self) -> Dict[Path, float]:
        """Take snapshot of file modification times."""
        snapshot = {}

        if not self.path.exists():
            return snapshot

        if self.path.is_file():
            snapshot[self.path] = self.path.stat().st_mtime
        else:
            if self.recursive:
                for path in self.path.rglob("*"):
                    if path.is_file():
                        snapshot[path] = path.stat().st_mtime
            else:
                for path in self.path.glob("*"):
                    if path.is_file():
                        snapshot[path] = path.stat().st_mtime

        return snapshot

    async def _notify(self, notification: WatchNotification) -> None:
        """Notify handlers."""
        for handler in self.handlers:
            try:
                await handler(notification)
            except Exception as e:
                logger.error(f"Handler error: {e}")


# =============================================================================
# FILE OPERATIONS
# =============================================================================

class FileOperations:
    """Core file operations."""

    def __init__(self):
        self.stats = FileStats()

    async def read_text(
        self,
        path: Path,
        encoding: str = "utf-8"
    ) -> str:
        """Read text file."""
        path = Path(path)

        try:
            content = await asyncio.to_thread(path.read_text, encoding)
            self.stats.files_read += 1
            self.stats.bytes_read += len(content.encode(encoding))
            return content
        except Exception as e:
            self.stats.errors += 1
            raise

    async def read_bytes(self, path: Path) -> bytes:
        """Read binary file."""
        path = Path(path)

        try:
            content = await asyncio.to_thread(path.read_bytes)
            self.stats.files_read += 1
            self.stats.bytes_read += len(content)
            return content
        except Exception as e:
            self.stats.errors += 1
            raise

    async def read_json(self, path: Path) -> Any:
        """Read JSON file."""
        content = await self.read_text(path)
        return json.loads(content)

    async def write_text(
        self,
        path: Path,
        content: str,
        encoding: str = "utf-8",
        atomic: bool = True
    ) -> None:
        """Write text file."""
        path = Path(path)

        try:
            if atomic:
                await self._atomic_write(path, content.encode(encoding))
            else:
                await asyncio.to_thread(path.write_text, content, encoding)

            self.stats.files_written += 1
            self.stats.bytes_written += len(content.encode(encoding))
        except Exception as e:
            self.stats.errors += 1
            raise

    async def write_bytes(
        self,
        path: Path,
        content: bytes,
        atomic: bool = True
    ) -> None:
        """Write binary file."""
        path = Path(path)

        try:
            if atomic:
                await self._atomic_write(path, content)
            else:
                await asyncio.to_thread(path.write_bytes, content)

            self.stats.files_written += 1
            self.stats.bytes_written += len(content)
        except Exception as e:
            self.stats.errors += 1
            raise

    async def write_json(
        self,
        path: Path,
        data: Any,
        indent: int = 2,
        atomic: bool = True
    ) -> None:
        """Write JSON file."""
        content = json.dumps(data, indent=indent, ensure_ascii=False)
        await self.write_text(path, content, atomic=atomic)

    async def _atomic_write(self, path: Path, content: bytes) -> None:
        """Write file atomically using temp file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        temp_path = path.with_suffix(path.suffix + ".tmp")

        try:
            await asyncio.to_thread(temp_path.write_bytes, content)
            await asyncio.to_thread(shutil.move, str(temp_path), str(path))
        except Exception:
            if temp_path.exists():
                temp_path.unlink()
            raise

    async def append_text(
        self,
        path: Path,
        content: str,
        encoding: str = "utf-8"
    ) -> None:
        """Append to text file."""
        path = Path(path)

        def _append():
            with open(path, "a", encoding=encoding) as f:
                f.write(content)

        await asyncio.to_thread(_append)
        self.stats.bytes_written += len(content.encode(encoding))

    async def copy(
        self,
        src: Path,
        dst: Path,
        overwrite: bool = False
    ) -> None:
        """Copy file or directory."""
        src, dst = Path(src), Path(dst)

        if dst.exists() and not overwrite:
            raise FileExistsError(f"Destination exists: {dst}")

        if src.is_dir():
            await asyncio.to_thread(
                shutil.copytree,
                str(src),
                str(dst),
                dirs_exist_ok=overwrite
            )
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            await asyncio.to_thread(shutil.copy2, str(src), str(dst))

    async def move(
        self,
        src: Path,
        dst: Path,
        overwrite: bool = False
    ) -> None:
        """Move file or directory."""
        src, dst = Path(src), Path(dst)

        if dst.exists() and not overwrite:
            raise FileExistsError(f"Destination exists: {dst}")

        dst.parent.mkdir(parents=True, exist_ok=True)
        await asyncio.to_thread(shutil.move, str(src), str(dst))

    async def delete(self, path: Path, recursive: bool = False) -> None:
        """Delete file or directory."""
        path = Path(path)

        if not path.exists():
            return

        if path.is_dir():
            if recursive:
                await asyncio.to_thread(shutil.rmtree, str(path))
            else:
                await asyncio.to_thread(path.rmdir)
        else:
            await asyncio.to_thread(path.unlink)

        self.stats.files_deleted += 1

    async def mkdir(
        self,
        path: Path,
        parents: bool = True,
        exist_ok: bool = True
    ) -> None:
        """Create directory."""
        path = Path(path)
        await asyncio.to_thread(path.mkdir, parents=parents, exist_ok=exist_ok)
        self.stats.directories_created += 1

    async def exists(self, path: Path) -> bool:
        """Check if path exists."""
        return Path(path).exists()

    async def is_file(self, path: Path) -> bool:
        """Check if path is a file."""
        return Path(path).is_file()

    async def is_dir(self, path: Path) -> bool:
        """Check if path is a directory."""
        return Path(path).is_dir()

    async def get_info(self, path: Path) -> FileInfo:
        """Get file information."""
        return FileInfo.from_path(Path(path))

    async def list_dir(
        self,
        path: Path,
        pattern: str = "*",
        recursive: bool = False
    ) -> List[FileInfo]:
        """List directory contents."""
        path = Path(path)

        if recursive:
            paths = list(path.rglob(pattern))
        else:
            paths = list(path.glob(pattern))

        return [FileInfo.from_path(p) for p in paths]

    async def find_files(
        self,
        path: Path,
        pattern: str = "*",
        file_type: FileType = None
    ) -> List[Path]:
        """Find files matching pattern."""
        path = Path(path)
        results = []

        for p in path.rglob(pattern):
            if file_type is None:
                results.append(p)
            elif file_type == FileType.FILE and p.is_file():
                results.append(p)
            elif file_type == FileType.DIRECTORY and p.is_dir():
                results.append(p)

        return results

    async def checksum(
        self,
        path: Path,
        algorithm: str = "sha256"
    ) -> str:
        """Calculate file checksum."""
        path = Path(path)

        def _calc_hash():
            hasher = hashlib.new(algorithm)
            with open(path, "rb") as f:
                while chunk := f.read(8192):
                    hasher.update(chunk)
            return hasher.hexdigest()

        return await asyncio.to_thread(_calc_hash)

    async def compress_gzip(self, path: Path, output: Path = None) -> Path:
        """Compress file with gzip."""
        path = Path(path)
        output = output or path.with_suffix(path.suffix + ".gz")

        def _compress():
            with open(path, "rb") as f_in:
                with gzip.open(output, "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)

        await asyncio.to_thread(_compress)
        return output

    async def decompress_gzip(self, path: Path, output: Path = None) -> Path:
        """Decompress gzip file."""
        path = Path(path)
        output = output or path.with_suffix("")

        def _decompress():
            with gzip.open(path, "rb") as f_in:
                with open(output, "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)

        await asyncio.to_thread(_decompress)
        return output

    async def temp_file(
        self,
        suffix: str = "",
        prefix: str = "bael_",
        content: bytes = None
    ) -> Path:
        """Create temporary file."""
        fd, path = tempfile.mkstemp(suffix=suffix, prefix=prefix)
        os.close(fd)

        path = Path(path)

        if content:
            await self.write_bytes(path, content, atomic=False)

        return path

    async def temp_dir(self, prefix: str = "bael_") -> Path:
        """Create temporary directory."""
        path = tempfile.mkdtemp(prefix=prefix)
        return Path(path)


# =============================================================================
# FILE SYSTEM MANAGER
# =============================================================================

class FileSystemManager:
    """
    Master file system manager for BAEL.
    """

    def __init__(self, base_path: Path = None):
        self.base_path = Path(base_path) if base_path else Path.cwd()
        self.ops = FileOperations()
        self.watchers: Dict[str, FileWatcher] = {}

    def _resolve(self, path: Union[str, Path]) -> Path:
        """Resolve path relative to base."""
        path = Path(path)
        if not path.is_absolute():
            path = self.base_path / path
        return path

    async def read(
        self,
        path: Union[str, Path],
        encoding: str = "utf-8"
    ) -> str:
        """Read text file."""
        return await self.ops.read_text(self._resolve(path), encoding)

    async def read_bytes(self, path: Union[str, Path]) -> bytes:
        """Read binary file."""
        return await self.ops.read_bytes(self._resolve(path))

    async def read_json(self, path: Union[str, Path]) -> Any:
        """Read JSON file."""
        return await self.ops.read_json(self._resolve(path))

    async def write(
        self,
        path: Union[str, Path],
        content: str,
        encoding: str = "utf-8",
        atomic: bool = True
    ) -> None:
        """Write text file."""
        await self.ops.write_text(self._resolve(path), content, encoding, atomic)

    async def write_bytes(
        self,
        path: Union[str, Path],
        content: bytes,
        atomic: bool = True
    ) -> None:
        """Write binary file."""
        await self.ops.write_bytes(self._resolve(path), content, atomic)

    async def write_json(
        self,
        path: Union[str, Path],
        data: Any,
        indent: int = 2
    ) -> None:
        """Write JSON file."""
        await self.ops.write_json(self._resolve(path), data, indent)

    async def append(
        self,
        path: Union[str, Path],
        content: str
    ) -> None:
        """Append to file."""
        await self.ops.append_text(self._resolve(path), content)

    async def copy(
        self,
        src: Union[str, Path],
        dst: Union[str, Path],
        overwrite: bool = False
    ) -> None:
        """Copy file or directory."""
        await self.ops.copy(
            self._resolve(src),
            self._resolve(dst),
            overwrite
        )

    async def move(
        self,
        src: Union[str, Path],
        dst: Union[str, Path],
        overwrite: bool = False
    ) -> None:
        """Move file or directory."""
        await self.ops.move(
            self._resolve(src),
            self._resolve(dst),
            overwrite
        )

    async def delete(
        self,
        path: Union[str, Path],
        recursive: bool = False
    ) -> None:
        """Delete file or directory."""
        await self.ops.delete(self._resolve(path), recursive)

    async def mkdir(self, path: Union[str, Path]) -> None:
        """Create directory."""
        await self.ops.mkdir(self._resolve(path))

    async def exists(self, path: Union[str, Path]) -> bool:
        """Check if path exists."""
        return await self.ops.exists(self._resolve(path))

    async def info(self, path: Union[str, Path]) -> FileInfo:
        """Get file info."""
        return await self.ops.get_info(self._resolve(path))

    async def list(
        self,
        path: Union[str, Path] = ".",
        pattern: str = "*",
        recursive: bool = False
    ) -> List[FileInfo]:
        """List directory."""
        return await self.ops.list_dir(
            self._resolve(path),
            pattern,
            recursive
        )

    async def find(
        self,
        pattern: str = "*",
        path: Union[str, Path] = ".",
        file_type: FileType = None
    ) -> List[Path]:
        """Find files."""
        return await self.ops.find_files(
            self._resolve(path),
            pattern,
            file_type
        )

    async def checksum(
        self,
        path: Union[str, Path],
        algorithm: str = "sha256"
    ) -> str:
        """Calculate checksum."""
        return await self.ops.checksum(self._resolve(path), algorithm)

    async def compress(
        self,
        path: Union[str, Path],
        output: Union[str, Path] = None
    ) -> Path:
        """Compress file."""
        return await self.ops.compress_gzip(
            self._resolve(path),
            self._resolve(output) if output else None
        )

    async def decompress(
        self,
        path: Union[str, Path],
        output: Union[str, Path] = None
    ) -> Path:
        """Decompress file."""
        return await self.ops.decompress_gzip(
            self._resolve(path),
            self._resolve(output) if output else None
        )

    async def lock(self, path: Union[str, Path]) -> FileLock:
        """Get file lock."""
        return FileLock(self._resolve(path))

    def watch(
        self,
        path: Union[str, Path],
        name: str = None,
        recursive: bool = True
    ) -> FileWatcher:
        """Create file watcher."""
        watcher = FileWatcher(self._resolve(path), recursive)

        if name:
            self.watchers[name] = watcher

        return watcher

    async def temp_file(
        self,
        suffix: str = "",
        content: bytes = None
    ) -> Path:
        """Create temp file."""
        return await self.ops.temp_file(suffix=suffix, content=content)

    async def temp_dir(self) -> Path:
        """Create temp directory."""
        return await self.ops.temp_dir()

    def get_stats(self) -> FileStats:
        """Get statistics."""
        return self.ops.stats


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the File System Manager."""
    print("=" * 70)
    print("BAEL - FILE SYSTEM MANAGER DEMO")
    print("Comprehensive Async File Operations")
    print("=" * 70)
    print()

    # Create temp directory for demo
    demo_dir = Path(tempfile.mkdtemp(prefix="bael_fs_demo_"))
    manager = FileSystemManager(demo_dir)

    try:
        # 1. Create Directory
        print("1. CREATE DIRECTORY:")
        print("-" * 40)

        await manager.mkdir("data/subdir")
        print(f"   Created: {demo_dir}/data/subdir")
        print()

        # 2. Write Files
        print("2. WRITE FILES:")
        print("-" * 40)

        await manager.write("test.txt", "Hello, BAEL!")
        print("   Written: test.txt")

        await manager.write_json("config.json", {
            "name": "BAEL",
            "version": "1.0.0",
            "features": ["ai", "agents", "automation"]
        })
        print("   Written: config.json")

        await manager.write_bytes("binary.dat", b"\x00\x01\x02\x03\x04")
        print("   Written: binary.dat")
        print()

        # 3. Read Files
        print("3. READ FILES:")
        print("-" * 40)

        content = await manager.read("test.txt")
        print(f"   test.txt: {content}")

        config = await manager.read_json("config.json")
        print(f"   config.json: {config}")

        binary = await manager.read_bytes("binary.dat")
        print(f"   binary.dat: {binary.hex()}")
        print()

        # 4. File Info
        print("4. FILE INFO:")
        print("-" * 40)

        info = await manager.info("test.txt")
        print(f"   File: {info.name}")
        print(f"   Type: {info.file_type.value}")
        print(f"   Size: {info.size_human}")
        print(f"   Extension: {info.extension}")
        print()

        # 5. List Directory
        print("5. LIST DIRECTORY:")
        print("-" * 40)

        files = await manager.list(".", recursive=True)
        print(f"   Found {len(files)} items:")
        for f in files:
            print(f"     {f.file_type.value}: {f.name} ({f.size_human})")
        print()

        # 6. Find Files
        print("6. FIND FILES:")
        print("-" * 40)

        json_files = await manager.find("*.json")
        print(f"   JSON files: {[f.name for f in json_files]}")

        all_files = await manager.find("*", file_type=FileType.FILE)
        print(f"   All files: {[f.name for f in all_files]}")
        print()

        # 7. Append to File
        print("7. APPEND TO FILE:")
        print("-" * 40)

        await manager.append("test.txt", "\nAppended line!")
        content = await manager.read("test.txt")
        print(f"   After append: {repr(content)}")
        print()

        # 8. Copy and Move
        print("8. COPY AND MOVE:")
        print("-" * 40)

        await manager.copy("test.txt", "test_copy.txt")
        print("   Copied: test.txt -> test_copy.txt")

        await manager.move("test_copy.txt", "data/test_moved.txt")
        print("   Moved: test_copy.txt -> data/test_moved.txt")

        exists_copy = await manager.exists("test_copy.txt")
        exists_moved = await manager.exists("data/test_moved.txt")
        print(f"   Original exists: {exists_copy}, Moved exists: {exists_moved}")
        print()

        # 9. Checksum
        print("9. CHECKSUM:")
        print("-" * 40)

        sha256 = await manager.checksum("test.txt", "sha256")
        md5 = await manager.checksum("test.txt", "md5")
        print(f"   SHA256: {sha256[:32]}...")
        print(f"   MD5: {md5}")
        print()

        # 10. Compression
        print("10. COMPRESSION:")
        print("-" * 40)

        compressed = await manager.compress("test.txt")
        print(f"   Compressed: {compressed.name}")

        original_info = await manager.info("test.txt")
        compressed_info = await manager.info(compressed)
        print(f"   Original size: {original_info.size} bytes")
        print(f"   Compressed size: {compressed_info.size} bytes")
        print()

        # 11. File Locking
        print("11. FILE LOCKING:")
        print("-" * 40)

        lock = await manager.lock("test.txt")
        async with lock:
            print("   Lock acquired")
            await asyncio.sleep(0.1)
        print("   Lock released")
        print()

        # 12. Temporary Files
        print("12. TEMPORARY FILES:")
        print("-" * 40)

        temp_file = await manager.temp_file(suffix=".tmp", content=b"temp data")
        print(f"   Temp file: {temp_file}")

        temp_dir = await manager.temp_dir()
        print(f"   Temp dir: {temp_dir}")
        print()

        # 13. File Watcher (quick demo)
        print("13. FILE WATCHER:")
        print("-" * 40)

        notifications = []

        async def on_change(notification: WatchNotification):
            notifications.append(notification)

        watcher = manager.watch(".", recursive=True)
        watcher.on_change(on_change)

        await watcher.start(poll_interval=0.2)
        print("   Watcher started")

        # Create a file to trigger event
        await manager.write("watched.txt", "New file!")
        await asyncio.sleep(0.5)

        await watcher.stop()
        print(f"   Watcher stopped, captured {len(notifications)} events")
        print()

        # 14. Delete Files
        print("14. DELETE FILES:")
        print("-" * 40)

        await manager.delete("test.txt")
        print("   Deleted: test.txt")

        await manager.delete("data", recursive=True)
        print("   Deleted: data/ (recursive)")
        print()

        # 15. Statistics
        print("15. STATISTICS:")
        print("-" * 40)

        stats = manager.get_stats()
        print(f"    Files read: {stats.files_read}")
        print(f"    Files written: {stats.files_written}")
        print(f"    Bytes read: {stats.bytes_read}")
        print(f"    Bytes written: {stats.bytes_written}")
        print(f"    Directories created: {stats.directories_created}")
        print(f"    Files deleted: {stats.files_deleted}")
        print()

    finally:
        # Cleanup demo directory
        shutil.rmtree(demo_dir, ignore_errors=True)

    print("=" * 70)
    print("DEMO COMPLETE - File System Manager Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())

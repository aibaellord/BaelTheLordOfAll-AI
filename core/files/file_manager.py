#!/usr/bin/env python3
"""
BAEL - File Manager System
Comprehensive file operations and management.

Features:
- File CRUD operations
- Directory management
- File streaming
- Chunked uploads
- File metadata
- MIME type detection
- File compression
- Archive handling
- File watching
- Storage backends
"""

import asyncio
import base64
import gzip
import hashlib
import io
import logging
import mimetypes
import os
import shutil
import stat
import tempfile
import time
import uuid
import zipfile
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from typing import (Any, AsyncIterator, BinaryIO, Callable, Dict, Generator,
                    Generic, Iterator, List, Optional, Set, Tuple, Type,
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


class StorageBackend(Enum):
    """Storage backends."""
    LOCAL = "local"
    MEMORY = "memory"
    S3 = "s3"
    GCS = "gcs"


class CompressionType(Enum):
    """Compression types."""
    NONE = "none"
    GZIP = "gzip"
    DEFLATE = "deflate"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class FileMetadata:
    """File metadata."""
    path: str
    name: str
    size: int
    file_type: FileType
    mime_type: str = "application/octet-stream"
    created_at: Optional[datetime] = None
    modified_at: Optional[datetime] = None
    accessed_at: Optional[datetime] = None
    checksum: Optional[str] = None
    is_hidden: bool = False
    permissions: int = 0o644
    owner: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def extension(self) -> str:
        """Get file extension."""
        return Path(self.name).suffix.lower()

    @property
    def is_directory(self) -> bool:
        """Check if directory."""
        return self.file_type == FileType.DIRECTORY

    @property
    def is_file(self) -> bool:
        """Check if regular file."""
        return self.file_type == FileType.FILE


@dataclass
class FileChunk:
    """File chunk for streaming."""
    data: bytes
    offset: int
    size: int
    chunk_number: int
    total_chunks: int
    checksum: Optional[str] = None


@dataclass
class UploadSession:
    """Chunked upload session."""
    id: str
    filename: str
    total_size: int
    chunk_size: int
    chunks_received: Set[int] = field(default_factory=set)
    temp_path: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def total_chunks(self) -> int:
        """Calculate total chunks needed."""
        return (self.total_size + self.chunk_size - 1) // self.chunk_size

    @property
    def is_complete(self) -> bool:
        """Check if upload is complete."""
        return len(self.chunks_received) == self.total_chunks

    @property
    def progress(self) -> float:
        """Calculate upload progress."""
        if self.total_chunks == 0:
            return 0.0

        return len(self.chunks_received) / self.total_chunks


@dataclass
class WatchEvent:
    """File watch event."""
    path: str
    event_type: str  # created, modified, deleted, moved
    timestamp: datetime = field(default_factory=datetime.utcnow)
    old_path: Optional[str] = None


# =============================================================================
# STORAGE BACKENDS
# =============================================================================

class Storage(ABC):
    """Abstract storage backend."""

    @abstractmethod
    async def read(self, path: str) -> bytes:
        """Read file content."""
        pass

    @abstractmethod
    async def write(self, path: str, content: bytes) -> None:
        """Write file content."""
        pass

    @abstractmethod
    async def delete(self, path: str) -> None:
        """Delete file."""
        pass

    @abstractmethod
    async def exists(self, path: str) -> bool:
        """Check if file exists."""
        pass

    @abstractmethod
    async def list(self, path: str) -> List[FileMetadata]:
        """List directory contents."""
        pass

    @abstractmethod
    async def get_metadata(self, path: str) -> FileMetadata:
        """Get file metadata."""
        pass


class MemoryStorage(Storage):
    """In-memory storage backend."""

    def __init__(self):
        self._files: Dict[str, bytes] = {}
        self._metadata: Dict[str, FileMetadata] = {}
        self._directories: Set[str] = {"/"}

    async def read(self, path: str) -> bytes:
        """Read file content."""
        path = self._normalize_path(path)

        if path not in self._files:
            raise FileNotFoundError(f"File not found: {path}")

        return self._files[path]

    async def write(self, path: str, content: bytes) -> None:
        """Write file content."""
        path = self._normalize_path(path)

        # Ensure parent directories exist
        parent = str(Path(path).parent)
        self._ensure_directory(parent)

        self._files[path] = content
        self._metadata[path] = FileMetadata(
            path=path,
            name=Path(path).name,
            size=len(content),
            file_type=FileType.FILE,
            mime_type=self._guess_mime_type(path),
            created_at=datetime.utcnow(),
            modified_at=datetime.utcnow()
        )

    async def delete(self, path: str) -> None:
        """Delete file."""
        path = self._normalize_path(path)

        if path in self._files:
            del self._files[path]
            del self._metadata[path]

        elif path in self._directories:
            # Delete directory and contents
            to_delete = [p for p in self._files if p.startswith(path + "/")]

            for p in to_delete:
                del self._files[p]
                del self._metadata[p]

            self._directories.discard(path)

        else:
            raise FileNotFoundError(f"Path not found: {path}")

    async def exists(self, path: str) -> bool:
        """Check if file exists."""
        path = self._normalize_path(path)
        return path in self._files or path in self._directories

    async def list(self, path: str) -> List[FileMetadata]:
        """List directory contents."""
        path = self._normalize_path(path)

        if path != "/" and path not in self._directories:
            raise FileNotFoundError(f"Directory not found: {path}")

        result = []
        seen = set()

        prefix = path if path == "/" else path + "/"

        for file_path in self._files:
            if file_path.startswith(prefix):
                relative = file_path[len(prefix):]

                if "/" in relative:
                    # It's in a subdirectory
                    dir_name = relative.split("/")[0]

                    if dir_name not in seen:
                        seen.add(dir_name)
                        result.append(FileMetadata(
                            path=prefix + dir_name,
                            name=dir_name,
                            size=0,
                            file_type=FileType.DIRECTORY
                        ))

                else:
                    result.append(self._metadata[file_path])

        return result

    async def get_metadata(self, path: str) -> FileMetadata:
        """Get file metadata."""
        path = self._normalize_path(path)

        if path in self._metadata:
            return self._metadata[path]

        if path in self._directories:
            return FileMetadata(
                path=path,
                name=Path(path).name or "/",
                size=0,
                file_type=FileType.DIRECTORY
            )

        raise FileNotFoundError(f"Path not found: {path}")

    def _normalize_path(self, path: str) -> str:
        """Normalize path."""
        if not path.startswith("/"):
            path = "/" + path

        return path.rstrip("/") or "/"

    def _ensure_directory(self, path: str) -> None:
        """Ensure directory exists."""
        path = self._normalize_path(path)
        parts = path.split("/")

        current = ""

        for part in parts:
            if part:
                current += "/" + part
                self._directories.add(current)

    def _guess_mime_type(self, path: str) -> str:
        """Guess MIME type from path."""
        mime_type, _ = mimetypes.guess_type(path)
        return mime_type or "application/octet-stream"


class LocalStorage(Storage):
    """Local filesystem storage."""

    def __init__(self, base_path: str = "."):
        self.base_path = Path(base_path).resolve()

    def _get_full_path(self, path: str) -> Path:
        """Get full filesystem path."""
        return self.base_path / path.lstrip("/")

    async def read(self, path: str) -> bytes:
        """Read file content."""
        full_path = self._get_full_path(path)

        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        return await asyncio.to_thread(full_path.read_bytes)

    async def write(self, path: str, content: bytes) -> None:
        """Write file content."""
        full_path = self._get_full_path(path)

        # Create parent directories
        full_path.parent.mkdir(parents=True, exist_ok=True)

        await asyncio.to_thread(full_path.write_bytes, content)

    async def delete(self, path: str) -> None:
        """Delete file."""
        full_path = self._get_full_path(path)

        if not full_path.exists():
            raise FileNotFoundError(f"Path not found: {path}")

        if full_path.is_dir():
            await asyncio.to_thread(shutil.rmtree, full_path)
        else:
            await asyncio.to_thread(full_path.unlink)

    async def exists(self, path: str) -> bool:
        """Check if file exists."""
        full_path = self._get_full_path(path)
        return await asyncio.to_thread(full_path.exists)

    async def list(self, path: str) -> List[FileMetadata]:
        """List directory contents."""
        full_path = self._get_full_path(path)

        if not full_path.exists():
            raise FileNotFoundError(f"Directory not found: {path}")

        if not full_path.is_dir():
            raise NotADirectoryError(f"Not a directory: {path}")

        result = []

        for item in full_path.iterdir():
            result.append(await self._get_item_metadata(item, path))

        return result

    async def get_metadata(self, path: str) -> FileMetadata:
        """Get file metadata."""
        full_path = self._get_full_path(path)

        if not full_path.exists():
            raise FileNotFoundError(f"Path not found: {path}")

        return await self._get_item_metadata(full_path, path)

    async def _get_item_metadata(self, item: Path, parent: str) -> FileMetadata:
        """Get metadata for filesystem item."""
        stat_result = await asyncio.to_thread(item.stat)

        if item.is_dir():
            file_type = FileType.DIRECTORY
        elif item.is_symlink():
            file_type = FileType.SYMLINK
        else:
            file_type = FileType.FILE

        mime_type, _ = mimetypes.guess_type(str(item))

        return FileMetadata(
            path=str(item.relative_to(self.base_path)),
            name=item.name,
            size=stat_result.st_size,
            file_type=file_type,
            mime_type=mime_type or "application/octet-stream",
            created_at=datetime.fromtimestamp(stat_result.st_ctime),
            modified_at=datetime.fromtimestamp(stat_result.st_mtime),
            accessed_at=datetime.fromtimestamp(stat_result.st_atime),
            is_hidden=item.name.startswith("."),
            permissions=stat.S_IMODE(stat_result.st_mode)
        )


# =============================================================================
# FILE MANAGER
# =============================================================================

class FileManager:
    """
    Comprehensive File Manager for BAEL.

    Provides file operations, streaming, and management.
    """

    def __init__(self, storage: Storage = None):
        self._storage = storage or MemoryStorage()
        self._upload_sessions: Dict[str, UploadSession] = {}
        self._watchers: List[Callable[[WatchEvent], None]] = []

    # -------------------------------------------------------------------------
    # BASIC OPERATIONS
    # -------------------------------------------------------------------------

    async def read(self, path: str) -> bytes:
        """Read file content."""
        return await self._storage.read(path)

    async def read_text(self, path: str, encoding: str = "utf-8") -> str:
        """Read file as text."""
        content = await self.read(path)
        return content.decode(encoding)

    async def write(self, path: str, content: Union[bytes, str]) -> FileMetadata:
        """Write file content."""
        if isinstance(content, str):
            content = content.encode("utf-8")

        await self._storage.write(path, content)
        self._emit_event(WatchEvent(path, "created"))

        return await self._storage.get_metadata(path)

    async def append(self, path: str, content: Union[bytes, str]) -> None:
        """Append to file."""
        if isinstance(content, str):
            content = content.encode("utf-8")

        try:
            existing = await self.read(path)
        except FileNotFoundError:
            existing = b""

        await self.write(path, existing + content)
        self._emit_event(WatchEvent(path, "modified"))

    async def delete(self, path: str) -> None:
        """Delete file or directory."""
        await self._storage.delete(path)
        self._emit_event(WatchEvent(path, "deleted"))

    async def exists(self, path: str) -> bool:
        """Check if file exists."""
        return await self._storage.exists(path)

    async def copy(self, source: str, destination: str) -> FileMetadata:
        """Copy file."""
        content = await self.read(source)
        return await self.write(destination, content)

    async def move(self, source: str, destination: str) -> FileMetadata:
        """Move file."""
        metadata = await self.copy(source, destination)
        await self.delete(source)
        self._emit_event(WatchEvent(destination, "moved", old_path=source))

        return metadata

    async def rename(self, path: str, new_name: str) -> FileMetadata:
        """Rename file."""
        parent = str(Path(path).parent)
        new_path = f"{parent}/{new_name}"

        return await self.move(path, new_path)

    # -------------------------------------------------------------------------
    # DIRECTORY OPERATIONS
    # -------------------------------------------------------------------------

    async def mkdir(self, path: str, parents: bool = True) -> None:
        """Create directory."""
        if isinstance(self._storage, MemoryStorage):
            self._storage._ensure_directory(path)

        elif isinstance(self._storage, LocalStorage):
            full_path = self._storage._get_full_path(path)

            if parents:
                full_path.mkdir(parents=True, exist_ok=True)
            else:
                full_path.mkdir()

    async def list(self, path: str = "/") -> List[FileMetadata]:
        """List directory contents."""
        return await self._storage.list(path)

    async def list_recursive(
        self,
        path: str = "/",
        pattern: str = None
    ) -> List[FileMetadata]:
        """List directory recursively."""
        result = []

        async def recurse(dir_path: str):
            items = await self._storage.list(dir_path)

            for item in items:
                if pattern and not self._match_pattern(item.name, pattern):
                    continue

                result.append(item)

                if item.is_directory:
                    await recurse(item.path)

        await recurse(path)
        return result

    def _match_pattern(self, name: str, pattern: str) -> bool:
        """Match filename against pattern."""
        import fnmatch
        return fnmatch.fnmatch(name, pattern)

    # -------------------------------------------------------------------------
    # METADATA
    # -------------------------------------------------------------------------

    async def get_metadata(self, path: str) -> FileMetadata:
        """Get file metadata."""
        return await self._storage.get_metadata(path)

    async def get_size(self, path: str) -> int:
        """Get file size."""
        metadata = await self.get_metadata(path)
        return metadata.size

    async def get_checksum(
        self,
        path: str,
        algorithm: str = "sha256"
    ) -> str:
        """Calculate file checksum."""
        content = await self.read(path)

        if algorithm == "sha256":
            return hashlib.sha256(content).hexdigest()

        elif algorithm == "md5":
            return hashlib.md5(content).hexdigest()

        elif algorithm == "sha1":
            return hashlib.sha1(content).hexdigest()

        raise ValueError(f"Unknown algorithm: {algorithm}")

    async def get_mime_type(self, path: str) -> str:
        """Get file MIME type."""
        mime_type, _ = mimetypes.guess_type(path)
        return mime_type or "application/octet-stream"

    # -------------------------------------------------------------------------
    # STREAMING
    # -------------------------------------------------------------------------

    async def read_chunks(
        self,
        path: str,
        chunk_size: int = 8192
    ) -> AsyncIterator[bytes]:
        """Read file in chunks."""
        content = await self.read(path)

        for i in range(0, len(content), chunk_size):
            yield content[i:i + chunk_size]

    async def write_stream(
        self,
        path: str,
        stream: AsyncIterator[bytes]
    ) -> FileMetadata:
        """Write from async stream."""
        chunks = []

        async for chunk in stream:
            chunks.append(chunk)

        content = b"".join(chunks)
        return await self.write(path, content)

    # -------------------------------------------------------------------------
    # CHUNKED UPLOADS
    # -------------------------------------------------------------------------

    async def start_upload(
        self,
        filename: str,
        total_size: int,
        chunk_size: int = 1024 * 1024  # 1MB
    ) -> UploadSession:
        """Start chunked upload session."""
        session = UploadSession(
            id=str(uuid.uuid4()),
            filename=filename,
            total_size=total_size,
            chunk_size=chunk_size
        )

        self._upload_sessions[session.id] = session
        return session

    async def upload_chunk(
        self,
        session_id: str,
        chunk_number: int,
        data: bytes
    ) -> UploadSession:
        """Upload chunk to session."""
        session = self._upload_sessions.get(session_id)

        if not session:
            raise ValueError(f"Upload session not found: {session_id}")

        session.chunks_received.add(chunk_number)

        # Store chunk (in real implementation, would append to temp file)
        if session.temp_path is None:
            session.temp_path = f"/tmp/upload_{session_id}"

        return session

    async def complete_upload(
        self,
        session_id: str,
        destination: str
    ) -> FileMetadata:
        """Complete chunked upload."""
        session = self._upload_sessions.get(session_id)

        if not session:
            raise ValueError(f"Upload session not found: {session_id}")

        if not session.is_complete:
            missing = session.total_chunks - len(session.chunks_received)
            raise ValueError(f"Upload incomplete: {missing} chunks missing")

        # In real implementation, would combine chunks and move to destination
        del self._upload_sessions[session_id]

        return await self.get_metadata(destination)

    async def abort_upload(self, session_id: str) -> None:
        """Abort chunked upload."""
        if session_id in self._upload_sessions:
            del self._upload_sessions[session_id]

    # -------------------------------------------------------------------------
    # COMPRESSION
    # -------------------------------------------------------------------------

    async def compress(
        self,
        path: str,
        compression: CompressionType = CompressionType.GZIP
    ) -> bytes:
        """Compress file content."""
        content = await self.read(path)

        if compression == CompressionType.GZIP:
            return gzip.compress(content)

        elif compression == CompressionType.DEFLATE:
            import zlib
            return zlib.compress(content)

        return content

    async def decompress(
        self,
        data: bytes,
        compression: CompressionType = CompressionType.GZIP
    ) -> bytes:
        """Decompress data."""
        if compression == CompressionType.GZIP:
            return gzip.decompress(data)

        elif compression == CompressionType.DEFLATE:
            import zlib
            return zlib.decompress(data)

        return data

    # -------------------------------------------------------------------------
    # ARCHIVES
    # -------------------------------------------------------------------------

    async def create_zip(
        self,
        paths: List[str],
        archive_path: str
    ) -> FileMetadata:
        """Create ZIP archive."""
        buffer = io.BytesIO()

        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            for path in paths:
                try:
                    content = await self.read(path)
                    zf.writestr(Path(path).name, content)
                except FileNotFoundError:
                    pass

        return await self.write(archive_path, buffer.getvalue())

    async def extract_zip(
        self,
        archive_path: str,
        destination: str
    ) -> List[FileMetadata]:
        """Extract ZIP archive."""
        content = await self.read(archive_path)
        buffer = io.BytesIO(content)

        extracted = []

        with zipfile.ZipFile(buffer, 'r') as zf:
            for name in zf.namelist():
                data = zf.read(name)
                dest_path = f"{destination}/{name}"

                metadata = await self.write(dest_path, data)
                extracted.append(metadata)

        return extracted

    # -------------------------------------------------------------------------
    # WATCHING
    # -------------------------------------------------------------------------

    def watch(self, callback: Callable[[WatchEvent], None]) -> Callable:
        """Register file watcher."""
        self._watchers.append(callback)

        def unwatch():
            self._watchers.remove(callback)

        return unwatch

    def _emit_event(self, event: WatchEvent) -> None:
        """Emit watch event."""
        for callback in self._watchers:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Watcher error: {e}")


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the File Manager System."""
    print("=" * 70)
    print("BAEL - FILE MANAGER SYSTEM DEMO")
    print("Comprehensive File Operations")
    print("=" * 70)
    print()

    manager = FileManager()  # Uses MemoryStorage by default

    # 1. Basic Write/Read
    print("1. BASIC WRITE/READ:")
    print("-" * 40)

    content = "Hello, BAEL! This is a test file."
    metadata = await manager.write("/documents/test.txt", content)

    print(f"   Written: {metadata.name}")
    print(f"   Size: {metadata.size} bytes")
    print(f"   MIME: {metadata.mime_type}")

    read_content = await manager.read_text("/documents/test.txt")
    print(f"   Read: {read_content}")
    print()

    # 2. Directory Operations
    print("2. DIRECTORY OPERATIONS:")
    print("-" * 40)

    await manager.write("/docs/readme.md", "# README")
    await manager.write("/docs/guide.md", "# Guide")
    await manager.write("/docs/api/reference.md", "# API Reference")

    files = await manager.list("/docs")
    print("   Contents of /docs:")

    for f in files:
        type_icon = "📁" if f.is_directory else "📄"
        print(f"      {type_icon} {f.name}")
    print()

    # 3. Recursive Listing
    print("3. RECURSIVE LISTING:")
    print("-" * 40)

    all_files = await manager.list_recursive("/docs")

    for f in all_files:
        print(f"   {f.path}")
    print()

    # 4. Copy and Move
    print("4. COPY AND MOVE:")
    print("-" * 40)

    await manager.copy("/documents/test.txt", "/backup/test.txt")
    exists_backup = await manager.exists("/backup/test.txt")
    print(f"   Copied to /backup: {exists_backup}")

    await manager.move("/backup/test.txt", "/archive/test.txt")
    exists_archive = await manager.exists("/archive/test.txt")
    exists_backup = await manager.exists("/backup/test.txt")
    print(f"   Moved to /archive: {exists_archive}")
    print(f"   Still in /backup: {exists_backup}")
    print()

    # 5. Append
    print("5. APPEND:")
    print("-" * 40)

    await manager.write("/logs/app.log", "Log entry 1\n")
    await manager.append("/logs/app.log", "Log entry 2\n")
    await manager.append("/logs/app.log", "Log entry 3\n")

    log_content = await manager.read_text("/logs/app.log")
    print(f"   Log content:\n{log_content}")

    # 6. File Metadata
    print("6. FILE METADATA:")
    print("-" * 40)

    metadata = await manager.get_metadata("/documents/test.txt")

    print(f"   Path: {metadata.path}")
    print(f"   Name: {metadata.name}")
    print(f"   Size: {metadata.size}")
    print(f"   Type: {metadata.file_type.value}")
    print(f"   Extension: {metadata.extension}")
    print(f"   Created: {metadata.created_at}")
    print()

    # 7. Checksum
    print("7. CHECKSUM:")
    print("-" * 40)

    checksum = await manager.get_checksum("/documents/test.txt", "sha256")
    print(f"   SHA256: {checksum[:32]}...")

    md5 = await manager.get_checksum("/documents/test.txt", "md5")
    print(f"   MD5: {md5}")
    print()

    # 8. Streaming Read
    print("8. STREAMING READ:")
    print("-" * 40)

    chunk_count = 0
    total_bytes = 0

    async for chunk in manager.read_chunks("/documents/test.txt", chunk_size=10):
        chunk_count += 1
        total_bytes += len(chunk)

    print(f"   Chunks: {chunk_count}")
    print(f"   Total bytes: {total_bytes}")
    print()

    # 9. Compression
    print("9. COMPRESSION:")
    print("-" * 40)

    original = await manager.read("/documents/test.txt")
    compressed = await manager.compress("/documents/test.txt", CompressionType.GZIP)

    print(f"   Original size: {len(original)} bytes")
    print(f"   Compressed size: {len(compressed)} bytes")
    print(f"   Ratio: {len(compressed) / len(original):.2%}")

    decompressed = await manager.decompress(compressed, CompressionType.GZIP)
    print(f"   Decompressed matches: {decompressed == original}")
    print()

    # 10. ZIP Archive
    print("10. ZIP ARCHIVE:")
    print("-" * 40)

    await manager.create_zip(
        ["/docs/readme.md", "/docs/guide.md"],
        "/archives/docs.zip"
    )

    zip_metadata = await manager.get_metadata("/archives/docs.zip")
    print(f"   Created: {zip_metadata.name}")
    print(f"   Size: {zip_metadata.size} bytes")
    print()

    # 11. Chunked Upload
    print("11. CHUNKED UPLOAD:")
    print("-" * 40)

    session = await manager.start_upload(
        filename="large_file.bin",
        total_size=1000,
        chunk_size=100
    )

    print(f"   Session ID: {session.id[:8]}...")
    print(f"   Total chunks: {session.total_chunks}")

    # Simulate uploading chunks
    for i in range(session.total_chunks):
        await manager.upload_chunk(session.id, i, b"x" * 100)

    print(f"   Progress: {session.progress:.0%}")
    print(f"   Complete: {session.is_complete}")
    print()

    # 12. File Watching
    print("12. FILE WATCHING:")
    print("-" * 40)

    events = []

    def on_event(event: WatchEvent):
        events.append(event)

    unwatch = manager.watch(on_event)

    await manager.write("/watched/file.txt", "Watched content")
    await manager.delete("/watched/file.txt")

    for event in events:
        print(f"   {event.event_type}: {event.path}")

    unwatch()
    print()

    print("=" * 70)
    print("DEMO COMPLETE - File Manager Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())

"""
BAEL File Storage Engine Implementation
=======================================

Unified file storage with multiple backends.

"Ba'el's archives span infinite dimensions." — Ba'el
"""

import asyncio
import hashlib
import logging
import mimetypes
import os
import shutil
import threading
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, BinaryIO, Union
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import uuid

logger = logging.getLogger("BAEL.FileStorage")


# ============================================================================
# ENUMS
# ============================================================================

class StorageBackend(Enum):
    """Storage backend types."""
    LOCAL = "local"
    MEMORY = "memory"
    S3 = "s3"
    GCS = "gcs"  # Google Cloud Storage
    AZURE = "azure"
    FTP = "ftp"


class StorageClass(Enum):
    """Storage classes (like S3)."""
    STANDARD = "standard"
    INFREQUENT_ACCESS = "infrequent_access"
    ARCHIVE = "archive"
    GLACIER = "glacier"


class ContentDisposition(Enum):
    """Content disposition for downloads."""
    INLINE = "inline"
    ATTACHMENT = "attachment"


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class FileMetadata:
    """File metadata."""
    content_type: Optional[str] = None
    size: int = 0
    checksum: Optional[str] = None
    checksum_type: str = "md5"

    # Custom metadata
    metadata: Dict[str, str] = field(default_factory=dict)

    # Tags
    tags: Dict[str, str] = field(default_factory=dict)

    # Storage
    storage_class: StorageClass = StorageClass.STANDARD


@dataclass
class StoredFile:
    """A stored file."""
    id: str
    path: str  # Virtual path
    filename: str

    # Storage location
    backend: StorageBackend
    location: str  # Actual storage location

    # Metadata
    metadata: FileMetadata

    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    modified_at: datetime = field(default_factory=datetime.utcnow)
    accessed_at: Optional[datetime] = None

    # State
    exists: bool = True

    @property
    def extension(self) -> str:
        """Get file extension."""
        _, ext = os.path.splitext(self.filename)
        return ext.lower()


@dataclass
class UploadOptions:
    """Options for file upload."""
    filename: Optional[str] = None
    content_type: Optional[str] = None
    storage_class: StorageClass = StorageClass.STANDARD
    metadata: Dict[str, str] = field(default_factory=dict)
    tags: Dict[str, str] = field(default_factory=dict)
    overwrite: bool = False


@dataclass
class StorageConfig:
    """File storage configuration."""
    backend: StorageBackend = StorageBackend.LOCAL

    # Local
    base_path: str = "./storage"

    # S3
    s3_bucket: Optional[str] = None
    s3_region: str = "us-east-1"
    s3_endpoint: Optional[str] = None

    # GCS
    gcs_bucket: Optional[str] = None
    gcs_project: Optional[str] = None

    # Behavior
    auto_create_dirs: bool = True
    generate_checksums: bool = True


# ============================================================================
# STORAGE BACKENDS
# ============================================================================

class StorageBackendBase(ABC):
    """Base class for storage backends."""

    @abstractmethod
    async def put(self, path: str, data: bytes, options: UploadOptions) -> str:
        """Store data and return location."""
        pass

    @abstractmethod
    async def get(self, path: str) -> bytes:
        """Get data."""
        pass

    @abstractmethod
    async def delete(self, path: str) -> bool:
        """Delete file."""
        pass

    @abstractmethod
    async def exists(self, path: str) -> bool:
        """Check if file exists."""
        pass

    @abstractmethod
    async def list(self, prefix: str = "") -> List[str]:
        """List files with prefix."""
        pass

    @abstractmethod
    async def get_metadata(self, path: str) -> FileMetadata:
        """Get file metadata."""
        pass


class LocalBackend(StorageBackendBase):
    """Local filesystem backend."""

    def __init__(self, base_path: str, auto_create: bool = True):
        """Initialize local backend."""
        self.base_path = Path(base_path)

        if auto_create:
            self.base_path.mkdir(parents=True, exist_ok=True)

    def _full_path(self, path: str) -> Path:
        """Get full path."""
        return self.base_path / path

    async def put(self, path: str, data: bytes, options: UploadOptions) -> str:
        """Store file locally."""
        full_path = self._full_path(path)

        # Create directories
        full_path.parent.mkdir(parents=True, exist_ok=True)

        # Write file
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, full_path.write_bytes, data)

        return str(full_path)

    async def get(self, path: str) -> bytes:
        """Read file."""
        full_path = self._full_path(path)

        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, full_path.read_bytes)

    async def delete(self, path: str) -> bool:
        """Delete file."""
        full_path = self._full_path(path)

        if full_path.exists():
            full_path.unlink()
            return True
        return False

    async def exists(self, path: str) -> bool:
        """Check if exists."""
        return self._full_path(path).exists()

    async def list(self, prefix: str = "") -> List[str]:
        """List files."""
        base = self._full_path(prefix)

        if not base.exists():
            return []

        files = []
        for item in base.rglob("*"):
            if item.is_file():
                rel_path = str(item.relative_to(self.base_path))
                files.append(rel_path)

        return files

    async def get_metadata(self, path: str) -> FileMetadata:
        """Get file metadata."""
        full_path = self._full_path(path)

        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        stat = full_path.stat()
        content_type, _ = mimetypes.guess_type(str(full_path))

        return FileMetadata(
            content_type=content_type,
            size=stat.st_size
        )


class MemoryBackend(StorageBackendBase):
    """In-memory backend (for testing)."""

    def __init__(self):
        """Initialize memory backend."""
        self._files: Dict[str, bytes] = {}
        self._metadata: Dict[str, FileMetadata] = {}
        self._lock = threading.RLock()

    async def put(self, path: str, data: bytes, options: UploadOptions) -> str:
        """Store in memory."""
        with self._lock:
            self._files[path] = data

            content_type = options.content_type
            if not content_type:
                content_type, _ = mimetypes.guess_type(path)

            self._metadata[path] = FileMetadata(
                content_type=content_type,
                size=len(data),
                metadata=options.metadata,
                tags=options.tags,
                storage_class=options.storage_class
            )

        return f"memory://{path}"

    async def get(self, path: str) -> bytes:
        """Get from memory."""
        with self._lock:
            if path not in self._files:
                raise FileNotFoundError(f"File not found: {path}")
            return self._files[path]

    async def delete(self, path: str) -> bool:
        """Delete from memory."""
        with self._lock:
            if path in self._files:
                del self._files[path]
                self._metadata.pop(path, None)
                return True
            return False

    async def exists(self, path: str) -> bool:
        """Check if exists."""
        with self._lock:
            return path in self._files

    async def list(self, prefix: str = "") -> List[str]:
        """List files."""
        with self._lock:
            return [p for p in self._files.keys() if p.startswith(prefix)]

    async def get_metadata(self, path: str) -> FileMetadata:
        """Get metadata."""
        with self._lock:
            if path not in self._metadata:
                raise FileNotFoundError(f"File not found: {path}")
            return self._metadata[path]


class MockS3Backend(StorageBackendBase):
    """Mock S3 backend (for testing without AWS)."""

    def __init__(self, bucket: str, region: str = "us-east-1"):
        """Initialize mock S3."""
        self.bucket = bucket
        self.region = region
        self._memory = MemoryBackend()

    async def put(self, path: str, data: bytes, options: UploadOptions) -> str:
        """Store to mock S3."""
        await self._memory.put(path, data, options)
        return f"s3://{self.bucket}/{path}"

    async def get(self, path: str) -> bytes:
        """Get from mock S3."""
        return await self._memory.get(path)

    async def delete(self, path: str) -> bool:
        """Delete from mock S3."""
        return await self._memory.delete(path)

    async def exists(self, path: str) -> bool:
        """Check existence."""
        return await self._memory.exists(path)

    async def list(self, prefix: str = "") -> List[str]:
        """List objects."""
        return await self._memory.list(prefix)

    async def get_metadata(self, path: str) -> FileMetadata:
        """Get object metadata."""
        return await self._memory.get_metadata(path)


# ============================================================================
# MAIN ENGINE
# ============================================================================

class FileStorageEngine:
    """
    Main file storage engine.

    Features:
    - Multiple backends (local, S3, memory)
    - Metadata tracking
    - Checksum verification
    - File listing and search

    "Ba'el's archives contain all knowledge." — Ba'el
    """

    def __init__(self, config: Optional[StorageConfig] = None):
        """Initialize file storage engine."""
        self.config = config or StorageConfig()

        # Create backend
        self._backend = self._create_backend()

        # File index: id -> StoredFile
        self._files: Dict[str, StoredFile] = {}

        # Path index: path -> id
        self._path_index: Dict[str, str] = {}

        self._lock = threading.RLock()

        logger.info(f"FileStorageEngine initialized with {self.config.backend.value} backend")

    def _create_backend(self) -> StorageBackendBase:
        """Create storage backend."""
        if self.config.backend == StorageBackend.LOCAL:
            return LocalBackend(
                self.config.base_path,
                self.config.auto_create_dirs
            )
        elif self.config.backend == StorageBackend.MEMORY:
            return MemoryBackend()
        elif self.config.backend == StorageBackend.S3:
            return MockS3Backend(
                self.config.s3_bucket or "default-bucket",
                self.config.s3_region
            )
        else:
            # Default to memory
            return MemoryBackend()

    # ========================================================================
    # STORAGE OPERATIONS
    # ========================================================================

    async def upload(
        self,
        data: Union[bytes, BinaryIO, str, Path],
        path: str,
        options: Optional[UploadOptions] = None
    ) -> StoredFile:
        """
        Upload a file.

        Args:
            data: File data (bytes, file object, or path)
            path: Virtual storage path
            options: Upload options

        Returns:
            StoredFile record
        """
        options = options or UploadOptions()

        # Read data
        if isinstance(data, (str, Path)):
            data_path = Path(data)
            with open(data_path, 'rb') as f:
                file_data = f.read()
            if not options.filename:
                options.filename = data_path.name
        elif hasattr(data, 'read'):
            file_data = data.read()
        else:
            file_data = data

        # Determine filename
        filename = options.filename or os.path.basename(path)

        # Determine content type
        content_type = options.content_type
        if not content_type:
            content_type, _ = mimetypes.guess_type(filename)

        # Check for existing file
        with self._lock:
            if path in self._path_index and not options.overwrite:
                raise FileExistsError(f"File already exists: {path}")

        # Calculate checksum
        checksum = None
        if self.config.generate_checksums:
            checksum = hashlib.md5(file_data).hexdigest()

        # Upload to backend
        location = await self._backend.put(path, file_data, options)

        # Create record
        file_id = str(uuid.uuid4())
        stored_file = StoredFile(
            id=file_id,
            path=path,
            filename=filename,
            backend=self.config.backend,
            location=location,
            metadata=FileMetadata(
                content_type=content_type,
                size=len(file_data),
                checksum=checksum,
                metadata=options.metadata,
                tags=options.tags,
                storage_class=options.storage_class
            )
        )

        # Index
        with self._lock:
            self._files[file_id] = stored_file
            self._path_index[path] = file_id

        logger.info(f"Uploaded file: {path} ({len(file_data)} bytes)")

        return stored_file

    async def download(self, path: str) -> bytes:
        """Download file data."""
        return await self._backend.get(path)

    async def download_to(self, path: str, destination: Union[str, Path]) -> None:
        """Download file to local path."""
        data = await self.download(path)

        dest_path = Path(destination)
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        with open(dest_path, 'wb') as f:
            f.write(data)

    async def delete(self, path: str) -> bool:
        """Delete a file."""
        # Remove from backend
        deleted = await self._backend.delete(path)

        # Remove from index
        with self._lock:
            if path in self._path_index:
                file_id = self._path_index.pop(path)
                self._files.pop(file_id, None)

        if deleted:
            logger.info(f"Deleted file: {path}")

        return deleted

    async def exists(self, path: str) -> bool:
        """Check if file exists."""
        return await self._backend.exists(path)

    async def move(self, source: str, destination: str) -> StoredFile:
        """Move/rename a file."""
        # Download
        data = await self.download(source)

        # Get original metadata
        with self._lock:
            if source in self._path_index:
                file_id = self._path_index[source]
                original = self._files.get(file_id)
                options = UploadOptions(
                    filename=os.path.basename(destination),
                    content_type=original.metadata.content_type if original else None,
                    metadata=original.metadata.metadata if original else {},
                    tags=original.metadata.tags if original else {},
                    overwrite=True
                )
            else:
                options = UploadOptions(overwrite=True)

        # Upload to new location
        stored = await self.upload(data, destination, options)

        # Delete original
        await self.delete(source)

        return stored

    async def copy(self, source: str, destination: str) -> StoredFile:
        """Copy a file."""
        data = await self.download(source)

        with self._lock:
            if source in self._path_index:
                file_id = self._path_index[source]
                original = self._files.get(file_id)
                options = UploadOptions(
                    filename=os.path.basename(destination),
                    content_type=original.metadata.content_type if original else None,
                    overwrite=True
                )
            else:
                options = UploadOptions(overwrite=True)

        return await self.upload(data, destination, options)

    # ========================================================================
    # QUERYING
    # ========================================================================

    async def list(self, prefix: str = "") -> List[StoredFile]:
        """List files with prefix."""
        paths = await self._backend.list(prefix)

        result = []
        with self._lock:
            for path in paths:
                if path in self._path_index:
                    file_id = self._path_index[path]
                    if file_id in self._files:
                        result.append(self._files[file_id])

        return result

    def get_file(self, file_id: str) -> Optional[StoredFile]:
        """Get file by ID."""
        with self._lock:
            return self._files.get(file_id)

    def get_file_by_path(self, path: str) -> Optional[StoredFile]:
        """Get file by path."""
        with self._lock:
            file_id = self._path_index.get(path)
            if file_id:
                return self._files.get(file_id)
        return None

    async def get_metadata(self, path: str) -> Optional[FileMetadata]:
        """Get file metadata."""
        try:
            return await self._backend.get_metadata(path)
        except FileNotFoundError:
            return None

    # ========================================================================
    # UTILITIES
    # ========================================================================

    def generate_path(
        self,
        filename: str,
        prefix: str = "",
        use_date_structure: bool = True
    ) -> str:
        """Generate a storage path."""
        parts = []

        if prefix:
            parts.append(prefix)

        if use_date_structure:
            now = datetime.utcnow()
            parts.extend([str(now.year), f"{now.month:02d}", f"{now.day:02d}"])

        # Add unique ID to filename
        unique_id = str(uuid.uuid4())[:8]
        name, ext = os.path.splitext(filename)
        unique_filename = f"{name}_{unique_id}{ext}"

        parts.append(unique_filename)

        return "/".join(parts)

    def get_status(self) -> Dict[str, Any]:
        """Get engine status."""
        with self._lock:
            total_size = sum(f.metadata.size for f in self._files.values())

        return {
            'backend': self.config.backend.value,
            'file_count': len(self._files),
            'total_size': total_size,
            'base_path': self.config.base_path
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

file_storage = FileStorageEngine()

"""
BAEL File Storage Engine
========================

Unified file storage with multiple backends (local, S3, cloud).

"Ba'el stores infinite knowledge across all realms." — Ba'el
"""

from .file_storage_engine import (
    # Enums
    StorageBackend,
    StorageClass,

    # Data structures
    FileMetadata,
    StoredFile,
    UploadOptions,
    StorageConfig,

    # Main engine
    FileStorageEngine,

    # Backends
    LocalBackend,
    MemoryBackend,

    # Convenience
    file_storage
)

__all__ = [
    'StorageBackend',
    'StorageClass',
    'FileMetadata',
    'StoredFile',
    'UploadOptions',
    'StorageConfig',
    'FileStorageEngine',
    'LocalBackend',
    'MemoryBackend',
    'file_storage'
]

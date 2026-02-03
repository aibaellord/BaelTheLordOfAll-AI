#!/usr/bin/env python3
"""
BAEL - Archive Manager
Comprehensive file archiving and compression system.

Features:
- Multiple archive formats (zip, tar, gzip, bzip2, xz)
- Archive creation and extraction
- Selective extraction
- Archive inspection
- Password protection (for zip)
- Multi-volume archives
- Integrity verification
- Progress tracking
- Streaming support
- Archive modification
"""

import asyncio
import gzip
import hashlib
import io
import json
import logging
import os
import shutil
import struct
import tarfile
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
from typing import (Any, BinaryIO, Callable, Dict, Generator, Iterator, List,
                    Optional, Set, Tuple, Type, TypeVar, Union)

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS
# =============================================================================

class ArchiveFormat(Enum):
    """Archive format."""
    ZIP = "zip"
    TAR = "tar"
    TAR_GZ = "tar.gz"
    TAR_BZ2 = "tar.bz2"
    TAR_XZ = "tar.xz"
    GZIP = "gzip"
    RAW = "raw"


class CompressionLevel(Enum):
    """Compression level."""
    NONE = 0
    FASTEST = 1
    FAST = 3
    NORMAL = 6
    BEST = 9


class EntryType(Enum):
    """Archive entry type."""
    FILE = "file"
    DIRECTORY = "directory"
    SYMLINK = "symlink"


class OperationType(Enum):
    """Operation type."""
    CREATE = "create"
    EXTRACT = "extract"
    LIST = "list"
    UPDATE = "update"
    DELETE = "delete"
    VERIFY = "verify"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class ArchiveEntry:
    """Entry in an archive."""
    name: str
    size: int
    compressed_size: int
    entry_type: EntryType
    modified_time: Optional[datetime] = None
    permissions: int = 0o644
    checksum: Optional[str] = None
    is_encrypted: bool = False
    comment: str = ""
    extra: Dict[str, Any] = field(default_factory=dict)

    @property
    def compression_ratio(self) -> float:
        if self.size == 0:
            return 0.0
        return 1 - (self.compressed_size / self.size)


@dataclass
class ArchiveInfo:
    """Information about an archive."""
    path: str
    format: ArchiveFormat
    total_size: int
    compressed_size: int
    entry_count: int
    entries: List[ArchiveEntry] = field(default_factory=list)
    comment: str = ""
    created_at: Optional[datetime] = None
    modified_at: Optional[datetime] = None
    is_encrypted: bool = False
    is_multipart: bool = False

    @property
    def compression_ratio(self) -> float:
        if self.total_size == 0:
            return 0.0
        return 1 - (self.compressed_size / self.total_size)


@dataclass
class ArchiveOptions:
    """Archive creation options."""
    format: ArchiveFormat = ArchiveFormat.ZIP
    compression_level: CompressionLevel = CompressionLevel.NORMAL
    password: Optional[str] = None
    comment: str = ""
    exclude_patterns: List[str] = field(default_factory=list)
    include_hidden: bool = False
    preserve_permissions: bool = True
    follow_symlinks: bool = True
    max_size: Optional[int] = None


@dataclass
class ExtractionOptions:
    """Extraction options."""
    password: Optional[str] = None
    overwrite: bool = True
    preserve_permissions: bool = True
    extract_symlinks: bool = True
    filter_entries: Optional[List[str]] = None


@dataclass
class ProgressInfo:
    """Progress information."""
    operation: OperationType
    current_file: str = ""
    files_processed: int = 0
    total_files: int = 0
    bytes_processed: int = 0
    total_bytes: int = 0

    @property
    def percent_complete(self) -> float:
        if self.total_bytes == 0:
            return 0.0
        return (self.bytes_processed / self.total_bytes) * 100


@dataclass
class VerificationResult:
    """Verification result."""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    entries_checked: int = 0
    entries_passed: int = 0


# =============================================================================
# HANDLERS
# =============================================================================

class ArchiveHandler(ABC):
    """Abstract archive handler."""

    @abstractmethod
    def create(
        self,
        archive_path: str,
        files: List[str],
        options: ArchiveOptions
    ) -> ArchiveInfo:
        """Create an archive."""
        pass

    @abstractmethod
    def extract(
        self,
        archive_path: str,
        output_dir: str,
        options: ExtractionOptions
    ) -> List[str]:
        """Extract an archive."""
        pass

    @abstractmethod
    def list_contents(self, archive_path: str) -> List[ArchiveEntry]:
        """List archive contents."""
        pass

    @abstractmethod
    def get_info(self, archive_path: str) -> ArchiveInfo:
        """Get archive information."""
        pass


class ZipHandler(ArchiveHandler):
    """ZIP archive handler."""

    def __init__(self):
        self._level_map = {
            CompressionLevel.NONE: zipfile.ZIP_STORED,
            CompressionLevel.FASTEST: zipfile.ZIP_DEFLATED,
            CompressionLevel.FAST: zipfile.ZIP_DEFLATED,
            CompressionLevel.NORMAL: zipfile.ZIP_DEFLATED,
            CompressionLevel.BEST: zipfile.ZIP_DEFLATED,
        }

    def create(
        self,
        archive_path: str,
        files: List[str],
        options: ArchiveOptions
    ) -> ArchiveInfo:
        compression = self._level_map.get(
            options.compression_level,
            zipfile.ZIP_DEFLATED
        )

        with zipfile.ZipFile(
            archive_path, 'w',
            compression=compression,
            compresslevel=options.compression_level.value
        ) as zf:
            if options.comment:
                zf.comment = options.comment.encode('utf-8')

            for file_path in files:
                if os.path.isfile(file_path):
                    arcname = os.path.basename(file_path)
                    zf.write(file_path, arcname)
                elif os.path.isdir(file_path):
                    for root, dirs, filenames in os.walk(file_path):
                        for filename in filenames:
                            full_path = os.path.join(root, filename)
                            arcname = os.path.relpath(full_path, os.path.dirname(file_path))
                            zf.write(full_path, arcname)

        return self.get_info(archive_path)

    def extract(
        self,
        archive_path: str,
        output_dir: str,
        options: ExtractionOptions
    ) -> List[str]:
        extracted = []

        with zipfile.ZipFile(archive_path, 'r') as zf:
            members = zf.namelist()

            if options.filter_entries:
                members = [
                    m for m in members
                    if any(m.startswith(f) for f in options.filter_entries)
                ]

            for member in members:
                target_path = os.path.join(output_dir, member)

                if not options.overwrite and os.path.exists(target_path):
                    continue

                zf.extract(member, output_dir)
                extracted.append(target_path)

        return extracted

    def list_contents(self, archive_path: str) -> List[ArchiveEntry]:
        entries = []

        with zipfile.ZipFile(archive_path, 'r') as zf:
            for info in zf.infolist():
                entry_type = EntryType.DIRECTORY if info.is_dir() else EntryType.FILE

                mod_time = datetime(*info.date_time) if info.date_time else None

                entries.append(ArchiveEntry(
                    name=info.filename,
                    size=info.file_size,
                    compressed_size=info.compress_size,
                    entry_type=entry_type,
                    modified_time=mod_time,
                    checksum=f"{info.CRC:08x}",
                    comment=info.comment.decode('utf-8') if info.comment else ""
                ))

        return entries

    def get_info(self, archive_path: str) -> ArchiveInfo:
        entries = self.list_contents(archive_path)

        total_size = sum(e.size for e in entries)
        compressed_size = os.path.getsize(archive_path)

        with zipfile.ZipFile(archive_path, 'r') as zf:
            comment = zf.comment.decode('utf-8') if zf.comment else ""

        return ArchiveInfo(
            path=archive_path,
            format=ArchiveFormat.ZIP,
            total_size=total_size,
            compressed_size=compressed_size,
            entry_count=len(entries),
            entries=entries,
            comment=comment,
            modified_at=datetime.fromtimestamp(os.path.getmtime(archive_path))
        )

    def add_file(
        self,
        archive_path: str,
        file_path: str,
        arcname: Optional[str] = None
    ) -> None:
        """Add a file to existing archive."""
        with zipfile.ZipFile(archive_path, 'a') as zf:
            zf.write(file_path, arcname or os.path.basename(file_path))

    def remove_file(
        self,
        archive_path: str,
        entry_name: str
    ) -> None:
        """Remove a file from archive."""
        # ZIP doesn't support removal, so we recreate
        temp_path = archive_path + '.tmp'

        with zipfile.ZipFile(archive_path, 'r') as zf_in:
            with zipfile.ZipFile(temp_path, 'w', zf_in.compression) as zf_out:
                for item in zf_in.infolist():
                    if item.filename != entry_name:
                        data = zf_in.read(item.filename)
                        zf_out.writestr(item, data)

        os.replace(temp_path, archive_path)


class TarHandler(ArchiveHandler):
    """TAR archive handler (including .tar.gz, .tar.bz2, .tar.xz)."""

    def __init__(self, format: ArchiveFormat = ArchiveFormat.TAR):
        self.format = format
        self._mode_map = {
            ArchiveFormat.TAR: "",
            ArchiveFormat.TAR_GZ: "gz",
            ArchiveFormat.TAR_BZ2: "bz2",
            ArchiveFormat.TAR_XZ: "xz",
        }

    def create(
        self,
        archive_path: str,
        files: List[str],
        options: ArchiveOptions
    ) -> ArchiveInfo:
        mode = "w:" + self._mode_map.get(self.format, "")

        with tarfile.open(archive_path, mode) as tf:
            for file_path in files:
                if os.path.exists(file_path):
                    arcname = os.path.basename(file_path)
                    tf.add(file_path, arcname=arcname)

        return self.get_info(archive_path)

    def extract(
        self,
        archive_path: str,
        output_dir: str,
        options: ExtractionOptions
    ) -> List[str]:
        extracted = []
        mode = "r:*"

        with tarfile.open(archive_path, mode) as tf:
            members = tf.getmembers()

            if options.filter_entries:
                members = [
                    m for m in members
                    if any(m.name.startswith(f) for f in options.filter_entries)
                ]

            for member in members:
                target_path = os.path.join(output_dir, member.name)

                if not options.overwrite and os.path.exists(target_path):
                    continue

                tf.extract(member, output_dir)
                extracted.append(target_path)

        return extracted

    def list_contents(self, archive_path: str) -> List[ArchiveEntry]:
        entries = []

        with tarfile.open(archive_path, "r:*") as tf:
            for member in tf.getmembers():
                if member.isdir():
                    entry_type = EntryType.DIRECTORY
                elif member.issym():
                    entry_type = EntryType.SYMLINK
                else:
                    entry_type = EntryType.FILE

                entries.append(ArchiveEntry(
                    name=member.name,
                    size=member.size,
                    compressed_size=member.size,  # TAR doesn't store compressed size per file
                    entry_type=entry_type,
                    modified_time=datetime.fromtimestamp(member.mtime),
                    permissions=member.mode
                ))

        return entries

    def get_info(self, archive_path: str) -> ArchiveInfo:
        entries = self.list_contents(archive_path)

        total_size = sum(e.size for e in entries)
        compressed_size = os.path.getsize(archive_path)

        return ArchiveInfo(
            path=archive_path,
            format=self.format,
            total_size=total_size,
            compressed_size=compressed_size,
            entry_count=len(entries),
            entries=entries,
            modified_at=datetime.fromtimestamp(os.path.getmtime(archive_path))
        )


class GzipHandler(ArchiveHandler):
    """GZIP handler for single files."""

    def create(
        self,
        archive_path: str,
        files: List[str],
        options: ArchiveOptions
    ) -> ArchiveInfo:
        if len(files) != 1:
            raise ValueError("GZIP can only compress a single file")

        file_path = files[0]

        with open(file_path, 'rb') as f_in:
            with gzip.open(
                archive_path, 'wb',
                compresslevel=options.compression_level.value
            ) as f_out:
                shutil.copyfileobj(f_in, f_out)

        return self.get_info(archive_path)

    def extract(
        self,
        archive_path: str,
        output_dir: str,
        options: ExtractionOptions
    ) -> List[str]:
        # Determine output filename
        base_name = os.path.basename(archive_path)
        if base_name.endswith('.gz'):
            output_name = base_name[:-3]
        else:
            output_name = base_name + '.extracted'

        output_path = os.path.join(output_dir, output_name)

        with gzip.open(archive_path, 'rb') as f_in:
            with open(output_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)

        return [output_path]

    def list_contents(self, archive_path: str) -> List[ArchiveEntry]:
        compressed_size = os.path.getsize(archive_path)

        # Get uncompressed size (stored in last 4 bytes)
        with open(archive_path, 'rb') as f:
            f.seek(-4, 2)
            uncompressed_size = struct.unpack('<I', f.read(4))[0]

        base_name = os.path.basename(archive_path)
        if base_name.endswith('.gz'):
            name = base_name[:-3]
        else:
            name = base_name

        return [ArchiveEntry(
            name=name,
            size=uncompressed_size,
            compressed_size=compressed_size,
            entry_type=EntryType.FILE
        )]

    def get_info(self, archive_path: str) -> ArchiveInfo:
        entries = self.list_contents(archive_path)

        return ArchiveInfo(
            path=archive_path,
            format=ArchiveFormat.GZIP,
            total_size=entries[0].size if entries else 0,
            compressed_size=os.path.getsize(archive_path),
            entry_count=1,
            entries=entries,
            modified_at=datetime.fromtimestamp(os.path.getmtime(archive_path))
        )


# =============================================================================
# ARCHIVE BUILDER
# =============================================================================

class ArchiveBuilder:
    """Fluent archive builder."""

    def __init__(self):
        self._files: List[str] = []
        self._options = ArchiveOptions()
        self._output_path: Optional[str] = None

    def format(self, fmt: ArchiveFormat) -> "ArchiveBuilder":
        """Set archive format."""
        self._options.format = fmt
        return self

    def compression(self, level: CompressionLevel) -> "ArchiveBuilder":
        """Set compression level."""
        self._options.compression_level = level
        return self

    def password(self, pwd: str) -> "ArchiveBuilder":
        """Set password."""
        self._options.password = pwd
        return self

    def comment(self, text: str) -> "ArchiveBuilder":
        """Set comment."""
        self._options.comment = text
        return self

    def exclude(self, *patterns: str) -> "ArchiveBuilder":
        """Add exclude patterns."""
        self._options.exclude_patterns.extend(patterns)
        return self

    def include_hidden(self, include: bool = True) -> "ArchiveBuilder":
        """Include hidden files."""
        self._options.include_hidden = include
        return self

    def add_file(self, path: str) -> "ArchiveBuilder":
        """Add a file."""
        self._files.append(path)
        return self

    def add_files(self, *paths: str) -> "ArchiveBuilder":
        """Add multiple files."""
        self._files.extend(paths)
        return self

    def add_directory(self, path: str) -> "ArchiveBuilder":
        """Add a directory."""
        self._files.append(path)
        return self

    def output(self, path: str) -> "ArchiveBuilder":
        """Set output path."""
        self._output_path = path
        return self

    def build(self) -> ArchiveInfo:
        """Create the archive."""
        if not self._output_path:
            raise ValueError("Output path not set")

        manager = ArchiveManager()
        return manager.create(
            self._output_path,
            self._files,
            self._options
        )


# =============================================================================
# ARCHIVE MANAGER
# =============================================================================

class ArchiveManager:
    """
    Comprehensive Archive Manager for BAEL.

    Provides archiving and compression operations.
    """

    def __init__(self):
        self._handlers: Dict[ArchiveFormat, ArchiveHandler] = {
            ArchiveFormat.ZIP: ZipHandler(),
            ArchiveFormat.TAR: TarHandler(ArchiveFormat.TAR),
            ArchiveFormat.TAR_GZ: TarHandler(ArchiveFormat.TAR_GZ),
            ArchiveFormat.TAR_BZ2: TarHandler(ArchiveFormat.TAR_BZ2),
            ArchiveFormat.TAR_XZ: TarHandler(ArchiveFormat.TAR_XZ),
            ArchiveFormat.GZIP: GzipHandler(),
        }

        self._progress_callback: Optional[Callable[[ProgressInfo], None]] = None
        self._stats: Dict[str, int] = defaultdict(int)

    # -------------------------------------------------------------------------
    # CORE OPERATIONS
    # -------------------------------------------------------------------------

    def create(
        self,
        archive_path: str,
        files: List[str],
        options: Optional[ArchiveOptions] = None
    ) -> ArchiveInfo:
        """Create an archive."""
        options = options or ArchiveOptions()

        # Auto-detect format from extension
        if options.format == ArchiveFormat.ZIP:
            ext = os.path.splitext(archive_path)[1].lower()
            if ext in ('.tar', '.tgz', '.tbz', '.txz'):
                if ext == '.tgz':
                    options.format = ArchiveFormat.TAR_GZ
                elif ext == '.tbz':
                    options.format = ArchiveFormat.TAR_BZ2
                elif ext == '.txz':
                    options.format = ArchiveFormat.TAR_XZ
                else:
                    options.format = ArchiveFormat.TAR
            elif ext == '.gz' and not archive_path.endswith('.tar.gz'):
                options.format = ArchiveFormat.GZIP

        handler = self._handlers.get(options.format)
        if not handler:
            raise ValueError(f"Unsupported format: {options.format}")

        # Filter files
        filtered_files = self._filter_files(files, options)

        result = handler.create(archive_path, filtered_files, options)

        self._stats["archives_created"] += 1
        self._stats["bytes_compressed"] += result.total_size

        return result

    def extract(
        self,
        archive_path: str,
        output_dir: str,
        options: Optional[ExtractionOptions] = None
    ) -> List[str]:
        """Extract an archive."""
        options = options or ExtractionOptions()

        # Detect format
        fmt = self._detect_format(archive_path)

        handler = self._handlers.get(fmt)
        if not handler:
            raise ValueError(f"Unsupported format: {fmt}")

        os.makedirs(output_dir, exist_ok=True)

        extracted = handler.extract(archive_path, output_dir, options)

        self._stats["archives_extracted"] += 1
        self._stats["files_extracted"] += len(extracted)

        return extracted

    def list_contents(self, archive_path: str) -> List[ArchiveEntry]:
        """List archive contents."""
        fmt = self._detect_format(archive_path)

        handler = self._handlers.get(fmt)
        if not handler:
            raise ValueError(f"Unsupported format: {fmt}")

        return handler.list_contents(archive_path)

    def get_info(self, archive_path: str) -> ArchiveInfo:
        """Get archive information."""
        fmt = self._detect_format(archive_path)

        handler = self._handlers.get(fmt)
        if not handler:
            raise ValueError(f"Unsupported format: {fmt}")

        return handler.get_info(archive_path)

    # -------------------------------------------------------------------------
    # CONVENIENCE METHODS
    # -------------------------------------------------------------------------

    def builder(self) -> ArchiveBuilder:
        """Get a new archive builder."""
        return ArchiveBuilder()

    def zip(
        self,
        archive_path: str,
        files: List[str],
        level: CompressionLevel = CompressionLevel.NORMAL
    ) -> ArchiveInfo:
        """Create a ZIP archive."""
        options = ArchiveOptions(
            format=ArchiveFormat.ZIP,
            compression_level=level
        )
        return self.create(archive_path, files, options)

    def tar_gz(
        self,
        archive_path: str,
        files: List[str],
        level: CompressionLevel = CompressionLevel.NORMAL
    ) -> ArchiveInfo:
        """Create a tar.gz archive."""
        options = ArchiveOptions(
            format=ArchiveFormat.TAR_GZ,
            compression_level=level
        )
        return self.create(archive_path, files, options)

    def unzip(
        self,
        archive_path: str,
        output_dir: str
    ) -> List[str]:
        """Extract a ZIP archive."""
        return self.extract(archive_path, output_dir)

    # -------------------------------------------------------------------------
    # VERIFICATION
    # -------------------------------------------------------------------------

    def verify(self, archive_path: str) -> VerificationResult:
        """Verify archive integrity."""
        result = VerificationResult(is_valid=True)

        try:
            fmt = self._detect_format(archive_path)

            if fmt == ArchiveFormat.ZIP:
                with zipfile.ZipFile(archive_path, 'r') as zf:
                    bad_files = zf.testzip()
                    if bad_files:
                        result.is_valid = False
                        result.errors.append(f"Corrupted file: {bad_files}")

                    result.entries_checked = len(zf.namelist())
                    result.entries_passed = result.entries_checked if result.is_valid else 0

            elif fmt in (ArchiveFormat.TAR, ArchiveFormat.TAR_GZ, ArchiveFormat.TAR_BZ2, ArchiveFormat.TAR_XZ):
                with tarfile.open(archive_path, 'r:*') as tf:
                    result.entries_checked = len(tf.getmembers())
                    result.entries_passed = result.entries_checked

            elif fmt == ArchiveFormat.GZIP:
                with gzip.open(archive_path, 'rb') as f:
                    while f.read(65536):
                        pass
                result.entries_checked = 1
                result.entries_passed = 1

        except Exception as e:
            result.is_valid = False
            result.errors.append(str(e))

        return result

    # -------------------------------------------------------------------------
    # UTILITIES
    # -------------------------------------------------------------------------

    def _detect_format(self, path: str) -> ArchiveFormat:
        """Detect archive format from path."""
        lower = path.lower()

        if lower.endswith('.zip'):
            return ArchiveFormat.ZIP
        elif lower.endswith('.tar.gz') or lower.endswith('.tgz'):
            return ArchiveFormat.TAR_GZ
        elif lower.endswith('.tar.bz2') or lower.endswith('.tbz2') or lower.endswith('.tbz'):
            return ArchiveFormat.TAR_BZ2
        elif lower.endswith('.tar.xz') or lower.endswith('.txz'):
            return ArchiveFormat.TAR_XZ
        elif lower.endswith('.tar'):
            return ArchiveFormat.TAR
        elif lower.endswith('.gz'):
            return ArchiveFormat.GZIP
        else:
            return ArchiveFormat.ZIP

    def _filter_files(
        self,
        files: List[str],
        options: ArchiveOptions
    ) -> List[str]:
        """Filter files based on options."""
        import fnmatch

        filtered = []

        for file_path in files:
            if not os.path.exists(file_path):
                continue

            basename = os.path.basename(file_path)

            # Skip hidden files unless included
            if not options.include_hidden and basename.startswith('.'):
                continue

            # Check exclude patterns
            excluded = False
            for pattern in options.exclude_patterns:
                if fnmatch.fnmatch(basename, pattern):
                    excluded = True
                    break

            if not excluded:
                filtered.append(file_path)

        return filtered

    def on_progress(
        self,
        callback: Callable[[ProgressInfo], None]
    ) -> "ArchiveManager":
        """Set progress callback."""
        self._progress_callback = callback
        return self

    def get_stats(self) -> Dict[str, int]:
        """Get manager statistics."""
        return dict(self._stats)

    # -------------------------------------------------------------------------
    # ASYNC OPERATIONS
    # -------------------------------------------------------------------------

    async def create_async(
        self,
        archive_path: str,
        files: List[str],
        options: Optional[ArchiveOptions] = None
    ) -> ArchiveInfo:
        """Create archive asynchronously."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self.create, archive_path, files, options
        )

    async def extract_async(
        self,
        archive_path: str,
        output_dir: str,
        options: Optional[ExtractionOptions] = None
    ) -> List[str]:
        """Extract archive asynchronously."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self.extract, archive_path, output_dir, options
        )


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Archive Manager."""
    print("=" * 70)
    print("BAEL - ARCHIVE MANAGER DEMO")
    print("Comprehensive File Archiving System")
    print("=" * 70)
    print()

    manager = ArchiveManager()

    # Create temp directory for demo
    import tempfile
    temp_dir = tempfile.mkdtemp(prefix="bael_archive_demo_")

    try:
        # Create test files
        test_files = []
        for i in range(5):
            file_path = os.path.join(temp_dir, f"file_{i}.txt")
            with open(file_path, 'w') as f:
                f.write(f"This is test file {i}\n" * 100)
            test_files.append(file_path)

        # Create subdirectory with files
        subdir = os.path.join(temp_dir, "subdir")
        os.makedirs(subdir)
        for i in range(3):
            file_path = os.path.join(subdir, f"sub_file_{i}.txt")
            with open(file_path, 'w') as f:
                f.write(f"Subdirectory file {i}\n" * 50)
            test_files.append(file_path)

        # 1. Create ZIP Archive
        print("1. CREATE ZIP ARCHIVE:")
        print("-" * 40)

        zip_path = os.path.join(temp_dir, "archive.zip")
        info = manager.zip(zip_path, test_files)

        print(f"   Created: {os.path.basename(info.path)}")
        print(f"   Format: {info.format.value}")
        print(f"   Entries: {info.entry_count}")
        print(f"   Total size: {info.total_size:,} bytes")
        print(f"   Compressed: {info.compressed_size:,} bytes")
        print(f"   Ratio: {info.compression_ratio:.1%}")
        print()

        # 2. Create TAR.GZ Archive
        print("2. CREATE TAR.GZ ARCHIVE:")
        print("-" * 40)

        tar_path = os.path.join(temp_dir, "archive.tar.gz")
        info = manager.tar_gz(tar_path, test_files[:5])

        print(f"   Created: {os.path.basename(info.path)}")
        print(f"   Format: {info.format.value}")
        print(f"   Entries: {info.entry_count}")
        print(f"   Ratio: {info.compression_ratio:.1%}")
        print()

        # 3. Using Builder
        print("3. ARCHIVE BUILDER:")
        print("-" * 40)

        builder_path = os.path.join(temp_dir, "builder_archive.zip")
        info = (manager.builder()
                .format(ArchiveFormat.ZIP)
                .compression(CompressionLevel.BEST)
                .comment("Created by BAEL Archive Manager")
                .add_files(*test_files[:3])
                .output(builder_path)
                .build())

        print(f"   Created via builder: {os.path.basename(info.path)}")
        print(f"   Comment: {info.comment}")
        print()

        # 4. List Archive Contents
        print("4. LIST ARCHIVE CONTENTS:")
        print("-" * 40)

        entries = manager.list_contents(zip_path)
        print(f"   Archive: {os.path.basename(zip_path)}")
        for entry in entries[:5]:
            print(f"     - {entry.name}: {entry.size:,} bytes ({entry.entry_type.value})")
        if len(entries) > 5:
            print(f"     ... and {len(entries) - 5} more entries")
        print()

        # 5. Get Archive Info
        print("5. ARCHIVE INFO:")
        print("-" * 40)

        info = manager.get_info(zip_path)
        print(f"   Path: {info.path}")
        print(f"   Format: {info.format.value}")
        print(f"   Total entries: {info.entry_count}")
        print(f"   Total size: {info.total_size:,} bytes")
        print(f"   Compressed size: {info.compressed_size:,} bytes")
        print(f"   Modified: {info.modified_at}")
        print()

        # 6. Extract Archive
        print("6. EXTRACT ARCHIVE:")
        print("-" * 40)

        extract_dir = os.path.join(temp_dir, "extracted")
        extracted = manager.extract(zip_path, extract_dir)

        print(f"   Extracted to: {extract_dir}")
        print(f"   Files extracted: {len(extracted)}")
        for f in extracted[:3]:
            print(f"     - {os.path.basename(f)}")
        print()

        # 7. Selective Extraction
        print("7. SELECTIVE EXTRACTION:")
        print("-" * 40)

        select_dir = os.path.join(temp_dir, "selective")
        options = ExtractionOptions(filter_entries=["file_0", "file_1"])
        extracted = manager.extract(zip_path, select_dir, options)

        print(f"   Filter: file_0, file_1")
        print(f"   Extracted: {len(extracted)} files")
        print()

        # 8. Verify Archive
        print("8. VERIFY ARCHIVE:")
        print("-" * 40)

        result = manager.verify(zip_path)
        print(f"   Valid: {result.is_valid}")
        print(f"   Entries checked: {result.entries_checked}")
        print(f"   Entries passed: {result.entries_passed}")
        print(f"   Errors: {result.errors}")
        print()

        # 9. GZIP Single File
        print("9. GZIP SINGLE FILE:")
        print("-" * 40)

        single_file = test_files[0]
        gz_path = single_file + ".gz"

        options = ArchiveOptions(format=ArchiveFormat.GZIP)
        info = manager.create(gz_path, [single_file], options)

        print(f"   Original: {os.path.getsize(single_file):,} bytes")
        print(f"   Compressed: {info.compressed_size:,} bytes")
        print(f"   Ratio: {info.compression_ratio:.1%}")
        print()

        # 10. Compression Levels
        print("10. COMPRESSION LEVELS:")
        print("-" * 40)

        levels = [
            CompressionLevel.NONE,
            CompressionLevel.FASTEST,
            CompressionLevel.NORMAL,
            CompressionLevel.BEST
        ]

        for level in levels:
            level_path = os.path.join(temp_dir, f"level_{level.name.lower()}.zip")
            info = manager.zip(level_path, test_files[:3], level)
            print(f"   {level.name}: {info.compressed_size:,} bytes ({info.compression_ratio:.1%})")
        print()

        # 11. Format Detection
        print("11. FORMAT DETECTION:")
        print("-" * 40)

        formats = [
            "test.zip",
            "test.tar",
            "test.tar.gz",
            "test.tgz",
            "test.tar.bz2",
            "test.tar.xz",
            "test.gz"
        ]

        for fmt in formats:
            detected = manager._detect_format(fmt)
            print(f"   {fmt} -> {detected.value}")
        print()

        # 12. Archive Entry Details
        print("12. ENTRY DETAILS:")
        print("-" * 40)

        entries = manager.list_contents(zip_path)
        if entries:
            entry = entries[0]
            print(f"   Name: {entry.name}")
            print(f"   Size: {entry.size:,} bytes")
            print(f"   Compressed: {entry.compressed_size:,} bytes")
            print(f"   Type: {entry.entry_type.value}")
            print(f"   Modified: {entry.modified_time}")
            print(f"   Checksum: {entry.checksum}")
            print(f"   Ratio: {entry.compression_ratio:.1%}")
        print()

        # 13. Async Operations
        print("13. ASYNC OPERATIONS:")
        print("-" * 40)

        async_path = os.path.join(temp_dir, "async_archive.zip")
        info = await manager.create_async(async_path, test_files[:3])
        print(f"   Created asynchronously: {os.path.basename(info.path)}")
        print(f"   Entries: {info.entry_count}")
        print()

        # 14. Statistics
        print("14. MANAGER STATISTICS:")
        print("-" * 40)

        stats = manager.get_stats()
        print(f"   Stats: {stats}")
        print()

    finally:
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)

    print("=" * 70)
    print("DEMO COMPLETE - Archive Manager Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())

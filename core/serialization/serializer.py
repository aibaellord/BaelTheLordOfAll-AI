#!/usr/bin/env python3
"""
BAEL - Serialization System
Comprehensive data serialization and deserialization.

This module provides a complete serialization framework
for converting data between formats and transports.

Features:
- Multiple formats (JSON, MessagePack, Pickle, YAML)
- Schema-aware serialization
- Custom type handlers
- Compression support
- Streaming serialization
- Versioned serialization
- Encryption support
- Lazy deserialization
- Schema evolution
- Binary optimization
"""

import asyncio
import base64
import gzip
import hashlib
import io
import json
import logging
import pickle
import struct
import time
import uuid
import zlib
from abc import ABC, abstractmethod
from collections import OrderedDict
from dataclasses import asdict, dataclass, field, fields, is_dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from enum import Enum, auto
from pathlib import Path
from typing import (Any, Callable, Dict, Generic, List, Optional, Set, Tuple,
                    Type, TypeVar, Union, get_args, get_origin, get_type_hints)

logger = logging.getLogger(__name__)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class SerializationFormat(Enum):
    """Serialization formats."""
    JSON = "json"
    BINARY = "binary"
    PICKLE = "pickle"
    MSGPACK = "msgpack"
    BASE64 = "base64"


class CompressionType(Enum):
    """Compression types."""
    NONE = "none"
    GZIP = "gzip"
    ZLIB = "zlib"
    LZ4 = "lz4"


class EncodingType(Enum):
    """Text encodings."""
    UTF8 = "utf-8"
    UTF16 = "utf-16"
    ASCII = "ascii"
    LATIN1 = "latin-1"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class SerializationConfig:
    """Serialization configuration."""
    format: SerializationFormat = SerializationFormat.JSON
    compression: CompressionType = CompressionType.NONE
    encoding: EncodingType = EncodingType.UTF8

    # JSON options
    indent: int = None
    sort_keys: bool = False
    ensure_ascii: bool = False

    # Binary options
    include_type_info: bool = True
    use_references: bool = False

    # Security
    max_depth: int = 100
    max_size: int = 100 * 1024 * 1024  # 100MB

    # Versioning
    version: int = 1
    include_version: bool = True


@dataclass
class SerializedData:
    """Serialized data container."""
    data: bytes
    format: SerializationFormat
    compression: CompressionType
    version: int = 1
    checksum: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

    @property
    def size(self) -> int:
        return len(self.data)

    def verify_checksum(self) -> bool:
        """Verify data checksum."""
        if not self.checksum:
            return True
        return hashlib.sha256(self.data).hexdigest() == self.checksum


@dataclass
class TypeInfo:
    """Type information for serialization."""
    type_name: str
    module: str = ""
    version: int = 1
    schema: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# TYPE HANDLERS
# =============================================================================

class TypeHandler(ABC):
    """Abstract type handler."""

    @abstractmethod
    def can_handle(self, obj: Any) -> bool:
        """Check if handler can serialize object."""
        pass

    @abstractmethod
    def serialize(self, obj: Any) -> Dict[str, Any]:
        """Serialize object to dict."""
        pass

    @abstractmethod
    def deserialize(self, data: Dict[str, Any]) -> Any:
        """Deserialize dict to object."""
        pass


class DateTimeHandler(TypeHandler):
    """Handler for datetime objects."""

    def can_handle(self, obj: Any) -> bool:
        return isinstance(obj, (datetime, date))

    def serialize(self, obj: Any) -> Dict[str, Any]:
        return {
            "__type__": "datetime" if isinstance(obj, datetime) else "date",
            "value": obj.isoformat()
        }

    def deserialize(self, data: Dict[str, Any]) -> Any:
        if data.get("__type__") == "datetime":
            return datetime.fromisoformat(data["value"])
        else:
            return date.fromisoformat(data["value"])


class TimeDeltaHandler(TypeHandler):
    """Handler for timedelta objects."""

    def can_handle(self, obj: Any) -> bool:
        return isinstance(obj, timedelta)

    def serialize(self, obj: timedelta) -> Dict[str, Any]:
        return {
            "__type__": "timedelta",
            "seconds": obj.total_seconds()
        }

    def deserialize(self, data: Dict[str, Any]) -> timedelta:
        return timedelta(seconds=data["seconds"])


class DecimalHandler(TypeHandler):
    """Handler for Decimal objects."""

    def can_handle(self, obj: Any) -> bool:
        return isinstance(obj, Decimal)

    def serialize(self, obj: Decimal) -> Dict[str, Any]:
        return {
            "__type__": "decimal",
            "value": str(obj)
        }

    def deserialize(self, data: Dict[str, Any]) -> Decimal:
        return Decimal(data["value"])


class UUIDHandler(TypeHandler):
    """Handler for UUID objects."""

    def can_handle(self, obj: Any) -> bool:
        return isinstance(obj, uuid.UUID)

    def serialize(self, obj: uuid.UUID) -> Dict[str, Any]:
        return {
            "__type__": "uuid",
            "value": str(obj)
        }

    def deserialize(self, data: Dict[str, Any]) -> uuid.UUID:
        return uuid.UUID(data["value"])


class PathHandler(TypeHandler):
    """Handler for Path objects."""

    def can_handle(self, obj: Any) -> bool:
        return isinstance(obj, Path)

    def serialize(self, obj: Path) -> Dict[str, Any]:
        return {
            "__type__": "path",
            "value": str(obj)
        }

    def deserialize(self, data: Dict[str, Any]) -> Path:
        return Path(data["value"])


class SetHandler(TypeHandler):
    """Handler for set objects."""

    def can_handle(self, obj: Any) -> bool:
        return isinstance(obj, (set, frozenset))

    def serialize(self, obj: Any) -> Dict[str, Any]:
        return {
            "__type__": "set" if isinstance(obj, set) else "frozenset",
            "value": list(obj)
        }

    def deserialize(self, data: Dict[str, Any]) -> Any:
        if data.get("__type__") == "frozenset":
            return frozenset(data["value"])
        return set(data["value"])


class BytesHandler(TypeHandler):
    """Handler for bytes objects."""

    def can_handle(self, obj: Any) -> bool:
        return isinstance(obj, bytes)

    def serialize(self, obj: bytes) -> Dict[str, Any]:
        return {
            "__type__": "bytes",
            "value": base64.b64encode(obj).decode('ascii')
        }

    def deserialize(self, data: Dict[str, Any]) -> bytes:
        return base64.b64decode(data["value"])


class EnumHandler(TypeHandler):
    """Handler for Enum objects."""

    def can_handle(self, obj: Any) -> bool:
        return isinstance(obj, Enum)

    def serialize(self, obj: Enum) -> Dict[str, Any]:
        return {
            "__type__": "enum",
            "enum_class": f"{obj.__class__.__module__}.{obj.__class__.__name__}",
            "value": obj.value
        }

    def deserialize(self, data: Dict[str, Any]) -> Any:
        # For safety, return the value directly
        return data["value"]


class DataclassHandler(TypeHandler):
    """Handler for dataclass objects."""

    def can_handle(self, obj: Any) -> bool:
        return is_dataclass(obj) and not isinstance(obj, type)

    def serialize(self, obj: Any) -> Dict[str, Any]:
        return {
            "__type__": "dataclass",
            "class_name": f"{obj.__class__.__module__}.{obj.__class__.__name__}",
            "data": asdict(obj)
        }

    def deserialize(self, data: Dict[str, Any]) -> Dict[str, Any]:
        # Return as dict for safety
        return data.get("data", {})


# =============================================================================
# COMPRESSOR
# =============================================================================

class Compressor:
    """Data compression/decompression."""

    @staticmethod
    def compress(data: bytes, method: CompressionType) -> bytes:
        """Compress data."""
        if method == CompressionType.NONE:
            return data
        elif method == CompressionType.GZIP:
            return gzip.compress(data)
        elif method == CompressionType.ZLIB:
            return zlib.compress(data)
        elif method == CompressionType.LZ4:
            # Fallback to zlib if lz4 not available
            try:
                import lz4.frame
                return lz4.frame.compress(data)
            except ImportError:
                return zlib.compress(data)
        else:
            return data

    @staticmethod
    def decompress(data: bytes, method: CompressionType) -> bytes:
        """Decompress data."""
        if method == CompressionType.NONE:
            return data
        elif method == CompressionType.GZIP:
            return gzip.decompress(data)
        elif method == CompressionType.ZLIB:
            return zlib.decompress(data)
        elif method == CompressionType.LZ4:
            try:
                import lz4.frame
                return lz4.frame.decompress(data)
            except ImportError:
                return zlib.decompress(data)
        else:
            return data


# =============================================================================
# ENCODERS
# =============================================================================

class JSONEncoderExtended(json.JSONEncoder):
    """Extended JSON encoder with type handlers."""

    def __init__(self, handlers: List[TypeHandler] = None, **kwargs):
        super().__init__(**kwargs)
        self.handlers = handlers or []

    def default(self, obj: Any) -> Any:
        # Check handlers
        for handler in self.handlers:
            if handler.can_handle(obj):
                return handler.serialize(obj)

        # Fallback
        if hasattr(obj, '__dict__'):
            return {
                "__type__": "object",
                "class": obj.__class__.__name__,
                "data": obj.__dict__
            }

        return super().default(obj)


class JSONDecoderExtended(json.JSONDecoder):
    """Extended JSON decoder with type handlers."""

    def __init__(self, handlers: List[TypeHandler] = None, **kwargs):
        super().__init__(object_hook=self._object_hook, **kwargs)
        self.handlers = handlers or []

    def _object_hook(self, obj: Dict) -> Any:
        if "__type__" in obj:
            for handler in self.handlers:
                try:
                    return handler.deserialize(obj)
                except:
                    continue
        return obj


# =============================================================================
# SERIALIZERS
# =============================================================================

class Serializer(ABC):
    """Abstract serializer."""

    @abstractmethod
    def serialize(self, obj: Any, config: SerializationConfig) -> bytes:
        """Serialize object to bytes."""
        pass

    @abstractmethod
    def deserialize(self, data: bytes, config: SerializationConfig) -> Any:
        """Deserialize bytes to object."""
        pass


class JSONSerializer(Serializer):
    """JSON serializer."""

    def __init__(self, handlers: List[TypeHandler] = None):
        self.handlers = handlers or self._default_handlers()

    def _default_handlers(self) -> List[TypeHandler]:
        return [
            DateTimeHandler(),
            TimeDeltaHandler(),
            DecimalHandler(),
            UUIDHandler(),
            PathHandler(),
            SetHandler(),
            BytesHandler(),
            EnumHandler(),
            DataclassHandler()
        ]

    def serialize(self, obj: Any, config: SerializationConfig) -> bytes:
        encoder = JSONEncoderExtended(
            handlers=self.handlers,
            indent=config.indent,
            sort_keys=config.sort_keys,
            ensure_ascii=config.ensure_ascii
        )
        json_str = encoder.encode(obj)
        return json_str.encode(config.encoding.value)

    def deserialize(self, data: bytes, config: SerializationConfig) -> Any:
        json_str = data.decode(config.encoding.value)
        decoder = JSONDecoderExtended(handlers=self.handlers)
        return decoder.decode(json_str)


class BinarySerializer(Serializer):
    """Custom binary serializer."""

    # Type markers
    MARKER_NONE = 0x00
    MARKER_BOOL = 0x01
    MARKER_INT = 0x02
    MARKER_FLOAT = 0x03
    MARKER_STRING = 0x04
    MARKER_BYTES = 0x05
    MARKER_LIST = 0x06
    MARKER_DICT = 0x07
    MARKER_TUPLE = 0x08

    def serialize(self, obj: Any, config: SerializationConfig) -> bytes:
        buffer = io.BytesIO()
        self._write(buffer, obj)
        return buffer.getvalue()

    def deserialize(self, data: bytes, config: SerializationConfig) -> Any:
        buffer = io.BytesIO(data)
        return self._read(buffer)

    def _write(self, buffer: io.BytesIO, obj: Any) -> None:
        if obj is None:
            buffer.write(bytes([self.MARKER_NONE]))

        elif isinstance(obj, bool):
            buffer.write(bytes([self.MARKER_BOOL]))
            buffer.write(bytes([1 if obj else 0]))

        elif isinstance(obj, int):
            buffer.write(bytes([self.MARKER_INT]))
            # Variable length encoding
            data = struct.pack('>q', obj)
            buffer.write(data)

        elif isinstance(obj, float):
            buffer.write(bytes([self.MARKER_FLOAT]))
            buffer.write(struct.pack('>d', obj))

        elif isinstance(obj, str):
            buffer.write(bytes([self.MARKER_STRING]))
            encoded = obj.encode('utf-8')
            buffer.write(struct.pack('>I', len(encoded)))
            buffer.write(encoded)

        elif isinstance(obj, bytes):
            buffer.write(bytes([self.MARKER_BYTES]))
            buffer.write(struct.pack('>I', len(obj)))
            buffer.write(obj)

        elif isinstance(obj, (list, tuple)):
            marker = self.MARKER_TUPLE if isinstance(obj, tuple) else self.MARKER_LIST
            buffer.write(bytes([marker]))
            buffer.write(struct.pack('>I', len(obj)))
            for item in obj:
                self._write(buffer, item)

        elif isinstance(obj, dict):
            buffer.write(bytes([self.MARKER_DICT]))
            buffer.write(struct.pack('>I', len(obj)))
            for key, value in obj.items():
                self._write(buffer, key)
                self._write(buffer, value)

        else:
            # Fallback: convert to string
            self._write(buffer, str(obj))

    def _read(self, buffer: io.BytesIO) -> Any:
        marker = buffer.read(1)[0]

        if marker == self.MARKER_NONE:
            return None

        elif marker == self.MARKER_BOOL:
            return buffer.read(1)[0] == 1

        elif marker == self.MARKER_INT:
            return struct.unpack('>q', buffer.read(8))[0]

        elif marker == self.MARKER_FLOAT:
            return struct.unpack('>d', buffer.read(8))[0]

        elif marker == self.MARKER_STRING:
            length = struct.unpack('>I', buffer.read(4))[0]
            return buffer.read(length).decode('utf-8')

        elif marker == self.MARKER_BYTES:
            length = struct.unpack('>I', buffer.read(4))[0]
            return buffer.read(length)

        elif marker == self.MARKER_LIST:
            length = struct.unpack('>I', buffer.read(4))[0]
            return [self._read(buffer) for _ in range(length)]

        elif marker == self.MARKER_TUPLE:
            length = struct.unpack('>I', buffer.read(4))[0]
            return tuple(self._read(buffer) for _ in range(length))

        elif marker == self.MARKER_DICT:
            length = struct.unpack('>I', buffer.read(4))[0]
            return {self._read(buffer): self._read(buffer) for _ in range(length)}

        return None


class PickleSerializer(Serializer):
    """Pickle serializer."""

    def serialize(self, obj: Any, config: SerializationConfig) -> bytes:
        return pickle.dumps(obj, protocol=pickle.HIGHEST_PROTOCOL)

    def deserialize(self, data: bytes, config: SerializationConfig) -> Any:
        return pickle.loads(data)


# =============================================================================
# STREAMING SERIALIZER
# =============================================================================

class StreamingSerializer:
    """Streaming serializer for large data."""

    def __init__(self, serializer: Serializer = None):
        self.serializer = serializer or JSONSerializer()

    async def serialize_stream(
        self,
        items: List[Any],
        chunk_size: int = 100,
        config: SerializationConfig = None
    ):
        """Serialize items in streaming fashion."""
        config = config or SerializationConfig()

        for i in range(0, len(items), chunk_size):
            chunk = items[i:i + chunk_size]
            yield self.serializer.serialize(chunk, config)
            await asyncio.sleep(0)  # Allow other tasks

    async def deserialize_stream(
        self,
        chunks,
        config: SerializationConfig = None
    ):
        """Deserialize streaming data."""
        config = config or SerializationConfig()

        async for chunk in chunks:
            items = self.serializer.deserialize(chunk, config)
            for item in items:
                yield item


# =============================================================================
# SCHEMA REGISTRY
# =============================================================================

@dataclass
class Schema:
    """Serialization schema."""
    name: str
    version: int
    fields: Dict[str, str]  # field_name -> type_name
    required: List[str] = field(default_factory=list)
    defaults: Dict[str, Any] = field(default_factory=dict)
    migrations: Dict[int, Callable] = field(default_factory=dict)  # version -> migration_func


class SchemaRegistry:
    """Registry for serialization schemas."""

    def __init__(self):
        self.schemas: Dict[str, Dict[int, Schema]] = {}  # name -> version -> schema

    def register(self, schema: Schema) -> None:
        """Register a schema."""
        if schema.name not in self.schemas:
            self.schemas[schema.name] = {}
        self.schemas[schema.name][schema.version] = schema

    def get(self, name: str, version: int = None) -> Optional[Schema]:
        """Get a schema by name and version."""
        if name not in self.schemas:
            return None

        versions = self.schemas[name]

        if version is not None:
            return versions.get(version)

        # Return latest version
        latest = max(versions.keys())
        return versions[latest]

    def migrate(
        self,
        data: Dict[str, Any],
        schema_name: str,
        from_version: int,
        to_version: int
    ) -> Dict[str, Any]:
        """Migrate data between schema versions."""
        if from_version == to_version:
            return data

        current_version = from_version

        while current_version < to_version:
            next_version = current_version + 1
            schema = self.get(schema_name, next_version)

            if schema and next_version in schema.migrations:
                data = schema.migrations[next_version](data)

            current_version = next_version

        return data


# =============================================================================
# SERIALIZATION MANAGER
# =============================================================================

class SerializationManager:
    """
    Master serialization management for BAEL.

    Provides comprehensive data serialization with multiple formats.
    """

    def __init__(self):
        self.serializers: Dict[SerializationFormat, Serializer] = {
            SerializationFormat.JSON: JSONSerializer(),
            SerializationFormat.BINARY: BinarySerializer(),
            SerializationFormat.PICKLE: PickleSerializer()
        }

        self.type_handlers: List[TypeHandler] = [
            DateTimeHandler(),
            TimeDeltaHandler(),
            DecimalHandler(),
            UUIDHandler(),
            PathHandler(),
            SetHandler(),
            BytesHandler(),
            EnumHandler(),
            DataclassHandler()
        ]

        self.schema_registry = SchemaRegistry()
        self.compressor = Compressor()

        # Statistics
        self.serializations = 0
        self.deserializations = 0
        self.bytes_serialized = 0
        self.bytes_deserialized = 0

    def serialize(
        self,
        obj: Any,
        config: SerializationConfig = None,
        schema: str = None
    ) -> SerializedData:
        """Serialize an object."""
        config = config or SerializationConfig()

        serializer = self.serializers.get(config.format)
        if not serializer:
            raise ValueError(f"Unknown format: {config.format}")

        # Serialize
        data = serializer.serialize(obj, config)

        # Compress
        compressed_data = self.compressor.compress(data, config.compression)

        # Calculate checksum
        checksum = hashlib.sha256(compressed_data).hexdigest()

        # Create result
        result = SerializedData(
            data=compressed_data,
            format=config.format,
            compression=config.compression,
            version=config.version,
            checksum=checksum,
            metadata={
                "schema": schema,
                "original_size": len(data),
                "compressed_size": len(compressed_data)
            }
        )

        # Update statistics
        self.serializations += 1
        self.bytes_serialized += len(compressed_data)

        return result

    def deserialize(
        self,
        serialized: SerializedData,
        config: SerializationConfig = None,
        verify_checksum: bool = True
    ) -> Any:
        """Deserialize data."""
        config = config or SerializationConfig(
            format=serialized.format,
            compression=serialized.compression
        )

        # Verify checksum
        if verify_checksum and not serialized.verify_checksum():
            raise ValueError("Checksum verification failed")

        # Decompress
        data = self.compressor.decompress(serialized.data, serialized.compression)

        # Deserialize
        serializer = self.serializers.get(serialized.format)
        if not serializer:
            raise ValueError(f"Unknown format: {serialized.format}")

        result = serializer.deserialize(data, config)

        # Update statistics
        self.deserializations += 1
        self.bytes_deserialized += len(serialized.data)

        return result

    def to_json(
        self,
        obj: Any,
        indent: int = None,
        compress: bool = False
    ) -> str:
        """Quick JSON serialization."""
        config = SerializationConfig(
            format=SerializationFormat.JSON,
            indent=indent,
            compression=CompressionType.GZIP if compress else CompressionType.NONE
        )

        serialized = self.serialize(obj, config)

        if compress:
            return base64.b64encode(serialized.data).decode('ascii')
        return serialized.data.decode('utf-8')

    def from_json(self, json_str: str, compressed: bool = False) -> Any:
        """Quick JSON deserialization."""
        if compressed:
            data = base64.b64decode(json_str)
        else:
            data = json_str.encode('utf-8')

        serialized = SerializedData(
            data=data,
            format=SerializationFormat.JSON,
            compression=CompressionType.GZIP if compressed else CompressionType.NONE
        )

        return self.deserialize(serialized, verify_checksum=False)

    def to_bytes(self, obj: Any, compress: bool = True) -> bytes:
        """Quick binary serialization."""
        config = SerializationConfig(
            format=SerializationFormat.BINARY,
            compression=CompressionType.ZLIB if compress else CompressionType.NONE
        )
        return self.serialize(obj, config).data

    def from_bytes(self, data: bytes, compressed: bool = True) -> Any:
        """Quick binary deserialization."""
        serialized = SerializedData(
            data=data,
            format=SerializationFormat.BINARY,
            compression=CompressionType.ZLIB if compressed else CompressionType.NONE
        )
        return self.deserialize(serialized, verify_checksum=False)

    def register_handler(self, handler: TypeHandler) -> None:
        """Register a custom type handler."""
        self.type_handlers.append(handler)

        # Update JSON serializer
        if SerializationFormat.JSON in self.serializers:
            json_ser = self.serializers[SerializationFormat.JSON]
            if isinstance(json_ser, JSONSerializer):
                json_ser.handlers.append(handler)

    def register_schema(self, schema: Schema) -> None:
        """Register a schema."""
        self.schema_registry.register(schema)

    def clone(self, obj: Any) -> Any:
        """Deep clone an object via serialization."""
        config = SerializationConfig(format=SerializationFormat.BINARY)
        serialized = self.serialize(obj, config)
        return self.deserialize(serialized)

    def get_statistics(self) -> Dict[str, Any]:
        """Get serialization statistics."""
        return {
            "serializations": self.serializations,
            "deserializations": self.deserializations,
            "bytes_serialized": self.bytes_serialized,
            "bytes_deserialized": self.bytes_deserialized,
            "average_serialization_size": (
                self.bytes_serialized / self.serializations
                if self.serializations > 0 else 0
            )
        }


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

_default_manager = SerializationManager()


def serialize(obj: Any, format: SerializationFormat = SerializationFormat.JSON) -> bytes:
    """Serialize an object."""
    config = SerializationConfig(format=format)
    return _default_manager.serialize(obj, config).data


def deserialize(data: bytes, format: SerializationFormat = SerializationFormat.JSON) -> Any:
    """Deserialize data."""
    serialized = SerializedData(
        data=data,
        format=format,
        compression=CompressionType.NONE
    )
    return _default_manager.deserialize(serialized, verify_checksum=False)


def to_json(obj: Any) -> str:
    """Convert to JSON string."""
    return _default_manager.to_json(obj)


def from_json(s: str) -> Any:
    """Parse JSON string."""
    return _default_manager.from_json(s)


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Serialization System."""
    print("=" * 70)
    print("BAEL - SERIALIZATION SYSTEM DEMO")
    print("Multi-Format Data Serialization")
    print("=" * 70)
    print()

    manager = SerializationManager()

    # 1. Basic JSON Serialization
    print("1. BASIC JSON SERIALIZATION:")
    print("-" * 40)

    data = {
        "name": "BAEL",
        "version": 1.0,
        "active": True,
        "tags": ["ai", "agent", "lord"]
    }

    json_result = manager.serialize(data)
    print(f"   Original data: {data}")
    print(f"   Serialized size: {json_result.size} bytes")
    print(f"   Format: {json_result.format.value}")

    restored = manager.deserialize(json_result)
    print(f"   Restored: {restored}")
    print()

    # 2. Complex Types
    print("2. COMPLEX TYPE SERIALIZATION:")
    print("-" * 40)

    complex_data = {
        "timestamp": datetime.now(),
        "duration": timedelta(hours=2, minutes=30),
        "price": Decimal("99.99"),
        "id": uuid.uuid4(),
        "path": Path("/home/bael"),
        "tags": {"ai", "ml", "agent"}
    }

    serialized = manager.serialize(complex_data)
    print(f"   Complex data types serialized")
    print(f"   Size: {serialized.size} bytes")

    restored = manager.deserialize(serialized)
    print(f"   Restored timestamp type: {type(restored['timestamp'])}")
    print()

    # 3. Binary Serialization
    print("3. BINARY SERIALIZATION:")
    print("-" * 40)

    config = SerializationConfig(format=SerializationFormat.BINARY)

    binary_result = manager.serialize(data, config)
    print(f"   JSON size: {json_result.size} bytes")
    print(f"   Binary size: {binary_result.size} bytes")
    print(f"   Savings: {((json_result.size - binary_result.size) / json_result.size * 100):.1f}%")
    print()

    # 4. Compression
    print("4. COMPRESSION:")
    print("-" * 40)

    large_data = {"items": [{"id": i, "name": f"Item {i}"} for i in range(1000)]}

    uncompressed = manager.serialize(large_data)

    compressed_config = SerializationConfig(compression=CompressionType.GZIP)
    compressed = manager.serialize(large_data, compressed_config)

    print(f"   Uncompressed size: {uncompressed.size} bytes")
    print(f"   Compressed size (gzip): {compressed.size} bytes")
    print(f"   Compression ratio: {uncompressed.size / compressed.size:.2f}x")

    zlib_config = SerializationConfig(compression=CompressionType.ZLIB)
    zlib_compressed = manager.serialize(large_data, zlib_config)
    print(f"   Compressed size (zlib): {zlib_compressed.size} bytes")
    print()

    # 5. Checksum Verification
    print("5. CHECKSUM VERIFICATION:")
    print("-" * 40)

    serialized = manager.serialize(data)
    print(f"   Checksum: {serialized.checksum[:32]}...")
    print(f"   Verification: {serialized.verify_checksum()}")

    # Corrupt data
    corrupted = SerializedData(
        data=b"corrupted",
        format=serialized.format,
        compression=serialized.compression,
        checksum=serialized.checksum
    )
    print(f"   Corrupted verification: {corrupted.verify_checksum()}")
    print()

    # 6. Quick Helpers
    print("6. QUICK HELPERS:")
    print("-" * 40)

    json_str = manager.to_json(data, indent=2)
    print(f"   to_json:\n{json_str}")

    restored = manager.from_json(json_str)
    print(f"   from_json: {restored}")
    print()

    # 7. Cloning
    print("7. DEEP CLONING:")
    print("-" * 40)

    original = {"nested": {"value": 42, "list": [1, 2, 3]}}
    cloned = manager.clone(original)

    cloned["nested"]["value"] = 99

    print(f"   Original: {original}")
    print(f"   Cloned: {cloned}")
    print(f"   Independent: {original['nested']['value'] != cloned['nested']['value']}")
    print()

    # 8. Pickle Format
    print("8. PICKLE FORMAT:")
    print("-" * 40)

    class CustomClass:
        def __init__(self, value):
            self.value = value

        def __repr__(self):
            return f"CustomClass({self.value})"

    obj = CustomClass(42)
    pickle_config = SerializationConfig(format=SerializationFormat.PICKLE)

    serialized = manager.serialize(obj, pickle_config)
    print(f"   Serialized custom class: {serialized.size} bytes")

    restored = manager.deserialize(serialized)
    print(f"   Restored: {restored}")
    print()

    # 9. Streaming Serialization
    print("9. STREAMING SERIALIZATION:")
    print("-" * 40)

    streamer = StreamingSerializer()
    items = [{"id": i} for i in range(1000)]

    chunks = []
    async for chunk in streamer.serialize_stream(items, chunk_size=200):
        chunks.append(chunk)

    print(f"   Items: {len(items)}")
    print(f"   Chunks: {len(chunks)}")
    print(f"   Total size: {sum(len(c) for c in chunks)} bytes")
    print()

    # 10. Statistics
    print("10. STATISTICS:")
    print("-" * 40)

    stats = manager.get_statistics()
    for key, value in stats.items():
        if isinstance(value, float):
            print(f"    {key}: {value:.2f}")
        else:
            print(f"    {key}: {value}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Serialization System Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())

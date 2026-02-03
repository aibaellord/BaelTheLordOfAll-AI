#!/usr/bin/env python3
"""
BAEL - Serialization Engine
Data serialization and deserialization for agents.

Features:
- Multi-format support (JSON, MessagePack, Pickle)
- Schema-based serialization
- Custom serializers
- Compression
- Versioning
"""

import asyncio
import base64
import gzip
import hashlib
import json
import pickle
import struct
import time
import uuid
import zlib
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import (Any, Callable, Dict, Generic, Iterator, List, Optional,
                    Set, Tuple, Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class SerialFormat(Enum):
    """Serialization formats."""
    JSON = "json"
    PICKLE = "pickle"
    BINARY = "binary"
    BASE64 = "base64"
    MSGPACK = "msgpack"


class Compression(Enum):
    """Compression algorithms."""
    NONE = "none"
    GZIP = "gzip"
    ZLIB = "zlib"


class EncodingType(Enum):
    """String encodings."""
    UTF8 = "utf-8"
    ASCII = "ascii"
    LATIN1 = "latin-1"


class TypeCode(Enum):
    """Type codes for binary serialization."""
    NULL = 0
    BOOL = 1
    INT = 2
    FLOAT = 3
    STRING = 4
    BYTES = 5
    LIST = 6
    DICT = 7
    DATETIME = 8
    CUSTOM = 9


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class SerializationConfig:
    """Serialization configuration."""
    format: SerialFormat = SerialFormat.JSON
    compression: Compression = Compression.NONE
    encoding: EncodingType = EncodingType.UTF8
    pretty: bool = False
    include_type_info: bool = False
    version: int = 1


@dataclass
class SerializedData:
    """Serialized data container."""
    data: bytes = b""
    format: SerialFormat = SerialFormat.JSON
    compression: Compression = Compression.NONE
    original_size: int = 0
    compressed_size: int = 0
    checksum: str = ""
    version: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Schema:
    """Serialization schema."""
    schema_id: str = ""
    name: str = ""
    version: int = 1
    fields: Dict[str, Type] = field(default_factory=dict)
    required: Set[str] = field(default_factory=set)
    defaults: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.schema_id:
            self.schema_id = str(uuid.uuid4())[:8]


# =============================================================================
# TYPE CONVERTER
# =============================================================================

class TypeConverter:
    """Convert types for serialization."""

    def __init__(self):
        self._serializers: Dict[Type, Callable] = {}
        self._deserializers: Dict[str, Callable] = {}

        self._register_defaults()

    def _register_defaults(self) -> None:
        """Register default converters."""
        self.register(datetime, self._serialize_datetime, self._deserialize_datetime)
        self.register(date, self._serialize_date, self._deserialize_date)
        self.register(Decimal, self._serialize_decimal, self._deserialize_decimal)
        self.register(bytes, self._serialize_bytes, self._deserialize_bytes)
        self.register(set, self._serialize_set, self._deserialize_set)
        self.register(Path, self._serialize_path, self._deserialize_path)

    def register(
        self,
        typ: Type,
        serializer: Callable,
        deserializer: Callable
    ) -> None:
        """Register type converter."""
        self._serializers[typ] = serializer
        self._deserializers[typ.__name__] = deserializer

    def serialize(self, value: Any) -> Any:
        """Serialize value."""
        if value is None:
            return None

        value_type = type(value)

        if value_type in self._serializers:
            return {
                "__type__": value_type.__name__,
                "__value__": self._serializers[value_type](value)
            }

        if isinstance(value, Enum):
            return {
                "__type__": "enum",
                "__enum__": type(value).__name__,
                "__value__": value.value
            }

        if is_dataclass(value):
            return {
                "__type__": "dataclass",
                "__class__": type(value).__name__,
                "__value__": asdict(value)
            }

        if isinstance(value, (list, tuple)):
            return [self.serialize(v) for v in value]

        if isinstance(value, dict):
            return {k: self.serialize(v) for k, v in value.items()}

        return value

    def deserialize(self, value: Any, type_hint: Optional[Type] = None) -> Any:
        """Deserialize value."""
        if value is None:
            return None

        if isinstance(value, dict) and "__type__" in value:
            type_name = value["__type__"]

            if type_name in self._deserializers:
                return self._deserializers[type_name](value["__value__"])

            if type_name == "enum":
                return value["__value__"]

            if type_name == "dataclass":
                return value["__value__"]

        if isinstance(value, list):
            return [self.deserialize(v) for v in value]

        if isinstance(value, dict):
            return {k: self.deserialize(v) for k, v in value.items()}

        return value

    def _serialize_datetime(self, dt: datetime) -> str:
        return dt.isoformat()

    def _deserialize_datetime(self, s: str) -> datetime:
        return datetime.fromisoformat(s)

    def _serialize_date(self, d: date) -> str:
        return d.isoformat()

    def _deserialize_date(self, s: str) -> date:
        return date.fromisoformat(s)

    def _serialize_decimal(self, d: Decimal) -> str:
        return str(d)

    def _deserialize_decimal(self, s: str) -> Decimal:
        return Decimal(s)

    def _serialize_bytes(self, b: bytes) -> str:
        return base64.b64encode(b).decode('ascii')

    def _deserialize_bytes(self, s: str) -> bytes:
        return base64.b64decode(s)

    def _serialize_set(self, s: set) -> list:
        return list(s)

    def _deserialize_set(self, lst: list) -> set:
        return set(lst)

    def _serialize_path(self, p: Path) -> str:
        return str(p)

    def _deserialize_path(self, s: str) -> Path:
        return Path(s)


# =============================================================================
# COMPRESSOR
# =============================================================================

class Compressor:
    """Compress and decompress data."""

    def compress(self, data: bytes, method: Compression) -> bytes:
        """Compress data."""
        if method == Compression.NONE:
            return data
        elif method == Compression.GZIP:
            return gzip.compress(data)
        elif method == Compression.ZLIB:
            return zlib.compress(data)

        return data

    def decompress(self, data: bytes, method: Compression) -> bytes:
        """Decompress data."""
        if method == Compression.NONE:
            return data
        elif method == Compression.GZIP:
            return gzip.decompress(data)
        elif method == Compression.ZLIB:
            return zlib.decompress(data)

        return data


# =============================================================================
# JSON SERIALIZER
# =============================================================================

class JSONSerializer:
    """JSON serializer."""

    def __init__(self, converter: TypeConverter):
        self._converter = converter

    def serialize(
        self,
        data: Any,
        pretty: bool = False,
        encoding: EncodingType = EncodingType.UTF8
    ) -> bytes:
        """Serialize to JSON."""
        converted = self._converter.serialize(data)

        if pretty:
            json_str = json.dumps(converted, indent=2, ensure_ascii=False)
        else:
            json_str = json.dumps(converted, separators=(',', ':'), ensure_ascii=False)

        return json_str.encode(encoding.value)

    def deserialize(
        self,
        data: bytes,
        encoding: EncodingType = EncodingType.UTF8
    ) -> Any:
        """Deserialize from JSON."""
        json_str = data.decode(encoding.value)
        parsed = json.loads(json_str)

        return self._converter.deserialize(parsed)


# =============================================================================
# PICKLE SERIALIZER
# =============================================================================

class PickleSerializer:
    """Pickle serializer."""

    def serialize(self, data: Any, protocol: int = pickle.HIGHEST_PROTOCOL) -> bytes:
        """Serialize to pickle."""
        return pickle.dumps(data, protocol=protocol)

    def deserialize(self, data: bytes) -> Any:
        """Deserialize from pickle."""
        return pickle.loads(data)


# =============================================================================
# BINARY SERIALIZER
# =============================================================================

class BinarySerializer:
    """Custom binary serializer."""

    def serialize(self, data: Any) -> bytes:
        """Serialize to binary format."""
        return self._encode_value(data)

    def deserialize(self, data: bytes) -> Any:
        """Deserialize from binary format."""
        value, _ = self._decode_value(data, 0)
        return value

    def _encode_value(self, value: Any) -> bytes:
        """Encode a value to bytes."""
        if value is None:
            return struct.pack('B', TypeCode.NULL.value)

        elif isinstance(value, bool):
            return struct.pack('BB', TypeCode.BOOL.value, 1 if value else 0)

        elif isinstance(value, int):
            return struct.pack('Bq', TypeCode.INT.value, value)

        elif isinstance(value, float):
            return struct.pack('Bd', TypeCode.FLOAT.value, value)

        elif isinstance(value, str):
            encoded = value.encode('utf-8')
            return struct.pack('BI', TypeCode.STRING.value, len(encoded)) + encoded

        elif isinstance(value, bytes):
            return struct.pack('BI', TypeCode.BYTES.value, len(value)) + value

        elif isinstance(value, (list, tuple)):
            items = b''.join(self._encode_value(v) for v in value)
            return struct.pack('BI', TypeCode.LIST.value, len(value)) + items

        elif isinstance(value, dict):
            items = b''
            for k, v in value.items():
                items += self._encode_value(k) + self._encode_value(v)
            return struct.pack('BI', TypeCode.DICT.value, len(value)) + items

        elif isinstance(value, datetime):
            ts = value.timestamp()
            return struct.pack('Bd', TypeCode.DATETIME.value, ts)

        else:
            pickled = pickle.dumps(value)
            return struct.pack('BI', TypeCode.CUSTOM.value, len(pickled)) + pickled

    def _decode_value(self, data: bytes, offset: int) -> Tuple[Any, int]:
        """Decode a value from bytes."""
        type_code = struct.unpack_from('B', data, offset)[0]
        offset += 1

        if type_code == TypeCode.NULL.value:
            return None, offset

        elif type_code == TypeCode.BOOL.value:
            value = struct.unpack_from('B', data, offset)[0]
            return bool(value), offset + 1

        elif type_code == TypeCode.INT.value:
            value = struct.unpack_from('q', data, offset)[0]
            return value, offset + 8

        elif type_code == TypeCode.FLOAT.value:
            value = struct.unpack_from('d', data, offset)[0]
            return value, offset + 8

        elif type_code == TypeCode.STRING.value:
            length = struct.unpack_from('I', data, offset)[0]
            offset += 4
            value = data[offset:offset + length].decode('utf-8')
            return value, offset + length

        elif type_code == TypeCode.BYTES.value:
            length = struct.unpack_from('I', data, offset)[0]
            offset += 4
            value = data[offset:offset + length]
            return value, offset + length

        elif type_code == TypeCode.LIST.value:
            count = struct.unpack_from('I', data, offset)[0]
            offset += 4
            items = []
            for _ in range(count):
                value, offset = self._decode_value(data, offset)
                items.append(value)
            return items, offset

        elif type_code == TypeCode.DICT.value:
            count = struct.unpack_from('I', data, offset)[0]
            offset += 4
            result = {}
            for _ in range(count):
                key, offset = self._decode_value(data, offset)
                value, offset = self._decode_value(data, offset)
                result[key] = value
            return result, offset

        elif type_code == TypeCode.DATETIME.value:
            ts = struct.unpack_from('d', data, offset)[0]
            return datetime.fromtimestamp(ts), offset + 8

        elif type_code == TypeCode.CUSTOM.value:
            length = struct.unpack_from('I', data, offset)[0]
            offset += 4
            value = pickle.loads(data[offset:offset + length])
            return value, offset + length

        return None, offset


# =============================================================================
# SERIALIZATION ENGINE
# =============================================================================

class SerializationEngine:
    """
    Serialization Engine for BAEL.

    Data serialization and deserialization.
    """

    def __init__(self, config: Optional[SerializationConfig] = None):
        self._config = config or SerializationConfig()

        self._converter = TypeConverter()
        self._compressor = Compressor()

        self._json = JSONSerializer(self._converter)
        self._pickle = PickleSerializer()
        self._binary = BinarySerializer()

        self._schemas: Dict[str, Schema] = {}

    # ----- Serialize -----

    def serialize(
        self,
        data: Any,
        format: Optional[SerialFormat] = None,
        compression: Optional[Compression] = None,
        **kwargs
    ) -> SerializedData:
        """Serialize data."""
        fmt = format or self._config.format
        comp = compression or self._config.compression

        if fmt == SerialFormat.JSON:
            raw = self._json.serialize(
                data,
                pretty=kwargs.get('pretty', self._config.pretty),
                encoding=self._config.encoding
            )
        elif fmt == SerialFormat.PICKLE:
            raw = self._pickle.serialize(data)
        elif fmt == SerialFormat.BINARY:
            raw = self._binary.serialize(data)
        elif fmt == SerialFormat.BASE64:
            json_bytes = self._json.serialize(data)
            raw = base64.b64encode(json_bytes)
        else:
            raw = self._json.serialize(data)

        original_size = len(raw)

        compressed = self._compressor.compress(raw, comp)

        checksum = hashlib.sha256(compressed).hexdigest()[:16]

        return SerializedData(
            data=compressed,
            format=fmt,
            compression=comp,
            original_size=original_size,
            compressed_size=len(compressed),
            checksum=checksum,
            version=self._config.version
        )

    def deserialize(
        self,
        serialized: Union[SerializedData, bytes],
        format: Optional[SerialFormat] = None,
        compression: Optional[Compression] = None
    ) -> Any:
        """Deserialize data."""
        if isinstance(serialized, SerializedData):
            data = serialized.data
            fmt = serialized.format
            comp = serialized.compression
        else:
            data = serialized
            fmt = format or self._config.format
            comp = compression or self._config.compression

        decompressed = self._compressor.decompress(data, comp)

        if fmt == SerialFormat.JSON:
            return self._json.deserialize(decompressed, self._config.encoding)
        elif fmt == SerialFormat.PICKLE:
            return self._pickle.deserialize(decompressed)
        elif fmt == SerialFormat.BINARY:
            return self._binary.deserialize(decompressed)
        elif fmt == SerialFormat.BASE64:
            json_bytes = base64.b64decode(decompressed)
            return self._json.deserialize(json_bytes)

        return self._json.deserialize(decompressed)

    # ----- Format-specific shortcuts -----

    def to_json(self, data: Any, pretty: bool = False) -> str:
        """Serialize to JSON string."""
        result = self.serialize(data, SerialFormat.JSON, pretty=pretty)
        return result.data.decode(self._config.encoding.value)

    def from_json(self, json_str: str) -> Any:
        """Deserialize from JSON string."""
        return self.deserialize(
            json_str.encode(self._config.encoding.value),
            SerialFormat.JSON
        )

    def to_bytes(self, data: Any) -> bytes:
        """Serialize to bytes."""
        result = self.serialize(data, SerialFormat.BINARY)
        return result.data

    def from_bytes(self, data: bytes) -> Any:
        """Deserialize from bytes."""
        return self.deserialize(data, SerialFormat.BINARY)

    def to_base64(self, data: Any) -> str:
        """Serialize to base64 string."""
        result = self.serialize(data, SerialFormat.BASE64)
        return result.data.decode('ascii')

    def from_base64(self, b64_str: str) -> Any:
        """Deserialize from base64 string."""
        return self.deserialize(
            b64_str.encode('ascii'),
            SerialFormat.BASE64
        )

    # ----- Compression shortcuts -----

    def compress(self, data: bytes, method: Compression = Compression.GZIP) -> bytes:
        """Compress data."""
        return self._compressor.compress(data, method)

    def decompress(self, data: bytes, method: Compression = Compression.GZIP) -> bytes:
        """Decompress data."""
        return self._compressor.decompress(data, method)

    # ----- Type registration -----

    def register_type(
        self,
        typ: Type,
        serializer: Callable,
        deserializer: Callable
    ) -> None:
        """Register custom type converter."""
        self._converter.register(typ, serializer, deserializer)

    # ----- Schema operations -----

    def create_schema(
        self,
        name: str,
        fields: Dict[str, Type],
        required: Optional[Set[str]] = None,
        defaults: Optional[Dict[str, Any]] = None
    ) -> Schema:
        """Create a serialization schema."""
        schema = Schema(
            name=name,
            fields=fields,
            required=required or set(),
            defaults=defaults or {}
        )

        self._schemas[name] = schema

        return schema

    def validate_schema(self, data: Dict[str, Any], schema_name: str) -> Tuple[bool, List[str]]:
        """Validate data against schema."""
        schema = self._schemas.get(schema_name)

        if not schema:
            return False, [f"Schema not found: {schema_name}"]

        errors = []

        for field_name in schema.required:
            if field_name not in data:
                errors.append(f"Missing required field: {field_name}")

        for field_name, field_type in schema.fields.items():
            if field_name in data:
                value = data[field_name]
                if not isinstance(value, field_type):
                    errors.append(
                        f"Type mismatch for {field_name}: "
                        f"expected {field_type.__name__}, got {type(value).__name__}"
                    )

        return len(errors) == 0, errors

    # ----- Utilities -----

    def checksum(self, data: bytes) -> str:
        """Calculate checksum."""
        return hashlib.sha256(data).hexdigest()

    def verify(self, serialized: SerializedData) -> bool:
        """Verify serialized data integrity."""
        calculated = hashlib.sha256(serialized.data).hexdigest()[:16]
        return calculated == serialized.checksum

    def summary(self) -> Dict[str, Any]:
        """Get engine summary."""
        return {
            "default_format": self._config.format.value,
            "default_compression": self._config.compression.value,
            "encoding": self._config.encoding.value,
            "version": self._config.version,
            "schemas": len(self._schemas)
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Serialization Engine."""
    print("=" * 70)
    print("BAEL - SERIALIZATION ENGINE DEMO")
    print("Data Serialization and Deserialization")
    print("=" * 70)
    print()

    engine = SerializationEngine()

    # 1. JSON Serialization
    print("1. JSON SERIALIZATION:")
    print("-" * 40)

    data = {
        "name": "Alice",
        "age": 30,
        "scores": [95, 87, 92],
        "active": True
    }

    json_str = engine.to_json(data)
    print(f"   Original: {data}")
    print(f"   JSON: {json_str}")

    restored = engine.from_json(json_str)
    print(f"   Restored: {restored}")
    print()

    # 2. Pretty JSON
    print("2. PRETTY JSON:")
    print("-" * 40)

    pretty = engine.to_json(data, pretty=True)
    print("   Pretty formatted:")
    for line in pretty.split('\n')[:5]:
        print(f"   {line}")
    print()

    # 3. Binary Serialization
    print("3. BINARY SERIALIZATION:")
    print("-" * 40)

    binary = engine.to_bytes(data)
    print(f"   Binary size: {len(binary)} bytes")
    print(f"   First 20 bytes: {binary[:20]}")

    restored = engine.from_bytes(binary)
    print(f"   Restored: {restored}")
    print()

    # 4. Base64 Serialization
    print("4. BASE64 SERIALIZATION:")
    print("-" * 40)

    b64 = engine.to_base64(data)
    print(f"   Base64: {b64[:50]}...")

    restored = engine.from_base64(b64)
    print(f"   Restored: {restored}")
    print()

    # 5. Compression
    print("5. COMPRESSION:")
    print("-" * 40)

    large_data = {"items": list(range(1000))}

    result = engine.serialize(large_data, compression=Compression.NONE)
    print(f"   Uncompressed size: {result.original_size} bytes")

    result = engine.serialize(large_data, compression=Compression.GZIP)
    print(f"   GZIP compressed: {result.compressed_size} bytes")
    print(f"   Compression ratio: {result.original_size / result.compressed_size:.2f}x")

    restored = engine.deserialize(result)
    print(f"   Restored items count: {len(restored['items'])}")
    print()

    # 6. Complex Types
    print("6. COMPLEX TYPES:")
    print("-" * 40)

    complex_data = {
        "timestamp": datetime.now(),
        "path": Path("/home/user"),
        "decimal": Decimal("123.456"),
        "raw_bytes": b"hello bytes",
        "unique": {1, 2, 3}
    }

    serialized = engine.serialize(complex_data)
    restored = engine.deserialize(serialized)

    print(f"   datetime: {type(restored['timestamp']).__name__}")
    print(f"   path: {restored['path']}")
    print(f"   decimal: {restored['decimal']}")
    print(f"   bytes: {restored['raw_bytes']}")
    print(f"   set: {restored['unique']}")
    print()

    # 7. Checksum Verification
    print("7. CHECKSUM VERIFICATION:")
    print("-" * 40)

    serialized = engine.serialize(data)
    print(f"   Checksum: {serialized.checksum}")
    print(f"   Verify: {engine.verify(serialized)}")

    serialized.data = b"corrupted"
    print(f"   Verify corrupted: {engine.verify(serialized)}")
    print()

    # 8. Custom Type Registration
    print("8. CUSTOM TYPE REGISTRATION:")
    print("-" * 40)

    class Point:
        def __init__(self, x: int, y: int):
            self.x = x
            self.y = y

        def __repr__(self):
            return f"Point({self.x}, {self.y})"

    engine.register_type(
        Point,
        lambda p: {"x": p.x, "y": p.y},
        lambda d: Point(d["x"], d["y"])
    )

    point_data = {"point": Point(10, 20)}
    serialized = engine.serialize(point_data)
    restored = engine.deserialize(serialized)

    print(f"   Original: {point_data}")
    print(f"   Restored: {restored}")
    print()

    # 9. Schema Creation
    print("9. SCHEMA CREATION:")
    print("-" * 40)

    engine.create_schema(
        "user",
        fields={"name": str, "age": int, "email": str},
        required={"name", "email"}
    )

    print("   Created schema: user")
    print("   Fields: name (str), age (int), email (str)")
    print("   Required: name, email")
    print()

    # 10. Schema Validation
    print("10. SCHEMA VALIDATION:")
    print("-" * 40)

    valid_data = {"name": "Bob", "age": 25, "email": "bob@test.com"}
    is_valid, errors = engine.validate_schema(valid_data, "user")
    print(f"   Valid data: {is_valid}")

    invalid_data = {"name": "Carol"}
    is_valid, errors = engine.validate_schema(invalid_data, "user")
    print(f"   Invalid data: {is_valid}")
    for error in errors:
        print(f"   - {error}")
    print()

    # 11. Pickle Format
    print("11. PICKLE FORMAT:")
    print("-" * 40)

    class CustomObject:
        def __init__(self):
            self.data = [1, 2, 3]

    obj = CustomObject()

    result = engine.serialize(obj, SerialFormat.PICKLE)
    print(f"   Pickle size: {len(result.data)} bytes")

    restored = engine.deserialize(result)
    print(f"   Restored data: {restored.data}")
    print()

    # 12. Different Formats Comparison
    print("12. FORMAT COMPARISON:")
    print("-" * 40)

    test_data = {"numbers": list(range(100)), "text": "Hello " * 50}

    for fmt in [SerialFormat.JSON, SerialFormat.BINARY, SerialFormat.PICKLE]:
        result = engine.serialize(test_data, fmt)
        print(f"   {fmt.value}: {len(result.data)} bytes")
    print()

    # 13. Nested Data
    print("13. NESTED DATA:")
    print("-" * 40)

    nested = {
        "level1": {
            "level2": {
                "level3": {
                    "value": "deep nested"
                }
            }
        }
    }

    serialized = engine.serialize(nested)
    restored = engine.deserialize(serialized)

    print(f"   Deep value: {restored['level1']['level2']['level3']['value']}")
    print()

    # 14. Large Data
    print("14. LARGE DATA:")
    print("-" * 40)

    large = {"data": "x" * 100000}

    result = engine.serialize(large, compression=Compression.GZIP)
    print(f"   Original: {result.original_size:,} bytes")
    print(f"   Compressed: {result.compressed_size:,} bytes")
    print(f"   Ratio: {result.original_size / result.compressed_size:.1f}x")
    print()

    # 15. Summary
    print("15. ENGINE SUMMARY:")
    print("-" * 40)

    summary = engine.summary()

    for key, value in summary.items():
        print(f"   {key}: {value}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Serialization Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())

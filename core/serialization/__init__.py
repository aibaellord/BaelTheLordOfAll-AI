"""
BAEL Serialization Engine Implementation
=========================================

Multi-format serialization utilities.

"Ba'el transforms data across dimensions." — Ba'el
"""

import io
import json
import logging
import pickle
import struct
from typing import Any, Callable, Dict, List, Optional, Type, Union
from dataclasses import dataclass, field, asdict, is_dataclass
from datetime import datetime, date
from enum import Enum
import base64

logger = logging.getLogger("BAEL.Serialization")


# ============================================================================
# ENUMS
# ============================================================================

class SerializationFormat(Enum):
    """Serialization formats."""
    JSON = "json"
    PICKLE = "pickle"
    MSGPACK = "msgpack"
    CBOR = "cbor"
    YAML = "yaml"
    TOML = "toml"
    BINARY = "binary"


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class SerializationResult:
    """Result of serialization."""
    data: bytes
    format: SerializationFormat
    size: int

    def as_string(self) -> str:
        """Get as string (for text formats)."""
        return self.data.decode('utf-8')

    def as_base64(self) -> str:
        """Get as base64 string."""
        return base64.b64encode(self.data).decode('ascii')


@dataclass
class SerializerConfig:
    """Serializer configuration."""
    default_format: SerializationFormat = SerializationFormat.JSON
    pretty_print: bool = False
    sort_keys: bool = False
    include_type_info: bool = False


# ============================================================================
# TYPE ENCODERS
# ============================================================================

class ExtendedEncoder(json.JSONEncoder):
    """JSON encoder with extended type support."""

    def default(self, obj: Any) -> Any:
        if isinstance(obj, datetime):
            return {'__type__': 'datetime', 'value': obj.isoformat()}
        elif isinstance(obj, date):
            return {'__type__': 'date', 'value': obj.isoformat()}
        elif isinstance(obj, bytes):
            return {'__type__': 'bytes', 'value': base64.b64encode(obj).decode()}
        elif isinstance(obj, set):
            return {'__type__': 'set', 'value': list(obj)}
        elif isinstance(obj, frozenset):
            return {'__type__': 'frozenset', 'value': list(obj)}
        elif isinstance(obj, Enum):
            return {'__type__': 'enum', 'class': obj.__class__.__name__,
                    'value': obj.value}
        elif is_dataclass(obj) and not isinstance(obj, type):
            return {'__type__': 'dataclass', 'class': obj.__class__.__name__,
                    'value': asdict(obj)}
        elif hasattr(obj, '__dict__'):
            return {'__type__': 'object', 'class': obj.__class__.__name__,
                    'value': obj.__dict__}
        return super().default(obj)


def extended_decoder(obj: dict) -> Any:
    """JSON decoder for extended types."""
    if '__type__' not in obj:
        return obj

    type_name = obj['__type__']
    value = obj['value']

    if type_name == 'datetime':
        return datetime.fromisoformat(value)
    elif type_name == 'date':
        return date.fromisoformat(value)
    elif type_name == 'bytes':
        return base64.b64decode(value)
    elif type_name == 'set':
        return set(value)
    elif type_name == 'frozenset':
        return frozenset(value)

    return obj


# ============================================================================
# SERIALIZATION ENGINE
# ============================================================================

class SerializationEngine:
    """
    Multi-format serialization engine.

    Features:
    - Multiple formats
    - Extended type support
    - Schema support
    - Custom serializers

    "Ba'el preserves state across transformations." — Ba'el
    """

    def __init__(self, config: Optional[SerializerConfig] = None):
        """Initialize serialization engine."""
        self.config = config or SerializerConfig()

        # Check optional dependencies
        self._msgpack_available = self._check_msgpack()
        self._cbor_available = self._check_cbor()
        self._yaml_available = self._check_yaml()
        self._toml_available = self._check_toml()

        # Custom serializers
        self._custom_serializers: Dict[type, Callable] = {}
        self._custom_deserializers: Dict[str, Callable] = {}

        # Stats
        self._stats = {
            'serializations': 0,
            'deserializations': 0,
            'bytes_out': 0,
            'bytes_in': 0
        }

        logger.info(
            f"Serialization engine initialized "
            f"(default={self.config.default_format.value})"
        )

    def _check_msgpack(self) -> bool:
        try:
            import msgpack
            return True
        except ImportError:
            return False

    def _check_cbor(self) -> bool:
        try:
            import cbor2
            return True
        except ImportError:
            return False

    def _check_yaml(self) -> bool:
        try:
            import yaml
            return True
        except ImportError:
            return False

    def _check_toml(self) -> bool:
        try:
            import tomli
            import tomli_w
            return True
        except ImportError:
            return False

    # ========================================================================
    # REGISTRATION
    # ========================================================================

    def register_serializer(
        self,
        type_class: type,
        serializer: Callable[[Any], dict],
        deserializer: Optional[Callable[[dict], Any]] = None,
        type_name: Optional[str] = None
    ) -> None:
        """
        Register custom serializer.

        Args:
            type_class: Type to serialize
            serializer: Function to convert to dict
            deserializer: Function to convert from dict
            type_name: Type name for deserialization
        """
        self._custom_serializers[type_class] = serializer

        if deserializer:
            name = type_name or type_class.__name__
            self._custom_deserializers[name] = deserializer

    # ========================================================================
    # SERIALIZATION
    # ========================================================================

    def serialize(
        self,
        obj: Any,
        format: Optional[SerializationFormat] = None
    ) -> SerializationResult:
        """
        Serialize object.

        Args:
            obj: Object to serialize
            format: Output format

        Returns:
            SerializationResult
        """
        format = format or self.config.default_format

        # Apply custom serializers
        obj = self._apply_custom_serializers(obj)

        if format == SerializationFormat.JSON:
            data = self._serialize_json(obj)

        elif format == SerializationFormat.PICKLE:
            data = pickle.dumps(obj)

        elif format == SerializationFormat.MSGPACK:
            if not self._msgpack_available:
                raise ValueError("msgpack not available")
            import msgpack
            data = msgpack.packb(obj, default=self._msgpack_default)

        elif format == SerializationFormat.CBOR:
            if not self._cbor_available:
                raise ValueError("cbor2 not available")
            import cbor2
            data = cbor2.dumps(obj)

        elif format == SerializationFormat.YAML:
            if not self._yaml_available:
                raise ValueError("PyYAML not available")
            import yaml
            data = yaml.dump(obj, default_flow_style=not self.config.pretty_print)
            data = data.encode('utf-8')

        elif format == SerializationFormat.TOML:
            if not self._toml_available:
                raise ValueError("tomli/tomli_w not available")
            import tomli_w
            data = tomli_w.dumps(obj).encode('utf-8')

        elif format == SerializationFormat.BINARY:
            data = self._serialize_binary(obj)

        else:
            raise ValueError(f"Unknown format: {format}")

        self._stats['serializations'] += 1
        self._stats['bytes_out'] += len(data)

        return SerializationResult(
            data=data,
            format=format,
            size=len(data)
        )

    def _serialize_json(self, obj: Any) -> bytes:
        """Serialize to JSON."""
        return json.dumps(
            obj,
            cls=ExtendedEncoder,
            indent=2 if self.config.pretty_print else None,
            sort_keys=self.config.sort_keys
        ).encode('utf-8')

    def _serialize_binary(self, obj: Any) -> bytes:
        """Serialize to custom binary format."""
        buffer = io.BytesIO()
        self._write_value(buffer, obj)
        return buffer.getvalue()

    def _write_value(self, buffer: io.BytesIO, value: Any) -> None:
        """Write value to binary buffer."""
        if value is None:
            buffer.write(b'\x00')
        elif isinstance(value, bool):
            buffer.write(b'\x01' if value else b'\x02')
        elif isinstance(value, int):
            buffer.write(b'\x03')
            buffer.write(struct.pack('>q', value))
        elif isinstance(value, float):
            buffer.write(b'\x04')
            buffer.write(struct.pack('>d', value))
        elif isinstance(value, str):
            buffer.write(b'\x05')
            encoded = value.encode('utf-8')
            buffer.write(struct.pack('>I', len(encoded)))
            buffer.write(encoded)
        elif isinstance(value, bytes):
            buffer.write(b'\x06')
            buffer.write(struct.pack('>I', len(value)))
            buffer.write(value)
        elif isinstance(value, list):
            buffer.write(b'\x07')
            buffer.write(struct.pack('>I', len(value)))
            for item in value:
                self._write_value(buffer, item)
        elif isinstance(value, dict):
            buffer.write(b'\x08')
            buffer.write(struct.pack('>I', len(value)))
            for k, v in value.items():
                self._write_value(buffer, k)
                self._write_value(buffer, v)
        else:
            # Fallback to pickle
            buffer.write(b'\xFF')
            pickled = pickle.dumps(value)
            buffer.write(struct.pack('>I', len(pickled)))
            buffer.write(pickled)

    def _apply_custom_serializers(self, obj: Any) -> Any:
        """Apply custom serializers recursively."""
        obj_type = type(obj)

        if obj_type in self._custom_serializers:
            serializer = self._custom_serializers[obj_type]
            result = serializer(obj)
            result['__custom_type__'] = obj_type.__name__
            return result

        if isinstance(obj, dict):
            return {k: self._apply_custom_serializers(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._apply_custom_serializers(item) for item in obj]

        return obj

    def _msgpack_default(self, obj: Any) -> Any:
        """Default handler for msgpack."""
        if isinstance(obj, datetime):
            return {'__type__': 'datetime', 'value': obj.isoformat()}
        elif isinstance(obj, date):
            return {'__type__': 'date', 'value': obj.isoformat()}
        elif isinstance(obj, bytes):
            return {'__type__': 'bytes', 'value': base64.b64encode(obj).decode()}
        raise TypeError(f"Unknown type: {type(obj)}")

    # ========================================================================
    # DESERIALIZATION
    # ========================================================================

    def deserialize(
        self,
        data: Union[bytes, str],
        format: Optional[SerializationFormat] = None
    ) -> Any:
        """
        Deserialize data.

        Args:
            data: Data to deserialize
            format: Input format (auto-detect if None)

        Returns:
            Deserialized object
        """
        if isinstance(data, str):
            data = data.encode('utf-8')

        format = format or self._detect_format(data)

        if format == SerializationFormat.JSON:
            obj = json.loads(data.decode('utf-8'), object_hook=extended_decoder)

        elif format == SerializationFormat.PICKLE:
            obj = pickle.loads(data)

        elif format == SerializationFormat.MSGPACK:
            if not self._msgpack_available:
                raise ValueError("msgpack not available")
            import msgpack
            obj = msgpack.unpackb(data, raw=False)

        elif format == SerializationFormat.CBOR:
            if not self._cbor_available:
                raise ValueError("cbor2 not available")
            import cbor2
            obj = cbor2.loads(data)

        elif format == SerializationFormat.YAML:
            if not self._yaml_available:
                raise ValueError("PyYAML not available")
            import yaml
            obj = yaml.safe_load(data.decode('utf-8'))

        elif format == SerializationFormat.TOML:
            if not self._toml_available:
                raise ValueError("tomli not available")
            import tomli
            obj = tomli.loads(data.decode('utf-8'))

        elif format == SerializationFormat.BINARY:
            obj = self._deserialize_binary(data)

        else:
            raise ValueError(f"Unknown format: {format}")

        # Apply custom deserializers
        obj = self._apply_custom_deserializers(obj)

        self._stats['deserializations'] += 1
        self._stats['bytes_in'] += len(data)

        return obj

    def _deserialize_binary(self, data: bytes) -> Any:
        """Deserialize from binary format."""
        buffer = io.BytesIO(data)
        return self._read_value(buffer)

    def _read_value(self, buffer: io.BytesIO) -> Any:
        """Read value from binary buffer."""
        type_byte = buffer.read(1)

        if type_byte == b'\x00':
            return None
        elif type_byte == b'\x01':
            return True
        elif type_byte == b'\x02':
            return False
        elif type_byte == b'\x03':
            return struct.unpack('>q', buffer.read(8))[0]
        elif type_byte == b'\x04':
            return struct.unpack('>d', buffer.read(8))[0]
        elif type_byte == b'\x05':
            length = struct.unpack('>I', buffer.read(4))[0]
            return buffer.read(length).decode('utf-8')
        elif type_byte == b'\x06':
            length = struct.unpack('>I', buffer.read(4))[0]
            return buffer.read(length)
        elif type_byte == b'\x07':
            length = struct.unpack('>I', buffer.read(4))[0]
            return [self._read_value(buffer) for _ in range(length)]
        elif type_byte == b'\x08':
            length = struct.unpack('>I', buffer.read(4))[0]
            return {
                self._read_value(buffer): self._read_value(buffer)
                for _ in range(length)
            }
        elif type_byte == b'\xFF':
            length = struct.unpack('>I', buffer.read(4))[0]
            return pickle.loads(buffer.read(length))
        else:
            raise ValueError(f"Unknown type byte: {type_byte}")

    def _apply_custom_deserializers(self, obj: Any) -> Any:
        """Apply custom deserializers."""
        if isinstance(obj, dict):
            if '__custom_type__' in obj:
                type_name = obj.pop('__custom_type__')
                if type_name in self._custom_deserializers:
                    return self._custom_deserializers[type_name](obj)

            return {k: self._apply_custom_deserializers(v)
                    for k, v in obj.items()}

        elif isinstance(obj, list):
            return [self._apply_custom_deserializers(item) for item in obj]

        return obj

    def _detect_format(self, data: bytes) -> SerializationFormat:
        """Detect serialization format."""
        if data.startswith(b'{') or data.startswith(b'['):
            return SerializationFormat.JSON
        elif data.startswith(b'\x80'):
            return SerializationFormat.PICKLE
        elif data.startswith(b'\x00') or data.startswith(b'\x01'):
            return SerializationFormat.BINARY
        return SerializationFormat.JSON

    # ========================================================================
    # UTILITIES
    # ========================================================================

    def get_available_formats(self) -> List[SerializationFormat]:
        """Get available formats."""
        formats = [
            SerializationFormat.JSON,
            SerializationFormat.PICKLE,
            SerializationFormat.BINARY
        ]

        if self._msgpack_available:
            formats.append(SerializationFormat.MSGPACK)
        if self._cbor_available:
            formats.append(SerializationFormat.CBOR)
        if self._yaml_available:
            formats.append(SerializationFormat.YAML)
        if self._toml_available:
            formats.append(SerializationFormat.TOML)

        return formats

    def get_stats(self) -> Dict[str, Any]:
        """Get serialization statistics."""
        return {
            **self._stats,
            'available_formats': [f.value for f in self.get_available_formats()]
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

_engine: Optional[SerializationEngine] = None


def get_serialization_engine(
    config: Optional[SerializerConfig] = None
) -> SerializationEngine:
    """Get or create serialization engine."""
    global _engine
    if _engine is None:
        _engine = SerializationEngine(config)
    return _engine


def to_json(obj: Any, pretty: bool = False) -> str:
    """Serialize to JSON string."""
    engine = get_serialization_engine()
    engine.config.pretty_print = pretty
    result = engine.serialize(obj, SerializationFormat.JSON)
    return result.as_string()


def from_json(data: Union[bytes, str]) -> Any:
    """Deserialize from JSON."""
    return get_serialization_engine().deserialize(data, SerializationFormat.JSON)


def to_pickle(obj: Any) -> bytes:
    """Serialize to pickle."""
    return get_serialization_engine().serialize(
        obj, SerializationFormat.PICKLE
    ).data


def from_pickle(data: bytes) -> Any:
    """Deserialize from pickle."""
    return get_serialization_engine().deserialize(
        data, SerializationFormat.PICKLE
    )

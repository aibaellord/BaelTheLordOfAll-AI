"""
BAEL Protocol Buffer Engine Implementation
==========================================

Binary serialization and protocol buffer support.

"Ba'el encodes reality into its purest binary form." — Ba'el
"""

import asyncio
import logging
import struct
import threading
from io import BytesIO
from typing import Any, Dict, List, Optional, Type, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

logger = logging.getLogger("BAEL.Protocol")


# ============================================================================
# ENUMS
# ============================================================================

class FieldType(Enum):
    """Protocol buffer field types."""
    INT32 = "int32"
    INT64 = "int64"
    UINT32 = "uint32"
    UINT64 = "uint64"
    SINT32 = "sint32"
    SINT64 = "sint64"
    FLOAT = "float"
    DOUBLE = "double"
    BOOL = "bool"
    STRING = "string"
    BYTES = "bytes"
    MESSAGE = "message"
    ENUM = "enum"
    FIXED32 = "fixed32"
    FIXED64 = "fixed64"


class WireType(Enum):
    """Wire types for encoding."""
    VARINT = 0
    FIXED64 = 1
    LENGTH_DELIMITED = 2
    START_GROUP = 3  # Deprecated
    END_GROUP = 4    # Deprecated
    FIXED32 = 5


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class Field:
    """A message field definition."""
    name: str
    field_type: FieldType
    number: int

    # Modifiers
    repeated: bool = False
    optional: bool = True
    packed: bool = False

    # Default value
    default: Any = None

    # For nested messages
    message_type: Optional[str] = None

    # For enums
    enum_type: Optional[str] = None


@dataclass
class Message:
    """A protocol buffer message."""
    name: str
    fields: List[Field] = field(default_factory=list)

    # Nested types
    nested_messages: List['Message'] = field(default_factory=list)
    nested_enums: Dict[str, List[str]] = field(default_factory=dict)

    def add_field(self, name: str, field_type: FieldType, number: int, **kwargs) -> 'Message':
        """Add field to message."""
        self.fields.append(Field(name=name, field_type=field_type, number=number, **kwargs))
        return self

    def get_field(self, name: str) -> Optional[Field]:
        """Get field by name."""
        for f in self.fields:
            if f.name == name:
                return f
        return None

    def get_field_by_number(self, number: int) -> Optional[Field]:
        """Get field by number."""
        for f in self.fields:
            if f.number == number:
                return f
        return None


@dataclass
class Schema:
    """A protocol buffer schema."""
    name: str
    package: str = ""
    messages: List[Message] = field(default_factory=list)
    enums: Dict[str, List[str]] = field(default_factory=dict)

    # Imports
    imports: List[str] = field(default_factory=list)

    def add_message(self, message: Message) -> 'Schema':
        """Add message to schema."""
        self.messages.append(message)
        return self

    def get_message(self, name: str) -> Optional[Message]:
        """Get message by name."""
        for m in self.messages:
            if m.name == name:
                return m
        return None


@dataclass
class EncodedMessage:
    """An encoded message."""
    data: bytes
    message_type: str
    size: int

    def to_hex(self) -> str:
        """Convert to hex string."""
        return self.data.hex()

    @classmethod
    def from_hex(cls, hex_str: str, message_type: str) -> 'EncodedMessage':
        """Create from hex string."""
        data = bytes.fromhex(hex_str)
        return cls(data=data, message_type=message_type, size=len(data))


# ============================================================================
# VARINT ENCODING
# ============================================================================

def encode_varint(value: int) -> bytes:
    """Encode integer as varint."""
    if value < 0:
        # Handle negative numbers (two's complement)
        value = value & 0xFFFFFFFFFFFFFFFF

    result = []
    while value > 127:
        result.append((value & 0x7F) | 0x80)
        value >>= 7
    result.append(value & 0x7F)

    return bytes(result)


def decode_varint(data: bytes, offset: int = 0) -> tuple:
    """Decode varint from bytes. Returns (value, bytes_consumed)."""
    result = 0
    shift = 0

    while True:
        byte = data[offset]
        result |= (byte & 0x7F) << shift
        offset += 1

        if not (byte & 0x80):
            break
        shift += 7

    return result, offset


def encode_zigzag(value: int) -> int:
    """ZigZag encode for signed integers."""
    return (value << 1) ^ (value >> 63)


def decode_zigzag(value: int) -> int:
    """ZigZag decode for signed integers."""
    return (value >> 1) ^ -(value & 1)


# ============================================================================
# WIRE FORMAT
# ============================================================================

def encode_tag(field_number: int, wire_type: WireType) -> bytes:
    """Encode field tag."""
    tag = (field_number << 3) | wire_type.value
    return encode_varint(tag)


def decode_tag(data: bytes, offset: int = 0) -> tuple:
    """Decode field tag. Returns (field_number, wire_type, bytes_consumed)."""
    tag, new_offset = decode_varint(data, offset)
    field_number = tag >> 3
    wire_type = WireType(tag & 0x07)
    return field_number, wire_type, new_offset


# ============================================================================
# FIELD ENCODING
# ============================================================================

def get_wire_type(field_type: FieldType) -> WireType:
    """Get wire type for field type."""
    if field_type in [FieldType.INT32, FieldType.INT64, FieldType.UINT32,
                      FieldType.UINT64, FieldType.SINT32, FieldType.SINT64,
                      FieldType.BOOL, FieldType.ENUM]:
        return WireType.VARINT
    elif field_type in [FieldType.FIXED64, FieldType.DOUBLE]:
        return WireType.FIXED64
    elif field_type in [FieldType.FIXED32, FieldType.FLOAT]:
        return WireType.FIXED32
    else:
        return WireType.LENGTH_DELIMITED


def encode_field(field_def: Field, value: Any) -> bytes:
    """Encode a single field."""
    wire_type = get_wire_type(field_def.field_type)
    result = BytesIO()

    # Write tag
    result.write(encode_tag(field_def.number, wire_type))

    # Write value
    if field_def.field_type == FieldType.BOOL:
        result.write(encode_varint(1 if value else 0))
    elif field_def.field_type in [FieldType.INT32, FieldType.INT64]:
        result.write(encode_varint(value))
    elif field_def.field_type in [FieldType.UINT32, FieldType.UINT64]:
        result.write(encode_varint(value))
    elif field_def.field_type in [FieldType.SINT32, FieldType.SINT64]:
        result.write(encode_varint(encode_zigzag(value)))
    elif field_def.field_type == FieldType.FLOAT:
        result.write(struct.pack('<f', value))
    elif field_def.field_type == FieldType.DOUBLE:
        result.write(struct.pack('<d', value))
    elif field_def.field_type == FieldType.FIXED32:
        result.write(struct.pack('<I', value))
    elif field_def.field_type == FieldType.FIXED64:
        result.write(struct.pack('<Q', value))
    elif field_def.field_type == FieldType.STRING:
        encoded = value.encode('utf-8')
        result.write(encode_varint(len(encoded)))
        result.write(encoded)
    elif field_def.field_type == FieldType.BYTES:
        result.write(encode_varint(len(value)))
        result.write(value)
    elif field_def.field_type == FieldType.ENUM:
        result.write(encode_varint(value))
    elif field_def.field_type == FieldType.MESSAGE:
        # Nested message - value should already be encoded
        if isinstance(value, bytes):
            result.write(encode_varint(len(value)))
            result.write(value)
        else:
            raise ValueError("MESSAGE field requires encoded bytes")

    return result.getvalue()


def decode_field(
    wire_type: WireType,
    field_type: FieldType,
    data: bytes,
    offset: int
) -> tuple:
    """Decode a single field. Returns (value, bytes_consumed)."""
    if wire_type == WireType.VARINT:
        value, new_offset = decode_varint(data, offset)

        if field_type == FieldType.BOOL:
            return bool(value), new_offset - offset
        elif field_type in [FieldType.SINT32, FieldType.SINT64]:
            return decode_zigzag(value), new_offset - offset
        else:
            return value, new_offset - offset

    elif wire_type == WireType.FIXED64:
        if field_type == FieldType.DOUBLE:
            value = struct.unpack('<d', data[offset:offset + 8])[0]
        else:
            value = struct.unpack('<Q', data[offset:offset + 8])[0]
        return value, 8

    elif wire_type == WireType.FIXED32:
        if field_type == FieldType.FLOAT:
            value = struct.unpack('<f', data[offset:offset + 4])[0]
        else:
            value = struct.unpack('<I', data[offset:offset + 4])[0]
        return value, 4

    elif wire_type == WireType.LENGTH_DELIMITED:
        length, len_bytes = decode_varint(data, offset)
        start = offset + len_bytes - offset

        if field_type == FieldType.STRING:
            value = data[offset + (len_bytes - offset):offset + (len_bytes - offset) + length].decode('utf-8')
        elif field_type == FieldType.BYTES or field_type == FieldType.MESSAGE:
            value = data[offset + (len_bytes - offset):offset + (len_bytes - offset) + length]
        else:
            value = data[offset + (len_bytes - offset):offset + (len_bytes - offset) + length]

        return value, (len_bytes - offset) + length

    raise ValueError(f"Unknown wire type: {wire_type}")


# ============================================================================
# MAIN ENGINE
# ============================================================================

class ProtocolEngine:
    """
    Main protocol buffer engine.

    Features:
    - Message definition
    - Binary serialization
    - Deserialization
    - Schema management

    "Ba'el speaks in the language of pure binary truth." — Ba'el
    """

    def __init__(self):
        """Initialize protocol engine."""
        # Registered schemas
        self._schemas: Dict[str, Schema] = {}

        # Registered messages
        self._messages: Dict[str, Message] = {}

        self._lock = threading.RLock()

        logger.info("ProtocolEngine initialized")

    # ========================================================================
    # SCHEMA MANAGEMENT
    # ========================================================================

    def register_schema(self, schema: Schema) -> None:
        """Register a schema."""
        with self._lock:
            self._schemas[schema.name] = schema

            # Register all messages
            for message in schema.messages:
                full_name = f"{schema.package}.{message.name}" if schema.package else message.name
                self._messages[full_name] = message

    def get_schema(self, name: str) -> Optional[Schema]:
        """Get schema by name."""
        return self._schemas.get(name)

    def get_message(self, name: str) -> Optional[Message]:
        """Get message by name."""
        return self._messages.get(name)

    def define_message(
        self,
        name: str,
        fields: List[tuple]
    ) -> Message:
        """
        Define a message.

        Args:
            name: Message name
            fields: List of (name, type, number) tuples

        Returns:
            Message definition
        """
        message = Message(name=name)

        for field_def in fields:
            if len(field_def) == 3:
                name, ftype, number = field_def
                message.add_field(name, ftype, number)
            elif len(field_def) >= 4:
                name, ftype, number = field_def[:3]
                kwargs = field_def[3] if len(field_def) > 3 else {}
                message.add_field(name, ftype, number, **kwargs)

        with self._lock:
            self._messages[name] = message

        return message

    # ========================================================================
    # SERIALIZATION
    # ========================================================================

    def serialize(
        self,
        message_name: str,
        data: Dict[str, Any]
    ) -> EncodedMessage:
        """
        Serialize data to protocol buffer format.

        Args:
            message_name: Message type name
            data: Dictionary of field values

        Returns:
            EncodedMessage
        """
        message = self.get_message(message_name)
        if not message:
            raise ValueError(f"Unknown message type: {message_name}")

        result = BytesIO()

        for field_def in message.fields:
            if field_def.name in data:
                value = data[field_def.name]

                if field_def.repeated and isinstance(value, list):
                    # Repeated field
                    for item in value:
                        result.write(encode_field(field_def, item))
                else:
                    result.write(encode_field(field_def, value))

        encoded = result.getvalue()

        return EncodedMessage(
            data=encoded,
            message_type=message_name,
            size=len(encoded)
        )

    def deserialize(
        self,
        message_name: str,
        data: bytes
    ) -> Dict[str, Any]:
        """
        Deserialize protocol buffer data.

        Args:
            message_name: Message type name
            data: Encoded bytes

        Returns:
            Dictionary of field values
        """
        message = self.get_message(message_name)
        if not message:
            raise ValueError(f"Unknown message type: {message_name}")

        result = {}
        offset = 0

        while offset < len(data):
            # Read tag
            field_number, wire_type, new_offset = decode_tag(data, offset)
            offset = new_offset

            # Find field definition
            field_def = message.get_field_by_number(field_number)

            if field_def:
                # Decode value
                value, consumed = decode_field(
                    wire_type,
                    field_def.field_type,
                    data,
                    offset
                )
                offset += consumed

                # Handle repeated fields
                if field_def.repeated:
                    if field_def.name not in result:
                        result[field_def.name] = []
                    result[field_def.name].append(value)
                else:
                    result[field_def.name] = value
            else:
                # Skip unknown field
                if wire_type == WireType.VARINT:
                    _, new_offset = decode_varint(data, offset)
                    offset = new_offset
                elif wire_type == WireType.FIXED64:
                    offset += 8
                elif wire_type == WireType.FIXED32:
                    offset += 4
                elif wire_type == WireType.LENGTH_DELIMITED:
                    length, len_bytes = decode_varint(data, offset)
                    offset = len_bytes + length

        return result

    # ========================================================================
    # CONVENIENCE
    # ========================================================================

    def to_dict(self, encoded: EncodedMessage) -> Dict[str, Any]:
        """Convert encoded message to dictionary."""
        return self.deserialize(encoded.message_type, encoded.data)

    def from_dict(self, message_name: str, data: Dict[str, Any]) -> EncodedMessage:
        """Create encoded message from dictionary."""
        return self.serialize(message_name, data)

    # ========================================================================
    # ASYNC
    # ========================================================================

    async def serialize_async(
        self,
        message_name: str,
        data: Dict[str, Any]
    ) -> EncodedMessage:
        """Serialize asynchronously."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.serialize(message_name, data)
        )

    async def deserialize_async(
        self,
        message_name: str,
        data: bytes
    ) -> Dict[str, Any]:
        """Deserialize asynchronously."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.deserialize(message_name, data)
        )

    # ========================================================================
    # STATUS
    # ========================================================================

    def get_status(self) -> Dict[str, Any]:
        """Get engine status."""
        with self._lock:
            return {
                'schemas': len(self._schemas),
                'messages': len(self._messages),
                'message_types': list(self._messages.keys())
            }


# ============================================================================
# CONVENIENCE
# ============================================================================

proto_engine = ProtocolEngine()


def serialize(message_name: str, data: Dict[str, Any]) -> EncodedMessage:
    """Serialize data."""
    return proto_engine.serialize(message_name, data)


def deserialize(message_name: str, data: bytes) -> Dict[str, Any]:
    """Deserialize data."""
    return proto_engine.deserialize(message_name, data)

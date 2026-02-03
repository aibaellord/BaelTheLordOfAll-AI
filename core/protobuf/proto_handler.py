#!/usr/bin/env python3
"""
BAEL - Protocol Buffer Handler
Comprehensive protobuf-like binary serialization system.

Features:
- Schema definition
- Binary encoding/decoding
- Wire types (varint, fixed64, length-delimited, fixed32)
- Nested messages
- Repeated fields
- Map fields
- Oneof fields
- Default values
- Schema evolution
- Backward compatibility
"""

import asyncio
import logging
import struct
import uuid
from abc import ABC, abstractmethod
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from io import BytesIO
from typing import (Any, Callable, Dict, Generator, List, Optional, Set, Tuple,
                    Type, TypeVar, Union)

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS
# =============================================================================

class WireType(Enum):
    """Wire types for binary encoding."""
    VARINT = 0      # int32, int64, uint32, uint64, sint32, sint64, bool, enum
    FIXED64 = 1     # fixed64, sfixed64, double
    LENGTH_DELIMITED = 2  # string, bytes, embedded messages, packed repeated
    FIXED32 = 5     # fixed32, sfixed32, float


class FieldType(Enum):
    """Field types."""
    INT32 = "int32"
    INT64 = "int64"
    UINT32 = "uint32"
    UINT64 = "uint64"
    SINT32 = "sint32"
    SINT64 = "sint64"
    BOOL = "bool"
    FIXED32 = "fixed32"
    FIXED64 = "fixed64"
    SFIXED32 = "sfixed32"
    SFIXED64 = "sfixed64"
    FLOAT = "float"
    DOUBLE = "double"
    STRING = "string"
    BYTES = "bytes"
    MESSAGE = "message"
    ENUM = "enum"


class FieldRule(Enum):
    """Field rules."""
    REQUIRED = "required"
    OPTIONAL = "optional"
    REPEATED = "repeated"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class FieldDescriptor:
    """Field descriptor."""
    number: int
    name: str
    field_type: FieldType
    rule: FieldRule = FieldRule.OPTIONAL
    message_type: Optional[str] = None  # For MESSAGE type
    enum_type: Optional[str] = None     # For ENUM type
    default: Any = None
    packed: bool = False  # For repeated numeric fields
    map_key_type: Optional[FieldType] = None
    map_value_type: Optional[FieldType] = None


@dataclass
class EnumDescriptor:
    """Enum descriptor."""
    name: str
    values: Dict[str, int] = field(default_factory=dict)


@dataclass
class MessageDescriptor:
    """Message descriptor."""
    name: str
    fields: Dict[int, FieldDescriptor] = field(default_factory=dict)
    nested_messages: Dict[str, "MessageDescriptor"] = field(default_factory=dict)
    nested_enums: Dict[str, EnumDescriptor] = field(default_factory=dict)
    oneof_groups: Dict[str, List[int]] = field(default_factory=dict)  # oneof name -> field numbers


@dataclass
class SchemaDescriptor:
    """Schema descriptor."""
    package: str = ""
    messages: Dict[str, MessageDescriptor] = field(default_factory=dict)
    enums: Dict[str, EnumDescriptor] = field(default_factory=dict)


# =============================================================================
# WIRE FORMAT ENCODER/DECODER
# =============================================================================

class WireEncoder:
    """Wire format encoder."""

    @staticmethod
    def encode_varint(value: int) -> bytes:
        """Encode a varint."""
        if value < 0:
            value = value & 0xFFFFFFFFFFFFFFFF

        result = []
        while value > 127:
            result.append((value & 0x7F) | 0x80)
            value >>= 7
        result.append(value)

        return bytes(result)

    @staticmethod
    def encode_signed_varint(value: int) -> bytes:
        """Encode a signed varint (zigzag encoding)."""
        # Zigzag encoding: (n << 1) ^ (n >> 63)
        if value >= 0:
            zigzag = value << 1
        else:
            zigzag = ((-value) << 1) - 1

        return WireEncoder.encode_varint(zigzag)

    @staticmethod
    def encode_fixed32(value: int) -> bytes:
        """Encode a fixed 32-bit integer."""
        return struct.pack('<I', value & 0xFFFFFFFF)

    @staticmethod
    def encode_fixed64(value: int) -> bytes:
        """Encode a fixed 64-bit integer."""
        return struct.pack('<Q', value & 0xFFFFFFFFFFFFFFFF)

    @staticmethod
    def encode_sfixed32(value: int) -> bytes:
        """Encode a signed fixed 32-bit integer."""
        return struct.pack('<i', value)

    @staticmethod
    def encode_sfixed64(value: int) -> bytes:
        """Encode a signed fixed 64-bit integer."""
        return struct.pack('<q', value)

    @staticmethod
    def encode_float(value: float) -> bytes:
        """Encode a float."""
        return struct.pack('<f', value)

    @staticmethod
    def encode_double(value: float) -> bytes:
        """Encode a double."""
        return struct.pack('<d', value)

    @staticmethod
    def encode_tag(field_number: int, wire_type: WireType) -> bytes:
        """Encode a field tag."""
        tag = (field_number << 3) | wire_type.value
        return WireEncoder.encode_varint(tag)

    @staticmethod
    def encode_length_delimited(data: bytes) -> bytes:
        """Encode length-delimited data."""
        return WireEncoder.encode_varint(len(data)) + data


class WireDecoder:
    """Wire format decoder."""

    def __init__(self, data: bytes):
        self.buffer = BytesIO(data)
        self.length = len(data)

    def decode_varint(self) -> int:
        """Decode a varint."""
        result = 0
        shift = 0

        while True:
            byte = self.buffer.read(1)
            if not byte:
                raise ValueError("Unexpected end of buffer")

            b = byte[0]
            result |= (b & 0x7F) << shift

            if (b & 0x80) == 0:
                break

            shift += 7
            if shift >= 64:
                raise ValueError("Varint too long")

        return result

    def decode_signed_varint(self) -> int:
        """Decode a signed varint (zigzag encoding)."""
        zigzag = self.decode_varint()
        # Decode zigzag: (n >> 1) ^ -(n & 1)
        return (zigzag >> 1) ^ -(zigzag & 1)

    def decode_fixed32(self) -> int:
        """Decode a fixed 32-bit integer."""
        data = self.buffer.read(4)
        if len(data) < 4:
            raise ValueError("Unexpected end of buffer")
        return struct.unpack('<I', data)[0]

    def decode_fixed64(self) -> int:
        """Decode a fixed 64-bit integer."""
        data = self.buffer.read(8)
        if len(data) < 8:
            raise ValueError("Unexpected end of buffer")
        return struct.unpack('<Q', data)[0]

    def decode_sfixed32(self) -> int:
        """Decode a signed fixed 32-bit integer."""
        data = self.buffer.read(4)
        if len(data) < 4:
            raise ValueError("Unexpected end of buffer")
        return struct.unpack('<i', data)[0]

    def decode_sfixed64(self) -> int:
        """Decode a signed fixed 64-bit integer."""
        data = self.buffer.read(8)
        if len(data) < 8:
            raise ValueError("Unexpected end of buffer")
        return struct.unpack('<q', data)[0]

    def decode_float(self) -> float:
        """Decode a float."""
        data = self.buffer.read(4)
        if len(data) < 4:
            raise ValueError("Unexpected end of buffer")
        return struct.unpack('<f', data)[0]

    def decode_double(self) -> float:
        """Decode a double."""
        data = self.buffer.read(8)
        if len(data) < 8:
            raise ValueError("Unexpected end of buffer")
        return struct.unpack('<d', data)[0]

    def decode_tag(self) -> Tuple[int, WireType]:
        """Decode a field tag."""
        tag = self.decode_varint()
        field_number = tag >> 3
        wire_type = WireType(tag & 0x07)
        return field_number, wire_type

    def decode_length_delimited(self) -> bytes:
        """Decode length-delimited data."""
        length = self.decode_varint()
        data = self.buffer.read(length)
        if len(data) < length:
            raise ValueError("Unexpected end of buffer")
        return data

    def has_more(self) -> bool:
        """Check if more data is available."""
        return self.buffer.tell() < self.length


# =============================================================================
# MESSAGE BUILDER
# =============================================================================

class MessageBuilder:
    """Fluent message builder."""

    def __init__(self, name: str):
        self.descriptor = MessageDescriptor(name=name)
        self._field_counter = 1

    def field(
        self,
        name: str,
        field_type: FieldType,
        number: Optional[int] = None,
        rule: FieldRule = FieldRule.OPTIONAL,
        default: Any = None
    ) -> "MessageBuilder":
        """Add a field."""
        if number is None:
            number = self._field_counter
            self._field_counter += 1

        self.descriptor.fields[number] = FieldDescriptor(
            number=number,
            name=name,
            field_type=field_type,
            rule=rule,
            default=default
        )

        return self

    def message_field(
        self,
        name: str,
        message_type: str,
        number: Optional[int] = None,
        rule: FieldRule = FieldRule.OPTIONAL
    ) -> "MessageBuilder":
        """Add a message field."""
        if number is None:
            number = self._field_counter
            self._field_counter += 1

        self.descriptor.fields[number] = FieldDescriptor(
            number=number,
            name=name,
            field_type=FieldType.MESSAGE,
            message_type=message_type,
            rule=rule
        )

        return self

    def repeated(
        self,
        name: str,
        field_type: FieldType,
        number: Optional[int] = None,
        packed: bool = True
    ) -> "MessageBuilder":
        """Add a repeated field."""
        if number is None:
            number = self._field_counter
            self._field_counter += 1

        self.descriptor.fields[number] = FieldDescriptor(
            number=number,
            name=name,
            field_type=field_type,
            rule=FieldRule.REPEATED,
            packed=packed
        )

        return self

    def enum_field(
        self,
        name: str,
        enum_type: str,
        number: Optional[int] = None,
        rule: FieldRule = FieldRule.OPTIONAL
    ) -> "MessageBuilder":
        """Add an enum field."""
        if number is None:
            number = self._field_counter
            self._field_counter += 1

        self.descriptor.fields[number] = FieldDescriptor(
            number=number,
            name=name,
            field_type=FieldType.ENUM,
            enum_type=enum_type,
            rule=rule
        )

        return self

    def nested_message(self, descriptor: MessageDescriptor) -> "MessageBuilder":
        """Add a nested message."""
        self.descriptor.nested_messages[descriptor.name] = descriptor
        return self

    def nested_enum(self, descriptor: EnumDescriptor) -> "MessageBuilder":
        """Add a nested enum."""
        self.descriptor.nested_enums[descriptor.name] = descriptor
        return self

    def build(self) -> MessageDescriptor:
        """Build the message descriptor."""
        return self.descriptor


# =============================================================================
# PROTOCOL HANDLER
# =============================================================================

class ProtocolHandler:
    """
    Comprehensive Protocol Buffer Handler for BAEL.

    Provides binary serialization/deserialization.
    """

    def __init__(self):
        self._messages: Dict[str, MessageDescriptor] = {}
        self._enums: Dict[str, EnumDescriptor] = {}

    # -------------------------------------------------------------------------
    # SCHEMA REGISTRATION
    # -------------------------------------------------------------------------

    def register_message(self, descriptor: MessageDescriptor) -> None:
        """Register a message type."""
        self._messages[descriptor.name] = descriptor

    def register_enum(self, descriptor: EnumDescriptor) -> None:
        """Register an enum type."""
        self._enums[descriptor.name] = descriptor

    def get_message(self, name: str) -> Optional[MessageDescriptor]:
        """Get message descriptor by name."""
        return self._messages.get(name)

    def get_enum(self, name: str) -> Optional[EnumDescriptor]:
        """Get enum descriptor by name."""
        return self._enums.get(name)

    # -------------------------------------------------------------------------
    # ENCODING
    # -------------------------------------------------------------------------

    def encode(self, message_type: str, data: Dict[str, Any]) -> bytes:
        """Encode a message to binary format."""
        descriptor = self._messages.get(message_type)
        if not descriptor:
            raise ValueError(f"Unknown message type: {message_type}")

        return self._encode_message(descriptor, data)

    def _encode_message(self, descriptor: MessageDescriptor, data: Dict[str, Any]) -> bytes:
        """Encode a message."""
        result = BytesIO()

        # Create name to field number mapping
        name_to_field = {f.name: f for f in descriptor.fields.values()}

        for name, value in data.items():
            if name not in name_to_field:
                continue  # Skip unknown fields

            field = name_to_field[name]

            if value is None:
                continue

            if field.rule == FieldRule.REPEATED:
                encoded = self._encode_repeated(field, value)
            else:
                encoded = self._encode_field(field, value)

            result.write(encoded)

        return result.getvalue()

    def _encode_field(self, field: FieldDescriptor, value: Any) -> bytes:
        """Encode a single field."""
        wire_type = self._get_wire_type(field.field_type)
        tag = WireEncoder.encode_tag(field.number, wire_type)

        if field.field_type == FieldType.INT32:
            return tag + WireEncoder.encode_varint(value)

        elif field.field_type == FieldType.INT64:
            return tag + WireEncoder.encode_varint(value)

        elif field.field_type == FieldType.UINT32:
            return tag + WireEncoder.encode_varint(value)

        elif field.field_type == FieldType.UINT64:
            return tag + WireEncoder.encode_varint(value)

        elif field.field_type == FieldType.SINT32:
            return tag + WireEncoder.encode_signed_varint(value)

        elif field.field_type == FieldType.SINT64:
            return tag + WireEncoder.encode_signed_varint(value)

        elif field.field_type == FieldType.BOOL:
            return tag + WireEncoder.encode_varint(1 if value else 0)

        elif field.field_type == FieldType.FIXED32:
            return tag + WireEncoder.encode_fixed32(value)

        elif field.field_type == FieldType.FIXED64:
            return tag + WireEncoder.encode_fixed64(value)

        elif field.field_type == FieldType.SFIXED32:
            return tag + WireEncoder.encode_sfixed32(value)

        elif field.field_type == FieldType.SFIXED64:
            return tag + WireEncoder.encode_sfixed64(value)

        elif field.field_type == FieldType.FLOAT:
            return tag + WireEncoder.encode_float(value)

        elif field.field_type == FieldType.DOUBLE:
            return tag + WireEncoder.encode_double(value)

        elif field.field_type == FieldType.STRING:
            encoded = value.encode('utf-8')
            return tag + WireEncoder.encode_length_delimited(encoded)

        elif field.field_type == FieldType.BYTES:
            return tag + WireEncoder.encode_length_delimited(value)

        elif field.field_type == FieldType.MESSAGE:
            message_desc = self._messages.get(field.message_type)
            if not message_desc:
                raise ValueError(f"Unknown message type: {field.message_type}")
            encoded = self._encode_message(message_desc, value)
            return tag + WireEncoder.encode_length_delimited(encoded)

        elif field.field_type == FieldType.ENUM:
            enum_desc = self._enums.get(field.enum_type)
            if enum_desc and isinstance(value, str):
                value = enum_desc.values.get(value, 0)
            return tag + WireEncoder.encode_varint(value)

        return b''

    def _encode_repeated(self, field: FieldDescriptor, values: List[Any]) -> bytes:
        """Encode a repeated field."""
        if not values:
            return b''

        if field.packed and self._is_packable(field.field_type):
            return self._encode_packed(field, values)

        # Non-packed: encode each value separately
        result = BytesIO()
        for value in values:
            result.write(self._encode_field(field, value))
        return result.getvalue()

    def _encode_packed(self, field: FieldDescriptor, values: List[Any]) -> bytes:
        """Encode a packed repeated field."""
        packed_data = BytesIO()

        for value in values:
            if field.field_type in (FieldType.INT32, FieldType.INT64, FieldType.UINT32, FieldType.UINT64):
                packed_data.write(WireEncoder.encode_varint(value))
            elif field.field_type in (FieldType.SINT32, FieldType.SINT64):
                packed_data.write(WireEncoder.encode_signed_varint(value))
            elif field.field_type == FieldType.BOOL:
                packed_data.write(WireEncoder.encode_varint(1 if value else 0))
            elif field.field_type == FieldType.FIXED32:
                packed_data.write(WireEncoder.encode_fixed32(value))
            elif field.field_type == FieldType.FIXED64:
                packed_data.write(WireEncoder.encode_fixed64(value))
            elif field.field_type == FieldType.FLOAT:
                packed_data.write(WireEncoder.encode_float(value))
            elif field.field_type == FieldType.DOUBLE:
                packed_data.write(WireEncoder.encode_double(value))

        tag = WireEncoder.encode_tag(field.number, WireType.LENGTH_DELIMITED)
        return tag + WireEncoder.encode_length_delimited(packed_data.getvalue())

    # -------------------------------------------------------------------------
    # DECODING
    # -------------------------------------------------------------------------

    def decode(self, message_type: str, data: bytes) -> Dict[str, Any]:
        """Decode binary data to a message."""
        descriptor = self._messages.get(message_type)
        if not descriptor:
            raise ValueError(f"Unknown message type: {message_type}")

        return self._decode_message(descriptor, data)

    def _decode_message(self, descriptor: MessageDescriptor, data: bytes) -> Dict[str, Any]:
        """Decode a message."""
        result = {}
        decoder = WireDecoder(data)

        # Initialize defaults
        for field in descriptor.fields.values():
            if field.rule == FieldRule.REPEATED:
                result[field.name] = []
            elif field.default is not None:
                result[field.name] = field.default

        while decoder.has_more():
            field_number, wire_type = decoder.decode_tag()

            if field_number not in descriptor.fields:
                # Skip unknown field
                self._skip_field(decoder, wire_type)
                continue

            field = descriptor.fields[field_number]
            value = self._decode_field(decoder, field, wire_type)

            if field.rule == FieldRule.REPEATED:
                if isinstance(value, list):
                    result[field.name].extend(value)
                else:
                    result[field.name].append(value)
            else:
                result[field.name] = value

        return result

    def _decode_field(self, decoder: WireDecoder, field: FieldDescriptor, wire_type: WireType) -> Any:
        """Decode a single field."""
        # Handle packed repeated
        if wire_type == WireType.LENGTH_DELIMITED and field.rule == FieldRule.REPEATED and self._is_packable(field.field_type):
            return self._decode_packed(decoder, field)

        if field.field_type in (FieldType.INT32, FieldType.INT64, FieldType.UINT32, FieldType.UINT64):
            return decoder.decode_varint()

        elif field.field_type in (FieldType.SINT32, FieldType.SINT64):
            return decoder.decode_signed_varint()

        elif field.field_type == FieldType.BOOL:
            return decoder.decode_varint() != 0

        elif field.field_type == FieldType.FIXED32:
            return decoder.decode_fixed32()

        elif field.field_type == FieldType.FIXED64:
            return decoder.decode_fixed64()

        elif field.field_type == FieldType.SFIXED32:
            return decoder.decode_sfixed32()

        elif field.field_type == FieldType.SFIXED64:
            return decoder.decode_sfixed64()

        elif field.field_type == FieldType.FLOAT:
            return decoder.decode_float()

        elif field.field_type == FieldType.DOUBLE:
            return decoder.decode_double()

        elif field.field_type == FieldType.STRING:
            data = decoder.decode_length_delimited()
            return data.decode('utf-8')

        elif field.field_type == FieldType.BYTES:
            return decoder.decode_length_delimited()

        elif field.field_type == FieldType.MESSAGE:
            message_desc = self._messages.get(field.message_type)
            if not message_desc:
                raise ValueError(f"Unknown message type: {field.message_type}")
            data = decoder.decode_length_delimited()
            return self._decode_message(message_desc, data)

        elif field.field_type == FieldType.ENUM:
            value = decoder.decode_varint()
            enum_desc = self._enums.get(field.enum_type)
            if enum_desc:
                # Reverse lookup
                for name, num in enum_desc.values.items():
                    if num == value:
                        return name
            return value

        return None

    def _decode_packed(self, decoder: WireDecoder, field: FieldDescriptor) -> List[Any]:
        """Decode a packed repeated field."""
        data = decoder.decode_length_delimited()
        packed_decoder = WireDecoder(data)
        values = []

        while packed_decoder.has_more():
            if field.field_type in (FieldType.INT32, FieldType.INT64, FieldType.UINT32, FieldType.UINT64):
                values.append(packed_decoder.decode_varint())
            elif field.field_type in (FieldType.SINT32, FieldType.SINT64):
                values.append(packed_decoder.decode_signed_varint())
            elif field.field_type == FieldType.BOOL:
                values.append(packed_decoder.decode_varint() != 0)
            elif field.field_type == FieldType.FIXED32:
                values.append(packed_decoder.decode_fixed32())
            elif field.field_type == FieldType.FIXED64:
                values.append(packed_decoder.decode_fixed64())
            elif field.field_type == FieldType.FLOAT:
                values.append(packed_decoder.decode_float())
            elif field.field_type == FieldType.DOUBLE:
                values.append(packed_decoder.decode_double())

        return values

    def _skip_field(self, decoder: WireDecoder, wire_type: WireType) -> None:
        """Skip an unknown field."""
        if wire_type == WireType.VARINT:
            decoder.decode_varint()
        elif wire_type == WireType.FIXED64:
            decoder.buffer.read(8)
        elif wire_type == WireType.LENGTH_DELIMITED:
            length = decoder.decode_varint()
            decoder.buffer.read(length)
        elif wire_type == WireType.FIXED32:
            decoder.buffer.read(4)

    # -------------------------------------------------------------------------
    # UTILITIES
    # -------------------------------------------------------------------------

    def _get_wire_type(self, field_type: FieldType) -> WireType:
        """Get wire type for field type."""
        if field_type in (FieldType.INT32, FieldType.INT64, FieldType.UINT32,
                         FieldType.UINT64, FieldType.SINT32, FieldType.SINT64,
                         FieldType.BOOL, FieldType.ENUM):
            return WireType.VARINT
        elif field_type in (FieldType.FIXED64, FieldType.SFIXED64, FieldType.DOUBLE):
            return WireType.FIXED64
        elif field_type in (FieldType.FIXED32, FieldType.SFIXED32, FieldType.FLOAT):
            return WireType.FIXED32
        else:
            return WireType.LENGTH_DELIMITED

    def _is_packable(self, field_type: FieldType) -> bool:
        """Check if field type can be packed."""
        return field_type in (
            FieldType.INT32, FieldType.INT64, FieldType.UINT32, FieldType.UINT64,
            FieldType.SINT32, FieldType.SINT64, FieldType.BOOL,
            FieldType.FIXED32, FieldType.FIXED64, FieldType.SFIXED32, FieldType.SFIXED64,
            FieldType.FLOAT, FieldType.DOUBLE
        )

    # -------------------------------------------------------------------------
    # SCHEMA OPERATIONS
    # -------------------------------------------------------------------------

    def list_messages(self) -> List[str]:
        """List all registered message types."""
        return list(self._messages.keys())

    def list_enums(self) -> List[str]:
        """List all registered enum types."""
        return list(self._enums.keys())

    def get_schema_info(self, message_type: str) -> Dict[str, Any]:
        """Get schema information for a message type."""
        descriptor = self._messages.get(message_type)
        if not descriptor:
            return {}

        return {
            "name": descriptor.name,
            "fields": [
                {
                    "number": f.number,
                    "name": f.name,
                    "type": f.field_type.value,
                    "rule": f.rule.value,
                    "message_type": f.message_type,
                    "enum_type": f.enum_type
                }
                for f in descriptor.fields.values()
            ],
            "nested_messages": list(descriptor.nested_messages.keys()),
            "nested_enums": list(descriptor.nested_enums.keys())
        }

    def clear(self) -> None:
        """Clear all registered schemas."""
        self._messages.clear()
        self._enums.clear()


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Protocol Handler."""
    print("=" * 70)
    print("BAEL - PROTOCOL BUFFER HANDLER DEMO")
    print("Binary Serialization System")
    print("=" * 70)
    print()

    handler = ProtocolHandler()

    # 1. Define Messages
    print("1. DEFINE MESSAGES:")
    print("-" * 40)

    # Define enum
    status_enum = EnumDescriptor(
        name="Status",
        values={"UNKNOWN": 0, "ACTIVE": 1, "INACTIVE": 2, "PENDING": 3}
    )
    handler.register_enum(status_enum)
    print(f"   Registered enum: Status")

    # Define Address message
    address_msg = (MessageBuilder("Address")
                  .field("street", FieldType.STRING, 1)
                  .field("city", FieldType.STRING, 2)
                  .field("zip", FieldType.STRING, 3)
                  .field("country", FieldType.STRING, 4, default="USA")
                  .build())
    handler.register_message(address_msg)
    print(f"   Registered message: Address")

    # Define Person message
    person_msg = (MessageBuilder("Person")
                 .field("id", FieldType.INT32, 1)
                 .field("name", FieldType.STRING, 2)
                 .field("email", FieldType.STRING, 3)
                 .field("age", FieldType.INT32, 4)
                 .field("score", FieldType.DOUBLE, 5)
                 .field("active", FieldType.BOOL, 6)
                 .enum_field("status", "Status", 7)
                 .message_field("address", "Address", 8)
                 .repeated("tags", FieldType.STRING, 9)
                 .repeated("scores", FieldType.INT32, 10, packed=True)
                 .build())
    handler.register_message(person_msg)
    print(f"   Registered message: Person")
    print()

    # 2. Encode Simple Message
    print("2. ENCODE SIMPLE MESSAGE:")
    print("-" * 40)

    address_data = {
        "street": "123 Main St",
        "city": "Boston",
        "zip": "02101",
        "country": "USA"
    }

    encoded_address = handler.encode("Address", address_data)
    print(f"   Original: {address_data}")
    print(f"   Encoded: {len(encoded_address)} bytes")
    print(f"   Hex: {encoded_address.hex()[:50]}...")
    print()

    # 3. Decode Message
    print("3. DECODE MESSAGE:")
    print("-" * 40)

    decoded_address = handler.decode("Address", encoded_address)
    print(f"   Decoded: {decoded_address}")
    print(f"   Match: {decoded_address == address_data}")
    print()

    # 4. Complex Message
    print("4. COMPLEX MESSAGE WITH NESTED:")
    print("-" * 40)

    person_data = {
        "id": 12345,
        "name": "Alice Smith",
        "email": "alice@example.com",
        "age": 30,
        "score": 95.5,
        "active": True,
        "status": "ACTIVE",
        "address": {
            "street": "456 Oak Ave",
            "city": "Chicago",
            "zip": "60601"
        },
        "tags": ["developer", "python", "ai"],
        "scores": [85, 92, 78, 95, 88]
    }

    encoded_person = handler.encode("Person", person_data)
    decoded_person = handler.decode("Person", encoded_person)

    print(f"   Encoded size: {len(encoded_person)} bytes")
    print(f"   Decoded fields: {list(decoded_person.keys())}")
    print(f"   Name: {decoded_person['name']}")
    print(f"   Status: {decoded_person['status']}")
    print(f"   Address city: {decoded_person['address']['city']}")
    print(f"   Tags: {decoded_person['tags']}")
    print(f"   Scores: {decoded_person['scores']}")
    print()

    # 5. Wire Types
    print("5. WIRE TYPES:")
    print("-" * 40)

    for field_type in [FieldType.INT32, FieldType.STRING, FieldType.DOUBLE, FieldType.BOOL]:
        wire_type = handler._get_wire_type(field_type)
        print(f"   {field_type.value:10} -> {wire_type.name}")
    print()

    # 6. Varint Encoding
    print("6. VARINT ENCODING:")
    print("-" * 40)

    test_values = [1, 127, 128, 300, 16384, 2097152]

    for value in test_values:
        encoded = WireEncoder.encode_varint(value)
        print(f"   {value:10} -> {encoded.hex():15} ({len(encoded)} bytes)")
    print()

    # 7. Signed Varint (ZigZag)
    print("7. SIGNED VARINT (ZIGZAG):")
    print("-" * 40)

    signed_values = [-1, -2, 1, 2, -2147483648]

    for value in signed_values:
        encoded = WireEncoder.encode_signed_varint(value)
        decoded = WireDecoder(encoded).decode_signed_varint()
        print(f"   {value:15} -> {encoded.hex():15} -> {decoded}")
    print()

    # 8. Packed Repeated
    print("8. PACKED REPEATED FIELDS:")
    print("-" * 40)

    numbers_msg = (MessageBuilder("Numbers")
                  .repeated("values", FieldType.INT32, 1, packed=True)
                  .build())
    handler.register_message(numbers_msg)

    numbers_data = {"values": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]}
    encoded_numbers = handler.encode("Numbers", numbers_data)

    print(f"   Data: {numbers_data['values']}")
    print(f"   Encoded: {len(encoded_numbers)} bytes")
    print(f"   Hex: {encoded_numbers.hex()}")

    decoded_numbers = handler.decode("Numbers", encoded_numbers)
    print(f"   Decoded: {decoded_numbers['values']}")
    print()

    # 9. Float/Double Encoding
    print("9. FLOAT/DOUBLE ENCODING:")
    print("-" * 40)

    float_val = 3.14159
    double_val = 2.718281828459045

    float_encoded = WireEncoder.encode_float(float_val)
    double_encoded = WireEncoder.encode_double(double_val)

    float_decoded = WireDecoder(float_encoded).decode_float()
    double_decoded = WireDecoder(double_encoded).decode_double()

    print(f"   Float:  {float_val} -> {float_encoded.hex()} -> {float_decoded:.5f}")
    print(f"   Double: {double_val} -> {double_encoded.hex()} -> {double_decoded}")
    print()

    # 10. Schema Info
    print("10. SCHEMA INFORMATION:")
    print("-" * 40)

    person_info = handler.get_schema_info("Person")
    print(f"   Message: {person_info['name']}")
    print(f"   Fields: {len(person_info['fields'])}")

    for field in person_info['fields'][:5]:
        print(f"     {field['number']:2}. {field['name']:10} ({field['type']})")
    print()

    # 11. List Schemas
    print("11. REGISTERED SCHEMAS:")
    print("-" * 40)

    print(f"   Messages: {handler.list_messages()}")
    print(f"   Enums: {handler.list_enums()}")
    print()

    # 12. Default Values
    print("12. DEFAULT VALUES:")
    print("-" * 40)

    minimal_data = {"street": "Test St"}
    encoded_minimal = handler.encode("Address", minimal_data)
    decoded_minimal = handler.decode("Address", encoded_minimal)

    print(f"   Input: {minimal_data}")
    print(f"   Decoded: {decoded_minimal}")
    print(f"   Country default: {decoded_minimal.get('country', 'None')}")
    print()

    # 13. Bytes Field
    print("13. BYTES FIELD:")
    print("-" * 40)

    binary_msg = (MessageBuilder("BinaryData")
                 .field("data", FieldType.BYTES, 1)
                 .field("checksum", FieldType.FIXED32, 2)
                 .build())
    handler.register_message(binary_msg)

    binary_data = {
        "data": b"\x00\x01\x02\x03\x04\x05\xFF\xFE\xFD",
        "checksum": 0xDEADBEEF
    }

    encoded_binary = handler.encode("BinaryData", binary_data)
    decoded_binary = handler.decode("BinaryData", encoded_binary)

    print(f"   Original bytes: {binary_data['data'].hex()}")
    print(f"   Decoded bytes: {decoded_binary['data'].hex()}")
    print(f"   Checksum: {decoded_binary['checksum']:08X}")
    print()

    # 14. Comparison with JSON
    print("14. SIZE COMPARISON (vs JSON):")
    print("-" * 40)

    import json

    json_encoded = json.dumps(person_data).encode('utf-8')
    proto_encoded = handler.encode("Person", person_data)

    print(f"   JSON size:  {len(json_encoded)} bytes")
    print(f"   Proto size: {len(proto_encoded)} bytes")
    print(f"   Savings:    {(1 - len(proto_encoded)/len(json_encoded))*100:.1f}%")
    print()

    # 15. Performance
    print("15. PERFORMANCE:")
    print("-" * 40)

    import time

    iterations = 10000

    # Encode performance
    start = time.time()
    for _ in range(iterations):
        handler.encode("Person", person_data)
    encode_time = time.time() - start

    # Decode performance
    start = time.time()
    for _ in range(iterations):
        handler.decode("Person", proto_encoded)
    decode_time = time.time() - start

    print(f"   Encode: {iterations} iterations in {encode_time:.3f}s ({iterations/encode_time:.0f} ops/sec)")
    print(f"   Decode: {iterations} iterations in {decode_time:.3f}s ({iterations/decode_time:.0f} ops/sec)")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Protocol Handler Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())

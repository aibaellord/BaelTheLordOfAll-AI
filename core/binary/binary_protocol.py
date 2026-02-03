#!/usr/bin/env python3
"""
BAEL - Binary Protocol Handler
Advanced binary protocol encoding/decoding for AI agents.

Features:
- Binary message framing
- Protocol buffer style encoding
- Variable-length integers
- Wire formats
- Message serialization
- Schema definition
- Checksum validation
- Streaming binary data
- Custom codecs
- Network byte ordering
"""

import asyncio
import hashlib
import struct
import uuid
import zlib
from abc import ABC, abstractmethod
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, IntEnum
from io import BytesIO
from typing import (
    Any, BinaryIO, Callable, Dict, Generic, Iterator, List,
    Optional, Tuple, Type, TypeVar, Union
)

import logging
logger = logging.getLogger(__name__)


T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class WireType(IntEnum):
    """Protocol wire types."""
    VARINT = 0      # int32, int64, uint32, uint64, bool, enum
    FIXED64 = 1     # fixed64, sfixed64, double
    LENGTH = 2      # string, bytes, embedded messages
    FIXED32 = 5     # fixed32, sfixed32, float


class FieldType(Enum):
    """Field data types."""
    INT32 = "int32"
    INT64 = "int64"
    UINT32 = "uint32"
    UINT64 = "uint64"
    SINT32 = "sint32"
    SINT64 = "sint64"
    BOOL = "bool"
    FLOAT = "float"
    DOUBLE = "double"
    STRING = "string"
    BYTES = "bytes"
    FIXED32 = "fixed32"
    FIXED64 = "fixed64"
    SFIXED32 = "sfixed32"
    SFIXED64 = "sfixed64"
    MESSAGE = "message"


class ByteOrder(Enum):
    """Byte ordering."""
    BIG_ENDIAN = "big"
    LITTLE_ENDIAN = "little"
    NETWORK = "big"


class FrameType(Enum):
    """Message frame types."""
    DATA = 0
    PING = 1
    PONG = 2
    CLOSE = 3
    ERROR = 4
    ACK = 5


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class FieldDescriptor:
    """Field descriptor."""
    number: int
    name: str
    field_type: FieldType
    repeated: bool = False
    optional: bool = False
    default: Any = None
    message_type: Optional[str] = None


@dataclass
class MessageDescriptor:
    """Message descriptor."""
    name: str
    fields: Dict[int, FieldDescriptor] = field(default_factory=dict)
    nested: Dict[str, 'MessageDescriptor'] = field(default_factory=dict)


@dataclass
class Frame:
    """Binary frame."""
    frame_type: FrameType
    sequence: int = 0
    payload: bytes = b""
    checksum: int = 0
    timestamp: float = field(default_factory=lambda: datetime.utcnow().timestamp())


@dataclass
class ParseResult:
    """Parse result."""
    success: bool
    data: Dict[str, Any] = field(default_factory=dict)
    bytes_consumed: int = 0
    error: Optional[str] = None


@dataclass
class EncodedMessage:
    """Encoded message."""
    data: bytes
    size: int = 0
    checksum: int = 0

    def __post_init__(self):
        self.size = len(self.data)
        self.checksum = zlib.crc32(self.data)


# =============================================================================
# VARINT CODEC
# =============================================================================

class VarintCodec:
    """Variable-length integer encoding/decoding."""

    @staticmethod
    def encode(value: int) -> bytes:
        """Encode integer as varint."""
        if value < 0:
            # Handle negative numbers using zigzag encoding
            value = (value << 1) ^ (value >> 63)

        result = []
        while value > 0x7F:
            result.append((value & 0x7F) | 0x80)
            value >>= 7
        result.append(value & 0x7F)

        return bytes(result) if result else b'\x00'

    @staticmethod
    def decode(data: bytes, offset: int = 0) -> Tuple[int, int]:
        """Decode varint from bytes. Returns (value, bytes_consumed)."""
        result = 0
        shift = 0
        pos = offset

        while pos < len(data):
            byte = data[pos]
            result |= (byte & 0x7F) << shift
            pos += 1

            if not (byte & 0x80):
                break

            shift += 7

            if shift > 63:
                raise ValueError("Varint too long")

        return result, pos - offset

    @staticmethod
    def encode_signed(value: int) -> bytes:
        """Encode signed integer using zigzag encoding."""
        # Zigzag encode
        if value >= 0:
            zigzag = value << 1
        else:
            zigzag = ((-value) << 1) - 1

        return VarintCodec.encode(zigzag)

    @staticmethod
    def decode_signed(data: bytes, offset: int = 0) -> Tuple[int, int]:
        """Decode signed varint. Returns (value, bytes_consumed)."""
        zigzag, consumed = VarintCodec.decode(data, offset)

        # Zigzag decode
        if zigzag & 1:
            value = -((zigzag >> 1) + 1)
        else:
            value = zigzag >> 1

        return value, consumed


# =============================================================================
# BINARY READER
# =============================================================================

class BinaryReader:
    """Binary data reader."""

    def __init__(self, data: bytes, order: ByteOrder = ByteOrder.LITTLE_ENDIAN):
        self._data = data
        self._pos = 0
        self._order = '>' if order == ByteOrder.BIG_ENDIAN else '<'

    @property
    def position(self) -> int:
        return self._pos

    @property
    def remaining(self) -> int:
        return len(self._data) - self._pos

    def seek(self, pos: int) -> None:
        self._pos = pos

    def skip(self, count: int) -> None:
        self._pos += count

    def read_bytes(self, count: int) -> bytes:
        """Read raw bytes."""
        result = self._data[self._pos:self._pos + count]
        self._pos += count
        return result

    def read_byte(self) -> int:
        """Read single byte."""
        result = self._data[self._pos]
        self._pos += 1
        return result

    def read_bool(self) -> bool:
        """Read boolean."""
        return self.read_byte() != 0

    def read_int8(self) -> int:
        """Read signed 8-bit integer."""
        data = self.read_bytes(1)
        return struct.unpack(f'{self._order}b', data)[0]

    def read_uint8(self) -> int:
        """Read unsigned 8-bit integer."""
        return self.read_byte()

    def read_int16(self) -> int:
        """Read signed 16-bit integer."""
        data = self.read_bytes(2)
        return struct.unpack(f'{self._order}h', data)[0]

    def read_uint16(self) -> int:
        """Read unsigned 16-bit integer."""
        data = self.read_bytes(2)
        return struct.unpack(f'{self._order}H', data)[0]

    def read_int32(self) -> int:
        """Read signed 32-bit integer."""
        data = self.read_bytes(4)
        return struct.unpack(f'{self._order}i', data)[0]

    def read_uint32(self) -> int:
        """Read unsigned 32-bit integer."""
        data = self.read_bytes(4)
        return struct.unpack(f'{self._order}I', data)[0]

    def read_int64(self) -> int:
        """Read signed 64-bit integer."""
        data = self.read_bytes(8)
        return struct.unpack(f'{self._order}q', data)[0]

    def read_uint64(self) -> int:
        """Read unsigned 64-bit integer."""
        data = self.read_bytes(8)
        return struct.unpack(f'{self._order}Q', data)[0]

    def read_float(self) -> float:
        """Read 32-bit float."""
        data = self.read_bytes(4)
        return struct.unpack(f'{self._order}f', data)[0]

    def read_double(self) -> float:
        """Read 64-bit double."""
        data = self.read_bytes(8)
        return struct.unpack(f'{self._order}d', data)[0]

    def read_varint(self) -> int:
        """Read variable-length integer."""
        value, consumed = VarintCodec.decode(self._data, self._pos)
        self._pos += consumed
        return value

    def read_string(self) -> str:
        """Read length-prefixed string."""
        length = self.read_varint()
        data = self.read_bytes(length)
        return data.decode('utf-8')

    def read_bytes_prefixed(self) -> bytes:
        """Read length-prefixed bytes."""
        length = self.read_varint()
        return self.read_bytes(length)


# =============================================================================
# BINARY WRITER
# =============================================================================

class BinaryWriter:
    """Binary data writer."""

    def __init__(self, order: ByteOrder = ByteOrder.LITTLE_ENDIAN):
        self._buffer = BytesIO()
        self._order = '>' if order == ByteOrder.BIG_ENDIAN else '<'

    def get_data(self) -> bytes:
        """Get written data."""
        return self._buffer.getvalue()

    @property
    def size(self) -> int:
        return self._buffer.tell()

    def write_bytes(self, data: bytes) -> None:
        """Write raw bytes."""
        self._buffer.write(data)

    def write_byte(self, value: int) -> None:
        """Write single byte."""
        self._buffer.write(bytes([value & 0xFF]))

    def write_bool(self, value: bool) -> None:
        """Write boolean."""
        self.write_byte(1 if value else 0)

    def write_int8(self, value: int) -> None:
        """Write signed 8-bit integer."""
        self._buffer.write(struct.pack(f'{self._order}b', value))

    def write_uint8(self, value: int) -> None:
        """Write unsigned 8-bit integer."""
        self.write_byte(value)

    def write_int16(self, value: int) -> None:
        """Write signed 16-bit integer."""
        self._buffer.write(struct.pack(f'{self._order}h', value))

    def write_uint16(self, value: int) -> None:
        """Write unsigned 16-bit integer."""
        self._buffer.write(struct.pack(f'{self._order}H', value))

    def write_int32(self, value: int) -> None:
        """Write signed 32-bit integer."""
        self._buffer.write(struct.pack(f'{self._order}i', value))

    def write_uint32(self, value: int) -> None:
        """Write unsigned 32-bit integer."""
        self._buffer.write(struct.pack(f'{self._order}I', value))

    def write_int64(self, value: int) -> None:
        """Write signed 64-bit integer."""
        self._buffer.write(struct.pack(f'{self._order}q', value))

    def write_uint64(self, value: int) -> None:
        """Write unsigned 64-bit integer."""
        self._buffer.write(struct.pack(f'{self._order}Q', value))

    def write_float(self, value: float) -> None:
        """Write 32-bit float."""
        self._buffer.write(struct.pack(f'{self._order}f', value))

    def write_double(self, value: float) -> None:
        """Write 64-bit double."""
        self._buffer.write(struct.pack(f'{self._order}d', value))

    def write_varint(self, value: int) -> None:
        """Write variable-length integer."""
        self._buffer.write(VarintCodec.encode(value))

    def write_string(self, value: str) -> None:
        """Write length-prefixed string."""
        data = value.encode('utf-8')
        self.write_varint(len(data))
        self.write_bytes(data)

    def write_bytes_prefixed(self, data: bytes) -> None:
        """Write length-prefixed bytes."""
        self.write_varint(len(data))
        self.write_bytes(data)


# =============================================================================
# FRAME ENCODER/DECODER
# =============================================================================

class FrameCodec:
    """Frame encoding/decoding."""

    HEADER_SIZE = 16  # 1 byte type + 4 bytes seq + 4 bytes len + 4 bytes checksum + 3 bytes reserved
    MAGIC = b'\xBA\xEL'  # BAEL magic bytes (2 bytes)

    def encode(self, frame: Frame) -> bytes:
        """Encode frame to bytes."""
        writer = BinaryWriter(ByteOrder.BIG_ENDIAN)

        # Magic bytes
        writer.write_bytes(self.MAGIC)

        # Frame type
        writer.write_byte(frame.frame_type.value)

        # Sequence number
        writer.write_uint32(frame.sequence)

        # Payload length
        writer.write_uint32(len(frame.payload))

        # Timestamp
        writer.write_double(frame.timestamp)

        # Payload
        writer.write_bytes(frame.payload)

        # Calculate and append checksum
        data = writer.get_data()
        checksum = zlib.crc32(data)
        writer.write_uint32(checksum)

        return writer.get_data()

    def decode(self, data: bytes) -> Optional[Frame]:
        """Decode bytes to frame."""
        if len(data) < self.HEADER_SIZE + 4:  # Header + checksum
            return None

        reader = BinaryReader(data, ByteOrder.BIG_ENDIAN)

        # Verify magic
        magic = reader.read_bytes(2)
        if magic != self.MAGIC:
            return None

        # Frame type
        frame_type_value = reader.read_byte()
        try:
            frame_type = FrameType(frame_type_value)
        except ValueError:
            return None

        # Sequence
        sequence = reader.read_uint32()

        # Payload length
        payload_length = reader.read_uint32()

        # Timestamp
        timestamp = reader.read_double()

        # Payload
        payload = reader.read_bytes(payload_length)

        # Checksum
        stored_checksum = reader.read_uint32()

        # Verify checksum
        data_to_check = data[:-4]
        computed_checksum = zlib.crc32(data_to_check)

        if computed_checksum != stored_checksum:
            return None

        return Frame(
            frame_type=frame_type,
            sequence=sequence,
            payload=payload,
            checksum=stored_checksum,
            timestamp=timestamp
        )


# =============================================================================
# PROTOCOL BUFFER ENCODER
# =============================================================================

class ProtoEncoder:
    """Protocol buffer style encoder."""

    def __init__(self):
        self._wire_types = {
            FieldType.INT32: WireType.VARINT,
            FieldType.INT64: WireType.VARINT,
            FieldType.UINT32: WireType.VARINT,
            FieldType.UINT64: WireType.VARINT,
            FieldType.SINT32: WireType.VARINT,
            FieldType.SINT64: WireType.VARINT,
            FieldType.BOOL: WireType.VARINT,
            FieldType.FLOAT: WireType.FIXED32,
            FieldType.DOUBLE: WireType.FIXED64,
            FieldType.STRING: WireType.LENGTH,
            FieldType.BYTES: WireType.LENGTH,
            FieldType.FIXED32: WireType.FIXED32,
            FieldType.FIXED64: WireType.FIXED64,
            FieldType.SFIXED32: WireType.FIXED32,
            FieldType.SFIXED64: WireType.FIXED64,
            FieldType.MESSAGE: WireType.LENGTH,
        }

    def encode_field_key(self, field_number: int, wire_type: WireType) -> bytes:
        """Encode field key (tag)."""
        key = (field_number << 3) | wire_type.value
        return VarintCodec.encode(key)

    def encode_field(
        self,
        field_number: int,
        field_type: FieldType,
        value: Any
    ) -> bytes:
        """Encode a single field."""
        wire_type = self._wire_types[field_type]
        writer = BinaryWriter()

        # Write field key
        writer.write_bytes(self.encode_field_key(field_number, wire_type))

        # Write value based on type
        if field_type in (FieldType.INT32, FieldType.INT64, FieldType.UINT32, FieldType.UINT64):
            writer.write_varint(value)
        elif field_type in (FieldType.SINT32, FieldType.SINT64):
            writer.write_bytes(VarintCodec.encode_signed(value))
        elif field_type == FieldType.BOOL:
            writer.write_varint(1 if value else 0)
        elif field_type == FieldType.FLOAT:
            writer.write_float(value)
        elif field_type == FieldType.DOUBLE:
            writer.write_double(value)
        elif field_type == FieldType.STRING:
            encoded = value.encode('utf-8')
            writer.write_varint(len(encoded))
            writer.write_bytes(encoded)
        elif field_type == FieldType.BYTES:
            writer.write_varint(len(value))
            writer.write_bytes(value)
        elif field_type in (FieldType.FIXED32, FieldType.SFIXED32):
            writer.write_int32(value) if field_type == FieldType.SFIXED32 else writer.write_uint32(value)
        elif field_type in (FieldType.FIXED64, FieldType.SFIXED64):
            writer.write_int64(value) if field_type == FieldType.SFIXED64 else writer.write_uint64(value)

        return writer.get_data()

    def encode_message(
        self,
        descriptor: MessageDescriptor,
        data: Dict[str, Any]
    ) -> bytes:
        """Encode a message."""
        writer = BinaryWriter()

        for field_num, field_desc in sorted(descriptor.fields.items()):
            if field_desc.name not in data:
                continue

            value = data[field_desc.name]

            if field_desc.repeated and isinstance(value, list):
                for item in value:
                    writer.write_bytes(self.encode_field(field_num, field_desc.field_type, item))
            else:
                writer.write_bytes(self.encode_field(field_num, field_desc.field_type, value))

        return writer.get_data()


# =============================================================================
# PROTOCOL BUFFER DECODER
# =============================================================================

class ProtoDecoder:
    """Protocol buffer style decoder."""

    def decode_field_key(self, data: bytes, offset: int = 0) -> Tuple[int, WireType, int]:
        """Decode field key. Returns (field_number, wire_type, bytes_consumed)."""
        key, consumed = VarintCodec.decode(data, offset)
        field_number = key >> 3
        wire_type = WireType(key & 0x07)
        return field_number, wire_type, consumed

    def decode_value(
        self,
        data: bytes,
        offset: int,
        wire_type: WireType,
        field_type: FieldType
    ) -> Tuple[Any, int]:
        """Decode a value. Returns (value, bytes_consumed)."""
        reader = BinaryReader(data[offset:])

        if wire_type == WireType.VARINT:
            if field_type in (FieldType.SINT32, FieldType.SINT64):
                value, consumed = VarintCodec.decode_signed(data, offset)
            else:
                value, consumed = VarintCodec.decode(data, offset)

            if field_type == FieldType.BOOL:
                value = bool(value)

            return value, consumed

        elif wire_type == WireType.FIXED32:
            if field_type == FieldType.FLOAT:
                return reader.read_float(), 4
            elif field_type == FieldType.SFIXED32:
                return reader.read_int32(), 4
            else:
                return reader.read_uint32(), 4

        elif wire_type == WireType.FIXED64:
            if field_type == FieldType.DOUBLE:
                return reader.read_double(), 8
            elif field_type == FieldType.SFIXED64:
                return reader.read_int64(), 8
            else:
                return reader.read_uint64(), 8

        elif wire_type == WireType.LENGTH:
            length, length_consumed = VarintCodec.decode(data, offset)
            start = offset + length_consumed
            value_data = data[start:start + length]

            if field_type == FieldType.STRING:
                return value_data.decode('utf-8'), length_consumed + length
            else:
                return value_data, length_consumed + length

        return None, 0

    def decode_message(
        self,
        descriptor: MessageDescriptor,
        data: bytes
    ) -> ParseResult:
        """Decode a message."""
        result: Dict[str, Any] = {}
        offset = 0

        # Initialize repeated fields
        for field_desc in descriptor.fields.values():
            if field_desc.repeated:
                result[field_desc.name] = []

        try:
            while offset < len(data):
                # Decode field key
                field_number, wire_type, key_consumed = self.decode_field_key(data, offset)
                offset += key_consumed

                # Find field descriptor
                if field_number not in descriptor.fields:
                    # Skip unknown field
                    if wire_type == WireType.VARINT:
                        _, consumed = VarintCodec.decode(data, offset)
                        offset += consumed
                    elif wire_type == WireType.FIXED32:
                        offset += 4
                    elif wire_type == WireType.FIXED64:
                        offset += 8
                    elif wire_type == WireType.LENGTH:
                        length, consumed = VarintCodec.decode(data, offset)
                        offset += consumed + length
                    continue

                field_desc = descriptor.fields[field_number]

                # Decode value
                value, consumed = self.decode_value(data, offset, wire_type, field_desc.field_type)
                offset += consumed

                # Store value
                if field_desc.repeated:
                    result[field_desc.name].append(value)
                else:
                    result[field_desc.name] = value

            return ParseResult(success=True, data=result, bytes_consumed=offset)

        except Exception as e:
            return ParseResult(success=False, error=str(e), bytes_consumed=offset)


# =============================================================================
# SCHEMA BUILDER
# =============================================================================

class SchemaBuilder:
    """Build message schemas."""

    def __init__(self):
        self._messages: Dict[str, MessageDescriptor] = {}

    def message(self, name: str) -> 'MessageBuilder':
        """Start building a message."""
        return MessageBuilder(self, name)

    def add_message(self, descriptor: MessageDescriptor) -> None:
        """Add a message descriptor."""
        self._messages[descriptor.name] = descriptor

    def get_message(self, name: str) -> Optional[MessageDescriptor]:
        """Get a message descriptor."""
        return self._messages.get(name)

    def all_messages(self) -> Dict[str, MessageDescriptor]:
        """Get all message descriptors."""
        return self._messages.copy()


class MessageBuilder:
    """Message builder for schema construction."""

    def __init__(self, schema: SchemaBuilder, name: str):
        self._schema = schema
        self._name = name
        self._fields: Dict[int, FieldDescriptor] = {}
        self._next_number = 1

    def field(
        self,
        name: str,
        field_type: FieldType,
        number: Optional[int] = None,
        repeated: bool = False,
        optional: bool = False,
        default: Any = None
    ) -> 'MessageBuilder':
        """Add a field."""
        if number is None:
            number = self._next_number

        self._fields[number] = FieldDescriptor(
            number=number,
            name=name,
            field_type=field_type,
            repeated=repeated,
            optional=optional,
            default=default
        )

        self._next_number = max(self._next_number, number + 1)
        return self

    def build(self) -> MessageDescriptor:
        """Build the message descriptor."""
        descriptor = MessageDescriptor(
            name=self._name,
            fields=self._fields
        )
        self._schema.add_message(descriptor)
        return descriptor


# =============================================================================
# BINARY STREAM
# =============================================================================

class BinaryStream:
    """Streaming binary protocol handler."""

    def __init__(self, chunk_size: int = 4096):
        self.chunk_size = chunk_size
        self._buffer = BytesIO()
        self._frame_codec = FrameCodec()

    def write_frame(self, frame: Frame) -> bytes:
        """Encode and write frame."""
        return self._frame_codec.encode(frame)

    def read_frames(self, data: bytes) -> List[Frame]:
        """Read frames from data."""
        self._buffer.write(data)
        self._buffer.seek(0)

        frames = []
        buffer_data = self._buffer.read()
        offset = 0

        while offset < len(buffer_data):
            # Need at least header + checksum
            if len(buffer_data) - offset < FrameCodec.HEADER_SIZE + 4:
                break

            # Try to decode frame
            frame = self._frame_codec.decode(buffer_data[offset:])
            if frame:
                frames.append(frame)
                # Calculate consumed bytes (header + payload + checksum)
                consumed = FrameCodec.HEADER_SIZE + len(frame.payload) + 4
                offset += consumed
            else:
                offset += 1  # Skip invalid byte

        # Keep remaining data in buffer
        remaining = buffer_data[offset:]
        self._buffer = BytesIO()
        self._buffer.write(remaining)

        return frames

    def clear(self) -> None:
        """Clear buffer."""
        self._buffer = BytesIO()


# =============================================================================
# BINARY PROTOCOL MANAGER
# =============================================================================

class BinaryProtocol:
    """
    Binary Protocol Handler for BAEL.

    Advanced binary protocol encoding/decoding.
    """

    def __init__(self, byte_order: ByteOrder = ByteOrder.LITTLE_ENDIAN):
        self.byte_order = byte_order
        self._schema = SchemaBuilder()
        self._encoder = ProtoEncoder()
        self._decoder = ProtoDecoder()
        self._frame_codec = FrameCodec()
        self._sequence = 0

    # -------------------------------------------------------------------------
    # SCHEMA
    # -------------------------------------------------------------------------

    def define_message(self, name: str) -> MessageBuilder:
        """Define a message type."""
        return self._schema.message(name)

    def get_message(self, name: str) -> Optional[MessageDescriptor]:
        """Get a message descriptor."""
        return self._schema.get_message(name)

    # -------------------------------------------------------------------------
    # BASIC I/O
    # -------------------------------------------------------------------------

    def reader(self, data: bytes) -> BinaryReader:
        """Create a binary reader."""
        return BinaryReader(data, self.byte_order)

    def writer(self) -> BinaryWriter:
        """Create a binary writer."""
        return BinaryWriter(self.byte_order)

    # -------------------------------------------------------------------------
    # VARINT
    # -------------------------------------------------------------------------

    def encode_varint(self, value: int) -> bytes:
        """Encode a varint."""
        return VarintCodec.encode(value)

    def decode_varint(self, data: bytes, offset: int = 0) -> Tuple[int, int]:
        """Decode a varint."""
        return VarintCodec.decode(data, offset)

    # -------------------------------------------------------------------------
    # MESSAGE ENCODING
    # -------------------------------------------------------------------------

    def encode(self, message_name: str, data: Dict[str, Any]) -> EncodedMessage:
        """Encode a message."""
        descriptor = self._schema.get_message(message_name)
        if not descriptor:
            raise ValueError(f"Unknown message type: {message_name}")

        encoded = self._encoder.encode_message(descriptor, data)
        return EncodedMessage(data=encoded)

    def decode(self, message_name: str, data: bytes) -> ParseResult:
        """Decode a message."""
        descriptor = self._schema.get_message(message_name)
        if not descriptor:
            return ParseResult(success=False, error=f"Unknown message type: {message_name}")

        return self._decoder.decode_message(descriptor, data)

    # -------------------------------------------------------------------------
    # FRAME OPERATIONS
    # -------------------------------------------------------------------------

    def create_frame(
        self,
        payload: bytes,
        frame_type: FrameType = FrameType.DATA
    ) -> Frame:
        """Create a frame."""
        self._sequence += 1
        return Frame(
            frame_type=frame_type,
            sequence=self._sequence,
            payload=payload
        )

    def encode_frame(self, frame: Frame) -> bytes:
        """Encode a frame."""
        return self._frame_codec.encode(frame)

    def decode_frame(self, data: bytes) -> Optional[Frame]:
        """Decode a frame."""
        return self._frame_codec.decode(data)

    def create_data_frame(self, data: bytes) -> bytes:
        """Create and encode a data frame."""
        frame = self.create_frame(data, FrameType.DATA)
        return self.encode_frame(frame)

    def create_ping_frame(self) -> bytes:
        """Create and encode a ping frame."""
        frame = self.create_frame(b"", FrameType.PING)
        return self.encode_frame(frame)

    def create_pong_frame(self) -> bytes:
        """Create and encode a pong frame."""
        frame = self.create_frame(b"", FrameType.PONG)
        return self.encode_frame(frame)

    # -------------------------------------------------------------------------
    # STREAM
    # -------------------------------------------------------------------------

    def create_stream(self, chunk_size: int = 4096) -> BinaryStream:
        """Create a binary stream."""
        return BinaryStream(chunk_size)

    # -------------------------------------------------------------------------
    # UTILITIES
    # -------------------------------------------------------------------------

    def checksum(self, data: bytes) -> int:
        """Calculate CRC32 checksum."""
        return zlib.crc32(data)

    def hash_data(self, data: bytes, algorithm: str = "sha256") -> str:
        """Calculate hash of data."""
        hasher = hashlib.new(algorithm)
        hasher.update(data)
        return hasher.hexdigest()

    def pack(self, fmt: str, *values) -> bytes:
        """Pack values using struct format."""
        prefix = '>' if self.byte_order == ByteOrder.BIG_ENDIAN else '<'
        return struct.pack(prefix + fmt, *values)

    def unpack(self, fmt: str, data: bytes) -> Tuple:
        """Unpack data using struct format."""
        prefix = '>' if self.byte_order == ByteOrder.BIG_ENDIAN else '<'
        return struct.unpack(prefix + fmt, data)


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Binary Protocol Handler."""
    print("=" * 70)
    print("BAEL - BINARY PROTOCOL HANDLER DEMO")
    print("Advanced Binary Encoding/Decoding for AI Agents")
    print("=" * 70)
    print()

    protocol = BinaryProtocol()

    # 1. Varint Encoding
    print("1. VARINT ENCODING:")
    print("-" * 40)

    test_values = [0, 1, 127, 128, 16383, 16384, 300, 150]
    for value in test_values:
        encoded = protocol.encode_varint(value)
        decoded, _ = protocol.decode_varint(encoded)
        print(f"   {value:6} -> {encoded.hex():16} -> {decoded}")
    print()

    # 2. Binary Reader/Writer
    print("2. BINARY READER/WRITER:")
    print("-" * 40)

    writer = protocol.writer()
    writer.write_uint32(42)
    writer.write_float(3.14)
    writer.write_string("BAEL")
    writer.write_bool(True)

    data = writer.get_data()
    print(f"   Written: {data.hex()}")
    print(f"   Size: {len(data)} bytes")

    reader = protocol.reader(data)
    print(f"   uint32: {reader.read_uint32()}")
    print(f"   float: {reader.read_float():.2f}")
    print(f"   string: {reader.read_string()}")
    print(f"   bool: {reader.read_bool()}")
    print()

    # 3. Message Schema Definition
    print("3. MESSAGE SCHEMA DEFINITION:")
    print("-" * 40)

    # Define a User message
    user_msg = protocol.define_message("User") \
        .field("id", FieldType.UINT32, number=1) \
        .field("name", FieldType.STRING, number=2) \
        .field("email", FieldType.STRING, number=3) \
        .field("active", FieldType.BOOL, number=4) \
        .field("score", FieldType.DOUBLE, number=5) \
        .build()

    print(f"   Message: {user_msg.name}")
    for num, field in user_msg.fields.items():
        print(f"   Field {num}: {field.name} ({field.field_type.value})")
    print()

    # 4. Message Encoding
    print("4. MESSAGE ENCODING:")
    print("-" * 40)

    user_data = {
        "id": 12345,
        "name": "BAEL",
        "email": "bael@ai.lord",
        "active": True,
        "score": 99.99
    }

    encoded = protocol.encode("User", user_data)
    print(f"   Original: {user_data}")
    print(f"   Encoded: {encoded.data.hex()}")
    print(f"   Size: {encoded.size} bytes")
    print(f"   Checksum: {encoded.checksum}")
    print()

    # 5. Message Decoding
    print("5. MESSAGE DECODING:")
    print("-" * 40)

    result = protocol.decode("User", encoded.data)
    print(f"   Success: {result.success}")
    print(f"   Decoded: {result.data}")
    print(f"   Bytes consumed: {result.bytes_consumed}")
    print()

    # 6. Frame Encoding
    print("6. FRAME ENCODING:")
    print("-" * 40)

    frame = protocol.create_frame(
        payload=b"Hello, BAEL!",
        frame_type=FrameType.DATA
    )

    frame_data = protocol.encode_frame(frame)
    print(f"   Frame type: {frame.frame_type.value}")
    print(f"   Sequence: {frame.sequence}")
    print(f"   Payload: {frame.payload}")
    print(f"   Encoded size: {len(frame_data)} bytes")
    print()

    # 7. Frame Decoding
    print("7. FRAME DECODING:")
    print("-" * 40)

    decoded_frame = protocol.decode_frame(frame_data)
    if decoded_frame:
        print(f"   Type: {decoded_frame.frame_type.value}")
        print(f"   Sequence: {decoded_frame.sequence}")
        print(f"   Payload: {decoded_frame.payload}")
        print(f"   Checksum: {decoded_frame.checksum}")
    print()

    # 8. Special Frames
    print("8. SPECIAL FRAMES:")
    print("-" * 40)

    ping = protocol.create_ping_frame()
    pong = protocol.create_pong_frame()
    print(f"   Ping frame: {len(ping)} bytes")
    print(f"   Pong frame: {len(pong)} bytes")
    print()

    # 9. Streaming
    print("9. STREAMING:")
    print("-" * 40)

    stream = protocol.create_stream()

    # Write multiple frames
    frames_to_send = []
    for i in range(3):
        f = protocol.create_frame(f"Message {i}".encode())
        frames_to_send.append(protocol.encode_frame(f))

    # Simulate receiving data
    combined = b"".join(frames_to_send)
    received_frames = stream.read_frames(combined)
    print(f"   Sent: {len(frames_to_send)} frames")
    print(f"   Received: {len(received_frames)} frames")
    for f in received_frames:
        print(f"   - {f.payload.decode()}")
    print()

    # 10. Utilities
    print("10. UTILITIES:")
    print("-" * 40)

    test_data = b"BAEL is the Lord of All AI Agents"
    checksum = protocol.checksum(test_data)
    hash_val = protocol.hash_data(test_data)

    print(f"   Data: {test_data.decode()}")
    print(f"   CRC32: {checksum}")
    print(f"   SHA256: {hash_val[:32]}...")

    packed = protocol.pack("IHB", 42, 1000, 255)
    unpacked = protocol.unpack("IHB", packed)
    print(f"   Packed: {packed.hex()}")
    print(f"   Unpacked: {unpacked}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Binary Protocol Handler Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())

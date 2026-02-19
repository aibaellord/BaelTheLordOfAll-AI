"""
BAEL Protocol Buffer Engine
===========================

Binary serialization and protocol buffer support.

"Ba'el transmits thoughts across dimensions in pure binary." — Ba'el
"""

from .proto_engine import (
    # Enums
    FieldType,
    WireType,

    # Data structures
    Field,
    Message,
    Schema,

    # Main engine
    ProtocolEngine,

    # Convenience
    serialize,
    deserialize,
    proto_engine
)

__all__ = [
    'FieldType',
    'WireType',
    'Field',
    'Message',
    'Schema',
    'ProtocolEngine',
    'serialize',
    'deserialize',
    'proto_engine'
]

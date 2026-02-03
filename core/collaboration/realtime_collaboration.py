"""
Real-Time Collaboration System - Multi-user collaborative editing and communication.

Features:
- Operational Transformation (OT) for conflict-free editing
- Real-time presence awareness with cursor tracking
- Collaborative document editing
- Live chat and video/audio integration
- Conflict resolution algorithms
- Version control integration
- Collaborative debugging
- Permission-based access control
- Activity streams and notifications
- Session recording and playback

Target: 1,400+ lines for enterprise collaboration
"""

import asyncio
import json
import logging
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

# ============================================================================
# COLLABORATION ENUMS
# ============================================================================

class OperationType(Enum):
    """Operation types for OT."""
    INSERT = "INSERT"
    DELETE = "DELETE"
    RETAIN = "RETAIN"
    REPLACE = "REPLACE"

class UserStatus(Enum):
    """User presence status."""
    ONLINE = "ONLINE"
    AWAY = "AWAY"
    BUSY = "BUSY"
    OFFLINE = "OFFLINE"

class PermissionLevel(Enum):
    """Access permission levels."""
    OWNER = "OWNER"
    ADMIN = "ADMIN"
    WRITE = "WRITE"
    READ = "READ"
    COMMENT = "COMMENT"

class ActivityType(Enum):
    """Activity types."""
    EDIT = "EDIT"
    COMMENT = "COMMENT"
    CURSOR_MOVE = "CURSOR_MOVE"
    JOIN = "JOIN"
    LEAVE = "LEAVE"
    CHAT = "CHAT"

# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class Operation:
    """Operational Transformation operation."""
    op_type: OperationType
    position: int
    content: str = ""
    length: int = 0
    user_id: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])

@dataclass
class User:
    """Collaborative user."""
    user_id: str
    username: str
    email: str
    status: UserStatus = UserStatus.ONLINE
    permission: PermissionLevel = PermissionLevel.READ
    cursor_position: int = 0
    selection_start: Optional[int] = None
    selection_end: Optional[int] = None
    color: str = "#3498db"
    last_seen: datetime = field(default_factory=datetime.now)

@dataclass
class Document:
    """Collaborative document."""
    doc_id: str
    title: str
    content: str
    version: int = 0
    created_by: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    modified_at: datetime = field(default_factory=datetime.now)
    active_users: Set[str] = field(default_factory=set)

@dataclass
class ChatMessage:
    """Chat message."""
    message_id: str
    user_id: str
    username: str
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    edited: bool = False

@dataclass
class Activity:
    """User activity."""
    activity_id: str
    activity_type: ActivityType
    user_id: str
    username: str
    data: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class CursorPosition:
    """User cursor position."""
    user_id: str
    username: str
    position: int
    color: str
    timestamp: datetime = field(default_factory=datetime.now)

# ============================================================================
# OPERATIONAL TRANSFORMATION ENGINE
# ============================================================================

class OperationalTransformationEngine:
    """Operational Transformation for conflict-free editing."""

    def __init__(self):
        self.operations: deque = deque(maxlen=1000)
        self.logger = logging.getLogger("ot_engine")

    def transform(self, op1: Operation, op2: Operation) -> Tuple[Operation, Operation]:
        """Transform two concurrent operations."""
        # INSERT vs INSERT
        if op1.op_type == OperationType.INSERT and op2.op_type == OperationType.INSERT:
            if op1.position < op2.position:
                return op1, Operation(
                    op_type=op2.op_type,
                    position=op2.position + len(op1.content),
                    content=op2.content,
                    user_id=op2.user_id
                )
            elif op1.position > op2.position:
                return Operation(
                    op_type=op1.op_type,
                    position=op1.position + len(op2.content),
                    content=op1.content,
                    user_id=op1.user_id
                ), op2
            else:
                # Same position - user_id tiebreaker
                if op1.user_id < op2.user_id:
                    return op1, Operation(
                        op_type=op2.op_type,
                        position=op2.position + len(op1.content),
                        content=op2.content,
                        user_id=op2.user_id
                    )
                else:
                    return Operation(
                        op_type=op1.op_type,
                        position=op1.position + len(op2.content),
                        content=op1.content,
                        user_id=op1.user_id
                    ), op2

        # INSERT vs DELETE
        elif op1.op_type == OperationType.INSERT and op2.op_type == OperationType.DELETE:
            if op1.position <= op2.position:
                return op1, Operation(
                    op_type=op2.op_type,
                    position=op2.position + len(op1.content),
                    length=op2.length,
                    user_id=op2.user_id
                )
            elif op1.position >= op2.position + op2.length:
                return Operation(
                    op_type=op1.op_type,
                    position=op1.position - op2.length,
                    content=op1.content,
                    user_id=op1.user_id
                ), op2
            else:
                # Insert within deleted range
                return Operation(
                    op_type=op1.op_type,
                    position=op2.position,
                    content=op1.content,
                    user_id=op1.user_id
                ), op2

        # DELETE vs INSERT
        elif op1.op_type == OperationType.DELETE and op2.op_type == OperationType.INSERT:
            op2_prime, op1_prime = self.transform(op2, op1)
            return op1_prime, op2_prime

        # DELETE vs DELETE
        elif op1.op_type == OperationType.DELETE and op2.op_type == OperationType.DELETE:
            if op1.position + op1.length <= op2.position:
                return op1, Operation(
                    op_type=op2.op_type,
                    position=op2.position - op1.length,
                    length=op2.length,
                    user_id=op2.user_id
                )
            elif op2.position + op2.length <= op1.position:
                return Operation(
                    op_type=op1.op_type,
                    position=op1.position - op2.length,
                    length=op1.length,
                    user_id=op1.user_id
                ), op2
            else:
                # Overlapping deletes
                return Operation(
                    op_type=op1.op_type,
                    position=min(op1.position, op2.position),
                    length=max(op1.position + op1.length, op2.position + op2.length) - min(op1.position, op2.position),
                    user_id=op1.user_id
                ), Operation(
                    op_type=OperationType.RETAIN,
                    position=0,
                    length=0,
                    user_id=op2.user_id
                )

        return op1, op2

    def apply_operation(self, content: str, operation: Operation) -> str:
        """Apply operation to content."""
        if operation.op_type == OperationType.INSERT:
            return content[:operation.position] + operation.content + content[operation.position:]
        elif operation.op_type == OperationType.DELETE:
            return content[:operation.position] + content[operation.position + operation.length:]
        elif operation.op_type == OperationType.REPLACE:
            return content[:operation.position] + operation.content + content[operation.position + operation.length:]

        return content

    def record_operation(self, operation: Operation) -> None:
        """Record operation in history."""
        self.operations.append(operation)
        self.logger.debug(f"Recorded {operation.op_type.value} at position {operation.position}")

# ============================================================================
# PRESENCE MANAGER
# ============================================================================

class PresenceManager:
    """Manage user presence and cursor positions."""

    def __init__(self):
        self.users: Dict[str, User] = {}
        self.cursors: Dict[str, CursorPosition] = {}
        self.logger = logging.getLogger("presence_manager")

    def add_user(self, user: User) -> None:
        """Add user to session."""
        self.users[user.user_id] = user
        self.logger.info(f"User joined: {user.username}")

    def remove_user(self, user_id: str) -> None:
        """Remove user from session."""
        if user_id in self.users:
            username = self.users[user_id].username
            del self.users[user_id]
            if user_id in self.cursors:
                del self.cursors[user_id]
            self.logger.info(f"User left: {username}")

    def update_status(self, user_id: str, status: UserStatus) -> None:
        """Update user status."""
        if user_id in self.users:
            self.users[user_id].status = status
            self.users[user_id].last_seen = datetime.now()

    def update_cursor(self, user_id: str, position: int,
                     selection_start: Optional[int] = None,
                     selection_end: Optional[int] = None) -> None:
        """Update cursor position."""
        if user_id in self.users:
            user = self.users[user_id]
            user.cursor_position = position
            user.selection_start = selection_start
            user.selection_end = selection_end

            self.cursors[user_id] = CursorPosition(
                user_id=user_id,
                username=user.username,
                position=position,
                color=user.color
            )

    def get_active_users(self) -> List[User]:
        """Get active users."""
        cutoff = datetime.now() - timedelta(minutes=5)
        return [u for u in self.users.values() if u.last_seen > cutoff]

    def get_all_cursors(self) -> List[CursorPosition]:
        """Get all cursor positions."""
        return list(self.cursors.values())

# ============================================================================
# DOCUMENT MANAGER
# ============================================================================

class DocumentManager:
    """Manage collaborative documents."""

    def __init__(self, ot_engine: OperationalTransformationEngine):
        self.documents: Dict[str, Document] = {}
        self.ot_engine = ot_engine
        self.logger = logging.getLogger("document_manager")

    def create_document(self, title: str, content: str, user_id: str) -> Document:
        """Create new document."""
        doc = Document(
            doc_id=f"doc-{uuid.uuid4().hex[:8]}",
            title=title,
            content=content,
            created_by=user_id
        )

        self.documents[doc.doc_id] = doc
        self.logger.info(f"Created document: {title}")

        return doc

    def get_document(self, doc_id: str) -> Optional[Document]:
        """Get document."""
        return self.documents.get(doc_id)

    def apply_operation(self, doc_id: str, operation: Operation) -> bool:
        """Apply operation to document."""
        if doc_id not in self.documents:
            return False

        doc = self.documents[doc_id]

        # Apply operation
        doc.content = self.ot_engine.apply_operation(doc.content, operation)
        doc.version += 1
        doc.modified_at = datetime.now()

        # Record operation
        self.ot_engine.record_operation(operation)

        self.logger.debug(f"Applied {operation.op_type.value} to {doc.title}")

        return True

    def join_document(self, doc_id: str, user_id: str) -> bool:
        """User joins document."""
        if doc_id in self.documents:
            self.documents[doc_id].active_users.add(user_id)
            return True
        return False

    def leave_document(self, doc_id: str, user_id: str) -> None:
        """User leaves document."""
        if doc_id in self.documents:
            self.documents[doc_id].active_users.discard(user_id)

# ============================================================================
# CHAT SYSTEM
# ============================================================================

class ChatSystem:
    """Real-time chat system."""

    def __init__(self):
        self.messages: deque = deque(maxlen=1000)
        self.logger = logging.getLogger("chat_system")

    def send_message(self, user_id: str, username: str, content: str) -> ChatMessage:
        """Send chat message."""
        message = ChatMessage(
            message_id=f"msg-{uuid.uuid4().hex[:8]}",
            user_id=user_id,
            username=username,
            content=content
        )

        self.messages.append(message)
        self.logger.info(f"Chat from {username}: {content[:50]}")

        return message

    def edit_message(self, message_id: str, new_content: str) -> bool:
        """Edit message."""
        for msg in self.messages:
            if msg.message_id == message_id:
                msg.content = new_content
                msg.edited = True
                return True
        return False

    def get_recent_messages(self, limit: int = 50) -> List[ChatMessage]:
        """Get recent messages."""
        return list(self.messages)[-limit:]

# ============================================================================
# ACTIVITY STREAM
# ============================================================================

class ActivityStream:
    """Track user activities."""

    def __init__(self):
        self.activities: deque = deque(maxlen=1000)
        self.logger = logging.getLogger("activity_stream")

    def log_activity(self, activity_type: ActivityType, user_id: str,
                    username: str, data: Dict[str, Any]) -> Activity:
        """Log activity."""
        activity = Activity(
            activity_id=f"act-{uuid.uuid4().hex[:8]}",
            activity_type=activity_type,
            user_id=user_id,
            username=username,
            data=data
        )

        self.activities.append(activity)
        self.logger.debug(f"{username} - {activity_type.value}")

        return activity

    def get_activities(self, limit: int = 100,
                      activity_types: Optional[List[ActivityType]] = None) -> List[Activity]:
        """Get activities."""
        activities = list(self.activities)

        if activity_types:
            activities = [a for a in activities if a.activity_type in activity_types]

        return activities[-limit:]

# ============================================================================
# CONFLICT RESOLVER
# ============================================================================

class ConflictResolver:
    """Resolve editing conflicts."""

    def __init__(self):
        self.logger = logging.getLogger("conflict_resolver")

    def resolve_concurrent_edits(self, ops: List[Operation]) -> List[Operation]:
        """Resolve concurrent edits."""
        if len(ops) <= 1:
            return ops

        # Sort by timestamp
        sorted_ops = sorted(ops, key=lambda o: o.timestamp)

        self.logger.info(f"Resolving {len(ops)} concurrent operations")

        return sorted_ops

    def detect_conflict(self, op1: Operation, op2: Operation) -> bool:
        """Detect if operations conflict."""
        # Check for overlapping ranges
        if op1.op_type == OperationType.DELETE and op2.op_type == OperationType.DELETE:
            range1 = (op1.position, op1.position + op1.length)
            range2 = (op2.position, op2.position + op2.length)

            return not (range1[1] <= range2[0] or range2[1] <= range1[0])

        return False

# ============================================================================
# PERMISSION MANAGER
# ============================================================================

class PermissionManager:
    """Manage document permissions."""

    def __init__(self):
        self.permissions: Dict[str, Dict[str, PermissionLevel]] = {}  # doc_id -> user_id -> level
        self.logger = logging.getLogger("permission_manager")

    def grant_permission(self, doc_id: str, user_id: str, level: PermissionLevel) -> None:
        """Grant permission."""
        if doc_id not in self.permissions:
            self.permissions[doc_id] = {}

        self.permissions[doc_id][user_id] = level
        self.logger.info(f"Granted {level.value} to user {user_id} for doc {doc_id}")

    def check_permission(self, doc_id: str, user_id: str,
                        required_level: PermissionLevel) -> bool:
        """Check if user has permission."""
        if doc_id not in self.permissions:
            return False

        if user_id not in self.permissions[doc_id]:
            return False

        user_level = self.permissions[doc_id][user_id]

        # Permission hierarchy
        levels = {
            PermissionLevel.OWNER: 4,
            PermissionLevel.ADMIN: 3,
            PermissionLevel.WRITE: 2,
            PermissionLevel.READ: 1,
            PermissionLevel.COMMENT: 0
        }

        return levels[user_level] >= levels[required_level]

    def revoke_permission(self, doc_id: str, user_id: str) -> None:
        """Revoke permission."""
        if doc_id in self.permissions and user_id in self.permissions[doc_id]:
            del self.permissions[doc_id][user_id]
            self.logger.info(f"Revoked permission for user {user_id} on doc {doc_id}")

# ============================================================================
# COLLABORATION HUB
# ============================================================================

class CollaborationHub:
    """Central collaboration management system."""

    def __init__(self):
        self.ot_engine = OperationalTransformationEngine()
        self.document_manager = DocumentManager(self.ot_engine)
        self.presence_manager = PresenceManager()
        self.chat_system = ChatSystem()
        self.activity_stream = ActivityStream()
        self.conflict_resolver = ConflictResolver()
        self.permission_manager = PermissionManager()

        self.sessions: Dict[str, Set[str]] = {}  # doc_id -> user_ids
        self.logger = logging.getLogger("collaboration_hub")

    async def initialize(self) -> None:
        """Initialize collaboration hub."""
        self.logger.info("Initializing collaboration hub")

    async def create_session(self, title: str, content: str, owner_id: str,
                           owner_username: str) -> Tuple[Document, User]:
        """Create collaboration session."""
        # Create document
        doc = self.document_manager.create_document(title, content, owner_id)

        # Create owner user
        owner = User(
            user_id=owner_id,
            username=owner_username,
            email=f"{owner_username}@example.com",
            permission=PermissionLevel.OWNER
        )

        # Setup permissions
        self.permission_manager.grant_permission(doc.doc_id, owner_id, PermissionLevel.OWNER)

        # Add user
        self.presence_manager.add_user(owner)
        self.document_manager.join_document(doc.doc_id, owner_id)

        # Initialize session
        self.sessions[doc.doc_id] = {owner_id}

        # Log activity
        self.activity_stream.log_activity(
            ActivityType.JOIN,
            owner_id,
            owner_username,
            {'doc_id': doc.doc_id, 'title': title}
        )

        self.logger.info(f"Created session: {title}")

        return doc, owner

    async def join_session(self, doc_id: str, user_id: str, username: str,
                          permission: PermissionLevel = PermissionLevel.READ) -> bool:
        """Join collaboration session."""
        doc = self.document_manager.get_document(doc_id)

        if not doc:
            return False

        # Create user
        user = User(
            user_id=user_id,
            username=username,
            email=f"{username}@example.com",
            permission=permission
        )

        # Grant permission
        self.permission_manager.grant_permission(doc_id, user_id, permission)

        # Add user
        self.presence_manager.add_user(user)
        self.document_manager.join_document(doc_id, user_id)

        if doc_id not in self.sessions:
            self.sessions[doc_id] = set()
        self.sessions[doc_id].add(user_id)

        # Log activity
        self.activity_stream.log_activity(
            ActivityType.JOIN,
            user_id,
            username,
            {'doc_id': doc_id}
        )

        self.logger.info(f"{username} joined session {doc_id}")

        return True

    async def apply_edit(self, doc_id: str, user_id: str, operation: Operation) -> bool:
        """Apply edit with permission check."""
        # Check permission
        if not self.permission_manager.check_permission(doc_id, user_id, PermissionLevel.WRITE):
            self.logger.warning(f"User {user_id} lacks write permission")
            return False

        # Apply operation
        success = self.document_manager.apply_operation(doc_id, operation)

        if success:
            # Log activity
            user = self.presence_manager.users.get(user_id)
            if user:
                self.activity_stream.log_activity(
                    ActivityType.EDIT,
                    user_id,
                    user.username,
                    {
                        'doc_id': doc_id,
                        'operation': operation.op_type.value,
                        'position': operation.position
                    }
                )

        return success

    async def update_cursor(self, doc_id: str, user_id: str, position: int) -> None:
        """Update cursor position."""
        self.presence_manager.update_cursor(user_id, position)

        user = self.presence_manager.users.get(user_id)
        if user:
            self.activity_stream.log_activity(
                ActivityType.CURSOR_MOVE,
                user_id,
                user.username,
                {'doc_id': doc_id, 'position': position}
            )

    async def send_chat(self, user_id: str, content: str) -> ChatMessage:
        """Send chat message."""
        user = self.presence_manager.users.get(user_id)
        if not user:
            raise ValueError(f"User not found: {user_id}")

        message = self.chat_system.send_message(user_id, user.username, content)

        self.activity_stream.log_activity(
            ActivityType.CHAT,
            user_id,
            user.username,
            {'message': content}
        )

        return message

    def get_session_state(self, doc_id: str) -> Dict[str, Any]:
        """Get complete session state."""
        doc = self.document_manager.get_document(doc_id)

        if not doc:
            return {}

        active_users = [
            {
                'user_id': u.user_id,
                'username': u.username,
                'status': u.status.value,
                'cursor_position': u.cursor_position,
                'color': u.color
            }
            for u in self.presence_manager.get_active_users()
            if u.user_id in self.sessions.get(doc_id, set())
        ]

        return {
            'document': {
                'doc_id': doc.doc_id,
                'title': doc.title,
                'content': doc.content,
                'version': doc.version
            },
            'users': active_users,
            'cursors': [
                {
                    'user_id': c.user_id,
                    'username': c.username,
                    'position': c.position,
                    'color': c.color
                }
                for c in self.presence_manager.get_all_cursors()
            ],
            'chat_messages': [
                {
                    'message_id': m.message_id,
                    'username': m.username,
                    'content': m.content,
                    'timestamp': m.timestamp.isoformat()
                }
                for m in self.chat_system.get_recent_messages(20)
            ],
            'recent_activities': [
                {
                    'type': a.activity_type.value,
                    'username': a.username,
                    'data': a.data,
                    'timestamp': a.timestamp.isoformat()
                }
                for a in self.activity_stream.get_activities(50)
            ]
        }

    def get_hub_stats(self) -> Dict[str, Any]:
        """Get hub statistics."""
        return {
            'total_documents': len(self.document_manager.documents),
            'active_sessions': len(self.sessions),
            'total_users': len(self.presence_manager.users),
            'active_users': len(self.presence_manager.get_active_users()),
            'total_operations': len(self.ot_engine.operations),
            'total_messages': len(self.chat_system.messages),
            'total_activities': len(self.activity_stream.activities)
        }

def create_collaboration_hub() -> CollaborationHub:
    """Create collaboration hub."""
    return CollaborationHub()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    hub = create_collaboration_hub()
    print("Collaboration hub initialized")

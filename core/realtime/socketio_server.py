"""
Socket.IO server implementation for real-time communication.

Features:
- Connection management with authentication
- Room-based messaging and broadcasting
- Heartbeat monitoring
- Event handling and routing
- Redis adapter for multi-node scaling
- Compression support
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Set

import jwt
import socketio

logger = logging.getLogger(__name__)


@dataclass
class Connection:
    """Represents an active WebSocket connection."""
    sid: str
    user_id: str
    authenticated: bool = False
    connected_at: datetime = field(default_factory=datetime.now)
    last_heartbeat: datetime = field(default_factory=datetime.now)
    rooms: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ConnectionManager:
    """Manages active WebSocket connections."""

    def __init__(self):
        self.connections: Dict[str, Connection] = {}
        self._lock = asyncio.Lock()

    async def add_connection(
        self,
        sid: str,
        user_id: str,
        authenticated: bool = False,
        metadata: Optional[Dict] = None
    ) -> Connection:
        """Add a new connection."""
        async with self._lock:
            conn = Connection(
                sid=sid,
                user_id=user_id,
                authenticated=authenticated,
                metadata=metadata or {}
            )
            self.connections[sid] = conn
            logger.info(f"Connection added: {sid} (user: {user_id})")
            return conn

    async def remove_connection(self, sid: str) -> Optional[Connection]:
        """Remove a connection."""
        async with self._lock:
            conn = self.connections.pop(sid, None)
            if conn:
                logger.info(f"Connection removed: {sid}")
            return conn

    async def get_connection(self, sid: str) -> Optional[Connection]:
        """Get connection by session ID."""
        return self.connections.get(sid)

    async def update_heartbeat(self, sid: str):
        """Update last heartbeat time for a connection."""
        conn = await self.get_connection(sid)
        if conn:
            conn.last_heartbeat = datetime.now()

    async def get_stale_connections(self, timeout_seconds: int = 60) -> List[Connection]:
        """Get connections that haven't sent heartbeat recently."""
        cutoff = datetime.now() - timedelta(seconds=timeout_seconds)
        return [
            conn for conn in self.connections.values()
            if conn.last_heartbeat < cutoff
        ]

    async def get_user_connections(self, user_id: str) -> List[Connection]:
        """Get all connections for a specific user."""
        return [
            conn for conn in self.connections.values()
            if conn.user_id == user_id
        ]

    async def get_room_connections(self, room: str) -> List[Connection]:
        """Get all connections in a specific room."""
        return [
            conn for conn in self.connections.values()
            if room in conn.rooms
        ]

    def get_stats(self) -> Dict[str, Any]:
        """Get connection statistics."""
        total = len(self.connections)
        authenticated = sum(1 for c in self.connections.values() if c.authenticated)

        return {
            "total_connections": total,
            "authenticated_connections": authenticated,
            "unauthenticated_connections": total - authenticated,
            "unique_users": len(set(c.user_id for c in self.connections.values())),
        }


class RoomManager:
    """Manages Socket.IO rooms for organized messaging."""

    def __init__(self, sio: socketio.AsyncServer):
        self.sio = sio
        self.rooms: Dict[str, Set[str]] = {}
        self._lock = asyncio.Lock()

    async def join_room(self, sid: str, room: str):
        """Add a connection to a room."""
        async with self._lock:
            await self.sio.enter_room(sid, room)
            if room not in self.rooms:
                self.rooms[room] = set()
            self.rooms[room].add(sid)
            logger.info(f"Connection {sid} joined room {room}")

    async def leave_room(self, sid: str, room: str):
        """Remove a connection from a room."""
        async with self._lock:
            await self.sio.leave_room(sid, room)
            if room in self.rooms:
                self.rooms[room].discard(sid)
                if not self.rooms[room]:
                    del self.rooms[room]
            logger.info(f"Connection {sid} left room {room}")

    async def leave_all_rooms(self, sid: str):
        """Remove a connection from all rooms."""
        async with self._lock:
            for room in list(self.rooms.keys()):
                if sid in self.rooms[room]:
                    await self.sio.leave_room(sid, room)
                    self.rooms[room].discard(sid)
                    if not self.rooms[room]:
                        del self.rooms[room]

    async def get_room_members(self, room: str) -> Set[str]:
        """Get all session IDs in a room."""
        return self.rooms.get(room, set()).copy()

    async def get_user_rooms(self, sid: str) -> List[str]:
        """Get all rooms a connection is in."""
        return [
            room for room, members in self.rooms.items()
            if sid in members
        ]

    def get_stats(self) -> Dict[str, Any]:
        """Get room statistics."""
        return {
            "total_rooms": len(self.rooms),
            "room_details": {
                room: len(members)
                for room, members in self.rooms.items()
            }
        }


class SocketIOServer:
    """Main Socket.IO server for real-time communication."""

    def __init__(
        self,
        secret_key: str,
        cors_allowed_origins: str = "*",
        enable_redis: bool = False,
        redis_url: str = "redis://localhost:6379",
        heartbeat_interval: int = 30,
        heartbeat_timeout: int = 60
    ):
        """
        Initialize Socket.IO server.

        Args:
            secret_key: JWT secret key for authentication
            cors_allowed_origins: CORS allowed origins
            enable_redis: Enable Redis adapter for multi-node
            redis_url: Redis connection URL
            heartbeat_interval: Heartbeat interval in seconds
            heartbeat_timeout: Heartbeat timeout in seconds
        """
        self.secret_key = secret_key
        self.heartbeat_interval = heartbeat_interval
        self.heartbeat_timeout = heartbeat_timeout

        # Create Socket.IO server with compression
        self.sio = socketio.AsyncServer(
            async_mode='asgi',
            cors_allowed_origins=cors_allowed_origins,
            logger=logger,
            engineio_logger=False,
            compression_threshold=1024,  # Compress messages > 1KB
        )

        # Set up Redis adapter if enabled
        if enable_redis:
            import aioredis
            self.sio.attach(socketio.AsyncRedisManager(redis_url))
            logger.info(f"Redis adapter enabled: {redis_url}")

        # Initialize managers
        self.connection_manager = ConnectionManager()
        self.room_manager = RoomManager(self.sio)

        # Event handlers
        self.event_handlers: Dict[str, Callable] = {}

        # Set up default event handlers
        self._setup_handlers()

        # Background tasks
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None

    def _setup_handlers(self):
        """Set up default Socket.IO event handlers."""

        @self.sio.event
        async def connect(sid, environ, auth):
            """Handle client connection."""
            logger.info(f"Client connecting: {sid}")

            # Authenticate via JWT token
            token = auth.get('token') if auth else None
            user_id = "anonymous"
            authenticated = False

            if token:
                try:
                    payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
                    user_id = payload.get('user_id', 'anonymous')
                    authenticated = True
                    logger.info(f"Authenticated user: {user_id}")
                except jwt.InvalidTokenError as e:
                    logger.warning(f"Invalid token: {e}")

            # Add connection
            await self.connection_manager.add_connection(
                sid=sid,
                user_id=user_id,
                authenticated=authenticated,
                metadata={"environ": environ}
            )

            # Send connection confirmation
            await self.sio.emit('connected', {
                'sid': sid,
                'user_id': user_id,
                'authenticated': authenticated,
                'timestamp': datetime.now().isoformat()
            }, room=sid)

        @self.sio.event
        async def disconnect(sid):
            """Handle client disconnection."""
            logger.info(f"Client disconnecting: {sid}")

            # Leave all rooms
            await self.room_manager.leave_all_rooms(sid)

            # Remove connection
            await self.connection_manager.remove_connection(sid)

        @self.sio.event
        async def heartbeat(sid):
            """Handle heartbeat from client."""
            await self.connection_manager.update_heartbeat(sid)
            await self.sio.emit('heartbeat_ack', {'timestamp': datetime.now().isoformat()}, room=sid)

        @self.sio.event
        async def join_room(sid, data):
            """Handle join room request."""
            room = data.get('room')
            if not room:
                await self.sio.emit('error', {'message': 'Room name required'}, room=sid)
                return

            conn = await self.connection_manager.get_connection(sid)
            if conn:
                await self.room_manager.join_room(sid, room)
                conn.rooms.add(room)
                await self.sio.emit('room_joined', {'room': room}, room=sid)

                # Notify room members
                await self.sio.emit('user_joined', {
                    'user_id': conn.user_id,
                    'room': room
                }, room=room, skip_sid=sid)

        @self.sio.event
        async def leave_room(sid, data):
            """Handle leave room request."""
            room = data.get('room')
            if not room:
                await self.sio.emit('error', {'message': 'Room name required'}, room=sid)
                return

            conn = await self.connection_manager.get_connection(sid)
            if conn:
                await self.room_manager.leave_room(sid, room)
                conn.rooms.discard(room)
                await self.sio.emit('room_left', {'room': room}, room=sid)

                # Notify room members
                await self.sio.emit('user_left', {
                    'user_id': conn.user_id,
                    'room': room
                }, room=room)

        @self.sio.event
        async def message(sid, data):
            """Handle generic message event."""
            await self._handle_event('message', sid, data)

    def on(self, event: str):
        """Decorator to register custom event handlers."""
        def decorator(func: Callable):
            self.event_handlers[event] = func

            @self.sio.event
            async def handler(sid, data):
                await self._handle_event(event, sid, data)

            return func
        return decorator

    async def _handle_event(self, event: str, sid: str, data: Any):
        """Handle custom event."""
        conn = await self.connection_manager.get_connection(sid)
        if not conn:
            logger.warning(f"Event from unknown connection: {sid}")
            return

        # Call registered handler
        handler = self.event_handlers.get(event)
        if handler:
            try:
                await handler(sid, conn, data)
            except Exception as e:
                logger.error(f"Error in event handler {event}: {e}")
                await self.sio.emit('error', {
                    'event': event,
                    'message': str(e)
                }, room=sid)

    async def emit_to_user(self, user_id: str, event: str, data: Any):
        """Emit event to all connections of a user."""
        connections = await self.connection_manager.get_user_connections(user_id)
        for conn in connections:
            await self.sio.emit(event, data, room=conn.sid)

    async def emit_to_room(self, room: str, event: str, data: Any, skip_sid: Optional[str] = None):
        """Emit event to all connections in a room."""
        await self.sio.emit(event, data, room=room, skip_sid=skip_sid)

    async def broadcast(self, event: str, data: Any):
        """Broadcast event to all connected clients."""
        await self.sio.emit(event, data)

    async def _heartbeat_monitor(self):
        """Monitor heartbeats and disconnect stale connections."""
        while True:
            try:
                await asyncio.sleep(self.heartbeat_interval)

                # Find stale connections
                stale = await self.connection_manager.get_stale_connections(
                    self.heartbeat_timeout
                )

                # Disconnect stale connections
                for conn in stale:
                    logger.warning(f"Disconnecting stale connection: {conn.sid}")
                    await self.sio.disconnect(conn.sid)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in heartbeat monitor: {e}")

    async def start(self):
        """Start background tasks."""
        logger.info("Starting Socket.IO server background tasks")
        self._heartbeat_task = asyncio.create_task(self._heartbeat_monitor())

    async def stop(self):
        """Stop background tasks."""
        logger.info("Stopping Socket.IO server background tasks")
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass

    def get_asgi_app(self):
        """Get ASGI application for mounting."""
        return socketio.ASGIApp(self.sio)

    def get_stats(self) -> Dict[str, Any]:
        """Get server statistics."""
        return {
            "connections": self.connection_manager.get_stats(),
            "rooms": self.room_manager.get_stats(),
            "heartbeat_interval": self.heartbeat_interval,
            "heartbeat_timeout": self.heartbeat_timeout,
        }


# Example usage
if __name__ == "__main__":
    # Create server
    server = SocketIOServer(
        secret_key="your-secret-key",
        enable_redis=False,
        heartbeat_interval=30
    )

    # Register custom event handlers
    @server.on('chat_message')
    async def handle_chat(sid, conn, data):
        """Handle chat messages."""
        message = data.get('message')
        room = data.get('room', 'general')

        # Broadcast to room
        await server.emit_to_room(room, 'chat_message', {
            'user_id': conn.user_id,
            'message': message,
            'timestamp': datetime.now().isoformat()
        })

    @server.on('task_update')
    async def handle_task_update(sid, conn, data):
        """Handle task progress updates."""
        task_id = data.get('task_id')
        progress = data.get('progress')

        # Emit to user's connections
        await server.emit_to_user(conn.user_id, 'task_progress', {
            'task_id': task_id,
            'progress': progress,
            'timestamp': datetime.now().isoformat()
        })

    print("Socket.IO server configured")

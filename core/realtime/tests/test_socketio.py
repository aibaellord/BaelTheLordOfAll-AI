"""
Tests for Socket.IO real-time communication.
"""

import asyncio
from datetime import datetime, timedelta

import jwt
import pytest

from core.realtime.socketio_server import (Connection, ConnectionManager,
                                           RoomManager, SocketIOServer)


class TestConnectionManager:
    """Test ConnectionManager functionality."""

    @pytest.fixture
    def manager(self):
        return ConnectionManager()

    @pytest.mark.asyncio
    async def test_add_connection(self, manager):
        """Test adding a connection."""
        conn = await manager.add_connection("sid1", "user1", authenticated=True)

        assert conn.sid == "sid1"
        assert conn.user_id == "user1"
        assert conn.authenticated is True
        assert "sid1" in manager.connections

    @pytest.mark.asyncio
    async def test_remove_connection(self, manager):
        """Test removing a connection."""
        await manager.add_connection("sid1", "user1")
        conn = await manager.remove_connection("sid1")

        assert conn is not None
        assert conn.sid == "sid1"
        assert "sid1" not in manager.connections

    @pytest.mark.asyncio
    async def test_get_connection(self, manager):
        """Test getting a connection."""
        await manager.add_connection("sid1", "user1")
        conn = await manager.get_connection("sid1")

        assert conn is not None
        assert conn.sid == "sid1"

    @pytest.mark.asyncio
    async def test_update_heartbeat(self, manager):
        """Test updating heartbeat."""
        await manager.add_connection("sid1", "user1")

        # Wait a bit
        await asyncio.sleep(0.1)

        old_heartbeat = manager.connections["sid1"].last_heartbeat
        await manager.update_heartbeat("sid1")
        new_heartbeat = manager.connections["sid1"].last_heartbeat

        assert new_heartbeat > old_heartbeat

    @pytest.mark.asyncio
    async def test_get_stale_connections(self, manager):
        """Test getting stale connections."""
        # Add connection with old heartbeat
        conn = await manager.add_connection("sid1", "user1")
        conn.last_heartbeat = datetime.now() - timedelta(seconds=120)

        # Add fresh connection
        await manager.add_connection("sid2", "user2")

        stale = await manager.get_stale_connections(timeout_seconds=60)

        assert len(stale) == 1
        assert stale[0].sid == "sid1"

    @pytest.mark.asyncio
    async def test_get_user_connections(self, manager):
        """Test getting user connections."""
        await manager.add_connection("sid1", "user1")
        await manager.add_connection("sid2", "user1")
        await manager.add_connection("sid3", "user2")

        user1_conns = await manager.get_user_connections("user1")

        assert len(user1_conns) == 2
        assert all(c.user_id == "user1" for c in user1_conns)

    def test_get_stats(self, manager):
        """Test getting statistics."""
        asyncio.run(manager.add_connection("sid1", "user1", authenticated=True))
        asyncio.run(manager.add_connection("sid2", "user1", authenticated=False))
        asyncio.run(manager.add_connection("sid3", "user2", authenticated=True))

        stats = manager.get_stats()

        assert stats["total_connections"] == 3
        assert stats["authenticated_connections"] == 2
        assert stats["unauthenticated_connections"] == 1
        assert stats["unique_users"] == 2


class TestSocketIOServer:
    """Test SocketIOServer functionality."""

    @pytest.fixture
    def server(self):
        return SocketIOServer(
            secret_key="test-secret-key",
            enable_redis=False,
            heartbeat_interval=30,
            heartbeat_timeout=60
        )

    def test_initialization(self, server):
        """Test server initialization."""
        assert server.secret_key == "test-secret-key"
        assert server.heartbeat_interval == 30
        assert server.heartbeat_timeout == 60
        assert server.sio is not None
        assert isinstance(server.connection_manager, ConnectionManager)
        assert isinstance(server.room_manager, RoomManager)

    def test_event_handler_registration(self, server):
        """Test custom event handler registration."""

        @server.on('test_event')
        async def handle_test(sid, conn, data):
            return {"success": True}

        assert 'test_event' in server.event_handlers
        assert server.event_handlers['test_event'] == handle_test

    @pytest.mark.asyncio
    async def test_emit_to_user(self, server):
        """Test emitting to user."""
        # Add test connections
        await server.connection_manager.add_connection("sid1", "user1")
        await server.connection_manager.add_connection("sid2", "user1")

        # This would normally emit, but we can't test actual emission without a client
        # Just verify the method doesn't error
        await server.emit_to_user("user1", "test_event", {"message": "test"})

    @pytest.mark.asyncio
    async def test_broadcast(self, server):
        """Test broadcasting."""
        await server.connection_manager.add_connection("sid1", "user1")
        await server.connection_manager.add_connection("sid2", "user2")

        # Verify method doesn't error
        await server.broadcast("test_event", {"message": "broadcast"})

    def test_get_stats(self, server):
        """Test getting server statistics."""
        asyncio.run(server.connection_manager.add_connection("sid1", "user1"))

        stats = server.get_stats()

        assert "connections" in stats
        assert "rooms" in stats
        assert "heartbeat_interval" in stats
        assert stats["heartbeat_interval"] == 30

    def test_get_asgi_app(self, server):
        """Test getting ASGI application."""
        app = server.get_asgi_app()

        assert app is not None

    @pytest.mark.asyncio
    async def test_start_stop(self, server):
        """Test starting and stopping server."""
        await server.start()
        assert server._heartbeat_task is not None

        await server.stop()
        assert server._heartbeat_task.cancelled() or server._heartbeat_task.done()


class TestJWTAuthentication:
    """Test JWT authentication in Socket.IO."""

    def test_generate_token(self):
        """Test generating JWT token."""
        secret_key = "test-secret-key"
        payload = {
            "user_id": "user123",
            "exp": datetime.now() + timedelta(hours=1)
        }

        token = jwt.encode(payload, secret_key, algorithm='HS256')

        assert token is not None
        assert isinstance(token, str)

    def test_decode_token(self):
        """Test decoding JWT token."""
        secret_key = "test-secret-key"
        payload = {
            "user_id": "user123",
            "exp": datetime.now() + timedelta(hours=1)
        }

        token = jwt.encode(payload, secret_key, algorithm='HS256')
        decoded = jwt.decode(token, secret_key, algorithms=['HS256'])

        assert decoded["user_id"] == "user123"

    def test_expired_token(self):
        """Test expired token handling."""
        secret_key = "test-secret-key"
        payload = {
            "user_id": "user123",
            "exp": datetime.now() - timedelta(hours=1)  # Expired
        }

        token = jwt.encode(payload, secret_key, algorithm='HS256')

        with pytest.raises(jwt.ExpiredSignatureError):
            jwt.decode(token, secret_key, algorithms=['HS256'])

    def test_invalid_token(self):
        """Test invalid token handling."""
        secret_key = "test-secret-key"
        wrong_key = "wrong-secret-key"
        payload = {
            "user_id": "user123",
            "exp": datetime.now() + timedelta(hours=1)
        }

        token = jwt.encode(payload, secret_key, algorithm='HS256')

        with pytest.raises(jwt.InvalidTokenError):
            jwt.decode(token, wrong_key, algorithms=['HS256'])


# Integration test example
@pytest.mark.asyncio
async def test_full_connection_lifecycle():
    """Test complete connection lifecycle."""
    server = SocketIOServer(
        secret_key="test-key",
        enable_redis=False
    )

    # Start server
    await server.start()

    # Simulate connection
    sid = "test-sid-123"
    user_id = "test-user"

    await server.connection_manager.add_connection(sid, user_id, authenticated=True)

    # Join rooms
    await server.room_manager.join_room(sid, "general")
    await server.room_manager.join_room(sid, "testing")

    # Update heartbeat
    await server.connection_manager.update_heartbeat(sid)

    # Get stats
    stats = server.get_stats()
    assert stats["connections"]["total_connections"] == 1
    assert stats["rooms"]["total_rooms"] == 2

    # Leave room
    await server.room_manager.leave_room(sid, "testing")

    # Disconnect
    await server.room_manager.leave_all_rooms(sid)
    await server.connection_manager.remove_connection(sid)

    # Verify cleanup
    final_stats = server.get_stats()
    assert final_stats["connections"]["total_connections"] == 0

    # Stop server
    await server.stop()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

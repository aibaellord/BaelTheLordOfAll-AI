"""
FastAPI integration for Socket.IO server.

Provides REST API endpoints for WebSocket management and statistics.
"""

from datetime import datetime
from typing import Any, Dict, Optional

import jwt
from fastapi import APIRouter, Depends, Header, HTTPException

from .socketio_server import SocketIOServer

router = APIRouter(prefix="/realtime", tags=["realtime"])

# Global server instance (set by main app)
_server: Optional[SocketIOServer] = None


def get_server() -> SocketIOServer:
    """Get Socket.IO server instance."""
    if _server is None:
        raise HTTPException(status_code=503, detail="Socket.IO server not initialized")
    return _server


def set_server(server: SocketIOServer):
    """Set global Socket.IO server instance."""
    global _server
    _server = server


@router.get("/stats")
async def get_stats(server: SocketIOServer = Depends(get_server)) -> Dict[str, Any]:
    """
    Get real-time server statistics.

    Returns connection counts, room information, and server metrics.
    """
    return server.get_stats()


@router.get("/connections")
async def get_connections(server: SocketIOServer = Depends(get_server)) -> Dict[str, Any]:
    """Get all active connections."""
    stats = server.connection_manager.get_stats()

    connections = []
    for conn in server.connection_manager.connections.values():
        connections.append({
            "sid": conn.sid,
            "user_id": conn.user_id,
            "authenticated": conn.authenticated,
            "connected_at": conn.connected_at.isoformat(),
            "last_heartbeat": conn.last_heartbeat.isoformat(),
            "rooms": list(conn.rooms),
        })

    return {
        "stats": stats,
        "connections": connections
    }


@router.get("/connections/{user_id}")
async def get_user_connections(
    user_id: str,
    server: SocketIOServer = Depends(get_server)
) -> Dict[str, Any]:
    """Get all connections for a specific user."""
    connections = await server.connection_manager.get_user_connections(user_id)

    return {
        "user_id": user_id,
        "connection_count": len(connections),
        "connections": [
            {
                "sid": conn.sid,
                "authenticated": conn.authenticated,
                "connected_at": conn.connected_at.isoformat(),
                "rooms": list(conn.rooms),
            }
            for conn in connections
        ]
    }


@router.get("/rooms")
async def get_rooms(server: SocketIOServer = Depends(get_server)) -> Dict[str, Any]:
    """Get all active rooms and their members."""
    stats = server.room_manager.get_stats()

    rooms = []
    for room, members in server.room_manager.rooms.items():
        rooms.append({
            "room": room,
            "member_count": len(members),
            "members": list(members),
        })

    return {
        "stats": stats,
        "rooms": rooms
    }


@router.get("/rooms/{room_name}")
async def get_room_details(
    room_name: str,
    server: SocketIOServer = Depends(get_server)
) -> Dict[str, Any]:
    """Get details about a specific room."""
    members = await server.room_manager.get_room_members(room_name)

    if not members:
        raise HTTPException(status_code=404, detail=f"Room '{room_name}' not found")

    # Get connection details for members
    connections = []
    for sid in members:
        conn = await server.connection_manager.get_connection(sid)
        if conn:
            connections.append({
                "sid": conn.sid,
                "user_id": conn.user_id,
                "authenticated": conn.authenticated,
            })

    return {
        "room": room_name,
        "member_count": len(members),
        "connections": connections
    }


@router.post("/broadcast")
async def broadcast_event(
    event: str,
    data: Dict[str, Any],
    server: SocketIOServer = Depends(get_server)
):
    """
    Broadcast an event to all connected clients.

    Args:
        event: Event name
        data: Event data
    """
    await server.broadcast(event, data)

    return {
        "success": True,
        "event": event,
        "broadcast_to": "all",
        "timestamp": datetime.now().isoformat()
    }


@router.post("/emit/user/{user_id}")
async def emit_to_user(
    user_id: str,
    event: str,
    data: Dict[str, Any],
    server: SocketIOServer = Depends(get_server)
):
    """
    Emit an event to all connections of a specific user.

    Args:
        user_id: Target user ID
        event: Event name
        data: Event data
    """
    connections = await server.connection_manager.get_user_connections(user_id)

    if not connections:
        raise HTTPException(status_code=404, detail=f"No connections found for user '{user_id}'")

    await server.emit_to_user(user_id, event, data)

    return {
        "success": True,
        "event": event,
        "user_id": user_id,
        "connection_count": len(connections),
        "timestamp": datetime.now().isoformat()
    }


@router.post("/emit/room/{room_name}")
async def emit_to_room(
    room_name: str,
    event: str,
    data: Dict[str, Any],
    skip_sid: Optional[str] = None,
    server: SocketIOServer = Depends(get_server)
):
    """
    Emit an event to all connections in a room.

    Args:
        room_name: Target room name
        event: Event name
        data: Event data
        skip_sid: Optional session ID to skip
    """
    members = await server.room_manager.get_room_members(room_name)

    if not members:
        raise HTTPException(status_code=404, detail=f"Room '{room_name}' not found")

    await server.emit_to_room(room_name, event, data, skip_sid=skip_sid)

    return {
        "success": True,
        "event": event,
        "room": room_name,
        "member_count": len(members),
        "timestamp": datetime.now().isoformat()
    }


@router.delete("/connections/{sid}")
async def disconnect_client(
    sid: str,
    server: SocketIOServer = Depends(get_server)
):
    """
    Forcefully disconnect a client.

    Args:
        sid: Session ID to disconnect
    """
    conn = await server.connection_manager.get_connection(sid)

    if not conn:
        raise HTTPException(status_code=404, detail=f"Connection '{sid}' not found")

    await server.sio.disconnect(sid)

    return {
        "success": True,
        "sid": sid,
        "user_id": conn.user_id,
        "timestamp": datetime.now().isoformat()
    }


@router.get("/health")
async def health_check(server: SocketIOServer = Depends(get_server)):
    """Health check endpoint for real-time server."""
    stats = server.get_stats()

    return {
        "status": "healthy",
        "connections": stats["connections"]["total_connections"],
        "rooms": stats["rooms"]["total_rooms"],
        "timestamp": datetime.now().isoformat()
    }

"""
Real-time communication module for BAEL.

Provides WebSocket support via Socket.IO for real-time bidirectional communication.
"""

from .socketio_server import ConnectionManager, RoomManager, SocketIOServer

__all__ = ['SocketIOServer', 'ConnectionManager', 'RoomManager']

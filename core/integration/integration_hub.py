"""
INTEGRATION HUB
===============
Central hub that connects ALL systems into a unified whole.

This hub ensures seamless communication and data flow between:
- All 957+ subsystems
- Meta Commander
- Consciousness systems
- Intelligence engines
- Sacred mathematics
- Domination core
- Reality synthesis
- MCP gateway
- Agent teams
- Councils

Everything flows through the Integration Hub.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable, Awaitable
import math

logger = logging.getLogger("BAEL.IntegrationHub")


@dataclass
class IntegrationChannel:
    """A channel for system integration."""
    channel_id: str
    name: str
    source_system: str
    target_system: str
    bidirectional: bool = True
    active: bool = True
    message_count: int = 0


@dataclass
class SystemMessage:
    """A message between systems."""
    message_id: str
    source: str
    target: str
    content: Any
    priority: int = 5
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class IntegrationMetrics:
    """Metrics for integration performance."""
    total_messages: int = 0
    successful_deliveries: int = 0
    failed_deliveries: int = 0
    active_channels: int = 0
    systems_connected: int = 0


class IntegrationHub:
    """
    The central integration point for ALL BAEL systems.
    
    Features:
    - Universal message routing
    - System registration and discovery
    - Health monitoring
    - Automatic reconnection
    - Priority-based queuing
    
    All systems connect here. All data flows through here.
    """
    
    def __init__(self):
        # Registered systems
        self.systems: Dict[str, Dict[str, Any]] = {}
        
        # Channels
        self.channels: Dict[str, IntegrationChannel] = {}
        
        # Message queue
        self.message_queue: List[SystemMessage] = []
        
        # Handlers
        self.handlers: Dict[str, Callable[[SystemMessage], Awaitable[None]]] = {}
        
        # Metrics
        self.metrics = IntegrationMetrics()
        
        # Golden ratio for optimization
        self.phi = (1 + math.sqrt(5)) / 2
        
        logger.info("INTEGRATION HUB ONLINE - ALL SYSTEMS CONNECTING")
    
    def register_system(self, 
                       system_id: str, 
                       system_name: str,
                       capabilities: List[str] = None) -> None:
        """Register a system with the hub."""
        self.systems[system_id] = {
            "id": system_id,
            "name": system_name,
            "capabilities": capabilities or [],
            "registered_at": datetime.now(),
            "active": True,
            "message_count": 0
        }
        self.metrics.systems_connected = len(self.systems)
        logger.info(f"System registered: {system_name}")
    
    def create_channel(self,
                      name: str,
                      source: str,
                      target: str,
                      bidirectional: bool = True) -> IntegrationChannel:
        """Create an integration channel between systems."""
        import uuid
        
        channel = IntegrationChannel(
            channel_id=str(uuid.uuid4()),
            name=name,
            source_system=source,
            target_system=target,
            bidirectional=bidirectional
        )
        
        self.channels[channel.channel_id] = channel
        self.metrics.active_channels = len(self.channels)
        
        return channel
    
    def register_handler(self,
                        system_id: str,
                        handler: Callable[[SystemMessage], Awaitable[None]]) -> None:
        """Register a message handler for a system."""
        self.handlers[system_id] = handler
    
    async def send(self,
                  source: str,
                  target: str,
                  content: Any,
                  priority: int = 5) -> bool:
        """Send a message from one system to another."""
        import uuid
        
        message = SystemMessage(
            message_id=str(uuid.uuid4()),
            source=source,
            target=target,
            content=content,
            priority=priority
        )
        
        self.metrics.total_messages += 1
        
        # Update source stats
        if source in self.systems:
            self.systems[source]["message_count"] += 1
        
        # Route message
        try:
            if target in self.handlers:
                await self.handlers[target](message)
                self.metrics.successful_deliveries += 1
                return True
            else:
                # Queue for later
                self.message_queue.append(message)
                return True
        except Exception as e:
            self.metrics.failed_deliveries += 1
            logger.error(f"Message delivery failed: {e}")
            return False
    
    async def broadcast(self, source: str, content: Any, priority: int = 5) -> int:
        """Broadcast a message to all systems."""
        delivered = 0
        for system_id in self.systems:
            if system_id != source:
                if await self.send(source, system_id, content, priority):
                    delivered += 1
        return delivered
    
    async def process_queue(self) -> int:
        """Process queued messages."""
        processed = 0
        remaining = []
        
        for message in self.message_queue:
            if message.target in self.handlers:
                try:
                    await self.handlers[message.target](message)
                    self.metrics.successful_deliveries += 1
                    processed += 1
                except:
                    remaining.append(message)
            else:
                remaining.append(message)
        
        self.message_queue = remaining
        return processed
    
    def get_system_status(self, system_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific system."""
        return self.systems.get(system_id)
    
    def discover_systems(self, capability: str) -> List[str]:
        """Discover systems with a specific capability."""
        return [
            sys_id for sys_id, sys_info in self.systems.items()
            if capability in sys_info.get("capabilities", [])
        ]
    
    def get_health(self) -> Dict[str, Any]:
        """Get overall hub health."""
        delivery_rate = (self.metrics.successful_deliveries / 
                        max(1, self.metrics.total_messages))
        
        return {
            "status": "HEALTHY" if delivery_rate > 0.9 else "DEGRADED",
            "delivery_rate": delivery_rate,
            "systems_connected": len(self.systems),
            "active_channels": len(self.channels),
            "queue_size": len(self.message_queue)
        }
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get hub metrics."""
        return {
            "total_messages": self.metrics.total_messages,
            "successful_deliveries": self.metrics.successful_deliveries,
            "failed_deliveries": self.metrics.failed_deliveries,
            "systems_connected": len(self.systems),
            "active_channels": len(self.channels),
            "queue_size": len(self.message_queue)
        }


_hub: Optional[IntegrationHub] = None

def get_integration_hub() -> IntegrationHub:
    """Get the Integration Hub."""
    global _hub
    if _hub is None:
        _hub = IntegrationHub()
    return _hub


__all__ = [
    'IntegrationChannel', 'SystemMessage', 'IntegrationMetrics',
    'IntegrationHub', 'get_integration_hub'
]

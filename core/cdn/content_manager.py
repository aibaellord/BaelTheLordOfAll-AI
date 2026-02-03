#!/usr/bin/env python3
"""
BAEL - Content Delivery Manager
Comprehensive CDN-like content management and delivery system.

Features:
- Content caching
- Edge node simulation
- Content versioning
- Cache invalidation
- Content compression
- ETags and conditional requests
- Range requests
- Content transformation
- Origin failover
- Analytics
"""

import asyncio
import gzip
import hashlib
import json
import logging
import mimetypes
import time
import uuid
import zlib
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import (Any, Awaitable, Callable, Dict, Generic, List, Optional,
                    Set, Tuple, TypeVar, Union)

logger = logging.getLogger(__name__)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class CacheStatus(Enum):
    """Cache status."""
    HIT = "hit"
    MISS = "miss"
    STALE = "stale"
    EXPIRED = "expired"
    BYPASS = "bypass"


class ContentType(Enum):
    """Content types."""
    HTML = "text/html"
    CSS = "text/css"
    JAVASCRIPT = "application/javascript"
    JSON = "application/json"
    IMAGE = "image/*"
    VIDEO = "video/*"
    AUDIO = "audio/*"
    BINARY = "application/octet-stream"


class CompressionType(Enum):
    """Compression types."""
    NONE = "none"
    GZIP = "gzip"
    DEFLATE = "deflate"
    BROTLI = "br"


class EdgeNodeStatus(Enum):
    """Edge node status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    OFFLINE = "offline"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class ContentMetadata:
    """Content metadata."""
    content_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    path: str = ""
    content_type: str = "application/octet-stream"
    size: int = 0
    etag: str = ""
    last_modified: float = field(default_factory=time.time)
    cache_control: str = "public, max-age=3600"
    version: int = 1
    encoding: CompressionType = CompressionType.NONE
    headers: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CachedContent:
    """Cached content entry."""
    metadata: ContentMetadata
    content: bytes = b""
    cached_at: float = field(default_factory=time.time)
    expires_at: float = 0.0
    hit_count: int = 0
    last_accessed: float = field(default_factory=time.time)

    @property
    def is_expired(self) -> bool:
        return time.time() > self.expires_at if self.expires_at > 0 else False

    def touch(self) -> None:
        self.hit_count += 1
        self.last_accessed = time.time()


@dataclass
class ContentRequest:
    """Content delivery request."""
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    path: str = ""
    method: str = "GET"
    headers: Dict[str, str] = field(default_factory=dict)
    query_params: Dict[str, str] = field(default_factory=dict)
    client_ip: str = ""
    accept_encoding: str = ""
    if_none_match: str = ""
    if_modified_since: float = 0.0
    range_start: int = 0
    range_end: int = 0

    def accepts_gzip(self) -> bool:
        return "gzip" in self.accept_encoding

    def is_conditional(self) -> bool:
        return bool(self.if_none_match or self.if_modified_since)

    def is_range_request(self) -> bool:
        return self.range_start > 0 or self.range_end > 0


@dataclass
class ContentResponse:
    """Content delivery response."""
    status_code: int = 200
    content: bytes = b""
    headers: Dict[str, str] = field(default_factory=dict)
    metadata: ContentMetadata = None
    cache_status: CacheStatus = CacheStatus.MISS
    served_by: str = ""
    response_time: float = 0.0


@dataclass
class EdgeNode:
    """Edge node (PoP)."""
    node_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    region: str = ""
    location: str = ""
    status: EdgeNodeStatus = EdgeNodeStatus.HEALTHY
    capacity: int = 1000  # MB
    used: int = 0  # MB
    cache: Dict[str, CachedContent] = field(default_factory=dict)
    stats: Dict[str, int] = field(default_factory=lambda: defaultdict(int))

    @property
    def utilization(self) -> float:
        return (self.used / self.capacity) * 100 if self.capacity > 0 else 0.0


@dataclass
class OriginServer:
    """Origin server."""
    origin_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    host: str = ""
    port: int = 443
    protocol: str = "https"
    priority: int = 1
    healthy: bool = True
    content: Dict[str, bytes] = field(default_factory=dict)  # Simulated content

    @property
    def url(self) -> str:
        return f"{self.protocol}://{self.host}:{self.port}"


@dataclass
class DeliveryStats:
    """Content delivery statistics."""
    total_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    bytes_served: int = 0
    bytes_saved: int = 0
    avg_response_time: float = 0.0
    requests_by_type: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    requests_by_region: Dict[str, int] = field(default_factory=lambda: defaultdict(int))


# =============================================================================
# CACHE POLICY
# =============================================================================

class CachePolicy:
    """Cache policy configuration."""

    def __init__(self):
        self.default_ttl = 3600  # 1 hour
        self.max_ttl = 86400  # 24 hours
        self.min_ttl = 60  # 1 minute
        self.type_ttls: Dict[str, int] = {
            "text/html": 300,
            "text/css": 86400,
            "application/javascript": 86400,
            "image/*": 604800,  # 1 week
            "video/*": 2592000,  # 30 days
        }
        self.path_patterns: Dict[str, int] = {
            "/api/": 0,  # No cache
            "/static/": 2592000,
            "/assets/": 604800,
        }

    def get_ttl(self, path: str, content_type: str) -> int:
        """Get TTL for content."""
        # Check path patterns
        for pattern, ttl in self.path_patterns.items():
            if path.startswith(pattern):
                return ttl

        # Check content type
        for type_pattern, ttl in self.type_ttls.items():
            if type_pattern.endswith("/*"):
                if content_type.startswith(type_pattern[:-2]):
                    return ttl
            elif content_type == type_pattern:
                return ttl

        return self.default_ttl

    def should_cache(self, path: str, content_type: str) -> bool:
        """Check if content should be cached."""
        return self.get_ttl(path, content_type) > 0


# =============================================================================
# CONTENT TRANSFORMER
# =============================================================================

class ContentTransformer:
    """Content transformation."""

    def __init__(self):
        self.transformers: Dict[str, Callable[[bytes], bytes]] = {}

    def register(
        self,
        content_type: str,
        transformer: Callable[[bytes], bytes]
    ) -> None:
        """Register transformer."""
        self.transformers[content_type] = transformer

    def transform(
        self,
        content: bytes,
        content_type: str
    ) -> bytes:
        """Transform content."""
        transformer = self.transformers.get(content_type)

        if transformer:
            return transformer(content)

        return content


# =============================================================================
# COMPRESSOR
# =============================================================================

class Compressor:
    """Content compression."""

    @staticmethod
    def compress(
        content: bytes,
        compression: CompressionType
    ) -> Tuple[bytes, CompressionType]:
        """Compress content."""
        if compression == CompressionType.GZIP:
            return gzip.compress(content), CompressionType.GZIP

        if compression == CompressionType.DEFLATE:
            return zlib.compress(content), CompressionType.DEFLATE

        return content, CompressionType.NONE

    @staticmethod
    def decompress(
        content: bytes,
        compression: CompressionType
    ) -> bytes:
        """Decompress content."""
        if compression == CompressionType.GZIP:
            return gzip.decompress(content)

        if compression == CompressionType.DEFLATE:
            return zlib.decompress(content)

        return content

    @staticmethod
    def best_encoding(
        accept_encoding: str,
        content: bytes
    ) -> CompressionType:
        """Determine best encoding."""
        if len(content) < 1024:
            return CompressionType.NONE

        if "br" in accept_encoding:
            return CompressionType.BROTLI

        if "gzip" in accept_encoding:
            return CompressionType.GZIP

        if "deflate" in accept_encoding:
            return CompressionType.DEFLATE

        return CompressionType.NONE


# =============================================================================
# CONTENT DELIVERY MANAGER
# =============================================================================

class ContentDeliveryManager:
    """
    Comprehensive Content Delivery Manager for BAEL.
    """

    def __init__(self):
        self.edge_nodes: Dict[str, EdgeNode] = {}
        self.origins: List[OriginServer] = []
        self.cache_policy = CachePolicy()
        self.transformer = ContentTransformer()
        self.compressor = Compressor()
        self.stats = DeliveryStats()
        self._invalidation_queue: List[str] = []

    # -------------------------------------------------------------------------
    # EDGE NODE MANAGEMENT
    # -------------------------------------------------------------------------

    def add_edge_node(
        self,
        name: str,
        region: str,
        location: str,
        capacity: int = 1000
    ) -> str:
        """Add edge node."""
        node = EdgeNode(
            name=name,
            region=region,
            location=location,
            capacity=capacity
        )

        self.edge_nodes[node.node_id] = node
        return node.node_id

    def remove_edge_node(self, node_id: str) -> bool:
        """Remove edge node."""
        if node_id in self.edge_nodes:
            del self.edge_nodes[node_id]
            return True
        return False

    def get_edge_node(self, node_id: str) -> Optional[EdgeNode]:
        """Get edge node."""
        return self.edge_nodes.get(node_id)

    def select_edge_node(self, client_ip: str) -> Optional[EdgeNode]:
        """Select best edge node for client."""
        # In real implementation, would use GeoIP
        # For demo, return first healthy node
        for node in self.edge_nodes.values():
            if node.status == EdgeNodeStatus.HEALTHY:
                return node

        return None

    # -------------------------------------------------------------------------
    # ORIGIN MANAGEMENT
    # -------------------------------------------------------------------------

    def add_origin(
        self,
        host: str,
        port: int = 443,
        protocol: str = "https",
        priority: int = 1
    ) -> str:
        """Add origin server."""
        origin = OriginServer(
            host=host,
            port=port,
            protocol=protocol,
            priority=priority
        )

        self.origins.append(origin)
        self.origins.sort(key=lambda o: o.priority)

        return origin.origin_id

    def get_healthy_origin(self) -> Optional[OriginServer]:
        """Get healthy origin server."""
        for origin in self.origins:
            if origin.healthy:
                return origin
        return None

    # -------------------------------------------------------------------------
    # CONTENT DELIVERY
    # -------------------------------------------------------------------------

    async def deliver(
        self,
        request: ContentRequest
    ) -> ContentResponse:
        """Deliver content."""
        start_time = time.time()

        self.stats.total_requests += 1

        # Select edge node
        edge_node = self.select_edge_node(request.client_ip)

        if not edge_node:
            return ContentResponse(
                status_code=503,
                headers={"X-Error": "No available edge nodes"}
            )

        # Check cache
        cached = edge_node.cache.get(request.path)

        if cached and not cached.is_expired:
            cached.touch()
            self.stats.cache_hits += 1
            edge_node.stats["hits"] += 1

            # Handle conditional request
            if request.is_conditional():
                if request.if_none_match == cached.metadata.etag:
                    return ContentResponse(
                        status_code=304,
                        headers={"ETag": cached.metadata.etag},
                        cache_status=CacheStatus.HIT,
                        served_by=edge_node.name
                    )

            # Handle range request
            content = cached.content

            if request.is_range_request():
                content = self._handle_range(
                    content,
                    request.range_start,
                    request.range_end
                )

            # Compress if needed
            if request.accepts_gzip() and len(content) > 1024:
                content, encoding = self.compressor.compress(
                    content,
                    CompressionType.GZIP
                )

                headers = {
                    "Content-Encoding": encoding.value,
                    "Vary": "Accept-Encoding"
                }
            else:
                headers = {}

            response_time = time.time() - start_time
            self.stats.bytes_served += len(content)

            return ContentResponse(
                status_code=200,
                content=content,
                headers={
                    **headers,
                    "ETag": cached.metadata.etag,
                    "Cache-Control": cached.metadata.cache_control,
                    "Content-Type": cached.metadata.content_type,
                    "X-Cache": "HIT"
                },
                metadata=cached.metadata,
                cache_status=CacheStatus.HIT,
                served_by=edge_node.name,
                response_time=response_time
            )

        # Cache miss - fetch from origin
        self.stats.cache_misses += 1
        edge_node.stats["misses"] += 1

        content, metadata = await self._fetch_from_origin(request.path)

        if content is None:
            return ContentResponse(
                status_code=404,
                headers={"X-Error": "Content not found"},
                cache_status=CacheStatus.MISS,
                served_by=edge_node.name
            )

        # Cache content
        if self.cache_policy.should_cache(request.path, metadata.content_type):
            ttl = self.cache_policy.get_ttl(request.path, metadata.content_type)

            cached_content = CachedContent(
                metadata=metadata,
                content=content,
                expires_at=time.time() + ttl
            )

            edge_node.cache[request.path] = cached_content
            edge_node.used += len(content) // (1024 * 1024)  # MB

        response_time = time.time() - start_time
        self.stats.bytes_served += len(content)

        # Update avg response time
        total_time = self.stats.avg_response_time * (self.stats.total_requests - 1)
        self.stats.avg_response_time = (total_time + response_time) / self.stats.total_requests

        return ContentResponse(
            status_code=200,
            content=content,
            headers={
                "ETag": metadata.etag,
                "Cache-Control": metadata.cache_control,
                "Content-Type": metadata.content_type,
                "X-Cache": "MISS"
            },
            metadata=metadata,
            cache_status=CacheStatus.MISS,
            served_by=edge_node.name,
            response_time=response_time
        )

    async def _fetch_from_origin(
        self,
        path: str
    ) -> Tuple[Optional[bytes], Optional[ContentMetadata]]:
        """Fetch content from origin."""
        origin = self.get_healthy_origin()

        if not origin:
            return None, None

        # Simulate origin fetch
        await asyncio.sleep(0.05)  # Network latency

        # Check simulated content
        content = origin.content.get(path)

        if content is None:
            # Generate sample content
            content = f"Content for {path}".encode()

        # Generate metadata
        content_type = mimetypes.guess_type(path)[0] or "text/html"
        etag = hashlib.md5(content).hexdigest()

        metadata = ContentMetadata(
            path=path,
            content_type=content_type,
            size=len(content),
            etag=etag
        )

        return content, metadata

    def _handle_range(
        self,
        content: bytes,
        start: int,
        end: int
    ) -> bytes:
        """Handle range request."""
        if end == 0:
            end = len(content)

        return content[start:end]

    # -------------------------------------------------------------------------
    # CACHE MANAGEMENT
    # -------------------------------------------------------------------------

    def invalidate(
        self,
        path: str,
        purge_all_nodes: bool = True
    ) -> int:
        """Invalidate cached content."""
        invalidated = 0

        if purge_all_nodes:
            for node in self.edge_nodes.values():
                if path in node.cache:
                    del node.cache[path]
                    invalidated += 1

        return invalidated

    def invalidate_pattern(
        self,
        pattern: str
    ) -> int:
        """Invalidate by pattern."""
        import fnmatch

        invalidated = 0

        for node in self.edge_nodes.values():
            paths_to_remove = [
                p for p in node.cache.keys()
                if fnmatch.fnmatch(p, pattern)
            ]

            for path in paths_to_remove:
                del node.cache[path]
                invalidated += 1

        return invalidated

    def purge_all(self) -> int:
        """Purge all cached content."""
        purged = 0

        for node in self.edge_nodes.values():
            purged += len(node.cache)
            node.cache.clear()
            node.used = 0

        return purged

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_items = sum(len(n.cache) for n in self.edge_nodes.values())
        total_size = sum(n.used for n in self.edge_nodes.values())

        return {
            "total_items": total_items,
            "total_size_mb": total_size,
            "hit_rate": (
                self.stats.cache_hits / self.stats.total_requests
                if self.stats.total_requests > 0
                else 0.0
            ),
            "nodes": {
                node.name: {
                    "items": len(node.cache),
                    "size_mb": node.used,
                    "utilization": node.utilization,
                    "hits": node.stats.get("hits", 0),
                    "misses": node.stats.get("misses", 0)
                }
                for node in self.edge_nodes.values()
            }
        }

    # -------------------------------------------------------------------------
    # CONTENT MANAGEMENT
    # -------------------------------------------------------------------------

    def add_content(
        self,
        path: str,
        content: bytes,
        content_type: str = None
    ) -> ContentMetadata:
        """Add content to origin."""
        origin = self.get_healthy_origin()

        if origin:
            origin.content[path] = content

        content_type = content_type or mimetypes.guess_type(path)[0] or "text/html"
        etag = hashlib.md5(content).hexdigest()

        return ContentMetadata(
            path=path,
            content_type=content_type,
            size=len(content),
            etag=etag
        )

    def remove_content(self, path: str) -> bool:
        """Remove content from origin."""
        removed = False

        for origin in self.origins:
            if path in origin.content:
                del origin.content[path]
                removed = True

        # Also invalidate cache
        self.invalidate(path)

        return removed

    # -------------------------------------------------------------------------
    # STATISTICS
    # -------------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Get delivery statistics."""
        return {
            "total_requests": self.stats.total_requests,
            "cache_hits": self.stats.cache_hits,
            "cache_misses": self.stats.cache_misses,
            "hit_rate": (
                self.stats.cache_hits / self.stats.total_requests
                if self.stats.total_requests > 0
                else 0.0
            ),
            "bytes_served": self.stats.bytes_served,
            "bytes_saved": self.stats.bytes_saved,
            "avg_response_time_ms": self.stats.avg_response_time * 1000,
            "edge_nodes": len(self.edge_nodes),
            "origins": len(self.origins)
        }

    def get_node_stats(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Get edge node statistics."""
        node = self.edge_nodes.get(node_id)

        if not node:
            return None

        return {
            "node_id": node_id,
            "name": node.name,
            "region": node.region,
            "status": node.status.value,
            "cache_items": len(node.cache),
            "capacity_mb": node.capacity,
            "used_mb": node.used,
            "utilization": node.utilization,
            "hits": node.stats.get("hits", 0),
            "misses": node.stats.get("misses", 0)
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Content Delivery Manager System."""
    print("=" * 70)
    print("BAEL - CONTENT DELIVERY MANAGER DEMO")
    print("Comprehensive CDN-like Content Delivery")
    print("=" * 70)
    print()

    cdm = ContentDeliveryManager()

    # 1. Add Edge Nodes
    print("1. ADD EDGE NODES:")
    print("-" * 40)

    us_east = cdm.add_edge_node("US-East-1", "us-east", "Virginia", 2000)
    us_west = cdm.add_edge_node("US-West-1", "us-west", "California", 1500)
    eu_west = cdm.add_edge_node("EU-West-1", "eu-west", "Ireland", 1000)

    print(f"   Added {len(cdm.edge_nodes)} edge nodes:")

    for node in cdm.edge_nodes.values():
        print(f"      - {node.name} ({node.region})")
    print()

    # 2. Add Origin Server
    print("2. ADD ORIGIN SERVER:")
    print("-" * 40)

    origin_id = cdm.add_origin("origin.example.com", 443, "https", priority=1)

    print(f"   Origin: origin.example.com:443")
    print()

    # 3. Add Content
    print("3. ADD CONTENT:")
    print("-" * 40)

    contents = [
        ("/index.html", b"<html><body>Hello World</body></html>", "text/html"),
        ("/style.css", b"body { margin: 0; }", "text/css"),
        ("/app.js", b"console.log('Hello');", "application/javascript"),
        ("/data.json", b'{"key": "value"}', "application/json"),
        ("/image.png", b"\x89PNG\r\n\x1a\n" + b"x" * 1000, "image/png"),
    ]

    for path, content, content_type in contents:
        metadata = cdm.add_content(path, content, content_type)
        print(f"   Added: {path} ({metadata.size} bytes)")
    print()

    # 4. Deliver Content (Cache Miss)
    print("4. DELIVER CONTENT (CACHE MISS):")
    print("-" * 40)

    request = ContentRequest(
        path="/index.html",
        client_ip="192.168.1.100"
    )

    response = await cdm.deliver(request)

    print(f"   Path: {request.path}")
    print(f"   Status: {response.status_code}")
    print(f"   Cache: {response.cache_status.value}")
    print(f"   Served by: {response.served_by}")
    print(f"   Response time: {response.response_time*1000:.2f}ms")
    print()

    # 5. Deliver Content (Cache Hit)
    print("5. DELIVER CONTENT (CACHE HIT):")
    print("-" * 40)

    request = ContentRequest(
        path="/index.html",
        client_ip="192.168.1.100"
    )

    response = await cdm.deliver(request)

    print(f"   Path: {request.path}")
    print(f"   Status: {response.status_code}")
    print(f"   Cache: {response.cache_status.value}")
    print(f"   Response time: {response.response_time*1000:.2f}ms")
    print()

    # 6. Conditional Request
    print("6. CONDITIONAL REQUEST:")
    print("-" * 40)

    request = ContentRequest(
        path="/index.html",
        client_ip="192.168.1.100",
        if_none_match=response.metadata.etag
    )

    response = await cdm.deliver(request)

    print(f"   Status: {response.status_code} (304 = Not Modified)")
    print(f"   Cache: {response.cache_status.value}")
    print()

    # 7. Compressed Response
    print("7. COMPRESSED RESPONSE:")
    print("-" * 40)

    request = ContentRequest(
        path="/app.js",
        client_ip="192.168.1.100",
        accept_encoding="gzip, deflate"
    )

    # First request to populate cache
    await cdm.deliver(request)

    # Add larger content for compression
    large_content = b"console.log('Hello World');\n" * 100
    cdm.add_content("/large.js", large_content, "application/javascript")

    request = ContentRequest(
        path="/large.js",
        client_ip="192.168.1.100",
        accept_encoding="gzip, deflate"
    )

    response = await cdm.deliver(request)

    print(f"   Original size: {len(large_content)} bytes")
    print(f"   Compressed size: {len(response.content)} bytes")
    print(f"   Encoding: {response.headers.get('Content-Encoding', 'none')}")
    print()

    # 8. Multiple Requests
    print("8. MULTIPLE REQUESTS:")
    print("-" * 40)

    for path, _, _ in contents:
        for i in range(3):
            request = ContentRequest(
                path=path,
                client_ip=f"192.168.1.{i}"
            )
            await cdm.deliver(request)

    stats = cdm.get_stats()

    print(f"   Total requests: {stats['total_requests']}")
    print(f"   Cache hits: {stats['cache_hits']}")
    print(f"   Cache misses: {stats['cache_misses']}")
    print(f"   Hit rate: {stats['hit_rate']*100:.1f}%")
    print()

    # 9. Cache Invalidation
    print("9. CACHE INVALIDATION:")
    print("-" * 40)

    invalidated = cdm.invalidate("/index.html")
    print(f"   Invalidated /index.html: {invalidated} nodes")

    pattern_invalidated = cdm.invalidate_pattern("/*.js")
    print(f"   Invalidated /*.js: {pattern_invalidated} items")
    print()

    # 10. Edge Node Stats
    print("10. EDGE NODE STATS:")
    print("-" * 40)

    for node_id in cdm.edge_nodes.keys():
        node_stats = cdm.get_node_stats(node_id)

        print(f"   {node_stats['name']}:")
        print(f"      Cache items: {node_stats['cache_items']}")
        print(f"      Hits: {node_stats['hits']}")
        print(f"      Misses: {node_stats['misses']}")
    print()

    # 11. Cache Statistics
    print("11. CACHE STATISTICS:")
    print("-" * 40)

    cache_stats = cdm.get_cache_stats()

    print(f"   Total cached items: {cache_stats['total_items']}")
    print(f"   Total cache size: {cache_stats['total_size_mb']} MB")
    print(f"   Hit rate: {cache_stats['hit_rate']*100:.1f}%")
    print()

    # 12. Delivery Statistics
    print("12. DELIVERY STATISTICS:")
    print("-" * 40)

    stats = cdm.get_stats()

    print(f"   Total requests: {stats['total_requests']}")
    print(f"   Bytes served: {stats['bytes_served']}")
    print(f"   Avg response time: {stats['avg_response_time_ms']:.2f}ms")
    print(f"   Edge nodes: {stats['edge_nodes']}")
    print(f"   Origins: {stats['origins']}")
    print()

    # 13. Purge All
    print("13. PURGE ALL CACHE:")
    print("-" * 40)

    purged = cdm.purge_all()
    print(f"   Purged items: {purged}")

    cache_stats = cdm.get_cache_stats()
    print(f"   Remaining items: {cache_stats['total_items']}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Content Delivery Manager System Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())

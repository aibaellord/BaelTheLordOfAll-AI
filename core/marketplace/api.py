"""
Plugin Marketplace API endpoints for BAEL
"""

import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from core.marketplace.marketplace import (PluginCategory, PluginMarketplace,
                                          PluginMetadata, PluginRating,
                                          PluginVersion, SecurityLevel,
                                          SecurityScan)

logger = logging.getLogger(__name__)

# Global marketplace instance
marketplace = PluginMarketplace()

router = APIRouter(prefix="/v1/marketplace", tags=["marketplace"])


# ============================================================================
# Search & Discovery
# ============================================================================

@router.get("/search")
async def search_plugins(
    q: str = Query(..., description="Search query"),
    category: Optional[str] = Query(None, description="Filter by category"),
    sort_by: str = Query("downloads", description="Sort by: downloads, rating, recent"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> dict:
    """Search plugins in marketplace"""
    try:
        cat = PluginCategory(category) if category else None
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid category: {category}")

    plugins = marketplace.search(q, cat, sort_by, limit, offset)

    return {
        "query": q,
        "results": [p.to_dict() for p in plugins],
        "total": len([p for p in marketplace.plugins.values() if p.active]),
        "limit": limit,
        "offset": offset,
    }


@router.get("/featured")
async def get_featured(limit: int = Query(10, ge=1, le=50)) -> dict:
    """Get featured plugins"""
    plugins = marketplace.get_featured(limit)
    return {
        "plugins": [p.to_dict() for p in plugins],
        "count": len(plugins),
    }


@router.get("/trending")
async def get_trending(limit: int = Query(10, ge=1, le=50)) -> dict:
    """Get trending plugins"""
    plugins = marketplace.get_trending(limit)
    return {
        "plugins": [p.to_dict() for p in plugins],
        "count": len(plugins),
    }


@router.get("/categories")
async def get_categories() -> dict:
    """Get all plugin categories"""
    return {
        "categories": [cat.value for cat in PluginCategory],
        "count": len(PluginCategory),
    }


@router.get("/category/{category}")
async def get_by_category(
    category: str,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> dict:
    """Get plugins in category"""
    try:
        cat = PluginCategory(category)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid category: {category}")

    plugins = marketplace.get_by_category(cat, limit, offset)

    return {
        "category": category,
        "plugins": [p.to_dict() for p in plugins],
        "count": len(plugins),
        "limit": limit,
        "offset": offset,
    }


# ============================================================================
# Plugin Details
# ============================================================================

@router.get("/plugin/{plugin_id}")
async def get_plugin(plugin_id: str) -> dict:
    """Get plugin details"""
    plugin = marketplace.get_plugin(plugin_id)
    if not plugin:
        raise HTTPException(status_code=404, detail=f"Plugin not found: {plugin_id}")

    return {
        "plugin": plugin.to_dict(),
        "versions": [v.to_dict() for v in plugin.versions],
        "ratings": [r.to_dict() for r in plugin.ratings[-10:]],  # Last 10
    }


@router.get("/plugin/{plugin_id}/compatibility")
async def get_compatibility(
    plugin_id: str,
    bael_version: str = Query("2.1.0"),
) -> dict:
    """Check plugin compatibility with BAEL version"""
    plugin = marketplace.get_plugin(plugin_id)
    if not plugin:
        raise HTTPException(status_code=404, detail=f"Plugin not found: {plugin_id}")

    return marketplace.get_compatibility_info(plugin_id, bael_version)


@router.get("/author/{author}")
async def get_by_author(author: str) -> dict:
    """Get all plugins by author"""
    plugins = marketplace.get_by_author(author)

    return {
        "author": author,
        "plugins": [p.to_dict() for p in plugins],
        "count": len(plugins),
    }


# ============================================================================
# Recommendations
# ============================================================================

@router.get("/recommendations")
async def get_recommendations(
    category: Optional[str] = Query(None),
    limit: int = Query(5, ge=1, le=20),
) -> dict:
    """Get recommended plugins"""
    try:
        cat = PluginCategory(category) if category else None
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid category: {category}")

    plugins = marketplace.get_recommendations(cat, limit)

    return {
        "recommendations": [p.to_dict() for p in plugins],
        "count": len(plugins),
    }


# ============================================================================
# Ratings & Reviews
# ============================================================================

@router.post("/plugin/{plugin_id}/rate")
async def rate_plugin(
    plugin_id: str,
    user_id: str = Query(...),
    rating: int = Query(..., ge=1, le=5),
    review: str = Query("", max_length=500),
) -> dict:
    """Submit a rating for a plugin"""
    if not marketplace.get_plugin(plugin_id):
        raise HTTPException(status_code=404, detail=f"Plugin not found: {plugin_id}")

    plugin_rating = PluginRating(
        user_id=user_id,
        rating=rating,
        review=review,
        timestamp=datetime.utcnow().isoformat(),
        verified_user=True,
    )

    success = marketplace.add_rating(plugin_id, plugin_rating)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to add rating")

    plugin = marketplace.get_plugin(plugin_id)
    return {
        "plugin_id": plugin_id,
        "rating_count": plugin.rating_count,
        "average_rating": plugin.rating_average,
    }


@router.get("/plugin/{plugin_id}/ratings")
async def get_ratings(
    plugin_id: str,
    limit: int = Query(20, ge=1, le=100),
) -> dict:
    """Get ratings for a plugin"""
    plugin = marketplace.get_plugin(plugin_id)
    if not plugin:
        raise HTTPException(status_code=404, detail=f"Plugin not found: {plugin_id}")

    ratings = [r.to_dict() for r in plugin.ratings[-limit:]]

    return {
        "plugin_id": plugin_id,
        "ratings": ratings,
        "total_count": plugin.rating_count,
        "average_rating": plugin.rating_average,
    }


# ============================================================================
# Downloads
# ============================================================================

@router.post("/plugin/{plugin_id}/download")
async def record_download(plugin_id: str) -> dict:
    """Record a plugin download"""
    if not marketplace.record_download(plugin_id):
        raise HTTPException(status_code=404, detail=f"Plugin not found: {plugin_id}")

    plugin = marketplace.get_plugin(plugin_id)
    return {
        "plugin_id": plugin_id,
        "downloads_total": plugin.downloads_total,
    }


# ============================================================================
# Admin APIs
# ============================================================================

@router.post("/admin/register")
async def register_plugin(plugin_data: dict) -> dict:
    """Register a new plugin"""
    try:
        metadata = PluginMetadata(
            id=plugin_data.get("id"),
            name=plugin_data.get("name"),
            author=plugin_data.get("author"),
            author_email=plugin_data.get("author_email"),
            description=plugin_data.get("description"),
            long_description=plugin_data.get("long_description", ""),
            category=PluginCategory(plugin_data.get("category", "tool")),
            version=plugin_data.get("version", "1.0.0"),
            homepage=plugin_data.get("homepage", ""),
            repository=plugin_data.get("repository", ""),
            documentation=plugin_data.get("documentation", ""),
            keywords=plugin_data.get("keywords", []),
            published_at=datetime.utcnow().isoformat(),
            updated_at=datetime.utcnow().isoformat(),
        )

        # Add initial version
        if "version" in plugin_data:
            version = PluginVersion(
                version=plugin_data.get("version", "1.0.0"),
                release_date=datetime.utcnow().isoformat(),
                size_bytes=plugin_data.get("size_bytes", 0),
                changelog=plugin_data.get("changelog", ""),
            )
            metadata.versions.append(version)

        if not marketplace.register_plugin(metadata):
            raise HTTPException(status_code=400, detail="Plugin already exists")

        logger.info(f"Registered plugin: {metadata.id}")
        return {"message": "Plugin registered", "plugin_id": metadata.id}

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/admin/verify-author/{author}")
async def verify_author(author: str) -> dict:
    """Verify an author"""
    marketplace.verify_author(author)
    return {"message": f"Author verified: {author}"}


@router.post("/admin/trust-plugin/{plugin_id}")
async def trust_plugin(plugin_id: str) -> dict:
    """Mark plugin as trusted"""
    if not marketplace.trust_plugin(plugin_id):
        raise HTTPException(status_code=404, detail=f"Plugin not found: {plugin_id}")

    return {"message": f"Plugin trusted: {plugin_id}"}


@router.post("/admin/security-scan/{plugin_id}")
async def security_scan(plugin_id: str, scan_data: dict) -> dict:
    """Record security scan result"""
    try:
        scan = SecurityScan(
            timestamp=datetime.utcnow().isoformat(),
            level=SecurityLevel(scan_data.get("level", "medium")),
            issues=scan_data.get("issues", []),
            permissions_requested=set(scan_data.get("permissions", [])),
            dependencies_audited=scan_data.get("dependencies_audited", False),
            malware_check=scan_data.get("malware_check", False),
        )

        if not marketplace.scan_security(plugin_id, scan):
            raise HTTPException(status_code=404, detail=f"Plugin not found: {plugin_id}")

        return {"message": f"Security scan recorded: {plugin_id}", "level": scan.level.value}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid security level: {e}")


# ============================================================================
# Statistics
# ============================================================================

@router.get("/statistics")
async def get_statistics() -> dict:
    """Get marketplace statistics"""
    return marketplace.get_statistics()


@router.get("/catalog")
async def get_catalog() -> dict:
    """Export complete marketplace catalog"""
    return marketplace.export_catalog()


# Export router
__all__ = ["router", "marketplace"]

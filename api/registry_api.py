"""
BAEL Registry API
Exposes the MasterRegistry and BAELStartup status via REST endpoints.
Allows the UI and external tools to browse all discovered capabilities.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

logger = logging.getLogger("BAEL.API.Registry")

router = APIRouter(prefix="/registry", tags=["Registry"])

# Lazy imports so the server doesn't fail if bootstrap isn't ready
def _get_registry():
    from core.bootstrap.registry import get_registry
    return get_registry()


def _get_startup():
    from core.bootstrap.startup import get_startup
    return get_startup()


# ─────────────────────────────────────────────────────────────
# MODELS
# ─────────────────────────────────────────────────────────────

class CapabilityOut(BaseModel):
    id: str
    name: str
    item_type: str
    description: str
    version: str = "1.0.0"
    enabled: bool
    tags: List[str] = []
    metadata: Dict[str, Any] = {}


class RegistryStats(BaseModel):
    total: int
    by_type: Dict[str, int]
    enabled: int
    disabled: int


class StartupStatus(BaseModel):
    phase: str
    success: bool
    capabilities_loaded: int
    agents_registered: int
    plugins_loaded: int
    workflows_loaded: int
    startup_time_ms: float
    errors: List[str] = []
    warnings: List[str] = []


# ─────────────────────────────────────────────────────────────
# ENDPOINTS
# ─────────────────────────────────────────────────────────────

@router.get("/capabilities", response_model=List[CapabilityOut])
async def list_capabilities(
    type: Optional[str] = Query(None, description="Filter by capability type"),
    enabled_only: bool = Query(False, description="Only return enabled capabilities"),
    search: Optional[str] = Query(None, description="Search term"),
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    """List all capabilities registered in the MasterRegistry."""
    try:
        registry = _get_registry()
    except Exception as e:
        raise HTTPException(503, f"Registry not initialized: {e}")

    if type:
        items = registry.list_by_type(type)
    elif search:
        items = registry.search(search)
    else:
        items = registry.list_all()

    if enabled_only:
        items = [i for i in items if i.enabled]

    sliced = items[offset: offset + limit]

    return [
        CapabilityOut(
            id=item.id,
            name=item.name,
            item_type=item.item_type,
            description=item.description or "",
            version=item.version,
            enabled=item.enabled,
            tags=sorted(item.tags),
            metadata=item.metadata,
        )
        for item in sliced
    ]


@router.get("/capabilities/types", response_model=List[str])
async def list_capability_types():
    """Return distinct capability types present in the registry."""
    try:
        registry = _get_registry()
    except Exception as e:
        raise HTTPException(503, f"Registry not initialized: {e}")

    types = sorted({item.item_type for item in registry.list_all()})
    return types


@router.get("/capabilities/{capability_id}", response_model=CapabilityOut)
async def get_capability(capability_id: str):
    """Get a specific capability by ID."""
    try:
        registry = _get_registry()
    except Exception as e:
        raise HTTPException(503, f"Registry not initialized: {e}")

    item = registry.get(capability_id)
    if not item:
        raise HTTPException(404, f"Capability '{capability_id}' not found")

    return CapabilityOut(
        id=item.id,
        name=item.name,
        item_type=item.item_type,
        description=item.description or "",
        version=item.version,
        enabled=item.enabled,
        tags=sorted(item.tags),
        metadata=item.metadata,
    )


@router.get("/capabilities/{capability_id}/enable", response_model=dict)
async def enable_capability(capability_id: str):
    """Enable a capability."""
    try:
        registry = _get_registry()
    except Exception as e:
        raise HTTPException(503, f"Registry not initialized: {e}")

    ok = registry.enable(capability_id)
    if not ok:
        raise HTTPException(404, f"Capability '{capability_id}' not found")
    return {"success": True, "id": capability_id, "enabled": True}


@router.get("/capabilities/{capability_id}/disable", response_model=dict)
async def disable_capability(capability_id: str):
    """Disable a capability."""
    try:
        registry = _get_registry()
    except Exception as e:
        raise HTTPException(503, f"Registry not initialized: {e}")

    ok = registry.disable(capability_id)
    if not ok:
        raise HTTPException(404, f"Capability '{capability_id}' not found")
    return {"success": True, "id": capability_id, "enabled": False}


@router.get("/stats", response_model=RegistryStats)
async def registry_stats():
    """Return registry statistics."""
    try:
        registry = _get_registry()
        by_type = registry.stats()  # {type: count}
        all_items = registry.list_all()
        enabled = sum(1 for i in all_items if i.enabled)
        total = len(all_items)
    except Exception as e:
        raise HTTPException(503, f"Registry not initialized: {e}")

    return RegistryStats(
        total=total,
        by_type=by_type,
        enabled=enabled,
        disabled=total - enabled,
    )


@router.get("/bootstrap/status", response_model=StartupStatus)
async def bootstrap_status():
    """Return the BAEL startup / bootstrap status."""
    try:
        startup = _get_startup()
        result = startup.last_result
    except Exception as e:
        return StartupStatus(
            phase="unknown",
            success=False,
            capabilities_loaded=0,
            agents_registered=0,
            plugins_loaded=0,
            workflows_loaded=0,
            startup_time_ms=0.0,
            errors=[str(e)],
        )

    if result is None:
        return StartupStatus(
            phase="not_started",
            success=False,
            capabilities_loaded=0,
            agents_registered=0,
            plugins_loaded=0,
            workflows_loaded=0,
            startup_time_ms=0.0,
        )

    return StartupStatus(
        phase=result.final_phase,
        success=result.success,
        capabilities_loaded=result.capabilities_loaded,
        agents_registered=result.agents_registered,
        plugins_loaded=result.plugins_loaded,
        workflows_loaded=result.workflows_loaded,
        startup_time_ms=result.startup_time_ms,
        errors=result.errors,
        warnings=result.warnings,
    )


@router.post("/reload", response_model=dict)
async def reload_registry():
    """Trigger a full registry re-scan and reload."""
    try:
        from core.bootstrap.startup import initialize
        result = await initialize(fail_fast=False)
        return {
            "success": result.success,
            "capabilities_loaded": result.capabilities_loaded,
            "phase": result.final_phase,
        }
    except Exception as e:
        raise HTTPException(500, f"Reload failed: {e}")

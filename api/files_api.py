"""
BAEL Files API - Workspace File Management
==========================================

This API provides file system access for the UI file browser,
allowing users to browse, read, write, and manage files in
their workspace.
"""

import logging
import mimetypes
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

logger = logging.getLogger("BAEL.FilesAPI")

router = APIRouter(prefix="/v1/files", tags=["files"])

# Base workspace directory
WORKSPACE_ROOT = Path(__file__).parent.parent


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class FileNode(BaseModel):
    """File or directory node."""
    name: str
    path: str
    type: str  # 'file' or 'directory'
    size: Optional[int] = None
    modified: Optional[str] = None
    children: Optional[List["FileNode"]] = None
    extension: Optional[str] = None


class FileContent(BaseModel):
    """File content response."""
    path: str
    name: str
    content: str
    size: int
    modified: str
    language: Optional[str] = None


class WriteFileRequest(BaseModel):
    """Request to write file content."""
    path: str
    content: str


class CreateRequest(BaseModel):
    """Request to create file or directory."""
    path: str
    type: str = "file"  # 'file' or 'directory'
    content: Optional[str] = ""


class RenameRequest(BaseModel):
    """Request to rename file or directory."""
    old_path: str
    new_path: str


class SearchRequest(BaseModel):
    """Request to search files."""
    query: str
    path: Optional[str] = None
    extensions: Optional[List[str]] = None
    max_results: int = 50


class SearchResult(BaseModel):
    """Search result item."""
    path: str
    name: str
    type: str
    line: Optional[int] = None
    preview: Optional[str] = None


# =============================================================================
# HELPERS
# =============================================================================

def get_language_from_extension(ext: str) -> str:
    """Map file extension to language for syntax highlighting."""
    lang_map = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".tsx": "typescriptreact",
        ".jsx": "javascriptreact",
        ".json": "json",
        ".html": "html",
        ".css": "css",
        ".scss": "scss",
        ".md": "markdown",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".toml": "toml",
        ".sh": "bash",
        ".bash": "bash",
        ".zsh": "zsh",
        ".sql": "sql",
        ".rs": "rust",
        ".go": "go",
        ".java": "java",
        ".c": "c",
        ".cpp": "cpp",
        ".h": "c",
        ".hpp": "cpp",
        ".rb": "ruby",
        ".php": "php",
        ".swift": "swift",
        ".kt": "kotlin",
        ".r": "r",
        ".jl": "julia",
        ".lua": "lua",
        ".vim": "vim",
        ".dockerfile": "dockerfile",
        ".xml": "xml",
        ".svg": "xml",
    }
    return lang_map.get(ext.lower(), "plaintext")


def safe_path(path: str) -> Path:
    """Validate and resolve path within workspace."""
    # Resolve the path relative to workspace root
    if path.startswith("/"):
        full_path = Path(path)
    else:
        full_path = WORKSPACE_ROOT / path

    # Resolve to absolute and check it's within allowed directories
    resolved = full_path.resolve()

    # Allow workspace root and user home
    allowed_roots = [
        WORKSPACE_ROOT.resolve(),
        Path.home().resolve(),
    ]

    is_allowed = any(
        str(resolved).startswith(str(root))
        for root in allowed_roots
    )

    if not is_allowed:
        raise HTTPException(status_code=403, detail="Access denied to this path")

    return resolved


def build_tree(path: Path, depth: int = 0, max_depth: int = 3) -> Optional[FileNode]:
    """Build file tree from path."""
    if not path.exists():
        return None

    # Skip hidden files and common ignore patterns
    ignore_patterns = {
        "__pycache__", ".git", "node_modules", ".venv", "venv",
        ".pytest_cache", ".mypy_cache", "dist", "build", ".tox",
        ".eggs", "*.egg-info", ".DS_Store", "*.pyc"
    }

    if path.name in ignore_patterns or path.name.startswith("."):
        return None

    if path.is_file():
        stat = path.stat()
        return FileNode(
            name=path.name,
            path=str(path),
            type="file",
            size=stat.st_size,
            modified=datetime.fromtimestamp(stat.st_mtime).isoformat(),
            extension=path.suffix
        )
    elif path.is_dir():
        children = []
        if depth < max_depth:
            try:
                for child in sorted(path.iterdir(), key=lambda p: (p.is_file(), p.name.lower())):
                    child_node = build_tree(child, depth + 1, max_depth)
                    if child_node:
                        children.append(child_node)
            except PermissionError:
                pass

        stat = path.stat()
        return FileNode(
            name=path.name,
            path=str(path),
            type="directory",
            modified=datetime.fromtimestamp(stat.st_mtime).isoformat(),
            children=children if children else None
        )

    return None


# =============================================================================
# API ENDPOINTS
# =============================================================================

@router.get("/tree")
async def get_file_tree(path: Optional[str] = None, depth: int = 3):
    """Get file tree for a directory."""
    target = safe_path(path) if path else WORKSPACE_ROOT

    if not target.exists():
        raise HTTPException(status_code=404, detail="Path not found")

    if not target.is_dir():
        raise HTTPException(status_code=400, detail="Path is not a directory")

    tree = build_tree(target, max_depth=depth)
    return {"tree": tree}


@router.get("/list")
async def list_directory(path: Optional[str] = None):
    """List contents of a directory."""
    target = safe_path(path) if path else WORKSPACE_ROOT

    if not target.exists():
        raise HTTPException(status_code=404, detail="Path not found")

    if not target.is_dir():
        raise HTTPException(status_code=400, detail="Path is not a directory")

    items = []
    try:
        for item in sorted(target.iterdir(), key=lambda p: (p.is_file(), p.name.lower())):
            if item.name.startswith("."):
                continue

            stat = item.stat()
            items.append({
                "name": item.name,
                "path": str(item),
                "type": "directory" if item.is_dir() else "file",
                "size": stat.st_size if item.is_file() else None,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "extension": item.suffix if item.is_file() else None
            })
    except PermissionError:
        raise HTTPException(status_code=403, detail="Permission denied")

    return {"items": items, "path": str(target)}


@router.get("/read")
async def read_file(path: str):
    """Read file content."""
    target = safe_path(path)

    if not target.exists():
        raise HTTPException(status_code=404, detail="File not found")

    if not target.is_file():
        raise HTTPException(status_code=400, detail="Path is not a file")

    # Check file size (limit to 5MB for text files)
    stat = target.stat()
    if stat.st_size > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 5MB)")

    try:
        content = target.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File is not a text file")

    return FileContent(
        path=str(target),
        name=target.name,
        content=content,
        size=stat.st_size,
        modified=datetime.fromtimestamp(stat.st_mtime).isoformat(),
        language=get_language_from_extension(target.suffix)
    )


@router.post("/write")
async def write_file(request: WriteFileRequest):
    """Write content to a file."""
    target = safe_path(request.path)

    # Ensure parent directory exists
    target.parent.mkdir(parents=True, exist_ok=True)

    try:
        target.write_text(request.content, encoding="utf-8")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to write file: {e}")

    return {"success": True, "path": str(target)}


@router.post("/create")
async def create_item(request: CreateRequest):
    """Create a new file or directory."""
    target = safe_path(request.path)

    if target.exists():
        raise HTTPException(status_code=409, detail="Path already exists")

    try:
        if request.type == "directory":
            target.mkdir(parents=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(request.content or "", encoding="utf-8")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create: {e}")

    return {"success": True, "path": str(target)}


@router.post("/rename")
async def rename_item(request: RenameRequest):
    """Rename a file or directory."""
    old_path = safe_path(request.old_path)
    new_path = safe_path(request.new_path)

    if not old_path.exists():
        raise HTTPException(status_code=404, detail="Source path not found")

    if new_path.exists():
        raise HTTPException(status_code=409, detail="Destination already exists")

    try:
        old_path.rename(new_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to rename: {e}")

    return {"success": True, "old_path": str(old_path), "new_path": str(new_path)}


@router.delete("/delete")
async def delete_item(path: str):
    """Delete a file or directory."""
    target = safe_path(path)

    if not target.exists():
        raise HTTPException(status_code=404, detail="Path not found")

    try:
        if target.is_dir():
            import shutil
            shutil.rmtree(target)
        else:
            target.unlink()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete: {e}")

    return {"success": True, "path": str(target)}


@router.post("/upload")
async def upload_file(path: str, file: UploadFile = File(...)):
    """Upload a file."""
    target_dir = safe_path(path)

    if not target_dir.is_dir():
        target_dir.mkdir(parents=True, exist_ok=True)

    target = target_dir / file.filename

    try:
        content = await file.read()
        target.write_bytes(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload: {e}")

    return {"success": True, "path": str(target), "size": len(content)}


@router.get("/download")
async def download_file(path: str):
    """Download a file."""
    target = safe_path(path)

    if not target.exists():
        raise HTTPException(status_code=404, detail="File not found")

    if not target.is_file():
        raise HTTPException(status_code=400, detail="Path is not a file")

    return FileResponse(
        path=target,
        filename=target.name,
        media_type=mimetypes.guess_type(target.name)[0] or "application/octet-stream"
    )


@router.post("/search")
async def search_files(request: SearchRequest):
    """Search for files matching query."""
    base = safe_path(request.path) if request.path else WORKSPACE_ROOT

    if not base.is_dir():
        raise HTTPException(status_code=400, detail="Base path is not a directory")

    results = []
    query = request.query.lower()

    try:
        for path in base.rglob("*"):
            if len(results) >= request.max_results:
                break

            # Skip hidden and ignored
            if any(part.startswith(".") for part in path.parts):
                continue
            if any(part in {"node_modules", "__pycache__", ".git", "venv"} for part in path.parts):
                continue

            # Filter by extension if specified
            if request.extensions and path.is_file():
                if path.suffix.lower() not in [ext.lower() for ext in request.extensions]:
                    continue

            # Match query in filename
            if query in path.name.lower():
                results.append(SearchResult(
                    path=str(path),
                    name=path.name,
                    type="directory" if path.is_dir() else "file"
                ))
                continue

            # Search in file content for text files
            if path.is_file() and path.stat().st_size < 1024 * 1024:  # < 1MB
                try:
                    content = path.read_text(encoding="utf-8", errors="ignore")
                    lines = content.split("\n")
                    for i, line in enumerate(lines):
                        if query in line.lower():
                            results.append(SearchResult(
                                path=str(path),
                                name=path.name,
                                type="file",
                                line=i + 1,
                                preview=line.strip()[:100]
                            ))
                            break
                except:
                    pass
    except Exception as e:
        logger.error(f"Search error: {e}")

    return {"results": results, "total": len(results)}


@router.get("/workspace")
async def get_workspace_info():
    """Get workspace information."""
    return {
        "root": str(WORKSPACE_ROOT),
        "name": WORKSPACE_ROOT.name,
        "exists": WORKSPACE_ROOT.exists(),
    }

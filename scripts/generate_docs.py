#!/usr/bin/env python3
"""
BAEL Documentation Generator
Automatically harvests docstrings, capability matrices, folder maps,
API schemas, and module inventories — then writes them to docs/.
"""
from __future__ import annotations

import ast
import importlib
import importlib.util
import inspect
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DOCS_OUT = ROOT / "docs" / "generated"
DOCS_OUT.mkdir(parents=True, exist_ok=True)


# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────

def safe_read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


EXCLUDE_DIRS = {".venv", "__pycache__", "node_modules", ".git", "dist", "build", "htmlcov"}


def iter_py_files(root: Path):
    """Yield .py files excluding common non-project dirs."""
    for f in root.rglob("*.py"):
        parts = set(f.parts)
        if not parts.intersection(EXCLUDE_DIRS):
            yield f


def _module_docstring(path: Path) -> str:
    """Extract the top-level docstring from a Python file without importing it."""
    try:
        tree = ast.parse(safe_read(path))
        return ast.get_docstring(tree) or ""
    except Exception:
        return ""


def _count_classes_functions(path: Path) -> tuple[int, int]:
    try:
        tree = ast.parse(safe_read(path))
        classes = sum(1 for n in ast.walk(tree) if isinstance(n, ast.ClassDef))
        functions = sum(1 for n in ast.walk(tree) if isinstance(n, ast.FunctionDef))
        return classes, functions
    except Exception:
        return 0, 0


# ─────────────────────────────────────────────────────────────
# 1. FOLDER MAP
# ─────────────────────────────────────────────────────────────

def generate_folder_map() -> str:
    lines = [
        "# BAEL Folder Map",
        f"> Auto-generated on {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        "| Path | Files | Description |",
        "|------|-------|-------------|",
    ]

    important_dirs = [
        ("core/", "500+ AI modules — reasoning, orchestration, memory, consciousness"),
        ("api/", "FastAPI REST server and route handlers"),
        ("mcp/", "Model Context Protocol server exposing BAEL tools to Claude/VSCode"),
        ("ui/web/src/", "React + TypeScript frontend"),
        ("sdk/", "Public Python SDK for external integrations"),
        ("plugins/", "Hot-loadable plugin packages"),
        ("workflows/", "YAML automation workflow definitions"),
        ("integrations/", "Third-party connector modules"),
        ("scripts/", "CLI utilities and maintenance scripts"),
        ("tools/", "Developer tooling and helpers"),
        ("config/", "Environment and system configuration files"),
        (".agent/", "Agent skill templates and workflow blueprints"),
        (".ai/", "AI persona and capability overrides"),
        (".gemini/", "Gemini-specific settings"),
        ("docs/", "Documentation and auto-generated references"),
        ("tests/", "Pytest suite"),
        ("deploy/", "Deployment manifests"),
        ("docker/", "Docker build files"),
        ("k8s/", "Kubernetes manifests"),
        ("memory/", "Persistent memory storage"),
        ("knowledge/", "Knowledge base files"),
        ("research/", "Research notes and findings"),
        ("outputs/", "Agent and pipeline outputs"),
        ("prompts/", "Prompt templates"),
        ("personas/", "Agent personas"),
    ]

    for rel, desc in important_dirs:
        full = ROOT / rel
        if full.exists():
            n_files = sum(1 for f in full.rglob("*")
                         if f.is_file() and not any(p in EXCLUDE_DIRS for p in f.parts))
            lines.append(f"| `{rel}` | {n_files} | {desc} |")

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────
# 2. CAPABILITY MATRIX
# ─────────────────────────────────────────────────────────────

def generate_capability_matrix() -> str:
    core_dir = ROOT / "core"
    if not core_dir.exists():
        return "# Capability Matrix\n\ncore/ directory not found."

    rows: list[dict[str, Any]] = []

    for subdir in sorted(core_dir.iterdir()):
        if not subdir.is_dir() or subdir.name.startswith("__"):
            continue

        py_files = [f for f in subdir.rglob("*.py")
                    if not any(p in EXCLUDE_DIRS for p in f.parts)]
        total_classes = 0
        total_functions = 0
        docstrings: list[str] = []

        for pf in py_files:
            c, f = _count_classes_functions(pf)
            total_classes += c
            total_functions += f
            ds = _module_docstring(pf)
            if ds:
                docstrings.append(ds.splitlines()[0][:80])

        rows.append({
            "module": subdir.name,
            "files": len(py_files),
            "classes": total_classes,
            "functions": total_functions,
            "desc": docstrings[0] if docstrings else "—",
        })

    lines = [
        "# BAEL Capability Matrix",
        f"> Auto-generated on {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
        f"> **{len(rows)} core modules** spanning {sum(r['files'] for r in rows)} Python files",
        "",
        "| Module | Files | Classes | Functions | Description |",
        "|--------|-------|---------|-----------|-------------|",
    ]

    for r in rows:
        lines.append(
            f"| `{r['module']}` | {r['files']} | {r['classes']} | {r['functions']} | {r['desc']} |"
        )

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────
# 3. PLUGIN INVENTORY
# ─────────────────────────────────────────────────────────────

def generate_plugin_inventory() -> str:
    plugins_dir = ROOT / "plugins"
    lines = [
        "# Plugin Inventory",
        f"> Auto-generated on {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
        "",
    ]

    if not plugins_dir.exists():
        lines.append("No plugins directory found.")
        return "\n".join(lines)

    for plugin_dir in sorted(plugins_dir.iterdir()):
        if not plugin_dir.is_dir():
            continue
        readme = plugin_dir / "README.md"
        plugin_yaml = plugin_dir / "plugin.yaml"
        main_py = plugin_dir / "main.py"

        lines.append(f"## {plugin_dir.name}")

        if plugin_yaml.exists():
            try:
                import yaml
                cfg = yaml.safe_load(safe_read(plugin_yaml))
                if isinstance(cfg, dict):
                    lines.append(f"- **Version**: {cfg.get('version', 'unknown')}")
                    lines.append(f"- **Description**: {cfg.get('description', '—')}")
            except Exception:
                pass

        if readme.exists():
            first_line = safe_read(readme).splitlines()[0].lstrip("# ").strip()
            lines.append(f"- **README summary**: {first_line}")

        if main_py.exists():
            ds = _module_docstring(main_py)
            if ds:
                lines.append(f"- **Docstring**: {ds.splitlines()[0][:100]}")

        py_count = len(list(plugin_dir.rglob("*.py")))
        lines.append(f"- **Python files**: {py_count}")
        lines.append("")

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────
# 4. WORKFLOW INVENTORY
# ─────────────────────────────────────────────────────────────

def generate_workflow_inventory() -> str:
    workflows_dir = ROOT / "workflows"
    agent_workflows = ROOT / ".agent" / "workflows"

    lines = [
        "# Workflow Inventory",
        f"> Auto-generated on {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        "## workflows/",
    ]

    def _scan_dir(d: Path) -> None:
        if not d.exists():
            lines.append(f"> Directory `{d.relative_to(ROOT)}` not found.\n")
            return
        for f in sorted(d.rglob("*.yaml")) + sorted(d.rglob("*.yml")) + sorted(d.rglob("*.md")):
            rel = f.relative_to(ROOT)
            first = safe_read(f).splitlines()[0].lstrip("# ").strip()[:100]
            lines.append(f"- [`{rel}`]({rel}): {first}")
        lines.append("")

    _scan_dir(workflows_dir)
    lines.append("## .agent/workflows/")
    _scan_dir(agent_workflows)

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────
# 5. API ENDPOINT INVENTORY
# ─────────────────────────────────────────────────────────────

def generate_api_inventory() -> str:
    api_server = ROOT / "api" / "server.py"
    lines = [
        "# API Endpoint Inventory",
        f"> Auto-generated on {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
        "",
    ]

    if not api_server.exists():
        lines.append("api/server.py not found.")
        return "\n".join(lines)

    content = safe_read(api_server)
    # Regex to find @app.get/@app.post etc.
    pattern = re.compile(
        r'@(?:app|router)\.(get|post|put|delete|patch|websocket)\(["\']([^"\']+)["\']',
        re.MULTILINE,
    )
    endpoints: list[tuple[str, str]] = pattern.findall(content)

    lines.append(f"**{len(endpoints)} endpoints** found in `api/server.py`\n")
    lines.append("| Method | Path |")
    lines.append("|--------|------|")
    for method, path in sorted(endpoints, key=lambda x: x[1]):
        lines.append(f"| `{method.upper()}` | `{path}` |")

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────
# 6. MCP TOOL INVENTORY
# ─────────────────────────────────────────────────────────────

def generate_mcp_inventory() -> str:
    mcp_server = ROOT / "mcp" / "server.py"
    lines = [
        "# MCP Tool Inventory",
        f"> Auto-generated on {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
        "",
    ]

    if not mcp_server.exists():
        lines.append("mcp/server.py not found.")
        return "\n".join(lines)

    content = safe_read(mcp_server)
    # Find @server.tool() decorated functions
    pattern = re.compile(r'@(?:server|mcp)\.tool\(\)(.*?)async def (\w+)', re.DOTALL)
    tools = pattern.findall(content)

    # Simpler fallback — find 'async def bael_*'
    if not tools:
        tool_fns = re.findall(r'async def (bael_\w+)', content)
    else:
        tool_fns = [t[1] for t in tools]

    lines.append(f"**{len(tool_fns)} tools** found in `mcp/server.py`\n")
    for fn in sorted(set(tool_fns)):
        lines.append(f"- `{fn}`")

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────
# 7. INTEGRATION INVENTORY
# ─────────────────────────────────────────────────────────────

def generate_integration_inventory() -> str:
    integrations_dir = ROOT / "integrations"
    lines = [
        "# Integration Inventory",
        f"> Auto-generated on {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        "| Integration | Files | Description |",
        "|-------------|-------|-------------|",
    ]

    if not integrations_dir.exists():
        lines.append("integrations/ not found.")
        return "\n".join(lines)

    for item in sorted(integrations_dir.iterdir()):
        if item.is_dir():
            py_files = list(item.rglob("*.py"))
            desc = "—"
            for pf in py_files:
                ds = _module_docstring(pf)
                if ds:
                    desc = ds.splitlines()[0][:80]
                    break
            lines.append(f"| `{item.name}` | {len(py_files)} | {desc} |")
        elif item.suffix == ".py":
            ds = _module_docstring(item)
            desc = ds.splitlines()[0][:80] if ds else "—"
            lines.append(f"| `{item.stem}` | 1 | {desc} |")

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────
# 8. SUMMARY REPORT
# ─────────────────────────────────────────────────────────────

def generate_summary() -> str:
    core_modules = len([d for d in (ROOT / "core").iterdir()
                        if d.is_dir() and not d.name.startswith("__")]) if (ROOT / "core").exists() else 0
    total_py = len(list(iter_py_files(ROOT)))
    plugins = len([d for d in (ROOT / "plugins").iterdir()
                   if d.is_dir()]) if (ROOT / "plugins").exists() else 0
    workflows_count = len(list((ROOT / "workflows").rglob("*.yaml"))) if (ROOT / "workflows").exists() else 0

    return f"""# BAEL System Summary

> Auto-generated on {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}

| Metric | Count |
|--------|-------|
| Core Modules | {core_modules} |
| Total Python Files | {total_py} |
| Plugins | {plugins} |
| Workflow Definitions | {workflows_count} |
| Generation Timestamp | {datetime.utcnow().isoformat()} |

## Quick Links

- [Folder Map](folder_map.md)
- [Capability Matrix](capability_matrix.md)
- [Plugin Inventory](plugin_inventory.md)
- [Workflow Inventory](workflow_inventory.md)
- [API Endpoints](api_inventory.md)
- [MCP Tools](mcp_inventory.md)
- [Integrations](integration_inventory.md)
"""


# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────

GENERATORS = {
    "folder_map.md": generate_folder_map,
    "capability_matrix.md": generate_capability_matrix,
    "plugin_inventory.md": generate_plugin_inventory,
    "workflow_inventory.md": generate_workflow_inventory,
    "api_inventory.md": generate_api_inventory,
    "mcp_inventory.md": generate_mcp_inventory,
    "integration_inventory.md": generate_integration_inventory,
    "summary.md": generate_summary,
}


def main() -> None:
    print(f"BAEL Documentation Generator\n{'='*40}")
    print(f"Output directory: {DOCS_OUT}\n")

    for filename, generator in GENERATORS.items():
        out_path = DOCS_OUT / filename
        print(f"  Generating {filename}...", end=" ")
        try:
            content = generator()
            out_path.write_text(content, encoding="utf-8")
            print(f"✓  ({len(content)} chars)")
        except Exception as exc:
            print(f"✗  ERROR: {exc}")

    # Write manifest JSON
    manifest = {
        "generated_at": datetime.utcnow().isoformat(),
        "files": list(GENERATORS.keys()),
        "output_dir": str(DOCS_OUT),
    }
    (DOCS_OUT / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )

    print(f"\n✅ Documentation generated → {DOCS_OUT}")


if __name__ == "__main__":
    main()

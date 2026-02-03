#!/usr/bin/env python3
"""
BAEL - Agent Marketplace
Plugin and agent marketplace for sharing and discovering extensions.

Features:
- Plugin registry
- Agent templates
- Dependency resolution
- Version management
- Rating system
- Installation manager
"""

import asyncio
import hashlib
import json
import logging
import os
import shutil
import zipfile
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import uuid4

logger = logging.getLogger(__name__)


# =============================================================================
# TYPES
# =============================================================================

class PackageType(Enum):
    """Package types."""
    PLUGIN = "plugin"
    AGENT = "agent"
    TOOL = "tool"
    PERSONA = "persona"
    WORKFLOW = "workflow"
    THEME = "theme"


class PackageStatus(Enum):
    """Package status."""
    DRAFT = "draft"
    PUBLISHED = "published"
    DEPRECATED = "deprecated"
    REMOVED = "removed"


class InstallStatus(Enum):
    """Installation status."""
    NOT_INSTALLED = "not_installed"
    INSTALLING = "installing"
    INSTALLED = "installed"
    UPDATING = "updating"
    FAILED = "failed"


@dataclass
class Version:
    """Semantic version."""
    major: int
    minor: int
    patch: int
    prerelease: str = ""
    build: str = ""

    @classmethod
    def parse(cls, version_str: str) -> "Version":
        """Parse version string."""
        # Remove v prefix if present
        version_str = version_str.lstrip("v")

        # Split main version and prerelease
        if "-" in version_str:
            main, prerelease = version_str.split("-", 1)
        else:
            main, prerelease = version_str, ""

        # Split prerelease and build
        if "+" in prerelease:
            prerelease, build = prerelease.split("+", 1)
        else:
            build = ""

        # Parse major.minor.patch
        parts = main.split(".")
        major = int(parts[0]) if len(parts) > 0 else 0
        minor = int(parts[1]) if len(parts) > 1 else 0
        patch = int(parts[2]) if len(parts) > 2 else 0

        return cls(major, minor, patch, prerelease, build)

    def __str__(self) -> str:
        version = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            version += f"-{self.prerelease}"
        if self.build:
            version += f"+{self.build}"
        return version

    def __lt__(self, other: "Version") -> bool:
        return (self.major, self.minor, self.patch) < (other.major, other.minor, other.patch)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Version):
            return False
        return (self.major, self.minor, self.patch) == (other.major, other.minor, other.patch)

    def __hash__(self) -> int:
        return hash((self.major, self.minor, self.patch))

    def satisfies(self, constraint: str) -> bool:
        """Check if version satisfies constraint."""
        if constraint.startswith("^"):
            # Caret: compatible with major version
            other = Version.parse(constraint[1:])
            return self.major == other.major and self >= other
        elif constraint.startswith("~"):
            # Tilde: compatible with minor version
            other = Version.parse(constraint[1:])
            return (self.major == other.major and
                    self.minor == other.minor and
                    self >= other)
        elif constraint.startswith(">="):
            return self >= Version.parse(constraint[2:])
        elif constraint.startswith("<="):
            return self <= Version.parse(constraint[2:])
        elif constraint.startswith(">"):
            return self > Version.parse(constraint[1:])
        elif constraint.startswith("<"):
            return self < Version.parse(constraint[1:])
        elif constraint.startswith("="):
            return self == Version.parse(constraint[1:])
        else:
            return self == Version.parse(constraint)


@dataclass
class Dependency:
    """Package dependency."""
    name: str
    version_constraint: str = "*"
    optional: bool = False


@dataclass
class Author:
    """Package author."""
    name: str
    email: str = ""
    url: str = ""


@dataclass
class Package:
    """Marketplace package."""
    id: str
    name: str
    version: Version
    type: PackageType
    description: str
    author: Author

    # Content
    entry_point: str = ""
    dependencies: List[Dependency] = field(default_factory=list)

    # Metadata
    keywords: List[str] = field(default_factory=list)
    license: str = "MIT"
    repository: str = ""
    homepage: str = ""

    # Assets
    icon_url: str = ""
    screenshots: List[str] = field(default_factory=list)
    readme: str = ""

    # Stats
    downloads: int = 0
    rating: float = 0.0
    rating_count: int = 0

    # Status
    status: PackageStatus = PackageStatus.PUBLISHED
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "version": str(self.version),
            "type": self.type.value,
            "description": self.description,
            "author": {
                "name": self.author.name,
                "email": self.author.email,
                "url": self.author.url
            },
            "entry_point": self.entry_point,
            "dependencies": [
                {"name": d.name, "version": d.version_constraint}
                for d in self.dependencies
            ],
            "keywords": self.keywords,
            "license": self.license,
            "repository": self.repository,
            "downloads": self.downloads,
            "rating": self.rating,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Package":
        return cls(
            id=data["id"],
            name=data["name"],
            version=Version.parse(data["version"]),
            type=PackageType(data["type"]),
            description=data["description"],
            author=Author(**data.get("author", {})),
            entry_point=data.get("entry_point", ""),
            dependencies=[
                Dependency(d["name"], d.get("version", "*"))
                for d in data.get("dependencies", [])
            ],
            keywords=data.get("keywords", []),
            license=data.get("license", "MIT"),
            repository=data.get("repository", ""),
            downloads=data.get("downloads", 0),
            rating=data.get("rating", 0.0),
            status=PackageStatus(data.get("status", "published")),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else datetime.now()
        )


# =============================================================================
# REGISTRY
# =============================================================================

class PackageRegistry(ABC):
    """Abstract package registry."""

    @abstractmethod
    async def search(
        self,
        query: str = "",
        type: PackageType = None,
        page: int = 1,
        limit: int = 20
    ) -> Tuple[List[Package], int]:
        """Search packages."""
        pass

    @abstractmethod
    async def get_package(self, package_id: str) -> Optional[Package]:
        """Get package by ID."""
        pass

    @abstractmethod
    async def get_versions(self, package_id: str) -> List[Version]:
        """Get all versions of a package."""
        pass

    @abstractmethod
    async def publish(self, package: Package, content: bytes) -> bool:
        """Publish a package."""
        pass

    @abstractmethod
    async def download(self, package_id: str, version: str = None) -> Optional[bytes]:
        """Download package content."""
        pass


class LocalRegistry(PackageRegistry):
    """Local file-based registry."""

    def __init__(self, path: str):
        self.path = Path(path)
        self.packages_dir = self.path / "packages"
        self.index_file = self.path / "index.json"
        self._packages: Dict[str, List[Package]] = {}
        self._load_index()

    def _load_index(self) -> None:
        """Load package index."""
        self.path.mkdir(parents=True, exist_ok=True)
        self.packages_dir.mkdir(exist_ok=True)

        if self.index_file.exists():
            with open(self.index_file) as f:
                data = json.load(f)
                for pkg_data in data.get("packages", []):
                    pkg = Package.from_dict(pkg_data)
                    if pkg.id not in self._packages:
                        self._packages[pkg.id] = []
                    self._packages[pkg.id].append(pkg)

    def _save_index(self) -> None:
        """Save package index."""
        packages = []
        for versions in self._packages.values():
            for pkg in versions:
                packages.append(pkg.to_dict())

        with open(self.index_file, "w") as f:
            json.dump({"packages": packages}, f, indent=2)

    async def search(
        self,
        query: str = "",
        type: PackageType = None,
        page: int = 1,
        limit: int = 20
    ) -> Tuple[List[Package], int]:
        """Search packages."""
        results = []

        for versions in self._packages.values():
            if not versions:
                continue

            # Get latest version
            pkg = max(versions, key=lambda p: p.version)

            # Filter by type
            if type and pkg.type != type:
                continue

            # Filter by query
            if query:
                query_lower = query.lower()
                if (query_lower not in pkg.name.lower() and
                    query_lower not in pkg.description.lower() and
                    not any(query_lower in kw.lower() for kw in pkg.keywords)):
                    continue

            results.append(pkg)

        # Sort by downloads
        results.sort(key=lambda p: p.downloads, reverse=True)

        # Paginate
        total = len(results)
        start = (page - 1) * limit
        end = start + limit

        return results[start:end], total

    async def get_package(self, package_id: str) -> Optional[Package]:
        """Get latest version of package."""
        versions = self._packages.get(package_id, [])
        if not versions:
            return None
        return max(versions, key=lambda p: p.version)

    async def get_versions(self, package_id: str) -> List[Version]:
        """Get all versions."""
        versions = self._packages.get(package_id, [])
        return sorted([p.version for p in versions], reverse=True)

    async def publish(self, package: Package, content: bytes) -> bool:
        """Publish package."""
        try:
            # Store content
            pkg_dir = self.packages_dir / package.id
            pkg_dir.mkdir(exist_ok=True)

            version_file = pkg_dir / f"{package.version}.zip"
            with open(version_file, "wb") as f:
                f.write(content)

            # Update index
            if package.id not in self._packages:
                self._packages[package.id] = []
            self._packages[package.id].append(package)

            self._save_index()

            return True

        except Exception as e:
            logger.error(f"Publish failed: {e}")
            return False

    async def download(self, package_id: str, version: str = None) -> Optional[bytes]:
        """Download package."""
        pkg_dir = self.packages_dir / package_id

        if not pkg_dir.exists():
            return None

        if version:
            version_file = pkg_dir / f"{version}.zip"
        else:
            # Get latest
            versions = await self.get_versions(package_id)
            if not versions:
                return None
            version_file = pkg_dir / f"{versions[0]}.zip"

        if not version_file.exists():
            return None

        with open(version_file, "rb") as f:
            return f.read()


class RemoteRegistry(PackageRegistry):
    """Remote HTTP registry."""

    def __init__(self, base_url: str, api_key: str = ""):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    async def _request(self, method: str, path: str, **kwargs) -> Any:
        """Make HTTP request."""
        import httpx

        headers = kwargs.pop("headers", {})
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        async with httpx.AsyncClient() as client:
            response = await client.request(
                method,
                f"{self.base_url}{path}",
                headers=headers,
                **kwargs
            )
            response.raise_for_status()
            return response

    async def search(
        self,
        query: str = "",
        type: PackageType = None,
        page: int = 1,
        limit: int = 20
    ) -> Tuple[List[Package], int]:
        """Search packages."""
        params = {"page": page, "limit": limit}
        if query:
            params["q"] = query
        if type:
            params["type"] = type.value

        response = await self._request("GET", "/packages", params=params)
        data = response.json()

        packages = [Package.from_dict(p) for p in data.get("packages", [])]
        total = data.get("total", len(packages))

        return packages, total

    async def get_package(self, package_id: str) -> Optional[Package]:
        """Get package."""
        try:
            response = await self._request("GET", f"/packages/{package_id}")
            return Package.from_dict(response.json())
        except:
            return None

    async def get_versions(self, package_id: str) -> List[Version]:
        """Get versions."""
        response = await self._request("GET", f"/packages/{package_id}/versions")
        return [Version.parse(v) for v in response.json().get("versions", [])]

    async def publish(self, package: Package, content: bytes) -> bool:
        """Publish package."""
        try:
            await self._request(
                "POST",
                "/packages",
                json=package.to_dict(),
                files={"content": ("package.zip", content)}
            )
            return True
        except:
            return False

    async def download(self, package_id: str, version: str = None) -> Optional[bytes]:
        """Download package."""
        try:
            path = f"/packages/{package_id}/download"
            if version:
                path += f"?version={version}"
            response = await self._request("GET", path)
            return response.content
        except:
            return None


# =============================================================================
# INSTALLATION MANAGER
# =============================================================================

@dataclass
class InstalledPackage:
    """Installed package info."""
    package: Package
    install_path: Path
    installed_at: datetime = field(default_factory=datetime.now)
    status: InstallStatus = InstallStatus.INSTALLED


class InstallationManager:
    """Manage package installation."""

    def __init__(
        self,
        install_dir: str,
        registry: PackageRegistry
    ):
        self.install_dir = Path(install_dir)
        self.registry = registry
        self.installed: Dict[str, InstalledPackage] = {}
        self._manifest_file = self.install_dir / "manifest.json"
        self._load_manifest()

    def _load_manifest(self) -> None:
        """Load installed packages manifest."""
        self.install_dir.mkdir(parents=True, exist_ok=True)

        if self._manifest_file.exists():
            with open(self._manifest_file) as f:
                data = json.load(f)
                for pkg_data in data.get("installed", []):
                    pkg = Package.from_dict(pkg_data["package"])
                    self.installed[pkg.id] = InstalledPackage(
                        package=pkg,
                        install_path=Path(pkg_data["install_path"]),
                        installed_at=datetime.fromisoformat(pkg_data["installed_at"]),
                        status=InstallStatus.INSTALLED
                    )

    def _save_manifest(self) -> None:
        """Save manifest."""
        data = {
            "installed": [
                {
                    "package": ip.package.to_dict(),
                    "install_path": str(ip.install_path),
                    "installed_at": ip.installed_at.isoformat()
                }
                for ip in self.installed.values()
            ]
        }

        with open(self._manifest_file, "w") as f:
            json.dump(data, f, indent=2)

    async def install(
        self,
        package_id: str,
        version: str = None,
        force: bool = False
    ) -> Tuple[bool, str]:
        """Install a package."""
        # Check if already installed
        if package_id in self.installed and not force:
            return False, "Package already installed"

        # Get package info
        package = await self.registry.get_package(package_id)
        if not package:
            return False, "Package not found"

        # Download content
        content = await self.registry.download(package_id, version)
        if not content:
            return False, "Failed to download package"

        # Install
        try:
            install_path = self.install_dir / package.type.value / package.id
            install_path.mkdir(parents=True, exist_ok=True)

            # Extract content
            import io
            with zipfile.ZipFile(io.BytesIO(content)) as zf:
                zf.extractall(install_path)

            # Record installation
            self.installed[package.id] = InstalledPackage(
                package=package,
                install_path=install_path
            )

            self._save_manifest()

            logger.info(f"Installed {package.name} v{package.version}")
            return True, f"Installed {package.name}"

        except Exception as e:
            logger.error(f"Installation failed: {e}")
            return False, str(e)

    async def uninstall(self, package_id: str) -> Tuple[bool, str]:
        """Uninstall a package."""
        if package_id not in self.installed:
            return False, "Package not installed"

        installed = self.installed[package_id]

        try:
            # Remove files
            if installed.install_path.exists():
                shutil.rmtree(installed.install_path)

            # Update manifest
            del self.installed[package_id]
            self._save_manifest()

            logger.info(f"Uninstalled {installed.package.name}")
            return True, f"Uninstalled {installed.package.name}"

        except Exception as e:
            logger.error(f"Uninstall failed: {e}")
            return False, str(e)

    async def update(self, package_id: str) -> Tuple[bool, str]:
        """Update a package to latest version."""
        if package_id not in self.installed:
            return False, "Package not installed"

        current = self.installed[package_id].package

        # Get latest version
        latest = await self.registry.get_package(package_id)
        if not latest:
            return False, "Package not found in registry"

        if latest.version <= current.version:
            return False, "Already at latest version"

        # Install new version
        return await self.install(package_id, str(latest.version), force=True)

    async def update_all(self) -> Dict[str, Tuple[bool, str]]:
        """Update all packages."""
        results = {}
        for package_id in list(self.installed.keys()):
            results[package_id] = await self.update(package_id)
        return results

    def list_installed(self, type: PackageType = None) -> List[InstalledPackage]:
        """List installed packages."""
        packages = list(self.installed.values())

        if type:
            packages = [p for p in packages if p.package.type == type]

        return sorted(packages, key=lambda p: p.package.name)


# =============================================================================
# DEPENDENCY RESOLVER
# =============================================================================

class DependencyResolver:
    """Resolve package dependencies."""

    def __init__(self, registry: PackageRegistry, installed: Dict[str, InstalledPackage]):
        self.registry = registry
        self.installed = installed

    async def resolve(self, package: Package) -> List[Package]:
        """Resolve all dependencies for a package."""
        resolved: List[Package] = []
        seen: Set[str] = set()

        await self._resolve_recursive(package, resolved, seen)

        return resolved

    async def _resolve_recursive(
        self,
        package: Package,
        resolved: List[Package],
        seen: Set[str]
    ) -> None:
        """Recursively resolve dependencies."""
        if package.id in seen:
            return
        seen.add(package.id)

        for dep in package.dependencies:
            # Skip optional if already have it
            if dep.optional and dep.name in self.installed:
                continue

            # Get dependency package
            dep_pkg = await self.registry.get_package(dep.name)
            if not dep_pkg:
                if not dep.optional:
                    raise ValueError(f"Missing required dependency: {dep.name}")
                continue

            # Check version constraint
            if not dep_pkg.version.satisfies(dep.version_constraint):
                raise ValueError(
                    f"Dependency {dep.name} version {dep_pkg.version} "
                    f"does not satisfy {dep.version_constraint}"
                )

            # Resolve dependencies of dependency
            await self._resolve_recursive(dep_pkg, resolved, seen)

        resolved.append(package)


# =============================================================================
# PACKAGE BUILDER
# =============================================================================

class PackageBuilder:
    """Build packages for publishing."""

    def __init__(self, source_dir: str):
        self.source_dir = Path(source_dir)
        self.manifest_file = self.source_dir / "bael.json"

    def load_manifest(self) -> Dict[str, Any]:
        """Load package manifest."""
        if not self.manifest_file.exists():
            raise FileNotFoundError("bael.json not found")

        with open(self.manifest_file) as f:
            return json.load(f)

    def build(self, output_dir: str = None) -> Tuple[Package, bytes]:
        """Build package."""
        manifest = self.load_manifest()

        # Create package
        package = Package(
            id=manifest["name"],
            name=manifest.get("display_name", manifest["name"]),
            version=Version.parse(manifest["version"]),
            type=PackageType(manifest.get("type", "plugin")),
            description=manifest.get("description", ""),
            author=Author(
                name=manifest.get("author", {}).get("name", ""),
                email=manifest.get("author", {}).get("email", "")
            ),
            entry_point=manifest.get("main", ""),
            dependencies=[
                Dependency(name, ver)
                for name, ver in manifest.get("dependencies", {}).items()
            ],
            keywords=manifest.get("keywords", []),
            license=manifest.get("license", "MIT"),
            repository=manifest.get("repository", "")
        )

        # Create zip
        import io
        buffer = io.BytesIO()

        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for file in self.source_dir.rglob("*"):
                if file.is_file():
                    # Skip common exclusions
                    rel_path = file.relative_to(self.source_dir)
                    if any(p.startswith(".") or p == "__pycache__" for p in rel_path.parts):
                        continue
                    zf.write(file, rel_path)

        content = buffer.getvalue()

        # Save to output if specified
        if output_dir:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            output_file = output_path / f"{package.id}-{package.version}.zip"
            with open(output_file, "wb") as f:
                f.write(content)

        return package, content


# =============================================================================
# MARKETPLACE CLIENT
# =============================================================================

class MarketplaceClient:
    """High-level marketplace client."""

    def __init__(
        self,
        install_dir: str = "~/.bael/packages",
        registry_url: str = None
    ):
        self.install_dir = Path(install_dir).expanduser()

        # Use local registry by default
        if registry_url:
            self.registry = RemoteRegistry(registry_url)
        else:
            self.registry = LocalRegistry(self.install_dir / "registry")

        self.installer = InstallationManager(
            str(self.install_dir / "installed"),
            self.registry
        )

    async def search(self, query: str = "", type: str = None) -> List[Package]:
        """Search marketplace."""
        pkg_type = PackageType(type) if type else None
        packages, _ = await self.registry.search(query, pkg_type)
        return packages

    async def install(self, package_name: str, version: str = None) -> Tuple[bool, str]:
        """Install package."""
        # Resolve dependencies
        package = await self.registry.get_package(package_name)
        if not package:
            return False, "Package not found"

        resolver = DependencyResolver(self.registry, self.installer.installed)

        try:
            deps = await resolver.resolve(package)
        except ValueError as e:
            return False, str(e)

        # Install dependencies first
        for dep in deps[:-1]:  # Exclude main package
            if dep.id not in self.installer.installed:
                success, msg = await self.installer.install(dep.id)
                if not success:
                    return False, f"Failed to install dependency {dep.name}: {msg}"

        # Install main package
        return await self.installer.install(package_name, version)

    async def uninstall(self, package_name: str) -> Tuple[bool, str]:
        """Uninstall package."""
        return await self.installer.uninstall(package_name)

    async def update(self, package_name: str = None) -> Dict[str, Tuple[bool, str]]:
        """Update package(s)."""
        if package_name:
            return {package_name: await self.installer.update(package_name)}
        return await self.installer.update_all()

    def list_installed(self) -> List[InstalledPackage]:
        """List installed packages."""
        return self.installer.list_installed()

    async def publish(self, source_dir: str) -> Tuple[bool, str]:
        """Publish package from source directory."""
        try:
            builder = PackageBuilder(source_dir)
            package, content = builder.build()

            success = await self.registry.publish(package, content)
            if success:
                return True, f"Published {package.name} v{package.version}"
            return False, "Publish failed"

        except Exception as e:
            return False, str(e)


# =============================================================================
# CLI
# =============================================================================

async def cli_main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="BAEL Package Manager")
    subparsers = parser.add_subparsers(dest="command")

    # Search
    search_parser = subparsers.add_parser("search", help="Search packages")
    search_parser.add_argument("query", nargs="?", default="")
    search_parser.add_argument("--type", "-t", help="Package type")

    # Install
    install_parser = subparsers.add_parser("install", help="Install package")
    install_parser.add_argument("package", help="Package name")
    install_parser.add_argument("--version", "-v", help="Specific version")

    # Uninstall
    uninstall_parser = subparsers.add_parser("uninstall", help="Uninstall package")
    uninstall_parser.add_argument("package", help="Package name")

    # Update
    update_parser = subparsers.add_parser("update", help="Update package(s)")
    update_parser.add_argument("package", nargs="?", help="Package name (or all)")

    # List
    subparsers.add_parser("list", help="List installed packages")

    # Publish
    publish_parser = subparsers.add_parser("publish", help="Publish package")
    publish_parser.add_argument("path", default=".", nargs="?", help="Source directory")

    args = parser.parse_args()

    client = MarketplaceClient()

    if args.command == "search":
        packages = await client.search(args.query, args.type)
        for pkg in packages:
            print(f"{pkg.name} ({pkg.type.value}) v{pkg.version}")
            print(f"  {pkg.description}")
            print(f"  Downloads: {pkg.downloads} | Rating: {pkg.rating:.1f}")
            print()

    elif args.command == "install":
        success, msg = await client.install(args.package, args.version)
        print(msg)

    elif args.command == "uninstall":
        success, msg = await client.uninstall(args.package)
        print(msg)

    elif args.command == "update":
        results = await client.update(args.package)
        for pkg, (success, msg) in results.items():
            status = "✓" if success else "✗"
            print(f"{status} {pkg}: {msg}")

    elif args.command == "list":
        packages = client.list_installed()
        for ip in packages:
            print(f"{ip.package.name} v{ip.package.version}")
            print(f"  Type: {ip.package.type.value}")
            print(f"  Installed: {ip.installed_at.strftime('%Y-%m-%d')}")
            print()

    elif args.command == "publish":
        success, msg = await client.publish(args.path)
        print(msg)


if __name__ == "__main__":
    asyncio.run(cli_main())

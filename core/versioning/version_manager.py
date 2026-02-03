#!/usr/bin/env python3
"""
BAEL - Semantic Version Manager
Automatic versioning and changelog generation.

Features:
- Semantic versioning (SemVer)
- Automatic version bumping
- Changelog generation
- Git tag management
- Version file updates
"""

import asyncio
import json
import logging
import os
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# TYPES
# =============================================================================

class BumpType(Enum):
    """Version bump types."""
    MAJOR = "major"
    MINOR = "minor"
    PATCH = "patch"
    PRERELEASE = "prerelease"
    BUILD = "build"


class CommitType(Enum):
    """Conventional commit types."""
    FEAT = "feat"
    FIX = "fix"
    DOCS = "docs"
    STYLE = "style"
    REFACTOR = "refactor"
    PERF = "perf"
    TEST = "test"
    BUILD = "build"
    CI = "ci"
    CHORE = "chore"
    REVERT = "revert"
    BREAKING = "breaking"


@dataclass
class Version:
    """Semantic version."""
    major: int = 0
    minor: int = 0
    patch: int = 0
    prerelease: Optional[str] = None
    build: Optional[str] = None

    def __str__(self) -> str:
        version = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            version += f"-{self.prerelease}"
        if self.build:
            version += f"+{self.build}"
        return version

    def __lt__(self, other: "Version") -> bool:
        if self.major != other.major:
            return self.major < other.major
        if self.minor != other.minor:
            return self.minor < other.minor
        if self.patch != other.patch:
            return self.patch < other.patch
        # Prerelease versions have lower precedence
        if self.prerelease and not other.prerelease:
            return True
        if not self.prerelease and other.prerelease:
            return False
        return False

    @classmethod
    def parse(cls, version_str: str) -> "Version":
        """Parse version string."""
        # Remove leading 'v' if present
        version_str = version_str.lstrip('v')

        # Split build metadata
        build = None
        if '+' in version_str:
            version_str, build = version_str.split('+', 1)

        # Split prerelease
        prerelease = None
        if '-' in version_str:
            version_str, prerelease = version_str.split('-', 1)

        # Parse main version
        parts = version_str.split('.')
        major = int(parts[0]) if len(parts) > 0 else 0
        minor = int(parts[1]) if len(parts) > 1 else 0
        patch = int(parts[2]) if len(parts) > 2 else 0

        return cls(
            major=major,
            minor=minor,
            patch=patch,
            prerelease=prerelease,
            build=build
        )

    def bump(self, bump_type: BumpType, prerelease_id: str = None) -> "Version":
        """Create bumped version."""
        if bump_type == BumpType.MAJOR:
            return Version(self.major + 1, 0, 0)
        elif bump_type == BumpType.MINOR:
            return Version(self.major, self.minor + 1, 0)
        elif bump_type == BumpType.PATCH:
            return Version(self.major, self.minor, self.patch + 1)
        elif bump_type == BumpType.PRERELEASE:
            if self.prerelease:
                # Increment prerelease number
                match = re.match(r'(.+?)(\d+)$', self.prerelease)
                if match:
                    prefix = match.group(1)
                    num = int(match.group(2)) + 1
                    prerelease = f"{prefix}{num}"
                else:
                    prerelease = f"{self.prerelease}.1"
            else:
                prerelease = prerelease_id or "alpha.1"
            return Version(self.major, self.minor, self.patch, prerelease)
        elif bump_type == BumpType.BUILD:
            build = datetime.now().strftime("%Y%m%d%H%M%S")
            return Version(self.major, self.minor, self.patch, self.prerelease, build)
        else:
            return self


@dataclass
class Commit:
    """Git commit information."""
    hash: str
    short_hash: str
    message: str
    body: str = ""
    author: str = ""
    date: Optional[datetime] = None
    type: Optional[CommitType] = None
    scope: Optional[str] = None
    description: str = ""
    breaking: bool = False

    @classmethod
    def parse_conventional(cls, message: str) -> Tuple[Optional[CommitType], Optional[str], str, bool]:
        """Parse conventional commit message."""
        # Pattern: type(scope)!: description
        pattern = r'^(\w+)(?:\(([^)]+)\))?(!)?:\s*(.+)$'
        match = re.match(pattern, message.split('\n')[0])

        if not match:
            return None, None, message, False

        type_str, scope, breaking, description = match.groups()

        try:
            commit_type = CommitType(type_str.lower())
        except ValueError:
            commit_type = None

        return commit_type, scope, description, bool(breaking)


@dataclass
class ChangelogEntry:
    """Changelog entry."""
    version: Version
    date: datetime
    commits: List[Commit]
    breaking_changes: List[str] = field(default_factory=list)

    def to_markdown(self) -> str:
        """Generate markdown changelog entry."""
        lines = [
            f"## [{self.version}] - {self.date.strftime('%Y-%m-%d')}",
            ""
        ]

        # Breaking changes
        if self.breaking_changes:
            lines.append("### ⚠️ Breaking Changes")
            lines.append("")
            for change in self.breaking_changes:
                lines.append(f"- {change}")
            lines.append("")

        # Group by type
        by_type: Dict[CommitType, List[Commit]] = {}
        for commit in self.commits:
            if commit.type:
                if commit.type not in by_type:
                    by_type[commit.type] = []
                by_type[commit.type].append(commit)

        type_titles = {
            CommitType.FEAT: "✨ Features",
            CommitType.FIX: "🐛 Bug Fixes",
            CommitType.PERF: "⚡ Performance",
            CommitType.DOCS: "📚 Documentation",
            CommitType.REFACTOR: "♻️ Refactoring",
            CommitType.TEST: "✅ Tests",
            CommitType.BUILD: "📦 Build",
            CommitType.CI: "👷 CI",
            CommitType.CHORE: "🔧 Chores"
        }

        for commit_type in [CommitType.FEAT, CommitType.FIX, CommitType.PERF,
                          CommitType.DOCS, CommitType.REFACTOR, CommitType.TEST,
                          CommitType.BUILD, CommitType.CI, CommitType.CHORE]:
            if commit_type in by_type:
                lines.append(f"### {type_titles.get(commit_type, commit_type.value)}")
                lines.append("")
                for commit in by_type[commit_type]:
                    scope = f"**{commit.scope}:** " if commit.scope else ""
                    lines.append(f"- {scope}{commit.description} ({commit.short_hash})")
                lines.append("")

        return "\n".join(lines)


# =============================================================================
# VERSION MANAGER
# =============================================================================

class VersionManager:
    """Manage project versions."""

    def __init__(self, project_dir: str = "."):
        self.project_dir = Path(project_dir)
        self._current_version: Optional[Version] = None

    def get_version(self) -> Version:
        """Get current version from various sources."""
        # Try VERSION file
        version_file = self.project_dir / "VERSION"
        if version_file.exists():
            return Version.parse(version_file.read_text().strip())

        # Try package.json
        package_json = self.project_dir / "package.json"
        if package_json.exists():
            with open(package_json) as f:
                data = json.load(f)
                if "version" in data:
                    return Version.parse(data["version"])

        # Try pyproject.toml
        pyproject = self.project_dir / "pyproject.toml"
        if pyproject.exists():
            content = pyproject.read_text()
            match = re.search(r'version\s*=\s*["\']([^"\']+)["\']', content)
            if match:
                return Version.parse(match.group(1))

        # Try setup.py
        setup_py = self.project_dir / "setup.py"
        if setup_py.exists():
            content = setup_py.read_text()
            match = re.search(r'version\s*=\s*["\']([^"\']+)["\']', content)
            if match:
                return Version.parse(match.group(1))

        # Try git tags
        try:
            result = subprocess.run(
                ["git", "describe", "--tags", "--abbrev=0"],
                cwd=self.project_dir,
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                return Version.parse(result.stdout.strip())
        except Exception:
            pass

        return Version(0, 1, 0)

    def set_version(self, version: Version) -> Dict[str, bool]:
        """Update version in all version files."""
        results = {}
        version_str = str(version)

        # VERSION file
        version_file = self.project_dir / "VERSION"
        try:
            version_file.write_text(version_str + "\n")
            results["VERSION"] = True
        except Exception as e:
            logger.error(f"Failed to update VERSION: {e}")
            results["VERSION"] = False

        # package.json
        package_json = self.project_dir / "package.json"
        if package_json.exists():
            try:
                with open(package_json) as f:
                    data = json.load(f)
                data["version"] = version_str
                with open(package_json, 'w') as f:
                    json.dump(data, f, indent=2)
                results["package.json"] = True
            except Exception as e:
                logger.error(f"Failed to update package.json: {e}")
                results["package.json"] = False

        # pyproject.toml
        pyproject = self.project_dir / "pyproject.toml"
        if pyproject.exists():
            try:
                content = pyproject.read_text()
                content = re.sub(
                    r'(version\s*=\s*["\'])[^"\']+(["\'])',
                    f'\\g<1>{version_str}\\g<2>',
                    content
                )
                pyproject.write_text(content)
                results["pyproject.toml"] = True
            except Exception as e:
                logger.error(f"Failed to update pyproject.toml: {e}")
                results["pyproject.toml"] = False

        # __version__ in Python files
        for init_file in self.project_dir.rglob("__init__.py"):
            try:
                content = init_file.read_text()
                if "__version__" in content:
                    content = re.sub(
                        r'(__version__\s*=\s*["\'])[^"\']+(["\'])',
                        f'\\g<1>{version_str}\\g<2>',
                        content
                    )
                    init_file.write_text(content)
                    results[str(init_file)] = True
            except Exception:
                pass

        return results

    def get_commits_since(self, since_tag: str = None) -> List[Commit]:
        """Get commits since a tag or from beginning."""
        try:
            if since_tag:
                cmd = ["git", "log", f"{since_tag}..HEAD", "--pretty=format:%H|%h|%s|%b|%an|%ai"]
            else:
                cmd = ["git", "log", "--pretty=format:%H|%h|%s|%b|%an|%ai"]

            result = subprocess.run(
                cmd,
                cwd=self.project_dir,
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                return []

            commits = []
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue

                parts = line.split('|')
                if len(parts) >= 6:
                    hash_full, hash_short, subject, body, author, date_str = parts[:6]

                    # Parse conventional commit
                    commit_type, scope, description, breaking = Commit.parse_conventional(subject)

                    # Check body for breaking changes
                    if "BREAKING CHANGE:" in body:
                        breaking = True

                    commit = Commit(
                        hash=hash_full,
                        short_hash=hash_short,
                        message=subject,
                        body=body,
                        author=author,
                        date=datetime.fromisoformat(date_str.split(' ')[0]) if date_str else None,
                        type=commit_type,
                        scope=scope,
                        description=description,
                        breaking=breaking
                    )
                    commits.append(commit)

            return commits

        except Exception as e:
            logger.error(f"Failed to get commits: {e}")
            return []

    def analyze_commits(self, commits: List[Commit]) -> BumpType:
        """Analyze commits to determine bump type."""
        has_breaking = any(c.breaking for c in commits)
        has_feat = any(c.type == CommitType.FEAT for c in commits)
        has_fix = any(c.type == CommitType.FIX for c in commits)

        if has_breaking:
            return BumpType.MAJOR
        elif has_feat:
            return BumpType.MINOR
        elif has_fix:
            return BumpType.PATCH
        else:
            return BumpType.PATCH

    def create_tag(self, version: Version, message: str = None) -> bool:
        """Create git tag for version."""
        tag = f"v{version}"
        msg = message or f"Release {version}"

        try:
            result = subprocess.run(
                ["git", "tag", "-a", tag, "-m", msg],
                cwd=self.project_dir,
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Failed to create tag: {e}")
            return False

    def push_tag(self, version: Version) -> bool:
        """Push tag to remote."""
        tag = f"v{version}"

        try:
            result = subprocess.run(
                ["git", "push", "origin", tag],
                cwd=self.project_dir,
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Failed to push tag: {e}")
            return False


# =============================================================================
# CHANGELOG GENERATOR
# =============================================================================

class ChangelogGenerator:
    """Generate changelogs from commits."""

    def __init__(self, version_manager: VersionManager):
        self.version_manager = version_manager

    def generate_entry(
        self,
        version: Version,
        commits: List[Commit]
    ) -> ChangelogEntry:
        """Generate changelog entry."""
        breaking_changes = []

        for commit in commits:
            if commit.breaking:
                # Extract breaking change description
                if "BREAKING CHANGE:" in commit.body:
                    match = re.search(r'BREAKING CHANGE:\s*(.+)', commit.body)
                    if match:
                        breaking_changes.append(match.group(1))
                    else:
                        breaking_changes.append(commit.description)
                else:
                    breaking_changes.append(commit.description)

        return ChangelogEntry(
            version=version,
            date=datetime.now(),
            commits=commits,
            breaking_changes=breaking_changes
        )

    def update_changelog(
        self,
        entry: ChangelogEntry,
        changelog_file: str = "CHANGELOG.md"
    ) -> None:
        """Update changelog file with new entry."""
        changelog_path = self.version_manager.project_dir / changelog_file

        new_content = entry.to_markdown()

        if changelog_path.exists():
            existing = changelog_path.read_text()

            # Find insertion point after header
            header_pattern = r'^#\s+Changelog\s*\n'
            match = re.match(header_pattern, existing, re.MULTILINE)

            if match:
                insert_pos = match.end()
                updated = (
                    existing[:insert_pos] +
                    "\n" + new_content + "\n" +
                    existing[insert_pos:]
                )
            else:
                updated = f"# Changelog\n\n{new_content}\n\n{existing}"
        else:
            updated = f"# Changelog\n\n{new_content}"

        changelog_path.write_text(updated)
        logger.info(f"Updated {changelog_file}")

    def generate_full(
        self,
        include_unreleased: bool = True
    ) -> str:
        """Generate complete changelog."""
        lines = ["# Changelog", ""]

        # Get all tags
        try:
            result = subprocess.run(
                ["git", "tag", "-l", "--sort=-version:refname"],
                cwd=self.version_manager.project_dir,
                capture_output=True,
                text=True
            )
            tags = [t.strip() for t in result.stdout.split('\n') if t.strip()]
        except Exception:
            tags = []

        # Unreleased changes
        if include_unreleased and tags:
            commits = self.version_manager.get_commits_since(tags[0])
            if commits:
                lines.append("## [Unreleased]")
                lines.append("")
                for commit in commits[:10]:
                    if commit.type:
                        lines.append(f"- {commit.description}")
                lines.append("")

        # Released versions
        for i, tag in enumerate(tags):
            try:
                version = Version.parse(tag)
            except:
                continue

            since_tag = tags[i + 1] if i + 1 < len(tags) else None
            commits = self.version_manager.get_commits_since(since_tag)

            # Filter to commits before this tag
            # (simplified - would need proper date filtering)

            entry = self.generate_entry(version, commits[:20])
            lines.append(entry.to_markdown())

        return "\n".join(lines)


# =============================================================================
# CLI
# =============================================================================

async def main():
    """CLI main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="BAEL Version Manager")
    subparsers = parser.add_subparsers(dest="command")

    # Get command
    subparsers.add_parser("get", help="Get current version")

    # Bump command
    bump_parser = subparsers.add_parser("bump", help="Bump version")
    bump_parser.add_argument("type", choices=["major", "minor", "patch", "prerelease"])
    bump_parser.add_argument("--prerelease-id", default="alpha")
    bump_parser.add_argument("--tag", action="store_true", help="Create git tag")
    bump_parser.add_argument("--push", action="store_true", help="Push tag")

    # Set command
    set_parser = subparsers.add_parser("set", help="Set specific version")
    set_parser.add_argument("version")

    # Changelog command
    changelog_parser = subparsers.add_parser("changelog", help="Generate changelog")
    changelog_parser.add_argument("--output", "-o", default="CHANGELOG.md")

    # Release command
    release_parser = subparsers.add_parser("release", help="Full release workflow")
    release_parser.add_argument("--type", choices=["major", "minor", "patch", "auto"], default="auto")
    release_parser.add_argument("--dry-run", action="store_true")

    args = parser.parse_args()

    manager = VersionManager()
    changelog = ChangelogGenerator(manager)

    if args.command == "get":
        print(manager.get_version())

    elif args.command == "bump":
        current = manager.get_version()
        bump_type = BumpType(args.type)

        if bump_type == BumpType.PRERELEASE:
            new_version = current.bump(bump_type, args.prerelease_id)
        else:
            new_version = current.bump(bump_type)

        manager.set_version(new_version)
        print(f"Bumped version: {current} -> {new_version}")

        if args.tag:
            if manager.create_tag(new_version):
                print(f"Created tag: v{new_version}")

        if args.push:
            if manager.push_tag(new_version):
                print(f"Pushed tag: v{new_version}")

    elif args.command == "set":
        version = Version.parse(args.version)
        results = manager.set_version(version)
        print(f"Set version to {version}")
        for file, success in results.items():
            status = "✓" if success else "✗"
            print(f"  {status} {file}")

    elif args.command == "changelog":
        content = changelog.generate_full()
        Path(args.output).write_text(content)
        print(f"Generated changelog: {args.output}")

    elif args.command == "release":
        current = manager.get_version()

        # Determine bump type
        if args.type == "auto":
            commits = manager.get_commits_since(f"v{current}")
            bump_type = manager.analyze_commits(commits)
        else:
            bump_type = BumpType(args.type)
            commits = manager.get_commits_since(f"v{current}")

        new_version = current.bump(bump_type)

        print(f"Release: {current} -> {new_version} ({bump_type.value})")
        print(f"Commits: {len(commits)}")

        if args.dry_run:
            print("Dry run - no changes made")
            return

        # Update version
        manager.set_version(new_version)
        print("✓ Updated version files")

        # Generate changelog
        entry = changelog.generate_entry(new_version, commits)
        changelog.update_changelog(entry)
        print("✓ Updated changelog")

        # Create tag
        if manager.create_tag(new_version):
            print(f"✓ Created tag v{new_version}")

        print(f"\nRelease {new_version} prepared!")
        print("Run 'git push && git push --tags' to publish")

    else:
        parser.print_help()


if __name__ == "__main__":
    asyncio.run(main())

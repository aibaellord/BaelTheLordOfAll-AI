#!/usr/bin/env python3
"""
BAEL - Diff Engine
Comprehensive text comparison and difference analysis system.

Features:
- Line-by-line diff
- Character-level diff
- Word-level diff
- Unified diff format
- Side-by-side diff
- Three-way merge
- Patch generation and application
- Similarity calculation
- Change statistics
- Semantic diff
"""

import asyncio
import difflib
import hashlib
import json
import logging
import re
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import (Any, Callable, Dict, Generic, Iterator, List, Optional,
                    Sequence, Set, Tuple, Type, TypeVar, Union)

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS
# =============================================================================

class ChangeType(Enum):
    """Type of change."""
    EQUAL = "equal"
    INSERT = "insert"
    DELETE = "delete"
    REPLACE = "replace"


class DiffMode(Enum):
    """Diff mode."""
    LINE = "line"
    WORD = "word"
    CHARACTER = "character"


class OutputFormat(Enum):
    """Output format."""
    UNIFIED = "unified"
    CONTEXT = "context"
    SIDE_BY_SIDE = "side_by_side"
    HTML = "html"
    JSON = "json"


class MergeResult(Enum):
    """Merge result type."""
    CLEAN = "clean"
    CONFLICT = "conflict"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class Change:
    """Single change in a diff."""
    type: ChangeType
    old_start: int
    old_end: int
    new_start: int
    new_end: int
    old_content: List[str] = field(default_factory=list)
    new_content: List[str] = field(default_factory=list)

    @property
    def old_count(self) -> int:
        return self.old_end - self.old_start

    @property
    def new_count(self) -> int:
        return self.new_end - self.new_start


@dataclass
class Hunk:
    """A hunk in a unified diff."""
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    changes: List[Change] = field(default_factory=list)
    header: str = ""


@dataclass
class DiffResult:
    """Result of a diff operation."""
    changes: List[Change]
    old_lines: List[str]
    new_lines: List[str]
    hunks: List[Hunk] = field(default_factory=list)
    similarity: float = 0.0

    @property
    def has_changes(self) -> bool:
        return any(c.type != ChangeType.EQUAL for c in self.changes)

    @property
    def insertions(self) -> int:
        return sum(1 for c in self.changes if c.type == ChangeType.INSERT)

    @property
    def deletions(self) -> int:
        return sum(1 for c in self.changes if c.type == ChangeType.DELETE)


@dataclass
class PatchHeader:
    """Patch file header."""
    old_file: str = ""
    new_file: str = ""
    old_timestamp: Optional[str] = None
    new_timestamp: Optional[str] = None


@dataclass
class Patch:
    """A patch that can be applied to text."""
    header: PatchHeader
    hunks: List[Hunk]

    def to_unified(self) -> str:
        """Convert to unified diff format."""
        lines = []

        if self.header.old_file:
            lines.append(f"--- {self.header.old_file}")
        if self.header.new_file:
            lines.append(f"+++ {self.header.new_file}")

        for hunk in self.hunks:
            lines.append(f"@@ -{hunk.old_start},{hunk.old_count} +{hunk.new_start},{hunk.new_count} @@")

            for change in hunk.changes:
                if change.type == ChangeType.EQUAL:
                    for line in change.old_content:
                        lines.append(f" {line}")
                elif change.type == ChangeType.DELETE:
                    for line in change.old_content:
                        lines.append(f"-{line}")
                elif change.type == ChangeType.INSERT:
                    for line in change.new_content:
                        lines.append(f"+{line}")
                elif change.type == ChangeType.REPLACE:
                    for line in change.old_content:
                        lines.append(f"-{line}")
                    for line in change.new_content:
                        lines.append(f"+{line}")

        return '\n'.join(lines)


@dataclass
class MergeConflict:
    """Merge conflict information."""
    line: int
    base: List[str]
    left: List[str]
    right: List[str]


@dataclass
class MergeOutput:
    """Result of a three-way merge."""
    result: MergeResult
    merged: List[str]
    conflicts: List[MergeConflict] = field(default_factory=list)


@dataclass
class DiffStats:
    """Diff statistics."""
    lines_added: int = 0
    lines_deleted: int = 0
    lines_modified: int = 0
    lines_unchanged: int = 0
    similarity: float = 0.0

    @property
    def total_changes(self) -> int:
        return self.lines_added + self.lines_deleted + self.lines_modified


# =============================================================================
# SEQUENCE MATCHER
# =============================================================================

class SequenceMatcher:
    """Custom sequence matcher for diff operations."""

    def __init__(
        self,
        a: Sequence,
        b: Sequence,
        junk: Optional[Callable] = None
    ):
        self.a = a
        self.b = b
        self.junk = junk or (lambda x: False)
        self._matching_blocks: Optional[List[Tuple[int, int, int]]] = None
        self._opcodes: Optional[List[Tuple[str, int, int, int, int]]] = None

    def get_matching_blocks(self) -> List[Tuple[int, int, int]]:
        """Get matching blocks between sequences."""
        if self._matching_blocks is not None:
            return self._matching_blocks

        # Use difflib's implementation
        matcher = difflib.SequenceMatcher(self.junk, self.a, self.b)
        self._matching_blocks = matcher.get_matching_blocks()

        return self._matching_blocks

    def get_opcodes(self) -> List[Tuple[str, int, int, int, int]]:
        """Get opcodes for transforming a to b."""
        if self._opcodes is not None:
            return self._opcodes

        matcher = difflib.SequenceMatcher(self.junk, self.a, self.b)
        self._opcodes = matcher.get_opcodes()

        return self._opcodes

    def ratio(self) -> float:
        """Calculate similarity ratio."""
        matcher = difflib.SequenceMatcher(self.junk, self.a, self.b)
        return matcher.ratio()

    def quick_ratio(self) -> float:
        """Quick similarity estimate."""
        matcher = difflib.SequenceMatcher(self.junk, self.a, self.b)
        return matcher.quick_ratio()


# =============================================================================
# DIFF ALGORITHMS
# =============================================================================

class DiffAlgorithm(ABC):
    """Abstract diff algorithm."""

    @abstractmethod
    def diff(
        self,
        old: List[str],
        new: List[str]
    ) -> List[Change]:
        """Compute differences."""
        pass


class LineDiff(DiffAlgorithm):
    """Line-by-line diff."""

    def diff(self, old: List[str], new: List[str]) -> List[Change]:
        matcher = SequenceMatcher(old, new)
        changes = []

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'equal':
                changes.append(Change(
                    type=ChangeType.EQUAL,
                    old_start=i1,
                    old_end=i2,
                    new_start=j1,
                    new_end=j2,
                    old_content=old[i1:i2],
                    new_content=new[j1:j2]
                ))
            elif tag == 'delete':
                changes.append(Change(
                    type=ChangeType.DELETE,
                    old_start=i1,
                    old_end=i2,
                    new_start=j1,
                    new_end=j2,
                    old_content=old[i1:i2]
                ))
            elif tag == 'insert':
                changes.append(Change(
                    type=ChangeType.INSERT,
                    old_start=i1,
                    old_end=i2,
                    new_start=j1,
                    new_end=j2,
                    new_content=new[j1:j2]
                ))
            elif tag == 'replace':
                changes.append(Change(
                    type=ChangeType.REPLACE,
                    old_start=i1,
                    old_end=i2,
                    new_start=j1,
                    new_end=j2,
                    old_content=old[i1:i2],
                    new_content=new[j1:j2]
                ))

        return changes


class WordDiff(DiffAlgorithm):
    """Word-level diff."""

    def diff(self, old: List[str], new: List[str]) -> List[Change]:
        # Tokenize into words
        old_words = self._tokenize('\n'.join(old))
        new_words = self._tokenize('\n'.join(new))

        matcher = SequenceMatcher(old_words, new_words)
        changes = []

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            change_type = {
                'equal': ChangeType.EQUAL,
                'delete': ChangeType.DELETE,
                'insert': ChangeType.INSERT,
                'replace': ChangeType.REPLACE
            }.get(tag, ChangeType.EQUAL)

            changes.append(Change(
                type=change_type,
                old_start=i1,
                old_end=i2,
                new_start=j1,
                new_end=j2,
                old_content=old_words[i1:i2],
                new_content=new_words[j1:j2]
            ))

        return changes

    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text into words."""
        return re.findall(r'\S+|\s+', text)


class CharacterDiff(DiffAlgorithm):
    """Character-level diff."""

    def diff(self, old: List[str], new: List[str]) -> List[Change]:
        old_text = '\n'.join(old)
        new_text = '\n'.join(new)

        matcher = SequenceMatcher(list(old_text), list(new_text))
        changes = []

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            change_type = {
                'equal': ChangeType.EQUAL,
                'delete': ChangeType.DELETE,
                'insert': ChangeType.INSERT,
                'replace': ChangeType.REPLACE
            }.get(tag, ChangeType.EQUAL)

            changes.append(Change(
                type=change_type,
                old_start=i1,
                old_end=i2,
                new_start=j1,
                new_end=j2,
                old_content=list(old_text[i1:i2]),
                new_content=list(new_text[j1:j2])
            ))

        return changes


# =============================================================================
# FORMATTERS
# =============================================================================

class DiffFormatter(ABC):
    """Abstract diff formatter."""

    @abstractmethod
    def format(self, result: DiffResult) -> str:
        """Format diff result."""
        pass


class UnifiedFormatter(DiffFormatter):
    """Unified diff format."""

    def __init__(self, context_lines: int = 3):
        self.context_lines = context_lines

    def format(self, result: DiffResult) -> str:
        lines = []

        # Generate hunks with context
        hunks = self._generate_hunks(result)

        for hunk in hunks:
            lines.append(
                f"@@ -{hunk.old_start},{hunk.old_count} "
                f"+{hunk.new_start},{hunk.new_count} @@"
            )

            for change in hunk.changes:
                if change.type == ChangeType.EQUAL:
                    for line in change.old_content:
                        lines.append(f" {line}")
                elif change.type == ChangeType.DELETE:
                    for line in change.old_content:
                        lines.append(f"-{line}")
                elif change.type == ChangeType.INSERT:
                    for line in change.new_content:
                        lines.append(f"+{line}")
                elif change.type == ChangeType.REPLACE:
                    for line in change.old_content:
                        lines.append(f"-{line}")
                    for line in change.new_content:
                        lines.append(f"+{line}")

        return '\n'.join(lines)

    def _generate_hunks(self, result: DiffResult) -> List[Hunk]:
        """Generate hunks with context."""
        # Simplified hunk generation
        if not result.changes:
            return []

        hunk = Hunk(
            old_start=1,
            old_count=len(result.old_lines),
            new_start=1,
            new_count=len(result.new_lines),
            changes=result.changes
        )

        return [hunk]


class SideBySideFormatter(DiffFormatter):
    """Side-by-side diff format."""

    def __init__(self, width: int = 80):
        self.width = width
        self.column_width = (width - 3) // 2

    def format(self, result: DiffResult) -> str:
        lines = []

        # Header
        header = f"{'OLD':<{self.column_width}} | {'NEW':<{self.column_width}}"
        lines.append(header)
        lines.append('-' * self.width)

        old_idx = 0
        new_idx = 0

        for change in result.changes:
            if change.type == ChangeType.EQUAL:
                for i in range(len(change.old_content)):
                    old_line = self._truncate(change.old_content[i])
                    new_line = self._truncate(change.new_content[i])
                    lines.append(f"{old_line:<{self.column_width}} | {new_line}")

            elif change.type == ChangeType.DELETE:
                for line in change.old_content:
                    old_line = self._truncate(line)
                    lines.append(f"{old_line:<{self.column_width}} | ")

            elif change.type == ChangeType.INSERT:
                for line in change.new_content:
                    new_line = self._truncate(line)
                    lines.append(f"{'':<{self.column_width}} | {new_line}")

            elif change.type == ChangeType.REPLACE:
                max_len = max(len(change.old_content), len(change.new_content))

                for i in range(max_len):
                    old_line = ""
                    new_line = ""

                    if i < len(change.old_content):
                        old_line = self._truncate(change.old_content[i])
                    if i < len(change.new_content):
                        new_line = self._truncate(change.new_content[i])

                    lines.append(f"{old_line:<{self.column_width}} | {new_line}")

        return '\n'.join(lines)

    def _truncate(self, text: str) -> str:
        """Truncate text to column width."""
        if len(text) > self.column_width:
            return text[:self.column_width - 3] + "..."
        return text


class HTMLFormatter(DiffFormatter):
    """HTML diff format."""

    def format(self, result: DiffResult) -> str:
        lines = [
            '<style>',
            '.diff-add { background-color: #e6ffec; }',
            '.diff-del { background-color: #ffebe9; }',
            '.diff-line { font-family: monospace; white-space: pre; }',
            '</style>',
            '<div class="diff">'
        ]

        for change in result.changes:
            if change.type == ChangeType.EQUAL:
                for line in change.old_content:
                    escaped = self._escape(line)
                    lines.append(f'<div class="diff-line">{escaped}</div>')

            elif change.type == ChangeType.DELETE:
                for line in change.old_content:
                    escaped = self._escape(line)
                    lines.append(f'<div class="diff-line diff-del">-{escaped}</div>')

            elif change.type == ChangeType.INSERT:
                for line in change.new_content:
                    escaped = self._escape(line)
                    lines.append(f'<div class="diff-line diff-add">+{escaped}</div>')

            elif change.type == ChangeType.REPLACE:
                for line in change.old_content:
                    escaped = self._escape(line)
                    lines.append(f'<div class="diff-line diff-del">-{escaped}</div>')
                for line in change.new_content:
                    escaped = self._escape(line)
                    lines.append(f'<div class="diff-line diff-add">+{escaped}</div>')

        lines.append('</div>')

        return '\n'.join(lines)

    def _escape(self, text: str) -> str:
        """Escape HTML entities."""
        return (text
                .replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;'))


class JSONFormatter(DiffFormatter):
    """JSON diff format."""

    def format(self, result: DiffResult) -> str:
        data = {
            "changes": [],
            "stats": {
                "insertions": result.insertions,
                "deletions": result.deletions,
                "similarity": result.similarity
            }
        }

        for change in result.changes:
            data["changes"].append({
                "type": change.type.value,
                "old_range": [change.old_start, change.old_end],
                "new_range": [change.new_start, change.new_end],
                "old_content": change.old_content,
                "new_content": change.new_content
            })

        return json.dumps(data, indent=2)


# =============================================================================
# DIFF ENGINE
# =============================================================================

class DiffEngine:
    """
    Comprehensive Diff Engine for BAEL.

    Provides text comparison and difference analysis.
    """

    def __init__(self):
        self._algorithms: Dict[DiffMode, DiffAlgorithm] = {
            DiffMode.LINE: LineDiff(),
            DiffMode.WORD: WordDiff(),
            DiffMode.CHARACTER: CharacterDiff(),
        }

        self._formatters: Dict[OutputFormat, DiffFormatter] = {
            OutputFormat.UNIFIED: UnifiedFormatter(),
            OutputFormat.SIDE_BY_SIDE: SideBySideFormatter(),
            OutputFormat.HTML: HTMLFormatter(),
            OutputFormat.JSON: JSONFormatter(),
        }

        self._stats: Dict[str, int] = defaultdict(int)

    # -------------------------------------------------------------------------
    # DIFF OPERATIONS
    # -------------------------------------------------------------------------

    def diff(
        self,
        old: str,
        new: str,
        mode: DiffMode = DiffMode.LINE
    ) -> DiffResult:
        """Compute difference between two texts."""
        self._stats["diffs_computed"] += 1

        old_lines = old.splitlines()
        new_lines = new.splitlines()

        algorithm = self._algorithms[mode]
        changes = algorithm.diff(old_lines, new_lines)

        # Calculate similarity
        matcher = SequenceMatcher(old_lines, new_lines)
        similarity = matcher.ratio()

        return DiffResult(
            changes=changes,
            old_lines=old_lines,
            new_lines=new_lines,
            similarity=similarity
        )

    def diff_files(
        self,
        old_content: str,
        new_content: str,
        old_name: str = "old",
        new_name: str = "new",
        mode: DiffMode = DiffMode.LINE
    ) -> Patch:
        """Create a patch from two file contents."""
        result = self.diff(old_content, new_content, mode)

        header = PatchHeader(
            old_file=old_name,
            new_file=new_name,
            old_timestamp=datetime.utcnow().isoformat(),
            new_timestamp=datetime.utcnow().isoformat()
        )

        # Create hunk
        hunk = Hunk(
            old_start=1,
            old_count=len(result.old_lines),
            new_start=1,
            new_count=len(result.new_lines),
            changes=result.changes
        )

        return Patch(header=header, hunks=[hunk])

    # -------------------------------------------------------------------------
    # FORMATTING
    # -------------------------------------------------------------------------

    def format(
        self,
        result: DiffResult,
        format: OutputFormat = OutputFormat.UNIFIED
    ) -> str:
        """Format diff result."""
        formatter = self._formatters[format]
        return formatter.format(result)

    def to_unified(self, old: str, new: str) -> str:
        """Generate unified diff."""
        result = self.diff(old, new)
        return self.format(result, OutputFormat.UNIFIED)

    def to_side_by_side(self, old: str, new: str, width: int = 80) -> str:
        """Generate side-by-side diff."""
        formatter = SideBySideFormatter(width)
        result = self.diff(old, new)
        return formatter.format(result)

    def to_html(self, old: str, new: str) -> str:
        """Generate HTML diff."""
        result = self.diff(old, new)
        return self.format(result, OutputFormat.HTML)

    def to_json(self, old: str, new: str) -> str:
        """Generate JSON diff."""
        result = self.diff(old, new)
        return self.format(result, OutputFormat.JSON)

    # -------------------------------------------------------------------------
    # PATCH OPERATIONS
    # -------------------------------------------------------------------------

    def create_patch(
        self,
        old: str,
        new: str,
        old_name: str = "a",
        new_name: str = "b"
    ) -> str:
        """Create a patch string."""
        patch = self.diff_files(old, new, old_name, new_name)
        return patch.to_unified()

    def apply_patch(self, text: str, patch_text: str) -> str:
        """Apply a patch to text."""
        self._stats["patches_applied"] += 1

        lines = text.splitlines()
        patch_lines = patch_text.splitlines()

        result_lines = list(lines)
        offset = 0

        i = 0
        while i < len(patch_lines):
            line = patch_lines[i]

            # Hunk header
            if line.startswith('@@'):
                match = re.match(r'@@ -(\d+),(\d+) \+(\d+),(\d+) @@', line)

                if match:
                    old_start = int(match.group(1)) - 1

                    i += 1

                    # Process hunk content
                    while i < len(patch_lines) and not patch_lines[i].startswith('@@'):
                        pline = patch_lines[i]

                        if pline.startswith(' '):
                            old_start += 1
                        elif pline.startswith('-'):
                            if old_start + offset < len(result_lines):
                                result_lines.pop(old_start + offset)
                                offset -= 1
                        elif pline.startswith('+'):
                            result_lines.insert(old_start + offset + 1, pline[1:])
                            offset += 1
                            old_start += 1

                        i += 1
                else:
                    i += 1
            else:
                i += 1

        return '\n'.join(result_lines)

    # -------------------------------------------------------------------------
    # THREE-WAY MERGE
    # -------------------------------------------------------------------------

    def merge3(
        self,
        base: str,
        left: str,
        right: str
    ) -> MergeOutput:
        """Perform three-way merge."""
        self._stats["merges_performed"] += 1

        base_lines = base.splitlines()
        left_lines = left.splitlines()
        right_lines = right.splitlines()

        # Get changes from base to each version
        left_diff = self.diff(base, left)
        right_diff = self.diff(base, right)

        merged = []
        conflicts = []

        # Simple merge algorithm
        base_idx = 0

        left_changes = {c.old_start: c for c in left_diff.changes if c.type != ChangeType.EQUAL}
        right_changes = {c.old_start: c for c in right_diff.changes if c.type != ChangeType.EQUAL}

        while base_idx < len(base_lines):
            left_change = left_changes.get(base_idx)
            right_change = right_changes.get(base_idx)

            if left_change is None and right_change is None:
                # No changes
                merged.append(base_lines[base_idx])
                base_idx += 1

            elif left_change is None:
                # Only right changed
                merged.extend(right_change.new_content)
                base_idx = right_change.old_end

            elif right_change is None:
                # Only left changed
                merged.extend(left_change.new_content)
                base_idx = left_change.old_end

            elif left_change.new_content == right_change.new_content:
                # Same change
                merged.extend(left_change.new_content)
                base_idx = max(left_change.old_end, right_change.old_end)

            else:
                # Conflict
                conflicts.append(MergeConflict(
                    line=len(merged),
                    base=base_lines[base_idx:max(left_change.old_end, right_change.old_end)],
                    left=left_change.new_content,
                    right=right_change.new_content
                ))

                merged.append("<<<<<<< LEFT")
                merged.extend(left_change.new_content)
                merged.append("=======")
                merged.extend(right_change.new_content)
                merged.append(">>>>>>> RIGHT")

                base_idx = max(left_change.old_end, right_change.old_end)

        return MergeOutput(
            result=MergeResult.CONFLICT if conflicts else MergeResult.CLEAN,
            merged=merged,
            conflicts=conflicts
        )

    # -------------------------------------------------------------------------
    # SIMILARITY
    # -------------------------------------------------------------------------

    def similarity(self, text1: str, text2: str) -> float:
        """Calculate text similarity (0-1)."""
        lines1 = text1.splitlines()
        lines2 = text2.splitlines()

        matcher = SequenceMatcher(lines1, lines2)
        return matcher.ratio()

    def quick_similarity(self, text1: str, text2: str) -> float:
        """Quick similarity estimate."""
        lines1 = text1.splitlines()
        lines2 = text2.splitlines()

        matcher = SequenceMatcher(lines1, lines2)
        return matcher.quick_ratio()

    # -------------------------------------------------------------------------
    # STATISTICS
    # -------------------------------------------------------------------------

    def get_diff_stats(self, result: DiffResult) -> DiffStats:
        """Get statistics for a diff."""
        stats = DiffStats()

        for change in result.changes:
            if change.type == ChangeType.EQUAL:
                stats.lines_unchanged += len(change.old_content)
            elif change.type == ChangeType.INSERT:
                stats.lines_added += len(change.new_content)
            elif change.type == ChangeType.DELETE:
                stats.lines_deleted += len(change.old_content)
            elif change.type == ChangeType.REPLACE:
                stats.lines_modified += max(
                    len(change.old_content),
                    len(change.new_content)
                )

        stats.similarity = result.similarity

        return stats

    def get_stats(self) -> Dict[str, int]:
        """Get engine statistics."""
        return dict(self._stats)

    # -------------------------------------------------------------------------
    # UTILITIES
    # -------------------------------------------------------------------------

    def is_identical(self, text1: str, text2: str) -> bool:
        """Check if texts are identical."""
        return text1 == text2

    def has_changes(self, old: str, new: str) -> bool:
        """Check if there are any changes."""
        result = self.diff(old, new)
        return result.has_changes

    def get_changed_lines(self, old: str, new: str) -> Tuple[Set[int], Set[int]]:
        """Get line numbers that changed."""
        result = self.diff(old, new)

        old_changed = set()
        new_changed = set()

        for change in result.changes:
            if change.type != ChangeType.EQUAL:
                old_changed.update(range(change.old_start, change.old_end))
                new_changed.update(range(change.new_start, change.new_end))

        return old_changed, new_changed


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Diff Engine."""
    print("=" * 70)
    print("BAEL - DIFF ENGINE DEMO")
    print("Comprehensive Text Comparison System")
    print("=" * 70)
    print()

    engine = DiffEngine()

    # Sample texts
    old_text = """# BAEL Configuration
version: 1.0
name: BAEL
description: AI Agent System
features:
  - nlp
  - vision
  - audio
settings:
  debug: false
  logging: info"""

    new_text = """# BAEL Configuration
version: 2.0
name: BAEL Supreme
description: Advanced AI Agent System
features:
  - nlp
  - vision
  - speech
  - reasoning
settings:
  debug: true
  logging: debug
  cache: enabled"""

    # 1. Basic Diff
    print("1. BASIC DIFF:")
    print("-" * 40)

    result = engine.diff(old_text, new_text)
    print(f"   Has changes: {result.has_changes}")
    print(f"   Similarity: {result.similarity:.2%}")
    print(f"   Insertions: {result.insertions}")
    print(f"   Deletions: {result.deletions}")
    print()

    # 2. Unified Format
    print("2. UNIFIED DIFF FORMAT:")
    print("-" * 40)

    unified = engine.to_unified(old_text, new_text)
    print(unified[:500])
    print("...")
    print()

    # 3. Side-by-Side Format
    print("3. SIDE-BY-SIDE FORMAT:")
    print("-" * 40)

    side_by_side = engine.to_side_by_side(old_text, new_text, 70)
    lines = side_by_side.split('\n')[:15]
    print('\n'.join(lines))
    print("...")
    print()

    # 4. HTML Format
    print("4. HTML FORMAT:")
    print("-" * 40)

    html = engine.to_html(old_text, new_text)
    print(f"   HTML output ({len(html)} chars)")
    print(f"   {html[:200]}...")
    print()

    # 5. JSON Format
    print("5. JSON FORMAT:")
    print("-" * 40)

    json_output = engine.to_json(old_text, new_text)
    print(f"   JSON output:")
    print(f"   {json_output[:300]}...")
    print()

    # 6. Diff Statistics
    print("6. DIFF STATISTICS:")
    print("-" * 40)

    result = engine.diff(old_text, new_text)
    stats = engine.get_diff_stats(result)

    print(f"   Lines added: {stats.lines_added}")
    print(f"   Lines deleted: {stats.lines_deleted}")
    print(f"   Lines modified: {stats.lines_modified}")
    print(f"   Lines unchanged: {stats.lines_unchanged}")
    print(f"   Total changes: {stats.total_changes}")
    print(f"   Similarity: {stats.similarity:.2%}")
    print()

    # 7. Word-Level Diff
    print("7. WORD-LEVEL DIFF:")
    print("-" * 40)

    old_sentence = "The quick brown fox jumps over the lazy dog"
    new_sentence = "The fast brown fox leaps over the sleepy dog"

    result = engine.diff(old_sentence, new_sentence, DiffMode.WORD)
    print(f"   Old: {old_sentence}")
    print(f"   New: {new_sentence}")
    print(f"   Changes: {len([c for c in result.changes if c.type != ChangeType.EQUAL])}")
    print()

    # 8. Character-Level Diff
    print("8. CHARACTER-LEVEL DIFF:")
    print("-" * 40)

    old_word = "hello"
    new_word = "jello"

    result = engine.diff(old_word, new_word, DiffMode.CHARACTER)
    print(f"   Old: {old_word}")
    print(f"   New: {new_word}")
    print(f"   Similarity: {result.similarity:.2%}")
    print()

    # 9. Patch Creation
    print("9. PATCH CREATION:")
    print("-" * 40)

    patch = engine.create_patch(old_text, new_text, "config.old.yaml", "config.new.yaml")
    print(f"   Patch ({len(patch)} chars):")
    print(f"   {patch[:300]}...")
    print()

    # 10. Patch Application
    print("10. PATCH APPLICATION:")
    print("-" * 40)

    simple_old = "line1\nline2\nline3"
    simple_new = "line1\nmodified line2\nline3\nline4"

    patch = engine.create_patch(simple_old, simple_new)
    # Note: This is a simplified demo - full patch application is complex
    print(f"   Original:\n   {simple_old.replace(chr(10), ' | ')}")
    print(f"   Target:\n   {simple_new.replace(chr(10), ' | ')}")
    print()

    # 11. Three-Way Merge
    print("11. THREE-WAY MERGE:")
    print("-" * 40)

    base = "line1\nline2\nline3"
    left = "line1\nleft modified\nline3"
    right = "line1\nline2\nright added\nline3"

    merge = engine.merge3(base, left, right)

    print(f"   Base: {base.replace(chr(10), ' | ')}")
    print(f"   Left: {left.replace(chr(10), ' | ')}")
    print(f"   Right: {right.replace(chr(10), ' | ')}")
    print(f"   Result: {merge.result.value}")
    print(f"   Merged: {' | '.join(merge.merged)}")
    print(f"   Conflicts: {len(merge.conflicts)}")
    print()

    # 12. Similarity Calculation
    print("12. SIMILARITY CALCULATION:")
    print("-" * 40)

    text1 = "The quick brown fox"
    text2 = "The quick brown dog"
    text3 = "Something completely different"

    print(f"   '{text1}' vs '{text2}': {engine.similarity(text1, text2):.2%}")
    print(f"   '{text1}' vs '{text3}': {engine.similarity(text1, text3):.2%}")
    print()

    # 13. Changed Lines
    print("13. CHANGED LINES:")
    print("-" * 40)

    old_changed, new_changed = engine.get_changed_lines(old_text, new_text)

    print(f"   Lines changed in old: {sorted(old_changed)}")
    print(f"   Lines changed in new: {sorted(new_changed)}")
    print()

    # 14. Engine Statistics
    print("14. ENGINE STATISTICS:")
    print("-" * 40)

    stats = engine.get_stats()
    print(f"   Stats: {stats}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Diff Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())

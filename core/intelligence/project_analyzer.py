"""
BAEL Project Analyzer
======================

Analyze project structure, patterns, and metrics.
Provides deep understanding of codebases.

Features:
- Structure analysis
- Dependency mapping
- Code pattern detection
- Quality metrics
- Architecture inference
"""

import asyncio
import hashlib
import logging
import os
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class ProjectType(Enum):
    """Project type classifications."""
    PYTHON_LIBRARY = "python_library"
    PYTHON_APP = "python_app"
    WEB_FRONTEND = "web_frontend"
    WEB_BACKEND = "web_backend"
    FULLSTACK = "fullstack"
    CLI_TOOL = "cli_tool"
    API_SERVICE = "api_service"
    DATA_SCIENCE = "data_science"
    ML_PROJECT = "ml_project"
    MOBILE_APP = "mobile_app"
    UNKNOWN = "unknown"


class ArchitectureStyle(Enum):
    """Architecture styles."""
    MONOLITH = "monolith"
    MICROSERVICES = "microservices"
    MODULAR = "modular"
    LAYERED = "layered"
    MVC = "mvc"
    HEXAGONAL = "hexagonal"
    EVENT_DRIVEN = "event_driven"


@dataclass
class FileInfo:
    """Information about a file."""
    path: str
    name: str
    extension: str
    size_bytes: int
    lines: int = 0

    # Code info
    imports: List[str] = field(default_factory=list)
    classes: List[str] = field(default_factory=list)
    functions: List[str] = field(default_factory=list)

    # Metadata
    modified_at: Optional[datetime] = None


@dataclass
class ModuleInfo:
    """Information about a module/package."""
    name: str
    path: str
    files: List[FileInfo] = field(default_factory=list)
    submodules: List[str] = field(default_factory=list)

    # Dependencies
    internal_deps: List[str] = field(default_factory=list)
    external_deps: List[str] = field(default_factory=list)

    # Metrics
    total_lines: int = 0
    complexity: float = 0.0


@dataclass
class DependencyGraph:
    """Project dependency graph."""
    nodes: List[str] = field(default_factory=list)
    edges: List[Tuple[str, str]] = field(default_factory=list)

    def add_edge(self, source: str, target: str) -> None:
        if source not in self.nodes:
            self.nodes.append(source)
        if target not in self.nodes:
            self.nodes.append(target)
        self.edges.append((source, target))

    def get_dependencies(self, module: str) -> List[str]:
        return [t for s, t in self.edges if s == module]

    def get_dependents(self, module: str) -> List[str]:
        return [s for s, t in self.edges if t == module]


@dataclass
class ProjectMetrics:
    """Project quality and size metrics."""
    # Size
    total_files: int = 0
    total_lines: int = 0
    code_lines: int = 0
    comment_lines: int = 0

    # Complexity
    avg_file_complexity: float = 0.0
    max_file_complexity: float = 0.0

    # Quality
    test_coverage: float = 0.0
    doc_coverage: float = 0.0
    type_hint_coverage: float = 0.0

    # Dependencies
    internal_dep_count: int = 0
    external_dep_count: int = 0


@dataclass
class ProjectProfile:
    """Complete project profile."""
    id: str
    name: str
    path: str

    # Classification
    type: ProjectType = ProjectType.UNKNOWN
    architecture: ArchitectureStyle = ArchitectureStyle.MODULAR
    languages: List[str] = field(default_factory=list)
    frameworks: List[str] = field(default_factory=list)

    # Structure
    modules: List[ModuleInfo] = field(default_factory=list)
    dependency_graph: DependencyGraph = field(default_factory=DependencyGraph)

    # Metrics
    metrics: ProjectMetrics = field(default_factory=ProjectMetrics)

    # Patterns detected
    patterns: List[str] = field(default_factory=list)

    # Metadata
    analyzed_at: datetime = field(default_factory=datetime.now)
    analysis_time_ms: float = 0.0


@dataclass
class AnalysisConfig:
    """Analysis configuration."""
    # Scope
    analyze_tests: bool = True
    analyze_docs: bool = True
    max_file_size_kb: int = 500

    # Depth
    extract_imports: bool = True
    extract_classes: bool = True
    extract_functions: bool = True

    # Patterns
    detect_patterns: bool = True

    # Exclusions
    exclude_dirs: List[str] = field(default_factory=lambda: [
        "__pycache__", ".git", "node_modules", ".venv", "venv",
        "dist", "build", ".eggs", "*.egg-info",
    ])
    exclude_files: List[str] = field(default_factory=lambda: [
        "*.pyc", "*.pyo", "*.min.js", "*.map",
    ])


class ProjectAnalyzer:
    """
    Project analysis system for BAEL.
    """

    def __init__(
        self,
        config: Optional[AnalysisConfig] = None,
    ):
        self.config = config or AnalysisConfig()

        # Analysis cache
        self.profiles: Dict[str, ProjectProfile] = {}

        # Language detection
        self._language_extensions = {
            ".py": "Python",
            ".js": "JavaScript",
            ".ts": "TypeScript",
            ".jsx": "JavaScript",
            ".tsx": "TypeScript",
            ".java": "Java",
            ".rs": "Rust",
            ".go": "Go",
            ".rb": "Ruby",
            ".php": "PHP",
            ".cs": "C#",
            ".cpp": "C++",
            ".c": "C",
        }

        # Framework detection patterns
        self._framework_patterns = {
            "Django": ["django", "DJANGO_SETTINGS"],
            "Flask": ["flask", "Flask(__name__)"],
            "FastAPI": ["fastapi", "FastAPI()"],
            "React": ["react", "React.Component", "useState"],
            "Vue": ["vue", "createApp", "Vue.component"],
            "Express": ["express", "express()"],
            "PyTorch": ["torch", "nn.Module"],
            "TensorFlow": ["tensorflow", "tf.keras"],
        }

        # Stats
        self.stats = {
            "projects_analyzed": 0,
            "files_processed": 0,
            "patterns_detected": 0,
        }

    async def analyze(
        self,
        project_path: str,
    ) -> ProjectProfile:
        """
        Analyze a project.

        Args:
            project_path: Path to project root

        Returns:
            ProjectProfile
        """
        import time

        self.stats["projects_analyzed"] += 1
        start_time = time.time()

        path = Path(project_path)
        if not path.exists():
            raise ValueError(f"Project path does not exist: {project_path}")

        # Generate profile ID
        profile_id = hashlib.md5(str(path.resolve()).encode()).hexdigest()[:12]

        # Create profile
        profile = ProjectProfile(
            id=profile_id,
            name=path.name,
            path=str(path.resolve()),
        )

        # Scan files
        files = await self._scan_files(path)
        self.stats["files_processed"] += len(files)

        # Detect languages
        profile.languages = self._detect_languages(files)

        # Build modules
        profile.modules = self._build_modules(files, path)

        # Build dependency graph
        profile.dependency_graph = self._build_dependency_graph(profile.modules)

        # Detect frameworks
        profile.frameworks = await self._detect_frameworks(files)

        # Infer project type
        profile.type = self._infer_project_type(profile)

        # Infer architecture
        profile.architecture = self._infer_architecture(profile)

        # Calculate metrics
        profile.metrics = self._calculate_metrics(files, profile)

        # Detect patterns
        if self.config.detect_patterns:
            profile.patterns = await self._detect_patterns(files, profile)
            self.stats["patterns_detected"] += len(profile.patterns)

        # Finalize
        profile.analysis_time_ms = (time.time() - start_time) * 1000

        # Cache
        self.profiles[profile_id] = profile

        logger.info(f"Analyzed project: {profile.name} ({profile.type.value})")

        return profile

    async def _scan_files(self, root: Path) -> List[FileInfo]:
        """Scan all relevant files."""
        files = []

        for file_path in root.rglob("*"):
            if not file_path.is_file():
                continue

            # Check exclusions
            if self._is_excluded(file_path):
                continue

            # Check size
            try:
                size = file_path.stat().st_size
                if size > self.config.max_file_size_kb * 1024:
                    continue
            except OSError:
                continue

            file_info = FileInfo(
                path=str(file_path),
                name=file_path.name,
                extension=file_path.suffix,
                size_bytes=size,
            )

            # Parse if code file
            if file_path.suffix in self._language_extensions:
                await self._parse_file(file_path, file_info)

            files.append(file_info)

        return files

    def _is_excluded(self, path: Path) -> bool:
        """Check if path should be excluded."""
        path_str = str(path)

        for exclude in self.config.exclude_dirs:
            if exclude.replace("*", "") in path_str:
                return True

        for exclude in self.config.exclude_files:
            pattern = exclude.replace("*", ".*")
            if re.match(pattern, path.name):
                return True

        return False

    async def _parse_file(self, path: Path, file_info: FileInfo) -> None:
        """Parse a code file."""
        try:
            content = path.read_text(errors="ignore")
            lines = content.split("\n")
            file_info.lines = len(lines)

            if self.config.extract_imports:
                file_info.imports = self._extract_imports(content, path.suffix)

            if self.config.extract_classes:
                file_info.classes = self._extract_classes(content, path.suffix)

            if self.config.extract_functions:
                file_info.functions = self._extract_functions(content, path.suffix)

        except Exception as e:
            logger.debug(f"Error parsing {path}: {e}")

    def _extract_imports(self, content: str, ext: str) -> List[str]:
        """Extract import statements."""
        imports = []

        if ext == ".py":
            # Python imports
            for match in re.finditer(r"^(?:from|import)\s+(\S+)", content, re.MULTILINE):
                imports.append(match.group(1).split(".")[0])
        elif ext in (".js", ".ts", ".jsx", ".tsx"):
            # JS/TS imports
            for match in re.finditer(r"(?:import|require)\s*\(?['\"]([^'\"]+)", content):
                imports.append(match.group(1))

        return list(set(imports))

    def _extract_classes(self, content: str, ext: str) -> List[str]:
        """Extract class definitions."""
        classes = []

        if ext == ".py":
            for match in re.finditer(r"^class\s+(\w+)", content, re.MULTILINE):
                classes.append(match.group(1))
        elif ext in (".js", ".ts", ".jsx", ".tsx"):
            for match in re.finditer(r"class\s+(\w+)", content):
                classes.append(match.group(1))

        return classes

    def _extract_functions(self, content: str, ext: str) -> List[str]:
        """Extract function definitions."""
        functions = []

        if ext == ".py":
            for match in re.finditer(r"^(?:async\s+)?def\s+(\w+)", content, re.MULTILINE):
                functions.append(match.group(1))
        elif ext in (".js", ".ts", ".jsx", ".tsx"):
            for match in re.finditer(r"(?:async\s+)?function\s+(\w+)", content):
                functions.append(match.group(1))
            for match in re.finditer(r"const\s+(\w+)\s*=\s*(?:async\s+)?\(", content):
                functions.append(match.group(1))

        return functions

    def _detect_languages(self, files: List[FileInfo]) -> List[str]:
        """Detect languages used in project."""
        language_counts = defaultdict(int)

        for file in files:
            if file.extension in self._language_extensions:
                lang = self._language_extensions[file.extension]
                language_counts[lang] += file.lines or 1

        # Sort by usage
        sorted_langs = sorted(
            language_counts.items(),
            key=lambda x: x[1],
            reverse=True,
        )

        return [lang for lang, _ in sorted_langs]

    def _build_modules(
        self,
        files: List[FileInfo],
        root: Path,
    ) -> List[ModuleInfo]:
        """Build module information."""
        modules = {}

        for file in files:
            file_path = Path(file.path)

            # Get relative directory
            try:
                rel_path = file_path.parent.relative_to(root)
                module_name = str(rel_path).replace(os.sep, ".")
            except ValueError:
                module_name = "root"

            if not module_name or module_name == ".":
                module_name = "root"

            if module_name not in modules:
                modules[module_name] = ModuleInfo(
                    name=module_name,
                    path=str(file_path.parent),
                )

            modules[module_name].files.append(file)
            modules[module_name].total_lines += file.lines

            # Track dependencies
            for imp in file.imports:
                if imp in modules or any(imp.startswith(m + ".") for m in modules):
                    if imp not in modules[module_name].internal_deps:
                        modules[module_name].internal_deps.append(imp)
                else:
                    if imp not in modules[module_name].external_deps:
                        modules[module_name].external_deps.append(imp)

        return list(modules.values())

    def _build_dependency_graph(
        self,
        modules: List[ModuleInfo],
    ) -> DependencyGraph:
        """Build dependency graph."""
        graph = DependencyGraph()

        for module in modules:
            for dep in module.internal_deps:
                graph.add_edge(module.name, dep)

        return graph

    async def _detect_frameworks(self, files: List[FileInfo]) -> List[str]:
        """Detect frameworks used."""
        detected = set()

        # Check imports
        all_imports = set()
        for file in files:
            all_imports.update(file.imports)

        for framework, patterns in self._framework_patterns.items():
            for pattern in patterns:
                if pattern.lower() in [i.lower() for i in all_imports]:
                    detected.add(framework)
                    break

        # Check file contents for additional patterns
        for file in files[:50]:  # Check first 50 files
            try:
                content = Path(file.path).read_text(errors="ignore")
                for framework, patterns in self._framework_patterns.items():
                    for pattern in patterns:
                        if pattern in content:
                            detected.add(framework)
                            break
            except Exception:
                continue

        return list(detected)

    def _infer_project_type(self, profile: ProjectProfile) -> ProjectType:
        """Infer project type from analysis."""
        frameworks = set(profile.frameworks)
        languages = profile.languages

        # Check for specific frameworks
        if "Django" in frameworks or "Flask" in frameworks or "FastAPI" in frameworks:
            return ProjectType.WEB_BACKEND

        if "React" in frameworks or "Vue" in frameworks:
            if any(fw in frameworks for fw in ["Django", "Flask", "FastAPI", "Express"]):
                return ProjectType.FULLSTACK
            return ProjectType.WEB_FRONTEND

        if "PyTorch" in frameworks or "TensorFlow" in frameworks:
            return ProjectType.ML_PROJECT

        # Check for CLI indicators
        if languages and languages[0] == "Python":
            has_cli = any(
                "argparse" in m.external_deps or "click" in m.external_deps
                for m in profile.modules
            )
            if has_cli:
                return ProjectType.CLI_TOOL

        # Check for API indicators
        has_api = any("api" in m.name.lower() for m in profile.modules)
        if has_api:
            return ProjectType.API_SERVICE

        # Default based on structure
        if "Python" in languages:
            if any("setup.py" in f.name or "pyproject.toml" in f.name
                   for m in profile.modules for f in m.files):
                return ProjectType.PYTHON_LIBRARY
            return ProjectType.PYTHON_APP

        return ProjectType.UNKNOWN

    def _infer_architecture(self, profile: ProjectProfile) -> ArchitectureStyle:
        """Infer architecture style."""
        module_count = len(profile.modules)
        avg_module_size = profile.metrics.total_lines / max(module_count, 1)

        # Check for layered patterns
        layer_keywords = ["controller", "service", "repository", "model", "view"]
        layer_matches = sum(
            1 for m in profile.modules
            if any(kw in m.name.lower() for kw in layer_keywords)
        )

        if layer_matches >= 3:
            return ArchitectureStyle.LAYERED

        # Check for MVC pattern
        mvc_parts = {"model": False, "view": False, "controller": False}
        for m in profile.modules:
            name_lower = m.name.lower()
            if "model" in name_lower:
                mvc_parts["model"] = True
            if "view" in name_lower:
                mvc_parts["view"] = True
            if "controller" in name_lower:
                mvc_parts["controller"] = True

        if all(mvc_parts.values()):
            return ArchitectureStyle.MVC

        # Check module structure
        if module_count >= 10 and avg_module_size < 500:
            return ArchitectureStyle.MODULAR

        if module_count < 5 and avg_module_size > 1000:
            return ArchitectureStyle.MONOLITH

        return ArchitectureStyle.MODULAR

    def _calculate_metrics(
        self,
        files: List[FileInfo],
        profile: ProjectProfile,
    ) -> ProjectMetrics:
        """Calculate project metrics."""
        metrics = ProjectMetrics()

        metrics.total_files = len(files)
        metrics.total_lines = sum(f.lines for f in files)

        # Count code vs comments (simplified)
        code_lines = 0
        comment_lines = 0

        for file in files:
            if file.extension == ".py":
                # Rough estimate
                code_lines += int(file.lines * 0.85)
                comment_lines += int(file.lines * 0.15)
            else:
                code_lines += file.lines

        metrics.code_lines = code_lines
        metrics.comment_lines = comment_lines

        # Dependencies
        all_internal = set()
        all_external = set()
        for module in profile.modules:
            all_internal.update(module.internal_deps)
            all_external.update(module.external_deps)

        metrics.internal_dep_count = len(all_internal)
        metrics.external_dep_count = len(all_external)

        # Doc coverage (files with docstrings)
        files_with_docs = sum(
            1 for f in files
            if f.extension == ".py" and any(c for c in f.classes)
        )
        metrics.doc_coverage = files_with_docs / max(len(files), 1)

        return metrics

    async def _detect_patterns(
        self,
        files: List[FileInfo],
        profile: ProjectProfile,
    ) -> List[str]:
        """Detect design patterns in use."""
        patterns = set()

        # Singleton pattern
        for file in files:
            if file.extension == ".py":
                if any("_instance" in f for f in file.functions):
                    patterns.add("Singleton")

        # Factory pattern
        for module in profile.modules:
            if "factory" in module.name.lower():
                patterns.add("Factory")

        # Repository pattern
        for module in profile.modules:
            if "repository" in module.name.lower():
                patterns.add("Repository")

        # Observer/Event pattern
        all_classes = set()
        for file in files:
            all_classes.update(file.classes)

        if any("Observer" in c or "Listener" in c for c in all_classes):
            patterns.add("Observer")

        if any("EventHandler" in c or "EventEmitter" in c for c in all_classes):
            patterns.add("Event-Driven")

        # Decorator pattern
        for file in files:
            if any("decorator" in f.lower() for f in file.functions):
                patterns.add("Decorator")

        return list(patterns)

    def get_profile(self, profile_id: str) -> Optional[ProjectProfile]:
        """Get cached profile."""
        return self.profiles.get(profile_id)

    def compare_profiles(
        self,
        profile1: ProjectProfile,
        profile2: ProjectProfile,
    ) -> Dict[str, Any]:
        """Compare two project profiles."""
        return {
            "type_match": profile1.type == profile2.type,
            "architecture_match": profile1.architecture == profile2.architecture,
            "shared_languages": set(profile1.languages) & set(profile2.languages),
            "shared_frameworks": set(profile1.frameworks) & set(profile2.frameworks),
            "shared_patterns": set(profile1.patterns) & set(profile2.patterns),
            "size_ratio": profile1.metrics.total_lines / max(profile2.metrics.total_lines, 1),
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get analyzer statistics."""
        return {
            **self.stats,
            "cached_profiles": len(self.profiles),
        }


def demo():
    """Demonstrate project analyzer."""
    import asyncio

    print("=" * 60)
    print("BAEL Project Analyzer Demo")
    print("=" * 60)

    analyzer = ProjectAnalyzer()

    # Analyze current directory as example
    async def analyze():
        # Use current file's directory as a mini-project
        import os
        current_dir = os.path.dirname(os.path.abspath(__file__))

        try:
            return await analyzer.analyze(current_dir)
        except Exception as e:
            print(f"Analysis error: {e}")
            return None

    profile = asyncio.run(analyze())

    if profile:
        print(f"\nProject: {profile.name}")
        print(f"  ID: {profile.id}")
        print(f"  Type: {profile.type.value}")
        print(f"  Architecture: {profile.architecture.value}")
        print(f"  Languages: {', '.join(profile.languages)}")
        print(f"  Frameworks: {', '.join(profile.frameworks) or 'None'}")

        print(f"\nModules ({len(profile.modules)}):")
        for module in profile.modules[:5]:
            print(f"  - {module.name}: {len(module.files)} files, {module.total_lines} lines")

        print(f"\nMetrics:")
        print(f"  Total files: {profile.metrics.total_files}")
        print(f"  Total lines: {profile.metrics.total_lines}")
        print(f"  External deps: {profile.metrics.external_dep_count}")

        print(f"\nPatterns: {', '.join(profile.patterns) or 'None detected'}")
        print(f"\nAnalysis time: {profile.analysis_time_ms:.2f}ms")

    print(f"\nStats: {analyzer.get_stats()}")


if __name__ == "__main__":
    demo()

#!/usr/bin/env python3
"""
BAEL - Export Engine
Comprehensive model export and conversion.

Features:
- Multiple export formats
- Model serialization
- Format conversion
- Optimization for deployment
- Metadata preservation
"""

import asyncio
import base64
import hashlib
import json
import os
import pickle
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import (Any, Callable, Dict, Generic, Iterator, List, Optional,
                    Set, Tuple, Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class ExportFormat(Enum):
    """Export formats."""
    PICKLE = "pickle"
    JSON = "json"
    ONNX = "onnx"
    TORCHSCRIPT = "torchscript"
    TENSORFLOW_SAVED_MODEL = "tf_saved_model"
    TENSORFLOW_LITE = "tflite"
    SAFETENSORS = "safetensors"
    CUSTOM = "custom"


class CompressionType(Enum):
    """Compression types."""
    NONE = "none"
    GZIP = "gzip"
    LZ4 = "lz4"
    ZSTD = "zstd"


class QuantizationType(Enum):
    """Quantization types."""
    NONE = "none"
    FLOAT16 = "float16"
    INT8 = "int8"
    INT4 = "int4"
    DYNAMIC = "dynamic"


class ExportStatus(Enum):
    """Export status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class ModelMetadata:
    """Model metadata for export."""
    name: str = ""
    version: str = "1.0.0"
    description: str = ""
    author: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    framework: str = ""
    framework_version: str = ""
    input_schema: Dict[str, Any] = field(default_factory=dict)
    output_schema: Dict[str, Any] = field(default_factory=dict)
    hyperparameters: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, float] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    custom: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "created_at": self.created_at.isoformat(),
            "framework": self.framework,
            "framework_version": self.framework_version,
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
            "hyperparameters": self.hyperparameters,
            "metrics": self.metrics,
            "tags": self.tags,
            "custom": self.custom
        }


@dataclass
class ExportConfig:
    """Export configuration."""
    format: ExportFormat = ExportFormat.PICKLE
    compression: CompressionType = CompressionType.NONE
    quantization: QuantizationType = QuantizationType.NONE
    optimize: bool = True
    include_metadata: bool = True
    include_weights: bool = True
    include_optimizer_state: bool = False
    output_dir: str = "./exports"


@dataclass
class ExportResult:
    """Export result."""
    export_id: str = ""
    status: ExportStatus = ExportStatus.PENDING
    format: ExportFormat = ExportFormat.PICKLE
    output_path: str = ""
    file_size: int = 0
    checksum: str = ""
    duration_ms: float = 0.0
    metadata: Optional[ModelMetadata] = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not self.export_id:
            self.export_id = str(uuid.uuid4())[:8]


@dataclass
class ImportResult:
    """Import result."""
    import_id: str = ""
    status: ExportStatus = ExportStatus.PENDING
    model: Any = None
    metadata: Optional[ModelMetadata] = None
    source_path: str = ""
    duration_ms: float = 0.0
    error: Optional[str] = None

    def __post_init__(self):
        if not self.import_id:
            self.import_id = str(uuid.uuid4())[:8]


@dataclass
class ConversionResult:
    """Format conversion result."""
    conversion_id: str = ""
    status: ExportStatus = ExportStatus.PENDING
    source_format: ExportFormat = ExportFormat.PICKLE
    target_format: ExportFormat = ExportFormat.ONNX
    source_path: str = ""
    output_path: str = ""
    duration_ms: float = 0.0
    error: Optional[str] = None

    def __post_init__(self):
        if not self.conversion_id:
            self.conversion_id = str(uuid.uuid4())[:8]


# =============================================================================
# BASE EXPORTER
# =============================================================================

class BaseExporter(ABC):
    """Abstract base class for exporters."""

    def __init__(self, config: ExportConfig):
        self._config = config

    @property
    @abstractmethod
    def format(self) -> ExportFormat:
        """Get the export format."""
        pass

    @property
    def file_extension(self) -> str:
        """Get file extension."""
        extensions = {
            ExportFormat.PICKLE: ".pkl",
            ExportFormat.JSON: ".json",
            ExportFormat.ONNX: ".onnx",
            ExportFormat.TORCHSCRIPT: ".pt",
            ExportFormat.TENSORFLOW_SAVED_MODEL: "",
            ExportFormat.TENSORFLOW_LITE: ".tflite",
            ExportFormat.SAFETENSORS: ".safetensors",
            ExportFormat.CUSTOM: ".bin"
        }
        return extensions.get(self.format, ".bin")

    @abstractmethod
    async def export(
        self,
        model: Any,
        output_path: str,
        metadata: Optional[ModelMetadata] = None
    ) -> ExportResult:
        """Export a model."""
        pass

    @abstractmethod
    async def load(
        self,
        path: str
    ) -> ImportResult:
        """Load an exported model."""
        pass


# =============================================================================
# EXPORTER IMPLEMENTATIONS
# =============================================================================

class PickleExporter(BaseExporter):
    """Pickle format exporter."""

    @property
    def format(self) -> ExportFormat:
        return ExportFormat.PICKLE

    async def export(
        self,
        model: Any,
        output_path: str,
        metadata: Optional[ModelMetadata] = None
    ) -> ExportResult:
        start_time = time.time()
        result = ExportResult(format=self.format)

        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            export_data = {
                "model": model,
                "metadata": metadata.to_dict() if metadata else None
            }

            with open(output_path, "wb") as f:
                pickle.dump(export_data, f)

            file_size = os.path.getsize(output_path)

            with open(output_path, "rb") as f:
                checksum = hashlib.md5(f.read()).hexdigest()

            result.status = ExportStatus.COMPLETED
            result.output_path = output_path
            result.file_size = file_size
            result.checksum = checksum
            result.metadata = metadata
            result.duration_ms = (time.time() - start_time) * 1000

        except Exception as e:
            result.status = ExportStatus.FAILED
            result.error = str(e)
            result.duration_ms = (time.time() - start_time) * 1000

        return result

    async def load(self, path: str) -> ImportResult:
        start_time = time.time()
        result = ImportResult(source_path=path)

        try:
            with open(path, "rb") as f:
                export_data = pickle.load(f)

            result.model = export_data.get("model")

            meta_dict = export_data.get("metadata")
            if meta_dict:
                result.metadata = ModelMetadata(**{
                    k: v for k, v in meta_dict.items()
                    if k != "created_at"
                })

            result.status = ExportStatus.COMPLETED
            result.duration_ms = (time.time() - start_time) * 1000

        except Exception as e:
            result.status = ExportStatus.FAILED
            result.error = str(e)
            result.duration_ms = (time.time() - start_time) * 1000

        return result


class JSONExporter(BaseExporter):
    """JSON format exporter (for serializable models)."""

    @property
    def format(self) -> ExportFormat:
        return ExportFormat.JSON

    async def export(
        self,
        model: Any,
        output_path: str,
        metadata: Optional[ModelMetadata] = None
    ) -> ExportResult:
        start_time = time.time()
        result = ExportResult(format=self.format)

        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            if hasattr(model, "to_dict"):
                model_data = model.to_dict()
            elif hasattr(model, "__dict__"):
                model_data = model.__dict__
            else:
                model_data = str(model)

            export_data = {
                "model": model_data,
                "metadata": metadata.to_dict() if metadata else None
            }

            with open(output_path, "w") as f:
                json.dump(export_data, f, indent=2, default=str)

            file_size = os.path.getsize(output_path)

            with open(output_path, "rb") as f:
                checksum = hashlib.md5(f.read()).hexdigest()

            result.status = ExportStatus.COMPLETED
            result.output_path = output_path
            result.file_size = file_size
            result.checksum = checksum
            result.metadata = metadata
            result.duration_ms = (time.time() - start_time) * 1000

        except Exception as e:
            result.status = ExportStatus.FAILED
            result.error = str(e)
            result.duration_ms = (time.time() - start_time) * 1000

        return result

    async def load(self, path: str) -> ImportResult:
        start_time = time.time()
        result = ImportResult(source_path=path)

        try:
            with open(path, "r") as f:
                export_data = json.load(f)

            result.model = export_data.get("model")

            meta_dict = export_data.get("metadata")
            if meta_dict:
                result.metadata = ModelMetadata(**{
                    k: v for k, v in meta_dict.items()
                    if k != "created_at"
                })

            result.status = ExportStatus.COMPLETED
            result.duration_ms = (time.time() - start_time) * 1000

        except Exception as e:
            result.status = ExportStatus.FAILED
            result.error = str(e)
            result.duration_ms = (time.time() - start_time) * 1000

        return result


class CustomBinaryExporter(BaseExporter):
    """Custom binary format exporter."""

    MAGIC = b"BAEL"
    VERSION = 1

    @property
    def format(self) -> ExportFormat:
        return ExportFormat.CUSTOM

    async def export(
        self,
        model: Any,
        output_path: str,
        metadata: Optional[ModelMetadata] = None
    ) -> ExportResult:
        start_time = time.time()
        result = ExportResult(format=self.format)

        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            model_bytes = pickle.dumps(model)
            meta_bytes = json.dumps(metadata.to_dict() if metadata else {}).encode()

            with open(output_path, "wb") as f:
                f.write(self.MAGIC)
                f.write(self.VERSION.to_bytes(4, "big"))

                f.write(len(meta_bytes).to_bytes(8, "big"))
                f.write(meta_bytes)

                f.write(len(model_bytes).to_bytes(8, "big"))
                f.write(model_bytes)

            file_size = os.path.getsize(output_path)

            with open(output_path, "rb") as f:
                checksum = hashlib.md5(f.read()).hexdigest()

            result.status = ExportStatus.COMPLETED
            result.output_path = output_path
            result.file_size = file_size
            result.checksum = checksum
            result.metadata = metadata
            result.duration_ms = (time.time() - start_time) * 1000

        except Exception as e:
            result.status = ExportStatus.FAILED
            result.error = str(e)
            result.duration_ms = (time.time() - start_time) * 1000

        return result

    async def load(self, path: str) -> ImportResult:
        start_time = time.time()
        result = ImportResult(source_path=path)

        try:
            with open(path, "rb") as f:
                magic = f.read(4)
                if magic != self.MAGIC:
                    raise ValueError("Invalid BAEL export file")

                version = int.from_bytes(f.read(4), "big")

                meta_len = int.from_bytes(f.read(8), "big")
                meta_bytes = f.read(meta_len)

                model_len = int.from_bytes(f.read(8), "big")
                model_bytes = f.read(model_len)

            result.model = pickle.loads(model_bytes)

            meta_dict = json.loads(meta_bytes.decode())
            if meta_dict:
                result.metadata = ModelMetadata(**{
                    k: v for k, v in meta_dict.items()
                    if k != "created_at"
                })

            result.status = ExportStatus.COMPLETED
            result.duration_ms = (time.time() - start_time) * 1000

        except Exception as e:
            result.status = ExportStatus.FAILED
            result.error = str(e)
            result.duration_ms = (time.time() - start_time) * 1000

        return result


# =============================================================================
# EXPORT ENGINE
# =============================================================================

class ExportEngine:
    """
    Export Engine for BAEL.

    Comprehensive model export and conversion.
    """

    def __init__(self, output_dir: str = "./exports"):
        self._output_dir = Path(output_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)

        self._exporters: Dict[ExportFormat, BaseExporter] = {}
        self._exports: Dict[str, ExportResult] = {}

        self._register_default_exporters()

    def _register_default_exporters(self) -> None:
        """Register default exporters."""
        default_config = ExportConfig()

        self._exporters[ExportFormat.PICKLE] = PickleExporter(default_config)
        self._exporters[ExportFormat.JSON] = JSONExporter(default_config)
        self._exporters[ExportFormat.CUSTOM] = CustomBinaryExporter(default_config)

    def register_exporter(
        self,
        format: ExportFormat,
        exporter: BaseExporter
    ) -> None:
        """Register a custom exporter."""
        self._exporters[format] = exporter

    async def export(
        self,
        model: Any,
        name: str,
        format: ExportFormat = ExportFormat.PICKLE,
        metadata: Optional[ModelMetadata] = None,
        output_path: Optional[str] = None
    ) -> ExportResult:
        """Export a model."""
        if format not in self._exporters:
            return ExportResult(
                status=ExportStatus.FAILED,
                format=format,
                error=f"No exporter registered for format: {format.value}"
            )

        exporter = self._exporters[format]

        if output_path is None:
            output_path = str(self._output_dir / f"{name}{exporter.file_extension}")

        result = await exporter.export(model, output_path, metadata)

        self._exports[result.export_id] = result

        return result

    async def load(
        self,
        path: str,
        format: Optional[ExportFormat] = None
    ) -> ImportResult:
        """Load an exported model."""
        if format is None:
            format = self._detect_format(path)

        if format not in self._exporters:
            return ImportResult(
                status=ExportStatus.FAILED,
                source_path=path,
                error=f"No exporter registered for format: {format.value}"
            )

        exporter = self._exporters[format]
        return await exporter.load(path)

    def _detect_format(self, path: str) -> ExportFormat:
        """Detect format from file path."""
        ext = Path(path).suffix.lower()

        format_map = {
            ".pkl": ExportFormat.PICKLE,
            ".pickle": ExportFormat.PICKLE,
            ".json": ExportFormat.JSON,
            ".onnx": ExportFormat.ONNX,
            ".pt": ExportFormat.TORCHSCRIPT,
            ".tflite": ExportFormat.TENSORFLOW_LITE,
            ".safetensors": ExportFormat.SAFETENSORS,
            ".bin": ExportFormat.CUSTOM
        }

        return format_map.get(ext, ExportFormat.CUSTOM)

    async def convert(
        self,
        source_path: str,
        target_format: ExportFormat,
        output_path: Optional[str] = None
    ) -> ConversionResult:
        """Convert between formats."""
        start_time = time.time()
        result = ConversionResult(
            source_path=source_path,
            target_format=target_format
        )

        try:
            source_format = self._detect_format(source_path)
            result.source_format = source_format

            import_result = await self.load(source_path, source_format)

            if import_result.status != ExportStatus.COMPLETED:
                result.status = ExportStatus.FAILED
                result.error = f"Failed to load source: {import_result.error}"
                return result

            if output_path is None:
                exporter = self._exporters[target_format]
                base_name = Path(source_path).stem
                output_path = str(self._output_dir / f"{base_name}{exporter.file_extension}")

            export_result = await self.export(
                import_result.model,
                Path(output_path).stem,
                target_format,
                import_result.metadata,
                output_path
            )

            if export_result.status == ExportStatus.COMPLETED:
                result.status = ExportStatus.COMPLETED
                result.output_path = export_result.output_path
            else:
                result.status = ExportStatus.FAILED
                result.error = export_result.error

            result.duration_ms = (time.time() - start_time) * 1000

        except Exception as e:
            result.status = ExportStatus.FAILED
            result.error = str(e)
            result.duration_ms = (time.time() - start_time) * 1000

        return result

    def list_exports(self) -> List[ExportResult]:
        """List all exports."""
        return list(self._exports.values())

    def get_export(self, export_id: str) -> Optional[ExportResult]:
        """Get an export by ID."""
        return self._exports.get(export_id)

    def supported_formats(self) -> List[ExportFormat]:
        """List supported formats."""
        return list(self._exporters.keys())

    def summary(self) -> Dict[str, Any]:
        """Get engine summary."""
        return {
            "output_dir": str(self._output_dir),
            "supported_formats": [f.value for f in self._exporters.keys()],
            "total_exports": len(self._exports),
            "successful_exports": sum(
                1 for e in self._exports.values()
                if e.status == ExportStatus.COMPLETED
            ),
            "failed_exports": sum(
                1 for e in self._exports.values()
                if e.status == ExportStatus.FAILED
            )
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Export Engine."""
    print("=" * 70)
    print("BAEL - EXPORT ENGINE DEMO")
    print("Model Export and Conversion")
    print("=" * 70)
    print()

    engine = ExportEngine(output_dir="/tmp/bael_exports")

    # 1. Supported Formats
    print("1. SUPPORTED FORMATS:")
    print("-" * 40)

    formats = engine.supported_formats()
    for fmt in formats:
        print(f"   - {fmt.value}")
    print()

    # 2. Create Sample Model
    print("2. CREATE SAMPLE MODEL:")
    print("-" * 40)

    class SampleModel:
        def __init__(self):
            self.weights = [0.1, 0.2, 0.3, 0.4, 0.5]
            self.bias = 0.01
            self.layers = ["input", "hidden", "output"]

        def to_dict(self):
            return {
                "weights": self.weights,
                "bias": self.bias,
                "layers": self.layers
            }

        def predict(self, x):
            return sum(w * xi for w, xi in zip(self.weights, x)) + self.bias

    model = SampleModel()

    print(f"   Weights: {model.weights}")
    print(f"   Bias: {model.bias}")
    print()

    # 3. Create Metadata
    print("3. CREATE METADATA:")
    print("-" * 40)

    metadata = ModelMetadata(
        name="sample-model",
        version="1.0.0",
        description="A sample model for export demo",
        author="BAEL",
        framework="pure-python",
        input_schema={"type": "list", "length": 5},
        output_schema={"type": "float"},
        hyperparameters={"learning_rate": 0.001},
        metrics={"accuracy": 0.95, "loss": 0.05},
        tags=["demo", "sample"]
    )

    print(f"   Name: {metadata.name}")
    print(f"   Version: {metadata.version}")
    print(f"   Tags: {metadata.tags}")
    print()

    # 4. Export to Pickle
    print("4. EXPORT TO PICKLE:")
    print("-" * 40)

    pickle_result = await engine.export(
        model,
        "sample-model",
        ExportFormat.PICKLE,
        metadata
    )

    print(f"   Status: {pickle_result.status.value}")
    print(f"   Path: {pickle_result.output_path}")
    print(f"   Size: {pickle_result.file_size} bytes")
    print(f"   Duration: {pickle_result.duration_ms:.2f}ms")
    print()

    # 5. Export to JSON
    print("5. EXPORT TO JSON:")
    print("-" * 40)

    json_result = await engine.export(
        model,
        "sample-model",
        ExportFormat.JSON,
        metadata
    )

    print(f"   Status: {json_result.status.value}")
    print(f"   Path: {json_result.output_path}")
    print(f"   Size: {json_result.file_size} bytes")
    print()

    # 6. Export to Custom Binary
    print("6. EXPORT TO CUSTOM BINARY:")
    print("-" * 40)

    custom_result = await engine.export(
        model,
        "sample-model",
        ExportFormat.CUSTOM,
        metadata
    )

    print(f"   Status: {custom_result.status.value}")
    print(f"   Checksum: {custom_result.checksum}")
    print()

    # 7. Load Pickle Export
    print("7. LOAD PICKLE EXPORT:")
    print("-" * 40)

    import_result = await engine.load(pickle_result.output_path)

    print(f"   Status: {import_result.status.value}")
    print(f"   Model type: {type(import_result.model).__name__}")

    if import_result.model:
        print(f"   Weights: {import_result.model.weights}")
    print()

    # 8. Load JSON Export
    print("8. LOAD JSON EXPORT:")
    print("-" * 40)

    json_import = await engine.load(json_result.output_path)

    print(f"   Status: {json_import.status.value}")
    print(f"   Model data: {json_import.model}")
    print()

    # 9. Convert Formats
    print("9. CONVERT PICKLE TO JSON:")
    print("-" * 40)

    convert_result = await engine.convert(
        pickle_result.output_path,
        ExportFormat.JSON
    )

    print(f"   Status: {convert_result.status.value}")
    print(f"   Source: {convert_result.source_format.value}")
    print(f"   Target: {convert_result.target_format.value}")
    print(f"   Output: {convert_result.output_path}")
    print()

    # 10. Engine Summary
    print("10. ENGINE SUMMARY:")
    print("-" * 40)

    summary = engine.summary()

    print(f"   Output dir: {summary['output_dir']}")
    print(f"   Formats: {summary['supported_formats']}")
    print(f"   Total exports: {summary['total_exports']}")
    print(f"   Successful: {summary['successful_exports']}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Export Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())

#!/usr/bin/env python3
"""
BAEL - Quantization Engine
Model quantization for efficient inference.

Features:
- Post-training quantization
- Dynamic quantization
- Quantization-aware training
- Mixed precision support
- Calibration
"""

import asyncio
import json
import math
import os
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

class QuantizationType(Enum):
    """Quantization types."""
    DYNAMIC = "dynamic"
    STATIC = "static"
    QUANTIZATION_AWARE = "quantization_aware"


class QuantizationMode(Enum):
    """Quantization modes."""
    INT8 = "int8"
    INT4 = "int4"
    FLOAT16 = "float16"
    BFLOAT16 = "bfloat16"
    MIXED = "mixed"


class CalibrationMethod(Enum):
    """Calibration methods."""
    MINMAX = "minmax"
    HISTOGRAM = "histogram"
    ENTROPY = "entropy"
    PERCENTILE = "percentile"


class QuantizationStatus(Enum):
    """Quantization status."""
    PENDING = "pending"
    CALIBRATING = "calibrating"
    QUANTIZING = "quantizing"
    COMPLETED = "completed"
    FAILED = "failed"


class LayerType(Enum):
    """Layer types for quantization."""
    LINEAR = "linear"
    CONV = "conv"
    EMBEDDING = "embedding"
    ATTENTION = "attention"
    NORMALIZATION = "normalization"
    ACTIVATION = "activation"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class QuantizationConfig:
    """Quantization configuration."""
    quant_type: QuantizationType = QuantizationType.DYNAMIC
    mode: QuantizationMode = QuantizationMode.INT8
    calibration_method: CalibrationMethod = CalibrationMethod.MINMAX
    calibration_samples: int = 100
    per_channel: bool = True
    symmetric: bool = True
    preserve_accuracy: bool = True
    target_layers: List[LayerType] = field(default_factory=list)
    exclude_layers: List[str] = field(default_factory=list)


@dataclass
class QuantizationScale:
    """Quantization scale and zero point."""
    scale: float = 1.0
    zero_point: int = 0
    min_val: float = 0.0
    max_val: float = 0.0
    num_bits: int = 8
    symmetric: bool = True
    per_channel: bool = False
    channel_scales: Optional[List[float]] = None


@dataclass
class LayerQuantInfo:
    """Quantization info for a layer."""
    layer_name: str = ""
    layer_type: LayerType = LayerType.LINEAR
    input_scale: QuantizationScale = field(default_factory=QuantizationScale)
    weight_scale: QuantizationScale = field(default_factory=QuantizationScale)
    output_scale: QuantizationScale = field(default_factory=QuantizationScale)
    is_quantized: bool = False
    original_dtype: str = "float32"
    quantized_dtype: str = "int8"


@dataclass
class CalibrationResult:
    """Calibration result."""
    calibration_id: str = ""
    layer_stats: Dict[str, Dict[str, float]] = field(default_factory=dict)
    num_samples: int = 0
    duration_ms: float = 0.0
    method: CalibrationMethod = CalibrationMethod.MINMAX

    def __post_init__(self):
        if not self.calibration_id:
            self.calibration_id = str(uuid.uuid4())[:8]


@dataclass
class QuantizationResult:
    """Quantization result."""
    result_id: str = ""
    status: QuantizationStatus = QuantizationStatus.PENDING
    config: QuantizationConfig = field(default_factory=QuantizationConfig)
    original_size_mb: float = 0.0
    quantized_size_mb: float = 0.0
    compression_ratio: float = 1.0
    layer_info: Dict[str, LayerQuantInfo] = field(default_factory=dict)
    accuracy_loss: float = 0.0
    duration_ms: float = 0.0
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not self.result_id:
            self.result_id = str(uuid.uuid4())[:8]


@dataclass
class QuantizedTensor:
    """Quantized tensor representation."""
    data: List[int] = field(default_factory=list)
    scale: QuantizationScale = field(default_factory=QuantizationScale)
    shape: Tuple[int, ...] = field(default_factory=tuple)
    original_dtype: str = "float32"

    def dequantize(self) -> List[float]:
        """Dequantize to float."""
        result = []
        for val in self.data:
            dequant = (val - self.scale.zero_point) * self.scale.scale
            result.append(dequant)
        return result


# =============================================================================
# QUANTIZATION OBSERVERS
# =============================================================================

class BaseObserver(ABC):
    """Abstract base observer for calibration."""

    def __init__(self, num_bits: int = 8, symmetric: bool = True):
        self._num_bits = num_bits
        self._symmetric = symmetric
        self._min_val = float("inf")
        self._max_val = float("-inf")

    @abstractmethod
    def observe(self, tensor: List[float]) -> None:
        """Observe tensor values."""
        pass

    @abstractmethod
    def calculate_scale(self) -> QuantizationScale:
        """Calculate quantization scale."""
        pass

    def reset(self) -> None:
        """Reset observer state."""
        self._min_val = float("inf")
        self._max_val = float("-inf")


class MinMaxObserver(BaseObserver):
    """Min-max observer."""

    def observe(self, tensor: List[float]) -> None:
        self._min_val = min(self._min_val, min(tensor))
        self._max_val = max(self._max_val, max(tensor))

    def calculate_scale(self) -> QuantizationScale:
        if self._symmetric:
            abs_max = max(abs(self._min_val), abs(self._max_val))
            qmin = -(1 << (self._num_bits - 1))
            qmax = (1 << (self._num_bits - 1)) - 1
            scale = abs_max / qmax if qmax > 0 else 1.0
            zero_point = 0
        else:
            qmin = 0
            qmax = (1 << self._num_bits) - 1
            scale = (self._max_val - self._min_val) / (qmax - qmin)
            scale = scale if scale > 0 else 1.0
            zero_point = int(round(-self._min_val / scale))

        return QuantizationScale(
            scale=scale,
            zero_point=zero_point,
            min_val=self._min_val,
            max_val=self._max_val,
            num_bits=self._num_bits,
            symmetric=self._symmetric
        )


class HistogramObserver(BaseObserver):
    """Histogram-based observer."""

    def __init__(
        self,
        num_bits: int = 8,
        symmetric: bool = True,
        num_bins: int = 2048
    ):
        super().__init__(num_bits, symmetric)
        self._num_bins = num_bins
        self._histogram: List[int] = [0] * num_bins
        self._bin_edges: List[float] = []

    def observe(self, tensor: List[float]) -> None:
        self._min_val = min(self._min_val, min(tensor))
        self._max_val = max(self._max_val, max(tensor))

        if not self._bin_edges:
            range_val = self._max_val - self._min_val
            if range_val <= 0:
                range_val = 1.0
            bin_width = range_val / self._num_bins
            self._bin_edges = [
                self._min_val + i * bin_width
                for i in range(self._num_bins + 1)
            ]

        for val in tensor:
            bin_idx = min(
                int((val - self._min_val) / (self._max_val - self._min_val) * self._num_bins),
                self._num_bins - 1
            )
            bin_idx = max(0, bin_idx)
            self._histogram[bin_idx] += 1

    def calculate_scale(self) -> QuantizationScale:
        total = sum(self._histogram)
        cumsum = 0
        p01_idx = 0
        p99_idx = self._num_bins - 1

        for i, count in enumerate(self._histogram):
            cumsum += count
            if cumsum >= total * 0.01 and p01_idx == 0:
                p01_idx = i
            if cumsum >= total * 0.99:
                p99_idx = i
                break

        range_val = self._max_val - self._min_val
        if range_val <= 0:
            range_val = 1.0

        bin_width = range_val / self._num_bins
        adjusted_min = self._min_val + p01_idx * bin_width
        adjusted_max = self._min_val + p99_idx * bin_width

        if self._symmetric:
            abs_max = max(abs(adjusted_min), abs(adjusted_max))
            qmax = (1 << (self._num_bits - 1)) - 1
            scale = abs_max / qmax if qmax > 0 else 1.0
            zero_point = 0
        else:
            qmax = (1 << self._num_bits) - 1
            scale = (adjusted_max - adjusted_min) / qmax
            scale = scale if scale > 0 else 1.0
            zero_point = int(round(-adjusted_min / scale))

        return QuantizationScale(
            scale=scale,
            zero_point=zero_point,
            min_val=adjusted_min,
            max_val=adjusted_max,
            num_bits=self._num_bits,
            symmetric=self._symmetric
        )


class PercentileObserver(BaseObserver):
    """Percentile-based observer."""

    def __init__(
        self,
        num_bits: int = 8,
        symmetric: bool = True,
        percentile: float = 99.9
    ):
        super().__init__(num_bits, symmetric)
        self._percentile = percentile
        self._values: List[float] = []

    def observe(self, tensor: List[float]) -> None:
        self._values.extend(tensor)
        self._min_val = min(self._min_val, min(tensor))
        self._max_val = max(self._max_val, max(tensor))

    def calculate_scale(self) -> QuantizationScale:
        if not self._values:
            return QuantizationScale()

        sorted_vals = sorted(self._values)
        n = len(sorted_vals)

        low_idx = int(n * (100 - self._percentile) / 100)
        high_idx = int(n * self._percentile / 100) - 1

        adjusted_min = sorted_vals[max(0, low_idx)]
        adjusted_max = sorted_vals[min(n - 1, high_idx)]

        if self._symmetric:
            abs_max = max(abs(adjusted_min), abs(adjusted_max))
            qmax = (1 << (self._num_bits - 1)) - 1
            scale = abs_max / qmax if qmax > 0 else 1.0
            zero_point = 0
        else:
            qmax = (1 << self._num_bits) - 1
            scale = (adjusted_max - adjusted_min) / qmax
            scale = scale if scale > 0 else 1.0
            zero_point = int(round(-adjusted_min / scale))

        return QuantizationScale(
            scale=scale,
            zero_point=zero_point,
            min_val=adjusted_min,
            max_val=adjusted_max,
            num_bits=self._num_bits,
            symmetric=self._symmetric
        )


# =============================================================================
# QUANTIZERS
# =============================================================================

class BaseQuantizer(ABC):
    """Abstract base quantizer."""

    def __init__(self, config: QuantizationConfig):
        self._config = config

    @abstractmethod
    def quantize(
        self,
        tensor: List[float],
        scale: QuantizationScale
    ) -> QuantizedTensor:
        """Quantize a tensor."""
        pass

    @abstractmethod
    def dequantize(self, qtensor: QuantizedTensor) -> List[float]:
        """Dequantize a tensor."""
        pass


class Int8Quantizer(BaseQuantizer):
    """INT8 quantizer."""

    def quantize(
        self,
        tensor: List[float],
        scale: QuantizationScale
    ) -> QuantizedTensor:
        qmin = -(1 << 7) if scale.symmetric else 0
        qmax = (1 << 7) - 1 if scale.symmetric else 255

        quantized = []
        for val in tensor:
            q = round(val / scale.scale) + scale.zero_point
            q = max(qmin, min(qmax, int(q)))
            quantized.append(q)

        return QuantizedTensor(
            data=quantized,
            scale=scale,
            shape=(len(tensor),),
            original_dtype="float32"
        )

    def dequantize(self, qtensor: QuantizedTensor) -> List[float]:
        return qtensor.dequantize()


class Int4Quantizer(BaseQuantizer):
    """INT4 quantizer."""

    def quantize(
        self,
        tensor: List[float],
        scale: QuantizationScale
    ) -> QuantizedTensor:
        qmin = -8 if scale.symmetric else 0
        qmax = 7 if scale.symmetric else 15

        quantized = []
        for val in tensor:
            q = round(val / scale.scale) + scale.zero_point
            q = max(qmin, min(qmax, int(q)))
            quantized.append(q)

        return QuantizedTensor(
            data=quantized,
            scale=scale,
            shape=(len(tensor),),
            original_dtype="float32"
        )

    def dequantize(self, qtensor: QuantizedTensor) -> List[float]:
        return qtensor.dequantize()


class Float16Quantizer(BaseQuantizer):
    """Float16 quantizer (simulated)."""

    def quantize(
        self,
        tensor: List[float],
        scale: QuantizationScale
    ) -> QuantizedTensor:
        quantized = []
        for val in tensor:
            fp16_val = self._float32_to_float16(val)
            quantized.append(int(fp16_val * 1000))

        return QuantizedTensor(
            data=quantized,
            scale=scale,
            shape=(len(tensor),),
            original_dtype="float32"
        )

    def _float32_to_float16(self, val: float) -> float:
        """Simulate float16 precision loss."""
        if val == 0:
            return 0.0

        sign = -1 if val < 0 else 1
        val = abs(val)

        if val > 65504:
            return sign * 65504
        if val < 6.1e-5:
            return 0.0

        mantissa_bits = 10
        precision = 2 ** (-mantissa_bits)

        return sign * round(val / precision) * precision

    def dequantize(self, qtensor: QuantizedTensor) -> List[float]:
        return [v / 1000.0 for v in qtensor.data]


# =============================================================================
# QUANTIZATION ENGINE
# =============================================================================

class QuantizationEngine:
    """
    Quantization Engine for BAEL.

    Model quantization for efficient inference.
    """

    def __init__(self):
        self._observers: Dict[CalibrationMethod, Type[BaseObserver]] = {
            CalibrationMethod.MINMAX: MinMaxObserver,
            CalibrationMethod.HISTOGRAM: HistogramObserver,
            CalibrationMethod.PERCENTILE: PercentileObserver
        }

        self._quantizers: Dict[QuantizationMode, Type[BaseQuantizer]] = {
            QuantizationMode.INT8: Int8Quantizer,
            QuantizationMode.INT4: Int4Quantizer,
            QuantizationMode.FLOAT16: Float16Quantizer
        }

        self._results: Dict[str, QuantizationResult] = {}
        self._calibrations: Dict[str, CalibrationResult] = {}

    def create_observer(
        self,
        method: CalibrationMethod = CalibrationMethod.MINMAX,
        num_bits: int = 8,
        symmetric: bool = True
    ) -> BaseObserver:
        """Create a calibration observer."""
        observer_cls = self._observers.get(method, MinMaxObserver)
        return observer_cls(num_bits=num_bits, symmetric=symmetric)

    def create_quantizer(
        self,
        mode: QuantizationMode = QuantizationMode.INT8,
        config: Optional[QuantizationConfig] = None
    ) -> BaseQuantizer:
        """Create a quantizer."""
        config = config or QuantizationConfig(mode=mode)
        quantizer_cls = self._quantizers.get(mode, Int8Quantizer)
        return quantizer_cls(config)

    async def calibrate(
        self,
        layers: Dict[str, List[List[float]]],
        config: QuantizationConfig
    ) -> CalibrationResult:
        """Calibrate quantization scales using sample data."""
        start_time = time.time()

        result = CalibrationResult(
            method=config.calibration_method
        )

        num_bits = 8 if config.mode == QuantizationMode.INT8 else 4

        for layer_name, samples in layers.items():
            observer = self.create_observer(
                config.calibration_method,
                num_bits=num_bits,
                symmetric=config.symmetric
            )

            for sample in samples[:config.calibration_samples]:
                observer.observe(sample)

            scale = observer.calculate_scale()

            result.layer_stats[layer_name] = {
                "min": scale.min_val,
                "max": scale.max_val,
                "scale": scale.scale,
                "zero_point": scale.zero_point
            }
            result.num_samples += len(samples)

        result.duration_ms = (time.time() - start_time) * 1000

        self._calibrations[result.calibration_id] = result

        return result

    async def quantize_tensor(
        self,
        tensor: List[float],
        config: Optional[QuantizationConfig] = None,
        scale: Optional[QuantizationScale] = None
    ) -> QuantizedTensor:
        """Quantize a single tensor."""
        config = config or QuantizationConfig()

        if scale is None:
            observer = self.create_observer(
                config.calibration_method,
                num_bits=8 if config.mode == QuantizationMode.INT8 else 4,
                symmetric=config.symmetric
            )
            observer.observe(tensor)
            scale = observer.calculate_scale()

        quantizer = self.create_quantizer(config.mode, config)

        return quantizer.quantize(tensor, scale)

    async def quantize_model(
        self,
        model_weights: Dict[str, List[float]],
        config: Optional[QuantizationConfig] = None
    ) -> QuantizationResult:
        """Quantize a model's weights."""
        start_time = time.time()
        config = config or QuantizationConfig()

        result = QuantizationResult(
            config=config,
            status=QuantizationStatus.CALIBRATING
        )

        try:
            original_size = sum(
                len(w) * 4 for w in model_weights.values()
            ) / (1024 * 1024)
            result.original_size_mb = original_size

            result.status = QuantizationStatus.QUANTIZING

            for layer_name, weights in model_weights.items():
                layer_type = self._detect_layer_type(layer_name)

                if layer_name in config.exclude_layers:
                    continue

                if config.target_layers and layer_type not in config.target_layers:
                    continue

                observer = self.create_observer(
                    config.calibration_method,
                    num_bits=8 if config.mode == QuantizationMode.INT8 else 4,
                    symmetric=config.symmetric
                )
                observer.observe(weights)
                scale = observer.calculate_scale()

                layer_info = LayerQuantInfo(
                    layer_name=layer_name,
                    layer_type=layer_type,
                    weight_scale=scale,
                    is_quantized=True,
                    original_dtype="float32",
                    quantized_dtype=config.mode.value
                )
                result.layer_info[layer_name] = layer_info

            bytes_per_element = {
                QuantizationMode.INT8: 1,
                QuantizationMode.INT4: 0.5,
                QuantizationMode.FLOAT16: 2,
                QuantizationMode.BFLOAT16: 2
            }

            bpe = bytes_per_element.get(config.mode, 1)
            quantized_size = sum(
                len(w) * bpe for w in model_weights.values()
            ) / (1024 * 1024)

            result.quantized_size_mb = quantized_size
            result.compression_ratio = original_size / quantized_size if quantized_size > 0 else 1.0
            result.status = QuantizationStatus.COMPLETED
            result.duration_ms = (time.time() - start_time) * 1000

        except Exception as e:
            result.status = QuantizationStatus.FAILED
            result.error = str(e)
            result.duration_ms = (time.time() - start_time) * 1000

        self._results[result.result_id] = result

        return result

    def _detect_layer_type(self, layer_name: str) -> LayerType:
        """Detect layer type from name."""
        name_lower = layer_name.lower()

        if "linear" in name_lower or "fc" in name_lower or "dense" in name_lower:
            return LayerType.LINEAR
        elif "conv" in name_lower:
            return LayerType.CONV
        elif "embed" in name_lower:
            return LayerType.EMBEDDING
        elif "attn" in name_lower or "attention" in name_lower:
            return LayerType.ATTENTION
        elif "norm" in name_lower or "bn" in name_lower or "ln" in name_lower:
            return LayerType.NORMALIZATION
        elif "relu" in name_lower or "gelu" in name_lower or "act" in name_lower:
            return LayerType.ACTIVATION

        return LayerType.LINEAR

    async def measure_accuracy_loss(
        self,
        original: List[float],
        quantized: QuantizedTensor
    ) -> float:
        """Measure accuracy loss from quantization."""
        dequantized = quantized.dequantize()

        if len(original) != len(dequantized):
            return 1.0

        mse = sum(
            (o - d) ** 2 for o, d in zip(original, dequantized)
        ) / len(original)

        original_var = sum(
            (o - sum(original) / len(original)) ** 2
            for o in original
        ) / len(original)

        if original_var == 0:
            return 0.0 if mse == 0 else 1.0

        return mse / original_var

    def get_result(self, result_id: str) -> Optional[QuantizationResult]:
        """Get a quantization result."""
        return self._results.get(result_id)

    def get_calibration(self, calibration_id: str) -> Optional[CalibrationResult]:
        """Get a calibration result."""
        return self._calibrations.get(calibration_id)

    def summary(self) -> Dict[str, Any]:
        """Get engine summary."""
        return {
            "supported_modes": [m.value for m in self._quantizers.keys()],
            "calibration_methods": [m.value for m in self._observers.keys()],
            "total_quantizations": len(self._results),
            "total_calibrations": len(self._calibrations),
            "successful_quantizations": sum(
                1 for r in self._results.values()
                if r.status == QuantizationStatus.COMPLETED
            )
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Quantization Engine."""
    print("=" * 70)
    print("BAEL - QUANTIZATION ENGINE DEMO")
    print("Model Quantization for Efficient Inference")
    print("=" * 70)
    print()

    engine = QuantizationEngine()

    # 1. Engine Capabilities
    print("1. ENGINE CAPABILITIES:")
    print("-" * 40)

    summary = engine.summary()
    print(f"   Modes: {summary['supported_modes']}")
    print(f"   Calibration: {summary['calibration_methods']}")
    print()

    # 2. Create Sample Weights
    print("2. CREATE SAMPLE WEIGHTS:")
    print("-" * 40)

    import random
    random.seed(42)

    model_weights = {
        "layer1.linear.weight": [random.gauss(0, 0.5) for _ in range(1000)],
        "layer2.conv.weight": [random.gauss(0, 0.3) for _ in range(500)],
        "layer3.attention.weight": [random.gauss(0, 0.4) for _ in range(800)],
        "layer4.fc.weight": [random.gauss(0, 0.6) for _ in range(1200)]
    }

    for name, weights in model_weights.items():
        print(f"   {name}: {len(weights)} params, range [{min(weights):.3f}, {max(weights):.3f}]")
    print()

    # 3. Calibrate
    print("3. CALIBRATE LAYERS:")
    print("-" * 40)

    calibration_data = {
        name: [weights] for name, weights in model_weights.items()
    }

    config = QuantizationConfig(
        calibration_method=CalibrationMethod.MINMAX,
        calibration_samples=100
    )

    calibration = await engine.calibrate(calibration_data, config)

    print(f"   Calibration ID: {calibration.calibration_id}")
    print(f"   Duration: {calibration.duration_ms:.2f}ms")

    for layer, stats in calibration.layer_stats.items():
        print(f"   {layer}: scale={stats['scale']:.6f}")
    print()

    # 4. Quantize Single Tensor
    print("4. QUANTIZE SINGLE TENSOR:")
    print("-" * 40)

    sample_tensor = [0.1, 0.5, -0.3, 0.8, -0.6, 0.2, -0.1, 0.4]

    qtensor = await engine.quantize_tensor(sample_tensor)

    print(f"   Original: {sample_tensor}")
    print(f"   Quantized: {qtensor.data}")
    print(f"   Scale: {qtensor.scale.scale:.6f}")

    dequantized = qtensor.dequantize()
    print(f"   Dequantized: {[round(v, 3) for v in dequantized]}")
    print()

    # 5. Measure Accuracy Loss
    print("5. MEASURE ACCURACY LOSS:")
    print("-" * 40)

    accuracy_loss = await engine.measure_accuracy_loss(sample_tensor, qtensor)

    print(f"   Relative Error: {accuracy_loss:.6f}")
    print(f"   Accuracy Retained: {(1 - accuracy_loss) * 100:.4f}%")
    print()

    # 6. INT8 Quantization
    print("6. INT8 MODEL QUANTIZATION:")
    print("-" * 40)

    int8_config = QuantizationConfig(
        mode=QuantizationMode.INT8,
        symmetric=True,
        per_channel=True
    )

    int8_result = await engine.quantize_model(model_weights, int8_config)

    print(f"   Status: {int8_result.status.value}")
    print(f"   Original: {int8_result.original_size_mb:.4f} MB")
    print(f"   Quantized: {int8_result.quantized_size_mb:.4f} MB")
    print(f"   Compression: {int8_result.compression_ratio:.2f}x")
    print()

    # 7. INT4 Quantization
    print("7. INT4 MODEL QUANTIZATION:")
    print("-" * 40)

    int4_config = QuantizationConfig(
        mode=QuantizationMode.INT4,
        symmetric=True
    )

    int4_result = await engine.quantize_model(model_weights, int4_config)

    print(f"   Original: {int4_result.original_size_mb:.4f} MB")
    print(f"   Quantized: {int4_result.quantized_size_mb:.4f} MB")
    print(f"   Compression: {int4_result.compression_ratio:.2f}x")
    print()

    # 8. Float16 Quantization
    print("8. FLOAT16 QUANTIZATION:")
    print("-" * 40)

    fp16_config = QuantizationConfig(mode=QuantizationMode.FLOAT16)

    fp16_result = await engine.quantize_model(model_weights, fp16_config)

    print(f"   Original: {fp16_result.original_size_mb:.4f} MB")
    print(f"   Quantized: {fp16_result.quantized_size_mb:.4f} MB")
    print(f"   Compression: {fp16_result.compression_ratio:.2f}x")
    print()

    # 9. Histogram Calibration
    print("9. HISTOGRAM CALIBRATION:")
    print("-" * 40)

    hist_config = QuantizationConfig(
        calibration_method=CalibrationMethod.HISTOGRAM
    )

    hist_calibration = await engine.calibrate(calibration_data, hist_config)

    print(f"   Method: {hist_calibration.method.value}")
    print(f"   Duration: {hist_calibration.duration_ms:.2f}ms")
    print()

    # 10. Layer Info
    print("10. LAYER QUANTIZATION INFO:")
    print("-" * 40)

    for layer_name, info in int8_result.layer_info.items():
        print(f"   {layer_name}:")
        print(f"      Type: {info.layer_type.value}")
        print(f"      Original: {info.original_dtype}")
        print(f"      Quantized: {info.quantized_dtype}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Quantization Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())

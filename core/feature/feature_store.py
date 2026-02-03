#!/usr/bin/env python3
"""
BAEL - Feature Store
Centralized feature management for ML.

Features:
- Feature registration
- Feature versioning
- Online/offline serving
- Feature lineage
- Feature statistics
"""

import asyncio
import hashlib
import json
import os
import random
import statistics
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import (Any, Callable, Dict, Generic, Iterator, List, Optional,
                    Set, Tuple, Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class FeatureType(Enum):
    """Feature data types."""
    INT = "int"
    FLOAT = "float"
    STRING = "string"
    BOOL = "bool"
    LIST = "list"
    EMBEDDING = "embedding"
    TIMESTAMP = "timestamp"


class ServingMode(Enum):
    """Feature serving modes."""
    ONLINE = "online"
    OFFLINE = "offline"
    BATCH = "batch"


class FeatureStatus(Enum):
    """Feature status."""
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    EXPERIMENTAL = "experimental"
    ARCHIVED = "archived"


class TransformationType(Enum):
    """Transformation types."""
    IDENTITY = "identity"
    NORMALIZE = "normalize"
    STANDARDIZE = "standardize"
    LOG = "log"
    BUCKETIZE = "bucketize"
    EMBED = "embed"
    HASH = "hash"


class AggregationType(Enum):
    """Aggregation types for feature engineering."""
    SUM = "sum"
    MEAN = "mean"
    MIN = "min"
    MAX = "max"
    COUNT = "count"
    STD = "std"
    LAST = "last"
    FIRST = "first"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class FeatureSchema:
    """Feature schema definition."""
    name: str
    feature_type: FeatureType = FeatureType.FLOAT
    description: str = ""
    nullable: bool = False
    default_value: Any = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    allowed_values: Optional[List[Any]] = None
    embedding_dim: Optional[int] = None


@dataclass
class FeatureMetadata:
    """Feature metadata."""
    feature_id: str = ""
    name: str = ""
    version: str = "1.0.0"
    status: FeatureStatus = FeatureStatus.ACTIVE
    schema: Optional[FeatureSchema] = None
    owner: str = ""
    description: str = ""
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    source: str = ""
    lineage: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.feature_id:
            self.feature_id = str(uuid.uuid4())[:8]


@dataclass
class FeatureValue:
    """Feature value with metadata."""
    feature_name: str
    value: Any
    entity_id: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    version: str = "1.0.0"


@dataclass
class FeatureVector:
    """Vector of feature values."""
    entity_id: str
    features: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    def to_list(self, feature_names: List[str]) -> List[Any]:
        """Convert to ordered list."""
        return [self.features.get(name) for name in feature_names]


@dataclass
class FeatureStats:
    """Feature statistics."""
    feature_name: str
    count: int = 0
    null_count: int = 0
    unique_count: int = 0
    mean: Optional[float] = None
    std: Optional[float] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    percentiles: Dict[str, float] = field(default_factory=dict)
    computed_at: datetime = field(default_factory=datetime.now)


@dataclass
class FeatureGroup:
    """Group of related features."""
    group_id: str = ""
    name: str = ""
    description: str = ""
    features: List[str] = field(default_factory=list)
    entity_id_column: str = "entity_id"
    timestamp_column: str = "timestamp"
    online_enabled: bool = True
    offline_enabled: bool = True
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not self.group_id:
            self.group_id = str(uuid.uuid4())[:8]


@dataclass
class FeatureTransform:
    """Feature transformation definition."""
    transform_id: str = ""
    name: str = ""
    input_features: List[str] = field(default_factory=list)
    output_feature: str = ""
    transform_type: TransformationType = TransformationType.IDENTITY
    params: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.transform_id:
            self.transform_id = str(uuid.uuid4())[:8]


@dataclass
class FeatureRequest:
    """Feature request for serving."""
    entity_ids: List[str] = field(default_factory=list)
    feature_names: List[str] = field(default_factory=list)
    timestamp: Optional[datetime] = None
    mode: ServingMode = ServingMode.ONLINE


@dataclass
class FeatureResponse:
    """Feature serving response."""
    request_id: str = ""
    vectors: List[FeatureVector] = field(default_factory=list)
    missing_features: List[str] = field(default_factory=list)
    latency_ms: float = 0.0

    def __post_init__(self):
        if not self.request_id:
            self.request_id = str(uuid.uuid4())[:8]


# =============================================================================
# FEATURE TRANSFORMERS
# =============================================================================

class BaseTransformer(ABC):
    """Abstract base transformer."""

    @property
    @abstractmethod
    def transform_type(self) -> TransformationType:
        """Get transformation type."""
        pass

    @abstractmethod
    def transform(self, value: Any, params: Dict[str, Any]) -> Any:
        """Transform a value."""
        pass


class IdentityTransformer(BaseTransformer):
    """Identity transformer (no-op)."""

    @property
    def transform_type(self) -> TransformationType:
        return TransformationType.IDENTITY

    def transform(self, value: Any, params: Dict[str, Any]) -> Any:
        return value


class NormalizeTransformer(BaseTransformer):
    """Min-max normalization transformer."""

    @property
    def transform_type(self) -> TransformationType:
        return TransformationType.NORMALIZE

    def transform(self, value: Any, params: Dict[str, Any]) -> Any:
        if value is None:
            return None

        min_val = params.get("min", 0)
        max_val = params.get("max", 1)

        if max_val == min_val:
            return 0.5

        return (float(value) - min_val) / (max_val - min_val)


class StandardizeTransformer(BaseTransformer):
    """Z-score standardization transformer."""

    @property
    def transform_type(self) -> TransformationType:
        return TransformationType.STANDARDIZE

    def transform(self, value: Any, params: Dict[str, Any]) -> Any:
        if value is None:
            return None

        mean = params.get("mean", 0)
        std = params.get("std", 1)

        if std == 0:
            return 0.0

        return (float(value) - mean) / std


class LogTransformer(BaseTransformer):
    """Log transformation."""

    @property
    def transform_type(self) -> TransformationType:
        return TransformationType.LOG

    def transform(self, value: Any, params: Dict[str, Any]) -> Any:
        import math

        if value is None or value <= 0:
            return None

        base = params.get("base", math.e)
        offset = params.get("offset", 0)

        return math.log(float(value) + offset) / math.log(base)


class BucketizeTransformer(BaseTransformer):
    """Bucketization transformer."""

    @property
    def transform_type(self) -> TransformationType:
        return TransformationType.BUCKETIZE

    def transform(self, value: Any, params: Dict[str, Any]) -> Any:
        if value is None:
            return None

        boundaries = params.get("boundaries", [])

        for i, boundary in enumerate(boundaries):
            if float(value) < boundary:
                return i

        return len(boundaries)


class HashTransformer(BaseTransformer):
    """Hash feature transformer."""

    @property
    def transform_type(self) -> TransformationType:
        return TransformationType.HASH

    def transform(self, value: Any, params: Dict[str, Any]) -> Any:
        if value is None:
            return None

        num_buckets = params.get("num_buckets", 1000)

        hash_value = int(hashlib.md5(str(value).encode()).hexdigest(), 16)

        return hash_value % num_buckets


# =============================================================================
# FEATURE STORE
# =============================================================================

class FeatureStore:
    """
    Feature Store for BAEL.

    Centralized feature management for ML.
    """

    def __init__(self, store_path: str = "./feature_store"):
        self._store_path = Path(store_path)
        self._store_path.mkdir(parents=True, exist_ok=True)

        self._features: Dict[str, FeatureMetadata] = {}
        self._feature_groups: Dict[str, FeatureGroup] = {}
        self._transforms: Dict[str, FeatureTransform] = {}

        self._online_store: Dict[str, Dict[str, Any]] = defaultdict(dict)
        self._offline_store: List[FeatureVector] = []

        self._transformers: Dict[TransformationType, BaseTransformer] = {
            TransformationType.IDENTITY: IdentityTransformer(),
            TransformationType.NORMALIZE: NormalizeTransformer(),
            TransformationType.STANDARDIZE: StandardizeTransformer(),
            TransformationType.LOG: LogTransformer(),
            TransformationType.BUCKETIZE: BucketizeTransformer(),
            TransformationType.HASH: HashTransformer()
        }

        self._stats_cache: Dict[str, FeatureStats] = {}

    def register_feature(
        self,
        name: str,
        feature_type: FeatureType = FeatureType.FLOAT,
        description: str = "",
        owner: str = "",
        tags: Optional[List[str]] = None,
        schema: Optional[FeatureSchema] = None
    ) -> FeatureMetadata:
        """Register a new feature."""
        if schema is None:
            schema = FeatureSchema(name=name, feature_type=feature_type)

        metadata = FeatureMetadata(
            name=name,
            schema=schema,
            description=description,
            owner=owner,
            tags=tags or []
        )

        self._features[name] = metadata

        return metadata

    def get_feature(self, name: str) -> Optional[FeatureMetadata]:
        """Get feature metadata."""
        return self._features.get(name)

    def list_features(
        self,
        status: Optional[FeatureStatus] = None,
        tag: Optional[str] = None
    ) -> List[FeatureMetadata]:
        """List all features."""
        features = list(self._features.values())

        if status:
            features = [f for f in features if f.status == status]

        if tag:
            features = [f for f in features if tag in f.tags]

        return features

    def create_feature_group(
        self,
        name: str,
        features: List[str],
        description: str = "",
        entity_id_column: str = "entity_id"
    ) -> FeatureGroup:
        """Create a feature group."""
        group = FeatureGroup(
            name=name,
            description=description,
            features=features,
            entity_id_column=entity_id_column
        )

        self._feature_groups[name] = group

        return group

    def get_feature_group(self, name: str) -> Optional[FeatureGroup]:
        """Get a feature group."""
        return self._feature_groups.get(name)

    def register_transform(
        self,
        name: str,
        input_features: List[str],
        output_feature: str,
        transform_type: TransformationType,
        params: Optional[Dict[str, Any]] = None
    ) -> FeatureTransform:
        """Register a feature transformation."""
        transform = FeatureTransform(
            name=name,
            input_features=input_features,
            output_feature=output_feature,
            transform_type=transform_type,
            params=params or {}
        )

        self._transforms[name] = transform

        return transform

    async def ingest(
        self,
        entity_id: str,
        features: Dict[str, Any],
        timestamp: Optional[datetime] = None
    ) -> None:
        """Ingest feature values."""
        timestamp = timestamp or datetime.now()

        for name, value in features.items():
            key = f"{entity_id}:{name}"
            self._online_store[key] = {
                "value": value,
                "timestamp": timestamp
            }

        vector = FeatureVector(
            entity_id=entity_id,
            features=features,
            timestamp=timestamp
        )
        self._offline_store.append(vector)

    async def ingest_batch(
        self,
        vectors: List[FeatureVector]
    ) -> int:
        """Ingest batch of feature vectors."""
        count = 0

        for vector in vectors:
            await self.ingest(
                vector.entity_id,
                vector.features,
                vector.timestamp
            )
            count += 1

        return count

    async def get_online_features(
        self,
        entity_ids: List[str],
        feature_names: List[str]
    ) -> FeatureResponse:
        """Get features from online store."""
        start_time = time.time()

        vectors = []
        missing = set()

        for entity_id in entity_ids:
            features = {}

            for name in feature_names:
                key = f"{entity_id}:{name}"
                if key in self._online_store:
                    features[name] = self._online_store[key]["value"]
                else:
                    missing.add(name)

            vectors.append(FeatureVector(
                entity_id=entity_id,
                features=features
            ))

        return FeatureResponse(
            vectors=vectors,
            missing_features=list(missing),
            latency_ms=(time.time() - start_time) * 1000
        )

    async def get_offline_features(
        self,
        entity_ids: List[str],
        feature_names: List[str],
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> FeatureResponse:
        """Get features from offline store."""
        query_start = time.time()

        vectors = []

        for vector in self._offline_store:
            if vector.entity_id not in entity_ids:
                continue

            if start_time and vector.timestamp < start_time:
                continue

            if end_time and vector.timestamp > end_time:
                continue

            filtered_features = {
                k: v for k, v in vector.features.items()
                if k in feature_names
            }

            vectors.append(FeatureVector(
                entity_id=vector.entity_id,
                features=filtered_features,
                timestamp=vector.timestamp
            ))

        return FeatureResponse(
            vectors=vectors,
            latency_ms=(time.time() - query_start) * 1000
        )

    async def serve(
        self,
        request: FeatureRequest
    ) -> FeatureResponse:
        """Serve features based on request."""
        if request.mode == ServingMode.ONLINE:
            return await self.get_online_features(
                request.entity_ids,
                request.feature_names
            )
        else:
            return await self.get_offline_features(
                request.entity_ids,
                request.feature_names
            )

    def apply_transform(
        self,
        transform_name: str,
        value: Any
    ) -> Any:
        """Apply a registered transformation."""
        transform = self._transforms.get(transform_name)
        if not transform:
            return value

        transformer = self._transformers.get(transform.transform_type)
        if not transformer:
            return value

        return transformer.transform(value, transform.params)

    async def compute_statistics(
        self,
        feature_name: str
    ) -> FeatureStats:
        """Compute feature statistics."""
        values = []

        for vector in self._offline_store:
            if feature_name in vector.features:
                val = vector.features[feature_name]
                if val is not None:
                    values.append(val)

        stats = FeatureStats(feature_name=feature_name)
        stats.count = len(values)

        if not values:
            return stats

        numeric_values = [v for v in values if isinstance(v, (int, float))]

        if numeric_values:
            stats.mean = statistics.mean(numeric_values)
            stats.std = statistics.stdev(numeric_values) if len(numeric_values) > 1 else 0
            stats.min_value = min(numeric_values)
            stats.max_value = max(numeric_values)

            sorted_vals = sorted(numeric_values)
            n = len(sorted_vals)
            stats.percentiles = {
                "p25": sorted_vals[int(n * 0.25)],
                "p50": sorted_vals[int(n * 0.50)],
                "p75": sorted_vals[int(n * 0.75)],
                "p99": sorted_vals[int(n * 0.99)]
            }

        stats.unique_count = len(set(str(v) for v in values))
        stats.null_count = sum(1 for v in self._offline_store if v.features.get(feature_name) is None)

        self._stats_cache[feature_name] = stats

        return stats

    def get_lineage(self, feature_name: str) -> Dict[str, Any]:
        """Get feature lineage."""
        feature = self._features.get(feature_name)
        if not feature:
            return {}

        lineage = {
            "feature": feature_name,
            "source": feature.source,
            "created_at": feature.created_at.isoformat(),
            "transforms": []
        }

        for transform in self._transforms.values():
            if feature_name in transform.input_features:
                lineage["transforms"].append({
                    "name": transform.name,
                    "output": transform.output_feature,
                    "type": transform.transform_type.value
                })

        return lineage

    def deprecate_feature(self, feature_name: str) -> bool:
        """Deprecate a feature."""
        feature = self._features.get(feature_name)
        if feature:
            feature.status = FeatureStatus.DEPRECATED
            feature.updated_at = datetime.now()
            return True
        return False

    def summary(self) -> Dict[str, Any]:
        """Get store summary."""
        by_type = defaultdict(int)
        by_status = defaultdict(int)

        for f in self._features.values():
            if f.schema:
                by_type[f.schema.feature_type.value] += 1
            by_status[f.status.value] += 1

        return {
            "store_path": str(self._store_path),
            "total_features": len(self._features),
            "feature_groups": len(self._feature_groups),
            "transforms": len(self._transforms),
            "online_entries": len(self._online_store),
            "offline_entries": len(self._offline_store),
            "by_type": dict(by_type),
            "by_status": dict(by_status)
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Feature Store."""
    print("=" * 70)
    print("BAEL - FEATURE STORE DEMO")
    print("Centralized Feature Management")
    print("=" * 70)
    print()

    store = FeatureStore(store_path="/tmp/bael_features")

    # 1. Register Features
    print("1. REGISTER FEATURES:")
    print("-" * 40)

    age = store.register_feature(
        name="user_age",
        feature_type=FeatureType.INT,
        description="User age in years",
        owner="data-team",
        tags=["user", "demographic"]
    )

    income = store.register_feature(
        name="user_income",
        feature_type=FeatureType.FLOAT,
        description="Annual income",
        owner="data-team",
        tags=["user", "financial"]
    )

    clicks = store.register_feature(
        name="click_count",
        feature_type=FeatureType.INT,
        description="Total clicks",
        tags=["behavior"]
    )

    print(f"   Registered: {age.name} (id={age.feature_id})")
    print(f"   Registered: {income.name}")
    print(f"   Registered: {clicks.name}")
    print()

    # 2. Create Feature Group
    print("2. CREATE FEATURE GROUP:")
    print("-" * 40)

    group = store.create_feature_group(
        name="user_features",
        features=["user_age", "user_income", "click_count"],
        description="Core user features"
    )

    print(f"   Group: {group.name}")
    print(f"   Features: {group.features}")
    print()

    # 3. Register Transforms
    print("3. REGISTER TRANSFORMS:")
    print("-" * 40)

    store.register_transform(
        name="normalize_income",
        input_features=["user_income"],
        output_feature="income_normalized",
        transform_type=TransformationType.NORMALIZE,
        params={"min": 0, "max": 500000}
    )

    store.register_transform(
        name="bucketize_age",
        input_features=["user_age"],
        output_feature="age_bucket",
        transform_type=TransformationType.BUCKETIZE,
        params={"boundaries": [18, 25, 35, 50, 65]}
    )

    print("   Registered: normalize_income")
    print("   Registered: bucketize_age")
    print()

    # 4. Ingest Features
    print("4. INGEST FEATURES:")
    print("-" * 40)

    for i in range(100):
        await store.ingest(
            entity_id=f"user_{i}",
            features={
                "user_age": random.randint(18, 80),
                "user_income": random.uniform(20000, 200000),
                "click_count": random.randint(0, 1000)
            }
        )

    print("   Ingested 100 user feature vectors")
    print()

    # 5. Online Feature Serving
    print("5. ONLINE FEATURE SERVING:")
    print("-" * 40)

    request = FeatureRequest(
        entity_ids=["user_0", "user_1", "user_2"],
        feature_names=["user_age", "user_income"],
        mode=ServingMode.ONLINE
    )

    response = await store.serve(request)

    print(f"   Latency: {response.latency_ms:.2f}ms")

    for vector in response.vectors[:3]:
        print(f"   {vector.entity_id}: {vector.features}")
    print()

    # 6. Apply Transforms
    print("6. APPLY TRANSFORMS:")
    print("-" * 40)

    sample_income = 75000
    normalized = store.apply_transform("normalize_income", sample_income)

    sample_age = 32
    bucketed = store.apply_transform("bucketize_age", sample_age)

    print(f"   Income {sample_income} → normalized: {normalized:.4f}")
    print(f"   Age {sample_age} → bucket: {bucketed}")
    print()

    # 7. Compute Statistics
    print("7. COMPUTE STATISTICS:")
    print("-" * 40)

    age_stats = await store.compute_statistics("user_age")
    income_stats = await store.compute_statistics("user_income")

    print(f"   user_age:")
    print(f"      Mean: {age_stats.mean:.2f}")
    print(f"      Std: {age_stats.std:.2f}")
    print(f"      Range: [{age_stats.min_value}, {age_stats.max_value}]")

    print(f"   user_income:")
    print(f"      Mean: ${income_stats.mean:,.2f}")
    print(f"      P50: ${income_stats.percentiles.get('p50', 0):,.2f}")
    print()

    # 8. Feature Lineage
    print("8. FEATURE LINEAGE:")
    print("-" * 40)

    lineage = store.get_lineage("user_income")

    print(f"   Feature: {lineage.get('feature')}")
    print(f"   Transforms: {len(lineage.get('transforms', []))}")

    for t in lineage.get("transforms", []):
        print(f"      → {t['output']} ({t['type']})")
    print()

    # 9. List Features
    print("9. LIST FEATURES:")
    print("-" * 40)

    all_features = store.list_features()

    for f in all_features:
        print(f"   - {f.name}: {f.status.value} (tags: {f.tags})")
    print()

    # 10. Store Summary
    print("10. STORE SUMMARY:")
    print("-" * 40)

    summary = store.summary()

    print(f"   Total Features: {summary['total_features']}")
    print(f"   Feature Groups: {summary['feature_groups']}")
    print(f"   Transforms: {summary['transforms']}")
    print(f"   Online Entries: {summary['online_entries']}")
    print(f"   Offline Entries: {summary['offline_entries']}")
    print(f"   By Type: {summary['by_type']}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Feature Store Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())

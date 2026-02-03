#!/usr/bin/env python3
"""
BAEL - Feature Store
Advanced feature management for AI agent ML operations.

Features:
- Feature definitions and schemas
- Feature groups and namespaces
- Online/offline feature stores
- Feature versioning
- Point-in-time joins
- Feature transformations
- Feature serving
- Feature lineage tracking
"""

import asyncio
import copy
import hashlib
import json
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
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


class StoreType(Enum):
    """Feature store types."""
    ONLINE = "online"
    OFFLINE = "offline"
    BOTH = "both"


class TransformationType(Enum):
    """Feature transformation types."""
    IDENTITY = "identity"
    NORMALIZE = "normalize"
    STANDARDIZE = "standardize"
    LOG = "log"
    BUCKETIZE = "bucketize"
    HASH = "hash"
    EMBEDDING = "embedding"


class AggregationType(Enum):
    """Aggregation types for window features."""
    SUM = "sum"
    MEAN = "mean"
    MAX = "max"
    MIN = "min"
    COUNT = "count"
    LAST = "last"


class FeatureStatus(Enum):
    """Feature status."""
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    EXPERIMENTAL = "experimental"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class FeatureSchema:
    """Feature schema definition."""
    name: str
    dtype: FeatureType
    description: str = ""
    default_value: Any = None
    nullable: bool = True
    tags: List[str] = field(default_factory=list)


@dataclass
class FeatureDefinition:
    """Complete feature definition."""
    name: str
    schema: FeatureSchema
    version: int = 1
    status: FeatureStatus = FeatureStatus.ACTIVE
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    owner: str = ""
    source: str = ""
    transformation: Optional['Transformation'] = None
    dependencies: List[str] = field(default_factory=list)


@dataclass
class FeatureValue:
    """Feature value with metadata."""
    name: str
    value: Any
    timestamp: datetime = field(default_factory=datetime.now)
    version: int = 1
    entity_id: str = ""


@dataclass
class FeatureVector:
    """Vector of feature values."""
    entity_id: str
    features: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class FeatureGroupConfig:
    """Feature group configuration."""
    name: str
    description: str = ""
    entity_id_column: str = "entity_id"
    event_time_column: str = "event_time"
    ttl: Optional[timedelta] = None
    store_type: StoreType = StoreType.BOTH


@dataclass
class FeatureStats:
    """Feature statistics."""
    name: str
    count: int = 0
    null_count: int = 0
    min_value: Optional[Any] = None
    max_value: Optional[Any] = None
    mean_value: Optional[float] = None
    unique_count: int = 0


# =============================================================================
# TRANSFORMATION
# =============================================================================

@dataclass
class Transformation:
    """Feature transformation."""
    type: TransformationType
    params: Dict[str, Any] = field(default_factory=dict)

    def apply(self, value: Any) -> Any:
        """Apply transformation."""
        if self.type == TransformationType.IDENTITY:
            return value

        if self.type == TransformationType.NORMALIZE:
            min_val = self.params.get("min", 0)
            max_val = self.params.get("max", 1)
            if max_val == min_val:
                return 0.0
            return (float(value) - min_val) / (max_val - min_val)

        if self.type == TransformationType.STANDARDIZE:
            mean = self.params.get("mean", 0)
            std = self.params.get("std", 1)
            if std == 0:
                return 0.0
            return (float(value) - mean) / std

        if self.type == TransformationType.LOG:
            import math
            return math.log(max(float(value), 1e-10))

        if self.type == TransformationType.BUCKETIZE:
            boundaries = self.params.get("boundaries", [])
            val = float(value)
            for i, boundary in enumerate(boundaries):
                if val < boundary:
                    return i
            return len(boundaries)

        if self.type == TransformationType.HASH:
            num_buckets = self.params.get("num_buckets", 1000)
            h = hashlib.md5(str(value).encode()).hexdigest()
            return int(h, 16) % num_buckets

        return value


# =============================================================================
# ONLINE STORE
# =============================================================================

class OnlineStore:
    """In-memory online feature store."""

    def __init__(self, ttl: Optional[timedelta] = None):
        self._store: Dict[str, Dict[str, FeatureValue]] = defaultdict(dict)
        self._ttl = ttl

    def put(
        self,
        entity_id: str,
        feature_name: str,
        value: Any,
        timestamp: Optional[datetime] = None
    ) -> None:
        """Store feature value."""
        fv = FeatureValue(
            name=feature_name,
            value=value,
            timestamp=timestamp or datetime.now(),
            entity_id=entity_id
        )
        self._store[entity_id][feature_name] = fv

    def get(
        self,
        entity_id: str,
        feature_name: str
    ) -> Optional[Any]:
        """Get feature value."""
        if entity_id not in self._store:
            return None

        fv = self._store[entity_id].get(feature_name)

        if fv is None:
            return None

        # Check TTL
        if self._ttl:
            if datetime.now() - fv.timestamp > self._ttl:
                del self._store[entity_id][feature_name]
                return None

        return fv.value

    def get_all(self, entity_id: str) -> Dict[str, Any]:
        """Get all features for entity."""
        if entity_id not in self._store:
            return {}

        result = {}
        for name, fv in self._store[entity_id].items():
            if self._ttl and datetime.now() - fv.timestamp > self._ttl:
                continue
            result[name] = fv.value

        return result

    def delete(self, entity_id: str, feature_name: Optional[str] = None) -> bool:
        """Delete feature(s)."""
        if entity_id not in self._store:
            return False

        if feature_name:
            if feature_name in self._store[entity_id]:
                del self._store[entity_id][feature_name]
                return True
            return False
        else:
            del self._store[entity_id]
            return True

    def size(self) -> int:
        """Get total stored features."""
        return sum(len(features) for features in self._store.values())

    def entities(self) -> List[str]:
        """Get all entity IDs."""
        return list(self._store.keys())


# =============================================================================
# OFFLINE STORE
# =============================================================================

class OfflineStore:
    """Time-series offline feature store."""

    def __init__(self):
        self._store: Dict[str, List[FeatureValue]] = defaultdict(list)

    def put(
        self,
        entity_id: str,
        feature_name: str,
        value: Any,
        timestamp: datetime
    ) -> None:
        """Store feature value with timestamp."""
        key = f"{entity_id}:{feature_name}"
        fv = FeatureValue(
            name=feature_name,
            value=value,
            timestamp=timestamp,
            entity_id=entity_id
        )
        self._store[key].append(fv)
        self._store[key].sort(key=lambda x: x.timestamp)

    def get_latest(
        self,
        entity_id: str,
        feature_name: str,
        as_of: Optional[datetime] = None
    ) -> Optional[Any]:
        """Get latest value as of timestamp."""
        key = f"{entity_id}:{feature_name}"

        if key not in self._store:
            return None

        as_of = as_of or datetime.now()

        # Find latest value before as_of
        latest = None
        for fv in self._store[key]:
            if fv.timestamp <= as_of:
                latest = fv
            else:
                break

        return latest.value if latest else None

    def get_history(
        self,
        entity_id: str,
        feature_name: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None
    ) -> List[FeatureValue]:
        """Get feature history in time range."""
        key = f"{entity_id}:{feature_name}"

        if key not in self._store:
            return []

        result = []
        for fv in self._store[key]:
            if start and fv.timestamp < start:
                continue
            if end and fv.timestamp > end:
                break
            result.append(fv)

        return result

    def point_in_time_join(
        self,
        entity_ids: List[str],
        feature_names: List[str],
        timestamps: List[datetime]
    ) -> List[FeatureVector]:
        """Point-in-time join for training data."""
        result = []

        for entity_id, ts in zip(entity_ids, timestamps):
            features = {}

            for name in feature_names:
                value = self.get_latest(entity_id, name, ts)
                if value is not None:
                    features[name] = value

            result.append(FeatureVector(
                entity_id=entity_id,
                features=features,
                timestamp=ts
            ))

        return result


# =============================================================================
# FEATURE GROUP
# =============================================================================

class FeatureGroup:
    """Group of related features."""

    def __init__(self, config: FeatureGroupConfig):
        self.config = config
        self._definitions: Dict[str, FeatureDefinition] = {}
        self._online = OnlineStore(config.ttl)
        self._offline = OfflineStore()

    def add_feature(self, definition: FeatureDefinition) -> None:
        """Add feature definition."""
        self._definitions[definition.name] = definition

    def get_feature(self, name: str) -> Optional[FeatureDefinition]:
        """Get feature definition."""
        return self._definitions.get(name)

    def list_features(self) -> List[str]:
        """List feature names."""
        return list(self._definitions.keys())

    def ingest(
        self,
        entity_id: str,
        features: Dict[str, Any],
        timestamp: Optional[datetime] = None
    ) -> None:
        """Ingest feature values."""
        timestamp = timestamp or datetime.now()

        for name, value in features.items():
            if name not in self._definitions:
                continue

            defn = self._definitions[name]

            # Apply transformation
            if defn.transformation:
                value = defn.transformation.apply(value)

            # Store based on config
            if self.config.store_type in [StoreType.ONLINE, StoreType.BOTH]:
                self._online.put(entity_id, name, value, timestamp)

            if self.config.store_type in [StoreType.OFFLINE, StoreType.BOTH]:
                self._offline.put(entity_id, name, value, timestamp)

    def get_online(
        self,
        entity_id: str,
        feature_names: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Get online features."""
        if feature_names:
            result = {}
            for name in feature_names:
                value = self._online.get(entity_id, name)
                if value is not None:
                    result[name] = value
            return result
        else:
            return self._online.get_all(entity_id)

    def get_offline(
        self,
        entity_id: str,
        feature_names: List[str],
        as_of: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get offline features as of timestamp."""
        result = {}
        for name in feature_names:
            value = self._offline.get_latest(entity_id, name, as_of)
            if value is not None:
                result[name] = value
        return result

    def get_training_data(
        self,
        entity_ids: List[str],
        feature_names: List[str],
        timestamps: List[datetime]
    ) -> List[FeatureVector]:
        """Get training data with point-in-time correctness."""
        return self._offline.point_in_time_join(
            entity_ids, feature_names, timestamps
        )


# =============================================================================
# FEATURE REGISTRY
# =============================================================================

class FeatureRegistry:
    """Central registry for feature definitions."""

    def __init__(self):
        self._definitions: Dict[str, FeatureDefinition] = {}
        self._lineage: Dict[str, List[str]] = defaultdict(list)

    def register(self, definition: FeatureDefinition) -> None:
        """Register feature definition."""
        self._definitions[definition.name] = definition

        # Track lineage
        for dep in definition.dependencies:
            self._lineage[dep].append(definition.name)

    def get(self, name: str) -> Optional[FeatureDefinition]:
        """Get feature definition."""
        return self._definitions.get(name)

    def list_all(self) -> List[str]:
        """List all feature names."""
        return list(self._definitions.keys())

    def list_by_status(self, status: FeatureStatus) -> List[str]:
        """List features by status."""
        return [
            name for name, defn in self._definitions.items()
            if defn.status == status
        ]

    def list_by_tag(self, tag: str) -> List[str]:
        """List features by tag."""
        return [
            name for name, defn in self._definitions.items()
            if tag in defn.schema.tags
        ]

    def get_dependents(self, name: str) -> List[str]:
        """Get features that depend on this feature."""
        return self._lineage.get(name, [])

    def get_dependencies(self, name: str) -> List[str]:
        """Get features this feature depends on."""
        defn = self._definitions.get(name)
        return defn.dependencies if defn else []

    def deprecate(self, name: str) -> bool:
        """Deprecate a feature."""
        if name in self._definitions:
            self._definitions[name].status = FeatureStatus.DEPRECATED
            self._definitions[name].updated_at = datetime.now()
            return True
        return False


# =============================================================================
# FEATURE STORE MANAGER
# =============================================================================

class FeatureStoreManager:
    """
    Feature Store Manager for BAEL.

    Advanced feature management for ML operations.
    """

    def __init__(self):
        self._registry = FeatureRegistry()
        self._groups: Dict[str, FeatureGroup] = {}

    # -------------------------------------------------------------------------
    # FEATURE DEFINITIONS
    # -------------------------------------------------------------------------

    def define_feature(
        self,
        name: str,
        dtype: FeatureType,
        description: str = "",
        tags: Optional[List[str]] = None,
        transformation: Optional[Transformation] = None,
        dependencies: Optional[List[str]] = None
    ) -> FeatureDefinition:
        """Define a new feature."""
        schema = FeatureSchema(
            name=name,
            dtype=dtype,
            description=description,
            tags=tags or []
        )

        definition = FeatureDefinition(
            name=name,
            schema=schema,
            transformation=transformation,
            dependencies=dependencies or []
        )

        self._registry.register(definition)
        return definition

    def get_definition(self, name: str) -> Optional[FeatureDefinition]:
        """Get feature definition."""
        return self._registry.get(name)

    def list_features(self) -> List[str]:
        """List all defined features."""
        return self._registry.list_all()

    # -------------------------------------------------------------------------
    # FEATURE GROUPS
    # -------------------------------------------------------------------------

    def create_group(
        self,
        name: str,
        description: str = "",
        ttl: Optional[timedelta] = None,
        store_type: StoreType = StoreType.BOTH
    ) -> FeatureGroup:
        """Create feature group."""
        config = FeatureGroupConfig(
            name=name,
            description=description,
            ttl=ttl,
            store_type=store_type
        )

        group = FeatureGroup(config)
        self._groups[name] = group
        return group

    def get_group(self, name: str) -> Optional[FeatureGroup]:
        """Get feature group."""
        return self._groups.get(name)

    def list_groups(self) -> List[str]:
        """List feature groups."""
        return list(self._groups.keys())

    def add_to_group(
        self,
        group_name: str,
        feature_name: str
    ) -> bool:
        """Add feature to group."""
        group = self._groups.get(group_name)
        defn = self._registry.get(feature_name)

        if group and defn:
            group.add_feature(defn)
            return True
        return False

    # -------------------------------------------------------------------------
    # FEATURE INGESTION
    # -------------------------------------------------------------------------

    def ingest(
        self,
        group_name: str,
        entity_id: str,
        features: Dict[str, Any],
        timestamp: Optional[datetime] = None
    ) -> bool:
        """Ingest features to group."""
        group = self._groups.get(group_name)
        if group:
            group.ingest(entity_id, features, timestamp)
            return True
        return False

    def batch_ingest(
        self,
        group_name: str,
        records: List[Dict[str, Any]],
        entity_id_field: str = "entity_id",
        timestamp_field: str = "timestamp"
    ) -> int:
        """Batch ingest records."""
        group = self._groups.get(group_name)
        if not group:
            return 0

        count = 0
        for record in records:
            entity_id = record.get(entity_id_field)
            timestamp = record.get(timestamp_field)

            if not entity_id:
                continue

            features = {
                k: v for k, v in record.items()
                if k not in [entity_id_field, timestamp_field]
            }

            group.ingest(entity_id, features, timestamp)
            count += 1

        return count

    # -------------------------------------------------------------------------
    # FEATURE RETRIEVAL
    # -------------------------------------------------------------------------

    def get_online_features(
        self,
        group_name: str,
        entity_id: str,
        feature_names: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Get online features."""
        group = self._groups.get(group_name)
        if group:
            return group.get_online(entity_id, feature_names)
        return {}

    def get_offline_features(
        self,
        group_name: str,
        entity_id: str,
        feature_names: List[str],
        as_of: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get offline features."""
        group = self._groups.get(group_name)
        if group:
            return group.get_offline(entity_id, feature_names, as_of)
        return {}

    def get_training_data(
        self,
        group_name: str,
        entity_ids: List[str],
        feature_names: List[str],
        timestamps: List[datetime]
    ) -> List[FeatureVector]:
        """Get training data."""
        group = self._groups.get(group_name)
        if group:
            return group.get_training_data(entity_ids, feature_names, timestamps)
        return []

    # -------------------------------------------------------------------------
    # LINEAGE
    # -------------------------------------------------------------------------

    def get_dependents(self, feature_name: str) -> List[str]:
        """Get dependent features."""
        return self._registry.get_dependents(feature_name)

    def get_dependencies(self, feature_name: str) -> List[str]:
        """Get feature dependencies."""
        return self._registry.get_dependencies(feature_name)

    # -------------------------------------------------------------------------
    # MANAGEMENT
    # -------------------------------------------------------------------------

    def deprecate_feature(self, name: str) -> bool:
        """Deprecate a feature."""
        return self._registry.deprecate(name)

    def list_by_tag(self, tag: str) -> List[str]:
        """List features by tag."""
        return self._registry.list_by_tag(tag)

    def list_deprecated(self) -> List[str]:
        """List deprecated features."""
        return self._registry.list_by_status(FeatureStatus.DEPRECATED)


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Feature Store."""
    print("=" * 70)
    print("BAEL - FEATURE STORE DEMO")
    print("Advanced Feature Management for AI Agents")
    print("=" * 70)
    print()

    manager = FeatureStoreManager()

    # 1. Define Features
    print("1. DEFINE FEATURES:")
    print("-" * 40)

    age = manager.define_feature(
        "age",
        FeatureType.INT,
        description="User age in years",
        tags=["demographics", "user"]
    )

    income = manager.define_feature(
        "income",
        FeatureType.FLOAT,
        description="Annual income",
        tags=["financial", "user"],
        transformation=Transformation(TransformationType.LOG)
    )

    score = manager.define_feature(
        "score",
        FeatureType.FLOAT,
        description="Credit score",
        tags=["financial", "derived"],
        dependencies=["age", "income"]
    )

    print(f"   Defined: {manager.list_features()}")
    print()

    # 2. Create Feature Group
    print("2. CREATE FEATURE GROUP:")
    print("-" * 40)

    group = manager.create_group(
        "user_features",
        description="User feature group",
        ttl=timedelta(hours=24),
        store_type=StoreType.BOTH
    )

    manager.add_to_group("user_features", "age")
    manager.add_to_group("user_features", "income")

    print(f"   Groups: {manager.list_groups()}")
    print(f"   Features in group: {group.list_features()}")
    print()

    # 3. Ingest Features
    print("3. INGEST FEATURES:")
    print("-" * 40)

    manager.ingest(
        "user_features",
        "user_001",
        {"age": 30, "income": 75000}
    )

    manager.ingest(
        "user_features",
        "user_002",
        {"age": 45, "income": 120000}
    )

    print(f"   Ingested features for user_001 and user_002")
    print()

    # 4. Get Online Features
    print("4. GET ONLINE FEATURES:")
    print("-" * 40)

    features = manager.get_online_features("user_features", "user_001")
    print(f"   user_001: {features}")

    features = manager.get_online_features("user_features", "user_002", ["age"])
    print(f"   user_002 (age only): {features}")
    print()

    # 5. Batch Ingest
    print("5. BATCH INGEST:")
    print("-" * 40)

    records = [
        {"entity_id": "user_003", "age": 25, "income": 50000},
        {"entity_id": "user_004", "age": 55, "income": 200000},
        {"entity_id": "user_005", "age": 35, "income": 90000}
    ]

    count = manager.batch_ingest("user_features", records)
    print(f"   Ingested {count} records")
    print()

    # 6. Get Offline Features
    print("6. GET OFFLINE FEATURES:")
    print("-" * 40)

    features = manager.get_offline_features(
        "user_features",
        "user_001",
        ["age", "income"]
    )
    print(f"   user_001 offline: {features}")
    print()

    # 7. Point-in-Time Join
    print("7. POINT-IN-TIME JOIN:")
    print("-" * 40)

    from datetime import datetime
    now = datetime.now()

    training_data = manager.get_training_data(
        "user_features",
        ["user_001", "user_002"],
        ["age", "income"],
        [now, now]
    )

    for fv in training_data:
        print(f"   {fv.entity_id}: {fv.features}")
    print()

    # 8. Feature Lineage
    print("8. FEATURE LINEAGE:")
    print("-" * 40)

    deps = manager.get_dependencies("score")
    print(f"   'score' depends on: {deps}")

    dependents = manager.get_dependents("age")
    print(f"   Features depending on 'age': {dependents}")
    print()

    # 9. Tags
    print("9. FEATURES BY TAG:")
    print("-" * 40)

    financial = manager.list_by_tag("financial")
    print(f"   Financial features: {financial}")

    user = manager.list_by_tag("user")
    print(f"   User features: {user}")
    print()

    # 10. Deprecation
    print("10. DEPRECATE FEATURE:")
    print("-" * 40)

    deprecated = manager.deprecate_feature("score")
    print(f"   Deprecated 'score': {deprecated}")
    print(f"   Deprecated features: {manager.list_deprecated()}")
    print()

    # 11. Transformation
    print("11. TRANSFORMATION:")
    print("-" * 40)

    norm = Transformation(
        TransformationType.NORMALIZE,
        {"min": 0, "max": 100}
    )

    print(f"   Normalize 50: {norm.apply(50)}")
    print(f"   Normalize 100: {norm.apply(100)}")

    bucket = Transformation(
        TransformationType.BUCKETIZE,
        {"boundaries": [18, 30, 45, 60]}
    )

    print(f"   Bucket 25: {bucket.apply(25)}")
    print(f"   Bucket 50: {bucket.apply(50)}")
    print()

    # 12. Feature Definition Details
    print("12. FEATURE DEFINITION:")
    print("-" * 40)

    defn = manager.get_definition("age")
    if defn:
        print(f"   Name: {defn.name}")
        print(f"   Type: {defn.schema.dtype.value}")
        print(f"   Tags: {defn.schema.tags}")
        print(f"   Status: {defn.status.value}")
    print()

    # 13. Group Features
    print("13. GROUP FEATURES:")
    print("-" * 40)

    group = manager.get_group("user_features")
    if group:
        print(f"   Group: {group.config.name}")
        print(f"   Features: {group.list_features()}")
        print(f"   Store type: {group.config.store_type.value}")
    print()

    # 14. Online Store Size
    print("14. ONLINE STORE SIZE:")
    print("-" * 40)

    if group:
        print(f"   Size: {group._online.size()}")
        print(f"   Entities: {group._online.entities()}")
    print()

    # 15. Feature Stats
    print("15. FEATURE REGISTRY:")
    print("-" * 40)

    all_features = manager.list_features()
    print(f"   Total defined: {len(all_features)}")
    print(f"   Features: {all_features}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Feature Store Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())

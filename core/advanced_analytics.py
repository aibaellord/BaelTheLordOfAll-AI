"""
Advanced Analytics & Business Intelligence System

Comprehensive analytics system providing:
- User behavior analysis and segmentation
- Cohort analysis and lifecycle tracking
- Funnel analysis with conversion metrics
- Churn prediction with ML models
- Engagement metrics and scoring
- Feature adoption tracking
- RFM (Recency, Frequency, Monetary) analysis
- Custom report generation
- Data export capabilities
- Statistical analysis and forecasting

This module integrates with Phase 3 Analytics Engine and Phase 4 Monitoring System.
"""

import asyncio
import json
import logging
import pickle
import statistics
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from functools import lru_cache
from typing import (Any, Callable, Dict, List, Optional, Protocol, Set, Tuple,
                    Union)
from uuid import uuid4

import numpy as np
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (confusion_matrix, f1_score, precision_score,
                             recall_score, roc_auc_score)
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)


# ============================================================================
# ENUMS & TYPES
# ============================================================================

class SegmentationType(str, Enum):
    """Types of user segmentation"""
    BEHAVIORAL = "behavioral"
    DEMOGRAPHIC = "demographic"
    GEOGRAPHIC = "geographic"
    VALUE_BASED = "value_based"
    LIFECYCLE = "lifecycle"
    RFM = "rfm"
    CUSTOM = "custom"


class FunnelMetricType(str, Enum):
    """Types of funnel metrics"""
    CONVERSION_RATE = "conversion_rate"
    DROP_OFF = "drop_off"
    TIME_TO_CONVERSION = "time_to_conversion"
    COHORT_RETENTION = "cohort_retention"
    STEP_COMPLETION = "step_completion"


class ChurnRiskLevel(str, Enum):
    """Risk levels for churn prediction"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ReportFormat(str, Enum):
    """Supported report formats"""
    JSON = "json"
    CSV = "csv"
    EXCEL = "excel"
    PDF = "pdf"
    HTML = "html"


# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class UserEvent:
    """Represents a user event for analytics"""
    user_id: str
    event_type: str
    timestamp: datetime
    properties: Dict[str, Any] = field(default_factory=dict)
    session_id: Optional[str] = None
    source: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'user_id': self.user_id,
            'event_type': self.event_type,
            'timestamp': self.timestamp.isoformat(),
            'properties': self.properties,
            'session_id': self.session_id,
            'source': self.source
        }


@dataclass
class UserSegment:
    """Represents a user segment"""
    segment_id: str
    name: str
    segmentation_type: SegmentationType
    user_ids: Set[str] = field(default_factory=set)
    criteria: Dict[str, Any] = field(default_factory=dict)
    size: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            'segment_id': self.segment_id,
            'name': self.name,
            'type': self.segmentation_type.value,
            'size': len(self.user_ids),
            'criteria': self.criteria,
            'created_at': self.created_at.isoformat(),
            'last_updated': self.last_updated.isoformat()
        }


@dataclass
class CohortAnalysis:
    """Represents cohort analysis results"""
    cohort_id: str
    cohort_date: datetime
    metric_name: str
    cohort_size: int
    periods: List[int] = field(default_factory=list)  # weeks or months
    retention_rates: List[float] = field(default_factory=list)
    churn_rates: List[float] = field(default_factory=list)
    engagement_scores: List[float] = field(default_factory=list)
    lifetime_value: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'cohort_id': self.cohort_id,
            'cohort_date': self.cohort_date.isoformat(),
            'metric': self.metric_name,
            'size': self.cohort_size,
            'periods': self.periods,
            'retention': self.retention_rates,
            'churn': self.churn_rates,
            'engagement': self.engagement_scores,
            'ltv': self.lifetime_value
        }


@dataclass
class FunnelMetrics:
    """Represents funnel analysis metrics"""
    funnel_id: str
    name: str
    steps: List[str]
    start_date: datetime
    end_date: datetime
    total_users: int
    step_counts: Dict[str, int] = field(default_factory=dict)
    conversion_rates: Dict[str, float] = field(default_factory=dict)
    drop_off_rates: Dict[str, float] = field(default_factory=dict)
    avg_time_between_steps: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'funnel_id': self.funnel_id,
            'name': self.name,
            'steps': self.steps,
            'period': {'start': self.start_date.isoformat(), 'end': self.end_date.isoformat()},
            'total_users': self.total_users,
            'step_counts': self.step_counts,
            'conversion': self.conversion_rates,
            'dropoff': self.drop_off_rates,
            'avg_time': self.avg_time_between_steps
        }


@dataclass
class ChurnPrediction:
    """Represents churn prediction for a user"""
    user_id: str
    churn_probability: float
    risk_level: ChurnRiskLevel
    contributing_factors: Dict[str, float] = field(default_factory=dict)
    recommendation: str = ""
    prediction_date: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    confidence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'user_id': self.user_id,
            'churn_probability': self.churn_probability,
            'risk_level': self.risk_level.value,
            'factors': self.contributing_factors,
            'recommendation': self.recommendation,
            'confidence': self.confidence,
            'predicted_at': self.prediction_date.isoformat()
        }


@dataclass
class RFMScore:
    """Represents RFM analysis score"""
    user_id: str
    recency_score: float
    frequency_score: float
    monetary_score: float
    rfm_segment: str
    overall_score: float
    value_tier: str
    analysis_date: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            'user_id': self.user_id,
            'recency': self.recency_score,
            'frequency': self.frequency_score,
            'monetary': self.monetary_score,
            'segment': self.rfm_segment,
            'score': self.overall_score,
            'tier': self.value_tier,
            'analyzed_at': self.analysis_date.isoformat()
        }


@dataclass
class EngagementMetrics:
    """Represents engagement metrics for a user"""
    user_id: str
    session_count: int
    total_session_duration: float
    avg_session_duration: float
    event_count: int
    active_days: int
    retention_day_30: bool
    retention_day_90: bool
    engagement_score: float
    last_active: datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            'user_id': self.user_id,
            'sessions': self.session_count,
            'total_duration': self.total_session_duration,
            'avg_duration': self.avg_session_duration,
            'events': self.event_count,
            'active_days': self.active_days,
            'retention_30d': self.retention_day_30,
            'retention_90d': self.retention_day_90,
            'engagement': self.engagement_score,
            'last_active': self.last_active.isoformat()
        }


@dataclass
class CustomReport:
    """Represents a custom analytics report"""
    report_id: str
    name: str
    description: str
    metrics: List[str]
    filters: Dict[str, Any]
    dimensions: List[str]
    data: List[Dict[str, Any]] = field(default_factory=list)
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    generated_by: str = "system"
    format: ReportFormat = ReportFormat.JSON

    def to_dict(self) -> Dict[str, Any]:
        return {
            'report_id': self.report_id,
            'name': self.name,
            'description': self.description,
            'metrics': self.metrics,
            'dimensions': self.dimensions,
            'filters': self.filters,
            'rows': len(self.data),
            'format': self.format.value,
            'generated_at': self.generated_at.isoformat(),
            'generated_by': self.generated_by
        }


# ============================================================================
# ANALYTICS ENGINES
# ============================================================================

class UserBehaviorAnalyzer:
    """Analyzes user behavior patterns"""

    def __init__(self, window_days: int = 90):
        self.window_days = window_days
        self.user_events: Dict[str, List[UserEvent]] = {}
        self.user_sessions: Dict[str, List[Dict[str, Any]]] = {}
        self.scaler = StandardScaler()

    def track_event(self, event: UserEvent) -> None:
        """Track a user event"""
        if event.user_id not in self.user_events:
            self.user_events[event.user_id] = []
        self.user_events[event.user_id].append(event)

    def track_session(self, user_id: str, session_data: Dict[str, Any]) -> None:
        """Track a user session"""
        if user_id not in self.user_sessions:
            self.user_sessions[user_id] = []
        self.user_sessions[user_id].append(session_data)

    def get_engagement_metrics(self, user_id: str) -> EngagementMetrics:
        """Calculate engagement metrics for a user"""
        events = self.user_events.get(user_id, [])
        sessions = self.user_sessions.get(user_id, [])

        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(days=self.window_days)

        recent_events = [e for e in events if e.timestamp >= cutoff]
        recent_sessions = [s for s in sessions if s.get('start_time', now) >= cutoff]

        # Calculate metrics
        session_count = len(recent_sessions)
        total_duration = sum(s.get('duration', 0) for s in recent_sessions)
        avg_duration = total_duration / session_count if session_count > 0 else 0
        event_count = len(recent_events)

        # Active days
        active_dates = set()
        for event in recent_events:
            active_dates.add(event.timestamp.date())

        # Retention
        thirty_days_ago = now - timedelta(days=30)
        ninety_days_ago = now - timedelta(days=90)
        retention_30d = any(e.timestamp >= thirty_days_ago for e in events)
        retention_90d = any(e.timestamp >= ninety_days_ago for e in events)

        # Engagement score (0-100)
        engagement_score = min(100, (
            (session_count / 10) * 20 +  # Sessions weight
            (event_count / 50) * 20 +    # Events weight
            (len(active_dates) / self.window_days) * 30 +  # Active days weight
            (avg_duration / 600) * 20 +  # Duration weight (10 mins baseline)
            (10 if retention_30d else 0)  # Recent activity
        ))

        last_active = recent_events[-1].timestamp if recent_events else now

        return EngagementMetrics(
            user_id=user_id,
            session_count=session_count,
            total_session_duration=total_duration,
            avg_session_duration=avg_duration,
            event_count=event_count,
            active_days=len(active_dates),
            retention_day_30=retention_30d,
            retention_day_90=retention_90d,
            engagement_score=engagement_score,
            last_active=last_active
        )

    def segment_by_behavior(self, behavior_type: str) -> UserSegment:
        """Segment users by behavior type"""
        segment_id = str(uuid4())
        user_ids: Set[str] = set()

        for user_id in self.user_events.keys():
            metrics = self.get_engagement_metrics(user_id)

            if behavior_type == "active":
                if metrics.engagement_score >= 70:
                    user_ids.add(user_id)
            elif behavior_type == "at_risk":
                if metrics.engagement_score < 30 and metrics.session_count > 0:
                    user_ids.add(user_id)
            elif behavior_type == "dormant":
                if metrics.session_count == 0 or not metrics.retention_day_30:
                    user_ids.add(user_id)
            elif behavior_type == "power_user":
                if metrics.engagement_score >= 90 and metrics.session_count >= 20:
                    user_ids.add(user_id)

        return UserSegment(
            segment_id=segment_id,
            name=f"{behavior_type.replace('_', ' ').title()} Users",
            segmentation_type=SegmentationType.BEHAVIORAL,
            user_ids=user_ids,
            criteria={'behavior_type': behavior_type, 'threshold': 0.7}
        )


class CohortAnalyzer:
    """Analyzes user cohorts over time"""

    def __init__(self):
        self.cohort_data: Dict[str, Dict[str, Any]] = {}

    def create_cohort(self, cohort_id: str, cohort_date: datetime,
                     metric_name: str, user_ids: Set[str]) -> CohortAnalysis:
        """Create a new cohort"""
        self.cohort_data[cohort_id] = {
            'date': cohort_date,
            'metric': metric_name,
            'users': user_ids.copy(),
            'size': len(user_ids),
            'snapshots': {}
        }

        return CohortAnalysis(
            cohort_id=cohort_id,
            cohort_date=cohort_date,
            metric_name=metric_name,
            cohort_size=len(user_ids)
        )

    def add_cohort_snapshot(self, cohort_id: str, week: int,
                           retained_users: int, engagement_score: float,
                           revenue: float = 0.0) -> None:
        """Add a time snapshot for a cohort"""
        if cohort_id in self.cohort_data:
            cohort = self.cohort_data[cohort_id]
            cohort_size = cohort['size']
            retention_rate = retained_users / cohort_size if cohort_size > 0 else 0
            churn_rate = 1 - retention_rate

            cohort['snapshots'][week] = {
                'retained': retained_users,
                'retention_rate': retention_rate,
                'churn_rate': churn_rate,
                'engagement': engagement_score,
                'revenue': revenue
            }

    def get_cohort_analysis(self, cohort_id: str) -> Optional[CohortAnalysis]:
        """Retrieve cohort analysis"""
        if cohort_id not in self.cohort_data:
            return None

        cohort = self.cohort_data[cohort_id]
        snapshots = cohort['snapshots']

        periods = sorted(snapshots.keys())
        retention_rates = [snapshots[p]['retention_rate'] for p in periods]
        churn_rates = [snapshots[p]['churn_rate'] for p in periods]
        engagement_scores = [snapshots[p]['engagement'] for p in periods]
        lifetime_value = sum(snapshots[p]['revenue'] for p in periods)

        return CohortAnalysis(
            cohort_id=cohort_id,
            cohort_date=cohort['date'],
            metric_name=cohort['metric'],
            cohort_size=cohort['size'],
            periods=periods,
            retention_rates=retention_rates,
            churn_rates=churn_rates,
            engagement_scores=engagement_scores,
            lifetime_value=lifetime_value
        )

    def get_retention_curve(self, cohort_id: str) -> Tuple[List[int], List[float]]:
        """Get retention curve for visualization"""
        analysis = self.get_cohort_analysis(cohort_id)
        if not analysis:
            return [], []
        return analysis.periods, analysis.retention_rates


class FunnelAnalyzer:
    """Analyzes conversion funnels"""

    def __init__(self):
        self.funnels: Dict[str, Dict[str, Any]] = {}
        self.user_funnel_progress: Dict[str, Dict[str, int]] = {}

    def create_funnel(self, funnel_id: str, name: str, steps: List[str],
                     start_date: datetime, end_date: datetime) -> FunnelMetrics:
        """Create a new funnel"""
        self.funnels[funnel_id] = {
            'name': name,
            'steps': steps,
            'start_date': start_date,
            'end_date': end_date,
            'events': []
        }

        return FunnelMetrics(
            funnel_id=funnel_id,
            name=name,
            steps=steps,
            start_date=start_date,
            end_date=end_date,
            total_users=0
        )

    def track_funnel_event(self, funnel_id: str, user_id: str, step: str,
                          timestamp: datetime) -> None:
        """Track a user's progress through a funnel"""
        if funnel_id in self.funnels:
            self.funnels[funnel_id]['events'].append({
                'user_id': user_id,
                'step': step,
                'timestamp': timestamp
            })

            if user_id not in self.user_funnel_progress:
                self.user_funnel_progress[user_id] = {}
            if funnel_id not in self.user_funnel_progress[user_id]:
                self.user_funnel_progress[user_id][funnel_id] = 0

            step_index = self.funnels[funnel_id]['steps'].index(step)
            self.user_funnel_progress[user_id][funnel_id] = max(
                self.user_funnel_progress[user_id][funnel_id],
                step_index
            )

    def calculate_funnel_metrics(self, funnel_id: str) -> Optional[FunnelMetrics]:
        """Calculate comprehensive funnel metrics"""
        if funnel_id not in self.funnels:
            return None

        funnel = self.funnels[funnel_id]
        events = funnel['events']
        steps = funnel['steps']

        # Count users at each step
        step_users: Dict[str, Set[str]] = {step: set() for step in steps}
        for event in events:
            if event['step'] in step_users:
                step_users[event['step']].add(event['user_id'])

        step_counts = {step: len(step_users[step]) for step in steps}
        total_users = step_counts[steps[0]] if steps else 0

        # Calculate conversion rates
        conversion_rates = {}
        drop_off_rates = {}
        for i, step in enumerate(steps):
            if i == 0:
                conversion_rates[step] = 1.0
                drop_off_rates[step] = 0.0
            else:
                prev_step = steps[i - 1]
                prev_count = step_counts[prev_step]
                curr_count = step_counts[step]
                conversion_rates[step] = curr_count / prev_count if prev_count > 0 else 0
                drop_off_rates[prev_step] = 1 - conversion_rates[step]

        # Calculate average time between steps
        avg_times = {}
        for i in range(1, len(steps)):
            prev_step = steps[i - 1]
            curr_step = steps[i]
            times = []

            for user_id in step_users[curr_step]:
                prev_events = [e for e in events if e['user_id'] == user_id and e['step'] == prev_step]
                curr_events = [e for e in events if e['user_id'] == user_id and e['step'] == curr_step]

                if prev_events and curr_events:
                    time_diff = (curr_events[0]['timestamp'] - prev_events[0]['timestamp']).total_seconds()
                    if time_diff >= 0:
                        times.append(time_diff)

            avg_times[f"{prev_step}->{curr_step}"] = statistics.mean(times) if times else 0

        return FunnelMetrics(
            funnel_id=funnel_id,
            name=funnel['name'],
            steps=steps,
            start_date=funnel['start_date'],
            end_date=funnel['end_date'],
            total_users=total_users,
            step_counts=step_counts,
            conversion_rates=conversion_rates,
            drop_off_rates=drop_off_rates,
            avg_time_between_steps=avg_times
        )


class ChurnPredictor:
    """Predicts user churn using ML models"""

    def __init__(self):
        self.model = GradientBoostingClassifier(n_estimators=100, max_depth=5, random_state=42)
        self.scaler = StandardScaler()
        self.feature_names = [
            'session_count', 'event_count', 'avg_session_duration',
            'active_days', 'days_since_last_active', 'engagement_score'
        ]
        self.is_trained = False
        self.churn_threshold = 0.5

    def prepare_features(self, metrics: EngagementMetrics) -> np.ndarray:
        """Prepare features for prediction"""
        now = datetime.now(timezone.utc)
        days_since_active = (now - metrics.last_active).days

        features = np.array([
            metrics.session_count,
            metrics.event_count,
            metrics.avg_session_duration,
            metrics.active_days,
            days_since_active,
            metrics.engagement_score
        ]).reshape(1, -1)

        return features

    def train(self, training_data: List[Tuple[EngagementMetrics, bool]]) -> None:
        """Train churn prediction model"""
        if not training_data:
            return

        X = np.array([self.prepare_features(metrics).flatten() for metrics, _ in training_data])
        y = np.array([1 if churned else 0 for _, churned in training_data])

        X_scaled = self.scaler.fit_transform(X)
        self.model.fit(X_scaled, y)
        self.is_trained = True

    def predict_churn(self, metrics: EngagementMetrics) -> ChurnPrediction:
        """Predict churn for a user"""
        if not self.is_trained:
            return ChurnPrediction(
                user_id=metrics.user_id,
                churn_probability=0.0,
                risk_level=ChurnRiskLevel.LOW,
                confidence=0.0
            )

        features = self.prepare_features(metrics)
        features_scaled = self.scaler.transform(features)

        churn_probability = self.model.predict_proba(features_scaled)[0][1]

        # Determine risk level
        if churn_probability >= 0.75:
            risk_level = ChurnRiskLevel.CRITICAL
        elif churn_probability >= 0.5:
            risk_level = ChurnRiskLevel.HIGH
        elif churn_probability >= 0.3:
            risk_level = ChurnRiskLevel.MEDIUM
        else:
            risk_level = ChurnRiskLevel.LOW

        # Contributing factors
        contributing_factors = {}
        feature_importance = self.model.feature_importances_
        for name, importance in zip(self.feature_names, feature_importance):
            contributing_factors[name] = float(importance)

        # Recommendation
        recommendation = self._get_recommendation(metrics, risk_level)

        return ChurnPrediction(
            user_id=metrics.user_id,
            churn_probability=float(churn_probability),
            risk_level=risk_level,
            contributing_factors=contributing_factors,
            recommendation=recommendation,
            confidence=float(max(self.model.predict_proba(features_scaled)[0]))
        )

    def _get_recommendation(self, metrics: EngagementMetrics,
                           risk_level: ChurnRiskLevel) -> str:
        """Generate churn mitigation recommendation"""
        recommendations = {
            ChurnRiskLevel.CRITICAL: (
                "Immediate action needed: Reach out with personalized support, "
                "offer incentives or exclusive features"
            ),
            ChurnRiskLevel.HIGH: (
                "Increase engagement: Send targeted content, offer premium features trial, "
                "schedule check-in call"
            ),
            ChurnRiskLevel.MEDIUM: (
                "Monitor closely: Provide relevant resources, increase communication frequency"
            ),
            ChurnRiskLevel.LOW: (
                "Continue engagement: Regular feature updates, user success stories"
            )
        }
        return recommendations.get(risk_level, "")


class RFMAnalyzer:
    """Performs RFM (Recency, Frequency, Monetary) analysis"""

    def __init__(self, window_days: int = 365):
        self.window_days = window_days
        self.user_transactions: Dict[str, List[Dict[str, Any]]] = {}

    def add_transaction(self, user_id: str, amount: float, timestamp: datetime) -> None:
        """Add a transaction for a user"""
        if user_id not in self.user_transactions:
            self.user_transactions[user_id] = []
        self.user_transactions[user_id].append({
            'amount': amount,
            'timestamp': timestamp
        })

    def calculate_rfm(self, user_id: str) -> Optional[RFMScore]:
        """Calculate RFM score for a user"""
        if user_id not in self.user_transactions:
            return None

        transactions = self.user_transactions[user_id]
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(days=self.window_days)

        recent_transactions = [t for t in transactions if t['timestamp'] >= cutoff]

        if not recent_transactions:
            return RFMScore(
                user_id=user_id,
                recency_score=0.0,
                frequency_score=0.0,
                monetary_score=0.0,
                rfm_segment="inactive",
                overall_score=0.0,
                value_tier="low"
            )

        # Recency: days since last transaction
        last_transaction = max(t['timestamp'] for t in recent_transactions)
        days_since = (now - last_transaction).days
        recency_score = max(0, 100 - (days_since / self.window_days * 100))

        # Frequency: number of transactions
        frequency = len(recent_transactions)
        frequency_score = min(100, (frequency / 10) * 100)

        # Monetary: total spending
        monetary = sum(t['amount'] for t in recent_transactions)
        monetary_score = min(100, (monetary / 1000) * 100)  # $1000 baseline

        # Overall RFM score
        overall_score = (recency_score + frequency_score + monetary_score) / 3

        # Segment
        rfm_segment = self._determine_segment(recency_score, frequency_score, monetary_score)
        value_tier = self._determine_value_tier(overall_score)

        return RFMScore(
            user_id=user_id,
            recency_score=recency_score,
            frequency_score=frequency_score,
            monetary_score=monetary_score,
            rfm_segment=rfm_segment,
            overall_score=overall_score,
            value_tier=value_tier
        )

    def _determine_segment(self, r: float, f: float, m: float) -> str:
        """Determine RFM segment"""
        if r >= 75 and f >= 75 and m >= 75:
            return "champions"
        elif r >= 75 and f >= 50:
            return "loyal_customers"
        elif f >= 75 and m >= 75:
            return "at_risk"
        elif r >= 50 and f >= 50:
            return "potential"
        elif r < 25:
            return "dormant"
        else:
            return "active"

    def _determine_value_tier(self, score: float) -> str:
        """Determine value tier"""
        if score >= 80:
            return "premium"
        elif score >= 60:
            return "high"
        elif score >= 40:
            return "medium"
        else:
            return "low"


class ReportGenerator:
    """Generates custom analytics reports"""

    def __init__(self):
        self.reports: Dict[str, CustomReport] = {}

    def generate_report(self, name: str, description: str,
                       metrics: List[str], dimensions: List[str],
                       filters: Dict[str, Any],
                       data: List[Dict[str, Any]],
                       generated_by: str = "system",
                       format_type: ReportFormat = ReportFormat.JSON) -> CustomReport:
        """Generate a custom report"""
        report_id = str(uuid4())

        report = CustomReport(
            report_id=report_id,
            name=name,
            description=description,
            metrics=metrics,
            filters=filters,
            dimensions=dimensions,
            data=data,
            generated_by=generated_by,
            format=format_type
        )

        self.reports[report_id] = report
        return report

    def export_report(self, report_id: str, format_type: ReportFormat) -> Optional[str]:
        """Export report in specified format"""
        if report_id not in self.reports:
            return None

        report = self.reports[report_id]

        if format_type == ReportFormat.JSON:
            return json.dumps(report.to_dict(), default=str, indent=2)
        elif format_type == ReportFormat.CSV:
            return self._to_csv(report)
        elif format_type == ReportFormat.HTML:
            return self._to_html(report)

        return None

    def _to_csv(self, report: CustomReport) -> str:
        """Convert report to CSV"""
        if not report.data:
            return ""

        import csv
        from io import StringIO

        output = StringIO()
        fieldnames = list(report.data[0].keys()) if report.data else []
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(report.data)

        return output.getvalue()

    def _to_html(self, report: CustomReport) -> str:
        """Convert report to HTML"""
        html = f"""
        <html>
        <head>
            <title>{report.name}</title>
            <style>
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid black; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
            </style>
        </head>
        <body>
            <h1>{report.name}</h1>
            <p>{report.description}</p>
            <table>
                <tr>
                    {''.join(f'<th>{k}</th>' for k in report.data[0].keys())}
                </tr>
                {''.join(
                    '<tr>' + ''.join(f'<td>{v}</td>' for v in row.values()) + '</tr>'
                    for row in report.data
                )}
            </table>
        </body>
        </html>
        """
        return html


# ============================================================================
# MAIN ANALYTICS SYSTEM
# ============================================================================

class AdvancedAnalyticsSystem:
    """Unified advanced analytics and BI system"""

    def __init__(self):
        self.behavior_analyzer = UserBehaviorAnalyzer()
        self.cohort_analyzer = CohortAnalyzer()
        self.funnel_analyzer = FunnelAnalyzer()
        self.churn_predictor = ChurnPredictor()
        self.rfm_analyzer = RFMAnalyzer()
        self.report_generator = ReportGenerator()

        self.segments: Dict[str, UserSegment] = {}
        self.churn_predictions: Dict[str, ChurnPrediction] = {}

    def track_event(self, event: UserEvent) -> None:
        """Track a user event"""
        self.behavior_analyzer.track_event(event)

    def track_session(self, user_id: str, session_data: Dict[str, Any]) -> None:
        """Track a user session"""
        self.behavior_analyzer.track_session(user_id, session_data)

    def track_transaction(self, user_id: str, amount: float, timestamp: datetime) -> None:
        """Track a transaction for RFM analysis"""
        self.rfm_analyzer.add_transaction(user_id, amount, timestamp)

    def analyze_user_engagement(self, user_id: str) -> EngagementMetrics:
        """Analyze engagement for a user"""
        return self.behavior_analyzer.get_engagement_metrics(user_id)

    def create_behavioral_segment(self, behavior_type: str) -> UserSegment:
        """Create a behavioral segment"""
        segment = self.behavior_analyzer.segment_by_behavior(behavior_type)
        self.segments[segment.segment_id] = segment
        return segment

    def create_cohort(self, cohort_id: str, cohort_date: datetime,
                     metric_name: str, user_ids: Set[str]) -> CohortAnalysis:
        """Create a cohort for analysis"""
        return self.cohort_analyzer.create_cohort(cohort_id, cohort_date, metric_name, user_ids)

    def analyze_cohort(self, cohort_id: str) -> Optional[CohortAnalysis]:
        """Retrieve cohort analysis"""
        return self.cohort_analyzer.get_cohort_analysis(cohort_id)

    def create_funnel(self, funnel_id: str, name: str, steps: List[str],
                     start_date: datetime, end_date: datetime) -> FunnelMetrics:
        """Create a conversion funnel"""
        return self.funnel_analyzer.create_funnel(funnel_id, name, steps, start_date, end_date)

    def analyze_funnel(self, funnel_id: str) -> Optional[FunnelMetrics]:
        """Analyze a funnel"""
        return self.funnel_analyzer.calculate_funnel_metrics(funnel_id)

    def train_churn_model(self, training_data: List[Tuple[EngagementMetrics, bool]]) -> None:
        """Train the churn prediction model"""
        self.churn_predictor.train(training_data)

    def predict_user_churn(self, user_id: str) -> Optional[ChurnPrediction]:
        """Predict churn for a user"""
        metrics = self.behavior_analyzer.get_engagement_metrics(user_id)
        prediction = self.churn_predictor.predict_churn(metrics)
        self.churn_predictions[user_id] = prediction
        return prediction

    def calculate_rfm(self, user_id: str) -> Optional[RFMScore]:
        """Calculate RFM score"""
        return self.rfm_analyzer.calculate_rfm(user_id)

    def generate_custom_report(self, name: str, description: str,
                              metrics: List[str], dimensions: List[str],
                              filters: Dict[str, Any],
                              data: List[Dict[str, Any]]) -> CustomReport:
        """Generate a custom analytics report"""
        return self.report_generator.generate_report(
            name=name,
            description=description,
            metrics=metrics,
            dimensions=dimensions,
            filters=filters,
            data=data
        )

    def export_report(self, report_id: str, format_type: ReportFormat) -> Optional[str]:
        """Export a report"""
        return self.report_generator.export_report(report_id, format_type)

    def get_segment(self, segment_id: str) -> Optional[UserSegment]:
        """Retrieve a segment"""
        return self.segments.get(segment_id)

    def get_churn_predictions(self, risk_level: Optional[ChurnRiskLevel] = None) -> List[ChurnPrediction]:
        """Get churn predictions, optionally filtered by risk level"""
        predictions = list(self.churn_predictions.values())
        if risk_level:
            predictions = [p for p in predictions if p.risk_level == risk_level]
        return sorted(predictions, key=lambda p: p.churn_probability, reverse=True)


# ============================================================================
# SINGLETON ACCESS
# ============================================================================

_analytics_system: Optional[AdvancedAnalyticsSystem] = None


def get_advanced_analytics() -> AdvancedAnalyticsSystem:
    """Get or create the singleton AdvancedAnalyticsSystem instance"""
    global _analytics_system
    if _analytics_system is None:
        _analytics_system = AdvancedAnalyticsSystem()
    return _analytics_system


if __name__ == "__main__":
    # Example usage
    analytics = get_advanced_analytics()

    # Track events
    now = datetime.now(timezone.utc)
    event1 = UserEvent(
        user_id="user_123",
        event_type="page_view",
        timestamp=now,
        properties={"page": "home"}
    )
    analytics.track_event(event1)

    # Analyze engagement
    engagement = analytics.analyze_user_engagement("user_123")
    print(f"Engagement Score: {engagement.engagement_score}")

    # Create segment
    segment = analytics.create_behavioral_segment("active")
    print(f"Segment: {segment.name}, Size: {len(segment.user_ids)}")

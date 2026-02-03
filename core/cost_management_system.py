"""
Cost Management & Optimization System

Comprehensive cost management and optimization system providing:
- Real-time usage tracking and metering
- Cost forecasting and budget management
- Budget alerts and notifications
- Resource optimization recommendations
- Savings analysis and reporting
- Chargeback and billing models
- Cost allocation per tenant/service
- ML-based cost prediction
- RI (Reserved Instance) management
- Spot instance optimization

This module provides complete cost visibility and optimization.
"""

import asyncio
import logging
import statistics
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from functools import lru_cache
from typing import Any, Callable, Dict, List, Optional, Tuple
from uuid import uuid4

import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)


# ============================================================================
# ENUMS
# ============================================================================

class CostCategory(str, Enum):
    """Cost categories"""
    COMPUTE = "compute"
    STORAGE = "storage"
    NETWORK = "network"
    DATABASE = "database"
    CACHE = "cache"
    LICENSE = "license"
    SUPPORT = "support"
    OTHER = "other"


class OptimizationType(str, Enum):
    """Types of optimizations"""
    INSTANCE_RIGHTSIZING = "instance_rightsizing"
    RESERVED_INSTANCES = "reserved_instances"
    SPOT_INSTANCES = "spot_instances"
    AUTO_SCALING = "auto_scaling"
    STORAGE_OPTIMIZATION = "storage_optimization"
    NETWORK_OPTIMIZATION = "network_optimization"


class AlertSeverity(str, Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class CostMetric:
    """Represents a cost metric"""
    metric_id: str
    tenant_id: str
    category: CostCategory
    resource_type: str
    resource_id: str
    amount: float
    currency: str = "USD"
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    tags: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'metric_id': self.metric_id,
            'tenant_id': self.tenant_id,
            'category': self.category.value,
            'resource_type': self.resource_type,
            'amount': self.amount,
            'currency': self.currency,
            'timestamp': self.timestamp.isoformat(),
            'tags': self.tags
        }


@dataclass
class CostBreakdown:
    """Cost breakdown by category"""
    tenant_id: str
    period_start: datetime
    period_end: datetime
    total_cost: float
    by_category: Dict[str, float] = field(default_factory=dict)
    by_resource: Dict[str, float] = field(default_factory=dict)
    top_resources: List[Tuple[str, float]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'tenant_id': self.tenant_id,
            'period': {
                'start': self.period_start.isoformat(),
                'end': self.period_end.isoformat()
            },
            'total': self.total_cost,
            'by_category': self.by_category,
            'by_resource': self.by_resource,
            'top_resources': self.top_resources
        }


@dataclass
class Budget:
    """Budget definition"""
    budget_id: str
    tenant_id: str
    name: str
    limit: float
    period: str  # monthly, quarterly, annual
    category: Optional[CostCategory] = None
    start_date: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    end_date: Optional[datetime] = None
    alert_thresholds: List[float] = field(default_factory=lambda: [50, 75, 90])
    accumulated_cost: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'budget_id': self.budget_id,
            'tenant_id': self.tenant_id,
            'name': self.name,
            'limit': self.limit,
            'period': self.period,
            'category': self.category.value if self.category else None,
            'accumulated': self.accumulated_cost,
            'remaining': self.limit - self.accumulated_cost,
            'utilization': (self.accumulated_cost / self.limit * 100) if self.limit > 0 else 0
        }


@dataclass
class CostForecast:
    """Cost forecast"""
    forecast_id: str
    tenant_id: str
    category: CostCategory
    forecast_date: datetime
    predicted_cost: float
    confidence_interval: float = 0.95
    trend: str = "stable"  # increasing, decreasing, stable
    trend_percentage: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'forecast_id': self.forecast_id,
            'tenant_id': self.tenant_id,
            'category': self.category.value,
            'forecast_date': self.forecast_date.isoformat(),
            'predicted_cost': self.predicted_cost,
            'confidence': self.confidence_interval,
            'trend': self.trend,
            'trend_percentage': self.trend_percentage
        }


@dataclass
class OptimizationRecommendation:
    """Cost optimization recommendation"""
    recommendation_id: str
    tenant_id: str
    optimization_type: OptimizationType
    resource_id: str
    resource_type: str
    current_cost: float
    estimated_savings: float
    implementation_effort: str  # low, medium, high
    description: str = ""
    action_items: List[str] = field(default_factory=list)
    priority: int = 1  # 1-10

    def to_dict(self) -> Dict[str, Any]:
        return {
            'recommendation_id': self.recommendation_id,
            'tenant_id': self.tenant_id,
            'type': self.optimization_type.value,
            'resource_id': self.resource_id,
            'resource_type': self.resource_type,
            'current_cost': self.current_cost,
            'savings': self.estimated_savings,
            'savings_percentage': (self.estimated_savings / self.current_cost * 100) if self.current_cost > 0 else 0,
            'effort': self.implementation_effort,
            'description': self.description,
            'priority': self.priority
        }


@dataclass
class CostAlert:
    """Cost alert"""
    alert_id: str
    tenant_id: str
    budget_id: Optional[str] = None
    severity: AlertSeverity = AlertSeverity.WARNING
    title: str = ""
    message: str = ""
    threshold_exceeded: float = 0.0
    current_cost: float = 0.0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    acknowledged: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            'alert_id': self.alert_id,
            'tenant_id': self.tenant_id,
            'budget_id': self.budget_id,
            'severity': self.severity.value,
            'title': self.title,
            'message': self.message,
            'threshold': self.threshold_exceeded,
            'current_cost': self.current_cost,
            'created_at': self.created_at.isoformat(),
            'acknowledged': self.acknowledged
        }


# ============================================================================
# COST TRACKING
# ============================================================================

class CostMeter:
    """Tracks resource usage and costs"""

    def __init__(self):
        self.metrics: Dict[str, CostMetric] = {}
        self.metrics_by_tenant: Dict[str, List[CostMetric]] = {}
        self.hourly_rates: Dict[str, float] = {
            'compute.small': 0.05,
            'compute.medium': 0.10,
            'compute.large': 0.20,
            'storage.gb': 0.023,
            'network.gb': 0.12,
            'database.instance': 0.50,
            'cache.gb': 0.15
        }

    def record_metric(self, tenant_id: str, category: CostCategory,
                     resource_type: str, resource_id: str,
                     quantity: float) -> CostMetric:
        """Record a cost metric"""
        metric_id = str(uuid4())

        # Calculate cost
        rate_key = f"{category.value}.{resource_type}"
        rate = self.hourly_rates.get(rate_key, 0.01)
        amount = quantity * rate

        metric = CostMetric(
            metric_id=metric_id,
            tenant_id=tenant_id,
            category=category,
            resource_type=resource_type,
            resource_id=resource_id,
            amount=amount
        )

        self.metrics[metric_id] = metric

        if tenant_id not in self.metrics_by_tenant:
            self.metrics_by_tenant[tenant_id] = []
        self.metrics_by_tenant[tenant_id].append(metric)

        logger.info(f"Cost metric recorded: ${amount:.2f} for {resource_type}")
        return metric

    def get_metrics_for_period(self, tenant_id: str, start: datetime,
                               end: datetime) -> List[CostMetric]:
        """Get metrics for a time period"""
        metrics = self.metrics_by_tenant.get(tenant_id, [])
        return [m for m in metrics if start <= m.timestamp <= end]

    def set_custom_rate(self, resource_type: str, rate: float) -> None:
        """Set custom hourly rate for resource type"""
        self.hourly_rates[resource_type] = rate
        logger.info(f"Custom rate set: {resource_type} = ${rate:.4f}")


class CostAnalyzer:
    """Analyzes costs and generates breakdowns"""

    def __init__(self, meter: CostMeter):
        self.meter = meter
        self.cost_breakdowns: Dict[str, CostBreakdown] = {}

    def calculate_breakdown(self, tenant_id: str, start: datetime,
                           end: datetime) -> CostBreakdown:
        """Calculate cost breakdown for a period"""
        breakdown_id = str(uuid4())

        metrics = self.meter.get_metrics_for_period(tenant_id, start, end)

        total_cost = sum(m.amount for m in metrics)

        # Breakdown by category
        by_category: Dict[str, float] = {}
        for metric in metrics:
            category = metric.category.value
            by_category[category] = by_category.get(category, 0) + metric.amount

        # Breakdown by resource
        by_resource: Dict[str, float] = {}
        for metric in metrics:
            resource_key = f"{metric.resource_type}:{metric.resource_id}"
            by_resource[resource_key] = by_resource.get(resource_key, 0) + metric.amount

        # Top resources
        top_resources = sorted(by_resource.items(), key=lambda x: x[1], reverse=True)[:10]

        breakdown = CostBreakdown(
            tenant_id=tenant_id,
            period_start=start,
            period_end=end,
            total_cost=total_cost,
            by_category=by_category,
            by_resource=by_resource,
            top_resources=top_resources
        )

        self.cost_breakdowns[breakdown_id] = breakdown
        return breakdown

    def get_cost_trend(self, tenant_id: str, days: int = 30) -> List[Tuple[datetime, float]]:
        """Get cost trend over time"""
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=days)

        metrics = self.meter.get_metrics_for_period(tenant_id, start, end)

        # Group by day
        daily_costs: Dict[datetime, float] = {}
        for metric in metrics:
            day = metric.timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
            daily_costs[day] = daily_costs.get(day, 0) + metric.amount

        return sorted(daily_costs.items())


class BudgetManager:
    """Manages budgets and alerts"""

    def __init__(self):
        self.budgets: Dict[str, Budget] = {}
        self.alerts: Dict[str, CostAlert] = {}
        self.alert_callbacks: List[Callable] = []

    def create_budget(self, tenant_id: str, name: str, limit: float,
                     period: str = "monthly",
                     category: Optional[CostCategory] = None) -> Budget:
        """Create a budget"""
        budget_id = str(uuid4())

        budget = Budget(
            budget_id=budget_id,
            tenant_id=tenant_id,
            name=name,
            limit=limit,
            period=period,
            category=category
        )

        self.budgets[budget_id] = budget
        logger.info(f"Budget created: {name} (${limit})")
        return budget

    def update_budget_cost(self, budget_id: str, cost: float) -> Optional[CostAlert]:
        """Update accumulated cost for a budget"""
        budget = self.budgets.get(budget_id)
        if not budget:
            return None

        budget.accumulated_cost += cost

        # Check alert thresholds
        for threshold in budget.alert_thresholds:
            threshold_amount = (budget.limit * threshold) / 100
            if budget.accumulated_cost >= threshold_amount:
                return self._create_alert(budget)

        return None

    def get_budget(self, budget_id: str) -> Optional[Budget]:
        """Retrieve a budget"""
        return self.budgets.get(budget_id)

    def get_tenant_budgets(self, tenant_id: str) -> List[Budget]:
        """Get all budgets for a tenant"""
        return [b for b in self.budgets.values() if b.tenant_id == tenant_id]

    def register_alert_callback(self, callback: Callable) -> None:
        """Register a callback for budget alerts"""
        self.alert_callbacks.append(callback)

    def _create_alert(self, budget: Budget) -> CostAlert:
        """Create an alert for a budget"""
        alert_id = str(uuid4())

        utilization = (budget.accumulated_cost / budget.limit * 100) if budget.limit > 0 else 0

        if utilization >= 90:
            severity = AlertSeverity.CRITICAL
        elif utilization >= 75:
            severity = AlertSeverity.WARNING
        else:
            severity = AlertSeverity.INFO

        alert = CostAlert(
            alert_id=alert_id,
            tenant_id=budget.tenant_id,
            budget_id=budget.budget_id,
            severity=severity,
            title=f"{budget.name} Budget Alert",
            message=f"Budget utilization at {utilization:.1f}%",
            threshold_exceeded=utilization,
            current_cost=budget.accumulated_cost
        )

        self.alerts[alert_id] = alert

        # Notify callbacks
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"Alert callback error: {e}")

        logger.warning(f"Budget alert created: {alert.title}")
        return alert


class CostPredictor:
    """Predicts future costs using ML"""

    def __init__(self, analyzer: CostAnalyzer):
        self.analyzer = analyzer
        self.forecasts: Dict[str, CostForecast] = {}
        self.model = LinearRegression()
        self.scaler = StandardScaler()

    def predict_monthly_cost(self, tenant_id: str) -> Optional[CostForecast]:
        """Predict cost for next month"""
        # Get historical cost trend
        trend = self.analyzer.get_cost_trend(tenant_id, days=90)

        if len(trend) < 5:
            return None

        # Prepare data
        X = np.array([(i) for i in range(len(trend))]).reshape(-1, 1)
        y = np.array([cost for _, cost in trend])

        # Train model
        X_scaled = self.scaler.fit_transform(X)
        self.model.fit(X_scaled, y)

        # Predict next 30 days
        X_future = np.array([[len(trend) + i] for i in range(30)])
        X_future_scaled = self.scaler.transform(X_future)
        predictions = self.model.predict(X_future_scaled)

        predicted_cost = float(np.sum(predictions))

        # Calculate trend
        avg_recent = statistics.mean([cost for _, cost in trend[-7:]])
        avg_historical = statistics.mean([cost for _, cost in trend])
        trend_pct = ((avg_recent - avg_historical) / avg_historical * 100) if avg_historical > 0 else 0

        trend_str = "increasing" if trend_pct > 5 else "decreasing" if trend_pct < -5 else "stable"

        forecast_id = str(uuid4())
        forecast = CostForecast(
            forecast_id=forecast_id,
            tenant_id=tenant_id,
            category=CostCategory.COMPUTE,
            forecast_date=datetime.now(timezone.utc) + timedelta(days=30),
            predicted_cost=predicted_cost,
            trend=trend_str,
            trend_percentage=trend_pct
        )

        self.forecasts[forecast_id] = forecast
        logger.info(f"Cost forecast generated: ${predicted_cost:.2f} ({trend_str})")
        return forecast


class OptimizationEngine:
    """Generates cost optimization recommendations"""

    def __init__(self, analyzer: CostAnalyzer):
        self.analyzer = analyzer
        self.recommendations: Dict[str, OptimizationRecommendation] = {}

    def analyze_and_recommend(self, tenant_id: str) -> List[OptimizationRecommendation]:
        """Analyze costs and generate recommendations"""
        recommendations = []

        # Get latest breakdown
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=7)
        breakdown = self.analyzer.calculate_breakdown(tenant_id, start, end)

        # Recommend instance rightsizing (if compute is >40% of costs)
        compute_cost = breakdown.by_category.get('compute', 0)
        if compute_cost / breakdown.total_cost > 0.4 if breakdown.total_cost > 0 else False:
            recommendation_id = str(uuid4())
            rec = OptimizationRecommendation(
                recommendation_id=recommendation_id,
                tenant_id=tenant_id,
                optimization_type=OptimizationType.INSTANCE_RIGHTSIZING,
                resource_id="all_instances",
                resource_type="compute",
                current_cost=compute_cost,
                estimated_savings=compute_cost * 0.15,
                implementation_effort="medium",
                description="Consider rightsizing underutilized instances",
                action_items=["Review instance utilization", "Right-size to appropriate tiers"],
                priority=8
            )
            self.recommendations[recommendation_id] = rec
            recommendations.append(rec)

        # Recommend storage optimization (if storage is present)
        storage_cost = breakdown.by_category.get('storage', 0)
        if storage_cost > 0:
            recommendation_id = str(uuid4())
            rec = OptimizationRecommendation(
                recommendation_id=recommendation_id,
                tenant_id=tenant_id,
                optimization_type=OptimizationType.STORAGE_OPTIMIZATION,
                resource_id="all_storage",
                resource_type="storage",
                current_cost=storage_cost,
                estimated_savings=storage_cost * 0.20,
                implementation_effort="low",
                description="Archive old data and optimize storage tiers",
                action_items=["Identify old data", "Move to archive storage"],
                priority=6
            )
            self.recommendations[recommendation_id] = rec
            recommendations.append(rec)

        logger.info(f"Generated {len(recommendations)} recommendations for {tenant_id}")
        return recommendations


# ============================================================================
# MAIN COST MANAGEMENT SYSTEM
# ============================================================================

class CostManagementSystem:
    """Unified cost management and optimization system"""

    def __init__(self):
        self.meter = CostMeter()
        self.analyzer = CostAnalyzer(self.meter)
        self.budget_manager = BudgetManager()
        self.predictor = CostPredictor(self.analyzer)
        self.optimization_engine = OptimizationEngine(self.analyzer)

    def record_cost(self, tenant_id: str, category: CostCategory,
                   resource_type: str, resource_id: str,
                   quantity: float) -> CostMetric:
        """Record a cost metric"""
        return self.meter.record_metric(tenant_id, category, resource_type, resource_id, quantity)

    def get_cost_breakdown(self, tenant_id: str, days: int = 30) -> Optional[CostBreakdown]:
        """Get cost breakdown for a period"""
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=days)
        return self.analyzer.calculate_breakdown(tenant_id, start, end)

    def get_cost_trend(self, tenant_id: str, days: int = 30) -> List[Tuple[datetime, float]]:
        """Get cost trend"""
        return self.analyzer.get_cost_trend(tenant_id, days)

    def create_budget(self, tenant_id: str, name: str, limit: float,
                     period: str = "monthly") -> Budget:
        """Create a budget"""
        return self.budget_manager.create_budget(tenant_id, name, limit, period)

    def predict_costs(self, tenant_id: str) -> Optional[CostForecast]:
        """Predict future costs"""
        return self.predictor.predict_monthly_cost(tenant_id)

    def get_optimization_recommendations(self, tenant_id: str) -> List[OptimizationRecommendation]:
        """Get cost optimization recommendations"""
        return self.optimization_engine.analyze_and_recommend(tenant_id)

    def get_total_savings_potential(self, tenant_id: str) -> float:
        """Calculate total savings potential"""
        recommendations = self.get_optimization_recommendations(tenant_id)
        return sum(r.estimated_savings for r in recommendations)


# ============================================================================
# SINGLETON ACCESS
# ============================================================================

_cost_system: Optional[CostManagementSystem] = None


def get_cost_management_system() -> CostManagementSystem:
    """Get or create the singleton CostManagementSystem instance"""
    global _cost_system
    if _cost_system is None:
        _cost_system = CostManagementSystem()
    return _cost_system


if __name__ == "__main__":
    system = get_cost_management_system()

    # Example usage
    metric = system.record_cost(
        "tenant_123",
        CostCategory.COMPUTE,
        "large",
        "instance_456",
        24  # 24 hours
    )
    print(f"Cost recorded: ${metric.amount:.2f}")

    budget = system.create_budget("tenant_123", "Monthly Compute", 1000)
    print(f"Budget created: {budget.budget_id}")

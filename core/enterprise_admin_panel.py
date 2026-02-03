"""
Enterprise Admin Panel System

Comprehensive web-based management dashboard providing:
- User management and lifecycle control
- Real-time system health monitoring
- Analytics visualization and dashboards
- Configuration management interface
- Audit log viewing and analysis
- Performance tuning controls
- Compliance reporting and validation
- Role-based access control (RBAC)
- Alert management
- Resource allocation and scaling

This module provides REST API endpoints and integrates with FastAPI.
"""

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from uuid import uuid4

from fastapi import Body, Depends, FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ============================================================================
# ENUMS
# ============================================================================

class UserRole(str, Enum):
    """User roles with permission levels"""
    ADMIN = "admin"
    SUPERADMIN = "superadmin"
    ANALYTICS_MANAGER = "analytics_manager"
    COMPLIANCE_OFFICER = "compliance_officer"
    INFRASTRUCTURE_LEAD = "infrastructure_lead"
    SUPPORT_LEAD = "support_lead"
    VIEWER = "viewer"


class ResourceType(str, Enum):
    """Types of system resources"""
    CPU = "cpu"
    MEMORY = "memory"
    DISK = "disk"
    NETWORK = "network"
    DATABASE = "database"
    CACHE = "cache"


class SystemHealthStatus(str, Enum):
    """System health statuses"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    WARNING = "warning"
    CRITICAL = "critical"


class ComplianceStatus(str, Enum):
    """Compliance statuses"""
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    PENDING_REVIEW = "pending_review"


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class UserDTO(BaseModel):
    """User data transfer object"""
    user_id: str
    username: str
    email: str
    role: UserRole
    created_at: datetime
    last_login: Optional[datetime] = None
    is_active: bool = True
    permissions: List[str] = Field(default_factory=list)


class UserCreateRequest(BaseModel):
    """Request to create a user"""
    username: str
    email: str
    role: UserRole
    password: str


class SystemHealthDTO(BaseModel):
    """System health status"""
    status: SystemHealthStatus
    timestamp: datetime
    components: Dict[str, Any]
    metrics: Dict[str, float]
    alerts: List[Dict[str, Any]] = Field(default_factory=list)


class AnalyticsMetricDTO(BaseModel):
    """Analytics metric for dashboard"""
    metric_name: str
    value: float
    timestamp: datetime
    dimension: Optional[str] = None
    tags: Dict[str, str] = Field(default_factory=dict)


class ConfigurationDTO(BaseModel):
    """Configuration item"""
    config_id: str
    key: str
    value: Any
    environment: str
    updated_by: str
    updated_at: datetime


class AuditLogDTO(BaseModel):
    """Audit log entry"""
    log_id: str
    user_id: str
    action: str
    resource_type: str
    resource_id: str
    changes: Dict[str, Any]
    timestamp: datetime
    ip_address: Optional[str] = None


class ComplianceReportDTO(BaseModel):
    """Compliance report"""
    report_id: str
    framework: str  # SOC2, HIPAA, GDPR, etc.
    status: ComplianceStatus
    checks_passed: int
    checks_failed: int
    checks_total: int
    generated_at: datetime
    next_review: datetime


class AlertDTO(BaseModel):
    """System alert"""
    alert_id: str
    severity: str  # critical, high, medium, low
    title: str
    description: str
    source: str
    created_at: datetime
    resolved_at: Optional[datetime] = None
    is_resolved: bool = False


# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class AdminUser:
    """Represents an admin panel user"""
    user_id: str
    username: str
    email: str
    role: UserRole
    password_hash: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_login: Optional[datetime] = None
    is_active: bool = True
    permissions: Set[str] = field(default_factory=set)
    mfa_enabled: bool = False
    mfa_secret: Optional[str] = None

    def to_dto(self) -> UserDTO:
        return UserDTO(
            user_id=self.user_id,
            username=self.username,
            email=self.email,
            role=self.role,
            created_at=self.created_at,
            last_login=self.last_login,
            is_active=self.is_active,
            permissions=list(self.permissions)
        )


@dataclass
class DashboardWidget:
    """Represents a customizable dashboard widget"""
    widget_id: str
    title: str
    widget_type: str  # metric, chart, table, gauge, etc.
    data_source: str
    position: Dict[str, int] = field(default_factory=dict)  # x, y, width, height
    refresh_interval: int = 60  # seconds
    configuration: Dict[str, Any] = field(default_factory=dict)
    is_visible: bool = True


@dataclass
class SystemMetric:
    """Represents a system metric"""
    metric_id: str
    metric_name: str
    resource_type: ResourceType
    value: float
    unit: str
    timestamp: datetime
    threshold_warning: float = 0.0
    threshold_critical: float = 0.0


@dataclass
class AuditLog:
    """Represents an audit log entry"""
    log_id: str
    user_id: str
    action: str
    resource_type: str
    resource_id: str
    changes: Dict[str, Any]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    status: str = "success"


@dataclass
class ComplianceCheck:
    """Represents a compliance check"""
    check_id: str
    framework: str
    requirement: str
    description: str
    test_function: Optional[Callable] = None
    last_checked: Optional[datetime] = None
    status: ComplianceStatus = ComplianceStatus.PENDING_REVIEW


# ============================================================================
# MANAGERS
# ============================================================================

class UserManagementSystem:
    """Manages admin users and permissions"""

    def __init__(self):
        self.users: Dict[str, AdminUser] = {}
        self.role_permissions: Dict[UserRole, Set[str]] = {
            UserRole.SUPERADMIN: {
                "manage_users", "manage_config", "view_audit", "manage_alerts",
                "manage_resources", "view_compliance", "export_data"
            },
            UserRole.ADMIN: {
                "manage_users", "manage_config", "view_audit",
                "manage_alerts", "view_compliance"
            },
            UserRole.ANALYTICS_MANAGER: {
                "view_analytics", "manage_reports", "view_audit"
            },
            UserRole.COMPLIANCE_OFFICER: {
                "view_compliance", "view_audit", "export_compliance_reports"
            },
            UserRole.INFRASTRUCTURE_LEAD: {
                "view_metrics", "manage_resources", "manage_alerts"
            },
            UserRole.SUPPORT_LEAD: {
                "view_users", "view_analytics", "view_audit"
            },
            UserRole.VIEWER: {
                "view_analytics", "view_metrics"
            }
        }

    def create_user(self, username: str, email: str, role: UserRole,
                   password_hash: str) -> AdminUser:
        """Create a new admin user"""
        user_id = str(uuid4())

        user = AdminUser(
            user_id=user_id,
            username=username,
            email=email,
            role=role,
            password_hash=password_hash,
            permissions=self.role_permissions.get(role, set()).copy()
        )

        self.users[user_id] = user
        logger.info(f"Created user: {username}")
        return user

    def get_user(self, user_id: str) -> Optional[AdminUser]:
        """Retrieve a user"""
        return self.users.get(user_id)

    def get_user_by_username(self, username: str) -> Optional[AdminUser]:
        """Retrieve a user by username"""
        for user in self.users.values():
            if user.username == username:
                return user
        return None

    def update_user_role(self, user_id: str, new_role: UserRole) -> Optional[AdminUser]:
        """Update user's role and permissions"""
        user = self.users.get(user_id)
        if user:
            user.role = new_role
            user.permissions = self.role_permissions.get(new_role, set()).copy()
            logger.info(f"Updated role for user {user_id}")
        return user

    def enable_mfa(self, user_id: str, mfa_secret: str) -> bool:
        """Enable MFA for a user"""
        user = self.users.get(user_id)
        if user:
            user.mfa_enabled = True
            user.mfa_secret = mfa_secret
            return True
        return False

    def record_login(self, user_id: str) -> Optional[AdminUser]:
        """Record a user login"""
        user = self.users.get(user_id)
        if user:
            user.last_login = datetime.now(timezone.utc)
        return user

    def has_permission(self, user_id: str, permission: str) -> bool:
        """Check if user has a specific permission"""
        user = self.users.get(user_id)
        if not user:
            return False
        return permission in user.permissions

    def list_users(self, role: Optional[UserRole] = None) -> List[AdminUser]:
        """List users, optionally filtered by role"""
        users = list(self.users.values())
        if role:
            users = [u for u in users if u.role == role]
        return users


class DashboardManager:
    """Manages admin dashboards and widgets"""

    def __init__(self):
        self.dashboards: Dict[str, Dict[str, Any]] = {}
        self.widgets: Dict[str, DashboardWidget] = {}
        self.user_dashboards: Dict[str, List[str]] = {}  # user_id -> dashboard_ids

    def create_dashboard(self, user_id: str, title: str,
                        description: str = "") -> Dict[str, Any]:
        """Create a new dashboard"""
        dashboard_id = str(uuid4())

        dashboard = {
            'dashboard_id': dashboard_id,
            'title': title,
            'description': description,
            'owner_id': user_id,
            'widgets': [],
            'created_at': datetime.now(timezone.utc),
            'updated_at': datetime.now(timezone.utc),
            'is_shared': False,
            'shared_with': set()
        }

        self.dashboards[dashboard_id] = dashboard

        if user_id not in self.user_dashboards:
            self.user_dashboards[user_id] = []
        self.user_dashboards[user_id].append(dashboard_id)

        logger.info(f"Created dashboard: {dashboard_id}")
        return dashboard

    def add_widget(self, dashboard_id: str, widget: DashboardWidget) -> bool:
        """Add a widget to a dashboard"""
        if dashboard_id not in self.dashboards:
            return False

        dashboard = self.dashboards[dashboard_id]
        dashboard['widgets'].append(widget.widget_id)
        dashboard['updated_at'] = datetime.now(timezone.utc)

        self.widgets[widget.widget_id] = widget
        return True

    def get_dashboard(self, dashboard_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a dashboard"""
        return self.dashboards.get(dashboard_id)

    def get_user_dashboards(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all dashboards for a user"""
        dashboard_ids = self.user_dashboards.get(user_id, [])
        return [self.dashboards[did] for did in dashboard_ids if did in self.dashboards]

    def create_metric_widget(self, title: str, metric_name: str,
                            unit: str = "") -> DashboardWidget:
        """Create a metric widget"""
        return DashboardWidget(
            widget_id=str(uuid4()),
            title=title,
            widget_type="metric",
            data_source=metric_name,
            refresh_interval=60,
            configuration={'unit': unit}
        )

    def create_chart_widget(self, title: str, chart_type: str,
                           metric_name: str) -> DashboardWidget:
        """Create a chart widget"""
        return DashboardWidget(
            widget_id=str(uuid4()),
            title=title,
            widget_type="chart",
            data_source=metric_name,
            refresh_interval=120,
            configuration={'chart_type': chart_type}
        )


class ConfigurationManagementSystem:
    """Manages system configuration"""

    def __init__(self):
        self.configurations: Dict[str, Dict[str, Any]] = {}
        self.config_history: Dict[str, List[Dict[str, Any]]] = {}
        self.watchers: List[Callable] = []

    def set_configuration(self, key: str, value: Any, environment: str,
                         updated_by: str) -> bool:
        """Set a configuration value"""
        config_id = f"{environment}:{key}"

        old_value = self.configurations.get(config_id, {}).get('value')

        self.configurations[config_id] = {
            'key': key,
            'value': value,
            'environment': environment,
            'updated_by': updated_by,
            'updated_at': datetime.now(timezone.utc)
        }

        # Track history
        if config_id not in self.config_history:
            self.config_history[config_id] = []

        self.config_history[config_id].append({
            'old_value': old_value,
            'new_value': value,
            'updated_by': updated_by,
            'updated_at': datetime.now(timezone.utc)
        })

        # Notify watchers
        self._notify_watchers(key, value)
        logger.info(f"Configuration updated: {key} = {value}")
        return True

    def get_configuration(self, key: str, environment: str) -> Optional[Any]:
        """Get a configuration value"""
        config_id = f"{environment}:{key}"
        config = self.configurations.get(config_id)
        return config['value'] if config else None

    def list_configurations(self, environment: Optional[str] = None) -> List[Dict[str, Any]]:
        """List configurations"""
        configs = list(self.configurations.values())
        if environment:
            configs = [c for c in configs if c['environment'] == environment]
        return configs

    def register_watcher(self, callback: Callable) -> None:
        """Register a callback for configuration changes"""
        self.watchers.append(callback)

    def _notify_watchers(self, key: str, value: Any) -> None:
        """Notify all watchers of a change"""
        for watcher in self.watchers:
            try:
                watcher(key, value)
            except Exception as e:
                logger.error(f"Watcher error: {e}")


class AuditLoggingSystem:
    """Manages audit logging and compliance tracking"""

    def __init__(self):
        self.logs: Dict[str, AuditLog] = {}
        self.logs_list: List[AuditLog] = []
        self.retention_days = 365

    def log_action(self, user_id: str, action: str, resource_type: str,
                  resource_id: str, changes: Dict[str, Any],
                  ip_address: Optional[str] = None) -> AuditLog:
        """Log an action"""
        log_id = str(uuid4())

        log = AuditLog(
            log_id=log_id,
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            changes=changes,
            ip_address=ip_address
        )

        self.logs[log_id] = log
        self.logs_list.append(log)

        logger.info(f"Audit log: {action} on {resource_type}/{resource_id} by {user_id}")
        return log

    def query_logs(self, user_id: Optional[str] = None,
                  action: Optional[str] = None,
                  resource_type: Optional[str] = None,
                  days_back: int = 30) -> List[AuditLog]:
        """Query audit logs with filters"""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)

        results = [log for log in self.logs_list if log.timestamp >= cutoff]

        if user_id:
            results = [log for log in results if log.user_id == user_id]
        if action:
            results = [log for log in results if log.action == action]
        if resource_type:
            results = [log for log in results if log.resource_type == resource_type]

        return sorted(results, key=lambda x: x.timestamp, reverse=True)

    def cleanup_old_logs(self) -> int:
        """Remove logs older than retention period"""
        cutoff = datetime.now(timezone.utc) - timedelta(days=self.retention_days)

        old_logs = [log for log in self.logs_list if log.timestamp < cutoff]
        count = len(old_logs)

        for log in old_logs:
            self.logs_list.remove(log)
            if log.log_id in self.logs:
                del self.logs[log.log_id]

        logger.info(f"Cleaned up {count} audit logs")
        return count


class ComplianceManager:
    """Manages compliance checks and reporting"""

    def __init__(self):
        self.checks: Dict[str, ComplianceCheck] = {}
        self.frameworks = {
            'SOC2': ['access_control', 'data_protection', 'monitoring', 'incident_response'],
            'HIPAA': ['privacy', 'security', 'breach_notification', 'audit_control'],
            'GDPR': ['consent', 'data_minimization', 'user_rights', 'privacy_by_design'],
        }

    def register_check(self, framework: str, requirement: str,
                      description: str, test_fn: Callable) -> ComplianceCheck:
        """Register a compliance check"""
        check_id = str(uuid4())

        check = ComplianceCheck(
            check_id=check_id,
            framework=framework,
            requirement=requirement,
            description=description,
            test_function=test_fn
        )

        self.checks[check_id] = check
        return check

    def run_compliance_checks(self, framework: str) -> Dict[str, Any]:
        """Run all compliance checks for a framework"""
        framework_checks = [c for c in self.checks.values() if c.framework == framework]

        passed = 0
        failed = 0
        failed_checks = []

        for check in framework_checks:
            try:
                if check.test_function and check.test_function():
                    passed += 1
                    check.status = ComplianceStatus.COMPLIANT
                else:
                    failed += 1
                    failed_checks.append(check.requirement)
                    check.status = ComplianceStatus.NON_COMPLIANT
            except Exception as e:
                failed += 1
                check.status = ComplianceStatus.PENDING_REVIEW
                logger.error(f"Compliance check failed: {check.requirement} - {e}")

            check.last_checked = datetime.now(timezone.utc)

        return {
            'framework': framework,
            'passed': passed,
            'failed': failed,
            'total': passed + failed,
            'failed_checks': failed_checks,
            'checked_at': datetime.now(timezone.utc)
        }

    def generate_compliance_report(self, framework: str) -> ComplianceReportDTO:
        """Generate a compliance report"""
        framework_checks = [c for c in self.checks.values() if c.framework == framework]
        passed = sum(1 for c in framework_checks if c.status == ComplianceStatus.COMPLIANT)
        failed = sum(1 for c in framework_checks if c.status == ComplianceStatus.NON_COMPLIANT)
        total = len(framework_checks)

        return ComplianceReportDTO(
            report_id=str(uuid4()),
            framework=framework,
            status=ComplianceStatus.COMPLIANT if failed == 0 else ComplianceStatus.NON_COMPLIANT,
            checks_passed=passed,
            checks_failed=failed,
            checks_total=total,
            generated_at=datetime.now(timezone.utc),
            next_review=datetime.now(timezone.utc) + timedelta(days=90)
        )


class AlertManagementSystem:
    """Manages system alerts and notifications"""

    def __init__(self):
        self.alerts: Dict[str, AlertDTO] = {}
        self.alert_rules: Dict[str, Dict[str, Any]] = {}
        self.notification_handlers: List[Callable] = []

    def create_alert(self, severity: str, title: str, description: str,
                    source: str) -> AlertDTO:
        """Create a new alert"""
        alert_id = str(uuid4())

        alert = AlertDTO(
            alert_id=alert_id,
            severity=severity,
            title=title,
            description=description,
            source=source,
            created_at=datetime.now(timezone.utc)
        )

        self.alerts[alert_id] = alert

        # Notify handlers
        self._notify_handlers(alert)
        logger.warning(f"Alert created: [{severity}] {title}")

        return alert

    def resolve_alert(self, alert_id: str) -> Optional[AlertDTO]:
        """Resolve an alert"""
        alert = self.alerts.get(alert_id)
        if alert:
            alert.is_resolved = True
            alert.resolved_at = datetime.now(timezone.utc)
        return alert

    def get_active_alerts(self, severity: Optional[str] = None) -> List[AlertDTO]:
        """Get all active alerts"""
        alerts = [a for a in self.alerts.values() if not a.is_resolved]
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        return sorted(alerts, key=lambda x: x.created_at, reverse=True)

    def register_notification_handler(self, handler: Callable) -> None:
        """Register a notification handler"""
        self.notification_handlers.append(handler)

    def _notify_handlers(self, alert: AlertDTO) -> None:
        """Notify all handlers of an alert"""
        for handler in self.notification_handlers:
            try:
                handler(alert)
            except Exception as e:
                logger.error(f"Notification handler error: {e}")


# ============================================================================
# MAIN ADMIN PANEL SYSTEM
# ============================================================================

class EnterpriseAdminPanel:
    """Main admin panel system"""

    def __init__(self, app: Optional[FastAPI] = None):
        self.app = app
        self.user_manager = UserManagementSystem()
        self.dashboard_manager = DashboardManager()
        self.config_manager = ConfigurationManagementSystem()
        self.audit_logger = AuditLoggingSystem()
        self.compliance_manager = ComplianceManager()
        self.alert_manager = AlertManagementSystem()

        if app:
            self._register_routes()

    def _register_routes(self) -> None:
        """Register FastAPI routes"""
        if not self.app:
            return

        # User management routes
        @self.app.post("/admin/users")
        async def create_user(req: UserCreateRequest):
            user = self.user_manager.create_user(
                username=req.username,
                email=req.email,
                role=req.role,
                password_hash=self._hash_password(req.password)
            )
            return user.to_dto()

        @self.app.get("/admin/users")
        async def list_users(role: Optional[UserRole] = Query(None)):
            users = self.user_manager.list_users(role)
            return [u.to_dto() for u in users]

        @self.app.get("/admin/users/{user_id}")
        async def get_user(user_id: str):
            user = self.user_manager.get_user(user_id)
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            return user.to_dto()

        # Dashboard routes
        @self.app.post("/admin/dashboards")
        async def create_dashboard(user_id: str, title: str, description: str = ""):
            dashboard = self.dashboard_manager.create_dashboard(user_id, title, description)
            return dashboard

        @self.app.get("/admin/dashboards/{user_id}")
        async def get_user_dashboards(user_id: str):
            return self.dashboard_manager.get_user_dashboards(user_id)

        # Configuration routes
        @self.app.post("/admin/config")
        async def set_config(key: str, value: Any, environment: str, updated_by: str):
            self.config_manager.set_configuration(key, value, environment, updated_by)
            return {"status": "success"}

        @self.app.get("/admin/config")
        async def list_config(environment: Optional[str] = Query(None)):
            return self.config_manager.list_configurations(environment)

        # Audit log routes
        @self.app.get("/admin/audit")
        async def query_audit_logs(
            user_id: Optional[str] = Query(None),
            action: Optional[str] = Query(None),
            resource_type: Optional[str] = Query(None),
            days_back: int = Query(30)
        ):
            logs = self.audit_logger.query_logs(user_id, action, resource_type, days_back)
            return [asdict(log) for log in logs]

        # Compliance routes
        @self.app.get("/admin/compliance/report/{framework}")
        async def get_compliance_report(framework: str):
            report = self.compliance_manager.generate_compliance_report(framework)
            return report.dict()

        # Alert routes
        @self.app.get("/admin/alerts")
        async def get_alerts(severity: Optional[str] = Query(None)):
            alerts = self.alert_manager.get_active_alerts(severity)
            return [asdict(alert) for alert in alerts]

    def _hash_password(self, password: str) -> str:
        """Hash a password (simplified)"""
        import hashlib
        return hashlib.sha256(password.encode()).hexdigest()


# ============================================================================
# SINGLETON ACCESS
# ============================================================================

_admin_panel: Optional[EnterpriseAdminPanel] = None


def get_admin_panel(app: Optional[FastAPI] = None) -> EnterpriseAdminPanel:
    """Get or create the singleton EnterpriseAdminPanel instance"""
    global _admin_panel
    if _admin_panel is None:
        _admin_panel = EnterpriseAdminPanel(app)
    return _admin_panel


if __name__ == "__main__":
    from fastapi import FastAPI

    app = FastAPI(title="BAEL Admin Panel")
    admin_panel = get_admin_panel(app)

    # Example usage
    print(f"Admin panel initialized: {admin_panel}")

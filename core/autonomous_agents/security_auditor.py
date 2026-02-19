"""
Security Auditor Agent - Finds and Fixes Security Vulnerabilities
===================================================================

The vigilant guardian that hunts security vulnerabilities
with relentless precision.

"Security is not a product, but a process of eternal vigilance." — Ba'el
"""

import asyncio
import hashlib
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
import ast

from .agent_factory import (
    AutonomousAgent,
    AgentConfig,
    AgentType,
    AgentCapability,
    AgentTask,
    AgentResult,
    autonomous_agent,
)


logger = logging.getLogger("BAEL.SecurityAuditor")


class VulnerabilityType(Enum):
    """Types of security vulnerabilities."""
    # Injection
    SQL_INJECTION = "sql_injection"
    COMMAND_INJECTION = "command_injection"
    CODE_INJECTION = "code_injection"
    XSS = "cross_site_scripting"
    XXE = "xml_external_entity"
    LDAP_INJECTION = "ldap_injection"

    # Authentication & Authorization
    BROKEN_AUTH = "broken_authentication"
    BROKEN_ACCESS_CONTROL = "broken_access_control"
    SESSION_FIXATION = "session_fixation"
    WEAK_PASSWORD = "weak_password_policy"

    # Data Exposure
    SENSITIVE_DATA_EXPOSURE = "sensitive_data_exposure"
    HARDCODED_SECRETS = "hardcoded_secrets"
    INSECURE_STORAGE = "insecure_storage"

    # Configuration
    SECURITY_MISCONFIGURATION = "security_misconfiguration"
    DEBUG_ENABLED = "debug_enabled"
    INSECURE_DEFAULTS = "insecure_defaults"

    # Dependencies
    VULNERABLE_DEPENDENCY = "vulnerable_dependency"
    OUTDATED_DEPENDENCY = "outdated_dependency"

    # Cryptography
    WEAK_CRYPTO = "weak_cryptography"
    INSECURE_RANDOM = "insecure_random"

    # Other
    INSECURE_DESERIALIZATION = "insecure_deserialization"
    PATH_TRAVERSAL = "path_traversal"
    SSRF = "server_side_request_forgery"
    OPEN_REDIRECT = "open_redirect"
    RACE_CONDITION = "race_condition"
    PROTOTYPE_POLLUTION = "prototype_pollution"


class SeverityLevel(Enum):
    """Severity levels for vulnerabilities."""
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4
    INFO = 5


class CVSS(Enum):
    """CVSS score ranges."""
    NONE = (0.0, 0.0)
    LOW = (0.1, 3.9)
    MEDIUM = (4.0, 6.9)
    HIGH = (7.0, 8.9)
    CRITICAL = (9.0, 10.0)


@dataclass
class Vulnerability:
    """A detected security vulnerability."""
    id: str
    type: VulnerabilityType
    severity: SeverityLevel
    file_path: str
    line_number: int
    column: int = 0
    code_snippet: str = ""
    description: str = ""
    cwe_id: Optional[str] = None
    cvss_score: float = 0.0
    recommendation: str = ""
    auto_fixable: bool = False
    fix_code: Optional[str] = None
    false_positive_likelihood: float = 0.0
    detected_at: datetime = field(default_factory=datetime.now)


@dataclass
class SecurityAuditResult:
    """Result of a security audit."""
    target_path: str
    scan_duration_ms: int
    total_files_scanned: int
    vulnerabilities: List[Vulnerability] = field(default_factory=list)
    risk_score: float = 0.0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    info_count: int = 0
    recommendations: List[str] = field(default_factory=list)
    compliance_status: Dict[str, bool] = field(default_factory=dict)


# Security patterns to detect
DANGEROUS_PATTERNS = {
    VulnerabilityType.SQL_INJECTION: [
        r'execute\s*\(\s*["\'].*%s.*["\']\s*%',
        r'execute\s*\(\s*f["\'].*\{.*\}.*["\']',
        r'cursor\.execute\s*\([^,]+\+',
        r'\.raw\s*\([^)]*\+',
    ],
    VulnerabilityType.COMMAND_INJECTION: [
        r'os\.system\s*\(',
        r'subprocess\.call\s*\([^,]*shell\s*=\s*True',
        r'subprocess\.Popen\s*\([^,]*shell\s*=\s*True',
        r'eval\s*\(',
        r'exec\s*\(',
    ],
    VulnerabilityType.HARDCODED_SECRETS: [
        r'(?:password|passwd|pwd|secret|api_key|apikey|token|auth)\s*=\s*["\'][^"\']+["\']',
        r'(?:AWS_ACCESS_KEY|AWS_SECRET_KEY)\s*=\s*["\'][^"\']+["\']',
        r'-----BEGIN (?:RSA )?PRIVATE KEY-----',
    ],
    VulnerabilityType.PATH_TRAVERSAL: [
        r'open\s*\([^)]*\+',
        r'\.read\s*\([^)]*\.\.',
        r'os\.path\.join\s*\([^)]*request\.',
    ],
    VulnerabilityType.XSS: [
        r'innerHTML\s*=',
        r'document\.write\s*\(',
        r'\.html\s*\([^)]*request\.',
    ],
    VulnerabilityType.INSECURE_RANDOM: [
        r'random\.random\s*\(',
        r'random\.randint\s*\(',
        r'random\.choice\s*\(',
    ],
    VulnerabilityType.WEAK_CRYPTO: [
        r'hashlib\.md5\s*\(',
        r'hashlib\.sha1\s*\(',
        r'DES\.',
        r'RC4',
    ],
    VulnerabilityType.DEBUG_ENABLED: [
        r'DEBUG\s*=\s*True',
        r'debug\s*=\s*True',
        r'\.set_trace\s*\(',
    ],
}


@autonomous_agent(AgentType.SECURITY_AUDITOR)
class SecurityAuditorAgent(AutonomousAgent):
    """Agent that performs security audits and vulnerability detection."""

    def __init__(self, config: AgentConfig):
        super().__init__(config)
        self.audit_results: Dict[str, SecurityAuditResult] = {}
        self.vulnerability_db: List[Vulnerability] = []

    async def _setup(self) -> None:
        """Initialize the security auditor."""
        self.config.capabilities = [
            AgentCapability.SECURITY_ANALYSIS,
            AgentCapability.CODE_ANALYSIS,
            AgentCapability.REPORTING,
            AgentCapability.ALERTING,
        ]
        logger.info("Security Auditor Agent initialized")

    async def execute_task(self, task: AgentTask) -> AgentResult:
        """Execute a security audit task."""
        start = datetime.now()

        try:
            action = task.parameters.get("action", "full_audit")

            if action == "full_audit":
                result = await self._full_audit(task.target_path)
            elif action == "quick_scan":
                result = await self._quick_scan(task.target_path)
            elif action == "dependency_check":
                result = await self._check_dependencies(task.target_path)
            elif action == "secret_scan":
                result = await self._scan_for_secrets(task.target_path)
            else:
                result = await self._full_audit(task.target_path)

            duration = (datetime.now() - start).total_seconds() * 1000

            return AgentResult(
                task_id=task.id,
                agent_id=self.id,
                agent_type=self.agent_type,
                success=True,
                result=result,
                metrics={
                    "vulnerabilities_found": len(result.vulnerabilities),
                    "critical_count": result.critical_count,
                    "risk_score": result.risk_score,
                },
                recommendations=result.recommendations,
            )

        except Exception as e:
            logger.error(f"Security audit failed: {e}")
            return AgentResult(
                task_id=task.id,
                agent_id=self.id,
                agent_type=self.agent_type,
                success=False,
                error=str(e),
            )

    async def _full_audit(self, path: Path) -> SecurityAuditResult:
        """Perform a comprehensive security audit."""
        start = datetime.now()
        result = SecurityAuditResult(
            target_path=str(path),
            scan_duration_ms=0,
            total_files_scanned=0,
        )

        if not path or not path.exists():
            return result

        # Scan all code files
        extensions = {'.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.go', '.rb', '.php'}
        files_to_scan = [
            f for f in path.rglob('*')
            if f.suffix in extensions and f.is_file()
        ]

        result.total_files_scanned = len(files_to_scan)

        for file_path in files_to_scan:
            vulnerabilities = await self._scan_file(file_path)
            result.vulnerabilities.extend(vulnerabilities)

        # Count by severity
        for vuln in result.vulnerabilities:
            if vuln.severity == SeverityLevel.CRITICAL:
                result.critical_count += 1
            elif vuln.severity == SeverityLevel.HIGH:
                result.high_count += 1
            elif vuln.severity == SeverityLevel.MEDIUM:
                result.medium_count += 1
            elif vuln.severity == SeverityLevel.LOW:
                result.low_count += 1
            else:
                result.info_count += 1

        # Calculate risk score
        result.risk_score = self._calculate_risk_score(result)

        # Generate recommendations
        result.recommendations = self._generate_recommendations(result)

        # Check compliance
        result.compliance_status = {
            "OWASP_TOP_10": result.critical_count == 0,
            "NO_HARDCODED_SECRETS": not any(
                v.type == VulnerabilityType.HARDCODED_SECRETS
                for v in result.vulnerabilities
            ),
            "SECURE_CRYPTO": not any(
                v.type == VulnerabilityType.WEAK_CRYPTO
                for v in result.vulnerabilities
            ),
        }

        duration = (datetime.now() - start).total_seconds() * 1000
        result.scan_duration_ms = int(duration)

        self.audit_results[str(path)] = result
        self.metrics.issues_found += len(result.vulnerabilities)

        return result

    async def _scan_file(self, file_path: Path) -> List[Vulnerability]:
        """Scan a single file for vulnerabilities."""
        vulnerabilities = []

        try:
            content = file_path.read_text(errors='ignore')
            lines = content.split('\n')

            for vuln_type, patterns in DANGEROUS_PATTERNS.items():
                for pattern in patterns:
                    for i, line in enumerate(lines, 1):
                        if re.search(pattern, line, re.IGNORECASE):
                            vuln = Vulnerability(
                                id=hashlib.md5(f"{file_path}:{i}:{vuln_type}".encode()).hexdigest()[:12],
                                type=vuln_type,
                                severity=self._get_severity(vuln_type),
                                file_path=str(file_path),
                                line_number=i,
                                code_snippet=line.strip()[:100],
                                description=self._get_description(vuln_type),
                                recommendation=self._get_recommendation(vuln_type),
                                cwe_id=self._get_cwe_id(vuln_type),
                                cvss_score=self._get_cvss_score(vuln_type),
                            )
                            vulnerabilities.append(vuln)

        except Exception as e:
            logger.debug(f"Error scanning {file_path}: {e}")

        return vulnerabilities

    async def _quick_scan(self, path: Path) -> SecurityAuditResult:
        """Quick security scan focusing on critical issues only."""
        result = SecurityAuditResult(
            target_path=str(path),
            scan_duration_ms=0,
            total_files_scanned=0,
        )

        if not path or not path.exists():
            return result

        # Only scan Python files for critical patterns
        critical_patterns = {
            VulnerabilityType.HARDCODED_SECRETS,
            VulnerabilityType.SQL_INJECTION,
            VulnerabilityType.COMMAND_INJECTION,
        }

        for file_path in path.rglob('*.py'):
            if file_path.is_file():
                result.total_files_scanned += 1
                vulns = await self._scan_file(file_path)
                result.vulnerabilities.extend([
                    v for v in vulns if v.type in critical_patterns
                ])

        return result

    async def _check_dependencies(self, path: Path) -> SecurityAuditResult:
        """Check dependencies for known vulnerabilities."""
        result = SecurityAuditResult(
            target_path=str(path),
            scan_duration_ms=0,
            total_files_scanned=0,
        )

        # Check requirements.txt
        requirements_file = path / "requirements.txt"
        if requirements_file.exists():
            # In real implementation, would check against vulnerability databases
            result.recommendations.append(
                "Run 'pip-audit' or 'safety check' to scan dependencies"
            )

        # Check package.json
        package_json = path / "package.json"
        if package_json.exists():
            result.recommendations.append(
                "Run 'npm audit' to scan JavaScript dependencies"
            )

        return result

    async def _scan_for_secrets(self, path: Path) -> SecurityAuditResult:
        """Scan specifically for hardcoded secrets."""
        result = SecurityAuditResult(
            target_path=str(path),
            scan_duration_ms=0,
            total_files_scanned=0,
        )

        secret_patterns = DANGEROUS_PATTERNS[VulnerabilityType.HARDCODED_SECRETS]

        for file_path in path.rglob('*'):
            if file_path.is_file() and file_path.suffix in {'.py', '.js', '.ts', '.env', '.yml', '.yaml', '.json'}:
                try:
                    content = file_path.read_text(errors='ignore')
                    lines = content.split('\n')

                    for pattern in secret_patterns:
                        for i, line in enumerate(lines, 1):
                            if re.search(pattern, line, re.IGNORECASE):
                                vuln = Vulnerability(
                                    id=hashlib.md5(f"{file_path}:{i}:secret".encode()).hexdigest()[:12],
                                    type=VulnerabilityType.HARDCODED_SECRETS,
                                    severity=SeverityLevel.CRITICAL,
                                    file_path=str(file_path),
                                    line_number=i,
                                    code_snippet="[REDACTED]",
                                    description="Potential hardcoded secret detected",
                                    recommendation="Move to environment variables or secrets manager",
                                )
                                result.vulnerabilities.append(vuln)
                except Exception:
                    continue

        return result

    def _get_severity(self, vuln_type: VulnerabilityType) -> SeverityLevel:
        """Get severity level for a vulnerability type."""
        critical = {
            VulnerabilityType.SQL_INJECTION,
            VulnerabilityType.COMMAND_INJECTION,
            VulnerabilityType.CODE_INJECTION,
            VulnerabilityType.HARDCODED_SECRETS,
            VulnerabilityType.INSECURE_DESERIALIZATION,
        }
        high = {
            VulnerabilityType.XSS,
            VulnerabilityType.PATH_TRAVERSAL,
            VulnerabilityType.BROKEN_AUTH,
            VulnerabilityType.SSRF,
        }

        if vuln_type in critical:
            return SeverityLevel.CRITICAL
        elif vuln_type in high:
            return SeverityLevel.HIGH
        else:
            return SeverityLevel.MEDIUM

    def _get_description(self, vuln_type: VulnerabilityType) -> str:
        """Get description for a vulnerability type."""
        descriptions = {
            VulnerabilityType.SQL_INJECTION: "SQL injection vulnerability allows attackers to manipulate database queries",
            VulnerabilityType.COMMAND_INJECTION: "Command injection allows execution of arbitrary system commands",
            VulnerabilityType.HARDCODED_SECRETS: "Hardcoded secrets can be extracted from source code",
            VulnerabilityType.XSS: "Cross-site scripting allows injection of malicious scripts",
            VulnerabilityType.PATH_TRAVERSAL: "Path traversal allows access to files outside intended directory",
            VulnerabilityType.INSECURE_RANDOM: "Use of weak random number generator for security-sensitive operations",
            VulnerabilityType.WEAK_CRYPTO: "Use of weak or deprecated cryptographic algorithms",
            VulnerabilityType.DEBUG_ENABLED: "Debug mode enabled in production environment",
        }
        return descriptions.get(vuln_type, f"Security issue: {vuln_type.value}")

    def _get_recommendation(self, vuln_type: VulnerabilityType) -> str:
        """Get recommendation for fixing a vulnerability."""
        recommendations = {
            VulnerabilityType.SQL_INJECTION: "Use parameterized queries or ORM",
            VulnerabilityType.COMMAND_INJECTION: "Avoid shell=True, use shlex.quote for inputs",
            VulnerabilityType.HARDCODED_SECRETS: "Use environment variables or secrets manager",
            VulnerabilityType.XSS: "Sanitize and escape user input",
            VulnerabilityType.PATH_TRAVERSAL: "Validate and sanitize file paths",
            VulnerabilityType.INSECURE_RANDOM: "Use secrets module for security-sensitive randomness",
            VulnerabilityType.WEAK_CRYPTO: "Use SHA-256 or stronger, AES-256 for encryption",
            VulnerabilityType.DEBUG_ENABLED: "Disable debug mode in production",
        }
        return recommendations.get(vuln_type, f"Review and fix: {vuln_type.value}")

    def _get_cwe_id(self, vuln_type: VulnerabilityType) -> str:
        """Get CWE ID for a vulnerability type."""
        cwe_mapping = {
            VulnerabilityType.SQL_INJECTION: "CWE-89",
            VulnerabilityType.COMMAND_INJECTION: "CWE-78",
            VulnerabilityType.CODE_INJECTION: "CWE-94",
            VulnerabilityType.XSS: "CWE-79",
            VulnerabilityType.HARDCODED_SECRETS: "CWE-798",
            VulnerabilityType.PATH_TRAVERSAL: "CWE-22",
            VulnerabilityType.INSECURE_RANDOM: "CWE-330",
            VulnerabilityType.WEAK_CRYPTO: "CWE-327",
        }
        return cwe_mapping.get(vuln_type, "")

    def _get_cvss_score(self, vuln_type: VulnerabilityType) -> float:
        """Get approximate CVSS score for a vulnerability type."""
        scores = {
            VulnerabilityType.SQL_INJECTION: 9.8,
            VulnerabilityType.COMMAND_INJECTION: 9.8,
            VulnerabilityType.CODE_INJECTION: 9.8,
            VulnerabilityType.HARDCODED_SECRETS: 9.1,
            VulnerabilityType.XSS: 7.5,
            VulnerabilityType.PATH_TRAVERSAL: 7.5,
            VulnerabilityType.INSECURE_RANDOM: 5.3,
            VulnerabilityType.WEAK_CRYPTO: 5.3,
            VulnerabilityType.DEBUG_ENABLED: 3.7,
        }
        return scores.get(vuln_type, 5.0)

    def _calculate_risk_score(self, result: SecurityAuditResult) -> float:
        """Calculate overall risk score (0-100)."""
        score = 0.0
        score += result.critical_count * 25
        score += result.high_count * 15
        score += result.medium_count * 5
        score += result.low_count * 1
        return min(100.0, score)

    def _generate_recommendations(self, result: SecurityAuditResult) -> List[str]:
        """Generate prioritized recommendations."""
        recommendations = []

        if result.critical_count > 0:
            recommendations.append(
                f"🚨 CRITICAL: Address {result.critical_count} critical vulnerabilities immediately"
            )

        if result.high_count > 0:
            recommendations.append(
                f"⚠️ HIGH: Fix {result.high_count} high-severity issues within 24 hours"
            )

        # Add specific recommendations based on vulnerability types found
        vuln_types = set(v.type for v in result.vulnerabilities)

        if VulnerabilityType.HARDCODED_SECRETS in vuln_types:
            recommendations.append(
                "Implement secrets management (e.g., HashiCorp Vault, AWS Secrets Manager)"
            )

        if VulnerabilityType.SQL_INJECTION in vuln_types:
            recommendations.append(
                "Adopt an ORM or implement parameterized queries throughout"
            )

        recommendations.append(
            "Set up automated security scanning in CI/CD pipeline"
        )

        return recommendations

    async def audit_project(self, path: Path) -> SecurityAuditResult:
        """Public method to audit a project."""
        return await self._full_audit(path)

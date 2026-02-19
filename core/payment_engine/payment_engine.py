"""
BAEL Payment Engine
====================

Payment processing with Stripe-like functionality.

"Ba'el's treasury processes all transactions with perfect precision." — Ba'el
"""

import asyncio
import logging
import uuid
import threading
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum, auto
from collections import defaultdict
from decimal import Decimal

logger = logging.getLogger("BAEL.Payment")


# ============================================================================
# ENUMS
# ============================================================================

class PaymentStatus(Enum):
    """Payment status."""
    PENDING = "pending"
    REQUIRES_ACTION = "requires_action"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"
    PARTIALLY_REFUNDED = "partially_refunded"


class PaymentMethod(Enum):
    """Payment method types."""
    CARD = "card"
    BANK_TRANSFER = "bank_transfer"
    PAYPAL = "paypal"
    CRYPTO = "crypto"
    WALLET = "wallet"


class Currency(Enum):
    """Currency codes."""
    USD = "usd"
    EUR = "eur"
    GBP = "gbp"
    JPY = "jpy"
    CAD = "cad"
    AUD = "aud"
    BTC = "btc"
    ETH = "eth"


class SubscriptionStatus(Enum):
    """Subscription status."""
    ACTIVE = "active"
    PAST_DUE = "past_due"
    UNPAID = "unpaid"
    CANCELLED = "cancelled"
    INCOMPLETE = "incomplete"
    TRIALING = "trialing"
    PAUSED = "paused"


class SubscriptionInterval(Enum):
    """Billing interval."""
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    YEAR = "year"


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class Price:
    """A price point."""
    id: str
    amount: int  # In cents
    currency: Currency = Currency.USD
    interval: Optional[SubscriptionInterval] = None
    interval_count: int = 1
    product_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PaymentIntent:
    """A payment intent."""
    id: str
    amount: int
    currency: Currency
    status: PaymentStatus = PaymentStatus.PENDING

    # Method
    payment_method_id: Optional[str] = None
    payment_method_type: Optional[PaymentMethod] = None

    # Customer
    customer_id: Optional[str] = None

    # Metadata
    description: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    confirmed_at: Optional[datetime] = None

    # Client secret for frontend
    client_secret: str = field(default_factory=lambda: str(uuid.uuid4()))


@dataclass
class Payment:
    """A completed payment."""
    id: str
    amount: int
    currency: Currency
    status: PaymentStatus

    # Intent
    payment_intent_id: str

    # Customer
    customer_id: Optional[str] = None

    # Method
    payment_method: Optional[PaymentMethod] = None
    last_four: Optional[str] = None

    # Refund
    amount_refunded: int = 0

    # Metadata
    description: Optional[str] = None
    receipt_url: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class Customer:
    """A customer."""
    id: str
    email: str
    name: Optional[str] = None

    # Payment methods
    default_payment_method_id: Optional[str] = None
    payment_methods: List[str] = field(default_factory=list)

    # Balance
    balance: int = 0  # In cents

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class Subscription:
    """A subscription."""
    id: str
    customer_id: str
    price_id: str

    # Status
    status: SubscriptionStatus = SubscriptionStatus.INCOMPLETE

    # Billing
    current_period_start: datetime = field(default_factory=datetime.now)
    current_period_end: Optional[datetime] = None

    # Trial
    trial_start: Optional[datetime] = None
    trial_end: Optional[datetime] = None

    # Cancellation
    cancel_at_period_end: bool = False
    cancelled_at: Optional[datetime] = None

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class Invoice:
    """An invoice."""
    id: str
    customer_id: str
    subscription_id: Optional[str] = None

    # Amounts
    amount_due: int = 0
    amount_paid: int = 0

    # Status
    paid: bool = False
    status: str = "draft"

    # Items
    lines: List[Dict[str, Any]] = field(default_factory=list)

    # URLs
    hosted_invoice_url: Optional[str] = None
    pdf_url: Optional[str] = None

    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    due_date: Optional[datetime] = None


@dataclass
class PaymentConfig:
    """Payment engine configuration."""
    # Provider
    provider: str = "mock"
    api_key: Optional[str] = None
    api_secret: Optional[str] = None

    # Webhooks
    webhook_secret: Optional[str] = None

    # Settings
    default_currency: Currency = Currency.USD
    auto_confirm: bool = True


# ============================================================================
# PAYMENT PROCESSOR (MOCK)
# ============================================================================

class MockProcessor:
    """Mock payment processor for testing."""

    def __init__(self):
        """Initialize processor."""
        self.transactions: List[Dict] = []

    async def create_payment_intent(
        self,
        amount: int,
        currency: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Create a payment intent."""
        intent = {
            'id': f"pi_{uuid.uuid4().hex[:24]}",
            'amount': amount,
            'currency': currency,
            'status': 'requires_confirmation',
            'client_secret': f"pi_{uuid.uuid4().hex}_secret_{uuid.uuid4().hex[:24]}"
        }
        self.transactions.append(intent)
        return intent

    async def confirm_payment(
        self,
        payment_intent_id: str,
        payment_method_id: str
    ) -> Dict[str, Any]:
        """Confirm a payment."""
        # Simulate processing
        await asyncio.sleep(0.1)

        return {
            'id': payment_intent_id,
            'status': 'succeeded',
            'payment_method': payment_method_id
        }

    async def create_refund(
        self,
        payment_intent_id: str,
        amount: Optional[int] = None
    ) -> Dict[str, Any]:
        """Create a refund."""
        return {
            'id': f"re_{uuid.uuid4().hex[:24]}",
            'payment_intent': payment_intent_id,
            'amount': amount,
            'status': 'succeeded'
        }


# ============================================================================
# MAIN PAYMENT ENGINE
# ============================================================================

class PaymentEngine:
    """
    Main payment engine.

    Features:
    - Payment intents
    - Subscriptions
    - Customers
    - Invoices

    "Ba'el's transactions are immutable and eternal." — Ba'el
    """

    def __init__(self, config: Optional[PaymentConfig] = None):
        """Initialize payment engine."""
        self.config = config or PaymentConfig()

        # Processor
        self._processor = MockProcessor()

        # Storage
        self._customers: Dict[str, Customer] = {}
        self._payment_intents: Dict[str, PaymentIntent] = {}
        self._payments: Dict[str, Payment] = {}
        self._subscriptions: Dict[str, Subscription] = {}
        self._invoices: Dict[str, Invoice] = {}
        self._prices: Dict[str, Price] = {}

        # Webhooks
        self._webhook_handlers: Dict[str, List[Callable]] = defaultdict(list)

        # Stats
        self._stats = defaultdict(int)

        self._lock = threading.RLock()

        logger.info("PaymentEngine initialized")

    # ========================================================================
    # CUSTOMERS
    # ========================================================================

    async def create_customer(
        self,
        email: str,
        name: Optional[str] = None,
        **kwargs
    ) -> Customer:
        """Create a customer."""
        customer = Customer(
            id=f"cus_{uuid.uuid4().hex[:24]}",
            email=email,
            name=name,
            **kwargs
        )

        with self._lock:
            self._customers[customer.id] = customer

        self._stats['customers_created'] += 1

        return customer

    def get_customer(self, customer_id: str) -> Optional[Customer]:
        """Get a customer by ID."""
        return self._customers.get(customer_id)

    async def update_customer(
        self,
        customer_id: str,
        **kwargs
    ) -> Optional[Customer]:
        """Update a customer."""
        with self._lock:
            if customer_id in self._customers:
                customer = self._customers[customer_id]
                for key, value in kwargs.items():
                    if hasattr(customer, key):
                        setattr(customer, key, value)
                return customer
        return None

    # ========================================================================
    # PRICES
    # ========================================================================

    async def create_price(
        self,
        amount: int,
        currency: Currency = Currency.USD,
        interval: Optional[SubscriptionInterval] = None,
        **kwargs
    ) -> Price:
        """Create a price."""
        price = Price(
            id=f"price_{uuid.uuid4().hex[:24]}",
            amount=amount,
            currency=currency,
            interval=interval,
            **kwargs
        )

        with self._lock:
            self._prices[price.id] = price

        return price

    def get_price(self, price_id: str) -> Optional[Price]:
        """Get a price by ID."""
        return self._prices.get(price_id)

    # ========================================================================
    # PAYMENT INTENTS
    # ========================================================================

    async def create_payment_intent(
        self,
        amount: int,
        currency: Currency = Currency.USD,
        customer_id: Optional[str] = None,
        **kwargs
    ) -> PaymentIntent:
        """
        Create a payment intent.

        Args:
            amount: Amount in cents
            currency: Currency
            customer_id: Customer ID

        Returns:
            PaymentIntent
        """
        intent = PaymentIntent(
            id=f"pi_{uuid.uuid4().hex[:24]}",
            amount=amount,
            currency=currency,
            customer_id=customer_id,
            **kwargs
        )

        with self._lock:
            self._payment_intents[intent.id] = intent

        self._stats['intents_created'] += 1

        await self._emit_event('payment_intent.created', intent)

        return intent

    async def confirm_payment_intent(
        self,
        payment_intent_id: str,
        payment_method_id: Optional[str] = None
    ) -> PaymentIntent:
        """Confirm a payment intent."""
        with self._lock:
            intent = self._payment_intents.get(payment_intent_id)

            if not intent:
                raise ValueError(f"Payment intent not found: {payment_intent_id}")

            if intent.status != PaymentStatus.PENDING:
                raise ValueError(f"Payment intent not pending: {intent.status}")

            # Confirm with processor
            intent.status = PaymentStatus.PROCESSING

        try:
            result = await self._processor.confirm_payment(
                payment_intent_id,
                payment_method_id or "pm_default"
            )

            intent.status = PaymentStatus.SUCCEEDED
            intent.confirmed_at = datetime.now()
            intent.payment_method_id = payment_method_id

            # Create payment record
            payment = Payment(
                id=f"pay_{uuid.uuid4().hex[:24]}",
                amount=intent.amount,
                currency=intent.currency,
                status=PaymentStatus.SUCCEEDED,
                payment_intent_id=intent.id,
                customer_id=intent.customer_id
            )

            with self._lock:
                self._payments[payment.id] = payment

            self._stats['payments_succeeded'] += 1

            await self._emit_event('payment_intent.succeeded', intent)

        except Exception as e:
            intent.status = PaymentStatus.FAILED
            self._stats['payments_failed'] += 1
            await self._emit_event('payment_intent.failed', intent)
            raise

        return intent

    # ========================================================================
    # SUBSCRIPTIONS
    # ========================================================================

    async def create_subscription(
        self,
        customer_id: str,
        price_id: str,
        trial_days: int = 0,
        **kwargs
    ) -> Subscription:
        """
        Create a subscription.

        Args:
            customer_id: Customer ID
            price_id: Price ID
            trial_days: Trial period days

        Returns:
            Subscription
        """
        # Verify customer
        customer = self.get_customer(customer_id)
        if not customer:
            raise ValueError(f"Customer not found: {customer_id}")

        # Verify price
        price = self.get_price(price_id)
        if not price:
            raise ValueError(f"Price not found: {price_id}")

        if not price.interval:
            raise ValueError("Price must have an interval for subscriptions")

        # Calculate period
        now = datetime.now()

        if price.interval == SubscriptionInterval.DAY:
            period_end = now + timedelta(days=price.interval_count)
        elif price.interval == SubscriptionInterval.WEEK:
            period_end = now + timedelta(weeks=price.interval_count)
        elif price.interval == SubscriptionInterval.MONTH:
            period_end = now + timedelta(days=30 * price.interval_count)
        else:
            period_end = now + timedelta(days=365 * price.interval_count)

        # Create subscription
        subscription = Subscription(
            id=f"sub_{uuid.uuid4().hex[:24]}",
            customer_id=customer_id,
            price_id=price_id,
            current_period_start=now,
            current_period_end=period_end,
            **kwargs
        )

        # Handle trial
        if trial_days > 0:
            subscription.trial_start = now
            subscription.trial_end = now + timedelta(days=trial_days)
            subscription.status = SubscriptionStatus.TRIALING
        else:
            subscription.status = SubscriptionStatus.ACTIVE

        with self._lock:
            self._subscriptions[subscription.id] = subscription

        self._stats['subscriptions_created'] += 1

        await self._emit_event('subscription.created', subscription)

        return subscription

    async def cancel_subscription(
        self,
        subscription_id: str,
        at_period_end: bool = True
    ) -> Subscription:
        """Cancel a subscription."""
        with self._lock:
            subscription = self._subscriptions.get(subscription_id)

            if not subscription:
                raise ValueError(f"Subscription not found: {subscription_id}")

            if at_period_end:
                subscription.cancel_at_period_end = True
            else:
                subscription.status = SubscriptionStatus.CANCELLED
                subscription.cancelled_at = datetime.now()

        self._stats['subscriptions_cancelled'] += 1

        await self._emit_event('subscription.cancelled', subscription)

        return subscription

    def get_subscription(self, subscription_id: str) -> Optional[Subscription]:
        """Get a subscription by ID."""
        return self._subscriptions.get(subscription_id)

    # ========================================================================
    # INVOICES
    # ========================================================================

    async def create_invoice(
        self,
        customer_id: str,
        items: List[Dict[str, Any]] = None,
        **kwargs
    ) -> Invoice:
        """Create an invoice."""
        items = items or []
        amount = sum(item.get('amount', 0) for item in items)

        invoice = Invoice(
            id=f"inv_{uuid.uuid4().hex[:24]}",
            customer_id=customer_id,
            amount_due=amount,
            lines=items,
            **kwargs
        )

        with self._lock:
            self._invoices[invoice.id] = invoice

        return invoice

    async def pay_invoice(self, invoice_id: str) -> Invoice:
        """Pay an invoice."""
        with self._lock:
            invoice = self._invoices.get(invoice_id)

            if not invoice:
                raise ValueError(f"Invoice not found: {invoice_id}")

            invoice.paid = True
            invoice.amount_paid = invoice.amount_due
            invoice.status = 'paid'

        return invoice

    # ========================================================================
    # REFUNDS
    # ========================================================================

    async def refund_payment(
        self,
        payment_id: str,
        amount: Optional[int] = None
    ) -> Payment:
        """Refund a payment."""
        with self._lock:
            payment = self._payments.get(payment_id)

            if not payment:
                raise ValueError(f"Payment not found: {payment_id}")

            refund_amount = amount or (payment.amount - payment.amount_refunded)

            if refund_amount > (payment.amount - payment.amount_refunded):
                raise ValueError("Refund amount exceeds available balance")

        # Process refund
        await self._processor.create_refund(payment.payment_intent_id, refund_amount)

        payment.amount_refunded += refund_amount

        if payment.amount_refunded >= payment.amount:
            payment.status = PaymentStatus.REFUNDED
        else:
            payment.status = PaymentStatus.PARTIALLY_REFUNDED

        self._stats['refunds_issued'] += 1

        return payment

    # ========================================================================
    # WEBHOOKS
    # ========================================================================

    def on(self, event: str, handler: Callable) -> None:
        """Register a webhook handler."""
        self._webhook_handlers[event].append(handler)

    async def _emit_event(self, event: str, data: Any) -> None:
        """Emit a webhook event."""
        handlers = self._webhook_handlers.get(event, [])

        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event, data)
                else:
                    handler(event, data)
            except Exception as e:
                logger.error(f"Webhook handler error: {e}")

    # ========================================================================
    # STATUS
    # ========================================================================

    def get_status(self) -> Dict[str, Any]:
        """Get engine status."""
        return {
            'provider': self.config.provider,
            'customers': len(self._customers),
            'subscriptions': len(self._subscriptions),
            'payments': len(self._payments),
            'stats': dict(self._stats)
        }


# ============================================================================
# CONVENIENCE INSTANCE
# ============================================================================

payment_engine = PaymentEngine()

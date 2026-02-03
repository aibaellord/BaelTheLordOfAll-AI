#!/usr/bin/env python3
"""
BAEL - Localization Manager
Comprehensive internationalization (i18n) and localization (l10n) system.

Features:
- Multi-language support
- Translation management
- Message formatting
- Pluralization
- Number/date/currency formatting
- Locale detection
- Translation fallback
- Context-aware translations
- Variable interpolation
- ICU message format
"""

import asyncio
import hashlib
import json
import logging
import re
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal
from enum import Enum, auto
from typing import (Any, Callable, Dict, Generic, Iterator, List, Optional,
                    Set, Tuple, Type, TypeVar, Union)

logger = logging.getLogger(__name__)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class PluralCategory(Enum):
    """CLDR plural categories."""
    ZERO = "zero"
    ONE = "one"
    TWO = "two"
    FEW = "few"
    MANY = "many"
    OTHER = "other"


class DateFormat(Enum):
    """Date format styles."""
    SHORT = "short"
    MEDIUM = "medium"
    LONG = "long"
    FULL = "full"


class NumberFormat(Enum):
    """Number format styles."""
    DECIMAL = "decimal"
    CURRENCY = "currency"
    PERCENT = "percent"
    SCIENTIFIC = "scientific"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class Locale:
    """Locale representation."""
    language: str
    region: Optional[str] = None
    script: Optional[str] = None
    variant: Optional[str] = None

    @classmethod
    def parse(cls, locale_str: str) -> 'Locale':
        """Parse locale string."""
        parts = locale_str.replace("-", "_").split("_")

        language = parts[0].lower() if parts else "en"
        region = parts[1].upper() if len(parts) > 1 else None
        script = parts[2] if len(parts) > 2 else None
        variant = parts[3] if len(parts) > 3 else None

        return cls(
            language=language,
            region=region,
            script=script,
            variant=variant
        )

    def __str__(self) -> str:
        parts = [self.language]

        if self.region:
            parts.append(self.region)

        if self.script:
            parts.append(self.script)

        if self.variant:
            parts.append(self.variant)

        return "_".join(parts)

    @property
    def language_tag(self) -> str:
        """Get BCP 47 language tag."""
        parts = [self.language]

        if self.script:
            parts.append(self.script)

        if self.region:
            parts.append(self.region)

        return "-".join(parts)

    def matches(self, other: 'Locale') -> bool:
        """Check if locales match."""
        if self.language != other.language:
            return False

        if self.region and other.region and self.region != other.region:
            return False

        return True


@dataclass
class TranslationEntry:
    """Translation entry."""
    key: str
    value: str
    locale: str
    context: Optional[str] = None
    plural_forms: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class LocaleData:
    """Locale-specific data."""
    locale: str
    decimal_separator: str = "."
    thousands_separator: str = ","
    currency_symbol: str = "$"
    currency_code: str = "USD"
    date_format: str = "%Y-%m-%d"
    time_format: str = "%H:%M:%S"
    datetime_format: str = "%Y-%m-%d %H:%M:%S"
    first_day_of_week: int = 0  # 0 = Sunday, 1 = Monday
    rtl: bool = False

    # Names
    month_names: List[str] = field(default_factory=list)
    month_abbreviations: List[str] = field(default_factory=list)
    day_names: List[str] = field(default_factory=list)
    day_abbreviations: List[str] = field(default_factory=list)


# =============================================================================
# PLURAL RULES
# =============================================================================

class PluralRule(ABC):
    """Abstract plural rule."""

    @abstractmethod
    def select(self, n: float) -> PluralCategory:
        """Select plural category for number."""
        pass


class EnglishPluralRule(PluralRule):
    """English plural rules."""

    def select(self, n: float) -> PluralCategory:
        """Select plural category."""
        if n == 1:
            return PluralCategory.ONE

        return PluralCategory.OTHER


class RussianPluralRule(PluralRule):
    """Russian plural rules."""

    def select(self, n: float) -> PluralCategory:
        """Select plural category."""
        n = abs(int(n))

        if n % 10 == 1 and n % 100 != 11:
            return PluralCategory.ONE

        if n % 10 >= 2 and n % 10 <= 4 and (n % 100 < 10 or n % 100 >= 20):
            return PluralCategory.FEW

        return PluralCategory.MANY


class ArabicPluralRule(PluralRule):
    """Arabic plural rules."""

    def select(self, n: float) -> PluralCategory:
        """Select plural category."""
        n = abs(int(n))

        if n == 0:
            return PluralCategory.ZERO

        if n == 1:
            return PluralCategory.ONE

        if n == 2:
            return PluralCategory.TWO

        if n % 100 >= 3 and n % 100 <= 10:
            return PluralCategory.FEW

        if n % 100 >= 11:
            return PluralCategory.MANY

        return PluralCategory.OTHER


class PluralRules:
    """Plural rules registry."""

    _rules: Dict[str, PluralRule] = {
        "en": EnglishPluralRule(),
        "ru": RussianPluralRule(),
        "ar": ArabicPluralRule(),
    }

    @classmethod
    def get(cls, language: str) -> PluralRule:
        """Get plural rule for language."""
        return cls._rules.get(language, EnglishPluralRule())

    @classmethod
    def register(cls, language: str, rule: PluralRule) -> None:
        """Register plural rule."""
        cls._rules[language] = rule


# =============================================================================
# MESSAGE FORMATTER
# =============================================================================

class MessageFormatter:
    """ICU-like message formatter."""

    VARIABLE_PATTERN = re.compile(r'\{(\w+)(?:,\s*(\w+)(?:,\s*(.+?))?)?\}')

    def __init__(self, locale: str):
        self.locale = Locale.parse(locale)
        self.plural_rule = PluralRules.get(self.locale.language)

    def format(self, message: str, values: Dict[str, Any] = None) -> str:
        """Format message with values."""
        if not values:
            return message

        def replace_match(match: re.Match) -> str:
            variable_name = match.group(1)
            format_type = match.group(2)
            format_style = match.group(3)

            if variable_name not in values:
                return match.group(0)

            value = values[variable_name]

            if format_type is None:
                return str(value)

            elif format_type == "number":
                return self._format_number(value, format_style)

            elif format_type == "date":
                return self._format_date(value, format_style)

            elif format_type == "time":
                return self._format_time(value, format_style)

            elif format_type == "plural":
                return self._format_plural(value, format_style, values)

            elif format_type == "select":
                return self._format_select(value, format_style)

            return str(value)

        return self.VARIABLE_PATTERN.sub(replace_match, message)

    def _format_number(self, value: float, style: str = None) -> str:
        """Format number."""
        if style == "percent":
            return f"{value * 100:.1f}%"

        elif style == "currency":
            return f"${value:,.2f}"

        elif style == "integer":
            return f"{int(value):,}"

        return f"{value:,}"

    def _format_date(self, value: Union[datetime, date], style: str = None) -> str:
        """Format date."""
        if isinstance(value, datetime):
            value = value.date()

        if style == "short":
            return value.strftime("%m/%d/%y")

        elif style == "medium":
            return value.strftime("%b %d, %Y")

        elif style == "long":
            return value.strftime("%B %d, %Y")

        elif style == "full":
            return value.strftime("%A, %B %d, %Y")

        return value.strftime("%Y-%m-%d")

    def _format_time(self, value: datetime, style: str = None) -> str:
        """Format time."""
        if style == "short":
            return value.strftime("%H:%M")

        elif style == "medium":
            return value.strftime("%H:%M:%S")

        elif style == "long":
            return value.strftime("%H:%M:%S %Z")

        return value.strftime("%H:%M:%S")

    def _format_plural(
        self,
        value: float,
        pattern: str,
        values: Dict[str, Any]
    ) -> str:
        """Format plural."""
        category = self.plural_rule.select(value)

        # Parse plural options
        options = self._parse_options(pattern)

        # Try exact match first
        if f"={int(value)}" in options:
            return options[f"={int(value)}"]

        # Then category match
        if category.value in options:
            return options[category.value]

        # Fallback to other
        return options.get("other", str(value))

    def _format_select(self, value: str, pattern: str) -> str:
        """Format select."""
        options = self._parse_options(pattern)
        return options.get(value, options.get("other", value))

    def _parse_options(self, pattern: str) -> Dict[str, str]:
        """Parse options from pattern."""
        options = {}

        if not pattern:
            return options

        # Simple parsing for key{value} pairs
        current_key = None
        current_value = []
        depth = 0

        parts = pattern.split()
        i = 0

        while i < len(parts):
            part = parts[i]

            if depth == 0 and "{" not in part:
                current_key = part

            elif "{" in part:
                value_start = part.index("{") + 1

                if "}" in part:
                    # Single word value
                    value_end = part.index("}")
                    options[current_key] = part[value_start:value_end]

                else:
                    depth += part.count("{")
                    current_value.append(part[value_start:])

            elif depth > 0:
                if "}" in part:
                    depth -= part.count("}")

                    if depth == 0:
                        value_end = part.index("}")
                        current_value.append(part[:value_end])
                        options[current_key] = " ".join(current_value)
                        current_value = []
                    else:
                        current_value.append(part)

                else:
                    current_value.append(part)

            i += 1

        return options


# =============================================================================
# TRANSLATION STORE
# =============================================================================

class TranslationStore(ABC):
    """Abstract translation store."""

    @abstractmethod
    async def get(
        self,
        key: str,
        locale: str,
        context: str = None
    ) -> Optional[TranslationEntry]:
        """Get translation."""
        pass

    @abstractmethod
    async def set(self, entry: TranslationEntry) -> None:
        """Set translation."""
        pass

    @abstractmethod
    async def get_all(self, locale: str) -> Dict[str, TranslationEntry]:
        """Get all translations for locale."""
        pass


class MemoryTranslationStore(TranslationStore):
    """In-memory translation store."""

    def __init__(self):
        self._translations: Dict[str, Dict[str, TranslationEntry]] = defaultdict(dict)

    async def get(
        self,
        key: str,
        locale: str,
        context: str = None
    ) -> Optional[TranslationEntry]:
        """Get translation."""
        locale_key = f"{locale}:{context}" if context else locale
        return self._translations[locale_key].get(key)

    async def set(self, entry: TranslationEntry) -> None:
        """Set translation."""
        locale_key = f"{entry.locale}:{entry.context}" if entry.context else entry.locale
        self._translations[locale_key][entry.key] = entry

    async def get_all(self, locale: str) -> Dict[str, TranslationEntry]:
        """Get all translations for locale."""
        return dict(self._translations.get(locale, {}))

    def load_from_dict(self, locale: str, translations: Dict[str, str]) -> int:
        """Load translations from dictionary."""
        count = 0

        for key, value in translations.items():
            entry = TranslationEntry(key=key, value=value, locale=locale)
            self._translations[locale][key] = entry
            count += 1

        return count


# =============================================================================
# LOCALIZATION MANAGER
# =============================================================================

class LocalizationManager:
    """
    Comprehensive Localization Manager for BAEL.

    Provides i18n/l10n with advanced features.
    """

    def __init__(
        self,
        default_locale: str = "en",
        fallback_locale: str = "en",
        store: TranslationStore = None
    ):
        self.default_locale = default_locale
        self.fallback_locale = fallback_locale
        self._store = store or MemoryTranslationStore()
        self._locale_data: Dict[str, LocaleData] = {}
        self._formatters: Dict[str, MessageFormatter] = {}
        self._current_locale = default_locale

        # Initialize default locale data
        self._init_default_locale_data()

    def _init_default_locale_data(self) -> None:
        """Initialize default locale data."""
        self._locale_data["en"] = LocaleData(
            locale="en",
            decimal_separator=".",
            thousands_separator=",",
            currency_symbol="$",
            currency_code="USD",
            date_format="%m/%d/%Y",
            time_format="%I:%M %p",
            month_names=[
                "January", "February", "March", "April", "May", "June",
                "July", "August", "September", "October", "November", "December"
            ],
            month_abbreviations=[
                "Jan", "Feb", "Mar", "Apr", "May", "Jun",
                "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
            ],
            day_names=[
                "Sunday", "Monday", "Tuesday", "Wednesday",
                "Thursday", "Friday", "Saturday"
            ],
            day_abbreviations=["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
        )

        self._locale_data["nl"] = LocaleData(
            locale="nl",
            decimal_separator=",",
            thousands_separator=".",
            currency_symbol="€",
            currency_code="EUR",
            date_format="%d-%m-%Y",
            time_format="%H:%M",
            first_day_of_week=1,
            month_names=[
                "januari", "februari", "maart", "april", "mei", "juni",
                "juli", "augustus", "september", "oktober", "november", "december"
            ],
            month_abbreviations=[
                "jan", "feb", "mrt", "apr", "mei", "jun",
                "jul", "aug", "sep", "okt", "nov", "dec"
            ],
            day_names=[
                "zondag", "maandag", "dinsdag", "woensdag",
                "donderdag", "vrijdag", "zaterdag"
            ],
            day_abbreviations=["zo", "ma", "di", "wo", "do", "vr", "za"]
        )

        self._locale_data["de"] = LocaleData(
            locale="de",
            decimal_separator=",",
            thousands_separator=".",
            currency_symbol="€",
            currency_code="EUR",
            date_format="%d.%m.%Y",
            time_format="%H:%M",
            first_day_of_week=1,
            month_names=[
                "Januar", "Februar", "März", "April", "Mai", "Juni",
                "Juli", "August", "September", "Oktober", "November", "Dezember"
            ],
            month_abbreviations=[
                "Jan", "Feb", "Mär", "Apr", "Mai", "Jun",
                "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"
            ],
            day_names=[
                "Sonntag", "Montag", "Dienstag", "Mittwoch",
                "Donnerstag", "Freitag", "Samstag"
            ],
            day_abbreviations=["So", "Mo", "Di", "Mi", "Do", "Fr", "Sa"]
        )

    def _get_formatter(self, locale: str) -> MessageFormatter:
        """Get or create formatter for locale."""
        if locale not in self._formatters:
            self._formatters[locale] = MessageFormatter(locale)

        return self._formatters[locale]

    # -------------------------------------------------------------------------
    # LOCALE MANAGEMENT
    # -------------------------------------------------------------------------

    def set_locale(self, locale: str) -> None:
        """Set current locale."""
        self._current_locale = locale

    def get_locale(self) -> str:
        """Get current locale."""
        return self._current_locale

    def set_locale_data(self, data: LocaleData) -> None:
        """Set locale data."""
        self._locale_data[data.locale] = data

    def get_locale_data(self, locale: str = None) -> Optional[LocaleData]:
        """Get locale data."""
        locale = locale or self._current_locale
        return self._locale_data.get(locale)

    @property
    def supported_locales(self) -> List[str]:
        """Get supported locales."""
        return list(self._locale_data.keys())

    # -------------------------------------------------------------------------
    # TRANSLATIONS
    # -------------------------------------------------------------------------

    async def translate(
        self,
        key: str,
        values: Dict[str, Any] = None,
        locale: str = None,
        context: str = None,
        count: int = None
    ) -> str:
        """Translate key with optional formatting."""
        locale = locale or self._current_locale

        # Try exact locale
        entry = await self._store.get(key, locale, context)

        # Fallback to language only
        if not entry and "_" in locale:
            language = locale.split("_")[0]
            entry = await self._store.get(key, language, context)

        # Fallback to fallback locale
        if not entry and locale != self.fallback_locale:
            entry = await self._store.get(key, self.fallback_locale, context)

        if not entry:
            return key

        # Handle pluralization
        if count is not None and entry.plural_forms:
            plural_rule = PluralRules.get(Locale.parse(locale).language)
            category = plural_rule.select(count)

            message = entry.plural_forms.get(
                category.value,
                entry.plural_forms.get("other", entry.value)
            )
        else:
            message = entry.value

        # Format message
        if values:
            formatter = self._get_formatter(locale)
            message = formatter.format(message, values)

        return message

    # Shorthand
    async def t(
        self,
        key: str,
        values: Dict[str, Any] = None,
        **kwargs
    ) -> str:
        """Shorthand for translate."""
        return await self.translate(key, values, **kwargs)

    async def add_translation(
        self,
        key: str,
        value: str,
        locale: str,
        context: str = None,
        plural_forms: Dict[str, str] = None
    ) -> None:
        """Add translation."""
        entry = TranslationEntry(
            key=key,
            value=value,
            locale=locale,
            context=context,
            plural_forms=plural_forms or {}
        )

        await self._store.set(entry)

    async def load_translations(
        self,
        locale: str,
        translations: Dict[str, Union[str, Dict[str, str]]]
    ) -> int:
        """Load translations from dictionary."""
        count = 0

        for key, value in translations.items():
            if isinstance(value, dict):
                # Plural forms
                await self.add_translation(
                    key=key,
                    value=value.get("other", ""),
                    locale=locale,
                    plural_forms=value
                )
            else:
                await self.add_translation(
                    key=key,
                    value=value,
                    locale=locale
                )

            count += 1

        return count

    # -------------------------------------------------------------------------
    # FORMATTING
    # -------------------------------------------------------------------------

    def format_number(
        self,
        value: float,
        style: NumberFormat = NumberFormat.DECIMAL,
        locale: str = None,
        precision: int = None
    ) -> str:
        """Format number."""
        locale = locale or self._current_locale
        data = self._locale_data.get(locale)

        if not data:
            data = LocaleData(locale=locale)

        if style == NumberFormat.CURRENCY:
            formatted = f"{abs(value):,.2f}"
            formatted = formatted.replace(",", "TEMP")
            formatted = formatted.replace(".", data.decimal_separator)
            formatted = formatted.replace("TEMP", data.thousands_separator)

            sign = "-" if value < 0 else ""
            return f"{sign}{data.currency_symbol}{formatted}"

        elif style == NumberFormat.PERCENT:
            formatted = f"{value * 100:.1f}%"
            return formatted.replace(".", data.decimal_separator)

        elif style == NumberFormat.SCIENTIFIC:
            return f"{value:.2e}"

        # Decimal
        if precision is not None:
            formatted = f"{value:,.{precision}f}"
        else:
            formatted = f"{value:,.2f}"

        formatted = formatted.replace(",", "TEMP")
        formatted = formatted.replace(".", data.decimal_separator)
        formatted = formatted.replace("TEMP", data.thousands_separator)

        return formatted

    def format_date(
        self,
        value: Union[datetime, date],
        style: DateFormat = DateFormat.MEDIUM,
        locale: str = None
    ) -> str:
        """Format date."""
        locale = locale or self._current_locale
        data = self._locale_data.get(locale)

        if isinstance(value, datetime):
            value = value.date()

        if not data:
            return value.strftime("%Y-%m-%d")

        if style == DateFormat.SHORT:
            return value.strftime(data.date_format.replace("%Y", "%y"))

        elif style == DateFormat.MEDIUM:
            month_name = data.month_abbreviations[value.month - 1]
            return f"{value.day} {month_name} {value.year}"

        elif style == DateFormat.LONG:
            month_name = data.month_names[value.month - 1]
            return f"{value.day} {month_name} {value.year}"

        elif style == DateFormat.FULL:
            day_name = data.day_names[value.weekday()]
            month_name = data.month_names[value.month - 1]
            return f"{day_name}, {value.day} {month_name} {value.year}"

        return value.strftime(data.date_format)

    def format_time(
        self,
        value: datetime,
        style: DateFormat = DateFormat.MEDIUM,
        locale: str = None
    ) -> str:
        """Format time."""
        locale = locale or self._current_locale
        data = self._locale_data.get(locale)

        if not data:
            return value.strftime("%H:%M:%S")

        if style == DateFormat.SHORT:
            return value.strftime("%H:%M")

        elif style == DateFormat.MEDIUM:
            return value.strftime(data.time_format)

        elif style == DateFormat.LONG:
            return value.strftime(f"{data.time_format}:%S")

        return value.strftime(data.time_format)

    def format_datetime(
        self,
        value: datetime,
        date_style: DateFormat = DateFormat.MEDIUM,
        time_style: DateFormat = DateFormat.MEDIUM,
        locale: str = None
    ) -> str:
        """Format datetime."""
        date_part = self.format_date(value, date_style, locale)
        time_part = self.format_time(value, time_style, locale)

        return f"{date_part} {time_part}"

    def format_relative_time(
        self,
        value: datetime,
        base: datetime = None,
        locale: str = None
    ) -> str:
        """Format relative time."""
        locale = locale or self._current_locale
        base = base or datetime.utcnow()

        diff = base - value

        if diff.days < 0:
            # Future
            return self._format_future_time(abs(diff), locale)

        return self._format_past_time(diff, locale)

    def _format_past_time(self, diff: timedelta, locale: str) -> str:
        """Format past relative time."""
        seconds = diff.total_seconds()

        if seconds < 60:
            return "just now"

        if seconds < 3600:
            minutes = int(seconds / 60)
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"

        if seconds < 86400:
            hours = int(seconds / 3600)
            return f"{hours} hour{'s' if hours != 1 else ''} ago"

        if diff.days == 1:
            return "yesterday"

        if diff.days < 7:
            return f"{diff.days} days ago"

        if diff.days < 30:
            weeks = diff.days // 7
            return f"{weeks} week{'s' if weeks != 1 else ''} ago"

        if diff.days < 365:
            months = diff.days // 30
            return f"{months} month{'s' if months != 1 else ''} ago"

        years = diff.days // 365
        return f"{years} year{'s' if years != 1 else ''} ago"

    def _format_future_time(self, diff: timedelta, locale: str) -> str:
        """Format future relative time."""
        seconds = diff.total_seconds()

        if seconds < 60:
            return "in a moment"

        if seconds < 3600:
            minutes = int(seconds / 60)
            return f"in {minutes} minute{'s' if minutes != 1 else ''}"

        if seconds < 86400:
            hours = int(seconds / 3600)
            return f"in {hours} hour{'s' if hours != 1 else ''}"

        if diff.days == 1:
            return "tomorrow"

        if diff.days < 7:
            return f"in {diff.days} days"

        if diff.days < 30:
            weeks = diff.days // 7
            return f"in {weeks} week{'s' if weeks != 1 else ''}"

        if diff.days < 365:
            months = diff.days // 30
            return f"in {months} month{'s' if months != 1 else ''}"

        years = diff.days // 365
        return f"in {years} year{'s' if years != 1 else ''}"

    def format_currency(
        self,
        value: float,
        currency: str = None,
        locale: str = None
    ) -> str:
        """Format currency."""
        locale = locale or self._current_locale
        data = self._locale_data.get(locale)

        if not data:
            return f"${value:.2f}"

        formatted = self.format_number(value, NumberFormat.DECIMAL, locale, 2)
        symbol = currency or data.currency_symbol

        return f"{symbol}{formatted}"

    # -------------------------------------------------------------------------
    # DETECTION
    # -------------------------------------------------------------------------

    def detect_locale(
        self,
        accept_language: str = None,
        preferred: List[str] = None
    ) -> str:
        """Detect best matching locale."""
        candidates = []

        # Parse Accept-Language header
        if accept_language:
            for part in accept_language.split(","):
                part = part.strip()

                if ";q=" in part:
                    lang, q = part.split(";q=")
                    quality = float(q)
                else:
                    lang = part
                    quality = 1.0

                candidates.append((lang.strip(), quality))

        # Add preferred locales
        if preferred:
            for i, locale in enumerate(preferred):
                quality = 0.9 - (i * 0.1)
                candidates.append((locale, quality))

        # Sort by quality
        candidates.sort(key=lambda x: x[1], reverse=True)

        # Find best match
        for locale, _ in candidates:
            locale_obj = Locale.parse(locale)

            for supported in self.supported_locales:
                supported_obj = Locale.parse(supported)

                if locale_obj.matches(supported_obj):
                    return supported

        return self.default_locale

    # -------------------------------------------------------------------------
    # UTILITIES
    # -------------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Get localization statistics."""
        return {
            "current_locale": self._current_locale,
            "default_locale": self.default_locale,
            "fallback_locale": self.fallback_locale,
            "supported_locales": self.supported_locales
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Localization Manager."""
    print("=" * 70)
    print("BAEL - LOCALIZATION MANAGER DEMO")
    print("Comprehensive I18n/L10n System")
    print("=" * 70)
    print()

    # Create manager
    manager = LocalizationManager(default_locale="en")

    # 1. Load Translations
    print("1. LOADING TRANSLATIONS:")
    print("-" * 40)

    en_translations = {
        "greeting": "Hello, {name}!",
        "welcome": "Welcome to BAEL",
        "items_count": {
            "one": "You have {count} item",
            "other": "You have {count} items"
        },
        "goodbye": "Goodbye!"
    }

    nl_translations = {
        "greeting": "Hallo, {name}!",
        "welcome": "Welkom bij BAEL",
        "items_count": {
            "one": "Je hebt {count} item",
            "other": "Je hebt {count} items"
        },
        "goodbye": "Tot ziens!"
    }

    de_translations = {
        "greeting": "Hallo, {name}!",
        "welcome": "Willkommen bei BAEL",
        "items_count": {
            "one": "Sie haben {count} Artikel",
            "other": "Sie haben {count} Artikel"
        },
        "goodbye": "Auf Wiedersehen!"
    }

    count_en = await manager.load_translations("en", en_translations)
    count_nl = await manager.load_translations("nl", nl_translations)
    count_de = await manager.load_translations("de", de_translations)

    print(f"   English: {count_en} translations")
    print(f"   Dutch: {count_nl} translations")
    print(f"   German: {count_de} translations")
    print()

    # 2. Basic Translations
    print("2. BASIC TRANSLATIONS:")
    print("-" * 40)

    for locale in ["en", "nl", "de"]:
        manager.set_locale(locale)
        greeting = await manager.t("greeting", {"name": "BAEL"})
        welcome = await manager.t("welcome")
        print(f"   [{locale}] {greeting} - {welcome}")
    print()

    # 3. Pluralization
    print("3. PLURALIZATION:")
    print("-" * 40)

    for count in [0, 1, 2, 5, 10]:
        manager.set_locale("en")
        en_text = await manager.t("items_count", {"count": count}, count=count)

        manager.set_locale("nl")
        nl_text = await manager.t("items_count", {"count": count}, count=count)

        print(f"   Count {count}: [en] {en_text} | [nl] {nl_text}")
    print()

    # 4. Number Formatting
    print("4. NUMBER FORMATTING:")
    print("-" * 40)

    number = 1234567.89

    for locale in ["en", "nl", "de"]:
        formatted = manager.format_number(number, locale=locale)
        currency = manager.format_currency(number, locale=locale)
        percent = manager.format_number(0.1542, NumberFormat.PERCENT, locale)

        print(f"   [{locale}] {formatted} | {currency} | {percent}")
    print()

    # 5. Date Formatting
    print("5. DATE FORMATTING:")
    print("-" * 40)

    today = datetime.now()

    for locale in ["en", "nl", "de"]:
        for style in [DateFormat.SHORT, DateFormat.MEDIUM, DateFormat.LONG]:
            formatted = manager.format_date(today, style, locale)
            print(f"   [{locale}] {style.value}: {formatted}")
    print()

    # 6. Relative Time
    print("6. RELATIVE TIME:")
    print("-" * 40)

    now = datetime.utcnow()

    times = [
        now - timedelta(seconds=30),
        now - timedelta(minutes=5),
        now - timedelta(hours=2),
        now - timedelta(days=1),
        now - timedelta(weeks=2),
        now + timedelta(hours=3)
    ]

    for t in times:
        relative = manager.format_relative_time(t, now)
        print(f"   {relative}")
    print()

    # 7. Message Formatting
    print("7. MESSAGE FORMATTING:")
    print("-" * 40)

    formatter = MessageFormatter("en")

    messages = [
        ("Hello, {name}!", {"name": "World"}),
        ("Count: {count, number}", {"count": 1234567}),
        ("Date: {date, date, long}", {"date": datetime.now()}),
        ("Price: {price, number, currency}", {"price": 99.99})
    ]

    for template, values in messages:
        result = formatter.format(template, values)
        print(f"   {template}")
        print(f"   → {result}")
    print()

    # 8. Locale Detection
    print("8. LOCALE DETECTION:")
    print("-" * 40)

    accept_headers = [
        "en-US,en;q=0.9",
        "nl-NL,nl;q=0.9,en;q=0.8",
        "de-DE,de;q=0.9,en;q=0.8",
        "fr-FR,fr;q=0.9"
    ]

    for header in accept_headers:
        detected = manager.detect_locale(accept_language=header)
        print(f"   '{header[:20]}...' → {detected}")
    print()

    # 9. Locale Data
    print("9. LOCALE DATA:")
    print("-" * 40)

    for locale in ["en", "nl", "de"]:
        data = manager.get_locale_data(locale)

        if data:
            print(f"   [{locale}]")
            print(f"      Decimal: {data.decimal_separator}")
            print(f"      Currency: {data.currency_symbol}")
            print(f"      First day: {data.day_names[data.first_day_of_week]}")
    print()

    # 10. Fallback
    print("10. TRANSLATION FALLBACK:")
    print("-" * 40)

    manager.set_locale("fr")  # No French translations
    result = await manager.t("welcome")
    print(f"   French (missing): '{result}'")
    print(f"   (Falls back to English)")
    print()

    # 11. Locale Object
    print("11. LOCALE PARSING:")
    print("-" * 40)

    locale_strings = ["en", "en_US", "zh_Hans_CN", "sr-Latn-RS"]

    for ls in locale_strings:
        locale = Locale.parse(ls)
        print(f"   '{ls}' → lang={locale.language}, region={locale.region}")
    print()

    # 12. Stats
    print("12. STATISTICS:")
    print("-" * 40)

    stats = manager.get_stats()

    print(f"   Current: {stats['current_locale']}")
    print(f"   Default: {stats['default_locale']}")
    print(f"   Fallback: {stats['fallback_locale']}")
    print(f"   Supported: {stats['supported_locales']}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Localization Manager Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())

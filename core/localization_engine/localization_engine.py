"""
BAEL Localization Engine
=========================

Internationalization (i18n), translations, and formatting.

"Ba'el's words transcend all mortal languages." — Ba'el
"""

import asyncio
import logging
import re
import threading
from datetime import datetime, date
from typing import Any, Dict, List, Optional, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
from decimal import Decimal
import contextvars

logger = logging.getLogger("BAEL.Localization")

# Context variable for current locale
_current_locale: contextvars.ContextVar[str] = contextvars.ContextVar('locale', default='en')


# ============================================================================
# ENUMS
# ============================================================================

class PluralForm(Enum):
    """Plural forms."""
    ZERO = "zero"
    ONE = "one"
    TWO = "two"
    FEW = "few"
    MANY = "many"
    OTHER = "other"


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class Locale:
    """A locale definition."""
    code: str  # e.g., "en", "en-US", "fr-FR"
    name: str
    native_name: str

    # Regional
    language: str
    region: Optional[str] = None

    # Formatting
    date_format: str = "%Y-%m-%d"
    time_format: str = "%H:%M:%S"
    datetime_format: str = "%Y-%m-%d %H:%M:%S"

    # Numbers
    decimal_separator: str = "."
    thousands_separator: str = ","

    # Currency
    currency_code: str = "USD"
    currency_symbol: str = "$"
    currency_position: str = "before"  # before or after

    # Direction
    rtl: bool = False

    # Plural rule
    plural_rule: Optional[Callable[[int], PluralForm]] = None


@dataclass
class Translation:
    """A translation entry."""
    key: str
    value: str
    locale: str

    # Plural forms
    plurals: Dict[str, str] = field(default_factory=dict)

    # Context
    context: Optional[str] = None


@dataclass
class LocaleConfig:
    """Localization engine configuration."""
    default_locale: str = "en"
    fallback_locale: str = "en"
    supported_locales: List[str] = field(default_factory=lambda: ["en"])


# ============================================================================
# PLURAL RULES
# ============================================================================

def english_plural(n: int) -> PluralForm:
    """English plural rule."""
    if n == 1:
        return PluralForm.ONE
    return PluralForm.OTHER


def french_plural(n: int) -> PluralForm:
    """French plural rule (0 and 1 are singular)."""
    if n == 0 or n == 1:
        return PluralForm.ONE
    return PluralForm.OTHER


def russian_plural(n: int) -> PluralForm:
    """Russian plural rule."""
    n_mod_10 = n % 10
    n_mod_100 = n % 100

    if n_mod_10 == 1 and n_mod_100 != 11:
        return PluralForm.ONE
    elif 2 <= n_mod_10 <= 4 and not (12 <= n_mod_100 <= 14):
        return PluralForm.FEW
    else:
        return PluralForm.MANY


def arabic_plural(n: int) -> PluralForm:
    """Arabic plural rule."""
    if n == 0:
        return PluralForm.ZERO
    elif n == 1:
        return PluralForm.ONE
    elif n == 2:
        return PluralForm.TWO
    elif 3 <= n % 100 <= 10:
        return PluralForm.FEW
    elif 11 <= n % 100 <= 99:
        return PluralForm.MANY
    return PluralForm.OTHER


# ============================================================================
# DEFAULT LOCALES
# ============================================================================

DEFAULT_LOCALES = {
    "en": Locale(
        code="en",
        name="English",
        native_name="English",
        language="en",
        date_format="%m/%d/%Y",
        currency_code="USD",
        currency_symbol="$",
        plural_rule=english_plural
    ),
    "en-GB": Locale(
        code="en-GB",
        name="English (UK)",
        native_name="English (UK)",
        language="en",
        region="GB",
        date_format="%d/%m/%Y",
        currency_code="GBP",
        currency_symbol="£",
        plural_rule=english_plural
    ),
    "es": Locale(
        code="es",
        name="Spanish",
        native_name="Español",
        language="es",
        date_format="%d/%m/%Y",
        currency_code="EUR",
        currency_symbol="€",
        currency_position="after",
        plural_rule=english_plural
    ),
    "fr": Locale(
        code="fr",
        name="French",
        native_name="Français",
        language="fr",
        date_format="%d/%m/%Y",
        decimal_separator=",",
        thousands_separator=" ",
        currency_code="EUR",
        currency_symbol="€",
        currency_position="after",
        plural_rule=french_plural
    ),
    "de": Locale(
        code="de",
        name="German",
        native_name="Deutsch",
        language="de",
        date_format="%d.%m.%Y",
        decimal_separator=",",
        thousands_separator=".",
        currency_code="EUR",
        currency_symbol="€",
        currency_position="after",
        plural_rule=english_plural
    ),
    "ja": Locale(
        code="ja",
        name="Japanese",
        native_name="日本語",
        language="ja",
        date_format="%Y年%m月%d日",
        currency_code="JPY",
        currency_symbol="¥",
        plural_rule=lambda n: PluralForm.OTHER  # No plurals
    ),
    "zh": Locale(
        code="zh",
        name="Chinese",
        native_name="中文",
        language="zh",
        date_format="%Y年%m月%d日",
        currency_code="CNY",
        currency_symbol="¥",
        plural_rule=lambda n: PluralForm.OTHER
    ),
    "ar": Locale(
        code="ar",
        name="Arabic",
        native_name="العربية",
        language="ar",
        rtl=True,
        plural_rule=arabic_plural
    ),
    "ru": Locale(
        code="ru",
        name="Russian",
        native_name="Русский",
        language="ru",
        date_format="%d.%m.%Y",
        decimal_separator=",",
        thousands_separator=" ",
        currency_code="RUB",
        currency_symbol="₽",
        currency_position="after",
        plural_rule=russian_plural
    ),
}


# ============================================================================
# MAIN LOCALIZATION ENGINE
# ============================================================================

class LocalizationEngine:
    """
    Main localization engine.

    Features:
    - Translation lookup
    - Plural forms
    - Number formatting
    - Date/time formatting
    - Currency formatting

    "Ba'el communicates in all tongues." — Ba'el
    """

    def __init__(self, config: Optional[LocaleConfig] = None):
        """Initialize localization engine."""
        self.config = config or LocaleConfig()

        # Locales
        self._locales: Dict[str, Locale] = dict(DEFAULT_LOCALES)

        # Translations: locale -> key -> Translation
        self._translations: Dict[str, Dict[str, Translation]] = {}

        self._lock = threading.RLock()

        logger.info("LocalizationEngine initialized")

    # ========================================================================
    # LOCALE MANAGEMENT
    # ========================================================================

    def register_locale(self, locale: Locale) -> None:
        """Register a locale."""
        with self._lock:
            self._locales[locale.code] = locale

    def get_locale(self, code: str) -> Optional[Locale]:
        """Get a locale by code."""
        return self._locales.get(code)

    def list_locales(self) -> List[Locale]:
        """List all registered locales."""
        return list(self._locales.values())

    def set_current_locale(self, code: str) -> None:
        """Set the current locale for this context."""
        _current_locale.set(code)

    def get_current_locale(self) -> str:
        """Get the current locale code."""
        return _current_locale.get()

    def get_current_locale_info(self) -> Optional[Locale]:
        """Get the current locale info."""
        return self.get_locale(self.get_current_locale())

    # ========================================================================
    # TRANSLATION MANAGEMENT
    # ========================================================================

    def add_translation(
        self,
        key: str,
        value: str,
        locale: str,
        plurals: Optional[Dict[str, str]] = None,
        context: Optional[str] = None
    ) -> Translation:
        """Add a translation."""
        translation = Translation(
            key=key,
            value=value,
            locale=locale,
            plurals=plurals or {},
            context=context
        )

        with self._lock:
            if locale not in self._translations:
                self._translations[locale] = {}
            self._translations[locale][key] = translation

        return translation

    def add_translations(
        self,
        translations: Dict[str, str],
        locale: str
    ) -> None:
        """Add multiple translations."""
        for key, value in translations.items():
            self.add_translation(key, value, locale)

    def load_translations(
        self,
        data: Dict[str, Dict[str, str]]
    ) -> None:
        """Load translations from nested dict (locale -> key -> value)."""
        for locale, translations in data.items():
            self.add_translations(translations, locale)

    # ========================================================================
    # TRANSLATION LOOKUP
    # ========================================================================

    def translate(
        self,
        key: str,
        locale: Optional[str] = None,
        count: Optional[int] = None,
        **kwargs
    ) -> str:
        """
        Translate a key.

        Args:
            key: Translation key
            locale: Locale code (uses current if None)
            count: Count for pluralization
            **kwargs: Variables for interpolation

        Returns:
            Translated string
        """
        locale = locale or self.get_current_locale()

        # Get translation
        translation = self._get_translation(key, locale)

        if not translation:
            # Try fallback locale
            if locale != self.config.fallback_locale:
                translation = self._get_translation(key, self.config.fallback_locale)

        if not translation:
            # Return key as fallback
            return key

        # Get value (with plural handling)
        if count is not None and translation.plurals:
            value = self._get_plural_value(translation, count, locale)
        else:
            value = translation.value

        # Interpolate
        if kwargs:
            value = self._interpolate(value, kwargs)

        return value

    def _get_translation(self, key: str, locale: str) -> Optional[Translation]:
        """Get translation for key and locale."""
        with self._lock:
            locale_translations = self._translations.get(locale, {})
            return locale_translations.get(key)

    def _get_plural_value(
        self,
        translation: Translation,
        count: int,
        locale: str
    ) -> str:
        """Get plural form value."""
        locale_info = self.get_locale(locale)

        if locale_info and locale_info.plural_rule:
            form = locale_info.plural_rule(count)
        else:
            form = english_plural(count)

        if form.value in translation.plurals:
            return translation.plurals[form.value]
        elif 'other' in translation.plurals:
            return translation.plurals['other']
        else:
            return translation.value

    def _interpolate(self, template: str, values: Dict[str, Any]) -> str:
        """Interpolate variables into template."""
        result = template

        for key, value in values.items():
            # Support both {key} and {{key}} formats
            result = result.replace(f'{{{key}}}', str(value))
            result = result.replace(f'{{{{ {key} }}}}', str(value))

        return result

    # ========================================================================
    # FORMATTING
    # ========================================================================

    def format_number(
        self,
        value: Union[int, float, Decimal],
        locale: Optional[str] = None,
        decimal_places: Optional[int] = None
    ) -> str:
        """Format a number according to locale."""
        locale = locale or self.get_current_locale()
        locale_info = self.get_locale(locale) or self.get_locale('en')

        # Format number
        if decimal_places is not None:
            formatted = f"{value:,.{decimal_places}f}"
        elif isinstance(value, float):
            formatted = f"{value:,.2f}"
        else:
            formatted = f"{value:,}"

        # Replace separators
        if locale_info:
            formatted = formatted.replace(',', 'THOU')
            formatted = formatted.replace('.', locale_info.decimal_separator)
            formatted = formatted.replace('THOU', locale_info.thousands_separator)

        return formatted

    def format_currency(
        self,
        value: Union[int, float, Decimal],
        locale: Optional[str] = None,
        currency: Optional[str] = None
    ) -> str:
        """Format a currency value."""
        locale = locale or self.get_current_locale()
        locale_info = self.get_locale(locale) or self.get_locale('en')

        formatted_number = self.format_number(value, locale, decimal_places=2)

        symbol = locale_info.currency_symbol if locale_info else '$'

        if locale_info and locale_info.currency_position == "after":
            return f"{formatted_number} {symbol}"
        else:
            return f"{symbol}{formatted_number}"

    def format_date(
        self,
        value: Union[date, datetime],
        locale: Optional[str] = None,
        format_str: Optional[str] = None
    ) -> str:
        """Format a date."""
        locale = locale or self.get_current_locale()
        locale_info = self.get_locale(locale) or self.get_locale('en')

        format_str = format_str or (locale_info.date_format if locale_info else "%Y-%m-%d")

        return value.strftime(format_str)

    def format_datetime(
        self,
        value: datetime,
        locale: Optional[str] = None,
        format_str: Optional[str] = None
    ) -> str:
        """Format a datetime."""
        locale = locale or self.get_current_locale()
        locale_info = self.get_locale(locale) or self.get_locale('en')

        format_str = format_str or (locale_info.datetime_format if locale_info else "%Y-%m-%d %H:%M:%S")

        return value.strftime(format_str)

    def format_time(
        self,
        value: datetime,
        locale: Optional[str] = None,
        format_str: Optional[str] = None
    ) -> str:
        """Format a time."""
        locale = locale or self.get_current_locale()
        locale_info = self.get_locale(locale) or self.get_locale('en')

        format_str = format_str or (locale_info.time_format if locale_info else "%H:%M:%S")

        return value.strftime(format_str)

    # ========================================================================
    # STATUS
    # ========================================================================

    def get_status(self) -> Dict[str, Any]:
        """Get engine status."""
        with self._lock:
            translation_counts = {
                locale: len(translations)
                for locale, translations in self._translations.items()
            }

        return {
            'current_locale': self.get_current_locale(),
            'default_locale': self.config.default_locale,
            'locales': len(self._locales),
            'translations': translation_counts
        }


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

localization_engine = LocalizationEngine()


def t(key: str, **kwargs) -> str:
    """Shorthand for translate."""
    return localization_engine.translate(key, **kwargs)


def set_locale(code: str) -> None:
    """Set current locale."""
    localization_engine.set_current_locale(code)


def get_locale() -> str:
    """Get current locale."""
    return localization_engine.get_current_locale()

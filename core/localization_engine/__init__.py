"""
BAEL Localization Engine
=========================

Internationalization and translation support.

"Ba'el speaks all languages of mortals." — Ba'el
"""

from .localization_engine import (
    # Enums
    PluralForm,

    # Data structures
    Locale,
    Translation,
    LocaleConfig,

    # Engine
    LocalizationEngine,

    # Functions
    t,
    set_locale,
    get_locale,

    # Instance
    localization_engine,
)

__all__ = [
    # Enums
    "PluralForm",

    # Data structures
    "Locale",
    "Translation",
    "LocaleConfig",

    # Engine
    "LocalizationEngine",

    # Functions
    "t",
    "set_locale",
    "get_locale",

    # Instance
    "localization_engine",
]

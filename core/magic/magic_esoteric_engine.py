"""
BAEL - Magic & Esoteric Engine
===============================

HARNESS THE HIDDEN FORCES. COMMAND THE UNSEEN.

This engine provides:
- Complete magical traditions library
- Ritual construction and execution
- Symbol power activation
- Energy manipulation
- Correspondences and timing
- Sigil creation
- Invocation patterns
- Sacred geometry
- Planetary magic
- Elemental commands

"Magic is the science of the future, viewed from the past."
"""

import asyncio
import hashlib
import json
import logging
import math
import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("BAEL.MAGIC")


class MagicalTradition(Enum):
    """Magical traditions."""
    HERMETIC = "hermetic"
    KABBALISTIC = "kabbalistic"
    ENOCHIAN = "enochian"
    GOETIC = "goetic"
    CHAOS = "chaos"
    THELEMIC = "thelemic"
    WICCAN = "wiccan"
    CEREMONIAL = "ceremonial"
    SHAMANIC = "shamanic"
    TANTRA = "tantra"
    VOODOO = "voodoo"
    RUNIC = "runic"
    ELEMENTAL = "elemental"
    PLANETARY = "planetary"
    FOLK = "folk"


class Element(Enum):
    """Classical elements."""
    FIRE = "fire"
    WATER = "water"
    AIR = "air"
    EARTH = "earth"
    SPIRIT = "spirit"
    AETHER = "aether"


class Planet(Enum):
    """Planetary correspondences."""
    SUN = "sun"
    MOON = "moon"
    MERCURY = "mercury"
    VENUS = "venus"
    MARS = "mars"
    JUPITER = "jupiter"
    SATURN = "saturn"
    URANUS = "uranus"
    NEPTUNE = "neptune"
    PLUTO = "pluto"


class ZodiacSign(Enum):
    """Zodiac signs."""
    ARIES = "aries"
    TAURUS = "taurus"
    GEMINI = "gemini"
    CANCER = "cancer"
    LEO = "leo"
    VIRGO = "virgo"
    LIBRA = "libra"
    SCORPIO = "scorpio"
    SAGITTARIUS = "sagittarius"
    CAPRICORN = "capricorn"
    AQUARIUS = "aquarius"
    PISCES = "pisces"


class MagicalIntent(Enum):
    """Types of magical intent."""
    PROTECTION = "protection"
    PROSPERITY = "prosperity"
    LOVE = "love"
    HEALING = "healing"
    KNOWLEDGE = "knowledge"
    POWER = "power"
    BANISHMENT = "banishment"
    BINDING = "binding"
    DIVINATION = "divination"
    MANIFESTATION = "manifestation"
    TRANSFORMATION = "transformation"
    COMMUNICATION = "communication"
    INVOCATION = "invocation"
    EVOCATION = "evocation"


class RitualPhase(Enum):
    """Phases of ritual work."""
    PREPARATION = "preparation"
    PURIFICATION = "purification"
    CONSECRATION = "consecration"
    INVOCATION = "invocation"
    MAIN_WORKING = "main_working"
    CHARGING = "charging"
    RELEASE = "release"
    GROUNDING = "grounding"
    CLOSING = "closing"


class SacredGeometry(Enum):
    """Sacred geometry patterns."""
    CIRCLE = "circle"
    TRIANGLE = "triangle"
    SQUARE = "square"
    PENTAGON = "pentagon"
    HEXAGON = "hexagon"
    HEPTAGON = "heptagon"
    OCTAGON = "octagon"
    VESICA_PISCIS = "vesica_piscis"
    FLOWER_OF_LIFE = "flower_of_life"
    SEED_OF_LIFE = "seed_of_life"
    METATRONS_CUBE = "metatrons_cube"
    SRI_YANTRA = "sri_yantra"
    MERKABA = "merkaba"
    TORUS = "torus"
    GOLDEN_SPIRAL = "golden_spiral"


class MoonPhase(Enum):
    """Moon phases."""
    NEW_MOON = "new_moon"
    WAXING_CRESCENT = "waxing_crescent"
    FIRST_QUARTER = "first_quarter"
    WAXING_GIBBOUS = "waxing_gibbous"
    FULL_MOON = "full_moon"
    WANING_GIBBOUS = "waning_gibbous"
    LAST_QUARTER = "last_quarter"
    WANING_CRESCENT = "waning_crescent"


@dataclass
class MagicalCorrespondence:
    """Magical correspondences."""
    id: str
    name: str
    element: Element
    planet: Planet
    zodiac: Optional[ZodiacSign]
    day: str
    hour: int
    colors: List[str]
    metals: List[str]
    stones: List[str]
    herbs: List[str]
    number: int
    intent: List[MagicalIntent]


@dataclass
class MagicalSymbol:
    """A magical symbol."""
    id: str
    name: str
    tradition: MagicalTradition
    geometry: SacredGeometry
    meaning: str
    power: str
    activation_method: str
    properties: Dict[str, Any]


@dataclass
class Ritual:
    """A magical ritual."""
    id: str
    name: str
    tradition: MagicalTradition
    intent: MagicalIntent
    phases: List[Dict[str, Any]]
    correspondences: MagicalCorrespondence
    timing: Dict[str, Any]
    components: List[str]
    invocations: List[str]
    expected_result: str
    power_level: int


@dataclass
class Sigil:
    """A magical sigil."""
    id: str
    statement_of_intent: str
    letters_extracted: str
    design_method: str
    charging_method: str
    activation_state: bool


@dataclass
class EnergyWorking:
    """An energy manipulation working."""
    id: str
    name: str
    energy_type: str
    direction: str  # invoke, evoke, circulate, ground
    visualization: str
    duration_seconds: float
    intensity: float


class MagicEsotericEngine:
    """
    Engine for magical and esoteric operations.

    Features:
    - Multiple traditions
    - Correspondence tables
    - Ritual construction
    - Sigil generation
    - Timing calculations
    - Energy workings
    """

    def __init__(self):
        self.correspondences: Dict[str, MagicalCorrespondence] = {}
        self.symbols: Dict[str, MagicalSymbol] = {}
        self.rituals: Dict[str, Ritual] = {}
        self.sigils: Dict[str, Sigil] = {}
        self.energy_workings: Dict[str, EnergyWorking] = {}

        self._init_planetary_correspondences()
        self._init_elemental_correspondences()
        self._init_symbols()
        self._init_standard_rituals()

        logger.info("MagicEsotericEngine initialized - powers awakened")

    def _init_planetary_correspondences(self):
        """Initialize planetary correspondences."""
        planetary_data = [
            ("Sun", Element.FIRE, Planet.SUN, "Sunday", 1,
             ["gold", "yellow", "orange"], ["gold"], ["amber", "topaz", "diamond"],
             ["frankincense", "cinnamon", "bay"], 6, [MagicalIntent.POWER, MagicalIntent.HEALING]),
            ("Moon", Element.WATER, Planet.MOON, "Monday", 9,
             ["silver", "white", "violet"], ["silver"], ["moonstone", "pearl", "quartz"],
             ["jasmine", "lotus", "camphor"], 9, [MagicalIntent.DIVINATION, MagicalIntent.PROTECTION]),
            ("Mercury", Element.AIR, Planet.MERCURY, "Wednesday", 8,
             ["orange", "purple"], ["mercury", "aluminum"], ["agate", "opal"],
             ["lavender", "marjoram"], 8, [MagicalIntent.KNOWLEDGE, MagicalIntent.COMMUNICATION]),
            ("Venus", Element.WATER, Planet.VENUS, "Friday", 7,
             ["green", "pink", "turquoise"], ["copper"], ["emerald", "rose quartz"],
             ["rose", "myrtle", "vanilla"], 7, [MagicalIntent.LOVE, MagicalIntent.PROSPERITY]),
            ("Mars", Element.FIRE, Planet.MARS, "Tuesday", 5,
             ["red", "scarlet"], ["iron"], ["ruby", "garnet", "bloodstone"],
             ["dragon's blood", "tobacco", "nettle"], 5, [MagicalIntent.POWER, MagicalIntent.PROTECTION]),
            ("Jupiter", Element.FIRE, Planet.JUPITER, "Thursday", 4,
             ["blue", "purple", "royal blue"], ["tin"], ["sapphire", "amethyst", "lapis"],
             ["cedar", "sage", "nutmeg"], 4, [MagicalIntent.PROSPERITY, MagicalIntent.MANIFESTATION]),
            ("Saturn", Element.EARTH, Planet.SATURN, "Saturday", 3,
             ["black", "dark brown", "indigo"], ["lead"], ["onyx", "obsidian", "jet"],
             ["myrrh", "cypress", "patchouli"], 3, [MagicalIntent.BANISHMENT, MagicalIntent.BINDING]),
        ]

        for name, elem, planet, day, hour, colors, metals, stones, herbs, num, intents in planetary_data:
            corr = MagicalCorrespondence(
                id=self._gen_id("corr"),
                name=name,
                element=elem,
                planet=planet,
                zodiac=None,
                day=day,
                hour=hour,
                colors=colors,
                metals=metals,
                stones=stones,
                herbs=herbs,
                number=num,
                intent=intents
            )
            self.correspondences[name] = corr

    def _init_elemental_correspondences(self):
        """Initialize elemental correspondences."""
        elemental_data = [
            ("Fire", Element.FIRE, ["red", "orange", "gold"],
             ["salamanders"], ["south"], ["wand", "sword"],
             [MagicalIntent.POWER, MagicalIntent.TRANSFORMATION]),
            ("Water", Element.WATER, ["blue", "silver", "teal"],
             ["undines"], ["west"], ["cup", "chalice"],
             [MagicalIntent.HEALING, MagicalIntent.LOVE, MagicalIntent.DIVINATION]),
            ("Air", Element.AIR, ["yellow", "white", "violet"],
             ["sylphs"], ["east"], ["sword", "athame"],
             [MagicalIntent.KNOWLEDGE, MagicalIntent.COMMUNICATION]),
            ("Earth", Element.EARTH, ["green", "brown", "black"],
             ["gnomes"], ["north"], ["pentacle", "stone"],
             [MagicalIntent.PROSPERITY, MagicalIntent.PROTECTION, MagicalIntent.MANIFESTATION]),
        ]

        for name, elem, colors, spirits, direction, tools, intents in elemental_data:
            corr = MagicalCorrespondence(
                id=self._gen_id("corr"),
                name=f"Elemental_{name}",
                element=elem,
                planet=Planet.EARTH if elem == Element.EARTH else Planet.SUN,
                zodiac=None,
                day="Any",
                hour=0,
                colors=colors,
                metals=[],
                stones=[],
                herbs=[],
                number=4,
                intent=intents
            )
            self.correspondences[f"Elemental_{name}"] = corr

    def _init_symbols(self):
        """Initialize magical symbols."""
        symbols_data = [
            ("Pentagram", MagicalTradition.CEREMONIAL, SacredGeometry.PENTAGON,
             "Five elements unified", "Protection and invocation", "trace in air"),
            ("Hexagram", MagicalTradition.KABBALISTIC, SacredGeometry.HEXAGON,
             "As above, so below", "Planetary magic", "ceremonial tracing"),
            ("Sigil of Solomon", MagicalTradition.GOETIC, SacredGeometry.HEXAGON,
             "Divine authority", "Spirit binding", "consecration"),
            ("Flower of Life", MagicalTradition.HERMETIC, SacredGeometry.FLOWER_OF_LIFE,
             "Creation pattern", "Harmony and connection", "meditation"),
            ("Merkaba", MagicalTradition.KABBALISTIC, SacredGeometry.MERKABA,
             "Vehicle of light", "Dimensional travel", "visualization"),
            ("Sri Yantra", MagicalTradition.TANTRA, SacredGeometry.SRI_YANTRA,
             "Supreme form", "Manifestation", "concentration"),
            ("Veve", MagicalTradition.VOODOO, SacredGeometry.CIRCLE,
             "Spirit doorway", "Spirit contact", "drawing and offering"),
            ("Bindrune", MagicalTradition.RUNIC, SacredGeometry.TRIANGLE,
             "Combined power", "Specific intent", "carving and charging"),
        ]

        for name, trad, geom, meaning, power, activation in symbols_data:
            symbol = MagicalSymbol(
                id=self._gen_id("sym"),
                name=name,
                tradition=trad,
                geometry=geom,
                meaning=meaning,
                power=power,
                activation_method=activation,
                properties={}
            )
            self.symbols[name] = symbol

    def _init_standard_rituals(self):
        """Initialize standard ritual templates."""
        rituals_data = [
            ("Lesser Banishing Ritual of the Pentagram", MagicalTradition.CEREMONIAL,
             MagicalIntent.BANISHMENT,
             ["Qabalistic Cross", "Pentagrams", "Invocation of Archangels", "Qabalistic Cross"],
             "Clear negative energies, establish sacred space", 5),
            ("Middle Pillar", MagicalTradition.KABBALISTIC,
             MagicalIntent.POWER,
             ["Ground", "Kether visualization", "Descent through spheres", "Circulation"],
             "Energy enhancement and balance", 6),
            ("Calling the Quarters", MagicalTradition.WICCAN,
             MagicalIntent.INVOCATION,
             ["Cast circle", "Invoke East", "Invoke South", "Invoke West", "Invoke North", "Close"],
             "Establish sacred space with elemental guardians", 4),
            ("Sigil Charging", MagicalTradition.CHAOS,
             MagicalIntent.MANIFESTATION,
             ["Create sigil", "Gnosis", "Charge", "Forget"],
             "Manifest specific intent", 7),
            ("Planetary Hour Working", MagicalTradition.PLANETARY,
             MagicalIntent.MANIFESTATION,
             ["Calculate hour", "Prepare correspondences", "Invoke planet", "Statement", "License to depart"],
             "Work with planetary energies", 6),
        ]

        for name, trad, intent, phases, result, power in rituals_data:
            ritual = Ritual(
                id=self._gen_id("rit"),
                name=name,
                tradition=trad,
                intent=intent,
                phases=[{"phase": p, "order": i} for i, p in enumerate(phases)],
                correspondences=list(self.correspondences.values())[0],
                timing={},
                components=[],
                invocations=[],
                expected_result=result,
                power_level=power
            )
            self.rituals[name] = ritual

    # -------------------------------------------------------------------------
    # SIGIL MAGIC
    # -------------------------------------------------------------------------

    async def create_sigil(
        self,
        statement_of_intent: str,
        method: str = "letter_reduction"
    ) -> Sigil:
        """Create a sigil from statement of intent."""
        # Remove vowels and repeating letters
        statement_clean = statement_of_intent.upper()
        statement_clean = ''.join([c for c in statement_clean if c.isalpha()])

        # Remove vowels
        vowels = "AEIOU"
        letters = [c for c in statement_clean if c not in vowels]

        # Remove duplicates while preserving order
        seen = set()
        unique_letters = []
        for c in letters:
            if c not in seen:
                seen.add(c)
                unique_letters.append(c)

        letters_extracted = ''.join(unique_letters)

        sigil = Sigil(
            id=self._gen_id("sigil"),
            statement_of_intent=statement_of_intent,
            letters_extracted=letters_extracted,
            design_method=method,
            charging_method="gnosis",
            activation_state=False
        )

        self.sigils[sigil.id] = sigil
        return sigil

    async def charge_sigil(
        self,
        sigil_id: str,
        method: str = "gnosis"
    ) -> Dict[str, Any]:
        """Charge a sigil."""
        sigil = self.sigils.get(sigil_id)
        if not sigil:
            return {"success": False, "reason": "Sigil not found"}

        sigil.charging_method = method
        sigil.activation_state = True

        return {
            "success": True,
            "sigil_id": sigil_id,
            "method": method,
            "state": "activated"
        }

    # -------------------------------------------------------------------------
    # TIMING
    # -------------------------------------------------------------------------

    def calculate_planetary_hour(
        self,
        target_planet: Planet,
        date: datetime = None
    ) -> Dict[str, Any]:
        """Calculate when the next planetary hour occurs."""
        if date is None:
            date = datetime.now()

        # Simplified planetary hour calculation
        day_rulers = [Planet.SUN, Planet.MOON, Planet.MARS, Planet.MERCURY,
                     Planet.JUPITER, Planet.VENUS, Planet.SATURN]

        day_of_week = date.weekday()  # 0=Monday
        # Chaldean order
        chaldean = [Planet.SATURN, Planet.JUPITER, Planet.MARS, Planet.SUN,
                   Planet.VENUS, Planet.MERCURY, Planet.MOON]

        # Find current hour ruler
        current_hour = date.hour

        return {
            "target_planet": target_planet.value,
            "current_day_ruler": day_rulers[(day_of_week + 1) % 7].value,
            "suggested_hour": (chaldean.index(target_planet) + 1) % 24,
            "date": date.isoformat()
        }

    def get_moon_phase(self, date: datetime = None) -> MoonPhase:
        """Get current moon phase."""
        if date is None:
            date = datetime.now()

        # Simplified moon phase calculation
        # Synodic month ≈ 29.53 days
        known_new_moon = datetime(2024, 1, 11)  # Known new moon date
        days_since = (date - known_new_moon).days
        phase_progress = (days_since % 29.53) / 29.53

        if phase_progress < 0.0625:
            return MoonPhase.NEW_MOON
        elif phase_progress < 0.1875:
            return MoonPhase.WAXING_CRESCENT
        elif phase_progress < 0.3125:
            return MoonPhase.FIRST_QUARTER
        elif phase_progress < 0.4375:
            return MoonPhase.WAXING_GIBBOUS
        elif phase_progress < 0.5625:
            return MoonPhase.FULL_MOON
        elif phase_progress < 0.6875:
            return MoonPhase.WANING_GIBBOUS
        elif phase_progress < 0.8125:
            return MoonPhase.LAST_QUARTER
        else:
            return MoonPhase.WANING_CRESCENT

    def get_optimal_timing(
        self,
        intent: MagicalIntent
    ) -> Dict[str, Any]:
        """Get optimal timing for magical intent."""
        # Intent to planet mapping
        intent_planets = {
            MagicalIntent.PROTECTION: Planet.MARS,
            MagicalIntent.PROSPERITY: Planet.JUPITER,
            MagicalIntent.LOVE: Planet.VENUS,
            MagicalIntent.HEALING: Planet.SUN,
            MagicalIntent.KNOWLEDGE: Planet.MERCURY,
            MagicalIntent.POWER: Planet.SUN,
            MagicalIntent.BANISHMENT: Planet.SATURN,
            MagicalIntent.BINDING: Planet.SATURN,
            MagicalIntent.DIVINATION: Planet.MOON,
            MagicalIntent.MANIFESTATION: Planet.JUPITER,
        }

        planet = intent_planets.get(intent, Planet.SUN)
        moon_phase = self.get_moon_phase()
        planetary_hour = self.calculate_planetary_hour(planet)

        # Moon phase recommendations
        waxing_intents = [MagicalIntent.PROSPERITY, MagicalIntent.LOVE, MagicalIntent.MANIFESTATION]
        waning_intents = [MagicalIntent.BANISHMENT, MagicalIntent.BINDING]

        if intent in waxing_intents:
            moon_rec = "Waxing moon preferred"
        elif intent in waning_intents:
            moon_rec = "Waning moon preferred"
        else:
            moon_rec = "Any moon phase"

        return {
            "intent": intent.value,
            "optimal_planet": planet.value,
            "current_moon_phase": moon_phase.value,
            "moon_recommendation": moon_rec,
            "planetary_hour_info": planetary_hour
        }

    # -------------------------------------------------------------------------
    # CORRESPONDENCES
    # -------------------------------------------------------------------------

    def get_correspondence(
        self,
        planet: Optional[Planet] = None,
        element: Optional[Element] = None,
        intent: Optional[MagicalIntent] = None
    ) -> List[MagicalCorrespondence]:
        """Get correspondences matching criteria."""
        results = []

        for corr in self.correspondences.values():
            if planet and corr.planet != planet:
                continue
            if element and corr.element != element:
                continue
            if intent and intent not in corr.intent:
                continue
            results.append(corr)

        return results

    # -------------------------------------------------------------------------
    # STATISTICS
    # -------------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics."""
        return {
            "correspondences": len(self.correspondences),
            "symbols": len(self.symbols),
            "rituals": len(self.rituals),
            "sigils": len(self.sigils),
            "traditions": len(MagicalTradition),
            "intents": len(MagicalIntent)
        }

    def _gen_id(self, prefix: str) -> str:
        """Generate unique ID."""
        return hashlib.md5(f"{prefix}{time.time()}{random.random()}".encode()).hexdigest()[:12]


# ============================================================================
# SINGLETON
# ============================================================================

_engine: Optional[MagicEsotericEngine] = None


def get_magic_engine() -> MagicEsotericEngine:
    """Get global magic engine."""
    global _engine
    if _engine is None:
        _engine = MagicEsotericEngine()
    return _engine


# ============================================================================
# DEMO
# ============================================================================

async def demo():
    """Demonstrate magic engine."""
    print("=" * 60)
    print("🔮 MAGIC & ESOTERIC ENGINE 🔮")
    print("=" * 60)

    engine = get_magic_engine()

    # Stats
    print("\n--- Engine Statistics ---")
    stats = engine.get_stats()
    print(f"Correspondences: {stats['correspondences']}")
    print(f"Symbols: {stats['symbols']}")
    print(f"Rituals: {stats['rituals']}")
    print(f"Traditions: {stats['traditions']}")

    # Moon phase
    print("\n--- Current Moon Phase ---")
    moon = engine.get_moon_phase()
    print(f"  {moon.value}")

    # Create sigil
    print("\n--- Sigil Creation ---")
    sigil = await engine.create_sigil("I will achieve absolute power")
    print(f"  Statement: {sigil.statement_of_intent}")
    print(f"  Letters: {sigil.letters_extracted}")

    # Timing
    print("\n--- Optimal Timing ---")
    timing = engine.get_optimal_timing(MagicalIntent.POWER)
    print(f"  Intent: {timing['intent']}")
    print(f"  Planet: {timing['optimal_planet']}")
    print(f"  Moon: {timing['moon_recommendation']}")

    # Correspondences
    print("\n--- Planetary Correspondences ---")
    for name in ["Sun", "Moon", "Mars"]:
        corr = engine.correspondences.get(name)
        if corr:
            print(f"  {name}: {corr.day}, Colors: {', '.join(corr.colors[:2])}")

    # Symbols
    print("\n--- Magical Symbols ---")
    for name, symbol in list(engine.symbols.items())[:3]:
        print(f"  ✡ {name}: {symbol.power}")

    # Rituals
    print("\n--- Available Rituals ---")
    for name, ritual in list(engine.rituals.items())[:3]:
        print(f"  📿 {name}")
        print(f"      Intent: {ritual.intent.value}")

    print("\n" + "=" * 60)
    print("🔮 MAGICAL POWERS AWAKENED 🔮")


if __name__ == "__main__":
    asyncio.run(demo())

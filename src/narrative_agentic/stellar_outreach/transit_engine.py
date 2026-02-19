"""
NEXUS STATION - Stellar Outreach: Daily Transit Calculation Engine (TASK-002)

Calculates daily planetary transits and overlays them against a player's
natal chart to produce personalized Cosmic Briefings.

The transit snapshot (current sky) is universal — the same for all players.
The overlay (aspect hits, module statuses, briefing text) is personalized
per player based on their natal chart from the Birth Chart Engine (TASK-001).

References:
    - GDD §7.2: Aspect definitions and game effects
    - GDD §7.3: Planet-to-module mapping

Security Note (Article II / Kai Chen review):
    This module reads natal chart data from PlayerProfile objects but does
    not store, transmit, or log any personally identifiable birth data.
"""

from __future__ import annotations

import hashlib
import math
import random
from dataclasses import dataclass, field
from datetime import date, datetime, time
from typing import Dict, List, Optional, Tuple

import swisseph as swe

from narrative_agentic.stellar_outreach.birth_chart import (
    PLANET_IDS,
    PlayerProfile,
    PlanetPosition,
    _sign_from_longitude,
    _sign_degree,
    _to_julian_day,
)


# ────────────────────────────────────────────────────────────────
# Constants
# ────────────────────────────────────────────────────────────────

# Aspect definitions: (name, target_angle, status, orb, strength_tier)
# Strength tiers: "strong", "moderate", "mild"
ASPECT_DEFINITIONS: List[Tuple[str, float, str, float, str]] = [
    ("Conjunction",     0.0,   "PRESSURE", 6.0, "strong"),
    ("Semi-sextile",    30.0,  "POWER",    3.0, "mild"),
    ("Semi-square",     45.0,  "TROUBLE",  3.0, "moderate"),
    ("Sextile",         60.0,  "POWER",    6.0, "moderate"),
    ("Square",          90.0,  "TROUBLE",  6.0, "strong"),
    ("Trine",           120.0, "POWER",    6.0, "strong"),
    ("Sesquiquadrate",  135.0, "TROUBLE",  3.0, "mild"),
    ("Quincunx",        150.0, "PRESSURE", 3.0, "moderate"),
    ("Opposition",      180.0, "PRESSURE", 6.0, "strong"),
]

# Buff/debuff percentage ranges by strength tier
BUFF_RANGES: Dict[str, Tuple[int, int]] = {
    "strong":   (20, 25),
    "moderate": (10, 15),
    "mild":     (5, 5),
}

# Planet-to-Module mapping (GDD §7.3)
PLANET_MODULE_MAP: Dict[str, Tuple[str, str]] = {
    "Mercury": ("Observatory",  "Thinking & Creativity"),
    "Venus":   ("Greenhouse",   "Sex & Love"),
    "Mars":    ("Workshop",     "Energy & Drive"),
    "Jupiter": ("Commons",      "Expansion & Luck"),
    "Saturn":  ("Quarters",     "Routine"),
    "Moon":    ("Bridge",       "Emotions & Instincts"),
    "Sun":     ("Shrine",       "Purpose & Vitality"),
}

# Generational planets — affect modules based on natal house
GENERATIONAL_PLANETS = {"Uranus", "Neptune", "Pluto"}

# House-to-module fallback for generational planets
HOUSE_MODULE_MAP: Dict[int, str] = {
    1:  "Shrine",       # Self / identity
    2:  "Commons",      # Resources
    3:  "Observatory",  # Communication
    4:  "Quarters",     # Home / routine
    5:  "Greenhouse",   # Pleasure / creativity
    6:  "Workshop",     # Work / service
    7:  "Greenhouse",   # Partnerships
    8:  "Observatory",  # Transformation / research
    9:  "Commons",      # Exploration
    10: "Workshop",     # Career / ambition
    11: "Commons",      # Community
    12: "Bridge",       # Subconscious / intuition
}

# Status symbols for briefing text
STATUS_SYMBOLS: Dict[str, str] = {
    "POWER":    "★",
    "TROUBLE":  "✕",
    "PRESSURE": "▲",
    "NEUTRAL":  "○",
}

# Module names list (the 7 station modules)
MODULE_NAMES = ["Observatory", "Greenhouse", "Workshop", "Commons",
                "Quarters", "Bridge", "Shrine"]

# Co-Star category lookup for modules
MODULE_CATEGORIES: Dict[str, str] = {
    "Observatory":  "Thinking & Creativity",
    "Greenhouse":   "Sex & Love",
    "Workshop":     "Energy & Drive",
    "Commons":      "Expansion & Luck",
    "Quarters":     "Routine",
    "Bridge":       "Emotions & Instincts",
    "Shrine":       "Purpose & Vitality",
}


# ────────────────────────────────────────────────────────────────
# Daily Dispatch Messages
# ────────────────────────────────────────────────────────────────

DISPATCH_POSITIVE = [
    "your systems are humming. trust the momentum.",
    "the stars are whispering coordinates. follow them.",
    "today the universe opens a door it usually keeps locked.",
    "something good is docking at your station. let it in.",
    "you have been cleared for launch. don't overthink the trajectory.",
    "the cosmos is handing you a gift. no strings attached.",
    "your orbit is aligned. today, you move with gravity, not against it.",
]

DISPATCH_CHALLENGING = [
    "the universe is stress-testing your wiring. hold steady.",
    "the stars aren't against you. they just have better things to do today.",
    "some turbulence ahead. tighten your harness and breathe.",
    "today is a systems check. everything that rattles needed tightening anyway.",
    "the cosmos is recalibrating. you might feel it in your bones.",
    "not every day is a launch day. some days are maintenance.",
    "pressure builds diamonds and also headaches. choose wisely.",
]

DISPATCH_PRESSURE = [
    "tension is just potential waiting for direction.",
    "the universe is asking you a question. you don't have to answer today.",
    "something is shifting. you can fight the current or learn to swim in it.",
    "today pulls you in two directions. the answer is probably neither.",
    "the stars are arguing about you. take it as a compliment.",
    "you are standing at a crossroads that the cosmos built overnight.",
    "the signal is mixed. trust the static between the stations.",
]

DISPATCH_NEUTRAL = [
    "the cosmos is quiet today. make your own weather.",
    "no major transmissions from the stars. a good day to explore inward.",
    "the universe has no notes for you today. carry on.",
    "a still sky is not an empty one. sometimes silence is the message.",
    "the celestial switchboard is quiet. enjoy the calm.",
    "nothing is pushing or pulling. today you are weightless.",
]


# ────────────────────────────────────────────────────────────────
# Data Classes
# ────────────────────────────────────────────────────────────────

@dataclass
class TransitPlanetPosition:
    """Position of a single planet in the current transit sky."""
    planet: str
    sign: str
    degree: float           # 0-360 ecliptic longitude
    sign_degree: float      # 0-30 degree within the sign
    retrograde: bool


@dataclass
class TransitSnapshot:
    """Daily transit snapshot — the real sky for a given date.

    This is universal (the same for every player).
    """
    date: str                                   # ISO date string
    planets: List[TransitPlanetPosition]


@dataclass
class AspectHit:
    """A detected aspect between a transiting planet and a natal planet."""
    transit_planet: str
    natal_planet: str
    aspect_type: str        # e.g. "Trine", "Square"
    angle: float            # actual angle between the two
    orb: float              # how far from exact (degrees)
    status: str             # POWER / TROUBLE / PRESSURE
    strength: str           # strong / moderate / mild
    buff_percentage: int    # signed: positive = buff, negative = debuff


@dataclass
class ModuleStatus:
    """Status of a single station module for the day."""
    module_name: str
    co_star_category: str
    status: str             # POWER / TROUBLE / PRESSURE / NEUTRAL
    buff_percentage: int    # net buff (positive) or debuff (negative)
    aspects: List[AspectHit]
    description: str        # generated briefing line


@dataclass
class CosmicBriefing:
    """Complete personalized cosmic briefing for a player on a given date."""
    date: str
    player_id: str          # "universal" for snapshot-only
    module_statuses: List[ModuleStatus]
    briefing_text: str
    daily_dispatch: str
    is_cached: bool = False


# ────────────────────────────────────────────────────────────────
# Internal Helpers
# ────────────────────────────────────────────────────────────────

def _normalize_angle(angle: float) -> float:
    """Normalize an angle difference to [0, 180]."""
    diff = abs(angle) % 360.0
    if diff > 180.0:
        diff = 360.0 - diff
    return diff


def _date_to_jd(date_str: Optional[str] = None) -> Tuple[float, str]:
    """Convert a date string (YYYY-MM-DD) or today to Julian Day (noon UT).

    Returns (jd, iso_date_str).
    """
    if date_str:
        d = date.fromisoformat(date_str)
    else:
        d = date.today()

    jd = swe.julday(d.year, d.month, d.day, 12.0)  # noon UT
    return jd, d.isoformat()


def _calc_buff_percentage(status: str, strength: str) -> int:
    """Calculate buff/debuff percentage from status and strength tier.

    POWER  -> positive buff
    TROUBLE -> negative debuff
    PRESSURE -> can go either way, we use positive as intensity
    """
    low, high = BUFF_RANGES[strength]
    # Use midpoint for deterministic results
    value = (low + high) // 2

    if status == "TROUBLE":
        return -value
    # POWER and PRESSURE return positive values
    return value


def _detect_aspects(
    transit_planets: List[TransitPlanetPosition],
    natal_planets: List[PlanetPosition],
) -> List[AspectHit]:
    """Detect all aspects between transit and natal planets."""
    hits: List[AspectHit] = []

    for tp in transit_planets:
        for np in natal_planets:
            diff = _normalize_angle(tp.degree - np.degree)

            for asp_name, asp_angle, asp_status, asp_orb, asp_strength in ASPECT_DEFINITIONS:
                orb = abs(diff - asp_angle)
                if orb <= asp_orb:
                    buff = _calc_buff_percentage(asp_status, asp_strength)
                    hits.append(AspectHit(
                        transit_planet=tp.planet,
                        natal_planet=np.planet,
                        aspect_type=asp_name,
                        angle=round(diff, 2),
                        orb=round(orb, 2),
                        status=asp_status,
                        strength=asp_strength,
                        buff_percentage=buff,
                    ))
                    break  # only one aspect per planet pair

    return hits


def _resolve_module_for_aspect(aspect: AspectHit, natal_planets: List[PlanetPosition]) -> str:
    """Determine which module an aspect affects.

    Personal planets map directly via PLANET_MODULE_MAP.
    Generational planets (Uranus, Neptune, Pluto) map via the natal
    planet's house position using HOUSE_MODULE_MAP.
    """
    transit_name = aspect.transit_planet

    # Personal planet mapping takes priority
    if transit_name in PLANET_MODULE_MAP:
        return PLANET_MODULE_MAP[transit_name][0]

    # Generational planet — use natal planet's house
    if transit_name in GENERATIONAL_PLANETS:
        # Find the natal planet that was aspected
        for np in natal_planets:
            if np.planet == aspect.natal_planet:
                return HOUSE_MODULE_MAP.get(np.house, "Bridge")

    # Fallback
    return "Bridge"


def _aspect_description(aspect: AspectHit) -> str:
    """Generate a short poetic description for an aspect hit."""
    verb = aspect.aspect_type.lower()
    descriptions = {
        ("Mars", "POWER"):      "your research burns bright today",
        ("Mars", "TROUBLE"):    "restless energy rattles the hull",
        ("Mars", "PRESSURE"):   "a surge of intensity demands action",
        ("Venus", "POWER"):     "beauty finds you in unexpected places",
        ("Venus", "TROUBLE"):   "walls up, guard down",
        ("Venus", "PRESSURE"):  "desire and hesitation orbit each other",
        ("Mercury", "POWER"):   "thoughts crystallize into breakthroughs",
        ("Mercury", "TROUBLE"): "the gears grind between thought and speech",
        ("Mercury", "PRESSURE"): "messages arrive with double meanings",
        ("Jupiter", "POWER"):   "expansion flows through every corridor",
        ("Jupiter", "TROUBLE"): "too much of a good thing strains the system",
        ("Jupiter", "PRESSURE"): "opportunity knocks but the door is heavy",
        ("Saturn", "POWER"):    "discipline becomes your superpower",
        ("Saturn", "TROUBLE"):  "the weight of structure presses down",
        ("Saturn", "PRESSURE"): "boundaries test your patience",
        ("Moon", "POWER"):      "intuition guides your every move",
        ("Moon", "TROUBLE"):    "emotional static clouds the sensors",
        ("Moon", "PRESSURE"):   "feelings surge beneath the surface",
        ("Sun", "POWER"):       "your core identity radiates outward",
        ("Sun", "TROUBLE"):     "the light flickers — find your center",
        ("Sun", "PRESSURE"):    "purpose and doubt stand face to face",
        ("Uranus", "POWER"):    "a flash of innovation rewires the system",
        ("Uranus", "TROUBLE"):  "unexpected disruptions shake the station",
        ("Uranus", "PRESSURE"): "change arrives unannounced",
        ("Neptune", "POWER"):   "imagination paints new constellations",
        ("Neptune", "TROUBLE"): "illusions fog the viewport",
        ("Neptune", "PRESSURE"): "dreams and reality blur at the edges",
        ("Pluto", "POWER"):     "transformation runs deep and sure",
        ("Pluto", "TROUBLE"):   "buried tensions surface without warning",
        ("Pluto", "PRESSURE"):  "power shifts beneath the deck plates",
    }

    key = (aspect.transit_planet, aspect.status)
    desc = descriptions.get(key, f"{aspect.transit_planet.lower()} energy shifts the station")
    return f"{aspect.transit_planet} {verb} natal {aspect.natal_planet} — {desc}"


def _module_effect_text(module_status: ModuleStatus) -> str:
    """Generate the game-effect text line for a module."""
    if module_status.status == "NEUTRAL":
        return "No significant cosmic influence today"

    effects = []
    buff = module_status.buff_percentage

    effect_templates = {
        "Observatory": [
            f"Research speed {buff:+d}%",
            f"Crafting crit chance {buff:+d}%",
        ],
        "Greenhouse": [
            f"Crew relationship events {'trigger unexpectedly' if buff < 0 else 'bloom naturally'}",
            f"Social influence {buff:+d}%",
        ],
        "Workshop": [
            f"Construction efficiency {buff:+d}%",
            f"Combat readiness {buff:+d}%",
        ],
        "Commons": [
            f"Trade margins {buff:+d}%",
            f"Discovery chance {buff:+d}%",
        ],
        "Quarters": [
            f"Station maintenance costs {-buff:+d}%",
            f"Rest recovery {buff:+d}%",
        ],
        "Bridge": [
            f"Crew morale drift {buff:+d}%",
            f"Instinct accuracy {buff:+d}%",
        ],
        "Shrine": [
            f"XP gain {buff:+d}%",
            f"Leadership effectiveness {buff:+d}%",
        ],
    }

    templates = effect_templates.get(module_status.module_name, [f"Module efficiency {buff:+d}%"])
    return ", ".join(templates)


def _pick_dispatch(module_statuses: List[ModuleStatus]) -> str:
    """Select a daily dispatch message based on overall cosmic weather."""
    power_count = sum(1 for m in module_statuses if m.status == "POWER")
    trouble_count = sum(1 for m in module_statuses if m.status == "TROUBLE")
    pressure_count = sum(1 for m in module_statuses if m.status == "PRESSURE")

    # Determine overall mood
    if power_count == 0 and trouble_count == 0 and pressure_count == 0:
        pool = DISPATCH_NEUTRAL
    elif power_count >= trouble_count and power_count >= pressure_count:
        pool = DISPATCH_POSITIVE
    elif trouble_count >= power_count and trouble_count >= pressure_count:
        pool = DISPATCH_CHALLENGING
    else:
        pool = DISPATCH_PRESSURE

    # Deterministic-ish selection based on date
    today_str = date.today().isoformat()
    seed = int(hashlib.md5(today_str.encode()).hexdigest()[:8], 16)
    return pool[seed % len(pool)]


# ────────────────────────────────────────────────────────────────
# Public API
# ────────────────────────────────────────────────────────────────

def get_transit_snapshot(date_str: Optional[str] = None) -> TransitSnapshot:
    """Calculate today's (or a given date's) planetary positions.

    This is the universal sky — the same for every player.

    Args:
        date_str: Optional ISO date string (YYYY-MM-DD).
                  Defaults to today.

    Returns:
        A TransitSnapshot with positions for all 10 planets.
    """
    swe.set_ephe_path(None)

    jd, iso_date = _date_to_jd(date_str)

    planets: List[TransitPlanetPosition] = []

    for name, planet_id in PLANET_IDS.items():
        try:
            result, ret_flag = swe.calc_ut(jd, planet_id)
        except Exception as e:
            raise RuntimeError(f"Transit calculation failed for {name}: {e}") from e

        longitude = result[0]
        retrograde = result[3] < 0

        sign = _sign_from_longitude(longitude)
        deg_in_sign = _sign_degree(longitude)

        planets.append(TransitPlanetPosition(
            planet=name,
            sign=sign,
            degree=round(longitude, 4),
            sign_degree=deg_in_sign,
            retrograde=retrograde,
        ))

    swe.close()

    return TransitSnapshot(date=iso_date, planets=planets)


def calculate_player_transits(
    profile: PlayerProfile,
    date_str: Optional[str] = None,
) -> CosmicBriefing:
    """Calculate a full personalized cosmic briefing for a player.

    Overlays the daily transit sky onto the player's natal chart,
    detects aspects, assigns module statuses, and generates the
    briefing text and daily dispatch.

    Args:
        profile:  A PlayerProfile from the birth chart engine.
        date_str: Optional ISO date string (YYYY-MM-DD).
                  Defaults to today.

    Returns:
        A CosmicBriefing with module statuses, text, and dispatch.
    """
    # Get the transit snapshot
    snapshot = get_transit_snapshot(date_str)

    # Detect all aspects between transit planets and natal planets
    natal_planets = profile.natal_chart.planets
    aspect_hits = _detect_aspects(snapshot.planets, natal_planets)

    # Bucket aspects by module
    module_aspects: Dict[str, List[AspectHit]] = {m: [] for m in MODULE_NAMES}

    for hit in aspect_hits:
        module = _resolve_module_for_aspect(hit, natal_planets)
        if module in module_aspects:
            module_aspects[module].append(hit)

    # Build module statuses
    module_statuses: List[ModuleStatus] = []

    for module_name in MODULE_NAMES:
        aspects = module_aspects[module_name]
        co_star_cat = MODULE_CATEGORIES[module_name]

        if not aspects:
            module_statuses.append(ModuleStatus(
                module_name=module_name,
                co_star_category=co_star_cat,
                status="NEUTRAL",
                buff_percentage=0,
                aspects=[],
                description="No significant transits affecting this module today.",
            ))
            continue

        # Determine dominant status: count occurrences of each
        status_counts: Dict[str, int] = {"POWER": 0, "TROUBLE": 0, "PRESSURE": 0}
        total_buff = 0

        for a in aspects:
            status_counts[a.status] += 1
            total_buff += a.buff_percentage

        # Dominant status is the one with most hits; ties go in priority order
        dominant_status = max(
            status_counts,
            key=lambda s: (status_counts[s], ["PRESSURE", "TROUBLE", "POWER"].index(s)),
        )

        # Build description from all aspects
        desc_lines = []
        for a in aspects:
            desc_lines.append(_aspect_description(a))

        module_statuses.append(ModuleStatus(
            module_name=module_name,
            co_star_category=co_star_cat,
            status=dominant_status,
            buff_percentage=total_buff,
            aspects=aspects,
            description="; ".join(desc_lines),
        ))

    # Generate daily dispatch
    dispatch = _pick_dispatch(module_statuses)

    # Build briefing (text generated separately)
    briefing = CosmicBriefing(
        date=snapshot.date,
        player_id="player",
        module_statuses=module_statuses,
        briefing_text="",  # filled by generate_briefing_text
        daily_dispatch=dispatch,
    )

    # Generate and attach briefing text
    briefing.briefing_text = generate_briefing_text(briefing)

    return briefing


def generate_briefing_text(briefing: CosmicBriefing) -> str:
    """Format a CosmicBriefing into human-readable display text.

    Produces the station-style briefing with symbols, module names,
    aspect descriptions, and game effects.

    Args:
        briefing: A CosmicBriefing to format.

    Returns:
        Multi-line formatted string.
    """
    lines: List[str] = []
    lines.append(f"═══ COSMIC BRIEFING — {briefing.date} ═══")
    lines.append("")

    active_modules = [m for m in briefing.module_statuses if m.status != "NEUTRAL"]
    neutral_modules = [m for m in briefing.module_statuses if m.status == "NEUTRAL"]

    if not active_modules:
        lines.append("  No significant cosmic weather today.")
        lines.append("  All station modules operating at baseline.")
        lines.append("")
    else:
        for ms in active_modules:
            symbol = STATUS_SYMBOLS[ms.status]
            lines.append(f"  {symbol} {ms.status} in {ms.module_name} [{ms.co_star_category}]")

            for aspect in ms.aspects:
                desc = _aspect_description(aspect)
                lines.append(f"    {desc}")

            effect = _module_effect_text(ms)
            lines.append(f"    → {effect}")
            lines.append("")

    if neutral_modules:
        neutral_names = ", ".join(m.module_name for m in neutral_modules)
        lines.append(f"  ○ NEUTRAL: {neutral_names}")
        lines.append("")

    lines.append("───────────────────────────────────────────")
    lines.append(f"  \"{briefing.daily_dispatch}\"")
    lines.append("───────────────────────────────────────────")

    return "\n".join(lines)


def cosmic_briefing_to_dict(briefing: CosmicBriefing) -> dict:
    """Serialize a CosmicBriefing to a JSON-safe dictionary.

    Used by the API endpoint to return briefing data.
    """
    return {
        "date": briefing.date,
        "player_id": briefing.player_id,
        "module_statuses": [
            {
                "module_name": ms.module_name,
                "co_star_category": ms.co_star_category,
                "status": ms.status,
                "buff_percentage": ms.buff_percentage,
                "aspects": [
                    {
                        "transit_planet": a.transit_planet,
                        "natal_planet": a.natal_planet,
                        "aspect_type": a.aspect_type,
                        "angle": a.angle,
                        "orb": a.orb,
                        "status": a.status,
                        "strength": a.strength,
                        "buff_percentage": a.buff_percentage,
                    }
                    for a in ms.aspects
                ],
                "description": ms.description,
            }
            for ms in briefing.module_statuses
        ],
        "briefing_text": briefing.briefing_text,
        "daily_dispatch": briefing.daily_dispatch,
        "is_cached": briefing.is_cached,
    }


def transit_snapshot_to_dict(snapshot: TransitSnapshot) -> dict:
    """Serialize a TransitSnapshot to a JSON-safe dictionary."""
    return {
        "date": snapshot.date,
        "planets": [
            {
                "planet": p.planet,
                "sign": p.sign,
                "degree": p.degree,
                "sign_degree": p.sign_degree,
                "retrograde": p.retrograde,
            }
            for p in snapshot.planets
        ],
    }

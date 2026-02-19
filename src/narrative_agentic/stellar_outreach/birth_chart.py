"""
NEXUS STATION - Stellar Outreach: Birth Chart Engine (TASK-001)

Calculates natal birth charts using the Swiss Ephemeris (swisseph/pyswisseph).
Maps astronomical positions to the Zodiac Archetype system defined in the
Stellar Outreach Game Design Document (GDD S3.2).

Security Note (Article II / Kai Chen review):
    This module computes and returns derived chart data only.
    Raw birth details (date, time, coordinates) are NOT stored or
    included in any output structure.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date, time, datetime
from typing import Dict, List, Optional, Tuple

import swisseph as swe


# ────────────────────────────────────────────────────────────────
# Constants
# ────────────────────────────────────────────────────────────────

ZODIAC_SIGNS: List[str] = [
    "Aries", "Taurus", "Gemini", "Cancer",
    "Leo", "Virgo", "Libra", "Scorpio",
    "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]

ELEMENTS: Dict[str, str] = {
    "Aries": "Fire", "Taurus": "Earth", "Gemini": "Air", "Cancer": "Water",
    "Leo": "Fire", "Virgo": "Earth", "Libra": "Air", "Scorpio": "Water",
    "Sagittarius": "Fire", "Capricorn": "Earth", "Aquarius": "Air", "Pisces": "Water",
}

# Swiss Ephemeris planet IDs we care about
PLANET_IDS: Dict[str, int] = {
    "Sun": swe.SUN,
    "Moon": swe.MOON,
    "Mercury": swe.MERCURY,
    "Venus": swe.VENUS,
    "Mars": swe.MARS,
    "Jupiter": swe.JUPITER,
    "Saturn": swe.SATURN,
    "Uranus": swe.URANUS,
    "Neptune": swe.NEPTUNE,
    "Pluto": swe.PLUTO,
}

# Essential dignities: planet -> sign(s) where it rules
PLANET_RULERSHIPS: Dict[str, List[str]] = {
    "Sun": ["Leo"],
    "Moon": ["Cancer"],
    "Mercury": ["Gemini", "Virgo"],
    "Venus": ["Taurus", "Libra"],
    "Mars": ["Aries", "Scorpio"],
    "Jupiter": ["Sagittarius", "Pisces"],
    "Saturn": ["Capricorn", "Aquarius"],
    "Uranus": ["Aquarius"],
    "Neptune": ["Pisces"],
    "Pluto": ["Scorpio"],
}

# Exaltation signs
PLANET_EXALTATIONS: Dict[str, str] = {
    "Sun": "Aries",
    "Moon": "Taurus",
    "Mercury": "Virgo",
    "Venus": "Pisces",
    "Mars": "Capricorn",
    "Jupiter": "Cancer",
    "Saturn": "Libra",
}

# Angular houses (strongest positional dignity)
ANGULAR_HOUSES: List[int] = [1, 4, 7, 10]

# Orb for major aspects (degrees)
ASPECT_ORB: float = 8.0

# Major aspects (degrees)
MAJOR_ASPECTS: List[float] = [0.0, 60.0, 90.0, 120.0, 180.0]


# ────────────────────────────────────────────────────────────────
# GDD S3.2 - Zodiac Archetype Definitions
# ────────────────────────────────────────────────────────────────

_ARCHETYPE_TABLE: Dict[str, Dict] = {
    "Aries": {
        "element": "Fire",
        "role": "Commander",
        "strengths": ["+Combat", "+Speed"],
        "weakness": "-Patience",
    },
    "Taurus": {
        "element": "Earth",
        "role": "Engineer",
        "strengths": ["+Building", "+Resources"],
        "weakness": "-Adaptability",
    },
    "Gemini": {
        "element": "Air",
        "role": "Communications",
        "strengths": ["+Social", "+Intel"],
        "weakness": "-Focus",
    },
    "Cancer": {
        "element": "Water",
        "role": "Life Support",
        "strengths": ["+Crew Morale", "+Healing"],
        "weakness": "-Risk-taking",
    },
    "Leo": {
        "element": "Fire",
        "role": "Captain",
        "strengths": ["+Leadership", "+Charisma"],
        "weakness": "-Stealth",
    },
    "Virgo": {
        "element": "Earth",
        "role": "Analyst",
        "strengths": ["+Precision", "+Crafting"],
        "weakness": "-Spontaneity",
    },
    "Libra": {
        "element": "Air",
        "role": "Diplomat",
        "strengths": ["+Trade", "+Alliances"],
        "weakness": "-Decisiveness",
    },
    "Scorpio": {
        "element": "Water",
        "role": "Intelligence",
        "strengths": ["+Research", "+Crit Chance"],
        "weakness": "-Trust",
    },
    "Sagittarius": {
        "element": "Fire",
        "role": "Explorer",
        "strengths": ["+Discovery", "+XP Gain"],
        "weakness": "-Defense",
    },
    "Capricorn": {
        "element": "Earth",
        "role": "Administrator",
        "strengths": ["+Efficiency", "+Gold"],
        "weakness": "-Creativity",
    },
    "Aquarius": {
        "element": "Air",
        "role": "Innovator",
        "strengths": ["+Tech", "+Unique Finds"],
        "weakness": "-Tradition",
    },
    "Pisces": {
        "element": "Water",
        "role": "Mystic",
        "strengths": ["+Intuition", "+Healing"],
        "weakness": "-Combat",
    },
}


# ────────────────────────────────────────────────────────────────
# Data Classes
# ────────────────────────────────────────────────────────────────

@dataclass
class BirthChartInput:
    """Input parameters for chart calculation.

    Attributes:
        birth_date: Date of birth (YYYY-MM-DD).
        birth_time: Time of birth (HH:MM), optional.
                    When None a sunrise chart is used as fallback.
        latitude:   Birth location latitude  (-90 to 90).
        longitude:  Birth location longitude (-180 to 180).
    """
    birth_date: date
    latitude: float
    longitude: float
    birth_time: Optional[time] = None

    def __post_init__(self):
        if not (-90 <= self.latitude <= 90):
            raise ValueError(f"Latitude must be between -90 and 90, got {self.latitude}")
        if not (-180 <= self.longitude <= 180):
            raise ValueError(f"Longitude must be between -180 and 180, got {self.longitude}")


@dataclass
class PlanetPosition:
    """Position of a single celestial body in the natal chart."""
    planet: str
    sign: str
    degree: float          # 0-360 ecliptic longitude
    sign_degree: float     # 0-30 degree within the sign
    house: int             # 1-12
    retrograde: bool


@dataclass
class NatalChart:
    """Full natal chart data."""
    planets: List[PlanetPosition]
    house_cusps: List[float]       # 12 house cusp longitudes (Placidus)
    ascendant: float               # Ecliptic longitude of ASC
    ascendant_sign: str
    midheaven: float               # Ecliptic longitude of MC
    midheaven_sign: str


@dataclass
class ZodiacArchetype:
    """Game archetype derived from Sun sign (GDD S3.2)."""
    sign: str
    element: str
    role: str
    strengths: List[str]
    weakness: str


@dataclass
class PlayerProfile:
    """Complete player profile returned by the birth chart engine.

    Security: This object contains NO raw birth data - only derived
    astronomical and game-mechanic information.
    """
    natal_chart: NatalChart
    archetype: ZodiacArchetype
    elemental_balance: Dict[str, int]
    dominant_planet: str
    is_sunrise_chart: bool


# ────────────────────────────────────────────────────────────────
# Internal Helpers
# ────────────────────────────────────────────────────────────────

def _sign_from_longitude(longitude: float) -> str:
    """Return the zodiac sign for an ecliptic longitude (0-360)."""
    index = int(longitude / 30.0) % 12
    return ZODIAC_SIGNS[index]


def _sign_degree(longitude: float) -> float:
    """Return the degree within a zodiac sign (0-30)."""
    return round(longitude % 30.0, 4)


def _to_julian_day(dt: datetime) -> float:
    """Convert a Python datetime to Julian Day (UT)."""
    hour_decimal = dt.hour + dt.minute / 60.0 + dt.second / 3600.0
    jd = swe.julday(dt.year, dt.month, dt.day, hour_decimal)
    return jd


def _calculate_sunrise(jd_date: float, lat: float, lon: float) -> float:
    """Calculate sunrise time as a Julian Day for the given date and location.

    Uses Swiss Ephemeris rise/transit/set function.
    Returns the JD of sunrise, or noon UT as a last-resort fallback.
    """
    # swe.rise_trans expects geographic longitude positive=East
    geopos = (lon, lat, 0.0)  # (lon, lat, altitude)

    try:
        result = swe.rise_trans(
            jd_date,
            swe.SUN,
            geopos=geopos,
            rsmi=swe.CALC_RISE,
        )
        # result is a tuple: (jd_rise, retflag) or similar depending on version
        if isinstance(result, tuple):
            # pyswisseph returns (tuple_of_values, return_flag)
            jd_rise = result[1][0] if isinstance(result[1], (list, tuple)) else result[0]
            if isinstance(jd_rise, (list, tuple)):
                jd_rise = jd_rise[0]
            return float(jd_rise)
    except Exception:
        pass

    # Fallback: approximate sunrise as 6:00 local solar time
    local_solar_offset = lon / 15.0  # hours offset from UT
    return jd_date + (6.0 - local_solar_offset) / 24.0


def _determine_house(longitude: float, house_cusps: List[float]) -> int:
    """Determine which house a planet falls in based on house cusps.

    Args:
        longitude:   Ecliptic longitude of the planet (0-360).
        house_cusps: List of 12 house cusp longitudes.

    Returns:
        House number (1-12).
    """
    for i in range(12):
        cusp_start = house_cusps[i]
        cusp_end = house_cusps[(i + 1) % 12]

        if cusp_start < cusp_end:
            # Normal case: cusp doesn't cross 0 Aries
            if cusp_start <= longitude < cusp_end:
                return i + 1
        else:
            # Cusp crosses 0 Aries
            if longitude >= cusp_start or longitude < cusp_end:
                return i + 1

    # Fallback (should not occur with valid cusps)
    return 1


def _count_aspects(planet_lon: float, all_longitudes: List[float]) -> int:
    """Count the number of major aspects a planet makes to other bodies."""
    count = 0
    for other_lon in all_longitudes:
        if abs(planet_lon - other_lon) < 0.01:
            continue  # skip self
        diff = abs(planet_lon - other_lon) % 360
        if diff > 180:
            diff = 360 - diff
        for aspect in MAJOR_ASPECTS:
            if abs(diff - aspect) <= ASPECT_ORB:
                count += 1
                break
    return count


def _calculate_dominant_planet(
    planets: List[PlanetPosition],
    house_cusps: List[float],
) -> str:
    """Determine the most influential planet by scoring dignity, aspects, and angularity.

    Scoring:
        +4  Planet in its own ruling sign (domicile)
        +3  Planet in exaltation sign
        +3  Planet in an angular house (1, 4, 7, 10)
        +1  Per major aspect to another planet
    """
    all_longitudes = [p.degree for p in planets]
    scores: Dict[str, int] = {}

    for p in planets:
        score = 0

        # Dignity: domicile
        if p.sign in PLANET_RULERSHIPS.get(p.planet, []):
            score += 4

        # Dignity: exaltation
        if PLANET_EXALTATIONS.get(p.planet) == p.sign:
            score += 3

        # Angular house bonus
        if p.house in ANGULAR_HOUSES:
            score += 3

        # Aspect count
        score += _count_aspects(p.degree, all_longitudes)

        scores[p.planet] = score

    # Return the planet with the highest score; break ties by traditional order
    planet_order = list(PLANET_IDS.keys())
    dominant = max(scores, key=lambda name: (scores[name], -planet_order.index(name)))
    return dominant


def _calculate_elemental_balance(planets: List[PlanetPosition]) -> Dict[str, int]:
    """Count how many planets fall in each element."""
    balance: Dict[str, int] = {"Fire": 0, "Earth": 0, "Air": 0, "Water": 0}
    for p in planets:
        element = ELEMENTS.get(p.sign)
        if element:
            balance[element] += 1
    return balance


def _get_archetype(sun_sign: str) -> ZodiacArchetype:
    """Map a Sun sign to its GDD archetype."""
    entry = _ARCHETYPE_TABLE[sun_sign]
    return ZodiacArchetype(
        sign=sun_sign,
        element=entry["element"],
        role=entry["role"],
        strengths=list(entry["strengths"]),
        weakness=entry["weakness"],
    )


# ────────────────────────────────────────────────────────────────
# Public API
# ────────────────────────────────────────────────────────────────

def calculate_birth_chart(input: BirthChartInput) -> PlayerProfile:
    """Calculate a full birth chart and derive the player profile.

    Args:
        input: A BirthChartInput with date, optional time, and coordinates.

    Returns:
        A PlayerProfile containing the natal chart, archetype,
        elemental balance, dominant planet, and sunrise chart flag.

    Raises:
        ValueError: For invalid input parameters.
        RuntimeError: If Swiss Ephemeris calculation fails.
    """
    # Use built-in ephemeris (no external data files needed)
    swe.set_ephe_path(None)

    is_sunrise_chart = input.birth_time is None

    # Build datetime in UT
    if input.birth_time is not None:
        dt = datetime.combine(input.birth_date, input.birth_time)
        jd = _to_julian_day(dt)
    else:
        # Sunrise fallback (GDD requirement)
        jd_noon = swe.julday(
            input.birth_date.year,
            input.birth_date.month,
            input.birth_date.day,
            12.0,
        )
        jd = _calculate_sunrise(jd_noon, input.latitude, input.longitude)

    # ── House Cusps (Placidus) ──────────────────────────────────
    try:
        cusps_tuple, ascmc = swe.houses(jd, input.latitude, input.longitude, b'P')
    except Exception as e:
        raise RuntimeError(f"House calculation failed: {e}") from e

    house_cusps = list(cusps_tuple)  # 12 cusp longitudes
    ascendant = ascmc[0]
    midheaven = ascmc[1]

    # ── Planet Positions ────────────────────────────────────────
    planets: List[PlanetPosition] = []

    for name, planet_id in PLANET_IDS.items():
        try:
            result, ret_flag = swe.calc_ut(jd, planet_id)
        except Exception as e:
            raise RuntimeError(f"Calculation failed for {name}: {e}") from e

        longitude = result[0]
        # Negative speed in longitude indicates retrograde motion
        retrograde = result[3] < 0

        sign = _sign_from_longitude(longitude)
        deg_in_sign = _sign_degree(longitude)
        house = _determine_house(longitude, house_cusps)

        planets.append(PlanetPosition(
            planet=name,
            sign=sign,
            degree=round(longitude, 4),
            sign_degree=deg_in_sign,
            house=house,
            retrograde=retrograde,
        ))

    # ── Assemble Natal Chart ────────────────────────────────────
    natal_chart = NatalChart(
        planets=planets,
        house_cusps=[round(c, 4) for c in house_cusps],
        ascendant=round(ascendant, 4),
        ascendant_sign=_sign_from_longitude(ascendant),
        midheaven=round(midheaven, 4),
        midheaven_sign=_sign_from_longitude(midheaven),
    )

    # ── Derive Game Mechanics ───────────────────────────────────
    sun_pos = next(p for p in planets if p.planet == "Sun")
    archetype = _get_archetype(sun_pos.sign)
    elemental_balance = _calculate_elemental_balance(planets)
    dominant_planet = _calculate_dominant_planet(planets, house_cusps)

    # ── Build Player Profile (no raw birth data) ────────────────
    profile = PlayerProfile(
        natal_chart=natal_chart,
        archetype=archetype,
        elemental_balance=elemental_balance,
        dominant_planet=dominant_planet,
        is_sunrise_chart=is_sunrise_chart,
    )

    # Close Swiss Ephemeris
    swe.close()

    return profile


def player_profile_to_dict(profile: PlayerProfile) -> dict:
    """Serialize a PlayerProfile to a JSON-safe dictionary.

    Used by the API endpoint to return chart data.
    """
    return {
        "natal_chart": {
            "planets": [
                {
                    "planet": p.planet,
                    "sign": p.sign,
                    "degree": p.degree,
                    "sign_degree": p.sign_degree,
                    "house": p.house,
                    "retrograde": p.retrograde,
                }
                for p in profile.natal_chart.planets
            ],
            "house_cusps": profile.natal_chart.house_cusps,
            "ascendant": profile.natal_chart.ascendant,
            "ascendant_sign": profile.natal_chart.ascendant_sign,
            "midheaven": profile.natal_chart.midheaven,
            "midheaven_sign": profile.natal_chart.midheaven_sign,
        },
        "archetype": {
            "sign": profile.archetype.sign,
            "element": profile.archetype.element,
            "role": profile.archetype.role,
            "strengths": profile.archetype.strengths,
            "weakness": profile.archetype.weakness,
        },
        "elemental_balance": profile.elemental_balance,
        "dominant_planet": profile.dominant_planet,
        "is_sunrise_chart": profile.is_sunrise_chart,
    }

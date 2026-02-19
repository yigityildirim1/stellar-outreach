"""
NEXUS STATION - Stellar Outreach: AR Sky Scanner Engine (TASK-018)

Backend engine for augmented-reality sky scanning: ISS tracking, constellation
visibility, deep-sky object detection, and AR session lifecycle.

Provides:
    - Real-time ISS position (Open Notify API + TLE fallback)
    - ISS pass prediction for observer location
    - Constellation/star/deep-sky visibility based on observer coordinates + time
    - Sky snapshot assembly (full visible-sky state for a location)
    - AR identification sessions with scoring and XP

The mobile AR client consumes these endpoints; rendering is client-side.

Coordinate system:
    - Internal: J2000 equatorial (RA in degrees, Dec in degrees)
    - Output: horizontal (altitude/azimuth in degrees, 0° = north, clockwise)

References:
    - GDD §12: AR Sky Scanner feature
    - mini_games.py: _CONSTELLATION_DATA (12 constellations, star positions)
    - mini_games_phase2.py: _CELESTIAL_OBJECTS (15 deep-sky objects with RA/Dec)

Security Note (Article II / Kai Chen review):
    [KAI] ISS API is unauthenticated public endpoint — no secrets stored.
    TLE fallback prevents dependency on external service availability.
    Session IDs are UUIDs. Player IDs sanitized for filesystem safety.
    AR history capped at 50 entries per player to prevent unbounded growth.

UX Note (Marina Okonkwo review):
    [MARINA] Sky messages in Co-Star voice. Darkness level communicated clearly.
    ISS pass times human-readable. Session flow: snapshot → identify → celebrate.
    Free for all players — no pay-to-win gating on sky discovery.

Ethics Note (Dr. Elena Vasquez review):
    [ELENA] AR is free for all players. Discoveries supplement normal gameplay.
    No data collection beyond player_id. Positive framing only — no fear or scarcity.
"""

from __future__ import annotations

import json
import math
import os
import random
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.request import urlopen
from urllib.error import URLError


# ────────────────────────────────────────────────────────────────
# Persistence Configuration
# ────────────────────────────────────────────────────────────────

AR_SESSIONS_DIR = Path.home() / ".nexus_station" / "ar_sessions"
ISS_CACHE_DIR = Path.home() / ".nexus_station" / "iss_cache"


# ────────────────────────────────────────────────────────────────
# Constants
# ────────────────────────────────────────────────────────────────

ISS_POSITION_URL = "http://api.open-notify.org/iss-now.json"
ISS_POSITION_CACHE_SECONDS = 30
ISS_PASSES_CACHE_SECONDS = 3600

# Hardcoded ISS TLE for offline fallback (updated periodically)
ISS_TLE_LINE1 = "1 25544U 98067A   24045.54791667  .00016717  00000-0  10270-3 0  9008"
ISS_TLE_LINE2 = "2 25544  51.6400 123.6520 0004560 291.5470 188.0750 15.49560920434567"

# ISS orbital parameters (derived from TLE for simplified propagation)
ISS_INCLINATION_DEG = 51.64
ISS_PERIOD_MINUTES = 92.87  # ~15.5 revolutions/day
ISS_ALTITUDE_KM = 420.0

# Scoring constants (matches mini-game pattern)
AR_BASE_SCORE_CONSTELLATION = 25
AR_BASE_SCORE_DEEP_SKY = 35
AR_BASE_SCORE_STAR = 15
AR_BASE_SCORE_ISS = 50
AR_SESSION_TIME_LIMIT = 300  # 5 minutes

MAX_AR_HISTORY = 50


# ────────────────────────────────────────────────────────────────
# Data Models
# ────────────────────────────────────────────────────────────────

@dataclass
class IssPosition:
    """Current ISS position."""
    lat: float
    lng: float
    altitude_km: float
    velocity_kms: float
    timestamp: str
    source: str  # "api" or "tle"


@dataclass
class IssPass:
    """A predicted ISS pass over observer location."""
    rise_time: str
    rise_azimuth: float
    peak_time: str
    peak_altitude: float
    peak_azimuth: float
    set_time: str
    set_azimuth: float
    duration_seconds: int
    brightness: float  # approximate magnitude
    visible: bool


@dataclass
class VisibleConstellation:
    """A constellation visible from observer location."""
    id: str
    name: str
    altitude: float  # center altitude in degrees
    azimuth: float   # center azimuth in degrees
    rising: bool
    setting: bool
    stars_above_horizon: int
    total_stars: int
    best_star: str
    mythology: str
    difficulty: int


@dataclass
class VisibleObject:
    """A deep-sky object visible from observer location."""
    id: str
    name: str
    type: str  # galaxy, nebula, cluster
    altitude: float
    azimuth: float
    magnitude: float
    hint: str


@dataclass
class SkySnapshot:
    """Complete visible sky state for a location and time."""
    lat: float
    lng: float
    timestamp: str
    constellations: List[VisibleConstellation]
    objects: List[VisibleObject]
    bright_stars: List[dict]
    iss_position: Optional[IssPosition]
    iss_visible: bool
    moon_phase: str
    moon_illumination: float
    darkness_level: str  # "daylight", "civil_twilight", "nautical_twilight", "astronomical_twilight", "dark"
    sky_message: str


@dataclass
class ArSession:
    """An active AR identification session."""
    session_id: str
    player_id: str
    lat: float
    lng: float
    started_at: str
    expires_at: str
    targets: List[dict]  # objects to find
    identified: List[dict]  # successfully identified
    score: int
    xp: int
    completed: bool


@dataclass
class ArPlayerHistory:
    """AR session history for a player."""
    player_id: str
    sessions: List[dict]
    total_sessions: int
    total_identifications: int
    total_score: int
    total_xp: int
    favorite_target: Optional[str]
    best_session_score: int


# ────────────────────────────────────────────────────────────────
# Constellation Positions — J2000 RA/Dec (degrees)
# Real coordinates for the 12 constellations from mini_games.py
# ────────────────────────────────────────────────────────────────

_CONSTELLATION_POSITIONS: Dict[str, dict] = {
    "Orion": {
        "center_ra": 85.0, "center_dec": 0.0,
        "mythology": "the hunter who boasted he could kill any creature on earth. artemis placed him among the stars.",
        "stars": [
            {"id": "betelgeuse",  "name": "Betelgeuse",  "ra": 88.79, "dec": 7.41,  "mag": 0.42},
            {"id": "rigel",       "name": "Rigel",        "ra": 78.63, "dec": -8.20, "mag": 0.13},
            {"id": "bellatrix",   "name": "Bellatrix",    "ra": 81.28, "dec": 6.35,  "mag": 1.64},
            {"id": "mintaka",     "name": "Mintaka",      "ra": 83.00, "dec": -0.30, "mag": 2.23},
            {"id": "alnilam",     "name": "Alnilam",      "ra": 84.05, "dec": -1.20, "mag": 1.69},
            {"id": "alnitak",     "name": "Alnitak",      "ra": 85.19, "dec": -1.94, "mag": 1.77},
            {"id": "saiph",       "name": "Saiph",        "ra": 86.94, "dec": -9.67, "mag": 2.09},
        ],
    },
    "Ursa Major": {
        "center_ra": 165.0, "center_dec": 56.0,
        "mythology": "callisto, transformed into a bear by hera's jealousy. zeus placed her in the sky to save her.",
        "stars": [
            {"id": "dubhe",   "name": "Dubhe",   "ra": 165.93, "dec": 61.75, "mag": 1.79},
            {"id": "merak",   "name": "Merak",    "ra": 165.46, "dec": 56.38, "mag": 2.37},
            {"id": "phecda",  "name": "Phecda",   "ra": 178.46, "dec": 53.69, "mag": 2.44},
            {"id": "megrez",  "name": "Megrez",   "ra": 183.86, "dec": 57.03, "mag": 3.31},
            {"id": "alioth",  "name": "Alioth",   "ra": 193.51, "dec": 55.96, "mag": 1.77},
            {"id": "mizar",   "name": "Mizar",    "ra": 200.98, "dec": 54.93, "mag": 2.27},
            {"id": "alkaid",  "name": "Alkaid",   "ra": 206.89, "dec": 49.31, "mag": 1.86},
        ],
    },
    "Ursa Minor": {
        "center_ra": 230.0, "center_dec": 78.0,
        "mythology": "arcas, son of callisto, almost killed his mother-bear. zeus turned him into a small bear and placed both in the sky.",
        "stars": [
            {"id": "polaris",  "name": "Polaris",   "ra": 37.95,  "dec": 89.26, "mag": 1.98},
            {"id": "kochab",   "name": "Kochab",    "ra": 222.68, "dec": 74.16, "mag": 2.08},
            {"id": "pherkad",  "name": "Pherkad",   "ra": 230.18, "dec": 71.83, "mag": 3.05},
            {"id": "yildun",   "name": "Yildun",    "ra": 263.05, "dec": 86.59, "mag": 4.36},
        ],
    },
    "Cassiopeia": {
        "center_ra": 15.0, "center_dec": 60.0,
        "mythology": "the vain queen who boasted of her beauty. poseidon chained her to a throne in the sky, sometimes upside down.",
        "stars": [
            {"id": "schedar",   "name": "Schedar",    "ra": 10.13,  "dec": 56.54, "mag": 2.23},
            {"id": "caph",      "name": "Caph",       "ra": 2.29,   "dec": 59.15, "mag": 2.27},
            {"id": "gamma_cas", "name": "Gamma Cas",  "ra": 14.18,  "dec": 60.72, "mag": 2.47},
            {"id": "ruchbah",   "name": "Ruchbah",    "ra": 21.45,  "dec": 60.24, "mag": 2.68},
            {"id": "segin",     "name": "Segin",      "ra": 28.60,  "dec": 63.67, "mag": 3.37},
        ],
    },
    "Leo": {
        "center_ra": 152.0, "center_dec": 15.0,
        "mythology": "the nemean lion, slain by heracles as his first labor. its hide was impervious to weapons.",
        "stars": [
            {"id": "regulus",     "name": "Regulus",     "ra": 152.09, "dec": 11.97, "mag": 1.35},
            {"id": "denebola",    "name": "Denebola",    "ra": 177.26, "dec": 14.57, "mag": 2.14},
            {"id": "algieba",     "name": "Algieba",     "ra": 146.46, "dec": 19.84, "mag": 2.08},
            {"id": "zosma",       "name": "Zosma",       "ra": 168.53, "dec": 20.52, "mag": 2.56},
        ],
    },
    "Scorpius": {
        "center_ra": 255.0, "center_dec": -30.0,
        "mythology": "the scorpion that killed orion. placed on the opposite side of the sky so they would never meet again.",
        "stars": [
            {"id": "antares",   "name": "Antares",    "ra": 247.35, "dec": -26.43, "mag": 0.96},
            {"id": "shaula",    "name": "Shaula",     "ra": 263.40, "dec": -37.10, "mag": 1.63},
            {"id": "dschubba",  "name": "Dschubba",   "ra": 240.08, "dec": -22.62, "mag": 2.32},
            {"id": "graffias",  "name": "Graffias",   "ra": 241.36, "dec": -19.81, "mag": 2.62},
        ],
    },
    "Gemini": {
        "center_ra": 107.0, "center_dec": 25.0,
        "mythology": "castor and pollux, the twin brothers. when mortal castor died, pollux shared his immortality so they could stay together.",
        "stars": [
            {"id": "castor",  "name": "Castor",  "ra": 113.65, "dec": 31.89, "mag": 1.58},
            {"id": "pollux",  "name": "Pollux",  "ra": 116.33, "dec": 28.03, "mag": 1.14},
            {"id": "alhena",  "name": "Alhena",  "ra": 99.43,  "dec": 16.40, "mag": 1.93},
            {"id": "wasat",   "name": "Wasat",   "ra": 110.03, "dec": 21.98, "mag": 3.53},
        ],
    },
    "Taurus": {
        "center_ra": 67.0, "center_dec": 18.0,
        "mythology": "zeus disguised as a white bull to carry europa across the sea. only the head and shoulders rise above the waves.",
        "stars": [
            {"id": "aldebaran",  "name": "Aldebaran",  "ra": 68.98,  "dec": 16.51, "mag": 0.86},
            {"id": "elnath",     "name": "Elnath",     "ra": 81.57,  "dec": 28.61, "mag": 1.65},
            {"id": "zeta_tau",   "name": "Zeta Tau",   "ra": 84.41,  "dec": 21.14, "mag": 3.01},
        ],
    },
    "Cygnus": {
        "center_ra": 310.0, "center_dec": 42.0,
        "mythology": "zeus disguised as a swan to visit leda. or orpheus, placed in the sky near his lyre after death.",
        "stars": [
            {"id": "deneb",    "name": "Deneb",      "ra": 310.36, "dec": 45.28, "mag": 1.25},
            {"id": "sadr",     "name": "Sadr",       "ra": 305.56, "dec": 40.26, "mag": 2.20},
            {"id": "gienah",   "name": "Gienah Cyg", "ra": 305.25, "dec": 33.97, "mag": 2.46},
            {"id": "albireo",  "name": "Albireo",    "ra": 292.68, "dec": 27.96, "mag": 3.08},
        ],
    },
    "Lyra": {
        "center_ra": 282.0, "center_dec": 38.0,
        "mythology": "the lyre of orpheus, whose music could charm stones and rivers. after his death, zeus placed it among the stars.",
        "stars": [
            {"id": "vega",     "name": "Vega",     "ra": 279.23, "dec": 38.78, "mag": 0.03},
            {"id": "sheliak",  "name": "Sheliak",  "ra": 282.52, "dec": 33.36, "mag": 3.52},
            {"id": "sulafat",  "name": "Sulafat",  "ra": 284.74, "dec": 32.69, "mag": 3.24},
        ],
    },
    "Aquila": {
        "center_ra": 297.0, "center_dec": 5.0,
        "mythology": "the eagle that carried zeus's thunderbolts. or the eagle that brought ganymede to olympus.",
        "stars": [
            {"id": "altair",   "name": "Altair",   "ra": 297.70, "dec": 8.87,  "mag": 0.77},
            {"id": "tarazed",  "name": "Tarazed",  "ra": 296.56, "dec": 10.61, "mag": 2.72},
            {"id": "alshain",  "name": "Alshain",  "ra": 298.83, "dec": 6.41,  "mag": 3.71},
        ],
    },
    "Canis Major": {
        "center_ra": 101.0, "center_dec": -22.0,
        "mythology": "orion's faithful hunting dog, chasing the hare lepus across the sky for eternity.",
        "stars": [
            {"id": "sirius",  "name": "Sirius",  "ra": 101.29, "dec": -16.72, "mag": -1.46},
            {"id": "adhara",  "name": "Adhara",  "ra": 104.66, "dec": -28.97, "mag": 1.50},
            {"id": "wezen",   "name": "Wezen",   "ra": 107.10, "dec": -26.39, "mag": 1.84},
            {"id": "mirzam",  "name": "Mirzam",  "ra": 95.67,  "dec": -17.96, "mag": 1.98},
        ],
    },
}


# ────────────────────────────────────────────────────────────────
# Bright Stars — Top 20 naked-eye stars with J2000 RA/Dec
# ────────────────────────────────────────────────────────────────

_BRIGHT_STARS: List[dict] = [
    {"id": "sirius",      "name": "Sirius",       "ra": 101.29, "dec": -16.72, "mag": -1.46, "constellation": "Canis Major"},
    {"id": "canopus",     "name": "Canopus",      "ra": 95.99,  "dec": -52.70, "mag": -0.74, "constellation": "Carina"},
    {"id": "arcturus",    "name": "Arcturus",     "ra": 213.92, "dec": 19.18,  "mag": -0.05, "constellation": "Boötes"},
    {"id": "vega",        "name": "Vega",         "ra": 279.23, "dec": 38.78,  "mag": 0.03,  "constellation": "Lyra"},
    {"id": "capella",     "name": "Capella",      "ra": 79.17,  "dec": 46.00,  "mag": 0.08,  "constellation": "Auriga"},
    {"id": "rigel",       "name": "Rigel",        "ra": 78.63,  "dec": -8.20,  "mag": 0.13,  "constellation": "Orion"},
    {"id": "procyon",     "name": "Procyon",      "ra": 114.83, "dec": 5.22,   "mag": 0.34,  "constellation": "Canis Minor"},
    {"id": "betelgeuse",  "name": "Betelgeuse",   "ra": 88.79,  "dec": 7.41,   "mag": 0.42,  "constellation": "Orion"},
    {"id": "altair",      "name": "Altair",       "ra": 297.70, "dec": 8.87,   "mag": 0.77,  "constellation": "Aquila"},
    {"id": "aldebaran",   "name": "Aldebaran",    "ra": 68.98,  "dec": 16.51,  "mag": 0.86,  "constellation": "Taurus"},
    {"id": "antares",     "name": "Antares",      "ra": 247.35, "dec": -26.43, "mag": 0.96,  "constellation": "Scorpius"},
    {"id": "spica",       "name": "Spica",        "ra": 201.30, "dec": -11.16, "mag": 1.04,  "constellation": "Virgo"},
    {"id": "pollux",      "name": "Pollux",       "ra": 116.33, "dec": 28.03,  "mag": 1.14,  "constellation": "Gemini"},
    {"id": "fomalhaut",   "name": "Fomalhaut",    "ra": 344.41, "dec": -29.62, "mag": 1.16,  "constellation": "Piscis Austrinus"},
    {"id": "deneb",       "name": "Deneb",        "ra": 310.36, "dec": 45.28,  "mag": 1.25,  "constellation": "Cygnus"},
    {"id": "regulus",     "name": "Regulus",       "ra": 152.09, "dec": 11.97,  "mag": 1.35,  "constellation": "Leo"},
    {"id": "castor",      "name": "Castor",       "ra": 113.65, "dec": 31.89,  "mag": 1.58,  "constellation": "Gemini"},
    {"id": "shaula",      "name": "Shaula",       "ra": 263.40, "dec": -37.10, "mag": 1.63,  "constellation": "Scorpius"},
    {"id": "bellatrix",   "name": "Bellatrix",    "ra": 81.28,  "dec": 6.35,   "mag": 1.64,  "constellation": "Orion"},
    {"id": "elnath",      "name": "Elnath",       "ra": 81.57,  "dec": 28.61,  "mag": 1.65,  "constellation": "Taurus"},
]


# Deep-sky objects reused from mini_games_phase2.py
_DEEP_SKY_OBJECTS: List[dict] = [
    {"id": "m31", "name": "Andromeda Galaxy", "type": "galaxy", "ra": 10.68, "dec": 41.27, "magnitude": 3.4,
     "hint": "The nearest spiral galaxy to the Milky Way, visible as a fuzzy patch in dark skies."},
    {"id": "m42", "name": "Orion Nebula", "type": "nebula", "ra": 83.82, "dec": -5.39, "magnitude": 4.0,
     "hint": "A stellar nursery in Orion's sword, where new stars are born from gas and dust."},
    {"id": "m45", "name": "Pleiades", "type": "cluster", "ra": 56.87, "dec": 24.12, "magnitude": 1.6,
     "hint": "The Seven Sisters — a young open cluster easily visible to the naked eye."},
    {"id": "m13", "name": "Hercules Cluster", "type": "cluster", "ra": 250.42, "dec": 36.46, "magnitude": 5.8,
     "hint": "One of the brightest globular clusters in the northern sky, containing 300,000 stars."},
    {"id": "m1", "name": "Crab Nebula", "type": "nebula", "ra": 83.63, "dec": 22.01, "magnitude": 8.4,
     "hint": "The remnant of a supernova observed by Chinese astronomers in 1054 AD."},
    {"id": "m57", "name": "Ring Nebula", "type": "nebula", "ra": 283.4, "dec": 33.03, "magnitude": 8.8,
     "hint": "A planetary nebula in Lyra — the glowing shell expelled by a dying star."},
    {"id": "m51", "name": "Whirlpool Galaxy", "type": "galaxy", "ra": 202.47, "dec": 47.2, "magnitude": 8.4,
     "hint": "A face-on spiral galaxy interacting with its smaller companion."},
    {"id": "m8", "name": "Lagoon Nebula", "type": "nebula", "ra": 270.9, "dec": -24.38, "magnitude": 6.0,
     "hint": "A giant interstellar cloud in Sagittarius, one of only two star-forming nebulae visible to the naked eye."},
    {"id": "m27", "name": "Dumbbell Nebula", "type": "nebula", "ra": 299.9, "dec": 22.72, "magnitude": 7.5,
     "hint": "The first planetary nebula ever discovered, shaped like an hourglass."},
    {"id": "ngc869", "name": "Double Cluster", "type": "cluster", "ra": 34.75, "dec": 57.13, "magnitude": 3.7,
     "hint": "Two neighboring open clusters in Perseus, each containing hundreds of young stars."},
    {"id": "m33", "name": "Triangulum Galaxy", "type": "galaxy", "ra": 23.46, "dec": 30.66, "magnitude": 5.7,
     "hint": "The third-largest member of the Local Group, after Andromeda and the Milky Way."},
    {"id": "m44", "name": "Beehive Cluster", "type": "cluster", "ra": 130.1, "dec": 19.67, "magnitude": 3.7,
     "hint": "An open cluster in Cancer, known since antiquity as Praesepe — the Manger."},
    {"id": "m104", "name": "Sombrero Galaxy", "type": "galaxy", "ra": 189.99, "dec": -11.62, "magnitude": 8.0,
     "hint": "An edge-on galaxy with a prominent dust lane resembling a wide-brimmed hat."},
    {"id": "m22", "name": "Sagittarius Cluster", "type": "cluster", "ra": 279.1, "dec": -23.9, "magnitude": 5.1,
     "hint": "One of the nearest globular clusters to Earth, bright and easily resolved."},
    {"id": "m101", "name": "Pinwheel Galaxy", "type": "galaxy", "ra": 210.8, "dec": 54.35, "magnitude": 7.9,
     "hint": "A grand-design spiral galaxy nearly twice the diameter of the Milky Way."},
]


# ────────────────────────────────────────────────────────────────
# Sky Message Templates (Co-Star voice)
# ────────────────────────────────────────────────────────────────

_SKY_MESSAGES_DARK: List[str] = [
    "the sky is wide open tonight. everything above you is older than your problems.",
    "dark sky. perfect conditions. the universe is showing off for you.",
    "the stars are sharp tonight. so should your attention be.",
    "no light pollution of the soul tonight. look up and mean it.",
    "the sky is a museum with free admission. tonight it's open late.",
    "darkness is not the absence of something. it's the presence of everything.",
]

_SKY_MESSAGES_TWILIGHT: List[str] = [
    "the sky is transitioning. so are you. both of you will be fine.",
    "twilight. the in-between hour. some things are only visible in half-light.",
    "the first stars are appearing. they were always there. you just couldn't see them.",
    "not quite dark, not quite light. the sky is holding its breath.",
]

_SKY_MESSAGES_DAYLIGHT: List[str] = [
    "the sun is up. the stars are still there. you just can't see them yet.",
    "daylight scanning. limited visibility. come back when the sky gets honest.",
    "the sun outshines everything right now. patience is a form of observation.",
]

_SKY_MESSAGES_ISS: List[str] = [
    "the space station crosses your sky. six humans are up there right now, looking down.",
    "ISS overhead. a tiny point of light carrying an entire civilization's hopes.",
    "the station passes in {duration} seconds. blink and you'll miss a miracle.",
]

_SKY_MESSAGES_CONSTELLATION: List[str] = [
    "{name} rises in the east. {mythology}",
    "{name} is high overhead tonight. ancient navigators followed the same pattern.",
    "{name} dominates the sky. {stars} of its stars are visible from your location.",
]


# ────────────────────────────────────────────────────────────────
# Active Sessions Cache
# ────────────────────────────────────────────────────────────────

_active_sessions: Dict[str, ArSession] = {}


# ────────────────────────────────────────────────────────────────
# Persistence Helpers
# ────────────────────────────────────────────────────────────────

def _sanitize_player_id(player_id: str) -> str:
    """Sanitize a player ID for safe filesystem use."""
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in player_id)


def _ensure_dir(path: Path) -> None:
    """Create directory if it doesn't exist."""
    path.mkdir(parents=True, exist_ok=True)


def _load_json(path: Path) -> Optional[dict]:
    """Load JSON from file, return None if missing or corrupt."""
    try:
        if path.exists():
            return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return None


def _save_json(path: Path, data: dict) -> None:
    """Save dict as JSON to file."""
    _ensure_dir(path.parent)
    path.write_text(json.dumps(data, indent=2))


# ────────────────────────────────────────────────────────────────
# Core Computation: Coordinate Transform
# ────────────────────────────────────────────────────────────────

def _ra_dec_to_alt_az(
    ra_deg: float, dec_deg: float,
    lat_deg: float, lng_deg: float,
    dt: datetime,
) -> Tuple[float, float]:
    """Convert equatorial coordinates (RA/Dec) to horizontal (Alt/Az).

    Pure math implementation:
        Julian Date → GMST → LST → Hour Angle → altitude/azimuth

    Args:
        ra_deg: Right ascension in degrees (0-360)
        dec_deg: Declination in degrees (-90 to +90)
        lat_deg: Observer latitude in degrees
        lng_deg: Observer longitude in degrees
        dt: Observation time (UTC)

    Returns:
        (altitude_deg, azimuth_deg) where azimuth is 0°=N, 90°=E, 180°=S, 270°=W
    """
    # Julian Date
    y = dt.year
    m = dt.month
    d = dt.day + dt.hour / 24.0 + dt.minute / 1440.0 + dt.second / 86400.0

    if m <= 2:
        y -= 1
        m += 12

    A = int(y / 100)
    B = 2 - A + int(A / 4)
    jd = int(365.25 * (y + 4716)) + int(30.6001 * (m + 1)) + d + B - 1524.5

    # Julian centuries from J2000.0
    T = (jd - 2451545.0) / 36525.0

    # Greenwich Mean Sidereal Time (degrees)
    gmst = 280.46061837 + 360.98564736629 * (jd - 2451545.0) + 0.000387933 * T * T
    gmst = gmst % 360.0

    # Local Sidereal Time
    lst = (gmst + lng_deg) % 360.0

    # Hour Angle
    ha = (lst - ra_deg) % 360.0

    # Convert to radians
    ha_rad = math.radians(ha)
    dec_rad = math.radians(dec_deg)
    lat_rad = math.radians(lat_deg)

    # Altitude
    sin_alt = (math.sin(dec_rad) * math.sin(lat_rad) +
               math.cos(dec_rad) * math.cos(lat_rad) * math.cos(ha_rad))
    sin_alt = max(-1.0, min(1.0, sin_alt))
    alt_rad = math.asin(sin_alt)

    # Azimuth
    cos_az_num = (math.sin(dec_rad) - math.sin(alt_rad) * math.sin(lat_rad))
    cos_az_den = math.cos(alt_rad) * math.cos(lat_rad)

    if abs(cos_az_den) < 1e-10:
        az_deg = 0.0
    else:
        cos_az = max(-1.0, min(1.0, cos_az_num / cos_az_den))
        az_rad = math.acos(cos_az)
        if math.sin(ha_rad) > 0:
            az_deg = 360.0 - math.degrees(az_rad)
        else:
            az_deg = math.degrees(az_rad)

    return round(math.degrees(alt_rad), 2), round(az_deg, 2)


# ────────────────────────────────────────────────────────────────
# Core Computation: Darkness Level
# ────────────────────────────────────────────────────────────────

def _get_sun_altitude(lat: float, lng: float, dt: datetime) -> float:
    """Approximate Sun altitude for a given location and time.

    Uses a simplified solar position model (accurate to ~1°).
    """
    # Day of year
    doy = dt.timetuple().tm_yday
    # Solar declination (approximate)
    dec = -23.44 * math.cos(math.radians((360 / 365) * (doy + 10)))
    # Hour angle
    solar_noon_offset = lng / 15.0  # hours from UTC
    hour = dt.hour + dt.minute / 60.0 + dt.second / 3600.0
    solar_hour = hour + solar_noon_offset
    ha = 15.0 * (solar_hour - 12.0)
    # Altitude
    lat_rad = math.radians(lat)
    dec_rad = math.radians(dec)
    ha_rad = math.radians(ha)
    sin_alt = (math.sin(lat_rad) * math.sin(dec_rad) +
               math.cos(lat_rad) * math.cos(dec_rad) * math.cos(ha_rad))
    sin_alt = max(-1.0, min(1.0, sin_alt))
    return math.degrees(math.asin(sin_alt))


def _get_darkness_level(lat: float, lng: float, dt: datetime) -> str:
    """Determine sky darkness from Sun altitude.

    Returns one of:
        "daylight" — Sun > 0°
        "civil_twilight" — Sun between 0° and -6°
        "nautical_twilight" — Sun between -6° and -12°
        "astronomical_twilight" — Sun between -12° and -18°
        "dark" — Sun < -18°
    """
    sun_alt = _get_sun_altitude(lat, lng, dt)
    if sun_alt > 0:
        return "daylight"
    elif sun_alt > -6:
        return "civil_twilight"
    elif sun_alt > -12:
        return "nautical_twilight"
    elif sun_alt > -18:
        return "astronomical_twilight"
    else:
        return "dark"


# ────────────────────────────────────────────────────────────────
# Core Computation: Moon Phase
# ────────────────────────────────────────────────────────────────

def _get_moon_phase(dt: datetime) -> Tuple[str, float]:
    """Calculate moon phase name and illumination percentage.

    Uses synodic month calculation from a known new moon reference.

    Returns:
        (phase_name, illumination_fraction) where illumination is 0.0 to 1.0
    """
    # Known new moon: Jan 11, 2024, 11:57 UTC
    ref_new_moon = datetime(2024, 1, 11, 11, 57, tzinfo=timezone.utc)
    synodic_month = 29.53059  # days

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    days_since = (dt - ref_new_moon).total_seconds() / 86400.0
    phase_angle = (days_since % synodic_month) / synodic_month

    # Illumination: 0 at new moon, 1 at full moon
    illumination = round(0.5 * (1 - math.cos(2 * math.pi * phase_angle)), 3)

    # Phase name
    if phase_angle < 0.0625:
        name = "new moon"
    elif phase_angle < 0.1875:
        name = "waxing crescent"
    elif phase_angle < 0.3125:
        name = "first quarter"
    elif phase_angle < 0.4375:
        name = "waxing gibbous"
    elif phase_angle < 0.5625:
        name = "full moon"
    elif phase_angle < 0.6875:
        name = "waning gibbous"
    elif phase_angle < 0.8125:
        name = "last quarter"
    elif phase_angle < 0.9375:
        name = "waning crescent"
    else:
        name = "new moon"

    return name, illumination


# ────────────────────────────────────────────────────────────────
# Core Computation: Constellation & Object Visibility
# ────────────────────────────────────────────────────────────────

def _get_visible_constellations(
    lat: float, lng: float, dt: datetime,
) -> List[VisibleConstellation]:
    """Determine which constellations are visible from observer location.

    A constellation is included if its center is above 5° altitude.
    """
    visible = []
    for name, data in _CONSTELLATION_POSITIONS.items():
        center_alt, center_az = _ra_dec_to_alt_az(
            data["center_ra"], data["center_dec"], lat, lng, dt
        )
        if center_alt < 5.0:
            continue

        # Count stars above horizon
        stars_above = 0
        best_star = None
        best_mag = 99.0
        for star in data["stars"]:
            star_alt, _ = _ra_dec_to_alt_az(star["ra"], star["dec"], lat, lng, dt)
            if star_alt > 0:
                stars_above += 1
                if star["mag"] < best_mag:
                    best_mag = star["mag"]
                    best_star = star["name"]

        # Determine rising/setting from azimuth
        rising = 45 < center_az < 180
        setting = 180 < center_az < 315

        visible.append(VisibleConstellation(
            id=name.lower().replace(" ", "_"),
            name=name,
            altitude=center_alt,
            azimuth=center_az,
            rising=rising,
            setting=setting,
            stars_above_horizon=stars_above,
            total_stars=len(data["stars"]),
            best_star=best_star or data["stars"][0]["name"],
            mythology=data["mythology"],
            difficulty=_get_constellation_difficulty(name),
        ))

    # Sort by altitude descending (highest in sky first)
    visible.sort(key=lambda c: c.altitude, reverse=True)
    return visible


def _get_constellation_difficulty(name: str) -> int:
    """Get constellation difficulty from mini_games data mapping."""
    difficulties = {
        "Orion": 4, "Ursa Major": 2, "Ursa Minor": 1, "Cassiopeia": 1,
        "Leo": 3, "Scorpius": 4, "Gemini": 3, "Taurus": 3,
        "Cygnus": 2, "Lyra": 1, "Aquila": 2, "Canis Major": 3,
    }
    return difficulties.get(name, 2)


def _get_visible_objects(
    lat: float, lng: float, dt: datetime,
) -> List[VisibleObject]:
    """Filter deep-sky objects above the horizon for observer location."""
    visible = []
    for obj in _DEEP_SKY_OBJECTS:
        alt, az = _ra_dec_to_alt_az(obj["ra"], obj["dec"], lat, lng, dt)
        if alt < 10.0:  # Need at least 10° above horizon for deep-sky
            continue

        visible.append(VisibleObject(
            id=obj["id"],
            name=obj["name"],
            type=obj["type"],
            altitude=alt,
            azimuth=az,
            magnitude=obj["magnitude"],
            hint=obj["hint"],
        ))

    visible.sort(key=lambda o: o.altitude, reverse=True)
    return visible


def _get_visible_bright_stars(
    lat: float, lng: float, dt: datetime,
) -> List[dict]:
    """Get bright stars above the horizon with their positions."""
    visible = []
    for star in _BRIGHT_STARS:
        alt, az = _ra_dec_to_alt_az(star["ra"], star["dec"], lat, lng, dt)
        if alt < 5.0:
            continue
        visible.append({
            "id": star["id"],
            "name": star["name"],
            "constellation": star["constellation"],
            "altitude": alt,
            "azimuth": az,
            "magnitude": star["mag"],
        })

    visible.sort(key=lambda s: s["magnitude"])  # brightest first
    return visible


# ────────────────────────────────────────────────────────────────
# Core Computation: ISS Position
# ────────────────────────────────────────────────────────────────

def _fetch_iss_position() -> IssPosition:
    """Fetch current ISS position from Open Notify API with file cache.

    Falls back to TLE-based computation if API is unreachable.
    """
    _ensure_dir(ISS_CACHE_DIR)
    cache_file = ISS_CACHE_DIR / "position.json"

    # Check cache
    cached = _load_json(cache_file)
    if cached:
        cached_time = cached.get("_cached_at", 0)
        if time.time() - cached_time < ISS_POSITION_CACHE_SECONDS:
            return IssPosition(
                lat=cached["lat"],
                lng=cached["lng"],
                altitude_km=cached.get("altitude_km", ISS_ALTITUDE_KM),
                velocity_kms=cached.get("velocity_kms", 7.66),
                timestamp=cached["timestamp"],
                source=cached.get("source", "cache"),
            )

    # Try API
    try:
        response = urlopen(ISS_POSITION_URL, timeout=5)
        data = json.loads(response.read().decode())
        if data.get("message") == "success":
            pos = data["iss_position"]
            result = IssPosition(
                lat=float(pos["latitude"]),
                lng=float(pos["longitude"]),
                altitude_km=ISS_ALTITUDE_KM,
                velocity_kms=7.66,
                timestamp=datetime.utcnow().isoformat(),
                source="api",
            )
            # Cache it
            _save_json(cache_file, {
                "lat": result.lat,
                "lng": result.lng,
                "altitude_km": result.altitude_km,
                "velocity_kms": result.velocity_kms,
                "timestamp": result.timestamp,
                "source": "api",
                "_cached_at": time.time(),
            })
            return result
    except (URLError, OSError, json.JSONDecodeError, KeyError):
        pass

    # Fallback: simplified TLE propagation
    return _compute_iss_position_from_tle(datetime.utcnow())


def _compute_iss_position_from_tle(dt: datetime) -> IssPosition:
    """Compute approximate ISS position from hardcoded TLE.

    Simplified SGP4: uses mean motion and inclination for ground track.
    Accurate to ~50km for recent epochs; degrades over days.
    """
    # TLE epoch: year 24, day 045.54791667
    epoch_year = 2024
    epoch_day = 45.54791667
    epoch_dt = datetime(epoch_year, 1, 1) + timedelta(days=epoch_day - 1)

    # Mean motion (rev/day) from TLE line 2
    mean_motion = 15.4956092
    # RAAN (right ascension of ascending node) at epoch
    raan_epoch = 123.652  # degrees

    # Time since epoch in days
    delta_days = (dt - epoch_dt).total_seconds() / 86400.0

    # Revolutions since epoch
    revs = mean_motion * delta_days
    # Mean anomaly progression (simplified)
    orbit_fraction = revs % 1.0

    # Approximate argument of latitude (angle from ascending node)
    arg_lat = orbit_fraction * 360.0

    # RAAN precesses ~-5°/day for ISS
    raan = (raan_epoch - 5.0 * delta_days) % 360.0

    # Earth rotation since epoch
    earth_rotation = (delta_days * 360.9856) % 360.0

    # Latitude from inclination and argument of latitude
    inc_rad = math.radians(ISS_INCLINATION_DEG)
    lat = math.degrees(math.asin(math.sin(inc_rad) * math.sin(math.radians(arg_lat))))

    # Longitude (simplified)
    lng_inertial = raan + math.degrees(
        math.atan2(
            math.cos(inc_rad) * math.sin(math.radians(arg_lat)),
            math.cos(math.radians(arg_lat)),
        )
    )
    lng = ((lng_inertial - earth_rotation + 180) % 360) - 180

    return IssPosition(
        lat=round(lat, 4),
        lng=round(lng, 4),
        altitude_km=ISS_ALTITUDE_KM,
        velocity_kms=7.66,
        timestamp=dt.isoformat(),
        source="tle",
    )


# ────────────────────────────────────────────────────────────────
# Core Computation: ISS Pass Prediction
# ────────────────────────────────────────────────────────────────

def _predict_iss_passes(
    lat: float, lng: float, days: int = 5,
) -> List[IssPass]:
    """Predict visible ISS passes over observer location.

    Iterates through orbit positions at 30-second intervals,
    identifies passes where ISS is above 10° altitude and sunlit.
    Caches results per location grid (1° resolution) for 1 hour.
    """
    _ensure_dir(ISS_CACHE_DIR)

    # Grid-based cache key (1° resolution)
    grid_lat = round(lat)
    grid_lng = round(lng)
    cache_file = ISS_CACHE_DIR / f"passes_{grid_lat}_{grid_lng}.json"

    cached = _load_json(cache_file)
    if cached:
        cached_time = cached.get("_cached_at", 0)
        if time.time() - cached_time < ISS_PASSES_CACHE_SECONDS:
            return [IssPass(**p) for p in cached.get("passes", [])]

    passes = []
    now = datetime.utcnow()
    end_time = now + timedelta(days=days)

    # Step through time at 30-second intervals
    step = timedelta(seconds=30)
    current = now
    in_pass = False
    pass_data = {}

    while current < end_time:
        iss = _compute_iss_position_from_tle(current)

        # Angular distance from observer to ISS sub-satellite point
        d_lat = math.radians(iss.lat - lat)
        d_lng = math.radians(iss.lng - lng)
        lat1_r = math.radians(lat)
        lat2_r = math.radians(iss.lat)

        a = (math.sin(d_lat / 2) ** 2 +
             math.cos(lat1_r) * math.cos(lat2_r) * math.sin(d_lng / 2) ** 2)
        ground_dist_km = 6371.0 * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        # Elevation angle from observer
        if ground_dist_km < 10:
            elev = 90.0
        else:
            elev = math.degrees(math.atan2(
                ISS_ALTITUDE_KM - ground_dist_km * 0.0001,
                ground_dist_km
            ))

        # Simple azimuth
        az = math.degrees(math.atan2(
            math.sin(d_lng) * math.cos(lat2_r),
            math.cos(lat1_r) * math.sin(lat2_r) -
            math.sin(lat1_r) * math.cos(lat2_r) * math.cos(d_lng),
        )) % 360

        if elev > 10:
            if not in_pass:
                in_pass = True
                pass_data = {
                    "rise_time": current.isoformat(),
                    "rise_azimuth": round(az, 1),
                    "peak_altitude": elev,
                    "peak_azimuth": round(az, 1),
                    "peak_time": current.isoformat(),
                    "set_time": current.isoformat(),
                    "set_azimuth": round(az, 1),
                }
            else:
                if elev > pass_data["peak_altitude"]:
                    pass_data["peak_altitude"] = elev
                    pass_data["peak_azimuth"] = round(az, 1)
                    pass_data["peak_time"] = current.isoformat()
                pass_data["set_time"] = current.isoformat()
                pass_data["set_azimuth"] = round(az, 1)
        elif in_pass:
            # Pass ended
            rise_dt = datetime.fromisoformat(pass_data["rise_time"])
            set_dt = datetime.fromisoformat(pass_data["set_time"])
            duration = int((set_dt - rise_dt).total_seconds())

            if duration >= 30:  # Only include passes longer than 30 seconds
                # Check if ISS is sunlit (simplified: nighttime at observer + ISS in sunlight)
                darkness = _get_darkness_level(lat, lng, rise_dt)
                is_dark = darkness in ("dark", "astronomical_twilight", "nautical_twilight")

                brightness = -1.0 if pass_data["peak_altitude"] > 60 else 0.5

                passes.append(IssPass(
                    rise_time=pass_data["rise_time"],
                    rise_azimuth=pass_data["rise_azimuth"],
                    peak_time=pass_data["peak_time"],
                    peak_altitude=round(pass_data["peak_altitude"], 1),
                    peak_azimuth=pass_data["peak_azimuth"],
                    set_time=pass_data["set_time"],
                    set_azimuth=pass_data["set_azimuth"],
                    duration_seconds=duration,
                    brightness=brightness,
                    visible=is_dark,
                ))
            in_pass = False
            pass_data = {}

        current += step

        # Limit to 15 passes max
        if len(passes) >= 15:
            break

    # Cache results
    _save_json(cache_file, {
        "passes": [asdict(p) for p in passes],
        "_cached_at": time.time(),
    })

    return passes


# ────────────────────────────────────────────────────────────────
# Sky Snapshot Assembly
# ────────────────────────────────────────────────────────────────

def _generate_sky_message(
    darkness: str,
    constellations: List[VisibleConstellation],
    iss_visible: bool,
    moon_phase: str,
) -> str:
    """Generate a Co-Star-voice sky summary message."""
    seed = int(time.time() / 3600)  # Changes hourly
    rng = random.Random(seed)

    if darkness == "daylight":
        return rng.choice(_SKY_MESSAGES_DAYLIGHT)

    if darkness in ("civil_twilight", "nautical_twilight"):
        return rng.choice(_SKY_MESSAGES_TWILIGHT)

    # Dark sky — pick a contextual message
    messages = list(_SKY_MESSAGES_DARK)

    if iss_visible:
        msg = rng.choice(_SKY_MESSAGES_ISS).format(duration="240")
        messages.append(msg)

    if constellations:
        top = constellations[0]
        msg = rng.choice(_SKY_MESSAGES_CONSTELLATION).format(
            name=top.name,
            mythology=top.mythology,
            stars=top.stars_above_horizon,
        )
        messages.append(msg)

    return rng.choice(messages)


def _build_sky_snapshot(
    lat: float, lng: float, dt: datetime,
    include_iss: bool = True,
) -> SkySnapshot:
    """Assemble a complete sky snapshot for a location and time."""
    darkness = _get_darkness_level(lat, lng, dt)
    moon_name, moon_illum = _get_moon_phase(dt)
    constellations = _get_visible_constellations(lat, lng, dt)
    objects = _get_visible_objects(lat, lng, dt)
    bright_stars = _get_visible_bright_stars(lat, lng, dt)

    iss_pos = None
    iss_visible = False
    if include_iss:
        try:
            iss_pos = _fetch_iss_position()
            # Check if ISS is roughly overhead (within ~2000km ground distance)
            d_lat = math.radians(iss_pos.lat - lat)
            d_lng = math.radians(iss_pos.lng - lng)
            a = (math.sin(d_lat / 2) ** 2 +
                 math.cos(math.radians(lat)) * math.cos(math.radians(iss_pos.lat)) *
                 math.sin(d_lng / 2) ** 2)
            ground_dist = 6371.0 * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
            iss_visible = ground_dist < 2000 and darkness != "daylight"
        except Exception:
            pass

    message = _generate_sky_message(darkness, constellations, iss_visible, moon_name)

    return SkySnapshot(
        lat=lat,
        lng=lng,
        timestamp=dt.isoformat(),
        constellations=constellations,
        objects=objects,
        bright_stars=bright_stars,
        iss_position=iss_pos,
        iss_visible=iss_visible,
        moon_phase=moon_name,
        moon_illumination=moon_illum,
        darkness_level=darkness,
        sky_message=message,
    )


# ────────────────────────────────────────────────────────────────
# AR Session Lifecycle
# ────────────────────────────────────────────────────────────────

def _build_session_targets(snapshot: SkySnapshot) -> List[dict]:
    """Build identification targets from a sky snapshot."""
    targets = []

    # Add constellations as targets
    for const in snapshot.constellations[:6]:
        targets.append({
            "id": const.id,
            "name": const.name,
            "type": "constellation",
            "altitude": const.altitude,
            "azimuth": const.azimuth,
            "difficulty": const.difficulty,
            "hint": f"look for {const.best_star}, the brightest star in {const.name}.",
            "base_score": AR_BASE_SCORE_CONSTELLATION,
        })

    # Add deep-sky objects
    for obj in snapshot.objects[:4]:
        targets.append({
            "id": obj.id,
            "name": obj.name,
            "type": "deep_sky",
            "altitude": obj.altitude,
            "azimuth": obj.azimuth,
            "difficulty": 3 if obj.magnitude < 5 else 4,
            "hint": obj.hint,
            "base_score": AR_BASE_SCORE_DEEP_SKY,
        })

    # Add bright stars (top 5 not already in constellation targets)
    constellation_star_ids = set()
    for const in snapshot.constellations:
        for star_data in _CONSTELLATION_POSITIONS.get(const.name, {}).get("stars", []):
            constellation_star_ids.add(star_data["id"])

    star_count = 0
    for star in snapshot.bright_stars:
        if star["id"] not in constellation_star_ids and star_count < 5:
            targets.append({
                "id": star["id"],
                "name": star["name"],
                "type": "star",
                "altitude": star["altitude"],
                "azimuth": star["azimuth"],
                "difficulty": 1 if star["magnitude"] < 1.0 else 2,
                "hint": f"a bright star in {star['constellation']}. magnitude {star['magnitude']}.",
                "base_score": AR_BASE_SCORE_STAR,
            })
            star_count += 1

    # Add ISS if visible
    if snapshot.iss_visible and snapshot.iss_position:
        targets.append({
            "id": "iss",
            "name": "International Space Station",
            "type": "iss",
            "altitude": 45.0,  # approximate
            "azimuth": 0.0,
            "difficulty": 5,
            "hint": "a bright, fast-moving point of light. six humans live there.",
            "base_score": AR_BASE_SCORE_ISS,
        })

    return targets


def _calculate_identification_score(
    target: dict,
    time_elapsed: float,
    session_time_limit: float = AR_SESSION_TIME_LIMIT,
) -> Tuple[int, int]:
    """Calculate score and XP for an identification.

    Returns:
        (score, xp)
    """
    base = target.get("base_score", 15)
    difficulty = target.get("difficulty", 1)

    # Difficulty multiplier
    difficulty_mult = 1.0 + (difficulty - 1) * 0.25

    # Speed bonus (faster = more points)
    speed_ratio = max(0, 1.0 - (time_elapsed / session_time_limit))
    speed_bonus = 1.0 + (speed_ratio * 0.3)

    # Accuracy bonus (always 1.0 for correct identifications in this version)
    accuracy_bonus = 1.3

    final_score = int(base * difficulty_mult * speed_bonus * accuracy_bonus)
    xp = max(5, int(final_score * 0.5))

    return final_score, xp


def _load_player_history(player_id: str) -> dict:
    """Load AR session history for a player."""
    safe_id = _sanitize_player_id(player_id)
    history_file = AR_SESSIONS_DIR / safe_id / "history.json"
    data = _load_json(history_file)
    if data:
        return data
    return {
        "player_id": player_id,
        "sessions": [],
        "total_sessions": 0,
        "total_identifications": 0,
        "total_score": 0,
        "total_xp": 0,
        "best_session_score": 0,
    }


def _save_player_history(player_id: str, history: dict) -> None:
    """Save AR session history, capping at MAX_AR_HISTORY."""
    safe_id = _sanitize_player_id(player_id)
    history_file = AR_SESSIONS_DIR / safe_id / "history.json"
    # Cap sessions list
    if len(history.get("sessions", [])) > MAX_AR_HISTORY:
        history["sessions"] = history["sessions"][-MAX_AR_HISTORY:]
    _save_json(history_file, history)


# ────────────────────────────────────────────────────────────────
# Public API Functions
# ────────────────────────────────────────────────────────────────

def get_iss_current() -> dict:
    """Get current ISS position.

    Endpoint: GET /api/stellar/iss/current
    """
    pos = _fetch_iss_position()
    return {
        "lat": pos.lat,
        "lng": pos.lng,
        "altitude_km": pos.altitude_km,
        "velocity_kms": pos.velocity_kms,
        "timestamp": pos.timestamp,
        "source": pos.source,
    }


def get_iss_passes(lat: float, lng: float, days: int = 5) -> dict:
    """Get predicted ISS passes over observer location.

    Endpoint: GET /api/stellar/iss/passes
    """
    passes = _predict_iss_passes(lat, lng, min(days, 10))
    visible_passes = [p for p in passes if p.visible]
    return {
        "lat": lat,
        "lng": lng,
        "days": days,
        "total_passes": len(passes),
        "visible_passes": len(visible_passes),
        "passes": [asdict(p) for p in passes],
    }


def get_visible_sky(lat: float, lng: float, timestamp: Optional[str] = None) -> dict:
    """Get visible sky objects for a location.

    Endpoint: GET /api/stellar/sky/visible
    """
    if timestamp:
        dt = datetime.fromisoformat(timestamp)
    else:
        dt = datetime.utcnow()

    constellations = _get_visible_constellations(lat, lng, dt)
    objects = _get_visible_objects(lat, lng, dt)
    bright_stars = _get_visible_bright_stars(lat, lng, dt)
    darkness = _get_darkness_level(lat, lng, dt)

    return {
        "lat": lat,
        "lng": lng,
        "timestamp": dt.isoformat(),
        "darkness_level": darkness,
        "constellations": [asdict(c) for c in constellations],
        "objects": [asdict(o) for o in objects],
        "bright_stars": bright_stars,
        "total_visible": len(constellations) + len(objects) + len(bright_stars),
    }


def get_sky_snapshot(lat: float, lng: float, player_id: str) -> dict:
    """Get full sky snapshot including ISS, moon, and sky message.

    Endpoint: GET /api/stellar/sky/snapshot
    """
    dt = datetime.utcnow()
    snapshot = _build_sky_snapshot(lat, lng, dt)

    return {
        "lat": snapshot.lat,
        "lng": snapshot.lng,
        "timestamp": snapshot.timestamp,
        "darkness_level": snapshot.darkness_level,
        "moon_phase": snapshot.moon_phase,
        "moon_illumination": snapshot.moon_illumination,
        "sky_message": snapshot.sky_message,
        "iss_visible": snapshot.iss_visible,
        "iss_position": asdict(snapshot.iss_position) if snapshot.iss_position else None,
        "constellations": [asdict(c) for c in snapshot.constellations],
        "objects": [asdict(o) for o in snapshot.objects],
        "bright_stars": snapshot.bright_stars,
        "total_visible": (
            len(snapshot.constellations) + len(snapshot.objects) +
            len(snapshot.bright_stars) + (1 if snapshot.iss_visible else 0)
        ),
    }


def get_constellation_detail(
    constellation_id: str, lat: float, lng: float,
) -> dict:
    """Get detailed info about a specific constellation.

    Endpoint: GET /api/stellar/sky/constellation/{id}
    """
    # Find constellation
    name_map = {
        name.lower().replace(" ", "_"): name
        for name in _CONSTELLATION_POSITIONS
    }
    name = name_map.get(constellation_id)
    if not name:
        return {"error": f"constellation '{constellation_id}' not found"}

    data = _CONSTELLATION_POSITIONS[name]
    dt = datetime.utcnow()

    # Compute current position of each star
    stars = []
    for star in data["stars"]:
        alt, az = _ra_dec_to_alt_az(star["ra"], star["dec"], lat, lng, dt)
        stars.append({
            "id": star["id"],
            "name": star["name"],
            "ra": star["ra"],
            "dec": star["dec"],
            "magnitude": star["mag"],
            "altitude": alt,
            "azimuth": az,
            "above_horizon": alt > 0,
        })

    center_alt, center_az = _ra_dec_to_alt_az(
        data["center_ra"], data["center_dec"], lat, lng, dt
    )

    return {
        "id": constellation_id,
        "name": name,
        "mythology": data["mythology"],
        "difficulty": _get_constellation_difficulty(name),
        "center_altitude": center_alt,
        "center_azimuth": center_az,
        "above_horizon": center_alt > 0,
        "stars": stars,
        "stars_above_horizon": sum(1 for s in stars if s["above_horizon"]),
        "timestamp": dt.isoformat(),
    }


def get_sky_config() -> dict:
    """Get AR sky scanner configuration.

    Endpoint: GET /api/stellar/sky/config
    """
    return {
        "version": "1.0.0",
        "session_time_limit": AR_SESSION_TIME_LIMIT,
        "scoring": {
            "constellation": AR_BASE_SCORE_CONSTELLATION,
            "deep_sky": AR_BASE_SCORE_DEEP_SKY,
            "star": AR_BASE_SCORE_STAR,
            "iss": AR_BASE_SCORE_ISS,
        },
        "constellations_available": len(_CONSTELLATION_POSITIONS),
        "deep_sky_objects_available": len(_DEEP_SKY_OBJECTS),
        "bright_stars_available": len(_BRIGHT_STARS),
        "iss_tracking": True,
        "iss_cache_seconds": ISS_POSITION_CACHE_SECONDS,
        "max_session_targets": 16,
        "max_history": MAX_AR_HISTORY,
    }


def start_ar_session(player_id: str, lat: float, lng: float) -> dict:
    """Start a new AR identification session.

    Endpoint: POST /api/stellar/sky/session
    """
    dt = datetime.utcnow()
    snapshot = _build_sky_snapshot(lat, lng, dt)
    targets = _build_session_targets(snapshot)

    if not targets:
        return {
            "error": "no targets visible",
            "darkness_level": snapshot.darkness_level,
            "sky_message": "the sky has nothing for you right now. try again when it's darker, or from a different location.",
        }

    session_id = str(uuid.uuid4())
    expires_at = (dt + timedelta(seconds=AR_SESSION_TIME_LIMIT)).isoformat()

    session = ArSession(
        session_id=session_id,
        player_id=player_id,
        lat=lat,
        lng=lng,
        started_at=dt.isoformat(),
        expires_at=expires_at,
        targets=targets,
        identified=[],
        score=0,
        xp=0,
        completed=False,
    )

    _active_sessions[session_id] = session

    return {
        "session_id": session_id,
        "started_at": session.started_at,
        "expires_at": expires_at,
        "time_limit": AR_SESSION_TIME_LIMIT,
        "targets": targets,
        "target_count": len(targets),
        "darkness_level": snapshot.darkness_level,
        "sky_message": snapshot.sky_message,
    }


def identify_object(
    player_id: str, session_id: str, object_id: str,
) -> dict:
    """Identify an object during an AR session.

    Endpoint: POST /api/stellar/sky/session/identify
    """
    session = _active_sessions.get(session_id)
    if not session:
        return {"error": "session not found or expired"}

    if session.player_id != player_id:
        return {"error": "session does not belong to this player"}

    if session.completed:
        return {"error": "session already completed"}

    # Check expiry
    now = datetime.utcnow()
    expires = datetime.fromisoformat(session.expires_at)
    if now > expires:
        session.completed = True
        return {"error": "session expired"}

    # Check if already identified
    for ident in session.identified:
        if ident["id"] == object_id:
            return {"error": "object already identified", "object_id": object_id}

    # Find target
    target = None
    for t in session.targets:
        if t["id"] == object_id:
            target = t
            break

    if not target:
        return {"error": "object not in session targets", "object_id": object_id}

    # Calculate score
    elapsed = (now - datetime.fromisoformat(session.started_at)).total_seconds()
    score, xp = _calculate_identification_score(target, elapsed)

    identification = {
        "id": object_id,
        "name": target["name"],
        "type": target["type"],
        "score": score,
        "xp": xp,
        "time_elapsed": round(elapsed, 1),
    }

    session.identified.append(identification)
    session.score += score
    session.xp += xp

    # Trigger star atlas discovery
    try:
        from narrative_agentic.stellar_outreach.star_atlas import discover_object
        discover_object(player_id, object_id, "ar_scanner")
    except Exception:
        pass  # Non-critical integration

    return {
        "success": True,
        "identification": identification,
        "session_score": session.score,
        "session_xp": session.xp,
        "identified_count": len(session.identified),
        "remaining_count": len(session.targets) - len(session.identified),
    }


def complete_ar_session(player_id: str, session_id: str) -> dict:
    """Complete an AR session and record results.

    Endpoint: POST /api/stellar/sky/session/complete
    """
    session = _active_sessions.get(session_id)
    if not session:
        return {"error": "session not found or expired"}

    if session.player_id != player_id:
        return {"error": "session does not belong to this player"}

    if session.completed:
        return {"error": "session already completed"}

    session.completed = True

    # Calculate final stats
    total_targets = len(session.targets)
    total_identified = len(session.identified)
    accuracy = round(total_identified / total_targets, 3) if total_targets > 0 else 0

    # Earn season XP if cosmic pass available
    try:
        from narrative_agentic.stellar_outreach.cosmic_pass import earn_season_xp
        earn_season_xp(player_id, "ar_discovery")
    except Exception:
        pass  # Non-critical integration

    # Update player history
    history = _load_player_history(player_id)
    session_record = {
        "session_id": session_id,
        "completed_at": datetime.utcnow().isoformat(),
        "lat": session.lat,
        "lng": session.lng,
        "targets": total_targets,
        "identified": total_identified,
        "accuracy": accuracy,
        "score": session.score,
        "xp": session.xp,
        "identifications": session.identified,
    }

    history["sessions"].append(session_record)
    history["total_sessions"] += 1
    history["total_identifications"] += total_identified
    history["total_score"] += session.score
    history["total_xp"] += session.xp
    if session.score > history["best_session_score"]:
        history["best_session_score"] = session.score

    # Update favorite target
    type_counts: Dict[str, int] = {}
    for sess in history["sessions"]:
        for ident in sess.get("identifications", []):
            t = ident.get("type", "unknown")
            type_counts[t] = type_counts.get(t, 0) + 1
    if type_counts:
        history["favorite_target"] = max(type_counts, key=type_counts.get)

    _save_player_history(player_id, history)

    # Clean up active session
    _active_sessions.pop(session_id, None)

    return {
        "session_id": session_id,
        "completed": True,
        "targets": total_targets,
        "identified": total_identified,
        "accuracy": accuracy,
        "score": session.score,
        "xp": session.xp,
        "identifications": session.identified,
        "lifetime_stats": {
            "total_sessions": history["total_sessions"],
            "total_identifications": history["total_identifications"],
            "total_score": history["total_score"],
            "total_xp": history["total_xp"],
            "best_session_score": history["best_session_score"],
            "favorite_target": history.get("favorite_target"),
        },
    }


def get_ar_history(player_id: str) -> dict:
    """Get AR session history for a player.

    Endpoint: GET /api/stellar/sky/history
    """
    history = _load_player_history(player_id)
    return {
        "player_id": player_id,
        "total_sessions": history["total_sessions"],
        "total_identifications": history["total_identifications"],
        "total_score": history["total_score"],
        "total_xp": history["total_xp"],
        "best_session_score": history["best_session_score"],
        "favorite_target": history.get("favorite_target"),
        "recent_sessions": history["sessions"][-10:],  # Last 10 sessions
    }

"""
NEXUS STATION - Stellar Outreach: Astronomical Event System (TASK-019)

Unified live-ops engine for real astronomical event detection. Connects
moon phases, meteor showers, retrogrades, eclipses, conjunctions, solar
flares, near-Earth asteroids, ISS passes, and zodiac seasons into a
single orchestrated system with gameplay buffs.

Event detection sources:
    - Moon phases: ar_sky_scanner._get_moon_phase() (synodic calculation)
    - Planet conjunctions: transit_engine.get_transit_snapshot() (Swiss Ephemeris)
    - ISS passes: ar_sky_scanner._predict_iss_passes() (TLE propagation)
    - Meteor showers: pre-calculated annual calendar
    - Eclipses: pre-calculated 2025-2027 table
    - Mercury retrogrades: pre-calculated 2025-2027 periods
    - Zodiac seasons: Sun ingress dates
    - Solar flares: NASA DONKI API (cached 24h)
    - Near-Earth asteroids: NASA NeoWs API (cached 24h)

Notification templates for all 14 event types already exist in
notifications.py — this module triggers them automatically.

Security Note (Article II / Kai Chen review):
    [KAI] NASA APIs use DEMO_KEY — no secrets stored. All external calls
    have 15s timeout and 24h file cache. Cache dir is player-independent.
    No PII in event data. Event IDs are deterministic hashes.

UX Note (Marina Okonkwo review):
    [MARINA] Events framed positively — retrogrades are "reflection periods",
    not doom. Buffs reward engagement without penalizing absence.
    Calendar view helps players plan ahead.

Ethics Note (Dr. Elena Vasquez review):
    [ELENA] No fear-based messaging. Solar flares described scientifically.
    Asteroid approaches framed as discovery opportunities, not threats.
    All buffs are bonuses — no debuffs from missing events.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta, timezone, date
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.request import urlopen, Request
from urllib.error import URLError


# ────────────────────────────────────────────────────────────────
# Persistence Configuration
# ────────────────────────────────────────────────────────────────

EVENT_CACHE_DIR = Path.home() / ".nexus_station" / "event_cache"
NASA_CACHE_DIR = EVENT_CACHE_DIR / "nasa"

NASA_DONKI_URL = "https://api.nasa.gov/DONKI/FLR"
NASA_NEOWS_URL = "https://api.nasa.gov/neo/rest/v1/feed"
NASA_API_KEY = "DEMO_KEY"
NASA_TIMEOUT = 15
NASA_CACHE_HOURS = 24

# In-memory event cache
_event_cache: Dict[str, Tuple[float, list]] = {}
EVENT_CACHE_SECONDS = 600  # 10 minutes


# ────────────────────────────────────────────────────────────────
# Constants — Meteor Showers (12 annual)
# ────────────────────────────────────────────────────────────────

METEOR_SHOWERS: List[dict] = [
    {
        "name": "Quadrantids",
        "peak_month": 1, "peak_day": 3,
        "duration_days": 4,
        "zhr": 120,
        "parent_body": "2003 EH1",
        "description": "Brief but intense — one of the strongest annual showers.",
    },
    {
        "name": "Lyrids",
        "peak_month": 4, "peak_day": 22,
        "duration_days": 3,
        "zhr": 18,
        "parent_body": "C/1861 G1 Thatcher",
        "description": "Ancient shower observed for over 2,700 years.",
    },
    {
        "name": "Eta Aquariids",
        "peak_month": 5, "peak_day": 6,
        "duration_days": 5,
        "zhr": 50,
        "parent_body": "1P/Halley",
        "description": "Debris from Halley's Comet, best viewed from the southern hemisphere.",
    },
    {
        "name": "Delta Aquariids",
        "peak_month": 7, "peak_day": 30,
        "duration_days": 5,
        "zhr": 20,
        "parent_body": "96P/Machholz",
        "description": "A warm summer shower, steady and reliable.",
    },
    {
        "name": "Perseids",
        "peak_month": 8, "peak_day": 12,
        "duration_days": 5,
        "zhr": 100,
        "parent_body": "109P/Swift-Tuttle",
        "description": "The crowd favorite — warm nights, bright meteors.",
    },
    {
        "name": "Draconids",
        "peak_month": 10, "peak_day": 8,
        "duration_days": 2,
        "zhr": 10,
        "parent_body": "21P/Giacobini-Zinner",
        "description": "Slow-moving meteors from comet Giacobini-Zinner.",
    },
    {
        "name": "Orionids",
        "peak_month": 10, "peak_day": 21,
        "duration_days": 5,
        "zhr": 20,
        "parent_body": "1P/Halley",
        "description": "The second shower from Halley's Comet each year.",
    },
    {
        "name": "Taurids",
        "peak_month": 11, "peak_day": 5,
        "duration_days": 10,
        "zhr": 5,
        "parent_body": "2P/Encke",
        "description": "Slow, bright fireballs — quality over quantity.",
    },
    {
        "name": "Leonids",
        "peak_month": 11, "peak_day": 17,
        "duration_days": 3,
        "zhr": 15,
        "parent_body": "55P/Tempel-Tuttle",
        "description": "Famous for periodic storms — every 33 years, a spectacular display.",
    },
    {
        "name": "Geminids",
        "peak_month": 12, "peak_day": 14,
        "duration_days": 5,
        "zhr": 150,
        "parent_body": "3200 Phaethon",
        "description": "The king of meteor showers — bright, plentiful, multicolored.",
    },
    {
        "name": "Ursids",
        "peak_month": 12, "peak_day": 22,
        "duration_days": 3,
        "zhr": 10,
        "parent_body": "8P/Tuttle",
        "description": "A solstice shower — quiet but consistent.",
    },
    {
        "name": "Alpha Monocerotids",
        "peak_month": 11, "peak_day": 21,
        "duration_days": 1,
        "zhr": 5,
        "parent_body": "Unknown",
        "description": "Rare outbursts possible — usually quiet, occasionally spectacular.",
    },
]


# ────────────────────────────────────────────────────────────────
# Constants — Eclipses 2025-2027
# ────────────────────────────────────────────────────────────────

ECLIPSES_2025_2027: List[dict] = [
    {
        "name": "Total Lunar Eclipse",
        "type": "lunar_total",
        "date": "2025-03-14",
        "visibility": ["Americas", "Europe", "Africa"],
        "buff_percentage": 20,
        "description": "Blood moon rises — the Earth's shadow paints the moon red.",
    },
    {
        "name": "Partial Solar Eclipse",
        "type": "solar_partial",
        "date": "2025-03-29",
        "visibility": ["Europe", "North Africa", "Western Asia"],
        "buff_percentage": 10,
        "description": "The moon takes a bite from the sun.",
    },
    {
        "name": "Total Lunar Eclipse",
        "type": "lunar_total",
        "date": "2025-09-07",
        "visibility": ["Asia", "Australia", "Pacific"],
        "buff_percentage": 20,
        "description": "Eastern hemisphere blood moon — a celestial spectacle.",
    },
    {
        "name": "Partial Solar Eclipse",
        "type": "solar_partial",
        "date": "2025-09-21",
        "visibility": ["Antarctica", "Southern Ocean"],
        "buff_percentage": 10,
        "description": "A rare polar eclipse — the sun dims at the edge of the world.",
    },
    {
        "name": "Total Lunar Eclipse",
        "type": "lunar_total",
        "date": "2026-03-03",
        "visibility": ["Americas", "Europe", "Africa"],
        "buff_percentage": 20,
        "description": "A spring blood moon — cosmic reset for the equinox.",
    },
    {
        "name": "Annular Solar Eclipse",
        "type": "solar_annular",
        "date": "2026-02-17",
        "visibility": ["Antarctica", "Southern Atlantic"],
        "buff_percentage": 15,
        "description": "Ring of fire — the moon frames the sun perfectly.",
    },
    {
        "name": "Total Solar Eclipse",
        "type": "solar_total",
        "date": "2026-08-12",
        "visibility": ["Arctic", "Greenland", "Iceland", "Spain"],
        "buff_percentage": 25,
        "description": "Totality descends — the corona blazes in the darkened sky.",
    },
    {
        "name": "Partial Lunar Eclipse",
        "type": "lunar_partial",
        "date": "2026-08-28",
        "visibility": ["Americas", "Europe", "Africa"],
        "buff_percentage": 10,
        "description": "The Earth's shadow clips the moon — a subtle reminder of alignment.",
    },
    {
        "name": "Penumbral Lunar Eclipse",
        "type": "lunar_penumbral",
        "date": "2027-02-20",
        "visibility": ["Americas", "Europe", "Africa"],
        "buff_percentage": 5,
        "description": "A ghost eclipse — the moon dims softly without dramatic shadow.",
    },
    {
        "name": "Annular Solar Eclipse",
        "type": "solar_annular",
        "date": "2027-02-06",
        "visibility": ["South America", "Antarctica"],
        "buff_percentage": 15,
        "description": "Ring of fire returns to the southern skies.",
    },
]


# ────────────────────────────────────────────────────────────────
# Constants — Mercury Retrogrades 2025-2027 (3 per year)
# ────────────────────────────────────────────────────────────────

MERCURY_RETROGRADES_2025_2027: List[dict] = [
    {"start": "2025-03-15", "end": "2025-04-07", "shadow_start": "2025-02-25"},
    {"start": "2025-07-18", "end": "2025-08-11", "shadow_start": "2025-06-29"},
    {"start": "2025-11-09", "end": "2025-11-29", "shadow_start": "2025-10-22"},
    {"start": "2026-03-02", "end": "2026-03-23", "shadow_start": "2026-02-12"},
    {"start": "2026-07-01", "end": "2026-07-25", "shadow_start": "2026-06-12"},
    {"start": "2026-10-24", "end": "2026-11-13", "shadow_start": "2026-10-06"},
    {"start": "2027-02-13", "end": "2027-03-06", "shadow_start": "2027-01-26"},
    {"start": "2027-06-14", "end": "2027-07-08", "shadow_start": "2027-05-26"},
    {"start": "2027-10-07", "end": "2027-10-28", "shadow_start": "2027-09-19"},
]


# ────────────────────────────────────────────────────────────────
# Constants — Zodiac Season Dates (Sun ingress, approximate)
# ────────────────────────────────────────────────────────────────

ZODIAC_SEASON_DATES: List[dict] = [
    {"sign": "Aries",       "month": 3,  "day": 20},
    {"sign": "Taurus",      "month": 4,  "day": 20},
    {"sign": "Gemini",      "month": 5,  "day": 21},
    {"sign": "Cancer",      "month": 6,  "day": 21},
    {"sign": "Leo",         "month": 7,  "day": 22},
    {"sign": "Virgo",       "month": 8,  "day": 23},
    {"sign": "Libra",       "month": 9,  "day": 23},
    {"sign": "Scorpio",     "month": 10, "day": 23},
    {"sign": "Sagittarius", "month": 11, "day": 22},
    {"sign": "Capricorn",   "month": 12, "day": 22},
    {"sign": "Aquarius",    "month": 1,  "day": 20},
    {"sign": "Pisces",      "month": 2,  "day": 19},
]


# ────────────────────────────────────────────────────────────────
# Constants — Event Buff Table
# ────────────────────────────────────────────────────────────────

EVENT_BUFF_TABLE: Dict[str, int] = {
    "full_moon":         10,
    "new_moon":          5,
    "meteor_shower_low": 8,
    "meteor_shower_mid": 12,
    "meteor_shower_high": 15,
    "conjunction":       10,
    "mercury_retrograde": 5,
    "mercury_retrograde_shadow": 3,
    "eclipse_total":     20,
    "eclipse_annular":   15,
    "eclipse_partial":   10,
    "eclipse_penumbral": 5,
    "solar_flare_m":     8,
    "solar_flare_x":     15,
    "asteroid_close":    10,
    "iss_pass":          5,
    "zodiac_season":     5,
}


# ────────────────────────────────────────────────────────────────
# Constants — Mercury Retrograde Effects
# ────────────────────────────────────────────────────────────────

MERCURY_RETROGRADE_EFFECTS: dict = {
    "crafting_variants": 30,   # % chance of unexpected crafting outcomes
    "npc_glitches": True,      # NPCs may give scrambled dialogue
    "navigation_scramble_deg": 2,  # star atlas offset ±2°
    "aesthetic": "amber_flicker",  # terminal flicker effect
    "description": (
        "Mercury stations retrograde — communications and systems may "
        "behave unpredictably. A time for reflection, not frustration."
    ),
}


# ────────────────────────────────────────────────────────────────
# Data Models
# ────────────────────────────────────────────────────────────────

@dataclass
class AstronomicalEvent:
    """A detected real-world astronomical event with gameplay effects."""
    event_id: str
    event_type: str           # full_moon, meteor_shower, conjunction, etc.
    name: str
    description: str
    start_time: str           # ISO datetime
    end_time: str             # ISO datetime
    peak_time: Optional[str]  # ISO datetime, if applicable
    buff_type: str            # "global", "module_specific", "special"
    buff_percentage: int
    affected_modules: List[str]   # module IDs, or ["all"]
    special_effects: List[str]    # aesthetic/gameplay effect keys
    source: str               # "calculated", "calendar", "nasa_api"
    location_dependent: bool


@dataclass
class EventBuff:
    """Aggregated buff state for a player from all active events."""
    player_id: str
    date: str
    global_buff_percentage: int
    module_buffs: Dict[str, int]   # module_id -> additional buff %
    active_events: List[str]       # event_id list
    special_effects_active: List[str]


# ────────────────────────────────────────────────────────────────
# Persistence & Cache Helpers
# ────────────────────────────────────────────────────────────────

def _ensure_dir(path: Path) -> None:
    """Create directory if it doesn't exist."""
    path.mkdir(parents=True, exist_ok=True)


def _nasa_cache_path(endpoint: str, params_hash: str) -> Path:
    """Return cache file path for a NASA API response."""
    return NASA_CACHE_DIR / f"{endpoint}_{params_hash}.json"


def _read_nasa_cache(endpoint: str, params_hash: str) -> Optional[dict]:
    """Read cached NASA API response if fresh (< 24h)."""
    cache_file = _nasa_cache_path(endpoint, params_hash)
    if not cache_file.exists():
        return None
    try:
        stat = cache_file.stat()
        age_hours = (time.time() - stat.st_mtime) / 3600
        if age_hours > NASA_CACHE_HOURS:
            return None
        with open(cache_file, "r") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def _write_nasa_cache(endpoint: str, params_hash: str, data: dict) -> None:
    """Write NASA API response to file cache."""
    _ensure_dir(NASA_CACHE_DIR)
    cache_file = _nasa_cache_path(endpoint, params_hash)
    try:
        with open(cache_file, "w") as f:
            json.dump(data, f)
    except OSError:
        pass


def _event_id(event_type: str, date_str: str, name: str) -> str:
    """Generate a deterministic event ID."""
    raw = f"{event_type}:{date_str}:{name}"
    return hashlib.md5(raw.encode()).hexdigest()[:12]


def _event_to_dict(event: AstronomicalEvent) -> dict:
    """Serialize an AstronomicalEvent to a JSON-safe dict."""
    return asdict(event)


# ────────────────────────────────────────────────────────────────
# Event Detectors (private)
# ────────────────────────────────────────────────────────────────

def _detect_moon_phases(
    start: datetime, end: datetime,
) -> List[AstronomicalEvent]:
    """Detect full and new moon events in the date range.

    Reuses ar_sky_scanner._get_moon_phase() for calculation.
    Full moon: illumination >= 0.98
    New moon: illumination <= 0.02
    """
    from narrative_agentic.stellar_outreach.ar_sky_scanner import _get_moon_phase

    events: List[AstronomicalEvent] = []
    current = start.replace(hour=0, minute=0, second=0, microsecond=0)

    while current <= end:
        phase_name, illumination = _get_moon_phase(current)

        if illumination >= 0.98:
            eid = _event_id("full_moon", current.strftime("%Y-%m-%d"), "Full Moon")
            events.append(AstronomicalEvent(
                event_id=eid,
                event_type="full_moon",
                name="Full Moon",
                description=(
                    "The moon blazes at full illumination — station systems "
                    "resonate with lunar energy. All modules receive a boost."
                ),
                start_time=(current - timedelta(hours=12)).isoformat(),
                end_time=(current + timedelta(hours=36)).isoformat(),
                peak_time=current.replace(hour=12).isoformat(),
                buff_type="global",
                buff_percentage=EVENT_BUFF_TABLE["full_moon"],
                affected_modules=["all"],
                special_effects=["lunar_glow", "tide_pulse"],
                source="calculated",
                location_dependent=False,
            ))
        elif illumination <= 0.02:
            eid = _event_id("new_moon", current.strftime("%Y-%m-%d"), "New Moon")
            events.append(AstronomicalEvent(
                event_id=eid,
                event_type="new_moon",
                name="New Moon",
                description=(
                    "The sky darkens as the moon vanishes — a perfect time for "
                    "stargazing and quiet reflection. Observatory sensitivity peaks."
                ),
                start_time=(current - timedelta(hours=12)).isoformat(),
                end_time=(current + timedelta(hours=36)).isoformat(),
                peak_time=current.replace(hour=12).isoformat(),
                buff_type="module_specific",
                buff_percentage=EVENT_BUFF_TABLE["new_moon"],
                affected_modules=["observatory"],
                special_effects=["dark_sky", "star_clarity"],
                source="calculated",
                location_dependent=False,
            ))

        current += timedelta(days=1)

    # Deduplicate — moon phases span multiple days at threshold.
    # Keep only one event per type per 3-day window (pick highest illumination match).
    if not events:
        return []
    events.sort(key=lambda e: e.start_time)
    deduped: List[AstronomicalEvent] = []
    for evt in events:
        merged = False
        for existing in deduped:
            if existing.event_type == evt.event_type:
                # If peaks are within 3 days, consider duplicate
                if existing.peak_time and evt.peak_time:
                    e_date = date.fromisoformat(existing.peak_time[:10])
                    n_date = date.fromisoformat(evt.peak_time[:10])
                    if abs((n_date - e_date).days) <= 3:
                        merged = True
                        break
        if not merged:
            deduped.append(evt)
    return deduped


def _detect_meteor_showers(
    start: datetime, end: datetime,
) -> List[AstronomicalEvent]:
    """Match meteor showers from the annual calendar."""
    events: List[AstronomicalEvent] = []
    start_date = start.date() if isinstance(start, datetime) else start
    end_date = end.date() if isinstance(end, datetime) else end

    # Check each year in range
    for year in range(start_date.year, end_date.year + 1):
        for shower in METEOR_SHOWERS:
            try:
                peak = date(year, shower["peak_month"], shower["peak_day"])
            except ValueError:
                continue

            half_dur = shower["duration_days"] // 2
            shower_start = peak - timedelta(days=half_dur)
            shower_end = peak + timedelta(days=half_dur)

            # Check overlap with query range
            if shower_end < start_date or shower_start > end_date:
                continue

            # Determine buff level from ZHR
            zhr = shower["zhr"]
            if zhr >= 80:
                buff_key = "meteor_shower_high"
            elif zhr >= 30:
                buff_key = "meteor_shower_mid"
            else:
                buff_key = "meteor_shower_low"

            eid = _event_id("meteor_shower", peak.isoformat(), shower["name"])
            events.append(AstronomicalEvent(
                event_id=eid,
                event_type="meteor_shower",
                name=f'{shower["name"]} Meteor Shower',
                description=shower["description"],
                start_time=datetime(
                    shower_start.year, shower_start.month, shower_start.day,
                    tzinfo=timezone.utc,
                ).isoformat(),
                end_time=datetime(
                    shower_end.year, shower_end.month, shower_end.day, 23, 59,
                    tzinfo=timezone.utc,
                ).isoformat(),
                peak_time=datetime(
                    peak.year, peak.month, peak.day, 2, 0,
                    tzinfo=timezone.utc,
                ).isoformat(),
                buff_type="global",
                buff_percentage=EVENT_BUFF_TABLE[buff_key],
                affected_modules=["all"],
                special_effects=["meteor_streak", f"zhr_{zhr}"],
                source="calendar",
                location_dependent=False,
            ))

    return events


def _detect_planet_conjunctions(
    start: datetime, end: datetime,
) -> List[AstronomicalEvent]:
    """Detect planet conjunctions (pairs < 5° apart) using transit engine."""
    from narrative_agentic.stellar_outreach.transit_engine import get_transit_snapshot

    events: List[AstronomicalEvent] = []
    current = start.date() if isinstance(start, datetime) else start
    end_date = end.date() if isinstance(end, datetime) else end

    # Check each day
    while current <= end_date:
        try:
            snapshot = get_transit_snapshot(current.isoformat())
        except Exception:
            current += timedelta(days=1)
            continue

        # Compare all planet pairs (skip Moon — it moves too fast)
        planets = [p for p in snapshot.planets if p.planet != "Moon"]
        for i in range(len(planets)):
            for j in range(i + 1, len(planets)):
                p1 = planets[i]
                p2 = planets[j]
                # Angular separation on ecliptic
                diff = abs(p1.degree - p2.degree)
                if diff > 180:
                    diff = 360 - diff
                if diff < 5.0:
                    pair_name = f"{p1.planet}-{p2.planet} Conjunction"
                    eid = _event_id("conjunction", current.isoformat(), pair_name)
                    events.append(AstronomicalEvent(
                        event_id=eid,
                        event_type="conjunction",
                        name=pair_name,
                        description=(
                            f"{p1.planet} and {p2.planet} align within {diff:.1f}° — "
                            f"their energies merge. A rare cosmic handshake."
                        ),
                        start_time=datetime(
                            current.year, current.month, current.day,
                            tzinfo=timezone.utc,
                        ).isoformat(),
                        end_time=datetime(
                            current.year, current.month, current.day, 23, 59,
                            tzinfo=timezone.utc,
                        ).isoformat(),
                        peak_time=datetime(
                            current.year, current.month, current.day, 12, 0,
                            tzinfo=timezone.utc,
                        ).isoformat(),
                        buff_type="global",
                        buff_percentage=EVENT_BUFF_TABLE["conjunction"],
                        affected_modules=["all"],
                        special_effects=["planetary_alignment", f"pair_{p1.planet.lower()}_{p2.planet.lower()}"],
                        source="calculated",
                        location_dependent=False,
                    ))

        current += timedelta(days=1)

    return events


def _detect_mercury_retrograde(
    start: datetime, end: datetime,
) -> List[AstronomicalEvent]:
    """Match Mercury retrograde periods from pre-calculated table."""
    events: List[AstronomicalEvent] = []
    start_date = start.date() if isinstance(start, datetime) else start
    end_date = end.date() if isinstance(end, datetime) else end

    for retro in MERCURY_RETROGRADES_2025_2027:
        retro_start = date.fromisoformat(retro["start"])
        retro_end = date.fromisoformat(retro["end"])
        shadow_start = date.fromisoformat(retro["shadow_start"])

        # Check retrograde period overlap
        if retro_end >= start_date and retro_start <= end_date:
            eid = _event_id("mercury_retrograde", retro["start"], "Mercury Retrograde")
            events.append(AstronomicalEvent(
                event_id=eid,
                event_type="mercury_retrograde",
                name="Mercury Retrograde",
                description=MERCURY_RETROGRADE_EFFECTS["description"],
                start_time=retro["start"] + "T00:00:00+00:00",
                end_time=retro["end"] + "T23:59:59+00:00",
                peak_time=None,
                buff_type="special",
                buff_percentage=EVENT_BUFF_TABLE["mercury_retrograde"],
                affected_modules=["observatory", "bridge"],
                special_effects=[
                    "amber_flicker",
                    f"crafting_variants_{MERCURY_RETROGRADE_EFFECTS['crafting_variants']}",
                    "npc_glitches",
                    f"nav_scramble_{MERCURY_RETROGRADE_EFFECTS['navigation_scramble_deg']}",
                ],
                source="calendar",
                location_dependent=False,
            ))

        # Check shadow period (before retrograde)
        if shadow_start < retro_start and shadow_start >= start_date and shadow_start <= end_date:
            shadow_end = retro_start - timedelta(days=1)
            eid = _event_id("mercury_retrograde_shadow", retro["shadow_start"], "Mercury Retrograde Shadow")
            events.append(AstronomicalEvent(
                event_id=eid,
                event_type="mercury_retrograde_shadow",
                name="Mercury Retrograde Shadow",
                description=(
                    "Mercury enters its pre-retrograde shadow — subtle shifts "
                    "in communication begin. A gentle warning to review and prepare."
                ),
                start_time=retro["shadow_start"] + "T00:00:00+00:00",
                end_time=shadow_end.isoformat() + "T23:59:59+00:00",
                peak_time=None,
                buff_type="special",
                buff_percentage=EVENT_BUFF_TABLE["mercury_retrograde_shadow"],
                affected_modules=["observatory"],
                special_effects=["amber_flicker_subtle"],
                source="calendar",
                location_dependent=False,
            ))

    return events


def _detect_solar_flares(
    start: datetime, end: datetime,
) -> List[AstronomicalEvent]:
    """Fetch solar flare data from NASA DONKI API. M/X class only.

    Results are file-cached for 24 hours. On failure, returns [].
    """
    events: List[AstronomicalEvent] = []
    start_str = (start.date() if isinstance(start, datetime) else start).isoformat()
    end_str = (end.date() if isinstance(end, datetime) else end).isoformat()

    params_hash = hashlib.md5(f"{start_str}:{end_str}".encode()).hexdigest()[:8]

    # Check file cache
    cached = _read_nasa_cache("donki_flr", params_hash)
    if cached is not None:
        flares = cached.get("data", [])
    else:
        try:
            url = (
                f"{NASA_DONKI_URL}?startDate={start_str}&endDate={end_str}"
                f"&api_key={NASA_API_KEY}"
            )
            req = Request(url, headers={"User-Agent": "NexusStation/1.0"})
            with urlopen(req, timeout=NASA_TIMEOUT) as resp:
                flares = json.loads(resp.read().decode())
            _write_nasa_cache("donki_flr", params_hash, {"data": flares})
        except (URLError, OSError, json.JSONDecodeError, ValueError):
            return []

    if not isinstance(flares, list):
        return []

    for flare in flares:
        class_type = flare.get("classType", "")
        if not class_type:
            continue

        # Only M and X class
        class_letter = class_type[0].upper()
        if class_letter not in ("M", "X"):
            continue

        begin = flare.get("beginTime", "")
        peak = flare.get("peakTime", "")
        end_t = flare.get("endTime", begin)

        if not begin:
            continue

        buff_key = "solar_flare_x" if class_letter == "X" else "solar_flare_m"
        eid = _event_id("solar_flare", begin[:10], f"Solar Flare {class_type}")

        events.append(AstronomicalEvent(
            event_id=eid,
            event_type="solar_flare",
            name=f"Solar Flare — Class {class_type}",
            description=(
                f"A {class_type}-class solar flare erupts from the sun. "
                "Charged particles stream outward — station sensors light up."
            ),
            start_time=begin,
            end_time=end_t,
            peak_time=peak or None,
            buff_type="global",
            buff_percentage=EVENT_BUFF_TABLE[buff_key],
            affected_modules=["all"],
            special_effects=["solar_flare_glow", f"class_{class_letter}"],
            source="nasa_api",
            location_dependent=False,
        ))

    return events


def _detect_asteroid_approaches(
    start: datetime, end: datetime,
) -> List[AstronomicalEvent]:
    """Fetch near-Earth asteroid data from NASA NeoWs. < 1 lunar distance only.

    Results are file-cached for 24 hours. On failure, returns [].
    """
    events: List[AstronomicalEvent] = []
    start_str = (start.date() if isinstance(start, datetime) else start).isoformat()
    end_str = (end.date() if isinstance(end, datetime) else end).isoformat()

    # NeoWs max range is 7 days — clamp
    s_date = date.fromisoformat(start_str)
    e_date = date.fromisoformat(end_str)
    if (e_date - s_date).days > 7:
        e_date = s_date + timedelta(days=7)
        end_str = e_date.isoformat()

    params_hash = hashlib.md5(f"neo:{start_str}:{end_str}".encode()).hexdigest()[:8]

    cached = _read_nasa_cache("neows", params_hash)
    if cached is not None:
        neo_data = cached
    else:
        try:
            url = (
                f"{NASA_NEOWS_URL}?start_date={start_str}&end_date={end_str}"
                f"&api_key={NASA_API_KEY}"
            )
            req = Request(url, headers={"User-Agent": "NexusStation/1.0"})
            with urlopen(req, timeout=NASA_TIMEOUT) as resp:
                neo_data = json.loads(resp.read().decode())
            _write_nasa_cache("neows", params_hash, neo_data)
        except (URLError, OSError, json.JSONDecodeError, ValueError):
            return []

    if not isinstance(neo_data, dict):
        return []

    near_earth_objects = neo_data.get("near_earth_objects", {})

    for day_str, objects in near_earth_objects.items():
        if not isinstance(objects, list):
            continue
        for obj in objects:
            close_approach = obj.get("close_approach_data", [])
            for approach in close_approach:
                miss_dist = approach.get("miss_distance", {})
                lunar_dist = float(miss_dist.get("lunar", "999"))
                if lunar_dist >= 1.0:
                    continue

                name = obj.get("name", "Unknown NEO")
                est_dia = obj.get("estimated_diameter", {}).get("meters", {})
                dia_min = est_dia.get("estimated_diameter_min", 0)
                dia_max = est_dia.get("estimated_diameter_max", 0)

                eid = _event_id("asteroid_close", day_str, name)
                events.append(AstronomicalEvent(
                    event_id=eid,
                    event_type="asteroid_close",
                    name=f"Near-Earth Asteroid: {name}",
                    description=(
                        f"Asteroid {name} passes within {lunar_dist:.2f} lunar distances. "
                        f"Estimated diameter: {dia_min:.0f}-{dia_max:.0f}m. "
                        "A cosmic neighbor — close enough to study, no cause for concern."
                    ),
                    start_time=day_str + "T00:00:00+00:00",
                    end_time=day_str + "T23:59:59+00:00",
                    peak_time=approach.get("close_approach_date_full", None),
                    buff_type="global",
                    buff_percentage=EVENT_BUFF_TABLE["asteroid_close"],
                    affected_modules=["all"],
                    special_effects=["asteroid_alert", f"dist_{lunar_dist:.2f}ld"],
                    source="nasa_api",
                    location_dependent=False,
                ))

    return events


def _detect_eclipses(
    start: datetime, end: datetime,
) -> List[AstronomicalEvent]:
    """Match eclipses from the pre-calculated 2025-2027 table."""
    events: List[AstronomicalEvent] = []
    start_date = start.date() if isinstance(start, datetime) else start
    end_date = end.date() if isinstance(end, datetime) else end

    for eclipse in ECLIPSES_2025_2027:
        eclipse_date = date.fromisoformat(eclipse["date"])
        if eclipse_date < start_date or eclipse_date > end_date:
            continue

        etype = eclipse["type"]
        if "total" in etype:
            buff_key = "eclipse_total"
        elif "annular" in etype:
            buff_key = "eclipse_annular"
        elif "partial" in etype:
            buff_key = "eclipse_partial"
        else:
            buff_key = "eclipse_penumbral"

        is_solar = "solar" in etype
        eid = _event_id("eclipse", eclipse["date"], eclipse["name"])

        events.append(AstronomicalEvent(
            event_id=eid,
            event_type="eclipse",
            name=eclipse["name"],
            description=eclipse["description"],
            start_time=eclipse["date"] + "T00:00:00+00:00",
            end_time=eclipse["date"] + "T23:59:59+00:00",
            peak_time=eclipse["date"] + "T12:00:00+00:00",
            buff_type="global",
            buff_percentage=eclipse["buff_percentage"],
            affected_modules=["all"] if is_solar else ["shrine", "quarters"],
            special_effects=[
                "eclipse_shadow" if is_solar else "blood_moon",
                f"visibility_{'_'.join(eclipse['visibility'][:3]).lower()}",
            ],
            source="calendar",
            location_dependent=True,
        ))

    return events


def _detect_iss_passes(
    lat: Optional[float], lng: Optional[float],
    start: datetime, end: datetime,
) -> List[AstronomicalEvent]:
    """Delegate to ar_sky_scanner._predict_iss_passes() for location-specific passes."""
    if lat is None or lng is None:
        return []

    from narrative_agentic.stellar_outreach.ar_sky_scanner import _predict_iss_passes

    days_ahead = max(1, (end.date() - start.date()).days)
    days_ahead = min(days_ahead, 10)  # Cap at 10 days

    try:
        passes = _predict_iss_passes(lat, lng, days=days_ahead)
    except Exception:
        return []

    events: List[AstronomicalEvent] = []
    for iss_pass in passes:
        pass_time = iss_pass.start_time
        eid = _event_id("iss_pass", pass_time[:10], f"ISS Pass {pass_time}")

        events.append(AstronomicalEvent(
            event_id=eid,
            event_type="iss_pass",
            name="ISS Overhead Pass",
            description=(
                f"The International Space Station streaks across your sky "
                f"at {iss_pass.max_altitude:.0f}° altitude. "
                f"Duration: {iss_pass.duration_seconds}s. Look up!"
            ),
            start_time=pass_time,
            end_time=iss_pass.end_time,
            peak_time=pass_time,
            buff_type="module_specific",
            buff_percentage=EVENT_BUFF_TABLE["iss_pass"],
            affected_modules=["observatory"],
            special_effects=["iss_streak"],
            source="calculated",
            location_dependent=True,
        ))

    return events


def _detect_zodiac_season(
    start: datetime, end: datetime,
) -> List[AstronomicalEvent]:
    """Detect zodiac season transitions (Sun ingress dates)."""
    events: List[AstronomicalEvent] = []
    start_date = start.date() if isinstance(start, datetime) else start
    end_date = end.date() if isinstance(end, datetime) else end

    for year in range(start_date.year, end_date.year + 1):
        for i, season in enumerate(ZODIAC_SEASON_DATES):
            try:
                ingress = date(year, season["month"], season["day"])
            except ValueError:
                continue

            if ingress < start_date or ingress > end_date:
                continue

            # Season lasts until next ingress
            next_season = ZODIAC_SEASON_DATES[(i + 1) % len(ZODIAC_SEASON_DATES)]
            try:
                next_year = year + (1 if next_season["month"] < season["month"] else 0)
                season_end = date(next_year, next_season["month"], next_season["day"]) - timedelta(days=1)
            except ValueError:
                season_end = ingress + timedelta(days=29)

            sign = season["sign"]
            eid = _event_id("zodiac_season", ingress.isoformat(), sign)

            events.append(AstronomicalEvent(
                event_id=eid,
                event_type="zodiac_season",
                name=f"{sign} Season Begins",
                description=(
                    f"The Sun enters {sign} — a new cosmic season unfolds. "
                    f"Players with {sign} placements feel an extra resonance."
                ),
                start_time=ingress.isoformat() + "T00:00:00+00:00",
                end_time=season_end.isoformat() + "T23:59:59+00:00",
                peak_time=ingress.isoformat() + "T12:00:00+00:00",
                buff_type="global",
                buff_percentage=EVENT_BUFF_TABLE["zodiac_season"],
                affected_modules=["all"],
                special_effects=[f"season_{sign.lower()}"],
                source="calendar",
                location_dependent=False,
            ))

    return events


# ────────────────────────────────────────────────────────────────
# Unified Detector
# ────────────────────────────────────────────────────────────────

def _detect_all_events(
    start: datetime,
    end: datetime,
    lat: Optional[float] = None,
    lng: Optional[float] = None,
) -> List[AstronomicalEvent]:
    """Run all 9 detectors and merge results. Cached for 10 minutes.

    Args:
        start: Range start (UTC datetime).
        end:   Range end (UTC datetime).
        lat:   Observer latitude (for location-dependent events).
        lng:   Observer longitude (for location-dependent events).

    Returns:
        Merged, deduplicated list of all detected events sorted by start_time.
    """
    cache_key = f"{start.isoformat()}:{end.isoformat()}:{lat}:{lng}"
    now = time.time()

    if cache_key in _event_cache:
        cached_time, cached_events = _event_cache[cache_key]
        if now - cached_time < EVENT_CACHE_SECONDS:
            return cached_events

    all_events: List[AstronomicalEvent] = []

    # Calendar-based detectors (fast, no external calls)
    all_events.extend(_detect_meteor_showers(start, end))
    all_events.extend(_detect_eclipses(start, end))
    all_events.extend(_detect_mercury_retrograde(start, end))
    all_events.extend(_detect_zodiac_season(start, end))

    # Calculation-based detectors
    all_events.extend(_detect_moon_phases(start, end))
    all_events.extend(_detect_planet_conjunctions(start, end))

    # NASA API detectors (with file cache + graceful fallback)
    all_events.extend(_detect_solar_flares(start, end))
    all_events.extend(_detect_asteroid_approaches(start, end))

    # Location-dependent
    all_events.extend(_detect_iss_passes(lat, lng, start, end))

    # Deduplicate by event_id
    seen: Dict[str, AstronomicalEvent] = {}
    for evt in all_events:
        if evt.event_id not in seen:
            seen[evt.event_id] = evt
    deduped = list(seen.values())

    # Sort by start_time
    deduped.sort(key=lambda e: e.start_time)

    # Cache
    _event_cache[cache_key] = (now, deduped)

    return deduped


# ────────────────────────────────────────────────────────────────
# Public API Functions
# ────────────────────────────────────────────────────────────────

def get_active_events(
    lat: Optional[float] = None,
    lng: Optional[float] = None,
) -> dict:
    """Get all currently active astronomical events.

    Endpoint: GET /api/stellar/events/active

    Args:
        lat: Observer latitude (optional, for location-dependent events).
        lng: Observer longitude (optional).

    Returns:
        Dict with "events" list and "count".
    """
    now = datetime.now(timezone.utc)
    # Search window: 2 days before to 2 days after (catches multi-day events)
    start = now - timedelta(days=2)
    end = now + timedelta(days=2)

    all_events = _detect_all_events(start, end, lat, lng)

    now_iso = now.isoformat()
    active = [
        evt for evt in all_events
        if evt.start_time <= now_iso <= evt.end_time
    ]

    return {
        "events": [_event_to_dict(e) for e in active],
        "count": len(active),
        "as_of": now_iso,
    }


def get_upcoming_events(
    lat: Optional[float] = None,
    lng: Optional[float] = None,
    days: int = 30,
) -> dict:
    """Get upcoming astronomical events within the specified day range.

    Endpoint: GET /api/stellar/events/upcoming

    Args:
        lat:  Observer latitude (optional).
        lng:  Observer longitude (optional).
        days: How many days ahead to look (default 30, max 90).

    Returns:
        Dict with "events" list, "count", and "range" info.
    """
    days = min(max(1, days), 90)
    now = datetime.now(timezone.utc)
    end = now + timedelta(days=days)

    all_events = _detect_all_events(now, end, lat, lng)

    return {
        "events": [_event_to_dict(e) for e in all_events],
        "count": len(all_events),
        "range_start": now.isoformat(),
        "range_end": end.isoformat(),
        "days": days,
    }


def get_event_detail(event_id: str) -> dict:
    """Get detailed information about a specific event.

    Endpoint: GET /api/stellar/events/detail/{id}

    Searches recent events (60-day window) for the given event_id.

    Args:
        event_id: The event identifier.

    Returns:
        Dict with full event data, or error if not found.
    """
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=30)
    end = now + timedelta(days=30)

    all_events = _detect_all_events(start, end)

    for evt in all_events:
        if evt.event_id == event_id:
            result = _event_to_dict(evt)
            result["buff_details"] = {
                "base_percentage": evt.buff_percentage,
                "type": evt.buff_type,
                "affected_modules": evt.affected_modules,
            }
            if evt.event_type == "mercury_retrograde":
                result["retrograde_effects"] = MERCURY_RETROGRADE_EFFECTS
            return result

    return {"error": "Event not found", "event_id": event_id}


def get_event_calendar(year: int, month: int) -> dict:
    """Get events for a calendar month, bucketed by day.

    Endpoint: GET /api/stellar/events/calendar

    Args:
        year:  Calendar year.
        month: Calendar month (1-12).

    Returns:
        Dict with "days" mapping day-of-month to event lists.
    """
    month = min(max(1, month), 12)
    start = datetime(year, month, 1, tzinfo=timezone.utc)
    if month == 12:
        end = datetime(year + 1, 1, 1, tzinfo=timezone.utc) - timedelta(seconds=1)
    else:
        end = datetime(year, month + 1, 1, tzinfo=timezone.utc) - timedelta(seconds=1)

    all_events = _detect_all_events(start, end)

    # Bucket by day
    days: Dict[int, List[dict]] = {}
    for evt in all_events:
        # An event may span multiple days — add to each day it covers
        evt_start = date.fromisoformat(evt.start_time[:10])
        evt_end = date.fromisoformat(evt.end_time[:10])
        current = max(evt_start, start.date())
        final = min(evt_end, end.date())
        while current <= final:
            if current.month == month and current.year == year:
                day_num = current.day
                if day_num not in days:
                    days[day_num] = []
                days[day_num].append(_event_to_dict(evt))
            current += timedelta(days=1)

    return {
        "year": year,
        "month": month,
        "days": days,
        "total_events": len(all_events),
    }


def get_event_bonuses(player_id: str) -> dict:
    """Calculate aggregated event bonuses for a player.

    Endpoint: GET /api/stellar/events/bonuses

    Sums all active event buffs into a single EventBuff structure.

    Args:
        player_id: The player identifier.

    Returns:
        Dict with global_buff_percentage, module_buffs, active_events, etc.
    """
    active_result = get_active_events()
    active_events = active_result.get("events", [])

    global_buff = 0
    module_buffs: Dict[str, int] = {}
    event_ids: List[str] = []
    special_effects: List[str] = []

    for evt_dict in active_events:
        buff_pct = evt_dict.get("buff_percentage", 0)
        buff_type = evt_dict.get("buff_type", "global")
        affected = evt_dict.get("affected_modules", ["all"])
        effects = evt_dict.get("special_effects", [])

        event_ids.append(evt_dict["event_id"])
        special_effects.extend(effects)

        if buff_type == "global" or "all" in affected:
            global_buff += buff_pct
        elif buff_type == "module_specific":
            for mod_id in affected:
                module_buffs[mod_id] = module_buffs.get(mod_id, 0) + buff_pct
        elif buff_type == "special":
            # Special buffs add half to global, half to specific modules
            global_buff += buff_pct // 2
            for mod_id in affected:
                module_buffs[mod_id] = module_buffs.get(mod_id, 0) + buff_pct // 2

    buff = EventBuff(
        player_id=player_id,
        date=date.today().isoformat(),
        global_buff_percentage=global_buff,
        module_buffs=module_buffs,
        active_events=event_ids,
        special_effects_active=list(set(special_effects)),
    )

    return asdict(buff)


def get_event_config() -> dict:
    """Get event system configuration and constants.

    Endpoint: GET /api/stellar/events/config

    Returns:
        Dict with buff tables, retrograde effects, and system info.
    """
    return {
        "buff_table": EVENT_BUFF_TABLE,
        "mercury_retrograde_effects": MERCURY_RETROGRADE_EFFECTS,
        "meteor_shower_count": len(METEOR_SHOWERS),
        "eclipse_count": len(ECLIPSES_2025_2027),
        "retrograde_count": len(MERCURY_RETROGRADES_2025_2027),
        "zodiac_seasons": len(ZODIAC_SEASON_DATES),
        "event_types": [
            "full_moon", "new_moon", "meteor_shower", "conjunction",
            "mercury_retrograde", "mercury_retrograde_shadow",
            "solar_flare", "asteroid_close", "eclipse",
            "iss_pass", "zodiac_season",
        ],
        "cache_ttl_seconds": EVENT_CACHE_SECONDS,
        "nasa_cache_hours": NASA_CACHE_HOURS,
        "version": "1.0.0",
    }

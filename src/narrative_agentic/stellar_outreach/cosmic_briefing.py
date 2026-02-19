"""
NEXUS STATION - Stellar Outreach: Daily Cosmic Briefing (TASK-005)

Orchestrates the complete daily briefing flow — the FIRST thing players
see each day. Combines transit engine output, station state, player
identity, and discovery cards into a unified DailyBriefingData payload
for the mobile client.

Daily Flow (GDD S5.1):
    1. OPEN APP
    2. COSMIC BRIEFING (30 sec) — Power/Trouble/Pressure, daily dispatch
    3. STATION CHECK (60 sec) — Collect overnight resources, module alerts
    4. DAILY MISSION (3-5 min) — Main activity shaped by cosmic alignment
    5. DISCOVERY CARD (30 sec) — NASA APOD image + space fact
    6. CLOSE or CONTINUE

References:
    - GDD S4.1: Daily briefing screen
    - GDD S5.1: Daily flow design
    - GDD S12.2: Element color theming

Security Note (Article II / Kai Chen review):
    Birth input is used only for chart calculation. Raw birth data is NOT
    stored in briefing caches — only derived profile data is persisted.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import date, datetime, time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from narrative_agentic.stellar_outreach.birth_chart import (
    BirthChartInput,
    PlayerProfile,
    ZodiacArchetype,
    calculate_birth_chart,
    player_profile_to_dict,
    ELEMENTS,
)
from narrative_agentic.stellar_outreach.transit_engine import (
    CosmicBriefing,
    ModuleStatus,
    calculate_player_transits,
    generate_briefing_text,
    cosmic_briefing_to_dict,
)
from narrative_agentic.stellar_outreach.station_modules import (
    PlayerStation,
    StationModule,
    create_station,
    get_station,
    save_station,
    apply_cosmic_status,
    collect_resources,
    station_to_dict,
    MODULE_DEFINITIONS,
    CORE_RESOURCES,
)
from narrative_agentic.stellar_outreach.discovery_cards import (
    DiscoveryCard,
    fetch_daily_card,
)


# ────────────────────────────────────────────────────────────────
# Persistence Configuration
# ────────────────────────────────────────────────────────────────

BRIEFINGS_DIR = Path.home() / ".nexus_station" / "briefings"
PROFILES_DIR = Path.home() / ".nexus_station" / "profiles"


# ────────────────────────────────────────────────────────────────
# Element Color Theming (GDD S12.2)
# ────────────────────────────────────────────────────────────────

ELEMENT_COLORS: Dict[str, Dict[str, str]] = {
    "Fire": {
        "primary": "#DC2626",
        "secondary": "#F59E0B",
        "accent": "#FCD34D",
        "bg_gradient_start": "#1A0A0A",
        "bg_gradient_end": "#0A0A0A",
    },
    "Earth": {
        "primary": "#059669",
        "secondary": "#92400E",
        "accent": "#A16207",
        "bg_gradient_start": "#0A1A0A",
        "bg_gradient_end": "#0A0A0A",
    },
    "Air": {
        "primary": "#3B82F6",
        "secondary": "#9CA3AF",
        "accent": "#A78BFA",
        "bg_gradient_start": "#0A0A1A",
        "bg_gradient_end": "#0A0A0A",
    },
    "Water": {
        "primary": "#0891B2",
        "secondary": "#0D9488",
        "accent": "#E0E7FF",
        "bg_gradient_start": "#0A0A1A",
        "bg_gradient_end": "#0A0A0A",
    },
}


# ────────────────────────────────────────────────────────────────
# Archetype-Specific Dispatch Messages (15 per element = 60 total)
# ────────────────────────────────────────────────────────────────

DISPATCH_FIRE: List[str] = [
    "burn bright. the station needs your fire today.",
    "sparks catch. you are the ignition this crew has been waiting for.",
    "lead from the front. the corridor is lit by your conviction.",
    "the forge is hot. shape something that matters.",
    "your flame is the only compass that never lies.",
    "audacity is a fuel source. burn it recklessly today.",
    "the stars called. they want that energy back. tell them no.",
    "you were not built for caution. move fast, leave embers.",
    "the universe respects momentum. don't stop now.",
    "fire doesn't ask permission. neither should you today.",
    "your heat bends the trajectory of everyone around you.",
    "ignite the thing you've been circling. today it catches.",
    "courage is not the absence of static. it's launch anyway.",
    "your blaze lights the dark side of every corridor.",
    "the station's core temperature rises when you show up.",
]

DISPATCH_EARTH: List[str] = [
    "foundations hold. build what lasts.",
    "the soil is ready. plant something real today.",
    "patience is a resource. you have reserves others don't.",
    "steady hands build steady stations. take your time.",
    "the bedrock doesn't flinch. neither do you.",
    "what you build today will still be standing next cycle.",
    "trust the process. the harvest comes to those who tend.",
    "your roots run deeper than anyone suspects.",
    "measure twice, weld once. precision is your gift.",
    "the station rests on your shoulders and it doesn't even know.",
    "gravity is on your side. let things settle where they belong.",
    "you are the ballast. the station stays level because of you.",
    "slow work is real work. the cosmos respects craftsmanship.",
    "the ground beneath your feet is more certain than the stars above.",
    "endurance is your element. today tests it. you pass.",
]

DISPATCH_AIR: List[str] = [
    "the signal is clear. broadcast your truth.",
    "ideas are weather systems. let yours form a front today.",
    "the frequency shifts. you're the only one who can decode it.",
    "words carry farther in vacuum. choose yours carefully.",
    "your mind moves at light-speed. let the station catch up.",
    "clarity arrives on a breeze you didn't expect.",
    "the network hums with your frequency. transmit.",
    "connections form. the pattern was always there. you just see it now.",
    "the airwaves are yours. speak and the static parts.",
    "think laterally. the answer is in the space between the data.",
    "your thoughts are satellites. today they find their orbit.",
    "the comms array resonates at your pitch. use it.",
    "intelligence is not knowledge. it's the wind between the facts.",
    "the station's neural net lights up when you're thinking.",
    "curiosity is your propulsion system. let it steer.",
]

DISPATCH_WATER: List[str] = [
    "the currents run deep today. trust the flow.",
    "still water reads the stars more clearly than any telescope.",
    "your intuition is a sonar pulse. listen for the echo.",
    "the tides shift. you felt it before the instruments did.",
    "depth is not weakness. it's where the real discoveries live.",
    "let the current carry what your arms can't hold.",
    "your empathy is a sensor array. it misses nothing.",
    "the station needs your calm. be the anchor today.",
    "waves crash and recede. you remain. that is your power.",
    "the deep places of the station answer only to you.",
    "feel first. the data will confirm what your heart already knows.",
    "the ocean of space mirrors the ocean inside you.",
    "vulnerability is a port, not a weakness. dock there today.",
    "the undercurrent knows the way. stop swimming against it.",
    "healing starts in the quiet. find a quiet corridor.",
]

# Mapping from element to dispatch pool
ELEMENT_DISPATCH: Dict[str, List[str]] = {
    "Fire": DISPATCH_FIRE,
    "Earth": DISPATCH_EARTH,
    "Air": DISPATCH_AIR,
    "Water": DISPATCH_WATER,
}

# Special condition messages
DISPATCH_ALL_POWER: List[str] = [
    "every system is green. the cosmos is handing you a perfect day.",
    "all modules in resonance. this doesn't happen often. use it.",
    "stellar alignment is total. the station hums with rare harmony.",
]

DISPATCH_ALL_TROUBLE: List[str] = [
    "red across the board. hunker down and ride it out.",
    "the cosmos is running a stress test. you are the variable that passes.",
    "turbulence everywhere. but turbulence is just energy with no direction yet.",
]


# ────────────────────────────────────────────────────────────────
# Data Class
# ────────────────────────────────────────────────────────────────

@dataclass
class DailyBriefingData:
    """Complete daily briefing payload for the frontend.

    Combines cosmic weather, station state, player identity, and
    discovery card into a single structure optimized for vertical
    mobile card-based UI rendering.
    """
    # Core identity
    player_id: str
    date: str
    station_name: str

    # Cosmic Weather (from transit_engine)
    cosmic_briefing_text: str
    daily_dispatch: str
    module_statuses: List[dict]
    overall_mood: str  # "positive", "challenging", "mixed", "neutral"

    # Station State (from station_modules)
    station_level: int
    resources: Dict[str, int]
    resources_collected: Dict[str, int]
    module_alerts: List[dict]

    # Player Identity (from birth_chart)
    archetype: dict
    element_color: dict

    # Discovery Card
    discovery_card: dict

    # Astronomical Events (TASK-019)
    active_events: List[dict] = field(default_factory=list)
    event_bonuses: dict = field(default_factory=dict)

    # Metadata
    generated_at: str = ""
    is_cached: bool = False


# ────────────────────────────────────────────────────────────────
# Internal Helpers — Persistence
# ────────────────────────────────────────────────────────────────

def _sanitize_id(player_id: str) -> str:
    """Sanitize a player ID for filesystem use."""
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in player_id)


def _briefing_dir(player_id: str) -> Path:
    """Return the briefing cache directory for a player."""
    return BRIEFINGS_DIR / _sanitize_id(player_id)


def _briefing_path(player_id: str, date_str: str) -> Path:
    """Return the file path for a cached briefing."""
    return _briefing_dir(player_id) / f"{date_str}.json"


def _ensure_briefing_dir(player_id: str) -> None:
    """Create the briefing cache directory if needed."""
    _briefing_dir(player_id).mkdir(parents=True, exist_ok=True)


def _profile_path(player_id: str) -> Path:
    """Return the file path for a cached player profile."""
    return PROFILES_DIR / f"{_sanitize_id(player_id)}.json"


def _ensure_profiles_dir() -> None:
    """Create the profiles directory if needed."""
    PROFILES_DIR.mkdir(parents=True, exist_ok=True)


def _save_profile_cache(player_id: str, profile_dict: dict) -> None:
    """Cache a player profile to disk (derived data only, no raw birth info)."""
    _ensure_profiles_dir()
    path = _profile_path(player_id)
    try:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(profile_dict, fh, indent=2)
    except IOError:
        pass


def _load_profile_cache(player_id: str) -> Optional[dict]:
    """Load a cached player profile from disk."""
    path = _profile_path(player_id)
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (json.JSONDecodeError, IOError):
        return None


# ────────────────────────────────────────────────────────────────
# Internal Helpers — Alerts
# ────────────────────────────────────────────────────────────────

def _generate_module_alerts(
    station: PlayerStation,
    module_statuses: List[ModuleStatus],
) -> List[dict]:
    """Generate alert entries for modules needing attention.

    Alert types:
        - Module health below 0.5
        - Module in TROUBLE cosmic status
        - Module eligible for upgrade (XP threshold met)
        - Critical resource at 0
    """
    alerts: List[dict] = []

    # Build a lookup for cosmic status by module name
    status_by_name: Dict[str, str] = {}
    for ms in module_statuses:
        status_by_name[ms.module_name] = ms.status

    for module in station.modules.values():
        # Low health
        if module.health < 0.5:
            alerts.append({
                "module_id": module.id,
                "module_name": module.name,
                "type": "WARNING",
                "message": (
                    f"WARNING: {module.name} structural integrity "
                    f"at {module.health * 100:.0f}%"
                ),
            })

        # TROUBLE status
        cosmic = status_by_name.get(module.name, "NEUTRAL")
        if cosmic == "TROUBLE":
            alerts.append({
                "module_id": module.id,
                "module_name": module.name,
                "type": "ALERT",
                "message": (
                    f"ALERT: {module.name} experiencing cosmic turbulence"
                ),
            })

        # Level-up available (XP >= threshold)
        if module.xp >= module.xp_to_next and module.level < 10:
            alerts.append({
                "module_id": module.id,
                "module_name": module.name,
                "type": "READY",
                "message": (
                    f"READY: {module.name} eligible for upgrade"
                ),
            })

    # Critical resource shortage
    for resource_name, amount in station.resources.items():
        if amount <= 0 and resource_name in CORE_RESOURCES:
            alerts.append({
                "module_id": None,
                "module_name": None,
                "type": "SHORTAGE",
                "message": (
                    f"SHORTAGE: {resource_name} reserves depleted"
                ),
            })

    return alerts


# ────────────────────────────────────────────────────────────────
# Internal Helpers — Mood & Dispatch
# ────────────────────────────────────────────────────────────────

def _determine_overall_mood(module_statuses: List[ModuleStatus]) -> str:
    """Determine overall cosmic mood from module statuses.

    Returns one of: "positive", "challenging", "mixed", "neutral".
    """
    power = sum(1 for m in module_statuses if m.status == "POWER")
    trouble = sum(1 for m in module_statuses if m.status == "TROUBLE")
    pressure = sum(1 for m in module_statuses if m.status == "PRESSURE")

    if power == 0 and trouble == 0 and pressure == 0:
        return "neutral"
    if power > 0 and trouble == 0:
        return "positive"
    if trouble > 0 and power == 0:
        return "challenging"
    return "mixed"


def _generate_personalized_dispatch(
    archetype: ZodiacArchetype,
    module_statuses: List[ModuleStatus],
    station_level: int,
    date_str: str,
) -> str:
    """Generate a personalized daily dispatch message.

    Considers:
        - Player archetype / element
        - Ratio of POWER vs TROUBLE modules
        - Station level
        - Special conditions (all POWER, all TROUBLE)
    """
    power_count = sum(1 for m in module_statuses if m.status == "POWER")
    trouble_count = sum(1 for m in module_statuses if m.status == "TROUBLE")
    active_count = sum(1 for m in module_statuses if m.status != "NEUTRAL")

    # Special conditions override
    if active_count > 0 and power_count == active_count:
        pool = DISPATCH_ALL_POWER
    elif active_count > 0 and trouble_count == active_count:
        pool = DISPATCH_ALL_TROUBLE
    else:
        # Use element-specific pool
        pool = ELEMENT_DISPATCH.get(archetype.element, DISPATCH_FIRE)

    # Deterministic selection based on date + player element
    seed_str = f"{date_str}:{archetype.element}:{archetype.sign}"
    seed = int(hashlib.md5(seed_str.encode()).hexdigest()[:8], 16)
    return pool[seed % len(pool)]


# ────────────────────────────────────────────────────────────────
# Internal Helpers — Module Status Serialization
# ────────────────────────────────────────────────────────────────

def _module_status_to_dict(ms: ModuleStatus) -> dict:
    """Serialize a ModuleStatus to a JSON-safe dictionary for the briefing."""
    return {
        "module_name": ms.module_name,
        "co_star_category": ms.co_star_category,
        "status": ms.status,
        "buff_percentage": ms.buff_percentage,
        "description": ms.description,
    }


# ────────────────────────────────────────────────────────────────
# Public API
# ────────────────────────────────────────────────────────────────

def get_element_colors(element: str) -> dict:
    """Return the color palette for a given element.

    Args:
        element: One of "Fire", "Earth", "Air", "Water".

    Returns:
        Dictionary with primary, secondary, accent, and gradient colors.
        Falls back to Fire palette for unknown elements.
    """
    return dict(ELEMENT_COLORS.get(element, ELEMENT_COLORS["Fire"]))


def get_cached_briefing(
    player_id: str,
    date_str: Optional[str] = None,
) -> Optional[DailyBriefingData]:
    """Load a cached briefing from disk.

    Args:
        player_id: Player identifier.
        date_str:  ISO date string (YYYY-MM-DD). Defaults to today.

    Returns:
        A DailyBriefingData if a cached briefing exists, otherwise None.
    """
    if date_str is None:
        date_str = date.today().isoformat()

    path = _briefing_path(player_id, date_str)
    if not path.exists():
        return None

    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return DailyBriefingData(
            player_id=data["player_id"],
            date=data["date"],
            station_name=data["station_name"],
            cosmic_briefing_text=data["cosmic_briefing_text"],
            daily_dispatch=data["daily_dispatch"],
            module_statuses=data["module_statuses"],
            overall_mood=data["overall_mood"],
            station_level=data["station_level"],
            resources=data["resources"],
            resources_collected=data["resources_collected"],
            module_alerts=data["module_alerts"],
            archetype=data["archetype"],
            element_color=data["element_color"],
            discovery_card=data["discovery_card"],
            generated_at=data["generated_at"],
            is_cached=True,
        )
    except (json.JSONDecodeError, IOError, KeyError):
        return None


def generate_daily_briefing(
    player_id: str,
    birth_input: Optional[dict] = None,
    date_str: Optional[str] = None,
) -> DailyBriefingData:
    """Generate the complete daily briefing for a player.

    This is the main orchestrator function. It:
        1. Checks for a cached briefing for today
        2. Calculates (or loads) the player's birth chart profile
        3. Runs transit calculations for the date
        4. Loads (or creates) the player's station
        5. Applies cosmic statuses to station modules
        6. Collects overnight resources
        7. Generates module alerts
        8. Fetches the daily discovery card
        9. Assembles DailyBriefingData
       10. Caches the result

    Args:
        player_id:   Unique player identifier.
        birth_input: Optional dict with keys: birth_date (str YYYY-MM-DD),
                     birth_time (str HH:MM, optional), latitude (float),
                     longitude (float). If not provided, tries to load a
                     cached profile.
        date_str:    ISO date string (YYYY-MM-DD). Defaults to today.

    Returns:
        A DailyBriefingData instance.

    Raises:
        ValueError: If no birth data and no cached profile exists.
    """
    if date_str is None:
        date_str = date.today().isoformat()

    # ── Step 1: Check cache ──────────────────────────────────────
    cached = get_cached_briefing(player_id, date_str)
    if cached is not None:
        return cached

    # ── Step 2: Player profile ───────────────────────────────────
    profile: Optional[PlayerProfile] = None
    profile_dict: Optional[dict] = None

    if birth_input:
        bd = date.fromisoformat(birth_input["birth_date"])
        bt = None
        if birth_input.get("birth_time"):
            parts = birth_input["birth_time"].split(":")
            bt = time(int(parts[0]), int(parts[1]))

        chart_input = BirthChartInput(
            birth_date=bd,
            latitude=float(birth_input["latitude"]),
            longitude=float(birth_input["longitude"]),
            birth_time=bt,
        )
        profile = calculate_birth_chart(chart_input)
        profile_dict = player_profile_to_dict(profile)
        _save_profile_cache(player_id, profile_dict)
    else:
        # Try loading cached profile
        profile_dict = _load_profile_cache(player_id)
        if profile_dict is None:
            raise ValueError(
                f"No birth data provided and no cached profile for player '{player_id}'. "
                "Please provide birth_input on first use."
            )

    # Extract archetype info from profile_dict
    archetype_data = profile_dict["archetype"]
    archetype = ZodiacArchetype(
        sign=archetype_data["sign"],
        element=archetype_data["element"],
        role=archetype_data["role"],
        strengths=archetype_data["strengths"],
        weakness=archetype_data["weakness"],
    )

    # ── Step 3: Transit calculations ─────────────────────────────
    # We need a PlayerProfile object for calculate_player_transits.
    # If we don't have one (loaded from cache), recalculate from
    # the cached profile's natal chart data.
    if profile is None:
        # Reconstruct a minimal profile from cached dict for transits
        # We need to re-calculate from birth input if available,
        # but since we don't store raw birth data, we use a fresh
        # birth_input if provided. Since birth_input is None here,
        # we need the profile object. Let's reconstruct from cache.
        profile = _reconstruct_profile(profile_dict)

    cosmic_briefing: CosmicBriefing = calculate_player_transits(
        profile, date_str=date_str
    )

    # ── Step 4: Station ──────────────────────────────────────────
    station = get_station(player_id)
    if station is None:
        station_name = f"{archetype.sign} Station"
        station = create_station(player_id, station_name)

    # ── Step 5: Apply cosmic statuses ────────────────────────────
    station = apply_cosmic_status(station, cosmic_briefing.module_statuses)

    # ── Step 6: Collect overnight resources ──────────────────────
    resources_collected = collect_resources(station)
    save_station(station)

    # ── Step 7: Module alerts ────────────────────────────────────
    module_alerts = _generate_module_alerts(
        station, cosmic_briefing.module_statuses
    )

    # ── Step 8: Discovery card ───────────────────────────────────
    discovery_card = fetch_daily_card(date_str=date_str)
    discovery_card_dict = discovery_card.to_dict()

    # ── Step 9: Personalized dispatch ────────────────────────────
    personalized_dispatch = _generate_personalized_dispatch(
        archetype,
        cosmic_briefing.module_statuses,
        station.station_level,
        date_str,
    )

    # ── Step 10: Overall mood ────────────────────────────────────
    overall_mood = _determine_overall_mood(cosmic_briefing.module_statuses)

    # ── Step 11: Element colors ──────────────────────────────────
    element_color = get_element_colors(archetype.element)

    # ── Step 12: Module statuses as dicts ────────────────────────
    module_statuses_dicts = [
        _module_status_to_dict(ms) for ms in cosmic_briefing.module_statuses
    ]

    # ── Step 13: Astronomical events (TASK-019) ─────────────────
    try:
        from narrative_agentic.stellar_outreach.astronomical_events import (
            get_active_events,
            get_event_bonuses,
        )
        active_events_data = get_active_events()
        active_events_list = active_events_data.get("events", [])
        event_bonuses_data = get_event_bonuses(player_id)
    except Exception:
        active_events_list = []
        event_bonuses_data = {}

    # ── Step 14: Assemble briefing ───────────────────────────────
    generated_at = datetime.utcnow().isoformat()

    briefing = DailyBriefingData(
        player_id=player_id,
        date=date_str,
        station_name=station.station_name,
        cosmic_briefing_text=cosmic_briefing.briefing_text,
        daily_dispatch=personalized_dispatch,
        module_statuses=module_statuses_dicts,
        overall_mood=overall_mood,
        station_level=station.station_level,
        resources=dict(station.resources),
        resources_collected=resources_collected,
        module_alerts=module_alerts,
        archetype=archetype_data,
        element_color=element_color,
        discovery_card=discovery_card_dict,
        active_events=active_events_list,
        event_bonuses=event_bonuses_data,
        generated_at=generated_at,
        is_cached=False,
    )

    # ── Step 15: Cache the result ────────────────────────────────
    _cache_briefing(briefing)

    return briefing


def briefing_to_dict(briefing: DailyBriefingData) -> dict:
    """Serialize a DailyBriefingData to a JSON-safe dictionary.

    Used by the API endpoint to return the full briefing payload.

    Args:
        briefing: The briefing to serialize.

    Returns:
        A JSON-safe dictionary.
    """
    return {
        "player_id": briefing.player_id,
        "date": briefing.date,
        "station_name": briefing.station_name,
        "cosmic_briefing_text": briefing.cosmic_briefing_text,
        "daily_dispatch": briefing.daily_dispatch,
        "module_statuses": briefing.module_statuses,
        "overall_mood": briefing.overall_mood,
        "station_level": briefing.station_level,
        "resources": briefing.resources,
        "resources_collected": briefing.resources_collected,
        "module_alerts": briefing.module_alerts,
        "archetype": briefing.archetype,
        "element_color": briefing.element_color,
        "discovery_card": briefing.discovery_card,
        "active_events": briefing.active_events,
        "event_bonuses": briefing.event_bonuses,
        "generated_at": briefing.generated_at,
        "is_cached": briefing.is_cached,
    }


# ────────────────────────────────────────────────────────────────
# Internal Helpers — Profile Reconstruction
# ────────────────────────────────────────────────────────────────

def _reconstruct_profile(profile_dict: dict) -> PlayerProfile:
    """Reconstruct a PlayerProfile object from a cached dictionary.

    This rebuilds the dataclass hierarchy from the serialized form
    so that calculate_player_transits can operate on it.
    """
    from narrative_agentic.stellar_outreach.birth_chart import (
        NatalChart,
        PlanetPosition,
    )

    natal_data = profile_dict["natal_chart"]
    planets = [
        PlanetPosition(
            planet=p["planet"],
            sign=p["sign"],
            degree=p["degree"],
            sign_degree=p["sign_degree"],
            house=p["house"],
            retrograde=p["retrograde"],
        )
        for p in natal_data["planets"]
    ]

    natal_chart = NatalChart(
        planets=planets,
        house_cusps=natal_data["house_cusps"],
        ascendant=natal_data["ascendant"],
        ascendant_sign=natal_data["ascendant_sign"],
        midheaven=natal_data["midheaven"],
        midheaven_sign=natal_data["midheaven_sign"],
    )

    arch_data = profile_dict["archetype"]
    archetype = ZodiacArchetype(
        sign=arch_data["sign"],
        element=arch_data["element"],
        role=arch_data["role"],
        strengths=arch_data["strengths"],
        weakness=arch_data["weakness"],
    )

    return PlayerProfile(
        natal_chart=natal_chart,
        archetype=archetype,
        elemental_balance=profile_dict["elemental_balance"],
        dominant_planet=profile_dict["dominant_planet"],
        is_sunrise_chart=profile_dict["is_sunrise_chart"],
    )


# ────────────────────────────────────────────────────────────────
# Internal Helpers — Briefing Cache
# ────────────────────────────────────────────────────────────────

def _cache_briefing(briefing: DailyBriefingData) -> None:
    """Write a briefing to the file cache."""
    _ensure_briefing_dir(briefing.player_id)
    path = _briefing_path(briefing.player_id, briefing.date)
    try:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(briefing_to_dict(briefing), fh, indent=2)
    except IOError:
        pass  # Graceful degradation

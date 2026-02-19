"""
NEXUS STATION - Stellar Outreach: Seven Station Modules (TASK-003)

Core implementation of the player station system. Each station comprises
seven modules mapped to Co-Star life categories. Modules level up
independently, produce resources, and are affected by daily cosmic
transits from the Transit Engine (TASK-002).

References:
    - GDD S4:   Station Module definitions
    - GDD S6.1: Station and module level systems

Security Note (Article II / Kai Chen review):
    Player stations are stored on disk keyed by sanitized player_id.
    No personally identifiable information beyond a chosen station name
    is persisted.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from narrative_agentic.stellar_outreach.transit_engine import ModuleStatus


# ────────────────────────────────────────────────────────────────
# Persistence Configuration
# ────────────────────────────────────────────────────────────────

STATIONS_DIR = Path.home() / ".nexus_station" / "stations"


# ────────────────────────────────────────────────────────────────
# Constants — Module Definitions (GDD S4)
# ────────────────────────────────────────────────────────────────

MODULE_DEFINITIONS: Dict[str, dict] = {
    "bridge": {
        "name": "Bridge",
        "co_star_category": "Self",
        "description": (
            "The warm heart of your station. Amber console lights hum softly "
            "as you settle into the command chair. Every decision you make "
            "ripples outward from here."
        ),
        "power_buff_description": "+15% XP gain",
        "trouble_debuff_description": "Decision cooldowns longer",
        "pressure_effect_description": "Forced binary choices",
        "resources_produced": {"morale": 1.0},
    },
    "quarters": {
        "name": "Quarters",
        "co_star_category": "Routine",
        "description": (
            "Soft lighting, the scent of recycled cedar, a neatly folded "
            "blanket on every bunk. The Quarters keep your crew rested, "
            "fed, and ready for whatever the cosmos throws next."
        ),
        "power_buff_description": "Auto-repair active",
        "trouble_debuff_description": "Systems degrade faster",
        "pressure_effect_description": "Maintenance costs +20%",
        "resources_produced": {"food": 1.0},
    },
    "observatory": {
        "name": "Observatory",
        "co_star_category": "Thinking & Creativity",
        "description": (
            "A domed room of glass and brass, telescopes angled toward "
            "the infinite. Here, data streams into knowledge and knowledge "
            "becomes discovery. Think slowly. See clearly."
        ),
        "power_buff_description": "Crafting crit +20%",
        "trouble_debuff_description": "Research speed -25%",
        "pressure_effect_description": "Random crafting outcomes",
        "resources_produced": {"data": 1.0},
    },
    "greenhouse": {
        "name": "Greenhouse",
        "co_star_category": "Sex & Love",
        "description": (
            "Vines climb copper trellises under grow-lamps that mimic "
            "a summer afternoon. The Greenhouse tends relationships as "
            "carefully as it tends its plants — with patience and warmth."
        ),
        "power_buff_description": "Relationship XP +25%",
        "trouble_debuff_description": "Crew conflicts arise",
        "pressure_effect_description": "Emotional events trigger",
        "resources_produced": {"food": 0.5, "morale": 0.5},
    },
    "commons": {
        "name": "Commons",
        "co_star_category": "Social Life",
        "description": (
            "Long tables, mismatched chairs, a bulletin board covered in "
            "trade notices and alliance postings. The Commons is where "
            "strangers become allies and deals are sealed with a handshake."
        ),
        "power_buff_description": "Trade prices -15%",
        "trouble_debuff_description": "Alliance features locked",
        "pressure_effect_description": "Social obligations increase",
        "resources_produced": {"morale": 1.0},
    },
    "shrine": {
        "name": "Shrine",
        "co_star_category": "Spirituality",
        "description": (
            "A quiet alcove lined with star charts and candle stubs. "
            "The Shrine is where you listen for signals that instruments "
            "cannot detect. Meditate here and the universe might whisper back."
        ),
        "power_buff_description": "Rare discovery +30%",
        "trouble_debuff_description": "Lore fragments scrambled",
        "pressure_effect_description": "Cryptic quest clues only",
        "resources_produced": {"stardust": 1.0},
    },
    "workshop": {
        "name": "Workshop",
        "co_star_category": "Work",
        "description": (
            "Sparks fly off the welding bench. Tools hang in careful rows "
            "along pegboard walls. The Workshop smells of solder and ambition. "
            "If it can be built, it gets built here."
        ),
        "power_buff_description": "Build speed +25%",
        "trouble_debuff_description": "Production output -20%",
        "pressure_effect_description": "Resource costs fluctuate",
        "resources_produced": {"energy": 0.5, "materials": 0.5},
    },
}

# The 6 core resources
CORE_RESOURCES: List[str] = [
    "energy",
    "materials",
    "data",
    "food",
    "morale",
    "stardust",
]

# Module level feature unlocks: {module_id: {level: [features]}}
MODULE_UNLOCKS: Dict[str, Dict[int, List[str]]] = {
    "bridge": {
        3: ["Priority Comm Channel", "Quick Decision Mode"],
        5: ["Fleet Command Interface", "Identity Beacon"],
        7: ["Tactical Overlay", "Crisis Autopilot"],
        10: ["Admiral's Console", "Prestige Insignia", "Legendary Decree"],
    },
    "quarters": {
        3: ["Crew Lounge", "Auto-Meal Prep"],
        5: ["Hydro Shower Suite", "Sleep Cycle Optimizer"],
        7: ["Gravity Gym", "Medical Bay Annex"],
        10: ["Luxury Quarters", "Crew Morale Aura", "Full Auto-Repair"],
    },
    "observatory": {
        3: ["Spectral Analyzer", "Starfield Journal"],
        5: ["Deep-Sky Scanner", "Crafting Blueprints Mk II"],
        7: ["Quantum Telescope", "Research Chain Bonus"],
        10: ["Celestial Cartography Lab", "Discovery Amplifier", "Eureka Protocol"],
    },
    "greenhouse": {
        3: ["Exotic Seedlings", "Crew Bonding Events"],
        5: ["Bioluminescent Garden", "Relationship Tracker"],
        7: ["Hybrid Breeding Lab", "Empathy Resonance Field"],
        10: ["Terraforming Preview", "Soul Garden", "Eternal Bloom"],
    },
    "commons": {
        3: ["Trade Board", "Alliance Registry"],
        5: ["Market Analytics", "Diplomatic Lounge"],
        7: ["Galactic Bazaar", "Coalition Pact System"],
        10: ["Interstellar Exchange", "Cultural Embassy", "Trade Monarch Title"],
    },
    "shrine": {
        3: ["Meditation Alcove", "Lore Fragment Collector"],
        5: ["Vision Chamber", "Star Whisper Decoder"],
        7: ["Astral Projection Suite", "Ancient Signal Receiver"],
        10: ["Cosmic Oracle", "Transcendence Gate", "Stardust Forge"],
    },
    "workshop": {
        3: ["Smelting Furnace", "Blueprint Drafting Table"],
        5: ["Automated Assembly Line", "Advanced Alloys"],
        7: ["Nanofabrication Bay", "Overclocked Forge"],
        10: ["Masterwork Bench", "Infinite Schematic Library", "Titan Forge"],
    },
}

# Station level thresholds (GDD S6.1)
STATION_LEVEL_THRESHOLDS: Dict[int, str] = {
    1:  "Basic modules, limited capacity",
    5:  "Module specializations unlock",
    10: "Advanced research, rare crafting",
    20: "Station customization (aesthetic)",
    50: "Prestige — New Station with bonuses",
}


# ────────────────────────────────────────────────────────────────
# Data Classes
# ────────────────────────────────────────────────────────────────

@dataclass
class StationModule:
    """A single station module.

    Each module maps to a Co-Star life category and maintains its own
    level, health, cosmic status, and resource production.
    """
    id: str
    name: str
    co_star_category: str
    description: str
    level: int = 1
    xp: int = 0
    xp_to_next: int = 100
    health: float = 1.0
    cosmic_status: str = "NEUTRAL"
    buff_percentage: float = 0.0
    power_buff_description: str = ""
    trouble_debuff_description: str = ""
    pressure_effect_description: str = ""
    resources_produced: Dict[str, float] = field(default_factory=dict)
    upgrade_cost: Dict[str, int] = field(default_factory=dict)
    unlocked_features: List[str] = field(default_factory=list)


@dataclass
class PlayerStation:
    """The player's complete station comprising all seven modules."""
    player_id: str
    station_name: str
    station_level: int = 1
    modules: Dict[str, StationModule] = field(default_factory=dict)
    resources: Dict[str, int] = field(default_factory=dict)
    created_at: str = ""
    last_active: str = ""


# ────────────────────────────────────────────────────────────────
# Internal Helpers
# ────────────────────────────────────────────────────────────────

def _sanitize_player_id(player_id: str) -> str:
    """Sanitize a player ID for safe filesystem use."""
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in player_id)


def _station_path(player_id: str) -> Path:
    """Return the file path for a player's station data."""
    safe_id = _sanitize_player_id(player_id)
    return STATIONS_DIR / f"{safe_id}.json"


def _ensure_stations_dir() -> None:
    """Create the stations directory if it does not exist."""
    STATIONS_DIR.mkdir(parents=True, exist_ok=True)


def _calculate_xp_to_next(level: int) -> int:
    """XP required to advance from the given level to the next.

    Scaling: level N requires N * 100 XP.
    """
    return level * 100


def _calculate_upgrade_cost(level: int) -> Dict[str, int]:
    """Calculate the resource cost to upgrade a module from the given level.

    Costs scale with level: base cost * level.
    """
    base_energy = 50
    base_materials = 50
    return {
        "energy": base_energy * level,
        "materials": base_materials * level,
    }


def _calculate_station_level(modules: Dict[str, StationModule]) -> int:
    """Station level = average of all module levels, rounded down."""
    if not modules:
        return 1
    total = sum(m.level for m in modules.values())
    return max(1, math.floor(total / len(modules)))


def _get_unlocked_features(module_id: str, level: int) -> List[str]:
    """Collect all features unlocked up to and including the given level."""
    unlocks = MODULE_UNLOCKS.get(module_id, {})
    features: List[str] = []
    for milestone in sorted(unlocks.keys()):
        if milestone <= level:
            features.extend(unlocks[milestone])
    return features


def _module_to_dict(module: StationModule) -> dict:
    """Serialize a StationModule to a JSON-safe dictionary."""
    return {
        "id": module.id,
        "name": module.name,
        "co_star_category": module.co_star_category,
        "description": module.description,
        "level": module.level,
        "xp": module.xp,
        "xp_to_next": module.xp_to_next,
        "health": module.health,
        "cosmic_status": module.cosmic_status,
        "buff_percentage": module.buff_percentage,
        "power_buff_description": module.power_buff_description,
        "trouble_debuff_description": module.trouble_debuff_description,
        "pressure_effect_description": module.pressure_effect_description,
        "resources_produced": module.resources_produced,
        "upgrade_cost": module.upgrade_cost,
        "unlocked_features": module.unlocked_features,
    }


def _module_from_dict(data: dict) -> StationModule:
    """Deserialize a StationModule from a dictionary."""
    return StationModule(
        id=data["id"],
        name=data["name"],
        co_star_category=data["co_star_category"],
        description=data.get("description", ""),
        level=data.get("level", 1),
        xp=data.get("xp", 0),
        xp_to_next=data.get("xp_to_next", 100),
        health=data.get("health", 1.0),
        cosmic_status=data.get("cosmic_status", "NEUTRAL"),
        buff_percentage=data.get("buff_percentage", 0.0),
        power_buff_description=data.get("power_buff_description", ""),
        trouble_debuff_description=data.get("trouble_debuff_description", ""),
        pressure_effect_description=data.get("pressure_effect_description", ""),
        resources_produced=data.get("resources_produced", {}),
        upgrade_cost=data.get("upgrade_cost", {}),
        unlocked_features=data.get("unlocked_features", []),
    )


# ────────────────────────────────────────────────────────────────
# Public API
# ────────────────────────────────────────────────────────────────

def create_station(player_id: str, station_name: str) -> PlayerStation:
    """Initialize a new player station with all seven modules at level 1.

    Args:
        player_id:    Unique player identifier.
        station_name: Display name chosen by the player.

    Returns:
        A fully initialized PlayerStation.
    """
    now = datetime.utcnow().isoformat()

    modules: Dict[str, StationModule] = {}
    for module_id, defn in MODULE_DEFINITIONS.items():
        modules[module_id] = StationModule(
            id=module_id,
            name=defn["name"],
            co_star_category=defn["co_star_category"],
            description=defn["description"],
            level=1,
            xp=0,
            xp_to_next=_calculate_xp_to_next(1),
            health=1.0,
            cosmic_status="NEUTRAL",
            buff_percentage=0.0,
            power_buff_description=defn["power_buff_description"],
            trouble_debuff_description=defn["trouble_debuff_description"],
            pressure_effect_description=defn["pressure_effect_description"],
            resources_produced=dict(defn["resources_produced"]),
            upgrade_cost=_calculate_upgrade_cost(1),
            unlocked_features=[],
        )

    resources: Dict[str, int] = {r: 0 for r in CORE_RESOURCES}

    station = PlayerStation(
        player_id=player_id,
        station_name=station_name,
        station_level=1,
        modules=modules,
        resources=resources,
        created_at=now,
        last_active=now,
    )

    save_station(station)
    return station


def get_station(player_id: str) -> Optional[PlayerStation]:
    """Load a player's station from disk.

    Args:
        player_id: The player identifier.

    Returns:
        A PlayerStation if found, or None.
    """
    path = _station_path(player_id)
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return _station_from_dict(data)
    except (json.JSONDecodeError, IOError, KeyError):
        return None


def save_station(station: PlayerStation) -> None:
    """Persist a PlayerStation to disk.

    Args:
        station: The station to save.
    """
    _ensure_stations_dir()
    station.last_active = datetime.utcnow().isoformat()
    path = _station_path(station.player_id)
    try:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(station_to_dict(station), fh, indent=2)
    except IOError:
        pass  # Graceful degradation


def apply_cosmic_status(
    station: PlayerStation,
    module_statuses: List[ModuleStatus],
) -> PlayerStation:
    """Apply transit engine module statuses to the player's station.

    Takes output from transit_engine.calculate_player_transits() and
    updates each module's cosmic_status and buff_percentage accordingly.

    Args:
        station:         The player's station.
        module_statuses: List of ModuleStatus from the transit engine.

    Returns:
        The updated PlayerStation (mutated in place and returned).
    """
    # Build a lookup from module name to ModuleStatus
    status_lookup: Dict[str, ModuleStatus] = {}
    for ms in module_statuses:
        status_lookup[ms.module_name] = ms

    # Map module names to module ids
    name_to_id: Dict[str, str] = {
        defn["name"]: mid for mid, defn in MODULE_DEFINITIONS.items()
    }

    for module_name, ms in status_lookup.items():
        module_id = name_to_id.get(module_name)
        if module_id and module_id in station.modules:
            module = station.modules[module_id]
            module.cosmic_status = ms.status
            module.buff_percentage = float(ms.buff_percentage)

    return station


def collect_resources(station: PlayerStation) -> Dict[str, int]:
    """Collect resources produced by all station modules for one cycle.

    Base production per resource = level * 10 * resource_weight,
    modified by cosmic buff percentage.

    Args:
        station: The player's station.

    Returns:
        Dictionary of resources collected this cycle.
    """
    collected: Dict[str, int] = {r: 0 for r in CORE_RESOURCES}

    # Fetch event bonuses (TASK-019) — lazy import, graceful fallback
    try:
        from narrative_agentic.stellar_outreach.astronomical_events import get_event_bonuses
        event_data = get_event_bonuses(station.player_id)
        global_event_buff = event_data.get("global_buff_percentage", 0)
        module_event_buffs = event_data.get("module_buffs", {})
    except Exception:
        global_event_buff = 0
        module_event_buffs = {}

    for module in station.modules.values():
        base_rate = module.level * 10
        buff_multiplier = 1.0 + (module.buff_percentage / 100.0)

        # Stack event buffs on top of transit buffs
        module_event_buff = module_event_buffs.get(module.id, 0)
        event_mult = 1.0 + (global_event_buff + module_event_buff) / 100.0
        total_mult = buff_multiplier * event_mult

        for resource_name, weight in module.resources_produced.items():
            if resource_name in collected:
                amount = int(base_rate * weight * total_mult)
                collected[resource_name] += amount

    # Add collected resources to the station's global pool
    for resource_name, amount in collected.items():
        station.resources[resource_name] = station.resources.get(resource_name, 0) + amount

    return collected


def upgrade_module(station: PlayerStation, module_id: str) -> bool:
    """Attempt to upgrade a module by spending resources.

    Checks if the player has sufficient resources. On success,
    increments the module level, recalculates XP thresholds,
    unlocks features, and updates the station level.

    Args:
        station:   The player's station.
        module_id: The ID of the module to upgrade.

    Returns:
        True if the upgrade succeeded, False otherwise.
    """
    if module_id not in station.modules:
        return False

    module = station.modules[module_id]

    if module.level >= 10:
        return False  # Max module level

    cost = module.upgrade_cost

    # Check resources
    for resource_name, amount_needed in cost.items():
        if station.resources.get(resource_name, 0) < amount_needed:
            return False

    # Spend resources
    for resource_name, amount_needed in cost.items():
        station.resources[resource_name] -= amount_needed

    # Level up
    module.level += 1
    module.xp = 0
    module.xp_to_next = _calculate_xp_to_next(module.level)
    module.upgrade_cost = _calculate_upgrade_cost(module.level)
    module.unlocked_features = _get_unlocked_features(module_id, module.level)

    # Recalculate station level
    station.station_level = _calculate_station_level(station.modules)

    return True


def get_module_info(station: PlayerStation, module_id: str) -> Optional[dict]:
    """Get detailed information about a specific module.

    Args:
        station:   The player's station.
        module_id: The ID of the module.

    Returns:
        A dictionary with detailed module info, or None if not found.
    """
    if module_id not in station.modules:
        return None

    module = station.modules[module_id]
    info = _module_to_dict(module)

    # Add computed fields for display
    info["active_buff"] = ""
    if module.cosmic_status == "POWER":
        info["active_buff"] = module.power_buff_description
    elif module.cosmic_status == "TROUBLE":
        info["active_buff"] = module.trouble_debuff_description
    elif module.cosmic_status == "PRESSURE":
        info["active_buff"] = module.pressure_effect_description

    # Next unlock milestone
    unlocks = MODULE_UNLOCKS.get(module_id, {})
    next_milestone = None
    for milestone in sorted(unlocks.keys()):
        if milestone > module.level:
            next_milestone = milestone
            break
    info["next_unlock_level"] = next_milestone
    info["next_unlock_features"] = unlocks.get(next_milestone, []) if next_milestone else []

    return info


def station_to_dict(station: PlayerStation) -> dict:
    """Serialize a PlayerStation to a JSON-safe dictionary.

    Used for API responses and persistence.

    Args:
        station: The station to serialize.

    Returns:
        A JSON-safe dictionary.
    """
    return {
        "player_id": station.player_id,
        "station_name": station.station_name,
        "station_level": station.station_level,
        "modules": {
            mid: _module_to_dict(mod)
            for mid, mod in station.modules.items()
        },
        "resources": station.resources,
        "created_at": station.created_at,
        "last_active": station.last_active,
    }


def _station_from_dict(data: dict) -> PlayerStation:
    """Deserialize a PlayerStation from a dictionary."""
    modules: Dict[str, StationModule] = {}
    for mid, mod_data in data.get("modules", {}).items():
        modules[mid] = _module_from_dict(mod_data)

    return PlayerStation(
        player_id=data["player_id"],
        station_name=data["station_name"],
        station_level=data.get("station_level", 1),
        modules=modules,
        resources=data.get("resources", {r: 0 for r in CORE_RESOURCES}),
        created_at=data.get("created_at", ""),
        last_active=data.get("last_active", ""),
    )

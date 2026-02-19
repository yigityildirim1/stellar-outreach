"""
NEXUS STATION - Stellar Outreach: Star Atlas Collection (TASK-013)

Discovery catalog of 116 astronomical objects (12 constellations, 77 stars,
15 deep-sky objects, 12 zodiac signs) with mission archive and seasonal
cosmic passport stamps.

Features:
    - Full catalog from existing game data with real astronomical metadata
    - Discovery tracking (objects found via mini-games, sky scanner, etc.)
    - Completion percentages per category and overall
    - Mission archive (rolling 100 entries of completed missions)
    - Cosmic passport (12 seasonal stamps, one per zodiac season)

Ethics Note (Dr. Elena Vasquez review):
    Atlas rewards curiosity and exploration. No objects are permanently
    missable — every discovery can be made at any time.

Security Note (Article II / Kai Chen review):
    Atlas data persisted per player_id with sanitized paths.
    Discovery sources validated against known types.

References:
    - TASK-004: Constellation and star data
    - TASK-008: Celestial objects and sky scanner data
    - TASK-001: Zodiac signs and elements
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional

from narrative_agentic.stellar_outreach.mini_games import _CONSTELLATION_DATA
from narrative_agentic.stellar_outreach.mini_games_phase2 import _CELESTIAL_OBJECTS
from narrative_agentic.stellar_outreach.birth_chart import ZODIAC_SIGNS, ELEMENTS


# ────────────────────────────────────────────────────────────────
# Persistence Configuration
# ────────────────────────────────────────────────────────────────

STAR_ATLAS_DIR = Path.home() / ".nexus_station" / "star_atlas"

MAX_MISSION_ARCHIVE = 100

# Valid discovery sources
VALID_DISCOVERY_SOURCES = [
    "mini_game", "sky_scanner", "daily_briefing", "manual",
    "star_pattern", "signal_decode", "resource_harvest",
    "diplomacy", "friend_gift", "achievement", "ar_scanner",
]


def _sanitize_player_id(player_id: str) -> str:
    """Sanitize a player ID for safe filesystem use."""
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in player_id)


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


# ────────────────────────────────────────────────────────────────
# Catalog — Build complete catalog from existing game data
# ────────────────────────────────────────────────────────────────

# Zodiac season date ranges (approximate start dates)
_ZODIAC_SEASONS: Dict[str, Dict[str, str]] = {
    "Aries":       {"start": "03-21", "end": "04-19"},
    "Taurus":      {"start": "04-20", "end": "05-20"},
    "Gemini":      {"start": "05-21", "end": "06-20"},
    "Cancer":      {"start": "06-21", "end": "07-22"},
    "Leo":         {"start": "07-23", "end": "08-22"},
    "Virgo":       {"start": "08-23", "end": "09-22"},
    "Libra":       {"start": "09-23", "end": "10-22"},
    "Scorpio":     {"start": "10-23", "end": "11-21"},
    "Sagittarius": {"start": "11-22", "end": "12-21"},
    "Capricorn":   {"start": "12-22", "end": "01-19"},
    "Aquarius":    {"start": "01-20", "end": "02-18"},
    "Pisces":      {"start": "02-19", "end": "03-20"},
}

# Best viewing seasons for constellations
_CONSTELLATION_SEASONS: Dict[str, str] = {
    "Orion": "Winter", "Ursa Major": "Spring", "Ursa Minor": "Year-round",
    "Cassiopeia": "Autumn", "Leo": "Spring", "Scorpius": "Summer",
    "Gemini": "Winter", "Taurus": "Winter", "Cygnus": "Summer",
    "Lyra": "Summer", "Aquila": "Summer", "Canis Major": "Winter",
}

# Additional metadata for constellations
_CONSTELLATION_METADATA: Dict[str, dict] = {
    "Orion": {"mythology": "The Hunter of Greek mythology, placed among the stars by Zeus.", "distance_note": "Stars range from 245 to 1,344 light-years"},
    "Ursa Major": {"mythology": "The Great Bear — Callisto transformed by Zeus to protect her from Hera's jealousy.", "distance_note": "Big Dipper stars ~80 light-years"},
    "Ursa Minor": {"mythology": "The Little Bear — Arcas, son of Callisto, placed near his mother in the sky.", "distance_note": "Polaris is 433 light-years away"},
    "Cassiopeia": {"mythology": "The vain queen of Ethiopia, chained to her throne in the sky as punishment.", "distance_note": "Stars range from 54 to 613 light-years"},
    "Leo": {"mythology": "The Nemean Lion slain by Heracles as the first of his twelve labors.", "distance_note": "Regulus is 79 light-years away"},
    "Scorpius": {"mythology": "The scorpion sent by Gaia to slay Orion — they were placed on opposite sides of the sky.", "distance_note": "Antares is 550 light-years away"},
    "Gemini": {"mythology": "The twins Castor and Pollux — one mortal, one divine, inseparable in life and death.", "distance_note": "Pollux is 34 light-years away"},
    "Taurus": {"mythology": "The bull form Zeus took to carry Europa across the sea to Crete.", "distance_note": "Aldebaran is 65 light-years away"},
    "Cygnus": {"mythology": "The swan form of Zeus, or Orpheus placed in the sky near his lyre.", "distance_note": "Deneb is ~2,600 light-years away"},
    "Lyra": {"mythology": "The lyre of Orpheus, whose music could charm all living things.", "distance_note": "Vega is 25 light-years away"},
    "Aquila": {"mythology": "The eagle of Zeus who carried Ganymede to Mount Olympus.", "distance_note": "Altair is 17 light-years away"},
    "Canis Major": {"mythology": "The faithful hunting dog of Orion, following him across the sky.", "distance_note": "Sirius is 8.6 light-years away"},
}

# Zodiac sign metadata
_ZODIAC_METADATA: Dict[str, dict] = {
    "Aries": {"ruling_planet": "Mars", "quality": "Cardinal", "symbol": "Ram"},
    "Taurus": {"ruling_planet": "Venus", "quality": "Fixed", "symbol": "Bull"},
    "Gemini": {"ruling_planet": "Mercury", "quality": "Mutable", "symbol": "Twins"},
    "Cancer": {"ruling_planet": "Moon", "quality": "Cardinal", "symbol": "Crab"},
    "Leo": {"ruling_planet": "Sun", "quality": "Fixed", "symbol": "Lion"},
    "Virgo": {"ruling_planet": "Mercury", "quality": "Mutable", "symbol": "Maiden"},
    "Libra": {"ruling_planet": "Venus", "quality": "Cardinal", "symbol": "Scales"},
    "Scorpio": {"ruling_planet": "Pluto", "quality": "Fixed", "symbol": "Scorpion"},
    "Sagittarius": {"ruling_planet": "Jupiter", "quality": "Mutable", "symbol": "Archer"},
    "Capricorn": {"ruling_planet": "Saturn", "quality": "Cardinal", "symbol": "Sea-Goat"},
    "Aquarius": {"ruling_planet": "Uranus", "quality": "Fixed", "symbol": "Water-Bearer"},
    "Pisces": {"ruling_planet": "Neptune", "quality": "Mutable", "symbol": "Fish"},
}


def _build_full_catalog() -> Dict[str, dict]:
    """Build the complete atlas catalog from all game data sources.

    Returns:
        Dict of object_id → object metadata.
    """
    catalog = {}

    # 1. Constellations (12)
    for const_name, const_data in _CONSTELLATION_DATA.items():
        obj_id = f"const_{const_name.lower().replace(' ', '_')}"
        meta = _CONSTELLATION_METADATA.get(const_name, {})
        catalog[obj_id] = {
            "id": obj_id,
            "name": const_name,
            "category": "constellations",
            "type": "constellation",
            "difficulty": const_data["difficulty"],
            "fun_fact": const_data["fun_fact"],
            "star_count": len(const_data["stars"]),
            "mythology": meta.get("mythology", ""),
            "distance_note": meta.get("distance_note", ""),
            "best_season": _CONSTELLATION_SEASONS.get(const_name, "Year-round"),
        }

        # 2. Stars from each constellation (77 total)
        for star in const_data["stars"]:
            star_id = f"star_{star['id']}"
            catalog[star_id] = {
                "id": star_id,
                "name": star["name"],
                "category": "stars",
                "type": "star",
                "constellation": const_name,
                "magnitude": star["magnitude"],
                "spectral_type": star["spectral_type"],
                "best_season": _CONSTELLATION_SEASONS.get(const_name, "Year-round"),
            }

    # 3. Deep-sky objects (15)
    for obj in _CELESTIAL_OBJECTS:
        obj_id = f"dso_{obj['id']}"
        catalog[obj_id] = {
            "id": obj_id,
            "name": obj["name"],
            "category": "objects",
            "type": obj["type"],
            "ra": obj["ra"],
            "dec": obj["dec"],
            "magnitude": obj["magnitude"],
            "description": obj["hint"],
        }

    # 4. Zodiac signs (12)
    for sign in ZODIAC_SIGNS:
        sign_id = f"zodiac_{sign.lower()}"
        meta = _ZODIAC_METADATA.get(sign, {})
        season = _ZODIAC_SEASONS.get(sign, {})
        catalog[sign_id] = {
            "id": sign_id,
            "name": sign,
            "category": "signs",
            "type": "zodiac_sign",
            "element": ELEMENTS.get(sign, ""),
            "ruling_planet": meta.get("ruling_planet", ""),
            "quality": meta.get("quality", ""),
            "symbol": meta.get("symbol", ""),
            "season_start": season.get("start", ""),
            "season_end": season.get("end", ""),
        }

    return catalog


# Cache the catalog (built once on import)
_CATALOG: Dict[str, dict] = {}


def _get_catalog() -> Dict[str, dict]:
    """Get or build the catalog (lazy singleton)."""
    global _CATALOG
    if not _CATALOG:
        _CATALOG = _build_full_catalog()
    return _CATALOG


# ────────────────────────────────────────────────────────────────
# Data Model
# ────────────────────────────────────────────────────────────────

@dataclass
class StarAtlasData:
    """Player's star atlas state."""
    player_id: str
    discovered: Dict[str, dict] = field(default_factory=dict)
    mission_archive: List[dict] = field(default_factory=list)
    cosmic_passport: Dict[str, dict] = field(default_factory=dict)


# ────────────────────────────────────────────────────────────────
# Persistence
# ────────────────────────────────────────────────────────────────

def _load_atlas(player_id: str) -> StarAtlasData:
    """Load player's star atlas from disk."""
    safe_id = _sanitize_player_id(player_id)
    path = STAR_ATLAS_DIR / f"{safe_id}.json"
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                d = json.load(f)
            return StarAtlasData(
                player_id=player_id,
                discovered=d.get("discovered", {}),
                mission_archive=d.get("mission_archive", []),
                cosmic_passport=d.get("cosmic_passport", {}),
            )
        except (json.JSONDecodeError, IOError):
            pass
    return StarAtlasData(player_id=player_id)


def _save_atlas(atlas: StarAtlasData) -> None:
    """Save player's star atlas to disk."""
    _ensure_dir(STAR_ATLAS_DIR)
    safe_id = _sanitize_player_id(atlas.player_id)
    path = STAR_ATLAS_DIR / f"{safe_id}.json"
    d = {
        "player_id": atlas.player_id,
        "discovered": atlas.discovered,
        "mission_archive": atlas.mission_archive[-MAX_MISSION_ARCHIVE:],
        "cosmic_passport": atlas.cosmic_passport,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2)


def _get_current_zodiac_season() -> Optional[str]:
    """Determine which zodiac season we're currently in."""
    today = date.today()
    month_day = today.strftime("%m-%d")

    for sign, dates in _ZODIAC_SEASONS.items():
        start = dates["start"]
        end = dates["end"]

        # Handle Capricorn which spans year boundary
        if start > end:  # e.g., 12-22 to 01-19
            if month_day >= start or month_day <= end:
                return sign
        else:
            if start <= month_day <= end:
                return sign

    return None


def _calculate_stats(atlas: StarAtlasData) -> dict:
    """Calculate discovery statistics."""
    catalog = _get_catalog()

    # Category counts
    categories = {"constellations": 0, "stars": 0, "objects": 0, "signs": 0}
    category_totals = {"constellations": 0, "stars": 0, "objects": 0, "signs": 0}

    for obj_id, obj in catalog.items():
        cat = obj["category"]
        if cat in category_totals:
            category_totals[cat] += 1
            if obj_id in atlas.discovered:
                categories[cat] += 1

    total_discovered = sum(categories.values())
    total_objects = sum(category_totals.values())

    stats = {
        "total_discovered": total_discovered,
        "total_objects": total_objects,
        "completion_percent": round((total_discovered / total_objects * 100) if total_objects else 0, 1),
        "categories": {},
    }

    for cat in categories:
        total = category_totals[cat]
        found = categories[cat]
        stats["categories"][cat] = {
            "discovered": found,
            "total": total,
            "percent": round((found / total * 100) if total else 0, 1),
        }

    # Passport stats
    passport_collected = sum(1 for v in atlas.cosmic_passport.values() if v.get("collected"))
    stats["passport_stamps"] = passport_collected
    stats["passport_total"] = 12

    return stats


# ────────────────────────────────────────────────────────────────
# API Functions
# ────────────────────────────────────────────────────────────────

def get_atlas(player_id: str) -> dict:
    """Get the full star atlas with discovery stats.

    Returns:
        Dict with catalog summary, stats, and recent discoveries.
    """
    atlas = _load_atlas(player_id)
    catalog = _get_catalog()
    stats = _calculate_stats(atlas)

    # Recent discoveries (last 10)
    recent = sorted(
        atlas.discovered.items(),
        key=lambda x: x[1].get("date", ""),
        reverse=True,
    )[:10]

    recent_list = []
    for obj_id, disc in recent:
        obj = catalog.get(obj_id, {})
        recent_list.append({
            "object_id": obj_id,
            "name": obj.get("name", obj_id),
            "category": obj.get("category", "unknown"),
            "discovered_date": disc.get("date", ""),
            "source": disc.get("source", "unknown"),
        })

    return {
        "stats": stats,
        "recent_discoveries": recent_list,
        "current_zodiac_season": _get_current_zodiac_season(),
    }


def get_atlas_category(player_id: str, category: str) -> dict:
    """Get detailed view of a specific atlas category.

    Args:
        player_id: Player identifier.
        category: One of: constellations, stars, objects, signs.

    Returns:
        Dict with all objects in category and discovery status.
    """
    valid_categories = ["constellations", "stars", "objects", "signs"]
    if category not in valid_categories:
        return {"error": f"Invalid category. Must be one of: {', '.join(valid_categories)}"}

    atlas = _load_atlas(player_id)
    catalog = _get_catalog()

    objects = []
    for obj_id, obj in catalog.items():
        if obj["category"] != category:
            continue

        discovered = obj_id in atlas.discovered
        entry = {**obj, "discovered": discovered}
        if discovered:
            entry["discovered_date"] = atlas.discovered[obj_id].get("date", "")
            entry["discovered_source"] = atlas.discovered[obj_id].get("source", "")
        objects.append(entry)

    # Sort: discovered first, then by name
    objects.sort(key=lambda x: (not x["discovered"], x["name"]))

    discovered_count = sum(1 for o in objects if o["discovered"])
    return {
        "category": category,
        "objects": objects,
        "discovered": discovered_count,
        "total": len(objects),
        "percent": round((discovered_count / len(objects) * 100) if objects else 0, 1),
    }


def discover_object(player_id: str, object_id: str, source: str = "manual") -> dict:
    """Mark an astronomical object as discovered.

    Args:
        player_id: Player identifier.
        object_id: The object to discover (must be in catalog).
        source: How the object was discovered.

    Returns:
        Dict with discovery result and any passport stamps earned.
    """
    catalog = _get_catalog()

    if object_id not in catalog:
        return {"error": f"Unknown object: {object_id}"}

    if source not in VALID_DISCOVERY_SOURCES:
        source = "manual"

    atlas = _load_atlas(player_id)
    obj = catalog[object_id]
    today = date.today().isoformat()
    events = []

    # Check if already discovered
    already_known = object_id in atlas.discovered
    if not already_known:
        atlas.discovered[object_id] = {
            "type": obj["category"],
            "date": today,
            "source": source,
        }
        events.append({"type": "new_discovery", "object": obj["name"], "category": obj["category"]})

    # Check cosmic passport — if discovering a zodiac sign during its season
    if obj["category"] == "signs":
        sign_name = obj["name"]
        current_season = _get_current_zodiac_season()
        if current_season and current_season == sign_name:
            if sign_name not in atlas.cosmic_passport or not atlas.cosmic_passport[sign_name].get("collected"):
                atlas.cosmic_passport[sign_name] = {
                    "collected": True,
                    "date": today,
                }
                events.append({"type": "passport_stamp", "sign": sign_name, "season": True})

    _save_atlas(atlas)

    stats = _calculate_stats(atlas)
    return {
        "success": True,
        "object_id": object_id,
        "object_name": obj["name"],
        "category": obj["category"],
        "new_discovery": not already_known,
        "events": events,
        "stats": stats,
    }


def get_mission_archive(player_id: str) -> dict:
    """Get the mission archive (rolling 100 completed missions).

    Returns:
        Dict with mission log entries.
    """
    atlas = _load_atlas(player_id)
    return {
        "missions": atlas.mission_archive[-MAX_MISSION_ARCHIVE:],
        "total_missions": len(atlas.mission_archive),
    }


def add_mission_entry(player_id: str, mission_type: str, score: int, cosmic_context: str = "") -> dict:
    """Add a completed mission to the archive.

    Args:
        player_id: Player identifier.
        mission_type: Type of mission completed.
        score: Score achieved.
        cosmic_context: Cosmic context at time of completion.

    Returns:
        Dict confirming the addition.
    """
    atlas = _load_atlas(player_id)
    today = date.today().isoformat()

    entry = {
        "date": today,
        "mission_type": mission_type,
        "score": score,
        "cosmic_context": cosmic_context,
    }
    atlas.mission_archive.append(entry)
    atlas.mission_archive = atlas.mission_archive[-MAX_MISSION_ARCHIVE:]

    _save_atlas(atlas)
    return {"success": True, "entry": entry, "total_missions": len(atlas.mission_archive)}


def get_cosmic_passport(player_id: str) -> dict:
    """Get the cosmic passport with seasonal stamps.

    Returns:
        Dict with all 12 zodiac stamps and collection status.
    """
    atlas = _load_atlas(player_id)
    current_season = _get_current_zodiac_season()

    stamps = []
    for sign in ZODIAC_SIGNS:
        season_data = _ZODIAC_SEASONS.get(sign, {})
        passport_entry = atlas.cosmic_passport.get(sign, {})
        meta = _ZODIAC_METADATA.get(sign, {})

        stamps.append({
            "sign": sign,
            "element": ELEMENTS.get(sign, ""),
            "symbol": meta.get("symbol", ""),
            "season_start": season_data.get("start", ""),
            "season_end": season_data.get("end", ""),
            "collected": passport_entry.get("collected", False),
            "collected_date": passport_entry.get("date", ""),
            "is_current_season": current_season == sign,
        })

    collected_count = sum(1 for s in stamps if s["collected"])
    return {
        "stamps": stamps,
        "collected": collected_count,
        "total": 12,
        "percent": round((collected_count / 12) * 100, 1),
        "current_season": current_season,
    }

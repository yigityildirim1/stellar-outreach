"""
NEXUS STATION - Stellar Outreach: Station Visual Customization (TASK-014)

Aesthetic customization system for player stations. Supports station skins,
module visual upgrades, element-themed color accents, decorations earned
from gameplay, and prestige visual indicators.

Design Language (GDD §12):
    Base aesthetic: 1970s retrofuturism — warm amber terminals, brass fittings,
    mechanical precision with human warmth. Customization extends this palette
    without breaking coherence.

Features:
    - Station skins: 8 thematic skins (base + 7 unlockable)
    - Module visual tiers: 4 visual tiers per module (levels 1/3/5/10)
    - Element-themed accents: Fire/Earth/Air/Water color palettes
    - Decorations: 20 decorations earned from streaks, NPC perks, atlas, guilds
    - Preview system: preview any skin/decoration before applying
    - Prestige indicators: special visuals at station level 50+

Ethics Note (Dr. Elena Vasquez review):
    All cosmetics are earned through gameplay, not purchased. No pay-to-win.
    Prestige is celebratory, not exclusionary. Every player's station is warm.

Security Note (Article II / Kai Chen review):
    Customization data persisted per player_id with sanitized paths.
    Skin/decoration IDs validated against known catalogs.

UX Note (Marina Okonkwo review):
    Preview system prevents regret. Element accents create personal connection.
    Visual upgrades provide tangible feedback for module leveling.

References:
    - GDD §6.1: Station level thresholds
    - GDD §12.2: Color palette specifications
    - TASK-003: Station modules and levels
    - TASK-012: Streak milestones for decorations
    - TASK-009: NPC perks for decorations
    - TASK-013: Atlas completion for decorations
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from narrative_agentic.stellar_outreach.birth_chart import ELEMENTS
from narrative_agentic.stellar_outreach.station_modules import (
    MODULE_DEFINITIONS,
    get_station,
)


# ────────────────────────────────────────────────────────────────
# Persistence Configuration
# ────────────────────────────────────────────────────────────────

CUSTOMIZATION_DIR = Path.home() / ".nexus_station" / "customization"


def _sanitize_player_id(player_id: str) -> str:
    """Sanitize a player ID for safe filesystem use."""
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in player_id)


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


# ────────────────────────────────────────────────────────────────
# Color Palette (GDD §12.2)
# ────────────────────────────────────────────────────────────────

# Base station palette — warm amber retrofuturism
BASE_PALETTE: Dict[str, str] = {
    "primary": "#D4890E",       # warm amber
    "secondary": "#3D2B1F",     # deep brown
    "accent": "#B8860B",        # brass/dark goldenrod
    "background": "#1A1208",    # near-black warm
    "surface": "#2A1F12",       # dark warm panel
    "text": "#F5E6C8",          # soft cream
    "text_dim": "#A89070",      # muted warm
    "success": "#6B8E23",       # olive drab
    "warning": "#CD853F",       # peru
    "danger": "#8B3A3A",        # dark red muted
}

# Element-themed accent palettes
ELEMENT_PALETTES: Dict[str, Dict[str, str]] = {
    "Fire": {
        "accent_primary": "#C0392B",    # deep red
        "accent_secondary": "#E67E22",  # orange
        "accent_highlight": "#F1C40F",  # gold
        "accent_glow": "#FF6B35",       # warm glow
    },
    "Earth": {
        "accent_primary": "#27AE60",    # forest green
        "accent_secondary": "#A0522D",  # terra cotta/sienna
        "accent_highlight": "#8B6914",  # dark goldenrod brown
        "accent_glow": "#6B8E23",       # olive
    },
    "Air": {
        "accent_primary": "#5DADE2",    # sky blue
        "accent_secondary": "#BDC3C7",  # silver
        "accent_highlight": "#BB8FCE",  # lavender
        "accent_glow": "#85C1E9",       # light blue glow
    },
    "Water": {
        "accent_primary": "#2C3E8C",    # deep blue
        "accent_secondary": "#1ABC9C",  # teal
        "accent_highlight": "#ECF0F1",  # pearl
        "accent_glow": "#3498DB",       # blue glow
    },
}


# ────────────────────────────────────────────────────────────────
# Station Skins
# ────────────────────────────────────────────────────────────────

STATION_SKINS: Dict[str, dict] = {
    "standard_amber": {
        "name": "Standard Amber",
        "description": "The default NEXUS Station aesthetic. Warm amber terminals, brass fittings, the hum of reliable machinery.",
        "unlock_condition": "default",
        "unlock_description": "Available to all stations",
        "palette_overrides": {},
        "visual_class": "skin-standard",
    },
    "deep_space_noir": {
        "name": "Deep Space Noir",
        "description": "Darker tones, cooler contrasts. The station whispers in shadow and silver — for those who prefer mystery to warmth.",
        "unlock_condition": "station_level_10",
        "unlock_description": "Reach Station Level 10",
        "palette_overrides": {
            "primary": "#708090",
            "secondary": "#1C1C2E",
            "accent": "#C0C0C0",
            "background": "#0A0A14",
            "surface": "#16162A",
        },
        "visual_class": "skin-noir",
    },
    "solar_flare": {
        "name": "Solar Flare",
        "description": "Blazing golds and deep reds — as if the station orbited too close to a star. Bold, bright, and unapologetic.",
        "unlock_condition": "station_level_20",
        "unlock_description": "Reach Station Level 20",
        "palette_overrides": {
            "primary": "#FF8C00",
            "secondary": "#4A0E0E",
            "accent": "#FFD700",
            "background": "#1A0800",
            "surface": "#2E1200",
        },
        "visual_class": "skin-flare",
    },
    "nebula_garden": {
        "name": "Nebula Garden",
        "description": "Soft greens and bioluminescent accents. The greenhouse has taken over — and it's beautiful.",
        "unlock_condition": "module_greenhouse_level_7",
        "unlock_description": "Reach Greenhouse Module Level 7",
        "palette_overrides": {
            "primary": "#2ECC71",
            "secondary": "#1A2F1A",
            "accent": "#27AE60",
            "background": "#0A140A",
            "surface": "#142814",
        },
        "visual_class": "skin-nebula-garden",
    },
    "cosmic_archive": {
        "name": "Cosmic Archive",
        "description": "Parchment tones and constellation overlays. The Archivist's aesthetic — every surface tells a story.",
        "unlock_condition": "atlas_50_percent",
        "unlock_description": "Discover 50% of the Star Atlas",
        "palette_overrides": {
            "primary": "#D2B48C",
            "secondary": "#2F1B14",
            "accent": "#8B7355",
            "background": "#140E08",
            "surface": "#261A10",
        },
        "visual_class": "skin-archive",
    },
    "crew_quarters": {
        "name": "Crew Quarters",
        "description": "Soft lighting, worn leather, shared meals. The station feels like home — because it is.",
        "unlock_condition": "npc_all_level_5",
        "unlock_description": "Reach Level 5 with all 6 NPCs",
        "palette_overrides": {
            "primary": "#CD853F",
            "secondary": "#2B1810",
            "accent": "#DEB887",
            "background": "#120C06",
            "surface": "#221608",
        },
        "visual_class": "skin-quarters",
    },
    "constellation_crew": {
        "name": "Constellation Crew",
        "description": "Star-map overlays and crew insignia. A skin that celebrates your guild and the bonds between explorers.",
        "unlock_condition": "guild_member",
        "unlock_description": "Join a Constellation Crew (Guild)",
        "palette_overrides": {
            "primary": "#9B59B6",
            "secondary": "#1A0E2E",
            "accent": "#8E44AD",
            "background": "#0E0618",
            "surface": "#1C0E30",
        },
        "visual_class": "skin-constellation",
    },
    "prestige_gold": {
        "name": "Prestige Gold",
        "description": "Polished gold, white marble, celestial engravings. Reserved for those who have seen everything and started again.",
        "unlock_condition": "station_level_50",
        "unlock_description": "Reach Station Level 50 (Prestige)",
        "palette_overrides": {
            "primary": "#FFD700",
            "secondary": "#1A1400",
            "accent": "#DAA520",
            "background": "#0E0C00",
            "surface": "#1E1A00",
            "text": "#FFFDE7",
        },
        "visual_class": "skin-prestige",
    },
}


# ────────────────────────────────────────────────────────────────
# Module Visual Tiers
# ────────────────────────────────────────────────────────────────

# Each module has 4 visual tiers unlocked at specific levels
MODULE_VISUAL_TIERS: Dict[int, dict] = {
    1: {
        "tier": 1,
        "name": "Basic",
        "description": "Standard-issue equipment. Functional, reliable, unadorned.",
        "visual_class": "tier-basic",
        "particle_effect": None,
    },
    3: {
        "tier": 2,
        "name": "Improved",
        "description": "Polished surfaces, indicator lights, the first signs of care.",
        "visual_class": "tier-improved",
        "particle_effect": "subtle_glow",
    },
    5: {
        "tier": 3,
        "name": "Advanced",
        "description": "Custom fittings, ambient lighting, a module that takes pride in its work.",
        "visual_class": "tier-advanced",
        "particle_effect": "ambient_particles",
    },
    10: {
        "tier": 4,
        "name": "Masterwork",
        "description": "Every detail perfected. Brass engravings, holographic displays, the pinnacle of station craft.",
        "visual_class": "tier-masterwork",
        "particle_effect": "masterwork_aura",
    },
}

# Module-specific visual descriptions at each tier
_MODULE_TIER_FLAVORS: Dict[str, Dict[int, str]] = {
    "bridge": {
        1: "A utilitarian command console with flickering readouts.",
        3: "Polished brass controls, a captain's chair with real leather.",
        5: "Holographic star map above the console, priority comm indicators glow amber.",
        10: "The Admiral's Bridge — panoramic viewport, gilded command throne, constellation ceiling.",
    },
    "quarters": {
        1: "Standard bunks, fluorescent lighting, recycled air.",
        3: "Soft blankets, a reading lamp, the scent of clean laundry.",
        5: "Private alcoves, hydroponic window box, sleep cycle lighting.",
        10: "Luxury suites — gravity-adjusted beds, personal climate, meditation corner.",
    },
    "observatory": {
        1: "A basic telescope mount and data terminal.",
        3: "Spectral analyzer installed, star chart projections on the dome.",
        5: "Deep-sky scanner array, quantum-stabilized optics, research workstation.",
        10: "The Celestial Cartography Lab — full-dome immersive starfield, discovery amplification array.",
    },
    "greenhouse": {
        1: "A few grow-trays under fluorescent lights.",
        3: "Copper trellises, exotic seedlings, bioluminescent moss accents.",
        5: "Full garden with simulated sunlight, aromatic herb wall, crew bonding alcove.",
        10: "The Soul Garden — terraforming preview dome, eternal bloom specimens, empathy resonance field.",
    },
    "commons": {
        1: "Long table, folding chairs, a bulletin board.",
        3: "Trade board installed, alliance flags on the walls, proper seating.",
        5: "Market analytics display, diplomatic lounge with comfortable chairs.",
        10: "The Interstellar Exchange — cultural embassy decor, galactic bazaar hologram, trade monarch's table.",
    },
    "shrine": {
        1: "A quiet alcove with a single candle and star chart.",
        3: "Meditation cushions, lore fragment collector glowing faintly.",
        5: "Vision chamber with star whisper decoder, ancient signal receiver.",
        10: "The Cosmic Oracle — transcendence gate shimmer, stardust forge altar, astral projection suite.",
    },
    "workshop": {
        1: "Workbench, basic tools, a welding torch.",
        3: "Smelting furnace, blueprint drafting table, organized tool wall.",
        5: "Automated assembly line, advanced alloy samples on display.",
        10: "The Titan Forge — masterwork bench with infinite schematic library, nanofabrication bay.",
    },
}


# ────────────────────────────────────────────────────────────────
# Decorations
# ────────────────────────────────────────────────────────────────

DECORATIONS: Dict[str, dict] = {
    # Streak decorations
    "streak_flame_3": {
        "name": "Ember Flame",
        "description": "A small holographic flame that flickers on your station dashboard. 3-day streak reward.",
        "category": "streak",
        "source": "streak_3_days",
        "slot": "dashboard",
        "rarity": "common",
    },
    "streak_flame_7": {
        "name": "Steady Flame",
        "description": "A stronger flame with amber core. 7-day streak reward.",
        "category": "streak",
        "source": "streak_7_days",
        "slot": "dashboard",
        "rarity": "uncommon",
    },
    "streak_flame_14": {
        "name": "Constellation Flame",
        "description": "A flame that traces constellation patterns. 14-day streak reward.",
        "category": "streak",
        "source": "streak_14_days",
        "slot": "dashboard",
        "rarity": "rare",
    },
    "streak_flame_30": {
        "name": "Cosmic Fire",
        "description": "A nebula-colored flame that hums softly. 30-day streak reward.",
        "category": "streak",
        "source": "streak_30_days",
        "slot": "dashboard",
        "rarity": "epic",
    },
    "streak_flame_100": {
        "name": "Eternal Flame",
        "description": "A transcendent flame that never wavers. 100-day streak mastery.",
        "category": "streak",
        "source": "streak_100_days",
        "slot": "dashboard",
        "rarity": "legendary",
    },
    # NPC decorations
    "npc_reyes_portrait": {
        "name": "Commander's Portrait",
        "description": "A brass-framed portrait of Commander Reyes, eyes on the horizon.",
        "category": "npc",
        "source": "npc_cmdr_reyes_level_10",
        "slot": "wall",
        "rarity": "epic",
    },
    "npc_okafor_specimen": {
        "name": "Okafor's Specimen Jar",
        "description": "A bioluminescent sample from Dr. Okafor's collection, glowing faintly green.",
        "category": "npc",
        "source": "npc_dr_okafor_level_10",
        "slot": "shelf",
        "rarity": "epic",
    },
    "npc_jin_circuit": {
        "name": "Jin's Perfect Circuit",
        "description": "The legendary perfect circuit board under glass — every trace flawless.",
        "category": "npc",
        "source": "npc_tech_jin_level_10",
        "slot": "shelf",
        "rarity": "epic",
    },
    "npc_vasquez_badge": {
        "name": "Vasquez's Honor Badge",
        "description": "A security honor badge, polished daily. 'Safe' engraved on the back.",
        "category": "npc",
        "source": "npc_lt_vasquez_level_10",
        "slot": "wall",
        "rarity": "epic",
    },
    "npc_amari_recipe": {
        "name": "Grandmother's Recipe Card",
        "description": "A yellowed recipe card in an unknown script, framed with love.",
        "category": "npc",
        "source": "npc_chef_amari_level_10",
        "slot": "wall",
        "rarity": "epic",
    },
    "npc_lune_datacore": {
        "name": "Lune's First Data Core",
        "description": "One of the original seventeen data cores, still softly glowing.",
        "category": "npc",
        "source": "npc_archivist_lune_level_10",
        "slot": "shelf",
        "rarity": "epic",
    },
    # Atlas decorations
    "atlas_constellation_map": {
        "name": "Constellation Wall Map",
        "description": "A hand-drawn map of all discovered constellations, updated in real-time.",
        "category": "atlas",
        "source": "atlas_constellations_100",
        "slot": "wall",
        "rarity": "rare",
    },
    "atlas_star_chart": {
        "name": "Complete Star Chart",
        "description": "Every star cataloged, every magnitude noted. A cartographer's dream.",
        "category": "atlas",
        "source": "atlas_stars_100",
        "slot": "wall",
        "rarity": "epic",
    },
    "atlas_deep_sky_portfolio": {
        "name": "Deep Sky Portfolio",
        "description": "Holographic renders of every deep-sky object discovered. Galaxies spin lazily.",
        "category": "atlas",
        "source": "atlas_objects_100",
        "slot": "shelf",
        "rarity": "rare",
    },
    "atlas_zodiac_wheel": {
        "name": "Zodiac Wheel",
        "description": "A brass zodiac wheel that slowly rotates to match the current season.",
        "category": "atlas",
        "source": "atlas_signs_100",
        "slot": "dashboard",
        "rarity": "rare",
    },
    "atlas_cosmic_passport_frame": {
        "name": "Cosmic Passport Display",
        "description": "All 12 seasonal stamps collected and framed. The cosmos has been witnessed.",
        "category": "atlas",
        "source": "passport_complete",
        "slot": "wall",
        "rarity": "legendary",
    },
    # Guild decorations
    "guild_banner": {
        "name": "Crew Banner",
        "description": "Your Constellation Crew's banner, proudly displayed at the station entrance.",
        "category": "guild",
        "source": "guild_member",
        "slot": "entrance",
        "rarity": "uncommon",
    },
    "guild_challenge_trophy": {
        "name": "Weekly Challenge Trophy",
        "description": "A gleaming trophy for completing a guild weekly challenge.",
        "category": "guild",
        "source": "guild_challenge_complete",
        "slot": "shelf",
        "rarity": "rare",
    },
    # Prestige
    "prestige_star": {
        "name": "Prestige Star",
        "description": "A golden star that orbits your station — visible proof of mastery and rebirth.",
        "category": "prestige",
        "source": "station_level_50",
        "slot": "exterior",
        "rarity": "legendary",
    },
}


# ────────────────────────────────────────────────────────────────
# Data Model
# ────────────────────────────────────────────────────────────────

@dataclass
class CustomizationData:
    """Player's station customization state."""
    player_id: str
    active_skin: str = "standard_amber"
    unlocked_skins: List[str] = field(default_factory=lambda: ["standard_amber"])
    unlocked_decorations: List[str] = field(default_factory=list)
    active_decorations: Dict[str, str] = field(default_factory=dict)  # slot → decoration_id
    element_accent: str = ""        # player's element for accent colors
    prestige_level: int = 0         # 0 = none, 1+ = prestige tiers
    last_updated: str = ""


# ────────────────────────────────────────────────────────────────
# Persistence
# ────────────────────────────────────────────────────────────────

def _load_customization(player_id: str) -> CustomizationData:
    """Load player's customization data."""
    safe_id = _sanitize_player_id(player_id)
    path = CUSTOMIZATION_DIR / f"{safe_id}.json"
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                d = json.load(f)
            return CustomizationData(
                player_id=player_id,
                active_skin=d.get("active_skin", "standard_amber"),
                unlocked_skins=d.get("unlocked_skins", ["standard_amber"]),
                unlocked_decorations=d.get("unlocked_decorations", []),
                active_decorations=d.get("active_decorations", {}),
                element_accent=d.get("element_accent", ""),
                prestige_level=d.get("prestige_level", 0),
                last_updated=d.get("last_updated", ""),
            )
        except (json.JSONDecodeError, IOError):
            pass
    return CustomizationData(player_id=player_id)


def _save_customization(data: CustomizationData) -> None:
    """Save player's customization data."""
    _ensure_dir(CUSTOMIZATION_DIR)
    safe_id = _sanitize_player_id(data.player_id)
    path = CUSTOMIZATION_DIR / f"{safe_id}.json"
    data.last_updated = datetime.utcnow().isoformat()
    d = {
        "player_id": data.player_id,
        "active_skin": data.active_skin,
        "unlocked_skins": data.unlocked_skins,
        "unlocked_decorations": data.unlocked_decorations,
        "active_decorations": data.active_decorations,
        "element_accent": data.element_accent,
        "prestige_level": data.prestige_level,
        "last_updated": data.last_updated,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2)


# ────────────────────────────────────────────────────────────────
# Unlock Condition Checking
# ────────────────────────────────────────────────────────────────

def _check_skin_unlock(skin_id: str, player_id: str) -> bool:
    """Check if a player meets the unlock condition for a skin."""
    skin = STATION_SKINS.get(skin_id)
    if not skin:
        return False

    condition = skin["unlock_condition"]
    if condition == "default":
        return True

    station = get_station(player_id)

    if condition.startswith("station_level_"):
        required = int(condition.split("_")[-1])
        return station is not None and station.station_level >= required

    if condition.startswith("module_"):
        # e.g., "module_greenhouse_level_7"
        parts = condition.split("_")
        module_id = parts[1]
        required = int(parts[-1])
        if station and module_id in station.modules:
            return station.modules[module_id].level >= required
        return False

    if condition == "atlas_50_percent":
        try:
            from narrative_agentic.stellar_outreach.star_atlas import get_atlas
            atlas = get_atlas(player_id)
            return atlas["stats"]["completion_percent"] >= 50.0
        except Exception:
            return False

    if condition == "npc_all_level_5":
        try:
            from narrative_agentic.stellar_outreach.npc_crew import get_npc_list
            npcs = get_npc_list(player_id)
            return all(npc["level"] >= 5 for npc in npcs["npcs"])
        except Exception:
            return False

    if condition == "guild_member":
        try:
            from narrative_agentic.stellar_outreach.guilds import get_guild
            result = get_guild(player_id)
            return result.get("in_guild", False)
        except Exception:
            return False

    return False


# ────────────────────────────────────────────────────────────────
# API Functions
# ────────────────────────────────────────────────────────────────

def get_customization(player_id: str, sun_sign: str = "") -> dict:
    """Get full customization state for a player.

    Returns:
        Dict with active skin, palette, decorations, module visuals.
    """
    data = _load_customization(player_id)
    station = get_station(player_id)

    # Set element accent if provided and not already set
    if sun_sign and not data.element_accent:
        data.element_accent = ELEMENTS.get(sun_sign, "")
        _save_customization(data)

    # Build effective palette
    skin = STATION_SKINS.get(data.active_skin, STATION_SKINS["standard_amber"])
    palette = {**BASE_PALETTE, **skin.get("palette_overrides", {})}

    # Add element accent colors
    element_colors = ELEMENT_PALETTES.get(data.element_accent, {})

    # Build module visuals
    module_visuals = {}
    if station:
        for mod_id, mod in station.modules.items():
            tier_level = 1
            for lvl in sorted(MODULE_VISUAL_TIERS.keys()):
                if mod.level >= lvl:
                    tier_level = lvl
            tier = MODULE_VISUAL_TIERS[tier_level]
            flavor = _MODULE_TIER_FLAVORS.get(mod_id, {}).get(tier_level, "")
            module_visuals[mod_id] = {
                "module_name": mod.name,
                "module_level": mod.level,
                "visual_tier": tier["tier"],
                "tier_name": tier["name"],
                "tier_description": tier["description"],
                "visual_class": tier["visual_class"],
                "particle_effect": tier["particle_effect"],
                "flavor_text": flavor,
            }

    # Build active decorations detail
    active_deco_detail = {}
    for slot, deco_id in data.active_decorations.items():
        if deco_id in DECORATIONS:
            active_deco_detail[slot] = {
                "decoration_id": deco_id,
                **DECORATIONS[deco_id],
            }

    # Prestige
    prestige = None
    if station and station.station_level >= 50:
        data.prestige_level = max(data.prestige_level, 1)
        _save_customization(data)
        prestige = {
            "level": data.prestige_level,
            "visual_class": "prestige-gold",
            "particle_effect": "prestige_aura",
            "title": "Station Master" if data.prestige_level == 1 else f"Station Master {data.prestige_level}",
        }

    return {
        "active_skin": data.active_skin,
        "skin_name": skin["name"],
        "skin_description": skin["description"],
        "skin_visual_class": skin["visual_class"],
        "palette": palette,
        "element_accent": data.element_accent,
        "element_colors": element_colors,
        "module_visuals": module_visuals,
        "active_decorations": active_deco_detail,
        "prestige": prestige,
    }


def get_available_skins(player_id: str) -> dict:
    """Get all skins with unlock status.

    Returns:
        Dict with list of all skins and their unlock status.
    """
    data = _load_customization(player_id)
    skins = []

    for skin_id, skin in STATION_SKINS.items():
        unlocked = skin_id in data.unlocked_skins
        can_unlock = False
        if not unlocked:
            can_unlock = _check_skin_unlock(skin_id, player_id)
            if can_unlock and skin_id not in data.unlocked_skins:
                data.unlocked_skins.append(skin_id)
                unlocked = True

        skins.append({
            "skin_id": skin_id,
            "name": skin["name"],
            "description": skin["description"],
            "unlock_description": skin["unlock_description"],
            "unlocked": unlocked,
            "active": skin_id == data.active_skin,
            "visual_class": skin["visual_class"],
            "palette_overrides": skin["palette_overrides"],
        })

    # Save if we unlocked new skins
    _save_customization(data)

    unlocked_count = sum(1 for s in skins if s["unlocked"])
    return {
        "skins": skins,
        "unlocked_count": unlocked_count,
        "total_count": len(skins),
    }


def force_unlock_skin(player_id: str, skin_id: str) -> dict:
    """Force-unlock a skin, bypassing condition checks.

    Used by the cosmetic store (TASK-015) for purchased premium skins.

    Args:
        player_id: Player identifier.
        skin_id: Skin to unlock (must exist in STATION_SKINS or PREMIUM_SKIN_DEFINITIONS).

    Returns:
        Dict with unlock result.
    """
    # Register premium skin in STATION_SKINS if not already present
    _ensure_premium_skin_registered(skin_id)

    if skin_id not in STATION_SKINS:
        return {"error": f"Unknown skin: {skin_id}"}

    data = _load_customization(player_id)
    if skin_id in data.unlocked_skins:
        return {"already_unlocked": True, "skin_id": skin_id}

    data.unlocked_skins.append(skin_id)
    _save_customization(data)

    return {
        "success": True,
        "skin_id": skin_id,
        "skin_name": STATION_SKINS[skin_id]["name"],
    }


def _ensure_premium_skin_registered(skin_id: str) -> None:
    """Register a premium skin in STATION_SKINS if it exists in PREMIUM_SKIN_DEFINITIONS."""
    if skin_id in STATION_SKINS:
        return
    try:
        from narrative_agentic.stellar_outreach.cosmetic_store import PREMIUM_SKIN_DEFINITIONS
        if skin_id in PREMIUM_SKIN_DEFINITIONS:
            defn = PREMIUM_SKIN_DEFINITIONS[skin_id]
            STATION_SKINS[skin_id] = {
                "name": defn["name"],
                "description": f"Premium skin — {defn['name']}",
                "unlock_condition": "store_purchase",
                "unlock_description": "Available in the Cosmetic Store",
                "palette_overrides": defn["palette_overrides"],
                "visual_class": defn["visual_class"],
            }
    except Exception:
        pass


def apply_skin(player_id: str, skin_id: str) -> dict:
    """Apply a skin to the player's station.

    Args:
        player_id: Player identifier.
        skin_id: Skin to apply (must be unlocked).

    Returns:
        Dict with result and new palette.
    """
    # Ensure premium skins are registered
    _ensure_premium_skin_registered(skin_id)

    if skin_id not in STATION_SKINS:
        return {"error": f"Unknown skin: {skin_id}"}

    data = _load_customization(player_id)

    # Auto-unlock check
    if skin_id not in data.unlocked_skins:
        if _check_skin_unlock(skin_id, player_id):
            data.unlocked_skins.append(skin_id)
        else:
            return {"error": f"Skin '{STATION_SKINS[skin_id]['name']}' is locked. {STATION_SKINS[skin_id]['unlock_description']}"}

    data.active_skin = skin_id
    _save_customization(data)

    skin = STATION_SKINS[skin_id]
    palette = {**BASE_PALETTE, **skin.get("palette_overrides", {})}

    return {
        "success": True,
        "skin_id": skin_id,
        "skin_name": skin["name"],
        "palette": palette,
        "visual_class": skin["visual_class"],
    }


def preview_skin(skin_id: str, element: str = "") -> dict:
    """Preview a skin without applying it.

    Args:
        skin_id: Skin to preview.
        element: Optional element for accent colors.

    Returns:
        Dict with full palette preview.
    """
    if skin_id not in STATION_SKINS:
        return {"error": f"Unknown skin: {skin_id}"}

    skin = STATION_SKINS[skin_id]
    palette = {**BASE_PALETTE, **skin.get("palette_overrides", {})}
    element_colors = ELEMENT_PALETTES.get(element, {})

    return {
        "preview": True,
        "skin_id": skin_id,
        "skin_name": skin["name"],
        "description": skin["description"],
        "palette": palette,
        "element_colors": element_colors,
        "visual_class": skin["visual_class"],
    }


def get_available_decorations(player_id: str) -> dict:
    """Get all decorations with unlock status.

    Returns:
        Dict with decoration list grouped by category.
    """
    data = _load_customization(player_id)

    by_category = {}
    for deco_id, deco in DECORATIONS.items():
        cat = deco["category"]
        if cat not in by_category:
            by_category[cat] = []

        by_category[cat].append({
            "decoration_id": deco_id,
            "name": deco["name"],
            "description": deco["description"],
            "slot": deco["slot"],
            "rarity": deco["rarity"],
            "unlocked": deco_id in data.unlocked_decorations,
            "active": deco_id in data.active_decorations.values(),
            "source": deco["source"],
        })

    unlocked_count = sum(1 for d in data.unlocked_decorations if d in DECORATIONS)
    return {
        "decorations": by_category,
        "unlocked_count": unlocked_count,
        "total_count": len(DECORATIONS),
    }


def unlock_decoration(player_id: str, decoration_id: str) -> dict:
    """Unlock a decoration for a player.

    Called by other systems (streaks, NPCs, atlas) when conditions are met.

    Args:
        player_id: Player identifier.
        decoration_id: Decoration to unlock.

    Returns:
        Dict with unlock result.
    """
    if decoration_id not in DECORATIONS:
        return {"error": f"Unknown decoration: {decoration_id}"}

    data = _load_customization(player_id)

    if decoration_id in data.unlocked_decorations:
        return {"already_unlocked": True, "decoration": DECORATIONS[decoration_id]}

    data.unlocked_decorations.append(decoration_id)
    _save_customization(data)

    deco = DECORATIONS[decoration_id]
    return {
        "success": True,
        "new_unlock": True,
        "decoration_id": decoration_id,
        "name": deco["name"],
        "description": deco["description"],
        "rarity": deco["rarity"],
        "slot": deco["slot"],
    }


def apply_decoration(player_id: str, decoration_id: str) -> dict:
    """Apply an unlocked decoration to its slot.

    Args:
        player_id: Player identifier.
        decoration_id: Decoration to apply (must be unlocked).

    Returns:
        Dict with result.
    """
    if decoration_id not in DECORATIONS:
        return {"error": f"Unknown decoration: {decoration_id}"}

    data = _load_customization(player_id)

    if decoration_id not in data.unlocked_decorations:
        return {"error": f"Decoration '{DECORATIONS[decoration_id]['name']}' is locked."}

    deco = DECORATIONS[decoration_id]
    slot = deco["slot"]

    # Replace whatever is in that slot
    data.active_decorations[slot] = decoration_id
    _save_customization(data)

    return {
        "success": True,
        "decoration_id": decoration_id,
        "name": deco["name"],
        "slot": slot,
        "active_decorations": data.active_decorations,
    }


def remove_decoration(player_id: str, slot: str) -> dict:
    """Remove a decoration from a slot.

    Args:
        player_id: Player identifier.
        slot: Slot to clear.

    Returns:
        Dict with result.
    """
    data = _load_customization(player_id)

    if slot not in data.active_decorations:
        return {"error": f"No decoration in slot '{slot}'."}

    removed = data.active_decorations.pop(slot)
    _save_customization(data)

    return {
        "success": True,
        "removed": removed,
        "slot": slot,
        "active_decorations": data.active_decorations,
    }


def get_element_palette(sun_sign: str) -> dict:
    """Get the element accent palette for a zodiac sign.

    Args:
        sun_sign: Zodiac sign name.

    Returns:
        Dict with element, base palette, and accent colors.
    """
    element = ELEMENTS.get(sun_sign, "")
    accent = ELEMENT_PALETTES.get(element, {})

    return {
        "sun_sign": sun_sign,
        "element": element,
        "base_palette": BASE_PALETTE,
        "accent_colors": accent,
    }

"""
NEXUS STATION - Stellar Outreach: Crew NPC System (TASK-009)

Full relationship progression system for the 6 station NPCs introduced in
TASK-008 Crew Diplomacy. Each NPC has 10 relationship levels, backstory
chapters unlocked at even levels, and gameplay perks at 3/5/7/10.

Features:
    - 10 relationship levels (XP-based progression)
    - 5 backstory chapters per NPC (levels 2, 4, 6, 8, 10)
    - Gameplay perks: resource discount, daily mission, crafting recipe, cosmetic
    - Daily interaction (1 free/NPC/day, 20 base XP, streak bonus)
    - Gift system (spend resources for bonus XP)
    - Cosmic mood integration from transit system

Ethics Note (Dr. Elena Vasquez review):
    NPC relationships use positive-sum design. No punishments for missed days.
    Backstory chapters reward engagement with narrative, not gatekeeping content.

Security Note (Article II / Kai Chen review):
    NPC data persisted per player_id with sanitized paths.
    Gift amounts capped to prevent resource manipulation.

References:
    - TASK-008: NPC database and diplomacy system
    - TASK-003: Station module resource integration
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional

from narrative_agentic.stellar_outreach.mini_games_phase2 import (
    _NPC_DATABASE,
    _COSMIC_MOOD_SHIFTS,
)
from narrative_agentic.stellar_outreach.station_modules import (
    get_station,
    save_station,
)


# ────────────────────────────────────────────────────────────────
# Persistence Configuration
# ────────────────────────────────────────────────────────────────

NPC_CREW_DIR = Path.home() / ".nexus_station" / "npc_crew"


def _sanitize_player_id(player_id: str) -> str:
    """Sanitize a player ID for safe filesystem use."""
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in player_id)


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


# ────────────────────────────────────────────────────────────────
# Constants
# ────────────────────────────────────────────────────────────────

# NPC → station module mapping
NPC_MODULE_MAP: Dict[str, str] = {
    "cmdr_reyes": "bridge",
    "dr_okafor": "quarters",
    "tech_jin": "workshop",
    "lt_vasquez": "commons",
    "chef_amari": "greenhouse",
    "archivist_lune": "shrine",
}

# XP required to advance from level N to N+1: N * 100
# Total XP for level N: sum(i*100 for i in range(1, N))
_XP_PER_LEVEL = {lvl: lvl * 100 for lvl in range(1, 11)}

# Backstory chapter unlock levels
_BACKSTORY_LEVELS = [2, 4, 6, 8, 10]

# Perk definitions per unlock level
_PERK_DEFINITIONS: Dict[int, Dict[str, str]] = {
    3: {"type": "resource_discount", "description": "10% discount on resources from linked module"},
    5: {"type": "unique_mission", "description": "Unique daily mission from this NPC"},
    7: {"type": "crafting_recipe", "description": "Special crafting recipe unlocked"},
    10: {"type": "cosmetic_title", "description": "Cosmetic station title and NPC portrait upgrade"},
}

# Daily interaction constants
BASE_INTERACTION_XP = 20
STREAK_BONUS_XP = 5
MAX_STREAK_BONUS = 25
MAX_GIFT_RESOURCES = 100
GIFT_XP_PER_10_RESOURCES = 1


# ────────────────────────────────────────────────────────────────
# Backstory Chapters — 5 per NPC, rich narrative content
# ────────────────────────────────────────────────────────────────

_NPC_BACKSTORIES: Dict[str, List[dict]] = {
    "cmdr_reyes": [
        {"chapter": 1, "level": 2, "title": "The Cartographer's Oath",
         "text": "Before command found Reyes, Reyes found the edges of the map. Twenty years charting unregistered asteroid fields taught one truth: the void doesn't forgive carelessness, but it rewards patience. The scars on their hands tell the story — each one a near-miss that became a data point."},
        {"chapter": 2, "level": 4, "title": "The Last Rotation",
         "text": "The previous commander left without ceremony — just a sealed envelope and an empty chair. Reyes opened it alone. Inside: coordinates to a gravitational anomaly and a single line: 'Don't let them bury this.' The anomaly is still out there, and Reyes checks its drift every morning before dawn cycle."},
        {"chapter": 3, "level": 6, "title": "Signal in the Static",
         "text": "During a routine deep-space survey, Reyes picked up a pattern in background radiation that shouldn't exist. Not random noise, not known pulsar signatures — something structured. The official report classified it as equipment error. Reyes kept the raw recordings in a locked drawer."},
        {"chapter": 4, "level": 8, "title": "The Weight of Command",
         "text": "There was a moment, three months into command, when Reyes almost resigned. A supply miscalculation left the crew on half rations for two weeks. Nobody blamed them — but Reyes blamed themselves. They solved it by trading star charts to a passing freighter, but the lesson stuck: every number on a manifest is someone's meal."},
        {"chapter": 5, "level": 10, "title": "Horizon Protocol",
         "text": "Reyes has been quietly developing Horizon Protocol — a contingency plan for first contact scenarios. Not the bureaucratic kind filed with central command, but a real one. A human one. It includes a music playlist, a recipe for coffee the way Earth makes it, and a hand-drawn star map showing where we came from. 'If we meet someone out here,' Reyes says, 'I want them to know we tried to be good.'"},
    ],
    "dr_okafor": [
        {"chapter": 1, "level": 2, "title": "The Xenobiologist's Dilemma",
         "text": "Okafor didn't choose medicine — medicine chose Okafor when the xenobiology grant dried up. But the skills transferred: understanding alien cell structures gave an intuition for human healing that medical school couldn't teach. 'Every body is an ecosystem,' Okafor says. 'I just learned to read the strange ones first.'"},
        {"chapter": 2, "level": 4, "title": "Patient Zero-G",
         "text": "The first patient Okafor treated in deep space had a condition textbooks didn't cover: cosmic radiation had caused their cells to photosynthesize. Briefly. Harmlessly. But beautifully — their skin glowed faint green in darkness. Okafor documented everything and published nothing. Some discoveries deserve to stay with their owners."},
        {"chapter": 3, "level": 6, "title": "The Garden Lab",
         "text": "In the quietest corner of the medical bay, Okafor maintains a collection of 47 specimens — not medical samples, but seeds. Seeds from every station they've served on, every planet-side leave, every gift from a grateful patient. 'Medicine heals people,' Okafor says. 'Gardens heal places.'"},
        {"chapter": 4, "level": 8, "title": "Cosmic Immunity",
         "text": "Okafor's unpublished research suggests that long-term deep space crews develop subtle immune system changes — not weaknesses, but adaptations. The body learns to coexist with cosmic radiation rather than fight it. If true, it would rewrite the textbooks on human spaceflight limits. Okafor waits for more data, ever the patient scientist."},
        {"chapter": 5, "level": 10, "title": "The Healer's Archive",
         "text": "Hidden in Okafor's quarters is a journal with entries spanning fifteen years. Not medical records — stories. Every patient's name (changed for privacy), what brought them to the med bay, and what they talked about while healing. 'People tell doctors things they tell no one else,' Okafor says. 'I keep them safe. All of them.'"},
    ],
    "tech_jin": [
        {"chapter": 1, "level": 2, "title": "Self-Taught",
         "text": "Jin never attended an academy. Everything they know came from taking things apart and occasionally getting them back together. The first thing they ever fixed was their family's water recycler at age nine. The second was the school's communication array — which technically counted as unauthorized access, but the principal let it slide when the emergency beacon started working again."},
        {"chapter": 2, "level": 4, "title": "The Ghost in the Machine",
         "text": "Every station Jin has served on developed minor quirks — elevators that played music, airlocks that sighed contentedly after cycling, temperature controls that adjusted to individual preferences without being told. Jin insists these are 'optimization cascades.' The crew calls them blessings."},
        {"chapter": 3, "level": 6, "title": "Trust Protocol",
         "text": "Jin's distrust of authority isn't abstract — it's born from watching a station commander override safety protocols to meet a mining quota. Jin was the one who pulled three engineers out of a decompressing module. The commander received a commendation. Jin received a transfer. 'Machines don't lie,' Jin says. 'People do.'"},
        {"chapter": 4, "level": 8, "title": "The Perfect Circuit",
         "text": "In Jin's workshop, under a glass case, sits a single circuit board that does nothing. It's not connected to anything. But its design is flawless — every trace at the optimal width, every component placed for maximum efficiency. Jin made it during a particularly dark week as proof that perfection is possible, even if everything else falls apart."},
        {"chapter": 5, "level": 10, "title": "Jin's Legacy Code",
         "text": "Jin has been embedding tiny improvements in the station's firmware for years — nothing dramatic, just elegant solutions to problems nobody else noticed. After Jin eventually moves on, the station will run 3.7% more efficiently, and nobody will know why. That's exactly how Jin wants it. 'Good engineering is invisible,' they say. 'If you notice it, I failed.'"},
    ],
    "lt_vasquez": [
        {"chapter": 1, "level": 2, "title": "The Lost Crewmate",
         "text": "Lieutenant Vasquez doesn't talk about Station Kepler-7. But the crew knows the broad strokes: a hull breach during a micrometeorite storm, a sealed corridor, a choice made in twelve seconds that saved eleven and lost one. The name 'Torres' is engraved inside Vasquez's watch. They check it every time they lock a bulkhead."},
        {"chapter": 2, "level": 4, "title": "By the Book",
         "text": "Vasquez's adherence to protocol isn't rigidity — it's love. Every regulation was written because someone, somewhere, was hurt. The safety manual isn't bureaucracy to Vasquez; it's a memorial. 'Each rule has a name behind it,' Vasquez says. 'I just make sure we don't add more names.'"},
        {"chapter": 3, "level": 6, "title": "Night Watch Meditations",
         "text": "During the quiet hours of night watch, Vasquez practices an old martial art adapted for zero-G — slow, flowing movements that look like tai chi performed by a ghost. It started as combat training and became something else entirely. 'In space, violence is always the last resort,' Vasquez says. 'Because there's nowhere to retreat.'"},
        {"chapter": 4, "level": 8, "title": "The Vulnerability Report",
         "text": "Vasquez filed a classified vulnerability report six months ago about a systemic flaw in station emergency lighting. Central command marked it 'low priority.' Vasquez quietly fixed it anyway, using personal leave time and spare parts from Jin's workshop. If the lights ever fail during an emergency, the crew will find their way to the escape pods. They just won't know who made that possible."},
        {"chapter": 5, "level": 10, "title": "Vasquez's Promise",
         "text": "In the security locker that only Vasquez can open, there's a handwritten list of every crew member who has ever served under their watch. Beside each name, a single word: 'Safe.' It's updated daily. Vasquez made a promise the day Torres was lost — no more names without that word beside them. So far, the promise holds."},
    ],
    "chef_amari": [
        {"chapter": 1, "level": 2, "title": "The Spice Trader",
         "text": "Amari's 'underground spice trade' is the worst-kept secret on the station. Every passing freighter captain knows that NEXUS Station is the place to trade saffron for stories, cumin for coordinates, and real vanilla for almost anything. 'Morale is a resource,' Amari insists. 'And I'm the only one mining it properly.'"},
        {"chapter": 2, "level": 4, "title": "Grandmother's Recipe",
         "text": "There's one dish Amari makes only on crew birthdays — a complex layered pastry that takes six hours and ingredients from three different supply runs. The recipe is handwritten on a yellowed card in a language the translation systems don't recognize. 'My grandmother's writing,' Amari says. 'The recipe is older than spaceflight.'"},
        {"chapter": 3, "level": 6, "title": "The Empty Chair",
         "text": "In the mess hall, there's always one extra place set at the main table. Amari maintains it without explanation. New crew members learn not to sit there. Old crew members understand: it's for whoever needs it next — the unexpected visitor, the crew member eating alone, the stranger who needs to feel welcome. 'A table with an empty chair,' Amari says, 'is a table that still has room for hope.'"},
        {"chapter": 4, "level": 8, "title": "Harvest Moon Protocol",
         "text": "Once a year, Amari coordinates a feast using only ingredients grown in the station greenhouse. No supply-run supplements, no preserved rations. It takes months of planning and coordination with the botany team. The meal is never fancy, but it's always honest — a reminder that even in deep space, the crew can sustain itself. Amari calls it 'remembering what ground tastes like.'"},
        {"chapter": 5, "level": 10, "title": "Amari's Table",
         "text": "Amari is writing a cookbook. Not recipes — those are the easy part. It's a cookbook of moments: what the crew talked about over each meal, what was happening on the station, what was visible through the mess hall viewport. 'Food is time travel,' Amari says. 'Fifty years from now, someone will make this stew and taste Tuesday on NEXUS Station.'"},
    ],
    "archivist_lune": [
        {"chapter": 1, "level": 2, "title": "The Keeper of Names",
         "text": "Lune arrived at NEXUS Station with seventeen sealed data cores and no personal belongings. The cores contained station logs going back to the original construction — voices of people long transferred, retired, or lost. 'A station without memory,' Lune whispered upon arrival, 'is just metal pretending to matter.'"},
        {"chapter": 2, "level": 4, "title": "Riddles and Reasons",
         "text": "Lune's habit of speaking in riddles isn't affectation — it's training. The Archivist tradition teaches that direct statements create certainty, and certainty stops inquiry. A riddle keeps the mind searching. 'The answer you find yourself,' Lune says, 'is the answer you'll remember.'"},
        {"chapter": 3, "level": 6, "title": "The Listening Room",
         "text": "Deep in the station archives, Lune maintains a room where old transmissions play on loop — distress calls that were answered, first contact attempts that went nowhere, a lullaby someone broadcast into the void on the anniversary of Earth's last sunrise visible from Station Prime. 'Not all records are data,' Lune says. 'Some are prayers.'"},
        {"chapter": 4, "level": 8, "title": "The Pattern",
         "text": "Lune has been mapping something across the station logs — not events, but emotions. A graph of crew morale across decades, correlated with cosmic events, station configurations, and command decisions. The pattern suggests that stations near certain stellar formations produce more creative output. Lune won't publish until the data is irrefutable, but quietly, they've been recommending 'optimal contemplation positions' to the crew."},
        {"chapter": 5, "level": 10, "title": "Lune's Gift",
         "text": "When a crew member leaves NEXUS Station, Lune gives them a small, hand-bound book containing every log entry that mentions them by name. Not surveillance — celebration. Their contributions, their jokes overhead in corridors, the systems they improved, the friendships they built. 'You think you pass through a station,' Lune says. 'But a station passes through you, too. I just make sure it's written down.'"},
    ],
}

# NPC-specific dialogue for daily interactions
_INTERACTION_DIALOGUES: Dict[str, List[str]] = {
    "cmdr_reyes": [
        "Reyes nods as you enter the bridge. 'Good timing. I was reviewing the morning reports — care to take a look?'",
        "Reyes passes you a mug of synthetic coffee. 'It's not great, but it's warm. That counts for something out here.'",
        "Reyes is studying a star chart when you arrive. 'Come see this. There's a pattern I can't quite name.'",
        "Reyes straightens from the command console. 'Another cycle. Another chance to do this right.'",
    ],
    "dr_okafor": [
        "Okafor looks up from a microscope with bright eyes. 'You won't believe what I found in this morning's samples.'",
        "Okafor is tending a small plant on the med bay windowsill. 'Sometimes the best medicine is just being present.'",
        "Okafor greets you with a warm smile. 'No appointments today? Good. Let's just talk.'",
        "Okafor offers you a cup of herbal tea. 'My own blend. The greenhouse is surprisingly cooperative.'",
    ],
    "tech_jin": [
        "Jin doesn't look up from the circuit board. 'Hand me that soldering iron. No, the other one. ...Thanks.'",
        "Jin's workspace hums with half-finished projects. 'Don't touch anything. Actually, hand me that wrench.'",
        "Jin pauses mid-repair. 'You know what I like about machines? They don't pretend to be something they're not.'",
        "Jin offers a rare grin. 'I optimized the life support by 0.3% last night. Nobody noticed. Perfect.'",
    ],
    "lt_vasquez": [
        "Vasquez is checking the security feeds with practiced efficiency. 'All sectors quiet. For now.'",
        "Vasquez nods formally. 'Good to see you making the rounds. A visible commander is a safe commander.'",
        "Vasquez is running through zero-G martial arts forms in the corridor. 'Care to join? It clears the mind.'",
        "Vasquez looks up from a safety manual. 'Page 847. They finally updated the pressure seal protocols.'",
    ],
    "chef_amari": [
        "Amari is humming while stirring something that smells impossibly good. 'Taste this. Tell me what's missing.'",
        "Amari slides a plate toward you. 'Leftovers from last night. But leftovers made with love are just previews.'",
        "Amari is negotiating with a supply manifest. 'If I can get real cinnamon, I can change the whole station's mood.'",
        "Amari beams when you enter. 'My favorite critic! Sit, sit. I'm trying something new.'",
    ],
    "archivist_lune": [
        "Lune is surrounded by data cores, each one glowing faintly. 'The station remembers more than we think.'",
        "Lune speaks without turning. 'You walk like someone carrying a question. Ask it.'",
        "Lune offers a thin smile. 'I found your name in a log from three cycles ago. You made someone laugh.'",
        "Lune is cataloging transmissions. 'Listen to this one. Someone, somewhere, sent a song into the void.'",
    ],
}

# Gift response dialogues
_GIFT_DIALOGUES: Dict[str, List[str]] = {
    "cmdr_reyes": [
        "Reyes accepts the gift with a firm nod. 'This will be put to good use. You have my word.'",
        "Reyes looks genuinely surprised. 'Generosity is its own kind of leadership. Thank you.'",
    ],
    "dr_okafor": [
        "Okafor's eyes light up. 'Resources for the med bay? You're speaking my language.'",
        "Okafor carefully catalogs the gift. 'Every bit helps. Thank you for thinking of us.'",
    ],
    "tech_jin": [
        "Jin inspects the offering. '...This is actually useful. Don't expect me to say that often.'",
        "Jin pockets the resources without ceremony. 'I know exactly what to do with this. Thanks.'",
    ],
    "lt_vasquez": [
        "Vasquez accepts with military precision. 'Noted and appreciated. These resources mean safer operations.'",
        "Vasquez allows a small smile. 'Security improvements incoming. Thank you.'",
    ],
    "chef_amari": [
        "Amari clasps their hands together. 'Oh wonderful! I can finally make that dish I've been planning!'",
        "Amari beams. 'The crew is going to eat well tonight. You're an angel.'",
    ],
    "archivist_lune": [
        "Lune tilts their head. 'A gift freely given carries more weight than any requisition form.'",
        "Lune carefully places the offering among the archive supplies. 'Generosity becomes part of the record.'",
    ],
}


# ────────────────────────────────────────────────────────────────
# Data Model
# ────────────────────────────────────────────────────────────────

@dataclass
class NpcRelationship:
    """Relationship state between a player and a station NPC."""
    npc_id: str
    level: int = 1
    xp: int = 0
    xp_to_next: int = 100       # level 1 → 2 requires 100 XP
    last_interaction_date: str = ""
    interaction_streak: int = 0
    backstory_chapters_unlocked: List[int] = field(default_factory=list)
    perks_unlocked: List[str] = field(default_factory=list)
    total_interactions: int = 0


# ────────────────────────────────────────────────────────────────
# Persistence
# ────────────────────────────────────────────────────────────────

def _load_npc_data(player_id: str) -> Dict[str, dict]:
    """Load NPC relationship data for a player."""
    safe_id = _sanitize_player_id(player_id)
    path = NPC_CREW_DIR / f"{safe_id}.json"
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {}


def _save_npc_data(player_id: str, data: Dict[str, dict]) -> None:
    """Save NPC relationship data for a player."""
    _ensure_dir(NPC_CREW_DIR)
    safe_id = _sanitize_player_id(player_id)
    path = NPC_CREW_DIR / f"{safe_id}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def _get_relationship(player_data: dict, npc_id: str) -> NpcRelationship:
    """Get or create a relationship record for an NPC."""
    if npc_id in player_data:
        d = player_data[npc_id]
        return NpcRelationship(
            npc_id=npc_id,
            level=d.get("level", 1),
            xp=d.get("xp", 0),
            xp_to_next=d.get("xp_to_next", 100),
            last_interaction_date=d.get("last_interaction_date", ""),
            interaction_streak=d.get("interaction_streak", 0),
            backstory_chapters_unlocked=d.get("backstory_chapters_unlocked", []),
            perks_unlocked=d.get("perks_unlocked", []),
            total_interactions=d.get("total_interactions", 0),
        )
    return NpcRelationship(npc_id=npc_id)


def _relationship_to_dict(rel: NpcRelationship) -> dict:
    """Serialize a relationship to dict."""
    return {
        "npc_id": rel.npc_id,
        "level": rel.level,
        "xp": rel.xp,
        "xp_to_next": rel.xp_to_next,
        "last_interaction_date": rel.last_interaction_date,
        "interaction_streak": rel.interaction_streak,
        "backstory_chapters_unlocked": rel.backstory_chapters_unlocked,
        "perks_unlocked": rel.perks_unlocked,
        "total_interactions": rel.total_interactions,
    }


# ────────────────────────────────────────────────────────────────
# Level Progression
# ────────────────────────────────────────────────────────────────

def _check_level_up(rel: NpcRelationship) -> List[dict]:
    """Process XP and check for level-ups. Returns list of events."""
    events = []
    while rel.level < 10 and rel.xp >= rel.xp_to_next:
        rel.xp -= rel.xp_to_next
        rel.level += 1
        rel.xp_to_next = _XP_PER_LEVEL.get(rel.level, 1000)
        events.append({"type": "level_up", "new_level": rel.level})

        # Check backstory unlock
        if rel.level in _BACKSTORY_LEVELS:
            chapter_num = _BACKSTORY_LEVELS.index(rel.level) + 1
            if chapter_num not in rel.backstory_chapters_unlocked:
                rel.backstory_chapters_unlocked.append(chapter_num)
                events.append({"type": "backstory_unlock", "chapter": chapter_num})

        # Check perk unlock
        if rel.level in _PERK_DEFINITIONS:
            perk = _PERK_DEFINITIONS[rel.level]
            perk_key = f"level_{rel.level}_{perk['type']}"
            if perk_key not in rel.perks_unlocked:
                rel.perks_unlocked.append(perk_key)
                events.append({"type": "perk_unlock", "perk": perk_key, "description": perk["description"]})

    # Cap XP at max level
    if rel.level >= 10:
        rel.xp = 0
        rel.xp_to_next = 0

    return events


# ────────────────────────────────────────────────────────────────
# API Functions
# ────────────────────────────────────────────────────────────────

def get_npc_list(player_id: str) -> dict:
    """Get all NPCs with their relationship status for a player.

    Returns:
        Dict with "npcs" list of NPC info dicts.
    """
    player_data = _load_npc_data(player_id)
    today = date.today().isoformat()
    npcs = []

    for npc_id, npc_info in _NPC_DATABASE.items():
        rel = _get_relationship(player_data, npc_id)
        module_id = NPC_MODULE_MAP.get(npc_id, "bridge")

        npcs.append({
            "npc_id": npc_id,
            "name": npc_info["name"],
            "role": npc_info["role"],
            "personality": npc_info["personality"],
            "module": module_id,
            "level": rel.level,
            "xp": rel.xp,
            "xp_to_next": rel.xp_to_next,
            "interaction_streak": rel.interaction_streak,
            "total_interactions": rel.total_interactions,
            "can_interact_today": rel.last_interaction_date != today,
            "backstory_chapters_unlocked": rel.backstory_chapters_unlocked,
            "perks_unlocked": rel.perks_unlocked,
        })

    return {"npcs": npcs}


def get_npc_detail(player_id: str, npc_id: str) -> dict:
    """Get detailed info for a single NPC including backstory chapters.

    Returns:
        Dict with NPC info, relationship data, and unlocked backstory.
    """
    if npc_id not in _NPC_DATABASE:
        return {"error": f"Unknown NPC: {npc_id}"}

    npc_info = _NPC_DATABASE[npc_id]
    player_data = _load_npc_data(player_id)
    rel = _get_relationship(player_data, npc_id)
    today = date.today().isoformat()
    module_id = NPC_MODULE_MAP.get(npc_id, "bridge")

    # Build backstory list (only unlocked chapters)
    backstory = []
    npc_chapters = _NPC_BACKSTORIES.get(npc_id, [])
    for ch in npc_chapters:
        if ch["chapter"] in rel.backstory_chapters_unlocked:
            backstory.append(ch)
        else:
            backstory.append({
                "chapter": ch["chapter"],
                "level": ch["level"],
                "title": "???",
                "text": f"Reach level {ch['level']} to unlock this chapter.",
                "locked": True,
            })

    # Build perks list
    perks = []
    for lvl, perk_def in _PERK_DEFINITIONS.items():
        perk_key = f"level_{lvl}_{perk_def['type']}"
        perks.append({
            "level_required": lvl,
            "type": perk_def["type"],
            "description": perk_def["description"],
            "unlocked": perk_key in rel.perks_unlocked,
        })

    return {
        "npc_id": npc_id,
        "name": npc_info["name"],
        "role": npc_info["role"],
        "backstory_intro": npc_info["backstory"],
        "personality": npc_info["personality"],
        "default_mood": npc_info["default_mood"],
        "module": module_id,
        "relationship": _relationship_to_dict(rel),
        "can_interact_today": rel.last_interaction_date != today,
        "backstory_chapters": backstory,
        "perks": perks,
    }


def interact_with_npc(player_id: str, npc_id: str, cosmic_status: str = "NEUTRAL") -> dict:
    """Perform a daily interaction with an NPC.

    Args:
        player_id: The player identifier.
        npc_id: The NPC to interact with.
        cosmic_status: Current cosmic mood (POWER/TROUBLE/PRESSURE/NEUTRAL).

    Returns:
        Dict with interaction result, XP gained, events, and dialogue.
    """
    if npc_id not in _NPC_DATABASE:
        return {"error": f"Unknown NPC: {npc_id}"}

    player_data = _load_npc_data(player_id)
    rel = _get_relationship(player_data, npc_id)
    today = date.today().isoformat()

    # Check daily cooldown
    if rel.last_interaction_date == today:
        return {
            "error": "Already interacted with this NPC today",
            "next_interaction": "tomorrow",
        }

    # Calculate streak
    yesterday = date.today().toordinal() - 1
    if rel.last_interaction_date:
        try:
            last_date = date.fromisoformat(rel.last_interaction_date)
            if last_date.toordinal() == yesterday:
                rel.interaction_streak += 1
            elif last_date.toordinal() < yesterday:
                rel.interaction_streak = 1
        except ValueError:
            rel.interaction_streak = 1
    else:
        rel.interaction_streak = 1

    # Calculate XP
    streak_bonus = min(rel.interaction_streak * STREAK_BONUS_XP, MAX_STREAK_BONUS)
    xp_earned = BASE_INTERACTION_XP + streak_bonus

    # Cosmic mood modifier
    mood_shifts = _COSMIC_MOOD_SHIFTS.get(cosmic_status, _COSMIC_MOOD_SHIFTS["NEUTRAL"])
    npc_info = _NPC_DATABASE[npc_id]
    current_mood = mood_shifts.get(npc_info["default_mood"], npc_info["default_mood"])

    # Mood XP bonus: friendly +5, neutral 0, guarded -3, hostile -5
    mood_xp = {"friendly": 5, "neutral": 0, "guarded": -3, "hostile": -5}.get(current_mood, 0)
    xp_earned = max(1, xp_earned + mood_xp)

    # Apply XP
    rel.xp += xp_earned
    rel.last_interaction_date = today
    rel.total_interactions += 1

    # Check level ups
    events = _check_level_up(rel)

    # Pick dialogue
    dialogues = _INTERACTION_DIALOGUES.get(npc_id, ["The crew member nods in greeting."])
    dialogue = random.choice(dialogues)

    # Save
    player_data[npc_id] = _relationship_to_dict(rel)
    _save_npc_data(player_id, player_data)

    return {
        "success": True,
        "npc_id": npc_id,
        "npc_name": npc_info["name"],
        "dialogue": dialogue,
        "xp_earned": xp_earned,
        "streak_bonus": streak_bonus,
        "mood_bonus": mood_xp,
        "cosmic_mood": current_mood,
        "interaction_streak": rel.interaction_streak,
        "level": rel.level,
        "xp": rel.xp,
        "xp_to_next": rel.xp_to_next,
        "events": events,
    }


def gift_npc(player_id: str, npc_id: str, resource: str, amount: int) -> dict:
    """Give a resource gift to an NPC for bonus XP.

    Args:
        player_id: The player identifier.
        npc_id: The NPC to gift.
        resource: Resource type to gift.
        amount: Amount of resource (max 100, must be positive).

    Returns:
        Dict with gift result, XP earned, and NPC response.
    """
    if npc_id not in _NPC_DATABASE:
        return {"error": f"Unknown NPC: {npc_id}"}

    # Validate amount
    if amount <= 0:
        return {"error": "Gift amount must be positive"}
    amount = min(amount, MAX_GIFT_RESOURCES)

    # Check player has resources
    station = get_station(player_id)
    if station is None:
        return {"error": "No station found. Create a station first."}

    current_amount = station.resources.get(resource, 0)
    if current_amount < amount:
        return {"error": f"Insufficient {resource}. Have {current_amount}, need {amount}."}

    # Deduct resources
    station.resources[resource] = current_amount - amount
    save_station(station)

    # Calculate XP from gift
    xp_earned = max(1, amount // 10 * GIFT_XP_PER_10_RESOURCES)

    # Apply XP
    player_data = _load_npc_data(player_id)
    rel = _get_relationship(player_data, npc_id)
    rel.xp += xp_earned
    events = _check_level_up(rel)

    # Save
    player_data[npc_id] = _relationship_to_dict(rel)
    _save_npc_data(player_id, player_data)

    # Pick gift dialogue
    npc_info = _NPC_DATABASE[npc_id]
    dialogues = _GIFT_DIALOGUES.get(npc_id, ["The crew member accepts your gift graciously."])
    dialogue = random.choice(dialogues)

    return {
        "success": True,
        "npc_id": npc_id,
        "npc_name": npc_info["name"],
        "resource": resource,
        "amount": amount,
        "xp_earned": xp_earned,
        "dialogue": dialogue,
        "level": rel.level,
        "xp": rel.xp,
        "xp_to_next": rel.xp_to_next,
        "events": events,
    }


def get_active_perks(player_id: str) -> dict:
    """Get all active perks from NPC relationships.

    Returns:
        Dict with list of active perks and their effects.
    """
    player_data = _load_npc_data(player_id)
    active_perks = []

    for npc_id in _NPC_DATABASE:
        rel = _get_relationship(player_data, npc_id)
        npc_info = _NPC_DATABASE[npc_id]
        module_id = NPC_MODULE_MAP.get(npc_id, "bridge")

        for perk_key in rel.perks_unlocked:
            # Parse level from perk key
            parts = perk_key.split("_")
            if len(parts) >= 3:
                lvl = int(parts[1])
                perk_def = _PERK_DEFINITIONS.get(lvl, {})
                active_perks.append({
                    "npc_id": npc_id,
                    "npc_name": npc_info["name"],
                    "module": module_id,
                    "perk_key": perk_key,
                    "level_required": lvl,
                    "type": perk_def.get("type", "unknown"),
                    "description": perk_def.get("description", ""),
                })

    return {"active_perks": active_perks, "total_perks": len(active_perks)}

"""
NEXUS STATION - Stellar Outreach: Phase 2 Mini-Games (TASK-008)

Four new mini-games expanding the station gameplay:
    1. Crew Diplomacy   — Card-based NPC dialogue (Greenhouse/Commons)
    2. Signal Decode    — Cryptogram puzzles (Shrine)
    3. Resource Harvest  — Merge-style tile combining (Workshop/Quarters)
    4. Sky Scanner       — Celestial object identification (Observatory)

Scoring pattern (matches Phase 1):
    base_score * difficulty_mult * speed_bonus * cosmic_buff_mult

References:
    - GDD S5.3: Mini-game definitions (Phase 2)
    - TASK-004: Phase 1 mini-games pattern

Security Note (Article II / Kai Chen review):
    NPC relationships and lore progress are persisted per player_id
    using sanitized file paths. No PII beyond player_id is stored.

UX Note (Marina Okonkwo review):
    All games designed for mobile portrait layout. Card-based UI
    patterns for diplomacy; single-tap interactions for harvest.
"""

from __future__ import annotations

import hashlib
import json
import random
import string
import uuid
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# ────────────────────────────────────────────────────────────────
# Persistence Configuration
# ────────────────────────────────────────────────────────────────

NPC_RELATIONSHIPS_DIR = Path.home() / ".nexus_station" / "npc_relationships"
LORE_PROGRESS_DIR = Path.home() / ".nexus_station" / "lore_progress"


def _sanitize_player_id(player_id: str) -> str:
    """Sanitize a player ID for safe filesystem use."""
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in player_id)


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


# ────────────────────────────────────────────────────────────────
# 1. Crew Diplomacy — NPC Dialogue Card Game
# ────────────────────────────────────────────────────────────────

@dataclass
class NpcState:
    """State of a single NPC for diplomacy interactions."""
    npc_id: str
    name: str
    role: str
    mood: str          # "friendly", "neutral", "guarded", "hostile"
    relationship: int  # 0-100
    backstory: str


@dataclass
class DiplomacyScenario:
    """A Crew Diplomacy encounter."""
    scenario_id: str
    npc: NpcState
    situation: str
    choices: List[dict]  # [{id, text, tone, effect}]
    difficulty: int
    time_limit_seconds: int
    cosmic_mood: str     # current cosmic influence on NPC


@dataclass
class DiplomacyResult:
    """Scoring result for a Crew Diplomacy encounter."""
    scenario_id: str
    npc_id: str
    npc_name: str
    choice_id: str
    relationship_change: int
    new_relationship: int
    new_mood: str
    score: int
    xp_earned: int
    dialogue_response: str


# NPC definitions — 6 station NPCs
_NPC_DATABASE: Dict[str, dict] = {
    "cmdr_reyes": {
        "name": "Commander Reyes",
        "role": "Station Operations",
        "backstory": "Former deep-space cartographer who took command after the last rotation. Pragmatic but fair.",
        "default_mood": "neutral",
        "personality": "pragmatic",
    },
    "dr_okafor": {
        "name": "Dr. Okafor",
        "role": "Chief Medical Officer",
        "backstory": "Xenobiologist reassigned to medical duty. Fascinated by how cosmic radiation affects crew health.",
        "default_mood": "friendly",
        "personality": "curious",
    },
    "tech_jin": {
        "name": "Tech Specialist Jin",
        "role": "Systems Engineer",
        "backstory": "Self-taught engineer who can fix anything. Distrusts authority but respects competence.",
        "default_mood": "guarded",
        "personality": "skeptical",
    },
    "lt_vasquez": {
        "name": "Lieutenant Vasquez",
        "role": "Security",
        "backstory": "By-the-book security officer. Lost a crew member on her last posting and takes safety personally.",
        "default_mood": "neutral",
        "personality": "protective",
    },
    "chef_amari": {
        "name": "Chef Amari",
        "role": "Nutrition & Morale",
        "backstory": "Believes food is the foundation of crew cohesion. Runs an underground spice trade with passing ships.",
        "default_mood": "friendly",
        "personality": "warm",
    },
    "archivist_lune": {
        "name": "Archivist Lune",
        "role": "Records & History",
        "backstory": "Keeper of station logs going back generations. Speaks in riddles but remembers everything.",
        "default_mood": "neutral",
        "personality": "cryptic",
    },
}

# Situation templates per mood
_SITUATIONS: Dict[str, List[dict]] = {
    "friendly": [
        {"text": "{name} approaches with a warm smile. 'I've been thinking about something and I'd value your input.'",
         "choices": [
             {"id": "a", "text": "I'd be happy to help. What's on your mind?", "tone": "supportive", "effect": 8},
             {"id": "b", "text": "Sure, but make it quick — busy day.", "tone": "dismissive", "effect": -3},
             {"id": "c", "text": "Of course. Let's sit down and discuss it properly.", "tone": "thoughtful", "effect": 12},
         ]},
        {"text": "{name} waves you over during a quiet moment. 'I found something interesting in the star charts.'",
         "choices": [
             {"id": "a", "text": "Show me! I love a good discovery.", "tone": "enthusiastic", "effect": 10},
             {"id": "b", "text": "Log it and I'll review it later.", "tone": "bureaucratic", "effect": -5},
             {"id": "c", "text": "Interesting. What do you make of it?", "tone": "curious", "effect": 7},
         ]},
    ],
    "neutral": [
        {"text": "{name} stops you in the corridor. 'We need to discuss the resource allocation for next cycle.'",
         "choices": [
             {"id": "a", "text": "Let's review the numbers together.", "tone": "collaborative", "effect": 8},
             {"id": "b", "text": "I'll handle it. Trust my judgment.", "tone": "authoritative", "effect": -2},
             {"id": "c", "text": "What's your recommendation?", "tone": "respectful", "effect": 10},
         ]},
        {"text": "{name} sends a formal request for a meeting. The subject line reads: 'Operational Concerns.'",
         "choices": [
             {"id": "a", "text": "Schedule it immediately — concerns deserve attention.", "tone": "responsive", "effect": 9},
             {"id": "b", "text": "Add it to the queue. I'll get to it.", "tone": "indifferent", "effect": -4},
             {"id": "c", "text": "Reply asking for a brief summary first.", "tone": "efficient", "effect": 3},
         ]},
    ],
    "guarded": [
        {"text": "{name} keeps their distance but catches your eye. Something's clearly on their mind.",
         "choices": [
             {"id": "a", "text": "Approach gently. 'Everything alright?'", "tone": "caring", "effect": 10},
             {"id": "b", "text": "Give them space. They'll come to you when ready.", "tone": "patient", "effect": 5},
             {"id": "c", "text": "Direct approach. 'We need to talk.'", "tone": "confrontational", "effect": -6},
         ]},
        {"text": "{name} submits a terse status report. Between the lines, you sense frustration.",
         "choices": [
             {"id": "a", "text": "Acknowledge the report and ask how they're doing personally.", "tone": "empathetic", "effect": 12},
             {"id": "b", "text": "Send back corrections on formatting.", "tone": "pedantic", "effect": -8},
             {"id": "c", "text": "Reply: 'Good work. Let me know if you need anything.'", "tone": "supportive", "effect": 7},
         ]},
    ],
    "hostile": [
        {"text": "{name} confronts you openly. 'This station's priorities are wrong and everyone knows it.'",
         "choices": [
             {"id": "a", "text": "Listen fully before responding. 'Tell me more.'", "tone": "open", "effect": 15},
             {"id": "b", "text": "Match their energy. 'Then propose a solution.'", "tone": "challenging", "effect": 3},
             {"id": "c", "text": "Shut it down. 'That's not how we operate here.'", "tone": "authoritarian", "effect": -10},
         ]},
        {"text": "{name} has been avoiding you for days. Other crew members are starting to notice.",
         "choices": [
             {"id": "a", "text": "Arrange a private, off-the-record conversation.", "tone": "diplomatic", "effect": 12},
             {"id": "b", "text": "Address it publicly at the next briefing.", "tone": "public", "effect": -8},
             {"id": "c", "text": "Send a handwritten note: 'I'd like to understand.'", "tone": "personal", "effect": 10},
         ]},
    ],
}

# Cosmic mood effects on NPC mood
_COSMIC_MOOD_SHIFTS: Dict[str, Dict[str, str]] = {
    "POWER": {"hostile": "guarded", "guarded": "neutral", "neutral": "friendly", "friendly": "friendly"},
    "TROUBLE": {"friendly": "neutral", "neutral": "guarded", "guarded": "hostile", "hostile": "hostile"},
    "PRESSURE": {"friendly": "neutral", "neutral": "neutral", "guarded": "guarded", "hostile": "guarded"},
    "NEUTRAL": {"friendly": "friendly", "neutral": "neutral", "guarded": "guarded", "hostile": "hostile"},
}

# Dialogue responses by tone outcome
_DIALOGUE_RESPONSES: Dict[str, List[str]] = {
    "positive": [
        "{name} nods slowly. 'I appreciate that. Really.'",
        "{name}'s expression softens. 'Maybe I misjudged things.'",
        "{name} smiles. 'That's exactly what I needed to hear.'",
        "A weight seems to lift from {name}'s shoulders. 'Thank you.'",
    ],
    "negative": [
        "{name} turns away without a word.",
        "{name}'s jaw tightens. 'Noted.' The word carries frost.",
        "{name} shakes their head. 'I expected better.'",
        "The silence that follows says everything.",
    ],
    "neutral": [
        "{name} considers your words carefully. 'I'll think about that.'",
        "{name} gives a noncommittal nod. 'We'll see.'",
        "{name} files the conversation away. Business as usual.",
    ],
}

# Active scenarios cache
_active_diplomacy: Dict[str, DiplomacyScenario] = {}


def _load_relationships(player_id: str) -> Dict[str, dict]:
    """Load NPC relationships for a player."""
    safe_id = _sanitize_player_id(player_id)
    path = NPC_RELATIONSHIPS_DIR / f"{safe_id}.json"
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {}


def _save_relationships(player_id: str, data: Dict[str, dict]) -> None:
    """Save NPC relationships for a player."""
    _ensure_dir(NPC_RELATIONSHIPS_DIR)
    safe_id = _sanitize_player_id(player_id)
    path = NPC_RELATIONSHIPS_DIR / f"{safe_id}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def _get_npc_state(player_id: str, npc_id: str, cosmic_status: str = "NEUTRAL") -> NpcState:
    """Get current NPC state for a player, applying cosmic mood shifts."""
    npc_def = _NPC_DATABASE[npc_id]
    rels = _load_relationships(player_id)
    rel_data = rels.get(npc_id, {"relationship": 50, "mood": npc_def["default_mood"]})

    base_mood = rel_data.get("mood", npc_def["default_mood"])
    shifted_mood = _COSMIC_MOOD_SHIFTS.get(cosmic_status, {}).get(base_mood, base_mood)

    return NpcState(
        npc_id=npc_id,
        name=npc_def["name"],
        role=npc_def["role"],
        mood=shifted_mood,
        relationship=rel_data.get("relationship", 50),
        backstory=npc_def["backstory"],
    )


def generate_diplomacy_scenario(
    player_id: str,
    npc_id: str = None,
    cosmic_status: str = "NEUTRAL",
    difficulty: int = None,
) -> DiplomacyScenario:
    """Generate a Crew Diplomacy encounter.

    Args:
        player_id: The player's ID for relationship tracking.
        npc_id: Specific NPC, or None for random.
        cosmic_status: Current cosmic state affecting NPC mood.
        difficulty: 1-5, or None for auto-based on relationship.

    Returns:
        A DiplomacyScenario ready for frontend rendering.
    """
    if npc_id is None:
        npc_id = random.choice(list(_NPC_DATABASE.keys()))

    if npc_id not in _NPC_DATABASE:
        raise ValueError(f"Unknown NPC: {npc_id}")

    npc = _get_npc_state(player_id, npc_id, cosmic_status)

    if difficulty is None:
        # Higher relationship = harder to gain more
        difficulty = min(5, max(1, 1 + (npc.relationship // 25)))

    situations = _SITUATIONS.get(npc.mood, _SITUATIONS["neutral"])
    situation_data = random.choice(situations)

    scenario_id = f"dp_{uuid.uuid4().hex[:12]}"
    time_limit = max(20, 60 - difficulty * 5)

    scenario = DiplomacyScenario(
        scenario_id=scenario_id,
        npc=npc,
        situation=situation_data["text"].format(name=npc.name),
        choices=[
            {
                "id": c["id"],
                "text": c["text"],
                "tone": c["tone"],
            }
            for c in situation_data["choices"]
        ],
        difficulty=difficulty,
        time_limit_seconds=time_limit,
        cosmic_mood=cosmic_status,
    )

    # Store full choice data for scoring
    _active_diplomacy[scenario_id] = scenario
    # Stash effects in a separate dict keyed by scenario_id
    _diplomacy_effects[scenario_id] = {c["id"]: c["effect"] for c in situation_data["choices"]}

    return scenario


# Effects cache (choice_id -> relationship_change)
_diplomacy_effects: Dict[str, Dict[str, int]] = {}


def score_diplomacy(
    scenario_id: str,
    choice_id: str,
    player_id: str,
    time_taken: float = 0.0,
    cosmic_buff: float = 0.0,
) -> DiplomacyResult:
    """Score a Crew Diplomacy encounter.

    Args:
        scenario_id: The scenario being scored.
        choice_id: The choice the player selected.
        player_id: Player ID for persisting relationship changes.
        time_taken: Seconds the player took.
        cosmic_buff: Buff/debuff percentage from cosmic state.

    Returns:
        A DiplomacyResult with relationship changes and score.
    """
    scenario = _active_diplomacy.get(scenario_id)
    if scenario is None:
        raise ValueError(f"Unknown scenario_id: {scenario_id}")

    effects = _diplomacy_effects.get(scenario_id, {})
    rel_change = effects.get(choice_id, 0)

    # Apply cosmic buff to positive changes
    buff_mult = 1.0 + (cosmic_buff / 100.0)
    if rel_change > 0:
        rel_change = int(rel_change * buff_mult)

    # Update relationship
    rels = _load_relationships(player_id)
    npc_id = scenario.npc.npc_id
    if npc_id not in rels:
        rels[npc_id] = {"relationship": 50, "mood": scenario.npc.mood}

    old_rel = rels[npc_id].get("relationship", 50)
    new_rel = max(0, min(100, old_rel + rel_change))
    rels[npc_id]["relationship"] = new_rel

    # Update mood based on new relationship
    if new_rel >= 75:
        new_mood = "friendly"
    elif new_rel >= 50:
        new_mood = "neutral"
    elif new_rel >= 25:
        new_mood = "guarded"
    else:
        new_mood = "hostile"
    rels[npc_id]["mood"] = new_mood

    _save_relationships(player_id, rels)

    # Score calculation
    difficulty_mult = 1.0 + (scenario.difficulty - 1) * 0.25
    speed_ratio = max(0.0, 1.0 - (time_taken / scenario.time_limit_seconds))
    speed_bonus = 1.0 + (speed_ratio * 0.3)

    if rel_change > 0:
        raw_score = int(rel_change * 10 * difficulty_mult * speed_bonus)
    elif rel_change == 0:
        raw_score = int(20 * difficulty_mult)
    else:
        raw_score = max(5, int(10 + rel_change))

    score = max(5, int(raw_score * buff_mult))
    xp = max(3, int(score * 0.5))

    # Generate dialogue response
    if rel_change > 5:
        pool = _DIALOGUE_RESPONSES["positive"]
    elif rel_change < -3:
        pool = _DIALOGUE_RESPONSES["negative"]
    else:
        pool = _DIALOGUE_RESPONSES["neutral"]
    dialogue = random.choice(pool).format(name=scenario.npc.name)

    # Clean up
    _active_diplomacy.pop(scenario_id, None)
    _diplomacy_effects.pop(scenario_id, None)

    return DiplomacyResult(
        scenario_id=scenario_id,
        npc_id=npc_id,
        npc_name=scenario.npc.name,
        choice_id=choice_id,
        relationship_change=rel_change,
        new_relationship=new_rel,
        new_mood=new_mood,
        score=score,
        xp_earned=xp,
        dialogue_response=dialogue,
    )


# ────────────────────────────────────────────────────────────────
# 2. Signal Decode — Cryptogram Puzzles
# ────────────────────────────────────────────────────────────────

@dataclass
class SignalPuzzle:
    """A Signal Decode cryptogram puzzle."""
    puzzle_id: str
    puzzle_type: str        # "substitution", "frequency", "pattern", "morse"
    encoded_message: str
    hint: str
    answer: str             # correct decoded message
    difficulty: int
    time_limit_seconds: int
    lore_fragment: str      # revealed on solve


@dataclass
class SignalDecodeResult:
    """Scoring result for a Signal Decode puzzle."""
    puzzle_id: str
    puzzle_type: str
    correct: bool
    player_answer: str
    expected_answer: str
    score: int
    xp_earned: int
    lore_fragment: Optional[str]  # only if solved


# Lore fragments — revealed progressively
_LORE_FRAGMENTS: List[dict] = [
    {"id": "lore_001", "text": "The station was not built. It was grown — from a seed of collapsed starlight.", "tier": 1},
    {"id": "lore_002", "text": "Before the first crew arrived, the instruments recorded a single word: REMEMBER.", "tier": 1},
    {"id": "lore_003", "text": "The L2 point was chosen not for stability, but because something already lived there.", "tier": 1},
    {"id": "lore_004", "text": "Every seventh rotation, the station hums at 432 Hz. No one knows why.", "tier": 2},
    {"id": "lore_005", "text": "The original blueprints show an eighth module. It was never built. It was sealed.", "tier": 2},
    {"id": "lore_006", "text": "Commander Zero's last log: 'They are not signals. They are memories. Not ours.'", "tier": 2},
    {"id": "lore_007", "text": "The shrine predates the station by approximately four thousand years.", "tier": 3},
    {"id": "lore_008", "text": "Stardust is not a resource. It is a language we have not yet learned to read.", "tier": 3},
    {"id": "lore_009", "text": "The constellation patterns were placed there. By whom is the wrong question. Ask: for whom.", "tier": 3},
    {"id": "lore_010", "text": "When the last module reaches level 10, the station will remember what it forgot.", "tier": 4},
]

# Morse code mapping
_MORSE_CODE: Dict[str, str] = {
    "A": ".-", "B": "-...", "C": "-.-.", "D": "-..", "E": ".",
    "F": "..-.", "G": "--.", "H": "....", "I": "..", "J": ".---",
    "K": "-.-", "L": ".-..", "M": "--", "N": "-.", "O": "---",
    "P": ".--.", "Q": "--.-", "R": ".-.", "S": "...", "T": "-",
    "U": "..-", "V": "...-", "W": ".--", "X": "-..-", "Y": "-.--",
    "Z": "--..",
    "0": "-----", "1": ".----", "2": "..---", "3": "...--",
    "4": "....-", "5": ".....", "6": "-....", "7": "--...",
    "8": "---..", "9": "----.",
}

# Signal messages for puzzles (short, space-themed)
_SIGNAL_MESSAGES: List[str] = [
    "STAR RISING",
    "DEEP SPACE",
    "ORBIT DECAY",
    "SOLAR WIND",
    "DARK MATTER",
    "RED GIANT",
    "PULSE FOUND",
    "NOVA BRIGHT",
    "WARP SIGNAL",
    "ZERO POINT",
    "COMET TRAIL",
    "LUNAR PHASE",
    "VOID WALKER",
    "LIGHT SPEED",
    "COSMIC DUST",
]

# Active puzzles cache
_active_signals: Dict[str, SignalPuzzle] = {}


def _generate_substitution(message: str, difficulty: int) -> Tuple[str, str]:
    """Generate a substitution cipher."""
    alphabet = list(string.ascii_uppercase)
    shuffled = list(alphabet)

    # For easier difficulties, reveal some mappings
    random.shuffle(shuffled)
    cipher_map = dict(zip(alphabet, shuffled))

    encoded = ""
    for ch in message.upper():
        if ch in cipher_map:
            encoded += cipher_map[ch]
        else:
            encoded += ch

    # Hint: reveal some letter mappings
    reveals = max(1, 6 - difficulty)
    revealed_letters = random.sample(alphabet, min(reveals, len(alphabet)))
    hints = [f"{l}={cipher_map[l]}" for l in revealed_letters]
    hint = f"Known mappings: {', '.join(hints)}"

    return encoded, hint


def _generate_pattern(message: str, difficulty: int) -> Tuple[str, str]:
    """Generate a pattern puzzle (shift cipher with variable shifts)."""
    shifts = list(range(1, 6))
    shift = shifts[min(difficulty - 1, len(shifts) - 1)]

    encoded = ""
    for ch in message.upper():
        if ch.isalpha():
            base = ord('A')
            encoded += chr((ord(ch) - base + shift) % 26 + base)
        else:
            encoded += ch

    hint = f"Each letter has been shifted forward by a constant amount. The first letter '{encoded[0]}' decodes to '{message[0].upper()}'."
    return encoded, hint


def _generate_morse(message: str, difficulty: int) -> Tuple[str, str]:
    """Generate a Morse code puzzle."""
    words = message.upper().split()
    morse_words = []
    for word in words:
        morse_chars = [_MORSE_CODE.get(ch, ch) for ch in word]
        morse_words.append(" ".join(morse_chars))
    encoded = " / ".join(morse_words)

    # Hint depends on difficulty
    if difficulty <= 2:
        hint = "Standard Morse code. Dots (.) and dashes (-). Letters separated by spaces, words by /."
    elif difficulty <= 4:
        hint = "Morse code transmission. / separates words."
    else:
        hint = "Decode this signal transmission."

    return encoded, hint


def _generate_frequency(message: str, difficulty: int) -> Tuple[str, str]:
    """Generate a frequency analysis puzzle (numbers for letters)."""
    # Assign random numbers to letters
    used_letters = set(ch for ch in message.upper() if ch.isalpha())
    number_map = {}
    available_nums = list(range(1, 27))
    random.shuffle(available_nums)
    for i, letter in enumerate(sorted(used_letters)):
        number_map[letter] = available_nums[i]

    encoded = ""
    for ch in message.upper():
        if ch in number_map:
            encoded += f"{number_map[ch]:02d}"
        elif ch == " ":
            encoded += "-"
        else:
            encoded += ch

    # Reveal some numbers
    reveals = max(1, 5 - difficulty)
    revealed = random.sample(list(used_letters), min(reveals, len(used_letters)))
    hints = [f"{number_map[l]:02d}={l}" for l in revealed]
    hint = f"Number-to-letter cipher. Known: {', '.join(hints)}"

    return encoded, hint


def generate_signal_puzzle(
    difficulty: int = None,
    module_level: int = 1,
    player_id: str = "default",
) -> SignalPuzzle:
    """Generate a Signal Decode cryptogram puzzle.

    Args:
        difficulty: 1-5, or None for auto.
        module_level: Player's Shrine module level.
        player_id: For lore progress tracking.

    Returns:
        A SignalPuzzle ready for frontend rendering.
    """
    if difficulty is None:
        difficulty = min(5, max(1, (module_level + 1) // 2))

    message = random.choice(_SIGNAL_MESSAGES)

    puzzle_types = ["substitution", "pattern", "morse", "frequency"]
    # Weight toward simpler types at low difficulty
    if difficulty <= 2:
        puzzle_type = random.choice(["pattern", "morse", "pattern", "morse"])
    elif difficulty <= 4:
        puzzle_type = random.choice(puzzle_types)
    else:
        puzzle_type = random.choice(["substitution", "frequency", "substitution"])

    generators = {
        "substitution": _generate_substitution,
        "pattern": _generate_pattern,
        "morse": _generate_morse,
        "frequency": _generate_frequency,
    }

    encoded, hint = generators[puzzle_type](message, difficulty)

    # Select a lore fragment based on player progress
    lore_progress = _load_lore_progress(player_id)
    unlocked_ids = set(lore_progress.get("unlocked", []))
    available = [l for l in _LORE_FRAGMENTS if l["id"] not in unlocked_ids and l["tier"] <= difficulty]
    if not available:
        available = [l for l in _LORE_FRAGMENTS if l["id"] not in unlocked_ids]
    if not available:
        available = _LORE_FRAGMENTS  # All unlocked, cycle through

    lore = random.choice(available)

    time_limit = max(30, 90 - difficulty * 10)
    puzzle_id = f"sd_{uuid.uuid4().hex[:12]}"

    puzzle = SignalPuzzle(
        puzzle_id=puzzle_id,
        puzzle_type=puzzle_type,
        encoded_message=encoded,
        hint=hint,
        answer=message.upper(),
        difficulty=difficulty,
        time_limit_seconds=time_limit,
        lore_fragment=lore["text"],
    )

    _active_signals[puzzle_id] = puzzle
    return puzzle


def _load_lore_progress(player_id: str) -> dict:
    """Load lore progress for a player."""
    safe_id = _sanitize_player_id(player_id)
    path = LORE_PROGRESS_DIR / f"{safe_id}.json"
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {"unlocked": [], "total_solved": 0}


def _save_lore_progress(player_id: str, data: dict) -> None:
    """Save lore progress for a player."""
    _ensure_dir(LORE_PROGRESS_DIR)
    safe_id = _sanitize_player_id(player_id)
    path = LORE_PROGRESS_DIR / f"{safe_id}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def score_signal_decode(
    puzzle_id: str,
    player_answer: str,
    player_id: str = "default",
    time_taken: float = 0.0,
    cosmic_buff: float = 0.0,
) -> SignalDecodeResult:
    """Score a Signal Decode puzzle attempt.

    Args:
        puzzle_id: The puzzle being scored.
        player_answer: The player's decoded answer.
        player_id: For lore progress tracking.
        time_taken: Seconds the player took.
        cosmic_buff: Buff/debuff percentage from cosmic state.

    Returns:
        A SignalDecodeResult with score and optional lore.
    """
    puzzle = _active_signals.get(puzzle_id)
    if puzzle is None:
        raise ValueError(f"Unknown puzzle_id: {puzzle_id}")

    correct = player_answer.strip().upper() == puzzle.answer

    difficulty_mult = 1.0 + (puzzle.difficulty - 1) * 0.25
    speed_ratio = max(0.0, 1.0 - (time_taken / puzzle.time_limit_seconds))
    speed_bonus = 1.0 + (speed_ratio * 0.5)
    buff_mult = 1.0 + (cosmic_buff / 100.0)

    lore_fragment = None

    if correct:
        raw_score = int(100 * difficulty_mult * speed_bonus)
        score = max(10, int(raw_score * buff_mult))
        lore_fragment = puzzle.lore_fragment

        # Update lore progress
        progress = _load_lore_progress(player_id)
        # Find the lore_id for this fragment
        for lore in _LORE_FRAGMENTS:
            if lore["text"] == puzzle.lore_fragment and lore["id"] not in progress["unlocked"]:
                progress["unlocked"].append(lore["id"])
                break
        progress["total_solved"] = progress.get("total_solved", 0) + 1
        _save_lore_progress(player_id, progress)
    else:
        score = max(5, int(20 * buff_mult))

    xp = max(3, int(score * 0.5))

    # Clean up
    _active_signals.pop(puzzle_id, None)

    return SignalDecodeResult(
        puzzle_id=puzzle_id,
        puzzle_type=puzzle.puzzle_type,
        correct=correct,
        player_answer=player_answer.strip().upper(),
        expected_answer=puzzle.answer,
        score=score,
        xp_earned=xp,
        lore_fragment=lore_fragment,
    )


# ────────────────────────────────────────────────────────────────
# 3. Resource Harvest — Merge-Style Tile Game
# ────────────────────────────────────────────────────────────────

@dataclass
class HarvestBoard:
    """A Resource Harvest merge-style puzzle board."""
    board_id: str
    grid_size: int          # 4x4 or 5x5
    tiles: List[List[dict]] # 2D grid of {tier, resource_type, id}
    resource_types: List[str]
    merge_cost: int         # tiles needed to merge (3 normally, 2 with cosmic buff)
    difficulty: int
    time_limit_seconds: int
    max_tier: int           # 4


@dataclass
class HarvestResult:
    """Scoring result for a Resource Harvest game."""
    board_id: str
    merges_completed: int
    highest_tier_reached: int
    resources_earned: Dict[str, int]
    score: int
    xp_earned: int


_HARVEST_RESOURCE_TYPES = ["energy", "materials", "data", "food"]

# Active boards cache
_active_harvests: Dict[str, HarvestBoard] = {}


def generate_harvest_board(
    difficulty: int = None,
    module_level: int = 1,
    cosmic_buff: float = 0.0,
) -> HarvestBoard:
    """Generate a Resource Harvest board.

    Args:
        difficulty: 1-5, or None for auto.
        module_level: Player's Workshop/Quarters level.
        cosmic_buff: If positive, merge cost reduced to 2.

    Returns:
        A HarvestBoard ready for frontend rendering.
    """
    if difficulty is None:
        difficulty = min(5, max(1, (module_level + 1) // 2))

    grid_size = 4 if difficulty <= 3 else 5
    merge_cost = 2 if cosmic_buff > 0 else 3

    # Generate initial tiles (mostly tier 1, some tier 2)
    tiles = []
    for row in range(grid_size):
        tile_row = []
        for col in range(grid_size):
            tier = 1 if random.random() < 0.8 else 2
            resource_type = random.choice(_HARVEST_RESOURCE_TYPES)
            tile_row.append({
                "id": f"t_{row}_{col}",
                "tier": tier,
                "resource_type": resource_type,
            })
        tiles.append(tile_row)

    time_limit = max(60, 120 - difficulty * 10)
    board_id = f"rh_{uuid.uuid4().hex[:12]}"

    board = HarvestBoard(
        board_id=board_id,
        grid_size=grid_size,
        tiles=tiles,
        resource_types=_HARVEST_RESOURCE_TYPES,
        merge_cost=merge_cost,
        difficulty=difficulty,
        time_limit_seconds=time_limit,
        max_tier=4,
    )

    _active_harvests[board_id] = board
    return board


def score_harvest(
    board_id: str,
    merges: List[dict],
    time_taken: float = 0.0,
    cosmic_buff: float = 0.0,
) -> HarvestResult:
    """Score a Resource Harvest game.

    Args:
        board_id: The board being scored.
        merges: List of merge actions [{tiles: [id, id, id], result_tier: int, resource_type: str}].
        time_taken: Seconds the player took.
        cosmic_buff: Buff/debuff percentage from cosmic state.

    Returns:
        A HarvestResult with resources earned and score.
    """
    board = _active_harvests.get(board_id)
    if board is None:
        raise ValueError(f"Unknown board_id: {board_id}")

    merges_completed = len(merges)
    highest_tier = 1
    resources_earned: Dict[str, int] = {}

    for merge in merges:
        result_tier = merge.get("result_tier", 1)
        resource_type = merge.get("resource_type", "energy")
        highest_tier = max(highest_tier, result_tier)

        # Resources earned per merge: tier * 5
        amount = result_tier * 5
        resources_earned[resource_type] = resources_earned.get(resource_type, 0) + amount

    # Score calculation
    base_score = merges_completed * 15 + highest_tier * 25
    difficulty_mult = 1.0 + (board.difficulty - 1) * 0.2
    speed_ratio = max(0.0, 1.0 - (time_taken / board.time_limit_seconds))
    speed_bonus = 1.0 + (speed_ratio * 0.3)
    buff_mult = 1.0 + (cosmic_buff / 100.0)

    raw_score = int(base_score * difficulty_mult * speed_bonus)
    score = max(10, int(raw_score * buff_mult))
    xp = max(5, int(score * 0.5))

    # Apply cosmic buff to resources
    if cosmic_buff > 0:
        for k in resources_earned:
            resources_earned[k] = int(resources_earned[k] * buff_mult)

    # Clean up
    _active_harvests.pop(board_id, None)

    return HarvestResult(
        board_id=board_id,
        merges_completed=merges_completed,
        highest_tier_reached=highest_tier,
        resources_earned=resources_earned,
        score=score,
        xp_earned=xp,
    )


# ────────────────────────────────────────────────────────────────
# 4. Sky Scanner — Celestial Object Identification
# ────────────────────────────────────────────────────────────────

@dataclass
class SkyScannerSession:
    """A Sky Scanner identification session."""
    session_id: str
    targets: List[dict]       # [{id, name, type, ra, dec, magnitude, hint}]
    bonus_targets: List[dict] # extra targets during events
    difficulty: int
    time_limit_seconds: int
    sky_region: str           # "northern", "southern", "equatorial"


@dataclass
class SkyScannerResult:
    """Scoring result for a Sky Scanner session."""
    session_id: str
    targets_found: int
    targets_total: int
    bonus_found: int
    accuracy: float
    score: int
    xp_earned: int


# Celestial objects database
_CELESTIAL_OBJECTS: List[dict] = [
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

# Active sessions cache
_active_scanners: Dict[str, SkyScannerSession] = {}


def generate_sky_scanner_session(
    difficulty: int = None,
    module_level: int = 1,
    event_active: bool = False,
) -> SkyScannerSession:
    """Generate a Sky Scanner identification session.

    Args:
        difficulty: 1-5, or None for auto.
        module_level: Player's Observatory module level.
        event_active: Whether an astronomical event is active (adds bonus targets).

    Returns:
        A SkyScannerSession ready for backend scoring.
    """
    if difficulty is None:
        difficulty = min(5, max(1, (module_level + 1) // 2))

    # Number of targets based on difficulty
    num_targets = min(len(_CELESTIAL_OBJECTS), 3 + difficulty)
    targets = random.sample(_CELESTIAL_OBJECTS, num_targets)

    # Bonus targets during events
    bonus_targets = []
    if event_active:
        remaining = [obj for obj in _CELESTIAL_OBJECTS if obj not in targets]
        if remaining:
            bonus_targets = random.sample(remaining, min(2, len(remaining)))

    # Determine sky region
    avg_dec = sum(t["dec"] for t in targets) / len(targets) if targets else 0
    if avg_dec > 20:
        sky_region = "northern"
    elif avg_dec < -20:
        sky_region = "southern"
    else:
        sky_region = "equatorial"

    time_limit = max(30, 90 - difficulty * 10)
    session_id = f"ss_{uuid.uuid4().hex[:12]}"

    session = SkyScannerSession(
        session_id=session_id,
        targets=targets,
        bonus_targets=bonus_targets,
        difficulty=difficulty,
        time_limit_seconds=time_limit,
        sky_region=sky_region,
    )

    _active_scanners[session_id] = session
    return session


def score_sky_scanner(
    session_id: str,
    identified: List[str],
    time_taken: float = 0.0,
    cosmic_buff: float = 0.0,
) -> SkyScannerResult:
    """Score a Sky Scanner session.

    Args:
        session_id: The session being scored.
        identified: List of object IDs the player identified.
        time_taken: Seconds the player took.
        cosmic_buff: Buff/debuff percentage from cosmic state.

    Returns:
        A SkyScannerResult with identification stats and score.
    """
    session = _active_scanners.get(session_id)
    if session is None:
        raise ValueError(f"Unknown session_id: {session_id}")

    target_ids = {t["id"] for t in session.targets}
    bonus_ids = {t["id"] for t in session.bonus_targets}
    all_valid = target_ids | bonus_ids

    identified_set = set(identified)
    correct = identified_set & all_valid
    incorrect = identified_set - all_valid

    targets_found = len(correct & target_ids)
    bonus_found = len(correct & bonus_ids)
    targets_total = len(target_ids)

    total_attempts = len(correct) + len(incorrect)
    accuracy = len(correct) / max(1, total_attempts)

    # Score calculation
    base_score = targets_found * 20 + bonus_found * 30
    difficulty_mult = 1.0 + (session.difficulty - 1) * 0.25
    speed_ratio = max(0.0, 1.0 - (time_taken / session.time_limit_seconds))
    speed_bonus = 1.0 + (speed_ratio * 0.4)
    accuracy_bonus = 1.0 + (accuracy * 0.3)
    buff_mult = 1.0 + (cosmic_buff / 100.0)

    raw_score = int(base_score * difficulty_mult * speed_bonus * accuracy_bonus)
    score = max(10, int(raw_score * buff_mult))
    xp = max(5, int(score * 0.5))

    # Clean up
    _active_scanners.pop(session_id, None)

    return SkyScannerResult(
        session_id=session_id,
        targets_found=targets_found,
        targets_total=targets_total,
        bonus_found=bonus_found,
        accuracy=round(accuracy, 4),
        score=score,
        xp_earned=xp,
    )


# ────────────────────────────────────────────────────────────────
# Serialization Helpers
# ────────────────────────────────────────────────────────────────

def diplomacy_scenario_to_dict(scenario: DiplomacyScenario) -> dict:
    """Serialize a DiplomacyScenario to a JSON-safe dictionary."""
    return {
        "scenario_id": scenario.scenario_id,
        "npc": {
            "npc_id": scenario.npc.npc_id,
            "name": scenario.npc.name,
            "role": scenario.npc.role,
            "mood": scenario.npc.mood,
            "relationship": scenario.npc.relationship,
            "backstory": scenario.npc.backstory,
        },
        "situation": scenario.situation,
        "choices": scenario.choices,
        "difficulty": scenario.difficulty,
        "time_limit_seconds": scenario.time_limit_seconds,
        "cosmic_mood": scenario.cosmic_mood,
    }


def diplomacy_result_to_dict(result: DiplomacyResult) -> dict:
    """Serialize a DiplomacyResult to a JSON-safe dictionary."""
    return {
        "scenario_id": result.scenario_id,
        "npc_id": result.npc_id,
        "npc_name": result.npc_name,
        "choice_id": result.choice_id,
        "relationship_change": result.relationship_change,
        "new_relationship": result.new_relationship,
        "new_mood": result.new_mood,
        "score": result.score,
        "xp_earned": result.xp_earned,
        "dialogue_response": result.dialogue_response,
    }


def signal_puzzle_to_dict(puzzle: SignalPuzzle) -> dict:
    """Serialize a SignalPuzzle to a JSON-safe dictionary (hides answer)."""
    return {
        "puzzle_id": puzzle.puzzle_id,
        "puzzle_type": puzzle.puzzle_type,
        "encoded_message": puzzle.encoded_message,
        "hint": puzzle.hint,
        "difficulty": puzzle.difficulty,
        "time_limit_seconds": puzzle.time_limit_seconds,
    }


def signal_result_to_dict(result: SignalDecodeResult) -> dict:
    """Serialize a SignalDecodeResult to a JSON-safe dictionary."""
    return {
        "puzzle_id": result.puzzle_id,
        "puzzle_type": result.puzzle_type,
        "correct": result.correct,
        "player_answer": result.player_answer,
        "expected_answer": result.expected_answer,
        "score": result.score,
        "xp_earned": result.xp_earned,
        "lore_fragment": result.lore_fragment,
    }


def harvest_board_to_dict(board: HarvestBoard) -> dict:
    """Serialize a HarvestBoard to a JSON-safe dictionary."""
    return {
        "board_id": board.board_id,
        "grid_size": board.grid_size,
        "tiles": board.tiles,
        "resource_types": board.resource_types,
        "merge_cost": board.merge_cost,
        "difficulty": board.difficulty,
        "time_limit_seconds": board.time_limit_seconds,
        "max_tier": board.max_tier,
    }


def harvest_result_to_dict(result: HarvestResult) -> dict:
    """Serialize a HarvestResult to a JSON-safe dictionary."""
    return {
        "board_id": result.board_id,
        "merges_completed": result.merges_completed,
        "highest_tier_reached": result.highest_tier_reached,
        "resources_earned": result.resources_earned,
        "score": result.score,
        "xp_earned": result.xp_earned,
    }


def sky_scanner_session_to_dict(session: SkyScannerSession) -> dict:
    """Serialize a SkyScannerSession to a JSON-safe dictionary."""
    return {
        "session_id": session.session_id,
        "targets": [
            {
                "id": t["id"],
                "name": t["name"],
                "type": t["type"],
                "magnitude": t["magnitude"],
                "hint": t["hint"],
            }
            for t in session.targets
        ],
        "bonus_targets": [
            {
                "id": t["id"],
                "name": t["name"],
                "type": t["type"],
                "magnitude": t["magnitude"],
                "hint": t["hint"],
            }
            for t in session.bonus_targets
        ],
        "difficulty": session.difficulty,
        "time_limit_seconds": session.time_limit_seconds,
        "sky_region": session.sky_region,
    }


def sky_scanner_result_to_dict(result: SkyScannerResult) -> dict:
    """Serialize a SkyScannerResult to a JSON-safe dictionary."""
    return {
        "session_id": result.session_id,
        "targets_found": result.targets_found,
        "targets_total": result.targets_total,
        "bonus_found": result.bonus_found,
        "accuracy": result.accuracy,
        "score": result.score,
        "xp_earned": result.xp_earned,
    }

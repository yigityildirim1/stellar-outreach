"""
NEXUS STATION - Stellar Outreach: Core Mini-Games Backend (TASK-004)

Backend logic for the three core mini-games and the daily mission system.
Handles puzzle generation, scoring, and cosmic buff integration.

Mini-Games:
    1. Star Pattern Match  — constellation tracing (Observatory)
    2. Module Repair Puzzle — circuit-board path routing (Quarters/Workshop)
    3. Asteroid Deflection  — trajectory correction (Bridge)

References:
    - GDD S5.3: Mini-game definitions
    - GDD S5.2: Daily mission system & cosmic state mapping

Security Note (Article II / Kai Chen review):
    This module generates and scores puzzles using deterministic or
    seeded randomness. No player data is stored or transmitted beyond
    the scoring result structures returned to callers.
"""

from __future__ import annotations

import hashlib
import math
import random
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Dict, List, Optional, Tuple


# ────────────────────────────────────────────────────────────────
# 1. Star Pattern Match — Constellation Data & Logic
# ────────────────────────────────────────────────────────────────

@dataclass
class ConstellationPuzzle:
    """A Star Pattern Match puzzle for the Observatory module."""
    puzzle_id: str
    constellation_name: str
    stars: List[dict]                        # {id, name, x, y, magnitude, spectral_type}
    connections: List[Tuple[str, str]]       # full set of star-to-star connections
    revealed_connections: List[Tuple[str, str]]  # shown to player
    hidden_connections: List[Tuple[str, str]]    # player must trace
    difficulty: int                           # 1-5
    fun_fact: str
    time_limit_seconds: int


@dataclass
class StarPatternResult:
    """Scoring result for a Star Pattern Match puzzle."""
    puzzle_id: str
    constellation_name: str
    connections_found: int
    connections_total: int
    accuracy: float           # 0-1
    time_taken_seconds: float
    score: int
    xp_earned: int
    perfect: bool


# Real constellation data: stars with approximate normalized portrait positions
# Coordinates: x in [0, 1], y in [0, 1.5] for portrait layout
_CONSTELLATION_DATA: Dict[str, dict] = {
    "Orion": {
        "difficulty": 4,
        "fun_fact": "Betelgeuse, Orion's red supergiant shoulder star, is so large that if placed at our Sun's position its surface would extend past the orbit of Jupiter.",
        "stars": [
            {"id": "betelgeuse",  "name": "Betelgeuse",  "x": 0.35, "y": 0.25, "magnitude": 0.42, "spectral_type": "M1"},
            {"id": "rigel",       "name": "Rigel",        "x": 0.65, "y": 1.20, "magnitude": 0.13, "spectral_type": "B8"},
            {"id": "bellatrix",   "name": "Bellatrix",    "x": 0.62, "y": 0.28, "magnitude": 1.64, "spectral_type": "B2"},
            {"id": "mintaka",     "name": "Mintaka",      "x": 0.52, "y": 0.65, "magnitude": 2.23, "spectral_type": "O9"},
            {"id": "alnilam",     "name": "Alnilam",      "x": 0.48, "y": 0.70, "magnitude": 1.69, "spectral_type": "B0"},
            {"id": "alnitak",     "name": "Alnitak",      "x": 0.44, "y": 0.75, "magnitude": 1.77, "spectral_type": "O9"},
            {"id": "saiph",       "name": "Saiph",        "x": 0.38, "y": 1.15, "magnitude": 2.09, "spectral_type": "B0"},
        ],
        "connections": [
            ("betelgeuse", "bellatrix"),
            ("betelgeuse", "alnitak"),
            ("bellatrix", "mintaka"),
            ("mintaka", "alnilam"),
            ("alnilam", "alnitak"),
            ("alnitak", "saiph"),
            ("mintaka", "rigel"),
        ],
    },
    "Ursa Major": {
        "difficulty": 2,
        "fun_fact": "Five of the seven stars in the Big Dipper are part of the Ursa Major Moving Group, traveling together through space at about 14.4 km/s.",
        "stars": [
            {"id": "dubhe",   "name": "Dubhe",   "x": 0.25, "y": 0.30, "magnitude": 1.79, "spectral_type": "K0"},
            {"id": "merak",   "name": "Merak",    "x": 0.30, "y": 0.50, "magnitude": 2.37, "spectral_type": "A1"},
            {"id": "phecda",  "name": "Phecda",   "x": 0.48, "y": 0.55, "magnitude": 2.44, "spectral_type": "A0"},
            {"id": "megrez",  "name": "Megrez",   "x": 0.50, "y": 0.38, "magnitude": 3.31, "spectral_type": "A3"},
            {"id": "alioth",  "name": "Alioth",   "x": 0.62, "y": 0.42, "magnitude": 1.77, "spectral_type": "A1"},
            {"id": "mizar",   "name": "Mizar",    "x": 0.72, "y": 0.50, "magnitude": 2.27, "spectral_type": "A2"},
            {"id": "alkaid",  "name": "Alkaid",   "x": 0.82, "y": 0.62, "magnitude": 1.86, "spectral_type": "B3"},
        ],
        "connections": [
            ("dubhe", "merak"),
            ("merak", "phecda"),
            ("phecda", "megrez"),
            ("megrez", "dubhe"),
            ("megrez", "alioth"),
            ("alioth", "mizar"),
            ("mizar", "alkaid"),
        ],
    },
    "Ursa Minor": {
        "difficulty": 1,
        "fun_fact": "Polaris, the North Star at the tip of Ursa Minor's handle, is actually a triple star system and a Cepheid variable that pulsates in brightness.",
        "stars": [
            {"id": "polaris",   "name": "Polaris",   "x": 0.50, "y": 0.15, "magnitude": 1.98, "spectral_type": "F7"},
            {"id": "yildun",    "name": "Yildun",    "x": 0.55, "y": 0.35, "magnitude": 4.36, "spectral_type": "A1"},
            {"id": "epsilon",   "name": "Epsilon UMi", "x": 0.60, "y": 0.52, "magnitude": 4.23, "spectral_type": "G5"},
            {"id": "zeta",      "name": "Zeta UMi",  "x": 0.52, "y": 0.68, "magnitude": 4.32, "spectral_type": "A3"},
            {"id": "eta",       "name": "Eta UMi",   "x": 0.42, "y": 0.78, "magnitude": 4.95, "spectral_type": "F5"},
            {"id": "beta",      "name": "Kochab",    "x": 0.35, "y": 0.65, "magnitude": 2.08, "spectral_type": "K4"},
            {"id": "gamma",     "name": "Pherkad",   "x": 0.32, "y": 0.72, "magnitude": 3.05, "spectral_type": "A3"},
        ],
        "connections": [
            ("polaris", "yildun"),
            ("yildun", "epsilon"),
            ("epsilon", "zeta"),
            ("zeta", "eta"),
            ("eta", "beta"),
            ("beta", "gamma"),
        ],
    },
    "Cassiopeia": {
        "difficulty": 1,
        "fun_fact": "Cassiopeia contains two notable supernova remnants, including Tycho's Supernova observed by Tycho Brahe in 1572 — visible in daylight for two weeks.",
        "stars": [
            {"id": "schedar",    "name": "Schedar",    "x": 0.20, "y": 0.50, "magnitude": 2.23, "spectral_type": "K0"},
            {"id": "caph",       "name": "Caph",       "x": 0.30, "y": 0.30, "magnitude": 2.27, "spectral_type": "F2"},
            {"id": "gamma_cas",  "name": "Gamma Cas",  "x": 0.45, "y": 0.55, "magnitude": 2.47, "spectral_type": "B0"},
            {"id": "ruchbah",    "name": "Ruchbah",    "x": 0.60, "y": 0.35, "magnitude": 2.68, "spectral_type": "A5"},
            {"id": "segin",      "name": "Segin",      "x": 0.75, "y": 0.52, "magnitude": 3.37, "spectral_type": "B3"},
        ],
        "connections": [
            ("schedar", "caph"),
            ("schedar", "gamma_cas"),
            ("gamma_cas", "ruchbah"),
            ("ruchbah", "segin"),
        ],
    },
    "Leo": {
        "difficulty": 3,
        "fun_fact": "Regulus, the heart of Leo, spins so fast it is shaped like a flattened egg — completing one rotation every 15.9 hours compared to our Sun's 25 days.",
        "stars": [
            {"id": "regulus",     "name": "Regulus",     "x": 0.30, "y": 0.85, "magnitude": 1.35, "spectral_type": "B8"},
            {"id": "eta_leo",     "name": "Eta Leo",     "x": 0.25, "y": 0.55, "magnitude": 3.52, "spectral_type": "A0"},
            {"id": "algieba",     "name": "Algieba",     "x": 0.32, "y": 0.45, "magnitude": 2.08, "spectral_type": "K1"},
            {"id": "zosma",       "name": "Zosma",       "x": 0.55, "y": 0.50, "magnitude": 2.56, "spectral_type": "A4"},
            {"id": "chertan",     "name": "Chertan",     "x": 0.50, "y": 0.70, "magnitude": 3.34, "spectral_type": "A2"},
            {"id": "denebola",    "name": "Denebola",    "x": 0.75, "y": 0.55, "magnitude": 2.14, "spectral_type": "A3"},
            {"id": "epsilon_leo", "name": "Ras Elased",  "x": 0.28, "y": 0.28, "magnitude": 2.98, "spectral_type": "G1"},
            {"id": "mu_leo",      "name": "Mu Leo",      "x": 0.38, "y": 0.32, "magnitude": 3.88, "spectral_type": "K2"},
        ],
        "connections": [
            ("regulus", "eta_leo"),
            ("eta_leo", "algieba"),
            ("algieba", "mu_leo"),
            ("mu_leo", "epsilon_leo"),
            ("algieba", "zosma"),
            ("zosma", "chertan"),
            ("chertan", "regulus"),
            ("zosma", "denebola"),
        ],
    },
    "Scorpius": {
        "difficulty": 4,
        "fun_fact": "Antares, the red supergiant heart of Scorpius, has a diameter about 700 times that of our Sun. If placed in our solar system it would engulf Mars.",
        "stars": [
            {"id": "graffias",  "name": "Graffias",  "x": 0.40, "y": 0.15, "magnitude": 2.62, "spectral_type": "B1"},
            {"id": "dschubba",  "name": "Dschubba",  "x": 0.45, "y": 0.25, "magnitude": 2.32, "spectral_type": "B0"},
            {"id": "acrab",     "name": "Acrab",     "x": 0.38, "y": 0.10, "magnitude": 2.56, "spectral_type": "B1"},
            {"id": "antares",   "name": "Antares",   "x": 0.50, "y": 0.50, "magnitude": 0.96, "spectral_type": "M1"},
            {"id": "tau_sco",   "name": "Tau Sco",   "x": 0.55, "y": 0.38, "magnitude": 2.82, "spectral_type": "B0"},
            {"id": "epsilon_sco","name": "Epsilon Sco","x": 0.58, "y": 0.68, "magnitude": 2.29, "spectral_type": "K2"},
            {"id": "zeta_sco",  "name": "Zeta Sco",  "x": 0.52, "y": 0.82, "magnitude": 3.62, "spectral_type": "B1"},
            {"id": "kappa_sco", "name": "Kappa Sco", "x": 0.45, "y": 0.95, "magnitude": 2.41, "spectral_type": "B1"},
            {"id": "shaula",    "name": "Shaula",     "x": 0.38, "y": 1.15, "magnitude": 1.63, "spectral_type": "B2"},
            {"id": "lesath",    "name": "Lesath",     "x": 0.40, "y": 1.18, "magnitude": 2.69, "spectral_type": "B2"},
        ],
        "connections": [
            ("acrab", "graffias"),
            ("graffias", "dschubba"),
            ("dschubba", "tau_sco"),
            ("tau_sco", "antares"),
            ("antares", "epsilon_sco"),
            ("epsilon_sco", "zeta_sco"),
            ("zeta_sco", "kappa_sco"),
            ("kappa_sco", "shaula"),
            ("shaula", "lesath"),
        ],
    },
    "Gemini": {
        "difficulty": 3,
        "fun_fact": "Castor, one of the Gemini twins, is actually a sextuple star system — six stars orbiting each other in three gravitationally bound pairs.",
        "stars": [
            {"id": "castor",    "name": "Castor",    "x": 0.42, "y": 0.15, "magnitude": 1.58, "spectral_type": "A1"},
            {"id": "pollux",    "name": "Pollux",    "x": 0.52, "y": 0.22, "magnitude": 1.14, "spectral_type": "K0"},
            {"id": "alhena",    "name": "Alhena",    "x": 0.55, "y": 0.80, "magnitude": 1.93, "spectral_type": "A1"},
            {"id": "wasat",     "name": "Wasat",     "x": 0.50, "y": 0.55, "magnitude": 3.53, "spectral_type": "F0"},
            {"id": "mebsuta",   "name": "Mebsuta",   "x": 0.38, "y": 0.48, "magnitude": 3.06, "spectral_type": "G8"},
            {"id": "tejat",     "name": "Tejat",     "x": 0.32, "y": 0.72, "magnitude": 2.88, "spectral_type": "M3"},
            {"id": "propus",    "name": "Propus",    "x": 0.28, "y": 0.82, "magnitude": 3.31, "spectral_type": "M3"},
        ],
        "connections": [
            ("castor", "mebsuta"),
            ("mebsuta", "tejat"),
            ("tejat", "propus"),
            ("pollux", "wasat"),
            ("wasat", "alhena"),
            ("castor", "pollux"),
        ],
    },
    "Taurus": {
        "difficulty": 3,
        "fun_fact": "The Pleiades star cluster in Taurus contains over 1,000 confirmed members and is one of the nearest star clusters to Earth at about 444 light-years away.",
        "stars": [
            {"id": "aldebaran",   "name": "Aldebaran",   "x": 0.45, "y": 0.65, "magnitude": 0.86, "spectral_type": "K5"},
            {"id": "elnath",      "name": "Elnath",      "x": 0.72, "y": 0.20, "magnitude": 1.65, "spectral_type": "B7"},
            {"id": "zeta_tau",    "name": "Zeta Tau",    "x": 0.70, "y": 0.35, "magnitude": 3.01, "spectral_type": "B2"},
            {"id": "theta2_tau",  "name": "Theta2 Tau",  "x": 0.50, "y": 0.55, "magnitude": 3.40, "spectral_type": "A7"},
            {"id": "gamma_tau",   "name": "Gamma Tau",   "x": 0.42, "y": 0.52, "magnitude": 3.65, "spectral_type": "G8"},
            {"id": "delta_tau",   "name": "Delta Tau",   "x": 0.38, "y": 0.48, "magnitude": 3.77, "spectral_type": "G8"},
            {"id": "epsilon_tau", "name": "Epsilon Tau", "x": 0.52, "y": 0.48, "magnitude": 3.53, "spectral_type": "K0"},
        ],
        "connections": [
            ("aldebaran", "theta2_tau"),
            ("theta2_tau", "gamma_tau"),
            ("gamma_tau", "delta_tau"),
            ("theta2_tau", "epsilon_tau"),
            ("epsilon_tau", "elnath"),
            ("elnath", "zeta_tau"),
        ],
    },
    "Cygnus": {
        "difficulty": 2,
        "fun_fact": "Cygnus X-1, located in this constellation, was the first widely accepted black hole candidate and the subject of a famous bet between Stephen Hawking and Kip Thorne.",
        "stars": [
            {"id": "deneb",     "name": "Deneb",      "x": 0.50, "y": 0.15, "magnitude": 1.25, "spectral_type": "A2"},
            {"id": "sadr",      "name": "Sadr",       "x": 0.50, "y": 0.50, "magnitude": 2.20, "spectral_type": "F8"},
            {"id": "gienah",    "name": "Gienah Cyg", "x": 0.30, "y": 0.70, "magnitude": 2.46, "spectral_type": "K0"},
            {"id": "delta_cyg", "name": "Delta Cyg",  "x": 0.70, "y": 0.68, "magnitude": 2.87, "spectral_type": "B9"},
            {"id": "albireo",   "name": "Albireo",    "x": 0.50, "y": 1.00, "magnitude": 3.08, "spectral_type": "K3"},
        ],
        "connections": [
            ("deneb", "sadr"),
            ("sadr", "gienah"),
            ("sadr", "delta_cyg"),
            ("sadr", "albireo"),
        ],
    },
    "Lyra": {
        "difficulty": 1,
        "fun_fact": "Vega in Lyra was the first star besides the Sun to be photographed (1850) and the first to have its spectrum recorded. It served as the standard zero-magnitude star for over a century.",
        "stars": [
            {"id": "vega",        "name": "Vega",        "x": 0.50, "y": 0.20, "magnitude": 0.03, "spectral_type": "A0"},
            {"id": "sheliak",     "name": "Sheliak",     "x": 0.55, "y": 0.55, "magnitude": 3.52, "spectral_type": "A8"},
            {"id": "sulafat",     "name": "Sulafat",     "x": 0.58, "y": 0.65, "magnitude": 3.24, "spectral_type": "B9"},
            {"id": "delta1_lyr",  "name": "Delta1 Lyr",  "x": 0.42, "y": 0.58, "magnitude": 5.58, "spectral_type": "B2"},
            {"id": "delta2_lyr",  "name": "Delta2 Lyr",  "x": 0.40, "y": 0.65, "magnitude": 4.30, "spectral_type": "M4"},
        ],
        "connections": [
            ("vega", "sheliak"),
            ("vega", "delta1_lyr"),
            ("sheliak", "sulafat"),
            ("delta1_lyr", "delta2_lyr"),
            ("sulafat", "delta2_lyr"),
        ],
    },
    "Aquila": {
        "difficulty": 2,
        "fun_fact": "Altair, the brightest star in Aquila, rotates so rapidly (once every 8.9 hours) that it bulges at the equator, making it 22% wider than it is tall.",
        "stars": [
            {"id": "altair",     "name": "Altair",      "x": 0.50, "y": 0.45, "magnitude": 0.77, "spectral_type": "A7"},
            {"id": "tarazed",    "name": "Tarazed",     "x": 0.42, "y": 0.35, "magnitude": 2.72, "spectral_type": "K3"},
            {"id": "alshain",    "name": "Alshain",     "x": 0.55, "y": 0.55, "magnitude": 3.71, "spectral_type": "G8"},
            {"id": "theta_aql",  "name": "Theta Aql",   "x": 0.60, "y": 0.80, "magnitude": 3.23, "spectral_type": "B9"},
            {"id": "delta_aql",  "name": "Delta Aql",   "x": 0.40, "y": 0.18, "magnitude": 3.36, "spectral_type": "F0"},
            {"id": "lambda_aql", "name": "Lambda Aql",  "x": 0.58, "y": 0.15, "magnitude": 3.44, "spectral_type": "B9"},
        ],
        "connections": [
            ("delta_aql", "tarazed"),
            ("tarazed", "altair"),
            ("altair", "alshain"),
            ("alshain", "theta_aql"),
            ("lambda_aql", "delta_aql"),
        ],
    },
    "Canis Major": {
        "difficulty": 3,
        "fun_fact": "Sirius, the Dog Star in Canis Major, is the brightest star in the night sky at magnitude -1.46. It is actually a binary system — Sirius B is a white dwarf the size of Earth but with the mass of the Sun.",
        "stars": [
            {"id": "sirius",     "name": "Sirius",     "x": 0.45, "y": 0.25, "magnitude": -1.46, "spectral_type": "A1"},
            {"id": "mirzam",     "name": "Mirzam",     "x": 0.30, "y": 0.30, "magnitude": 1.98, "spectral_type": "B1"},
            {"id": "wezen",      "name": "Wezen",      "x": 0.50, "y": 0.72, "magnitude": 1.84, "spectral_type": "F8"},
            {"id": "adhara",     "name": "Adhara",     "x": 0.42, "y": 0.90, "magnitude": 1.50, "spectral_type": "B2"},
            {"id": "furud",      "name": "Furud",      "x": 0.35, "y": 1.05, "magnitude": 3.02, "spectral_type": "B3"},
            {"id": "aludra",     "name": "Aludra",     "x": 0.58, "y": 0.95, "magnitude": 2.45, "spectral_type": "B5"},
        ],
        "connections": [
            ("sirius", "mirzam"),
            ("sirius", "wezen"),
            ("wezen", "adhara"),
            ("wezen", "aludra"),
            ("adhara", "furud"),
        ],
    },
}

# Puzzle cache for scoring lookups
_active_puzzles: Dict[str, ConstellationPuzzle] = {}


def _connection_set(conns: List[Tuple[str, str]]) -> set:
    """Normalize connections to a set of frozensets for order-independent comparison."""
    return {frozenset(c) for c in conns}


def generate_star_puzzle(difficulty: int = None, module_level: int = 1) -> ConstellationPuzzle:
    """Generate a Star Pattern Match puzzle.

    Args:
        difficulty: Target difficulty 1-5. None = random.
        module_level: Player's Observatory module level (affects reveal ratio).

    Returns:
        A ConstellationPuzzle ready for the frontend to render.
    """
    # Filter constellations by difficulty
    candidates = []
    for name, data in _CONSTELLATION_DATA.items():
        if difficulty is not None and data["difficulty"] != difficulty:
            continue
        candidates.append((name, data))

    if not candidates:
        # Fallback: pick from all constellations
        candidates = list(_CONSTELLATION_DATA.items())

    const_name, const_data = random.choice(candidates)

    all_connections = [tuple(c) for c in const_data["connections"]]
    total = len(all_connections)

    # Reveal ratio: higher module_level => fewer revealed (harder gameplay)
    # At level 1 reveal ~60%, at level 10 reveal ~20%
    reveal_ratio = max(0.15, 0.65 - (module_level - 1) * 0.05)
    num_revealed = max(1, int(total * reveal_ratio))
    num_revealed = min(num_revealed, total - 1)  # always hide at least 1

    shuffled = list(all_connections)
    random.shuffle(shuffled)
    revealed = shuffled[:num_revealed]
    hidden = shuffled[num_revealed:]

    # Time limit: based on difficulty and hidden count
    base_time = 30
    time_limit = base_time + len(hidden) * 10 + (5 - const_data["difficulty"]) * 5

    puzzle_id = f"sp_{uuid.uuid4().hex[:12]}"

    puzzle = ConstellationPuzzle(
        puzzle_id=puzzle_id,
        constellation_name=const_name,
        stars=list(const_data["stars"]),
        connections=all_connections,
        revealed_connections=revealed,
        hidden_connections=hidden,
        difficulty=const_data["difficulty"],
        fun_fact=const_data["fun_fact"],
        time_limit_seconds=time_limit,
    )

    _active_puzzles[puzzle_id] = puzzle
    return puzzle


def score_star_puzzle(
    puzzle_id: str,
    player_connections: list,
    time_taken: float,
    cosmic_buff: float = 0.0,
) -> StarPatternResult:
    """Score a completed Star Pattern Match puzzle.

    Args:
        puzzle_id: The puzzle being scored.
        player_connections: List of [star_a, star_b] pairs the player traced.
        time_taken: Seconds the player took.
        cosmic_buff: Buff/debuff percentage from cosmic state.

    Returns:
        A StarPatternResult with score and XP.
    """
    puzzle = _active_puzzles.get(puzzle_id)
    if puzzle is None:
        raise ValueError(f"Unknown puzzle_id: {puzzle_id}")

    hidden_set = _connection_set(puzzle.hidden_connections)
    player_set = _connection_set([tuple(c) for c in player_connections])

    correct = hidden_set & player_set
    incorrect = player_set - hidden_set - _connection_set(puzzle.revealed_connections)

    connections_found = len(correct)
    connections_total = len(hidden_set)

    # Accuracy: correct / (correct + incorrect), avoid div-by-zero
    total_attempts = len(correct) + len(incorrect)
    accuracy = connections_found / max(1, total_attempts)

    # Perfect: all hidden found, no mistakes
    perfect = connections_found == connections_total and len(incorrect) == 0

    # Score calculation
    # Base: 100 * accuracy * difficulty
    # Speed bonus: up to 50% bonus for finishing in under half the time limit
    speed_ratio = max(0.0, 1.0 - (time_taken / puzzle.time_limit_seconds))
    speed_bonus = 1.0 + (speed_ratio * 0.5)
    difficulty_multiplier = 1.0 + (puzzle.difficulty - 1) * 0.25

    raw_score = int(100 * accuracy * speed_bonus * difficulty_multiplier)
    if perfect:
        raw_score = int(raw_score * 1.5)

    # Apply cosmic buff
    buff_mult = 1.0 + (cosmic_buff / 100.0)
    score = max(10, int(raw_score * buff_mult))

    # XP: proportional to score
    xp = max(5, int(score * 0.6))

    # Clean up
    _active_puzzles.pop(puzzle_id, None)

    return StarPatternResult(
        puzzle_id=puzzle_id,
        constellation_name=puzzle.constellation_name,
        connections_found=connections_found,
        connections_total=connections_total,
        accuracy=round(accuracy, 4),
        time_taken_seconds=round(time_taken, 2),
        score=score,
        xp_earned=xp,
        perfect=perfect,
    )


# ────────────────────────────────────────────────────────────────
# 2. Module Repair Puzzle — Grid Path Connection
# ────────────────────────────────────────────────────────────────

@dataclass
class RepairGrid:
    """A Module Repair Puzzle for the Quarters/Workshop module."""
    puzzle_id: str
    grid_size: int
    system_type: str              # "power", "water", "air", "thermal"
    sources: List[dict]           # {id, x, y, color, system}
    sinks: List[dict]             # {id, x, y, color, system}
    obstacles: List[dict]         # {x, y}
    solution_exists: bool
    difficulty: int               # 1-5
    time_limit_seconds: int
    flavor_text: str


@dataclass
class RepairResult:
    """Scoring result for a Module Repair Puzzle."""
    puzzle_id: str
    system_type: str
    paths_completed: int
    paths_total: int
    all_cells_used: bool
    time_taken_seconds: float
    score: int
    xp_earned: int
    resources_earned: dict


# System type configurations
_SYSTEM_CONFIGS = {
    "power":   {"color": "#FFB000", "resource": "energy"},
    "water":   {"color": "#4A90D9", "resource": "food"},
    "air":     {"color": "#E0E0E0", "resource": "morale"},
    "thermal": {"color": "#D94040", "resource": "materials"},
}

_FLAVOR_TEXTS = {
    "power": [
        "The main power relay is offline. Route backup generators to critical systems.",
        "Solar panel array misaligned. Reroute power through secondary conduits.",
        "Power surge detected in section 7. Isolate and reroute to prevent overload.",
    ],
    "water": [
        "The oxygen recycler is offline. Route backup air supply.",
        "Water reclamation pump failure. Bridge the flow to hydroponics.",
        "Coolant leak in the main loop. Patch and reroute through reserve pipes.",
    ],
    "air": [
        "Atmospheric scrubbers need emergency bypass. Route clean air to crew quarters.",
        "Ventilation shaft blockage in the lower deck. Open alternate air channels.",
        "CO2 levels rising in Section B. Reroute atmospheric processors.",
    ],
    "thermal": [
        "Heat exchanger malfunction. Route thermal energy to radiator arrays.",
        "Thermal blanket breach on the starboard side. Reroute heating circuits.",
        "Cryogenic coolant leak. Emergency thermal bypass needed.",
    ],
}

# Cache for scoring
_active_repairs: Dict[str, RepairGrid] = {}


def _find_path_bfs(
    grid_size: int,
    start: Tuple[int, int],
    end: Tuple[int, int],
    blocked: set,
) -> Optional[List[Tuple[int, int]]]:
    """BFS pathfinding on the grid, avoiding blocked cells."""
    from collections import deque

    if start == end:
        return [start]

    visited = {start}
    queue = deque([(start, [start])])

    while queue:
        (cx, cy), path = queue.popleft()
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            nx, ny = cx + dx, cy + dy
            if 0 <= nx < grid_size and 0 <= ny < grid_size:
                if (nx, ny) not in visited and (nx, ny) not in blocked:
                    if (nx, ny) == end:
                        return path + [(nx, ny)]
                    visited.add((nx, ny))
                    queue.append(((nx, ny), path + [(nx, ny)]))
    return None


def generate_repair_puzzle(difficulty: int = None, module_level: int = 1) -> RepairGrid:
    """Generate a Module Repair Puzzle.

    Args:
        difficulty: Target difficulty 1-5. None = random based on module_level.
        module_level: Player's module level (affects grid size selection).

    Returns:
        A RepairGrid with guaranteed solvable path connections.
    """
    if difficulty is None:
        difficulty = min(5, max(1, (module_level + 1) // 2))

    # Grid size based on difficulty
    if difficulty <= 2:
        grid_size = 4
    elif difficulty <= 3:
        grid_size = 5
    else:
        grid_size = 6

    # Number of source-sink pairs: 2 for easy, up to 4 for hard
    num_pairs = min(4, max(2, difficulty))

    # Pick a system type
    system_type = random.choice(list(_SYSTEM_CONFIGS.keys()))
    config = _SYSTEM_CONFIGS[system_type]

    # Number of obstacles: 0 for easy, up to 3 for hard
    num_obstacles = min(3, max(0, difficulty - 2))

    # Generate valid puzzle with retries
    for _attempt in range(50):
        # Place sources on left/top edges, sinks on right/bottom edges
        used_cells: set = set()
        sources = []
        sinks = []

        # Generate source positions (left column or top row)
        source_positions = []
        for i in range(num_pairs):
            for _ in range(20):
                if random.random() < 0.5:
                    pos = (0, random.randint(0, grid_size - 1))
                else:
                    pos = (random.randint(0, grid_size - 1), 0)
                if pos not in used_cells:
                    source_positions.append(pos)
                    used_cells.add(pos)
                    break

        # Generate sink positions (right column or bottom row)
        sink_positions = []
        for i in range(len(source_positions)):
            for _ in range(20):
                if random.random() < 0.5:
                    pos = (grid_size - 1, random.randint(0, grid_size - 1))
                else:
                    pos = (random.randint(0, grid_size - 1), grid_size - 1)
                if pos not in used_cells:
                    sink_positions.append(pos)
                    used_cells.add(pos)
                    break

        actual_pairs = min(len(source_positions), len(sink_positions))
        if actual_pairs < 2:
            continue

        source_positions = source_positions[:actual_pairs]
        sink_positions = sink_positions[:actual_pairs]

        # Place obstacles (not on sources/sinks)
        obstacle_positions = []
        for _ in range(num_obstacles):
            for _ in range(20):
                ox = random.randint(1, grid_size - 2)
                oy = random.randint(1, grid_size - 2)
                if (ox, oy) not in used_cells:
                    obstacle_positions.append((ox, oy))
                    used_cells.add((ox, oy))
                    break

        # Validate all paths exist using BFS
        blocked = set(obstacle_positions)
        all_paths_valid = True
        path_cells = set()

        for i in range(actual_pairs):
            # For path validation, block cells used by previous paths
            # (simplified: just check each path independently with obstacles)
            path = _find_path_bfs(
                grid_size,
                source_positions[i],
                sink_positions[i],
                blocked | (path_cells - {source_positions[i], sink_positions[i]}),
            )
            if path is None:
                # Try without blocking previous paths
                path = _find_path_bfs(
                    grid_size,
                    source_positions[i],
                    sink_positions[i],
                    blocked,
                )
            if path is None:
                all_paths_valid = False
                break
            path_cells.update(path)

        if not all_paths_valid:
            continue

        # Build the puzzle data
        pair_colors = ["#FFB000", "#4A90D9", "#E0E0E0", "#D94040"]
        for i in range(actual_pairs):
            sx, sy = source_positions[i]
            sources.append({
                "id": f"src_{i}",
                "x": sx, "y": sy,
                "color": pair_colors[i % len(pair_colors)],
                "system": system_type,
            })
            ex, ey = sink_positions[i]
            sinks.append({
                "id": f"snk_{i}",
                "x": ex, "y": ey,
                "color": pair_colors[i % len(pair_colors)],
                "system": system_type,
            })

        obstacles = [{"x": ox, "y": oy} for ox, oy in obstacle_positions]

        flavor = random.choice(_FLAVOR_TEXTS[system_type])
        time_limit = 60 + (grid_size - 4) * 15 + (5 - difficulty) * 10

        puzzle_id = f"rp_{uuid.uuid4().hex[:12]}"

        grid = RepairGrid(
            puzzle_id=puzzle_id,
            grid_size=grid_size,
            system_type=system_type,
            sources=sources,
            sinks=sinks,
            obstacles=obstacles,
            solution_exists=True,
            difficulty=difficulty,
            time_limit_seconds=time_limit,
            flavor_text=flavor,
        )

        _active_repairs[puzzle_id] = grid
        return grid

    # Fallback: minimal guaranteed-solvable puzzle
    puzzle_id = f"rp_{uuid.uuid4().hex[:12]}"
    grid = RepairGrid(
        puzzle_id=puzzle_id,
        grid_size=4,
        system_type=system_type,
        sources=[
            {"id": "src_0", "x": 0, "y": 0, "color": "#FFB000", "system": system_type},
            {"id": "src_1", "x": 0, "y": 3, "color": "#4A90D9", "system": system_type},
        ],
        sinks=[
            {"id": "snk_0", "x": 3, "y": 0, "color": "#FFB000", "system": system_type},
            {"id": "snk_1", "x": 3, "y": 3, "color": "#4A90D9", "system": system_type},
        ],
        obstacles=[],
        solution_exists=True,
        difficulty=difficulty,
        time_limit_seconds=90,
        flavor_text=random.choice(_FLAVOR_TEXTS[system_type]),
    )

    _active_repairs[puzzle_id] = grid
    return grid


def validate_repair_solution(
    puzzle_id: str,
    paths: list,
    time_taken: float = 0.0,
    cosmic_buff: float = 0.0,
) -> RepairResult:
    """Validate and score a repair puzzle solution.

    Args:
        puzzle_id: The puzzle being scored.
        paths: List of paths. Each path is a list of [x, y] cells forming
               a continuous route from a source to its matching sink.
        time_taken: Seconds the player took.
        cosmic_buff: Buff/debuff percentage from cosmic state.

    Returns:
        A RepairResult with score and resources.
    """
    grid = _active_repairs.get(puzzle_id)
    if grid is None:
        raise ValueError(f"Unknown puzzle_id: {puzzle_id}")

    total_pairs = len(grid.sources)
    paths_completed = 0
    all_path_cells: set = set()

    # Build source/sink lookup by color
    source_lookup = {(s["x"], s["y"]): s for s in grid.sources}
    sink_lookup = {(s["x"], s["y"]): s for s in grid.sinks}
    obstacle_set = {(o["x"], o["y"]) for o in grid.obstacles}

    for path in paths:
        if len(path) < 2:
            continue

        cells = [tuple(c) for c in path]
        start = cells[0]
        end = cells[-1]

        # Verify start is a source and end is its matching sink (by color)
        src = source_lookup.get(start)
        snk = sink_lookup.get(end)

        if src is None or snk is None:
            continue
        if src["color"] != snk["color"]:
            continue

        # Verify path continuity (each cell adjacent to previous)
        valid_path = True
        for i in range(1, len(cells)):
            px, py = cells[i - 1]
            cx, cy = cells[i]
            if abs(px - cx) + abs(py - cy) != 1:
                valid_path = False
                break
            # Check bounds
            if not (0 <= cx < grid.grid_size and 0 <= cy < grid.grid_size):
                valid_path = False
                break
            # Check obstacles
            if (cx, cy) in obstacle_set:
                valid_path = False
                break

        if valid_path:
            paths_completed += 1
            all_path_cells.update(cells)

    # Check if all grid cells are used (bonus)
    total_cells = grid.grid_size * grid.grid_size - len(grid.obstacles)
    all_cells_used = len(all_path_cells) >= total_cells

    # Score calculation
    completion_ratio = paths_completed / max(1, total_pairs)
    raw_score = int(100 * completion_ratio * (1.0 + (grid.difficulty - 1) * 0.2))

    if all_cells_used:
        raw_score = int(raw_score * 1.3)

    # Speed bonus
    speed_ratio = max(0.0, 1.0 - (time_taken / grid.time_limit_seconds))
    raw_score = int(raw_score * (1.0 + speed_ratio * 0.3))

    # Cosmic buff
    buff_mult = 1.0 + (cosmic_buff / 100.0)
    score = max(10, int(raw_score * buff_mult))

    xp = max(5, int(score * 0.5))

    # Resources earned based on system type
    resource_type = _SYSTEM_CONFIGS[grid.system_type]["resource"]
    resource_amount = max(1, int(paths_completed * 5 * buff_mult))
    resources_earned = {resource_type: resource_amount}

    # Clean up
    _active_repairs.pop(puzzle_id, None)

    return RepairResult(
        puzzle_id=puzzle_id,
        system_type=grid.system_type,
        paths_completed=paths_completed,
        paths_total=total_pairs,
        all_cells_used=all_cells_used,
        time_taken_seconds=round(time_taken, 2),
        score=score,
        xp_earned=xp,
        resources_earned=resources_earned,
    )


# ────────────────────────────────────────────────────────────────
# 3. Asteroid Deflection — Trajectory Game
# ────────────────────────────────────────────────────────────────

@dataclass
class AsteroidScenario:
    """An Asteroid Deflection scenario for the Bridge module."""
    scenario_id: str
    asteroid_name: str
    asteroid_size_meters: float
    asteroid_speed_kph: float
    size_comparison: str
    approach_angle: float         # 0-360
    optimal_deflection_angle: float
    deflection_tolerance: float   # degrees of acceptable error
    distance_km: float
    difficulty: int               # 1-5
    time_limit_seconds: int
    fun_fact: str


@dataclass
class DeflectionResult:
    """Scoring result for an Asteroid Deflection scenario."""
    scenario_id: str
    asteroid_name: str
    player_angle: float
    optimal_angle: float
    angle_error: float
    success: bool
    accuracy: float              # 0-1
    score: int
    xp_earned: int
    close_call: bool


# Predefined asteroid scenarios with real-feeling data
_ASTEROID_SCENARIOS: List[dict] = [
    {
        "name": "2026 AB7",
        "size_m": 12.0,
        "speed_kph": 28000.0,
        "comparison": "the size of a school bus",
        "distance_km": 45000.0,
        "difficulty": 1,
        "fact": "Most asteroids smaller than 25 meters burn up in the atmosphere before reaching the ground, creating spectacular fireballs called bolides.",
    },
    {
        "name": "2025 KX4",
        "size_m": 35.0,
        "speed_kph": 42000.0,
        "comparison": "the size of a ten-story building",
        "distance_km": 120000.0,
        "difficulty": 2,
        "fact": "The Chelyabinsk meteor of 2013 was only about 20 meters wide but released energy equivalent to 30 Hiroshima bombs when it exploded over Russia.",
    },
    {
        "name": "2027 DL9",
        "size_m": 50.0,
        "speed_kph": 51000.0,
        "comparison": "roughly the size of the Arc de Triomphe",
        "distance_km": 280000.0,
        "difficulty": 2,
        "fact": "NASA's DART mission in 2022 successfully changed the orbit of asteroid Dimorphos by crashing a spacecraft into it at 22,530 km/h.",
    },
    {
        "name": "2024 RZ",
        "size_m": 90.0,
        "speed_kph": 36000.0,
        "comparison": "about as long as a football field",
        "distance_km": 500000.0,
        "difficulty": 3,
        "fact": "The Tunguska event of 1908 was caused by an object roughly 50-80 meters wide and flattened 2,150 square kilometers of Siberian forest.",
    },
    {
        "name": "2028 FG3",
        "size_m": 140.0,
        "speed_kph": 67000.0,
        "comparison": "the height of the Great Pyramid of Giza",
        "distance_km": 750000.0,
        "difficulty": 3,
        "fact": "An asteroid 140 meters or larger could devastate an entire region. NASA considers this the threshold for a 'potentially hazardous asteroid.'",
    },
    {
        "name": "Apophis-II",
        "size_m": 200.0,
        "speed_kph": 45000.0,
        "comparison": "about the height of the Statue of Liberty (with pedestal)",
        "distance_km": 1200000.0,
        "difficulty": 3,
        "fact": "Asteroid 99942 Apophis will pass closer to Earth than geostationary satellites on April 13, 2029 — close enough to be visible to the naked eye.",
    },
    {
        "name": "2026 MN7",
        "size_m": 300.0,
        "speed_kph": 78000.0,
        "comparison": "about as tall as the Eiffel Tower",
        "distance_km": 2000000.0,
        "difficulty": 4,
        "fact": "It takes only about 5 years of advance warning to deflect a 300-meter asteroid using a kinetic impactor — if we detect it early enough.",
    },
    {
        "name": "2029 VX1",
        "size_m": 350.0,
        "speed_kph": 55000.0,
        "comparison": "roughly the height of the Empire State Building",
        "distance_km": 3500000.0,
        "difficulty": 4,
        "fact": "A gravity tractor spacecraft could deflect a large asteroid by hovering near it for years, gently pulling it off course with its own gravity.",
    },
    {
        "name": "2031 QP5",
        "size_m": 450.0,
        "speed_kph": 92000.0,
        "comparison": "about the length of five city blocks",
        "distance_km": 5000000.0,
        "difficulty": 5,
        "fact": "The asteroid belt between Mars and Jupiter contains millions of asteroids, but their total mass is only about 4% of the Moon's mass.",
    },
    {
        "name": "Nemesis-7",
        "size_m": 500.0,
        "speed_kph": 105000.0,
        "comparison": "roughly the size of the One World Trade Center tower",
        "distance_km": 8000000.0,
        "difficulty": 5,
        "fact": "The Chicxulub impactor that ended the dinosaurs was about 10 km wide — 20 times larger than this asteroid — and struck with the energy of 10 billion Hiroshima bombs.",
    },
]

# Cache for scoring
_active_asteroids: Dict[str, AsteroidScenario] = {}


def generate_asteroid_scenario(difficulty: int = None, module_level: int = 1) -> AsteroidScenario:
    """Generate an Asteroid Deflection scenario.

    Args:
        difficulty: Target difficulty 1-5. None = random based on module_level.
        module_level: Player's Bridge module level (affects tolerance).

    Returns:
        An AsteroidScenario ready for the frontend to render.
    """
    if difficulty is None:
        difficulty = min(5, max(1, (module_level + 1) // 2))

    candidates = [s for s in _ASTEROID_SCENARIOS if s["difficulty"] == difficulty]
    if not candidates:
        candidates = list(_ASTEROID_SCENARIOS)

    scenario_data = random.choice(candidates)

    # Generate approach and deflection angles
    approach_angle = round(random.uniform(0, 360), 1)

    # Optimal deflection: perpendicular to approach +/- some offset
    base_deflection = (approach_angle + 90.0) % 360.0
    offset = random.uniform(-30, 30) * (difficulty / 5.0)
    optimal = (base_deflection + offset) % 360.0

    # Tolerance: easier difficulty = more forgiving
    # Level also increases tolerance slightly
    base_tolerance = 25.0 - (difficulty * 4.0)  # 21, 17, 13, 9, 5
    level_bonus = min(5.0, (module_level - 1) * 0.5)
    tolerance = max(3.0, base_tolerance + level_bonus)

    time_limit = max(15, 45 - difficulty * 5)

    scenario_id = f"ad_{uuid.uuid4().hex[:12]}"

    scenario = AsteroidScenario(
        scenario_id=scenario_id,
        asteroid_name=scenario_data["name"],
        asteroid_size_meters=scenario_data["size_m"],
        asteroid_speed_kph=scenario_data["speed_kph"],
        size_comparison=scenario_data["comparison"],
        approach_angle=round(approach_angle, 2),
        optimal_deflection_angle=round(optimal, 2),
        deflection_tolerance=round(tolerance, 2),
        distance_km=scenario_data["distance_km"],
        difficulty=difficulty,
        time_limit_seconds=time_limit,
        fun_fact=scenario_data["fact"],
    )

    _active_asteroids[scenario_id] = scenario
    return scenario


def score_deflection(
    scenario_id: str,
    player_angle: float,
    time_taken: float,
    cosmic_buff: float = 0.0,
) -> DeflectionResult:
    """Score an Asteroid Deflection attempt.

    Args:
        scenario_id: The scenario being scored.
        player_angle: The deflection angle the player chose (0-360).
        time_taken: Seconds the player took.
        cosmic_buff: Buff/debuff percentage from cosmic state.

    Returns:
        A DeflectionResult with success status and score.
    """
    scenario = _active_asteroids.get(scenario_id)
    if scenario is None:
        raise ValueError(f"Unknown scenario_id: {scenario_id}")

    # Calculate angular error (handle wraparound)
    diff = abs(player_angle - scenario.optimal_deflection_angle)
    if diff > 180:
        diff = 360 - diff
    angle_error = round(diff, 2)

    success = angle_error <= scenario.deflection_tolerance
    close_call = success and angle_error > (scenario.deflection_tolerance * 0.75)

    # Accuracy: 1.0 at exact, 0.0 at tolerance boundary, clamped
    if scenario.deflection_tolerance > 0:
        accuracy = max(0.0, 1.0 - (angle_error / scenario.deflection_tolerance))
    else:
        accuracy = 1.0 if angle_error == 0 else 0.0

    # Score calculation
    if success:
        base_score = int(100 * accuracy)
        difficulty_bonus = 1.0 + (scenario.difficulty - 1) * 0.3
        speed_ratio = max(0.0, 1.0 - (time_taken / scenario.time_limit_seconds))
        speed_bonus = 1.0 + (speed_ratio * 0.4)
        raw_score = int(base_score * difficulty_bonus * speed_bonus)
    else:
        # Partial score for near-misses
        miss_ratio = max(0.0, 1.0 - (angle_error / 180.0))
        raw_score = int(30 * miss_ratio)

    # Cosmic buff
    buff_mult = 1.0 + (cosmic_buff / 100.0)
    score = max(5, int(raw_score * buff_mult))

    xp = max(3, int(score * 0.5))

    # Clean up
    _active_asteroids.pop(scenario_id, None)

    return DeflectionResult(
        scenario_id=scenario_id,
        asteroid_name=scenario.asteroid_name,
        player_angle=round(player_angle, 2),
        optimal_angle=scenario.optimal_deflection_angle,
        angle_error=angle_error,
        success=success,
        accuracy=round(accuracy, 4),
        score=score,
        xp_earned=xp,
        close_call=close_call,
    )


# ────────────────────────────────────────────────────────────────
# 4. Daily Mission System
# ────────────────────────────────────────────────────────────────

@dataclass
class DailyMission:
    """A daily mission shaped by the player's cosmic state."""
    mission_id: str
    date: str
    mission_type: str
    title: str
    description: str
    module_id: str
    cosmic_trigger: str
    mini_game_type: str           # "star_pattern", "repair_puzzle", "asteroid_deflection"
    difficulty: int
    rewards: dict                 # {xp, resources}


# Cosmic state -> mission mapping (GDD S5.2)
_COSMIC_MISSION_MAP: List[dict] = [
    {
        "condition": lambda ms: ms.get("Observatory") == "POWER",
        "trigger": "POWER in Observatory",
        "type": "research_sprint",
        "title": "Deep Sky Research Sprint",
        "desc": "The Observatory hums with cosmic energy. The stars are aligned for discovery — identify as many constellation patterns as you can.",
        "module": "observatory",
        "game": "star_pattern",
    },
    {
        "condition": lambda ms: ms.get("Workshop") == "POWER",
        "trigger": "POWER in Workshop",
        "type": "build_rush",
        "title": "System Optimization Rush",
        "desc": "The Workshop is supercharged today. Route station systems with maximum efficiency while the cosmic winds are favorable.",
        "module": "workshop",
        "game": "repair_puzzle",
    },
    {
        "condition": lambda ms: ms.get("Quarters") == "TROUBLE",
        "trigger": "TROUBLE in Quarters",
        "type": "emergency_repair",
        "title": "Emergency Life Support Repair",
        "desc": "Cosmic interference has disrupted life support systems. Reroute critical pathways before the crew is affected.",
        "module": "quarters",
        "game": "repair_puzzle",
    },
    {
        "condition": lambda ms: ms.get("Bridge") == "TROUBLE",
        "trigger": "TROUBLE in Bridge",
        "type": "hard_choices",
        "title": "Incoming Threat Assessment",
        "desc": "The Bridge sensors are strained under cosmic pressure. An asteroid approaches — calculate the deflection vector before it's too late.",
        "module": "bridge",
        "game": "asteroid_deflection",
    },
    {
        "condition": lambda ms: ms.get("Shrine") == "PRESSURE",
        "trigger": "PRESSURE in Shrine",
        "type": "cryptic_vision",
        "title": "Cryptic Star Vision",
        "desc": "The Shrine pulses with mysterious cosmic tension. Ancient star patterns appear in your mind's eye — trace them before they fade.",
        "module": "shrine",
        "game": "star_pattern",
    },
    {
        "condition": lambda ms: ms.get("Bridge") == "POWER",
        "trigger": "POWER in Bridge",
        "type": "precision_strike",
        "title": "Precision Deflection Training",
        "desc": "With the Bridge systems boosted by cosmic power, run advanced asteroid deflection simulations.",
        "module": "bridge",
        "game": "asteroid_deflection",
    },
    {
        "condition": lambda ms: ms.get("Commons") == "TROUBLE",
        "trigger": "TROUBLE in Commons",
        "type": "resource_crisis",
        "title": "Supply Line Repair",
        "desc": "Trade routes are disrupted. Repair the station's distribution networks to keep resources flowing.",
        "module": "commons",
        "game": "repair_puzzle",
    },
    {
        "condition": lambda ms: ms.get("Observatory") == "PRESSURE",
        "trigger": "PRESSURE in Observatory",
        "type": "star_pressure",
        "title": "Constellation Under Pressure",
        "desc": "The Observatory instruments are fluctuating. Quickly identify the star patterns before calibration drifts.",
        "module": "observatory",
        "game": "star_pattern",
    },
    {
        "condition": lambda ms: ms.get("Greenhouse") == "POWER",
        "trigger": "POWER in Greenhouse",
        "type": "growth_sprint",
        "title": "Stellar Growth Patterns",
        "desc": "The Greenhouse resonates with cosmic vitality. Chart the constellations that guide today's growth cycles.",
        "module": "greenhouse",
        "game": "star_pattern",
    },
    {
        "condition": lambda ms: ms.get("Workshop") == "TROUBLE",
        "trigger": "TROUBLE in Workshop",
        "type": "workshop_emergency",
        "title": "Workshop Systems Failure",
        "desc": "Multiple workshop subsystems have gone offline. Route emergency power to restore production.",
        "module": "workshop",
        "game": "repair_puzzle",
    },
]

# Default missions when no cosmic state matches
_DEFAULT_MISSIONS: List[dict] = [
    {
        "type": "routine_observation",
        "title": "Routine Star Survey",
        "desc": "A calm day at the station. Use the downtime to practice star pattern recognition.",
        "module": "observatory",
        "game": "star_pattern",
        "trigger": "NEUTRAL — routine operations",
    },
    {
        "type": "routine_maintenance",
        "title": "Scheduled Maintenance Check",
        "desc": "No cosmic disruptions today. Run standard maintenance drills on station systems.",
        "module": "quarters",
        "game": "repair_puzzle",
        "trigger": "NEUTRAL — routine operations",
    },
    {
        "type": "deflection_drill",
        "title": "Asteroid Deflection Drill",
        "desc": "Clear skies for training. Run simulated asteroid approach scenarios from the Bridge.",
        "module": "bridge",
        "game": "asteroid_deflection",
        "trigger": "NEUTRAL — routine operations",
    },
]


def generate_daily_mission(
    module_statuses: list,
    date_str: str = None,
) -> DailyMission:
    """Generate today's daily mission based on cosmic state.

    Args:
        module_statuses: List of dicts with {module_name, status} or
                         ModuleStatus objects from the transit engine.
        date_str: Optional ISO date string. Defaults to today.

    Returns:
        A DailyMission tied to the current cosmic state.
    """
    if date_str is None:
        date_str = date.today().isoformat()

    # Build status lookup: module_name -> status string
    status_lookup: Dict[str, str] = {}
    for ms in module_statuses:
        if isinstance(ms, dict):
            name = ms.get("module_name", "")
            status = ms.get("status", "NEUTRAL")
        else:
            # Assume object with .module_name and .status
            name = getattr(ms, "module_name", "")
            status = getattr(ms, "status", "NEUTRAL")
        status_lookup[name] = status

    # Find first matching cosmic mission
    # Use date as seed for deterministic daily selection
    date_seed = int(hashlib.md5(date_str.encode()).hexdigest()[:8], 16)

    matched = None
    for mapping in _COSMIC_MISSION_MAP:
        if mapping["condition"](status_lookup):
            matched = mapping
            break

    if matched is None:
        # Use default mission, rotated by date
        matched = _DEFAULT_MISSIONS[date_seed % len(_DEFAULT_MISSIONS)]

    # Difficulty: base from cosmic state, varies by date
    base_diff = 2
    active_statuses = [s for s in status_lookup.values() if s != "NEUTRAL"]
    if any(s == "TROUBLE" for s in active_statuses):
        base_diff = 3
    if any(s == "PRESSURE" for s in active_statuses):
        base_diff = max(base_diff, 3)

    # Add slight date-based variance
    difficulty = max(1, min(5, base_diff + (date_seed % 3) - 1))

    # Rewards scale with difficulty
    base_xp = 50 + difficulty * 25
    rewards = {
        "xp": base_xp,
        "energy": 10 * difficulty,
        "stardust": 2 * difficulty,
    }

    mission_id = f"dm_{date_str.replace('-', '')}"

    return DailyMission(
        mission_id=mission_id,
        date=date_str,
        mission_type=matched["type"],
        title=matched["title"],
        description=matched["desc"],
        module_id=matched["module"],
        cosmic_trigger=matched["trigger"],
        mini_game_type=matched["game"],
        difficulty=difficulty,
        rewards=rewards,
    )


def daily_mission_to_dict(mission: DailyMission) -> dict:
    """Serialize a DailyMission to a JSON-safe dictionary."""
    return {
        "mission_id": mission.mission_id,
        "date": mission.date,
        "mission_type": mission.mission_type,
        "title": mission.title,
        "description": mission.description,
        "module_id": mission.module_id,
        "cosmic_trigger": mission.cosmic_trigger,
        "mini_game_type": mission.mini_game_type,
        "difficulty": mission.difficulty,
        "rewards": mission.rewards,
    }

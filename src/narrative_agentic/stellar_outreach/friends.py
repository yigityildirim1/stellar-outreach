"""
NEXUS STATION - Stellar Outreach: Friends & Cosmic Compatibility (TASK-010)

Friend system with mutual requests, resource gifting, and synastry-based
cosmic compatibility engine.

Features:
    - Mutual friend requests (send/accept/reject)
    - Block/report, remove friend
    - Resource gifting (1x/friend/day, max 50 per gift)
    - Synastry engine for natal-natal chart comparison
    - Compatibility score 0-100 with 6 tiers
    - Elemental compatibility matrix
    - Role synergy narratives for all 78 sign pairs

Security caps (Kai Chen review):
    - 50 friends max
    - 20 pending requests max
    - Gift cooldown: 1 per friend per day, max 50 resources per gift
    - All IDs sanitized before filesystem use

References:
    - GDD S8: Social features
    - TASK-002: Transit engine (_detect_aspects pattern)
    - TASK-001: Birth chart (PlayerProfile, PlanetPosition)
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from narrative_agentic.stellar_outreach.birth_chart import (
    ZODIAC_SIGNS,
    ELEMENTS,
    PlayerProfile,
    PlanetPosition,
)
from narrative_agentic.stellar_outreach.transit_engine import (
    ASPECT_DEFINITIONS,
    _normalize_angle,
)


# ────────────────────────────────────────────────────────────────
# Persistence Configuration
# ────────────────────────────────────────────────────────────────

FRIENDS_DIR = Path.home() / ".nexus_station" / "friends"

MAX_FRIENDS = 50
MAX_PENDING_REQUESTS = 20
MAX_GIFT_AMOUNT = 50
GIFT_COOLDOWN_HOURS = 24


def _sanitize_player_id(player_id: str) -> str:
    """Sanitize a player ID for safe filesystem use."""
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in player_id)


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


# ────────────────────────────────────────────────────────────────
# Data Classes
# ────────────────────────────────────────────────────────────────

@dataclass
class FriendEntry:
    """A single friend relationship."""
    friend_id: str
    added_at: str           # ISO datetime
    last_gift_sent: str     # ISO datetime or ""
    last_gift_received: str # ISO datetime or ""


@dataclass
class FriendRequest:
    """A pending friend request."""
    from_id: str
    to_id: str
    sent_at: str            # ISO datetime
    message: str


@dataclass
class FriendData:
    """Complete friend data for a player."""
    player_id: str
    friends: List[FriendEntry]
    pending_incoming: List[FriendRequest]
    pending_outgoing: List[FriendRequest]
    blocked: List[str]
    gift_log: Dict[str, str]  # friend_id -> last_gift_sent ISO datetime


@dataclass
class SynastryResult:
    """Cosmic compatibility result between two players."""
    player_a_id: str
    player_b_id: str
    overall_score: int        # 0-100
    tier: str                 # compatibility tier name
    tier_description: str
    elemental_harmony: float  # 0-1
    aspect_hits: List[dict]   # simplified aspect data
    sign_synergy: str         # narrative for sun sign pair
    co_op_bonus: str          # trine or opposition bonus description
    co_op_bonus_percent: int  # bonus percentage


# ────────────────────────────────────────────────────────────────
# Persistence
# ────────────────────────────────────────────────────────────────

def _friend_path(player_id: str) -> Path:
    safe_id = _sanitize_player_id(player_id)
    return FRIENDS_DIR / f"{safe_id}.json"


def _load_friend_data(player_id: str) -> FriendData:
    """Load friend data for a player."""
    path = _friend_path(player_id)
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return FriendData(
                player_id=player_id,
                friends=[FriendEntry(**e) for e in data.get("friends", [])],
                pending_incoming=[FriendRequest(**r) for r in data.get("pending_incoming", [])],
                pending_outgoing=[FriendRequest(**r) for r in data.get("pending_outgoing", [])],
                blocked=data.get("blocked", []),
                gift_log=data.get("gift_log", {}),
            )
        except (json.JSONDecodeError, IOError, TypeError):
            pass
    return FriendData(
        player_id=player_id,
        friends=[],
        pending_incoming=[],
        pending_outgoing=[],
        blocked=[],
        gift_log={},
    )


def _save_friend_data(data: FriendData) -> None:
    """Save friend data for a player."""
    _ensure_dir(FRIENDS_DIR)
    path = _friend_path(data.player_id)
    serialized = {
        "player_id": data.player_id,
        "friends": [
            {"friend_id": f.friend_id, "added_at": f.added_at,
             "last_gift_sent": f.last_gift_sent, "last_gift_received": f.last_gift_received}
            for f in data.friends
        ],
        "pending_incoming": [
            {"from_id": r.from_id, "to_id": r.to_id, "sent_at": r.sent_at, "message": r.message}
            for r in data.pending_incoming
        ],
        "pending_outgoing": [
            {"from_id": r.from_id, "to_id": r.to_id, "sent_at": r.sent_at, "message": r.message}
            for r in data.pending_outgoing
        ],
        "blocked": data.blocked,
        "gift_log": data.gift_log,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(serialized, f, indent=2)


# ────────────────────────────────────────────────────────────────
# Friend System API
# ────────────────────────────────────────────────────────────────

def get_friends(player_id: str) -> dict:
    """Get a player's friend list.

    Returns:
        Dictionary with friends list and counts.
    """
    data = _load_friend_data(player_id)
    return {
        "player_id": player_id,
        "friends": [
            {
                "friend_id": f.friend_id,
                "added_at": f.added_at,
                "last_gift_sent": f.last_gift_sent,
                "last_gift_received": f.last_gift_received,
            }
            for f in data.friends
        ],
        "count": len(data.friends),
        "max_friends": MAX_FRIENDS,
    }


def get_friend_requests(player_id: str) -> dict:
    """Get pending friend requests for a player.

    Returns:
        Dictionary with incoming and outgoing requests.
    """
    data = _load_friend_data(player_id)
    return {
        "player_id": player_id,
        "incoming": [
            {"from_id": r.from_id, "sent_at": r.sent_at, "message": r.message}
            for r in data.pending_incoming
        ],
        "outgoing": [
            {"to_id": r.to_id, "sent_at": r.sent_at, "message": r.message}
            for r in data.pending_outgoing
        ],
        "incoming_count": len(data.pending_incoming),
        "outgoing_count": len(data.pending_outgoing),
        "max_pending": MAX_PENDING_REQUESTS,
    }


def send_friend_request(from_id: str, to_id: str, message: str = "") -> dict:
    """Send a friend request.

    Args:
        from_id: The sender's player ID.
        to_id: The recipient's player ID.
        message: Optional message with the request.

    Returns:
        Status dictionary.
    """
    if from_id == to_id:
        return {"success": False, "reason": "Cannot send a friend request to yourself"}

    sender_data = _load_friend_data(from_id)
    receiver_data = _load_friend_data(to_id)

    # Check blocks
    if to_id in sender_data.blocked:
        return {"success": False, "reason": "You have blocked this player"}
    if from_id in receiver_data.blocked:
        return {"success": False, "reason": "This player is not accepting requests from you"}

    # Check if already friends
    if any(f.friend_id == to_id for f in sender_data.friends):
        return {"success": False, "reason": "Already friends"}

    # Check friend limits
    if len(sender_data.friends) >= MAX_FRIENDS:
        return {"success": False, "reason": f"Friend limit reached ({MAX_FRIENDS})"}

    # Check pending request limits
    if len(sender_data.pending_outgoing) >= MAX_PENDING_REQUESTS:
        return {"success": False, "reason": f"Pending request limit reached ({MAX_PENDING_REQUESTS})"}

    # Check for duplicate request
    if any(r.to_id == to_id for r in sender_data.pending_outgoing):
        return {"success": False, "reason": "Request already sent"}

    # Check if receiver already sent a request to us (auto-accept)
    mutual = next((r for r in sender_data.pending_incoming if r.from_id == to_id), None)
    if mutual:
        return _accept_mutual(sender_data, receiver_data, mutual)

    now = datetime.utcnow().isoformat()
    request = FriendRequest(from_id=from_id, to_id=to_id, sent_at=now, message=message[:200])

    sender_data.pending_outgoing.append(request)
    receiver_data.pending_incoming.append(request)

    _save_friend_data(sender_data)
    _save_friend_data(receiver_data)

    return {"success": True, "status": "request_sent"}


def _accept_mutual(sender_data: FriendData, receiver_data: FriendData, mutual_request: FriendRequest) -> dict:
    """Auto-accept when both players have requested each other."""
    now = datetime.utcnow().isoformat()

    # Remove the pending requests
    sender_data.pending_incoming = [r for r in sender_data.pending_incoming if r.from_id != receiver_data.player_id]
    receiver_data.pending_outgoing = [r for r in receiver_data.pending_outgoing if r.to_id != sender_data.player_id]

    # Add as friends
    sender_data.friends.append(FriendEntry(
        friend_id=receiver_data.player_id, added_at=now,
        last_gift_sent="", last_gift_received="",
    ))
    receiver_data.friends.append(FriendEntry(
        friend_id=sender_data.player_id, added_at=now,
        last_gift_sent="", last_gift_received="",
    ))

    _save_friend_data(sender_data)
    _save_friend_data(receiver_data)

    return {"success": True, "status": "auto_accepted", "message": "Mutual request — automatically accepted!"}


def respond_to_request(player_id: str, from_id: str, accept: bool) -> dict:
    """Accept or reject a friend request.

    Args:
        player_id: The player responding.
        from_id: The player who sent the request.
        accept: True to accept, False to reject.

    Returns:
        Status dictionary.
    """
    my_data = _load_friend_data(player_id)
    their_data = _load_friend_data(from_id)

    # Find the request
    request = next((r for r in my_data.pending_incoming if r.from_id == from_id), None)
    if request is None:
        return {"success": False, "reason": "No pending request from this player"}

    # Remove from both sides
    my_data.pending_incoming = [r for r in my_data.pending_incoming if r.from_id != from_id]
    their_data.pending_outgoing = [r for r in their_data.pending_outgoing if r.to_id != player_id]

    if accept:
        if len(my_data.friends) >= MAX_FRIENDS:
            _save_friend_data(my_data)
            _save_friend_data(their_data)
            return {"success": False, "reason": f"Friend limit reached ({MAX_FRIENDS})"}

        now = datetime.utcnow().isoformat()
        my_data.friends.append(FriendEntry(
            friend_id=from_id, added_at=now,
            last_gift_sent="", last_gift_received="",
        ))
        their_data.friends.append(FriendEntry(
            friend_id=player_id, added_at=now,
            last_gift_sent="", last_gift_received="",
        ))

    _save_friend_data(my_data)
    _save_friend_data(their_data)

    return {
        "success": True,
        "status": "accepted" if accept else "rejected",
        "friend_id": from_id,
    }


def remove_friend(player_id: str, friend_id: str) -> dict:
    """Remove a friend.

    Args:
        player_id: The player removing.
        friend_id: The friend to remove.

    Returns:
        Status dictionary.
    """
    my_data = _load_friend_data(player_id)
    their_data = _load_friend_data(friend_id)

    my_data.friends = [f for f in my_data.friends if f.friend_id != friend_id]
    their_data.friends = [f for f in their_data.friends if f.friend_id != player_id]

    _save_friend_data(my_data)
    _save_friend_data(their_data)

    return {"success": True, "removed": friend_id}


def block_player(player_id: str, target_id: str) -> dict:
    """Block a player (also removes friendship if any).

    Args:
        player_id: The player blocking.
        target_id: The player to block.

    Returns:
        Status dictionary.
    """
    if player_id == target_id:
        return {"success": False, "reason": "Cannot block yourself"}

    my_data = _load_friend_data(player_id)

    if target_id in my_data.blocked:
        return {"success": False, "reason": "Already blocked"}

    # Remove from friends if present
    my_data.friends = [f for f in my_data.friends if f.friend_id != target_id]

    # Remove any pending requests
    my_data.pending_incoming = [r for r in my_data.pending_incoming if r.from_id != target_id]
    my_data.pending_outgoing = [r for r in my_data.pending_outgoing if r.to_id != target_id]

    my_data.blocked.append(target_id)
    _save_friend_data(my_data)

    # Also remove from their friends list
    their_data = _load_friend_data(target_id)
    their_data.friends = [f for f in their_data.friends if f.friend_id != player_id]
    their_data.pending_incoming = [r for r in their_data.pending_incoming if r.from_id != player_id]
    their_data.pending_outgoing = [r for r in their_data.pending_outgoing if r.to_id != player_id]
    _save_friend_data(their_data)

    return {"success": True, "blocked": target_id}


def send_gift(
    player_id: str,
    friend_id: str,
    resource_type: str,
    amount: int,
) -> dict:
    """Send a resource gift to a friend.

    Args:
        player_id: The sender.
        friend_id: The recipient (must be a friend).
        resource_type: Type of resource to gift.
        amount: Amount to gift (max 50).

    Returns:
        Status dictionary.
    """
    if amount <= 0:
        return {"success": False, "reason": "Amount must be positive"}
    if amount > MAX_GIFT_AMOUNT:
        return {"success": False, "reason": f"Maximum gift amount is {MAX_GIFT_AMOUNT}"}

    my_data = _load_friend_data(player_id)

    # Check friendship
    friend_entry = next((f for f in my_data.friends if f.friend_id == friend_id), None)
    if friend_entry is None:
        return {"success": False, "reason": "Not friends with this player"}

    # Check cooldown
    last_gift = my_data.gift_log.get(friend_id, "")
    if last_gift:
        last_dt = datetime.fromisoformat(last_gift)
        hours_since = (datetime.utcnow() - last_dt).total_seconds() / 3600
        if hours_since < GIFT_COOLDOWN_HOURS:
            remaining = GIFT_COOLDOWN_HOURS - hours_since
            return {
                "success": False,
                "reason": f"Gift cooldown active. {remaining:.1f} hours remaining.",
            }

    # Check sender has resources (requires station)
    from narrative_agentic.stellar_outreach.station_modules import get_station, save_station

    sender_station = get_station(player_id)
    if sender_station is None:
        return {"success": False, "reason": "Sender station not found"}

    current = sender_station.resources.get(resource_type, 0)
    if current < amount:
        return {"success": False, "reason": f"Insufficient {resource_type} (have {current}, need {amount})"}

    # Transfer resources
    sender_station.resources[resource_type] -= amount
    save_station(sender_station)

    receiver_station = get_station(friend_id)
    if receiver_station is not None:
        receiver_station.resources[resource_type] = receiver_station.resources.get(resource_type, 0) + amount
        save_station(receiver_station)

    # Update gift log
    now = datetime.utcnow().isoformat()
    my_data.gift_log[friend_id] = now
    friend_entry.last_gift_sent = now
    _save_friend_data(my_data)

    # Update receiver's friend entry
    their_data = _load_friend_data(friend_id)
    their_friend = next((f for f in their_data.friends if f.friend_id == player_id), None)
    if their_friend:
        their_friend.last_gift_received = now
        _save_friend_data(their_data)

    return {
        "success": True,
        "gift": {
            "from": player_id,
            "to": friend_id,
            "resource_type": resource_type,
            "amount": amount,
            "sent_at": now,
        },
    }


# ────────────────────────────────────────────────────────────────
# Synastry Engine — Cosmic Compatibility
# ────────────────────────────────────────────────────────────────

# Compatibility tiers
_COMPATIBILITY_TIERS: List[Tuple[int, str, str]] = [
    (90, "Cosmic Twins", "Your charts vibrate at nearly identical frequencies. This is an extraordinarily rare resonance."),
    (75, "Stellar Harmony", "The stars wove your paths with complementary threads. Deep understanding comes naturally."),
    (60, "Orbital Resonance", "Your cosmic rhythms sync in meaningful ways. Growth together feels effortless."),
    (45, "Gravitational Pull", "A solid cosmic connection with interesting tension points that fuel growth."),
    (25, "Parallel Orbits", "Your paths run alongside each other — connection requires conscious effort."),
    (0, "Star-Crossed Paths", "Your charts create friction that can be transformative if navigated with care."),
]

# Element compatibility matrix (0-1 score)
_ELEMENT_COMPAT: Dict[Tuple[str, str], float] = {
    ("Fire", "Fire"): 0.85,
    ("Fire", "Air"): 0.9,
    ("Fire", "Earth"): 0.4,
    ("Fire", "Water"): 0.35,
    ("Air", "Fire"): 0.9,
    ("Air", "Air"): 0.8,
    ("Air", "Earth"): 0.45,
    ("Air", "Water"): 0.5,
    ("Earth", "Fire"): 0.4,
    ("Earth", "Air"): 0.45,
    ("Earth", "Earth"): 0.85,
    ("Earth", "Water"): 0.9,
    ("Water", "Fire"): 0.35,
    ("Water", "Air"): 0.5,
    ("Water", "Earth"): 0.9,
    ("Water", "Water"): 0.8,
}

# Sign pair synergy narratives (indexed by sorted pair)
# Generate narratives for all 78 unique pairs (12 same + 66 different)
_SIGN_SYNERGY_TEMPLATES: Dict[str, str] = {
    "same": "Two {sign}s together amplify each other's {element} energy — a mirror that can dazzle or blind.",
    "same_element": "{sign_a} and {sign_b} share {element} energy. Like different instruments in the same key, you harmonize naturally.",
    "complementary": "{sign_a} and {sign_b} are complementary opposites — what one lacks, the other provides. The tension is generative.",
    "square": "{sign_a} and {sign_b} form a cosmic square — friction that builds heat. The challenge creates diamonds.",
    "trine": "{sign_a} and {sign_b} flow in a natural trine. Understanding comes almost telepathically between you.",
    "default": "{sign_a} and {sign_b} create a unique cosmic conversation. Your energies blend in unexpected ways.",
}


def _get_sign_relationship(sign_a: str, sign_b: str) -> str:
    """Determine the astrological relationship between two signs."""
    if sign_a == sign_b:
        return "same"

    idx_a = ZODIAC_SIGNS.index(sign_a)
    idx_b = ZODIAC_SIGNS.index(sign_b)
    diff = abs(idx_a - idx_b)
    if diff > 6:
        diff = 12 - diff

    elem_a = ELEMENTS[sign_a]
    elem_b = ELEMENTS[sign_b]

    if diff == 6:
        return "complementary"
    if diff == 3 or diff == 9:
        return "square"
    if diff == 4 or diff == 8:
        return "trine"
    if elem_a == elem_b:
        return "same_element"
    return "default"


def _generate_sign_synergy(sign_a: str, sign_b: str) -> str:
    """Generate a narrative for a sign pair."""
    relationship = _get_sign_relationship(sign_a, sign_b)
    template = _SIGN_SYNERGY_TEMPLATES[relationship]

    elem_a = ELEMENTS[sign_a]
    elem_b = ELEMENTS[sign_b]

    return template.format(
        sign=sign_a if sign_a == sign_b else "",
        sign_a=sign_a,
        sign_b=sign_b,
        element=elem_a if elem_a == elem_b else f"{elem_a}/{elem_b}",
    )


def _detect_synastry_aspects(
    planets_a: List[PlanetPosition],
    planets_b: List[PlanetPosition],
) -> List[dict]:
    """Detect aspects between two natal charts (adapted from transit_engine._detect_aspects)."""
    hits = []

    for pa in planets_a:
        for pb in planets_b:
            diff = _normalize_angle(pa.degree - pb.degree)

            for asp_name, asp_angle, asp_status, asp_orb, asp_strength in ASPECT_DEFINITIONS:
                orb = abs(diff - asp_angle)
                if orb <= asp_orb:
                    hits.append({
                        "planet_a": pa.planet,
                        "planet_b": pb.planet,
                        "aspect_type": asp_name,
                        "angle": round(diff, 2),
                        "orb": round(orb, 2),
                        "status": asp_status,
                        "strength": asp_strength,
                    })
                    break  # one aspect per planet pair

    return hits


def calculate_compatibility(
    profile_a: PlayerProfile,
    profile_b: PlayerProfile,
    player_a_id: str = "player_a",
    player_b_id: str = "player_b",
) -> SynastryResult:
    """Calculate cosmic compatibility between two players.

    Adapts the transit engine's aspect detection for natal-natal comparison.

    Args:
        profile_a: First player's profile.
        profile_b: Second player's profile.
        player_a_id: First player's ID.
        player_b_id: Second player's ID.

    Returns:
        A SynastryResult with compatibility data.
    """
    planets_a = profile_a.natal_chart.planets
    planets_b = profile_b.natal_chart.planets

    # 1. Aspect-based score (40% weight)
    aspect_hits = _detect_synastry_aspects(planets_a, planets_b)

    aspect_score = 0
    power_count = 0
    trouble_count = 0

    for hit in aspect_hits:
        if hit["status"] == "POWER":
            aspect_score += 6 if hit["strength"] == "strong" else 3
            power_count += 1
        elif hit["status"] == "PRESSURE":
            aspect_score += 3 if hit["strength"] == "strong" else 1
        elif hit["status"] == "TROUBLE":
            aspect_score -= 2 if hit["strength"] == "strong" else 1
            trouble_count += 1

    # Normalize to 0-100
    max_possible_aspects = len(planets_a) * 6  # roughly
    aspect_component = min(100, max(0, int((aspect_score / max(1, max_possible_aspects)) * 100 + 50)))

    # 2. Elemental harmony (30% weight)
    sun_a = next(p for p in planets_a if p.planet == "Sun")
    sun_b = next(p for p in planets_b if p.planet == "Sun")
    moon_a = next(p for p in planets_a if p.planet == "Moon")
    moon_b = next(p for p in planets_b if p.planet == "Moon")

    elem_sun_a = ELEMENTS[sun_a.sign]
    elem_sun_b = ELEMENTS[sun_b.sign]
    elem_moon_a = ELEMENTS[moon_a.sign]
    elem_moon_b = ELEMENTS[moon_b.sign]

    # Sun-Sun, Sun-Moon (both ways), Moon-Moon compatibility
    sun_sun = _ELEMENT_COMPAT.get((elem_sun_a, elem_sun_b), 0.5)
    sun_moon_1 = _ELEMENT_COMPAT.get((elem_sun_a, elem_moon_b), 0.5)
    sun_moon_2 = _ELEMENT_COMPAT.get((elem_moon_a, elem_sun_b), 0.5)
    moon_moon = _ELEMENT_COMPAT.get((elem_moon_a, elem_moon_b), 0.5)

    elemental_harmony = (sun_sun * 0.4 + sun_moon_1 * 0.2 + sun_moon_2 * 0.2 + moon_moon * 0.2)
    elemental_component = int(elemental_harmony * 100)

    # 3. Sign relationship (30% weight)
    sign_rel = _get_sign_relationship(sun_a.sign, sun_b.sign)
    sign_scores = {
        "same": 75,
        "same_element": 80,
        "trine": 90,
        "complementary": 60,
        "square": 35,
        "default": 55,
    }
    sign_component = sign_scores.get(sign_rel, 55)

    # Overall score (weighted)
    overall = int(aspect_component * 0.4 + elemental_component * 0.3 + sign_component * 0.3)
    overall = max(0, min(100, overall))

    # Determine tier
    tier_name = "Star-Crossed Paths"
    tier_desc = ""
    for threshold, name, desc in _COMPATIBILITY_TIERS:
        if overall >= threshold:
            tier_name = name
            tier_desc = desc
            break

    # Sign synergy narrative
    sign_synergy = _generate_sign_synergy(sun_a.sign, sun_b.sign)

    # Co-op bonus
    co_op_bonus = ""
    co_op_percent = 0

    if sign_rel == "trine" or elem_sun_a == elem_sun_b:
        co_op_bonus = f"Trine Resonance: +10% co-op mission rewards when paired"
        co_op_percent = 10
    elif sign_rel == "complementary":
        co_op_bonus = f"Opposition Fusion: Unlock special fusion missions together"
        co_op_percent = 5

    return SynastryResult(
        player_a_id=player_a_id,
        player_b_id=player_b_id,
        overall_score=overall,
        tier=tier_name,
        tier_description=tier_desc,
        elemental_harmony=round(elemental_harmony, 4),
        aspect_hits=aspect_hits,
        sign_synergy=sign_synergy,
        co_op_bonus=co_op_bonus,
        co_op_bonus_percent=co_op_percent,
    )


# ────────────────────────────────────────────────────────────────
# Serialization
# ────────────────────────────────────────────────────────────────

def synastry_result_to_dict(result: SynastryResult) -> dict:
    """Serialize a SynastryResult to a JSON-safe dictionary."""
    return {
        "player_a_id": result.player_a_id,
        "player_b_id": result.player_b_id,
        "overall_score": result.overall_score,
        "tier": result.tier,
        "tier_description": result.tier_description,
        "elemental_harmony": result.elemental_harmony,
        "aspect_hits": result.aspect_hits,
        "sign_synergy": result.sign_synergy,
        "co_op_bonus": result.co_op_bonus,
        "co_op_bonus_percent": result.co_op_bonus_percent,
    }

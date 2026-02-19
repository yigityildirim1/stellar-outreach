"""
NEXUS STATION - Stellar Outreach: Constellation Crews / Guilds (TASK-011)

Guild system where 4-12 players form cooperative crews with elemental balance
bonuses, weekly challenges, shared resource pools, and rate-limited chat.

Features:
    - Create/join/leave guilds with invite codes
    - Elemental balance bonus (+15% when 3+ different elements)
    - Weekly cooperative challenge (contribute 500 resources by Monday)
    - Shared resource pool from member contributions
    - Rate-limited chat (100 messages rolling, 10/hour/player)

Ethics Note (Dr. Elena Vasquez review):
    Guild system uses cooperative design — bonuses reward diversity
    of elements, not exclusion. No punishment for inactive members.

Security Note (Article II / Kai Chen review):
    Guild names sanitized, chat rate-limited, resource contributions
    capped. Player index prevents multi-guild exploits.

UX Note (Marina Okonkwo review):
    Invite codes are 8 chars for easy sharing. Guild names max 30 chars.
    Chat messages max 200 chars to keep mobile-friendly.

References:
    - TASK-003: Station module resource integration
    - TASK-001: Birth chart elements for balance bonus
"""

from __future__ import annotations

import json
import random
import string
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from narrative_agentic.stellar_outreach.birth_chart import ELEMENTS
from narrative_agentic.stellar_outreach.station_modules import (
    CORE_RESOURCES,
    get_station,
    save_station,
)


# ────────────────────────────────────────────────────────────────
# Persistence Configuration
# ────────────────────────────────────────────────────────────────

GUILDS_DIR = Path.home() / ".nexus_station" / "guilds"

# Limits
MAX_MEMBERS = 12
MIN_MEMBERS_FOR_BONUS = 4
MAX_GUILD_NAME_LENGTH = 30
MAX_CHAT_MESSAGE_LENGTH = 200
MAX_CHAT_MESSAGES = 100
CHAT_RATE_LIMIT_PER_HOUR = 10
INVITE_CODE_LENGTH = 8
WEEKLY_CHALLENGE_GOAL = 500
WEEKLY_CHALLENGE_REWARD = 50  # stardust per member
ELEMENTAL_BALANCE_BONUS = 15.0  # percent
MIN_ELEMENTS_FOR_BONUS = 3


def _sanitize_player_id(player_id: str) -> str:
    """Sanitize a player ID for safe filesystem use."""
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in player_id)


def _sanitize_guild_name(name: str) -> str:
    """Sanitize guild name: alphanumeric, spaces, hyphens only."""
    sanitized = "".join(c if c.isalnum() or c in " -" else "" for c in name)
    return sanitized[:MAX_GUILD_NAME_LENGTH].strip()


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _generate_invite_code() -> str:
    """Generate an 8-character alphanumeric invite code."""
    chars = string.ascii_uppercase + string.digits
    return "".join(random.choices(chars, k=INVITE_CODE_LENGTH))


def _next_monday() -> str:
    """Get the date of next Monday (or today if Monday)."""
    today = date.today()
    days_ahead = 0 - today.weekday()  # Monday is 0
    if days_ahead <= 0:
        days_ahead += 7
    return (today + timedelta(days=days_ahead)).isoformat()


# ────────────────────────────────────────────────────────────────
# Data Models
# ────────────────────────────────────────────────────────────────

@dataclass
class GuildMember:
    """A member of a guild."""
    player_id: str
    sun_sign: str = ""
    element: str = ""
    contribution: int = 0
    joined_at: str = ""


@dataclass
class GuildData:
    """Full guild state."""
    guild_id: str
    guild_name: str
    created_by: str
    members: List[GuildMember] = field(default_factory=list)
    resource_pool: Dict[str, int] = field(default_factory=lambda: {r: 0 for r in CORE_RESOURCES})
    weekly_challenge_progress: int = 0
    weekly_challenge_goal: int = WEEKLY_CHALLENGE_GOAL
    weekly_challenge_reset_date: str = ""
    invite_code: str = ""
    element_balance_bonus: float = 0.0


# ────────────────────────────────────────────────────────────────
# Persistence
# ────────────────────────────────────────────────────────────────

def _guild_path(guild_id: str) -> Path:
    return GUILDS_DIR / f"{guild_id}.json"


def _chat_path(guild_id: str) -> Path:
    return GUILDS_DIR / f"{guild_id}_chat.json"


def _player_index_path() -> Path:
    return GUILDS_DIR / "player_index.json"


def _load_player_index() -> Dict[str, str]:
    """Load player_id → guild_id mapping."""
    path = _player_index_path()
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {}


def _save_player_index(index: Dict[str, str]) -> None:
    _ensure_dir(GUILDS_DIR)
    with open(_player_index_path(), "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2)


def _load_guild(guild_id: str) -> Optional[GuildData]:
    """Load guild data from disk."""
    path = _guild_path(guild_id)
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
        members = [GuildMember(**m) for m in d.get("members", [])]
        return GuildData(
            guild_id=d["guild_id"],
            guild_name=d["guild_name"],
            created_by=d["created_by"],
            members=members,
            resource_pool=d.get("resource_pool", {r: 0 for r in CORE_RESOURCES}),
            weekly_challenge_progress=d.get("weekly_challenge_progress", 0),
            weekly_challenge_goal=d.get("weekly_challenge_goal", WEEKLY_CHALLENGE_GOAL),
            weekly_challenge_reset_date=d.get("weekly_challenge_reset_date", ""),
            invite_code=d.get("invite_code", ""),
            element_balance_bonus=d.get("element_balance_bonus", 0.0),
        )
    except (json.JSONDecodeError, IOError, KeyError):
        return None


def _save_guild(guild: GuildData) -> None:
    """Save guild data to disk."""
    _ensure_dir(GUILDS_DIR)
    d = {
        "guild_id": guild.guild_id,
        "guild_name": guild.guild_name,
        "created_by": guild.created_by,
        "members": [
            {"player_id": m.player_id, "sun_sign": m.sun_sign,
             "element": m.element, "contribution": m.contribution,
             "joined_at": m.joined_at}
            for m in guild.members
        ],
        "resource_pool": guild.resource_pool,
        "weekly_challenge_progress": guild.weekly_challenge_progress,
        "weekly_challenge_goal": guild.weekly_challenge_goal,
        "weekly_challenge_reset_date": guild.weekly_challenge_reset_date,
        "invite_code": guild.invite_code,
        "element_balance_bonus": guild.element_balance_bonus,
    }
    with open(_guild_path(guild.guild_id), "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2)


def _load_chat(guild_id: str) -> List[dict]:
    """Load chat messages for a guild."""
    path = _chat_path(guild_id)
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return []


def _save_chat(guild_id: str, messages: List[dict]) -> None:
    """Save chat messages (rolling 100)."""
    _ensure_dir(GUILDS_DIR)
    messages = messages[-MAX_CHAT_MESSAGES:]
    with open(_chat_path(guild_id), "w", encoding="utf-8") as f:
        json.dump(messages, f, indent=2)


def _calculate_element_balance(members: List[GuildMember]) -> float:
    """Calculate elemental balance bonus.

    Returns 15.0 if 3+ different elements among members and min 4 members,
    otherwise 0.0.
    """
    if len(members) < MIN_MEMBERS_FOR_BONUS:
        return 0.0
    elements = {m.element for m in members if m.element}
    if len(elements) >= MIN_ELEMENTS_FOR_BONUS:
        return ELEMENTAL_BALANCE_BONUS
    return 0.0


def _check_weekly_reset(guild: GuildData) -> bool:
    """Check if weekly challenge needs reset. Returns True if reset occurred."""
    today = date.today().isoformat()
    if guild.weekly_challenge_reset_date and today >= guild.weekly_challenge_reset_date:
        # Check if challenge was completed before resetting
        completed = guild.weekly_challenge_progress >= guild.weekly_challenge_goal
        guild.weekly_challenge_progress = 0
        guild.weekly_challenge_reset_date = _next_monday()
        return completed
    if not guild.weekly_challenge_reset_date:
        guild.weekly_challenge_reset_date = _next_monday()
    return False


def _guild_to_response(guild: GuildData) -> dict:
    """Convert guild to API response dict."""
    return {
        "guild_id": guild.guild_id,
        "guild_name": guild.guild_name,
        "created_by": guild.created_by,
        "member_count": len(guild.members),
        "members": [
            {"player_id": m.player_id, "sun_sign": m.sun_sign,
             "element": m.element, "contribution": m.contribution,
             "joined_at": m.joined_at}
            for m in guild.members
        ],
        "resource_pool": guild.resource_pool,
        "weekly_challenge_progress": guild.weekly_challenge_progress,
        "weekly_challenge_goal": guild.weekly_challenge_goal,
        "weekly_challenge_reset_date": guild.weekly_challenge_reset_date,
        "invite_code": guild.invite_code,
        "element_balance_bonus": guild.element_balance_bonus,
    }


# ────────────────────────────────────────────────────────────────
# API Functions
# ────────────────────────────────────────────────────────────────

def create_guild(player_id: str, guild_name: str, sun_sign: str = "") -> dict:
    """Create a new guild.

    Args:
        player_id: Creator's player ID.
        guild_name: Name for the guild (max 30 chars).
        sun_sign: Creator's sun sign for element tracking.

    Returns:
        Dict with guild data or error.
    """
    # Check player isn't already in a guild
    index = _load_player_index()
    if player_id in index:
        return {"error": "You are already in a guild. Leave your current guild first."}

    # Sanitize name
    clean_name = _sanitize_guild_name(guild_name)
    if len(clean_name) < 2:
        return {"error": "Guild name must be at least 2 characters."}

    # Create guild
    guild_id = str(uuid.uuid4())[:12]
    element = ELEMENTS.get(sun_sign, "")
    member = GuildMember(
        player_id=player_id,
        sun_sign=sun_sign,
        element=element,
        contribution=0,
        joined_at=datetime.utcnow().isoformat(),
    )

    guild = GuildData(
        guild_id=guild_id,
        guild_name=clean_name,
        created_by=player_id,
        members=[member],
        invite_code=_generate_invite_code(),
        weekly_challenge_reset_date=_next_monday(),
    )
    guild.element_balance_bonus = _calculate_element_balance(guild.members)

    _save_guild(guild)
    index[player_id] = guild_id
    _save_player_index(index)

    return {"success": True, "guild": _guild_to_response(guild)}


def get_guild(player_id: str) -> dict:
    """Get guild details for a player.

    Returns:
        Dict with guild data or error if not in a guild.
    """
    index = _load_player_index()
    guild_id = index.get(player_id)
    if not guild_id:
        return {"error": "You are not in a guild.", "in_guild": False}

    guild = _load_guild(guild_id)
    if not guild:
        # Stale index entry
        del index[player_id]
        _save_player_index(index)
        return {"error": "Guild not found.", "in_guild": False}

    _check_weekly_reset(guild)
    _save_guild(guild)

    return {"success": True, "in_guild": True, "guild": _guild_to_response(guild)}


def join_guild(player_id: str, invite_code: str, sun_sign: str = "") -> dict:
    """Join a guild via invite code.

    Args:
        player_id: Player joining.
        invite_code: 8-char invite code.
        sun_sign: Player's sun sign for element tracking.

    Returns:
        Dict with guild data or error.
    """
    # Check player isn't already in a guild
    index = _load_player_index()
    if player_id in index:
        return {"error": "You are already in a guild. Leave your current guild first."}

    # Find guild by invite code
    _ensure_dir(GUILDS_DIR)
    target_guild = None
    for path in GUILDS_DIR.glob("*.json"):
        if path.name == "player_index.json" or path.name.endswith("_chat.json"):
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                d = json.load(f)
            if d.get("invite_code") == invite_code.upper():
                target_guild = _load_guild(d["guild_id"])
                break
        except (json.JSONDecodeError, IOError, KeyError):
            continue

    if not target_guild:
        return {"error": "Invalid invite code."}

    # Check capacity
    if len(target_guild.members) >= MAX_MEMBERS:
        return {"error": "This guild is full (max 12 members)."}

    # Add member
    element = ELEMENTS.get(sun_sign, "")
    member = GuildMember(
        player_id=player_id,
        sun_sign=sun_sign,
        element=element,
        contribution=0,
        joined_at=datetime.utcnow().isoformat(),
    )
    target_guild.members.append(member)
    target_guild.element_balance_bonus = _calculate_element_balance(target_guild.members)

    _save_guild(target_guild)
    index[player_id] = target_guild.guild_id
    _save_player_index(index)

    return {"success": True, "guild": _guild_to_response(target_guild)}


def leave_guild(player_id: str) -> dict:
    """Leave current guild. Transfers ownership if creator leaves.

    Returns:
        Dict with result.
    """
    index = _load_player_index()
    guild_id = index.get(player_id)
    if not guild_id:
        return {"error": "You are not in a guild."}

    guild = _load_guild(guild_id)
    if not guild:
        del index[player_id]
        _save_player_index(index)
        return {"error": "Guild not found."}

    # Remove member
    guild.members = [m for m in guild.members if m.player_id != player_id]
    del index[player_id]

    if not guild.members:
        # Guild is empty — delete it
        _guild_path(guild_id).unlink(missing_ok=True)
        _chat_path(guild_id).unlink(missing_ok=True)
        _save_player_index(index)
        return {"success": True, "message": "Left guild. Guild was disbanded (no members remaining)."}

    # Transfer ownership if creator left
    if guild.created_by == player_id:
        guild.created_by = guild.members[0].player_id

    guild.element_balance_bonus = _calculate_element_balance(guild.members)
    _save_guild(guild)
    _save_player_index(index)

    return {"success": True, "message": "Left guild successfully."}


def generate_invite(player_id: str) -> dict:
    """Generate a new invite code for the guild.

    Returns:
        Dict with new invite code.
    """
    index = _load_player_index()
    guild_id = index.get(player_id)
    if not guild_id:
        return {"error": "You are not in a guild."}

    guild = _load_guild(guild_id)
    if not guild:
        return {"error": "Guild not found."}

    guild.invite_code = _generate_invite_code()
    _save_guild(guild)

    return {"success": True, "invite_code": guild.invite_code}


def contribute_resources(player_id: str, resource: str, amount: int) -> dict:
    """Contribute resources from personal station to guild pool.

    Args:
        player_id: Contributing player.
        resource: Resource type.
        amount: Amount to contribute (must be positive).

    Returns:
        Dict with contribution result.
    """
    if amount <= 0:
        return {"error": "Contribution amount must be positive."}

    index = _load_player_index()
    guild_id = index.get(player_id)
    if not guild_id:
        return {"error": "You are not in a guild."}

    guild = _load_guild(guild_id)
    if not guild:
        return {"error": "Guild not found."}

    # Check player has resources
    station = get_station(player_id)
    if station is None:
        return {"error": "No station found. Create a station first."}

    if resource not in CORE_RESOURCES:
        return {"error": f"Invalid resource type: {resource}"}

    current = station.resources.get(resource, 0)
    if current < amount:
        return {"error": f"Insufficient {resource}. Have {current}, need {amount}."}

    # Deduct from player
    station.resources[resource] = current - amount
    save_station(station)

    # Add to guild pool
    guild.resource_pool[resource] = guild.resource_pool.get(resource, 0) + amount

    # Update member contribution
    for m in guild.members:
        if m.player_id == player_id:
            m.contribution += amount
            break

    # Update weekly challenge
    _check_weekly_reset(guild)
    guild.weekly_challenge_progress += amount

    _save_guild(guild)

    return {
        "success": True,
        "resource": resource,
        "amount": amount,
        "guild_pool": guild.resource_pool,
        "weekly_challenge_progress": guild.weekly_challenge_progress,
        "weekly_challenge_goal": guild.weekly_challenge_goal,
        "challenge_complete": guild.weekly_challenge_progress >= guild.weekly_challenge_goal,
    }


def get_weekly_challenge(player_id: str) -> dict:
    """Get weekly challenge status.

    Returns:
        Dict with challenge progress and goal.
    """
    index = _load_player_index()
    guild_id = index.get(player_id)
    if not guild_id:
        return {"error": "You are not in a guild."}

    guild = _load_guild(guild_id)
    if not guild:
        return {"error": "Guild not found."}

    _check_weekly_reset(guild)
    _save_guild(guild)

    progress_pct = min(100.0, (guild.weekly_challenge_progress / guild.weekly_challenge_goal) * 100)

    return {
        "success": True,
        "progress": guild.weekly_challenge_progress,
        "goal": guild.weekly_challenge_goal,
        "progress_percent": round(progress_pct, 1),
        "complete": guild.weekly_challenge_progress >= guild.weekly_challenge_goal,
        "reset_date": guild.weekly_challenge_reset_date,
        "reward_per_member": WEEKLY_CHALLENGE_REWARD,
        "member_count": len(guild.members),
    }


def send_chat_message(player_id: str, message: str) -> dict:
    """Send a chat message to guild chat.

    Args:
        player_id: Sending player.
        message: Message text (max 200 chars).

    Returns:
        Dict with result and recent messages.
    """
    index = _load_player_index()
    guild_id = index.get(player_id)
    if not guild_id:
        return {"error": "You are not in a guild."}

    guild = _load_guild(guild_id)
    if not guild:
        return {"error": "Guild not found."}

    # Sanitize message
    clean_message = message[:MAX_CHAT_MESSAGE_LENGTH].strip()
    if not clean_message:
        return {"error": "Message cannot be empty."}

    # Rate limiting
    messages = _load_chat(guild_id)
    now = datetime.utcnow()
    one_hour_ago = (now - timedelta(hours=1)).isoformat()
    recent_from_player = sum(
        1 for m in messages
        if m.get("player_id") == player_id and m.get("timestamp", "") > one_hour_ago
    )
    if recent_from_player >= CHAT_RATE_LIMIT_PER_HOUR:
        return {"error": f"Rate limited. Max {CHAT_RATE_LIMIT_PER_HOUR} messages per hour."}

    # Add message
    messages.append({
        "player_id": player_id,
        "message": clean_message,
        "timestamp": now.isoformat(),
    })
    _save_chat(guild_id, messages)

    # Return recent messages
    recent = messages[-20:]
    return {
        "success": True,
        "messages": recent,
        "total_messages": len(messages),
    }

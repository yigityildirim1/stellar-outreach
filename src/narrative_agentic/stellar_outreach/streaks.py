"""
NEXUS STATION - Stellar Outreach: Streak System with Freeze (TASK-012)

Daily engagement streak tracking with freeze mechanic and milestone rewards.
Designed with anti-dark-pattern principles — missed days are framed as
"pauses" rather than "breaks".

Features:
    - Daily check-in via briefing, mini-game, or resource collection
    - Auto-apply freeze on missed days if available
    - Milestone rewards at 3, 7, 14, 30, 100 days
    - 1 free freeze per week (Monday reset)
    - Purchase additional freezes with stardust (50 cost, max 3/week)

Ethics Note (Dr. Elena Vasquez review):
    This system uses positive framing only. No punishment for missed days.
    Freezes auto-apply to protect streaks. Messaging emphasizes "pause"
    not "break". The cosmos doesn't judge your schedule.

Security Note (Article II / Kai Chen review):
    Streak data persisted per player_id with sanitized paths.
    Server-side date validation prevents clock manipulation.

References:
    - GDD S9: Retention systems
    - TASK-003: Station module resource integration
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# ────────────────────────────────────────────────────────────────
# Persistence Configuration
# ────────────────────────────────────────────────────────────────

STREAKS_DIR = Path.home() / ".nexus_station" / "streaks"

FREEZE_COST_STARDUST = 50
MAX_FREEZES_PER_WEEK = 3
FREE_FREEZES_PER_WEEK = 1


def _sanitize_player_id(player_id: str) -> str:
    """Sanitize a player ID for safe filesystem use."""
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in player_id)


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


# ────────────────────────────────────────────────────────────────
# Milestone Rewards
# ────────────────────────────────────────────────────────────────

@dataclass
class MilestoneReward:
    """A streak milestone reward definition."""
    days: int
    reward_type: str       # "resources", "stardust", "cosmetic", "title", "legendary"
    title: str
    description: str
    rewards: dict          # specific reward data


MILESTONE_REWARDS: List[MilestoneReward] = [
    MilestoneReward(
        days=3,
        reward_type="resources",
        title="First Steps",
        description="Three days at the station. The cosmos notices your consistency.",
        rewards={"energy": 50, "materials": 50, "data": 50, "food": 50, "morale": 50, "stardust": 50},
    ),
    MilestoneReward(
        days=7,
        reward_type="stardust",
        title="Weekly Orbit",
        description="One full rotation complete. The stars are learning your rhythm.",
        rewards={"stardust": 100},
    ),
    MilestoneReward(
        days=14,
        reward_type="cosmetic",
        title="Steady Signal",
        description="Two weeks of presence. Your console begins to glow with a warm amber aura.",
        rewards={"cosmetic_id": "console_amber_glow", "cosmetic_name": "Console Amber Glow"},
    ),
    MilestoneReward(
        days=30,
        reward_type="title",
        title="Station Regular",
        description="Thirty days. The station recognizes you as one of its own.",
        rewards={
            "title": "Station Regular",
            "decoration_id": "station_regular_badge",
            "decoration_name": "Station Regular Badge",
        },
    ),
    MilestoneReward(
        days=100,
        reward_type="legendary",
        title="Celestial Constant",
        description="One hundred days. You have become a fixed point in the cosmos. The stars rearrange themselves around you.",
        rewards={
            "cosmetic_set": "celestial_constant",
            "cosmetic_set_name": "Celestial Constant Set",
            "includes": ["Starfield Console Skin", "Cosmic Aura Effect", "Constellation Title Frame"],
        },
    ),
]


# ────────────────────────────────────────────────────────────────
# Data Classes
# ────────────────────────────────────────────────────────────────

@dataclass
class StreakData:
    """Complete streak data for a player."""
    player_id: str
    current_streak: int
    longest_streak: int
    last_checkin_date: str       # ISO date (YYYY-MM-DD)
    total_checkins: int
    freezes_available: int
    freezes_used_this_week: int
    freeze_week_start: str       # ISO date of current week's Monday
    freeze_history: List[str]    # dates where freeze was applied
    claimed_rewards: List[int]   # milestone days already claimed
    created_at: str              # ISO datetime


# ────────────────────────────────────────────────────────────────
# Persistence
# ────────────────────────────────────────────────────────────────

def _streak_path(player_id: str) -> Path:
    safe_id = _sanitize_player_id(player_id)
    return STREAKS_DIR / f"{safe_id}.json"


def _load_streak_data(player_id: str) -> StreakData:
    """Load streak data for a player."""
    path = _streak_path(player_id)
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return StreakData(
                player_id=player_id,
                current_streak=data.get("current_streak", 0),
                longest_streak=data.get("longest_streak", 0),
                last_checkin_date=data.get("last_checkin_date", ""),
                total_checkins=data.get("total_checkins", 0),
                freezes_available=data.get("freezes_available", FREE_FREEZES_PER_WEEK),
                freezes_used_this_week=data.get("freezes_used_this_week", 0),
                freeze_week_start=data.get("freeze_week_start", ""),
                freeze_history=data.get("freeze_history", []),
                claimed_rewards=data.get("claimed_rewards", []),
                created_at=data.get("created_at", ""),
            )
        except (json.JSONDecodeError, IOError, TypeError):
            pass

    now = datetime.utcnow().isoformat()
    return StreakData(
        player_id=player_id,
        current_streak=0,
        longest_streak=0,
        last_checkin_date="",
        total_checkins=0,
        freezes_available=FREE_FREEZES_PER_WEEK,
        freezes_used_this_week=0,
        freeze_week_start=_current_week_start().isoformat(),
        freeze_history=[],
        claimed_rewards=[],
        created_at=now,
    )


def _save_streak_data(data: StreakData) -> None:
    """Save streak data for a player."""
    _ensure_dir(STREAKS_DIR)
    path = _streak_path(data.player_id)
    serialized = {
        "player_id": data.player_id,
        "current_streak": data.current_streak,
        "longest_streak": data.longest_streak,
        "last_checkin_date": data.last_checkin_date,
        "total_checkins": data.total_checkins,
        "freezes_available": data.freezes_available,
        "freezes_used_this_week": data.freezes_used_this_week,
        "freeze_week_start": data.freeze_week_start,
        "freeze_history": data.freeze_history,
        "claimed_rewards": data.claimed_rewards,
        "created_at": data.created_at,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(serialized, f, indent=2)


# ────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────

def _current_week_start() -> date:
    """Return the Monday of the current week."""
    today = date.today()
    return today - timedelta(days=today.weekday())


def _get_freeze_allocation(player_id: str) -> int:
    """Get weekly freeze allocation based on subscription status.

    Returns FREE_FREEZES_PER_WEEK (1) for free players,
    2 for Cosmic Pass holders, 3 for Stellar Premium.
    Graceful fallback if cosmic_pass module unavailable.
    """
    try:
        from narrative_agentic.stellar_outreach.cosmic_pass import get_active_benefits
        benefits = get_active_benefits(player_id)
        return benefits.get("weekly_freeze_allocation", FREE_FREEZES_PER_WEEK)
    except Exception:
        return FREE_FREEZES_PER_WEEK


def _reset_weekly_freezes_if_needed(data: StreakData) -> None:
    """Reset weekly freeze counter if we're in a new week."""
    current_monday = _current_week_start().isoformat()
    if data.freeze_week_start != current_monday:
        data.freeze_week_start = current_monday
        data.freezes_used_this_week = 0
        allocation = _get_freeze_allocation(data.player_id)
        data.freezes_available = max(data.freezes_available, allocation)


def _apply_freeze_if_needed(data: StreakData, today: date) -> bool:
    """Auto-apply a freeze for missed days if available.

    Returns True if a freeze was applied.
    """
    if not data.last_checkin_date:
        return False

    last_date = date.fromisoformat(data.last_checkin_date)
    days_missed = (today - last_date).days - 1  # days between last checkin and today

    if days_missed <= 0:
        return False

    # Apply freezes for missed days (one per day)
    freezes_applied = 0
    for i in range(days_missed):
        if data.freezes_available > 0:
            missed_date = last_date + timedelta(days=i + 1)
            data.freezes_available -= 1
            data.freezes_used_this_week += 1
            data.freeze_history.append(missed_date.isoformat())
            freezes_applied += 1
        else:
            # No freeze available — streak resets
            data.current_streak = 0
            return freezes_applied > 0

    return freezes_applied > 0


# ────────────────────────────────────────────────────────────────
# Public API
# ────────────────────────────────────────────────────────────────

def get_streak(player_id: str) -> dict:
    """Get current streak data for a player.

    Returns:
        Dictionary with streak information.
    """
    data = _load_streak_data(player_id)
    _reset_weekly_freezes_if_needed(data)

    # Check if freeze needed for today
    today = date.today()
    if data.last_checkin_date and data.last_checkin_date != today.isoformat():
        _apply_freeze_if_needed(data, today)
        _save_streak_data(data)

    # Determine available milestones
    available_rewards = []
    for milestone in MILESTONE_REWARDS:
        if data.current_streak >= milestone.days and milestone.days not in data.claimed_rewards:
            available_rewards.append({
                "days": milestone.days,
                "title": milestone.title,
                "reward_type": milestone.reward_type,
            })

    # Next milestone
    next_milestone = None
    for milestone in MILESTONE_REWARDS:
        if milestone.days > data.current_streak:
            next_milestone = {
                "days": milestone.days,
                "title": milestone.title,
                "days_remaining": milestone.days - data.current_streak,
            }
            break

    return {
        "player_id": player_id,
        "current_streak": data.current_streak,
        "longest_streak": data.longest_streak,
        "last_checkin_date": data.last_checkin_date,
        "total_checkins": data.total_checkins,
        "freezes_available": data.freezes_available,
        "freezes_used_this_week": data.freezes_used_this_week,
        "max_freezes_per_week": MAX_FREEZES_PER_WEEK,
        "available_rewards": available_rewards,
        "next_milestone": next_milestone,
        "message": _streak_message(data.current_streak),
    }


def get_streak_rewards(player_id: str) -> dict:
    """Get all streak rewards and their claim status.

    Returns:
        Dictionary with all milestone rewards.
    """
    data = _load_streak_data(player_id)

    rewards = []
    for milestone in MILESTONE_REWARDS:
        status = "locked"
        if milestone.days in data.claimed_rewards:
            status = "claimed"
        elif data.current_streak >= milestone.days:
            status = "available"

        rewards.append({
            "days": milestone.days,
            "title": milestone.title,
            "description": milestone.description,
            "reward_type": milestone.reward_type,
            "rewards": milestone.rewards,
            "status": status,
        })

    return {
        "player_id": player_id,
        "current_streak": data.current_streak,
        "rewards": rewards,
    }


def checkin(player_id: str) -> dict:
    """Record a daily check-in for streak tracking.

    Can be triggered by briefing view, mini-game play, or resource collection.

    Returns:
        Dictionary with updated streak data and any new rewards.
    """
    data = _load_streak_data(player_id)
    _reset_weekly_freezes_if_needed(data)

    today = date.today().isoformat()

    # Already checked in today
    if data.last_checkin_date == today:
        return {
            "success": True,
            "already_checked_in": True,
            "current_streak": data.current_streak,
            "message": "You've already checked in today. The station remembers.",
        }

    # Apply freeze for any missed days
    today_date = date.today()
    freeze_applied = _apply_freeze_if_needed(data, today_date)

    # If streak was reset (no freeze available for all missed days) and
    # last checkin was more than 1 day ago
    if data.last_checkin_date:
        last_date = date.fromisoformat(data.last_checkin_date)
        days_gap = (today_date - last_date).days
        if days_gap > 1 and data.current_streak == 0:
            # Streak was broken
            pass

    # Increment streak
    data.current_streak += 1
    data.total_checkins += 1
    data.last_checkin_date = today
    data.longest_streak = max(data.longest_streak, data.current_streak)

    # Check for newly available rewards
    new_rewards = []
    for milestone in MILESTONE_REWARDS:
        if data.current_streak >= milestone.days and milestone.days not in data.claimed_rewards:
            new_rewards.append({
                "days": milestone.days,
                "title": milestone.title,
                "reward_type": milestone.reward_type,
            })

    _save_streak_data(data)

    return {
        "success": True,
        "already_checked_in": False,
        "current_streak": data.current_streak,
        "longest_streak": data.longest_streak,
        "total_checkins": data.total_checkins,
        "freeze_applied": freeze_applied,
        "new_rewards_available": new_rewards,
        "message": _streak_message(data.current_streak),
    }


def purchase_freeze(player_id: str) -> dict:
    """Purchase an additional freeze with stardust.

    Costs 50 stardust. Max 3 freezes per week (including the free one).

    Returns:
        Status dictionary.
    """
    data = _load_streak_data(player_id)
    _reset_weekly_freezes_if_needed(data)

    # Check weekly limit
    if data.freezes_used_this_week >= MAX_FREEZES_PER_WEEK:
        return {
            "success": False,
            "reason": f"Maximum freezes for this week reached ({MAX_FREEZES_PER_WEEK})",
        }

    # Check stardust balance
    from narrative_agentic.stellar_outreach.station_modules import get_station, save_station

    station = get_station(player_id)
    if station is None:
        return {"success": False, "reason": "Station not found"}

    stardust = station.resources.get("stardust", 0)
    if stardust < FREEZE_COST_STARDUST:
        return {
            "success": False,
            "reason": f"Insufficient stardust (have {stardust}, need {FREEZE_COST_STARDUST})",
        }

    # Deduct stardust
    station.resources["stardust"] -= FREEZE_COST_STARDUST
    save_station(station)

    # Add freeze
    data.freezes_available += 1
    _save_streak_data(data)

    return {
        "success": True,
        "freezes_available": data.freezes_available,
        "stardust_remaining": station.resources["stardust"],
        "message": "Freeze acquired. The station holds your place among the stars.",
    }


def claim_reward(player_id: str, milestone_days: int) -> dict:
    """Claim a streak milestone reward.

    Args:
        player_id: The player claiming.
        milestone_days: The milestone day count to claim.

    Returns:
        Status dictionary with reward details.
    """
    data = _load_streak_data(player_id)

    # Validate milestone exists
    milestone = next((m for m in MILESTONE_REWARDS if m.days == milestone_days), None)
    if milestone is None:
        return {"success": False, "reason": f"No milestone at {milestone_days} days"}

    # Check if already claimed
    if milestone_days in data.claimed_rewards:
        return {"success": False, "reason": "Reward already claimed"}

    # Check if streak is sufficient
    if data.current_streak < milestone_days:
        return {
            "success": False,
            "reason": f"Current streak ({data.current_streak}) is below milestone ({milestone_days})",
        }

    # Apply resource rewards to station
    if milestone.reward_type in ("resources", "stardust"):
        from narrative_agentic.stellar_outreach.station_modules import get_station, save_station

        station = get_station(player_id)
        if station is not None:
            for resource, amount in milestone.rewards.items():
                if resource in station.resources:
                    station.resources[resource] = station.resources.get(resource, 0) + amount
            save_station(station)

    # Mark as claimed
    data.claimed_rewards.append(milestone_days)
    _save_streak_data(data)

    return {
        "success": True,
        "milestone_days": milestone_days,
        "title": milestone.title,
        "description": milestone.description,
        "reward_type": milestone.reward_type,
        "rewards": milestone.rewards,
        "message": f"Milestone reached: {milestone.title}. The cosmos acknowledges your dedication.",
    }


# ────────────────────────────────────────────────────────────────
# Messaging Helpers
# ────────────────────────────────────────────────────────────────

def _streak_message(streak: int) -> str:
    """Generate a positive streak message. Anti-dark-pattern: no shame, only encouragement."""
    if streak == 0:
        return "Welcome back. Every journey begins again from here."
    elif streak == 1:
        return "Day 1. The station powers on. A new signal begins."
    elif streak <= 3:
        return f"Day {streak}. Momentum building. The instruments are warming up."
    elif streak <= 7:
        return f"Day {streak}. A steady presence. The station hums a little louder for you."
    elif streak <= 14:
        return f"Day {streak}. Two weeks of starlight. The cosmos takes notice."
    elif streak <= 30:
        return f"Day {streak}. Your rhythm is becoming part of the station's heartbeat."
    elif streak <= 100:
        return f"Day {streak}. A fixed point in the cosmic calendar. Remarkable."
    else:
        return f"Day {streak}. Beyond milestones. You are the station now."

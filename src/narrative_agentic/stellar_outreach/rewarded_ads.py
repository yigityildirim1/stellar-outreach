"""
NEXUS STATION - Stellar Outreach: Rewarded Ads Integration (TASK-017)

Server-side rewarded ad system completing the monetization triad:
Store (TASK-015) + Pass (TASK-016) + Ads (TASK-017).

Features:
    - 4 ad placement types: daily_bonus, mission_boost, streak_save, resource_boost
    - Subscription-aware caps: free (5/day), pass (3/day), premium (0/day ad-free)
    - 5-minute cooldown between ads (server-enforced)
    - Rewards: stardust, season XP, streak freezes
    - Stubbed ad network verification (production needs server-side callbacks)

Ethics Note (Dr. Elena Vasquez review):
    [ELENA] Premium subscribers see zero ads (ad_free flag respected).
    Free players capped at 5/day — generous but not exploitative.
    5-minute cooldown prevents compulsive ad watching.
    Rewards are meaningful but not so large they create pay-to-win pressure.
    All rewards available through normal gameplay — ads are a shortcut, not a gate.

Security Note (Kai Chen review):
    [KAI] Ad network verification is stubbed (production needs server-side
    callback verification). Daily cap enforced server-side (client can't bypass).
    Ad history append-only with max 200 entries (prevents unbounded growth).
    Player ID sanitized on all endpoints. Cooldown tracked server-side.

UX Note (Marina Okonkwo review):
    [MARINA] Reward previews shown before watching. Clear messaging on
    remaining daily slots. No dark patterns — user always knows what they get.

Precedent Note (Prof. James Whitmore):
    PREC-017-A: Subscription-gated ad frequency pattern
    PREC-017-B: Multi-placement reward table
    PREC-017-C: Server-side ad cooldown enforcement

References:
    - TASK-015: Cosmetic Store (wallet, transaction patterns)
    - TASK-016: Cosmic Pass (benefits aggregator, XP sources)
    - TASK-012: Streaks (freeze mechanic)
    - TASK-003: Station modules (stardust resource)
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional


# ────────────────────────────────────────────────────────────────
# Configuration
# ────────────────────────────────────────────────────────────────

ADS_DIR = Path.home() / ".nexus_station" / "ads"

# Daily ad caps by subscription tier
MAX_ADS_PER_DAY_FREE = 5
MAX_ADS_PER_DAY_PASS = 3       # Cosmic Pass (reduced_ads)
MAX_ADS_PER_DAY_PREMIUM = 0    # Stellar Premium (ad_free)

# Cooldown between ads
AD_COOLDOWN_SECONDS = 300       # 5 minutes

# History cap
MAX_AD_HISTORY = 200


def _sanitize_player_id(player_id: str) -> str:
    """Sanitize a player ID for safe filesystem use."""
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in player_id)


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


# ────────────────────────────────────────────────────────────────
# Reward Table — 4 Ad Placement Types
# ────────────────────────────────────────────────────────────────

REWARD_TABLE: Dict[str, dict] = {
    "daily_bonus": {
        "placement": "daily_bonus",
        "name": "Daily Bonus",
        "description": "Watch an ad to collect your daily stardust bonus.",
        "reward_type": "stardust",
        "reward_amount": 100,
        "max_per_day": 1,
        "cooldown_seconds": 0,     # Once per day, no cooldown needed
    },
    "mission_boost": {
        "placement": "mission_boost",
        "name": "Mission Boost",
        "description": "Watch an ad after a mission for bonus season XP.",
        "reward_type": "season_xp",
        "reward_amount": 15,
        "max_per_day": 0,          # 0 = use global daily cap
        "cooldown_seconds": AD_COOLDOWN_SECONDS,
    },
    "streak_save": {
        "placement": "streak_save",
        "name": "Streak Save",
        "description": "Watch an ad to earn a streak freeze for later use.",
        "reward_type": "freeze",
        "reward_amount": 1,
        "max_per_day": 1,
        "cooldown_seconds": 0,     # Once per day
    },
    "resource_boost": {
        "placement": "resource_boost",
        "name": "Resource Boost",
        "description": "Watch an ad for a quick stardust infusion.",
        "reward_type": "stardust",
        "reward_amount": 50,
        "max_per_day": 0,          # Use global daily cap
        "cooldown_seconds": AD_COOLDOWN_SECONDS,
    },
}


# ────────────────────────────────────────────────────────────────
# Data Model
# ────────────────────────────────────────────────────────────────

@dataclass
class AdPlayerData:
    """Complete ad data for a player."""
    player_id: str
    ads_watched_today: int = 0
    total_ads_watched: int = 0
    last_watch_date: str = ""           # ISO date for daily reset
    last_watch_time: str = ""           # ISO datetime for cooldown
    ad_history: List[dict] = field(default_factory=list)
    pending_rewards: List[dict] = field(default_factory=list)
    placement_counts_today: Dict[str, int] = field(default_factory=dict)
    lifetime_stardust_from_ads: int = 0
    lifetime_freezes_from_ads: int = 0
    lifetime_xp_from_ads: int = 0
    created_at: str = ""


# ────────────────────────────────────────────────────────────────
# Persistence
# ────────────────────────────────────────────────────────────────

def _ad_path(player_id: str) -> Path:
    safe_id = _sanitize_player_id(player_id)
    return ADS_DIR / f"{safe_id}.json"


def _load_ad_data(player_id: str) -> AdPlayerData:
    """Load ad data for a player."""
    path = _ad_path(player_id)
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                d = json.load(f)
            return AdPlayerData(
                player_id=player_id,
                ads_watched_today=d.get("ads_watched_today", 0),
                total_ads_watched=d.get("total_ads_watched", 0),
                last_watch_date=d.get("last_watch_date", ""),
                last_watch_time=d.get("last_watch_time", ""),
                ad_history=d.get("ad_history", [])[-MAX_AD_HISTORY:],
                pending_rewards=d.get("pending_rewards", []),
                placement_counts_today=d.get("placement_counts_today", {}),
                lifetime_stardust_from_ads=d.get("lifetime_stardust_from_ads", 0),
                lifetime_freezes_from_ads=d.get("lifetime_freezes_from_ads", 0),
                lifetime_xp_from_ads=d.get("lifetime_xp_from_ads", 0),
                created_at=d.get("created_at", ""),
            )
        except (json.JSONDecodeError, IOError, TypeError):
            pass

    now = datetime.utcnow().isoformat()
    return AdPlayerData(player_id=player_id, created_at=now)


def _save_ad_data(data: AdPlayerData) -> None:
    """Save ad data for a player."""
    _ensure_dir(ADS_DIR)
    path = _ad_path(data.player_id)

    # Trim history before saving
    history = data.ad_history[-MAX_AD_HISTORY:]

    d = {
        "player_id": data.player_id,
        "ads_watched_today": data.ads_watched_today,
        "total_ads_watched": data.total_ads_watched,
        "last_watch_date": data.last_watch_date,
        "last_watch_time": data.last_watch_time,
        "ad_history": history,
        "pending_rewards": data.pending_rewards,
        "placement_counts_today": data.placement_counts_today,
        "lifetime_stardust_from_ads": data.lifetime_stardust_from_ads,
        "lifetime_freezes_from_ads": data.lifetime_freezes_from_ads,
        "lifetime_xp_from_ads": data.lifetime_xp_from_ads,
        "created_at": data.created_at,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2)


def _reset_daily_if_needed(data: AdPlayerData) -> None:
    """Reset daily counters if the date has changed."""
    today = date.today().isoformat()
    if data.last_watch_date != today:
        data.ads_watched_today = 0
        data.placement_counts_today = {}
        data.last_watch_date = today


# ────────────────────────────────────────────────────────────────
# Subscription-Aware Helpers
# ────────────────────────────────────────────────────────────────

def _get_daily_cap(player_id: str) -> int:
    """Get the daily ad cap based on subscription status."""
    try:
        from narrative_agentic.stellar_outreach.cosmic_pass import get_active_benefits
        benefits = get_active_benefits(player_id)
        if benefits.get("ad_free"):
            return MAX_ADS_PER_DAY_PREMIUM
        if benefits.get("reduced_ads"):
            return MAX_ADS_PER_DAY_PASS
    except Exception:
        pass
    return MAX_ADS_PER_DAY_FREE


def _seconds_until_cooldown_expires(data: AdPlayerData) -> int:
    """Calculate seconds remaining on cooldown. Returns 0 if ready."""
    if not data.last_watch_time:
        return 0
    try:
        last = datetime.fromisoformat(data.last_watch_time)
        elapsed = (datetime.utcnow() - last).total_seconds()
        remaining = AD_COOLDOWN_SECONDS - elapsed
        return max(0, int(remaining))
    except (ValueError, TypeError):
        return 0


# ────────────────────────────────────────────────────────────────
# Reward Granting
# ────────────────────────────────────────────────────────────────

def _grant_stardust(player_id: str, amount: int) -> bool:
    """Grant stardust to a player's station."""
    try:
        from narrative_agentic.stellar_outreach.station_modules import get_station, save_station
        station = get_station(player_id)
        if station:
            station.resources["stardust"] = station.resources.get("stardust", 0) + amount
            save_station(station)
            return True
    except Exception:
        pass
    return False


def _grant_freeze(player_id: str, amount: int) -> bool:
    """Grant streak freezes to a player."""
    try:
        from narrative_agentic.stellar_outreach.streaks import _load_streak_data, _save_streak_data
        streak = _load_streak_data(player_id)
        streak.freezes_available += amount
        _save_streak_data(streak)
        return True
    except Exception:
        pass
    return False


def _grant_season_xp(player_id: str, amount: int) -> bool:
    """Grant season XP via the cosmic pass system."""
    try:
        from narrative_agentic.stellar_outreach.cosmic_pass import earn_season_xp
        result = earn_season_xp(player_id, "rewarded_ad", amount)
        return result.get("success", False)
    except Exception:
        pass
    return False


# ────────────────────────────────────────────────────────────────
# Public API — GET Endpoints
# ────────────────────────────────────────────────────────────────

def get_ad_status(player_id: str) -> dict:
    """Get current ad status for a player.

    Returns daily watches, remaining slots, cooldown timer,
    available placements, and next reward preview.

    Args:
        player_id: Player identifier.

    Returns:
        Dict with ad status information.
    """
    data = _load_ad_data(player_id)
    _reset_daily_if_needed(data)
    _save_ad_data(data)

    daily_cap = _get_daily_cap(player_id)
    remaining = max(0, daily_cap - data.ads_watched_today)
    cooldown_remaining = _seconds_until_cooldown_expires(data)

    # Find next available placement for preview
    available = _get_available_list(data, daily_cap)
    next_reward = None
    if available:
        placement_info = REWARD_TABLE[available[0]]
        next_reward = {
            "placement": placement_info["placement"],
            "reward_type": placement_info["reward_type"],
            "reward_amount": placement_info["reward_amount"],
        }

    return {
        "player_id": player_id,
        "ads_watched_today": data.ads_watched_today,
        "daily_cap": daily_cap,
        "remaining_today": remaining,
        "cooldown_seconds": cooldown_remaining,
        "available_placements": available,
        "next_reward_preview": next_reward,
        "ad_free": daily_cap == 0,
    }


def get_available_placements(player_id: str) -> dict:
    """Get which ad placements are currently available.

    Respects cooldowns, daily caps per placement, and subscription status.

    Args:
        player_id: Player identifier.

    Returns:
        Dict with available placement details.
    """
    data = _load_ad_data(player_id)
    _reset_daily_if_needed(data)

    daily_cap = _get_daily_cap(player_id)

    if daily_cap == 0:
        return {
            "player_id": player_id,
            "ad_free": True,
            "placements": [],
            "message": "your premium subscription keeps the signal clear. no ads.",
        }

    available = _get_available_list(data, daily_cap)
    cooldown_remaining = _seconds_until_cooldown_expires(data)

    placements = []
    for placement_id in REWARD_TABLE:
        info = REWARD_TABLE[placement_id]
        is_available = placement_id in available
        placement_today = data.placement_counts_today.get(placement_id, 0)
        placement_cap = info["max_per_day"]

        placements.append({
            "placement": placement_id,
            "name": info["name"],
            "description": info["description"],
            "reward_type": info["reward_type"],
            "reward_amount": info["reward_amount"],
            "available": is_available,
            "watched_today": placement_today,
            "daily_limit": placement_cap if placement_cap > 0 else daily_cap,
            "on_cooldown": cooldown_remaining > 0 and info["cooldown_seconds"] > 0,
        })

    return {
        "player_id": player_id,
        "ad_free": False,
        "placements": placements,
        "cooldown_seconds": cooldown_remaining,
        "ads_remaining_today": max(0, daily_cap - data.ads_watched_today),
    }


def get_ad_config() -> dict:
    """Get ad system configuration for the mobile client.

    Returns reward table, caps, cooldowns — everything the client
    needs to display ad opportunities correctly.

    Returns:
        Dict with full ad configuration.
    """
    placements = []
    for placement_id, info in REWARD_TABLE.items():
        placements.append({
            "placement": placement_id,
            "name": info["name"],
            "description": info["description"],
            "reward_type": info["reward_type"],
            "reward_amount": info["reward_amount"],
            "max_per_day": info["max_per_day"],
            "cooldown_seconds": info["cooldown_seconds"],
        })

    return {
        "placements": placements,
        "daily_caps": {
            "free": MAX_ADS_PER_DAY_FREE,
            "cosmic_pass": MAX_ADS_PER_DAY_PASS,
            "stellar_premium": MAX_ADS_PER_DAY_PREMIUM,
        },
        "cooldown_seconds": AD_COOLDOWN_SECONDS,
        "max_history": MAX_AD_HISTORY,
    }


def get_ad_history(player_id: str, limit: int = 20, offset: int = 0) -> dict:
    """Get paginated ad watch history.

    Args:
        player_id: Player identifier.
        limit: Number of entries to return (default 20).
        offset: Number of entries to skip (default 0).

    Returns:
        Dict with paginated ad history.
    """
    data = _load_ad_data(player_id)

    # History is newest-first
    history = list(reversed(data.ad_history))
    total = len(history)
    page = history[offset:offset + limit]

    return {
        "player_id": player_id,
        "total": total,
        "limit": limit,
        "offset": offset,
        "history": page,
    }


def get_ad_stats(player_id: str) -> dict:
    """Get lifetime ad statistics.

    Args:
        player_id: Player identifier.

    Returns:
        Dict with lifetime ad stats.
    """
    data = _load_ad_data(player_id)
    _reset_daily_if_needed(data)

    return {
        "player_id": player_id,
        "total_ads_watched": data.total_ads_watched,
        "ads_watched_today": data.ads_watched_today,
        "lifetime_stardust_from_ads": data.lifetime_stardust_from_ads,
        "lifetime_freezes_from_ads": data.lifetime_freezes_from_ads,
        "lifetime_xp_from_ads": data.lifetime_xp_from_ads,
        "created_at": data.created_at,
    }


# ────────────────────────────────────────────────────────────────
# Public API — POST Endpoint
# ────────────────────────────────────────────────────────────────

def watch_rewarded_ad(player_id: str, placement: str, ad_network: str = "stub") -> dict:
    """Watch a rewarded ad and receive the corresponding reward.

    Main endpoint: validates eligibility (subscription caps, cooldown,
    placement limits), generates ad_id, calculates reward, grants it
    through the appropriate system, logs the transaction.

    Args:
        player_id: Player identifier.
        placement: Ad placement type (daily_bonus, mission_boost, etc.).
        ad_network: Ad network identifier (stub for development).

    Returns:
        Dict with ad reward result.
    """
    # Validate placement
    if placement not in REWARD_TABLE:
        return {
            "error": f"Unknown placement: {placement}. Valid: {list(REWARD_TABLE.keys())}",
        }

    # Load and reset
    data = _load_ad_data(player_id)
    _reset_daily_if_needed(data)

    # Check subscription — premium = ad-free
    daily_cap = _get_daily_cap(player_id)
    if daily_cap == 0:
        return {
            "error": "ad_free",
            "message": "your premium subscription means no ads. the cosmos thanks your patronage.",
        }

    # Check global daily cap
    if data.ads_watched_today >= daily_cap:
        return {
            "error": "daily_cap_reached",
            "ads_watched": data.ads_watched_today,
            "daily_cap": daily_cap,
            "message": "you've reached today's limit. the station dims the ad beacon. rest.",
        }

    # Check placement-specific daily cap
    placement_info = REWARD_TABLE[placement]
    placement_cap = placement_info["max_per_day"]
    placement_today = data.placement_counts_today.get(placement, 0)
    if placement_cap > 0 and placement_today >= placement_cap:
        return {
            "error": "placement_cap_reached",
            "placement": placement,
            "watched": placement_today,
            "max_per_day": placement_cap,
            "message": f"you've already claimed {placement_info['name'].lower()} today. try another placement.",
        }

    # Check cooldown (only for placements that have one)
    if placement_info["cooldown_seconds"] > 0:
        cooldown_left = _seconds_until_cooldown_expires(data)
        if cooldown_left > 0:
            return {
                "error": "cooldown_active",
                "seconds_remaining": cooldown_left,
                "message": f"the ad beacon recharges. {cooldown_left} seconds until next transmission.",
            }

    # ── Ad network verification (stubbed) ──
    ad_id = f"ad_{uuid.uuid4().hex[:12]}"
    if ad_network != "stub":
        # Production: verify ad completion via server-side callback
        # For now, accept all networks in stub mode
        pass

    # ── Grant reward ──
    reward_type = placement_info["reward_type"]
    reward_amount = placement_info["reward_amount"]
    granted = False

    if reward_type == "stardust":
        granted = _grant_stardust(player_id, reward_amount)
        if granted:
            data.lifetime_stardust_from_ads += reward_amount

    elif reward_type == "freeze":
        granted = _grant_freeze(player_id, reward_amount)
        if granted:
            data.lifetime_freezes_from_ads += reward_amount

    elif reward_type == "season_xp":
        granted = _grant_season_xp(player_id, reward_amount)
        if granted:
            data.lifetime_xp_from_ads += reward_amount

    if not granted:
        # Reward couldn't be applied — still count the ad but note the issue
        data.pending_rewards.append({
            "ad_id": ad_id,
            "placement": placement,
            "reward_type": reward_type,
            "reward_amount": reward_amount,
            "timestamp": datetime.utcnow().isoformat(),
        })

    # ── Update counters ──
    now = datetime.utcnow()
    data.ads_watched_today += 1
    data.total_ads_watched += 1
    data.last_watch_time = now.isoformat()
    data.last_watch_date = date.today().isoformat()
    data.placement_counts_today[placement] = placement_today + 1

    # ── Log transaction ──
    entry = {
        "ad_id": ad_id,
        "placement": placement,
        "ad_network": ad_network,
        "reward_type": reward_type,
        "reward_amount": reward_amount,
        "granted": granted,
        "timestamp": now.isoformat(),
    }
    data.ad_history.append(entry)

    _save_ad_data(data)

    remaining = max(0, daily_cap - data.ads_watched_today)

    return {
        "success": True,
        "ad_id": ad_id,
        "placement": placement,
        "reward_type": reward_type,
        "reward_amount": reward_amount,
        "granted": granted,
        "ads_watched_today": data.ads_watched_today,
        "remaining_today": remaining,
        "message": _reward_message(reward_type, reward_amount),
    }


# ────────────────────────────────────────────────────────────────
# Private Helpers
# ────────────────────────────────────────────────────────────────

def _get_available_list(data: AdPlayerData, daily_cap: int) -> List[str]:
    """Get list of currently available placement IDs."""
    if daily_cap == 0:
        return []

    if data.ads_watched_today >= daily_cap:
        return []

    cooldown_left = _seconds_until_cooldown_expires(data)
    available = []

    for placement_id, info in REWARD_TABLE.items():
        # Check placement-specific daily cap
        placement_cap = info["max_per_day"]
        placement_today = data.placement_counts_today.get(placement_id, 0)
        if placement_cap > 0 and placement_today >= placement_cap:
            continue

        # Check cooldown (only for placements that require it)
        if info["cooldown_seconds"] > 0 and cooldown_left > 0:
            continue

        available.append(placement_id)

    return available


def _reward_message(reward_type: str, amount: int) -> str:
    """Generate a Co-Star-style reward message."""
    if reward_type == "stardust":
        return f"+{amount} stardust collected. the cosmos pays its debts."
    elif reward_type == "freeze":
        return "a streak freeze crystallizes in your quarters. use it wisely."
    elif reward_type == "season_xp":
        return f"+{amount} season XP. the pass advances. momentum builds."
    return f"reward granted: {amount} {reward_type}."

"""
NEXUS STATION - Stellar Outreach: Cosmic Pass & Stellar Premium (TASK-016)

Season pass (battle pass) and monthly premium subscription system.
Dual-track reward tiers, subscription lifecycle, XP earning, and
centralized benefits aggregation.

Features:
    - Cosmic Pass ($4.99/season ~90 days): bonus daily mission, 2 freezes/week,
      reduced ads, season-exclusive cosmetics, 1hr early event access
    - Stellar Premium ($2.99/month): ad-free, 3 freezes/week, monthly exclusive
      cosmetic, extra weekly mission, 1hr early event access
    - 30-tier battle pass with free + premium tracks
    - XP sources from daily missions, mini-games, check-ins, NPCs, guilds, atlas
    - Central benefits aggregator consumed by all systems

Ethics Note (Dr. Elena Vasquez review):
    Free track has meaningful rewards (3475+ stardust, freezes, title).
    No gameplay advantage from subscriptions — cosmetics + convenience only.
    Cancellation is graceful (benefits persist until end_date).
    Season is 90 days — ample time, no FOMO pressure.
    Monthly cosmetic framed as "gift" not "loss if missed".

Security Note (Kai Chen review):
    Receipt dedup via SHA-256 (reuses cosmetic_store pattern).
    STUB_MODE=True for development. Idempotent: re-subscribe extends
    from current end_date, not today. Grace period prevents accidental
    benefit loss on billing delays.

UX Note (Marina Okonkwo review):
    Battle pass progress always visible. Free rewards celebrated equally.
    Premium track shown as "bonus" not "locked". Cancel flow is one action
    with clear messaging about remaining benefits.

Precedent Note (Prof. James Whitmore):
    PREC-016-A: Subscription lifecycle pattern
    PREC-016-B: Battle-pass dual-track reward system
    PREC-016-C: Distributed XP earning from multiple systems
    PREC-016-D: Benefits aggregation pattern

References:
    - TASK-015: Cosmetic Store (receipt dedup, wallet, transaction patterns)
    - TASK-012: Streaks (freeze allocation integration)
    - TASK-003: Station modules (stardust resource)
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional


# ────────────────────────────────────────────────────────────────
# Configuration
# ────────────────────────────────────────────────────────────────

PASS_DIR = Path.home() / ".nexus_station" / "cosmic_pass"

# IAP validation mode — True = stub (dev/testing), False = production
STUB_MODE = True

# Subscription durations
SEASON_DURATION_DAYS = 90
PREMIUM_DURATION_DAYS = 30
GRACE_PERIOD_DAYS = 3

# XP configuration
XP_PER_TIER = 100
TOTAL_TIERS = 30

# Freeze allocations by tier
FREE_FREEZES_PER_WEEK = 1
PASS_FREEZES_PER_WEEK = 2
PREMIUM_FREEZES_PER_WEEK = 3

# Valid XP sources and their awards
XP_SOURCES: Dict[str, int] = {
    "daily_mission": 15,
    "bonus_mission": 15,       # Cosmic Pass holders only
    "mini_game_win": 5,
    "daily_checkin": 10,
    "discovery_card": 5,
    "npc_interaction": 3,
    "guild_challenge": 10,
    "atlas_discovery": 5,
    "rewarded_ad": 10,
    "ar_discovery": 5,
}


def _sanitize_player_id(player_id: str) -> str:
    """Sanitize a player ID for safe filesystem use."""
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in player_id)


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


# ────────────────────────────────────────────────────────────────
# Subscription Products
# ────────────────────────────────────────────────────────────────

SUBSCRIPTION_PRODUCTS: Dict[str, dict] = {
    "cosmic_pass": {
        "product_id": "cosmic_pass",
        "name": "Cosmic Pass",
        "description": "Season pass with bonus missions, extra freezes, reduced ads, and exclusive cosmetics. Lasts the full season (~90 days).",
        "price_usd": 4.99,
        "duration_days": SEASON_DURATION_DAYS,
        "apple_product_id": "com.nexusstation.cosmic_pass",
        "google_product_id": "cosmic_pass_season",
        "benefits": [
            "Bonus daily mission (+15 XP/day)",
            "2 streak freezes per week (instead of 1)",
            "Reduced ads",
            "Season-exclusive cosmetics (premium track)",
            "1hr early event access",
        ],
    },
    "stellar_premium": {
        "product_id": "stellar_premium",
        "name": "Stellar Premium",
        "description": "Monthly premium subscription. Ad-free experience, extra freezes, monthly exclusive cosmetic, and early event access.",
        "price_usd": 2.99,
        "duration_days": PREMIUM_DURATION_DAYS,
        "apple_product_id": "com.nexusstation.stellar_premium",
        "google_product_id": "stellar_premium_monthly",
        "benefits": [
            "Ad-free experience",
            "3 streak freezes per week (instead of 1)",
            "Monthly exclusive cosmetic gift",
            "Extra weekly mission",
            "1hr early event access",
        ],
    },
}


# ────────────────────────────────────────────────────────────────
# Season Definitions
# ────────────────────────────────────────────────────────────────

def _current_season() -> dict:
    """Get current season info based on date.

    Seasons rotate every SEASON_DURATION_DAYS starting from a fixed epoch.
    """
    epoch = date(2025, 1, 1)
    today = date.today()
    days_since = (today - epoch).days
    season_number = (days_since // SEASON_DURATION_DAYS) + 1
    season_start = epoch + timedelta(days=(season_number - 1) * SEASON_DURATION_DAYS)
    season_end = season_start + timedelta(days=SEASON_DURATION_DAYS - 1)
    days_remaining = (season_end - today).days

    return {
        "season_id": f"S{season_number:03d}",
        "season_number": season_number,
        "season_name": _season_name(season_number),
        "start_date": season_start.isoformat(),
        "end_date": season_end.isoformat(),
        "duration_days": SEASON_DURATION_DAYS,
        "days_remaining": max(0, days_remaining),
        "days_elapsed": min(SEASON_DURATION_DAYS, (today - season_start).days),
        "total_tiers": TOTAL_TIERS,
        "xp_per_tier": XP_PER_TIER,
        "total_xp_needed": TOTAL_TIERS * XP_PER_TIER,
    }


def _season_name(number: int) -> str:
    """Generate a thematic season name."""
    names = [
        "Stellar Dawn", "Nebula Rising", "Cosmic Drift",
        "Void Whisper", "Pulsar Echo", "Quasar Bloom",
        "Aurora Tide", "Eclipse Path", "Comet Trail",
        "Singularity", "Starfall", "Horizon Signal",
    ]
    return names[(number - 1) % len(names)]


# ────────────────────────────────────────────────────────────────
# Battle Pass Rewards — 30 Tiers, Dual Track
# ────────────────────────────────────────────────────────────────

def _build_reward_tiers() -> List[dict]:
    """Build the 30-tier reward table with free + premium tracks.

    Free track: stardust, resources, streak freezes, title
    Premium track: gems, skins, trails, effects, outfits, decorations
    """
    tiers = []

    # Free track reward pool (meaningful rewards — ELENA review)
    free_rewards = {
        1: {"type": "stardust", "amount": 50, "name": "50 Stardust"},
        2: {"type": "stardust", "amount": 75, "name": "75 Stardust"},
        3: {"type": "resources", "data": {"energy": 30, "materials": 30}, "name": "Resource Pack I"},
        4: {"type": "stardust", "amount": 100, "name": "100 Stardust"},
        5: {"type": "freeze", "amount": 1, "name": "Streak Freeze"},
        6: {"type": "stardust", "amount": 100, "name": "100 Stardust"},
        7: {"type": "resources", "data": {"energy": 50, "materials": 50, "data": 50}, "name": "Resource Pack II"},
        8: {"type": "stardust", "amount": 125, "name": "125 Stardust"},
        9: {"type": "stardust", "amount": 125, "name": "125 Stardust"},
        10: {"type": "freeze", "amount": 1, "name": "Streak Freeze"},
        11: {"type": "stardust", "amount": 150, "name": "150 Stardust"},
        12: {"type": "resources", "data": {"energy": 75, "materials": 75, "food": 75}, "name": "Resource Pack III"},
        13: {"type": "stardust", "amount": 150, "name": "150 Stardust"},
        14: {"type": "stardust", "amount": 175, "name": "175 Stardust"},
        15: {"type": "freeze", "amount": 2, "name": "2x Streak Freeze"},
        16: {"type": "stardust", "amount": 175, "name": "175 Stardust"},
        17: {"type": "resources", "data": {"energy": 100, "materials": 100, "data": 100, "food": 100}, "name": "Resource Pack IV"},
        18: {"type": "stardust", "amount": 200, "name": "200 Stardust"},
        19: {"type": "stardust", "amount": 200, "name": "200 Stardust"},
        20: {"type": "freeze", "amount": 2, "name": "2x Streak Freeze"},
        21: {"type": "stardust", "amount": 225, "name": "225 Stardust"},
        22: {"type": "resources", "data": {"energy": 150, "materials": 150, "data": 150, "morale": 100}, "name": "Resource Pack V"},
        23: {"type": "stardust", "amount": 225, "name": "225 Stardust"},
        24: {"type": "stardust", "amount": 250, "name": "250 Stardust"},
        25: {"type": "freeze", "amount": 3, "name": "3x Streak Freeze"},
        26: {"type": "stardust", "amount": 250, "name": "250 Stardust"},
        27: {"type": "resources", "data": {"energy": 200, "materials": 200, "data": 200, "food": 200, "morale": 150}, "name": "Resource Pack VI"},
        28: {"type": "stardust", "amount": 300, "name": "300 Stardust"},
        29: {"type": "stardust", "amount": 300, "name": "300 Stardust"},
        30: {"type": "title", "title": "Season Voyager", "name": "Title: Season Voyager"},
    }

    # Premium track reward pool (cosmetics + bonus gems)
    premium_rewards = {
        1: {"type": "gems", "amount": 25, "name": "25 Stellar Gems"},
        2: {"type": "gems", "amount": 25, "name": "25 Stellar Gems"},
        3: {"type": "trail", "item_id": "trail_season_ember", "name": "Season Ember Trail"},
        4: {"type": "gems", "amount": 50, "name": "50 Stellar Gems"},
        5: {"type": "gems", "amount": 50, "name": "50 Stellar Gems"},
        6: {"type": "decoration", "item_id": "deco_season_badge", "name": "Season Badge"},
        7: {"type": "gems", "amount": 50, "name": "50 Stellar Gems"},
        8: {"type": "gems", "amount": 75, "name": "75 Stellar Gems"},
        9: {"type": "effect", "item_id": "effect_season_glow", "name": "Season Glow Effect"},
        10: {"type": "skin", "item_id": "skin_season_alpha", "name": "Season Skin: Alpha"},
        11: {"type": "gems", "amount": 75, "name": "75 Stellar Gems"},
        12: {"type": "outfit", "item_id": "outfit_season_reyes", "name": "Season Outfit: Reyes"},
        13: {"type": "gems", "amount": 75, "name": "75 Stellar Gems"},
        14: {"type": "gems", "amount": 100, "name": "100 Stellar Gems"},
        15: {"type": "trail", "item_id": "trail_season_cosmic", "name": "Season Cosmic Trail"},
        16: {"type": "gems", "amount": 100, "name": "100 Stellar Gems"},
        17: {"type": "decoration", "item_id": "deco_season_banner", "name": "Season Banner"},
        18: {"type": "gems", "amount": 100, "name": "100 Stellar Gems"},
        19: {"type": "effect", "item_id": "effect_season_aura", "name": "Season Aura Effect"},
        20: {"type": "skin", "item_id": "skin_season_omega", "name": "Season Skin: Omega"},
        21: {"type": "gems", "amount": 125, "name": "125 Stellar Gems"},
        22: {"type": "outfit", "item_id": "outfit_season_jin", "name": "Season Outfit: Jin"},
        23: {"type": "gems", "amount": 125, "name": "125 Stellar Gems"},
        24: {"type": "gems", "amount": 150, "name": "150 Stellar Gems"},
        25: {"type": "trail", "item_id": "trail_season_prismatic", "name": "Season Prismatic Trail"},
        26: {"type": "gems", "amount": 150, "name": "150 Stellar Gems"},
        27: {"type": "decoration", "item_id": "deco_season_trophy", "name": "Season Trophy"},
        28: {"type": "gems", "amount": 200, "name": "200 Stellar Gems"},
        29: {"type": "effect", "item_id": "effect_season_constellation", "name": "Season Constellation Effect"},
        30: {"type": "skin", "item_id": "skin_season_legendary", "name": "Season Legendary Skin"},
    }

    for tier_num in range(1, TOTAL_TIERS + 1):
        tiers.append({
            "tier": tier_num,
            "xp_required": tier_num * XP_PER_TIER,
            "free_reward": free_rewards.get(tier_num, {"type": "stardust", "amount": 50, "name": "50 Stardust"}),
            "premium_reward": premium_rewards.get(tier_num, {"type": "gems", "amount": 25, "name": "25 Stellar Gems"}),
        })

    return tiers


# Cache built tiers
REWARD_TIERS = _build_reward_tiers()


# ────────────────────────────────────────────────────────────────
# Monthly Cosmetic Rotation (Stellar Premium)
# ────────────────────────────────────────────────────────────────

MONTHLY_COSMETICS: Dict[int, dict] = {
    1: {"cosmetic_id": "monthly_nebula_frame", "name": "Nebula Frame", "type": "decoration"},
    2: {"cosmetic_id": "monthly_aurora_trail", "name": "Aurora Trail", "type": "trail"},
    3: {"cosmetic_id": "monthly_stellar_glow", "name": "Stellar Glow", "type": "effect"},
    4: {"cosmetic_id": "monthly_cosmic_badge", "name": "Cosmic Badge", "type": "decoration"},
    5: {"cosmetic_id": "monthly_void_trail", "name": "Void Trail", "type": "trail"},
    6: {"cosmetic_id": "monthly_pulsar_effect", "name": "Pulsar Effect", "type": "effect"},
    7: {"cosmetic_id": "monthly_quasar_frame", "name": "Quasar Frame", "type": "decoration"},
    8: {"cosmetic_id": "monthly_comet_trail", "name": "Comet Trail", "type": "trail"},
    9: {"cosmetic_id": "monthly_eclipse_glow", "name": "Eclipse Glow", "type": "effect"},
    10: {"cosmetic_id": "monthly_starfall_badge", "name": "Starfall Badge", "type": "decoration"},
    11: {"cosmetic_id": "monthly_horizon_trail", "name": "Horizon Trail", "type": "trail"},
    12: {"cosmetic_id": "monthly_singularity_effect", "name": "Singularity Effect", "type": "effect"},
}


# ────────────────────────────────────────────────────────────────
# Data Model
# ────────────────────────────────────────────────────────────────

@dataclass
class SubscriptionState:
    """Per-product subscription state."""
    product_id: str
    active: bool = False
    start_date: str = ""       # ISO date
    end_date: str = ""         # ISO date
    auto_renew: bool = True
    receipt_ids: List[str] = field(default_factory=list)


@dataclass
class SeasonProgress:
    """Player's season battle pass progress."""
    season_id: str = ""
    season_xp: int = 0
    current_tier: int = 0
    claimed_free: List[int] = field(default_factory=list)
    claimed_premium: List[int] = field(default_factory=list)
    xp_history: List[dict] = field(default_factory=list)


@dataclass
class CosmicPassData:
    """Complete cosmic pass data for a player."""
    player_id: str
    subscriptions: Dict[str, SubscriptionState] = field(default_factory=dict)
    season_progress: SeasonProgress = field(default_factory=SeasonProgress)
    claimed_monthly_cosmetics: List[str] = field(default_factory=list)
    created_at: str = ""


# ────────────────────────────────────────────────────────────────
# Persistence
# ────────────────────────────────────────────────────────────────

def _pass_path(player_id: str) -> Path:
    safe_id = _sanitize_player_id(player_id)
    return PASS_DIR / f"{safe_id}.json"


def _load_pass_data(player_id: str) -> CosmicPassData:
    """Load cosmic pass data for a player."""
    path = _pass_path(player_id)
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                d = json.load(f)

            subs = {}
            for prod_id, sub_data in d.get("subscriptions", {}).items():
                subs[prod_id] = SubscriptionState(
                    product_id=prod_id,
                    active=sub_data.get("active", False),
                    start_date=sub_data.get("start_date", ""),
                    end_date=sub_data.get("end_date", ""),
                    auto_renew=sub_data.get("auto_renew", True),
                    receipt_ids=sub_data.get("receipt_ids", []),
                )

            sp = d.get("season_progress", {})
            season = SeasonProgress(
                season_id=sp.get("season_id", ""),
                season_xp=sp.get("season_xp", 0),
                current_tier=sp.get("current_tier", 0),
                claimed_free=sp.get("claimed_free", []),
                claimed_premium=sp.get("claimed_premium", []),
                xp_history=sp.get("xp_history", [])[-100:],
            )

            return CosmicPassData(
                player_id=player_id,
                subscriptions=subs,
                season_progress=season,
                claimed_monthly_cosmetics=d.get("claimed_monthly_cosmetics", []),
                created_at=d.get("created_at", ""),
            )
        except (json.JSONDecodeError, IOError, TypeError):
            pass

    now = datetime.utcnow().isoformat()
    return CosmicPassData(
        player_id=player_id,
        subscriptions={},
        season_progress=SeasonProgress(),
        claimed_monthly_cosmetics=[],
        created_at=now,
    )


def _save_pass_data(data: CosmicPassData) -> None:
    """Save cosmic pass data for a player."""
    _ensure_dir(PASS_DIR)
    path = _pass_path(data.player_id)

    subs_serialized = {}
    for prod_id, sub in data.subscriptions.items():
        subs_serialized[prod_id] = {
            "product_id": sub.product_id,
            "active": sub.active,
            "start_date": sub.start_date,
            "end_date": sub.end_date,
            "auto_renew": sub.auto_renew,
            "receipt_ids": sub.receipt_ids,
        }

    d = {
        "player_id": data.player_id,
        "subscriptions": subs_serialized,
        "season_progress": {
            "season_id": data.season_progress.season_id,
            "season_xp": data.season_progress.season_xp,
            "current_tier": data.season_progress.current_tier,
            "claimed_free": data.season_progress.claimed_free,
            "claimed_premium": data.season_progress.claimed_premium,
            "xp_history": data.season_progress.xp_history[-100:],
        },
        "claimed_monthly_cosmetics": data.claimed_monthly_cosmetics,
        "created_at": data.created_at,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2)


# ────────────────────────────────────────────────────────────────
# Subscription Lifecycle Helpers [KAI]
# ────────────────────────────────────────────────────────────────

def _receipt_hash(receipt_data: str) -> str:
    """Generate a deterministic hash for receipt deduplication."""
    return hashlib.sha256(receipt_data.encode("utf-8")).hexdigest()[:32]


def _is_subscription_active(sub: SubscriptionState) -> bool:
    """Check if a subscription is currently active (including grace period)."""
    if not sub.active or not sub.end_date:
        return False
    today = date.today()
    end = date.fromisoformat(sub.end_date)
    grace_end = end + timedelta(days=GRACE_PERIOD_DAYS)
    return today <= grace_end


def _is_in_grace_period(sub: SubscriptionState) -> bool:
    """Check if subscription is in the grace period (expired but within 3 days)."""
    if not sub.active or not sub.end_date:
        return False
    today = date.today()
    end = date.fromisoformat(sub.end_date)
    return today > end and today <= end + timedelta(days=GRACE_PERIOD_DAYS)


def _expire_stale_subscriptions(data: CosmicPassData) -> None:
    """Mark subscriptions as inactive if past grace period."""
    today = date.today()
    for prod_id, sub in data.subscriptions.items():
        if sub.active and sub.end_date:
            end = date.fromisoformat(sub.end_date)
            grace_end = end + timedelta(days=GRACE_PERIOD_DAYS)
            if today > grace_end:
                sub.active = False


def _ensure_season_current(data: CosmicPassData) -> None:
    """Reset season progress if we've entered a new season."""
    season = _current_season()
    if data.season_progress.season_id != season["season_id"]:
        data.season_progress = SeasonProgress(
            season_id=season["season_id"],
            season_xp=0,
            current_tier=0,
            claimed_free=[],
            claimed_premium=[],
            xp_history=[],
        )


# ────────────────────────────────────────────────────────────────
# Benefits Aggregator [PREC-016-D]
# ────────────────────────────────────────────────────────────────

def get_active_benefits(player_id: str) -> dict:
    """Central benefits aggregator consumed by all systems.

    Returns a dict of active benefits based on subscription state.
    Used by streaks.py for freeze allocation, ads system, events, etc.

    Args:
        player_id: Player identifier.

    Returns:
        Dict with all active benefit flags and values.
    """
    data = _load_pass_data(player_id)
    _expire_stale_subscriptions(data)

    has_pass = False
    has_premium = False

    pass_sub = data.subscriptions.get("cosmic_pass")
    if pass_sub and _is_subscription_active(pass_sub):
        has_pass = True

    premium_sub = data.subscriptions.get("stellar_premium")
    if premium_sub and _is_subscription_active(premium_sub):
        has_premium = True

    # Freeze allocation: premium > pass > free
    if has_premium:
        freeze_alloc = PREMIUM_FREEZES_PER_WEEK
    elif has_pass:
        freeze_alloc = PASS_FREEZES_PER_WEEK
    else:
        freeze_alloc = FREE_FREEZES_PER_WEEK

    # Monthly cosmetic check
    month = date.today().month
    month_cosmetic = MONTHLY_COSMETICS.get(month)
    monthly_available = (
        has_premium
        and month_cosmetic is not None
        and month_cosmetic["cosmetic_id"] not in data.claimed_monthly_cosmetics
    )

    return {
        "has_cosmic_pass": has_pass,
        "has_stellar_premium": has_premium,
        "ad_free": has_premium,
        "reduced_ads": has_pass and not has_premium,
        "bonus_daily_missions": 1 if has_pass else 0,
        "weekly_freeze_allocation": freeze_alloc,
        "early_event_access_minutes": 60 if (has_pass or has_premium) else 0,
        "extra_weekly_mission": has_premium,
        "monthly_cosmetic_available": monthly_available,
    }


# ────────────────────────────────────────────────────────────────
# Public API — GET Endpoints
# ────────────────────────────────────────────────────────────────

def get_pass_status(player_id: str) -> dict:
    """Get subscription status for both products.

    Returns:
        Dict with subscription states, grace period info.
    """
    data = _load_pass_data(player_id)
    _expire_stale_subscriptions(data)
    _save_pass_data(data)

    result = {"player_id": player_id, "subscriptions": {}}

    for prod_id in ("cosmic_pass", "stellar_premium"):
        sub = data.subscriptions.get(prod_id)
        if sub:
            active = _is_subscription_active(sub)
            in_grace = _is_in_grace_period(sub)
            result["subscriptions"][prod_id] = {
                "active": active,
                "in_grace_period": in_grace,
                "start_date": sub.start_date,
                "end_date": sub.end_date,
                "auto_renew": sub.auto_renew,
                "status": "grace" if in_grace else ("active" if active else "expired"),
            }
        else:
            result["subscriptions"][prod_id] = {
                "active": False,
                "in_grace_period": False,
                "start_date": "",
                "end_date": "",
                "auto_renew": False,
                "status": "none",
            }

    return result


def get_season_info() -> dict:
    """Get current season information.

    Returns:
        Dict with season ID, dates, tier count, XP requirements.
    """
    return _current_season()


def get_season_progress(player_id: str) -> dict:
    """Get player's season progress — tier, XP, claimed rewards.

    Returns:
        Dict with current tier, XP, progress percentage.
    """
    data = _load_pass_data(player_id)
    _expire_stale_subscriptions(data)
    _ensure_season_current(data)
    _save_pass_data(data)

    season = _current_season()
    sp = data.season_progress
    total_xp_needed = TOTAL_TIERS * XP_PER_TIER
    next_tier_xp = (sp.current_tier + 1) * XP_PER_TIER if sp.current_tier < TOTAL_TIERS else total_xp_needed

    return {
        "player_id": player_id,
        "season_id": season["season_id"],
        "season_name": season["season_name"],
        "season_xp": sp.season_xp,
        "current_tier": sp.current_tier,
        "next_tier_xp": next_tier_xp,
        "xp_to_next_tier": max(0, next_tier_xp - sp.season_xp),
        "total_tiers": TOTAL_TIERS,
        "progress_pct": round(min(100.0, (sp.season_xp / total_xp_needed) * 100), 1),
        "max_tier_reached": sp.current_tier >= TOTAL_TIERS,
        "claimed_free_count": len(sp.claimed_free),
        "claimed_premium_count": len(sp.claimed_premium),
        "days_remaining": season["days_remaining"],
    }


def get_season_rewards(player_id: str) -> dict:
    """Get all 30 tiers with claim status for both tracks.

    Returns:
        Dict with tier list showing free/premium rewards and claim states.
    """
    data = _load_pass_data(player_id)
    _expire_stale_subscriptions(data)
    _ensure_season_current(data)

    sp = data.season_progress
    has_pass = False
    pass_sub = data.subscriptions.get("cosmic_pass")
    if pass_sub and _is_subscription_active(pass_sub):
        has_pass = True

    tiers = []
    for tier_data in REWARD_TIERS:
        tier_num = tier_data["tier"]
        unlocked = sp.current_tier >= tier_num

        free_status = "locked"
        if tier_num in sp.claimed_free:
            free_status = "claimed"
        elif unlocked:
            free_status = "available"

        premium_status = "locked"
        if tier_num in sp.claimed_premium:
            premium_status = "claimed"
        elif unlocked and has_pass:
            premium_status = "available"
        elif unlocked and not has_pass:
            premium_status = "requires_pass"

        tiers.append({
            "tier": tier_num,
            "xp_required": tier_data["xp_required"],
            "unlocked": unlocked,
            "free_reward": tier_data["free_reward"],
            "free_status": free_status,
            "premium_reward": tier_data["premium_reward"],
            "premium_status": premium_status,
        })

    return {
        "player_id": player_id,
        "season_id": sp.season_id,
        "current_tier": sp.current_tier,
        "has_cosmic_pass": has_pass,
        "tiers": tiers,
    }


def get_pass_benefits(player_id: str) -> dict:
    """Get active benefits summary for a player.

    Returns:
        Dict with all active benefit flags and values.
    """
    benefits = get_active_benefits(player_id)
    benefits["player_id"] = player_id
    return benefits


def get_subscription_products() -> dict:
    """Get subscription product definitions.

    Returns:
        Dict with available subscription products.
    """
    products = []
    for prod_id, prod in SUBSCRIPTION_PRODUCTS.items():
        products.append({
            "product_id": prod_id,
            "name": prod["name"],
            "description": prod["description"],
            "price_usd": prod["price_usd"],
            "duration_days": prod["duration_days"],
            "benefits": prod["benefits"],
        })
    return {"products": products}


# ────────────────────────────────────────────────────────────────
# Public API — POST Endpoints
# ────────────────────────────────────────────────────────────────

def subscribe(player_id: str, product_id: str, receipt_data: str, store: str = "apple") -> dict:
    """Subscribe to a product with receipt verification.

    Idempotent: re-subscribe extends from current end_date, not today.

    Args:
        player_id: Player identifier.
        product_id: "cosmic_pass" or "stellar_premium".
        receipt_data: Receipt string from app store.
        store: "apple" or "google".

    Returns:
        Dict with subscription result.
    """
    if product_id not in SUBSCRIPTION_PRODUCTS:
        return {"error": f"Unknown product: {product_id}"}

    if store not in ("apple", "google"):
        return {"error": f"Unknown store: {store}. Use 'apple' or 'google'."}

    if not receipt_data:
        return {"error": "receipt_data is required"}

    data = _load_pass_data(player_id)
    _expire_stale_subscriptions(data)

    # Receipt deduplication [KAI]
    receipt_id = _receipt_hash(receipt_data)
    sub = data.subscriptions.get(product_id)
    if sub and receipt_id in sub.receipt_ids:
        return {"error": "receipt_already_redeemed", "receipt_id": receipt_id}

    product = SUBSCRIPTION_PRODUCTS[product_id]

    if STUB_MODE:
        # Stub: accept any receipt
        today = date.today()

        if sub and sub.active and sub.end_date:
            # Idempotent: extend from current end_date
            current_end = date.fromisoformat(sub.end_date)
            new_start = max(today, current_end)
        else:
            new_start = today

        new_end = new_start + timedelta(days=product["duration_days"])

        if sub is None:
            sub = SubscriptionState(product_id=product_id)
            data.subscriptions[product_id] = sub

        sub.active = True
        sub.start_date = today.isoformat() if not sub.start_date else sub.start_date
        sub.end_date = new_end.isoformat()
        sub.auto_renew = True
        sub.receipt_ids.append(receipt_id)

        # For cosmic_pass, ensure season progress is initialized
        if product_id == "cosmic_pass":
            _ensure_season_current(data)

        _save_pass_data(data)

        return {
            "success": True,
            "stub_mode": True,
            "product_id": product_id,
            "product_name": product["name"],
            "start_date": sub.start_date,
            "end_date": sub.end_date,
            "auto_renew": sub.auto_renew,
            "receipt_id": receipt_id,
            "message": f"Welcome aboard! {product['name']} is now active.",
        }
    else:
        return {
            "error": "production_iap_not_implemented",
            "message": "Subscription verification requires Apple/Google API integration.",
        }


def verify_subscription_receipt(player_id: str, product_id: str, receipt_data: str, store: str = "apple") -> dict:
    """Verify a renewal receipt for an existing subscription.

    Used when the app store sends a renewal notification.

    Args:
        player_id: Player identifier.
        product_id: "cosmic_pass" or "stellar_premium".
        receipt_data: Receipt string from app store.
        store: "apple" or "google".

    Returns:
        Dict with verification result.
    """
    if product_id not in SUBSCRIPTION_PRODUCTS:
        return {"error": f"Unknown product: {product_id}"}

    data = _load_pass_data(player_id)
    sub = data.subscriptions.get(product_id)

    if sub is None:
        return {"error": f"No subscription found for {product_id}. Use /subscribe first."}

    # Receipt dedup
    receipt_id = _receipt_hash(receipt_data)
    if receipt_id in sub.receipt_ids:
        return {"error": "receipt_already_redeemed", "receipt_id": receipt_id}

    if STUB_MODE:
        product = SUBSCRIPTION_PRODUCTS[product_id]
        current_end = date.fromisoformat(sub.end_date) if sub.end_date else date.today()
        new_end = max(current_end, date.today()) + timedelta(days=product["duration_days"])

        sub.active = True
        sub.end_date = new_end.isoformat()
        sub.auto_renew = True
        sub.receipt_ids.append(receipt_id)

        _save_pass_data(data)

        return {
            "success": True,
            "stub_mode": True,
            "product_id": product_id,
            "new_end_date": sub.end_date,
            "receipt_id": receipt_id,
            "message": f"Subscription renewed. {product['name']} extended to {sub.end_date}.",
        }
    else:
        return {
            "error": "production_iap_not_implemented",
            "message": "Renewal verification requires Apple/Google API integration.",
        }


def cancel_subscription(player_id: str, product_id: str) -> dict:
    """Cancel auto-renewal. Benefits persist until end_date.

    Args:
        player_id: Player identifier.
        product_id: "cosmic_pass" or "stellar_premium".

    Returns:
        Dict with cancellation result.
    """
    if product_id not in SUBSCRIPTION_PRODUCTS:
        return {"error": f"Unknown product: {product_id}"}

    data = _load_pass_data(player_id)
    sub = data.subscriptions.get(product_id)

    if sub is None or not sub.active:
        return {"error": f"No active subscription for {product_id}"}

    sub.auto_renew = False
    _save_pass_data(data)

    return {
        "success": True,
        "product_id": product_id,
        "end_date": sub.end_date,
        "message": f"Auto-renewal cancelled. Your benefits continue until {sub.end_date}. The station thanks you for your time among the stars.",
    }


def claim_tier_reward(player_id: str, tier: int, track: str = "free") -> dict:
    """Claim a battle pass tier reward (free or premium track).

    Args:
        player_id: Player identifier.
        tier: Tier number (1-30).
        track: "free" or "premium".

    Returns:
        Dict with claimed reward details.
    """
    if tier < 1 or tier > TOTAL_TIERS:
        return {"error": f"Invalid tier: {tier}. Must be 1-{TOTAL_TIERS}."}

    if track not in ("free", "premium"):
        return {"error": f"Invalid track: {track}. Use 'free' or 'premium'."}

    data = _load_pass_data(player_id)
    _expire_stale_subscriptions(data)
    _ensure_season_current(data)

    sp = data.season_progress

    # Check tier unlocked
    if sp.current_tier < tier:
        return {
            "error": "tier_locked",
            "current_tier": sp.current_tier,
            "required_tier": tier,
        }

    # Get reward data
    tier_data = REWARD_TIERS[tier - 1]

    if track == "free":
        if tier in sp.claimed_free:
            return {"error": "already_claimed", "tier": tier, "track": "free"}

        reward = tier_data["free_reward"]
        sp.claimed_free.append(tier)

        # Apply free rewards
        _apply_reward(player_id, reward)

    else:  # premium
        # Check cosmic pass ownership
        pass_sub = data.subscriptions.get("cosmic_pass")
        if not pass_sub or not _is_subscription_active(pass_sub):
            return {"error": "requires_cosmic_pass", "message": "Premium track requires an active Cosmic Pass."}

        if tier in sp.claimed_premium:
            return {"error": "already_claimed", "tier": tier, "track": "premium"}

        reward = tier_data["premium_reward"]
        sp.claimed_premium.append(tier)

        # Apply premium rewards
        _apply_reward(player_id, reward)

    _save_pass_data(data)

    return {
        "success": True,
        "tier": tier,
        "track": track,
        "reward": reward,
        "message": f"Tier {tier} {track} reward claimed: {reward['name']}",
    }


def _apply_reward(player_id: str, reward: dict) -> None:
    """Apply a tier reward to the player's account."""
    reward_type = reward.get("type", "")

    if reward_type == "stardust":
        try:
            from narrative_agentic.stellar_outreach.station_modules import get_station, save_station
            station = get_station(player_id)
            if station:
                station.resources["stardust"] = station.resources.get("stardust", 0) + reward["amount"]
                save_station(station)
        except Exception:
            pass

    elif reward_type == "resources":
        try:
            from narrative_agentic.stellar_outreach.station_modules import get_station, save_station
            station = get_station(player_id)
            if station:
                for resource, amount in reward.get("data", {}).items():
                    station.resources[resource] = station.resources.get(resource, 0) + amount
                save_station(station)
        except Exception:
            pass

    elif reward_type == "gems":
        try:
            from narrative_agentic.stellar_outreach.cosmetic_store import _load_wallet, _save_wallet
            wallet = _load_wallet(player_id)
            wallet.stellar_gems += reward["amount"]
            _save_wallet(wallet)
        except Exception:
            pass

    elif reward_type == "freeze":
        try:
            from narrative_agentic.stellar_outreach.streaks import _load_streak_data, _save_streak_data
            streak = _load_streak_data(player_id)
            streak.freezes_available += reward["amount"]
            _save_streak_data(streak)
        except Exception:
            pass

    # Cosmetic types (skin, trail, effect, decoration, outfit, title)
    # are recorded by the claim itself — the frontend reads claim status


def earn_season_xp(player_id: str, source: str, amount: Optional[int] = None) -> dict:
    """Award season XP from a validated source.

    Args:
        player_id: Player identifier.
        source: XP source key (must be in XP_SOURCES whitelist).
        amount: Override XP amount (defaults to source's defined amount).

    Returns:
        Dict with updated XP and tier info.
    """
    if source not in XP_SOURCES:
        return {"error": f"Invalid XP source: {source}. Valid: {list(XP_SOURCES.keys())}"}

    # Bonus mission requires cosmic pass
    if source == "bonus_mission":
        benefits = get_active_benefits(player_id)
        if not benefits["has_cosmic_pass"]:
            return {"error": "Bonus mission XP requires an active Cosmic Pass."}

    xp_award = amount if amount is not None else XP_SOURCES[source]
    if xp_award <= 0:
        return {"error": "XP amount must be positive"}

    data = _load_pass_data(player_id)
    _expire_stale_subscriptions(data)
    _ensure_season_current(data)

    sp = data.season_progress
    old_tier = sp.current_tier
    sp.season_xp += xp_award

    # Recalculate tier
    new_tier = min(TOTAL_TIERS, sp.season_xp // XP_PER_TIER)
    sp.current_tier = new_tier
    tiers_gained = new_tier - old_tier

    # Log XP event
    sp.xp_history.append({
        "source": source,
        "amount": xp_award,
        "timestamp": datetime.utcnow().isoformat(),
        "tier_after": new_tier,
    })

    _save_pass_data(data)

    result = {
        "success": True,
        "source": source,
        "xp_awarded": xp_award,
        "total_xp": sp.season_xp,
        "current_tier": new_tier,
        "tiers_gained": tiers_gained,
    }

    if tiers_gained > 0:
        result["message"] = f"+{xp_award} XP! Advanced to Tier {new_tier}!"
        result["new_tiers"] = list(range(old_tier + 1, new_tier + 1))
    else:
        next_tier_xp = (new_tier + 1) * XP_PER_TIER if new_tier < TOTAL_TIERS else TOTAL_TIERS * XP_PER_TIER
        result["message"] = f"+{xp_award} XP ({sp.season_xp}/{next_tier_xp} to next tier)"
        result["xp_to_next_tier"] = max(0, next_tier_xp - sp.season_xp)

    return result


def claim_monthly_cosmetic(player_id: str) -> dict:
    """Claim the Stellar Premium monthly exclusive cosmetic.

    Each month has a unique cosmetic. Can only claim once per month.
    Framed as a "gift" not "loss if missed". [ELENA]

    Args:
        player_id: Player identifier.

    Returns:
        Dict with claimed cosmetic details.
    """
    data = _load_pass_data(player_id)
    _expire_stale_subscriptions(data)

    # Check premium active
    premium_sub = data.subscriptions.get("stellar_premium")
    if not premium_sub or not _is_subscription_active(premium_sub):
        return {"error": "Requires an active Stellar Premium subscription."}

    month = date.today().month
    cosmetic = MONTHLY_COSMETICS.get(month)
    if cosmetic is None:
        return {"error": "No monthly cosmetic available for this month."}

    cosmetic_id = cosmetic["cosmetic_id"]
    if cosmetic_id in data.claimed_monthly_cosmetics:
        return {
            "error": "already_claimed",
            "cosmetic_id": cosmetic_id,
            "cosmetic_name": cosmetic["name"],
            "message": f"You've already received this month's gift: {cosmetic['name']}.",
        }

    data.claimed_monthly_cosmetics.append(cosmetic_id)
    _save_pass_data(data)

    return {
        "success": True,
        "cosmetic_id": cosmetic_id,
        "cosmetic_name": cosmetic["name"],
        "cosmetic_type": cosmetic["type"],
        "month": month,
        "message": f"A gift from the cosmos: {cosmetic['name']}. Thank you for being part of the station.",
    }

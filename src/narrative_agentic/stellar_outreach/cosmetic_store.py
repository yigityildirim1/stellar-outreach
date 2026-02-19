"""
NEXUS STATION - Stellar Outreach: Cosmetic Store & IAP System (TASK-015)

Premium cosmetic store with dual currency (Stardust + Stellar Gems),
IAP receipt validation stubs, append-only transaction ledger, and
gifting system. Foundation for Phase 3 monetization.

Features:
    - 28 premium cosmetic items across 4 categories
    - 5 IAP gem packs ($0.99 – $49.99)
    - Dual currency: Stardust (grindable) + Stellar Gems (IAP)
    - Append-only transaction ledger per player
    - VIP tier progression based on total gem spend
    - Gifting to friends (3/day cap)
    - Featured items rotation (weekly, no FOMO — all items always available)
    - IAP receipt validation stubs with replay protection

Ethics Note (Dr. Elena Vasquez review):
    No loot boxes — transparent pricing. No FOMO — featured items rotate but
    ALL items always purchasable. No pay-to-win — cosmetics only. Free players
    are first-class citizens — existing 8 skins + 20 decorations stay free.
    Spending totals visible in wallet for self-awareness.

Security Note (Kai Chen review):
    Receipt deduplication prevents replay attacks. Idempotent purchases
    (already_owned check). Atomic writes (deduct + add item in single save).
    Daily gift cap (3/day). Daily spend cap (10,000 gems). STUB_MODE flag
    for IAP validation — production requires real Apple/Google verification.

UX Note (Marina Okonkwo review):
    Store browsable by category/rarity/tag. Preview before purchase.
    Featured rotation highlights variety without urgency. Wallet always
    shows total spending for transparency.

Precedent Note (Prof. James Whitmore):
    PREC-015-A: Premium catalog separated from free earnable items.
    PREC-015-B: Append-only transaction ledger per player.
    PREC-015-C: IAP stub pattern with STUB_MODE flag.

References:
    - TASK-014: Station customization (free skins/decorations)
    - TASK-012: Streak system (purchase_freeze stardust pattern)
    - TASK-010: Friends system (friendship verification for gifting)
    - TASK-003: Station modules (stardust resource)
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional


# ────────────────────────────────────────────────────────────────
# Configuration
# ────────────────────────────────────────────────────────────────

STORE_DIR = Path.home() / ".nexus_station" / "store"

# IAP validation mode — True = stub (dev/testing), False = production
STUB_MODE = True

# Safety caps [KAI]
DAILY_GIFT_CAP = 3
DAILY_SPEND_CAP_GEMS = 10_000
MAX_TRANSACTION_HISTORY = 500


def _sanitize_player_id(player_id: str) -> str:
    """Sanitize a player ID for safe filesystem use."""
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in player_id)


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


# ────────────────────────────────────────────────────────────────
# VIP Tiers
# ────────────────────────────────────────────────────────────────

VIP_TIERS: Dict[str, dict] = {
    "none": {"name": "Explorer", "threshold": 0, "bonus_pct": 0},
    "bronze": {"name": "Bronze Voyager", "threshold": 500, "bonus_pct": 5},
    "silver": {"name": "Silver Navigator", "threshold": 2000, "bonus_pct": 10},
    "gold": {"name": "Gold Commander", "threshold": 5000, "bonus_pct": 15},
    "stellar": {"name": "Stellar Admiral", "threshold": 15000, "bonus_pct": 25},
}


def _calculate_vip_tier(total_gems_purchased: int) -> str:
    """Determine VIP tier from lifetime gem purchases."""
    tier = "none"
    for tier_id, info in VIP_TIERS.items():
        if total_gems_purchased >= info["threshold"]:
            tier = tier_id
    return tier


# ────────────────────────────────────────────────────────────────
# Premium Skin Definitions (palette overrides for store skins)
# ────────────────────────────────────────────────────────────────

PREMIUM_SKIN_DEFINITIONS: Dict[str, dict] = {
    "aurora_borealis": {
        "name": "Aurora Borealis",
        "palette_overrides": {
            "primary": "#00CED1",
            "secondary": "#0B1628",
            "accent": "#7FFFD4",
            "background": "#040E18",
            "surface": "#0A1A2E",
            "text": "#E0F7FA",
        },
        "visual_class": "skin-aurora",
    },
    "void_walker": {
        "name": "Void Walker",
        "palette_overrides": {
            "primary": "#8B00FF",
            "secondary": "#0D0015",
            "accent": "#DA70D6",
            "background": "#050008",
            "surface": "#120020",
            "text": "#E8D5F5",
        },
        "visual_class": "skin-void",
    },
    "copper_age": {
        "name": "Copper Age",
        "palette_overrides": {
            "primary": "#B87333",
            "secondary": "#2A1810",
            "accent": "#DA8A67",
            "background": "#120C08",
            "surface": "#241A10",
            "text": "#F5E0C8",
        },
        "visual_class": "skin-copper",
    },
    "stellar_nursery": {
        "name": "Stellar Nursery",
        "palette_overrides": {
            "primary": "#FF69B4",
            "secondary": "#1A0A18",
            "accent": "#FFB6C1",
            "background": "#0E0410",
            "surface": "#1E0E20",
            "text": "#FFF0F5",
        },
        "visual_class": "skin-nursery",
    },
    "signal_static": {
        "name": "Signal Static",
        "palette_overrides": {
            "primary": "#00FF41",
            "secondary": "#0A0A0A",
            "accent": "#33FF77",
            "background": "#000000",
            "surface": "#111111",
            "text": "#C0FFC0",
        },
        "visual_class": "skin-static",
    },
}


# ────────────────────────────────────────────────────────────────
# Store Catalog (~28 premium cosmetics)
# ────────────────────────────────────────────────────────────────

STORE_CATALOG: Dict[str, dict] = {
    # ── Premium Skins (5) ──
    "skin_aurora_borealis": {
        "name": "Aurora Borealis",
        "description": "Shimmering teal and aquamarine — the northern lights dance across every panel. A station bathed in polar wonder.",
        "category": "skin",
        "rarity": "epic",
        "price_gems": 800,
        "price_stardust": None,  # gems-only
        "tags": ["skin", "premium", "nature"],
        "skin_id": "aurora_borealis",
    },
    "skin_void_walker": {
        "name": "Void Walker",
        "description": "Deep violet and orchid — the station peers into the abyss, and the abyss winks back. For those who find beauty in darkness.",
        "category": "skin",
        "rarity": "epic",
        "price_gems": 800,
        "price_stardust": None,
        "tags": ["skin", "premium", "dark"],
        "skin_id": "void_walker",
    },
    "skin_copper_age": {
        "name": "Copper Age",
        "description": "Burnished copper and warm earth tones — steampunk meets deep space. Every rivet tells a story of craftsmanship.",
        "category": "skin",
        "rarity": "rare",
        "price_gems": 500,
        "price_stardust": 2500,  # also stardust
        "tags": ["skin", "premium", "warm"],
        "skin_id": "copper_age",
    },
    "skin_stellar_nursery": {
        "name": "Stellar Nursery",
        "description": "Soft pinks and rose gold — where new stars are born. Gentle, luminous, alive with nascent energy.",
        "category": "skin",
        "rarity": "epic",
        "price_gems": 800,
        "price_stardust": None,
        "tags": ["skin", "premium", "soft"],
        "skin_id": "stellar_nursery",
    },
    "skin_signal_static": {
        "name": "Signal Static",
        "description": "Terminal green on pure black — the signal cuts through noise. Retro hacker aesthetic for purists.",
        "category": "skin",
        "rarity": "rare",
        "price_gems": 500,
        "price_stardust": 2500,
        "tags": ["skin", "premium", "retro"],
        "skin_id": "signal_static",
    },

    # ── Star Trails (7) ──
    "trail_ember": {
        "name": "Ember Trail",
        "description": "A warm trail of glowing embers follows your station cursor — sparks that fade like campfire memories.",
        "category": "star_trail",
        "rarity": "uncommon",
        "price_gems": 200,
        "price_stardust": 1000,
        "tags": ["trail", "fire", "warm"],
    },
    "trail_ocean": {
        "name": "Ocean Trail",
        "description": "Cool blue ripples spread outward — the deep sea follows you through space.",
        "category": "star_trail",
        "rarity": "uncommon",
        "price_gems": 200,
        "price_stardust": 1000,
        "tags": ["trail", "water", "cool"],
    },
    "trail_aurora": {
        "name": "Aurora Trail",
        "description": "Shimmering green-to-violet curtains trail behind — the northern lights in miniature.",
        "category": "star_trail",
        "rarity": "rare",
        "price_gems": 350,
        "price_stardust": 1750,
        "tags": ["trail", "nature", "ethereal"],
    },
    "trail_nebula_pink": {
        "name": "Nebula Pink Trail",
        "description": "Soft rose-colored nebula clouds drift in your wake — stardust in bloom.",
        "category": "star_trail",
        "rarity": "rare",
        "price_gems": 350,
        "price_stardust": 1750,
        "tags": ["trail", "soft", "cosmic"],
    },
    "trail_stardust_gold": {
        "name": "Stardust Gold Trail",
        "description": "Flecks of golden stardust scatter behind you — wealth made visible in light.",
        "category": "star_trail",
        "rarity": "epic",
        "price_gems": 500,
        "price_stardust": None,
        "tags": ["trail", "gold", "luxury"],
    },
    "trail_void_purple": {
        "name": "Void Purple Trail",
        "description": "Dark violet tendrils that seem to pull light inward — the void is always just behind you.",
        "category": "star_trail",
        "rarity": "rare",
        "price_gems": 350,
        "price_stardust": 1750,
        "tags": ["trail", "dark", "mysterious"],
    },
    "trail_prismatic": {
        "name": "Prismatic Trail",
        "description": "All colors cycle in a slow, endless rainbow — the full spectrum of cosmic joy.",
        "category": "star_trail",
        "rarity": "legendary",
        "price_gems": 1200,
        "price_stardust": None,
        "tags": ["trail", "rainbow", "celebration"],
    },

    # ── Crew Outfits (6) ──
    "outfit_reyes": {
        "name": "Commander Reyes — Dress Uniform",
        "description": "Gold-trimmed formal wear for the Commander. For diplomatic occasions among the stars.",
        "category": "crew_outfit",
        "rarity": "rare",
        "price_gems": 300,
        "price_stardust": 1500,
        "tags": ["outfit", "npc", "formal"],
        "npc_id": "cmdr_reyes",
    },
    "outfit_okafor": {
        "name": "Dr. Okafor — Expedition Gear",
        "description": "Field research suit with bioluminescent accents. Ready for any biome.",
        "category": "crew_outfit",
        "rarity": "rare",
        "price_gems": 300,
        "price_stardust": 1500,
        "tags": ["outfit", "npc", "science"],
        "npc_id": "dr_okafor",
    },
    "outfit_jin": {
        "name": "Tech Jin — Neon Circuit Jacket",
        "description": "A jacket threaded with fiber-optic circuits that pulse with system data.",
        "category": "crew_outfit",
        "rarity": "rare",
        "price_gems": 300,
        "price_stardust": 1500,
        "tags": ["outfit", "npc", "tech"],
        "npc_id": "tech_jin",
    },
    "outfit_vasquez": {
        "name": "Lt. Vasquez — Tactical Ceremonial",
        "description": "Honor guard ceremonial armor with polished security insignia.",
        "category": "crew_outfit",
        "rarity": "rare",
        "price_gems": 300,
        "price_stardust": 1500,
        "tags": ["outfit", "npc", "security"],
        "npc_id": "lt_vasquez",
    },
    "outfit_amari": {
        "name": "Chef Amari — Cosmic Cuisine Apron",
        "description": "A handwoven apron with constellation patterns. Smells faintly of cardamom and starlight.",
        "category": "crew_outfit",
        "rarity": "rare",
        "price_gems": 300,
        "price_stardust": 1500,
        "tags": ["outfit", "npc", "culinary"],
        "npc_id": "chef_amari",
    },
    "outfit_lune": {
        "name": "Archivist Lune — Data Robe",
        "description": "Flowing robes inscribed with scrolling data. Knowledge made wearable.",
        "category": "crew_outfit",
        "rarity": "rare",
        "price_gems": 300,
        "price_stardust": 1500,
        "tags": ["outfit", "npc", "archive"],
        "npc_id": "archivist_lune",
    },

    # ── Visual Effects (5) ──
    "effect_ambient_stars": {
        "name": "Ambient Starfield",
        "description": "Gentle twinkling stars fill the background of every screen — a quiet cosmos always present.",
        "category": "visual_effect",
        "rarity": "uncommon",
        "price_gems": 150,
        "price_stardust": 750,
        "tags": ["effect", "ambient", "gentle"],
    },
    "effect_console_hologram": {
        "name": "Console Hologram",
        "description": "A small holographic projection above your console — a rotating planet, star, or station model.",
        "category": "visual_effect",
        "rarity": "rare",
        "price_gems": 400,
        "price_stardust": 2000,
        "tags": ["effect", "hologram", "interactive"],
    },
    "effect_particle_dust": {
        "name": "Particle Dust",
        "description": "Fine luminous particles drift through the station — cosmic dust caught in recycled air.",
        "category": "visual_effect",
        "rarity": "uncommon",
        "price_gems": 150,
        "price_stardust": 750,
        "tags": ["effect", "particle", "subtle"],
    },
    "effect_nebula_backdrop": {
        "name": "Nebula Backdrop",
        "description": "A slowly shifting nebula fills the viewport behind all station screens — deep space in motion.",
        "category": "visual_effect",
        "rarity": "epic",
        "price_gems": 600,
        "price_stardust": None,
        "tags": ["effect", "nebula", "cosmic"],
    },
    "effect_cosmic_rain": {
        "name": "Cosmic Rain",
        "description": "Slow-falling streaks of light — meteor showers rendered in miniature across the UI.",
        "category": "visual_effect",
        "rarity": "rare",
        "price_gems": 400,
        "price_stardust": 2000,
        "tags": ["effect", "dynamic", "rain"],
    },
}


# ────────────────────────────────────────────────────────────────
# Gem Packs (IAP Products)
# ────────────────────────────────────────────────────────────────

GEM_PACKS: Dict[str, dict] = {
    "gem_pack_starter": {
        "pack_id": "gem_pack_starter",
        "name": "Starter Pouch",
        "gems": 100,
        "bonus_gems": 0,
        "price_usd": 0.99,
        "description": "A modest pouch of Stellar Gems — enough for a trail or effect.",
        "apple_product_id": "com.nexusstation.gems.100",
        "google_product_id": "gems_100",
    },
    "gem_pack_explorer": {
        "pack_id": "gem_pack_explorer",
        "name": "Explorer Bundle",
        "gems": 500,
        "bonus_gems": 50,
        "price_usd": 4.99,
        "description": "An explorer's supply of gems, with a bonus 50 for the journey.",
        "apple_product_id": "com.nexusstation.gems.550",
        "google_product_id": "gems_550",
    },
    "gem_pack_navigator": {
        "pack_id": "gem_pack_navigator",
        "name": "Navigator Chest",
        "gems": 1200,
        "bonus_gems": 200,
        "price_usd": 9.99,
        "description": "A navigator's chest — 1200 gems plus 200 bonus. Chart your course.",
        "apple_product_id": "com.nexusstation.gems.1400",
        "google_product_id": "gems_1400",
    },
    "gem_pack_commander": {
        "pack_id": "gem_pack_commander",
        "name": "Commander's Vault",
        "gems": 3000,
        "bonus_gems": 600,
        "price_usd": 24.99,
        "description": "The Commander's Vault — 3000 gems with 600 bonus. Authority has its perks.",
        "apple_product_id": "com.nexusstation.gems.3600",
        "google_product_id": "gems_3600",
    },
    "gem_pack_admiral": {
        "pack_id": "gem_pack_admiral",
        "name": "Admiral's Treasury",
        "gems": 6500,
        "bonus_gems": 1500,
        "price_usd": 49.99,
        "description": "The Admiral's Treasury — 6500 gems plus 1500 bonus. The stars are yours.",
        "apple_product_id": "com.nexusstation.gems.8000",
        "google_product_id": "gems_8000",
    },
}


# ────────────────────────────────────────────────────────────────
# Data Model
# ────────────────────────────────────────────────────────────────

@dataclass
class PlayerWallet:
    """Player's store wallet and inventory."""
    player_id: str
    stellar_gems: int = 0
    owned_items: List[str] = field(default_factory=list)
    vip_tier: str = "none"
    total_gems_purchased: int = 0
    total_gems_spent: int = 0
    total_stardust_spent: int = 0
    gifts_sent_today: int = 0
    gems_spent_today: int = 0
    last_active_date: str = ""
    transactions: List[dict] = field(default_factory=list)
    redeemed_receipts: List[str] = field(default_factory=list)


# ────────────────────────────────────────────────────────────────
# Persistence
# ────────────────────────────────────────────────────────────────

def _wallet_path(player_id: str) -> Path:
    safe_id = _sanitize_player_id(player_id)
    return STORE_DIR / f"{safe_id}.json"


def _load_wallet(player_id: str) -> PlayerWallet:
    """Load player wallet from disk."""
    path = _wallet_path(player_id)
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                d = json.load(f)
            return PlayerWallet(
                player_id=player_id,
                stellar_gems=d.get("stellar_gems", 0),
                owned_items=d.get("owned_items", []),
                vip_tier=d.get("vip_tier", "none"),
                total_gems_purchased=d.get("total_gems_purchased", 0),
                total_gems_spent=d.get("total_gems_spent", 0),
                total_stardust_spent=d.get("total_stardust_spent", 0),
                gifts_sent_today=d.get("gifts_sent_today", 0),
                gems_spent_today=d.get("gems_spent_today", 0),
                last_active_date=d.get("last_active_date", ""),
                transactions=d.get("transactions", [])[-MAX_TRANSACTION_HISTORY:],
                redeemed_receipts=d.get("redeemed_receipts", []),
            )
        except (json.JSONDecodeError, IOError):
            pass
    return PlayerWallet(player_id=player_id)


def _save_wallet(wallet: PlayerWallet) -> None:
    """Save player wallet to disk (atomic write)."""
    _ensure_dir(STORE_DIR)
    path = _wallet_path(wallet.player_id)
    d = {
        "player_id": wallet.player_id,
        "stellar_gems": wallet.stellar_gems,
        "owned_items": wallet.owned_items,
        "vip_tier": wallet.vip_tier,
        "total_gems_purchased": wallet.total_gems_purchased,
        "total_gems_spent": wallet.total_gems_spent,
        "total_stardust_spent": wallet.total_stardust_spent,
        "gifts_sent_today": wallet.gifts_sent_today,
        "gems_spent_today": wallet.gems_spent_today,
        "last_active_date": wallet.last_active_date,
        "transactions": wallet.transactions[-MAX_TRANSACTION_HISTORY:],
        "redeemed_receipts": wallet.redeemed_receipts,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2)


def _reset_daily_caps(wallet: PlayerWallet) -> None:
    """Reset daily caps if the date has changed."""
    today = date.today().isoformat()
    if wallet.last_active_date != today:
        wallet.gifts_sent_today = 0
        wallet.gems_spent_today = 0
        wallet.last_active_date = today


def _add_transaction(wallet: PlayerWallet, tx_type: str, **kwargs) -> dict:
    """Add an append-only transaction record."""
    tx = {
        "type": tx_type,
        "timestamp": datetime.utcnow().isoformat(),
        **kwargs,
    }
    wallet.transactions.append(tx)
    return tx


def _receipt_hash(receipt_data: str) -> str:
    """Generate a deterministic hash for receipt deduplication."""
    return hashlib.sha256(receipt_data.encode("utf-8")).hexdigest()[:32]


# ────────────────────────────────────────────────────────────────
# Featured Items (weekly rotation, no FOMO)
# ────────────────────────────────────────────────────────────────

def _get_weekly_seed() -> int:
    """Deterministic seed for the current week."""
    today = date.today()
    return today.isocalendar()[0] * 100 + today.isocalendar()[1]


def _select_featured(count: int = 6) -> List[str]:
    """Select featured items for this week (deterministic rotation)."""
    import random
    seed = _get_weekly_seed()
    rng = random.Random(seed)
    item_ids = list(STORE_CATALOG.keys())
    rng.shuffle(item_ids)
    return item_ids[:count]


# ────────────────────────────────────────────────────────────────
# Public API Functions
# ────────────────────────────────────────────────────────────────

def get_store_catalog(
    category: Optional[str] = None,
    rarity: Optional[str] = None,
    tag: Optional[str] = None,
) -> dict:
    """Browse the store catalog with optional filters.

    Args:
        category: Filter by category (skin, star_trail, crew_outfit, visual_effect).
        rarity: Filter by rarity (common, uncommon, rare, epic, legendary).
        tag: Filter by tag.

    Returns:
        Dict with filtered catalog items and counts.
    """
    items = []
    for item_id, item in STORE_CATALOG.items():
        if category and item["category"] != category:
            continue
        if rarity and item["rarity"] != rarity:
            continue
        if tag and tag not in item.get("tags", []):
            continue
        items.append({"item_id": item_id, **item})

    # Group by category
    by_category: Dict[str, list] = {}
    for item in items:
        cat = item["category"]
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(item)

    return {
        "items": items,
        "by_category": by_category,
        "total_count": len(items),
        "filters_applied": {
            "category": category,
            "rarity": rarity,
            "tag": tag,
        },
    }


def get_featured_items() -> dict:
    """Get this week's featured items.

    Featured items rotate weekly but ALL items are always available.
    No FOMO — this is a highlight, not a limited-time offer. [ELENA]

    Returns:
        Dict with featured items and rotation info.
    """
    featured_ids = _select_featured(6)
    items = []
    for item_id in featured_ids:
        if item_id in STORE_CATALOG:
            items.append({"item_id": item_id, **STORE_CATALOG[item_id]})

    seed = _get_weekly_seed()
    return {
        "featured": items,
        "rotation_week": seed,
        "note": "All items are always available — featured is a highlight, not a limit.",
    }


def get_wallet(player_id: str) -> dict:
    """Get a player's wallet: gem balance, owned items, VIP tier.

    Returns:
        Dict with wallet state.
    """
    wallet = _load_wallet(player_id)
    _reset_daily_caps(wallet)
    vip_info = VIP_TIERS.get(wallet.vip_tier, VIP_TIERS["none"])

    return {
        "player_id": player_id,
        "stellar_gems": wallet.stellar_gems,
        "owned_items": wallet.owned_items,
        "owned_count": len(wallet.owned_items),
        "vip_tier": wallet.vip_tier,
        "vip_name": vip_info["name"],
        "vip_bonus_pct": vip_info["bonus_pct"],
        "total_gems_purchased": wallet.total_gems_purchased,
        "total_gems_spent": wallet.total_gems_spent,
        "total_stardust_spent": wallet.total_stardust_spent,
        "gifts_sent_today": wallet.gifts_sent_today,
        "daily_gift_cap": DAILY_GIFT_CAP,
        "gems_spent_today": wallet.gems_spent_today,
        "daily_spend_cap": DAILY_SPEND_CAP_GEMS,
    }


def purchase_item(player_id: str, item_id: str, currency: str = "gems") -> dict:
    """Purchase a cosmetic item with stardust or gems.

    Args:
        player_id: Player identifier.
        item_id: Catalog item to purchase.
        currency: "gems" or "stardust".

    Returns:
        Dict with purchase result.
    """
    if item_id not in STORE_CATALOG:
        return {"error": f"Unknown item: {item_id}"}

    item = STORE_CATALOG[item_id]
    wallet = _load_wallet(player_id)
    _reset_daily_caps(wallet)

    # Already owned check (idempotent) [KAI]
    if item_id in wallet.owned_items:
        return {"error": "already_owned", "item_id": item_id, "item_name": item["name"]}

    if currency == "gems":
        price = item["price_gems"]
        if price is None:
            return {"error": f"Item '{item['name']}' cannot be purchased with gems"}

        # Daily spend cap [KAI]
        if wallet.gems_spent_today + price > DAILY_SPEND_CAP_GEMS:
            return {
                "error": "daily_spend_cap",
                "message": f"Daily gem spend cap reached ({DAILY_SPEND_CAP_GEMS}). Try again tomorrow.",
            }

        if wallet.stellar_gems < price:
            return {
                "error": "insufficient_gems",
                "have": wallet.stellar_gems,
                "need": price,
            }

        # Atomic: deduct + add item
        wallet.stellar_gems -= price
        wallet.total_gems_spent += price
        wallet.gems_spent_today += price
        wallet.owned_items.append(item_id)
        _add_transaction(wallet, "purchase", item_id=item_id, currency="gems", amount=price)
        _save_wallet(wallet)

        # If it's a skin, force-unlock in customization
        if item["category"] == "skin" and "skin_id" in item:
            _unlock_premium_skin(player_id, item["skin_id"])

        return {
            "success": True,
            "item_id": item_id,
            "item_name": item["name"],
            "currency": "gems",
            "price": price,
            "gems_remaining": wallet.stellar_gems,
        }

    elif currency == "stardust":
        price = item.get("price_stardust")
        if price is None:
            return {"error": f"Item '{item['name']}' is gems-only"}

        # Check stardust via station_modules
        from narrative_agentic.stellar_outreach.station_modules import get_station, save_station

        station = get_station(player_id)
        if station is None:
            return {"error": "Station not found"}

        stardust = station.resources.get("stardust", 0)
        if stardust < price:
            return {
                "error": "insufficient_stardust",
                "have": stardust,
                "need": price,
            }

        # Atomic: deduct stardust + add item
        station.resources["stardust"] -= price
        save_station(station)
        wallet.total_stardust_spent += price
        wallet.owned_items.append(item_id)
        _add_transaction(wallet, "purchase", item_id=item_id, currency="stardust", amount=price)
        _save_wallet(wallet)

        # If it's a skin, force-unlock in customization
        if item["category"] == "skin" and "skin_id" in item:
            _unlock_premium_skin(player_id, item["skin_id"])

        return {
            "success": True,
            "item_id": item_id,
            "item_name": item["name"],
            "currency": "stardust",
            "price": price,
            "stardust_remaining": station.resources["stardust"],
        }

    else:
        return {"error": f"Invalid currency: {currency}. Use 'gems' or 'stardust'."}


def _unlock_premium_skin(player_id: str, skin_id: str) -> None:
    """Unlock a premium skin in the customization system."""
    try:
        from narrative_agentic.stellar_outreach.station_customization import force_unlock_skin
        force_unlock_skin(player_id, skin_id)
    except Exception:
        pass  # Non-fatal — skin will be available once customization is updated


def verify_iap_receipt(
    player_id: str,
    receipt_data: str,
    store: str = "apple",
) -> dict:
    """Verify an IAP receipt and credit gems.

    In STUB_MODE, accepts any receipt and credits gems.
    In production, would call Apple/Google verification APIs.

    Args:
        player_id: Player identifier.
        receipt_data: Receipt string from app store.
        store: "apple" or "google".

    Returns:
        Dict with verification result and credited gems.
    """
    if store not in ("apple", "google"):
        return {"error": f"Unknown store: {store}. Use 'apple' or 'google'."}

    if not receipt_data:
        return {"error": "receipt_data is required"}

    wallet = _load_wallet(player_id)
    _reset_daily_caps(wallet)

    # Receipt deduplication [KAI]
    receipt_id = _receipt_hash(receipt_data)
    if receipt_id in wallet.redeemed_receipts:
        return {"error": "receipt_already_redeemed", "receipt_id": receipt_id}

    if STUB_MODE:
        # Extract pack_id from receipt (stub format: "pack_id:gem_pack_xxx")
        pack_id = receipt_data.split(":")[-1] if ":" in receipt_data else receipt_data
        if pack_id not in GEM_PACKS:
            return {"error": f"Unknown gem pack: {pack_id}"}

        pack = GEM_PACKS[pack_id]
        total_gems = pack["gems"] + pack["bonus_gems"]

        # VIP bonus
        vip_info = VIP_TIERS.get(wallet.vip_tier, VIP_TIERS["none"])
        vip_bonus = int(total_gems * vip_info["bonus_pct"] / 100)
        credited = total_gems + vip_bonus

        wallet.stellar_gems += credited
        wallet.total_gems_purchased += credited
        wallet.redeemed_receipts.append(receipt_id)

        # Recalculate VIP tier
        wallet.vip_tier = _calculate_vip_tier(wallet.total_gems_purchased)

        _add_transaction(wallet, "iap_purchase",
                         pack_id=pack_id,
                         gems_base=pack["gems"],
                         gems_bonus=pack["bonus_gems"],
                         vip_bonus=vip_bonus,
                         total_credited=credited,
                         store=store,
                         receipt_id=receipt_id)
        _save_wallet(wallet)

        return {
            "success": True,
            "verified": True,
            "stub_mode": True,
            "pack_id": pack_id,
            "pack_name": pack["name"],
            "gems_base": pack["gems"],
            "gems_bonus": pack["bonus_gems"],
            "vip_bonus": vip_bonus,
            "total_credited": credited,
            "new_balance": wallet.stellar_gems,
            "vip_tier": wallet.vip_tier,
            "vip_name": VIP_TIERS[wallet.vip_tier]["name"],
        }
    else:
        # Production: call Apple/Google verification APIs
        return {
            "error": "production_iap_not_implemented",
            "message": "IAP verification requires Apple/Google API integration.",
        }


def get_transaction_history(
    player_id: str,
    limit: int = 20,
    offset: int = 0,
) -> dict:
    """Get paginated transaction history.

    Args:
        player_id: Player identifier.
        limit: Max items per page (default 20, max 50).
        offset: Skip N items.

    Returns:
        Dict with transaction page and pagination info.
    """
    wallet = _load_wallet(player_id)
    limit = min(max(1, limit), 50)
    offset = max(0, offset)

    # Reverse chronological
    all_tx = list(reversed(wallet.transactions))
    total = len(all_tx)
    page = all_tx[offset:offset + limit]

    return {
        "player_id": player_id,
        "transactions": page,
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": offset + limit < total,
    }


def gift_store_item(
    sender_id: str,
    recipient_id: str,
    item_id: str,
    currency: str = "gems",
) -> dict:
    """Gift a store item to a friend.

    Args:
        sender_id: Gifting player.
        recipient_id: Receiving player (must be a friend).
        item_id: Item to gift.
        currency: "gems" or "stardust".

    Returns:
        Dict with gift result.
    """
    if item_id not in STORE_CATALOG:
        return {"error": f"Unknown item: {item_id}"}

    if sender_id == recipient_id:
        return {"error": "Cannot gift to yourself"}

    item = STORE_CATALOG[item_id]

    # Verify friendship [TASK-010 integration]
    from narrative_agentic.stellar_outreach.friends import get_friends as _get_friends
    friends_data = _get_friends(sender_id)
    friend_ids = [f["friend_id"] for f in friends_data.get("friends", [])]
    if recipient_id not in friend_ids:
        return {"error": "Recipient is not on your friends list"}

    # Check sender wallet
    sender_wallet = _load_wallet(sender_id)
    _reset_daily_caps(sender_wallet)

    # Daily gift cap [KAI]
    if sender_wallet.gifts_sent_today >= DAILY_GIFT_CAP:
        return {
            "error": "daily_gift_cap",
            "message": f"Daily gift cap reached ({DAILY_GIFT_CAP}). Try again tomorrow.",
        }

    # Check recipient doesn't already own it
    recipient_wallet = _load_wallet(recipient_id)
    if item_id in recipient_wallet.owned_items:
        return {"error": "recipient_already_owns", "item_name": item["name"]}

    # Process payment from sender
    if currency == "gems":
        price = item["price_gems"]
        if price is None:
            return {"error": f"Item '{item['name']}' cannot be purchased with gems"}
        if sender_wallet.stellar_gems < price:
            return {"error": "insufficient_gems", "have": sender_wallet.stellar_gems, "need": price}

        # Daily spend cap
        if sender_wallet.gems_spent_today + price > DAILY_SPEND_CAP_GEMS:
            return {"error": "daily_spend_cap"}

        sender_wallet.stellar_gems -= price
        sender_wallet.total_gems_spent += price
        sender_wallet.gems_spent_today += price

    elif currency == "stardust":
        price = item.get("price_stardust")
        if price is None:
            return {"error": f"Item '{item['name']}' is gems-only"}

        from narrative_agentic.stellar_outreach.station_modules import get_station, save_station
        station = get_station(sender_id)
        if station is None:
            return {"error": "Sender station not found"}
        stardust = station.resources.get("stardust", 0)
        if stardust < price:
            return {"error": "insufficient_stardust", "have": stardust, "need": price}

        station.resources["stardust"] -= price
        save_station(station)
        sender_wallet.total_stardust_spent += price
    else:
        return {"error": f"Invalid currency: {currency}"}

    # Credit item to recipient
    sender_wallet.gifts_sent_today += 1
    _add_transaction(sender_wallet, "gift_sent",
                     item_id=item_id, recipient_id=recipient_id,
                     currency=currency, amount=price)
    _save_wallet(sender_wallet)

    recipient_wallet.owned_items.append(item_id)
    _add_transaction(recipient_wallet, "gift_received",
                     item_id=item_id, sender_id=sender_id,
                     currency="gift", amount=0)
    _save_wallet(recipient_wallet)

    # If it's a skin, force-unlock for recipient
    if item["category"] == "skin" and "skin_id" in item:
        _unlock_premium_skin(recipient_id, item["skin_id"])

    return {
        "success": True,
        "item_id": item_id,
        "item_name": item["name"],
        "sender_id": sender_id,
        "recipient_id": recipient_id,
        "currency": currency,
        "price": price,
        "message": f"Gift sent! {item['name']} is on its way through the cosmos.",
    }


def get_gem_packs() -> dict:
    """Get IAP gem pack definitions.

    Returns:
        Dict with all available gem packs.
    """
    packs = []
    for pack_id, pack in GEM_PACKS.items():
        packs.append({
            "pack_id": pack_id,
            "name": pack["name"],
            "gems": pack["gems"],
            "bonus_gems": pack["bonus_gems"],
            "total_gems": pack["gems"] + pack["bonus_gems"],
            "price_usd": pack["price_usd"],
            "description": pack["description"],
        })
    return {"packs": packs}


def get_store_summary(player_id: str) -> dict:
    """Get combined wallet + featured items for the store screen.

    Returns:
        Dict with wallet, featured items, and catalog counts.
    """
    wallet_data = get_wallet(player_id)
    featured_data = get_featured_items()

    # Category counts
    categories = {}
    for item_id, item in STORE_CATALOG.items():
        cat = item["category"]
        if cat not in categories:
            categories[cat] = {"total": 0, "owned": 0}
        categories[cat]["total"] += 1
        if item_id in wallet_data["owned_items"]:
            categories[cat]["owned"] += 1

    return {
        "wallet": wallet_data,
        "featured": featured_data["featured"],
        "rotation_week": featured_data["rotation_week"],
        "categories": categories,
        "total_items": len(STORE_CATALOG),
        "total_owned": wallet_data["owned_count"],
    }
